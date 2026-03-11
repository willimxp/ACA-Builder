#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新PO文件中的翻译条目并编译MO文件
用法: python3 update_translations.py '{"原文1": "译文1", "原文2": "译文2"}'
"""

import os
import sys
import json
import subprocess
import re
from typing import Dict

def get_po_file_path():
    skill_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(skill_dir)))
    return os.path.join(project_root, 'locale', 'en_US', 'LC_MESSAGES', 'aca_builder.po')

def get_mo_file_path():
    skill_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(skill_dir)))
    return os.path.join(project_root, 'locale', 'en_US', 'LC_MESSAGES', 'aca_builder.mo')

def compile_mo():
    """编译MO文件"""
    po_path = get_po_file_path()
    mo_path = get_mo_file_path()
    
    try:
        subprocess.run(['msgfmt', po_path, '-o', mo_path], check=True, capture_output=True)
        print(f"MO文件编译成功: {mo_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"msgfmt编译失败: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except FileNotFoundError:
        print("警告: msgfmt未找到，尝试使用Python gettext模块")
        try:
            import gettext
            po = gettext.GNUTranslations(open(po_path, 'rb'))
            with open(mo_path, 'wb') as f:
                po.write(f)
            print(f"MO文件编译成功(使用Python): {mo_path}")
            return True
        except Exception as e:
            print(f"Python gettext编译失败: {e}")
            return False

def add_entries_to_po(entries: Dict[str, str], source_info: Dict[str, Dict]) -> bool:
    """将新的翻译条目添加到PO文件"""
    po_path = get_po_file_path()
    
    try:
        if os.path.exists(po_path):
            with open(po_path, 'r', encoding='utf-8') as f:
                po_content = f.read()
        else:
            po_content = '''msgid ""
msgstr ""
"Project-Id-Version: ACA Builder\\n"
"Report-Msgid-Bugs-To: \\n"
"POT-Creation-Date: 2026-03-11\\n"
"PO-Revision-Date: 2026-03-11\\n"
"Last-Translator: \\n"
"Language-Team: \\n"
"Language: en_US\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"

'''
        
        existing_msgids = set()
        msgid_pattern = re.compile(r'msgid "(.*?)"')
        for match in msgid_pattern.finditer(po_content):
            existing_msgids.add(match.group(1))
        
        new_entries = []
        for msgid, translation in entries.items():
            if msgid and msgid not in existing_msgids:
                source = source_info.get(msgid, {})
                file_name = source.get("file", "unknown")
                line_num = source.get("line", 1)
                entry = f"#: {file_name}:{line_num}\n"
                entry += f"msgid \"{msgid}\"\n"
                if translation:
                    entry += f"msgstr \"{translation}\"\n\n"
                else:
                    entry += f"msgstr \"fuzzy\"\n\n"
                new_entries.append(entry)
        
        if new_entries:
            po_content += ''.join(new_entries)
            with open(po_path, 'w', encoding='utf-8') as f:
                f.write(po_content)
            print(f"已添加 {len(new_entries)} 个新条目到PO文件")
        
        return True
    except Exception as e:
        print(f"添加条目到PO文件时出错: {e}")
        return False

def get_translations_json_path():
    skill_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(skill_dir)))
    return os.path.join(project_root, 'locale', 'en_US', 'LC_MESSAGES', 'translations_to_translate.json')

def main():
    if len(sys.argv) < 2:
        print("用法: python3 update_translations.py '{\"原文1\": \"译文1\", \"原文2\": \"译文2\"}'")
        print("或:   python3 update_translations.py translations_to_translate.json")
        sys.exit(1)
    
    json_path = sys.argv[1]
    translations = None
    temp_file_path = None
    
    if os.path.isfile(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            temp_file_path = json_path
            print(f"从文件读取翻译: {json_path}")
            
            if isinstance(data, dict) and "entries" in data:
                entries = data["entries"]
                translations = {msgid: info.get("translation", "") for msgid, info in entries.items()}
                source_info = {msgid: {"file": info.get("file", "unknown"), "line": info.get("line", 1)} for msgid, info in entries.items()}
            else:
                translations = data
                source_info = {}
        except Exception as e:
            print(f"读取JSON文件错误: {e}")
            sys.exit(1)
    else:
        try:
            translations = json.loads(json_path)
            source_info = {}
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            sys.exit(1)
    
    if not isinstance(translations, dict):
        print("错误: 参数必须是JSON对象格式")
        sys.exit(1)
    
    if add_entries_to_po(translations, source_info):
        compile_mo()
        
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"已删除临时文件: {temp_file_path}")
        
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
