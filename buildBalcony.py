# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   平坐的营造
import bpy
import bmesh
import math
from mathutils import Vector

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

        # 平坐斗栱的枋子在素材库中统一加高了一斗口
        zLoc += dk

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
    
    # 构造楼板
    floorX = (bData.x_total 
              + bData.dg_extend*2 
              + con.BALCONY_EXTENT*dk*2)
    floorY = (bData.y_total 
              + bData.dg_extend*2 
              + con.BALCONY_EXTENT*dk*2)
    floorZ = con.BALCONY_FLOOR_H*dk
    floorDim = Vector((floorX,floorY,floorZ))
    floorLoc = Vector((0,0,floorZ/2))
    floorObj = utils.addCube(
        name='楼板',
        location=floorLoc,
        dimension=floorDim,
        parent=balconyRoot)
    mat.paint(floorObj,con.M_PLATFORM_FLOOR)

    # 构造挂檐板
    eaveH = con.BALCONY_EAVE_H*dk
    eaveY = con.BALCONY_EAVE_Y*dk
    # 前后檐
    eaveDim = (floorX + eaveY*2, # 延长以便转角于两山相交
                 eaveY,
                 eaveH)
    eaveLoc = (0,
                 floorY/2+eaveY/2,
                 floorZ - eaveH/2)
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
    mat.paint(eaveObjFB,con.M_PAINT)

    # 两山
    eaveDim = (eaveY,
                 floorY,
                 eaveH)
    eaveLoc = (floorX/2+eaveY/2,
                 0,
                 floorZ - eaveH/2)
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
    mat.paint(eaveObjLR,con.M_PAINT)

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
              + con.BALCONY_EXTENT*dk # 平坐出跳，对齐桁出梢
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

            # 定位
            locX = (net_x[x] + net_x[x+1])/2
            # 定长
            length = net_x[x+1] - net_x[x]
            # 尽间X坐标考虑延长的偏移
            if x in (0,bData.x_rooms-1):
                length += extend
                if net_x[x]>0:
                    locX += extend/2
                else:
                    locX -= extend/2

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

            # 定位
            locY = (net_y[y] + net_y[y+1])/2
            # 定长
            length = net_y[y+1] - net_y[y]
            # 尽间Y坐标考虑延长的偏移
            if y in (0,bData.y_rooms-1):
                length += extend
                if net_y[y]>0:
                    locY += extend/2
                else:
                    locY -= extend/2

            proxy['location'] = (locX,locY,floorTop)
            proxy['length'] = length
            proxy['rotation'] = (0,0,rotZ)
            proxyList.append(proxy.copy())

    return proxyList

