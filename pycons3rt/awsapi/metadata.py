#!/usr/bin/python

"""Module: metadata

This module provides utilities for interacting with the AWS
meta data service.

"""
import logging
import urllib
import sys

import netifaces

# Pass ImportError on boto3 for offline assets
try:
    import boto3
    from botocore.client import ClientError
except ImportError:
    boto3 = None
    ClientError = None
    pass

from pycons3rt.logify import Logify


__author__ = 'Joe Yennaco'


# Set up logger name for this module
mod_logger = Logify.get_name() + '.awsapi.metadata'

# AWS Meta Data Service URL
metadata_url = 'http://169.254.169.254/latest/meta-data/'


class AWSMetaDataError(Exception):
    """Simple exception type for AWS meta data service errors
    """
    pass


def is_aws():
    """Determines if this system is on AWS

    :return: bool True if this system is running on AWS
    """
    log = logging.getLogger(mod_logger + '.is_aws')
    log.info('Querying AWS meta data URL: {u}'.format(u=metadata_url))

    # Query the AWS meta data URL
    try:
        response = urllib.urlopen(metadata_url)
    except(IOError, OSError) as ex:
        log.info('Unable to query the AWS meta data URL, this system is NOT running on AWS\n{e}'.format(e=str(ex)))
        return False

    # Check the code
    if response.getcode() == 200:
        log.info('This system is running on AWS')
        return True
    else:
        log.info('This system is NOT running on AWS')
        return False


def get_instance_id():
    """Gets the instance ID of this EC2 instance

    :return: String instance ID or None
    """
    log = logging.getLogger(mod_logger + '.get_instance_id')

    # Exit if not running on AWS
    if not is_aws():
        log.info('This machine is not running in AWS, exiting...')
        return

    instance_id_url = metadata_url + 'instance-id'
    try:
        response = urllib.urlopen(instance_id_url)
    except(IOError, OSError) as ex:
        msg = 'Unable to query URL to get instance ID: {u}\n{e}'. \
            format(u=instance_id_url, e=ex)
        log.error(msg)
        return

    # Check the code
    if response.getcode() != 200:
        msg = 'There was a problem querying url: {u}, returned code: {c}, unable to get the instance-id'.format(
                u=instance_id_url, c=response.getcode())
        log.error(msg)
        return
    instance_id = response.read()
    return instance_id


def get_vpc_id_from_mac_address():
    """Gets the VPC ID for this EC2 instance

    :return: String instance ID or None
    """
    log = logging.getLogger(mod_logger + '.get_vpc_id')

    # Exit if not running on AWS
    if not is_aws():
        log.info('This machine is not running in AWS, exiting...')
        return

    # Get the primary interface MAC address to query the meta data service
    log.debug('Attempting to determine the primary interface MAC address...')
    try:
        mac_address = get_primary_mac_address()
    except AWSMetaDataError:
        _, ex, trace = sys.exc_info()
        msg = '{n}: Unable to determine the mac address, cannot determine VPC ID:\n{e}'.format(
            n=ex.__class__.__name__, e=str(ex))
        log.error(msg)
        return

    vpc_id_url = metadata_url + 'network/interfaces/macs/' + mac_address + '/vpc-id'
    try:
        response = urllib.urlopen(vpc_id_url)
    except(IOError, OSError) as ex:
        msg = 'Unable to query URL to get VPC ID: {u}\n{e}'.format(u=vpc_id_url, e=ex)
        log.error(msg)
        return

    # Check the code
    if response.getcode() != 200:
        msg = 'There was a problem querying url: {u}, returned code: {c}, unable to get the vpc-id'.format(
                u=vpc_id_url, c=response.getcode())
        log.error(msg)
        return
    vpc_id = response.read()
    return vpc_id


def get_owner_id_from_mac_address():
    """Gets the Owner ID for this EC2 instance

    :return: String instance ID or None
    """
    log = logging.getLogger(mod_logger + '.get_owner_id')

    # Exit if not running on AWS
    if not is_aws():
        log.info('This machine is not running in AWS, exiting...')
        return

    # Get the primary interface MAC address to query the meta data service
    log.debug('Attempting to determine the primary interface MAC address...')
    try:
        mac_address = get_primary_mac_address()
    except AWSMetaDataError:
        _, ex, trace = sys.exc_info()
        msg = '{n}: Unable to determine the mac address, cannot determine Owner ID:\n{e}'.format(
            n=ex.__class__.__name__, e=str(ex))
        log.error(msg)
        return

    owner_id_url = metadata_url + 'network/interfaces/macs/' + mac_address + '/owner-id'
    try:
        response = urllib.urlopen(owner_id_url)
    except(IOError, OSError) as ex:
        msg = 'Unable to query URL to get Owner ID: {u}\n{e}'.format(u=owner_id_url, e=ex)
        log.error(msg)
        return

    # Check the code
    if response.getcode() != 200:
        msg = 'There was a problem querying url: {u}, returned code: {c}, unable to get the Owner ID'.format(
            u=owner_id_url, c=response.getcode())
        log.error(msg)
        return
    owner_id = response.read()
    return owner_id


def get_availability_zone():
    """Gets the AWS Availability Zone ID for this system

    :return: (str) Availability Zone ID where this system lives
    """
    log = logging.getLogger(mod_logger + '.get_availability_zone')

    # Exit if not running on AWS
    if not is_aws():
        log.info('This machine is not running in AWS, exiting...')
        return

    availability_zone_url = metadata_url + 'placement/availability-zone'
    try:
        response = urllib.urlopen(availability_zone_url)
    except(IOError, OSError) as ex:
        msg = 'Unable to query URL to get Availability Zone: {u}\n{e}'.format(u=availability_zone_url, e=ex)
        log.error(msg)
        return

    # Check the code
    if response.getcode() != 200:
        msg = 'There was a problem querying url: {u}, returned code: {c}, unable to get the Availability Zone'.format(
            u=availability_zone_url, c=response.getcode())
        log.error(msg)
        return
    availability_zone = response.read()
    return availability_zone


def get_region():
    """Gets the AWS Region ID for this system

    :return: (str) AWS Region ID where this system lives
    """
    log = logging.getLogger(mod_logger + '.get_region')

    # First get the availability zone
    availability_zone = get_availability_zone()

    if availability_zone is None:
        msg = 'Unable to determine the Availability Zone for this system, cannot determine the AWS Region'
        log.error(msg)
        return

    # Strip of the last character to get the region
    region = availability_zone[:-1]
    return region


def get_primary_mac_address():
    """Determines the MAC address to use for querying the AWS
    meta data service for network related queries

    :return: (str) MAC address for the eth0 interface
    :raises: AWSMetaDataError
    """
    log = logging.getLogger(mod_logger + '.get_primary_mac_address')
    log.debug('Attempting to determine the MAC address for eth0...')
    try:
        mac_address = netifaces.ifaddresses('eth0')[netifaces.AF_LINK][0]['addr']
    except Exception:
        _, ex, trace = sys.exc_info()
        msg = '{n}: Unable to determine the eth0 mac address for this system:\n{e}'.format(
            n=ex.__class__.__name__, e=str(ex))
        raise AWSMetaDataError, msg, trace
    return mac_address
