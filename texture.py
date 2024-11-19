# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   对象展UV和贴材质
import bpy
import bmesh
import math
from mathutils import Vector,Euler

from . import utils
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from .data import ACA_data_template as tmpData

# 设置材质的输入参数
# https://blender.stackexchange.com/questions/191183/changing-a-value-node-in-many-materials-with-a-python-script
def __setMatValue(mat:bpy.types.Material,
                inputName:str,
                value):
    if mat is not None and mat.use_nodes and mat.node_tree is not None:
        for node in mat.node_tree.nodes:
            for input in node.inputs:
                if input.name == inputName and input.type == 'VALUE':
                    input.default_value = value 
    return

# 二维点阵基于p点的缩放
# v：待缩放的向量（vx，vy）
# s: 缩放比例（sx，sy）
# p：缩放的原点（px，py）
def __Scale2D( v, s, p ):
    return ( p[0] + s[0]*(v[0] - p[0]), p[1] + s[1]*(v[1] - p[1]) )     

# UV的缩放
def __ScaleUV( uvMap, scale, pivot ):
    for uvIndex in range( len(uvMap.data) ):
        uvMap.data[uvIndex].uv = __Scale2D( uvMap.data[uvIndex].uv, scale, pivot )

# 二维点阵的旋转
def __make_rotation_transformation(angle, origin=(0, 0)):
    from math import cos, sin
    cos_theta, sin_theta = cos(angle), sin(angle)
    x0, y0 = origin    
    def xform(point):
        x, y = point[0] - x0, point[1] - y0
        return (x * cos_theta - y * sin_theta + x0,
                x * sin_theta + y * cos_theta + y0)
    return xform

# UV的旋转
def __RotateUV(uvMap, angle, pivot):
    rot = __make_rotation_transformation(angle, pivot)
    for uvIndex in range( len(uvMap.data) ):
        uvMap.data[uvIndex].uv = rot(uvMap.data[uvIndex].uv ) 
    return

# 展UV，提供了多种不同的方式
def UvUnwrap(object:bpy.types.Object,
             type=None,
             scale=None,
             pivot=(0,0),
             rotate=None,
             fitIndex=None,
             ):
    # 聚焦对象
    utils.focusObj(object)

    # 应用modifier
    utils.applyAllModifer(object)

    # 进入编辑模式
    bpy.ops.object.mode_set(mode = 'EDIT') 
    bpy.ops.mesh.select_mode(type = 'FACE')
    bpy.ops.mesh.select_all(action='SELECT')
    
    if type == None:
        # 默认采用smart project
        bpy.ops.uv.smart_project(
            angle_limit=math.radians(66), 
            margin_method='SCALED', 
            island_margin=0.0001, 
            area_weight=0.0, 
            correct_aspect=True, 
            scale_to_bounds=False
        )
    # 普通材质的cube project，保证贴图缩放的一致性
    elif type == uvType.CUBE:
        bpy.ops.uv.cube_project(
            cube_size=10,
        )
    # 窗棂比例较小
    elif type == uvType.WIN:
        bpy.ops.uv.cube_project(
            cube_size=0.1,
        )
    # 系统默认的cube project，在梁枋的六棱柱上效果更好
    elif type == uvType.SCALE:
        bpy.ops.uv.cube_project(
            scale_to_bounds=True
        )
    # 精确适配
    # 先所有面一起做加权分uv，然后针对需要特殊处理的面，进行二次适配
    elif type == uvType.FIT:
        # 先做一次加权投影
        bpy.ops.uv.cube_project(
            scale_to_bounds=True
        )
        # 清空选择
        bpy.ops.mesh.select_all(action = 'DESELECT')
        # 载入bmesh
        me = object.data
        bm = bmesh.from_edit_mesh(me)
        # 选择面
        for face in bm.faces:
            if face.index in fitIndex:
                face.select = True 
        # 写回对象
        bmesh.update_edit_mesh(me)
        # unwarp
        bpy.ops.uv.cube_project(
            scale_to_bounds=True
        )
    # 重置UV，让每个面都满铺，但存在rotate的问题，暂未使用
    elif type == uvType.RESET:
        bpy.ops.uv.reset()
    # 柱状投影，在柱子上效果很好
    elif type == uvType.CYLINDER:
        bpy.ops.uv.cylinder_project(
            direction='ALIGN_TO_OBJECT',
            align='POLAR_ZY',
            scale_to_bounds=True
        )
    bpy.ops.object.mode_set(mode = 'OBJECT')

    # 拉伸UV，参考以下：
    # https://blender.stackexchange.com/questions/75061/scale-uv-map-script
    if scale != None:
        uvMap = object.data.uv_layers['UVMap']
        __ScaleUV(uvMap,scale,pivot)

    # 旋转UV，参考：
    # https://blender.stackexchange.com/questions/28929/rotate-uv-by-specific-angle-e-g-30deg-in-python-script-in-backgroud-mode
    if rotate != None:
        uvMap = object.data.uv_layers['UVMap']
        __RotateUV(uvMap,rotate,pivot)

    return
