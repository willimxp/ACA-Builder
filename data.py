# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   自定义数据结构
#   绑定面板控件
#   触发控件数据更新

import bpy
from . import data_callback as dc
from .locale.i18n import T

#######################################################
### Section 1: 数据管理的入口 (Entry)
# 初始化自定义属性
def initprop():
    # 在scene中添加可全局访问的自定义数据集
    bpy.types.Scene.ACA_data = bpy.props.PointerProperty(
        type=ACA_data_scene,
        name=T("古建场景属性集")
    )
    bpy.types.Scene.ACA_temp = bpy.props.PointerProperty(
        type=ACA_data_template,
        name=T("古建场景资产集")
    )
    bpy.types.Object.ACA_data = bpy.props.PointerProperty(
        type=ACA_data_obj,
        name=T("古建构件属性集")
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
        name=T("重楼收分"),
        default=0.0
    ) # type: ignore
    # 添加重屋
    use_floor:bpy.props.BoolProperty(
            name = T("添加重屋"),
            default=True,
        ) # type: ignore
    # 添加平坐
    use_pingzuo:bpy.props.BoolProperty(
            name = T("添加平坐"),
            default=False,
        ) # type: ignore
    # 回廊宽度
    pingzuo_taper: bpy.props.FloatProperty(
        name=T("平坐收分"),
        default=0.0
    ) # type: ignore
    # 添加腰檐
    use_mideave:bpy.props.BoolProperty(
            name = T("添加腰檐"),
            default=True,
        ) # type: ignore
    # 添加栏杆
    use_railing:bpy.props.BoolProperty(
            name = T("添加栏杆"),
            default=False,
        ) # type: ignore
    # 添加回廊
    use_loggia:bpy.props.BoolProperty(
            name = T("添加回廊"),
            default=False,
        ) # type: ignore
    # 回廊宽度
    loggia_width: bpy.props.FloatProperty(
        name=T("回廊宽度"),
        default=0.0
    ) # type: ignore
    # 下出平坐
    use_lower_pingzuo:bpy.props.BoolProperty(
        name = T("下出平坐"),
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
            name = T("是否实时重绘"),
            description = T("取消后，生成过程中不进行刷新，直到全部生成后才显示"),
        ) # type: ignore
    is_auto_viewall : bpy.props.BoolProperty(
            default = True,
            name = T("是否设置视角"),
            description = T("取消后，不再自动切换视角，始终保持当前视角"),
        ) # type: ignore
    is_auto_rebuild : bpy.props.BoolProperty(
            default = True,
            name = T("是否实时重建"),
            description = T("取消后，在大部分参数修改时，不会自动重建，直到手工点击更新建筑"),
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
            name=T("Active List Index"),
            default=0, 
            update=dc.updateSelectedThumb,
        )# type: ignore 
    pavilionItem : bpy.props.CollectionProperty(
        type=TemplateListItem)# type: ignore
    pavilionIndex: bpy.props.IntProperty(
            name=T("请选择上出楼阁的做法"),
            description=T("请选择上出楼阁的做法"),
            default=0, 
            update=dc.updateSelectedPavilionThumb,
        )# type: ignore 
    pavilionSetting: bpy.props.PointerProperty(
        type=ACA_data_pavilion,
        name=T("楼阁设置")
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
        name=T('踏跺宽度'),
        description=T('踏跺在开间内的比例，最大为1，最小为0.3'),
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
        name=T('开口宽度'),
        description=T('在开间内开口的比例，设置为0时不做开口，最大为0.9'),
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
            name=T("走马板高度"),
            default=0,
            min=0,
            precision=3,
            description=T('重檐时，装修不做到柱头，用走马板填充，输入0则不做走马板'),
            update=dc.update_wall,
        )# type: ignore 

# 门窗共用属性
class ACA_data_door_common(ACA_data_wall_common):
    doorFrame_width_per : bpy.props.FloatProperty(
            name=T("门口宽比"),
            default=1,
            max=1,
            min=0.1,
            precision=3,
            description=T('开间中的门口/窗口宽度比例，小于1则开间的部分做余塞板，不可大于1'),
            update=dc.update_wall,
        )# type: ignore 
    doorFrame_height : bpy.props.FloatProperty(
            name=T("门口高度"),
            default=3,
            min=0.1,
            precision=3,
            description=T('开间中的门口高度，小于柱高的空间将自动布置横披窗/迎风板'),
            update=dc.update_wall,
        )# type: ignore 
    topwin_height : bpy.props.FloatProperty(
            name=T("横披窗高度"),
            default=0,
            precision=3,
            update=dc.update_wall,
            description=T("横披窗（棂心）的高度，输入0则不做横披窗"),
        )# type: ignore 
    
