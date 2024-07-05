# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   斗栱的营造
import bpy
import math
from mathutils import Vector

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from .data import ACA_data_template as tmpData
from . import utils
from . import buildFloor
from . import buildRoof

# 添加斗栱根节点
def __addDougongRoot(buildingObj:bpy.types.Object):
    # 设置目录
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('斗栱',parentColl=buildingColl) 
    
    # 载入数据
    bData : acaData = buildingObj.ACA_data # 载入数据

    # 新建或清空根节点
    dgrootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_DG_ROOT)
    if dgrootObj == None:
        # 创建根对象（empty）===========================================================
        # 相对于屋顶层根节点（挑檐桁下皮）
        root_z = -bData.dg_height
        bpy.ops.object.empty_add(
            type='PLAIN_AXES',location=(0,0,root_z))
        dgrootObj = bpy.context.object
        dgrootObj.name = "斗栱层"
        dgrootObj.ACA_data['aca_obj'] = True
        dgrootObj.ACA_data['aca_type'] = con.ACA_TYPE_DG_ROOT
        # 绑定在屋顶根节点下
        roofRootObj = utils.getAcaChild(
            buildingObj,con.ACA_TYPE_ROOF_ROOT)
        dgrootObj.parent = roofRootObj
    else:
        # 清空根节点
        utils.deleteHierarchy(dgrootObj)
        utils.focusCollByObj(dgrootObj)

    return dgrootObj

