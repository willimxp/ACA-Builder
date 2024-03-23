# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   椽架的营造
import bpy
import bmesh
import math
from mathutils import Vector,Euler

from . import utils
from . import buildFloor
from . import buildDougong
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData

# 设置“屋顶层”根节点
def __setRoofRoot(buildingObj:bpy.types.Object)->bpy.types.Object:
    # 新建或清空根节点
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    if roofRootObj != None:
        utils.deleteHierarchy(roofRootObj,del_parent=True)
    # 创建屋顶根对象
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    roofRootObj = bpy.context.object
    roofRootObj.name = "屋顶层"
    roofRootObj.parent = buildingObj
    roofRootObj.ACA_data['aca_obj'] = True
    roofRootObj.ACA_data['aca_type'] = con.ACA_TYPE_ROOF_ROOT
    # 以挑檐桁下皮为起始点
    bData : acaData = buildingObj.ACA_data # 载入数据
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    roof_base = bData.platform_height \
                + bData.piller_height
    # 如果有斗栱，抬高斗栱高度
    if bData.use_dg:
        roof_base += bData.dg_height
    else:
        # 以大梁抬升
        roof_base += con.BEAM_HEIGHT*pd
    roofRootObj.location = (0,0,roof_base)
        
    return roofRootObj

# 举架数据计算，与屋顶样式无关
# 按照清则例的举架算法，引入每一举的举架系数LIFT_RATIO
# 根据实际的进深，计算出实际的举架高度
# 返回的是纵切面上的二维坐标（x值在Y-axis，y值在Z-axis）
def __getLiftPos(buildingDeepth,rafterCount): 
    # 步架宽，这里按照常见的步架宽度相等处理，实际有些特例可能是不相等的
    rafterSpan = buildingDeepth / rafterCount

    # 举架坐标，仅计算纵截面的二维数据
    liftPos = []
    # 根据举架系数，逐个桁架上举
    for n in range(int(rafterCount/2)+1):
        # 进深方向内推一步架  
        purlin_x = buildingDeepth/2 - rafterSpan * n
        # 高度方向逐级上举
        if n == 0 :
            purlin_y = 0
        else:
            purlin_y += rafterSpan * con.LIFT_RATIO[n-1]
        liftPos.append(Vector((purlin_x,purlin_y)))

    # 返回居家数据集
    return liftPos

# 计算举架数据
# 1、根据不同的屋顶样式生成，自动判断了桁在檐面需要延长的长度
# 2、根据是否带斗栱，自动判断了是否插入挑檐桁
# 3、根据建筑面阔进深，将举架数据转换为了桁檩转角交点
def __getPurlinPos(buildingObj:bpy.types.Object):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    # 屋顶样式，1-庑殿，2-歇山，3-悬山，4-硬山
    roofStyle = bData.roof_style
    # 计算举架参数集
    buildingDeepth = bData.y_total      # 建筑进深
    rafterCount = bData.rafter_count    # 步架数
    rafterSpan = buildingDeepth / rafterCount   # 步架宽
    # 计算举架系数
    liftPos = __getLiftPos(buildingDeepth,rafterCount)

    # 举架坐标集，保存了各层桁在檐面和山面的交叉点坐标
    purlin_pos = []

    liftEavePurlin = 0
    # 1、有斗栱建筑，添加一根挑檐桁
    if bData.use_dg:    
        # 1、定位挑檐桁
        # 平面上延伸斗栱出檐
        dgExtend = bData.dg_extend
        purlin_x = bData.x_total/2 + dgExtend
        purlin_y = bData.y_total/2 + dgExtend
        # 屋顶起点root在挑檐枋下皮，上移半桁
        purlin_z = con.HENG_TIAOYAN_D / 2 * dk
        purlin_pos.append(Vector((purlin_x,purlin_y,purlin_z)))
        # 挑檐部分的举架高度
        liftEavePurlin = purlin_z + dgExtend * con.LIFT_RATIO[0] \
            - (con.HENG_COMMON_D-con.HENG_TIAOYAN_D)*dk/2   # 减去挑檐桁、正心桁的直径差，向下压实

    # 2、定位正心桁、上下金桁、脊桁    
    for n in range(int(rafterCount/2)+1):
        # 每层桁的宽度与屋顶样式有关
        if roofStyle == '4':
            # 硬山，在面阔上延长一柱径，略超出柱边
            purlin_x = bData.x_total/2 + con.BEAM_DEEPTH * pd/2
        if roofStyle == '3':
            # 悬山，出梢一种做法是柱中出四椽四当，一种做法是柱中出上檐出
            # 这里简单的按上檐出计算
            purlin_x = bData.x_total/2 + con.YANCHUAN_EX* dk
        if roofStyle == '2':
            # 歇山
            if n in (0,1):
                # 歇山的正心桁、下金桁按45度对称返回
                # 但实际檐面的下金桁长度在摆放时，应该延伸到脊槫长度
                purlin_x = liftPos[n].x + (bData.x_total-bData.y_total)/2
            else:
                # 其他椽架，类似悬山，从下金桁交点，悬出固定值（这里取上檐出）
                purlin_x = liftPos[1].x + (bData.x_total-bData.y_total)/2+ con.YANCHUAN_EX* dk
        # 庑殿为四坡顶，在转角对称的基础上做推山处理
        if roofStyle == '1':
            purlin_x = liftPos[n].x + (bData.x_total-bData.y_total)/2 
            if n>1:
                # ================================
                # 推山做法，仅清代庑殿建筑使用，其他朝代未见，其他屋顶类型不涉及
                # 推山：面阔方向推一步架，第一架不推山   
                purlin_x -= rafterSpan * (1 - 0.9**(n-1))
        
        # 前后檐可直接使用举架数据
        purlin_y = liftPos[n].x
        purlin_z = liftPos[n].y + liftEavePurlin # 加上挑檐桁的举高
        purlin_pos.append(Vector((purlin_x,purlin_y,purlin_z)))

    # 返回桁檩定位数据集
    return purlin_pos

