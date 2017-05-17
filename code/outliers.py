"""
Module Name:
outliers.py

Original Author: K. Gegner
Created On: 3/23/2017
Modified By: K. Gegner
Modified On: 5/10/2017

Functionality:
- Gets outlier buses that are likely the problematic ones an operator 
  should look at
"""

# Standard python modules
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd

# Analytics app modules
from userdef import *

class Outliers:
	"""
	Class definition for clustering measurement data (voltage mag, voltage ang, 
	frequency, current mag), storing it in a new dataframe, and creating a plot 
	of it.
	
	Parameters
	----------
	measure_data: A pandas dataframe of measurement data (one of vmag, vang, freq, cmag).
	measure_type: Whether measurement data is for freq, vmag, vang, cmag
	"""

	def __init__(self, measure_data, measure_type, **kwargs):

		# Save type of measurement data being dealt with and the data itself
		self.measure_type = measure_type
		self.measurement_data = measure_data

		# Get outliers
		self.bin_info_df, self.maxes = self.getHistogramInfo()
		self.outliers = self.getOutliers()
	
	def getHistogramInfo(self):
		""""
		Function calculates difference between timesteps for each bus, and 
		creates a histogram of the maximum difference observed for each
		bus. Histograms are stacked and colored according to the time window
		in which the maximum is observed.
		
		Output
		------
		bin_info_df: Dataframe with bin number, buses contained within 
				     each bin, max differences for each bus within each bin,
				     lower, middle, and upper bound of the bin
		maxes_df: Dataframe with bus numbers as the index, and the values are
				  the maximum observed difference for each bus
		"""
		
		# Get difference between adjacent datapoints of measurement data (1st derivative)
		deriv1 = self.measurement_data.diff()
		deriv1.dropna(inplace=True)
		deriv1.reset_index(drop=True, inplace=True)
		
		# Save time at which the maximum change occurred
		time_of_max = (deriv1.idxmax() * (1/30.))
		time_of_max_start = time_of_max  - (1/60.)
		time_of_max_finish = time_of_max + (1/60.)
		
		# Get maximum differences for each bus
		maxes = deriv1.max(axis=0).sort_values(ascending=False)
		
		# Create dataframe with maximum difference value and the time window it occurred
		maxes = pd.concat([maxes, time_of_max_start, time_of_max_finish], axis=1)
		maxes.columns = ['Max Difference', 'Start Time', 'Finish Time']
		
		# Calculate the number of 10 second time windows in the dataset
		num_time_windows = self.measurement_data.index.values[-1] / 10.
		
		# Create lists and classifier to designate the time window bounds
		initial_t = [num * 10 for num in np.arange(0, num_time_windows)]
		final_t = [10. + num * 10 for num in np.arange(0, num_time_windows)]
		window_classifiers = ['{}-{}'.format(lower, upper) for lower,upper in zip(initial_t, final_t)]
		
		# Loop through the maximum difference data and add a column specifying 
		# the time window classifier the max was observed at
		i = 0
		for bot, top in zip(initial_t, final_t):
			max_data = maxes[maxes['Start Time'] >= bot]
			max_data = max_data[max_data['Finish Time'] < top]
			if len(max_data.index):
				group_list = [window_classifiers[i]] * len(max_data.index)
				max_data['Group'] = group_list
				try:
					maxes_df = pd.concat([maxes_df, max_data])
				except NameError:
					maxes_df = max_data.copy()			
			i = i + 1

		# Make a histogram of the differences between time steps
		self.occurrences, self.bins = np.histogram(maxes_df['Max Difference'], bins=10)

		# Get width of each bin and its lower, center, and upper bounds
		bin_width = self.bins[1] - self.bins[0]
		lower_bound = self.bins[:]
		upper_bound = [bin for bin in self.bins[1:]]
		upper_bound.append(upper_bound[-1]+bin_width)
		centers = [bin+(0.5*bin_width) for bin in self.bins]
		
		# Assign number to each bin, where 0 corresponds to the smallest difference (x value)
		bin_nums = np.arange(0, len(self.bins))
		
		# Get bus numbers contained in each bin
		bus_nums = []
		max_diffs = []
		i = 0
		for lower, upper in zip(lower_bound, upper_bound):
			# Make sure very first bin uses lower bound of 0
			if i == 0:
				lower = 0
				i = 1	# Set so won't enter this if statement again
			
			# Extract subset of data for max differences between lower and upper
			dat = maxes_df[maxes_df['Max Difference']>lower]
			dat = dat[dat['Max Difference']<=upper]
			
			# If there is data available, get bus numbers and maximum difference values
			if len(dat.index):
				bus_nums.append(list(dat.index))
				max_diffs.append(list(dat['Max Difference']))
			else:
				bus_nums.append([])
				max_diffs.append([])
		
		# Create dictionary of bin info
		bin_info_dict = {'Bin Number': bin_nums, 'Bus Numbers': bus_nums, 
						 'Max Differences': max_diffs, 'Lower Bound': lower_bound, 
						 'Center': centers, 'Upper Bound': upper_bound}
		
		# Create data frame of bin info
		bin_info_df = pd.DataFrame.from_dict(bin_info_dict)
		bin_info_df = bin_info_df[['Bin Number', 'Bus Numbers', 
								   'Max Differences', 'Lower Bound', 
								   'Center', 'Upper Bound']]
		
		return bin_info_df, maxes_df
	
	def getOutliers(self):
		"""
		Select buses contained within the last few bins of the histogram.
		If frequency data, outliers contained in last histogram bin.
		If voltage angle data, outlier contained in 3 last histogram bins.
		If voltage magnitude data, outlier contained in 2 last histogram bins.
		
		Output
		------
		outliers: bus numbers of the outlier buses
		"""
		
		# Specify the number of bins for which to look for outliers
		num_bins_dict = {'freq': -1, 'vang': -3, 'vmag': -2}
		full_bins = np.nonzero(self.occurrences)[0].tolist()
		out_bins = full_bins[num_bins_dict[self.measure_type]:]
		
		# Get buses for only the last number of bins, above min_bin
		buses = self.bin_info_df[self.bin_info_df['Bin Number'].isin(out_bins)]['Bus Numbers']
		out_buses = [bus_num for sublist in buses for bus_num in sublist]
		
		# Get outlier data for those buses
		outliers = self.maxes['Max Difference'][out_buses]

		return outliers
	
	def makeHist(self, fig, ax):
		"""
		Create a figure and histogram plot.
		"""
		
		# Make axis background color white instead of gray
		ax.set_axis_bgcolor((1, 1, 1))	# Make background white

		# Create histogram, categorized by time window when the maximum value occurs
		list_of_maxes = []
		labels = []
		groups = np.unique(self.maxes['Group'])
		for group in groups:
			list_of_maxes.append(self.maxes[self.maxes['Group'] == group]['Max Difference'])
			labels.append(group)
		ax.hist(list_of_maxes, self.bins, stacked=True, label=labels)
		ax.legend(title='Time Window (sec)')
		
		# Calculate bin centers
		bin_width = self.bins[1] - self.bins[0]
		centers = [bin+(0.5*bin_width) for bin in self.bins[0:-1]]
		
		# Annotate the figure to show number of items in each bin
		for occurrence, center in zip(self.occurrences, centers):
			if occurrence != 0:
				ax.annotate(str(occurrence), xy=(center, occurrence+0.75), 
						   	ha='center', color=(0.6, 0.6, 0.6, 1))
		
		# Adjust plot settings
		xlab = 'Maximum Difference ({})'.format(PLOT_INFO[self.measure_type]['units'])
		ax.set_xlabel(xlab)
		ax.set_ylabel('Number of Buses')
		ax.get_yaxis().set_ticks([])			# Don't show y ticks
		ax.xaxis.set_ticks_position('bottom')	# Make x ticks appear only at bottom
		
		return ax

