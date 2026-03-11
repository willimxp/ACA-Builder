#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACA Builder MO文件编译工具
用于编译PO文件生成MO文件
"""

import os
import sys
import subprocess
import argparse

def get_default_paths():
    """获取默认的PO和MO文件路径"""
    skill_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(skill_dir)))
    po_path = os.path.join(project_root, 'locale', 'en_US', 'LC_MESSAGES', 'aca_builder.po')
    mo_path = os.path.join(project_root, 'locale', 'en_US', 'LC_MESSAGES', 'aca_builder.mo')
    return po_path, mo_path

def compile_mo_file(po_file_path: str, mo_file_path: str) -> bool:
    """编译MO文件"""
    try:
        subprocess.run(['msgfmt', po_file_path, '-o', mo_file_path], check=True, capture_output=True)
        print(f"成功编译MO文件: {mo_file_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"编译MO文件失败: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except FileNotFoundError:
        print("警告: msgfmt未找到，尝试使用Python gettext模块")
        try:
            import gettext
            po = gettext.GNUTranslations(open(po_file_path, 'rb'))
            with open(mo_file_path, 'wb') as f:
                po.write(f)
            print(f"成功编译MO文件(使用Python): {mo_file_path}")
            return True
        except Exception as e2:
            print(f"使用Python gettext模块编译失败: {e2}")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ACA Builder MO文件编译工具')
    parser.add_argument('po_file', nargs='?', help='PO文件路径（可选，默认使用aca_builder.po）')
    parser.add_argument('mo_file', nargs='?', help='MO文件输出路径（可选，默认使用aca_builder.mo）')
    
    args = parser.parse_args()
    
    if args.po_file and args.mo_file:
        po_path = args.po_file
        mo_path = args.mo_file
    else:
        po_path, mo_path = get_default_paths()
        print(f"使用默认路径: PO={po_path}, MO={mo_path}")
    
    success = compile_mo_file(po_path, mo_path)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
