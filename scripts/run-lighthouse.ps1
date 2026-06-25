param(
    [string]$Url = "http://127.0.0.1:5055/"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$reportsDir = Join-Path $projectRoot "reports\lighthouse"
$profileDir = Join-Path $projectRoot (".lighthouse-profile\run-" + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
$chromePath = if ($env:CHROME_PATH) {
    $env:CHROME_PATH
} else {
    "C:\Program Files\Google\Chrome\Application\chrome.exe"
}
$waitressPath = Join-Path $projectRoot ".venv\Scripts\waitress-serve.exe"

if (-not (Test-Path -LiteralPath $chromePath)) {
    throw "Chrome was not found. Set CHROME_PATH to chrome.exe."
}
if (-not (Test-Path -LiteralPath $waitressPath)) {
    throw "Waitress is missing. Run .\.venv\Scripts\python.exe -m pip install -r requirements.txt."
}

New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null
New-Item -ItemType Directory -Force -Path $profileDir | Out-Null

$server = $null
$chrome = $null

try {
    $server = Start-Process `
        -FilePath $waitressPath `
        -ArgumentList "--host=127.0.0.1", "--port=5055", "app:app" `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -PassThru

    $ready = $false
    foreach ($attempt in 1..30) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $ready) {
        throw "The local storefront did not become ready at $Url."
    }

    $chrome = Start-Process `
        -FilePath $chromePath `
        -ArgumentList "--headless=new", "--remote-debugging-address=127.0.0.1", "--remote-debugging-port=9222", "--user-data-dir=`"$profileDir`"", "--no-first-run", "--disable-gpu", "--remote-allow-origins=*" `
        -WindowStyle Hidden `
        -PassThru

    $chromeReady = $false
    foreach ($attempt in 1..30) {
        try {
            $debugInfo = Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version" -TimeoutSec 2
            if ($debugInfo.webSocketDebuggerUrl) {
                $chromeReady = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $chromeReady) {
        throw "Chrome remote debugging did not become ready on port 9222."
    }

    & npx.cmd --no-install lighthouse $Url `
        --port=9222 `
        --preset=desktop `
        --only-categories=performance,accessibility,best-practices,seo `
        --output=html `
        --output=json `
        --output-path="$reportsDir\home" `
        --quiet

    if ($LASTEXITCODE -ne 0) {
        throw "Lighthouse exited with code $LASTEXITCODE."
    }

    Write-Output "Lighthouse reports created in $reportsDir"
} finally {
    if ($chrome -and -not $chrome.HasExited) {
        Stop-Process -Id $chrome.Id -Force -ErrorAction SilentlyContinue
    }
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    }
}
