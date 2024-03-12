# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   墙体布局树状结构的营造
import bpy
import math
from mathutils import Vector
from functools import partial

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import utils
from . import buildDoor

def __getFloorDate(buildingObj:bpy.types.Object):
    # 载入设计参数
    bData : acaData = buildingObj.ACA_data

    # 构造柱网X坐标序列，罗列了1，3，5，7，9，11间的情况，未能抽象成通用公式
    x_rooms = bData.x_rooms   # 面阔几间
    y_rooms = bData.y_rooms   # 进深几间

    net_x = []  # 重新计算
    if x_rooms >=1:     # 明间
        offset = bData.x_1 / 2
        net_x.append(offset)
        net_x.insert(0, -offset)
    if x_rooms >=3:     # 次间
        offset = bData.x_1 / 2 + bData.x_2
        net_x.append(offset)
        net_x.insert(0, -offset)  
    if x_rooms >=5:     # 梢间
        offset = bData.x_1 / 2 + bData.x_2 \
                + bData.x_3
        net_x.append(offset)
        net_x.insert(0, -offset)  
    if x_rooms >=7:     # 尽间
        offset = bData.x_1 / 2 + bData.x_2 \
            + bData.x_3 + bData.x_4
        net_x.append(offset)
        net_x.insert(0, -offset)  
    if x_rooms >=9:     #更多梢间
        offset = bData.x_1 / 2 + bData.x_2 \
            + bData.x_3 * 2
        net_x[-1] = offset
        net_x[0]= -offset  
        offset = bData.x_1 / 2 + bData.x_2 \
            + bData.x_3 *2 + bData.x_4
        net_x.append(offset)
        net_x.insert(0, -offset) 
    if x_rooms >=11:     #更多梢间
        offset = bData.x_1 / 2 + bData.x_2 \
            + bData.x_3 * 3
        net_x[-1] = offset
        net_x[0]= -offset  
        offset = bData.x_1 / 2 + bData.x_2 \
            + bData.x_3 *3 + bData.x_4
        net_x.append(offset)
        net_x.insert(0, -offset) 

    # 构造柱网Y坐标序列，罗列了1-5间的情况，未能抽象成通用公式
    net_y=[]    # 重新计算
    if y_rooms%2 == 1: # 奇数间
        if y_rooms >= 1:     # 明间
            offset = bData.y_1 / 2
            net_y.append(offset)
            net_y.insert(0, -offset)
        if y_rooms >= 3:     # 次间
            offset = bData.y_1 / 2 + bData.y_2
            net_y.append(offset)
            net_y.insert(0, -offset)  
        if y_rooms >= 5:     # 梢间
            offset = bData.y_1 / 2 + bData.y_2 \
                    + bData.y_3
            net_y.append(offset)
            net_y.insert(0, -offset) 
    else:   #偶数间
        if y_rooms >= 2:
            net_y.append(0)
            offset = bData.y_1
            net_y.append(offset)
            net_y.insert(0,-offset)
        if y_rooms >= 4:
            offset = bData.y_1 + bData.y_2
            net_y.append(offset)
            net_y.insert(0,-offset)
    
    # 保存通面阔计算结果，以便其他函数中复用
    bData["x_total"] = net_x[-1]-net_x[0]
    # 保存通进深计算结果，以便其他函数中复用
    bData["y_total"] = net_y[-1]-net_y[0]

    return net_x,net_y

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
    net_x,net_y = __getFloorDate(buildingObj)
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
            utils.ApplyScale(wallobj)
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
            utils.ApplyScale(wallobj)
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
            wData['is_with_wall'] = bData.is_with_wall
            wData['lingxin_source'] = bData.lingxin_source

    # 三、批量绑定墙体构件
    for wallproxy in wallrootObj.children:
        buildDoor.buildSingleWall(wallproxy)
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)

# 重设墙布局
# 因为墙体数量产生了变化，重新生成所有墙体
# 用户的个性化设置丢失
# 按照默认设计参数生成
# todo：后续可以按照模版中的设置生成（包含预设的个性化设置）
def resetWallLayout(buildingObj:bpy.types.Object):
    # 查找墙体布局节点
    wallrootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_WALL_ROOT)
    # 如果找不到“墙体布局”根节点，重新创建
    if wallrootObj == None:        
        wallrootObj = __addWallrootNode(buildingObj)
    else:
        # 清空根节点
        utils.delete_hierarchy(wallrootObj)

    # 一、批量生成wallproxy
    # a、默认尺寸
    wall_deepth = 1 # 墙线框尺寸
    pillerObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_PILLER)
    wall_height = pillerObj.dimensions.z   
    # b、计算布局数据
    net_x,net_y = __getFloorDate(buildingObj)
    row,col,rowRange,colRange = \
        __getWallData(buildingObj,net_x,net_y)         
    # c、生成横向墙体
    for r in row: 
        for c in colRange:
            pStart = Vector((net_x[c],net_y[r],0))
            pEnd = Vector((net_x[c+1],net_y[r],0))
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
            pStart = Vector((net_x[c],net_y[r],0))
            pEnd = Vector((net_x[c],net_y[r+1],0))
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
        wData['is_with_wall'] = bData.is_with_wall
        wData['lingxin_source'] = bData.lingxin_source

    utils.outputMsg("wall layout reset.")

    # 三、批量绑定墙体构件
    for wallproxy in wallrootObj.children:
        buildDoor.buildSingleWall(wallproxy)
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)

# 批量生成整个墙体布局
# 载入建筑根节点buildingObj（及全局设计参数）
# 自动判断是否已有墙体布局根节点，如果没有就新建
# 自动判断墙体数量是否变化，尽可能保留原有个性化设置
def buildWallLayout(buildingObj:bpy.types.Object) :
    # 校验输入对象
    bData : acaData = buildingObj.ACA_data
    if bData.aca_type != con.ACA_TYPE_BUILDING:
        utils.ShowMessageBox("错误，输入的不是建筑根节点")
        return

    # 查找墙体布局节点
    wallrootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_WALL_ROOT)
    # 如果找不到“墙体布局”根节点，重新创建
    if wallrootObj == None:        
        wallrootObj = __addWallrootNode(buildingObj)

    # 判断墙体数量是否变化
    net_x,net_y = __getFloorDate(buildingObj)
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



