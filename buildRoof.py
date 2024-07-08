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
from . import buildFloor
from . import buildDougong
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
        # 创建根节点
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        roofRootObj = bpy.context.object
        roofRootObj.name = '屋顶层'
        roofRootObj.parent = buildingObj
        roofRootObj.ACA_data['aca_obj'] = True
        roofRootObj.ACA_data['aca_type'] = con.ACA_TYPE_ROOF_ROOT

    # 以挑檐桁下皮为起始点
    bData : acaData = buildingObj.ACA_data # 载入数据
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    tile_base = bData.platform_height \
                + bData.piller_height
    # 如果有斗栱，抬高斗栱高度
    if bData.use_dg:
        tile_base += bData.dg_height
        # 是否使用平板枋
        if bData.use_pingbanfang:
            tile_base += con.PINGBANFANG_H*dk
    else:
        # 以大梁抬升金桁垫板高度，即为挑檐桁下皮位置
        tile_base += con.BOARD_HENG_H*dk
    
    roofRootObj.location = (0,0,tile_base)       

    return roofRootObj

# 设置“梁椽望”根节点
def __addRafterRoot(buildingObj:bpy.types.Object)->bpy.types.Object:
    # 设置目录
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('梁椽望',parentColl=buildingColl) 
    
    # 新建或清空根节点
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    if rafterRootObj == None:
        # 创建梁椽望根对象
        bpy.ops.object.empty_add(
            type='PLAIN_AXES',location=(0,0,0))
        rafterRootObj = bpy.context.object
        rafterRootObj.name = "梁椽望"
        rafterRootObj.ACA_data['aca_obj'] = True
        rafterRootObj.ACA_data['aca_type'] = con.ACA_TYPE_RAFTER_ROOT
        # 绑定在屋顶根节点下
        roofRootObj = utils.getAcaChild(
            buildingObj,con.ACA_TYPE_ROOF_ROOT)
        rafterRootObj.parent = roofRootObj
    else:
        utils.deleteHierarchy(rafterRootObj)
        utils.focusCollByObj(rafterRootObj)

    return rafterRootObj

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

    # 1、三组举折系数，可供选择
    lift_ratio = []
    if bData.juzhe == '0':
        lift_ratio = con.LIFT_RATIO_DEFAULT
    if bData.juzhe == '1':
        lift_ratio = con.LIFT_RATIO_BIG
    if bData.juzhe == '2':
        lift_ratio = con.LIFT_RATIO_SMALL

    # 2、步架宽度：进深/步架数（卷棚等减3椽）
    # 卷棚顶：顶层桁檩间距3椽径，要从进深中减去后，平分椽架
    if roofStyle == con.ROOF_XUANSHAN_JUANPENG:
        rafterSpan = (bData.y_total 
            - con.JUANPENG_SPAN*dk)/bData.rafter_count
    # 盝顶：直接采用用户设置的参数
    elif roofStyle == con.ROOF_LUDING:
        rafterSpan = bData.luding_rafterspan
    # 其他屋顶的步架宽度：按椽架数平分进深长度
    # 包括庑殿、歇山、悬山、硬山
    else:
        rafterSpan = bData.y_total/bData.rafter_count

    # 3、起始点
    purlinWidth = bData.x_total/2
    purlinDeepth = bData.y_total/2
    # 屋顶起点root在挑檐枋下皮，所以初始即上移半桁
    purlinHeight = con.HENG_TIAOYAN_D/2*dk
    # 0.1、起始点微调
    # 硬山桁檩：做到梁的外皮
    if roofStyle == con.ROOF_YINGSHAN:
        purlinWidth += con.BEAM_DEEPTH*pd/2
    # 悬山（卷棚）：从山柱中加檐出（14斗口）
    if roofStyle in (
            con.ROOF_XUANSHAN,
            con.ROOF_XUANSHAN_JUANPENG):
        purlinWidth += con.YANCHUAN_EX*dk

    # 开始构造槫子数据
    purlin_pos = []

    # 1、定位挑檐桁（仅适用于有斗栱）  
    if bData.use_dg:
        # 为了不改动起始点，另用变量计算挑檐桁
        purlinWidth_dg = purlinWidth
        # 庑殿、歇山、盝顶，做两山斗栱出跳
        if roofStyle in (
                con.ROOF_WUDIAN,
                con.ROOF_XIESHAN,
                con.ROOF_LUDING):
            purlinWidth_dg = purlinWidth + bData.dg_extend
        # 插入挑檐桁等位点
        purlin_pos.append(Vector((
            purlinWidth_dg,
            purlinDeepth+ bData.dg_extend,
            purlinHeight)))  
        # 桁檩抬升挑檐桁举折
        purlinHeight += bData.dg_extend*lift_ratio[0]

    # 2、插入正心桁
    purlin_pos.append(Vector((
            purlinWidth,
            purlinDeepth,
            purlinHeight,
        )))

    # 3、循环定位下金桁、上金桁、脊桁   
    for n in range(int(bData.rafter_count/2)):
        # a、面阔X方向的推山
        # 硬山、悬山（卷棚）不推
        if roofStyle in (con.ROOF_YINGSHAN,
                         con.ROOF_XUANSHAN,
                         con.ROOF_XUANSHAN_JUANPENG):
            pass
        # 歇山，面阔方向，下金桁以上按收山法则
        elif (roofStyle == con.ROOF_XIESHAN
                and n>0):
                # 收山系统的选择，推荐一桁径以上，一步架以下
                # 当超出限制值时，自动设置为限制值
                shoushanLimit = (
                    rafterSpan              # 步架
                    - con.BOFENG_WIDTH*dk   # 博缝板
                    - con.XYB_WIDTH*dk      # 山花板
                    - con.BEAM_DEEPTH*pd/2  # 梁架中线
                    )
                if bData.shoushan > shoushanLimit:
                    bData['shoushan'] = shoushanLimit
                purlinWidth = (bData.x_total/2 
                        - con.BOFENG_WIDTH*dk   # 推山做到博缝板外皮
                        - bData.shoushan         # 用户自定义推山尺寸
                    )
        # 庑殿，下金桁以上，应用推山做法
        elif (roofStyle == con.ROOF_WUDIAN
            and n>0): 
            purlinWidth -= bData.tuishan**(n-1)*rafterSpan
        # 盝顶仅做到下金桁
        elif roofStyle== con.ROOF_LUDING and n >0:
            continue
        else:
            # 面阔、进深，每次推一个步架
            purlinWidth -= rafterSpan

        # b、进深Y方向的举折
        purlinDeepth -= rafterSpan

        # c、举折：举架高度 = 步架 * 举架系数
        purlinHeight += rafterSpan*lift_ratio[n]

        purlin_pos.append(Vector((
            purlinWidth,
            purlinDeepth,
            purlinHeight)))

    # 返回桁檩定位数据集
    return purlin_pos

