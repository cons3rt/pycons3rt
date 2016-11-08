#!/usr/bin/python

"""Module: bash

This module provides utilities for running standard bash commands
from python.

"""
import logging
import os
import subprocess
import errno
import fileinput
import re
import sys
import zipfile
import socket
import contextlib
import time
from threading import Timer, Thread
from Queue import Queue, Empty

from logify import Logify

__author__ = 'Joe Yennaco'


# Set up logger name for this module
mod_logger = Logify.get_name() + '.bash'


class CommandError(Exception):
    """Error encompassing problems that could be encountered while
    running Linux commands.
    """
    pass


def process_killer(p):
    """Returns a function to kill the process p
    :param p: Process
    :return: kill function for process p
    """
    return p.kill()


def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()


def run_command(command, timeout_sec=3600.0, output=True):
    """Runs a command using the subprocess module

    :param command: List containing the command and all args
    :param timeout_sec (float) seconds to wait before killing
        the command.
    :param output (bool) True collects output, False ignores output
    :return: Dict containing the command output and return code
    :raises CommandError
    """
    log = logging.getLogger(mod_logger + '.run_command')
    if not isinstance(command, list):
        msg = 'command arg must be a list'
        log.error(msg)
        raise CommandError(msg)
    if output:
        subproc_stdout = subprocess.PIPE
        subproc_stderr = subprocess.STDOUT
    else:
        subproc_stdout = None
        subproc_stderr = None
    command = map(str, command)
    command_str = ' '.join(command)
    timer = None
    log.debug('Running command: {c}'.format(c=command_str))
    output_collector = ''
    try:
        log.debug('Opening subprocess...')
        subproc = subprocess.Popen(
            command,
            bufsize=1,
            stdin=open(os.devnull),
            stdout=subproc_stdout,
            stderr=subproc_stderr
        )
        log.debug('Opened subprocess wih PID: {p}'.format(p=subproc.pid))
        log.debug('Setting up process kill timer for PID {p} at {s} sec...'.format(p=subproc.pid, s=timeout_sec))
        kill_proc = process_killer
        timer = Timer(timeout_sec, kill_proc, [subproc])
        timer.start()
        if output:
            log.debug('Collecting and logging output...')
            with subproc.stdout:
                for line in iter(subproc.stdout.readline, b''):
                    output_collector += line.rstrip() + '\n'
                    print(">>> " + line.rstrip())
        log.debug('Waiting for process completion...')
        subproc.wait()
        log.debug('Collecting the exit code...')
        code = subproc.poll()
    except ValueError:
        _, ex, trace = sys.exc_info()
        msg = 'Bad command supplied: {c}\n{e}'.format(
            c=command_str, e=str(ex)
        )
        log.error(msg)
        raise CommandError, msg, trace
    except (OSError, IOError):
        _, ex, trace = sys.exc_info()
        msg = 'There was a problem running command: {c}\n{e}'.format(
            c=command_str, e=str(ex))
        log.error(msg)
        raise CommandError, msg, trace
    except subprocess.CalledProcessError:
        _, ex, trace = sys.exc_info()
        msg = 'Command returned a non-zero exit code: {c}, return code: {cde}\n{e}'.format(
            c=command_str, cde=ex.returncode, e=ex)
        log.error(msg)
        raise CommandError, msg, trace
    finally:
        if timer is not None:
            log.debug('Cancelling the timer...')
            timer.cancel()
        else:
            log.debug('No need to cancel the timer.')
    # Collect exit code and output for return
    output = output_collector.strip()
    try:
        code = int(code)
    except ValueError:
        _, ex, trace = sys.exc_info()
        msg = 'Return code {c} could not be parsed into an int\n{e}'.format(
            c=code, e=str(ex))
        log.error(msg)
        raise CommandError, msg, trace
    else:
        log.debug('Command executed and returned code: {c} with output:\n{o}'.format(c=code, o=output))
        output = {
            'output': output,
            'code': code
        }
    return output


def get_ip_addresses():
    """Gets the ip addresses from ifconfig

    :return: (dict) of devices and aliases with the IPv4 address
    """
    log = logging.getLogger(mod_logger + '.get_ip_addresses')

    command = ['/sbin/ifconfig']
    try:
        result = run_command(command)
    except CommandError:
        raise
    ifconfig = result['output']

    # Scan the ifconfig output for IPv4 addresses
    devices = {}
    parts = ifconfig.split()
    device = None
    for part in parts:
        if device is None:
            if 'eth' in part:
                device = part
        else:
            test = part.split(':', 1)
            if len(test) == 2:
                if test[0] == 'addr':
                    ip_address = test[1]
                    log.info('Found IP address %s on device %s', ip_address,
                             device)
                    devices[device] = ip_address
                    device = None
    return devices


