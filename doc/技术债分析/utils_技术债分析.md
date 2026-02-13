# 技术债分析报告：utils.py

## 1. 文件概览
- **路径**: `/Volumes/XP.T9/Blender/ACA Builder/utils.py`
- **功能**: 通用工具库，包含数学计算、Blender API 封装、几何操作、对象管理等。
- **行数**: 约 3600 行

## 2. 主要技术债

### 2.1 严重的“上帝对象”问题 (Critical)
该文件长达 3600 行，包含了太多互不相关的功能：
- 基础数学运算 (`getVectorDistance`, `bezier_point`)
- Blender 对象操作 (`copyObject`, `applyTransform`)
- 几何算法 (`mesh_mesh_intersection`, `intersect_curve_mesh`)
- UI 辅助 (`popMessageBox`, `redrawViewport`)
- 数据处理 (`copyAcaData`)

这导致代码难以导航，难以测试，且任何修改都可能意外影响其他不相关的功能。

**建议**: 必须进行模块化拆分：
- `utils_math.py`: 纯数学计算
- `utils_blender.py`: Blender 对象/集合操作
- `utils_geometry.py`: 复杂的几何算法（如 BVH 检测）
- `utils_ui.py`: 界面交互相关
- `utils_data.py`: 数据处理相关

### 2.2 循环依赖风险 (High)
- 存在局部导入 `from . import data` 和 `from . import build` (在 `logError` 中)。这是为了解决循环导入而采取的临时方案，表明模块间的依赖关系混乱。

**建议**: 重构依赖关系，确保 `utils` 层级只依赖于更底层的库，不应依赖上层业务逻辑（如 `build`）。`logError` 中的依赖可以通过回调或依赖注入解决。

### 2.3 危险的 Monkey Patch (High)
- `fastRun` 函数中修改了 `_BPyOpsSubModOp._view_layer_update`。这是一种极度危险的操作，依赖于 Blender 内部实现细节，Blender 升级可能随时导致此功能失效或崩溃。

**建议**: 寻找官方支持的性能优化方案（如批量操作 API），或至少为此功能添加严格的版本检测保护。

### 2.4 函数过长与复杂度过高 (Medium)
- `mesh_mesh_intersection` 等几何算法函数极其复杂，包含了 BVH 构建、射线检测、KDTree 去重、曲线生成等多个步骤。

**建议**: 将复杂算法提取为独立的算法类或拆分为多个子函数。

### 2.5 代码重复 (Medium)
- `addCube` 和 `addCubeBy2Points` 等函数存在逻辑重复。
- 多个 `addModifier...` 函数结构相似。

**建议**: 使用构建者模式或参数化工厂方法来统一创建逻辑。

### 2.6 废弃代码残留 (Low)
- 存在大量注释掉的代码块（如 `console_print` 的旧实现）。

**建议**: 清理死代码，保持代码库整洁。

## 3. 重构计划建议
1. **拆分文件**: 立即着手将 `utils.py` 拆分为多个子模块。
2. **移除 Monkey Patch**: 调研 `fastRun` 的替代方案。
3. **依赖解耦**: 移除 `utils` 对业务层 (`build`, `data`) 的反向依赖。
