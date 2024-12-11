# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   隔扇、槛窗的营造
import bpy
import math
from mathutils import Vector

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from .data import ACA_data_template as tmpData
from . import texture as mat
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
    aData:tmpData = bpy.context.scene.ACA_temp
    # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
    # todo：是采用用户可调整的设计值，还是取模版中定义的理论值？
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk

    # 扇心高度校验，以免出现row=0的异常
    linxingHeight = scale.z- con.ZIBIAN_WIDTH*2*pd
    unitWidth,unitDeepth,unitHeight = utils.getMeshDims(aData.lingxin_source)
    rows = math.ceil(linxingHeight/unitHeight)+1
    if rows<=0:
        return

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
    # 转为mesh
    bpy.ops.object.convert(target='MESH')

    # # 填充棂心
    # lingxinObj = aData.lingxin_source
    # if lingxinObj == None: return
    # # 定位：从左下角排布array
    # loc = (location.x-scale.x/2+con.ZIBIAN_WIDTH*pd,
    #         location.y,
    #         location.z-scale.z/2+con.ZIBIAN_WIDTH*pd)
    # lingxin = utils.copyObject(
    #     sourceObj=lingxinObj,
    #     name='棂心',
    #     parentObj=parent,
    #     location=loc,
    #     singleUser=True)
    # # 计算平铺的行列数
    # unitWidth,unitDeepth,unitHeight = utils.getMeshDims(lingxin)
    # lingxingWidth = scale.x- con.ZIBIAN_WIDTH*2*pd
    # linxingHeight = scale.z- con.ZIBIAN_WIDTH*2*pd
    # rows = math.ceil(linxingHeight/unitHeight)+1 #加一，尽量让棂心紧凑，避免出现割裂
    # row_span = linxingHeight/rows
    # mod_rows = lingxin.modifiers.get('Rows')
    # mod_rows.count = rows
    # mod_rows.constant_offset_displace[2] = row_span

    # cols = math.ceil(lingxingWidth/unitWidth)+1#加一，尽量让棂心紧凑，避免出现割裂
    # col_span = lingxingWidth/cols
    # mod_cols = lingxin.modifiers.get('Columns')
    # mod_cols.count = cols
    # mod_cols.constant_offset_displace[0] = col_span
    # # 应用array modifier
    # utils.applyAllModifer(lingxin)

    # 添加简化版的棂心（平面贴图方式）
    bpy.ops.mesh.primitive_plane_add(location=location,size=1)
    plane = bpy.context.object
    plane.name = '棂心'
    plane.data.name = '棂心'
    plane.parent = parent
    plane.scale = (scale.x- con.ZIBIAN_WIDTH*2*pd,
                   scale.z- con.ZIBIAN_WIDTH*2*pd,
                   1)
    plane.rotation_euler.x = math.radians(90)
    # apply
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mat.setShader(plane,mat.shaderType.GESHANXIN)

    return # linxinObj

