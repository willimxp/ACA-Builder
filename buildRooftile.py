# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   屋瓦的营造
import bpy
import bmesh
import math
from mathutils import Vector,Matrix,Euler

from . import utils
from . import buildBeam
from . import template
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from .data import ACA_data_template as tmpData
from . import texture as mat

# 创建瓦作层根节点
# 如果已存在根节点，则一概清空重建
# 暂无增量式更新，或局部更新
def __setTileRoot(buildingObj:bpy.types.Object)->bpy.types.Object:
    # 设置目录
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection(
        con.COLL_NAME_TILE,
        parentColl=buildingColl) 
    
    # 新建或清空根节点
    tileRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_TILE_ROOT)
    if tileRootObj == None:
        # 创建屋顶根对象
        tileRootObj = utils.addEmpty(
            name = con.COLL_NAME_TILE,
            parent = buildingObj,
            location=(0,0,0)
        )
        tileRootObj.ACA_data['aca_obj'] = True
        tileRootObj.ACA_data['aca_type'] = con.ACA_TYPE_TILE_ROOT
    else:
        utils.deleteHierarchy(tileRootObj)
        utils.focusCollByObj(tileRootObj)
    
    # 250108 屋顶层原点改为柱头，椽望层相应抬高到斗栱高度
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    zLoc = bData.platform_height + bData.piller_height 
    # 如果有斗栱，抬高斗栱高度
    if bData.use_dg:
        zLoc += bData.dg_height
        # 是否使用平板枋
        if bData.use_pingbanfang:
            zLoc += con.PINGBANFANG_H*dk
    else:
        # 以大梁抬升檐桁垫板高度，即为挑檐桁下皮位置
        zLoc += con.BOARD_YANHENG_H*dk
    tileRootObj.location.z = zLoc
        
    return tileRootObj

# 绘制正身瓦垄线
# 前后檐direction=‘X'
# 两山direction=’Y‘
def __drawTileCurve(buildingObj:bpy.types.Object,
                    purlin_pos,
                    direction='X',
                    eaveCurve:bpy.types.Curve=None):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )

    # 综合考虑桁架上铺椽、望、灰泥后的效果，主要保证整体线条的流畅
    # 同时与梁思成绘制的图纸进行了拟合，所以也有一定的推测成分
    tileCurveVerts = []

    # p1 檐口点，与大连檐相切，定位瓦当滴水的伸出
    # 250325 p1改为通过eaveCurve中统一计算，避免多处定义而不吻合
    eaveCurveData:bpy.types.Curve = eaveCurve.data
    start_point = eaveCurveData.splines[0].bezier_points[0]
    curve_p1= start_point.co+eaveCurve.location
    tileCurveVerts.append(curve_p1)

    # 第3-5点，从举架定位点做偏移
    # 半桁径+椽径+望板高+灰泥层高 + 筒瓦高
    aData:tmpData = bpy.context.scene.ACA_temp
    tileHeight = aData.circularTile_source.dimensions.z * tileScale
    offset = (con.HENG_COMMON_D*dk /2 
                    + con.YUANCHUAN_D*dk 
                    + con.WANGBAN_H*dk
                    + con.ROOFMUD_H*dk
                    + tileHeight)
    # 从桁檩中心，按法线方向提升
    tile_pos = utils.push_purlinPos(purlin_pos, 
                        -offset, direction)
    
    # 歇山的山面坐标需要根据檐面矫正，否则会产生极大的错误
    if bData.roof_style in (
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG) and direction=='Y':
        purlinPosNew = []
        for p in purlin_pos:
            # 从前后檐面的y坐标，45度对称到两山
            px = p.y + (bData.x_total - bData.y_total)/2
            purlinPosNew.append(Vector((
                px,p.y,p.z)))
        tile_pos = utils.push_purlinPos(
                        purlinPosNew, -offset, direction)
    else:
        tile_pos = utils.push_purlinPos(
                        purlin_pos, -offset, direction)

    for n in range(len(tile_pos)):
        # 盝顶只做到下金桁
        if bData.roof_style == con.ROOF_LUDING:
            if n >1:
                continue
        # 歇山的山面只做到金桁高度（踏脚木位置）
        if (bData.roof_style in (con.ROOF_XIESHAN,
                                 con.ROOF_XIESHAN_JUANPENG,) 
            and direction == 'Y' 
            and n>1): 
                continue
        tileCurveVerts.append(tile_pos[n])

    # 卷棚的前后坡，增加辅助点
    if (bData.roof_style in (
            con.ROOF_XUANSHAN_JUANPENG,
            con.ROOF_YINGSHAN_JUANPENG,
            con.ROOF_XIESHAN_JUANPENG,
            )
        and direction == 'X'
    ):
        # 1、调整囊点
        tileCurveVerts[-1] += Vector((0,
                con.JUANPENG_PUMP*dk,   # 卷棚的囊调整
                0))
        # 2、添加正脊位置的原点
        p1 = tileCurveVerts[-1] + Vector((
                                    0,
                                    -tile_pos[-1].y/2,
                                    con.JUANPENG_POP*dk))
        tileCurveVerts.append(p1)
        # 3、添加一个延伸点
        # 添加一个瓦片重合距离
        p2 = p1 + Vector((0,-tile_pos[-1].y/2,0))
        tileCurveVerts.append(p2)

    # 创建瓦垄曲线
    if direction == 'X':
        tileCurve_name = "前后正身坡线"
    else:
        tileCurve_name = "两山正身坡线"
    tileCurve = utils.addCurveByPoints(
            CurvePoints=tileCurveVerts,
            name=tileCurve_name,
            root_obj=tileRootObj,
            tilt=math.radians(90),
            order_u=4, # 取4级平滑，让坡面曲线更加流畅
            )
    # 设置origin
    utils.setOrigin(tileCurve,curve_p1)
    utils.hideObj(tileCurve)
    return tileCurve

# 绘制侧边瓦垄线，决定了瓦面的宽度、翼角瓦面的曲率
# 前后檐direction=‘X'
# 两山direction=’Y‘
def __drawSideCurve(buildingObj:bpy.types.Object,
                purlin_pos,
                direction='X',
                eaveCurve:bpy.types.Curve=None):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )

    # 计算曲线控制点
    sideCurveVerts = []

    # p1点
    # 250325 p1改为通过eaveCurve传送
    eaveCurveData:bpy.types.Curve = eaveCurve.data
    start_point = eaveCurveData.splines[0].bezier_points[0]
    end_point = eaveCurveData.splines[0].bezier_points[-1]
    p1= end_point.co+eaveCurve.location
    sideCurveVerts.append(p1)

    # 第3-5点，从举架定位点做偏移
    # 庑殿、歇山按照冲三翘四的理论值计算（
    if bData.roof_style in (
        con.ROOF_WUDIAN,
        con.ROOF_XIESHAN,
        con.ROOF_XIESHAN_JUANPENG,
        con.ROOF_LUDING,
    ):
        ex_chong = bData.chong * con.YUANCHUAN_D * dk
        ex_qiqiao = bData.qiqiao * con.YUANCHUAN_D * dk
    else:
        ex_chong = 0
        ex_qiqiao = 0
    # XY方向冲出,Z方向起翘
    offset_cq = Vector((ex_chong,ex_chong,ex_qiqiao))

    # 瓦片与椽架的间隙高度
    # 半桁径+椽径+望板高+灰泥层高 + 筒瓦高
    aData:tmpData = bpy.context.scene.ACA_temp
    tileHeight = aData.circularTile_source.dimensions.z * tileScale
    offset = (con.HENG_COMMON_D*dk /2 
                    + con.YUANCHUAN_D*dk 
                    + con.WANGBAN_H*dk
                    + con.ROOFMUD_H*dk
                    + tileHeight)
    # 从桁檩中心，按法线方向提升
    # 歇山的山面坐标需要根据檐面矫正，否则会产生极大的错误
    if bData.roof_style in (
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG) and direction=='Y':
        purlinPosNew = []
        for p in purlin_pos:
            # 从前后檐面的y坐标，45度对称到两山
            px = p.y + (bData.x_total - bData.y_total)/2
            purlinPosNew.append(Vector((
                px,p.y,p.z)))
        tile_pos = utils.push_purlinPos(
                        purlinPosNew, -offset, direction)
    else:
        tile_pos = utils.push_purlinPos(
                        purlin_pos, -offset, direction)
        
    for n in range(len(tile_pos)):
        # 盝顶只做到下金桁
        if bData.roof_style == con.ROOF_LUDING:
            if n >1:
                continue
        # 歇山的山面只做到金桁高度（踏脚木位置）
        if (bData.roof_style in (con.ROOF_XIESHAN,
                                    con.ROOF_XIESHAN_JUANPENG,)
            and direction == 'Y' 
            and n>1): 
                continue
        
        if direction == 'X':
            # 与檐口P1点X向对齐
            point = Vector((p1.x,tile_pos[n].y,tile_pos[n].z))
            # 檐出、冲出、起翘,不做X方向
            point += offset_cq * Vector((0,1,1))
        else:
            # 与檐口P1点Y向对齐
            point = Vector((tile_pos[n].x,p1.y,tile_pos[n].z))
            # 檐出、冲出、起翘,不做Y方向
            point += offset_cq * Vector((1,0,1))

        sideCurveVerts.append(point)   

    # 卷棚的前后坡，增加辅助点
    if (bData.roof_style in (
            con.ROOF_XUANSHAN_JUANPENG,
            con.ROOF_YINGSHAN_JUANPENG,
            con.ROOF_XIESHAN_JUANPENG,)
        and direction == 'X'
    ):
        # 1、 调整囊点
        sideCurveVerts[-1] += Vector((0,
                con.JUANPENG_PUMP*dk,   # 卷棚的囊调整
                0))
        # 2、 退半步
        JuanSpan = sideCurveVerts[-1].y
        p1 = sideCurveVerts[-1] + Vector((
                0,
                -JuanSpan/2,
                con.JUANPENG_POP*dk))
        sideCurveVerts.append(p1)
        # 3、添加一个延伸点,再退半步
        p2 = p1 + Vector((0,-JuanSpan/2,0))
        sideCurveVerts.append(p2)

    # 绘制翼角瓦垄线
    if direction == 'X':
        sideCurve_name = "前后翼角坡线"
    else:
        sideCurve_name = "两山翼角坡线"
    sideCurve = utils.addCurveByPoints(
            CurvePoints=sideCurveVerts,
            name=sideCurve_name,
            root_obj=tileRootObj,
            order_u=4, # 取4级平滑，让坡面曲线更加流畅
        )
    # 设置origin，与eave curve的origin重合，正身瓦口点
    originPoint = start_point.co + eaveCurve.location
    utils.setOrigin(sideCurve,originPoint)
    utils.hideObj(sideCurve)
    return sideCurve

