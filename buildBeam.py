# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   梁架的营造
import bpy
import bmesh
import math
from mathutils import Vector

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from .data import ACA_data_template as tmpData
from . import utils
from . import buildFloor
from . import texture as mat

# 设置“梁架”根节点
def __addBeamRoot(buildingObj:bpy.types.Object)->bpy.types.Object:
    # 设置目录
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('梁架',parentColl=buildingColl) 
    
    # 新建或清空根节点
    beamRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_BEAM_ROOT)
    # 清空梁架节点下的所有子节点
    if beamRootObj !=None:
        utils.deleteHierarchy(beamRootObj)
        utils.focusCollByObj(beamRootObj)
        return
    
    # 绑定在屋顶根节点下
    roofRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_ROOF_ROOT)

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

    # 创建梁架根对象
    beamRootObj = utils.addEmpty(
        name='梁架层',
        location=(0,0,zLoc),
        parent=roofRootObj
    )
    beamRootObj.ACA_data['aca_obj'] = True
    beamRootObj.ACA_data['aca_type'] = con.ACA_TYPE_BEAM_ROOT

    return beamRootObj

# 计算举架数据
# 1、根据不同的屋顶样式生成，自动判断了桁在檐面需要延长的长度
#    其中包括了举折做法，以及庑殿推山、歇山收山的做法
# 2、支持悬山的举架计算，自动扣除一个顶步架
# 3、支持“廊步架”做法，廊步架按柱网的廊间进深计算，其他步架再平分剩余的进深
# 4、根据是否带斗栱，自动判断了是否插入挑檐桁
# 5、根据建筑面阔进深，将举架数据转换为了桁檩转角交点
def getPurlinPos(buildingObj:bpy.types.Object):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    # 屋顶样式，1-庑殿，2-歇山，3-悬山，4-硬山
    roofStyle = bData.roof_style
    # 三组举折系数，可供选择
    lift_ratio = []
    if bData.juzhe == '0':
        lift_ratio = con.LIFT_RATIO_DEFAULT
    if bData.juzhe == '1':
        lift_ratio = con.LIFT_RATIO_BIG
    if bData.juzhe == '2':
        lift_ratio = con.LIFT_RATIO_SMALL

    # 开始构造槫子数据
    purlin_pos = []

    # 0、槫子布局起点
    purlinWidth = bData.x_total/2
    purlinDeepth = bData.y_total/2
    # 屋顶起点root在挑檐枋下皮，所以初始即上移半桁
    purlinHeight = con.HENG_TIAOYAN_D/2*dk
    # 硬山桁檩：做到梁的外皮
    if roofStyle in (
            con.ROOF_YINGSHAN,
            con.ROOF_YINGSHAN_JUANPENG):
        purlinWidth += con.BEAM_DEPTH*pd/2
    # 悬山（卷棚）：从山柱中加檐出（14斗口）
    if roofStyle in (
            con.ROOF_XUANSHAN,
            con.ROOF_XUANSHAN_JUANPENG):
        purlinWidth += con.YANCHUAN_EX*dk

    # 1、构造挑檐桁
    if (bData.use_dg                # 不使用斗栱的不用挑檐桁
        and bData.dg_extend > 0     # 一斗三升这种无出跳的，不用挑檐桁
        ):
        # 为了不改动起始点，另用变量计算挑檐桁
        purlinWidth_dg = purlinWidth
        # 庑殿、歇山、盝顶，做两山斗栱出跳
        if roofStyle in (
                con.ROOF_WUDIAN,
                con.ROOF_XIESHAN,
                con.ROOF_XIESHAN_JUANPENG,
                con.ROOF_LUDING):
            purlinWidth_dg = purlinWidth + bData.dg_extend
        # 插入挑檐桁等位点
        purlin_pos.append(Vector((
            purlinWidth_dg,
            purlinDeepth+bData.dg_extend,
            purlinHeight)))  
        # 补偿正心桁的抬升挑檐桁举折
        purlinHeight += bData.dg_extend*lift_ratio[0]

    # 2、构造正心桁
    purlin_pos.append(Vector((
            purlinWidth,
            purlinDeepth,
            purlinHeight,
        )))

    # 3、构造下金桁、上金桁、脊桁
    # 房屋总进深
    roomDepth = bData.y_total
    # 步架数量
    rafterCount = bData.rafter_count
    # 获取开间、进深数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    # 卷棚顶：顶层桁檩间距3椽径，要从进深中减去后，平分椽架
    if roofStyle in (
            con.ROOF_XUANSHAN_JUANPENG,
            con.ROOF_YINGSHAN_JUANPENG,
            con.ROOF_XIESHAN_JUANPENG,
        ):
        # 卷棚椽架排除“顶步架”，如果为奇数，自动扣除一步架
        roomDepth -= con.JUANPENG_SPAN*dk
        if rafterCount%2 != 0:
            rafterCount -= 1
            # 正常的奇变偶，不输出提示
    else:
        if rafterCount%2 != 0:
            rafterCount -= 1
            # 异常的奇变偶，给出提出
            utils.outputMsg("请留意：一般屋顶椽架数量应该为偶数（卷棚为奇数），所以，椽架数量自动减少了一椽架")
    for n in range(int(rafterCount/2)):
        # 1、计算每层步架的进深----------------
        # 20241123 根据尖山、卷棚、盝顶、是否做廊步架等计算每个步架长度
        # 判断是否做廊步架(至少4步架才能做廊步架，否则忽略)
        if bData.use_hallway and rafterCount>=4:
            if n==0 :
                # 廊步架宽度 = 柱网的廊间进深
                rafterSpan = abs(net_y[1]-net_y[0])
                rafterSpan0 = rafterSpan    # 檐步架宽度，后续使用
                roomDepth -= rafterSpan*2 # 从通进深扣除前后的两个廊步架
            else:
                # 其他步架平分
                rafterSpan = roomDepth/(rafterCount-2)
        else:
            # 不做廊步架，则所有步架平分
            rafterSpan = roomDepth/rafterCount
            rafterSpan0 = rafterSpan    # 檐步架宽度，后续使用
        # 盝顶：直接采用用户设置的参数
        if roofStyle == con.ROOF_LUDING:
            rafterSpan = bData.luding_rafterspan
            
        # 2、计算每根槫子的长度，包括推山做法、收山做法的影响--------------
        # 2.a、硬山、悬山（卷棚）不推
        if roofStyle in (con.ROOF_YINGSHAN,
                         con.ROOF_YINGSHAN_JUANPENG,
                         con.ROOF_XUANSHAN,
                         con.ROOF_XUANSHAN_JUANPENG):
            pass
        # 2.b、歇山，面阔方向，下金桁以上按收山法则
        elif (roofStyle in (
                    con.ROOF_XIESHAN,
                    con.ROOF_XIESHAN_JUANPENG,)
                and n>0):
                # 收山系统的选择，推荐一桁径以上，一步架以下
                # 当超出限制值时，自动设置为限制值
                # 注意：这里必须按照檐步架计算
                # 而且在廊间举架做法中，檐步架与其他步架宽度不同
                shoushanLimit = (
                    rafterSpan0                 # 檐步架
                    - con.BOFENG_WIDTH*dk       # 博缝板
                    - con.XYB_WIDTH*dk          # 山花板
                    - con.BEAM_DEPTH*pd/2       # 梁架中线
                    )
                if bData.shoushan > shoushanLimit:
                    bData['shoushan'] = shoushanLimit
                purlinWidth = (bData.x_total/2 
                        - con.BOFENG_WIDTH*dk   # 推山做到博缝板外皮
                        - bData.shoushan         # 用户自定义推山尺寸
                    )
        # 2.c、庑殿，下金桁以上，应用推山做法
        # 见马炳坚书p25，Xn= 0.9**n * X
        elif (roofStyle == con.ROOF_WUDIAN
            and n>0): 
            purlinWidth -= bData.tuishan**n*rafterSpan
        # 2.4、盝顶仅做到下金桁
        elif roofStyle== con.ROOF_LUDING and n >0:
            continue
        else:
            # 面阔、进深，每次推一个步架
            purlinWidth -= rafterSpan

        # 3. 计算每根槫子的举折
        # 3.a、进深Y方向的举折
        purlinDeepth -= rafterSpan
        # 3.b、举折：举架高度 = 步架 * 举架系数
        purlinHeight += rafterSpan*lift_ratio[n]

        # 4、存入槫子参数集合
        purlin_pos.append(Vector((
            purlinWidth,
            purlinDeepth,
            purlinHeight)))

    # 返回桁檩定位数据集
    return purlin_pos