# 营造桁檩
# 包括檐面和山面
# 其中对庑殿和歇山做了特殊处理
def __buildPurlin(buildingObj:bpy.types.Object,purlin_pos):
    # 一、载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    # 屋顶样式，1-庑殿，2-歇山，3-悬山，4-硬山
    roofStyle = bData.roof_style
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    if roofStyle in ('3','4'):
        # 硬山、悬山桁不做出梢
        hengExtend = 0
    else:
        # 庑殿和歇山为了便于垂直交扣，做一桁径的出梢
        hengExtend = con.HENG_EXTEND * dk
    
    # 二、布置前后檐桁,根据上述计算的purlin_pos数据，批量放置桁对象
    for n in range(len(purlin_pos)) :
        # 桁交点
        pCross = purlin_pos[n]
        
        # 1、计算桁的直径
        if bData.use_dg and n==0:
            # 有斗栱建筑，第一根桁直径使用挑檐桁
            purlin_r = con.HENG_TIAOYAN_D / 2 * dk
        else:   # 金桁、脊桁
            # 其他桁直径（正心桁、金桁、脊桁）
            purlin_r = con.HENG_COMMON_D / 2 * dk
        
        # 2、计算桁的长度
        purlin_length_x = pCross.x * 2 + hengExtend
        # 歇山檐面的下金桁延长，与上层对齐
        if roofStyle == '2' :
            if bData.use_dg and n >= 2 :
                purlin_length_x = purlin_pos[-1].x * 2
            if not bData.use_dg and n >= 1 :
                purlin_length_x = purlin_pos[-1].x * 2
        
        # 3、创建桁对象
        hengFB = utils.addCylinderHorizontal(
                radius = purlin_r, 
                depth = purlin_length_x,
                location = (0,pCross.y,pCross.z), 
                name = "桁-前后",
                root_obj = roofRootObj
            )
        
        # 4、前后镜像
        if n!=len(purlin_pos)-1:
            # 除最后一根脊桁的处理，挑檐桁、正心桁、金桁做Y镜像
            utils.addModifierMirror(
                    object=hengFB,
                    mirrorObj=roofRootObj,
                    use_axis=(False,True,False)
                )
        else: 
            # 最后一根脊桁添加伏脊木
            # 伏脊木为6变形（其实不是正六边形，上大下小，这里偷懒了）
            # 为了补偿圆柱径与六边形柱径的误差，向下调整了1/8的伏脊木高
            loc_z = pCross.z+ (con.HENG_COMMON_D+con.FUJIMU_D)/2*dk - con.FUJIMU_D/8*dk
            fujimuObj = utils.addCylinderHorizontal(
                    radius = con.FUJIMU_D/2*dk, 
                    depth = purlin_length_x,
                    location = (0,0,loc_z), 
                    name = "伏脊木",
                    root_obj = roofRootObj,
                    edge_num =6
                )
    
    # 三、布置山面桁檩
    # 仅庑殿、歇山做山面桁檩，硬山、悬山不做山面桁檩
    if roofStyle in ('1','2'):
        if roofStyle == '1':
            # 庑殿的上面做所有桁檩，除脊桁
            rafterRange = range(len(purlin_pos)-1)
        if roofStyle == '2':
            # 歇山仅做挑檐桁(如果有)、正心桁、下金桁
            if bData.use_dg:
                rafterRange = range(3)
            else:
                rafterRange = range(2)
        for n in rafterRange :
            pCross = purlin_pos[n]
            # 1、计算桁的直径
            if bData.use_dg and n==0:
                # 有斗栱建筑，第一根桁直径使用挑檐桁
                purlin_r = con.HENG_TIAOYAN_D / 2 * dk
            else:   # 金桁、脊桁
                # 其他桁直径（正心桁、金桁、脊桁）
                purlin_r = con.HENG_COMMON_D / 2 * dk

            # 2、计算桁的长度
            purlin_length_y = pCross.y * 2 + hengExtend

            # 3、摆放桁对象
            hengLR = utils.addCylinderHorizontal(
                    radius = purlin_r, 
                    depth = purlin_length_y,
                    location = (pCross.x,0,pCross.z), 
                    rotation=Vector((0, 0, math.radians(90))), 
                    name = "桁-两山",
                    root_obj = roofRootObj
                )
            
            # 4、添加镜像
            utils.addModifierMirror(
                object=hengLR,
                mirrorObj=roofRootObj,
                use_axis=(True,False,False)
            )
    return

