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

# 生成台基Proxy
def __addPlatformProxy(buildingObj:bpy.types.Object):
    bData : acaData = buildingObj.ACA_data
    # 载入模板配置
    platform_height = bData.platform_height
    platform_extend = bData.platform_extend
    # 构造cube三维
    height = platform_height
    width = platform_extend * 2 + bData.x_total
    length = platform_extend * 2 + bData.y_total
    pfProxy = utils.addCube(
        name='台基proxy',
        location=(0,0,height/2),
        dimension=(width,length,height),
        parent=buildingObj
    )
    # 设置插件属性
    pfProxy.ACA_data['aca_obj'] = True
    pfProxy.ACA_data['aca_type'] = con.ACA_TYPE_PLATFORM
    utils.hideObj(pfProxy)
    return pfProxy

# 构造台基的几何细节
def __drawPlatform(platformObj:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(
        platformObj,con.ACA_TYPE_BUILDING
    )
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
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
        dimension=(
            bData.x_total+bData.piller_diameter*2,
            bData.y_total+bData.piller_diameter*2,
            con.STEP_HEIGHT
        ),
        parent=platformObj
    )
    # 方砖缦地
    mat.setShader(brickObj,
        mat.shaderType.BRICK1)

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
            dimension=(
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
            dimension=(
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
        dimension=(
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
        dimension=(
            pWidth - stoneWidth*2,    # 台基宽度 - 两头的角柱（与阶条石同宽）
            con.STEP_HEIGHT,             # 与阶条石同宽
            h
        ),
        parent=platformObj
    )
    # 方砖横铺
    mat.setShader(brickObj,
        mat.shaderType.BRICK3)

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
        dimension=(
            con.STEP_HEIGHT,             # 与阶条石同宽
            pDeepth - stoneWidth*2,    # 台基宽度 - 两头的角柱（与阶条石同宽）
            h
        ),
        parent=platformObj
    )
    # 方砖横铺
    mat.setShader(brickObj,
        mat.shaderType.BRICK3)
    utils.addModifierMirror(
        object=brickObj,
        mirrorObj=platformObj,
        use_axis=(True,False,False)
    )
    jtsObjs.append(brickObj)

    # 统一设置
    for obj in jtsObjs:
        # 添加bevel
        modBevel:bpy.types.BevelModifier = \
            obj.modifiers.new('Bevel','BEVEL')
        modBevel.width = con.BEVEL_EXHIGH
        # 设置材质
        mat.setShader(obj,
            mat.shaderType.ROCK)
    
    # 合并台基
    platformSet = utils.joinObjects(
        jtsObjs,newName='台明'
        )

    return platformSet

# 绘制踏跺对象
def __drawStep(stepProxy:bpy.types.Object, isOnlyLeft=False):
    # 载入数据
    buildingObj = utils.getAcaParent(
        stepProxy,con.ACA_TYPE_BUILDING
    )
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp

    dk = bData.DK
    (pWidth,pDeepth,pHeight) = stepProxy.dimensions
    bevel = con.BEVEL_HIGH
    # 计算柱网数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    # 固定在台基目录中
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('台基',parentColl=buildingColl)

    # 收集待合并对象
    taduoObjs = []

    # 阶条石宽度，取下出-半个柱顶石（柱顶石为2pd，这里直接减1pd）
    stoneWidth = bData.platform_extend \
                    -bData.piller_diameter
    # 垂带/象眼石的位置
    # 中间踏跺做左侧，向右镜像
    # 左右两侧踏跺不做镜像，仅做左侧或右侧
    # 241115 垂带与柱对齐
    chuidaiX = -pWidth/2

    # 3、象眼石
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
    # 方砖横铺
    mat.setShader(brickObj,mat.shaderType.BRICK3)
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

    # 5、台阶（上基石、中基石，也叫踏跺心子）
    # 计算台阶数量，每个台阶不超过基石的最大高度（15cm）
    count = math.ceil(
        (pHeight-con.GROUND_BORDER)
        /con.STEP_HEIGHT)
    stepHeight = (pHeight-con.GROUND_BORDER)/count
    stepDeepth = pDeepth/(count)
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
        modBevel:bpy.types.BevelModifier = \
            obj.modifiers.new('Bevel','BEVEL')
        modBevel.width = bevel
        modBevel.offset_type = 'WIDTH'
        modBevel.use_clamp_overlap = False
        # 设置材质
        mat.setShader(obj,mat.shaderType.ROCK)

    # 合并对象
    taduoSet = utils.joinObjects(
        taduoObjs,newName='踏跺')
    # 识别对象类型
    taduoSet.ACA_data['aca_type'] = con.ACA_TYPE_STEP
    taduoSet.ACA_data['stepID'] = stepProxy.ACA_data['stepID'] 

    # # 绑定到上一层
    # taduoSet.parent = stepProxy.parent
    # taduoSet.location = stepProxy.matrix_local @ taduoSet.location
    # taduoSet.rotation_euler = stepProxy.rotation_euler
    # # 移除proxy
    # bpy.data.objects.remove(stepProxy)

    return taduoSet

# 根据踏跺配置参数stepID，生成踏跺proxy
def __addStepProxy(buildingObj:bpy.types.Object,
                   stepID:str):
    # 载入数据
    platformObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_PLATFORM)
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
        dimension=(stepWidth,stepDeepth,stepHeight),
        rotation=rot,
    )
    stepProxy.parent = platformObj
    stepProxy.ACA_data['stepID'] = stepID
    stepProxy.ACA_data['aca_type'] = con.ACA_TYPE_STEP
    utils.hideObj(stepProxy)
    utils.lockObj(stepProxy)

    return stepProxy

