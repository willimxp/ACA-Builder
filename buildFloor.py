# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   柱子的营造
import bpy
from mathutils import Vector
from functools import partial
import math
from typing import List

from . import texture as mat
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from .data import ACA_data_template as tmpData
from . import utils
from . import acaTemplate
from . import buildWall
from . import buildPlatform
from . import buildRoof

# 添加建筑empty根节点，并绑定设计模版
# 返回建筑empty根节点对象
# 被ACA_OT_add_newbuilding类调用
def __addBuildingRoot(templateName):
    # 创建或锁定根目录
    coll = utils.setCollection(templateName)
    
    # 创建buildObj根节点
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    buildingObj = bpy.context.object
    buildingObj.location = bpy.context.scene.cursor.location   # 原点摆放在3D Cursor位置
    buildingObj.name = templateName   # 系统遇到重名会自动添加00x的后缀       
    buildingObj.empty_display_type = 'SPHERE'

    # 在buildingObj中填充模版数据
    acaTemplate.openTemplate(buildingObj,templateName)
    
    return buildingObj

# 返回柱网数据
# 非内部函数，在墙体、斗栱、屋顶制作时都有公开调用
# 将panel中设置的面宽、进深，组合成柱网数组
# 返回net_x[],net_y[]数组
def getFloorDate(buildingObj:bpy.types.Object):
    # 载入设计参数
    bData:acaData = buildingObj.ACA_data

    # 构造柱网X坐标序列
    x_rooms = bData.x_rooms   # 面阔几间
    y_rooms = bData.y_rooms   # 进深几间

    net_x = []  # 重新计算    
    # 排布规律：明间+多个次间+梢间
    # 明间有且只有1间
    offset = bData.x_1 / 2
    net_x.append(offset)
    net_x.insert(0, -offset)
    # 次间可能有多间
    if x_rooms > 5:
        # -1明间-2梢间-2尽间
        cijianNum = x_rooms - 5
    elif x_rooms > 3:
        # -1明间-2梢间
        cijianNum = x_rooms - 3
    else:
        # -1明间
        cijianNum = x_rooms - 1
    for n in range(1,int(cijianNum/2)+1):
        offset = (bData.x_1/2 + bData.x_2*n)
        net_x.append(offset)
        net_x.insert(0, -offset) 
    # 梢间，5间以上配置一间
    if x_rooms >= 5 :
        offset += bData.x_3 
        net_x.append(offset)
        net_x.insert(0, -offset) 
    # 尽间，7间以上配置一间
    if x_rooms >= 7 :
        offset += bData.x_4 
        net_x.append(offset)
        net_x.insert(0, -offset) 

    # 构造柱网Y坐标序列
    # 进深可以为奇数（山柱分两侧），也可以为偶数（山柱居中）
    net_y=[]    # 重新计算
    if y_rooms%2 == 1: # 奇数间
        # 明间，有且只有1间
        offset = bData.y_1 / 2
        net_y.append(offset)
        net_y.insert(0, -offset)
        # 计算次间数量
        if y_rooms > 3:
            # 1间明间，2间梢间
            cijianNum = y_rooms - 3
        else:
            # 仅1间明间，不做梢间
            cijianNum = y_rooms -1
        # 循环计算次间柱位
        for n in range(1,int(cijianNum/2)+1):
            offset = (bData.y_1/2 + bData.y_2*n)
            net_y.append(offset)
            net_y.insert(0, -offset) 
        # 梢间
        if y_rooms > 3:
            offset += bData.y_3 
            net_y.append(offset)
            net_y.insert(0, -offset)
    else:   #偶数间
        # 偶数间进深，有默认的山柱，位置Y=0
        net_y.append(0)
        # 明间，分做2间
        offset = bData.y_1
        net_y.append(offset)
        net_y.insert(0, -offset)
        # 计算次间数量
        if y_rooms > 4:
            # 2间明间，2间梢间
            cijianNum = y_rooms - 4
        else:
            # 仅2间明间，无梢间
            cijianNum = y_rooms - 2
        # 循环计算次间柱位
        for n in range(1,int(cijianNum/2)+1):
            offset = (bData.y_1 + bData.y_2*n)
            net_y.append(offset)
            net_y.insert(0, -offset) 
        # 梢间
        if y_rooms > 4:
            offset += bData.y_3 
            net_y.append(offset)
            net_y.insert(0, -offset)
    
    # 保存通面阔计算结果，以便其他函数中复用
    bData.x_total = net_x[-1]-net_x[0]
    # 保存通进深计算结果，以便其他函数中复用
    bData.y_total = net_y[-1]-net_y[0]

    return net_x,net_y

