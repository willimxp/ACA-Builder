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
from . import const
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
    "blender" : (4, 2, 0),
    "version" : (0, 6, 0),
    "location" : "View3D > Properties > ACA Builder",
    "tracker_url": "https://github.com/willimxp/ACA-Builder/issues",
    "doc_url": "https://docs.qq.com/doc/DYXpwbUp1UWR0RXpu",
    "category" : "Add Mesh"
}

# 插件设置 - 单独注册以避免语言切换时重载导致的问题
class ACA_OT_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__.split('.')[0]

    filepath: bpy.props.StringProperty(
        name=_("素材库路径"),
        subtype='FILE_PATH',
    ) # type: ignore

    use_bevel : bpy.props.BoolProperty(
            default = True,
            name = _("是否使用倒角"),
            description = _("取消后，不再使用倒角，直接生成直角构件"),
        ) # type: ignore

    # 260210 Windows CLI中文乱码矫正选项
    fix_windows_cli_encoding : bpy.props.BoolProperty(
            default = True,
            name = _("Windows CLI中文乱码矫正"),
            description = _("在Windows系统上自动设置UTF-8编码以解决中文乱码问题（仅Windows有效）"),
        ) # type: ignore
    
    # 260210 日志配置选项
    log_level: bpy.props.EnumProperty(
        name=_("日志级别"),
        description=_("设置日志记录的详细程度，DEBUG级别会记录更多信息但可能影响性能"),
        items=[
            ('DEBUG', _('调试 (Debug)'), _('详细的调试信息')),
            ('INFO', _('信息 (Info)'), _('一般信息')),
            ('WARNING', _('警告 (Warning)'), _('警告信息')),
            ('ERROR', _('错误 (Error)'), _('错误信息')),
        ],
        default='INFO',
    ) # type: ignore
    
    use_log_rotation: bpy.props.BoolProperty(
        default=True,
        name=_("启用日志轮转"),
        description=_("自动归档旧日志文件，防止日志文件过大"),
    ) # type: ignore

    # 多语言设置
    language: bpy.props.EnumProperty(
        name=_("语言 / Language"),
        description=_("选择显示语言 / Select display language"),
        items=[
            ('FOLLOW', _('跟随系统 (Follow System)'), _('跟随Blender系统语言设置')),
            ('zh_HANS', _('简体中文 (Simplified Chinese)'), _('简体中文')),
            ('en_US', 'English (English)', 'English'),
        ],
        default = const.ACA_Consts.DEFAULT_LANGUAGE,
        update = i18n.update_language,
    ) # type: ignore

    def draw(self, context):
        layout = self.layout

        # 关联素材库
        box = layout.box()
        row = box.row()
        filepath = self.filepath
        if filepath == '':
            row.label(text=_("请设置acaAssets.blend文件的路径:"),icon='LINKED')
        else:
            row.label(text=self.filepath,icon='LINKED')
        row = box.row()
        row.operator(
            "aca.link_assets")
        
        # 260226 多语言设置
        layout.separator()
        box = layout.box()
        box.label(text=_("语言设置 / Language:"), icon='WORLD')
        row = box.row()
        row.prop(self, 'language')
        
        # 260210 日志配置选项
        layout.separator()
        box = layout.box()
        box.label(text=_("日志设置:"), icon='TEXT')
        row = box.row()
        row.prop(self, 'log_level')
        row = box.row()
        row.prop(self, 'use_log_rotation')

        # 使用倒角
        row = layout.row()
        row.prop(self,'use_bevel')
        
        # 260210 Windows CLI中文乱码矫正选项：仅在Windows系统上可用
        row = layout.row()
        is_windows = platform.system() == "Windows"
        if not is_windows:
            row.enabled = False
            self.fix_windows_cli_encoding = False
        row.prop(self,'fix_windows_cli_encoding')

# 自动从模块中发现并注册所有Blender类
# 这样新增类时无需手动添加到这个列表中
classes = auto_register.auto_register_classes(data, panel, operators)

# 可选：打印注册信息到控制台（调试用）
# print(auto_register.get_registration_info(classes))

def register():       
    # ##############################################
    # 0、注册插件设置（单独注册，避免语言切换时被重载）
    bpy.utils.register_class(ACA_OT_Preferences)

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
    # 当Blender设为中文，插件设为英文时，静态文字资源无法及时刷新
    # 重新加载类模块，以便强制刷新类中的静态文字资源
    if addon_prefs.language == 'en_US':
        try:
            i18n.update_language(addon_prefs, bpy.context)
        except Exception as e:
            logger.warning(f"Init language failed: {e}")
    
    # 记录类注册信息
    logger.info(f"成功注册 {len(classes)} 个类")
    logger.debug("类注册详情：")
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
    # 销毁插件设置（单独注销）
    bpy.utils.unregister_class(ACA_OT_Preferences)

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
