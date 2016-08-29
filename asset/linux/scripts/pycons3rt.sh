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
pycons3rtRootDir="/root/.cons3rt"

# Defines the directory where cons3rt-deploying-cons3rt source code will
# be staged and installed to.
sourceDir="${pycons3rtRootDir}/pycons3rt"

# Deployment properties filename
deploymentPropsFile="deployment-properties.sh"

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

# Main Install Function
function main() {
    ${logInfo} "Beginning CONS3RT Configuration Source Code install ..."
    ${logInfo} "Timestamp: ${TIMESTAMP}"

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

    # Ensure the pycons3rt install script can be found
    pycons3rtInstaller="${sourceDir}/scripts/install.sh"
    if [ ! -f ${pycons3rtInstaller} ] ; then
        ${logErr} "File not found: ${pycons3rtInstaller}. pycons3rt install file not found, src may not have been checked out or staged correctly"
        return 5
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
        return 6
    else
        ${logInfo} "pycons3rt completed successfully!"
    fi

    # Copy the logging config file to the log directory
    #${logInfo} "Staging the logging config file..."
    #run_and_check_status cp -f ${sourceDir}/pycons3rt/pycons3rt-logging.conf ${pycons3rtRootDir}/log/

    # Ensure asset install was successful
    ${logInfo} "Verifying asset installed successfully ..."
    for resultCheck in "${resultSet[@]}" ; do
        if [ ${resultCheck} -ne 0 ] ; then
            ${logErr} "Non-zero exit code found: ${resultCheck}"
            return 7
        fi
    done
    ${logInfo} "Completed pycons3rt install Successfully!"
    return 0
}

main
result=$?

${logInfo} "Exiting with code ${result} ..."
exit ${result}
