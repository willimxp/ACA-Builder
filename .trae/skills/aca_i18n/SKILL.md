---
name: "aca_i18n"
description: "自动处理ACA插件的i18n国际化，包括提取中文文本、代码预处理、自动调用_()翻译函数，生成PO文件、编译MO文件等。Invoke when user needs to internationalize ACA plugin Python files."
---

# ACA Builder 国际化技能

## 技能功能
自动处理ACA插件的i18n国际化，包括：
- 提取Python文件中的中文文本
- 代码预处理，修改format字符串为%s格式
- 自动导入locale.i18n模块并调用_()翻译函数
- 生成和更新PO文件
- 编译MO文件

## 技能参数
- **file**：需要处理的Python文件路径（绝对路径）
- 如果输入了多个文件，则以文件纬度串行处理，而非按步骤纬度批量处理。第一个文件预处理、翻译、更新PO文件全部完成后，再处理下一个文件。

## 技能调用方法

**直接执行以下命令即可：**

```bash
# 处理单个Python文件（自动完成代码预处理并导出待翻译JSON，不更新PO文件）
python3 "/Volumes/XP.T9/Blender/ACA Builder/.trae/skills/aca_i18n/aca_i18n.py" "需要处理的Python文件绝对路径"

# Agent翻译JSON后，更新PO文件并编译MO文件（自动删除临时JSON文件）
python3 "/Volumes/XP.T9/Blender/ACA Builder/.trae/skills/aca_i18n/update_translations.py" "locale/en_US/LC_MESSAGES/translations_to_translate.json"
```

## 技能执行过程

### 1. 代码预处理
1. 扫描Python文件，找到中文文本（跳过注释行中的中文）
2. 修改代码中的format字符串，改为%s的调用方式
   - 例如：`print(f"{v1}中文文本{v2}")` 改为 `print(_("%s中文文本%s") % (v1, v2))`
3. 根据代码的相对目录结构，确定_()函数的导入方式
   - 根目录下的Python脚本：`from .locale.i18n import _`
   - 子目录下的Python脚本：`from ..locale.i18n import _`
4. 对中文文本自动调用_()翻译函数
   - 例如：`_('中文文本')`
5. **防重复包裹规则**：如果中文文本已经被_()函数包裹，不再进行二次包裹
   - 例如：`_('中文文本')` 不会进一步改成 `_(_('中文文本'))`
   - f-string如 `_(f"{v1}中文{v2}")` 也不会重复处理
6. 将中文文本导出到JSON文件
   - 文件位置：`locale/en_US/LC_MESSAGES/translations_to_translate.json`
   - 格式：
     ```json
     {
       "entries": {
         "中文文本": {
           "translation": "",
           "file": "operators.py",
           "line": 347
         }
       }
     }
     ```

### 2. 与Agent交互进行翻译
1. JSON文件导出后，Agent翻译JSON中的`translation`字段

### 3. 更新PO文件，编译MO文件
1. 执行 `update_translations.py` 更新PO文件并编译MO文件
   - 会将新条目添加到PO文件
   - 填充翻译后的内容
   - 编译MO文件
2. 临时JSON文件会自动删除
3. 编译`aca_builder.po`文件，生成`aca_builder.mo`文件
4. 将生成的MO文件保存在`locale/en_US/LC_MESSAGES`目录下

## 注意事项
- 确保Python文件编码为UTF-8
- 确保`locale/en_US/LC_MESSAGES`目录存在
- 如遇编译MO文件失败，会尝试使用Python的gettext模块作为备选方案