# 营造梁架
# 1、只做了通檐的大梁，没有做抱头梁形式
def __buildBeam(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    
    # 准备基本构件
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    beamObj = bpy.context.object

    # 横向循环每一幅梁架
    roofStyle = bData.roof_style
    if roofStyle in ('1'):
        # 庑殿、歇山不做两山的梁架
        beamRange = range(1,len(net_x)-1)
    if roofStyle in ('2','3','4'):
        # 硬山和悬山在每个开间上都做梁架
        beamRange = range(len(net_x))
    for x in beamRange:# 这里为庑殿，山面柱头不设梁架
        # 纵向循环每一层梁架
        for n in range(len(purlin_pos)):  
            # 添加横梁
            if n!=len(purlin_pos)-1: # 排除脊槫
                # X向随槫交点依次排列
                beam_x = net_x[x]
                beam_z = purlin_pos[n].z - con.BEAM_HEIGHT*pd/2
                beam_l = purlin_pos[n].y*2 + con.HENG_COMMON_D*dk*2
                
                # 歇山做特殊处理
                if roofStyle == '2':
                    # 歇山的山面梁坐在金桁的X位置
                    if n>0 :
                        if x == 0:
                            beam_x = -purlin_pos[1].x
                        if x == beamRange[-1]:
                            beam_x = purlin_pos[1].x
                    # 歇山做踩步金，向上位移到与桁下皮平
                    if n==1 and x in (0,beamRange[-1]):
                        beam_z = purlin_pos[n].z \
                            + con.BEAM_HEIGHT*pd/2 \
                            - con.HENG_COMMON_D*dk/2
                        beam_l = purlin_pos[n].y*2

                beam_loc = Vector((beam_x,0,beam_z))
                beamCopyObj = utils.copyObject(
                            sourceObj= beamObj,
                            name="直梁",
                            location=beam_loc,
                            parentObj=roofRootObj
                        )
                beamCopyObj.dimensions = Vector((
                    con.BEAM_DEEPTH*pd,
                    beam_l,
                    con.BEAM_HEIGHT*pd
                ))

                # 在梁上添加蜀柱
                if roofStyle == '2' and n==0 and x in (0,beamRange[-1]):
                    # 歇山山面第一层不做蜀柱
                    continue
                if n == len(purlin_pos)-2:
                    # 直接支撑到脊槫
                    shuzhu_height = purlin_pos[n+1].z - purlin_pos[n].z
                else:
                    # 支撑到上下两根梁之间
                    shuzhu_height = purlin_pos[n+1].z \
                        - purlin_pos[n].z \
                        - con.BEAM_HEIGHT*pd
                shuzhu_loc = Vector((
                    beam_x,   # X向随槫交点依次排列
                    purlin_pos[n+1].y, # 对齐上一层的槫的Y位置
                    purlin_pos[n].z + shuzhu_height/2
                ))
                shuzhuCopyObj = utils.copyObject(
                            sourceObj= beamObj,
                            name="蜀柱",
                            location=shuzhu_loc,
                            parentObj=roofRootObj
                        )
                shuzhuCopyObj.dimensions = Vector((
                    con.PILLER_CHILD*dk,
                    con.PILLER_CHILD*dk,
                    shuzhu_height
                ))
                if n!=len(purlin_pos)-1:
                    #镜像
                    mod = shuzhuCopyObj.modifiers.new(name='mirror', type='MIRROR')
                    mod.mirror_object = roofRootObj
                    mod.use_axis[0] = False
                    mod.use_axis[1] = True            
    
    # 删除基本构件
    bpy.data.objects.remove(beamObj)
    return

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
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
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
    bpy.ops.mesh.primitive_cube_add(size=1,
            location = LKM_loc,
            rotation = LKM_rotate,
            scale = LKM_scale
            )
    LKMObj = bpy.context.object
    LKMObj.name = LKM_name
    LKMObj.parent = roofRootObj
    LKMObj.ACA_data['aca_obj'] = True
    LKMObj.ACA_data['aca_type'] = LKM_type
    utils.addModifierMirror(
        object=LKMObj,
        mirrorObj=roofRootObj,
        use_axis=LKM_mirrorAxis
    )
    return

# 营造前后檐椽子
# 庑殿、歇山可自动裁切
def __buildRafter_FB(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    # 金桁是数组中的第二个（已排除挑檐桁）
    jinhengPos = purlin_pos[1]
    # 计算椽当
    rafter_gap_x = __getRafterGap(buildingObj,
                rafter_tile_width=jinhengPos.x)
    
    # 根据桁数组循环计算各层椽架
    for n in range(len(purlin_pos)-1):
        # 1.逐层定位椽子，直接连接上下层的桁檩(槫子)
        rafter_offset = Vector((rafter_gap_x/2,0,0))
        rafter_end = purlin_pos[n] * Vector((0,1,1)) + rafter_offset
        rafter_start = purlin_pos[n+1] * Vector((0,1,1)) + rafter_offset
        fbRafterObj = utils.addCylinderBy2Points(
            radius = con.YUANCHUAN_D/2*dk,
            start_point = rafter_start,
            end_point = rafter_end,
            name="檐椽.前后",
            root_obj = roofRootObj
        )
        fbRafterObj.ACA_data['aca_obj'] = True
        fbRafterObj.ACA_data['aca_type'] = con.ACA_TYPE_RAFTER_FB
        # 2. 各层椽子都上移，与桁檩上皮相切
        bpy.ops.transform.translate(
            value = (0,0,(con.HENG_COMMON_D+con.YUANCHUAN_D)*dk/2),
            orient_type = 'LOCAL'
        )  
        
        # 3. 仅檐椽延长，按檐总平出加斜计算
        if n == 0:
            # 檐椽斜率（圆柱体默认转90度）
            yan_rafter_angle = math.cos(fbRafterObj.rotation_euler.y)
            # 斗栱平出+14斗口檐椽平出
            yan_rafter_ex = con.YANCHUAN_EX * dk
            if bData.use_dg : 
                yan_rafter_ex += bData.dg_extend

            # 加斜计算
            fbRafterObj.dimensions.x += yan_rafter_ex / yan_rafter_angle
            utils.applyTransfrom(fbRafterObj,use_scale=True) # 便于后续做望板时获取真实长度
        
        # 4. 仅脑椽延长，达到伏脊木的位置
        # 【手工修正】：没有理论依据，纯粹为了好看
        if n== len(purlin_pos)-2 :
            naochuan_adj = con.HENG_COMMON_D/2*dk   # 手工设定了一个调节值，瞎估的
            fbRafterObj.dimensions.x += naochuan_adj
            utils.applyTransfrom(fbRafterObj,use_scale=True)
            bpy.ops.transform.translate(
                value = (-naochuan_adj,0,0),
                orient_type = con.OFFSET_ORIENTATION 
            )

        # 5. 各层椽子平铺
        if bData.roof_style == '1' and n != 0:
            # 庑殿的椽架需要延伸到下层宽度，以便后续做45度裁剪
            rafter_tile_x = purlin_pos[n].x
        else:
            # 檐椽平铺到上层桁交点
            rafter_tile_x = purlin_pos[n+1].x  
        utils.addModifierArray(
            object=fbRafterObj,
            count=int(rafter_tile_x /rafter_gap_x),
            offset=(0,-rafter_gap_x,0)
        )
        
        # 四、裁剪，仅用于庑殿，且檐椽不涉及
        if bData.roof_style =='1' and n!=0:
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
        utils.addModifierMirror(
            object=fbRafterObj,
            mirrorObj=roofRootObj,
            use_axis=(True,True,False)
        )

    # 构造里口木
    __buildLKM(buildingObj,purlin_pos,'X') 

    return

# 营造两山椽子
# 硬山、悬山建筑不涉及
def __buildRafter_LR(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    # 金桁是数组中的第二个（已排除挑檐桁）
    jinhengPos = purlin_pos[1]
    # 计算山面椽当
    rafter_gap_y = __getRafterGap(buildingObj,
                    rafter_tile_width=jinhengPos.y)     
        
    # 根据桁数组循环计算各层椽架
    for n in range(len(purlin_pos)-1):
        if bData.roof_style == '2': 
            if n > 0: continue  # 歇山山面仅做一层椽架
        # 1.逐层定位椽子，直接连接上下层的桁檩(槫子)
        rafter_offset = Vector((0,rafter_gap_y/2,0))
        rafter_end = purlin_pos[n]*Vector((1,0,1))+rafter_offset
        rafter_start = purlin_pos[n+1]*Vector((1,0,1))+rafter_offset
        lrRafterObj = utils.addCylinderBy2Points(
            radius = con.YUANCHUAN_D/2*dk,
            start_point = rafter_start,
            end_point = rafter_end,
            name="檐椽.两山",
            root_obj = roofRootObj
        )
        lrRafterObj.ACA_data['aca_obj'] = True
        lrRafterObj.ACA_data['aca_type'] = con.ACA_TYPE_RAFTER_LR
        # 上移，与桁檩上皮相切
        bpy.ops.transform.translate(
            value = (0,0,(con.HENG_COMMON_D+con.YUANCHUAN_D)*dk/2),
            orient_type = con.OFFSET_ORIENTATION # GLOBAL/LOCAL ?
        )   
        
        # 檐面和山面的檐椽延长，按檐总平出加斜计算
        if n == 0:
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
        if bData.roof_style == '1' and n != 0:
            # 庑殿的椽架需要延伸到下层宽度，以便后续做45度裁剪
            rafter_tile_y = purlin_pos[n].y
        else:
            # 檐椽平铺到上层桁交点
            rafter_tile_y = purlin_pos[n+1].y       
        utils.addModifierArray(
            object=lrRafterObj,
            count=math.floor(rafter_tile_y /rafter_gap_y),
            offset=(0,rafter_gap_y,0)
        )
        
        # 裁剪，仅用于庑殿，且檐椽不涉及
        if bData.roof_style in ('1') and n!=0:
            utils.addBisect(
                    object=lrRafterObj,
                    pStart=buildingObj.matrix_world @ purlin_pos[n],
                    pEnd=buildingObj.matrix_world @ purlin_pos[n+1],
                    pCut=buildingObj.matrix_world @ purlin_pos[n] + \
                        Vector((con.JIAOLIANG_Y*dk/2,0,0)),
                    clear_inner=True
            ) 
        
        # 镜像
        utils.addModifierMirror(
            object=lrRafterObj,
            mirrorObj=roofRootObj,
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
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)

    # 添板只做1象限半幅，然后镜像
    # 根据桁数组循环计算各层椽架
    for n in range(len(purlin_pos)-1):
        # 望板宽度
        if n==0: # 平铺到上层桁交点     
            width = purlin_pos[n+1].x 
        else: # 其他椽架平铺到下层桁交点，然后切割
            width = purlin_pos[n].x
        # 歇山的望板统一取脊槫宽度
        if bData.roof_style=='2' and n>0:
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
            deepth=width,
            height=con.WANGBAN_H*dk,
            name="望板",
            root_obj=roofRootObj,
            origin_at_start=True
        )
        # 望板延长，按檐总平出加斜计算
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
        offset = (con.HENG_COMMON_D/2 
                  + con.YUANCHUAN_D 
                  + con.WANGBAN_H/2) * dk
        bpy.ops.transform.translate(
            value = (0,0,offset),
            orient_type = 'LOCAL'
        )
        if bData.roof_style =='1':
            # 仅庑殿需要裁剪望板
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
            mirrorObj=roofRootObj,
            use_axis=(True,True,False)
        )

    return  # EOF：__buildWangban_FB

# 营造两山望板
# 与椽架代码解耦，降低复杂度
def __buildWangban_LR(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)

    # 添板只做1象限半幅，然后镜像
    # 根据桁数组循环计算各层椽架
    for n in range(len(purlin_pos)-1):
        # 歇山的山面只做一层望板
        if bData.roof_style == '2' and n>0: continue
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
            deepth=width,
            height=con.WANGBAN_H*dk,
            name="望板",
            root_obj=roofRootObj,
            origin_at_start=True
        )
        # 望板延长，按檐总平出加斜计算
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
        offset = (con.HENG_COMMON_D/2 
                  + con.YUANCHUAN_D 
                  + con.WANGBAN_H/2) * dk
        bpy.ops.transform.translate(
            value = (0,0,offset),
            orient_type = 'LOCAL'
        )
        if bData.roof_style =='1':
            # 仅庑殿需要裁剪望板
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
            mirrorObj=roofRootObj,
            use_axis=(True,True,False)
        )  

    return # EOF：

