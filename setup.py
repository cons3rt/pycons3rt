#!/usr/bin/env python


import sys
import os
from setuptools import setup, find_packages


py_version = sys.version_info[:2]


# Ensure supported python version
if py_version < (2, 7):
    raise RuntimeError('pycons3rt requires Python 2.7 or later')
elif py_version >= (3, 0):
    raise RuntimeError('pycons3rt does not support Python3 at this time')


here = os.path.abspath(os.path.dirname(__file__))


# Get the version
version_txt = os.path.join(here, 'pycons3rt/VERSION.txt')
pycons3rt_version = open(version_txt).read().strip()


# Get the requirements
requirements_txt = os.path.join(here, 'cfg/requirements.txt')
requirements = []
with open(requirements_txt) as f:
    for line in f:
        requirements.append(line.strip())


dist = setup(
    name='pycons3rt',
    version=pycons3rt_version,
    description='A python library for CONS3RT assets',
    long_description=open('README.md').read(),
    author='Joe Yennaco',
    author_email='joe.yennaco@jackpinetech.com',
    url='https://github.com/cons3rt/pycons3rt',
    include_package_data=True,
    license='GNU GPL v3',
    packages=find_packages(),
    zip_safe=True,
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'pycons3rt_setup = pycons3rt.osutil:main',
            'asset = pycons3rt.asset:main'
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent'
    ]
)
