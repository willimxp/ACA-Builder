# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   平坐的营造
import bpy
import bmesh
import math
from mathutils import Vector
from typing import List

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from .data import ACA_data_template as tmpData
from . import utils
from . import buildFloor
from . import texture as mat

# 添加平坐根节点
def __addBalconyRoot(buildingObj:bpy.types.Object):
    # 设置目录
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection(
        con.COLL_NAME_BALCONY,
        parentColl=buildingColl) 

    # 新建或清空根节点
    balconyRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_BALCONY_ROOT)
    if balconyRootObj == None:       
        # 计算位置
        bData : acaData = buildingObj.ACA_data
        dk = bData.DK
        zLoc = bData.platform_height + bData.piller_height 
        # 如果有斗栱，抬高斗栱高度
        if bData.use_dg:
            zLoc += bData.dg_height
            # 是否使用平板枋
            if bData.use_pingbanfang:
                zLoc += con.PINGBANFANG_H*dk
        else:
            # 以大梁抬升檐桁垫板高度，即为挑檐桁下皮位置
            zLoc += con.BOARD_YANHENG_H*dk

        # 创建根对象（empty）
        balconyRootObj = utils.addEmpty(
            name=con.COLL_NAME_BALCONY,
            parent=buildingObj,
            location=(0,0,zLoc),)
        balconyRootObj.ACA_data['aca_obj'] = True
        balconyRootObj.ACA_data['aca_type'] = con.ACA_TYPE_BALCONY_ROOT
    else:
        # 清空根节点
        utils.deleteHierarchy(balconyRootObj)
        utils.focusCollByObj(balconyRootObj)

    return balconyRootObj

