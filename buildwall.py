# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   墙体布局树状结构的营造
import bpy
import math
from mathutils import Vector
from functools import partial
from typing import List

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import utils
from . import buildDoor
from . import buildFloor

# 创建新地盘对象（empty）
def __addWallrootNode(buildingObj:bpy.types.Object):
    # 创建新地盘对象（empty）
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    wallrootObj = bpy.context.object
    wallrootObj.name = "墙体布局"
    wallrootObj.parent = buildingObj  # 挂接在对应建筑节点下
    wallrootObj.ACA_data['aca_obj'] = True
    wallrootObj.ACA_data['aca_type'] = con.ACA_TYPE_WALL_ROOT
    #与台基顶面对齐
    wall_z = buildingObj.ACA_data.platform_height
    wallrootObj.location = (0,0,wall_z)
    return wallrootObj

# 计算墙体数据
# 用于根据有廊、无廊、前廊、后廊、斗底槽等自动布局
# 已暂时停用
def __getWallData(buildingObj:bpy.types.Object,net_x,net_y):
    # 根据墙体布局类型（无廊、周围廊、前廊等），分别处理
    bData = buildingObj.ACA_data
    wallLayout = int(bData.wall_layout)
    row=[]
    col=[]
    rowRange=()
    colRange=()
    if wallLayout == 1: # 默认无廊
        row = [0,len(net_y)-1]   # 左右两列
        rowRange = range(0,len(net_y)-1)
        col = [0,len(net_x)-1]   # 前后两排
        colRange = range(0,len(net_x)-1)
    if wallLayout == 2: # 周围廊
        row = [1,len(net_y)-2]   # 左右两列
        rowRange = range(1,len(net_y)-2)
        col = [1,len(net_x)-2]   # 前后两排
        colRange = range(1,len(net_x)-2)
    if wallLayout == 3: # 前廊
        row = [1,len(net_y)-1]   # 左右两列
        rowRange = range(1,len(net_y)-1)
        col = [0,len(net_x)-1]   # 前后两排
        colRange = range(0,len(net_x)-1)
    if wallLayout == 4: # 斗底槽
        row = [0,1,len(net_y)-2,len(net_y)-1]   # 左右两列
        rowRange = range(0,len(net_y)-1)
        col = [0,1,len(net_x)-2,len(net_x)-1]   # 前后两排
        colRange = range(0,len(net_x)-1)
    return row,col,rowRange,colRange

# 构造wallproxy
# 根据wallID，实现wallproxy的大小、位置、属性的构造
def buildWallproxy(buildingObj:bpy.types.Object,
                   wallID:str):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    # 墙体根节点
    wallrootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_WALL_ROOT)
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('墙体',parentColl=buildingColl)
    
    # 获取柱网数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)

    # 定义wallproxy尺寸
    wall_deepth = 1 # 墙线框默认尺寸，后续被隐藏显示，所以没有实际影响
    wall_height = bData.piller_height \
        - con.EFANG_LARGE_H * pd # 除去大额枋高度
    if bData.use_smallfang:
        wall_height += \
        - con.BOARD_YOUE_H * pd \
        - con.EFANG_SMALL_H * pd # 除去小额枋、垫板高度

    # 解析wallID，例如”wall#3/0#3/3“，或”window#0/0#0/1“，或”door#0/1#0/2“
    setting = wallID.split('#')
    
    # 样式为墙、门、窗
    style = setting[0]

    # 以柱编号定位
    # 起始柱子
    pFrom = setting[1].split('/')
    pFrom_x = int(pFrom[0])
    pFrom_y = int(pFrom[1])
    pStart = Vector((net_x[pFrom_x],net_y[pFrom_y],wall_height/2))
    # 结束柱子
    pTo = setting[2].split('/')
    pTo_x = int(pTo[0])
    pTo_y = int(pTo[1])
    pEnd = Vector((net_x[pTo_x],net_y[pTo_y],wall_height/2))

    # 矫正墙体的内外
    # 因为pStart,pEnd用户选择时没有顺序，只能根据坐标强行处理
    if (pStart.x == pEnd.x and pStart.x>0) \
        or (pStart.y == pEnd.y and pStart.y<0):
        pTemp = pStart
        pStart = pEnd
        pEnd = pTemp


    # 生成wallproxy
    wallproxy = utils.addCubeBy2Points(
                start_point = pStart,
                end_point = pEnd,
                deepth = wall_deepth,
                height = wall_height,
                name = "墙体proxy",
                root_obj = wallrootObj,
                origin_at_bottom = True
            )
    
    # 填充wallproxy的数据
    wData:acaData = wallproxy.ACA_data
    wData['aca_obj'] = True
    wData['aca_type'] = con.ACA_TYPE_WALL
    wData['wallID'] = wallID
    if style == con.ACA_WALLTYPE_WALL:
        wData['wall_style'] = 1
    if style == con.ACA_WALLTYPE_DOOR:
        wData['wall_style'] = 2
        wData['use_KanWall'] = False
    if style == con.ACA_WALLTYPE_WINDOW:
        wData['wall_style'] = 3
        wData['use_KanWall'] = True
    wData['wall_source'] = bData.wall_source
    wData['door_height'] = bData.door_height
    wData['door_num'] = bData.door_num
    wData['gap_num'] = bData.gap_num
    wData['lingxin_source'] = bData.lingxin_source

    return wallproxy

