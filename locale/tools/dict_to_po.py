# 这个脚本用于从 en_US.py 字典生成 en_US.po 文件
# 用于翻译 ACA Builder 插件
# 由Trae自动编写

import os
import sys
import time

# Add current directory to path to allow importing en_US if run from locale/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import en_US
except ImportError:
    # If run from project root
    from . import en_US

def escape_po_string(s):
    """Escapes a string for use in a PO file."""
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

def generate_po():
    """Generates en_US.po from en_US.py dictionary."""
    
    output_file = os.path.join(os.path.dirname(__file__), "en_US.po")
    
    with open(output_file, "w", encoding="utf-8") as f:
        # Write Header
        f.write('msgid ""\n')
        f.write('msgstr ""\n')
        f.write('"Project-Id-Version: ACA Builder\\n"\n')
        f.write('"MIME-Version: 1.0\\n"\n')
        f.write('"Content-Type: text/plain; charset=UTF-8\\n"\n')
        f.write('"Content-Transfer-Encoding: 8bit\\n"\n')
        f.write(f'"PO-Revision-Date: {time.strftime("%Y-%m-%d %H:%M%z")}\\n"\n')
        f.write('"Last-Translator: Auto Generated <noreply@example.com>\\n"\n')
        f.write('"Language-Team: English <en@li.org>\\n"\n')
        f.write('"Language: en_US\\n"\n')
        f.write('\n')

        data = en_US.data.get("en_US", {})
        
        # Sort keys to ensure deterministic output
        sorted_keys = sorted(data.keys(), key=lambda x: (x[0], x[1]))
        
        for context, msgid in sorted_keys:
            msgstr = data[(context, msgid)]
            
            if not msgid:
                continue
                
            f.write(f'msgctxt "{escape_po_string(context)}"\n')
            f.write(f'msgid "{escape_po_string(msgid)}"\n')
            f.write(f'msgstr "{escape_po_string(msgstr)}"\n')
            f.write('\n')
            
    print(f"Generated {output_file}")

if __name__ == "__main__":
    generate_po()
