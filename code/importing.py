"""
Script Name:
importing.py

Original Author: K. Gegner
Created On: 8/22/16
Modified By: K. Gegner
Modified On: 5/16/17

Functionality:
- Reads in and formats data, then saves it
- Filters and reshapes data into various forms, for easier manipulation later
- Reads data from csv files that have been saved from PowerWorld.
- Strips extraneous info from row and column names
- ...

Data Files (csv extension):
_branch_cmag: Contains branch current (pu) measurements
_bus_freq:    Contains bus frequency (Hz) measurements
_bus_vang:    Contains bus voltage angle (deg) measurements
_bus_vmag:    Contains bus voltage magnitude (pu) measurements
_buses:       Contains bus name/number and corresponding substation name/number
_subs:        Contains substation name/number, geographic lat/long coordinate,
			  and bus names/numbers at that substation
_bus_info:    Output file contains bus and sub name and number, area name,
			  geo coordinates, and nominal voltage
_pmu_info:	  Output file contains bus and sub name and number, area name,
				  geo coordinates, and nominal voltage, for only substations assigned a PMU

Data Format Assumptions:
- Data saved from PowerWorld in ~/case_name/ts_name/raw with the above names and csv extension
- Bus, substation, and generator data saved from PowerWorld should have (at least) the columns
  specified in MUST_HAVE_COLS in userdef.py (or shown below):
	MUST_HAVE_COLS = {'buses': ['Bus Number', 'Sub ID', 'Sub Name', 'Area Name', 'Nom kV'],
					  'gens': ['Bus Number', 'Sub Name', 'Area Name', 'Gen MW'],
					  'subs': ['Sub ID', 'Sub Name', 'Area Name', 'Latitude', 'Longitude']}
  To specify, which columns are saved from PowerWorld (see User Guide for more details):
	 1. Open model explorer
	 2. Select the type of data you want to look at: buses, substations, generators
	 3. Within the data area right click
	 4. Select Display/Column Options
	 5. Select the column names you want to include (they should be some version of those in MUST_HAVE_COLS)
- For bus and substation data, final data keeps only columns with the names:
	Bus Number, Bus Name, Sub Name, Area Name, Nom kV, Latitude, Longitude,
	To change these, go to userdef.py and change KEEP_COLS.

Notes for improvement:
- Handle blank cases instead of dropping
- Handle dynamic area names
"""

# -*- coding: utf-8 -*-

# Standard python modules
import pandas as pd
import os

# Analytics app modules
from userdef import *