# 拷贝目标对象的材质

# 展UV的类型
class uvType:
    CUBE = 'cube'
    SCALE = 'scale'
    FIT = 'fit'
    RESET = 'reset'
    CYLINDER  = 'cylinder'
    WIN = 'win'

# 复制所有材质
def __copyMaterial(fromObj:bpy.types.Object,
                 toObj:bpy.types.Object,
                 single=False):
    if type(fromObj) == bpy.types.Object:
        toObj.data.materials.clear()
        for mat in fromObj.data.materials:
            if single:
                mat = mat.copy()
            toObj.data.materials.append(mat)

    return

# 根据制定的材质，展UV，并调用材质属性设置
def __setTexture(
        object:bpy.types.Object,
        mat:bpy.types.Object,
        single=False):
    # 绑定材质
    __copyMaterial(mat,object,single)
    aData:tmpData = bpy.context.scene.ACA_temp

    # 简单平铺的材质
    if mat in (
        aData.mat_wood,         # 木材材质
        aData.mat_rock,         # 石材材质
        aData.mat_stone,        # 石头材质
        aData.mat_red,          # 漆.土朱材质
        aData.mat_brick_1,      # 方砖缦地
        aData.mat_brick_2,      # 条砖竖铺
        aData.mat_brick_3,      # 条砖横铺
        aData.mat_dust_red,     # 抹灰.红
    ):
        # 依赖几何体默认生成的UV，不再重新生成
        # UvUnwrap(object,uvType.CUBE)
        pass  
    
    # 梁枋彩画
    if mat in (
            aData.mat_paint_beam, 
            aData.mat_paint_beam_alt,
        ):
        UvUnwrap(object,uvType.SCALE)
        # 设置槫头坐龙
        if object.name.startswith('挑檐桁'):
            __setTuanHead(object)

    # 垫板.公母草
    if mat == aData.mat_paint_grasscouple:
        UvUnwrap(object,uvType.SCALE)   

    # 柱头贴图
    if mat == aData.mat_paint_pillerhead:
        UvUnwrap(object,uvType.CYLINDER)
        # 设置材质属性
        __setPillerHead(object)

    # 平板枋.行龙
    if mat == aData.mat_paint_walkdragon:
        # 对前后面做fit方式，保证能够铺满这个材质
        UvUnwrap(object,uvType.FIT,fitIndex=[1,3])

    # 栱垫板
    if mat == aData.mat_paint_dgfillboard:
        UvUnwrap(object,uvType.SCALE)
        # 设置材质属性
        __setDgCount(object)

    # 檐椽
    if mat == aData.mat_paint_rafter:
        # 檐椽展UV比较特殊，专门写了一个处理函数
        object = __setRafterMat(object)
    
    # 飞椽
    if mat == aData.mat_paint_flyrafter:
        object = __setFlyrafterMat(object)

    # 翼角望板
    if mat == aData.mat_paint_wangban:
        UvUnwrap(object,uvType.CUBE)
        # 已经在材质中判断了在原木底面刷红，不需要用python设置了
        #__setWangCornerMat(object)

    # 挑檐枋，工王云
    if mat == aData.mat_paint_cloud:
        UvUnwrap(object,uvType.SCALE)

    # 子角梁，龙肚子
    if mat == aData.mat_paint_ccb:
        UvUnwrap(object,uvType.RESET)

    # 隔扇，壶门
    if mat == aData.mat_paint_door:
        UvUnwrap(object,uvType.SCALE)

    # 隔扇，绦环板
    if mat == aData.mat_paint_doorring:
        UvUnwrap(object,uvType.SCALE)

    # 山花板
    if mat == aData.mat_paint_shanhua:
        # do nothing
        pass

    # 三交六椀隔心
    if mat == aData.mat_geshanxin:
        UvUnwrap(object,uvType.WIN)

    return object

