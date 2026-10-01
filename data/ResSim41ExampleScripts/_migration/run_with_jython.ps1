# Runs one of the migration scripts under ResSim's own Jython, using ResSim's
# jars and ResSim's bundled Java. Nothing else needs to be installed -- no
# CPython, no Java on PATH.
#
# Import smoke test (the default):
#   .\run_with_jython.ps1 -Install "C:\Program Files\HEC\HEC-ResSim\4.1"
#
# Build the catalog:
#   .\run_with_jython.ps1 -Install "...\4.1" -Script catalog_imports.py
#
# Check the jars, passing the install path through to the script:
#   .\run_with_jython.ps1 -Install "...\4.1" -Script check_against_install.py -ScriptArgs "C:\Program Files\HEC\HEC-ResSim\4.1"
#
# No watershed is opened and nothing is computed.

param(
    [Parameter(Mandatory=$true)][string]$Install,
    [string]$Script = 'smoketest_imports.py',
    [string[]]$ScriptArgs = @()
)

if (-not (Test-Path $Install)) {
    Write-Error "No such directory: $Install"
    exit 1
}

# Wildcard classpath entries are expanded by Java itself, so this survives a
# change in how the jars are laid out between versions.
$jarDirs = Get-ChildItem -Path $Install -Recurse -Filter *.jar |
    ForEach-Object { $_.DirectoryName } | Sort-Object -Unique
if ($jarDirs.Count -eq 0) {
    Write-Error "No .jar files found under $Install"
    exit 1
}
$classPath = ($jarDirs | ForEach-Object { Join-Path $_ '*' }) -join ';'
Write-Host "Found jars in $($jarDirs.Count) directory(ies) under $Install"

# Prefer the JRE shipped with ResSim, so this uses the Java it really runs on
$java = Get-ChildItem -Path $Install -Recurse -Filter java.exe -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($java) {
    $javaExe = $java.FullName
    Write-Host "Using bundled Java: $javaExe"
} else {
    $javaExe = 'java'
    Write-Host "No bundled java.exe found, falling back to java on PATH"
}

# It has to be the directory holding javaHeclib.dll specifically. Taking the
# first .dll found anywhere lands on the JRE's own dlls in java\bin, and then
# every DSS class fails to initialise for a reason that has nothing to do with
# the migration.
$heclib = Get-ChildItem -Path $Install -Recurse -Filter javaHeclib.dll -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($heclib) {
    $libPath = $heclib.DirectoryName
    Write-Host "Native library path: $libPath"
} else {
    $libPath = $Install
    Write-Warning "javaHeclib.dll not found under $Install. Every DSS class will fail to initialise."
}

$scriptPath = Join-Path $PSScriptRoot $Script
if (-not (Test-Path $scriptPath)) {
    Write-Error "No such script: $scriptPath"
    exit 1
}

Write-Host "Running $Script"
Write-Host ''
& $javaExe "-Djava.library.path=$libPath" -cp $classPath org.python.util.jython $scriptPath @ScriptArgs
