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
    # 屋顶层根节点
    roofRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_ROOF_ROOT) 
    # 新建或清空根节点
    tileRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_TILE_ROOT)
    if tileRootObj != None:
        utils.deleteHierarchy(tileRootObj,del_parent=True)
    # 创建屋顶根对象
    bpy.ops.object.empty_add(
        type='PLAIN_AXES',location=(0,0,0))
    tileRootObj = bpy.context.object
    tileRootObj.name = "瓦作层"
    tileRootObj.parent = roofRootObj
    tileRootObj.ACA_data['aca_obj'] = True
    tileRootObj.ACA_data['aca_type'] = con.ACA_TYPE_TILE_ROOT
        
    return tileRootObj

# 绘制正身瓦垄线
# 前后檐direction=‘X'
# 两山direction=’Y‘
def __drawTileCurve(buildingObj:bpy.types.Object,
                    purlin_pos,
                    direction='X'):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )

    if direction == 'X':
        tileCurve_name = "前后正身坡线"
        dly_type = con.ACA_TYPE_RAFTER_DLY_FB
        proj_v = Vector((0,1,1))
    else:
        tileCurve_name = "两山正身坡线"
        dly_type = con.ACA_TYPE_RAFTER_DLY_LR
        proj_v = Vector((1,0,1))

    # 综合考虑桁架上铺椽、望、灰泥后的效果，主要保证整体线条的流畅
    # 同时与梁思成绘制的图纸进行了拟合，所以也有一定的推测成分
    tileCurveVerts = []

    # 第1点：从正身飞椽的中心当开始，上移半飞椽+大连檐
    # 大连檐中心
    dlyObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,dly_type)
    curve_p1 = Vector(dlyObj.location)
    # 位移到大连檐外沿，瓦当滴水向外延伸
    if direction == 'X':
        offset = Vector((0,con.DALIANYAN_H*dk/2,
            -con.DALIANYAN_Y*dk/2-con.EAVETILE_EX*dk))
    else:
        offset = Vector((0,con.DALIANYAN_H*dk/2,
            con.DALIANYAN_Y*dk/2+con.EAVETILE_EX*dk))
    offset.rotate(dlyObj.rotation_euler)
    curve_p1 += offset
    tileCurveVerts.append(curve_p1)

    # 第3-5点，从举架定位点做偏移
    for n in range(len(purlin_pos)):
        # 歇山的山面只做到金桁高度（踏脚木位置）
        if bData.roof_style == '2' \
            and direction == 'Y' \
            and n>1: continue
        # 向上位移:半桁径+椽径+望板高+灰泥层高
        offset = (con.HENG_COMMON_D/2 + con.YUANCHUAN_D 
                  + con.WANGBAN_H + con.ROOFMUD_H)*dk
        point = purlin_pos[n]*proj_v+Vector((0,0,offset))
        tileCurveVerts.append(point)

    # 创建瓦垄曲线
    tileCurve = utils.addCurveByPoints(
            CurvePoints=tileCurveVerts,
            name=tileCurve_name,
            root_obj=tileRootObj,
            tilt=math.radians(90),
            order_u=4, # 取4级平滑，让坡面曲线更加流畅
            )
    # 设置origin
    utils.setOrigin(tileCurve,curve_p1)
    return tileCurve