def get_mac_address(device_index=0):
    """Returns the Mac Address given a device index

    :param device_index: (int) Device index
    :return: (str) Mac address or None
    """
    log = logging.getLogger(mod_logger + '.get_mac_address')
    command = ['ip', 'addr', 'show', 'eth{d}'.format(d=device_index)]
    log.info('Attempting to find a mac address at device index: {d}'.format(d=device_index))
    try:
        result = run_command(command)
    except CommandError:
        _, ex, trace = sys.exc_info()
        log.error('There was a problem running command, unable to determine mac address: {c}\n{e}'.format(
                c=command, e=str(ex)))
        return
    ipaddr = result['output'].split()
    get_next = False
    mac_address = None
    for part in ipaddr:
        if get_next:
            mac_address = part
            log.info('Found mac address: {m}'.format(m=mac_address))
            break
        if 'link' in part:
            get_next = True
    if not mac_address:
        log.info('mac address not found for device: {d}'.format(d=device_index))
    return mac_address


def chmod(path, mode, recursive=False):
    """Emulates bash chmod command

    This method sets the file permissions to the specified mode.

    :param path: (str) Full path to the file or directory
    :param mode: (str) Mode to be set (e.g. 0755)
    :param recursive: (bool) Set True to make a recursive call
    :return: int exit code of the chmod command
    :raises CommandError
    """
    log = logging.getLogger(mod_logger + '.chmod')

    # Validate args
    if not isinstance(path, basestring):
        msg = 'path argument is not a string'
        log.error(msg)
        raise CommandError(msg)
    if not isinstance(mode, basestring):
        msg = 'mode argument is not a string'
        log.error(msg)
        raise CommandError(msg)

    # Ensure the item exists
    if not os.path.exists(path):
        msg = 'Item not found: {p}'.format(p=path)
        log.error(msg)
        raise CommandError(msg)

    # Create the chmod command
    command = ['chmod']
    # Make it recursive if specified
    if recursive:
        command.append('-R')
    command.append(mode)
    command.append(path)
    try:
        result = run_command(command)
    except CommandError:
        raise
    log.info('chmod command exited with code: {c}'.format(c=result['code']))
    return result['code']


def mkdir_p(path):
    """Emulates 'mkdir -p' in bash

    :param path: (str) Path to create
    :return: None
    :raises CommandError
    """
    log = logging.getLogger(mod_logger + '.mkdir_p')
    if not isinstance(path, basestring):
        msg = 'path argument is not a string'
        log.error(msg)
        raise CommandError(msg)
    log.info('Attempting to create directory: %s', path)
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            msg = 'Unable to create directory: {p}'.format(p=path)
            log.error(msg)
            raise CommandError(msg)


def source(script):
    """Emulates 'source' command in bash

    :param script: (str) Full path to the script to source
    :return: Updated environment
    :raises CommandError
    """
    log = logging.getLogger(mod_logger + '.source')
    if not isinstance(script, basestring):
        msg = 'script argument must be a string'
        log.error(msg)
        raise CommandError(msg)
    log.info('Attempting to source script: %s', script)
    try:
        pipe = subprocess.Popen(". %s; env" % script, stdout=subprocess.PIPE, shell=True)
        data = pipe.communicate()[0]
    except ValueError:
        _, ex, trace = sys.exc_info()
        msg = 'Invalid argument:\n{e}'.format(e=str(ex))
        log.error(msg)
        raise CommandError, msg, trace
    except OSError:
        _, ex, trace = sys.exc_info()
        msg = 'File not found: {s}\n{e}'.format(s=script, e=str(ex))
        raise CommandError, msg, trace
    except subprocess.CalledProcessError:
        _, ex, trace = sys.exc_info()
        msg = 'Script {s} returned a non-zero exit code: {c}\n{e}'.format(
            s=script, e=str(ex), c=ex.returncode)
        log.error(msg)
        raise CommandError, msg, trace
    env = {}
    for line in data.splitlines():
        entry = line.split("=", 1)
        env[entry[0]] = entry[1]
    os.environ.update(env)
    return env


def yum_update(downloadonly=False, dest_dir='/tmp'):
    """Run a yum update on this system

    This public method runs the yum -y update command to update
    packages from yum. If downloadonly is set to true, the yum
    updates will be downloaded to the specified dest_dir.

    :param dest_dir: (str) Full path to the download directory
    :param downloadonly: Boolean
    :return: int exit code from the yum command
    :raises CommandError
    """
    log = logging.getLogger(mod_logger + '.yum_update')

    # Type checks on the args
    if not isinstance(dest_dir, basestring):
        msg = 'dest_dir argument must be a string'
        log.error(msg)
        raise CommandError(msg)
    if not isinstance(downloadonly, bool):
        msg = 'downloadonly argument must be a bool'
        log.error(msg)
        raise CommandError(msg)

    # If downloadonly was True, download packages to dest_dir
    if downloadonly:
        # Create the destination directory if it does not exist
        log.info('Creating directory: %s', dest_dir)
        try:
            mkdir_p(dest_dir)
        except OSError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to create destination directory: {d}'.format(
                d=dest_dir)
            log.error(msg)
            raise CommandError, msg, trace

        # Build command string with downloadonly options specified
        command = ['yum', '-y', 'update', '--downloadonly',
                   '--downloaddir={d}'.format(d=dest_dir)]
        log.info('Downloading updates from yum to %s...', dest_dir)
    else:
        # Build command string to update directly
        command = ['yum', '-y', 'update']
        log.info('Installing yum updates from RHN...')

    # Run the command
    try:
        result = run_command(command)
    except CommandError:
        raise
    log.info('Yum update completed and exit with code: {c}'.format(
        c=result['code']))
    return result['code']


