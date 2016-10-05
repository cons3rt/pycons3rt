#!/usr/bin/python

"""Module: cons3rtutil

This module provides a set of utilities for sending CONS3RT CLI
commands.
"""
import sys
import os
import logging
import random
import string
import re

from logify import Logify
from bash import run_command
from bash import CommandError
import deployment

__author__ = 'Joe Yennaco'

# Set up logger name for this module
mod_logger = Logify.get_name() + '.cons3rtutil'

# Path to the cons3rt-otto.txt file
_secrets_file = '/root/cons3rt-otto.txt'


class Cons3rtUtilError(Exception):
    """This class is an Exception type for handling errors running
    CONS3RT CLI commands.
    """
    pass


class Cons3rtUtil(object):
    def __init__(self, cons3rt_fqdn, dep=None):
        self.cls_logger = mod_logger + '.Cons3rtUtil'
        log = logging.getLogger(self.cls_logger + '.__init__')
        self.dep = dep
        self.cons3rt_fqdn = cons3rt_fqdn
        self.secrets_file = _secrets_file
        # Determine cons3rt base
        if os.path.isdir('/app/cons3rt'):
            self.cons3rt_base = '/app'
        elif os.path.isdir('/opt/cons3rt'):
            self.cons3rt_base = '/opt'
        else:
            msg = 'Unable to determine CONS3RT_BASE'
            log.error(msg)
            raise Cons3rtUtilError(msg)

        # Validate deployment info provided and get it if needed
        if (dep is None) or (not isinstance(dep, deployment.Deployment)):
            try:
                self.dep = deployment.Deployment()
            except deployment.DeploymentError:
                _, ex, trace = sys.exc_info()
                msg = 'Could not get deployment info: {e}'.format(e=str(ex))
                log.error(msg)
                raise Cons3rtUtilError, msg, trace

        # Raise exception if not running on evergreen
        if self.dep.cons3rt_role_name != 'evergreen':
            msg = 'This host is not evergreen, Cons3rtUtil is designed to run ' \
                  'from the evergreen host'
            log.error(msg)
            raise Cons3rtUtilError(msg)

        # Get the admin user password
        log.info('Getting the admin CONS3RT user password...')
        self.admin_user = 'admin'
        self.admin_pass = ''
        if os.path.isfile(self.secrets_file):
            log.info('Reading file: {f}'.format(f=self.secrets_file))
            with open(self.secrets_file, 'r') as f:
                for line in f:
                    if line.startswith('ADMIN_PASS='):
                        self.admin_pass = line.split('=')[1].strip()
        else:
            msg = 'File not found: {f}'.format(f=self.secrets_file)
            raise Cons3rtUtilError(msg)
        if self.admin_pass == '':
            msg = 'Could not find a value for ADMIN_PASS'
            log.error(msg)
            raise Cons3rtUtilError(msg)
        self.rca = os.path.join(self.cons3rt_base, 'cons3rt', 'scripts', 'run_cons3rt_admin.sh')
        self.rsa = os.path.join(self.cons3rt_base, 'cons3rt', 'scripts', 'run_security_admin.sh')

    def run_cons3rt_command(self, command_string):
        """Runs a cons3rt CLI command string remotely on the cons3rt host

        :param command_string:
        :return: (dict) output of bash.run_command
        :raises: Cons3rtUtilError
        """
        log = logging.getLogger(self.cls_logger + '.run_cons3rt_command')

        command = ['ssh', 'cons3rt', command_string]

        # Run the run_security_admin.sh script to create the user
        log.debug('Running CONS3RT CLI Command: {d}'.format(d=command))
        try:
            result = run_command(command, timeout_sec=180)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'There was a problem running cons3rt CLI command: {c}\n{e}'.format(c=command_string, e=str(ex))
            raise Cons3rtUtilError, msg, trace
        if result['code'] != 0:
            msg = 'Running cons3rt CLI command [ {d} ] return non-zero exit code: {c}, and produced output:{o}'.format(
                d=command_string, c=result['code'], o=result['output'])
            log.error(msg)
            raise Cons3rtUtilError(msg)
        else:
            log.info('Successfully ran CONS3RT Command: {d}'.format(d=command_string))
        return result

    def run_security_admin_command(self, command_args):
        """Builds a command string for a run_security_admin.sh command

        :param command_args: (str) Args for the run_security_admin.sh command not including credentials
        :return: (dict) output of bash.run_command
        """
        log = logging.getLogger(self.cls_logger + '.run_security_admin_command')
        command_string = '{s} -adminuser {u} -adminpassword {p} {a}'.format(
            s=self.rsa, u=self.admin_user, p=self.admin_pass, a=command_args)
        log.debug('Created run_security_admin command string: {d}'.format(d=command_string))
        return self.run_cons3rt_command(command_string)

    def run_cons3rt_admin_command(self, command_args):
        """Builds a command string for a run_cons3rt_admin.sh command

        :param command_args: (str) Args for the run_cons3rt_admin.sh command not including credentials
        :return: (dict) output of bash.run_command
        """
        log = logging.getLogger(self.cls_logger + '.run_cons3rt_admin_command')
        command_string = '{s} -user {u} -password {p} {a}'.format(
            s=self.rca, u=self.admin_user, p=self.admin_pass, a=command_args)
        log.debug('Created run_security_admin command string: {d}'.format(d=command_string))
        return self.run_cons3rt_command(command_string)

    def get_cons3rt_users(self):
        """Queries CONS3RT for a list of users

        :return: (list) Containing user data
        :raises: Cons3rtUtilError
        """
        log = logging.getLogger(self.cls_logger + '.get_cons3rt_users')
        users = []
        log.debug('Running the command to get a list of CONS3RT users...')
        result = self.run_security_admin_command('-listusers')
        result_parts = re.split(r'\s{2,}', result['output'])
        if len(result_parts) < 6:
            log.info('No users found')
            return users
        result_parts = result_parts[5:]

        if len(result_parts) % 5 != 0:
            msg = 'Unable to compute a list of users from the output'
            log.error(msg)
            raise Cons3rtUtilError(msg)

        # Parse the output into sub-lists of length 5
        user_chunks = [result_parts[x:x+5] for x in xrange(0, len(result_parts), 5)]

        # Parse the list of User Info Chunks
        for user_chunk in user_chunks:
            user = {}
            if len(user_chunk) != 5:
                continue
            id_chunk = user_chunk[0].split(':')
            if len(id_chunk) != 2:
                continue
            user['id'] = id_chunk[0].strip()
            user['username'] = id_chunk[1].strip()
            user['state'] = user_chunk[1].replace(':', '').strip()
            user['certs'] = user_chunk[2].replace(':', '').strip()
            user['system_roles'] = user_chunk[3].strip()
            user['project_roles'] = user_chunk[4].strip()
            log.debug('Adding user to list: {u}'.format(u=user))
            users.append(user)
        return users

    def get_cons3rt_projects(self):
        """Queries CONS3RT for a list of projects

        :return: (list) of projects
        :raises: Cons3rtUtilError
        """
        log = logging.getLogger(self.cls_logger + '.get_cons3rt_projects')
        projects = []
        log.debug('Running the command to get a list of CONS3RT projects...')
        result = self.run_cons3rt_admin_command('-listprojects -terse')
        output = result['output'].replace('\n', '   ')
        result_parts = re.split(r'\s{2,}', output)
        if len(result_parts) < 9:
            log.info('No projects found')
            return projects
        result_parts = result_parts[7:]

        if len(result_parts) % 5 != 0:
            msg = 'Unable to compute a list of projects from the output'
            log.error(msg)
            raise Cons3rtUtilError(msg)

        # Parse the output into sub-lists of length 5
        project_chunks = [result_parts[x:x+5] for x in xrange(0, len(result_parts), 5)]

        # Parse the list of Project Info Chunks
        for project_chunk in project_chunks:
            project = {}
            if len(project_chunk) != 5:
                continue
            project['id'] = project_chunk[0].strip()
            project['name'] = project_chunk[1].replace(':', '').strip()
            project['description'] = project_chunk[2].strip()
            itar_info = project_chunk[3].split(':')
            if len(itar_info) != 3:
                project['itar'] = ''
                project['trustedProjects'] = ''
            else:
                project['itar'] = itar_info[1].strip()
                project['trustedProjects'] = itar_info[2].strip()
            project['members'] = project_chunk[4].replace(':', '').strip()
            log.debug('Adding project to list: {p}'.format(p=project))
            projects.append(project)
        return projects

    def create_user(self):
        """Creates a CONS3RT user for this CONS3RT instance based on
        the Deployment Run submitter

        :return: Dict containing username and password
        :raises: Cons3rtUtilError
        """
        log = logging.getLogger(self.cls_logger + '.create_user')
        log.info('Creating a CONS3RT user...')

        # Determine the username
        log.info('Determining username to use...')
        user = self.dep.get_value('cons3rt.user')
        if user is None:
            log.info('Using default username: homer')
            user = 'homer'
        else:
            log.info('Username: {u}'.format(u=user))

        # Check to see if the username already exists
        log.info('Checking if the username already exists...')
        user_exists = False
        cons3rt_users = self.get_cons3rt_users()
        for cons3rt_user in cons3rt_users:
            log.debug('Found user: {u}'.format(u=cons3rt_user['username']))
            if cons3rt_user['username'] == user:
                user_exists = True
                log.info('Username already exists: {u}'.format(u=user))
                break

        # Create a user if it does not exist
        if not user_exists:
            # Determine the email address
            log.info('Determining email address to use...')
            email = self.dep.get_value('cons3rt.user.email')
            if email is None:
                log.info('Using default email address: homer@jackpinetech.com')
                email = 'homer@jackpinetech.com'
            else:
                log.info('Email: {e}'.format(e=email))

            command_string = '-createuser {u} -email {e} -firstname Admin -lastname User'.format(u=user, e=email)
            self.run_security_admin_command(command_string)

        # Create a random password
        password = generate_cons3rt_password()
        log.info('Using password: {p}'.format(p=password))

        # Set the admin user's password
        command_string = '-setpassword {u} \'{p}\''.format(u=user, p=password)
        self.run_security_admin_command(command_string)

        log.info('Successfully created user {u} with password {p}'.format(u=user, p=password))
        result = {
            'username': user,
            'password': password
        }
        log.debug('Returning result: {r}'.format(r=result))
        return result

    def assign_system_role(self, user, role):
        """Assigns a CONS3RT system role to a CONS3RT user

        :param user: String CONS3RT username
        :param role: String CONS3RT system role
        :return: None
        :raises: Cons3rtUtilError
        """
        log = logging.getLogger(self.cls_logger + '.assign_system_role')
        if not isinstance(user, basestring):
            msg = 'user argument must be a string'
            log.error(msg)
            raise Cons3rtUtilError(msg)
        if not isinstance(role, basestring):
            msg = 'role argument must be a string'
            log.error(msg)
            raise Cons3rtUtilError(msg)
        log.info('Attempting to assign system role {r} to user: {u}'.format(
            r=role, u=user))

        command_string = '-assignsystemrole {u} {r}'.format(u=user, r=role)
        self.run_security_admin_command(command_string)
        log.info('Successfully assigned system role {r} to user {u}'.format(u=user, r=role))

    def create_project(self, project_name, description=''):
        """Creates a CONS3RT project with the specified name

        :param project_name: String name of the Project
        :param description: String description
        :return: None
        :raises: Cons3rtUtilError
        """
        log = logging.getLogger(self.cls_logger + '.assign_system_role')
        if not isinstance(project_name, basestring):
            msg = 'project_name argument must be a string'
            log.error(msg)
            raise Cons3rtUtilError(msg)

        log.info('Checking if the project already exists...')
        project_exists = False
        cons3rt_projects = self.get_cons3rt_projects()
        for cons3rt_project in cons3rt_projects:
            log.debug('Found CONS3RT Project: {p}'.format(p=cons3rt_project['name']))
            if cons3rt_project['name'] == project_name:
                project_exists = True
                log.info('Project already exists: {p}'.format(p=project_name))
                break

        # Create the new project if it does not exist
        if not project_exists:
            log.info('Attempting to create project with name: {p}'.format(p=project_name))
            command_string = '-createproject \'{p}\' -description \'{d}\''.format(p=project_name, d=description)
            self.run_security_admin_command(command_string)
            log.info('Created project: {p}'.format(p=project_name))

    def assign_project(self, user, project):
        """Assigns an existing CONS3RT user to a CONS3RT project

        :param user: String username
        :param project: String project name
        :return: None
        :raises: Cons3rtUtilError
        """
        log = logging.getLogger(self.cls_logger + '.assign_project')
        if not isinstance(user, basestring):
            msg = 'user argument must be a string'
            log.error(msg)
            raise Cons3rtUtilError(msg)
        if not isinstance(project, basestring):
            msg = 'project argument must be a string'
            log.error(msg)
            raise Cons3rtUtilError(msg)

        log.info('Attempting to assign user {u} to project {p}'.format(u=user, p=project))
        command_string = '-assignproject {u} \'{p}\''.format(u=user, p=project)
        self.run_security_admin_command(command_string)
        log.info('Successfully assigned user {u} to project {p}'.format(u=user, p=project))

    def get_project_id(self, project_name):
        """Returns the project ID given a project name

        :param project_name: String name of the project to get the ID
        :return: int ID of the CONS3RT project or None
        :raises Cons3rtUtilError
        """
        log = logging.getLogger(self.cls_logger + '.get_project_id')
        if not isinstance(project_name, basestring):
            msg = 'project_name argument must be a string'
            log.error(msg)
            raise Cons3rtUtilError(msg)

        projects = self.get_cons3rt_projects()
        log.debug('Found projects: {p}'.format(p=projects))

        # Find the project ID by name
        project_id = None
        for project in projects:
            if project_name == project['name']:
                project_id = project['id']
        log.info('Found project ID: {id}'.format(id=project_id))
        return project_id

    def generate_rest_key(self, user, project):
        """Assigns an ReST key to an existing CONS3RT user for a CONS3RT project

        :param user: String username
        :param project: String project name
        :return: String rest_key
        :raises: Cons3rtUtilError
        """
        log = logging.getLogger(self.cls_logger + '.generate_rest_key')
        if not isinstance(user, basestring):
            msg = 'user argument must be a string'
            log.error(msg)
            raise Cons3rtUtilError(msg)
        if not isinstance(project, basestring):
            msg = 'project argument must be a string'
            log.error(msg)
            raise Cons3rtUtilError(msg)

        log.info('Attempting to generate a rest key for user {u} in project {p}...'.format(u=user, p=project))
        command_string = '-requestapitoken {u} \'{p}\''.format(u=user, p=project)
        result = self.run_security_admin_command(command_string)
        rest_key = result['output'].split()[6]
        log.info('Successfully generated ReST key for user {u} in project {p}: {k}'.format(
            k=rest_key, u=user, p=project))
        return rest_key


