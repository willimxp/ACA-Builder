# ACA Builder 项目代码结构优化建议

## 1. 项目架构分析

### 1.1 当前架构特点
ACA Builder项目采用了模块化的架构设计，主要分为以下几个层次：
- **核心模块**：`__init__.py`、`build.py`、`panel.py`、`operators.py`
- **数据管理**：`data.py`、`const.py`、`template.py`
- **建筑模块**：`buildFloor.py`、`buildWall.py`、`buildRoof.py`、`buildDougong.py`等
- **工具函数**：`utils.py`、`texture.py`

### 1.2 优势
- 模块职责划分清晰
- 遵循单一职责原则
- Blender插件架构合理

### 1.3 存在的问题
- 部分文件过大（如`utils.py`超过3500行）
- 某些模块间耦合度过高
- 缺乏统一的错误处理机制

## 2. 代码结构优化建议

### 2.1 文件拆分优化

#### 2.1.1 拆分超大文件
**问题**：`utils.py`（3577行）过于庞大
**建议**：
```
utils/ (新目录)
├── __init__.py
├── common_utils.py          # 通用工具函数
├── geometry_utils.py        # 几何计算相关
├── collection_utils.py      # 集合管理相关
├── material_utils.py        # 材质处理相关
├── validation_utils.py      # 数据验证相关
└── debug_utils.py          # 调试相关
```

#### 2.1.2 模块化建筑构建组件
**当前问题**：建筑构建文件过大
**建议**：
```
builders/
├── __init__.py
├── base_builder.py          # 基础构建器接口
├── floor/
│   ├── __init__.py
│   ├── pillar_builder.py    # 柱网构建
│   ├── grid_generator.py    # 网格生成
│   └── foundation_builder.py # 基础构建
├── wall/
│   ├── __init__.py
│   ├── wall_builder.py      # 墙体构建
│   ├── window_builder.py    # 窗户构建
│   └── door_builder.py      # 门构建
├── roof/
│   ├── __init__.py
│   ├── roof_shape.py        # 屋顶形状
│   ├── rafter_system.py     # 椽系统
│   └── tile_system.py       # 瓦系统
└── dougong/
    ├── __init__.py
    ├── component_factory.py # 斗栱组件工厂
    └── positioning.py       # 定位算法
```

### 2.2 设计模式优化

#### 2.2.1 引入工厂模式
**问题**：建筑构件创建逻辑分散
**建议**：创建建筑构件工厂

```python
# builders/component_factory.py
class ComponentFactory:
    """建筑构件工厂"""
    
    @staticmethod
    def create_component(component_type, **kwargs):
        """根据类型创建建筑构件"""
        if component_type == 'pillar':
            return PillarComponent(**kwargs)
        elif component_type == 'beam':
            return BeamComponent(**kwargs)
        elif component_type == 'roof':
            return RoofComponent(**kwargs)
        # 更多类型...
```

#### 2.2.2 实现建造者模式
**建议**：创建建筑建造者模式

```python
# builders/architecture_builder.py
class ArchitectureBuilder:
    """建筑建造者"""
    
    def __init__(self):
        self.architecture = Architecture()
    
    def build_foundation(self, specs):
        self.architecture.foundation = FoundationBuilder(specs).build()
        return self
    
    def build_structure(self, specs):
        self.architecture.structure = StructureBuilder(specs).build()
        return self
    
    def build_roof(self, specs):
        self.architecture.roof = RoofBuilder(specs).build()
        return self
    
    def get_architecture(self):
        return self.architecture
```

#### 2.2.3 引入策略模式
**建议**：用于不同的构建策略

```python
# strategies/build_strategy.py
from abc import ABC, abstractmethod

class BuildStrategy(ABC):
    """构建策略抽象基类"""
    
    @abstractmethod
    def execute(self, context):
        pass

class StandardBuildStrategy(BuildStrategy):
    """标准构建策略"""
    
    def execute(self, context):
        # 标准构建逻辑
        pass

class OptimizedBuildStrategy(BuildStrategy):
    """优化构建策略（快速模式）"""
    
    def execute(self, context):
        # 优化构建逻辑
        pass
```

### 2.3 数据管理优化

#### 2.3.1 配置管理模块化
**问题**：常量定义过于集中
**建议**：
```
config/
├── __init__.py
├── constants.py            # 基础常量
├── dimension_config.py     # 尺寸配置
├── material_config.py      # 材质配置
├── ui_config.py           # UI配置
└── build_config.py        # 构建配置
```

#### 2.3.2 数据模型重构
**建议**：使用数据类代替简单的属性组

