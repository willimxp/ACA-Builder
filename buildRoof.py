# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   椽架的营造
import bpy
import bmesh
import math
from mathutils import Vector,Euler

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from .data import ACA_data_template as tmpData
from . import utils
from . import buildDougong
from . import buildBeam
from . import buildRooftile
from . import texture as mat

# 添加屋顶根节点
def __addRoofRoot(buildingObj:bpy.types.Object):
    # 设置目录
    buildingColl = buildingObj.users_collection[0]
    utils.focusCollection(buildingColl.name)

    # 设置根节点
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT) 
    if roofRootObj != None:
        utils.deleteHierarchy(roofRootObj)
    else:
        # 250108 以柱头为屋顶层的起始点
        # 台基高度 + 柱高
        bData : acaData = buildingObj.ACA_data # 载入数据
        tile_base = bData.platform_height \
                    + bData.piller_height 
        
        # 创建根节点
        roofRootObj = utils.addEmpty(
            name='屋顶层',
            parent = buildingObj,
            location=(0,0,tile_base),
        )
        roofRootObj.ACA_data['aca_obj'] = True
        roofRootObj.ACA_data['aca_type'] = con.ACA_TYPE_ROOF_ROOT

    return roofRootObj

# 设置“椽望”根节点
def __addRafterRoot(buildingObj:bpy.types.Object)->bpy.types.Object:
    # 设置目录
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('椽望',parentColl=buildingColl) 
    
    # 新建或清空根节点
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    if rafterRootObj == None:
        # 绑定在屋顶根节点下
        roofRootObj = utils.getAcaChild(
            buildingObj,con.ACA_TYPE_ROOF_ROOT)
        
        # 创建椽望根对象
        rafterRootObj = utils.addEmpty(
            name = "椽望层",
            parent = roofRootObj,
            location=(0,0,0)
        )
        rafterRootObj.ACA_data['aca_obj'] = True
        rafterRootObj.ACA_data['aca_type'] = con.ACA_TYPE_RAFTER_ROOT
        
    else:
        utils.deleteHierarchy(rafterRootObj)
        utils.focusCollByObj(rafterRootObj)

    # 250108 屋顶层原点改为柱头，椽望层相应抬高到斗栱高度
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    zLoc = 0
    # 如果有斗栱，抬高斗栱高度
    if bData.use_dg:
        zLoc += bData.dg_height
        # 是否使用平板枋
        if bData.use_pingbanfang:
            zLoc += con.PINGBANFANG_H*dk
    else:
        # 以大梁抬升檐桁垫板高度，即为挑檐桁下皮位置
        zLoc += con.BOARD_YANHENG_H*dk
    rafterRootObj.location.z = zLoc

    return rafterRootObj

# 根据给定的宽度，计算最佳的椽当宽度
# 采用一椽一当，椽当略大于椽径
def __getRafterGap(buildingObj,rafter_tile_width:float):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK

    # 根据椽当=1椽径估算，取整
    rafter_count = math.floor(rafter_tile_width / (con.YUANCHUAN_D*dk*2))
    # 最终椽当宽度
    rafter_gap = rafter_tile_width / rafter_count

    return rafter_gap

# 营造里口木(在没有飞椽时，也就是大连檐)
# 通过direction='X'或'Y'决定山面和檐面
def __buildLKM(buildingObj:bpy.types.Object,
               purlin_pos,
               direction):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    # 获取金桁位置，做为里口木的宽度
    jinhengPos = purlin_pos[1]

    # 获取檐椽对象
    if direction == 'X':    # 前后檐
        rafterType = con.ACA_TYPE_RAFTER_FB
    else:
        rafterType = con.ACA_TYPE_RAFTER_LR
    yanRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,rafterType)
    # 计算檐椽头坐标
    yanchuan_head_co = utils.getObjectHeadPoint(yanRafterObj,
            is_symmetry=(True,True,False))
    # 里口木相对于檐口的位移，与檐椽上皮相切，并内收一个雀台，
    offset = Vector(
        (-(con.QUETAI+con.LIKOUMU_Y/2)*dk, # 内收一个雀台
        0,
        (con.YUANCHUAN_D/2+con.LIKOUMU_H/2)*dk)) # 从椽中上移
    # 转换到檐椽坐标系
    offset.rotate(yanRafterObj.rotation_euler)

    # 前后檐、两山的location，rotation不同
    if direction == 'X': 
        LKM_name = "里口木.前后"
        LKM_loc:Vector = (yanchuan_head_co + offset)*Vector((0,1,1))
        LKM_rotate = (-yanRafterObj.rotation_euler.y,0,0)
        LKM_scale = (jinhengPos.x * 2,con.LIKOUMU_Y*dk,con.LIKOUMU_H*dk)
        LKM_mirrorAxis = (False,True,False) # Y轴镜像
        LKM_type = con.ACA_TYPE_RAFTER_LKM_FB
    else:
        LKM_name = "里口木.两山"
        LKM_loc:Vector = (yanchuan_head_co + offset)*Vector((1,0,1))
        LKM_rotate = (yanRafterObj.rotation_euler.y,
                    0,math.radians(90))
        LKM_scale = (jinhengPos.y * 2,con.LIKOUMU_Y*dk,con.LIKOUMU_H*dk)
        LKM_mirrorAxis = (True,False,False) # X轴镜像
        LKM_type = con.ACA_TYPE_RAFTER_LKM_LR

    # 里口木生成
    LKMObj = utils.addCube(
                name=LKM_name,
                location=LKM_loc,
                dimension=LKM_scale,
                rotation=LKM_rotate,
                parent=rafterRootObj,
            )
    LKMObj.ACA_data['aca_obj'] = True
    LKMObj.ACA_data['aca_type'] = LKM_type
    # 设置材质，刷红漆
    mat.setMat(LKMObj,aData.mat_red)

    # 镜像
    utils.addModifierMirror(
        object=LKMObj,
        mirrorObj=rafterRootObj,
        use_axis=LKM_mirrorAxis
    )
    
    return LKMObj

# 椽名称
def __getRafterName(count):
    names = []
    if count > 1:
        names.append('檐椽')
    if count > 2:
        names.append('脑椽')
    if count > 3:
        names.insert(1,'花架椽')
    if count > 4:
        names[1] = '下花架椽'
        names.insert(2,'上花架椽')
    if count > 5:
        names.insert(2,'中花架椽')
    return names

