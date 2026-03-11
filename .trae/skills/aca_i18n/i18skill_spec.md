# 新建一个针对本项目的i18n国际化的skill

- 技能名称：aca_i18n
- 技能描述：自动处理ACA插件的i18n国际化，包括提取中文文本、代码预处理、自动调用_()翻译函数，生成PO文件、编译MO文件等
- 技能参数：
  - file：需要处理的python文件路径

## 技能执行过程：
### 1、代码预处理python脚本
- 扫描python文件，找到中文文本
    - 跳过注释行中的中文
- 修改代码中的format字符串，改为%s的调用方式,
    - 如：print(f"{v1}中文文本{v2}")，改为print("%s中文文本%s" % (v1,v2))
- 导入locale.i18n模块，根据代码的相对目录结构，确定_()函数的导入方式
    - 如, 根目录下的python脚本，导入方式为`from .locale.i18n import _`
    - 如，子目录下的python脚本，导入方式为`from ..locale.i18n import _`
- 对中文文本自动调用_()翻译函数
    - 例如：_("中文文本")
- 将中文文本添加到locale/en_US/LC_MESSAGES/aca_builder.po文件中，第1行标注代码文件名和代码行号，第2行msgid为抽取的中文文本，第3行msgstr统一用'fuzzy'替代，第4行为空白行，如：
```
#: operators.py:347
msgid "中文文本"
msgstr "fuzzy"

```
- 不要修改locale/en_US/LC_MESSAGES/aca_builder.po文件中原有的其他内容
### 2、与agent交互进行翻译
- 提取aca_builder.po中标注为'fuzzy'的msgid内容
- 将需要翻译的内容展示给当前运行的大模型agent会话
- 等待agent提供英文翻译结果
- 通过update_translations方法更新翻译结果到PO文件
### 3、编译python脚本
- 编译aca_builder.po文件，生成aca_builder.mo文件
- 将生成的mo文件保存在locale/en_US/LC_MESSAGES目录下

## 新增功能：
- **_extract_fuzzy_entries()**：提取PO文件中标注为'fuzzy'的条目
- **update_translations(translations)**：更新翻译结果并编译MO文件
- **compile_mo.py**：独立的MO文件编译工具