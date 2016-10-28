#!/usr/bin/python

"""Module: nexus

This module provides simple method of fetching artifacts from a nexus
repository.

"""
import logging
import os
import sys
import time
import argparse

import requests

from bash import mkdir_p, CommandError

__author__ = 'Joe Yennaco'

# Set up logger name for this module
try:
    from logify import Logify
except ImportError:
    Logify = None
    mod_logger = 'nexus'
else:
    mod_logger = Logify.get_name() + '.nexus'

# Sample Nexus URL
sample_nexus_url = 'https://nexus.jackpinetech.com/nexus/service/local/artifact/maven/redirect'

# Suppress warning for Python 2.6
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecurePlatformWarning)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.SNIMissingWarning)


def get_artifact(suppress_status=False, nexus_url=sample_nexus_url, timeout_sec=600, **kwargs):
    """Retrieves an artifact from Nexus

    :param suppress_status: (bool) Set to True to suppress printing download status
    :param nexus_url: (str) URL of the Nexus Server
    :param timeout_sec: (int) Number of seconds to wait before
        timing out the artifact retrieval.
    :param kwargs:
        group_id: (str) The artifact's Group ID in Nexus
        artifact_id: (str) The artifact's Artifact ID in Nexus
        packaging: (str) The artifact's packaging (e.g. war, zip)
        version: (str) Version of the artifact to retrieve (e.g.
            LATEST, 4.8.4, 4.9.0-SNAPSHOT)
        destination_dir: (str) Full path to the destination directory
        classifier: (str) The artifact's classifier (e.g. bin)
    :return: None
    :raises: TypeError, ValueError, OSError, RuntimeError
    """
    log = logging.getLogger(mod_logger + '.get_artifact')

    required_args = ['group_id', 'artifact_id', 'packaging', 'version', 'destination_dir']

    if not isinstance(nexus_url, basestring):
        msg = 'nexus_url arg must be a string'
        log.error(msg)
        raise TypeError(msg)
    else:
        log.debug('Using Nexus Server URL: {u}'.format(u=nexus_url))

    # Ensure the required args are supplied, and that they are all strings
    for required_arg in required_args:
        try:
            assert required_arg in kwargs
        except AssertionError:
            _, ex, trace = sys.exc_info()
            msg = 'A required arg was not supplied. Required args are: group_id, artifact_id, classifier, version, ' \
                  'packaging and destination_dir\n{e}'.format(e=str(ex))
            log.error(msg)
            raise ValueError(msg)
        if not isinstance(kwargs[required_arg], basestring):
            msg = 'Arg {a} should be a string'.format(a=required_arg)
            log.error(msg)
            raise TypeError(msg)

    # Set variables to be used in the REST call
    group_id = kwargs['group_id']
    artifact_id = kwargs['artifact_id']
    version = kwargs['version']
    packaging = kwargs['packaging']
    destination_dir = kwargs['destination_dir']

    # Ensure the destination directory exists
    if not os.path.isdir(destination_dir):
        log.debug('Specified destination_dir not found on file system, creating: {d}'.format(d=destination_dir))
        try:
            mkdir_p(destination_dir)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to create destination directory: {d}\n{e}'.format(d=destination_dir, e=str(ex))
            raise OSError(msg)

    # Set the classifier if it was provided
    classifier = None
    if 'classifier' in kwargs:
        if isinstance(kwargs['classifier'], basestring):
            classifier = kwargs['classifier']
            log.debug('Using classifier: {c}'.format(c=classifier))
        else:
            log.warn('Arg classifier provided but it was not an instance of basestring')

    # Set the repo if it was provided
    repo = None
    if 'repo' in kwargs:
        if isinstance(kwargs['repo'], basestring):
            repo = kwargs['repo']
            log.debug('Using repo: {r}'.format(r=repo))

    # Determine the repo based on the version
    if repo is None:
        repo_test = version.lower().strip()
        log.debug('Checking if the version {v} is a release or snapshot...'.format(v=repo_test))
        # Determine the repo based on the version
        if ('snapshot' in repo_test) or (repo_test == 'latest'):
            repo = 'snapshots'
        else:
            repo = 'releases'
        log.info('Based on the version {v}, determined repo: {r}'.format(v=version, r=repo))

    # Construct the parameter string
    params = 'g=' + group_id + '&a=' + artifact_id + '&v=' + version + '&r=' + repo + '&p=' + packaging

    # Add the classifier if it was provided
    if classifier is not None:
        params = params + '&c=' + classifier

    query_url = nexus_url + '?' + params
    log.info('Attempting to download the artifact using URL:  {u}'.format(u=query_url))

    # Attempt to download from Nexus
    retry_sec = 5
    max_retries = 6
    try_num = 1
    download_success = False
    nexus_response = None
    while try_num <= max_retries:
        if download_success:
            break
        log.debug('Attempt # {n} of {m} to download from Nexus URL: {u}'.format(n=try_num, u=query_url, m=max_retries))
        try:
            nexus_response = requests.get(query_url, stream=True, timeout=timeout_sec)
        except requests.exceptions.Timeout:
            _, ex, trace = sys.exc_info()
            msg = 'Caught {n} exception: Nexus download timed out after {t} seconds, retrying in {r} sec. Details:\n{e}'.format(
                n=ex.__class__.__name__, t=timeout_sec, r=retry_sec, e=str(ex))
            log.warn(msg)
            if try_num < max_retries:
                time.sleep(retry_sec)
        except requests.exceptions.RequestException:
            _, ex, trace = sys.exc_info()
            msg = 'Caught {n} exception: Nexus download failed with the following exception, retrying in {r} sec. ' \
                  'Details:\n{e}'.format(n=ex.__class__.__name__, r=retry_sec, e=str(ex))
            log.warn(msg)
            if try_num < max_retries:
                time.sleep(retry_sec)
        else:
            download_success = True
        try_num += 1

    if download_success is False:
        msg = 'Unable to download the artifact from Nexus with URL after {m} attempts: {u}'.format(
            u=query_url, m=max_retries)
        log.error(msg)
        raise RuntimeError(msg)

    if nexus_response.status_code != 200:
        msg = 'Nexus request returned code {c}, unable to download from Nexus using query URL: {u}'.format(
            u=query_url, c=nexus_response.status_code)
        log.error(msg)
        raise RuntimeError(msg)

    # Attempt to get the content-length
    file_size = 0
    try:
        file_size = int(nexus_response.headers['Content-Length'])
    except(KeyError, ValueError):
        log.debug('Could not get Content-Length, suppressing download status...')
        suppress_status = True
    else:
        log.info('Artifact file size: {s}'.format(s=file_size))

    # Check for an existing file
    file_name = nexus_response.url.split('/')[-1]
    download_file = os.path.join(destination_dir, file_name)
    if os.path.isfile(download_file):
        log.debug('File already exists, removing: {d}'.format(d=download_file))
        os.remove(download_file)

    # Download the content from the response
    log.debug('Attempting to save file: {d}'.format(d=download_file))
    chunk_size = 1024
    file_size_dl = 0
    with open(download_file, 'wb') as f:
        for chunk in nexus_response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                if not suppress_status:
                    file_size_dl += len(chunk)
                    status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
                    status += chr(8)*(len(status)+1)
                    print status,
    log.info('Saved file: {d}'.format(d=download_file))


