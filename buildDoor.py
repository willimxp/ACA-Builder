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
def __buildShanxin(
        parent,
        scale:Vector,
        location:Vector,
        borderWidth=None,
        lingxinMat=None,):
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
    if borderWidth == None:
        borderWidth = con.ZIBIAN_WIDTH*pd
    if lingxinMat == None:
        lingxinMat = con.M_WINDOW_INNER

    # 扇心高度校验，以免出现row=0的异常
    linxingHeight = scale.z - borderWidth*2
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
        scale.x - borderWidth,
        scale.z - borderWidth, # 旋转90度，原Zscale给Yscale
        1)
    # apply scale
    utils.applyTransform(zibianObj,use_rotation=True,use_scale=True)
    # 转换为Curve
    bpy.ops.object.convert(target='CURVE')
    # 旋转所有的点45度，形成四边形
    bpy.ops.object.editmode_toggle()
    bpy.ops.curve.select_all(action='SELECT')
    bpy.ops.transform.tilt(value=math.radians(45))
    bpy.ops.object.editmode_toggle()
    # 设置Bevel
    zibianObj.data.bevel_mode = 'PROFILE'        
    zibianObj.data.bevel_depth = borderWidth  # 仔边宽度
    zibianObj.data.bevel_resolution = 0
    # 转为mesh
    bpy.ops.object.convert(target='MESH')
    zibianObj = bpy.context.object
    # 导角
    utils.addModifierBevel(zibianObj,con.BEVEL_LOW)
    # 仔边刷漆
    mat.paint(zibianObj,con.M_WINDOW)
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
    # 250717 为了实现水密，做成cube
    linxinDim = (scale.x- borderWidth*2,
                0.005,  # 5毫米厚度
                scale.z- borderWidth*2,)
    linxinObj = utils.addCube(
        location=location,
        dimension=linxinDim,
        parent=parent
    )
    # 棂心贴图（三交六椀）
    mat.paint(linxinObj,lingxinMat)
    linxingList.append(linxinObj)

    # 合并扇心
    linxingObj = utils.joinObjects(linxingList)

    return linxingObj

# 构造隔扇数据
# 做法二，按照梁思成和马炳坚的做法
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
    # 2.1，计算扇心高度，采用马炳坚做法
    # 参考汤崇平p43
    
    # 扇心满做
    if gapNum == 2:
        heartHeight = geshan_height - border_width*2
    # 从扇心底皮向上为0.6的隔扇高，减去最上面的一根抹头
    if gapNum in (3,4,5):
        # 无绦环板
        heartHeight = geshan_height*0.6 - border_width
    elif gapNum == 6:
        # 一个绦环板
        heartHeight = geshan_height*0.6 - border_width*4

    # 裙板高度在下部0.4隔扇高中，根据抹头和绦环板的高度调整
    if gapNum == 3:
        # 三抹：0-抹头，1-扇心，2-抹头，【3-裙板，4-抹头】
        qunbanHeight = geshan_height*0.4 - border_width*2
    if gapNum == 4:
        # 四抹：0-抹头，1-扇心，2-抹头，【3-绦环，4，抹头】，
        # 5-裙板，6-抹头
        qunbanHeight = geshan_height*0.4 - border_width*5
    if gapNum == 5:
        # 五抹：0-抹头，1-扇心，2-抹头，3-绦环，4，抹头，
        # 5-裙板，6-抹头，【7-绦环，8-抹头】
        qunbanHeight = geshan_height*0.4 - border_width*8
    if gapNum == 6:
        # 六抹：【0-抹头，1-绦环】，2-抹头，3-扇心，4-抹头，
        # 5-绦环，6，抹头，7-裙板，8-抹头，9-绦环，10-抹头
        qunbanHeight = geshan_height*0.4 - border_width*8
    
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
    # 门轴长度，上部穿过上窗楹，下部抵住下窗楹
    menzhouExUp = con.KAN_MID_HEIGHT*pd
    if useKanwall:
        # 下部抵住下窗楹
        menzhouExDown = (
            con.KAN_WIND_HEIGHT*pd 
            - con.MENYIN_HEIGHT*pd)
    else:
        # 下部抵住下门楹
        menzhouExDown = (
            con.KAN_DOWN_HEIGHT*pd
            - con.MENYIN_HEIGHT*pd
        )
    # 嵌入下门楹2cm
    menzhouExDown += 0.02
    menzhouHeight = biantingHeight + menzhouExUp + menzhouExDown
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
        menzhouZ = menzhouExUp/2 - menzhouExDown/2
    else:
        # 槛窗与门轴对齐
        menzhouZ = (geshan_height/2 
                    - biantingHeight/2
                    + menzhouExUp/2 
                    - menzhouExDown/2)
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
    wallType = wData['wallID'].split('#')[0]
    if wallType == con.ACA_WALLTYPE_GESHAN:
        use_kanwall = False
    elif wallType == con.ACA_WALLTYPE_WINDOW:
        use_kanwall = True
    else:
        raise Exception("构建隔扇时无法判断是否使用槛墙")
    
    # 提取geshanData
    geshanID = wallproxy.ACA_data['wallID']    
    geshanSetting = utils.getDataChild(
        contextObj=wallproxy,
        obj_type=con.ACA_WALLTYPE_GESHAN,
        obj_id=geshanID
    )
    if geshanSetting is None:
        raise Exception(f"无法找到geshanData:{geshanID}")

    # 1、隔扇根对象
    geshan_root = utils.addEmpty(
        name=name,
        location=location,
        parent=wallproxy,   # 绑定到外框父对象
    )
    
    # 2、构造隔扇数据
    # 250226 重构，采用梁思成和马炳坚的做法
    # 原来的故宫王璞子书的做法，暂时不用，保留__getGeshanData
    geshanData,windowsillZ = __getGeshanData(
        wallproxy=wallproxy,
        scale=scale,
        gapNum=geshanSetting.gap_num,
        useKanwall=use_kanwall,
        dir=dir
    )

    # 3、构造隔扇mesh
    for part in geshanData:
        # 绦环和裙板尺寸扩大，避免bevel的穿帮
        if part['name'] in ('裙板','绦环'):
            part['size'] += Vector((
                geshan_bevel*2,0,geshan_bevel*2))
        
        # 循环生成隔扇构件
        if part['name'] in ('抹头','绦环','裙板','边梃'):
            # 简单的构造立方体
            partObj = utils.addCube(
                    name=part['name'],
                    location=part['loc'],
                    dimension=part['size'],
                    parent=geshan_root,
                )
            utils.addModifierBevel(partObj,geshan_bevel,clamp=True)
        elif part['name'] == '扇心':
            # 构造扇心
            __buildShanxin(
                parent=geshan_root,
                scale=part['size'],
                location=part['loc'],
            )
        elif part['name'] == '门轴':
            # 构造门轴
            menzhouObj = utils.addCylinder(
                radius = part['size'].x,
                depth = part['size'].z,
                location=part['loc'],
                name=part['name'],
                root_obj=geshan_root,  # 挂接在柱网节点下
            )
            utils.addModifierBevel(menzhouObj,geshan_bevel)
            mat.paint(menzhouObj,con.M_WINDOW)

        # 设置材质
        partMat = None
        if part['name'] == '绦环':
            partMat = con.M_DOOR_RING
        elif part['name'] == '裙板':
            partMat = con.M_DOOR_BOTTOM
        else:
            partMat = con.M_WINDOW
        mat.paint(partObj,partMat)
            
    # 隔扇子对象合并
    if use_kanwall:
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

    return geshanObj,windowsillZ
    
