#!/usr/bin/python

"""Module: systemd

This module provides utilities for running various 
systemd/systemctl commands.

Usage:

from pycons3rt import systemd
systemctl = systemd.Systemd()
systemctl.start('sshd.service')

"""
import sys
import logging
from logify import Logify
from dbus import SystemBus, Interface

__author__ = 'Mac <mac@lokilabs.io>'
__version__ = '0.20161029'

mod_logger = Logify.get_name() + '.systemd'

class Systemd():

	def __init__(self):
		self.cls_logger = mod_logger + '.Systemd'
		log = logging.getLogger(self.cls_logger + '.__init__')

		try:
			log.info('Creating systemd interface')
			self.bus = SystemBus()
			self.systemd = self.bus.get_object('org.freedesktop.systemd1',
				'/org/freedesktop/systemd1')
			self.manager = Interface(self.systemd, dbus_interface='org.freedesktop.systemd1.Manager')
		except Exception:
			_, ex, trace = sys.exc_info()
			msg = 'Unable to open systemd interface: {}'.format(str(ex))
			log.error(msg)
			log.info('Are you sure this system uses systemd? ^_^')
			raise msg, trace

	def start(self,process):
		"""Starts a process via systemd

		:param process: String process name; e.g., sshd.service
		:return: NONE
		:raise: CommandError on invalid string
		"""

		log = logging.getLogger(self.cls_logger + '.start')
		if not isinstance(process, str):
			msg = 'process must be a string'
			log.error(msg)
			raise TypeError(msg)
		try:
			log.info('Starting {} via systemd'.format(process))
			self.manager.StartUnit(process, 'replace')
		except Exception as e:
			log.error('Failed to start process {}: Error: {}'.format(process,str(e)))

	def stop(self,process):
		"""Stops a process via systemd

		:param process: String process name; e.g., sshd.service
		:return: NONE
		:raise: CommandError on invalid string
		"""
		log = logging.getLogger(self.cls_logger + '.stop')
		if not isinstance(process, str):
			msg = 'process must be a string'
			log.error(msg)
			raise TypeError(msg)

		try:
			log.info('Stopping {} via systemd'.format(process))
			self.manager.StopUnit(process,'replace')
		except Exception as e:
			log.error('Failed to stop process {}: Error: {}'.format(process,str(e)))

	def restart(self,process):
		"""Restarts/Reloads a process via systemd

		:param process: String process name; e.g., sshd.service
		:return: NONE
		:raise: CommandError on invalid string
		"""
		log = logging.getLogger(self.cls_logger + '.restart')

		if not isinstance(process, str):
			msg = 'process must be a string'
			log.error(msg)
			raise TypeError(msg)

		try:
			log.info('Restarting {} via systemd'.format(process))
			self.manager.ReloadOrRestartUnit(process,'replace')
		except Exception as e:
			log.error('Failed to restart process {}: Error: {}'.format(process,str(e)))

	def disable(self,process):
		"""Disables a process via systemd

		:param process: String process name; e.g., sshd.service
		:return: NONE
		:raise: CommandError on invalid string
		"""
		log = logging.getLogger(self.cls_logger + '.disable')

		if not isinstance(process, str):
			msg = 'process must be a string'
			log.error(msg)
			raise TypeError(msg)
		
		try:
			log.info('Disabling {} via systemd'.format(process))
			self.manager.DisableUnitFiles([process], False)
		except Exception as e:
			log.error('Failed to disable process {}: Error: {}'.format(process,str(e)))

	def enable(self,process):
		"""Enables a process via systemd

		:param process: String process name; e.g., sshd.service
		:return: NONE
		:raise: CommandError on invalid string
		"""
		log = logging.getLogger(self.cls_logger + '.enable')

		if not isinstance(process, str):
			msg = 'process must be a string'
			log.error(msg)
			raise TypeError(msg)

		try:
			log.info('Enabling {} via systemd'.format(process))
			self.manager.EnableUnitFiles([process],False, True)
		except Exception as e:
			log.error('Failed to enable process {}: Error: {}'.format(process,str(e)))

if __name__ == '__main__':
    sys.exit('Pycons3rt Library File. Should not be called directly.')