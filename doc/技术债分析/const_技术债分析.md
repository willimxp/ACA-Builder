# 技术债分析报告：const.py

## 1. 文件概览
- **路径**: `/Volumes/XP.T9/Blender/ACA Builder/const.py`
- **功能**: 全局常量定义，包括几何参数、材质名称、类型枚举等。
- **行数**: 约 392 行

## 2. 主要技术债

### 2.1 上帝类 (God Class) 倾向 (High)
`ACA_Consts` 类包含了一切：
- 目录名称 (`COLL_NAME_ROOT`)
- 系统类型 (`ACA_TYPE_BUILDING`)
- 几何参数 (`DEFAULT_DK`, `PLATFORM_HEIGHT`)
- 材质名称 (`M_ROCK`)
- 构造尺寸 (`BANWA_SIZE`)

这种“大杂烩”式的常量定义导致该类内聚性低，任何模块都需要依赖它，且修改任何一类常量都涉及此文件。

**建议**:
拆分为多个功能专用的常量类或命名空间：
- `GeometryConsts`: 几何尺寸相关
- `MaterialConsts`: 材质名称相关
- `TypeConsts`: 对象类型标识
- `PathConsts`: 目录和文件路径

### 2.2 命名规范不统一 (Medium)
- 部分常量有前缀（如 `ACA_TYPE_`），部分没有（如 `PLATFORM_NAME`）。
- 存在缩写不一致的情况（`DG` vs `DOUGONG`）。

**建议**: 统一命名规范，或者通过类嵌套来建立命名空间（例如 `ACA_Consts.Type.BUILDING`）。

### 2.3 缺乏单位明确性 (Low)
- 虽然大部分注释中标注了 `(DK)` 或 `(m)`，但在变量名中体现单位会更安全。例如 `DEFAULT_DK_METER` 或 `PILLAR_HEIGHT_DK`。

### 2.4 运行时保护开销 (Low)
- 使用 `__setattr__` 抛出异常来防止修改常量。虽然 Python 中没有原生常量，但通常约定俗成（全大写）即可。这种运行时检查增加了少量的复杂性，且在 Python 哲学中通常是不必要的（"We are all consenting adults here"）。

**建议**: 移除 `__setattr__` 限制，遵循 Python 社区惯例。

## 3. 重构计划建议
1. 按功能拆分常量类。
2. 统一变量命名风格。
3. 移除不必要的运行时写入保护。
