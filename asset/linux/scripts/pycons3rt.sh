#!/bin/bash

# Source the environment
if [ -f /etc/bashrc ] ; then
    . /etc/bashrc
fi
if [ -f /etc/environment ] ; then
    . /etc/environment
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

# Pycons3rt conf directory
confDir="/etc/pycons3rt/conf"

# Deployment properties filename
deploymentPropsFile="deployment-properties.sh"

# List of prereq packages to install before pip
prereqPackages="gcc python-devel python-setuptools python-crypto"

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
        getent hosts ${domainName}
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
	python --version
	if [ $? -ne 0 ] ; then
        logErr "Python not detected, and is a required dependency"
        return 1
    fi

    # Install gcc and python-dev as required
    packageManagerCommand="yum -y install"
    which dnf
    if [ $? -eq 0 ] ; then
    logInfo "Detected dnf on this system, dnf will be used to install packages"
        packageManagerCommand="dnf --assumeyes install"
    fi

    which apt-get
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

function install_pip_latest() {
    logInfo "Attempting to download the latest pip from URL: ${pipLatestDownloadUrl}"

    cd /root
    curl -O "${pipLatestDownloadUrl}" >> ${logFile} 2>&1

    # Ensure the download succeeded
    if [ $? -ne 0 ] ; then
        logErr "There was a problem downloading pip from URL: ${pipLatestDownloadUrl}"
        return 1
    fi

    # Attempt to install pip
    logInfo "Attempting to install pip..."
    python get-pip.py >> ${logFile} 2>&1

    # Ensure the install succeeded
    if [ $? -ne 0 ] ; then
        logErr "There was a problem installing the latest pip"
        return 2
    fi

    logInfo "Latest pip installed successfully"
    return 0
}

function install_pip_alternate() {
    logInfo "Attempting to download an alternate version of pip [${pipAlternateVersion}] from URL: ${pipJackpineDownloadUrl}"

    cd /root
    curl -O "${pipJackpineDownloadUrl}" >> ${logFile} 2>&1

    # Ensure the download succeeded
    if [ $? -ne 0 ] ; then
        logErr "There was a problem downloading pip from URL: ${pipJackpineDownloadUrl}"
        return 1
    fi

    # Ensure the get-pip.py file exists
    getPipFile="/root/get-pip-${pipAlternateVersion}.py"
    if [ ! -f ${getPipFile} ] ; then
        logErr "File not found, may not have downloaded: ${getPipFile}"
        return 2
    fi

    # Attempt to install pip
    logInfo "Attempting to install pip..."
    python ${getPipFile} >> ${logFile} 2>&1

    # Ensure the install succeeded
    if [ $? -ne 0 ] ; then
        logErr "There was a problem installing the pip version: ${pipAlternateVersion}"
        return 2
    fi

    logInfo "pip version [${pipAlternateVersion}] installed successfully"
    return 0
}

function install_pip() {
    logInfo "Installing pip..."

    # Skip install if pip already installed
    which pip
    if [ $? -eq 0 ] ; then logInfo "pip already installed!  Nothing to do..."; return 0; fi

    # Check the version of pip to install
    latestRes=1
    if [[ ${pipVersion} == "LATEST" ]] ; then
        install_pip_latest
        latestRes=$?
    fi

    # Exit if it was successful
    if [ ${latestRes} -eq 0 ] ; then
        logInfo "Latest pip installed successfully!"
        return 0
    fi

    logWarn "Installing the latest pip failed, attempting to install an alternate version..."
    install_pip_alternate
    if [ $? -ne 0 ] ; then
        logErr "There was a problem downloading or installing the alternate version of pip"
        return 1
    fi
    logInfo "pip installed successfully!"
    return 0
}