# 构建槛墙
# 槛墙定位要与隔扇裙板上抹对齐，所以要根据隔扇的尺寸进行定位
def __buildKanqiang(wallproxy:bpy.types.Object
                    ,dimension):
    # 载入数据
    buildingObj,bData,wData = utils.getRoot(wallproxy)
    # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
    # todo：是采用用户可调整的设计值，还是取模板中定义的理论值？
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    pillerD = bData.piller_diameter
    # 分解槛框的长、宽、高
    frame_width,frame_depth,frame_height = wallproxy.dimensions
    # 解析wallProxy
    wallID = wallproxy.ACA_data['wallID']
    wallType = wallID.split('#')[0]

    kanQiangObjs = []

    # 风槛
    if wallType == con.ACA_WALLTYPE_FLIPWINDOW:
        # 支摘窗不做风槛
        scl1 = Vector((0,0,0))
    else:
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
        dimension.x,
        con.TABAN_DEPTH*pd,
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
        dimension.x-con.TABAN_EX,
        con.TABAN_DEPTH*pd-con.TABAN_EX,
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
    mat.paint(kanqiangObj,con.M_WINDOW_WALL)
    kanQiangObjs.append(kanqiangObj)

    # 设置材质
    for obj in kanQiangObjs:
        mat.paint(obj,con.M_WINDOW)

    # 合并构件
    kangqiangObj = utils.joinObjects(kanQiangObjs,'槛墙')
    kangqiangObj.parent = wallproxy
    # 设置bevel
    utils.addModifierBevel(kangqiangObj, con.BEVEL_HIGH)

    return kangqiangObj

# 营造板门
def buildDoor(wallProxy:bpy.types.Object):       
    # 载入设计数据
    buildingObj,bData,wData = utils.getRoot(wallProxy)
    if buildingObj == None:
        utils.popMessageBox(
            "未找到建筑根节点或设计数据")
        return

    # 清理之前的子对象
    utils.deleteHierarchy(wallProxy)

    # 解析wallProxy
    wallID = wallProxy.ACA_data['wallID']
    wallType = wallID.split('#')[0]

    # 3、构建槛框
    kankuangObj = __buildKanKuang(wallProxy)
    # 个性化设置参数的传递
    utils.copyAcaData(wallProxy,kankuangObj)
    # wallID不在propertyGroup中，需要单独传递
    kankuangObj.ACA_data['wallID'] = wallID

    # 4、构建子对象
    if wallType == con.ACA_WALLTYPE_MAINDOOR:
        # 构建板门
        __addMaindoor(kankuangObj)
    elif wallType in (con.ACA_WALLTYPE_GESHAN,
                      con.ACA_WALLTYPE_WINDOW):
        # 构建隔扇门/隔扇窗
        __addGeshan(kankuangObj)
    elif wallType == con.ACA_WALLTYPE_BARWINDOW:
        # 构建直棂窗
        __addBarwindow(kankuangObj)
    elif wallType == con.ACA_WALLTYPE_FLIPWINDOW:
        # 构建支摘窗
        __addFlipwindow(kankuangObj)
    else:
        raise Exception(f"无法构建子对象，未知的wallType：{wallType}")

    utils.focusObj(kankuangObj)

    return kankuangObj

