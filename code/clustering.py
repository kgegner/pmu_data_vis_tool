"""
Module Name:
clustering.py

Original Author: K. Gegner
Created On: 12/14/16
Modified By: K. Gegner
Modified On: 5/15/2017

Functionality:
- Clusters voltage, frequency, and current data using K-means and Dbscan clustering
- Number of clusters for K-means is determined from DBSCAN clustering or from 
  testing/scoring a variety of cluster sizes
"""

# Standard python modules
import pandas as pd
import os
from sklearn.cluster import KMeans, DBSCAN

# Silhouette scoring imports
from sklearn.metrics import silhouette_samples, silhouette_score
import matplotlib
import matplotlib.pyplot as plt

# Custom modules
from userdef import *

class Clustering:
	"""
	Class definition for clustering measurement data (voltage mag, voltage ang, 
	frequency, current mag), storing it in a new dataframe, and creating a plot 
	of it.
	
	Parameters
	----------
	data_dict: A dictionary of pandas dataframes containing case information and all 
			   measurement data (frequency, voltage magnitude, voltage angle, or current magnitude).
	measure_type: Whether measurement data is for freq, vmag, vang, cmag
	"""

	def __init__(self, data_dict, measure_type, **kwargs):
		
		# Keyword arguments
		# Decide whether to modify clustering if data is differential
		self.show_plots = kwargs.get('show_plots', False)
		# Save clustering methods to use
		self.num_cluster_method = kwargs.get('num_cluster_method', 'dbscan')	#'elbow' or 'dbscan'
		self.cluster_method = kwargs.get('cluster_method', 'kmeans')			#'kmeans' or 'dbscan'

		# Make plots prettier by using ggplot
		if self.show_plots:
			matplotlib.style.use('ggplot')
		
		# Save type of data being clustered
		self.measure_type = measure_type
		
		# Sort data_dict to get measurement data and case information
		for key, value in data_dict.items():
			if 'info' not in key:
				self.measurement_data = value
			else:
				self.case_info = value
				self.case_info.set_index('Bus Number', inplace=True)
		
	def doClustering(self):
		"""
		Calling function
		
		Output
		------
		case_info: dataframe with bus number, sub name, nominal kV, lat/long 
				   coordinates, cluster assignments
		measurement_data: dictionary of dataframes that contain the original
					  	  measurement data and clustered measurement data, once
						  the clustering method specified by self.cluster_method 
						  has been completed
		"""
		
		# Make sure data is ready for clustering (bus number in each row, measurements in each col)
		formatted_data = self.transpose(self.measurement_data.transpose())
		
		# Perform clustering based on num_cluster_method and cluster_method
		if self.num_cluster_method == 'elbow':
			# Silhouette testing to determine how many clusters to use for kmeans
			num_clusters = self.doSilhouetteScoring(formatted_data)
			
			# Do kmeans to cluster data, using estimated number of clusters found in dbscan
			clustered_data = self.doKmeans(formatted_data, self.measurement_data, num_clusters)
		
		else:
			# Do dbscan to cluster data and get estimated number of clusters
			clustered_data = self.doDbscan(formatted_data, self.measurement_data)
			num_clusters = clustered_data['num clusters']
			
			if self.cluster_method == 'kmeans':
				# Do kmeans to cluster data, using estimated number of clusters found in dbscan
				clustered_data = self.doKmeans(formatted_data, self.measurement_data, num_clusters)
				
		# Save clustering results to a dictionary with clustered data and original data
		measurement_data = {'clustered': clustered_data, 'original': self.measurement_data}
				
		# Add cluster assignment information to case information dataframe
		self.case_info = self.addToCaseInfo(self.case_info, measurement_data['clustered']['cluster assignments df'])

		# Revert index of case_info back to ordered numbers rather than bus number
		self.case_info.index.rename('Bus Number', inplace=True)
		self.case_info.reset_index(inplace=True)
		
		# Show plots, if requested
		if self.show_plots:
			self.plotClusters(self.case_info.copy(), 
				clustered_data['data by cluster'].copy(), 
				clustered_data['cluster centers'])
			plt.show()
				
		return self.case_info, measurement_data
	
	def plotClusters(self, case_data, measurement_data, centers):
		"""
		Create plots to show the cluster center (orange), outlier data (blue), and 
		regular measurement data (gray).
		
		Parameters
		----------
		case_data: Pandas dataframe with bus number, substation name, 
				   nominal kV, lat/long coordinates
		measurement_data: Dictionary of pandas dataframes with data for
						  frequency, voltage angle, and voltage magnitude.
		centers: Dictionary of pandas dataframes with cluster centers for each 
				 cluster ID
		
		Output
		------
		Figures if plotting set to True
		"""
		
		# Loop through each cluster
		i = 0
		for cluster_id, cluster_data in measurement_data.items():
			# Get cluster centers
			cluster_centers = centers[cluster_id]
			
			# Create figure and adjust axis settings
			fig, ax = plt.subplots()
			ax.set_axis_bgcolor((1, 1, 1))	# Make background white
			
			# Plot original cluster data (i.e. not the outlier data)
			color = [(0.7, 0.7, 0.7, 0.5)] * len(cluster_data.columns)
			if len(color) == 1:
				color = color[0]
			if len(color) > 0:
				cluster_data.plot(ax=ax, color=color, legend=False)
							
			# Plot cluster centers
			cluster_centers.plot(ax=ax, color=TABLEAU_COLORS_L_DK[i], lw=2)
			
			# Set title and axis labels
			title = '{} Data K-means Cluster {}'.format(PLOT_INFO[self.measure_type]['title'], cluster_id)
			ax.set_title(title, fontsize=13, y=1.05)
			ax.set_xlabel(PLOT_INFO[self.measure_type]['xlabel'])
			ax.set_ylabel(PLOT_INFO[self.measure_type]['ylabel'], labelpad=10)
			
			i = i + 1
			
	def transpose(self, orig_data):
		"""
		Transpose the original dataframe, so bus numbers are the index, 
		and time values are the column headings.
		
		Parameters
		----------
		orig_data: Measurement data (bus freq, vmag, vang, cmag) where bus numbers are 
				   each column name and each time measurement is the row number
		
		Output
		------
		Transposed dataframe where bus numbers are each row name and each time 
		measurement is the column name
		"""

		if str(orig_data.index.values[0]).isdigit():
			# Original dataframe already in transposed format (probably shouldn't ever get here)
			return orig_data
		else:
			# Transpose original dataframe to get in proper format
			return orig_data.transpose()
	
	def doDbscan(self, formatted_data, orig_data):
		"""
		Perform DBscan clustering. Gets data for each cluster.
		
		Parameters
		----------
		formatted_data: Transposed dataframe of measurement data (bus freq, vmag, vang, cmag)
						where bus numbers are each row name and each time measurement is the 
						column name
		"""

		# Perform DBSCAN clustering
		if self.measure_type == 'freq':
			db = DBSCAN(eps=0.02, min_samples=10).fit(formatted_data)    # freq
		if self.measure_type == 'vang':
			db = DBSCAN(eps=2, min_samples=5).fit(formatted_data)        # vang
		if self.measure_type == 'vmag':
			db = DBSCAN(eps=0.05, min_samples=10).fit(formatted_data)    # vmag

		# Get cluster assignments
		clusterIds = db.labels_
		
		# Number of clusters 
		n_clusters_ = len(set(clusterIds))
		print('DBSCAN estimated number of clusters for {}: {}'.format(self.measure_type,n_clusters_))

		# Create data frame specifying which cluster each bus belongs in
		col_title = self.measure_type.title() + ' ' + 'Dbscan Cluster ID'
		cluster_assignments_df = pd.DataFrame({col_title: clusterIds}, index = orig_data.columns.values)		
		
		# Create dictionary of bus numbers for each cluster
		cluster_assignments_dict = {}
		for clusterId in set(clusterIds):
			cluster_data = cluster_assignments_df[cluster_assignments_df[col_title]==clusterId].index.values
			cluster_assignments_dict[clusterId] = cluster_data

		# Get actual data for each bus in a cluster, save data into dictionary with a key of clusterId
		clustered_data = {}
		for clusterId, bus_nums in cluster_assignments_dict.items():
			clustered_data[clusterId] = orig_data[bus_nums]

		# Create dataframe of cluster averages at each time measurement with columns specifying the cluster
		cluster_avgs_df = pd.DataFrame()
		for clusterId in set(clusterIds):
			avg = clustered_data[clusterId].transpose().mean()
			cluster_avgs_df[clusterId] = avg
		
		# Make dictionary keys uniform with dictionary keys returned in doKmeans
		return {'data by cluster': clustered_data, 'cluster assignments df': cluster_assignments_df,
				'cluster centers': cluster_avgs_df, 'cluster assignments dict': cluster_assignments_dict,
				'num clusters': n_clusters_}
							
	def doKmeans(self, formatted_data, orig_data, num_clusters):
		"""
		Perform Kmeans clustering. Gets data for each cluster and the cluster centers.
		
		Parameters
		----------
		formatted_data: Transposed dataframe of measurement data (bus freq, vmag, vang, cmag)
						where bus numbers are each row name and each time measurement is the 
						column name
		num_clusters:   Number of clusters that should be used for the kmeans clustering, 
						determined by the DBSCAN   
												
		Output
		------
		clustered_data:        Dictionary with keys that are the cluster IDs and values
							   that are pandas dataframes of measurement data for the 
							   buses in each cluster
		cluster_assignments:   Pandas dataframe with cluster IDs for each bus
		"""
		
		# Peform kmeans
		data_kmeans = KMeans(n_clusters=num_clusters).fit(formatted_data)

		# Get cluster centers
		cluster_centers = data_kmeans.cluster_centers_
		
		# Get cluster assignments for each bus
		clusterIds = data_kmeans.labels_
		
		# Create data frame specifying which cluster each bus belongs in
		col_title = self.measure_type.title() + ' ' + 'Kmeans Cluster ID'
		cluster_assignments_df = pd.DataFrame({col_title: clusterIds}, index = orig_data.columns.values)
				
		# Create dictionary of bus numbers for each cluster
		cluster_assignments_dict = {}
		for clusterId in set(clusterIds):
			cluster_data = cluster_assignments_df[cluster_assignments_df[col_title]==clusterId].index.values
			cluster_assignments_dict[clusterId] = cluster_data
		
		# Get actual data for each bus in a cluster, save data into dictionary with a key of clusterId
		clustered_data = {}
		for clusterId, bus_nums in cluster_assignments_dict.items():
			clustered_data[clusterId] = orig_data[bus_nums]

		# Create dataframe of cluster centers at each time measurement with columns specificying the cluster
		cluster_center_df = pd.DataFrame()
		for i, cluster_center in enumerate(cluster_centers):
			cluster_center_df[i] = cluster_center
		cluster_center_df.set_index(orig_data.index, inplace=True)
				
		return {'data by cluster': clustered_data, 'cluster assignments df': cluster_assignments_df,
				'cluster centers': cluster_center_df, 'cluster assignments dict': cluster_assignments_dict,
				'num clusters': num_clusters}
	
	def addToCaseInfo(self, case_info, cluster_assignments):
		"""
		Function to add the cluster ID to each bus number in the case_info dataframe
		
		Parameters
		----------
		case_info:	Dataframe with substation name, bus number, nominal kV, 
					area name, lat/long coordinate
		cluster_assignments:	DBSCAN or kmeans cluster IDs for each bus
		
		Output
		------
		Dataframe with case information and cluster assignments. If no cluster
		assignment, than no data was recorded at that bus.
		"""
		
		# Make sure the index for cluster assignments are integers
		cluster_assignments.index = [int(idx) for idx in cluster_assignments.index]
		
		# Join the cluster assignments with dataframe that has all info (lat/long, sub name, etc) for each bus
		case_info = case_info.join(cluster_assignments)

		# Remove any buses where measurements were not recorded (cluster assignment is na)
		case_info.dropna(inplace=True)
		
		return case_info

	def doSilhouetteScoring(self, data):
		"""
		Try various number of clusters to determine which should be used as the input
		to the final K-means algorithm
		
		Parameters
		----------
		data: Transposed measurement data frame, with bus numbers as the 
			  rows and time values as the columns
			
		Output
		------
		best_num_clusters: number of clusters that should be used in the final K-means algorithm
		"""
		
		# Specify range of clusters to try
		range_n_clusters = [2, 3, 4, 5, 6, 7, 8, 9, 10]
		
		# Initialize dictionary to store silhouette score for each number of clusters tested
		scores_by_n_clusters = {}

		for n_clusters in range_n_clusters:
			# Initialize the clusterer with n_clusters
			clusterer = KMeans(n_clusters=n_clusters)
			cluster_labels = clusterer.fit_predict(data)

			# The silhouette_score gives the average value for all the samples.
			# This gives a perspective into the density and separation of the formed
			# clusters
			silhouette_avg = silhouette_score(data, cluster_labels)

			# Compute the silhouette scores for each sample
			sample_silhouette_values = silhouette_samples(data, cluster_labels)
				
			# Keep track of average silhouette score for each cluster number in a dictionary
			scores_by_n_clusters[n_clusters] = silhouette_avg

		# Save the silohuette score for 2 clusters
		save_score = scores_by_n_clusters[2] 
		
		# Get the lower bound of scores to determine which of the remaining
		# silohuette scores deviate enough from the score for 2 clusters
		l_bound = scores_by_n_clusters[2] - 0.1 * scores_by_n_clusters[2] 
		
		# Initialize dictionary to store the differences between cluster scores
		score_difs = {}
		
		# Initialize list to store cluster numbers for which the silohuette 
		# score differs enough from save_score
		score_deviates_enough = []
		
		# Loop through cluster scores to calculate the difference in silohuette
		# scores and keep track of the clusters with scores that deviate enough
		# from the score for 2 clusters
		for n_clusters, score in scores_by_n_clusters.items():
			if score >= l_bound:
				score_deviates_enough.append(n_clusters)
			score_difs[n_clusters] = score - save_score
			save_score = score
		
		def getBestNumClusters(score_differences):
			"""
			Function returns the number of clusters that creates the elbow point
			on the silohuette score plot. In other words, once the silohoutte score
			stops decreasing by 0.03, after the greatest decrease in silohuette 
			scores has been observed that is considered the elbow point. 
			
			Parameters
			----------
			score_differences: Dictionary with keys of the cluster number and values
							   of the difference in silohuette score between the key 
							   and the silohuette score for the previous key.
			Output
			------
			Best number of clusters to use for the final k-means clustering.
			"""
			
			# Get number of clusters for which the silhoutte score decreases the most
			num_clusters_with_grtst_dec = min(score_difs, key=score_difs.get)
			
			# Check to see if the silohuette score is still decreasing by more than 0.03
			# after the greatest decrease in silohuette scores is observed
			# If so, return the number of clusters for which that is true
			# Otherwise, None is returned
			for num_clusters, difference in score_difs.items():
				if num_clusters >= num_clusters_with_grtst_dec:
					if difference > -0.03:
						# Difference isn't big enough so return previous number of clusters
						return(num_clusters - 1)
		
		# Get the best number of clusters to use in the final k-means clustering algorithm
		best_num_clusters = getBestNumClusters(score_difs)
		if best_num_clusters is None:
			# This if statement may not be necessary, but keep it for now (5/15/17)
			best_num_clusters = min(score_difs, key=score_difs.get) 
		
		# In case the silohuette score for the best_num_clusters is almost
		# exactly the same as the silohuette score for 2 clusters, then
		# just make the final k-means algorithm use 2 clusters
		if best_num_clusters in score_deviates_enough:
			#print('num clusters should be 2, not %d'%best_num_clusters)
			best_num_clusters = 2
						
		# Make plot of silhouette scores
		if self.show_plots:		
			# Create scatter plot
			fig, ax = plt.subplots()
			score_data = list(zip(*scores_by_n_clusters.items()))
			ax.scatter(x=score_data[0], y=score_data[1], color=TABLEAU_COLORS_L[0], s=100)
			ax.set_axis_bgcolor((1, 1, 1))	# Make background white
			ax.grid(b=True, which='both', color=(0.7, 0.7, 0.7, 1), linestyle='-')
			ax.set_xlabel('Number of Clusters')
			ax.set_ylabel('Silhouette Score', labelpad=10)
			title = PLOT_INFO[self.measure_type]['title'] + ' Data Silhouette Score'
			ax.set_title(title, y=1.05, fontsize=13)
	
		print('\nElbow estimated number of clusters for {}: {}'.format(self.measure_type, best_num_clusters))
		
		return best_num_clusters
				
					
if __name__ == '__main__':
	import time
	
	# Reformat case name given in userdef.py	
	case_name_formatted = ''.join(CASE_NAME.lower().split('_'))

	# Get case data
	case_data_path = os.path.join('..','data', CASE_NAME, 
		'case_info', 'formatted', '{}_caseinfo_pmus.csv'.format(case_name_formatted))
	case_data = pd.read_csv(case_data_path)
	
	# Get measurement data and cluster it
	pmu_data_path = os.path.join('..','data', CASE_NAME, SIM_NAME, 'formatted')
	for data_type in ['freq', 'vmag', 'vang']:
		# Read in measurement data
		fp = os.path.join(pmu_data_path, '{}_{}_pmu_{}.csv'.format(case_name_formatted, SIM_NAME.replace('_', ''), data_type))
		measurement_data = pd.read_csv(fp, index_col='Time')
		
		# Join measurement data and case information for clustering
		all_data = {'pmu_{}'.format(data_type): measurement_data, 'pmu_info': case_data}
		
		# Perform clustering
		case_data, clustered_data = Clustering(all_data, data_type, num_cluster_method='elbow', 
			cluster_method='kmeans', show_plots=True).doClustering()