# 构建槛框
# 基于输入的槛框线框对象
def __buildKanKuang(wallproxy):
    # 载入数据
    buildingObj,bData,wData = utils.getRoot(wallproxy)
    if buildingObj == None:
        utils.showMessageBox(
            "未找到建筑根节点或设计数据","ERROR")
        return
    # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
    # todo：是采用用户可调整的设计值，还是取模版中定义的理论值？
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    use_KanWall = wData.use_KanWall
    pillerD = bData.piller_diameter
    # 分解槛框的长、宽、高
    frame_width,frame_depth,frame_height = wallproxy.dimensions

    KankuangObjs = []

    # 1、下槛 ---------------------
    # 槛窗无需下槛
    if not use_KanWall:
        KanDownLoc = Vector((0,0,con.KAN_DOWN_HEIGHT*pd/2))
        KanDownScale = Vector((frame_width, # 长度随面宽
                    con.KAN_DOWN_DEPTH * pd, # 厚0.3D
                    con.KAN_DOWN_HEIGHT * pd, # 高0.8D
                    ))
        KanDownObj = utils.addCube(
            name="下槛",
            location=KanDownLoc,
            dimension=KanDownScale,
            parent=wallproxy,
        )
        KankuangObjs.append(KanDownObj)
        
    # 2、上槛 ---------------------
    KanUpLoc = Vector((0,0,
            frame_height - con.KAN_UP_HEIGHT*pd/2))
    KanUpScale = Vector((frame_width, # 长度随面宽
                con.KAN_UP_DEPTH * pd, # 厚0.3D
                con.KAN_UP_HEIGHT * pd, # 高0.8D
                ))
    KanTopObj = utils.addCube(
        name="上槛",
        location=KanUpLoc,
        dimension=KanUpScale,
        parent=wallproxy,
    )
    KankuangObjs.append(KanTopObj)

    # 3、下抱框 ---------------------
    if wData.use_topwin:
        # 有横披窗时，下抱框从中槛下皮到下槛上皮
        BaoKuangDownHeight = \
            (wData.door_height - con.KAN_MID_HEIGHT*pd/2) \
            - con.KAN_DOWN_HEIGHT*pd
    else:
        # 无横披窗时，下抱框从上槛下皮到下槛上皮
        BaoKuangDownHeight = \
            frame_height - con.KAN_UP_HEIGHT*pd \
            - con.KAN_DOWN_HEIGHT*pd
    # 位置Z：从下槛+一半高度
    BaoKuangDown_z = con.KAN_DOWN_HEIGHT*pd \
                        + BaoKuangDownHeight/2
    # 位置X：半柱间距 - 半柱径 - 半抱框宽度
    BaoKuangDown_x = frame_width/2 - pillerD/2 - con.BAOKUANG_WIDTH*pd/2
    BaoKuangDownLoc = Vector((BaoKuangDown_x,0,BaoKuangDown_z))
    BaoKuangDownScale = Vector((
                con.BAOKUANG_WIDTH * pd, # 宽0.66D
                con.BAOKUANG_DEPTH * pd, # 厚0.3D
                BaoKuangDownHeight, 
                ))
    BaoKuangDownObj = utils.addCube(
        name="下抱框",
        location=BaoKuangDownLoc,
        dimension=BaoKuangDownScale,
        parent=wallproxy,
    )
    # 添加mirror
    mod = BaoKuangDownObj.modifiers.new(name='mirror', type='MIRROR')
    mod.use_axis[0] = True
    mod.use_axis[1] = False
    mod.mirror_object = wallproxy
    KankuangObjs.append(BaoKuangDownObj)

    # 横披窗 ---------------------
    if wData.use_topwin:
        # 1、中槛
        KanMidLoc = Vector((0,0,wData.door_height))
        KanMidScale = Vector((frame_width, # 长度随面宽
                con.KAN_MID_DEPTH * pd, # 厚0.3D
                con.KAN_MID_HEIGHT * pd, # 高0.8D
                ))
        KanMidObj = utils.addCube(
            name="中槛",
            location=KanMidLoc,
            dimension=KanMidScale,
            parent=wallproxy,
        )
        KankuangObjs.append(KanMidObj)

        # 2、上抱框
        # 高度：从上槛下皮到中槛上皮
        BaoKuangUpHeight = \
            frame_height - con.KAN_UP_HEIGHT*pd \
            - (wData.door_height + con.KAN_MID_HEIGHT*pd/2)
        # 位置Z：从上槛下皮，减一半高度
        BaoKuangUp_z = \
            frame_height - con.KAN_UP_HEIGHT*pd \
            - BaoKuangUpHeight/2
        # 位置X：半柱间距 - 半柱径 - 半抱框宽度
        BaoKuangUp_x = frame_width/2 - pillerD/2 - con.BAOKUANG_WIDTH*pd/2
        BaoKuangUpLoc = Vector((BaoKuangUp_x,0,BaoKuangUp_z))
        BaoKuangUpScale = Vector((
                    con.BAOKUANG_WIDTH * pd, # 宽0.66D
                    con.BAOKUANG_DEPTH * pd, # 厚0.3D
                    BaoKuangUpHeight, 
                    ))
        BaoKuangUpObj = utils.addCube(
            name="上抱框",
            location=BaoKuangUpLoc,
            dimension=BaoKuangUpScale,
            parent=wallproxy,
        )
        # 添加mirror
        mod = BaoKuangUpObj.modifiers.new(name='mirror', type='MIRROR')
        mod.use_axis[0] = True
        mod.use_axis[1] = False
        mod.mirror_object = wallproxy
        KankuangObjs.append(BaoKuangUpObj)

        # 3、横披窗棂心 ---------------------
        topWinObjs = []
        # 横披窗数量：比隔扇少一扇
        window_top_num = wData.door_num - 1
        # 横披窗宽度:(柱间距-柱径-抱框*(横披窗数量+1))/3
        window_top_width = ((frame_width 
                             - pillerD 
                             - (window_top_num+1)*con.BAOKUANG_WIDTH*pd)
                            /window_top_num)
        # 循环生成每一扇横披窗
        for n in range(1,window_top_num):
            # 横披间框：右抱框中心 - n*横披窗间隔 - n*横披窗宽度
            windowTopKuang_x = BaoKuangUp_x - con.BAOKUANG_WIDTH*pd*n \
                - window_top_width * n
            windowTopKuangLoc = Vector((windowTopKuang_x,0,BaoKuangUp_z))
            hengKuangObj = utils.addCube(
                name="横披间框",
                location=windowTopKuangLoc,
                dimension=BaoKuangUpScale,
                parent=wallproxy,
            )
            KankuangObjs.append(hengKuangObj)
        # 横披窗尺寸
        WindowTopScale = Vector((window_top_width, # 宽度取横披窗宽度
                    con.ZIBIAN_DEPTH*pd,
                BaoKuangUpHeight # 高度与上抱框相同
        ))
        # 填充棂心
        for n in range(0,window_top_num):
            windowTop_x = BaoKuangUp_x - \
                (con.BAOKUANG_WIDTH*pd + window_top_width)*(n+0.5)
            WindowTopLoc =  Vector((windowTop_x,0,BaoKuangUp_z))
            linxinObj = __buildShanxin(
                wallproxy,WindowTopScale,WindowTopLoc)
    
    # 门楹
    if not use_KanWall:
        geshan_num = wData.door_num
        kuangWidth = (frame_width 
            - pillerD - con.BAOKUANG_WIDTH*pd*2)
        dim = Vector((con.MENYIN_WIDTH*pd,
                    con.MENYIN_DEPTH*pd,
                    con.MENYIN_HEIGHT*pd))
        for n in range(geshan_num):
            # 仅做奇数，不做偶数
            if n%2 ==0 : continue
            # 横坐标，平均分配每扇隔扇的中点
            x = -kuangWidth/2 + n*kuangWidth/geshan_num
            # 与下槛内皮相平
            y = con.KAN_DOWN_DEPTH * pd/2

            if wData.use_topwin:
                # 上门楹与中槛垂直居中
                z = wData.door_height
            else:
                # 上门楹与上槛上皮平
                z = frame_height - con.MENYIN_HEIGHT*pd/2

            loc = Vector((x,y,z))
            menyinObj = utils.drawHexagon(
                dim,
                loc,
                half=True,
                name='上门楹',
                parent=wallproxy)
            KankuangObjs.append(menyinObj)

            # 下门楹与下槛下皮相平
            z = con.MENYIN_HEIGHT*pd/2
            loc = Vector((x,y,z))        
            menyinObj = utils.drawHexagon(
                dim,
                loc,
                half=True,
                name='下门楹',
                parent=wallproxy
                )
            KankuangObjs.append(menyinObj)
            
    # 统一添加bevel
    for obj in KankuangObjs:
        modBevel:bpy.types.BevelModifier = \
            obj.modifiers.new('Bevel','BEVEL')
        modBevel.width = con.BEVEL_HIGH

    # 输出下抱框，做为隔扇生成的参考
    return BaoKuangDownObj

