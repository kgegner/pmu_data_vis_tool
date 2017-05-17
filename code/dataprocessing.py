"""
Script Name:
dataprocessing.py

Original Author: K. Gegner
Created On: 8/22/16
Modified By: K. Gegner
Modified On: 5/16/2017

Functionality:
- Home screen for data analytics tool
- Choose between reading csv file(s) or streaming data

References:
- https://gist.github.com/tshirtman/5000276 (data between screens)
"""

# Standard python modules
import os
import re

# Kivy modules
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import DictProperty, BooleanProperty, ObjectProperty, StringProperty

# Data processing application modules
from importing import CaseData, PmuData
from userdef import *
from extrafuncs import *


class TextPopup(Popup):
    """ 
    Class definition for content to go in pop up windows.
    Content includes text and a button.
    """		
        
    def __init__(self, popup_title, popup_text, button_text, **kwargs):
        super(TextPopup, self).__init__(**kwargs)
        self.title = popup_title
        self.label.text = popup_text
        self.btn.text = button_text


class HomeScreen(Screen):
    """
    Creates a screen with a button prompting the user to initiate 
    the data importing and formatting process.
    """
    pass


class FileSelectScreen(Screen):
    """
    Creates a screen that allows a user to select electric grid 
    simulation data using folder/file icons.
    """
    # Initialize object to store the formatted simulation and case data
    data = ObjectProperty(None)

    def is_dir(self, directory, filename):
        """
        Function checks if filename is a directory.
        If so, returns True. If not, returns False.
        """
        return os.path.isdir(filename)
    
    def load(self, path, files):
        """
        Function to actually load the data files for the user selected folder.
        """
        # Save the file path for data files selected by the user
        data_directory = files[0]
        
        # Specify slash that will separate directories (depends on operating system)
        slash = '/'
        if os.name == 'nt':
    	    # Windows operating system, use backslash to separate directories
    	        slash = "\\"
        
        # If the user selects the case_info folder launch popup to warn them
        if 'case_info' in data_directory:
            line1 = 'You cannot select the folder case_info.\n\n'
            line2 = 'Try loading the data again, but select a folder with simulation data, not case_info.'
            popup = TextPopup('Bad Folder Selection', line1+line2, 'OK')
            popup.open()
            self.data = {}
        
        # The user selected a valid folder with simulation data, so import the data
        else:
            # Reformat the data directory path if the user selects too far down the folder hierarchy
            if 'raw' in data_directory or 'formatted' in data_directory:
                data_dir_split = data_directory.split(slash)
                data_directory = os.path.join(*data_dir_split[:-1])
            
            # Get files contained in the data_directory
            files = os.listdir(os.path.join(data_directory, 'raw'))
            
            # Initialize lists to store valid file names and their endings
            file_list = []
            file_ends = []

            # Loop through files and save only the valid filenames to the filelist
            for file_name in files:
                if file_name in MEASUREMENT_FILES:
                    file_ends.append(file_name)
                    file_list.append(os.path.join(data_directory, 'raw', file_name))

            # Check that all necessary files are included
            missing_files = [name for name in MEASUREMENT_FILES if name not in file_ends]
            if not missing_files:
                # Read in data from each of the files in file_list
                case_data = CaseData(file_list).getData()
                pmu_data = PmuData(case_data, file_list).getAllPmuData()
                self.data = merge_dicts(case_data, pmu_data)
                
                # Print case name and simulation name to the console, so user can copy 
                # into the userdef.py file
                self.printPathInfo(data_directory)
            else:
                # Files were missing so no data was read in, thus return just an empty dictionary
                self.data = {}
                
                # Create error message for files missing from MEASUREMENT_FILES, to be displayed in a popup
                incomplete_dir = os.path.join(data_directory, 'raw')
                line1 = 'The following file(s) are missing:\n{}'.format(missing_files)
                line2 = '\n\nAdd the missing file(s) to the directory below, and try re-loading files.\n{}'.format(incomplete_dir)
                popup = TextPopup('Missing Files', line1+line2, 'OK')
                popup.open()

        return self.data
    
    def printPathInfo(self, file_path):
        """
        Print case and simulation name, so user can copy and paste
        them into the userdef.py file, which is then read automatically
        by the display1.py and display2.py scripts.
        """
        # Specify slash that will separate directories (depends on operating system)
        slash = '/'
        if os.name == 'nt':
    	    # Windows operating system, use backslash to separate directories
    	    slash = "\\"
        
        # Split data path into parts
        data_path_parts = file_path.split(slash)
        
        # Get power system model and simulation names
        idx = data_path_parts.index('data')
        case_name = data_path_parts[idx+1]
        sim_name = data_path_parts[idx+2]
        
        # Print case name and simulation name to console
        print('\n\nCopy the variable definitions below into the userdef.py file.')
        print('-'*65)
        print("CASE_NAME = '{}'".format(case_name))
        print("SIM_NAME = '{}'\n\n".format(sim_name))


class ScreenManagement(ScreenManager):
    """
    Create a structure to host multiple screens and manages
    transitions between them.
    """
    # Dictionary to store all case, measurement, and pmu data
    all_data = DictProperty()

    def __init__(self, **kwargs):
        super(ScreenManagement, self).__init__(**kwargs)


class DataProcessingApp(App):
    """
    Application to allow a user to select data to be imported and formated.
    """
    def build(self):
        return ScreenManagement()


if __name__ == "__main__":
    DataProcessingApp().run()
else:
    Builder.load_file('dataprocessing.kv')
