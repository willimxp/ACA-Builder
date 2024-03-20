# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   公共的工具方法

import bpy
import bmesh
import math
from mathutils import Vector,Euler,Matrix
import numpy as np
import time

from . import data

# 弹出提示框
def showMessageBox(message = "", title = "Message Box", icon = 'INFO'):
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
def setCollection(name:str, IsClear=False):
    coll_name = name  # 在大纲中的目录名称
    coll_found = False
    coll = bpy.types.Collection
    for coll in bpy.context.scene.collection.children:
        # 在有多个scene时，名称可能是“china_arch.001”
        if str.find(coll.name,coll_name) >= 0:
            coll_found = True
            coll_name = coll.name
            break   # 找到第一个匹配的目录

    if not coll_found:    
        # 新建collection，不与其他用户自建的模型打架
        outputMsg("Add new collection " + coll_name)
        coll = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(coll)
        # 聚焦到新目录上
        bpy.context.view_layer.active_layer_collection = \
            bpy.context.view_layer.layer_collection.children[-1]
    else:
        # 根据IsClear入参，决定是否要清空目录
        if IsClear:
            # 清空collection，每次重绘
            for obj in coll.objects: 
                bpy.data.objects.remove(obj)
        # 强制关闭目录隐藏属性，防止失焦
        coll.hide_viewport = False
        bpy.context.view_layer.layer_collection.children[coll_name].hide_viewport = False
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
def copyObject(sourceObj:bpy.types.Object, name, 
         parentObj:bpy.types.Object = None, 
         location=(0,0,0),
         singleUser=False):
    # 强制原对象不能隐藏
    IsHideViewport = sourceObj.hide_viewport
    sourceObj.hide_viewport = False
    IsHideRender = sourceObj.hide_render
    sourceObj.hide_render = False
    
    # 复制基本信息
    newObj = bpy.types.Object
    if singleUser :
        newObj.data = sourceObj.data.copy()
    else:
        newObj = sourceObj.copy()
    newObj.name = name
    newObj.location = location
    newObj.parent = parentObj
    bpy.context.collection.objects.link(newObj) 
    # 复制子对象
    if len(sourceObj.children) > 0 :
        for child in sourceObj.children:
            copyObject(child, 
                       child.name, 
                        newObj, 
                        child.location,
                        singleUser) 
    
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

# 查找当前对象的兄弟节点
# 如，根据台基对象，找到对应的柱网对象
def getAcaSibling(object:bpy.types.Object,
                  acaObj_type:str) -> bpy.types.Object:
    siblings = object.parent.children
    sibling = None
    for obj in siblings:
        if obj.ACA_data.aca_type == acaObj_type:
            sibling = obj
    return sibling
        
# 递归查找当前对象的子节点
# 只返回第一个对象，为了偷懒，没有返回所有
# 如，根据台基对象，找到对应的柱网对象
def getAcaChild(object:bpy.types.Object,
                  acaObj_type:str) -> bpy.types.Object:
    children = object.children
    child = None
    for obj in children:
        if obj.ACA_data.aca_type == acaObj_type:
            child = obj
            break # 如果找到，直接停止
        # 递归，深挖下一级子节点
        if len(obj.children) > 0:
            child = getAcaChild(obj,acaObj_type)
            if child != None: break
            
    return child

# 递归查找父节点，输入对象类型
def getAcaParent(object:bpy.types.Object,
                    acaObj_type:str) -> bpy.types.Object:
    parent = object.parent
    parentData : data.ACA_data_obj = parent.ACA_data
    if parentData.aca_type != acaObj_type :
        parent = getAcaParent(parent,acaObj_type)
    
    return parent

# 应用缩放(有时ops.object会乱跑，这里确保针对台基对象)      
def applyScale(object:bpy.types.Object):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = object
    object.select_set(True)
    bpy.ops.object.transform_apply(
        scale=True,
        rotation=False,
        location=False,
        isolate_users=True) # apply多用户对象时可能失败，所以要加上这个强制单用户

def applyTransfrom(ob, 
                    use_location=False, 
                    use_rotation=False, 
                    use_scale=False):
    mb = ob.matrix_basis
    I = Matrix()
    loc, rot, scale = mb.decompose()

    # rotation
    T = Matrix.Translation(loc)
    R = mb.to_3x3().normalized().to_4x4()
    S = Matrix.Diagonal(scale).to_4x4()

    transform = [I, I, I]
    basis = [T, R, S]

    def swap(i):
        transform[i], basis[i] = basis[i], transform[i]

    if use_location:
        swap(0)
    if use_rotation:
        swap(1)
    if use_scale:
        swap(2)
        
    M = transform[0] @ transform[1] @ transform[2]
    if hasattr(ob.data, "transform"):
        ob.data.transform(M)
    for c in ob.children:
        c.matrix_local = M @ c.matrix_local
        
    ob.matrix_basis = basis[0] @ basis[1] @ basis[2]

