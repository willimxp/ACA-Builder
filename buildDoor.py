# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   隔扇、槛窗的营造
import bpy
import math
from mathutils import Vector

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import utils

# 构建扇心
# 包括在槛框中嵌入的横披窗扇心
# 也包括在隔扇中嵌入的隔扇扇心
def __buildShanxin(parent,scale:Vector,location:Vector):
    # parent在横披窗中传入的wallproxy，但在隔扇中传入的geshanroot，所以需要重新定位
    # 载入数据
    buildingObj = utils.getAcaParent(parent,con.ACA_TYPE_BUILDING)
    wallproxy = utils.getAcaChild(buildingObj,con.ACA_TYPE_WALL)
    bData:acaData = buildingObj.ACA_data
    wData:acaData = wallproxy.ACA_data
    # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
    # todo：是采用用户可调整的设计值，还是取模版中定义的理论值？
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk

    # 仔边环绕
    # 创建一个平面，转换为curve，设置curve的横截面
    bpy.ops.mesh.primitive_plane_add(size=1,location=location)
    zibianObj = bpy.context.object
    zibianObj.name = '仔边'
    zibianObj.parent = parent
    # 三维的scale转为plane二维的scale
    zibianObj.rotation_euler.x = math.radians(90)
    zibianObj.scale = (
        scale.x - con.ZIBIAN_WIDTH*pd,
        scale.z - con.ZIBIAN_WIDTH*pd, # 旋转90度，原Zscale给Yscale
        0)
    # apply scale
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    # 转换为Curve
    bpy.ops.object.convert(target='CURVE')
    # 旋转所有的点45度，形成四边形
    bpy.ops.object.editmode_toggle()
    bpy.ops.curve.select_all(action='SELECT')
    bpy.ops.transform.tilt(value=math.radians(45))
    bpy.ops.object.editmode_toggle()
    # 设置Bevel
    zibianObj.data.bevel_mode = 'PROFILE'        
    zibianObj.data.bevel_depth = con.ZIBIAN_WIDTH/2  # 仔边宽度

    # 填充棂心
    lingxinObj = wData.lingxin_source
    if lingxinObj == None: return
    # 定位：从左下角排布array
    loc = (location.x-scale.x/2+con.ZIBIAN_WIDTH*pd,
            location.y,
            location.z-scale.z/2+con.ZIBIAN_WIDTH*pd)
    lingxin = utils.copyObject(
        sourceObj=lingxinObj,
        name='棂心',
        parentObj=parent,
        location=loc)
    # 计算平铺的行列数
    unitWidth,unitDeepth,unitHeight = utils.getMeshDims(lingxin)
    lingxingWidth = scale.x- con.ZIBIAN_WIDTH*2*pd
    linxingHeight = scale.z- con.ZIBIAN_WIDTH*2*pd
    rows = math.ceil(linxingHeight/unitHeight)+1 #加一，尽量让棂心紧凑，避免出现割裂
    row_span = linxingHeight/rows
    mod_rows = lingxin.modifiers.get('Rows')
    mod_rows.count = rows
    mod_rows.constant_offset_displace[2] = row_span

    cols = math.ceil(lingxingWidth/unitWidth)+1#加一，尽量让棂心紧凑，避免出现割裂
    col_span = lingxingWidth/cols
    mod_cols = lingxin.modifiers.get('Columns')
    mod_cols.count = cols
    mod_cols.constant_offset_displace[0] = col_span

