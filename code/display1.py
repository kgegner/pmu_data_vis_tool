"""
Module Name:
display1.py

Original Author: K. Gegner
Created On: 1/12/2017
Modified By: K. Gegner
Modified On: 5/15/2017

Functionality:
- Create visualizations for measurement data (vmag, vang, freq, cmag)
- Create visualizations for case info (geo location, cluster assignment, etc)

Notes/Refs:
- http://basemaptutorial.readthedocs.io/en/latest/index.html
- matplotlib and kivy
	https://andnovar.wordpress.com/2015/06/11/backend-for-kivy-in-matplotlib-first-steps/
"""

# Standard python modules
import math
import matplotlib.lines as mlines
from matplotlib.patches import Rectangle
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

# Ignore one warning
import warnings
warnings.filterwarnings("ignore", message="tight_layout : falling back to Agg renderer")


class LinePlot(object):	
	""" 
	Class definition for creating a line plot.
	
	Parameters
	----------
	ax: matplotlib axis object where line plot should be created
	data: dictionary of dataframes for each cluster. Data from which 
		  the plot is made, unless data_centers is provided
	data_name: string specifying the type of data that is being
			   plotted (eg. 'freq', 'vmag', 'vang')
	plot_order_keys: list of keys that are used to specify in what 
					  order elements from data are plotted, so as to
					  ensure important data is not hidden 
					   - eg. list of clusterIds ordered such that the 
					     clusters with largest values are first and those 
						 with the smallest are last, and thus plotted on top
	data_centers: dataframe of cluster centers or averages, if specified, 
				  this is the data from which a line plot will be made
	 
	Keyword arguments
	-----------------
	title_on: Boolean value specifying whether a title should be shown or not
	title: String specifying the title of the line plot
	xlabel: String specifying the x-axis label
	ylabel: String specifying the y-axis label
	color_list: list of colors in (R,G,B,A) format from which plotting colors 
				should be used, in userdef.py, GGPLOT and TABLEAU colors are 
				pre-defined: GGPLOT_COLORS_L, and TABLEAU_COLORS_L.
	
	Output
	------
	matplotlib ax object of a line plot
	"""
	
	def __init__(self, ax, data, data_name, plot_order_keys=None, data_centers=None, **kwargs):

		# Assign input parameters
		self.ax = ax
		self.data = data
		self.plot_order_keys = plot_order_keys
		self.data_centers = data_centers
		if data_name == 'freq':
			self.data_name = 'frequency'
		elif data_name == 'vmag':
			self.data_name = 'voltage'
		else:
			self.data_name = 'phase angle'
			
		# Assign keyword arguments
		self.title_on = kwargs.get('title_on', False)
		self.title = kwargs.get('title', self.data_name.upper())
		self.xlabel = kwargs.get('xlabel', 'Seconds')
		self.ylabel = kwargs.get('ylabel', UNITS[self.data_name])
		self.shade_bounds = kwargs.get('shade_bounds', False)
		self.color_list = kwargs.get('color_list', PLOT_COLORS[:])
	
	def create_plot(self):
		"""
		Function creates a line plot on the ax object passed into the class.
		The data that is plotted is either from the argument data or data_centers, if specified.
		"""
		# If there is data for cluster centers/averages make line plot of just centers
		if self.data_centers is not None:
			  
			# Note: i used to iterate through colors, though same colors in different plots are not synonymous
			for i, plot_order_key in enumerate(self.plot_order_keys):
				# Get dataframe of data for each plotting key (eg. clusterId)
				data = self.data[plot_order_key]				

				# Make a plot for each plotting group and create shading between min and max measurements
				x = data.index.values
				try:
					# Make line plots
					self.ax.plot(x, self.data_centers[plot_order_key], color=self.color_list[i], lw=2.0, zorder=i+1)
				except IndexError:
					# More lines to plot than previously defined colors (shouldn't get here)
					self.ax.plot(x, self.data_centers[plot_order_key], lw=2.0)
		
		# If there is not data for cluster centers/averages, make line plot of all data in specified plotting order
		if self.data_centers is None and self.plot_order_keys is not None:
			
			# Note: i used to iterate through colors, though same colors in different plots are not synonymous
			for i, plot_order_key in enumerate(self.plot_order_keys):
				# Get dataframe of measurement data for each plotting key (eg. clusterId)
				data = self.data.get(plot_order_key, None)
				color = []
				
				# Make a plot for each plotting group
				if data is not None:
					x = data.index.values
					self.ax.plot(x, data, color=self.color_list[i])
		
		# If there is not data for cluster centers/averages or plotting order, create normal plot
		if self.data_centers is None and self.plot_order_keys is None and isinstance(self.data, pd.DataFrame):
			matplotlib.style.use('ggplot')
			self.data.plot(ax=self.ax)
			self.ax.set_axis_bgcolor((1,1,1))	
		
		# Set axis labels
		self.ax.set_xlabel(self.xlabel, fontsize=12, color='black', labelpad = 10)
		self.ax.set_ylabel(self.ylabel, fontsize=12, color='black', labelpad = 10)
		
		# Set axis title, if title_on property set to True
		if self.title_on:
			self.ax.set_title(self.title, fontsize=14, fontweight='bold', color='black')
			self.ax.title.set_position([.5, 1.05]) # add vertical space between plot and title, adjust 1.1
		
		return self.ax