# 设置槫头坐龙
def __setTuanHead(tuan:bpy.types.Object):
    # 追加槫头坐龙材质
    aData:tmpData = bpy.context.scene.ACA_temp
    matHeadDragon = aData.mat_paint_tuanend.active_material
    tuan.data.materials.append(matHeadDragon)

    # 找到左右两个端头，并绑定新材质
    bm = bmesh.new()
    bm.from_mesh(tuan.data)
    for face in bm.faces:
        face.select = False

    # 以底面可确定的0号面为参考
    rightNormal = Vector((1,0,0))
    leftNormal = Vector((-1,0,0))
    # 选择法线类似的所有面，0.1是在blender里尝试的经验值
    for face in bm.faces:
        right:Vector = face.normal - rightNormal
        if right.length < 1:
            face.material_index = 1
            face.select = True
        left:Vector = face.normal - leftNormal
        if left.length < 1:
            face.material_index = 1
            face.select = True
    bm.to_mesh(tuan.data)
    bm.free()

    # 从资产中传递预定义的UV
    __copyUV(
        fromObj=aData.mat_paint_tuanend,
        toObj= tuan,
    )
    return

# 复制UV
def __copyUV(
    fromObj:bpy.types.Object,
    toObj:bpy.types.Object):
    # 从资产中传递预定义的UV
    # 确认选中两个对象
    fromobjCopy = utils.copySimplyObject(fromObj,singleUser=True)
    fromobjCopy.select_set(True)
    toObj.select_set(True)
    bpy.context.view_layer.objects.active = fromobjCopy
    # 获取源UV
    uv = fromobjCopy.data.uv_layers[0]
    uv.active = True
    # 重建目标UV
    toObj.data.uv_layers.remove(toObj.data.uv_layers[0])
    new_uv = toObj.data.uv_layers.new(name='UVMap')
    new_uv.active = True
    # 调用UV传递
    bpy.ops.object.join_uvs()

    # 删除fromObj
    bpy.data.objects.remove(fromobjCopy)

    return

# 翼角望板材质，底面刷红
def __setWangCornerMat(wangban:bpy.types.Object):
    # 添加原木和红漆材质
    aData:tmpData = bpy.context.scene.ACA_temp
    matWood = aData.mat_wood.active_material
    wangban.data.materials.append(matWood)
    matRed = aData.mat_red.active_material
    wangban.data.materials.append(matRed)

    # 找到所有的底面
    bm = bmesh.new()
    bm.from_mesh(wangban.data)

    # 以底面可确定的0号面为参考
    # bm.faces.ensure_lookup_table()
    # baseNormal = bm.faces[0].normal
    baseNormal = Vector((0,0,-1))
    # 选择法线类似的所有面，0.1是在blender里尝试的经验值
    for face in bm.faces:
        threshold:Vector = face.normal - baseNormal
        if threshold.length < 1:
            face.material_index = 1
    bm.to_mesh(wangban.data)
    bm.free()
    return

