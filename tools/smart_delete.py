# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   智能删除功能模块，包括智能删除操作符、配置项和键位映射管理

import bpy
from .. import utils
from ..const import ACA_Consts as con
from ..locale.i18n import _

_keymaps = []


def update_smart_delete(self, context):
    """
    更新智能删除设置时的回调函数
    动态注册/注销键位映射
    """
    global _keymaps
    
    if self.enable_smart_delete:
        if not _keymaps:
            wm = bpy.context.window_manager
            kc = wm.keyconfigs.addon
            if kc:
                km = kc.keymaps.new(name="Object Mode", space_type='EMPTY')
                kmi = km.keymap_items.new(
                    idname="aca.smart_delete",
                    type='DEL',
                    value='PRESS',
                )
                _keymaps.append((km, kmi))
    else:
        for km, kmi in _keymaps:
            km.keymap_items.remove(kmi)
        _keymaps.clear()


class SmartDeleteMixin:
    """智能删除配置项混入类"""
    
    enable_smart_delete: bpy.props.BoolProperty(
        default=True,
        name=_("启用智能删除"),
        description=_("启用后，按下Delete键将自动识别ACA建筑构件并调用专用删除方法；禁用后将使用Blender默认删除行为"),
        update=update_smart_delete,
    ) # type: ignore
    
    def draw_smart_delete_prefs(self, layout):
        """绘制智能删除配置UI"""
        row = layout.row()
        row.prop(self, 'enable_smart_delete')


class ACA_OT_smart_delete(bpy.types.Operator):
    """智能删除：自动识别ACA建筑/墙体/踏跺/柱子/月台并调用专用删除方法"""
    bl_idname = "aca.smart_delete"
    bl_label = _("智能删除")
    bl_description = _('智能删除：自动识别ACA建筑/墙体/踏跺/柱子/月台并调用专用删除方法')
    bl_options = {'REGISTER', 'UNDO'}

    WALL_TYPES = (
        con.ACA_TYPE_WALL,
        con.ACA_WALLTYPE_WINDOW,
        con.ACA_WALLTYPE_GESHAN,
        con.ACA_WALLTYPE_BARWINDOW,
        con.ACA_WALLTYPE_MAINDOOR,
        con.ACA_WALLTYPE_FLIPWINDOW,
        con.ACA_WALLTYPE_RAILILNG,
        con.ACA_WALLTYPE_BENCH,
        con.ACA_TYPE_FANG,
    )

    BUILDING_TYPES = (
        con.ACA_TYPE_BUILDING,
        con.ACA_TYPE_BUILDING_JOINED,
    )

    def _filter_valid_objs(self, obj_list):
        """过滤已删除的对象，返回仍然存在的有效对象列表"""
        valid_objs = []
        for obj in obj_list:
            try:
                if obj is not None and obj.name in bpy.data.objects:
                    valid_objs.append(obj)
            except ReferenceError:
                pass
        return valid_objs

    def _classify_object(self, obj):
        """根据对象的aca_type分类，返回对象类型标识"""
        buildingObj, bData, objData = utils.getRoot(obj)
        
        if objData and hasattr(objData, 'aca_type'):
            aca_type = objData.aca_type
            if aca_type in self.BUILDING_TYPES:
                return 'building'
            if aca_type in self.WALL_TYPES:
                return 'wall'
            if aca_type == con.ACA_TYPE_STEP:
                return 'step'
            if aca_type == con.ACA_TYPE_PILLAR:
                return 'pillar'
        
        if bData and hasattr(bData, 'combo_type'):
            if bData.combo_type == con.COMBO_TERRACE:
                return 'terrace'
        
        return 'normal'

    def _select_objects(self, *obj_lists):
        """选中指定的对象列表（支持多个列表参数）"""
        bpy.ops.object.select_all(action='DESELECT')
        for obj_list in obj_lists:
            for obj in obj_list:
                try:
                    obj.select_set(True)
                except ReferenceError:
                    pass

    def execute(self, context):
        selected_objs = context.selected_objects
        
        if not selected_objs:
            self.report({'INFO'}, _("没有选中对象"))
            return {'CANCELLED'}
        
        classified = {
            'building': [],
            'wall': [],
            'step': [],
            'pillar': [],
            'terrace': [],
            'normal': [],
        }
        
        for obj in selected_objs:
            obj_type = self._classify_object(obj)
            classified[obj_type].append(obj)
        
        result = {'FINISHED'}
        
        if classified['building']:
            self._select_objects(classified['building'])
            result = bpy.ops.aca.del_building()
            for key in classified:
                classified[key] = self._filter_valid_objs(classified[key])
        
        if not context.selected_objects:
            return result
        
        if classified['wall']:
            self._select_objects(classified['wall'])
            result = bpy.ops.aca.del_wall()
            self._select_objects(
                classified['step'],
                classified['pillar'],
                classified['terrace'],
                classified['normal']
            )
        
        if classified['step']:
            self._select_objects(classified['step'])
            result = bpy.ops.aca.del_step()
            self._select_objects(
                classified['pillar'],
                classified['terrace'],
                classified['normal']
            )
        
        if classified['pillar']:
            self._select_objects(classified['pillar'])
            result = bpy.ops.aca.del_pillar('INVOKE_DEFAULT')
            self._select_objects(
                classified['terrace'],
                classified['normal']
            )
        
        if classified['terrace']:
            self._select_objects(classified['terrace'])
            result = bpy.ops.aca.terrace_del()
            self._select_objects(classified['normal'])
        
        if classified['normal']:
            try:
                self._select_objects(classified['normal'])
                result = bpy.ops.object.delete(use_global=False, confirm=False)
            except RuntimeError:
                pass
        
        return result


def register_keymaps():
    """注册智能删除的键位映射"""
    global _keymaps
    
    package_name = __name__.split('.')[0]
    preferences = bpy.context.preferences
    addon_prefs = preferences.addons[package_name].preferences
    
    if addon_prefs.enable_smart_delete:
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.addon
        if kc:
            km = kc.keymaps.new(name="Object Mode", space_type='EMPTY')
            kmi = km.keymap_items.new(
                idname="aca.smart_delete",
                type='DEL',
                value='PRESS',
            )
            _keymaps.append((km, kmi))


def unregister_keymaps():
    """注销智能删除的键位映射"""
    global _keymaps
    
    for km, kmi in _keymaps:
        km.keymap_items.remove(kmi)
    _keymaps.clear()


classes = [
    ACA_OT_smart_delete,
]


def register():
    """注册智能删除模块"""
    for cls in classes:
        bpy.utils.register_class(cls)
    register_keymaps()


def unregister():
    """注销智能删除模块"""
    unregister_keymaps()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
