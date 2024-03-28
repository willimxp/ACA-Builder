# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   屋瓦的营造
import bpy
import bmesh
import math
from mathutils import Vector,Euler,Matrix

from . import utils
from . import buildRoof
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import acaLibrary

# 创建瓦作层根节点
# 如果已存在根节点，则一概清空重建
# 暂无增量式更新，或局部更新
def __setTileRoot(buildingObj:bpy.types.Object)->bpy.types.Object:
    # 新建或清空根节点
    tileRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_TILE_ROOT)
    if tileRootObj != None:
        utils.deleteHierarchy(tileRootObj,del_parent=True)
    # 创建屋顶根对象
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    tileRootObj = bpy.context.object
    tileRootObj.name = "瓦作层"
    tileRootObj.parent = buildingObj
    tileRootObj.ACA_data['aca_obj'] = True
    tileRootObj.ACA_data['aca_type'] = con.ACA_TYPE_TILE_ROOT
    # 以挑檐桁下皮为起始点
    bData : acaData = buildingObj.ACA_data # 载入数据
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    tile_base = bData.platform_height \
                + bData.piller_height
    # 如果有斗栱，抬高斗栱高度
    if bData.use_dg:
        tile_base += bData.dg_height
    else:
        # 以大梁抬升
        tile_base += con.BEAM_HEIGHT*pd
    tileRootObj.location = (0,0,tile_base)
        
    return tileRootObj

# 绘制正身瓦垄线
def __drawTileCurve(buildingObj:bpy.types.Object,
                           purlin_pos):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )

    # 综合考虑桁架上铺椽、望、灰泥后的效果，主要保证整体线条的流畅
    # 同时与梁思成绘制的图纸进行了拟合，所以也有一定的推测成分
    tileCurveVerts = []

    # 第1点：从正身飞椽的中心当开始，上移半飞椽+大连檐
    # 获取飞椽对象
    flyrafterObj: bpy.types.Object = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_FLYRAFTER_FB
    )
    # 获取飞椽头坐标
    flyrafterHead_co = utils.getObjectHeadPoint(
                            flyrafterObj,
                            eval=False,
                            is_symmetry=(True,True,False)
                        )
    # 向上位移：半飞椽+大连檐，并且加斜到飞椽方向
    offset = (con.FLYRAFTER_H/2 + con.DALIANYAN_H)*dk
    offset_v = Vector((0,0,offset))
    offset_v.rotate(Euler((-flyrafterObj.rotation_euler.y,0,0),'XYZ'))
    # 添加第1点
    curve_p1 = flyrafterHead_co * Vector((0,1,1)) # 投影到X平面
    curve_p1 += offset_v
    tileCurveVerts.append(curve_p1)

    # 第3-5点，从举架定位点做偏移
    for n in range(len(purlin_pos)):
        # 向上位移:半桁径+椽径+望板高+灰泥层高
        offset = (con.HENG_COMMON_D/2 + con.YUANCHUAN_D 
                  + con.WANGBAN_H + con.ROOFMUD_H)*dk
        point = purlin_pos[n]*Vector((0,1,1))+Vector((0,0,offset))
        tileCurveVerts.append(point)

    # 创建瓦垄曲线
    tileCurve = utils.addCurveByPoints(
            CurvePoints=tileCurveVerts,
            name='正身瓦垄线',
            root_obj=tileRootObj,
            tilt=math.radians(90),
            order_u=4, # 取4级平滑，让坡面曲线更加流畅
            )
    # 设置origin
    utils.setOrigin(tileCurve,curve_p1)
    return tileCurve