function install_pip_packages() {
    logInfo "Attempting to install packages with pip..."

    # Upgrade setuptools to the latest
    logInfo "Upgrading setuptools..."
    pip install setuptools --upgrade >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then logErr "There was a problem upgrading setuptools"; return 1; fi

	# Install Python packages using PIP
	logInfo "Installing wheel 0.29.0..."
	pip install wheel==0.29.0 >> ${logFile} 2>&1
	if [ $? -ne 0 ] ; then logErr "There was a problem installing wheel==0.29.0"; return 2; fi

	logInfo "Installing awscli..."
	pip install awscli >> ${logFile} 2>&1
	if [ $? -ne 0 ] ; then logErr "There was a problem installing awscli"; return 3; fi

	logInfo "Installing boto3..."
	pip install boto3 >> ${logFile} 2>&1
	if [ $? -ne 0 ] ; then logErr "There was a problem installing boto3"; return 4; fi

	logInfo "Installing netifaces..."
	pip install netifaces >> ${logFile} 2>&1
	if [ $? -ne 0 ] ; then logErr "There was a problem installing netifaces"; return 5; fi

	logInfo "Installing jinja2..."
	pip install jinja2 >> ${logFile} 2>&1
	if [ $? -ne 0 ] ; then logErr "There was a problem installing jinja2"; return 6; fi

	logInfo "Installing requests version 2.10.0..."
	pip install requests==2.10.0 >> ${logFile} 2>&1
	if [ $? -ne 0 ] ; then
	    logInfo "Trouble installing requests==2.10.0, trying to install without a version..."
	    pip install requests >> ${logFile} 2>&1
	    if [ $? -ne 0 ] ; then logErr "There was a problem installing requests"; return 7; fi
	fi

	logInfo "Installing requests[security]..."
	pip install requests[security] >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then logErr "There was a problem installing requests[security]"; return 8; fi

    # Remove python-crypto from RHEL systems
	#if [[ ${packageManagerCommand} == *yum* ]] ; then
	#    logInfo "This is a RHEL system, removing python-crypto..."
	#    yum -y remove python-crypto >> ${logFile} 2>&1
    #fi

    logInfo "Setting permissions on the AWS executable..."
    chmod +x /usr/bin/aws >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then logErr "There was a problem setting permissions on /usr/bin/aws"; return 9; fi

	logInfo "Verifying AWS CLI install ..."
	aws --version >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then logErr "There was a problem detecting the aws version"; return 10; fi

    logInfo "All packages installed successfully"
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
        pycons3rtBranch=${PYCONS3RT_BRANCH}
    fi
    logInfo "Git branch to clone: ${pycons3rtBranch}"

    # Create the pycons3rt log directory
    logInfo "Creating directory: ${pycons3rtRootDir}..."
    mkdir -p ${pycons3rtRootDir}/log >> ${logFile} 2>&1

    # Create the src directory
    logInfo "Creating directory: ${sourceDir}..."
    mkdir -p ${sourceDir} >> ${logFile} 2>&1

    logInfo "Ensuring HOME is set..."
    if [ -z "${HOME}" ] ; then
        export HOME="/root"
    fi

    # Git clone the specified branch
    logInfo "Cloning the pycons3rt GIT repo..."
    for i in {1..10} ; do
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

function install_pycons3rt() {
    logInfo "Attempting to install pycons3rt..."

    # Install the pycons3rt python project into the system python lib
    logInfo "Installing pycons3rt ..."
    ${pycons3rtInstaller} >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then logInfo "pycons3rt install exited with code: ${?}"; return 1; fi

    logInfo "pycons3rt completed successfully!"

    # Run the osutil to configure logging and directories
    logInfo "Running osutil to configure logging and directories..."
    osutil="${sourceDir}/pycons3rt/osutil.py"
    if [ ! -f ${osutil} ] ; then logErr "osutil file not found: ${osutil}"; return 2; fi

    logInfo "Found osutil: [${osutil}], running..."
    python ${osutil} >> ${logFile} 2>&1
    if [ $? -ne 0 ] ; then logErr "There was a problem running osutil: ${osutil}"; return 3; fi

    logInfo "Installed pycons3rt successfully!"
    return 0
}


function main() {
    logInfo "Beginning ${logTag} install script..."
    set_deployment_home
    read_deployment_properties
    install_prerequisites
    if [ $? -ne 0 ] ; then logErr "There was a problem installing prerequisite packages"; return 1; fi
    install_pip
    if [ $? -ne 0 ] ; then logErr "There was a problem installing pip"; return 2; fi
    install_pip_packages
    if [ $? -ne 0 ] ; then logErr "There was a problem installing one or more pip packages"; return 3; fi
    git_clone
    if [ $? -ne 0 ] ; then logErr "There was a problem cloning the pycons3rt git repo"; return 4; fi
    install_pycons3rt
    if [ $? -ne 0 ] ; then logErr "There was a problem installing pycons3rt"; return 5; fi
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