```python
# models/architecture_data.py
from dataclasses import dataclass
from typing import Dict, List, Optional
import bpy

@dataclass
class BuildingSpecs:
    """建筑规格数据类"""
    width: float = 10.0
    depth: float = 8.0
    height: float = 5.0
    dk_size: float = 0.08
    pillar_spacing: List[float] = None
    
    def __post_init__(self):
        if self.pillar_spacing is None:
            self.pillar_spacing = []

@dataclass
class ConstructionParams:
    """构建参数数据类"""
    roof_type: str = "xieshan"
    has_dougong: bool = True
    has_balcony: bool = False
    floor_count: int = 1
```

### 2.4 错误处理机制优化

#### 2.4.1 统一异常处理
**建议**：创建自定义异常体系

```
exceptions/
├── __init__.py
├── base_exceptions.py      # 基础异常类
├── validation_errors.py    # 验证错误
├── build_errors.py         # 构建错误
└── io_errors.py           # 输入输出错误
```

```python
# exceptions/base_exceptions.py
class ACAException(Exception):
    """ACA插件基础异常"""
    pass

class ACAValidationError(ACAException):
    """验证错误"""
    pass

class ACABuildError(ACAException):
    """构建错误"""
    pass
```

#### 2.4.2 错误处理装饰器
**建议**：创建错误处理装饰器

```python
# decorators/error_handling.py
import functools
import logging
from ..exceptions.base_exceptions import ACAException

def handle_errors(error_callback=None):
    """错误处理装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ACAException as e:
                # 专业错误处理
                logging.error(f"ACA错误: {str(e)}")
                if error_callback:
                    error_callback(e)
                raise
            except Exception as e:
                # 通用错误处理
                logging.error(f"未知错误: {str(e)}")
                raise ACAException(f"发生未知错误: {str(e)}")
        return wrapper
    return decorator
```

### 2.5 依赖注入优化

#### 2.5.1 服务容器
**建议**：实现服务容器管理依赖

```python
# services/container.py
class ServiceContainer:
    """服务容器"""
    
    def __init__(self):
        self._services = {}
        self._singletons = {}
    
    def register(self, name, factory, singleton=False):
        """注册服务"""
        if singleton:
            self._services[name] = lambda: self._get_singleton(name, factory)
        else:
            self._services[name] = factory
    
    def get(self, name):
        """获取服务实例"""
        if name in self._services:
            return self._services[name]()
        raise KeyError(f"Service {name} not found")
    
    def _get_singleton(self, name, factory):
        """获取单例服务"""
        if name not in self._singletons:
            self._singletons[name] = factory()
        return self._singletons[name]
```

### 2.6 事件系统优化

#### 2.6.1 事件驱动架构
**建议**：引入事件系统解耦模块

```python
# events/event_system.py
from typing import Callable, Dict, List
import weakref

class EventSystem:
    """事件系统"""
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        if event_type in self._listeners:
            self._listeners[event_type].remove(callback)
    
    def emit(self, event_type: str, data=None):
        """发出事件"""
        if event_type in self._listeners:
            for callback in self._listeners[event_type][:]:  # 复制列表避免修改时的问题
                callback(data)

# 使用示例
class BuildingService:
    def __init__(self, event_system: EventSystem):
        self.event_system = event_system
        self.event_system.subscribe('building_created', self.on_building_created)
    
    def create_building(self, specs):
        # 创建建筑逻辑
        building = self._build(specs)
        # 发出事件
        self.event_system.emit('building_created', building)
    
    def on_building_created(self, building):
        # 建筑创建后的处理
        pass
```

## 3. 重构实施建议

### 3.1 分阶段重构计划

#### 第一阶段：基础设施优化（1-2周）
- 创建新的目录结构
- 拆分超大的utils.py文件
- 实现基础的异常处理系统

#### 第二阶段：核心模块重构（2-3周）
- 重构建筑构建模块
- 实现设计模式
- 优化数据模型

#### 第三阶段：高级特性（1-2周）
- 实现依赖注入
- 添加事件系统
- 完善错误处理

### 3.2 向后兼容性保证
- 保持现有的API接口不变
- 逐步迁移，避免破坏性变更
- 提供适配器层确保兼容

### 3.3 测试策略
- 为重构的模块编写单元测试
- 确保重构后功能完全一致
- 性能测试确保优化效果

## 4. 代码质量提升建议

### 4.1 代码规范强化
- 统一的代码风格（PEP 8）
- 完善的类型注解
- 详细的文档字符串

### 4.2 重构工具建议
- 使用静态分析工具（如mypy、pylint）
- 代码复杂度分析
- 依赖关系可视化

## 5. 总结

通过以上结构优化建议，ACA Builder项目可以获得：
1. **更好的可维护性**：模块化结构便于理解和修改
2. **更高的可扩展性**：设计模式支持新功能的快速添加
3. **更强的健壮性**：完善的错误处理机制
4. **更优的性能**：合理的架构设计提升运行效率

这些建议应该分阶段实施，确保重构过程的平稳过渡，同时保持项目的稳定性和功能完整性。