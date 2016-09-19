#!/usr/bin/python

"""Module: metadata

This module provides utilities for interacting with the AWS
meta data service.

"""
import logging
import urllib

# Pass ImportError on boto3 for offline assets
try:
    import boto3
    from botocore.client import ClientError
except ImportError:
    boto3 = None
    ClientError = None
    pass

from pycons3rt.logify import Logify
from pycons3rt.bash import get_mac_address


__author__ = 'Joe Yennaco'


# Set up logger name for this module
mod_logger = Logify.get_name() + '.awsapi.metadata'

# AWS Meta Data Service URL
metadata_url = 'http://169.254.169.254/latest/meta-data/'


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
        log.info('Unable to query the AWS meta data URL, this system is NOT running on AWS')
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

    mac_address = get_mac_address()
    if not mac_address:
        log.error('Unable to determine the mac address, cannot determine VPC ID')
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

    mac_address = get_mac_address()
    if not mac_address:
        log.error('Unable to determine the mac address, cannot determine Owner ID')
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
        msg = 'There was a problem querying url: {u}, returned code: {c}, unable to get the vpc-id'.format(
            u=owner_id_url, c=response.getcode())
        log.error(msg)
        return
    owner_id = response.read()
    return owner_id