# 营造桁檩
# 包括檐面和山面
# 其中对庑殿和歇山做了特殊处理
def __buildPurlin(buildingObj:bpy.types.Object,purlin_pos):
    # 一、载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    # 屋顶样式，1-庑殿，2-歇山，3-悬山，4-硬山
    roofStyle = bData.roof_style
    beamRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_BEAM_ROOT)
    
    # 收集桁架对象
    purlinFrameList = []
    
    # 挑檐桁为了便于彩画贴图，按开间逐一生成
    if (bData.use_dg                # 不使用斗栱的不用挑檐桁
        and bData.dg_extend > 0     # 一斗三升这种无出跳的，不用挑檐桁
        ):
        tiaoyanhengObj = __buildYanHeng(
                        beamRootObj,
                        purlin_cross=purlin_pos[0],
                        purlin_name='挑檐桁')
        purlinFrameList.append(tiaoyanhengObj)
        # 删除挑檐桁数据
        del purlin_pos[0]
    # 其他的桁为了效率，还是贯通整做成一根
    
    # 桁直径（正心桁、金桁、脊桁）
    purlin_r = con.HENG_COMMON_D / 2 * dk

    # 二、布置前后檐桁,根据上述计算的purlin_pos数据，批量放置桁对象
    for n in range(len(purlin_pos)) :
        # 1、桁交点
        pCross = purlin_pos[n]
        
        # 2、计算桁的长度====================
        # 四坡顶做交圈出梢
        if bData.roof_style in (
            con.ROOF_WUDIAN,
            con.ROOF_LUDING,
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
        ):
            purlin_length_x = (pCross.x * 2
                + con.HENG_EXTEND * dk)
        # 2坡顶，微微出梢
        else:
            purlin_length_x = pCross.x * 2 + 0.02
        # 脊桁出梢控制
        if n == len(purlin_pos)-1:
            # 庑殿脊桁出梢半个太平梁
            if bData.roof_style==con.ROOF_WUDIAN:
                purlin_length_x = (pCross.x * 2
                         + con.GABELBEAM_DEPTH*dk)
        # 歇山檐面的下金桁延长，与上层对齐
        if n >= 1:
            if roofStyle in (
                    con.ROOF_XIESHAN,
                    con.ROOF_XIESHAN_JUANPENG) :
                purlin_length_x = purlin_pos[-1].x * 2            
            
        # 241118 正心桁也做彩画
        if n==0:
            zhengxinhengObj = __buildYanHeng(
                            beamRootObj,
                            purlin_cross=purlin_pos[0],
                            purlin_name='正心桁')
            purlinFrameList.append(zhengxinhengObj)
        else:
            

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
                    parent=beamRootObj
                )
            # 其他一般情况下的槫子
            else:
                hengFB = utils.addCylinderHorizontal(
                        radius = purlin_r, 
                        depth = purlin_length_x,
                        location = loc, 
                        name = "桁-前后",
                        root_obj = beamRootObj
                    )
            purlinFrameList.append(hengFB)
            # 前后镜像
            if (
                    # 一般情况最后一根为脊桁，不做镜像
                    n!=len(purlin_pos)-1            
                    # 卷棚最后一根为脊桁，应该做前后的镜像
                    or (n==len(purlin_pos)-1 and    
                        bData.roof_style in (
                            con.ROOF_XUANSHAN_JUANPENG,
                            con.ROOF_YINGSHAN_JUANPENG,
                            con.ROOF_XIESHAN_JUANPENG,
                         )
                     )
                    # 盝顶最后一根为承椽枋，应该做前后镜像
                    or (n==len(purlin_pos)-1 and    
                        bData.roof_style==con.ROOF_LUDING)
                ):
                # 除最后一根脊桁的处理，挑檐桁、正心桁、金桁做Y镜像
                utils.addModifierMirror(
                        object=hengFB,
                        mirrorObj=beamRootObj,
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
                        root_obj = beamRootObj,
                        edge_num =6
                    )
                purlinFrameList.append(fujimuObj)
            # 倒角
            utils.addModifierBevel(hengFB,con.BEVEL_LOW)
        
        # 桁垫板 =======================================================
        # 250225 区分檐桁、金桁的不同垫板高度
        if n == 0 :
            board_h = con.BOARD_YANHENG_H
        else:
            board_h = con.BOARD_JINHENG_H
        # 有斗拱时，正心桁下不做垫板
        if not (bData.use_dg and n == 0):
            # 4、桁垫板
            # 定位
            loc = (0,pCross.y,
                (pCross.z - con.HENG_COMMON_D*dk/2
                    - board_h*dk/2))
            # 桁垫板长度
            dianbanL = purlin_length_x
            # 定尺寸
            dim = (dianbanL,
                con.BOARD_HENG_Y*dk,
                board_h*dk)
            # 创建桁垫板
            dianbanObj = utils.addCube(
                name="桁垫板",
                location=loc,
                dimension=dim,
                parent=beamRootObj,
            )
            purlinFrameList.append(dianbanObj)
            # 添加镜像
            if (
                    # 除了脊桁
                    n!=len(purlin_pos)-1  
                    # 或者卷棚的脊桁          
                    or (n==len(purlin_pos)-1 and    
                        bData.roof_style in (
                            con.ROOF_XUANSHAN_JUANPENG,
                            con.ROOF_YINGSHAN_JUANPENG,
                            con.ROOF_XIESHAN_JUANPENG,
                         )
                     )
                    # 或者盝顶的下金桁
                    or (n==len(purlin_pos)-1 and    
                        bData.roof_style==con.ROOF_LUDING)
                ) :
                utils.addModifierMirror(
                    object=dianbanObj,
                    mirrorObj=beamRootObj,
                    use_axis=(False,True,False)
                )
            # 导角
            utils.applyTransfrom(dianbanObj,use_scale=True)
            utils.addModifierBevel(dianbanObj,con.BEVEL_EXLOW)
        
        # 桁枋 =======================================================
        useHengFang = True
        # 正心桁下不做枋
        if n == 0: 
            useHengFang = False
        # 250213 下面这个逻辑没有看懂，暂时屏蔽，待观察
        # # 做廊步架时，金桁下不做枋
        # if bData.use_hallway and n == 1:
        #     useHengFang = False
        
        if useHengFang: 
            # 5、桁枋
            loc = (0,pCross.y,
                (pCross.z - con.HENG_COMMON_D*dk/2
                    - board_h*dk
                    - con.HENGFANG_H*dk/2))
            # 桁枋长度
            hengfangL = purlin_length_x
            dim = (hengfangL,
                con.HENGFANG_Y*dk,
                con.HENGFANG_H*dk)
            hengfangObj = utils.addCube(
                name="金/脊枋",
                location=loc,
                dimension=dim,
                parent=beamRootObj,
            )
            purlinFrameList.append(hengfangObj)
            if (
                    # 除了脊桁
                    n!=len(purlin_pos)-1  
                    # 或者卷棚的脊桁          
                    or (n==len(purlin_pos)-1 and    
                        bData.roof_style in (
                            con.ROOF_XUANSHAN_JUANPENG,
                            con.ROOF_YINGSHAN_JUANPENG,
                            con.ROOF_XIESHAN_JUANPENG,
                         )
                     )
                    # 或者盝顶的下金桁
                    or (n==len(purlin_pos)-1 and    
                        bData.roof_style==con.ROOF_LUDING)
                ):
                utils.addModifierMirror(
                    object=hengfangObj,
                    mirrorObj=beamRootObj,
                    use_axis=(False,True,False)
                )  
            utils.applyTransfrom(hengfangObj,use_scale=True)
            # 倒角
            utils.addModifierBevel(hengfangObj,con.BEVEL_LOW)

        # 设色 =======================================================
        # 根据需要刷红漆，否则默认做原木色       
        # 无斗拱时，正心桁下刷红漆
        if n==0 and not bData.use_dg:
            mat.setMat(dianbanObj,aData.mat_red)

        # 金桁如果做承椽枋、垫板、枋，则涂红
        if n==1 and bData.roof_style == con.ROOF_LUDING:
            mat.setMat(hengFB,aData.mat_red)
            mat.setMat(dianbanObj,aData.mat_red)
            mat.setMat(hengfangObj,aData.mat_red)

    # 三、布置山面桁檩
    # 仅庑殿、歇山做山面桁檩，硬山、悬山不做山面桁檩
    if roofStyle in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
            con.ROOF_LUDING):
        if roofStyle == con.ROOF_WUDIAN :
            # 庑殿的上面做所有桁檩，除脊桁
            rafterRange = range(len(purlin_pos)-1)
        if roofStyle in (
                con.ROOF_XIESHAN,
                con.ROOF_XIESHAN_JUANPENG):
            # 歇山仅做正心桁、下金桁
            rafterRange = range(2)
        if roofStyle == con.ROOF_LUDING:
            rafterRange = range(len(purlin_pos))
        for n in rafterRange :
            pCross = purlin_pos[n]
            # 2、计算桁的长度
            # 四坡顶做交圈出梢
            purlin_length_y = (pCross.y * 2
                + con.HENG_EXTEND * dk)

            # 241118 正心桁做彩画
            if n==0: 
                # 在前后檐做正心桁彩画时通过__buildYanHeng已经做了山面正心桁
                # 这里就不在需要做处理了
                pass
            else:
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
                        parent=beamRootObj
                    )
                # 其他一般情况下的槫子
                else:
                    hengLR = utils.addCylinderHorizontal(
                            radius = purlin_r, 
                            depth = purlin_length_y,
                            location = (pCross.x,0,pCross.z), 
                            rotation=Vector((0, 0, math.radians(90))), 
                            name = "桁-两山",
                            root_obj = beamRootObj
                        )
                purlinFrameList.append(hengLR)
                utils.addModifierMirror(
                        object=hengLR,
                        mirrorObj=beamRootObj,
                        use_axis=(True,False,False)
                    )
                # 倒角
                utils.addModifierBevel(hengLR,con.BEVEL_LOW)
            
            # 判断垫板、枋的逻辑
            use_dianban = True
            use_fang = True
            # 歇山的踩步金下不做
            if roofStyle in (con.ROOF_XIESHAN,
                             con.ROOF_XIESHAN_JUANPENG) :
                if n==1:
                    use_fang = False
                    use_dianban = False
            # 正心桁下不做枋
            # 有斗栱时，正心桁下不做垫板
            if roofStyle in (
                    con.ROOF_WUDIAN,
                    con.ROOF_XIESHAN,
                    con.ROOF_XIESHAN_JUANPENG,
                    con.ROOF_LUDING,) and n==0:
                use_fang = False
                if bData.use_dg:
                    use_dianban = False
            # 4坡顶，金桁下不做枋（排除盝顶）
            if roofStyle in (
                    con.ROOF_WUDIAN,
                    con.ROOF_XIESHAN,
                    con.ROOF_XIESHAN_JUANPENG,) and n==1:
                 use_fang = False
            # 250225 区分檐桁、金桁的不同垫板高度
            if n == 0 :
                board_h = con.BOARD_YANHENG_H
            else:
                board_h = con.BOARD_JINHENG_H
            # 桁垫板
            if use_dianban:
                loc = (pCross.x,0,
                    (pCross.z - con.HENG_COMMON_D*dk/2
                        - board_h*dk/2))
                # 桁垫板长度
                dianbanL = purlin_length_y
                dim = (dianbanL,
                    con.BOARD_HENG_Y*dk,
                    board_h*dk)
                dianbanObj = utils.addCube(
                    name="垫板",
                    location=loc,
                    dimension=dim,
                    rotation=Vector((0, 0, math.radians(90))),
                    parent=beamRootObj,
                )
                purlinFrameList.append(dianbanObj)
                # 无斗拱，第一层垫板刷红漆
                if n==0 and not bData.use_dg:
                    mat.setMat(dianbanObj,aData.mat_red)
                # 镜像
                utils.addModifierMirror(
                    object=dianbanObj,
                    mirrorObj=beamRootObj,
                    use_axis=(True,False,False)
                )
                # 导角
                utils.applyTransfrom(dianbanObj,use_scale=True)
                # 倒角
                utils.addModifierBevel(dianbanObj,con.BEVEL_EXLOW)
            # 桁枋
            if use_fang:
                loc = (pCross.x,0,
                    (pCross.z - con.HENG_COMMON_D*dk/2
                        - board_h*dk
                        - con.HENGFANG_H*dk/2))
                # 桁枋长度
                hengfangL = purlin_length_y
                dim = (hengfangL,
                    con.HENGFANG_Y*dk,
                    con.HENGFANG_H*dk)
                hengfangObj = utils.addCube(
                    name="金/脊枋",
                    location=loc,
                    rotation=Vector((0, 0, math.radians(90))),
                    dimension=dim,
                    parent=beamRootObj,
                )
                purlinFrameList.append(hengfangObj)
                utils.addModifierMirror(
                    object=hengfangObj,
                    mirrorObj=beamRootObj,
                    use_axis=(True,False,False)
                )
                utils.applyTransfrom(hengfangObj,use_scale=True)
                # 倒角
                utils.addModifierBevel(hengfangObj,con.BEVEL_LOW)

            # 金桁如果做承椽枋、垫板、枋，则涂红
            if n==1 and bData.roof_style == con.ROOF_LUDING:
                mat.setMat(hengLR,aData.mat_red)
                mat.setMat(dianbanObj,aData.mat_red)
                mat.setMat(hengfangObj,aData.mat_red)

    # 设置材质
    for obj in purlinFrameList:
        mat.setMat(obj,aData.mat_wood)
    # 合并桁对象
    purlinFrameObj = utils.joinObjects(purlinFrameList,'桁架')      
    return

