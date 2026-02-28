# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   自定义数据结构
#   绑定面板控件
#   触发控件数据更新

import bpy
from . import data_callback as dc

#######################################################
### Section 1: 数据管理的入口 (Entry)
# 初始化自定义属性
def initprop():
    # 在scene中添加可全局访问的自定义数据集
    bpy.types.Scene.ACA_data = bpy.props.PointerProperty(
        type=ACA_data_scene,
        name="古建场景属性集"
    )
    bpy.types.Scene.ACA_temp = bpy.props.PointerProperty(
        type=ACA_data_template,
        name="古建场景资产集"
    )
    bpy.types.Object.ACA_data = bpy.props.PointerProperty(
        type=ACA_data_obj,
        name="古建构件属性集"
    )

    # 用于模板缩略图控件的载入
    from . import template
    bpy.types.Scene.image_browser_items = bpy.props.CollectionProperty(
        type=TemplateThumbItem)
    bpy.types.Scene.image_browser_enum = bpy.props.EnumProperty(
        name="Images",
        items=template.getThumbEnum,
        update=dc.updateSelectedTemplate,
    )

    # 用于楼阁缩略图控件的载入
    bpy.types.Scene.pavilion_browser_items = bpy.props.CollectionProperty(
        type=TemplateThumbItem)
    bpy.types.Scene.pavilion_browser_enum = bpy.props.EnumProperty(
        name="pavilion",
        items=template.getPavilionEnum,
        update=dc.updateSelectedPavilion,
    )
    return

# 销毁自定义属性
def delprop():
    del bpy.types.Scene.ACA_data
    del bpy.types.Object.ACA_data
    
    # 用于模板缩略图控件的载入
    del bpy.types.Scene.image_browser_items
    del bpy.types.Scene.image_browser_enum
    del bpy.types.Scene.pavilion_browser_items
    del bpy.types.Scene.pavilion_browser_enum

#######################################################
### Section 2: 对话框初始数据 (UI & Resources)

#### 2.1 建筑模板列表 (Building Template)
# 模板样式列表的行对象，绑定在UI_list上
class TemplateListItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Name", default="Item"
    ) # type: ignore

# 模板缩略图控件对象，绑定在template_view_icon上
class TemplateThumbItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()# type: ignore     
    path: bpy.props.StringProperty()# type: ignore     

#### 2.2 楼阁模板列表 (Pavilion Template)
# 楼阁设置属性集
class ACA_data_pavilion(bpy.types.PropertyGroup):
    # 收分
    taper: bpy.props.FloatProperty(
        name="Pavilion Taper",
        default=0.0
    ) # type: ignore
    # 添加重屋
    use_floor:bpy.props.BoolProperty(
            name = "Add Floor",
            default=True,
        ) # type: ignore
    # 添加平坐
    use_pingzuo:bpy.props.BoolProperty(
            name = "Add Pingzuo",
            default=False,
        ) # type: ignore
    # 回廊宽度
    pingzuo_taper: bpy.props.FloatProperty(
        name="Pingzuo Taper",
        default=0.0
    ) # type: ignore
    # 添加腰檐
    use_mideave:bpy.props.BoolProperty(
            name = "Add Mideave",
            default=True,
        ) # type: ignore
    # 添加栏杆
    use_railing:bpy.props.BoolProperty(
            name = "Add Railing",
            default=False,
        ) # type: ignore
    # 添加回廊
    use_loggia:bpy.props.BoolProperty(
            name = "Add Loggia",
            default=False,
        ) # type: ignore
    # 回廊宽度
    loggia_width: bpy.props.FloatProperty(
        name="Loggia Width",
        default=0.0
    ) # type: ignore
    # 下出平坐
    use_lower_pingzuo:bpy.props.BoolProperty(
        name = "Lower Pingzuo",
        default=False,
    ) # type: ignore

#######################################################
### Section 3: 场景全局数据 (Scene Settings)
# 场景范围的数据
# 可绑定面板参数属性
# 也可做为全局变量访问
# 属性声明的格式在vscode有告警，但blender表示为了保持兼容性，无需更改
# 直接添加“# type:ignore”
# https://blender.stackexchange.com/questions/311578/how-do-you-correctly-add-ui-elements-to-adhere-to-the-typing-spec
class ACA_data_scene(bpy.types.PropertyGroup):
    is_auto_redraw : bpy.props.BoolProperty(
            default = True,
            name = "Auto Redraw",
            description = "Disable to refresh only after building",
        ) # type: ignore
    is_auto_viewall : bpy.props.BoolProperty(
            default = True,
            name = "Auto Viewall",
            description = "Disable to keep current view",
        ) # type: ignore
    is_auto_rebuild : bpy.props.BoolProperty(
            default = True,
            name = "Auto Rebuild",
            description = "Disable to rebuild manually",
        ) # type: ignore
    # template原来提供给模板下拉框使用，现在改为列表，则不再使用该属性
    # template : bpy.props.EnumProperty(
    #         name = "样式列表",
    #         description = "样式列表",
    #         items = getTemplateList,
    #         options = {"ANIMATABLE"},
    #     ) # type: ignore
    templateItem : bpy.props.CollectionProperty(
        type=TemplateListItem)# type: ignore
    templateIndex: bpy.props.IntProperty(
            name="Active List Index",
            default=0, 
            update=dc.updateSelectedThumb,
        )# type: ignore 
    pavilionItem : bpy.props.CollectionProperty(
        type=TemplateListItem)# type: ignore
    pavilionIndex: bpy.props.IntProperty(
            name="Select Pavilion Style",
            description="Select Pavilion Style",
            default=0, 
            update=dc.updateSelectedPavilionThumb,
        )# type: ignore 
    pavilionSetting: bpy.props.PointerProperty(
        type=ACA_data_pavilion,
        name="Pavilion Settings"
    )# type: ignore

