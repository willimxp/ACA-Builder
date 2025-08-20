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
from . import template
from . import buildWall
from . import buildPlatform
from . import buildRoof

# 添加建筑empty根节点，并绑定设计模板
# 返回建筑empty根节点对象
# 被ACA_OT_add_newbuilding类调用
def __addBuildingRoot(templateName,
                      comboObj = None,
                      ):    
    # 新建建筑目录，强制新建，遇到重名自动添加.001后缀
    buildingColl = bpy.data.collections.new(templateName)
    # 建筑目录的父目录
    if comboObj is not None:        
        # 组合建筑，挂接在combo根目录下
        parentColl = comboObj.users_collection[0]
    else:
        # 单体建筑，挂接在ACA根目录下
        parentColl = utils.setCollection(
            con.COLL_NAME_ROOT,isRoot=True)
    # 关联父目录
    parentColl.children.link(buildingColl)
    # 聚焦父目录
    utils.focusCollection(buildingColl.name)
    
    # 创建buildObj根节点
    # 原点摆放在3D Cursor位置
    buildingObj = utils.addEmpty(
        name=templateName,
        location=bpy.context.scene.cursor.location
    )
    bData:acaData = buildingObj.ACA_data
    bData['aca_type'] = con.ACA_TYPE_BUILDING
    bData['template_name'] = templateName

    if comboObj is not None:
        # 绑定Combo对象父子关系
        buildingObj.parent = comboObj

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
    buildingObj = utils.getAcaParent(fangObj,con.ACA_TYPE_BUILDING)
    bData : acaData = buildingObj.ACA_data
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
    # 注意：对于只有一开间的小建筑，可能在同一根枋上做左右两头的霸王拳
    # 左向添加的如：西南0/0#1/0，东南x/0#x/1，东北x/y#x-1/y,西北0/y#0/y-1
    # 将两端相加进行判断，左向：1/0,2x/1,2x-1/2y,0/2y-1
    fangStr = str(pFrom_x+pTo_x) + '/' + str(pFrom_y+pTo_y)
    xtop = len(net_x)-1
    ytop = len(net_y)-1
    if fangStr in ("1/0",
                    str(xtop*2) + '/1',                  # 2x/1
                    str(xtop*2-1) + '/' + str(ytop*2),   # 2x-1/2y
                    '0/' + str(ytop*2-1)                 # 0/2y-1
                    ):
        bwqX = -fang_length/2
        rotZ = math.radians(180)
        __drawBWQ(fangObj,bwqX,rotZ)
    # 右侧添加的如：东南x-1/0#x/0,东北x/y-1#x/y，西北0/y#1/y,西南0/0#0/1
    # 将两端相加进行判断，右向：2x-1/0,2x/2y-1,1/2y,0/1
    if fangStr in (
                    str(xtop*2-1) +'/0',                # 2x-1/0
                    str(xtop*2) + '/' + str(ytop*2-1),  # 2x/2y-1
                    '1/' + str(ytop*2),                 # 1/2y
                    "0/1"):
        bwqX = fang_length/2
        rotZ = 0
        __drawBWQ(fangObj,bwqX,rotZ)
    
    return
        