# 绘制侧边瓦垄线
# 前后檐direction=‘X'
# 两山direction=’Y‘
def __drawSideCurve(buildingObj:bpy.types.Object,
                purlin_pos,
                direction='X'):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    
    if direction == 'X':
        sideCurve_name = "前后翼角坡线"
        dly_type = con.ACA_TYPE_RAFTER_DLY_FB
        proj_v = Vector((0,1,1))
        proj_v2 = Vector((1,0,1))
        # 闪避1/4角梁
        shift = Vector((-con.JIAOLIANG_Y/4*dk * math.sqrt(2),0,0))
    else:
        sideCurve_name = "两山翼角坡线"
        dly_type = con.ACA_TYPE_RAFTER_DLY_LR
        proj_v = Vector((1,0,1))
        proj_v2 = Vector((0,1,1))
        # 闪避1/4角梁
        shift = Vector((0,-con.JIAOLIANG_Y/4*dk * math.sqrt(2),0))

    sideCurveVerts = []
    
    # 第1点：檐口线终点
    # 大连檐
    dlyObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,dly_type)
    p0 = Vector(dlyObj.location)
    # 瓦当滴水向外延伸（相对大连檐位移）
    if direction == 'X':
        offset = Vector((0,
            con.DALIANYAN_H*dk/2,
            -con.DALIANYAN_Y*dk/2-con.EAVETILE_EX*dk))
    else:
        offset = Vector((0,
            con.DALIANYAN_H*dk/2,
            con.DALIANYAN_Y*dk/2+con.EAVETILE_EX*dk))
    offset.rotate(dlyObj.rotation_euler)

    # 硬山悬山
    if bData.roof_style in ('3','4'):       
        x = utils.getMeshDims(dlyObj).x / 2
        y = dlyObj.location.y
        z = dlyObj.location.z
        qiqiao = 0
        p1 = Vector((x,y,z))+offset
        sideCurveVerts.append(p1)

    # 庑殿、歇山按照冲三翘四的理论值计算（与子角梁解耦）
    if bData.roof_style in ('1','2'):
        # 上檐出（檐椽平出+飞椽平出）
        ex = con.YANCHUAN_EX*dk + con.FLYRAFTER_EX*dk
        # 斗栱平出
        if bData.use_dg:
            ex += bData.dg_extend
        # 冲出，大连檐仅冲1椽
        ex += bData.chong * con.YUANCHUAN_D * dk
        x = bData.x_total/2 + ex
        y = bData.y_total/2 + ex
        qiqiao = bData.qiqiao * con.YUANCHUAN_D * dk
        z = dlyObj.location.z + qiqiao
        p1 = Vector((x,y,z)) + shift
        p1 += offset
        sideCurveVerts.append(p1)

    # 第3-5点，从举架定位点做偏移
    for n in range(len(purlin_pos)):
        # 歇山的山面只做到金桁高度（踏脚木位置）
        if bData.roof_style == '2' \
            and direction == 'Y' \
            and n>1: continue
        # 向上位移:半桁径+椽径+望板高+灰泥层高+起翘
        offset2 = Vector((0,0,
                (con.HENG_COMMON_D/2 + con.YUANCHUAN_D 
                + con.WANGBAN_H + con.ROOFMUD_H)*dk+qiqiao))
        point = purlin_pos[n]*proj_v + offset2
        # 叠加起翘影响，X坐标对齐p1点
        point += Vector((x,y,qiqiao)) * proj_v2
        sideCurveVerts.append(point)

    # 绘制翼角瓦垄线
    sideCurve = utils.addCurveByPoints(
            CurvePoints=sideCurveVerts,
            name=sideCurve_name,
            resolution = con.CURVE_RESOLUTION,
            root_obj=tileRootObj
        )
    utils.hideObj(sideCurve)
    # 设置origin
    utils.setOrigin(sideCurve,p0+offset)
    return sideCurve

# 绘制檐口线（直达子角梁中心），做为翼角瓦檐口终点
def __drawEaveCurve(buildingObj:bpy.types.Object,
                    purlin_pos,
                    direction='X'):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    
    if direction == 'X':
        eaveCurve_name = "前后檐口瓦线"
        dly_type = con.ACA_TYPE_RAFTER_DLY_FB
        proj_v1 = Vector((1,0,0))
        # 闪避1/4角梁
        shift = Vector((-con.JIAOLIANG_Y/4*dk * math.sqrt(2),0,0))
    else:
        eaveCurve_name = "两山檐口瓦线"
        dly_type = con.ACA_TYPE_RAFTER_DLY_LR
        proj_v1 = Vector((0,1,0))
        # 闪避1/4角梁
        shift = Vector((0,-con.JIAOLIANG_Y/4*dk * math.sqrt(2),0))

    eaveCurveVerts = []

    # 第1点：大连檐中心
    # 大连檐
    dlyObj:bpy.types.Object = \
        utils.getAcaChild(buildingObj,dly_type)
    p1 = Vector(dlyObj.location)
    eaveCurveVerts.append(p1)

    # 第2点：翼角起翘点，X与下金桁对齐
    p2 = p1 + purlin_pos[1] * proj_v1
    eaveCurveVerts.append(p2)

    if bData.roof_style in ('3','4'):
        # 绘制檐口线
        CurvePoints = utils.setEaveCurvePoint(p1,p2,direction)
        eaveCurve = utils.addBezierByPoints(
                CurvePoints=CurvePoints,
                name=eaveCurve_name,
                resolution = con.CURVE_RESOLUTION,
                root_obj=tileRootObj
            )

    # 庑殿、歇山按照冲三翘四的理论值计算
    if bData.roof_style in ('1','2'):
        # 第3点：檐口线终点，按照冲三翘四的理论值计算（与子角梁解耦）
        # 上檐出（檐椽平出+飞椽平出）
        ex = con.YANCHUAN_EX*dk + con.FLYRAFTER_EX*dk
        # 斗栱平出
        if bData.use_dg:
            ex += bData.dg_extend
        # 冲出，大连檐仅冲1椽
        ex += bData.chong * con.YUANCHUAN_D * dk
        x = bData.x_total/2 + ex
        y = bData.y_total/2 + ex
        qiqiao = bData.qiqiao * con.YUANCHUAN_D * dk
        z = p2.z + qiqiao
        p3 = Vector((x,y,z)) + shift

        # 绘制檐口线
        CurvePoints = utils.setEaveCurvePoint(p2,p3,direction)
        eaveCurve = utils.addBezierByPoints(
                CurvePoints=CurvePoints,
                name=eaveCurve_name,
                resolution = con.CURVE_RESOLUTION,
                root_obj=tileRootObj
            )
        
        # 延长到P1点
        eaveCurveData:bpy.types.Curve = eaveCurve.data
        bpoints = eaveCurveData.splines[0].bezier_points
        bpoints.add(1)
        utils.transBezierPoint(bpoints[1],bpoints[2])
        utils.transBezierPoint(bpoints[0],bpoints[1])
        bpoints[0].co = p1

    # 设置origin
    utils.setOrigin(eaveCurve,p1)
    
    # 位移到大连檐外沿，瓦当滴水向外延伸
    if direction == 'X':
        offset = Vector((0,con.DALIANYAN_H*dk/2,
            -con.DALIANYAN_Y*dk/2-con.EAVETILE_EX*dk))
    else:
        offset = Vector((0,con.DALIANYAN_H*dk/2,
            con.DALIANYAN_Y*dk/2+con.EAVETILE_EX*dk))
    offset.rotate(dlyObj.rotation_euler)
    eaveCurve.location += offset

    return eaveCurve

