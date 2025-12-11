# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   建筑之间的拼接，包括勾连搭、抱厦、转角等操作

import bpy
import math
import bmesh
from mathutils import Vector,Euler,Matrix,geometry
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import utils
from . import template
from . import buildFloor
from . import buildYardWall
from . import buildRoof
from . import texture as mat
from . import buildCombo

# 建筑拼接
def spliceBuilding(fromBuilding:bpy.types.Object,
                   toBuilding:bpy.types.Object,):
    bData:acaData = fromBuilding.ACA_data
    mData:acaData = toBuilding.ACA_data

    # 1、判断拼接方式 -------------------------------
    spliceType = None
    # 拼接对象可能为单体与combo的拼接，需要将location转换到全局坐标系
    # 251210 可以用translation直接获取全局坐标
    fromLoc = fromBuilding.matrix_world.translation
    toLoc = toBuilding.matrix_world.translation

    # 方案一：勾连搭
    # 两个建筑面阔相等，且为平行相交
    if (bData.x_total == mData.x_total 
        and (fromBuilding.rotation_euler.z ==
              toBuilding.rotation_euler.z)
        ):
        # 是否相交
        buildingSpan = abs(fromLoc.y - toLoc.y)
        roofSpan = (bData.y_total+mData.y_total)/2+21*bData.DK
        if buildingSpan > roofSpan:
            utils.popMessageBox("建筑不相交，无法进行组合")
            return {'CANCELLED'}
        # 确定勾连搭
        spliceType = 'goulianda'

    # 方案二：平行抱厦
    baoshaRot = fromBuilding.rotation_euler.z
    mainRot = toBuilding.rotation_euler.z
    angleDiff = abs(baoshaRot - mainRot)
    xDiff = abs(fromLoc.x - toLoc.x)
    yDiff = abs(fromLoc.y - toLoc.y)
    if (bData.x_total != mData.x_total
        and xDiff < abs(mData.x_total-bData.x_total)/2
        and yDiff > abs(mData.y_total-bData.y_total)/2
        and angleDiff < 0.001
        ):
        
        # 是否相交
        buildingSpan = abs(fromLoc.y - toLoc.y)
        roofSpan = (bData.y_total+mData.y_total)/2+21*bData.DK
        if buildingSpan > roofSpan:
            utils.popMessageBox("建筑不相交，无法进行组合")
            return {'CANCELLED'}

        # 设置面阔较小的为fromBuilding(抱厦)
        if bData.x_total > mData.x_total:
            temp = fromBuilding
            fromBuilding = toBuilding
            toBuilding = temp
            bData:acaData = fromBuilding.ACA_data
            mData:acaData = toBuilding.ACA_data

        # 抱厦为悬山顶
        if bData.roof_style in (
            con.ROOF_XUANSHAN,con.ROOF_XUANSHAN_JUANPENG):
            spliceType = 'parallelXuanshan'
        # 抱厦为歇山顶
        if bData.roof_style in (
            con.ROOF_XIESHAN,con.ROOF_XIESHAN_JUANPENG):
            spliceType = 'parallelXieshan'

    # 无法判断拼接方式
    if spliceType == None:
        utils.popMessageBox("无法处理的建筑合并")
        return {'CANCELLED'}
    
    # 2、预处理 ------------------------------------
    from . import buildCombo
    # 建筑集成到一个统一的combo中
    # 以第一个建筑为origin原点
    result,comboObj = buildCombo.addCombo(
        [toBuilding,fromBuilding])

    # 3、执行拼接 -------------------------------------
    if spliceType == 'goulianda':
        utils.outputMsg("拼接建筑：勾连搭...")
        result = __unionGoulianda(
            fromBuilding,
            toBuilding,
            comboObj,
        )
    if spliceType == 'parallelXuanshan':
        utils.outputMsg("拼接建筑：平行抱厦/悬山...")
        result = __unionParallelXuanshan(
            fromBuilding,
            toBuilding,
            comboObj,
        )
    if spliceType == 'parallelXieshan':
        utils.outputMsg("拼接建筑：平行抱厦/歇山...")
        result = __unionParallelXieshan(
            fromBuilding,
            toBuilding,
            comboObj,
        )
    
    # 4、标注和记录 ——————————————————————————————————
    # 标注颜色
    fromColl = fromBuilding.users_collection[0]
    fromColl.color_tag = 'COLOR_05'
    toColl = toBuilding.users_collection[0]
    toColl.color_tag = 'COLOR_05'
    # 给拼接对象编号
    # 如果没有编号，则自动生成
    # 如果有编号，是否有其他重复的对象，如果有则重新生成，
    # 没有没有重复对象，则保留原编号
    __setSpliceID(fromBuilding)
    __setSpliceID(toBuilding)
    # 记录操作
    comboData:acaData = comboObj.ACA_data
    pp = comboData.postProcess.add()
    pp.action = con.POSTPROC_SPLICE
    pp.parameter = f"{bData.splice_id}#{mData.splice_id}"

    # 5、聚焦在主建筑
    utils.focusObj(toBuilding)

    return result

