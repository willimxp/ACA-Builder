# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   装修布局树状结构的营造
import bpy
import bmesh
from mathutils import Vector
from typing import List

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from .data import ACA_data_template as tmpData
from . import utils
from . import buildDoor
from . import buildFloor
from . import texture as mat

# 创建新地盘对象（empty）
def __addWallrootNode(buildingObj:bpy.types.Object):
    #与台基顶面对齐
    wall_z = buildingObj.ACA_data.platform_height
    # 创建新地盘对象（empty）
    wallrootObj = utils.addEmpty(
        name = "装修层",
        parent = buildingObj,
        location = (0,0,wall_z),
    )
    wallrootObj.ACA_data['aca_obj'] = True
    wallrootObj.ACA_data['aca_type'] = con.ACA_TYPE_WALL_ROOT
    return wallrootObj

# 计算墙体数据
# 用于根据有廊、无廊、前廊、后廊、斗底槽等自动布局
# 已暂时停用
def __getWallData(buildingObj:bpy.types.Object,net_x,net_y):
    # 根据装修布局类型（无廊、周围廊、前廊等），分别处理
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
def __tempWallproxy(buildingObj:bpy.types.Object,
                   wallID:str):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    # 墙体根节点
    wallrootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_WALL_ROOT)
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('装修',parentColl=buildingColl)
    
    # 获取柱网数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    # 解析wallID，例如”wall#3/0#3/3“，或”window#0/0#0/1“，或”door#0/1#0/2“
    setting = wallID.split('#')

    # 对象命名
    wallType = setting[0]
    if wallType == con.ACA_WALLTYPE_WALL:
        wallName = '墙体'
    elif wallType == con.ACA_WALLTYPE_WINDOW:
        wallName = '槛窗'
    elif wallType == con.ACA_WALLTYPE_GESHAN:
        wallName = '隔扇'
    elif wallType == con.ACA_WALLTYPE_BARWINDOW:
        wallName = '直棂窗'
    elif wallType == con.ACA_WALLTYPE_MAINDOOR:
        wallName = '板门'
    elif wallType == con.ACA_WALLTYPE_FLIPWINDOW:
        wallName = '支摘窗'
    else:
        utils.outputMsg(f"无法生成wallproxy，walltype：{wallType}")
        return
    wallName = "%s.%s#%s" % (wallName,setting[1],setting[2])

    # 获取实际柱高   
    pillerFromHeight = buildFloor.getPillerHeight(
        buildingObj,setting[1])
    pillerToHeight = buildFloor.getPillerHeight(
        buildingObj,setting[2])
    # 装修高度取较低的柱高
    if pillerFromHeight > pillerToHeight:
        pillerHeight = pillerToHeight
    else:
        pillerHeight = pillerFromHeight
    # 装修在额枋下
    wall_height = pillerHeight \
        - con.EFANG_LARGE_H*dk # 除去大额枋高度
    if bData.use_smallfang:
        wall_height += \
        - con.BOARD_YOUE_H*dk \
        - con.EFANG_SMALL_H*dk # 除去小额枋、垫板高度
        
    # 定义wallproxy尺寸
    wall_depth = 1 # 墙线框默认尺寸，后续被隐藏显示，所以没有实际影响
    # 以柱编号定位
    # 起始柱子
    pFrom = setting[1].split('/')
    pFrom_x = int(pFrom[0])
    pFrom_y = int(pFrom[1])
    # 结束柱子
    pTo = setting[2].split('/')
    pTo_x = int(pTo[0])
    pTo_y = int(pTo[1])
    
    # 250226 如果是廊间装修，槛框做到穿插枋上皮
    # 此时上槛与抱头梁重叠
    # 与是否做廊间举架无关
    isLangjian = False
    # 横向廊间，如，0/1#1/1
    if bData.y_rooms>3:
        if (pFrom_y == pTo_y 
            and pFrom_x+pTo_x in (1,bData.x_rooms*2-1)):
            isLangjian = True
    # 纵向廊间
    if bData.x_rooms >3:
        if (pFrom_x == pTo_x 
            and pFrom_y+pTo_y in (1,bData.y_rooms*2-1)):
            isLangjian = True
    if isLangjian:
        # 穿插枋下皮与由额垫板下皮持平
        # (简化处理，上槛中线对齐大额枋底皮)
        # 上槛和穿插枋高度可能不同，存在误差
        wall_height = (pillerHeight 
                       - con.EFANG_LARGE_H*dk
                       + con.KAN_UP_HEIGHT*pd/2)

    pStart = Vector((net_x[pFrom_x],net_y[pFrom_y],wall_height/2))
    pEnd = Vector((net_x[pTo_x],net_y[pTo_y],wall_height/2))
    # 计算墙体的方向，以建筑中心点，逆时针排布
    # 参考https://math.stackexchange.com/questions/285346/why-does-cross-product-tell-us-about-clockwise-or-anti-clockwise-rotation#:~:text=We%20can%20tell%20which%20direction,are%20parallel%20to%20each%20other.
    zAxis = Vector((0,0,1))
    vFrom = Vector((net_x[pFrom_x],net_y[pFrom_y],0))
    vTo = Vector((net_x[pTo_x],net_y[pTo_y],0))
    dirValue = vFrom.cross(vTo).dot(zAxis)
    if dirValue > 0:
        # 交换起始柱子
        pTemp = pStart
        pStart = pEnd
        pEnd = pTemp

    # 生成wallproxy
    wallproxy = utils.addCubeBy2Points(
                start_point = pStart,
                end_point = pEnd,
                depth = wall_depth,
                height = wall_height,
                name = wallName,
                root_obj = wallrootObj,
                origin_at_bottom = True
            )
    return wallproxy