# 绘制翼角瓦垄线
def __drawCornerCurve(buildingObj:bpy.types.Object,
                           purlin_pos):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )

    cornerCurveVerts = []
    
    # 第1点：檐口线终点，按照冲三翘四的理论值计算（与子角梁解耦）
    # 大连檐
    dlyObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_DLY_FB)
    p0 = Vector(dlyObj.location)

    # 上檐出（檐椽平出+飞椽平出）
    ex = con.YANCHUAN_EX*dk + con.FLYRAFTER_EX*dk
    # 斗栱平出
    if bData.use_dg:
        ex += bData.dg_extend
    # 冲出，大连檐仅冲1椽
    ex += bData.chong * con.YUANCHUAN_D * dk
    # 避让角梁，向内1/4角梁，见汤崇平书籍的p196
    shift = con.JIAOLIANG_Y/4*dk * math.sqrt(2)
    x = bData.x_total/2 + ex - shift
    y = bData.y_total/2 + ex - con.QUETAI*dk
    qiqiao = bData.qiqiao * con.YUANCHUAN_D * dk
    z = dlyObj.location.z + qiqiao
    p1 = Vector((x,y,z))
    # 相对大连檐位移
    offset = Vector((0,con.DALIANYAN_H*dk/2,
                     -con.DALIANYAN_Y*dk/2-con.QUETAI*dk))
    offset.rotate(dlyObj.rotation_euler)
    p1 += offset
    cornerCurveVerts.append(p1)

    # 第3-5点，从举架定位点做偏移
    for n in range(len(purlin_pos)):
        # 向上位移:半桁径+椽径+望板高+灰泥层高
        offset2 = (con.HENG_COMMON_D/2 + con.YUANCHUAN_D 
                  + con.WANGBAN_H + con.ROOFMUD_H)*dk
        point = purlin_pos[n]*Vector((0,1,1))+Vector((0,0,offset2))
        # 叠加起翘影响，X坐标对齐p1点
        point += Vector((x,0,qiqiao))
        cornerCurveVerts.append(point)

    # 绘制翼角瓦垄线
    cornerCurve = utils.addCurveByPoints(
            CurvePoints=cornerCurveVerts,
            name='翼角瓦垄线',
            resolution = con.CURVE_RESOLUTION,
            root_obj=tileRootObj
        )
    # 设置origin
    utils.setOrigin(cornerCurve,p0+offset)
    return cornerCurve

# 绘制檐口线（直达子角梁中心），做为翼角瓦檐口终点
def __drawEaveCurve(buildingObj:bpy.types.Object,
                    purlin_pos):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    # 大连檐
    dlyObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,con.ACA_TYPE_RAFTER_DLY_FB)

    eaveCurveVerts = []

    # 第1点：大连檐中心
    p1 = Vector(dlyObj.location)
    eaveCurveVerts.append(p1)

    # 第2点：翼角起翘点，X与下金桁对齐
    p2 = p1 + Vector((purlin_pos[1].x,0,0))
    eaveCurveVerts.append(p2)

    # 第4点：檐口线终点，按照冲三翘四的理论值计算（与子角梁解耦）
    # 上檐出（檐椽平出+飞椽平出）
    ex = con.YANCHUAN_EX*dk + con.FLYRAFTER_EX*dk
    # 斗栱平出
    if bData.use_dg:
        ex += bData.dg_extend
    # 冲出，大连檐仅冲1椽
    ex += bData.chong * con.YUANCHUAN_D * dk
    # 避让角梁，向内1/4角梁，见汤崇平书籍的p196
    shift = con.JIAOLIANG_Y/4*dk * math.sqrt(2)
    x = bData.x_total/2 + ex - shift
    y = bData.y_total/2 + ex - con.QUETAI*dk
    qiqiao = bData.qiqiao * con.YUANCHUAN_D * dk
    z = p2.z + qiqiao
    p4 = Vector((x,y,z))
    
    # 第3点：檐口线中点
    p3 = Vector((
        (p2.x+p4.x)/2,   # 水平线上取中点
        p2.y,   # 与起点水平
        (p2.z+p4.z)/8)) # 略做了手工调整
    eaveCurveVerts.append(p3)
    eaveCurveVerts.append(p4)

    # 绘制檐口线
    eaveCurve = utils.addCurveByPoints(
            CurvePoints=eaveCurveVerts,
            name='檐口瓦垄线',
            resolution = con.CURVE_RESOLUTION,
            root_obj=tileRootObj
        )
    # 设置origin
    utils.setOrigin(eaveCurve,p1)
    
    # 位移到大连檐外沿
    offset = Vector((0,con.DALIANYAN_H*dk/2,
                     -con.DALIANYAN_Y*dk/2-con.QUETAI*dk))
    offset.rotate(dlyObj.rotation_euler)
    eaveCurve.location += offset

    return eaveCurve

