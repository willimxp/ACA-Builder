# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：插件初始化，注入扩展类

import bpy
from . import panel
from . import operators
from . import data

# Blender配置元数据，用户安装插件时的设置项
# https://developer.blender.org/docs/handbook/addons/addon_meta_info/
bl_info = {
    "name" : "ACA Builder",
    "author" : "willimxp",
    "description" : "Generate architecher in chinese style.",
    "blender" : (2, 80, 0),
    "version" : (0, 0, 1),
    "location" : "View3D > Properties > ACA Builder",
    "tracker_url": "https://github.com/willimxp/China-Arch/issues",
    "doc_url": "https://github.com/willimxp/China-Arch/wiki",
    "category" : "Add Mesh"
}

# 定义一个注入类列表，在register和unregister时自动批量处理
classes = (
    # 全局数据类
    data.ACA_data_scene,    
    data.ACA_data_obj,
    data.ACA_data_template,
    
    # 基本面板类
    panel.ACA_PT_basic,
    panel.ACA_PT_props, 
    panel.ACA_PT_roof_props,
    panel.ACA_PT_platform, 
    panel.ACA_PT_pillers,
    panel.ACA_PT_wall,
    panel.ACA_PT_dougong,
    panel.ACA_PT_beam,
    panel.ACA_PT_rafter,
    panel.ACA_PT_tiles,
    panel.ACA_PT_yardwall_props,
    
    # 操作逻辑类    
    operators.ACA_OT_test,
    operators.ACA_OT_add_building,
    operators.ACA_OT_update_building,
    operators.ACA_OT_del_building,
    operators.ACA_OT_reset_wall_layout,
    operators.ACA_OT_build_dougong,
    operators.ACA_OT_build_roof,
    operators.ACA_OT_focusBuilding,
    operators.ACA_OT_reset_floor,
    operators.ACA_OT_add_step,
    operators.ACA_OT_del_step,
    operators.ACA_OT_del_piller,
    operators.ACA_OT_add_fang,
    operators.ACA_OT_del_fang,
    operators.ACA_OT_add_wall,
    operators.ACA_OT_del_wall,
    operators.ACA_OT_add_window,
    operators.ACA_OT_add_door,
    operators.ACA_OT_default_dk,
    operators.ACA_OT_save_template,
    operators.ACA_OT_del_template,
    operators.ACA_OT_build_yardwall,
    operators.ACA_OT_default_ludingRafterSpan,
    operators.ACA_OT_Show_Message_Box,
)

def register():   
    # 注入类
    for cls in classes:
        bpy.utils.register_class(cls)

    # 注册自定义属性
    data.initprop()
    
def unregister():
    # 销毁类
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # 销毁自定义属性
    data.delprop()

# 仅用于在blender text editor中测试用途
# 当做为blender addon插件载入时不会触发
if __name__ == "__main__":
    register()