def generate_cons3rt_password():
    """Creates a cons3rt password meeting the following requirements:

    CONS3RT Rules
    Password must be less than 17 and more than 7 characters in length
    Password can not be same as nor contain user name
    Password must contain at least one uppercase letter
    Password must contain at least one lowercase letter
    Password must contain at least one number
    Password must contain at least one special character

    DISA Rules
    Password must be more than 14 and less than 121 characters in length
    Password can not be same as nor contain user name
    Password must contain at least two uppercase letters
    Password must contain at least two lowercase letters
    Password must contain at least two numbers
    Password must contain at least two special characters

    :return: String password
    """
    log = logging.getLogger(mod_logger + '.generate_cons3rt_password')
    special_chars = '#$%&*@'
    upper1 = random.SystemRandom().choice(string.ascii_uppercase)
    upper2 = random.SystemRandom().choice(string.ascii_uppercase)
    lower1 = random.SystemRandom().choice(string.ascii_lowercase)
    lower2 = random.SystemRandom().choice(string.ascii_lowercase)
    special1 = random.SystemRandom().choice(special_chars)
    special2 = random.SystemRandom().choice(special_chars)
    digit1 = random.SystemRandom().choice(string.digits)
    digit2 = random.SystemRandom().choice(string.digits)
    bulk = ''.join(random.SystemRandom().choice(
        string.ascii_lowercase +
        string.ascii_uppercase +
        string.digits) for _ in range(8))
    pre_password = list(upper1 + upper2 + lower1 + lower2 + special1 +
                        special2 + digit1 + digit2 + bulk)

    password = []
    for i in range(len(pre_password)):
        pick = random.choice(pre_password)
        pre_password.remove(pick)
        password.append(pick)
    password = ''.join(password)
    log.info('Generated password: {p}'.format(p=password))
    return password


def main():
    """Sample usage for this python module
    :return: None

    log = logging.getLogger(mod_logger + '.main')
    log.info('Running main...')
    project = 'Doooonut'
    cons3rtutil = Cons3rtUtil(homer=homer)
    user_dict = cons3rtutil.create_user()
    cons3rtutil.assign_system_role(user=user_dict['username'], role='administrator')
    cons3rtutil.create_project(project_name=project, description='Default project for Homer')
    cons3rtutil.assign_project(user=user_dict['username'], project=project)
    generate_cons3rt_password()
    """
    pass


if __name__ == '__main__':
    main()