#######################################################
### Section 4: 建筑管理数据 (Building Settings)

#### 4.1 单体建筑构件 (Building Components)
# 踏跺属性
class ACA_data_taduo(bpy.types.PropertyGroup):
    id: bpy.props.StringProperty(
            name = 'id',
        ) # type: ignore
    width : bpy.props.FloatProperty(
        name='Step Width',
        description='Step Width Ratio (0.3~1.0)',
        default=1.0,
        max=1.0,
        min=0.3,
        step=10,    # 这里是[n/100],10代表0.1
        update=dc.update_step,
        precision=3,
    ) # type: ignore

# 栏杆属性
class ACA_data_railing(bpy.types.PropertyGroup):
    id: bpy.props.StringProperty(
            name = 'id',
        ) # type: ignore
    gap : bpy.props.FloatProperty(
        name='Railing Gap',
        description='Railing Gap Ratio (0.0~0.9)',
        default=0.0,
        max=0.9,
        min=0.0,
        step=10,    # 这里是[n/100],10代表0.1
        precision=3,
        update=dc.update_railing,
    ) # type: ignore

# 墙体共用属性
class ACA_data_wall_common(bpy.types.PropertyGroup):
    id: bpy.props.StringProperty(
            name = 'id',
        ) # type: ignore
    wall_span : bpy.props.FloatProperty(
            name="Wall Span",
            default=0,
            min=0,
            precision=3,
            description='Height of Zouma Board (0 for None)',
            update=dc.update_wall,
        )# type: ignore 

# 门窗共用属性
class ACA_data_door_common(ACA_data_wall_common):
    doorFrame_width_per : bpy.props.FloatProperty(
            name="Door Frame Width Ratio",
            default=1,
            max=1,
            min=0.1,
            precision=3,
            description='Width Ratio of Door/Window (0.1~1.0)',
            update=dc.update_wall,
        )# type: ignore 
    doorFrame_height : bpy.props.FloatProperty(
            name="Door Frame Height",
            default=3,
            min=0.1,
            precision=3,
            description='Height of Door (Smaller than pillar)',
            update=dc.update_wall,
        )# type: ignore 
    topwin_height : bpy.props.FloatProperty(
            name="Top Window Height",
            default=0,
            precision=3,
            update=dc.update_wall,
            description="Height of Top Window (0 for None)",
        )# type: ignore 
    
# 板门属性
class ACA_data_maindoor(ACA_data_door_common):
    door_num : bpy.props.IntProperty(
            name="Door Number",
            default=2, max=4,step=2,min=2,
            update=dc.update_wall,
            description="Number of Doors (2 or 4)",
        )# type: ignore 
    door_ding_num : bpy.props.IntProperty(
            name="Door Nail Number",
            default=5,
            min=0,max=9,
            update=dc.update_wall,
            description="Number of Door Nails (0~9)",
        )# type: ignore 
    
# 隔扇属性
class ACA_data_geshan(ACA_data_door_common):
    door_num : bpy.props.IntProperty(
            name="Geshan Number",
            default=4, max=6,step=2,min=2,
            update=dc.update_wall,
            description="Number of Geshan (2~6)",
        )# type: ignore 
    gap_num : bpy.props.IntProperty(
            name="Motou Number",
            default=5,min=2,max=6,
            update=dc.update_wall,
            description="Number of Motou (2~6)",
        )# type: ignore 

#### 4.2 组合建筑数据 (Combo Building)
# 子建筑索引列表
class ACA_id_list(bpy.types.PropertyGroup):
    id: bpy.props.StringProperty(
            name = 'id',
        ) # type: ignore
    
# 251205 后处理操作属性
class ACA_data_postProcess(bpy.types.PropertyGroup):
    # 操作类型：如，建筑拼接union
    action:bpy.props.StringProperty(
            name = 'Action',
        ) # type: ignore
    # 操作参数：将多个操作参数拼接成字串，如，"from=building1,to=building2"
    parameter:bpy.props.StringProperty(
            name = 'Parameter',
        ) # type: ignore

