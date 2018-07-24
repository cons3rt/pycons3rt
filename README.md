# pycons3rt Python Library for CONS3RT Assets

## Features

* Gathers CONS3RT deployment info
* Runs Linux commands from python
* Configures networking on Linux
* Configuring AWS EC2 instance networking
* Downloads and uploads files to AWS S3
* Downloads files from a Nexus Artifact Repository
* Posts CONS3RT run info to Slack
* Establishes a logging infrastructure for python CONS3RT assets

## Installation

### Install from pip

If you have Python 2.7 installed, you can run:

`pip install pycons3rt`

Also you can install specific versions:

`pip install pycons3rt==0.0.2`

### Install from source

~~~
git clone https://github.com/cons3rt/pycons3rt
cd pycons3rt
python setup.py
~~~

### Install with CONS3RT assets

Search for community `pycons3rt` software assets in HmC or cons3rt.com to use.

To create your own pycons3rt assets, from the pycons3rt repo root directory, run:

    $ ./scripts/make-assets.sh

This will create your own Linux and Windows pycons3rt assets for import:

    ./build/asset-pycons3rt-linux.zip
    ./build/asset-pycons3rt-windows.zip

## Configuration

Once installed, run the following command to set up pycons3rt:

`pycons3rt_setup`

### Asset Prerequisites

1. Git
1. Python 2.7.x
1. pip

### Asset Exit Codes (Linux):

* 0 - Success
* Non-zero - See log file in /var/log/cons3rt/ for additional details

### Asset Exit Codes (Windows)

* 0 - Success
* 1 - Asset install failed:
  * pycons3rt install script not found, git clone may not have succeeded
  * There was a problem setting up pycons3rt
  * pycons3rt osutil not found
  * There was a problem running osutil


# pycons3rt documentation

## Configuration

When installed, pycons3rt creates a system directory (`pycons3rt_system_home`) and 
a local user directory (`pycons3rt_user_home`).  

The `pycons3rt_system_home` directory is located on your system here:

* Linux: `/etc/pycons3rt`
* MacOS: `~/.pycons3rt`
* Windows: `C:\pycons3rt`

The `pycons3rt_user_home` directory is here on all OS types:

* `~/.pycons3rt`

The following assets are also created:

* System pycons3rt config dir: `pycons3rt_system_home/conf/`
* User log dir (default): `pycons3rt_user_home/log/`
* Pycons3rt source dir: `pycons3rt_user_home/src/`

The asset clones the pycons3rt source code here for installation:

* `pycons3rt_user_home/src/pycons3rt`

The logging configuration file is installed here:

* `pycons3rt_system_home/conf/pycons3rt-logging.conf`

By default, pycons3rt log files will output here:

* `pycons3rt_user_home/log/pycons3rt-info.log`
* `pycons3rt_user_home/log/pycons3rt-warn.log`
* `pycons3rt_user_home/log/pycons3rt-debug.log`

## Logify

With the default configuration log files go to: `~/.pycons3rt/log/`, and INFO 
level is printed to stdout.  To customize pycons3rt logging, modify the 
`pycons3rt-logging.conf` file.

~~~
import logging
from pycons3rt.logify import Logify

mod_logger = Logify.get_name() + '.your_module'
    
    # Then use in a function or class:
    
    class MyClass(object):
        def __init__(self, dep=None):
            self.cls_logger = mod_logger + '.MyCLass'
    	def class_method(self):
    		log = logging.getLogger(self.cls_logger + '.class_method')
    		log.info('Class Method Logging')
    
    def main():
        log = logging.getLogger(mod_logger + '.main')
        log.debug('DEBUG')
    	log.info('INFO')
    	log.warn('WARN')
    	log.error('ERROR')
~~~

Deployment
---

This module provides a set of useful utilities for accessing CONS3RT
deployment related info. It is intended to be imported and used in
other python-based CONS3RT assets.

~~~
from pycons3rt.deployment import Deployment
    
# Create a new Deployment object
dep = new Deployment()
    
# Deployment name
print(dep.deployment_name)
    
# Get the role name
print(dep.cons3rt_role_name)
    
# Deployment properties
print(dep.properties)
    
# Get a specific deployment property value by name
my_value = dep.get_value('cons3rt.user')
    
# Scenario network info
print(dep.scenario_network_info)

# ASSET_DIR
print(dep.asset_dir)
~~~

Slack
---

This module provides an interface for posting anything to Slack!

~~~
from pycons3rt.slack import SlackMessage
from pycons3rt.slack import SlackAttachments

# Create a message
slack_msg = SlackMessage(
                my_webhook_url, 
                channel='#DevOps', 
                icon_url='http://cool-icon-url',
                text='This is a Slack message',
                user='@sender_username')

# Create and add an attachment
slack_attachment = SlackAttachment(
                       fallback='This is the fallback text', 
                       color='green', 
                       pretext='Pretext', 
                       text='Moar text!')

slack_msg.add_attachment(slack_attachment)

# Send a message
slack_msg.send()
~~~

## Nexus

This module provides simple method of fetching artifacts from a nexus
repository.

~~~
from pycons3rt import nexus

nexus.get_artifact(
    username=nexus_username,
    password=nexus_password,
    suppress_status=True,
    nexus_url=nexus_url,
    timeout_sec=45,
    overwrite=False,
    group_id='com.cons3rt',
    artifact_id='cons3rt-backend-install',
    version=`18.11.1`,
    packaging='zip',
    classifier='package-otto',
    destination_dir=dest_dir)
~~~

## Bash (Linux)

Executes commands on a Linux system.  See the source code for specific available
commands but the most commonly used `run_command` is shown below.

### run_command(command, timeout_sec=3600.0, output=True)

Parameters

* command: List containing the command and any additional args
* timeout_sec: (optional) Float specifying how long to wait before 
terminating the command.  Default is 3600.0.
* output: (boolean) True collects the output of the command.  In some cases
supressing the command output improves stability.

Returns:

* A dictionary containing "code", the numeric exit code from the command, and 
"output" which captures the stdout/strerrif output was set `True`. Sample output:

Raises: `CommandError` when there is a problem running the command.

~~~
{
    "code": "0",
    "output": "stdout/stderr from the command"
}
~~~

Example Usage:

~~~
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
~~~



## Alias IP (Linux)

Utility for setting IP address aliases in Linux.

## Cons3rtUtil

Utility for running CONS3RT CLI commands.  Only useful for CONS3RT site 
administrators with CLI access.

## OsUtil

Handles the initial pycons3rt configuration based on the detected OS type.

## PyGit

Utility for cloning a git repo from python.

## PyJavaKeys

Utility for importing Root Certificate Authority (CA) certificates into a 
Java keystore.

## Windows

Basic Windows utlities like adding host file entries.