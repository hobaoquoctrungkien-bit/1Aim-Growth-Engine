$soundPath = "C:\Windows\Media\notify.wav"

try {
    if (Test-Path $soundPath) {
        (New-Object Media.SoundPlayer $soundPath).PlaySync()
    } else {
        [console]::beep(1000, 300)
    }
} catch {
    try {
        [console]::beep(1000, 300)
    } catch {
        Write-Host "Notification sound failed: $($_.Exception.Message)"
    }
}
