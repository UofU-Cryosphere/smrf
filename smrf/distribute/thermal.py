"""
20160107 Scott Havens

Distribute thermal radiation

"""

import numpy as np
import logging, os
import subprocess as sp
from multiprocessing import Process
from smrf.distribute import image_data
from smrf.envphys import radiation
import smrf.utils as utils
from smrf import ipw

import matplotlib.pyplot as plt

class th(image_data.image_data):
    """
    ta extends the base class of image_data()
    The th() class allows for variable specific distributions that 
    go beyond the base class
    
    Attributes:
    
    """
    
    variable = 'thermal'
    min = -600
    max = 600
    
    # these are variables that can be output
    output_variables = {'thermal':{
                                  'units': 'W/m^2',
                                  'long_name': 'thermal_radiation'
                                  }
                        }
    
    def __init__(self, thermalConfig, tempDir=None):
        """
        Initialize th()
        
        Args:
            solarConfig: configuration from [solar] section
            albedoConfig: configuration from [albedo] section
            stoporad_in: file path to the stoporad_in file created from topo()
            tempDir: location of temp/working directory
        """
        
        # extend the base class
        image_data.image_data.__init__(self, self.variable)
        self._logger = logging.getLogger(__name__)
        
        self.config = thermalConfig
                
        if (tempDir is None) | (tempDir == 'TMPDIR'):
            tempDir = os.environ['TMPDIR']
        self.tempDir = tempDir        
        
                
        self._logger.debug('Created distribute.thermal')
        
        
    def initialize(self, topo, metadata):
        """
        Initialize the distribution, calls image_data.image_data._initialize()
        
        Args:
            topo: smrf.data.loadTopo.topo instance contain topo data/info
            metadata: metadata dataframe containing the station metadata
            
        """

        self._logger.debug('Initializing distribute.thermal')
#         self._initialize(topo, metadata)
        self.veg_height = topo.veg_height
        self.veg_tau = topo.veg_tau
        self.veg_k = topo.veg_k
        self.sky_view = topo.sky_view
        self.dem = topo.dem
               
    
    def distribute(self, air_temp, dew_point, cloud_factor):
        """
        Distribute solar
        
        Args:
            air_temp: distributed air temperature for the time step
            dew_point: distributed dew point for the time step
            cloud_factor: distributed cloud factor for the time step measured/modeled
        """
    
        self._logger.debug('Distributing thermal')
        
        # calculate clear sky thermal
        cth = radiation.topotherm(air_temp, dew_point, self.dem, self.sky_view)
    
        # correct for the cloud factor based on Garen and Marks 2005
        # ratio of measured/modeled solar indicates the thermal correction
        tc = 1.485 - 0.488 * cloud_factor
        cth *= tc
        
        # correct for vegetation
        self.thermal = radiation.thermal_correct_canopy(cth, air_temp, self.veg_tau, self.veg_height)
            
            
    
    