# ACA Builder 国际化 (i18n) 规格说明书

## 1. 概述

### 1.1 目标

为 ACA Builder 筑韵古建插件实现多语言支持 (i18n)，支持用户在偏好设置中切换语言：

| 选项 | 说明 |
|------|------|
| 跟随系统 | 根据 Blender 环境的语言设置自动切换 |
| 简体中文 | 显示简体中文界面 |
| 英文 | 显示英文界面 |

### 1.2 技术选型

- **翻译模块**: Python 原生 `gettext` 模块（不使用 Blender 的 `bpy.app.translations`）
- **支持功能**:
  - 不带上下文的翻译 (`gettext`)
  - 带上下文的翻译 (`pgettext`)
- **源码语言**: 简体中文（`msg_id` 使用中文，`msgstr` 使用英文）

---

## 2. 模块结构

```
locale/
├── i18n.py                    # 核心逻辑模块
└── en_US/LC_MESSAGES/         # 英文翻译资源
    ├── aca_builder.po/.mo     # Python 文件翻译
    └── aca_xml.po/.mo         # XML 文件翻译
```

### 2.1 i18n.py 核心功能

| 函数/类 | 说明 |
|---------|------|
| `I18nPrefsMixin` | 插件偏好设置中的语言选项定义 |
| `update_language()` | 设置当前插件展示的语言，缓存设置并触发 UI 刷新 |
| `load_translations()` | 初始化翻译系统，加载翻译文件 |
| `_()` | 全局翻译函数入口 |

### 2.2 load_translations() 行为

| 模式 | 行为 |
|------|------|
| DEBUG | 加载 `.mo` 文件，绕过缓存 |
| 生产 | 加载 `.po` 文件，应用缓存 |
| 特性 | 自动合并 `aca_builder` 和 `aca_xml` 两个域 |

---

## 3. 核心 API

### 3.1 翻译函数 `_()`

**函数签名**:
```python
def _(msg_id: str, context: str | None = None) -> str
```

**参数说明**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `msg_id` | str | 待翻译的文本（源码为中文） |
| `context` | str \| None | 翻译上下文，用于区分不同场景 |

**分发逻辑**:

```
┌─────────────────────────────────────────────┐
│           获取语言偏好                        │
│     (优先缓存 _current_language)              │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
   [en_US]              [zh_HANS]
        │                   │
        ▼                   │
┌───────────────┐           │
│ pgettext()    │           │ 直接返回 msg_id
│ gettext()     │           │
│ "*" 上下文     │           │
└───────────────┘           │
        │                   │
        └─────────┬─────────┘
                  ▼
            [返回结果]
```

**详细查找顺序 (en_US 模式)**:

1. `gettext.pgettext(context, msg_id)`
2. 若 `context` 为 `None`，退回 `gettext.gettext(msg_id)`
3. 若仍未命中，尝试使用 `"*"` 通用上下文查找

**语言模式说明**:

| 模式 | 行为 |
|------|------|
| `en_US` | 查找 `.mo` 文件将中文翻译为英文 |
| `zh_HANS` | 直接返回原始 `msg_id` |
| `FOLLOW` | 委托 `bpy.context.preferences.view.language` 决定 |

---

## 4. 动态语言切换

### 4.1 update_language() 处理流程

**触发条件**: 偏好设置中 `language` 属性的 `update` 回调

**执行步骤**:

```
┌────────────────────────────────────────────┐
│ 1. 缓存语言状态                              │
│    设置 _current_language                    │
├────────────────────────────────────────────┤
│ 2. 注销所有类                               │
│    从 sys.modules 查找主模块并反向注销       │
├────────────────────────────────────────────┤
│ 3. 清理自定义属性                           │
│    调用 data.delprop()                      │
├────────────────────────────────────────────┤
│ 4. 重新加载模块                             │
│    importlib.reload(data/panel/operators)  │
├────────────────────────────────────────────┤
│ 5. 重新发现并注册                           │
│    使用 auto_register                        │
├────────────────────────────────────────────┤
│ 6. 重新初始化属性                           │
│    调用 data.initprop()                     │
├────────────────────────────────────────────┤
│ 7. 强制重绘                                 │
│    遍历窗口区域执行 area.tag_redraw()        │
└────────────────────────────────────────────┘
```

---

## 5. 翻译文件格式

### 5.1 PO 文件结构

```po
# 普通翻译
msgid "彩画风格"
msgstr "Paint Style"

# 带上下文的翻译
msgctxt "template"
msgid "三间庑殿"
msgstr "3-Bay Hip Roof"
```

### 5.2 翻译域 (Domains)

| 域名 | 用途 |
|------|------|
| `aca_builder` | 核心界面与插件逻辑文本（`.py` 文件） |
| `aca_xml` | 动态加载的 XML 资源（`template.xml`、`acaAssets.xml`） |

---

## 6. 集成规范

### 6.1 代码中使用 `_()`

所有需要国际化的文本必须通过 `_()` 包装：

- 静态字段
- `EnumProperty` 的枚举项描述
- 动态 UI 元素文本

### 6.2 启动与性能

- `load_translations()` 在 `i18n.py` 模块加载时自动调用
- DEBUG 模式下绕过 `gettext` 内部缓存，直接从磁盘读取 `.mo` 文件

---

## 7. 相关文件

| 文件 | 说明 |
|------|------|
| [i18n.py](file:///Volumes/XP.T9/Blender/ACA%20Builder/locale/i18n.py) | 核心查找、加载与模块重载逻辑 |
| [aca_builder.po](file:///Volumes/XP.T9/Blender/ACA%20Builder/locale/en_US/LC_MESSAGES/aca_builder.po) | Python 文件翻译源文件 |
| [data.py](file:///Volumes/XP.T9/Blender/ACA%20Builder/data.py) | 插件属性定义国际化 |
| [panel.py](file:///Volumes/XP.T9/Blender/ACA%20Builder/panel.py) | UI 面板国际化文本 |
| [dict_to_po.py](file:///Volumes/XP.T9/Blender/ACA%20Builder/locale/tools/dict_to_po.py) | 字典转 PO 格式工具 |
