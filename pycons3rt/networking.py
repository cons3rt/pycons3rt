#!/usr/bin/env python

import os
import sys
import logging
import netifaces
from pycons3rt.logify import Logify

__author__ = 'Mac <mac@lokilabs.io>'
__version__ = '0.20161029'

def get_ip_addresses():
    """
    :return: (dict) of devices and aliases with the IPv4 address
    """

    # BUG: if there are more than one IPs on an interfaces, current
    # code will not detect one of them. SO TODO

    log = logging.getLogger(self.cls_logger + '.get_ip_addresses')
    devices = {}
    interfaces = netifaces.interfaces()
    for int in interfaces:
        try:
            ipaddr = (netifaces.ifaddresses(int)[netifaces.AF_INET])[0]['addr']
            devices[int] = ipaddr
            log.info('Found ip {} on interface {}.'.format(ipaddr,int))
        except KeyError as e:
            log.warn('Interface {} does not have a valid IPv4 address.'.format(int))
    return devices

if __name__ == '__main__':
    sys.exit('Pycons3rt Library File. Should not be called directly.')