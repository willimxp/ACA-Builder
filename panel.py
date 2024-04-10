# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   定义插件面板的UI

import bpy
from . import data
from .const import ACA_Consts as con
from . import utils

# 营造向导面板
class ACA_PT_basic(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示 
    
    # 自定义属性
    bl_category = "古建营造"             # 标签页名称
    bl_label = "营造向导"            # 面板名称，显示为可折叠的箭头后
    
    def draw(self, context):
        # 从当前场景中载入数据集
        scnData : data.ACA_data_scene = context.scene.ACA_data
        
        layout = self.layout
        box = layout.box()
        # 模板选择列表
        row = box.row()
        row.prop(scnData, "template")
        # 按钮，生成新建筑
        row = box.row()
        row.operator("aca.add_newbuilding",icon='FILE_3D')
        # 选择框，是否实时重绘
        row = box.row()
        row.prop(scnData, "is_auto_redraw")
        
        # 测试按钮
        row = layout.row()
        row.operator("aca.test",icon='HOME')# 按钮：生成门窗

# “构件属性”面板
# 根据当前选择的对象，显示对象的名称、类型
# 同时，根据对象类型，显示对应的可设置参数
class ACA_PT_props(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "古建营造"             # 标签页名称
    bl_label = "建筑参数"            # 面板名称，显示为可折叠的箭头后

    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            layout = self.layout
            objData :data.ACA_data_obj = context.object.ACA_data             

            # 仅在选中建筑根节点时显示
            if objData.aca_type == con.ACA_TYPE_BUILDING:
                box = layout.box()

                # 名称
                row = box.row()
                row.prop(context.object,"name",text="建筑名称")
                # 建筑属性
                row = box.row()
                row.prop(objData,"DK")  # 斗口

                # 台基属性
                box = layout.box()
                row = box.row()
                row.prop(objData, "platform_height")
                row = box.row()
                row.prop(objData, "platform_extend")

                # 柱网属性
                box = layout.box()
                row = box.column(align=True)
                row.prop(objData, "x_rooms")    # 面阔间数
                row.prop(objData, "x_1")        # 明间宽度
                if objData.x_rooms >= 3:
                    row.prop(objData, "x_2")    # 次间宽度
                if objData.x_rooms >= 5:
                    row.prop(objData, "x_3")    # 梢间宽度
                if objData.x_rooms >= 7:
                    row.prop(objData, "x_4")    # 尽间宽度
                row = box.column(align=True)
                row.prop(objData, "y_rooms")    # 进深间数
                row.prop(objData, "y_1")        # 明间深度
                if objData.y_rooms >= 3:
                    row.prop(objData, "y_2")    # 次间深度
                if objData.y_rooms >= 5:
                    row.prop(objData, "y_3")    # 梢间深度

                #柱子属性
                box = layout.box()
                row = box.row()
                row.prop(objData, "piller_height") # 柱高
                row = box.row()
                row.prop(objData, "piller_diameter") # 柱径
                row = box.row()
                row.prop(objData, "piller_source") # 柱样式
                
                # 墙属性
                box = layout.box()
                row = box.row()
                row.prop(objData, "wall_layout") # 墙布局
                row = box.row() 
                row.prop(objData, "wall_style") # 墙样式
                # 批量设置全局的墙样式
                if objData.wall_style == "1": # 槛墙
                    row = box.row() 
                    row.prop(objData, "wall_source") # 墙样式
                if objData.wall_style in ("2","3"): # 2-隔扇，3-槛窗
                    row = box.row()
                    row.prop(objData, "door_height")  # 中槛高度
                    row = box.row()
                    row.prop(objData, "door_num")     # 隔扇数量
                    row = box.row()
                    row.prop(objData, "gap_num")      # 抹头数量
                    row = box.row() 
                    row.prop(objData, "lingxin_source")   # 棂心样式
                row = box.row()
                row.operator("aca.reset_wall_layout",icon='HOME')# 按钮：墙体营造

                # 斗栱属性
                box = layout.box()
                row = box.row()
                row.prop(objData, "use_dg") # 柱头斗栱
                if objData.use_dg:
                    row = box.row()
                    row.prop(objData, "dg_extend") # 斗栱出跳
                    row = box.row()
                    row.prop(objData, "dg_height") # 斗栱高度
                    row = box.row()
                    row.prop(objData, "dg_piller_source") # 柱头斗栱
                    row = box.row()
                    row.prop(objData, "dg_fillgap_source") # 补间斗栱
                    row = box.row()
                    row.prop(objData, "dg_corner_source") # 转角斗栱
                row = box.row()
                row.operator("aca.build_dougong",icon='HOME',)# 按钮：生成斗栱
                if objData.use_dg:
                    row.enabled = True
                else:
                    row.enabled = False

                # 屋顶属性
                box = layout.box()
                row = box.row()
                row.prop(objData, "roof_style") # 屋顶样式
                row = box.row()
                row.prop(objData, "rafter_count") # 椽架数量
                row = box.row()
                row.prop(objData, "use_flyrafter") # 添加飞椽
                row = box.row()
                row.prop(objData, "use_wangban") # 添加望板
                row = box.row()
                row.prop(objData, "use_tile") # 添加瓦作
                if objData.roof_style in ('1','2'):
                    row = box.row()
                    row.prop(objData, "chong") # 出冲
                    row = box.row()
                    row.prop(objData, "qiqiao") # 起翘
                    row = box.row()
                    row.prop(objData, "shengqi") # 生起
                row = box.row()
                row.operator("aca.build_roof",icon='HOME',)# 按钮：生成屋顶

                # 瓦作属性
                if objData.use_tile:
                    box = layout.box()
                    row = box.row()
                    row.prop(objData, "tile_width") # 瓦垄宽度
                    row = box.row()
                    row.prop(objData, "tile_length") # 瓦片长度
                    row = box.row()
                    row.prop(objData, "flatTile_source") # 板瓦
                    row = box.row()
                    row.prop(objData, "circularTile_source") # 筒瓦
                    row = box.row()
                    row.prop(objData, "eaveTile_source") # 瓦当
                    row = box.row()
                    row.prop(objData, "dripTile_source") # 滴水

            # 选择wallproxy时，可以设置墙体的独立样式
            if objData.aca_type == con.ACA_TYPE_WALL: 
                box = layout.box()
                row = box.row() 
                row.prop(objData, "wall_style") # 墙样式
                if objData.wall_style == "1": # 槛墙
                    row = box.row() 
                    row.prop(objData, "wall_source") # 墙样式
                if objData.wall_style in ("2","3"): # 2-隔扇，3-槛窗
                    # 隔扇工具
                    row = box.row()
                    row.label(text="请确选择一个墙体线框对象")
                    row = box.row()
                    row.prop(objData, "door_height")  # 中槛高度
                    row = box.row()
                    row.prop(objData, "door_num")     # 隔扇数量
                    row = box.row()
                    row.prop(objData, "gap_num")      # 抹头数量
                    row = box.row() 
                    row.prop(objData, "lingxin_source")   # 棂心样式
                    row = box.row()
                    row.prop(objData, "use_KanWall") # 是否有槛墙                
                row = box.row()
                row.operator("aca.build_door",icon='HOME')# 按钮：生成门窗
