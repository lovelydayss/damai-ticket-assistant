# 编译指南

## 🔧 环境要求

### 必需软件
- **Python 3.11.6**: 与目标用户环境保持一致
- **PyInstaller 6.16.0**: 用于打包可执行文件
- **Git**: 用于版本控制（可选）

### 可选组件
- **PyArmor 9.1.9**: 代码保护（可选安装）

## 📋 编译步骤

### 1. 环境准备
```bash
# 安装 PyInstaller
pip install pyinstaller==6.16.0

# 安装其他依赖
pip install -r resources/requirements.txt

# 可选：安装 PyArmor
pip install pyarmor==9.1.9
```

### 2. 一键编译
```bash
# 进入项目目录
cd damai_installer

# 运行编译脚本
build_installer.bat
```

### 3. 手动编译
```bash
# 使用 PyInstaller 配置文件
pyinstaller installer.spec

# 或使用命令行参数
pyinstaller --onefile --windowed --icon=installer_files/favicon.ico --add-data "resources;resources" --add-data "scripts;scripts" --add-data "installer_files;installer_files" src/installer.py
```

## 📂 输出文件

编译成功后，会在以下位置生成文件：
- `dist/installer.exe` - 可执行文件
- `build/` - 临时构建文件（可删除）

## 🐛 常见问题

### 1. PyArmor 导入错误
**问题**: `AttributeError: module 'pyarmor' has no attribute 'xxx'`

**解决方案**:
```bash
# 重新安装 PyArmor
pip uninstall pyarmor
pip install pyarmor==9.1.9
```

### 2. 路径分隔符问题
**问题**: Windows/Linux 路径分隔符不一致

**解决方案**: 代码中已使用 `os.path.join()` 和 `pathlib.Path` 处理跨平台兼容性

### 3. 资源文件缺失
**问题**: 运行时找不到资源文件

**解决方案**: 检查 `installer.spec` 中的 `datas` 配置，确保所有资源文件都被包含

### 4. 杀毒软件误报
**问题**: 编译后的 exe 被杀毒软件拦截

**解决方案**:
1. 添加到杀毒软件白名单
2. 使用数字签名（推荐）
3. 联系杀毒软件厂商提交样本

## ⚙️ 编译选项说明

### installer.spec 配置文件
```python
# 主要配置项
a = Analysis(
    ['src\\installer.py'],           # 入口脚本
    pathex=[],                       # 搜索路径
    binaries=[],                     # 二进制文件
    datas=[                          # 数据文件
        ('resources', 'resources'),
        ('scripts', 'scripts'),
        ('installer_files', 'installer_files'),
    ],
    hiddenimports=[                  # 隐式导入
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'subprocess',
        'threading',
        'json',
        'os',
        'sys',
        'pathlib',
        'shutil',
        'platform',
        're',
        'webbrowser'
    ],
    hookspath=[],                    # 钩子路径
    hooksconfig={},                  # 钩子配置
    runtime_hooks=[],                # 运行时钩子
    excludes=[],                     # 排除模块
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,                     # 加密
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='installer',                # 输出文件名
    debug=False,                     # 调试模式
    bootloader_ignore_signals=False,
    strip=False,                     # 去除调试符号
    upx=True,                        # UPX压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                   # 隐藏控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='installer_files\\favicon.ico'  # 图标文件
)
```

## 🔍 测试验证

### 编译后测试
```bash
# 1. 检查文件大小（应该在 50-100MB 范围内）
dir dist\installer.exe

# 2. 运行快速测试
dist\installer.exe

# 3. 测试各个功能模块
# - 环境检测
# - 组件安装
# - 错误处理
```

### 分发前检查
- [ ] 在干净的Windows环境中测试
- [ ] 验证所有依赖是否正确打包
- [ ] 检查管理员权限提示
- [ ] 测试离线安装功能
- [ ] 验证Appium安装和配置

## 📦 打包发布

### 创建发布包
```bash
# 1. 复制编译输出
copy dist\installer.exe ..\大麦抢票助手安装器.exe

# 2. 创建发布文档
# 包含 README.md、CHANGELOG.md 等

# 3. 压缩打包
# 可以使用 7-Zip 或 WinRAR
```

### 版本管理
- 更新版本号: 修改 `installer.py` 中的 `VERSION` 常量
- 更新变更日志: 编辑 `CHANGELOG.md`
- 创建 Git 标签: `git tag v2.0.0`

## 🛡️ 安全考虑

### 代码保护
```bash
# 使用 PyArmor 加密（可选）
pyarmor gen --output obfuscated src/installer.py
pyinstaller --add-data "obfuscated;." installer.spec
```

### 数字签名
```bash
# 使用 signtool（需要代码签名证书）
signtool sign /f certificate.p12 /p password /t http://timestamp.digicert.com dist\installer.exe
```

## 📊 性能优化

### 减小文件大小
1. **排除无用模块**: 在 `excludes` 中添加不需要的模块
2. **启用UPX压缩**: `upx=True`（已启用）
3. **移除调试信息**: `debug=False`, `strip=True`

### 启动速度优化
1. **延迟导入**: 在需要时才导入大型模块
2. **缓存机制**: 缓存重复的检测结果
3. **异步操作**: 使用线程处理耗时操作

---

**提示**: 建议在不同的Windows版本（Win10, Win11）和环境（有/无管理员权限）中测试编译后的安装器，确保兼容性。