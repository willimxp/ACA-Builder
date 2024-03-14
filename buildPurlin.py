# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   椽架的营造
import bpy
import math
from mathutils import Vector

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
        utils.delete_hierarchy(roofRootObj)
    return roofRootObj

# 计算桁檩定位数据
# 集合中包含了每层桁檩相交的坐标点
# 可以据此定位前后檐和两山的桁檩
# 采用了举架公式进行计算
def __getPurlinPos(buildingObj:bpy.types.Object):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    if bData.aca_type != con.ACA_TYPE_BUILDING:
        utils.ShowMessageBox("错误，输入的不是建筑根节点")
        return
    dk = bData.DK
    
    # 计算屋顶基本参数 ===================
    # 步架数
    rafterstep_count = bData.rafter_step

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
    purlin_x -= dg_jump_length
    purlin_y -= dg_jump_length
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
    for n in range(len(con.LIFT_RATIO)):
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
    if bData.aca_type != con.ACA_TYPE_BUILDING:
        utils.ShowMessageBox("错误，输入的不是建筑根节点")
        return
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

# 营造整个房顶
def buildRoof(buildingObj:bpy.types.Object):
    # 聚焦根目录
    utils.setCollection(con.ROOT_COLL_NAME)

    # 设定“屋顶层”根节点
    roofRootObj = __setRoofRoot(buildingObj)
    
    # 计算桁檩定位点
    purlin_pos = __getPurlinPos(buildingObj)
    
    # 摆放桁檩
    __buildPurlin(buildingObj,purlin_pos)

    # 摆放梁架
    __buildBeam(buildingObj,purlin_pos)
    
    # 重新聚焦根节点
    utils.focusObj(buildingObj)
    return