# 檐桁为了便于彩画贴图，按开间逐一生成
# 其他的桁为了效率，还是贯通整做成一根
def __buildYanHeng(rafterRootObj:bpy.types.Object,
                   purlin_pos):
    # 载入数据
    buildingObj = utils.getAcaParent(
        rafterRootObj,con.ACA_TYPE_BUILDING)
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    # 获取开间、进深数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    # 挑檐桁交叉点
    purlin_cross = purlin_pos[0]

    # 收集待生成的挑檐桁
    purlinList = []
    
    # 计算转角出头
    hengExtend = 0
    # 悬山做固定的出跳
    if bData.roof_style in (
            con.ROOF_XUANSHAN,
            con.ROOF_XUANSHAN_JUANPENG):
        # 延长悬山的悬出
        hengExtend += con.YANCHUAN_EX*dk
    else:
        # 四坡顶为了垂直交扣，做一桁径的出梢
        # 硬山为了承托斗栱，也做了出梢
        if bData.use_dg:
            hengExtend += con.HENG_EXTEND*dk /2
    # 四坡顶用斗拱时，增加斗栱出跳
    if bData.roof_style in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_LUDING):
        if bData.use_dg:
            hengExtend += bData.dg_extend

    # 前后檐排布
    for n in range(len(net_x)-1):
        length = net_x[n+1] - net_x[n]
        loc = Vector(((net_x[n+1] + net_x[n])/2,
               purlin_cross.y,
               purlin_cross.z))
        # 转角出头
        if n in (0,len(net_x)-2):
            length += hengExtend
            sign = utils.getSign(net_x[n])
            loc += Vector((hengExtend/2*sign,0,0))
        purlinList.append(
            {'len':length,
             'loc':loc,
             'rot':0,
             'mirror':(False,True,False)})
    # 两山排布(仅庑殿、歇山、盝顶，不适用硬山、悬山、卷棚)
    if bData.roof_style in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_LUDING):
        for n in range(len(net_y)-1):
            length = net_y[n+1] - net_y[n]
            loc = Vector((purlin_cross.x,
                (net_y[n+1] + net_y[n])/2,
                purlin_cross.z))
            # 转角出头
            if n in (0,len(net_y)-2):
                length += hengExtend
                sign = utils.getSign(net_y[n])
                loc += Vector((0,hengExtend/2*sign,0))
            purlinList.append(
                {'len':length,
                'loc':loc,
                'rot':90,
                'mirror':(True,False,False)
                })
    
    # 生成所有的挑檐桁
    for purlin in purlinList:
        hengObj = utils.addCylinderHorizontal(
            radius= con.HENG_COMMON_D / 2 * dk,
            depth = purlin['len'],
            location = purlin['loc'], 
            rotation = (
                math.radians(-26),0,
                math.radians(purlin['rot'])),
            name = "挑檐桁",
            root_obj = rafterRootObj,
        )
        # 设置梁枋彩画
        mat.setShader(hengObj,mat.shaderType.LIANGFANG)
        # 设置对称
        utils.addModifierMirror(
            object=hengObj,
            mirrorObj=rafterRootObj,
            use_axis=purlin['mirror']
        )
    
    return

