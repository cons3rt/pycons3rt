#!/usr/bin/python

"""Module: nexus

This module provides simple method of fetching artifacts from a nexus
repository.

"""
import logging
import os
import requests

__author__ = 'Joe Yennaco'

# Set up logger name for this module
try:
    from logify import Logify
except ImportError:
    Logify = None
    mod_logger = 'nexus'
else:
    mod_logger = Logify.get_name() + '.nexus'

# Base URL for Jackpine Nexus
nexus_url = 'https://nexus.jackpinetech.com/nexus/service/local/artifact/maven/redirect'


def set_nexus_url(url):
    """Sets the Nexus URL to retrieve artifacts from

    This method sets the value of nexus_url, which is used for
    artifact retrieval.
    
    :param url: (str) URL of the Nexus repository
    :return: None
    """
    log = logging.getLogger(mod_logger + '.set_nexus_url')
    if not isinstance(url, basestring):
        msg = 'url argument is not a string'
        log.error(msg)
        raise TypeError(msg)
    global nexus_url
    log.info('Setting the Nexus URL to: %s', url)
    nexus_url = url


def get_artifact(**kwargs):
    """Retrieves an artifact from Nexus

    :param kwargs:
        group_id: (str) The artifact's Group ID in Nexus
        artifact_id: (str) The artifact's Artifact ID in Nexus
        packaging: (str) The artifact's packaging (e.g. war, zip)
        version: (str) Version of the artifact to retrieve (e.g.
            LATEST, 4.8.4, 4.9.0-SNAPSHOT)
        destination_dir: (str) Full path to the destination directory
        classifier: (str) The artifact's classifier (e.g. bin)
    :return:
    """
    log = logging.getLogger(mod_logger + '.get_artifact')

    required_args = ['group_id', 'artifact_id', 'packaging', 'version',
                     'destination_dir']

    # Ensure the required args are supplied, and that they are all strings
    for required_arg in required_args:
        try:
            assert required_arg in kwargs
        except AssertionError as e:
            log.error('A required arg was not supplied. Required args are: '
                      'group_id, artifact_id, classifier, version, '
                      'packaging and destination_dir\n%s', e)
            raise
        if not isinstance(kwargs[required_arg], basestring):
            msg = 'Arg {a} should be a string'.format(a=required_arg)
            log.error(msg)
            raise TypeError(msg)
        else:
            log.info('Found required arg %s set to: %s', required_arg,
                     kwargs[required_arg])

    # Set variables to be used in the REST call
    group_id = kwargs['group_id']
    artifact_id = kwargs['artifact_id']
    version = kwargs['version']
    packaging = kwargs['packaging']
    destination_dir = kwargs['destination_dir']
    classifier = None

    # Ensure the destination directory exists
    if not os.path.isdir(destination_dir):
        msg = 'Specified destination_dir not found on file system: {d}'.\
            format(d=destination_dir)
        log.error(msg)
        raise IOError(msg)
    else:
        log.info('Found destination directory: %s', destination_dir)

    # Set the classifier if it was provided
    if 'classifier' in kwargs:
        if isinstance(kwargs['classifier'], basestring):
            classifier = kwargs['classifier']
            log.info('Using classifier: %s', classifier)
        else:
            log.warn('Arg classifier provided but it was not an instance of '
                     'basestring')
    else:
        log.info('Optional arg classifier not provided')

    repo_test = version.lower().strip()
    log.info('Checking if the version %s is a release or snapshot...', repo_test)
    # Determine the repo based on the version
    if ('snapshot' in repo_test) or (repo_test == 'latest'):
        repo = 'snapshots'
    else:
        repo = 'releases'
    log.info('Using repo: %s', repo)

    # Construct the parameter string
    params = 'g=' + group_id + '&a=' + artifact_id + '&v=' + version + '&r=' + \
             repo + '&p=' + packaging

    # Add the classifier if it was provided
    if classifier is not None:
        params = params + '&c=' + classifier

    query_url = nexus_url + '?' + params
    log.info('Fetching artifact using URL:  %s', query_url)

    nexus_response = requests.get(query_url, stream=True)

    if nexus_response.status_code != 200:
        msg = 'Nexus request returned code {c}, unable to download from Nexus using query URL: {u}'.format(
            u=query_url, c=nexus_response.status_code)
        log.error(msg)
        raise RuntimeError(msg)

    # Download the content from the response
    file_name = nexus_response.url.split('/')[-1]
    download_file = destination_dir + '/' + file_name
    log.debug('Saving file: {d}'.format(d=download_file))
    with open(file_name, 'wb') as f:
        for chunk in nexus_response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    log.info('Saved file: {d}'.format(d=download_file))
    """
    try:
        nexus_response = urllib.urlopen(query_url)
    except(IOError, OSError) as e:
        msg = 'Unable to query URL: {u}\n{e}'.format(u=query_url, e=e)
        log.error(msg)
        raise OSError(msg)

    # Check the error code from Nexus
    if nexus_response.getcode() != 200:
        msg = 'Query returned code {c}, unable to download from Nexus using ' \
              'query URL: {u}'.format(u=query_url, c=nexus_response.getcode())
        log.error(msg)
        raise ValueError(msg)
    else:
        log.info('Query returned code 200!')


    # Pull data from Nexus response
    meta = nexus_response.info()
    actual_url = nexus_response.geturl()
    file_name = actual_url.split('/')[-1]
    file_size = int(meta.getheaders("Content-Length")[0])
    destination = destination_dir + '/' + file_name
    log.info('Actual Nexus download URL: %s', actual_url)
    log.info('Downloading filename: {f}, file size {s}, to destination {d}'.
             format(f=file_name, s=file_size, d=destination))
    log.info('File meta data:\n%s', meta)

    f = open(destination, 'wb')
    file_size_dl = 0
    block_sz = 8192
    while True:
        chunk = nexus_response.read(block_sz)
        if not chunk:
            break

        file_size_dl += len(chunk)
        f.write(chunk)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl *
                                       100. / file_size)
        status += chr(8)*(len(status)+1)
        # print status,
    f.close()
    """


def main():
    """Sample usage for this python module

    This main method simply illustrates sample usage for this python
    module.

    :return: None
    """
    log = logging.getLogger(mod_logger + '.main')
    try:
        get_artifact(group_id='com.cons3rt',
                     artifact_id='cons3rt-install',
                     version='4.9.0-SNAPSHOT',
                     classifier='bin',
                     packaging='zip',
                     destination_dir='/Users/yennaco/Downloads')
        get_artifact(group_id='com.cons3rt',
                     artifact_id='cons3rt-package',
                     version='4.9.0-SNAPSHOT',
                     packaging='zip',
                     destination_dir='/Users/yennaco/Downloads')
    except Exception as e:
        msg = 'Caught exception {name}, unable for download artifact from ' \
              'Nexus\n{s}'.format(name=e.__class__.__name__, s=e)
        log.error(msg)
        return


if __name__ == '__main__':
    main()