# 根据檐椽，绘制对应飞椽
# 基于“一飞二尾五”的原则计算
def __drawflyRafterMesh(yanRafterObj:bpy.types.Object)->bpy.types.Object:
    # 载入数据
    buildingObj = utils.getAcaParent(yanRafterObj,con.ACA_TYPE_BUILDING)
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    
    # 创建bmesh
    bm = bmesh.new()
    # 各个点的集合
    vectors = []

    # 第1点在飞椽腰，对齐了檐椽头，分割飞椽头、尾的转折点
    v1 = Vector((0,0,0))
    vectors.append(v1)

    # 第2点在飞椽尾
    # 飞尾平出：7斗口*2.5=17.5斗口
    flyrafterEnd_pingchu = con.flyrafter_EX / con.flyrafter_HEAD_TILE_RATIO * dk
    # 飞尾在檐椽方向加斜
    yanChuan_angle = yanRafterObj.rotation_euler.y   # 檐椽斜角
    flyrafterEnd_loc = flyrafterEnd_pingchu / math.cos(yanChuan_angle)    
    v2 = Vector((-flyrafterEnd_loc,0,0)) # 飞椽尾的坐标
    vectors.append(v2)

    # 第3点在飞椽腰的上沿
    v3 = Vector((0,0,con.flyrafter_H*dk))
    # 飞椽仰角（基于飞尾楔形的对边为飞椽高）
    flyrafter_angle_change = -math.asin(con.flyrafter_H*dk / flyrafterEnd_loc)
    # 随椽头昂起
    v3.rotate(Euler((0,flyrafter_angle_change,0),'XYZ'))
    vectors.append(v3)

    # 第4点在飞椽头上沿
    flyrafterEnd_length = flyrafterEnd_loc * math.cos(flyrafter_angle_change)
    flyrafterHead_length = flyrafterEnd_length * con.flyrafter_HEAD_TILE_RATIO
    v4 = Vector((flyrafterHead_length,0,con.flyrafter_H*dk))
    # 随椽头昂起
    v4.rotate(Euler((0,flyrafter_angle_change,0),'XYZ'))
    vectors.append(v4)

    # 第5点在飞椽头下檐
    v5 = Vector((flyrafterHead_length,0,0))
    # 随椽头昂起
    v5.rotate(Euler((0,flyrafter_angle_change,0),'XYZ'))
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
    bmesh.ops.translate(bm, verts=verts, vec=(0, con.flyrafter_H*dk, 0))

    offset = Vector((0,0,(con.YUANCHUAN_D/2+con.WANGBAN_H)*dk))
    for v in bm.verts:
        # 移动所有点，居中
        v.co.y -= con.flyrafter_H*dk/2
        # 向上位移半檐椽+一望板
        v.co += Vector((0,0,(con.YUANCHUAN_D/2+con.WANGBAN_H)*dk))
    
    # 确保face normal朝向
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    #=============================
    # 将Mesh绑定到Object上
    # 对齐檐椽位置
    yanchuan_head_co = utils.getObjectHeadPoint(yanRafterObj,
            is_symmetry=(True,True,False))
    # 任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add(
        location=yanchuan_head_co
    )
    flyrafterObj = bpy.context.object
    # 对齐檐椽角度
    flyrafterObj.rotation_euler = yanRafterObj.rotation_euler 
    # 填充bmesh数据
    bm.to_mesh(flyrafterObj.data)
    flyrafterObj.data.update()
    bm.free()

    # 重设Origin：把原点放在椽尾，方便后续计算椽头坐标
    vo = v2 + offset
    utils.setOrigin(flyrafterObj,vo)

    # 重设旋转数据：把旋转角度与上皮对齐，方便后续摆放压椽尾望板
    change_rot = v4-v3
    utils.changeOriginRotation(change_rot,flyrafterObj)

    return flyrafterObj

# 营造檐椽
# 通过direction='X'或'Y'决定山面和檐面
def __buildflyrafter(buildingObj,direction):
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)

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

    flyrafterObj = __drawflyRafterMesh(yanRafterObj)
    flyrafterObj.name = flyrafterName
    flyrafterObj.parent = roofRootObj
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
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    # 获取金桁位置，做为望板的宽度
    jinhengPos = purlin_pos[1]

    # 判断前后檐，还是两山
    if direction == 'X':    # 前后檐
        FWB_name = "压飞尾望板.前后"
        FWB_width = jinhengPos.x * 2    # 宽度取金桁交点
        mirrorAxis = (False,True,False) # Y轴镜像
        flyrafterType = con.ACA_TYPE_FLYRAFTER_FB
    else:
        FWB_name = "压飞尾望板.两山"
        FWB_width = jinhengPos.y * 2    # 宽度取金桁交点
        mirrorAxis = (True,False,False) # X轴镜像
        flyrafterType = con.ACA_TYPE_FLYRAFTER_LR
    
    # 生成前后檐压飞尾望板
    # 以飞椽为参考基准
    flyrafterObj = utils.getAcaChild(buildingObj,flyrafterType)
    # 长度取飞椽长度，闪躲大连檐
    fwb_deepth = utils.getMeshDims(flyrafterObj).x \
            -(con.QUETAI+con.DALIANYAN_Y)*dk
    # 从飞椽尾，平移半飞椽长，向上半望板高
    offset = Vector((fwb_deepth/2,0,con.WANGBAN_H/2*dk))
    offset.rotate(flyrafterObj.rotation_euler)
    if direction == 'X':
        flyrafterEndban_co = (flyrafterObj.location+offset) * Vector((0,1,1)) # 飞椽尾
    else:
        flyrafterEndban_co = (flyrafterObj.location+offset) * Vector((1,0,1)) # 飞椽尾
    # 生成压飞望板
    bpy.ops.mesh.primitive_cube_add(
            size=1.0, 
            location=flyrafterEndban_co,
            rotation=flyrafterObj.rotation_euler, 
            scale=(fwb_deepth,FWB_width,con.WANGBAN_H*dk)
        )
    fwbObj = bpy.context.object
    fwbObj.name = FWB_name
    fwbObj.parent = roofRootObj
    # 镜像
    utils.addModifierMirror(
        object=fwbObj,
        mirrorObj=roofRootObj,
        use_axis=mirrorAxis
    )