# 绘制瓦面网格
def __drawTileGrid(buildingObj,rafter_pos):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )

    # 瓦垄宽度
    tileWidth = 0.4
    # 瓦片长度
    tileLength = 0.5
    # 载入瓦片资源
    flatTile:bpy.types.Object = acaLibrary.loadAssets(
        "板瓦",tileRootObj,hide=False)
    circularTile:bpy.types.Object = acaLibrary.loadAssets(
        "筒瓦",tileRootObj,hide=False)
    eaveTile:bpy.types.Object = acaLibrary.loadAssets(
        "瓦当",tileRootObj,hide=False)
    dripTile:bpy.types.Object = acaLibrary.loadAssets(
        "滴水",tileRootObj)

    # 0、生成三条辅助线，这是后续所有计算的基础
    # 绘制正身坡线
    TileCurve:bpy.types.Curve = __drawTileCurve(buildingObj,rafter_pos)
    # 绘制檐口线
    EaveCurve = __drawEaveCurve(buildingObj,rafter_pos)
    # 绘制翼角瓦垄线
    CornerCurve = __drawCornerCurve(buildingObj,rafter_pos)

    # 1、计算瓦垄的数量
    # 半侧通面阔 + 檐出
    roofWidth = bData.x_total/2+ con.YANCHUAN_EX*dk
    # 斗栱出跳
    if bData.use_dg:
        roofWidth += bData.dg_extend
    # 飞椽出
    if bData.use_flyrafter:
        roofWidth += con.FLYRAFTER_EX*dk
    # 翼角冲出
    roofWidth += bData.chong * con.YUANCHUAN_D * dk
    # 瓦垄数
    tileCols = math.ceil(roofWidth / tileWidth)
    # 坡面长度
    # 似乎是2.8版本中新增的方法
    # https://docs.blender.org/api/current/bpy.types.Spline.html#bpy.types.Spline.calc_length
    roofLength = TileCurve.data.splines[0].calc_length()
    # 瓦层数
    tileRows = math.ceil(roofLength /tileLength)+1

    # 2、生成瓦面网格
    # 这里采用几何节点实现，利用了resample curve节点，可以生成均匀分布的网格
    # 而python中暂未找到在curve上均匀分配的API
    # 连接资产blender文件中的瓦面对象，直接放到“瓦作层”节点下
    tileGrid:bpy.types.Object = acaLibrary.loadAssets(
        "瓦面",tileRootObj,hide=False)
    # 瓦面要与辅助线重合
    tileGrid.location = TileCurve.location
    # 输入修改器参数
    gnMod:bpy.types.NodesModifier = \
        tileGrid.modifiers.get('GeometryNodes')
    # 几何节点修改器的传参比较特殊，封装了一个方法
    utils.setGN_Input(gnMod,"正身瓦线",TileCurve)
    utils.setGN_Input(gnMod,"檐口线",EaveCurve)
    utils.setGN_Input(gnMod,"翼角瓦线",CornerCurve)
    utils.setGN_Input(gnMod,"瓦片列数",tileCols)
    utils.setGN_Input(gnMod,"瓦片行数",tileRows)    

    # 3、平铺瓦片对象
    # 应用modifier
    utils.applyAllModifer(tileGrid)
    # 在瓦面网格中布瓦
    bm = bmesh.new()   # create an empty BMesh
    bm.from_mesh(tileGrid.data)   # fill it in from a Mesh
    for f in bm.faces:
              
        # # 做法一：基于face的normal，并强制矫正
        # # https://blender.stackexchange.com/questions/46566/aligning-plane-normal-vector-side-to-face-a-point-python
        # # 固定Z轴向上，追踪Y轴在法线上的转动
        # # 获取面的normal
        # normal_eular = f.normal.to_track_quat('Z','Y').to_euler()
        # # 这个normal不能直接用，翼角瓦口没有正对檐口，偏转到了45度方向
        # # 强制矫正瓦片，强制瓦片统一向前
        # tile_rotation = (normal_eular.x,0,math.radians(180))
        # tileObj.rotation_euler = tile_rotation
        # # 缺陷：翼角瓦没有沿檐口线斜切
                
        # 做法二：效果完美，尽管没有完全理解原理
        # 基于edge，构造Matrix变换矩阵，用于瓦片的定位
        # https://blender.stackexchange.com/questions/177218/make-bone-roll-match-a-face-vertex-normal/177331#177331
        # 取面上第一条边（沿着坡面）
        e = f.edges[0]
        # 边的向量(归一化)，做为Y轴
        y = (e.verts[1].co - e.verts[0].co).normalized()
        # 平均相邻面的法线，做为边的法线，做为Z轴
        z = sum((f.normal for f in e.link_faces), Vector()).normalized()
        # Y/Z轴做叉积，得到与之垂直的X轴
        x = y.cross(z)
        # 坐标系转置（行列互换，以复合blender的坐标系要求）
        M = Matrix((x, y, z)).transposed().to_4x4()

        # 排布板瓦
        flatTileCopy = utils.copySimplyObject(
            sourceObj=flatTile,
            name='板瓦',
            parentObj=tileGrid,
        )
        # 排布筒瓦
        circularTileCopy = utils.copySimplyObject(
            sourceObj=circularTile,
            name='筒瓦',
            parentObj=tileGrid,
        )  
        
        # 板瓦定位，从网格面中心偏移半个瓦垄（实际落在网格线上，也保证了瓦垄居中）
        M.translation = f.calc_center_median() - Vector((tileWidth/2,0,0))
        flatTileCopy.matrix_local = M
        # 筒瓦定位，在网格面中心点
        M.translation = f.calc_center_median()
        circularTileCopy.matrix_local = M
        
        # 四向对称
        utils.addModifierMirror(
            object=flatTileCopy,
            mirrorObj=tileRootObj,
            use_axis=(True,True,False),
            use_bisect=(False,True,False)
        )    
        utils.addModifierMirror(
            object=circularTileCopy,
            mirrorObj=tileRootObj,
            use_axis=(True,True,False),
            use_bisect=(False,True,False)
        )

    # 隐藏辅助对象
    utils.hideObj(tileGrid)
    utils.hideObj(flatTile)
    utils.hideObj(circularTile)
    utils.hideObj(eaveTile)
    utils.hideObj(dripTile)

    return 