class CaseData:
	"""
	Class definition for describing and storing PowerWorld data. Data is read in from
	CSV files, is formatted and filtered, stored in a dataframe, and then all dataframes
	are returned in a dictionary.
	Data from PowerWorld includes:
		- Bus names, numbers, voltage levels, and the substation name they belong to.
		- Substation names, numbers, voltage levels, geographic coordinates, and the 
		  area a substation belongs to.
		- Generator bus numbers and generation amount.
		- Known PMU locations, if any (this information is separate from PowerWorld)
		- Measurement data including bus voltage magnitude, voltage angle, and frequency, 
		  and current magnitude in each branch for each simulation.
	
	Parameters
	----------
	fileList: list of full path names to each of the PowerWorld data files
	
	Methods
	-------
	getData: 			Calling function to import all case information (getCaseInfo)
						and measurement data (getMeasurementData) for the user selected simulation.
	getCaseInfo:		Read in PowerWorld data - bus and substation information - 
						known PMU locations, if any, for the selected PowerWorld case.
	getMeasurementData:	Read in PowerWorld simulation data - bus frequency, voltage magnitude, 
						voltage angle, and branch current magnitude for the selected PowerWorld
						simulation
	getGenInfo:			Read in generator information from PowerWorld data including the bus where
						each generator is installed and the MW amount of the generator
	readFile:			Calling function to read a csv file and make sure it has the right header
	filterCols:			Formatting function - remove extraneous columns that are not listed in 
						KEEP_COLS (see userdef.py)
	fixColHeadings:		Formatting function - make column headings more concise
	mergeData:			Formatting function - Merge bus and substation data to make one 
						comprehensive bus/substation information dataframe
	saveData:			Function to save the formatted case information and measurement data
	
	Output
	------
	A dictionary with six data frames for bus information, known PMUs, 
	bus voltage magnitude (pu), bus voltage angle (deg), bus frequency (Hz), 
	and branch current magnitude (pu)
	"""

	def __init__(self, fileList):
		self.file_list = fileList

		# Specify slash that will separate directories (depends on operating system)
		slash = '/'
		if os.name == 'nt':
			# Windows operating system, use backslash to separate directories
			slash = "\\"

		case_name_idx = fileList[0].split(slash).index('data') + 1
		self.case_name = fileList[0].split(slash)[case_name_idx]
		self.simulation_name = fileList[0].split(slash)[case_name_idx+1]
		
	def getData(self):
		"""
		Functionality:	Calling function to read in case information, bus measurement data 
						and PMU locations, if known, otherwise PMU locations are assigned.
						
		Output
		------
		all_data:	Returns bus information and measurement data. 
					Bus information includes:
						Bus name, sub name, nominal kV, lat/long coord, area name
					Measurement data includes:
						Bus frequency, bus voltage mag, bus voltage angle, bus current mag
		"""		
		# Get bus/substation information - names, nominal kV levels, area names, and geographic coordinates
		case_info = self.getCaseInfo()
		
		# Get frequency, voltage, and current measurements
		measurement_data = self.getMeasurementData()

		# Intialize dictionary to store case information and power system measurements at each bus
		all_data = {} 
		
		# Loop through keys of case info and measurement data to store data in all_data
		if case_info and measurement_data:
			for key in measurement_data.keys():
				all_data[key] = measurement_data[key]
			for key in case_info.keys():
				all_data[key] = case_info[key]
			return all_data
		elif measurement_data and not case_info:
			print('Case information not imported correctly.')
		elif case_info and not measurement_data:
			print('Measurement data not imported correctly.')
	
	def getCaseInfo(self):
		"""
		Functionality:	Function to read in case information, including:
						buses, substations, generators, and pmu locations, if known.
						
		Output
		------
		case_info:	Combined dataset of buses, substations, voltage levels,
					geographic coordinates where each substation is located, and location
					of pmus, by substation, if known. 
		"""
		
		# Specify path to read case information from
		slash = "/"
		if os.name == 'nt':
			# Windows operating system, use backslash to separate directories
			slash = "\\"
		read_data_path = os.path.join('..', 'data', self.case_name, 'case_info', 'raw')

		# Get files in the case information directory
		files = [f for f in os.listdir(read_data_path) if os.path.isfile(os.path.join(read_data_path, f))]

		# Provide status
		print('\n\nImporting case information...')
		
		# Initialize dictionary to store case info
		case_info = {}
		
		# Import case information provided all necessary files are available
		try:
			# Loop through files in the case information directory
			for file_name in files:

				# Read in only the required files
				if file_name in CASE_INFO_FILES:

					# Import data for each file_name
					data = self.readFile(os.path.join(read_data_path, file_name))

					# Get the type of data being imported (given by last word before .csv)
					file_type = file_name.split('/')[-1].split('.')[-2]

					# Remove extra columns, replace ambiguous column names, and aggregate generator information
					if file_type == 'gens':
						case_info[file_type] = self.getGenInfo(self.filterCols(data, file_type))
					elif file_type == 'real_pmus':
						case_info[file_type] = data
					else:
						case_info[file_type] = self.filterCols(data, file_type)

			# Merge bus and substation information and save it
			case_info['bus_info'] = self.mergeData(case_info['buses'], case_info['subs'],['Sub Name', 'Sub ID'], 'Sub ID')

			# Remove bus and sub data from data dictionary
			del case_info['buses']
			del case_info['subs']

			# Save newly formatted/filtered case information to csv files
			for key in case_info.keys():
				save_data_path = os.path.join(read_data_path, key) + '.csv'
				if key == 'gens':
					self.saveData(case_info[key], save_data_path,  saveRowNames=True)
				elif key == 'real_pmus':
					pass
				else:
					self.saveData(case_info[key], save_data_path,  saveRowNames=False)

			# If no information on real PMUs (real_pmus.csv doesn't exist), make an empty list
			if 'real_pmus' not in case_info.keys():
				case_info['real_pmus'] = []

			# Provide status
			print('Case information imported.')

			return case_info
	
		except:
			# Data not successfully imported
			raise
	
	def getMeasurementData(self):
		"""
		Functionality:   Function to read in measurement data (vang, vmag, cmag, freq), 
						 modify columns names, and filter out unnecessary columns from the 
						 original dataframe.
		Output
		------
		measurement_data:	dictionary that stores all measurement data
		"""
		# Define the type of slash that is used by the operating system to separate directories
		slash = "/"
		if os.name == 'nt':
			# Windows operating system, use backslash to separate directories
			slash = "\\"
		
		# Provide status
		print('\nImporting measurement data...')

		# Initialize dictionary to store all measurement data for buses 
		measurement_data = {}

		# Make sure all necessary files are read in, if not, return value of False
		try:
			# Loop through listed files
			for file_name in self.file_list:
				# Import data for each file_name
				data = self.readFile(file_name)

				# Get the type of data being imported (given by last word before .csv)
				file_type = file_name.split(slash)[-1].split('.')[-2]

				# Rename columns to be just the bus number
				measurement_data[file_type] = self.fixColHeadings(data, delimiter=COL_DELIMITER)
				self.saveData(measurement_data[file_type], file_name,  saveRowNames=True)

			print('Measurement data imported.')

			return measurement_data

		except:
			# Data not successfully imported
			return False
	
	def getGenInfo(self, gen_data):
		"""
		Summarizes generator information including substation name, number of generators, and 
		total MW generating capacity for the generators in the areas specified in SYSTEM_AREA_NAMES
		
		Parameters
		----------
		gen_data:	dataframe with generator information including, bus number, 
					generating amount, substation name, area name
					
		Output
		------
		Dataframe indexed by substation name and columns with a list of all 
		the generator buses at each substation, area name, number of generators,
		and generation amount (based on last power flow run in PowerWorld)
		"""
		# Make sure values in Gen MW column are float values, not strings
		gen_data['Gen MW'] = pd.to_numeric(gen_data['Gen MW'], errors='ignore')
		
		# Get generators in each area listed in SYSTEM_AREA_NAMES, if specified
		try:
			# Get possible area names
			all_area_names = set(gen_data['Area Name'])
			
			# Create list of area names that should be kept based on user specification and 
			# those available in gens.csv
			keep_area_names = [area_name for area_name in all_area_names if area_name in SYSTEM_AREA_NAMES]
			
			# Get generator information for only the areas listed in keep_area_names
			# Provided user has specified correct areas to be considered
			if len(keep_area_names):
				gens = gen_data[gen_data['Area Name'].isin(keep_area_names)]
			else:
				# Deal with the case where the area name(s) listed in SYSTEM_AREA_NAMES do not
				# match any of the areas listed in the gens.csv file.
				gens = gen_data.copy()
				print('\n-----------------------------WARNING MESSAGE-----------------------------')
				print('The program assumed you wanted to include generator data for\n'
					  'all areas in the gens.csv file, because it could not find the\n'
					  'area name(s) you listed. Make sure you have specified the correct\n' 
					  'area(s) you want to use in the userdef.py file for the variable,\n'
					  'SYSTEM_AREA_NAMES, and then run the program again.')
				print('-----------------------------WARNING MESSAGE-----------------------------\n')
			
		except NameError:
			# Exception to deal with the case that the user accidentally deleted the variable
			# SYSTEM_AREA_NAMES from the userdef.py file.
			gens = gen_data.copy()
			print('\n-----------------------------WARNING MESSAGE-----------------------------')
			print('The program assumed you wanted to include generator data for\n'
				  'all areas in the gens.csv file, because it could not find your\n'
				  'definition of the variable SYSTEM_AREA_NAMES in the userdef.py\n'
				  'It is possible you accidentally deleted it. So, create a new\n'
				  'one in the USER SPECIFICATIONS section and include the areas you\n'
				  'want, and run the program again.\n'
				  "Eg. SYSTEM_AREA_NAMES = ['MY AREA NAME']")
			print('-----------------------------WARNING MESSAGE-----------------------------\n')

		
		def getGenBuses(gen_data):
			"""
			Return the substation name and the bus numbers that reside in it, as a data frame
			
			Parameters
			----------
			gen_data:	dataframe with generator information including, bus number, 
						generating amount, substation name, area name
			
			Output
			------
			Dataframe indexed by substation name and column with a list of all 
			the generator buses at each substation
			"""
			# Initialize dictionary to store the bus numbers for each substation
			buses_by_sub = {}
		
			# Loop through each unique substation
			for sub in gen_data['Sub Name'].unique():
		
				# As long as the substation name is a string (eliminate any 'nan' float values)
				if isinstance(sub, str):
			
					# Extract data for that specific substation
					sub_data = gen_data[gen_data['Sub Name'] == sub]
			
					# Initialize empty list to store bus numbers for the current substation
					bus_list = []
			
					# Loop through all the buses in each substation
					for bus_num in sub_data['Bus Number']:
						bus_list.append(str(bus_num))
			
					# Save bus list to full dictionary
					buses_by_sub[sub] = ', '.join(bus_list)

			# Make dictionary of bus numbers at each substaion into a dataframe
			buses_by_sub = pd.DataFrame.from_dict(buses_by_sub, orient='index')
			buses_by_sub.sort_index(axis=0, inplace=True)
			buses_by_sub.columns = ['Bus Numbers']
			
			return buses_by_sub

		# Count number of generators and total gen MW, save bus numbers and area name at each substation
		num_gens = gens['Sub Name'].value_counts()
		num_gens.name = 'Num Gens'
		mw_cap = gens.groupby(['Sub Name'])['Gen MW'].sum()
		mw_cap.name = 'Total Gen MW'
		bus_nums = getGenBuses(gens)
		area_names = gens[['Sub Name', 'Area Name']].drop_duplicates().dropna()
		area_names.set_index('Sub Name', inplace=True)

		# Merge all data into one dataframe
		gen_data_final = pd.merge(area_names, pd.DataFrame(bus_nums), left_index=True, right_index=True)
		gen_data_final = pd.merge(gen_data_final, pd.DataFrame(mw_cap), left_index=True, right_index=True)
		gen_data_final = pd.merge(gen_data_final, pd.DataFrame(num_gens), left_index=True, right_index=True) 
		gen_data_final = gen_data_final[['Area Name', 'Total Gen MW', 
										  'Num Gens', 'Bus Numbers']].sort_values(by='Total Gen MW', ascending=False)
		
		return gen_data_final

	def readFile(self, dataPath):
		"""
		Read csv file at the specified dataPath and makes sure the correct column
		headings for the data are used.
		
		Parameters
		----------
		dataPath:	Full filepath to a csv file that should be read
		
		Output
		------
		Pandas dataframe after being read in from a csv file
		"""
		# Print to console which file is currently being read in
		print(dataPath)
		
		try:
			# Read csv and store in new data frame, data
			data = pd.read_csv(dataPath, low_memory=False)
		except:
			# Read csv with utf-8 encoding (western europe), store in data frame, data
			data = pd.read_csv(dataPath, encoding='iso-8859-1', low_memory=False)

		# If there are the wrong header names, correct them
		if 'Unnamed' in data.columns.values[1]:
			# Assign names listed in first row to be the column headings
			data.columns = list(data.iloc[0])
			
			# Remove the row of column names from the rest of the data
			data.drop(0, inplace=True)
		
		return data

	def filterCols(self, data, file_type):
		"""
		Change any ambiguous column names to more specific ones, filter
		out any extraneous columns that are not listed in KEEP_COLS, and make
		sure all columns listed in MUST_HAVE_COLS are included, otherwise raise
		an error.
		
		Parameters
		----------
		data:	dataframe of case information or generator data
		file_type:	Specifies whether data is case info or generator data
		
		Output
		------
		Dataframe with only the columns listed in KEEP_COLS. To change the 
		columns to be included, change KEEP_COLS in userdef.py
		"""
		# Make a copy of the column headings
		header = list(data.columns.values)

		# Loop through column heading names
		for index, element in enumerate(header):
			# If necessary, change column names
			if element == 'Number of Bus' or element == 'Number':
				header[index] = 'Bus Number'
			if element == 'Name of Bus' or element == 'Name':
				header[index] = 'Bus Name'
			if element == 'Area Name of Bus':
				header[index] = 'Area Name'
			if element == 'Sub Name of Bus':
				header[index] = 'Sub Name'

		# Update column headings
		data.columns = header

		# Loop through column names again
		for column in header:
			# If column not one of the needed columns, delete it
			if column not in KEEP_COLS:
				data.drop(column, axis=1, inplace=True)
			
		# Remove 'Gen MW' column from any non-generator data
		if 'Gen MW' in data.columns and file_type != 'gens':
			data.drop('Gen MW', axis=1, inplace=True)
		
		def checkForNeededCols(data, file_type):
			"""
			Function makes sure the necessary columns are included. If there are missing columns,
			an error is raised specifying the file type and name of columns that are missing. To 
			correct the missing columns, the user needs to re-save the appropriate file, making sure
			to include the correct column when doing so.
				- Within model explorer for the correct file type 
					right click in the data --> Display/Column Options --> select items that are missing
				 - Note: the names of the missing columns may be abbreviated compared to what is seen in PowerWorld
			
			Parameters
			----------
			data: Pandas dataframe with bus, substation, or generator data
			file_type: string specifying whether data is buses, subs, or gens
			
			Output
			------
			Pandas dataframe with abbreviated/clarified columns names and only the columns specified in KEEP_COLS
			"""
			# Get columns, if any, that are missing from those listed in MUST_HAVE_COLS based on the file type
			missing_cols = list(filter(lambda col_heading: col_heading not in data.columns, MUST_HAVE_COLS[file_type]))
			
			# If there are missing columns, print an error message and raise an exception
			if len(missing_cols):
				print('\n-----------------------------ERROR MESSAGE-----------------------------')
				print('File ending in {}.csv is missing column(s): {}'.format(file_type, missing_cols))
				print('You need to re-save {} data from PowerWorld, and make sure'.format(file_type))
				print('a column with information for the above missing column(s)')
				print('are included in the new file.')
				print('-----------------------------ERROR MESSAGE-----------------------------\n')
				raise ValueError('File ending in {}.csv is missing column(s): {}'.format(file_type, missing_cols))
			# There are no missing columns, so just return the data, unchanged
			else:
				return data
		
		return checkForNeededCols(data, file_type)

	def fixColHeadings(self, data, delimiter):
		"""
		Change a column's heading to a more concise representation, usually it is 
		shortened to one of the words already contained in the full column heading.
		
		Parameters
		----------
		index: specifies the location of the word to keep for each column name
		delimiter: specifies the character that separates words in each column name
		
		Output
		------
		Dataframe with more concise column headings
		"""
		# Get column names from the desired data frame
		colNames = list(data.columns.values)

		# Create blank list to store the new column names
		colNamesNew = []

		# Save only the part of the column name specified by the index location
		for name in colNames:
			
			# Split the column name into distinct parts and remove any spaces from that list
			nameParts = name.split(delimiter)
			nameParts = list(filter(('').__ne__, nameParts))

			if 'Line' in name or 'Transformer' in name or 'Series Cap' in name:
				# Change column heading for branch data to be: branchType toBusNum TO fromBusNum CKT #
				colNamesNew.append(' '.join(nameParts[0:6]))
			if 'Bus' in name:
				# Change column heading for bus data to be: busNum
				bus_num = [int(char) for char in name.split() if char.isdigit()][0]
				colNamesNew.append(bus_num)
			if 'Time' in name:
				# Just keep the time column heading as is: Time
				colNamesNew.append(name)

		# Update the column names
		data.columns = colNamesNew

		# Make row names the time the measurement was taken
		data.set_index(data.loc[:, 'Time'], inplace=True)
		data.drop('Time', axis=1, inplace=True)

		return data

	def mergeData(self, bus_df, sub_df, joinByCols, cols2delete):
		"""
		Join two dataframes by the columns specified in joinByCols. Any column
		names listed in cols2delete, will be deleted from the merged dataframe.
		
		Parameters
		----------
		bus_df:	Dataframe with bus name, number, substation name, etc.
		sub_df: Dataframe with substation name, nominal kV, etc.
		joinByCols: List of column names to compare and join the two dataframes on 
					 when they are matching
		cols2delete: List of column names that specify which ones should be deleted
		
		Output
		------
		Merged dataframe with bus and substation information
		"""
		# Check if the incoming data frames have common columns besides those they
		# will be joined by. If so, delete those duplicates from df1.
		matchingColNames = []
		for colName in list(bus_df.columns.values):
			if colName in list(sub_df.columns.values) and colName not in joinByCols:
				matchingColNames.append(colName)
		bus_df.drop(matchingColNames, inplace=True, axis=1)

		return pd.merge(bus_df, sub_df, on=joinByCols).drop(cols2delete, 1)

	def saveData(self, data, dataPath, saveRowNames=False):
		"""
		Save dataFrame to a csv file at the given dataPath and with a file name
		format of powerworldcasename_transientstabilityname_filename. If the file
		you are trying to write to is open in another program, an error is raised.
		
		Parameters
		----------
		data:			Dataframe that needs to be saved as a csv file
		dataPath:		File location of where the csv should be saved 
		saveRowNames:	Boolean value that is used to specify whether the row names should be saved. 
						Should be saved when indexes are something important, like bus numbers.
		"""
		# Split data path into pieces (account for operating system's directory separator)
		slash = "/"
		if os.name == 'nt':
			slash = "\\"
		split_data_path = dataPath.split(slash)

		# Get index of raw directory (this is the directory files from PW are saved in)
		dir_index = split_data_path.index('raw')

		# If formatted data directory doesn't exist, create it
		directory = os.path.join(slash.join(split_data_path[:dir_index]), 'formatted')
		if not os.path.exists(directory):
			os.makedirs(directory)

		# Create file name for saving the data (include case, simulation, and measurement type names)
		file_type = split_data_path[-1].split('.')[-2]
		data_type = ''.join(split_data_path[dir_index-1].split('_'))	# Simulation name or 'case_info'
		case_name = ''.join(self.case_name.lower().split('_'))
		file_path = os.path.join(directory, '_'.join([case_name, data_type, file_type])) + '.csv'
		
		# Save data. If file trying to be saved is open, raise an error
		try:
			data.to_csv(file_path, index=saveRowNames)
		except PermissionError:
			print("\nERROR: The file {} is open, and can't be saved. Close it, then run program again.\n".format(file_path))
			raise

