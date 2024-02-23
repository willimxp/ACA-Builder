# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   公共的工具方法

import bpy

# 弹出提示框
def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

# 递归查询，并选择collection，似乎没有找到更好的办法
# Recursivly transverse layer_collection for a particular name
# https://blender.stackexchange.com/questions/127403/change-active-collection
def recurLayerCollection(layerColl, collName):
    found = None
    if (layerColl.name == collName):
        return layerColl
    for layer in layerColl.children:
        found = recurLayerCollection(layer, collName)
        if found:
            return found

# 新建或聚焦当前场景下的目录
# 所有对象建立在插件目录下，以免与用户自建的内容冲突
def setCollection(context:bpy.types.Context, name:str, IsClear=False):
    coll_name = name  # 在大纲中的目录名称
    coll_found = False
    coll = bpy.types.Collection
    for coll in context.scene.collection.children:
        # 在有多个scene时，名称可能是“china_arch.001”
        if str.find(coll.name,coll_name) >= 0:
            coll_found = True
            coll_name = coll.name
            break   # 找到第一个匹配的目录

    if not coll_found:    
        # 新建collection，不与其他用户自建的模型打架
        print("ACA: Add new collection " + coll_name)
        coll = bpy.data.collections.new(coll_name)
        context.scene.collection.children.link(coll)
        # 聚焦到新目录上
        context.view_layer.active_layer_collection = \
            context.view_layer.layer_collection.children[-1]
    else:
        # 根据IsClear入参，决定是否要清空目录
        if IsClear:
            # 清空collection，每次重绘
            for obj in coll.objects: 
                bpy.data.objects.remove(obj)
        # 强制关闭目录隐藏属性，防止失焦
        coll.hide_viewport = False
        context.view_layer.layer_collection.children[coll_name].hide_viewport = False
        # 选中目录，防止用户手工选择其他目录而导致的失焦
        layer_collection = bpy.context.view_layer.layer_collection
        layerColl = recurLayerCollection(layer_collection, coll_name)
        bpy.context.view_layer.active_layer_collection = layerColl
    
    # 返回china_arch目录的对象
    return coll

# 创建一个基本圆柱体，可用于柱等直立构件
def addCylinder(radius,depth,name,root_obj,
                location=(0,0,0),
                rotation=(0,0,0),
                edge_num = 16,
                origin_at_bottom = False):
    # 定义圆柱体圆周面上的面数，不宜太高造成面数负担，也不宜太低影响美观
    bpy.ops.mesh.primitive_cylinder_add(
                        vertices = edge_num, 
                        radius = radius, 
                        depth = depth,
                        end_fill_type='NGON', 
                        calc_uvs=True, 
                        enter_editmode=False, 
                        align='WORLD', 
                        location=location, 
                        rotation=rotation, 
                        scale=(1,1,1)
                    )
    cylinderObj = bpy.context.object
    cylinderObj.name = name
    cylinderObj.parent = root_obj
    cylinderObj.ACA_data.aca_obj = True

    # 将Origin置于底部
    if origin_at_bottom :
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.transform.translate(value=(0,0,depth/2))
        bpy.ops.object.mode_set(mode = 'OBJECT')

    return cylinderObj

# 复制对象（仅复制instance，包括modifier）
def ObjectCopy(sourceObj:bpy.types.Object, name, 
         parentObj:bpy.types.Object, 
         location=(0,0,0),
         singleUser=False):
    # 强制原对象不能隐藏
    IsHideViewport = sourceObj.hide_viewport
    sourceObj.hide_viewport = False
    IsHideRender = sourceObj.hide_render
    sourceObj.hide_render = False
    
    # 复制基本信息
    newObj:bpy.types.Object = sourceObj.copy()
    if singleUser :
        newObj.data = sourceObj.data.copy()
    newObj.name = name
    newObj.location = location
    newObj.parent = parentObj
    bpy.context.collection.objects.link(newObj) 

    # 复制modifier
    bpy.ops.object.select_all(action='DESELECT')
    sourceObj.select_set(True)
    bpy.context.view_layer.objects.active = sourceObj
    newObj.select_set(True)
    bpy.ops.object.make_links_data(type='MODIFIERS') 
    bpy.context.view_layer.objects.active = newObj

    # 恢复原对象的隐藏属性
    sourceObj.hide_viewport = IsHideViewport
    sourceObj.hide_render = IsHideRender
    
    return newObj

# 创建一个基本圆柱体，可用于柱等直立构件
def setAcaProps(aca_obj:bpy.types.Object,
                aca_parent:bpy.types.Object,
                aca_name:str,
                aca_type:str):   
     # 父节点绑定到建筑根节点上  
    aca_obj.parent = aca_parent
    # 对象名称
    aca_obj.name = aca_name
    # 标识为aca对象
    aca_obj.ACA_data.aca_obj = True
    # 标识aca对象类型，如，platform，piller，roof等
    aca_obj.ACA_data.aca_type = aca_type

    # 默认锁定对象的位置、旋转、缩放（用户可自行解锁）
    aca_obj.lock_location = (True,True,True)
    aca_obj.lock_rotation = (True,True,True)
    aca_obj.lock_scale = (True,True,True)

# 查找当前对象的兄弟节点
# 如，根据台基对象，找到对应的柱网对象
def getAcaSibling(object:bpy.types.Object,
                  sibling_type:str) -> bpy.types.Object:
    siblings = object.parent.children
    for obj in siblings:
        if obj.ACA_data.aca_type == sibling_type:
            return obj

# 应用缩放(有时ops.object会乱跑，这里确保针对台基对象)      
def ApplyScale(object:bpy.types.Object):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = object
    object.select_set(True)
    bpy.ops.object.transform_apply(
        scale=True,
        rotation=False,
        location=False,
        isolate_users=True) # apply多用户对象时可能失败，所以要加上这个强制单用户