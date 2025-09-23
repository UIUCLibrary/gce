$IsValid = $true

[int]$NumberOfTestsPerformed=0

function CheckUninstalled( [string]$Name){
    Write-Host "Checking Application not installed"
    $results = Get-WmiObject -Class Win32_Product -Filter "name = '$Name'"
    if (($results.Count) -ne 0){
        Write-Host "Checking Application not installed - Failed"
        return $false
    } else {
        Write-Host "Checking Application not installed - Passed"
        return $true
    }
}

if(!$(CheckUninstalled 'Galatea Config Editor')){
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