# 营造前后檐椽子
# 庑殿、歇山可自动裁切
def __buildRafter_FB(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    # 金桁是数组中的第二个（已排除挑檐桁）
    jinhengPos = purlin_pos[1]
    # 计算椽当，考虑椽当居中，实际平铺长度减半椽
    # （真实的半椽，不做椽当取整计算）
    rafter_gap_x = __getRafterGap(buildingObj,
        rafter_tile_width=(jinhengPos.x-con.YUANCHUAN_D*dk))
    
    rafterNames = __getRafterName(len(purlin_pos))
    # 根据桁数组循环计算各层椽架
    for n in range(len(purlin_pos)-1):
        # 1.逐层定位椽子，直接连接上下层的桁檩(槫子)
        # 前后檐椽从X=0的中心平铺，并做四方镜像        
        rafter_end = purlin_pos[n] * Vector((0,1,1))
        rafter_start = purlin_pos[n+1] * Vector((0,1,1))
        # 椽当居中，将桁交点投影到X=0椽子偏移半椽（真实的半椽，不做椽当取整计算）
        rafter_offset = Vector((con.YUANCHUAN_D*dk,0,0))
        rafter_end += rafter_offset
        rafter_start += rafter_offset
        # 根据起始点创建椽子
        fbRafterObj = utils.addCylinderBy2Points(
            radius = con.YUANCHUAN_D/2*dk,
            start_point = rafter_start,
            end_point = rafter_end,
            name="前后檐.%d-%s" % (n+1,rafterNames[n]),
            root_obj = rafterRootObj
        )
        
        # 2. 各层椽子都上移，与桁檩上皮相切
        bpy.ops.transform.translate(
            value = (0,0,(con.HENG_COMMON_D+con.YUANCHUAN_D)*dk/2),
            orient_type = con.OFFSET_ORIENTATION
        )  
        
        # 3. 仅檐椽延长，按檐总平出加斜计算
        if n == 0:
            fbRafterObj.ACA_data['aca_obj'] = True
            fbRafterObj.ACA_data['aca_type'] = con.ACA_TYPE_RAFTER_FB
            # 檐椽斜率（圆柱体默认转90度）
            yan_rafter_angle = math.cos(fbRafterObj.rotation_euler.y)
            # 斗栱平出+14斗口檐椽平出
            yan_rafter_ex = con.YANCHUAN_EX * dk
            if bData.use_dg : 
                yan_rafter_ex += bData.dg_extend

            # 加斜计算
            fbRafterObj.dimensions.x += yan_rafter_ex / yan_rafter_angle
            utils.applyTransfrom(fbRafterObj,use_scale=True) # 便于后续做望板时获取真实长度

        # 4、歇山顶在山花处再加一层檐椽
        if (bData.roof_style in (con.ROOF_XIESHAN,
                                 con.ROOF_XIESHAN_JUANPENG)
            and n==0):
            # 复制檐椽
            tympanumRafter:bpy.types.Object = fbRafterObj.copy()
            tympanumRafter.data = fbRafterObj.data.copy()
            tympanumRafter.name = '山花补齐檐椽'
            bpy.context.collection.objects.link(tympanumRafter)
            tympanumRafter.ACA_data['aca_type'] = ''
            # 重设檐椽平铺宽度
            rafter_tile_x = purlin_pos[-1].x 
            utils.addModifierArray(
                object=tympanumRafter,
                count=int(rafter_tile_x /rafter_gap_x),
                offset=(0,-rafter_gap_x,0)
            )
            # 裁剪椽架，檐椽不做裁剪
            utils.addBisect(
                    object=tympanumRafter,
                    pStart=buildingObj.matrix_world @ purlin_pos[n],
                    pEnd=buildingObj.matrix_world @ purlin_pos[n+1],
                    pCut=buildingObj.matrix_world @ purlin_pos[n] + \
                        Vector((con.JIAOLIANG_Y*dk/2,0,0)),
                    clear_inner=True
            ) 
            # 四方镜像
            utils.addModifierMirror(
                object=tympanumRafter,
                mirrorObj=rafterRootObj,
                use_axis=(True,True,False)
            )

        # 4.1、卷棚顶的最后一个椽架上，再添加一层罗锅椽
        if (bData.roof_style in (
                con.ROOF_XUANSHAN_JUANPENG,
                con.ROOF_YINGSHAN_JUANPENG,
                con.ROOF_XIESHAN_JUANPENG,)
            and n==len(purlin_pos)-2):
            # p0点从上金桁檩开始（投影到X中心）
            p0 = purlin_pos[n] * Vector((0,1,1))
            # p1点从脊檩开始（投影到X中心）
            p1 = purlin_pos[n+1] * Vector((0,1,1))
            # p2点为罗锅椽的屋脊高度
            p2 = p1 + Vector((
                0,
                -purlin_pos[n+1].y,   # 回归到y=0的位置
                con.YUANCHUAN_D*dk  # 抬升1椽径，见马炳坚p20
            ))
            # p3点是为了控制罗锅椽的曲率，没有理论依据，我觉得好看就行
            p3 = p2 + Vector((0,-con.HENG_COMMON_D*dk,0))
            # 四点生成曲线
            curveRafter:bpy.types.Object = \
                utils.addCurveByPoints(
                    CurvePoints=(p0,p1,p2,p3),
                    name='罗锅椽',
                    root_obj=rafterRootObj)
            # 设置曲线的椽径（半径）
            curveRafter.data.bevel_depth = con.YUANCHUAN_D*dk/2
            # 调整定位
            rafter_offset = Vector((
                rafter_gap_x/2,     # 椽当坐中
                0,
                (con.HENG_COMMON_D*dk/2
                    +con.YUANCHUAN_D*dk*1.1))   # 桁檩相切，因为曲线弯曲后，略作了调整
            )
            curveRafter.location += rafter_offset
            # 裁剪掉尾部
            '''为了罗锅椽能与脑椽紧密相连，所以曲线延长到了脑椽上
            最后把这个部分再裁剪掉'''
            # 裁剪点置于桁檩上皮（转到全局坐标）
            pCut = (rafterRootObj.matrix_world @ 
                    purlin_pos[n+1]
                    +Vector((0,0,con.HENG_COMMON_D*dk/2)))
            pStart = rafterRootObj.matrix_world @ Vector((0,0,0))
            pEnd = rafterRootObj.matrix_world @ Vector((0,1,1))
            utils.addBisect(
                object=curveRafter,
                pStart=pStart,
                pEnd=pEnd,   #近似按45度斜切，其实有误差
                pCut=pCut,
                clear_inner=True,
                direction='Y'
            )            
            # 横向平铺
            rafter_tile_x = purlin_pos[-1].x 
            # 计算椽子数量：椽当数+1
            # 取整可小不可大，否则会超出博缝板，导致穿模
            count = math.floor(
                (rafter_tile_x- con.YUANCHUAN_D*dk)
                    /rafter_gap_x) + 1
            utils.addModifierArray(
                object=curveRafter,
                count=count,
                offset=(rafter_gap_x,0,0)
            )            
            # 四方镜像，Y向裁剪
            utils.addModifierMirror(
                object=curveRafter,
                mirrorObj=rafterRootObj,
                use_axis=(True,True,False),
                use_bisect=(False,True,False)
            )
            # 平滑
            utils.shaderSmooth(curveRafter)
            
        # 5. 各层椽子平铺
        if bData.roof_style == con.ROOF_WUDIAN and n != 0:
            # 庑殿的椽架需要延伸到下层宽度，以便后续做45度裁剪
            rafter_tile_x = purlin_pos[n].x
        elif bData.roof_style in (
                con.ROOF_YINGSHAN,
                con.ROOF_YINGSHAN_JUANPENG):
            # 硬山的椽架只做到山柱中线，避免与山墙打架
            rafter_tile_x = bData.x_total/2
        else:
            # 檐椽平铺到上层桁交点
            rafter_tile_x = purlin_pos[n+1].x  
        # 计算椽子数量：椽当数+1
        # 取整可小不可大，否则会超出博缝板，导致穿模
        count = math.floor(
            (rafter_tile_x- con.YUANCHUAN_D*dk)
                /rafter_gap_x) + 1
        utils.addModifierArray(
            object=fbRafterObj,
            count=count,
            offset=(0,-rafter_gap_x,0)
        )
        
        # 四、裁剪，仅用于庑殿，且檐椽不涉及
        if bData.roof_style == con.ROOF_WUDIAN and n!=0:
            # 裁剪椽架，檐椽不做裁剪
            utils.addBisect(
                    object=fbRafterObj,
                    pStart=buildingObj.matrix_world @ purlin_pos[n],
                    pEnd=buildingObj.matrix_world @ purlin_pos[n+1],
                    pCut=buildingObj.matrix_world @ purlin_pos[n] - \
                        Vector((con.JIAOLIANG_Y*dk/2,0,0)),
                    clear_outer=True
            ) 
        
        # 五、镜像必须放在裁剪之后，才能做上下对称     
        # 檐椽不在此时镜像，延后到整个椽架做完后镜像
        # 因为檐椽需要做AB色的贴图，且需要考虑居中对称问题
        if n != 0:
            utils.addModifierMirror(
                object=fbRafterObj,
                mirrorObj=rafterRootObj,
                use_axis=(True,True,False)
            )

        # 平滑
        utils.shaderSmooth(fbRafterObj)

    # 构造里口木
    __buildLKM(buildingObj,purlin_pos,'X') 

    return fbRafterObj

# 营造两山椽子
# 硬山、悬山建筑不涉及
def __buildRafter_LR(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    # 金桁是数组中的第二个（已排除挑檐桁）
    jinhengPos = purlin_pos[1]
    # 计算山面椽当
    rafter_gap_y = __getRafterGap(buildingObj,
        rafter_tile_width=(jinhengPos.y-con.YUANCHUAN_D*dk))     
    
    rafterNames = __getRafterName(len(purlin_pos))
    # 根据桁数组循环计算各层椽架
    for n in range(len(purlin_pos)-1):
        if bData.roof_style in (con.ROOF_XIESHAN,
                                con.ROOF_XIESHAN_JUANPENG): 
            if n > 0: continue  # 歇山山面仅做一层椽架
        # 1.逐层定位椽子，直接连接上下层的桁檩(槫子)
        rafter_offset = Vector((0,con.YUANCHUAN_D*dk,0))
        rafter_end = purlin_pos[n]*Vector((1,0,1))+rafter_offset
        rafter_start = purlin_pos[n+1]*Vector((1,0,1))+rafter_offset
        lrRafterObj = utils.addCylinderBy2Points(
            radius = con.YUANCHUAN_D/2*dk,
            start_point = rafter_start,
            end_point = rafter_end,
            name="两山.%d-%s" % (n+1,rafterNames[n]),
            root_obj = rafterRootObj
        )
        # 上移，与桁檩上皮相切
        bpy.ops.transform.translate(
            value = (0,0,(con.HENG_COMMON_D+con.YUANCHUAN_D)*dk/2),
            orient_type = con.OFFSET_ORIENTATION # GLOBAL/LOCAL ?
        )   
        
        # 檐面和山面的檐椽延长，按檐总平出加斜计算
        if n == 0:
            lrRafterObj.ACA_data['aca_obj'] = True
            lrRafterObj.ACA_data['aca_type'] = con.ACA_TYPE_RAFTER_LR
            # 檐椽斜率（圆柱体默认转90度）
            yan_rafter_angle = math.cos(lrRafterObj.rotation_euler.y)
            # 檐总平出=斗栱平出+14斗口檐椽平出（暂不考虑7斗口的飞椽平出）
            yan_rafter_ex = con.YANCHUAN_EX * dk
            if bData.use_dg : 
                yan_rafter_ex += bData.dg_extend
            # 檐椽加斜长度
            lrRafterObj.dimensions.x += yan_rafter_ex / yan_rafter_angle
            utils.applyTransfrom(lrRafterObj,use_scale=True) # 便于后续做望板时获取真实长度

        # 平铺Array
        if bData.roof_style == con.ROOF_WUDIAN and n != 0:
            # 庑殿的椽架需要延伸到下层宽度，以便后续做45度裁剪
            rafter_tile_y = purlin_pos[n].y
        else:
            # 檐椽平铺到上层桁交点
            rafter_tile_y = purlin_pos[n+1].y       
        utils.addModifierArray(
            object=lrRafterObj,
            count=round(rafter_tile_y /rafter_gap_y)+1,
            offset=(0,rafter_gap_y,0)
        )
        
        # 裁剪，仅用于庑殿，且檐椽不涉及
        if bData.roof_style in (con.ROOF_WUDIAN) and n!=0:
            utils.addBisect(
                    object=lrRafterObj,
                    pStart=buildingObj.matrix_world @ purlin_pos[n],
                    pEnd=buildingObj.matrix_world @ purlin_pos[n+1],
                    pCut=buildingObj.matrix_world @ purlin_pos[n] + \
                        Vector((con.JIAOLIANG_Y*dk/2,0,0)),
                    clear_inner=True
            ) 
            utils.shaderSmooth(lrRafterObj)
        
        # 五、镜像必须放在裁剪之后，才能做上下对称     
        # 檐椽不在此时镜像，延后到整个椽架做完后镜像
        # 因为檐椽需要做AB色的贴图，且需要考虑居中对称问题
        if n != 0 :
            utils.addModifierMirror(
                object=lrRafterObj,
                mirrorObj=rafterRootObj,
                use_axis=(True,True,False)
            )
    
    # 构造里口木
    __buildLKM(buildingObj,purlin_pos,'Y') 

    return

# 营造前后檐望板
# 与椽架代码解耦，降低复杂度
def __buildWangban_FB(buildingObj:bpy.types.Object,
                      purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    
    # 收集望板对象，并合并
    wangbanObjs = []

    # 望板只做1象限半幅，然后镜像
    # 根据桁数组循环计算各层椽架
    for n in range(len(purlin_pos)-1):
        # 望板宽度
        if n==0: # 平铺到上层桁交点     
            width = purlin_pos[n+1].x 
        else: # 其他椽架平铺到下层桁交点，然后切割
            width = purlin_pos[n].x
        # 歇山的望板统一取脊槫宽度
        if (bData.roof_style in (con.ROOF_XIESHAN,
                                 con.ROOF_XIESHAN_JUANPENG)
            and n>0):
            width = purlin_pos[-1].x
        # 起点在上层桁檩
        pstart = purlin_pos[n+1].copy()
        pstart.x = width/2
        # 终点在本层桁檩
        pend = purlin_pos[n].copy()
        pend.x = width/2
        # 摆放望板
        wangbanObj = utils.addCubeBy2Points(
            start_point=pstart,
            end_point=pend,
            depth=width,
            height=con.WANGBAN_H*dk,
            name="望板",
            root_obj=rafterRootObj,
            origin_at_start=True
        )
        
        # 檐椽望板延长，按檐总平出加斜计算
        if n==0:
            # 檐椽斜率（圆柱体默认转90度）
            angle = wangbanObj.rotation_euler.y
            # 斗栱平出+14斗口檐椽平出-里口木避让
            extend = con.YANCHUAN_EX * dk
            if bData.use_dg : 
                extend += bData.dg_extend
            # 檐出加斜
            extend_hyp = extend/math.cos(angle)
            # 里口木避让（无需加斜）
            extend_hyp -= (con.QUETAI            # 雀台避让
                    + con.LIKOUMU_Y)* dk    # 里口木避让
            # 加斜计算
            wangbanObj.dimensions.x += extend_hyp
            utils.applyTransfrom(wangbanObj,use_scale=True) 

        # 所有望板上移
        # 1. 上移到椽头，采用global坐标，半檩+半椽
        offset = con.HENG_COMMON_D/2*dk+con.YUANCHUAN_D/2*dk
        bpy.ops.transform.translate(
            value = (0,0,offset),
            orient_type = con.OFFSET_ORIENTATION
        )
        # 2. 上移到望板高度，采用local坐标，半椽+半望
        offset = con.WANGBAN_H/2*dk + con.YUANCHUAN_D/2*dk
        bpy.ops.transform.translate(
            value = (0,0,offset),
            orient_type = 'LOCAL'
        )

        # 仅庑殿需要裁剪望板
        if bData.roof_style == con.ROOF_WUDIAN:
            utils.addBisect(
                    object=wangbanObj,
                    pStart=buildingObj.matrix_world @ purlin_pos[n],
                    pEnd=buildingObj.matrix_world @ purlin_pos[n+1],
                    pCut=buildingObj.matrix_world @ purlin_pos[n] - \
                        Vector((con.JIAOLIANG_Y*dk/2,0,0)),
                    clear_outer=True
            ) 

        # 望板镜像
        utils.addModifierMirror(
            object=wangbanObj,
            mirrorObj=rafterRootObj,
            use_axis=(True,True,False)
        )
        wangbanObjs.append(wangbanObj)

        # 歇山顶的山花处，再补一小块望板
        if (bData.roof_style in (con.ROOF_XIESHAN,
                                 con.ROOF_XIESHAN_JUANPENG)
            and n ==0):
            tympanumWangban:bpy.types.Object = wangbanObj.copy()
            tympanumWangban.data = wangbanObj.data.copy()
            tympanumWangban.name = '山花补齐望板'
            tympanumWangban.modifiers.clear()
            tympanumWangban.ACA_data['aca_type'] = ''
            tympanumWangban.dimensions.y = purlin_pos[-1].x
            tympanumWangban.location.x += (purlin_pos[-1].x - purlin_pos[1].x)/2
            bpy.context.collection.objects.link(tympanumWangban)
            # 裁剪
            utils.addBisect(
                    object=tympanumWangban,
                    pStart=buildingObj.matrix_world @ Vector((0,0,0)),
                    pEnd=buildingObj.matrix_world @ Vector((-1,-1,0)),
                    pCut=buildingObj.matrix_world @ purlin_pos[0],
                    clear_inner=True
            )
            # 望板镜像
            utils.addModifierMirror(
                object=tympanumWangban,
                mirrorObj=rafterRootObj,
                use_axis=(True,True,False)
            )
            wangbanObjs.append(tympanumWangban)

        # 另做卷棚望板
        if (n == len(purlin_pos)-2 and 
            bData.roof_style in (
                con.ROOF_XUANSHAN_JUANPENG,
                con.ROOF_YINGSHAN_JUANPENG,
                con.ROOF_XIESHAN_JUANPENG,)):
            # p0点从上金桁檩开始（投影到X中心）
            p0 = purlin_pos[n] * Vector((0,1,1))
            # p1点从脊檩开始（投影到X中心）
            p1 = purlin_pos[n+1] * Vector((0,1,1))
            # p2点为罗锅椽的屋脊高度
            p2 = p1 + Vector((
                0,
                -purlin_pos[n+1].y,   # 回归到y=0的位置
                con.YUANCHUAN_D*dk  # 抬升1椽径，见马炳坚p20
            ))
            # p3点是为了控制罗锅椽的曲率，没有理论依据，我觉得好看就行
            p3 = p2 + Vector((0,-con.HENG_COMMON_D*dk,0))
            # 四点生成曲线
            curveRafter:bpy.types.Object = \
                utils.addCurveByPoints(
                    CurvePoints=(p0,p1,p2,p3),
                    name='卷棚望板',
                    root_obj=rafterRootObj,
                    height=con.WANGBAN_H*dk,
                    width=purlin_pos[-1].x *2
                    )
            # 调整定位
            rafter_offset = Vector((0,0,
                (con.HENG_COMMON_D*dk/2
                    +con.YUANCHUAN_D*dk*1.9))   # 与椽架相切，因为曲线弯曲后，略作了调整
            )
            curveRafter.location += rafter_offset
            # 裁剪掉尾部
            '''为了罗锅椽能与脑椽紧密相连，所以曲线延长到了脑椽上
            最后把这个部分再裁剪掉'''
            # 裁剪点置于桁檩上皮（转到全局坐标）
            pCut = (rafterRootObj.matrix_world @ 
                    purlin_pos[n+1]
                    +Vector((0,0,con.HENG_COMMON_D*dk/2)))
            utils.addBisect(
                object=curveRafter,
                pStart=rafterRootObj.matrix_world @Vector((0,0,0)),
                pEnd=rafterRootObj.matrix_world @Vector((0,1,1)),   #近似按45度斜切，其实有误差
                pCut=pCut,
                clear_inner=True,
                direction='Y'
            )
            # 四方镜像，Y向裁剪
            utils.addModifierMirror(
                object=curveRafter,
                mirrorObj=rafterRootObj,
                use_axis=(False,True,False),
                use_bisect=(False,True,False)
            )
            # 平滑
            utils.shaderSmooth(curveRafter)
            
    # 合并望板
    wangbanSetObj = utils.joinObjects(
        wangbanObjs,newName='望板-前后檐')

    return wangbanSetObj # EOF：__buildWangban_FB

# 营造两山望板
# 与椽架代码解耦，降低复杂度
def __buildWangban_LR(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    
    # 收集待合并的望板
    wangbanObjs = []

    # 望板只做1象限半幅，然后镜像
    # 根据桁数组循环计算各层椽架
    for n in range(len(purlin_pos)-1):
        # 歇山的山面只做一层望板
        if (bData.roof_style in (con.ROOF_XIESHAN,
                                 con.ROOF_XIESHAN_JUANPENG) 
            and n>0):
            continue
        # 望板宽度
        if n==0: # 平铺到上层桁交点     
            width = purlin_pos[n+1].y
        else: # 其他椽架平铺到下层桁交点，然后切割
            width = purlin_pos[n].y
        # 起点在上层桁檩
        pstart = purlin_pos[n+1].copy()
        pstart.y = width/2
        # 终点在本层桁檩
        pend = purlin_pos[n].copy()
        pend.y = width/2
        # 摆放望板
        wangbanObj = utils.addCubeBy2Points(
            start_point=pstart,
            end_point=pend,
            depth=width,
            height=con.WANGBAN_H*dk,
            name="望板",
            root_obj=rafterRootObj,
            origin_at_start=True
        )
        # 檐椽望板延长，按檐总平出加斜计算
        if n==0:
            # 檐椽斜率（圆柱体默认转90度）
            angle = wangbanObj.rotation_euler.y
            # 斗栱平出+14斗口檐椽平出-里口木避让
            extend = con.YANCHUAN_EX * dk
            if bData.use_dg : 
                extend += bData.dg_extend
            # 檐出加斜
            extend_hyp = extend/math.cos(angle)
            if bData.use_flyrafter:
                # 里口木避让（无需加斜）
                extend_hyp -= (con.QUETAI            # 雀台避让
                        + con.LIKOUMU_Y)* dk    # 里口木避让
            # 加斜计算
            wangbanObj.dimensions.x += extend_hyp
            utils.applyTransfrom(wangbanObj,use_scale=True)

        # 所有望板上移，与椽架上皮相切（从桁檩中心偏：半桁檩+1椽径+半望板）
        # 1. 上移到椽头，采用global坐标，半檩+半椽
        offset = con.HENG_COMMON_D/2*dk+con.YUANCHUAN_D/2*dk
        bpy.ops.transform.translate(
            value = (0,0,offset),
            orient_type = con.OFFSET_ORIENTATION
        )
        # 2. 上移到望板高度，采用local坐标，半椽+半望
        offset = con.WANGBAN_H/2*dk + con.YUANCHUAN_D/2*dk
        bpy.ops.transform.translate(
            value = (0,0,offset),
            orient_type = 'LOCAL'
        )

        # 仅庑殿需要裁剪望板
        if bData.roof_style == con.ROOF_WUDIAN:
            utils.addBisect(
                    object=wangbanObj,
                    pStart=buildingObj.matrix_world @ purlin_pos[n],
                    pEnd=buildingObj.matrix_world @ purlin_pos[n+1],
                    pCut=buildingObj.matrix_world @ purlin_pos[n] + \
                        Vector((con.JIAOLIANG_Y*dk/2,0,0)),
                    clear_inner=True
            ) 
        # 望板镜像
        utils.addModifierMirror(
            object=wangbanObj,
            mirrorObj=rafterRootObj,
            use_axis=(True,True,False)
        )  
        wangbanObjs.append(wangbanObj)
    
    # 合并望板
    wangbanSetObj = utils.joinObjects(
        wangbanObjs,newName='望板-两山')

    return wangbanSetObj # EOF：

# 根据檐椽，绘制对应飞椽
# 基于“一飞二尾五”的原则计算
def __drawFlyrafter(yanRafterObj:bpy.types.Object,
                    flyrafterName='飞椽')->bpy.types.Object:
    # 载入数据
    buildingObj = utils.getAcaParent(yanRafterObj,con.ACA_TYPE_BUILDING)
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK

    # 1、计算椽尾坐标
    # 檐椽斜角
    yanChuan_angle = yanRafterObj.rotation_euler.y 
    # 飞尾平出：7斗口*2.5=17.5斗口
    flyrafterEnd_pingchu = con.FLYRAFTER_EX/con.FLYRAFTER_HEAD_TILE_RATIO*dk
    # 飞尾长斜边的长度，平出转到檐椽角度
    flyrafterEnd_length = flyrafterEnd_pingchu / math.cos(yanChuan_angle) 
    # 飞椽仰角（基于飞尾楔形的对边为飞椽高）
    flyrafter_angle_change = math.asin(con.FLYRAFTER_H*dk/flyrafterEnd_length)

    # 2、计算椽头坐标
    # 飞椽的全局仰角
    flyrafter_angle = yanChuan_angle - flyrafter_angle_change
    # 飞椽头长度，按飞椽仰角加斜
    flyrafterHead_length = con.FLYRAFTER_EX*dk / math.cos(flyrafter_angle)
    # 调整半椽高度，确保飞椽头的中心在出檐线上
    flyrafterHead_co = flyrafterHead_length \
        - con.FLYRAFTER_H/2*dk * math.tan(flyrafter_angle)
    
    # 创建bmesh
    bm = bmesh.new()
    # 各个点的集合
    vectors = []

    # 第1点在飞椽腰，对齐了檐椽头，分割飞椽头、尾的转折点
    v1 = Vector((0,0,0))
    vectors.append(v1)

    # 第2点在飞椽尾
    # 飞尾在檐椽方向加斜
    v2 = Vector((-flyrafterEnd_length,0,0)) # 飞椽尾的坐标
    vectors.append(v2)

    # 第3点在飞椽腰的上沿
    v3 = Vector((0,0,con.FLYRAFTER_H*dk))    
    # 随椽头昂起
    v3.rotate(Euler((0,-flyrafter_angle_change,0),'XYZ'))
    vectors.append(v3)

    # 第4点在飞椽头上沿
    v4 = Vector((flyrafterHead_co,0,con.FLYRAFTER_H*dk))
    # 随椽头昂起
    v4.rotate(Euler((0,-flyrafter_angle_change,0),'XYZ'))
    vectors.append(v4)

    # 第5点在飞椽头下檐
    v5 = Vector((flyrafterHead_co,0,0))
    # 随椽头昂起
    v5.rotate(Euler((0,-flyrafter_angle_change,0),'XYZ'))
    vectors.append(v5)

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
    flyrafterEnd_face = bm.faces.new((vertices[0],vertices[1],vertices[2])) # 飞尾
    flyrafterHead_face =bm.faces.new((vertices[0],vertices[2],vertices[3],vertices[4])) # 飞头

    # 挤出厚度
    return_geo = bmesh.ops.extrude_face_region(bm, geom=[flyrafterEnd_face,flyrafterHead_face])
    verts = [elem for elem in return_geo['geom'] if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, verts=verts, vec=(0, con.FLYRAFTER_H*dk, 0))
    for v in bm.verts:
        # 移动所有点，居中
        v.co.y -= con.FLYRAFTER_H*dk/2
    
    # 确保face normal朝向
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    #=============================
    # 将Mesh绑定到Object上
    # 新建Mesh
    mesh = bpy.data.meshes.new(flyrafterName)
    bm.to_mesh(mesh)
    bm.free()
    # 新建Object
    flyrafterObj = bpy.data.objects.new(flyrafterName, mesh)
    bpy.context.collection.objects.link(flyrafterObj) 

    # 对齐檐椽位置
    yanchuan_head_co = utils.getObjectHeadPoint(yanRafterObj,
            is_symmetry=(True,True,False))
    # 向上位移半檐椽+一望板（基于水平投影的垂直移动)
    offset_z = (con.YUANCHUAN_D/2+con.WANGBAN_H)*dk
    #250207 改为基于檐椽角度的平行移动
    # offset_z = offset_z / math.cos(yanRafterObj.rotation_euler.y)
    # loc = yanchuan_head_co + Vector((0,0,offset_z))
    offset = Vector((0,0,offset_z))
    offset.rotate(yanRafterObj.rotation_euler)
    loc = yanchuan_head_co + offset
    # 位置
    flyrafterObj.location = loc
    # 对齐檐椽角度
    flyrafterObj.rotation_euler = yanRafterObj.rotation_euler

    # 重设Origin：把原点放在椽尾，方便后续计算椽头坐标
    utils.setOrigin(flyrafterObj,v2)

    # 重设旋转数据：把旋转角度与上皮对齐，方便后续摆放压椽尾望板
    change_rot = v4-v3
    utils.changeOriginRotation(change_rot,flyrafterObj)

    # 处理UV
    mat.UvUnwrap(flyrafterObj,type='cube')

    return flyrafterObj

# 营造檐椽
# 通过direction='X'或'Y'决定山面和檐面
def __buildFlyrafter(buildingObj,direction):
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)

    # 判断前后檐，还是两山
    if direction == 'X':    # 前后檐
        flyrafterName = '飞椽.前后'
        rafterType = con.ACA_TYPE_RAFTER_FB
        flyrafterType = con.ACA_TYPE_FLYRAFTER_FB
    else:
        flyrafterName = '飞椽.两山'
        rafterType = con.ACA_TYPE_RAFTER_LR
        flyrafterType = con.ACA_TYPE_FLYRAFTER_LR
    yanRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,rafterType)

    flyrafterObj = __drawFlyrafter(yanRafterObj,flyrafterName)
    flyrafterObj.parent = rafterRootObj
    flyrafterObj.ACA_data['aca_obj'] = True
    flyrafterObj.ACA_data['aca_type'] = flyrafterType

    # 复制檐椽的modifier到飞椽上，相同的array，相同的mirror
    utils.copyModifiers(from_0bj=yanRafterObj,to_obj=flyrafterObj)

# 营造压飞尾望板
# 通过direction='X'或'Y'决定山面和檐面
def __buildFlyrafterWangban(buildingObj,purlin_pos,direction):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    # 获取金桁位置，做为望板的宽度
    jinhengPos = purlin_pos[1]

    # 判断前后檐，还是两山
    if direction == 'X':    # 前后檐
        frwName = "压飞尾望板.前后"
        frwWidth = jinhengPos.x * 2    # 宽度取金桁交点
        mirrorAxis = (False,True,False) # Y轴镜像
        flyrafterType = con.ACA_TYPE_FLYRAFTER_FB
    else:
        frwName = "压飞尾望板.两山"
        frwWidth = jinhengPos.y * 2    # 宽度取金桁交点
        mirrorAxis = (True,False,False) # X轴镜像
        flyrafterType = con.ACA_TYPE_FLYRAFTER_LR
    
    # 生成前后檐压飞尾望板
    # 以飞椽为参考基准
    flyrafterObj = utils.getAcaChild(buildingObj,flyrafterType)
    # 长度取飞椽长度，闪躲大连檐
    frwDeepth = utils.getMeshDims(flyrafterObj).x \
            -(con.QUETAI+con.DALIANYAN_Y)*dk
    # 从飞椽尾，平移半飞椽长，向上半望板高
    offset = Vector((frwDeepth/2,0,con.WANGBAN_H/2*dk))
    offset.rotate(flyrafterObj.rotation_euler)
    if direction == 'X':
        frwLoc = (flyrafterObj.location+offset) * Vector((0,1,1)) # 飞椽尾
    else:
        frwLoc = (flyrafterObj.location+offset) * Vector((1,0,1)) # 飞椽尾
    # 生成压飞望板
    fwbObj = utils.addCube(
        name=frwName,
        location=frwLoc,
        dimension=(frwDeepth,frwWidth,con.WANGBAN_H*dk),
        rotation=flyrafterObj.rotation_euler, 
        parent=rafterRootObj,
    )
    # 镜像
    utils.addModifierMirror(
        object=fwbObj,
        mirrorObj=rafterRootObj,
        use_axis=mirrorAxis
    )
    
    return fwbObj

# 营造大连檐
# 通过direction='X'或'Y'决定山面和檐面
def __buildDLY(buildingObj,purlin_pos,direction):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    # 获取金桁位置，做为望板的宽度
    jinhengPos = purlin_pos[1]

    # 以飞椽为参考基准
    if direction == 'X':    # 前后檐
        flyrafterType = con.ACA_TYPE_FLYRAFTER_FB
    else:
        flyrafterType = con.ACA_TYPE_FLYRAFTER_LR
    flyrafterObj = utils.getAcaChild(buildingObj,flyrafterType)

    # 重新获取前后檐的檐椽的端头点坐标
    flyrafter_head_co = utils.getObjectHeadPoint(flyrafterObj,
            is_symmetry=(True,True,False))
    # 大连檐相对于檐口的位移，与檐椽上皮相切，并内收一个雀台，
    offset = Vector((-(con.QUETAI+con.LIKOUMU_Y/2)*dk, # 内收一个雀台
                    0,
                    (con.FLYRAFTER_H/2+con.DALIANYAN_H/2)*dk)) # 从飞椽中上移
    offset.rotate(flyrafterObj.rotation_euler)
    
    # 前后檐、两山的location，rotation不同
    if direction == 'X': 
        DLY_name = "大连檐.前后"
        DLY_rotate = (math.radians(90)-flyrafterObj.rotation_euler.y,0,0)
        DLY_loc:Vector = (flyrafter_head_co + offset)*Vector((0,1,1))
        DLY_scale = (jinhengPos.x * 2,  
            con.DALIANYAN_H*dk,
            con.DALIANYAN_Y*dk)
        if bData.roof_style in (
                con.ROOF_YINGSHAN,
                con.ROOF_YINGSHAN_JUANPENG
            ):
            # 硬山建筑的大连檐做到山墙边
            DLY_scale = (bData.x_total + con.SHANQIANG_WIDTH*dk*2,  
                con.DALIANYAN_H*dk,
                con.DALIANYAN_Y*dk)
        DLY_mirrorAxis = (False,True,False) # Y轴镜像
        DLY_type = con.ACA_TYPE_RAFTER_DLY_FB
    else:
        DLY_name = "大连檐.两山"
        DLY_rotate = (flyrafterObj.rotation_euler.y+math.radians(90),
                      0,math.radians(90))
        DLY_loc:Vector = (flyrafter_head_co + offset)*Vector((1,0,1))
        DLY_scale = (jinhengPos.y * 2,  
            con.DALIANYAN_H*dk,
            con.DALIANYAN_Y*dk)
        DLY_mirrorAxis = (True,False,False) # Y轴镜像
        DLY_type = con.ACA_TYPE_RAFTER_DLY_LR
    
    # 生成大连檐
    DLY_Obj = utils.addCube(
        name=DLY_name,
        location=DLY_loc,
        rotation=DLY_rotate,
        dimension=DLY_scale,
        parent=rafterRootObj,
    )
    DLY_Obj.ACA_data['aca_obj'] = True
    DLY_Obj.ACA_data['aca_type'] = DLY_type
    # 设置材质，刷红漆
    mat.setMat(DLY_Obj,aData.mat_red)

    # 添加镜像
    utils.addModifierMirror(
        object=DLY_Obj,
        mirrorObj=rafterRootObj,
        use_axis=DLY_mirrorAxis
    )

    return DLY_Obj
    

# 营造飞椽（以及里口木、压飞望板、大连檐等附属构件)
# 小式建筑中，可以不使用飞椽
def __buildFlyrafterAll(buildingObj:bpy.types.Object,purlinPos,direction):    
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    useFlyrafter = bData.use_flyrafter
    useWangban = bData.use_wangban

    frWangban = None
    if useFlyrafter:  # 用户可选择不使用飞椽
        # 构造飞椽
        __buildFlyrafter(buildingObj,direction)  

        # 压飞望板
        if useWangban:  # 用户可选择暂时不生成望板（更便于观察椽架形态）
            frWangban = __buildFlyrafterWangban(buildingObj,purlinPos,direction)     

        # 大连檐
        __buildDLY(buildingObj,purlinPos,direction)
        
    return frWangban

# 根据老角梁，绘制对应子角梁
# 基于“冲三翘四”的原则计算
# 硬山、悬山不涉及
def __drawCornerBeamChild(cornerBeamObj:bpy.types.Object,
                          ccbName='仔角梁'):
    # 载入数据
    buildingObj = utils.getAcaParent(
        cornerBeamObj,
        con.ACA_TYPE_BUILDING)
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    
    # 计算老角梁头
    cornerBeam_head_co = utils.getObjectHeadPoint(
                            cornerBeamObj,
                            is_symmetry=(True,True,False)
                        )
    # 向上位移半角梁高度，达到老角梁上皮
    offset:Vector = Vector((0,0,con.JIAOLIANG_H/2*dk))
    offset.rotate(cornerBeamObj.rotation_euler)
    cornerBeam_head_co += offset
    
    # 新建mesh
    mesh = bpy.data.meshes.new(ccbName)
    # 新建Object
    smallCornerBeamObj = bpy.data.objects.new(ccbName, mesh)
    bpy.context.collection.objects.link(smallCornerBeamObj) 
    smallCornerBeamObj.location = cornerBeam_head_co
    smallCornerBeamObj.rotation_euler = cornerBeamObj.rotation_euler # 将飞椽与檐椽对齐旋转角度

    # 创建bmesh
    bm = bmesh.new()
    # 各个点的集合
    vectors = []

    # 第1点在子角梁腰，对齐了老角梁头，分割子角梁头、子角梁尾的转折点
    v1 = Vector((0,0,0))
    vectors.append(v1)

    # 第2点在子角梁尾
    # 与老角梁同长
    cornerBeam_length = utils.getMeshDims(cornerBeamObj).x
    # 后尾补偿，确保子角梁后尾的origin与老角梁的origin相同
    # 避免子角梁与由戗之间有太大间隙
    offset = con.JIAOLIANG_H/4*dk/math.cos(cornerBeamObj.rotation_euler.y)
    v2 = Vector((-cornerBeam_length-offset,0,0))
    vectors.append(v2)

    # 第3点在子角梁尾向上一角梁高
    # 与老角梁同长
    v3 = Vector((-cornerBeam_length-offset ,0,con.JIAOLIANG_H*dk))
    vectors.append(v3)

    # 第4点在子角梁腰向上一角梁高
    l = con.JIAOLIANG_H*dk / math.cos(cornerBeamObj.rotation_euler.y)
    v4 = Vector((0,0,l))
    v4.rotate(Euler((0,-cornerBeamObj.rotation_euler.y,0)))
    vectors.append(v4)

    # 第5点，定位子角梁的梁头上沿
    # 在local坐标系中计算子角梁头的绝对位置
    # 计算冲出后的X、Y坐标，由飞椽平出+冲1椽（老角梁已经冲了2椽）
    scb_ex_length = (con.FLYRAFTER_EX + con.YUANCHUAN_D) * dk
    scb_abs_x = cornerBeam_head_co.x + scb_ex_length
    scb_abs_y = cornerBeam_head_co.y + scb_ex_length
    # 计算翘四后的Z坐标
    # 取檐椽头高度
    flyrafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_FB)
    flyrafter_head_co = utils.getObjectHeadPoint(
                            flyrafterObj,
                            is_symmetry=(True,True,False)
                        )
    # 翘四: 从飞椽头上皮，到子角梁上皮，其中要补偿0.75斗口，即半椽，合计调整一椽（见汤书p171）
    scb_abs_z = flyrafter_head_co.z + con.YUANCHUAN_D*dk \
            + bData.qiqiao*con.YUANCHUAN_D*dk # 默认起翘4椽
    scb_abs_co = Vector((scb_abs_x,scb_abs_y,scb_abs_z))
    # 将该起翘点存入dataset，后续翼角可供参考（相对于root_obj）
    bData['roof_qiao_point'] = scb_abs_co.copy()
    # 将坐标转换到子角梁坐标系中
    v5 = smallCornerBeamObj.matrix_local.inverted() @ scb_abs_co
    vectors.append(v5)
    
    # 第6点，定位子角梁的梁头下沿
    v6:Vector = (v4-v5).normalized()
    v6.rotate(Euler((0,-math.radians(90),0),'XYZ'))
    v6 = v6 * con.JIAOLIANG_H*dk + v5
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
    wei_face = bm.faces.new((vertices[0],vertices[1],vertices[2],vertices[3])) # 子角梁尾
    head_face =bm.faces.new((vertices[0],vertices[3],vertices[4],vertices[5])) # 子角梁头

    # 挤出厚度
    return_geo = bmesh.ops.extrude_face_region(bm, geom=[wei_face,head_face])
    verts = [elem for elem in return_geo['geom'] if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, verts=verts, vec=(0, con.JIAOLIANG_Y*dk, 0))

    # 移动所有点，居中
    for v in bm.verts:
        v.co.y -= con.JIAOLIANG_Y*dk/2

    # 确保face normal朝向
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(smallCornerBeamObj.data)
    smallCornerBeamObj.data.update()
    bm.free()

    # 把原点放在子角梁尾，方便后续计算椽头坐标
    new_origin = (v2+v3)/2
    utils.setOrigin(smallCornerBeamObj,new_origin)

    # 重设旋转数据：把旋转角度与子角梁头对齐，方便计算端头盘子角度
    change_rot = v5-v4
    utils.changeOriginRotation(change_rot,smallCornerBeamObj)

    # uv处理
    mat.UvUnwrap(smallCornerBeamObj,type='cube')

    return smallCornerBeamObj

# 营造角梁（包括老角梁、子角梁、由戗）
def __buildCornerBeam(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    
    # 计算角梁数据，忽略第一个挑檐桁交点，直接从正心桁到脊桁分段生成
    cb_collection = []
    # 根据桁数组循环计算各层椽架
    for n in range(len(purlin_pos)-1) :
        if n == 0:  #翼角角梁
            if bData.use_flyrafter:
                # 老角梁用压金做法，压在槫子之下，以便与子角梁相扣
                pEnd = Vector(purlin_pos[n+1]) \
                    - Vector((0,0,con.JIAOLIANG_H*dk*con.JIAOLIANG_WEI_KOUJIN))
                # 计算老角梁头先放在正心桁交点上，后续根据檐出、冲出延长
                # pStart = Vector(purlin_pos[n]) \
                #     + Vector((0,0,con.JIAOLIANG_H*dk*con.JIAOLIANG_HEAD_YAJIN))
                # 250120 为了防止在步架过短时，仔角梁出现反弓
                # 允许用户手工调整老角梁头与挑檐桁的交错位置
                pStart = Vector(purlin_pos[n]) \
                    + Vector((0,0,con.JIAOLIANG_H*dk*bData.liangtou))
            else:
                # 老角梁用扣金做法，压在槫子之上
                pEnd = Vector(purlin_pos[n+1]) \
                    + Vector((0,0,con.JIAOLIANG_H*dk*con.YOUQIANG_YAJIN))
                # 为了能够起翘，转角斗栱上不做压金
                pStart = Vector(purlin_pos[n]) \
                    + Vector((0,0,con.JIAOLIANG_H*dk))
            cb_collection.append((pStart,pEnd,'老角梁'))
        else:
            # 歇山只有老角梁，没有由戗
            if bData.roof_style in (con.ROOF_XIESHAN,
                                    con.ROOF_XIESHAN_JUANPENG) : 
                continue
            # 其他角梁为压金做法，都压在桁之上
            pStart = Vector(purlin_pos[n]) \
                + Vector((0,0,con.JIAOLIANG_H*dk*con.YOUQIANG_YAJIN))
            pEnd = Vector(purlin_pos[n+1]) \
                + Vector((0,0,con.JIAOLIANG_H*dk*con.YOUQIANG_YAJIN))
            cb_collection.append((pStart,pEnd,'由戗'))
    
    # 根据cb集合，放置角梁对象
    for n in range(len(cb_collection)):
        pStart = cb_collection[n][0]
        pEnd = cb_collection[n][1]
        CornerBeamName = cb_collection[n][2]
        CornerBeamObj = utils.addCubeBy2Points(
            start_point=pStart,
            end_point=pEnd,
            depth=con.JIAOLIANG_Y*dk,
            height=con.JIAOLIANG_H*dk,
            name=CornerBeamName,
            root_obj=rafterRootObj,
            origin_at_end=True
        )
        
        if n==0:    # 老角梁
            CornerBeamObj.ACA_data['aca_obj'] = True
            CornerBeamObj.ACA_data['aca_type'] = con.ACA_TYPE_CORNER_BEAM
            # 延长老角梁
            # 上檐平出
            ex_length = con.YANCHUAN_EX*dk
            # 斗栱平出
            if bData.use_dg:
                ex_length += bData.dg_extend
            # 冲出
            if bData.use_flyrafter:
                # 有飞椽，少冲一椽，留给飞椽冲
                ex_length += (bData.chong-1)*con.YUANCHUAN_D*dk
            else:
                ex_length += bData.chong*con.YUANCHUAN_D*dk
            # 水平面加斜45度
            ex_length = ex_length * math.sqrt(2)
            # 立面加斜老角梁扣金角度   
            ex_length = ex_length / math.cos(CornerBeamObj.rotation_euler.y)
            CornerBeamObj.dimensions.x += ex_length
            utils.applyTransfrom(CornerBeamObj,use_scale=True)
            utils.addModifierBevel(
                object=CornerBeamObj,
                width=con.BEVEL_LOW
            )
            # 替换老角梁造型
            if aData.cornerbeam_source != None:
                cbNewObj = utils.copyObject(
                    sourceObj=aData.cornerbeam_source,
                    singleUser=True
                )
                # 传递老角梁属性
                utils.replaceObject(CornerBeamObj,cbNewObj)
                # 添加镜像
                utils.addModifierMirror(
                    object=cbNewObj,
                    mirrorObj=rafterRootObj,
                    use_axis=(True,True,False))
            
            if bData.use_flyrafter:
                # 绘制子角梁
                cbcObj:bpy.types.Object = \
                    __drawCornerBeamChild(CornerBeamObj,'仔角梁')
                # 设置材质
                mat.setMat(cbcObj,aData.mat_paint_ccb)
                cbcObj.parent = rafterRootObj
                cbcObj.ACA_data['aca_obj'] = True
                cbcObj.ACA_data['aca_type'] = con.ACA_TYPE_CORNER_BEAM_CHILD
                utils.addModifierMirror(
                    object=cbcObj,
                    mirrorObj=rafterRootObj,
                    use_axis=(True,True,False))
                utils.addModifierBevel(
                    object=cbcObj,
                    width=con.BEVEL_LOW
                )

        # 添加镜像
        utils.addModifierMirror(
            object=CornerBeamObj,
            mirrorObj=rafterRootObj,
            use_axis=(True,True,False))
    
    return

# 营造翼角小连檐实体（连接翼角椽）
def __buildCornerRafterEave(buildingObj:bpy.types.Object):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    # 屋顶根节点
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    # 前后檐椽
    yanRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_FB)
    
    # 1.小连檐起点：对接前后檐正身里口木位置
    # 里口木
    lkmObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_LKM_FB)
    # 对接前后檐正身里口木位置
    pStart = Vector((
        utils.getMeshDims(lkmObj).x / 2,    # 大连檐右端顶点，长度/2
        lkmObj.location.y,
        lkmObj.location.z
    ))

    # 2.小连檐终点
    # 2.1 立面高度，基于老角梁头坐标（小连檐受到老角梁的限制）
    # 老角梁
    cornerBeamObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_CORNER_BEAM)
    cornerBeamHead_co = utils.getObjectHeadPoint(cornerBeamObj,
            is_symmetry=(True,True,False))            
    # 定位小连檐终点（靠近角梁的一侧）
    # 小连檐中点与老角梁上皮平
    if bData.use_flyrafter:
        # 下皮平，从中心+半角梁高+半个里口木高
        offset = Vector((-con.LIKOUMU_Y/2*dk-con.QUETAI*dk,
            con.JIAOLIANG_Y/4*dk, # 退让1/4角梁,
            con.JIAOLIANG_H/2*dk + con.LIKOUMU_H/2*dk))
    else:
        # 上皮平，从老角梁头+半角梁-半里口木
        offset = Vector((-con.LIKOUMU_Y/2*dk-con.QUETAI*dk,
            con.JIAOLIANG_Y/4*dk, # 退让1/4角梁,
            con.JIAOLIANG_H/2*dk - con.LIKOUMU_H/2*dk))
    offset.rotate(cornerBeamObj.rotation_euler)
    pEnd_z = cornerBeamHead_co + offset

    # 2.2 平面X/Y坐标，从里口木按出冲系数进行计算
    #（不依赖角梁，避免难以补偿的累计误差）
    # 上檐平出
    rafterExtend = con.YANCHUAN_EX*dk
    # 斗栱平出
    if bData.use_dg:
        rafterExtend += bData.dg_extend
    # 翼角冲出
    if bData.use_flyrafter and bData.chong>0:
        # 有飞椽时，翘飞椽冲一份，其他在檐椽冲出
        rafterExtend += (bData.chong-1)*con.YUANCHUAN_D*dk
    else:
        # 没有飞椽时，全部通过檐椽冲出
        rafterExtend += bData.chong*con.YUANCHUAN_D*dk
    # 避让老角梁，见汤崇平书籍的p196
    shift = con.JIAOLIANG_Y/4*dk * math.sqrt(2)
    # 定位小连檐结束点
    pEnd = Vector((
        bData.x_total/2 + rafterExtend - shift,
        bData.y_total/2 + rafterExtend - con.QUETAI*dk,
        pEnd_z.z
    ))
    
    # 4.绘制小连檐对象
    CurvePoints = utils.setEaveCurvePoint(pStart,pEnd)
    tilt = - yanRafterObj.rotation_euler.y
    xly_curve_obj = utils.addBezierByPoints(
                        CurvePoints=CurvePoints,
                        tilt=tilt,
                        name='小连檐',
                        root_obj=rafterRootObj,
                        width = con.LIKOUMU_Y*dk,
                        height = con.LIKOUMU_H*dk,
                    )
    # Curve转为mesh
    utils.applyAllModifer(xly_curve_obj)
    # 处理UV
    mat.UvUnwrap(xly_curve_obj)

    # 相对角梁做45度对称
    utils.addModifierMirror(
        object=xly_curve_obj,
        mirrorObj=cornerBeamObj,
        use_axis=(False,True,False)
    )
    # 四面对称
    utils.addModifierMirror(
        object=xly_curve_obj,
        mirrorObj=rafterRootObj,
        use_axis=(True,True,False)
    )
    # 设置材质，刷红漆
    mat.setMat(xly_curve_obj,
        aData.mat_red)

