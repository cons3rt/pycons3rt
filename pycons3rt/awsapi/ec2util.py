#!/usr/bin/python

"""Module: ec2util

This module provides utilities for interacting with the AWS
EC2 API, including networking and security group
configurations.

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

from pycons3rt.bash import get_ip_addresses
from pycons3rt.logify import Logify

from awslibs import AWSAPIError
from metadata import is_aws
from metadata import get_instance_id
from metadata import get_vpc_id_from_mac_address

__author__ = 'Joe Yennaco'


# Set up logger name for this module
mod_logger = Logify.get_name() + '.awsapi.ec2util'


class EC2UtilError(Exception):
    """Simple exception type for EC2Util errors
    """
    pass


class EC2Util(object):
    """Utility for interacting with the AWS API

    """
    def __init__(self, region_name=None, aws_access_key_id=None, aws_secret_access_key=None):
        self.cls_logger = mod_logger + '.EC2Util'
        log = logging.getLogger(self.cls_logger + '.__init__')
        try:
            self.client = get_ec2_client(region_name=region_name, aws_access_key_id=aws_access_key_id,
                                         aws_secret_access_key=aws_secret_access_key)
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to create an EC2 client.\n{e}'.format(e=str(ex))
            log.error(msg)
            raise EC2UtilError, msg, trace
        self.instance_id = get_instance_id()
        self.is_aws = is_aws()
        if self.instance_id and self.is_aws:
            self.vpc_id = get_vpc_id_from_mac_address()
        else:
            self.vpc_id = None

    def get_vpc_id(self):
        """Gets the VPC ID for this EC2 instance

        :return: String instance ID or None
        """
        log = logging.getLogger(self.cls_logger + '.get_vpc_id')

        # Exit if not running on AWS
        if not self.is_aws():
            log.info('This machine is not running in AWS, exiting...')
            return

        if self.instance_id is None:
            log.error('Unable to get the Instance ID for this machine')
            return
        log.info('Found Instance ID: {i}'.format(i=self.instance_id))

        log.info('Querying AWS to get the VPC ID...')
        try:
            response = self.client.describe_instances(
                    DryRun=False,
                    InstanceIds=[self.instance_id])
        except ClientError as ex:
            log.error('Unable to query AWS to get info for instance {i}\n{e}'.format(
                    i=self.instance_id, e=ex))
            return

        # Get the VPC ID from the response
        try:
            vpc_id = response['Reservations'][0]['Instances'][0]['VpcId']
        except KeyError as ex:
            log.error('Unable to get VPC ID from response: {r}\n{e}'.format(r=response, e=ex))
            return
        log.info('Found VPC ID: {v}'.format(v=vpc_id))
        return vpc_id

    def get_eni_id(self, interface=0):
        """Given an interface number, gets the AWS elastic network
        interface associated with the interface.

        :param interface: Integer associated to the interface/device number
        :return: String Elastic Network Interface ID or None if not found
        :raises OSError, AWSAPIError, EC2UtilError
        """
        log = logging.getLogger(self.cls_logger + '.get_eni_id')

        # Get the instance-id
        if self.instance_id is None:
            msg = 'Instance ID not found for this machine'
            log.error(msg)
            raise OSError(msg)
        log.info('Found instance ID: {i}'.format(i=self.instance_id))

        log.debug('Querying EC2 instances...')
        try:
            response = self.client.describe_instances(
                    DryRun=False,
                    InstanceIds=[self.instance_id]
            )
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query EC2 for instances\n{e}'.format(e=str(ex))
            log.error(msg)
            raise AWSAPIError, msg, trace
        log.debug('Found instance info: {r}'.format(r=response))

        # Find the ENI ID
        log.info('Looking for the ENI ID to alias...')
        eni_id = None
        try:
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    if instance['InstanceId'] == self.instance_id:
                        for network_interface in instance['NetworkInterfaces']:
                            if network_interface['Attachment']['DeviceIndex'] == interface:
                                eni_id = network_interface['NetworkInterfaceId']
        except KeyError:
            _, ex, trace = sys.exc_info()
            msg = 'ENI ID not found in AWS response for interface: {i}'.format(i=interface)
            log.error(msg)
            raise EC2UtilError, msg, trace

        log.info('Found ENI ID: {e}'.format(e=eni_id))
        return eni_id

    def add_secondary_ip(self, ip_address, interface=0):
        """Adds an IP address as a secondary IP address

        :param ip_address: String IP address to add as a secondary IP
        :param interface: Integer associated to the interface/device number
        :return: None
        :raises: AWSAPIError, EC2UtilError
        """
        log = logging.getLogger(self.cls_logger + '.add_secondary_ip')

        # Get the ENI ID
        eni_id = self.get_eni_id(interface)

        # Verify the ENI ID was found
        if eni_id is None:
            msg = 'Unable to find the corresponding ENI ID for interface: {i}'. \
                format(i=interface)
            log.error(msg)
            raise EC2UtilError(msg)
        else:
            log.info('Found ENI ID: {e}'.format(e=eni_id))

        # Assign the secondary IP address
        log.info('Attempting to assign the secondary IP address...')
        try:
            self.client.assign_private_ip_addresses(
                    NetworkInterfaceId=eni_id,
                    PrivateIpAddresses=[
                        ip_address,
                    ],
                    AllowReassignment=True
            )
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to assign secondary IP address\n{e}'.format(e=str(ex))
            log.error(msg)
            raise AWSAPIError, msg, trace
        log.info('Successfully added secondary IP address {s} to ENI ID {e} on interface {i}'.format(
                s=ip_address, e=eni_id, i=interface))

    def associate_elastic_ip(self, allocation_id, interface=0, private_ip=None):
        """Given an elastic IP address and an interface number, associates the
        elastic IP to the interface number on this host.

        :param allocation_id: String ID for the elastic IP
        :param interface: Integer associated to the interface/device number
        :param private_ip: String IP address of the private IP address to
                assign
        :return: None
        :raises: OSError, AWSAPIError, EC2UtilError
        """
        log = logging.getLogger(self.cls_logger + '.associate_elastic_ip')

        if private_ip is None:
            log.info('No private IP address provided, getting the primary IP'
                     'address on interface {i}...'.format(i=interface))
            private_ip = get_ip_addresses()['eth{i}'.format(i=interface)]

        log.info('Associating Elastic IP {e} on interface {i} on IP {p}'.format(
                e=allocation_id, i=interface, p=private_ip))

        # Get the ENI ID
        log.info('Getting the ENI ID for interface: {i}'.format(i=interface))
        eni_id = self.get_eni_id(interface)

        # Verify the ENI ID was found
        if eni_id is None:
            msg = 'Unable to find the corresponding ENI ID for interface: {i}'. \
                format(i=interface)
            log.error(msg)
            raise OSError(msg)
        else:
            log.info('Found ENI ID: {e}'.format(e=eni_id))

        # Assign the secondary IP address
        log.info('Attempting to assign the secondary IP address...')
        try:
            response = self.client.associate_address(
                    NetworkInterfaceId=eni_id,
                    AllowReassociation=True,
                    AllocationId=allocation_id,
                    PrivateIpAddress=private_ip
            )
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to attach elastic IP address {a} to interface {i}\n{e}'.format(
                    a=allocation_id, i=interface, e=str(ex))
            log.error(msg)
            raise AWSAPIError, msg, trace

        code = response['ResponseMetadata']['HTTPStatusCode']
        if code != 200:
            msg = 'associate_address returned invalid code: {c}'.format(c=code)
            log.error(msg)
            raise AWSAPIError(msg)
        log.info('Successfully associated elastic IP address ID {a} to interface {i} on ENI ID {e}'.format(
                a=allocation_id, i=interface, e=eni_id))

    def allocate_elastic_ip(self):
        """Allocates an elastic IP address

        :return: Dict with allocation ID and Public IP that were created
        :raises: AWSAPIError, EC2UtilError
        """
        log = logging.getLogger(self.cls_logger + '.allocate_elastic_ip')

        # Attempt to allocate a new elastic IP
        log.info('Attempting to allocate an elastic IP...')
        try:
            response = self.client.allocate_address(
                    DryRun=False,
                    Domain='vpc'
            )
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to allocate a new elastic IP address\n{e}'.format(e=str(ex))
            log.error(msg)
            raise AWSAPIError, msg, trace

        allocation_id = response['AllocationId']
        public_ip = response['PublicIp']
        log.info('Allocated Elastic IP with ID {a} and Public IP address {p}'.
                 format(a=allocation_id, p=public_ip))

        # Verify the Address was allocated successfully
        log.info('Verifying the elastic IP address was allocated and is available '
                 'for use...')
        ready = False
        num_checks = 60
        for _ in range(num_checks):
            try:
                self.client.describe_addresses(
                        DryRun=False,
                        AllocationIds=[allocation_id]
                )
            except ClientError:
                _, ex, trace = sys.exc_info()
                log.info('Elastic IP address {a} is not available for use, trying again in 1 sec...\n{e}'.format(
                        a=allocation_id, e=str(ex)))
                time.sleep(1)
            else:
                log.info('Elastic IP {a} is available for use'.format(a=allocation_id))
                ready = True
                break
        if ready:
            return {'AllocationId': allocation_id, 'PublicIp': public_ip}
        else:
            msg = 'Unable to verify existence of new elastic IP: {a}'. \
                format(a=allocation_id)
            log.error(msg)
            raise EC2UtilError(msg)

    def attach_new_eni(self, subnet_name, security_group_ids, device_index=2, allocation_id=None, description=''):
        """Creates a new Elastic Network Interface on the Subnet
        matching the subnet_name, with Security Group identified by
        the security_group_name, then attaches an Elastic IP address
        if specified in the allocation_id parameter, and finally
        attaches the new ENI to the EC2 instance instance_id at
        device index device_index.

        :param subnet_name: String name of the subnet
        :param security_group_ids: List of str IDs of the security groups
        :param device_index: Integer device index
        :param allocation_id: String ID of the elastic IP address
        :param description: String description
        :return: None
        :raises: EC2UtilError, AWSAPIError
        """
        log = logging.getLogger(self.cls_logger + '.attach_new_eni')
        log.info('Attempting to attach a new network interface to this instance...')

        # Validate args
        if not isinstance(security_group_ids, list):
            msg = 'security_group_name argument is not a string'
            log.error(msg)
            raise EC2UtilError(msg)
        if not isinstance(subnet_name, basestring):
            msg = 'subnet_name argument is not a string'
            log.error(msg)
            raise EC2UtilError(msg)
        if allocation_id is not None:
            if not isinstance(allocation_id, basestring):
                msg = 'allocation_id argument is not a string'
                log.error(msg)
                raise EC2UtilError(msg)
        try:
            device_index = int(device_index)
        except ValueError:
            _, ex, trace = sys.exc_info()
            msg = 'device_index argument is not an int\n{e}'.format(e=str(ex))
            log.error(msg)
            raise EC2UtilError, msg, trace

        # Get the instance ID and VPC ID for this machine
        if self.instance_id is None or self.vpc_id is None:
            msg = 'Unable to obtain instance ID or VPC ID'
            log.error(msg)
            raise EC2UtilError(msg)

        # Get the subnet ID by name
        log.info('Looking up the subnet ID by name: {n}'.format(n=subnet_name))
        filters = [
            {'Name': 'vpc-id', 'Values': [self.vpc_id]},
            {'Name': 'tag-key', 'Values': ['Name']},
            {'Name': 'tag-value', 'Values': [subnet_name]}]
        try:
            response = self.client.describe_subnets(
                    DryRun=False,
                    Filters=filters
            )
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to find subnet by name {n} in VPC {v}\n{e}'.format(n=subnet_name, v=self.vpc_id, e=str(ex))
            log.error(msg)
            raise EC2UtilError, msg, trace

        if len(response['Subnets']) < 1:
            msg = 'No subnets found with name {n} in VPC {v}'.format(n=subnet_name, v=self.vpc_id)
            log.error(msg)
            raise EC2UtilError(msg)
        elif len(response['Subnets']) > 1:
            msg = 'More than 1 subnet found in VPC {v} with name {n}'.format(n=subnet_name, v=self.vpc_id)
            log.error(msg)
            raise EC2UtilError(msg)

        subnet_id = response['Subnets'][0]['SubnetId']
        log.info('Found Subnet ID: {s}'.format(s=subnet_id))

        # Create the ENI
        log.info('Attempting to create the Elastic Network Interface on subnet: {s}, with Security Groups: {g}'.format(
                s=subnet_id, g=security_group_ids))
        try:
            response = self.client.create_network_interface(
                    DryRun=False,
                    SubnetId=subnet_id,
                    Description=description,
                    Groups=security_group_ids)
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to create a network interface on Subnet {s} using Security Groups {g}\n{e}'.format(
                    s=subnet_id, g=security_group_ids, e=str(ex))
            log.error(msg)
            raise AWSAPIError, msg, trace

        code = response['ResponseMetadata']['HTTPStatusCode']
        if code != 200:
            msg = 'create_network_interface returned invalid code: {c}'.format(c=code)
            log.error(msg)
            raise AWSAPIError(msg)

        try:
            eni_id = response['NetworkInterface']['NetworkInterfaceId']
        except KeyError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to parse ENI ID from response: {r}\n{e}'.format(r=response, e=str(ex))
            log.error(msg)
            raise EC2UtilError, msg, trace
        log.info('Created ENI ID: {eni}'.format(eni=eni_id))

        # Verify the ENI was created successfully
        log.info('Verifying the ENI was created and is available for use...')
        ready = False
        num_checks = 60
        for _ in range(num_checks):
            try:
                self.client.describe_network_interfaces(
                        DryRun=False,
                        NetworkInterfaceIds=[eni_id]
                )
            except ClientError as ex:
                log.info('ENI ID {eni} is not available for use, trying again in 1 sec...\n{e}'.format(
                        eni=eni_id, e=ex))
                time.sleep(2)
            else:
                log.info('ENI ID {eni} is available for use'.format(eni=eni_id))
                ready = True
                break
        if not ready:
            msg = 'Unable to verify existence of new ENI ID: {eni}'.format(eni=eni_id)
            log.error(msg)
            raise EC2UtilError(msg)

        # If an allocation_id is specified, attach the elastic IP to the new ENI
        if allocation_id is not None:
            log.info('Attempting to attach elastic IP {a} to ENI {e}'.format(a=allocation_id, e=eni_id))
            try:
                response = self.client.associate_address(
                        AllocationId=allocation_id,
                        DryRun=False,
                        NetworkInterfaceId=eni_id,
                        AllowReassociation=True)
            except ClientError:
                _, ex, trace = sys.exc_info()
                msg = 'Unable to associate Elastic IP {a} to ENI {eni}\n{e}'.format(
                        a=allocation_id, eni=eni_id, e=str(ex))
                log.error(msg)
                raise AWSAPIError, msg, trace

            code = response['ResponseMetadata']['HTTPStatusCode']
            if code != 200:
                msg = 'associate_address returned invalid code: {c}'.format(c=code)
                log.error(msg)
                raise AWSAPIError(msg)
            log.info('Successfully attached Elastic IP {a} to ENI ID {eni}'.format(
                    eni=eni_id, a=allocation_id))

        # Attach the ENI to this EC2 instance
        log.info('Attempting to attach ENI ID {eni} to instance ID {i}'.format(
                eni=eni_id, i=self.instance_id))
        try:
            response = self.client.attach_network_interface(
                    DryRun=False,
                    NetworkInterfaceId=eni_id,
                    InstanceId=self.instance_id,
                    DeviceIndex=device_index)
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to attach ENI ID {eni} to instance {i} at device index {d}\n{e}'.format(
                    eni=eni_id, i=self.instance_id, d=device_index, e=ex)
            log.error(msg)
            raise AWSAPIError, msg, trace

        code = response['ResponseMetadata']['HTTPStatusCode']
        if code != 200:
            msg = 'attach_network_interface returned invalid code: {c}'.format(c=code)
            log.error(msg)
            raise AWSAPIError(msg)
        log.info('Successfully attached ENI ID {eni} to EC2 instance ID {i}'.format(
                eni=eni_id, i=self.instance_id))

    def get_elastic_ips(self):
        """Returns the elastic IP info for this instance any are
        attached

        :return: (dict) Info about the Elastic IPs
        :raises AWSAPIError
        """
        log = logging.getLogger(self.cls_logger + '.get_elastic_ips')
        instance_id = get_instance_id()
        if instance_id is None:
            log.error('Unable to get the Instance ID for this machine')
            return
        log.info('Found Instance ID: {i}'.format(i=instance_id))

        log.info('Querying AWS for info about instance ID {i}...'.format(i=instance_id))
        try:
            instance_info = self.client.describe_instances(DryRun=False, InstanceIds=[instance_id])
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query AWS to get info for instance {i}\n{e}'.format(i=instance_id, e=ex)
            log.error(msg)
            raise AWSAPIError, msg, trace

        # Get the list of Public/Elastic IPs for this instance
        public_ips = []
        for network_interface in instance_info['Reservations'][0]['Instances'][0]['NetworkInterfaces']:
            network_interface_id = network_interface['NetworkInterfaceId']
            log.info('Checking ENI: {n}...'.format(n=network_interface_id))
            try:
                public_ips.append(network_interface['Association']['PublicIp'])
            except KeyError:
                log.info('No Public IP found for Network Interface ID: {n}'.format(n=network_interface_id))
            else:
                log.info('Found public IP for Network Interface ID {n}: {p}'.format(
                        n=network_interface_id, p=network_interface['Association']['PublicIp']))

        # Return if no Public/Elastic IPs found
        if len(public_ips) == 0:
            log.info('No Elastic IPs found for this instance: {i}'.format(i=instance_id))
            return
        else:
            log.info('Found Public IPs: {p}'.format(p=public_ips))

        # Get info for each Public/Elastic IP
        try:
            address_info = self.client.describe_addresses(DryRun=False, PublicIps=public_ips)
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query AWS to get info for addresses {p}\n{e}'.format(p=public_ips, e=str(ex))
            log.error(msg)
            raise AWSAPIError, msg, trace
        if not address_info:
            msg = 'No address info return for Public IPs: {p}'.format(p=public_ips)
            log.error(msg)
            raise AWSAPIError(msg)
        return address_info

    def disassociate_elastic_ips(self):
        """For each attached Elastic IP, disassociate it

        :return: None
        :raises AWSAPIError
        """
        log = logging.getLogger(self.cls_logger + '.disassociate_elastic_ips')

        try:
            address_info = self.get_elastic_ips()
        except AWSAPIError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to determine Elastic IPs on this EC2 instance'
            log.error(msg)
            raise AWSAPIError, msg, trace

        # Return is no elastic IPs were found
        if not address_info:
            log.info('No elastic IPs found to disassociate')
            return

        # Disassociate each Elastic IP
        for address in address_info['Addresses']:
            association_id = address['AssociationId']
            public_ip = address['PublicIp']
            log.info('Attempting to disassociate address {p} from Association ID: {a}'.format(
                    p=public_ip, a=association_id))
            try:
                self.client.disassociate_address(PublicIp=public_ip, AssociationId=association_id)
            except ClientError:
                _, ex, trace = sys.exc_info()
                msg = 'There was a problem disassociating Public IP {p} from Association ID {a}'.format(
                        p=public_ip, a=association_id)
                log.error(msg)
                raise AWSAPIError, msg, trace
            else:
                log.info('Successfully disassociated Public IP: {p}'.format(p=public_ip))

    def create_security_group(self, name, description='', vpc_id=None):
        """Creates a new Security Group with the specified name,
        description, in the specified vpc_id if provided.  If
        vpc_id is not provided, use self.vpc_id

        :param name: (str) Security Group Name
        :param description: (str) Security Group Description
        :param vpc_id: (str) VPC ID to create the Security Group
        :return: (str) Security Group ID
        :raises: AWSAPIError, EC2UtilError
        """
        log = logging.getLogger(self.cls_logger + '.create_security_group')
        # Validate args
        if not isinstance(name, basestring):
            msg = 'name argument is not a string'
            log.error(msg)
            raise EC2UtilError(msg)
        if not isinstance(description, basestring):
            msg = 'description argument is not a string'
            log.error(msg)
            raise EC2UtilError(msg)
        if vpc_id is None and self.vpc_id is not None:
            vpc_id = self.vpc_id
        else:
            msg = 'Unable to determine VPC ID to use to create the Security Group'
            log.error(msg)
            raise EC2UtilError(msg)

        # See if a Security Group already exists with the same name
        log.info('Checking for an existing security group with name {n} in VPC: {v}'.format(n=name, v=vpc_id))
        filters = [{
                'Name': 'vpc-id',
                'Values': [vpc_id]
            },
            {
                'Name': 'group-name',
                'Values': [name]
            }]
        try:
            response = self.client.describe_security_groups(DryRun=False, Filters=filters)
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query Security Groups to determine if {n} exists in VPC ID {v}\n{e}'.format(
                n=name, v=vpc_id, e=str(ex))
            log.error(msg)
            raise AWSAPIError, msg, trace
        else:
            log.debug('Found Security Group: {r}'.format(r=response))
            if len(response['SecurityGroups']) == 1:
                log.info('Found an existing security group with name {n} in VPC: {v}'.format(n=name, v=vpc_id))
                try:
                    group_id = response['SecurityGroups'][0]['GroupId']
                except KeyError:
                    _, ex, trace = sys.exc_info()
                    msg = 'Unable to determine the Security Group GroupId from response: {r}\n{e}'.format(
                        r=response, e=str(ex))
                    log.error(msg)
                    raise AWSAPIError, msg, trace
                else:
                    log.info('Found existing Security Group with GroupId: {g}'.format(g=group_id))
                    return group_id
            else:
                log.info('No existing Security Group with name {n} found in VPC: {v}'.format(n=name, v=vpc_id))

        # Create a new Security Group
        log.info('Attempting to create a Security Group with name <{n}>, description <{d}>, in VPC: {v}'.format(
            n=name, d=description, v=vpc_id))
        try:
            response = self.client.create_security_group(
                DryRun=False,
                GroupName=name,
                Description=description,
                VpcId=vpc_id
            )
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to create Security Group <{n}> in VPC: {v}'.format(n=name, v=vpc_id)
            log.error(msg)
            raise AWSAPIError, msg, trace
        else:
            log.info('Successfully created Security Group <{n}> in VPC: {v}'.format(n=name, v=vpc_id))
        return response['GroupId']

    def configure_security_group_ingress(self, security_group_id, port, desired_cidr_blocks):
        """Configures the security group ID allowing access
        only to the specified CIDR blocks, for the specified
        port number.

        :param security_group_id: (str) Security Group ID
        :param port: (str) TCP Port number
        :param desired_cidr_blocks: (list) List of desired CIDR
               blocks, e.g. 192.168.1.2/32
        :return: None
        :raises: AWSAPIError, EC2UtilError
        """
        log = logging.getLogger(self.cls_logger + '.configure_security_group_ingress')
        # Validate args
        if not isinstance(security_group_id, basestring):
            msg = 'security_group_id argument is not a string'
            log.error(msg)
            raise EC2UtilError(msg)
        if not isinstance(port, basestring):
            msg = 'port argument is not a string'
            log.error(msg)
            raise EC2UtilError(msg)
        if not isinstance(desired_cidr_blocks, list):
            msg = 'desired_cidr_blocks argument is not a list'
            log.error(msg)
            raise EC2UtilError(msg)
        log.info('Configuring Security Group <{g}> on port {p} to allow: {r}'.format(
            g=security_group_id, p=port, r=desired_cidr_blocks
        ))
        log.debug('Querying AWS for info on Security Group ID: {g}...'.format(g=security_group_id))
        try:
            security_group_info = self.client.describe_security_groups(DryRun=False, GroupIds=[security_group_id])
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to query AWS for Security Group ID: {g}\n{e}'.format(g=security_group_id, e=str(ex))
            log.error(msg)
            raise AWSAPIError, msg, trace
        else:
            log.debug('Found Security Group: {g}'.format(g=security_group_info))
        try:
            ingress_rules = security_group_info['SecurityGroups'][0]['IpPermissions']
        except KeyError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to get list of ingress rules for Security Group ID: {g}\n{e}'.format(
                    g=security_group_id, e=str(ex))
            log.error(msg)
            raise AWSAPIError, msg, trace
        else:
            log.debug('Found ingress rules: {r}'.format(r=ingress_rules))

        # Evaluate each rule against the provided port and IP address list
        log.debug('Setting ingress rules...')
        for ingress_rule in ingress_rules:
            log.debug('Evaluating ingress rule: {r}'.format(r=ingress_rule))
            if ingress_rule['ToPort'] != int(port):
                log.debug('Skipping rule not matching port: {p}'.format(p=port))
                continue
            log.info('Removing existing rules from Security Group {g} for port: {p}...'.format(
                    g=security_group_id, p=port))
            try:
                self.client.revoke_security_group_ingress(
                        DryRun=False,
                        GroupId=security_group_id,
                        IpPermissions=[ingress_rule])
            except ClientError:
                _, ex, trace = sys.exc_info()
                msg = 'Unable to remove existing Security Group rules for port {p} from Security Group: ' \
                      '{g}\n{e}'.format(p=port, g=security_group_id, e=str(ex))
                log.error(msg)
                raise AWSAPIError, msg, trace

        # Build ingress rule based on the provided CIDR block list
        desired_ip_permissions = [
            {
                'IpProtocol': 'tcp',
                'FromPort': int(port),
                'ToPort': int(port),
                'UserIdGroupPairs': [],
                'IpRanges': [],
                'PrefixListIds': []
            }
        ]

        # Add IP rules
        for desired_cidr_block in desired_cidr_blocks:
            log.debug('Adding ingress for CIDR block: {b}'.format(b=desired_cidr_block))
            cidr_block_entry = {
                'CidrIp': desired_cidr_block
            }
            desired_ip_permissions[0]['IpRanges'].append(cidr_block_entry)

        # Add the ingress rule
        log.debug('Adding ingress rule: {r}'.format(r=desired_ip_permissions))
        try:
            self.client.authorize_security_group_ingress(
                DryRun=False,
                GroupId=security_group_id,
                IpPermissions=desired_ip_permissions
            )
        except ClientError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to authorize Security Group ingress rule for Security Group {g}: {r}\n{e}'.format(
                    g=security_group_id, r=desired_ip_permissions, e=str(ex))
            log.error(msg)
            raise AWSAPIError, msg, trace
        else:
            log.info('Successfully added ingress rule for Security Group {g} on port: {p}'.format(
                    g=security_group_id, p=port))


def get_ec2_client(region_name=None, aws_access_key_id=None, aws_secret_access_key=None):
    """Gets an EC2 client

    :return: boto3.client object
    :raises: AWSAPIError
    """
    log = logging.getLogger(mod_logger + '.get_ec2_client')
    # Connect to EC2 API
    try:
        client = boto3.client('ec2', region_name=region_name, aws_access_key_id=aws_access_key_id,
                              aws_secret_access_key=aws_secret_access_key)
    except ClientError:
        _, ex, trace = sys.exc_info()
        msg = 'There was a problem connecting to EC2, please check AWS CLI and boto configuration, ensure ' \
              'credentials and region are set appropriately.\n{e}'.format(e=str(ex))
        log.error(msg)
        raise AWSAPIError, msg, trace
    else:
        log.info('Successfully created an EC2 client')
        return client


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