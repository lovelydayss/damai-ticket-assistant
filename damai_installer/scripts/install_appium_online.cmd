@echo off
REM Appium 在线安装脚本
echo 正在执行Appium在线安装...

REM 执行在线安装
echo 开始从npm仓库下载并安装Appium 2.5.0...
npm install -g appium@2.5.0
if %ERRORLEVEL% NEQ 0 (
    echo Appium 2.5.0 安装失败！
    exit /b 1
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
    echo UiAutomator2 Driver 2.45.1 安装失败！
    exit /b 1
)

echo 验证安装结果...
echo 检查Appium版本:
appium --version

echo 检查已安装的驱动:
appium driver list --installed

echo Appium 2.5.0, Appium Doctor 和 UiAutomator2 Driver 2.45.1 在线安装成功！
exit /b 0