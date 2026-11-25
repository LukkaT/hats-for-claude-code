# Hats for Claude Code: PowerShell integration (PowerShell 7 and Windows PowerShell 5.1).
# All logic is in hat.py; this file only hooks it into the prompt and the `claude` command.

if (-not $env:HAT_HOME) { $env:HAT_HOME = Join-Path $HOME '.config/hats' }
# The installer records which Python to use; if that one is gone, use any.
if (-not ($env:HAT_PYTHON -and (Test-Path -LiteralPath $env:HAT_PYTHON))) {
    $env:HAT_PYTHON = $null
    $found = Get-Command python3, python -CommandType Application -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -notlike '*\WindowsApps\*' } | Select-Object -First 1
    if ($found) { $env:HAT_PYTHON = $found.Source }
}
$global:HatCore = Join-Path $env:HAT_HOME 'hat.py'
$env:HAT_HOOK = 'pwsh'  # lets `hat doctor` see that this terminal is hooked

# Runs hat.py and returns what it prints, read as UTF-8. The arguments travel as one
# array so that ones starting with "--" are never read as PowerShell parameters.
function global:Invoke-HatCapture([string[]]$CoreArgs) {
    $saved = [Console]::OutputEncoding
    try {
        [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
        $out = & $env:HAT_PYTHON $global:HatCore @CoreArgs
    } finally {
        [Console]::OutputEncoding = $saved
    }
    return ($out -join "`n")
}

function global:Test-HatReady { [bool]$env:HAT_PYTHON -and (Test-Path -LiteralPath $global:HatCore) }

# `claude` starts on the account shown in the prompt. If Hats has been removed,
# it is the normal claude again.
function global:claude {
    if (Test-HatReady) {
        & $env:HAT_PYTHON $global:HatCore claude @args
    } else {
        $real = Get-Command claude -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($real) { & $real.Source @args } else { Write-Error 'claude is not installed' }
    }
}

function global:hat {
    if (-not (Test-HatReady)) { Write-Error 'hat is not installed (or Python was not found)'; return }
    if ($args.Count -eq 0 -or @('pick', 'use', 'auto') -contains $args[0]) {
        # These change this terminal's environment: hat.py prints the code to run.
        $code = Invoke-HatCapture -CoreArgs (@('--shell', 'pwsh', '--eval') + $args)
        if ($code) { Invoke-Expression $code }
    } else {
        & $env:HAT_PYTHON $global:HatCore @args
    }
}

# Put the account name in front of whatever prompt is already set up.
if (-not $global:HatOriginalPrompt) { $global:HatOriginalPrompt = $function:prompt }
function global:prompt {
    $exit = $global:LASTEXITCODE
    $out = ''
    if (Test-HatReady) {
        try { $out = Invoke-HatCapture -CoreArgs @('--shell', 'pwsh', 'prompt') 2>$null } catch { $out = '' }
    }
    $global:LASTEXITCODE = $exit
    $seg = ''
    if ($out) {
        $parts = $out -split [char]0x1f, 2
        $seg = $parts[0]
        if ($parts.Count -gt 1 -and $parts[1]) { $Host.UI.RawUI.WindowTitle = $parts[1] }
    }
    $seg + (& $global:HatOriginalPrompt)
}

# F2 opens the account menu.
if (Get-Command Set-PSReadLineKeyHandler -ErrorAction SilentlyContinue) {
    Set-PSReadLineKeyHandler -Key F2 -BriefDescription 'hat' -Description 'Pick the Claude account' -ScriptBlock {
        [Microsoft.PowerShell.PSConsoleReadLine]::RevertLine()
        [Microsoft.PowerShell.PSConsoleReadLine]::Insert('hat')
        [Microsoft.PowerShell.PSConsoleReadLine]::AcceptLine()
    }
}
