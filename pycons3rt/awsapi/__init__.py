# -*- coding: utf-8 -*-
"""
      ___           ___           ___                    ___           ___
     /\  \         /\  \         /\__\                  /\  \         /\  \
    /::\  \       _\:\  \       /:/ _/_                /::\  \       /::\  \     ___
   /:/\:\  \     /\ \:\  \     /:/ /\  \              /:/\:\  \     /:/\:\__\   /\__\
  /:/ /::\  \   _\:\ \:\  \   /:/ /::\  \            /:/ /::\  \   /:/ /:/  /  /:/__/
 /:/_/:/\:\__\ /\ \:\ \:\__\ /:/_/:/\:\__\          /:/_/:/\:\__\ /:/_/:/  /  /::\  \
 \:\/:/  \/__/ \:\ \:\/:/  / \:\/:/ /:/  /          \:\/:/  \/__/ \:\/:/  /   \/\:\  \__
  \::/__/       \:\ \::/  /   \::/ /:/  /            \::/__/       \::/__/     ~~\:\/\__\
   \:\  \        \:\/:/  /     \/_/:/  /              \:\  \        \:\  \        \::/  /
    \:\__\        \::/  /        /:/  /                \:\__\        \:\__\       /:/  /
     \/__/         \/__/         \/__/                  \/__/         \/__/       \/__/

awsapi
~~~~~~~~~
:copyright: (c) 2016 by Jackpine Technologies Corporation.
:license: ISC, see LICENSE for more details.

"""
from . import awslibs
from . import ec2util
from . import metadata
from . import s3util
from . import images


__title__ = 'pycons3rt.awsapi'
__version__ = '0.0.1'
__description__ = 'Set of utils to integrate with the AWS API.'
__url__ = 'https://software.forge.mil/sf/projects/testforge'
__build__ = 0
__author__ = 'Joe Yennaco'
__author_email__ = 'joe.yennaco@jackpinetech.com'
__license__ = 'DoD Community Source Usage Agreement Version 1.1'
__copyright__ = 'Copyright 2016 by Jackpine Technologies Corporation'
__all__ = ['awslibs', 'ec2util', 'metadata', 's3util', 'images']
