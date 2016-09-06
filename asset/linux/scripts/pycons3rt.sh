#!/bin/bash

# Created by Joe Yennaco (8/29/2016)

# Set log commands
logTag="pycons3rt-install"
logInfo="logger -i -s -p local3.info -t ${logTag} -- [INFO] "
logWarn="logger -i -s -p local3.warning -t ${logTag} -- [WARNING] "
logErr="logger -i -s -p local3.err -t ${logTag} -- [ERROR] "

# Get the current timestamp and append to logfile name
TIMESTAMP=$(date "+%Y-%m-%d-%H%M")

${logInfo} "Sourcing /etc/bashrc to get the environment ..."
source /etc/bashrc

######################### GLOBAL VARIABLES #########################

# Git Server Domain Name
gitServerDomainName="github.com"

# GIT clone URL
gitUrl="https://${gitServerDomainName}/cons3rt/pycons3rt.git"

# Default Branch to clone
defaultBranch="develop"

# Root directory for pycons3rt
pycons3rtRootDir="/root/.pycons3rt"

# Defines the directory for pycons3rt source code
pycons3rtSourceDir="${pycons3rtRootDir}/src"
sourceDir="${pycons3rtSourceDir}/pycons3rt"

# Pycons3rt conf directory
confDir="/etc/pycons3rt/conf"

# Deployment properties filename
deploymentPropsFile="deployment-properties.sh"

# List of prereq packages to install before pip
prereqPackages="gcc python-devel python-setuptools python-crypto"

# Array to maintain exit codes of RPM install commands
resultSet=();

####################### END GLOBAL VARIABLES #######################

# Parameters:
# 1 - Command to execute
# Returns:
# Exit code of the command that was executed
function run_and_check_status() {
    "$@"
    local status=$?
    if [ ${status} -ne 0 ]
    then
        ${logErr} "Error executing: $@, exited with code: ${status}"
    else
        ${logInfo} "$@ executed successfully and exited with code: ${status}"
    fi
    resultSet+=("${status}")
    return ${status}
}

# Tries to resolve a domain name for 5 minutes
# Parameters:
# 1 - Domain Name (e.g. example.com)
# Returns:
# 0 - Successfully resolved domain name
# 1 - Failed to resolve domain name
function verify_dns() {
    local domainName=$1
    local count=0
    while [ ${count} -le 150 ] ; do
        ${logInfo} "Verifying domain name resolution for ${domainName}"
        getent hosts ${domainName}
        if [ $? -ne 0 ] ; then
            ${logWarn} "Could not resolve domain name - ${domainName} - trying again in 2 seconds..."
        else
            ${logInfo} "Successfully resolved domain name: ${domainName}!"
            return 0
        fi
        count=$((${count}+1))
        sleep 2
    done
    ${logErr} "Failed DNS resolution for domain name: ${domainName}"
    return 1
}