# 添加散水，根据台基proxy、踏跺proxy进行生成，并合并
def __addPlatformExpand(pfProxy:bpy.types.Object,
                 stepProxyList,
                 type):
    # 载入数据
    buildingObj = utils.getAcaParent(
        pfProxy,con.ACA_TYPE_BUILDING
    )
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = bData.piller_diameter

    # 1、分别定义土衬和散水在扩展时的不同参数设置
    if type == 'tuchen':
        name = '土衬'
        # 拓展尺寸
        pfExpand = con.GROUND_BORDER*2
        # 位置
        loc_z = -bData.platform_height/2 + con.GROUND_BORDER/2
        # 高度
        height = con.GROUND_BORDER
        # 材质
        pfeMat = mat.shaderType.ROCK
    if type == 'sanshui':
        name = '散水' 
        # 拓展尺寸
        pfExpand = con.SANSHUI_WIDTH*dk*2
        # 位置
        loc_z = -bData.platform_height/2
        # 高度
        height = con.SANSHUI_HEIGHT 
        # 材质
        pfeMat = mat.shaderType.BRICK2

    # 2、台明拓展，做为后续合并踏跺扩展的本体
    baseExpandObj = utils.addCube(
            name= name,
            location=(
                pfProxy.location.x,
                pfProxy.location.y,
                loc_z,
            ),
            dimension=(
                    pfProxy.dimensions.x + pfExpand,
                    pfProxy.dimensions.y + pfExpand,
                    height
            ),
            rotation= pfProxy.rotation_euler,
            parent=pfProxy
        )

    # 3、踏跺拓展
    stepExpandList = []
    # 依据台基proxy、踏跺proxy生成新的散水对象
    # 计算踏跺的两侧扩展
    # stepProxy是按照两柱间距创建的，而垂带对柱中对齐，使得踏跺垂带超出柱中
    # 垂带的宽度与阶条石同宽：取台基下出-半个柱顶石
    stepSideExpand = bData.platform_extend - con.PILLERBASE_WIDTH*pd/2
    for n in range(len(stepProxyList)):
        stepProxy:bpy.types.Object = stepProxyList[n]
        stepExpandObj = utils.addCube(
            name= name,
            location=(
                stepProxy.location.x,
                stepProxy.location.y,
                loc_z,
            ),
            dimension=(
                    (stepProxy.dimensions.x 
                     + stepSideExpand
                     + pfExpand),
                    stepProxy.dimensions.y + pfExpand,
                    height
            ),
            rotation= stepProxy.rotation_euler,
            parent=pfProxy
        )
        stepExpandList.append(stepExpandObj)
    
    # 4、在台明扩展本体上，添加踏跺拓展对象
    for stepExpandObj in stepExpandList:
        modBool:bpy.types.BooleanModifier = \
            baseExpandObj.modifiers.new('合并','BOOLEAN')
        modBool.object = stepExpandObj
        modBool.solver = 'EXACT'
        modBool.operation = 'UNION'
    # 应用boolean modifier
    utils.applyAllModifer(baseExpandObj)
    # 删除已被合并的踏跺扩展对象
    for stepExpandObj in stepExpandList:
        bpy.data.objects.remove(stepExpandObj)
    
    # 5、设置材质
    mat.setShader(baseExpandObj,pfeMat)

    # 6、添加导角
    modBevel:bpy.types.BevelModifier = \
            baseExpandObj.modifiers.new('Bevel','BEVEL')
    modBevel.width = con.BEVEL_HIGH
    modBevel.offset_type = 'WIDTH'
    modBevel.use_clamp_overlap = False

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
        utils.showMessageBox("ERROR:请至少选择2根柱子")
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
                # 将step转换为stepProxy
                stepProxy = step.parent
                utils.deleteHierarchy(stepProxy,del_parent=True)

    # 重新生成柱网配置
    pfRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_PLATFORM
    )    
    pfChildren:List[bpy.types.Object] = pfRootObj.children
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