def yum_install(packages, downloadonly=False, dest_dir='/tmp'):
    """Installs (or downloads) a list of packages from yum

    This public method installs a list of packages from yum or
    downloads the packages to the specified destination directory using
    the yum-downloadonly yum plugin.

    :param downloadonly: Boolean, set to only download the package and
        not install it
    :param packages: List of package names (str) to download param
    :param dest_dir: (str) Full path to the download directory
    :return: int exit code from the yum command
    :raises CommandError
    """
    log = logging.getLogger(mod_logger + '.yum_install')

    # Type checks on the args
    if not isinstance(dest_dir, basestring):
        msg = 'dest_dir argument must be a string'
        log.error(msg)
        raise CommandError(msg)
    if not isinstance(packages, list):
        msg = 'packages argument must be a list'
        log.error(msg)
        raise CommandError(msg)
    if not isinstance(downloadonly, bool):
        msg = 'downloadonly argument must be a bool'
        log.error(msg)
        raise CommandError(msg)
    if not packages:
        msg = 'Empty list of packages provided'
        log.error(msg)
        raise CommandError(msg)
    for package in packages:
        # Ensure the package is specified as a string
        if not isinstance(package, basestring):
            msg = 'One of the packages was not specified as a string'
            log.error(msg)
            raise CommandError(msg)

    # Build the yum install command string
    command = ['yum', '-y', 'install'] + packages

    # If downloadonly was True, download packages to dest_dir
    if downloadonly:
        log.info('yum downloadonly was specified, adding additional options...')

        # Append downloadonly args to the command
        command += ['--downloadonly', '--downloaddir={d}'.format(d=dest_dir)]

        # Create the destination directory if it does not exist
        log.info('Creating directory: %s', dest_dir)
        try:
            mkdir_p(dest_dir)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to create destination directory: {d}'.format(d=dest_dir)
            log.error(msg)
            raise CommandError, msg, trace
        log.info('Downloading packages from yum to %s...', dest_dir)
    else:
        log.info('Installing yum packages from RHN...')

    # Run the yum install command
    try:
        result = run_command(command)
    except CommandError:
        raise
    log.info('Yum update completed and exit with code: {c}'.format(
        c=result['code']))
    return result['code']


def rpm_install(install_dir):
    """This method installs all RPM files in a specific dir

    :param install_dir: (str) Full path to the directory
    :return int exit code form the rpm command
    :raises CommandError
    """
    log = logging.getLogger(mod_logger + '.rpm_install')

    # Type checks on the args
    if not isinstance(install_dir, basestring):
        msg = 'install_dir argument must be a string'
        log.error(msg)
        raise CommandError(msg)

    # Ensure the install_dir directory exists
    if not os.path.isdir(install_dir):
        msg = 'Directory not found: {f}'.format(f=install_dir)
        log.error(msg)
        raise CommandError(msg)

    # Create the command
    command = ['rpm', '-iv', '--force', '{d}/*.rpm'.format(d=install_dir)]

    # Run the rpm command
    try:
        result = run_command(command)
    except CommandError:
        raise
    log.info('RPM completed and exit with code: {c}'.format(
        c=result['code']))
    return result['code']


def sed(file_path, pattern, replace_str, g=0):
    """Python impl of the bash sed command

    This method emulates the functionality of a bash sed command.

    :param file_path: (str) Full path to the file to be edited
    :param pattern: (str) Search pattern to replace as a regex
    :param replace_str: (str) String to replace the pattern
    :param g: (int) Whether to globally replace (0) or replace 1
        instance (equivalent to the 'g' option in bash sed
    :return: None
    :raises CommandError
    """
    log = logging.getLogger(mod_logger + '.sed')

    # Type checks on the args
    if not isinstance(file_path, basestring):
        msg = 'file_path argument must be a string'
        log.error(msg)
        raise CommandError(msg)
    if not isinstance(pattern, basestring):
        msg = 'pattern argument must be a string'
        log.error(msg)
        raise CommandError(msg)
    if not isinstance(replace_str, basestring):
        msg = 'replace_str argument must be a string'
        log.error(msg)
        raise CommandError(msg)

    # Ensure the file_path file exists
    if not os.path.isfile(file_path):
        msg = 'File not found: {f}'.format(f=file_path)
        log.error(msg)
        raise CommandError(msg)

    # Search for a matching pattern and replace matching patterns
    log.info('Updating file: %s...', file_path)
    for line in fileinput.input(file_path, inplace=True):
        if re.search(pattern, line):
            log.info('Updating line: %s', line)
            new_line = re.sub(pattern, replace_str, line, count=g)
            log.info('Replacing with line: %s', new_line)
            sys.stdout.write(new_line)
        else:
            sys.stdout.write(line)