# Install pycons3rt prerequisites including boto3 and pip
function install_prerequisites() {
    ${logInfo} "Installing AWS CLI, AWS SDK, Ansible, and prerequisite packages..."
	python --version
	if [ $? -ne 0 ] ; then
        ${logErr} "Python not detected, and is a required dependency"
        return 1
    fi

    # Install gcc and python-dev as required
    packageManagerCommand="yum -y install"
    which dnf
    if [ $? -eq 0 ] ; then
    ${logInfo} "Detected dnf on this system, dnf will be used to install packages"
        packageManagerCommand="dnf --assumeyes install"
    fi

    which apt-get
    if [ $? -eq 0 ] ; then
        ${logInfo} "Detected apt-get on this system, apt-get will be used to install packages"
        packageManagerCommand="apt-get -y install"
    fi

    installCommand="${packageManagerCommand} ${prereqPackages}"
    ${logInfo} "Using package manager command: ${installCommand}"
    run_and_check_status ${installCommand}

    if [ $? -ne 0 ] ; then
        ${logErr} "Unable to install prerequisites for the AWS CLI and python packages"
        return 2
    else
        ${logInfo} "Successfully install prerequisites"
    fi

    # Install PIP
	run_and_check_status curl -O "https://bootstrap.pypa.io/get-pip.py"
	run_and_check_status python get-pip.py
	run_and_check_status pip install setuptools --upgrade

	# Install Python packages using PIP
	run_and_check_status pip install awscli
	run_and_check_status pip install boto3

	# TODO requests prereq should move to the pyBART install asset
	run_and_check_status pip install requests==2.10.0

    # Remove python-crypto from RHEL systems
	if [[ ${packageManagerCommand} == *yum* ]] ; then
	    ${logInfo} "This is a RHEL system, removing python-crypto..."
	    run_and_check_status yum -y remove python-crypto
    fi

	${logInfo} "Verifying AWS CLI install ..."
	run_and_check_status aws --version

    # Check the results of commands from this script, return error if an error is found
    for resultCheck in "${resultSet[@]}" ; do
        if [ ${resultCheck} -ne 0 ] ; then
            ${logErr} "Non-zero exit code detected, there was a problem with a prerequisite installation."
            return 3
        fi
    done

    ${logInfo} "Successfully installed the pycons3rt prerequisites"
    return 0
}

