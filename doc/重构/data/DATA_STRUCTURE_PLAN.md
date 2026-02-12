# data.py 代码结构优化执行计划

## 1. 目标
重构 `data.py` 文件结构，使其逻辑清晰、阅读顺畅，同时严格遵循 Python 的类依赖顺序（先定义后引用），确保插件运行无误。

## 2. 最终代码顺序

### Section 1: 数据管理的入口 (Entry)
*   `initprop` (注册入口)
*   `delprop` (销毁入口)

### Section 2: 对话框初始数据 (UI & Resources)
#### 2.1 建筑模板列表 (Building Template)
*   `TemplateListItem` (UI列表项)
*   `TemplateThumbItem` (UI缩略图项)

#### 2.2 楼阁模板列表 (Pavilion Template)
*   `ACA_data_pavilion` (楼阁参数)

### Section 3: 场景全局数据 (Scene Settings)
*   `ACA_data_scene` (场景全局开关、视图控制)

### Section 4: 建筑管理数据 (Building Settings)
#### 4.1 单体建筑构件 (Building Components)
*   `ACA_data_taduo` (踏跺)
*   `ACA_data_railing` (栏杆)
*   `ACA_data_wall_common` (墙体基类)
*   `ACA_data_door_common` (门窗基类)
*   `ACA_data_maindoor` (板门)
*   `ACA_data_geshan` (隔扇)

#### 4.2 组合建筑数据 (Combo Building)
*   `ACA_id_list` (组合子对象ID列表)
*   `ACA_data_postProcess` (后处理操作定义)

#### 4.3 建筑主数据 (Building Main Data)
*   `ACA_data_obj` (核心构件数据)
    *   包含：柱网、斗栱、屋顶、瓦作、平坐等核心参数
    *   引用了上述所有部件类、组合类和后处理类

### Section 5: 建筑素材库 (Building Assets)
*   `ACA_data_template` (建筑素材库的引用)
    * 包含各建筑构件的纹理材质引用
    * 包含各建筑构件的几何实体引用

## 3. 执行动作
1.  **重组代码**：依据上述顺序重新排列 `data.py` 中的类定义。
2.  **添加注释**：为每个 Section 添加清晰的分隔注释。
3.  **语法验证**：使用 `py_compile` 验证重构后的文件。