class GeoPlot(object):
	""" 
	Class definition for creating a geographic plot, using Python's Basemap.
	
	Parameters
	----------
	case_info: Data about the case, including bus name, sub name, nominal kV, 
			   operating area, lat/long coord.

	Keyword arguments
	-----------------
	map_region: String specifying a geographic region for which the 
				map should be made. Possible strings are as specified 
				in MAPS in the module userdef.py.
	plot_order_keys: list of keys that are used to specify in what 
	  				  order elements from data are plotted, so as to
	  				  ensure important data is not hidden 
	   					- eg. list of clusterIds ordered such that the 
						  clusters with largest values are first and those 
		 				  with the smallest are last, and thus plotted on top
	
	Output
	------
	case_info: Dataframe with original case information, plus x,y basemap projections
	bmap: A basemap object with points for each element given in case_info, plotted 
		  on the geographic region specified by map_region
	"""
	
	def __init__(self, case_info, **kwargs):
		
		# User can define lat/long coordinates to create the boundaries for 
		# the geographic map, or use a string defined in MAPS in the module 
		# userdef.py for a specific region of North America or the United States.
		ll_long = kwargs.get('ll_long', None)	# lower left of map longitude
		ll_lat = kwargs.get('ll_lat', None)	# lower left of map latitude
		ur_long = kwargs.get('ur_long', None)	# upper right of map longitude
		ur_lat = kwargs.get('ur_lat', None)	# upper right of map latitude
		
		# If the points should be plotted in a particular order, save that order
		self.plot_order_keys = kwargs.get('plot_order_keys', None)

		# If a set of colors has been provided use that to direct coloring of markers
		self.color_list = kwargs.get('color_list', False)
		if self.color_list:
			self.colors_provided = True
		else:
			self.color_list = PLOT_COLORS[:]
			self.colors_provided = False
		
		# User specified lat/long coordinates for each map corner, so create map using those bounds
		if ll_long is not None and ll_lat is not None and ur_long is not None and ur_lat is not None:
			self.map_region = {'ll_long': ll_long, 'll_lat': ll_lat,
								'ur_long': ur_long, 'ur_lat': ur_lat}
		
		# Create map for the region specified by the user, or if no coordinates or region have 
		# been specified, use a map of the continental U.S.
		else:
			self.map_region = kwargs.get('map_region', MAPS['us'])
		
		# Save case information (eg. bus number, substation name, nominal kV, geo coords)
		self.case_info = case_info
		
	def create_points(self):
		""" 
		Function to create the plot background map and the points that will be plotted on top of 
		the geographic basemap.
		"""
		# Create basemap for the specified coordinates or region
		bmap = Basemap(projection='gall',
				   	   llcrnrlon = self.map_region['ll_long'],   # lower-left corner longitude
				   	   llcrnrlat = self.map_region['ll_lat'],    # lower-left corner latitude
				   	   urcrnrlon = self.map_region['ur_long'],   # upper-right corner longitude
				       urcrnrlat = self.map_region['ur_lat'],    # upper-right corner latitude
				       resolution = 'i',
				       area_thresh = 100.0)	
		
		# Get basemap x,y coordinates for the latitude and longitude coordinates of each pmu
		latitude = self.case_info['Latitude'].values
		longitude = self.case_info['Longitude'].values
		x, y = bmap(longitude, latitude)
		
		# Create a dataframe to store the map projection coordinates for each bus or pmu
		self.map_xy_projections = pd.DataFrame({'Bus Number': self.case_info['Bus Number'],
												'Map x': x,
												'Map y': y})
												
		# Add map projections to the case information dataframe
		self.case_info = self.case_info.merge(self.map_xy_projections, on='Bus Number')
		
		return bmap
		
	def create_plot(self):
		""" 
		Calling function to create the geographic map and points to go on it. 
		Point color is determined by the cluster its data is classified in.
		Point shape is determined by the voltage level of the bus/pmu.
		
		Output
		------
		case_info: Dataframe with original case information, plus x,y basemap projections
		bmap: A basemap object with points for each element given in case_info, plotted 
			  on the geographic region specified by map_region
		"""
		# Create point coordinates
		bmap = self.create_points()
		
		# Color each part of the map
		bmap.drawcoastlines(color='gray')
		bmap.drawcountries(color='gray')
		bmap.drawstates(color='gray')
		bmap.fillcontinents(color='#C8C8C8') #'#D3D3D3'
		bmap.drawmapboundary(color='black')
		
		# Assign marker shapes for each voltage level
		marker_shape = {}
		voltages = set(self.case_info['Nom kV'])
		for i, voltage in enumerate(voltages):
			marker_shape[voltage] = SHAPES[i]

		# If plotting order specified
		if self.plot_order_keys is not None:
			
			# Loop through each cluster
			for i, plot_order_key in enumerate(self.plot_order_keys):
				
				# Get data for each cluster and create list of voltage levels in that cluster
				col_name = [col_name for col_name in self.case_info.columns if 'Cluster' in col_name][0]
				data = self.case_info[self.case_info[col_name] == plot_order_key]
				voltages = set(data['Nom kV'])
				
				# Loop through each voltage level in each cluster
				for voltage in voltages:
					
					# Get subset of case data, filtered by cluster id and voltage level, and x/y coordinates
					data_subset = data[data['Nom kV'] == voltage].reset_index()
					x, y = data_subset['Map x'], data_subset['Map y']
					
					# Add points to basemap, and handle case where there are more clusters than defined colors
					try:
						# Make geographic plots
						plot_layer_num = len(self.plot_order_keys) - i
						bmap.plot(x, y, marker_shape[voltage], color=self.color_list[i], 
								  markersize=7, zorder=plot_layer_num)
					except IndexError:
						# More clusters to plot than number of defined colors (shouldn't get here)
						bmap.plot(x, y, marker_shape[voltage], markersize=7)

		# Colors to use for plotting specified, so use those to color the markers
		elif self.colors_provided:
			for i, color in enumerate(self.color_list):
				x,y = self.case_info.iloc[i]['Map x'], self.case_info.iloc[i]['Map y']
				mshape = marker_shape[self.case_info.iloc[i]['Nom kV']]
				bmap.plot(x, y, mshape, color=color, markersize=7)

		# Plotting order not specified and neither is plotting color, 
		# so just color all points black
		else:
			# Get set of voltages
			voltages = set(self.case_info['Nom kV'])
				
			# Loop through each voltage level in each cluster
			for voltage in voltages:

				# Get subset of case data, filtered by cluster id and voltage level, and x/y coordinates
				data_subset = self.case_info[self.case_info['Nom kV'] == voltage].reset_index()
				x, y = data_subset['Map x'], data_subset['Map y']
					
				# Add points to basemap
				bmap.plot(x, y, marker_shape[voltage], color='black', markersize=8)

		# Create legend to identify different voltage levels
		circ_marker = mlines.Line2D([], [], color='black', marker='o', linestyle = 'None',
			markersize=7, label='230 kV')
		tri_marker = mlines.Line2D([], [], color='black', marker='^', linestyle = 'None',
			markersize=7, label='500 kV')
		plt.legend(handles=[circ_marker, tri_marker], loc='lower right', fontsize=10)
				
		return bmap, self.case_info