# 强制聚焦到对象
def focusObj(object:bpy.types.Object):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = object
    object.select_set(True)

# 删除树状层次下的所有对象
def deleteHierarchy(parent_obj:bpy.types.Object,with_parent=False):
    #utils.outputMsg("deleting...")
    if parent_obj == None:
        # 没有可删除的对象
        return
    bpy.ops.object.select_all(action='DESELECT')
    obj = bpy.data.objects[parent_obj.name]
    obj.animation_data_clear()
    names = set()
    # Go over all the objects in the hierarchy like @zeffi suggested:
    def get_child_names(obj):
        for child in obj.children:
            names.add(child.name)
            if child.children:
                get_child_names(child)

    get_child_names(obj)
    
    # 是否删除根节点？
    if with_parent:
        names.add(parent_obj.name)
    objects = bpy.data.objects
    # Remove the animation from the all the child objects
    if names:
        for child_name in names:
            # bpy.data.objects[child_name].animation_data_clear()
            # objects[child_name].select_set(state=True)
            # utils.outputMsg("remove child： " +child_name)
            bpy.data.objects.remove(objects[child_name])
        # utils.outputMsg ("Successfully deleted object")
    # else:
    #     utils.outputMsg ("Could not delete object")

# 计算两个点之间距离
# 使用blender提供的mathutils库中的Vector类
# https://sinestesia.co/blog/tutorials/calculating-distances-in-blender-with-python/
def getVectorDistance(point1: Vector, point2: Vector) -> float:
    """Calculate distance between two points.""" 
    return (point2 - point1).length

# 把对象旋转与向量对齐
# 对象要求水平放置，长边指向+X方向
# 向量为原点到坐标点，两点需要先相减
# 返回四元向量
def alignToVector(vector) -> Vector:
    quaternion = vector.to_track_quat('X','Z')
    euler = quaternion.to_euler('XYZ')
    return euler

# 根据起始点，创建连接的矩形
# 长度在X轴方向
def addCubeBy2Points(start_point:Vector,
                     end_point:Vector,
                     deepth:float,
                     height:float,
                     name:str,
                     root_obj:bpy.types.Object,
                     origin_at_bottom = False,
                     origin_at_end = False,
                     origin_at_start=False):
    length = getVectorDistance(start_point,end_point)
    if origin_at_end:
        origin_point = end_point
    elif origin_at_start:
        origin_point = start_point
    else:
        origin_point = (start_point+end_point)/2
    rotation = alignToVector(start_point - end_point)
    rotation.x = 0 # 避免x轴翻转
    bpy.ops.mesh.primitive_cube_add(
                size=1.0, 
                calc_uvs=True, 
                enter_editmode=False, 
                align='WORLD', 
                location = origin_point, 
                rotation = rotation, 
                scale=(length, deepth,height))
    cube = bpy.context.object
    cube.name = name
    cube.parent = root_obj

    # 将Origin置于底部
    if origin_at_bottom :
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.transform.translate(value=(0,0,height/2))
        bpy.ops.object.mode_set(mode = 'OBJECT')
    if origin_at_end :
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.transform.translate(value=(length/2,0,0),orient_type='LOCAL')
        bpy.ops.object.mode_set(mode = 'OBJECT')
    if origin_at_start :
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.transform.translate(value=(-length/2,0,0),orient_type='LOCAL')
        bpy.ops.object.mode_set(mode = 'OBJECT')

    return cube

# 获取对象的原始尺寸
# 排除modifier的影响
# 参考 https://blender.stackexchange.com/questions/238109/how-to-set-the-dimensions-of-an-object-without-its-modifiers
def getMeshDims(object):
    me = object.data
    if object.type == "CURVE":
        me = bpy.data.meshes.new_from_object(object)

    coords = np.empty(3 * len(me.vertices))
    me.vertices.foreach_get("co", coords)

    x, y, z = coords.reshape((-1, 3)).T

    return Vector((
            x.max() - x.min(),
            y.max() - y.min(),
            z.max() - z.min()
            ))

