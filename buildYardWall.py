# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   院墙的营造

import bpy
from mathutils import Vector
import math

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from .data import ACA_data_template as tmpData
from . import utils
from . import acaTemplate
from . import texture as mat

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

# 平铺瓦顶
def __arrayTile(
        wallProxy:bpy.types.Object,
        sourceObj:bpy.types.Object,
        arrayLength,
        arrayWidth=None,
        name='瓦顶',
        location=(0,0,0),
        rotation=(0,0,0),
    ):
    # 载入数据
    buildingObj = wallProxy.parent
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    # 墙体的长宽高，以wallproxy为依据
    (wallLength,wallDeepth,wallHeight) = wallProxy.dimensions

    # 瓦件缩放，当前设置的斗口与默认斗口
    tileScale = bData.DK / con.DEFAULT_DK
    # 垄距，以最宽的滴水瓦为参考
    colWidth = aData.dripTile_source.dimensions.x * tileScale
    # 取可以整数排布的垄距
    colWidth = wallLength/math.floor(wallLength/colWidth)
    # 行距，以筒瓦长度为参考
    rowHeight = aData.circularTile_source.dimensions.y * tileScale

    # 导入瓦片对象
    tileObj = utils.copyObject(
        name=name,
        sourceObj=sourceObj,
        location=location,
        rotation=rotation,
        parentObj=wallProxy,
        singleUser=True)
    # 根据斗口调整尺度
    utils.resizeObj(tileObj,tileScale)
    utils.applyTransfrom(tileObj,use_scale=True)
    # 应用所有的modifier，以免后续快速合并时丢失
    utils.applyAllModifer(tileObj)

    # 横向平铺
    modArray:bpy.types.ArrayModifier = \
        tileObj.modifiers.new('横向平铺','ARRAY')
    modArray.use_relative_offset = False
    modArray.use_constant_offset = True
    modArray.constant_offset_displace = (colWidth,0,0)
    modArray.fit_type = 'FIT_LENGTH' 
    modArray.fit_length = arrayLength
    # 纵向平铺
    if arrayWidth != None:
        modArray:bpy.types.ArrayModifier = \
            tileObj.modifiers.new('纵向平铺','ARRAY')
        modArray.use_relative_offset = False
        modArray.use_constant_offset = True
        modArray.constant_offset_displace = (0,rowHeight,0)
        modArray.fit_type = 'FIT_LENGTH' 
        modArray.fit_length = arrayWidth
    # 镜像
    utils.addModifierMirror(
        object=tileObj,
        mirrorObj=wallProxy,
        use_axis=(False,True,False),
        use_bisect=(False,True,False),
        use_flip=(False,True,False),
    )
    return tileObj

