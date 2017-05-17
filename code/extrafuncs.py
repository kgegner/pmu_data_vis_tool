"""
Script Name:
extrafuncs.py

Original Author: K. Gegner
Created On: 12/14/16
Modified By: K. Gegner
Modified On: 12/14/2016

Functionality:
- Function definitions that supplement the analytics tool, but are more general functions
"""

def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    http://stackoverflow.com/questions/38987/how-to-merge-two-python-dictionaries-in-a-single-expression
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result