# 板门属性
class ACA_data_maindoor(ACA_data_door_common):
    door_num : bpy.props.IntProperty(
            name=T("板门数量"),
            default=2, max=4,step=2,min=2,
            update=dc.update_wall,
            description=T("板门可以做2扇，也可以做4扇"),
        )# type: ignore 
    door_ding_num : bpy.props.IntProperty(
            name=T("门钉数量"),
            default=5,
            min=0,max=9,
            update=dc.update_wall,
            description=T("门钉的路数，最大9路，取0时不做门钉"),
        )# type: ignore 
    
# 隔扇属性
class ACA_data_geshan(ACA_data_door_common):
    door_num : bpy.props.IntProperty(
            name=T("隔扇数量"),
            default=4, max=6,step=2,min=2,
            update=dc.update_wall,
            description=T("一般做4扇隔扇"),
        )# type: ignore 
    gap_num : bpy.props.IntProperty(
            name=T("抹头数量"),
            default=5,min=2,max=6,
            update=dc.update_wall,
            description=T("2~6抹头都可以，根据需要自由设置"),
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
            name = T('Action'),
        ) # type: ignore
    # 操作参数：将多个操作参数拼接成字串，如，"from=building1,to=building2"
    parameter:bpy.props.StringProperty(
            name = T('Parameter'),
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
            name = T('建筑ID')
        ) #type: ignore
    aca_obj : bpy.props.BoolProperty(
            name = T('是ACA对象'),
            default = False
        ) # type: ignore
    aca_type : bpy.props.StringProperty(
            name = T('对象类型'),
        ) # type: ignore
    template_name : bpy.props.StringProperty(
            name = T('模板名称')
        ) #type: ignore
    combo_type : bpy.props.StringProperty(
            name = T('组合类型'),
            default = 'combo_main',
        ) # type: ignore
    combo_parent:bpy.props.StringProperty(
            name = T('组合关联对象'),
        ) # type: ignore
    combo_children: bpy.props.CollectionProperty(
        type=ACA_id_list, name=T("组合关联子对象")
    ) # type: ignore
    combo_location : bpy.props.FloatVectorProperty(
            name = T('根节点位移'),
            default=(0.0, 0.0, 0.0),
        ) # type: ignore
    combo_rotation : bpy.props.FloatVectorProperty(
            name = T('根节点旋转'),
            default=(0.0, 0.0, 0.0),
        ) # type: ignore
    combo_floor_height : bpy.props.FloatProperty(
            name = T("重楼高度"),
            min = 0.00,
            default= 0.00 ,
            precision=3,
            description=T("累计重楼的root高度"),
        ) # type: ignore
    DK: bpy.props.FloatProperty(
            name = T("斗口"),
            default=0.0,
            min=0.016,
            max=0.16,
            step=0.01,
            precision=3,
            description=T("比例模数(m)，清官式常用0.08(二寸半)、0.096(三寸)等"),
            update=dc.update_dk
        ) # type: ignore
    is_showPlatform: bpy.props.BoolProperty(
            default = True,
            name = T("是否显示台基"),
            update=dc.hide_platform
        ) # type: ignore
    is_showPillars: bpy.props.BoolProperty(
            default = True,
            name = T("是否显示柱网"),
            update=dc.hide_pillars
        ) # type: ignore
    is_showWalls: bpy.props.BoolProperty(
            default = True,
            name = T("是否显示墙体"),
            update=dc.hide_walls
        ) # type: ignore
    is_showDougong: bpy.props.BoolProperty(
            default = True,
            name = T("是否显示斗栱"),
            update=dc.hide_dougong
        ) # type: ignore
    is_showBeam: bpy.props.BoolProperty(
            default = True,
            name = T("是否显示梁架"),
            update=dc.hide_beam
        ) # type: ignore
    is_showRafter: bpy.props.BoolProperty(
            default = True,
            name = T("是否显示椽望"),
            update=dc.hide_rafter
        ) # type: ignore
    is_showTiles: bpy.props.BoolProperty(
            default = True,
            name = T("是否显示瓦作"),
            update=dc.hide_tiles
        ) # type: ignore
    is_showBalcony: bpy.props.BoolProperty(
            default = True,
            name = T("是否显示平坐"),
            update=dc.hide_balcony
        ) # type: ignore
    
    # 台基对象属性
    platform_height : bpy.props.FloatProperty(
            name = T("台基高度"),
            min = 0.01, 
            precision=3,
            update=dc.update_platform, # 绑定回调
            description=T("一般为柱高的1/5，或2柱径"),
        ) # type: ignore
    platform_extend : bpy.props.FloatProperty(
            name = T("台基下出"),
            precision=3,
            min = 0.01, 
            update=dc.update_platform,    # 绑定回调
            description=T("檐柱的2.4倍，或上出檐的3/4~4/5"),
        ) # type: ignore
    use_terrace: bpy.props.BoolProperty(
            default = False,
            name = T("是否有月台"),
        ) # type: ignore
    step_list: bpy.props.CollectionProperty(
        type=ACA_data_taduo, name=T("踏跺列表")
    ) # type: ignore
    
    # 柱网对象属性
    x_total : bpy.props.FloatProperty(
            name = T("通面阔"),
            precision=3,
        )# type: ignore
    y_total : bpy.props.FloatProperty(
            name = T("通进深"),
            precision=3,
        )# type: ignore
    x_rooms : bpy.props.IntProperty(
            name = T("面阔间数"),
            min = 1, 
            # max = 11,
            step = 2,
            update=dc.reset_building,
            description=T("必须为奇数，建议最多不超过11间"),
        )# type: ignore
    x_1 : bpy.props.FloatProperty(
            name = T("明间宽度"),
            min = 0, 
            precision=3,
            update=dc.update_building,
            description=T("常取7攒斗栱，且一般柱不越间广（柱高小于明间宽度）"),
        )# type: ignore
    x_2 : bpy.props.FloatProperty(
            name = T("次间宽度"),
            min = 0, 
            precision=3,
            update=dc.update_building,
            description=T("常取6攒斗栱，且一般柱不越间广（柱高小于明间宽度）"),
        )# type: ignore
    x_3 : bpy.props.FloatProperty(
            name = T("梢间宽度"),
            min = 0, 
            precision=3,
            update=dc.update_building,
            description=T("可以与次间宽度相同"),
        )# type: ignore
    x_4 : bpy.props.FloatProperty(
            name = T("尽间宽度"),
            min = 0, 
            precision=3,
            update=dc.update_building,
            description=T("如果做四面廊，一般取2攒斗栱"),
        )# type: ignore
    y_rooms : bpy.props.IntProperty(
            name = T("进深间数"),
            #max = 5,
            min = 1, 
            update=dc.reset_building,
            description=T("根据通进深的需要，以及是否做前后廊，可以为偶数"),
        )# type: ignore
    y_1 : bpy.props.FloatProperty(
            name = T("明间深度"),
            min = 0, 
            precision=3,
            update=dc.update_building,
            description=T("需综合考虑步架进行设计"),
        )# type: ignore
    y_2 : bpy.props.FloatProperty(
            name = T("次间深度"),
            min = 0, 
            precision=3,
            update=dc.update_building,
            description=T("需综合考虑步架进行设计"),
        )# type: ignore
    y_3 : bpy.props.FloatProperty(
            name = T("梢间深度"),
            min = 0, 
            precision=3,
            update=dc.update_building,
            description=T("需综合考虑步架进行设计"),
        )# type: ignore
    
    # 柱子属性
    pillar_net : bpy.props.StringProperty(
            name = T("保存的柱网列表")
        )# type: ignore
    pillar_height : bpy.props.FloatProperty(
            name = T("檐柱高"),
            default = 0.0,
            min = 0.01, 
            precision=3,
            update=dc.update_pillarHeight,
            description=T("有斗拱的取57-60斗口，无斗拱的取面阔的8/10"),
        )# type: ignore
    pillar_diameter : bpy.props.FloatProperty(
            name = T("檐柱径"),
            default = 0.0,
            min = 0.01, 
            precision=3,
            # update=dc.update_pillar
            update=dc.update_building,
            description=T("有斗拱的取6斗口，无斗拱的取1/10柱高"),
        )# type: ignore
    use_smallfang: bpy.props.BoolProperty(
            default=False,
            name=T("双重额枋"),
            update=dc.update_building,
            description=T("同时使用大额枋、由额垫板、小额枋的三件套连接两根柱"),
        )# type: ignore 
    pillar_insert: bpy.props.FloatProperty(
            name = T("插柱深度"),
            default = 0.0,
            min = 0.01, 
            precision=3,
            description=T("楼阁上层柱体插入下层的深度"),
        )# type: ignore
    
    
    # 墙体属性
    railing_list: bpy.props.CollectionProperty(
        type=ACA_data_railing, name=T("栏杆列表")
    ) # type: ignore
    maindoor_list: bpy.props.CollectionProperty(
        type=ACA_data_maindoor, name=T("板门列表")
    ) # type: ignore
    wall_list: bpy.props.CollectionProperty(
        type=ACA_data_wall_common, name=T("墙体列表")
    ) # type: ignore
    window_list: bpy.props.CollectionProperty(
        type=ACA_data_door_common, name=T("窗户列表")
    ) # type: ignore
    geshan_list: bpy.props.CollectionProperty(
        type=ACA_data_geshan, name=T("隔扇列表")
    ) # type: ignore 
    paint_style : bpy.props.EnumProperty(
            name = T("彩画样式"),
            description = T("可以切换清和玺等彩画样式"),
            # 枚举项仅国际化显示文本，内部值(0/1/2/3)保持不变
            items = [
                ("0",T("清-和玺彩画"),""),
                ("1",T("酱油色"),""),
                ("2",T("白模"),""),
                ("3",T("红漆无彩画"),""),
            ],
            update=dc.update_building,
            options = {"ANIMATABLE"}
        ) # type: ignore
    use_balcony_railing :  bpy.props.BoolProperty(
            default=False,
            name=T("使用平坐栏杆"),
            update=dc.update_dougong,
            description=T("自动添加围绕平坐的连续栏杆"),
        )# type: ignore 
    
    # 斗栱属性
    use_dg :  bpy.props.BoolProperty(
            default=False,
            name=T("使用斗栱"),
            update=dc.update_dougong,
            description=T("小式建筑可以不使用斗栱，大梁直接坐在柱头"),
        )# type: ignore 
    use_pingbanfang: bpy.props.BoolProperty(
            default=True,
            name=T("使用平板枋"),
            update=dc.update_dougong,
            description=T("在柱头和斗栱之间的一层垫板，明清式建筑一般都会使用"),
        )# type: ignore 
    dg_style : bpy.props.EnumProperty(
            name = T("斗栱类型"),
            description = T("根据建筑等级的不同，斗栱有严格的限制"),
            items=dc.getDougongList,
            options = {"ANIMATABLE"},
            update=dc.update_dougong,
            default=0,
        ) # type: ignore
    dg_extend : bpy.props.FloatProperty(
            name=T("斗栱挑檐"),    # 令拱出跳距离
            default=0.45,
            description = T("斗栱出跳由斗栱模板预先定义，不可修改"),
            min=0.01,
            precision=3,
        )# type: ignore 
    dg_height : bpy.props.FloatProperty(
            name=T("斗栱高度"),    # 取挑檐桁下皮高度
            default=1.0,
            precision=3,
        )# type: ignore 
    dg_scale:bpy.props.FloatVectorProperty(
            name=T("斗栱缩放"),    # 斗栱缩放
            default=(1,1,1),
            precision=3,
        )# type: ignore 
    dk_scale:bpy.props.FloatProperty(
            name=T("斗口放大"),    # 斗栱间距
            description = T("为了模仿唐宋建筑风格，可以放大斗栱"),
            default=1,
            precision=3,
            min=0.5,
            max=2.5,
            update=dc.update_dougong,
        )# type: ignore 
    dg_gap:bpy.props.FloatProperty(
            name=T("斗栱间距"),    # 斗栱间距
            description = T("一般取11斗口"),
            default=0.99,
            precision=3,
            min=0.1,
            update=dc.update_dougong,
        )# type: ignore 
    dg_withbeam:bpy.props.BoolProperty(
            name=T("斗栱与大梁连做"),    # 斗栱间距
            description = T("斗栱中已经包含大梁，则不再生成大梁"),
            default=True,
        )# type: ignore 
    
    # 屋顶属性
    roof_style : bpy.props.EnumProperty(
            name = T("屋顶类型"),
            # 枚举项仅国际化显示文本，内部值(0~9)保持不变
            items = [
                ("0","",""),
                ("1",T("庑殿顶"),""),
                ("2",T("歇山顶"),""),
                ("3",T("悬山顶"),""),
                ("4",T("硬山顶"),""),
                ('5',T("盝顶"),""),
                ("6",T("悬山卷棚顶"),""),
                ('7',T("硬山卷棚顶"),""),
                ('8',T("歇山卷棚顶"),""),
                ('9',T("平坐"),""),
            ],
            #update=dc.update_roof,
            update=dc.update_roofstyle,
            description=T("请选择一种屋顶样式"),
        ) # type: ignore
    use_double_eave: bpy.props.BoolProperty(
            default=False,
            name=T("使用重檐"),
            update=dc.update_roof,
            description=T("使用重檐形式的屋顶"),
        )# type: ignore 
    use_hallway : bpy.props.BoolProperty(
            default=False,
            name=T("做廊步架"),
            update=dc.update_building,
            description=T("在前后廊和周围廊做法时，升高金柱到下金桁高度"),
        )# type: ignore 
    rafter_count : bpy.props.IntProperty(
            name=T("步架数量"),
            default=8,
            min=2,max=9,
            update=dc.update_roof,
            description=T("以通进深除以22斗口来估算，过大过小会有很多潜在问题"),
        )# type: ignore 
    use_flyrafter :  bpy.props.BoolProperty(
            default=True,
            name=T("使用飞椽"),
            update=dc.update_roof,
            description=T("小式的硬山、悬山可以不做飞椽，但四坡面必须使用飞椽做翼角"),
        )# type: ignore 
    use_wangban :  bpy.props.BoolProperty(
            default=True,
            name=T("添加望板"),
            update=dc.update_roof,
            description=T("可以不做望板，更直观的查看屋顶结构"),
        )# type: ignore 
    qiqiao: bpy.props.FloatProperty(
            name=T("起翘(椽径倍数)"),
            default=4, 
            min=0,
            update=dc.update_roof,
            description=T("常做4椽起翘，也可以视情况适当增加"),
        )# type: ignore 
    chong: bpy.props.FloatProperty(
            name=T("出冲(椽径倍数)"),
            default=3,
            min=0, 
            update=dc.update_roof,
            description=T("常做3椽出冲，也可以视情况适当增加"),
        )# type: ignore 
    use_pie: bpy.props.BoolProperty(
            name=T("使用撇"),
            default=True,
            update=dc.update_roof,
            description=T("翼角翘飞椽可以选择是否做官式的撇向做法，起翘夸张的非官式做法建议关闭"),
    )# type: ignore
    shengqi: bpy.props.IntProperty(
            name=T("生起(椽径倍数)"),
            default=1, 
            update=dc.update_roof
        )# type: ignore 
    liangtou: bpy.props.FloatProperty(
            name=T("梁头位置"), 
            default=0.5,
            min=0,
            max=1.0,
            precision=3,
            update=dc.update_roof,
            description=T("老梁头压挑檐桁的尺度，建议在0.5左右，可根据起翘形态适当调整")
        )# type: ignore
    tuishan: bpy.props.FloatProperty(
            name=T("推山系数"), 
            default=0.9,
            min=0.1,
            max=1.0,
            precision=3,
            update=dc.update_roof,
            description=T("庑殿顶两山坡度的调整系数，标准值为0.9，设置为1.0即不做推山")
        )# type: ignore
    shoushan: bpy.props.FloatProperty(
            name=T("收山尺寸"), 
            default=2,
            min=0,
            max=2,
            precision=3,
            update=dc.update_roof,
            description=T("歇山顶的山花板从檐檩中向内移动的距离(米)，一般为1檩径(4斗口)，最大不超过檐步架")
        )# type: ignore
    luding_rafterspan:bpy.props.FloatProperty(
            name=T("盝顶檐步架宽"), 
            default=3,
            min=0.01,
            max=6,
            precision=3,
            update=dc.update_roof,
            description=T("盝顶檐步架宽度，用于重檐时，请设置为上下层面阔/进深收分的距离")
        )# type: ignore
    juzhe : bpy.props.EnumProperty(
            name = T("举折系数"),
            # 枚举项仅国际化显示文本，内部值(0~3)保持不变
            items = [
                ("0",T("   举折系数：默认"),T("[0.5,0.7,0.8,0.9]")),
                ("1",T("   举折系数：陡峭"),T("[0.5,1,1.5,2]，慎用，一般用于亭子等建筑")),
                ("2",T("   举折系数：平缓"),T("[0.5,0.65,0.75,0.9]")),
                ("3",T("   举折系数：按屋架高度推算"),T("根据输入屋架高度，进行举折计算"))
            ],
            description=T("决定了屋面坡度的曲率"),
            update=dc.update_juzhe,
        ) # type: ignore
    roof_height:bpy.props.FloatProperty(
            name=T("屋架高度"), 
            default=3,
            min=0.01,
            max=10,
            precision=3,
            update=dc.update_roof,
            description=T("从正心桁到脊桁的垂直高度")
        )# type: ignore
    roof_qiao_point : bpy.props.FloatVectorProperty(
        name=T("翼角起翘参考点"),
        subtype='XYZ',
        unit='LENGTH',
        )# type: ignore 
    
    # 瓦作属性
    # 250616 添加瓦作缩放因子
    tile_scale:bpy.props.FloatProperty(
            name=T("瓦作缩放"),    # 瓦作缩放
            default=1.0,
            min=0.5,max=2.0,
            precision=2,
            description=T("放大或缩小瓦作的比例，默认1.0"),
            update=dc.update_building,
        )# type: ignore
    tile_color : bpy.props.EnumProperty(
            name = T("瓦面颜色"),
            # 枚举项仅国际化显示文本，内部值(0~4)保持不变
            items = [
                ("0",T("黄琉璃"),""),
                ("1",T("绿琉璃"),""),
                ("2",T("灰琉璃"),""),
                ("3",T("蓝琉璃"),""),
                ("4",T("紫琉璃"),""),
            ],
        ) # type: ignore
    tile_alt_color : bpy.props.EnumProperty(
            name = T("剪边颜色"),
            # 枚举项仅国际化显示文本，内部值(0~4)保持不变
            items = [
                ("0",T("黄琉璃"),""),
                ("1",T("绿琉璃"),""),
                ("2",T("灰琉璃"),""),
                ("3",T("蓝琉璃"),""),
                ("4",T("紫琉璃"),""),
            ],
        ) # type: ignore
    tile_width : bpy.props.FloatProperty(
            name=T("瓦垄宽度"), 
            default=0.4,
            min=0.0,
            precision=3,
        )# type: ignore
    tile_width_real : bpy.props.FloatProperty(
            name=T("瓦垄实际宽度"), 
            precision=3,
        )# type: ignore
    tile_length : bpy.props.FloatProperty(
            name=T("瓦片长度"), 
            default=0.4,
            min=0.0,
            precision=3,
        )# type: ignore
    
    # 屋脊属性
    paoshou_count:bpy.props.IntProperty(
            name = T('跑兽数量'),
            default=6,
            min=0,
            max=10,
            update=dc.update_rooftile,
            description=T("包括骑鸡仙人的数量"),
        )# type: ignore 
    
    # 院墙属性
    is_4_sides:bpy.props.BoolProperty(
            default = True,
            name = T("是否做四面墙"),
            description=T("同时生成四面合围的墙体，转角处将做45度拼接"),
        ) # type: ignore
    yard_width :bpy.props.FloatProperty(
            name=T("庭院面阔"),
            default=40,
            precision=3,
            min=1,
            description=T("围墙的长度"),
            update=dc.update_yardwall,
        )# type: ignore 
    yard_depth :bpy.props.FloatProperty(
            name=T("庭院进深"),
            default=30,
            precision=3,
            min=1,
            description=T("仅在四面合围墙体时设置"),
            update=dc.update_yardwall,
        )# type: ignore
    yardwall_height:bpy.props.FloatProperty(
            name=T("院墙高度"),
            default=3,
            precision=3,
            min=1,
            description=T("院墙高度，不含帽瓦"),
            update=dc.update_yardwall,
        )# type: ignore
    yardwall_depth:bpy.props.FloatProperty(
            name=T("院墙厚度"),
            default=1,
            precision=3,
            min=0.5,
            description=T("院墙厚度，不含帽瓦"),
            update=dc.update_yardwall,
        )# type: ignore
    yardwall_angle:bpy.props.FloatProperty(
            name=T("院墙帽瓦斜率"),
            default=30,
            precision=3,
            min=0,
            max=45,
            description=T("帽瓦斜率，一般可维持30度"),
            update=dc.update_yardwall,
        )# type: ignore  
    
    # 251112 回廊标识
    loggia_sign : bpy.props.StringProperty(
            name = T("回廊标识")
        )# type: ignore
    
    # 251117 举折系数
    juzhe_var :bpy.props.FloatProperty(
            name=T("举折系数"),
            default=0.1,
            precision=3,
            min=0.1,
            max=0.3,
            update=dc.update_roof,
            description=T("举折系数，默认0.1，适当调大可以获得更加明显的瓦面弧度"),
        )# type: ignore
    
    # 251205 后处理操作列表
    postProcess: bpy.props.CollectionProperty(
        type=ACA_data_postProcess, name=T("后处理列表")
    ) # type: ignore

