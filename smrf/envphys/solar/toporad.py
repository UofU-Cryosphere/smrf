import numpy as np
from topocalc.horizon import horizon
from topocalc.shade import shade

from smrf.envphys.solar.twostream import twostream
from smrf.envphys.solar.irradiance import direct_solar_irradiance
from smrf.envphys.thermal.topotherm import hysat
from smrf.envphys.albedo import albedo
from smrf.envphys.constants import SEA_LEVEL, STD_LAPSE, \
    GRAVITY, MOL_AIR, STD_AIRTMP

VISIBLE_MIN = .28
VISIBLE_MAX = .7
IR_MIN = .7
IR_MAX = 2.8


def stoporad(date_time, topo, cosz, azimuth, illum_ang, albedo_surface, wavelength_range,
             tau_elevation=100, tau=0.2, omega=0.85, scattering_factor=0.3):

    if wavelength_range[0] >= VISIBLE_MIN and \
            wavelength_range[1] <= VISIBLE_MAX:
        wavelength_flag = 'vis'
    elif wavelength_range[0] >= IR_MIN and wavelength_range[1] <= IR_MAX:
        wavelength_flag = 'ir'
    else:
        raise ValueError(
            'stoporad wavelength range not within visible or IR wavelengths')

    # check cosz if sun is down
    if cosz < 0:
        return np.zeros_like(topo.dem), np.zeros_like(topo.dem)

    else:
        solar_irradiance = direct_solar_irradiance(
            date_time, w=wavelength_range)

        # Run horizon to get sun-below-horizon mask
        horizon_angles = horizon(azimuth, topo.dem, topo.dx)
        thresh = np.tan(np.pi / 2 - np.arccos(cosz))
        no_sun_mask = np.tan(np.abs(horizon_angles)) > thresh

        # Run shade to get cosine local illumination angle
        # mask by horizon mask using cosz=0 where the sun is not visible
        illum_ang = np.copy(illum_ang)
        illum_ang[no_sun_mask] = 0

        R0 = np.mean(albedo_surface)

        # Run elevrad to get beam & diffuse then toporad
        evrad = Elevrad(
            topo.dem,
            solar_irradiance,
            cosz,
            tau_elevation=tau_elevation,
            tau=tau,
            omega=omega,
            scattering_factor=scattering_factor,
            surface_albedo=R0)

        trad_beam, trad_diff = toporad(
            evrad.beam,
            evrad.diffuse,
            illum_ang,
            topo.sky_view_factor,
            topo.terrain_config_factor,
            cosz,
            surface_albedo=albedo_surface)

    return trad_beam, trad_diff


def stoporad_ipw(date_time, tau_elevation, tau, omega, scattering_factor,
                 wavelength_range, start, current_day, time_zone,
                 year, cosz, azimuth, grain_size, max_grain, dirt, topo):
    """stoporad simulates topographic radiation over snow-covered terrain.
    Uses a two-stream atmospheric radiation model. This function mimics the
    original IPW stoporad program and differences are bit noise resolution
    of the 8-bit IPW images.

    Args:
        date_time (datetime): date and time
        tau_elevation (float): Elevation [m] of optical depth measurement.
        tau (float): optical depth at tau_elevation.
        omega (float): Single scattering albedo.
        scattering_factor (float): Scattering asymmetry parameter.
        wavelength_range (list): Min/max wavelengths to simulate
        start (float): decimal day of last storm
        current_day (float): decimal day for the current day
        time_zone (float): minutes from UTC
        year (float): water year
        cosz (float): cosine of solar zenith angle
        azimuth (float): aspect to the sun
        grain_size (float): starting grain size for albedo
        max_grain (float): max grain size for albedo
        dirt (float): dirt factor for albedo
        topo (Topo class): Topo class for dem

    Raises:
        ValueError: wavelength_range must be in the visible or ir band

    Returns:
        [tuple]: beam and diffuse radiation over snow covered area
    """

    if wavelength_range[0] >= VISIBLE_MIN and \
            wavelength_range[1] <= VISIBLE_MAX:
        wavelength_flag = 'vis'
    elif wavelength_range[0] >= IR_MIN and wavelength_range[1] <= IR_MAX:
        wavelength_flag = 'ir'
    else:
        raise ValueError(
            'stoporad wavelength range not within visible or IR wavelengths')

    # check cosz if sun is down
    if cosz < 0:
        return np.zeros_like(topo.dem), np.zeros_like(topo.dem)

    else:
        solar_irradiance = direct_solar_irradiance(
            date_time, w=wavelength_range)

        # Run horizon to get sun-below-horizon mask
        horizon_angles = horizon(azimuth, topo.dem, topo.dx)
        thresh = np.tan(np.pi / 2 - np.arccos(cosz))
        no_sun_mask = np.tan(np.abs(horizon_angles)) > thresh

        # Run shade to get cosine local illumination angle
        # mask by horizon mask using cosz=0 where the sun is not visible
        illum_ang = shade(topo.sin_slope, topo.aspect, azimuth, cosz)
        illum_ang[no_sun_mask] = 0

        # Run ialbedo to get albedo
        if isinstance(start, float):
            alb_v, alb_ir = albedo(
                start * np.ones_like(topo.dem), illum_ang, grain_size,
                max_grain, dirt)
        else:
            alb_v, alb_ir = albedo(
                start, illum_ang, grain_size, max_grain, dirt)

        # mean albedo for elevrad
        if wavelength_flag == 'vis':
            R0 = np.mean(alb_v)
            alb = alb_v
        else:
            R0 = np.mean(alb_ir)
            alb = alb_ir

        # Run elevrad to get beam & diffuse (if -r option not specified)
        evrad = Elevrad(
            topo.dem,
            solar_irradiance,
            cosz,
            tau_elevation=tau_elevation,
            tau=tau,
            omega=omega,
            scattering_factor=scattering_factor,
            surface_albedo=R0)

        # Form input file and run toporad
        trad_beam, trad_diff = toporad(
            evrad.beam,
            evrad.diffuse,
            illum_ang,
            topo.sky_view_factor,
            topo.terrain_config_factor,
            cosz,
            surface_albedo=alb)

    return trad_beam, trad_diff


