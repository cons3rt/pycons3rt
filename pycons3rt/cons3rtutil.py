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

        self.rca = os.path.join('/net', 'cons3rt.{dn}'.format(dn=self.cons3rt_fqdn),
                                'cons3rt', 'scripts', 'run_cons3rt_admin.sh')
        self.rsa = os.path.join('/net', 'cons3rt.{dn}'.format(dn=self.cons3rt_fqdn),
                                'cons3rt', 'scripts', 'run_security_admin.sh')
        self.rym = os.path.join('/net', 'cons3rt.{dn}'.format(dn=self.cons3rt_fqdn),
                                'cons3rt', 'scripts', 'run_yaml_main.sh')
        if not os.path.isfile(self.rca) or not os.path.isfile(self.rsa):
            msg = 'CONS3RT scripts not found {c}, {s}'.format(c=self.rca,
                                                              s=self.rsa)
            log.error(msg)
            raise Cons3rtUtilError(msg)
        else:
            log.info('Found run_cons3rt_admin.sh and run_security_admin.sh scripts')

    def create_user(self):
        """Creates a CONS3RT user for this CONS3RT instance based on
        the Deployment Run submitter

        :return: Dict containing username and password
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

        # Determine the email address
        log.info('Determining email address to use...')
        email = self.dep.get_value('cons3rt.user.email')
        if email is None:
            log.info('Using default email address: homer@jackpinetech.com')
            email = 'homer@jackpinetech.com'
        else:
            log.info('Email: {e}'.format(e=email))

        # Create a random password
        password = generate_cons3rt_password()
        log.info('Using password: {p}'.format(p=password))

        command = [self.rsa, '-adminuser', 'admin', '-adminpassword',
                   self.admin_pass, '-createuser', user, '-email',
                   email, '-firstname', 'Homer', '-lastname', 'Simpson']

        # Run the run_security_admin.sh script to create the user
        try:
            result = run_command(command)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to create CONS3RT user'
            raise Cons3rtUtilError, msg, trace

        if result['code'] != 0:
            msg = 'Creating CONS3RT user produced the following output and ' \
                  'returned exit code: {c}\n{o}'.format(c=result['code'],
                                                        o=result['output'])
            log.error(msg)
            raise Cons3rtUtilError(msg)
        else:
            log.info('Successfully created the CONS3RT user\n{o}'.format(
                o=result['output']))

        command = [self.rsa, '-adminuser', 'admin', '-adminpassword',
                   self.admin_pass, '-setpassword', user, '{p}'.format(p=password)]

        # Run the run_security_admin.sh script to set the password
        try:
            result = run_command(command)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to set CONS3RT user password'
            log.error(msg)
            raise Cons3rtUtilError, msg, trace

        if result['code'] != 0:
            msg = 'Setting CONS3RT user password produced the following output ' \
                  'and returned exit code: {c}\n{o}'.format(c=result['code'],
                                                            o=result['output'])
            log.error(msg)
            raise Cons3rtUtilError(msg)
        else:
            log.info('Successfully set the CONS3RT user password\n{o}'.format(
                o=result['output']))

        log.info('Successfully created user {u} with password {p}'.format(
            u=user, p=password))
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

        command = [self.rsa, '-adminuser', 'admin', '-adminpassword',
                   self.admin_pass, '-assignsystemrole', user, role]

        # Assign system role to user
        try:
            result = run_command(command)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to assign system role {r} to user {u}'.format(
                r=role, u=user)
            log.error(msg)
            raise Cons3rtUtilError, msg, trace

        if result['code'] != 0:
            msg = 'Assigning system role {r} to user {u} produced the following ' \
                  'output and returned exit code: {c}\n{o}'.format(c=result['code'],
                                                                   o=result['output'],
                                                                   u=user, r=role)
            log.error(msg)
            raise Cons3rtUtilError(msg)
        else:
            log.info('Successfully assigned system role {r} to user {u}\n{o}'.format(
                o=result['output'], u=user, r=role))

    def create_project(self, project_name, description=''):
        """Creates a CONS3RT project with the specified name

        :param project_name: String name of the Project
        :param description: String description
        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.assign_system_role')
        if not isinstance(project_name, basestring):
            msg = 'project_name argument must be a string'
            log.error(msg)
            raise Cons3rtUtilError(msg)

        log.info('Attempting to create project with name: {p}'.format(
            p=project_name))

        command = [self.rsa, '-adminuser', 'admin', '-adminpassword', self.admin_pass,
                   '-createproject', project_name, '-description', description]

        # Create the project
        try:
            result = run_command(command)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to create project: {p}'.format(p=project_name)
            log.error(msg)
            raise Cons3rtUtilError, msg, trace

        if result['code'] != 0:
            msg = 'Creating project {p} produced the following output and ' \
                  'returned exit code: {c}\n{o}'.format(c=result['code'],
                                                        o=result['output'],
                                                        p=project_name)
            log.error(msg)
            raise Cons3rtUtilError(msg)
        else:
            log.info('Successfully created project {p}\n{o}'.format(
                o=result['output'], p=project_name))

    def assign_project(self, user, project):
        """Assigns an existing CONS3RT user to a CONS3RT project

        :param user: String username
        :param project: String project name
        :return: None
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

        log.info('Attempting to assign user {u} to project {p}'.format(
            u=user, p=project))

        command = [self.rsa, '-adminuser', 'admin', '-adminpassword', self.admin_pass,
                   '-assignproject', user, project]

        # Assign user to project
        try:
            result = run_command(command)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to assign user {u} to project {p}'.format(
                p=project, u=user)
            log.error(msg)
            raise Cons3rtUtilError, msg, trace

        if result['code'] != 0:
            msg = 'Adding user {u} to project {p} produced the following ' \
                  'output and returned exit code: {c}\n{o}'.format(c=result['code'],
                                                                   o=result['output'],
                                                                   u=user, p=project)
            log.error(msg)
            raise Cons3rtUtilError(msg)
        else:
            log.info('Successfully assigned user {u} to project {p}\n{o}'.format(
                o=result['output'], u=user, p=project))

    def get_project_id(self, project_name, admin_user=None, admin_pass=None):
        """Returns the project ID given a project name

        :param project_name: String name of the project to get the ID
        :param admin_user String username of the administrative user
        :param admin_pass String password for the administrative user
        :return: int ID of the CONS3RT project or None
        :raises Cons3rtUtilError
        """
        log = logging.getLogger(self.cls_logger + '.get_project_id')
        if not isinstance(project_name, basestring):
            msg = 'project_name argument must be a string'
            log.error(msg)
            raise Cons3rtUtilError(msg)

        if admin_user is None:
            admin_user = self.admin_user
        if admin_pass is None:
            admin_pass = self.admin_pass

        command = [self.rca, '-user', admin_user, '-password', admin_pass,
                   '-listprojects', '-terse']
        try:
            result = run_command(command)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to list projects to get the project ID'
            log.error(msg)
            raise Cons3rtUtilError, msg, trace

        if result['code'] != 0:
            msg = 'Listing projects produced the following output and returned ' \
                  'exit code: {c}\n{o}'.format(c=result['code'], o=result['output'])
            log.error(msg)
            raise Cons3rtUtilError(msg)

        projects = result['output'].split('\n')
        projects.pop(0)
        log.debug('Found projects: {p}'.format(p=projects))

        # Find the project ID by name
        project_id = None
        for project in projects:
            if project_name in project:
                project_id = project.split()[0].strip()
        log.info('Found project ID: {id}'.format(id=project_id))
        return project_id

    def get_cloudspace_id(self, cloudspace_name, admin_user=None,
                          admin_pass=None):
        """Returns the cloudspace ID given a cloudspace name

        :param cloudspace_name: String name of the cloudspace
        :param admin_user: String username of the administrative user
        :param admin_pass: String password for the administrative user
        :return: int ID of the Cloudspace or None
        :raises Cons3rtUtilError
        """
        log = logging.getLogger(self.cls_logger + '.get_cloudspace_id')
        if not isinstance(cloudspace_name, basestring):
            msg = 'cloudspace_name argument must be a string'
            log.error(msg)
            raise Cons3rtUtilError(msg)

        if admin_user is None:
            admin_user = self.admin_user
        if admin_pass is None:
            admin_pass = self.admin_pass

        command = [self.rca, '-user', admin_user, '-password', admin_pass,
                   '-listvirtrealms', '-terse']
        try:
            result = run_command(command)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to list cloudspaces to get the cloudspace ID'
            log.error(msg)
            raise Cons3rtUtilError, msg, trace

        if result['code'] != 0:
            msg = 'Listing cloudspaces produced the following output and returned ' \
                  'exit code: {c}\n{o}'.format(c=result['code'], o=result['output'])
            log.error(msg)
            raise Cons3rtUtilError(msg)

        cloudspaces = result['output'].split('\n')
        cloudspaces.pop(0)
        cloudspaces.remove('')

        log.debug('Found cloudspaces: {c}'.format(c=cloudspaces))

        cloudspace_id = None
        for cloudspace in cloudspaces:
            if cloudspace_name in cloudspace:
                cloudspace_id = cloudspace.split()[0].strip().translate(None, '.')
        log.info('Found Cloudspace ID: {id}'.format(id=cloudspace_id))
        return cloudspace_id

    def add_project_to_cloudspace(self, project_id, cloudspace_id,
                                  admin_user=None, admin_pass=None):
        """Adds the project ID to the provided Cloudspace ID

        :param project_id: int ID of the project
        :param cloudspace_id: int ID of the cloudspace
        :param admin_user:  String username of the administrative user
        :param admin_pass: String password for the administrative user
        :return: None
        :raises Cons3rtUtilError
        """
        log = logging.getLogger(self.cls_logger + '.add_project_to_cloudspace')
        try:
            project_id = int(project_id)
        except ValueError:
            msg = 'project_id argument must be an int'
            log.error(msg)
            raise Cons3rtUtilError(msg)
        try:
            cloudspace_id = int(cloudspace_id)
        except ValueError:
            msg = 'cloudspace_id argument must be an int'
            log.error(msg)
            raise Cons3rtUtilError(msg)

        if admin_user is None:
            admin_user = self.admin_user
        if admin_pass is None:
            admin_pass = self.admin_pass

        command = [self.rca, '-user', admin_user, '-password', admin_pass,
                   '-addprojecttovirtrealm', project_id, cloudspace_id]
        try:
            result = run_command(command)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to add project {p} to cloudspace {c}'.format(
                p=project_id, c=cloudspace_id)
            log.error(msg)
            raise Cons3rtUtilError, msg, trace

        if result['code'] != 0:
            msg = 'Adding project {p} to cloudspace {cs} produced the following output and returned exit code: ' \
                  '{c}\n{o}'.format(c=result['code'], o=result['output'], p=project_id, cs=cloudspace_id)
            log.error(msg)
            raise Cons3rtUtilError(msg)
        log.info('Successfully added project {p} to cloudspace {c}'.format(
            c=cloudspace_id, p=project_id))

    def set_default_cloudspace(self, project_id, cloudspace_id, admin_user=None, admin_pass=None):
        """Adds the Cloudspace ID as default for the provided Project
        ID

        :param project_id: int ID of the project
        :param cloudspace_id: int ID of the cloudspace
        :param admin_user:  String username of the administrative user
        :param admin_pass: String password for the administrative user
        :return: None
        :raises Cons3rtUtilError
        """
        log = logging.getLogger(self.cls_logger + '.set_default_cloudspace')
        try:
            project_id = int(project_id)
        except ValueError:
            msg = 'project_id argument must be an int'
            log.error(msg)
            raise Cons3rtUtilError(msg)
        try:
            cloudspace_id = int(cloudspace_id)
        except ValueError:
            msg = 'cloudspace_id argument must be an int'
            log.error(msg)
            raise Cons3rtUtilError(msg)

        if admin_user is None:
            admin_user = self.admin_user
        if admin_pass is None:
            admin_pass = self.admin_pass

        command = [self.rca, '-user', admin_user, '-password', admin_pass,
                   '-setdefaultvirtrealmforproject', project_id, cloudspace_id]
        try:
            result = run_command(command)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to set default cloudspace to {c} for project {p}'.format(
                p=project_id, c=cloudspace_id)
            log.error(msg)
            raise Cons3rtUtilError, msg, trace

        if result['code'] != 0:
            msg = 'Setting default cloudspace {cs} for project {p} produced the following output and returned exit ' \
                  'code: {c}\n{o}'.format(c=result['code'], o=result['output'], p=project_id, cs=cloudspace_id)
            log.error(msg)
            raise Cons3rtUtilError(msg)
        log.info('Successfully set cloudspace {c} as default for project {p}'.format(c=cloudspace_id, p=project_id))

    def run_yaml_main(self, project_name, asset_type, yaml_file, admin_user=None, admin_pass=None):
        """Runs a CONS3RT yaml import

        :param project_name: String Project Name
        :param asset_type: String asset type (e.g. CLOUD)
        :param yaml_file: String path to the yaml file to import
        :param admin_user: String username of the administrative user
        :param admin_pass: String password for the administrative user
        :return: None
        :raises Cons3rtUtilError
        """
        log = logging.getLogger(self.cls_logger + '.run_yaml_main')

        if not isinstance(project_name, basestring):
            msg = 'project_name argument must be a string'
            log.error(msg)
            raise Cons3rtUtilError(msg)
        if not isinstance(asset_type, basestring):
            msg = 'asset_type argument must be a string'
            log.error(msg)
            raise Cons3rtUtilError(msg)
        if not os.path.isfile(yaml_file):
            msg = 'File not found: {f}'.format(f=yaml_file)
            log.error(msg)
            raise Cons3rtUtilError(msg)
        if admin_user is None:
            admin_user = self.admin_user
        if admin_pass is None:
            admin_pass = self.admin_pass

        command = [self.rym, '-user', admin_user, '-password', admin_pass,
                   '-project', project_name, '-assetType', asset_type,
                   '-file', yaml_file, '-import']
        try:
            result = run_command(command)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable import from yaml file: {f}'.format(f=yaml_file)
            log.error(msg)
            raise Cons3rtUtilError, msg, trace

        if result['code'] != 0:
            msg = 'Importing yaml file {f} produced the following output and returned exit code: {c}\n{o}'.format(
                c=result['code'], o=result['output'], f=yaml_file)
            log.error(msg)
            raise Cons3rtUtilError(msg)
        log.info('Successfully imported yaml file: {f}'.format(f=yaml_file))

    def generate_rest_key(self, user, project):
        """Assigns an ReST key to an existing CONS3RT user for a CONS3RT project

        :param user: String username
        :param project: String project name
        :return: String rest_key
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

        log.info('Attempting to generate a rest key for user {u} in project {p}'.format(
                u=user, p=project))

        command = [self.rsa, '-adminuser', 'admin', '-adminpassword', self.admin_pass,
                   '-requestapitoken', user, project]

        # Generate ReST key
        try:
            result = run_command(command)
        except CommandError:
            _, ex, trace = sys.exc_info()
            msg = 'Unable to generate rest key for user {u} in project {p}'.format(
                    p=project, u=user)
            log.error(msg)
            raise Cons3rtUtilError, msg, trace

        if result['code'] != 0:
            msg = 'Generating rest key for {u} in project {p} produced the following ' \
                  'output and returned exit code: {c}\n{o}'.format(c=result['code'],
                                                                   o=result['output'],
                                                                   u=user, p=project)
            log.error(msg)
            raise Cons3rtUtilError(msg)
        else:
            rest_key = result['output'].split()[6]
            log.info('Successfully generated ReST key for user {u} in project {p}:\n{k}'.format(
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