# 营造桁檩
# 包括檐面和山面
# 其中对庑殿和歇山做了特殊处理
def __buildPurlin(buildingObj:bpy.types.Object,purlin_pos):
    # 一、载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE*dk
    # 屋顶样式，1-庑殿，2-歇山，3-悬山，4-硬山
    roofStyle = bData.roof_style
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    
    # 桁的各个参数
    if roofStyle in (
            con.ROOF_XUANSHAN,
            con.ROOF_YINGSHAN,
            con.ROOF_XUANSHAN_JUANPENG):
        # 硬山、悬山桁不做出梢
        hengExtend = 0
    else:
        # 庑殿和歇山为了便于垂直交扣，做一桁径的出梢
        hengExtend = con.HENG_EXTEND * dk
    # 桁直径（正心桁、金桁、脊桁）
    purlin_r = con.HENG_COMMON_D / 2 * dk
    
    
    # 檐桁为了便于彩画贴图，按开间逐一生成
    if bData.use_dg:
        __buildYanHeng(rafterRootObj,purlin_pos)
        # 删除挑檐桁数据
        del purlin_pos[0]
    # 其他的桁为了效率，还是贯通整做成一根

    # 二、布置前后檐桁,根据上述计算的purlin_pos数据，批量放置桁对象
    for n in range(len(purlin_pos)) :
        # 1、桁交点
        pCross = purlin_pos[n]
        
        # 2、计算桁的长度
        purlin_length_x = pCross.x * 2 + hengExtend
        # 歇山檐面的下金桁延长，与上层对齐
        if roofStyle == con.ROOF_XIESHAN and n >= 1 :
                purlin_length_x = purlin_pos[-1].x * 2

        # 3、创建桁对象
        loc = (0,pCross.y,pCross.z)
        # 盝顶做承椽枋
        if (n == len(purlin_pos)-1 and 
               bData.roof_style == con.ROOF_LUDING) :
            hengFB = utils.addCube(
                name = '承椽枋-前后',
                location= loc,
                dimension= (purlin_length_x,
                            con.EFANG_SMALL_H*dk,
                            con.HENG_COMMON_D*dk),
                parent=rafterRootObj
            )
        # 其他一般情况下的槫子
        else:
            hengFB = utils.addCylinderHorizontal(
                    radius = purlin_r, 
                    depth = purlin_length_x,
                    location = loc, 
                    name = "桁-前后",
                    root_obj = rafterRootObj
                )
        # 前后镜像
        if (
                # 一般情况最后一根为脊桁，不做镜像
                n!=len(purlin_pos)-1            
                # 卷棚最后一根为脊桁，应该做前后的镜像
                or (n==len(purlin_pos)-1 and    
                    bData.roof_style==con.ROOF_XUANSHAN_JUANPENG)
                # 盝顶最后一根为下金桁，应该做前后镜像
                or (n==len(purlin_pos)-1 and    
                    bData.roof_style==con.ROOF_LUDING)
            ):
            # 除最后一根脊桁的处理，挑檐桁、正心桁、金桁做Y镜像
            utils.addModifierMirror(
                    object=hengFB,
                    mirrorObj=rafterRootObj,
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
                    root_obj = rafterRootObj,
                    edge_num =6
                )
        modBevel:bpy.types.BevelModifier = \
            hengFB.modifiers.new('Bevel','BEVEL')
        modBevel.width = con.BEVEL_LOW
        
        # 有斗拱时，正心桁下不做垫板
        if not (bData.use_dg and n == 0):
            # 4、桁垫板
            loc = (0,pCross.y,
                (pCross.z - con.HENG_COMMON_D*dk/2
                    - con.BOARD_HENG_H*dk/2))
            dim = (purlin_length_x,
                con.BOARD_HENG_Y*dk,
                con.BOARD_HENG_H*dk)
            dianbanObj = utils.addCube(
                name="垫板",
                location=loc,
                dimension=dim,
                parent=rafterRootObj,
            )
            if (
                    # 除了脊桁
                    n!=len(purlin_pos)-1  
                    # 或者卷棚的脊桁          
                    or (n==len(purlin_pos)-1 and    
                        bData.roof_style==con.ROOF_XUANSHAN_JUANPENG)
                    # 或者盝顶的下金桁
                    or (n==len(purlin_pos)-1 and    
                        bData.roof_style==con.ROOF_LUDING)
                ) :
                utils.addModifierMirror(
                    object=dianbanObj,
                    mirrorObj=rafterRootObj,
                    use_axis=(False,True,False)
                )
            utils.applyTransfrom(dianbanObj,use_scale=True)
            modBevel:bpy.types.BevelModifier = \
                dianbanObj.modifiers.new('Bevel','BEVEL')
            modBevel.width = con.BEVEL_EXLOW
        
        # 正心桁下不做枋
        if n != 0: 
            # 5、桁枋
            loc = (0,pCross.y,
                (pCross.z - con.HENG_COMMON_D*dk/2
                    - con.BOARD_HENG_H*dk
                    - con.HENGFANG_H*dk/2))
            dim = (purlin_length_x,
                con.HENGFANG_Y*dk,
                con.HENGFANG_H*dk)
            hengfangObj = utils.addCube(
                name="金/脊枋",
                location=loc,
                dimension=dim,
                parent=rafterRootObj,
            )
            if (
                    # 除了脊桁
                    n!=len(purlin_pos)-1  
                    # 或者卷棚的脊桁          
                    or (n==len(purlin_pos)-1 and    
                        bData.roof_style==con.ROOF_XUANSHAN_JUANPENG)
                    # 或者盝顶的下金桁
                    or (n==len(purlin_pos)-1 and    
                        bData.roof_style==con.ROOF_LUDING)
                ):
                utils.addModifierMirror(
                    object=hengfangObj,
                    mirrorObj=rafterRootObj,
                    use_axis=(False,True,False)
                )  
            utils.applyTransfrom(hengfangObj,use_scale=True)
            modBevel:bpy.types.BevelModifier = \
                hengfangObj.modifiers.new('Bevel','BEVEL')
            modBevel.width = con.BEVEL_LOW

    # 三、布置山面桁檩
    # 仅庑殿、歇山做山面桁檩，硬山、悬山不做山面桁檩
    if roofStyle in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_LUDING):
        if roofStyle == con.ROOF_WUDIAN :
            # 庑殿的上面做所有桁檩，除脊桁
            rafterRange = range(len(purlin_pos)-1)
        if roofStyle == con.ROOF_XIESHAN:
            # 歇山仅做正心桁、下金桁
            rafterRange = range(2)
        if roofStyle == con.ROOF_LUDING:
            rafterRange = range(len(purlin_pos))
        for n in rafterRange :
            pCross = purlin_pos[n]

            # 2、计算桁的长度
            purlin_length_y = pCross.y * 2 + hengExtend

            # 3、摆放桁对象
            # 盝顶做承椽枋
            if (n == len(purlin_pos)-1 and 
                bData.roof_style == con.ROOF_LUDING) :
                hengLR = utils.addCube(
                    name = '承椽枋-两山',
                    location= (pCross.x,0,pCross.z),
                    dimension= (con.EFANG_SMALL_H*dk,
                                purlin_length_y,
                                con.HENG_COMMON_D*dk),
                    parent=rafterRootObj
                )
            # 其他一般情况下的槫子
            else:
                hengLR = utils.addCylinderHorizontal(
                        radius = purlin_r, 
                        depth = purlin_length_y,
                        location = (pCross.x,0,pCross.z), 
                        rotation=Vector((0, 0, math.radians(90))), 
                        name = "桁-两山",
                        root_obj = rafterRootObj
                    )
            utils.addModifierMirror(
                    object=hengLR,
                    mirrorObj=rafterRootObj,
                    use_axis=(True,False,False)
                )
            modBevel:bpy.types.BevelModifier = \
                hengLR.modifiers.new('Bevel','BEVEL')
            modBevel.width = con.BEVEL_LOW
            
            # 判断垫板、枋的逻辑
            use_dianban = True
            use_fang = True
            # 歇山的踩步金下不做
            if roofStyle== con.ROOF_XIESHAN :
                if n==1:
                    use_fang = False
                    use_dianban = False
            # 正心桁下不做枋
            # 有斗栱时，正心桁下不做垫板
            if roofStyle in (
                    con.ROOF_WUDIAN,
                    con.ROOF_XIESHAN,
                    con.ROOF_LUDING,) and n==0:
                use_fang = False
                if bData.use_dg:
                    use_dianban = False
            # 桁垫板
            if use_dianban:
                loc = (pCross.x,0,
                    (pCross.z - con.HENG_COMMON_D*dk/2
                        - con.BOARD_HENG_H*dk/2))
                dim = (purlin_length_y,
                    con.BOARD_HENG_Y*dk,
                    con.BOARD_HENG_H*dk)
                dianbanObj = utils.addCube(
                    name="垫板",
                    location=loc,
                    dimension=dim,
                    rotation=Vector((0, 0, math.radians(90))),
                    parent=rafterRootObj,
                )
                utils.addModifierMirror(
                    object=dianbanObj,
                    mirrorObj=rafterRootObj,
                    use_axis=(True,False,False)
                )
                utils.applyTransfrom(dianbanObj,use_scale=True)
                modBevel:bpy.types.BevelModifier = \
                    dianbanObj.modifiers.new('Bevel','BEVEL')
                modBevel.width = con.BEVEL_EXLOW
            # 桁枋
            if use_fang:
                loc = (pCross.x,0,
                    (pCross.z - con.HENG_COMMON_D*dk/2
                        - con.BOARD_HENG_H*dk
                        - con.HENGFANG_H*dk/2))
                dim = (purlin_length_y,
                    con.HENGFANG_Y*dk,
                    con.HENGFANG_H*dk)
                hengfangObj = utils.addCube(
                    name="金/脊枋",
                    location=loc,
                    rotation=Vector((0, 0, math.radians(90))),
                    dimension=dim,
                    parent=rafterRootObj,
                )
                utils.addModifierMirror(
                    object=hengfangObj,
                    mirrorObj=rafterRootObj,
                    use_axis=(True,False,False)
                )
                utils.applyTransfrom(hengfangObj,use_scale=True)
                modBevel:bpy.types.BevelModifier = \
                    hengfangObj.modifiers.new('Bevel','BEVEL')
                modBevel.width = con.BEVEL_LOW

            # 4、添加镜像
                 
    return

# 绘制梁
# 参考马炳坚p149
def __drawBeam(
        location:Vector,
        dimension:Vector,
        buildingObj:bpy.types.Object,
        name='梁',):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    bWidth = dimension.x
    bLength = dimension.y
    bHeight = dimension.z

    # 梁头与横梁中线齐平
    p1 = Vector((0,bLength/2,0))
    # 梁底，从P1向下半檩径+垫板高度
    p2 = p1 - Vector((0,0,
        con.HENG_COMMON_D*dk/2+con.BOARD_HENG_H*dk))
    # 梁底，Y镜像P2
    p3 = p2 * Vector((1,-1,1))
    # 梁头，Y镜像坡P1
    p4 = p1 * Vector((1,-1,1))
    # 梁腰，从梁头退1.5桁径（出梢半桁径）
    p5 = p4 + Vector((
        0,1.5*con.HENG_COMMON_D*dk,0))
    # 微调
    p5 += Vector((0,0.05,0))
    # 梁肩，从梁腰45度，延伸到梁顶部（梁高-垫板高-半桁）
    offset = (bHeight
              - con.BOARD_HENG_H*dk
              - con.HENG_COMMON_D*dk/2)
    p6 = p5 + Vector((0,offset,offset))
    # 梁肩Y镜像
    p7 = p6 * Vector((1,-1,1))
    # 梁腰Y镜像
    p8 = p5 * Vector((1,-1,1))

    # 创建bmesh
    bm = bmesh.new()
    # 各个点的集合
    vectors = [p1,p2,p3,p4,p5,p6,p7,p8]

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
    face = bm.faces.new((vertices[:]))
    
    # 挤出厚度
    return_geo = bmesh.ops.extrude_face_region(
        bm, geom=[face])
    verts = [elem for elem in return_geo['geom'] 
             if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, 
            verts=verts, 
            vec=(bWidth,0, 0))
    for v in bm.verts:
        # 移动所有点，居中
        v.co.x -= bWidth/2
    
    # 确保face normal朝向
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    # 任意添加一个对象，具体几何数据在bmesh中建立
    # 原点在对应桁檩的Z高度，X一般对应到柱头，Y一般为0
    bpy.ops.mesh.primitive_cube_add(
        location=location
    )
    beamObj = bpy.context.object
    beamObj.name = name

    # 填充bmesh数据
    bm.to_mesh(beamObj.data)
    beamObj.data.update()
    bm.free()

    # 处理UV
    mat.UvUnwrap(beamObj,type='cube')

    return beamObj