# 绘制霸王拳
def __drawBWQ(fangObj:bpy.types.Object,
              bwqX,
              rotZ,):
    buildingObj = utils.getAcaParent(fangObj,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    # 添加霸王拳，以大额枋为父对象，继承位置和旋转
    bawangquanObj = utils.copyObject(
        sourceObj=aData.bawangquan_source,
        name='霸王拳',parentObj=fangObj,
        location=(bwqX,0,con.EFANG_LARGE_H * dk/2),
        rotation=(0,0,rotZ),
        singleUser=True
    )
    # 霸王拳尺度权衡，参考马炳坚p163
    bawangquanObj.dimensions = (
        con.BAWANGQUAN_L*pd,         # 长1D
        con.BAWANGQUAN_Y*pd,         # 厚0.5D，马炳坚定义的0.8额枋
        con.BAWANGQUAN_H*pd,          # 厚0.5D，马炳坚定义的高0.8额枋
    )
    # 250613 根据斗口的缩放，调整霸王拳的位置
    bawangquanObj.location.x += \
        (bData.piller_diameter - pd)/2*utils.getSign(bwqX)
    utils.applyTransform(bawangquanObj,use_scale=True)
    # 霸王拳着色
    mat.paint(bawangquanObj,con.M_BAWANGQUAN,override=True)
    return

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
    # 是否为前后檐
    if pFrom_y == pTo_y and pFrom_y in (0,len(net_y)-1):
        isQueti = True
    # 是否为两山
    if pFrom_x == pTo_x and pFrom_x in (0,len(net_x)-1):
        isQueti = True
        # 硬山的两山不做雀替
        if bData.roof_style in (
            con.ROOF_YINGSHAN,
            con.ROOF_YINGSHAN_JUANPENG):
            isQueti = False
        else:
            isQueti = True
    # 是否有装修（槛墙、隔扇、槛窗等）
    # 解析模板输入的墙体设置，格式如下
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
    # 250613 根据斗口的缩放，调整雀替的尺度
    quetiObj.scale.y = dk / con.DEFAULT_DK
    quetiObj.scale.z = dk / con.DEFAULT_DK
    # 250613 有GN的对象不能应用缩放
    # utils.applyTransform(quetiObj,use_scale=True)
    # 应用GN修改器
    utils.applyAllModifer(quetiObj)
    # 设置雀替外观
    mat.paint(quetiObj,con.M_QUETI,override=True)
    return quetiObj

# 添加穿插枋
# 适用于采用了廊间做法的
def __buildCCFang(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    
    # 校验：穿插枋做在廊间，所以，进深至少3间，面阔至少3间
    if bData.x_rooms < 3 or bData.y_rooms < 3:
        # 否则不做
        return {'CANCELLED'}
    
    dk = bData.DK
    aData:tmpData = bpy.context.scene.ACA_temp
    # 查找或新建地盘根节点
    floorRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_FLOOR_ROOT)
    utils.deleteByName(floorRootObj,name='穿插枋')
    
    # 获取开间、进深数据
    net_x,net_y = getFloorDate(buildingObj)
    # 穿插枋列表
    ccfangList = []

    # 解析柱网
    # 如果是重檐建筑
    if bData.use_double_eave:
        # 重檐主建筑(下檐)，柱网拼接，以便穿插枋连接上檐和下檐柱网
        if bData.combo_type == con.COMBO_MAIN:
            pillerNet = __getComboPillerNet(buildingObj)
        # 重檐的上檐，不做穿插枋，由金枋代替
        if bData.combo_type == con.COMBO_DOUBLE_EAVE:
            return {'CANCELLED'}
    else:
        pillerNet = bData.piller_net
    # 柱网列表
    pillerList = pillerNet.rstrip(',').split(',')

    # 循环所有的柱子
    for pillerID in pillerList:
        px,py = pillerID.split('/')
        px = int(px)
        py = int(py)

        # 判断柱子是否为金柱，并向相邻的檐柱做穿插枋
        # 前后檐（包括2坡顶和4坡顶）
        if (py in (0,bData.y_rooms)
             and px not in (0, bData.x_rooms) ):
            if net_y[py] > 0: # 北面
                pillerNext = f"{px}/{py-1}" 
            else: # 南面
                pillerNext = f"{px}/{py+1}" 
            if pillerNext in pillerNet:
                ccfangList.append(f"{pillerID}#{pillerNext}") 

        # 如果4坡顶，两山做穿插枋
        # 对于2坡顶，两山廊间应该做金枋，而不是穿插枋
        if bData.roof_style in (
            con.ROOF_LUDING,
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
        ):
            if (px in (0, bData.x_rooms) and 
                py not in (0,bData.y_rooms)):
                if net_x[px] > 0: # 东面
                    pillerNext = f"{px-1}/{py}" 
                else: # 西面
                    pillerNext = f"{px+1}/{py}" 
                if pillerNext in pillerNet:
                    ccfangList.append(f"{pillerID}#{pillerNext}")


    # 循环生成穿插枋
    # 从柱头向下一个大额枋
    ccfangOffset = con.EFANG_LARGE_H*dk
    for ccfang in ccfangList:
        # 找到相对较矮的柱高
        startPillerID,endPillerID = ccfang.split('#')
        startPillerHeight = getPillerHeight(
                    buildingObj,startPillerID)
        endPillerHeight = getPillerHeight(
                    buildingObj,endPillerID)
        if startPillerHeight > endPillerHeight:
            pillerHeight = endPillerHeight
        else:
            pillerHeight = startPillerHeight
        # 起点檐柱
        px1,py1 = startPillerID.split('/')
        pStart = Vector((
            net_x[int(px1)],net_y[int(py1)],
            pillerHeight-ccfangOffset
        ))
        # 终点金柱
        px2,py2 = endPillerID.split('/')
        pEnd = Vector((
            net_x[int(px2)],net_y[int(py2)],
            pillerHeight-ccfangOffset
        ))
        # 做穿插枋proxy，定下尺寸、位置、大小
        ccFangProxy = utils.addCubeBy2Points(
            start_point=pStart,
            end_point=pEnd,
            depth=con.CCFANG_Y*dk,  # 高4斗口，厚3.2斗口
            height=con.CCFANG_H*dk,
            name='穿插枋.'+ccfang,
            root_obj=floorRootObj
        )
        # 引入穿插枋资源，与proxy适配
        ccFangObj = utils.copyObject(
            sourceObj=aData.ccfang_source,
            singleUser=True
        )
        # 将proxy定位数据传递给穿插枋
        utils.replaceObject(
            fromObj=ccFangProxy,
            toObj=ccFangObj,
            delete=True,
            use_Modifier=False
        )
        # 调整柱头伸出，一个柱径
        gnMod:bpy.types.NodesModifier = \
            ccFangObj.modifiers.get('ccFang')
        # 强制每个对象的node group为单一用户
        gnMod.node_group = gnMod.node_group.copy()
        if gnMod != None:
            pd = bData.piller_diameter/2
            # 出梢0.1m，并根据斗口缩放
            extend = 0.1 * bData.DK / con.DEFAULT_DK
            # 根据实际穿插枋的拉伸进行缩放
            var = (pd+extend)/ccFangObj.scale.x
            utils.setGN_Input(gnMod,"pd",var)
        utils.applyAllModifer(ccFangObj)
        # 穿插枋着色
        mat.paint(ccFangObj,con.M_FANG_CHUANCHA,override=True)

    return {'FINISHED'}

# 添加金柱之间的金枋
def __buildJinFang(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    aData:tmpData = bpy.context.scene.ACA_temp
    # 查找或新建地盘根节点
    floorRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_FLOOR_ROOT)
    utils.deleteByName(floorRootObj,name='金枋')
    
    # 获取开间、进深数据
    net_x,net_y = getFloorDate(buildingObj)
    # 金枋列表
    jinfangList = []

    # 生成金枋列表jinfangList
    # 循环解析柱网piller_net，删除结尾的','，并用','分割
    pillerList = bData.piller_net.rstrip(',').split(',')
    for pillerID in pillerList:
        px,py = pillerID.split('/')
        px = int(px)
        py = int(py)

        # 判断柱子是否为金柱，并向相邻的金柱做金枋
        # 横向金枋，檐柱和金柱不做，仅做内金柱间
        # 四坡顶廊间不做横向金枋，改作穿插枋
        if bData.roof_style in (con.ROOF_LUDING,
                                con.ROOF_WUDIAN,
                                con.ROOF_XIESHAN,
                                con.ROOF_XIESHAN_JUANPENG):
            pxRangeNot = (0,bData.x_rooms-1,bData.x_rooms)
        else:
            pxRangeNot = (bData.x_rooms,)
        if (px not in pxRangeNot and 
            py not in (0,1,bData.y_rooms-1,bData.y_rooms)):  
            # 250802 是否存在相邻的柱子？
            pillerNext = f"{px+1}/{py}"  
            if pillerNext in bData.piller_net:
                jinfangList.append(f"{pillerID}#{pillerNext}")
        
        # 纵向金枋，无论内外金柱，都做纵向金枋
        # 四坡顶廊间不做纵向金枋，改作额枋
        if bData.roof_style in (con.ROOF_LUDING,
                                con.ROOF_WUDIAN,
                                con.ROOF_XIESHAN,
                                con.ROOF_XIESHAN_JUANPENG):
            pxRangeNot = (0,1,bData.x_rooms-1,bData.x_rooms)
        else:
            pxRangeNot = (0,bData.x_rooms,)
        if (px not in pxRangeNot and 
            py not in (0,bData.y_rooms-1, bData.y_rooms)):
            # 250802 是否存在相邻的柱子？
            pillerNext = f"{px}/{py+1}"   
            if pillerNext in bData.piller_net:
                jinfangList.append(f"{pillerID}#{pillerNext}")

    # 重檐上檐代替穿插枋做的金枋
    if (bData.use_double_eave and 
        bData.combo_type == con.COMBO_DOUBLE_EAVE):
        # 循环所有的柱子
        for pillerID in pillerList:
            px,py = pillerID.split('/')
            px = int(px)
            py = int(py)

            # 判断柱子是否为金柱，并向相邻的檐柱做穿插枋
            # 前后檐（包括2坡顶和4坡顶）
            if (py in (0,bData.y_rooms)
                and px not in (0, bData.x_rooms) ):
                if net_y[py] > 0: # 北面
                    pillerNext = f"{px}/{py-1}" 
                else: # 南面
                    pillerNext = f"{px}/{py+1}" 
                if pillerNext in bData.piller_net:
                    jinfangList.append(f"{pillerID}#{pillerNext}") 

            # 如果4坡顶，两山做穿插枋
            # 对于2坡顶，两山廊间应该做金枋，而不是穿插枋
            if bData.roof_style in (
                con.ROOF_LUDING,
                con.ROOF_WUDIAN,
                con.ROOF_XIESHAN,
                con.ROOF_XIESHAN_JUANPENG,
            ):
                if (px in (0, bData.x_rooms) and 
                    py not in (0,bData.y_rooms)):
                    if net_x[px] > 0: # 东面
                        pillerNext = f"{px-1}/{py}" 
                    else: # 西面
                        pillerNext = f"{px+1}/{py}" 
                    if pillerNext in bData.piller_net:
                        jinfangList.append(f"{pillerID}#{pillerNext}")

    # 循环生成金枋（金枋在柱头）
    for jinfang in jinfangList:
        startPillerID,endPillerID = jinfang.split('#')
        # 找到相对较矮的柱高
        startPillerHeight = getPillerHeight(
                    buildingObj,startPillerID)
        endPillerHeight = getPillerHeight(
                    buildingObj,endPillerID)
        if startPillerHeight > endPillerHeight:
            pillerHeight = endPillerHeight
        else:
            pillerHeight = startPillerHeight
        # 起点檐柱
        px1,py1 = startPillerID.split('/')
        pStart = Vector((
            net_x[int(px1)],net_y[int(py1)],
            pillerHeight-con.HENGFANG_H*dk/2
        ))
        # 终点金柱
        px2,py2 = endPillerID.split('/')
        pEnd = Vector((
            net_x[int(px2)],net_y[int(py2)],
            pillerHeight-con.HENGFANG_H*dk/2
        ))
        # 做金枋，定下尺寸、位置、大小
        # 金枋做小一圈，以免和梁架生成的桁枋打架
        # 其实这里的金枋和桁架的金枋是同一个东西，应该在生成桁架时避开
        jinFangObj = utils.addCubeBy2Points(
            start_point=pStart,
            end_point=pEnd,
            depth=con.HENGFANG_Y*dk-0.01,
            height=con.HENGFANG_H*dk-0.01,
            name='金枋.'+jinfang,
            root_obj=floorRootObj
        )
        # 刷漆
        mat.paint(jinFangObj,con.M_FANG_JIN)
        # 倒角
        utils.addModifierBevel(
            object=jinFangObj,
            width=con.BEVEL_LOW
        )

    return

# 在柱间添加额枋
def __buildFang(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    aData:tmpData = bpy.context.scene.ACA_temp

    # 根据fang_net判断是否需要自动生成
    # '0/0#1/0,1/0#2/0,2/0#3/0,3/0#3/1,3/1#3/2,3/2#3/3,3/3#2/3,2/3#1/3,1/3#0/3,0/3#0/2,0/2#0/1,0/1#0/0,'
    # fangNet = bData.fang_net
    # 250802 不再保留以前用户手工创建的额枋，而完全按照柱网自动判断
    fangNet = ''

    # 自动生成fangstr
    # 提取柱网列表
    pillerList = bData.piller_net.rstrip(',').split(',')
    for pillerID in pillerList:
        px,py = pillerID.split('/')
        px = int(px)
        py = int(py)

        # 判断柱子是否为檐柱，并向相邻的檐柱做额枋
        # 横向
        # 外檐都做额枋
        waiyan_range = (py in (0,bData.y_rooms) 
                and px not in (bData.x_rooms,))
        # 內檐为了适配內檐装修，也做额枋
        if bData.roof_style in (con.ROOF_LUDING,
                                con.ROOF_WUDIAN,
                                con.ROOF_XIESHAN,
                                con.ROOF_XIESHAN_JUANPENG):
            # 四坡顶廊间不做
            neiyan_range = (py in (1,bData.y_rooms-1) 
                    and px not in (0,bData.x_rooms-1,bData.x_rooms))
        else:
            # 2坡顶廊间也做
            neiyan_range = (py in (1,bData.y_rooms-1) 
                    and px not in (bData.x_rooms,))
        if (waiyan_range or neiyan_range):
            # 250714是否存在相邻的柱子？
            pillerNext = f"{px+1}/{py}"
            if pillerNext in bData.piller_net:
                # 构造fangID
                sfang = f"{pillerID}#{pillerNext},"
                sfang_alt = f"{pillerNext}#{pillerID},"
                # 判断该fangID是否已经在fangNet中
                if (sfang not in fangNet 
                    and sfang_alt not in fangNet):
                    fangNet += sfang

        # 纵向
        # 外檐都做额枋
        waiyan_range = (px in (0, bData.x_rooms) 
                and py != bData.y_rooms)
        # 內檐为了适配四坡顶的內檐装修，也做额枋（但是廊间不做）
        if bData.roof_style in (con.ROOF_LUDING,
                                con.ROOF_WUDIAN,
                                con.ROOF_XIESHAN,
                                con.ROOF_XIESHAN_JUANPENG):
            neiyan_range = (px in (1, bData.x_rooms-1) 
                    and py not in (0,bData.y_rooms-1,bData.y_rooms))
        else:
            neiyan_range = False
        if (waiyan_range or neiyan_range):
            pillerNext = f"{px}/{py+1}"
            if pillerNext in bData.piller_net:
                sfang = f"{pillerID}#{pillerNext},"
                sfang_alt = f"{pillerNext}#{pillerID},"
                # 判断该fangStr是否已经在fangNet中
                if (sfang not in fangNet 
                    and sfang_alt not in fangNet):
                    fangNet += sfang
    # 将fangstr存入bdata
    bData['fang_net'] = fangNet

    # 柱网根节点
    floorRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_FLOOR_ROOT)
    # 获取开间、进深数据
    net_x,net_y = getFloorDate(buildingObj)
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection(
        con.COLL_NAME_PILLER,
        parentColl=buildingColl)

    # 删除现有枋
    for obj in floorRootObj.children:
        if 'aca_type' in obj.ACA_data:
            if obj.ACA_data['aca_type'] == con.ACA_TYPE_FANG:
                # 连带小额枋、垫板子对象
                utils.deleteHierarchy(obj,del_parent=True)
    
    # 根据建筑模板的参数设置分布
    fangID_List = fangNet.split(',')
    for fangID in fangID_List:
        if fangID == '': continue

        # 合并大小额枋、由额垫板
        fangPart = []

        setting = fangID.split('#')
        # 分解获取柱子编号
        pFrom = setting[0].split('/')
        pFrom_x = int(pFrom[0])
        pFrom_y = int(pFrom[1])
        pTo = setting[1].split('/')
        pTo_x = int(pTo[0])
        pTo_y = int(pTo[1])

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
        # 为了防止柱头与大额枋之间穿模，同时也便于在俯视图中选择柱头
        # 将额枋轻微位移1mm
        fang_z -= 0.001
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
            name =  "额枋." + fangID,
            parent = floorRootObj,
            )
        bigFangObj.rotation_euler = bigFangRot
        bigFangObj.ACA_data['aca_obj'] = True
        bigFangObj.ACA_data['aca_type'] = con.ACA_TYPE_FANG
        bigFangObj.ACA_data['fangID'] = fangID
        # 设置梁枋彩画
        mat.paint(bigFangObj,con.M_FANG_EBIG)
        # 添加边缘导角
        utils.addModifierBevel(bigFangObj, 
                               width=con.BEVEL_EXHIGH, 
                               segments=3)
        fangPart.append(bigFangObj)
        # 241120 添加霸王拳
        # 仅对四坡顶做霸王拳，硬山、悬山等不做霸王拳
        if bData.roof_style in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
            con.ROOF_LUDING,
        ):
            # 重檐的上檐不做霸王拳
            if (bData.use_double_eave and
                bData.combo_type != con.COMBO_DOUBLE_EAVE):
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
            # 设置公母草，注意对象被替换
            newDianbanObj = mat.paint(dianbanObj,con.M_BOARD_YOUE)
            fangPart.append(newDianbanObj)
            
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
            mat.paint(smallFangObj,con.M_FANG_ESMALL)
            # 添加边缘导角
            utils.addModifierBevel(smallFangObj, 
                                   width=con.BEVEL_HIGH, 
                                   segments=2)
            fangPart.append(smallFangObj)
    
        # 201121 添加雀替
        quetiObj = __buildQueti(bigFangObj)
        if quetiObj != None:
            fangPart.append(quetiObj)

        # 合并大小额枋、由额垫板
        if len(fangPart) > 1:
            fangJoined = utils.joinObjects(fangPart,newName='额枋.'+ fangID)
            bigFangObj = fangJoined
        
    # # 聚焦到最后添加的大额枋，便于用户可以直接删除
    # utils.focusObj(bigFangObj)
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
        utils.popMessageBox("请至少选择2根柱子")
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