# 建筑拼接：勾连搭
# 适用于主建筑和副建筑平行，且面阔相等
def __unionGoulianda(fromBuilding:bpy.types.Object,
                     toBuilding:bpy.types.Object,
                     comboObj:bpy.types.Object):    
    # 载入数据
    bData = fromBuilding.ACA_data
    dk = bData.DK
    
    # 计算屋顶碰撞点
    crossPoint = __getRoofCrossPoint(fromBuilding,toBuilding)
    if 'CANCELLED' not in crossPoint: 
        # 将碰撞点转换到combo坐标系
        if comboObj:
            crossPoint = comboObj.matrix_world.inverted() @ crossPoint
    else:
        # 如果屋顶碰撞失败，则取主建筑临近副建筑的额枋外皮
        boolY = (bData.y_total+con.EFANG_LARGE_Y*dk+0.01)/2
        if fromBuilding.location.y > toBuilding.location.y:
            boolY *= -1
        crossPoint = Vector((0,boolY,0))
        # 基于主建筑转换坐标
        crossPoint = fromBuilding.matrix_local @ crossPoint

    # 生成剪切体 ----------------------------------
    # 1、出檐
    # 椽飞出檐
    eave_extend = (con.YANCHUAN_EX*dk 
              + con.FLYRAFTER_EX*dk)
    # 斗栱出檐
    if bData.use_dg:
        eave_extend += bData.dg_extend*bData.dg_scale[0]
    # 出冲
    eave_extend += bData.chong * con.YUANCHUAN_D*dk
    # 保险数
    eave_extend += 20*dk

    # 2、建筑高度
    buildingH = bData.platform_height + bData.piller_height
    if bData.use_dg:
        buildingH += bData.dg_height * bData.dg_scale[0]
    # 屋顶举高，简单的按进深1:1计算
    buildingH += bData.y_total
    # 保险数
    buildingH += 20*dk

    # 3、裁剪体大小、位置
    boolX = bData.x_total + eave_extend*2
    boolY = bData.y_total + eave_extend*2
    boolDim = (boolX,boolY,buildingH)
    # 根据屋顶碰撞点定位
    if fromBuilding.location.y > toBuilding.location.y:
        offset = boolY/2
    else:
        offset = -boolY/2
    
    boolLoc = (0,
               offset+crossPoint.y, # 碰撞点
               buildingH/2)
    boolObj = utils.addCube(
        name="勾连搭" + con.BOOL_SUFFIX,
        location=boolLoc,
        dimension=boolDim,
        parent=comboObj,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 4、添加bool modifier
    fromChildren = utils.getChildrenHierarchy(fromBuilding)
    for obj in fromChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        # 跳过装修层
        collName = obj.users_collection[0].name
        if con.COLL_NAME_WALL in collName : continue
        utils.addModifierBoolean(
            name='建筑拼接' + con.BOOL_SUFFIX,
            object=obj,
            boolObj=boolObj,
            operation='INTERSECT',
        )

    toChildren = utils.getChildrenHierarchy(toBuilding)
    for obj in toChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        utils.addModifierBoolean(
            name='建筑拼接' + con.BOOL_SUFFIX,
            object=obj,
            boolObj=boolObj,
            operation='DIFFERENCE',
        )

    return {'FINISHED'}

# 判断屋顶相交点
def __getRoofCrossPoint(fromBuilding:bpy.types.Object,
                        toBuilding:bpy.types.Object,):
    # 主建筑正身坡线
    tileCurve = utils.getAcaChild(
        fromBuilding,con.ACA_TYPE_TILE_CURVE_FB)
    if tileCurve:
        tileCurve_copy = utils.copySimplyObject(
            tileCurve,singleUser=True)
        utils.showObj(tileCurve_copy)
    else:
        utils.outputMsg("无法获取正身坡线")
        return {'CANCELLED'}
    # 副建筑瓦面
    tileGrid = utils.getAcaChild(
        toBuilding,con.ACA_TYPE_TILE_GRID)
    if tileGrid:
        tileGrid_copy = utils.copySimplyObject(
            tileGrid,singleUser=True)
        utils.showObj(tileGrid_copy)
        # 镜像
        utils.addModifierMirror(
            object=tileGrid_copy,
            mirrorObj=toBuilding,
            use_axis=(True,True,False),
            use_bisect=(True,True,False),
            use_merge=True
        )
        utils.applyAllModifer(tileGrid_copy)
    else:
        utils.popMessageBox("无法获取屋面")
        return {'CANCELLED'}

    # 3、计算交点
    intersections = utils.intersect_curve_mesh(
        curve_obj=tileCurve_copy,
        mesh_obj=tileGrid_copy
    )
    if intersections == []:
        tileCurve_copy.location.y = - tileCurve_copy.location.y
        tileCurve_copy.scale.y = -1
        intersections = utils.intersect_curve_mesh(
            curve_obj=tileCurve_copy,
            mesh_obj=tileGrid_copy
        )
        if intersections == []:
            # 回收辅助对象
            utils.delObject(tileCurve_copy)
            utils.delObject(tileGrid_copy)
            utils.delOrphan()
            utils.popMessageBox("建筑没有相交，未做任何裁剪")
            return {'CANCELLED'}
    # # 转换到局部坐标
    # crossPoint = fromBuilding.matrix_world.inverted() @ intersections[0]['location']
    # 251209 使用全局坐标
    crossPoint = intersections[0]['location']

    # 4、回收辅助对象
    utils.delObject(tileCurve_copy)
    utils.delObject(tileGrid_copy)
    utils.delOrphan()
    return crossPoint

# 建筑拼接：平行抱厦-悬山
# fromBuilding为面阔较小的抱厦
def __unionParallelXuanshan(fromBuilding:bpy.types.Object,
                     toBuilding:bpy.types.Object,
                     comboObj:bpy.types.Object):
    # 载入数据
    bData:acaData = fromBuilding.ACA_data
    mData:acaData = toBuilding.ACA_data
    dk = bData.DK

    # 一、裁剪屋顶 ------------------------
    # 包括：装修、斗栱、梁架、椽架
    # 不包括：台基、柱网、装修
    # 1、主建筑屋顶裁剪：宽到柱外皮，深到瓦面交界点，高覆盖建筑高度
    # 瓦面碰撞点
    crossPoint = __getRoofCrossPoint(fromBuilding,toBuilding)
    if 'CANCELLED' in crossPoint: return {'CANCELLED'}
    # 将碰撞点转换到combo坐标系
    if comboObj:
        crossPoint = comboObj.matrix_world.inverted() @ crossPoint

    # 建筑高度
    buildingH = bData.platform_height + bData.piller_height
    if bData.use_dg:
        buildingH += bData.dg_height * bData.dg_scale[0]
    # 屋顶举高，简单的按进深1:1计算
    buildingH += bData.y_total
    # 保险数
    buildingH += 20*dk

    # 出檐
    eave_extend = (con.YANCHUAN_EX*dk 
              + con.FLYRAFTER_EX*dk)
    # 斗栱出檐
    if bData.use_dg:
        eave_extend += bData.dg_extend*bData.dg_scale[0]
    # 保险数
    eave_extend += 20*dk

    # 剪切体尺寸
    boolWidth = bData.x_total + mData.piller_diameter
    boolDeepth = bData.y_total + eave_extend*2
    boolHeight = buildingH

    # 裁剪体定位
    if fromBuilding.location.y > toBuilding.location.y:
        offset = boolDeepth/2
    else:
        offset = -boolDeepth/2
    boolX = 0
    boolY = offset + crossPoint.y # 碰撞点
    boolZ = buildingH/2

    boolObj = utils.addCube(
        name="平行抱厦-悬山-屋瓦-主建筑" + con.BOOL_SUFFIX ,
        location=(boolX,boolY,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=comboObj,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 添加bool modifier
    toChildren = utils.getChildrenHierarchy(toBuilding)
    for obj in toChildren:
        obj:bpy.types.Object
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in obj.name : continue
        # 跳过台基、柱网、装修
        collName = obj.users_collection[0].name
        if con.COLL_NAME_BASE in collName : continue
        if con.COLL_NAME_PILLER in collName : continue
        if con.COLL_NAME_WALL in collName : continue
        utils.addModifierBoolean(
            object=obj,
            boolObj=boolObj,
            operation='DIFFERENCE',
        )

    # 2、抱厦屋顶裁剪：宽度到悬山外侧
    # 裁剪体尺寸
    boolWidth = bData.x_total + 21*2*dk # 悬山出檐
    boolDeepth = bData.y_total + eave_extend*2
    boolHeight = buildingH

    # 裁剪体定位
    if fromBuilding.location.y > toBuilding.location.y:
        offset = boolDeepth/2
    else:
        offset = -boolDeepth/2
    boolX = 0
    boolY = offset + crossPoint.y # 碰撞点
    boolZ = buildingH/2
    
    boolObj = utils.addCube(
        name="平行抱厦-悬山-屋瓦-抱厦" + con.BOOL_SUFFIX ,
        location=(boolX,boolY,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=comboObj,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 添加bool modifier
    fromChildren = utils.getChildrenHierarchy(fromBuilding)
    for obj in fromChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        # 跳过台基、柱网、装修
        collName = obj.users_collection[0].name
        if con.COLL_NAME_BASE in collName : continue
        if con.COLL_NAME_PILLER in collName : continue
        if con.COLL_NAME_WALL in collName : continue
        utils.addModifierBoolean(
            object=obj,
            boolObj=boolObj,
            operation='INTERSECT',
        )

    # 二、裁剪柱网 -------------------------------
    # 沿着主建筑的檐面额枋进行裁剪，以同时保证不破坏主建筑的额枋，同时不产生柱础的重叠
    # 同时，保留了主建筑保修，裁剪了抱厦可能存在的雀替等
    boolWidth= bData.x_total + 21*2*dk # 悬山出檐
    boolDeepth = bData.y_total + eave_extend*2
    boolHeight = buildingH
    # 定位点做在檐柱中线，没有按瓦面碰撞
    # 后出抱厦的定位
    boolY = (boolDeepth-bData.y_total+con.EFANG_LARGE_Y*dk+0.01)/2
    if fromBuilding.location.y < toBuilding.location.y:
        # 前出抱厦的定位
        boolY *= -1
    boolZ = boolHeight/2

    # 位置按主建筑转换
    loc = Vector((boolX,boolY,boolZ))
    loc = fromBuilding.matrix_local @ loc
    boolObj = utils.addCube(
        name="平行抱厦-悬山-柱网" + con.BOOL_SUFFIX ,
        location=loc,
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=comboObj,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 绑定boolean
    toChildren = utils.getChildrenHierarchy(toBuilding)
    for obj in toChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        # 仅裁剪柱网层
        collName = obj.users_collection[0].name
        if con.COLL_NAME_PILLER in collName:
            utils.addModifierBoolean(
                object=obj,
                boolObj=boolObj,
                operation='DIFFERENCE',
            )
        # 裁剪后柱体normal异常，做平滑
        if  '柱子' in obj.name:
            utils.shaderSmooth(obj)
    fromChildren = utils.getChildrenHierarchy(fromBuilding)
    for obj in fromChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        # 仅裁剪柱网层、装修层
        collName = obj.users_collection[0].name
        if (con.COLL_NAME_PILLER in collName
            # 抱厦的装修也按这个范围裁剪，包括雀替等
            or con.COLL_NAME_WALL in collName) :
            utils.addModifierBoolean(
                object=obj,
                boolObj=boolObj,
                operation='INTERSECT',
            )
        if  '柱子' in obj.name:
            # 裁剪后柱体normal异常，做平滑
            utils.shaderSmooth(obj)
    
    # 三、裁剪台基 --------------------------------
    # 从柱做45度斜切
    boolWidth= (bData.x_total 
                + bData.platform_extend *2
                + con.GROUND_BORDER *2
                )
    boolDeepth = (bData.y_total
                  + bData.platform_extend
                  + con.GROUND_BORDER
                  + bData.platform_height*3 # 保留踏跺空间
                  )
    boolHeight = bData.platform_height
    # 定位点做在檐柱中线，没有按瓦面碰撞
    # 后出抱厦的定位
    boolY = (boolDeepth-bData.y_total)/2
    if fromBuilding.location.y < toBuilding.location.y:
        # 前出抱厦的定位
        boolY *= -1
    boolZ = boolHeight/2

    # 位置按主建筑转换
    loc = Vector((boolX,boolY,boolZ))
    loc = fromBuilding.matrix_local @ loc
    boolObj = utils.addCube(
        name="平行抱厦-悬山-台基" + con.BOOL_SUFFIX ,
        location=loc,
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=comboObj,
    )

    # 做45度折角
    # 折角宽度取台基下出
    offset= bData.platform_extend + con.GROUND_BORDER
    # 选择内侧被裁剪的边线做折角
    if fromBuilding.location.y > toBuilding.location.y:
        bevelEdges = [1,9]
    else:
        bevelEdges = [3,6]
    utils.edgeBevel(bevelObj=boolObj,
                    bevelEdges=bevelEdges,
                    bevelOffset=offset)

    # 向两侧推出侧踏跺空间
    # 挤出距离
    extrude_distance = bData.platform_height * 3
    # 编辑模式
    bpy.ops.object.mode_set(mode='EDIT')
    # 载入boolObj的mesh数据
    bm = bmesh.from_edit_mesh(boolObj.data)
    # 全部取消选中
    for face in bm.faces: face.select = False
    # 待挤出的面
    bm.faces.ensure_lookup_table()
    face_refs = [bm.faces[4],bm.faces[7]]
    # 使用面引用逐一挤出
    for target_face in face_refs:
        normal = target_face.normal.copy()
        res = bmesh.ops.extrude_face_region(bm, geom=[target_face])
        bm.verts.ensure_lookup_table()
        new_verts = [ele for ele in res.get('geom', []) 
                     if isinstance(ele, bmesh.types.BMVert)]
        if new_verts:
            bmesh.ops.translate(
                bm, 
                verts=new_verts, 
                vec=normal * extrude_distance)
    # 删除原始被挤出的面
    for f in face_refs:
        try:
            # 有时原面已被替换或合并，remove 前先检查仍在 bm.faces
            if f in bm.faces:
                bm.faces.remove(f)
        except Exception:
            # 忽略删除失败，继续处理
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.update_edit_mesh(boolObj.data ) 
    bm.free() 
    bpy.ops.object.mode_set( mode = 'OBJECT' )

    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    toChildren = utils.getChildrenHierarchy(toBuilding)
    for obj in toChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        # 仅裁剪台基层
        collName = obj.users_collection[0].name
        if con.COLL_NAME_BASE in collName :
            utils.addModifierBoolean(
                object=obj,
                boolObj=boolObj,
                operation='DIFFERENCE',
            )
    fromChildren = utils.getChildrenHierarchy(fromBuilding)
    for obj in fromChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX in obj.name : continue
        # 仅裁剪台基层
        collName = obj.users_collection[0].name
        if con.COLL_NAME_BASE in collName :
            utils.addModifierBoolean(
                object=obj,
                boolObj=boolObj,
                operation='INTERSECT',
            )

    # 四、裁剪抱厦的博缝板
    # 以主建筑的瓦面为基础进行拉伸
    tileGrid = utils.getAcaChild(
        toBuilding,con.ACA_TYPE_TILE_GRID)
    if not tileGrid: raise Exception('无法找到主建筑瓦面')
    tileGrid_copy = utils.copySimplyObject(
        tileGrid,
        singleUser=True,
        name='平行抱厦-悬山-山花板' + con.BOOL_SUFFIX
        )
    # 挂接到合并对象下
    tileGrid_copy.parent = comboObj
    # 重新映射坐标系
    tileGrid_copy.location = (comboObj.matrix_world.inverted()
                              @ tileGrid.parent.matrix_world 
                              @ tileGrid.location)
    utils.showObj(tileGrid_copy)
    utils.focusObj(tileGrid_copy)
    # 镜像
    utils.addModifierMirror(
        object=tileGrid_copy,
        mirrorObj=toBuilding,
        use_axis=(True,True,False),
        use_bisect=(True,True,False),
        use_merge=True
    )
    utils.applyAllModifer(tileGrid_copy)

    # 推出裁剪体
    boolDeepth = bData.y_total
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.new()
    bm = bmesh.from_edit_mesh(tileGrid_copy.data)
    # 选中所有面
    for face in bm.faces: face.select = True
    # 沿Z方向挤出
    extrude_result = bmesh.ops.extrude_face_region(
        bm, geom=bm.faces)
    extruded_verts = [v for v in extrude_result['geom'] 
                      if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(
        bm,
        vec=Vector((0, 0, -boolDeepth)),  # Y轴方向移动
        verts=extruded_verts
    )
    # 沿Y方向缩放0
    # 以所有挤出面的平均中心为原点
    center = Vector((0, 0, 0))
    for v in extruded_verts:
        center += v.co
    center /= len(extruded_verts)
    for v in extruded_verts:
        v.co.z = center.z
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.update_edit_mesh(tileGrid_copy.data ) 
    bm.free() 
    bpy.ops.object.mode_set( mode = 'OBJECT' )
    utils.hideObjFace(tileGrid_copy)
    utils.hideObj(tileGrid_copy)

    fromChildren = utils.getChildrenHierarchy(fromBuilding)
    for obj in fromChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        # 仅裁剪山花望板层
        collName = obj.users_collection[0].name
        if con.COLL_NAME_BOARD in collName :
            utils.addModifierBoolean(
                object=obj,
                boolObj=tileGrid_copy,
                operation='DIFFERENCE',
            )

    return {'FINISHED'}

# 建筑拼接：平行抱厦-歇山
# fromBuilding为面阔较小的抱厦
def __unionParallelXieshan(fromBuilding:bpy.types.Object,
                     toBuilding:bpy.types.Object,
                     comboObj:bpy.types.Object):
    # 载入数据
    bData:acaData = fromBuilding.ACA_data
    mData:acaData = toBuilding.ACA_data
    dk = bData.DK

    # 一、裁剪屋顶 ------------------------
    # 包括：装修、斗栱、梁架、椽架
    # 不包括：台基、柱网、装修
    # 宽到抱厦正身出檐，45度折角
    # 瓦面碰撞点
    crossPoint = __getRoofCrossPoint(fromBuilding,toBuilding)
    if 'CANCELLED' in crossPoint: return {'CANCELLED'}
    # 将碰撞点转换到combo坐标系
    if comboObj:
        crossPoint = comboObj.matrix_world.inverted() @ crossPoint

    # 建筑高度
    buildingH = bData.platform_height + bData.piller_height
    if bData.use_dg:
        buildingH += bData.dg_height * bData.dg_scale[0]
    # 屋顶举高，简单的按进深1:1计算
    buildingH += bData.y_total
    # 保险数
    buildingH += 20*dk

    # 出檐
    eave_extend = (con.YANCHUAN_EX*dk 
              + con.FLYRAFTER_EX*dk)
    # 斗栱出檐
    if bData.use_dg:
        eave_extend += bData.dg_extend*bData.dg_scale[0]
    # 安全保留（包括翘飞椽雀台、勾滴等）
    eave_extend += 20*dk

    # 剪切体尺寸
    boolWidth = bData.x_total + eave_extend*2
    boolDeepth = bData.y_total + eave_extend*2
    boolHeight = buildingH

    # 裁剪体定位
    if fromBuilding.location.y > toBuilding.location.y:
        offset = boolDeepth/2
    else:
        offset = -boolDeepth/2
    boolX = 0
    boolY = offset + crossPoint.y # 碰撞点
    boolZ = buildingH/2
    boolObj = utils.addCube(
        name="平行抱厦-歇山-屋瓦" + con.BOOL_SUFFIX ,
        location=(boolX,boolY,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=comboObj,
    )
    # 做45度折角
    # 折角宽度取檐出
    offset= eave_extend
    # 选择内侧被裁剪的边线做折角
    if fromBuilding.location.y > toBuilding.location.y:
        bevelEdges = [1,9]
    else:
        bevelEdges = [3,6]
    utils.edgeBevel(bevelObj=boolObj,
                    bevelEdges=bevelEdges,
                    bevelOffset=offset)
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 添加bool modifier
    toChildren = utils.getChildrenHierarchy(toBuilding)
    for obj in toChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        # 跳过台基、柱网、装修
        collName = obj.users_collection[0].name
        if con.COLL_NAME_BASE in collName : continue
        if con.COLL_NAME_PILLER in collName : continue
        if con.COLL_NAME_WALL in collName : continue
        utils.addModifierBoolean(
            object=obj,
            boolObj=boolObj,
            operation='DIFFERENCE',
        )

    # 添加bool modifier
    fromChildren = utils.getChildrenHierarchy(fromBuilding)
    for obj in fromChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        # 跳过台基、柱网、装修
        collName = obj.users_collection[0].name
        if con.COLL_NAME_BASE in collName : continue
        if con.COLL_NAME_PILLER in collName : continue
        if con.COLL_NAME_WALL in collName : continue
        utils.addModifierBoolean(
            object=obj,
            boolObj=boolObj,
            operation='INTERSECT',
        )

    # 二、裁剪柱网 -------------------------------
    # 沿着主建筑的檐面额枋进行裁剪，以同时保证不破坏主建筑的额枋，同时不产生柱础的重叠
    # 同时，保留了主建筑保修，裁剪了抱厦可能存在的雀替等
    boolWidth= bData.x_total + 21*2*dk # 歇山出檐
    boolDeepth = bData.y_total + eave_extend*2
    boolHeight = buildingH
    # 定位点做在檐柱中线，没有按瓦面碰撞
    # 后出抱厦的定位
    boolY = (boolDeepth-bData.y_total+con.EFANG_LARGE_Y*dk+0.01)/2
    if fromBuilding.location.y < toBuilding.location.y:
        # 前出抱厦的定位
        boolY *= -1
    boolZ = boolHeight/2
    # 位置按主建筑转换
    loc = Vector((boolX,boolY,boolZ))
    loc = fromBuilding.matrix_local @ loc
    boolObj = utils.addCube(
        name="平行抱厦-歇山-柱网" + con.BOOL_SUFFIX ,
        location=loc,
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=comboObj,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 绑定boolean
    toChildren = utils.getChildrenHierarchy(toBuilding)
    for obj in toChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        # 仅裁剪柱网
        collName = obj.users_collection[0].name
        if con.COLL_NAME_PILLER in collName :
            utils.addModifierBoolean(
                object=obj,
                boolObj=boolObj,
                operation='DIFFERENCE',
            )
        # 裁剪后柱体normal异常，做平滑
        if '柱子' in obj.name:
            utils.shaderSmooth(obj)

    fromChildren = utils.getChildrenHierarchy(fromBuilding)
    for obj in fromChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX in obj.name : continue
        # 仅裁剪柱网和装修
        collName = obj.users_collection[0].name
        if (con.COLL_NAME_PILLER in collName
            # 抱厦的装修也按这个范围裁剪，包括雀替等
            or con.COLL_NAME_WALL in collName) :
            utils.addModifierBoolean(
                object=obj,
                boolObj=boolObj,
                operation='INTERSECT',
            )
        # 裁剪后柱体normal异常，做平滑
        if '柱子' in obj.name:
            utils.shaderSmooth(obj)
    
    # 三、裁剪台基 --------------------------------
    # 从柱做45度斜切
    boolWidth= (bData.x_total 
                + bData.platform_extend *2
                + con.GROUND_BORDER *2
                )
    boolDeepth = (bData.y_total
                  + bData.platform_extend
                  + con.GROUND_BORDER
                  + bData.platform_height*3 # 保留踏跺空间
                  )
    boolHeight = bData.platform_height
    # 定位点做在檐柱中线，没有按瓦面碰撞
    # 后出抱厦的定位
    boolY = (boolDeepth-bData.y_total)/2
    if fromBuilding.location.y < toBuilding.location.y:
        # 前出抱厦的定位
        boolY *= -1
    boolZ = boolHeight/2
    # 位置按主建筑转换
    loc = Vector((boolX,boolY,boolZ))
    loc = fromBuilding.matrix_local @ loc
    boolObj = utils.addCube(
        name="平行抱厦-歇山-台基" + con.BOOL_SUFFIX ,
        location=loc,
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=comboObj,
    )

    # 做45度折角
    # 折角宽度取台基下出
    offset= bData.platform_extend + con.GROUND_BORDER
    # 选择内侧被裁剪的边线做折角
    if fromBuilding.location.y > toBuilding.location.y:
        bevelEdges = [1,9]
    else:
        bevelEdges = [3,6]
    utils.edgeBevel(bevelObj=boolObj,
                    bevelEdges=bevelEdges,
                    bevelOffset=offset)

    # 向两侧推出侧踏跺空间
    # 挤出距离
    extrude_distance = bData.platform_height * 3
    # 编辑模式
    bpy.ops.object.mode_set(mode='EDIT')
    # 载入boolObj的mesh数据
    bm = bmesh.from_edit_mesh(boolObj.data)
    # 全部取消选中
    for face in bm.faces: face.select = False
    # 待挤出的面
    bm.faces.ensure_lookup_table()
    face_refs = [bm.faces[4],bm.faces[7]]
    # 使用面引用逐一挤出
    for target_face in face_refs:
        normal = target_face.normal.copy()
        res = bmesh.ops.extrude_face_region(bm, geom=[target_face])
        bm.verts.ensure_lookup_table()
        new_verts = [ele for ele in res.get('geom', []) 
                     if isinstance(ele, bmesh.types.BMVert)]
        if new_verts:
            bmesh.ops.translate(
                bm, 
                verts=new_verts, 
                vec=normal * extrude_distance)
    # 删除原始被挤出的面
    for f in face_refs:
        try:
            # 有时原面已被替换或合并，remove 前先检查仍在 bm.faces
            if f in bm.faces:
                bm.faces.remove(f)
        except Exception:
            # 忽略删除失败，继续处理
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.update_edit_mesh(boolObj.data ) 
    bm.free() 
    bpy.ops.object.mode_set( mode = 'OBJECT' )

    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    toChildren = utils.getChildrenHierarchy(toBuilding)
    for obj in toChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        # 仅裁剪台基
        collName = obj.users_collection[0].name
        if con.COLL_NAME_BASE in collName :
            utils.addModifierBoolean(
                object=obj,
                boolObj=boolObj,
                operation='DIFFERENCE',
            )

    fromChildren = utils.getChildrenHierarchy(fromBuilding)
    for obj in fromChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX in obj.name : continue
        # 仅裁剪台基
        collName = obj.users_collection[0].name
        if con.COLL_NAME_BASE in collName :
            utils.addModifierBoolean(
                object=obj,
                boolObj=boolObj,
                operation='INTERSECT',
            )

    # 四、裁剪抱厦的博缝板
    # 以主建筑的瓦面为基础进行拉伸
    tileGrid = utils.getAcaChild(
        toBuilding,con.ACA_TYPE_TILE_GRID)
    if not tileGrid: raise Exception('无法找到主建筑瓦面')
    tileGrid_copy = utils.copySimplyObject(
        tileGrid,
        singleUser=True,
        name='平行抱厦-歇山-山花板' + con.BOOL_SUFFIX)
    # 挂接到合并对象下
    tileGrid_copy.parent = comboObj
    # 重新映射坐标系
    tileGrid_copy.location = (comboObj.matrix_world.inverted()
                              @ tileGrid.parent.matrix_world 
                              @ tileGrid.location)
    utils.showObj(tileGrid_copy)
    utils.focusObj(tileGrid_copy)
    # 镜像
    utils.addModifierMirror(
        object=tileGrid_copy,
        mirrorObj=toBuilding,
        use_axis=(True,True,False),
        use_bisect=(True,True,False),
        use_merge=True
    )
    utils.applyAllModifer(tileGrid_copy)

    # 推出裁剪体
    boolDeepth = bData.y_total
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.new()
    bm = bmesh.from_edit_mesh(tileGrid_copy.data)
    # 选中所有面
    for face in bm.faces: face.select = True
    # 沿Z方向挤出
    extrude_result = bmesh.ops.extrude_face_region(
        bm, geom=bm.faces)
    extruded_verts = [v for v in extrude_result['geom'] 
                      if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(
        bm,
        vec=Vector((0, 0, -boolDeepth)),  # Y轴方向移动
        verts=extruded_verts
    )
    # 沿Y方向缩放0
    # 以所有挤出面的平均中心为原点
    center = Vector((0, 0, 0))
    for v in extruded_verts:
        center += v.co
    center /= len(extruded_verts)
    for v in extruded_verts:
        v.co.z = center.z
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.update_edit_mesh(tileGrid_copy.data ) 
    bm.free() 
    bpy.ops.object.mode_set( mode = 'OBJECT' )
    utils.hideObjFace(tileGrid_copy)
    utils.hideObj(tileGrid_copy)

    fromChildren = utils.getChildrenHierarchy(fromBuilding)
    for obj in fromChildren:
        obj:bpy.types.Object
        # 跳过bool对象
        if con.BOOL_SUFFIX in obj.name : continue
        # 仅裁剪山花望板
        collName = obj.users_collection[0].name
        if con.COLL_NAME_BOARD in collName :
            utils.addModifierBoolean(
                object=obj,
                boolObj=tileGrid_copy,
                operation='DIFFERENCE',
            )

    return {'FINISHED'}

# 生成拼接编号
def __setSpliceID(buildingObj:bpy.types.Object):
    # 拼接编号如果不存在，直接生成新ID
    bData:acaData = buildingObj.ACA_data
    if bData.splice_id == '':
        bData['splice_id'] = utils.generateID()
    # 拼接编号如果已经存在，可能是通过模板自动初始化的
    else:
        hasDuplicate = False
        # 查询当前项目，是否有重复的拼接编号
        for obj in bpy.data.objects:
            # 跳过非ACA对象
            if not hasattr(obj,'ACA_data'):continue
            # 跳过自身
            if obj == buildingObj:continue
            # 检查重复
            if obj.ACA_data.splice_id == bData.splice_id:
                hasDuplicate = True
                break

        # 如果有重复的，则更新为新的拼接编号
        if hasDuplicate:
            bData['splice_id'] = utils.generateID()
        # 如果没有重复，则保留原编号
        else:
            pass
        
    return