# 绘制角背
def __drawJiaobei(shuzhuObj:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(
        shuzhuObj,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    
    shuzhu_height = shuzhuObj.dimensions.z
    # 仅柱高大于柱径才需要角背，否则直接返回
    if shuzhu_height <= con.PILLER_CHILD*dk: 
        return None
    
    # 计算尺寸
    # 角背高度可以取1/2，也可以取1/3
    if shuzhu_height/(con.PILLER_CHILD*dk) >2:
        height = shuzhu_height/3
    else:
        height = shuzhu_height/2
    # 角背长度取一个步架宽
    rafterSpan = bData.y_total/bData.rafter_count
    dim = Vector((
        con.JIAOBEI_WIDTH*dk,
        rafterSpan,
        height,
    ))

    # 位置
    loc = (shuzhuObj.location.x,
        shuzhuObj.location.y, # 对齐上一层的槫的Y位置
        (shuzhuObj.location.z-shuzhu_height/2
            + height/2))
    bpy.ops.mesh.primitive_cube_add(
        location = loc
    )
    jiaobeiObj = bpy.context.object
    jiaobeiObj.name = '角背'
    jiaobeiObj.parent = shuzhuObj.parent
    jiaobeiObj.dimensions = dim
    utils.applyTransfrom(jiaobeiObj,use_scale=True)
    # 挤压两个角
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.new()
    bm = bmesh.from_edit_mesh(bpy.context.object.data)
    bpy.ops.mesh.select_mode(type = 'EDGE')
    bm.edges.ensure_lookup_table()
    bpy.ops.mesh.select_all(action = 'DESELECT')
    bm.edges[5].select = True
    bm.edges[11].select = True
    bpy.ops.mesh.bevel(affect='EDGES',
                offset_type='OFFSET',
                offset=height/2,
                segments=1,
                )
    bmesh.update_edit_mesh(bpy.context.object.data ) 
    bm.free() 
    bpy.ops.object.mode_set( mode = 'OBJECT' )

    # 处理UV
    mat.UvUnwrap(jiaobeiObj,type='cube')

    utils.copyModifiers(
        from_0bj=shuzhuObj,
        to_obj=jiaobeiObj)
    
    return jiaobeiObj

# 营造梁架
# 1、只做了通檐的大梁，没有做抱头梁形式
def __buildBeam(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    
    # 收集所有梁架，便于后续合并
    beamObjects = []

    # 横向循环每一幅梁架
    roofStyle = bData.roof_style
    for x in range(len(net_x)):
        # 判断梁架是否与脊槫相交
        # 在庑殿中很明显，可能存在不合理的梁架
        if (bData.roof_style in (
                    con.ROOF_WUDIAN,
                    con.ROOF_LUDING,)
            and abs(net_x[x]) > purlin_pos[-1].x ):
            # 忽略此副梁架
            continue
        # 在歇山中，不做超过金槫交点的梁架
        # 但放过山面梁架，做为排山梁架
        if (bData.roof_style in (con.ROOF_XIESHAN)
            and abs(net_x[x]) > purlin_pos[-1].x - con.HENG_EXTEND*dk
            and x not in (0,len(net_x)-1)):
            # 忽略此副梁架
            continue

        # 纵向循环每一层梁架
        for n in range(len(purlin_pos)):  
            # 添加横梁
            # 一般脊槫不做横梁，例外：卷棚要做
            isJuanpengJituan = (n == len(purlin_pos)-1 
                and bData.roof_style in (con.ROOF_XUANSHAN_JUANPENG))
            if n!=len(purlin_pos)-1 or isJuanpengJituan: 
                # X向随槫交点依次排列
                beam_x = net_x[x]
                beam_z = purlin_pos[n].z
                beam_l = purlin_pos[n].y*2 + con.HENG_COMMON_D*dk*2
                beam_name = '梁'
                
                # 歇山特殊处理：做排山梁架
                # 将两山柱对应的梁架，偏移到金桁交点
                if (roofStyle == con.ROOF_XIESHAN and
                        x in (0,len(net_x)-1)):
                    # 第一层不做（排山梁架不坐在柱头）
                    if n == 0: 
                        continue
                    # 第二层做踩步金，与下金桁下皮平
                    if n == 1:
                        beam_z = purlin_pos[1].z \
                            + con.BEAM_HEIGHT*pd \
                            - con.HENG_COMMON_D*dk/2
                        beam_l = purlin_pos[1].y*2
                        beam_name = '踩步金'
                    # X坐标，位移到下金桁的X位置
                    if n > 0 :
                        if x == 0:
                            beam_x = -purlin_pos[1].x
                        if x == len(net_x)-1:
                            beam_x = purlin_pos[1].x

                # 梁定位
                beam_loc = Vector((beam_x,0,beam_z))
                beam_dim = Vector((
                    con.BEAM_DEEPTH*pd,
                    beam_l,
                    con.BEAM_HEIGHT*pd
                ))
                # 绘制梁mesh，包括梁头形状
                beamCopyObj = __drawBeam(
                    location=beam_loc,
                    dimension=beam_dim,
                    buildingObj=buildingObj,
                    name = beam_name
                )
                beamCopyObj.parent= rafterRootObj
                beamObjects.append(beamCopyObj)

                # 盝顶仅做抱头梁
                if roofStyle == con.ROOF_LUDING:
                    # 剪切到金柱位置
                    utils.addBisect(
                        object=beamCopyObj,
                        pStart=Vector((0,0,0)),
                        pEnd=Vector((1,0,0)),
                        pCut=((
                            0,
                            bData.y_total/2 - bData.luding_rafterspan,
                            0)),
                        clear_inner=True,
                    )
                    utils.addModifierMirror(
                        object=beamCopyObj,
                        mirrorObj=rafterRootObj,
                        use_axis=(False,True,False),
                    )
                
                # 开始做蜀柱和垫板 ===============
                # 在梁上添加蜀柱
                # 歇山山面第一层不做蜀柱和垫板
                if (roofStyle == con.ROOF_XIESHAN 
                        and n==0 and x in (0,len(net_x)-1)):
                    continue
                # 卷棚的脊槫处不做蜀柱和垫板
                if (roofStyle in (con.ROOF_XUANSHAN_JUANPENG) 
                        and n==len(purlin_pos)-1):
                    continue
                # 盝顶不做蜀柱和垫板
                if (roofStyle in (con.ROOF_LUDING)):
                    # 卷棚的脊槫处不做蜀柱
                    continue

                # 梁下皮与origin的距离
                beamBottom_offset = (con.HENG_COMMON_D*dk/2 
                             + con.BOARD_HENG_H*dk)
                # 梁上皮于origin的距离
                beamTop_offset = (con.BEAM_HEIGHT*pd 
                             - beamBottom_offset)
                if (n == len(purlin_pos)-2 and 
                    roofStyle not in (con.ROOF_XUANSHAN_JUANPENG)):
                    # 直接支撑到脊槫
                    shuzhu_height = (purlin_pos[n+1].z 
                        - purlin_pos[n].z - beamTop_offset)
                else:
                    # 支撑到上下两根梁之间
                    shuzhu_height = purlin_pos[n+1].z \
                        - purlin_pos[n].z \
                        - con.BEAM_HEIGHT*pd
                shuzhu_loc = Vector((
                    beam_x,   # X向随槫交点依次排列
                    purlin_pos[n+1].y, # 对齐上一层的槫的Y位置
                    purlin_pos[n].z + shuzhu_height/2 + beamTop_offset
                ))
                shuzhu_dimensions = Vector((
                    con.PILLER_CHILD*dk,
                    con.PILLER_CHILD*dk,
                    shuzhu_height
                ))                
                shuzhuCopyObj = utils.addCube(
                    name="垫板",
                    location=shuzhu_loc,
                    dimension=shuzhu_dimensions,
                    parent=rafterRootObj,
                )
                if n!=len(purlin_pos)-1:
                    #镜像
                    utils.addModifierMirror(
                        shuzhuCopyObj,
                        mirrorObj=rafterRootObj,
                        use_axis=(False,True,False),
                        use_bisect=(False,True,False)
                    )
                beamObjects.append(shuzhuCopyObj)

                # 蜀柱添加角背
                jiaobeiObj = __drawJiaobei(shuzhuCopyObj)
                if jiaobeiObj != None:
                    beamObjects.append(jiaobeiObj)
        
    # 合并梁架各个部件
    # 攒尖顶时，不做梁架
    if beamObjects != []:
        beamSetObj = utils.joinObjects(
            beamObjects,newName='梁架')
        modBevel:bpy.types.BevelModifier = \
            beamSetObj.modifiers.new('Bevel','BEVEL')
        modBevel.width = con.BEVEL_HIGH
                           
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
    utils.addModifierMirror(
        object=LKMObj,
        mirrorObj=rafterRootObj,
        use_axis=LKM_mirrorAxis
    )
    # 设置材质，刷红漆
    mat.setShader(LKMObj,mat.shaderType.REDPAINT)
    return

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
            name="檐椽.前后",
            root_obj = rafterRootObj
        )
        fbRafterObj.ACA_data['aca_obj'] = True
        fbRafterObj.ACA_data['aca_type'] = con.ACA_TYPE_RAFTER_FB
        
        # 2. 各层椽子都上移，与桁檩上皮相切
        bpy.ops.transform.translate(
            value = (0,0,(con.HENG_COMMON_D+con.YUANCHUAN_D)*dk/2),
            orient_type = con.OFFSET_ORIENTATION
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

        # 4、歇山顶在山花处再加一层檐椽
        if bData.roof_style == con.ROOF_XIESHAN and n==0:
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
        if (bData.roof_style in (con.ROOF_XUANSHAN_JUANPENG)
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
            utils.addBisect(
                object=curveRafter,
                pStart=Vector((0,0,0)),
                pEnd=Vector((0,1,1)),   #近似按45度斜切，其实有误差
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
        elif bData.roof_style == con.ROOF_YINGSHAN:
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
        
    # 根据桁数组循环计算各层椽架
    for n in range(len(purlin_pos)-1):
        if bData.roof_style == con.ROOF_XIESHAN: 
            if n > 0: continue  # 歇山山面仅做一层椽架
        # 1.逐层定位椽子，直接连接上下层的桁檩(槫子)
        rafter_offset = Vector((0,con.YUANCHUAN_D*dk,0))
        rafter_end = purlin_pos[n]*Vector((1,0,1))+rafter_offset
        rafter_start = purlin_pos[n+1]*Vector((1,0,1))+rafter_offset
        lrRafterObj = utils.addCylinderBy2Points(
            radius = con.YUANCHUAN_D/2*dk,
            start_point = rafter_start,
            end_point = rafter_end,
            name="檐椽.两山",
            root_obj = rafterRootObj
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
        
        # 镜像
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
        if bData.roof_style==con.ROOF_XIESHAN and n>0:
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
            root_obj=rafterRootObj,
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
            # 里口木避让（无需加斜）
            extend_hyp -= (con.QUETAI            # 雀台避让
                    + con.LIKOUMU_Y)* dk    # 里口木避让
            # 加斜计算
            wangbanObj.dimensions.x += extend_hyp
            utils.applyTransfrom(wangbanObj,use_scale=True) 
            # 更新UV
            mat.UvUnwrap(wangbanObj,type='cube')

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
        if bData.roof_style == con.ROOF_XIESHAN and n ==0:
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
                    pStart=Vector((0,0,0)),
                    pEnd=Vector((-1,-1,0)),
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
            bData.roof_style in (con.ROOF_XUANSHAN_JUANPENG)):
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
                pStart=Vector((0,0,0)),
                pEnd=Vector((0,1,1)),   #近似按45度斜切，其实有误差
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
        if bData.roof_style == con.ROOF_XIESHAN and n>0: continue
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
            root_obj=rafterRootObj,
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
            # 更新UV
            mat.UvUnwrap(wangbanObj,type='cube')

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
def __drawFlyrafter(yanRafterObj:bpy.types.Object)->bpy.types.Object:
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
    # 对齐檐椽位置
    yanchuan_head_co = utils.getObjectHeadPoint(yanRafterObj,
            is_symmetry=(True,True,False))
    # 向上位移半檐椽+一望板（基于水平投影的垂直移动)
    offset_z = (con.YUANCHUAN_D/2+con.WANGBAN_H)*dk
    offset_z = offset_z / math.cos(yanRafterObj.rotation_euler.y)
    loc = yanchuan_head_co + Vector((0,0,offset_z))
    # 任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add(
        location=loc
    )
    flyrafterObj = bpy.context.object
    # 对齐檐椽角度
    flyrafterObj.rotation_euler = yanRafterObj.rotation_euler 
    # 填充bmesh数据
    bm.to_mesh(flyrafterObj.data)
    flyrafterObj.data.update()
    bm.free()

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

    flyrafterObj = __drawFlyrafter(yanRafterObj)
    flyrafterObj.name = flyrafterName
    flyrafterObj.data.name = flyrafterName
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
        if bData.roof_style==con.ROOF_YINGSHAN:
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

    # 添加镜像
    utils.addModifierMirror(
        object=DLY_Obj,
        mirrorObj=rafterRootObj,
        use_axis=DLY_mirrorAxis
    )
    # 设置材质，刷红漆
    mat.setShader(DLY_Obj,mat.shaderType.REDPAINT)

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
            if bData.roof_style == con.ROOF_XIESHAN : continue

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
            modBevel:bpy.types.BevelModifier = \
                CornerBeamObj.modifiers.new('Bevel','BEVEL')
            modBevel.width = con.BEVEL_LOW
            
            if bData.use_flyrafter:
                # 绘制子角梁
                cbcObj:bpy.types.Object = \
                    __drawCornerBeamChild(CornerBeamObj)
                cbcObj.name = '仔角梁'
                cbcObj.data.name = '仔角梁'
                cbcObj.parent = rafterRootObj
                cbcObj.ACA_data['aca_obj'] = True
                cbcObj.ACA_data['aca_type'] = con.ACA_TYPE_CORNER_BEAM_CHILD
                utils.addModifierMirror(
                    object=cbcObj,
                    mirrorObj=rafterRootObj,
                    use_axis=(True,True,False))
                modBevel:bpy.types.BevelModifier = \
                    cbcObj.modifiers.new('Bevel','BEVEL')
                modBevel.width = con.BEVEL_LOW

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
    mat.setShader(xly_curve_obj,
        mat.shaderType.REDPAINT)

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
        # 角梁45度对称
        utils.addModifierMirror(
            object=cornerRafterObj,
            mirrorObj=cornerBeamObj,
            use_axis=(False,True,False)
        )
        # 四向对称
        utils.addModifierMirror(
            object=cornerRafterObj,
            mirrorObj=rafterRootObj,
            use_axis=(True,True,False)
        )

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
    crWangban.name = '翼角椽望板'
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
    # 冲出，大连檐仅冲1椽
    ex += bData.chong * con.YUANCHUAN_D * dk
    # # 避让角梁，向内1/4角梁，见汤崇平书籍的p196
    # shift = - con.JIAOLIANG_Y/4*dk * math.sqrt(2)
    # 延伸，以便后续做45度相交裁剪
    shift = con.JIAOLIANG_H*dk/2
    pEnd_x = bData.x_total/2 + ex + shift
    pEnd_y = bData.y_total/2 + ex
    qiqiao = bData.qiqiao * con.YUANCHUAN_D * dk
    pEnd_z = dlyObj.location.z + qiqiao
    pEnd = Vector((pEnd_x,pEnd_y,pEnd_z))

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
    mat.setShader(flyrafterEaveObj,
        mat.shaderType.REDPAINT)

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
            is_symmetry=(True,True,False))
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
    offset_z = offset_z / math.cos(cornerRafterObj.rotation_euler.y)
    origin_point = cr_head_co + Vector((0,0,offset_z))
    # # 沿翼角椽Z方向抬升，半椽+1望板
    # # 不按水平投影抬升，虽然在图纸上好看，但实际会与大连檐穿模
    # offset = Vector((0,0,con.YUANCHUAN_D*dk/2+con.WANGBAN_H*dk))
    # offset.rotate(cornerRafterObj.rotation_euler)
    # origin_point = cr_head_co + offset

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
    # 计算翘飞椽头与檐口线的夹角
    shear_rot = utils.alignToVector(head_shear) # 檐口线夹角
    tilt_rot = cfrObj.rotation_euler.z - shear_rot.z 
    tilt_offset = (con.FLYRAFTER_H/2*dk+con.QUETAI*dk) / math.tan(tilt_rot)
    # 2.4 向外延长，并且下移半椽
    offset = Vector((tilt_offset,0,-con.FLYRAFTER_H*dk/2)) # 下移半椽
    offset.rotate(cfr_head_rotation)
    # offset.rotate(Euler((0,-cfrObj.rotation_euler.y,0)))
    v2 = cfrEnd_center + offset
    vectors.append(v2)
    
    # 3.到翘飞椽头上皮，上移一椽径
    offset = Vector((0,0,con.FLYRAFTER_H*dk))
    offset.rotate(cfr_head_rotation)
    # offset.rotate(Euler((0,-cfrObj.rotation_euler.y,0)))
    v3 = v2 + offset
    vectors.append(v3)

    # 4.到翘飞椽腰点上皮，上移一椽径，注意坐标系已经旋转到檐椽角度
    v4 = Vector((0,0,con.FLYRAFTER_H*dk))
    # 将位置旋转到垂直为止
    # 尝试了很久矩阵运算，都没搞对，只能先这么做了
    v4.rotate(Euler((0,-cfrObj.rotation_euler.y,0)))
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
    # for v in tilt_edge.verts:
    #     #v.co.x -= tilt_offset_x
    #     v.co.z -= tilt_offset_z/2
    tilt_edge = bm.edges[6] # 椽腰左侧边
    for v in tilt_edge.verts:
        v.co.x += tilt_offset_x
        v.co.z += tilt_offset_z

    # 椽头撇向处理
    # 计算撇向量：用当前斜率-初始斜率，再投影到“翘飞椽头”的Z轴
    Z_vec = Vector((0,0,1))
    Z_vec.rotate(cfr_head_rotation)
    header_adj = (head_shear-head_shear_base)*Z_vec
    # 点位移
    bm.edges.ensure_lookup_table() # 按序号访问前，必须先ensure
    head_shear_edge = bm.edges[10] # 椽头左侧线
    for v in head_shear_edge.verts:
        v.co += header_adj/2
    head_shear_edge = bm.edges[1] # 椽头左侧线
    for v in head_shear_edge.verts:
        v.co -= header_adj/2

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
    dk = bData.DK
    # 屋顶根节点
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    # 老角梁
    cornerBeamObj = utils.getAcaChild(
        buildingObj,
        con.ACA_TYPE_CORNER_BEAM)
    # 翼角椽定位线
    rafterCurveObj = utils.getAcaChild(
        buildingObj,
        con.ACA_TYPE_CORNER_RAFTER_CURVE)
    # 翼角椽的椽尾坐标集合
    crCount = len(cornerRafterColl)
    crEnds = utils.getBezierSegment(rafterCurveObj,crCount)

    # 绘制翘飞椽定位线
    cfrCurve = __buildCornerFlyrafterCurve(buildingObj)
    # 翘飞椽的椽尾坐标集合
    cfrEnds = utils.getBezierSegment(cfrCurve,crCount)

    # 摆放翘飞椽
    # 收集翘飞椽对象，输出绘制翘飞椽望板
    cfrCollection = []
    head_shear_base = Vector((0,0,0))
    mid_shear_base = Vector((0,0,0))
    for n in range(len(cfrEnds)):
        # 计算相邻椽头间的撇向
        head_shear_direction = Vector((0,0,0))
        
        mid_shear_direction = Vector((0,0,0))
        if n != 0 :
            head_shear_direction = cfrEnds[n] - cfrEnds[n-1]
            mid_shear_direction = crEnds[n] - crEnds[n-1]
        # if n != len(cfrEnds)-1:
        #     mid_shear_base = crEnds[n+1] - crEnds[n]
        if n == 1:
            head_shear_base = head_shear_direction
            mid_shear_base = mid_shear_direction
        

        cfr_Obj = __drawCornerFlyrafterNew(
            cornerRafterObj = cornerRafterColl[n], # 对应的翼角椽对象
            cornerFlyrafterEnd = cfrEnds[n], # 头在翘飞椽定位线上
            head_shear = head_shear_direction, # 椽头撇向
            head_shear_base=head_shear_base,    
            name='翘飞椽',
            root_obj=rafterRootObj
        )
        cfrCollection.append(cfr_Obj)
        mod = cfr_Obj.modifiers.new(name='角梁对称', type='MIRROR')
        mod.mirror_object = cornerBeamObj
        mod.use_axis[0] = False
        mod.use_axis[1] = True
        mod = cfr_Obj.modifiers.new(name='mirror', type='MIRROR')
        mod.mirror_object = rafterRootObj
        mod.use_axis[0] = True
        mod.use_axis[1] = True

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
    roofStyle = bData.roof_style
    useFlyrafter = bData.use_flyrafter
    useWangban = bData.use_wangban

    # 收集待合并的望板
    wangbanObjs = []

    # 各种屋顶都有前后檐
    utils.outputMsg("Building Rafter Front/Back...")
    fbRafterObj = __buildRafter_FB(buildingObj,purlin_pos)    # 前后檐椽
    
    if useFlyrafter:  # 用户可选择不使用飞椽
        utils.outputMsg("Building Fly Rafter...")
        # 这里生成的是飞椽，但返回的是压飞望板
        wangbanF_FB = __buildFlyrafterAll(
            buildingObj,purlin_pos,'X') # 前后飞椽
        wangbanObjs.append(wangbanF_FB)
        
    if useWangban:  # 用户可选择暂时不生成望板（更便于观察椽架形态）
        utils.outputMsg("Building Wangban...")
        wangbanFB = __buildWangban_FB(buildingObj,purlin_pos)   # 前后望板
        wangbanObjs.append(wangbanFB)
    
    # 庑殿、歇山的处理（硬山、悬山不涉及）
    if roofStyle in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_LUDING):
        # 营造角梁
        utils.outputMsg("Building Corner Beam...")
        __buildCornerBeam(buildingObj,purlin_pos)
        
        # 两山檐椽
        utils.outputMsg("Building Rafter Left/Right...")
        __buildRafter_LR(buildingObj,purlin_pos)    
        
        if useFlyrafter:
            # 两山飞椽
            utils.outputMsg("Building Fly Rafter Left/Right...")
            wangbanF_LR = __buildFlyrafterAll(buildingObj,purlin_pos,'Y') 
            wangbanObjs.append(wangbanF_LR)
            
        if useWangban:
            # 两山望板
            utils.outputMsg("Building Wangban Left/Right...")
            wangbanLR = __buildWangban_LR(buildingObj,purlin_pos)  
            wangbanObjs.append(wangbanLR) 
            
        # 翼角部分
        # 营造小连檐
        utils.outputMsg("Building Corner Rafter Eave...")
        __buildCornerRafterEave(buildingObj)
        
        # 营造翼角椽
        utils.outputMsg("Building Corner Rafter...")
        cornerRafterColl = __buildCornerRafter(buildingObj,purlin_pos)
        
        if useWangban:
            # 翼角椽望板
            utils.outputMsg("Building Corner Rafter Wangban...")
            wangbanCR = __buildCrWangban(buildingObj,purlin_pos,cornerRafterColl)
            wangbanObjs.append(wangbanCR) 

        # 是否做二层飞椽
        if useFlyrafter:
            # 大连檐
            utils.outputMsg("Building Corner Fly Rafter Eave...")
            __buildCornerFlyrafterEave(buildingObj)
            
            # 翘飞椽，以翼角椽为基准
            utils.outputMsg("Building Corner Fly Rafter...")
            cfrCollection = __buildCornerFlyrafter(buildingObj,cornerRafterColl)
            
            if useWangban:
                # 翘飞椽望板
                utils.outputMsg("Building Corner Fly Rafter Wangban...")
                wangbanCFR = __buildCfrWangban(buildingObj,purlin_pos,cfrCollection)
                wangbanObjs.append(wangbanCFR) 

            # 合并翘飞椽
            cfrSet = utils.joinObjects(
                cfrCollection,newName='翘飞椽')
            # UV处理
            mat.UvUnwrap(cfrSet)
            # 倒角
            modBevel:bpy.types.BevelModifier = \
                cfrSet.modifiers.new('Bevel','BEVEL')
            modBevel.width = con.BEVEL_EXLOW

        # 合并翼角椽
        crSet = utils.joinObjects(
            cornerRafterColl,newName='翼角椽')
        # UV处理
        mat.UvUnwrap(crSet)
        # 倒角
        modBevel:bpy.types.BevelModifier = \
            crSet.modifiers.new('Bevel','BEVEL')
        modBevel.width = con.BEVEL_EXLOW
        # 平滑
        utils.shaderSmooth(crSet)

    # 以下为各类屋顶类型通用的处理  
    # 合并望板
    if useWangban:
        wangbanSet = utils.joinObjects(
            wangbanObjs,newName='望板')
        # 更新UV
        mat.UvUnwrap(wangbanSet,type='cube')
    
    # 檐椽事后处理(处理UV,添加倒角)
    # 只能放在最后加倒角，因为计算翼角椽时有取檐椽头坐标
    # 加了倒角后，取檐椽头坐标时就出错了
    yanRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_FB)
    mat.UvUnwrap(yanRafterObj)
    modBevel:bpy.types.BevelModifier = \
        yanRafterObj.modifiers.new('Bevel','BEVEL')
    modBevel.width = con.BEVEL_EXLOW
    # 两山檐椽
    yanRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_LR)
    if yanRafterObj != None:
        mat.UvUnwrap(yanRafterObj)
        modBevel:bpy.types.BevelModifier = \
            yanRafterObj.modifiers.new('Bevel','BEVEL')
        modBevel.width = con.BEVEL_EXLOW
    # 两山飞椽
    flyRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_FLYRAFTER_LR)
    if flyRafterObj != None:
        mat.UvUnwrap(flyRafterObj)
        modBevel:bpy.types.BevelModifier = \
            flyRafterObj.modifiers.new('Bevel','BEVEL')
        modBevel.width = con.BEVEL_EXLOW
    # 前后檐飞椽
    flyRafterObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_FLYRAFTER_FB)
    if flyRafterObj != None:
        mat.UvUnwrap(flyRafterObj)
        modBevel:bpy.types.BevelModifier = \
            flyRafterObj.modifiers.new('Bevel','BEVEL')
        modBevel.width = con.BEVEL_EXLOW

    return