# 构造楼板
def __buildFloor(balconyRoot:bpy.types.Object):
    # 载入数据
    buildingObj,bData,oData = utils.getRoot(balconyRoot)
    dk = bData.DK
    
    # 1、构造楼板 --------------------------------
    # 平坐出挑，基于桁出梢
    floorExtend = con.BALCONY_EXTENT*dk*2*bData.dk_scale

    floorX = (bData.x_total 
              + bData.dg_extend*2 
              + floorExtend)
    floorY = (bData.y_total 
              + bData.dg_extend*2 
              + floorExtend)
    floorZ = con.BALCONY_FLOOR_H*dk
    floorDim = Vector((floorX,floorY,floorZ))
    floorLoc = Vector((0,0,floorZ/2))
    floorObj = utils.addCube(
        name='楼板',
        location=floorLoc,
        dimension=floorDim,
        parent=balconyRoot)
    mat.paint(floorObj,con.M_PLATFORM_FLOOR)

    # 2、构造挂檐板 --------------------------------
    eaveH = con.BALCONY_EAVE_H*dk
    eaveY = con.BALCONY_EAVE_Y*dk
    # 前后檐
    eaveDim = (floorX - eaveY*2, # 延长以便转角于两山相交
                 eaveY,
                 eaveH)
    eaveLoc = (0,
                 floorY/2-eaveY*1.5,
                 - eaveH/2)
    eaveObjFB = utils.addCube(
        name=f"挂檐板.前后檐",
        dimension=eaveDim,
        location=eaveLoc,
        parent=balconyRoot
    )
    utils.addModifierMirror(
        object=eaveObjFB,
        mirrorObj=balconyRoot,
        use_axis=(False,True,False)
    )
    utils.updateScene()
    utils.applyTransform(eaveObjFB,use_scale=True)
    mat.paint(eaveObjFB,con.M_GUAYANBAN)

    # 两山
    eaveDim = (eaveY,
                 floorY- eaveY*4,
                 eaveH)
    eaveLoc = (floorX/2-eaveY*1.5,
                 0,
                 - eaveH/2)
    eaveObjLR = utils.addCube(
        name=f"挂檐板.两山",
        dimension=eaveDim,
        location=eaveLoc,
        parent=balconyRoot
    )
    utils.addModifierMirror(
        object=eaveObjLR,
        mirrorObj=balconyRoot,
        use_axis=(True,False,False)
    )
    utils.updateScene()
    utils.applyTransform(eaveObjLR,use_scale=True)
    mat.paint(eaveObjLR,con.M_GUAYANBAN)

    # 3、构造地栿 --------------------------------
    if bData.use_balcony_railing:
        # 平坐出跳
        extend = (bData.dg_extend   # 斗栱出跳
                + con.BALCONY_EXTENT*dk # 平坐出跳，对齐桁出梢
                - con.RAILING_DEEPTH*dk/2 # 栏杆保留深度
                )
        
        # 因为栏杆按照0.08的斗口固定大小，所以这次的地栿也固定使用0.08斗口
        difuDeepth = con.RAILING_DIFU_Y*con.DEFAULT_DK
        difuHeight = con.RAILING_DIFU_H*con.DEFAULT_DK

        # 前后檐
        # 地栿长度
        difuLength = (floorX # 楼板总宽
                    - con.RAILING_DEEPTH*dk # 收一个栏杆的保留宽度
                    + difuDeepth) # 出头一个边框
        difuDim = (difuLength,difuDeepth,difuHeight)
        difuY = floorY/2 - con.RAILING_DEEPTH*dk/2
        difuZ = floorZ + difuHeight/2
        difuLoc = (0,difuY,difuZ)
        difuObjFB = utils.addCube(
            name=f"地栿.前后檐",
            dimension=difuDim,
            location=difuLoc,
            parent=balconyRoot
        )
        utils.addModifierMirror(
            object=difuObjFB,
            mirrorObj=balconyRoot,
            use_axis=(False,True,False)
        )
        # 导角
        utils.addModifierBevel(
            object=difuObjFB,width=con.BEVEL_LOW)
        mat.paint(difuObjFB,con.M_PAINT)

        # 两山
        # 地栿长度
        difuLength = (floorY # 楼板总宽
                    - con.RAILING_DEEPTH*dk # 收一个栏杆的保留宽度
                    - difuDeepth) # 出头一个边框
        difuDim = (difuDeepth,difuLength,difuHeight)
        difuX = floorX/2 - con.RAILING_DEEPTH*dk/2
        difuZ = floorZ + difuHeight/2
        difuLoc = (difuX,0,difuZ)
        difuObjLR = utils.addCube(
            name=f"地栿.两山",
            dimension=difuDim,
            location=difuLoc,
            parent=balconyRoot
        )
        utils.addModifierMirror(
            object=difuObjLR,
            mirrorObj=balconyRoot,
            use_axis=(True,False,False)
        )
        # 导角
        utils.addModifierBevel(
            object=difuObjLR,width=con.BEVEL_LOW)
        mat.paint(difuObjLR,con.M_PAINT)

    # 合并
    floorJoined = utils.joinObjects(
        [floorObj,eaveObjFB,eaveObjLR],
        newName='楼板')
    # 导角
    utils.addModifierBevel(floorJoined,con.BEVEL_LOW)
    return floorObj