# 绘制六边形，用于窗台、槛墙等
def drawHexagon(dimensions,location):
    # 创建bmesh
    bm = bmesh.new()
    # 各个点的集合
    vectors = []

    # 六边形位移距离
    offset = dimensions.y/math.tan(math.radians(60))
    # 左顶点
    v1=Vector((-dimensions.x/2,
               0,
               -dimensions.z/2))
    vectors.append(v1)
    # 左上点
    v2=Vector((
        -dimensions.x/2+offset,
        dimensions.y/2,
        -dimensions.z/2))
    vectors.append(v2)
    # 右上点
    v3=Vector((
        dimensions.x/2-offset,
        dimensions.y/2,
        -dimensions.z/2))
    vectors.append(v3)
    # 右顶点
    v4=Vector((dimensions.x/2,
               0,
               -dimensions.z/2))
    vectors.append(v4)
    # 右下点
    v5=Vector((
        dimensions.x/2-offset,
        -dimensions.y/2,
        -dimensions.z/2))
    vectors.append(v5)
    # 左下点
    v6=Vector((
        -dimensions.x/2+offset,
        -dimensions.y/2,
        -dimensions.z/2))
    vectors.append(v6)

    # 摆放点
    vertices=[]
    for n in range(len(vectors)):
        if n==0:
            vert = bm.verts.new(vectors[n])
        else:
            # 挤出
            return_geo = bmesh.ops.extrude_vert_indiv(bm, verts=[vert])
            vertex_new = return_geo['verts'][0]
            del return_geo
            # 给挤出的点赋值
            vertex_new.co = vectors[n]
            # 交换vertex给下一次循环
            vert = vertex_new
        vertices.append(vert)
    
    # 创建面
    bm.faces.new((vertices[0],vertices[1],vertices[2],vertices[3],vertices[4],vertices[5]))

    # 挤出厚度
    return_geo = bmesh.ops.extrude_face_region(bm, geom=bm.faces)
    verts = [elem for elem in return_geo['geom'] if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0,dimensions.z))


    # 确保face normal朝向
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    # 移动3d cursor，做为bmesh的origin，一般也是起点
    bpy.context.scene.cursor.location = location
    # 任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object
    bm.to_mesh(obj.data)
    obj.data.update()
    bm.free()
    return obj

# 快速执行bpy.ops执行
# 原理上，是禁用了bpy.ops操作时反复更新scene，效果有5倍的提升
# 注意：传入的参数为函数指针
# 如果函数不需要参数可不带括号直接传入
# 如果函数带参数，需要用偏函数或闭包进行封装后传入
# https://blender.stackexchange.com/questions/7358/python-performance-with-blender-operators
def fastRun(func):
    from bpy.ops import _BPyOpsSubModOp
    view_layer_update = _BPyOpsSubModOp._view_layer_update
    def dummy_view_layer_update(context):
        pass
    try:
        _BPyOpsSubModOp._view_layer_update = dummy_view_layer_update
        func()
    finally:
        _BPyOpsSubModOp._view_layer_update = view_layer_update

# 刷新viewport，避免长时间卡死，并可见到建造过程
def redrawViewport():
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
    return 

# 格式化输出内容
def outputMsg(msg:str):
    stime = time.strftime("%H:%M:%S", time.localtime())
    strout = "ACA[" + stime + "]: " + msg
    print(strout)

# 隐藏对象，包括viewport和render渲染
def hideObj(object:bpy.types.Object) : 
    object.hide_set(True)          # 隐藏“眼睛”，暂时隐藏
    object.hide_viewport = True    # 隐藏“屏幕”，不含在viewport中
    object.hide_render = True      # 隐藏“相机”，不渲染

# 创建一个水平放置的圆柱体，可用于桁、椽等构件
def addCylinderHorizontal(radius,depth,name,root_obj,
                location=(0,0,0),
                rotation=(0,0,0),
                edge_num=16):
    # 圆柱旋转到横向摆放（默认为相对World垂直摆放）
    rotation_default = (0,math.radians(90),0)
    cylinder = addCylinder(radius=radius,
        depth=depth,
        location=location,
        rotation=rotation_default,
        name=name,
        root_obj=root_obj,
        edge_num=edge_num
    )
    # apply rotation
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    # 旋转到实际角度
    cylinder.rotation_euler = rotation
    return cylinder

