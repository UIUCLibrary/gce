Write-Host 'Checking that application has properly installed'
[int]$NumberOfTestsPerformed=0
$IsValid = $true
function CheckInstalled( [string]$Name) {
    Write-Host "Checking Windows Management Win32 for <$APP_NAME>"
    $results = Get-WmiObject -Class Win32_Product -Filter "name = '$Name'"
    if (($results.Count) -ne 0)
    {
        Write-Host "Windows Management Win32 Product - Found"
        return $true
    }
    Write-Host "Windows Management Win32 Product - NOT FOUND"
    return $false

}

$APP_NAME = 'Galatea Config Editor'

if(!$(CheckInstalled -Name $APP_NAME)){
    $IsValid = $false
}
$NumberOfTestsPerformed++

Write-Host "$NumberOfTestsPerformed tests performed."
if ($NumberOfTestsPerformed -gt 0){
    if ($IsValid)
    {
        Write-Host "Success!"
        exit 0
    } else {
        Write-Host "Failed!"
        exit 1
    }

}
