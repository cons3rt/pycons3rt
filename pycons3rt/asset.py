#!/usr/bin/env python

"""Module: asset

This module provides utilities for creating asset zip files.

"""
import logging
import os
import sys
import zipfile
import contextlib

from logify import Logify
from bash import mkdir_p

__author__ = 'Joe Yennaco'


# Set up logger name for this module
mod_logger = Logify.get_name() + '.asset'

# Files to ignore when creating assets
ignore_files = [
    '.DS_Store',
    '.gitignore',
    '._'
]

# Directories to ignore when creating assets
ignore_dirs = [
    '.git',
    '.svn',
    '.cons3rt'
]

# Acceptable items at the asset root
acceptable_items = [
    'asset.properties',
    'scripts',
    'media',
    'config',
    'README',
    'HELP',
    'LICENSE',
    'HELP.md',
    'README.md',
    'LICENSE.md'
]

# Acceptable dirs at the root
acceptable_dirs = [
    'scripts',
    'media',
    'config'
]

# Items to warn about
warn_items = [
    'HELP.html',
    'README.html',
    'LICENSE.html'
]

potential_doc_files = [
    'HELP.html',
    'README.html',
    'HELP',
    'README',
    'HELP.md',
    'README.md',
    'ALTERNATE_README'
]

potential_license_files = [
    'LICENSE.html',
    'LICENSE',
    'LICENSE.md',
    'ALTERNATE_LICENSE'
]

# All items to ignore when creating assets
ignore_items = ignore_files + ignore_dirs


class Cons3rtAssetStructureError(Exception):
    """Simple exception type for handling errors with CONS3RT asset structure
    """
    pass


class AssetZipCreationError(Exception):
    """Simple exception type for handling errors creating the asset zip file
    """
    pass


def validate_asset_structure(asset_dir_path):
    """Checks asset structure validity

    :param asset_dir_path: (str) path to the directory containing the asset
    :return: (str) Asset name
    :raises: Cons3rtAssetStructureError
    """
    log = logging.getLogger(mod_logger + '.validate_asset_structure')

    log.info('Validating asset directory: {d}'.format(d=asset_dir_path))

    # Ensure there is an asset.properties file
    asset_props = os.path.join(asset_dir_path, 'asset.properties')

    if not os.path.isfile(asset_props):
        raise Cons3rtAssetStructureError('Asset properties file not found: {f}'.format(f=asset_props))

    # Props to find
    install_script_rel_path = None
    doc_file_rel_path = None
    license_file_rel_path = None
    asset_type = None
    license_file_path = ''
    doc_file_path = ''
    asset_name = None

    log.info('Reading asset properties file: {f}'.format(f=asset_props))
    with open(asset_props, 'r') as f:
        for line in f:
            if line.strip().startswith('installScript='):
                install_script_name = line.strip().split('=')[1]
                install_script_rel_path = os.path.join('scripts', install_script_name)
            elif line.strip().startswith('documentationFile='):
                doc_file_rel_path = line.strip().split('=')[1]
            elif line.strip().startswith('licenseFile='):
                license_file_rel_path = line.strip().split('=')[1]
            elif line.strip().startswith('assetType='):
                asset_type = line.strip().split('=')[1]
                asset_type = asset_type.lower()
            elif line.strip().startswith('name='):
                asset_name = line.strip().split('=')[1]

    # Ensure a name was provided
    if asset_name is None:
        raise Cons3rtAssetStructureError('Required property [name] not found in asset properties file: {f}'.format(
            f=asset_props))
    if asset_name == '':
        raise Cons3rtAssetStructureError('Required property [name] found blank in asset properties file: {f}'.format(
            f=asset_props))

    # Ensure asset_type was provided
    if asset_type is None:
        raise Cons3rtAssetStructureError('Required property [asset_type] not found in asset properties '
                                         'file: {f}'.format(f=asset_props))
    if asset_type == '':
        raise Cons3rtAssetStructureError('Required property [asset_type] found blank in asset properties '
                                         'file: {f}'.format(f=asset_props))

    log.info('Found installScript={f}'.format(f=install_script_rel_path))
    log.info('Found assetType={f}'.format(f=asset_type))

    # Verify the doc file exists if specified
    if doc_file_rel_path:
        log.info('Found documentationFile={f}'.format(f=doc_file_rel_path))
        doc_file_path = os.path.join(asset_dir_path, doc_file_rel_path)
        if not os.path.isfile(doc_file_path):
            raise Cons3rtAssetStructureError('Documentation file not found: {f}'.format(f=doc_file_path))
        else:
            log.info('Verified documentation file: {f}'.format(f=doc_file_path))
    else:
        log.info('The documentationFile property was not specified in asset.properties')

    # Verify the license file exists if specified
    if license_file_rel_path:
        log.info('Found licenseFile={f}'.format(f=license_file_rel_path))
        license_file_path = os.path.join(asset_dir_path, license_file_rel_path)
        if not os.path.isfile(license_file_path):
            raise Cons3rtAssetStructureError('License file not found: {f}'.format(f=license_file_path))
        else:
            log.info('Verified license file: {f}'.format(f=license_file_path))
    else:
        log.info('The licenseFile property was not specified in asset.properties')

    if asset_type == 'software':
        if not install_script_rel_path:
            raise Cons3rtAssetStructureError('Software asset has an asset.properties missing the installScript '
                                             'prop: {f}'.format(f=asset_props))
        else:
            install_script_path = os.path.join(asset_dir_path, install_script_rel_path)
            if not os.path.isfile(install_script_path):
                raise Cons3rtAssetStructureError('Install script file not found: {f}'.format(f=install_script_path))
            else:
                log.info('Verified install script for software asset: {f}'.format(f=install_script_path))

    log.info('Checking items at the root of the asset directory...')
    for item in os.listdir(asset_dir_path):
        log.info('Checking item: {i}'.format(i=item))
        item_path = os.path.join(asset_dir_path, item)
        if item_path == license_file_path:
            continue
        elif item_path == doc_file_path:
            continue
        elif item_path == asset_props:
            continue
        elif item in ignore_items:
            continue
        elif item in acceptable_dirs and os.path.isdir(item_path):
            continue
        else:
            if item == 'VERSION':
                os.remove(item_path)
                log.warn('Deleted file: {f}'.format(f=item_path))
            elif item == 'doc':
                raise Cons3rtAssetStructureError('Found a doc directory at the asset root, this is not allowed')
            elif item in potential_doc_files:
                if not doc_file_rel_path:
                    raise Cons3rtAssetStructureError('Documentation file found but not specified in '
                                                     'asset.properties: {f}'.format(f=item_path))
                else:
                    raise Cons3rtAssetStructureError('Extra documentation file found: {f}'.format(f=item_path))
            elif item in potential_license_files:
                if not license_file_rel_path:
                    raise Cons3rtAssetStructureError('License file found but not specified in '
                                                     'asset.properties: {f}'.format(f=item_path))
                else:
                    raise Cons3rtAssetStructureError('Extra license file found: {f}'.format(f=item_path))
            else:
                raise Cons3rtAssetStructureError('Found illegal item at the asset root dir: {i}'.format(i=item))
    log.info('Validated asset directory successfully: {d}'.format(d=asset_dir_path))
    return asset_name


