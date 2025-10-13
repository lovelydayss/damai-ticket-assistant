@echo off
REM 设置Android环境变量脚本
echo 正在设置Android环境变量...

REM 设置ANDROID_SDK_ROOT环境变量（系统级）
echo 设置ANDROID_SDK_ROOT=C:\Android（系统变量）
setx ANDROID_SDK_ROOT "C:\Android" /M
if %ERRORLEVEL% NEQ 0 (
    echo 设置ANDROID_SDK_ROOT失败！可能需要管理员权限
    REM 尝试用户级别设置作为备用
    setx ANDROID_SDK_ROOT "C:\Android"
)

REM 设置ANDROID_HOME环境变量（系统级）
echo 设置ANDROID_HOME=C:\Android（系统变量）
setx ANDROID_HOME "C:\Android" /M
if %ERRORLEVEL% NEQ 0 (
    echo 设置ANDROID_HOME失败！可能需要管理员权限
    REM 尝试用户级别设置作为备用
    setx ANDROID_HOME "C:\Android"
)

REM 获取当前系统PATH并添加platform-tools
echo 添加C:\Android\platform-tools到系统PATH...
for /f "tokens=2*" %%i in ('reg query "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYSTEM_PATH=%%j"
if defined SYSTEM_PATH (
    echo 当前系统PATH已获取
    echo %SYSTEM_PATH% | findstr /i "C:\Android\platform-tools" >nul
    if %ERRORLEVEL% NEQ 0 (
        setx PATH "%SYSTEM_PATH%;C:\Android\platform-tools" /M
        if %ERRORLEVEL% NEQ 0 (
            echo 设置系统PATH失败！尝试用户PATH...
            setx PATH "%PATH%;C:\Android\platform-tools"
        )
    ) else (
        echo platform-tools已存在于系统PATH中
    )
) else (
    echo 无法获取系统PATH，使用用户PATH
    setx PATH "%PATH%;C:\Android\platform-tools"
)

echo Android环境变量设置完成！
echo 请重启终端或重新登录以使环境变量生效。
exit /b 0