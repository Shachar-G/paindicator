@echo off
REM ============================================================
REM  Reset the Windows icon cache.
REM  Fixes stale / old icons shown in Explorer and on the Desktop.
REM  Just double-tap this file to run it.
REM ============================================================
echo Closing Explorer...
taskkill /f /im explorer.exe >nul 2>&1

echo Deleting icon cache files...
del /a /q  "%localappdata%\IconCache.db" >nul 2>&1
del /a /f /q "%localappdata%\Microsoft\Windows\Explorer\iconcache*" >nul 2>&1

echo Restarting Explorer...
start explorer.exe

echo.
echo Done. The icons should now show the new logo.
echo (If a Desktop shortcut still looks wrong, delete it and make a new one.)
echo.
pause
