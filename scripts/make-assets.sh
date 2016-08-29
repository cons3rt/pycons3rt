#!/bin/bash

# The purpose of this script is make the pycons3rt assets for cons3rt import

echo "Creating the pycons3rt asset..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="${SCRIPT_DIR}/.."
ASSET_DIR="${SCRIPT_DIR}/../asset"
BUILD_DIR="${ASSET_DIR}/../build"
resultSet=()

function run_and_check_status() {
    "$@"
    local status=$?
    if [ ${status} -ne 0 ] ; then
        echo "ERROR: Error executing: $@, exited with code: ${status}"
    else
        echo "$@ executed successfully and exited with code: ${status}"
    fi
    resultSet+=("${status}")
    return ${status}
}

function create_asset_zip() {
    echo "Creating asset zip file..."
    cd $1
    echo "Current directory: $(pwd)"
    zipFileName=$(echo $(pwd) | awk -F '/' '{print $NF}')
    zipFilePath="${BUILD_DIR}/${zipFileName}.zip"
    echo "Attempting to create zip file: ${zipFilePath}"

    find . -name ".DS_Store" -exec rm {} \;
    find . -type f -name "._*" -exec rm {} \;
    zip -r ${zipFilePath} asset.properties doc media scripts config data src README* LICENSE* HELP* -x "doc\._*" -x "media\._*" -x "scripts\._*" -x "._*" -x \"*.DS_Store*\" -x \".DS_Store\"  -x \"*.svn\" -x \"*.git\" -x media\MEDIA_README;
    return $?
}

function make_asset() {
    echo "Creating asset directory structure..."
    assetName="asset-pycons3rt-$1"
    assetCreationDir="${BUILD_DIR}/${assetName}"
    subAssetDir="${ASSET_DIR}/$1"

    run_and_check_status mkdir -p ${assetCreationDir}/scripts
    run_and_check_status cp -f ${subAssetDir}/asset.properties ${assetCreationDir}/
    run_and_check_status cp -f ${subAssetDir}/scripts/* ${assetCreationDir}/scripts/
    run_and_check_status cp -f ${REPO_DIR}/LICENSE.md ${assetCreationDir}/
    run_and_check_status cp -f ${REPO_DIR}/README.md ${assetCreationDir}/

    for resultCheck in "${resultSet[@]}" ; do
        if [ ${resultCheck} -ne 0 ] ; then
            echo "Non-zero exit code found: ${resultCheck}"
            return 1
        fi
    done

    # Create the asset zip file
    create_asset_zip ${assetCreationDir}
    if [ $? -ne 0 ] ; then
        echo "ERROR: Unable to create asset zip file"
        return 2
    fi

    # Clean up
    rm -Rf ${assetCreationDir}
}

mkdir -p ${BUILD_DIR}

make_asset "linux"
if [ $? -ne 0 ] ; then
    echo "ERROR: Unable to create the linux asset"
    exit 1
fi

make_asset "windows"
if [ $? -ne 0 ] ; then
    echo "ERROR: Unable to create the windows asset"
    exit 2
fi

exit 0
