#!/bin/bash

# The purpose of this script is make the pycons3rt assets for cons3rt import

# Set log commands
logTag="make-assets"
logInfo="logger -i -s -p local3.info -t ${logTag} -- [INFO] "
logWarn="logger -i -s -p local3.warning -t ${logTag} -- [WARNING] "
logErr="logger -i -s -p local3.err -t ${logTag} -- [ERROR] "

# Get the current timestamp and append to logfile name
TIMESTAMP=$(date "+%Y-%m-%d-%H%M")

######################### GLOBAL VARIABLES #########################

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="${SCRIPT_DIR}/.."
ASSET_DIR="${SCRIPT_DIR}/../asset"
BUILD_DIR="${ASSET_DIR}/../build"
resultSet=()

####################### END GLOBAL VARIABLES #######################

# Executes the passed command, adds the status to the resultSet
function run_and_check_status() {
    "$@"
    local status=$?
    if [ ${status} -ne 0 ] ; then
        ${logErr} "Error executing: $@, exited with code: ${status}"
    fi
    resultSet+=("${status}")
    return ${status}
}

function create_asset_zip() {
    cd $1
    zipFileName=$(echo $(pwd) | awk -F '/' '{print $NF}')
    zipFilePath="${BUILD_DIR}/${zipFileName}.zip"
    find . -name ".DS_Store" -exec rm {} \;
    find . -type f -name "._*" -exec rm {} \;
    zip -r ${zipFilePath} asset.properties doc media scripts config data src README* LICENSE* HELP* -x "doc\._*" -x "media\._*" -x "scripts\._*" -x "._*" -x \"*.DS_Store*\" -x \".DS_Store\"  -x \"*.svn\" -x \"*.git\" -x media\MEDIA_README > /dev/null 2>&1
    result=$?
    ${logInfo} "Created asset: build/${zipFileName}.zip"
    return ${result}
}

function make_asset() {
    assetName="asset-pycons3rt-$1"
    assetCreationDir="${BUILD_DIR}/${assetName}"
    subAssetDir="${ASSET_DIR}/$1"

    # Copy the asset.properties and scripts directories
    run_and_check_status mkdir -p ${assetCreationDir}/scripts
    run_and_check_status cp -f ${subAssetDir}/asset.properties ${assetCreationDir}/
    run_and_check_status cp -f ${subAssetDir}/scripts/* ${assetCreationDir}/scripts/

    # Copy the README file to the asset
    if [ -f ${subAssetDir}/README.md ] ; then
        run_and_check_status cp -f ${subAssetDir}/README.md ${assetCreationDir}/
    else
        run_and_check_status cp -f ${REPO_DIR}/README.md ${assetCreationDir}/
    fi

    # Copy license file to asset
    run_and_check_status cp -f ${REPO_DIR}/LICENSE ${assetCreationDir}/

    # Copy the media directory if it exists
    if [ -d ${subAssetDir}/media ] ; then
        run_and_check_status mkdir -p ${assetCreationDir}/media
        run_and_check_status cp -f ${subAssetDir}/media/* ${assetCreationDir}/media/
    fi

    if [ -z $2 ] ; then
        :
    else
        if [ ! -f $2 ] ; then
            ${logErr} "Additional file not found for asset $1, stage locally before running: $2"
            return 1
        else
            ${logInfo} "Additional file found for asset $1, adding to media directory: $2"
            run_and_check_status mkdir -p ${assetCreationDir}/media
            run_and_check_status cp -f $2 ${assetCreationDir}/media/
        fi
    fi

    for resultCheck in "${resultSet[@]}" ; do
        if [ ${resultCheck} -ne 0 ] ; then
            ${logErr} "Non-zero exit code found: ${resultCheck}"
            return 2
        fi
    done

    # Create the asset zip file
    create_asset_zip ${assetCreationDir}
    if [ $? -ne 0 ] ; then
        ${logErr} "Unable to create asset zip file"
        return 3
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
