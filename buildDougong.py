# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   斗栱的营造
import bpy
import math

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import utils
from . import buildFloor

def buildDougong(buildingObj:bpy.types.Object): 
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    if bData.aca_type != con.ACA_TYPE_BUILDING:
        utils.showMessageBox("错误，输入的不是建筑根节点")
        return
    dk = bData.DK

    # 聚焦在根目录下
    utils.setCollection(con.ROOT_COLL_NAME)

    # 新建或清空根节点
    dgrootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_DG_ROOT)
    if dgrootObj == None:
        # 创建根对象（empty）===========================================================
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        dgrootObj = bpy.context.object
        dgrootObj.name = "斗栱层"
        # 铺作起点高度在台基和柱头高度之上
        root_z = bData.platform_height + bData.piller_height
        dgrootObj.location = (0,0,root_z)
        dgrootObj.ACA_data['aca_obj'] = True
        dgrootObj.ACA_data['aca_type'] = con.ACA_TYPE_DG_ROOT
        dgrootObj.parent = buildingObj
    else:
        # 清空根节点
        utils.deleteHierarchy(dgrootObj)

    # todo：建造平板枋

    # 3、布置斗栱/铺作======================================================
    net_x,net_y = buildFloor.getFloorDate(buildingObj)
    # 转角斗栱/角科
    if bData.dg_corner_source != None:
        dgCornerObj:bpy.types.Object = bData.dg_corner_source
        # 四个角柱坐标
        dgCornerArray = [
            [net_x[-1], net_y[0]],
            [net_x[-1], net_y[-1]],
            [net_x[0], net_y[-1]],
            [net_x[0], net_y[0]]
        ]
        for n in range(len(dgCornerArray)) :
            loc = (dgCornerArray[n][0],dgCornerArray[n][1],0)
            dgCornerCopy:bpy.types.Object = utils.copyObject(
                sourceObj = dgCornerObj,
                name = "转角斗栱",
                location=loc,
                parentObj = dgrootObj
                )
            dgCornerCopy.rotation_euler.z = math.radians(n * 90)
        
    # 柱头斗栱/柱头科
    if bData.dg_piller_source != None:
        dgPillerObj:bpy.types.Object = bData.dg_piller_source
        # 下侧
        for n in range(len(net_x)-2) : 
            dgPillerCopy:bpy.types.Object = utils.copyObject(
                sourceObj = dgPillerObj,
                name = "柱头斗栱",
                location=(net_x[n+1],net_y[0],0),
                parentObj = dgrootObj
                )
            dgPillerCopy.rotation_euler.z = math.radians(0)
        # 右侧
        for n in range(len(net_y)-2) : 
            dgPillerCopy:bpy.types.Object = utils.copyObject(
                sourceObj = dgPillerObj,
                name = "柱头斗栱",
                location=(net_x[-1],net_y[n+1],0),
                parentObj = dgrootObj
                )
            dgPillerCopy.rotation_euler.z = math.radians(90)
        # 上侧
        for n in range(len(net_x)-2) : 
            dgPillerCopy:bpy.types.Object = utils.copyObject(
                sourceObj = dgPillerObj,
                name = "柱头斗栱",
                location=(net_x[-n-2],net_y[-1],0),
                parentObj = dgrootObj
                )
            dgPillerCopy.rotation_euler.z = math.radians(180)
        # 左侧
        for n in range(len(net_y)-2) : 
            dgPillerCopy:bpy.types.Object = utils.copyObject(
                sourceObj = dgPillerObj,
                name = "柱头斗栱",
                location=(net_x[0],net_y[-n-2],0),
                parentObj = dgrootObj
                )
            dgPillerCopy.rotation_euler.z = math.radians(270)
    
    # 补间斗栱/平身科
    if bData.dg_fillgap_source != '' :
        dgFillObj:bpy.types.Object = bData.dg_fillgap_source
        # 前后檐
        for n in range(len(net_x)-1) : 
            # 求平身科攒数
            pStart = net_x[n]
            pEnd = net_x[n+1]
            dougong_count =  round(abs(pEnd - pStart) / (con.DOUGONG_SPAN * dk)) # 向下取整
            dougong_span = abs(pEnd - pStart) / dougong_count
            for m in range(1,dougong_count):
                # 上侧
                dgFillCopy:bpy.types.Object = utils.copyObject(
                    sourceObj = dgFillObj,
                    name = "补间斗栱",
                    location=(net_x[n] + dougong_span * m,
                                net_y[-1],0),
                    parentObj = dgrootObj
                    )
                dgFillCopy.rotation_euler.z = math.radians(180)
                # 下侧
                dgFillCopy:bpy.types.Object = utils.copyObject(
                    sourceObj = dgFillObj,
                    name = "补间斗栱",
                    location=(net_x[n] + dougong_span * m,
                                net_y[0],0),
                    parentObj = dgrootObj
                    )
                dgFillCopy.rotation_euler.z = math.radians(0)
        
        # 两山
        for n in range(len(net_y)-1) : 
            # 求平身科攒数
            pStart = net_y[n]
            pEnd = net_y[n+1]
            dougong_count =  math.floor(abs(pEnd - pStart) / (con.DOUGONG_SPAN * dk)) # 向下取整
            dougong_span = abs(pEnd - pStart) / dougong_count
            for m in range(1,dougong_count):
                # 左侧
                dgFillCopy:bpy.types.Object = utils.copyObject(
                    sourceObj = dgFillObj,
                    name = "补间斗栱",
                    location=(net_x[0],
                        net_y[n] + dougong_span * m,0),
                    parentObj = dgrootObj
                    )
                dgFillCopy.rotation_euler.z = math.radians(270)
                # 右侧
                dgFillCopy:bpy.types.Object = utils.copyObject(
                    sourceObj = dgFillObj,
                    name = "补间斗栱",
                    location=(net_x[-1],
                        net_y[n] + dougong_span * m,0),
                    parentObj = dgrootObj
                    )
                dgFillCopy.rotation_euler.z = math.radians(90)
    
    # 重新聚焦在建筑根节点
    utils.focusObj(buildingObj)
    return 