#######################################################
### Section 5: 建筑素材库 (Building Assets)
# 全局共用的模板信息，各个建筑都进行引用
# 包括资产库资产引用等    
class ACA_data_template(bpy.types.PropertyGroup):
    # 材质对象
    mat_override:bpy.props.PointerProperty(
            name = T("UVgrid"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_wood:bpy.props.PointerProperty(
            name = T("木材材质"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_rock:bpy.props.PointerProperty(
            name = T("石材材质"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_stone:bpy.props.PointerProperty(
            name = T("石头材质"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_oilpaint:bpy.props.PointerProperty(
            name = T("漆.通用"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_gold:bpy.props.PointerProperty(
            name = T("漆.金"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_green:bpy.props.PointerProperty(
            name = T("漆.绿"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_brick_1:bpy.props.PointerProperty(
            name = T("方砖缦地"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_brick_2:bpy.props.PointerProperty(
            name = T("条砖竖铺"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_brick_3:bpy.props.PointerProperty(
            name = T("条砖横铺"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_dust_wall:bpy.props.PointerProperty(
            name = T("墙体抹灰"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_beam_big :bpy.props.PointerProperty(
            name = T("梁枋彩画.大额枋"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_beam_small :bpy.props.PointerProperty(
            name = T("梁枋彩画.小额枋"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_pillarhead :bpy.props.PointerProperty(
            name = T("柱头贴图"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_walkdragon :bpy.props.PointerProperty(
            name = T("平板枋.行龙"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_grasscouple :bpy.props.PointerProperty(
            name = T("垫板.公母草"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_dgfillboard :bpy.props.PointerProperty(
            name = T("栱垫板"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_dgfillboard_s :bpy.props.PointerProperty(
            name = T("栱垫板"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_rafter : bpy.props.PointerProperty(
            name = T("檐椽贴图"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_flyrafter : bpy.props.PointerProperty(
            name = T("飞椽贴图"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_wangban: bpy.props.PointerProperty(
            name = T("望板着色"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_cloud: bpy.props.PointerProperty(
            name = T("工王云"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_tuanend: bpy.props.PointerProperty(
            name = T("端头坐龙"),
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_ccb : bpy.props.PointerProperty(
            name = T("子角梁"),
            type = bpy.types.Object,
        )# type: ignore
    mat_paint_door : bpy.props.PointerProperty(
            name = T("裙板"),
            type = bpy.types.Object,
        )# type: ignore
    mat_paint_doorring : bpy.props.PointerProperty(
            name = T("绦环板"),
            type = bpy.types.Object,
        )# type: ignore
    mat_paint_shanhua : bpy.props.PointerProperty(
            name = T("山花板"),
            type = bpy.types.Object,
        )# type: ignore
    mat_geshanxin : bpy.props.PointerProperty(
            name = T("三交六椀隔心"),
            type = bpy.types.Object,
        )# type: ignore    
    mat_geshanxin_wan : bpy.props.PointerProperty(
            name = T("万字锦棂心"),
            type = bpy.types.Object,
        )# type: ignore    
    mat_ccfang : bpy.props.PointerProperty(
            name = T("穿插枋"),
            type = bpy.types.Object,
        )# type: ignore  
    mat_cornerbeam : bpy.props.PointerProperty(
            name = T("老角梁"),
            type = bpy.types.Object,
        )# type: ignore  
    mat_queti : bpy.props.PointerProperty(
            name = T("雀替"),
            type = bpy.types.Object,
        )# type: ignore  
    mat_dougong : bpy.props.PointerProperty(
            name = T("斗栱"),
            type = bpy.types.Object,
        )# type: ignore  
    mat_guayanban : bpy.props.PointerProperty(
            name = T("挂檐板"),
            type = bpy.types.Object,
        )# type: ignore 
    
    # 柱对象
    pillar_source : bpy.props.PointerProperty(
            name = T("柱样式"),
            type = bpy.types.Object,
        )# type: ignore
    pillar_lift_source : bpy.props.PointerProperty(
            name = T("垂花柱样式"),
            type = bpy.types.Object,
        )# type: ignore
    pillarbase_source : bpy.props.PointerProperty(
            name = T("柱础样式"),
            type = bpy.types.Object,
        )# type: ignore
    
    # 棂心对象
    lingxin_source:bpy.props.PointerProperty(
            name = T("棂心"),
            type = bpy.types.Object,
            update=dc.update_wall
        )# type: ignore 
    
    # 斗栱对象
    dg_pillar_source:bpy.props.PointerProperty(
            name = T("柱头斗栱"),
            type = bpy.types.Object,
        )# type: ignore 
    dg_fillgap_source:bpy.props.PointerProperty(
            name = T("补间斗栱"),
            type = bpy.types.Object,
        )# type: ignore 
    dg_fillgap_alt_source:bpy.props.PointerProperty(
            name = T("补间斗栱-异色"),
            type = bpy.types.Object,
        )# type: ignore 
    dg_corner_source:bpy.props.PointerProperty(
            name = T("转角斗栱"),
            type = bpy.types.Object,
        )# type: ignore 
    dg_balcony_pillar_source:bpy.props.PointerProperty(
            name = T("平坐柱头斗栱"),
            type = bpy.types.Object,
        )# type: ignore 
    dg_balcony_corner_source:bpy.props.PointerProperty(
            name = T("平坐转角斗栱"),
            type = bpy.types.Object,
        )# type: ignore 
    dg_balcony_fillgap_source:bpy.props.PointerProperty(
            name = T("平坐补间斗栱"),
            type = bpy.types.Object,
        )# type: ignore 
    dg_balcony_fillgap_alt_source:bpy.props.PointerProperty(
            name = T("平坐补间斗栱-异色"),
            type = bpy.types.Object,
        )# type: ignore 
    
    # 博缝板对象
    bofeng_source : bpy.props.PointerProperty(
            name = T("博缝板"),
            type = bpy.types.Object,
        )# type: ignore
    
    # 老角梁对象
    cornerbeam_source : bpy.props.PointerProperty(
            name = T("老角梁"),
            type = bpy.types.Object,
        )# type: ignore
    
    # 霸王拳对象
    bawangquan_source : bpy.props.PointerProperty(
            name = T("霸王拳"),
            type = bpy.types.Object,
        )# type: ignore
    
    # 雀替对象
    queti_source : bpy.props.PointerProperty(
            name = T("雀替"),
            type = bpy.types.Object,
        )# type: ignore
    
    # 穿插枋对象
    ccfang_source : bpy.props.PointerProperty(
            name = T("穿插枋"),
            type = bpy.types.Object,
        )# type: ignore
    
    # 琉璃瓦对象
    flatTile_source:bpy.props.PointerProperty(
            name = T("板瓦"),
            type = bpy.types.Object,
        )# type: ignore 
    circularTile_source:bpy.props.PointerProperty(
            name = T("筒瓦"),
            type = bpy.types.Object,
        )# type: ignore 
    eaveTile_source:bpy.props.PointerProperty(
            name = T("瓦当"),
            type = bpy.types.Object,
        )# type: ignore 
    dripTile_source:bpy.props.PointerProperty(
            name = T("滴水"),
            type = bpy.types.Object,
        )# type: ignore 
    
    # 屋脊对象
    ridgeTop_source:bpy.props.PointerProperty(
            name = T("正脊筒"),
            type = bpy.types.Object,
        )# type: ignore 
    ridgeBack_source:bpy.props.PointerProperty(
            name = T("垂脊兽后"),
            type = bpy.types.Object,
        )# type: ignore 
    ridgeFront_source:bpy.props.PointerProperty(
            name = T("垂脊兽前"),
            type = bpy.types.Object,
        )# type: ignore 
    ridgeEnd_source:bpy.props.PointerProperty(
            name = T("端头盘子"),
            type = bpy.types.Object,
        )# type: ignore 
    chiwen_source:bpy.props.PointerProperty(
            name = T("螭吻"),
            type = bpy.types.Object,
        )# type: ignore 
    hejiaowen_source:bpy.props.PointerProperty(
            name = T("合角吻"),
            type = bpy.types.Object,
        )# type: ignore 
    baoding_source:bpy.props.PointerProperty(
            name = T("宝顶"),
            type = bpy.types.Object,
        )# type: ignore 
    chuishou_source:bpy.props.PointerProperty(
            name = T("垂兽"),
            type = bpy.types.Object,
        )# type: ignore 
    taoshou_source:bpy.props.PointerProperty(
            name = T("套兽"),
            type = bpy.types.Object,
        )# type: ignore 
    
    # 跑兽对象
    paoshou_0_source:bpy.props.PointerProperty(
            name = T("仙人"),
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_1_source:bpy.props.PointerProperty(
            name = T("龙"),
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_2_source:bpy.props.PointerProperty(
            name = T("凤"),
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_3_source:bpy.props.PointerProperty(
            name = T("狮子"),
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_4_source:bpy.props.PointerProperty(
            name = T("海马"),
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_5_source:bpy.props.PointerProperty(
            name = T("天马"),
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_6_source:bpy.props.PointerProperty(
            name = T("狎鱼"),
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_7_source:bpy.props.PointerProperty(
            name = T("狻猊"),
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_8_source:bpy.props.PointerProperty(
            name = T("獬豸"),
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_9_source:bpy.props.PointerProperty(
            name = T("斗牛"),
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_10_source:bpy.props.PointerProperty(
            name = T("行什"),
            type = bpy.types.Object,
        )# type: ignore     
    walleave:bpy.props.PointerProperty(
            name = T("墙檐"),
            type = bpy.types.Object,
        )# type: ignore     
    door_pushou:bpy.props.PointerProperty(
            name = T("铺首"),
            type = bpy.types.Object,
        )# type: ignore     
    door_ding:bpy.props.PointerProperty(
            name = T("门钉"),
            type = bpy.types.Object,
        )# type: ignore     
    door_zan:bpy.props.PointerProperty(
            name = T("门簪"),
            type = bpy.types.Object,
        )# type: ignore 
    railing_pillar:bpy.props.PointerProperty(
            name = T("栏杆望柱"),
            type = bpy.types.Object,
        )# type: ignore 
    railing_vase:bpy.props.PointerProperty(
            name = T("栏杆净瓶"),
            type = bpy.types.Object,
        )# type: ignore 
    xuanyu_source:bpy.props.PointerProperty(
            name = T("悬鱼"),
            type = bpy.types.Object,
        )# type: ignore 
    