# 构建槛框
# 基于输入的槛框线框对象
def __buildKanKuang(wallproxy):
    # 载入数据
    buildingObj = utils.getAcaParent(wallproxy,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    wData:acaData = wallproxy.ACA_data
    # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
    # todo：是采用用户可调整的设计值，还是取模版中定义的理论值？
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    use_KanWall = wData.use_KanWall
    pillerD = bData.piller_diameter
    # 分解槛框的长、宽、高
    frame_width,frame_deepth,frame_height = wallproxy.dimensions

    # region 1、下槛 ---------------------
    KanDownScale = Vector((frame_width, # 长度随面宽
                con.KAN_DOWN_DEEPTH * pd, # 厚0.3D
                con.KAN_DOWN_HEIGHT * pd, # 高0.8D
                ))
    KanDownLoc = Vector((0,0,con.KAN_DOWN_HEIGHT*pd/2))
    bpy.ops.mesh.primitive_cube_add(
                        size=1.0, 
                        location = KanDownLoc, 
                        scale= KanDownScale)
    KanDownObj = bpy.context.object
    KanDownObj.name = '下槛'
    KanDownObj.parent = wallproxy
    if use_KanWall:
        KanDownObj.hide_set(True) 
    # endregion 1、下槛 ---------------------
        
    # region 2、上槛 ---------------------
    KanUpScale = Vector((frame_width, # 长度随面宽
                con.KAN_UP_DEEPTH * pd, # 厚0.3D
                con.KAN_UP_HEIGHT * pd, # 高0.8D
                ))
    KanUpLoc = Vector((0,0,
            frame_height - con.KAN_UP_HEIGHT*pd/2))
    bpy.ops.mesh.primitive_cube_add(
                        size=1.0, 
                        location = KanUpLoc, 
                        scale= KanUpScale)
    bpy.context.object.name = '上槛'
    bpy.context.object.parent = wallproxy
    # endregion 2、上槛 ---------------------

    # region 3、中槛 ---------------------
    KanMidScale = Vector((frame_width, # 长度随面宽
                con.KAN_MID_DEEPTH * pd, # 厚0.3D
                con.KAN_MID_HEIGHT * pd, # 高0.8D
                ))
    KanMidLoc = Vector((0,0,
            wData.door_height + con.KAN_MID_HEIGHT*pd/2))
    bpy.ops.mesh.primitive_cube_add(
                        size=1.0, 
                        location = KanMidLoc, 
                        scale= KanMidScale)
    bpy.context.object.name = '中槛'
    bpy.context.object.parent = wallproxy
    # endregion 3、中槛 ---------------------

    # region 4、下抱框 ---------------------
    # 高度：从下槛上皮到中槛下皮
    BaoKuangDownHeight = (KanMidLoc.z - KanMidScale.z/2) \
        - (KanDownLoc.z + KanDownScale.z/2)
    BaoKuangDownScale = Vector((
                con.BAOKUANG_WIDTH * pd, # 宽0.66D
                con.BAOKUANG_DEEPTH * pd, # 厚0.3D
                BaoKuangDownHeight, 
                ))
    # 位置Z：从下槛+一半高度
    BaoKuangDown_z = (KanDownLoc.z + KanDownScale.z/2) \
                        + BaoKuangDownHeight/2
    # 位置X：半柱间距 - 半柱径 - 半抱框宽度
    BaoKuangDown_x = frame_width/2 - pillerD/2 - con.BAOKUANG_WIDTH*pd/2
    BaoKuangDownLoc = Vector((BaoKuangDown_x,0,BaoKuangDown_z))
    bpy.ops.mesh.primitive_cube_add(
                        size=1.0, 
                        location = BaoKuangDownLoc, 
                        scale= BaoKuangDownScale)
    BaoKuangDownObj = bpy.context.object
    BaoKuangDownObj.name = '下抱框'
    BaoKuangDownObj.parent = wallproxy
    # 添加mirror
    mod = BaoKuangDownObj.modifiers.new(name='mirror', type='MIRROR')
    mod.use_axis[0] = True
    mod.use_axis[1] = False
    mod.mirror_object = wallproxy
    # endregion 4、下抱框 ---------------------

    # region 5、上抱框 ---------------------
    # 高度：从上槛下皮到中槛上皮
    BaoKuangUpHeight = (KanUpLoc.z - KanUpScale.z/2) \
        - (KanMidLoc.z + KanMidScale.z/2)
    BaoKuangUpScale = Vector((
                con.BAOKUANG_WIDTH * pd, # 宽0.66D
                con.BAOKUANG_DEEPTH * pd, # 厚0.3D
                BaoKuangUpHeight, 
                ))
    # 位置Z：从上槛下皮，减一半高度
    BaoKuangUp_z = (KanUpLoc.z - KanUpScale.z/2) \
                        - BaoKuangUpHeight/2
    # 位置X：半柱间距 - 半柱径 - 半抱框宽度
    BaoKuangUp_x = frame_width/2 - pillerD/2 - con.BAOKUANG_WIDTH*pd/2
    BaoKuangUpLoc = Vector((BaoKuangUp_x,0,BaoKuangUp_z))
    bpy.ops.mesh.primitive_cube_add(
                        size=1.0, 
                        location = BaoKuangUpLoc, 
                        scale= BaoKuangUpScale)
    BaoKuangUpObj  = bpy.context.object
    BaoKuangUpObj.name = '上抱框'
    BaoKuangUpObj.parent = wallproxy
    # 添加mirror
    mod = BaoKuangUpObj.modifiers.new(name='mirror', type='MIRROR')
    mod.use_axis[0] = True
    mod.use_axis[1] = False
    mod.mirror_object = wallproxy
    # endregion 5、上抱框 ---------------------

    # region 6、横披窗 ---------------------
    # 横披窗数量：比隔扇少一扇
    window_top_num = wData.door_num - 1
    # 横披窗宽度:(柱间距-柱径-4抱框)/3
    window_top_width =  \
        (frame_width - pillerD - con.BAOKUANG_WIDTH*4*pd)/window_top_num
    # 循环生成每一扇横披窗
    for n in range(1,window_top_num):
        # 横披间框：右抱框中心 - n*横披窗间隔 - n*横披窗宽度
        windowTopKuang_x = BaoKuangUp_x - con.BAOKUANG_WIDTH*pd*n \
            - window_top_width * n
        windowTopKuangLoc = Vector((windowTopKuang_x,0,BaoKuangUp_z))
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = windowTopKuangLoc, 
                            scale= BaoKuangUpScale)
        bpy.context.object.name = '横披间框'
        bpy.context.object.parent = wallproxy

    # 横披窗尺寸
    WindowTopScale = Vector((window_top_width, # 宽度取横披窗宽度
                con.ZIBIAN_DEEPTH,
            BaoKuangUpHeight # 高度与上抱框相同
    ))
    # 填充棂心
    for n in range(0,window_top_num):
        windowTop_x = BaoKuangUp_x - \
            (con.BAOKUANG_WIDTH*pd + window_top_width)*(n+0.5)
        WindowTopLoc =  Vector((windowTop_x,0,BaoKuangUp_z))
        __buildShanxin(wallproxy,WindowTopScale,WindowTopLoc)

    # endregion 6、横披窗 ---------------------
    
    # 输出下抱框，做为隔扇生成的参考
    return BaoKuangDownObj