# 个性化设置一个墙体
# 传入wallproxy
def buildSingleWall(wallproxy:bpy.types.Object):
    # 清空框线
    utils.deleteHierarchy(wallproxy)

    # 载入数据
    buildingObj = utils.getAcaParent(wallproxy,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    wData:acaData = wallproxy.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    
    if wData.wall_style == "1":   #槛墙
        if wData.wall_source != None:
            wallChildObj:bpy.types.Object = utils.copyObject(
                sourceObj=wData.wall_source,
                name='墙体',
                parentObj=wallproxy,
                singleUser=True)
            wallChildObj.dimensions = (wallproxy.dimensions.x,
                                    wallChildObj.dimensions.y,
                                    wallproxy.dimensions.z)
            utils.applyTransfrom(ob=wallChildObj,use_scale=True)
            utils.updateScene()
            wallChildObj.dimensions.z = wallproxy.dimensions.z
            wData : acaData = wallChildObj.ACA_data
            wData['aca_obj'] = True
            wData['aca_type'] = con.ACA_TYPE_WALL_CHILD

    if wData.wall_style in ("2","3"): # 2-隔扇，3-槛墙
        utils.focusObj(wallproxy)
        buildDoor.buildDoor(wallproxy)

    utils.hideObjFace(wallproxy)
    utils.outputMsg("Wallproxy: " + wallproxy.name)

    return

# 更新墙布局
# 墙体数量不变，仅更新墙体尺寸、样式等
# 可以保持用户的个性化设置不丢失
def updateWallLayout(buildingObj:bpy.types.Object):
    # 获取墙布局根节点，并清空
    wallrootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_WALL_ROOT)

    # 一、批量更新wallproxy尺寸
    # a、默认尺寸
    wall_deepth = 1 # 墙线框尺寸
    pillerObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_PILLER)
    wall_height = pillerObj.dimensions.z   
    # b、计算布局数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    row,col,rowRange,colRange = \
        __getWallData(buildingObj,net_x,net_y)  
    wallcounter = 0       
    # c、缩放横向墙体
    for r in row: 
        for c in colRange:
            pStart = Vector((net_x[c],net_y[r],0))
            pEnd = Vector((net_x[c+1],net_y[r],0))
            length = utils.getVectorDistance(pStart,pEnd)
            origin_point = (pStart+pEnd)/2
            wallobj = wallrootObj.children[wallcounter]
            wallobj.dimensions.x = length
            wallobj.location = origin_point
            utils.applyScale(wallobj)
            wallcounter += 1
    # d、缩放纵向墙体
    for c in col: 
        for r in rowRange:
            pStart = Vector((net_x[c],net_y[r],0))
            pEnd = Vector((net_x[c],net_y[r+1],0))
            length = utils.getVectorDistance(pStart,pEnd)
            origin_point = (pStart+pEnd)/2
            wallobj = wallrootObj.children[wallcounter]
            wallobj.dimensions.x = length
            wallobj.location = origin_point
            utils.applyScale(wallobj)
            wallcounter += 1

    # 二、检查wallproxy属性是否未初始化
    # 比如，新建建筑时，可能wallproxy属性仍为空
    # 批量更新wallproxy属性，以全局参数填入
    bData :acaData = buildingObj.ACA_data
    for wallproxy in wallrootObj.children:
        # 填充wallproxy的数据
        wData :acaData = wallproxy.ACA_data
        if wData.wall_style == '':
            # enumProperty赋值很奇怪
            if bData.wall_style != "":
                wData['wall_style'] = int(bData.wall_style) 
            wData['wall_source'] = bData.wall_source
            wData['door_height'] = bData.door_height
            wData['door_num'] = bData.door_num
            wData['gap_num'] = bData.gap_num
            wData['use_KanWall'] = bData.use_KanWall
            wData['lingxin_source'] = bData.lingxin_source

    # 三、批量绑定墙体构件
    for wallproxy in wallrootObj.children:
        buildSingleWall(wallproxy)
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)

