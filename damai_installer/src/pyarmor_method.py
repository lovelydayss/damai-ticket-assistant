    def install_pyarmor_runtime(self):
        """安装PyArmor运行时库"""
        try:
            # 获取项目根目录
            project_dir = self.get_install_dir() or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(sys.executable)), ".."))
            
            self.log("\n===== 开始安装 PyArmor 运行时库 =====")
            self.log(f"项目目录: {project_dir}")
            
            # 创建 PyArmor 运行时目录结构
            runtime_dir = os.path.join(project_dir, "damai", "pyarmor_runtime_000000")
            if not os.path.exists(runtime_dir):
                os.makedirs(runtime_dir, exist_ok=True)
                self.log(f"创建目录: {runtime_dir}")
            
            # 查找安装器资源中的 PyArmor 运行时文件
            installer_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
            
            # 可能的运行时文件位置列表
            runtime_paths = [
                os.path.join(installer_dir, "resources", "pyarmor_runtime"),
                resource_path("resources/pyarmor_runtime"),
                os.path.join(installer_dir, "..", "resources", "pyarmor_runtime"),
                os.path.join(installer_dir, "..", "_internal", "resources", "pyarmor_runtime"),
            ]
            
            runtime_src = None
            for path in runtime_paths:
                if os.path.exists(path) and os.path.isdir(path):
                    runtime_src = path
                    self.log(f"找到 PyArmor 运行时资源: {path}")
                    break
            
            if runtime_src:
                # 复制预打包的运行时文件
                self.log("正在复制预打包的 PyArmor 运行时文件...")
                
                # 复制 __init__.py
                init_src = os.path.join(runtime_src, "__init__.py")
                init_dst = os.path.join(runtime_dir, "__init__.py")
                if os.path.exists(init_src):
                    shutil.copy2(init_src, init_dst)
                    self.log(f"已复制: {init_dst}")
                else:
                    # 创建默认的 __init__.py
                    with open(init_dst, "w", encoding="utf-8") as f:
                        f.write('# Pyarmor 9.1.9 (trial), 000000, 2025-10-12\nfrom .pyarmor_runtime import __pyarmor__\n')
                    self.log(f"已创建: {init_dst}")
                
                # 复制 pyarmor_runtime.pyd
                pyd_src = os.path.join(runtime_src, "pyarmor_runtime.pyd")
                pyd_dst = os.path.join(runtime_dir, "pyarmor_runtime.pyd")
                if os.path.exists(pyd_src):
                    shutil.copy2(pyd_src, pyd_dst)
                    self.log(f"已复制: {pyd_dst}")
                else:
                    self.log(f"警告: 未找到 pyarmor_runtime.pyd 文件")
                    
                self.log("PyArmor 运行时库安装完成!")
            else:
                # 如果没有预打包的运行时文件，尝试使用pip安装
                self.log("未找到预打包的运行时文件，正在尝试通过 pip 安装...")
                
                try:
                    # 先安装 PyArmor
                    self.log("正在安装 PyArmor...")
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "pyarmor==9.1.9"],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    
                    # 创建临时脚本生成运行时文件
                    temp_script = os.path.join(os.environ.get('TEMP', os.environ.get('TMP', '.')), 'generate_pyarmor_runtime.py')
                    with open(temp_script, 'w', encoding='utf-8') as f:
                        f.write("""
import os
import sys
import shutil
from pyarmor.cli.__init__ import main as pyarmor_main

# 生成运行时
output_dir = sys.argv[1]
os.makedirs(output_dir, exist_ok=True)

# 调用 PyArmor 命令行生成运行时
sys.argv = ['pyarmor', 'runtime', '-O', output_dir, '--index', '0']
pyarmor_main()

print(f"Runtime files generated in {output_dir}")
                        """)
                    
                    # 执行脚本生成运行时
                    self.log("正在生成 PyArmor 运行时...")
                    result = subprocess.run(
                        [sys.executable, temp_script, runtime_dir],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    self.log(result.stdout)
                    
                    # 确保 __init__.py 存在且内容正确
                    init_dst = os.path.join(runtime_dir, "__init__.py")
                    with open(init_dst, "w", encoding="utf-8") as f:
                        f.write('# Pyarmor 9.1.9 (trial), 000000, 2025-10-12\nfrom .pyarmor_runtime import __pyarmor__\n')
                    self.log(f"已创建/更新: {init_dst}")
                    
                    self.log("PyArmor 运行时库安装完成!")
                    
                except Exception as e:
                    self.log(f"⚠️ PyArmor 安装失败: {str(e)}")
                    self.log("警告: 程序可能无法正常运行，请手动安装 PyArmor 或复制运行时文件")
            
            # 创建安装确认文件
            confirmation_file = os.path.join(runtime_dir, ".installed")
            with open(confirmation_file, 'w') as f:
                f.write(f"Installed: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            return True
            
        except Exception as e:
            self.log(f"⚠️ 安装 PyArmor 运行时库失败: {str(e)}")
            self.log("详细错误信息:")
            self.log(traceback.format_exc())
            return False