class PmuData:
	
	def __init__(self, case_data, fileList):
		# Case information
		self.real_pmus = case_data['real_pmus']
		self.gens = case_data['gens']
		self.bus_info = case_data['bus_info']
		
		# Case measurement data
		self.bus_freq = case_data['bus_freq']
		self.bus_vang = case_data['bus_vang']
		self.bus_vmag = case_data['bus_vmag']
		self.branch_cmag = case_data['branch_cmag']
		
		# Information for file saving
		# Specify slash that will separate directories (depends on operating system)
		slash = '/'
		if os.name == 'nt':
			# Windows operating system, use backslash to separate directories
			slash = "\\"
		self.file_list = fileList
		case_name_idx = fileList[0].split(slash).index('data') + 1
		self.case_name = fileList[0].split(slash)[case_name_idx]
		self.simulation_name = fileList[0].split(slash)[case_name_idx+1]
	
	def getAllPmuData(self):
		"""
		Calling function to either return the substation locations PMUs, when known
		or to return hypothetical substation locations of PMUs, and to filter the
		power system measurement data for just buses being monitored by PMUs.

		Output
		------
		pmu_data:	Dictionary of Pandas dataframes including measurement data for
		 			bus freq, volt ang, volt mag, amd current mag, as well as
		 			pmu location/substation information
		"""
		# Make dictionary of dataframes with PMU location info and PMU measurement data
		pmu_info = self.getPmuInfo()
		pmu_data = self.getPmuMeasurementData(pmu_info)
		pmu_data['pmu_info'] = pmu_info

		# Save PMU locations (after assigning and/or using known locations)
		file_name = '_'.join([''.join(self.case_name.lower().split('_')), 'caseinfo', 'pmus.csv'])
		file_path = os.path.join('..', 'data', self.case_name, 'case_info', 'formatted', file_name)

		# If the file trying to be saved is open, raise an error
		try:
			pmu_info.to_csv(file_path, index=False)
		except PermissionError:
			print("\nERROR: The file {} is open, and can't be saved. Close it, then run program again.\n".format(file_path))
			raise

		return pmu_data

	def getPmuInfo(self):
		"""
		Calling function to either return the substation location of PMUs,
		when known, or to return hypothetical substation locations of PMUs.

		Output
		------
		pmu_info:	A Pandas dataframe with substation name and voltage level
					of where PMUs are located
		"""
		# Get bus/sub information for known PMUs, if any are known
		if len(self.real_pmus):
			# Store bus/sub information for where PMUs are known to be located
			self.real_pmu_bus_info = self.getKnownPmuBusInfo()
			
			# Get number of known substations that have PMUs
			num_known_PMUs = len(self.real_pmu_bus_info[['Sub Name', 'Nom kV']].drop_duplicates())
		else:
			# No known PMUs
			num_known_PMUs = 0
			
		# Assign PMUs to substations until NUM_SUBS_WITH_PMUs is met
		num_pmus_needed = NUM_SUBS_WITH_PMU - num_known_PMUs
		pmu_info = self.assignPmus(num_pmus_needed)
		
		# Print brief summary of PMU related info
		print('\nPMU Assignment Summary')
		print('Num PMUs requested:', NUM_SUBS_WITH_PMU)
		print('Num PMUs known:', num_known_PMUs)
		print('Num PMUs needed:', num_pmus_needed)
		print('Num PMUs assigned:', len(pmu_info[['Sub Name', 'Nom kV']].drop_duplicates()))
		
		return pmu_info
			
	def getKnownPmuBusInfo(self):
		"""
		Functionality: Get bus information at substations that are known to have a PMU
			
		Output
		------
		pmus:	If known, list of substations and their voltage level where PMUs are located.
				If PMU locations not known, program assigns PMUs with precedence 
				to generator substations and high voltages until required PMU amount
				met. It is assumed that a PMU will monitor all buses at the substation
				it is assigned to.
		"""
		# Flag to determine whether or not a new dataframe should be created to store bus/sub info
		make_new_df = True
		
		# Loop through
		for sub in self.real_pmus['Sub Name'].unique():
			
			# Filter data for the current substation being checked
			current_sub_info = self.bus_info[self.bus_info['Sub Name'] == sub]
				
			# Loop through voltage levels, for each sub, that should have a PMU 
			for index, volt in self.real_pmus[self.real_pmus['Sub Name'] == sub].iterrows():
					
				# Filter data by substation and the appropriate voltage level
				by_sub_volt = current_sub_info[current_sub_info['Nom kV']== str(volt['Nom kV'])]

				# Store bus/substation information for all substations that are known to have PMUs
				if make_new_df:
					real_pmu_buses = by_sub_volt.copy()
					make_new_df = False
				else:
					real_pmu_buses = real_pmu_buses.append(by_sub_volt.copy(), ignore_index=True)
			
		return real_pmu_buses
		
	def assignPmus(self, num_pmus_needed):
		"""
		Functionality: This function is called when the number of known PMUs is less than the
					   total number of PMUs that are needed. It assigns PMUs to substations
					   until the number of required PMUs is met. Precedence of substation is
					   given to substations with generators and higher voltage levels
					   (eg. 230,500 kV).

		Parameters
		-----------
		num_pmus_needed: The difference between the required number of PMUs and the number
						 of known substations where PMUs are located.

		Output
		------
		all_pmus:	Pandas dataframe with bus num, bus name, sub name, area name, volt level,
		 			and lat/long coord, of substation where PMUs are really located, or have
		 			been assigned.If not all PMU locations known, program assigns PMUs with
		 			precedence to generator substations and high voltages until required PMU
		 			amount met. It is assumed that a PMU will monitor all buses at the substation
					it is assigned to.
		"""
		# May not known locations of all required PMUS, so assign remaining number of PMUs to substations
		if num_pmus_needed == 0:
			# All PMU locations known, so just return the info already collected
			return self.real_pmu_bus_info
		else:
			# Need to assign PMUs to additional substations
			try:
				# Get generator substations and remove any that have already been accounted for in known PMUs
				gen_subs = self.gens[~(self.gens.index.isin(self.real_pmu_bus_info['Sub Name'].unique()))]
			except AttributeError:
				# No known PMUs
				gen_subs = self.gens.copy()
			
			# Get generator substation info
			if len(gen_subs) > num_pmus_needed:
				gen_subs = gen_subs.head(num_pmus_needed)
			else:
				gen_subs = gen_subs.copy()

			# Filter bus_info based on SYSTEM_AREA_NAMES provided, and handle case where improperly done
			try:
				# Get possible area names
				all_area_names = set(self.bus_info['Area Name'])
				
				# Create list of area names that should be kept based on user specification and 
				# those available in bus_info.csv
				keep_area_names = [area_name for area_name in all_area_names if area_name in SYSTEM_AREA_NAMES]
				
				# Get bus information for only the areas listed in keep_area_names
				# Provided user has specified correct areas to be considered
				if len(keep_area_names):
					bus_info = self.bus_info[self.bus_info['Area Name'].isin(keep_area_names)]
				else:
					# Deal with the case where the area name(s) listed in SYSTEM_AREA_NAMES do not
					# match any of the areas listed in the bus_info.csv file.
					bus_info = self.bus_info.copy()
				
			except NameError:
				# Exception to deal with the case that the user accidentally deleted the variable
				# SYSTEM_AREA_NAMES from the userdef.py file.
				bus_info = self.bus_info.copy()
				
			# Get voltage levels that PMUs should monitor, will be used to filter which substations
			# could be assigned a PMU 
			volt_lvls = bus_info['Nom kV'][:]
			try:
				pmu_volt_lvls = [kv for kv in volt_lvls if kv in PMU_VOLT_LVLS]
				
				if not len(pmu_volt_lvls):
					volt_lvls = [int(float(kv)) for kv in volt_lvls]
					volt_lvls_count = [{'kv': kv, 'num_buses': volt_lvls.count(kv)} for kv in set(volt_lvls) if kv >= 100]
					sorted_volt_lvls_count = sorted(volt_lvls_count, key=lambda k: k['num_buses'], reverse=True) 
					pmu_volt_lvls = [str(dictionary['kv']) for dictionary in sorted_volt_lvls_count[:2]]
			
			except NameError:
				volt_lvls = [int(float(kv)) for kv in volt_lvls]
				volt_lvls_count = [{'kv': kv, 'num_buses': volt_lvls.count(kv)} for kv in set(volt_lvls) if kv >= 100]
				sorted_volt_lvls_count = sorted(volt_lvls_count, key=lambda k: k['num_buses'], reverse=True) 
				pmu_volt_lvls = [str(dictionary['kv']) for dictionary in sorted_volt_lvls_count[:2]]
			
			# Assign PMUs to generator substations and get their bus/sub information (after filtering for correct area)
			fake_pmu_bus_info = bus_info[bus_info['Sub Name'].isin(gen_subs.index)]
			fake_pmu_bus_info = fake_pmu_bus_info[fake_pmu_bus_info['Nom kV'].isin(pmu_volt_lvls)]

			# Calculate number of substations that still need to have a PMU, so that NUM_SUBS_WITH_PMU is met
			num_pmus_needed = num_pmus_needed - len(fake_pmu_bus_info[['Sub Name', 'Nom kV']].drop_duplicates())
			
			# Filter out any substations that are known to have PMUs (handle case where there are no known PMUs)
			try:
				sub_info = bus_info[~(bus_info['Sub Name'].\
									isin(self.real_pmu_bus_info['Sub Name'].unique()))]
			except AttributeError:
				sub_info = bus_info.copy()
			
			# Filter out fake substations that have not already been assigned PMUs
			sub_info = sub_info[~(sub_info['Sub Name'].\
						isin(fake_pmu_bus_info['Sub Name'].unique()))]

			# Filter out substations that meet voltage level criteria
			sub_info = sub_info[(sub_info['Nom kV'].isin(pmu_volt_lvls))]
			
			# Filter out number of substations to meet the number of pmus that are still needed
			sub_info = sub_info[['Sub Name', 'Nom kV']].drop_duplicates().head(num_pmus_needed)
			
			# Assign remaining PMUs to substations
			# From bus info, filter out the bus/sub information that matches the substations found above
			# NOTE: May have one more PMU than specified if last PMU assigned to substation with both 230 & 500 kV levels
			more_fake_pmu_bus_info = bus_info[bus_info['Sub Name'].isin(sub_info['Sub Name'])]
			more_fake_pmu_bus_info = more_fake_pmu_bus_info[more_fake_pmu_bus_info['Nom kV'].isin(pmu_volt_lvls)]
			
			# Join info for PMUs assigned at generator substations and extra substations required to meet NUM_SUBS_WITH_PMU
			fake_pmu_bus_info = fake_pmu_bus_info.append(more_fake_pmu_bus_info).\
								 sort_values(['Sub Name', 'Nom kV'])
			
			# Merge all real or fake PMU data into one dataframe
			try:
				all_pmus = self.real_pmu_bus_info.append(fake_pmu_bus_info).sort_values(['Sub Name', 'Nom kV'])
			except AttributeError:
				# No known PMUs, so the required number of PMUs are assigned to substations
				all_pmus = fake_pmu_bus_info.copy()
				
			return all_pmus
		
	def getPmuMeasurementData(self, pmu_info):
		"""
		Filters out measurement data for just the buses where PMUs are located.

		Parameters
		----------
		pmu_info: 	Dataframe of PMU substation information, including bus name/num, sub name,
				  	area name, lat/long coord, and volt level

		Output
		------
		Dictionary of dataframes with PMU measurements for frequency, volt ang,
		volt mag, and current mag
		"""		
		# Get bus numbers where PMUs are assigned
		pmu_bus_nums = pmu_info['Bus Number'].tolist()
		pmu_bus_nums = [int(bus_num) for bus_num in pmu_bus_nums] # Changed 4/25 str --> int

		# Filter out measurement data for pmu locations
		valid_pmu_buses = [bus_num for bus_num in pmu_bus_nums if bus_num in self.bus_freq.columns.values]
		pmu_freq = self.bus_freq[valid_pmu_buses]
		pmu_vang = self.bus_vang[valid_pmu_buses]
		pmu_vmag = self.bus_vmag[valid_pmu_buses]
		pmu_cmag = self.filterBranchData(valid_pmu_buses)

		# Let user know if a generator is offline and consequently no PMU data are available at that bus
		invalid_pmu_buses = [bus_num for bus_num in pmu_bus_nums if bus_num not in self.bus_freq.columns.values]
		if invalid_pmu_buses:
			print('\nMeasurements at the following buses were not recorded due to a generator outage:\n', invalid_pmu_buses)
		
		# Save data
		self.savePmuData(pmu_freq, [filename for filename in self.file_list if 'freq' in filename][0])
		self.savePmuData(pmu_vang, [filename for filename in self.file_list if 'vang' in filename][0])
		self.savePmuData(pmu_vmag, [filename for filename in self.file_list if 'vmag' in filename][0])
		self.savePmuData(pmu_cmag, [filename for filename in self.file_list if 'cmag' in filename][0])

		return {'pmu_freq': pmu_freq, 'pmu_vang': pmu_vang, 'pmu_vmag': pmu_vmag, 'pmu_cmag': pmu_cmag}

	def filterBranchData(self, pmu_buses):
		"""
		Function to filter out the current measurement data for branches
		that terminate with valid PMUs given in pmu_bus_info.

		Parameters
		----------
		pmu_buses: A list of buses where a PMU has been assigned

		Output
		------
		Pandas dataframe of branch current data that has been filtered to only include
		measurements at buses where a PMU has been assigned
		"""
		# Initialize list to store the column names that represent bus where PMUs are located
		filtered_col_names = []

		# Loop through each column name in branch current measurement data
		for col_name in self.branch_cmag.columns:
			# Use regex to look for bus numbers in the column heading
			# First number is for the from bus, second number is for the to bus, 
			# third number is for the circuit number
			from_bus_num = [int(char) for char in col_name.split() if char.isdigit()][0]
			to_bus_num = [int(char) for char in col_name.split() if char.isdigit()][1]

			# If bus numbers are within the buses where PMUs are located, save that column name
			if from_bus_num in pmu_buses and to_bus_num in pmu_buses:
				filtered_col_names.append(col_name)

		return self.branch_cmag[filtered_col_names]

	def savePmuData(self, data, filePath):
		"""
		Save dataFrame to a csv file at the given dataPath and with a file name
		format of powerworldcasename_transientstabilityname_filename. If the file
		you are trying to write to is open in another program, an error is raised.
		
		Parameters
		----------
		data: Dataframe of data to be saved as csv
		filepath: File location where data will be saved as a csv
		"""
		# Specify slash that will separate directories (depends on operating system)
		slash = '/'
		if os.name == 'nt':
			# Windows operating system, use backslash to separate directories
			slash = "\\"

		# Split file path into pieces
		split_file_path = filePath.lower().split(slash)

		# Get index of raw directory (this is the directory files from PW are saved in)
		dir_index = split_file_path.index('raw')

		# If formatted data directory doesn't exist, create it
		directory = os.path.join(slash.join(split_file_path[:dir_index]), 'formatted')
		if not os.path.exists(directory):
			os.makedirs(directory)

		# Create file name for saving the data (include case, simulation, and measurement type names)
		file_type = split_file_path[-1].split('.')[-2].split('_')[-1]
		case_name = ''.join(self.case_name.lower().split('_'))
		data_type = ''.join(split_file_path[dir_index-1].split('_'))	# Simulation name or 'case_info'
		file_path = os.path.join(directory, '_'.join([case_name, data_type, 'pmu', file_type])) + '.csv'

		# Save data. If file trying to be saved is open, raise an error
		try:
			data.to_csv(file_path, index=True)
		except PermissionError:
			print("\nERROR: The file {} is open, and can't be saved. Close it, then run program again.\n".format(file_path))
			raise


if __name__ == '__main__':

	to_raw_dir = os.path.join('..', 'data', CASE_NAME, SIM_NAME, 'raw')
	fileList = [os.path.join(to_raw_dir, 'branch_cmag.csv'),
				os.path.join(to_raw_dir, 'bus_freq.csv'),
				os.path.join(to_raw_dir, 'bus_vang.csv'),
				os.path.join(to_raw_dir, 'bus_vmag.csv')]
			 
	all_data = CaseData(fileList).getData()
	pmu_data = PmuData(all_data, fileList).getAllPmuData()
