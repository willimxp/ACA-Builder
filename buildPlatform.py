# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   台基的营造
import bpy
import math
import bmesh
from mathutils import Vector,Euler

from . import utils
from . import buildFloor
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData

# 构造台基的几何细节
def __drawPlatform(platformObj:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(
        platformObj,con.ACA_TYPE_BUILDING
    )
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    (pWidth,pDeepth,pHeight) = platformObj.dimensions
    # 计算柱网数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)

    # 台基第一层
    # 方砖缦地
    brickObj = utils.addCube(
        name='方砖缦地',
        location=(
            0,0,
            pHeight/2-con.STEP_HEIGHT/2
        ),
        scale=(
            bData.x_total+bData.piller_diameter*2,
            bData.y_total+bData.piller_diameter*2,
            con.STEP_HEIGHT
        ),
        parent=platformObj
    )
    # UV处理
    utils.UvUnwrap(brickObj,type='cube')
    # 方砖缦地
    utils.copyMaterial(bData.mat_brick_1,brickObj)

    # 阶条石
    jtsObjs = []    # 收集待合并的阶条石
    # 阶条石宽度，从台基边缘做到柱顶石边缘
    stoneWidth = bData.platform_extend-bData.piller_diameter

    # 前后檐面阶条石，两头置好头石，尽间为去除好头石长度，明间(次间)对齐
    # 插入第一点，到台明两山尽头（从角柱延伸台基下出长度）
    firstRoomWidth = net_x[1]-net_x[0]    # 尽间宽度
    net_x.insert(0,net_x[0]-bData.platform_extend)
    net_x.append(net_x[-1]+bData.platform_extend)
    # 调整第二点，即好头石长度
    net_x[1] = net_x[0] + ((firstRoomWidth 
                + bData.platform_extend)
                * con.FIRST_LENGTH)
    net_x[-2] = net_x[-1] - ((firstRoomWidth 
                + bData.platform_extend)
                * con.FIRST_LENGTH)
    # 依次做出前后檐阶条石
    for n in range((len(net_x)-1)):
        brickObj = utils.addCube(
            name='阶条石',
            location=(
                (net_x[n+1]+net_x[n])/2,
                pDeepth/2-stoneWidth/2,
                pHeight/2-con.STEP_HEIGHT/2
            ),
            scale=(
                net_x[n+1]-net_x[n],
                stoneWidth,
                con.STEP_HEIGHT
            ),
            parent=platformObj
        )
        # 上下镜像
        utils.addModifierMirror(
            object=brickObj,
            mirrorObj=platformObj,
            use_axis=(False,True,False)
        )
        jtsObjs.append(brickObj)

    # 两山阶条石
    # 延长尽间阶条石，与好头石相接
    net_y[0] -= bData.piller_diameter
    net_y[-1] += bData.piller_diameter
    # 依次做出前后檐阶条石
    for n in range((len(net_y)-1)):
        brickObj = utils.addCube(
            name='阶条石',
            location=(
                pWidth/2-stoneWidth/2,
                (net_y[n+1]+net_y[n])/2,
                pHeight/2-con.STEP_HEIGHT/2
            ),
            scale=(
                stoneWidth,
                net_y[n+1]-net_y[n],
                con.STEP_HEIGHT
            ),
            parent=platformObj
        )
        # 上下镜像
        utils.addModifierMirror(
            object=brickObj,
            mirrorObj=platformObj,
            use_axis=(True,False,False)
        )
        jtsObjs.append(brickObj)

    # 埋头角柱
    # 角柱高度：台基总高度 - 阶条石 - 土衬
    cornerPillerH = (pHeight 
            - con.STEP_HEIGHT 
             - con.GROUND_BORDER) 
    brickObj = utils.addCube(
        name='埋头角柱',
        location=(
            pWidth/2-stoneWidth/2,
            pDeepth/2-stoneWidth/2,
            (pHeight/2
             -con.STEP_HEIGHT
             -cornerPillerH/2)
        ),
        scale=(
            stoneWidth,             # 与阶条石同宽
            stoneWidth,             # 与阶条石同宽
            cornerPillerH
        ),
        parent=platformObj
    )
    # 四面镜像
    utils.addModifierMirror(
        object=brickObj,
        mirrorObj=platformObj,
        use_axis=(True,True,False)
    )
    jtsObjs.append(brickObj)

    # 第二层，陡板
    h = pHeight - con.STEP_HEIGHT - con.GROUND_BORDER
    brickObj = utils.addCube(
        name='陡板-前后檐',
        location=(
            0,pDeepth/2- con.STEP_HEIGHT/2,
            (pHeight/2 - con.STEP_HEIGHT - h/2)
        ),
        scale=(
            pWidth - stoneWidth*2,    # 台基宽度 - 两头的角柱（与阶条石同宽）
            con.STEP_HEIGHT,             # 与阶条石同宽
            h
        ),
        parent=platformObj
    )
    # 方砖横铺
    utils.copyMaterial(bData.mat_brick_3,brickObj)
    utils.addModifierMirror(
        object=brickObj,
        mirrorObj=platformObj,
        use_axis=(False,True,False)
    )
    jtsObjs.append(brickObj)
    
    brickObj = utils.addCube(
        name='陡板-两山',
        location=(
            pWidth/2- con.STEP_HEIGHT/2,
            0,
            (pHeight/2 - con.STEP_HEIGHT - h/2)
        ),
        scale=(
            con.STEP_HEIGHT,             # 与阶条石同宽
            pDeepth - stoneWidth*2,    # 台基宽度 - 两头的角柱（与阶条石同宽）
            h
        ),
        parent=platformObj
    )
    # 方砖横铺
    utils.copyMaterial(bData.mat_brick_3,brickObj)
    utils.addModifierMirror(
        object=brickObj,
        mirrorObj=platformObj,
        use_axis=(True,False,False)
    )
    jtsObjs.append(brickObj)

    # 第三层，土衬石，从水平露明，并外扩金边
    brickObj = utils.addCube(
        name='土衬',
        location=(
            0,0,
            (-pHeight/2
             +con.GROUND_BORDER/2)
        ),
        scale=(
            pWidth+con.GROUND_BORDER*2,             # 与阶条石同宽
            pDeepth+con.GROUND_BORDER*2,             # 与阶条石同宽
            con.GROUND_BORDER
        ),
        parent=platformObj
    )
    jtsObjs.append(brickObj)

    # 统一设置
    for obj in jtsObjs:
        # 添加bevel
        modBevel:bpy.types.BevelModifier = \
            obj.modifiers.new('Bevel','BEVEL')
        modBevel.width = con.BEVEL_EXHIGH
        # 设置材质
        utils.copyMaterial(bData.mat_rock,obj)
    
    # 合并台基
    platformSet = utils.joinObjects(jtsObjs)
    platformSet.name = '台明'
    # UV处理
    utils.UvUnwrap(platformSet,type='cube')


    # 第四层，散水，将土衬石变形，并拉伸出坡度
    sanshuiObj = utils.addCube(
        name='散水',
        location=(
            0,0,
            -pHeight/2),
        scale=(
            pWidth + con.SANSHUI_WIDTH*dk*2,
            pDeepth + con.SANSHUI_WIDTH*dk*2,
            con.SANSHUI_HEIGHT
        ),
        parent=platformObj,)
    
    return sanshuiObj

# 绘制踏跺对象
def __drawStep(stepProxy:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(
        stepProxy,con.ACA_TYPE_BUILDING
    )
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    (pWidth,pDeepth,pHeight) = stepProxy.dimensions
    # 阶条石宽度，取下出-半个柱顶石（柱顶石为2pd，这里直接减1pd）
    stoneWidth = bData.platform_extend \
                    -bData.piller_diameter
    bevel = con.BEVEL_HIGH
    # 计算柱网数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    utils.hideObjFace(stepProxy)
    # 判断是否为“连三踏跺”
    stepSide = ''
    spx = stepProxy.location.x
    spy = stepProxy.location.y
    if spx == 0 or spy == 0:
        stepSide = 'center'
    else:
        if spx * spy > 0 :
            stepSide = 'left'
        else:
            stepSide = 'right'
    # 垂带/象眼石的位置
    # 中间踏跺做左侧，向右镜像
    # 左右两侧踏跺不做镜像，仅做左侧或右侧
    chuidaiX = -pWidth/2
    if stepSide == 'right' :
        chuidaiX = pWidth/2

    # 收集待合并对象
    taduoObjs = []
    
    # 1、土衬
    # 宽度：柱间距+金边+台阶石出头（垂带中与柱中对齐）
    if stepSide == 'center':
        tuchenWidth = pWidth+con.GROUND_BORDER*2+stoneWidth
        tuchenX = 0
    else:
        # 连三踏跺，为了不与中间土衬交叠，而错开
        tuchenWidth = pWidth
        if stepSide == 'left':
            tuchenX = -con.GROUND_BORDER-stoneWidth/2
        else:
            tuchenX = con.GROUND_BORDER+stoneWidth/2
    tuchenObj = utils.addCube(
        name='土衬',
        location=(
            tuchenX,0,
            (-pHeight/2
             +con.GROUND_BORDER/2)
        ),
        scale=(
            tuchenWidth,
            pDeepth+con.GROUND_BORDER*2,    
            con.GROUND_BORDER
        ),
        parent=stepProxy
    )
    taduoObjs.append(tuchenObj)

    # 2、散水，将土衬石变形，并拉伸出坡度
    if stepSide == 'center':
        sanshuiWidth = pWidth+con.SANSHUI_WIDTH*dk*2
        sanshuiX = 0
    else:
        # 连三踏跺，为了不与中间土衬交叠，而错开
        sanshuiWidth = pWidth
        if stepSide == 'left':
            sanshuiX = -con.SANSHUI_WIDTH*dk
        else:
            sanshuiX = con.SANSHUI_WIDTH*dk
    loc = Vector((sanshuiX,
            -con.SANSHUI_WIDTH*dk,
            -pHeight/2))
    loc = stepProxy.matrix_local @ loc
    sanshuiObj = utils.addCube(
        name='散水',
        location=loc,
        rotation=stepProxy.rotation_euler,
        scale=(
            sanshuiWidth,
            pDeepth,    
            con.SANSHUI_HEIGHT
        ),
        parent=stepProxy.parent)

    # 3、象眼石
    brickObj = utils.addCube(
        name='象眼石',
        location=(
            # 对齐柱中
            chuidaiX,
            con.STEP_HEIGHT*con.STEP_RATIO/2,
            con.GROUND_BORDER/2 - con.STEP_HEIGHT/2
        ),
        scale=(
            stoneWidth,             
            pDeepth - con.STEP_HEIGHT*con.STEP_RATIO,
            pHeight-con.GROUND_BORDER-con.STEP_HEIGHT
        ),
        parent=stepProxy
    )
    # 删除一条边，变成三角形，index=11
    utils.dissolveEdge(brickObj,[11])
    # 镜像（连三踏跺中，仅中间踏跺做镜像）
    if stepSide == 'center':
        utils.addModifierMirror(
            object=brickObj,
            mirrorObj=stepProxy,
            use_axis=(True,False,False)
        )
    # 方砖横铺
    utils.copyMaterial(bData.mat_brick_3,brickObj)
    taduoObjs.append(brickObj)

    # 4、垂带
    brickObj = utils.addCube(
        name='垂带',
        location=(
            # 对齐柱中
            chuidaiX,
            0,
            con.GROUND_BORDER/2
        ),
        scale=(
            # 宽度与阶条石宽度相同
            stoneWidth,             
            pDeepth,
            pHeight-con.GROUND_BORDER
        ),
        parent=stepProxy
    )
    # 删除一条边，变成三角形，index=11
    utils.dissolveEdge(brickObj,[11])
    # 裁剪掉象眼石的部分，仅剩垂带高度
    pStart:Vector = stepProxy.matrix_world @ Vector((0,pDeepth/2,pHeight/2))
    pEnd:Vector = stepProxy.matrix_world @ Vector((0,0,con.GROUND_BORDER/2))
    pCut:Vector=stepProxy.matrix_world @ Vector((0,0,con.GROUND_BORDER/2-con.STEP_HEIGHT))
    clear_outer = False
    clear_inner = False
    dir='Y'
    # 获取踏跺的全局旋转
    stepRot = stepProxy.matrix_world.to_euler().z
    # 南踏跺
    if stepRot == 0:
        clear_outer=True
        dir='Y'
    # 北踏跺
    if abs(stepRot - math.radians(-180))<0.001:
        clear_inner=True
        dir='Y'
    # 东
    if abs(stepRot - math.radians(90))<0.001:
        clear_outer=True
        dir='X'
    # 西
    if abs(stepRot - math.radians(-90))<0.001:
        clear_inner=True
        dir='X'
    utils.addBisect(
        object=brickObj,
        pStart=pStart,
        pEnd=pEnd,
        pCut=pCut,
        direction=dir,
        clear_outer=clear_outer,
        clear_inner=clear_inner
    )
    # 镜像（三连踏跺中，仅中间踏跺做镜像）
    if stepSide == 'center':
        utils.addModifierMirror(
            object=brickObj,
            mirrorObj=stepProxy,
            use_axis=(True,False,False)
        )
    taduoObjs.append(brickObj)

    # 5、台阶（上基石、中基石，也叫踏跺心子）
    # 计算台阶数量，每个台阶不超过基石的最大高度（15cm）
    count = math.ceil(
        (pHeight-con.GROUND_BORDER)
        /con.STEP_HEIGHT)
    stepHeight = (pHeight-con.GROUND_BORDER)/count
    stepDeepth = pDeepth/(count)
    for n in range(count-1):
        brickObj = utils.addCube(
            name='台阶',
            location=(
                0,
                (-pDeepth/2
                 +(n+1.5)*stepDeepth),
                (-pHeight/2
                +con.GROUND_BORDER/2
                + (n+0.5)*stepHeight)
            ),
            scale=(
                pWidth-stoneWidth,
                stepDeepth+bevel*2,
                stepHeight
            ),
            parent=stepProxy
        )
        taduoObjs.append(brickObj)
    
    # 批量设置
    for obj in stepProxy.children:
        modBevel:bpy.types.BevelModifier = \
            obj.modifiers.new('Bevel','BEVEL')
        modBevel.width = bevel
        modBevel.offset_type = 'WIDTH'
        modBevel.use_clamp_overlap = False
        # 设置材质
        utils.copyMaterial(bData.mat_rock,obj)

    # 合并对象
    taduoSet = utils.joinObjects(taduoObjs)
    taduoSet.name = '踏跺'
    # UV处理
    utils.UvUnwrap(taduoSet,type='cube')


    # 绑定到上一层
    taduoSet.parent = stepProxy.parent
    taduoSet.location = stepProxy.matrix_local @ taduoSet.location
    taduoSet.rotation_euler = stepProxy.rotation_euler
    # 移除proxy
    bpy.data.objects.remove(stepProxy)

    return sanshuiObj

# 构造台基的踏跺，根据门的设定，自动判断
def __buildStep(platformObj:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(
        platformObj,con.ACA_TYPE_BUILDING
    )
    bData:acaData = buildingObj.ACA_data
    (pWidth,pDeepth,pHeight) = platformObj.dimensions
    # 计算柱网数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    sanshuiObjs = []

    # 解析模版输入的墙体设置，格式如下
    # "wall#3/0#3/3,wall#0/0#3/0,wall#0/3#3/3,window#0/0#0/1,window#0/2#0/3,door#0/1#0/2,"
    wallSetting = bData.wall_net
    wallList = wallSetting.split(',')
    for wallID in wallList:
        if wallID == '': continue
        setting = wallID.split('#')
        # 样式为墙、门、窗
        style = setting[0]
        # 仅在门外设踏跺，槛窗、墙体外不设踏跺
        if style == con.ACA_WALLTYPE_DOOR:
            # 起始柱子
            pFrom = setting[1].split('/')
            pFrom_x = int(pFrom[0])
            pFrom_y = int(pFrom[1])
            # 结束柱子
            pTo = setting[2].split('/')
            pTo_x = int(pTo[0])
            pTo_y = int(pTo[1])

            # 考虑周围廊的情况，门可能在外圈，也可能在内圈
            # 注意：进深1间的小屋，不考虑周围廊，否则会出现既是南门又是北门的笑话
            if bData.y_rooms>1 and bData.x_rooms>1:
                roomStart = (0,1)
                roomEndX = (len(net_x)-1,len(net_x)-2)
                roomEndY = (len(net_y)-1,len(net_y)-2)
            else:
                roomStart = (0,)
                roomEndX = (len(net_x)-1,)
                roomEndY = (len(net_y)-1,)
            
            # 判断台阶朝向
            step_dir = ''   
            # 西门
            if pFrom_x in roomStart and pTo_x in roomStart:
                # 明间
                if pFrom_y+pTo_y ==  len(net_y)-1:
                    step_dir = 'W'
            # 东门
            if pFrom_x in roomEndX and pTo_x in roomEndX:
                # 明间
                if pFrom_y+pTo_y ==  len(net_y)-1:
                    step_dir = 'E'
            # 南门
            if pFrom_y in roomStart and pTo_y in roomStart:
                # 明间
                if pFrom_x+pTo_x in (len(net_x)-1,  # 明间
                                     len(net_x)-3,  # 左次间
                                     len(net_x)+1): # 右次间
                    step_dir = 'S'
            # 北门
            if pFrom_y in roomEndY and pTo_y in roomEndY:
                # 明间
                if pFrom_x+pTo_x in (len(net_x)-1,  # 明间
                                     len(net_x)-3,  # 左次间
                                     len(net_x)+1): # 右次间
                    step_dir = 'N'
            
            # 计算踏跺尺度，生成proxy，逐一生成
            if step_dir != '':
                # 踏跺与台基同高
                stepHeight = platformObj.dimensions.z
                # 踏跺进深取固定的2.5倍高
                stepDeepth = stepHeight * con.STEP_RATIO
                # 踏跺几何中心：柱头+台基下出+半踏跺
                offset = bData.platform_extend+stepDeepth/2
                if step_dir in ('N','S'):
                    stepWidth = abs(net_x[pTo_x] - net_x[pFrom_x])
                    # 横坐标对齐两柱连线的中间点
                    x = (net_x[pTo_x] + net_x[pFrom_x])/2
                    # 北门
                    if step_dir == 'N':
                        # 纵坐标与台基边缘对齐
                        y = bData.y_total/2 + offset
                        rot = (0,0,math.radians(180))
                    # 南门
                    if step_dir == 'S':
                        # 纵坐标与台基边缘对齐
                        y = -bData.y_total/2 - offset
                        rot = (0,0,0)
                if step_dir in ('W','E'):
                    stepWidth = abs(net_y[pTo_y] - net_y[pFrom_y])
                    if step_dir == 'W':
                        # 横坐标与台基边缘对齐
                        x = -bData.x_total/2 - offset
                        rot = (0,0,math.radians(270))
                    if step_dir == 'E':
                        # 横坐标与台基边缘对齐
                        x = bData.x_total/2 + offset
                        rot = (0,0,math.radians(90))
                    # 纵坐标对齐两柱连线的中间点
                    y = (net_y[pTo_y] + net_y[pFrom_y])/2
                stepProxy = utils.addCube(
                    name='踏跺proxy',
                    location=(x,y,0),
                    scale=(stepWidth,stepDeepth,stepHeight),
                    rotation=rot,
                )
                stepProxy.parent = platformObj
                sanshuiObj = __drawStep(stepProxy)
                sanshuiObjs.append(sanshuiObj)

    return sanshuiObjs

# 根据固定模板，创建新的台基
def buildPlatform(buildingObj:bpy.types.Object):
    bData : acaData = buildingObj.ACA_data
    bData['is_showPlatform'] = True

    # 台基可以跳过不做
    if bData.platform_height <= 0.01: return 

    # 固定在台基目录中
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('台基',parentColl=buildingColl)

    # 1、创建地基===========================================================
    # 如果已有，先删除
    pfObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_PLATFORM)
    if pfObj != None:
        utils.deleteHierarchy(pfObj,del_parent=True)

    # 载入模板配置
    platform_height = buildingObj.ACA_data.platform_height
    platform_extend = buildingObj.ACA_data.platform_extend
    # 构造cube三维
    height = platform_height
    width = platform_extend * 2 + bData.x_total
    length = platform_extend * 2 + bData.y_total
    bpy.ops.mesh.primitive_cube_add(
                size=1.0, 
                calc_uvs=True, 
                enter_editmode=False, 
                align='WORLD', 
                location = (0,0,height/2), 
                scale=(width,length,height))
    pfObj = bpy.context.object
    pfObj.name = '台基proxy'
    pfObj.data.name = '台基proxy'
    pfObj.parent = buildingObj
    # 设置插件属性
    pfObj.ACA_data['aca_obj'] = True
    pfObj.ACA_data['aca_type'] = con.ACA_TYPE_PLATFORM
    utils.hideObjFace(pfObj)

    # 构造台基细节
    sanshuiObj = __drawPlatform(pfObj)

    # 构造台基踏跺
    sanshuiobjs = __buildStep(pfObj)

    # 合并各个散水对象
    sanshuiobjs.append(sanshuiObj)
    sanshuiSet = utils.joinObjects(sanshuiobjs)
    # UV处理
    utils.UvUnwrap(sanshuiObj,type='cube')
    # 条砖竖铺
    utils.copyMaterial(bData.mat_brick_2,sanshuiSet)

     # 更新建筑框大小
    buildingObj.empty_display_size = math.sqrt(
            pfObj.dimensions.x * pfObj.dimensions.x
            + pfObj.dimensions.y * pfObj.dimensions.y
        ) / 2
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)
    return pfObj

# 根据插件面板的台基高度、下出等参数变化，更新台基外观
# 绑定于data.py中update_platform回调
def resizePlatform(buildingObj:bpy.types.Object):
    # 载入根节点中的设计参数
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    
    # # 找到台基对象
    # pfObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_PLATFORM)
    # # 重绘
    # pf_extend = bData.platform_extend
    # # 缩放台基尺寸
    # pfObj.dimensions= (
    #     pf_extend * 2 + bData.x_total,
    #     pf_extend * 2 + bData.y_total,
    #     bData.platform_height
    # )
    # # 应用缩放(有时ops.object会乱跑，这里确保针对台基对象)
    # utils.applyScale(pfObj)
    # # 平移，保持台基下沿在地平线高度
    # pfObj.location.z = bData.platform_height /2

    # 刷新台基
    pfObj = buildPlatform(buildingObj)

    # 对齐其他各个层
    # 柱网层
    floorRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_FLOOR_ROOT)
    floorRootObj.location.z =  bData.platform_height
    # 墙体层
    wallRoot = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_WALL_ROOT)
    wallRoot.location.z = bData.platform_height
    # 屋顶层
    roofRoot = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_ROOF_ROOT)
    tile_base = bData.platform_height \
                + bData.piller_height
    # 如果有斗栱，抬高斗栱高度
    if bData.use_dg:
        tile_base += bData.dg_height
        # 是否使用平板枋
        if bData.use_pingbanfang:
            tile_base += con.PINGBANFANG_H*dk
    else:
        # 以大梁抬升
        # tile_base += con.BEAM_HEIGHT*pd
        # 实际为金桁垫板高度+半桁
        tile_base += con.BOARD_HENG_H*dk + con.HENG_COMMON_D*dk/2
    roofRoot.location.z = tile_base

    # 更新建筑框大小
    buildingObj.empty_display_size = math.sqrt(
            pfObj.dimensions.x * pfObj.dimensions.x
            + pfObj.dimensions.y * pfObj.dimensions.y
        ) / 2
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)
    utils.outputMsg("Platform updated")