# 檐桁为了便于彩画贴图，按开间逐一生成
# 其他的桁为了效率，还是贯通整做成一根
def __buildYanHeng(rafterRootObj:bpy.types.Object,
                   purlin_cross,purlin_name):
    # 载入数据
    buildingObj = utils.getAcaParent(
        rafterRootObj,con.ACA_TYPE_BUILDING)
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    # 获取开间、进深数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)

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
        # 241118 无论是否有斗拱都应该出梢
        hengExtend += con.HENG_EXTEND*dk /2
    # 四坡顶用斗拱时，如果是挑檐桁增加斗栱出跳
    if bData.roof_style in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
            con.ROOF_LUDING):
        # 是否用斗栱
        if bData.use_dg:
            # 是否为挑檐桁
            if abs(purlin_cross.x) - abs(net_x[0]) > 0.001:
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
        # 类似做大小额枋，也在挑檐桁上做ID
        fangID = "%s/%s#%s/%s" % (n,0,n+1,0)
        purlinList.append(
            {'len':length,
             'loc':loc,
             'rot':(0,0,math.radians(180)),
             'mirror':(False,True,False),
             'id': fangID,
             })
             
    # 两山排布(仅庑殿、歇山、盝顶，不适用硬山、悬山、卷棚)
    if bData.roof_style in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
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
            # 类似做大小额枋，也在挑檐桁上做ID
            fangID = "%s/%s#%s/%s" % (0,n,0,n+1)
            purlinList.append(
                {'len':length,
                'loc':loc,
                'rot':(0,0,math.radians(90)),
                'mirror':(True,False,False),
                'id': fangID,
                })
    
    # 生成所有的挑檐桁
    purlinObjs = []
    for purlin in purlinList:
        hengObj = utils.addCylinderHorizontal(
            radius= con.HENG_COMMON_D / 2 * dk,
            depth = purlin['len'],
            location = purlin['loc'], 
            rotation = purlin['rot'],
            name = purlin_name,
            root_obj = rafterRootObj,
        )
        purlinObjs.append(hengObj)
        # 传入id，便于后续做彩画时判断异色
        hengObj.ACA_data['fangID'] = purlin['id']
        # 设置梁枋彩画
        mat.setMat(hengObj,aData.mat_paint_beam_small)
        # 设置对称
        utils.addModifierMirror(
            object=hengObj,
            mirrorObj=rafterRootObj,
            use_axis=purlin['mirror']
        )

    # 合并檐桁
    yanhengObj = utils.joinObjects(purlinObjs)
    
    return yanhengObj

