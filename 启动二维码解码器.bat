@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
REM 启动器不含任何本机专属路径，便于随仓库分发。
REM 解释器查找顺序：QR_GUI_PYTHON 环境变量 -> PATH 里的 pythonw -> py -3

set "PYW=%QR_GUI_PYTHON%"
set "PYW_ARG="

if not defined PYW (
    for /f "delims=" %%i in ('where pythonw 2^>nul') do (
        if not defined PYW set "PYW=%%i"
    )
)

if not defined PYW (
    for /f "delims=" %%i in ('where py 2^>nul') do (
        if not defined PYW set "PYW=%%i"
    )
    if defined PYW set "PYW_ARG=-3"
)

if not defined PYW (
    echo [!] 未找到 Python 解释器。
    echo     请安装 Python（需带 tkinter），或设置环境变量 QR_GUI_PYTHON：
    echo     setx QR_GUI_PYTHON "C:\Path\To\pythonw.exe"
    echo.
    pause
    exit /b 1
)

if defined PYW_ARG (
    start "" "%PYW%" %PYW_ARG% "%~dp0qr_gui.pyw" %*
) else (
    start "" "%PYW%" "%~dp0qr_gui.pyw" %*
)
endlocal