# Main Install Function
function main() {
    ${logInfo} "Beginning CONS3RT Configuration Source Code install ..."
    ${logInfo} "Timestamp: ${TIMESTAMP}"

    # Ensure ASSET_DIR exists, if not assume this script exists in ASSET_DIR/scripts
    if [ -z "${ASSET_DIR}" ] ; then
        ${logWarn} "ASSET_DIR not found, assuming ASSET_DIR is 1 level above this script ..."
        SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
        ASSET_DIR=${SCRIPT_DIR}/..
    fi
    scriptDir="${ASSET_DIR}/scripts"

    # Ensure the osutil script exists
    if [ ! -f ${scriptDir}/osutil.py ] ; then
        ${logErr} "File not found: ${scriptDir}/osutil.py"
        return 1
    else
        ${logInfo} "Found osutil script: ${scriptDir}/osutil.py"
    fi

    # Run the osutil script to configure directories

    # Ensure DEPLOYMENT_HOME exists
    if [ -z ${DEPLOYMENT_HOME} ] ; then
        ${logWarn} "DEPLOYMENT_HOME is not set, attempting to determine..."
        deploymentDirCount=$(ls /opt/cons3rt-agent/run | grep Deployment | wc -l)
        # Ensure only 1 deployment directory was found
        if [ ${deploymentDirCount} -ne 1 ] ; then
            ${logErr} "Could not determine DEPLOYMENT_HOME"
            return 1
        fi
        # Get the full path to deployment home
        deploymentDir=$(ls /opt/cons3rt-agent/run | grep Deployment)
        deploymentHome="/opt/cons3rt-agent/run/${deploymentDir}"
    else
        deploymentHome="${DEPLOYMENT_HOME}"
        ${logInfo} "DEPLOYMENT_HOME: ${deploymentHome}"
    fi

    # Ensure the deployment properties file can be found
    deploymentProperties="${deploymentHome}/${deploymentPropsFile}"
    if [ ! -f ${deploymentProperties} ] ; then
        ${logErr} "File not found: ${deploymentProperties}"
        return 2
    else
        ${logInfo} "Found deployment properties file: ${deploymentProperties}"
    fi

    # Source deployment properties
    run_and_check_status source ${deploymentProperties}

    verify_dns ${gitServerDomainName}
    if [ $? -ne 0 ] ; then
        ${logErr} "Unable to resolve GIT server domain name: ${gitServerDomainName}"
        return 3
    else
        ${logInfo} "Successfully resolved domain name: ${gitServerDomainName}"
    fi

    # Determine the branch to clone based on deployment properties
    pycons3rtBranch=${defaultBranch}
    if [ -z "${PYCONS3RT_BRANCH}" ] ; then
        ${logInfo} "PYCONS3RT_BRANCH deployment property not found, git will clone the ${pycons3rtBranch} branch"
    else
        ${logInfo} "Found deployment property PYCONS3RT_BRANCH: ${PYCONS3RT_BRANCH}"
        pycons3rtBranch=${PYCONS3RT_BRANCH}
    fi
    ${logInfo} "Git branch to clone: ${pycons3rtBranch}"

    # Create the pycons3rt log directory
    ${logInfo} "Creating directory: ${pycons3rtRootDir}..."
    run_and_check_status mkdir -p ${pycons3rtRootDir}/log

    # Create the src directory
    ${logInfo} "Creating directory: ${sourceDir}..."
    run_and_check_status mkdir -p ${sourceDir}

    ${logInfo} "Ensuring HOME is set..."
    if [ -z "${HOME}" ] ; then
        export HOME="/root"
    fi

    # Git clone the specified branch
    ${logInfo} "Cloning the pycons3rt GIT repo..."
    for i in {1..10} ; do
        ${logInfo} "Attempting to clone the GIT repo, attempt ${i} of 10..."
        git clone -b ${pycons3rtBranch} ${gitUrl} ${sourceDir}
        result=$?
        ${logInfo} "git clone exited with code: ${result}"
        if [ ${result} -ne 0 ] && [ $i -ge 10 ] ; then
            ${logErr} "Unable to clone git repo after ${i} attempts: ${gitUrl}"
            return 4
        elif [ ${result} -ne 0 ] ; then
            ${logWarn} "Unable to clone git repo, re-trying in 5 seconds: ${gitUrl}"
            sleep 5
        else
            ${logInfo} "Successfully cloned git repo: ${gitUrl}"
            break
        fi
    done

    # Install prerequisites for pycons3rt
    install_prerequisites
    if [ $? -ne 0 ] ; then
        ${logErr} "There was a problem installing prerequisites for pycons3rt"
        return 5
    else
        ${logInfo} "Successfully installed pycons3rt prerequisites"
    fi

    # Ensure the pycons3rt install script can be found
    pycons3rtInstaller="${sourceDir}/scripts/install.sh"
    if [ ! -f ${pycons3rtInstaller} ] ; then
        ${logErr} "File not found: ${pycons3rtInstaller}. pycons3rt install file not found, src may not have been checked out or staged correctly"
        return 6
    else
        ${logInfo} "Found file: ${pycons3rtInstaller}"
    fi

    # Install the pycons3rt python project into the system python lib
    ${logInfo} "Installing pycons3rt ..."
    ${pycons3rtInstaller}
    installResult=$?

    # Exit with an error if the checkout did not succeed
    if [ ${installResult} -ne 0 ] ; then
        ${logInfo} "pycons3rt install did not complete successfully and exited with code: ${installResult}"
        return 7
    else
        ${logInfo} "pycons3rt completed successfully!"
    fi

    # Run the osutil to configure logging and directories
    ${logInfo} "Running osutil to configure logging and directories..."
    osutil="${sourceDir}/pycons3rt/osutil.py"
    if [ ! -f ${osutil} ] ; then
        ${logErr} "osutil file not found: ${osutil}"
        return 8
    else
        ${logInfo} "Found osutil: ${osutil}"
    fi
    run_and_check_status python ${osutil}

    # Ensure asset install was successful
    ${logInfo} "Verifying asset installed successfully ..."
    for resultCheck in "${resultSet[@]}" ; do
        if [ ${resultCheck} -ne 0 ] ; then
            ${logErr} "Non-zero exit code found: ${resultCheck}"
            return 9
        fi
    done
    ${logInfo} "Completed pycons3rt install Successfully!"
    return 0
}

main
result=$?

${logInfo} "Exiting with code ${result} ..."
exit ${result}
