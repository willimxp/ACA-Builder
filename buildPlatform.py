# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   台基的营造
import bpy
import math

from . import utils
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData

# 根据固定模板，创建新的台基
def buildPlatform(buildingObj:bpy.types.Object):
    buildingData : acaData = buildingObj.ACA_data

    # 1、创建地基===========================================================
    # 如果已有，先删除
    pfObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_PLATFORM)
    if pfObj != None:
        utils.deleteHierarchy(pfObj,with_parent=True)

    # 载入模板配置
    platform_height = buildingObj.ACA_data.platform_height
    platform_extend = buildingObj.ACA_data.platform_extend
    # 构造cube三维
    height = platform_height
    width = platform_extend * 2 + buildingData.x_total
    length = platform_extend * 2 + buildingData.y_total
    bpy.ops.mesh.primitive_cube_add(
                size=1.0, 
                calc_uvs=True, 
                enter_editmode=False, 
                align='WORLD', 
                location = (0,0,height/2), 
                scale=(width,length,height))
    pfObj = bpy.context.object
    pfObj.parent = buildingObj
    pfObj.name = con.PLATFORM_NAME
    # 设置插件属性
    pfObj.ACA_data['aca_obj'] = True
    pfObj.ACA_data['aca_type'] = con.ACA_TYPE_PLATFORM

    # 默认锁定对象的位置、旋转、缩放（用户可自行解锁）
    pfObj.lock_location = (True,True,True)
    pfObj.lock_rotation = (True,True,True)
    pfObj.lock_scale = (True,True,True)

     # 更新建筑框大小
    buildingObj.empty_display_size = math.sqrt(
            pfObj.dimensions.x * pfObj.dimensions.x
            + pfObj.dimensions.y * pfObj.dimensions.y
        ) / 2
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)
    utils.outputMsg("Platform added")

# 根据插件面板的台基高度、下出等参数变化，更新台基外观
# 绑定于data.py中update_platform回调
def resizePlatform(buildingObj:bpy.types.Object):
    # 载入根节点中的设计参数
    buildingData : acaData = buildingObj.ACA_data
    
    # 找到台基对象
    pfObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_PLATFORM)
    # 重绘
    pf_extend = buildingData.platform_extend
    # 缩放台基尺寸
    pfObj.dimensions= (
        pf_extend * 2 + buildingData.x_total,
        pf_extend * 2 + buildingData.y_total,
        buildingData.platform_height
    )
    # 应用缩放(有时ops.object会乱跑，这里确保针对台基对象)
    utils.applyScale(pfObj)
    # 平移，保持台基下沿在地平线高度
    pfObj.location.z = buildingData.platform_height /2

    # 对齐柱网
    floorObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_FLOOR)
    floorObj.location.z =  buildingData.platform_height

    # 更新建筑框大小
    buildingObj.empty_display_size = math.sqrt(
            pfObj.dimensions.x * pfObj.dimensions.x
            + pfObj.dimensions.y * pfObj.dimensions.y
        ) / 2
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)
    utils.outputMsg("Platform updated")