def zip_dir(dir_path, zip_file):
    """Creates a zip file of a directory tree

    This method creates a zip archive using the directory tree dir_path
    and adds to zip_file output.

    :param dir_path: (str) Full path to directory to be zipped
    :param zip_file: (str) Full path to the output zip file
    :return: None
    :raises CommandError
    """
    log = logging.getLogger(mod_logger + '.zip_dir')

    # Validate args
    if not isinstance(dir_path, basestring):
        msg = 'dir_path argument must be a string'
        log.error(msg)
        raise CommandError(msg)
    if not isinstance(zip_file, basestring):
        msg = 'zip_file argument must be a string'
        log.error(msg)
        raise CommandError(msg)

    # Ensure the dir_path file exists
    if not os.path.isdir(dir_path):
        msg = 'Directory not found: {f}'.format(f=dir_path)
        log.error(msg)
        raise CommandError(msg)

    try:
        with contextlib.closing(zipfile.ZipFile(zip_file, 'w')) as zip_w:
            for root, dirs, files in os.walk(dir_path):
                for f in files:
                    log.debug('Adding file to zip: %s', f)
                    strip = len(dir_path) - len(os.path.split(dir_path)[-1])
                    file_name = os.path.join(root, f)
                    archive_name = os.path.join(root[strip:], f)
                    zip_w.write(file_name, archive_name)
    except Exception:
        _, ex, trace = sys.exc_info()
        msg = 'Unable to create zip file: {f}\n{e}'.format(
            f=zip_file, e=str(ex))
        log.error(msg)
        raise CommandError, msg, trace
    log.info('Successfully created zip file: %s', zip_file)


def get_ip(interface=0):
    """This method return the IP address

    :param interface: (int) Interface number (e.g. 0 for eth0)
    :return: (str) IP address or None
    """
    log = logging.getLogger(mod_logger + '.get_ip')

    log.info('Getting the IP address for this system...')
    ip_address = None
    try:
        log.info('Attempting to get IP address by hostname...')
        ip_address = socket.gethostbyname(socket.gethostname())
    except socket.error:
        log.info('Unable to get IP address for this system using hostname, '
                 'using a bash command...')
        command = 'ip addr show eth%s | grep inet | grep -v inet6 | ' \
                  'awk \'{ print $2 }\' | cut -d/ -f1 ' \
                  '>> /root/ip' % interface
        try:
            log.info('Running command: %s', command)
            subprocess.check_call(command, shell=True)
        except(OSError, subprocess.CalledProcessError):
            _, ex, trace = sys.exc_info()
            msg = 'Unable to get the IP address of this system\n{e}'.format(
                e=str(ex))
            log.error(msg)
            raise CommandError, msg, trace
        else:
            ip_file = '/root/ip'
            log.info('Command executed successfully, pulling IP address from '
                     'file: %s', ip_file)
            if os.path.isfile(ip_file):
                with open(ip_file, 'r') as f:
                    for line in f:
                        ip_address = line.strip()
                        log.info('Found IP address from file: %s', ip_address)
            else:
                msg = 'File not found: {f}'.format(f=ip_file)
                log.error(msg)
                raise CommandError(msg)
    log.info('Returning IP address: %s', ip_address)
    return ip_address


def update_hosts_file(ip, entry):
    """Updates the /etc/hosts file for the specified ip

    This method updates the /etc/hosts file for the specified IP
    address with the specified entry.

    :param ip: (str) IP address to be added or updated
    :param entry: (str) Hosts file entry to be added
    :return: None
    :raises CommandError
    """
    log = logging.getLogger(mod_logger + '.update_hosts_file')

    # Validate args
    if not isinstance(ip, basestring):
        msg = 'ip argument must be a string'
        log.error(msg)
        raise CommandError(msg)
    if not isinstance(entry, basestring):
        msg = 'entry argument must be a string'
        log.error(msg)
        raise CommandError(msg)

    # Ensure the file_path file exists
    hosts_file = '/etc/hosts'
    if not os.path.isfile(hosts_file):
        msg = 'File not found: {f}'.format(f=hosts_file)
        log.error(msg)
        raise CommandError(msg)

    # Updating /etc/hosts file
    log.info('Updating hosts file: {f} with IP {i} and entry: {e}'.format(f=hosts_file, i=ip, e=entry))
    full_entry = ip + ' ' + entry.strip() + '\n'
    updated = False
    for line in fileinput.input(hosts_file, inplace=True):
        if re.search(ip, line):
            if line.split()[0] == ip:
                log.info('Found IP {i} in line: {l}, updating...'.format(i=ip, l=line))
                log.info('Replacing with new line: {n}'.format(n=full_entry))
                sys.stdout.write(full_entry)
                updated = True
            else:
                log.debug('Found ip {i} in line {l} but not an exact match, adding line back to hosts file {f}...'.
                          format(i=ip, l=line, f=hosts_file))
                sys.stdout.write(line)
        else:
            log.debug('IP address {i} not found in line, adding line back to hosts file {f}: {l}'.format(
                    i=ip, l=line, f=hosts_file))
            sys.stdout.write(line)

    # Append the entry if the hosts file was not updated
    if updated is False:
        with open(hosts_file, 'a') as f:
            log.info('Appending hosts file entry to {f}: {e}'.format(f=hosts_file, e=full_entry))
            f.write(full_entry)


