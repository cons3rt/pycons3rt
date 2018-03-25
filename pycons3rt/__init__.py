# -*- coding: utf-8 -*-
"""

                                                              /$$$$$$              /$$
                                                             /$$__  $$            | $$
  /$$$$$$  /$$   /$$  /$$$$$$$  /$$$$$$  /$$$$$$$   /$$$$$$$|__/  \ $$  /$$$$$$  /$$$$$$
 /$$__  $$| $$  | $$ /$$_____/ /$$__  $$| $$__  $$ /$$_____/   /$$$$$/ /$$__  $$|_  $$_/
| $$  \ $$| $$  | $$| $$      | $$  \ $$| $$  \ $$|  $$$$$$   |___  $$| $$  \__/  | $$
| $$  | $$| $$  | $$| $$      | $$  | $$| $$  | $$ \____  $$ /$$  \ $$| $$        | $$ /$$
| $$$$$$$/|  $$$$$$$|  $$$$$$$|  $$$$$$/| $$  | $$ /$$$$$$$/|  $$$$$$/| $$        |  $$$$/
| $$____/  \____  $$ \_______/ \______/ |__/  |__/|_______/  \______/ |__/         \___/
| $$       /$$  | $$
| $$      |  $$$$$$/
|__/       \______/


pycons3rt
~~~~~~~~~
:copyright: (c) 2016 by Jackpine Technologies Corporation.
:license: ISC, see LICENSE for more details.

"""
from . import osutil
from . import bash
from . import aliasip
from . import deployment
from . import cons3rtutil
from . import dyndict
from . import logify
from . import nexus
from . import slack
from . import windows


__title__ = 'pycons3rt'
__version__ = '0.0.1'
__description__ = 'Collection of python packages support CONS3RT asset installations.'
__url__ = 'https://software.forge.mil/sf/projects/testforge'
__build__ = 0
__author__ = 'Joe Yennaco'
__author_email__ = 'joe.yennaco@jackpinetech.com'
__license__ = 'DoD Community Source Usage Agreement Version 1.1'
__copyright__ = 'Copyright 2016 by Jackpine Technologies Corporation'
__all__ = ['osutil', 'bash', 'aliasip', 'deployment', 'cons3rtutil', 'dyndict', 'logify', 'nexus', 'slack', 'windows']
