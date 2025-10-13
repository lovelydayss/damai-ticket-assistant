#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证修复后的安装器功能
"""

import os
import sys

def check_wheels_completeness():
    """检查wheels目录的完整性"""
    print("🔍 检查 wheels 目录完整性...")
    
    wheels_dir = "installer_files/wheels"
    if not os.path.exists(wheels_dir):
        print("❌ wheels 目录不存在")
        return False
    
    # 检查核心依赖的wheel文件
    core_packages = {
        "selenium": "selenium-4.36.0-py3-none-any.whl",
        "pydantic": "pydantic-2.6.0-py3-none-any.whl", 
        "pydantic-core": "pydantic_core-2.16.1-cp311-none-win_amd64.whl",
        "annotated-types": "annotated_types-0.7.0-py3-none-any.whl",
        "appium-python-client": "appium_python_client-5.2.4-py3-none-any.whl",
        "requests": "requests-2.32.5-py3-none-any.whl"
    }
    
    print("\n📦 检查核心依赖包:")
    all_present = True
    
    for package, wheel_file in core_packages.items():
        wheel_path = os.path.join(wheels_dir, wheel_file)
        exists = os.path.exists(wheel_path)
        size = os.path.getsize(wheel_path) if exists else 0
        print(f"  {'✅' if exists else '❌'} {package}: {wheel_file} ({size} 字节)")
        if not exists:
            all_present = False
    
    return all_present

def check_requirements_compatibility():
    """检查requirements.txt与wheels的兼容性"""
    print("\n📋 检查 requirements.txt 兼容性...")
    
    req_path = "resources/requirements.txt"
    if not os.path.exists(req_path):
        print("❌ requirements.txt 不存在")
        return False
    
    with open(req_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键依赖是否使用固定版本
    checks = [
        ("selenium==4.36.0", "Selenium版本固定"),
        ("pydantic==2.6.0", "Pydantic版本固定"),
        ("Appium-Python-Client==5.2.4", "Appium Python客户端版本固定")
    ]
    
    all_good = True
    for check, desc in checks:
        if check in content:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ 缺少: {desc}")
            all_good = False
    
    return all_good

def check_offline_packages():
    """检查离线npm包"""
    print("\n📦 检查 npm 离线包:")
    
    npm_dir = "installer_files/npm_packages"
    expected_files = [
        "appium-2.5.0.tgz",
        "appium-uiautomator2-driver-2.45.1.tgz",
        "package.json"
    ]
    
    all_present = True
    for file in expected_files:
        file_path = os.path.join(npm_dir, file)
        exists = os.path.exists(file_path)
        size = os.path.getsize(file_path) if exists else 0
        print(f"  {'✅' if exists else '❌'} {file} ({size} 字节)")
        if not exists:
            all_present = False
    
    return all_present

def check_installer_fixes():
    """检查安装器源代码修复"""
    print("\n🔧 检查安装器修复:")
    
    installer_path = "src/installer.py"
    if not os.path.exists(installer_path):
        print("❌ installer.py 不存在")
        return False
    
    with open(installer_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ("appium-2.5.0.tgz", "使用正确的Appium离线包文件名"),
        ("npm 命令可用，版本:", "添加了npm命令检测"),
        ("刷新环境变量以确保npm命令可用", "添加了环境变量刷新"),
        ("Driver 2.45.1", "使用正确的UiAutomator2驱动版本")
    ]
    
    all_good = True
    for check, desc in checks:
        if check in content:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ 缺少: {desc}")
            all_good = False
    
    return all_good

def main():
    """主函数"""
    print("🚀 大麦抢票助手安装器修复验证")
    print("=" * 50)
    
    # 切换到正确的目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 执行检查
    checks = [
        ("Python依赖包完整性", check_wheels_completeness),
        ("Requirements配置", check_requirements_compatibility), 
        ("npm离线包", check_offline_packages),
        ("安装器源代码修复", check_installer_fixes)
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        result = check_func()
        results.append((name, result))
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 修复验证总结:")
    
    all_passed = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} {name}")
        if not result:
            all_passed = False
    
    print("\n🎯 总体结果:")
    if all_passed:
        print("🎉 所有修复验证通过!")
        print("✅ 安装器已修复以下问题:")
        print("   - Python依赖包缺失 (pydantic)")
        print("   - npm命令不可用")
        print("   - 离线包检测错误")
        print("   - 版本信息不匹配")
        print("\n💡 建议:")
        print("   新安装器现在应该能够成功安装所有依赖!")
        return 0
    else:
        print("❌ 部分修复验证失败!")
        print("   请检查失败项目并重新编译")
        return 1

if __name__ == "__main__":
    sys.exit(main())