#!/usr/bin/python

"""Module: osutil

This module initializes the pycons3rt directories and provides
OS-agnostic resources
"""
import platform
import os
import errno

__author__ = 'Joe Yennaco'


def get_pycons3rt_home_dir():
    """Returns the pycons3rt home directory based on OS

    :return: (str) Full path to pycons3rt home
    :raises: OSError
    """
    if platform.system() == 'Linux':
        return os.path.join(os.path.sep, 'etc', 'pycons3rt')
    elif platform.system() == 'Windows':
        return os.path.join('c:', 'pycons3rt')
    elif platform.system() == 'Darwin':
        return os.path.join(os.path.expanduser('~'), '.pycons3rt')
    else:
        raise OSError('Unsupported Operating System')


def get_pycons3rt_user_dir():
    """Returns the pycons3rt user-writable home dir

    :return: (str) Full path to the user-writable pycons3rt home
    """
    return os.path.join(os.path.expanduser('~'), '.pycons3rt')


def get_pycons3rt_log_dir():
    """Returns the pycons3rt log directory

    :return: (str) Full path to pycons3rt log directory
    """
    return os.path.join(get_pycons3rt_user_dir(), 'log')


def get_pycons3rt_conf_dir():
    """Returns the pycons3rt conf directory

    :return: (str) Full path to pycons3rt conf directory
    """
    return os.path.join(get_pycons3rt_home_dir(), 'conf')


def initialize_pycons3rt_dirs():
    """Initializes the pycons3rt diretories

    :return: None
    :raises: OSError
    """
    for pycons3rt_dir in [get_pycons3rt_home_dir(),
                          get_pycons3rt_user_dir(),
                          get_pycons3rt_conf_dir(),
                          get_pycons3rt_log_dir()]:
        if os.path.isdir(pycons3rt_dir):
            continue
        try:
            os.makedirs(pycons3rt_dir)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(pycons3rt_dir):
                pass
            else:
                msg = 'Unable to create directory: {d}'.format(d=pycons3rt_dir)
                print msg
                raise OSError(msg)