def main():
    """Handles calling this module as a script

    :return: None
    """
    log = logging.getLogger(mod_logger + '.main')
    parser = argparse.ArgumentParser(description='This Python module retrieves artifacts from Nexus.')
    parser.add_argument('-u', '--url', help='Nexus Server URL', required=False)
    parser.add_argument('-g', '--groupId', help='Group ID', required=True)
    parser.add_argument('-a', '--artifactId', help='Artifact ID', required=True)
    parser.add_argument('-v', '--version', help='Artifact Version', required=True)
    parser.add_argument('-c', '--classifier', help='Artifact Classifier', required=False)
    parser.add_argument('-p', '--packaging', help='Artifact Packaging', required=True)
    parser.add_argument('-r', '--repo', help='Nexus repository name', required=False)
    parser.add_argument('-d', '--destinationDir', help='Directory to download to', required=True)
    args = parser.parse_args()
    try:
        get_artifact(
            nexus_url=args.url,
            group_id=args.groupId,
            artifact_id=args.artifactId,
            version=args.version,
            classifier=args.classifier,
            packaging=args.packaging,
            repo=args.repo,
            destination_dir=args.destinationDir)
    except Exception as e:
        msg = 'Caught exception {n}, unable for download artifact from Nexus\n{s}'.format(
            n=e.__class__.__name__, s=e)
        log.error(msg)
        return


if __name__ == '__main__':
    main()