# 计算檐柱、金柱高度
# 檐柱直接返回用户输入的柱高
# 金柱如果不做斗拱、不做廊间举架，与檐柱通高
# 如果做斗拱，则抬升斗拱高度-2*正心枋
# 如果做廊间举架，则额外抬升檐步举高
def getPillerHeight(buildingObj,pillerID):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    pillerIndex = pillerID.split('/')
    x = int(pillerIndex[0])
    y = int(pillerIndex[1])

    # 默认为用户输入的檐柱高
    pillerHeight = bData.piller_height

    # 1、判断是否要做斗栱增高
    needLiftDG = False
    # 如果2坡顶，则前后金柱全部升高
    if bData.roof_style in (
        con.ROOF_XUANSHAN,
        con.ROOF_XUANSHAN_JUANPENG,
        con.ROOF_YINGSHAN,
        con.ROOF_YINGSHAN_JUANPENG,
    ):
        if y not in (0,bData.y_rooms):
            needLiftDG = True
    # 如果4坡顶，则仅内圈金柱升高（无论前后廊，还是周围廊）
    if bData.roof_style in (
        con.ROOF_LUDING,
        con.ROOF_WUDIAN,
        con.ROOF_XIESHAN,
        con.ROOF_XIESHAN_JUANPENG,
        con.ROOF_PINGZUO,
    ):
        if x not in (0,bData.x_rooms) \
           and y not in (0,bData.y_rooms):
            needLiftDG = True
    
    # 如果有斗拱，先增高到挑檐桁底皮
    if needLiftDG and bData.use_dg:
        pillerHeight += bData.dg_height
        # 是否使用平板枋
        if bData.use_pingbanfang:
            pillerHeight += con.PINGBANFANG_H*dk
        # 向下扣除金桁垫板，即到了梁底高度
        pillerHeight -= con.BOARD_JINHENG_H*dk


    # 2、判断是否需要做廊步举架
    needResizePiller = False
    if bData.y_rooms>=3 and bData.use_hallway:
        # 如果2坡顶，则前后廊柱全部升高
        if bData.roof_style in (
            con.ROOF_XUANSHAN,
            con.ROOF_XUANSHAN_JUANPENG,
            con.ROOF_YINGSHAN,
            con.ROOF_YINGSHAN_JUANPENG,
        ):
            if y not in (0,bData.y_rooms):
                needResizePiller = True
        # 如果4坡顶，则仅内圈廊柱升高（无论前后廊，还是周围廊）
        if bData.roof_style in (
            con.ROOF_LUDING,
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
            con.ROOF_PINGZUO,
        ):
            # 前后檐
            if x not in (0,bData.x_rooms) \
                and y not in (0,bData.y_rooms):
                needResizePiller = True
            # 两山
            if x not in (0,bData.x_rooms)  \
                and y not in (0,bData.y_rooms):
                needResizePiller = True

    if needResizePiller:
        # 计算廊间进深
        net_x,net_y = getFloorDate(buildingObj)
        rafterSpan = abs(net_y[1]-net_y[0])
        # 如果带斗拱，叠加斗栱出跳
        if bData.use_dg:
            rafterSpan += bData.dg_extend
        # 乘以举折系数
        from . import buildBeam
        lift_ratio = buildBeam.getLiftRatio(buildingObj)
        pillerHeight += rafterSpan*lift_ratio[0]  

        # 250225 补偿檐桁垫板与金桁垫板的高度差
        # 无斗栱时，正心桁由檐垫板支撑，金桁由金桁垫板支撑，导致了该高度差
        if not bData.use_dg:
            pillerHeight += (con.BOARD_YANHENG_H
                    -con.BOARD_JINHENG_H)*dk

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

    # 锁定操作目录
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection(
        con.COLL_NAME_PILLER,
        parentColl=buildingColl)

    # 解决bug：面阔间数在鼠标拖拽时可能为偶数，出现异常
    if bData.x_rooms % 2 == 0:
        # 不处理偶数面阔间数
        utils.popMessageBox("面阔间数不能为偶数")
        return
    
    # 1、查找或新建地盘根节点
    floorRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_FLOOR_ROOT)
    if floorRootObj == None:        
        #与台基顶面对齐
        floor_z = bData.platform_height
        # 创建新地盘对象（empty）
        floorRootObj = utils.addEmpty(
            name=con.COLL_NAME_PILLER,
            parent=buildingObj,
            location = (0,0,floor_z)
        )
        floorRootObj.ACA_data['aca_obj'] = True
        floorRootObj.ACA_data['aca_type'] = con.ACA_TYPE_FLOOR_ROOT
    else:
        # 清空地盘下所有的柱子、柱础
        utils.deleteHierarchy(floorRootObj)

    # 2、柱子素材准备
    piller_source = utils.copySimplyObject(
        aData.piller_source,singleUser=True)
    # 生成柱顶石模板，因为是简单立方体，就不做模板导入了
    pillerBase_h = 0.3
    pillerBase_popup = 0.02
    # 柱顶石边长（为了防止与方砖缦地交叠，做了1/10000的放大）
    pillerBase_size = con.PILLERBASE_WIDTH*pd * 1.0001
    pillerBottom_basemesh = utils.addCube(
        name='柱顶石',
        location=(0,0,
                    (- pillerBase_h/2
                    +pillerBase_popup)),
        dimension=(pillerBase_size,
                pillerBase_size,
                pillerBase_h),
        parent=floorRootObj,
    )
    # 柱顶石材质：石头
    mat.paint(pillerBottom_basemesh,con.M_PILLER_BASE)
    # 添加bevel
    utils.addModifierBevel(pillerBottom_basemesh, 
                           width=con.BEVEL_HIGH, 
                           type='WIDTH',)
    
    # 3、根据地盘数据，循环排布每根柱子
    net_x,net_y = getFloorDate(buildingObj)
    x_rooms = bData.x_rooms   # 面阔几间
    y_rooms = bData.y_rooms   # 进深几间
    pillerList = []
    for y in range(y_rooms + 1):
        for x in range(x_rooms + 1):
            # 统一命名为“柱.x/y”，以免更换不同柱形时，减柱设置失效
            pillerID = str(x) + '/' + str(y)

            # 1、减柱逻辑 ----------------------------
            # 包括：用户在单体减柱中手工减柱，或在月台/重檐场景中自动减柱
            useEmptyPiller = False
            # 1.1、pillernet为hide，月台场景，全部自动减柱
            if bData.piller_net == con.ACA_PILLER_HIDE:
                useEmptyPiller = True
            # 1.2、pillernet为''时，柱网全部重建
            elif bData.piller_net == '':
                # 重檐下檐，內檐金柱全部自动减柱
                if (bData.use_double_eave and 
                    bData.combo_type == con.COMBO_MAIN):
                    if not (x in (0,x_rooms) 
                            or y in (0,y_rooms)):
                        useEmptyPiller = True
            # 1.3、pillernet不为空，按照pillernet判断减柱
            else:
                # 廊间举架，不做减柱
                if not bData.use_hallway:
                    # 柱ID是否在piller_net，就减柱
                    if pillerID not in bData.piller_net:
                        useEmptyPiller = True
            
            # 2、减柱的，显示empty标识 -------------------
            # 空柱位上用Empty标识，以便添加踏跺等操作
            if useEmptyPiller:
                pillerObj = utils.addEmpty(
                    name = '柱定位点.' + pillerID,
                    type='CONE',
                    radius=pd,
                    location = (net_x[x],net_y[y],0),
                    parent = floorRootObj,
                    rotation=(math.radians(90),0,0)
                )
                pillerObj.ACA_data['aca_obj'] = True
                pillerObj.ACA_data['aca_type'] = con.ACA_TYPE_PILLER
                pillerObj.ACA_data['pillerID'] = pillerID
                # 不再继续做柱实体
                continue    # 结束本次循环

            # 3、非减柱的，显示正常柱体 ----------------
            # 复制柱子，仅instance，包含modifier
            pillerObj = utils.copySimplyObject(
                sourceObj = piller_source,
                name = '柱子.'+pillerID,
                location=(net_x[x],net_y[y],0),
                parentObj = floorRootObj,
                singleUser=True # 内外柱不等高，为避免打架，全部
            )
            pillerObj.ACA_data['aca_obj'] = True
            pillerObj.ACA_data['aca_type'] = con.ACA_TYPE_PILLER
            pillerObj.ACA_data['pillerID'] = pillerID
            # 250212 金柱的升高处理（包含廊间举架）
            pillerHeight = getPillerHeight(
                    buildingObj,pillerID)
            pillerObj.dimensions = (
                pd,pd,pillerHeight
            )
            utils.applyTransform(pillerObj,use_scale=True,autoUpdate=False)
            # 做柱头彩画
            mat.paint(pillerObj,con.M_PILLER_HEAD,
                        override=True)
            pillerList.append(pillerObj)

            # 250817 不做台基时，也不做柱础和柱顶石
            if bData.is_showPlatform:
                # 复制柱础
                pillerbase_basemesh:bpy.types.Object = utils.copySimplyObject(
                    sourceObj=aData.pillerbase_source,
                    location=(0,0,0),
                    parentObj=pillerObj
                )
                pillerbase_basemesh.scale = (
                            pd/piller_source.dimensions.x,
                            pd/piller_source.dimensions.y,
                            pd/piller_source.dimensions.x,
                        )
                # 柱础材质：石头
                mat.paint(pillerbase_basemesh,con.M_PILLER_BASE)
                
                # 复制柱顶石
                pillerBottomObj = utils.copySimplyObject(
                    sourceObj=pillerBottom_basemesh,
                    parentObj=pillerObj
                )

    # 移除柱子和柱顶石模板    
    utils.delObject(pillerBottom_basemesh)
    utils.delObject(piller_source)

    # 4、后处理 ---------------------
    # 月台隐藏柱网时，无需后处理
    if bData.piller_net == con.ACA_PILLER_HIDE:
        return
    
    # 4.1、重新生成柱网配置
    bData.piller_net = ''
    floorChildren:List[bpy.types.Object] = floorRootObj.children
    for piller in floorChildren:
        if piller.type == 'EMPTY': continue
        if 'aca_type' in piller.ACA_data:
            if piller.ACA_data['aca_type']==con.ACA_TYPE_PILLER:
                pillerID = piller.ACA_data['pillerID']
                bData.piller_net += pillerID + ','


    # 4.2、重新生成额枋、穿插枋、金枋
    if bData.piller_net != '':
        # 添加柱间的额枋
        # 函数内部会自动生成默认额枋
        utils.outputMsg("Building Fangs...")
        __buildFang(buildingObj)

        # 250227 始终调用穿插枋处理
        # 函数内部会判断是否满足做穿插枋的条件
        __buildCCFang(buildingObj)

        # 250302 添加金柱间的金枋
        __buildJinFang(buildingObj)

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
        if piller.type == 'EMPTY': continue
        if 'aca_type' in piller.ACA_data:
            if piller.ACA_data['aca_type']==con.ACA_TYPE_PILLER:
                pillerID = piller.ACA_data['pillerID']
                bData.piller_net += pillerID + ','

    # 刷新柱网
    buildPillers(buildingObj)

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
def resetFloor(buildingObj:bpy.types.Object,
               comboObj:bpy.types.Object = None,
               ):
    # 清空柱网、额枋、装修的设置
    bData:acaData = buildingObj.ACA_data
    if bData.piller_net != con.ACA_PILLER_HIDE:
        bData.piller_net = ''
    bData.fang_net = ''
    bData.wall_net = ''
    
    # 250109 踏跺数据未重置，导致开间变化后，错误的踏跺无法生成而崩溃
    bData.step_net = ''

    # 250306 重新考虑后，觉得似乎不必禁止
    # # 250215 重设地盘后，默认不做屋顶
    # bData.is_showDougong = False
    # bData.is_showBeam = False
    # bData.is_showRafter = False
    # bData.is_showTiles = False

    # 调用
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if isRebuild:
        result = buildFloor(buildingObj,
                            comboObj=comboObj)
    else:
        result = {'CANCELLED'}
    return result

