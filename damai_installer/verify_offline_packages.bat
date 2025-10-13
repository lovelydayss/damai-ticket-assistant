@echo off
REM 大麦抢票助手离线包验证脚本
echo 正在验证离线安装包配置...
echo.

set "npm_packages_dir=installer_files\npm_packages"

REM 检查离线包文件是否存在
echo 🔍 检查离线包文件:

if exist "%npm_packages_dir%\appium-2.5.0.tgz" (
    echo   ✅ appium-2.5.0.tgz 存在
    for %%F in ("%npm_packages_dir%\appium-2.5.0.tgz") do echo     大小: %%~zF 字节
) else (
    echo   ❌ appium-2.5.0.tgz 缺失
    set "has_error=1"
)

if exist "%npm_packages_dir%\appium-uiautomator2-driver-2.45.1.tgz" (
    echo   ✅ appium-uiautomator2-driver-2.45.1.tgz 存在  
    for %%F in ("%npm_packages_dir%\appium-uiautomator2-driver-2.45.1.tgz") do echo     大小: %%~zF 字节
) else (
    echo   ❌ appium-uiautomator2-driver-2.45.1.tgz 缺失
    set "has_error=1"
)

REM 检查是否还有旧版本文件
if exist "%npm_packages_dir%\appium-3.1.0.tgz" (
    echo   ⚠️  发现旧版本: appium-3.1.0.tgz (应该删除)
    set "has_warning=1"
)

echo.
echo 📋 检查 package.json 配置:
if exist "%npm_packages_dir%\package.json" (
    echo   ✅ package.json 存在
    findstr /C:"\"appium\": \"2.5.0\"" "%npm_packages_dir%\package.json" >nul
    if !ERRORLEVEL! EQU 0 (
        echo   ✅ Appium 版本配置正确 (2.5.0)
    ) else (
        echo   ❌ Appium 版本配置错误
        set "has_error=1"
    )
    
    findstr /C:"\"appium-uiautomator2-driver\": \"2.45.1\"" "%npm_packages_dir%\package.json" >nul
    if !ERRORLEVEL! EQU 0 (
        echo   ✅ UiAutomator2 Driver 版本配置正确 (2.45.1)
    ) else (
        echo   ❌ UiAutomator2 Driver 版本配置错误
        set "has_error=1"
    )
) else (
    echo   ❌ package.json 缺失
    set "has_error=1"
)

echo.
echo 🚀 检查安装脚本配置:
if exist "scripts\install_appium_offline.cmd" (
    echo   ✅ install_appium_offline.cmd 存在
    
    findstr /C:"appium-2.5.0.tgz" "scripts\install_appium_offline.cmd" >nul
    if !ERRORLEVEL! EQU 0 (
        echo   ✅ 脚本引用正确的 Appium 2.5.0 离线包
    ) else (
        echo   ❌ 脚本未正确引用 Appium 2.5.0 离线包  
        set "has_error=1"
    )
    
    findstr /C:"appium-uiautomator2-driver-2.45.1.tgz" "scripts\install_appium_offline.cmd" >nul
    if !ERRORLEVEL! EQU 0 (
        echo   ✅ 脚本引用正确的 UiAutomator2 Driver 2.45.1 离线包
    ) else (
        echo   ❌ 脚本未正确引用 UiAutomator2 Driver 2.45.1 离线包
        set "has_error=1"
    )
    
    findstr /C:"appium-3.1.0.tgz" "scripts\install_appium_offline.cmd" >nul
    if !ERRORLEVEL! EQU 0 (
        echo   ⚠️  脚本仍引用旧版本 appium-3.1.0.tgz
        set "has_warning=1"
    ) else (
        echo   ✅ 脚本已移除旧版本引用
    )
) else (
    echo   ❌ install_appium_offline.cmd 缺失
    set "has_error=1"
)

echo.
echo ================================================
if defined has_error (
    echo ❌ 验证失败! 发现配置错误，请修复后重新编译安装器
    exit /b 1
) else if defined has_warning (
    echo ⚠️  验证通过但有警告，建议修复警告项  
    exit /b 0
) else (
    echo 🎉 所有验证通过! 离线包配置正确
    echo ✅ 新安装器将能够使用正确版本的离线包
    exit /b 0
)