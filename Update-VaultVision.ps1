$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = $PSScriptRoot
$exe = Join-Path $root 'VaultVision.exe'
$headers = @{ 'User-Agent' = 'VaultVision-Updater'; 'Accept' = 'application/vnd.github+json' }
$work = Join-Path $env:TEMP ('VaultVision-update-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null
$installed = @()
$backedUp = @()
$cleanup = $true
$backup = Join-Path $work 'backup'
try {
    Write-Host 'Checking the latest successful VaultVision build...'
    $release = Invoke-RestMethod -Headers $headers -Uri 'https://api.github.com/repos/Buhlistik/VaultVision/releases/tags/latest'
    $zipAsset = @($release.assets | Where-Object { $_.name -eq 'VaultVision-Windows.zip' })
    $hashAsset = @($release.assets | Where-Object { $_.name -eq 'VaultVision-Windows.zip.sha256' })
    if ($zipAsset.Count -ne 1 -or $hashAsset.Count -ne 1) { throw 'The latest build is not published yet. Try again shortly.' }
    $zip = Join-Path $work 'build.zip'
    $hash = Join-Path $work 'build.sha256'
    Write-Host 'Downloading the Windows build...'
    Invoke-WebRequest -UseBasicParsing -Uri $zipAsset[0].browser_download_url -OutFile $zip
    Invoke-WebRequest -UseBasicParsing -Uri $hashAsset[0].browser_download_url -OutFile $hash
    $expected = (Get-Content -Raw $hash).Trim().Split(' ')[0]
    if ($expected -notmatch '^[a-fA-F0-9]{64}$' -or (Get-FileHash $zip -Algorithm SHA256).Hash -ne $expected) {
        throw 'Download checksum verification failed. Existing files were not changed.'
    }
    # Validate archive paths before extraction.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($zip)
    try {
        foreach ($entry in $archive.Entries) {
            if ($entry.FullName -match '(^[/\\]|(^|[/\\])\.\.([/\\]|$)|:)') {
                throw 'The archive contains an invalid path.'
            }
        }
    } finally { $archive.Dispose() }
    $stage = Join-Path $work 'staged'
    Expand-Archive -LiteralPath $zip -DestinationPath $stage
    if (!(Test-Path (Join-Path $stage 'VaultVision.exe')) -or !(Test-Path (Join-Path $stage '_internal'))) {
        throw 'The downloaded build has an unexpected layout. Existing files were not changed.'
    }
    Write-Host 'Closing VaultVision before replacing its files...'
    foreach ($process in @(Get-Process -Name 'VaultVision' -ErrorAction SilentlyContinue)) {
        if ($process.Path -and [IO.Path]::GetFullPath($process.Path) -eq [IO.Path]::GetFullPath($exe)) {
            if (!$process.CloseMainWindow()) { throw 'Close VaultVision manually, then run this updater again.' }
            if (!$process.WaitForExit(60000)) { throw 'VaultVision is still closing. Close it manually and run the updater again.' }
        }
    }
    New-Item -ItemType Directory -Path $backup | Out-Null
    # Only replace app-owned files, leaving clips and other local files alone.
    foreach ($name in @('VaultVision.exe', '_internal', 'Update-VaultVision.cmd', 'Update-VaultVision.ps1')) {
        $incoming = Join-Path $stage $name
        if (!(Test-Path $incoming)) { continue }
        $target = Join-Path $root $name
        if (Test-Path $target) {
            Move-Item -LiteralPath $target -Destination (Join-Path $backup $name)
            $backedUp += $name
        }
        $installed += $name
        Move-Item -LiteralPath $incoming -Destination $target
    }
    Write-Host 'VaultVision updated successfully. You can open VaultVision.exe now.' -ForegroundColor Green
} catch {
    $failure = $_.Exception.Message
    $cleanup = $false
    try {
    foreach ($name in $installed) {
        $target = Join-Path $root $name
        if (Test-Path $target) { Remove-Item -LiteralPath $target -Recurse -Force }
    }
    foreach ($name in $backedUp) {
        Move-Item -LiteralPath (Join-Path $backup $name) -Destination (Join-Path $root $name)
    }
    $cleanup = $true
    } catch {
        Write-Host ('Could not finish restoring files. Backup retained at: ' + $backup) -ForegroundColor Red
    }
    Write-Host ('Update failed: ' + $failure) -ForegroundColor Red
    exit 1
} finally {
    if ($cleanup -and (Test-Path $work)) { Remove-Item -LiteralPath $work -Recurse -Force }
}
