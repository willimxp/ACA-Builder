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

    # 方案一：勾连搭
    # 两个建筑面阔相等，且为平行相交
    if (bData.x_total == mData.x_total 
        and (fromBuilding.rotation_euler.z ==
              toBuilding.rotation_euler.z)
        ):
        # 是否相交
        buildingSpan = abs(fromBuilding.location.y 
                           - toBuilding.location.y)
        roofSpan = (bData.y_total+mData.y_total)/2+21*bData.DK
        if buildingSpan > roofSpan:
            utils.popMessageBox("建筑不相交，无法进行组合")
            return {'CANCELLED'}
        # 确定勾连搭
        spliceType = 'goulianda'

    # 无法判断拼接方式
    if spliceType == None:
        utils.popMessageBox("无法处理的建筑合并")
        return {'CANCELLED'}
    
    # 2、预处理 ------------------------------------
    from . import buildCombo
    # 建筑集成到一个统一的combo中
    result,comboObj = buildCombo.addCombo(
        [fromBuilding,toBuilding])

    # 3、执行拼接 -------------------------------------
    if spliceType == 'goulianda':
        result = __unionGoulianda(
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
    bData.splice_id = utils.generateID()
    mData.splice_id = utils.generateID()
    # 记录操作
    comboData:acaData = comboObj.ACA_data
    pp = comboData.postProcess.add()
    pp.action = con.POSTPROC_SPLICE
    pp.parameter = f"{bData.splice_id}#{mData.splice_id}"

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
    # 放入frombuilding的Collection中
    cubeColl = boolObj.users_collection[0]
    cubeColl.objects.unlink(boolObj)
    comboColl = comboObj.users_collection[0]
    comboColl.objects.link(boolObj)
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

    utils.focusObj(fromBuilding)

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


