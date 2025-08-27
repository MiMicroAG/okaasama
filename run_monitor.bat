@echo off
REM OneDriveフォルダ監視スクリプト実行バッチファイル
REM Windowsタスクスケジューラーで定期実行するために使用

REM UTF-8エンコーディングを設定
chcp 65001 >nul

echo OneDriveフォルダ監視を開始します...
echo %DATE% %TIME%

REM Pythonスクリプトのパス（必要に応じて変更）
set SCRIPT_DIR=%~dp0
set PYTHON_SCRIPT=%SCRIPT_DIR%onedrive_monitor.py

REM Python実行（仮想環境を使用する場合などは適宜変更）
python "%PYTHON_SCRIPT%" --once

if %ERRORLEVEL% EQU 0 (
    echo 監視スクリプトが正常に完了しました
) else (
    echo 監視スクリプトでエラーが発生しました
    exit /b %ERRORLEVEL%
)

echo %DATE% %TIME%
echo 完了