def set_hostname(new_hostname):
    """Sets this hosts hostname

    This method updates /etc/sysconfig/network and calls the hostname
    command to set a hostname on a Linux system.

    :param new_hostname: (str) New hostname
    :return int exit code of the hostname command
    :raises CommandError
    """
    log = logging.getLogger(mod_logger + '.set_hostname')

    # Ensure the hostname is a str
    if not isinstance(new_hostname, basestring):
        msg = 'new_hostname argument must be a string'
        log.error(msg)
        raise CommandError(msg)

    # Update the network config file
    network_file = '/etc/sysconfig/network'
    log.info('Updating %s with the new hostname: %s...', network_file,
             new_hostname)
    try:
        sed(network_file, '^HOSTNAME=.*', 'HOSTNAME=' + new_hostname)
    except CommandError:
        _, ex, trace = sys.exc_info()
        msg = 'Unable to update {f}\n{e}'.format(f=network_file, e=str(ex))
        log.error(msg)
        raise CommandError, msg, trace

    # Run the hostname command
    log.info('Running hostname command to set the hostname...')
    command = ['/bin/hostname', new_hostname]
    try:
        result = run_command(command)
    except CommandError:
        raise
    log.info('Hostname command completed with code: {c}'.format(
        c=result['code']))

    log.info('Writing new_hostname to /etc/hostname...')
    try:
        with open('/etc/hostname', 'w+') as h:
            h.write(new_hostname)
    except IOError as e:
        log.error('Failed to write new hostname to /etc/hostname.\nError: {}'.format(e))
        raise

def set_ntp_server(server):
    """Sets the NTP server on Linux

    :param server: (str) NTP server IP or hostname
    :return: None
    :raises CommandError
    """
    log = logging.getLogger(mod_logger + '.set_ntp_server')

    # Ensure the hostname is a str
    if not isinstance(server, basestring):
        msg = 'server argument must be a string'
        log.error(msg)
        raise CommandError(msg)
    # Ensure the ntp.conf file exists
    ntp_conf = '/etc/ntp.conf'
    if not os.path.isfile(ntp_conf):
        msg = 'File not found: {f}'.format(f=ntp_conf)
        log.error(msg)
        raise CommandError(msg)
    log.info('Clearing out existing server entries from %s...', ntp_conf)
    try:
        sed(ntp_conf, '^server.*', '', g=0)
    except CommandError:
        _, ex, trace = sys.exc_info()
        msg = 'Unable to update file: {f}\n{e}'.format(f=ntp_conf, e=str(ex))
        log.error(msg)
        raise CommandError, msg, trace
    out_str = 'server ' + server
    log.info('Appending server: %s', out_str)
    with open(ntp_conf, 'a') as f:
        f.write(out_str)
    log.info('Successfully updated file: {f}'.format(f=ntp_conf))


def copy_ifcfg_file(source_interface, dest_interface):
    """Copies an existing ifcfg network script to another

    :param source_interface: String (e.g. 1)
    :param dest_interface: String (e.g. 0:0)
    :return: None
    :raises TypeError, OSError
    """
    log = logging.getLogger(mod_logger + '.copy_ifcfg_file')
    # Validate args
    if not isinstance(source_interface, basestring):
        msg = 'source_interface argument must be a string'
        log.error(msg)
        raise TypeError(msg)
    if not isinstance(dest_interface, basestring):
        msg = 'dest_interface argument must be a string'
        log.error(msg)
        raise TypeError(msg)

    network_script = '/etc/sysconfig/network-scripts/ifcfg-eth'
    source_file = network_script + source_interface
    dest_file = network_script + dest_interface
    command = ['cp', '-f', source_file, dest_file]
    try:
        result = run_command(command)
        code = result['code']
    except CommandError:
        _, ex, trace = sys.exc_info()
        msg = 'Unable to copy the ifcfg file from interface {s} to interface {d}\n{e}'.format(
            s=source_interface, d=dest_interface, e=str(ex))
        raise OSError, msg, trace
    log.info('Copy command exited with code: {c}'.format(c=code))

    if code != 0:
        msg = 'There was a problem copying file {s} file to {d}'.format(s=source, d=dest_file)
        log.error(msg)
        raise OSError(msg)

    # Updating the destination network script DEVICE property
    try:
        sed(file_path=dest_file, pattern='^DEVICE=.*',
            replace_str='DEVICE="eth{i}"'.format(i=dest_interface))
    except CommandError:
        _, ex, trace = sys.exc_info()
        msg = 'Unable to update DEVICE in file: {d}\n{e}'.format(
            d=dest_file, e=str(ex))
        log.error(msg)
        raise CommandError, msg, trace
    log.info('Successfully created file: {d}'.format(d=dest_file))

    log.info('Restarting networking in 10 seconds to ensure the changes take effect...')
    time.sleep(10)
    retry_time = 10
    max_retries = 10
    for i in range(1, max_retries+2):
        if i > max_retries:
            msg = 'Unable to successfully start the networking service after {m} attempts'.format(m=max_retries)
            log.error(msg)
            raise OSError(msg)
        log.info('Attempting to restart the networking service, attempt #{i} of {m}'.format(i=i, m=max_retries))
        try:
            service_network_restart()
        except CommandError:
            _, ex, trace = sys.exc_info()
            log.warn('Attempted unsuccessfully to restart networking on attempt #{i} of {m}, trying again in {t} '
                     'seconds\n{e}'.format(i=i, m=max_retries, t=retry_time, e=str(ex)))
            time.sleep(retry_time)
        else:
            log.info('Successfully restarted networking')
            break
    log.info('Successfully configured interface: {d}'.format(d=dest_interface))


