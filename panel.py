# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   定义插件面板的UI

import bpy
from . import data
from . import const

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
        # 载入常量列表
        con = const.ACA_Consts
        # 从当前场景中载入数据集
        if context.object != None:
            objData :data.ACA_data_obj = context.object.ACA_data

            # 仅在选中建筑根节点时显示
            if objData.aca_type == con.ACA_TYPE_BUILDING:            
                layout = self.layout
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
                row = box.row() 
                row.prop(objData, "piller_base_source") # 柱础样式