# 营造翼角椽参考线，后续为翼角椽椽头的定位
# 起点=定为正身檐椽的最后一根椽头坐标
# 终点的Z坐标=与老角梁平，与起翘参数无关
# 终点的X、Y坐标=以上檐平出（斗栱平出）+出冲数据进行计算
# 添加bezier控制点，做出曲线
def __buildCornerRafterCurve(buildingObj:bpy.types.Object):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    # 屋顶根节点
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
   
    # 1.曲线起点：对齐最后一根正身檐椽的椽头
    # 前后檐椽
    yanRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_FB)
    # 椽头坐标
    yanRafterHead_co = utils.getObjectHeadPoint(yanRafterObj,
            eval=True,  # eval=True可以取到应用了array后的结果
            is_symmetry=(True,True,False))
    # 曲线起点
    pStart = yanRafterHead_co
    
    # 2.曲线终点
    # 2.1 立面Z坐标，基于老角梁头坐标计算，与起翘参数无关
    # 老角梁
    cornerBeamObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_CORNER_BEAM)
    # 老角梁头坐标（顶面几何中心）
    cornerBeamHead_co = utils.getObjectHeadPoint(cornerBeamObj,
            is_symmetry=(True,True,False))
    # 偏移调整：避开老角梁穿模
    if bData.use_flyrafter:
        # 使用飞椽时，小连檐与角梁做下皮平
        # 檐椽位移：半角梁高-半椽
        offset_z = con.JIAOLIANG_H/2*dk - con.YUANCHUAN_D/2*dk
    else : 
        # 不使用飞椽时，小连檐与角梁做上皮平
        # 檐椽位移：半角梁-里口木-半椽
        offset_z = con.JIAOLIANG_H/2*dk - con.LIKOUMU_H*dk - con.YUANCHUAN_D/2*dk
    # 参考汤崇平的书，退让1/4
    offset_y = con.JIAOLIANG_Y/4*dk # 退让1/4角梁
    offset = Vector((0,offset_y,offset_z))
    offset.rotate(cornerBeamObj.rotation_euler)
    cornerBeamHead_co += offset
    pEnd_z = cornerBeamHead_co.z

    # 2.2 平面X/Y坐标，从椽头按出冲系数进行计算
    #（不依赖角梁，避免难以补偿的累计误差）
    # 上檐平出
    ex = con.YANCHUAN_EX*dk
    # 斗栱平出
    if bData.use_dg:
        ex += bData.dg_extend
    # 冲出
    if bData.use_flyrafter and bData.chong>0:
        # 有飞椽时，翘飞椽冲一份，其他在檐椽冲出
        ex += (bData.chong-1)*con.YUANCHUAN_D*dk
    else:
        # 没有飞椽时，全部通过檐椽冲出
        ex += bData.chong*con.YUANCHUAN_D*dk
    # 避让老角梁，见汤崇平书籍的p196
    shift = con.JIAOLIANG_Y/4*dk * math.sqrt(2)
    pEnd = Vector((
        bData.x_total/2 + ex - shift,
        bData.y_total/2 + ex,
        pEnd_z))
    
    # 4.绘制翼角椽定位线
    CurvePoints = utils.setEaveCurvePoint(pStart,pEnd)
    # resolution决定了后续细分的精度
    # 我尝试了64，150,300,500几个值，150能看出明显的误差，300和500几乎没有太大区别
    rafterCurve_obj = utils.addBezierByPoints(
            CurvePoints,
            name='翼角椽定位线',
            resolution = con.CURVE_RESOLUTION,
            root_obj=rafterRootObj
        ) 
    rafterCurve_obj.ACA_data['aca_obj'] = True
    rafterCurve_obj.ACA_data['aca_type'] = con.ACA_TYPE_CORNER_RAFTER_CURVE
    utils.hideObj(rafterCurve_obj)
    return rafterCurve_obj