# 绘制趴梁造型
def __drawGabelBeam(name='趴梁',
            location=(0,0,0),
            rotation=(0,0,0),
            dimension=(1,1,1),
            parent=None):
    gabelBeam = utils.addCube(
            name=name,
            location=location,
            dimension=dimension,
            parent=parent,
        )
    # 挤压8号边
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.new()
    bm = bmesh.from_edit_mesh(gabelBeam.data)
    bpy.ops.mesh.select_mode(type = 'EDGE')
    bm.edges.ensure_lookup_table()
    bpy.ops.mesh.select_all(action = 'DESELECT')
    bm.edges[8].select = True
    bpy.ops.mesh.bevel(affect='EDGES',
                offset_type='OFFSET',
                offset=dimension.z*0.75,
                segments=1,
                )
    bmesh.update_edit_mesh(gabelBeam.data ) 
    bm.free() 
    bpy.ops.object.mode_set( mode = 'OBJECT' )

    # 倒角
    utils.addModifierBevel(gabelBeam,con.BEVEL_HIGH,
                           type='WIDTH')

    return gabelBeam

# 添加庑殿顶山面的顺趴梁
def __addGabelBeam(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    beamRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_BEAM_ROOT)
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    
    # 六架以上，才能做顺趴梁
    if bData.rafter_count < 6:
        return
    else:
        # 庑殿的趴梁
        if bData.roof_style == con.ROOF_WUDIAN:
            beamRange = range(0,len(purlin_pos)-2)
        # 歇山的趴梁只从正心桁向上做一根
        if bData.roof_style in (con.ROOF_XIESHAN,
                     con.ROOF_XIESHAN_JUANPENG):
            beamRange = range(1)

    # 查找山面梁架的位置
    # 根据廊间等面阔的不同，第一幅梁架可能在第二根柱上，也可能在第三根柱子上
    beamX = 0
    for n in range(len(net_x)):
        px = abs(net_x[n])
        # 判断梁架是否与脊槫相交
        if (px < abs(purlin_pos[-1].x) ):
            beamX = px
            break
    
    gabelBeamList = []
    for n in beamRange:
        use_beam = True
        use_tuo = True
        # 廊间举架的下金桁下，只做坨橔，不做趴梁
        # 判断第一层山面梁架的做法（下金桁位置，从山面金柱到内圈金柱）
        if (n==0 
            and bData.use_dg
            and bData.use_hallway):
            # 做廊间举架、且有斗拱时，金桁交圈用坨橔支撑在山面的桃尖顺梁上
            # 此时不必做趴梁，仅做坨橔
            use_beam = False

        # 如果找不到梁架，极端情况可能没有，取上层槫子坐标
        if beamX == 0:
            beamX = purlin_pos[n+1].x
        # 1、趴梁定位
        loc = Vector((
                # 取桁檩到梁架的中点
                (abs(purlin_pos[n].x)+beamX)/2,
                # 取上一层桁檩的Y坐标
                purlin_pos[n+1].y,
                # 梁下皮与本层桁檩中线平
                (purlin_pos[n].z 
                    + con.GABELBEAM_HEIGHT*dk/2)
            ))
        # 2、趴梁定尺寸
        length = abs(purlin_pos[n].x)-beamX
        # 趴梁高6.5dk，厚5.2dk
        dim = Vector((
            length,
            con.GABELBEAM_DEPTH*dk,
            con.GABELBEAM_HEIGHT*dk
        ))
        # 3、创建趴梁
        if use_beam:
            gabelBeam = __drawGabelBeam(
                name="趴梁",
                location=loc,
                dimension=dim,
                parent=beamRootObj,
            )
            gabelBeamList.append(gabelBeam)
            utils.addModifierMirror(
                object=gabelBeam,
                mirrorObj=beamRootObj,
                use_axis=(True,True,False)
            )
        # 4、创建坨橔
        if use_tuo:
            tuodunHeight = purlin_pos[n+1].z - purlin_pos[n].z 
            if use_beam:
                tuodunHeight -= con.GABELBEAM_HEIGHT*dk
            # 250225 如果廊间举架
            # 且檐面廊间面阔与山面廊间进深相当
            # 此时坨橔直接立于柱头上
            if (n==0 and bData.use_hallway
                and net_x[1]-net_x[0] == net_y[1]-net_y[0]):
                # 坨橔高度从桁中线，做到梁底（一个金桁垫板）
                tuodunHeight = (con.BOARD_JINHENG_H*dk
                                + con.HENG_COMMON_D*dk/2)
            
            tuodunLoc = purlin_pos[n+1] - Vector((0,0,tuodunHeight/2))
            tuodunDim = Vector((
                con.GABELBEAM_DEPTH*dk,
                con.GABELBEAM_DEPTH*dk,
                tuodunHeight
            ))
            tuodunObj = utils.addCube(
                name='坨橔',
                location=tuodunLoc,
                dimension=tuodunDim,
                parent=beamRootObj,
            )
            gabelBeamList.append(tuodunObj)
            # 倒角
            utils.addModifierBevel(tuodunObj,con.BEVEL_HIGH,
                                   type='WIDTH')
            utils.addModifierMirror(
                object=tuodunObj,
                mirrorObj=beamRootObj,
                use_axis=(True,True,False)
            )
    
    # 合并趴梁
    gabelBeamJoined = utils.joinObjects(
        gabelBeamList,'趴梁')
    
    return gabelBeamJoined