# 构建隔扇
# 采用故宫王璞子书的做法，马炳坚的做法不够协调
def __buildGeshan(name,wallproxy,scale,location):
    # 载入数据
    buildingObj = utils.getAcaParent(wallproxy,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    wData:acaData = wallproxy.ACA_data
    # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
    # todo：是采用用户可调整的设计值，还是取模版中定义的理论值？
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    use_KanWall = wData.use_KanWall

    # 1.隔扇根对象
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    geshan_root:bpy.types.Object = bpy.context.object
    geshan_root.name = name
    geshan_root.location = location
    geshan_width,geshan_deepth,geshan_height = scale
    geshan_root.parent = wallproxy  # 绑定到外框父对象    

    # 2.边梃/抹头宽（看面）: 1/10隔扇宽（或1/5D）
    # border_width = geshan_width / 10
    border_width = con.BORDER_WIDTH * pd
    # 边梃/抹头厚(进深)：1.5倍宽或0.3D，这里直接取了抱框厚度
    # border_deepth = BAOKUANG_DEEPTH * pd
    border_deepth = con.BORDER_DEEPTH * pd
    # 边梃
    loc = (geshan_width/2-border_width/2,0,0)
    scale = (border_width,border_deepth,geshan_height)
    bpy.ops.mesh.primitive_cube_add(
                        size=1.0, 
                        location = loc, 
                        scale= scale)
    bpy.context.object.name = '边梃'
    bpy.context.object.parent = geshan_root
    # 添加mirror
    mod = bpy.context.object.modifiers.new(name='mirror', type='MIRROR')
    mod.use_axis[0] = True
    mod.mirror_object = geshan_root

    # 3.构件抹头
    # 抹头上下
    loc = (0,0,geshan_height/2-border_width/2)
    motou_width = geshan_width-border_width*2
    scale = (motou_width,border_deepth,border_width)
    bpy.ops.mesh.primitive_cube_add(
                        size=1.0, 
                        location = loc, 
                        scale= scale)
    bpy.context.object.name = '抹头.上下'
    bpy.context.object.parent = geshan_root
    if not use_KanWall:
        # 添加mirror
        mod = bpy.context.object.modifiers.new(name='mirror', type='MIRROR')
        mod.use_axis[0] = False
        mod.use_axis[2] = True
        mod.mirror_object = geshan_root

    # 4. 分割棂心、裙板、绦环板
    gap_num = wData.gap_num   # 门缝，与槛框留出一些距离
    windowsill_height = 0       # 窗台高度，在需要做槛墙的槛框中定位
    if gap_num == 2:
        # 满铺扇心
        heartHeight = geshan_height - border_width *2
        # 扇心：抹二上推半扇心
        loc1 = Vector((0,0,0))
        scale = Vector((motou_width,border_deepth,heartHeight))
        __buildShanxin(geshan_root,scale,loc1)
    if gap_num == 3:
        # 三抹：扇心、裙板按6:4分
        # 隔扇心高度
        heartHeight = (geshan_height - border_width *3)*0.6
        loc2 = Vector((0,0,
            geshan_height/2-heartHeight-border_width*1.5))
        scale = Vector((motou_width,border_deepth,border_width))
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc2, 
                            scale= scale)
        bpy.context.object.name = '抹头.二'
        bpy.context.object.parent = geshan_root
        # 扇心：抹二上推半扇心
        loc8 = loc2+Vector((0,0,heartHeight/2+border_width/2))
        scale = Vector((motou_width,border_deepth,heartHeight))
        __buildShanxin(geshan_root,scale,loc8)
        if use_KanWall:
                # 计算窗台高度:抹二下皮
            windowsill_height = loc2.z - border_width/2
        else:
            # 裙板，抹二下方
            loc3 = loc2-Vector((0,0,heartHeight*2/6+border_width/2))
            scale = Vector((motou_width,border_deepth/3,heartHeight*4/6))
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc3, 
                                scale= scale)
            bpy.context.object.name = '裙板'
            bpy.context.object.parent = geshan_root           
    if gap_num == 4:
        # 四抹：一块绦环板
        # 减去4根抹头厚+绦环板(2抹高)，扇心裙板6/4分
        heartHeight = (geshan_height - border_width*6)*0.6
        # 抹二
        loc2 = Vector((0,0,
            geshan_height/2-heartHeight-border_width*1.5))
        scale = (motou_width,border_deepth,border_width)
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc2, 
                            scale= scale)
        bpy.context.object.name = '抹头.二'
        bpy.context.object.parent = geshan_root
        # 抹三
        loc3 = loc2 - Vector((0,0,border_width*3))
        scale = (motou_width,border_deepth,border_width)
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc3, 
                            scale= scale)
        bpy.context.object.name = '抹头.三'
        bpy.context.object.parent = geshan_root
        # 绦环板
        loc4 = (loc2+loc3)/2
        scale = (motou_width,border_deepth/3,border_width*2)
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc4, 
                            scale= scale)
        bpy.context.object.name = '绦环板'
        bpy.context.object.parent = geshan_root
        # 扇心：抹二上推半扇心
        loc8 = loc2+Vector((0,0,heartHeight/2+border_width/2))
        scale = Vector((motou_width,border_deepth,heartHeight))
        __buildShanxin(geshan_root,scale,loc8)
        if use_KanWall:
            # 计算窗台高度:抹三下皮
            windowsill_height = loc3.z - border_width/2
        else:
            # 裙板，抹三下方
            loc5 = loc3-Vector((0,0,heartHeight*2/6+border_width/2))
            scale = (motou_width,border_deepth/3,heartHeight*4/6)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc5, 
                                scale= scale)
            bpy.context.object.name = '裙板'
            bpy.context.object.parent = geshan_root            
    if gap_num == 5:
        # 五抹：减去5根抹头厚+2绦环板(4抹高)，扇心裙板6/4分
        heartHeight = (geshan_height - border_width*9)*0.6
        # 抹二
        loc2 = Vector((0,0,
            geshan_height/2-heartHeight-border_width*1.5))
        scale = (motou_width,border_deepth,border_width)
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc2, 
                            scale= scale)
        bpy.context.object.name = '抹头.二'
        bpy.context.object.parent = geshan_root
        # 抹三，抹二向下一块绦环板
        loc3 = loc2 - Vector((0,0,border_width*3))
        scale = (motou_width,border_deepth,border_width)
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc3, 
                            scale= scale)
        bpy.context.object.name = '抹头.三'
        bpy.context.object.parent = geshan_root
        # 绦环板一
        loc5 = (loc2+loc3)/2
        scale = (motou_width,border_deepth/3,border_width*2)
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc5, 
                            scale= scale)
        bpy.context.object.name = '绦环板一'
        bpy.context.object.parent = geshan_root
        # 扇心：抹二上推半扇心
        loc8 = loc2+Vector((0,0,heartHeight/2+border_width/2))
        scale = Vector((motou_width,border_deepth,heartHeight))
        __buildShanxin(geshan_root,scale,loc8)
        if use_KanWall:
            # 计算窗台高度:抹三下皮
            windowsill_height = loc3.z - border_width/2
        else:
            # 抹四，底边向上一块绦环板
            loc4 = Vector((0,0,
                -geshan_height/2+border_width*3.5))
            scale = (motou_width,border_deepth,border_width)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc4, 
                                scale= scale)
            bpy.context.object.name = '抹头.四'
            bpy.context.object.parent = geshan_root
            # 绦环板二
            loc6 = loc4 - Vector((0,0,border_width*1.5))
            scale = (motou_width,border_deepth/3,border_width*2)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc6, 
                                scale= scale)
            bpy.context.object.name = '绦环板二'
            bpy.context.object.parent = geshan_root
            # 裙板
            loc7 = (loc3+loc4)/2
            scale = (motou_width,border_deepth/3,heartHeight*4/6)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc7, 
                                scale= scale)
            bpy.context.object.name = '裙板'
            bpy.context.object.parent = geshan_root
    if gap_num == 6:
        # 六抹：减去6根抹头厚+3绦环板(6抹高)，扇心裙板6/4分
        heartHeight = (geshan_height-border_width*12)*0.6
        # 抹二，固定向下1.5抹+绦环板（2抹）
        loc2 = Vector((0,0,
            geshan_height/2-border_width*3.5))
        scale = (motou_width,border_deepth,border_width)
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc2, 
                            scale= scale)
        bpy.context.object.name = '抹头.二'
        bpy.context.object.parent = geshan_root
        # 抹三, 向下一个扇心+抹头
        loc3 = loc2 - Vector((0,0,heartHeight+border_width))
        scale = (motou_width,border_deepth,border_width)
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc3, 
                            scale= scale)
        bpy.context.object.name = '抹头.三'
        bpy.context.object.parent = geshan_root
        # 抹四，向下一块绦环板
        loc4 = loc3 - Vector((0,0,border_width*3))
        scale = (motou_width,border_deepth,border_width)
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc4, 
                            scale= scale)
        bpy.context.object.name = '抹头.四'
        bpy.context.object.parent = geshan_root
        # 抹五，底边反推一绦环板
        loc5 = Vector((
            0,0,-geshan_height/2+border_width*3.5
        ))
        scale = (motou_width,border_deepth,border_width)
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc5, 
                            scale= scale)
        bpy.context.object.name = '抹头.五'
        bpy.context.object.parent = geshan_root
        # 绦环板一，抹二反推
        loc6 = loc2+Vector((0,0,border_width*1.5))
        scale = (motou_width,border_deepth/3,border_width*2)
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc6, 
                            scale= scale)
        bpy.context.object.name = '绦环板一'
        bpy.context.object.parent = geshan_root
        # 绦环板二，抹三抹四之间
        loc7 = (loc3+loc4)/2
        scale = (motou_width,border_deepth/3,border_width*2)
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc7, 
                            scale= scale)
        bpy.context.object.name = '绦环板二'
        bpy.context.object.parent = geshan_root
        
        # 扇心：抹二和抹三之间
        loc8 = (loc2+loc3)/2
        scale = Vector((motou_width,border_deepth,heartHeight))
        __buildShanxin(geshan_root,scale,loc8)
        if use_KanWall:
            # 计算窗台高度:抹四下皮
            windowsill_height = loc4.z - border_width/2
        else:
            # 裙板，抹四抹五之间
            loc8 = (loc4+loc5)/2
            scale = (motou_width,border_deepth/3,heartHeight*4/6)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc8, 
                                scale= scale)
            bpy.context.object.name = '裙板'
            bpy.context.object.parent = geshan_root
            # 绦环板三，底边反推
            loc9 = Vector((0,0,-geshan_height/2+border_width*2))
            scale = (motou_width,border_deepth/3,border_width*2)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc9, 
                                scale= scale)
            bpy.context.object.name = '绦环板三'
            bpy.context.object.parent = geshan_root        
    return windowsill_height
    
