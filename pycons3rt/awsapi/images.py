#!/usr/bin/env python

"""Module: images

This module provides utilities for managing CONS3RT OS templates in AWS.

"""
import logging
import sys
import time

# Pass ImportError on boto3 for offline assets
try:
    import boto3
    from botocore.client import ClientError
except ImportError:
    boto3 = None
    ClientError = None
    pass

from pycons3rt.logify import Logify
from pycons3rt.awsapi.ec2util import get_ec2_client
from pycons3rt.awsapi.awslibs import AWSAPIError


__author__ = 'Joe Yennaco'


# Set up logger name for this module
mod_logger = Logify.get_name() + '.awsapi.images'

default_image_tags = [
    {
        'Key': 'cons3rtenabled',
        'Value': 'true'
    },
    {
        'Key': 'cons3rtNet1',
        'Value': 'user-net'
    },
    {
        'Key': 'cons3rtNet1SecurityGroup',
        'Value': 'default'
    }
]


class ImageUtilError(Exception):
    """Simple exception type for Image errors
    """
    pass


class ImageUtil(object):

    def __init__(self, owner_id, region_name=None, aws_access_key_id=None, aws_secret_access_key=None):
        self.cls_logger = mod_logger + '.ImageUtil'
        if not isinstance(owner_id, basestring):
            self.owner_id = None
        else:
            self.owner_id = owner_id
        try:
            self.ec2 = get_ec2_client()
        except AWSAPIError:
            raise
        self.region_name = region_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key

    def update_image(self, ami_id, instance_id):
        """Replaces an existing AMI ID with an image created from the provided
        instance ID
        
        :param ami_id: (str) ID of the AMI to delete and replace 
        :param instance_id: (str) ID of the instance ID to create an image from
        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.update_image')
        if not isinstance(ami_id, basestring):
            msg = 'Arg ami_id must be of type basestring, found: {t}'.format(t=ami_id.__class__.__name__)
            raise ImageUtilError(msg)
        if not isinstance(instance_id, basestring):
            msg = 'Arg instance_id must be of type basestring, found: {t}'.format(t=instance_id.__class__.__name__)
            raise ImageUtilError(msg)
        if ami_id is None or instance_id is None:
            raise ImageUtilError('The provided args ami_id and instance_id must not be None')

        log.info('Removing AMI ID: {a}, and replacing with an image for Instance ID: {i}'.format(
            a=ami_id, i=instance_id))

        # Get the current AMI info
        try:
            ami_info = self.ec2.describe_images(DryRun=False, ImageIds=[ami_id], Owners=[self.owner_id])
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to describe image ID: {a}.\n{e}'.format(n=ex.__class__.__name__, a=ami_id, e=str(ex))
            raise AWSAPIError, msg, trace
        log.debug('Found AMI info: {a}'.format(a=ami_info))

        # Grab the current cons3rtuuid tag data
        cons3rt_uuid = None
        try:
            image_tags = ami_info['Images'][0]['Tags']
            for image_tag in image_tags:
                if image_tag['Key'] == 'cons3rtuuid':
                    cons3rt_uuid = image_tag['Value']
        except KeyError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to find image tags for AMI ID: {a}\n{e}'.format(
                a=ami_id, n=ex.__class__.__name__, e=str(ex))
            raise ImageUtilError, msg, trace
        if cons3rt_uuid is None:
            raise ImageUtilError('AMI tag cons3rtuuid not found on image ID: {a}'.format(a=ami_id))
        log.info('Found image tag for cons3rtuuid: {u}'.format(u=cons3rt_uuid))
        log.debug('Found image tags: {t}'.format(t=image_tags))

        # Grab the Snapshot ID
        try:
            snapshot_id = ami_info['Images'][0]['BlockDeviceMappings'][0]['Ebs']['SnapshotId']
        except KeyError:
            _, ex, trace = sys.exc_info()
            raise ImageUtilError('{n}: Unable to determine Snapshot ID for AMI ID {a}\n{e}'.format(
                n=ex.__class__.__name__, a=ami_id, e=str(ex)))
        log.info('Found Snapshot ID of the current image: {s}'.format(s=snapshot_id))

        # Grab the Image name
        try:
            image_name = ami_info['Images'][0]['Name']
        except KeyError:
            _, ex, trace = sys.exc_info()
            raise ImageUtilError('{n}: Unable to determine Image name for AMI ID {a}\n{e}'.format(
                n=ex.__class__.__name__, a=ami_id, e=str(ex)))
        log.info('Found name of the current image: {n}'.format(n=image_name))

        # Grab the Image description
        try:
            image_description = ami_info['Images'][0]['Description']
        except KeyError:
            _, ex, trace = sys.exc_info()
            log.warn('{n}: Unable to determine Image description for AMI ID {a}\n{e}'.format(
                n=ex.__class__.__name__, a=ami_id, e=str(ex)))
            image_description = 'CONS3RT OS Template'
        log.info('Using description of the current image: {d}'.format(d=image_description))

        # Deregister the image
        log.debug('De-registering image ID: {a}...'.format(a=ami_id))
        try:
            self.ec2.deregister_image(DryRun=False, ImageId=ami_id)
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to de-register AMI ID: {a}\n{e}'.format(n=ex.__class__.__name__, a=ami_id, e=str(ex))
            raise ImageUtilError, msg, trace
        log.info('De-registered image ID: {a}'.format(a=ami_id))

        # Wait 20 seconds
        log.info('Waiting 20 seconds for the image to de-register...')
        time.sleep(20)

        # Create the new image
        log.info('Creating new image from instance ID: {i}'.format(i=instance_id))
        try:
            create_res = self.ec2.create_image(
                DryRun=False,
                InstanceId=instance_id,
                Name=image_name,
                Description=image_description,
                NoReboot=False
            )
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: There was a problem creating an image named [{m}] for image ID: {i}\n{e}'.format(
                n=ex.__class__.__name__, m=image_name, i=instance_id, e=str(ex))
            raise ImageUtilError, msg, trace

        # Get the new Image ID
        try:
            new_ami_id = create_res['ImageId']
        except KeyError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Image ID not found in the image creation response for instance ID: {i}\n{e}'.format(
                n=ex.__class__.__name__, i=instance_id, e=str(ex))
            raise ImageUtilError, msg, trace
        log.info('Created new image ID: {w}'.format(w=new_ami_id))

        # Wait 20 seconds
        log.info('Waiting 20 seconds for the image ID {w} to become available...'.format(w=new_ami_id))
        time.sleep(20)

        # Add tags to the new AMI
        try:
            self.ec2.create_tags(DryRun=False, Resources=[new_ami_id], Tags=image_tags)
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: There was a problem adding tags to the new image ID: {i}\n\nTags: {t}\n{e}'.format(
                n=ex.__class__.__name__, i=new_ami_id, t=image_tags, e=str(ex))
            raise ImageUtilError, msg, trace
        log.info('Successfully added tags to the new image ID: {w}\nTags: {t}'.format(w=new_ami_id, t=image_tags))

        # Delete the Snapshot ID
        log.debug('Deleting snapshot for the old image with ID: {s}'.format(s=snapshot_id))
        try:
            self.ec2.delete_snapshot(DryRun=False, SnapshotId=snapshot_id)
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to delete snapshot ID: {s}\n{e}'.format(
                n=ex.__class__.__name__, s=snapshot_id, e=str(ex))
            raise ImageUtilError, msg, trace

    def create_cons3rt_template(self, instance_id, name, description='CONS3RT OS template'):
        """Created a new CONS3RT-ready template from an instance ID
        
        :param instance_id: (str) Instance ID to create the image from
        :param name: (str) Name of the new image
        :param description: (str) Description of the new image
        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.create_cons3rt_template')
        if not isinstance(instance_id, basestring):
            msg = 'Arg instance_id must be of type basestring, found: {t}'.format(t=instance_id.__class__.__name__)
            raise ImageUtilError(msg)
        if not isinstance(name, basestring):
            msg = 'Arg name must be of type basestring, found: {t}'.format(t=instance_id.__class__.__name__)
            raise ImageUtilError(msg)
        if instance_id is None or name is None:
            raise ImageUtilError('The provided args instance_id or name must not be None')

        # Create the new image
        log.info('Creating new image from instance ID: {i}'.format(i=instance_id))
        try:
            create_res = self.ec2.create_image(
                DryRun=False,
                InstanceId=instance_id,
                Name=name,
                Description=description,
                NoReboot=False
            )
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: There was a problem creating an image named [{m}] for image ID: {i}\n{e}'.format(
                n=ex.__class__.__name__, m=name, i=instance_id, e=str(ex))
            raise ImageUtilError, msg, trace

        # Get the new Image ID
        try:
            new_ami_id = create_res['ImageId']
        except KeyError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Image ID not found in the image creation response for instance ID: {i}\n{e}'.format(
                n=ex.__class__.__name__, i=instance_id, e=str(ex))
            raise ImageUtilError, msg, trace
        log.info('Created new image ID: {w}'.format(w=new_ami_id))

        # Wait 20 seconds
        log.info('Waiting 20 seconds for the image ID {w} to become available...'.format(w=new_ami_id))
        time.sleep(20)

        # Add tags to the new AMI
        try:
            self.ec2.create_tags(DryRun=False, Resources=[new_ami_id], Tags=default_image_tags)
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: There was a problem adding tags to the new image ID: {i}\n\nTags: {t}\n{e}'.format(
                n=ex.__class__.__name__, i=new_ami_id, t=default_image_tags, e=str(ex))
            raise ImageUtilError, msg, trace
        log.info('Successfully added tags to the new image ID: {w}\nTags: {t}'.format(
            w=new_ami_id, t=default_image_tags))

    def copy_cons3rt_template(self, ami_id):
        """
        
        :param ami_id:
        :return: 
        """
        log = logging.getLogger(self.cls_logger + '.copy_cons3rt_template')

        # Get the current AMI info
        try:
            ami_info = self.ec2.describe_images(DryRun=False, ImageIds=[ami_id], Owners=[self.owner_id])
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to describe image ID: {a}.\n{e}'.format(n=ex.__class__.__name__, a=ami_id, e=str(ex))
            raise AWSAPIError, msg, trace
        log.debug('Found AMI info: {a}'.format(a=ami_info))

        # Grab the current cons3rtuuid tag data
        cons3rt_uuid = None
        try:
            image_tags = ami_info['Images'][0]['Tags']
            for image_tag in image_tags:
                if image_tag['Key'] == 'cons3rtuuid':
                    cons3rt_uuid = image_tag['Value']
        except KeyError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: Unable to find image tags for AMI ID: {a}\n{e}'.format(
                a=ami_id, n=ex.__class__.__name__, e=str(ex))
            raise ImageUtilError, msg, trace
        if cons3rt_uuid is None:
            raise ImageUtilError('AMI tag cons3rtuuid not found on image ID: {a}'.format(a=ami_id))
        log.info('Found image tag for cons3rtuuid: {u}'.format(u=cons3rt_uuid))
        log.debug('Found image tags: {t}'.format(t=image_tags))


def main():
    """Sample usage for this python module

    This main method simply illustrates sample usage for this python
    module.

    :return: None
    """
    log = logging.getLogger(mod_logger + '.main')
    log.info('Main!')


if __name__ == '__main__':
    main()