# 计算瓦垄的数量
def __getTileCols(buildingObj:bpy.types.Object,direction='X'):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    # 瓦垄宽度
    tileWidth = bData.tile_width

    if direction=='X':
        # 通面阔
        tongmiankuo = bData.x_total
    else:
        tongmiankuo = bData.y_total

    # 半侧通面阔 + 檐出
    roofWidth = tongmiankuo/2+ con.YANCHUAN_EX*dk

    # 斗栱、飞椽、冲出
    if bData.roof_style in ('3','4') and direction=='X':
        # 硬山、悬山的山面不出跳（檐面正常出跳）
        pass
    else:
        # 斗栱出跳
        if bData.use_dg:
            roofWidth += bData.dg_extend
        # 飞椽出
        if bData.use_flyrafter:
            roofWidth += con.FLYRAFTER_EX*dk
        # 翼角冲出
        roofWidth += bData.chong * con.YUANCHUAN_D * dk
    
    # 板瓦居中，所以多算半垄板瓦宽度
    roofWidth += tileWidth/2

    # 瓦垄数（完整的板瓦列数，包括居中的半列）
    tileCols = math.ceil(roofWidth / tileWidth)

    # 回写实际瓦垄宽度
    bData.tile_width_real = roofWidth / tileCols

    return tileCols

# 绘制瓦面网格，依赖于三条曲线的控制
def __drawTileGrid(
            buildingObj:bpy.types.Object,
            rafter_pos,
            direction='X'):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    # 瓦垄宽度
    tileWidth = bData.tile_width
    # 瓦片长度
    tileLength = bData.tile_length

    # 计算瓦垄的数量（包括居中列板瓦的半幅屋面列数）
    tileCols = __getTileCols(buildingObj,direction)

    # 在网格上以半垄划分，分别对应到板瓦和筒瓦
    GridCols = (tileCols+1)*2
    
    if direction == 'X':
        tileGrid_name = "前后檐瓦面"
    else:
        tileGrid_name = "两山瓦面"

    # 1、生成三条辅助线，这是后续所有计算的基础
    # 绘制正身坡线
    TileCurve:bpy.types.Curve = __drawTileCurve(
        buildingObj,rafter_pos,direction)
    # 绘制檐口线
    EaveCurve = __drawEaveCurve(buildingObj,
        rafter_pos,direction)
    # 绘制侧边瓦垄线
    SideCurve = __drawSideCurve(buildingObj,
        rafter_pos,direction)

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
    # 瓦面要与辅助线重合，并上移一个大连檐高度
    tileGrid.location = TileCurve.location
    tileGrid.name = tileGrid_name
    # 输入修改器参数
    gnMod:bpy.types.NodesModifier = \
        tileGrid.modifiers.get('GeometryNodes')
    # 几何节点修改器的传参比较特殊，封装了一个方法
    utils.setGN_Input(gnMod,"正身瓦线",TileCurve)
    utils.setGN_Input(gnMod,"檐口线",EaveCurve)
    utils.setGN_Input(gnMod,"翼角瓦线",SideCurve)
    utils.setGN_Input(gnMod,"瓦片列数",GridCols)
    utils.setGN_Input(gnMod,"瓦片行数",tileRows)  
    # 应用modifier
    utils.applyAllModifer(tileGrid)      

    return tileGrid