# 构建板门的槛框
# 基于输入的槛框线框对象
# 依赖于隔扇抹头计算出来的窗台高度
def __buildKanKuang(wallproxy:bpy.types.Object):
    # 载入数据
    buildingObj,bData,wData = utils.getRoot(wallproxy)
    aData:tmpData = bpy.context.scene.ACA_temp
    if buildingObj == None:
        utils.popMessageBox(
            "未找到建筑根节点或设计数据")
        return
    # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
    # todo：是采用用户可调整的设计值，还是取模板中定义的理论值？
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    pillerD = bData.piller_diameter
    # 分解槛框的长、宽、高
    frame_width,frame_depth,frame_height = wallproxy.dimensions
    KankuangObjs = []

    # 提取childData    
    childData = utils.getDataChild(
        contextObj=wallproxy,
        obj_type=wData.aca_type,
        obj_id=wData['wallID']
    )
    if childData is None:
        raise Exception(f"无法找到childData:{wData.wallID}")
    
    doorWidth = ((frame_width
                  - pillerD
                  - con.BAOKUANG_WIDTH*pd*2)
                 *childData.doorFrame_width_per)   # 门口宽度
    # 解析wallProxy
    wallID = wallproxy.ACA_data['wallID']
    wallType = wallID.split('#')[0]

    # 定位参数-------------------------
    # 门口宽度限制：不超过开间，去除两侧抱框，去除柱径
    doorWMax = (frame_width
                - con.BAOKUANG_WIDTH * pd * 2
                - pillerD)
    if doorWidth > doorWMax:
        # 此时不做余塞板，门板直接做到抱框
        doorWidth = doorWMax
    
    # 250814 门口高度以外檐柱高做为限制，不再与frame_height关联
    # 以便在“九檩歇山前后廊”这样需要在廊间做装修时，获得一致的高度
    # 同时內檐装修也会自动按金柱的抬升用横披窗填充
    frameMax = bData.piller_height - con.EFANG_LARGE_H*dk
    if bData.use_smallfang:
        frameMax -= (con.EFANG_SMALL_H*dk
                       +con.BOARD_YOUE_H*dk)
    # 门高从额枋之下，减去上槛、下槛
    doorHeight = (frameMax 
                - con.KAN_DOWN_HEIGHT*pd
                - con.KAN_UP_HEIGHT*pd)
    # 是否使用横披窗
    topWinH = childData.topwin_height
    bUseTopwin = False
    if frame_height - frameMax > 0.00001:
        # 內檐装修，自动开启横披窗，并自动计算高度
        bUseTopwin = True
    if topWinH > 0:
        bUseTopwin = True
        # 减去中槛和横披窗高度
        doorHeight -= (topWinH
                       + con.KAN_MID_HEIGHT*pd)
    # 是否使用走马板
    topBoardHeight = childData.wall_span 
    bUseTopBoard = False
    if topBoardHeight > 0:
        bUseTopBoard = True
        # 走马板
        doorHeight -= topBoardHeight
    # 自动更新门口高度
    childData['doorFrame_height'] = doorHeight

    # 0、槛墙 ------------------------
    # 放在最前面做，影响到后续的下槛、下抱框等
    doorBottom = con.KAN_DOWN_HEIGHT*pd
    # 仅隔扇窗需要
    if wallType in (con.ACA_WALLTYPE_WINDOW,
                    con.ACA_WALLTYPE_BARWINDOW,
                    con.ACA_WALLTYPE_FLIPWINDOW,):
        # 计算窗台高度
        frameDim = Vector((doorWidth,0,doorHeight))
        # 抹头数量
        if wallType == con.ACA_WALLTYPE_WINDOW:
            # 只有隔扇窗可以根据抹头计算不同的高度
            gapNum = childData.gap_num
        else:
            # 直棂窗和支摘窗没有抹头数，按照3抹计算窗台高度
            gapNum = 3
        geshanData,windowsillZ = __getGeshanData(
            wallproxy=wallproxy,
            scale=frameDim,
            gapNum=gapNum,
            useKanwall=True,
            dir=dir
        )
        # 返回的窗台坐标是基于隔扇中心，转换到相对wallproxy位置
        doorBottom = (
            windowsillZ 
            + doorHeight/2
            + con.KAN_DOWN_HEIGHT*pd
            - con.GESHAN_GAP/2
        )
        # 支摘窗不做风槛，向下调整
        if wallType == con.ACA_WALLTYPE_FLIPWINDOW:
            doorBottom -= con.KAN_WIND_HEIGHT*pd
        # 窗台高度
        windowsillDim = Vector((
            wallproxy.dimensions.x,
            wallproxy.dimensions.y,
            doorBottom
        ))
        # 添加槛墙
        kanqiangObj = __buildKanqiang(wallproxy,windowsillDim)
        KankuangObjs.append(kanqiangObj)

    # 1、下槛 ---------------------
    # 仅板门、隔扇下槛，其他有窗台的不做下槛
    if wallType in (con.ACA_WALLTYPE_MAINDOOR,
                    con.ACA_WALLTYPE_GESHAN):
        KanDownLoc = Vector((0,0,
                    con.KAN_DOWN_HEIGHT*pd/2))
        KanDownDim = Vector((frame_width, # 长度随面宽
                    con.KAN_DOWN_DEPTH * pd, # 厚0.3D
                    con.KAN_DOWN_HEIGHT * pd, # 高0.8D
                    ))
        KanDownObj = utils.addCube(
            name="下槛",
            location=KanDownLoc,
            dimension=KanDownDim,
            parent=wallproxy,
        )
        # 倒角
        utils.addModifierBevel(KanDownObj,con.BEVEL_HIGH)
        KankuangObjs.append(KanDownObj)

    # 2、中槛 ---------------------
    # 中槛底皮高度: 下槛高度 + 门口高度
    midDownZ = doorHeight + con.KAN_DOWN_HEIGHT*pd
    KanMidLoc = Vector((0,0,
                midDownZ + con.KAN_MID_HEIGHT*pd/2))
    KanMidDim = Vector((frame_width, # 长度随面宽
                con.KAN_MID_DEPTH * pd, # 厚0.3D
                con.KAN_MID_HEIGHT * pd, # 高0.8D
                ))
    KanMidObj = utils.addCube(
        name="中槛",
        location=KanMidLoc,
        dimension=KanMidDim,
        parent=wallproxy,
    )
    # 倒角
    utils.addModifierBevel(KanMidObj,con.BEVEL_HIGH)
    KankuangObjs.append(KanMidObj)
        
    # 3、上槛 ---------------------
    # 有横披窗时才做中槛
    if bUseTopwin:
        # 上槛上皮高度
        topUpZ = frame_height
        # 减去跑马板高度
        if bUseTopBoard:
            topUpZ -= topBoardHeight
        if (topUpZ - midDownZ) > con.KAN_UP_HEIGHT*pd:
            KanUpLoc = Vector((0,0,
                    topUpZ - con.KAN_UP_HEIGHT*pd/2))
            KanUpDim = Vector((frame_width, # 长度随面宽
                        con.KAN_UP_DEPTH * pd, # 厚0.3D
                        con.KAN_UP_HEIGHT * pd, # 高0.8D
                        ))
            KanTopObj = utils.addCube(
                name="上槛",
                location=KanUpLoc,
                dimension=KanUpDim,
                parent=wallproxy,
            )
            # 倒角
            utils.addModifierBevel(KanTopObj,con.BEVEL_HIGH)
            KankuangObjs.append(KanTopObj)

    # 4、门框 --------------------
    # 门框始终存在，在100%满做时，取代下抱框
    # 定高：参考doorBottom，决定是下槛还是窗台
    KuangDoorH = (
            midDownZ - doorBottom)
    kuangDoorDim = Vector((
            con.BAOKUANG_WIDTH * pd, # 宽0.66D
            con.BAOKUANG_DEPTH * pd - 0.01, # 厚0.3D
            KuangDoorH, 
            ))
    # 根据门口大小定位
    kuangDoorX = doorWidth/2 + con.BAOKUANG_WIDTH * pd /2
    KuangDoorZ = (
        KuangDoorH/2 + doorBottom)
    KuangDoorLoc = Vector((kuangDoorX,0,KuangDoorZ))
    # 添加门框
    KuangDoorObj = utils.addCube(
        name="门框",
        location=KuangDoorLoc,
        dimension=kuangDoorDim,
        parent=wallproxy,
    )
    # 添加mirror
    utils.addModifierMirror(
        KuangDoorObj, 
        wallproxy, 
        use_axis=(True,False,False)
    )
    # 倒角
    utils.addModifierBevel(KuangDoorObj,con.BEVEL_HIGH)
    KankuangObjs.append(KuangDoorObj)
    
    # 5、下抱框 ---------------------
    if childData.doorFrame_width_per == 1:
        # 门口满铺时，以门框与下抱框
        pass
    else:
        # 定高：下抱框做到中槛
        KuangDownH = (
            midDownZ - doorBottom)
        KuangDownDim = Vector((
                    con.BAOKUANG_WIDTH * pd, # 宽0.66D
                    con.BAOKUANG_DEPTH * pd, # 厚0.3D
                    KuangDownH, 
                    ))
        # 定位Z：从下槛 + 半下抱框高
        KuangDownZ = (
            KuangDownH/2 + doorBottom)
        # 定位X：半柱间距 - 半柱径 - 半抱框宽度
        KuangDownX = frame_width/2 - pillerD/2 - con.BAOKUANG_WIDTH*pd/2
        KuangDownLoc = Vector((KuangDownX,0,KuangDownZ))
        # 添加下抱框
        KuangDownObj = utils.addCube(
            name="下抱框",
            location=KuangDownLoc,
            dimension=KuangDownDim,
            parent=wallproxy,
        )
        # 添加mirror
        utils.addModifierMirror(
            KuangDownObj, 
            wallproxy, 
            use_axis=(True,False,False)
        )
        # 倒角
        utils.addModifierBevel(KuangDownObj,con.BEVEL_HIGH)
        KankuangObjs.append(KuangDownObj)

    # 6、上抱框 ---------------------
    # 仅在做横披窗时，才做上抱框
    if bUseTopwin: 
    # 251022 这个修改出现了副作用，撤销
    # 251020 防止无用的上抱框
    # if (bUseTopwin and 
    #     
    #     (frame_height - frameMax > con.KAN_UP_HEIGHT*pd)): 
        KuangUpH = (
            topUpZ - midDownZ
            - con.KAN_UP_HEIGHT*pd
            - con.KAN_MID_HEIGHT*pd)
        KuangUpDim = Vector((
                    con.BAOKUANG_WIDTH * pd, # 宽0.66D
                    con.BAOKUANG_DEPTH * pd, # 厚0.3D
                    KuangUpH, 
                    ))
        # 定位Z：从下槛 + 半下抱框高
        KuangUpZ = (
            midDownZ + KuangUpH/2 + con.KAN_MID_HEIGHT*pd)
        # 定位X：半柱间距 - 半柱径 - 半抱框宽度
        KuangUpX = frame_width/2 - pillerD/2 - con.BAOKUANG_WIDTH*pd/2
        KuangUpLoc = Vector((KuangUpX,0,KuangUpZ))
        # 添加上抱框
        KuangUpObj = utils.addCube(
            name="上抱框",
            location=KuangUpLoc,
            dimension=KuangUpDim,
            parent=wallproxy,
        )
        # 添加mirror
        utils.addModifierMirror(
            KuangUpObj, 
            wallproxy, 
            use_axis=(True,False,False)
        )
        # 倒角
        utils.addModifierBevel(KuangUpObj,con.BEVEL_HIGH)
        KankuangObjs.append(KuangUpObj)

    # 7、余塞板 ---------------------
    if doorWidth >= (frame_width 
                    - con.BAOKUANG_WIDTH*pd*4
                    - pillerD
                    ):
        # 在下抱框和门框都完整显示前，无需余塞板
        pass
    else:
        boardYusaiWidth = (
            frame_width/2 
            - doorWidth/2
            - pillerD/2
            - con.BAOKUANG_WIDTH*pd*2
            + con.KANKUANG_INSET*2)
        boardYusaiDim = Vector((
                    boardYusaiWidth,
                    con.BOARD_YOUE_Y*dk, # 厚随由额垫板
                    KuangDoorH + con.KANKUANG_INSET*2, 
                    ))
        boardYusaiX = (
            doorWidth/2
            + con.BAOKUANG_WIDTH * pd
            + boardYusaiWidth/2
            - con.KANKUANG_INSET)
        boardYusaiLoc = Vector((boardYusaiX,0,KuangDownZ))
        boardYusaiObj = utils.addCube(
                    name = "余塞板",
                    location=boardYusaiLoc,
                    dimension=boardYusaiDim,
                    parent=wallproxy,
                )
        # 添加mirror
        utils.addModifierMirror(
            boardYusaiObj, 
            wallproxy, 
            use_axis=(True,False,False)
        )
        KankuangObjs.append(boardYusaiObj)
    
    # 8、腰枋 ----------------------
    if doorWidth >= (frame_width 
                    - con.BAOKUANG_WIDTH*pd*4
                    - pillerD
                    ):
        # 在下抱框和门框都完整显示前，无需腰枋
        pass
    else:
        fangMidWidth = (
            frame_width/2 
            - doorWidth/2
            - pillerD/2
            - con.BAOKUANG_WIDTH * pd * 2)
        fangMidDim = Vector((
                    fangMidWidth,
                    con.KAN_MID_DEPTH * pd, # 厚随由额垫板
                    con.KAN_MID_HEIGHT * pd, 
                    ))
        fangMidX = (
            doorWidth/2
            + con.BAOKUANG_WIDTH * pd
            + fangMidWidth/2)
        fangMidLoc = Vector((fangMidX,0,KuangDownZ))
        fangMidObj = utils.addCube(
            name="腰枋",
            location=fangMidLoc,
            dimension=fangMidDim,
            parent=wallproxy,
        )
        # 添加mirror
        utils.addModifierMirror(
            fangMidObj, 
            wallproxy, 
            use_axis=(True,False,False)
        )
        # 倒角
        utils.addModifierBevel(fangMidObj,con.BEVEL_HIGH)
        KankuangObjs.append(fangMidObj)

    # 9、迎风板 ---------------------
    if bUseTopwin:
        # 板门做迎风板
        if wallType == con.ACA_WALLTYPE_MAINDOOR:
            # 定高
            boardWindH = (topUpZ 
                        - midDownZ
                        - con.KAN_UP_HEIGHT * pd
                        - con.KAN_MID_HEIGHT * pd
                        + con.KANKUANG_INSET*2)
            boardWindW = (frame_width 
                        - pillerD
                        - con.BAOKUANG_WIDTH * pd * 2
                        + con.KANKUANG_INSET*2)
            boardWindDim = Vector((boardWindW, 
                        con.BOARD_YOUE_Y*dk, 
                        boardWindH,
                        ))
            boardWindZ = (topUpZ 
                        - con.KAN_UP_HEIGHT * pd
                        - boardWindH/2
                        + con.KANKUANG_INSET)
            boardWindLoc = (0,0,boardWindZ)
            boardWindObj = utils.addCube(
                        name = "迎风板",
                        location=boardWindLoc,
                        dimension=boardWindDim,
                        parent=wallproxy,
                    )
            KankuangObjs.append(boardWindObj)
        
    # 10、横披窗 ---------------------
    if bUseTopwin:    
        # 隔扇门/隔扇窗/直棂窗/支摘窗做横披窗
        if wallType in (
            con.ACA_WALLTYPE_WINDOW,
            con.ACA_WALLTYPE_GESHAN,
            con.ACA_WALLTYPE_BARWINDOW,
            con.ACA_WALLTYPE_FLIPWINDOW,
            ):

            if wallType in (
                    con.ACA_WALLTYPE_WINDOW,
                    con.ACA_WALLTYPE_GESHAN,
                ):
                # 隔扇门/隔扇窗的横披窗数量比隔扇少一扇
                window_top_num = childData.door_num - 1
                if window_top_num < 3:
                    window_top_num = 3
            else:
                # 直棂窗/支摘窗，始终做3面
                window_top_num = 3
            # 横披窗宽度:(柱间距-柱径-抱框*(横披窗数量+1))/3
            window_top_width = ((frame_width 
                                - pillerD 
                                - (window_top_num+1)
                                *con.BAOKUANG_WIDTH*pd)
                                /window_top_num)
            # 循环生成每一扇横披窗
            for n in range(1,window_top_num):
                # 横披间框：右抱框中心 - n*横披窗间隔 - n*横披窗宽度
                windowTopKuang_x = KuangUpX - con.BAOKUANG_WIDTH*pd*n \
                    - window_top_width * n
                windowTopKuangLoc = Vector((windowTopKuang_x,0,KuangUpZ))
                hengKuangObj = utils.addCube(
                    name="横披间框",
                    location=windowTopKuangLoc,
                    dimension=KuangUpDim,
                    parent=wallproxy,
                )
                # 倒角
                utils.addModifierBevel(hengKuangObj,con.BEVEL_HIGH)
                KankuangObjs.append(hengKuangObj)
            # 横披窗尺寸
            WindowTopScale = Vector((window_top_width, # 宽度取横披窗宽度
                        con.ZIBIAN_DEPTH*pd,
                    KuangUpH # 高度与上抱框相同
            ))
            # 填充棂心
            for n in range(0,window_top_num):
                windowTop_x = KuangUpX - \
                    (con.BAOKUANG_WIDTH*pd + window_top_width)*(n+0.5)
                WindowTopLoc =  Vector((windowTop_x,0,KuangUpZ))
                if wallType in (
                    con.ACA_WALLTYPE_WINDOW,
                    con.ACA_WALLTYPE_GESHAN,
                    con.ACA_WALLTYPE_FLIPWINDOW,
                ):
                    # 隔扇门/隔扇窗/支摘窗填充棂心
                    linxinObj = __buildShanxin(
                        wallproxy,WindowTopScale,WindowTopLoc)
                else:
                    # 直棂窗只用余塞板，不用棂条
                    yusaiScale = WindowTopScale + Vector((
                        con.KANKUANG_INSET*2,
                        0,
                        con.KANKUANG_INSET*2))
                    # 直棂窗填充余塞板
                    linxinObj = utils.addCube(
                        name = "余塞板",
                        location=WindowTopLoc,
                        dimension=yusaiScale,
                        parent=wallproxy,
                    )
                KankuangObjs.append(linxinObj)
    
    # 11、走马板 ---------------------
    if bUseTopBoard:
        boardTopH = topBoardHeight
        boardTopDim = Vector((frame_width, # 长度随面宽
                    con.BOARD_YOUE_Y*dk, # 厚随由额垫板
                    boardTopH, # 高
                    ))
        boardTopZ = frame_height - boardTopH/2
        boardTopLoc = (0,0,boardTopZ)
        boardTopObj = utils.addCube(
                    name = "走马板",
                    location=boardTopLoc,
                    dimension=boardTopDim,
                    parent=wallproxy,
                )
        KankuangObjs.append(boardTopObj)

    # 12、门枕 --------------------------
    # 仅板门需要
    if wallType == con.ACA_WALLTYPE_MAINDOOR:
        # 定位
        zhenX = (doorWidth/2 
                + con.MAINDOOR_DEPTH*pd/2 
                + con.DOOR_YANFENG*pd
                )
        zhenZ = con.DOOR_ZHEN_HEIGHT*pd/2
        zhenLoc = (zhenX,0,zhenZ)
        # 尺寸
        zhenDim = (con.DOOR_ZHEN_WIDTH*pd,
                con.DOOR_ZHEN_LENTH*pd,
                con.DOOR_ZHEN_HEIGHT*pd)
        # 生成
        zhenObj = utils.addCube(
                        name = "门枕",
                        location=zhenLoc,
                        dimension=zhenDim,
                        parent=wallproxy,
                    )
        # 添加mirror
        utils.addModifierMirror(
            zhenObj, 
            wallproxy, 
            use_axis=(True,False,False)
        )
        # 倒角
        utils.addModifierBevel(zhenObj,con.BEVEL_LOW)
        # 着色
        mat.paint(zhenObj,con.M_ROCK)
        KankuangObjs.append(zhenObj)
    
    # 13、门楹 ------------------------
    # 板门做连楹
    if wallType == con.ACA_WALLTYPE_MAINDOOR:
        # 定位
        yinY = con.KAN_DOWN_DEPTH*pd/2
        yinZ = (doorHeight 
                + con.KAN_DOWN_HEIGHT*pd
                + con.KAN_MID_HEIGHT*pd/2)
        yinLoc = Vector((0,yinY,yinZ))
        # 尺寸
        yinDim = Vector((frame_width,
                con.MENYIN_DEPTH*pd,
                con.MENYIN_HEIGHT*pd))
        # 生成
        yinObj = utils.drawHexagon(
                    yinDim,
                    yinLoc,
                    half=True,
                    name='门楹',
                    parent=wallproxy)
        # 倒角
        utils.addModifierBevel(yinObj,con.BEVEL_LOW)
        KankuangObjs.append(yinObj)
    # 隔扇门/隔扇窗做连二楹
    elif wallType in (con.ACA_WALLTYPE_GESHAN,
                      con.ACA_WALLTYPE_WINDOW,):
        geshan_num = childData.door_num
        dim = Vector((con.MENYIN_WIDTH*pd,
                    con.MENYIN_DEPTH*pd,
                    con.MENYIN_HEIGHT*pd))
        for n in range(geshan_num):
            # 仅做奇数，不做偶数
            if n%2 ==0 : continue
            # 横坐标，平均分配每扇隔扇的中点
            x = -doorWidth/2 + n*doorWidth/geshan_num
            # 与下槛内皮相平
            y = con.KAN_DOWN_DEPTH * pd/2
            z = (midDownZ
                 + con.KAN_MID_HEIGHT*pd
                 - con.MENYIN_HEIGHT*pd/2
                 )
            loc = Vector((x,y,z))
            menyinObj = utils.drawHexagon(
                dim,
                loc,
                half=True,
                parent = wallproxy,
                name = '上窗楹',
                )
            # 倒角
            utils.addModifierBevel(menyinObj,con.BEVEL_LOW)
            KankuangObjs.append(menyinObj)

            # 下窗楹定位
            if wallType == con.ACA_WALLTYPE_GESHAN:
                # 与下槛下皮相平
                z = (doorBottom 
                    - con.KAN_DOWN_HEIGHT*pd 
                    + con.MENYIN_HEIGHT*pd/2)
            elif wallType == con.ACA_WALLTYPE_WINDOW:
                # 与风槛下皮相平
                z = (doorBottom 
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
            # 倒角
            utils.addModifierBevel(menyinObj,con.BEVEL_LOW)
            KankuangObjs.append(menyinObj)
        
    # 14、门簪 ------------------------
    # 仅板门需要
    if (wallType == con.ACA_WALLTYPE_MAINDOOR
        and childData.door_num != 4):
        # 定位
        span = (doorWidth 
                + con.BAOKUANG_WIDTH*pd*2)/4
        zanX = span*1.5
        zanY = -con.KAN_UP_DEPTH*pd/2
        zanZ = yinZ # 与连楹对齐
        zanLoc = (zanX,zanY,zanZ)
        # 导入门簪
        zanObj = utils.copyObject(
            sourceObj=aData.door_zan,
            name='门簪',
            parentObj=wallproxy,
            location=zanLoc,
            singleUser=True
        )
        # 尺寸与中槛匹配
        zanObj.dimensions.z = (con.KAN_MID_HEIGHT*pd
                                -con.BEVEL_HIGH*2)
        utils.updateScene()
        zanObj.scale.y = zanObj.scale.z
        zanObj.scale.x = zanObj.scale.z
        utils.applyTransform(zanObj,use_scale=True)
        # Array
        utils.addModifierArray(
            object=zanObj,
            count=4,
            offset=(-span,0,0),
        )
        mat.paint(zanObj,con.M_MENZAN,override=True)
        KankuangObjs.append(zanObj)

    # 15、间框 ------------------------
    # 仅支摘窗需要
    if wallType == con.ACA_WALLTYPE_FLIPWINDOW:
        # 尺寸，复用门框尺寸
        kuangMidDim = kuangDoorDim
        # 定位，上下与门框对齐，水平居中
        KuangMidLoc = Vector((0,0,KuangDoorZ))
        # 添加门框
        KuangMidObj = utils.addCube(
            name="间框",
            location=KuangMidLoc,
            dimension=kuangMidDim,
            parent=wallproxy,
        )
        # 倒角
        utils.addModifierBevel(KuangMidObj,con.BEVEL_HIGH)
        KankuangObjs.append(KuangMidObj)

    # 批量设置所有子对象材质
    aData:tmpData = bpy.context.scene.ACA_temp
    for ob in KankuangObjs:
        # 全部设置为朱漆材质
        # 其中槛窗的窗台为石质，并不会被覆盖
        mat.paint(ob,con.M_WINDOW)

    # 合并槛框，以中槛为基础
    kankuangObj = utils.joinObjects(
        KankuangObjs,
        newName='槛框',
        baseObj=KanMidObj,
        )
    # origin从中槛中心，移到槛框底部
    utils.setOrigin(kankuangObj,
        Vector((0,0,
                (- doorHeight
                 - con.KAN_DOWN_HEIGHT*pd
                 - con.KAN_MID_HEIGHT*pd/2
                )
              ))
    )

    # 输出下抱框，做为隔扇生成的参考
    return kankuangObj

# 营造板门
def __addMaindoor(kankuangObj:bpy.types.Object):
    # 载入数据
    buildingObj,bData,wData = utils.getRoot(kankuangObj)
    aData:tmpData = bpy.context.scene.ACA_temp
    if buildingObj == None:
        utils.popMessageBox(
            "未找到建筑根节点或设计数据")
        return
    # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
    # todo：是采用用户可调整的设计值，还是取模板中定义的理论值？
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    pillerD = bData.piller_diameter
    
    # 提取maindoorData
    maindoorID = kankuangObj.ACA_data['wallID']    
    maindoorData = utils.getDataChild(
        contextObj=kankuangObj,
        obj_type=con.ACA_WALLTYPE_MAINDOOR,
        obj_id=maindoorID
    )
    if maindoorData is None:
        raise Exception(f"无法找到maindoorData:{maindoorID}")
    
    # 分解槛框的长、宽、高
    frame_width,frame_depth,frame_height = kankuangObj.dimensions
    holeHeight = maindoorData.doorFrame_height  # 门口高度
    holeWidth = ((frame_width
                  - pillerD
                  - con.BAOKUANG_WIDTH*pd*2)
                 *maindoorData.doorFrame_width_per)   # 门口宽度

    doorParts = []
    
    # 1、门板 --------
    # 宽度考虑门轴
    doorWidth = (holeWidth/maindoorData.door_num
                 + con.MAINDOOR_DEPTH*pd # 考虑门轴长度取门厚
                 + con.DOOR_YANFENG*pd
                 - con.DOOR_MIDFENG
                 )
    # 高度增加2个掩缝
    doorHeight = holeHeight + con.DOOR_YANFENG*pd*2
    doorDim = (doorWidth,
               con.MAINDOOR_DEPTH*pd,
               doorHeight)
    # 定位
    doorX = doorWidth/2 + con.DOOR_MIDFENG
    doorY = (con.KAN_DOWN_DEPTH*pd/2
        + con.MAINDOOR_DEPTH*pd/2)
    doorZ = (doorHeight/2 
             + con.KAN_DOWN_HEIGHT*pd
             - con.DOOR_YANFENG*pd)
    doorLoc = (doorX,doorY,doorZ)
    # 创建门板
    doorObj = utils.addCube(
                    name = "门扇",
                    location=doorLoc,
                    dimension=doorDim,
                    parent=kankuangObj,
                )
    # 倒角
    utils.addModifierBevel(doorObj,con.BEVEL_LOW)
    doorParts.append(doorObj)

    # 2、门轴 ----------------------
    # 定位
    zhouX = (holeWidth/maindoorData.door_num
            + con.MAINDOOR_DEPTH*pd/2 
            + con.DOOR_YANFENG*pd
             )
    zhouLoc = (zhouX,doorY,doorZ)
    # 半径
    zhouR = (con.MAINDOOR_DEPTH*pd/2
             - con.BEVEL_LOW)
    # 长度
    zhouHeight = (holeHeight
                  + con.KAN_MID_HEIGHT*pd*2
                  - con.BEVEL_HIGH*2)
    # 生成
    zhouObj = utils.addCylinder(
        radius = zhouR,
        depth = zhouHeight,
        location=zhouLoc,
        name='门轴',
        root_obj=kankuangObj, 
    )
    doorParts.append(zhouObj)

    # 3、门边 -------------------------
    # 上碰头
    headUp = (con.KAN_MID_HEIGHT*pd
              - con.MENYIN_HEIGHT*pd)
    # 下碰头
    headDown = con.KAN_DOWN_HEIGHT*pd/2
    # 定位
    bianX = (con.DOOR_BIAN_WIDTH*pd/2
            + con.DOOR_YANFENG*pd)
    bianZ = (holeHeight/2 
             + con.KAN_DOWN_HEIGHT*pd 
             + headUp/2 - headDown/2)
    bianLoc = (bianX,doorY,bianZ)
    # 尺寸
    bianDepth = (con.MAINDOOR_DEPTH*pd
                 - con.BEVEL_EXLOW*2)
    bianHeight = (holeHeight 
                  + headUp 
                  + headDown)
    bianDim = (con.DOOR_BIAN_WIDTH*pd,
               bianDepth,
               bianHeight)
    # 创建门边
    bianObj = utils.addCube(
                    name = "门边",
                    location=bianLoc,
                    dimension=bianDim,
                    parent=kankuangObj,
                )
    # 倒角
    utils.addModifierBevel(bianObj,con.BEVEL_LOW)
    doorParts.append(bianObj)

    # 4、门钉 ---------------------------
    if maindoorData.door_num != 4:
        dingNum = maindoorData.door_ding_num   # 实际的排布行数和列数 
        if dingNum > 0:
            # 导入门钉
            dingObj = utils.copyObject(
                sourceObj=aData.door_ding,
                name='门钉',
                parentObj=kankuangObj,
                singleUser=True
            )
            mat.paint(dingObj,con.M_GOLD,True)
            # 根据门口宽度，调整门钉尺寸
            # 门钉分布范围，门口一半，去掉门缝
            dingTotalWidth = holeWidth/maindoorData.door_num - con.DOOR_MIDFENG
            # 这里按照最多9路门钉，门钉中到中2倍门钉直径计算
            # 因为7路2.2D，5路4D，为了简化计算，就统一在9路定尺寸了
            dingWidth = dingTotalWidth/18
            dingObj.dimensions.x = dingWidth
            utils.updateScene()
            dingObj.scale.y = dingObj.scale.x
            dingObj.scale.z = dingObj.scale.x
            utils.applyTransform(dingObj,use_scale=True)
            # 排布门钉
            # 排布起点(右下角)，以门口进行计算，不能按门板进行计算
            dingX = holeWidth/maindoorData.door_num - dingTotalWidth/dingNum/2
            dingY = doorY - con.MAINDOOR_DEPTH*pd/2
            dingZ = con.KAN_DOWN_HEIGHT*pd + holeHeight/dingNum/2
            dingObj.location = (dingX,dingY,dingZ)
            # 添加Array
            # X向
            utils.addModifierArray(
                object=dingObj,
                count=dingNum,
                offset=(-dingTotalWidth/dingNum,0,0),
            )
            # Z向
            utils.addModifierArray(
                object=dingObj,
                count=dingNum,
                offset=(0,0,holeHeight/dingNum),
            )
            doorParts.append(dingObj)

    # 5、铺首 ---------------------------
    if maindoorData.door_num != 4:
        # 导入铺首
        pushouObj = utils.copyObject(
            sourceObj=aData.door_pushou,
            name='铺首',
            parentObj=kankuangObj,
            singleUser=True
        )
        mat.paint(pushouObj,con.M_GOLD,True)
        # 尺寸
        # 无门钉时，取腰枋高度
        pushouH = pushouObj.dimensions.z
        if dingNum > 0:
            # 有门钉时，不超过门钉间距
            span = holeHeight/dingNum - dingWidth
            if pushouH > span:
                pushouH = span
        pushouObj.dimensions.z = pushouH
        utils.updateScene()
        pushouObj.scale.y = pushouObj.scale.z
        pushouObj.scale.x = pushouObj.scale.z
        utils.applyTransform(pushouObj,use_scale=True)
        # 定位
        pushouX = (
            pushouObj.dimensions.x/2
            + con.DOOR_MIDFENG
            + doorWidth * 0.1
            )
        pushouY = doorY-con.MAINDOOR_DEPTH*pd/2
        if dingNum == 0 :
            # 无门钉时与腰枋对齐
            pushouZ = doorZ
        else:
            # 有门钉时，放置在中间两行门钉间
            pushouZ = (con.KAN_DOWN_HEIGHT*pd 
                    + round(dingNum/2)*holeHeight/dingNum)
        pushouObj.location = (pushouX,pushouY,pushouZ)
        doorParts.append(pushouObj)

    # 6、批量后处理 ----------------------
    # 批量设置所有子对象材质
    aData:tmpData = bpy.context.scene.ACA_temp
    for ob in doorParts:
        # 全部设置为朱漆材质
        # 其中槛窗的窗台为石质，并不会被覆盖
        mat.paint(ob,con.M_WINDOW)
    # 合并板门
    doorJoin = utils.joinObjects(
        doorParts,
        newName='板门门扇',
        baseObj=zhouObj,
        )
    # 限制旋转轴，仅允许Z轴开窗、开门
    doorJoin.lock_rotation = (True,True,False)

    # 镜像板门
    doorJoin2 = utils.copySimplyObject(doorJoin)
    doorJoin2.location.x = - doorJoin2.location.x
    doorJoin2.scale.x = -1
    utils.applyTransform2(doorJoin2,use_scale=True)
    # 修正Normal
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode='OBJECT')

    # 4扇的板门进行生成
    if maindoorData.door_num == 4:
        doorJoin3 = utils.copySimplyObject(doorJoin2)
        doorJoin3.location.x = doorJoin2.location.x + doorWidth*2 + con.DOOR_YANFENG*pd*2
        doorJoin4 = utils.copySimplyObject(doorJoin)
        doorJoin4.location.x = doorJoin.location.x - doorWidth*2 - con.DOOR_YANFENG*pd*2

    return doorJoin

