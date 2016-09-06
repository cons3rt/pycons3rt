#!/usr/bin/python

"""Module: deployment

This module provides a set of useful utilities for accessing CONS3RT
deployment related info. It is intended to be imported and used in
other python-based CONS3RT assets.

Classes:
    Deployment: Provides utility for accessing information in the
        deployment.properties file, including validation, getting
        specific properties, and getting the scenario role name.

    DeploymentError: Custom exception for raised when there is a
        problem obtaining the deployment properties file.
"""
import logging
import os
import sys
import traceback
import re
import platform

from logify import Logify
from bash import get_ip_addresses
from bash import CommandError

__author__ = 'Joe Yennaco'


# Set up logger name for this module
mod_logger = Logify.get_name() + '.deployment'


class DeploymentError(Exception):
    """Simple exception type for Deployment errors

    This class is an Exception type for handling errors gathering
    deployment info.
    """
    pass


class Deployment(object):
    """Utility for storing and access info from deployment.properties

    This class provides a set of useful utilities for accessing CONS3RT
    deployment related deployment information, such as deployment
    properties, deployment home, asset directory, the and the CONS3RT
    role name. If a Deployment object cannot be instantiated, a
    DeploymentError is raised. Sample usage is shown below in the main
    module method.

    Args: None

    Attributes:
        properties (dict): Key value pair for each deployment
            property.
        properties_file (str): Full system path to the deployment
            properties file.
        deployment_home (str): Deployment home system path
        cons3rt_role_name (str): Role name of this system in the
            context of the CONS3RT scenario
        asset_dir (dir): Asset directory system path
    """
    def __init__(self):
        self.cls_logger = mod_logger + '.Deployment'
        self.properties = {}
        self.properties_file = ''
        self.deployment_home = ''
        self.cons3rt_role_name = ''
        self.asset_dir = ''
        try:
            self.set_deployment_home()
            self.read_deployment_properties()
        except DeploymentError:
            raise
        self.set_cons3rt_role_name()
        self.set_asset_dir()

    def set_deployment_home(self):
        """Sets self.deployment_home

        This method finds and sets deployment home, primarily based on
        the DEPLOYMENT_HOME environment variable. If not set, this
        method will attempt to determine deployment home.

        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.set_deployment_home')
        try:
            self.deployment_home = os.environ['DEPLOYMENT_HOME']
        except KeyError:
            log.warn('DEPLOYMENT_HOME environment variable is not set, attempting to set it...')
        else:
            log.info('Found DEPLOYMENT_HOME environment variable set to: {d}'.format(d=self.deployment_home))
            return

        log.info('Attempting to determine deployment home...')
        if platform.system() == 'Linux':
            cons3rt_run_dir = os.path.join(os.path.sep, 'opt', 'cons3rt-agent', 'run')
            log.debug('This is Linux, using cons3rt agent run directory: {d}'.format(d=cons3rt_run_dir))
        elif platform.system() == 'Windows':
            cons3rt_run_dir = os.path.join('C:', 'cons3rt-agent', 'run')
            log.debug('This is Windows, using cons3rt agent run directory: {d}'.format(d=cons3rt_run_dir))
        else:
            msg = 'This is not Windows nor Linux, cannot determine DEPLOYMENT_HOME'
            log.error(msg)
            raise DeploymentError(msg)

        # Ensure the run directory can be found
        if not os.path.isdir(cons3rt_run_dir):
            msg = 'Could not find the cons3rt run directory, DEPLOYMENT_HOME cannot be set'
            log.error(msg)
            raise DeploymentError(msg)

        run_dir_contents = os.listdir(cons3rt_run_dir)
        results = []
        for item in run_dir_contents:
            if 'Deployment' in item:
                results.append(item)
        if len(results) != 1:
            msg = 'Could not find deployment home in the cons3rt run directory, deployment home cannot be set'
            log.error(msg)
            raise DeploymentError(msg)

        # Ensure the Deployment Home is a directory
        candidate_deployment_home = os.path.join(cons3rt_run_dir, results[0])
        if not os.path.isdir(candidate_deployment_home):
            msg = 'The candidate deployment home is not a valid directory: {d}'.format(d=candidate_deployment_home)
            log.error(msg)
            raise DeploymentError(msg)

        # Ensure the deployment properties file can be found
        self.deployment_home = candidate_deployment_home
        os.environ['DEPLOYMENT_HOME'] = self.deployment_home
        log.info('Set DEPLOYMENT_HOME in the environment to: {d}'.format(d=self.deployment_home))

    def read_deployment_properties(self):
        """Reads the deployment properties file

        This method reads the deployment properties file into the
        "properties" dictionary object.

        :return: None
        :raises: DeploymentError
        """
        log = logging.getLogger(self.cls_logger + '.read_deployment_properties')

        # Ensure deployment properties file exists
        self.properties_file = os.path.join(self.deployment_home, 'deployment.properties')
        if not os.path.isfile(self.properties_file):
            msg = 'Deployment properties file not found: {f}'.format(f=self.properties_file)
            log.error(msg)
            raise DeploymentError(msg)
        log.info('Found deployment properties file: {f}'.format(f=self.properties_file))

        log.info('Reading deployment properties...')
        try:
            f = open(self.properties_file)
        except IOError:
            _, ex, trace = sys.exc_info()
            msg = 'Could not open file {file} to read property: {prop}'.format(
                file=self.properties_file,
                prop=property)
            log.error(msg)
            raise DeploymentError, msg, trace

        for line in f:
            log.debug('Processing deployment properties file line: {l}'.format(l=line))
            if not isinstance(line, basestring):
                log.debug('Skipping line that is not a string: {l}'.format(l=line))
                continue
            elif line.startswith('#'):
                log.debug('Skipping line that is a comment: {l}'.format(l=line))
                continue
            elif '=' in line:
                split_line = line.strip().split('=', 1)
                if len(split_line) == 2:
                    prop_name = split_line[0].strip()
                    prop_value = split_line[1].strip()
                    if prop_name is None or not prop_name or prop_value is None or not prop_value:
                        log.debug('Property name <{n}> or value <v> is none or blank, not including it'.format(
                                n=prop_name, v=prop_value))
                    else:
                        log.debug('Adding property {n} with value {v}...'.format(n=prop_name, v=prop_value))
                        self.properties[prop_name] = prop_value
                else:
                    log.debug('Skipping line that did not split into 2 part on an equal sign...')
        log.info('Successfully read in deployment properties')

    def get_property(self, regex):
        """Gets the name of a specific property

        This public method is passed a regular expression and
        returns the matching property name. If either the property
        is not found or if the passed string matches more than one
        property, this function will return None.

        :param regex: Regular expression to search on
        :return: (str) Property name matching the passed regex or None.
        """
        log = logging.getLogger(self.cls_logger + '.get_property')
        log.info('Looking up property based on regex: %s', regex)
        if not isinstance(regex, basestring):
            log.error('regex arg is not a string')
            return None
        prop_list = self.properties.keys()
        prop_list_matched = []
        for prop_name in prop_list:
            match = re.search(regex, prop_name)
            if match:
                prop_list_matched.append(prop_name)
        if len(prop_list_matched) == 1:
            log.info('Found property: %s', prop_list_matched[0])
            return prop_list_matched[0]
        elif len(prop_list_matched) > 1:
            log.info('Passed regex {r} matched more than 1 property, checking for an exact match...'.format(r=regex))
            for matched_prop in prop_list_matched:
                if matched_prop == regex:
                    log.info('Found an exact match: {p}'.format(p=matched_prop))
                    return matched_prop
            log.info('Exact match not found for regex {r}, returning None'.format(r=regex))
            return None
        else:
            log.info('Passed regex did not match any property: %s', regex)
            return None

    def get_value(self, property_name):
        """Returns the value associated to the passed property

        This public method is passed a specific property as a string
        and returns the value of that property. If the property is not
        found, None will be returned.

        :param property_name (str) The name of the property
        :return: (str) value for the passed property, or None.
        """
        log = logging.getLogger(self.cls_logger + '.get_value')
        if not isinstance(property_name, basestring):
            log.error('_prop arg is not a string')
            return None
        prop = self.get_property(property_name)
        if prop:
            log.info('Found value: %s', self.properties[prop])
            return self.properties[prop]
        else:
            log.info('Did not find a value for property: {p}'.format(p=property_name))
            return None

    def set_cons3rt_role_name(self):
        """Set the cons3rt_role_name member for this system

        :return: None
        :raises: DeploymentError
        """
        log = logging.getLogger(self.cls_logger + '.set_cons3rt_role_name')
        try:
            self.cons3rt_role_name = os.environ['CONS3RT_ROLE_NAME']
        except KeyError:
            log.warn('CONS3RT_ROLE_NAME is not set, attempting to determine it from deployment properties...')
        else:
            log.info('Found environment variable CONS3RT_ROLE_NAME: {r}'.format(r=self.cons3rt_role_name))
            return

        if platform.system() == 'Linux':
            log.info('Attempting to determine CONS3RT_ROLE_NAME on Linux...')
            try:
                self.determine_cons3rt_role_name_linux()
            except DeploymentError:
                raise
        else:
            log.warn('Unable to determine CONS3RT_ROLE_NAME on this System')

    def determine_cons3rt_role_name_linux(self):
        """Determines the CONS3RT_ROLE_NAME for this Linux system, and
        Set the cons3rt_role_name member for this system

        This method determines the CONS3RT_ROLE_NAME for this system
        in the deployment by first checking for the environment
        variable, if not set, determining the value from the
        deployment properties.

        :return: None
        :raises: DeploymentError
        """
        log = logging.getLogger(self.cls_logger + '.determine_cons3rt_role_name_linux')

        # Determine IP addresses for this system
        log.info('Determining the IPv4 addresses for this system...')
        try:
            ip_addresses = get_ip_addresses()
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to get the IP address of this system, thus cannot determine the ' \
                  'CONS3RT_ROLE_NAME\n{e}'.format(e=str(ex))
            log.error(msg)
            raise DeploymentError, msg, trace
        else:
            log.info('Found IP addresses: {a}'.format(a=ip_addresses))

        log.info('Trying to determine IP address for eth0...')
        try:
            ip_address = ip_addresses['eth0']
        except KeyError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to determine the IP address for eth0. Found the ' \
                  'following IP addresses: {i}\n{e}'.format(i=ip_addresses,
                                                            e=str(ex))
            log.error(msg)
            raise DeploymentError, msg, trace
        else:
            log.info('Found IP address for eth0: {i}'.format(i=ip_address))

        pattern = '^cons3rt\.fap\.deployment\.machine.*0.internalIp=' + ip_address + '$'
        try:
            f = open(self.properties_file)
        except IOError:
            _, ex, trace = sys.exc_info()
            msg = 'Could not open file {f}'.format(f=self.properties_file)
            log.error(msg)
            raise DeploymentError, msg, trace
        prop_list_matched = []
        log.debug('Searching for deployment properties matching pattern: {p}'.format(p=pattern))
        for line in f:
            log.debug('Processing deployment properties file line: {l}'.format(l=line))
            if line.startswith('#'):
                continue
            elif '=' in line:
                match = re.search(pattern, line)
                if match:
                    log.debug('Found matching prop: {l}'.format(l=line))
                    prop_list_matched.append(line)
        log.debug('Number of matching properties found: {n}'.format(n=len(prop_list_matched)))
        if len(prop_list_matched) == 1:
            prop_parts = prop_list_matched[0].split('.')
            if len(prop_parts) > 5:
                self.cons3rt_role_name = prop_parts[4]
                log.info('Found CONS3RT_ROLE_NAME from deployment properties: {c}'.format(c=self.cons3rt_role_name))
                log.info('Adding CONS3RT_ROLE_NAME to the current environment...')
                os.environ['CONS3RT_ROLE_NAME'] = self.cons3rt_role_name
                return
            else:
                log.error('Property found was not formatted as expected: %s',
                          prop_parts)
        else:
            log.error('Did not find a unique matching deployment property')
        msg = 'Could not determine CONS3RT_ROLE_NAME from deployment properties'
        log.error(msg)
        raise DeploymentError(msg)

    def set_asset_dir(self):
        """Returns the ASSET_DIR environment variable

        This method gets the ASSET_DIR environment variable for the
        current asset install. It returns either the string value if
        set or None if it is not set.

        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.get_asset_dir')
        try:
            self.asset_dir = os.environ['ASSET_DIR']
        except KeyError:
            log.warn('Environment variable ASSET_DIR is not set!')
        else:
            log.info('Found environment variable ASSET_DIR: {a}'.format(a=self.asset_dir))


def main():
    """Sample usage for this python module

    This main method simply illustrates sample usage for this python
    module.

    :return: None
    """
    log = logging.getLogger(mod_logger + '.main')
    try:
        log.info('Testing the Deployment class...')
        deployment = Deployment()
    except DeploymentError:
        log.error('Unable to get deployment info')
        traceback.print_exc()
        return

    log.debug('This is DEBUG')
    log.info('This is INFO')
    log.warning('This is a WARNING')
    log.error('This is an ERROR')
    log.info('CONS3RT_ROLE_NAME: %s', deployment.cons3rt_role_name)
    log.info('DEPLOYMENT_HOME: %s', deployment.deployment_home)
    log.info('ASSET_DIR: %s', deployment.asset_dir)
    user = deployment.get_value('cons3rt.user')
    if user:
        log.info('Found user: %s', user)
    else:
        log.warn('Did not find a user :(')
    deployment_id = deployment.get_value('deployment.id')
    if deployment_id:
        log.info('Found deployment id: %s', deployment_id)
    else:
        log.warn('Did not find deployment id :(')


if __name__ == '__main__':
    main()
