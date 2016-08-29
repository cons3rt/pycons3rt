# pycons3rt Python Library for CONS3RT Assets

Installs the pycons3rt library into the local Python.

Features
--------

- Utilities for gathering CONS3RT deployment info
- Utilities for running bash commands form python
- Utilities for configuring networking on Linux and on AWS
- A utility for downloading files from Nexus Artifact Repository
- A utility for posting to Slack


Deployment
---

To use the deployment module: ::

    from pycons3rt import deployment
    mydeployment = new deployment.Deployment()
    print mydeployment.cons3rt_role_name()
    print mydeployment.get_value('cons3rt.user')

Logify
---

To use the Logging framework Logify: ::

    import logging
    from pycons3rt.logify import Logify

Set up a Module logger:

    mod_logger = Logify.get_name() + '.module_name'
    log = logging.getLogger(mod_logger)
    
Set up a Class logger: 
    
    self.cls_logger = mod_logger + '.ClassName'
    log = logging.getLogger(self.cls_logger)

Set up a Class Method logger:
    
    log = logging.getLogger(self.cls_logger + '.method_name')

Use the logging framework: 
 
    log.debug('This is a line of DEBUG')
    log.info('This is a line of INFO')
    log.warn('This is a line of WARN')
    log.error('This is a line of ERROR')

Log files are output to ~/.cons3rt/log, and INFO level is printed to stdout.

Bash (Linux)
---

### run_command(command, timeout_sec=3600.0)

Runs any linux command on a Linux System.

Parameters
* command: List containing the command and any additional args
* timeout_sec: (optional) Float specifying how long to wait before terminating the command.  Default is 3600.0.

Returns:
* Dict containing "code", the numeric exit code from the command, and "output" which captures the stdout/strerr. Sample output:


    {
        "code": "0",
        "output": "stdout/stderr from the command"
    }

Example Usage:


    from pycons3rt.bash import run_command
    from pycons3rt.bash import CommandError
    command = ['ls', '/root']
    try:
        result = run_command(command, timeout_sec=60.0)
        code = result['code']
        output = result['output']
    except CommandError:
        raise
    if code == 0:
        log.info('Successfully executed command {c}'.format(s=command))
    else:
        msg = 'There was a problem running command returned code {c} and produced output: {o}'.format(
                        c=code, o=output)
                log.error(msg)
                raise CommandError(msg)
        
### get_ip_addresses()

Uses ifconfig to return a list of IP addresses configured on the Linux system

Parameters: None

Returns:
* Dict containing the device number and the ip address.  Sample output:


    {
        "eth0": "192.168.2.1",
        "eth0:0": "192.168.3.1"
        "eth1": "192.168.4.5"
    }

Example Usage:

    from pycons3rt.bash import get_ip_addresses
    my_ip_address = get_ip_addresses()['eth{0}']

### get_mac_address(device_index=0)

Returns the Mac Address given a device index

Parameters:
* device_index: int of the Device index.  Default is 0.

Returns:
* String mac address, or None if not found

Example usage:

    from pycons3rt.bash import get_mac_address
    my_mac_address = get_mac_address(device_index=0)

### chmod(path, mode, recursive=False)

Sets permissions on a file, directory, or recursively on a directory structure.

Parameters:
* path: (str) Full path to the file or directory
* mode: (str) Mode to be set (e.g. 0755)
* recursive: (bool) Set True to make a recursive call

Returns:
* int exit code of the chmod command

Raises: CommandError

Example usage:

    from pycons3rt.bash import chmod
    result = chmod('/path/to/file', '755')

### mkdir_p(path)

Emulates "mkdir -p /path/to/dir" command in Linux. Recursively creates a directory structure if the parent directories do not exist.

Parameters:
* path: (str) Path to directory to create

Returns: None

Raises: CommandError

Example usage:

    from pycons3rt.bash import mkdir_p
    from pycons3rt.bash import CommandError
    try:
        mkdir_p('/path/to/my/new/directory')
    except CommandError:
        raise

### source(script)

Reads in (or "sources") a linux file or script and makes the variables available in the current shell.

Parameters:
* script: (str) Full path to the script to source

Returns:
* Updated environment (e.g. os.environ)

Raises: CommandError

Example usage:

    import os
    from pycons3rt.bash import source
    from pycons3rt.bash import CommandError
    # Print the environment before sourcing
    print os.environ
    try:
        source('/path/to/file/to/source')
    except CommandError:
        raise
    # Print the environment after sourcing
    print os.environ

### yum_update(downloadonly=False, dest_dir='/tmp')

Runs the "yum update" command on RHEL-based Linux.

Parameters:
* downloadonly: Boolean to specify whether to install or only download updated packages.
* dest_dir: (str) Full path to the download directory.  This will only be used if downloadonly is True.

Returns:
* int exit code from the yum command

Raises: CommandError

Example usage:

    from pycons3rt.bash import yum_update
    from pycons3rt.bash import CommandError
    try:
        yum_update()
    except CommandError:
        raise

### 