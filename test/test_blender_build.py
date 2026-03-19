#!/usr/bin/env python3
"""
自动启动Blender并调用ACA Builder插件中的build()函数

用法:
    python3 test_blender_build.py                    # 使用第一个模板
    python3 test_blender_build.py <template_name>    # 使用指定模板
    python3 test_blender_build.py --list             # 列出所有可用模板
    python3 test_blender_build.py --vscode           # 通过VSCode启动
    python3 test_blender_build.py --batch            # 批量运行所有模板并生成报告
    python3 test_blender_build.py --batch --start 5  # 从第5个模板开始批量运行

从template.xml中获取模板名称，只使用<templates><template>中的template_name
"""

import os
import sys
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import tempfile
from datetime import datetime
import threading
import time

BLENDER_APP_NAME = 'Blender 5.0.1'

class SleepPreventer:
    """
    防止电脑休眠的上下文管理器
    支持Windows和macOS
    """
    
    def __init__(self):
        self.process = None
        self.platform = sys.platform
    
    def __enter__(self):
        if self.platform == 'darwin':
            self.process = subprocess.Popen(['caffeinate', '-i', '-s'])
        elif self.platform == 'win32':
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED
                )
            except Exception as e:
                print(f"警告: 无法设置防止休眠: {e}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        elif self.platform == 'win32':
            import ctypes
            ES_CONTINUOUS = 0x80000000
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            except Exception:
                pass


def format_duration(seconds: float) -> str:
    """
    将秒数格式化为中文时间显示
    不超过1分钟：显示"xx秒"
    不超过1小时：显示"xx分xx秒"
    超过1小时：显示"xx小时xx分xx秒"
    """
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    if hours > 0:
        return f"{hours}小时{minutes}分{secs}秒"
    elif minutes > 0:
        return f"{minutes}分{secs}秒"
    else:
        return f"{secs}秒"


def find_blender_executable() -> str:
    """
    查找Blender可执行文件路径
    支持macOS和Windows
    """
    if sys.platform == 'darwin':
        possible_paths = [
            f'/Applications/{BLENDER_APP_NAME}.app/Contents/MacOS/Blender',
            f'/Applications/{BLENDER_APP_NAME}/{BLENDER_APP_NAME.lower()}.app/Contents/MacOS/{BLENDER_APP_NAME.lower()}',
            f'/Applications/{BLENDER_APP_NAME} Foundation/{BLENDER_APP_NAME}/{BLENDER_APP_NAME}.app/Contents/MacOS/Blender',
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        try:
            result = subprocess.run(
                ['mdfind', 'kMDItemCFBundleIdentifier == "org.blenderfoundation.blender"'],
                capture_output=True, text=True
            )
            if result.stdout.strip():
                app_path = result.stdout.strip().split('\n')[0]
                blender_path = os.path.join(app_path, 'Contents/MacOS/Blender')
                if os.path.exists(blender_path):
                    return blender_path
        except Exception:
            pass
    elif sys.platform == 'win32':
        possible_paths = [
            rf'C:\Program Files\{BLENDER_APP_NAME} Foundation\{BLENDER_APP_NAME} 4.2\blender.exe',
            rf'C:\Program Files\{BLENDER_APP_NAME} Foundation\{BLENDER_APP_NAME} 4.1\blender.exe',
            rf'C:\Program Files\{BLENDER_APP_NAME} Foundation\{BLENDER_APP_NAME} 4.0\blender.exe',
            rf'C:\Program Files\{BLENDER_APP_NAME} Foundation\{BLENDER_APP_NAME}\blender.exe',
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        try:
            result = subprocess.run(['where', 'blender'], capture_output=True, text=True)
            if result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
        except Exception:
            pass
    
    return 'blender'


def get_system_info() -> dict:
    """
    获取系统信息：操作系统、CPU、内存、显卡
    """
    info = {}
    
    if sys.platform == 'darwin':
        import platform
        info['os'] = f"macOS {platform.mac_ver()[0]}"
        
        try:
            result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True)
            info['cpu'] = result.stdout.strip() if result.returncode == 0 else "未知"
        except Exception:
            info['cpu'] = "未知"
        
        try:
            result = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True)
            if result.returncode == 0:
                mem_bytes = int(result.stdout.strip())
                mem_gb = mem_bytes / (1024 ** 3)
                info['memory'] = f"{mem_gb:.1f} GB"
            else:
                info['memory'] = "未知"
        except Exception:
            info['memory'] = "未知"
        
        try:
            result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            gpu_lines = [l.strip() for l in lines if 'Chipset Model:' in l or 'VRAM' in l]
            if gpu_lines:
                info['gpu'] = gpu_lines[0].replace('Chipset Model: ', '').replace('VRAM (Total): ', '')
            else:
                info['gpu'] = "未知"
        except Exception:
            info['gpu'] = "未知"
            
    elif sys.platform == 'win32':
        import platform
        info['os'] = f"Windows {platform.win32_ver()[1]}"
        
        try:
            result = subprocess.run(['wmic', 'cpu', 'get', 'name'], capture_output=True, text=True, shell=True)
            lines = [l.strip() for l in result.stdout.split('\n') if l.strip()]
            info['cpu'] = lines[1] if len(lines) > 1 else "未知"
        except Exception:
            info['cpu'] = "未知"
        
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            c_ulonglong = ctypes.c_ulonglong
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ('dwLength', ctypes.c_ulong),
                    ('dwMemoryLoad', ctypes.c_ulong),
                    ('ullTotalPhys', c_ulonglong),
                    ('ullAvailPhys', c_ulonglong),
                    ('ullTotalPageFile', c_ulonglong),
                    ('ullAvailPageFile', c_ulonglong),
                    ('ullTotalVirtual', c_ulonglong),
                    ('ullAvailVirtual', c_ulonglong),
                    ('ullAvailExtendedVirtual', c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            mem_gb = stat.ullTotalPhys / (1024 ** 3)
            info['memory'] = f"{mem_gb:.1f} GB"
        except Exception:
            info['memory'] = "未知"
        
        try:
            result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name'], capture_output=True, text=True, shell=True)
            lines = [l.strip() for l in result.stdout.split('\n') if l.strip()]
            info['gpu'] = lines[1] if len(lines) > 1 else "未知"
        except Exception:
            info['gpu'] = "未知"
    else:
        info['os'] = sys.platform
        info['cpu'] = "未知"
        info['memory'] = "未知"
        info['gpu'] = "未知"
    
    try:
        blender_path = find_blender_executable()
        result = subprocess.run([blender_path, '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            first_line = result.stdout.split('\n')[0]
            info['blender_version'] = first_line.replace('Blender', '').strip()
        else:
            info['blender_version'] = "未知"
    except Exception:
        info['blender_version'] = "未知"
    
    return info


def get_output_base_path() -> Path:
    """
    获取测试输出基础目录
    macOS: iCloud云盘目录 ~/Library/Mobile Documents/com~apple~CloudDocs/ACA Test
    Windows: 桌面目录 ~/Desktop/ACA Builder Test Output
    """
    if sys.platform == 'darwin':
        icloud_path = Path.home() / 'Library' / 'Mobile Documents' / 'com~apple~CloudDocs'
        return icloud_path / 'ACA Test'
    elif sys.platform == 'win32':
        return Path.home() / 'Desktop' / 'ACA Test'
    else:
        return Path.home() / 'Desktop' / 'ACA Test'


def get_template_names(xml_path: str) -> list[str]:
    """
    从template.xml中获取所有顶层的template_name
    只获取<templates><template>中的template_name
    不获取<templates><template><template>中的template_name
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    template_names = []
    templates = root.find('templates')
    if templates is None:
        templates = root
    
    for template in templates.findall('template'):
        template_name_elem = template.find('template_name')
        if template_name_elem is not None and template_name_elem.text:
            template_names.append(template_name_elem.text)
    
    return template_names


def generate_blender_script(addon_path: str, template_name: str, screenshot_path: str) -> str:
    """
    生成在Blender中执行的Python脚本
    包含截屏功能
    """
    script = f'''
import bpy
import sys
import os
from datetime import datetime

# 添加插件父目录到sys.path
addon_parent = r"{os.path.dirname(addon_path)}"
if addon_parent not in sys.path:
    sys.path.insert(0, addon_parent)

def take_screenshot(output_path: str) -> bool:
    """截取当前Blender 3D视口的屏幕截图"""
    try:
        # 查找3D视图区域
        target_area_type = 'VIEW_3D'
        area = next((a for a in bpy.context.screen.areas if a.type == target_area_type), None)
        
        if area:
            # 找到3D视图，使用 opengl 渲染截图
            with bpy.context.temp_override(area=area):
                # 窗口截图的方式
                # result = bpy.ops.screen.screenshot_area(filepath=output_path)
                # 通过OpenGL渲染截图
                bpy.context.scene.render.filepath = output_path
                result = bpy.ops.render.opengl(write_still=True)
            print(f"截图保存到: {{output_path}}")
            return True
        
        # 如果没有找到3D视图，使用全屏截图
        result = bpy.ops.screen.screenshot(filepath=output_path)
        print(f"全屏截图保存到: {{output_path}}")
        return True
    except Exception as e:
        print(f"截图失败: {{e}}")
        return False

def execute_build():
    """延迟执行build函数，确保Blender完全启动"""
    success = False
    error_msg = ""
    
    try:
        # 确保插件已加载
        addon_name = "ACA Builder"
        
        # 检查插件是否已启用
        if addon_name not in bpy.context.preferences.addons:
            print(f"正在启用插件: {{addon_name}}")
            bpy.ops.preferences.addon_enable(module=addon_name)
            print(f"插件 {{addon_name}} 已启用")
        
        print(f"开始执行build函数，模板: {template_name}")
        result = bpy.ops.aca.add_newbuilding(templateName="{template_name}")
        print(f"Build完成，结果: {{result}}")
        
        if result == {'FINISHED'}:
            success = True
        else:
            error_msg = f"Build返回非FINISHED状态: {{result}}"
            
    except Exception as e:
        error_msg = str(e)
        print(f"执行build时发生错误: {{e}}")
        import traceback
        traceback.print_exc()
    
    # 截图
    take_screenshot(r"{screenshot_path}")
    
    # 延迟退出Blender，确保截图已保存
    def quit_blender():
        bpy.ops.wm.quit_blender()
    
    bpy.app.timers.register(quit_blender, first_interval=1.0)

# 使用定时器延迟执行，确保Blender完全启动
bpy.app.timers.register(execute_build, first_interval=2.0)
'''
    return script


def launch_via_vscode(template_name: str, addon_path: str):
    """
    通过VSCode的命令启动Blender
    """
    blender_script = generate_blender_script(addon_path, template_name, "", "")
    temp_script = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8')
    temp_script.write(blender_script)
    temp_script.close()
    
    try:
        vscode_cmd = [
            'code',
            '--command', 'blender.start',
        ]
        
        print(f"通过VSCode启动Blender...")
        print(f"注意: 请在VSCode中配置Blender扩展路径")
        print(f"临时脚本路径: {temp_script.name}")
        
        subprocess.run(vscode_cmd)
    finally:
        pass


def run_with_output_timeout(cmd: list, timeout_seconds: int = 600) -> tuple:
    """
    运行命令并监测输出，如果指定时间内没有新输出则判定超时
    返回: (return_code, stdout, stderr, timed_out)
    """
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    last_output_time = time.time()
    stdout_lines = []
    stderr_lines = []
    timed_out = False
    
    def read_output(pipe, lines_list, is_stdout):
        nonlocal last_output_time
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    lines_list.append(line)
                    last_output_time = time.time()
                    if is_stdout:
                        print(line, end='')
        except:
            pass
    
    stdout_thread = threading.Thread(target=read_output, args=(process.stdout, stdout_lines, True))
    stderr_thread = threading.Thread(target=read_output, args=(process.stderr, stderr_lines, False))
    
    stdout_thread.daemon = True
    stderr_thread.daemon = True
    
    stdout_thread.start()
    stderr_thread.start()
    
    while process.poll() is None:
        current_time = time.time()
        if current_time - last_output_time > timeout_seconds:
            print(f"\n检测到输出超时（{timeout_seconds}秒无新输出），正在终止进程...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            timed_out = True
            break
        time.sleep(0.5)
    
    stdout_thread.join(timeout=2)
    stderr_thread.join(timeout=2)
    
    return (
        process.returncode,
        ''.join(stdout_lines),
        ''.join(stderr_lines),
        timed_out
    )


def launch_single(template_name: str, addon_path: str, output_dir: Path) -> dict:
    """
    启动Blender并执行单个模板
    返回运行结果
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    safe_name = template_name.replace('/', '_').replace('\\', '_')
    screenshot_path = output_dir / f"{safe_name}.png"
    
    blender_script = generate_blender_script(
        str(addon_path), 
        template_name, 
        str(screenshot_path)
    )
    
    script_dir = Path(__file__).parent.resolve()
    temp_script_path = script_dir / '_temp_build_script.py'
    with open(temp_script_path, 'w', encoding='utf-8') as f:
        f.write(blender_script)
    
    blender_exe = find_blender_executable()
    print(f"\n{'='*60}")
    print(f"Blender路径: {blender_exe}")
    print(f"模板名称: {template_name}")
    print(f"截图路径: {screenshot_path}")
    
    cmd = [
        blender_exe,
        '--python', str(temp_script_path),
    ]
    
    start_time = datetime.now()
    
    try:
        return_code, stdout, stderr, timed_out = run_with_output_timeout(cmd, timeout_seconds=600)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        report = {
            "template_name": template_name,
            "success": False,
            "start_time": start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "end_time": end_time.strftime('%Y-%m-%d %H:%M:%S'),
            "timestamp": datetime.now().isoformat()
        }
        
        report['duration_seconds'] = duration
        report['screenshot_exists'] = screenshot_path.exists()
        report['blender_exit_code'] = return_code
        
        if timed_out:
            report['error'] = f"输出超时（超过10分钟无新输出）"
        elif return_code != 0:
            report['error'] = f"Blender退出码: {return_code}"
        else:
            report['success'] = True
        
        status = "✅ 成功" if report['success'] else "❌ 失败"
        print(f"状态: {status}")
        print(f"耗时: {format_duration(duration)}")
        
        return report
        
    except Exception as e:
        return {
            "template_name": template_name,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
    finally:
        if temp_script_path.exists():
            temp_script_path.unlink()


def launch_directly(template_name: str, addon_path: str, output_dir: Path):
    """
    直接启动Blender并执行脚本（单模板模式）
    """
    with SleepPreventer():
        start_time = datetime.now()
        report = launch_single(template_name, addon_path, output_dir)
        
        reports = [report]
        generate_markdown_report(reports, output_dir / 'test_report.md', start_time, output_dir)
        
        status = "成功" if report['success'] else "失败"
        print(f"\n执行{status}: {template_name}")
        if not report['success'] and report.get('error'):
            print(f"错误: {report['error']}")


def generate_markdown_report(reports: list[dict], output_path: Path, start_time: datetime, output_dir: Path):
    """
    生成Markdown格式的测试报告
    """
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    success_count = sum(1 for r in reports if r.get('success', False))
    fail_count = len(reports) - success_count
    
    system_info = get_system_info()
    
    md_content = f"""# ACA筑韵古建 自动测试报告

<style>
table {{ white-space: nowrap; width: 100%; }}
</style>

## 概述

- **测试时间**: {start_time.strftime('%Y-%m-%d %H:%M:%S')} - {end_time.strftime('%Y-%m-%d %H:%M:%S')}
- **操作系统**: {system_info['os']}
- **电脑型号**: {system_info['cpu']} / {system_info['memory']} / {system_info['gpu']}
- **Blender版本**: {system_info['blender_version']}
- **总耗时**: {format_duration(total_duration)}
- **测试模板数量**: {len(reports)}
- **成功**: {success_count}
- **失败**: {fail_count}
- **成功率**: {success_count/len(reports)*100:.1f}%

## 测试结果详情

| 序号 | 模板名称 | 开始时间 | 结束时间 | 耗时 | 状态 | 截图 | 错误信息 |
|------|----------|----------|----------|------|------|------|----------|
"""
    
    for i, report in enumerate(reports, 1):
        status = "✅" if report.get('success', False) else "❌"
        duration = report.get('duration_seconds', 0)
        duration_formatted = format_duration(duration)
        start_time_str = report.get('start_time', '-')
        end_time_str = report.get('end_time', '-')
        if start_time_str and start_time_str != '-':
            start_time_str = start_time_str.split(' ')[1]
        if end_time_str and end_time_str != '-':
            end_time_str = end_time_str.split(' ')[1]
        
        if report.get('screenshot_exists'):
            safe_name = report['template_name'].replace('/', '_').replace('\\', '_')
            screenshot_rel_path = f"{safe_name}.png"
            screenshot = f'<a href="{screenshot_rel_path}"><img src="{screenshot_rel_path}" width="100"></a>'
        else:
            screenshot = "-"
        
        error = report.get('error', '')
        if error:
            error = error.replace('|', '\\|')[:50]
        
        md_content += f"| {i} | {report['template_name']} | {start_time_str} | {end_time_str} | {duration_formatted} | {status} | {screenshot} | {error} |\n"
    
    failed_reports = [r for r in reports if not r.get('success', False)]
    if failed_reports:
        md_content += "\n## 失败详情\n\n"
        for report in failed_reports:
            md_content += f"### {report['template_name']}\n\n"
            md_content += f"- **错误信息**: {report.get('error', '未知错误')}\n"
            md_content += f"- **时间**: {report.get('timestamp', '未知')}\n"
            if report.get('duration_seconds'):
                md_content += f"- **耗时**: {format_duration(report.get('duration_seconds'))}\n"
            md_content += "\n"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"\n报告已生成: {output_path}")


def run_batch(template_names: list[str], addon_path: str, start_index: int = 0):
    """
    批量运行所有模板并生成报告
    """
    with SleepPreventer():
        start_time = datetime.now()
        output_dir_name = start_time.strftime('%y%m%d %H%M')
        output_dir = get_output_base_path() / output_dir_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        reports = []
        
        print(f"\n{'='*60}")
        print(f"开始批量测试")
        print(f"模板数量: {len(template_names)}")
        print(f"起始索引: {start_index}")
        print(f"输出目录: {output_dir}")
        print(f"防止休眠: 已启用")
        print(f"{'='*60}\n")
        
        for i, template_name in enumerate(template_names):
            if i < start_index:
                print(f"跳过模板 {i+1}: {template_name}")
                continue
            
            print(f"\n[{i+1}/{len(template_names)}] 正在测试: {template_name}")
            
            report = launch_single(template_name, addon_path, output_dir)
            reports.append(report)
            
            generate_markdown_report(reports, output_dir / 'test_report.md', start_time, output_dir)
        
        generate_markdown_report(reports, output_dir / 'test_report.md', start_time, output_dir)
        
        success_count = sum(1 for r in reports if r.get('success', False))
        fail_count = len(reports) - success_count
        
        print(f"\n{'='*60}")
        print(f"批量测试完成")
        print(f"成功: {success_count}, 失败: {fail_count}")
        print(f"报告路径: {output_dir / 'test_report.md'}")
        print(f"{'='*60}\n")


def main():
    script_dir = Path(__file__).parent.resolve()
    addon_path = script_dir.parent
    template_xml_path = addon_path / 'template' / 'template.xml'
    
    if not template_xml_path.exists():
        print(f"错误: 找不到template.xml文件: {template_xml_path}")
        sys.exit(1)
    
    template_names = get_template_names(str(template_xml_path))
    if not template_names:
        print("错误: 无法从template.xml中找到模板名称")
        sys.exit(1)
    
    if '--list' in sys.argv or '-l' in sys.argv:
        print("可用的模板名称:")
        for i, name in enumerate(template_names, 1):
            print(f"  {i}. {name}")
        return
    
    if '--batch' in sys.argv or '-b' in sys.argv:
        start_index = 0
        for i, arg in enumerate(sys.argv):
            if arg == '--start' and i + 1 < len(sys.argv):
                try:
                    start_index = int(sys.argv[i + 1]) - 1
                except ValueError:
                    print("错误: --start 参数需要提供数字")
                    sys.exit(1)
        
        run_batch(template_names, str(addon_path), start_index)
        return
    
    use_vscode = '--vscode' in sys.argv or '-v' in sys.argv
    
    template_name = None
    for arg in sys.argv[1:]:
        if not arg.startswith('-'):
            template_name = arg
            break
    
    if template_name is None:
        template_name = template_names[0]
        print(f"使用默认模板: {template_name}")
    
    if template_name not in template_names:
        print(f"警告: 模板名称 '{template_name}' 不在可用列表中")
        print(f"可用的模板: {template_names}")
        response = input("是否继续? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    start_time = datetime.now()
    output_dir_name = start_time.strftime('%y%m%d %H%M')
    output_dir = get_output_base_path() / output_dir_name
    
    if use_vscode:
        launch_via_vscode(template_name, str(addon_path))
    else:
        launch_directly(template_name, str(addon_path), output_dir)


if __name__ == '__main__':
    main()
