# install.ps1
# Created by Joe Yennaco (9/6/2016)

# The purpose of this script is to install pycons3rt into your local
# python installation

# To automate the install, execute this script like this:
# start /wait powershell -NoLogo -Noninteractive -ExecutionPolicy Bypass -File C:\path\to\install.ps1

$scriptPath = $MyInvocation.MyCommand.Path
$scriptDir = Split-Path $scriptPath
$pycons3rtDir = "$scriptDir\.."
cd $pycons3rtDir
python .\setup.py install
exit $lastexitcode