# 绘制太平梁造型
def __drawSaftBeam(name='太平梁',
            location=(0,0,0),
            rotation=(0,0,0),
            dimension=(1,1,1),
            parent=None):
    safeBeam = utils.addCube(
            name=name,
            location=location,
            dimension=dimension,
            parent=parent,
        )
    # 挤压5和11号边
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.new()
    bm = bmesh.from_edit_mesh(safeBeam.data)
    bpy.ops.mesh.select_mode(type = 'EDGE')
    bm.edges.ensure_lookup_table()
    bpy.ops.mesh.select_all(action = 'DESELECT')
    bm.edges[5].select = True
    bm.edges[11].select = True
    bpy.ops.mesh.bevel(affect='EDGES',
                offset_type='OFFSET',
                offset=dimension.z*0.75,
                segments=1,
                )
    bmesh.update_edit_mesh(safeBeam.data ) 
    bm.free() 
    bpy.ops.object.mode_set( mode = 'OBJECT' )

    # 倒角
    utils.addModifierBevel(safeBeam,con.BEVEL_HIGH,
                           type='WIDTH')

    return safeBeam

# 庑殿顶添加太平梁
def __addSafeBeam(buildingObj,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    beamRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_BEAM_ROOT)
    saftBeamList = []
    
    # 查找山面梁架的位置
    # 根据廊间等面阔的不同，第一幅梁架可能在第二根柱上，也可能在第三根柱子上
    beamX = 0
    for n in range(len(net_x)):
        px = abs(net_x[n])
        # 判断梁架是否与脊槫相交
        if (px < abs(purlin_pos[-1].x) ):
            beamX = px
            break
    
    if beamX != 0:
        # 判断是否有足够空间架设太平梁，否则就取消绘制
        # 计算脊桁端头到梁架外皮的宽度
        span = (purlin_pos[-1].x        # 桁交点
                + con.HENG_EXTEND*dk/2  # 桁出梢
                - (beamX + con.BEAM_DEPTH*pd/2))    # 梁架外皮
        if span < con.GABELBEAM_DEPTH*dk:
            # 取消以下绘制
            return
    
    # 1、太平梁定位
    # 定位在脊桁定位点
    x = purlin_pos[-1].x
    loc = Vector((x,0,
            # 梁下皮与下层桁檩中线平
            (purlin_pos[-2].z 
                + con.GABELBEAM_HEIGHT*dk/2)
        ))
    # 2、太平梁定尺寸
    length = purlin_pos[-2].y * 2
    # 趴梁高6.5dk，厚5.2dk
    dim = Vector((
        con.GABELBEAM_DEPTH*dk,
        length,
        con.GABELBEAM_HEIGHT*dk
    ))
    # 3、创建太平梁
    safeBeam = __drawSaftBeam(
        name="太平梁",
        location=loc,
        dimension=dim,
        parent=beamRootObj,
    )
    saftBeamList.append(safeBeam)
    utils.addModifierMirror(
            object=safeBeam,
            mirrorObj=beamRootObj,
            use_axis=(True,False,False)
        )
    # 4、立坨橔/蜀柱
    tuodunHeight = (purlin_pos[-1].z - purlin_pos[-2].z
                  - con.GABELBEAM_HEIGHT*dk)       
    tuodunLoc = Vector((
        x,
        0,
        purlin_pos[-1].z - tuodunHeight/2
    )) 
    tuodunDim = Vector((
        con.GABELBEAM_DEPTH*dk,
        con.GABELBEAM_DEPTH*dk,
        tuodunHeight
    ))
    tuodunObj = utils.addCube(
        name='坨橔',
        location=tuodunLoc,
        dimension=tuodunDim,
        parent=beamRootObj,
    )
    saftBeamList.append(tuodunObj)
    # 倒角
    utils.addModifierBevel(tuodunObj,con.BEVEL_HIGH,
                           type='WIDTH')
    utils.addModifierMirror(
        object=tuodunObj,
        mirrorObj=beamRootObj,
        use_axis=(True,False,False)
    )

    # 合并太平梁
    safeBeamJoined = utils.joinObjects(saftBeamList,'太平梁')

    return safeBeamJoined