# 绘制瓦面的斜切boolean对象
# 分别可以适应庑殿与歇山屋瓦的裁剪（悬山、硬山不涉及）
# 庑殿沿着角梁、由戗裁剪，其中包含了推山的因素
# 歇山基于桁架形状裁剪，其中的歇山转折点做了特殊计算
def __drawTileBool(
        buildingObj:bpy.types.Object,
        purlin_cross_points,
        name='tile.bool',
        direction='X'):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )

    # 任意添加一个对象，具体几何数据在bmesh中建立
    bpy.ops.mesh.primitive_cube_add(
        location=(0,0,0)
    )
    tileboolObj = bpy.context.object
    tileboolObj.name = name
    tileboolObj.parent = tileRootObj

    # 创建bmesh
    bm = bmesh.new()
    # 各个点的集合
    vectors = []
    z0 = - dk * 10 # 出檐后的檐口低于root_obj,所以要进行补偿
    # 从子角梁头算起
    ex = 6*dk # 向外延伸，确保包裹住瓦片
    roof_qiao_point = bData.roof_qiao_point + Vector((ex,ex,0))

    vectors.insert(0,(roof_qiao_point.x,roof_qiao_point.y,z0))
    vectors.append((roof_qiao_point.x,-roof_qiao_point.y,z0))

    # 循环添加由戗节点
    for n in range(len(purlin_cross_points)):
        # 这里不加copy，原始值就会被异常修改，python传值还是传指针太麻烦
        cutPoint = purlin_cross_points[n].copy()
        # 歇山转折点特殊处理
        if bData.roof_style == '2':
            if n==1:
                if direction == 'X':
                    cutPoint.x = purlin_cross_points[-1].x
                    # 保持45度斜切，简单的从翼角做X/Y相同的位移
                    cutPoint.y = roof_qiao_point.y \
                        - (roof_qiao_point.x-cutPoint.x)
                else:
                    cutPoint.x = purlin_cross_points[1].x
            if n > 1:
                continue
        vectors.insert(0,(cutPoint.x,cutPoint.y,z0))
        vectors.append((cutPoint.x,-cutPoint.y,z0))
    
    # 摆放点
    vertices=[]
    for n in range(len(vectors)):
        if n==0:
            vert = bm.verts.new(vectors[n])
        else:
            # 挤出
            return_geo = bmesh.ops.extrude_vert_indiv(bm, verts=[vert])
            vertex_new = return_geo['verts'][0]
            del return_geo
            # 给挤出的点赋值
            vertex_new.co = vectors[n]
            # 交换vertex给下一次循环
            vert = vertex_new
        vertices.append(vert)

    # 创建面
    for n in range(len(vertices)//2-1): #注意‘/’可能是float除,用'//'进行整除
        bm.faces.new((
            vertices[n],vertices[n+1], # 两根椽头
            vertices[-n-2],vertices[-n-1] # 两根椽尾
        ))

    # 挤出厚度
    height = purlin_cross_points[-1].z + 100*dk 
    return_geo = bmesh.ops.extrude_face_region(bm, geom=bm.faces)
    verts = [elem for elem in return_geo['geom'] if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0,height))
    #ps，这个挤出略有遗憾，没有按照每个面的normal进行extrude

    # 确保face normal朝向
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(tileboolObj.data)
    tileboolObj.data.update()
    bm.free()

    # 添加镜像
    mod = tileboolObj.modifiers.new(name='mirror', type='MIRROR')
    mod.use_axis[0] = True
    mod.use_axis[1] = False
    mod.mirror_object = tileRootObj

    return tileboolObj

# 在face上放置瓦片
def __setTile(
        sourceObj,name,Matrix,
        offset,parent,mirrorObj,
        isNeedBool=False,
        boolObj=None,
        isBoolInside=False
):
    TileCopy = utils.copySimplyObject(
        sourceObj=sourceObj,
        name=name,
        parentObj=parent,
    )  
    # 滴水定位，从网格面中心偏移半个瓦垄（实际落在网格线上，也保证了瓦垄居中）
    TileCopy.matrix_local = Matrix
    offset.rotate(TileCopy.rotation_euler)
    TileCopy.location += offset

    # todo：瓦片也可以在join以后的整体上做镜像和裁剪
    # 这里暂时保留用户不想join的可选余地（如，更方便做异色剪边等）
    # 添加镜像
    utils.addModifierMirror(
        object=TileCopy,
        mirrorObj=mirrorObj,
        use_axis=(True,True,False),
        use_bisect=(True,True,False)
    ) 

    if isNeedBool:
        # 添加boolean modifier
        mod:bpy.types.BooleanModifier = TileCopy.modifiers.new("由戗裁剪","BOOLEAN")
        mod.object = boolObj
        mod.solver = con.BOOLEAN_TYPE # FAST / EXACT
        if isBoolInside:
            mod.operation = 'INTERSECT'
        else:
            mod.operation = 'DIFFERENCE'

    return TileCopy   