# 营造大连檐
# 通过direction='X'或'Y'决定山面和檐面
def __buildDLY(buildingObj,purlin_pos,direction):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
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
                    (con.flyrafter_H/2+con.DALIANYAN_H/2)*dk)) # 从飞椽中上移
    offset.rotate(flyrafterObj.rotation_euler)
    
    # 前后檐、两山的location，rotation不同
    if direction == 'X': 
        DLY_name = "大连檐.前后"
        DLY_rotate = (math.radians(90)-flyrafterObj.rotation_euler.y,0,0)
        DLY_loc:Vector = (flyrafter_head_co + offset)*Vector((0,1,1))
        DLY_scale = (jinhengPos.x * 2,  
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
    bpy.ops.mesh.primitive_cube_add(size=1,
            location = DLY_loc,
            rotation = DLY_rotate,
            scale = DLY_scale
            )
    DLY_Obj = bpy.context.object
    DLY_Obj.name = DLY_name
    DLY_Obj.parent = roofRootObj
    DLY_Obj.ACA_data['aca_obj'] = True
    DLY_Obj.ACA_data['aca_type'] = DLY_type

    # 添加镜像
    utils.addModifierMirror(
        object=DLY_Obj,
        mirrorObj=roofRootObj,
        use_axis=DLY_mirrorAxis
    )

# 营造飞椽（以及里口木、压飞望板、大连檐等附属构件)
# 小式建筑中，可以不使用飞椽
def __buildFlyRafter(buildingObj:bpy.types.Object,purlinPos,direction):    
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    useFlyrafter = bData.use_flyrafter
    useWangban = bData.use_wangban

    if useFlyrafter:  # 用户可选择不使用飞椽
        # 构造飞椽
        __buildflyrafter(buildingObj,direction)  

        # 压飞望板
        if useWangban:  # 用户可选择暂时不生成望板（更便于观察椽架形态）
            __buildFlyrafterWangban(buildingObj,purlinPos,direction)     

        # 大连檐
        __buildDLY(buildingObj,purlinPos,direction)
            
    return

# 根据老角梁，绘制对应子角梁
# 基于“冲三翘四”的原则计算
# 硬山、悬山不涉及
def __drawCornerBeamChild(cornerBeamObj:bpy.types.Object):
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
    
    # 任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add(
        location=cornerBeam_head_co
    )
    smallCornerBeamObj = bpy.context.object
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
    v2 = Vector((-cornerBeam_length,0,0))
    vectors.append(v2)

    # 第3点在子角梁尾向上一角梁高
    # 与老角梁同长
    v3 = Vector((-cornerBeam_length ,0,con.JIAOLIANG_H*dk))
    vectors.append(v3)

    # 第4点在子角梁腰向上一角梁高
    # 与老角梁同长
    v4 = Vector((0,0,con.JIAOLIANG_H*dk))
    vectors.append(v4)

    # 第5点，定位子角梁的梁头上沿
    # 在local坐标系中计算子角梁头的绝对位置
    # 计算冲出后的X、Y坐标，由飞椽平出+冲1椽（老角梁已经冲了2椽）+雀台
    scb_ex_length = (con.flyrafter_EX + con.YUANCHUAN_D +con.QUETAI) * dk
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
    #showVector(bpy.context,root_obj,flyrafter_head_co)
    # 翘四: 从飞椽头上皮，到子角梁上皮，其中要补偿0.75斗口，即半椽，合计调整一椽（见汤书p171）
    scb_abs_z = flyrafter_head_co.z + con.YUANCHUAN_D*dk \
            + bData.qiqiao*con.YUANCHUAN_D*dk # 默认起翘4椽
    scb_abs_co = Vector((scb_abs_x,scb_abs_y,scb_abs_z))
    # 将该起翘点存入dataset，后续翼角可供参考（相对于root_obj）
    bData.roof_qiao_point = scb_abs_co
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

    return smallCornerBeamObj

# 营造角梁（包括老角梁、子角梁、由戗）
def __buildCornerBeam(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    
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
                pStart = Vector(purlin_pos[n]) \
                    + Vector((0,0,con.JIAOLIANG_H*dk*con.JIAOLIANG_HEAD_YAJIN))
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
            if bData.roof_style == '2' : continue

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
            deepth=con.JIAOLIANG_Y*dk,
            height=con.JIAOLIANG_H*dk,
            name=CornerBeamName,
            root_obj=roofRootObj,
            origin_at_end=True
        )
        
        if n==0:    # 老角梁
            CornerBeamObj.ACA_data['aca_obj'] = True
            CornerBeamObj.ACA_data['aca_type'] = con.ACA_TYPE_CORNER_BEAM
            # 延长老角梁，（斗栱平出+檐椽平出+出冲+雀台）*加斜
            ex_length = con.YANCHUAN_EX*dk \
                + (bData.chong-1)*con.YUANCHUAN_D*dk \
                + con.QUETAI*dk + con.LIKOUMU_Y/2*dk
            if bData.use_dg: ex_length += bData.dg_extend

            # 水平面加斜45度
            ex_length = ex_length * math.sqrt(2)
            # 立面加斜老角梁扣金角度   
            ex_length = ex_length / math.cos(CornerBeamObj.rotation_euler.y)
            CornerBeamObj.dimensions.x += ex_length
            utils.applyTransfrom(CornerBeamObj,use_scale=True)
            
            if bData.use_flyrafter:
                # 绘制子角梁
                cbcObj:bpy.types.Object = \
                    __drawCornerBeamChild(CornerBeamObj)
                cbcObj.name = '仔角梁'
                cbcObj.parent = roofRootObj
                cbcObj.ACA_data['aca_obj'] = True
                cbcObj.ACA_data['aca_type'] = con.ACA_TYPE_CORNER_BEAM_CHILD
                utils.addModifierMirror(
                    object=cbcObj,
                    mirrorObj=roofRootObj,
                    use_axis=(True,True,False))

        # 添加镜像
        utils.addModifierMirror(
            object=CornerBeamObj,
            mirrorObj=roofRootObj,
            use_axis=(True,True,False))
    
    return

