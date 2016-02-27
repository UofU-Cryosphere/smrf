"""
20160105 Scott Havens

Distribute precipitation

"""

import numpy as np
import logging
from smrf.distribute import image_data
from smrf.envphys import precip
import smrf.utils as utils
import matplotlib.pyplot as plt

class ppt(image_data.image_data):
    """
    ta extends the base class of image_data()
    The ppt() class allows for variable specific distributions that 
    go beyond the base class
    
    Attributes:
        config: configuration from [air_temp] section
        precip: numpy matrix of the precipitation
        stations: stations to be used in alphabetical order
    
    """
    
    variable = 'precip'
    
    # these are variables that can be output
    output_variables = {'precip':{
                                  'units': 'mm',
                                  'long_name': 'precipitation_mass'
                                  },
                        'percent_snow':{
                                  'units': '%',
                                  'long_name': 'percent_snow'
                                  },
                        'snow_density':{
                                  'units': 'kg/m^3',
                                  'long_name': 'snow_density'
                                  },
                        'storm_days':{
                                  'units': 'decimal_day',
                                  'long_name': 'days_since_last_storm'
                                  },
                        'storm_precip':{
                                  'units': 'mm',
                                  'long_name': 'precipitation_mass_storm'
                                  },
                        'last_storm_day':{
                                  'units': 'decimal_day',
                                  'long_name': 'day_of_last_storm'
                                  },
                        } 
    
    min = 0
    max = np.Inf
    
    def __init__(self, pptConfig, time_step=60):
        
        # extend the base class
        image_data.image_data.__init__(self, self.variable)
        self._logger = logging.getLogger(__name__)
        
        # check and assign the configuration
        self.getConfig(pptConfig)
        self.time_step = float(time_step)
        
        self._logger.debug('Created distribute.air_temp')
        
        
    def initialize(self, topo, metadata):
        """
        Initialize the distribution, calls image_data.image_data._initialize()
        
        Args:
            topo: smrf.data.loadTopo.topo instance contain topo data/info
            metadata: metadata dataframe containing the station metadata
                        
        """
        
        self._logger.debug('Initializing distribute.air_temp')
        
        self._initialize(topo, metadata)
        
        self.percent_snow = np.zeros((topo.ny, topo.ny))
        self.snow_density = np.zeros((topo.ny, topo.ny))
        self.storm_days = np.zeros((topo.ny, topo.ny))
        self.storm_precip = np.zeros((topo.ny, topo.ny))
        self.last_storm_day = np.zeros((topo.ny, topo.ny))
#         self.albedo
            
        
        
        
    def distribute(self, data, dpt, mask=None):
        """
        Distribute precipitation
        
        Args:
            data: precip data frame
            dpt: dew point array
            mask: basin mask to apply to the storm days
        """
    
        self._logger.debug('Distributing precip')
        
        # only need to distribute precip if there is any
        if data[self.stations].sum() > 0:
            
            # distribute data and set the min/max
            self._distribute(data, zeros=None)
            self.precip = utils.set_min_max(self.precip, self.min, self.max)
            

            # determine the precip phase
            perc_snow, snow_den = precip.mkprecip(self.precip, dpt)
    
            # determine the time since last storm
            stormDays, stormPrecip = precip.storms_time(self.precip, perc_snow, 
                                                        time_step=self.time_step/60/24, mass=0.5, time=4, 
                                                        stormDays=self.storm_days, 
                                                        stormPrecip=self.storm_precip) 
    
            # save the model state
            self.percent_snow = perc_snow
            self.snow_density = snow_den
            self.storm_days = stormDays
            self.storm_precip = stormPrecip
    
        else:
            
            self.storm_days += self.time_step/60/24
            
            # make everything else zeros
            self.precip = np.zeros(self.storm_days.shape)
            self.percent_snow = np.zeros(self.storm_days.shape)
            self.snow_density = np.zeros(self.storm_days.shape)
            

        # day of last storm, this will be used in albedo
        self.last_storm_day = utils.water_day(data.name)[0] - self.storm_days - 0.001    

        # get the time since most recent storm
        if mask is not None:
            self.last_storm_day_basin = np.max(mask * self.last_storm_day)
        else:
            self.last_storm_day_basin = np.max(self.last_storm_day)
        

         
        
#         plt.imshow(self.last_storm_day), plt.colorbar(), plt.show()
    
    
    