# 在网格上平铺瓦片
def __arrayTileGrid(buildingObj:bpy.types.Object,
                rafter_pos,
                tileGrid:bpy.types.Object,
                direction='X'):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    # 瓦垄宽度
    tileWidth = bData.tile_width
    # 瓦片长度
    tileLength = bData.tile_length
    # 计算瓦垄的数量
    tileCols = __getTileCols(buildingObj,direction)
    GridCols = tileCols*2+1

    # 载入瓦片资源
    flatTile:bpy.types.Object = utils.copyObject(
        bData.flatTile_source,singleUser=True)
    circularTile:bpy.types.Object = utils.copyObject(
        bData.circularTile_source,singleUser=True)
    eaveTile:bpy.types.Object = utils.copyObject(
        bData.eaveTile_source,singleUser=True)
    dripTile:bpy.types.Object = utils.copyObject(
        bData.dripTile_source,singleUser=True)
    utils.applyAllModifer(flatTile)
    utils.applyAllModifer(circularTile)
    utils.applyAllModifer(eaveTile)
    utils.applyAllModifer(dripTile)
    utils.showObj(flatTile)
    utils.showObj(circularTile)
    utils.showObj(eaveTile)
    utils.showObj(dripTile)

    # 构造一个裁剪对象，做boolean
    # 瓦面不适合像椽架那样做三个bisect面的切割
    # 因为推山导致的由戗角度交叉，使得三个bisect面也有交叉，导致上下被裁剪的过多
    tile_bool_obj = __drawTileBool(
        buildingObj,rafter_pos,direction=direction)

    # 檐面与山面的差异
    if direction=='X':
        # boolean用difference，向外切
        isBoolInside=False
        # 瓦片走向取第一条边
        dir_index = 0
        offset_aside = Vector((bData.tile_width_real/4,tileLength/2,0))
    else:
        tileGrid = utils.flipNormal(tileGrid)
        # boolean用intersec，向内切
        isBoolInside=True
        # 瓦片走向取第二条边
        dir_index = 1
        offset_aside = Vector((-bData.tile_width_real/4,tileLength/2,0))

    # 庑殿、歇山做裁剪
    isNeedBool = False
    if bData.roof_style in ('1','2'):
        isNeedBool = True

    bm = bmesh.new()   # create an empty BMesh
    bm.from_mesh(tileGrid.data)   # fill it in from a Mesh
    tileList = []
    for f in bm.faces:                
        # 基于edge，构造Matrix变换矩阵，用于瓦片的定位
        # https://blender.stackexchange.com/questions/177218/make-bone-roll-match-a-face-vertex-normal/177331#177331
        # 取面上第一条边（沿着坡面）
        e = f.edges[dir_index]
        # 边的向量(归一化)，做为Y轴
        y = (e.verts[1].co - e.verts[0].co).normalized()
        # 平均相邻面的法线，做为边的法线，做为Z轴
        z = sum((f.normal for f in e.link_faces), Vector()).normalized()
        # Y/Z轴做叉积，得到与之垂直的X轴
        x = y.cross(z)
        # 坐标系转置（行列互换，以复合blender的坐标系要求）
        M = Matrix((x, y, z)).transposed().to_4x4()
        M.translation = f.calc_center_median()
        
        # 排布板瓦，仅在偶数列排布
        if (f.index%GridCols) % 2 == 0:
            tileObj = __setTile(
                sourceObj=flatTile,
                name='板瓦',
                Matrix=M,
                offset=offset_aside.copy(),
                parent=tileGrid,
                mirrorObj=tileRootObj,
                isNeedBool=isNeedBool,
                boolObj=tile_bool_obj,
                isBoolInside=isBoolInside
            )
            tileList.append(tileObj)

        # 排布筒瓦，技术列排布
        if (f.index%GridCols) % 2 == 1:
            tileObj = __setTile(
                sourceObj=circularTile,
                name='筒瓦',
                Matrix=M,
                offset=offset_aside.copy(),
                parent=tileGrid,
                mirrorObj=tileRootObj,
                isNeedBool=isNeedBool,
                boolObj=tile_bool_obj,
                isBoolInside=isBoolInside
            )
            tileList.append(tileObj)

        # 排布檐口瓦
        if f.index < GridCols:# 第一行
            # 排布滴水
            if f.index % 2 == 0:
                tileObj = __setTile(
                    sourceObj=dripTile,
                    name='滴水',
                    Matrix=M,
                    offset=offset_aside.copy(),
                    parent=tileGrid,
                    mirrorObj=tileRootObj,
                    isNeedBool=isNeedBool,
                    boolObj=tile_bool_obj,
                    isBoolInside=isBoolInside
                )
                tileList.append(tileObj) 

            # 排布瓦当
            if f.index % 2 == 1:
                tileObj = __setTile(
                    sourceObj=eaveTile,
                    name='瓦当',
                    Matrix=M,
                    offset=offset_aside.copy(),
                    parent=tileGrid,
                    mirrorObj=tileRootObj,
                    isNeedBool=isNeedBool,
                    boolObj=tile_bool_obj,
                    isBoolInside=isBoolInside
                )
                tileList.append(tileObj)

            

        # 最后再加一列板瓦收口
        # 如果用排山勾滴，无需这一列
        # if f.index % (tileCols-1) ==tileCols-2: # 最后一列
        #     # 排布板瓦
        #     tileObj = __setTile(
        #         sourceObj=flatTile,
        #         name='板瓦',
        #         Matrix=M,
        #         offset=offset_aside.copy() * Vector((-1,1,1)),
        #         parent=tileGrid,
        #         mirrorObj=tileRootObj,
        #         isNeedBool=isNeedBool,
        #         boolObj=tile_bool_obj,
        #         isBoolInside=isBoolInside
        #     ) 
        #     tileList.append(tileObj)

            # if f.index < tileCols-1:# 第一行
            #     # 排布滴水
            #     tileObj = __setTile(
            #         sourceObj=dripTile,
            #         name='滴水',
            #         Matrix=M,
            #         offset=offset_aside.copy() * Vector((-1,1,1)),
            #         parent=tileGrid,
            #         mirrorObj=tileRootObj,
            #         isNeedBool=isNeedBool,
            #         boolObj=tile_bool_obj,
            #         isBoolInside=isBoolInside
            #     )
            #     tileList.append(tileObj)
    
    utils.joinObjects(tileList)
        
    # 隐藏辅助对象
    utils.hideObj(tile_bool_obj)
    utils.hideObj(tileGrid)

    bpy.data.objects.remove(flatTile)
    bpy.data.objects.remove(circularTile)
    bpy.data.objects.remove(eaveTile)
    bpy.data.objects.remove(dripTile)

