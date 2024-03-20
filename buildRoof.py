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
        utils.deleteHierarchy(roofRootObj,with_parent=True)
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
def __buildBeam(buildingObj:bpy.types.Object,purlinPos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    # 如果有斗栱，剔除挑檐桁的干扰
    purlin_pos = purlinPos.copy()
    if bData.use_dg:
        del purlin_pos[0]
    
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

# 营造前后檐椽子
# 庑殿、歇山可自动裁切
def __buildRafter_FB(buildingObj:bpy.types.Object,purlinPos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    # 如果有斗栱，剔除挑檐桁的干扰
    purlin_pos = purlinPos.copy()
    if bData.use_dg:
        del purlin_pos[0]
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
                yan_rafter_ex += bData.dg_extend* dk
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

    return

# 营造两山椽子
# 硬山、悬山建筑不涉及
def __buildRafter_LR(buildingObj:bpy.types.Object,purlinPos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    # 如果有斗栱，剔除挑檐桁的干扰
    purlin_pos = purlinPos.copy()
    if bData.use_dg:
        del purlin_pos[0]
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
                yan_rafter_ex += bData.dg_extend* dk
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
    
    return

# 根据檐椽，绘制对应飞椽
# 基于“一飞二尾五”的原则计算
def __drawFeiChuan(yanRafterObj,name,root_obj):
    # 载入数据
    buildingObj = utils.getAcaParent(yanRafterObj,con.ACA_TYPE_BUILDING)
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    
    # 计算椽头坐标
    yanchuan_head_co = utils.getObjectHeadPoint(yanRafterObj,
            eval=False,
            is_symmetry=(True,True,False))
    utils.showVector(yanchuan_head_co,root_obj)
    # 将cursor放置在檐椽头，做为bmesh的origin
    bpy.context.scene.cursor.location = yanchuan_head_co

    # 任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add()
    feiChuanObj = bpy.context.object
    feiChuanObj.name = name
    feiChuanObj.parent = root_obj
    # 将飞椽与檐椽对齐旋转角度
    feiChuanObj.rotation_euler = yanRafterObj.rotation_euler 

    # 创建bmesh
    bm = bmesh.new()
    # 各个点的集合
    vectors = []

    # 第1点在飞椽腰，对齐了檐椽头，分割飞椽头、尾的转折点
    v1 = Vector((0,0,0))
    vectors.append(v1)

    # 第2点在飞椽尾
    # 飞尾平出：7斗口*2.5=17.5斗口
    feiwei_pingchu = con.FEICHUAN_EX / con.FEICHUAN_HEAD_TILE_RATIO * dk
    # 飞尾在檐椽方向加斜
    yanChuan_angle = feiChuanObj.rotation_euler.y   # 檐椽斜角
    feiwei_loc = feiwei_pingchu / math.cos(yanChuan_angle)    
    v2 = Vector((-feiwei_loc,0,0)) # 飞椽尾的坐标
    vectors.append(v2)

    # 第3点在飞椽腰的上沿
    v3 = Vector((0,0,con.FEICHUAN_H*dk))
    # 飞椽仰角（基于飞尾楔形的对边为飞椽高）
    feichuan_angle_change = -math.asin(con.FEICHUAN_H*dk / feiwei_loc)
    # 随椽头昂起
    v3.rotate(Euler((0,feichuan_angle_change,0),'XYZ'))
    vectors.append(v3)

    # 第4点在飞椽头上沿
    feiwei_length = feiwei_loc * math.cos(feichuan_angle_change)
    feihead_length = feiwei_length * con.FEICHUAN_HEAD_TILE_RATIO
    v4 = Vector((feihead_length,0,con.FEICHUAN_H*dk))
    # 随椽头昂起
    v4.rotate(Euler((0,feichuan_angle_change,0),'XYZ'))
    vectors.append(v4)

    # 第5点在飞椽头下檐
    v5 = Vector((feihead_length,0,0))
    # 随椽头昂起
    v5.rotate(Euler((0,feichuan_angle_change,0),'XYZ'))
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
    feiwei_face = bm.faces.new((vertices[0],vertices[1],vertices[2])) # 飞尾
    feihead_face =bm.faces.new((vertices[0],vertices[2],vertices[3],vertices[4])) # 飞头

    # 挤出厚度
    return_geo = bmesh.ops.extrude_face_region(bm, geom=[feiwei_face,feihead_face])
    verts = [elem for elem in return_geo['geom'] if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, verts=verts, vec=(0, con.FEICHUAN_H*dk, 0))

    # 移动所有点，居中
    for v in bm.verts:
        v.co.y -= con.FEICHUAN_H*dk/2
    
    # 确保face normal朝向
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(feiChuanObj.data)
    feiChuanObj.data.update()
    bm.free()

    # 向上位移半檐椽+一望板
    bpy.ops.transform.translate(
            value = (0,0,(con.YUANCHUAN_D/2+con.WANGBAN_H)*dk),
            orient_type = 'GLOBAL' # GLOBAL/LOCAL ?
    )

    # 优化飞椽的matrix
    # 把原点放在椽尾，方便后续计算椽头坐标
    # 把飞椽腰的v2点转换到global坐标系，并制定给3d cursor
    # bpy.context.scene.cursor.location = feiChuanObj.matrix_world @ v2
    # bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    origin = feiChuanObj.matrix_world @ v2
    utils.setOrigin(feiChuanObj,origin)

    # 把旋转角度与上皮对齐，方便后续摆放压椽尾望板
    change_rot = v4-v3
    # 已封装了一个方法
    utils.changeOriginRotation(change_rot,feiChuanObj)
    return feiChuanObj

# 营造前后檐-飞椽（以及里口木等附属构件)
# 小式建筑中，可以不使用飞椽
def __buildRafterFei_FB(buildingObj:bpy.types.Object,purlinPos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    
    # 一、构造飞椽
    # 以檐椽对象为参考基准
    yanRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_FB)
    feiChuanObj:bpy.types.Object = \
            __drawFeiChuan(yanRafterObj,
                        name='飞椽.前后',
                        root_obj=roofRootObj)  
    # 复制檐椽的modifier到飞椽上，相同的array，相同的mirror
    utils.copyModifiers(from_0bj=yanRafterObj,to_obj=feiChuanObj)  

    # 二、构造里口木
    # 如果有斗栱，剔除挑檐桁的干扰
    purlin_pos = purlinPos.copy()
    if bData.use_dg:
        del purlin_pos[0]
    # 获取金桁位置，做为里口木的宽度
    jinhengPos = purlin_pos[1]
    yanchuan_head_co = utils.getObjectHeadPoint(yanRafterObj,
            eval=True,
            is_symmetry=(True,True,False))
    # 里口木相对于檐口的位移，与檐椽上皮相切，并内收一个雀台，
    offset = Vector((-(con.QUETAI+con.LIKOUMU_Y/2)*dk, # 内收一个雀台
                    0,
                    (con.YUANCHUAN_D/2+con.LIKOUMU_H/2)*dk)) # 从椽中上移
    offset.rotate(yanRafterObj.rotation_euler)
    lkm_pos:Vector = (yanchuan_head_co + offset)*Vector((0,1,1))
    lkm_scale = (jinhengPos.x * 2,  # 连接左右两个闸挡板
                    con.LIKOUMU_Y*dk,
                    con.LIKOUMU_H*dk
                    )
    bpy.ops.mesh.primitive_cube_add(size=1,
            location = lkm_pos,
            rotation = (-yanRafterObj.rotation_euler.y,0,0),
            scale = lkm_scale
            )
    LKMObj = bpy.context.object
    LKMObj.name = "里口木.檐面"
    LKMObj.parent = roofRootObj
    utils.addModifierMirror(
        object=LKMObj,
        mirrorObj=roofRootObj,
        use_axis=(False,True,False)
    )
    return

# 营造两山飞椽(及里口木等附件)
# 小式建筑中，可以不使用飞椽
# 硬山、悬山，不涉及两山飞椽
def __buildRafterFei_LR(buildingObj:bpy.types.Object,purlinPos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    
    # 一、构造飞椽
    # 获取檐椽对象
    yanRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_LR)
    feiChuanObj:bpy.types.Object = \
            __drawFeiChuan(yanRafterObj,
                        name='飞椽.两山',
                        root_obj=roofRootObj)  
    # 复制檐椽的modifier到飞椽上，相同的array，相同的mirror
    utils.copyModifiers(from_0bj=yanRafterObj,to_obj=feiChuanObj)  

    # 二、构造里口木
    # 如果有斗栱，剔除挑檐桁的干扰
    purlin_pos = purlinPos.copy()
    if bData.use_dg:
        del purlin_pos[0]
    # 获取金桁位置，做为里口木的长度
    jinhengPos = purlin_pos[1]
    yanchuan_head_co = utils.getObjectHeadPoint(yanRafterObj,
            eval=True,
            is_symmetry=(True,True,False))
    # 里口木相对于檐口的位移，与檐椽上皮相切，并内收一个雀台，
    offset = Vector((-(con.QUETAI+con.LIKOUMU_Y/2)*dk, # 内收一个雀台
                    0,
                    (con.YUANCHUAN_D/2+con.LIKOUMU_H/2)*dk)) # 从椽中上移
    offset.rotate(yanRafterObj.rotation_euler)
    lkm_pos:Vector = (yanchuan_head_co + offset)*Vector((1,0,1))
    lkm_scale = (jinhengPos.y * 2,  # 连接左右两个闸挡板
                    con.LIKOUMU_H*dk,
                    con.LIKOUMU_Y*dk)
    bpy.ops.mesh.primitive_cube_add(size=1,
            location = lkm_pos,
            rotation = (
                yanRafterObj.rotation_euler.y+math.radians(90),
                0,math.radians(90)),
            scale = lkm_scale
            )
    LKMObj = bpy.context.object
    LKMObj.name = "里口木.山面"
    LKMObj.parent = roofRootObj
    utils.addModifierMirror(
        object=LKMObj,
        mirrorObj=roofRootObj,
        use_axis=(True,False,False)
    )
    return 

# 营造前后檐望板
# 与椽架代码解耦，降低复杂度
def __buildWangban_FB(buildingObj:bpy.types.Object,purlinPos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    # 如果有斗栱，剔除挑檐桁的干扰
    purlin_pos = purlinPos.copy()
    if bData.use_dg:
        del purlin_pos[0]

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
                extend += bData.dg_extend* dk
            # 檐出加斜
            extend_hyp = extend/math.cos(angle)
            # 里口木避让（无需加斜）
            offset = (con.QUETAI            # 雀台避让
                    + con.LIKOUMU_Y)* dk    # 里口木避让
            # 加斜计算
            wangbanObj.dimensions.x += (extend_hyp - offset)
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

# 营造两山望板
# 与椽架代码解耦，降低复杂度
def __buildWangban_LR(buildingObj:bpy.types.Object,purlinPos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    # 如果有斗栱，剔除挑檐桁的干扰
    purlin_pos = purlinPos.copy()
    if bData.use_dg:
        del purlin_pos[0]

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
        utils.outputMsg("wangban_width = " + str(width))
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
                extend += bData.dg_extend* dk
            # 檐出加斜
            extend_hyp = extend/math.cos(angle)
            # 里口木避让（无需加斜）
            offset = (con.QUETAI            # 雀台避让
                    + con.LIKOUMU_Y)* dk    # 里口木避让
            # 加斜计算
            wangbanObj.dimensions.x += (extend_hyp - offset)
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

# 营造椽架
# 根据屋顶样式，自动判断
# 可选择是否需要飞椽、望板
def __buildRafter(buildingObj:bpy.types.Object,purlin_pos,
                  useFei=False,
                  useWangban=False):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    roofStyle = bData.roof_style
    useFei = bData.with_feichuan

    __buildRafter_FB(buildingObj,purlin_pos)    # 前后檐椽
    if useFei:
        __buildRafterFei_FB(buildingObj,purlin_pos) # 前后飞椽
    if useWangban:
        __buildWangban_FB(buildingObj,purlin_pos)   # 前后望板
    
    if roofStyle in ('1','2'):
        __buildRafter_LR(buildingObj,purlin_pos)    # 两山檐椽
        if useFei:
            __buildRafterFei_LR(buildingObj,purlin_pos) # 两山飞椽
        if useWangban:
            __buildWangban_LR(buildingObj,purlin_pos)   # 两山望板
        
    if roofStyle in ('3','4'):
        pass

# 根据老角梁，绘制对应子角梁
# 基于“冲三翘四”的原则计算
# 硬山、悬山不涉及
def __drawSmallCornerBeam(cornerBeamObj:bpy.types.Object,
                          name,
                          buildingObj:bpy.types.Object):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    
    # 计算老角梁头
    cornerBeam_head_co = utils.getObjectHeadPoint(
                            cornerBeamObj,
                            eval=True,
                            is_symmetry=(True,True,False)
                        )
    # 将cursor放置在檐椽头，做为bmesh的origin
    bpy.context.scene.cursor.location = cornerBeam_head_co
    
    # 任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add()
    smallCornerBeamObj = bpy.context.object
    smallCornerBeamObj.name = name
    smallCornerBeamObj.parent = roofRootObj
    smallCornerBeamObj.rotation_euler = cornerBeamObj.rotation_euler # 将飞椽与檐椽对齐旋转角度
    # 向上位移半角梁高度，达到老角梁上皮
    bpy.ops.transform.translate(
            value = (0,0,con.JIAOLIANG_H/2*dk),
            orient_type = 'LOCAL' # GLOBAL/LOCAL ?
    )   

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

    # 第5点，定位子角梁的梁头
    # 在local坐标系中计算子角梁头的绝对位置
    # 计算冲出后的X、Y坐标，由飞椽平出+冲1椽（老角梁已经冲了2椽）+雀台
    scb_ex_length = (con.FEICHUAN_EX + con.YUANCHUAN_D +con.QUETAI) * dk
    scb_abs_x = cornerBeam_head_co.x + scb_ex_length
    scb_abs_y = cornerBeam_head_co.y + scb_ex_length
    # 计算翘四后的Z坐标
    # 取檐椽头高度
    feiRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_FB)
    feiRafter_head_co = utils.getObjectHeadPoint(
                            feiRafterObj,
                            eval=True,
                            is_symmetry=(True,True,False)
                        )
    #showVector(bpy.context,root_obj,feiRafter_head_co)
    # 翘四: 从飞椽头上皮，到子角梁上皮，其中要补偿0.75斗口，即半椽，合计调整一椽（见汤书p171）
    scb_abs_z = feiRafter_head_co.z + con.YUANCHUAN_D*dk \
            + bData.qiqiao*con.YUANCHUAN_D*dk # 默认起翘4椽
    scb_abs_co = Vector((scb_abs_x,scb_abs_y,scb_abs_z))
    # 将该起翘点存入dataset，后续翼角可供参考（相对于root_obj）
    bData.roof_qiao_point = scb_abs_co
    # 将坐标转换到子角梁坐标系中
    v5 = smallCornerBeamObj.matrix_local.inverted() @ scb_abs_co
    vectors.append(v5)
    
    # 第6点，定位子角梁的梁头
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
    origin_world = smallCornerBeamObj.matrix_world @ new_origin
    utils.setOrigin(smallCornerBeamObj,origin_world)

    return smallCornerBeamObj

# 营造角梁（包括老角梁、子角梁、由戗）
def __buildCornerBeam(buildingObj:bpy.types.Object,purlinPos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    # 硬山、悬山不做角梁
    roofStyle = bData.roof_style
    if roofStyle in ('3','4'): return 
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    # 如果有斗栱，剔除挑檐桁的干扰
    purlin_pos = purlinPos.copy()
    if bData.use_dg:
        del purlin_pos[0]
    
    # 计算角梁数据，忽略第一个挑檐桁交点，直接从正心桁到脊桁分段生成
    cb_collection = []
    # 根据桁数组循环计算各层椽架
    for n in range(len(purlin_pos)-1) :
        if n == 0:  #翼角角梁
            if bData.with_feichuan:
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
            # 歇山不做其他角梁
            if roofStyle=='2': continue
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
            # 延长老角梁，（斗栱平出+檐椽平出+出冲+雀台）*加斜
            ex_length = con.YANCHUAN_EX*dk \
                + (bData.chong-1)*con.YUANCHUAN_D*dk \
                + con.QUETAI*dk
            if bData.use_dg: ex_length += bData.dg_extend
            # 水平面加斜45度
            ex_length = ex_length * math.sqrt(2)
            # 立面加斜老角梁扣金角度   
            ex_length = ex_length / math.cos(CornerBeamObj.rotation_euler.y)
            CornerBeamObj.dimensions.x += ex_length
            utils.applyTransfrom(CornerBeamObj,use_scale=True)
            
            if bData.with_feichuan:
                # 绘制子角梁
                smallCornerBeamObj = __drawSmallCornerBeam(CornerBeamObj,'仔角梁',buildingObj)
                utils.addModifierMirror(object=smallCornerBeamObj,
                            mirrorObj=roofRootObj,
                            use_axis=(True,True,False))

        # 添加镜像
        utils.addModifierMirror(object=CornerBeamObj,
                            mirrorObj=roofRootObj,
                            use_axis=(True,True,False))
    
    return

# 营造整个房顶
def buildRoof(buildingObj:bpy.types.Object):
    # 清理垃圾数据
    utils.delOrphan()    
    # 聚焦根目录
    utils.setCollection(con.ROOT_COLL_NAME)
    # 暂存cursor位置，注意要加copy()，否则传递的是引用
    old_loc = bpy.context.scene.cursor.location.copy()

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

    # 摆放梁架
    __buildBeam(buildingObj,purlin_pos)
    utils.outputMsg("Beam added")
    utils.redrawViewport()

    # 摆放椽架（包括檐椽、飞椽、里口木等）
    __buildRafter(buildingObj,purlin_pos,useFei=True,useWangban=True)
    utils.outputMsg("Rafter added")
    utils.redrawViewport()

    # 摆放角梁
    __buildCornerBeam(buildingObj,purlin_pos)
    utils.outputMsg("CornerBeam added")
    # utils.redrawViewport()
    
    # 重新聚焦根节点
    bpy.context.scene.cursor.location = old_loc # 恢复cursor位置
    utils.focusObj(buildingObj)
    return