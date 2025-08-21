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
from . import texture as mat

# 添加斗栱根节点
def __addDougongRoot(buildingObj:bpy.types.Object):
    # 设置目录
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection(
        con.COLL_NAME_DOUGONG,
        parentColl=buildingColl) 

    # 新建或清空根节点
    dgrootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_DG_ROOT)
    if dgrootObj == None:       
        # 计算位置
        bData : acaData = buildingObj.ACA_data
        zLoc = bData.platform_height + bData.piller_height 
        # 创建根对象（empty）
        dgrootObj = utils.addEmpty(
            name=con.COLL_NAME_DOUGONG,
            parent=buildingObj,
            location=(0,0,zLoc),)
        dgrootObj.ACA_data['aca_obj'] = True
        dgrootObj.ACA_data['aca_type'] = con.ACA_TYPE_DG_ROOT
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
    if (bData.use_double_eave and
        bData.combo_type == con.COMBO_DOUBLE_EAVE):
        extendLength = 0
    else:
        extendLength = bData.piller_diameter*2
    # 檐面平板枋
    loc = (0,net_y[0],con.PINGBANFANG_H*dk/2)
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
    # 添加倒角
    utils.addModifierBevel(
        object=pingbanfangObj,
        width=con.BEVEL_HIGH,
        segments=2
    )
    # 添加镜像
    utils.addModifierMirror(
        object=pingbanfangObj,
        mirrorObj=dgrootObj,
        use_axis=(False,True,False)
    )
    # 设置材质:平板枋走龙
    mat.paint(pingbanfangObj,con.M_FANG_PINGBAN)

    # 山面平板枋
    loc = (net_x[0],0,con.PINGBANFANG_H*dk/2)
    dimensions =(
        bData.y_total + extendLength,
        con.PINGBANFANG_Y*dk,
        con.PINGBANFANG_H*dk
    )
    pingbanfangObj = utils.addCube(
            name="平板枋.山面",
            location=loc,
            dimension=dimensions,
            rotation=(0,0,math.radians(90)),
            parent=dgrootObj,
        ) 
    # 设置倒角
    utils.addModifierBevel(
        object=pingbanfangObj,
        width=con.BEVEL_HIGH,
        segments=2
    )
    # 添加镜像
    utils.addModifierMirror(
        object=pingbanfangObj,
        mirrorObj=dgrootObj,
        use_axis=(True,False,False)
    )
    # 如果2坡顶，则做抱头裁剪
    if bData.roof_style in (
        con.ROOF_XUANSHAN,
        con.ROOF_XUANSHAN_JUANPENG,
        con.ROOF_YINGSHAN,
        con.ROOF_YINGSHAN_JUANPENG,
    ):
        pStart = Vector((0,0,0))
        pEnd = Vector((1,0,0))
        pCut = Vector((0,net_y[1],0))
        utils.addBisect(
            object=pingbanfangObj,
            pStart=pingbanfangObj.matrix_world @ pStart,
            pEnd=pingbanfangObj.matrix_world @ pEnd,
            pCut=pingbanfangObj.matrix_world @ pCut,
            clear_outer=True,
        )
        utils.addModifierMirror(
            object=pingbanfangObj,
            mirrorObj=dgrootObj,
            use_axis=(False,True,False),
        )

    # 设置材质:平板枋走龙
    mat.paint(pingbanfangObj,con.M_FANG_PINGBAN)
    return

