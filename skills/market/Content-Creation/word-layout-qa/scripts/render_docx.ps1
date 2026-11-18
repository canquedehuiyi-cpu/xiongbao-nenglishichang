param(
    [Parameter(Mandatory=$true)][string]$Docx,
    [Parameter(Mandatory=$true)][string]$Pdf,
    [Parameter(Mandatory=$true)][string]$Prefix,
    [switch]$AlignTable1
)
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
Add-Type -AssemblyName System.Drawing
try {
    $doc = $word.Documents.Open($Docx)
    if ($AlignTable1 -and $doc.Tables.Count -ge 1) {
        $t = $doc.Tables.Item(1)
        for ($r = 1; $r -le $t.Rows.Count; $r++) {
            for ($c = 1; $c -le $t.Columns.Count; $c++) {
                $cell = $t.Cell($r, $c)
                if ($r -eq 1) { $cell.Range.ParagraphFormat.Alignment = 1 } else { $cell.Range.ParagraphFormat.Alignment = 0 }
            }
        }
        Write-Output 'ALIGN_OK'
    }
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Fields.Update() | Out-Null
    foreach ($toc in $doc.TablesOfContents) { $toc.UpdatePageNumbers() }
    $doc.Save()
    Write-Output 'SAVED'
    $doc.ExportAsFixedFormat($Pdf, 17)
    Write-Output 'PDF_OK'
    $np = $doc.ComputeStatistics(2)
    Write-Output ("PAGES " + $np)
    $pane = $doc.ActiveWindow.Panes.Item(1)
    for ($i = 1; $i -le $np; $i++) {
        try {
            $bits = $pane.Pages.Item($i).EnhMetaFileBits
            $emf = "$Prefix$i.emf"
            [System.IO.File]::WriteAllBytes($emf, $bits)
            $mf = New-Object System.Drawing.Imaging.Metafile($emf)
            $w = [int]($mf.Width * 2); $h = [int]($mf.Height * 2)
            if ($w -lt 10 -or $h -lt 10) { $w = 1240; $h = 1754 }
            $bmp = New-Object System.Drawing.Bitmap($w, $h)
            $g = [System.Drawing.Graphics]::FromImage($bmp)
            $g.Clear([System.Drawing.Color]::White)
            $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $g.DrawImage($mf, 0, 0, $w, $h)
            $bmp.Save("$Prefix$i.png", [System.Drawing.Imaging.ImageFormat]::Png)
            $g.Dispose(); $bmp.Dispose(); $mf.Dispose()
            Write-Output ("PNG_OK $i")
        } catch {
            Write-Output ("PNG_FAIL $i " + $_.Exception.Message)
        }
    }
    $doc.Close($false)
} finally {
    $word.Quit()
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}