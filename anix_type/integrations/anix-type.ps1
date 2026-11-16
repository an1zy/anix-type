# ANIX Type — PowerShell integration module
# Hooked into PSReadLine for instant Tab completions and ?? command forging.

if (-not (Get-Module -Name PSReadLine)) {
    Import-Module PSReadLine -ErrorAction SilentlyContinue
}

$global:AnixTypePort = 8766
$global:AnixTypeUrl = "http://127.0.0.1:$global:AnixTypePort"

function Invoke-AnixTypeApi {
    param(
        [string]$Endpoint,
        [hashtable]$Body,
        [int]$TimeoutMs = 500
    )
    try {
        $json = $Body | ConvertTo-Json -Compress
        $req = [System.Net.HttpWebRequest]::Create("$global:AnixTypeUrl$Endpoint")
        $req.Method = "POST"
        $req.ContentType = "application/json; charset=utf-8"
        $req.Proxy = $null  # Bypass Windows WPAD proxy resolution (drops latency from 50ms to 2ms)
        $req.Timeout = $TimeoutMs
        $req.ReadWriteTimeout = $TimeoutMs

        $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
        $req.ContentLength = $bytes.Length
        $stream = $req.GetRequestStream()
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Close()

        $resp = $req.GetResponse()
        $reader = New-Object System.IO.StreamReader($resp.GetResponseStream(), [System.Text.Encoding]::UTF8)
        $resText = $reader.ReadToEnd()
        $reader.Close()
        $resp.Close()

        return ($resText | ConvertFrom-Json)
    }
    catch {
        # Fail silently on timeout or error to never block typing
        return $null
    }
}

function Get-AnixTypeStatus {
    try {
        $req = [System.Net.HttpWebRequest]::Create("$global:AnixTypeUrl/health")
        $req.Proxy = $null
        $req.Timeout = 400
        $resp = $req.GetResponse()
        $resp.Close()
        return $true
    }
    catch {
        return $false
    }
}

# Auto-start daemon in background if not already running
function Ensure-AnixTypeDaemon {
    if (-not (Get-AnixTypeStatus)) {
        $pwCmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
        $pythonw = if ($pwCmd) { $pwCmd.Source } else { "pythonw.exe" }
        Start-Process -FilePath $pythonw -ArgumentList "-m anix_type daemon --port $global:AnixTypePort" -WindowStyle Hidden -ErrorAction SilentlyContinue
    }
}
Ensure-AnixTypeDaemon

# Helper to safely replace current input buffer without throwing overload exceptions
function Set-AnixTypeLine {
    param([string]$NewText)
    $curLine = $null
    $curPos = $null
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$curLine, [ref]$curPos)
    if ($curLine -and $curLine.Length -gt 0) {
        [Microsoft.PowerShell.PSConsoleReadLine]::Delete(0, $curLine.Length)
    }
    if (-not [string]::IsNullOrEmpty($NewText)) {
        [Microsoft.PowerShell.PSConsoleReadLine]::Insert($NewText)
    }
}

function Apply-AnixTypeSuggestion {
    param($sug, $line, $cursor)
    if (-not $sug) { return $false }

    # If suffix is available and cursor is at the end of line, simply insert suffix
    if ($sug.suffix -and ($cursor -eq $line.Length)) {
        [Microsoft.PowerShell.PSConsoleReadLine]::Insert($sug.suffix)
        return $true
    }
    if ($sug.text) {
        Set-AnixTypeLine $sug.text
        return $true
    }
    return $false
}

# --- PSReadLine Key Handlers ---

# 1. TAB: complete prediction OR forge ?? prompt
Set-PSReadLineKeyHandler -Key Tab -BriefDescription "ANIX Type Tab Complete" -ScriptBlock {
    param($key, $arg)

    $line = $null
    $cursor = $null
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

    # 1. Check if it is a natural language command forge: ?? ...
    if ($line -match '^\s*\?\?\s*(.+)$') {
        $prompt = $matches[1]
        $res = Invoke-AnixTypeApi -Endpoint "/forge" -Body @{
            prompt = $prompt
            shell  = "powershell"
            cwd    = (Get-Location).Path
        } -TimeoutMs 4000

        if ($res -and $res.command) {
            Set-AnixTypeLine $res.command
            return
        }
    }

    # 2. Check if cursor is at the end and we have a prediction
    if ($cursor -eq $line.Length -and $line.Trim().Length -gt 0) {
        $sug = Invoke-AnixTypeApi -Endpoint "/suggest" -Body @{
            line   = $line
            cursor = $cursor
            cwd    = (Get-Location).Path
        } -TimeoutMs 400

        if (Apply-AnixTypeSuggestion -sug $sug -line $line -cursor $cursor) {
            return
        }
    }

    # 3. Fallback to native PowerShell completion
    [Microsoft.PowerShell.PSConsoleReadLine]::TabCompleteNext($key, $arg)
}

# 2. RightArrow: accept completion when at the end of the line
Set-PSReadLineKeyHandler -Key RightArrow -BriefDescription "ANIX Type RightArrow Complete" -ScriptBlock {
    param($key, $arg)

    $line = $null
    $cursor = $null
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

    if ($cursor -eq $line.Length -and $line.Trim().Length -gt 0) {
        $sug = Invoke-AnixTypeApi -Endpoint "/suggest" -Body @{
            line   = $line
            cursor = $cursor
            cwd    = (Get-Location).Path
        } -TimeoutMs 300

        if (Apply-AnixTypeSuggestion -sug $sug -line $line -cursor $cursor) {
            return
        }
    }

    [Microsoft.PowerShell.PSConsoleReadLine]::ForwardChar($key, $arg)
}

# 3. ENTER on '?? ...': forge command and replace in prompt
Set-PSReadLineKeyHandler -Key Enter -BriefDescription "ANIX Type Enter Forge" -ScriptBlock {
    param($key, $arg)

    $line = $null
    $cursor = $null
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

    if ($line -match '^\s*\?\?\s*(.+)$') {
        $prompt = $matches[1]
        $res = Invoke-AnixTypeApi -Endpoint "/forge" -Body @{
            prompt = $prompt
            shell  = "powershell"
            cwd    = (Get-Location).Path
        } -TimeoutMs 4000

        if ($res -and $res.command) {
            Set-AnixTypeLine $res.command
            return
        }
        if ($res -and $res.explanation) {
            Write-Host "`n⚡ $($res.explanation)" -ForegroundColor Yellow
            return
        }
        return
    }

    [Microsoft.PowerShell.PSConsoleReadLine]::AcceptLine($key, $arg)
}

# 4. Ctrl+Spacebar: manual trigger for suggestion
Set-PSReadLineKeyHandler -Chord 'Ctrl+Spacebar' -BriefDescription "ANIX Type Trigger" -ScriptBlock {
    param($key, $arg)

    $line = $null
    $cursor = $null
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

    if ($line.Trim().Length -gt 0) {
        $sug = Invoke-AnixTypeApi -Endpoint "/suggest" -Body @{
            line   = $line
            cursor = $cursor
            cwd    = (Get-Location).Path
        } -TimeoutMs 400

        Apply-AnixTypeSuggestion -sug $sug -line $line -cursor $cursor
    }
}

Write-Host "⚡ ANIX Type ready" -ForegroundColor DarkGray