# 绘制歇山顶的前后檐垂脊曲线
def __drawFrontRidgeCurve(buildingObj:bpy.types.Object,
                    purlin_pos):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    ridgeCurveVerts = []
    # 垂脊横坐标，向内一垄
    ridge_x = purlin_pos[-1].x - bData.tile_width_real/2

    # 第1点：从正身飞椽的中心当开始，上移半飞椽+大连檐
    # 大连檐中心
    dlyObj:bpy.types.Object = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_RAFTER_DLY_FB)
    curve_p1 = Vector(dlyObj.location)
    # 位移到大连檐外沿，瓦当滴水向外延伸
    offset = Vector((ridge_x,con.DALIANYAN_H*dk/2,
        -con.DALIANYAN_Y*dk/2-con.EAVETILE_EX*dk))
    # offset = Vector((purlin_pos[-1].x ,#-bData.tile_width_real/2,
    #                  con.DALIANYAN_H*dk/2,#这里本来只需要调整半个大连檐，考虑到瓦的高度，调整到了一个大连檐
    #                  0))
    offset.rotate(dlyObj.rotation_euler)
    curve_p1 += offset
    ridgeCurveVerts.append(curve_p1)

    # 综合考虑桁架上铺椽、望、灰泥后的效果，主要保证整体线条的流畅
    # 从举架定位点做偏移
    for n in range(len(purlin_pos)):
        # 向上位移:半桁径+椽径+望板高+灰泥层高
        offset = (con.HENG_COMMON_D/2 + con.YUANCHUAN_D 
                  + con.WANGBAN_H + con.ROOFMUD_H)*dk
        point:Vector = purlin_pos[n]+Vector((0,0,offset))
        point.x = ridge_x #-bData.tile_width_real/2
        
        # 调整曲线终点，与正脊相交
        if n == len(purlin_pos)-1:
            # 调整2个垂脊筒的长度，多余的会在镜像时裁剪掉
            # 斜率近似认为45度
            ridgeFrontObj:bpy.types.Object = bData.ridgeFront_source
            offset = ridgeFrontObj.dimensions.x * 2
            point.y -= offset
            point.z += offset
        ridgeCurveVerts.append(point)
    
    # 创建瓦垄曲线
    ridgeCurve = utils.addCurveByPoints(
            CurvePoints=ridgeCurveVerts,
            name="歇山垂脊线",
            root_obj=tileRootObj,
            order_u=4, # 取4级平滑，让坡面曲线更加流畅
            )
    utils.setOrigin(ridgeCurve,ridgeCurveVerts[0])
    utils.hideObj(ridgeCurve)
    return ridgeCurve

# 沿曲线排布脊筒
def __arrayFrontRidge(buildingObj: bpy.types.Object,
                    sourceObj:bpy.types.Object,
                    ridgeCurve:bpy.types.Curve,
                    ridgeName='垂脊',
                 ):
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    
    # 复制垂脊对象
    frontRidgeObj = utils.copyObject(
        sourceObj=sourceObj,
        name=ridgeName,
        location=ridgeCurve.location,
        parentObj=tileRootObj)
    
    # 沿垂脊曲线平铺
    modArray:bpy.types.ArrayModifier = \
        frontRidgeObj.modifiers.new('曲线平铺','ARRAY')
    modArray.fit_type = 'FIT_CURVE'
    modArray.curve = ridgeCurve

    # 沿垂脊曲线变形
    modCurve: bpy.types.CurveModifier = \
        frontRidgeObj.modifiers.new('曲线变形','CURVE')
    modCurve.object = ridgeCurve

    # 四面镜像
    modMirror: bpy.types.MirrorModifier = \
        frontRidgeObj.modifiers.new('镜像','MIRROR')
    modMirror.mirror_object = tileRootObj
    modMirror.use_axis = (True,True,False)
    modMirror.use_bisect_axis = (False,True,False)

    return frontRidgeObj

# 营造排山勾滴
def __arraySideTile(buildingObj: bpy.types.Object,
                    sourceObj:bpy.types.Object,
                    ridgeCurve:bpy.types.Curve,
                    tileName='排山勾滴',
                 ):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    
    # 复制勾滴对象
    tileObj = utils.copyObject(
        sourceObj=sourceObj,
        name=tileName,
        location=ridgeCurve.location,
        parentObj=tileRootObj)
    # 旋转
    tileObj.rotation_euler.x = math.radians(90)
    
    # 沿垂脊曲线平铺
    modArray:bpy.types.ArrayModifier = \
        tileObj.modifiers.new('曲线平铺','ARRAY')
    modArray.fit_type = 'FIT_CURVE'
    modArray.curve = ridgeCurve
    modArray.use_relative_offset = False
    modArray.use_constant_offset = True
    modArray.constant_offset_displace = (-bData.tile_width,0,0)

    # 沿垂脊曲线变形
    modCurve: bpy.types.CurveModifier = \
        tileObj.modifiers.new('曲线变形','CURVE')
    modCurve.object = ridgeCurve
    modCurve.deform_axis = 'NEG_X'

    # 四面镜像
    modMirror: bpy.types.MirrorModifier = \
        tileObj.modifiers.new('镜像','MIRROR')
    modMirror.mirror_object = tileRootObj
    modMirror.use_axis = (True,True,False)
    modMirror.use_bisect_axis = (False,True,False)

    return tileObj