# 根据起始点，创建连接的圆柱体
# 注意，该圆柱体已经经过翻转，长度指向+X轴
def addCylinderBy2Points(radius:float,
                         start_point:Vector,
                         end_point:Vector,
                         name:str,
                         root_obj:bpy.types.Object):
    depth = getVectorDistance(start_point,end_point)
    location = (start_point+end_point)/2
    rotation = alignToVector(end_point-start_point)
    rotation.x = 0 # 避免x轴翻转
    cylinder = addCylinderHorizontal(
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
        name=name,
        root_obj=root_obj
    )
    # 设置origin到椽头，便于后续向外檐出
    # focusObj(cylinder)
    # bpy.context.scene.cursor.location = start_point + root_obj.location
    # bpy.ops.object.origin_set(type='ORIGIN_CURSOR') 
    origin = root_obj.matrix_world @ start_point
    setOrigin(cylinder,origin)
    return cylinder

# 添加阵列修改器
def addModifierArray(object:bpy.types.Object,
                     count:int,
                     offset:float,
                     name='Array',
                     use_relative_offset=False,
                     use_constant_offset=True,
                     ):
    Xarray:bpy.types.ArrayModifier = \
            object.modifiers.new(name,'ARRAY')
    Xarray.count = count
    Xarray.use_relative_offset = use_relative_offset
    Xarray.use_constant_offset = use_constant_offset
    Xarray.constant_offset_displace = offset

# 添加镜像修改器
def addModifierMirror(object:bpy.types.Object,
                      mirrorObj:bpy.types.Object,
                      use_axis,
                      name='Mirror',):
    mod:bpy.types.MirrorModifier = \
            object.modifiers.new(name,'MIRROR')
    mod.mirror_object = mirrorObj
    mod.use_axis = use_axis

# 基于面的裁切
def addBisect(object:bpy.types.Object,
              pStart:Vector,
              pEnd:Vector,
              pCut:Vector,
              clear_outer=False,
              clear_inner=False,)    :
    # 1、计算剪切平面，先将由戗投影到XY平面，再旋转90度
    pstart_project = Vector((pStart.x,pStart.y,0))
    pend_project = Vector((pEnd.x,pEnd.y,0))
    bisect_normal = Vector(pend_project-pstart_project)
    bisect_normal.rotate(Euler((0,0,math.radians(90)),'XYZ'))
    bisect_normal = Vector(bisect_normal).normalized() # normal必须normalized,注意不是normalize

    # 2、选中并裁切
    focusObj(object)  
    bpy.ops.object.convert(target='MESH')   # 应用modifier
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.bisect(
        plane_co=pCut, 
        plane_no=bisect_normal, 
        clear_outer=clear_outer,
        clear_inner=clear_inner,
        use_fill=True
    )
    bpy.ops.object.editmode_toggle()  

# 寻找对象最外侧（远离原点）的面的中心点
# 注意，返回的坐标基于root_obj为parent的local坐标系
def getObjectHeadPoint(object:bpy.types.Object,
                       eval:bool=False,
                       is_symmetry=[False,False,False])-> Vector:
    if eval:
        # 获取应用modifier后的整体对象，包括镜像、阵列等
        # 参考 https://docs.blender.org/api/current/bpy.types.Depsgraph.html
        # 参考 https://blender.stackexchange.com/questions/7196/how-to-get-a-new-mesh-with-modifiers-applied-using-blender-python-api
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = object.evaluated_get(depsgraph)
    else:
        obj_eval = object

    # 发现有的时候获取端点还是会有异常，只能刷一把状态了
    # 比如，歇山山面飞椽的定位就会异常
    updateScene()

    # 将对象的几何数据载入bmesh
    bm = bmesh.new()
    bm.from_mesh(obj_eval.data)

    # 轮询面集合，查找最大值
    headPoint = Vector((0,0,0))
    for face in bm.faces:
        # 面的几何中心点
        faceCenter = face.calc_center_median()
        if faceCenter > headPoint:
            headPoint = faceCenter      
    # 基于origin点进行转换，转换到局部坐标（以root_obj为参考）
    objMatrix  = object.matrix_local
    headPoint= objMatrix @ headPoint
    
    # 如果对称，取正值
    for n in range(len(is_symmetry)):
        if is_symmetry[n]:
            headPoint[n]=abs(headPoint[n])

    bm.free()
    return headPoint

# 复制对象的所有modifier
def copyModifiers(from_0bj,to_obj):
    # 先取消所有选中，以免进入本函数前有其他选择项的干扰
    bpy.ops.object.select_all(action='DESELECT')
    # 分别选中from，to
    from_0bj.select_set(True)
    bpy.context.view_layer.objects.active = from_0bj
    to_obj.select_set(True)
    # 复制modifiers
    bpy.ops.object.make_links_data(type='MODIFIERS')
    # 取消选中
    bpy.ops.object.select_all(action='DESELECT')

