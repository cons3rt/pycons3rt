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
import fileinput
import re

__author__ = 'Joe Yennaco'


default_logging_conf_file_contents = '''[loggers]
keys=root

[handlers]
keys=stream_handler,file_handler_info,file_handler_debug,file_handler_warn

[formatters]
keys=formatter_info,formatter_debug

[logger_root]
level=DEBUG
handlers=stream_handler,file_handler_info,file_handler_debug,file_handler_warn

[handler_stream_handler]
class=StreamHandler
level=INFO
formatter=formatter_info
args=(sys.stderr,)

[handler_file_handler_info]
class=FileHandler
level=INFO
formatter=formatter_info
args=('REPLACE_LOG_DIRpycons3rt-info.log', 'a')

[handler_file_handler_debug]
class=FileHandler
level=DEBUG
formatter=formatter_debug
args=('REPLACE_LOG_DIRpycons3rt-debug.log', 'a')

[handler_file_handler_warn]
class=FileHandler
level=WARN
formatter=formatter_debug
args=('REPLACE_LOG_DIRpycons3rt-warn.log', 'a')

[formatter_formatter_info]
format=%(asctime)s [%(levelname)s] %(name)s - %(message)s

[formatter_formatter_debug]
format=%(asctime)s [%(levelname)s] %(name)s <%(threadName)s> - %(message)s
'''

replace_str = 'REPLACE_LOG_DIR'


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
        try:
            os.makedirs(pycons3rt_dir)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(pycons3rt_dir):
                pass
            else:
                msg = 'Unable to create directory: {d}'.format(d=pycons3rt_dir)
                raise OSError(msg)


def main():
    # Create the pycons3rt directories
    try:
        initialize_pycons3rt_dirs()
    except OSError as ex:
        traceback.print_exc()
        return 1



    # Replace log directory paths
    log_dir_path = get_pycons3rt_log_dir() + os.path.sep
    conf_contents = default_logging_conf_file_contents.replace(replace_str, log_dir_path)

    # Create the logging config file
    logging_config_file_dest = os.path.join(get_pycons3rt_conf_dir(), 'pycons3rt-logging.conf')
    with open(logging_config_file_dest, 'w') as f:
        f.write(conf_contents)
    """
    
    for line in fileinput.input(logging_config_file_dest, inplace=True):
        if re.search(replace_str, line):
            new_line = re.sub(replace_str, log_dir_path, line, count=0)
            sys.stdout.write(new_line)
        else:
            sys.stdout.write(line)
    """
    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
