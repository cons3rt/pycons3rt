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
from osutil import get_os
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
        self.scenario_role_names = []
        self.scenario_master = ''
        self.scenario_network_info = []
        self.deployment_id = None
        self.deployment_name = ''
        self.deployment_run_id = None
        self.deployment_run_name = ''
        self.virtualization_realm_type = ''

        # Determine cons3rt agent directories
        if get_os() == 'Linux':
            self.cons3rt_agent_home = os.path.join(os.path.sep, 'opt', 'cons3rt-agent')
        elif get_os() == 'Windows':
            self.cons3rt_agent_home = os.path.join('C:', os.path.sep, 'cons3rt-agent')
        else:
            self.cons3rt_agent_home = None
        if self.cons3rt_agent_home:
            self.cons3rt_agent_log_dir = os.path.join(self.cons3rt_agent_home, 'log')
            self.cons3rt_agent_run_dir = os.path.join(self.cons3rt_agent_home, 'run')
        else:
            self.cons3rt_agent_log_dir = None
            self.cons3rt_agent_run_dir = None

        # Set deployment home and read deployment properties
        try:
            self.set_deployment_home()
            self.read_deployment_properties()
        except DeploymentError:
            raise
        self.set_cons3rt_role_name()
        self.set_asset_dir()
        self.set_scenario_role_names()
        self.set_scenario_network_info()
        self.set_deployment_name()
        self.set_deployment_id()
        self.set_deployment_run_name()
        self.set_deployment_run_id()
        self.set_virtualization_realm_type()

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

        if self.cons3rt_agent_run_dir is None:
            msg = 'This is not Windows nor Linux, cannot determine DEPLOYMENT_HOME'
            log.error(msg)
            raise DeploymentError(msg)

        # Ensure the run directory can be found
        if not os.path.isdir(self.cons3rt_agent_run_dir):
            msg = 'Could not find the cons3rt run directory, DEPLOYMENT_HOME cannot be set'
            log.error(msg)
            raise DeploymentError(msg)

        run_dir_contents = os.listdir(self.cons3rt_agent_run_dir)
        results = []
        for item in run_dir_contents:
            if 'Deployment' in item:
                results.append(item)
        if len(results) != 1:
            msg = 'Could not find deployment home in the cons3rt run directory, deployment home cannot be set'
            log.error(msg)
            raise DeploymentError(msg)

        # Ensure the Deployment Home is a directory
        candidate_deployment_home = os.path.join(self.cons3rt_agent_run_dir, results[0])
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
        except (IOError, OSError):
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

        if not isinstance(regex, basestring):
            log.error('regex arg is not a string found type: {t}'.format(t=regex.__class__.__name__))
            return None

        log.debug('Looking up property based on regex: {r}'.format(r=regex))
        prop_list_matched = []
        for prop_name in self.properties.keys():
            match = re.search(regex, prop_name)
            if match:
                prop_list_matched.append(prop_name)
        if len(prop_list_matched) == 1:
            log.debug('Found matching property: {p}'.format(p=prop_list_matched[0]))
            return prop_list_matched[0]
        elif len(prop_list_matched) > 1:
            log.debug('Passed regex {r} matched more than 1 property, checking for an exact match...'.format(r=regex))
            for matched_prop in prop_list_matched:
                if matched_prop == regex:
                    log.debug('Found an exact match: {p}'.format(p=matched_prop))
                    return matched_prop
            log.debug('Exact match not found for regex {r}, returning None'.format(r=regex))
            return None
        else:
            log.debug('Passed regex did not match any deployment properties: {r}'.format(r=regex))
            return None

    def get_matching_property_names(self, regex):
        """Returns a list of property names matching the provided
        regular expression

        :param regex: Regular expression to search on
        :return: (list) of property names matching the regex
        """
        log = logging.getLogger(self.cls_logger + '.get_matching_property_names')
        prop_list_matched = []
        if not isinstance(regex, basestring):
            log.warn('regex arg is not a string, found type: {t}'.format(t=regex.__class__.__name__))
            return prop_list_matched
        log.debug('Finding properties matching regex: {r}'.format(r=regex))
        for prop_name in self.properties.keys():
            match = re.search(regex, prop_name)
            if match:
                prop_list_matched.append(prop_name)
        return prop_list_matched

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
            log.error('property_name arg is not a string, found type: {t}'.format(t=property_name.__class__.__name__))
            return None
        # Ensure a property with that name exists
        prop = self.get_property(property_name)
        if not prop:
            log.debug('Property name not found matching: {n}'.format(n=property_name))
            return None
        value = self.properties[prop]
        log.debug('Found value for property {n}: {v}'.format(n=property_name, v=value))
        return value

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

            if platform.system() == 'Linux':
                log.info('Attempting to determine CONS3RT_ROLE_NAME on Linux...')
                try:
                    self.determine_cons3rt_role_name_linux()
                except DeploymentError:
                    raise
            else:
                log.warn('Unable to determine CONS3RT_ROLE_NAME on this System')

        else:
            log.info('Found environment variable CONS3RT_ROLE_NAME: {r}'.format(r=self.cons3rt_role_name))
            return

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

    def set_scenario_role_names(self):
        """Populates the list of scenario role names in this deployment and
        populates the scenario_master with the master role

        Gets a list of deployment properties containing "isMaster" because
        there is exactly one per scenario host, containing the role name

        :return:
        """
        log = logging.getLogger(self.cls_logger + '.set_scenario_role_names')
        is_master_props = self.get_matching_property_names('isMaster')
        for is_master_prop in is_master_props:
            role_name = is_master_prop.split('.')[-1]
            log.info('Adding scenario host: {n}'.format(n=role_name))
            self.scenario_role_names.append(role_name)

            # Determine if this is the scenario master
            is_master = self.get_value(is_master_prop).lower().strip()
            if is_master == 'true':
                log.info('Found master scenario host: {r}'.format(r=role_name))
                self.scenario_master = role_name

    def set_scenario_network_info(self):
        """Populates a list of network info for each scenario host from
        deployment properties

        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.set_scenario_network_info')

        for scenario_host in self.scenario_role_names:
            scenario_host_network_info = {'scenario_role_name': scenario_host}
            log.debug('Looking up network info from deployment properties for scenario host: {s}'.format(
                s=scenario_host))
            network_name_props = self.get_matching_property_names(
                'cons3rt.fap.deployment.machine.*{r}.*networkName'.format(r=scenario_host)
            )
            log.debug('Found {n} network name props'.format(n=str(len(network_name_props))))

            network_info_list = []
            for network_name_prop in network_name_props:
                network_info = {}
                network_name = self.get_value(network_name_prop)
                if not network_name:
                    log.debug('Network name not found for prop: {n}'.format(n=network_name_prop))
                    continue
                log.debug('Adding info for network name: {n}'.format(n=network_name))
                network_info['network_name'] = network_name
                interface_name_prop = 'cons3rt.fap.deployment.machine.{r}.{n}.interfaceName'.format(
                    r=scenario_host, n=network_name)
                interface_name = self.get_value(interface_name_prop)
                if interface_name:
                    network_info['interface_name'] = interface_name
                external_ip_prop = 'cons3rt.fap.deployment.machine.{r}.{n}.externalIp'.format(
                    r=scenario_host, n=network_name)
                external_ip = self.get_value(external_ip_prop)
                if external_ip:
                    network_info['external_ip'] = external_ip
                internal_ip_prop = 'cons3rt.fap.deployment.machine.{r}.{n}.internalIp'.format(
                    r=scenario_host, n=network_name)
                internal_ip = self.get_value(internal_ip_prop)
                if internal_ip:
                    network_info['internal_ip'] = internal_ip
                is_cons3rt_connection_prop = 'cons3rt.fap.deployment.machine.{r}.{n}.isCons3rtConnection'.format(
                    r=scenario_host, n=network_name)
                is_cons3rt_connection = self.get_value(is_cons3rt_connection_prop)
                if is_cons3rt_connection:
                    if is_cons3rt_connection.lower().strip() == 'true':
                        network_info['is_cons3rt_connection'] = True
                    else:
                        network_info['is_cons3rt_connection'] = False
                mac_address_prop = 'cons3rt.fap.deployment.machine.{r}.{n}.mac'.format(r=scenario_host, n=network_name)
                mac_address = self.get_value(mac_address_prop)
                if mac_address:
                    # Trim the escape characters from the mac address
                    mac_address = mac_address.replace('\\', '')
                    network_info['mac_address'] = mac_address
                log.debug('Found network info: {n}'.format(n=str(network_info)))
                network_info_list.append(network_info)
            scenario_host_network_info['network_info'] = network_info_list
            self.scenario_network_info.append(scenario_host_network_info)

    def set_deployment_name(self):
        """Sets the deployment name from deployment properties

        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.set_deployment_name')
        self.deployment_name = self.get_value('cons3rt.deployment.name')
        log.info('Found deployment name: {n}'.format(n=self.deployment_name))

    def set_deployment_id(self):
        """Sets the deployment ID from deployment properties

        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.set_deployment_id')
        deployment_id_val = self.get_value('cons3rt.deployment.id')
        if not deployment_id_val:
            log.debug('Deployment ID not found in deployment properties')
            return
        try:
            deployment_id = int(deployment_id_val)
        except ValueError:
            log.debug('Deployment ID found was unable to convert to an int: {d}'.format(d=deployment_id_val))
            return
        self.deployment_id = deployment_id
        log.info('Found deployment ID: {i}'.format(i=str(self.deployment_id)))

    def set_deployment_run_name(self):
        """Sets the deployment run name from deployment properties

        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.set_deployment_run_name')
        self.deployment_run_name = self.get_value('cons3rt.deploymentRun.name')
        log.info('Found deployment run name: {n}'.format(n=self.deployment_run_name))

    def set_deployment_run_id(self):
        """Sets the deployment run ID from deployment properties

        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.set_deployment_run_id')
        deployment_run_id_val = self.get_value('cons3rt.deploymentRun.id')
        if not deployment_run_id_val:
            log.debug('Deployment run ID not found in deployment properties')
            return
        try:
            deployment_run_id = int(deployment_run_id_val)
        except ValueError:
            log.debug('Deployment run ID found was unable to convert to an int: {d}'.format(d=deployment_run_id_val))
            return
        self.deployment_run_id = deployment_run_id
        log.info('Found deployment run ID: {i}'.format(i=str(self.deployment_run_id)))

    def set_virtualization_realm_type(self):
        """Sets the virtualization realm type from deployment properties

        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.set_virtualization_realm_type')
        self.virtualization_realm_type = self.get_value('cons3rt.deploymentRun.virtRealm.type')
        log.info('Found virtualization realm type : {t}'.format(t=self.virtualization_realm_type))


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
