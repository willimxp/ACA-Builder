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
    # todo：是采用用户可调整的设计值，还是取模板中定义的理论值？
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    # 收集扇心对象
    linxingList = []

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
    zibianObj = bpy.context.object
    # 仔边刷红漆
    mat.setMat(zibianObj,aData.mat_red)
    linxingList.append(bpy.context.object)

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
    linxinObj = bpy.context.object
    linxinObj.name = '棂心'
    linxinObj.data.name = '棂心'
    linxinObj.parent = parent
    linxinObj.scale = (scale.x- con.ZIBIAN_WIDTH*2*pd,
                   scale.z- con.ZIBIAN_WIDTH*2*pd,
                   1)
    linxinObj.rotation_euler.x = math.radians(90)
    # apply
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # 棂心贴图（三交六椀）
    mat.setMat(linxinObj,aData.mat_geshanxin)
    linxingList.append(linxinObj)

    # 合并扇心
    linxingObj = utils.joinObjects(linxingList)

    return linxingObj

# 构建槛框
# 基于输入的槛框线框对象
# 依赖于隔扇抹头计算出来的窗台高度
def __buildKanKuang(wallproxy,windowsillHeight):
    # 载入数据
    buildingObj,bData,wData = utils.getRoot(wallproxy)
    if buildingObj == None:
        utils.popMessageBox(
            "未找到建筑根节点或设计数据")
        return
    # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
    # todo：是采用用户可调整的设计值，还是取模板中定义的理论值？
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
        # 有横披窗、有槛墙：从中槛下皮到窗台上皮
        if use_KanWall:
            BaoKuangDownHeight = (
                wData.door_height - con.KAN_MID_HEIGHT*pd/2
                - windowsillHeight)
        # 有横披窗、无槛墙：从中槛下皮到下槛上皮
        else:        
            BaoKuangDownHeight = (
                wData.door_height - con.KAN_MID_HEIGHT*pd/2
                - con.KAN_DOWN_HEIGHT*pd)
    else:
        # 无横披窗、有槛墙：从窗台到上槛下皮
        if use_KanWall:
            BaoKuangDownHeight = (
                frame_height - con.KAN_UP_HEIGHT*pd 
                - windowsillHeight)
        # 无横披窗、无槛墙：从下抱框从上槛下皮到下槛上皮
        else:
            BaoKuangDownHeight = (
                frame_height - con.KAN_UP_HEIGHT*pd 
                - con.KAN_DOWN_HEIGHT*pd)
    # 位置Z：
    if use_KanWall:
        # 从窗台 + 半下抱框高
        BaoKuangDown_z = (
            windowsillHeight + BaoKuangDownHeight/2)
    else:
        # 从下槛 + 半下抱框高
        BaoKuangDown_z = (
            con.KAN_DOWN_HEIGHT*pd + BaoKuangDownHeight/2)
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
            KankuangObjs.append(linxinObj)
    
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

    # 5、批量设置所有子对象材质
    aData:tmpData = bpy.context.scene.ACA_temp
    for ob in KankuangObjs:
        # 全部设置为朱漆材质
        # 其中槛窗的窗台为石质，并不会被覆盖
        mat.setMat(ob,aData.mat_red)
    
    # 合并槛框
    kankuangObj = utils.joinObjects(KankuangObjs,'槛框')     
    # 添加bevel
    modBevel:bpy.types.BevelModifier = \
        kankuangObj.modifiers.new('Bevel','BEVEL')
    modBevel.width = con.BEVEL_HIGH

    # 输出下抱框，做为隔扇生成的参考
    return kankuangObj

