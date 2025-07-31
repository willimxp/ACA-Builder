# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   台基的营造
import bpy
import math
from mathutils import Vector
from typing import List

from . import utils
from . import buildFloor
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from .data import ACA_data_template as tmpData
from . import texture as mat

# 营造台基的各个结构
def __buildTaiming(baseRootObj:bpy.types.Object):
    # 1、数据准备
    buildingObj = utils.getAcaParent(
        baseRootObj,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    # 构造台明三维
    # 载入模板配置
    platform_height = bData.platform_height
    platform_extend = bData.platform_extend
    # 计算柱网数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    # 构造cube三维
    pHeight = platform_height
    pWidth = platform_extend * 2 + bData.x_total
    pDeepth = platform_extend * 2 + bData.y_total

    #2、营造台明结构
    # 收集待合并的台明构件
    taimingList = []    

    # 2.0、夯土，填充在台基内部，以免剖视图中空心很奇怪
    stoneWidth = (bData.platform_extend
                  - bData.piller_diameter)
    width = (bData.x_total 
         + bData.piller_diameter*2
         + stoneWidth*2
         - con.STEP_HEIGHT*2
         - 0.02)
    deepth = (bData.y_total 
         + bData.piller_diameter*2
         + stoneWidth*2
         - con.STEP_HEIGHT*2
         - 0.02)
    height = (pHeight 
         - con.STEP_HEIGHT 
         - con.GROUND_BORDER
         - 0.02)
    z = (con.GROUND_BORDER 
         + height/2
         + 0.01 )
    earthObj = utils.addCube(
        name = '夯土',
        location=(0,0,z),
        dimension=(width,deepth,height),
        parent=baseRootObj
    )
    mat.paint(earthObj,con.M_ROCK)
    taimingList.append(earthObj)

    # 2.1、方砖缦地
    floorInsideObj = utils.addCube(
        name='方砖缦地',
        location=(
            0,0,
            pHeight-con.STEP_HEIGHT/2
        ),
        dimension=(
            bData.x_total+bData.piller_diameter*2,
            bData.y_total+bData.piller_diameter*2,
            con.STEP_HEIGHT
        ),
        parent=baseRootObj
    )
    # 设置材质：方砖缦地
    mat.paint(floorInsideObj,con.M_PLATFORM_FLOOR)
    taimingList.append(floorInsideObj)

    # 2.2、阶条石
    # 阶条石宽度，从台基边缘做到柱顶石边缘
    stoneWidth = bData.platform_extend-bData.piller_diameter
    # 2.2.1、前后檐面阶条石，两头置好头石，尽间为去除好头石长度，明间(次间)对齐
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
        sidebrickObj = utils.addCube(
            name='阶条石',
            location=(
                (net_x[n+1]+net_x[n])/2,
                pDeepth/2-stoneWidth/2,
                pHeight-con.STEP_HEIGHT/2
            ),
            dimension=(
                net_x[n+1]-net_x[n],
                stoneWidth,
                con.STEP_HEIGHT
            ),
            parent=baseRootObj
        )
        # 上下镜像
        utils.addModifierMirror(
            object=sidebrickObj,
            mirrorObj=baseRootObj,
            use_axis=(False,True,False)
        )
        taimingList.append(sidebrickObj)

    # 2.2.2、两山阶条石
    # 延长尽间阶条石，与好头石相接
    net_y[0] -= bData.piller_diameter
    net_y[-1] += bData.piller_diameter
    # 依次做出前后檐阶条石
    for n in range((len(net_y)-1)):
        sidebrickObj = utils.addCube(
            name='阶条石',
            location=(
                pWidth/2-stoneWidth/2,
                (net_y[n+1]+net_y[n])/2,
                pHeight-con.STEP_HEIGHT/2
            ),
            dimension=(
                stoneWidth,
                net_y[n+1]-net_y[n],
                con.STEP_HEIGHT
            ),
            parent=baseRootObj
        )
        # 上下镜像
        utils.addModifierMirror(
            object=sidebrickObj,
            mirrorObj=baseRootObj,
            use_axis=(True,False,False)
        )
        taimingList.append(sidebrickObj)

    # 2.3、埋头角柱
    # 角柱高度：台基总高度 - 阶条石 - 土衬
    cornerPillerH = (pHeight 
            - con.STEP_HEIGHT 
             - con.GROUND_BORDER) 
    conrnerPillerObj = utils.addCube(
        name='埋头角柱',
        location=(
            pWidth/2-stoneWidth/2,
            pDeepth/2-stoneWidth/2,
            (pHeight
             -con.STEP_HEIGHT
             -cornerPillerH/2)
        ),
        dimension=(
            stoneWidth,             # 与阶条石同宽
            stoneWidth,             # 与阶条石同宽
            cornerPillerH
        ),
        parent=baseRootObj
    )
    # 四面镜像
    utils.addModifierMirror(
        object=conrnerPillerObj,
        mirrorObj=baseRootObj,
        use_axis=(True,True,False)
    )
    taimingList.append(conrnerPillerObj)

    # 2.4、陡板
    h = pHeight - con.STEP_HEIGHT - con.GROUND_BORDER
    aroundbrickObj = utils.addCube(
        name='陡板-前后檐',
        location=(
            0,pDeepth/2- con.STEP_HEIGHT/2,
            (pHeight - con.STEP_HEIGHT - h/2)
        ),
        dimension=(
            pWidth - stoneWidth*2,    # 台基宽度 - 两头的角柱（与阶条石同宽）
            con.STEP_HEIGHT,             # 与阶条石同宽
            h
        ),
        parent=baseRootObj
    )
    # 条砖横铺
    mat.paint(aroundbrickObj,con.M_PLATFORM_WALL)
    utils.addModifierMirror(
        object=aroundbrickObj,
        mirrorObj=baseRootObj,
        use_axis=(False,True,False)
    )
    taimingList.append(aroundbrickObj)
    
    # 2.4.2、陡板两山
    aroundbrickObj = utils.addCube(
        name='陡板-两山',
        location=(
            pWidth/2- con.STEP_HEIGHT/2,
            0,
            (pHeight - con.STEP_HEIGHT - h/2)
        ),
        dimension=(
            con.STEP_HEIGHT,             # 与阶条石同宽
            pDeepth - stoneWidth*2,    # 台基宽度 - 两头的角柱（与阶条石同宽）
            h
        ),
        parent=baseRootObj
    )
    # 条砖横铺
    mat.paint(aroundbrickObj,con.M_PLATFORM_WALL)
    utils.addModifierMirror(
        object=aroundbrickObj,
        mirrorObj=baseRootObj,
        use_axis=(True,False,False)
    )
    taimingList.append(aroundbrickObj)

    # 统一设置
    for obj in taimingList:
        # 添加bevel
        utils.addModifierBevel(
            object=obj,
            width=con.BEVEL_EXHIGH
        )
        # 设置石材
        mat.paint(obj,con.M_PLATFORM_ROCK)
    
    # 合并台基
    taimingJoined = utils.joinObjects(
        taimingList,newName='台明'
        )
    # 设置插件属性
    taimingJoined.ACA_data['aca_obj'] = True
    taimingJoined.ACA_data['aca_type'] = con.ACA_TYPE_PLATFORM
    # origin回归baseRootObj
    utils.applyTransform(
        taimingJoined,use_location=True)

    return taimingJoined

# 营造踏跺
# 根据step_net定义，可以构造多个台明
def __buildSteps(baseRootObj:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(
        baseRootObj,con.ACA_TYPE_BUILDING
    )
    bData:acaData = buildingObj.ACA_data
    stepObjList = []

    # 解析模板输入的踏跺设置，格式如下
    # "3/0#4/0,4/0#5/0,2/0#3/0,3/0#5/0,"
    stepStr = bData.step_net
    stepList = stepStr.split(',')
    for stepID in stepList:
        if stepID == '': continue
        # 生成踏跺对象
        stepObj = __drawStep(baseRootObj,stepID)
        stepObjList.append(stepObj)

    return stepObjList

# 241115 判断踏跺是否有相邻需要绘制
# StepList的样式如"3/0#4/0,4/0#5/0,2/0#3/0,3/0#5/0,"
def __checkNextStep(baseRootObj:bpy.types.Object,
                    stepID):
    buildingObj = utils.getAcaParent(
        baseRootObj,con.ACA_TYPE_BUILDING
    )
    bData:acaData = buildingObj.ACA_data
    stepStr = bData.step_net
    stepList = stepStr.split(',')
    hasNextStep= False

    # 解析踏跺配置参数
    setting = stepID.split('#')
    # 起始柱子
    pFrom = setting[0].split('/')
    pFrom_x = int(pFrom[0])
    pFrom_y = int(pFrom[1])
    # 结束柱子
    pTo = setting[1].split('/')
    pTo_x = int(pTo[0])
    pTo_y = int(pTo[1])

    # 区分方向
    if pFrom_y == pTo_y and pFrom_y == 0 and pTo_y == 0:
        # 南向，stepID向右查看
        pFrom_x += 1
        pTo_x += 1
    if pFrom_y == pTo_y and pFrom_y != 0 and pTo_y != 0:
        # 北向，stepID向左查看
        pFrom_x -= 1
        pTo_x -= 1
    if pFrom_x == pTo_x and pFrom_x == 0 and pTo_x == 0:
        # 西向，stepID向下查看
        pFrom_y -= 1
        pTo_y -= 1
    if pFrom_x == pTo_x and pFrom_x != 0 and pTo_x != 0:
        # 东向，stepID向上查看
        pFrom_y += 1
        pTo_y += 1
    NextStepID = str(pFrom_x) + '/' + str(pFrom_y) \
            + '#' + str(pTo_x) + '/' + str(pTo_y)
    if NextStepID in stepList:
        hasNextStep = True
    return hasNextStep

# 根据踏跺配置参数stepID，生成踏跺proxy
def __addStepProxy(baseRootObj:bpy.types.Object,
                   stepID:str):
    # 载入数据
    buildingObj = utils.getAcaParent(
        baseRootObj,con.ACA_TYPE_BUILDING
    )
    bData:acaData = buildingObj.ACA_data
    # 计算柱网数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)

    # 解析踏跺配置参数
    setting = stepID.split('#')
    # 起始柱子
    pFrom = setting[0].split('/')
    pFrom_x = int(pFrom[0])
    pFrom_y = int(pFrom[1])
    # 结束柱子
    pTo = setting[1].split('/')
    pTo_x = int(pTo[0])
    pTo_y = int(pTo[1])

    # 判断台阶朝向
    step_dir = None   
    roomEndX = len(net_x)-1
    roomEndY = len(net_y)-1
    # 西门
    if pFrom_x == 0 and pTo_x == 0:
        step_dir = 'W'
    # 东门
    if pFrom_x == roomEndX and pTo_x == roomEndX:
        step_dir = 'E'
    # 南门
    if pFrom_y == 0 and pTo_y == 0:
        step_dir = 'S'
    # 北门
    if pFrom_y == roomEndY and pTo_y == roomEndY:
        step_dir = 'N'

    if step_dir == None:
        utils.outputMsg('无法生成踏跺，id='+stepID)
        # 退出
        return
    
    # 计算踏跺尺度，生成proxy，逐一生成
    # 踏跺与台基同高
    stepHeight = bData.platform_height
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
        location=(x,y,stepHeight/2),
        dimension=(stepWidth,stepDeepth,stepHeight),
        rotation=rot,
    )
    stepProxy.parent = baseRootObj
    stepProxy.ACA_data['stepID'] = stepID
    stepProxy.ACA_data['aca_type'] = con.ACA_TYPE_STEP
    utils.hideObj(stepProxy)
    utils.lockObj(stepProxy)

    return stepProxy

# 绘制踏跺对象
def __drawStep(
        baseRootObj:bpy.types.Object,
        stepID):
    # 0、载入数据
    buildingObj = utils.getAcaParent(
        baseRootObj,con.ACA_TYPE_BUILDING
    )
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    # 固定在台基目录中
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection(
        con.COLL_NAME_BASE,
        parentColl=buildingColl)

    bevel = con.BEVEL_HIGH
    # 根据stepID生成踏跺（如，’3/0#4/0‘）
    stepProxy = __addStepProxy(
        baseRootObj,stepID)
    (pWidth,pDeepth,pHeight) = stepProxy.dimensions
    # 判断相邻踏跺，只做单边
    isOnlyLeft = __checkNextStep(
        baseRootObj,stepID)
    # 阶条石宽度，取下出-半个柱顶石（柱顶石为2pd，这里直接减1pd）
    stoneWidth = bData.platform_extend \
                    -bData.piller_diameter
    # 垂带/象眼石的位置
    # 中间踏跺做左侧，向右镜像
    # 左右两侧踏跺不做镜像，仅做左侧或右侧
    # 241115 垂带与柱对齐
    chuidaiX = -pWidth/2
    

    # 营造踏跺结构=======================
    # 收集待合并对象
    taduoObjs = []

    # 1、象眼石
    brickObj = utils.addCube(
        name='象眼石',
        location=(
            # 对齐柱中
            chuidaiX,
            con.STEP_HEIGHT*con.STEP_RATIO/2,
            con.GROUND_BORDER/2 - con.STEP_HEIGHT/2
        ),
        dimension=(
            stoneWidth,             
            pDeepth - con.STEP_HEIGHT*con.STEP_RATIO,
            pHeight-con.GROUND_BORDER-con.STEP_HEIGHT
        ),
        parent=stepProxy
    )
    # 删除一条边，变成三角形，index=11
    utils.dissolveEdge(brickObj,[11])
    # 镜像
    if not isOnlyLeft:
        utils.addModifierMirror(
            object=brickObj,
            mirrorObj=stepProxy,
            use_axis=(True,False,False)
        )
    # 设置材质：方砖横铺
    mat.paint(brickObj,con.M_PLATFORM_WALL)
    taduoObjs.append(brickObj)

    # 2、垂带
    brickObj = utils.addCube(
        name='垂带',
        location=(
            # 对齐柱中
            chuidaiX,
            0,
            con.GROUND_BORDER/2
        ),
        dimension=(
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
    if not isOnlyLeft:
        utils.addModifierMirror(
            object=brickObj,
            mirrorObj=stepProxy,
            use_axis=(True,False,False))
    taduoObjs.append(brickObj)

    # 3、台阶（上基石、中基石，也叫踏跺心子）
    # 计算台阶数量，每个台阶不超过基石的最大高度（16cm）
    count = round(pHeight/con.STEP_HEIGHT)
    if count == 0: count += 1
    stepHeight = (pHeight-con.GROUND_BORDER)/count
    stepDeepth = pDeepth/count
    brickObj = utils.addCube(
        name='台阶',
        location=(
            0,
            (-pDeepth/2+stepDeepth*1.5),
            (-pHeight/2
                + con.GROUND_BORDER/2
                + stepHeight/2)
        ),
        dimension=(
            pWidth-stoneWidth,
            stepDeepth+bevel*2,
            stepHeight
        ),
        parent=stepProxy
    )
    utils.addModifierArray(
        object=brickObj,
        count=count-1,
        offset=(0,stepDeepth,stepHeight)
    )
    taduoObjs.append(brickObj)

    # 批量设置
    for obj in taduoObjs:
        utils.addModifierBevel(
            object=obj,
            width=bevel,
            type='WIDTH',
            clamp=False,
        )
        # 设置材质
        mat.paint(obj,con.M_PLATFORM_ROCK)

    # 合并对象
    stepJoined = utils.joinObjects(
        taduoObjs,newName='踏跺.'+stepID)
    # 识别对象类型
    stepJoined.ACA_data['aca_type'] = con.ACA_TYPE_STEP
    stepJoined.ACA_data['stepID'] = stepID
    # origin更新到stepProxy中心
    utils.applyTransform(stepJoined,use_location=True)
    # 对于单边垂带的对象（防止与相邻踏跺垂带交叠），将origin偏移半垂带
    # 这样可以在生成土衬时，自动对齐到单边垂带的边缘
    if isOnlyLeft:
        utils.setOrigin(stepJoined,
            Vector((-stoneWidth/2,0,0)))

    # 绑定到上一层
    stepJoined.parent = stepProxy.parent
    stepJoined.location = stepProxy.matrix_local @ stepJoined.location
    stepJoined.rotation_euler = stepProxy.rotation_euler
    # 移除proxy
    bpy.data.objects.remove(stepProxy)

    return stepJoined

# 添加散水，根据台基proxy、踏跺proxy进行生成，并合并
def __addPlatformExpand(
        taimingObj:bpy.types.Object,
        stepList,
        type):
    # 载入数据
    buildingObj = utils.getAcaParent(
        taimingObj,con.ACA_TYPE_BUILDING
    )
    baseRootObj = utils.getAcaParent(
        taimingObj,con.ACA_TYPE_BASE_ROOT
    )
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK

    # 1、分别定义土衬和散水在扩展时的不同参数设置
    if type == 'tuchen':
        name = '土衬'
        # 拓展尺寸
        pfExpand = con.GROUND_BORDER*2
        # 位置
        loc_z = con.GROUND_BORDER/2
        # 高度
        height = con.GROUND_BORDER
        # 材质
        pfeMat = con.M_PLATFORM_ROCK
    if type == 'sanshui':
        name = '散水' 
        # 拓展尺寸
        pfExpand = con.SANSHUI_WIDTH*dk*2
        # 位置
        loc_z = 0
        # 高度
        height = con.SANSHUI_HEIGHT 
        # 材质
        pfeMat = con.M_PLATFORM_EXPAND

    # 2、台明拓展，做为后续合并踏跺扩展的本体
    baseExpandObj = utils.addCube(
            name = name,
            location = (
                taimingObj.location.x,
                taimingObj.location.y,
                loc_z,
            ),
            dimension = (
                    taimingObj.dimensions.x + pfExpand,
                    taimingObj.dimensions.y + pfExpand,
                    height
            ),
            rotation = taimingObj.rotation_euler,
            parent = baseRootObj
        )

    # 3、踏跺拓展
    stepExpandList = []
    # 依据台基proxy、踏跺proxy生成新的散水对象
    for n in range(len(stepList)):
        stepObj:bpy.types.Object = stepList[n]
        # 削减0.1mm，改善后续boolean的毛刺
        import random
        offset = random.random()/1000
        stepExpandObj = utils.addCube(
            name = name,
            location = (
                stepObj.location.x,
                stepObj.location.y,
                loc_z,
            ),
            dimension = (
                    (stepObj.dimensions.x + pfExpand),
                     stepObj.dimensions.y + pfExpand,
                     height - offset   
            ),
            rotation = stepObj.rotation_euler,
            parent = baseRootObj
        )
        stepExpandList.append(stepExpandObj)
    
    # 4、在台明扩展本体上，添加踏跺拓展对象
    for stepExpandObj in stepExpandList:
        utils.addModifierBoolean(
            object=baseExpandObj,
            boolObj=stepExpandObj,
            operation='UNION',
            solver='EXACT'
        )
    # 应用boolean modifier
    utils.applyAllModifer(baseExpandObj)

    # 散水优化，效果不佳，暂时弃用
    # if type == 'sanshui':
    #     utils.unionProject(
    #         projectNormal=Vector((0,0,1)),
    #         projectCenter=Vector((0,0,0)),
    #         objectList=[baseExpandObj],
    #         insetThickness=con.SANSHUI_WIDTH*dk)

    # 删除已被合并的踏跺扩展对象
    for stepExpandObj in stepExpandList:
        bpy.data.objects.remove(stepExpandObj)
    
    # 5、设置材质
    mat.paint(baseExpandObj,pfeMat)

    return baseExpandObj

# 添加踏跺
def addStep(buildingObj:bpy.types.Object,
            pillers:List[bpy.types.Object]):
    # 载入数据
    bData:acaData = buildingObj.ACA_data

    # 校验用户至少选择2根柱子
    pillerNum = 0
    for piller in pillers:
        if 'aca_type' in piller.ACA_data:   # 可能选择了没有属性的对象
            if piller.ACA_data['aca_type'] \
                == con.ACA_TYPE_PILLER:
                pillerNum += 1
    if pillerNum < 2:
        utils.popMessageBox("请至少选择2根柱子")
        return
    
    # 构造枋网设置
    pFrom = None
    pTo= None
    stepStr = bData.step_net
    for piller in pillers:
        # 校验用户选择的对象，可能误选了其他东西，直接忽略
        if 'aca_type' in piller.ACA_data:   # 可能选择了没有属性的对象
            if piller.ACA_data['aca_type'] \
                == con.ACA_TYPE_PILLER:
                if pFrom == None: 
                    pFrom = piller
                    continue #暂存起点
                else:
                    pTo = piller
                    stepID = pFrom.ACA_data['pillerID'] \
                        + '#' + pTo.ACA_data['pillerID'] 
                    stepID_alt = pTo.ACA_data['pillerID'] \
                         + '#' + pFrom.ACA_data['pillerID'] 
                    # 验证踏跺是否已经存在
                    if stepID in stepStr or stepID_alt in stepStr:
                        print(stepID + " is in stepstr:" + stepStr)
                        continue
                                
                    # 将踏跺加入整体布局中
                    bData.step_net += stepID + ','
                    utils.outputMsg("添加踏跺：" + stepID)

                    # 交换柱子，为下一次循环做准备
                    pFrom = piller
    
    # 241115 重新生成台基，以便刷新合并后的散水
    buildPlatform(buildingObj)

    return {'FINISHED'}

def delStep(buildingObj:bpy.types.Object,
              steps:List[bpy.types.Object]):
    # 载入数据
    bData:acaData = buildingObj.ACA_data

    # 删除踏跺对象
    for step in steps:
        # 校验用户选择的对象，可能误选了其他东西，直接忽略
        # 如果用户选择的是step子对象，则强制转换到父对象
        if 'aca_type' in step.ACA_data:
            if step.ACA_data['aca_type'] \
                    == con.ACA_TYPE_STEP:
                utils.deleteHierarchy(step,del_parent=True)

    # 重新生成柱网配置
    baseRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_BASE_ROOT)
    pfChildren:List[bpy.types.Object] = baseRootObj.children
    bData.step_net = ''
    for step in pfChildren:
        if 'aca_type' in step.ACA_data:
            if step.ACA_data['aca_type']==con.ACA_TYPE_STEP:
                stepID = step.ACA_data['stepID']
                bData.step_net += stepID + ','
    
    # 241115 重新生成台基，以便刷新合并后的散水
    buildPlatform(buildingObj)
    # 重新聚焦根节点
    utils.focusObj(buildingObj)
    return {'FINISHED'}

# 根据固定模板，创建新的台基
def buildPlatform(buildingObj:bpy.types.Object):
    # 0、准备
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    # 预校验
    # 台基可以跳过不做
    if bData.platform_height <= 0.01: return 
    # 固定在台基目录中
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection(
        con.COLL_NAME_BASE,
        parentColl=buildingColl)

    # 1、查找或新建台基根节点
    baseRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_BASE_ROOT)
    if baseRootObj == None:        
        # 创建新台基对象（empty）
        baseRootObj = utils.addEmpty(
            name=con.COLL_NAME_BASE,
            parent = buildingObj,
            location = (0,0,0) # 台基以地平基线为原点
        )
        baseRootObj.ACA_data['aca_obj'] = True
        baseRootObj.ACA_data['aca_type'] = con.ACA_TYPE_BASE_ROOT
    else:
        # 清空台基下属的台明、踏跺
        utils.deleteHierarchy(baseRootObj)
    
    # 2、开始构建台基
    # 收集待合并的部件
    basePartList = []
    # 2.1、营造台明
    taimingObj = __buildTaiming(baseRootObj)
    basePartList.append(taimingObj)
    # 2.2、营造踏跺
    stepList = __buildSteps(baseRootObj)
    # 2.3、生成土衬
    tuchenObj = __addPlatformExpand(taimingObj,stepList,
                             type='tuchen')
    basePartList.append(tuchenObj)
    # 2.4、生成散水
    # sanshuiObj = __addPlatformExpand(taimingObj,stepList,
    #                           type='sanshui')
    # basePartList.append(sanshuiObj)
    # 3、合并构件
    baseJoined = utils.joinObjects(basePartList)
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)

    return {'FINISHED'}

