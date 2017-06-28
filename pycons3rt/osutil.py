#!/usr/bin/python

"""Module: osutil

This module initializes the pycons3rt directories and provides
OS-agnostic resources
"""
import platform
import os
import shutil
import sys
import errno
import traceback

__author__ = 'Joe Yennaco'


def get_os():
    """Returns the OS based on platform.sysyen

    :return: (str) OS family
    """
    return platform.system()


def get_pycons3rt_home_dir():
    """Returns the pycons3rt home directory based on OS

    :return: (str) Full path to pycons3rt home
    :raises: OSError
    """
    if platform.system() == 'Linux':
        return os.path.join(os.path.sep, 'etc', 'pycons3rt')
    elif platform.system() == 'Windows':
        return os.path.join('C:', os.path.sep, 'pycons3rt')
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


def get_pycons3rt_src_dir():
    """Returns the pycons3rt src directory

    :return: (str) Full path to pycons3rt src directory
    """
    return os.path.join(get_pycons3rt_user_dir(), 'src', 'pycons3rt')


def initialize_pycons3rt_dirs():
    """Initializes the pycons3rt directories

    :return: None
    :raises: OSError
    """
    for pycons3rt_dir in [get_pycons3rt_home_dir(),
                          get_pycons3rt_user_dir(),
                          get_pycons3rt_conf_dir(),
                          get_pycons3rt_log_dir(),
                          get_pycons3rt_src_dir()]:
        if os.path.isdir(pycons3rt_dir):
            continue
        print 'Creating directory: {d}'.format(d=pycons3rt_dir)
        try:
            os.makedirs(pycons3rt_dir)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(pycons3rt_dir):
                pass
            else:
                msg = 'Unable to create directory: {d}'.format(d=pycons3rt_dir)
                print msg
                raise OSError(msg)


def main():
    # Create the pycons3rt directories
    print 'Initializing pycons3rt directories...'
    try:
        initialize_pycons3rt_dirs()
    except OSError as ex:
        print 'There was a problem deploying CONS3RT with Homer!\n{e}'.format(e=str(ex))
        traceback.print_exc()
        return 1

    # Copy the logging config file to the conf directory
    script_dir = os.path.dirname(os.path.realpath(__file__))
    logging_config_file = os.path.join(script_dir, 'pycons3rt-logging.conf')
    if not os.path.isfile(logging_config_file):
        print 'Logging config file not found: {f}'.format(f=logging_config_file)
        return 2
    shutil.copy2(logging_config_file, get_pycons3rt_conf_dir())

    print 'Completed pycons3rt configuration'
    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
