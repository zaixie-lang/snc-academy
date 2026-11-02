Add-Type -AssemblyName System.Drawing

$srcPath = Join-Path $PSScriptRoot "..\images\snc-logo.png"
if (-not (Test-Path $srcPath)) {
    Write-Error "Source image not found at $srcPath"
    exit 1
}

$img = [System.Drawing.Image]::FromFile($srcPath)

function Resize-And-Save($targetWidth, $targetHeight, $outPath) {
    $bmp = New-Object System.Drawing.Bitmap $targetWidth, $targetHeight
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $g.DrawImage($img, 0, 0, $targetWidth, $targetHeight)
    $bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose()
    $bmp.Dispose()
    Write-Output "Generated: $outPath"
}

# 1. Root favicon.png and images/favicon-32x32.png
Resize-And-Save 32 32 (Join-Path $PSScriptRoot "..\favicon.png")
Resize-And-Save 32 32 (Join-Path $PSScriptRoot "..\images\favicon-32x32.png")
Resize-And-Save 16 16 (Join-Path $PSScriptRoot "..\images\favicon-16x16.png")
Resize-And-Save 180 180 (Join-Path $PSScriptRoot "..\images\apple-touch-icon.png")
Resize-And-Save 192 192 (Join-Path $PSScriptRoot "..\images\android-chrome-192x192.png")
Resize-And-Save 512 512 (Join-Path $PSScriptRoot "..\images\android-chrome-512x512.png")

# Also create a valid .ico file (standard 32x32 and 16x16 icon container or single icon)
$icoBmp = New-Object System.Drawing.Bitmap $img, 32, 32
$hIcon = $icoBmp.GetHicon()
$icon = [System.Drawing.Icon]::FromHandle($hIcon)
$icoStream = [System.IO.File]::OpenWrite((Join-Path $PSScriptRoot "..\favicon.ico"))
$icon.Save($icoStream)
$icoStream.Close()
$icoBmp.Dispose()

$img.Dispose()
Write-Output "All icons successfully created!"