class Display1(object):
	
	""" 
	Create figure that contains geographic plots and line plots for frequency,
	voltage angle, and voltage magnitude data. Colors in each column of plots 
	correspond to one another. Third row of plots will remain blank until a 
	user selects a region of a geographic plot to investigate further. 
	
	Parameters
	----------
	case_info:	Data about the case, including bus name, sub name, nominal kV, 
				operating area, lat/long coord.
	clustered_data: Dictionary with keys that are the cluster IDs and values
					that are pandas dataframes of measurement data for the 
				    buses in each cluster
				
	Keyword Arguments
	-----------------
	map_region: String specifying a geographic region for which the 
				map should be made. Possible strings are as specified 
				in MAPS in the module userdef.py.
	"""
	
	def __init__(self, case_info, clustered_data, **kwargs):
		
		# Save type of clustering to get cluster assignments from
		self.map_region = kwargs.get('map_region', MAPS['us'])
		
		# Get original measurement data and measurement data that has 
		# been clustered
		self.orig_measurement_data = {}
		self.clust_measurement_data = {}
		for key,value in clustered_data.items():
			self.orig_measurement_data[key] = value['original']
			self.clust_measurement_data[key] = value['clustered']
		
		# Save case information (bus number, substation name, nominal kV, geo coords)
		self.case_info = case_info
	
		# Create a figure
		self.fig = plt.figure()
		self.fig.set_size_inches(10.5, 7, forward=True)
		self.gs = gridspec.GridSpec(3, 3)
		
		# Initialize the points for a mouse click
		self.click_x0 = None
		self.click_y0 = None
		self.click_x1 = None
		self.click_y1 = None
		
		# Add button press and release functionality
		self.fig.canvas.mpl_connect('button_press_event', self.on_press)
		self.fig.canvas.mpl_connect('button_release_event', self.on_release)
			
	def create_figure(self):
		"""
		Create figure that contains geographic plots with markers for every bus given
		in case info. Within those plots, markers are colored by the cluster they 
		belong to. In the second row of plots, the figure contains line plots of the 
		cluster centroids. In the last row of plots, when a user draws a rectangle 
		over buses they want to investigate more in one of the geographic plots, 
		show line plots for only those buses. 
		"""
		
		# Get columns that have main information about the case
		main_cols = [col_name for col_name in self.case_info.columns if 'Cluster' not in col_name]
		
		# Initialize dictionaries to store information on what order clusters should be plotted in
		# and the color for each cluster
		self.cluster_order = {}
		self.cluster_color = {}
		
		# Make geographic plot for each cluster and measurement type
		for i, cluster_col in enumerate(sorted([col_name for col_name in self.case_info if 'Cluster' in col_name])):
			# Make title for each geographic plot
			measure_type = cluster_col.split(' ')[0].lower()
			plot_title = PLOT_INFO[measure_type]['title']
			
			# Set the columns to be read from the measurement data dataframe
			main_cols.append(cluster_col)
			
			# Create axis to host geographic plot and set title
			ax_geo = self.fig.add_subplot(self.gs[0:1, i:i+1])
			ax_geo.set_title(plot_title, fontsize=14, fontweight='bold', color='black')
			ax_geo.title.set_position([.5, 1.1]) # add vertical space between plot and title, adjust 1.1
			ax_geo.name = 'geo: ' + measure_type
			
			# Order the clusters so they get plotted correctly and save the cluster order for each measurement type
			data_type = cluster_col.split(' ')[0].lower()
			cluster_order = self.order_clusters(self.clust_measurement_data[data_type]['cluster centers'], data_type)
			self.cluster_order[data_type] = cluster_order.tolist()

			# Save the color used to identify each cluster
			cluster_color = {}
			if len(self.cluster_order[data_type]) > len(PLOT_COLORS):
				plot_colors = TABLEAU_COLORS_L[:]
			else:
				plot_colors = PLOT_COLORS[:]
			for i, clusterId in enumerate(self.cluster_order[data_type]):
				cluster_color[clusterId] = plot_colors[i]
			self.cluster_color[data_type] = cluster_color

			# Create a geographic plot
			gp, case_info = GeoPlot(self.case_info.copy()[main_cols], 
									plot_order_keys=cluster_order, 
									map_region=self.map_region).create_plot()
			
			# Update case_info to include the geographic x/y map projection coordinates
			self.case_info = pd.merge(self.case_info, case_info)
			
			# Get rid of extra column, so just back to the main columns
			main_cols.remove(cluster_col)
			
		# Make line plot for each measurement
		i=0
		for measure_type, measure_data in sorted(self.clust_measurement_data.items()):
			ax_line = self.fig.add_subplot(self.gs[1:2, i:i+1])
			ax_line.set_axis_bgcolor((1, 1, 1))	# Make background white
			lp = LinePlot(ax_line, measure_data['data by cluster'], measure_type, 
						  self.cluster_order[measure_type], measure_data['cluster centers']).create_plot()
			i = i + 1
		
	def order_clusters(self, cluster_centers, data_type):
		""""
		Function to order the clusters so that the largest signals are plotted in the
		back and smaller signals in the front.
		
		Parameters
		----------
		cluster_centers: Cluster centroids (kmeans) or averages (dbscan)
		data_type:	One of 'freq', 'vang', or 'vmag'
		
		Output
		------
		A list of cluster IDs in the order in which they should be plotted
		"""
		
		# Order the signals to make sure they are plotted so all signals/clusters can be seen
		ordered_clusters = cluster_centers.max(axis=0).sort_values(ascending=False).index.values
			
		# Order clusters based on data type
		if data_type == 'volt':
			ordered_clusters = list(reversed(ordered_clusters))
				
		return ordered_clusters
	
	def on_press(self, event):
		"""
		Function to handle when user clicks down somewhere in the figure.
		Saves the x,y value of the location of cursor when the click was made.
		"""	
		
		# Save the initial x,y coordinates of the cursor	
		self.x0 = event.xdata
		self.y0 = event.ydata
	
	def on_release(self, event):
		"""
		Function to handle when user has released their mouse click. 
		If the user selected within a geographic plot, buses contained 
		by the rectangle the user drew are used to make a subset of the
		case data. If it is a click anywhere else, nothing happens.
		"""
		
		# Save the final x,y coordinate of the cursor				
		self.x1 = event.xdata
		self.y1 = event.ydata
		
		if 'On Demand' in event.inaxes.name:
			lines,labels = event.inaxes.get_legend_handles_labels()
			print(labels)
		else:
			# Filter all buses to get data for only those highlighted by user
			filter1 = self.case_info[self.case_info['Map x'] <= max(self.x0, self.x1)]
			filter2 = filter1[filter1['Map x'] >= min(self.x0, self.x1)]
			filter3 = filter2[filter2['Map y'] <= max(self.y0, self.y1)]
			filter4 = filter3[filter3['Map y'] >= min(self.y0, self.y1)]

			# Clear on demand axes
			for ax in self.fig.get_axes():
				if 'On Demand' in ax.name and 'On Demand' not in event.inaxes.name:
					ax.cla()
		
			# Update line plots for the buses selected
			i = 0
			for measure_type, measure_data in sorted(self.orig_measurement_data.items()):
				data_by_cluster = {}
				color_list = []
				legend_info = []
				bus_num_list = []
				col_name = [cn for cn in filter4.columns.values if 'Cluster' in cn and measure_type in cn.lower()][0]
				cluster_order = [cid for cid in self.cluster_order[measure_type] if cid in set(filter4[col_name])]
				for clusterId in cluster_order:
					bus_nums = filter4[filter4[col_name] == clusterId]['Bus Number'].values
					bus_nums = [str(bus_num) for bus_num in bus_nums]
					bus_num_list.append(bus_nums)
					data_by_cluster[clusterId] = measure_data[bus_nums]
					color = self.cluster_color[measure_type][clusterId]
					color_list.append(color)
			
				ax_line = self.fig.add_subplot(self.gs[2:, i:i+1])
				ax_line.name = 'On Demand' + ' ' + measure_type.title()
				ax_line.set_axis_bgcolor((1, 1, 1))	# Make background white

				lp = LinePlot(ax_line, data_by_cluster, measure_type, cluster_order, color_list=color_list).create_plot()
				
				i = i + 1

			bus_num_list = [item for sublist in bus_num_list for item in sublist]
			buses = [int(bus_num) for bus_num in bus_num_list]
			subs_list = list(set(self.case_info[self.case_info['Bus Number'].isin(buses)]['Sub Name']))
			print('\nSelected Buses/Substations')
			print('-'*26)
			print('Substation list: {}'.format(subs_list))
			print('Bus numbers: {}\n\n'.format(bus_num_list))
			
			# Update plots in figure
			event.canvas.draw_idle()


