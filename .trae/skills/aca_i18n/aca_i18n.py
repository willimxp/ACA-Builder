#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACA Builder i18n国际化技能
自动处理ACA插件的i18n国际化，包括提取中文文本、代码预处理、自动调用_()翻译函数，生成PO文件、编译MO文件等

调用方式：
python3 "/Volumes/XP.T9/Blender/ACA Builder/.trae/skills/aca_i18n/aca_i18n.py" "/Volumes/XP.T9/Blender/ACA Builder/utils.py"
"""

import os
import re
import subprocess
import json
from typing import List, Tuple, Dict

class ACAI18nSkill:
    def __init__(self):
        skill_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(skill_dir)))
        self.po_file_path = os.path.join(project_root, 'locale', 'en_US', 'LC_MESSAGES', 'aca_builder.po')
        self.mo_file_path = os.path.join(project_root, 'locale', 'en_US', 'LC_MESSAGES', 'aca_builder.mo')
        
    def process_file(self, file_path: str) -> bool:
        """处理单个Python文件"""
        try:
            chinese_texts = self._preprocess_code(file_path)
            
            if not chinese_texts:
                print(f"文件 {file_path} 中没有发现中文文本")
                return True
            
            output_path = self._export_to_json(file_path, chinese_texts)
            if output_path:
                print(f"\n已导出 {len(chinese_texts)} 条待翻译条目到: {output_path}")
                print("请翻译JSON中的内容，然后使用以下命令更新PO文件并编译MO:")
                print(f'python3 "/Volumes/XP.T9/Blender/ACA Builder/.trae/skills/aca_i18n/update_translations.py" "{output_path}"')
            
            return True
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
            return False
    
    def _export_to_json(self, file_path: str, chinese_texts: List[Tuple[int, str]]) -> str:
        """将中文文本导出到JSON文件"""
        skill_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(skill_dir)))
        output_dir = os.path.join(project_root, 'locale', 'en_US', 'LC_MESSAGES')
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, 'translations_to_translate.json')
        
        unique_texts = []
        seen = set()
        for line_num, text in chinese_texts:
            if text not in seen:
                unique_texts.append({"msgid": text, "file": os.path.basename(file_path), "line": line_num})
                seen.add(text)
        
        export_data = {
            "entries": {item["msgid"]: {"translation": "", "file": item["file"], "line": item["line"]} for item in unique_texts}
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        return output_path
    
    def _extract_fuzzy_entries(self) -> List[str]:
        """提取PO文件中标注为'fuzzy'的条目"""
        fuzzy_entries = []
        processed_msgids = set()  # 用于跟踪已经处理过的msgid
        
        with open(self.po_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 检查是否是fuzzy的msgstr
            if line.startswith('msgstr "fuzzy"'):
                # 找到对应的msgid
                j = i - 1
                while j >= 0 and not lines[j].startswith('msgid "'):
                    j -= 1
                
                if j >= 0:
                    msgid_line = lines[j]
                    msgid = msgid_line.split('msgid "')[1].rstrip('"\n')
                    if msgid not in processed_msgids:
                        fuzzy_entries.append(msgid)
                        processed_msgids.add(msgid)
            
            i += 1
        
        return fuzzy_entries
    
    def update_translations(self, translations: Dict[str, str]) -> bool:
        """更新翻译结果并编译MO文件"""
        try:
            # 读取PO文件
            with open(self.po_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                new_lines.append(line)
                
                # 检查是否是fuzzy的msgstr
                if line.startswith('msgstr "fuzzy"'):
                    # 找到对应的msgid
                    j = i - 1
                    while j >= 0 and not lines[j].startswith('msgid "'):
                        j -= 1
                    
                    if j >= 0:
                        msgid_line = lines[j]
                        msgid = msgid_line.split('msgid "')[1].rstrip('"\n')
                        
                        # 检查是否有翻译结果
                        if msgid in translations:
                            # 替换fuzzy为翻译结果
                            new_lines[-1] = f"msgstr \"{translations[msgid]}\"\n"
                
                i += 1
            
            # 写回PO文件
            with open(self.po_file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            # 编译MO文件
            self._compile_mo_file()
            
            print("翻译更新成功！")
            return True
        except Exception as e:
            print(f"更新翻译时出错: {e}")
            return False
    
    def export_translations_json(self, output_path: str = None) -> str:
        """导出待翻译的条目到JSON文件"""
        fuzzy_entries = self._extract_fuzzy_entries()
        
        if not fuzzy_entries:
            print("没有待翻译的条目")
            return None
        
        if output_path is None:
            skill_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(skill_dir)))
            output_path = os.path.join(project_root, 'locale', 'en_US', 'LC_MESSAGES', 'translations_to_translate.json')
        
        translations_dict = {msgid: "" for msgid in fuzzy_entries}
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(translations_dict, f, ensure_ascii=False, indent=2)
        
        print(f"已导出 {len(fuzzy_entries)} 条待翻译条目到: {output_path}")
        print("请填充翻译值后，使用以下命令更新PO文件:")
        print(f'python3 "/Volumes/XP.T9/Blender/ACA Builder/.trae/skills/aca_i18n/update_translations.py" "$(cat {output_path})"')
        
        return output_path
    
    def _preprocess_code(self, file_path: str) -> List[Tuple[int, str]]:
        """预处理代码，提取中文文本并修改format字符串"""
        chinese_texts = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        has_i18n_import = False
        import_line_added = False
        
        # 检查是否已有i18n导入
        for line in lines:
            if 'from' in line and 'i18n' in line and '_' in line:
                has_i18n_import = True
                break
        
        # 计算相对路径
        file_dir = os.path.dirname(file_path)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        try:
            rel_path = os.path.relpath(file_dir, project_root)
        except ValueError:
            # 如果路径不在同一文件系统，使用绝对路径
            rel_path = '.'

        
        # 确定导入方式
        if rel_path == '.':
            import_stmt = 'from .locale.i18n import _\n'
        else:
            # 计算相对导入层级
            levels = rel_path.count(os.sep) + 1
            dots = '.' * levels
            import_stmt = f'from {dots}locale.i18n import _\n'
        
        # 先处理导入语句添加
        if not has_i18n_import:
            # 找到第一个非注释、非空行的位置
            import_pos = 0
            while import_pos < len(lines):
                line = lines[import_pos]
                if not (line.strip().startswith('#') or line.strip() == ''):
                    break
                import_pos += 1
            
            # 在该位置插入导入语句
            new_lines = lines.copy()
            new_lines.insert(import_pos, import_stmt)
            import_line_added = True
        else:
            new_lines = lines.copy()
        
        # 处理每一行
        for i, line in enumerate(new_lines):
            # 跳过注释行
            if line.strip().startswith('#'):
                continue
            
            # 处理f-string
            if 'f"' in line or "f'" in line:
                new_line, found_texts = self._process_fstring(line, i + 1)
                new_lines[i] = new_line
                chinese_texts.extend(found_texts)
            else:
                # 查找普通字符串中的中文
                line_texts = self._extract_chinese_from_string(line, i + 1)
                if line_texts:
                    new_line = self._wrap_chinese_with_translate(line, line_texts)
                    new_lines[i] = new_line
                    chinese_texts.extend(line_texts)
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        return chinese_texts
    
    def _process_fstring(self, line: str, line_num: int) -> Tuple[str, List[Tuple[int, str]]]:
        """处理f-string，转换为%s格式并提取中文"""
        chinese_texts = []
        
        # 匹配f-string
        fstring_pattern = re.compile(r'f(["\'])(.*?)\1')
        match = fstring_pattern.search(line)
        
        if not match:
            return line, chinese_texts
        
        # 检查该行是否已经被_()包裹
        if '_(' in line and match.group(0) in line:
            # 检查是否是 _() 包裹的f-string
            outer_underscore_pattern = re.compile(r'_\(\s*f(["\'])(.*?)\1\s*\)')
            if outer_underscore_pattern.search(line):
                return line, chinese_texts
        
        delimiter = match.group(1)
        content = match.group(2)
        
        # 提取中文文本
        chinese_pattern = re.compile(r'[\u4e00-\u9fa5]+')
        chinese_matches = chinese_pattern.findall(content)
        
        if not chinese_matches:
            return line, chinese_texts
        
        # 处理f-string中的变量和中文
        parts = []
        variables = []
        
        # 拆分f-string内容
        current_pos = 0
        for var_match in re.finditer(r'\{(.*?)\}', content):
            start, end = var_match.span()
            
            # 添加变量前的文本
            if start > current_pos:
                text_before = content[current_pos:start]
                parts.append(text_before)

            
            # 添加变量
            var_name = var_match.group(1)
            parts.append('%s')
            variables.append(var_name)
            
            current_pos = end
        
        # 添加剩余文本
        if current_pos < len(content):
            text_after = content[current_pos:]
            parts.append(text_after)
         
        
        # 构建新的字符串
        new_content = ''.join(parts)
        if variables:
            # 翻译字符串本身，% 格式化操作在 _() 外部
            new_format = f'_("{new_content}") % ({", ".join(variables)})'
        else:
            new_format = f'_("{new_content}")'
        
        # 替换原 f-string
        new_line = line.replace(match.group(0), new_format)
        
        # 提取包含占位符的完整中文文本
        if chinese_pattern.search(new_content):
            chinese_texts.append((line_num, new_content))
        
        return new_line, chinese_texts
    
    def _extract_chinese_from_string(self, line: str, line_num: int) -> List[Tuple[int, str]]:
        """从普通字符串中提取中文"""
        chinese_texts = []

        # 检查该行是否已经被_()包裹
        # 需要匹配 _("xxx") 和 _("xxx" % var) 两种形式
        if '_(' in line:
            # 使用正则匹配完整的 _("xxx") 或 _("xxx" % var) 形式
            # 匹配 _() 包裹的内容，包括字符串和变量
            underscore_wrapper_pattern = re.compile(r'_\s*\(\s*(["\'])(.*?)\1(?:\s*%\s*.*?)?\s*\)')
            
            for match in underscore_wrapper_pattern.finditer(line):
                # 提取 _() 内部的字符串内容（不包括变量部分）
                full_content = match.group(0)
                string_content = match.group(2)  # 只获取引号内的部分
                
                # 检查字符串内容中是否包含中文
                chinese_pattern = re.compile(r'[\u4e00-\u9fa5]+')
                if chinese_pattern.search(string_content):
                    # 该行已经有 _() 包裹中文，应该跳过整行
                    return []

        # 检查是否是独立的字符串语句（只有字符串，没有赋值或其他操作）
        # 例如：'''中文''' 或 _("中文") 这种单独一行的语句应该跳过
        stripped = line.strip()
        # 匹配独立的字符串语句：只有字符串和可能的空白
        standalone_string_pattern = re.compile(r'^(\s*)(\'\'\'[\s\S]*?\'\'\'|"""[\s\S]*?"""|[\'"][^\'"]*?[\'"])\s*$')
        # 或者匹配 _() 包裹的独立字符串语句
        standalone_underscore_pattern = re.compile(r'^(\s*)_\(\s*(\'\'\'[\s\S]*?\'\'\'|"""[\s\S]*?"""|[\'"][^\'"]*?[\'"])\s*\)\s*$')
        
        if standalone_string_pattern.match(stripped) or standalone_underscore_pattern.match(stripped):
            return []  # 独立的字符串语句，跳过
        
        # 匹配字符串
        string_pattern = re.compile(r'("""|"|\')(.*?)("""|"|\')')
        matches = string_pattern.finditer(line)

        for match in matches:
            content = match.group(2)
            # 提取中文
            chinese_pattern = re.compile(r'[\u4e00-\u9fa5]+')
            if chinese_pattern.search(content):
                chinese_texts.append((line_num, content))

        return chinese_texts
    
    def _find_closing_paren(self, line: str, start: int) -> int:
        """找到配对的闭合括号位置"""
        depth = 0
        in_string = False
        string_char = None
        
        i = start
        while i < len(line):
            char = line[i]
            
            # 处理字符串
            if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
            
            if not in_string:
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                    if depth == 0:
                        return i
            
            i += 1
        
        return -1
    
    def _wrap_chinese_with_translate(self, line: str, chinese_texts: List[Tuple[int, str]]) -> str:
        """用_()函数包装中文文本"""
        new_line = line
        
        # 按位置从后往前替换，避免影响位置
        # 先收集所有需要替换的位置信息
        replacements = []
        
        for line_num, text in chinese_texts:
            # 精确匹配单个字符串中的中文
            # 使用更精确的正则：匹配被引号包裹的完整字符串，且该字符串包含中文
            # 处理单引号和双引号，以及三引号字符串
            # 注意：三引号需要使用 [\s\S]*? 来匹配任意字符（包括换行）
            escaped_text = re.escape(text)
            patterns = [
                (r"f?'''([\s\S]*?''')", r"'''"),  # 三单引号
                (r'f?"""([\s\S]*?""")', r'"""'),  # 三双引号
                (r"f?'([^']*" + escaped_text + r"[^']*)'", r"'"),  # 单引号
                (r'f?"([^"]*' + escaped_text + r'[^"]*)"', r'"'),  # 双引号
            ]
            
            for pattern, quote in patterns:
                regex = re.compile(pattern)
                for match in regex.finditer(new_line):
                    full_match = match.group(0)
                    # 检查是否已经被_()包裹，包括 _("...") 和 _("..." % ...) 形式
                    # 使用正则匹配完整的 _() 调用
                    is_wrapped = False
                    underscore_wrapper_pattern = re.compile(r'_\s*\(\s*(["\'])(.*?)\1(?:\s*%\s*.*?)?\s*\)')
                    for wrapper_match in underscore_wrapper_pattern.finditer(new_line):
                        wrapper_start = wrapper_match.start()
                        wrapper_end = wrapper_match.end()
                        match_start = match.start()
                        match_end = match.end()
                        # 检查当前字符串是否在 _() 内部
                        if wrapper_start < match_start and wrapper_end > match_end:
                            is_wrapped = True
                            break
                    
                    if is_wrapped:
                        continue
                    
                    # 检查匹配的内容是否包含目标文本
                    captured = match.group(1)
                    if text in captured:
                        old_str = match.group(0)
                        new_str = f'_({old_str})'
                        replacements.append((old_str, new_str))
        
        # 从后往前替换，避免位置偏移
        for old_str, new_str in reversed(replacements):
            new_line = new_line.replace(old_str, new_str, 1)
        
        return new_line
    
    def _update_po_file(self, file_path: str, chinese_texts: List[Tuple[int, str]]):
        """更新PO文件"""
        # 读取现有PO文件
        if os.path.exists(self.po_file_path):
            with open(self.po_file_path, 'r', encoding='utf-8') as f:
                po_content = f.read()
        else:
            # 创建新的PO文件
            po_content = '''msgid ""
msgstr ""
"Project-Id-Version: ACA Builder\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: 2026-03-11\n"
"PO-Revision-Date: 2026-03-11\n"
"Last-Translator: \n"
"Language-Team: \n"
"Language: en_US\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\n"

'''
        
        # 提取现有msgid
        existing_msgids = set()
        msgid_pattern = re.compile(r'msgid "(.*?)"')
        for match in msgid_pattern.finditer(po_content):
            existing_msgids.add(match.group(1))
        
        # 添加新的中文文本
        new_entries = []
        processed_texts = set()  # 用于跟踪已经处理过的文本
        
        for line_num, text in chinese_texts:
            if text not in existing_msgids and text not in processed_texts:
                # 构建新条目
                entry = f"#: {os.path.basename(file_path)}:{line_num}\n"
                entry += f"msgid \"{text}\"\n"
                entry += f"msgstr \"fuzzy\"\n\n"
                new_entries.append(entry)
                processed_texts.add(text)  # 标记为已处理
        
        # 将新条目添加到PO文件末尾
        if new_entries:
            po_content += ''.join(new_entries)
            
            # 写回PO文件
            with open(self.po_file_path, 'w', encoding='utf-8') as f:
                f.write(po_content)
    

    
    def _compile_mo_file(self):
        """编译MO文件"""
        try:
            # 使用msgfmt工具编译
            subprocess.run(['msgfmt', self.po_file_path, '-o', self.mo_file_path], check=True)
            print(f"成功编译MO文件: {self.mo_file_path}")
        except Exception as e:
            print(f"编译MO文件失败: {e}")
            # 如果msgfmt不可用，尝试使用Python的gettext模块
            try:
                import gettext
                from gettext import GNUTranslations
                
                # 读取PO文件
                with open(self.po_file_path, 'r', encoding='utf-8') as f:
                    po_content = f.read()
                
                # 简单的PO文件解析和编译
                # 注意：这只是一个简化实现，实际项目中应该使用更完善的方法
                print("使用Python gettext模块尝试编译")
            except Exception as e2:
                print(f"使用Python gettext模块编译也失败: {e2}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ACA Builder i18n国际化工具')
    parser.add_argument('file', nargs='?', help='需要处理的Python文件路径')
    parser.add_argument('--export', '-e', action='store_true', help='导出待翻译的JSON文件')
    parser.add_argument('--output', '-o', help='导出JSON文件的路径')
    
    args = parser.parse_args()
    
    skill = ACAI18nSkill()
    
    if args.export:
        output_path = skill.export_translations_json(args.output)
        if output_path:
            print(f"导出成功: {output_path}")
        return
    
    if not args.file:
        parser.error("需要指定Python文件路径，或使用 --export 导出待翻译条目")
    
    success = skill.process_file(args.file)
    
    if success:
        print("处理成功！")
    else:
        print("处理失败！")

if __name__ == '__main__':
    main()