# 营造翼角椽(Corner Rafter,缩写CR)
def __buildCornerRafter(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    # 屋顶根节点
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    cornerBeamObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_CORNER_BEAM)
    
    # 1、计算翼角椽根数---------------------------
    # 工程上会采用奇数个翼角椽，采用“宜密不宜疏”原则
    # 工程做法为：(廊步架+斗栱出踩+檐总平出)/(1椽+1当)，取整，遇偶数加1（其中没有考虑冲的影响）
    # 见汤崇平《中国传统建筑木作知识入门》P195
    # 1.1 计算檐出
    # 檐步架=正心桁-下金桁
    yanExtend = purlin_pos[0].x -purlin_pos[1].x 
    # 檐平出=14斗口的檐椽平出+7斗口的飞椽平出
    yanExtend += con.YANCHUAN_EX * dk
    # 飞椽平出
    if bData.use_flyrafter:
        yanExtend += con.FLYRAFTER_EX * dk
    # 1.2 计算椽当（用前后檐椽当计算，以便在正视图中协调，注意这个数据已经是一椽+一当）
    jinhengPos = purlin_pos[1]  # 金桁是数组中的第二个（已排除挑檐桁）
    rafter_gap = __getRafterGap(buildingObj,
        rafter_tile_width=jinhengPos.x) # 以前后檐计算椽当，两山略有差别
    # 翼角椽根数
    crCount = round(yanExtend / rafter_gap)
    # 确认为奇数
    if crCount % 2 == 0: crCount += 1
    
    # 2、放置翼角椽---------------------------
    # 绘制檐口参考线
    crCurve = __buildCornerRafterCurve(buildingObj)
    # 计算每根翼角椽的椽头坐标
    crEndPoints = utils.getBezierSegment(crCurve,crCount)
    # 第一根翼角椽尾与正身椽尾同高
    crStart_0 = jinhengPos + Vector((0,0,(con.HENG_COMMON_D+con.YUANCHUAN_D)/2*dk))
    # 翼角椽尾展开的合计宽度
    crStartSpread = con.CORNER_RAFTER_START_SPREAD * dk
    # 依次摆放翼角椽
    cornerRafterColl = []  # 暂存翼角椽，传递给翘飞椽参考
    for n in range(len(crEndPoints)):
        # 椽头沿角梁散开一斗口
        offset = Vector((crStartSpread*n,0,0))
        offset.rotate(cornerBeamObj.rotation_euler)
        crStart = crStart_0 + offset
        cornerRafterObj = utils.addCylinderBy2Points(
            start_point = crStart, 
            end_point = crEndPoints[n],   # 在曲线上定位的椽头坐标
            radius=con.YUANCHUAN_D/2*dk,
            name='翼角椽',
            root_obj=rafterRootObj
        )
        # 裁剪椽架，檐椽不做裁剪
        utils.addBisect(
                object=cornerRafterObj,
                pStart=buildingObj.matrix_world @ purlin_pos[0],
                pEnd=buildingObj.matrix_world @ purlin_pos[1],
                pCut=buildingObj.matrix_world @ purlin_pos[0] - \
                    Vector((con.JIAOLIANG_Y*dk/2*math.sqrt(2),0,0)),
                clear_outer=True
        ) 
        # 为了便于贴图，将镜像延后到所有椽架做完后添加
        # # 角梁45度对称
        # utils.addModifierMirror(
        #     object=cornerRafterObj,
        #     mirrorObj=cornerBeamObj,
        #     use_axis=(False,True,False)
        # )
        # # 四向对称
        # utils.addModifierMirror(
        #     object=cornerRafterObj,
        #     mirrorObj=rafterRootObj,
        #     use_axis=(True,True,False)
        # )

        cornerRafterColl.append(cornerRafterObj)
    
    return cornerRafterColl

# 绘制翼角椽望板
# 分别连接金桁交点、各个翼角椽头上皮
def __drawCrWangban(
        origin,
        crEnds,
        crCollection,
        root_obj,
        ):
    # 载入数据
    buildingObj = utils.getAcaParent(
        root_obj,con.ACA_TYPE_BUILDING)
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    
    # 任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add(
        location=origin
    )
    crWangbanObj = bpy.context.object
    crWangbanObj.parent = root_obj    

    # 创建bmesh
    bm = bmesh.new()
    # 各个点的集合
    vectors = []

    # 循环插入翼角椽尾
    for n in range(len(crEnds)):
        crEnd_loc = crWangbanObj.matrix_world.inverted() @ crEnds[n]
        # 第一个檐口点在正身椽头，纠正到金桁X位置，以免和正身望板打架
        if n==0:
            crEnd_loc.x = 0
        # 基于翼角椽坐标系做位移
        # 翼角椽椽数组比檐口点数组少两个，只能特殊处理一下
        if n == 0:
            m = 0
        elif n == len(crEnds) -1 :
            m = n-2
        else:
            m = n-1
        crObj:bpy.types.Object = crCollection[m]
        # X：避让里口木和雀台，Z：抬升半椽
        offset = Vector(((-con.QUETAI-con.LIKOUMU_Y)*dk,0,con.YUANCHUAN_D/2*dk))
        offset.rotate(crObj.rotation_euler)
        crEnd_loc += offset
        vectors.insert(0,crEnd_loc)
    
    # 循环插入翼角椽头
    for n in range(len(crCollection)):
        # 翘飞椽头坐标,插入队列尾
        crObj:bpy.types.Object = crCollection[n]
        crHead_loc = crWangbanObj.matrix_world.inverted() @ crObj.location
        offset = Vector((0,0,con.YUANCHUAN_D/2*dk))
        offset.rotate(crObj.rotation_euler)
        crHead_loc += offset
        # 在第一根椽之前，手工添加金交点一侧的后点
        if n==0:
            vectors.append((
                0,crHead_loc.y,crHead_loc.z
            ))
        # 循环依次添加椽头
        vectors.append(crHead_loc)
        # 在最后一根椽后，再手工追加角梁侧的后点
        if n==len(crCollection)-1:
            vectors.append(crHead_loc)

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
    rafterObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_FB)
    offset=Vector((0, 0,con.WANGBAN_H*dk))
    offset.rotate(rafterObj.rotation_euler)
    return_geo = bmesh.ops.extrude_face_region(bm, geom=bm.faces)
    verts = [elem for elem in return_geo['geom'] if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, verts=verts, vec=offset)
    # ps，这个挤出略有遗憾，没有按照每个面的normal进行extrude

    # 确保face normal朝向
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(crWangbanObj.data)
    crWangbanObj.data.update()
    bm.free()

    # 处理UV
    mat.UvUnwrap(crWangbanObj,type='cube')

    return crWangbanObj

