# Video-Compress MPV Plugin Auto-Installer
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$destinations = @(
    "$env:APPDATA\mpv",
    "$env:USERPROFILE\.config\mpv"
)

Write-Host "================================================="
Write-Host "   Video-Compress MPV Plugin Auto-Installer      "
Write-Host "================================================="

$installedCount = 0

foreach ($dest in $destinations) {
    if (Test-Path (Split-Path $dest -Parent)) {
        $scriptsDir = Join-Path $dest "scripts"
        $shadersDir = Join-Path $dest "shaders"

        New-Item -ItemType Directory -Force -Path $scriptsDir | Out-Null
        New-Item -ItemType Directory -Force -Path $shadersDir | Out-Null

        Copy-Item (Join-Path $scriptDir "video_compress.lua") $scriptsDir -Force
        Copy-Item (Join-Path $scriptDir "video_compress_reconstruct.hook") $shadersDir -Force
        # Also copy shader directly alongside script for portable resolution
        Copy-Item (Join-Path $scriptDir "video_compress_reconstruct.hook") $scriptsDir -Force

        Write-Host "[SUCCESS] Installed plugin into: $dest"
        $installedCount++
    }
}

if ($installedCount -gt 0) {
    Write-Host "`nPlugin installation complete ($installedCount location(s) configured)!"
    Write-Host "Hotkeys inside MPV:"
    Write-Host "  [Ctrl + V] : Toggle Real-Time GPU Reconstruction Filter"
} else {
    Write-Host "[WARN] No standard MPV directory found. Please ensure MPV is installed."
}
