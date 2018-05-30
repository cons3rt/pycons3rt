#!/bin/bash

# Source the environment
if [ -f /etc/bashrc ] ; then
    . /etc/bashrc
fi
if [ -f /etc/profile ] ; then
    . /etc/profile
fi

# Establish a log file and log tag
logTag="pycons3rt-install"
logDir="/var/log/cons3rt"
logFile="${logDir}/${logTag}-$(date "+%Y%m%d-%H%M%S").log"

######################### GLOBAL VARIABLES #########################

# pip version to install, LATEST will download the latest from the PIIP team
pipVersion="LATEST"

# Alternate pip version to install if LATEST fails
pipAlternateVersion="9.0.3"

# Download URL for the latest PIP
pipLatestDownloadUrl="https://bootstrap.pypa.io/get-pip.py"

# Jackpine backup download URL for alternate pip versions
pipJackpineDownloadUrl="https://s3.amazonaws.com/jackpine-files/get-pip-${pipAlternateVersion}.py"

# Git Server Domain Name
gitServerDomainName="github.com"

# GIT clone URL
gitUrl="https://${gitServerDomainName}/cons3rt/pycons3rt.git"

# Default Branch to clone
defaultBranch="master"

# Root directory for pycons3rt
pycons3rtRootDir="/root/.pycons3rt"

# Defines the directory for pycons3rt source code
pycons3rtSourceDir="${pycons3rtRootDir}/src"
sourceDir="${pycons3rtSourceDir}/pycons3rt"

# Path to the pycons3rt linux install script
pycons3rtInstaller=

# Python info
pythonHome=
pythonExe=
pipExe=

# List of prereq packages to install before pip
prereqPackages="gcc python-devel python-setuptools python-crypto"

# Environment variable file
pycons3rtEnv="/etc/profile.d/pycons3rt.sh"

####################### END GLOBAL VARIABLES #######################

# Logging functions
function timestamp() { date "+%F %T"; }
function logInfo() { echo -e "$(timestamp) ${logTag} [INFO]: ${1}" >> ${logFile}; }
function logWarn() { echo -e "$(timestamp) ${logTag} [WARN]: ${1}" >> ${logFile}; }
function logErr() { echo -e "$(timestamp) ${logTag} [ERROR]: ${1}" >> ${logFile}; }

function set_deployment_home() {
    # Ensure DEPLOYMENT_HOME exists
    if [ -z "${DEPLOYMENT_HOME}" ] ; then
        logWarn "DEPLOYMENT_HOME is not set, attempting to determine..."
        deploymentDirCount=$(ls /opt/cons3rt-agent/run | grep Deployment | wc -l)
        # Ensure only 1 deployment directory was found
        if [ ${deploymentDirCount} -ne 1 ] ; then
            logErr "Could not determine DEPLOYMENT_HOME"
            return 1
        fi
        # Get the full path to deployment home
        deploymentDir=$(ls /opt/cons3rt-agent/run | grep "Deployment")
        deploymentHome="/opt/cons3rt-agent/run/${deploymentDir}"
        export DEPLOYMENT_HOME="${deploymentHome}"
    else
        deploymentHome="${DEPLOYMENT_HOME}"
    fi
}

function read_deployment_properties() {
    local deploymentPropertiesFile="${DEPLOYMENT_HOME}/deployment-properties.sh"
    if [ ! -f ${deploymentPropertiesFile} ] ; then
        logErr "Deployment properties file not found: ${deploymentPropertiesFile}"
        return 1
    fi
    . ${deploymentPropertiesFile}
    return $?
}

function verify_prerequisites() {
    logInfo "Verifying prerequisites..."

    # Ensure PYTHON2_HOME is set
    if [ -z "${PYTHON2_HOME}" ] ; then
        logErr "Required environment variable is not set: PYTHON2_HOME, this requires the Python asset to be installed"
        return 1
    else
        pythonHome="${PYTHON2_HOME}"
    fi
    logInfo "Found PYTHON2_HOME set to: ${pythonHome}"

    # Ensure the python executable is found
    pythonExe="${pythonHome}/bin/python2.7"
    if [ ! -f ${pythonExe} ] ; then
        logErr "Python 2.7 executable file not found: ${pythonExe}"
        return 2
    fi

    # Output the python version
    logInfo "Using python version: "
    ${pythonExe} --version >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then logErr "There was a problem running [${pythonExe} --version]"; return 3; fi
    logInfo "Found and ran python executable: ${pythonExe}"

    # Ensure the pip executable is found
    pip --version >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then logErr "There was a problem running [pip --version]"; return 4; fi

    # Set pipExe
    pipExe=$(which pip)
    logInfo "Using pip: ${pipExe}"
    return 0
}

