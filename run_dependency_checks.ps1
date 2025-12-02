<#
Small helper to run plugin dependency health and module checking Python scripts.
#>

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot

# Change to project root to run scripts
Set-Location $ProjectRoot

Write-Host "Running plugin_dependency_health.py"
try {
    python DevTools\python\plugin_dependency_health.py
} catch {
    Write-Warning "Running plugin_dependency_health.py failed: $_"
}

Write-Host "Running ensure_plugin_modules.py"
try {
    python DevTools\python\ensure_plugin_modules.py
} catch {
    Write-Warning "Running ensure_plugin_modules.py failed: $_"
}

Write-Host "Running fix_plugin_dependencies.py (dry-run mode if provided)"
try {
    python DevTools\python\fix_plugin_dependencies.py --dry-run
} catch {
    Write-Warning "Running fix_plugin_dependencies.py failed: $_"
}

Write-Host "Completed dependency checks."