# 绘制墙体
def __drawWall(wallProxy:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(wallProxy,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    (wallLength,wallDeepth,wallHeight) = wallProxy.dimensions
    # 覆盖墙体厚度
    wallDeepth = con.WALL_DEPTH * bData.piller_diameter
    # 退花碱厚度
    bodyShrink = con.WALL_SHRINK

    wallParts = []

    

    # 1、创建下碱对象
    # 下碱一般取墙体高度的1/3
    height = wallHeight * con.WALL_BOTTOM_RATE
    # 但最高不超过1.5m
    if height > con.WALL_BOTTOM_LIMIT:
        height = con.WALL_BOTTOM_LIMIT
    heightOffset = 0.02
    bottomObj = utils.drawHexagon(
        name='下碱',
        dimensions=Vector((wallLength,
               wallDeepth,
               height)),
        location=Vector((0,0,height/2-heightOffset)),
        parent=wallProxy,
    )
    # 赋材质
    mat.paint(bottomObj,con.M_WALL_BOTTOM)
    wallParts.append(bottomObj)

    # 2、创建上身对象
    extrudeHeight = wallHeight/10
    bodyObj = utils.drawHexagon(
        name='墙体',
        dimensions=Vector((wallLength-bodyShrink*2,
               wallDeepth-bodyShrink*2,
               wallHeight-extrudeHeight)),
        location=Vector((0,0,wallHeight/2-extrudeHeight/2)),
        parent=wallProxy,
    )
    
    # 2.1 上身顶部做出签尖造型，刘大可p99
    bm = bmesh.new()
    bm.from_mesh(bodyObj.data)
    # 先向上拉伸拉伸
    bm.faces.ensure_lookup_table()
    faceTop = bm.faces[1]
    return_geo = bmesh.ops.extrude_discrete_faces(
        bm, faces=[faceTop])
    return_face = return_geo['faces'][0]
    for v in return_face.verts:
        # 向上拉伸
        v.co.z += extrudeHeight
        # Y向挤压
        v.co.y = v.co.y /2
    # 结束
    bm.to_mesh(bodyObj.data)
    bm.free() 

    # 赋材质
    mat.paint(bodyObj,con.M_WALL)
    wallParts.append(bodyObj)
    
    # 合并
    # wallObj = utils.joinObjects(wallParts,'墙体')
    modBool:bpy.types.BooleanModifier = \
            bodyObj.modifiers.new('合并','BOOLEAN')
    modBool.object = bottomObj
    modBool.solver = 'EXACT'
    modBool.operation = 'UNION'
    modBool.material_mode = 'TRANSFER'
    utils.applyAllModifer(bodyObj)
    utils.delObject(bottomObj)
    # 导角
    utils.addModifierBevel(bodyObj, width=con.BEVEL_HIGH)

    # 针对重檐，装修不一定做到柱头，用走马板填充
    if bData.wall_span != 0 :
        wallHeadBoard = utils.addCube(
                name = "走马板",
                location=(0,0,
                    (wallHeight/2 
                     + extrudeHeight/2
                     +bData.wall_span/2)
                ),
                dimension=(wallLength,
                           con.BOARD_YOUE_Y*dk,
                           bData.wall_span),
                parent=bodyObj,
            )
        mat.paint(wallHeadBoard,con.M_BOARD_WALLHEAD)
        wallParts.append(wallHeadBoard)

    return bodyObj

# 更新隔断
def updateWall(wallObj:bpy.types.Object):
    buildingObj = utils.getAcaParent(
        wallObj,con.ACA_TYPE_BUILDING)
    wallID = wallObj.ACA_data['wallID']
    # 生成新隔断，额外传入wallObj，带入原始设置
    __buildWall(buildingObj,wallID,wallObj)

    # 删除老隔断
    utils.deleteHierarchy(wallObj,del_parent=True)
    return

# 根据传入的wallID，生成对应的墙、板门、隔扇、槛窗等
# wallID格式为wall#3/0#3/3,window#0/0#0/1,door#0/1#0/2,
def __buildWall(buildingObj:bpy.types.Object,
                wallID='',
                origin_wallObj=None, # 待更新的墙体对象，可保留之前的设置
                ):
    # 0、准备 --------------------
    # 锁定操作目录
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('装修',parentColl=buildingColl)
    # 查找装修布局节点
    wallrootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_WALL_ROOT)
    # 如果找不到“装修布局”根节点，重新创建
    if wallrootObj == None:        
        wallrootObj = __addWallrootNode(buildingObj)

    # 解析wallID
    wallType = wallID.split('#')[0]
    
    # 1、生成wallproxy，做为墙体生成的数据参考
    wallproxy = __tempWallproxy(buildingObj,wallID)
    if wallproxy:
        # 将设置参数带入wallproxy，可进行个性化设置
        if origin_wallObj == None:
            # 新的wallproxy数据，继承buildingObj
            utils.copyAcaData(buildingObj,wallproxy)
        else:
            # 老的wallproxy数据，从输入的对象中获取
            utils.copyAcaData(origin_wallObj,wallproxy)
        wallproxy.ACA_data['aca_type'] = wallType
        wallproxy.ACA_data['wallID'] = wallID

    # 2、生成对应的墙、板门、隔扇、槛窗等接口
    # 营造槛墙
    if wallType == con.ACA_WALLTYPE_WALL:
        wallObj = __drawWall(wallproxy)
    # 营造板门、隔扇、槛窗、直棂窗
    elif wallType in (con.ACA_WALLTYPE_MAINDOOR,
                      con.ACA_WALLTYPE_GESHAN,
                      con.ACA_WALLTYPE_WINDOW,
                      con.ACA_WALLTYPE_BARWINDOW,
                      con.ACA_WALLTYPE_FLIPWINDOW,):
        wallObj = buildDoor.buildDoor(wallproxy)
    else:
        utils.outputMsg(f"无法生成墙体类型:{wallType}")
        return
    # 个性化设置参数的传递
    utils.copyAcaData(wallproxy,wallObj)
    # wallID不在propertyGroup中，需要单独传递
    wallObj.ACA_data['wallID'] = wallID
    for child in wallObj.children:
        utils.copyAcaData(wallproxy,child)
        child.ACA_data['wallID'] = wallID
        child.ACA_data['aca_type'] = con.ACA_TYPE_WALL_CHILD

    # 3、最后的清理
    # 挂入根节点
    utils.changeParent(wallObj,wallrootObj,resetOrigin=False)
    wallname = wallproxy.name
    # 删除wallproxy
    utils.delObject(wallproxy)
    wallObj.name = wallname
    utils.outputMsg("Building " + wallObj.name)
    utils.focusObj(wallObj)
    return wallObj

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
        utils.popMessageBox("请至少选择2根柱子")
        return

    # 构造wallID
    pFrom = None
    pTo= None
    wall_net = bData.wall_net
    wallObj = None
    # 逐一生成墙体
    # 如果用户选择了2根以上的柱子，将依次生成多个墙体
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
                    wallID = wallType+'#'+wallID
                    
                    # 生成墙体
                    wallObj = __buildWall(buildingObj,wallID)

                    # 将墙体加入整体布局中
                    bData.wall_net += wallID + ','            

                    # 将柱子交换，为下一次循环做准备
                    pFrom = piller

    

    # 聚焦在创建的门上
    if wallObj != None:
        # 250702 添加隔断后，刷新额枋，隐藏雀替
        buildFloor.__buildFang(buildingObj)
        utils.focusObj(wallObj)
    else:
        utils.outputMsg(f"无墙体需要生成")

    return {'FINISHED'}

# 删除墙体
def delWall(buildingObj:bpy.types.Object,
              walls:List[bpy.types.Object]):
    # 载入数据
    bData:acaData = buildingObj.ACA_data

    # 删除装修对象
    for wall in walls:
        # 校验用户选择的对象，可能误选了其他东西，直接忽略
        if 'aca_type' in wall.ACA_data:
            # 删除wall
            if wall.ACA_data['aca_type'] in (
                con.ACA_TYPE_WALL,          # 槛墙
                con.ACA_WALLTYPE_WINDOW,    # 槛窗
                con.ACA_WALLTYPE_GESHAN,    # 隔扇
                con.ACA_WALLTYPE_BARWINDOW, # 直棂窗
                con.ACA_WALLTYPE_MAINDOOR,  # 板门
            ):
                utils.deleteHierarchy(wall,del_parent=True)

    # 重新生成wall_net
    wallRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_WALL_ROOT)
    bData.wall_net = ''
    for wall in wallRootObj.children:
        if 'wallID' in wall.ACA_data:
            wallStr = wall.ACA_data['wallID']
            bData.wall_net += wallStr + ','

    # 250702 添加隔断后，刷新额枋，重建雀替
    buildFloor.__buildFang(buildingObj)

    utils.focusObj(buildingObj)

    return

# 重设墙布局
# 因为墙体数量产生了变化，重新生成所有墙体
# 用户的个性化设置丢失
# 按照默认设计参数生成
# todo：后续可以按照模板中的设置生成（包含预设的个性化设置）
def buildWallLayout(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK

    # 锁定操作目录
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('装修',parentColl=buildingColl)
    
    # 查找装修布局节点
    wallrootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_WALL_ROOT)
    # 如果找不到“装修布局”根节点，重新创建
    if wallrootObj == None:        
        wallrootObj = __addWallrootNode(buildingObj)
    else:
        # 清空根节点
        utils.deleteHierarchy(wallrootObj)

    # 一、批量生成wallproxy
    # 计算布局数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    # 解析模板输入的墙体设置，格式如下
    # "wall#3/0#3/3,wall#0/0#3/0,wall#0/3#3/3,window#0/0#0/1,window#0/2#0/3,door#0/1#0/2,"
    wallSetting = bData.wall_net
    wallList = wallSetting.split(',')
    for wallID in wallList:
        if wallID == '': continue
        __buildWall(buildingObj,wallID)
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)

    return {'FINISHED'}