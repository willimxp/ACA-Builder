# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   对象展UV和贴材质
import bpy
import bmesh
import math
from mathutils import Vector

from . import utils
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from .data import ACA_data_template as tmpData

# 展UV的类型
class uvType:
    CUBE = 'cube'
    SCALE = 'scale'
    FIT = 'fit'
    RESET = 'reset'
    CYLINDER  = 'cylinder'
    WIN = 'win'

# 二维点阵基于p点的缩放
# v：待缩放的向量（vx，vy）
# s: 缩放比例（sx，sy）
# p：缩放的原点（px，py）
def __Scale2D( v, s, p ):
    return ( p[0] + s[0]*(v[0] - p[0]), p[1] + s[1]*(v[1] - p[1]) )     

# UV的缩放
def __ScaleUV( uvMap, scale, pivot, fixcenter=False):
    for uvIndex in range( len(uvMap.data) ):
        if fixcenter:
            if uvMap.data[uvIndex].uv[0] > - 0.0001 and uvMap.data[uvIndex].uv[0]< 1.0001:
                continue
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

# 展UV，提供了多种不同的方式
def UvUnwrap(object:bpy.types.Object,
             type=None,
             scale=None,
             pivot=(0,0),
             rotate=None,
             fitIndex=None,
             cubesize=2,
             correctAspect = True,
             scaleToBounds = False,
             remainSelect = False,
             onlyActiveMat = False,
             ):   
    # 隐藏对象不重新展UV
    if (object.hide_viewport 
        or object.hide_get()
        ):
        return
    
    # 非Mesh对象不能展UV
    if object.type not in ('MESH'):
        return
    
    # 聚焦对象
    utils.focusObj(object)
    # 应用modifier
    utils.applyAllModifer(object)

    # 验证对象是否可以展UV，至少应该有一个以上的面
    bm = bmesh.new()
    bm.from_mesh(object.data)
    faceCount= len(bm.faces)
    bm.free()
    if faceCount == 0 : 
        utils.outputMsg("展UV异常，该对象不存在几何面")
        return

    # 仅针对活跃材质active material
    if onlyActiveMat:
        bm = bmesh.new()
        bm.from_mesh(object.data)
        for face in bm.faces:
            face.select = False
            if face.material_index == object.active_material_index:
                face.select = True
        bm.to_mesh(object.data)
        bm.free()

    # 进入编辑模式
    bpy.ops.object.mode_set(mode = 'EDIT') 
    bpy.ops.mesh.select_mode(type = 'FACE')
    if (not remainSelect
        and not onlyActiveMat):
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
            cube_size=cubesize,
            correct_aspect=correctAspect,
            scale_to_bounds=scaleToBounds,
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