# 营造象眼板
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

    # 象眼板横坐标
    if bData.roof_style == con.ROOF_XIESHAN:
        # 歇山的象眼板在金桁交点处（加出梢）
        xyb_x = (purlin_pos[-1].x       # 桁檩定位点
                 - con.XYB_WIDTH*dk/2   # 移到外皮位置
                 + 0.01)                # 防止与檩头交叠
        # 歇山从金桁以上做起
        xyb_range = range(1,len(purlin_pos))
        xyb_name = '山花板'
    if bData.roof_style in (
            con.ROOF_XUANSHAN,
            con.ROOF_XUANSHAN_JUANPENG):
        # 悬山的象眼板在山柱中线处
        xyb_x = bData.x_total/2
        # 悬山从正心桁做起
        xyb_range = range(len(purlin_pos))
        xyb_name = '象眼板'

    # 综合考虑桁架上铺椽、望、灰泥后的效果，主要保证整体线条的流畅
    # 从举架定位点做偏移
    for n in xyb_range:
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
    xybObj.name = xyb_name
    xybObj.data.name = xyb_name
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
        mat.setShader(xybObj,
            mat.shaderType.STONE)
    elif bData.roof_style == con.ROOF_XIESHAN:
        # 歇山刷红漆
        mat.setShader(xybObj,
            mat.shaderType.REDPAINT)

    return xybObj