# 构造每副栏杆的框架数据
def __buildProxy(balconyRoot:bpy.types.Object):
    # 载入数据
    buildingObj,bData,oData = utils.getRoot(balconyRoot)
    dk = bData.DK
    # 获取开间、进深数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)

    # 构造开间proxy
    proxyList = []
    proxy = {}

    # 平坐出跳
    extend = (bData.dg_extend   # 斗栱出跳
              + con.BALCONY_EXTENT*dk*bData.dk_scale # 平坐出跳，对齐桁出梢
              - con.RAILING_DEEPTH*dk/2 # 栏杆保留深度
            ) 
    # 楼板高度
    floorTop = con.BALCONY_FLOOR_H*dk
    
    # 前后檐排布
    for y in (0,bData.y_rooms):
        for x in range(bData.x_rooms):
            # 拼接栏杆ID
            proxy['id'] = f"{x}/{y}#{x+1}/{y}"
            # 北侧栏杆
            if net_y[y]>0:
                locY = net_y[y] + extend
                rotZ = math.radians(180)
            # 南侧栏杆
            else:
                locY = net_y[y] - extend
                rotZ = 0

            # 明间等直接适配开间宽度
            # 开间中心
            locX = (net_x[x] + net_x[x+1])/2
            # 开间长度
            length = net_x[x+1] - net_x[x]
            # 与邻间共用望柱
            length += con.RAILING_PILLER_D*dk
            # 防止z-fight
            length -= 0.001

            # 尽间：根据平坐出跳进行延长
            if x in (0,bData.x_rooms-1):
                length += extend
                if net_x[x]>0:
                    locX += extend/2
                else:
                    locX -= extend/2
                # 250924 如果只有一间，则再累计右侧延长
                if bData.x_rooms == 1:
                    length += extend
                    locX = 0 # 回到居中位置

            proxy['location'] = (locX,locY,floorTop)
            proxy['length'] = length
            proxy['rotation'] = (0,0,rotZ)
            proxyList.append(proxy.copy())

    # 两山排布
    for x in (0,bData.x_rooms):
        for y in range(bData.y_rooms):
            # 拼接栏杆ID
            proxy['id'] = f"{x}/{y}#{x}/{y+1}"            
            # 东侧栏杆
            if net_x[x]>0:
                locX = net_x[x] + extend
                rotZ = math.radians(90)
            # 西侧栏杆
            else:
                locX = net_x[x] - extend
                rotZ = math.radians(-90)

            # 明间等直接适配开间宽度
            # 开间中心
            locY = (net_y[y] + net_y[y+1])/2
            # 开间长度
            length = net_y[y+1] - net_y[y]
            # 与邻间共用望柱
            length += con.RAILING_PILLER_D*dk
            # 防止z-fight
            length -= 0.001

            # 尽间Y坐标考虑延长的偏移
            if y in (0,bData.y_rooms-1):
                length += extend
                if net_y[y]>0:
                    locY += extend/2
                else:
                    locY -= extend/2
                # 250924 如果只有一间，则再累计右侧延长
                if bData.y_rooms == 1:
                    length += extend
                    locY = 0 # 回到居中位置

            proxy['location'] = (locX,locY,floorTop)
            proxy['length'] = length
            proxy['rotation'] = (0,0,rotZ)
            proxyList.append(proxy.copy())

    return proxyList