# 在坐标点上摆放一个cube，以便直观看到
def showVector(point: Vector,parentObj,name="定位点") -> object :
    bpy.ops.mesh.primitive_cube_add(size=0.3,location=point)
    cube = bpy.context.active_object
    cube.parent = parentObj
    cube.name = name
    return cube

# 设置origin到cursor
# 输入的origin必须为全局坐标系
def setOrigin(object:bpy.types.Object,origin:Vector):
    # 方法一：调用bpy.ops方法
    # bpy.context.scene.cursor.location = origin
    # focusObj(object)
    # bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

    # 方法二：Low Level，其实没有觉得有明显性能区别
    # https://blender.stackexchange.com/questions/16107/is-there-a-low-level-alternative-for-bpy-ops-object-origin-set
    # 强制刷新，以便正确获得object的matrix信息
    updateScene()
    # 转换到相对于object的本地坐标
    origin_local = object.matrix_world.inverted() @ origin
    # 反向移动原点
    mat = Matrix.Translation(-origin_local)
    me = object.data
    if me.is_editmode:
        bm = bmesh.from_edit_mesh(me)
        bm.transform(mat)
        bmesh.update_edit_mesh(me, False, False)
    else:
        me.transform(mat)
    me.update()
    # 再次正向移动，回归到原来位置
    object.matrix_world.translation = origin

# 场景数据刷新
# 特别在fastrun阻塞过程中，bpy.ops等操作的数据无法及时更新，导致执行的错误
# 这时可以手工刷新一次
# 老中医，药到病除的办法
def updateScene():
    #bpy.context.view_layer.update() 

    # 按照文章的说法，这个消耗更低
    dg = bpy.context.evaluated_depsgraph_get() 
    dg.update()

# 刷新viewport，避免长时间卡死，并可见到建造过程
def redrawViewport():
    do = bpy.context.scene.ACA_data.is_auto_redraw
    if do:
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
    return 

# 删除所有无用数据，以免拖累性能
def delOrphan():
    bpy.data.orphans_purge()
    
    for block in bpy.data.collections:
        if block.users == 0:
            bpy.data.collections.remove(block)

    for block in bpy.data.objects:
        if block.users == 0:
            bpy.data.objects.remove(block)
    
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    
    for block in bpy.data.curves:
        if block.users == 0:
            bpy.data.curves.remove(block)

    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)

    for block in bpy.data.textures:
        if block.users == 0:
            bpy.data.textures.remove(block)

    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)
    
    for block in bpy.data.node_groups:
        if block.users == 0:
            bpy.data.node_groups.remove(block)

# 获取对象的几何中心
# 已经在代码中使用评估对象，可以抗阻塞 
# https://blender.stackexchange.com/questions/129473/typeerror-element-wise-multiplication-not-supported-between-matrix-and-vect 
def getMeshCenter(object:bpy.types.Object):
    # 准确获取对象状态，避免脚本阻塞产生
    obj_eval = getEvalObj(object)
    local_bbox_center = 0.125 * sum((Vector(b) for b in obj_eval.bound_box), Vector())
    global_bbox_center = obj_eval.matrix_local @ local_bbox_center
    return global_bbox_center

# 重新设置对象的旋转角，而不改变对象的原来的旋转
def changeOriginRotation(RotationChange,Object:bpy.types.Object):
    # 先预存原旋转角度
    # 当心，原来直接使用返回值出现了bug，中间会变化
    old_rot_x,old_rot_y,old_rot_z = Object.rotation_euler
    # 以飞椽上皮角度做为调节角度
    change_rot_x,change_rot_y,change_rot_z = alignToVector(RotationChange)
    # 先矫枉
    Object.rotation_euler = Euler((
        -change_rot_x,
        -change_rot_y,
        -change_rot_z),'XYZ')
    # Apply
    applyTransfrom(ob=Object,use_rotation=True)
    Object.rotation_euler = Euler(
        (old_rot_x+change_rot_x,
         old_rot_y+change_rot_y,
         old_rot_z+change_rot_z),'XYZ'
    )

# 返回评估对象
# 在代码阻塞过程中，可以及时的计算对象当前的状态，刷新实际的尺寸、旋转和坐标
# 如果在fastrun中出现问题，多试试这个方法
# https://docs.blender.org/api/current/bpy.types.Depsgraph.html
def getEvalObj(object:bpy.types.Object)->bpy.types.Object:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = object.evaluated_get(depsgraph)
    return obj_eval