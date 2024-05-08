# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   构建逻辑类

import bpy
from functools import partial

from .const import ACA_Consts as con
from . import data
from . import utils
from . import buildWall
from . import buildFloor
from . import buildDougong
from . import buildRoof
from . import buildRooftile

# 根据当前选中的对象，聚焦建筑根节点
class ACA_OT_focusBuilding(bpy.types.Operator):
    bl_idname="aca.focus_building"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '聚焦建筑根节点'

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            utils.focusObj(buildingObj)
        else:
            utils.showMessageBox("ERROR: 找不到根节点")

        return {'FINISHED'}

# 生成新建筑
# 所有自动生成的建筑统一放置在项目的“ACA”collection中
# 每个建筑用一个empty做为parent，进行树状结构的管理
# 各个建筑之间的设置参数数据隔离，互不影响
# 用户在场景中选择时，可自动回溯到该建筑
class ACA_OT_add_building(bpy.types.Operator):
    bl_idname="aca.add_newbuilding"
    bl_label = "添加新建筑"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        # 创建新建筑
        # buildFloor.buildFloor(None) 
        funproxy = partial(buildFloor.buildFloor,
                    buildingObj=None)
        utils.fastRun(funproxy)
        return {'FINISHED'}

# 重新生成建筑
class ACA_OT_reset_floor(bpy.types.Operator):
    bl_idname="aca.reset_floor"
    bl_label = "重设柱网"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            funproxy = partial(buildFloor.resetFloor,
                        buildingObj=buildingObj)
            utils.fastRun(funproxy)
        else:
            utils.showMessageBox("ERROR: 找不到根节点")
        return {'FINISHED'}

# 刷新柱网的显示，应对部分属性没有直接触发实时重绘
class ACA_OT_refresh_floor(bpy.types.Operator):
    bl_idname="aca.refresh_floor"
    bl_label = "刷新柱网"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        # 调用营造序列
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            # buildFloor.buildFloor(buildingObj) 
            funproxy = partial(buildFloor.buildFloor,
                        buildingObj=buildingObj)
            utils.fastRun(funproxy)
        else:
            utils.showMessageBox("ERROR: 找不到建筑")
        
        return {'FINISHED'}
    
# 减柱
class ACA_OT_del_piller(bpy.types.Operator):
    bl_idname="aca.del_piller"
    bl_label = "减柱"
    bl_description = "删除柱子，先选择1根以上的柱子"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        piller = context.object
        pillers = context.selected_objects
        buildingObj = utils.getAcaParent(piller,con.ACA_TYPE_BUILDING)
        buildFloor.delPiller(buildingObj,pillers) 
        return {'FINISHED'}
    
# 连接柱-柱，添加枋
class ACA_OT_add_fang(bpy.types.Operator):
    bl_idname="aca.add_fang"
    bl_label = "连接"
    bl_description = "在柱间添加枋，先选择2根以上的柱子"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        piller = context.object
        pillers = context.selected_objects
        buildingObj = utils.getAcaParent(piller,con.ACA_TYPE_BUILDING)
        buildFloor.addFang(buildingObj,pillers) 
        return {'FINISHED'}
    
# 断开柱-柱，删除枋
class ACA_OT_del_fang(bpy.types.Operator):
    bl_idname="aca.del_fang"
    bl_label = "删除"
    bl_description = "在柱间删除枋，先选择1根以上的枋"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        fang = context.object
        fangs = context.selected_objects
        buildingObj = utils.getAcaParent(fang,con.ACA_TYPE_BUILDING)
        buildFloor.delFang(buildingObj,fangs) 
        return {'FINISHED'}

# 批量重新生成墙体布局，及所有墙体
# 绑定在建筑面板的“墙体营造按钮上”
class ACA_OT_reset_wall_layout(bpy.types.Operator):
    bl_idname="aca.reset_wall_layout"
    bl_label = "应用所有墙体"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            # # 生成墙体框线
            funproxy = partial(
                buildWall.resetWallLayout,
                buildingObj=buildingObj)
            utils.fastRun(funproxy)
        else:
            utils.showMessageBox("ERROR: 找不到根节点")

        return {'FINISHED'}