# 构造栏杆
def __buildRailing(balconyRoot:bpy.types.Object,
                   proxy):
    buildingObj,bData,oData = utils.getRoot(balconyRoot)
    dk = bData.DK
    railingParts= []
    railingNoBevel = []
    proxyW = proxy['length']
    # 分栏：分栏数量没有明确规定，我按照望柱高再四舍五入
    sectionTotal = proxyW - con.RAILING_PILLER_D*dk # 扣减两侧各半根望柱
    sectionCount = round(sectionTotal/con.RAILING_PILLER_H)
    sectionWidth = sectionTotal/sectionCount

    # 各开间根节点
    railingRoot = utils.addEmpty(
        name=f"栏杆.{proxy['id']}",
        location=proxy['location'],
        rotation=proxy['rotation'],
        parent=balconyRoot,
    )
    # utils.hideObj(railingRoot)

    # proxy
    proxyH = con.RAILING_PILLER_H
    proxyD = con.RAILING_DEEPTH*dk
    proxyDim = (proxyW,proxyD,proxyH)
    proxyObj = utils.addCube(
        name=f"proxy.{proxy['id']}",
        dimension=proxyDim,
        location=(0,0,proxyH/2),
        parent=railingRoot
    )
    utils.hideObjFace(proxyObj)

    # 望柱
    pillerH = con.RAILING_PILLER_H
    pillerD = con.RAILING_PILLER_D*dk
    pillerDim = (pillerD,
                 pillerD,
                 pillerH)
    pillerLoc = (-proxyW/2,
                 0,
                 pillerH/2)
    pillerObj = utils.addCube(
        name=f"望柱.{proxy['id']}",
        dimension=pillerDim,
        location=pillerLoc,
        parent=railingRoot
    )
    railingParts.append(pillerObj)

    # 桪杖扶手，固定高度
    handrailWidth = proxyW
    handrailDeepth = con.HANDRAIL_Y*dk
    handrailHeight = con.HANDRAIL_H*dk
    handrailDim = (handrailWidth,handrailDeepth,handrailHeight)
    handrailLoc = (0,0,con.HANDRAIL_Z)
    handrailObj = utils.addCube(
        name=f"桪杖扶手.{proxy['id']}",
        dimension=handrailDim,
        location=handrailLoc,
        parent=railingRoot
    )
    railingParts.append(handrailObj)

    # 折柱
    for n in range(sectionCount+1):
        # 折柱
        zzWidth = con.RAILING_ZZ_W*dk
        zzDeepth = con.RAILING_ZZ_Y*dk
        zzHeight = con.HANDRAIL_Z
        zzDim = (zzWidth,zzDeepth,zzHeight)
        zzX = (-proxyW/2 # 左侧边框
               + con.RAILING_PILLER_D*dk/2 # 半根望柱
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
        railingParts.append(zzObj)

    # 从下到上，累计高度
    sumZ = 0

    # 地栿
    difuWidth = proxyW
    difuDeepth = con.RAILING_DIFU_Y*dk
    difuHeight = con.RAILING_DIFU_H*dk
    difuDim = (difuWidth,difuDeepth,difuHeight)
    difuLoc = (0,0,difuHeight/2)
    difuObj = utils.addCube(
        name=f"地栿.{proxy['id']}",
        dimension=difuDim,
        location=difuLoc,
        parent=railingRoot
    )
    sumZ += difuHeight
    railingParts.append(difuObj)

    # 牙子板
    for n in range(sectionCount):
        # 尺寸
        yaziWidth = (sectionWidth # 分栏宽度
                     -con.RAILING_ZZ_W*dk)  # 扣除两侧各半根折柱
        yaziDeepth = con.RAILING_YAZI_Y*dk
        yaziHeight = con.RAILING_YAZI_H*dk
        yaziDim = (yaziWidth,yaziDeepth,yaziHeight)
        # 定位
        yaziX = (-proxyW/2 # 左侧边线
                 + con.RAILING_PILLER_D*dk/2 # 半根望柱
                 + (n+0.5)*con.RAILING_ZZ_W*dk # 半根折柱
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
        railingNoBevel.append(yaziObj)
    sumZ += yaziHeight

    # 下枋
    downFangWidth = proxyW
    downFangDeepth = con.RAILING_FANG_Y*dk
    downFangHeight = con.RAILING_FANG_H*dk
    downFangDim = (downFangWidth,downFangDeepth,downFangHeight)
    downFangLoc = (0,0,sumZ + downFangHeight/2)
    downFangObj = utils.addCube(
        name=f"下枋.{proxy['id']}",
        dimension=downFangDim,
        location=downFangLoc,
        parent=railingRoot
    )
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
        taohuanX = (-proxyW/2 # 左侧边线
                 + con.RAILING_PILLER_D*dk/2 # 半根望柱
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
        # mat.paint(taohuanObj,con.M_LINXIN_WAN)
        railingNoBevel.append(taohuanObj)
    sumZ += taohuanHeight
    
    # 中枋
    midFangWidth = proxyW
    midFangDeepth = con.RAILING_FANG_Y*dk
    midFangHeight = con.RAILING_FANG_H*dk
    midFangDim = (midFangWidth,midFangDeepth,midFangHeight)
    midFangLoc = (0,0,sumZ + midFangHeight/2)
    midFangObj = utils.addCube(
        name=f"中枋.{proxy['id']}",
        dimension=midFangDim,
        location=midFangLoc,
        parent=railingRoot
    )
    sumZ += downFangHeight
    railingParts.append(midFangObj)

    # 合并对象
    railingBevelObj = utils.joinObjects(
        objList=railingParts,newName='栏杆')
    # 导角
    utils.addModifierBevel(
        object=railingBevelObj,width=con.BEVEL_LOW)
    # 着色
    mat.paint(paintObj=railingBevelObj,
              paintMat=con.M_PAINT)
    
    # 与无需导角的合并
    railingNoBevel.append(railingBevelObj)
    railingObj = utils.joinObjects(
        objList=railingNoBevel,newName='栏杆')
    mat.paint(paintObj=railingObj,
              paintMat=con.M_PAINT)

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

    # 构造proxy
    proxyList = __buildProxy(balconyRoot)

    # 构造栏杆
    for proxy in proxyList:
        railingObj = __buildRailing(
            balconyRoot,proxy)
    
    return