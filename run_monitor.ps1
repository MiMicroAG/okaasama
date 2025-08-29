# OneDriveフォルダ監視スクリプト実行PowerShellスクリプト
# Windowsタスクスケジューラーで定期実行するために使用

param(
    [switch]$Once
)

Write-Host "OneDriveフォルダ監視を開始します..."
Write-Host "$(Get-Date)"

# Pythonスクリプトのパス
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScript = Join-Path $ScriptDir "onedrive_monitor.py"

# Python実行
try {
    $process = Start-Process -FilePath "python" -ArgumentList "`"$PythonScript`" --once" -NoNewWindow -Wait -PassThru

    if ($process.ExitCode -eq 0) {
        Write-Host "監視スクリプトが正常に完了しました"
    } else {
        Write-Host "監視スクリプトでエラーが発生しました"
        Write-Host "エラーコード: $($process.ExitCode)"
    }
} catch {
    Write-Host "エラー: $($_.Exception.Message)"
}

Write-Host "$(Get-Date)"
Write-Host "完了"

# PowerShellスクリプトは自動的に終了する