if __name__ == '__main__':
	
	def on_press(event):
		x = event.xdata
		print(x)
		df = outs.bin_info_df.copy()
		try:
			df = df[df['Lower Bound'] > x - bin_width]
			df = df[df['Upper Bound'] <= x + bin_width]
			buses = df['Bus Numbers'].values[0]
			print('Bus Numbers:', df['Bus Numbers'].values[0])
			print('Max Differences:', df['Max Differences'].values[0])
		except TypeError:
			pass

	case_name_formatted = ''.join(CASE_NAME.lower().split('_'))
	
	# Get measurement data and cluster it
	pmu_data_path = os.path.join('..', '..','data', CASE_NAME, SIM_NAME, 'formatted')
	for data_type in ['freq', 'vmag', 'vang']:
		
		# Read in measurement data
		fp = os.path.join(pmu_data_path, '{}_{}_pmu_{}.csv'.format(case_name_formatted, SIM_NAME.replace('_', ''), data_type))
		measurement_data = pd.read_csv(fp, index_col='Time')

		# Get outliers
		outs = Outliers(measurement_data, measure_type=data_type)
		
		# Get list of bounds
		lower_bounds = outs.bin_info_df['Lower Bound']
		upper_bounds = outs.bin_info_df['Upper Bound']
		bin_width = upper_bounds[0] - lower_bounds[0]
		
		# Create figure, axis, and use ggplot settings
		matplotlib.style.use('ggplot')
		fig, ax = plt.subplots()
		
		# Make histogram of outliers
		ax = outs.makeHist(fig, ax)
		
		# Create button press functionality
		fig.canvas.mpl_connect('button_press_event', on_press)
		
		plt.show()
		