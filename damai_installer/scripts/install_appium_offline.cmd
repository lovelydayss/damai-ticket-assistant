@echo off
REM Appium 离线安装脚本
echo 正在执行Appium离线安装...

REM 优先使用在线安装，失败时使用兼容版本的离线包
echo 检查是否存在离线包 appium-2.5.0.tgz...
if exist "appium-2.5.0.tgz" (
    echo 发现 Appium 2.5.0 离线包，优先使用在线安装...
) else (
    echo 未找到 Appium 2.5.0 离线包...
)

echo 开始安装 Appium 2.5.0...
npm install -g appium@2.5.0
if %ERRORLEVEL% NEQ 0 (
    echo Appium 2.5.0 在线安装失败！
    if exist "appium-2.5.0.tgz" (
        echo 尝试使用 Appium 2.5.0 离线包...
        npm install -g appium-2.5.0.tgz
        if %ERRORLEVEL% NEQ 0 (
            echo Appium 2.5.0 离线包安装也失败！
            exit /b 1
        ) else (
            echo Appium 2.5.0 离线安装成功！
        )
    ) else (
        echo 未找到 Appium 2.5.0 离线包！
        exit /b 1
    )
)

echo 开始安装Appium Doctor...
npm install -g appium-doctor
if %ERRORLEVEL% NEQ 0 (
    echo Appium Doctor 安装失败！
    exit /b 1
)

echo 开始安装UiAutomator2 Driver 2.45.1...
appium driver install uiautomator2@2.45.1
if %ERRORLEVEL% NEQ 0 (
    echo UiAutomator2 Driver 2.45.1 在线安装失败！
    if exist "appium-uiautomator2-driver-2.45.1.tgz" (
        echo 尝试使用 UiAutomator2 Driver 2.45.1 离线包...
        npm install -g appium-uiautomator2-driver-2.45.1.tgz
        if %ERRORLEVEL% NEQ 0 (
            echo UiAutomator2 Driver 2.45.1 离线包安装失败！
            exit /b 1
        ) else (
            echo UiAutomator2 Driver 2.45.1 离线安装成功！
        )
    ) else (
        echo 未找到 UiAutomator2 Driver 2.45.1 离线包！
        exit /b 1
    )
)

echo 验证安装结果...
echo 检查Appium版本:
appium --version

echo 检查已安装的驱动:
appium driver list --installed

echo Appium 2.5.0, Appium Doctor 和 UiAutomator2 Driver 2.45.1 安装成功！
echo 已完成所有组件的安装和验证。
exit /b 0