# 营造翼角椽望板
def __buildCrWangban(buildingObj:bpy.types.Object
                     ,purlin_pos,
                     cornerRafterColl):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    # 屋顶根节点
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    # 老角梁
    cornerBeamObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_CORNER_BEAM)
    # 翼角椽定位线
    CrCurve = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_CORNER_RAFTER_CURVE)
    
    # 获取翼角椽尾坐标集合
    crCount = len(cornerRafterColl)
    CrEnds = utils.getBezierSegment(
        CrCurve,
        crCount,
        withCurveEnd = True)
    
    # 绘制翼角椽望板
    origin = purlin_pos[1] + Vector((
        0,0,(con.HENG_COMMON_D+con.YUANCHUAN_D)/2*dk))
    crWangban = __drawCrWangban(
        origin = origin,
        crEnds = CrEnds,
        crCollection = cornerRafterColl,
        root_obj = rafterRootObj,
    )
    # 裁剪，沿角梁裁剪，以免穿模
    utils.addBisect(
            object=crWangban,
            pStart=buildingObj.matrix_world @ purlin_pos[0],
            pEnd=buildingObj.matrix_world @ purlin_pos[1],
            pCut=buildingObj.matrix_world @ purlin_pos[0] - \
                Vector((con.JIAOLIANG_Y*dk/2*math.sqrt(2),0,0)),
            clear_outer=True
    ) 
    # 相对角梁做45度对称
    utils.addModifierMirror(
        object=crWangban,
        mirrorObj=cornerBeamObj,
        use_axis=(False,True,False)
    )
    # 四面对称
    utils.addModifierMirror(
        object=crWangban,
        mirrorObj=rafterRootObj,
        use_axis=(True,True,False)
    )
    return crWangban

# 营造翼角大连檐实体（连接翘飞椽）
def __buildCornerFlyrafterEave(buildingObj:bpy.types.Object):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    # 屋顶根节点
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    # 前后檐椽
    yanRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_FB)
    # 老角梁
    cornerBeamObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_CORNER_BEAM)
    # 大连檐
    dlyObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_DLY_FB)
    # 子角梁(cbc: corner beam child)
    cbcObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_CORNER_BEAM_CHILD)
    
    # 绘制大连檐
    # 1.大连檐起点：对接正身大连檐
    pStart = Vector((
        utils.getMeshDims(dlyObj).x / 2,    # 大连檐右端顶点，长度/2
        dlyObj.location.y,
        dlyObj.location.z
    ))

    # 2.大连檐终点
    # 完全采用理论值计算，与子角梁解耦
    # 上檐出（檐椽平出+飞椽平出）
    ex = con.YANCHUAN_EX*dk + con.FLYRAFTER_EX*dk
    # 斗栱平出
    if bData.use_dg:
        ex += bData.dg_extend
    # 冲出
    ex += bData.chong * con.YUANCHUAN_D * dk
    # # 避让角梁，向内1/4角梁，见汤崇平书籍的p196
    # shift = - con.JIAOLIANG_Y/4*dk * math.sqrt(2)
    pEnd_x = bData.x_total/2 + ex
    pEnd_y = bData.y_total/2 + ex
    qiqiao = bData.qiqiao * con.YUANCHUAN_D * dk
    pEnd_z = dlyObj.location.z + qiqiao
    pEnd = Vector((pEnd_x,pEnd_y,pEnd_z))
    # 微调曲线
    shift = Vector((
        con.JIAOLIANG_H*dk/2,   # 横向延伸，以便做45度相交裁剪
        -0.5*dk,   # 防止与仔角梁头穿模
        0.5*dk,   # 防止与翘飞椽穿模
    ))
    pEnd += shift

    # 4.绘制大连檐对象
    CurvePoints = utils.setEaveCurvePoint(pStart,pEnd)
    # 与正身大连檐的旋转角度相同
    CurveTilt = dlyObj.rotation_euler.x - math.radians(90)
    flyrafterEaveObj = utils.addBezierByPoints(
                        CurvePoints=CurvePoints,
                        tilt=CurveTilt,
                        name='大连檐',
                        root_obj=rafterRootObj,
                        height = con.DALIANYAN_H*dk,
                        width = con.DALIANYAN_Y*dk
                    )
    # Curve转为mesh
    utils.applyAllModifer(flyrafterEaveObj)
    # 设置UV
    mat.UvUnwrap(flyrafterEaveObj,type='cube')
    
    # 相对角梁做45度对称
    utils.addModifierMirror(
        object=flyrafterEaveObj,
        mirrorObj=cornerBeamObj,
        use_axis=(False,True,False),
        use_bisect=(False,True,False)
    )
    # 四面对称
    utils.addModifierMirror(
        object=flyrafterEaveObj,
        mirrorObj=rafterRootObj,
        use_axis=(True,True,False),
    )
    # 设置材质
    mat.setMat(flyrafterEaveObj,
        aData.mat_red)

# 营造翘飞椽定位线
def __buildCornerFlyrafterCurve(buildingObj:bpy.types.Object):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    # 屋顶根节点
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    
    # 1.曲线起点：对齐最后一根正身飞椽的椽头
    flyrafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_FLYRAFTER_FB)
    flyrafterHeader_co = utils.getObjectHeadPoint(flyrafterObj,
            eval=True,
            )
    pStart = flyrafterHeader_co
    
    # 2.曲线终点     
    # 不依赖角梁，避免难以补偿的累计误差
    # 上檐出（檐椽平出+飞椽平出）
    ex = con.YANCHUAN_EX*dk + con.FLYRAFTER_EX*dk
    # 斗栱平出
    if bData.use_dg:
        ex += bData.dg_extend
    # 冲出，直接按用户输入的最终冲出总量计算
    ex += bData.chong * con.YUANCHUAN_D * dk
    # 避让角梁，向内1/4角梁，见汤崇平书籍的p196
    shift = con.JIAOLIANG_Y/4*dk * math.sqrt(2)
    pEnd_x = bData.x_total/2 + ex - shift
    pEnd_y = bData.y_total/2 + ex
    qiqiao = bData.qiqiao * con.YUANCHUAN_D * dk
    pEnd_z = flyrafterHeader_co.z + qiqiao
    pEnd = Vector((pEnd_x,pEnd_y,pEnd_z))

    # 4.绘制翘飞椽定位线
    CurvePoints = utils.setEaveCurvePoint(pStart,pEnd)
    flyrafterCurve_obj = utils.addBezierByPoints(
            CurvePoints=CurvePoints,
            name='翘飞椽定位线',
            resolution = con.CURVE_RESOLUTION,
            root_obj=rafterRootObj
        ) 
    flyrafterCurve_obj.ACA_data['aca_obj'] = True
    flyrafterCurve_obj.ACA_data['aca_type'] = con.ACA_TYPE_CORNER_FLYRAFTER_CURVE
    utils.hideObj(flyrafterCurve_obj)
    return flyrafterCurve_obj

# 绘制一根翘飞椽
# 椽头定位：基于每一根翼角椽，指向翘飞椽檐口线对应的定位点
# 椽尾楔形构造：使用bmesh逐点定位、绘制
# 特殊处理：椽头撇度处理、椽腰扭度处理
def __drawCornerFlyrafter(
        cornerRafterObj:bpy.types.Object,
        cornerFlyrafterEnd,
        name,
        head_shear:Vector,
        mid_shear:Vector,
        root_obj):
    # 载入数据
    buildingObj = utils.getAcaParent(cornerRafterObj,con.ACA_TYPE_BUILDING)
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK

    # 1、定位翘飞椽起点（腰点），在翼角椽头上移半椽+望板
    # 获取翼角椽的椽头坐标
    cr_head_co = utils.getObjectHeadPoint(cornerRafterObj,
            eval=False,
            is_symmetry=(True,True,False))
    # 移动到上皮+望板(做法与正身一致，基于水平投影的垂直移动)
    offset_z = (con.YUANCHUAN_D/2+con.WANGBAN_H)*dk
    offset_z = offset_z / math.cos(cornerRafterObj.rotation_euler.y)
    origin_point = cr_head_co + Vector((0,0,offset_z))

    # 2、任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add(
        location=origin_point
    )
    cfrObj = bpy.context.object
    cfrObj.name = name
    cfrObj.parent = root_obj    
    # 翘飞椽与翼角椽对齐旋转角度
    cfrObj.rotation_euler = cornerRafterObj.rotation_euler
    utils.updateScene() # 需要刷新，才能正确获取到该对象的matrix_local

    # 3、创建bmesh
    bm = bmesh.new()
    # 各个点的集合
    vectors = []

    # 1.在翘飞椽腰的下沿
    cfrMid_down = Vector((0,0,0))
    v1 = cfrMid_down    # （0,0,0）
    vectors.append(v1)

    # 2.翘飞椽尾的下皮点
    # 2.1 翘飞椽尾的中心，从“翘飞椽定位线”坐标系转换到“翘飞椽”坐标系
    cfrEnd_center = cfrObj.matrix_local.inverted() @ cornerFlyrafterEnd
    # 2.2 翘飞椽头角度, 从定位线上的翼角椽头点start_point，到腰线向上半椽中点
    cfrMid_center = Vector((0,0,con.FLYRAFTER_H/2*dk))
    cfr_head_vector:Vector = cfrEnd_center - cfrMid_center
    cfr_head_rotation = utils.alignToVector(cfr_head_vector)
    # 2.3 翘飞椽头补偿
    # 默认辅助线穿过椽头的中心 
    # 为了让檐口线落在椽头的最短边，椽头随曲线角度调整
    # 计算翘飞椽头与檐口线的夹角
    shear_rot = utils.alignToVector(head_shear) # 檐口线夹角
    tilt_rot = cfrObj.rotation_euler.z - shear_rot.z 
    tilt_offset = (con.FLYRAFTER_H/2*dk+con.QUETAI*dk) / math.tan(tilt_rot)
    # 2.4 计算椽尾下皮点
    offset = Vector((
        tilt_offset,  # 椽头沿檐口线的补偿
        0,-con.FLYRAFTER_H*0.5*dk # 下移半椽
        ))
    offset.rotate(cfr_head_rotation)
    v2 = cfrEnd_center + offset
    vectors.append(v2)
    
    # 3.到翘飞椽头上皮，上移一椽径
    offset = Vector((0,0,con.FLYRAFTER_H*dk))
    offset.rotate(cfr_head_rotation)
    v3 = v2 + offset
    vectors.append(v3)

    # 4.到翘飞椽腰点上皮，上移一椽径，注意坐标系已经旋转到檐椽角度
    v4 = Vector((0,0,con.FLYRAFTER_H*dk))
    vectors.append(v4)

    # 5.到翘飞椽尾，采用与正身飞椽相同的椽尾长度，以简化计算
    # 并没有按照实际翘飞椽头长度的2.5倍计算
    # 飞尾平出：7斗口*2.5=17.5斗口
    cfr_pingchu = con.FLYRAFTER_EX/con.FLYRAFTER_HEAD_TILE_RATIO*dk
    # 飞尾长斜边的长度，平出转到檐椽角度
    cfrEnd_length = cfr_pingchu / math.cos(cornerRafterObj.rotation_euler.y) 

    v5 = Vector((-cfrEnd_length,0,0))
    vectors.append(v5) 

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
    flyrafterEnd_face =bm.faces.new((vertices[0],vertices[3],vertices[4])) # 飞尾
    flyrafterHead_face = bm.faces.new((vertices[0],vertices[1],vertices[2],vertices[3])) # 飞头

    # 挤出厚度
    return_geo = bmesh.ops.extrude_face_region(bm, geom=[flyrafterEnd_face,flyrafterHead_face])
    verts = [elem for elem in return_geo['geom'] if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, verts=verts, vec=(0, -con.FLYRAFTER_H*dk, 0))
    # 移动所有点，居中
    for v in bm.verts:
        v.co.y += con.FLYRAFTER_H*dk/2

    # 椽头撇向处理
    # 翘飞椽檐口线的角度
    head_shear_rot = utils.alignToVector(head_shear) 
    # 计算椽头斜切量
    head_shear_value = con.YUANCHUAN_D*dk * math.tan(head_shear_rot.y)
    # 控制面、点位移
    bm.edges.ensure_lookup_table() # 按序号访问前，必须先ensure
    head_shear_edge = bm.edges[10] # 椽头左侧线
    for v in head_shear_edge.verts:
        v.co.z -= head_shear_value
    head_shear_edge = bm.edges[1] # 椽头右侧线
    for v in head_shear_edge.verts:
        v.co.z += head_shear_value
    
    # 椽腰撇向处理
    # 翼角椽檐口线的角度
    mid_shear_rot = utils.alignToVector(mid_shear) 
    # 计算椽腰斜切量
    mid_shear_value = con.YUANCHUAN_D*dk * math.tan(mid_shear_rot.y)
    # 控制面、点位移
    bm.edges.ensure_lookup_table() # 按序号访问前，必须先ensure
    mid_shear_edge = bm.edges[6] # 椽腰左侧线
    for v in mid_shear_edge.verts:
        v.co.z -= mid_shear_value

    # 椽腰扭向处理
    # 先简单的根据翘飞椽的Z角度，
    tilt_rot = cfrObj.rotation_euler.z - shear_rot.z 
    # 计算扭向位移
    tilt_offset_x = con.YUANCHUAN_D*dk / math.tan(tilt_rot)
    tilt_offset_z = tilt_offset_x * math.sin(cfrObj.rotation_euler.y)
    # 控制侧边9号线位移
    bm.edges.ensure_lookup_table() # 按序号访问前，必须先ensure
    tilt_edge = bm.edges[5] # 椽腰右侧边
    for v in tilt_edge.verts:
        v.co.x -= tilt_offset_x
        v.co.z -= tilt_offset_z

    bm.to_mesh(cfrObj.data)
    cfrObj.data.update()
    bm.free()

    # 把原点放在椽尾，方便后续计算椽头坐标
    utils.setOrigin(cfrObj,v5)

    # 处理UV
    mat.UvUnwrap(cfrObj,type='cube')

    # 以下有bug，导致翘飞椽有异常位移，后续找机会修正
    # 重设旋转数据：把旋转角度与翘飞椽头对齐，方便计算翘飞椽望板
    # change_rot = cfr_head_vector
    # utils.changeOriginRotation(change_rot,cfrObj)
    return cfrObj