# 绘制博缝板（上沿）曲线
def __drawBofengCurve(buildingObj:bpy.types.Object,
                    purlin_pos):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    ridgeCurveVerts = []
    # 垂脊横坐标
    ridge_x = purlin_pos[-1].x
    # 硬山调整一个山墙宽度
    if bData.roof_style ==con.ROOF_YINGSHAN:
        ridge_x += con.SHANQIANG_WIDTH * dk - con.BEAM_DEEPTH * pd/2

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
        offset = (con.HENG_COMMON_D/2 + con.YUANCHUAN_D 
                  + con.WANGBAN_H + con.ROOFMUD_H)*dk
        point:Vector = purlin_pos[n]+Vector((0,0,offset))
        point.x = ridge_x
        ridgeCurveVerts.append(point)
    
    # 卷棚顶的曲线调整,最后一点囊相调整，再加两个平滑点
    if bData.roof_style in (con.ROOF_XUANSHAN_JUANPENG):
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
    mat.setShader(bofengObj,mat.shaderType.REDPAINT,override=True)
    height = (con.HENG_COMMON_D + con.YUANCHUAN_D*4
                   + con.WANGBAN_H + con.ROOFMUD_H)*dk
    bofengObj.dimensions = (
        bofengObj.dimensions.x,
        con.BOFENG_WIDTH*dk,
        height)    

    # 添加curve modifier
    modCurve : bpy.types.CurveModifier = \
        bofengObj.modifiers.new('曲线拟合','CURVE')
    modCurve.object = bofengCurve
    
    # 应用镜像
    utils.addModifierMirror(
        object=bofengObj,
        mirrorObj=rafterRootObj,
        use_axis=(True,True,False),
        use_bisect=(False,True,False)
    )

    # 歇山的博缝板沿金桁高度裁剪
    if bData.roof_style == con.ROOF_XIESHAN:
        utils.addBisect(
            object=bofengObj,
            pStart=Vector((0,1,0)),
            pEnd=Vector((0,-1,0)),
            pCut=rafterRootObj.matrix_world @ (rafter_pos[1]),
            clear_outer=True,
            direction='Y'
        )
    modBevel:bpy.types.BevelModifier = \
        bofengObj.modifiers.new('Bevel','BEVEL')
    modBevel.width = con.BEVEL_LOW
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

    # 墀头点
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
    # 2、垂直延伸到柱头高度
    p01: Vector = Vector((bData.x_total/2,
        bData.y_total/2 + con.SHANQIANG_EX*dk,
        -tile_base+bData.piller_height))
    ShanWallVerts.insert(0,p01*Vector((1,-1,1)))
    ShanWallVerts.append(p01)

    # 3、檐口点：从正身飞椽的中心当开始，上移半飞椽+大连檐
    # 大连檐中心
    dlyObj:bpy.types.Object = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_DLY_FB)
    p1 = Vector(dlyObj.location)
    # 位移到大连檐外沿
    offset = Vector((ridge_x,con.DALIANYAN_H*dk/2,0))
    offset.rotate(dlyObj.rotation_euler)
    p1 += offset
    ShanWallVerts.insert(0,p1*Vector((1,-1,1)))
    ShanWallVerts.append(p1)

    # 综合考虑桁架上铺椽、望、灰泥后的效果，主要保证整体线条的流畅
    # 从举架定位点做偏移
    for n in range(len(purlin_pos)):
        # 向上位移:半桁径+椽径+望板高+灰泥层高
        offset = (con.HENG_COMMON_D/2 + con.YUANCHUAN_D 
                  + con.WANGBAN_H + con.ROOFMUD_H)*dk
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
    mat.setShader(shanWallObj,
            mat.shaderType.ROCK)
    
    # 添加镜像
    utils.addModifierMirror(
        object=shanWallObj,
        mirrorObj=rafterRootObj,
        use_axis=(True,False,False)
    )
    
    return