# 重设墙布局
# 因为墙体数量产生了变化，重新生成所有墙体
# 用户的个性化设置丢失
# 按照默认设计参数生成
# todo：后续可以按照模版中的设置生成（包含预设的个性化设置）
def resetWallLayoutOld(buildingObj:bpy.types.Object):
    # 查找墙体布局节点
    wallrootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_WALL_ROOT)
    # 如果找不到“墙体布局”根节点，重新创建
    if wallrootObj == None:        
        wallrootObj = __addWallrootNode(buildingObj)
    else:
        # 清空根节点
        utils.deleteHierarchy(wallrootObj)

    # 一、批量生成wallproxy
    # a、默认尺寸
    wall_deepth = 1 # 墙线框尺寸
    pillerObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_PILLER)
    wall_height = pillerObj.dimensions.z   
    # b、计算布局数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    row,col,rowRange,colRange = \
        __getWallData(buildingObj,net_x,net_y)         
    # c、生成横向墙体
    for r in row: 
        for c in colRange:
            pStart = Vector((net_x[c],net_y[r],wall_height/2))
            pEnd = Vector((net_x[c+1],net_y[r],wall_height/2))
            wallObj = utils.addCubeBy2Points(
                        start_point = pStart,
                        end_point = pEnd,
                        deepth = wall_deepth,
                        height = wall_height,
                        name = "墙体proxy",
                        root_obj = wallrootObj,
                        origin_at_bottom = True
                    )
            if r < len(net_y)/2:
                wallObj.rotation_euler.z +=  math.radians(-180)
    # d、生成纵向墙体
    for c in col: 
        for r in rowRange:
            pStart = Vector((net_x[c],net_y[r],wall_height/2))
            pEnd = Vector((net_x[c],net_y[r+1],wall_height/2))
            wallObj = utils.addCubeBy2Points(
                        start_point = pStart,
                        end_point = pEnd,
                        deepth = wall_deepth,
                        height = wall_height,
                        name = "墙体proxy",
                        root_obj = wallrootObj,
                        origin_at_bottom = True
                    )
            if c >= len(net_x)/2:
                wallObj.rotation_euler.z +=  math.radians(180)

    # 二、批量设置wallproxy属性，以全局参数填入
    bData :acaData = buildingObj.ACA_data
    for wallproxy in wallrootObj.children:
        wallproxy.display_type = 'WIRE' # 仅显示线框
        wallproxy.hide_render = True    # 不渲染输出
        # 填充wallproxy的数据
        wData : acaData = wallproxy.ACA_data
        wData['aca_obj'] = True
        wData['aca_type'] = con.ACA_TYPE_WALL
        if bData.wall_style != '':
            # enumProperty赋值很奇怪
            wData['wall_style'] = int(bData.wall_style) 
        wData['wall_source'] = bData.wall_source
        wData['door_height'] = bData.door_height
        wData['door_num'] = bData.door_num
        wData['gap_num'] = bData.gap_num
        wData['use_KanWall'] = bData.use_KanWall
        wData['lingxin_source'] = bData.lingxin_source

    # 三、批量绑定墙体构件
    for wallproxy in wallrootObj.children:
        buildSingleWall(wallproxy)
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)

# 手工添加隔断
def addWall(buildingObj:bpy.types.Object,
              pillers:List[bpy.types.Object],
              wallType:str):
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

    # 构造wallID
    pFrom = None
    pTo= None
    wall_net = bData.wall_net
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
                    wallID = pFrom.ACA_data['pillerID'] \
                        + '#' + pTo.ACA_data['pillerID'] 
                    wallID_alt = pTo.ACA_data['pillerID'] \
                         + '#' + pFrom.ACA_data['pillerID'] 
                    # 验证墙体在布局中是否已经存在
                    if wallID in wall_net or wallID_alt in wall_net:
                        print(wallID + " is in wall_net:" + wall_net)
                        continue
                    wallStr = wallType+'#'+wallID
                    
                    print(wallStr)
                    # 生成墙体
                    wallproxy = buildWallproxy(buildingObj,wallStr)
                    buildSingleWall(wallproxy)

                    # 将墙体加入整体布局中
                    bData.wall_net += wallStr + ','
                    print(bData.wall_net)                    

                    # 将柱子交换，为下一次循环做准备
                    pFrom = piller
    return

