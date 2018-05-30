#!/usr/bin/python

"""Module: aliasip

This module provides utilities for adding IP address aliases on Linux
and configuration the alias in AWS if needed.

"""
import logging
import socket
import os
import sys
import shutil
from datetime import datetime

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


class NetworkRestartError(Exception):
    """Error executing a network restart
    """
    pass


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

    # Ensure there are 3 dots
    num_dots = 0
    for c in ip_address:
        if c == '.':
            num_dots += 1
    if num_dots != 3:
        log.info('Not a valid IP address: {i}'.format(i=ip_address))
        return False

    # Use the socket module to test
    try:
        socket.inet_aton(ip_address)
    except socket.error as e:
        log.info('Not a valid IP address: {i}\n{e}'.format(i=ip_address, e=e))
        return False
    else:
        log.info('Validated IP address: %s', ip_address)
        return True


def ip_addr():
    """Uses the ip addr command to enumerate IP addresses by device

    :return: (dict) Containing device: ip_address
    """
    log = logging.getLogger(mod_logger + '.ip_addr')
    log.debug('Running the ip addr command...')
    ip_addr_output = {}

    command = ['ip', 'addr']
    try:
        ip_addr_result = run_command(command, timeout_sec=20)
    except CommandError:
        _, ex, trace = sys.exc_info()
        msg = 'There was a problem running command: {c}'.format(c=' '.join(command))
        raise CommandError, msg, trace

    ip_addr_lines = ip_addr_result['output'].split('\n')

    for line in ip_addr_lines:
        line = line.strip()
        if line.startswith('inet6'):
            continue
        elif line.startswith('inet'):
            parts = line.split()
            try:
                ip_address = parts[1].strip().split('/')[0]
            except KeyError:
                continue
            else:
                if not validate_ip_address(ip_address):
                    continue
                else:
                    for part in parts:
                        part = part.strip()
                        if part.strip().startswith('eth') or part.strip().startswith('eno') or \
                                part.strip().startswith('ens'):
                            device = part
                            ip_addr_output[device] = ip_address
    return ip_addr_output