# 营造翼角小连檐实体（连接翼角椽）
def __buildCornerRafterEave(buildingObj:bpy.types.Object):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    # 屋顶根节点
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    # 前后檐椽
    yanRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_FB)
    # 老角梁
    cornerBeamObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_CORNER_BEAM)
    # 里口木
    lkmObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_LKM_FB)

    # 1.小连檐起点：对接前后檐正身里口木位置
    xly_curve_start = Vector((
        utils.getMeshDims(lkmObj).x / 2,    # 大连檐右端顶点，长度/2
        lkmObj.location.y,
        lkmObj.location.z
    ))

    # 2.小连檐终点
    # 2.1 立面高度，基于老角梁头坐标（小连檐受到老角梁的限制）
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
    xly_curve_end_z = cornerBeamHead_co + offset

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
    xly_curve_end = Vector((
        bData.x_total/2 + rafterExtend - shift,
        bData.y_total/2 + rafterExtend -con.QUETAI*dk,
        xly_curve_end_z.z
    ))

    # 3.小连檐中点：定位小连檐曲率控制点
    xly_curve_middle = Vector(((xly_curve_start.x+xly_curve_end.x)/2,   # 水平线上取中点
                            xly_curve_start.y,   # 与起点水平
                            xly_curve_start.z))  # 与起点水平
    
    # 4.绘制小连檐对象
    CurvePoints = [xly_curve_start,xly_curve_middle,xly_curve_end]
    tiltHead = - yanRafterObj.rotation_euler.y
    tiltEnd = - cornerBeamObj.rotation_euler.y
    xly_curve_obj = utils.addCurveByPoints(
                        CurvePoints=CurvePoints,
                        tilt=tiltEnd,
                        tilt_head=tiltHead,
                        name='小连檐',
                        root_obj=roofRootObj,
                        width = con.LIKOUMU_Y*dk,
                        height = con.LIKOUMU_H*dk,
                    )
    # 相对角梁做45度对称
    utils.addModifierMirror(
        object=xly_curve_obj,
        mirrorObj=cornerBeamObj,
        use_axis=(False,True,False)
    )
    # 四面对称
    utils.addModifierMirror(
        object=xly_curve_obj,
        mirrorObj=roofRootObj,
        use_axis=(True,True,False)
    )

# 营造翼角椽定位线
def __buildCornerRafterCurve(buildingObj:bpy.types.Object):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    # 屋顶根节点
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    # 前后檐椽
    yanRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_FB)
    # 老角梁
    cornerBeamObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_CORNER_BEAM)
    
    # 1.曲线起点：对齐最后一根正身檐椽的椽头
    yanRafterHead_co = utils.getObjectHeadPoint(yanRafterObj,
            eval=True,  # eval=True可以取到应用了array后的结果
            is_symmetry=(True,True,False))
    rafterCurve_start = yanRafterHead_co
    
    # 2.曲线终点
    # 2.1 立面Z坐标，基于老角梁头坐标计算
    cornerBeamHead_co = utils.getObjectHeadPoint(cornerBeamObj,
            is_symmetry=(True,True,False))
    # 偏移调整：内收雀台，避开老角梁穿模，上移到上皮
    offset = Vector((
        -con.QUETAI*dk, # 内收1雀台
        con.JIAOLIANG_Y/4*dk, # 退让1/4角梁
        con.JIAOLIANG_H/2*dk \
            - con.LIKOUMU_H*dk \
            - con.YUANCHUAN_D/2*dk  # 从中心+半角梁高-半个檐椽高
        ))
    offset.rotate(cornerBeamObj.rotation_euler)
    cornerBeamHead_co += offset
    rafterCurve_end_z = cornerBeamHead_co.z

    # 2.2 平面X/Y坐标，从椽头按出冲系数进行计算
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
    rafterCurve_end = Vector((
        bData.x_total/2 + rafterExtend - shift,
        bData.y_total/2 + rafterExtend,
        rafterCurve_end_z))

    # 3.曲线中点，曲率控制
    rafterCurve_middle = Vector((
        (rafterCurve_start.x+rafterCurve_end.x)/2,   # 水平线上取中点
        rafterCurve_start.y,   # 与起点水平
        rafterCurve_start.z))  # 与起点水平
    
    # 4.绘制翼角椽定位线
    CurvePoints = [rafterCurve_start,
                    rafterCurve_middle,
                    rafterCurve_end]
    # resolution决定了后续细分的精度
    # 我尝试了64，150,300,500几个值，150能看出明显的误差，300和500几乎没有太大区别
    rafterCurve_obj = utils.addCurveByPoints(
            CurvePoints=CurvePoints,
            name='翼角椽定位线',
            resolution = con.CURVE_RESOLUTION,
            root_obj=roofRootObj
        ) 
    rafterCurve_obj.ACA_data['aca_obj'] = True
    rafterCurve_obj.ACA_data['aca_type'] = con.ACA_TYPE_CORNER_RAFTER_CURVE
    return rafterCurve_obj

# 营造翼角大连檐实体（连接翘飞椽）
def __buildCornerflyrafterEave(buildingObj:bpy.types.Object):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    # 屋顶根节点
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
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
    # 从最后一根正身飞椽头到子角梁头（子角梁经过冲、翘计算）
    # 1.大连檐起点：对接正身大连檐
    dlyStart = Vector((
        utils.getMeshDims(dlyObj).x / 2,    # 大连檐右端顶点，长度/2
        dlyObj.location.y,
        dlyObj.location.z
    ))
    # 2.大连檐终点
    # 完全采用理论值计算，与子角梁解耦
    # 有飞椽时，全部体现在翘飞椽上
    # （没有飞椽时，压根不进入本函数）
    chongLength = bData.chong * con.YUANCHUAN_D * dk
    qiqiao = bData.qiqiao * con.YUANCHUAN_D * dk
    dlyEnd_x = (bData.x_total/2
                +bData.dg_extend
                +con.YANCHUAN_EX*dk
                +con.flyrafter_EX*dk
                +chongLength)
    dlyEnd_y = dlyObj.location.y + chongLength
    dlyEnd_z = dlyObj.location.z + qiqiao
    dlyEnd = Vector((dlyEnd_x,dlyEnd_y,dlyEnd_z))

    # 3.大连檐中点：曲率控制
    dlyMiddle = Vector((
        (dlyStart.x+dlyEnd.x)/2,   # 水平线上取中点
        dlyStart.y,   # 与起点水平
        dlyStart.z))  # 与起点水平
    # 4.绘制大连檐对象
    CurvePoints = [dlyStart,dlyMiddle,dlyEnd]
    # 与正身大连檐的旋转角度相同
    CurveTilt = dlyObj.rotation_euler.x - math.radians(90)
    flyrafterEaveObj = utils.addCurveByPoints(
                        CurvePoints=CurvePoints,
                        tilt=CurveTilt,
                        name='大连檐',
                        root_obj=roofRootObj,
                        height = con.DALIANYAN_H*dk,
                        width = con.DALIANYAN_Y*dk
                    )
    
    # 相对角梁做45度对称
    utils.addModifierMirror(
        object=flyrafterEaveObj,
        mirrorObj=cornerBeamObj,
        use_axis=(False,True,False)
    )
    # 四面对称
    utils.addModifierMirror(
        object=flyrafterEaveObj,
        mirrorObj=roofRootObj,
        use_axis=(True,True,False)
    )

