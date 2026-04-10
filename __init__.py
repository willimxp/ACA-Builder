# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：插件初始化，注入扩展类

import bpy
import platform
import os
from . import panel
from . import operators
from . import data
from . import utils
from .locale import i18n
from .locale.i18n import _
from .tools import auto_register
from .tools import aca_logging

# Blender配置元数据，用户安装插件时的设置项
# https://developer.blender.org/docs/handbook/addons/addon_meta_info/
bl_info = {
    "name" : "ACA Builder",
    "author" : "皮皮 willimxp",
    "description" : "筑韵古建：模板化生成清官式建筑。Generate architecher in chinese style.",
    "blender" : (5, 0, 0),
    "version" : (0, 6, 1),
    "location" : "View3D > Properties > ACA Builder",
    "tracker_url": "https://github.com/willimxp/ACA-Builder/issues",
    "doc_url": "https://docs.qq.com/doc/DYXpwbUp1UWR0RXpu",
    "category" : "Add Mesh"
}

# 自动从模块中发现并注册所有Blender类
# 这样新增类时无需手动添加到这个列表中
classes = auto_register.auto_register_classes(data, panel, operators)

# 可选：打印注册信息到控制台（调试用）
# print(auto_register.get_registration_info(classes))

def register():       
    ##############################################
    # 1、初始化插件
    # 注入类
    for cls in classes:
        bpy.utils.register_class(cls)

    # 注册自定义属性
    data.initprop()

    ##############################################
    # 2、初始化日志
    # 260210 从偏好设置读取日志配置并初始化日志记录器
    preferences = bpy.context.preferences
    addon_main_name = __name__.split('.')[0]
    addon_prefs = preferences.addons[addon_main_name].preferences
    log_level = aca_logging.get_log_level_from_string(addon_prefs.log_level)
    logger = aca_logging.init_logger(
        log_level=log_level,
        use_rotating=addon_prefs.use_log_rotation
    )

    # 260225 插件加载，输出提示信息
    utils.outputMsg("=" * 60)
    utils.outputMsg(f"{bl_info['name']} v{'.'.join(map(str, bl_info['version']))}")
    utils.outputMsg(f"{bl_info['description']}")
    utils.outputMsg(f"{bl_info['doc_url']}")

    # 记录系统信息
    aca_logging.log_system_info(logger)

    ##############################################
    # 3、初始化多语言
    # 注册多语言
    i18n.register()
    
    # 记录类注册信息
    logger.info(f"Registred: {len(classes)} Classes")
    logger.debug("Register Detail：")
    logger.debug(auto_register.get_registration_info(classes))
    ##############################################
    # 4、其他初始化
    # 250311 发现在中文版中UV贴图异常
    # 最终发现是该选项会导致生成的'UVMap'变成'UV贴图'
    # 禁用语言-翻译-新建数据
    bpy.context.preferences.view.use_translate_new_dataname = False

    # 251211 解决在terminal中的中文乱码问题
    # 260210 添加平台检测和用户偏好设置，仅在Windows系统上执行
    if platform.system() == "Windows":
        preferences = bpy.context.preferences
        addon_main_name = __name__.split('.')[0]
        addon_prefs = preferences.addons[addon_main_name].preferences
        if addon_prefs.fix_windows_cli_encoding:
            os.system("chcp 65001")  # 65001 = UTF-8编码

    # 插件加载完成
    utils.outputMsg("=" * 60)
    
    return
    
def unregister():
    # 销毁类
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # 销毁多语言
    i18n.unregister()
    
    # 销毁自定义属性
    data.delprop()

    # 260210 使用新的日志模块移除日志记录器
    aca_logging.remove_logger()

    # 释放模板缩略图资源
    from . import template
    template.releasePreview()

    return

# 仅用于在blender text editor中测试用途
# 当做为blender addon插件载入时不会触发
if __name__ == "__main__":
    register()

# 260210 日志模块已迁移到 aca_logging.py
# 请注意：Blender做为root logger，已经使用了logging.basicConfig()
# https://blender.stackexchange.com/questions/270509/output-a-log-file-from-blender-for-debugging-addon
# https://docs.python.org/zh-cn/3.13/howto/logging.html#
