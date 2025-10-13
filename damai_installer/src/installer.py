import os
import sys
import subprocess
import threading
import shutil
import zipfile
import json
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import urllib.request
import ctypes
import webbrowser
import traceback
import time
import locale
import shlex

# 确保资源路径正确
def resource_path(relative_path):
    """ 获取资源绝对路径，适用于开发环境和PyInstaller打包环境 """
    try:
        # PyInstaller创建临时文件夹_MEIxxxx，并将所需文件存储在其中
        base_path = sys._MEIPASS
    except Exception:
        # 不在打包环境中，使用当前目录
        base_path = os.path.abspath(".")
        # 检查是否在开发环境中
        if os.path.basename(base_path) != "damai_installer" and os.path.exists(os.path.join(base_path, "damai_installer")):
            base_path = os.path.join(base_path, "damai_installer")
    
    full_path = os.path.join(base_path, relative_path)
    
    # 如果路径不存在，尝试其他可能的位置
    if not os.path.exists(full_path):
        # 尝试查找同级目录
        parent_dir = os.path.dirname(base_path)
        alt_path = os.path.join(parent_dir, relative_path)
        if os.path.exists(alt_path):
            return alt_path
        
        # 尝试查找内部_internal目录
        internal_path = os.path.join(base_path, "_internal", relative_path)
        if os.path.exists(internal_path):
            return internal_path
        
        # 对于特定的文件（如wheels目录），尝试一些常见的位置
        if "wheels" in relative_path or "requirements.txt" in relative_path:
            possible_locations = [
                os.path.join(base_path, "installer_files", "wheels"),
                os.path.join(parent_dir, "installer_files", "wheels"),
                os.path.join(base_path, "_internal", "installer_files", "wheels"),
                os.path.join(base_path, "resources")
            ]
            for loc in possible_locations:
                if os.path.exists(os.path.dirname(loc)):
                    return loc
    
    return full_path

