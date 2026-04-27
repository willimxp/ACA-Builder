# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   边界框相关工具函数
#   为combo或building对象添加立方体边框，体现建筑的边界尺寸
import bpy
from mathutils import Vector
from functools import wraps

from .. import utils
from ..const import ACA_Consts as con

# 更新边框尺寸
# 已做成装饰器
def update_boundbox(func):
    """
    装饰器：在函数执行后自动更新combo包裹框尺寸
    用于所有修改单体建筑的函数
    注意：使用延迟导入避免循环导入问题
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        buildingObj = None
        # 找到单体建筑
        if args and hasattr(args[0], 'ACA_data'):
            buildingObj = args[0]
        
        if buildingObj is not None:
            # 查找combo父节点
            from .. import utils
            comboObj = utils.getComboRoot(buildingObj)
            if comboObj == None:
                # 如果有combo，只显示/更新combo边框
                fitBoundBox(buildingObj)
            else:
                # 如果没有combo，只显示/更新building边框
                fitBoundBox(comboObj)
        
        return result
    return wrapper

# 计算合适的边框cube大小
def fitBoundBox(boundObj:bpy.types.Object):
    """
    调整包括对象的大小，使其包裹所有子对象，原点不变
    通过修改网格顶点实现，不影响子对象
    """
    # 查找所有的子对象
    def get_all_visible_children(obj):
        children = []
        for child in obj.children:
            # 仅加入可见对象
            if not child.hide_get() and not child.hide_viewport:
                children.append(child)
                # 树状结构递归
                children.extend(get_all_visible_children(child))
        return children
    all_children = get_all_visible_children(boundObj)
    if not all_children:
        return
    
    # 最小坐标
    min_co = Vector((float('inf'), float('inf'), float('inf')))
    # 最大坐标
    max_co = Vector((float('-inf'), float('-inf'), float('-inf')))
    
    # 找到最大边框坐标
    for child in all_children:
        for corner in child.bound_box:
            global_corner = child.matrix_world @ Vector(corner)
            for i in range(3):
                min_co[i] = min(min_co[i], global_corner[i])
                max_co[i] = max(max_co[i], global_corner[i])
    
    # 转换为局部坐标
    combo_matrix_inv = boundObj.matrix_world.inverted()
    local_min = combo_matrix_inv @ min_co
    local_max = combo_matrix_inv @ max_co
    
    # 边框的扩展宽度，combo和building可以不一样
    if boundObj.ACA_data.aca_type == con.ACA_TYPE_COMBO:
        span = con.BOUNDBOX_SPAN_COMBO
    else:
        span = con.BOUNDBOX_SPAN_BUILDING
    local_min = Vector((local_min.x - span, local_min.y - span, local_min.z - span))
    local_max = Vector((local_max.x + span, local_max.y + span, local_max.z + span))
    
    # 构造cube的8个顶点坐标，直接调整cube大小
    mesh = boundObj.data
    vertices = [
        (local_min.x, local_min.y, local_min.z),
        (local_min.x, local_min.y, local_max.z),
        (local_min.x, local_max.y, local_min.z),
        (local_min.x, local_max.y, local_max.z),
        (local_max.x, local_min.y, local_min.z),
        (local_max.x, local_min.y, local_max.z),
        (local_max.x, local_max.y, local_min.z),
        (local_max.x, local_max.y, local_max.z),
    ]
    for i, v in enumerate(mesh.vertices):
        v.co = vertices[i]
    mesh.update()

    return