# 统一开放的着色接口
def paint(paintObj:bpy.types.Object,        # 着色对象
          paintMat:str,                     # 材质名称，根据业务需要自定义
          override=False,                   # 是否覆盖已有材质
          ):
    # 预校验 #############################################
    # 非mesh对象直接跳过
    if paintObj == None: return
    if paintObj.type not in ('MESH','CURVE'):
        return
    # 如果已经有材质，且未声明override，则不做材质
    if paintObj.active_material != None \
        and not override:
        # 不做任何改变
        return
    
    # 初始化 ############################################
    buildingObj = utils.getAcaParent(
        paintObj,con.ACA_TYPE_BUILDING)
    # 尝试是否为院墙
    if buildingObj is None:
        buildingObj = utils.getAcaParent(
            paintObj,con.ACA_TYPE_YARDWALL)
    # 获取配色方案
    if buildingObj != None:
        # 有匹配的建筑类型，以建筑的配色为准
        paintStyle = buildingObj.ACA_data.paint_style
    else:
        # 没有匹配的建筑类型，指定默认值
        paintStyle = '0'
    aData:tmpData = bpy.context.scene.ACA_temp
    mat = None
    slot = None

    # 着色 #############################################
    # 0. 通用样式，定义在各个配色方案中都通用的材质
    if paintMat in (
            con.M_GOLD, # 金漆
        ):
            mat = aData.mat_gold # 金漆
    if paintMat in (
            con.M_GREEN, # 绿漆
        ):
            mat = aData.mat_green # 绿漆
    if paintMat in (
            con.M_PLATFORM_FLOOR, # 台基地面
        ):
            mat = aData.mat_brick_1 # 方砖缦地
    if paintMat in (
            con.M_PLATFORM_WALL, # 台基陡板
            con.M_BRICK_WALL, # 砖墙
        ):
            mat = aData.mat_brick_3 # 条砖横铺
    if paintMat in (
            con.M_ROCK, # 石材
            con.M_PLATFORM_ROCK, # 台基石材
            con.M_WALL_BOTTOM, # 墙-下碱
            con.M_WINDOW_WALL, # 槛墙
        ):
            mat = aData.mat_rock # 石材
    if paintMat in (
            con.M_PLATFORM_EXPAND, # 台基石材
        ):
            mat = aData.mat_brick_2 # 条砖竖铺
    if paintMat in (
            con.M_STONE, # 石头
            con.M_PILLER_BASE, # 柱顶石
            con.M_XIANGYAN, # 象眼板
        ):
            mat = aData.mat_stone # 石头
    if paintMat in (
            con.M_WOOD, # 原木
            con.M_BEAM_NOPAINT, # 梁架-无漆
            con.M_ROOF_NOPAINT, # 屋顶-无漆
        ):
            mat = aData.mat_wood # 原木
    
    
    # 0. 金龙和玺样式
    if paintStyle == '0':
        if paintMat in (
            con.M_PAINT,            # 上漆
            con.M_FANG_JIN,         # 金枋
            con.M_BOARD_WALLHEAD,   # 走马板
            con.M_WINDOW,           # 窗框
            con.M_BEAM_PAINT,       # 梁架上漆
            con.M_ROOF_PAINT,       # 梁架上漆
        ):
            mat = aData.mat_oilpaint # 红漆
        if paintMat in (
            con.M_FANG_EBIG, # 大额枋
        ):
            mat = aData.mat_paint_beam_big
        if paintMat in (
            con.M_FANG_ESMALL, # 小额枋
        ):
            mat = aData.mat_paint_beam_small    
        if paintMat in (
            con.M_BOARD_YOUE, # 由额垫板
        ):
            mat = aData.mat_paint_grasscouple   
        if paintMat in (
            con.M_PILLER_HEAD, # 柱头
        ):
            mat = aData.mat_paint_pillerhead 
        if paintMat in (
            con.M_WALL, # 墙-抹灰
        ):
            mat = aData.mat_dust_wall
        if paintMat in (
            con.M_WINDOW_INNER, # 棂心
        ):
            mat = aData.mat_geshanxin 
        if paintMat in (
            con.M_LINXIN_WAN, # 万字锦
        ):
            mat = aData.mat_geshanxin_wan 
        if paintMat in (
            con.M_DOOR_RING, # 绦环板
        ):
            mat = aData.mat_paint_doorring 
        if paintMat in (
            con.M_DOOR_BOTTOM, # 裙板
        ):
            mat = aData.mat_paint_door 
        if paintMat in (
            con.M_FANG_PINGBAN, # 平板枋
        ):
            mat = aData.mat_paint_walkdragon 
        if paintMat in (
            con.M_FANG_TIAOYAN, # 挑檐枋
        ):
            mat = aData.mat_paint_cloud 
        if paintMat in (
            con.M_BOARD_DG, # 栱垫板
        ):
            mat = aData.mat_paint_dgfillboard 
        if paintMat in (
            con.M_BOARD_DG_S, # 栱垫板-小
        ):
            mat = aData.mat_paint_dgfillboard_s 
        if paintMat in (
            con.M_CORNERBEAM_S, # 子角梁
        ):
            mat = aData.mat_paint_ccb
        if paintMat in (
            con.M_RAFTER, # 檐椽
        ):
            mat = aData.mat_paint_rafter
        if paintMat in (
            con.M_FLYRAFTER, # 飞椽
        ):
            mat = aData.mat_paint_flyrafter
        if paintMat in (
            con.M_WANGBAN, # 望板
        ):
            mat = aData.mat_paint_wangban
        if paintMat in (
            con.M_SHANHUA, # 山花板
        ):
            mat = aData.mat_paint_shanhua
        if paintMat in (
            con.M_FANG_DGCONNECT,   # 拽枋
            con.M_DOUGONG,          # 斗栱
            con.M_BAWANGQUAN,       # 霸王拳
            con.M_CORNERBEAM,       # 老角梁
            con.M_MENZAN,           # 门簪
            con.M_RAILING,          # 栏杆(望柱、净瓶)
        ):
            # 直接使用原始贴图，不做改变
            pass
        if paintMat in (
            con.M_ZHILINGCHUANG, # 直棂窗
        ):
            mat = aData.mat_green # 绿漆
        
    
    # 1. 酱油漆样式
    if paintStyle == '1':
        if paintMat in (
            con.M_PAINT,            # 上漆
            con.M_QUETI,            # 雀替
            con.M_FANG_CHUANCHA,    # 穿插枋
            con.M_FANG_JIN,         # 金枋
            con.M_FANG_EBIG,        # 大额枋
            con.M_FANG_ESMALL,      # 小额枋
            con.M_BOARD_YOUE,       # 由额垫板
            con.M_PILLER_HEAD,      # 柱头
            con.M_BOARD_WALLHEAD,   # 走马板
            con.M_WINDOW,           # 窗框
            con.M_DOOR_RING,        # 绦环板
            con.M_DOOR_BOTTOM,      # 裙板
            con.M_FANG_PINGBAN,     # 平板枋
            con.M_BAWANGQUAN,       # 霸王拳
            con.M_BEAM_PAINT,       # 梁架-上漆
            con.M_ROOF_PAINT,       # 屋顶-上漆
            con.M_CORNERBEAM,       # 老角梁
            con.M_CORNERBEAM_S,     # 子角梁
            con.M_RAFTER,           # 檐椽
            con.M_FLYRAFTER,        # 飞椽
            con.M_WANGBAN,          # 望板
            con.M_SHANHUA,          # 山花板
            con.M_ZHILINGCHUANG,    # 直棂窗
            con.M_MENZAN,           # 门簪
            con.M_RAILING,          # 栏杆(望柱、净瓶)
        ):
            mat = aData.mat_oilpaint
            slot = 1
        if paintMat in (
            con.M_WALL, # 墙-抹灰
            con.M_BOARD_DG, # 栱垫板
            con.M_BOARD_DG_S, # 栱垫板-小
        ):
            mat = aData.mat_dust_wall
            slot = 1
        if paintMat in (
            con.M_WINDOW_INNER, # 棂心
        ):
            mat = aData.mat_geshanxin 
            slot = 1
        if paintMat in (
            con.M_LINXIN_WAN, # 万字锦
        ):
            mat = aData.mat_geshanxin_wan 
            slot = 1
        if paintMat in (
            con.M_FANG_TIAOYAN, # 挑檐枋
            con.M_FANG_DGCONNECT, # 拽枋
            con.M_DOUGONG, # 斗栱
        ):
            mat = aData.mat_wood
        

    # 2. override，全局覆盖的着色方式
    if paintStyle == '2': 
        mat = aData.mat_override

    if mat == None:
        # 如果mat未成功匹配，表示无需切换材质，直接返回
        return paintObj

    paintObj = __paintMat(paintObj, mat, slot)

    return paintObj

