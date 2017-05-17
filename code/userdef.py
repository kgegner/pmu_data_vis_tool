"""
Script Name:
userdef.py

Original Author: K. Gegner
Created On: 8/22/16
Modified By: K. Gegner
Modified On: 5/16/17

Functionality:
- This module contains user specifications for filtering data,
  and values that should remain constant to use the application.
  If no user definitions are made, the following defaults are used:

  NUM_SUBS_WITH_PMU = 10% of total number of buses
  SYSTEM_AREA_NAMES = all areas
  PMU_VOLT_LVLS = two highest voltage levels in case
  COLOR_PALLETTE = 'ggplot'
"""

### USER SPECIFICATIONS
'''
   Change these variables as you like. 
   The program will try to make assumptions so it
   can run, just in case you enter crazy things.
'''

# List of area names that should be considered
SYSTEM_AREA_NAMES = ['TN']

# Number of substations that have a PMU
NUM_SUBS_WITH_PMU = 25

# Specify voltage levels where PMUs likely located
PMU_VOLT_LVLS = ['230', '500']

# Case name and simulation name, as copied from the console 
# after running dataprocessing.py
CASE_NAME = 'UIUC_TN_150'
SIM_NAME = 'fault'

# Map region as selected from the MAPS dictionary below
# eg. MAP_REGION = 'tn'  # for the state of tennessee
MAP_REGION = 'tn'

# Specify whether to use ggplot colors or tableau colors
COLOR_PALLETTE = 'ggplot'  #or 'tableau'

### USER SPECIFICATIONS


### SETTINGS
''' Change only if you know what you are doing. '''

# RGB colors for the analytics tool interface
COLORS = {'blue': (64, 124, 185, 1),
          'dgray': (102, 102, 102, 1),
          'white': (255, 255, 255, 1)}

# Scale the RGB values to the [0,1] range, which is the format kivy accepts
# a is the alpha value for transparency
for color, color_code in COLORS.items():
    r, g, b, a = color_code
    COLORS[color] = (r / 255., g / 255., b / 255., a)

# These are the "Tableau 20" colors as RGB
# http://www.randalolson.com/2014/06/28/how-to-make-beautiful-data-visualizations-in-python-with-matplotlib/  
TABLEAU_COLORS_L = [(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),
    (44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),    
    (148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),    
    (227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),    
    (188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)]    
  
# Scale the RGB values to the [0, 1] range, which is the format matplotlib accepts.    
for i in range(len(TABLEAU_COLORS_L)):
  r, g, b = TABLEAU_COLORS_L[i]    
  TABLEAU_COLORS_L[i] = (r / 255., g / 255., b / 255.) 

# Extract only dark colors for Tableau color list
TABLEAU_COLORS_L_DK = TABLEAU_COLORS_L[::2]

# GGPLOT colors
ggplot_default = ['#E24A33', '#348ABD', '#988ED5', '#777777', '#FBC15E', '#8EBA42', '#FFB5B8']
def hex2color(s):
  "Convert hex string (like html uses, eg, #efefef) to a r,g,b tuple"
  return tuple([int(n, 16)/255.0 for n in (s[1:3], s[3:5], s[5:7])])
GGPLOT_COLORS_L = [hex2color(c) for c in ggplot_default]

if COLOR_PALLETTE == 'ggplot':
  PLOT_COLORS = GGPLOT_COLORS_L
else:
  PLOT_COLORS = TABLEAU_COLORS_L

# Scatterplot marker shapes
SHAPES = ["o", "^", "s", "8"]  # circle, triangle up, square, octagon

# Font pallette
FONTS = {'open_sans': {'regular': './fonts/OpenSans-Regular.ttf',
                       'semibold': './fonts/OpenSans-Semibold.ttf',
                       'bold': './fonts/OpenSans-Bold.ttf'},
         'arial': {'regular': './fonts/Arial.ttf',
                   'bold': './fonts/Arial Bold.ttf'}}