# 对外的统一调用接口
# 一次性重建所有的瓦做
def buildTile(buildingObj: bpy.types.Object):
    utils.outputMsg("buildTile starting...")
    # 确认聚焦在根目录中
    utils.setCollection(con.ROOT_COLL_NAME)
    # 暂存cursor位置，注意要加copy()，否则传递的是引用
    old_loc = bpy.context.scene.cursor.location.copy()
    # 添加或清空根节点
    __setTileRoot(buildingObj)
    # 清理垃圾数据
    utils.delOrphan()
    utils.outputMsg("Rafter Tile root added")
    utils.redrawViewport()

    # 载入数据
    bData : acaData = buildingObj.ACA_data

    # 计算桁檩定位点
    purlin_pos = buildRoof.__getPurlinPos(buildingObj)
    # 如果有斗栱，剔除挑檐桁
    # 在梁架、椽架、角梁的计算中不考虑挑檐桁
    rafter_pos = purlin_pos.copy()
    if bData.use_dg:
        del rafter_pos[0]

    # 绘制瓦面网格
    __drawTileGrid(buildingObj,rafter_pos)
    utils.outputMsg("Tile Grid added")

    # 恢复cursor位置
    bpy.context.scene.cursor.location = old_loc 
    # 重新聚焦根节点
    utils.focusObj(buildingObj)
    