class DamaiInstaller(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("大麦票务助手一键安装器")
        self.geometry("800x600")
        self.minsize(700, 500)
        
        self.log_lock = threading.Lock()
        self.install_thread = None
        self.stop_event = threading.Event()
        
        # 加载配置
        self.components = self.load_components_config()
        self.create_ui()
        
        # 启动时简单检查组件状态
        self.after(1000, self.startup_check_components)
    
    def load_components_config(self):
        """加载组件配置"""
        # 尝试多个可能的位置
        possible_paths = [
            resource_path("resources/components.json"),
            resource_path("components.json"),
            resource_path("installer_files/components.json"),
            resource_path("_internal/resources/components.json")
        ]
        
        components = None
        config_path = None
        
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        components = json.load(f)
                    config_path = path
                    self.log(f"成功从 {path} 加载组件配置")
                    break
            except Exception as e:
                pass
        
        # 如果无法从文件加载，使用内置的默认配置
        if components is None:
            self.log("无法从文件加载组件配置，使用内置默认配置")
            # 默认组件配置
            components = [
                {
                    "name": "Python 3.11.6",
                    "type": "exe",
                    "file": "python-3.11.6-amd64.exe",
                    "install_cmd": '"{path}" /quiet PrependPath=1',
                    "check_cmd": "python --version 2>&1 | findstr \"Python 3.11\""
                },
                {
                    "name": "Node.js 18.18.2 LTS",
                    "type": "msi",
                    "file": "node-v18.18.2-x64.msi",
                    "install_cmd": "msiexec.exe /i \"{path}\" /quiet",
                    "check_cmd": "node --version 2>&1 | findstr \"v18\""
                },
                {
                    "name": "Android Platform Tools",
                    "type": "zip",
                    "file": "platform-tools-latest-windows.zip",
                    "extract_dir": "C:/Android/platform-tools",
                    "check_cmd": "adb --version 2>&1 | findstr \"Android\""
                },
                {
                    "name": "项目依赖安装",
                    "type": "pip",
                    "check_cmd": "python -c \"import appium, selenium; print('OK')\" 2>nul"
                },
                {
                    "name": "Appium Server 2.5.0 + UiAutomator2 Driver 2.45.1",
                    "type": "npm",
                    "install_cmd": "npm install -g appium@2.5.0 && npm install -g appium-doctor && appium driver install uiautomator2@2.45.1",
                    "check_cmd": "appium --version && appium-doctor --version && appium driver list --installed | findstr uiautomator2"
                }
            ]

        # 补全缺失字段，防止 UI 初始化时报 KeyError
        for comp in components:
            if 'status' not in comp or comp.get('status') is None:
                comp['status'] = '未安装'
            comp.setdefault('file', '')
            comp.setdefault('install_cmd', '')
            comp.setdefault('extract_dir', '')
        
        return components

    def create_ui(self):
        """创建UI界面"""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header_frame, text="大麦票务助手安装器", 
                 font=("Microsoft YaHei", 16, "bold")).pack()
        ttk.Label(header_frame, 
                 text="本工具将自动安装大麦票务助手所需的全部组件和依赖").pack()
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, padx=10, pady=5)
        
        component_frame = ttk.LabelFrame(main_frame, text="安装组件")
        component_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.component_listbox = ttk.Treeview(component_frame, 
                                             columns=("name", "type", "status"),
                                             show="headings",
                                             selectmode="browse")
        self.component_listbox.heading("name", text="组件名称")
        self.component_listbox.heading("type", text="类型")
        self.component_listbox.heading("status", text="状态")
        self.component_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        for i, component in enumerate(self.components):
            self.component_listbox.insert("", "end", values=(
                component["name"], component["type"], component["status"]
            ))
        
        log_frame = ttk.LabelFrame(main_frame, text="安装日志")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.install_btn = ttk.Button(button_frame, text="一键安装全部", 
                                     command=self.install_all)
        self.install_btn.pack(side=tk.LEFT, padx=5)
        
        self.uninstall_btn = ttk.Button(button_frame, text="一键卸载", 
                                     command=self.uninstall_all,
                                     style="Danger.TButton")
        self.uninstall_btn.pack(side=tk.LEFT, padx=5)
        
        self.check_btn = ttk.Button(button_frame, text="检查PATH", 
                                   command=self.check_environment)
        self.check_btn.pack(side=tk.LEFT, padx=5)
        
        self.start_gui_btn = ttk.Button(button_frame, text="启动助手", 
                                       command=self.start_gui,
                                       style="Success.TButton")
        self.start_gui_btn.pack(side=tk.LEFT, padx=5)
        
        # 创建红色按钮样式
        self.style = ttk.Style()
        if 'Danger.TButton' not in self.style.theme_names():
            self.style.configure('Danger.TButton', foreground='red')
        if 'Success.TButton' not in self.style.theme_names():
            self.style.configure('Success.TButton', foreground='green')
    
    def log(self, message):
        """添加日志"""
        with self.log_lock:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
            self.update_idletasks()
    
    def update_component_status(self, index, status):
        """更新组件状态"""
        self.components[index]["status"] = status
        item_id = self.component_listbox.get_children()[index]
        values = list(self.component_listbox.item(item_id, "values"))
        values[2] = status
        self.component_listbox.item(item_id, values=values)
        self.update_idletasks()
    
    def check_environment(self):
        """检查PATH环境变量是否生效"""
        self.log("=== 开始检查PATH环境变量 ===")
        
        # 刷新环境变量
        self.refresh_env_variables(force_subprocess_check=True)
        
        # 在检查前确保 npm 全局 bin 目录临时加入当前进程 PATH（避免 Appium 误判）
        self._ensure_npm_bin_in_process_path()
        
        # 检查关键命令是否在PATH中可用
        commands_to_check = [
            {"name": "Python", "cmd": "python", "expected_output": "Python 3.11"},
            {"name": "pip", "cmd": "pip", "expected_output": "pip"},
            {"name": "Node.js", "cmd": "node", "expected_output": "v18"},
            {"name": "npm", "cmd": "npm", "expected_output": "npm"},
            {"name": "Android ADB", "cmd": "adb", "expected_output": "Android Debug Bridge"},
            {"name": "Appium", "cmd": "appium", "expected_output": "2.5.0"},
        ]
        
        path_status = {}
        
        for command_info in commands_to_check:
            name = command_info["name"]
            cmd = command_info["cmd"]
            expected = command_info["expected_output"]
            
            self.log(f"检查 {name} 命令...")
            
            try:
                # 首先检查命令是否在PATH中
                where_result = subprocess.run(
                    f"where {cmd}", 
                    shell=True, 
                    capture_output=True, 
                    text=True
                )
                
                if where_result.returncode == 0:
                    cmd_path = where_result.stdout.strip().split('\n')[0]
                    self.log(f"✅ {name} 路径: {cmd_path}")
                    
                    # 检查版本信息
                    try:
                        if cmd == "adb":
                            version_cmd = f"{cmd} version"
                        elif cmd == "appium":
                            version_cmd = f"{cmd} --version"
                        else:
                            version_cmd = f"{cmd} --version"
                            
                        version_result = subprocess.run(
                            version_cmd,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        
                        if version_result.returncode == 0:
                            version_output = version_result.stdout + version_result.stderr
                            if expected.lower() in version_output.lower():
                                self.log(f"✅ {name} 版本正确: {version_output.strip()[:50]}...")
                                path_status[name] = "✅ 可用"
                            else:
                                self.log(f"⚠️ {name} 版本可能不匹配: {version_output.strip()[:50]}...")
                                path_status[name] = "⚠️ 版本异常"
                        else:
                            self.log(f"⚠️ {name} 版本检查失败: {version_result.stderr[:50]}...")
                            path_status[name] = "⚠️ 版本检查失败"
                            
                    except subprocess.TimeoutExpired:
                        self.log(f"⚠️ {name} 版本检查超时")
                        path_status[name] = "⚠️ 检查超时"
                    except Exception as e:
                        self.log(f"⚠️ {name} 版本检查异常: {str(e)}")
                        path_status[name] = "⚠️ 检查异常"
                else:
                    self.log(f"❌ {name} 不在PATH中")
                    path_status[name] = "❌ 未找到"
                    
            except Exception as e:
                self.log(f"❌ 检查 {name} 时出错: {str(e)}")
                path_status[name] = "❌ 检查失败"
        
        # 显示当前PATH环境变量信息
        self.log("=== PATH环境变量信息 ===")
        current_path = os.environ.get('PATH', '')
        path_entries = [p.strip() for p in current_path.split(';') if p.strip()]
        
        # 显示Python相关路径
        python_paths = [p for p in path_entries if 'python' in p.lower()]
        if python_paths:
            self.log("Python相关路径:")
            for path in python_paths[:3]:  # 只显示前3个
                self.log(f"  - {path}")
        
        # 显示Node.js相关路径
        node_paths = [p for p in path_entries if any(x in p.lower() for x in ['node', 'npm'])]
        if node_paths:
            self.log("Node.js相关路径:")
            for path in node_paths[:3]:  # 只显示前3个
                self.log(f"  - {path}")
                
        # 显示Android相关路径
        android_paths = [p for p in path_entries if 'android' in p.lower()]
        if android_paths:
            self.log("Android相关路径:")
            for path in android_paths[:3]:  # 只显示前3个
                self.log(f"  - {path}")
        
        # 显示总结
        self.log("=== PATH检查总结 ===")
        for name, status in path_status.items():
            self.log(f"{name}: {status}")
            
        # 更新组件状态（基于PATH检查结果）
        for i, component in enumerate(self.components):
            component_name = component['name']
            if "Python" in component_name:
                if "Python" in path_status and "✅" in path_status["Python"]:
                    self.update_component_status(i, "PATH正常")
                else:
                    self.update_component_status(i, "PATH异常")
            elif "Node.js" in component_name:
                if "Node.js" in path_status and "✅" in path_status["Node.js"]:
                    self.update_component_status(i, "PATH正常")
                else:
                    self.update_component_status(i, "PATH异常")
            elif "Android" in component_name:
                if "Android ADB" in path_status and "✅" in path_status["Android ADB"]:
                    self.update_component_status(i, "PATH正常")
                else:
                    self.update_component_status(i, "PATH异常")
            elif "Appium" in component_name:
                if "Appium" in path_status and "✅" in path_status["Appium"]:
                    self.update_component_status(i, "PATH正常")
                else:
                    self.update_component_status(i, "PATH异常")
            elif "项目依赖" in component_name:
                if "pip" in path_status and "✅" in path_status["pip"]:
                    self.update_component_status(i, "PATH正常")
                else:
                    self.update_component_status(i, "PATH异常")
        
        self.log("=== PATH环境变量检查完成 ===")
    
    def start_gui(self):
        """启动大麦票务助手GUI程序"""
        try:
            # 查找start_gui.pyw文件
            gui_script = None
            
            # 先检查当前目录的父目录（假设安装器在项目根目录）
            parent_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
            if getattr(sys, 'frozen', False):
                # 如果是打包的exe，获取exe所在目录
                parent_dir = os.path.dirname(sys.executable)
            
            gui_script_path = os.path.join(parent_dir, "start_gui.pyw")
            
            if os.path.exists(gui_script_path):
                gui_script = gui_script_path
            else:
                # 尝试其他可能的位置
                possible_paths = [
                    os.path.join(os.getcwd(), "start_gui.pyw"),
                    os.path.join(parent_dir, "..", "start_gui.pyw"),
                    os.path.join(parent_dir, "start_gui.pyw"),
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        gui_script = os.path.abspath(path)
                        break
            
            if gui_script:
                self.log(f"找到GUI启动脚本: {gui_script}")
                self.log("正在启动大麦票务助手...")
                
                # 使用pythonw启动pyw文件（无控制台窗口）
                subprocess.Popen([
                    "pythonw", gui_script
                ], cwd=os.path.dirname(gui_script))
                
                self.log("✅ 大麦票务助手启动成功！")
                
            else:
                error_msg = "❌ 未找到start_gui.pyw文件！\n请确保安装器与项目文件在同一目录。"
                self.log(error_msg)
                messagebox.showerror("启动失败", error_msg)
                
        except Exception as e:
            error_msg = f"❌ 启动助手时出错: {str(e)}"
            self.log(error_msg)
            messagebox.showerror("启动失败", error_msg)
    
    def startup_check_components(self):
        """启动时简单检查组件安装状态"""
        self.log("开始检查环境...")
        
        for i, component in enumerate(self.components):
            if "check_cmd" in component and component["check_cmd"]:
                try:
                    # 在检查前确保 npm 全局 bin 已加入当前进程 PATH（针对 Appium）
                    if "Appium" in component.get("name", "") or component.get("type") == "npm":
                        self._ensure_npm_bin_in_process_path()
                    
                    # 对 Appium 使用更稳健的检查命令，避免管道与 findstr 造成误判
                    check_cmd = component["check_cmd"]
                    if "Appium" in component.get("name", ""):
                        check_cmd = "appium --version"
                    
                    # 使用较短的超时时间，避免启动时卡顿
                    result = subprocess.run(
                        check_cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5  # 5秒超时
                    )
                    
                    # 为pip类型的组件特殊处理
                    if component.get("type") == "pip":
                        # 对于Python包检查，要求返回码为0且输出包含"OK"
                        if result.returncode == 0 and "OK" in result.stdout:
                            self.update_component_status(i, "已安装")
                            self.log(f"'{component['name']}' 已安装")
                        else:
                            self.update_component_status(i, "未安装")
                            self.log(f"'{component['name']}' 未安装")
                    else:
                        # 对于其他组件，只检查返回码
                        if result.returncode == 0:
                            self.update_component_status(i, "已安装")
                            self.log(f"'{component['name']}' 已安装")
                        else:
                            self.update_component_status(i, "未安装")
                            self.log(f"'{component['name']}' 未安装")
                            
                except subprocess.TimeoutExpired:
                    # 超时的情况下标记为未安装
                    self.update_component_status(i, "未安装")
                    self.log(f"'{component['name']}' 检查超时，标记为未安装")
                except Exception as e:
                    self.update_component_status(i, "未安装")
                    self.log(f"'{component['name']}' 检查失败: {str(e)}")
            else:
                # 没有检查命令的组件保持默认状态
                self.log(f"'{component['name']}' 无法检查，保持默认状态")
        
        self.log("环境检查完成")
    
    def install_all(self):
        """安装所有组件"""
        self.install_btn.config(state=tk.DISABLED)
        self.check_btn.config(state=tk.DISABLED)
        self.install_thread = threading.Thread(target=self._install_all_thread, daemon=True)
        self.install_thread.start()
    
    def _install_all_thread(self):
        """安装线程"""
        try:
            # 获取安装文件的实际路径
            installer_dir = resource_path("installer_files")
            self.log(f"安装文件路径: {installer_dir}")
            self.log("开始安装，请耐心等待...")
            
            # 记录系统信息，便于调试
            self.log(f"系统编码: {locale.getpreferredencoding()}")
            self.log(f"Python 版本: {sys.version}")
            self.log(f"系统平台: {sys.platform}")
            
            # 记录是否以管理员权限运行
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
                self.log(f"是否以管理员身份运行: {'是' if is_admin else '否'}")
                if not is_admin:
                    self.log("警告: 未以管理员身份运行，某些组件可能安装失败")
            except:
                self.log("无法检查管理员权限")
            
            # 定义组件依赖关系
            dependencies = {
                "Node.js 18.18.2 LTS": [],  # Node.js没有依赖
                "Python 3.11.6": [],  # Python没有依赖
                "Appium Server 2.5.0": ["Node.js 18.18.2 LTS"],  # Appium依赖Node.js
                "Android Platform Tools": [],  # Platform Tools没有依赖
                "项目依赖安装": ["Python 3.11.6"]  # 项目依赖依赖Python
            }
            
            # 按依赖顺序安装组件
            installed_components = set()
            failed_components = set()
            
            # 先检查已安装的组件
            for i, component in enumerate(self.components):
                if component["status"] == "已安装":
                    installed_components.add(component["name"])
                    self.log(f"组件已安装: '{component['name']}'")
            
            # 尝试最多两轮安装，以处理依赖关系
            for attempt in range(2):
                self.log(f"开始安装轮次 {attempt+1}...")
                
                for i, component in enumerate(self.components):
                    component_name = component["name"]
                    
                    # 跳过已安装或已失败的组件
                    if component_name in installed_components:
                        continue
                    if component_name in failed_components:
                        continue
                    
                    # 检查依赖是否已满足
                    if component_name in dependencies:
                        missing_deps = [dep for dep in dependencies[component_name] if dep not in installed_components]
                        if missing_deps:
                            self.log(f"组件 '{component_name}' 依赖未满足: {', '.join(missing_deps)}，暂时跳过")
                            continue
                    
                    self.log(f"正在安装 '{component_name}'...")
                    try:
                        # 安装组件
                        self.install_component(i, installer_dir)
                        self.update_component_status(i, "已安装")
                        installed_components.add(component_name)
                            
                    except Exception as e:
                        self.log(f"组件 '{component_name}' 安装失败: {str(e)}")
                        self.update_component_status(i, "安装失败")
                        failed_components.add(component_name)
                
                # 如果所有组件都已处理，则跳出循环
                if len(installed_components) + len(failed_components) >= len(self.components):
                    break

            # 检查是否所有组件都已安装
            all_installed = all(comp["status"] == "已安装" for comp in self.components)
            
            # 安装 PyArmor 运行时库
            self.log("\n开始安装 PyArmor 运行时库（解决 'No module named pyarmor_runtime_000000' 问题）")
            pyarmor_installed = self.install_pyarmor_runtime()
            
            if all_installed:
                if pyarmor_installed:
                    self.log("所有组件和 PyArmor 运行时库安装完成！")
                    messagebox.showinfo("成功", "所有组件已成功安装！")
                else:
                    self.log("所有组件已安装，但 PyArmor 运行时库安装失败！")
                    messagebox.showinfo("安装完成", "核心组件安装成功！\n\nPyArmor 运行时库安装失败，但这不会影响主要功能。\n如需完整功能，可以稍后手动安装 pyarmor>=9.1.9")
            else:
                failed_components = [comp["name"] for comp in self.components if comp["status"] != "已安装"]
                self.log(f"部分组件安装失败: {', '.join(failed_components)}")
                messagebox.showwarning("部分完成", f"以下组件安装失败: {', '.join(failed_components)}\n请查看日志获取详情")

        except Exception as e:
            self.log(f"安装失败: {str(e)}")
            self.log(f"堆栈跟踪: {traceback.format_exc()}")
            messagebox.showerror("错误", f"安装过程中发生错误: {e}")
        finally:
            self.install_btn.config(state=tk.NORMAL)
            self.check_btn.config(state=tk.NORMAL)
    
    def install_component(self, index, installer_dir):
        component = self.components[index]
        cmd = ""
        try:
            if component["type"] == "exe":
                # Python 安装 - 特别处理
                path = os.path.normpath(os.path.join(installer_dir, component["file"]))
                
                # 检查安装文件是否存在
                if not os.path.exists(path):
                    # 如果找不到文件，尝试在其他位置查找
                    possible_paths = [
                        os.path.join(os.path.dirname(installer_dir), component["file"]),
                        os.path.join("_internal", "installer_files", component["file"]),
                        os.path.join(os.getcwd(), "installer_files", component["file"]),
                        resource_path(os.path.join("installer_files", component["file"])),
                    ]
                    
                    for alt_path in possible_paths:
                        if os.path.exists(alt_path):
                            path = alt_path
                            self.log(f"找到安装程序在替代位置: {path}")
                            break
                
                # 最终检查
                if not os.path.exists(path):
                    self.log(f"错误: 安装程序文件不存在: {path}")
                    raise Exception(f"安装文件不存在: {path}")
                
                # 格式化命令，路径不带引号
                cmd = component["install_cmd"].format(path=path)
                
                # 记录额外信息
                self.log(f"安装程序路径: {path}")
                self.log(f"执行命令: {cmd}")
                self.log(f"执行: {cmd}")
                
            elif component["type"] == "msi":
                # MSI 安装需要特别处理路径，确保路径被正确引用
                path = os.path.normpath(os.path.join(installer_dir, component["file"]))
                
                # 检查文件是否存在
                if not os.path.exists(path):
                    self.log(f"错误: MSI文件不存在: {path}")
                    raise Exception(f"安装文件不存在: {path}")
                
                # 格式化命令时不添加引号，因为install_cmd中已经有格式
                cmd = component["install_cmd"].format(path=path)
                
                # 记录额外信息
                self.log(f"MSI路径: {path}")
                self.log(f"执行命令: {cmd}")
                self.log(f"执行: {cmd}")
                
            elif component["type"] == "npm":
                # 检查 Node.js 是否已正确安装并且环境变量已更新
                self.log("检查Node.js安装状态...")
                
                # 确保Node.js安装成功完成
                if not any(comp["name"] == "Node.js 18.18.2 LTS" and comp["status"] == "已安装" for comp in self.components):
                    self.log("依赖错误: Node.js未安装，无法继续安装Appium")
                    raise Exception("依赖错误: 需要先安装Node.js")
                
                # 刷新环境变量以确保 npm 命令可用
                self.log("刷新环境变量以确保npm命令可用...")
                self.refresh_env_variables()
                
                # 测试 npm 命令是否可用
                try:
                    result = subprocess.run(['npm', '--version'], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        self.log(f"✅ npm 命令可用，版本: {result.stdout.strip()}")
                    else:
                        # 尝试使用完整路径
                        nodejs_paths = [
                            r"C:\Program Files\nodejs\npm.cmd",
                            r"C:\Program Files (x86)\nodejs\npm.cmd", 
                            os.path.expanduser(r"~\AppData\Roaming\npm\npm.cmd")
                        ]
                        for npm_path in nodejs_paths:
                            if os.path.exists(npm_path):
                                os.environ['PATH'] = os.path.dirname(npm_path) + os.pathsep + os.environ.get('PATH', '')
                                self.log(f"🔧 添加 npm 路径到环境变量: {os.path.dirname(npm_path)}")
                                break
                except Exception as e:
                    self.log(f"⚠️ npm 命令测试失败: {e}")
                
                # 先尝试离线安装，失败后自动切换到在线安装
                self._install_appium_with_fallback(installer_dir)
                return  # 直接返回，不需要继续执行后面的cmd设置
                
            elif component["type"] == "zip":
                zip_path = os.path.join(installer_dir, component["file"])
                
                # 检查ZIP文件是否存在
                if not os.path.exists(zip_path):
                    # 尝试查找其他可能的位置
                    possible_paths = [
                        os.path.join(os.path.dirname(installer_dir), component["file"]),
                        os.path.join("_internal", "installer_files", component["file"]),
                        os.path.join(os.getcwd(), "installer_files", component["file"]),
                        resource_path(os.path.join("installer_files", component["file"])),
                    ]
                    
                    for alt_path in possible_paths:
                        if os.path.exists(alt_path):
                            zip_path = alt_path
                            self.log(f"找到ZIP文件在替代位置: {zip_path}")
                            break
                
                # 最终检查
                if not os.path.exists(zip_path):
                    self.log(f"错误: ZIP文件不存在: {zip_path}")
                    raise Exception(f"ZIP文件不存在: {zip_path}")
                
                extract_dir = component["extract_dir"]
                self.log(f"解压 {zip_path} 到 {extract_dir}")
                
                try:
                    # 确保目标目录存在
                    if not os.path.exists(extract_dir):
                        os.makedirs(extract_dir, exist_ok=True)
                    
                    # 解压时，为了避免解压后多一层 "platform-tools" 目录，我们先检查zip包内的结构
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        # 检查zip文件内的顶级目录名是否为 "platform-tools"
                        top_level_dirs = {os.path.normpath(f.filename).split(os.sep)[0] for f in zip_ref.infolist()}
                        
                        if len(top_level_dirs) == 1 and list(top_level_dirs)[0] == 'platform-tools':
                            # 如果zip包内有一个顶层目录 "platform-tools"，我们应该解压到其父目录
                            # C:/Android/platform-tools -> C:/Android
                            extract_target_dir = os.path.dirname(extract_dir)
                            self.log(f"检测到顶层目录 'platform-tools'，将解压到: {extract_target_dir}")
                            os.makedirs(extract_target_dir, exist_ok=True)
                            zip_ref.extractall(extract_target_dir)
                        else:
                            # 否则，直接解压到目标目录
                            zip_ref.extractall(extract_dir)

                    self.log(f"成功解压ZIP文件到: {extract_dir}")
                except Exception as e:
                    self.log(f"解压ZIP文件时出错: {str(e)}")
                    raise
                
                # 添加到PATH环境变量
                try:
                    # 添加到当前进程PATH
                    current_path = os.environ.get('PATH', '')
                    if extract_dir not in current_path:
                        os.environ['PATH'] = f"{extract_dir};{current_path}"
                        self.log(f"已将 {extract_dir} 添加到当前进程PATH环境变量")
                    
                    # 尝试将环境变量永久添加到用户变量
                    self.add_to_user_path(extract_dir)

                except Exception as e:
                    self.log(f"添加PATH环境变量时出错: {str(e)}")
                
                # 如果是Android Platform Tools，则设置Android环境变量
                if "Android Platform Tools" in component["name"]:
                    self._setup_android_env_variables()
                
                return
                
            elif component["type"] == "pip":
                # 确保Python安装成功完成
                if not any(comp["name"] == "Python 3.11.6" and comp["status"] == "已安装" for comp in self.components):
                    self.log("依赖错误: Python未安装，无法继续安装Python依赖")
                    raise Exception("依赖错误: 需要先安装Python")
                
                # 注意: Python自动安装后直接尝试查找pip
                
                # 寻找pip
                pip_path = self.find_program("pip.exe")
                self.log(f"查找到pip路径: {pip_path}")
                
                if not pip_path:
                    # 尝试查找Python安装目录下的pip - 增强路径查找
                    current_username = os.environ.get('USERNAME', 'Administrator')
                    possible_paths = [
                        # 用户特定路径
                        f"C:\\Users\\{current_username}\\AppData\\Local\\Programs\\Python\\Python311\\Scripts\\pip.exe",
                        # 标准系统路径
                        r"C:\Python311\Scripts\pip.exe",
                        r"C:\Program Files\Python311\Scripts\pip.exe",
                        r"C:\Program Files (x86)\Python311\Scripts\pip.exe",
                        # 环境变量路径
                        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311\Scripts\pip.exe"),
                        os.path.expandvars(r"%ProgramFiles%\Python311\Scripts\pip.exe"),
                        os.path.expandvars(r"%ProgramFiles(x86)%\Python311\Scripts\pip.exe"),
                        # 其他可能的路径
                        r"C:\Users\Administrator\AppData\Local\Programs\Python\Python311\Scripts\pip.exe",
                        r"C:\Users\10000\AppData\Local\Programs\Python\Python311\Scripts\pip.exe",
                    ]
                    
                    for possible_pip in possible_paths:
                        if os.path.exists(possible_pip):
                            pip_path = possible_pip
                            self.log(f"找到pip在其他位置: {pip_path}")
                            break
                
                # 构建更健壮的 pip 命令
                # 尝试多种可能的wheels目录位置
                wheels_dir = None
                possible_wheels_dirs = [
                    os.path.normpath(os.path.join(installer_dir, "wheels")),
                    os.path.normpath(resource_path("wheels")),
                    os.path.normpath(os.path.join(os.path.dirname(installer_dir), "wheels")),
                    os.path.normpath(os.path.join(installer_dir, "..", "wheels")),
                    os.path.normpath(os.path.join(installer_dir, "..", "installer_files", "wheels")),
                ]
                
                # 查找wheels目录
                for dir_path in possible_wheels_dirs:
                    if os.path.exists(dir_path) and os.path.isdir(dir_path):
                        wheels_dir = dir_path
                        self.log(f"找到wheels目录: {wheels_dir}")
                        break
                
                # 查找requirements.txt文件
                requirements_path = None
                possible_req_paths = [
                    os.path.normpath(os.path.join(installer_dir, "..", "resources", "requirements.txt")),
                    os.path.normpath(resource_path("resources/requirements.txt")),
                    os.path.normpath(os.path.join(installer_dir, "resources", "requirements.txt")),
                    os.path.normpath(os.path.join(os.path.dirname(installer_dir), "resources", "requirements.txt")),
                    os.path.normpath(os.path.join(installer_dir, "requirements.txt")),
                    os.path.normpath(os.path.join(os.path.dirname(installer_dir), "requirements.txt")),
                    # _internal目录下的可能位置
                    os.path.normpath(os.path.join(installer_dir, "..", "_internal", "resources", "requirements.txt")),
                    os.path.normpath(os.path.join(installer_dir, "_internal", "resources", "requirements.txt")),
                ]
                
                # 查找requirements.txt文件
                for req_path in possible_req_paths:
                    if os.path.exists(req_path) and os.path.isfile(req_path):
                        requirements_path = req_path
                        self.log(f"找到requirements.txt在: {requirements_path}")
                        break
                    
                self.log(f"Requirements路径: {requirements_path}")
                self.log(f"Wheels目录: {wheels_dir}")
                
                # 检查文件是否存在
                if not requirements_path or not os.path.exists(requirements_path):
                    # 如果找不到requirements.txt文件，尝试创建一个默认的
                    self.log(f"警告: requirements.txt 文件不存在，创建默认文件")
                    temp_req_path = os.path.join(os.environ.get('TEMP', os.environ.get('TMP', '.')), 'requirements.txt')
                    try:
                        with open(temp_req_path, 'w') as f:
                            f.write("appium-python-client>=2.0.0\n")
                            f.write("Pillow>=9.0.0\n")
                            f.write("opencv-python>=4.0.0\n")
                            f.write("numpy>=1.0.0\n")
                            f.write("pyarmor>=9.1.9\n")  # 添加PyArmor依赖
                        requirements_path = temp_req_path
                        self.log(f"已创建临时requirements文件: {requirements_path}")
                    except Exception as e:
                        self.log(f"创建临时requirements文件失败: {str(e)}")
                        raise Exception(f"依赖文件不存在，且无法创建临时文件: {str(e)}")
                
                if not wheels_dir or not os.path.exists(wheels_dir):
                    self.log(f"警告: wheels 目录不存在，将使用在线安装模式")
                    # 如果没有本地wheel目录，切换为在线安装模式
                    if pip_path:
                        self.log(f"使用找到的pip: {pip_path}")
                        cmd = f'"{pip_path}" install --upgrade appium-python-client Pillow opencv-python numpy'
                    else:
                        self.log("无法找到pip，使用python -m pip")
                        cmd = f'python -m pip install --upgrade appium-python-client Pillow opencv-python numpy'
                else:
                    # 使用本地wheels目录
                    if pip_path:
                        self.log(f"使用找到的pip与本地wheels: {pip_path}")
                        cmd = f'"{pip_path}" install --no-cache-dir --no-index --find-links="{wheels_dir}" -r "{requirements_path}"'
                    else:
                        # 尝试使用python -m pip作为备选
                        python_path = self.find_program("python.exe")
                        if python_path:
                            self.log(f"使用Python模块pip: {python_path}")
                            cmd = f'"{python_path}" -m pip install --no-cache-dir --no-index --find-links="{wheels_dir}" -r "{requirements_path}"'
                        else:
                            self.log("无法找到pip或python，使用默认命令")
                            cmd = f'python -m pip install --no-cache-dir --no-index --find-links="{wheels_dir}" -r "{requirements_path}"'
                
                self.log(f"执行: {cmd}")
            
            # 执行命令
            try:
                self.run_command(cmd)
            except Exception as e:
                self.log(f"命令执行失败: {str(e)}")
                
                # 对于MSI命令失败，尝试使用绝对路径到msiexec
                if "msiexec" in cmd and "msi" in component["type"].lower():
                    self.log("尝试使用绝对路径到msiexec...")
                    # 替换命令中的msiexec为绝对路径
                    msiexec_path = r"C:\Windows\System32\msiexec.exe"
                    if os.path.exists(msiexec_path):
                        new_cmd = cmd.replace("msiexec", f'"{msiexec_path}"')
                        self.log(f"重试命令: {new_cmd}")
                        self.run_command(new_cmd)
                    else:
                        raise e
                else:
                    raise e
            
            # Python和Node.js现在自动静默安装
            pass
                
        except Exception as e:
            error_msg = f"安装 {component['name']} 时发生错误: {str(e)}"
            self.log(error_msg)
            # 在组件安装失败时提供更清晰的错误消息
            if "msiexec" in str(cmd).lower():
                self.log("MSI 安装提示: 请确保您有管理员权限运行此程序")
            elif "pip" in str(cmd).lower():
                self.log("PIP 安装提示: 可能的编码问题，尝试使用 --no-cache-dir 选项")
            raise Exception(error_msg)
    
    def _install_appium_with_fallback(self, installer_dir):
        """使用离线安装和在线安装的回退策略安装Appium"""
        
        # 获取脚本文件路径 - 使用 resource_path 确保打包后正确
        offline_script_path = resource_path(os.path.join("scripts", "install_appium_offline.cmd"))
        online_script_path = resource_path(os.path.join("scripts", "install_appium_online.cmd"))
        
        # 检查是否有离线 Appium 包 (使用正确的版本 2.5.0)
        # installer_dir 应该已经指向 installer_files 目录
        self.log(f"🔍 离线包检测: installer_dir = {installer_dir}")
        
        offline_package_path = os.path.join(installer_dir, "npm_packages", "appium-2.5.0.tgz")
        self.log(f"🔍 检查主要离线包路径: {offline_package_path}")
        self.log(f"🔍 路径存在: {os.path.exists(offline_package_path)}")
        
        # 列出 npm_packages 目录内容进行调试
        npm_dir = os.path.join(installer_dir, "npm_packages")
        if os.path.exists(npm_dir):
            self.log(f"📁 npm_packages 目录存在，内容: {os.listdir(npm_dir)}")
        else:
            self.log(f"❌ npm_packages 目录不存在: {npm_dir}")
        
        if not os.path.exists(offline_package_path):
            # 尝试其他可能的位置
            possible_offline_paths = [
                resource_path(os.path.join("installer_files", "npm_packages", "appium-2.5.0.tgz")),
                os.path.join("_internal", "installer_files", "npm_packages", "appium-2.5.0.tgz"),
                os.path.join(os.getcwd(), "installer_files", "npm_packages", "appium-2.5.0.tgz"),
            ]
            
            self.log("🔍 尝试备用路径...")
            for alt_path in possible_offline_paths:
                self.log(f"   检查: {alt_path} -> {os.path.exists(alt_path)}")
            
            for alt_path in possible_offline_paths:
                if os.path.exists(alt_path):
                    offline_package_path = alt_path
                    break
            else:
                offline_package_path = None
        
        # 策略1：尝试离线安装（使用脚本）
        if offline_package_path and os.path.exists(offline_package_path) and os.path.exists(offline_script_path):
            self.log(f"=== 尝试离线安装 Appium 2.5.0 + UiAutomator2 Driver 2.45.1 ===")
            self.log(f"使用离线包: {offline_package_path}")
            self.log(f"使用离线安装脚本: {offline_script_path}")
            
            # 执行离线安装脚本
            try:
                # 设置脚本工作目录为包含离线包的目录
                script_work_dir = os.path.dirname(offline_package_path)
                result = subprocess.run(
                    f'cmd /c "{offline_script_path}"',
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=script_work_dir
                )
                
                if result.returncode == 0:
                    self.log("✅ 离线安装 Appium 成功!")
                    self.log(f"脚本输出: {result.stdout}")
                    # 将 npm 全局 bin（如 %APPDATA%\\npm）持久加入用户 PATH，避免下次启动误判
                    self._ensure_npm_bin_in_user_path()
                    # 立即广播环境变量更新
                    self.refresh_env_variables()
                    return  # 成功则直接返回
                else:
                    raise Exception(f"离线安装脚本执行失败，返回码: {result.returncode}, 错误: {result.stderr}")
                    
            except Exception as e:
                self.log(f"❌ 离线安装失败: {str(e)}")
                self.log("将尝试在线安装作为备用方案...")
        else:
            if not offline_package_path or not os.path.exists(offline_package_path):
                self.log("未找到离线包，将直接尝试在线安装")
            else:
                self.log("未找到离线安装脚本，将直接尝试在线安装")
        
        # 策略2：在线安装作为备用方案（使用脚本）
        if os.path.exists(online_script_path):
            self.log(f"=== 尝试在线安装 Appium 2.5.0 + UiAutomator2 Driver 2.45.1 ===")
            self.log(f"使用在线安装脚本: {online_script_path}")
            
            try:
                result = subprocess.run(
                    f'cmd /c "{online_script_path}"',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    self.log("✅ 在线安装 Appium 成功!")
                    self.log(f"脚本输出: {result.stdout}")
                    # 将 npm 全局 bin（如 %APPDATA%\\npm）持久加入用户 PATH，避免下次启动误判
                    self._ensure_npm_bin_in_user_path()
                    # 立即广播环境变量更新
                    self.refresh_env_variables()
                    return
                else:
                    raise Exception(f"在线安装脚本执行失败，返回码: {result.returncode}, 错误: {result.stderr}")
                    
            except Exception as e:
                self.log(f"❌ 在线安装也失败: {str(e)}")
        else:
            self.log(f"❌ 未找到在线安装脚本: {online_script_path}")
        
        # 如果脚本安装都失败，显示手动安装指引弹窗
        self._show_manual_install_dialog()
        
        error_msg = f"Appium安装失败 - 离线和在线安装都失败了"
        raise Exception(error_msg)
    
    def _setup_android_env_variables(self):
        """设置Android环境变量"""
        self.log("=== 设置Android环境变量 ===")
        
        # 获取环境变量设置脚本路径 - 使用 resource_path 确保打包后正确
        env_script_path = resource_path(os.path.join("scripts", "setup_android_env.cmd"))
        
        if not os.path.exists(env_script_path):
            self.log(f"环境变量设置脚本不存在: {env_script_path}")
            # 手动设置环境变量作为备选方案
            self._manual_setup_android_env()
            return
        
        try:
            self.log(f"执行Android环境变量设置脚本: {env_script_path}")
            result = subprocess.run(
                f'cmd /c "{env_script_path}"',
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.log("✅ Android环境变量设置成功!")
                self.log(f"脚本输出: {result.stdout}")
                # 立即刷新环境变量
                self.refresh_env_variables()
            else:
                self.log(f"❌ 环境变量设置脚本执行失败: {result.stderr}")
                # 手动设置作为备选方案
                self._manual_setup_android_env()
                
        except Exception as e:
            self.log(f"❌ 设置Android环境变量时出错: {str(e)}")
            # 手动设置作为备选方案
            self._manual_setup_android_env()
    
    def _manual_setup_android_env(self):
        """手动设置Android环境变量"""
        self.log("使用手动方式设置Android环境变量...")
        
        try:
            # 设置ANDROID_SDK_ROOT（尝试系统级，失败则用户级）
            cmd1 = 'setx ANDROID_SDK_ROOT "C:\\Android" /M'
            result1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True)
            if result1.returncode == 0:
                self.log("✅ ANDROID_SDK_ROOT设置成功（系统变量）")
            else:
                self.log("⚠️ 系统变量设置失败，尝试用户变量...")
                cmd1_user = 'setx ANDROID_SDK_ROOT "C:\\Android"'
                result1_user = subprocess.run(cmd1_user, shell=True, capture_output=True, text=True)
                if result1_user.returncode == 0:
                    self.log("✅ ANDROID_SDK_ROOT设置成功（用户变量）")
                else:
                    self.log(f"❌ ANDROID_SDK_ROOT设置失败: {result1_user.stderr}")
            
            # 设置ANDROID_HOME（尝试系统级，失败则用户级）
            cmd2 = 'setx ANDROID_HOME "C:\\Android" /M'
            result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
            if result2.returncode == 0:
                self.log("✅ ANDROID_HOME设置成功（系统变量）")
            else:
                self.log("⚠️ 系统变量设置失败，尝试用户变量...")
                cmd2_user = 'setx ANDROID_HOME "C:\\Android"'
                result2_user = subprocess.run(cmd2_user, shell=True, capture_output=True, text=True)
                if result2_user.returncode == 0:
                    self.log("✅ ANDROID_HOME设置成功（用户变量）")
                else:
                    self.log(f"❌ ANDROID_HOME设置失败: {result2_user.stderr}")
            
            # 添加platform-tools到PATH（使用更安全的方法）
            self.log("添加platform-tools到PATH...")
            try:
                # 先检查是否已存在
                current_path = os.environ.get('PATH', '')
                if 'C:\\Android\\platform-tools' not in current_path:
                    # 尝试系统PATH
                    cmd3 = 'reg query "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" /v PATH'
                    result_query = subprocess.run(cmd3, shell=True, capture_output=True, text=True)
                    
                    if result_query.returncode == 0 and 'C:\\Android\\platform-tools' not in result_query.stdout:
                        # 尝试添加到系统PATH
                        cmd3_sys = 'for /f "tokens=2*" %i in (\'reg query "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" /v PATH\') do setx PATH "%j;C:\\Android\\platform-tools" /M'
                        result3_sys = subprocess.run(cmd3_sys, shell=True, capture_output=True, text=True)
                        
                        if result3_sys.returncode == 0:
                            self.log("✅ platform-tools添加到系统PATH成功")
                        else:
                            # 回退到用户PATH
                            cmd3_user = 'setx PATH "%PATH%;C:\\Android\\platform-tools"'
                            result3_user = subprocess.run(cmd3_user, shell=True, capture_output=True, text=True)
                            if result3_user.returncode == 0:
                                self.log("✅ platform-tools添加到用户PATH成功")
                            else:
                                self.log(f"❌ 添加platform-tools到PATH失败: {result3_user.stderr}")
                    else:
                        self.log("✅ platform-tools已存在于系统PATH中")
                else:
                    self.log("✅ platform-tools已存在于当前PATH中")
                    
            except Exception as path_error:
                self.log(f"❌ PATH设置过程出错: {str(path_error)}")
                # 最简单的回退方案
                cmd3_simple = 'setx PATH "%PATH%;C:\\Android\\platform-tools"'
                result3_simple = subprocess.run(cmd3_simple, shell=True, capture_output=True, text=True)
                if result3_simple.returncode == 0:
                    self.log("✅ platform-tools添加到用户PATH成功（简单模式）")
                else:
                    self.log(f"❌ 简单模式PATH设置也失败: {result3_simple.stderr}")
                
        except Exception as e:
            self.log(f"❌ 手动设置环境变量时出错: {str(e)}")
        
        # 设置完成后刷新环境变量
        self.log("刷新环境变量以使设置立即生效...")
        self.refresh_env_variables()
    




    def _show_manual_install_dialog(self):
        """显示手动安装Appium的指引弹窗 - 可复制内容"""
        import tkinter as tk
        from tkinter import ttk
        
        # 创建自定义对话框窗口
        dialog = tk.Toplevel()
        dialog.title("手动安装 Appium Server 2.5.0")
        dialog.geometry("500x400")
        dialog.resizable(True, True)
        
        # 设置窗口居中
        dialog.transient()
        dialog.grab_set()
        
        # 创建主框架
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="Appium 自动安装失败！", font=("Arial", 12, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 10), sticky=tk.W)
        
        # 创建文本框显示安装指令
        text_content = """请手动安装 Appium Server 2.5.0 + UiAutomator2 Driver 2.45.1：

安装命令：
npm install -g appium@2.5.0
npm install -g appium-doctor
appium driver install uiautomator2@2.45.1

操作步骤：
1. 按 Win + R 打开运行对话框
2. 输入 cmd 并按回车打开命令提示符
3. 复制上述安装命令并粘贴到命令提示符中
4. 按回车执行安装
5. 等待安装完成后重新运行本安装程序

安装验证命令：
appium --version
appium-doctor --version

如果显示 "2.5.0" 和appium-doctor版本号则表示安装成功。"""

        text_widget = tk.Text(main_frame, wrap=tk.WORD, height=15, width=60)
        text_widget.insert(tk.END, text_content)
        text_widget.config(state=tk.NORMAL)  # 允许选择和复制
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # 布局文本框和滚动条
        text_widget.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        # 复制命令按钮
        def copy_command():
            dialog.clipboard_clear()
            dialog.clipboard_append("npm install -g appium@2.5.0 && npm install -g appium-doctor && appium driver install uiautomator2@2.45.1")
            copy_button.config(text="已复制！")
            dialog.after(1500, lambda: copy_button.config(text="复制安装命令"))
        
        copy_button = ttk.Button(button_frame, text="复制安装命令", command=copy_command)
        copy_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 关闭按钮
        close_button = ttk.Button(button_frame, text="关闭", command=dialog.destroy)
        close_button.pack(side=tk.LEFT)
        
        # 让对话框获得焦点
        dialog.focus_set()
        
        # 等待对话框关闭
        dialog.wait_window()
    
    def find_program(self, program_name):
        """查找程序在PATH中的位置"""
        self.log(f"查找程序: {program_name}")
        
        # 尝试使用where命令查找 (Windows)
        try:
            result = subprocess.run(['where', program_name], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True, 
                                   creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0]
                self.log(f"找到程序: {path}")
                return path
        except Exception as e:
            self.log(f"where命令失败: {str(e)}")
        
        # 手动在PATH中查找
        for path_dir in os.environ.get('PATH', '').split(os.pathsep):
            program_path = os.path.join(path_dir, program_name)
            if os.path.isfile(program_path):
                self.log(f"在PATH中找到程序: {program_path}")
                return program_path
        
        self.log(f"未找到程序: {program_name}")
        return None
    
    def refresh_env_variables(self, force_subprocess_check=False):
        """刷新环境变量（简化版，避免阻塞）"""
        self.log("刷新环境变量...")
        
        try:
            # 简单的环境变量刷新 - 仅广播消息
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            
            # 使用ctypes发送消息（设置超时避免阻塞）
            result = ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST, 
                WM_SETTINGCHANGE, 
                0, 
                "Environment",
                0x0002,  # SMTO_ABORTIFHUNG
                2000,    # 2秒超时
                None
            )
            self.log(f"已广播环境变量更改消息，结果: {result}")
        except Exception as e:
            self.log(f"广播环境变量更改失败: {str(e)}")
        
        self.log("环境变量刷新完成")

    def run_command(self, command):
        """运行命令并记录输出"""
        self.log(f"执行: {command}")
        
        # 对特殊命令进行检查和调整
        if 'msiexec' in command.lower():
            # 确保msiexec在系统中存在
            msiexec_path = r"C:\Windows\System32\msiexec.exe"
            if not os.path.exists(msiexec_path):
                self.log(f"警告: msiexec不在标准位置: {msiexec_path}")
                # 尝试搜索msiexec
                try:
                    where_result = subprocess.run("where msiexec", shell=True, check=False, 
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if where_result.returncode == 0 and where_result.stdout.strip():
                        found_path = where_result.stdout.strip().split('\n')[0]
                        self.log(f"找到msiexec在: {found_path}")
                        command = command.replace("msiexec", f'"{found_path}"')
                except Exception as e:
                    self.log(f"搜索msiexec时出错: {str(e)}")
        
        # Use the system preferred encoding (on Windows this will be the ANSI code page)
        # and set errors='replace' so that decoding errors from commands (like pip)
        # won't crash the installer when the tool prints non-UTF-8 output.
        preferred_enc = locale.getpreferredencoding(False)
        # On Windows prefer 'mbcs' to match the native ANSI code page
        if os.name == 'nt':
            preferred_enc = 'mbcs'
            
        # 检查命令中的文件是否存在
        cmd_parts = []
        quote_start = None
        current_part = ""
        
        # 解析命令行，正确处理带引号的部分
        for c in command:
            if c in ['"', "'"]:
                if quote_start is None:
                    quote_start = c
                    current_part += c
                elif quote_start == c:
                    quote_start = None
                    current_part += c
                else:
                    current_part += c
            elif c.isspace() and quote_start is None:
                if current_part:
                    cmd_parts.append(current_part)
                    current_part = ""
            else:
                current_part += c
                
        if current_part:
            cmd_parts.append(current_part)
            
        # 检查命令中的每个部分
        for i, part in enumerate(cmd_parts):
            # 跳过参数和选项
            if part.startswith('-') or part.startswith('/'):
                continue
                
            # 移除引号并解析路径
            cleaned_part = part.strip('"\'')
            ext = os.path.splitext(cleaned_part)[1].lower()
            
            # 检查可执行文件、MSI和其他关键文件
            if ext in ['.exe', '.msi', '.zip']:
                # 如果是带完整路径的文件
                if '\\' in cleaned_part or '/' in cleaned_part:
                    # 检查文件是否存在
                    if not os.path.exists(cleaned_part):
                        self.log(f"警告: 命令中可能不存在的文件: {cleaned_part}")
                        
                        # 检查该文件是否在_internal目录或其他常见位置
                        base_name = os.path.basename(cleaned_part)
                        possible_paths = [
                            os.path.join("_internal", "installer_files", base_name),
                            os.path.join(os.getcwd(), "installer_files", base_name),
                            os.path.join(os.path.dirname(os.getcwd()), "installer_files", base_name),
                        ]
                        
                        for alt_path in possible_paths:
                            if os.path.exists(alt_path):
                                self.log(f"找到文件在替代位置: {alt_path}")
                                # 尝试替换命令中的路径
                                command = command.replace(cleaned_part, alt_path)
                                self.log(f"已调整命令: {command}")
                                break
                
                # 如果是命令的第一部分且只有文件名(不含路径)
                elif i == 0:
                    self.log(f"检查程序是否在PATH中: {cleaned_part}")
                    
                    # 尝试在PATH中查找
                    try:
                        where_result = subprocess.run(f"where {cleaned_part}", 
                                                     shell=True, check=False, 
                                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                                     text=True)
                        if where_result.returncode == 0 and where_result.stdout.strip():
                            found_path = where_result.stdout.strip().split('\n')[0]
                            self.log(f"找到程序在: {found_path}")
                        else:
                            self.log(f"警告: 在PATH中找不到程序: {cleaned_part}")
                            # 检查常见位置
                            common_dirs = [
                                r"C:\Windows\System32",
                                r"C:\Windows",
                                r"C:\Program Files",
                                r"C:\Program Files (x86)",
                            ]
                            for dir_path in common_dirs:
                                check_path = os.path.join(dir_path, cleaned_part)
                                if os.path.exists(check_path):
                                    self.log(f"找到程序在常见位置: {check_path}")
                                    # 替换命令中的程序名为完整路径
                                    command = command.replace(cleaned_part, f'"{check_path}"', 1)
                                    self.log(f"已调整命令: {command}")
                                    break
                    except Exception as e:
                        self.log(f"检查程序路径时出错: {str(e)}")
            
        # 为特定命令使用更健壮的错误处理
        try:
            # 检测是否有包含空格的路径（尤其是Program Files）
            has_program_files = "Program Files" in command or "Program Files (x86)" in command
            has_npm_node = any(x in command for x in ["npm", "node"])
            self.log(f"路径检测: Program Files={has_program_files}, npm/node={has_npm_node}")
            
            if has_program_files and has_npm_node:
                # 对于带Program Files路径的npm/node命令，使用cmd /c来执行
                cmd_command = f'cmd /c {command}'
                self.log(f"命令中包含空格路径，使用cmd /c执行: {cmd_command}")
                
                process = subprocess.Popen(
                    cmd_command,
                    shell=True,  # 使用shell=True + cmd /c处理带空格的路径问题
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding=preferred_enc,
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
            else:
                # 其他命令仍然使用标准的、更安全的shell=False模式
                self.log(f"使用shell=False模式执行命令")
                cmd_args = shlex.split(command)
                self.log(f"执行 (shlex 解析后): {cmd_args}")
                
                process = subprocess.Popen(
                    cmd_args,
                    shell=False,  # 设置为False，更安全
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding=preferred_enc,
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
            
            # 记录命令输出
            for line in process.stdout:
                self.log(line.strip())
                
            process.wait()
            if process.returncode != 0:
                error = process.stderr.read()
                self.log(f"错误: {error}")
                
                # 添加更多调试信息以帮助诊断
                self.log(f"命令返回代码: {process.returncode}")
                if 'msiexec' in command.lower():
                    self.log("MSI 安装失败: 请尝试手动运行以获取更多信息，或确保以管理员身份运行")
                    
                    # 尝试使用绝对路径
                    if not command.startswith('"C:\\Windows\\System32\\msiexec.exe"'):
                        msiexec_path = r"C:\Windows\System32\msiexec.exe"
                        if os.path.exists(msiexec_path):
                            new_cmd = command.replace("msiexec", f'"{msiexec_path}"')
                            self.log(f"尝试使用绝对路径重新执行: {new_cmd}")
                            return self.run_command(new_cmd)
                
                raise Exception(f"命令执行失败: {command}")
                
        except FileNotFoundError as e:
            self.log(f"执行命令时出现文件未找到错误: {str(e)}")
            self.log(f"命令: {command}")
            self.log(f"异常类型: {type(e).__name__}")
            self.log(f"堆栈跟踪: {traceback.format_exc()}")
            
            # 尝试检查文件是否存在
            exe_name = command.split()[0].strip('"\'')
            if not os.path.exists(exe_name) and not exe_name.lower() in ["python", "pip", "npm", "msiexec"]:
                self.log(f"找不到可执行文件: {exe_name}")
                
            raise Exception(f"命令执行异常: {command}")
                
        except Exception as e:
            self.log(f"执行命令时出现异常: {str(e)}")
            self.log(f"命令: {command}")
            self.log(f"异常类型: {type(e).__name__}")
            self.log(f"堆栈跟踪: {traceback.format_exc()}")
            raise Exception(f"命令执行异常: {command}")
            
    def uninstall_all(self):
        """卸载所有组件"""
        result = messagebox.askquestion("确认卸载", "确定要卸载所有大麦助手组件吗？\n\n这将卸载：\n- Python 3.11\n- Node.js 18\n- Appium Server 3.1.0\n- Android Platform Tools\n\n您的个人数据不会被删除。", icon='warning')
        if result != 'yes':
            self.log("卸载已取消")
            return
            
        self.log("开始卸载组件...")
        self.install_btn.config(state=tk.DISABLED)
        self.uninstall_btn.config(state=tk.DISABLED)
        self.check_btn.config(state=tk.DISABLED)
        
        # 创建卸载线程
        self.install_thread = threading.Thread(target=self._uninstall_all_thread, daemon=True)
        self.install_thread.start()
    
    def _uninstall_all_thread(self):
        """卸载线程"""
        try:
            # 优先卸载 Appium Server
            appium_component_index = None
            for i, component in enumerate(self.components):
                if "Appium" in component["name"] and component["status"] == "已安装":
                    appium_component_index = i
                    break
            
            if appium_component_index is not None:
                self.log(f"优先卸载 Appium Server...")
                try:
                    self.uninstall_component(appium_component_index)
                    self.update_component_status(appium_component_index, "未安装")
                    self.log(f"'{self.components[appium_component_index]['name']}' 已卸载")
                except Exception as e:
                    self.log(f"卸载 Appium 失败: {str(e)}")
            
            # 然后逆序卸载其他组件
            for i in range(len(self.components) - 1, -1, -1):  # 逆序卸载
                component = self.components[i]
                
                # 跳过已经卸载的 Appium
                if "Appium" in component["name"]:
                    continue
                    
                if component["status"] != "已安装":
                    self.log(f"跳过未安装的 '{component['name']}'")
                    continue
                
                self.log(f"正在卸载 '{component['name']}'...")
                
                try:
                    self.uninstall_component(i)
                    self.update_component_status(i, "未安装")
                    self.log(f"'{component['name']}' 已卸载")
                except Exception as e:
                    self.log(f"卸载 '{component['name']}' 失败: {str(e)}")
            
            # 清理残留文件
            self.log("清理残留文件...")
            android_tools_paths = ["C:/platform-tools", "C:/Android/platform-tools"]
            for path in android_tools_paths:
                if os.path.exists(path):
                    try:
                        shutil.rmtree(path)
                        self.log(f"已删除 {path}")
                    except Exception as e:
                        self.log(f"删除 {path} 失败: {str(e)}")
            
            self.log("卸载完成")
            messagebox.showinfo("完成", "大麦助手组件已卸载")
            
        except Exception as e:
            self.log(f"卸载过程中发生错误: {str(e)}")
            self.log(f"堆栈跟踪: {traceback.format_exc()}")
            messagebox.showerror("错误", f"卸载过程中发生错误: {e}")
        finally:
            self.install_btn.config(state=tk.NORMAL)
            self.uninstall_btn.config(state=tk.NORMAL)
            self.check_btn.config(state=tk.NORMAL)
            
    def uninstall_component(self, index):
        """卸载指定组件"""
        component = self.components[index]
        
        if component["type"] == "exe" and "Python" in component["name"]:
            # 卸载Python
            uninstall_cmd = f'"{os.environ["SYSTEMDRIVE"]}\\Python311\\python.exe" -m ensurepip && "{os.environ["SYSTEMDRIVE"]}\\Python311\\Scripts\\pip.exe" install uninstall-python'
            try:
                self.run_command(uninstall_cmd)
                self.log("已安装Python卸载工具")
                self.run_command(f'"{os.environ["SYSTEMDRIVE"]}\\Python311\\python.exe" -m uninstall_python --company Python')
            except:
                # 如果失败，使用控制面板卸载
                self.log("使用控制面板方式卸载Python")
                self.run_command('wmic product where "name like \'%Python 3.11%\'" call uninstall /nointeractive')
        
        elif component["type"] == "msi" and "Node.js" in component["name"]:
            # 卸载Node.js
            self.log("卸载Node.js")
            self.run_command('wmic product where "name like \'%Node.js%\'" call uninstall /nointeractive')
        
        elif component["type"] == "npm" and "Appium" in component["name"]:
            # 卸载Appium
            self.log("卸载Appium")
            
            # 首先尝试使用找到的 npm 路径
            npm_path = self.find_program("npm.cmd")
            if npm_path:
                self.log(f"使用npm路径卸载Appium: {npm_path}")
                cmd = f'"{npm_path}" uninstall -g appium'
            else:
                # 尝试在默认安装位置找
                possible_paths = [
                    r"C:\Program Files\nodejs\npm.cmd",
                    r"C:\nodejs\npm.cmd",
                    os.path.expandvars(r"%ProgramFiles%\nodejs\npm.cmd"),
                    os.path.expandvars(r"%ProgramFiles(x86)%\nodejs\npm.cmd"),
                    os.path.expandvars(r"%APPDATA%\npm\npm.cmd")
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        self.log(f"使用找到的npm卸载Appium: {path}")
                        cmd = f'"{path}" uninstall -g appium'
                        break
                else:
                    self.log("无法找到npm，使用默认命令")
                    cmd = "npm uninstall -g appium"
            
            self.run_command(cmd)
        
        elif component["type"] == "pip":
            # 卸载pip包
            pip_packages = []
            with open(resource_path("resources/requirements.txt"), 'r', encoding='utf-8') as f:
                for line in f:
                    package = line.split('==')[0].strip()
                    if package:
                        pip_packages.append(package)
            
            if pip_packages:
                packages_str = " ".join(pip_packages)
                self.log(f"卸载Python依赖: {packages_str}")
                pip_cmd = f"pip uninstall -y {packages_str}"
                self.run_command(pip_cmd)

    def add_to_user_path(self, new_path):
        """将目录永久添加到用户PATH环境变量"""
        try:
            import winreg
            self.log(f"尝试将 {new_path} 添加到用户PATH")
            
            # 打开用户环境变量注册表键
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                try:
                    # 读取现有的PATH值
                    current_path, _ = winreg.QueryValueEx(key, 'Path')
                except FileNotFoundError:
                    # 如果PATH不存在，则创建一个
                    current_path = ""
                
                # 检查新路径是否已存在
                path_parts = [p.rstrip('\\/') for p in current_path.split(';') if p]
                if new_path.rstrip('\\/') not in path_parts:
                    # 添加新路径
                    new_user_path = f"{current_path};{new_path}" if current_path else new_path
                    winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_user_path)
                    self.log(f"成功将 {new_path} 添加到用户PATH")
                    
                    # 广播消息以通知系统环境变量已更改
                    self.refresh_env_variables()
                else:
                    self.log(f"路径 {new_path} 已存在于用户PATH中")

        except Exception as e:
            self.log(f"添加到用户PATH失败: {str(e)}")
    
    # ========== NPM 全局 bin 目录探测与 PATH 处理（用于 Appium 一致性检查） ==========
    def _get_npm_global_bin_candidates(self):
        """返回可能的 npm 全局 bin 目录列表（按优先级），仅返回存在的目录"""
        candidates = []
        try:
            # 优先使用 npm 配置前缀
            result = subprocess.run(
                ['npm', 'config', 'get', 'prefix'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                prefix = result.stdout.strip()
                if prefix:
                    # 常见情况下 prefix 已经是 %APPDATA%\\npm；否则尝试拼接 \\npm
                    candidates.append(prefix)
                    candidates.append(os.path.join(prefix, 'npm'))
        except Exception as e:
            self.log(f"npm prefix 探测失败: {e}")
        
        # 常见默认位置（当前用户）
        candidates.extend([
            os.path.expandvars(r"%APPDATA%\npm"),
            os.path.expanduser(r"~\AppData\Roaming\npm"),
        ])
        
        # 常见系统位置
        candidates.extend([
            r"C:\Program Files\nodejs",
            r"C:\Program Files (x86)\nodejs",
            r"C:\nodejs",
        ])
        
        # 管理员账户的常见位置（用于跨权限安装导致的路径不一致）
        candidates.append(r"C:\Users\Administrator\AppData\Roaming\npm")
        
        # 去重并仅保留存在的目录
        seen = set()
        existing = []
        for p in candidates:
            if not p:
                continue
            normp = os.path.normpath(p)
            if normp.lower() in seen:
                continue
            seen.add(normp.lower())
            if os.path.isdir(normp):
                existing.append(normp)
        return existing
    
    def _ensure_npm_bin_in_process_path(self):
        """将 npm 全局 bin 目录加入当前进程 PATH（不持久化），并记录日志"""
        try:
            current_path = os.environ.get('PATH', '')
            added = []
            for p in self._get_npm_global_bin_candidates():
                if p not in current_path:
                    os.environ['PATH'] = f"{p};{current_path}"
                    current_path = os.environ['PATH']
                    added.append(p)
            if added:
                self.log(f"🔧 已将以下 npm bin 目录加入当前进程 PATH: {added}")
            else:
                self.log("🔧 未发现需要加入的 npm bin 目录或已在 PATH 中")
        except Exception as e:
            self.log(f"⚠️ 临时加入 npm bin 到 PATH 失败: {e}")
    
    def _ensure_npm_bin_in_user_path(self):
        """将首个检测到的 npm 全局 bin 目录持久加入用户 PATH"""
        try:
            candidates = self._get_npm_global_bin_candidates()
            if not candidates:
                self.log("⚠️ 未检测到任何 npm 全局 bin 目录，跳过持久化 PATH 写入")
                return
            target = candidates[0]
            self.log(f"尝试持久加入 npm bin 到用户 PATH: {target}")
            self.add_to_user_path(target)
        except Exception as e:
            self.log(f"⚠️ 将 npm bin 持久加入用户 PATH 失败: {e}")
    
    def install_pyarmor_runtime(self):
        """安装PyArmor运行时库"""
        try:
            # 获取项目根目录 - 使用当前工作目录作为项目目录
            project_dir = os.getcwd()
            
            self.log("\n===== 开始安装 PyArmor 运行时库 =====")
            self.log(f"项目目录: {project_dir}")
            
            # 检查项目目录权限
            if not os.path.exists(project_dir):
                self.log(f"警告: 项目目录不存在: {project_dir}")
                return False
                
            # 检查写入权限
            try:
                test_file = os.path.join(project_dir, "test_write_permission.tmp")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                self.log(f"警告: 项目目录没有写入权限: {e}")
                self.log("PyArmor 运行时安装被跳过，这不会影响主要功能")
                return True  # 返回 True，因为这不应该阻止安装
            
            # 创建 PyArmor 运行时目录结构
            runtime_dir = os.path.join(project_dir, "damai", "pyarmor_runtime_000000")
            try:
                if not os.path.exists(runtime_dir):
                    os.makedirs(runtime_dir, exist_ok=True)
                    self.log(f"创建目录: {runtime_dir}")
            except Exception as e:
                self.log(f"无法创建 PyArmor 目录: {e}")
                self.log("PyArmor 运行时安装被跳过，这不会影响主要功能")
                return True  # 返回 True，因为这不应该阻止安装
            
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

if __name__ == "__main__":
    app = DamaiInstaller()
    app.mainloop()