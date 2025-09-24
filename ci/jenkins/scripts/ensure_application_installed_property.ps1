Write-Host 'Checking that application has properly installed'
[int]$NumberOfTestsPerformed=0
$IsValid = $true

function CheckShortCut([string]$StartMenuShortCut){

        Write-Host "Looking for Windows start menu Shortcut"
        $AllUsersStartMenuPath = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs"
        $expectedShortcutPath = Join-Path -Path "$AllUsersStartMenuPath" -ChildPath "$StartMenuShortCut.lnk"
        if (!([System.IO.File]::Exists("$expectedShortcutPath"))){
            Write-Host "Windows start menu Shortcut - Not Found"
            Write-Host "    Searched for shortcut at: $expectedShortcutPath"
            Get-ChildItem -Path $AllUsersStartMenuPath -Recurse -Include *.lnk | ForEach-Object {
                Write-Host "    Found shortcut: $($_.FullName)"
            }
            return $false
        } else {
            Write-Host "Windows start menu Shortcut - Found"
            return $true
        }
}
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

if(!$(CheckShortCut -StartMenuShortCut 'Galatea Config Editor\Galatea Config Editor')){
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
