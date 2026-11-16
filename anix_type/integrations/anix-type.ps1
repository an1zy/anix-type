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
        [int]$TimeoutMs = 150
    )
    try {
        $json = $Body | ConvertTo-Json -Compress
        $req = [System.Net.HttpWebRequest]::Create("$global:AnixTypeUrl$Endpoint")
        $req.Method = "POST"
        $req.ContentType = "application/json; charset=utf-8"
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
        # Daemon is not running or timed out — fail silently to never block typing
        return $null
    }
}

function Get-AnixTypeStatus {
    try {
        $req = [System.Net.HttpWebRequest]::Create("$global:AnixTypeUrl/health")
        $req.Timeout = 300
        $resp = $req.GetResponse()
        $resp.Close()
        return $true
    }
    catch {
        return $false
    }
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
            [Microsoft.PowerShell.PSConsoleReadLine]::Replace(0, $line.Length, $res.command)
            return
        }
    }

    # 2. Check if cursor is at the end and we have a prediction
    if ($cursor -eq $line.Length -and $line.Trim().Length -gt 0) {
        $sug = Invoke-AnixTypeApi -Endpoint "/suggest" -Body @{
            line   = $line
            cursor = $cursor
            cwd    = (Get-Location).Path
        } -TimeoutMs 200

        if ($sug -and $sug.suffix) {
            [Microsoft.PowerShell.PSConsoleReadLine]::Insert($sug.suffix)
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
        } -TimeoutMs 150

        if ($sug -and $sug.suffix) {
            [Microsoft.PowerShell.PSConsoleReadLine]::Insert($sug.suffix)
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
            [Microsoft.PowerShell.PSConsoleReadLine]::Replace(0, $line.Length, $res.command)
            return
        }
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
        } -TimeoutMs 250

        if ($sug -and $sug.suffix) {
            [Microsoft.PowerShell.PSConsoleReadLine]::Insert($sug.suffix)
        }
    }
}
