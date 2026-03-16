# Blender UI 翻译规范

本规范用于指导ACA Builder插件的中文到英文翻译工作，确保翻译符合Blender界面习惯和古建筑专业术语标准。

## 一、文本分类与翻译策略

### 1.1 错误消息 (Error Messages)

**特征**: 以"无法"、"失败"、"错误"开头，或描述操作结果

**翻译原则**:
- 使用简洁的陈述句
- 说明问题原因和解决建议
- 保持语气专业、友好

| 原中文 | 翻译规范 | 示例 |
|--------|----------|------|
| 无法... | Cannot... | 无法创建 → Cannot create |
| ...失败 | ...failed | 删除失败 → Deletion failed |
| ...错误 | ...error | 设置错误 → Setting error |
| 请... | Please... | 请选择 → Please select |
| ...不存在 | ...not found | 未找到 → Not found |
| ...无效 | ...invalid | 参数无效 → Invalid parameter |

**常用句式**:
```
Cannot [verb] [object]: [reason]
[Object] not found, please [action]
[Action] failed: [reason]. Please [suggestion]
```

### 1.2 建筑构件名称 (Component Names)

**特征**: 古建筑专业术语，对应具体构件

**翻译原则**:
- 严格遵守 `locale/i18n_term.json` 术语表

**翻译优先级**:
1. 术语表中有明确译法的 → 使用术语表译法
2. 无标准译法 → 直译并保留拼音

### 1.3 参数名称 (Parameter Labels)

**特征**: Blender面板中的属性名称，通常较短

**翻译原则**:
- 使用名词或名词短语
- 保持简洁，适合窄面板显示
- 参考Blender原生UI命名习惯

**常用参数翻译模式**:

| 中文模式 | 英文模式 | 示例 |
|----------|----------|------|
| 是否+名词 | Show/Use + noun | 是否显示 → Show |
| ...类型 | ...Type | 屋顶类型 → Roof Type |
| ...宽度 | ...Width | 开口宽度 → Opening Width |
| ...高度 | ...Height | 门口高度 → Door Height |
| ...数量 | ...Count | 步架数量 → Tread Count |
| ...比例 | ...Ratio | 门口宽比 → Door Width Ratio |
| ...系数 | ...Factor | 举折系数 → Slope Factor |
| ...列表 | ...List | 踏跺列表 → Step List |

**Blender风格参数翻译示例**:
```
台基高度 → Platform Height
檐柱高 → Eave Column Height
斗口 → Doukou
步架数量 → Tread Count
举折系数 → Slope Factor
收分尺寸 → Setback Size
出跳 → Projection
起翘 → Eave Lift
```

### 1.4 操作提示与帮助文本

**特征**: 较长的说明性文本，提供操作指导

**翻译原则**:
- 使用祈使句或动名词结构
- 保持简洁，避免冗长
- 首字母大写，符合UI规范

**常用句式**:
```
[Verb] + [object]...
[Action] + [condition]...
```

**示例**:
```
请先选择台基 → Please select platform first
先选择2根以上的柱子 → Select 2 or more columns first
根据参数的修改，重新生成建筑 → Regenerate building based on parameter changes
```

### 1.5 菜单项与按钮文本

**特征**: 用户交互元素，通常为动词或动词短语

**翻译原则**:
- 使用动词或动名词(ing形式)
- 首字母大写
- 保持简短有力

**常用翻译对照**:

| 中文 | 英文 | 说明 |
|------|------|------|
| 生成 | Generate | 创建建筑 |
| 更新 | Update | 刷新建筑 |
| 删除 | Delete | 移除对象 |
| 添加 | Add | 新增组件 |
| 设置 | Set | 配置参数 |
| 保存 | Save | 存储配置 |
| 导出 | Export | 输出模型 |
| 创建 | Create | 新建对象 |

### 1.6 格式化字符串

**特征**: 包含`%s`、`%d`、`[%s]`、`|`、`-`等占位符

**翻译原则**:
- 保持占位符位置不变
- 调整句子结构以适应占位符位置
- 确保语法正确

**示例**:
```
无法创建该类型的建筑：%s → Cannot create this type of building: %s
面阔尽间当前[%s],应大于[%s] → Very End Bay width is currently [%s], should be greater than [%s]
```

## 二、通用翻译规则

### 2.1 术语一致性

- **单复数统一**:
- **大小写规范**: 菜单项首字母大写，属性名可小写
- **缩写谨慎使用**: 避免使用不常见的缩写

### 2.2 标点规范

- 使用英文标点 `. , : ;`
- 冒号后留空格: `Property: Value`
- 句末不加句号（UI文本惯例）

### 2.3 空格规范

- 数字与单位之间加空格: `10 m` 而非 `10m`
- 百分号前不加空格: `50%` 而非 `50 %`

### 2.4 括号使用

- 使用英文括号 `( )`
- 参数说明中的范围: `[min, max]`
- 可选值: `(No Railing)`

## 三、特殊处理规则

### 3.2 组合对象命名

**翻译规范**: 使用点分隔符，保持层级结构

```
栏杆.%s → Railing.%s
望柱.%s → Baluster.%s
地栿.%s → Difu.%s
```

### 3.3 选项列表

**翻译规范**: 编号+描述，清晰对应

```
0-重檐 → 0-Double Eave
1-简单重楼 → 1-Simple Multi-Floor
2-重楼+平坐 → 2-Multi-Floor + Pingzuo
```

### 3.4 警告与提示

**翻译规范**: 使用清晰的问题-原因-解决方案结构

```
盝顶设置异常，斗栱出跳或盝顶檐步架宽太小。请使用有出跳的斗栱，或增加盝顶檐步架宽。
→
Truncated-Hip Roof setting error, Dougong-projection or Rafter-Span is too small. 
Please use Dougong with projection, or increase Rafter-Span.
```

## 四、常用参考句式

### 4.1 操作成功

```
[操作]完成！|[建筑样式：【%s】] |[运行时间：【%.1f秒】]
[Action] Complete! | Building Style: [%s] | Time: [%.1f seconds]
```

### 4.2 操作失败

```
[操作]失败：{原因}
[Action] failed: [reason]
```

### 4.3 参数验证

```
[参数]当前[%s],应大于[%s]
[Parameter] is currently [%s], should be greater than [%s]
```

### 4.4 操作确认

```
确定删除【%s】吗？
Delete [%s]?
```

### 4.5 进度提示

```
正在[操作]... | [Action] in progress...
[操作]中，请耐心等待 | Please wait while [action]...
```

## 五、翻译检查清单

- [ ] 术语表中的术语已正确使用
- [ ] 占位符位置保持不变
- [ ] 英文标点使用正确
- [ ] 首字母大写符合规范
- [ ] 句子简洁，适合UI显示
- [ ] 无拼写或语法错误
- [ ] 与现有翻译风格一致
