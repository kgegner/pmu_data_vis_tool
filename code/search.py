"""
Module Name:
search.py

Original Author: K. Gegner
Created On: 4/23/2017
Modified By: K. Gegner
Modified On: 5/16/2017

Functionality:
- Allows user to see the geographic location of buses or substations,
  for the power system case specified in userdef.py with CASE_NAME.
- To search for buses, create a list of bus numbers, as integers, 
  in the variable bus_nums_search, within the CHANGE THESE block, below
- To search for substations, create a list of substation names, as strings
  in the variable sub_names_search, within the CHANGE THESE block, below
- You can search for bus numbers OR substation names, but not both in
  a single run of this script. Comment out the variable you are not
  interested in searching by.
"""

import os
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import pandas as pd
from userdef import *
from display1 import GeoPlot

### -------------------------------------- CHANGE THESE ------------------------------------- ###

# Bus numbers to look for
bus_nums_search = [1]

# Substation names to look for
#sub_names_search = ['MEMPHIS_38127']

### -------------------------------------- CHANGE THESE ------------------------------------- ###


### -------------------------------------- DO NOT CHANGE ------------------------------------ ###

# Get case information for all buses and just PMUs
case_name_formatted = ''.join(CASE_NAME.lower().split('_'))

# Get PMU case data
pmu_data_path = os.path.join('..', 'data', CASE_NAME, 'case_info', 'formatted', 
	'{}_caseinfo_pmus.csv'.format(case_name_formatted))
pmu_case_data = pd.read_csv(pmu_data_path)

# Get all case data
all_data_path = os.path.join('..', 'data', CASE_NAME, 'case_info', 'formatted', 
	'{}_caseinfo_bus_info.csv'.format(case_name_formatted))
all_case_data = pd.read_csv(all_data_path)

# Get substation names and geographic locations for given bus numbers
try:
	# Filter out data for buses identified in bus_nums_search
	subset = all_case_data[all_case_data['Bus Number'].isin(bus_nums_search)]
	sub_names = subset['Sub Name'].values
	nom_kvs = subset['Nom kV'].values
	bus_nums = subset['Bus Number']
		
	# Check if substation has a PMU
	pmu_sub_names = set(pmu_case_data.copy()['Sub Name'])
	pmu_assigned = []
	for sub_name in sub_names:
		if sub_name in pmu_sub_names:
			pmu_assigned.append('Yes')
		else:
			pmu_assigned.append('No')
		
	# Print results to console
	print('\nResults')
	print('-'*75)
	for bus_num, sub_name, kv, pmu in zip(bus_nums, sub_names, nom_kvs, pmu_assigned):
		print('Bus: {}, Substation: {}, kV: {}, PMU: {}'.format(bus_num, sub_name, kv, pmu))
	print('')

except NameError:
	# bus_numbers_search not defined
	pass

# Get substation geographic locations for those identified in sub_names_search
try:
	# Filter out data for each matching substation name
	subset = all_case_data[all_case_data['Sub Name'].isin(sub_names_search)]
	for sub_name in sub_names_search:
		try:
			subset_cp = pd.concat([subset_cp, subset[subset['Sub Name']==sub_name].head(1)])
		except NameError:
			subset_cp = subset[subset['Sub Name']==sub_name].head(1)
	subset = subset_cp
	sub_names = sub_names_search

except NameError:
	# sub_names_search not defined
	pass

# Plot results to map
gp, case_info = GeoPlot(subset, map_region=MAPS[MAP_REGION]).create_plot()
plot_x = case_info['Map x']
plot_y = case_info['Map y']
for x, y, sub_name in zip(plot_x, plot_y, sub_names):
	plt.text(x, y, sub_name,fontsize=12, fontweight='bold',
			 ha='center', va='center', color=PLOT_COLORS[1])#color=(0.7, 1, 0.4, 1))
plt.show()

### -------------------------------------- DO NOT CHANGE ------------------------------------ ###



