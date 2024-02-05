# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   定义插件面板的UI

import bpy
from . import data

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
        dataset : data.ACA_data_scene = context.scene.ACA_data
        
        layout = self.layout
        # 选择框
        row = layout.row()
        row.prop(dataset, "is_auto_redraw")

        # 1、添加台基
        box = layout.box() 
        # 1.1、台基高度
        row = box.row()
        row.prop(dataset, "platform_height")
        # 1.2、台基下出
        row = box.row()
        row.prop(dataset, "platform_extend")
        # 1.3、按钮：添加台基
        row = box.row()
        row.operator("aca.build_platform",icon='FILE_3D')

        # 2、添加柱网
        box = layout.box() 
        # 2.1 面阔
        # 2.1.1 当心间宽度
        # 输入整体尺寸，绑定data中的自定义property
        row = box.column(align=True)
        row.prop(dataset, "x_rooms")    # 面阔间数
        row.prop(dataset, "x_1")        # 明间宽度
        if dataset.x_rooms >= 3:
            row.prop(dataset, "x_2")    # 次间宽度
        if dataset.x_rooms >= 5:
            row.prop(dataset, "x_3")    # 梢间宽度
        if dataset.x_rooms >= 7:
            row.prop(dataset, "x_4")    # 尽间宽度

        row = box.column(align=True)
        row.prop(context.scene.chinarch_data, "y_rooms")    # 进深间数
        row.prop(dataset, "y_1")        # 明间深度
        if dataset.y_rooms >= 3:
            row.prop(dataset, "y_2")    # 次间深度
        if dataset.y_rooms >= 5:
            row.prop(dataset, "y_3")    # 梢间深度

        row = box.row()
        row.operator("aca.build_piller",icon='FILE_3D')


        # 2.1.n 添加开间
        # 3.1 进深
        # 3.1.1 当心间进深
        # 3.1.n 添加进深


class ACA_PT_props(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "古建营造"             # 标签页名称
    bl_label = "构件属性"            # 面板名称，显示为可折叠的箭头后

    def draw(self, context):
        # 从当前场景中载入数据集
        dataset : data.ACA_data_scene = context.scene.ACA_data

        layout = self.layout

        # 仅在选中构件时显示
        selected_obj_count = len(bpy.context.selected_objects)
        if  selected_obj_count > 0 \
            and "aca_obj" in context.object:
            
            # 名称
            box = layout.box()
            row = box.row()
            row.prop(context.object,"name",text="名称")

            # 台基属性
            if context.object.aca_type == 'platform' :
                row = box.row()
                row.prop(dataset, "platform_height")
                row = box.row()
                row.prop(dataset, "platform_extend")