#!/usr/bin/python

"""Module: awslibs

This module provides a set of supporting classes and methods
as libraries used by various homer modules.
"""
from pycons3rt.logify import Logify

__author__ = 'Joe Yennaco'


# Set up logger name for this module
mod_logger = Logify.get_name() + '.awsapi.awslibs'


class AWSAPIError(Exception):
    """Simple exception type for AWS API errors
    """
    pass