# 构建槛墙
# 槛墙定位要与隔扇裙板上抹对齐，所以要根据隔扇的尺寸进行定位
def __buildKanqiang(wallproxy:bpy.types.Object
                    ,dimension):
    # 载入数据
    buildingObj = utils.getAcaParent(wallproxy,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    wData:acaData = wallproxy.ACA_data
    # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
    # todo：是采用用户可调整的设计值，还是取模版中定义的理论值？
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    use_KanWall = wData.use_KanWall

    # 风槛
    scl1 = Vector((
        dimension.x,
        con.KAN_WIND_DEEPTH*pd,
        con.KAN_WIND_HEIGHT*pd
    ))
    loc1 = Vector((
        0,0,dimension.z-scl1.z/2
    ))
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=loc1,
        scale=scl1
    )
    kanWindObj = bpy.context.object
    kanWindObj.name = '风槛'
    kanWindObj.parent = wallproxy
    # 榻板
    scl2 = Vector((
        dimension.x+con.TABAN_EX,
        con.TABAN_DEEPTH*pd+con.TABAN_EX,
        con.TABAN_HEIGHT*pd
    ))
    loc2 = Vector((
        0,0,dimension.z-scl1.z-scl2.z/2
    ))
    kanWindObj:bpy.types.Object = utils.drawHexagon(scl2,loc2)
    kanWindObj = bpy.context.object
    kanWindObj.name = '榻板'
    kanWindObj.parent = wallproxy
    # 槛墙
    scl3 = Vector((
        dimension.x,
        con.TABAN_DEEPTH*pd,
        dimension.z-scl1.z-scl2.z
    ))
    loc3 = Vector((
        0,0,scl3.z/2
    ))
    kanqiangObj:bpy.types.Object = utils.drawHexagon(scl3,loc3)
    kanqiangObj.name = '槛墙'
    kanqiangObj.parent = wallproxy
    return