if __name__ == '__main__':
	# Use ggplot style, so plots are pretty
	matplotlib.style.use('ggplot')
	
	# Reformat case name 
	case_name_formatted = ''.join(CASE_NAME.lower().split('_'))
	
	# Get case information
	case_data_path = os.path.join('..','data', CASE_NAME, 'case_info', 'formatted', 
		'{}_caseinfo_pmus.csv'.format(case_name_formatted))
	case_data = pd.read_csv(case_data_path)

	# Read in measurement data
	pmu_data_path = os.path.join('..','data', CASE_NAME, SIM_NAME, 'formatted')
	clustered_data={}
	for data_type in ['freq', 'vmag', 'vang']:
		fp = os.path.join(pmu_data_path, '{}_{}_pmu_{}.csv'.format(case_name_formatted, SIM_NAME.replace('_', ''), data_type))
		measurement_data = pd.read_csv(fp, index_col='Time')

		# Join measurement data and case information for clustering
		all_data = {'pmu_{}'.format(data_type): measurement_data, 'pmu_info': case_data}

		# Perform clustering
		case_data, clustered_data[data_type] = Clustering(all_data, cluster_method='kmeans',
			num_cluster_method='elbow', measure_type=data_type).doClustering()

	# Create visualizations
	vis = Display1(case_data, clustered_data, map_region=MAPS[MAP_REGION])
	vis.create_figure()

	plt.tight_layout()
	plt.show()