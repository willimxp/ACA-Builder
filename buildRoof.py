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
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData

# 设置“屋顶层”根节点
def __setRoofRoot(buildingObj:bpy.types.Object)->bpy.types.Object:
    # 新建或清空根节点
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    if roofRootObj == None:
        # 创建屋顶根对象
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        roofRootObj = bpy.context.object
        roofRootObj.name = "屋顶层"
        roofRootObj.parent = buildingObj
        roofRootObj.ACA_data['aca_obj'] = True
        roofRootObj.ACA_data['aca_type'] = con.ACA_TYPE_ROOF_ROOT
        # 以挑檐桁下皮为起始点
        bData : acaData = buildingObj.ACA_data # 载入数据
        roof_base = bData.platform_height \
                    + bData.piller_height \
                    + bData.dg_height
        roofRootObj.location = (0,0,roof_base)
    else:
        utils.deleteHierarchy(roofRootObj)
    return roofRootObj

# 计算桁檩定位数据
# 集合中包含了每层桁檩相交的坐标点
# 可以据此定位前后檐和两山的桁檩
# 采用了举架公式进行计算
def __getPurlinPos(buildingObj:bpy.types.Object):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    
    # 计算屋顶基本参数 ===================
    # 步架数
    rafterstep_count = bData.rafter_count

    # 举架坐标集，保存了各层桁在檐面和山面的交叉点坐标
    purlin_pos = []

    # 1、定位挑檐桁
    # 出檐包括通进深的一半+斗栱出踩（每个拽架3斗口）
    dg_jump_length = bData.dg_extend
    purlin_x = bData.x_total/2 + dg_jump_length
    purlin_y = bData.y_total/2 + dg_jump_length
    # 屋顶起点root在挑檐枋上皮，挑檐桁架于其上
    purlin_z = con.HENG_TIAOYAN_D / 2 * dk
    purlin_pos.append(Vector((purlin_x,purlin_y,purlin_z)))

    # 2、定位正心桁
    # 水平推斗栱出踩
    purlin_x = bData.x_total/2
    purlin_y = bData.y_total/2
    # 垂直按举架系数
    purlin_z += dg_jump_length * con.LIFT_RATIO[0] \
        - (con.HENG_COMMON_D-con.HENG_TIAOYAN_D)*dk/2   # 减去挑檐桁、正心桁的直径差，向下压实
    purlin_pos.append(Vector((purlin_x,purlin_y,purlin_z)))

    # 3、定位金桁、脊桁
    # 步架宽
    # 檐面步架宽根据步架数平均分
    # 山面的步架宽度后续会进行推山处理，而从下自上依次递减
    rafterstep_span = bData.y_total / rafterstep_count
    # 继续根据举架系数，逐个桁架上举
    for n in range(int(rafterstep_count/2)):
        # ================================
        # 推山做法，仅清代庑殿建筑使用，其他朝代未见，其他屋顶类型不涉及
        # 推山：面阔方向推一步架，第一架不推山
        if n==0:
            purlin_x -= rafterstep_span
        else:
            purlin_x -= rafterstep_span * 0.9**n
        # 进深方向推一步架  
        purlin_y -= rafterstep_span
        # ====================================
        # 垂直推一步架乘举架系数
        # 举架做法，采用了清则例做法，逐级上举
        purlin_z += rafterstep_span * con.LIFT_RATIO[n]
        purlin_pos.append(Vector((purlin_x,purlin_y,purlin_z)))

    # 返回桁檩定位数据集
    return purlin_pos