def alias_ip_address(ip_address, interface, aws=False):
    """Adds an IP alias to a specific interface

    Adds an ip address as an alias to the specified interface on
    Linux systems.

    :param ip_address: (str) IP address to set as an alias
    :param interface: (str) The interface number or full device name, if
        an int is provided assumes the device name is eth<i>
    :param aws (bool) True to perform additional AWS config
    :return: None
    """
    log = logging.getLogger(mod_logger + '.alias_ip_address')

    # Validate args
    if not isinstance(ip_address, basestring):
        msg = 'ip_address argument is not a string'
        log.error(msg)
        raise TypeError(msg)

    # Validate the IP address
    if not validate_ip_address(ip_address):
        msg = 'The provided IP address arg is invalid: {i}'.format(i=ip_address)
        log.error(msg)
        raise ValueError(msg)

    # Determine if the interface provided is a full device name
    try:
        int(interface)
    except ValueError:
        if isinstance(interface, basestring):
            device_name = str(interface)
            log.info('Full device name provided, will attempt to alias: {d}'.format(d=device_name))
        else:
            raise TypeError('Provided interface arg must be an int or str')
    else:
        device_name = 'eth{i}'.format(i=interface)
        log.info('Integer provided as interface, using device name: {d}'.format(d=device_name))

    # Add alias
    command = ['ifconfig', '{d}:0'.format(d=device_name), ip_address, 'up']
    log.info('Running command to bring up the alias: {c}'.format(c=' '.join(command)))
    try:
        result = run_command(command)
    except CommandError:
        _, ex, trace = sys.exc_info()
        log.warn('CommandError: There was a problem running command: {c}\n{e}'.format(
            c=' '.join(command), e=str(ex)))
    else:
        log.info('Command produced output:\n{o}'.format(o=result['output']))
        if int(result['code']) != 0:
            log.warn('ifconfig up command produced exit code: {c} and output:\n{o}'.format(
                c=result['code'], o=result['output']))
        else:
            log.info('ifconfig up exited successfully')

    # Create interface file from the existing file
    base_ifcfg = os.path.abspath(os.path.join(os.sep, 'etc', 'sysconfig', 'network-scripts', 'ifcfg-{d}'.format(
            d=device_name)))
    alias_ifcfg = base_ifcfg + ':0'
    log.info('Creating interface config file: {f}'.format(f=alias_ifcfg))

    # Ensure the base config file exists
    if not os.path.isfile(base_ifcfg):
        raise OSError('Required interface config file not found: {f}'.format(f=base_ifcfg))
    else:
        log.info('Found base interface config file: {f}'.format(f=base_ifcfg))

    # Delete the existing interface file if it exists
    if os.path.isfile(alias_ifcfg):
        log.info('Alias interface configuration file already exists, removing: {f}'.format(f=alias_ifcfg))
        try:
            os.remove(alias_ifcfg)
        except OSError:
            _, ex, trace = sys.exc_info()
            msg = 'OSError: There was a problem removing existing alias config file: {f}\n{e}'.format(
                f=alias_ifcfg, e=str(ex))
            raise OSError, msg, trace
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
    except(IOError, OSError):
        _, ex, trace = sys.exc_info()
        msg = 'Unable to read file: {f}\n{e}'.format(f=base_ifcfg, e=str(ex))
        raise OSError, msg, trace

    # Defined the ifcfg file entries for the alias
    ifcfg_entries['IPADDR'] = ip_address
    ifcfg_entries['NETMASK'] = '255.255.255.0'
    ifcfg_entries['DEVICE'] = '{d}:0'.format(d=device_name)
    ifcfg_entries['NAME'] = '{d}:0'.format(d=device_name)

    log.info('Creating file: {f}'.format(f=alias_ifcfg))
    try:
        with open(alias_ifcfg, 'a') as f:
            for var, val in ifcfg_entries.iteritems():
                out_str = str(var) + '="' + str(val) + '"\n'
                log.info('Adding entry to %s: %s', alias_ifcfg, out_str)
                f.write(out_str)
    except(IOError, OSError):
        _, ex, trace = sys.exc_info()
        msg = 'Unable to write to file: {f}\n{e}'.format(f=alias_ifcfg, e=str(ex))
        raise OSError, msg, trace

    # Performing additional configuration for AWS
    if aws:
        log.info('Checking if this host is actually on AWS...')
        if is_aws():
            log.info('Performing additional configuration for AWS...')
            try:
                ec2 = EC2Util()
                ec2.add_secondary_ip(ip_address, interface)
            except EC2UtilError:
                _, ex, trace = sys.exc_info()
                msg = 'Unable to instruct AWS to add a secondary IP address <{ip}> on interface <{d}>\n{e}'.format(
                    ip=ip_address, d=device_name, e=str(ex))
                raise OSError, msg, trace
            else:
                log.info('AWS added the secondary IP address <{ip}> on interface <{d}>'.format(
                    ip=ip_address, d=device_name))
        else:
            log.warn('This system is not on AWS, not performing additional configuration')

    log.info('Restarting networking to ensure the changes take effect...')
    try:
        service_network_restart()
    except CommandError:
        _, ex, trace = sys.exc_info()
        msg = 'CommandError: There was a problem restarting network services\n{e}'.format(e=str(ex))
        raise NetworkRestartError, msg, trace

    # Verify the alias was created
    log.info('Verifying the alias was successfully created...')
    command = ['/sbin/ifconfig']
    try:
        result = run_command(command)
    except CommandError:
        _, ex, trace = sys.exc_info()
        log.warn('CommandError: Unable to run ifconfig to verify the IP alias was created\n{e}'.format(e=str(ex)))
        return

    # Check for the alias
    if '{d}:0'.format(d=device_name) not in result['output']:
        log.warn('The alias was not created yet, system reboot may be required: {d}:0'.format(d=device_name))
    else:
        log.info('Alias created successfully!')


