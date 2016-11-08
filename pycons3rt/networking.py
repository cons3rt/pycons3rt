#!/usr/bin/env python

import os
import sys
import jinja2
import logging
import netifaces
from pycons3rt.logify import Logify
from pycons3rt.systemd import Systemd
from pycons3rt.deployment import Deployment

__author__ = 'Mac <mac@lokilabs.io>'
__version__ = '0.20161102'

mod_logger = Logify.get_name() + '.networking'

def get_ip_addresses():
    """
    :return: (dict) of devices and aliases with the IPv4 address
    """

    # BUG: if there are more than one IPs on an interfaces, current
    # code will not detect one of them. SO TODO

    log = logging.getLogger(mod_logger + '.get_ip_addresses')
    devices = {}
    interfaces = netifaces.interfaces()
    for int in interfaces:
        try:
            ipaddr = (netifaces.ifaddresses(int)[netifaces.AF_INET])[0]['addr']
            devices[int] = ipaddr
            log.info('Found ip {} on interface {}.'.format(ipaddr,int))
        except KeyError as e:
            log.warn('Interface {} does not have a valid IPv4 address.'.format(int))
        except:
            log.error('Unknown error: {}'.format(str(e)))
            raise
    return devices

def get_gateway(interface=None,default=False):
    log = logging.getLogger(mod_logger + '.get_gateway')

    if default:
        try:
            defaultGW = netifaces.gateways()['default'][netifaces.AF_INET][0]
            log.info('Default gateway found as: {}'.format(defaultGW))
            return defaultGW
        except:
            log.error('Failed to find default gateway. Error: {}'.format(str(e)))
            raise
    elif interface:
        try:
            for list in netifaces.gateways()[netifaces.AF_INET]:
                if interface in list:
                    log.info('Found gateway {} for interface {}'.format(list[0],interface))
                    return list[0]
        except:
            log.error('Failed to find gateway for interface: {}'.format(interface))
            raise
    else:
        log.error('No valid lookup specified, exiting.')

def add_routes(interface,routes):
    log = logging.getLogger(mod_logger + '.add_routes')

    try:
        with open('/etc/sysconfig/network-scripts/route-{}'.format(interface), 'a') as routes:
            for ip, gw in routes.iteritems():
                routes.write('{} via {}\n'.format(ip,gw))
                log.info('Added route to {} via {}'.format(ip,gw))
    except IOError as e:
        log.error('Failed to open route file. Error: {}'.format(str(e)))

def configure_interface(interface,configuration,template=None,immediate=False):
    log = logging.getLogger(mod_logger + '.configure_interface')

    if not template:
        template = 'rhel-ifcfg.j2'
        log.debug('Using default interface template {}'.format(template))
        output = _renderDefault(template, configuration)
    else:
        output = _renderFullpath(template, configuration)

    try:        
        with open('/etc/sysconfig/network-scripts/ifcfg-{}'.format(interface), 'w+') as ifcfg:
            ifcfg.write(output)
        log.info('Wrote network configuration file for interface: {}'.format(interface))
    except IOError:
        log.error('Failed to open interface file for writing. Interface: {}'.format(interface))
        raise
    except:
        log.error('Unknown error: {}'.format(str(e)))
        raise

    if immediate:
        Systemd().restart('network.service')
        log.info('Configuration change made active.')

def disable_interface(interfaces):
    log = logging.getLogger(mod_logger + '.disable_interface')
    log.warn("NOT IMPLEMENTED")
    #TODO

def add_cons3rt_hosts():
    log = logging.getLogger(mod_logger + '.add_cons3rt_hosts')

    cons3rt_ip_map = {'messaging.milcloud.ceif.hpc.mil' : '10.220.101.60', 
        'cons3rt.milcloud.ceif.hpc.mil': '10.220.101.60' ,
        'assetdb.milcloud.ceif.hpc.mil' : '10.220.101.63'}
    cons3rt_ip_map['ra'] = Deployment().get_value('cons3rt.deploymentRun.virtRealm.remoteAccess.Ip')
    log.info('Adding host entries for cons3rt')
    with open('/etc/hosts', 'a') as hosts:
        for k, v in cons3rt_ip_map.iteritems():
            hosts.write('{v}    {k}\n'.format(v=v,k=k))

def _renderFullpath(tpl_path, context):
    log = logging.getLogger(mod_logger + '._renderFullPath')

    path, filename = os.path.split(tpl_path)
    log.debug('Rendering template from path: {} , Template: {}'.format(path,filename))
    return jinja2.Environment(loader=jinja2.FileSystemLoader(path or './')
        ).get_template(filename).render(context)

def _renderDefault(tpl_name, context):
    log = logging.getLogger(mod_logger + '._renderDefault')

    log.debug('Rendering template from pycons3rt dir: {}'.format(tpl_name))
    return jinja2.Environment(loader=jinja2.PackageLoader('pycons3rt', 'templates')
        ).get_template(tpl_name).render(context)

if __name__ == '__main__':
    sys.exit('Pycons3rt Library File. Should not be called directly.')