def toporad(beam, diffuse, illum_angle, sky_view_factor, terrain_config_factor,
            cosz, surface_albedo=0.0):
    """Topographically-corrected solar radiation. Calculates the topographic
    distribution of solar radiation at a single time, using input beam and
    diffuse radiation calculates supplied by elevrad.

    Args:
        beam (np.array): beam radiation
        diffuse (np.array): diffuse radiation
        illum_angle (np.array): local illumination angles
        sky_view_factor (np.array): sky view factor
        terrain_config_factor (np.array): terrain configuraiton factor
        cosz (float): cosine of the zenith
        surface_albedo (float/np.array, optional): surface albedo. Defaults to 0.0.

    Returns:
        tuple: beam and diffuse radiation corrected for terrain
    """

    # adjust diffuse radiation accounting for sky view factor
    drad = diffuse * sky_view_factor

    # add reflection from adjacent terrain
    drad = drad + (diffuse * (1 - sky_view_factor) +
                   beam * cosz) * terrain_config_factor * surface_albedo

    # global radiation is diffuse + incoming_beam * cosine of local
    # illumination * angle
    rad = drad + beam * illum_angle

    return rad, drad


class Elevrad():
    """Beam and diffuse radiation from elevation.
    elevrad is essentially the spatial or grid version of the twostream
    command.

    Args:
        elevation (np.array): DEM elevations in meters
        solar_irradiance (float): from direct_solar_irradiance
        cosz (float): cosine of zenith angle
        tau_elevation (float, optional): Elevation [m] of optical depth measurement. Defaults to 100.
        tau (float, optional): optical depth at tau_elevation. Defaults to 0.2.
        omega (float, optional): Single scattering albedo. Defaults to 0.85.
        scattering_factor (float, optional): Scattering asymmetry parameter. Defaults to 0.3.
        surface_albedo (float, optional): Mean surface albedo. Defaults to 0.5.
    """

    def __init__(self, elevation, solar_irradiance, cosz, **kwargs):
        """Initialize then run elevrad

        Args:
            elevation (np.array): DEM elevation in meters
            solar_irradiance (float): from direct_solar_irradiance
            cosz (float): cosine of zenith angle
            kwargs: tau_elevation, tau, omega, scattering_factor, surface_albedo

        Returns:
            radiation: dict with beam and diffuse radiation
        """

        # defaults
        self.tau_elevation = 100.0
        self.tau = 0.2,
        self.omega = 0.85
        self.scattering_factor = 0.3
        self.surface_albedo = 0.5

        # set user specified values
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.elevation = elevation
        self.solar_irradiance = solar_irradiance
        self.cosz = cosz

        self.calculate()

    def calculate(self):
        """Perform the calculations
        """

        # reference pressure (at reference elevation, in km)
        reference_pressure = hysat(SEA_LEVEL, STD_AIRTMP, STD_LAPSE,
                                   self.tau_elevation / 1000, GRAVITY, MOL_AIR)

        # Convert each elevation in look-up table to pressure, then to optical
        # depth over the modeling domain
        pressure = hysat(SEA_LEVEL, STD_AIRTMP, STD_LAPSE,
                         self.elevation / 1000, GRAVITY, MOL_AIR)
        tau_domain = self.tau * pressure / reference_pressure

        # twostream over the optical depth of the domain
        self.twostream = twostream(
            self.cosz,
            self.solar_irradiance,
            tau=tau_domain,
            omega=self.omega,
            g=self.scattering_factor,
            R0=self.surface_albedo)

        # calculate beam and diffuse
        self.beam = self.solar_irradiance * \
            self.twostream['direct_transmittance']
        self.diffuse = self.solar_irradiance * self.cosz * \
            (self.twostream['transmittance'] -
             self.twostream['direct_transmittance'])