#### 4.3 建筑主数据 (Building Main Data)
# 对象范围的数据
# 可绑定面板参数属性
# 属性声明的格式在vscode有告警，但blender表示为了保持兼容性，无需更改
# 直接添加“# type:ignore”
# https://blender.stackexchange.com/questions/311578/how-do-you-correctly-add-ui-elements-to-adhere-to-the-typing-spec
class ACA_data_obj(bpy.types.PropertyGroup):
    # 通用对象属性
    # aca_id是建筑的唯一编号，在生成时随机编号，不会重复
    aca_id : bpy.props.StringProperty(
            name = 'ID',
        ) # type: ignore
    # splice_id拼接编号在拼接时生成，便于后续根据模板生成或更新建筑时自动触发
    splice_id : bpy.props.StringProperty(
            name = 'Building ID'
        ) #type: ignore
    aca_obj : bpy.props.BoolProperty(
            name = 'Is ACA Object',
            default = False
        ) # type: ignore
    aca_type : bpy.props.StringProperty(
            name = 'Object Type',
        ) # type: ignore
    template_name : bpy.props.StringProperty(
            name = 'Template Name'
        ) #type: ignore
    combo_type : bpy.props.StringProperty(
            name = 'Combo Type',
            default = 'combo_main',
        ) # type: ignore
    combo_parent:bpy.props.StringProperty(
            name = 'Combo Parent',
        ) # type: ignore
    combo_children: bpy.props.CollectionProperty(
        type=ACA_id_list, name="Combo Children"
    ) # type: ignore
    combo_location : bpy.props.FloatVectorProperty(
            name = 'Root Location',
            default=(0.0, 0.0, 0.0),
        ) # type: ignore
    combo_rotation : bpy.props.FloatVectorProperty(
            name = 'Root Rotation',
            default=(0.0, 0.0, 0.0),
        ) # type: ignore
    combo_floor_height : bpy.props.FloatProperty(
            name = "Floor Height",
            min = 0.00,
            default= 0.00 ,
            precision=3,
            description="Accumulated Height of Floors",
        ) # type: ignore
    DK: bpy.props.FloatProperty(
            name = "Doukou",
            default=0.0,
            min=0.016,
            max=0.16,
            step=0.01,
            precision=3,
            description="Module Scale (0.016~0.16)",
            update=dc.update_dk
        ) # type: ignore
    is_showPlatform: bpy.props.BoolProperty(
            default = True,
            name = "Show Platform",
            update=dc.hide_platform
        ) # type: ignore
    is_showPillars: bpy.props.BoolProperty(
            default = True,
            name = "Show Pillars",
            update=dc.hide_pillars
        ) # type: ignore
    is_showWalls: bpy.props.BoolProperty(
            default = True,
            name = "Show Walls",
            update=dc.hide_walls
        ) # type: ignore
    is_showDougong: bpy.props.BoolProperty(
            default = True,
            name = "Show Dougong",
            update=dc.hide_dougong
        ) # type: ignore
    is_showBeam: bpy.props.BoolProperty(
            default = True,
            name = "Show Beam",
            update=dc.hide_beam
        ) # type: ignore
    is_showRafter: bpy.props.BoolProperty(
            default = True,
            name = "Show Rafter",
            update=dc.hide_rafter
        ) # type: ignore
    is_showTiles: bpy.props.BoolProperty(
            default = True,
            name = "Show Tiles",
            update=dc.hide_tiles
        ) # type: ignore
    is_showBalcony: bpy.props.BoolProperty(
            default = True,
            name = "Show Balcony",
            update=dc.hide_balcony
        ) # type: ignore
    
    # 台基对象属性
    platform_height : bpy.props.FloatProperty(
            name = "Platform Height",
            min = 0.01, 
            precision=3,
            update=dc.update_platform, # 绑定回调
            description="Height of Platform (1/5 Pillar Height)",
        ) # type: ignore
    platform_extend : bpy.props.FloatProperty(
            name = "Platform Extend",
            precision=3,
            min = 0.01, 
            update=dc.update_platform,    # 绑定回调
            description="Extend of Platform (2.4 Pillar Diameter)",
        ) # type: ignore
    use_terrace: bpy.props.BoolProperty(
            default = False,
            name = "Has Terrace",
        ) # type: ignore
    step_list: bpy.props.CollectionProperty(
        type=ACA_data_taduo, name="Step List"
    ) # type: ignore
    
    # 柱网对象属性
    x_total : bpy.props.FloatProperty(
            name = "Total Width",
            precision=3,
        )# type: ignore
    y_total : bpy.props.FloatProperty(
            name = "Total Depth",
            precision=3,
        )# type: ignore
    x_rooms : bpy.props.IntProperty(
            name = "Rooms X",
            min = 1, 
            # max = 11,
            step = 2,
            update=dc.reset_building,
            description="Odd Number (1~11)",
        )# type: ignore
    x_1 : bpy.props.FloatProperty(
            name = "Room Width 1",
            min = 0, 
            precision=3,
            update=dc.update_building,
            description="Width of Room 1",
        )# type: ignore
    x_2 : bpy.props.FloatProperty(
            name = "Room Width 2",
            min = 0, 
            precision=3,
            update=dc.update_building,
            description="Width of Room 2",
        )# type: ignore
    x_3 : bpy.props.FloatProperty(
            name = "Room Width 3",
            min = 0, 
            precision=3,
            update=dc.update_building,
            description="Width of Room 3",
        )# type: ignore
    x_4 : bpy.props.FloatProperty(
            name = "Room Width 4",
            min = 0, 
            precision=3,
            update=dc.update_building,
            description="Width of Room 4",
        )# type: ignore
    y_rooms : bpy.props.IntProperty(
            name = "Rooms Y",
            #max = 5,
            min = 1, 
            update=dc.reset_building,
            description="Even Number Allowed",
        )# type: ignore
    y_1 : bpy.props.FloatProperty(
            name = "Room Depth 1",
            min = 0, 
            precision=3,
            update=dc.update_building,
            description="Depth of Room 1",
        )# type: ignore
    y_2 : bpy.props.FloatProperty(
            name = "Room Depth 2",
            min = 0, 
            precision=3,
            update=dc.update_building,
            description="Depth of Room 2",
        )# type: ignore
    y_3 : bpy.props.FloatProperty(
            name = "Room Depth 3",
            min = 0, 
            precision=3,
            update=dc.update_building,
            description="Depth of Room 3",
        )# type: ignore
    
    # 柱子属性
    pillar_net : bpy.props.StringProperty(
            name = "Saved Pillar Net"
        )# type: ignore
    pillar_height : bpy.props.FloatProperty(
            name = "Pillar Height",
            default = 0.0,
            min = 0.01, 
            precision=3,
            update=dc.update_pillarHeight,
            description="Height of Eave Pillar",
        )# type: ignore
    pillar_diameter : bpy.props.FloatProperty(
            name = "Pillar Diameter",
            default = 0.0,
            min = 0.01, 
            precision=3,
            # update=dc.update_pillar
            update=dc.update_building,
            description="Diameter of Eave Pillar",
        )# type: ignore
    use_smallfang: bpy.props.BoolProperty(
            default=False,
            name="Double Efang",
            update=dc.update_building,
            description="Use Big/Small Efang",
        )# type: ignore 
    pillar_insert: bpy.props.FloatProperty(
            name = "Pillar Insert Depth",
            default = 0.0,
            min = 0.01, 
            precision=3,
            description="Depth of Pillar Insertion",
        )# type: ignore
    
    
    # 墙体属性
    railing_list: bpy.props.CollectionProperty(
        type=ACA_data_railing, name="Railing List"
    ) # type: ignore
    maindoor_list: bpy.props.CollectionProperty(
        type=ACA_data_maindoor, name="Main Door List"
    ) # type: ignore
    wall_list: bpy.props.CollectionProperty(
        type=ACA_data_wall_common, name="Wall List"
    ) # type: ignore
    window_list: bpy.props.CollectionProperty(
        type=ACA_data_door_common, name="Window List"
    ) # type: ignore
    geshan_list: bpy.props.CollectionProperty(
        type=ACA_data_geshan, name="Geshan List"
    ) # type: ignore 
    paint_style : bpy.props.EnumProperty(
            name = "Paint Style",
            description = "Switch Paint Style",
            items = [
                ("0","清-和玺彩画",""),
                ("1","酱油色",""),
                ("2","白模",""),
                ("3","红漆无彩画",""),
            ],
            update=dc.update_building,
            options = {"ANIMATABLE"}
        ) # type: ignore
    use_balcony_railing :  bpy.props.BoolProperty(
            default=False,
            name="Use Balcony Railing",
            update=dc.update_dougong,
            description="Add Railing around Balcony",
        )# type: ignore 
    
    # 斗栱属性
    use_dg :  bpy.props.BoolProperty(
            default=False,
            name="Use Dougong",
            update=dc.update_dougong,
            description="Dougong is optional for small buildings",
        )# type: ignore 
    use_pingbanfang: bpy.props.BoolProperty(
            default=True,
            name="Use Pingbanfang",
            update=dc.update_dougong,
            description="Board between Pillar and Dougong",
        )# type: ignore 
    dg_style : bpy.props.EnumProperty(
            name = "Dougong Style",
            description = "Dougong Style based on Building Level",
            items=dc.getDougongList,
            options = {"ANIMATABLE"},
            update=dc.update_dougong,
            default=0,
        ) # type: ignore
    dg_extend : bpy.props.FloatProperty(
            name="Dougong Extend",    # 令拱出跳距离
            default=0.45,
            description = "Extend of Dougong (Defined by Template)",
            min=0.01,
            precision=3,
        )# type: ignore 
    dg_height : bpy.props.FloatProperty(
            name="Dougong Height",    # 取挑檐桁下皮高度
            default=1.0,
            precision=3,
        )# type: ignore 
    dg_scale:bpy.props.FloatVectorProperty(
            name="Dougong Scale",    # 斗栱缩放
            default=(1,1,1),
            precision=3,
        )# type: ignore 
    dk_scale:bpy.props.FloatProperty(
            name="Doukou Scale",    # 斗栱间距
            description = "Scale of Dougong Gap",
            default=1,
            precision=3,
            min=0.5,
            max=2.5,
            update=dc.update_dougong,
        )# type: ignore 
    dg_gap:bpy.props.FloatProperty(
            name="Dougong Gap",    # 斗栱间距
            description = "Gap of Dougong (11 Doukou)",
            default=0.99,
            precision=3,
            min=0.1,
            update=dc.update_dougong,
        )# type: ignore 
    dg_withbeam:bpy.props.BoolProperty(
            name="Dougong with Beam",    # 斗栱间距
            description = "Dougong contains Beam",
            default=True,
        )# type: ignore 
    
    # 屋顶属性
    roof_style : bpy.props.EnumProperty(
            name = "Roof Style",
            items = [
                ("0","",""),
                ("1","庑殿顶",""),
                ("2","歇山顶",""),
                ("3","悬山顶",""),
                ("4","硬山顶",""),
                ('5',"盝顶",""),
                ("6","悬山卷棚顶",""),
                ('7',"硬山卷棚顶",""),
                ('8','歇山卷棚顶',""),
                ('9','平坐',""),
            ],
            #update=dc.update_roof,
            update=dc.update_roofstyle,
            description="Select Roof Style",
        ) # type: ignore
    use_double_eave: bpy.props.BoolProperty(
            default=False,
            name="Use Double Eave",
            update=dc.update_roof,
            description="Use Double Eave Roof",
        )# type: ignore 
    use_hallway : bpy.props.BoolProperty(
            default=False,
            name="Use Hallway",
            update=dc.update_building,
            description="Raise Gold Pillar for Hallway",
        )# type: ignore 
    rafter_count : bpy.props.IntProperty(
            name="Rafter Count",
            default=8,
            min=2,max=9,
            update=dc.update_roof,
            description="Number of Rafters (2~9)",
        )# type: ignore 
    use_flyrafter :  bpy.props.BoolProperty(
            default=True,
            name="Use Fly Rafter",
            update=dc.update_roof,
            description="Fly Rafter for Eave",
        )# type: ignore 
    use_wangban :  bpy.props.BoolProperty(
            default=True,
            name="Use Wangban",
            update=dc.update_roof,
            description="Add Wangban",
        )# type: ignore 
    qiqiao: bpy.props.FloatProperty(
            name="Qiqiao (Rafter Diameter)",
            default=4, 
            min=0,
            update=dc.update_roof,
            description="Qiqiao (Usually 4)",
        )# type: ignore 
    chong: bpy.props.FloatProperty(
            name="Chong (Rafter Diameter)",
            default=3,
            min=0, 
            update=dc.update_roof,
            description="Chong (Usually 3)",
        )# type: ignore 
    use_pie: bpy.props.BoolProperty(
            name="Use Pie",
            default=True,
            update=dc.update_roof,
            description="Use Pie for Eave",
    )# type: ignore
    shengqi: bpy.props.IntProperty(
            name="Shengqi (Rafter Diameter)",
            default=1, 
            update=dc.update_roof
        )# type: ignore 
    liangtou: bpy.props.FloatProperty(
            name="Liangtou Position", 
            default=0.5,
            min=0,
            max=1.0,
            precision=3,
            update=dc.update_roof,
            description="Position of Liangtou (0.0~1.0)"
        )# type: ignore
    tuishan: bpy.props.FloatProperty(
            name="Tuishan Factor", 
            default=0.9,
            min=0.1,
            max=1.0,
            precision=3,
            update=dc.update_roof,
            description="Factor of Tuishan (0.1~1.0)"
        )# type: ignore
    shoushan: bpy.props.FloatProperty(
            name="Shoushan Size", 
            default=2,
            min=0,
            max=2,
            precision=3,
            update=dc.update_roof,
            description="Size of Shoushan (0~2)"
        )# type: ignore
    luding_rafterspan:bpy.props.FloatProperty(
            name="Luding Eave Span", 
            default=3,
            min=0.01,
            max=6,
            precision=3,
            update=dc.update_roof,
            description="Span of Luding Eave"
        )# type: ignore
    juzhe : bpy.props.EnumProperty(
            name = "Juzhe Factor",
            items = [
                ("0","   举折系数：默认","[0.5,0.7,0.8,0.9]"),
                ("1","   举折系数：陡峭","[0.5,1,1.5,2]，慎用，一般用于亭子等建筑"),
                ("2","   举折系数：平缓","[0.5,0.65,0.75,0.9]"),
                ("3","   举折系数：按屋架高度推算","根据输入屋架高度，进行举折计算")
            ],
            description="Curvature of Roof",
            update=dc.update_juzhe,
        ) # type: ignore
    roof_height:bpy.props.FloatProperty(
            name="Roof Height", 
            default=3,
            min=0.01,
            max=10,
            precision=3,
            update=dc.update_roof,
            description="Height from Zhengxin to Ridge"
        )# type: ignore
    roof_qiao_point : bpy.props.FloatVectorProperty(
        name="Qiao Reference Point",
        subtype='XYZ',
        unit='LENGTH',
        )# type: ignore 
    
    # 瓦作属性
    # 250616 添加瓦作缩放因子
    tile_scale:bpy.props.FloatProperty(
            name="Tile Scale",    # 瓦作缩放
            default=1.0,
            min=0.5,max=2.0,
            precision=2,
            description="Scale of Tiles (0.5~2.0)",
            update=dc.update_building,
        )# type: ignore
    tile_color : bpy.props.EnumProperty(
            name = "Tile Color",
            items = [
                ("0","黄琉璃",""),
                ("1","绿琉璃",""),
                ("2","灰琉璃",""),
                ("3","蓝琉璃",""),
                ("4","紫琉璃",""),
            ],
        ) # type: ignore
    tile_alt_color : bpy.props.EnumProperty(
            name = "Tile Alt Color",
            items = [
                ("0","黄琉璃",""),
                ("1","绿琉璃",""),
                ("2","灰琉璃",""),
                ("3","蓝琉璃",""),
                ("4","紫琉璃",""),
            ],
        ) # type: ignore
    tile_width : bpy.props.FloatProperty(
            name="Tile Width", 
            default=0.4,
            min=0.0,
            precision=3,
        )# type: ignore
    tile_width_real : bpy.props.FloatProperty(
            name="Tile Real Width", 
            precision=3,
        )# type: ignore
    tile_length : bpy.props.FloatProperty(
            name="Tile Length", 
            default=0.4,
            min=0.0,
            precision=3,
        )# type: ignore
    
    # 屋脊属性
    paoshou_count:bpy.props.IntProperty(
            name = 'Paoshou Count',
            default=6,
            min=0,
            max=10,
            update=dc.update_rooftile,
            description="Number of Paoshou",
        )# type: ignore 
    
    # 院墙属性
    is_4_sides:bpy.props.BoolProperty(
            default = True,
            name = "Is 4 Sides",
            description="Generate 4 Walls",
        ) # type: ignore
    yard_width :bpy.props.FloatProperty(
            name="Yard Width",
            default=40,
            precision=3,
            min=1,
            description="Length of Wall",
            update=dc.update_yardwall,
        )# type: ignore 
    yard_depth :bpy.props.FloatProperty(
            name="Yard Depth",
            default=30,
            precision=3,
            min=1,
            description="Depth of Yard (4 Sides Only)",
            update=dc.update_yardwall,
        )# type: ignore
    yardwall_height:bpy.props.FloatProperty(
            name="Yard Wall Height",
            default=3,
            precision=3,
            min=1,
            description="Height of Wall (No Cap)",
            update=dc.update_yardwall,
        )# type: ignore
    yardwall_depth:bpy.props.FloatProperty(
            name="Yard Wall Depth",
            default=1,
            precision=3,
            min=0.5,
            description="Depth of Wall (No Cap)",
            update=dc.update_yardwall,
        )# type: ignore
    yardwall_angle:bpy.props.FloatProperty(
            name="Yard Wall Angle",
            default=30,
            precision=3,
            min=0,
            max=45,
            description="Angle of Cap (0~45)",
            update=dc.update_yardwall,
        )# type: ignore  
    
    # 251112 回廊标识
    loggia_sign : bpy.props.StringProperty(
            name = "Loggia Sign"
        )# type: ignore
    
    # 251117 举折系数
    juzhe_var :bpy.props.FloatProperty(
            name="Juzhe Variable",
            default=0.1,
            precision=3,
            min=0.1,
            max=0.3,
            update=dc.update_roof,
            description="Variable Juzhe (0.1~0.3)",
        )# type: ignore
    
    # 251205 后处理操作列表
    postProcess: bpy.props.CollectionProperty(
        type=ACA_data_postProcess, name="Post Process List"
    ) # type: ignore

