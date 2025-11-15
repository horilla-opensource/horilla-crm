"""
JavaScript Registry Module

This module provides functionality to dynamically register JavaScript files
from different Django apps into a central registry. The registered JS files
can be loaded automatically in the base template without modifying core files.
"""

# Global list to store registered JavaScript file paths
REGISTERED_JS_FILES = []


def register_js(static_paths):
    """
    Register one or multiple JavaScript files relative to the Django static directory.

    Accepts:
        - Single string: 'assets/js/file.js'
        - List of strings: ['assets/js/file1.js', 'assets/js/file2.js']

    Ensures no duplicates are added.
    """

    # If a single string is passed, convert to list
    if isinstance(static_paths, str):
        static_paths = [static_paths]

    # Ensure it's now a list
    if isinstance(static_paths, (list, tuple)):
        for static_path in static_paths:
            if static_path not in REGISTERED_JS_FILES:
                REGISTERED_JS_FILES.append(static_path)


def get_registered_js():
    """
    Retrieve all registered JavaScript file paths.

    Returns:
        list: A list of strings representing the registered JavaScript files.
    """
    return REGISTERED_JS_FILES
