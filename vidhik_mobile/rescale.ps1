$s = [System.Drawing.Image]::FromFile((Resolve-Path 'C:\Users\aditi\Desktop\Capstone\Vidhik\vidhik_mobile\release3_now.png').Path)
$w = 900
$h = [int]($s.height * 900.0 / $s.width)
$t = New-Object System.Drawing.Bitmap($w, $h)
$g = [System.Drawing.Graphics]::FromImage($t)
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
$g.DrawImage($s, 0, 0, $w, $h)
$s.Dispose()
$t.Save('C:\Users\aditi\AppData\Local\Temp\preview3.png', 'PNG')
$t.Dispose()
Write-Output ("resized " + $w + "x" + $h)
