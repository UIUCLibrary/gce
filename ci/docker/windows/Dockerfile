# escape=`
FROM mcr.microsoft.com/dotnet/sdk:9.0-windowsservercore-ltsc2025
SHELL ["powershell", "-Command", "$ErrorActionPreference = 'Stop'; $ProgressPreference = 'SilentlyContinue';"]
RUN Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser;`
    Invoke-RestMethod -Uri https://get.scoop.sh -outfile install-scoop.ps1 ; .\install-scoop.ps1 -RunAsAdmin; `
    scoop install main/uv ; `
    Remove-Item install-scoop.ps1 ;`
    dotnet tool install --global wix --version 4.0.4;`
    wix extension add --global WixToolset.UI.wixext/4.0.4