# Plot settings depending on measurement type
PLOT_INFO = {'freq': {'title': 'Frequency', 'ylabel': 'Frequency (Hz)', 'xlabel': 'Time (s)', 'units': 'Hz'},
             'vang': {'title': 'Voltage Angle', 'ylabel': 'Angle (Deg)', 'xlabel': 'Time (s)', 'units': 'Deg.'},
             'vmag': {'title': 'Voltage Magnitude', 'ylabel': 'Voltage (pu)', 'xlabel': 'Time (s)', 'units': 'pu'}}

# Units for different measurement types
UNITS = {'frequency': 'Hertz', 'voltage': 'Per Unit', 'phase angle': 'Degrees'}

# Define lat/long boundary coordinates for regions of north america and the u.s.
# na = north america, us = united states, bpa = bonneville power administration
MAPS = {'na': {'ll_lat': 25, 'll_long': -169, 'ur_lat': 71, 'ur_long': -55},        # north america
        'na_west': {'ll_lat': 30, 'll_long': -141, 'ur_lat': 60, 'ur_long': -102},  # western north america
        'na_mid': {'ll_lat': 25, 'll_long': -106, 'ur_lat': 60, 'ur_long': -86},    # midwest north america
        'na_east': {'ll_lat': 30, 'll_long': -88, 'ur_lat': 60, 'ur_long': -54},    # eastern north america
        'us': {'ll_lat': 25, 'll_long': -125, 'ur_lat': 50, 'ur_long': -66},        # continental united states  
        'us_west': {'ll_lat': 31, 'll_long': -125, 'ur_lat': 50, 'ur_long': -102},  # western continental united states
        'us_mid': {'ll_lat': 25, 'll_long': -106, 'ur_lat': 50, 'ur_long': -89},    # midwest united states
        'us_east': {'ll_lat': 30, 'll_long': -92, 'ur_lat': 50, 'ur_long': -66},    # eastern united states
        'us_pnw': {'ll_lat': 40, 'll_long': -125, 'ur_lat': 50, 'ur_long': -103},   # united states pacific northwest
        'us_ne': {'ll_lat': 39, 'll_long': -81, 'ur_lat': 48, 'ur_long': -66},      # united states northeast
        'us_se': {'ll_lat': 25, 'll_long': -107, 'ur_lat': 40, 'ur_long': -75},     # united states southeast
        'bpa': {'ll_lat': 41, 'll_long': -125, 'ur_lat': 50, 'ur_long': -111},      # bonneville power admin. footprint
        'il': {'ll_lat': 36, 'll_long': -92, 'ur_lat': 43, 'ur_long': -87},         # state of illinois
        'tn': {'ll_lat': 34, 'll_long': -92, 'ur_lat': 38, 'ur_long': -80},}        # state of tennessee    

### SETTINGS


### DO NOT CHANGE
''' 
   Really, don't change any of these, 
   except maybe COL_DELIMITER, if necessary. :)
'''

# File names of files that store measurements for current magnitude,
# voltage magnitude and angle, and frequency. 
# These names remain the same for each TS simulation.
MEASUREMENT_FILES = ['branch_cmag.csv', 'bus_freq.csv', 'bus_vang.csv', 'bus_vmag.csv']

# File names of of files that have unchanging information about the PowerWorld case
CASE_INFO_FILES = ['buses.csv', 'gens.csv', 'real_pmus.csv', 'subs.csv']

# Specify columns that should be kept when parsing PowerWorld data
KEEP_COLS = ['Sub ID', 'Sub Name', 'Bus Number', 'Bus Name',
			       'Area Name', 'Owner Name', 'Nom kV', 'Latitude',
	           'Longitude', 'Gen MW']

# Columns that are absolutely required for each file type
MUST_HAVE_COLS = {'buses': ['Bus Number', 'Sub Name', 'Area Name', 'Nom kV'],
      'gens': ['Bus Number', 'Sub Name', 'Area Name', 'Gen MW'],
      'subs': ['Sub Name', 'Area Name', 'Latitude', 'Longitude']}

# Specify delimiter between words in column heading
# In PowerWorld, this is a space
COL_DELIMITER = ' '

# Make sure SYSTEM_AREA_NAMES are listed in upper case format
try:
  SYSTEM_AREA_NAMES = [name.upper() for name in SYSTEM_AREA_NAMES]
except NameError:
  # System will handle later.
  pass

### DO NOT CHANGE