def buildSingleWall(
        wallProxy:bpy.types.Object,
        bodyShrink,
        tileAngle,
        use_cut=False,
        ):
    # 载入数据
    buildingObj = wallProxy.parent
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    
    # 如果要四角融合，则适当延长瓦面
    if use_cut:
        cutExtend = 0.22    # 改变这个值，可以看到转角合并的瓦的变化
        wallProxy.dimensions.x += cutExtend*2
        utils.applyTransfrom(wallProxy,use_scale=True)
    # 墙体的长宽高，以wallproxy为依据
    (wallLength,wallDeepth,wallHeight) = wallProxy.dimensions

    # 1、创建下碱对象
    height = wallHeight * con.WALL_BOTTOM_RATE
    bottomObj = utils.addCube(
        name='下碱',
        dimension=(wallLength,
               wallDeepth,
               height),
        location=(0,0,height/2-wallHeight/2),
        parent=wallProxy,
    )

    # 赋材质
    mat.setShader(bottomObj,
            mat.shaderType.ROCK)

    # 2、创建上身对象
    bodyObj = utils.addCube(
        name='上身',
        dimension=(wallLength-bodyShrink*2,
               wallDeepth-bodyShrink*2,
               wallHeight-bodyShrink*2),
        location=(0,0,0),
        parent=wallProxy,
    )

    # 赋材质
    mat.setShader(bodyObj,
            mat.shaderType.REDDUST)

    # 3、瓦顶
    # 瓦件缩放
    tileScale = bData.DK / con.DEFAULT_DK
    # 垄距
    colWidth = aData.dripTile_source.dimensions.x * tileScale
    # 取可以整数排布的垄距
    colWidth = wallLength / math.floor(wallLength/colWidth)
    
    # 3.1、滴水
    __arrayTile(
        name = '滴水',
        sourceObj=aData.dripTile_source,
        location=(-wallLength/2+colWidth/2,
                  -wallDeepth/2,
                  wallHeight/2),
        rotation=(tileAngle,0,0),
        wallProxy=wallProxy,
        arrayLength=wallLength-colWidth,)

    # 3.2、瓦当
    __arrayTile(
        name = '瓦当',
        sourceObj=aData.eaveTile_source,
        location=(-wallLength/2,
                  -wallDeepth/2
                  ,wallHeight/2),
        rotation=(tileAngle,0,0),
        wallProxy=wallProxy,
        arrayLength=wallLength,)

    # 3.3、板瓦
    __arrayTile(
        name = '板瓦',
        sourceObj=aData.flatTile_source,
        location=(-wallLength/2+colWidth/2,
                  -wallDeepth/2,
                  wallHeight/2),
        rotation=(tileAngle,0,0),
        wallProxy=wallProxy,
        arrayLength=wallLength-colWidth,
        arrayWidth=wallDeepth,)

    # 3.4、筒瓦
    __arrayTile(
        name = '筒瓦',
        sourceObj=aData.circularTile_source,
        location=(-wallLength/2,
                  -wallDeepth/2,
                  wallHeight/2),
        rotation=(tileAngle,0,0),
        wallProxy=wallProxy,
        arrayLength=wallLength,
        arrayWidth=wallDeepth,)
    
    # 4、端头做博缝板
    bofengObj = utils.copyObject(
        sourceObj=aData.bofeng_source,
        name="博缝板",
        parentObj=wallProxy,
        location=(-wallLength/2+bodyShrink,
                  -wallDeepth/2-con.EAVETILE_EX*dk*2,
                  wallHeight/2),
        rotation=(0,-tileAngle,math.radians(90)),
        singleUser=True
    )
    # 根据斗口调整尺度
    utils.resizeObj(bofengObj,tileScale)
    utils.applyTransfrom(bofengObj,use_scale=True)
    # 镜像
    utils.addModifierMirror(
        object=bofengObj,
        mirrorObj=wallProxy,
        use_axis=(True,True,False),
        use_bisect=(False,True,False),
        use_flip=(False,True,False),
    )

    # 5、正脊 
    # 正脊长度，与瓦顶的出梢匹配
    bofengWidth = aData.bofeng_source.dimensions.y\
                     * tileScale*0.5
    ridgeLength = wallLength + bofengWidth
    # 正脊高度，根据瓦顶斜率计算，略作微调
    ridgeHeight = wallDeepth/2 * math.tan(tileAngle)-con.TILE_HEIGHT
    # 导入正脊
    ridgeObj = utils.copyObject(
        sourceObj=aData.ridgeFront_source,
        name="正脊",
        parentObj=wallProxy,
        singleUser=True)
    # 根据斗口调整尺度
    utils.resizeObj(ridgeObj,
        bData.DK / con.DEFAULT_DK)
    # 脊筒在正脊长度上整数排布，微调其长度
    ridgeWidth = ridgeObj.dimensions.x
    ridgeNum = math.floor(ridgeLength/ridgeWidth)
    ridgeWidth = ridgeLength / ridgeNum
    ridgeObj.dimensions.x = ridgeWidth
    utils.applyTransfrom(ridgeObj,use_scale=True)
    # 定位正脊排布起点
    ridgeObj.location = (
        -ridgeLength/2,
        0,
        wallHeight/2 + ridgeHeight)
    # 平铺
    modArray:bpy.types.ArrayModifier = \
        ridgeObj.modifiers.new('横向平铺','ARRAY')
    modArray.use_relative_offset = True
    modArray.relative_offset_displace = (1,0,0)
    modArray.fit_type = 'FIT_LENGTH' 
    modArray.fit_length = ridgeLength

    # 6、做裁剪
    if use_cut:
        # 合并子对象
        wallObj = utils.joinObjects(
            wallProxy.children,newName='院墙')
        # 左侧剪切
        utils.addBisect(
            object=wallObj,
            pStart=wallProxy.matrix_world @Vector((0,0,0)),
            pEnd=wallProxy.matrix_world @Vector((-1,-1,0)),
            pCut=wallProxy.matrix_world @ \
                Vector((-wallLength/2+wallDeepth/2+cutExtend,0,0)),
            clear_inner=True,
            use_fill=False,
        )
        # 右侧剪切
        utils.addBisect(
            object=wallObj,
            pStart=wallProxy.matrix_world @Vector((0,0,0)),
            pEnd=wallProxy.matrix_world @Vector((-1,1,0)),
            pCut=wallProxy.matrix_world @ \
                Vector((wallLength/2-wallDeepth/2-cutExtend,0,0)),
            clear_inner=True,
            use_fill=False,
        )

    return