# 在四角的大额枋外，添加霸王拳
def __buildFangBWQ(fangObj):    
    # 基础数据
    aData:tmpData = bpy.context.scene.ACA_temp
    buildingObj = utils.getAcaParent(fangObj,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    # 获取开间、进深数据
    net_x,net_y = getFloorDate(buildingObj)

    # 解析枋ID
    fangID = fangObj.ACA_data['fangID']
    setting = fangID.split('#')
    # 分解获取柱子编号
    pFrom = setting[0].split('/')
    pFrom_x = int(pFrom[0])
    pFrom_y = int(pFrom[1])
    vFrom = Vector((net_x[pFrom_x],net_y[pFrom_y],0))
    pTo = setting[1].split('/')
    pTo_x = int(pTo[0])
    pTo_y = int(pTo[1])
    vTo = Vector((net_x[pTo_x],net_y[pTo_y],0))
    # 额枋长度
    fang_length = utils.getVectorDistance(vFrom,vTo)
    
    # 判断是否需要添加霸王拳
    bLeft = bRight = False
    # 左向添加的如：西南0/0#1/0，东南x/0#x/1，东北x/y#x-1/y,西北0/y#0/y-1
    # 右侧添加的如：东南x-1/0#x/0,东北x/y-1#x/y，西北0/y#1/y,西南0/0#0/1
    # 将两端相加进行判断
    # 左向：1/0,2x/1,2x-1/2y,0/2y-1
    # 右向：2x-1/0,2x/2y-1,1/2y,0/1
    fangStr = str(pFrom_x+pTo_x) + '/' + str(pFrom_y+pTo_y)
    xtop = len(net_x)-1
    ytop = len(net_y)-1
    if fangStr in ("1/0",
                    str(xtop*2) + '/1',                  # 2x/1
                    str(xtop*2-1) + '/' + str(ytop*2),   # 2x-1/2y
                    '0/' + str(ytop*2-1)                 # 0/2y-1
                    ):
        bLeft = True
        bwqX = -fang_length/2
        rotZ = math.radians(180)
    if fangStr in (
                    str(xtop*2-1) +'/0',                # 2x-1/0
                    str(xtop*2) + '/' + str(ytop*2-1),  # 2x/2y-1
                    '1/' + str(ytop*2),                 # 1/2y
                    "0/1"):
        bRight = True
        bwqX = fang_length/2
        rotZ = 0
    if bLeft or bRight:
        # 添加霸王拳，以大额枋为父对象，继承位置和旋转
        bawangquanObj = utils.copyObject(
            sourceObj=aData.bawangquan_source,
            name='霸王拳',parentObj=fangObj,
            location=(bwqX,0,con.EFANG_LARGE_H * dk/2),
            rotation=(0,0,rotZ)
        )
        # 霸王拳尺度权衡，参考马炳坚p163
        bawangquanObj.dimensions = (
            con.BAWANGQUAN_L*bData.piller_diameter,         # 长1D
            con.BAWANGQUAN_Y*bData.piller_diameter,         # 厚0.5D，马炳坚定义的0.8额枋
            con.BAWANGQUAN_H*fangObj.dimensions.z,          # 高0.8额枋
        )
        utils.applyTransfrom(bawangquanObj,use_scale=True)

# 获取开间是否有装修
# 涉及到wall_net参数中槛墙跨越多个开间，拆分到每个开间的数据
def __getWallRange(wallSetting):
    # 解析wallID，例如”wall#3/0#3/3“，或”window#0/0#0/1“，或”door#0/1#0/2“
    wallList = wallSetting.split(',')
    wallStr = ''
    for wallID in wallList:
        if wallID == '': continue
        setting = wallID.split('#')
        # 以柱编号定位
        # 起始柱子
        pFrom = setting[1].split('/')
        pFrom_x = int(pFrom[0])
        pFrom_y = int(pFrom[1])
        # 结束柱子
        pTo = setting[2].split('/')
        pTo_x = int(pTo[0])
        pTo_y = int(pTo[1])

        # 前后檐跨多间
        if abs(pFrom_x - pTo_x) > 1:
            if pFrom_x < pTo_x:
                pRange = range(pFrom_x,pTo_x)
            else:
                pRange = range(pTo_x,pFrom_x)
            for n in pRange:
                wallStr += str(n) + '/' + str(pFrom_y) \
                    + '#' + str(n+1) + '/' + str(pTo_y) + ','
        # 两山跨多间    
        elif abs(pFrom_y - pTo_y) > 1:
            if pFrom_y < pTo_y:
                pRange = range(pFrom_y,pTo_y)
            else:
                pRange = range(pTo_y,pFrom_y)
            for n in pRange:
                wallStr += str(pFrom_x) + '/' + str(n) \
                    + '#' + str(pTo_x) + '/' + str(n+1) + ','
        else:
            wallStr += str(pFrom_x) + '/' + str(pFrom_y) \
                    + '#' + str(pTo_x) + '/' + str(pTo_y) + ','
                                
    return wallStr

# 添加雀替
# 仅在外檐、且无装修的开间摆放
# 以大额枋为父对象，相对大额枋进行定位
# 已在blender中通过GN预先对不同大小的雀替和插斗进行了适配和组装
# 根据开间大小，自动切换了长款、中款、短款
def __buildQueti(fangObj):
    # 基础数据
    aData:tmpData = bpy.context.scene.ACA_temp
    buildingObj = utils.getAcaParent(fangObj,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    # 获取开间、进深数据
    net_x,net_y = getFloorDate(buildingObj)

    # 解析枋ID
    fangID = fangObj.ACA_data['fangID']
    setting = fangID.split('#')
    # 分解获取柱子编号
    pFrom = setting[0].split('/')
    pFrom_x = int(pFrom[0])
    pFrom_y = int(pFrom[1])
    vFrom = Vector((net_x[pFrom_x],net_y[pFrom_y],0))
    pTo = setting[1].split('/')
    pTo_x = int(pTo[0])
    pTo_y = int(pTo[1])
    vTo = Vector((net_x[pTo_x],net_y[pTo_y],0))
    # 额枋长度
    fang_length = utils.getVectorDistance(vFrom,vTo)
    
    # 判断仅在檐面、且无装修的开间摆放
    isQueti = False
    # 是否为前后檐？
    if pFrom_x == pTo_x and pFrom_x in (0,len(net_x)-1):
        isQueti = True
    # 是否为两山
    if pFrom_y == pTo_y and pFrom_y in (0,len(net_y)-1):
        isQueti = True
    # 是否有装修（槛墙、隔扇、槛窗等）
    # 解析模版输入的墙体设置，格式如下
    # "wall#3/0#3/3,wall#0/0#3/0,wall#0/3#3/3,window#0/0#0/1,window#0/2#0/3,door#0/1#0/2,"
    wallSetting = bData.wall_net
    wallStr = __getWallRange(wallSetting)
    fangID_alt = setting[1] + '#' + setting[0]
    if fangID in wallStr:
        isQueti = False
    if fangID_alt in wallStr:
        isQueti = False
    if not isQueti: return

    # 雀替的尺度参考马炳坚P183，长度为净面宽的1/4，高同大额枋或小额枋，厚为檐柱的3/10
    # 栱长1/2瓜子栱，高2斗口，厚同雀替
    # 雀替Z坐标从大额枋中心下移半大额枋+由额垫板+小额枋
    zoffset = con.EFANG_LARGE_H*dk/2
    if bData.use_smallfang:
        zoffset += (con.BOARD_YOUE_H*dk
                +con.EFANG_SMALL_H*dk)
    # 雀替对象在blender中用Geometry Nodes预先进行了自动拼装
    quetiObj = utils.copyObject(
        sourceObj=aData.queti_source,
        name='雀替',
        parentObj=fangObj,
        location=(0,0,-zoffset),
        singleUser=True
    )
    # 宽度适配到开间的净面宽
    quetiObj.dimensions.x = fang_length-bData.piller_diameter
    utils.applyTransfrom(quetiObj,use_scale=True)
    return

# 添加穿插枋
# 适用于采用了廊间做法的
def __buildCCFang(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    aData:tmpData = bpy.context.scene.ACA_temp
    # 查找或新建地盘根节点
    floorRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_FLOOR_ROOT)
    # 获取开间、进深数据
    net_x,net_y = getFloorDate(buildingObj)
    # 穿插枋列表
    ccfangList = []

    # 循环所有的柱子
    # 解析piller_net,如：
    pillerList = bData.piller_net.split(',')
    for pillerID in pillerList:
        if pillerID == '' : continue
        px,py = pillerID.split('/')
        px = int(px)
        py = int(py)

        # 判断柱子是否为金柱，并向相邻的檐柱做穿插枋
        # 前后檐
        if (py in (1,bData.y_rooms-1)
             and px not in (0, bData.x_rooms) ):
            if net_y[py] < 0:
                # 南面
                ccfangList.append("%d/%d#%d/%d" 
                            % (px,py,px,py-1))
            else:
                # 北面
                ccfangList.append("%d/%d#%d/%d" 
                            % (px,py,px,py+1))
        # 两山
        if (px in (1, bData.x_rooms-1) 
             and py not in (0,bData.y_rooms)):
            if net_x[px] < 0:
                # 西面
                ccfangList.append("%d/%d#%d/%d" 
                            % (px,py,px-1,py))
            else:
                # 东面
                ccfangList.append("%d/%d#%d/%d" 
                            % (px,py,px+1,py))

    # 循环生成穿插枋
    # 从柱头向下一个大额枋
    ccfangOffset = con.EFANG_LARGE_H*dk
    for ccfang in ccfangList:
        jinPiller,yanPiller = ccfang.split('#')
        # 起点檐柱
        px1,py1 = yanPiller.split('/')
        pStart = Vector((
            net_x[int(px1)],net_y[int(py1)],
            bData.piller_height-ccfangOffset
        ))
        # 终点金柱
        px2,py2 = jinPiller.split('/')
        pEnd = Vector((
            net_x[int(px2)],net_y[int(py2)],
            bData.piller_height-ccfangOffset
        ))
        # 做穿插枋proxy，定下尺寸、位置、大小
        ccFangProxy = utils.addCubeBy2Points(
            start_point=pStart,
            end_point=pEnd,
            depth=con.CCFANG_Y*dk,  # 高4斗口，厚3.2斗口
            height=con.CCFANG_H*dk,
            name='穿插枋proxy',
            root_obj=floorRootObj
        )
        utils.hideObj(ccFangProxy)
        # 引入穿插枋资源，与proxy适配
        ccFangObj = utils.copyObject(
            sourceObj=aData.ccfang_source,
            name='穿插枋',
            parentObj=ccFangProxy,
            location=(0,0,0),
            singleUser=True
        )
        ccFangObj.dimensions = ccFangProxy.dimensions
        utils.applyTransfrom(ccFangObj,use_scale=True)
        # 调整柱头伸出，一个柱径
        gnMod:bpy.types.NodesModifier = \
            ccFangObj.modifiers.get('ccFang')
        # 强制每个对象的node group为单一用户
        gnMod.node_group = gnMod.node_group.copy()
        if gnMod != None:
            utils.setGN_Input(gnMod,"pd",bData.piller_diameter/2+0.1)

    return

# 在柱间添加额枋
def __buildFang(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    aData:tmpData = bpy.context.scene.ACA_temp

    # 柱网根节点
    floorRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_FLOOR_ROOT)
    # 获取开间、进深数据
    net_x,net_y = getFloorDate(buildingObj)
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('柱网',parentColl=buildingColl)

    # 删除现有枋
    for obj in floorRootObj.children:
        if 'aca_type' in obj.ACA_data:
            if obj.ACA_data['aca_type'] == con.ACA_TYPE_FANG:
                # 连带小额枋、垫板子对象
                utils.deleteHierarchy(obj,del_parent=True)
    
    # 根据建筑模版的参数设置分布
    # '0/0#1/0,1/0#2/0,2/0#3/0,3/0#3/1,3/1#3/2,3/2#3/3,3/3#2/3,2/3#1/3,1/3#0/3,0/3#0/2,0/2#0/1,0/1#0/0,'
    fangStr = bData.fang_net
    fangID_List = fangStr.split(',')
    for fangID in fangID_List:
        if fangID == '': continue
        setting = fangID.split('#')
        # 分解获取柱子编号
        pFrom = setting[0].split('/')
        pFrom_x = int(pFrom[0])
        pFrom_y = int(pFrom[1])
        pTo = setting[1].split('/')
        pTo_x = int(pTo[0])
        pTo_y = int(pTo[1])

        # 如果为2坡顶，山面额枋按檐面额枋高度摆放
        if bData.roof_style in (
            con.ROOF_YINGSHAN,
            con.ROOF_YINGSHAN_JUANPENG,
            con.ROOF_XUANSHAN,
            con.ROOF_XUANSHAN_JUANPENG,
        ) and pFrom_x in (0,bData.x_rooms) \
        and pFrom_x == pTo_x:
            pillerHeight = bData.piller_height
        # 如果为4坡顶，额枋按起始柱子的实际高度摆放
        else:
            # 获取实际柱高，取比较矮的柱高
            pillerFromHeight = getPillerHeight(
                buildingObj,setting[0])
            pillerToHeight = getPillerHeight(
                buildingObj,setting[1])
            if pillerFromHeight > pillerToHeight:
                pillerHeight = pillerToHeight
            else:
                pillerHeight = pillerFromHeight

        # 计算枋的坐标        
        fang_x = (net_x[pFrom_x]+net_x[pTo_x])/2
        fang_y = (net_y[pFrom_y]+net_y[pTo_y])/2
        fang_z = pillerHeight - con.EFANG_LARGE_H*dk/2
        bigFangLoc = Vector((fang_x,fang_y,fang_z))   
        # 计算枋的方向，以建筑中心点，逆时针排布
        # 参考https://math.stackexchange.com/questions/285346/why-does-cross-product-tell-us-about-clockwise-or-anti-clockwise-rotation#:~:text=We%20can%20tell%20which%20direction,are%20parallel%20to%20each%20other.
        zAxis = Vector((0,0,1))
        vFrom = Vector((net_x[pFrom_x],net_y[pFrom_y],0))
        vTo = Vector((net_x[pTo_x],net_y[pTo_y],0))
        dirValue = vFrom.cross(vTo).dot(zAxis)
        if dirValue < 0:
            fangDir = vFrom-vTo
        else:
            fangDir = vTo-vFrom
        bigFangRot = utils.alignToVector(fangDir)
        # 计算枋的尺寸
        fang_length = utils.getVectorDistance(vFrom,vTo)
        bigFangScale = Vector((fang_length, 
                con.EFANG_LARGE_Y * dk,
                con.EFANG_LARGE_H * dk))
        # 绘制大额枋
        bigFangObj = utils.drawHexagon(
            bigFangScale,
            bigFangLoc,
            name =  "大额枋." + fangID,
            parent = floorRootObj,
            )
        bigFangObj.rotation_euler = bigFangRot
        bigFangObj.ACA_data['aca_obj'] = True
        bigFangObj.ACA_data['aca_type'] = con.ACA_TYPE_FANG
        bigFangObj.ACA_data['fangID'] = fangID
        # 设置梁枋彩画
        mat.setMat(bigFangObj,aData.mat_paint_beam_big)
        # 添加边缘导角
        modBevel:bpy.types.BevelModifier=bigFangObj.modifiers.new(
            "Bevel",'BEVEL'
        )
        modBevel.width = con.BEVEL_EXHIGH
        modBevel.segments=3
        # 241120 添加霸王拳
        __buildFangBWQ(bigFangObj)

        # 是否需要做小额枋
        if bData.use_smallfang:
            # 垫板
            dianbanScale = Vector((fang_length, 
                    con.BOARD_YOUE_Y*dk,
                    con.BOARD_YOUE_H*dk))
            dianbanLoc = Vector((0,0,
                    - con.EFANG_LARGE_H*dk/2 \
                    - con.BOARD_YOUE_H*dk/2))
            dianbanObj = utils.addCube(
                name="由额垫板." + fangID,
                location=dianbanLoc,
                dimension=dianbanScale,
                parent=bigFangObj,
            )
            dianbanObj.ACA_data['aca_obj'] = True
            dianbanObj.ACA_data['aca_type'] = con.ACA_TYPE_FANG
            dianbanObj.ACA_data['fangID'] = fangID
            # 设置材质
            mat.setMat(dianbanObj,aData.mat_paint_grasscouple)
            
            # 小额枋
            smallFangScale = Vector( (fang_length, 
                    con.EFANG_SMALL_Y*dk,
                    con.EFANG_SMALL_H*dk))
            smallFangLoc = Vector((0,0,
                    - con.EFANG_LARGE_H*dk/2 \
                    - con.BOARD_YOUE_H*dk \
                    - con.EFANG_SMALL_H*dk/2))
            smallFangObj = utils.drawHexagon(
                smallFangScale,
                smallFangLoc,
                name =  "小额枋." + fangID,
                parent = bigFangObj,
            )
            smallFangObj.ACA_data['aca_obj'] = True
            smallFangObj.ACA_data['aca_type'] = con.ACA_TYPE_FANG
            smallFangObj.ACA_data['fangID'] = fangID
            # 设置梁枋彩画
            mat.setMat(smallFangObj,aData.mat_paint_beam_small)
            # 添加边缘导角
            modBevel:bpy.types.BevelModifier=smallFangObj.modifiers.new(
                "Bevel",'BEVEL'
            )
            modBevel.width = con.BEVEL_HIGH
            modBevel.segments=2     
    
        # 201121 添加雀替
        __buildQueti(bigFangObj)
        
    # 聚焦到最后添加的大额枋，便于用户可以直接删除
    utils.focusObj(bigFangObj)
    return {'FINISHED'}

# 在选中的柱子间，添加枋
def addFang(buildingObj:bpy.types.Object,
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
    fangStr = bData.fang_net
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
                    fangID = pFrom.ACA_data['pillerID'] \
                        + '#' + pTo.ACA_data['pillerID'] 
                    fangID_alt = pTo.ACA_data['pillerID'] \
                         + '#' + pFrom.ACA_data['pillerID'] 
                    # 验证枋子是否已经存在
                    if fangID in fangStr or fangID_alt in fangStr:
                        print(fangID + " is in fangstr:" + fangStr)
                        continue
                    fangStr += fangID + ','
                    pFrom = piller

    # 根据fang_net字串，重新生成所有枋子
    bData.fang_net = fangStr
    result = __buildFang(buildingObj)
    
    return result

# 减枋
def delFang(buildingObj:bpy.types.Object,
              fangs:List[bpy.types.Object]):
    # 载入数据
    bData:acaData = buildingObj.ACA_data

    # 删除额枋对象
    for fang in fangs:
        # 校验用户选择的对象，可能误选了其他东西，直接忽略
        if 'aca_type' in fang.ACA_data:
            if fang.ACA_data['aca_type'] \
                == con.ACA_TYPE_FANG:
                utils.deleteHierarchy(fang,del_parent=True)

    # 重新生成柱网配置
    # 遍历父节点，查找所有的枋对象，重新组合fangstr
    floorRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_FLOOR_ROOT
    )    
    floorChildren:List[bpy.types.Object] = floorRootObj.children
    bData.fang_net = ''
    for fang in floorChildren:
        if 'aca_type' in fang.ACA_data:
            if fang.ACA_data['aca_type']==con.ACA_TYPE_FANG:
                fangID = fang.ACA_data['fangID']
                bData.fang_net += fangID + ','
    
    # 重新聚焦根节点
    utils.focusObj(buildingObj)

    return

# 计算柱子的高度
# 根据pill二ID在当前buildingObj中计算柱子高度
# 檐柱用输入的柱高
# 金柱根据是否做廊间举架，判断是否要自动升高
def getPillerHeight(buildingObj,pillerID):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    pillerIndex = pillerID.split('/')
    x = int(pillerIndex[0])
    y = int(pillerIndex[1])

    # 判断是否需要加高
    needResizePiller = False
    # 如果2坡顶，则前后廊柱全部升高
    if bData.roof_style in (
        con.ROOF_XUANSHAN,
        con.ROOF_XUANSHAN_JUANPENG,
        con.ROOF_YINGSHAN,
        con.ROOF_YINGSHAN_JUANPENG,
    ):
        if y in (1,bData.y_rooms-1):
            needResizePiller = True
    # 如果4坡顶，则仅内圈廊柱升高（无论前后廊，还是周围廊）
    if bData.roof_style in (
        con.ROOF_LUDING,
        con.ROOF_WUDIAN,
        con.ROOF_XIESHAN,
        con.ROOF_XIESHAN_JUANPENG,
    ):
        # 前后檐
        if x not in (0,bData.x_rooms) \
            and y in (1,bData.y_rooms-1):
            needResizePiller = True
        # 两山
        if x in (1,bData.x_rooms-1)  \
            and y not in (0,bData.y_rooms):
            needResizePiller = True
    # 如果无需加高，直接返回檐柱高度
    if not needResizePiller: 
        return bData.piller_height

    # 基于用户输入的檐柱高度计算
    pillerHeight = bData.piller_height

    # 1、如果有斗拱，先增高到挑檐桁底皮
    if bData.use_dg:
        pillerHeight += bData.dg_height
        # 是否使用平板枋
        if bData.use_pingbanfang:
            pillerHeight += con.PINGBANFANG_H*dk
    else:
        # 无斗拱，正心桁在柱头上一个桁垫板
        pillerHeight += con.BOARD_HENG_H*dk

    # 2、抬高廊步向上举架
    # 计算廊间进深
    net_x,net_y = getFloorDate(buildingObj)
    rafterSpan = abs(net_y[1]-net_y[0])
    # 如果带斗拱，叠加斗栱出跳
    if bData.use_dg:
        rafterSpan += bData.dg_extend
    # 乘以举折系数
    lift_ratio = []
    if bData.juzhe == '0':
        lift_ratio = con.LIFT_RATIO_DEFAULT
    if bData.juzhe == '1':
        lift_ratio = con.LIFT_RATIO_BIG
    if bData.juzhe == '2':
        lift_ratio = con.LIFT_RATIO_SMALL
    pillerHeight += rafterSpan*lift_ratio[0]
    
    # 3、向下扣除一个桁垫板高度，即到了梁底高度
    pillerHeight -= con.BOARD_HENG_H*dk

    return pillerHeight

# 根据柱网数组，排布柱子
# 1. 第一次按照模板生成，柱网下没有柱，一切从0开始；
# 2. 用户调整柱网的开间、进深，需要保持柱子的高、径、样式
# 3. 修改柱样式时，也会重排柱子
# 建筑根节点（内带设计参数集）
# 不涉及墙体重建，很快
def buildPillers(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    pd = bData.piller_diameter
    ph = bData.piller_height

    # 锁定操作目录
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('柱网',parentColl=buildingColl)

    # 解决bug：面阔间数在鼠标拖拽时可能为偶数，出现异常
    if bData.x_rooms % 2 == 0:
        # 不处理偶数面阔间数
        utils.showMessageBox("面阔间数不能为偶数","ERROR")
        return
    
    # 1、查找或新建地盘根节点
    floorRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_FLOOR_ROOT)
    if floorRootObj == None:        
        # 创建新地盘对象（empty）===========================================================
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        floorRootObj = bpy.context.object
        floorRootObj.name = "柱网层"
        floorRootObj.parent = buildingObj  # 挂接在对应建筑节点下
        floorRootObj.ACA_data['aca_obj'] = True
        floorRootObj.ACA_data['aca_type'] = con.ACA_TYPE_FLOOR_ROOT
        #与台基顶面对齐
        floor_z = bData.platform_height
        floorRootObj.location = (0,0,floor_z)
    else:
        # 清空地盘下所有的柱子、柱础
        utils.deleteHierarchy(floorRootObj)

    # 2、生成柱顶石模版，因为是简单立方体，就不做模版导入了
    pillerBase_h = 0.3
    pillerBase_popup = 0.02
    # 柱顶石边长（为了防止与方砖缦地交叠，做了1/10000的放大）
    pillerBase_size = con.PILLERBASE_WIDTH*pd * 1.0001
    pillerBottom_basemesh = utils.addCube(
        location=(0,0,
                    (- pillerBase_h/2
                    +pillerBase_popup)),
        dimension=(pillerBase_size,
                pillerBase_size,
                pillerBase_h),
    )
    # 柱顶石材质：石头
    mat.setMat(pillerBottom_basemesh,aData.mat_stone)
    utils.lockObj(pillerBottom_basemesh)
    # 添加bevel
    modBevel:bpy.types.BevelModifier = \
        pillerBottom_basemesh.modifiers.new('Bevel','BEVEL')
    modBevel.width = con.BEVEL_HIGH
    modBevel.offset_type = 'WIDTH'
    
    # 3、根据地盘数据，循环排布每根柱子
    net_x,net_y = getFloorDate(buildingObj)
    x_rooms = bData.x_rooms   # 面阔几间
    y_rooms = bData.y_rooms   # 进深几间
    piller_source = aData.piller_source
    for y in range(y_rooms + 1):
        for x in range(x_rooms + 1):
            # 统一命名为“柱.x/y”，以免更换不同柱形时，减柱设置失效
            pillerID = str(x) + '/' + str(y)
            
            # 减柱验证
            piller_list_str = bData.piller_net
            if pillerID not in piller_list_str \
                    and piller_list_str != "" :
                continue    # 结束本次循环

            # 复制柱子，仅instance，包含modifier
            pillerObj = utils.copyObject(
                sourceObj = piller_source,
                name = '柱子.'+pillerID,
                location=(net_x[x],net_y[y],0),
                dimensions=(pd,pd,ph),
                parentObj = floorRootObj,
                singleUser=True # 内外柱不等高，为避免打架，全部
            )
            pillerObj.ACA_data['aca_obj'] = True
            pillerObj.ACA_data['aca_type'] = con.ACA_TYPE_PILLER
            pillerObj.ACA_data['pillerID'] = pillerID
            # 241124 添加廊间金柱的升高处理
            if y_rooms>=3 and bData.use_hallway:
                pillerObj.dimensions.z = getPillerHeight(
                    buildingObj,pillerID)
            # 应用拉伸
            utils.applyTransfrom(pillerObj,use_scale=True)

            # 柱头贴图，注意此方法会破坏原有柱对象，并返回新对象
            newPillerObj = mat.setMat(pillerObj,aData.mat_paint_pillerhead,
                       override=True)

            # 复制柱础
            pillerbase_basemesh:bpy.types.Object = utils.copySimplyObject(
                sourceObj=aData.pillerbase_source,
                location=(0,0,0),
                scale=(
                        pd/piller_source.dimensions.x,
                        pd/piller_source.dimensions.y,
                        pd/piller_source.dimensions.x,
                    ),
                parentObj=newPillerObj
            )
            utils.lockObj(pillerbase_basemesh)
            # 柱础材质：石头
            mat.setMat(pillerbase_basemesh,aData.mat_stone)
            
            # 复制柱顶石
            pillerBottomObj = utils.copySimplyObject(
                name='柱顶石',
                sourceObj=pillerBottom_basemesh,
                parentObj=newPillerObj
            )
            utils.lockObj(pillerBottomObj)

    # 移除柱顶石模版    
    bpy.data.objects.remove(pillerBottom_basemesh)

    # 重新生成柱网配置
    floorChildren:List[bpy.types.Object] = floorRootObj.children
    bData.piller_net = ''
    for piller in floorChildren:
        if 'aca_type' in piller.ACA_data:
            if piller.ACA_data['aca_type']==con.ACA_TYPE_PILLER:
                pillerID = piller.ACA_data['pillerID']
                bData.piller_net += pillerID + ','

    # 添加柱间的额枋
    # 重设柱网时，可能清除fang_net数据，而导致异常
    if bData.fang_net != '':
        __buildFang(buildingObj)

    # 做廊间举架时，添加穿插枋
    if bData.use_hallway:
        __buildCCFang(buildingObj)

    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)
    
    return

# 减柱并保存
def delPiller(buildingObj:bpy.types.Object,
              pillers:List[bpy.types.Object]):
    # 载入数据
    bData:acaData = buildingObj.ACA_data

    # 删除柱子和柱础
    # 20240624 发现批量删除柱子时报错：ReferenceError: StructRNA of type Object has been removed
    # 发现执行柱子删除时，顺带删除了柱础，导致真的轮询到柱础时已经找不到对象
    # 为了解决这个问题，先把要删除的对象名称挑出来，然后仅执行这些对象的删除
    # https://blender.stackexchange.com/questions/206060/how-to-resolve-referenceerror-structrna-of-type-object-has-been-removed
    delPillerNames = []
    for piller in pillers:
        # 校验用户选择的对象，可能误选了其他东西，直接忽略
        if 'aca_type' in piller.ACA_data:
            # 柱身向上查找柱proxy
            if piller.ACA_data['aca_type'] == \
                    con.ACA_TYPE_PILLER:
                # 验证柱proxy没有重复
                if piller.name not in delPillerNames:
                    delPillerNames.append(piller.name)    
    
    # 批量删除所有的柱proxy
    for name in delPillerNames:
        piller = bpy.data.objects[name]
        utils.deleteHierarchy(piller,del_parent=True)

    # 重新生成柱网配置
    floorRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_FLOOR_ROOT
    )    
    floorChildren:List[bpy.types.Object] = floorRootObj.children
    bData.piller_net = ''
    for piller in floorChildren:
        if 'aca_type' in piller.ACA_data:
            if piller.ACA_data['aca_type']==con.ACA_TYPE_PILLER:
                pillerID = piller.ACA_data['pillerID']
                bData.piller_net += pillerID + ','

    # 聚焦根节点
    utils.focusObj(buildingObj)
    return