# 绘制硬山/悬山等2坡顶的檐口线
# 基于传入的purlin_pos计算
def __drawEaveCurve(buildingObj:bpy.types.Object,
                    purlin_pos,
                    direction='X'):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    
    if direction == 'X':
        eaveCurve_name = "前后檐瓦口线"
        if bData.use_flyrafter:
            dly_type = con.ACA_TYPE_RAFTER_DLY_FB
        else:
            dly_type = con.ACA_TYPE_RAFTER_LKM_FB
        proj_v1 = Vector((1,0,0))
    else:
        eaveCurve_name = "两山檐瓦口线"
        if bData.use_flyrafter:
            dly_type = con.ACA_TYPE_RAFTER_DLY_LR
        else:
            dly_type = con.ACA_TYPE_RAFTER_LKM_LR
        proj_v1 = Vector((0,1,0))

    eaveCurveVerts = []

    # 第1点：大连檐中心
    # 大连檐
    dlyObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,dly_type)
    p1 = Vector(dlyObj.location)
    # 筒瓦高度
    aData:tmpData = bpy.context.scene.ACA_temp
    tileHeight = aData.circularTile_source.dimensions.z * tileScale
    # 位移到大连檐外沿+筒瓦高度，瓦当滴水向外延伸
    if direction == 'X':
        offset = Vector((0,
            con.DALIANYAN_H*dk/2 + tileHeight,
            -con.DALIANYAN_Y*dk/2-con.EAVETILE_EX*dk))
    else:
        offset = Vector((0,
            con.DALIANYAN_H*dk/2 + tileHeight,
            con.DALIANYAN_Y*dk/2+con.EAVETILE_EX*dk))
    offset.rotate(dlyObj.rotation_euler)
    p1 += offset
    eaveCurveVerts.append(p1)

    # 第2点：两山端点
    # 为了与垂脊完美匹配，以垂脊线算法为依据，参考__drawFrontRidgeCurve
    # 计算正脊长度
    ridge_x = __getTopRidgeLength(buildingObj,purlin_pos)
    # 计算一层瓦的投影长度(顺檐椽角度)
    offset = Vector((bData.tile_length,0,0))
    yanRafterObj:bpy.types.Object = utils.getAcaChild(
            buildingObj,con.ACA_TYPE_RAFTER_FB)
    offset.rotate(yanRafterObj.rotation_euler)
    # 向外歪一瓦层，做端头盘子的八字转角
    aside = offset.y
    split = con.TILE_CORNER_SPLIT*dk
    p2 = p1 + Vector((ridge_x+aside-split,0,0))

    # 绘制檐口线
    CurvePoints = utils.setEaveCurvePoint(p1,p2,direction)
    eaveCurve = utils.addBezierByPoints(
            CurvePoints=CurvePoints,
            name=eaveCurve_name,
            resolution = con.CURVE_RESOLUTION,
            root_obj=tileRootObj
        )

    # 设置origin
    utils.setOrigin(eaveCurve,p1)
    utils.hideObj(eaveCurve)
    return eaveCurve

# 绘制庑殿/歇山/盝顶等4坡顶的檐口线
# 基于翘飞椽定位线绘制
# 250328 重构，依据翘飞椽曲线进行法线方向的推算，更加完美的防止檐口的穿模
def __drawEaveCurveByCCB(buildingObj:bpy.types.Object,
                    direction='X'):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    
    # 载入翘飞椽定位线
    cfrCurve = utils.getAcaChild(buildingObj,
                con.ACA_TYPE_CORNER_FLYRAFTER_CURVE)
    # 复制并做为瓦面檐口线的基础
    eaveCurve = utils.copyObject(cfrCurve,
                                 parentObj=tileRootObj,
                                 singleUser=True)
    if direction == 'X':
        eaveCurve.name = "前后檐瓦口线"
        eaveCurve.ACA_data['aca_type'] = \
            con.ACA_TYPE_TILE_EAVE_CURVE_FB
        dlyObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,
                          con.ACA_TYPE_RAFTER_DLY_FB)
    else:
        eaveCurve.name = "两山檐瓦口线"
        eaveCurve.ACA_data['aca_type'] = \
            con.ACA_TYPE_TILE_EAVE_CURVE_LR
        dlyObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,
                          con.ACA_TYPE_RAFTER_DLY_LR)
        # 做45度镜像
        pivot = (bData.x_total/2-bData.y_total/2,0,0)
        utils.mirror45(eaveCurve,pivot)
        # 应用变换
        utils.applyTransform(eaveCurve,
                             use_location=True,
                             use_rotation=True,
                             use_scale=True)  

    # 重新构造大连檐上皮外沿的曲线
    # 不能简单的做位移，起点和终点的法线已经不同
    # 借助了豆包进行了分析计算
    eaveCurveData:bpy.types.Curve = eaveCurve.data
    bpoints = eaveCurveData.splines[0].bezier_points
    # ---------------------------------
    # 一、计算起点(起翘点)，简单的按照大连檐斜率进行推算
    # 从大连檐下皮上推的距离，包括一个大连檐和一个筒瓦高度
    aData:tmpData = bpy.context.scene.ACA_temp
    tileHeight = aData.circularTile_source.dimensions.z * tileScale
    liftHeight = con.DALIANYAN_H*dk + tileHeight
    if direction == 'X':
        offset = Vector((0, liftHeight,-con.EAVETILE_EX*dk))
    else:
        offset = Vector((0, liftHeight,con.EAVETILE_EX*dk))
    # 随大连檐翻转
    offset.rotate(dlyObj.rotation_euler)
    bpoints[0].co += offset
    bpoints[0].handle_left += offset
    bpoints[0].handle_right += offset

    # 二、计算终点，先计算终点的切线方向，再计算终点的法线方向
    # 注意，这里要求曲线的twist method为Z_UP
    # 1、计算法线方向
    # 1.1、计算切线方向
    end_point = bpoints[1].co
    handle = bpoints[1].handle_left
    tangent = end_point - handle
    tangent.normalize()
    # 1.2、计算副法线方向
    # 创建一个临时向量，用于叉乘计算
    temp_vector = Vector((0, 0, 1))
    if tangent.cross(temp_vector).length < 1e-6:
        temp_vector = Vector((1, 0, 0))
    # 计算副法线方向
    binormal = tangent.cross(temp_vector).normalized()
    # if direction == 'Y':
    #     binormal = -binormal
    # 1.3、应用倾斜度
    if direction == 'X':
        rotation = Matrix.Rotation(bpoints[1].tilt, 4, tangent)
    else:
        rotation = Matrix.Rotation(-bpoints[1].tilt, 4, tangent)
    # 应用旋转矩阵到法线方向
    binormal.rotate(rotation)
    # 1.4、通过切线和副切线计算法线向量
    normal = tangent.cross(binormal).normalized()

    # 2、沿法线方向，位移终点到大连檐上皮外侧
    if direction == 'X':
        offset = Vector((-liftHeight, con.EAVETILE_EX*dk,0))
    else:
        offset = Vector((-liftHeight, -con.EAVETILE_EX*dk,0))

    end_rot = utils.alignToVector(normal)
    offset.rotate(end_rot)
    bpoints[1].co += offset
    bpoints[1].handle_right += offset
    # 更新控制点
    if direction == 'X':
        bpoints[1].handle_left = (
                (bpoints[0].co.x + bpoints[1].co.x)/2,
                bpoints[0].co.y,
                bpoints[0].co.z)
    else:
        bpoints[1].handle_left = (
                bpoints[0].co.x,
                (bpoints[0].co.y + bpoints[1].co.y)/2,
                bpoints[0].co.z)
    
    # 2.1 延长终点，与角梁相交，以便两片滴水在子角梁头和龙
    # 重新计算曲线切线
    end_point = bpoints[1].co
    prev_point = bpoints[1].handle_left
    tangent2 = end_point - prev_point
    # 子角梁头
    ccbHead = bData.roof_qiao_point.copy()
    # 避让角梁，适当让滴水分开，纯手工调正
    shift = con.JIAOLIANG_Y/2*dk * math.sqrt(2)
    if direction == 'X':
        shiftV = Vector((shift,0,0))
    else:
        shiftV = Vector((0,shift,0))
    ccbHead -= shiftV
    # 计算沿 z 轴旋转 45 度的平面的法向量
    normal45 = Vector((1, -1, 0))
    # 计算从终点沿切线方向到平面的距离
    distance = (ccbHead -end_point).dot(normal45) / tangent2.dot(normal45)
    extended_point = end_point + tangent2 * distance
    bpoints[1].co = extended_point
    if direction == 'X':
        bpoints[1].handle_left = (
                (bpoints[0].co.x + bpoints[1].co.x)/2,
                bpoints[0].co.y,
                bpoints[0].co.z)
    else:
        bpoints[1].handle_left = (
                bpoints[0].co.x,
                (bpoints[0].co.y + bpoints[1].co.y)/2,
                bpoints[0].co.z)

    # 三、延长到正心中点
    # 0号点在起翘点，1号点在子角梁
    # 在0号点前插入正心中点
    bpoints.add(1)
    utils.transBezierPoint(bpoints[1],bpoints[2])
    utils.transBezierPoint(bpoints[0],bpoints[1])
    if direction == 'X':
        bpoints[0].co = Vector(bpoints[1].co) * Vector((0,1,1))
    else:
        bpoints[0].co = Vector(bpoints[1].co) * Vector((1,0,1))

    # 设置origin
    utils.setOrigin(eaveCurve,bpoints[0].co)
    utils.hideObj(eaveCurve)
    return eaveCurve

# 计算瓦垄的数量
def __getTileCols(buildingObj:bpy.types.Object,direction='X'):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    # 瓦垄宽度
    tileWidth = bData.tile_width

    # 计算瓦面宽度
    # 硬山、悬山（卷棚）做到大连檐
    ''' 大连檐计算长度时，自动包括了硬山的山墙 '''
    if (bData.roof_style in (con.ROOF_XUANSHAN,
                             con.ROOF_YINGSHAN,
                             con.ROOF_YINGSHAN_JUANPENG,
                             con.ROOF_XUANSHAN_JUANPENG) 
        and direction=='X'):
        # 硬山、悬山的山面不出跳（檐面正常出跳）
        dlyObj:bpy.types.Object = \
            utils.getAcaChild(
                buildingObj,con.ACA_TYPE_RAFTER_DLY_FB)
        roofWidth = utils.getMeshDims(dlyObj).x / 2 
    
    # 歇山、庑殿按出檐、出跳、出冲、起翘计算
    if bData.roof_style in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
            con.ROOF_LUDING):
        if direction=='X':
            # 通面阔
            tongmiankuo = bData.x_total
        else:
            tongmiankuo = bData.y_total
        # 半侧通面阔 + 檐出
        roofWidth = tongmiankuo/2+ con.YANCHUAN_EX*dk
        # 飞椽出
        if bData.use_flyrafter:
            roofWidth += con.FLYRAFTER_EX*dk
        # 斗栱出跳
        if bData.use_dg:
            roofWidth += bData.dg_extend
        # 翼角冲出
        roofWidth += bData.chong * con.YUANCHUAN_D * dk
    
    # 板瓦居中，所以多算半垄板瓦宽度
    roofWidth += tileWidth/2

    # 瓦垄数（完整的板瓦列数，包括居中的半列）
    tileCols = math.floor(roofWidth / tileWidth)
    if tileCols == 0 : tileCols += 1

    return tileCols

# 绘制瓦面网格，依赖于三条曲线的控制
def __drawTileGrid(
            buildingObj:bpy.types.Object,
            rafter_pos,
            direction='X'):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale
    
    # 瓦片长度
    tileLength = aData.circularTile_source.dimensions.y * tileScale

    # 计算瓦垄的数量（包括居中列板瓦的半幅屋面列数）
    tileCols = __getTileCols(buildingObj,direction)

    # 在网格上以半垄划分，分别对应到板瓦和筒瓦
    GridCols = tileCols*2
    
    if direction == 'X':
        tileGrid_name = "前后檐瓦面"
    else:
        tileGrid_name = "两山瓦面"

    # 1、生成三条辅助线，这是后续所有计算的基础
    # 绘制檐口线
    # 对于硬山/悬山，根据椽架进行计算
    if bData.roof_style in (con.ROOF_XUANSHAN,
                            con.ROOF_YINGSHAN,
                            con.ROOF_YINGSHAN_JUANPENG,
                            con.ROOF_XUANSHAN_JUANPENG):
        EaveCurve = __drawEaveCurve(buildingObj,rafter_pos,direction)
    # 对于庑殿、歇山、盝顶等，根据翼角翘飞椽定位线计算
    else:
        EaveCurve = __drawEaveCurveByCCB(buildingObj,direction)
    # 绘制正身坡线
    TileCurve:bpy.types.Curve = __drawTileCurve(
        buildingObj,rafter_pos,direction,EaveCurve)
    # 绘制侧边瓦垄线
    SideCurve = __drawSideCurve(buildingObj,
        rafter_pos,direction,EaveCurve)

    # 坡面长度
    # 似乎是2.8版本中新增的方法
    # https://docs.blender.org/api/current/bpy.types.Spline.html#bpy.types.Spline.calc_length
    roofLength = TileCurve.data.splines[0].calc_length()
    # 瓦层数
    tileRows = round(roofLength /tileLength)+1

    # 2、生成瓦面网格
    # 这里采用几何节点实现，利用了resample curve节点，可以生成均匀分布的网格
    # 而python中暂未找到在curve上均匀分配的API
    # 连接资产blender文件中的瓦面对象，直接放到“瓦作层”节点下
    tileGrid:bpy.types.Object = template.loadAssets(
        "瓦面",tileRootObj,hide=False,link=False)
    # 瓦面要与辅助线重合，并上移一个大连檐高度
    tileGrid.location = TileCurve.location
    # 250116 瓦面上移一个筒瓦高，以便卷棚顶筒瓦能够紧密结合
    # tileGrid.location.z += tileHeight
    tileGrid.name = tileGrid_name
    # 输入修改器参数
    gnMod:bpy.types.NodesModifier = \
        tileGrid.modifiers.get('GeometryNodes')
    # 几何节点修改器的传参比较特殊，封装了一个方法
    utils.setGN_Input(gnMod,"正身瓦线",TileCurve)
    utils.setGN_Input(gnMod,"檐口线",EaveCurve)
    utils.setGN_Input(gnMod,"翼角瓦线",SideCurve)
    utils.setGN_Input(gnMod,"瓦片列数",GridCols)
    utils.setGN_Input(gnMod,"瓦片行数",tileRows)  
    # 应用GN modifier
    utils.applyAllModifer(tileGrid)      
    
    # 回写准确的瓦垄宽度
    # 后续也用在计算正脊筒宽度，以便对齐当沟
    # 注意：GridCols不是列数，是划线数，需要减一，
    # 且GridCols是半垄，实际应该乘二
    if direction == 'X':
        bData['tile_width_real'] = tileGrid.dimensions.x/(GridCols-1)*2

    utils.hideObj(tileGrid)
    return tileGrid