# 绘制一根翘飞椽
# 椽头定位：基于每一根翼角椽，指向翘飞椽檐口线对应的定位点
# 椽尾楔形构造：使用bmesh逐点定位、绘制
# 特殊处理：椽头撇度处理、椽腰扭度处理
def __drawCornerFlyrafterNew(
        cornerRafterObj:bpy.types.Object,
        cornerFlyrafterEnd,
        name,
        head_shear:Vector,
        root_obj,
        head_shear_base:Vector = None):
    # 载入数据
    buildingObj = utils.getAcaParent(cornerRafterObj,con.ACA_TYPE_BUILDING)
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK

    # 1、定位翘飞椽起点（腰点），在翼角椽头上移半椽+望板
    # 获取翼角椽的椽头坐标
    cr_head_co = utils.getObjectHeadPoint(cornerRafterObj,
            eval=False,
            is_symmetry=(True,True,False))
    # 移动到上皮+望板(做法与正身一致，基于水平投影的垂直移动)
    offset_z = (con.YUANCHUAN_D/2+con.WANGBAN_H)*dk
    #250207 改为基于檐椽角度的平行移动
    # offset_z = offset_z / math.cos(cornerRafterObj.rotation_euler.y)
    # origin_point = cr_head_co + Vector((0,0,offset_z))
    offset = Vector((0,0,offset_z))
    offset.rotate(cornerRafterObj.rotation_euler)
    origin_point = cr_head_co + offset

    # 2、任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add(
        # 以椽腰为原点，便于计算
        location=origin_point
    )
    cfrObj = bpy.context.object
    cfrObj.name = name
    cfrObj.parent = root_obj    
    # 翘飞椽与翼角椽对齐旋转角度，便于后续在翼角椽的矩阵空间计算
    cfrObj.rotation_euler = cornerRafterObj.rotation_euler
    utils.updateScene() # 需要刷新，才能正确获取到该对象的matrix_local

    # 3、创建bmesh
    bm = bmesh.new()
    # 各个点的集合
    vectors = []

    # P1.翘飞椽腰下沿，即以上计算的原点
    v1 = Vector((0,0,0))
    vectors.append(v1)

    # P2.翘飞椽尾的下皮点
    # 2.1 函数输入了翘飞椽尾的中心点
    # 将“翘飞椽定位线”坐标系转换到“翘飞椽”坐标系
    cfrEnd_center = cfrObj.matrix_local.inverted() @ cornerFlyrafterEnd
    # 2.2 计算翘飞椽头仰角
    # 从翼角椽头中心点，到腰线中心点（椽腰抬升半椽）
    cfrMid_center = Vector((0,0,con.FLYRAFTER_H/2*dk))
    cfrMid_center.rotate(cfrObj.rotation_euler) # 取斜
    cfr_head_vector:Vector = cfrEnd_center - cfrMid_center
    cfr_head_rotation = utils.alignToVector(cfr_head_vector)
    # 2.3 翘飞椽头延长，保证椽头完全超出大连檐
    # 按照汤的做法，每一根翘飞椽头的最短边与大连檐保持出雀台
    # 所以这里将翘飞椽头的中心点，沿着翘飞椽椽头延长半椽
    # （传入的辅助点已考虑雀台）
    # 计算翘飞椽头与檐口线的夹角
    shear_rot = utils.alignToVector(head_shear) # 檐口线夹角
    # 翘飞椽头的角度为翼角椽减去檐口线冲出的斜角
    tilt_rot = cfrObj.rotation_euler.z - shear_rot.z 
    tilt_offset = con.FLYRAFTER_H/2*dk/ math.tan(tilt_rot)
    # 2.4 向外延长，并且下移半椽
    offset = Vector((tilt_offset,0,-con.FLYRAFTER_H*dk/2)) # 下移半椽
    offset.rotate(cfr_head_rotation)
    v2 = cfrEnd_center + offset
    vectors.append(v2)
    
    # 3.到翘飞椽头上皮，上移一椽径
    offset = Vector((0,0,con.FLYRAFTER_H*dk))
    offset.rotate(cfr_head_rotation)
    v3 = v2 + offset
    vectors.append(v3)

    # 4.到翘飞椽腰点上皮，上移一椽径
    # 注意坐标系已经旋转到檐椽角度，无需再做旋转
    v4 = Vector((0,0,con.FLYRAFTER_H*dk))
    vectors.append(v4)

    # 5.到翘飞椽尾，采用与正身飞椽相同的椽尾长度，以简化计算
    # 并没有按照实际翘飞椽头长度的2.5倍计算
    # 飞尾平出：7斗口*2.5=17.5斗口
    cfr_pingchu = con.FLYRAFTER_EX/con.FLYRAFTER_HEAD_TILE_RATIO*dk
    # 飞尾长斜边的长度，平出转到檐椽角度
    cfrEnd_length = cfr_pingchu / math.cos(cornerRafterObj.rotation_euler.y) 
    v5 = Vector((-cfrEnd_length,0,0))
    vectors.append(v5) 

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
    flyrafterEnd_face =bm.faces.new((vertices[0],vertices[3],vertices[4])) # 飞尾
    flyrafterHead_face = bm.faces.new((vertices[0],vertices[1],vertices[2],vertices[3])) # 飞头

    # 挤出厚度
    return_geo = bmesh.ops.extrude_face_region(bm, geom=[flyrafterEnd_face,flyrafterHead_face])
    verts = [elem for elem in return_geo['geom'] if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, verts=verts, vec=(0, -con.FLYRAFTER_H*dk, 0))
    # 移动所有点，居中
    for v in bm.verts:
        v.co.y += con.FLYRAFTER_H*dk/2

    # 椽腰扭向处理
    # 先简单的根据翘飞椽的Z角度，
    tilt_rot = cfrObj.rotation_euler.z - shear_rot.z 
    # 计算扭向位移
    tilt_offset_x = con.YUANCHUAN_D*dk / math.tan(tilt_rot)
    tilt_offset_z = tilt_offset_x * math.sin(cfrObj.rotation_euler.y)
    # 控制侧边9号线位移
    bm.edges.ensure_lookup_table() # 按序号访问前，必须先ensure
    tilt_edge = bm.edges[5] # 椽腰左侧边
    for v in tilt_edge.verts:
        v.co.x -= tilt_offset_x/2
        v.co.z -= tilt_offset_z/2
    tilt_edge = bm.edges[6] # 椽腰左侧边
    for v in tilt_edge.verts:
        v.co.x += tilt_offset_x/2
        v.co.z += tilt_offset_z/2

    # 椽头撇向处理
    # 计算撇向量：用当前斜率-初始斜率，仅计算Z轴偏移
    Z_vec = Vector((0,0,1))
    header_adj = (head_shear-head_shear_base)*Z_vec
    # 转换到翘飞椽的Y旋转轴
    euler = cfrObj.rotation_euler
    inverted_euler = Euler((0, -euler.y, 0), euler.order)
    header_adj.rotate(inverted_euler)
    # 点位移
    bm.edges.ensure_lookup_table() # 按序号访问前，必须先ensure
    # 因为大连檐为了在四角相交做了延长，导致与翘飞椽头曲线有差异
    # 所以这里只做了一侧下移，以弥补这个误差，实际其实还是有误差的
    # head_shear_edge = bm.edges[10] # 椽头左侧线
    # for v in head_shear_edge.verts:
    #     v.co += header_adj/2
    head_shear_edge = bm.edges[1] # 椽头左侧线
    for v in head_shear_edge.verts:
        v.co -= header_adj

    bm.to_mesh(cfrObj.data)
    cfrObj.data.update()
    bm.free()

    # 把原点放在椽尾，方便后续计算椽头坐标
    utils.setOrigin(cfrObj,v5)

    # 处理UV
    mat.UvUnwrap(cfrObj,type='cube')

    return cfrObj

# 营造翼角翘飞椽（Corner Flyrafter,缩写CFR）
def __buildCornerFlyrafter(
        buildingObj:bpy.types.Object,
        cornerRafterColl):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    # 屋顶根节点
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    # 翼角椽的椽尾坐标集合
    crCount = len(cornerRafterColl)
    # 绘制翘飞椽定位线
    cfrCurve = __buildCornerFlyrafterCurve(buildingObj)
    # 翘飞椽的椽尾坐标集合
    cfrEnds = utils.getBezierSegment(cfrCurve,crCount)

    # 摆放翘飞椽
    # 收集翘飞椽对象，输出绘制翘飞椽望板
    cfrCollection = []
    head_shear_base = Vector((0,0,0))
    for n in range(len(cfrEnds)):
        # 计算相邻椽头间的撇向
        if n == 0:
            head_shear_direction = Vector((0,0,0))
        else:
            head_shear_direction = cfrEnds[n] - cfrEnds[n-1] 
        # 始终取0-1两根翘飞椽的夹角为基础，为后续椽头撇向做基准
        if n == 1:
            head_shear_base = head_shear_direction
        
        cfr_Obj = __drawCornerFlyrafterNew(
            cornerRafterObj = cornerRafterColl[n], # 对应的翼角椽对象
            cornerFlyrafterEnd = cfrEnds[n], # 头在翘飞椽定位线上
            head_shear = head_shear_direction, # 椽头撇向
            head_shear_base=head_shear_base,    
            name='翘飞椽',
            root_obj=rafterRootObj
        )
        cfrCollection.append(cfr_Obj)

    return cfrCollection

# 绘制翘飞椽望板
# 连接各个翘飞椽尾，到翘飞椽头
def __drawCfrWangban(
        origin_point,
        cfrEnds,
        cfrCollection,
        root_obj,
        name = '翘飞椽望板'):
    # 载入数据
    buildingObj = utils.getAcaParent(root_obj,con.ACA_TYPE_BUILDING)
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK

    # 任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add(
        location=origin_point
    )
    cfrWangbanObj = bpy.context.object
    cfrWangbanObj.name = name
    cfrWangbanObj.parent = root_obj

    # 创建bmesh
    bm = bmesh.new()
    # 各个点的集合
    vectors = []

    # 插入望板前侧的檐口线点
    # 不从翘飞椽本身取椽头坐标，因为已经根据檐口线做了角度补偿，会导致望板穿模
    # 所以还是从檐口线上取
    # 计算从檐口线上移的距离，统一按正身檐椽计算，没有取每一根翼角椽计算，不然太复杂了
    flyrafterObj:bpy.types.Object = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_FLYRAFTER_FB)
    offset = con.FLYRAFTER_H/2*dk / math.cos(flyrafterObj.rotation_euler.y)
    # 循环插入翘飞椽尾坐标
    for n in range(len(cfrEnds)):
        # 翘飞椽头坐标, 插入队列头
        cfrEnd_loc = cfrWangbanObj.matrix_world.inverted() @ cfrEnds[n]
        # 基于每根翘飞椽（椽头角度）进行位移
        # 翘飞椽数组比檐口点数组少两个，只能特殊处理一下
        if n == 0:
            m = 0
        elif n == len(cfrEnds) -1 :
            m = n-2
        else:
            m = n-1
        cfrObj:bpy.types.Object = cfrCollection[m]
        # 偏移量，垂直半飞椽+半望板，水平1雀台+1里口木
        offset = Vector((
            -con.QUETAI*dk-con.DALIANYAN_Y*dk,0,
            con.FLYRAFTER_H/2*dk))
        offset.rotate(cfrObj.rotation_euler)
        cfrEnd_loc += offset
        if n == 0:
            # 矫正起点，檐口线起点在最后一根正身椽头，调整到金交点
            cfrEnd_loc.x = 0
        vectors.insert(0,cfrEnd_loc)
    # 循环插入翘飞椽头坐标
    for n in range(len(cfrCollection)):
        # 翘飞椽头坐标,插入队列尾
        cfrObj:bpy.types.Object = cfrCollection[n]
        cfrHead_loc = cfrWangbanObj.matrix_world.inverted() @ cfrObj.location
        # 上移半望板高度        
        offset = Vector((0,0,con.WANGBAN_H/2*dk))
        offset.rotate(cfrObj.rotation_euler)
        cfrHead_loc += offset
        # 在第一根椽之前，手工添加金交点一侧的后点
        if n==0:
            vectors.append((
                0,cfrHead_loc.y,cfrHead_loc.z
            ))
        # 循环依次添加椽头
        vectors.append(cfrHead_loc)
        # 在最后一根椽后，再手工追加角梁侧的后点
        if n==len(cfrCollection)-1:
            vectors.append(cfrHead_loc)

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
    return_geo = bmesh.ops.extrude_face_region(bm, geom=bm.faces)
    verts = [elem for elem in return_geo['geom'] if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0,con.WANGBAN_H*dk))
    #ps，这个挤出略有遗憾，没有按照每个面的normal进行extrude

    # 确保face normal朝向
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(cfrWangbanObj.data)
    cfrWangbanObj.data.update()
    bm.free()

    # 处理UV
    mat.UvUnwrap(cfrWangbanObj,type='cube')

    return cfrWangbanObj

# 营造翘飞椽望板
def __buildCfrWangban(
        buildingObj:bpy.types.Object,
        purlin_pos,
        cfrCollection
        ):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    # 屋顶根节点
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    # 老角梁
    cornerBeamObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_CORNER_BEAM)
    # 翘飞椽檐口定位线
    cfrCurve = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_CORNER_FLYRAFTER_CURVE)
    # 翘飞椽根数
    cr_count = len(cfrCollection)
    # 获取翘飞椽头坐标集合
    cfrEnds = utils.getBezierSegment(
        cfrCurve,cr_count,withCurveEnd=True)
    
    # 绘制翘飞椽望板
    cfrWangban = __drawCfrWangban(
        origin_point = purlin_pos[1],#金桁交点
        cfrEnds = cfrEnds,
        cfrCollection = cfrCollection,
        root_obj = rafterRootObj,
        name = '翘飞椽望板'
    )
    # 裁剪，沿角梁裁剪，以免穿模
    utils.addBisect(
            object=cfrWangban,
            pStart=buildingObj.matrix_world @ purlin_pos[0],
            pEnd=buildingObj.matrix_world @ purlin_pos[1],
            pCut=buildingObj.matrix_world @ purlin_pos[0] - \
                Vector((con.JIAOLIANG_Y*dk/2*math.sqrt(2),0,0)),
            clear_outer=True
    ) 
    # 相对角梁做45度对称
    utils.addModifierMirror(
        object=cfrWangban,
        mirrorObj=cornerBeamObj,
        use_axis=(False,True,False)
    )
    # 四面对称
    utils.addModifierMirror(
        object=cfrWangban,
        mirrorObj=rafterRootObj,
        use_axis=(True,True,False)
    )
    return cfrWangban

# 营造椽架（包括檐椽、飞椽、望板等）
# 根据屋顶样式，自动判断
def __buildRafterForAll(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    roofStyle = bData.roof_style
    useFlyrafter = bData.use_flyrafter
    useWangban = bData.use_wangban
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)

    # 收集待合并的望板
    wangbanObjs = []

    # 各种屋顶都有前后檐
    fbRafterObj = __buildRafter_FB(buildingObj,purlin_pos)    # 前后檐椽
    
    if useFlyrafter:  # 用户可选择不使用飞椽
        # 这里生成的是飞椽，但返回的是压飞望板
        wangbanF_FB = __buildFlyrafterAll(
            buildingObj,purlin_pos,'X') # 前后飞椽
        wangbanObjs.append(wangbanF_FB)
        
    if useWangban:  # 用户可选择暂时不生成望板（更便于观察椽架形态）
        wangbanFB = __buildWangban_FB(buildingObj,purlin_pos)   # 前后望板
        wangbanObjs.append(wangbanFB)
    
    # 庑殿、歇山的处理（硬山、悬山不涉及）
    if roofStyle in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
            con.ROOF_LUDING):
        # 营造角梁
        __buildCornerBeam(buildingObj,purlin_pos)
        
        # 两山檐椽
        __buildRafter_LR(buildingObj,purlin_pos)    
        
        if useFlyrafter:
            # 两山飞椽
            wangbanF_LR = __buildFlyrafterAll(buildingObj,purlin_pos,'Y') 
            wangbanObjs.append(wangbanF_LR)
            
        if useWangban:
            # 两山望板
            wangbanLR = __buildWangban_LR(buildingObj,purlin_pos)  
            wangbanObjs.append(wangbanLR) 
            
        # 翼角部分
        # 营造小连檐
        __buildCornerRafterEave(buildingObj)
        
        # 营造翼角椽
        cornerRafterColl = __buildCornerRafter(buildingObj,purlin_pos)
        
        if useWangban:
            # 翼角椽望板
            wangbanCR = __buildCrWangban(buildingObj,purlin_pos,cornerRafterColl)
            wangbanObjs.append(wangbanCR) 

        # 是否做二层飞椽
        # 找到角梁，做为翘飞椽和翼角椽45度镜像的依据
        cornerBeamObj = utils.getAcaChild(
            buildingObj,con.ACA_TYPE_CORNER_BEAM)
        if useFlyrafter:
            # 大连檐
            __buildCornerFlyrafterEave(buildingObj)
            
            # 翘飞椽，以翼角椽为基准
            cfrCollection = __buildCornerFlyrafter(buildingObj,cornerRafterColl)
            
            if useWangban:
                # 翘飞椽望板
                wangbanCFR = __buildCfrWangban(buildingObj,purlin_pos,cfrCollection)
                wangbanObjs.append(wangbanCFR) 

            # 合并翘飞椽
            cfrSet = utils.joinObjects(
                cfrCollection,newName='翘飞椽')
            # 绑定材质
            cfrSet = mat.setMat(
                cfrSet,aData.mat_paint_flyrafter,override=True)
            # 倒角
            utils.addModifierBevel(
                object=cfrSet,
                width=con.BEVEL_EXLOW,
                segments=2
            )
            # 角梁45度对称
            utils.addModifierMirror(
                object=cfrSet,
                mirrorObj=cornerBeamObj,
                use_axis=(False,True,False)
            )
            # 四向对称
            utils.addModifierMirror(
                object=cfrSet,
                mirrorObj=rafterRootObj,
                use_axis=(True,True,False)
            )

        # 合并翼角椽
        crSet = utils.joinObjects(
            cornerRafterColl,newName='翼角椽')
        # 绑定材质
        crSet = mat.setMat(crSet,aData.mat_paint_rafter,override=True)
        # 倒角
        utils.addModifierBevel(
            object=crSet,
            width=con.BEVEL_EXLOW,
            segments=2
        )
        # 角梁45度对称
        utils.addModifierMirror(
            object=crSet,
            mirrorObj=cornerBeamObj,
            use_axis=(False,True,False)
        )
        # 四向对称
        utils.addModifierMirror(
            object=crSet,
            mirrorObj=rafterRootObj,
            use_axis=(True,True,False)
        )

        # 平滑
        utils.shaderSmooth(crSet)

    # 以下为各类屋顶类型通用的处理  
    # 合并望板
    if useWangban:
        wangbanSet = utils.joinObjects(
            wangbanObjs,newName='望板')
        # 设置材质
        mat.setMat(wangbanSet,
                aData.mat_paint_wangban)
    
    # 檐椽事后处理(处理UV,添加倒角)
    # 只能放在最后加倒角，因为计算翼角椽时有取檐椽头坐标
    # 加了倒角后，取檐椽头坐标时就出错了
    yanRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_FB)
    # 材质设置
    yanRafterObj = mat.setMat(
        yanRafterObj,aData.mat_paint_rafter,override=True)
    # 倒角
    utils.addModifierBevel(
        object=yanRafterObj,
        width=con.BEVEL_EXLOW,
        segments=2
    )
    # 镜像
    utils.addModifierMirror(
            object=yanRafterObj,
            mirrorObj=rafterRootObj,
            use_axis=(True,True,False)
        )
    
    # 两山檐椽
    yanRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_LR)
    if yanRafterObj != None:
        # 材质设置
        yanRafterObj = mat.setMat(
            yanRafterObj,aData.mat_paint_rafter,override=True)
        # 倒角
        utils.addModifierBevel(
            object=yanRafterObj,
            width=con.BEVEL_EXLOW,
            segments=2
        )
        # 镜像
        utils.addModifierMirror(
            object=yanRafterObj,
            mirrorObj=rafterRootObj,
            use_axis=(True,True,False)
        )

    # 前后檐飞椽
    flyRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_FLYRAFTER_FB)
    if flyRafterObj != None:
        # 设置材质
        flyRafterObj = mat.setMat(
            flyRafterObj,aData.mat_paint_flyrafter,override=True)
        # 倒角
        utils.addModifierBevel(
            object=flyRafterObj,
            width=con.BEVEL_EXLOW,
            segments=2
        )
        # 镜像
        utils.addModifierMirror(
            object=flyRafterObj,
            mirrorObj=rafterRootObj,
            use_axis=(True,True,False)
        )

    # 两山飞椽
    flyRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_FLYRAFTER_LR)
    if flyRafterObj != None:
        # 设置材质
        flyRafterObj = mat.setMat(
            flyRafterObj,aData.mat_paint_flyrafter,override=True)
        # 倒角
        utils.addModifierBevel(
            object=flyRafterObj,
            width=con.BEVEL_EXLOW,
            segments=2
        )
        # 镜像
        utils.addModifierMirror(
            object=flyRafterObj,
            mirrorObj=rafterRootObj,
            use_axis=(True,True,False)
        )

    return