# 构造栏杆
def __buildRailing(parentObj:bpy.types.Object,
                   proxy,
                   connect=False):
    buildingObj,bData,oData = utils.getRoot(parentObj)
    aData:tmpData = bpy.context.scene.ACA_temp

    # 权衡尺度
    dk = bData.DK
    # 因为考虑栏杆应该始终适应人的身高，而不要随着dk而变化
    # 所以以下将dk做了人为的固定
    dk = con.DEFAULT_DK

    # 各开间根节点，在两根柱子之间居中
    railingRoot = utils.addEmpty(
        name=f"栏杆.{proxy['id']}",
        location=proxy['location'],
        rotation=proxy['rotation'],
        parent=parentObj,
    )
    utils.hideObj(railingRoot)

    # 栏杆默认做满开间
    proxyW = proxy['length']

    # 判断是否做开口
    useGap = False
    if 'gap' in proxy:  # 自动生成的平坐没有gap属性
        # print(f"gap={proxy['gap']}")
        # 处理开口栏杆
        railingGap=proxy['gap']
        if railingGap > 0.0001:
            # 栏杆只做开口后的左半幅
            proxyW = proxy['length']*(1-railingGap)/2
            useGap = True

    # proxy，体现栏杆的实际体积
    proxyH = con.RAILING_PILLER_H*dk
    proxyD = con.RAILING_DEEPTH*dk
    proxyDim = (proxyW,proxyD,proxyH)
    # 考虑了开口和不开口的proxy定位
    if useGap:
        proxyX = - proxy['length']/2 + proxyW/2
    else:
        proxyX = 0
    proxyObj = utils.addCube(
        name=f"proxy.{proxy['id']}",
        dimension=proxyDim,
        location=(proxyX,0,proxyH/2),
        parent=railingRoot
    )
    # utils.hideObjFace(proxyObj)
    utils.hideObj(proxyObj)

    # 分栏：分栏数量没有明确规定，我按照望柱高再四舍五入
    sectionTotal = proxyW - con.RAILING_PILLER_D*dk*2 # 扣减两侧各1根望柱
    sectionCount = math.ceil(sectionTotal/(con.RAILING_PILLER_H*dk))
    # 安全保护，避免除数为0
    if sectionCount <= 0: sectionCount = 1
    sectionWidth = sectionTotal/sectionCount

    # 收集栏杆构件
    railingParts= []

    # 望柱
    pillerH = con.RAILING_PILLER_H*dk
    pillerD = con.RAILING_PILLER_D*dk
    pillerDim = (pillerD,
                 pillerD,
                 pillerH)
    # 无论是否开口，仅靠左侧柱
    pillerLoc = (-proxy['length']/2 + pillerD/2,
                 0,0)
    pillerObj = utils.copyObject(
        sourceObj=aData.railing_piller,
        name=f"望柱.{proxy['id']}",
        dimensions=pillerDim,
        location=pillerLoc,
        parentObj=railingRoot,
        singleUser=True,
    )
    # 着色
    mat.paint(pillerObj,con.M_RAILING,override=True)
    # 开口栏杆基于proxy对称
    if useGap:
        utils.addModifierMirror(pillerObj,
                                mirrorObj=proxyObj,
                                use_axis=(True,False,False))
    else:
        # 如果栏杆不连续，就左右都做望柱
        if not connect:
            utils.addModifierMirror(pillerObj,
                                    mirrorObj=railingRoot,
                                    use_axis=(True,False,False))
    
    railingParts.append(pillerObj)

    # 桪杖扶手，固定高度
    handrailWidth = proxyW - con.RAILING_PILLER_D*dk
    handrailDeepth = con.HANDRAIL_Y*dk
    handrailHeight = con.HANDRAIL_H*dk
    handrailDim = (handrailWidth,handrailDeepth,handrailHeight)
    handrailLoc = (proxyX,0,con.HANDRAIL_Z)
    handrailObj = utils.addCube(
        name=f"桪杖扶手.{proxy['id']}",
        dimension=handrailDim,
        location=handrailLoc,
        parent=railingRoot
    )
    # 导角
    utils.addModifierBevel(
        object=handrailObj,width=con.BEVEL_LOW)
    railingParts.append(handrailObj)

    # 折柱
    for n in range(sectionCount+1):
        # 折柱
        zzWidth = con.RAILING_ZZ_W*dk
        zzDeepth = con.RAILING_ZZ_Y*dk
        zzHeight = con.HANDRAIL_Z
        zzDim = (zzWidth,zzDeepth,zzHeight)
        zzX = (-proxy['length']/2 # 左侧边框
               + con.RAILING_PILLER_D*dk # 整根望柱
               # + con.RAILING_ZZ_W*dk/2  # 半根折柱
               + n*sectionWidth)
        zzLoc = (zzX,    # 依次排列
                 0,zzHeight/2)
        zzObj = utils.addCube(
            name=f"折柱.{proxy['id']}.{n}",
            dimension=zzDim,
            location=zzLoc,
            parent=railingRoot
        )
        # 导角
        utils.addModifierBevel(
            object=zzObj,width=con.BEVEL_LOW)
        railingParts.append(zzObj)

        # 净瓶
        vaseZ = (con.RAILING_DIFU_H*dk # 地栿
                 + con.RAILING_YAZI_H*dk # 牙子板
                 + con.RAILING_FANG_H*dk # 下枋
                 + con.RAILING_TAOHUAN_H*dk # 绦环板
                 + con.RAILING_FANG_H*dk # 中枋
                 )
        vaseLoc = (zzX,0,vaseZ)
        vaseObj = utils.copyObject(
                sourceObj=aData.railing_vase,
                name=f"净瓶.{proxy['id']}",
                location=vaseLoc,
                parentObj=railingRoot,
                singleUser=True,
            )
        # 拉伸净瓶高度
        vaseH = (con.HANDRAIL_Z # 桪杖扶手高度
                 - con.HANDRAIL_H*dk/2 # 桪杖扶手厚度
                 - vaseZ)   # 下部所有构件
        vaseObj.dimensions.z = vaseH
        # 着色
        mat.paint(vaseObj,con.M_RAILING,override=True)
        # 裁剪
        if n in (0,sectionCount):
            if n == 0:
                clear_inner=False
                clear_outer=True
            else:
                clear_inner=True
                clear_outer=False

            utils.addBisect(
                object=vaseObj,
                pStart=railingRoot.matrix_world @ Vector((0,0,0)),
                pEnd=railingRoot.matrix_world @ Vector((0,1,0)),
                pCut=railingRoot.matrix_world @ Vector(vaseLoc),
                clear_inner=clear_inner,
                clear_outer=clear_outer,
            )
            utils.shaderSmooth(vaseObj)
        railingParts.append(vaseObj)
        
    # 从下到上，累计高度
    sumZ = 0

    # 连续栏杆在楼板中做地栿
    difuHeight = con.RAILING_DIFU_H*dk
    if not connect:
        # 地栿
        # 地栿长度略出头，两侧各1/4望柱
        difuWidth = proxyW + con.RAILING_PILLER_D*dk/2
        difuDeepth = con.RAILING_DIFU_Y*dk
        difuDim = (difuWidth,difuDeepth,difuHeight)
        difuLoc = (proxyX,0,difuHeight/2)
        difuObj = utils.addCube(
            name=f"地栿.{proxy['id']}",
            dimension=difuDim,
            location=difuLoc,
            parent=railingRoot
        )
        # 导角
        utils.addModifierBevel(
            object=difuObj,width=con.BEVEL_LOW)
        railingParts.append(difuObj)
    sumZ += difuHeight

    # 牙子板
    # 尺寸
    yaziWidth = (sectionWidth # 分栏宽度
                    -con.RAILING_ZZ_W*dk)  # 扣除两侧各半根折柱
    yaziDeepth = con.RAILING_YAZI_Y*dk
    yaziHeight = con.RAILING_YAZI_H*dk
    yaziDim = (yaziWidth,yaziDeepth,yaziHeight)
    for n in range(sectionCount):
        # 定位
        yaziX = (-proxy['length']/2 # 左侧边线
                 + con.RAILING_PILLER_D*dk # 整根望柱
                 + (n+0.5)*con.RAILING_ZZ_W*dk # 折柱
                 + (n+0.5)*yaziWidth)
        yaziLoc = (yaziX,
                   0,
                   sumZ + yaziHeight/2)
        yaziObj = utils.addCube(
            name=f"牙子板.{proxy['id']}.{n}",
            dimension=yaziDim,
            location=yaziLoc,
            parent=railingRoot
        )
        # mat.paint(yaziObj,con.M_LINXIN_WAN)
        railingParts.append(yaziObj)
    sumZ += yaziHeight

    # 下枋
    downFangWidth = proxyW - con.RAILING_PILLER_D*dk
    downFangDeepth = con.RAILING_FANG_Y*dk
    downFangHeight = con.RAILING_FANG_H*dk
    downFangDim = (downFangWidth,downFangDeepth,downFangHeight)
    downFangLoc = (proxyX,0,sumZ + downFangHeight/2)
    downFangObj = utils.addCube(
        name=f"下枋.{proxy['id']}",
        dimension=downFangDim,
        location=downFangLoc,
        parent=railingRoot
    )
    # 导角
    utils.addModifierBevel(
        object=downFangObj,width=con.BEVEL_LOW)
    sumZ += downFangHeight
    railingParts.append(downFangObj)    

    # 绦环板
    for n in range(sectionCount):
        # 尺寸
        taohuanWidth = (sectionWidth # 分栏宽度
                     -con.RAILING_ZZ_W*dk)  # 扣除两侧各半根折柱
        taohuanDeepth = con.RAILING_TAOHUAN_Y*dk
        taohuanHeight = con.RAILING_TAOHUAN_H*dk
        taohuanDim = (taohuanWidth,taohuanDeepth,taohuanHeight)
        # 定位
        taohuanX = (-proxy['length']/2 # 左侧边线
                 + con.RAILING_PILLER_D*dk # 整根望柱
                 + (n+0.5)*con.RAILING_ZZ_W*dk # 半根折柱
                 + (n+0.5)*taohuanWidth)
        taohuanLoc = (taohuanX,
                   0,
                   sumZ + taohuanHeight/2)
        taohuanObj = utils.addCube(
            name=f"绦环板.{proxy['id']}.{n}",
            dimension=taohuanDim,
            location=taohuanLoc,
            parent=railingRoot
        )
        # mat.paint(taohuanObj,con.M_DOOR_RING)
        railingParts.append(taohuanObj)
    sumZ += taohuanHeight
    
    # 中枋
    midFangWidth = proxyW - con.RAILING_PILLER_D*dk
    midFangDeepth = con.RAILING_FANG_Y*dk
    midFangHeight = con.RAILING_FANG_H*dk
    midFangDim = (midFangWidth,midFangDeepth,midFangHeight)
    midFangLoc = (proxyX,0,sumZ + midFangHeight/2)
    midFangObj = utils.addCube(
        name=f"中枋.{proxy['id']}",
        dimension=midFangDim,
        location=midFangLoc,
        parent=railingRoot
    )
    # 导角
    utils.addModifierBevel(
        object=midFangObj,width=con.BEVEL_LOW)
    sumZ += downFangHeight
    railingParts.append(midFangObj)

    # 着色
    for part in railingParts:
        mat.paint(paintObj=part,
                    paintMat=con.M_PAINT)
    
    # 合并对象
    railingObj = utils.joinObjects(
        objList=railingParts,newName='栏杆')
    
    # 开口栏杆左右镜像
    if useGap:
        utils.addModifierMirror(
            object=railingObj,
            mirrorObj=railingRoot,
            use_axis=(True,False,False)
        )
    utils.applyAllModifer(railingObj)
    
    if not connect:
        # 独立栏杆挂在wallproxy下
        railingObj.parent = parentObj
        # 独立栏杆不需要父节点
        utils.delObject(railingRoot)
        utils.delObject(proxyObj)

    return railingObj