# 添加隔扇
def __addGeshan(kankuangObj:bpy.types.Object):
    # 载入数据
    buildingObj,bData,wData = utils.getRoot(kankuangObj)
    aData:tmpData = bpy.context.scene.ACA_temp
    if buildingObj == None:
        utils.popMessageBox(
            "未找到建筑根节点或设计数据")
        return
    # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
    # todo：是采用用户可调整的设计值，还是取模板中定义的理论值？
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    pillerD = bData.piller_diameter

    # 提取geshanData
    geshanID = kankuangObj.ACA_data['wallID']    
    geshanData = utils.getDataChild(
        contextObj=kankuangObj,
        obj_type=con.ACA_WALLTYPE_GESHAN,
        obj_id=geshanID
    )
    if geshanData is None:
        raise Exception(f"无法找到geshanData:{geshanID}")
    
    # 分解槛框的长、宽、高
    frame_width,frame_depth,frame_height = kankuangObj.dimensions
    holeHeight = geshanData.doorFrame_height  # 门口高度
    holeWidth = ((frame_width
                  - pillerD
                  - con.BAOKUANG_WIDTH*pd*2)
                 *geshanData.doorFrame_width_per)   # 门口宽度
    geshanParts = []

    # 1、构建槛框内的每一扇隔扇
    # 注意：先做隔扇是因为考虑到槛窗模式下，窗台高度依赖于隔扇抹头的计算结果
    # 隔扇数量
    geshan_num = geshanData.door_num
    # 隔扇宽度
    geshan_width = holeWidth/geshan_num
    # 隔扇高度
    geshan_height = holeHeight
    geshanDim = Vector(
                (geshan_width - con.GESHAN_GAP,
                 con.BAOKUANG_DEPTH * pd,
                 geshan_height - con.GESHAN_GAP))
    # 隔扇z坐标
    geshanZ = con.KAN_DOWN_HEIGHT*pd + geshan_height/2
    for n in range(geshan_num):
        # 位置
        location = Vector(
            (geshan_width*(geshan_num/2-n-0.5),   #向右半扇
             0,geshanZ))
        # 左开还是右开
        if n%2 == 0: dir = 'L'
        else: dir = 'R'
        geshanObj,windowsillZ = __buildGeshan(
            name='隔扇',
            wallproxy=kankuangObj,
            scale=geshanDim,
            location=location,
            dir=dir)
        geshanParts.append(geshanObj)

    return

