# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   多语言支持模块，提供动态翻译功能

import bpy
from . import zh_HANS

# 全局翻译字典
translations_dict = {}

def load_translations():
    """从字典文件加载翻译数据"""
    global translations_dict
    translations_dict.update(zh_HANS.data)

def register():
    """向Blender注册翻译数据"""
    load_translations()
    try:
        # 使用主包名注册，以便Blender能自动识别UI翻译
        package_name = __name__.split('.')[0]
        bpy.app.translations.register(package_name, translations_dict)
    except ValueError:
        # 已注册，忽略
        pass

def unregister():
    """从Blender注销翻译数据"""
    try:
        package_name = __name__.split('.')[0]
        bpy.app.translations.unregister(package_name)
    except ValueError:
        # 已注销，忽略
        pass

def get_preferences():
    """获取插件偏好设置"""
    # 假设插件名称即为包名
    package = __name__.split('.')[0]
    try:
        preferences = bpy.context.preferences.addons[package].preferences
        return preferences
    except (AttributeError, KeyError):
        return None

def T(msg_id, context="*"):
    """
    根据用户偏好翻译消息ID
    
    参数:
        msg_id (str): 待翻译的消息ID
        context (str): 翻译上下文，默认为 "*"
        
    返回:
        str: 翻译后的字符串
    """
    # 默认行为：如果不需要或未找到翻译，则返回原消息ID
    
    prefs = get_preferences()
    from ..const import ACA_Consts as con
    lang_pref =  con.DEFAULT_LANGUAGE # 默认语言选项
    
    if prefs:
        # 假设属性名为 'language'
        if hasattr(prefs, 'language'):
            lang_pref = prefs.language
            
    if lang_pref == 'en_US':
        # 返回原始英文
        return msg_id
        
    elif lang_pref == 'zh_HANS':
        # 强制中文翻译
        # 如果系统语言已经是中文，pgettext 可以正常工作。
        # 但如果要在英文系统上强制显示中文，我们需要手动查找字典。
        # 虽然 bpy.app.translations.pgettext 通常遵循系统语言，
        # 但为了确保效果，我们优先在自己的字典中查找。
        
        # 手动在字典中查找
        if "zh_HANS" in translations_dict:
            # 优先尝试特定上下文
            key = (context, msg_id)
            if key in translations_dict["zh_HANS"]:
                return translations_dict["zh_HANS"][key]
            
            # 尝试通配符上下文
            key = ("*", msg_id)
            if key in translations_dict["zh_HANS"]:
                return translations_dict["zh_HANS"][key]
                
        # 如果字典中未找到，回退到 pgettext（可能是 Blender 内置字符串？）
        # 或者直接返回 msg_id
        return bpy.app.translations.pgettext(msg_id, context)
        
    else: # FOLLOW (默认)
        # 委托给 Blender 的翻译系统
        # 这将使用当前 Blender 的语言设置
        return bpy.app.translations.pgettext(msg_id, context)

# 模块导入时自动加载翻译字典，确保在register之前T()函数可用
load_translations()