def remove_ifcfg_file(device_index='0'):
    """Removes the ifcfg file at the specified device index
    and restarts the network service

    :param device_index: (int) Device Index
    :return: None
    :raises CommandError
    """
    log = logging.getLogger(mod_logger + '.remove_ifcfg_file')
    if not isinstance(device_index, basestring):
        msg = 'device_index argument must be a string'
        log.error(msg)
        raise CommandError(msg)
    network_script = '/etc/sysconfig/network-scripts/ifcfg-eth{d}'.format(d=device_index)
    if not os.path.isfile(network_script):
        log.info('File does not exist, nothing will be removed: {n}'.format(n=network_script))
        return

    # Remove the network config script
    log.info('Attempting to remove file: {n}'.format(n=network_script))
    try:
        os.remove(network_script)
    except(IOError, OSError):
        _, ex, trace = sys.exc_info()
        msg = 'There was a problem removing network script file: {n}\n{e}'.format(n=network_script, e=str(ex))
        log.error(msg)
        raise OSError, msg, trace
    else:
        log.info('Successfully removed file: {n}'.format(n=network_script))

    # Restart the network service
    log.info('Restarting the network service...')
    try:
        service_network_restart()
    except CommandError:
        _, ex, trace = sys.exc_info()
        msg = 'There was a problem restarting the network service\n{e}'.format(e=str(ex))
        log.error(msg)
        raise OSError, msg, trace
    else:
        log.info('Successfully restarted the network service')


def add_nat_rule(port, source_interface, dest_interface):
    """Adds a NAT rule to iptables

    :param port: String or int port number
    :param source_interface: String (e.g. 1)
    :param dest_interface: String (e.g. 0:0)
    :return: None
    :raises: TypeError, OSError
    """
    log = logging.getLogger(mod_logger + '.add_nat_rule')
    # Validate args
    if not isinstance(source_interface, basestring):
        msg = 'source_interface argument must be a string'
        log.error(msg)
        raise TypeError(msg)
    if not isinstance(dest_interface, basestring):
        msg = 'dest_interface argument must be a string'
        log.error(msg)
        raise TypeError(msg)

    ip_addresses = get_ip_addresses()
    destination_ip = ip_addresses['eth{i}'.format(i=dest_interface)]
    log.info('Using destination IP address: {d}'.format(d=destination_ip))

    command = ['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i',
               'eth{s}'.format(s=source_interface), '-p', 'tcp',
               '--dport', str(port), '-j', 'DNAT', '--to',
               '{d}:{p}'.format(p=port, d=destination_ip)]
    log.info('Running command: {c}'.format(c=command))
    try:
        subprocess.check_call(command)
    except OSError:
        _, ex, trace = sys.exc_info()
        msg = 'There was a problem running command: {c}\n{e}'.format(c=command, e=str(ex))
        log.error(msg)
        raise OSError, msg, trace
    except subprocess.CalledProcessError:
        _, ex, trace = sys.exc_info()
        msg = 'Command returned a non-zero exit code: {c}\n{e}'.format(c=command, e=str(ex))
        log.error(msg)
        raise OSError, msg, trace
    else:
        log.info('Successfully ran command: {c}'.format(c=command))

    # Save the iptables with the new NAT rule
    command = ['/etc/init.d/iptables', 'save']
    log.info('Running command: {c}'.format(c=command))
    try:
        subprocess.check_call(command)
    except OSError:
        _, ex, trace = sys.exc_info()
        msg = 'There was a problem running command: {c}\n{e}'.format(c=command, e=str(ex))
        log.error(msg)
        raise OSError, msg, trace
    except subprocess.CalledProcessError:
        _, ex, trace = sys.exc_info()
        msg = 'Command returned a non-zero exit code: {c}\n{e}'.format(c=command, e=str(ex))
        log.error(msg)
        raise OSError, msg, trace
    else:
        log.info('Successfully ran command: {c}'.format(c=command))


