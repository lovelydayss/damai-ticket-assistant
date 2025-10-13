@echo off
REM 大麦抢票助手安装器构建脚本
echo 正在构建大麦抢票助手安装器...

REM 检查 PyInstaller 是否安装
python -c "import PyInstaller" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 正在安装 PyInstaller...
    pip install pyinstaller
    if %ERRORLEVEL% NEQ 0 (
        echo PyInstaller 安装失败！
        pause
        exit /b 1
    )
)

REM 清理之前的构建结果
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

REM 使用 spec 文件构建
echo 开始构建...
pyinstaller installer.spec

if %ERRORLEVEL% EQU 0 (
    echo 构建成功！
    echo 安装器位置: dist\大麦抢票助手安装器.exe
    
    REM 复制到项目根目录
    if exist "dist\大麦抢票助手安装器.exe" (
        copy "dist\大麦抢票助手安装器.exe" "..\大麦抢票助手安装器.exe"
        echo 已复制到项目根目录: ..\大麦抢票助手安装器.exe
    )
) else (
    echo 构建失败！请检查错误信息。
)

pause