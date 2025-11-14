# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：插件初始化，注入扩展类

import bpy
from . import panel
from . import operators
from . import data
from . import utils
import logging
import pathlib

# Blender配置元数据，用户安装插件时的设置项
# https://developer.blender.org/docs/handbook/addons/addon_meta_info/
bl_info = {
    "name" : "ACA Builder",
    "author" : "皮皮 willimxp",
    "description" : "模板化生成清官式建筑。Generate architecher in chinese style.",
    "blender" : (4, 2, 0),
    "version" : (0, 4, 3),
    "location" : "View3D > Properties > ACA Builder",
    "tracker_url": "https://github.com/willimxp/ACA-Builder/issues",
    "doc_url": "https://docs.qq.com/doc/DYXpwbUp1UWR0RXpu",
    "category" : "Add Mesh"
}

# 定义一个注入类列表，在register和unregister时自动批量处理
classes = (
    # 全局数据类
    data.TemplateListItem,
    data.TemplateThumbItem,
    data.ACA_data_pavilion,
    data.ACA_data_scene,
    data.ACA_data_wall_common,
    data.ACA_data_door_common,
    data.ACA_data_taduo,
    data.ACA_data_railing,
    data.ACA_data_maindoor,
    data.ACA_data_geshan,
    data.ACA_data_obj,
    data.ACA_data_template,
    
    # 基本面板类
    panel.ACA_PT_basic,
    panel.ACA_PT_props, 
    panel.ACA_PT_roof_props,
    panel.ACA_PT_pillers,
    panel.ACA_PT_platform, 
    panel.ACA_PT_wall,
    panel.ACA_PT_dougong,
    panel.ACA_PT_beam,
    panel.ACA_PT_rafter,
    panel.ACA_PT_tiles,
    panel.ACA_PT_yardwall_props,
    
    # 操作逻辑类  
    operators.ACA_OT_LINK_ASSETS,
    operators.ACA_OT_Preferences,     # 插件设置
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
    operators.ACA_OT_set_piller,
    operators.ACA_OT_add_wall,
    operators.ACA_OT_del_wall,
    operators.ACA_OT_add_window,
    operators.ACA_OT_add_door,
    operators.ACA_OT_add_maindoor,
    operators.ACA_OT_add_barwindow,
    operators.ACA_OT_add_flipwindow,
    operators.ACA_OT_add_railing,
    operators.ACA_OT_add_bench,
    operators.ACA_OT_default_dk,
    operators.ACA_OT_save_template,
    operators.ACA_OT_del_template,
    operators.ACA_OT_build_yardwall,
    operators.ACA_OT_default_ludingRafterSpan,
    operators.ACA_OT_Show_Message_Box,
    operators.ACA_OT_PROFILE,
    operators.ACA_OT_EXPORT_FBX,
    operators.ACA_OT_EXPORT_GLB,
    operators.ACA_OT_JOIN,
    operators.ACA_UL_Template_Items,
    operators.ACA_OT_SELECT_TEMPLATE_DIALOG,
    operators.ACA_OT_SECTION,
    operators.ACA_OT_TERRACE_DEL,
    operators.ACA_OT_TERRACE_ADD,
    operators.ACA_OT_MULTI_FLOOR_ADD,
    operators.ACA_OT_ADD_LOGGIA,
    operators.ACA_OT_UNION_BUILDING,
    operators.ACA_OT_LOGGIA_EXTEND,
)

def register():   
    # 注入类
    for cls in classes:
        bpy.utils.register_class(cls)

    # 注册自定义属性
    data.initprop()

    # 初始化日志记录器
    initLogger()

    # 250311 发现在中文版中UV贴图异常
    # 最终发现是该选项会导致生成的'UVMap'变成'UV贴图'
    # 禁用语言-翻译-新建数据
    bpy.context.preferences.view.use_translate_new_dataname = False
    
    return
    
def unregister():
    # 销毁类
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # 销毁自定义属性
    data.delprop()

    # 移除日志记录器
    removeLogger()

    # 释放模板缩略图资源
    from . import template
    template.releasePreview()

    return

# 仅用于在blender text editor中测试用途
# 当做为blender addon插件载入时不会触发
if __name__ == "__main__":
    register()

# 初始化日志模块
# 请注意：Blender做为root logger，已经使用了logging.basicConfig()
# https://blender.stackexchange.com/questions/270509/output-a-log-file-from-blender-for-debugging-addon
# https://docs.python.org/zh-cn/3.13/howto/logging.html#
def initLogger():
    logLevel = logging.DEBUG

    # 获取日志记录器
    logger = logging.getLogger("ACA")
    logger.setLevel(logLevel)

    # 检查是否已经存在相同的 Handler
    if (logger.hasHandlers()):
        logger.handlers.clear()

    # 日志格式    
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] : %(message)s',
        datefmt='%y/%m/%d %H:%M:%S',
        )

    # 添加控制台日志记录器
    ch = logging.StreamHandler()
    ch.setLevel(logLevel)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # 添加文件日志记录器
    # 设置日志路径
    USER = pathlib.Path(
        bpy.utils.resource_path('USER'))
    log_dir = USER / "scripts/addons/ACA Builder"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / "aca_log.txt"
    if not log_file_path.exists():
        log_file_path.touch()
    log_handler = logging.FileHandler(
        filename=log_file_path,
        mode='w',                   # 每次清空上一次的日志
        )
    log_handler.setLevel(logLevel)
    log_handler.setFormatter(formatter)    
    logger.addHandler(log_handler)
    ver = 'V%s.%s.%s' % (
            bl_info['version'][0],
            bl_info['version'][1],
            bl_info['version'][2])
    utils.outputMsg('ACA筑韵古建%s——日志记录开始' % ver)

    return

# 移除日志记录器
def removeLogger():
    logger = logging.getLogger("ACA")
    if (logger.hasHandlers()):
        logger.handlers.clear()