def service_network_restart():
    """Restarts the network service on linux
    :return: None
    :raises CommandError
    """
    log = logging.getLogger(mod_logger + '.service_network_restart')
    command = ['service', 'network', 'restart']
    time.sleep(5)
    try:
        result = run_command(command)
        time.sleep(5)
        code = result['code']
    except CommandError:
        raise
    log.info('Network restart produced output:\n{o}'.format(o=result['output']))

    if code != 0:
        msg = 'Network services did not restart cleanly, exited with code: {c}'.format(c=code)
        log.error(msg)
        raise CommandError(msg)
    else:
        log.info('Successfully restarted networking!')


def get_remote_host_environment_variable(host, environment_variable):
    """Retrieves the value of an environment variable of a
    remote host over SSH

    :param host: (str) host to query
    :param environment_variable: (str) variable to query
    :return: (str) value of the environment variable
    :raises: TypeError, CommandError
    """
    log = logging.getLogger(mod_logger + '.get_remote_host_environment_variable')
    if not isinstance(host, basestring):
        msg = 'host argument must be a string'
        log.error(msg)
        raise TypeError(msg)
    if not isinstance(environment_variable, basestring):
        msg = 'environment_variable argument must be a string'
        log.error(msg)
        raise TypeError(msg)
    log.info('Checking host {h} for environment variable: {v}...'.format(h=host, v=environment_variable))
    command = ['ssh', '{h}'.format(h=host), 'echo ${v}'.format(v=environment_variable)]
    try:
        result = run_command(command, timeout_sec=5.0)
        code = result['code']
    except CommandError:
        raise
    if code != 0:
        msg = 'There was a problem checking the remote host {h} over SSH, return code: {c}'.format(
                h=host, c=code)
        log.error(msg)
        raise CommandError(msg)
    else:
        value = result['output'].strip()
        log.info('Environment variable {e} on host {h} value is: {v}'.format(
                e=environment_variable, h=host, v=value))
    return value


def set_remote_host_environment_variable(host, variable_name, variable_value, env_file='/etc/bashrc'):
    """Sets an environment variable on the remote host in the
    specified environment file

    :param host: (str) host to set environment variable on
    :param variable_name: (str) name of the variable
    :param variable_value: (str) value of the variable
    :param env_file: (str) full path to the environment file to set
    :return: None
    :raises: TypeError, CommandError
    """
    log = logging.getLogger(mod_logger + '.set_remote_host_environment_variable')
    if not isinstance(host, basestring):
        msg = 'host argument must be a string'
        log.error(msg)
        raise TypeError(msg)
    if not isinstance(variable_name, basestring):
        msg = 'variable_name argument must be a string'
        log.error(msg)
        raise TypeError(msg)
    if not isinstance(variable_value, basestring):
        msg = 'variable_value argument must be a string'
        log.error(msg)
        raise TypeError(msg)
    if not isinstance(env_file, basestring):
        msg = 'env_file argument must be a string'
        log.error(msg)
        raise TypeError(msg)
    log.info('Creating the environment file if it does not exist...')
    command = ['ssh', host, 'touch {f}'.format(f=env_file)]
    try:
        result = run_command(command, timeout_sec=5.0)
        code = result['code']
        output = result['output']
    except CommandError:
        raise
    if code != 0:
        msg = 'There was a problem creating environment file {f} on remote host {h} over SSH, ' \
              'exit code {c} and output:\n{o}'.format(h=host, c=code, f=env_file, o=output)
        log.error(msg)
        raise CommandError(msg)

    log.info('Creating ensuring the environment file is executable...')
    command = ['ssh', host, 'chmod +x {f}'.format(f=env_file)]
    try:
        result = run_command(command, timeout_sec=5.0)
        code = result['code']
        output = result['output']
    except CommandError:
        raise
    if code != 0:
        msg = 'There was a problem setting permissions on environment file {f} on remote host {h} over SSH, ' \
              'exit code {c} and output:\n{o}'.format(h=host, c=code, f=env_file, o=output)
        log.error(msg)
        raise CommandError(msg)

    log.info('Adding environment variable {v} with value {n} to file {f}...'.format(
            v=variable_name, n=variable_value, f=env_file))
    command = ['ssh', host, 'echo "export {v}=\\"{n}\\"" >> {f}'.format(f=env_file, v=variable_name, n=variable_value)]
    try:
        result = run_command(command, timeout_sec=5.0)
        code = result['code']
        output = result['output']
    except CommandError:
        raise
    if code != 0:
        msg = 'There was a problem adding variable {v} to environment file {f} on remote host {h} over SSH, ' \
              'exit code {c} and output:\n{o}'.format(h=host, c=code, f=env_file, o=output, v=variable_name)
        log.error(msg)
        raise CommandError(msg)
    else:
        log.info('Environment variable {v} set to {n} on host {h}'.format(v=variable_name, n=variable_value, h=host))


