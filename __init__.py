# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：插件初始化，注入扩展类

import bpy
from . import panel
from . import operators
from . import data
from . import utils
from .tools import auto_register
import logging
import pathlib

# Blender配置元数据，用户安装插件时的设置项
# https://developer.blender.org/docs/handbook/addons/addon_meta_info/
bl_info = {
    "name" : "ACA Builder",
    "author" : "皮皮 willimxp",
    "description" : "模板化生成清官式建筑。Generate architecher in chinese style.",
    "blender" : (4, 2, 0),
    "version" : (0, 6, 0),
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
    # 注入类
    for cls in classes:
        bpy.utils.register_class(cls)

    # 注册自定义属性
    data.initprop()

    # 初始化日志记录器
    initLogger()
    
    # 记录类注册信息（可选）
    logger = logging.getLogger("ACA")
    logger.info(f"成功注册 {len(classes)} 个类")
    logger.debug("类注册详情：")
    logger.debug(auto_register.get_registration_info(classes))

    # 250311 发现在中文版中UV贴图异常
    # 最终发现是该选项会导致生成的'UVMap'变成'UV贴图'
    # 禁用语言-翻译-新建数据
    bpy.context.preferences.view.use_translate_new_dataname = False

    # 251211 解决在terminal中的中文乱码问题
    import os
    os.system("chcp 65001")  # 65001 = UTF-8编码
    
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