# 设置材质，并进行相应几何处理
def __paintMat(object:bpy.types.Object,
              mat=None,
              slot=None,):    
    aData:tmpData = bpy.context.scene.ACA_temp

    if mat == aData.mat_override:
        object = __setTileMat(object,
                     mat,
                     uvType=uvType.CUBE,
                     cubesize=2)
        return object

    # 简单平铺的材质
    if mat in (
        aData.mat_oilpaint,          # 漆.通用
        aData.mat_wood,         # 木材材质
        aData.mat_rock,         # 石材材质
        aData.mat_stone,        # 石头材质
        aData.mat_brick_1,      # 方砖缦地
        aData.mat_brick_2,      # 条砖竖铺
        aData.mat_brick_3,      # 条砖横铺
        aData.mat_dust_wall,    # 墙体抹灰
        aData.mat_gold,         # 漆.金
        aData.mat_green,        # 漆.绿
    ):
        object = __setTileMat(object,
                     mat,
                     uvType=uvType.CUBE,
                     cubesize=2)
    
    # 三交六椀隔心
    if mat == aData.mat_geshanxin:
        object = __setTileMat(object,
                     mat,
                     uvType=uvType.CUBE,
                     cubesize=0.1)  
    
    # 万字锦
    if mat == aData.mat_geshanxin_wan:
        object = __setTileMat(object,
                     mat,
                     uvType=uvType.CUBE,
                     cubesize=0.3)  

    # 挑檐枋工王云，仅在前后两面做彩画
    if mat in (
        aData.mat_paint_cloud,
    ):
        object = __paintFrontBack(object,mat)

    # 平板枋走龙，在前后左右四面做彩画
    if mat in (
        aData.mat_paint_walkdragon, 
    ):
        object = __paintAround(object,mat)
    
    # 拉伸填充的材质
    if mat in (
        aData.mat_paint_doorring,   # 隔扇绦环
        aData.mat_paint_door,       # 隔扇壶门
    ):
        object = __setTileMat(object,
                     mat,
                     uvType=uvType.CUBE,
                     scaleToBounds=True)
    
    # 梁枋彩画
    if mat in (
        aData.mat_paint_beam_big,
        aData.mat_paint_beam_small,
    ):
        object = __setFangMat(object,mat)

    # 由额垫板，公母草贴图
    if mat == aData.mat_paint_grasscouple:
        object = __setYOUE(object,mat)

    # 柱头贴图
    if mat == aData.mat_paint_pillerhead:
        object = __setPillerHead2(object,mat)

    # 栱垫板(小号和普通版)
    if mat in (aData.mat_paint_dgfillboard,
               aData.mat_paint_dgfillboard_s):
        object = __setDgBoard(object,mat)

    # 檐椽
    if mat == aData.mat_paint_rafter:
        object = __setRafterMat(object,mat)
    
    # 飞椽
    if mat == aData.mat_paint_flyrafter:
        object = __setFlyrafterMat(object,mat)
    
    # 望板
    if mat == aData.mat_paint_wangban:
        object = __setWangban(object,mat)

    # 子角梁，龙肚子
    if mat == aData.mat_paint_ccb:
       object = __setCCB(object,mat)

    # 山花板
    if mat == aData.mat_paint_shanhua:
        object = __setShanhua(object,mat)

    # 设置材质slot
    if slot != None:
        __replaceSlot(object,toSlot=slot)

    return object

