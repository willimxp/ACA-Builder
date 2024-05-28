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
            self.report({'ERROR'},"找不到根节点！")

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
        funproxy = partial(buildFloor.buildFloor,
                    buildingObj=None)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
            self.report({'INFO'},"新建筑营造完成！")
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
            result = utils.fastRun(funproxy)
            if 'FINISHED' in result:
                self.report({'INFO'},"建筑已重新营造！")
        else:
            self.report({'ERROR'},"找不到根节点！")
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
        self.report({'INFO'},"已删除柱子。")
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
        # buildFloor.addFang(buildingObj,pillers) 
        funproxy = partial(
                buildFloor.addFang,
                buildingObj=buildingObj,pillers=pillers)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
                self.report({'INFO'},"已添加枋。")
        
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
        self.report({'INFO'},"已删除枋。")
        return {'FINISHED'}

# 批量重新生成墙体布局，及所有墙体
# 绑定在建筑面板的“墙体营造按钮上”
class ACA_OT_reset_wall_layout(bpy.types.Operator):
    bl_idname="aca.reset_wall_layout"
    bl_label = "更新所有墙体"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            # 生成墙体框线
            funproxy = partial(
                buildWall.buildWallLayout,
                buildingObj=buildingObj)
            result = utils.fastRun(funproxy)
            if 'FINISHED' in result:
                self.report({'INFO'},"墙体已更新！")
        else:
            self.report({'ERROR'},"找不到根节点！")

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
        funproxy = partial(
                buildWall.addWall,
                buildingObj=buildingObj,
                pillers=pillers,
                wallType=con.ACA_WALLTYPE_WALL)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
                self.report({'INFO'},"添加墙体。")

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
        funproxy = partial(
                buildWall.addWall,
                buildingObj=buildingObj,
                pillers=pillers,
                wallType=con.ACA_WALLTYPE_DOOR)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
                self.report({'INFO'},"添加隔扇。")

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
        funproxy = partial(
                buildWall.addWall,
                buildingObj=buildingObj,
                pillers=pillers,
                wallType=con.ACA_WALLTYPE_WINDOW)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
                self.report({'INFO'},"添加槛窗。")

        return {'FINISHED'}
    
# 删除一个墙体
class ACA_OT_del_wall(bpy.types.Operator):
    bl_idname="aca.del_wall"
    bl_label = "删除"
    bl_description = "删除隔断"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        funproxy = partial(
            buildWall.delWall,object=context.object)
        utils.fastRun(funproxy)
        self.report({'INFO'},"删除隔断。")
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
            result = utils.fastRun(funproxy)
            if 'FINISHED' in result:
                self.report({'INFO'},"斗栱已重新营造！")
        else:
            self.report({'ERROR'},"找不到根节点！")

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
            result = utils.fastRun(funproxy)
            if 'FINISHED' in result:
                self.report({'INFO'},"屋顶已重新营造！")
        else:
            self.report({'ERROR'},"找不到根节点！")

        return {'FINISHED'}
    
# 计算斗口推荐值
class ACA_OT_default_dk(bpy.types.Operator):
    bl_idname="aca.default_dk"
    bl_label = "计算斗口推荐值"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            # 计算斗口推荐值，取明间的0.8，再除以柱高57斗口
            dk = (bData.x_1 
                * con.DEFAULT_PILLER_HEIGHT 
                / con.PILLER_H_EAVE)
            # 取整
            bData['DK'] = int(dk*100)/100
            funproxy = partial(
                buildFloor.buildFloor,
                buildingObj=buildingObj)
            utils.fastRun(funproxy)
        else:
            self.report({'ERROR'},"找不到根节点！")

        return {'FINISHED'}

# 保存模版
class ACA_OT_save_template(bpy.types.Operator):
    bl_idname="aca.save_template"
    bl_label = "保存模版修改"

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            from . import acaTemplate
            result = acaTemplate.saveTemplate(buildingObj)
            if 'FINISHED' in result:
                self.report({'INFO'},"模版修改已保存。")
        else:
            self.report({'ERROR'},"找不到根节点！")

        return {'FINISHED'}

# 测试按钮
class ACA_OT_test(bpy.types.Operator):
    bl_idname="aca.test"
    bl_label = "测试"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            from . import buildPlatform
            funproxy = partial(buildPlatform.buildPlatform,buildingObj=buildingObj)
            utils.fastRun(funproxy)
        else:
            utils.showMessageBox("ERROR: 找不到建筑")

        return {'FINISHED'}
    
