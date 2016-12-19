#!/usr/bin/python

"""Module: aliasip

This module provides utilities for adding IP address aliases on Linux
and configuration the alias in AWS if needed.

"""
import logging
import socket
import os
import sys

# Pass ImportError on boto3 for offline assets
try:
    import boto3
    from botocore.client import ClientError
except ImportError:
    boto3 = None
    ClientError = None
    pass

from bash import run_command
from bash import get_ip_addresses
from bash import service_network_restart
from bash import CommandError
from logify import Logify

from pycons3rt.awsapi.metadata import is_aws
from pycons3rt.awsapi.ec2util import EC2Util
from pycons3rt.awsapi.ec2util import EC2UtilError

__author__ = 'Joe Yennaco'


# Set up logger name for this module
mod_logger = Logify.get_name() + '.aliasip'


def validate_ip_address(ip_address):
    """Validate the ip_address

    :param ip_address: (str) IP address
    :return: (bool) True if the ip_address is valid
    """
    # Validate the IP address
    log = logging.getLogger(mod_logger + '.validate_ip_address')
    if not isinstance(ip_address, basestring):
        log.warn('ip_address argument is not a string')
        return False
    try:
        socket.inet_aton(ip_address)
    except socket.error as e:
        log.info('Not a valid IP address: {i}\n{e}'.format(i=ip_address, e=e))
        return False
    else:
        log.info('Validated IP address: %s', ip_address)
        return True


def alias_ip_address(ip_address, interface):
    """Adds an IP alias to a specific interface

    Adds an ip address as an alias to the specified interface on
    Linux systems.

    :param ip_address: (str) IP address to set as an alias
    :param interface: (str) The interface number to set
    :return: None
    """
    log = logging.getLogger(mod_logger + '.alias_ip_address')

    # Validate args
    if not isinstance(ip_address, basestring):
        msg = 'ip_address argument is not a string'
        log.error(msg)
        raise TypeError(msg)
    try:
        interface = int(interface)
    except ValueError as e:
        msg = 'interface argument is not an int\n{e}'.format(e=e)
        log.error(msg)
        raise ValueError(msg)

    # Validate the IP address
    if not validate_ip_address(ip_address):
        msg = 'Not a valid IP address: {i}'.format(i=ip_address)
        log.error(msg)
        raise ValueError(msg)

    # Add alias
    command = ['ifconfig', 'eth{nic}:0'.format(nic=interface), ip_address, 'up']
    try:
        result = run_command(command)
    except CommandError:
        raise
    log.info('Command produced output:\n{o}'.format(o=result['output']))

    if int(result['code']) != 0:
        msg = 'ifconfig up command produced exit code: {c}'.format(c=result['code'])
        log.error(msg)
        raise OSError(msg)

    # Create interface file from the existing file
    base_ifcfg = os.path.abspath(os.path.join(os.sep, 'etc', 'sysconfig', 'network-scripts', 'ifcfg-eth{i}'.format(
            i=interface)))
    alias_ifcfg = base_ifcfg + ':0'

    # Ensure the base config file exists
    if not os.path.isfile(base_ifcfg):
        msg = 'Required interface config file not found: {f}'.format(f=base_ifcfg)
        log.error(msg)
        raise OSError(msg)
    else:
        log.info('Found base interface config file: {f}'.format(f=base_ifcfg))

    # Delete the existing interface file if it exists
    if os.path.isfile(alias_ifcfg):
        log.info('Alias interface configuration file already exists, removing: {f}'.format(f=alias_ifcfg))
        try:
            os.remove(alias_ifcfg)
        except OSError:
            raise
    else:
        log.info('No existing alias interface configuration exists yet: {f}'.format(f=alias_ifcfg))

    # Create the interface file
    log.info('Gathering entries from file: {f}...'.format(f=base_ifcfg))
    ifcfg_entries = {}
    try:
        with open(base_ifcfg, 'r') as f:
            for line in f:
                if '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        parts[0] = parts[0].strip()
                        parts[1] = parts[1].translate(None, '"').strip()
                        ifcfg_entries[parts[0]] = parts[1]
    except(IOError, OSError) as e:
        msg = 'Unable to read file: {f}\n{e}'.format(f=base_ifcfg, e=e)
        log.error(msg)
        raise OSError(msg)

    # Defined the ifcfg file entries for the alias
    ifcfg_entries['IPADDR'] = ip_address
    ifcfg_entries['NETMASK'] = '255.255.255.0'
    ifcfg_entries['DEVICE'] = 'eth{i}:0'.format(i=interface)
    ifcfg_entries['NAME'] = 'eth{i}:0'.format(i=interface)

    log.info('Creating file: {f}'.format(f=alias_ifcfg))
    try:
        with open(alias_ifcfg, 'a') as f:
            for var, val in ifcfg_entries.iteritems():
                out_str = str(var) + '="' + str(val) + '"\n'
                log.info('Adding entry to %s: %s', alias_ifcfg, out_str)
                f.write(out_str)
    except(IOError, OSError) as e:
        msg = 'Unable to write to file: {f}\n{e}'.format(f=alias_ifcfg, e=e)
        log.error(msg)
        raise OSError(msg)
    log.info('Restarting networking to ensure the changes take effect...')
    try:
        service_network_restart()
    except CommandError:
        raise

    # Verify the alias was created
    log.info('Verifying the alias was successfully created...')
    command = ['/sbin/ifconfig']
    try:
        result = run_command(command)
    except CommandError:
        _, ex, trace = sys.exc_info()
        msg = 'Unable to run ifconfig to verify the IP alias was created\n{e}'.format(e=str(ex))
        log.error(msg)
        raise OSError, msg, trace
    ifconfig = result['output']

    if 'eth{i}:0'.format(i=interface) not in ifconfig:
        msg = 'The alias was not created: eth{i}:0'.format(i=interface)
        log.error(msg)
        raise OSError(msg)
    else:
        log.info('Alias created successfully!')

    log.info('Performing additional configuration for AWS...')
    if is_aws():
        log.info('Performing additional configuration for AWS...')
        try:
            ec2 = EC2Util()
            ec2.add_secondary_ip(ip_address, interface)
        except EC2UtilError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to instruct AWS to add a secondary IP address <{ip}> on interface <{i}>\n{e}'.format(
                ip=ip_address, i=interface, e=str(ex))
            log.error(msg)
            raise OSError, msg, trace
        else:
            log.info('AWS added the secondary IP address <{ip}> on interface <{i}>'.format(
                ip=ip_address, i=interface))
    else:
        log.info('This system is not on AWS, no additional configuration required')