# 设置材质，并进行相应几何处理
def setMat(object:bpy.types.Object,
              mat:bpy.types.Object,
              override=False,
              single=False):
    # 非mesh对象直接跳过
    if object == None: return
    if object.type not in ('MESH','CURVE'):
        return
    
    # 如果已经有材质，且未声明override，则不做材质
    if object.active_material != None \
        and not override:
        # 不做任何改变
        return
    
    aData:tmpData = bpy.context.scene.ACA_temp

    # 彩画样式控制
    buildingObj = utils.getAcaParent(
        object,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    if bData.paint_style == '1':
        # 素体，无彩画
        if mat in (
            aData.mat_paint_walkdragon,     # 平板枋走龙
            aData.mat_paint_beam_big,       # 梁枋
            aData.mat_paint_beam_small,     # 梁枋
            aData.mat_paint_doorring,       # 隔扇绦环
            aData.mat_paint_door,           # 隔扇壶门
            aData.mat_paint_grasscouple,    # 由额垫板公母草
            aData.mat_paint_pillerhead,     # 柱头贴图
            aData.mat_paint_ccb,            # 子角梁，龙肚子
            aData.mat_paint_rafter,         # 檐椽
            aData.mat_paint_flyrafter,      # 飞椽
            aData.mat_ccfang,               # 穿插枋
            aData.mat_cornerbeam,           # 老角梁
            aData.mat_queti,                # 雀替
        ):
            mat = aData.mat_oilpaint

        if mat in (
            aData.mat_dougong,              # 斗栱
            aData.mat_paint_cloud,          # 挑檐枋
        ):
            mat = aData.mat_wood

    # 简单平铺的材质
    if mat in (
        aData.mat_oilpaint,     # 漆.通用
        aData.mat_wood,         # 木材材质
        aData.mat_rock,         # 石材材质
        aData.mat_stone,        # 石头材质
        aData.mat_brick_1,      # 方砖缦地
        aData.mat_brick_2,      # 条砖竖铺
        aData.mat_brick_3,      # 条砖横铺
        aData.mat_dust_wall,    # 墙体抹灰
        aData.mat_gold,         # 漆.金
    ):
        __setTileMat(object,
                     mat,
                     uvType=uvType.CUBE,
                     cubesize=2)
    
    # 三交六椀隔心
    if mat == aData.mat_geshanxin:
        __setTileMat(object,
                     mat,
                     uvType=uvType.CUBE,
                     cubesize=0.1)
        
    # 切换酱油色
    if bData.paint_style == '0':
        if mat in (aData.mat_oilpaint,        # 漆.通用
                aData.mat_dust_wall,      # 墙色抹灰
                aData.mat_geshanxin,     # 三交六椀隔心
                ):
            # 酱油色
            __replaceSlot(object,toSlot=1)    

    # 挑檐枋工王云，仅在前后两面做彩画
    if mat in (
        aData.mat_paint_cloud,
    ):
        object = __paintFrontBack(object,mat)

    # 平板枋走龙，在前后左右四面做彩画
    if mat in (
        aData.mat_paint_walkdragon, 
    ):
        object = __paintAround(object,mat)
    
    # 拉伸填充的材质
    if mat in (
        aData.mat_paint_doorring,   # 隔扇绦环
        aData.mat_paint_door,       # 隔扇壶门
    ):
        __setTileMat(object,
                     mat,
                     uvType=uvType.CUBE,
                     scaleToBounds=True)
    
    # 梁枋彩画
    if mat in (
        aData.mat_paint_beam_big,
        aData.mat_paint_beam_small,
    ):
        __setFangMat(object,mat)

    # 由额垫板，公母草贴图
    if mat == aData.mat_paint_grasscouple:
        object = __setYOUE(object,mat)

    # 柱头贴图
    if mat == aData.mat_paint_pillerhead:
        object = __setPillerHead2(object,mat)

    # 栱垫板(小号和普通版)
    if mat in (aData.mat_paint_dgfillboard,
               aData.mat_paint_dgfillboard_s):
        if bData.paint_style != '0':
            object = __setDgBoard(object,mat)

    # 檐椽
    if mat == aData.mat_paint_rafter:
        object = __setRafterMat(object,mat)
    
    # 飞椽
    if mat == aData.mat_paint_flyrafter:
        object = __setFlyrafterMat(object,mat)
    
    # 望板
    if mat == aData.mat_paint_wangban:
        if bData.paint_style != '0':
            __setWangban(object,mat)

    # 子角梁，龙肚子
    if mat == aData.mat_paint_ccb:
        __setCCB(object,mat)

    # 山花板
    if mat == aData.mat_paint_shanhua:
        __setShanhua(object,mat)
        pass

    return object

# 拷贝目标对象的材质
# 复制所有材质
def __copyMaterial(fromObj:bpy.types.Object,
                 toObj:bpy.types.Object,
                 single=False):
    if toObj.type in ('MESH','CURVE'):
        toObj.data.materials.clear()
        for mat in fromObj.data.materials:
            if single:
                mat = mat.copy()
            toObj.data.materials.append(mat)

    return

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

# 设置对象使用的材质编号
def __setMatByID(
        object:bpy.types.Object,
        id=0,
):
    bm = bmesh.new()
    bm.from_mesh(object.data)
    for face in bm.faces:
        face.material_index = id
    bm.to_mesh(object.data)
    bm.free()
    return

# 平铺材质
def __setTileMat(
        object:bpy.types.Object,
        mat:bpy.types.Object,
        single=False,
        uvType=uvType.CUBE,
        cubesize=2,
        correctAspect = True,
        scaleToBounds = False,
):
    # 绑定材质
    __copyMaterial(mat,object,single)

    # 平铺类材质默认使用Cube Projection
    # 也可以传入希望的uv方式
    UvUnwrap(object,
             uvType,
             cubesize=cubesize,
             correctAspect=correctAspect,
             scaleToBounds=scaleToBounds)
    
    return object

# 檐椽展UV
def __setRafterMat(rafter:bpy.types.Object,mat):
    # 绑定檐椽材质
    __copyMaterial(mat,rafter)

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
def __setFlyrafterMat(flyrafter:bpy.types.Object,mat):
    # 绑定飞椽材质
    __copyMaterial(mat,flyrafter)

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

# 计算柱头贴图的高度
# 依据大额枋、由额垫板、小额枋的高度计算
def __setPillerHead(pillerObj:bpy.types.Object,
                    mat:bpy.types.Object):
    buildingObj = utils.getAcaParent(
        pillerObj,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK

    # 为了使用静态的PBR贴图的同时，动态的控制柱头贴图高度    
    # 将柱子分为上中下分别裁切、拼接    
    # 柱身对象
    pillerBodyObj = utils.copySimplyObject(
        pillerObj,singleUser=True)
    # 柱头对象
    pillerHeadObj = utils.copySimplyObject(
        pillerObj,singleUser=True)
    # 柱顶对象
    pillerTopObj = utils.copySimplyObject(
        pillerObj,singleUser=True)
    pillerParts=[]
    pillerParts.append(pillerBodyObj)
    pillerParts.append(pillerHeadObj)
    pillerParts.append(pillerTopObj)
    
    # 刷新，否则出现柱头计算错误
    utils.updateScene()

    # 计算柱头高度（大额枋/小额枋下皮）
    fangHeight = con.EFANG_LARGE_H*dk
    if bData.use_smallfang:
        fangHeight += (con.BOARD_YOUE_H*dk
            + con.EFANG_SMALL_H*dk)
    # 裁切柱头
    pCut = pillerObj.matrix_world @ Vector((
        0,0,pillerObj.dimensions.z-fangHeight))
    utils.addBisect(
        object=pillerBodyObj,
        pCut=pCut,
        clear_inner=True,
        direction='V',
        use_fill=False,
    )
    utils.addBisect(
        object=pillerHeadObj,
        pCut=pCut,
        clear_outer=True,
        direction='V',
        use_fill=False,
    )

    # 裁切柱顶（剪掉顶面，只保留圆筒形状，做贴图）
    pCut = pillerObj.matrix_world @ Vector((
        0,0,pillerObj.dimensions.z-0.02))
    utils.addBisect(
        object=pillerTopObj,
        pCut=pCut,
        clear_outer=True,
        direction='V',
        use_fill=False,
    )
    utils.addBisect(
        object=pillerHeadObj,
        pCut=pCut,
        clear_inner=True,
        direction='V',
        use_fill=False,
    )

    # 绑定柱头材质
    __copyMaterial(mat,pillerHeadObj)
    __copyMaterial(aData.mat_oilpaint,pillerBodyObj)
    __copyMaterial(aData.mat_oilpaint,pillerTopObj)
    # 重新展UV
    UvUnwrap(pillerHeadObj,uvType.CYLINDER)
    UvUnwrap(pillerBodyObj,uvType.CUBE,cubesize=2)
    UvUnwrap(pillerTopObj,uvType.CUBE,cubesize=2)
    # 旋转45度，让金龙面对前方
    pillerHeadObj.rotation_euler.z = math.radians(45)

    # 表面平滑
    for part in pillerParts:
        utils.shaderSmooth(part)
    # 移除原有的柱身，并将柱名称让给新对象
    pillerName = pillerObj.name
    bpy.data.objects.remove(pillerObj)
    # 柱身、柱头合并
    newPiller = utils.joinObjects(pillerParts,pillerName,cleanup=True)
    
    return newPiller

# 重构，不再用bisect拼接的方式，直接控制vertex group
# 计算柱头贴图的高度
# 依据大额枋、由额垫板、小额枋的高度计算
def __setPillerHead2(pillerObj:bpy.types.Object,
                    mat:bpy.types.Object):
    buildingObj = utils.getAcaParent(
        pillerObj,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK

    # 计算柱头高度（大额枋/小额枋下皮）
    fangHeight = con.EFANG_LARGE_H*dk
    if bData.use_smallfang:
        fangHeight += (con.BOARD_YOUE_H*dk
            + con.EFANG_SMALL_H*dk)

    # 2、选择中段
    utils.focusObj(pillerObj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    # 选择中段中段控制采用了对象的vertex group
    vertex_group_name = 'neck'  # 在模板中预定义的vertex group名称
    pillerObj.vertex_groups.active = \
        pillerObj.vertex_groups[vertex_group_name]
    bpy.ops.object.vertex_group_select()

    # 3、拉伸柱头贴图区
    bpy.ops.transform.translate(
            value=(0,0,-fangHeight))
    
    # 4、退出编辑状态，以便后续获取uvmap
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return pillerObj

# 已废弃，栱垫板改为PBR模式，改用__setDgBoard方法
# # 设置垫拱板的重复次数，根据斗栱攒数计算
# def __setDgCount(object:bpy.types.Object):
#     # 载入数据
#     buildingObj = utils.getAcaParent(
#         object,con.ACA_TYPE_BUILDING)
#     bData:acaData = buildingObj.ACA_data

#     # 设置材质中的斗栱攒数
#     fang_length = object.dimensions.x
#     count = round(fang_length / bData.dg_gap)
#     __setMatValue(
#         mat=object.active_material,
#         inputName='count',
#         value=count)
    
# 判断枋子使用的AB配色
def __setFangMat(fangObj:bpy.types.Object,
                 mat:bpy.types.Object):
    # 根据开间位置的尺寸，选择不同的matID
    # 0-XL、1-L、2-M、3-S、4-异色XL、5-异色L、6-异色M、7-异色S
    matID = 0
    
    # 分解获取柱子编号
    fangID = fangObj.ACA_data['fangID']
    setting = fangID.split('#')
    pFrom = setting[0].split('/')
    pFrom_x = int(pFrom[0])
    pFrom_y = int(pFrom[1])
    pTo = setting[1].split('/')
    pTo_x = int(pTo[0])
    pTo_y = int(pTo[1])

    # 计算为第几间？
    buildingObj = utils.getAcaParent(fangObj,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    # 前后檐
    if pFrom_y == pTo_y:
        roomIndex = (pFrom_x+pTo_x-1)/2
        n = int((bData.x_rooms+1)/2)%2
    # 两山
    elif pFrom_x == pTo_x:
        roomIndex = (pFrom_y+pTo_y-1)/2
        n = int((bData.y_rooms+1)/2)%2

    ''' 根据n来判断是否是明间,比如，
    5间时,奇数间(1,3,5)应该用正色
    7间时,偶数间(2,4,6)应该用正色'''
    if roomIndex%2 == n:
        matID = 4
    else:
        matID = 0

    # 判断额枋长度
    fangLength = fangObj.dimensions.x
    if fangLength < 1.8:
        # 超短款
        matID += 3
    elif fangLength < 2.8:
        # 短款
        matID += 2
    elif fangLength < 5:
        # 中款
        matID += 1

    # 绑定材质
    __copyMaterial(fromObj=mat,toObj=fangObj)
    # 选择slot
    __setMatByID(fangObj,matID)
    # 展UV
    UvUnwrap(fangObj,
             uvType.CUBE,
             scaleToBounds=True)

    # 设置槫头坐龙
    if (fangObj.name.startswith('挑檐桁')
        or fangObj.name.startswith('正心桁')):
        __setTuanHead(fangObj)
    
    return fangObj

# 设置槫头坐龙
def __setTuanHead(tuan:bpy.types.Object):
    # 追加槫头坐龙材质
    aData:tmpData = bpy.context.scene.ACA_temp
    matHeadDragon = aData.mat_paint_tuanend.active_material
    tuan.data.materials.append(matHeadDragon)
    matIndex = len(tuan.material_slots)-1

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
        left:Vector = face.normal - leftNormal
        if right.length < 1 or left.length < 1:
            face.material_index = matIndex
    bm.to_mesh(tuan.data)
    bm.free()

    # 从资产中传递预定义的UV
    __copyUV(
        fromObj=aData.mat_paint_tuanend,
        toObj= tuan,
    )
    return

# 设置由额垫板公母草贴图
# 由额垫板贴图采用三段式，中间为横向平铺的公母草，两端为箍头
# 按照箍头、公母草贴图的XY比例，计算公母草的横向平铺次数
def __setYOUE(youeObj:bpy.types.Object,
              mat:bpy.types.Object):
    # 使用垫板模板替换原对象
    youeNewObj = utils.copyObject(mat,singleUser=True)
    utils.replaceObject(youeObj,youeNewObj,delete=True)
    
    # 2、选择中段
    utils.focusObj(youeNewObj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    # 选择中段中段控制采用了对象的vertex group
    vertex_group_name = 'body'  # 在模板中预定义的vertex group名称
    youeNewObj.vertex_groups.active = \
        youeNewObj.vertex_groups[vertex_group_name]
    bpy.ops.object.vertex_group_select()

    # 3、中段的mesh缩放
    a = 0.463       # 箍头长度
    l1 = mat.dimensions.x
    l2 = youeNewObj.dimensions.x
    x1 = l1 - a*2
    x2 = l2 - a*2
    scale = (x2/l2)/(x1/l1)
    # 注意，这里缩放时要根据全局的旋转角度来判断
    rot = youeNewObj.matrix_world.to_euler().z
    if abs(rot) < 0.01:
        bpy.ops.transform.resize(
            value=(scale,1,1))
    else:
        bpy.ops.transform.resize(
            value=(1,scale,1))
    
    # 4、退出编辑状态，以便后续获取uvmap
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # 5、中段的UV缩放
    b = 1.737       # 每一段的最佳长度（以0.16的垫板高度，按贴图尺寸826*76转换）
    scale = round(x2/b)
    # scale取整后，最小不能小于1
    if scale == 0:
        scale = 1
    # 模版文件中重复了3次，进行还原
    scale = scale / 3
    uvMap = youeNewObj.data.uv_layers['UVMap']
    # 这里用fixcenter的方式，避免影响箍头的uv（箍头UV预定义为满铺）
    # vertex group无法直接传递给uvmap，因为uvmap对应到面（faceloop）
    # 一个vertex可能对应对个uv
    __ScaleUV(uvMap,scale=(scale,1),pivot=(0.5,0.5),fixcenter=True)
    
    return youeNewObj

# 栱垫板贴图
def __setDgBoard(dgBoardObj:bpy.types.Object,
                 mat:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(
        dgBoardObj,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    
    # 计算斗栱攒数
    totalLength = dgBoardObj.dimensions.x
    # 补偿float精度
    totalLength += 0.001
    # 向下取整，宜疏不宜密（与builddougong.__buildDougong方法统一）
    count = math.floor(totalLength/bData.dg_gap)
    # count最小不能为0，否则导致异常
    if count == 0 : count = 1
    boardLength = totalLength/count

    # 在每攒斗栱之间摆放栱垫板
    newDgBoardList = []
    for n in range(count):
        newDgBoard = utils.copySimplyObject(mat)
        # 适配原栱垫板的尺寸（可能斗口不同）
        newDgBoard.dimensions = (
            boardLength,
            dgBoardObj.dimensions.y,
            dgBoardObj.dimensions.z)
        # 后续会将新的栱垫板替换旧的栱垫板
        # 所以location应该是相对旧的栱垫板的定位
        # 所以y=z=0
        newDgBoard.location.x = (
            (n+0.5)*boardLength-totalLength/2)
        newDgBoard.location.y = 0
        newDgBoard.location.z = 0
        utils.applyTransform(newDgBoard,use_scale=True)
        newDgBoardList.append(newDgBoard)

    # 合并栱垫板
    joinedDgBoard = utils.joinObjects(newDgBoardList)
    utils.applyTransform(joinedDgBoard,use_location=True)
    utils.replaceObject(
        dgBoardObj,
        joinedDgBoard,
        delete=True)

    return joinedDgBoard

# 前后两面做slot1的材质
# 如，挑檐枋工王云
def __paintFrontBack(paintObj:bpy.types.Object,
                   mat:bpy.types.Object):
    # 复制所有的材质
    # 默认所有面应用slot0的材质（大青）
    __copyMaterial(mat,paintObj)

    # 找到前后面，做材质slot1的彩画
    bm = bmesh.new()
    bm.from_mesh(paintObj.data)
    # Z轴为向量比较基准
    axisY = Vector((0,1,0))
    # 选择法线类似的所有面，0.1是在blender里尝试的经验值
    for face in bm.faces:
        # 根据向量的点积判断方向，正为同向，0为垂直，负为反向
        dir = face.normal.dot(axisY)
        if abs(dir) > 0:
            # 设置为slot1的彩画
            face.material_index = 1
    bm.to_mesh(paintObj.data)
    bm.free()

    # 更新UV，适配对象高度的满铺
    cubeHeight = paintObj.dimensions.z
    UvUnwrap(paintObj,
             type=uvType.CUBE,
             cubesize=cubeHeight)
    return paintObj

# 四周做彩画
# 如，挑檐枋工王云贴图
def __paintAround(fangObj:bpy.types.Object,
                   mat:bpy.types.Object):
    # 复制所有的材质
    # 默认所有面应用slot0的材质（大青）
    __copyMaterial(mat,fangObj)

    # 找到前后左右四面，做材质slot1（彩画）
    bm = bmesh.new()
    bm.from_mesh(fangObj.data)
    # Z轴为向量比较基准
    axisZ = Vector((0,0,1))
    # 选择法线类似的所有面，0.1是在blender里尝试的经验值
    for face in bm.faces:
        # 根据向量的点积判断方向，正为同向，0为垂直，负为反向
        dir = face.normal.dot(axisZ)
        if abs(dir) == 0:
            # 设置为slot1的彩画
            face.material_index = 1
    bm.to_mesh(fangObj.data)
    bm.free()

    # 更新UV，适配对象高度的满铺
    cubeHeight = fangObj.dimensions.z
    UvUnwrap(fangObj,
             type=uvType.CUBE,
             cubesize=cubeHeight)
    return fangObj

# 望板材质，底面刷漆
def __setWangban(wangban:bpy.types.Object,
                 mat:bpy.types.Object):
    __copyMaterial(mat,wangban)

    # 找到所有的底面
    bm = bmesh.new()
    bm.from_mesh(wangban.data)
    # -Z轴为向量比较基准
    negZ = Vector((0,0,-1))
    # 选择法线类似的所有面，0.1是在blender里尝试的经验值
    for face in bm.faces:
        # 根据向量的点积判断方向，正为同向，0为垂直，负为反向
        dir = face.normal.dot(negZ)
        if dir > 0:
            # 设置为slot1的红漆
            face.material_index = 1
    bm.to_mesh(wangban.data)
    bm.free()

    # 展UV
    UvUnwrap(wangban,uvType.CUBE)
    return wangban

# 设置仔角梁龙肚子
def __setCCB(ccbObj:bpy.types.Object,
             mat:bpy.types.Object):
    __copyMaterial(mat,ccbObj)

    # 找到所有的底面
    bm = bmesh.new()
    bm.from_mesh(ccbObj.data)
    # -Z轴为向量比较基准
    negZ = Vector((0,0,-1))
    # 选择法线类似的所有面，0.1是在blender里尝试的经验值
    for face in bm.faces:
        # 根据向量的点积判断方向，正为同向，0为垂直，负为反向
        dir = face.normal.dot(negZ)
        if dir > 0.5:
            # 设置为slot1的龙肚子
            face.material_index = 1
    bm.to_mesh(ccbObj.data)
    bm.free()

    # 展uv
    # 适配仔角梁宽度
    ccbWidth = utils.getMeshDims(ccbObj).y
    UvUnwrap(ccbObj,
             uvType.CUBE,
             cubesize=ccbWidth,
             correctAspect=False)
    return ccbObj

# 设置山花板
def __setShanhua(shanhuaObj:bpy.types.Object,
             mat:bpy.types.Object):
    # 绑定材质，默认在slot0上，即红漆木板
    __copyMaterial(mat,shanhuaObj)

    # 对山花进行分割，博脊之上做彩画，博脊之下仍为纯红漆木材
    shanghuaTopObj = utils.copySimplyObject(
        shanhuaObj,singleUser=True
    )
    # 裁切
    buildingObj = utils.getAcaParent(
        shanhuaObj,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    scale = dk / con.DEFAULT_DK
    ridgeHeight = aData.ridgeFront_source.dimensions.z * scale
    # 裁剪一个博脊高度，并调整1/4桁径
    offset = (
            con.ROOFMUD_H*dk      # 灰泥
            + ridgeHeight         # 取到博脊上皮
            - con.XYB_WIDTH*dk/2  # 山花厚度加斜
    )
    # 裁剪点
    pCut = shanhuaObj.matrix_world @ Vector((
        0,0,offset))
    utils.addBisect(
        object=shanghuaTopObj,
        pCut=pCut,
        clear_outer=True,
        direction='V',
        use_fill=False,
    )

    # 找到所有的底面
    bm = bmesh.new()
    bm.from_mesh(shanghuaTopObj.data)
    # X轴为向量比较基准
    negZ = Vector((1,0,0))
    # 选择法线类似的所有面，0.1是在blender里尝试的经验值
    for face in bm.faces:
        # 根据向量的点积判断方向，正为同向，0为垂直，负为反向
        dir = face.normal.dot(negZ)
        if abs(dir) > 0.5:
            # 设置为slot1的山花贴图
            face.material_index = 1
            face.select = True
    bm.to_mesh(shanghuaTopObj.data)
    bm.free()

    # 展uv,满铺拉伸
    UvUnwrap(shanghuaTopObj,
             uvType.CUBE,
             scaleToBounds=True,
             remainSelect=True)
    
    # 裁剪下侧
    utils.addBisect(
        object=shanhuaObj,
        pCut=pCut,
        clear_inner=True,
        direction='V',
        use_fill=False,
    )
    
    # 合并
    utils.joinObjects([shanhuaObj,shanghuaTopObj],
                      cleanup=True)
    return shanhuaObj

# 切换材质slot
def __replaceSlot(obj:bpy.types.Object,
                  fromSlot=None,
                  toSlot=0,):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for face in bm.faces:
        # 如果指定fromSlot，则判断原材质是否匹配
        if (fromSlot != None and 
            face.material_index != fromSlot):
                # 不匹配原材质，不做改变
                pass
        else:
            face.material_index = toSlot
    bm.to_mesh(obj.data)
    bm.free()
    return

# 根据琉璃瓦作配色
# 根据用户从panel上选择的bData.tile_style，切换obj的材质slot
# 0-黄琉璃
# 1-黄琉璃绿剪边
# 2-绿琉璃
# 3-绿琉璃黄剪边
def setGlazeStyle(paintObj:bpy.types.Object,
                  resetUV=True):
    # 载入数据
    aData:tmpData = bpy.context.scene.ACA_temp
    buildingObj,bData,objData = utils.getRoot(paintObj)
    paintName = paintObj.data.name

    # 2. override，全局覆盖的着色方式
    paintStyle = bData.paint_style
    if paintStyle == '2': 
        mat = aData.mat_override
        paintObj = __paintMat(paintObj, mat)
        return

    # 1、瓦面（筒瓦/板瓦）颜色
    tileColorIndex = int(bData.tile_color) 
    glazeMain = [
        aData.flatTile_source,      # 板瓦
        aData.circularTile_source,  # 筒瓦
    ]
    for obj in glazeMain:
        if obj.data.name in paintName:
            # 配色从slot0切换到slot1
            __replaceSlot(paintObj,0,tileColorIndex)
            paintObj.active_material_index = tileColorIndex

    # 2、剪边/屋脊的颜色
    # 2.1、单一材质
    tileAltColorIndex = int(bData.tile_alt_color)
    glazeList1 = [
        aData.ridgeTop_source,      # 正脊
        aData.ridgeBack_source,     # 垂脊兽后
        aData.ridgeFront_source,    # 垂脊兽前
        aData.chiwen_source,        # 螭吻
        aData.taoshou_source,       # 套兽
        aData.paoshou_0_source,     # 跑兽
        aData.paoshou_1_source,     # 跑兽
        aData.paoshou_2_source,     # 跑兽
        aData.paoshou_3_source,     # 跑兽
        aData.paoshou_4_source,     # 跑兽
        aData.paoshou_5_source,     # 跑兽
        aData.paoshou_6_source,     # 跑兽
        aData.paoshou_7_source,     # 跑兽
        aData.paoshou_8_source,     # 跑兽
        aData.paoshou_9_source,     # 跑兽
        aData.paoshou_10_source,    # 跑兽
        aData.baoding_source,       # 宝顶
    ] 
    for obj in glazeList1:
        if obj.data.name in paintName:
            # 配色从slot0切换到slot1
            __replaceSlot(
                paintObj,0,tileAltColorIndex)
            paintObj.active_material_index = tileAltColorIndex
    # 2.2、两个材质
    glazeList2 = [
        aData.dripTile_source,      # 滴水
        aData.eaveTile_source,      # 勾头
        aData.ridgeEnd_source,      # 端头盘子
        aData.chuishou_source,      # 垂兽
    ]
    for obj in glazeList2:
        if obj.data.name in paintName:
            # 两个材质切换到绿色
            __replaceSlot(
                paintObj,0,tileAltColorIndex*2)
            __replaceSlot(
                paintObj,1,tileAltColorIndex*2+1)
            paintObj.active_material_index = tileAltColorIndex*2

    # 重新展UV，在modifier的基础上平铺
    if resetUV:
        setGlazeUV(paintObj)
    return

# 对琉璃对象重展开UV
# 在对象应用了modifier的基础上，进行材质的平铺
def setGlazeUV(paintObj:bpy.types.Object,
    uvType = uvType.CUBE):
    UvUnwrap(
        object=paintObj,
        type=uvType,
        cubesize=200,
        onlyActiveMat=True)
    return