# 营造山花板
def __buildShanhuaBan(buildingObj: bpy.types.Object,
                 purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)

    # 绘制象眼板上沿曲线
    shbVerts = []

    for n in range(len(purlin_pos)):
        # 向下位移，要与博缝板的做法一致，
        offsetZ = (con.HENG_COMMON_D*dk/2
                +con.BOFENG_OFFSET_XS*dk
                -0.5*dk # 略作重叠，避免破口
                )
        offset = Vector((0,0,-offsetZ))
        # 位移向量按各段椽架的斜率旋转
        if n != 0:
            purlinAngle = math.atan(
                    (purlin_pos[n].z-purlin_pos[n-1].z)
                    /(purlin_pos[n-1].y-purlin_pos[n].y)
                )
            purlinEular = Euler((-purlinAngle,0,0),'XYZ')
            offset.rotate(purlinEular)
        point:Vector = purlin_pos[n]+offset
        # X坐标放到山花板位置
        point.x = (purlin_pos[-1].x       # 桁檩定位点
                    - con.XYB_WIDTH*dk/2   # 移到外皮位置
                    + 0.01)                # 防止与檩头交叠
        # 顶部点的Y坐标可能小于0，做纵向补偿
        if point.y <0: 
            point.z -= abs(point.y)*0.9 # 按最后一步架举架0.9计算
            point.y=0
        # 分别插入两侧的点
        shbVerts.insert(0,point*Vector((1,-1,1)))
        shbVerts.append(point)
    
    # 创建象眼板实体
    # 任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add(
        location=(0,0,0)
    )
    shbObj = bpy.context.object
    shbObj.name = '山花板'
    shbObj.data.name = '山花板'
    shbObj.parent = rafterRootObj

    # 创建bmesh
    bm = bmesh.new()
    # 摆放点
    vertices=[]
    for n in range(len(shbVerts)):
        if n==0:
            vert = bm.verts.new(shbVerts[n])
        else:
            # 挤出
            return_geo = bmesh.ops.extrude_vert_indiv(bm, verts=[vert])
            vertex_new = return_geo['verts'][0]
            del return_geo
            # 给挤出的点赋值
            vertex_new.co = shbVerts[n]
            # 交换vertex给下一次循环
            vert = vertex_new
        vertices.append(vert)
    
    # 创建面
    for n in range(len(vertices)//2-1): #注意‘/’可能是float除,用'//'进行整除
        bm.faces.new((
            vertices[n],vertices[n+1], 
            vertices[-n-2],vertices[-n-1] 
        ))

    # 挤出山花板厚度
    offset=Vector((con.XYB_WIDTH*dk, 0,0))
    return_geo = bmesh.ops.extrude_face_region(bm, geom=bm.faces)
    verts = [elem for elem in return_geo['geom'] if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, verts=verts, vec=offset)
    for v in bm.verts:
        # 移动所有点，居中
        v.co.x -= con.XYB_WIDTH*dk/2

    # 确保face normal朝向
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(shbObj.data)
    shbObj.data.update()
    bm.free()

    # 山花板板做到椽架
    # 从正心桁做收山加斜，再上移半桁+1椽
    cutPoint = purlin_pos[0] + Vector((
        0,0,
        ( bData.shoushan/2          # 收山加斜
         + con.XYB_WIDTH*dk/2       # 山花厚度加斜
         + con.WANGBAN_H*dk         # 望板
         + con.HENG_COMMON_D*dk/2   # 半桁径
         + con.YUANCHUAN_D*dk       # 椽径
        )
    ))
    utils.addBisect(
        object=shbObj,
        pCut=rafterRootObj.matrix_world @ cutPoint,
        clear_outer=True,
        direction='V'
    )
    # 将origin放在山花板下檐，方便后续贴图时的计算
    utils.setOrigin(shbObj,cutPoint*Vector((1,0,1)))

    # 应用镜像
    utils.addModifierMirror(
        object=shbObj,
        mirrorObj=rafterRootObj,
        use_axis=(True,False,False)
    )

    # 应用材质
    mat.setMat(shbObj,aData.mat_paint_shanhua)

    return shbObj

# 营造象眼板，仅适用于悬山（和悬山卷棚）
def __buildXiangyanBan(buildingObj: bpy.types.Object,
                 purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    # 绘制象眼板上沿曲线
    xybVerts = []
    # 悬山的象眼板在山柱中线处
    xyb_x = bData.x_total/2

    # 241119 有斗拱的悬山建筑，向下延伸象眼板，封闭缝隙
    # 有斗拱的，向下延伸：一斗栱高
    extend = 0
    if bData.use_dg:
        extend += bData.dg_height
        if bData.use_pingbanfang:
            extend += con.PINGBANFANG_H*dk
    # 没有斗栱的，延伸一个檐桁垫板高度
    else:
        extend += con.BOARD_YANHENG_H*dk
    # 做廊间举架的，向下延伸额枋/小额枋高度
    # 有斗拱的，也做这个延伸
    if bData.use_hallway or bData.use_dg:
        # 大额枋
        extend += con.EFANG_LARGE_H*dk
        if bData.use_smallfang:
            # 小额枋
            extend += con.EFANG_SMALL_H*dk
            # 由额垫板
            extend += con.BOARD_YOUE_H*dk
    point = Vector((xyb_x,
                    purlin_pos[0].y,
                    -extend))
    xybVerts.insert(0,point*Vector((1,-1,1)))
    xybVerts.append(point)

    # 综合考虑桁架上铺椽、望、灰泥后的效果，主要保证整体线条的流畅
    # 悬山从正心桁做起
    # 从举架定位点做偏移
    for n in range(len(purlin_pos)):
        # 向上位移:半桁径+椽径+望板高+灰泥层高
        point:Vector = purlin_pos[n].copy()
        point.x = xyb_x
        xybVerts.insert(0,point*Vector((1,-1,1)))
        xybVerts.append(point)
    
    # 创建象眼板实体
    # 任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add(
        location=(0,0,0)
    )
    xybObj = bpy.context.object
    xybObj.name = '象眼板'
    xybObj.data.name = '象眼板'
    xybObj.parent = rafterRootObj

    # 创建bmesh
    bm = bmesh.new()
    # 摆放点
    vertices=[]
    for n in range(len(xybVerts)):
        if n==0:
            vert = bm.verts.new(xybVerts[n])
        else:
            # 挤出
            return_geo = bmesh.ops.extrude_vert_indiv(bm, verts=[vert])
            vertex_new = return_geo['verts'][0]
            del return_geo
            # 给挤出的点赋值
            vertex_new.co = xybVerts[n]
            # 交换vertex给下一次循环
            vert = vertex_new
        vertices.append(vert)
    
    # 创建面
    for n in range(len(vertices)//2-1): #注意‘/’可能是float除,用'//'进行整除
        bm.faces.new((
            vertices[n],vertices[n+1], 
            vertices[-n-2],vertices[-n-1] 
        ))

    # 挤出象眼板厚度
    offset=Vector((con.XYB_WIDTH*dk, 0,0))
    return_geo = bmesh.ops.extrude_face_region(bm, geom=bm.faces)
    verts = [elem for elem in return_geo['geom'] if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, verts=verts, vec=offset)
    for v in bm.verts:
        # 移动所有点，居中
        v.co.x -= con.XYB_WIDTH*dk/2

    # 确保face normal朝向
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(xybObj.data)
    xybObj.data.update()
    bm.free()

    # 处理UV
    mat.UvUnwrap(xybObj,type='cube')

    # 应用镜像
    utils.addModifierMirror(
        object=xybObj,
        mirrorObj=rafterRootObj,
        use_axis=(True,False,False)
    )

    # 应用材质
    if bData.roof_style in (
            con.ROOF_XUANSHAN,
            con.ROOF_XUANSHAN_JUANPENG):
        # 悬山用石材封堵
        mat.setMat(xybObj,
            aData.mat_stone)
    elif bData.roof_style in (con.ROOF_XIESHAN,
                              con.ROOF_XIESHAN_JUANPENG,):
        # 歇山刷红漆
        mat.setMat(xybObj,
            aData.mat_paint_shanhua,override=True)

    return xybObj

# 绘制博缝板（上沿）曲线
def __drawBofengCurve(buildingObj:bpy.types.Object,
                    purlin_pos):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    ridgeCurveVerts = []
    # 垂脊横坐标
    ridge_x = purlin_pos[-1].x
    # 硬山调整一个山墙宽度
    if bData.roof_style in (
            con.ROOF_YINGSHAN,
            con.ROOF_YINGSHAN_JUANPENG):
        ridge_x += con.SHANQIANG_WIDTH * dk - con.BEAM_DEPTH * pd/2

    # 第1点：从正身飞椽的中心当开始，上移半飞椽+大连檐
    # 如果做飞椽，以大连檐定位，否则以小连檐（里口木）定位
    if bData.use_flyrafter:
        lianyanType = con.ACA_TYPE_RAFTER_DLY_FB
    else:
        lianyanType = con.ACA_TYPE_RAFTER_LKM_FB
    # 大连檐中心
    dlyObj:bpy.types.Object = utils.getAcaChild(
        buildingObj,lianyanType)
    curve_p1 = Vector(dlyObj.location)
    # 位移到大连檐外沿
    offset = Vector((ridge_x,con.DALIANYAN_H*dk/2,0))
    offset.rotate(dlyObj.rotation_euler)
    curve_p1 += offset
    ridgeCurveVerts.append(curve_p1)

    # 综合考虑桁架上铺椽、望、灰泥后的效果，主要保证整体线条的流畅
    # 从举架定位点做偏移
    for n in range(len(purlin_pos)):
        # 向上位移:半桁径+椽径+望板高+灰泥层高
        offsetZ = (con.HENG_COMMON_D/2*dk
                 + con.YUANCHUAN_D*dk 
                 + con.WANGBAN_H*dk
                 + con.ROOFMUD_H*dk
                )
        # 为了防止与排山勾滴穿模，向下调整一个筒瓦高度
        if n > 1 :
            tileHeight = (aData.circularTile_source.dimensions.z 
                  * bData.DK 
                  / con.DEFAULT_DK)
            offsetZ -= tileHeight
        offset = Vector((0,0,offsetZ))
        # 位移向量按各段椽架的斜率旋转
        if n != 0:
            purlinAngle = math.atan(
                    (purlin_pos[n].z-purlin_pos[n-1].z)
                    /(purlin_pos[n-1].y-purlin_pos[n].y)
                )
            purlinEular = Euler((-purlinAngle,0,0),'XYZ')
            offset.rotate(purlinEular)
        point:Vector = purlin_pos[n]+offset
        point.x = ridge_x
        ridgeCurveVerts.append(point)
    
    # 卷棚顶的曲线调整,最后一点囊相调整，再加两个平滑点
    if bData.roof_style in (
            con.ROOF_XUANSHAN_JUANPENG,
            con.ROOF_YINGSHAN_JUANPENG,
            con.ROOF_XIESHAN_JUANPENG,):
        ridgeCurveVerts[-1] += Vector((0,
                con.JUANPENG_PUMP*dk,   # 卷棚的囊调整
                con.YUANCHUAN_D*dk))    # 提前抬高屋脊高度
        # Y=0时，抬升1椽径，见马炳坚p20
        p1 = Vector((ridge_x,
            0,
            purlin_pos[-1].z + con.YUANCHUAN_D*dk))
        # 向上位移:半桁径+椽径+望板高+灰泥层高
        offset = Vector(
                            (0,0,
                                (con.HENG_COMMON_D/2 
                                    + con.YUANCHUAN_D 
                                    + con.WANGBAN_H 
                                    + con.ROOFMUD_H
                                )*dk
                            )
                        )
        p1 += offset
        ridgeCurveVerts.append(p1)

    # 创建博缝板曲线
    ridgeCurve = utils.addCurveByPoints(
            CurvePoints=ridgeCurveVerts,
            name="博缝板曲线",
            root_obj=rafterRootObj,
            order_u=4, # 取4级平滑，让坡面曲线更加流畅
            )
    utils.setOrigin(ridgeCurve,ridgeCurveVerts[0])
    utils.hideObj(ridgeCurve)
    return ridgeCurve

# 营造博缝板
# def __buildBofeng(buildingObj: bpy.types.Object,
#                  rafter_pos):
#     # 载入数据
#     bData : acaData = buildingObj.ACA_data
#     dk = bData.DK
#     rafterRootObj = utils.getAcaChild(
#         buildingObj,con.ACA_TYPE_RAFTER_ROOT)

#     # 新绘制一条垂脊曲线
#     bofengObj = __drawBofengCurve(
#         buildingObj,rafter_pos)
#     bofengObj.location.x = rafter_pos[-1].x
#     bofengObj.name = '博缝板'
    
#     # 转成mesh
#     utils.focusObj(bofengObj)
#     bpy.ops.object.convert(target='MESH')

#     # 挤压成型
#     bpy.ops.object.mode_set( mode = 'EDIT' ) 
#     bm = bmesh.new()
#     bm = bmesh.from_edit_mesh( bpy.context.object.data )

#     # 曲线向下挤出博缝板高度
#     bpy.ops.mesh.select_mode( type = 'EDGE' )
#     bpy.ops.mesh.select_all( action = 'SELECT' ) 
#     height = (con.HENG_COMMON_D + con.YUANCHUAN_D*4
#                   + con.WANGBAN_H + con.ROOFMUD_H)*dk
#     bpy.ops.mesh.extrude_edges_move(
#         TRANSFORM_OT_translate={'value': (0.0, 0.0, 
#                     -height)})

#     return_geo = bmesh.ops.extrude_face_region(
#             bm, geom=bm.faces)
#     verts = [elem for elem in return_geo['geom'] 
#              if type(elem) == bmesh.types.BMVert]
#     bmesh.ops.translate(bm, 
#             verts=verts, 
#             vec=(con.BOFENG_WIDTH*dk, 0, 0))

#     # Update & Destroy Bmesh
#     bmesh.update_edit_mesh(bpy.context.object.data) 
#     bm.free()  # free and prevent further access

#     # Flip normals
#     bpy.ops.mesh.select_all( action = 'SELECT' )
#     bpy.ops.mesh.flip_normals() 

#     # Switch back to Object at end
#     bpy.ops.object.mode_set( mode = 'OBJECT' )

#     # 应用镜像
#     utils.addModifierMirror(
#         object=bofengObj,
#         mirrorObj=rafterRootObj,
#         use_axis=(True,True,False),
#         use_bisect=(False,True,False)
#     )

#     # 应用裁剪
#     return

# 营造博缝板的雪花钉
def __buildBofengNails(
        buildingObj: bpy.types.Object,
        bofengObj : bpy.types.Object,
        rafter_pos,
        ):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    # 收集对象
    nails = []
    
    # 根据槫子位置，摆放雪花钉
    for rafter in rafter_pos:
        # 定位: 与博缝板外皮相切
        loc_x = bofengObj.location.x + con.BOFENG_WIDTH*dk
        # 大小
        radius = 0.6*dk
        # 创建
        nailObj = utils.addSphere(
            name='雪花钉',
            radius=radius,
            rotation=(0,math.radians(90),0),
            location= (
                loc_x,
                rafter.y,
                rafter.z), 
            parent=rafterRootObj
        )
        nails.append(nailObj)
        # 六边形环绕
        count = 6
        span = con.HENG_TIAOYAN_D*dk/2
        for n in range(count):
            nailObjCopy = utils.copySimplyObject(nailObj)
            offset = Vector((0,span,0))
            angle = n * 360/count
            rotEuler = Euler((math.radians(angle),0,0)) 
            offset.rotate(rotEuler)
            nailObjCopy.location += offset
            nails.append(nailObjCopy)
    
    # 合并雪花钉
    nailsSet = utils.joinObjects(nails)
    return nailsSet

# 营造博缝板，依赖于外部资产，更便于调整
def __buildBofeng(buildingObj: bpy.types.Object,
                 rafter_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)

    # 新绘制一条垂脊曲线
    bofengCurve = __drawBofengCurve(
        buildingObj,rafter_pos)
    
    # 复制博缝板资产
    bofengObj = utils.copyObject(
        sourceObj=aData.bofeng_source,
        name="博缝板",
        parentObj=rafterRootObj,
        location=bofengCurve.location,
        singleUser=True
    )
    # 尺寸适配
    # 先做到桁檩下皮
    bofengHeight = (con.ROOFMUD_H*dk
              + con.WANGBAN_H*dk
              + con.HENG_COMMON_D*dk
              + con.YUANCHUAN_D*dk
              )
    # 排山勾滴的瓦高调整
    tileHeight = (aData.circularTile_source.dimensions.z 
                  * bData.DK 
                  / con.DEFAULT_DK)
    bofengHeight -= tileHeight
    # 再适当调整，没有依据，仅为我的个人喜好
    if bData.roof_style in (
        con.ROOF_XIESHAN,
        con.ROOF_XIESHAN_JUANPENG):
        # 歇山做窄一些，留出更多的山花板
        bofengHeight += con.BOFENG_OFFSET_XS*dk
    if bData.roof_style in (
        con.ROOF_YINGSHAN,
        con.ROOF_YINGSHAN_JUANPENG,
        con.ROOF_XUANSHAN,
        con.ROOF_XUANSHAN_JUANPENG,
    ):
        # 硬山、悬山做宽一些，更加美观
        bofengHeight += con.BOFENG_OFFSET_YS*dk
    bofengObj.dimensions = (
        bofengObj.dimensions.x,
        con.BOFENG_WIDTH*dk,
        bofengHeight)
    # 添加curve变形
    modCurve : bpy.types.CurveModifier = \
        bofengObj.modifiers.new('曲线拟合','CURVE')
    modCurve.object = bofengCurve

    # 根据槫子位置，摆放雪花钉
    nailsSet = __buildBofengNails(buildingObj,
                bofengObj,
                rafter_pos)
    # 博缝板刷成红色
    # mat.setMat(bofengObj,
    #     aData.mat_red,override=True)
    # 雪花钉刷成金色
    mat.setMat(nailsSet,aData.mat_gold)
    # 合并博缝板和雪花钉
    bofengObj = utils.joinObjects([bofengObj,nailsSet])

    # 应用镜像
    utils.addModifierMirror(
        object=bofengObj,
        mirrorObj=rafterRootObj,
        use_axis=(True,True,False),
        use_bisect=(False,True,False)
    )

    # 歇山的博缝板裁剪，仅做到椽架
    # 从正心桁做收山加斜，再上移半桁+1椽
    if bData.roof_style in (con.ROOF_XIESHAN,
                            con.ROOF_XIESHAN_JUANPENG,):
        cutPoint = rafter_pos[0] + Vector((
            0,0,
            ( bData.shoushan/2         # 收山加斜
            + con.WANGBAN_H*dk         # 望板
            + con.HENG_COMMON_D*dk/2   # 半桁径
            + con.YUANCHUAN_D*dk       # 椽径
            )
        ))
        utils.addBisect(
            object=bofengObj,
            pCut=rafterRootObj.matrix_world @ cutPoint,
            clear_outer=True,
            direction='V'
        )
    utils.addModifierBevel(
        object=bofengObj,
        width=con.BEVEL_LOW
    )

    # 山花板
    if bData.roof_style in (
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,):
        # 1、定位
        # 基于博缝板曲线的位移
        offset = Vector((0,
             -(con.BOFENG_WIDTH*dk + con.XYB_WIDTH*dk)/2,
             -bofengHeight))
        shanhuaLoc = bofengCurve.location+offset
        # 2、复制博缝板资产
        shanhuaObj = utils.copyObject(
            sourceObj=aData.bofeng_source,
            name="山花板",
            parentObj=rafterRootObj,
            location=shanhuaLoc,
            singleUser=True
        )
        # 3、调整尺寸，这里无法给出一个确切大小，暂时使用了一个极大的值
        # 后续做镜像的时候，会在Y轴进行合并
        # 山花拉伸高度，要保证能够在Y轴合并
        # 太小，会出现没有完全合并，太大，反而会导致上部被合并
        shanhuaHeight = bData.y_total/2 # 没有依据，只是一个差不多的值
        shanhuaObj.dimensions = (
            shanhuaObj.dimensions.x,
            con.BOFENG_WIDTH*dk,
            shanhuaHeight)
        
        
        # 4、添加curve变形
        modCurve : bpy.types.CurveModifier = \
            shanhuaObj.modifiers.new('曲线拟合','CURVE')
        modCurve.object = bofengCurve
        
        # 5、镜像
        utils.addModifierMirror(
            object=shanhuaObj,
            mirrorObj=rafterRootObj,
            use_axis=(True,True,False),
            use_bisect=(False,True,False)
        )

        # 6、裁剪，只做到山花与檐椽架的交点，以下的部分剪掉
        if bData.roof_style in (con.ROOF_XIESHAN,
                                con.ROOF_XIESHAN_JUANPENG,):
            Px = (bofengCurve.location.x
                     -(con.BOFENG_WIDTH*dk + con.XYB_WIDTH*dk)/2)
            Py = 0
            # 从正心桁做收山加斜，再上移半桁+1椽
            Pz = rafter_pos[0].z + ( bData.shoushan/2         # 收山加斜
                                + con.WANGBAN_H*dk         # 望板
                                + con.HENG_COMMON_D*dk/2   # 半桁径
                                + con.YUANCHUAN_D*dk       # 椽径
                                )
            cutPoint = Vector((Px,Py,Pz))
            utils.addBisect(
                object=shanhuaObj,
                pCut=rafterRootObj.matrix_world @ cutPoint,
                clear_outer=True,
                direction='V'
            )
        
        # 7、将几何中心放在裁切点上，做为后续做山花材质时的定位参考
        bpy.ops.object.transform_apply(
            location=True, rotation=True, scale=True)
        utils.setOrigin(shanhuaObj,cutPoint)
        
        # 8、贴山花板贴材质
        mat.setMat(shanhuaObj,aData.mat_paint_shanhua,
                   override=True)

    return bofengObj

# 营造山墙
# todo: 后续迁移到墙体的代码文件，以及Colleciton、empty下去
def __buildShanWall(
        buildingObj:bpy.types.Object,
        purlin_pos):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    ShanWallVerts = []
    # 山墙横坐标
    ridge_x = bData.x_total/2

    # 从墙根底部做起，从屋顶层反向推算
    tile_base = bData.piller_height
    # 如果有斗栱，抬高斗栱高度
    if bData.use_dg:
        tile_base += bData.dg_height
    else:
        # 以大梁抬升
        tile_base += con.BEAM_HEIGHT*pd
    # 1、山墙下脚点，向外伸出檐椽平出，做到柱脚高度
    p00: Vector = Vector((bData.x_total/2,
        bData.y_total/2 + con.SHANQIANG_EX*dk,
        -tile_base))
    ShanWallVerts.insert(0,p00*Vector((1,-1,1)))
    ShanWallVerts.append(p00)
    # 2、做出墀头造型，简单的两个斜面
    # 具体的定位是自己粗估的，没有啥依据
    p01: Vector = Vector((bData.x_total/2,
                            p00.y,
                            -13*dk))
    ShanWallVerts.insert(0,p01*Vector((1,-1,1)))
    ShanWallVerts.append(p01)
    p02: Vector = Vector((bData.x_total/2,
                            p00.y+6*dk,
                            -10*dk))
    ShanWallVerts.insert(0,p02*Vector((1,-1,1)))
    ShanWallVerts.append(p02)

    # 3、檐口点：从正身飞椽的中心当开始，上移半飞椽+大连檐
    # 大连檐中心
    dlyObj:bpy.types.Object = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_DLY_FB)
    p1 = Vector(dlyObj.location)
    # 位移到大连檐X方向的最外侧，Z方向的底边
    offset = Vector((ridge_x,-con.DALIANYAN_H*dk/2,0))
    offset.rotate(dlyObj.rotation_euler)
    p1 += offset
    ShanWallVerts.insert(0,p1*Vector((1,-1,1)))
    ShanWallVerts.append(p1)

    # 综合考虑桁架上铺椽、望、灰泥后的效果，主要保证整体线条的流畅
    # 从举架定位点做偏移
    for n in range(len(purlin_pos)):
        # 向上位移:半桁径+椽径+望板高
        offset = (con.HENG_COMMON_D/2 
                  + con.YUANCHUAN_D 
                  + con.WANGBAN_H)*dk
        point:Vector = purlin_pos[n]*Vector((0,1,1)) \
                + Vector((ridge_x,0,offset))
        ShanWallVerts.insert(0,point*Vector((1,-1,1)))
        ShanWallVerts.append(point)
    
    # 创建山墙实体
    # 任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add(
        location=(0,0,0)
    )
    shanWallObj = bpy.context.object
    shanWallObj.name = '山墙'
    shanWallObj.data.name = '山墙'
    shanWallObj.parent = rafterRootObj

    # 创建bmesh
    bm = bmesh.new()
    # 摆放点
    vertices=[]
    for n in range(len(ShanWallVerts)):
        if n==0:
            vert = bm.verts.new(ShanWallVerts[n])
        else:
            # 挤出
            return_geo = bmesh.ops.extrude_vert_indiv(bm, verts=[vert])
            vertex_new = return_geo['verts'][0]
            del return_geo
            # 给挤出的点赋值
            vertex_new.co = ShanWallVerts[n]
            # 交换vertex给下一次循环
            vert = vertex_new
        vertices.append(vert)
    
    # 创建面
    for n in range(len(vertices)//2-1): #注意‘/’可能是float除,用'//'进行整除
        bm.faces.new((
            vertices[n],vertices[n+1], 
            vertices[-n-2],vertices[-n-1] 
        ))

    # 挤出山墙厚度
    offset=Vector((con.SHANQIANG_WIDTH*dk, 0,0))
    return_geo = bmesh.ops.extrude_face_region(bm, geom=bm.faces)
    verts = [elem for elem in return_geo['geom'] if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, verts=verts, vec=offset)

    # 确保face normal朝向
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(shanWallObj.data)
    shanWallObj.data.update()
    bm.free()

    # 设置材质
    mat.setMat(shanWallObj,
            aData.mat_brick_3)
    
    # 2、创建下碱对象
    # 下碱一般取柱高度的1/3
    bottomheight = bData.piller_height * con.WALL_BOTTOM_RATE
    # 但最高不超过1.5m
    if bottomheight > con.WALL_BOTTOM_LIMIT:
        bottomheight = con.WALL_BOTTOM_LIMIT
    # 下碱长度：通进深 + 墀头 + 下碱延伸
    bottomLength = (
        bData.y_total 
        + con.SHANQIANG_EX*dk*2
        + con.WALL_SHRINK*2
    )
    # 下碱宽度：山墙9DK+出碱
    bottomWidth = (
        con.SHANQIANG_WIDTH*dk
        + con.WALL_SHRINK*2
    )
    bottomObj = utils.addCube(
        name='下碱',
        dimension=(bottomWidth,
               bottomLength,
               bottomheight),
        location=(
            bData.x_total/2+bottomWidth/2-con.WALL_SHRINK,
            0,
            bottomheight/2-tile_base),
        parent=shanWallObj,
    )
    # 赋材质
    mat.setMat(bottomObj,aData.mat_rock)

    # 合并山墙和下碱
    shanwallJoin = utils.joinObjects([shanWallObj,bottomObj])
    
    # 添加镜像
    utils.addModifierMirror(
        object=shanwallJoin,
        mirrorObj=rafterRootObj,
        use_axis=(True,False,False)
    )
    
    return

# 营造椽望层
def __buildRafterFrame(buildingObj:bpy.types.Object):
    # 设定“椽望”根节点
    rafterRootObj = __addRafterRoot(buildingObj)

    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp

    # 计算桁檩定位点
    purlin_pos = buildBeam.getPurlinPos(buildingObj)
    
    # 如果有斗栱，剔除挑檐桁
    # 在椽架、角梁的计算中不考虑挑檐桁
    rafter_pos = purlin_pos.copy()
    if (bData.use_dg                # 不使用斗栱的不用挑檐桁
        and bData.dg_extend > 0     # 一斗三升这种无出跳的，不用挑檐桁
        ):
        del rafter_pos[0]

    # 摆放椽架（包括角梁、檐椽、望板、飞椽、里口木、大连檐等）
    __buildRafterForAll(buildingObj,rafter_pos)

    # 营造山墙，仅适用于硬山
    if bData.roof_style in (
            con.ROOF_YINGSHAN,
            con.ROOF_YINGSHAN_JUANPENG,
            ):
        __buildShanWall(buildingObj,rafter_pos)
    # 营造象眼板，适用于悬山（卷棚）
    if bData.roof_style in (
            con.ROOF_XUANSHAN,
            con.ROOF_XUANSHAN_JUANPENG):
        __buildXiangyanBan(buildingObj,rafter_pos)
    # 营造博缝板，适用于歇山、悬山(卷棚)、硬山
    if bData.roof_style in (
            con.ROOF_XIESHAN,
            con.ROOF_XUANSHAN,
            con.ROOF_YINGSHAN,
            con.ROOF_XUANSHAN_JUANPENG,
            con.ROOF_YINGSHAN_JUANPENG,
            con.ROOF_XIESHAN_JUANPENG,):
        __buildBofeng(buildingObj,rafter_pos)

    # 设置材质，原木色
    for obj in rafterRootObj.children:
        mat.setMat(obj,
            aData.mat_wood)
        
    return

# 营造整个房顶
def buildRoof(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    # 添加“屋顶层”根节点
    # 斗栱层、梁架、椽望、瓦作都绑定在该节点下，便于统一重新生成
    # 这三层的结构紧密相连，无法解耦，只能一起生成，一起刷新
    if (bData.is_showDougong 
        or bData.is_showBeam
        or bData.is_showRafter
        or bData.is_showTiles):
        __addRoofRoot(buildingObj)

    # 层间的依赖，自动处理
    # 斗栱层、梁架层、椽望层都已经分别解耦，可以独立生成
    # 瓦作层与椽望层耦合，暂时无法解耦
    if bData.is_showTiles:
        bData['is_showRafter'] = True

    # 生成斗栱层
    if bData.is_showDougong:
        utils.outputMsg("Building Dougong...")
        buildDougong.buildDougong(buildingObj)

    # 生成梁架
    if bData.is_showBeam:
        utils.outputMsg("Building Beams...")
        buildBeam.buildBeamFrame(buildingObj)
    
    # 生成椽望
    if bData.is_showRafter:
        utils.outputMsg("Building Rafters...")
        __buildRafterFrame(buildingObj)

    # 生成瓦作层
    if bData.is_showTiles:
        utils.outputMsg("Building Tiles...")
        buildRooftile.buildTile(buildingObj)
    
    utils.focusObj(buildingObj)
    return {'FINISHED'}