# 生成平板枋
# 采用贯穿整体建筑的方式，没有按照各间分别做
def __buildPingbanFang(dgrootObj:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(
        dgrootObj,con.ACA_TYPE_BUILDING)
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK
    # 获取地盘数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)

    # 平板枋，在根节点平面之下，便于整体控制
    extendLength = con.HENG_COMMON_D*dk*2
    # 檐面平板枋
    loc = (0,net_y[0],-con.PINGBANFANG_H*dk/2)
    dimensions =(
        bData.x_total + extendLength,
        con.PINGBANFANG_Y*dk,
        con.PINGBANFANG_H*dk
    )
    pingbanfangObj = utils.addCube(
            name="平板枋",
            location=loc,
            dimension=dimensions,
            parent=dgrootObj,
        ) 
    # 设置材质
    # 对前后面做fit方式，保证能够铺满这个材质
    utils.UvUnwrap(pingbanfangObj,'fit',fitIndex=[1,3])
    utils.copyMaterial(aData.mat_paint_walkdragon,pingbanfangObj)
    # 添加倒角
    modBevel:bpy.types.BevelModifier = \
        pingbanfangObj.modifiers.new('Bevel','BEVEL')
    modBevel.width = con.BEVEL_HIGH
    modBevel.segments = 2
    # 添加镜像
    utils.addModifierMirror(
        object=pingbanfangObj,
        mirrorObj=dgrootObj,
        use_axis=(False,True,False)
    )

    # 山面平板枋
    loc = (net_x[0],0,-con.PINGBANFANG_H*dk/2)
    dimensions =(
        bData.y_total + extendLength,
        con.PINGBANFANG_Y*dk,
        con.PINGBANFANG_H*dk
    )
    pingbanfangObj = utils.addCube(
            name="平板枋",
            location=loc,
            dimension=dimensions,
            rotation=(0,0,math.radians(90)),
            parent=dgrootObj,
        ) 
    # 设置材质
    utils.UvUnwrap(pingbanfangObj,'fit',fitIndex=[1,3])
    utils.copyMaterial(aData.mat_paint_walkdragon,pingbanfangObj)
    # 设置倒角
    modBevel:bpy.types.BevelModifier = \
        pingbanfangObj.modifiers.new('Bevel','BEVEL')
    modBevel.width = con.BEVEL_HIGH
    modBevel.segments = 2
    # 添加镜像
    utils.addModifierMirror(
        object=pingbanfangObj,
        mirrorObj=dgrootObj,
        use_axis=(True,False,False)
    )      
    return

# 生成连接枋
# 按照建筑面阔/进深，生成贯通全长的枋子，以便简化结构，提高效率
def __buildDGFangbyBuilding(dgrootObj:bpy.types.Object,
        fangSourceObj:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(
        dgrootObj,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK

    # 获取开间、进深数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)

    # 定位连接件
    yLoc = fangSourceObj.location.y * bData.dg_scale[1]
    zLoc = fangSourceObj.location.z * bData.dg_scale[2]
    if yLoc < 0:
        extendLength = con.HENG_COMMON_D*dk*2 - yLoc*2
    else:
        extendLength = 0
    # 做前后檐连接件
    loc = (0, net_y[0] + yLoc, zLoc)
    fangCopy = utils.copyObject(
        sourceObj = fangSourceObj,
        location = loc,
        parentObj = dgrootObj,
        singleUser=True
    )
    # 跟随缩放
    fangCopy.scale = bData.dg_scale
    utils.updateScene()
    fangCopy.dimensions.x = bData.x_total + extendLength
    utils.applyTransfrom(fangCopy,use_scale=True)
    # 处理UV
    utils.UvUnwrap(fangCopy,type='cube')
    # 镜像
    utils.addModifierMirror(
        object=fangCopy,
        mirrorObj=dgrootObj,
        use_axis=(False,True,False)
    )
    
    # 做两山连接件
    loc = (net_x[-1]- yLoc,0,zLoc)
    fangCopy = utils.copyObject(
        sourceObj = fangSourceObj,
        location = loc,
        parentObj = dgrootObj,
        singleUser=True
    )
    # 跟随缩放
    fangCopy.scale = bData.dg_scale
    utils.updateScene()
    fangCopy.dimensions.x = bData.y_total + extendLength
    utils.applyTransfrom(fangCopy,use_scale=True)
    fangCopy.rotation_euler.z = math.radians(90)
    # 处理UV
    utils.UvUnwrap(fangCopy,type='cube')
    # 镜像
    utils.addModifierMirror(
        object=fangCopy,
        mirrorObj=dgrootObj,
        use_axis=(True,False,False)
    )
    return

# 生成连接枋
# 为了便于根据每间面阔，精确的匹配攒当宽度的贴图，枋子在每间都生成
# 为了每间逐一生成，采用了额枋数据fang_net来处理
# 为了保持柱网层与斗栱层的独立，并没有把这段处理放在buildFloor的代码中
def __buildDGFangbyRoom(
        dgrootObj:bpy.types.Object,
        fangSourceObj:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(
        dgrootObj,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    
    # 获取开间、进深数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    
    # 根据建筑模版的参数设置分布
    # '0/0#1/0,1/0#2/0,2/0#3/0,3/0#3/1,3/1#3/2,3/2#3/3,3/3#2/3,2/3#1/3,1/3#0/3,0/3#0/2,0/2#0/1,0/1#0/0,'
    fangStr = bData.fang_net
    fangID_List = fangStr.split(',')
    for fangID in fangID_List:
        if fangID == '': continue
        setting = fangID.split('#')
        # 分解获取柱子编号
        pFrom = setting[0].split('/')
        pFrom_x = int(pFrom[0])
        pFrom_y = int(pFrom[1])
        vFrom = Vector((net_x[pFrom_x],net_y[pFrom_y],0))

        pTo = setting[1].split('/')
        pTo_x = int(pTo[0])
        pTo_y = int(pTo[1])
        vTo = Vector((net_x[pTo_x],net_y[pTo_y],0))

        # 计算柱子之间的距离和定位      
        fang_length = utils.getVectorDistance(vFrom,vTo)
        fang_rot = utils.alignToVector(vFrom-vTo)
        fang_x = (net_x[pFrom_x]+net_x[pTo_x])/2
        fang_y = (net_y[pFrom_y]+net_y[pTo_y])/2      
        offset_y = fangSourceObj.location.y * bData.dg_scale[1]
        offset_z = fangSourceObj.location.z * bData.dg_scale[2]
        loc = (fang_x, fang_y + offset_y, offset_z)
        # 生成
        fangCopy = utils.copyObject(
            sourceObj = fangSourceObj,
            location = loc,
            rotation= fang_rot,
            parentObj = dgrootObj,
            singleUser=True
        )

        # 跟随斗栱缩放
        fangCopy.scale = bData.dg_scale
        utils.updateScene()

        # 拉伸到开间面阔
        fangCopy.dimensions.x = fang_length
        utils.applyTransfrom(fangCopy,use_scale=True)

        # 处理UV
        if fangCopy.active_material.name == '栱垫板':
            utils.UvUnwrap(fangCopy,type='scale')
            utils.copyMaterial(
                aData.mat_paint_dgfillboard,
                fangCopy,
                override=True)
            # 设置材质中的斗栱攒数
            count = round(fang_length / bData.dg_gap)
            utils.setMatValue(
                mat=fangCopy.active_material,
                inputName='count',
                value=count)
        else:
            utils.UvUnwrap(fangCopy,'cube')
    return

# 排布斗栱
# 包括转角斗栱、柱头斗栱、补间斗栱
# 其中自动判断了屋顶类型，如，硬山、悬山，不做山面斗栱
def __buildDougong(dgrootObj:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(
        dgrootObj,con.ACA_TYPE_BUILDING)
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK

    # 获取开间、进深数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    
    # 转角斗栱，仅用于庑殿/歇山
    if (bData.roof_style in (
                con.ROOF_WUDIAN,
                con.ROOF_XIESHAN,
                con.ROOF_LUDING,)
            and aData.dg_corner_source != None):
        # 四个角柱坐标
        dgCornerArray = (
            (net_x[-1], net_y[0],0),
            (net_x[-1], net_y[-1],0),
            (net_x[0], net_y[-1],0),
            (net_x[0], net_y[0],0)
        )
        for n in range(len(dgCornerArray)) :
            dgCornerCopy:bpy.types.Object = utils.copyObject(
                sourceObj = aData.dg_corner_source,
                name = "转角斗栱",
                location = dgCornerArray[n],
                parentObj = dgrootObj,
                scale= bData.dg_scale,
                singleUser=True
            )
            dgCornerCopy.rotation_euler.z = math.radians(n * 90)

    # 柱头斗栱
    if aData.dg_piller_source != None:
        # 前后坡的柱头斗栱
        if bData.roof_style in (
                con.ROOF_WUDIAN,
                con.ROOF_XIESHAN,
                con.ROOF_LUDING,):
            # 庑殿/歇山有转角斗栱，所以四角柱头不做斗栱
            dgRange = range(1,len(net_x)-1) 
        else:
            # 硬山/悬山做到最后一个柱头
            dgRange = range(len(net_x)) 
        for n in dgRange : 
            dgPillerCopy:bpy.types.Object = utils.copySimplyObject(
                sourceObj = aData.dg_piller_source,
                name = "柱头斗栱",
                location=(net_x[n],net_y[0],0),
                scale= bData.dg_scale,
                parentObj = dgrootObj,
                singleUser=True
                )
            dgPillerCopy.rotation_euler.z = math.radians(0)
            utils.addModifierMirror(
                object=dgPillerCopy,
                mirrorObj=dgrootObj,
                use_axis=(False,True,False)
            )
        
        # 两山的柱头斗栱，仅庑殿/歇山做两山的斗栱
        if bData.roof_style in (
                con.ROOF_WUDIAN,
                con.ROOF_XIESHAN,
                con.ROOF_LUDING,):
            for n in range(len(net_y)-2) : 
                dgPillerCopy:bpy.types.Object = utils.copySimplyObject(
                    sourceObj = aData.dg_piller_source,
                    name = "柱头斗栱",
                    location=(net_x[-1],net_y[n+1],0),
                    scale= bData.dg_scale,
                    parentObj = dgrootObj,
                    singleUser=True
                    )
                dgPillerCopy.rotation_euler.z = math.radians(90)
                utils.addModifierMirror(
                    object=dgPillerCopy,
                    mirrorObj=dgrootObj,
                    use_axis=(True,False,False)
                )
    
    # 补间斗栱/平身科
    if aData.dg_fillgap_source != '' :
        # 前后坡的补间斗拱
        for n in range(len(net_x)-1) : 
            # 计算补间斗栱攒数
            pStart = net_x[n]
            pEnd = net_x[n+1]
            roomWidth = abs(pEnd - pStart)
            # 补偿float精度
            roomWidth += 0.001
            # 向下取整，宜疏不宜密
            dougong_count =  math.floor(roomWidth/ bData.dg_gap) 
            # 如果间距过大，可能无需补间斗栱
            if dougong_count == 0 : continue
            # 计算斗栱排布的实际间距
            dougong_span = abs(pEnd - pStart) / dougong_count
            for m in range(1,dougong_count):
                # 补间斗栱异色判断
                dgFillSource = None
                if (aData.dg_fillgap_alt_source != None
                            and m%2 == 0):
                        dgFillSource = aData.dg_fillgap_alt_source
                else:
                    dgFillSource = aData.dg_fillgap_source
                
                dgFillCopy:bpy.types.Object = utils.copySimplyObject(
                    sourceObj = dgFillSource,
                    name = "补间斗栱",
                    location=(net_x[n] + dougong_span * m,
                                net_y[-1],0),
                    scale= bData.dg_scale,            
                    parentObj = dgrootObj,
                    singleUser=True
                    )
                dgFillCopy.rotation_euler.z = math.radians(180)
                utils.addModifierMirror(
                    object=dgFillCopy,
                    mirrorObj=dgrootObj,
                    use_axis=(False,True,False)
                )
        
        # 两山
        if bData.roof_style in (
                con.ROOF_WUDIAN,
                con.ROOF_XIESHAN,
                con.ROOF_LUDING,):
            for n in range(len(net_y)-1) : 
                # 求平身科攒数
                pStart = net_y[n]
                pEnd = net_y[n+1]
                #dougong_count =  math.floor(abs(pEnd - pStart) / (con.DOUGONG_SPAN * dk)) # 向下取整
                dougong_count =  math.floor(abs(pEnd - pStart) / bData.dg_gap) 
                # 如果间距过大，可能无需补间斗栱
                if dougong_count == 0 : continue
                dougong_span = abs(pEnd - pStart) / dougong_count
                for m in range(1,dougong_count):
                    # 补间斗栱异色判断
                    dgFillSource = None
                    if (aData.dg_fillgap_alt_source != None
                                and m%2 == 0):
                            dgFillSource = aData.dg_fillgap_alt_source
                    else:
                        dgFillSource = aData.dg_fillgap_source

                    dgFillCopy:bpy.types.Object = utils.copySimplyObject(
                        sourceObj = dgFillSource,
                        name = "补间斗栱",
                        location=(net_x[0],
                            net_y[n] + dougong_span * m,0),
                        scale= bData.dg_scale,
                        parentObj = dgrootObj,
                        singleUser=True
                        )
                    dgFillCopy.rotation_euler.z = math.radians(270)
                    utils.addModifierMirror(
                        object=dgFillCopy,
                        mirrorObj=dgrootObj,
                        use_axis=(True,False,False)
                    )
    
    return

# 排布斗栱层
def buildDougong(buildingObj:bpy.types.Object): 
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    if bData.aca_type != con.ACA_TYPE_BUILDING:
        utils.showMessageBox("错误，输入的不是建筑根节点")
        return

    # 如果不使用斗栱，以下直接跳过
    if not bData.use_dg: return
    # 椽望定位依赖斗栱，强制生成
    if bData.is_showBPW : 
        bData['is_showDougong'] = True

    # 添加根节点以及目录
    dgrootObj = __addDougongRoot(buildingObj)

    # 1、生成平板枋
    if bData.use_pingbanfang:
        __buildPingbanFang(dgrootObj)

    # 2、布置斗栱/铺作======================================================
    # 斗栱缩放
    # 读取斗栱资产自定义属性dgHeight,dgExtend（需要在blender中定义）
    if 'dgHeight' in aData.dg_piller_source:
        originHeight = aData.dg_piller_source['dgHeight']
    else:
        originHeight = bData.dg_height
        utils.outputMsg("斗栱未定义默认高度")
    if 'dgExtend' in aData.dg_piller_source:
        originExtend = aData.dg_piller_source['dgExtend']
    else:
        originExtend = bData.dg_extend
        utils.outputMsg("斗栱未定义默认出跳")
    # 以用户定义的出跳，计算缩放
    scale = bData.dg_extend / originExtend
    # 斗栱高度，根据出跳缩放联动
    bData['dg_height'] = originHeight * scale
    # 暂存缩放比例，后续排布斗栱时使用
    bData['dg_scale'] = (scale,scale,scale)
    # 排布斗栱
    __buildDougong(dgrootObj)

    # 3、排布斗栱间的枋子
    # 循环处理各个连接件
    for fangObj in aData.dg_piller_source.children:
        if fangObj.name in ('栱垫板'):
            __buildDGFangbyRoom(dgrootObj,fangObj)
        else:
            __buildDGFangbyBuilding(dgrootObj,fangObj)
    
    # 重新聚焦在建筑根节点
    utils.focusObj(buildingObj)
    return {'FINISHED'}

# 更新斗栱高度
# 根据用户输入的斗栱出跳，转换斗栱挑高
def update_dgHeight(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    
    # 原始比例
    if 'dgHeight' in aData.dg_piller_source:
        originHeight = aData.dg_piller_source['dgHeight']
    else:
        originHeight = bData.dg_height
        utils.outputMsg("斗栱未定义该属性")
    if 'dgExtend' in aData.dg_piller_source:
        originExtend = aData.dg_piller_source['dgExtend']
    else:
        originExtend = bData.dg_extend
        utils.outputMsg("斗栱未定义该属性")

    # 以用户定义的出跳，计算缩放
    scale = bData.dg_extend / originExtend
    # 斗栱高度，根据出跳缩放联动
    bData['dg_height'] = originHeight * scale
    # 暂存缩放比例，后续排布斗栱时使用
    bData['dg_scale'] = (scale,scale,scale)

    # 重新生成
    buildRoof.buildRoof(buildingObj)
    return