def set_source_ip_for_interface(ip_address, device_num=0):
    """Configures the source IP address for a Linux interface

    :param ip_address: (str) IP address to configure as the source
    :param device_num: (int) Integer interface device number to configure
    :return: None
    :raises: TypeError, ValueError, OSError
    """
    log = logging.getLogger(mod_logger + '.alias_ip_address')
    if not isinstance(device_num, int) and not isinstance(device_num, basestring):
        msg = 'arg device_num should be an int, or string representation of an int'
        log.error(msg)
        raise TypeError(msg)
    if not isinstance(ip_address, basestring):
        msg = 'arg ip_address must be a string'
        log.error(msg)
        raise TypeError(msg)
    if not validate_ip_address(ip_address=ip_address):
        msg = 'The arg ip_address was found to be an invalid IP address.  Please pass a valid IP address'
        log.error(msg)
        raise ValueError(msg)

    # Build the command
    # iptables -t nat -I POSTROUTING -o eth0 -s ${RA_ORIGINAL_IP} -j SNAT --to-source
    device_num_str = str(device_num)

    command = ['iptables', '-t', 'nat', '-I', 'POSTROUTING', '-o', 'eth{d}'.format(d=device_num_str), '-s', ip_address,
               '-j', 'SNAT', '--to-source']
    log.info('Running command: {c}'.format(c=command))
    try:
        result = run_command(command, timeout_sec=20)
    except CommandError:
        _, ex, trace = sys.exc_info()
        msg = 'There was a problem running iptables command: {c}\n{e}'.format(c=' '.join(command), e=str(ex))
        log.error(msg)
        raise OSError, msg, trace

    if int(result['code']) != 0:
        msg = 'The iptables command produced an error with exit code: {c}, and output:\n{o}'.format(
            c=result['code'], o=result['output'])
        log.error(msg)
        raise OSError(msg)
    log.info('Successfully configured the source IP for eth{d} to be: {i}'.format(d=device_num_str, i=ip_address))


def main():
    """Sample usage for this python module

    This main method simply illustrates sample usage for this python
    module.

    :return: None
    """
    log = logging.getLogger(mod_logger + '.main')
    log.info('Main!')
    ips = get_ip_addresses()
    log.info('Found: %s', ips)


if __name__ == '__main__':
    main()