# 檐椽展UV
def __setRafterMat(rafter:bpy.types.Object):
    # 拆分，将合并或array的椽子，拆分到独立的对象
    rafterList = utils.separateObject(rafter)

    # 逐一处理每根椽子
    for n in range(len(rafterList)):
        rafter = rafterList[n]
        # 找到端头面
        bm = bmesh.new()
        bm.from_mesh(rafter.data)
        bm.faces.ensure_lookup_table()
        # 轮询面集合，查找最大值
        headPoint = Vector((0,0,0))
        endFaceIndex = 0
        for face in bm.faces:
            # 面的几何中心点
            faceCenter = face.calc_center_median()
            if faceCenter.x > headPoint.x:
                headPoint = faceCenter
                endFaceIndex = face.index
        # 端头材质绑定
        if n%2 == 1 :
            # 正常色（绿）
            bm.faces[endFaceIndex].material_index = 1
        else:
            # 异色（青）
            bm.faces[endFaceIndex].material_index = 2
        # 选中并展UV
        bm.faces[endFaceIndex].select = True
        bm.to_mesh(rafter.data)
        bm.free()
    # 端头按scale展开
    bpy.ops.object.mode_set(mode = 'EDIT') 
    bpy.ops.uv.cube_project(
        scale_to_bounds=True
    )
    bpy.ops.object.mode_set(mode = 'OBJECT')

    # 重新合并，以免造成混乱
    rafter = utils.joinObjects(rafterList)
    return rafter

# 飞椽展UV
def __setFlyrafterMat(flyrafter:bpy.types.Object):
    # 拆分，将合并或array的椽子，拆分到独立的对象
    flyrafterList = utils.separateObject(flyrafter)

    # 逐一处理每根椽子
    for n in range(len(flyrafterList)):
        flyrafter = flyrafterList[n]
        # 找到端头面
        bm = bmesh.new()
        bm.from_mesh(flyrafter.data)
        bm.faces.ensure_lookup_table()
        # 轮询面集合，查找最大值
        headPoint = Vector((0,0,0))
        endFaceIndex = 0
        for face in bm.faces:
            # 面的几何中心点
            faceCenter = face.calc_center_median()
            if faceCenter.x > headPoint.x:
                headPoint = faceCenter
                endFaceIndex = face.index
        # 端头材质绑定
        bm.faces[endFaceIndex].material_index = 1
        # 选中并展UV
        bm.faces[endFaceIndex].select = True
        bm.to_mesh(flyrafter.data)
        bm.free()
    # 端头用reset方式，可以适配椽头菱形的变形
    bpy.ops.object.mode_set(mode = 'EDIT') 
    bpy.ops.uv.reset()
    bpy.ops.object.mode_set(mode = 'OBJECT')

    # 重新合并，以免造成混乱
    flyrafter = utils.joinObjects(flyrafterList)

    return flyrafter

# 材质类型，实际是对材质的指向关系
class shaderType:
    WOOD = '木材'
    REDPAINT = '漆.土朱'
    GOLDPAINT = '漆.金'
    REDDUST = '抹灰.红'
    BRICK1 = '方砖缦地'
    BRICK2 = '条砖竖铺'
    BRICK3 = '条砖横铺'
    ROCK = '石材'
    STONE = '石头'
    PILLER = '柱子'
    PILLERBASE = '柱础'
    PINGBANFANG = '平板枋'
    GONGDIANBAN = '栱垫板'
    LIANGFANG = '梁枋'
    LIANGFANG_ALT = '梁枋异色'
    YOUEDIANBAN = '由额垫板'
    RAFTER = '檐椽'
    FLYRAFTER = '飞椽'
    WANGBANRED = '望板'
    CLOUD = '工王云'
    CCB = '子角梁'
    DOOR = '裙板'
    DOORRING = '绦环板'
    SHANHUA = '山花板'
    GESHANXIN = '三交六椀隔心'

