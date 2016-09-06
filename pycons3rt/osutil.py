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
import subprocess

__author__ = 'Joe Yennaco'


# pycons3rt clone URL
pycons3rt_git_url = 'git@github.com:cons3rt/pycons3rt.git'


def get_pycons3rt_home_dir():
    """Returns the pycons3rt home directory based on OS

    :return: (str) Full path to pycons3rt home
    :raises: OSError
    """
    if platform.system() == 'Linux':
        print 'Configuring pycons3rt for Linux...'
        return os.path.join(os.path.sep, 'etc', 'pycons3rt')
    elif platform.system() == 'Windows':
        print 'Configuing pycons3rt for Windows...'
        return os.path.join('C:', os.path.sep, 'pycons3rt')
    elif platform.system() == 'Darwin':
        print 'Configuring pycons3rt for Mac...'
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
    """Initializes the pycons3rt diretories

    :return: None
    :raises: OSError
    """
    for pycons3rt_dir in [get_pycons3rt_home_dir(),
                          get_pycons3rt_user_dir(),
                          get_pycons3rt_conf_dir(),
                          get_pycons3rt_log_dir(),
                          get_pycons3rt_src_dir()]:
        print 'Creating directory: {d}'.format(d=pycons3rt_dir)
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


def get_pycons3rt_source(branch='master'):
    """Clones the pycons3rt source

    :return: None
    :raises: OSError
    """
    os.environ['HOME'] = os.path.expanduser('~')
    command = ['git', 'clone', '-b', branch, pycons3rt_git_url, get_pycons3rt_src_dir()]
    try:
        result = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        std_out = result.communicate()
        code = result.poll()
    except (ValueError, TypeError, subprocess.CalledProcessError):
        _, ex, trace = sys.exc_info()
        msg = 'Unable to clone pycons3rt git repo with command: {c}'.format(c=command)
        print msg
        raise OSError(msg)
    if code != 0:
        msg = 'git clone command {g} returned code {c} with output:\n{o}'.format(
            g=command, c=code, o=std_out)
        print msg
        raise OSError(msg)
    else:
        print 'Successfully cloned git repo: {r}'.format(r=pycons3rt_git_url)


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