# 营造梁架
# 自动根据是否做廊间举架，判断采用通檐大梁，或是抱头梁
def __buildBeam(buildingObj:bpy.types.Object,purlin_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    beamRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_BEAM_ROOT)
    
    # 收集所有梁架，便于后续合并
    beamObjects = []

    # 在梁架的计算中不考虑挑檐桁
    if (bData.use_dg                # 不使用斗栱的不用挑檐桁
        and bData.dg_extend > 0     # 一斗三升这种无出跳的，不用挑檐桁
        ):
        del purlin_pos[0]

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
        if (bData.roof_style in (con.ROOF_XIESHAN,
                                 con.ROOF_XIESHAN_JUANPENG,)
            and abs(net_x[x]) > purlin_pos[-1].x - con.HENG_EXTEND*dk
            and x not in (0,len(net_x)-1)):
            # 忽略此副梁架
            continue

        # 纵向循环每一层梁架
        for n in range(len(purlin_pos)):  
            # 1、横梁属性             
            # X向随槫交点依次排列
            beam_x = net_x[x]
            beam_z = purlin_pos[n].z
            beam_l = purlin_pos[n].y*2 + con.HENG_COMMON_D*dk*2
            beam_name = '梁'
            use_beam = True
            
            # 有斗拱时，不做底层大梁（一般从桃尖梁后尾连做）
            if (n==0 and bData.use_dg):
                use_beam = False
            
            # 廊间举架，且有斗拱时，不做底层横梁（斗栱自带桃尖梁）
            # 廊间举架，无斗栱时，做抱头梁，见下面的抱头梁处理
            if (n==0 and bData.use_hallway 
                and bData.use_dg):
                use_beam = False

            # 脊槫不做横梁（但是卷棚顶步架有横梁）
            if n==len(purlin_pos)-1 and \
                bData.roof_style not in (
                    con.ROOF_XUANSHAN_JUANPENG,
                    con.ROOF_YINGSHAN_JUANPENG,
                    con.ROOF_XIESHAN_JUANPENG,):
                use_beam = False
            
            # 歇山特殊处理：做排山梁架
            # 将两山柱对应的梁架，偏移到金桁交点
            if (roofStyle in (con.ROOF_XIESHAN,
                              con.ROOF_XIESHAN_JUANPENG)
                and x in (0,len(net_x)-1)):
                # 第一层不做（排山梁架不坐在柱头）
                if n == 0: 
                    use_beam = False
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

            # 开始做横梁
            if use_beam:
                # 梁定位
                beam_loc = Vector((beam_x,0,beam_z))
                beam_dim = Vector((
                    con.BEAM_DEPTH*pd,
                    beam_l,
                    con.BEAM_HEIGHT*pd
                ))
                # 绘制梁mesh，包括梁头形状
                # 识别是否为首层梁，在绘制时檐桁垫板和金桁垫板高度不同
                if n==0: 
                    isFirst = True
                else: 
                    isFirst = False
                beamCopyObj = __drawBeam(
                    location=beam_loc,
                    dimension=beam_dim,
                    buildingObj=buildingObj,
                    name = beam_name,
                    isFirst=isFirst,
                )
                beamCopyObj.parent= beamRootObj
                beamObjects.append(beamCopyObj)
                # 无斗拱的首层梁刷红漆，否则做木色
                if not bData.use_dg and n==0:
                    mat.setMat(beamCopyObj,aData.mat_red)
                
                # 抱头梁做法
                BaotouliangLength = 0
                # 廊间举架，且无斗拱时，最下层做抱头梁
                if (n==0 
                    and bData.use_hallway 
                    and not bData.use_dg):
                    # 取廊间进深
                    BaotouliangLength = (abs(net_y[1]-net_y[0])
                                        - bData.piller_diameter/4)
                # 盝顶仅做抱头梁
                if roofStyle == con.ROOF_LUDING:
                    BaotouliangLength = (bData.luding_rafterspan
                                        - bData.piller_diameter/4)
                if BaotouliangLength != 0:
                    # 剪切到金柱位置
                    # 20250109 添加坐标全局转换
                    pStart = beamRootObj.matrix_world @ Vector((0,0,0))
                    pEnd = beamRootObj.matrix_world @ Vector((1,0,0))
                    pCut = beamRootObj.matrix_world @ Vector((
                            0,
                            bData.y_total/2 - BaotouliangLength,
                            0))
                    utils.addBisect(
                        object=beamCopyObj,
                        pStart=pStart,
                        pEnd=pEnd,
                        pCut=pCut,
                        clear_inner=True,
                    )
                    utils.addModifierMirror(
                        object=beamCopyObj,
                        mirrorObj=beamRootObj,
                        use_axis=(False,True,False),
                    )
            
            # 开始做蜀柱和缴背===============
            useShuzhu = True
            # 在梁上添加蜀柱
            # 尖山顶脊槫处不做蜀柱（卷棚下有蜀柱）
            if n==len(purlin_pos)-1 and \
                bData.roof_style not in (
                    con.ROOF_XUANSHAN_JUANPENG,
                    con.ROOF_YINGSHAN_JUANPENG,
                    con.ROOF_XIESHAN_JUANPENG,):
                useShuzhu = False
            # 歇山山面第一层不做蜀柱
            if (roofStyle in (con.ROOF_XIESHAN,
                              con.ROOF_XIESHAN_JUANPENG)
                    and n==0 and x in (0,len(net_x)-1)):
                useShuzhu = False
            # 卷棚的脊槫处不做蜀柱
            if (roofStyle in (
                        con.ROOF_XUANSHAN_JUANPENG,
                        con.ROOF_YINGSHAN_JUANPENG,
                        con.ROOF_XIESHAN_JUANPENG,
                    ) 
                    and n==len(purlin_pos)-1):
                useShuzhu = False
            # 做抱头梁时不做蜀柱（盝顶、廊间举架等）
            if (roofStyle == con.ROOF_LUDING):
                useShuzhu = False
            # 廊间举架，不做第一层蜀柱（大梁坐柱头）
            if (n==0 and bData.use_hallway):
                useShuzhu = False
            if useShuzhu:
                # 250225 区分檐桁、金桁的不同垫板高度
                if n == 0 :
                    board_h = con.BOARD_YANHENG_H
                else:
                    board_h = con.BOARD_JINHENG_H
                # 计算蜀柱高度
                # 梁肩高度，以梁高 - 半桁径 - 桁垫板
                beamShoulderHeight = (con.BEAM_HEIGHT*pd 
                                - con.HENG_COMMON_D*dk/2
                                - board_h*dk)
                # 首层蜀柱
                if n==0: 
                    # 如果有斗拱，一层蜀柱坐在桃尖梁上
                    if bData.use_dg:
                        # 注意：这里扣减的应该是金桁垫板高度，而不是檐桁垫板高度
                        board_h = con.BOARD_JINHENG_H
                        shuzhu_height = (purlin_pos[n+1].z 
                                        - purlin_pos[n].z 
                                        - con.HENG_COMMON_D*dk/2
                                        - board_h*dk)
                        # 桃尖梁没有梁肩
                        beamShoulderHeight = 0
                    # 首层蜀柱，如果无斗拱，补偿檐桁垫板和金桁垫板的高度差
                    else:
                        shuzhu_height = (purlin_pos[n+1].z 
                                        - purlin_pos[n].z 
                                        - con.BEAM_HEIGHT*pd)
                        shuzhu_height += (con.BOARD_YANHENG_H*dk
                                        -con.BOARD_JINHENG_H*dk)
                # 非卷棚顶的最后一根蜀柱，直接支撑到脊槫
                elif (n == len(purlin_pos)-2 and 
                        roofStyle not in (
                            con.ROOF_XUANSHAN_JUANPENG,
                            con.ROOF_YINGSHAN_JUANPENG,
                            con.ROOF_XIESHAN_JUANPENG,
                        )
                    ):
                    shuzhu_height = (purlin_pos[n+1].z 
                                    - purlin_pos[n].z
                                    - beamShoulderHeight)
                # 其他的一般情况，支撑到上下两根梁之间
                else:
                    shuzhu_height = (purlin_pos[n+1].z
                                    - purlin_pos[n].z 
                                    - con.BEAM_HEIGHT*pd)
                shuzhu_loc = Vector((
                    beam_x,   # X向随槫交点依次排列
                    purlin_pos[n+1].y, # 对齐上一层的槫的Y位置
                    purlin_pos[n].z + shuzhu_height/2 + beamShoulderHeight
                ))
                shuzhu_dimensions = Vector((
                    con.PILLER_CHILD*dk,
                    con.PILLER_CHILD*dk,
                    shuzhu_height
                ))                
                shuzhuCopyObj = utils.addCube(
                    name="蜀柱",
                    location=shuzhu_loc,
                    dimension=shuzhu_dimensions,
                    parent=beamRootObj,
                )
                if n!=len(purlin_pos)-1:
                    #镜像
                    utils.addModifierMirror(
                        shuzhuCopyObj,
                        mirrorObj=beamRootObj,
                        use_axis=(False,True,False),
                        use_bisect=(False,True,False)
                    )
                beamObjects.append(shuzhuCopyObj)

                # 蜀柱添加角背
                jiaobeiObj = __drawJiaobei(shuzhuCopyObj)
                if jiaobeiObj != None:
                    beamObjects.append(jiaobeiObj)
    
    # 如果为庑殿顶
    if roofStyle == con.ROOF_WUDIAN:
        # 添加山面趴梁
        gabelBeamObj = __addGabelBeam(buildingObj,purlin_pos)
        if gabelBeamObj != None:
            beamObjects.append(gabelBeamObj)
        # 添加太平梁
        safeBeamObj = __addSafeBeam(buildingObj,purlin_pos)
        if safeBeamObj != None:
            beamObjects.append(safeBeamObj)

    # 如果为歇山顶
    if roofStyle in (con.ROOF_XIESHAN,
                     con.ROOF_XIESHAN_JUANPENG):
        # 添加山面趴梁
        gabelBeamObj = __addGabelBeam(buildingObj,purlin_pos)
        if gabelBeamObj != None:
            beamObjects.append(gabelBeamObj)

    # 攒尖顶时，没有做梁架
    if beamObjects != []:
        # 设置材质
        for beamobj in beamObjects:
            mat.setMat(beamobj,aData.mat_wood)
        # 合并
        beamSetObj = utils.joinObjects(
            beamObjects,newName='梁架')
        # 倒角
        utils.addModifierBevel(beamSetObj,con.BEVEL_HIGH)
    else:
        beamSetObj = None
                           
    return beamSetObj