def set_source_ip_for_interface(source_ip_address, desired_source_ip_address, device_num=0):
    """Configures the source IP address for a Linux interface

    :param source_ip_address: (str) Source IP address to change
    :param desired_source_ip_address: (str) IP address to configure as the source in outgoing packets
    :param device_num: (int) Integer interface device number to configure
    :return: None
    :raises: TypeError, ValueError, OSError
    """
    log = logging.getLogger(mod_logger + '.set_source_ip_for_interface')
    if not isinstance(source_ip_address, basestring):
        msg = 'arg source_ip_address must be a string'
        log.error(msg)
        raise TypeError(msg)
    if not isinstance(desired_source_ip_address, basestring):
        msg = 'arg desired_source_ip_address must be a string'
        log.error(msg)
        raise TypeError(msg)
    if not validate_ip_address(ip_address=source_ip_address):
        msg = 'The arg source_ip_address was found to be an invalid IP address.  Please pass a valid IP address'
        log.error(msg)
        raise ValueError(msg)
    if not validate_ip_address(ip_address=desired_source_ip_address):
        msg = 'The arg desired_source_ip_address was found to be an invalid IP address.  Please pass a valid IP address'
        log.error(msg)
        raise ValueError(msg)

    # Determine the device name based on the device_num
    log.debug('Attempting to determine the device name based on the device_num arg...')
    try:
        int(device_num)
    except ValueError:
        if isinstance(device_num, basestring):
            device_name = device_num
            log.info('Provided device_num is not an int, assuming it is the full device name: {d}'.format(
                d=device_name))
        else:
            raise TypeError('device_num arg must be a string or int')
    else:
        device_name = 'eth{n}'.format(n=str(device_num))
        log.info('Provided device_num is an int, assuming device name is: {d}'.format(d=device_name))

    # Build the command
    # iptables -t nat -I POSTROUTING -o eth0 -s ${RA_ORIGINAL_IP} -j SNAT --to-source

    command = ['iptables', '-t', 'nat', '-I', 'POSTROUTING', '-o', device_name, '-s',
               source_ip_address, '-j', 'SNAT', '--to-source', desired_source_ip_address]
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
    log.info('Successfully configured the source IP for {d} to be: {i}'.format(
        d=device_name, i=desired_source_ip_address))


def save_iptables(rules_file='/etc/sysconfig/iptables'):
    """Saves iptables rules to the provided rules file

    :return: None
    :raises OSError
    """
    log = logging.getLogger(mod_logger + '.set_source_ip_for_interface')

    # Run iptables-save to get the output
    command = ['iptables-save']
    log.debug('Running command: iptables-save')
    try:
        iptables_out = run_command(command, timeout_sec=20)
    except CommandError:
        _, ex, trace = sys.exc_info()
        msg = 'There was a problem running iptables command: {c}\n{e}'.format(c=' '.join(command), e=str(ex))
        raise OSError, msg, trace

    # Error if iptables-save did not exit clean
    if int(iptables_out['code']) != 0:
        raise OSError('Command [{g}] exited with code [{c}] and output:\n{o}'.format(
            g=' '.join(command), c=iptables_out['code'], o=iptables_out['output']))

    # Back up the existing rules file if it exists
    if os.path.isfile(rules_file):
        time_now = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_file = '{f}.{d}'.format(f=rules_file, d=time_now)
        log.debug('Creating backup file: {f}'.format(f=backup_file))
        shutil.copy2(rules_file, backup_file)

    # Save the output to the rules file
    log.debug('Creating file: {f}'.format(f=rules_file))
    with open(rules_file, 'w') as f:
        f.write(iptables_out['output'])


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