function verify_dns() {
    # Tries to resolve a domain name for 5 minutes
    # Parameters:
    # 1 - Domain Name (e.g. example.com)
    # Returns:
    # 0 - Successfully resolved domain name
    # 1 - Failed to resolve domain name
    local domainName=$1
    local count=0
    while [ ${count} -le 150 ] ; do
        logInfo "Verifying domain name resolution for ${domainName}"
        getent hosts ${domainName} >> ${logFile} 2>&1
        if [ $? -ne 0 ] ; then
            logWarn "Could not resolve domain name - ${domainName} - trying again in 2 seconds..."
        else
            logInfo "Successfully resolved domain name: ${domainName}!"
            return 0
        fi
        count=$((${count}+1))
        sleep 2
    done
    logErr "Failed DNS resolution for domain name: ${domainName}"
    return 1
}

function install_prerequisites() {
    # Install pycons3rt prerequisites including boto3 and pip
    logInfo "Installing prerequisite packages..."

    # Install gcc and python-dev as required
    packageManagerCommand="yum -y install"
    which dnf >> ${logFile} 2>&1
    if [ $? -eq 0 ] ; then
    logInfo "Detected dnf on this system, dnf will be used to install packages"
        packageManagerCommand="dnf --assumeyes install"
    fi

    which apt-get >> ${logFile} 2>&1
    if [ $? -eq 0 ] ; then
        logInfo "Detected apt-get on this system, apt-get will be used to install packages"
        packageManagerCommand="apt-get -y install"
    fi

    installCommand="${packageManagerCommand} ${prereqPackages}"
    logInfo "Using package manager command: ${installCommand}"
    ${installCommand} >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then
        logErr "Unable to install prerequisites for the AWS CLI and python packages"
        return 2
    else
        logInfo "Successfully installed prerequisites"
    fi

    logInfo "Successfully installed the pycons3rt prerequisites"
    return 0
}

function git_clone() {
    logInfo "Attempting to git clone pycons3rt..."

    verify_dns ${gitServerDomainName}
    if [ $? -ne 0 ] ; then
        logErr "Unable to resolve GIT server domain name: ${gitServerDomainName}"
        return 1
    else
        logInfo "Successfully resolved domain name: ${gitServerDomainName}"
    fi

    # Determine the branch to clone based on deployment properties
    pycons3rtBranch="${defaultBranch}"
    if [ -z "${PYCONS3RT_BRANCH}" ] ; then
        logInfo "PYCONS3RT_BRANCH deployment property not found, git will clone the ${pycons3rtBranch} branch"
    else
        logInfo "Found deployment property PYCONS3RT_BRANCH: ${PYCONS3RT_BRANCH}"
        pycons3rtBranch="${PYCONS3RT_BRANCH}"
    fi
    logInfo "Git branch to clone: ${pycons3rtBranch}"

    # Create the pycons3rt log directory
    logInfo "Creating directory: ${pycons3rtRootDir}..."
    mkdir -p ${pycons3rtRootDir}/log >> ${logFile} 2>&1

    logInfo "Ensuring HOME is set..."
    if [ -z "${HOME}" ] ; then
        export HOME="/root"
    fi

    # Git clone the specified branch
    logInfo "Cloning the pycons3rt GIT repo..."
    for i in {1..10} ; do

        # Remove the source directory if it exists
        if [ -d ${sourceDir} ] ; then
            logInfo "Removing: ${sourceDir}"
            rm -Rf ${sourceDir} >> ${logFile} 2>&1
        fi

        logInfo "Attempting to clone the GIT repo, attempt ${i} of 10..."
        git clone -b ${pycons3rtBranch} ${gitUrl} ${sourceDir} >> ${logFile} 2>&1
        result=$?
        logInfo "git clone exited with code: ${result}"
        if [ ${result} -ne 0 ] && [ $i -ge 10 ] ; then
            logErr "Unable to clone git repo after ${i} attempts: ${gitUrl}"
            return 2
        elif [ ${result} -ne 0 ] ; then
            logWarn "Unable to clone git repo, re-trying in 5 seconds: ${gitUrl}"
            sleep 5
        else
            logInfo "Successfully cloned git repo: ${gitUrl}"
            break
        fi
    done

    # Ensure the pycons3rt install script can be found
    pycons3rtInstaller="${sourceDir}/scripts/install.sh"
    if [ ! -f ${pycons3rtInstaller} ] ; then
        logErr "File not found: ${pycons3rtInstaller}. pycons3rt install file not found, src may not have been checked out or staged correctly"
        return 3
    else
        logInfo "Found file: ${pycons3rtInstaller}"
    fi
    logInfo "git clone succeeded!"
    return 0
}

