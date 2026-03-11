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
- **file**：需要处理的Python文件路径

## 技能执行过程

### 1. 代码预处理
1. 扫描Python文件，找到中文文本（跳过注释行中的中文）
2. 修改代码中的format字符串，改为%s的调用方式
   - 例如：`print(f"{v1}中文文本{v2}")` 改为 `print(_("%s中文文本%s" % (v1, v2)))`
3. 根据代码的相对目录结构，确定_()函数的导入方式
   - 根目录下的Python脚本：`from .locale.i18n import _`
   - 子目录下的Python脚本：`from ..locale.i18n import _`
4. 对中文文本自动调用_()翻译函数
   - 例如：`_('中文文本')`
5. **防重复包裹规则**：如果中文文本已经被_()函数包裹，不再进行二次包裹
   - 例如：`_('中文文本')` 不会进一步改成 `_(_('中文文本'))`
   - f-string如 `_(f"{v1}中文{v2}")` 也不会重复处理
6. 将中文文本添加到`locale/en_US/LC_MESSAGES/aca_builder.po`文件中
   - 格式：
     ```
     #: operators.py:347
     msgid "中文文本"
     msgstr "fuzzy"
     
     ```
   - 不修改PO文件中原有的其他内容

### 2. 与Agent交互进行翻译
1. 提取`aca_builder.po`中标注为'fuzzy'的msgid内容
2. 将需要翻译的内容展示给当前运行的大模型Agent会话
3. 等待Agent提供英文翻译结果
4. 通过`update_translations`方法更新翻译结果到PO文件

### 3. 编译MO文件
1. 编译`aca_builder.po`文件，生成`aca_builder.mo`文件
2. 将生成的MO文件保存在`locale/en_US/LC_MESSAGES`目录下

## 工具调用
- 调用 `aca_i18n.py` 进行代码预处理和PO文件更新
- 调用 `compile_mo.py` 进行MO文件编译

## 使用示例
```bash
# 处理单个Python文件
python3 “aca_i18n.py” “path/to/file.py”

# 编译MO文件
python3 “compile_mo.py” “locale/en_US/LC_MESSAGES/aca_builder.po” “locale/en_US/LC_MESSAGES/aca_builder.mo”
```

## 注意事项
- 确保Python文件编码为UTF-8
- 确保`locale/en_US/LC_MESSAGES`目录存在
- 如遇编译MO文件失败，会尝试使用Python的gettext模块作为备选方案