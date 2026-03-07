# 任务列表

- [ ] 创建 `locale` 目录。
- [ ] 创建 `locale/zh_HANS.py` 并填充初始字典数据。
- [ ] 创建 `locale/i18n.py`，实现 `register()`、`unregister()` 和 `_()` 函数。
- [ ] 修改 `operators.py`，在 `ACA_OT_Preferences` 中添加 `language` 属性。
- [ ] 修改 `__init__.py` 以导入 `locale` 并注册/注销翻译模块。
- [ ] 验证 `_()` 函数在 "跟随系统"、"简体中文" 和 "English" 下是否正常工作。
- [ ] 测试上下文感知翻译和全局匹配。