# 241115 判断踏跺是否有相邻需要绘制
# StepList的样式如"3/0#4/0,4/0#5/0,2/0#3/0,3/0#5/0,"
def __checkNextStep(StepList,stepID):
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
    if NextStepID in StepList:
        hasNextStep = True
    return hasNextStep

# 根据固定模板，创建新的台基
def buildPlatform(buildingObj:bpy.types.Object):
    bData : acaData = buildingObj.ACA_data
    # 创建地基
    # 如果已有，先删除
    pfProxy = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_PLATFORM)
    if pfProxy != None:
        utils.deleteHierarchy(pfProxy,del_parent=True)

    # 台基可以跳过不做
    if bData.platform_height <= 0.01: return 

    # 固定在台基目录中
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('台基',parentColl=buildingColl)

    # 生成台基框线
    pfProxy = __addPlatformProxy(buildingObj)
    # 构造台基细节
    platformObj = __drawPlatform(pfProxy)

    # 构造台基踏跺
    # 解析模版输入的墙体设置，格式如下
    # "3/0#4/0,4/0#5/0,2/0#3/0,3/0#5/0,"
    stepStr = bData.step_net
    stepList = stepStr.split(',')
    stepProxyList = []
    for stepID in stepList:
        if stepID == '': continue
        # 根据stepID生成踏跺（如，’3/0#4/0‘）
        stepProxy = __addStepProxy(
            buildingObj,stepID)
        stepProxyList.append(stepProxy)
        # 生成踏跺对象
        # 241115 判断相邻踏跺，只做单边
        hasNextStep = __checkNextStep(stepList,stepID)
        stepObj = __drawStep(stepProxy,hasNextStep)
        
    # 生成土衬
    tuchenObj = __addPlatformExpand(pfProxy,stepProxyList,
                             type='tuchen')
    # 生成散水
    sanshuiObj = __addPlatformExpand(pfProxy,stepProxyList,
                              type='sanshui')

     # 更新建筑框大小
    buildingObj.empty_display_size = math.sqrt(
            pfProxy.dimensions.x * pfProxy.dimensions.x
            + pfProxy.dimensions.y * pfProxy.dimensions.y
        ) / 2
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)
    return pfProxy

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
        # 以大梁抬升, 实际为金桁垫板高度+半桁
        tile_base += con.BOARD_HENG_H*dk + con.HENG_COMMON_D*dk/2
    roofRoot.location.z = tile_base

    # 更新建筑框大小
    if pfObj == None:
        buildingObj.empty_display_size = bData.x_total
    else:
        buildingObj.empty_display_size = math.sqrt(
                pfObj.dimensions.x * pfObj.dimensions.x
                + pfObj.dimensions.y * pfObj.dimensions.y
            ) / 2
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)
    utils.outputMsg("Platform updated")