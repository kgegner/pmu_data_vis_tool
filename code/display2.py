"""
Module Name:
display2.py

Original Author: K. Gegner
Created On: 3/26/2017
Modified By: K. Gegner
Modified On: 5/15/2017

Functionality:
- Create visualizations for measurement data (vmag, vang, freq, cmag)
- Create visualizations for case info (geo location, cluster assignment, etc)
"""

# Standard python modules
import math
import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from mpl_toolkits.basemap import Basemap
import numpy as np
import pandas as pd
import os
import re

# Custom modules
from userdef import *
from clustering import *
from outliers import *
from display1 import GeoPlot

# Ignore one warning
import warnings
warnings.filterwarnings("ignore", message="tight_layout : falling back to Agg renderer")


class Display2(object):
	
	""" 
	Create figure that contains histogram of max differences observed for 
	each measurement type--frequency, voltage angle, voltage magnitude. Second 
	row contains line plots of outlier buses, determined by taking the buses 
	that have max difference contained in the last bin, for frequency, and 
	the last two bins for voltage angle and voltage magnitude. The last row
	plots the geographic location of the outlier buses. A user can select a 
	bin from a histogram to see the line and geogrpahic plots for the buses 
	in that bin. 
	
	Parameters
	----------
	case_info:	Data about the case, including bus name, sub name, nominal kV, 
				operating area, lat/long coord.
	measurement_data:	Frequency, voltage angle, and voltage magnitude data.
	"""
	
	def __init__(self, case_info, measurement_data, **kwargs):
		
		# Save case information (bus number, substation name, nominal kV, geo coords)
		self.case_info = case_info
		
		# Save measurement data
		self.measurement_data = measurement_data
		
		# Get keyword arguments
		self.map_region = kwargs.get('map_region', MAPS['us'])	# Assume map of US if not specified
	
		# Get measurement data that has been sorted into bins based on maximum
		# first derivative values, for each measurement type
		self.deriv_objects = {}
		for measure_type, measure_data in self.measurement_data.items():
			self.deriv_objects[measure_type] = Outliers(measure_data, measure_type)
		
		# Create a figure and use 'ggplot' style
		matplotlib.style.use('ggplot')
		self.fig = plt.figure()
		self.fig.set_size_inches(10.5, 6.5, forward=True)
		self.gs = gridspec.GridSpec(3, 3)
		
		# Add button press and release functionality
		self.fig.canvas.mpl_connect('button_press_event', self.on_press)
	
	def create_figure(self):
		
		"""
		Function creates histogram, line, and geographic plots to fill the figure.
		Histograms plot the maximum difference between time steps observed for each bus.
		They are colored according to the time window in which the maximum difference 
		occurred. Line plots are shown for the outlier buses contained within the last
		bin of the frequency histogram and the last two bins of the voltage angle and 
		voltage magnitude histograms. Geographic plots are shown for those same outlier
		buses. 
		
		The user may click on any bin of one the histogram plots to see line and 
		geographic plots for the buses within their selected bin.
		"""
		
		# Create histogram plots		
		i = 0
		for measure_type, deriv_object in sorted(self.deriv_objects.items()):
			
			# Create axes to host histograms for each measurement type
			ax_hist = self.fig.add_subplot(self.gs[0:1, i:i+1])
			
			# Create title for each axis/column of visuals
			ax_hist.set_title(PLOT_INFO[measure_type]['title'], fontsize=14, 
							  fontweight='bold', color='black')
			ax_hist.title.set_position([.5, 1.1]) # add vertical space between plot and title, adjust 1.1
			
			# Create histogram
			ax_hist = deriv_object.makeHist(self.fig, ax_hist)
			
			# Name each histogram plot for identification during user selection
			ax_hist.name = 'histogram: ' + measure_type
			i = i + 1
		
		# Create line and geographic plots
		i = 0
		for measure_type, measure_data in sorted(self.measurement_data.items()):
			
			# Get outlier buses, with bus number represented as a string and integer
			outlier_buses = self.deriv_objects[measure_type].outliers.index
			outlier_buses_int = [int(bus_num) for bus_num in outlier_buses]
			
			# Get subset of the case information data, for just the outlier buses
			case_data_sub = self.case_info[self.case_info['Bus Number'].isin(outlier_buses_int)]
			sub_names = list(set(case_data_sub['Sub Name'][:]))

			# Print selection
			print('\nOutlier {}. Buses/Substations'.format(measure_type.title()))
			print('-'*35)
			print('Substation list: {}'.format(sub_names))
			print('Bus numbers: {}\n\n'.format(outlier_buses_int))
			
			# Create axes to host line ang geographic plots for each measurement type
			ax_line = self.fig.add_subplot(self.gs[1:2, i:i+1])
			ax_line.set_axis_bgcolor((1, 1, 1))	# Make background white
			ax_geo = self.fig.add_subplot(self.gs[2:, i:i+1])

			# Make line and geographic plots of outlier buses and configure axis settings
			ax_line = measure_data[outlier_buses].plot(ax=ax_line, legend=False)
			ax_line.set_xlabel(PLOT_INFO[measure_type]['xlabel'])
			ax_line.set_ylabel(PLOT_INFO[measure_type]['ylabel'])
			lines = ax_line.lines
			colors = [line.get_color() for line in lines]
			geo_plot = GeoPlot(case_data_sub, map_region=self.map_region, color_list=colors)
			geo_plot.create_plot()
			
			# Name each line and geographic plot for identification during user selection
			ax_line.name = 'line: ' + measure_type
			ax_geo.name = 'geo: ' + measure_type
			
			i = i + 1
		
	def on_press(self, event):
		""" 
		Function handles what happens when a user clicks on some portion of the figure.
		If the user clicks on a bin of a histogram, the line plots and geographic plots
		are updated to reflect the buses that are contained within the bin the user
		selected.
		
		Parameters
		---------
		event:	Provided by matplotlib, when user clicks in figure. Gives access to the
				figures axes and x,y click location
		"""
		
		# Get x axis value of where user clicked
		x = event.xdata
		
		# Get name of the axis in which the user clicked
		ax_name = event.inaxes.name
		
		# The user clicked in a histogram plot
		if 'histogram' in ax_name:
			# Get the measurement type of the data in the selected histogram
			measure_type = ax_name.split(' ')[-1]
			
			# Get the bin and bin width defintions for the selected histogram
			bins = self.deriv_objects[measure_type].bins
			bin_width = bins[1] - bins[0]
			
			# Get the dataframe corresponding to the bin selected
			df = self.deriv_objects[measure_type].bin_info_df
			
			# Plot measurement data for the buses in the selected bin.
			# Make sure processing occurs only when the user clicks 
			# inside a histogram plot
			try:
				df = df[df['Lower Bound'] > x - bin_width]
				df = df[df['Upper Bound'] <= x + bin_width]
				buses = df['Bus Numbers'].values[0]
				bus_nums = [int(bus_num) for bus_num in buses]
				sub_names = list(set(self.case_info[self.case_info['Bus Number'].isin(bus_nums)]['Sub Name']))

				# Print selection
				print('\nSelected Buses/Substations')
				print('-'*26)
				print('Substation list: {}'.format(sub_names))
				print('Bus numbers: {}\n'.format(bus_nums))

				# Remove old line and geographic plot axes
				for ax in self.fig.get_axes():
					if 'line' in ax.name:
						ax.cla()
					elif 'geo' in ax.name:
						ax.cla()
				
				# Create axes for the line plots and set the title for each column of visuals
				i = 0
				for measure_type, measure_data in sorted(self.measurement_data.items()):
					
					# Refresh line plot
					ax_line = self.fig.add_subplot(self.gs[1:2, i:i+1])
					ax_line.set_axis_bgcolor((1, 1, 1))	# Make background white
					ax_line = measure_data[buses].plot(ax=ax_line)
					ax_line.legend(loc='upper right')
					ax_line.set_xlabel(PLOT_INFO[measure_type]['xlabel'])
					ax_line.set_ylabel(PLOT_INFO[measure_type]['ylabel'])
					ax_line.name = 'line: ' + measure_type
					lines = ax_line.lines
					colors = [line.get_color() for line in lines]

					# Refresh geographic plot
					ax_geo = self.fig.add_subplot(self.gs[2:, i:i+1])
					ax_geo.name = 'geo: ' + measure_type
					case_data_sub = self.case_info[self.case_info['Bus Number'].isin(bus_nums)]
					geo_plot = GeoPlot(case_data_sub, map_region=self.map_region, color_list=colors)
					geo_plot.create_plot()
					
					i = i + 1
				
				# Update the figure with new line and geographic plots
				event.canvas.draw_idle() #or event.canvas.draw()

			except TypeError:
				pass

if __name__ == '__main__':

	# Reformat case name
	case_name_formatted = ''.join(CASE_NAME.lower().split('_'))
	
	# Get case information
	case_data_path = os.path.join('..','data', CASE_NAME, 'case_info', 'formatted', 
		'{}_caseinfo_pmus.csv'.format(case_name_formatted))
	case_data = pd.read_csv(case_data_path)
	
	# Read in measurement data
	pmu_data_path = os.path.join('..', '..','data', CASE_NAME, SIM_NAME, 'formatted')
	all_measurement_data={}
	for data_type in ['freq', 'vmag', 'vang']:
		fp = os.path.join(pmu_data_path, '{}_{}_pmu_{}.csv'.format(case_name_formatted, SIM_NAME.replace('_', ''), data_type))
		all_measurement_data[data_type] = pd.read_csv(fp, index_col='Time')

	vis = Display2(case_data, all_measurement_data, map_region=MAPS[MAP_REGION])
	vis.create_figure()

	plt.tight_layout(pad=0.8)
	plt.show()