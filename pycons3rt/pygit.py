#!/usr/bin/python

"""Module: pygit

This module provides utilities for performing git operations

"""
import logging
import os
import sys
import time

from logify import Logify
from bash import run_command, CommandError, mkdir_p

__author__ = 'Joe Yennaco'


# Set up logger name for this module
mod_logger = Logify.get_name() + '.pygit'


class PyGitError(Exception):
    """Error encompassing problems that could be encountered while
    performing Git operations.
    """
    pass


def git_clone(url, clone_dir, branch='master', username=None, password=None, max_retries=10, retry_sec=30,
              git_cmd=None):
    """Clones a git url

    :param url: (str) Git URL in https or ssh
    :param clone_dir: (str) Path to the desired destination dir
    :param branch: (str) branch to clone
    :param username: (str) username for the git repo
    :param password: (str) password for the git repo
    :param max_retries: (int) the number of attempt to clone the git repo
    :param retry_sec: (int) number of seconds in between retries of the git clone
    :param git_cmd: (str) Path to git executable (required on Windows)
    :return: None
    :raises: PyGitError
    """
    log = logging.getLogger(mod_logger + '.git_clone')

    if not isinstance(url, basestring):
        msg = 'url arg must be a string'
        log.error(msg)
        raise PyGitError(msg)
    if not isinstance(clone_dir, basestring):
        msg = 'clone_dir arg must be a string'
        log.error(msg)
        raise PyGitError(msg)
    if not isinstance(max_retries, int):
        msg = 'max_retries arg must be an int'
        log.error(msg)
        raise PyGitError(msg)
    if not isinstance(retry_sec, int):
        msg = 'retry_sec arg must be an int'
        log.error(msg)
        raise PyGitError(msg)

    # Configure username/password if provided
    if url.startswith('https://') and username is not None and password is not None:
        stripped_url = str(url)[8:]
        log.info('Encoding password: {p}'.format(p=password))
        encoded_password = encode_password(password=password)
        clone_url = 'https://{u}:{p}@{v}'.format(u=username, p=encoded_password, v=stripped_url)
        log.info('Configured username/password for the GIT Clone URL: {u}'.format(u=url))
    else:
        clone_url = str(url)

    # Find the git command
    if git_cmd is None:
        log.info('Git executable not provided, attempting to determine (this will only work on *NIX platforms...')
        command = ['which', 'git']
        try:
            result = run_command(command)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to find the git executable\n{e}'.format(e=str(ex))
            log.error(msg)
            raise PyGitError, msg, trace
        else:
            git_cmd = result['output']

    if not os.path.isfile(git_cmd):
        msg = 'Could not find git command: {g}'.format(g=git_cmd)
        log.error(msg)
        raise PyGitError(msg)

    # Build a git clone or git pull command based on the existence of the clone directory
    if os.path.isdir(clone_dir):
        log.debug('Git repo directory already exists, updating repo in: {d}'.format(d=clone_dir))
        os.chdir(clone_dir)
        command = [git_cmd, 'pull']
    else:
        # Create a subdirectory to clone into
        log.debug('Creating the repo directory: {d}'.format(d=clone_dir))
        try:
            mkdir_p(clone_dir)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to create source directory: {d}\n{e}'.format(d=clone_dir, e=str(ex))
            log.error(msg)
            raise PyGitError, msg, trace

        # Create the git clone command
        command = [git_cmd, 'clone', '-b', branch, clone_url, clone_dir]

    # Run the git command
    log.info('Running git command: {c}'.format(c=command))
    for i in range(max_retries):
        attempt_num = i + 1
        log.info('Attempt #{n} to git clone the repository...'.format(n=attempt_num))
        try:
            result = run_command(command)
        except CommandError:
            _, ex, trace = sys.exc_info()
            log.warn('There was a problem running the git command: {c}\n{e}'.format(c=command, e=str(ex)))
        else:
            if result['code'] != 0:
                log.warn('The git command {g} failed and returned exit code: {c}\n{o}'.format(
                    g=command, c=result['code'], o=result['output']))
            else:
                log.info('Successfully cloned/updated GIT repo: {u}'.format(u=url))
                return
        if attempt_num == max_retries:
            msg = 'Attempted unsuccessfully to clone the git repo after {n} attempts'.format(n=attempt_num)
            log.error(msg)
            raise PyGitError(msg)
        log.info('Waiting to retry the git clone in {t} seconds...'.format(t=retry_sec))
        time.sleep(retry_sec)


def encode_password(password):
    """Performs URL encoding for passwords

    :param password: (str) password to encode
    :return: (str) encoded password
    """
    log = logging.getLogger(mod_logger + '.password_encoder')
    log.debug('Encoding password: {p}'.format(p=password))
    encoded_password = ''
    for c in password:
        encoded_password += encode_character(char=c)
    log.debug('Encoded password: {p}'.format(p=encoded_password))
    return encoded_password


def encode_character(char):
    """Returns URL encoding for a single character

    :param char (str) Single character to encode
    :returns (str) URL-encoded character
    """
    if char == '!': return '%21'
    elif char == '"': return '%22'
    elif char == '#': return '%23'
    elif char == '$': return '%24'
    elif char == '%': return '%25'
    elif char == '&': return '%26'
    elif char == '\'': return '%27'
    elif char == '(': return '%28'
    elif char == ')': return '%29'
    elif char == '*': return '%2A'
    elif char == '+': return '%2B'
    elif char == ',': return '%2C'
    elif char == '-': return '%2D'
    elif char == '.': return '%2E'
    elif char == '/': return '%2F'
    elif char == ':': return '%3A'
    elif char == ';': return '%3B'
    elif char == '<': return '%3C'
    elif char == '=': return '%3D'
    elif char == '>': return '%3E'
    elif char == '?': return '%3F'
    elif char == '@': return '%40'
    elif char == '[': return '%5B'
    elif char == '\\': return '%5C'
    elif char == ']': return '%5D'
    elif char == '^': return '%5E'
    elif char == '_': return '%5F'
    elif char == '`': return '%60'
    elif char == '{': return '%7B'
    elif char == '|': return '%7C'
    elif char == '}': return '%7D'
    elif char == '~': return '%7E'
    elif char == ' ': return '%7F'
    else: return char