def make_asset_zip(asset_dir_path, destination_directory=None):
    """Given an asset directory path, creates an asset zip file in the provided
    destination directory

    :param asset_dir_path: (str) path to the directory containing the asset
    :param destination_directory: (str) path to the destination directory for
            the asset
    :return: (str) Path to the asset zip file
    :raises: AssetZipCreationError
    """
    log = logging.getLogger(mod_logger + '.make_asset_zip')
    log.info('Attempting to create an asset zip from directory: {d}'.format(d=asset_dir_path))

    # Ensure the path is a directory
    if not os.path.isdir(asset_dir_path):
        raise AssetZipCreationError('Provided asset_dir_path is not a directory: {d}'.format(d=asset_dir_path))

    # Determine a destination directory if not provided
    if destination_directory is None:
        destination_directory = os.path.join(os.path.expanduser('~'), 'Downloads')
        mkdir_p(destination_directory)

    # Ensure the destination is a directory
    if not os.path.isdir(destination_directory):
        raise AssetZipCreationError('Provided destination_directory is not a directory: {d}'.format(
            d=destination_directory))

    # Validate the asset structure
    try:
        asset_name = validate_asset_structure(asset_dir_path=asset_dir_path)
    except Cons3rtAssetStructureError:
        _, ex, trace = sys.exc_info()
        msg = 'Cons3rtAssetStructureError: Problem found in the asset structure: {d}\n{e}'.format(
            d=asset_dir_path, e=str(ex))
        raise AssetZipCreationError, msg, trace

    # Determine the asset zip file name (same as asset name without spaces)
    zip_file_name = 'asset-' + asset_name.replace(' ', '') + '.zip'
    log.info('Using asset zip file name: {n}'.format(n=zip_file_name))

    # Determine the zip file path
    zip_file_path = os.path.join(destination_directory, zip_file_name)

    # Remove existing zip file if it exists
    if os.path.isfile(zip_file_path):
        log.info('Removing existing asset zip file: {f}'.format(f=zip_file_path))
        os.remove(zip_file_path)

    # Attempt to create the zip
    log.info('Attempting to create asset zip file: {f}'.format(f=zip_file_path))
    try:
        with contextlib.closing(zipfile.ZipFile(zip_file_path, 'w', allowZip64=True)) as zip_w:
            for root, dirs, files in os.walk(asset_dir_path):
                for f in files:
                    skip = False
                    file_path = os.path.join(root, f)

                    # Skip files in the ignore directories list
                    for ignore_dir in ignore_dirs:
                        if ignore_dir in file_path:
                            skip = True
                            break

                    # Skip file in the ignore files list
                    for ignore_file in ignore_files:
                        if f.startswith(ignore_file):
                            skip = True
                            break

                    if skip:
                        log.info('Skipping file: {f}'.format(f=file_path))
                        continue

                    log.info('Adding file to zip: {f}'.format(f=file_path))
                    archive_name = os.path.join(root[len(asset_dir_path):], f)
                    if archive_name.startswith('/'):
                        log.debug('Trimming the leading char: [/]')
                        archive_name = archive_name[1:]
                    log.info('Adding to archive as: {a}'.format(a=archive_name))
                    zip_w.write(file_path, archive_name)
    except Exception:
        _, ex, trace = sys.exc_info()
        msg = 'Unable to create zip file: {f}\n{e}'.format(f=zip_file_path, e=str(ex))
        raise AssetZipCreationError, msg, trace
    log.info('Successfully created asset zip file: {f}'.format(f=zip_file_path))
    return zip_file_path