# 营造梁架层，包括桁檩、梁架
def buildBeamFrame(buildingObj:bpy.types.Object):
    # 设定“梁架”根节点
    beamRootObj = __addBeamRoot(buildingObj)

    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp

    # 计算桁檩定位点
    purlin_pos = getPurlinPos(buildingObj)
    
    # 摆放桁架
    __buildPurlin(buildingObj,purlin_pos.copy())

    # 摆放梁架
    __buildBeam(buildingObj,purlin_pos.copy())
        
    return

# 绘制梁
# 参考马炳坚p149
def __drawBeam(
        location:Vector,
        dimension:Vector,
        buildingObj:bpy.types.Object,
        name='梁',
        isFirst=False,  # 是否为首层梁
        ):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    bWidth = dimension.x
    bLength = dimension.y
    bHeight = dimension.z
    if isFirst:
        board_h = con.BOARD_YANHENG_H
    else:  
        board_h = con.BOARD_JINHENG_H

    # 梁头与横梁中线齐平
    p1 = Vector((0,bLength/2,0))
    # 梁底，从P1向下半檩径+垫板高度
    p2 = p1 - Vector((0,0,
        con.HENG_COMMON_D*dk/2+board_h*dk))
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
              - board_h*dk
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

    # 原点在对应桁檩的Z高度，X一般对应到柱头，Y一般为0
    # 新建mesh
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    # 新建Object
    beamObj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(beamObj) 
    beamObj.location = location

    return beamObj

# 绘制角背
def __drawJiaobei(shuzhuObj:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(
        shuzhuObj,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    
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
    jiaobeiObj = utils.addCube(
        name='角背',
        location=loc,
        dimension=dim,
        parent=shuzhuObj.parent,
    )
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

    utils.copyModifiers(
        from_0bj=shuzhuObj,
        to_obj=jiaobeiObj)
    
    return jiaobeiObj