# 生成连接枋
# 按照建筑面阔/进深，生成贯通全长的枋子，以便简化结构，提高效率
def __buildDGFangbyBuilding(dgrootObj:bpy.types.Object,
        fangSourceObj:bpy.types.Object):
    # 载入数据
    buildingObj = utils.getAcaParent(
        dgrootObj,con.ACA_TYPE_BUILDING)
    bData:acaData = buildingObj.ACA_data
    aData : tmpData = bpy.context.scene.ACA_temp
    dk = bData.DK

    # 获取开间、进深数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    
    # 定位连接件
    yLoc = fangSourceObj.location.y * bData.dg_scale[1]
    # 斗栱高度，考虑平板枋的抬升
    dgZ = 0
    if bData.use_pingbanfang:
        dgZ = con.PINGBANFANG_H * dk
    zLoc = dgZ + fangSourceObj.location.z * bData.dg_scale[2]
    
    # 转角出头的处理
    extendLength = 0
    # 悬山
    if bData.roof_style in (
            con.ROOF_XUANSHAN,
            con.ROOF_XUANSHAN_JUANPENG):
        # # 挑檐桁下，配合檐桁延长到悬出长度
        # if (yLoc + bData.dg_extend)<0.001:
        #     extendLength += con.YANCHUAN_EX*dk*2
        # # 其他连接件，如果有斗栱，做出梢
        # else:
        #     if bData.use_dg:
        #         extendLength += con.HENG_EXTEND*dk
        #250103 悬山统一出梢到2椽径
        extendLength += con.YANCHUAN_EX*dk*2
    # 硬山也为了承托斗栱，做了出梢
    if bData.roof_style in (
        con.ROOF_YINGSHAN,
        con.ROOF_YINGSHAN_JUANPENG):
        if bData.use_dg:
            extendLength += con.HENG_EXTEND*dk        
    # 四坡顶的转角按Y向出跳
    if (yLoc < 0 
        and bData.roof_style in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
            con.ROOF_LUDING,
            con.ROOF_BALCONY)):
        # 配合斗栱，做出跳
        extendLength += abs(yLoc)*2
        # 配合挑檐桁做出梢
        if (yLoc + bData.dg_extend)<0.001:
            extendLength += con.HENG_EXTEND*dk
        
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
    utils.applyTransform(fangCopy,use_scale=True)
    # 镜像
    utils.addModifierMirror(
        object=fangCopy,
        mirrorObj=dgrootObj,
        use_axis=(False,True,False)
    )
    # 设置材质
    if '挑檐枋' in fangSourceObj.name:
        # 设置工王云
        mat.paint(fangCopy,con.M_FANG_TIAOYAN,
                   override=True)
    else:
        # 根据缩放，更新UV
        mat.UvUnwrap(fangCopy,type='cube')
        # 设置斗栱配色
        mat.paint(fangCopy,con.M_FANG_DGCONNECT,
                   override=True)
    
    # 做两山连接件(仅适用四坡顶，不适用于二坡顶)
    if bData.roof_style in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
            con.ROOF_LUDING,
            con.ROOF_BALCONY,):
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
        utils.applyTransform(fangCopy,use_scale=True)
        fangCopy.rotation_euler.z = math.radians(90)
        # 镜像
        utils.addModifierMirror(
            object=fangCopy,
            mirrorObj=dgrootObj,
            use_axis=(True,False,False)
        )
        # 设置材质
        if '挑檐枋' in fangSourceObj.name:
            # 设置工王云
            mat.paint(fangCopy,con.M_FANG_TIAOYAN,
                   override=True)
        else:
            # 根据缩放，更新UV
            mat.UvUnwrap(fangCopy,type='cube')
            # 设置斗栱配色
            mat.paint(fangCopy,con.M_FANG_DGCONNECT,
                       override=True)
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
    dk = bData.DK
    aData : tmpData = bpy.context.scene.ACA_temp
    # 获取开间、进深数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)

    # 收集待生成的连接枋
    fangList = []
    # 斗栱高度，考虑平板枋的抬升
    dgZ = 0
    if bData.use_pingbanfang:
        dgZ = con.PINGBANFANG_H * dk
    # 前后檐排布
    for n in range(len(net_x)-1):
        length = net_x[n+1] - net_x[n]
        loc = Vector(((net_x[n+1] + net_x[n])/2,
               net_y[0] + fangSourceObj.location.y * bData.dg_scale[1],
               dgZ + fangSourceObj.location.z * bData.dg_scale[2]))
        fangList.append(
            {'len':length,
             'loc':loc,
             'rot':(0,0,0),
             'mirror':(False,True,False)})
    # 两山排布(仅庑殿、歇山、盝顶，不适用硬山、悬山、卷棚)
    if bData.roof_style in (
            con.ROOF_WUDIAN,
            con.ROOF_XIESHAN,
            con.ROOF_XIESHAN_JUANPENG,
            con.ROOF_LUDING,
            con.ROOF_BALCONY,):
        for n in range(len(net_y)-1):
            length = net_y[n+1] - net_y[n]
            loc = Vector((
                net_x[0] + fangSourceObj.location.x * bData.dg_scale[0],
                (net_y[n+1] + net_y[n])/2,
                dgZ + fangSourceObj.location.z * bData.dg_scale[2]))
            fangList.append(
                {'len':length,
                'loc':loc,
                'rot':(0,0,math.radians(90)),
                'mirror':(True,False,False)
                })
    
    # 生成所有的连接枋
    for fang in fangList:
        fangCopy = utils.copyObject(
            sourceObj = fangSourceObj,
            location = fang['loc'],
            rotation = fang['rot'],
            scale = bData.dg_scale,
            parentObj = dgrootObj,
            singleUser=True
        )
        utils.updateScene()
        # 拉伸到开间面阔
        fangCopy.dimensions.x = fang['len']
        utils.applyTransform(fangCopy,use_scale=True)
        # 根据拉伸，更新UV平铺
        mat.UvUnwrap(fangCopy,mat.uvType.CUBE)
        # 设置斗栱配色
        mat.paint(fangCopy,con.M_FANG_DGCONNECT,
                  override=True)
        # 设置对称
        utils.addModifierMirror(
            object=fangCopy,
            mirrorObj=dgrootObj,
            use_axis=fang['mirror']
        )
        # 栱垫板材质
        # 务必放在最后操作，该方法会删除原有的垫拱板，替换为新的mesh
        if '栱垫板' in fangSourceObj.name:
            if bData.dg_extend == 0 :
                # 一斗三升使用小号的栱垫板，只有一层正心瓜栱
                mat.paint(fangCopy,con.M_BOARD_DG_S,
                        override=True)
            else:
                # 普通的栱垫板有一层正心瓜栱，一层正心厢栱
                mat.paint(fangCopy,con.M_BOARD_DG,
                        override=True)
            
    return