# 营造翘飞椽定位线
def __buildCornerFlyrafterCurve(buildingObj:bpy.types.Object):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    # 屋顶根节点
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    
    # 1.曲线起点：对齐最后一根正身飞椽的椽头
    flyrafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_FLYRAFTER_FB)
    flyrafterHeader_co = utils.getObjectHeadPoint(flyrafterObj,
            eval=True,
            is_symmetry=(True,True,False))
    flyrafterCurve_start = flyrafterHeader_co
    
    # 2.曲线终点     
    #（不依赖角梁，避免难以补偿的累计误差）
    # 有飞椽时，全部体现在翘飞椽上
    # （没有飞椽时，压根不进入本函数）
    chongLength = bData.chong*con.YUANCHUAN_D*dk
    flyrafterCurve_end_x = (bData.x_total/2
         +bData.dg_extend
         +con.YANCHUAN_EX*dk
         +con.flyrafter_EX*dk
         +chongLength)
    flyrafterCurve_end_y = flyrafterHeader_co.y + chongLength
    qiqiao = bData.qiqiao * con.YUANCHUAN_D * dk
    flyrafterCurve_end_z = flyrafterHeader_co.z + qiqiao
    flyrafterCurve_end = Vector((flyrafterCurve_end_x,flyrafterCurve_end_y,flyrafterCurve_end_z))

    # 3.曲线中点：曲率控制
    flyrafterCurve_middle = Vector((
        (flyrafterCurve_start.x+flyrafterCurve_end.x)/2,   # 水平线上取中点
        flyrafterCurve_start.y,   # 与起点水平
        flyrafterCurve_start.z))  # 与起点水平
    # 4.绘制翘飞椽定位线
    CurvePoints = [flyrafterCurve_start,
                    flyrafterCurve_middle,
                    flyrafterCurve_end]
    flyrafterCurve_obj = utils.addCurveByPoints(
            CurvePoints=CurvePoints,
            name='翘飞椽定位线',
            resolution = con.CURVE_RESOLUTION,
            root_obj=roofRootObj
        ) 
    return flyrafterCurve_obj

# 营造翼角椽(Corner Rafter,缩写CR)
def __buildCornerRafter(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    # 屋顶根节点
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
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
        yanExtend += con.flyrafter_EX * dk
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
    crEndPoints = utils.getNurbsSegment(crCurve,crCount)
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
            root_obj=roofRootObj
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
        # 角梁45度对称
        utils.addModifierMirror(
            object=cornerRafterObj,
            mirrorObj=cornerBeamObj,
            use_axis=(False,True,False)
        )
        # 四向对称
        utils.addModifierMirror(
            object=cornerRafterObj,
            mirrorObj=roofRootObj,
            use_axis=(True,True,False)
        )

        cornerRafterColl.append(cornerRafterObj)
    
    return cornerRafterColl

# 绘制一根翘飞椽
# 椽头定位：基于每一根翼角椽，指向翘飞椽檐口线对应的定位点
# 椽尾楔形构造：使用bmesh逐点定位、绘制
# 特殊处理：椽头撇度处理、椽腰扭度处理
def __drawQiaoflyrafter(yjcObj:bpy.types.Object,
                     qfc_head_point,
                     name,
                     head_shear:Vector,
                     mid_shear:Vector,
                     root_obj):
    # 载入数据
    buildingObj = utils.getAcaParent(yjcObj,con.ACA_TYPE_BUILDING)
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK

    # 将3d cursor定在翼角椽头上皮，也就是翘飞椽腰下皮
    # 获取翼角椽的椽头坐标
    yjc_head_co = utils.getObjectHeadPoint(yjcObj,
            eval=False,
            is_symmetry=(True,True,False))
    # 移动到上皮+望板
    offset = Vector((0,0,(con.YUANCHUAN_D /2+con.WANGBAN_H)*dk))
    offset.rotate(yjcObj.rotation_euler)
    origin_point = yjc_head_co + offset
    # 移动3d cursor
    bpy.context.scene.cursor.location = origin_point
    # 任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add()
    qfcObj = bpy.context.object
    qfcObj.name = name
    qfcObj.parent = root_obj    
    # 翘飞椽与翼角椽对齐旋转角度
    qfcObj.rotation_euler = yjcObj.rotation_euler
    bpy.context.view_layer.update() # 需要刷新，才能正确获取到该对象的matrix_local

    # 创建bmesh
    bm = bmesh.new()
    # 各个点的集合
    vectors = []

    # 1.在翘飞椽腰
    v1 = Vector((0,0,0))
    vectors.append(v1)
    # 2.到翘飞椽头下皮，从檐口定位线下移0.5半椽径
    # 获取翘飞椽坐标系中的椽头坐标
    qfc_head_point_local =  qfcObj.matrix_local.inverted() @ qfc_head_point
    qfc_mid_point_local = Vector((0,0,con.flyrafter_H/2*dk))
    # 计算飞椽头角度, 从定位线上的翼角椽头点start_point，到腰线向上半椽中点
    qfc_head_vector:Vector = qfc_head_point_local - qfc_mid_point_local
    qfc_head_rotation = utils.alignToVector(qfc_head_vector)
    # 因为实际的檐口线应该始终落在椽头的最短边，所以实际的椽头终点要根据斜率补偿
    # 计算翘飞椽头与檐口线的夹角
    shear_rot = utils.alignToVector(head_shear) # 檐口线夹角
    tilt_rot = qfcObj.rotation_euler.z - shear_rot.z 
    offset = Vector((
        con.flyrafter_H/2*dk / math.tan(tilt_rot),  # 椽头沿檐口线的补偿
        0,-con.flyrafter_H*0.5*dk # 下移半椽
        ))
    offset.rotate(qfc_head_rotation)
    v2 = qfc_head_point_local + offset
    vectors.append(v2)
    # 3.到翘飞椽头上皮，上移一椽径
    offset = Vector((0,0,con.flyrafter_H*dk))
    offset.rotate(qfc_head_rotation)
    v3 = v2 + offset
    vectors.append(v3)
    # 4.到翘飞椽腰点上皮，上移一椽径，注意坐标系已经旋转到檐椽角度
    v4 = Vector((0,0,con.flyrafter_H*dk))
    vectors.append(v4)
    # 5.到翘飞椽尾，椽头长度的2.5倍 
    qfc_wei_length = qfc_head_vector.length / con.flyrafter_HEAD_TILE_RATIO
    # todo: 应该用三角函数更精确的计算椽尾，这里略有出入，但影响不大
    qfc_wei_length_tilt = math.sqrt(math.pow(qfc_wei_length,2) \
                    + math.pow(con.flyrafter_H*dk,2))
    v5 = Vector((-qfc_wei_length_tilt,0,0))
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
    bmesh.ops.translate(bm, verts=verts, vec=(0, -con.flyrafter_H*dk, 0))
    # 移动所有点，居中
    for v in bm.verts:
        v.co.y += con.flyrafter_H*dk/2

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
    tilt_rot = qfcObj.rotation_euler.z - shear_rot.z 
    # 计算扭向位移
    tilt_offset_x = con.YUANCHUAN_D*dk / math.tan(tilt_rot)
    tilt_offset_z = tilt_offset_x * math.sin(qfcObj.rotation_euler.y)
    # 控制侧边9号线位移
    bm.edges.ensure_lookup_table() # 按序号访问前，必须先ensure
    tilt_edge = bm.edges[5] # 椽腰右侧边
    for v in tilt_edge.verts:
        v.co.x -= tilt_offset_x
        v.co.z -= tilt_offset_z

    bm.to_mesh(qfcObj.data)
    qfcObj.data.update()
    bm.free()

    # 把原点放在椽尾，方便后续计算椽头坐标
    # 把飞椽腰的v2点转换到global坐标系，并制定给3d cursor
    bpy.context.scene.cursor.location = qfcObj.matrix_world @ v5
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

    return qfcObj

# 营造翼角翘飞椽
def __buildCornerFlyrafter(buildingObj:bpy.types.Object,cornerRafterColl):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    # 屋顶根节点
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    cornerBeamObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_CORNER_BEAM)

    # 提取翼角椽定位线
    rafterCurveObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_CORNER_RAFTER_CURVE)

    # 根据椽子根数，计算曲线上的水平平分点
    cr_count = len(cornerRafterColl)
    yjc_verts = utils.getNurbsSegment(rafterCurveObj,cr_count)

    # 提取檐口线
    qfc_curve = __buildCornerFlyrafterCurve(buildingObj)
    # 根据椽子根数，计算曲线上的水平平分点
    qfc_verts = utils.getNurbsSegment(qfc_curve,cr_count)
    # 摆放翘飞椽
    last_chuan_head_point = qfc_verts[0] # 暂存相邻翘飞椽头
    last_chuan_mid_point = yjc_verts[0] # 暂存相邻翼角椽头
    # 收集翘飞椽对象，输出绘制翘飞椽望板
    qfc_collection = []
    for n in range(len(qfc_verts)):
        chuan_head_point  = qfc_verts[n]
        chuan_mid_point = yjc_verts[n]
        # 计算相邻椽头间的撇向
        head_shear_direction = chuan_head_point - last_chuan_head_point
        mid_shear_direction = chuan_mid_point - last_chuan_mid_point
        # 用于下一个循环迭代
        last_chuan_head_point = qfc_verts[n]
        last_chuan_mid_point = yjc_verts[n]
        qfc_Obj = __drawQiaoflyrafter(
            yjcObj = cornerRafterColl[n], # 对应的翼角椽对象
            qfc_head_point = qfc_verts[n], # 头在翘飞椽定位线上
            head_shear = head_shear_direction, # 椽头撇向
            mid_shear = mid_shear_direction, # 椽腰撇向
            name='翘飞椽',
            root_obj=roofRootObj
        )
        qfc_collection.append(qfc_Obj)
        mod = qfc_Obj.modifiers.new(name='角梁对称', type='MIRROR')
        mod.mirror_object = cornerBeamObj
        mod.use_axis[0] = False
        mod.use_axis[1] = True
        mod = qfc_Obj.modifiers.new(name='mirror', type='MIRROR')
        mod.mirror_object = roofRootObj
        mod.use_axis[0] = True
        mod.use_axis[1] = True

