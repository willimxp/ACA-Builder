# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   构建逻辑类

import math
import bpy
from mathutils import Vector
from functools import partial

from .const import ACA_Consts as con
from . import acaTemplate
from . import data
from . import utils
from . import buildWall
from . import buildFloor
from . import buildDoor
from . import buildDougong
from . import buildRoof
from . import buildRooftile
    
# 添加建筑empty根节点，并绑定设计模版
# 返回建筑empty根节点对象
# 被ACA_OT_add_newbuilding类调用
def addBuildingRoot():
    # 获取panel上选择的模版
    templateName = bpy.context.scene.ACA_data.template
    
    # 创建buildObj根节点
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    buildingObj = bpy.context.object
    buildingObj.location = bpy.context.scene.cursor.location   # 原点摆放在3D Cursor位置
    buildingObj.name = templateName   # 系统遇到重名会自动添加00x的后缀       
    buildingObj.empty_display_type = 'SPHERE'

    # 在buildingObj中填充模版数据
    templateData = acaTemplate.getTemplate(templateName)
    acaTemplate.fillTemplate(buildingObj,templateData)
    
    utils.outputMsg("Building Root added")
    return buildingObj

# 生成新建筑
# 所有自动生成的建筑统一放置在项目的“ACA”collection中
# 每个建筑用一个empty做为parent，进行树状结构的管理
# 各个建筑之间的设置参数数据隔离，互不影响
#（后续可以提供批量修改的功能）
# 用户在场景中选择时，可自动回溯到该建筑
class ACA_OT_add_building(bpy.types.Operator):
    bl_idname="aca.add_newbuilding"
    bl_label = "添加新建筑"

    def execute(self, context):      
        # 1.定位到“ACA”根collection，如果没有则新建
        utils.setCollection(con.ROOT_COLL_NAME)

        # 2.添加建筑empty
        # 其中绑定了模版数据
        buildingObj = addBuildingRoot()

        # 3.调用营造序列
        buildFloor.addFloor(buildingObj) 

        # 聚焦到建筑根节点
        utils.focusObj(buildingObj)
        return {'FINISHED'}

# 批量重新生成墙体布局，及所有墙体
# 绑定在建筑面板的“墙体营造按钮上”
class ACA_OT_reset_wall_layout(bpy.types.Operator):
    bl_idname="aca.reset_wall_layout"
    bl_label = "墙体营造"

    def execute(self, context):  
        buildingObj = context.object
        bData:data.ACA_data_obj = buildingObj.ACA_data
        if bData.aca_type != con.ACA_TYPE_BUILDING:
            utils.showMessageBox("ERROR: 找不到建筑")
        else:
            # # 生成墙体框线
            funproxy = partial(buildWall.resetWallLayout,buildingObj=buildingObj)
            utils.fastRun(funproxy)

        return {'FINISHED'}

# 单独生成一个墙体
class ACA_OT_build_door(bpy.types.Operator):
    bl_idname="aca.build_door"
    bl_label = "墙体营造"

    def execute(self, context):  
        wallproxy = context.object
        wData:data.ACA_data_obj = wallproxy.ACA_data
        if wData.aca_type != con.ACA_TYPE_WALL:
            utils.showMessageBox("ERROR: 找不到建筑")
        else:
            # 生成墙体框线
            funproxy = partial(buildDoor.buildSingleWall,wallproxy=wallproxy)
            utils.fastRun(funproxy)

        return {'FINISHED'}

# 批量重新生成墙体布局，及所有墙体
# 绑定在建筑面板的“墙体营造按钮上”
class ACA_OT_build_dougong(bpy.types.Operator):
    bl_idname="aca.build_dougong"
    bl_label = "斗栱营造"

    def execute(self, context):  
        buildingObj = context.object
        bData:data.ACA_data_obj = buildingObj.ACA_data
        if bData.aca_type != con.ACA_TYPE_BUILDING:
            utils.showMessageBox("ERROR: 找不到建筑")
        else:
            # 生成斗栱
            funproxy = partial(buildDougong.buildDougong,buildingObj=buildingObj)
            utils.fastRun(funproxy)

        return {'FINISHED'}
    
# 批量重新生成墙体布局，及所有墙体
# 绑定在建筑面板的“墙体营造按钮上”
class ACA_OT_build_roof(bpy.types.Operator):
    bl_idname="aca.build_roof"
    bl_label = "屋顶营造"

    def execute(self, context):  
        buildingObj = context.object
        bData:data.ACA_data_obj = buildingObj.ACA_data
        if bData.aca_type != con.ACA_TYPE_BUILDING:
            utils.showMessageBox("ERROR: 找不到建筑")
        else:
            #buildRoof.buildRoof(buildingObj)
            funproxy = partial(buildRoof.buildRoof,buildingObj=buildingObj)
            utils.fastRun(funproxy)

        return {'FINISHED'}
    
# 批量重新生成墙体布局，及所有墙体
# 绑定在建筑面板的“墙体营造按钮上”
class ACA_OT_test(bpy.types.Operator):
    bl_idname="aca.test"
    bl_label = "测试"

    def execute(self, context):  
        buildingObj = context.object
        bData:data.ACA_data_obj = buildingObj.ACA_data
        if bData.aca_type != con.ACA_TYPE_BUILDING:
            utils.showMessageBox("ERROR: 找不到建筑")
        else:
            buildRooftile.buildTile(buildingObj)
            # funproxy = partial(buildRoof.buildRoof,buildingObj=buildingObj)
            # utils.fastRun(funproxy)

        return {'FINISHED'}