def check_remote_host_marker_file(host, file_path):
    """Queries a remote host over SSH to check for existence
    of a marker file

    :param host: (str) host to query
    :param file_path: (str) path to the marker file
    :return: (bool) True if the marker file exists
    :raises: TypeError, CommandError
    """
    log = logging.getLogger(mod_logger + '.check_remote_host_marker_file')
    if not isinstance(host, basestring):
        msg = 'host argument must be a string'
        log.error(msg)
        raise TypeError(msg)
    if not isinstance(file_path, basestring):
        msg = 'file_path argument must be a string'
        log.error(msg)
        raise TypeError(msg)
    log.debug('Checking host {h} for marker file: {f}...'.format(h=host, f=file_path))
    command = ['ssh', '{h}'.format(h=host), 'if [ -f {f} ] ; then exit 0 ; else exit 1 ; fi'.format(f=file_path)]
    try:
        result = run_command(command, timeout_sec=5.0)
        code = result['code']
        output = result['output']
    except CommandError:
        raise
    if code == 0:
        log.debug('Marker file <{f}> was found on host {h}'.format(f=file_path, h=host))
        return True
    elif code == 1 and output == '':
        log.debug('Marker file <{f}> was not found on host {h}'.format(f=file_path, h=host))
        return False
    else:
        msg = 'There was a problem checking the remote host {h} over SSH for marker file {f}, ' \
              'command returned code {c} and produced output: {o}'.format(
                h=host, f=file_path, c=code, o=output)
        log.debug(msg)
        raise CommandError(msg)


def create_remote_host_marker_file(host, file_path):
    """Creates a marker file on a remote host

    :param host: (str) host to create the file on
    :param file_path: (str) Full path for the file to create
    :return: None
    :raises: TypeError, CommandError
    """
    log = logging.getLogger(mod_logger + '.create_remote_host_marker_file')
    if not isinstance(host, basestring):
        msg = 'host argument must be a string'
        log.error(msg)
        raise TypeError(msg)
    if not isinstance(file_path, basestring):
        msg = 'file_path argument must be a string'
        log.error(msg)
        raise TypeError(msg)
    log.info('Attempting to create marker file {f} on host: {h}...'.format(f=file_path, h=host))
    command = ['ssh', '{h}'.format(h=host), 'touch {f}'.format(f=file_path)]
    try:
        result = run_command(command, timeout_sec=5.0)
        code = result['code']
        output = result['output']
    except CommandError:
        raise
    if code == 0:
        log.info('Marker file {f} successfully created on host {h}'.format(f=file_path, h=host))
    else:
        msg = 'There was a problem checking the remote host {h} over SSH for marker file {f}, ' \
              'command returned code {c} and produced output: {o}'.format(
                h=host, f=file_path, c=code, o=output)
        log.error(msg)
        raise CommandError(msg)


def restore_iptables(firewall_rules):
    """Restores and saves firewall rules from the firewall_rules file

    TODO: Remove this deprecated function, functionality moved to post-STIG asset

    :param firewall_rules: (str) Full path to the firewall rules file
    :return: None
    :raises OSError
    """
    log = logging.getLogger(mod_logger + '.restore_iptables')
    log.info('Restoring firewall rules from file: {f}'.format(f=firewall_rules))

    # Ensure the firewall rules file exists
    if not os.path.isfile(firewall_rules):
        msg = 'Unable to restore iptables, file not found: {f}'.format(f=firewall_rules)
        log.error(msg)
        raise OSError(msg)

    # Restore the firewall rules
    log.info('Restoring iptables from file: {f}'.format(f=firewall_rules))
    command = ['/sbin/iptables-restore', firewall_rules]
    try:
        result = run_command(command)
    except CommandError:
        _, ex, trace = sys.exc_info()
        msg = 'Unable to restore firewall rules from file: {f}\n{e}'.format(f=firewall_rules, e=str(ex))
        log.error(msg)
        raise OSError(msg)
    log.info('Restoring iptables produced output:\n{o}'.format(o=result['output']))

    # Save iptables
    log.info('Saving iptables...')
    command = ['/etc/init.d/iptables', 'save']
    try:
        result = run_command(command)
    except CommandError:
        _, ex, trace = sys.exc_info()
        msg = 'Unable to save firewall rules\n{e}'.format(e=str(ex))
        log.error(msg)
        raise OSError(msg)
    log.info('Saving iptables produced output:\n{o}'.format(o=result['output']))


def main():
    """Sample usage for this python module

    This main method simply illustrates sample usage for this python
    module.

    :return: None
    """
    # mkdir_p('/tmp/test/test')
    # source('/root/.bash_profile')
    # yum_install(['httpd', 'git'])
    # yum_install(['httpd', 'git'], dest_dir='/tmp/test/test', downloadonly=True)
    #sed('/Users/yennaco/Downloads/homer_testing/network', '^HOSTNAME.*', 'HOSTNAME=foo.joe')
    test_script = '/Users/yennaco/Downloads/homer/script.sh'
    results = run_command([test_script], timeout_sec=1000)
    #print 'run_command exited with code: {c}\n{o}'.format(c=results['code'], o=results['output'])


if __name__ == '__main__':
    main()