# 根据插件面板的台基高度、下出等参数变化，更新台基外观
# 绑定于data.py中update_platform回调
def resizePlatform(buildingObj:bpy.types.Object):
    # 载入根节点中的设计参数
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK

    # 刷新台基
    pfObj = buildPlatform(buildingObj)

    # 对齐其他各个层
    # 柱网层
    floorRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_FLOOR_ROOT)
    if floorRootObj != None:
        floorRootObj.location.z =  bData.platform_height
    # 墙体层
    wallRoot = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_WALL_ROOT)
    if wallRoot != None:
        wallRoot.location.z = bData.platform_height    
    # 柱头高度
    roofBaseZ = (bData.platform_height
                    + bData.piller_height)
    # 斗栱层
    dgrootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_DG_ROOT)
    if dgrootObj != None: 
        dgrootObj.location.z = roofBaseZ
    # 如果有斗栱，抬高斗栱高度
    if bData.use_dg:
        roofBaseZ += bData.dg_height
        # 是否使用平板枋
        if bData.use_pingbanfang:
            roofBaseZ += con.PINGBANFANG_H*dk
    # 梁架层
    beamRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_BEAM_ROOT)
    if beamRootObj != None: 
        beamRootObj.location.z = roofBaseZ
    # 椽望层
    rafterRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_ROOT)
    if rafterRootObj != None: 
        rafterRootObj.location.z = roofBaseZ
    # 瓦作层
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT)
    if tileRootObj != None: 
        tileRootObj.location.z = roofBaseZ
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)
    utils.outputMsg("Platform updated")