# 营造直棂窗
def __addBarwindow(kankuangObj:bpy.types.Object):
    # 载入数据
    buildingObj,bData,wData = utils.getRoot(kankuangObj)
    aData:tmpData = bpy.context.scene.ACA_temp
    if buildingObj == None:
        utils.popMessageBox(
            "未找到建筑根节点或设计数据")
        return
    # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
    # todo：是采用用户可调整的设计值，还是取模板中定义的理论值？
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    pillerD = bData.piller_diameter

    # 提取geshanData
    windowID = kankuangObj.ACA_data['wallID']    
    windowData = utils.getDataChild(
        contextObj=kankuangObj,
        obj_type=con.ACA_WALLTYPE_BARWINDOW,
        obj_id=windowID
    )
    if windowData is None:
        raise Exception(f"无法找到geshanData:{windowID}")
    
    # 分解槛框的长、宽、高
    frame_width,frame_depth,frame_height = kankuangObj.dimensions
    holeHeight = windowData.doorFrame_height  # 门口高度
    holeWidth = ((frame_width
                  - pillerD
                  - con.BAOKUANG_WIDTH*pd*2)
                 *windowData.doorFrame_width_per)   # 门口宽度
    
    # 计算窗台高度
    frameDim = Vector((holeWidth,0,holeHeight))
    gapNum = 6 # 不涉及抹头，直接固定
    geshanData,windowsillZ = __getGeshanData(
        wallproxy=kankuangObj,
        scale=frameDim,
        gapNum=gapNum,
        useKanwall=True,
        dir=dir
    )
    # 返回的窗台坐标是基于隔扇中心，转换到相对wallproxy位置
    barwinBottom = (
        windowsillZ 
        + holeHeight/2
        + con.KAN_DOWN_HEIGHT*pd
        - con.GESHAN_GAP/2
    )
    # 尺寸
    barwinH = holeHeight - barwinBottom + con.KAN_DOWN_HEIGHT*pd
    barwinDim = (holeWidth,0.01,barwinH)
    # 位置
    barwinZ = barwinBottom + barwinH/2
    barwinLoc = (0,0,barwinZ)

    zhilinParts = []
    
    # 仔边环绕
    # 创建一个平面，转换为curve，设置curve的横截面
    bpy.ops.mesh.primitive_plane_add(size=1,location=barwinLoc)
    zibianObj = bpy.context.object
    zibianObj.name = '仔边'
    zibianObj.parent = kankuangObj
    # 三维的scale转为plane二维的scale
    zibianObj.rotation_euler.x = math.radians(90)
    zibianObj.scale = (
        holeWidth - con.ZIBIAN_WIDTH*pd,
        barwinH - con.ZIBIAN_WIDTH*pd, # 旋转90度，原Zscale给Yscale
        1)
    # apply scale
    utils.applyTransform(zibianObj,use_rotation=True,use_scale=True)
    # 转换为Curve
    bpy.ops.object.convert(target='CURVE')
    # 旋转所有的点45度，形成四边形
    bpy.ops.object.editmode_toggle()
    bpy.ops.curve.select_all(action='SELECT')
    bpy.ops.transform.tilt(value=math.radians(45))
    bpy.ops.object.editmode_toggle()
    # 设置Bevel
    zibianObj.data.bevel_mode = 'PROFILE'        
    zibianObj.data.bevel_depth = con.ZIBIAN_WIDTH*pd  # 仔边宽度
    zibianObj.data.bevel_resolution = 0
    # 转为mesh
    bpy.ops.object.convert(target='MESH')
    zibianObj = bpy.context.object
    # 倒角
    utils.addModifierBevel(zibianObj,con.BEVEL_LOW)
    zhilinParts.append(zibianObj)

    # 直棂条
    # 计算间隔
    lintiaoSpan = con.ZIBIAN_WIDTH*pd*4
    lintiaoCount = round(holeWidth/lintiaoSpan)
    lintiaoSpan_real = holeWidth/lintiaoCount
    # 排布第一根
    lintiaoX = holeWidth/2 - lintiaoSpan_real
    lintiaoObj = utils.addCylinder(
        radius=con.ZIBIAN_WIDTH*pd,
        depth=barwinH-con.BEVEL_HIGH,
        name='直棂条',
        root_obj=kankuangObj,
        location=(lintiaoX,0,barwinZ),
        edge_num=3,
        rotation=((0,0,math.radians(180)))
    )
    # array排布
    utils.addModifierArray(
        object=lintiaoObj,
        count=lintiaoCount-1,
        offset=(-lintiaoSpan_real,0,0)
    )
    # Y向缩小50%
    lintiaoObj.scale.y = 0.5
    utils.applyTransform(lintiaoObj,use_scale=True,use_rotation=True)
    utils.applyAllModifer(lintiaoObj)
    zhilinParts.append(lintiaoObj)

    # 合并槛框，以中槛为基础
    zhilinObj = utils.joinObjects(
        zhilinParts,
        newName='直棂窗',
        baseObj=zibianObj,
        )
    mat.paint(zhilinObj,con.M_ZHILINGCHUANG)

    return zhilinObj

