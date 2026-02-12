# ACA Builder 项目代码规则规范

## 目录
1. [项目架构规则](#1-项目架构规则)
2. [命名规范](#2-命名规范)
3. [代码结构规则](#3-代码结构规则)
4. [错误处理规则](#4-错误处理规则)
5. [UI界面规则](#5-ui界面规则)
6. [性能优化规则](#6-性能优化规则)
7. [数据管理规则](#7-数据管理规则)
8. [版本兼容规则](#8-版本兼容规则)
9. [国际化考虑](#9-国际化考虑)
10. [代码重构专项规范](#10-代码重构专项规范)

---

## 1. 项目架构规则

### 1.1 模块化组织结构

**核心模块层**
- `__init__.py` - 插件初始化和注册
- `build.py` - 建筑构建主入口引擎
- `panel.py` - UI界面面板系统
- `operators.py` - 操作逻辑类集合

**数据管理层**
- `data.py` - 自定义数据结构和属性绑定
- `data_callback.py` - 数据属性更新回调函数集合
- `const.py` - 全局常量和配置定义
- `template.py` - 模板管理系统

**工具函数层**
- `utils.py` - 通用工具方法集合
- `texture.py` - 材质贴图系统

**工具类模块层**
- `tools/` - 工具类模块目录
  - `auto_register.py` - 自动类注册工具
  - `aca_logging.py` - 日志管理模块

**测试文件层**
- `test/` - 测试脚本和调试工具目录

**建筑功能模块层**
- `buildFloor.py` - 柱网构建模块
- `buildWall.py` - 装修布局模块
- `buildRoof.py` - 屋顶构建模块
- `buildDougong.py` - 斗栱构建模块
- `buildPlatform.py` - 台基构建模块
- `buildBeam.py` - 梁架构建模块
- `buildRooftile.py` - 瓦作构建模块

### 1.2 依赖关系原则

**基础依赖流向**
```
const.py → 所有模块
utils.py → 建筑功能模块
```

**分层依赖架构**
```
UI层(panel.py) → 业务逻辑层(operators.py) → 构建引擎(build.py)
构建引擎 → 建筑模块(build*.py) → 工具层(utils.py)
数据层(data.py/template.py) → 工具层(utils.py)
```

**依赖约束**
- ✅ 单向依赖：上层模块依赖下层模块
- ❌ 禁止循环依赖
- ❌ 禁止跨层直接调用
- ✅ 工具函数可被多层复用

---

## 2. 命名规范

> **⚠️ 重要提示**：本章节规范仅适用于**新编写的代码**。对于从旧版本迁移的代码，必须严格遵守 [REFACTOR_FUNCTION_MIGRATION_RULES.md](REFACTOR_FUNCTION_MIGRATION_RULES.md) 中的“等效迁移”原则，保留原始变量名（即使不符合本规范）。

### 2.1 文件命名规则

**Python文件**
- 使用小写加下划线格式：`build_floor.py`
- 功能描述性命名：`build_roof.py`、`build_dougong.py`
- 避免缩写：使用完整单词描述功能

**目录命名**
- 资源目录：`template/`、`thumb/`、`pavilion/`
- 配置目录：`.vscode/`、`.qoder/`
- 工具目录：`tools/`、`test/`
- 文档目录：`doc/`

**文档文件命名**
- 格式：`{python模块名}_{功能描述}_使用说明.md`
- 示例：`auto_register自动类注册_使用说明.md`
- 目的：便于关联Python模块和对应文档

### 2.2 类命名规范

**Blender操作符类**
```python
# 格式：ACA_OT_[功能描述]
class ACA_OT_add_building(bpy.types.Operator):
    bl_idname = "aca.add_newbuilding"  # 格式：aca.[功能名称]
    bl_label = "添加新建筑"
```

**面板类**
```python
# 格式：ACA_PT_[功能描述]
class ACA_PT_basic(bpy.types.Panel):
    bl_category = "筑韵古建"
    bl_label = "基础设置"
```

**数据类**
```python
# 格式：ACA_data_[功能描述]
class ACA_data_scene(bpy.types.PropertyGroup):
    pass

class ACA_data_obj(bpy.types.PropertyGroup):
    pass
```

### 2.3 函数命名规范

**公共函数**
```python
# 动词+名词格式
def update_building(self, context):
    pass

def build_roof_structure():
    pass

def validate_template_data():
    pass
```

**私有函数**
```python
# 双下划线前缀
def __excludeOther():
    pass

def __drawBWQ(fangObj, bwqX, rotZ):
    pass
```

### 2.4 常量命名规范

```python
class ACA_Consts(object):
    # 系统类型常量
    ACA_TYPE_BUILDING = 'building'
    ACA_TYPE_PILLAR = 'pillar'
    
    # 几何参数常量
    DEFAULT_DK = 0.08           # 默认斗口(m)
    PLATFORM_HEIGHT = 2         # 台基高度(PD)
    
    # 材质名称常量
    M_WOOD = '原木'
    M_STONE = '石头'
    
    # 防止修改保护
    def __setattr__(self, name, value):
        raise AttributeError("Can't modify constant values")
```

### 2.5 变量命名规范

```python
# 描述性命名
buildingObj = None          # 建筑对象
pillar_height = 5.0         # 柱高
roof_type = 'xieshan'       # 屋顶类型

# 布尔变量
is_finished = False         # 完成状态
has_error = True            # 错误状态

# 计数变量
template_count = 0          # 模板数量
pillar_index = 0            # 柱索引
```

---

## 3. 代码结构规则

### 3.1 注释与文档规范

> **⚠️ 重要提示**：对于重构和迁移过程中的注释处理（如保留历史注释、迁移废弃代码等），请严格参考 [REFACTOR_FUNCTION_MIGRATION_RULES.md](REFACTOR_FUNCTION_MIGRATION_RULES.md) 中的“注释与内容保真”部分。本节规范主要适用于**新编写的代码**。

- **文档字符串 (Docstring)**：所有公开的类和函数必须包含文档字符串，说明其功能、参数和返回值。
- **复杂逻辑注释**：对于复杂的算法或业务逻辑，应在代码上方添加中文注释进行解释。
- **TODO标记**：使用 `# TODO: [描述]` 标记待完成或待优化的功能。
- **FIXME标记**：使用 `# FIXME: [描述]` 标记已知的问题或需要修复的缺陷。
- **BUG修复注释**：在修复Bug时，必须添加带日期的注释说明。
  - 格式：`# YYMMDD [修改理由]`
  - 示例：`# 260212 修复了空指针异常，增加了空值检查`

### 3.2 文件头部注释规范

```python
# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：[具体功能描述]
# 创建时间：[YYYY-MM-DD]
# 最后修改：[YYYY-MM-DD]
```

### 3.3 类定义结构规范

```python
class ACA_OT_add_building(bpy.types.Operator):
    """添加新建筑操作符"""
    
    # Blender元数据属性
    bl_idname = "aca.add_newbuilding"
    bl_label = "添加新建筑"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '根据选择的样式，自动生成建筑的各个构件'
    
    # 自定义属性
    buildingName: bpy.props.StringProperty(
        name="建筑名称",
        default=''
    ) # type: ignore
    
    def execute(self, context):
        """执行主要逻辑"""
        try:
            # 主要实现逻辑
            result = self._build_process(context)
            return {'FINISHED'}
        except Exception as e:
            # 错误处理
            utils.logError(e)
            return {'CANCELLED'}
    
    def _build_process(self, context):
        """构建过程的具体实现"""
        # 详细实现逻辑
        pass
```

### 3.4 函数定义规范

```python
def update_pillarHeight(self, context: bpy.types.Context):
    """
    更新柱高参数
    
    Args:
        self: 属性拥有者
        context: Blender上下文对象
        
    Returns:
        None
        
    Raises:
        Exception: 构建过程中可能出现的异常
    """
    # 参数验证
    if not context.scene.ACA_data.is_auto_rebuild:
        return
    
    # 主要逻辑
    comboRoot = utils.getComboRoot(context.object)
    if comboRoot is not None:
        # 更新楼阁层高
        buildCombo.__updateFloorLoc(comboRoot)
```

### 3.5 常量类定义规范

```python
class ACA_Consts(object):
    """ACA Builder 常量定义类"""
    
    # 继承object类，提供__setattr__等方法保护
    # 参考：https://www.jb51.net/article/274253.htm
    
    # 系统参数常量
    COLL_NAME_ROOT = 'ACA筑韵古建'
    ACA_TYPE_BUILDING = 'building'
    
    # 几何参数常量（带单位说明）
    DEFAULT_DK = 0.08   # 单位(m)
    PLATFORM_HEIGHT = 2 # 单位(PD)
    
    # 屋顶类型枚举
    ROOF_WUDIAN = '1'           # 庑殿顶
    ROOF_XIESHAN = '2'          # 歇山顶
    ROOF_XUANSHAN = '3'         # 悬山顶
    
    # 防止常量被意外修改
    def __setattr__(self, name, value):
        raise AttributeError("Can't modify constant values")
```



---

## 4. 错误处理规则

### 4.1 异常处理模式

```python
def safe_building_operation():
    """安全的建筑操作函数"""
    try:
        # 显示进度
        build.isFinished = False
        build.progress = 0
        
        # 主要逻辑
        funproxy = partial(build.build)
        result = utils.fastRun(funproxy)
        
        # 成功处理
        if 'FINISHED' in result:
            self._handle_success(result)
            return {'FINISHED'}
            
    except Exception as e:
        # 错误记录和处理
        return self._handle_error(e)
    
    finally:
        # 清理工作
        build.isFinished = True

def _handle_error(self, e):
    """统一错误处理"""
    # 记录到日志文件
    utils.logError(e)
    
    # 用户界面提示
    message = f"插件在运行中发生异常：{str(e)}"
    utils.popMessageBox(message)
    
    # 返回给上层调用
    return {'CANCELLED': e}
```

### 4.2 日志记录规范

```python
import logging
import time

def outputMsg(msg: str):
    """
    格式化输出消息到控制台和日志
    
    Args:
        msg: 要输出的消息内容
    """
    # 控制台格式化输出（带毫秒时间戳）
    timestamp = time.time()
    integer_part = int(timestamp)
    milliseconds = int((timestamp - integer_part) * 100)
    formatted_time = time.strftime("%H:%M:%S", time.localtime(integer_part))
    formatted_time_with_ms = f"{formatted_time}.{milliseconds:02d}"
    
    strout = f"ACA[{formatted_time_with_ms}]: {msg}"
    print(strout)
    
    # 文件日志记录
    logger = logging.getLogger('ACA')
    logger.info(msg)

def logError(e):
    """
    记录错误信息到日志
    
    Args:
        e: 异常对象
    """
    from . import build
    build.isFinished = True
    
    logger = logging.getLogger('ACA')
    logger.error(f"Exception occurred: {e}")
    logger.error(traceback.format_exc())
```

### 4.3 用户反馈机制

```python
def popMessageBox(message="", icon='INFO'):
    """
    弹出模态提示框
    
    Args:
        message: 提示消息内容
        icon: 图标类型 ('INFO', 'ERROR', 'WARNING')
    """
    if message is None:
        message = 'None'
    
    # 同时输出到debug console和日志
    outputMsg(message)
    
    # 调用Blender操作符显示对话框
    bpy.ops.aca.show_message_box(
        'INVOKE_DEFAULT',
        message=message,
        icon=icon,
        center=True
    )
```

---

## 5. UI界面规则

### 5.1 面板类结构规范

```python
class ACA_PT_basic(bpy.types.Panel):
    """营造向导主面板"""
    
    # Blender面板基础属性
    bl_context = "objectmode"       # 关联的上下文
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义面板属性
    bl_category = "筑韵古建"         # 标签页名称
    bl_label = ""                   # 面板名称，在draw_header中写入
    
    def draw_header(self, context):
        """绘制面板头部"""
        from . import bl_info
        ver = f" V{bl_info['version'][0]}.{bl_info['version'][1]}.{bl_info['version'][2]}"
        
        layout = self.layout
        row = layout.row()
        row.label(text='ACA筑韵古建' + ver)
    
    def draw_header_preset(self, context):
        """绘制头部预设按钮"""
        layout = self.layout
        helpbtn = layout.row(align=True)
        op = helpbtn.operator("wm.url_open", icon='HELP', text='')
        op.url = 'https://docs.qq.com/doc/DYXpwbUp1UWR0RXpu'
    
    def draw(self, context):
        """绘制面板主要内容"""
        layout = self.layout
        
        # 版本兼容性检查
        if not self._check_version_compatibility():
            return
        
        # 运行状态检查
        if not self._check_running_status(layout):
            return
        
        # 快速开始提示
        if self._show_quick_start(context):
            self._draw_quick_start(layout)
            return
        
        # 详细设置面板
        self._draw_detailed_settings(layout, context)
```

### 5.2 属性更新机制

```python
def update_dk(self, context: bpy.types.Context):
    """
    斗口参数更新回调函数
    
    Args:
        self: 属性拥有者
        context: Blender上下文
    """
    # 自动重建开关检查
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    # 建筑节点验证
    buildingObj, bData, odata = utils.getRoot(context.object)
    if buildingObj is not None:
        # 更新斗栱数据
        from . import template
        template.updateDougongData(buildingObj)
        # 重建建筑
        update_building(self, context)

def update_pillarHeight(self, context: bpy.types.Context):
    """
    柱高参数更新回调函数
    """
    # 自动重建检查
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    # 楼阁层高更新
    comboRoot = utils.getComboRoot(context.object)
    if comboRoot is not None:
        # 显示进度条
        from . import build
        build.isFinished = False
        build.progress = 0
        
        from . import buildCombo
        buildCombo.__updateFloorLoc(comboRoot)
    
    # 重建当前建筑
    update_building(self, context)
```

### 5.3 UI元素布局规范

```python
def _draw_detailed_settings(self, layout, context):
    """绘制详细设置面板"""
    # 场景数据获取
    scnData: data.ACA_data_scene = context.scene.ACA_data
    box = layout.box()
    
    # 基础参数设置
    col = box.column()
    col.label(text="基础参数", icon='MODIFIER')
    row = col.row()
    row.prop(scnData, "DK", text="斗口尺寸")
    row.prop(scnData, "is_auto_rebuild", text="自动重建")
    
    # 建筑类型选择
    col.separator()
    col.label(text="建筑类型", icon='HOME')
    row = col.row()
    row.prop(scnData, "building_type", expand=True)
    
    # 操作按钮区域
    col.separator()
    row = col.row()
    row.operator("aca.add_newbuilding", icon='ADD')
    row.operator("aca.update_building", icon='FILE_REFRESH')
```

---

## 6. 性能优化规则

### 6.1 集合管理优化

```python
def __excludeOther():
    """
    构建时排除其他集合以提升性能
    """
    # 获取当前场景的所有集合
    collections = bpy.context.scene.collection.children
    
    # 隐藏非当前建筑的集合
    for coll in collections:
        if coll.name != con.COLL_NAME_ROOT:
            coll.hide_viewport = True
            coll.hide_render = True

def __recoverOther():
    """
    构建完成后恢复其他集合显示
    """
    collections = bpy.context.scene.collection.children
    
    # 恢复所有集合显示
    for coll in collections:
        coll.hide_viewport = False
        coll.hide_render = False
```

### 6.2 内存管理优化

```python
def fastRun(func):
    """
    快速运行包装器，优化性能
    
    Args:
        func: 要执行的函数
        
    Returns:
        函数执行结果
    """
    # 保存当前状态
    view_layer_update = _BPyOpsSubModOp._view_layer_update
    _BPyOpsSubModOp._view_layer_update = False
    
    try:
        # 执行函数
        result = func()
        
        # 清理重复材质
        cleanDupMat()
        
        # 清理孤儿数据
        delOrphan()
        
        # 内存回收
        import gc
        gc.collect()
        
        # 恢复渲染设置
        bpy.context.scene.render.use_simplify = False
        bpy.context.scene.render.simplify_subdivision = 6
        
        return result
        
    except Exception as e:
        # 错误处理
        logError(e)
        popMessageBox(f"执行过程中发生错误：{str(e)}")
        return {'CANCELLED': e}
        
    finally:
        # 恢复状态
        _BPyOpsSubModOp._view_layer_update = view_layer_update
```

### 6.3 对象操作优化

```python
def copyObject(sourceObj, name, parentObj=None, 
               location=(0,0,0), rotation=(0,0,0), 
               singleUser=False):
    """
    优化的对象复制函数
    
    Args:
        sourceObj: 源对象
        name: 新对象名称
        parentObj: 父对象
        location: 位置
        rotation: 旋转
        singleUser: 是否创建独立用户数据
        
    Returns:
        复制的对象
    """
    # 数据链接复制
    if singleUser:
        new_obj = sourceObj.copy()
        new_obj.data = sourceObj.data.copy()
    else:
        new_obj = sourceObj.copy()
        new_obj.data = sourceObj.data
    
    # 设置属性
    new_obj.name = name
    new_obj.location = location
    new_obj.rotation_euler = rotation
    
    # 设置父对象
    if parentObj:
        new_obj.parent = parentObj
    
    # 添加到场景
    bpy.context.collection.objects.link(new_obj)
    
    return new_obj
```

---

## 7. 数据管理规则

### 7.1 自定义属性注册规范

```python
def initprop():
    """初始化自定义属性"""
    # 场景级属性
    bpy.types.Scene.ACA_data = bpy.props.PointerProperty(
        type=ACA_data_scene,
        name="古建场景属性集"
    )
    
    bpy.types.Scene.ACA_temp = bpy.props.PointerProperty(
        type=ACA_data_template,
        name="古建场景资产集"
    )
    
    # 对象级属性
    bpy.types.Object.ACA_data = bpy.props.PointerProperty(
        type=ACA_data_obj,
        name="古建构件属性集"
    )
    
    # 模板缩略图控件
    from . import template
    bpy.types.Scene.image_browser_items = bpy.props.CollectionProperty(
        type=TemplateThumbItem
    )
    bpy.types.Scene.image_browser_enum = bpy.props.EnumProperty(
        name="Images",
        items=template.getThumbEnum,
        update=updateSelectedTemplate,
    )

def delprop():
    """销毁自定义属性"""
    # 按相反顺序删除
    del bpy.types.Scene.ACA_data
    del bpy.types.Object.ACA_data
    del bpy.types.Scene.image_browser_items
    del bpy.types.Scene.image_browser_enum
```

### 7.2 数据验证规范

```python
def validate_building_data(buildingObj):
    """
    验证建筑数据完整性
    
    Args:
        buildingObj: 建筑对象
        
    Returns:
        bool: 数据是否有效
    """
    if buildingObj is None:
        return False
    
    # 检查必需属性
    if not hasattr(buildingObj, 'ACA_data'):
        return False
    
    bData = buildingObj.ACA_data
    if not bData:
        return False
    
    # 检查关键参数
    if bData.DK <= 0:
        return False
    
    if not bData.template_name:
        return False
    
    return True

def getRoot(contextObj):
    """
    获取建筑根节点
    
    Args:
        contextObj: 上下文对象
        
    Returns:
        tuple: (buildingObj, bData, objData) 或 (None, None, None)
    """
    if contextObj is None:
        return None, None, None
    
    # 向上追溯到建筑根节点
    current = contextObj
    while current is not None:
        if hasattr(current, 'ACA_data'):
            objData = current.ACA_data
            if objData.type == con.ACA_TYPE_BUILDING:
                bData = current.ACA_data
                return current, bData, objData
        current = current.parent
    
    return None, None, None
```

### 7.3 数据同步机制

```python
def sync_template_data(buildingObj):
    """
    同步模板数据到建筑对象
    
    Args:
        buildingObj: 建筑对象
    """
    if not validate_building_data(buildingObj):
        return
    
    bData = buildingObj.ACA_data
    template_name = bData.template_name
    
    # 从模板加载数据
    from . import template
    template_data = template.getTemplateData(template_name)
    
    if template_data:
        # 同步几何参数
        bData.building_width = template_data.width
        bData.building_depth = template_data.depth
        bData.floor_count = template_data.floors
        
        # 同步构建参数
        bData.roof_type = template_data.roof_type
        bData.has_dougong = template_data.has_dougong
        
        # 触发更新
        update_building(None, bpy.context)
```

---

## 8. 版本兼容规则

### 8.1 Blender版本检查

```python
def _check_version_compatibility(self):
    """检查Blender版本兼容性"""
    # 最低版本要求
    MIN_VERSION = (4, 2, 0)
    
    if bpy.app.version < MIN_VERSION:
        layout = self.layout
        row = layout.row()
        row.label(text=f'本插件无法运行在V{bpy.app.version[0]}.{bpy.app.version[1]}.{bpy.app.version[2]}')
        row = layout.row()
        row.label(text=f'请安装Blender V{MIN_VERSION[0]}.{MIN_VERSION[1]}.{MIN_VERSION[2]}以上')
        row = layout.row()
        op = row.operator("wm.url_open", icon='URL', text='下载Blender')
        op.url = 'https://www.blender.org/download/'
        return False
    
    return True
```

### 8.2 API适配处理

```python
def safe_context_override(context_data):
    """
    安全的上下文覆盖操作
    
    Args:
        context_data: 上下文数据字典
    """
    # Blender 3.2+ 使用 temp_override
    if hasattr(bpy.context, 'temp_override'):
        with bpy.context.temp_override(**context_data):
            yield
    else:
        # 兼容旧版本
        original_context = bpy.context.copy()
        bpy.context.update(context_data)
        try:
            yield
        finally:
            bpy.context.update(original_context)

def safe_operator_call(operator_name, **kwargs):
    """
    安全的操作符调用
    
    Args:
        operator_name: 操作符名称
        **kwargs: 操作符参数
    """
    try:
        # 使用上下文覆盖确保安全调用
        context_override = {
            'area': bpy.context.area,
            'region': bpy.context.region,
            'space': bpy.context.space_data,
        }
        
        with bpy.context.temp_override(**context_override):
            bpy.ops.aca.show_message_box(**kwargs)
            
    except Exception as e:
        print(f"操作符调用失败: {e}")
        # 降级处理
        fallback_message_box(kwargs.get('message', '操作失败'))
```

---

## 9. 国际化考虑

### 9.1 中文编码支持

```python
def init_chinese_support():
    """初始化中文支持"""
    import os
    import sys
    
    # 设置UTF-8编码
    if sys.platform == 'win32':
        os.system("chcp 65001")  # 65001 = UTF-8编码
    
    # 禁用Blender的翻译功能避免命名冲突
    bpy.context.preferences.view.use_translate_new_dataname = False
    
    # 设置控制台编码
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass

def safe_chinese_string(text):
    """
    安全处理中文字符串
    
    Args:
        text: 输入文本
        
    Returns:
        str: 处理后的文本
    """
    if text is None:
        return ""
    
    # 确保字符串编码正确
    if isinstance(text, bytes):
        try:
            return text.decode('utf-8')
        except UnicodeDecodeError:
            return text.decode('gbk', errors='ignore')
    
    return str(text)
```

### 9.2 多语言资源管理

```python
class LanguageManager:
    """语言管理器"""
    
    _translations = {
        'zh_CN': {
            'ADD_BUILDING': '添加新建筑',
            'UPDATE_BUILDING': '更新建筑',
            'BUILDING_COMPLETE': '建筑生成完成',
        },
        'en_US': {
            'ADD_BUILDING': 'Add New Building',
            'UPDATE_BUILDING': 'Update Building',
            'BUILDING_COMPLETE': 'Building Generation Complete',
        }
    }
    
    @classmethod
    def get_text(cls, key, language='zh_CN'):
        """获取本地化文本"""
        return cls._translations.get(language, {}).get(key, key)
    
    @classmethod
    def set_language(cls, language):
        """设置当前语言"""
        # 可以从用户偏好设置中读取
        pass
```

### 9.3 文件路径国际化处理

```python
def get_safe_filepath(filename):
    """
    获取安全的文件路径（处理中文路径）
    
    Args:
        filename: 文件名
        
    Returns:
        str: 安全的文件路径
    """
    import pathlib
    
    # 使用pathlib处理路径
    USER = pathlib.Path(bpy.utils.resource_path('USER'))
    plugin_dir = USER / "scripts/addons/ACA Builder"
    
    # 确保目录存在
    plugin_dir.mkdir(parents=True, exist_ok=True)
    
    # 安全的文件路径组合
    filepath = plugin_dir / filename
    
    # 处理中文路径编码
    try:
        return str(filepath)
    except UnicodeEncodeError:
        # 降级到ASCII路径
        ascii_filename = filename.encode('ascii', 'ignore').decode('ascii')
        return str(plugin_dir / ascii_filename)
```

---

## 附录：最佳实践示例

### 完整的操作符实现示例

```python
class ACA_OT_add_building(bpy.types.Operator):
    """添加新建筑操作符"""
    
    bl_idname = "aca.add_newbuilding"
    bl_label = "添加新建筑"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '根据选择的样式，自动生成建筑的各个构件'
    
    # 操作参数
    template_name: bpy.props.StringProperty(
        name="模板名称",
        default="默认样式"
    ) # type: ignore
    
    def execute(self, context):
        """执行操作"""
        try:
            # 记录开始时间
            import time
            timeStart = time.time()
            
            # 显示进度
            from . import build
            build.isFinished = False
            build.progress = 0
            build.buildStatus = "开始构建..."
            
            # 执行构建
            funproxy = partial(build.build, template_name=self.template_name)
            result = utils.fastRun(funproxy)
            
            # 处理结果
            if 'FINISHED' in result:
                self._report_success(context, timeStart)
                return {'FINISHED'}
            else:
                return result
                
        except Exception as e:
            return self._handle_error(e)
    
    def _report_success(self, context, start_time):
        """报告成功信息"""
        import time
        from . import data
        
        # 获取模板信息
        scnData: data.ACA_data_scene = context.scene.ACA_data
        templateList = scnData.templateItem
        templateIndex = scnData.templateIndex
        templateName = templateList[templateIndex].name if templateList else "未知"
        
        # 计算运行时间
        runTime = time.time() - start_time
        
        # 构造消息
        message = f"从模板样式新建完成！|建筑样式：【{templateName}】 |运行时间：【{runTime:.1f}秒】"
        
        # 显示消息
        utils.popMessageBox(message)
        self.report({'INFO'}, message)
    
    def _handle_error(self, e):
        """处理错误"""
        utils.logError(e)
        message = f"建筑创建失败：{str(e)}"
        utils.popMessageBox(message, icon='ERROR')
        self.report({'ERROR'}, message)
        return {'CANCELLED'}
```

### 完整的面板实现示例

```python
class ACA_PT_props(bpy.types.Panel):
    """建筑属性面板"""
    
    bl_context = "objectmode"
    bl_region_type = 'UI'
    bl_space_type = 'VIEW_3D'
    bl_category = "筑韵古建"
    bl_label = "建筑参数"
    bl_parent_id = "ACA_PT_basic"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        """面板显示条件"""
        # 只在选中建筑对象时显示
        buildingObj, bData, objData = utils.getRoot(context.object)
        return buildingObj is not None
    
    def draw(self, context):
        """绘制面板内容"""
        layout = self.layout
        buildingObj, bData, objData = utils.getRoot(context.object)
        
        if not buildingObj or not bData:
            return
        
        # 基础参数
        box = layout.box()
        col = box.column()
        col.label(text="基础参数", icon='PROPERTIES')
        
        # 斗口设置
        row = col.row()
        row.prop(bData, "DK", text="斗口尺寸(m)")
        row.operator("aca.default_dk", text="", icon='LOOP_BACK')
        
        # 建筑尺寸
        split = col.split(factor=0.5)
        col_left = split.column()
        col_right = split.column()
        
        col_left.prop(bData, "building_width", text="面阔")
        col_left.prop(bData, "building_depth", text="进深")
        col_right.prop(bData, "floor_count", text="层数")
        col_right.prop(bData, "pillar_height", text="柱高")
        
        # 屋顶参数
        box = layout.box()
        col = box.column()
        col.label(text="屋顶参数", icon='HOME')
        col.prop(bData, "roof_type", text="屋顶类型")
        col.prop(bData, "roof_height", text="屋架高度")
        
        # 操作按钮
        col.separator()
        row = col.row()
        row.operator("aca.update_building", icon='FILE_REFRESH')
        row.operator("aca.del_building", icon='X')
```

这套代码规则为ACA Builder项目的开发提供了完整的规范指导，确保代码的一致性、可维护性和专业性。

---

## 10. 代码重构专项规范
函数跨文件迁移的详细规则，请参考：[函数跨文件迁移编码规范](./REFACTOR_FUNCTION_MIGRATION_RULES.md)