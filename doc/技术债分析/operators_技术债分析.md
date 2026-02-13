# 技术债分析报告: operators.py

## 1. 文件概览
- **文件路径**: `operators.py`
- **主要功能**: 定义 Blender Operators（操作符），响应用户点击事件，连接 UI 与构建逻辑。
- **代码规模**: 约 1800+ 行。

## 2. 主要技术债

### 2.1 逻辑泄漏 (Logic Leakage)
- **问题描述**: Operator 的 `execute` 方法中不仅仅是调用 `build` 模块，还包含了很多参数校验、前置处理、后置清理的业务逻辑。
- **影响**: 业务逻辑分散在 Operator 和 Build 模块中，导致代码复用困难。如果在脚本中直接调用 Build 函数，会缺失 Operator 中的校验逻辑。

### 2.2 缺乏统一的错误处理
- **问题描述**: 每个 Operator 都有自己的 try-except 块（或者根本没有），错误提示方式不统一（有的 print，有的 popMessageBox）。
- **影响**: 用户体验不一致，难以定位错误。

### 2.3 复杂的参数传递
- **问题描述**: 使用 `functools.partial` 来封装函数调用，传递给 `utils.fastRun`。这种方式增加了代码的阅读难度和调试复杂度。

## 3. 改进建议
1.  **瘦 Operator 模式**: 严格遵守 Operator 仅作为“控制器”的原则，所有业务逻辑下沉到 Service 层（即 `build` 模块）。
2.  **统一装饰器**: 使用 Python 装饰器来处理通用的性能计时、错误捕获和上下文检查。
3.  **移除 fastRun hack**: 重新评估 `utils.fastRun` 的必要性，如果可能，回归标准的 Blender 操作调用方式。
