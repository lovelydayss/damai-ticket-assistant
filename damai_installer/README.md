# 大麦抢票助手安装器

本目录提供“安装器”与相关离线资源，用于在 Windows 环境下一键安装并配置运行大麦抢票助手所需的全部组件（Python、Node、Appium、Android 平台工具及项目依赖），支持离线/在线双模式安装。

## 项目定位与作用

- 目标：降低环境搭建成本，统一关键依赖版本，在管理员权限下自动完成安装与 PATH 设置。
- 形态：独立的图形化安装程序（可打包为 exe），并附带脚本化的离线安装资源。
- 集成：安装完成后可直接启动主 GUI 程序，或返回项目根目录运行 [`start_gui.pyw`](../start_gui.pyw)。

关键入口方法：
- 全量安装按钮：[DamaiInstaller.install_all()](damai_installer/src/installer.py:492)
- PATH 检查按钮：[DamaiInstaller.check_environment()](damai_installer/src/installer.py:239)
- 启动主助手按钮：[DamaiInstaller.start_gui()](damai_installer/src/installer.py:385)
- Appium 安装核心逻辑（离线/在线回退）：[DamaiInstaller._install_appium_with_fallback()](damai_installer/src/installer.py:923)

## 支持的组件版本

- Python：3.11.6
- Node.js：18.18.2 LTS
- Appium Server：2.5.0
- UiAutomator2 Driver：2.45.1
- Android Platform Tools：latest（zip 包形式）
- Python 项目依赖：通过 wheels 离线包与 `resources/requirements.txt`

## 目录结构与资源说明

```
damai_installer/
├─ src/                         # 安装器源码
│  ├─ installer.py              # Tkinter GUI 安装器主程序
│  └─ pyarmor_method.py         # 如需 PyArmor 处理（可选）
├─ resources/                   # 安装配置与运行时资源
│  ├─ components.json           # 组件列表与安装检查配置
│  ├─ requirements.txt          # Python 依赖清单
│  └─ pyarmor_runtime/          # PyArmor 运行时（可选）
├─ scripts/                     # 安装与环境脚本
│  ├─ install_appium_offline.cmd
│  ├─ install_appium_online.cmd
│  └─ setup_android_env.cmd
├─ installer_files/             # 离线安装资源
│  ├─ wheels/                   # Python 依赖离线 wheels
│  └─ npm_packages/             # NPM 离线包（appium、uiautomator2 等）
├─ build_installer.bat          # 一键打包为安装器 exe 的脚本
├─ installer.spec               # PyInstaller 打包配置
└─ README.md                    # 本说明文件
```

相关文件（可点击查看）：
- 安装器主程序：[damai_installer/src/installer.py](damai_installer/src/installer.py)
- 组件配置：[damai_installer/resources/components.json](damai_installer/resources/components.json)
- Python 依赖清单：[damai_installer/resources/requirements.txt](damai_installer/resources/requirements.txt)
- 安装脚本（离线）：[install_appium_offline.cmd](damai_installer/scripts/install_appium_offline.cmd:1)
- 安装脚本（在线）：[install_appium_online.cmd](damai_installer/scripts/install_appium_online.cmd:1)
- Android 环境设置脚本：[damai_installer/scripts/setup_android_env.cmd](damai_installer/scripts/setup_android_env.cmd)
- 打包配置：[damai_installer/installer.spec](damai_installer/installer.spec)
- 打包脚本：[damai_installer/build_installer.bat](damai_installer/build_installer.bat)

## 快速开始

1) 以管理员身份运行安装器
- 从项目根目录直接运行：`大麦抢票助手安装器.exe`（已移动到根目录）
- 或从源码启动安装器 GUI：
  ```bash
  cd damai_installer
  python src/installer.py
  ```

2) 点击“检查PATH”确认环境变量与版本
- 按钮实现：[DamaiInstaller.check_environment()](damai_installer/src/installer.py:239)

3) 点击“一键安装全部”
- 安装过程按依赖顺序执行，支持离线/在线回退策略。
- 按钮实现：[DamaiInstaller.install_all()](damai_installer/src/installer.py:492)

4) 安装完成后，点击“启动助手”
- 自动查找并运行项目根目录的 GUI 启动脚本。
- 按钮实现：[DamaiInstaller.start_gui()](damai_installer/src/installer.py:385)

## 安装策略与脚本

- Appium 安装策略（离线优先，在线回退）
  - 核心逻辑：[DamaiInstaller._install_appium_with_fallback()](damai_installer/src/installer.py:923)
  - 离线脚本：优先尝试 `appium@2.5.0` 与 `uiautomator2@2.45.1`，若在线失败则使用离线 tgz 包。
    - [install_appium_offline.cmd](damai_installer/scripts/install_appium_offline.cmd:1)
  - 在线脚本：直接从 npm 安装固定版本。
    - [install_appium_online.cmd](damai_installer/scripts/install_appium_online.cmd:1)

- Android 环境变量设置
  - 自动设置 ANDROID_HOME、ANDROID_SDK_ROOT 并将 platform-tools 加入 PATH。
    - [damai_installer/scripts/setup_android_env.cmd](damai_installer/scripts/setup_android_env.cmd)

- PATH 刷新
  - 安装器会通过 Windows 广播刷新 PATH，使当前会话尽可能生效。
    - [DamaiInstaller.refresh_env_variables()](damai_installer/src/installer.py:1272)

## 编译与发布

- 一键打包为安装器 exe：
  - 使用批处理脚本：[damai_installer/build_installer.bat](damai_installer/build_installer.bat)
  - 或使用 PyInstaller：
    - [damai_installer/installer.spec](damai_installer/installer.spec)

- 发布建议：
  - 不将大体积离线包与构建缓存提交到 GitHub（已在根目录 [.gitignore](../.gitignore) 进行忽略）。
  - 在干净的 Windows 环境中完成一次验证（管理员权限、PATH 正常、Appium/ADB 可用）。

## 常见问题与排查

- 未以管理员权限运行
  - 现象：安装报错或 PATH 写入失败。
  - 解决：右键以管理员身份运行安装器 exe。

- PATH 未即时生效
  - 现象：`appium`、`adb`、`npm` 等命令在当前窗口不可用。
  - 解决：点击“检查PATH”，或重新打开终端/注销后再试。

- 杀毒软件误报
  - 现象：打包 exe 被拦截。
  - 建议：加入白名单或进行代码签名。

- Appium 安装失败（网络/权限）
  - 解决：离线优先策略 + 在线回退；亦可参考安装提示窗口手动执行安装命令。

## 维护与升级指引

- 更新组件/依赖版本：
  - 组件配置：编辑 [damai_installer/resources/components.json](damai_installer/resources/components.json)
  - Python 依赖：更新 [damai_installer/resources/requirements.txt](damai_installer/resources/requirements.txt) 与 `installer_files/wheels/`
  - NPM 离线包：更新 `installer_files/npm_packages/` 中的 tgz（如 `appium-2.5.0.tgz`、`appium-uiautomator2-driver-2.45.1.tgz`）

- 打包流程：
  - 优先使用 [damai_installer/build_installer.bat](damai_installer/build_installer.bat)，或阅读 `COMPILE.md` 深入配置。

## 许可证

本安装器遵循项目主仓库的 LICENSE。如需分发/再发布，请遵守各第三方资源（Python wheels、NPM 包）的许可证要求。