# 构造平座层
def buildBalcony(buildingObj:bpy.types.Object):
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    if not bData.use_dg:
        raise Exception("没有斗栱，无法营造平坐")
    
    # 添加平座层根节点
    balconyRoot = __addBalconyRoot(buildingObj)

    # 构造楼板
    floorObj = __buildFloor(balconyRoot)

    if bData.use_balcony_railing:
        # 构造proxy
        proxyList = __buildProxy(balconyRoot)

        # 构造栏杆
        for proxy in proxyList:
            railingObj = __buildRailing(
                parentObj=balconyRoot,
                proxy=proxy,
                connect=True,
                )
    
    return

# 手工添加栏杆/坐凳
def addRailing(wallProxy:bpy.types.Object):       
    # 载入设计数据
    buildingObj,bData,wData = utils.getRoot(wallProxy)
    if buildingObj == None:
        raise Exception(
            "未找到建筑根节点或设计数据")
        return
    dk = bData.DK
    
    # 提取railingData
    railingID = wallProxy.ACA_data['wallID']    
    railingData = utils.getDataChild(
        contextObj=wallProxy,
        obj_type=con.ACA_WALLTYPE_RAILILNG,
        obj_id=railingID
    )
    if railingData is None:
        raise Exception(f"无法找到railingData:{railingID}")
    
    # 栏杆长度，只能做在两个柱间
    railingLen = wallProxy.dimensions.x - bData.piller_diameter
    if railingLen <= 0:
        utils.outputMsg(f"此位置无法做栏杆/坐凳，已跳过{wallProxy.name}")
        return
    
    # 开口的最大值控制
    if railingData.gap > 0:
        # 栏杆最小值，单侧
        railingMin = con.RAILING_PILLER_D*dk*4
        # 开口最大值
        gapMax = railingLen - railingMin*2
        # 开口最大比例
        gapMax_rate =  gapMax/railingLen
        if railingData.gap > gapMax_rate:
            railingData['gap'] = gapMax_rate
            print("栏杆开口过大，已自动设置到最大值")
    
    # 创建proxyData
    proxy = {}
    proxy['id'] = railingID
    # 柱间距，扣除柱径
    proxy['length'] = railingLen
    proxy['location'] = (0,0,0)
    proxy['rotation'] = (0,0,0)
    proxy['gap'] = railingData.gap

    # 清理之前的子对象
    utils.deleteHierarchy(wallProxy)

    # 区分做栏杆还是坐凳
    wallType = railingID.split('#')[0]

    if wallType == con.ACA_WALLTYPE_RAILILNG:
        # 创建栏杆
        railingObj = __buildRailing(
            parentObj=wallProxy,
            proxy=proxy
        )
    elif wallType == con.ACA_WALLTYPE_BENCH:
        # 创建坐凳
        railingObj = __buildBench(
            parentObj=wallProxy,
            proxy=proxy
        )

    return railingObj