# 绘制瓦面的斜切boolean对象
# 分别可以适应庑殿与歇山屋瓦的裁剪（悬山、硬山不涉及）
# 庑殿沿着角梁、由戗裁剪，其中包含了推山的因素
# 歇山基于桁架形状裁剪，其中的歇山转折点做了特殊计算
def __drawTileBool(
        buildingObj:bpy.types.Object,
        purlin_cross_points,
        name='tile.bool',
        direction='X'):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    roofBaseZ = (bData.platform_height 
                 + bData.piller_height )

    # 任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add(
        location=(0,0,0)
    )
    tileboolObj = bpy.context.object
    tileboolObj.name = name
    tileboolObj.data.name = name
    tileboolObj.parent = tileRootObj

    # 创建bmesh
    bm = bmesh.new()
    # 各个点的集合
    vectors = []

    # 起始点，从子角梁头向外延伸，确保包住所有瓦片
    p0 = bData.roof_qiao_point.copy()
    # 为了保险起见，切割体做到建筑的地平高度
    offsetz = p0.z + tileRootObj.location.z
    p0 += Vector((6*dk,6*dk,-offsetz))
    # 插入前点
    vectors.insert(0,p0)
    # 插入后点，即前点的Y镜像
    vectors.append(p0 * Vector((1,-1,1)))

    # 循环添加由戗节点
    for n in range(len(purlin_cross_points)):
        # 这里不加copy，原始值就会被异常修改，python传值还是传指针太麻烦
        cutPoint = purlin_cross_points[n].copy()
        
        # 歇山顶做特殊处理
        if bData.roof_style in (con.ROOF_XIESHAN,
                                con.ROOF_XIESHAN_JUANPENG,):          
            # 正心桁坐标不做处理
            if n == 0: 
                pass
            # 下金桁采用脊桁的坐标定位
            if n == 1:
                # 前后檐的山腰裁剪点，垂脊的定位类似
                # if direction == 'X':
                #     # X向：以脊桁宽度为基准
                #     cutPoint.x = (purlin_cross_points[-1].x
                #             + con.EAVETILE_EX*dk 
                #             - bData.tile_width_real)
                #     # Y向：与起始点做45度连线
                #     cutPoint.y = p0.y - (p0.x - cutPoint.x)
                # if direction == 'Y':
                #     # 偏移，以免山面瓦与前后檐面瓦穿模
                #     cutPoint -= Vector((0,con.JIAOLIANG_Y/2*dk,0))

                # 250227 歇山山面的瓦面与前后檐瓦面相同处理，都裁剪到山花位置
                # 原本为了兼容宋式开放的山花，而把山面瓦一直做到踩步金
                # 但是山面的瓦面从三根曲线生成的不完美，反而导致与前后檐瓦面穿模
                # 所以暂时这样按照清则例处理，与梁思成的图纸也一致
                # X向：以脊桁宽度为基准
                cutPoint.x = (purlin_cross_points[-1].x
                        + con.EAVETILE_EX*dk 
                        - bData.tile_width_real)
                # Y向：与起始点做45度连线
                cutPoint.y = p0.y - (p0.x - cutPoint.x)
            # 上金桁、脊桁不做裁剪点，直接跳过
            if n > 1: 
                continue   
        # # 庑殿特殊处理
        # if bData.roof_style == con.ROOF_WUDIAN: 
        #     if direction == 'Y':
        #         # 退让两山的瓦面
        #         # 以免在夸张的推山系数（如，0.5）时，
        #         # 过于陡峭的坡面，裁剪出现的穿模
        #         cutPoint += Vector((
        #             con.JIAOLIANG_Y/2*dk,
        #             -con.JIAOLIANG_Y/2*dk,
        #             0))
        #         # 避免在Y=0的中点过度退让
        #         if cutPoint.y < 0:
        #             cutPoint.y = 0
        
        # 纵坐标与起始点对齐
        cutPoint.z = p0.z         
        
        # 插入前点
        vectors.insert(0,cutPoint)
        # 插入后点，即前点的Y镜像
        vectors.append(cutPoint*Vector((1,-1,1)))
    
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
    for n in range(len(vertices)//2-1): #注意‘/’可能是float除,用'//'进行整除
        bm.faces.new((
            vertices[n],vertices[n+1], # 两根椽头
            vertices[-n-2],vertices[-n-1] # 两根椽尾
        ))

    # 挤出厚度
    # 裁剪体的高度为了保险起见，从地平一直做到正脊
    # 简化计算即屋顶层的起点高度+举架高度
    # 举架高度进一步简化为通进深*5举
    # 另外考虑斗栱高度，灰泥高度，正脊高度等，粗暴的再加100DK
    height = (roofBaseZ
              + bData.y_total * 0.5
              + 100*dk)
    return_geo = bmesh.ops.extrude_face_region(bm, geom=bm.faces)
    verts = [elem for elem in return_geo['geom'] if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0,height))

    # 确保face normal朝向
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(tileboolObj.data)
    tileboolObj.data.update()
    bm.free()

    # 是否添加细分？
    if bpy.app.version < (4,5,0):
        # 添加细分，可以减少裁剪瓦片时出现的异常毛刺点
        utils.subdivideObject(tileboolObj,level=3)
    else:
        # 4.5以上不要细分，否则反而破坏水密
        pass

    # 添加镜像
    utils.addModifierMirror(
        object=tileboolObj,
        mirrorObj=tileRootObj,
        use_axis=(True,False,False),
    )

    return tileboolObj

# 在face上放置瓦片
def __setTile(
            sourceObj,
            name,
            Matrix,
            offset,
            parent
):    
    TileCopy = utils.copySimplyObject(
        sourceObj=sourceObj,
        name=name,
        parentObj=parent,
    )  
    # 滴水定位，从网格面中心偏移半个瓦垄（实际落在网格线上，也保证了瓦垄居中）
    TileCopy.matrix_local = Matrix
    offset.rotate(TileCopy.rotation_euler)
    TileCopy.location += offset

    # 250110 新增琉璃颜色切换
    mat.setGlazeStyle(TileCopy)
    return TileCopy   

# 在网格上平铺瓦片
def __arrayTileGrid(buildingObj:bpy.types.Object,
                rafter_pos,
                tileGrid:bpy.types.Object,
                direction='X'):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale

    # 载入瓦片资源
    flatTile:bpy.types.Object = utils.copyObject(
        aData.flatTile_source,singleUser=True)
    circularTile:bpy.types.Object = utils.copyObject(
        aData.circularTile_source,singleUser=True)
    eaveTile:bpy.types.Object = utils.copyObject(
        aData.eaveTile_source,singleUser=True)
    dripTile:bpy.types.Object = utils.copyObject(
        aData.dripTile_source,singleUser=True)
    # 根据斗口调整尺度
    flatTile = utils.resizeObj(flatTile, tileScale)
    circularTile = utils.resizeObj(circularTile,tileScale)
    eaveTile = utils.resizeObj(eaveTile,tileScale)
    dripTile = utils.resizeObj(dripTile,tileScale)
    utils.applyTransform(flatTile,use_scale=True)
    utils.applyTransform(circularTile,use_scale=True)
    utils.applyTransform(eaveTile,use_scale=True)
    utils.applyTransform(dripTile,use_scale=True)
    # 应用所有的modifier，以免后续快速合并时丢失
    utils.applyAllModifer(flatTile)
    utils.applyAllModifer(circularTile)
    utils.applyAllModifer(eaveTile)
    utils.applyAllModifer(dripTile)

    # 瓦垄宽度
    tileWidth = bData.tile_width
    # 250116 不再以用户输入瓦垄长，以筒瓦为依据
    # # 瓦片长度
    # tileLength = bData.tile_length
    tileLength = aData.circularTile_source.dimensions.y * tileScale
    tileHeight = aData.circularTile_source.dimensions.z * tileScale
    # 计算瓦垄的数量
    tileCols = __getTileCols(buildingObj,direction)
    GridCols = tileCols*2-1

    # 构造一个裁剪对象，做boolean
    # 瓦面不适合像椽架那样做三个bisect面的切割
    # 因为推山导致的由戗角度交叉，使得三个bisect面也有交叉，导致上下被裁剪的过多
    tile_bool_obj = __drawTileBool(
        buildingObj,rafter_pos,direction=direction)
    
    # 檐面与山面的差异
    if direction=='X':
        # boolean用difference，向外切
        isBoolInside=False
        # 瓦片走向取第一条边
        dir_index = 0
    else:
        tileGrid = utils.flipNormal(tileGrid)
        # boolean用intersec，向内切
        isBoolInside=True
        # 瓦片走向取第二条边
        dir_index = 1

    # 在瓦面网格上依次排布瓦片
    bm = bmesh.new()   # create an empty BMesh
    bm.from_mesh(tileGrid.data)   # fill it in from a Mesh
    tileList = []
    for f in bm.faces:
        # 不能直接用face normal进行定位
        # # 构造矩阵的旋转
        # z_axis = Vector((0, 0, 1))
        # rotation = z_axis.rotation_difference(f.normal)
        # M = rotation.to_matrix().to_4x4()

        # 基于edge，构造Matrix变换矩阵，用于瓦片的定位
        # https://blender.stackexchange.com/questions/177218/make-bone-roll-match-a-face-vertex-normal/177331#177331
        # 取面上第一条边（沿着坡面）
        e = f.edges[dir_index]
        # 边的向量(归一化)，做为Y轴
        y = (e.verts[1].co - e.verts[0].co).normalized()
        # # 平均相邻面的法线，做为边的法线，做为Z轴
        # z = sum((f.normal for f in e.link_faces), Vector()).normalized()
        z = f.normal.normalized()
        # Y/Z轴做叉积，得到与之垂直的X轴
        x = y.cross(z)
        # 坐标系转置（行列互换，以复合blender的坐标系要求）
        M = Matrix((x, y, z)).transposed().to_4x4()

        # 构造矩阵的位移
        M.translation = f.calc_center_median()
        
        # 构造矩阵的缩放
        # 按照网格长度缩放筒板瓦
        # 网格边长
        cellLength = f.edges[dir_index].calc_length()
        # 筒瓦边长
        tileLength = aData.circularTile_source.dimensions.y * tileScale
        # 缩放比例
        scale_factor = cellLength/tileLength
        # 在矩阵中添加缩放
        # 250610 这里不需要根据direction的X/Y来缩放，统一在Y缩放即可
        scale_matrix = Matrix.Scale(scale_factor, 4, (0, 1, 0))
        M =  M @ scale_matrix
    
        # 250116 瓦片布在网格几何中心，
        # 并对齐筒瓦顶面，以避免卷棚顶筒瓦的间隙
        if direction=='X':
            offset_aside = Vector((
                bData.tile_width_real/4,
                -cellLength/2,
                -tileHeight))
            offset_head = Vector((
                bData.tile_width_real/4,
                cellLength/2,
                -tileHeight))
        else:
            offset_aside = Vector((
                -bData.tile_width_real/4,
                -cellLength/2,
                -tileHeight))
            offset_head = Vector((
                -bData.tile_width_real/4,
                cellLength/2,
                -tileHeight)) 
        
        # 241113 修正bug：原来的筒板瓦排布时从檐口的瓦面face开始计算，
        # 实际上第一行应该是勾头滴水的normal，筒板瓦应该从第二行的face开始计算
        # 排布板瓦，仅在偶数列排布
        if ((f.index%GridCols) % 2 == 0
            # 不做最后一列板瓦，以免与排山勾滴重叠
            and f.index%GridCols != GridCols-1
            and f.index >= GridCols):
            tileObj = __setTile(
                sourceObj=flatTile,
                name='板瓦',
                Matrix=M,
                offset=offset_aside.copy(),
                parent=tileGrid,
            )
            tileList.append(tileObj)

        # 排布筒瓦，奇数列排布
        if (f.index%GridCols) % 2 == 1 and f.index >= GridCols:
            tileObj = __setTile(
                sourceObj=circularTile,
                name='筒瓦',
                Matrix=M,
                offset=offset_aside.copy(),
                parent=tileGrid,
            )
            tileList.append(tileObj)

        # 排布檐口瓦
        if f.index < GridCols:# 第一行
            # 排布滴水
            if f.index % 2 == 0:
                tileObj = __setTile(
                    sourceObj=dripTile,
                    name='滴水',
                    Matrix=M,
                    offset=offset_head.copy(),
                    parent=tileGrid,
                )
                # 硬山、悬山（卷棚）最后一个滴水做斜切
                if bData.roof_style in (
                            con.ROOF_YINGSHAN,
                            con.ROOF_YINGSHAN_JUANPENG,
                            con.ROOF_XUANSHAN,
                            con.ROOF_XUANSHAN_JUANPENG
                        ):
                    if f.index%GridCols == GridCols-1:
                        utils.addBisect(
                            object=tileObj,
                            pStart=tileGrid.matrix_world @ Vector((0,0,0)),
                            pEnd=tileGrid.matrix_world @ Vector((1,1,0)),
                            pCut=tileGrid.matrix_world @ f.calc_center_median(),
                            clear_inner=True
                        )
                tileList.append(tileObj) 

            # 排布瓦当
            if f.index % 2 == 1:
                tileObj = __setTile(
                    sourceObj=eaveTile,
                    name='瓦当',
                    Matrix=M,
                    offset=offset_head.copy(),
                    parent=tileGrid,
                )
                tileList.append(tileObj)
    
    # 合并所有的瓦片对象
    # 可以极大的提高重新生成时的效率（海量对象删除太慢了）
    if direction == 'X':
        tileSetName = '前后檐'
    else:
        tileSetName = '两山'
    tileSet = utils.joinObjects(
        tileList,newName = '屋瓦.' + tileSetName)
    # 将屋瓦绑定到根节点
    utils.changeParent(tileSet,tileRootObj)
    # 庑殿、歇山做裁剪
    if bData.roof_style in (
                con.ROOF_WUDIAN,
                con.ROOF_XIESHAN,
                con.ROOF_XIESHAN_JUANPENG,
                con.ROOF_LUDING,):
        if isBoolInside:
            operation = 'INTERSECT'
        else:
            operation = 'DIFFERENCE'
        utils.addModifierBoolean(
            object=tileSet,
            boolObj=tile_bool_obj,
            operation=operation,
        )
    # 添加镜像
    utils.addModifierMirror(
        object=tileSet,
        mirrorObj=tileRootObj,
        use_axis=(True,True,False),
        use_bisect=(True,True,False),
        use_merge=True, # 合并接缝的点，实现水密
    )

    # 250110 重展UV
    # 实际在__setTile中已经做了setGlazeStyle，但仅基于单个瓦片
    # 将active_material落在筒板瓦的瓦面上
    # 250209 注意，瓦面同时使用琉璃和瓦当两个材质
    # 所以计算active material时，需要乘2
    tileSet.active_material_index = int(bData.tile_color)*2
    # 这里在modifier的平铺范围上做全局的UV平铺
    # 250209 使用cubeProject时有明显的横纹，改为smartProject
    mat.setGlazeUV(tileSet,uvType=None)

    # 隐藏辅助对象
    utils.hideObj(tile_bool_obj)

    bpy.data.objects.remove(flatTile)
    bpy.data.objects.remove(circularTile)
    bpy.data.objects.remove(eaveTile)
    bpy.data.objects.remove(dripTile)

