<#
.SYNOPSIS
    Cleans compiled plugin artifacts (Binaries/Intermediate) for a specified plugin or for all plugins.

.DESCRIPTION
    This PowerShell helper will delete the "Binaries" and "Intermediate" directories for a named plugin
    (e.g. "SOTS_TagManager") or all plugins under the project's Plugins directory. Use with caution.

.EXAMPLE
    # Clean a single plugin
    .\clean_plugin_artifacts.ps1 -PluginName SOTS_TagManager

    # Clean all plugins
    .\clean_plugin_artifacts.ps1 -PluginName All

.NOTES
    - If Unreal Editor or build tools are running, they may hold files open causing deletion to fail.
    - The script intentionally refuses to kill processes. Close the editor/programs manually first.
#>

param (
    [Parameter(Mandatory = $true)]
    [string]$PluginName
)

# Resolve project root by assuming this script runs from <Project>/DevTools
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot

$PluginsPath = Join-Path $ProjectRoot 'Plugins'

if (-not (Test-Path $PluginsPath)) {
    Write-Error "Plugins path not found: $PluginsPath"
    exit 1
}

# Ensure user closed the Unreal Editor / UBT before deletion to avoid locked files
$editorProcess = Get-Process -Name 'UnrealEditor' -ErrorAction SilentlyContinue
if ($editorProcess) {
    Write-Warning "Detected running Unreal Editor process(es). Please close the Editor before cleaning build artifacts. Exiting."
    exit 2
}

$pluginsToClean = @()
if ($PluginName -eq 'All') {
    $pluginsToClean = Get-ChildItem -Path $PluginsPath -Directory | ForEach-Object { $_.Name }
} else {
    if ((Test-Path (Join-Path $PluginsPath $PluginName))) {
        $pluginsToClean = @($PluginName)
    } else {
        Write-Error "Plugin not found: $PluginName"
        exit 3
    }
}

foreach ($p in $pluginsToClean) {
    Write-Host "Cleaning plugin: $p"
    $pluginPath = Join-Path $PluginsPath $p
    $binariesPath = Join-Path $pluginPath 'Binaries'
    $intermediatePath = Join-Path $pluginPath 'Intermediate'

    if (Test-Path $binariesPath) {
        try {
            Remove-Item -Path $binariesPath -Recurse -Force -ErrorAction Stop
            Write-Host "Removed: $binariesPath"
        } catch {
            Write-Warning "Failed to remove $binariesPath: $_.Exception.Message"
        }
    } else {
        Write-Host "Binaries path does not exist: $binariesPath"
    }

    if (Test-Path $intermediatePath) {
        try {
            Remove-Item -Path $intermediatePath -Recurse -Force -ErrorAction Stop
            Write-Host "Removed: $intermediatePath"
        } catch {
            Write-Warning "Failed to remove $intermediatePath: $_.Exception.Message"
        }
    } else {
        Write-Host "Intermediate path does not exist: $intermediatePath"
    }
}

Write-Host "Done. If any files were locked, close the editor or build processes, then re-run this script."