# 营造前后檐垂脊
def __buildFrontRidge(buildingObj: bpy.types.Object,
                 rafter_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )
    
    # 绘制垂脊曲线
    # 庑殿垂脊的做法，与歇山的戗脊做法合并
    # 歇山仅做到正心桁位置
    # 硬山悬山做到檐口位置
    frontRidgeCurve = __drawFrontRidgeCurve(
        buildingObj,rafter_pos)

    # 构造垂脊兽前
    frontRidgeObj = __arrayFrontRidge(buildingObj,
                    sourceObj=bData.ridgeFront_source,
                    ridgeCurve=frontRidgeCurve,
                    ridgeName='垂脊兽前')
    
    # 构造垂脊兽后
    backRidgeObj = __arrayFrontRidge(buildingObj,
                    sourceObj=bData.ridgeBack_source,
                    ridgeCurve=frontRidgeCurve,
                    ridgeName='垂脊兽后')
    
    # 留出跑兽的空间
    paoLength = 2
    backRidgeObj.location.x += paoLength
    frontRidgeObj.location.x += 1
    
    # 构造排山滴水
    dripTileObj = __arraySideTile(buildingObj,
                    sourceObj=bData.dripTile_source,
                    ridgeCurve=frontRidgeCurve,
                    tileName='排山滴水')
    
    eaveTileObj = __arraySideTile(buildingObj,
                    sourceObj=bData.eaveTile_source,
                    ridgeCurve=frontRidgeCurve,
                    tileName='排山勾头')
    
    # 排山勾头位移
    eaveTile:bpy.types.Object = bData.eaveTile_source
    eaveTileWidth = eaveTile.dimensions.x
    eaveTileLength = eaveTile.dimensions.y

    # 在curve modifier的影响下，X位移实际在Y方向，Z位移实际在X方向
    # 让排山勾头与檐面勾头“脚对脚”对齐
    eaveTileObj.location += Vector((
        # X方向（实际为Y方向），位移一个瓦层长，和半个勾头宽
        -bData.tile_length - eaveTileWidth/2,
        0,
        # Z方向（实际为X方向），位移（瓦垄宽-勾头宽）/2
        (bData.tile_width - eaveTileWidth)/2))

    # 排山滴水位移
    dripTileObj.location += Vector((
        # X方向（实际为Y方向），位移一个瓦层长，和半个勾头宽
        -bData.tile_length - eaveTileWidth/2 + bData.tile_width/2,
        0,
        # Z方向（实际为X方向），位移（瓦垄宽-勾头宽）/2
        (bData.tile_width - eaveTileWidth)/2))

    # 构造端头盘子
    ridgeEndObj = utils.copyObject(
        sourceObj=bData.ridgeEnd_source,
        name='端头盘子',
        location=frontRidgeCurve.location,
        parentObj=tileRootObj)
    
    # todo：定位暂未找到完美的算法
    ridgeEndObj.rotation_euler = (
        math.radians(26.5),
        0,
        math.radians(135)
    )
    # ridgeEndObj.location += Vector((
    #     -(bData.tile_width-eaveTileWidth)/2,
    #     -bData.tile_length,
    #     # 五举拿头，所以z的位移近似为Y的位移的一半
    #     (bData.tile_length+eaveTileWidth)/2))
    ridgeEndObj.location += Vector((
        -(bData.tile_width)/2,
        -bData.tile_length-eaveTileWidth/2,
        # 五举拿头，所以z的位移近似为Y的位移的一半
        (bData.tile_length+eaveTileWidth)/2))
    utils.addModifierMirror(
        object=ridgeEndObj,
        mirrorObj=tileRootObj,
        use_axis=(True,True,False),
    )
    

# 营造顶部正脊
def __buildTopRidge(buildingObj: bpy.types.Object,
                 rafter_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )

    # 正脊筒对象
    ridgeTopObj = bData.ridgeTop_source
    # 创建正脊
    # 向上位移:半桁径+椽径+望板高+灰泥层高
    offset = (con.HENG_COMMON_D/2 + con.YUANCHUAN_D 
                + con.WANGBAN_H + con.ROOFMUD_H)*dk
    zhengji_z = rafter_pos[-1].z + offset
    roofRidgeObj = utils.copyObject(
        sourceObj=ridgeTopObj,
        name="正脊",
        location=(0,0,zhengji_z),
        parentObj=tileRootObj)
    
    # 横向平铺
    l = roofRidgeObj.dimensions.x
    zhengji_length = rafter_pos[-1].x + l/2
    count = math.ceil(zhengji_length / l)
    span = zhengji_length/count
    roofRidgeObj.dimensions.x = span
    modArray:bpy.types.ArrayModifier = roofRidgeObj.modifiers.new('横向平铺','ARRAY')
    modArray.use_relative_offset = True
    modArray.relative_offset_displace = (1,0,0)
    modArray.count = count

    mod:bpy.types.MirrorModifier = roofRidgeObj.modifiers.new('X向对称','MIRROR')
    mod.mirror_object = tileRootObj
    mod.use_bisect_axis = (True,False,False)

    # 摆放螭吻
    chiwenObj = utils.copyObject(
        sourceObj=bData.chiwen_source,
        name='螭吻',
        location=(-rafter_pos[-1].x,0,zhengji_z),
        parentObj=tileRootObj)
    utils.addModifierMirror(
        object=chiwenObj,
        mirrorObj=tileRootObj,
        use_axis=(True,False,False)
    )
    return