# 删除隔断
def delWall(object:bpy.types.Object):
    # 找到wallproxy
    objData:acaData = object.ACA_data
    if objData['aca_type'] == con.ACA_TYPE_WALL_CHILD:
        wallproxy = utils.getAcaParent(
            object,con.ACA_TYPE_WALL)
    else:
        wallproxy = object
    wallRootObj = utils.getAcaParent(
        object,con.ACA_TYPE_WALL_ROOT)
    buildingObj = utils.getAcaParent(
        object,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    
    # 删除实例对象
    utils.deleteHierarchy(wallproxy,del_parent=True)
    # 重新生成wall_net
    bData.wall_net = ''
    for wallproxy in wallRootObj.children:
        wallStr = wallproxy.ACA_data['wallID']
        bData.wall_net += wallStr + ','

    utils.focusObj(wallRootObj)

    return

# 重设墙布局
# 因为墙体数量产生了变化，重新生成所有墙体
# 用户的个性化设置丢失
# 按照默认设计参数生成
# todo：后续可以按照模版中的设置生成（包含预设的个性化设置）
def resetWallLayout(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    
    # 查找墙体布局节点
    wallrootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_WALL_ROOT)
    # 如果找不到“墙体布局”根节点，重新创建
    if wallrootObj == None:        
        wallrootObj = __addWallrootNode(buildingObj)
    else:
        # 清空根节点
        utils.deleteHierarchy(wallrootObj)

    # 一、批量生成wallproxy
    # a、默认尺寸
    wall_deepth = 1 # 墙线框尺寸
    wall_height = bData.piller_height \
        - con.EFANG_LARGE_H * pd 
    if bData.use_smallfang:
        wall_height += \
        - con.BOARD_YOUE_H * pd \
        - con.EFANG_SMALL_H * pd

    # b、计算布局数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    # 解析模版输入的墙体设置，格式如下
    # "wall#3/0#3/3,wall#0/0#3/0,wall#0/3#3/3,window#0/0#0/1,window#0/2#0/3,door#0/1#0/2,"
    wallSetting = bData.wall_net
    wallList = wallSetting.split(',')
    for wallID in wallList:
        if wallID == '': continue
        wallproxy = buildWallproxy(
            buildingObj,wallID)
        buildSingleWall(wallproxy)
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)

    return

# 批量生成整个墙体布局
# 载入建筑根节点buildingObj（及全局设计参数）
# 自动判断是否已有墙体布局根节点，如果没有就新建
# 自动判断墙体数量是否变化，尽可能保留原有个性化设置
def buildWallLayout(buildingObj:bpy.types.Object) :
    # 校验输入对象
    bData : acaData = buildingObj.ACA_data
    if bData.aca_type != con.ACA_TYPE_BUILDING:
        utils.showMessageBox("错误，输入的不是建筑根节点")
        return

    # 查找墙体布局节点
    wallrootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_WALL_ROOT)
    # 如果找不到“墙体布局”根节点，重新创建
    if wallrootObj == None:        
        wallrootObj = __addWallrootNode(buildingObj)

    # 判断墙体数量是否变化
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    row,col,rowRange,colRange = __getWallData(buildingObj,net_x,net_y)
    # 原有墙体数量
    wallcount_old = len(wallrootObj.children)
    # 现需墙体数量
    wallcount_new = len(row)*len(colRange) + len(col)*len(rowRange)

    if wallcount_new == wallcount_old :
        # 墙数量没变，仅改变墙的尺寸、外观
        # 保留墙的个性化设置
        funproxy = partial(updateWallLayout,buildingObj=buildingObj)
        utils.fastRun(funproxy)
    else:
        # 墙数量变了，丢弃所有墙体数据，重建
        # 无法保留墙体的个性化设置
        funproxy = partial(resetWallLayout,buildingObj=buildingObj)
        utils.fastRun(funproxy)