# 营造椽架（包括檐椽、飞椽、望板等）
# 根据屋顶样式，自动判断
def __buildRafterForAll(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    roofStyle = bData.roof_style
    useFlyrafter = bData.use_flyrafter
    useWangban = bData.use_wangban

    # 各种屋顶都有前后檐
    __buildRafter_FB(buildingObj,purlin_pos)    # 前后檐椽
    utils.outputMsg("Rafter body added")
    if useFlyrafter:  # 用户可选择不使用飞椽
        __buildFlyRafter(buildingObj,purlin_pos,'X') # 前后飞椽
        utils.outputMsg("Flyrafter body added")
    if useWangban:  # 用户可选择暂时不生成望板（更便于观察椽架形态）
        __buildWangban_FB(buildingObj,purlin_pos)   # 前后望板
        utils.outputMsg("Wangban added")
    
    # 庑殿、歇山的处理（硬山、悬山不涉及）
    if roofStyle in ('1','2'):
        # 营造角梁
        __buildCornerBeam(buildingObj,purlin_pos)
        utils.outputMsg("Corner Beam added")
        
        # 两山檐椽
        __buildRafter_LR(buildingObj,purlin_pos)    
        utils.outputMsg("Rafter body LR added")
        if useFlyrafter:
            # 两山飞椽
            __buildFlyRafter(buildingObj,purlin_pos,'Y') 
            utils.outputMsg("Flyrafter body LR added")
        if useWangban:
            # 两山望板
            __buildWangban_LR(buildingObj,purlin_pos)   
            utils.outputMsg("Wangban LR added")
        
        # 翼角部分
        # 营造小连檐
        __buildCornerRafterEave(buildingObj)
        utils.outputMsg("Rafter Eave added")
        # 营造翼角椽
        cornerRafterColl = __buildCornerRafter(buildingObj,purlin_pos)
        utils.outputMsg("Corner Rafter added")
        if useFlyrafter:
            # 大连檐
            __buildCornerflyrafterEave(buildingObj)
            utils.outputMsg("Corner Flyrafter Eave added")
            # 翘飞椽，以翼角椽为基准
            __buildCornerFlyrafter(buildingObj,cornerRafterColl)
            utils.outputMsg("Corner Flyrafter added")
    
    return

# 营造整个房顶
def buildRoof(buildingObj:bpy.types.Object):
    # 清理垃圾数据
    utils.delOrphan()    
    # 聚焦根目录
    utils.setCollection(con.ROOT_COLL_NAME)
    # 暂存cursor位置，注意要加copy()，否则传递的是引用
    old_loc = bpy.context.scene.cursor.location.copy()
    # 载入数据
    bData : acaData = buildingObj.ACA_data

    # 生成斗栱
    buildDougong.buildDougong(buildingObj)

    # 设定“屋顶层”根节点
    roofRootObj = __setRoofRoot(buildingObj)

    # 计算桁檩定位点
    purlin_pos = __getPurlinPos(buildingObj)
    
    # 摆放桁檩
    __buildPurlin(buildingObj,purlin_pos)
    utils.outputMsg("Purlin added")
    utils.redrawViewport()

    # 如果有斗栱，剔除挑檐桁
    # 在梁架、椽架、角梁的计算中不考虑挑檐桁
    rafter_pos = purlin_pos.copy()
    if bData.use_dg:
        del rafter_pos[0]

    # 摆放梁架
    __buildBeam(buildingObj,rafter_pos)
    utils.outputMsg("Beam added")
    utils.redrawViewport()

    # 摆放椽架（包括角梁、檐椽、望板、飞椽、里口木、大连檐等）
    __buildRafterForAll(buildingObj,rafter_pos)
    utils.outputMsg("Rafter added")
    utils.redrawViewport()
    
    # 重新聚焦根节点
    bpy.context.scene.cursor.location = old_loc # 恢复cursor位置
    utils.focusObj(buildingObj)
    return