# 构造隔扇数据
def __getGeshanData(
        wallproxy,
        scale,      # 隔扇尺寸
        gapNum,     # 抹头数量
        useKanwall, # 是否做槛墙
        dir='L'     # 隔扇方向：左开/右开
        ):
    # 载入数据
    buildingObj = utils.getAcaParent(wallproxy,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    # 考虑到柱的艺术夸张可能性，隔扇按6dk计算
    pd = con.PILLER_D_EAVE * dk
    # 输入的隔扇三维尺寸
    geshan_width,geshan_depth,geshan_height = scale
    # 边梃/抹头宽（看面）: 1/10隔扇宽（或1/5D）
    border_width = con.BORDER_WIDTH * pd
    # 边梃/抹头厚(进深)：1.5倍宽或0.3D，这里直接取了抱框厚度
    border_depth = con.BORDER_DEPTH * pd
    # 隔扇部件数据集合
    geshanParts = []  
    
    # 1-预布局：根据抹头数量，排布扇心、裙板、绦环
    motouData = {'name':'抹头',}
    taohuanData = {'name':'绦环'}
    shanxinData = {'name':'扇心'}    
    qunbanData = {'name':'裙板'} 
    # 二抹：0-抹头，1-扇心，2-抹头
    if gapNum >= 2:
        geshanParts.append(motouData.copy())
        geshanParts.append(shanxinData.copy())
        geshanParts.append(motouData.copy())
        if gapNum==2 and useKanwall:
            # 槛窗不做2抹，按3抹做，继续进入下一个判断
            gapNum=3
    # 三抹：0-抹头，1-扇心，2-抹头，【3-裙板，4-抹头】
    if gapNum >= 3:
        if not useKanwall:
            # 扇心下增加裙板
            geshanParts.append(qunbanData.copy())
            geshanParts.append(motouData.copy())
    # 四抹：0-抹头，1-扇心，2-抹头，【3-绦环，4，抹头】，
    # 5-裙板，6-抹头
    if gapNum >= 4:
        # 扇心和裙板之间加绦环
        geshanParts.insert(3,taohuanData.copy())
        geshanParts.insert(4,motouData.copy())
    # 五抹：0-抹头，1-扇心，2-抹头，3-绦环，4，抹头，
    # 5-裙板，6-抹头，【7-绦环，8-抹头】
    if gapNum >= 5:
        if not useKanwall:
            # 底部增加绦环
            geshanParts.append(taohuanData.copy())
            geshanParts.append(motouData.copy())
    # 六抹：【0-抹头，1-绦环】，2-抹头，3-扇心，4-抹头，
    # 5-绦环，6，抹头，7-裙板，8-抹头，9-绦环，10-抹头
    if gapNum >= 6:
        # 顶步增加绦环
        geshanParts.insert(0,motouData.copy())
        geshanParts.insert(1,taohuanData.copy())
    
    # 2-计算各部件的尺寸、位置
    width = geshan_width-border_width*2
    # 2.1，计算扇心高度，采用故宫王璞子书的做法
    # 参见汤崇平书“木装修”分册的p43
    if gapNum == 2:
        # 扇心做满
        heartHeight = geshan_height - border_width*2
    if gapNum == 3:
        # 扇心、裙板按6:4分
        heartHeight = (geshan_height - border_width*3)*0.6
    if gapNum == 4:
        # 减去4根抹头厚+绦环板(2抹高)
        heartHeight = (geshan_height - border_width*6)*0.6
    if gapNum == 5:
        # 减去5根抹头厚+2绦环板(4抹高)
        heartHeight = (geshan_height - border_width*9)*0.6
    if gapNum == 6:
        # 减去6根抹头厚+3绦环板(6抹高)
        heartHeight = (geshan_height - border_width*12)*0.6
    # 2.2，计算裙板高度
    qunbanHeight = heartHeight*4/6
    # 2.3, 依次推理抹头定位
    # Z坐标从上向下依次推理
    locZ = geshan_height/2
    for part in geshanParts:
        if part['name'] == '抹头':
            # 抹头的高度、厚度与边梃相同
            height = depth = border_width
        if part['name'] == '绦环':
            # 绦环板按1/3边梃厚
            depth = border_depth/3
            # 绦环板按2边梃高
            height = border_width*2
        if part['name'] == '扇心':
            # 扇心厚度同边梃厚
            depth = border_depth
            height = heartHeight
        if part['name'] == '裙板':
            # 裙板板按1/3边梃厚
            depth = border_depth/3
            height = qunbanHeight
        # 尺寸
        part['size'] = Vector((width,depth,height))
        # 定位
        part['loc'] = Vector((0,0,locZ-height/2))
        # 下一步定位推理
        locZ -= height

    # 3、计算边梃
    # 根据是否有槛窗，计算边梃尺寸
    if not useKanwall:
        # 边梃高度做到底部
        biantingHeight = geshan_height
    else:
        # 边梃高度仅做到窗台
        # 取上文中推理得到的locZ
        biantingHeight = (geshan_height/2 - locZ)
    scale = Vector((border_width,border_depth,biantingHeight))
    loc = Vector((-geshan_width/2+border_width/2,0,
            (geshan_height - biantingHeight)/2) ) 
    biantingDataL = {
        'name' : '边梃',
        'loc' : loc,
        'size': scale,
    }
    biantingDataR = {
        'name' : '边梃',
        'loc' : loc * Vector((-1,1,1)),
        'size': scale,
    }
    geshanParts.append(biantingDataL)
    geshanParts.append(biantingDataR)

    # 4、计算门轴
    # 门轴长度，比隔扇延长2个门楹长度（粗略）
    menzhouHeight = biantingHeight + con.MENYIN_HEIGHT*pd*2
    # 门轴位置分左开，右开
    if dir=='L':
        menzhouX = -geshan_width/2 + con.MENZHOU_R*pd
    else:
        menzhouX = geshan_width/2 - con.MENZHOU_R*pd
    # 门轴外皮与隔扇相切（实际应该是做成一体的）
    menzhouY = con.BORDER_DEPTH * pd/2 + con.MENZHOU_R * pd
    # 门轴与隔扇垂直对齐
    if not useKanwall:
        # 隔扇与门轴居中对齐
        menzhouZ = 0
    else:
        # 槛窗与门轴对齐
        menzhouZ = (geshan_height - biantingHeight)/2
    menzhouData = {
        'name':'门轴',
        'loc':Vector((menzhouX,menzhouY,menzhouZ)),
        'size': Vector((con.MENZHOU_R*pd,
                        con.MENZHOU_R*pd,
                        menzhouHeight)),
    }
    geshanParts.append(menzhouData)

    return geshanParts,locZ

# 构件隔扇，重构241213
def __buildGeshan(name,wallproxy,scale,location,dir='L'):
    # 载入数据
    buildingObj = utils.getAcaParent(wallproxy,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    wData:acaData = wallproxy.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    # 隔扇导角大小
    geshan_bevel = con.BEVEL_LOW

    # 1、隔扇根对象
    geshan_root = utils.addEmpty(
        name=name,
        location=location,
        parent=wallproxy,   # 绑定到外框父对象
    )
    
    # 2、构造隔扇数据
    geshanData,windowsillZ = __getGeshanData(
        wallproxy=wallproxy,
        scale=scale,
        gapNum=wData.gap_num,
        useKanwall=wData.use_KanWall,
        dir=dir
    )

    # 3、构造隔扇mesh
    for part in geshanData:
        # 绦环和裙板尺寸扩大，避免bevel的穿帮
        if part['name'] in ('裙板','绦环'):
            part['size'] += Vector((
                geshan_bevel*2,0,geshan_bevel*2))
        if part['name'] in ('抹头','绦环','裙板','边梃'):
            # 简单的构造立方体
            partObj = utils.addCube(
                    name=part['name'],
                    location=part['loc'],
                    dimension=part['size'],
                    parent=geshan_root,
                )
        if part['name'] == '扇心':
            # 构造扇心
            __buildShanxin(
                parent=geshan_root,
                scale=part['size'],
                location=part['loc'],
            )
        if part['name'] == '门轴':
            # 构造门轴
            menzhouObj = utils.addCylinder(
                radius = part['size'].x,
                depth = part['size'].z,
                location=part['loc'],
                name=part['name'],
                root_obj=geshan_root,  # 挂接在柱网节点下
            )

        # 设置材质
        partMat = None
        if part['name'] == '绦环':
            partMat = aData.mat_paint_doorring
        elif part['name'] == '裙板':
            partMat = aData.mat_paint_door
        else:
            partMat = aData.mat_red
        mat.setMat(partObj,partMat)
            
    # 隔扇子对象合并
    if bData.use_KanWall:
        newName = '隔扇窗'
    else:
        newName = '隔扇门'
    geshanObj = utils.joinObjects(
        geshan_root.children,
        newName=newName,
        baseObj=menzhouObj)
    geshanObj.parent = wallproxy
    geshanObj.location += geshan_root.location
    bpy.data.objects.remove(geshan_root)

    # 锁定旋转，仅允许Z轴开窗、开门
    geshanObj.lock_rotation = (True,True,False)

    # 添加整体bevel
    modBevel:bpy.types.BevelModifier = \
        geshanObj.modifiers.new('Bevel','BEVEL')
    modBevel.width = geshan_bevel

    return geshanObj,windowsillZ
    
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
    # todo：是采用用户可调整的设计值，还是取模板中定义的理论值？
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
    # 设置材质：石材
    mat.setMat(kanqiangObj,aData.mat_rock)
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

    # 设置材质
    for obj in kanQiangObjs:
        mat.setMat(obj,aData.mat_red)

    # 合并构件
    kangqiangObj = utils.joinObjects(kanQiangObjs,'槛墙')
    # 设置bevel
    modBevel:bpy.types.BevelModifier = \
            kangqiangObj.modifiers.new('Bevel','BEVEL')
    modBevel.width = con.BEVEL_HIGH

    return kangqiangObj

# 构建完整的隔扇
def buildDoor(wallProxy:bpy.types.Object):       
    # 载入设计数据
    buildingObj,bData,wData = utils.getRoot(wallProxy)
    aData:tmpData = bpy.context.scene.ACA_temp
    if buildingObj == None:
        utils.popMessageBox(
            "未找到建筑根节点或设计数据")
        return
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    pillerD = bData.piller_diameter
    # 分解槛框的长、宽、高
    frame_width,frame_depth,frame_height = wallProxy.dimensions
    # wallID
    wallID = wallProxy.ACA_data['wallID']

    # 清理之前的子对象
    utils.deleteHierarchy(wallProxy)

    # 收集槛框对象
    kankuangList = []
    geshanList = []

    # 1、构建槛框内的每一扇隔扇
    # 注意：先做隔扇是因为考虑到槛窗模式下，窗台高度依赖于隔扇抹头的计算结果
    # 隔扇数量
    geshan_num = wData.door_num
    geshan_total_width = frame_width - pillerD - con.BAOKUANG_WIDTH*pd*2
    # 隔扇宽度：抱框宽度 / 隔扇数量
    geshan_width = geshan_total_width/geshan_num
    # 隔扇高度
    if wData.use_topwin:
        # 有横披窗时，下抱框从中槛下皮到下槛上皮
        geshan_height = \
            (wData.door_height - con.KAN_MID_HEIGHT*pd/2) \
            - con.KAN_DOWN_HEIGHT*pd
    else:
        # 无横披窗时，下抱框从上槛下皮到下槛上皮
        geshan_height = \
            frame_height - con.KAN_UP_HEIGHT*pd \
            - con.KAN_DOWN_HEIGHT*pd
    scale = Vector((geshan_width-con.GESHAN_GAP,
                con.BAOKUANG_DEPTH * pd,
                geshan_height-con.GESHAN_GAP))
    # 隔扇z坐标
    geshanZ = con.KAN_DOWN_HEIGHT*pd + geshan_height/2
    for n in range(geshan_num):
        # 位置
        location = Vector((geshan_width*(geshan_num/2-n-0.5),   #向右半扇
                    0,geshanZ))
        # 左开还是右开
        if n%2 == 0: dir = 'L'
        else: dir = 'R'
        geshanObj,windowsillZ = __buildGeshan(
            '隔扇',wallProxy,scale,location,dir)
        geshanList.append(geshanObj)
        
    # 2、构建槛墙
    windowsillHeight = windowsillZ + geshanZ # 将窗台坐标从隔扇proxy转换到wallproxy
    windowsillHeight -= con.GESHAN_GAP/2 # 留出窗缝
    if wData.use_KanWall :
        # 窗台高度
        scale = Vector((
            wallProxy.dimensions.x,
            wallProxy.dimensions.y,
            windowsillHeight
        ))
        # 添加槛墙
        kanqiangObj = __buildKanqiang(wallProxy,scale)
        kankuangList.append(kanqiangObj)
    
    # 3、构建槛框，基于隔扇计算的窗台高度
    kankuangObj = __buildKanKuang(wallProxy,windowsillHeight)
    kankuangList.append(kankuangObj)

    # 4、构建走马板：针对重檐，装修不一定做到柱头，用走马板填充
    if bData.wall_span != 0 :
        wallHeadBoard = utils.addCube(
                name = "走马板",
                location=(0,0,
                    frame_height \
                        +bData.wall_span/2),
                dimension=(frame_width,
                           con.BOARD_YOUE_Y*dk,
                           bData.wall_span),
                parent=wallProxy,
            )
        mat.setMat(wallHeadBoard,aData.mat_red)
        kankuangList.append(wallHeadBoard)

    # 合并槛框
    kankuangJoined = utils.joinObjects(kankuangList,'隔扇槛框')
    # 将隔扇挂入槛框父节点
    for geshan in geshanList:
        utils.changeParent(geshan,kankuangJoined,resetOrigin=False)

    utils.focusObj(kankuangJoined)

    return kankuangJoined