# 执行营造整体过程
# 输入buildingObj，自带设计参数集，且做为其他构件绑定的父节点
def buildFloor(buildingObj:bpy.types.Object,
               templateName = None,
               reloadAssets = False,
               comboObj:bpy.types.Object = None,
               ):
    # 定位到collection，如果没有则新建
    utils.setCollection(
        name = con.COLL_NAME_ROOT,
        isRoot=True,
        colorTag=2,
        )

    # 新建还是刷新？
    if buildingObj == None:
        utils.outputMsg("创建新建筑...")
        if templateName == None:
            # 获取panel上选择的模板
            from . import data
            scnData : data.ACA_data_scene = bpy.context.scene.ACA_data
            templateList = scnData.templateItem
            templateIndex = scnData.templateIndex
            templateName = templateList[templateIndex].name
        # 添加建筑根节点，同时载入模板
        buildingObj = __addBuildingRoot(
            templateName = templateName,
            comboObj = comboObj
            )
        # 在buldingObj上绑定模板bData和资产库aData
        template.loadTemplate(buildingObj)
    else:
        # 聚焦对象集合
        # 避免因为手工排除该集合导致后续构建掉落在集合外
        buildingColl = buildingObj.users_collection[0]
        utils.focusCollection(buildingColl.name)
        utils.outputMsg("更新建筑...")
        # 简单粗暴的全部删除
        utils.deleteHierarchy(buildingObj)
        if reloadAssets:
            # 刷新buildingObj中绑定的资产库aData
            template.loadAssetByBuilding(buildingObj)  

    # 载入数据
    bData:acaData = buildingObj.ACA_data
    # 组合建筑根据模板位移和旋转
    if comboObj != None:
        if tuple(bData.root_location) != (0.0,0.0,0.0):
            buildingObj.location = bData.root_location

        if tuple(bData.root_rotation) != (0.0,0.0,0.0):
            buildingObj.rotation_euler = bData.root_rotation

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
    buildRoof.buildRoof(buildingObj)

    # 应用所有子对象的修改器
    utils.applyCollModifier(buildingObj)

    # 重新聚焦回根节点
    utils.focusObj(buildingObj)

    return {'FINISHED'}

# 获取重檐柱网
# 在做穿插枋时，需要连接下檐柱网和上檐柱网
def __getComboPillerNet(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    # 下檐柱网
    pillerNet = bData.piller_net
    
    # 验证是否为重檐
    if not bData.use_double_eave:
        utils.outputMsg("穿插枋拼接上檐柱网失败，该建筑没有做重檐")
        return pillerNet
    
    # 查找上檐
    doubleEaveObj = utils.getComboChild(
        buildingObj,con.COMBO_DOUBLE_EAVE)
    if doubleEaveObj is None:
        utils.outputMsg("穿插枋拼接上檐柱网失败，未找到上檐柱网")
        return pillerNet

    # 处理上檐柱网
    dData:acaData = doubleEaveObj.ACA_data
    innerPillerNet = dData.piller_net
    # 所有柱编号按照一廊间做偏移
    innerPillerOffset = ''
    pillerList = innerPillerNet.rstrip(',').split(',')
    for pillerID in pillerList:
        px,py = pillerID.split('/')
        px = int(px) + 1
        py = int(py) + 1
        # 重新拼接新柱网
        innerPillerOffset += f"{px}/{py},"

    # 最终的拼接柱网
    pillerNet += innerPillerOffset

    return pillerNet