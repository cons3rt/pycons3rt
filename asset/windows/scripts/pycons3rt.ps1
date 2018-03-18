# pycons3rt.ps1
# Created by Joseph Yennaco (9/6/2016)
# Updated by J. Yennaco (10/8/2017) to add the requests[security] package

$ErrorActionPreference = "Stop"
#$scriptPath = Split-Path -LiteralPath $(if ($PSVersionTable.PSVersion.Major -ge 3) { $PSCommandPath } else { & { $MyInvocation.ScriptName } })
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

# Load the PATH environment variable
$env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine")

########################### VARIABLES ###############################

$ASSET_DIR = "$env:ASSET_DIR"
$TIMESTAMP = Get-Date -f yyyy-MM-dd-HHmm

# exit code
$exitCode = 0

# Log files
$LOGTAG = "pycons3rt-install"
$LOGFILE = "C:\log\cons3rt-install-$LOGTAG-$TIMESTAMP.log"

# Deployment properties file
$propFile="$env:DEPLOYMENT_HOME/deployment.properties"

# Root directory for pycons3rt
$pycons3rtRootDir = "C:\pycons3rt"
$sourceDir = "$pycons3rtRootDir/src/pycons3rt"

# Git clone URL
$gitUrl = "https://github.com/cons3rt/pycons3rt.git"

# Default branch to clone
$defaultBranch = "master"

######################### END VARIABLES #############################

######################## HELPER FUNCTIONS ############################

# Set up logging functions
function logger($level, $logstring) {
   $stamp = get-date -f yyyyMMdd-HHmmss
   $logmsg = "$stamp - $LOGTAG - [$level] - $logstring"
   write-output $logmsg
}
function logErr($logstring) { logger "ERROR" $logstring }
function logWarn($logstring) { logger "WARNING" $logstring }
function logInfo($logstring) { logger "INFO" $logstring }

###################### END HELPER FUNCTIONS ##########################

######################## SCRIPT EXECUTION ############################

new-item $logfile -itemType file -force
start-transcript -append -path $logfile
logInfo "Running $LOGTAG..."

try {
	logInfo "Installing $LOGTAG at: $TIMESTAMP"

	if ( test-path $propFile ) {
        logInfo "Found deployment properties file: $propFile"

        # Get the branch from the deployment.properties file
        $branch = Get-Content $propFile | Select-String PYCONS3RT_BRANCH | foreach {$d = $_ -split "="; Write-Output $d[1] }

        if ( ! $branch ) {
            logInfo "PYCONS3RT_BRANCH deployment property not found in deployment properties, using default branch: $defaultBranch"
            $branch = $defaultBranch
        }
        else {
            logInfo "Found PYCONS3RT_BRANCH set to: $branch"
        }
    }
    else {
        logInfo "Deployment properties file not found, using default branch: $defaultBranch"
        $branch = $defaultBranch
    }

    logInfo "Creating directory: $sourceDir..."
    mkdir $sourceDir

    # Clone the pycons3rt source
    logInfo "Cloning pycons3rt source code..."
    git clone -b $branch $gitUrl $sourceDir

    # Ensure the install script was found
    if ( test-path $sourceDir\scripts\install.ps1 ) {
        logInfo "Found the pycons3rt install script"
    }
    else {
        $errMsg="pycons3rt install script not found, git clone may not have succeeded: $sourceDir\scripts\install.ps1"
        logErr $errMsg
        throw $errMsg
    }

    # Install PIP prerequisites
    pip install awscli
    pip install boto3
    pip install netifaces
    pip install jinja2
    pip install requests==2.10.0
    pip install requests[security]

    # Run the pycons3rt setup
    logInfo "Installing pycons3rt..."
    cd $sourceDir
    powershell -NoLogo -Noninteractive -ExecutionPolicy Bypass -File .\scripts\install.ps1
    $result = $lastexitcode

    if ( $result -ne 0 ) {
        $errMsg="There was a problem setting up pycons3rt"
        logErr $errMsg
        throw $errMsg
    }

    # Ensure the osutil script was found
    $osutil = "$sourceDir\pycons3rt\osutil.py"
    if ( test-path $osutil ) {
        logInfo "Found the pycons3rt osutil: $osutil"
    }
    else {
        $errMsg="pycons3rt osutil not found: $osutil"
        logErr $errMsg
        throw $errMsg
    }

    # Run the osutil to configure logging and directories
    python $osutil
    $result = $lastexitcode

    if ( $result -ne 0 ) {
        $errMsg="There was a problem running osutil"
        logErr $errMsg
        throw $errMsg
    }

	logInfo "Completed $LOGTAG installation"
}
catch {
    logErr "Caught exception: $_"
    $exitCode = 1
}
finally {
    logInfo "$LOGTAG complete in $($stopwatch.Elapsed)"
}

###################### END SCRIPT EXECUTION ##########################

logInfo "Exiting with code: $exitCode"
stop-transcript
get-content -Path $logfile
exit $exitCode