# 营造桁檩
def __buildPurlin(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK

    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    
    # 布置桁,根据上述计算的purlin_pos数据，批量放置桁对象
    for n in range(len(purlin_pos)) :
        pCross = purlin_pos[n]
        if n==0:
            # 挑檐桁直径
            purlin_r = con.HENG_TIAOYAN_D / 2 * dk
        else:   # 金桁、脊桁
            # 其他桁直径（正心桁、金桁、脊桁）
            purlin_r = con.HENG_COMMON_D / 2 * dk
        # 除最后一根脊桁的处理
        if n!=len(purlin_pos)-1:
            # 桁的长度：山面按檐面坐标算，檐面按山面坐标算（自动考虑了推山因素）,多加一桁径
            # 本来挑檐桁只增了挑檐桁径，但做出来后，老角梁于挑檐桁交叉明显，所以统一改成了桁径
            purlin_length_x = pCross.x * 2 + con.HENG_COMMON_D * dk * 2
            purlin_length_y = pCross.y * 2 + con.HENG_COMMON_D * dk * 2
            # 前后桁，包括挑檐桁、正心桁、金桁
            hengFB = utils.addCylinderHorizontal(
                    radius = purlin_r, 
                    depth = purlin_length_x,
                    location = (0,pCross.y,pCross.z), 
                    name = "桁-前后",
                    root_obj = roofRootObj
                )
            # 挑檐桁、正心桁、金桁做Y镜像
            mod = hengFB.modifiers.new(name='mirror', type='MIRROR')
            mod.mirror_object = roofRootObj
            mod.use_axis[0] = False
            mod.use_axis[1] = True
            # 两山桁，两山没有脊桁
            hengLR = utils.addCylinderHorizontal(
                    radius = purlin_r, 
                    depth = purlin_length_y,
                    location = (pCross.x,0,pCross.z), 
                    rotation=(0, 0, math.radians(90)), 
                    name = "桁-两山",
                    root_obj = roofRootObj
                )
            # 添加镜像
            mod = hengLR.modifiers.new(name='mirror', type='MIRROR')
            mod.mirror_object = roofRootObj
            mod.use_axis[0] = True
            mod.use_axis[1] = False
        else: # 最后一根脊桁的处理
            # 脊桁左右只出半桁径，合计一桁径
            purlin_length_x = pCross.x * 2 + con.HENG_COMMON_D * dk
            purlin_length_y = pCross.y * 2 + con.HENG_COMMON_D * dk
            # 脊桁
            hengFB = utils.addCylinderHorizontal(
                    radius = purlin_r, 
                    depth = purlin_length_x,
                    location = (0,pCross.y,pCross.z), 
                    name = "桁-前后",
                    root_obj = roofRootObj
                )
            # 添加伏脊木
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
    return

# 营造梁架
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
    for x in range(1,len(net_x)-1):# 这里为庑殿，山面柱头不设梁架
        # 纵向循环每一层梁架
        for n in range(1,len(purlin_pos)):  # 跳过第一根挑檐桁
            # 添加横梁
            if n!=len(purlin_pos)-1: # 排除脊槫
                # 定位
                beam_loc = Vector((
                    net_x[x],   # X向随槫交点依次排列
                    0,          # Y向居中
                    purlin_pos[n].z - con.BEAM_HEIGHT*pd/2
                ))
                beamCopyObj = utils.copyObject(
                            sourceObj= beamObj,
                            name="直梁",
                            location=beam_loc,
                            parentObj=roofRootObj
                        )
                beamCopyObj.dimensions = Vector((
                    con.BEAM_DEEPTH*pd,
                    purlin_pos[n].y*2 + con.HENG_COMMON_D*dk*2,
                    con.BEAM_HEIGHT*pd
                ))

                # 在梁上添加蜀柱
                if n == len(purlin_pos)-2:
                    # 直接支撑到脊槫
                    shuzhu_height = purlin_pos[n+1].z - purlin_pos[n].z
                else:
                    # 支撑到上下两根梁之间
                    shuzhu_height = purlin_pos[n+1].z \
                        - purlin_pos[n].z \
                        - con.BEAM_HEIGHT*pd
                shuzhu_loc = Vector((
                    net_x[x],   # X向随槫交点依次排列
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
                    con.BEAM_DEEPTH*pd,
                    con.BEAM_DEEPTH*pd,
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

# 营造椽子
def __buildFBRafter(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    
    # 计算檐面椽当（注意，前后檐与两山的椽当可能不一样）
    # 正身椽平铺到金桁(计算半幅，然后镜像)
    rafter_gap_x = __getRafterGap(buildingObj,
                    rafter_tile_width=purlin_pos[2].x)
    # 存入数据集，后续做翼角等会复用
    bData.rafter_fb_gap = rafter_gap_x

    # 根据桁数组循环计算各层椽架
    # 忽略数组中的挑檐桁，只连接正心桁、下金桁、上金桁、脊桁等
    # 最后将第一层檐椽按“檐总平出”延长
    for n in range(1,len(purlin_pos)-1):
        # 定位前后椽
        rafter_end = Vector((rafter_gap_x/2,    # 椽当坐中，所以第一根在半椽当位置           
                            purlin_pos[n].y,
                            purlin_pos[n].z))
        rafter_start = Vector((rafter_gap_x/2,
                            purlin_pos[n+1].y,
                            purlin_pos[n+1].z))
        fbRafterObj = utils.addCylinderBy2Points(
            radius = con.YUANCHUAN_D/2*dk,
            start_point = rafter_start,
            end_point = rafter_end,
            name="檐椽.前后",
            root_obj = roofRootObj
        )
        fbRafterObj.ACA_data['aca_obj'] = True
        fbRafterObj.ACA_data['aca_type'] = con.ACA_TYPE_RAFTER
        # 上移，与桁檩上皮相切
        bpy.ops.transform.translate(
            value = (0,0,(con.HENG_COMMON_D+con.YUANCHUAN_D)*dk/2),
            orient_type = con.OFFSET_ORIENTATION # GLOBAL/LOCAL ?
        )  
        
        # 檐面和山面的檐椽延长，按檐总平出加斜计算
        if n==1:
            # 檐椽斜率（圆柱体默认转90度）
            yan_rafter_angle = math.cos(fbRafterObj.rotation_euler.y)
            # 檐总平出=斗栱平出+14斗口檐椽平出（暂不考虑7斗口的飞椽平出）
            yan_rafter_ex = (bData.dg_extend + con.YANCHUAN_EX)* dk
            # 檐椽加斜长度
            fbRafterObj.dimensions.x += yan_rafter_ex / yan_rafter_angle
            utils.applyTransfrom(fbRafterObj,use_scale=True) # 便于后续做望板时获取真实长度

        # 【手工修正】：没有理论依据，纯粹为了好看
        # 脑椽延长，达到伏脊木的位置
        if n== len(purlin_pos)-2 :
            naochuan_adj = con.HENG_COMMON_D/2*dk   # 手工设定了一个调节值，瞎估的
            fbRafterObj.dimensions.x += naochuan_adj
            utils.applyTransfrom(fbRafterObj,use_scale=True)
            bpy.ops.transform.translate(
                value = (-naochuan_adj,0,0),
                orient_type = con.OFFSET_ORIENTATION 
            ) 

        # 平铺Array
        # 根据椽当=1椽径估算，取整
        if n==1:
            # 檐椽平铺到上层桁交点
            rafter_tile_x = purlin_pos[n+1].x  
        else:
            # 其他椽架平铺到下层桁交点，然后切割
            rafter_tile_x = purlin_pos[n].x
        utils.addModifierArray(
            object=fbRafterObj,
            count=math.floor(rafter_tile_x /rafter_gap_x),
            offset=(0,-rafter_gap_x,0)
        )
        
        # 裁剪，檐椽不做裁剪（所以，檐椽的array modifier没有被apply）
        if n!=1:
            utils.addBisect(
                    object=fbRafterObj,
                    pStart=buildingObj.matrix_world @ purlin_pos[n],
                    pEnd=buildingObj.matrix_world @ purlin_pos[n+1],
                    pCut=buildingObj.matrix_world @ purlin_pos[n] - \
                        Vector((con.JIAOLIANG_Y*dk/2,0,0)),
                    clear_outer=True
            ) 
        
        # 镜像
        utils.addModifierMirror(
            object=fbRafterObj,
            mirrorObj=roofRootObj,
            use_axis=(True,True,False)
        )

    return

# 营造两山椽子（硬山、悬山建筑不涉及）
def __buildLRRafter(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)

    # 计算山面椽当
    # 正身椽平铺到金桁(计算半幅，然后镜像)
    rafter_gap_y = __getRafterGap(buildingObj,
                    rafter_tile_width=purlin_pos[2].y)

    # 根据桁数组循环计算各层椽架
    # 忽略数组中的挑檐桁，只连接正心桁、下金桁、上金桁、脊桁等
    # 最后将第一层檐椽按“檐总平出”延长
    for n in range(1,len(purlin_pos)-1):
        # 定位两山椽
        rafter_end = Vector((purlin_pos[n].x,   # 下层桁
                            rafter_gap_y/2,                   # Y偏移半椽当
                            purlin_pos[n].z))
        rafter_start = Vector((purlin_pos[n+1].x,   # 上层桁           
                            rafter_gap_y/2,                   # Y偏移半椽当
                            purlin_pos[n+1].z))   # 金桁Z
        lrRafterObj = utils.addCylinderBy2Points(
            radius = con.YUANCHUAN_D/2*dk,
            start_point = rafter_start,
            end_point = rafter_end,
            name="檐椽.两山",
            root_obj = roofRootObj
        )
        # 上移，与桁檩上皮相切
        bpy.ops.transform.translate(
            value = (0,0,(con.HENG_COMMON_D+con.YUANCHUAN_D)*dk/2),
            orient_type = con.OFFSET_ORIENTATION # GLOBAL/LOCAL ?
        )   
        
        # 檐面和山面的檐椽延长，按檐总平出加斜计算
        if n==1:
            # 檐椽斜率（圆柱体默认转90度）
            yan_rafter_angle = math.cos(lrRafterObj.rotation_euler.y)
            # 檐总平出=斗栱平出+14斗口檐椽平出（暂不考虑7斗口的飞椽平出）
            yan_rafter_ex = (bData.dg_extend + con.YANCHUAN_EX)* dk
            # 檐椽加斜长度
            lrRafterObj.dimensions.x += yan_rafter_ex / yan_rafter_angle
            utils.applyTransfrom(lrRafterObj,use_scale=True) # 便于后续做望板时获取真实长度

        # 平铺Array
        # 两山
        if n==1:
            # 檐椽平铺到上层桁交点 
            rafter_tile_y = purlin_pos[n+1].y  
        else:
            # 其他椽架平铺到下层桁交点，然后切割
            rafter_tile_y = purlin_pos[n].y        
        utils.addModifierArray(
            object=lrRafterObj,
            count=math.floor(rafter_tile_y /rafter_gap_y),
            offset=(0,rafter_gap_y,0)
        )
        
        # 裁剪，檐椽不做裁剪（所以，檐椽的array modifier没有被apply）
        if n!=1:
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

# 根据老角梁，绘制对应子角梁
# 基于“冲三翘四”的原则计算
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
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER)
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
def __buildCornerBeam(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT)
    
    # 计算角梁数据，忽略第一个挑檐桁交点，直接从正心桁到脊桁分段生成
    cb_collection = []
    for n in range(1,len(purlin_pos)-1) :
        if n == 1:  #翼角角梁
            # 老角梁，大式带斗拱的建筑采用扣金做法
            # 老角梁尾压在金桁下
            pEnd = Vector(purlin_pos[n+1]) \
                - Vector((0,0,con.JIAOLIANG_H*dk*con.JIAOLIANG_WEI_KOUJIN))
            # 计算老角梁头先放在正心桁交点上，后续根据檐出、冲出延长
            pStart = Vector(purlin_pos[n]) \
                + Vector((0,0,con.JIAOLIANG_H*dk*con.JIAOLIANG_HEAD_YAJIN))
            cb_collection.append((pStart,pEnd,'老角梁'))
        else:
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
            ex_length = bData.dg_extend \
                + con.YANCHUAN_EX*dk \
                + (bData.chong-1)*con.YUANCHUAN_D*dk \
                + con.QUETAI*dk
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
    # 聚焦根目录
    utils.setCollection(con.ROOT_COLL_NAME)
    # 暂存cursor位置，注意要加copy()，否则传递的是引用
    old_loc = bpy.context.scene.cursor.location.copy()

    # 设定“屋顶层”根节点
    roofRootObj = __setRoofRoot(buildingObj)
    
    # 计算桁檩定位点
    purlin_pos = __getPurlinPos(buildingObj)
    
    # 摆放桁檩
    __buildPurlin(buildingObj,purlin_pos)
    utils.outputMsg("Purlin added")

    # 摆放梁架
    __buildBeam(buildingObj,purlin_pos)
    utils.outputMsg("Beam added")

    # 摆放椽架
    __buildFBRafter(buildingObj,purlin_pos)
    utils.outputMsg("FBRafter added")
    __buildLRRafter(buildingObj,purlin_pos)
    utils.outputMsg("LRRafter added")

    # 摆放角梁
    __buildCornerBeam(buildingObj,purlin_pos)
    
    # 重新聚焦根节点
    bpy.context.scene.cursor.location = old_loc # 恢复cursor位置
    utils.focusObj(buildingObj)
    return