function install_pip_requirements() {
    logInfo "Installing pip requirements from the requirements.txt file..."

    if [ ! -d ${sourceDir} ] ; then
        logErr "Source code directory not found, cannot install pip requirements: ${sourceDir}"
        return 1
    fi

    logInfo "Changing to directory: ${sourceDir}"
    cd ${sourceDir} >> ${logFile} 2>&1

    # Ensure the requirements file exists
    requirementsFileRelPath="./cfg/requirements.txt"
    if [ ! -f ${requirementsFileRelPath} ] ; then
        logErr "Requirements file not found at relative path: ${requirementsFileRelPath}"
        return 2
    fi

    logInfo "Using pip: ${pipExe}"
    logInfo "Attempting to install pip requirements from file at relative path: ${requirementsFileRelPath}"
    ${pipExe} install -r ${requirementsFileRelPath} >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then
        logErr "There was a problem installing pip requirements"
        return 3
    fi
    logInfo "Successfully installed pip requirements"
    return 0
}

function run_setup_install() {
    logInfo "Attempting to run setup.py..."

    if [ ! -d ${sourceDir} ] ; then
        logErr "Source code directory not found, cannot run setup.py: ${sourceDir}"
        return 1
    fi

    logInfo "Changing to directory: ${sourceDir}"
    cd ${sourceDir} >> ${logFile} 2>&1

    # Ensure setup.py exists
    if [ ! -f setup.py ] ; then
        logErr "setup.py file not found"
        return 2
    fi

    logInfo "Running setup.py..."
    ${pythonExe} setup.py install >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then logErr "There was a problem running setup.py..."; return 3; fi
    logInfo "setup.py ran successfully!"

    # Run the osutil to configure logging and directories
    logInfo "Running osutil to configure logging and directories..."
    osutil="./pycons3rt/osutil.py"
    if [ ! -f ${osutil} ] ; then logErr "osutil file not found at relative path: ${osutil}"; return 4; fi

    logInfo "Found osutil: [${osutil}], running..."
    ${pythonExe} ${osutil} >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then logErr "There was a problem running osutil: ${osutil}"; return 5; fi

    logInfo "pycons3rt installed successfully!"
    return 0
}

function set_env() {
    logInfo "Setting the environment variables..."
    echo "export PYCONS3RT_PYTHON_HOME=${pythonHome}" > ${pycons3rtEnv}
    echo "export PYCONS3RT_PYTHON=${pythonExe}" >> ${pycons3rtEnv}
    echo "export PYCONS3RT_PIP=${pipExe}" >> ${pycons3rtEnv}
    echo "export PYCONS3RT_HOME=${pycons3rtRootDir}" >> ${pycons3rtEnv}
    echo "export PYCONS3RT_SOURCE_DIR=${pycons3rtSourceDir}" >> ${pycons3rtEnv}
    chown root:root ${pycons3rtEnv} >> ${logFile} 2>&1
    chmod 755 ${pycons3rtEnv} >> ${logFile} 2>&1
    . ${pycons3rtEnv}
    return $?
}

function main() {
    logInfo "Beginning ${logTag} install script..."
    set_deployment_home
    read_deployment_properties
    verify_prerequisites
    if [ $? -ne 0 ] ; then logErr "Unable to verify all prerequisites for pycons3rt"; return 1; fi
    install_prerequisites
    if [ $? -ne 0 ] ; then logErr "There was a problem installing prerequisite packages"; return 2; fi
    git_clone
    if [ $? -ne 0 ] ; then logErr "There was a problem cloning the pycons3rt git repo"; return 4; fi
    install_pip_requirements
    if [ $? -ne 0 ] ; then logErr "There was a problem installing one or more pip packages"; return 5; fi
    run_setup_install
    if [ $? -ne 0 ] ; then logErr "There was a problem installing pycons3rt"; return 6; fi
    set_env
    if [ $? -ne 0 ] ; then logErr "There was a problem configuring environment variables"; return 7; fi
    logInfo "Completed: ${logTag} install script"
    return 0
}

# Set up the log file
mkdir -p ${logDir}
chmod 700 ${logDir}
touch ${logFile}
chmod 644 ${logFile}

main
result=$?
cat ${logFile}

logInfo "Exiting with code ${result} ..."
exit ${result}