# 映射对象与材质的关系
# 便于后续统一的在“酱油配色”，“清官式彩画”等配色方案间切换
def setShader(object:bpy.types.Object,
              shader:str,
              override=False,
              single=False):
    # 如果已经有材质，且未声明override，则不做材质
    if object.active_material != None \
        and not override:
        # 不做任何改变
        return
    
    aData:tmpData = bpy.context.scene.ACA_temp
    mat = None

    # 木材
    if shader == shaderType.WOOD:
        mat = aData.mat_wood

    # 红
    if shader == shaderType.REDPAINT:
        mat = aData.mat_red
    # 金
    if shader == shaderType.GOLDPAINT:
        mat = aData.mat_gold
    # 灰.红
    if shader == shaderType.REDDUST:
        mat = aData.mat_dust_red

    # 石材
    if shader == shaderType.ROCK:
        mat = aData.mat_rock
    if shader == shaderType.STONE:
        mat = aData.mat_stone

    # 方砖缦地
    if shader == shaderType.BRICK1:
        mat = aData.mat_brick_1
    if shader == shaderType.BRICK2:
        mat = aData.mat_brick_2
    if shader == shaderType.BRICK3:
        mat = aData.mat_brick_3

    # 柱础
    if shader == shaderType.PILLERBASE:
        mat = aData.mat_stone

    # 柱头彩画，坐龙
    if shader == shaderType.PILLER:
        mat = aData.mat_paint_pillerhead
    
    # 梁枋彩画，双龙和玺
    if shader == shaderType.LIANGFANG:
        mat = aData.mat_paint_beam
    if shader == shaderType.LIANGFANG_ALT:
        mat = aData.mat_paint_beam_alt

    # 平板枋，行龙彩画
    if shader == shaderType.PINGBANFANG:
        mat = aData.mat_paint_walkdragon

    # 栱垫板，三宝珠彩画
    if shader == shaderType.GONGDIANBAN:
        mat = aData.mat_paint_dgfillboard

    # 由额垫板，公母草
    if shader == shaderType.YOUEDIANBAN:
        mat = aData.mat_paint_grasscouple

    # 檐椽，龙眼
    if shader == shaderType.RAFTER:
        mat = aData.mat_paint_rafter

    # 飞椽，万字
    if shader == shaderType.FLYRAFTER:
        mat = aData.mat_paint_flyrafter

    # 翼角望板，底面刷红
    if shader == shaderType.WANGBANRED:
        mat = aData.mat_paint_wangban

    # 挑檐枋，工王云
    if shader == shaderType.CLOUD:
        mat = aData.mat_paint_cloud
    
    # 子角梁，龙肚子
    if shader == shaderType.CCB:
        mat = aData.mat_paint_ccb
    
    # 隔扇，壶门
    if shader == shaderType.DOOR:
        mat = aData.mat_paint_door
    
    # 隔扇，绦环板
    if shader == shaderType.DOORRING:
        mat = aData.mat_paint_doorring
    
    # 山花板
    if shader == shaderType.SHANHUA:
        mat = aData.mat_paint_shanhua

    # 三交六椀隔心
    if shader == shaderType.GESHANXIN:
        mat = aData.mat_geshanxin

    if mat != None:
        # 展UV，绑材质
        object = __setTexture(object,mat,single)

    return object

# 计算柱头贴图的高度
# 依据大额枋、由额垫板、小额枋的高度计算
# 不判断是否做双重额枋
def __setPillerHead(object:bpy.types.Object):
    buildingObj = utils.getAcaParent(
        object,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK

    # 缩放柱头贴图尺寸，与大小额枋及垫板的高度计算
    fangHeight = con.EFANG_LARGE_H*dk
    if bData.use_smallfang:
        fangHeight += (con.BOARD_YOUE_H*dk
            + con.EFANG_SMALL_H*dk)
    scale = fangHeight / bData.piller_height
    __setMatValue(
        mat=object.active_material,
        inputName='headRate',
        value=scale)

# 设置垫拱板的重复次数，根据斗栱攒数计算
def __setDgCount(object:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(
        object,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data

    # 设置材质中的斗栱攒数
    fang_length = object.dimensions.x
    count = round(fang_length / bData.dg_gap)
    __setMatValue(
        mat=object.active_material,
        inputName='count',
        value=count)