# 构建隔扇
# 采用故宫王璞子书的做法，马炳坚的做法不够协调
# 参见汤崇平书“木装修”分册的p43
def __buildGeshan(name,wallproxy,scale,location,dir='L'):
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
    geshan_width,geshan_depth,geshan_height = scale
    geshan_root.parent = wallproxy  # 绑定到外框父对象    

    # 2.边梃/抹头宽（看面）: 1/10隔扇宽（或1/5D）
    border_width = con.BORDER_WIDTH * pd
    # 边梃/抹头厚(进深)：1.5倍宽或0.3D，这里直接取了抱框厚度
    border_depth = con.BORDER_DEPTH * pd

    # 3.构件抹头
    # 抹头上下
    loc = (0,0,geshan_height/2-border_width/2)
    motou_width = geshan_width-border_width*2
    scale = (motou_width,border_depth,border_width)
    motouObj = utils.addCube(
        name="抹头.上下",
        location=loc,
        dimension=scale,
        parent=geshan_root,
    )
    if not use_KanWall:
        # 添加mirror
        mod = bpy.context.object.modifiers.new(name='mirror', type='MIRROR')
        mod.use_axis[0] = False
        mod.use_axis[2] = True
        mod.mirror_object = geshan_root

    # 4. 分割棂心、裙板、绦环板
    gap_num = wData.gap_num   # 抹头数量
    qunbanObj = None    # 裙板对象
    taohuanList = []    # 收集绦环板对象
    windowsill_height = -geshan_height/2       # 窗台高度，在需要做槛墙的槛框中定位
    if gap_num == 2:
        if use_KanWall:
            # 槛窗不做2抹，直接按3抹做
            gap_num=3
        else:
            # 满铺扇心
            heartHeight = geshan_height - border_width *2
            # 扇心：抹二上推半扇心
            loc1 = Vector((0,0,0))
            scale = Vector((motou_width,border_depth,heartHeight))
            __buildShanxin(geshan_root,scale,loc1)
    if gap_num == 3:
        # 三抹：扇心、裙板按6:4分
        # 隔扇心高度
        heartHeight = (geshan_height - border_width *3)*0.6
        loc2 = Vector((0,0,
            geshan_height/2-heartHeight-border_width*1.5))
        scale = Vector((motou_width,border_depth,border_width))
        motouObj = utils.addCube(
            name="抹头.二",
            location=loc2,
            dimension=scale,
            parent=geshan_root,
        )
        # 扇心：抹二上推半扇心
        loc8 = loc2+Vector((0,0,heartHeight/2+border_width/2))
        scale = Vector((motou_width,border_depth,heartHeight))
        __buildShanxin(geshan_root,scale,loc8)
        if use_KanWall:
                # 计算窗台高度:抹二下皮
            windowsill_height = loc2.z - border_width/2
        else:
            # 裙板，抹二下方
            loc3 = loc2-Vector((0,0,heartHeight*2/6+border_width/2))
            scale = Vector((motou_width,border_depth/3,heartHeight*4/6))
            qunbanObj = utils.addCube(
                name="裙板",
                location=loc3,
                dimension=scale,
                parent=geshan_root,
            )          
    if gap_num == 4:
        # 四抹：一块绦环板
        # 减去4根抹头厚+绦环板(2抹高)，扇心裙板6/4分
        heartHeight = (geshan_height - border_width*6)*0.6
        # 抹二
        loc2 = Vector((0,0,
            geshan_height/2-heartHeight-border_width*1.5))
        scale = (motou_width,border_depth,border_width)
        motouObj = utils.addCube(
                name="抹头.二",
                location=loc2,
                dimension=scale,
                parent=geshan_root,
            ) 
        # 抹三
        loc3 = loc2 - Vector((0,0,border_width*3))
        scale = (motou_width,border_depth,border_width)
        motouObj = utils.addCube(
                name="抹头.三",
                location=loc3,
                dimension=scale,
                parent=geshan_root,
            )
        # 绦环板
        loc4 = (loc2+loc3)/2
        scale = (motou_width,border_depth/3,border_width*2)
        taohuanObj = utils.addCube(
                name="绦环板",
                location=loc4,
                dimension=scale,
                parent=geshan_root,
            )
        taohuanList.append(taohuanObj)
        # 扇心：抹二上推半扇心
        loc8 = loc2+Vector((0,0,heartHeight/2+border_width/2))
        scale = Vector((motou_width,border_depth,heartHeight))
        __buildShanxin(geshan_root,scale,loc8)
        if use_KanWall:
            # 计算窗台高度:抹三下皮
            windowsill_height = loc3.z - border_width/2
        else:
            # 裙板，抹三下方
            loc5 = loc3-Vector((0,0,heartHeight*2/6+border_width/2))
            scale = (motou_width,border_depth/3,heartHeight*4/6)
            qunbanObj = utils.addCube(
                name="裙板",
                location=loc5,
                dimension=scale,
                parent=geshan_root,
            )           
    if gap_num == 5:
        # 五抹：减去5根抹头厚+2绦环板(4抹高)，扇心裙板6/4分
        heartHeight = (geshan_height - border_width*9)*0.6
        # 抹二
        loc2 = Vector((0,0,
            geshan_height/2-heartHeight-border_width*1.5))
        scale = (motou_width,border_depth,border_width)
        motouObj = utils.addCube(
                name="抹头.二",
                location=loc2,
                dimension=scale,
                parent=geshan_root,
            ) 
        # 抹三，抹二向下一块绦环板
        loc3 = loc2 - Vector((0,0,border_width*3))
        scale = (motou_width,border_depth,border_width)
        motouObj = utils.addCube(
                name="抹头.三",
                location=loc3,
                dimension=scale,
                parent=geshan_root,
            ) 
        # 绦环板一
        loc5 = (loc2+loc3)/2
        scale = (motou_width,border_depth/3,border_width*2)
        taohuanObj = utils.addCube(
                name="绦环板一",
                location=loc5,
                dimension=scale,
                parent=geshan_root,
            ) 
        taohuanList.append(taohuanObj)
        # 扇心：抹二上推半扇心
        loc8 = loc2+Vector((0,0,heartHeight/2+border_width/2))
        scale = Vector((motou_width,border_depth,heartHeight))
        __buildShanxin(geshan_root,scale,loc8)
        if use_KanWall:
            # 计算窗台高度:抹三下皮
            windowsill_height = loc3.z - border_width/2
        else:
            # 抹四，底边向上一块绦环板
            loc4 = Vector((0,0,
                -geshan_height/2+border_width*3.5))
            scale = (motou_width,border_depth,border_width)
            motouObj = utils.addCube(
                name="抹头.四",
                location=loc4,
                dimension=scale,
                parent=geshan_root,
            ) 
            # 绦环板二
            loc6 = loc4 - Vector((0,0,border_width*1.5))
            scale = (motou_width,border_depth/3,border_width*2)
            taohuanObj = utils.addCube(
                name="绦环板二",
                location=loc6,
                dimension=scale,
                parent=geshan_root,
            ) 
            taohuanList.append(taohuanObj)
            # 裙板
            loc7 = (loc3+loc4)/2
            scale = (motou_width,border_depth/3,heartHeight*4/6)
            qunbanObj = utils.addCube(
                name="裙板",
                location=loc7,
                dimension=scale,
                parent=geshan_root,
            ) 
    if gap_num == 6:
        # 六抹：减去6根抹头厚+3绦环板(6抹高)，扇心裙板6/4分
        heartHeight = (geshan_height-border_width*12)*0.6
        # 抹二，固定向下1.5抹+绦环板（2抹）
        loc2 = Vector((0,0,
            geshan_height/2-border_width*3.5))
        scale = (motou_width,border_depth,border_width)
        motouObj = utils.addCube(
                name="抹头.二",
                location=loc2,
                dimension=scale,
                parent=geshan_root,
            ) 
        # 抹三, 向下一个扇心+抹头
        loc3 = loc2 - Vector((0,0,heartHeight+border_width))
        scale = (motou_width,border_depth,border_width)
        motouObj = utils.addCube(
                name="抹头.三",
                location=loc3,
                dimension=scale,
                parent=geshan_root,
            ) 
        # 抹四，向下一块绦环板
        loc4 = loc3 - Vector((0,0,border_width*3))
        scale = (motou_width,border_depth,border_width)
        motouObj = utils.addCube(
                name="抹头.四",
                location=loc4,
                dimension=scale,
                parent=geshan_root,
            ) 
        # 绦环板一，抹二反推
        loc6 = loc2+Vector((0,0,border_width*1.5))
        scale = (motou_width,border_depth/3,border_width*2)
        taohuanObj = utils.addCube(
                name="绦环板一",
                location=loc6,
                dimension=scale,
                parent=geshan_root,
            ) 
        taohuanList.append(taohuanObj)
        # 绦环板二，抹三抹四之间
        loc7 = (loc3+loc4)/2
        scale = (motou_width,border_depth/3,border_width*2)
        taohuanObj = utils.addCube(
                name="绦环板二",
                location=loc7,
                dimension=scale,
                parent=geshan_root,
            ) 
        taohuanList.append(taohuanObj)
        # 扇心：抹二和抹三之间
        loc8 = (loc2+loc3)/2
        scale = Vector((motou_width,border_depth,heartHeight))
        __buildShanxin(geshan_root,scale,loc8)
        if use_KanWall:
            # 计算窗台高度:抹四下皮
            windowsill_height = loc4.z - border_width/2
        else:
            # 抹五，底边反推一绦环板
            loc5 = Vector((
                0,0,-geshan_height/2+border_width*3.5
            ))
            scale = (motou_width,border_depth,border_width)
            motouObj = utils.addCube(
                name="抹头.五",
                location=loc5,
                dimension=scale,
                parent=geshan_root,
            ) 
            # 裙板，抹四抹五之间
            loc8 = (loc4+loc5)/2
            scale = (motou_width,border_depth/3,heartHeight*4/6)
            qunbanObj = utils.addCube(
                name="裙板",
                location=loc8,
                dimension=scale,
                parent=geshan_root,
            ) 
            # 绦环板三，底边反推
            loc9 = Vector((0,0,-geshan_height/2+border_width*2))
            scale = (motou_width,border_depth/3,border_width*2)
            taohuanObj = utils.addCube(
                name="绦环板三",
                location=loc9,
                dimension=scale,
                parent=geshan_root,
            )  
            taohuanList.append(taohuanObj)     
        
    # 留出窗缝
    windowsill_height -= con.GESHAN_GAP/2

    # 边梃
    final_height = geshan_height
    if use_KanWall:
        # 边梃高度依赖于槛窗的高度
        final_height = (geshan_height/2 
            - windowsill_height 
            - con.GESHAN_GAP/2)
        loc = (geshan_width/2-border_width/2,0,
            geshan_height/2 - final_height/2    
        )
    else:
        loc = (geshan_width/2-border_width/2,0,0)
    scale = (border_width,border_depth,final_height)
    geshanObj = utils.addCube(
                name="边梃",
                location=loc,
                dimension=scale,
                parent=geshan_root,
            )    
    # 添加mirror
    mod = bpy.context.object.modifiers.new(name='mirror', type='MIRROR')
    mod.use_axis[0] = True
    mod.mirror_object = geshan_root

    # 门轴 ========================
    # 门轴长度，比隔扇延长2个门楹长度（粗略）
    menzhou_height = final_height+con.MENYIN_HEIGHT*pd*2
    # 门轴位置分左开，右开
    if dir=='L':
        x = -geshan_width/2 + con.MENZHOU_R*pd
    else:
        x = geshan_width/2 - con.MENZHOU_R*pd
    # 门轴外皮与隔扇相切（实际应该是做成一体的）
    y = con.BORDER_DEPTH * pd/2 + con.MENZHOU_R * pd
    # 门轴与隔扇垂直对齐
    if not use_KanWall:
        # 隔扇与门轴居中对齐
        z = 0
    else:
        # 槛窗与门轴对齐
        z = (geshan_height/2+windowsill_height)/2
        
    menzhouObj = utils.addCylinder(
                radius = con.MENZHOU_R*pd,
                depth = menzhou_height,
                location=(x,y,z),
                name="门轴",
                root_obj=geshan_root,  # 挂接在柱网节点下
            )

    # 隐藏隔扇根节点
    utils.hideObj(geshan_root)

    # 隔扇着色
    for ob in geshan_root.children:
        # 全部设置为朱漆材质
        # 其中槛窗的窗台为石质，并不会被覆盖
        mat.setShader(ob,mat.shaderType.REDPAINT)
    
    # 绦环板着色
    for taohuan in taohuanList:
        mat.setShader(taohuan,
            mat.shaderType.DOORRING,override=True)

    # 设置裙板材质
    if qunbanObj != None:
        mat.setShader(qunbanObj,
            mat.shaderType.DOOR,override=True)

    # 隔扇子对象合并
    geshanObj = utils.joinObjects(
        geshan_root.children,
        newName='隔扇门')
    geshanObj.parent = wallproxy
    geshanObj.location += geshan_root.location
    bpy.data.objects.remove(geshan_root)

    # 锁定旋转，仅允许Z轴开窗、开门
    geshanObj.lock_rotation = (True,True,False)

    # 添加整体bevel
    modBevel:bpy.types.BevelModifier = \
        geshanObj.modifiers.new('Bevel','BEVEL')
    modBevel.width = con.BEVEL_LOW

    return windowsill_height
    