# 根据用户在插件面板修改的柱高、柱径，缩放柱子外观
# 会自动触发墙体的重建，速度很慢
# 绑定于data.py中objdata属性中触发的回调
def resizePiller(buildingObj:bpy.types.Object):   
    bData:acaData = buildingObj.ACA_data
    
    floorRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_FLOOR_ROOT)
    if len(floorRootObj.children) >0 :
        for pillerProxy in floorRootObj.children:
            if pillerProxy.ACA_data['aca_type'] == con.ACA_TYPE_PILLER:
                for child in pillerProxy.children:
                    if '柱子' in child.name:
                        child.dimensions = (
                            bData.piller_diameter,
                            bData.piller_diameter,
                            bData.piller_height
                        )

    # 柱高、柱径的变化，都会引起隔扇、墙体的变化，需要重建
    # 重新生成墙体
    funproxy = partial(buildWall.buildWallLayout,buildingObj=buildingObj)
    utils.fastRun(funproxy)

    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)
    utils.outputMsg("Piller resized")

# 重设柱网设置，让减柱重新显示
def resetFloor(buildingObj:bpy.types.Object):
    bData:acaData = buildingObj.ACA_data
    bData.piller_net = ''
    bData.fang_net = ''
    bData.wall_net = ''
    result = buildFloor(buildingObj)
    return result