# 单独生成一个墙体
class ACA_OT_add_wall(bpy.types.Operator):
    bl_idname="aca.add_wall"
    bl_label = "加墙"
    bl_description = "在柱间加墙，先选择2根以上的柱子"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        piller = context.object
        pillers = context.selected_objects
        buildingObj = utils.getAcaParent(
            piller,con.ACA_TYPE_BUILDING)
        buildWall.addWall(
            buildingObj,
            pillers,
            con.ACA_WALLTYPE_WALL) 

        return {'FINISHED'}
    
# 单独生成一个隔扇
class ACA_OT_add_door(bpy.types.Operator):
    bl_idname="aca.add_door"
    bl_label = "加门"
    bl_description = "在柱间加隔扇，先选择2根以上的柱子"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        piller = context.object
        pillers = context.selected_objects
        buildingObj = utils.getAcaParent(
            piller,con.ACA_TYPE_BUILDING)
        buildWall.addWall(
            buildingObj,
            pillers,
            con.ACA_WALLTYPE_DOOR) 

        return {'FINISHED'}

# 单独生成一个槛窗
class ACA_OT_add_window(bpy.types.Operator):
    bl_idname="aca.add_window"
    bl_label = "加窗"
    bl_description = "在柱间加槛窗，先选择2根以上的柱子"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        piller = context.object
        pillers = context.selected_objects
        buildingObj = utils.getAcaParent(
            piller,con.ACA_TYPE_BUILDING)
        buildWall.addWall(
            buildingObj,
            pillers,
            con.ACA_WALLTYPE_WINDOW) 

        return {'FINISHED'}
    
# 删除一个墙体
class ACA_OT_del_wall(bpy.types.Operator):
    bl_idname="aca.del_wall"
    bl_label = "删除"
    bl_description = "删除隔断"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        buildWall.delWall(context.object)
        return {'FINISHED'}

# 单独生成一个墙体
class ACA_OT_build_door(bpy.types.Operator):
    bl_idname="aca.build_door"
    bl_label = "仅应用该墙体"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        wallproxy = context.object
        wData:data.ACA_data_obj = wallproxy.ACA_data
        if wData.aca_type != con.ACA_TYPE_WALL:
            utils.showMessageBox("ERROR: 找不到建筑")
        else:
            # 生成墙体框线
            funproxy = partial(
                buildWall.buildSingleWall,
                wallproxy=wallproxy)
            utils.fastRun(funproxy)

        return {'FINISHED'}

# 生成斗栱
class ACA_OT_build_dougong(bpy.types.Operator):
    bl_idname="aca.build_dougong"
    bl_label = "斗栱营造"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            # 生成斗栱
            funproxy = partial(
                buildDougong.buildDougong,
                buildingObj=buildingObj)
            utils.fastRun(funproxy)
        else:
            utils.showMessageBox("ERROR: 找不到建筑")

        return {'FINISHED'}
    
# 生成屋顶，包括梁架、椽架、望板、角梁、屋瓦、屋脊等
class ACA_OT_build_roof(bpy.types.Operator):
    bl_idname="aca.build_roof"
    bl_label = "屋顶营造"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            # 生成屋顶
            utils.outputMsg("Building Roof...")
            funproxy = partial(
                buildRoof.buildRoof,
                buildingObj=buildingObj)
            utils.fastRun(funproxy)
        else:
            utils.showMessageBox("ERROR: 找不到建筑")

        return {'FINISHED'}

# 测试按钮
class ACA_OT_test(bpy.types.Operator):
    bl_idname="aca.test"
    bl_label = "测试"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        # buildingObj,bData,objData = utils.getRoot(context.object)
        # if buildingObj != None:
        #     funproxy = partial(buildRooftile.buildTile,buildingObj=buildingObj)
        #     utils.fastRun(funproxy)
        # else:
        #     utils.showMessageBox("ERROR: 找不到建筑")
        from mathutils import Vector,Euler
        location = Vector((0,0,0))
        dimention = Vector((0.1,2,0.1))
        buildRoof.__drawBeam(location,dimention,context.object)

        return {'FINISHED'}
    