# 构建槛墙
# 槛墙定位要与隔扇裙板上抹对齐，所以要根据隔扇的尺寸进行定位
def __buildKanqiang(wallproxy:bpy.types.Object
                    ,dimension):
    # 载入数据
    buildingObj = utils.getAcaParent(wallproxy,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    wData:acaData = wallproxy.ACA_data
    # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
    # todo：是采用用户可调整的设计值，还是取模版中定义的理论值？
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    pillerD = bData.piller_diameter
    use_KanWall = wData.use_KanWall
    # 分解槛框的长、宽、高
    frame_width,frame_depth,frame_height = wallproxy.dimensions

    kanQiangObjs = []

    # 风槛
    scl1 = Vector((
        dimension.x,
        con.KAN_WIND_DEPTH*pd,
        con.KAN_WIND_HEIGHT*pd
    ))
    loc1 = Vector((
        0,0,dimension.z-scl1.z/2
    ))
    kanWindObj = utils.addCube(
                name="风槛",
                location=loc1,
                dimension=scl1,
                parent=wallproxy,
            ) 
    kanQiangObjs.append(kanWindObj)

    # 榻板
    scl2 = Vector((
        dimension.x+con.TABAN_EX,
        con.TABAN_DEPTH*pd+con.TABAN_EX,
        con.TABAN_HEIGHT*pd
    ))
    loc2 = Vector((
        0,0,dimension.z-scl1.z-scl2.z/2
    ))
    taBanObj:bpy.types.Object = utils.drawHexagon(
        scl2,
        loc2,
        name='榻板',
        parent=wallproxy
        )
    kanQiangObjs.append(taBanObj)

    # 槛墙
    scl3 = Vector((
        dimension.x,
        con.TABAN_DEPTH*pd,
        dimension.z-scl1.z-scl2.z
    ))
    loc3 = Vector((
        0,0,scl3.z/2
    ))
    kanqiangObj:bpy.types.Object = utils.drawHexagon(
        scl3,
        loc3,
        name='槛墙',
        parent = wallproxy,
        )
    # 设置材质
    mat.setShader(kanqiangObj,mat.shaderType.ROCK)
    kanQiangObjs.append(kanqiangObj)

    # 窗楹
    geshan_num = wData.door_num
    kuangWidth = (frame_width 
        - pillerD - con.BAOKUANG_WIDTH*pd*2)
    dim = Vector((con.MENYIN_WIDTH*pd,
                con.MENYIN_DEPTH*pd,
                con.MENYIN_HEIGHT*pd))
    for n in range(geshan_num):
        # 仅做奇数，不做偶数
        if n%2 ==0 : continue
        # 横坐标，平均分配每扇隔扇的中点
        x = -kuangWidth/2 + n*kuangWidth/geshan_num
        # 与下槛内皮相平
        y = con.KAN_DOWN_DEPTH * pd/2
        
        if wData.use_topwin:
            # 上窗楹与中槛垂直居中
            z = wData.door_height
        else:
            # 上窗楹与上槛上皮平
            z = frame_height - con.MENYIN_HEIGHT*pd/2

        loc = Vector((x,y,z))
        menyinObj = utils.drawHexagon(
            dim,
            loc,
            half=True,
            parent = wallproxy,
            name = '上窗楹',
            )
        kanQiangObjs.append(menyinObj)

        # 下窗楹与风槛槛下皮相平
        z = (dimension.z 
             - con.KAN_WIND_HEIGHT*pd 
             + con.MENYIN_HEIGHT*pd/2)
        loc = Vector((x,y,z))        
        menyinObj = utils.drawHexagon(
            dim,
            loc,
            half=True,
            parent = wallproxy,
            name = '下窗楹',
            )
        kanQiangObjs.append(menyinObj)

    # 统一添加bevel
    for obj in kanQiangObjs:
        modBevel:bpy.types.BevelModifier = \
            obj.modifiers.new('Bevel','BEVEL')
        modBevel.width = con.BEVEL_HIGH

    return

# 构建完整的隔扇
def buildDoor(wallproxy:bpy.types.Object):       
    # 载入设计数据
    buildingObj,bData,wData = utils.getRoot(wallproxy)
    aData:tmpData = bpy.context.scene.ACA_temp
    if buildingObj == None:
        utils.showMessageBox(
            "未找到建筑根节点或设计数据","ERROR")
        return
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    pillerD = bData.piller_diameter
    # 分解槛框的长、宽、高
    frame_width,frame_depth,frame_height = wallproxy.dimensions

    # 清理之前的子对象
    utils.deleteHierarchy(wallproxy)

    # 针对重檐，装修不一定做到柱头，用走马板填充
    if bData.wall_span != 0 :
        wallHeadBoard = utils.addCube(
                name = "走马板",
                location=(0,0,
                    frame_height \
                        +bData.wall_span/2),
                dimension=(frame_width,
                           con.BOARD_YOUE_Y*dk,
                           bData.wall_span),
                parent=wallproxy,
            )
        mat.setShader(wallHeadBoard,mat.shaderType.WOOD)
    
    # 1、构建槛框
    # 返回的是下抱框，做为隔扇生成的参考  
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
                con.BAOKUANG_DEPTH * pd,
                geshan_height-con.GESHAN_GAP))
    for n in range(geshan_num):
        # 位置
        location = Vector((geshan_width*(geshan_num/2-n-0.5),   #向右半扇
                    0,
                    BaoKuangDownObj.location.z    #与抱框平齐
                    ))
        # 左开还是右开
        if n%2 == 0:
            dir = 'L'
        else:
            dir = 'R'
        windowsill_height = __buildGeshan(
            '隔扇',wallproxy,scale,location,dir)

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
        # 下抱框长度
        newLength = \
            BaoKuangDownObj.dimensions.z/2 - windowsill_height
        BaoKuangDownObj.dimensions.z = newLength
        # 下抱框位置
        BaoKuangDownObj.location.z = BaoKuangDownObj.location.z + geshan_height/2-newLength/2
        utils.applyTransfrom(BaoKuangDownObj,use_scale=True)
        # 添加槛墙
        __buildKanqiang(wallproxy,scale)

    # 5、批量设置所有子对象材质
    for ob in wallproxy.children:
        # 全部设置为朱漆材质
        # 其中槛窗的窗台为石质，并不会被覆盖
        mat.setShader(ob,mat.shaderType.REDPAINT)

    utils.focusObj(wallproxy)