# 添加支摘窗
def __addFlipwindow(kankuangObj:bpy.types.Object):
    # 载入数据
    buildingObj,bData,wData = utils.getRoot(kankuangObj)
    aData:tmpData = bpy.context.scene.ACA_temp
    if buildingObj == None:
        utils.popMessageBox(
            "未找到建筑根节点或设计数据")
        return
    # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
    # todo：是采用用户可调整的设计值，还是取模板中定义的理论值？
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    pillerD = bData.piller_diameter

    # 提取geshanData
    windowID = kankuangObj.ACA_data['wallID']    
    windowData = utils.getDataChild(
        contextObj=kankuangObj,
        obj_type=con.ACA_WALLTYPE_FLIPWINDOW,
        obj_id=windowID
    )
    if windowData is None:
        raise Exception(f"无法找到geshanData:{windowID}")
    
    # 分解槛框的长、宽、高
    frame_width,frame_depth,frame_height = kankuangObj.dimensions
    holeHeight = windowData.doorFrame_height  # 门口高度
    holeWidth = ((frame_width
                  - pillerD
                  - con.BAOKUANG_WIDTH*pd*2)
                 *windowData.doorFrame_width_per)   # 门口宽度
    
    # 计算窗台高度
    frameDim = Vector((holeWidth,0,holeHeight))
    gapNum = 6 # 不涉及抹头，直接固定
    geshanData,windowsillZ = __getGeshanData(
        wallproxy=kankuangObj,
        scale=frameDim,
        gapNum=gapNum,
        useKanwall=True,
        dir=dir
    )
    # 返回的窗台坐标是基于隔扇中心，转换到相对wallproxy位置
    flipwinBottom = (
        windowsillZ 
        + holeHeight/2
        + con.KAN_DOWN_HEIGHT*pd
        - con.GESHAN_GAP/2
        - con.KAN_WIND_HEIGHT*pd
    )
    # 尺寸
    flipwinW = (holeWidth/2 
                 - con.BAOKUANG_WIDTH*pd/2
                 - con.GESHAN_GAP)
    flipwinH = (holeHeight/2
                - flipwinBottom/2 
                + con.KAN_DOWN_HEIGHT*pd/2
                - con.GESHAN_GAP*0.75)
    flipwinDim = (flipwinW,0.01,flipwinH)
    # 位置
    flipwinX = (con.BAOKUANG_WIDTH*pd/2
                + flipwinW/2
                + con.GESHAN_GAP/2)
    flipwinZ = (flipwinBottom 
                + flipwinH/2 
                + con.GESHAN_GAP/2)
    flipwinLoc = (flipwinX,0,flipwinZ)

    # 生成右下窗，做为四幅窗的模板
    # flipwinObj_RightDown = utils.addCube(
    #     location=flipwinLoc,
    #     dimension=flipwinDim,
    #     parent=kankuangObj
    # )
    
    flipwinParts = []

    # 仔边环绕
    # 创建一个平面，转换为curve，设置curve的横截面
    bpy.ops.mesh.primitive_plane_add(size=1,location=flipwinLoc)
    zibianObj = bpy.context.object
    zibianObj.name = '仔边'
    zibianObj.parent = kankuangObj
    # 三维的scale转为plane二维的scale
    zibianObj.rotation_euler.x = math.radians(90)
    zibianObj.scale = (
        flipwinW - con.BORDER_WIDTH*pd,
        flipwinH - con.BORDER_WIDTH*pd, # 旋转90度，原Zscale给Yscale
        1)
    # apply scale
    utils.applyTransform(zibianObj,use_rotation=True,use_scale=True)
    # 转换为Curve
    bpy.ops.object.convert(target='CURVE')
    # 旋转所有的点45度，形成四边形
    bpy.ops.object.editmode_toggle()
    bpy.ops.curve.select_all(action='SELECT')
    bpy.ops.transform.tilt(value=math.radians(45))
    bpy.ops.object.editmode_toggle()
    # 设置Bevel
    zibianObj.data.bevel_mode = 'PROFILE'        
    zibianObj.data.bevel_depth = con.BORDER_WIDTH*pd  # 仔边宽度
    zibianObj.data.bevel_resolution = 0
    # 转为mesh
    bpy.ops.object.convert(target='MESH')
    zibianObj = bpy.context.object
    # 仔边刷漆
    mat.paint(zibianObj,con.M_WINDOW)
    # 倒角
    utils.addModifierBevel(
        zibianObj,con.BEVEL_LOW)
    flipwinParts.append(zibianObj)

    # 做棂心
    shanxinDim = (Vector(flipwinDim) 
                  - Vector((
                      con.BORDER_WIDTH*pd*2,
                      0,
                      con.BORDER_WIDTH*pd*2,
                    ))
                  )
    shanxinObj = __buildShanxin(
        kankuangObj,
        shanxinDim,
        Vector(flipwinLoc),
        lingxinMat=con.M_LINXIN_WAN)
    flipwinParts.append(shanxinObj)

    # 合并
    flipwinObj_RightDown = utils.joinObjects(
        flipwinParts,"支摘窗")
    
    # 复制右上，左下，左上的三幅窗
    flipwinObj_RightUp = utils.copySimplyObject(
        flipwinObj_RightDown,
        location=(Vector(flipwinLoc) 
                  + Vector((0,0,flipwinH 
                            + con.GESHAN_GAP*0.5))
                  ),
        singleUser=True,
    )
    flipwinObj_LeftDown = utils.copySimplyObject(
        flipwinObj_RightDown,
        location=Vector(flipwinLoc) * Vector((-1,1,1)),
        singleUser=True,
    )
    flipwinObj_LeftUp = utils.copySimplyObject(
        flipwinObj_RightDown,
        location=(Vector(flipwinLoc) 
                  * Vector((-1,1,1))  
                  + Vector((0,0,flipwinH 
                            + con.GESHAN_GAP*0.5))
                  ),
        singleUser=True,
    )

    # 移动origin到顶部
    utils.setOrigin(flipwinObj_RightUp,
                    Vector((0,
                            - con.BORDER_WIDTH*pd/2,
                            flipwinH/2))
                    )
    utils.setOrigin(flipwinObj_LeftUp,
                    Vector((0,
                            - con.BORDER_WIDTH*pd/2,
                            flipwinH/2))
                    )
    # 锁定旋转
    flipwinObj_RightUp.lock_rotation = (False,True,True)
    flipwinObj_LeftUp.lock_rotation = (False,True,True)

    return