# 计算正脊长度
# 并且可以在硬山、悬山、歇山的垂脊、排山勾滴等复用
def __getTopRidgeLength(buildingObj: bpy.types.Object,
        rafter_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = bData.piller_diameter

    # 硬山正脊，山墙向内半垄瓦
    if bData.roof_style in (
            con.ROOF_YINGSHAN,
            con.ROOF_YINGSHAN_JUANPENG,
            ):
        zhengji_length = (bData.x_total/2
            + con.SHANQIANG_WIDTH*dk
            -bData.tile_width_real/2
            )
    # 悬山正脊，从槫头向内半垄
    elif bData.roof_style in (
            con.ROOF_XUANSHAN,
            con.ROOF_XUANSHAN_JUANPENG,
            ):
        zhengji_length = (rafter_pos[-1].x
            -bData.tile_width_real/2)
    # 庑殿正脊外皮与垂脊相交
    elif bData.roof_style == con.ROOF_WUDIAN:
        zhengji_length = (rafter_pos[-1].x
            + bData.tile_width_real/2)
    # 歇山正脊对齐排山勾滴定位
    elif bData.roof_style in (
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
            ):
        # 从槫头向内微调，不要到半垄，以免排山勾滴过大
        # 因为排山勾滴要保持与博缝板的关系，不能调整
        # 还需要继续观察效果
        zhengji_length = (rafter_pos[-1].x
                -bData.tile_width_real/4)
        # 矫正到瓦垄中心(可能在筒瓦上，也可能在板瓦上)
        zhengji_length = __getTileCoord(
            buildingObj, zhengji_length)
    else:
        zhengji_length = 0

    return zhengji_length

# 营造顶部正脊
def __buildTopRidge(buildingObj: bpy.types.Object,
                 rafter_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale

    # 创建正脊
    # 定位：脊槫上皮+椽径+望板高+灰泥层高
    offset = (con.HENG_COMMON_D*dk /2       # 脊槫上皮
                + con.YUANCHUAN_D*dk        # 椽架厚度
                + con.WANGBAN_H*dk          # 望板厚度
                + con.ROOFMUD_H*dk )        # 灰泥厚度
    # 根据最后一根椽子的斜率，将法线高度换算到垂直高度
    angle = ((rafter_pos[-1].z-rafter_pos[-2].z)
           /(rafter_pos[-2].y-rafter_pos[-1].y))
    offsetZ = offset / math.cos(math.atan(angle))
    zhengji_z = rafter_pos[-1].z + offsetZ
    # 向下调减1斗口（纯粹为了好看，没啥依据）
    zhengji_z += con.RIDGE_OFFSET * dk
    
    # 根据庑殿、歇山、悬山、硬山的不同，计算正脊长度
    zhengji_length = __getTopRidgeLength(
        buildingObj,rafter_pos)

    # 攒尖顶仅做宝顶
    if (bData.x_total == bData.y_total 
        and bData.roof_style==con.ROOF_WUDIAN):
        baodingObj = utils.copyObject(
            sourceObj=aData.baoding_source,
            name='宝顶',
            location=(0,0,zhengji_z),
            parentObj=tileRootObj,
            singleUser=True,
            )
        # 根据斗口调整尺度
        utils.resizeObj(baodingObj,tileScale)
        # 退出，不再做后续的正脊和螭吻
        return
    
    # 载入正脊资产对象
    roofRidgeObj = utils.copyObject(
        sourceObj=aData.ridgeTop_source,
        name="正脊",
        location=(0,0,zhengji_z),
        parentObj=tileRootObj,
        singleUser=True)
    # 根据斗口调整尺度
    utils.resizeObj(roofRidgeObj,tileScale)
    # 与瓦垄宽度匹配
    roofRidgeObj.dimensions.x = bData.tile_width_real
    utils.applyTransform(roofRidgeObj,use_scale=True)
    # 脊筒坐中
    roofRidgeObj.location.x = - roofRidgeObj.dimensions.x/2
    
    # 横向平铺
    modArray:bpy.types.ArrayModifier = \
        roofRidgeObj.modifiers.new('横向平铺','ARRAY')
    modArray.use_relative_offset = True
    modArray.relative_offset_displace = (1,0,0)
    modArray.fit_type = 'FIT_LENGTH' 
    modArray.fit_length = zhengji_length

    # 镜像
    utils.addModifierMirror(
        object=roofRidgeObj,
        mirrorObj=tileRootObj,
        use_axis=(True,False,False),
        use_bisect=(True,False,False),
        use_merge=True,
    )

    # 250113 设置正脊材质
    mat.setGlazeStyle(roofRidgeObj)

    # 摆放螭吻
    chiwenObj = utils.copyObject(
        sourceObj=aData.chiwen_source,
        name='螭吻',
        location=(-zhengji_length,0,zhengji_z),
        parentObj=tileRootObj,
        singleUser=True)
    # 根据斗口调整尺度
    utils.resizeObj(chiwenObj,tileScale)
    utils.addModifierMirror(
        object=chiwenObj,
        mirrorObj=tileRootObj,
        use_axis=(True,False,False)
    )
    # 设置材质
    mat.setGlazeStyle(chiwenObj,resetUV=False)
    return

# 营造盝顶的围脊
def __buildSurroundRidge(buildingObj:bpy.types.Object,
                    rafter_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale
   
    # 围脊相交点，以金桁交点为参考
    # todo: 后续允许设置收分距离
    ridgeCross = rafter_pos[1]
    # 偏移计算：
    offset = Vector((
            # X、Y偏移：半柱径
            bData.piller_diameter/2,
            bData.piller_diameter/2,
            # Z偏移：槫子上皮+椽径+望板高+灰泥层高
            (con.HENG_COMMON_D/2*dk     # 槫子上皮
                + con.YUANCHUAN_D*dk    # 椽架厚度
                + con.WANGBAN_H*dk      # 望板厚度
                + con.ROOFMUD_H*dk      # 灰泥厚度
                - 1.2*dk                # 手工微调
            )
        ))
    ridgeCross += offset
    
    #------------------------
    # 1、横向围脊
    roofRidgeObj = utils.copyObject(
        sourceObj=aData.ridgeBack_source,
        name="围脊",
        location=(0,
                  ridgeCross.y,
                  ridgeCross.z),
        parentObj=tileRootObj,
        singleUser=True)
    # 根据斗口调整尺度
    utils.resizeObj(roofRidgeObj,tileScale)
    # 与瓦垄宽度匹配
    roofRidgeObj.dimensions.x = bData.tile_width_real
    utils.applyTransform(roofRidgeObj,use_scale=True)
    # 脊筒坐中
    roofRidgeObj.location.x = - roofRidgeObj.dimensions.x/2
    # 横向平铺
    zhengji_length = ridgeCross.x
    modArray:bpy.types.ArrayModifier = \
        roofRidgeObj.modifiers.new('横向平铺','ARRAY')
    modArray.use_relative_offset = True
    modArray.relative_offset_displace = (1,0,0)
    modArray.fit_type = 'FIT_LENGTH' 
    modArray.fit_length = zhengji_length
    # 镜像
    utils.addModifierMirror(
        object=roofRidgeObj,
        mirrorObj=tileRootObj,
        use_axis=(True,True,False),
        use_bisect=(True,True,False),
        use_merge=True,
    )
    # 250113 设置材质
    mat.setGlazeStyle(roofRidgeObj)

    #------------------------
    # 2、纵向围脊
    roofRidgeObj = utils.copyObject(
        sourceObj=aData.ridgeBack_source,
        name="围脊",
        location=(ridgeCross.x,
                  0,
                  ridgeCross.z),
        rotation=(0,0,math.radians(90)),
        parentObj=tileRootObj,
        singleUser=True)
    # 根据斗口调整尺度
    utils.resizeObj(roofRidgeObj,tileScale)
    # 与瓦垄宽度匹配
    roofRidgeObj.dimensions.x = bData.tile_width_real
    utils.applyTransform(roofRidgeObj,use_scale=True)
    # 脊筒坐中
    roofRidgeObj.location.y = - roofRidgeObj.dimensions.x/2
    # 横向平铺
    zhengji_length = ridgeCross.y
    modArray:bpy.types.ArrayModifier = \
        roofRidgeObj.modifiers.new('横向平铺','ARRAY')
    modArray.use_relative_offset = True
    modArray.relative_offset_displace = (1,0,0)
    modArray.fit_type = 'FIT_LENGTH' 
    modArray.fit_length = zhengji_length
    # 镜像
    utils.addModifierMirror(
        object=roofRidgeObj,
        mirrorObj=tileRootObj,
        use_axis=(True,True,False),
        use_bisect=(True,True,False),
        use_merge=True,
    )
    # 250113 设置材质
    mat.setGlazeStyle(roofRidgeObj)

    #------------------------
    # 3、摆放螭吻
    # 45度镜像
    diagnalObj = utils.addEmpty(
        name = '45度镜像',
        parent = tileRootObj,
        location=ridgeCross
    )
    diagnalObj.rotation_euler.z = math.radians(45)   
    # 螭吻对象
    chiwenObj = utils.copyObject(
        sourceObj=aData.chiwen_source,
        name='合角吻',
        location=ridgeCross,
        rotation=(0,0,math.radians(180)),
        parentObj=tileRootObj,
        singleUser=True)
    # 根据斗口调整尺度
    utils.resizeObj(chiwenObj,tileScale *0.75)
    # 镜像
    utils.addModifierMirror(
        object=chiwenObj,
        mirrorObj=diagnalObj,
        use_axis=(False,True,False),
        use_bisect=(False,True,False),
        use_merge=True,
    )
    # 镜像
    utils.addModifierMirror(
        object=chiwenObj,
        mirrorObj=tileRootObj,
        use_axis=(True,True,False)
    )
    # 设置材质
    mat.setGlazeStyle(chiwenObj,resetUV=False)

    return

# 查找给定X坐标附近的瓦垄X坐标
# 250227 修正，强制取X内侧（左侧）的瓦垄，以免意外取到右侧的瓦垄
def __getTileCoord(buildingObj:bpy.types.Object,
                   tileCoord):
    # 载入瓦面网格对象
    tileGrid = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_GRID
    )
    # 载入bmesh对象
    bm = bmesh.new()
    bm.from_mesh(tileGrid.data)
    
    # 临时做距离逼近的变量
    compare = 9999
    # 最终找到的瓦垄X坐标
    newTileCoord = None
    # 在瓦面网格上逐点比较
    for vert in bm.verts:
        # 当前点到瓦垄的距离n
        distance = tileCoord - vert.co.x
        if distance < 0: 
            # 仅找输入点左侧的瓦垄，如果为负数，说明已经到了右侧，退出循环
            break

        # 备份相对较小的值到m，便于下次比较
        if distance < compare:
            compare = distance
            newTileCoord = vert.co.x

    bm.free()

    return newTileCoord

# 绘制前后檐垂脊曲线
# 适用于歇山、悬山、硬山（不涉及庑殿）
# 自动判断歇山，只做到正心桁
# 自动判断悬山/硬山，做到檐口，且端头盘子八字转角
def __drawFrontRidgeCurve(buildingObj:bpy.types.Object,
                    purlin_pos):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    pd = bData.piller_diameter
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    ridgeCurveVerts = []

    # 根据庑殿、歇山、悬山、硬山的不同，计算正脊长度
    ridge_x = __getTopRidgeLength(buildingObj,purlin_pos)

    # 硬山和悬山添加垂脊在檐口的八字撇角
    if bData.roof_style in (
            con.ROOF_YINGSHAN,
            con.ROOF_YINGSHAN_JUANPENG,
            con.ROOF_XUANSHAN,
            con.ROOF_XUANSHAN_JUANPENG):
        # 大连檐中心
        dlyObj:bpy.types.Object = utils.getAcaChild(
            buildingObj,con.ACA_TYPE_RAFTER_DLY_FB)
        curve_p1 = Vector(dlyObj.location)
        # 位移到大连檐外沿，瓦当滴水向外延伸
        offset = Vector((ridge_x,con.DALIANYAN_H*dk/2,
            -con.DALIANYAN_Y*dk/2-con.EAVETILE_EX*dk))
        offset.rotate(dlyObj.rotation_euler)
        curve_p1 += offset

        # 计算一层瓦的投影长度(顺檐椽角度)
        offset = Vector((bData.tile_length,0,0))
        yanRafterObj:bpy.types.Object = utils.getAcaChild(
                buildingObj,con.ACA_TYPE_RAFTER_FB)
        offset.rotate(yanRafterObj.rotation_euler)
        # 向外歪一瓦层，做端头盘子的八字转角
        aside = offset.y
        curve_p1_aside = curve_p1 + Vector((aside,0,0))
        ridgeCurveVerts.append(curve_p1_aside)
        # P2：端头盘子定位点
        curve_p2 = curve_p1 - offset
        ridgeCurveVerts.append(curve_p2)
        # 重复添加转折点，形成一个“硬转折”，不做弧度
        ridgeCurveVerts.append(curve_p2)

    # Pn: 从举架定位点做偏移（歇山、硬山、悬山相同）
    # 从桁檩中点向上位移:半桁径+椽径+望板高+灰泥层高
    offset =  (con.HENG_COMMON_D*dk/2 
                + con.YUANCHUAN_D*dk 
                + con.WANGBAN_H*dk
                + con.ROOFMUD_H*dk)
    # 从桁檩中心，按法线方向提升
    tile_pos = utils.push_purlinPos(purlin_pos,-offset)
    for n in range(len(tile_pos)):
        point:Vector = tile_pos[n]
        point.x = ridge_x
        ridgeCurveVerts.append(point)

    # 卷棚顶的曲线调整,最后一点囊相调整，再加两个平滑点
    if bData.roof_style in (
            con.ROOF_XUANSHAN_JUANPENG,
            con.ROOF_YINGSHAN_JUANPENG,
            con.ROOF_XIESHAN_JUANPENG,):
        ridgeCurveVerts[-1] += Vector((0,
                con.JUANPENG_PUMP*dk,   # 卷棚的囊调整
                0))
        JuanSpan = ridgeCurveVerts[-1].y
        # Y=0时，抬升1椽径，见马炳坚p20
        p1 = ridgeCurveVerts[-1] + Vector((
                0,
                -JuanSpan/2,
                con.JUANPENG_POP*dk))
        ridgeCurveVerts.append(p1)
        # 延伸以便更加平滑
        p2 = p1 + Vector((0,-JuanSpan/2,0))
        ridgeCurveVerts.append(p2)
    else:
        # 延长曲线终点，与正脊相交
        # 计算尾段斜率
        pNeg1 = ridgeCurveVerts[-1]
        pNeg2 = ridgeCurveVerts[-2]
        r = abs((pNeg1.y - pNeg2.y)/(pNeg1.z - pNeg2.z))
        # Y方向延伸2个垂脊筒的长度，多余的会在镜像时裁剪掉
        ridgeFrontObj:bpy.types.Object = aData.ridgeFront_source
        offset_y = ridgeFrontObj.dimensions.x * 2
        pNeg1.y -= offset_y
        # Z方向按尾端斜率延伸
        pNeg1.z += offset_y / r
    
    # 创建曲线
    ridgeCurve = utils.addCurveByPoints(
            CurvePoints=ridgeCurveVerts,
            name="垂脊线",
            root_obj=tileRootObj,
            order_u=4, # 取4级平滑，让坡面曲线更加流畅
            )
    
    # 矫正曲线倾斜
    # todo：添加了八字拐弯后，屋脊不再垂直，只能手工矫正，暂时没有啥好办法
    if bData.roof_style in (
            con.ROOF_YINGSHAN,
            con.ROOF_YINGSHAN_JUANPENG,
            con.ROOF_XUANSHAN,
            con.ROOF_XUANSHAN_JUANPENG):
        curve_points = ridgeCurve.data.splines[0].points
        for point in curve_points:
            # 人工调整，这个角度只是估算值，不知道怎么计算
            point.tilt = math.radians(16)

    # 原点设置在檐口
    utils.setOrigin(ridgeCurve,ridgeCurveVerts[0])
    # 默认隐藏
    utils.hideObj(ridgeCurve)
    return ridgeCurve

# 绘制排山勾滴曲线(专为排山勾滴的布局使用)
# 区别在于不做延长，准确的在正脊位置结束
# 便于计算居中的排山勾头
def __drawSideRidgeCurve(buildingObj:bpy.types.Object,
                    purlin_pos):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = bData.piller_diameter
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    ridgeCurveVerts = []
    # 垂脊横坐标，向内半垄
    ridge_x = purlin_pos[-1].x - bData.tile_width_real/2
    # 硬山建筑，向外移动一个山墙
    if bData.roof_style in (
            con.ROOF_YINGSHAN,
            con.ROOF_YINGSHAN_JUANPENG
            ):
        ridge_x += con.SHANQIANG_WIDTH * dk - con.BEAM_DEPTH * pd/2

    # 硬山、悬山的垂脊从檐口做起
    if bData.roof_style in (
            con.ROOF_YINGSHAN,
            con.ROOF_YINGSHAN_JUANPENG,
            con.ROOF_XUANSHAN,
            con.ROOF_XUANSHAN_JUANPENG):
        # 第1点：从正身飞椽的中心当开始，上移半飞椽+大连檐
        # 大连檐中心
        dlyObj:bpy.types.Object = utils.getAcaChild(
            buildingObj,con.ACA_TYPE_RAFTER_DLY_FB)
        curve_p1 = Vector(dlyObj.location)
        # 位移到大连檐外沿，瓦当滴水向外延伸
        offset = Vector((ridge_x,con.DALIANYAN_H*dk/2,
            -con.DALIANYAN_Y*dk/2-con.EAVETILE_EX*dk))
        offset.rotate(dlyObj.rotation_euler)
        curve_p1 += offset
        ridgeCurveVerts.append(curve_p1)

    # 综合考虑桁架上铺椽、望、灰泥后的效果，主要保证整体线条的流畅
    # 从桁檩中点向上位移:半桁径+椽径+望板高+灰泥层高
    offset =  (con.HENG_COMMON_D*dk/2 
                + con.YUANCHUAN_D*dk 
                + con.WANGBAN_H*dk
                + con.ROOFMUD_H*dk)
    # 从桁檩中心，按法线方向提升
    tile_pos = utils.push_purlinPos(purlin_pos, -offset)
    # 从举架定位点做偏移
    for n in range(len(tile_pos)):
        point:Vector = tile_pos[n]
        point.x = ridge_x        
        ridgeCurveVerts.append(point)
    
    # 卷棚顶的曲线调整,最后一点囊相调整，再加两个平滑点
    if bData.roof_style in (
            con.ROOF_XUANSHAN_JUANPENG,
            con.ROOF_YINGSHAN_JUANPENG,
            con.ROOF_XIESHAN_JUANPENG,):
        ridgeCurveVerts[-1] += Vector((0,
                con.JUANPENG_PUMP*dk,   # 卷棚的囊调整
                0))
        JuanSpan = ridgeCurveVerts[-1].y
        # Y=0时，抬升1椽径，见马炳坚p20
        p1 = ridgeCurveVerts[-1] + Vector((
                0,
                -JuanSpan/2,
                con.JUANPENG_POP*dk))
        ridgeCurveVerts.append(p1)
        # 延伸以便更加平滑
        p2 = p1 + Vector((0,-JuanSpan/2,0))
        ridgeCurveVerts.append(p2)
    
    # 创建瓦垄曲线
    ridgeCurve = utils.addCurveByPoints(
            CurvePoints=ridgeCurveVerts,
            name="排山勾滴线",
            root_obj=tileRootObj,
            order_u=4, # 取4级平滑，让坡面曲线更加流畅
            )
    utils.setOrigin(ridgeCurve,ridgeCurveVerts[0])
    utils.hideObj(ridgeCurve)
    return ridgeCurve

# 沿曲线排布脊筒
def __arrayRidgeByCurve(buildingObj: bpy.types.Object,
                    sourceObj:bpy.types.Object,
                    ridgeCurve:bpy.types.Curve,
                    ridgeName='垂脊',
                    arrayCount=0,
                    userMerge=True,
                 ):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale
    
    # 复制垂脊对象
    frontRidgeObj = utils.copyObject(
        sourceObj=sourceObj,
        name=ridgeName,
        location=ridgeCurve.location,
        parentObj=tileRootObj,
        singleUser=True)
    # 根据斗口调整尺度
    utils.resizeObj(frontRidgeObj,tileScale)
    # 应用缩放，以便平铺到曲线长度
    utils.applyTransform(
        frontRidgeObj,use_scale=True)
    
    # 沿垂脊曲线平铺
    modArray:bpy.types.ArrayModifier = \
        frontRidgeObj.modifiers.new('曲线平铺','ARRAY')
    if arrayCount != 0:
        modArray.fit_type = 'FIXED_COUNT'
        modArray.count = arrayCount
    else:
        modArray.fit_type = 'FIT_CURVE'
        modArray.curve = ridgeCurve
    
    # 250718 脊筒间略作间隙，以确保在裁剪时保持水密
    modArray.relative_offset_displace = (1.001,0,0)
    
    # 沿垂脊曲线变形
    modCurve: bpy.types.CurveModifier = \
        frontRidgeObj.modifiers.new('曲线变形','CURVE')
    modCurve.object = ridgeCurve

    # 四面镜像
    utils.addModifierMirror(
        object=frontRidgeObj,
        mirrorObj=tileRootObj,
        use_axis=(True,True,False),
        use_bisect=(True,True,False),
        use_merge=userMerge,
    )

    return frontRidgeObj

# 营造排山勾滴
def __arraySideTile(buildingObj: bpy.types.Object,
                    sourceObj:bpy.types.Object,
                    ridgeCurve:bpy.types.Curve,
                    arraySpan:float,
                    arrayCount=0,
                    tileName='排山勾滴',
                 ):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale
    
    # 复制勾滴对象
    tileObj = utils.copyObject(
        sourceObj=sourceObj,
        name=tileName,
        location=ridgeCurve.location,
        parentObj=tileRootObj,
        singleUser=True)
    # 根据斗口调整尺度
    tileObj = utils.resizeObj(tileObj,tileScale)
    utils.applyTransform(tileObj,use_scale=True)
    # 旋转
    tileObj.rotation_euler.x = math.radians(90)
    
    # 沿垂脊曲线平铺
    modArray:bpy.types.ArrayModifier = \
        tileObj.modifiers.new('曲线平铺','ARRAY')
    if arrayCount != 0:
        modArray.fit_type = 'FIXED_COUNT'
        modArray.count = arrayCount
    else:
        modArray.fit_type = 'FIT_CURVE'
        modArray.curve = ridgeCurve
    modArray.use_relative_offset = False
    modArray.use_constant_offset = True
    modArray.constant_offset_displace = (-arraySpan,0,0)

    # 沿垂脊曲线变形
    modCurve: bpy.types.CurveModifier = \
        tileObj.modifiers.new('曲线变形','CURVE')
    modCurve.object = ridgeCurve
    modCurve.deform_axis = 'NEG_X'
    
    # 为了实现第一片排山滴水的裁剪，推迟到了排山滴水摆放位置完成后做镜像
    # # 四面镜像
    # modMirror: bpy.types.MirrorModifier = \
    #     tileObj.modifiers.new('镜像','MIRROR')
    # modMirror.mirror_object = tileRootObj
    # modMirror.use_axis = (True,True,False)
    # modMirror.use_bisect_axis = (False,True,False)

    return tileObj

# 摆放套兽
def __buildTaoshou(buildingObj: bpy.types.Object):
    # 载入数据
    bData:acaData  = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale

    # 获取子角梁
    ccbObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_CORNER_BEAM_CHILD)
    # 套兽定位与子角梁头下皮平
    offset = Vector((0,0,con.JIAOLIANG_H*dk))
    offset.rotate(ccbObj.rotation_euler)
    loc = bData.roof_qiao_point - offset

    taoshouObj = utils.copyObject(
        sourceObj=aData.taoshou_source,
        name='套兽',
        parentObj=tileRootObj,
        location=loc,
        singleUser=True
    )
    # 根据斗口调整尺度
    utils.resizeObj(taoshouObj,tileScale)
    # 与子角梁头做相同旋转
    taoshouObj.rotation_euler = ccbObj.rotation_euler

    # 做四面对称
    utils.addModifierMirror(
        object=taoshouObj,
        mirrorObj=tileRootObj,
        use_axis=(True,True,False)
    )
    # 设置材质
    mat.setGlazeStyle(taoshouObj,resetUV=False)
    return

# 摆放跑兽
def __buildPaoshou(buildingObj: bpy.types.Object,
                   ridgeCurve:bpy.types.Object,
                   count):
    # 载入数据
    bData:acaData  = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale
    
    # 载入10个跑兽
    paoshouObjs = []
    paoshouObjs.append(aData.paoshou_0_source)
    paoshouObjs.append(aData.paoshou_1_source)
    paoshouObjs.append(aData.paoshou_2_source)
    paoshouObjs.append(aData.paoshou_3_source)
    paoshouObjs.append(aData.paoshou_4_source)
    paoshouObjs.append(aData.paoshou_5_source)
    paoshouObjs.append(aData.paoshou_6_source)
    paoshouObjs.append(aData.paoshou_7_source)
    paoshouObjs.append(aData.paoshou_8_source)
    paoshouObjs.append(aData.paoshou_9_source)
    paoshouObjs.append(aData.paoshou_10_source)

    # 以一个脊筒长度为单位距离
    ridgeObj:bpy.types.Object = aData.ridgeFront_source
    ridgeLength = ridgeObj.dimensions.x * tileScale
    ridgeHeight = ridgeObj.dimensions.z * tileScale
    # 端头盘子长度
    ridgeEndObj:bpy.types.Object = aData.ridgeEnd_source
    ridgeEnd_Length = ridgeEndObj.dimensions.x * tileScale

    for n in range(count):
        #跑兽沿垂脊方向间隔一个脊筒，且坐在脊筒中间
        pao_offset = ridgeEnd_Length + ridgeLength*(n-0.5)
        loc = ridgeCurve.location + Vector((
                pao_offset,
                0,ridgeHeight)) 
        shouObj = utils.copyObject(
            sourceObj=paoshouObjs[n],
            parentObj=tileRootObj,
            location=loc,
            singleUser=True
        )
        # 根据斗口调整尺度
        utils.resizeObj(shouObj,tileScale)
        # 通过曲线变形，获得仰角
        modCurve:bpy.types.CurveModifier = \
             shouObj.modifiers.new('curve','CURVE')
        modCurve.object = ridgeCurve
        # 四向对称
        utils.addModifierMirror(
            object=shouObj,
            mirrorObj=tileRootObj,
            use_axis=(True,True,False),
        )
        utils.applyAllModifer(shouObj)
        utils.applyTransform(shouObj,use_location=True)

        # 250113 跑兽材质
        mat.setGlazeStyle(shouObj,resetUV=False)
    return

# 营造前后檐垂脊
# 适用于歇山、悬山、硬山
# 庑殿不涉及（不进入本函数）
def __buildFrontRidge(buildingObj: bpy.types.Object,
                 rafter_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    eaveTile:bpy.types.Object = aData.eaveTile_source
    eaveTileWidth = eaveTile.dimensions.x
    eaveTileLength = eaveTile.dimensions.y
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale
    
    # 绘制垂脊曲线，其中自动判断了垂脊起点：
    # 歇山仅做到正心桁位置
    # 硬山悬山做到檐口位置
    frontRidgeCurve = __drawFrontRidgeCurve(
        buildingObj,rafter_pos)
    # 垂脊兽后
    frontRidgeAfterObj = None
    # 垂脊兽前
    frontRidgeBeforeObj = None
    # 端头盘子
    ridgeEndObj=None
    # 垂兽
    chuishouObj=None
    
    # 构造垂脊兽后，歇山、悬山、硬山共用
    # 如果不做跑兽，也不做垂兽和垂脊兽后
    if bData.paoshou_count > 0 :
        frontRidgeAfterObj = __arrayRidgeByCurve(buildingObj,
                        sourceObj=aData.ridgeBack_source,
                        ridgeCurve=frontRidgeCurve,
                        ridgeName='垂脊兽后')
        # 获取脊筒长度
        ridgeObj:bpy.types.Object = aData.ridgeBack_source
        ridgeLength = ridgeObj.dimensions.x * tileScale
        # 摆放垂兽
        chuishouObj = utils.copyObject(
            sourceObj=aData.chuishou_source,
            name='垂兽',
            parentObj=tileRootObj,
            location=frontRidgeCurve.location,
            singleUser=True)
        
        # 根据斗口调整尺度
        utils.resizeObj(chuishouObj,tileScale)
        # 通过曲线变形，获得仰角
        modCurve:bpy.types.CurveModifier = \
                chuishouObj.modifiers.new('curve','CURVE')
        modCurve.object = frontRidgeCurve
        # 四向对称
        utils.addModifierMirror(
            object=chuishouObj,
            mirrorObj=tileRootObj,
            use_axis=(True,True,False)
        )
        if bData.roof_style in (con.ROOF_YINGSHAN,
                                con.ROOF_YINGSHAN_JUANPENG,
                                con.ROOF_XUANSHAN,
                                con.ROOF_XUANSHAN_JUANPENG,) :
            # 硬山悬山，垂脊兽后退后一个脊筒，摆放垂兽，与跑兽间隔开
            frontRidgeAfterObj.location.x += ridgeLength
        else:
            # 歇山垂兽做头，后尾对齐正心桁中线，向檐口位移一脊筒
            chuishouObj.location.x -= ridgeLength

    # 硬山、悬山：做垂脊兽前、端头盘子、跑兽
    # 歇山不做脊兽时，做垂脊兽前和端头盘子
    if (
            bData.roof_style in (con.ROOF_YINGSHAN,
                                con.ROOF_YINGSHAN_JUANPENG,
                                con.ROOF_XUANSHAN,
                                con.ROOF_XUANSHAN_JUANPENG,) 
            or 
            (bData.roof_style in (con.ROOF_XIESHAN,
                                con.ROOF_XIESHAN_JUANPENG)
                and bData.paoshou_count == 0) 
        ):
        # 构造端头盘子
        ridgeEndObj = utils.copyObject(
            sourceObj=aData.ridgeEnd_source,
            name='端头盘子',
            location=frontRidgeCurve.location,
            parentObj=tileRootObj,
            singleUser=True)
        # 根据斗口调整尺度
        utils.resizeObj(ridgeEndObj,tileScale)
        # 应用缩放，以便平铺到曲线长度
        utils.applyTransform(
            ridgeEndObj,use_scale=True)
        ridgeEnd_Length = ridgeEndObj.dimensions.x
        # 沿垂脊曲线变形，适配曲线仰角
        modCurve: bpy.types.CurveModifier = \
            ridgeEndObj.modifiers.new('曲线变形','CURVE')
        modCurve.object = frontRidgeCurve
        # 四面镜像
        utils.addModifierMirror(
            object=ridgeEndObj,
            mirrorObj=tileRootObj,
            use_axis=(True,True,False),
        )

        # 构造垂脊兽前的脊筒，仅根据需要的跑兽数量排布
        frontRidgeBeforeObj = __arrayRidgeByCurve(buildingObj,
                        sourceObj=aData.ridgeFront_source,
                        ridgeCurve=frontRidgeCurve,
                        ridgeName='垂脊兽前',
                        arrayCount= bData.paoshou_count)        
        # 垂脊兽前后退一个端头盘子长度
        frontRidgeBeforeObj.location.x += ridgeEnd_Length

        if (bData.paoshou_count > 0 
            and bData.roof_style not in (con.ROOF_XIESHAN,
                                         con.ROOF_XIESHAN_JUANPENG)
            ):
            # 放置跑兽
            __buildPaoshou(
                buildingObj=buildingObj,
                ridgeCurve=frontRidgeCurve,
                count=bData.paoshou_count
            )

            # 给垂脊兽后留出跑兽的空间
            ridgeUnit: bpy.types.Object= aData.ridgeFront_source
            ridgeUnit_Length = ridgeUnit.dimensions.x * tileScale
            paoLength = (ridgeEnd_Length 
                + ridgeUnit_Length * bData.paoshou_count)
            frontRidgeAfterObj.location.x += paoLength
            chuishouObj.location.x += paoLength
    
    # 250110 设置材质，务必放在最后，以免modifier过早被应用，导致错误
    if frontRidgeAfterObj != None:
        mat.setGlazeStyle(frontRidgeAfterObj)
        utils.shaderSmooth(frontRidgeAfterObj)
    if frontRidgeBeforeObj != None:
        mat.setGlazeStyle(frontRidgeBeforeObj)
        utils.shaderSmooth(frontRidgeBeforeObj)
    if ridgeEndObj != None:
        mat.setGlazeStyle(ridgeEndObj)
    if chuishouObj != None:
        mat.setGlazeStyle(chuishouObj)
    
    # 消除因为位移在UI上难看的关系线
    utils.applyTransform(frontRidgeAfterObj,use_location=True)
    utils.applyTransform(frontRidgeBeforeObj,use_location=True)
    utils.applyTransform2(chuishouObj,use_location=True)

    return {'FINISHED'}

# 排布排山勾滴
def __buildSideTile(buildingObj: bpy.types.Object,
                 rafter_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    aData:tmpData = bpy.context.scene.ACA_temp
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale
    
    # 构造排山滴水
    sideRidgeCurve = __drawSideRidgeCurve(
        buildingObj,rafter_pos)
    # 计算排布间隔，保证筒瓦坐中
    curveLength = sideRidgeCurve.data.splines[0].calc_length()
    # 实际勾头从曲线开头处让开一层瓦距
    arrayLength = (curveLength 
                   - bData.tile_length
                   + bData.tile_width
                   + con.TILE_CORNER_SPLIT*dk
                   )
    arrayCount = int(arrayLength/bData.tile_width)
    arraySpan = arrayLength / arrayCount
    dripTileObj = __arraySideTile(buildingObj,
                    sourceObj=aData.dripTile_source,
                    ridgeCurve=sideRidgeCurve,
                    arraySpan=arraySpan,
                    tileName='排山滴水',)
    
    eaveTileObj = __arraySideTile(buildingObj,
                    sourceObj=aData.eaveTile_source,
                    ridgeCurve=sideRidgeCurve,
                    arraySpan=arraySpan,
                    arrayCount = arrayCount-1,  # 少做一个勾头，手工放置坐中勾头
                    tileName='排山勾头')
    
    # 放置勾头坐中
    eaveTileCenterObj = utils.copyObject(
        sourceObj=aData.eaveTile_source,
        name='排山勾头坐中',
        location=(
                sideRidgeCurve.location.x,
                0,
                (
                sideRidgeCurve.location.z 
                + sideRidgeCurve.dimensions.z)
            ),
        parentObj=tileRootObj,
        singleUser=True)
    # 根据斗口调整尺度
    utils.resizeObj(eaveTileCenterObj,tileScale)
    eaveTileCenterObj.rotation_euler.z = math.radians(90)
    utils.addModifierMirror(
        object=eaveTileCenterObj,
        mirrorObj=tileRootObj,
        use_axis=(True,False,False)
    )

    # 排山勾头位移
    # 在curve modifier的影响下，X位移实际在Y方向，Z位移实际在X方向
    eaveTileObj.location += Vector((
        # X方向（实际为Y方向），位移一瓦宽，四角退让，适当手工调整
        - arraySpan - con.TILE_CORNER_SPLIT*dk, 
        0, 0))
    # 排山滴水位移
    dripTileObj.location += Vector((
        # X方向（实际为Y方向），位移半瓦宽，四角退让，适当手工调整
        - arraySpan/2 - con.TILE_CORNER_SPLIT*dk,
        0, 0))
    
    if bData.roof_style in (
            con.ROOF_XUANSHAN,
            con.ROOF_YINGSHAN,
            con.ROOF_YINGSHAN_JUANPENG,
            con.ROOF_XUANSHAN_JUANPENG):
        # 第一片滴水裁剪
        utils.addBisect(
            object=dripTileObj,
            pStart=tileRootObj.matrix_world @ Vector((0,0,0)),
            pEnd=tileRootObj.matrix_world @ Vector((1,1,0)),
            pCut=tileRootObj.matrix_world @ sideRidgeCurve.location+Vector((0,-bData.tile_length,0)),
            clear_outer=True
        )

    # 镜像
    '''本来镜像放在了__arraySideTile函数中，但为了做滴水的裁剪，不得不在裁剪后镜像
    也考虑过把裁剪放到__arraySideTile函数内，但裁剪一方面必须在curve后，
    另一方面，curve后的裁剪导致实例化，无法再做上面的沿曲线位移，
    无奈之下，只能放在这里事后镜像
    '''
    utils.addModifierMirror(
        object=dripTileObj,
        mirrorObj=tileRootObj,
        use_axis=(True,True,False),
        use_bisect=(False,True,False),
        use_merge=True, # 合并裁剪点，以实现水密
    )
    utils.addModifierMirror(
        object=eaveTileObj,
        mirrorObj=tileRootObj,
        use_axis=(True,True,False),
        use_bisect=(False,True,False)
    )

    # 歇山屋顶的排山勾滴裁剪
    # 与山花板类似，裁剪到博脊上皮
    # 即，从正心桁上推瓦面+收山加斜+博脊高
    ridgeObj:bpy.types.Object = aData.ridgeFront_source
    ridgeHeight = ridgeObj.dimensions.z * tileScale
    # 载入举折系数
    lift_ratio = buildBeam.getLiftRatio(buildingObj)
    # 收山举高，按第一层举架系数加斜
    shouLift = bData.shoushan*lift_ratio[0]
    cutPoint = rafter_pos[0] \
        + Vector((0,0,
            + shouLift                 # 收山举高
            + con.HENG_COMMON_D*dk/2   # 半桁径
            + con.YUANCHUAN_D*dk       # 椽径
            + con.WANGBAN_H*dk         # 望板
            + con.ROOFMUD_H*dk         # 灰泥
            + ridgeHeight))         # 取到博脊上皮
    if bData.roof_style in (con.ROOF_XIESHAN,
                            con.ROOF_XIESHAN_JUANPENG):
        utils.addBisect(
            object=eaveTileObj,
            pCut=tileRootObj.matrix_world @ cutPoint,
            clear_outer=True,
            direction='V'
        )
        utils.addBisect(
            object=dripTileObj,
            pCut=tileRootObj.matrix_world @ cutPoint,
            clear_outer=True,
            direction='V'
        )

    # 平滑处理
    utils.shaderSmooth(eaveTileObj)
    utils.shaderSmooth(dripTileObj)

    # 250113 设置材质
    mat.setGlazeStyle(eaveTileCenterObj)
    mat.setGlazeStyle(eaveTileObj)
    mat.setGlazeStyle(dripTileObj)

    return

# 营造戗脊（庑殿垂脊）曲线
def __buildCornerRidgeCurve(buildingObj:bpy.types.Object,
                    purlin_pos,name='戗脊线'):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    ridgeCurveVerts = []
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale

    # 250328 改为通过檐口线进行定义
    # 获取檐口线（前后檐）
    eaveCurve = utils.getAcaChild(buildingObj,
                    con.ACA_TYPE_TILE_EAVE_CURVE_FB)
    eaveCurveData:bpy.types.Curve = eaveCurve.data
    bpoints = eaveCurveData.splines[0].bezier_points
    # 获取檐口曲线的终点
    end_point = eaveCurve.matrix_local @ bpoints[2].co
    # 子角梁头
    ccbHead = bData.roof_qiao_point.copy()
    # 90度转头向子角梁方向
    tangent2 = Vector((1,-1,0))
    normal45 = Vector((1,-1,0))   
    # 计算从终点沿切线方向到子角梁中心的距离
    distance = (ccbHead - end_point).dot(normal45) / tangent2.dot(normal45)
    # 将p0延长到交点
    p0 = end_point + tangent2 * distance
    # 将p0向下移动一个筒瓦高度
    aData:tmpData = bpy.context.scene.ACA_temp
    tileHeight = aData.circularTile_source.dimensions.z * tileScale
    offset = Vector((0,0,tileHeight))
    # 沿子角梁方向位移
    ccbObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_CORNER_BEAM_CHILD)
    offset.rotate(ccbObj.rotation_euler)
    # 最终的p0位置
    p0 -= offset
    ridgeCurveVerts.append(p0)

    # 庑殿垂脊做到顶部的正脊
    if bData.roof_style in (
            con.ROOF_WUDIAN,
            con.ROOF_LUDING):
        ridgeRange = range(len(purlin_pos))
    # 歇山戗脊仅做到金桁高度
    if bData.roof_style in (con.ROOF_XIESHAN,
                            con.ROOF_XIESHAN_JUANPENG,):
        ridgeRange = range(2)

    # 综合考虑桁架上铺椽、望、灰泥后的效果，主要保证整体线条的流畅
    # 半桁径+椽径+望板高+灰泥层高 + 筒瓦高
    aData:tmpData = bpy.context.scene.ACA_temp
    tileHeight = aData.circularTile_source.dimensions.z * tileScale
    offset = (con.HENG_COMMON_D*dk /2 
                    + con.YUANCHUAN_D*dk 
                    + con.WANGBAN_H*dk
                    + con.ROOFMUD_H*dk
                    #+ tileHeight
                    )
    # 从桁檩中心，按法线方向提升
    tile_pos = utils.push_purlinPos(purlin_pos, 
                        -offset, 'X')
    
    # 从举架定位点做偏移
    for n in ridgeRange:
        # point:Vector = Vector((
        #         tile_pos[n].y+ (bData.x_total-bData.y_total)/2,
        #         tile_pos[n].y,
        #         tile_pos[n].z))

        # 向上位移:半桁径+椽径+望板高+灰泥层高
        offset = (con.HENG_COMMON_D/2 + con.YUANCHUAN_D 
                    + con.WANGBAN_H + con.ROOFMUD_H)*dk + tileHeight
        point:Vector = purlin_pos[n]+Vector((0,0,offset))
        # 曲线矫正，随着起翘幅度的增大，下金桁位置的垂脊有与瓦面分离的风险
        # 所以在第一点上随着起翘，反向进行了压制
        # 没有明确的算法，我人为估计的一个值，不够准确，先凑合着用
        if n==0:
            point -= Vector((0,0,bData.qiqiao*con.YUANCHUAN_D*dk/3))
        ridgeCurveVerts.append(point)
    
    # 创建瓦垄曲线
    ridgeCurve = utils.addCurveByPoints(
            CurvePoints=ridgeCurveVerts,
            name=name,
            root_obj=tileRootObj,
            order_u=4, # 取4级平滑，让坡面曲线更加流畅
            )
    utils.setOrigin(ridgeCurve,ridgeCurveVerts[0])
    utils.hideObj(ridgeCurve)
    return ridgeCurve

# 营造四角的戗脊
# 适用于庑殿、歇山，不涉及硬山、悬山
def __buildCornerRidge(buildingObj:bpy.types.Object,
                    rafter_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale

    cornerRidgeBeforeObj = None
    cornerRidgeAfterObj = None
    ridgeEndObj = None
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    if bData.roof_style in (
            con.ROOF_WUDIAN,
            con.ROOF_LUDING):
        cornerRidgeName = '垂脊'
    if bData.roof_style in (con.ROOF_XIESHAN,
                            con.ROOF_XIESHAN_JUANPENG,):
        cornerRidgeName = '戗脊'
    
    # 绘制戗脊曲线
    cornerRidgeCurve = __buildCornerRidgeCurve(
        buildingObj,rafter_pos,cornerRidgeName+'线')
    
    # 垂脊兽前摆放端头盘子
    ridgeEndObj = utils.copyObject(
            sourceObj=aData.ridgeEnd_source,
            name='端头盘子',
            location=cornerRidgeCurve.location,
            parentObj=tileRootObj,
            singleUser=True)
    # 根据斗口调整尺度
    utils.resizeObj(ridgeEndObj,tileScale)
    # 应用缩放，以便平铺到曲线长度
    utils.applyTransform(
        ridgeEndObj,use_scale=True)
    ridgeEnd_Length = ridgeEndObj.dimensions.x
    # 沿垂脊曲线变形，适配曲线仰角
    modCurve: bpy.types.CurveModifier = \
        ridgeEndObj.modifiers.new('曲线变形','CURVE')
    modCurve.object = cornerRidgeCurve
    # 四面镜像
    utils.addModifierMirror(
        object=ridgeEndObj,
        mirrorObj=tileRootObj,
        use_axis=(True,True,False),
    )

    # 沿曲线排布脊筒
    # 构造垂脊兽前
    cornerRidgeBeforeObj = __arrayRidgeByCurve(buildingObj,
                    sourceObj=aData.ridgeFront_source,
                    ridgeCurve=cornerRidgeCurve,
                    ridgeName=cornerRidgeName+'兽前',
                    arrayCount= bData.paoshou_count)
    # 戗脊兽前与端头盘子相接
    cornerRidgeBeforeObj.location.x += \
        ridgeEnd_Length
    utils.applyAllModifer(cornerRidgeBeforeObj)
    utils.applyTransform(cornerRidgeBeforeObj,use_location=True)
    
    if bData.paoshou_count > 0:
        # 放置跑兽
        __buildPaoshou(
            buildingObj=buildingObj,
            ridgeCurve=cornerRidgeCurve,
            count=bData.paoshou_count
        )

        # 构造垂脊兽后
        cornerRidgeAfterObj = __arrayRidgeByCurve(buildingObj,
                        sourceObj=aData.ridgeBack_source,
                        ridgeCurve=cornerRidgeCurve,
                        ridgeName=cornerRidgeName+'兽后')
        # 留出跑兽的空间
        ridgeUnit: bpy.types.Object= aData.ridgeFront_source
        ridgeUnit_Length = ridgeUnit.dimensions.x * tileScale
        paoLength = (ridgeEnd_Length
            + ridgeUnit_Length * bData.paoshou_count)
        cornerRidgeAfterObj.location.x += paoLength +ridgeUnit_Length

        # 盝顶戗脊兽后的跑兽偏移处理
        # 不做裁剪，仅修改垂脊长度
        if bData.roof_style == con.ROOF_LUDING:
            modArray:bpy.types.ArrayModifier \
                  = cornerRidgeAfterObj.modifiers['曲线平铺']
            modArray.fit_type = 'FIT_LENGTH'
            curveLength = cornerRidgeCurve.data.splines[0].calc_length()
            ridegLength = curveLength - paoLength - ridgeUnit_Length
            modArray.fit_length = ridegLength
        utils.applyAllModifer(cornerRidgeAfterObj)
        utils.applyTransform(cornerRidgeAfterObj,use_location=True)

        # 摆放垂兽
        loc = cornerRidgeCurve.location + Vector((paoLength,0,0))
        chuishouObj = utils.copyObject(
            sourceObj=aData.chuishou_source,
            name='垂兽',
            parentObj=tileRootObj,
            location=loc,
            singleUser=True)
        # 根据斗口调整尺度
        utils.resizeObj(chuishouObj,tileScale)
        # 通过曲线变形，获得仰角
        modCurve:bpy.types.CurveModifier = \
                chuishouObj.modifiers.new('curve','CURVE')
        modCurve.object = cornerRidgeCurve
        # 四向对称
        utils.addModifierMirror(
            object=chuishouObj,
            mirrorObj=tileRootObj,
            use_axis=(True,True,False)
        )
        utils.applyAllModifer(chuishouObj)
        utils.applyTransform2(chuishouObj,use_location=True)

        # 设置垂兽材质
        mat.setGlazeStyle(chuishouObj)        

    # 歇山戗脊，沿垂脊裁剪
    if bData.roof_style in (con.ROOF_XIESHAN,
                            con.ROOF_XIESHAN_JUANPENG):
        pcut = tileRootObj.matrix_world @ rafter_pos[-1]
        # 偏移半垄，与垂脊相交
        pcut += Vector((-bData.tile_width_real/2,0,0))
        
        # 裁剪戗脊-兽前
        utils.addBisect(
            object=cornerRidgeBeforeObj,
            pStart=tileRootObj.matrix_world @ Vector((0,-1,0)),
            pEnd=tileRootObj.matrix_world @ Vector((0,1,0)),
            pCut=pcut,
            clear_outer=True,
            direction='Z'
        )
        # 重建戗脊-兽前的左右镜像
        utils.addModifierMirror(
            object=cornerRidgeBeforeObj,
            mirrorObj=tileRootObj,
            use_axis=(True,False,False)
        )

        # 裁剪戗脊-兽后
        if bData.paoshou_count > 0:
            utils.addBisect(
                object=cornerRidgeAfterObj,
                pStart=tileRootObj.matrix_world @ Vector((0,-1,0)),
                pEnd=tileRootObj.matrix_world @ Vector((0,1,0)),
                pCut=pcut,
                clear_outer=True,
                direction='Z'
            )
            # 重建戗脊-兽后的左右镜像
            utils.addModifierMirror(
                object=cornerRidgeAfterObj,
                mirrorObj=tileRootObj,
                use_axis=(True,False,False)
            )   
    
    # 250110 设置材质
    if cornerRidgeBeforeObj != None:
        mat.setGlazeStyle(cornerRidgeBeforeObj)
        utils.shaderSmooth(cornerRidgeBeforeObj)
    if cornerRidgeAfterObj != None:
        mat.setGlazeStyle(cornerRidgeAfterObj)
        utils.shaderSmooth(cornerRidgeAfterObj)
    if ridgeEndObj != None:
        mat.setGlazeStyle(ridgeEndObj)

    # 放置套兽
    __buildTaoshou(buildingObj)

    return

# 营造歇山的博脊
def __buildSideRidge(buildingObj:bpy.types.Object,
                    rafter_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale

    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    ridgeObj:bpy.types.Object = aData.ridgeFront_source
    ridgeLength = ridgeObj.dimensions.x * tileScale
    
    # 博脊定位
    # X坐标：从山花中线，向外山花板厚度
    shanPoint = rafter_pos[-1]
    x = shanPoint.x + con.BOFENG_WIDTH*dk

    # Y坐标：从正心桁加上推山进行计算    
    zhengxinPoint = rafter_pos[0]
    # 从金桁交点瓦面的计算
    y = (zhengxinPoint.y 
         - bData.shoushan           # 收山影响
         - ridgeLength              # 留出一个挂尖长度
    )
    # 取整，以便后续与挂尖收尾进行衔接
    y = round(y/ridgeLength)* ridgeLength
    
    # Z坐标：从正心桁上推到瓦面，再添加推山影响
    # 载入举折系数
    lift_ratio = buildBeam.getLiftRatio(buildingObj)
    # 收山举高，按第一层举架系数加斜
    shouLift = bData.shoushan*lift_ratio[0]
    z = (zhengxinPoint.z 
         + shouLift                 # 收山举高
         + con.HENG_COMMON_D*dk/2   # 半桁径
         + con.YUANCHUAN_D*dk       # 椽径
         + con.WANGBAN_H*dk         # 望板
         + con.ROOFMUD_H*dk         # 灰泥
    )
    
    # 绘制博脊曲线
    sideRidgeVerts = []
    # 垂脊中点
    p0 = Vector((x,0,z))
    sideRidgeVerts.append(p0)

    # 垂脊终点
    p1 = Vector((x,y,z))
    sideRidgeVerts.append(p1)

    # 垂脊挂尖的头部，外延一脊筒
    p2 = p1 + Vector((0,ridgeLength,0))
    sideRidgeVerts.append(p2)

    sideRidgeCurve = utils.addCurveByPoints(
        CurvePoints=sideRidgeVerts,
        name='博脊线',
        root_obj=tileRootObj,
        resolution=64,
        order_u=2,
    )
    CurveData:bpy.types.Curve = sideRidgeCurve.data
    endCurvePoint = CurveData.splines[0].points[2]
    endCurvePoint.radius = 0
    utils.setOrigin(sideRidgeCurve,p0)
    utils.hideObj(sideRidgeCurve)

    # 平铺脊筒
    sideRidgeObj = __arrayRidgeByCurve(
        buildingObj=buildingObj,
        sourceObj=aData.ridgeFront_source,
        ridgeCurve=sideRidgeCurve,
        ridgeName='博脊',
        userMerge=False
    )

    # 250113 设置琉璃材质
    mat.setGlazeStyle(sideRidgeObj)

    return

# 营造屋脊
def __buildRidge(buildingObj: bpy.types.Object,
                 rafter_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    
    # 营造顶部正脊
    if bData.roof_style not in (
        con.ROOF_XUANSHAN_JUANPENG,
        con.ROOF_YINGSHAN_JUANPENG,
        con.ROOF_XIESHAN_JUANPENG,
        con.ROOF_LUDING,):
        __buildTopRidge(buildingObj,rafter_pos)
    
    # 营造前后垂脊（不涉及庑殿，自动判断硬山/悬山、歇山做法的不同）
    if bData.roof_style not in (
            con.ROOF_WUDIAN,
            con.ROOF_LUDING):
        # 排布垂脊兽前、垂脊兽后、跑兽
        __buildFrontRidge(buildingObj,rafter_pos)
        # 排布排山勾滴
        __buildSideTile(buildingObj,rafter_pos)

    # 营造歇山戗脊、庑殿垂脊
    if bData.roof_style in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
            con.ROOF_LUDING):
        __buildCornerRidge(buildingObj,rafter_pos)

    # 营造歇山的博脊
    if bData.roof_style in (con.ROOF_XIESHAN,
                            con.ROOF_XIESHAN_JUANPENG):
        __buildSideRidge(buildingObj,rafter_pos)

    # 营造盝顶的围脊
    if bData.roof_style == con.ROOF_LUDING:
        __buildSurroundRidge(buildingObj,rafter_pos)

    return

# 对外的统一调用接口
# 一次性重建所有的瓦做
def buildTile(buildingObj: bpy.types.Object):
    # 添加或清空根节点
    __setTileRoot(buildingObj)

    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp

    # 自动计算瓦垄长宽，不再需要用户输入
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale
    bData['tile_width'] = aData.dripTile_source.dimensions.x * tileScale
    bData['tile_length'] = aData.circularTile_source.dimensions.y * tileScale
    # 250612 同时初始化tile_width_real
    bData['tile_width_real'] = bData.tile_width

    # 计算桁檩定位点
    purlin_pos = buildBeam.getPurlinPos(buildingObj)
    # 如果有斗栱，剔除挑檐桁
    # 在梁架、椽架、角梁的计算中不考虑挑檐桁
    rafter_pos = purlin_pos.copy()
    if (bData.use_dg                # 不使用斗栱的不用挑檐桁
        and bData.dg_extend > 0     # 一斗三升这种无出跳的，不用挑檐桁
        ):
        del rafter_pos[0]

    utils.outputMsg("Building Tiles Front/Back...")
    # 绘制前后坡瓦面网格
    tileGrid = __drawTileGrid(
        buildingObj,
        rafter_pos,
        direction='X')
    # 250114 标记前后檐瓦面，后续在做垂脊定位时，可以精确判断瓦垄位置
    oData : acaData = tileGrid.ACA_data
    oData['aca_type'] = con.ACA_TYPE_TILE_GRID
    # 在网格上铺瓦
    __arrayTileGrid(
        buildingObj,
        rafter_pos,
        tileGrid,
        direction='X')
    
    # 仅庑殿、歇山做两山的瓦面
    if bData.roof_style in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
            con.ROOF_LUDING,):
        utils.outputMsg("Building Tiles Left/Right...")
        # 绘制两山瓦面网格
        tileGrid = __drawTileGrid(
            buildingObj,
            rafter_pos,
            direction='Y')
        # 在网格上铺瓦
        __arrayTileGrid(
            buildingObj,
            rafter_pos,
            tileGrid,
            direction='Y')
        
    # 添加屋脊
    utils.outputMsg("Building Ridge...")
    __buildRidge(buildingObj,rafter_pos)

    # 重新聚焦根节点
    utils.focusObj(buildingObj)

    return
    