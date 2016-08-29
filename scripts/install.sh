#!/bin/bash

# The purpose of this script is to install pycons3rt into your local
# python installation

echo "Installing pycons3rt ..."

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd ${SCRIPT_DIR}/..
python ${SCRIPT_DIR}/../setup.py install
result=$?

echo "pycons3rt installation exited with code: ${result}"
exit ${result}