# 删除月台
def terraceDelete(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    # 获取主建筑
    mainBuilding = utils.getMainBuilding(buildingObj)
    
    if bData.combo_type == con.COMBO_TERRACE:
        from . import build
        build.delBuilding(buildingObj,
            withCombo=False,# 仅删除个体
        )

    # 聚焦主建筑的台基
    mainPlatform = utils.getAcaChild(
        mainBuilding,con.ACA_TYPE_PLATFORM
    )
    if mainPlatform is not None:
        utils.focusObj(mainPlatform)

    return

def terraceAdd(buildingObj:bpy.types.Object):
    # 0、合法性验证 -----------------------
    # 验证组合根节点
    comboObj = None
    if buildingObj.parent is not None:
        parent = buildingObj.parent
        if parent.ACA_data.aca_type == con.ACA_TYPE_COMBO:
            comboObj = parent
    if comboObj is None:
        utils.outputMsg("未找到组织建筑根节点")
        return
    
    # 验证是否为主体建筑
    if buildingObj.ACA_data.combo_type != con.COMBO_MAIN:
        utils.popMessageBox("不能添加月台，只有主体建筑可以添加月台")
        return
    
    # 验证是否已经有月台
    for building in comboObj.children:
        if building.ACA_data.combo_type == con.COMBO_TERRACE:
            utils.popMessageBox("已经有一个月台，不能再生成新的月台了。")
            return

    # 1、开始构建月台 ----------------------------
    # 构建月台根节点
    from . import buildFloor
    terraceRoot = buildFloor.__addBuildingRoot(
        templateName = '月台',
        comboObj = comboObj
    )

    # 构建月台数据
    mData:acaData = buildingObj.ACA_data
    bData:acaData = terraceRoot.ACA_data
    # 继承主建筑属性
    utils.copyAcaData(buildingObj,terraceRoot)

    # 月台组合类型
    bData['combo_type'] = con.COMBO_TERRACE
    # 不做其他层次
    bData['is_showPillers'] = False
    bData['is_showWalls'] = False
    bData['is_showDougong'] = False
    bData['is_showBeam'] = False
    bData['is_showRafter'] = False
    bData['is_showTiles'] = False
    
    # 月台高度，比主体低1踏步
    bData['platform_height'] = (
        mData.platform_height - con.STEP_HEIGHT)
    # 月台下出，比主体窄2踏步（未见规则）
    bData['platform_extend'] = (
        mData.platform_extend 
        - con.STEP_HEIGHT*2
        )
    # 月台进深，保留1间
    bData['y_rooms'] = 1
    # 月台面阔，五间以上做“凸”形月台，减2间
    if mData.x_rooms > 5:
        bData['x_rooms'] = mData.x_rooms - 2

    # 相对位置
    offsetY = (mData.y_total/2 
               + mData.platform_extend
               + bData.y_1/2 
               + bData.platform_extend
               )
    terraceLoc = Vector((0,-offsetY,0))
    # 本次移动
    terraceRoot.location = terraceLoc
    # 存入属性，以便存入模板
    bData['root_location'] = terraceLoc

    # 调用月台营造
    buildPlatform(terraceRoot)

    # 聚焦主建筑的台基
    terraceObj = utils.getAcaChild(
        terraceRoot,con.ACA_TYPE_PLATFORM
    )
    if terraceObj is not None:
        utils.focusObj(terraceObj)

    return