# 营造博缝板
def __buildBofeng(buildingObj: bpy.types.Object,
                 rafter_pos):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    dk = bData.DK
    tileRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_TILE_ROOT
    )

    # 新绘制一条垂脊曲线
    bofengObj = __drawFrontRidgeCurve(
        buildingObj,rafter_pos)
    bofengObj.location.x = rafter_pos[-1].x
    bofengObj.name = '博缝板'
    
    # 转成mesh
    utils.focusObj(bofengObj)
    bpy.ops.object.convert(target='MESH')

    # 挤压成型
    bpy.ops.object.mode_set( mode = 'EDIT' ) 
    bm = bmesh.new()
    bm = bmesh.from_edit_mesh( bpy.context.object.data )

    # 曲线向下挤出博缝板高度
    bpy.ops.mesh.select_mode( type = 'EDGE' )
    bpy.ops.mesh.select_all( action = 'SELECT' ) 
    height = (con.HENG_COMMON_D + con.YUANCHUAN_D*4
                  + con.WANGBAN_H + con.ROOFMUD_H)*dk
    bpy.ops.mesh.extrude_edges_move(
        TRANSFORM_OT_translate={'value': (0.0, 0.0, 
                    -height)})

    return_geo = bmesh.ops.extrude_face_region(
            bm, geom=bm.faces)
    verts = [elem for elem in return_geo['geom'] 
             if type(elem) == bmesh.types.BMVert]
    bmesh.ops.translate(bm, 
            verts=verts, 
            vec=(con.BOFENG_WIDTH*dk, 0, 0))

    # Update & Destroy Bmesh
    bmesh.update_edit_mesh(bpy.context.object.data) 
    bm.free()  # free and prevent further access

    # Flip normals
    bpy.ops.mesh.select_all( action = 'SELECT' )
    bpy.ops.mesh.flip_normals() 

    # Switch back to Object at end
    bpy.ops.object.mode_set( mode = 'OBJECT' )

    # 应用镜像
    utils.addModifierMirror(
        object=bofengObj,
        mirrorObj=tileRootObj,
        use_axis=(True,True,False),
        use_bisect=(False,True,False)
    )

    # 应用裁剪
    return

# 营造屋脊
def __buildRidge(buildingObj: bpy.types.Object,
                 rafter_pos):
    # 营造顶部正脊
    __buildTopRidge(buildingObj,rafter_pos)
    
    # 营造前后垂脊（不涉及庑殿，自动判断硬山/悬山、歇山做法的不同）
    __buildFrontRidge(buildingObj,rafter_pos)

    # 营造博缝板
    __buildBofeng(buildingObj,rafter_pos)

    # 营造四角戗脊（包括庑殿的垂脊，自动判断歇山与庑殿做法的不同）

    # 歇山还有山花脊
    

# 对外的统一调用接口
# 一次性重建所有的瓦做
def buildTile(buildingObj: bpy.types.Object):
    # 添加或清空根节点
    __setTileRoot(buildingObj)
    # 清理垃圾数据
    utils.delOrphan()

    # 载入数据
    bData : acaData = buildingObj.ACA_data

    # 计算桁檩定位点
    purlin_pos = buildRoof.__getPurlinPos(buildingObj)
    # 如果有斗栱，剔除挑檐桁
    # 在梁架、椽架、角梁的计算中不考虑挑檐桁
    rafter_pos = purlin_pos.copy()
    if bData.use_dg:
        del rafter_pos[0]

    # 绘制前后坡瓦面网格
    tileGrid = __drawTileGrid(
        buildingObj,
        rafter_pos,
        direction='X')
    # 在网格上铺瓦
    utils.outputMsg("Building Tiles Front/Back...")
    __arrayTileGrid(
        buildingObj,
        rafter_pos,
        tileGrid,
        direction='X')
    
    # 仅庑殿、歇山做两山的瓦面
    if bData.roof_style in ('1','2'):
        # 绘制两山瓦面网格
        tileGrid = __drawTileGrid(
            buildingObj,
            rafter_pos,
            direction='Y')
        # 在网格上铺瓦
        utils.outputMsg("Building Tiles Left/Right...")
        __arrayTileGrid(
            buildingObj,
            rafter_pos,
            tileGrid,
            direction='Y')
        
    # 添加屋脊
    utils.outputMsg("Building Ridge...")
    __buildRidge(buildingObj,rafter_pos)

    # 重新聚焦根节点
    utils.focusObj(buildingObj)
    utils.outputMsg("Building Tiles down.")
    