# 构造坐凳
def __buildBench(parentObj:bpy.types.Object,
                   proxy,):
    buildingObj,bData,oData = utils.getRoot(parentObj)
    pd = bData.piller_diameter
    # 栏杆默认做满开间
    proxyW = proxy['length']

    # 收集坐凳部件，以便合并
    benchParts = []

    # 坐凳面
    faceDim = Vector((
        proxyW + 1.5*pd,  # 六边形头部延伸到两根柱边缘
        con.BENCH_FACE_Y*pd, # 坐凳面宽1.2柱径
        con.BENCH_FACE_H, # 固定高度,45~70mm
    ))
    faceLoc = Vector((0,0,
        con.BENCH_FACE_Z)) # 离地面高度50~55cm
    benchFace:bpy.types.Object = utils.drawHexagon(
        faceDim,
        faceLoc,
        name='坐凳面',
        parent=parentObj
        )
    # 导角
    utils.addModifierBevel(
        object=benchFace,
        width=con.BEVEL_HIGH
    )
    # 着色
    mat.paint(benchFace,con.M_PAINT)
    benchParts.append(benchFace)

    # 坐凳边抹
    # 定位，从坐凳面向下半坐等面高，再向下半牙子板高
    yaziZ = (con.BENCH_FACE_Z 
             - con.BENCH_FACE_H/2
             - con.BENCH_YAZI_H/2)
    yaziLoc = (0,0,yaziZ)
    # 创建一个平面，转换为curve，设置curve的横截面
    bpy.ops.mesh.primitive_plane_add(size=1,location=yaziLoc)
    zibianObj = bpy.context.object
    zibianObj.name = '牙子仔边'
    zibianObj.parent = parentObj
    # 三维的scale转为plane二维的scale
    zibianObj.rotation_euler.x = math.radians(90)
    zibianObj.scale = (
        proxyW - con.BENCH_BORDER,
        con.BENCH_YAZI_H - con.BENCH_BORDER, # 旋转90度，原Zscale给Yscale
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
    zibianObj.data.bevel_depth = con.BENCH_BORDER
    zibianObj.data.bevel_resolution = 0
    # 转为mesh
    bpy.ops.object.convert(target='MESH')
    zibianObj = bpy.context.object
    # 倒角
    utils.addModifierBevel(zibianObj,con.BEVEL_LOW)
    # 着色
    mat.paint(zibianObj,con.M_PAINT)
    benchParts.append(zibianObj)

    # 做棂心
    shanxinDim = (proxyW - con.BENCH_BORDER*2,
                  0.01,
                  con.BENCH_YAZI_H - con.BENCH_BORDER*2,)
    from . import buildDoor
    shanxinObj = buildDoor.__buildShanxin(
        parentObj,
        Vector(shanxinDim),
        Vector(yaziLoc),
        lingxinMat=con.M_LINXIN_WAN)
    utils.addModifierBevel(
        shanxinObj,con.BEVEL_LOW)
    benchParts.append(shanxinObj)

    # 合并构件
    benchObj = utils.joinObjects(benchParts,'坐凳')

    return benchObj