# 构建完整的隔扇
def __buildDoor(wallproxy):       
    # 载入设计数据
    buildingObj = utils.getAcaParent(wallproxy,con.ACA_TYPE_BUILDING)
    bdata:acaData = buildingObj.ACA_data
    wData:acaData = wallproxy.ACA_data
    if bdata == None:
        utils.showMessageBox("无法读取设计数据","ERROR")
        return {'FINISHED'}
    elif bdata.aca_type != con.ACA_TYPE_BUILDING:
        utils.showMessageBox("未找到建筑根节点","ERROR")
        return {'FINISHED'}
    dk = bdata.DK
    pd = con.PILLER_D_EAVE * dk
    pillerD = bdata.piller_diameter
    # 分解槛框的长、宽、高
    frame_width,frame_deepth,frame_height = wallproxy.dimensions

    # 清理之前的子对象
    # utils.deleteHierarchy(wallproxy)
    # 聚焦在当前collection中
    # utils.setCollection(con.ROOT_COLL_NAME)
    
    # 2、构建槛框，返回下抱框，做为隔扇生成的参考  
    BaoKuangDownObj = __buildKanKuang(wallproxy)

    # 3、构建槛框内的每一扇隔扇
    # 隔扇数量
    geshan_num = wData.door_num
    geshan_total_width = frame_width - pillerD - con.BAOKUANG_WIDTH*pd*2
    # 每个隔扇宽度：抱框位置 / 隔扇数量
    geshan_width = geshan_total_width/geshan_num
    # 与下抱框等高，参考buildKankuang函数的返回对象
    geshan_height = BaoKuangDownObj.dimensions.z
    scale = Vector((geshan_width-con.GESHAN_GAP,
                con.BAOKUANG_DEEPTH * pd,
                geshan_height-con.GESHAN_GAP))
    for n in range(geshan_num):
        # 位置
        location = Vector((geshan_width*(geshan_num/2-n-0.5),   #向右半扇
                    0,
                    BaoKuangDownObj.location.z    #与抱框平齐
                    ))
        windowsill_height = __buildGeshan(
            '隔扇',wallproxy,scale,location)

    # 4、添加槛墙
    use_KanWall = wData.use_KanWall
    if use_KanWall :
        # 窗台高度
        windowsill_z = windowsill_height + BaoKuangDownObj.location.z
        scale = Vector((
            wallproxy.dimensions.x,
            wallproxy.dimensions.y,
            windowsill_z
        ))
        # 添加槛墙
        __buildKanqiang(wallproxy,scale)

    utils.focusObj(wallproxy)

