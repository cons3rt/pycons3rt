#!/usr/bin/env python

import os
import sys
import logging
from pycons3rt.logify import Logify
from pycons3rt.bash import run_command, CommandError

__author__ = 'Mac <mac@lokilabs.io>'
__version__ = '0.20161029'

mod_logger = Logify.get_name() + '.utilities'

def install_jvmCerts(self,certPath=None,caStore=None,jhome=None):
    """Will install all .crt/.pem files from certPath into
    caStore location.
    
    :param certPath: (str) path to directory containing certs
    :param caStore: (str) path to java ca store
    :param jhome: (str) Path to java root
    :return: NONE
    """
    log = logging.getLogger(self.cls_logger + '.install_jvmCerts')
    if not
    try:
        jhome = os.environ['JAVA_HOME']
    except KeyError as e:
        log.warn('JAVA_HOME is not set in the environment.')
    if not jhome:
        try:
            with open('/etc/profile.d/java.sh', 'r') as java:
                for line in java.readlines():
                    if re.search('export JAVA_HOME', line):
                        jhome = line.split('=')[1].rstrip('\n')
        except:
            log.warn('Failed to fine JAVA_HOME in profile.d. Defaulting.')
            jhome = '/usr/java/latest'

    if not caStore:
        caStore = '{}/lib/security/cacerts'.format(jhome) 
    if not certPath:
        log.error('Path to certificates not defined.')
        return

    key_dir = certPath
    os.chdir(key_dir)
    log.info('CHDIR to {}'.format(key_dir))
    for cert in os.listdir('.'):
        try:
            if cert.endswith('.crt') or cert.endswith('.pem'):
                log.info('Importing cert {} into java keystore.'.format(cert))
                cmd = ['{}/bin/keytool'.format(jhome),'-import','-noprompt','-storepass',
                'changeit','-trustcacerts','-file','{}'.format(cert),'-alias',
                '{}'.format(cert[:-4]),'-keystore',caStore]
                run_cmd(cmd,log)
        except bash.CommandError: 
            log.error('Failed to import cert {}.'.format(cert))

def run_cmd(command,log,error=True,ret=False):
    """Command wrapper for pycons3rt run_command.
    Pass command as string or list, and the logging function.

    :param command: (str,list) Command to run
    :param log: (obj) Log object for calling function
    :param error: (boolean) Raise error. True or False 
    :param ret: (boolean) If set true, will return output and code
    :return: By default, none. Ret set true, code and output
    """

    if isinstance(command,list):
        pass
    elif isinstance(command,basestring):
        command = command.split()
    else:
        log.error('Command is not a list or string. Good job at being bad.')

    try:
        result = bash.run_command(command, timeout_sec=60.0)
        code = result['code']
        output = result['output']
    except bash.CommandError:
        if error: 
            raise

    if code == 0:
        log.info('Successfully executed command {c}'.format(c=command))
        if ret:
            return c, o
    else:
        msg = 'There was a problem running command: {cmd} Return code {c} and produced output: {o}'.format(
        c=code, o=output, cmd=command)
        log.error(msg)
        if error: 
            raise bash.CommandError(msg)

if __name__ == '__main__':
    sys.exit('Pycons3rt Library File. Should not be called directly.')