def buildYardWall(buildingObj:bpy.types.Object):
    # 定位到根目录，如果没有则新建
    utils.setCollection(con.ROOT_COLL_NAME,isRoot=True)

    # 新建还是刷新？
    if buildingObj == None:
        utils.outputMsg("创建新建筑...")
        # 获取panel上选择的模版
        templateName = bpy.context.scene.ACA_data.template
        # 添加建筑根节点，同时载入模版
        buildingObj = __addBuildingRoot(templateName)
    else:
        # 简单粗暴的全部删除
        utils.deleteHierarchy(buildingObj)

    # 锁定操作目录
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('院墙',parentColl=buildingColl)

    # 载入数据
    bData:acaData = buildingObj.ACA_data

    # 院子参数
    yardWidth = bData.yard_width
    yardDeepth = bData.yard_depth

    # 院墙参数
    wallHeight = bData.yardwall_height
    wallDeepth = bData.yardwall_depth
    # 退花碱厚度
    bodyShrink = con.WALL_SHRINK
    # 瓦顶斜率
    tileAngle = math.radians(bData.yardwall_angle)

    wallGroup = []
    # 如果做4面墙，则四角剪切
    use_cut = True
    # 是否做四面墙
    if not bData.is_4_sides:
        wallItem = {
            'dim': ((yardWidth,
                    wallDeepth,
                    wallHeight)),
            'loc': (0,0,wallHeight/2),
            'rot': (0,0,0),
        }
        wallGroup.append(wallItem)
        # 四角不做剪切
        use_cut = False
    else:
        # 南墙
        wallItem = {
            'dim': ((yardWidth+wallDeepth,
                    wallDeepth,
                    wallHeight)),
            'loc': (0,-yardDeepth/2,wallHeight/2),
            'rot': (0,0,0),
        }
        wallGroup.append(wallItem)
        # 北墙
        wallItem = {
            'dim': ((yardWidth+wallDeepth,
                    wallDeepth,
                    wallHeight)),
            'loc': (0,yardDeepth/2,wallHeight/2),
            'rot': (0,0,math.radians(180)),
        }
        wallGroup.append(wallItem)
        # 西墙
        wallItem = {
            'dim': ((yardDeepth+wallDeepth,
                    wallDeepth,
                    wallHeight)),
            'loc': (-yardWidth/2,0,wallHeight/2),
            'rot': (0,0,math.radians(270)),
        }
        wallGroup.append(wallItem)
        # 东墙
        wallItem = {
            'dim': ((yardDeepth+wallDeepth,
                    wallDeepth,
                    wallHeight)),
            'loc': (yardWidth/2,0,wallHeight/2),
            'rot': (0,0,math.radians(90)),
        }
        wallGroup.append(wallItem)

    # 依次生成院子四面的院墙
    for wallItem in wallGroup:        
        # 构造院墙proxy
        wallProxy = utils.addCube(
            name='wallProxy',
            dimension=wallItem['dim'],
            location=wallItem['loc'],
            rotation=wallItem['rot'],
            parent=buildingObj
        )
        utils.hideObjFace(wallProxy)

        # 依据proxy生成院墙
        buildSingleWall(
            wallProxy=wallProxy,
            bodyShrink=bodyShrink,
            tileAngle=tileAngle,
            use_cut=use_cut
            )

    utils.focusObj(buildingObj)

    return {'FINISHED'}