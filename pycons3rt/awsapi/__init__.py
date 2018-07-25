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
:copyright: (c) 2018 by Jackpine Technologies Corporation.
:license: ISC, see LICENSE for more details.

"""
from . import awslibs
from . import ec2util
from . import metadata
from . import s3util
from . import images


__title__ = 'pycons3rt.awsapi'
__name__ = 'pycons3rt.awsapi'
__all__ = [
    'awslibs',
    'ec2util',
    'metadata',
    's3util',
    'images'
]