# 在wallproxy的顶部插入大额枋、由额垫板、小额枋
def __addFang(wallproxy:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(wallproxy,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    wData:acaData = wallproxy.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk

    # 分解槛框的长、宽、高
    # 这里不取wallproxy高度，改用柱高，以便将额枋高度计入
    frame_width = wallproxy.dimensions.x
    frame_height = bData.piller_height

    # 大额枋
    bigFangScale = Vector(
                        (frame_width, # 长度随面宽
                        con.EFANG_LARGE_Y * pd,
                        con.EFANG_LARGE_H * pd
                        )
                    )
    bigFangLoc = Vector((0,0,
            frame_height - con.EFANG_LARGE_H*pd/2))
    bigFangObj = utils.drawHexagon(bigFangScale,bigFangLoc)
    bigFangObj.name =  "大额枋"

    # 垫板
    dianbanScale = Vector(
                        (frame_width, # 长度随面宽
                        con.BOARD_YOUE_Y * pd,
                        con.BOARD_YOUE_H * pd
                        )
                    )
    dianbanLoc = Vector((0,0,
            bigFangLoc.z \
            - con.EFANG_LARGE_H*pd/2 \
            - con.BOARD_YOUE_H*pd/2))
    bpy.ops.mesh.primitive_cube_add(
                        size=1.0, 
                        location = dianbanLoc, 
                        scale= dianbanScale)
    dianbanObj = bpy.context.object
    dianbanObj.name =  "由额垫板"
    
    # 小额枋
    smallFangScale = Vector(
                        (frame_width, # 长度随面宽
                        con.EFANG_SMALL_Y * pd,
                        con.EFANG_SMALL_H * pd
                        )
                    )
    smallFangLoc = Vector((0,0,
            dianbanLoc.z \
            - con.BOARD_YOUE_H*pd/2 \
            - con.EFANG_SMALL_H*pd/2))
    smallFangObj = utils.drawHexagon(smallFangScale,smallFangLoc)
    smallFangObj.name =  "小额枋"

    # 将额枋放在wallproxy的线框之外
    wallproxy.dimensions.z = frame_height - con.EFANG_LARGE_H*pd \
                            - con.BOARD_YOUE_H*pd \
                            - con.EFANG_SMALL_H*pd
    utils.applyScale(wallproxy)
    # 绑定额枋到wallproxy
    bigFangObj.parent = wallproxy
    dianbanObj.parent = wallproxy
    smallFangObj.parent = wallproxy

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

        # 在wallproxy顶部插入大额枋、由额垫板、小额枋
        # 插入后，wallproxy的高度将自动更新为柱头减去枋的高度
        wallproxy = __addFang(wallproxy)
        
        if wData.wall_style == "1":   #槛墙
            if wData.wall_source != None:
                wallChildObj = utils.copyObject(
                    sourceObj=wData.wall_source,
                    name='墙体',
                    parentObj=wallproxy
                )
                wallChildObj.dimensions = (wallproxy.dimensions.x,
                                        wallChildObj.dimensions.y,
                                        wallproxy.dimensions.z)
        if wData.wall_style in ("2","3"): # 2-隔扇，3-槛墙
            utils.focusObj(wallproxy)
            __buildDoor(wallproxy)

        # 重新聚焦建筑根节点
        utils.focusObj(wallproxy)

        utils.outputMsg("墙体构造：" + wallproxy.name)