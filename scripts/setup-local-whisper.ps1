$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$toolsDir = Join-Path $projectRoot 'tools\whisper'
$modelsDir = Join-Path $projectRoot 'models'
$archive = Join-Path $projectRoot 'tools\whisper-windows.zip'
$extractDir = Join-Path $projectRoot 'tools\whisper-extracted'
$modelPath = Join-Path $modelsDir 'ggml-small.en-tdrz.bin'

New-Item -ItemType Directory -Force -Path $toolsDir, $modelsDir | Out-Null

Write-Host 'Finding the latest official whisper.cpp Windows release...'
$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/ggml-org/whisper.cpp/releases/latest'
$asset = $release.assets | Where-Object { $_.name -eq 'whisper-bin-x64.zip' } | Select-Object -First 1
if (-not $asset) { throw 'The latest whisper.cpp release does not contain whisper-bin-x64.zip.' }

Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $archive
if (Test-Path -LiteralPath $extractDir) { Remove-Item -LiteralPath $extractDir -Recurse -Force }
Expand-Archive -LiteralPath $archive -DestinationPath $extractDir -Force
$cli = Get-ChildItem -LiteralPath $extractDir -Recurse -Filter 'whisper-cli.exe' | Select-Object -First 1
if (-not $cli) { throw 'whisper-cli.exe was not found in the downloaded release.' }
Copy-Item -Path (Join-Path $cli.DirectoryName '*') -Destination $toolsDir -Recurse -Force

Write-Host 'Downloading the free small.en tinydiarize model (about 500 MB)...'
$modelUrl = 'https://huggingface.co/akashmjn/tinydiarize-whisper.cpp/resolve/main/ggml-small.en-tdrz.bin'
& curl.exe --location --fail --retry 3 --continue-at - --output $modelPath $modelUrl
if ($LASTEXITCODE -ne 0) { throw "The model download failed with curl exit code $LASTEXITCODE." }
$expectedSha1 = 'b6c6e7e89af1a35c08e6de56b66ca6a02a2fdfa1'
$actualSha1 = (Get-FileHash -LiteralPath $modelPath -Algorithm SHA1).Hash.ToLowerInvariant()
if ($actualSha1 -ne $expectedSha1) {
  Remove-Item -LiteralPath $modelPath -Force
  throw "The downloaded model failed its checksum verification. Expected $expectedSha1 but received $actualSha1."
}

Remove-Item -LiteralPath $archive -Force
Remove-Item -LiteralPath $extractDir -Recurse -Force
Write-Host "Local Whisper is ready at $toolsDir"
Write-Host 'Restart npm run dev:full, upload audio, and click Transcribe.'