# 执行营造整体过程
# 输入buildingObj，自带设计参数集，且做为其他构件绑定的父节点
def buildFloor(buildingObj:bpy.types.Object):
    # 定位到collection，如果没有则新建
    utils.setCollection(con.ROOT_COLL_NAME,isRoot=True)

    # 新建还是刷新？
    if buildingObj == None:
        utils.outputMsg("创建新建筑...")
        # 获取panel上选择的模版
        templateName = bpy.context.scene.ACA_data.template
        # 添加建筑根节点，同时载入模版
        buildingObj = __addBuildingRoot(templateName)
    else:
        # # 删除屋顶，柱网变化必然引起屋顶重构
        # roofRoot = utils.getAcaChild(
        #     buildingObj,con.ACA_TYPE_ROOF_ROOT)
        # utils.deleteHierarchy(roofRoot)
        # # 删除墙体，柱网变化必然引起墙体重构
        # wallRoot = utils.getAcaChild(
        #     buildingObj,con.ACA_TYPE_WALL_ROOT)
        # utils.deleteHierarchy(wallRoot)

        # 20240616 简单粗暴的全部删除
        # todo：wallproxy的个性化设置丢失了
        utils.deleteHierarchy(buildingObj)

     # 载入数据
    bData:acaData = buildingObj.ACA_data

    # 生成柱网
    if bData.is_showPillers:
        utils.outputMsg("Building Pillers...")
        buildPillers(buildingObj)
    
    # 生成台基
    if bData.is_showPlatform:
        utils.outputMsg("Building Platform...")
        buildPlatform.buildPlatform(buildingObj)
    
    # 生成墙体
    if bData.is_showWalls:
        utils.outputMsg("Building Wall...")
        buildWall.buildWallLayout(buildingObj)
    
    # 生成屋顶
    utils.outputMsg("Building Roof...")
    buildRoof.buildRoof(buildingObj)

    # 重新聚焦回根节点
    utils.focusObj(buildingObj)

    return {'FINISHED'}