# 营造梁椽望层
def __buildBPW(buildingObj:bpy.types.Object):
    # 设定“梁椽望”根节点
    rafterRootObj = __addRafterRoot(buildingObj)

    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    # 屋瓦依赖于椽望，强制生成
    if bData.is_showTiles : 
        bData['is_showBPW']=True

    # 计算桁檩定位点
    purlin_pos = __getPurlinPos(buildingObj)
    
    # 摆放桁檩
    utils.outputMsg("Building Purlin...")
    __buildPurlin(buildingObj,purlin_pos.copy())
    
    # 如果有斗栱，剔除挑檐桁
    # 在梁架、椽架、角梁的计算中不考虑挑檐桁
    rafter_pos = purlin_pos.copy()
    if bData.use_dg:
        del rafter_pos[0]

    # 摆放梁架
    utils.outputMsg("Building Beam...")
    __buildBeam(buildingObj,rafter_pos)

    # 摆放椽架（包括角梁、檐椽、望板、飞椽、里口木、大连檐等）
    utils.outputMsg("Building Rafter...")
    __buildRafterForAll(buildingObj,rafter_pos)

    # 营造山墙，仅适用于硬山
    if bData.roof_style == con.ROOF_YINGSHAN:
        __buildShanWall(buildingObj,rafter_pos)
    # 营造象眼板，适用于歇山、悬山（卷棚）
    if bData.roof_style in (
            con.ROOF_XIESHAN,
            con.ROOF_XUANSHAN,
            con.ROOF_XUANSHAN_JUANPENG):
        __buildXiangyanBan(buildingObj,rafter_pos)
    # 营造博缝板，适用于歇山、悬山(卷棚)、硬山
    if bData.roof_style in (
            con.ROOF_XIESHAN,
            con.ROOF_XUANSHAN,
            con.ROOF_YINGSHAN,
            con.ROOF_XUANSHAN_JUANPENG):
        __buildBofeng(buildingObj,rafter_pos)

    # 设置材质，原木色
    for obj in rafterRootObj.children:
        mat.setShader(obj,
            mat.shaderType.WOOD)
        
    return

# 营造整个房顶
def buildRoof(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    # 添加“屋顶层”根节点
    # 斗栱层、梁椽望、瓦作都绑定在该节点下，便于统一重新生成
    # 这三层的结构紧密相连，无法解耦，只能一起生成，一起刷新
    __addRoofRoot(buildingObj)

    # 生成斗栱层
    if bData.is_showDougong:
        utils.outputMsg("Building Dougong...")
        buildDougong.buildDougong(buildingObj)

    # 生成梁椽望
    if bData.is_showBPW:
        utils.outputMsg("Building BPW...")
        __buildBPW(buildingObj)

    # 生成瓦作层
    if bData.is_showTiles:
        utils.outputMsg("Building Tiles...")
        buildRooftile.buildTile(buildingObj)
    
    utils.focusObj(buildingObj)
    return {'FINISHED'}