#######################################################
### Section 5: 建筑素材库 (Building Assets)
# 全局共用的模板信息，各个建筑都进行引用
# 包括资产库资产引用等    
class ACA_data_template(bpy.types.PropertyGroup):
    # 材质对象
    mat_override:bpy.props.PointerProperty(
            name = "UVgrid",
            type = bpy.types.Object,
        )# type: ignore 
    mat_wood:bpy.props.PointerProperty(
            name = "Mat Wood",
            type = bpy.types.Object,
        )# type: ignore 
    mat_rock:bpy.props.PointerProperty(
            name = "Mat Rock",
            type = bpy.types.Object,
        )# type: ignore 
    mat_stone:bpy.props.PointerProperty(
            name = "Mat Stone",
            type = bpy.types.Object,
        )# type: ignore 
    mat_oilpaint:bpy.props.PointerProperty(
            name = "Mat Oilpaint",
            type = bpy.types.Object,
        )# type: ignore 
    mat_gold:bpy.props.PointerProperty(
            name = "Mat Gold",
            type = bpy.types.Object,
        )# type: ignore 
    mat_green:bpy.props.PointerProperty(
            name = "Mat Green",
            type = bpy.types.Object,
        )# type: ignore 
    mat_brick_1:bpy.props.PointerProperty(
            name = "Mat Brick 1",
            type = bpy.types.Object,
        )# type: ignore 
    mat_brick_2:bpy.props.PointerProperty(
            name = "Mat Brick 2",
            type = bpy.types.Object,
        )# type: ignore 
    mat_brick_3:bpy.props.PointerProperty(
            name = "Mat Brick 3",
            type = bpy.types.Object,
        )# type: ignore 
    mat_dust_wall:bpy.props.PointerProperty(
            name = "Mat Dust Wall",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_beam_big :bpy.props.PointerProperty(
            name = "Mat Paint Beam Big",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_beam_small :bpy.props.PointerProperty(
            name = "Mat Paint Beam Small",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_pillarhead :bpy.props.PointerProperty(
            name = "Mat Paint Pillarhead",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_walkdragon :bpy.props.PointerProperty(
            name = "Mat Paint Walkdragon",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_grasscouple :bpy.props.PointerProperty(
            name = "Mat Paint Grasscouple",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_dgfillboard :bpy.props.PointerProperty(
            name = "Mat Paint Dougong Fill",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_dgfillboard_s :bpy.props.PointerProperty(
            name = "Mat Paint Dougong Fill S",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_rafter : bpy.props.PointerProperty(
            name = "Mat Paint Rafter",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_flyrafter : bpy.props.PointerProperty(
            name = "Mat Paint Fly Rafter",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_wangban: bpy.props.PointerProperty(
            name = "Mat Paint Wangban",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_cloud: bpy.props.PointerProperty(
            name = "Mat Paint Cloud",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_tuanend: bpy.props.PointerProperty(
            name = "Mat Paint Tuanend",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_ccb : bpy.props.PointerProperty(
            name = "Mat Paint CCB",
            type = bpy.types.Object,
        )# type: ignore
    mat_paint_door : bpy.props.PointerProperty(
            name = "Mat Paint Door",
            type = bpy.types.Object,
        )# type: ignore
    mat_paint_doorring : bpy.props.PointerProperty(
            name = "绦环板",
            type = bpy.types.Object,
        )# type: ignore
    mat_paint_shanhua : bpy.props.PointerProperty(
            name = "山花板",
            type = bpy.types.Object,
        )# type: ignore
    mat_geshanxin : bpy.props.PointerProperty(
            name = "三交六椀隔心",
            type = bpy.types.Object,
        )# type: ignore    
    mat_geshanxin_wan : bpy.props.PointerProperty(
            name = "万字锦棂心",
            type = bpy.types.Object,
        )# type: ignore    
    mat_ccfang : bpy.props.PointerProperty(
            name = "穿插枋",
            type = bpy.types.Object,
        )# type: ignore  
    mat_cornerbeam : bpy.props.PointerProperty(
            name = "老角梁",
            type = bpy.types.Object,
        )# type: ignore  
    mat_queti : bpy.props.PointerProperty(
            name = "雀替",
            type = bpy.types.Object,
        )# type: ignore  
    mat_dougong : bpy.props.PointerProperty(
            name = "斗栱",
            type = bpy.types.Object,
        )# type: ignore  
    mat_guayanban : bpy.props.PointerProperty(
            name = "挂檐板",
            type = bpy.types.Object,
        )# type: ignore 
    
    # 柱对象
    pillar_source : bpy.props.PointerProperty(
            name = "柱样式",
            type = bpy.types.Object,
        )# type: ignore
    pillar_lift_source : bpy.props.PointerProperty(
            name = "垂花柱样式",
            type = bpy.types.Object,
        )# type: ignore
    pillarbase_source : bpy.props.PointerProperty(
            name = "柱础样式",
            type = bpy.types.Object,
        )# type: ignore
    
    # 棂心对象
    lingxin_source:bpy.props.PointerProperty(
            name = "棂心",
            type = bpy.types.Object,
            update=dc.update_wall
        )# type: ignore 
    
    # 斗栱对象
    dg_pillar_source:bpy.props.PointerProperty(
            name = "柱头斗栱",
            type = bpy.types.Object,
        )# type: ignore 
    dg_fillgap_source:bpy.props.PointerProperty(
            name = "补间斗栱",
            type = bpy.types.Object,
        )# type: ignore 
    dg_fillgap_alt_source:bpy.props.PointerProperty(
            name = "补间斗栱-异色",
            type = bpy.types.Object,
        )# type: ignore 
    dg_corner_source:bpy.props.PointerProperty(
            name = "转角斗栱",
            type = bpy.types.Object,
        )# type: ignore 
    dg_balcony_pillar_source:bpy.props.PointerProperty(
            name = "平坐柱头斗栱",
            type = bpy.types.Object,
        )# type: ignore 
    dg_balcony_corner_source:bpy.props.PointerProperty(
            name = "平坐转角斗栱",
            type = bpy.types.Object,
        )# type: ignore 
    dg_balcony_fillgap_source:bpy.props.PointerProperty(
            name = "平坐补间斗栱",
            type = bpy.types.Object,
        )# type: ignore 
    dg_balcony_fillgap_alt_source:bpy.props.PointerProperty(
            name = "平坐补间斗栱-异色",
            type = bpy.types.Object,
        )# type: ignore 
    
    # 博缝板对象
    bofeng_source : bpy.props.PointerProperty(
            name = "博缝板",
            type = bpy.types.Object,
        )# type: ignore
    
    # 老角梁对象
    cornerbeam_source : bpy.props.PointerProperty(
            name = "老角梁",
            type = bpy.types.Object,
        )# type: ignore
    
    # 霸王拳对象
    bawangquan_source : bpy.props.PointerProperty(
            name = "霸王拳",
            type = bpy.types.Object,
        )# type: ignore
    
    # 雀替对象
    queti_source : bpy.props.PointerProperty(
            name = "雀替",
            type = bpy.types.Object,
        )# type: ignore
    
    # 穿插枋对象
    ccfang_source : bpy.props.PointerProperty(
            name = "穿插枋",
            type = bpy.types.Object,
        )# type: ignore
    
    # 琉璃瓦对象
    flatTile_source:bpy.props.PointerProperty(
            name = "板瓦",
            type = bpy.types.Object,
        )# type: ignore 
    circularTile_source:bpy.props.PointerProperty(
            name = "筒瓦",
            type = bpy.types.Object,
        )# type: ignore 
    eaveTile_source:bpy.props.PointerProperty(
            name = "瓦当",
            type = bpy.types.Object,
        )# type: ignore 
    dripTile_source:bpy.props.PointerProperty(
            name = "滴水",
            type = bpy.types.Object,
        )# type: ignore 
    
    # 屋脊对象
    ridgeTop_source:bpy.props.PointerProperty(
            name = "正脊筒",
            type = bpy.types.Object,
        )# type: ignore 
    ridgeBack_source:bpy.props.PointerProperty(
            name = "垂脊兽后",
            type = bpy.types.Object,
        )# type: ignore 
    ridgeFront_source:bpy.props.PointerProperty(
            name = "垂脊兽前",
            type = bpy.types.Object,
        )# type: ignore 
    ridgeEnd_source:bpy.props.PointerProperty(
            name = "端头盘子",
            type = bpy.types.Object,
        )# type: ignore 
    chiwen_source:bpy.props.PointerProperty(
            name = "螭吻",
            type = bpy.types.Object,
        )# type: ignore 
    hejiaowen_source:bpy.props.PointerProperty(
            name = "合角吻",
            type = bpy.types.Object,
        )# type: ignore 
    baoding_source:bpy.props.PointerProperty(
            name = "宝顶",
            type = bpy.types.Object,
        )# type: ignore 
    chuishou_source:bpy.props.PointerProperty(
            name = "垂兽",
            type = bpy.types.Object,
        )# type: ignore 
    taoshou_source:bpy.props.PointerProperty(
            name = "套兽",
            type = bpy.types.Object,
        )# type: ignore 
    
    # 跑兽对象
    paoshou_0_source:bpy.props.PointerProperty(
            name = "仙人",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_1_source:bpy.props.PointerProperty(
            name = "龙",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_2_source:bpy.props.PointerProperty(
            name = "凤",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_3_source:bpy.props.PointerProperty(
            name = "狮子",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_4_source:bpy.props.PointerProperty(
            name = "海马",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_5_source:bpy.props.PointerProperty(
            name = "天马",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_6_source:bpy.props.PointerProperty(
            name = "狎鱼",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_7_source:bpy.props.PointerProperty(
            name = "狻猊",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_8_source:bpy.props.PointerProperty(
            name = "獬豸",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_9_source:bpy.props.PointerProperty(
            name = "斗牛",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_10_source:bpy.props.PointerProperty(
            name = "行什",
            type = bpy.types.Object,
        )# type: ignore     
    walleave:bpy.props.PointerProperty(
            name = "墙檐",
            type = bpy.types.Object,
        )# type: ignore     
    door_pushou:bpy.props.PointerProperty(
            name = "铺首",
            type = bpy.types.Object,
        )# type: ignore     
    door_ding:bpy.props.PointerProperty(
            name = "门钉",
            type = bpy.types.Object,
        )# type: ignore     
    door_zan:bpy.props.PointerProperty(
            name = "门簪",
            type = bpy.types.Object,
        )# type: ignore 
    railing_pillar:bpy.props.PointerProperty(
            name = "栏杆望柱",
            type = bpy.types.Object,
        )# type: ignore 
    railing_vase:bpy.props.PointerProperty(
            name = "栏杆净瓶",
            type = bpy.types.Object,
        )# type: ignore 
    xuanyu_source:bpy.props.PointerProperty(
            name = "悬鱼",
            type = bpy.types.Object,
        )# type: ignore 
    