# 放置柱头斗栱
def __buildPillerDG(name = '柱头斗栱',
                    location = (0,0,0),
                    scale = (1,1,1),
                    rotation = (0,0,0),
                    parent = None,
                    mirror = (False,False,False),
                    tailExtend = 0
                    ):
    # 数据准备
    aData:tmpData = bpy.context.scene.ACA_temp

    # 判断是否做平坐斗栱
    dgSource = aData.dg_piller_source
    if parent != None:
        buildingObj,bData,oData = utils.getRoot(parent)
        if buildingObj is not None:
            if bData.roof_style == con.ROOF_BALCONY:
                dgSource = aData.dg_balcony_piller_source
    
    # 复制对象
    dgPillerCopy:bpy.types.Object = utils.copySimplyObject(
        sourceObj = dgSource,
        name = name,
        location=location,
        scale= scale,
        rotation=rotation,
        parentObj = parent,
        singleUser=True
        )
    
    # 调整前后檐桃尖梁长度
    extendLength = tailExtend/scale[1]  # 考虑到斗口不同的缩放，还原到缩放前
    gnMod:bpy.types.NodesModifier = \
        dgPillerCopy.modifiers.get('dgPillerGN')
    if gnMod != None:
        # 强制每个对象的node group为单一用户
        gnMod.node_group = gnMod.node_group.copy()
        utils.setGN_Input(gnMod,"Length",extendLength)
    # UV 矫正
    mat.UvUnwrap(dgPillerCopy,type=mat.uvType.CUBE)
    
    # 镜像
    utils.addModifierMirror(
        object=dgPillerCopy,
        mirrorObj=parent,
        use_axis=mirror
    )
    return dgPillerCopy

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

    # 初始化斗栱数据，避免跨建筑时公用的aData干扰
    from . import template
    template.updateDougongData(buildingObj)

    # 获取开间、进深数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)

    # 斗栱高度，考虑平板枋的抬升
    dgZ = 0
    if bData.use_pingbanfang:
        dgZ = con.PINGBANFANG_H * dk

    # 转角斗栱，仅用于庑殿/歇山/平坐
    if (bData.roof_style in (
                con.ROOF_WUDIAN,
                con.ROOF_XIESHAN,
                con.ROOF_XIESHAN_JUANPENG,
                con.ROOF_LUDING,
                con.ROOF_BALCONY,)
            and aData.dg_corner_source != None):
        # 四个角柱坐标
        dgCornerArray = (
            (net_x[-1], net_y[0],dgZ),
            (net_x[-1], net_y[-1],dgZ),
            (net_x[0], net_y[-1],dgZ),
            (net_x[0], net_y[0],dgZ)
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
            # 设置斗栱配色
            mat.paint(dgCornerCopy,con.M_DOUGONG,override=True)

    # 柱头斗栱
    if aData.dg_piller_source != None:
        # 前后坡的柱头斗栱
        if bData.roof_style in (
                con.ROOF_WUDIAN,
                con.ROOF_XIESHAN,
                con.ROOF_XIESHAN_JUANPENG,
                con.ROOF_LUDING,
                con.ROOF_BALCONY):
            # 庑殿/歇山有转角斗栱，所以四角柱头不做斗栱
            dgRange = range(1,len(net_x)-1) 
        else:
            # 硬山/悬山做到最后一个柱头
            dgRange = range(len(net_x)) 
        for n in dgRange : 
            # 如果为廊间举架或盝顶，做抱头桃尖梁
            # 桃尖梁做廊间进深-1/4柱径（搭接了1/4更好看）
            if (bData.use_hallway or 
                bData.roof_style==con.ROOF_LUDING):
                # 廊间进深-1/4柱径（搭接了1/4更好看）
                taojianLength = (abs(net_y[1]-net_y[0]) 
                                 - bData.piller_diameter/4)
            # 否则桃尖梁做前后通檐
            else:
                taojianLength = bData.y_total / 2
            
            dgPillerCopy = __buildPillerDG(
                location=(net_x[n],net_y[0],dgZ),
                scale=bData.dg_scale,
                rotation=(0,0,0),
                parent=dgrootObj,
                mirror=(False,True,False),
                tailExtend=taojianLength
            )
            # 设置斗栱配色
            mat.paint(dgPillerCopy,con.M_DOUGONG,override=True)

            # 250718 暂时取消以下处理，会产生难以修复的破口，导致无法水密
            # 目前的各个斗栱的大小也暂时没有超出山墙
            # # 250621 硬山角柱上的柱头斗栱做裁剪，以免超出山墙
            # if (bData.roof_style in (
            #     con.ROOF_YINGSHAN,
            #     con.ROOF_YINGSHAN_JUANPENG,)
            #     and n in (0,len(net_x)-1)):
            #         # 计算裁剪点
            #         pStart = Vector((0,0,0))
            #         pEnd = Vector((0,1,0))
            #         pCut = Vector((net_x[n],net_y[0],0))
            #         # 第一个斗栱裁掉左侧，最后一个斗栱裁掉右侧
            #         if n == 0:
            #             clear_outer = True
            #             clear_inner = False
            #         else:
            #             clear_outer = False
            #             clear_inner = True
            #         utils.addBisect(
            #             object=dgPillerCopy,
            #             pStart=dgrootObj.matrix_world @ pStart,
            #             pEnd=dgrootObj.matrix_world @ pEnd,
            #             pCut=dgrootObj.matrix_world @ pCut,
            #             clear_outer = clear_outer,
            #             clear_inner = clear_inner,
            #         )
        
        # 两山的柱头斗栱，仅庑殿/歇山/平坐做两山的斗栱
        if bData.roof_style in (
                con.ROOF_WUDIAN,
                con.ROOF_XIESHAN,
                con.ROOF_XIESHAN_JUANPENG,
                con.ROOF_LUDING,
                con.ROOF_BALCONY,):
            for n in range(len(net_y)-2) : 
                # 廊间进深-1/4柱径（搭接了1/4更好看）
                taojianLength = (abs(net_x[1]-net_x[0]) 
                                 - bData.piller_diameter/4)

                dgPillerCopy = __buildPillerDG(
                    location=(net_x[-1],net_y[n+1],dgZ),
                    scale=bData.dg_scale,
                    rotation=(0,0,math.radians(90)),
                    parent=dgrootObj,
                    mirror=(True,False,False),
                    tailExtend=taojianLength
                )
                # 设置斗栱配色
                mat.paint(dgPillerCopy,con.M_DOUGONG,override=True)
    
    # 补间斗栱/平身科
    if aData.dg_fillgap_source != '' :
        # 强制斗栱间距最小为11斗口
        if bData.dg_gap < dk*11:
            bData['dg_gap'] = dk*11
        # 前后坡的补间斗拱
        for n in range(len(net_x)-1) : 
            # 计算补间斗栱攒数
            pStart = net_x[n]
            pEnd = net_x[n+1]
            roomWidth = abs(pEnd - pStart)
            # 补偿float精度
            roomWidth += 0.001
            # 向下取整，宜疏不宜密(攒当数，实际的补间斗栱数要-1)
            dougong_count =  math.floor(roomWidth/ bData.dg_gap) 
            # 如果间距过大，可能无需补间斗栱
            if dougong_count == 0 : continue
            # 计算斗栱排布的实际间距
            dougong_span = abs(pEnd - pStart) / dougong_count
            for m in range(1,dougong_count):
                # 补间斗栱异色判断
                # 柱头斗栱始终为绿，补间斗拱的颜色穿插反色，如，绿|蓝|绿|蓝|绿
                dgFillSource = None
                if (aData.dg_fillgap_alt_source != None
                            and m%2 == 1):
                        dgFillSource = aData.dg_fillgap_alt_source
                else:
                    dgFillSource = aData.dg_fillgap_source
                # 但如果补间攒当数为奇数(补间斗栱为偶数)，则中间两攒同色
                # 如，绿|蓝|绿|【蓝|蓝】|绿|蓝|绿
                if dougong_count%2 !=0 and m>= dougong_count/2:
                    if (aData.dg_fillgap_alt_source != None
                                and m%2 == 1):
                            dgFillSource = aData.dg_fillgap_source
                    else:
                        dgFillSource = aData.dg_fillgap_alt_source
                # 摆放斗栱
                dgFillCopy:bpy.types.Object = utils.copySimplyObject(
                    sourceObj = dgFillSource,
                    name = "补间斗栱",
                    location=(net_x[n] + dougong_span * m,
                                net_y[-1],dgZ),
                    scale= bData.dg_scale,            
                    parentObj = dgrootObj,
                    singleUser=True
                    )
                dgFillCopy.rotation_euler.z = math.radians(180)
                # 设置斗栱配色
                mat.paint(dgFillCopy,con.M_DOUGONG,override=True)
                utils.addModifierMirror(
                    object=dgFillCopy,
                    mirrorObj=dgrootObj,
                    use_axis=(False,True,False)
                )
        
        # 两山
        if bData.roof_style in (
                con.ROOF_WUDIAN,
                con.ROOF_XIESHAN,
                con.ROOF_XIESHAN_JUANPENG,
                con.ROOF_LUDING,
                con.ROOF_BALCONY,):
            for n in range(len(net_y)-1) : 
                # 求平身科攒数
                pStart = net_y[n]
                pEnd = net_y[n+1]
                roomWidth = abs(pEnd - pStart)
                # 补偿float精度
                roomWidth += 0.001
                # 向下取整，宜疏不宜密
                dougong_count =  math.floor(roomWidth/ bData.dg_gap) 
                # 如果间距过大，可能无需补间斗栱
                if dougong_count == 0 : continue
                dougong_span = abs(pEnd - pStart) / dougong_count
                for m in range(1,dougong_count):
                    # 补间斗栱异色判断
                    dgFillSource = None
                    if (aData.dg_fillgap_alt_source != None
                                and m%2 == 1):
                            dgFillSource = aData.dg_fillgap_alt_source
                    else:
                        dgFillSource = aData.dg_fillgap_source
                    # 但如果补间攒当数为奇数(补间斗栱为偶数)，则中间两攒同色
                    # 如，绿|蓝|绿|【蓝|蓝】|绿|蓝|绿
                    if dougong_count%2 !=0 and m>= dougong_count/2:
                        if (aData.dg_fillgap_alt_source != None
                                    and m%2 == 1):
                                dgFillSource = aData.dg_fillgap_source
                        else:
                            dgFillSource = aData.dg_fillgap_alt_source

                    dgFillCopy:bpy.types.Object = utils.copySimplyObject(
                        sourceObj = dgFillSource,
                        name = "补间斗栱",
                        location=(net_x[0],
                            net_y[n] + dougong_span * m,dgZ),
                        scale= bData.dg_scale,
                        parentObj = dgrootObj,
                        singleUser=True
                        )
                    dgFillCopy.rotation_euler.z = math.radians(270)
                    # 设置斗栱配色
                    mat.paint(dgFillCopy,con.M_DOUGONG,override=True)
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
        utils.popMessageBox("输入的不是建筑根节点")
        return

    # 如果不使用斗栱，以下直接跳过
    if not bData.use_dg: return

    # 添加根节点以及目录
    dgrootObj = __addDougongRoot(buildingObj)

    # 1、生成平板枋
    if bData.use_pingbanfang:
        __buildPingbanFang(dgrootObj)

    # 2、布置斗栱/铺作======================================================
    # 排布斗栱
    __buildDougong(dgrootObj)

    # 3、排布斗栱间的枋子
    # 判断是否做平坐斗栱
    dgSource = aData.dg_piller_source
    if bData.roof_style == con.ROOF_BALCONY:
        dgSource = aData.dg_balcony_piller_source

    # 循环处理各个连接件
    for fangObj in dgSource.children:
        if '栱垫板' in fangObj.name:
            __buildDGFangbyRoom(dgrootObj,fangObj)
        else:
            __buildDGFangbyBuilding(dgrootObj,fangObj)
    
    # 重新聚焦在建筑根节点
    utils.focusObj(buildingObj)
    return {'FINISHED'}

