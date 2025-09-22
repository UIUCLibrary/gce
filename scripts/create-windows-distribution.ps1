param (
    [string]$uvExec,
    [string]$buildpath = "build"
)
$BOOTSTRAP_SCRIPT = Join-Path -Path $PSScriptRoot -ChildPath "create_standalone/bootstrap_standalone.py"
$FREEZE_SCRIPT = Join-Path -Path $PSScriptRoot -ChildPath "create_standalone/create_standalone.py"

function Get-UV() {
    [CmdletBinding()]
    param (
        [Parameter(mandatory=$true)]
        [string]$buildPath
    )
    if (Get-Command "uv" -ErrorAction SilentlyContinue)
    {
        return "$(Get-Command uv)"
    }
    py -m venv $buildpath\venv
    & "$buildPath\venv\Scripts\pip.exe" --disable-pip-version-check install uv | Out-Host -Paging
    return Join-Path "$buildPath" -ChildPath "venv\Scripts\uv.exe"

}
function Get-Wix{
    [CmdletBinding()]
    param (
        [Parameter(mandatory=$true)]
        [string]$path
    )
    $wix = $(Get-Command wix -ErrorAction SilentlyContinue)
    if ($wix){
        $wix = Get-Item -Path $wix.Source
        Write-Host "WiX found at $($wix.FullName)"
    } else {
        $wix = Get-ChildItem -Path $path -Recurse -File -Filter 'wix.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($wix -ne $null -and $wix -ne ""){
            Write-Host "WiX found at $($wix.FullName)"
        }
    }
    if ($wix -eq $null -or $wix -eq "")
    {
        $dotnetCommand = $( Get-Command dotnet )
        if (-not $dotnetCommand)
        {
            throw "The .NET SDK is required to install the WiX Toolset. Please install it from https://dotnet.microsoft.com/en-us/download"
        }
        Write-Host "Installing WiX Toolset"
        $WixPath = Join-Path -Path $path -ChildPath "WiX"
        & $dotnetCommand tool install --tool-path "$WixPath" wix --version 4.0.4 | Out-Host -Paging
        $wix = Get-ChildItem -Path "$WixPath" -Recurse -File -Filter 'wix.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $wix)
        {
            throw "WiX installation failed. 'wix.exe' not found in '$path\WiX'."
        }
    }
    $env:WIX_EXTENSIONS = "$path\WixExtensions"
    if (-not (Test-Path -Path $env:WIX_EXTENSIONS)) {
        New-Item -ItemType Directory -Path $env:WIX_EXTENSIONS | Out-Null
        & "$($wix.FullName)" extension add --global WixToolset.UI.wixext/4.0.4 | Out-Host -Paging
    }
    return $wix.DirectoryName
}

function Build-Standalone
{
    [CmdletBinding()]
    param (
        [Parameter(mandatory = $true)]
        [string]$Uv,
        [Parameter(mandatory = $true)]
        [string]$WixPath
    )
    & {$env:WIX = $WixPath; & "$Uv" run --isolated --frozen --group freeze --no-dev "$FREEZE_SCRIPT" gce "$BOOTSTRAP_SCRIPT" }
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Building Standalone - Success"
    } else {
        throw "Building Standalone - Failed"

    }}

Write-Host "Creating Windows Distribution"
$wixPath = Get-Wix -path $buildpath
if ($uvExec -eq $null -or $uvExec -eq ""){
    $uvExec = Get-UV $buildpath
}
Build-Standalone -Uv "$uvExec" -WixPath "$wixPath"
