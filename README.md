# pycons3rt Python Library for CONS3RT Assets

Features
--------

- Utilities for gathering CONS3RT deployment info
- Utilities for running bash commands form python
- Utilities for configuring networking on Linux and on AWS
- A utility for downloading files from Nexus Artifact Repository
- A utility for posting to Slack


pycons3rt Assets
---

To create the pycons3rt assets, from the pycons3rt repo root directory, run:

    $ ./scripts/make-assets.sh

This will create the Linux and Windows assets here:

    ./build/asset-pycons3rt-linux.zip
    ./build/asset-pycons3rt-windows.zip

#### Asset Prerequisites

1. Python (already installed on most Linux distros)
1. Git

#### Asset Exit Codes (Linux):

* 0 - Success
* 1 - Could not determine DEPLOYMENT_HOME
* 2 - deployment properties file not found
* 3 - Unable to resolve GIT server domain name
* 4 - Unable to clone git repo after 10 attempts
* 5 - There was a problem installing prerequisites for pycons3rt
* 6 - pycons3rt install file not found, src may not have been checked out or staged correctly
* 7 - pycons3rt install did not complete successfully 
* 8 - Non-zero exit code found, see the cons3rt agent log for more details

#### Asset Exit Codes (Windows)

1. TBD


# pycons3rt library documentation


Deployment
---

This module provides a set of useful utilities for accessing CONS3RT
deployment related info. It is intended to be imported and used in
other python-based CONS3RT assets.

To use the deployment module: ::

    from pycons3rt.deployment import Deployment
    from pycons3rt.deployment import DeploymentError
    dep = new Deployment()
    print dep.cons3rt_role_name()
    print dep.get_value('cons3rt.user')

## Members

* cons3rt_role_name: (str) Set to CONS3RT_ROLE_NAME defined by CONS3RT
* properties: (dict) Deployment property name/value pairs
* deployment_home: (str) Set to DEPLOYMENT_HOME defined by CONS3RT
* properties_file: (str) Full path to the deployment properties file used
* asset_dir: (str) Full path to the ASSET_DIR defined by CONS3RT

## Methods

### get_property(self, regex)

This public method is passed a regular expression and
returns the matching property name. If either the property
is not found or if the passed string matches more than one
property, this function will return None.

Parameters:
* regex: Regular expression to search on

Returns:
* (str) Property name matching the passed regex or None

Example usage:

    ip_address_prop = dep.get_property('cons3rt.fap.deployment.machine.*.externalIp')

### get_value(self, property_name)

This public method is passed a specific property as a string
and returns the value of that property. If the property is not
found, None will be returned.

Parameters:
* _prop (str) The name of the property

Returns:
* (str) value for the passed property, or None

Example usage:

    cons3rt_user = dep.get_value('cons3rt.user')
        

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


Slack
---

This module provides an interface for posting to Slack!

Example usage:

    from pycons3rt.slack import SlackMessage
    from pycons3rt.slack import SlackAttachments
    slack_msg = SlackMessage(my_webhook_url, channel='#DevOps', icon_url='http://cool-icon-url', text='This is a Slack message')
    slack_attachment = SlackAttachment(fallback='This is the fallback text', color='green', pretext='Pretext', text='Moar text!')
    slack_msg.add_attachment(slack_attachment)
    slack_msg.send()

### SlackMessage(self, webhook_url, text, **kwargs)

Parameters:
* webhook_url: (str) Webhook URL provided by Slack
* text: (str) Text to send in the Slack message
* user: (str) Slack sender
* channel: (str) Slack channel name
* icon_url: (str) URL to the icon to use in the Slack message
* icon_emoji: (str) URL to the icon emoji to use in the Slack message

#### add_attachment(self, attachment)

Adds an attachment to the SlackMessage payload

Parameters:
* attachment: SlackAttachment object

Returns: None

#### send(self)

This public method sends the Slack message along with any
attachments, then clears the attachments array.

### SlackAttachment(self, fallback, **kwargs)

This class is used to create an attachment for a Slack post.

Parameters:
* fallback: (str) Attachment text to be used as the fallback
* kwargs Slack attachment options:
  * color
  * pretext
  * author_name
  * author_link
  * author_icon
  * title
  * title_link
  * text
  * image_url
  * thumb_url

Nexus
---

This module provides simple method of fetching artifacts from a nexus
repository.

## Methods

### get_artifact(**kwargs)

Retrieves an artifact from Nexus

Parameters:
* group_id: (str) The artifact's Group ID in Nexus
* artifact_id: (str) The artifact's Artifact ID in Nexus
* packaging: (str) The artifact's packaging (e.g. war, zip)
* version: (str) Version of the artifact to retrieve (e.g. LATEST, 4.8.4, 4.9.0-SNAPSHOT)
* classifier: (str) The artifact's classifier (e.g. bin)
* destination_dir: (str) Full path to the destination directory

Returns: None

Raises: OSError, TypeError, ValueError

Example usage:

    from pycons3rt.nexus import get_artifact
    get_artifact(group_id='com.cons3rt',
                  artifact_id='cons3rt-install',
                  version='4.9.0-SNAPSHOT',
                  classifier='bin',
                  packaging='zip',
                  destination_dir='/Users/yennaco/Downloads')

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

### yum_install(packages, downloadonly=False, dest_dir='/tmp')

Runs the "yum install" command on RHEL-based Linux to install the list of provided packages.

Parameters:
* downloadonly: Boolean, set to only download the package and not install it
* packages: List of package names (str) to download param
* dest_dir: (str) Full path to the download directory.  This will only be used if downloadonly is True.

Returns:
* int exit code from the yum command

Raises: CommandError

Example usage:

    from pycons3rt.bash import yum_install
    from pycons3rt.bash import CommandError
    try:
        yum_install(['emacs', 'vim', 'httpd'])
    except CommandError:
        raise
        
### rpm_install(install_dir)

Runs the "rpm" command to install all RPM files in the specified directory.

Parameters:
* install_dir: (str) Full path to the directory

Returns: 
* int exit code form the rpm command

Raises: CommandError

### sed(file_path, pattern, replace_str, g=0)

Python impl of the bash sed command

Parameters:
* file_path: (str) Full path to the file to be edited
* pattern: (str) Search pattern to replace as a regex
* replace_str: (str) String to replace the pattern
* g: (int) Whether to globally replace (0) or replace 1 instance (equivalent to the 'g' option in bash sed)

Returns: None

Raises: CommandError

Example usage:

    import re
    from pycons3rt.bash import sed
    from pycons3rt.bash import CommandError
    try:
        sed('/etc/sysconfig/hostname', '^HOSTNAME=.*', 'HOSTNAME=' + 'MyCoolHostName')
    except CommandError:
        _, ex, trace = sys.exc_info()
        msg = 'Unable to update {f}\n{e}'.format(f=network_file, e=str(ex))
        log.error(msg)
        raise CommandError, msg, trace

### zip_dir(dir_path, zip_file)


### get_ip(interface=0)


### update_hosts_file(ip, entry)


### set_hostname(new_hostname)


### set_ntp_server(server)


### copy_ifcfg_file(source_interface, dest_interface)


### remove_ifcfg_file(device_index='0')


### add_nat_rule(port, source_interface, dest_interface)


### service_network_restart()


### get_remote_host_environment_variable(host, environment_variable)


### set_remote_host_environment_variable(host, variable_name, variable_value, env_file='/etc/bashrc')


### check_remote_host_marker_file(host, file_path)


### create_remote_host_marker_file(host, file_path)


### restore_iptables(firewall_rules)


### git_clone(repo_url, dest_dir)
