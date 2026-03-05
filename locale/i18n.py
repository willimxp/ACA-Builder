# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   多语言支持模块，提供动态翻译功能

import bpy
from . import en_US

# 全局翻译字典
translations_dict = {}

# 缓存当前语言设置，避免在模块重载期间上下文丢失
_current_language = None

def _translate_zh2en(msg_id, context="*"):
    """使用字典正向翻译（中文 -> 英文）"""
    # 验证字典是否包含英文翻译
    if "en_US" not in translations_dict:
        return None
    en_map = translations_dict["en_US"]

    # 优先根据上下文查找
    key = (context, msg_id)
    if key in en_map:
        return en_map[key]

    # 若上下文未找到，尝试通用上下文
    key = ("*", msg_id)
    if key in en_map:
        return en_map[key]

    return None

def set_language(lang):
    """设置当前语言（由偏好设置更新回调调用）"""
    global _current_language
    _current_language = lang

def get_language():
    """获取当前语言设置"""
    global _current_language
    
    # 1. 优先使用缓存的语言设置
    if _current_language:
        return _current_language
        
    # 2. 尝试从偏好设置获取
    prefs = get_preferences()
    if prefs and hasattr(prefs, 'language'):
        return prefs.language
        
    # 3. 返回默认值
    from ..const import ACA_Consts as con
    return con.DEFAULT_LANGUAGE

def load_translations():
    """从字典文件加载翻译数据"""
    global translations_dict
    translations_dict.update(en_US.data)

def register():
    """向Blender注册翻译数据"""
    load_translations()

    # 260305 不使用Blender自动翻译，以免被劫持
    # 根据用户在插件中设置的语言，由自定义的T()执行翻译
    # 如果启用以下设置，会导致翻译被Blender劫持
    # 如，Blender选择英文，插件偏好选择中文，此时插件会一直显示中文
    # try:
    #     # 使用主包名注册，以便Blender能自动识别UI翻译
    #     package_name = __name__.split('.')[0]
    #     bpy.app.translations.register(package_name, translations_dict)
    # except ValueError:
    #     # 已注册，忽略
    #     pass

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
    
def update_language(self, context):
    """
    更新语言设置时的回调函数
    重新加载相关模块以更新静态UI文本
    """
    import importlib
    import sys
    from .. import panel, operators, data
    from ..tools import auto_register
    
    # print(f"ACA Builder: Switching language to {self.language}...")
    
    # 0. 提前设置i18n模块的语言，避免在重载期间因上下文丢失导致获取偏好设置失败
    set_language(self.language)

    # 1. 获取包名和主模块
    package_name = __name__.split('.')[0]
    if package_name in sys.modules:
        init_module = sys.modules[package_name]
        
        # 2. 注销所有类
        if hasattr(init_module, 'classes'):
            for cls in reversed(init_module.classes):
                try:
                    bpy.utils.unregister_class(cls)
                except Exception as e:
                    # 忽略注销错误，可能是因为类已经被注销
                    pass
    
    # 3. 清除自定义属性
    try:
        data.delprop()
    except Exception as e:
        print(f"delprop error: {e}")

    # 4. 重新加载模块
    # 注意：必须按照依赖顺序重新加载
    try:
        importlib.reload(data)
        importlib.reload(panel)
        # reload(operators) 会导致当前运行的代码上下文失效，但在回调中通常是可以接受的
        # 因为Blender会在回调结束后使用新的类定义
        importlib.reload(operators)
    except Exception as e:
        print(f"Reload modules error: {e}")
        return

    # 5. 重新发现并注册类
    # 使用重新加载后的模块
    try:
        new_classes = auto_register.auto_register_classes(data, panel, operators)
        
        for cls in new_classes:
            try:
                bpy.utils.register_class(cls)
            except ValueError:
                # 类可能已经注册
                print(f"Register class {cls.__name__} error: {e}")
            except Exception as e:
                print(f"Register class {cls.__name__} error: {e}")
        
        # 6. 更新主模块的类列表，以便下次可以正确注销
        if package_name in sys.modules:
            sys.modules[package_name].classes = new_classes
            
        # 7. 重新初始化属性
        data.initprop()
        
        # 8. 刷新界面
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
                
        # print("ACA Builder: Language update completed.")
        return
        
    except Exception as e:
        print(f"Update language failed: {e}")
        import traceback
        traceback.print_exc()
        return

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
    lang_pref = get_language()

    # 若设置为跟随系统，返回Blender环境的当前语言
    if lang_pref == 'FOLLOW':
        lang_pref = bpy.context.preferences.view.language
    
    if lang_pref == 'en_US':
        # 强制英文翻译
        # 如果系统语言是英文，pgettext 可以工作
        # 但如果要在中文系统上强制显示英文，需要手动查找字典
        
        # 手动在字典中查找
        translated_text = _translate_zh2en(msg_id, context)
        if translated_text is not None:
            return translated_text
        
    elif lang_pref == 'zh_HANS':
        # zh_HANS下默认直接返回原文 (因为源码现在是中文)
        return msg_id
        
    else: # FOLLOW (默认)        
        # 委托给 Blender 的翻译系统
        # 这将使用当前 Blender 的语言设置
        return bpy.app.translations.pgettext(msg_id, context)

# 模块导入时自动加载翻译字典，确保在register之前T()函数可用
load_translations()
