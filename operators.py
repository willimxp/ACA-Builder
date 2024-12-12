# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   构建逻辑类

import bpy
from functools import partial
import time

from .const import ACA_Consts as con
from . import utils
from . import buildWall
from . import buildFloor
from . import buildDougong
from . import buildRoof

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
    bl_description = '根据选择的模版，自动生成建筑的各个构件'

    def execute(self, context):  
        timeStart = time.time()

        # 创建新建筑
        from . import build
        funproxy = partial(build.build)
        result = utils.fastRun(funproxy)

        if 'FINISHED' in result:
            templateName = bpy.context.scene.ACA_data.template
            runTime = time.time() - timeStart
            message = "参数化营造完成！(%s , %.1f秒)" \
                        % (templateName,runTime)
            utils.popMessageBox(message)
        return {'FINISHED'}

# 更新建筑
class ACA_OT_update_building(bpy.types.Operator):
    bl_idname="aca.update_building"
    bl_label = "添加新建筑"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '根据参数的修改，重新生成建筑'

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        buildingName = buildingObj.name
        # 更新新建筑
        timeStart = time.time()
        funproxy = partial(buildFloor.buildFloor,
                    buildingObj=buildingObj)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
            runTime = time.time() - timeStart
            message = "更新建筑完成！(%s , %.1f秒)" \
                        % (buildingName,runTime)
            utils.popMessageBox(message)
        return {'FINISHED'}
    
# 删除建筑
class ACA_OT_del_building(bpy.types.Operator):
    bl_idname="aca.del_building"
    bl_label = "删除建筑"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '删除当前建筑'

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        buildingName = buildingObj.name
        if buildingObj != None:
            from . import build
            build.delBuilding(buildingObj)
            message = "%s-建筑已删除！" \
                        % (buildingName)
            self.report({'INFO'},message)

        return {'FINISHED'}

# 重新生成柱网
class ACA_OT_reset_floor(bpy.types.Operator):
    bl_idname="aca.reset_floor"
    bl_label = "重设柱网"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '重新生成被减柱的柱子，但也会丢失所有的额枋、隔扇、槛墙等'

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            funproxy = partial(buildFloor.resetFloor,
                        buildingObj=buildingObj)
            result = utils.fastRun(funproxy)
            if 'FINISHED' in result:
                self.report({'INFO'},"柱网已重新营造！")
        else:
            self.report({'ERROR'},"找不到根节点！")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            operator = self,
            title="重设柱网",
            )

    def draw(self, context):
        row = self.layout
        row.label(
            text=("请注意，柱网数据将重新生成。"),
            icon='ERROR'
            )
        row = self.layout
        row.label(
            text=("所有额枋、槛墙、槛窗、隔扇都会被删除！"),
            icon='NONE'
            )
    
# 减柱
class ACA_OT_del_piller(bpy.types.Operator):
    bl_idname="aca.del_piller"
    bl_label = "减柱"
    bl_description = "删除柱子（先选择1根以上的柱子）"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        piller = context.object
        pillers = context.selected_objects
        buildingObj = utils.getAcaParent(piller,con.ACA_TYPE_BUILDING)
        buildFloor.delPiller(buildingObj,pillers) 
        self.report({'INFO'},"已删除柱子。")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            operator = self,
            title="删除柱子"
            )

    def draw(self, context):
        row = self.layout
        row.label(
            text=("确定删除【" 
                  + bpy.context.object.name
                  + "】吗？"),
            icon='QUESTION'
            )

# 添加踏跺
class ACA_OT_add_step(bpy.types.Operator):
    bl_idname="aca.add_step"
    bl_label = "添加踏跺"
    bl_description = "在柱间添加踏跺（先选择2根以上的柱子）"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        piller = context.object
        pillers = context.selected_objects
        buildingObj = utils.getAcaParent(piller,con.ACA_TYPE_BUILDING)
        from . import buildPlatform
        funproxy = partial(
                buildPlatform.addStep,
                buildingObj=buildingObj,pillers=pillers)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
                self.report({'INFO'},"已添加踏跺。")
        
        return {'FINISHED'}

# 删除踏跺
class ACA_OT_del_step(bpy.types.Operator):
    bl_idname="aca.del_step"
    bl_label = "删除踏跺"
    bl_description = "在柱间删除踏跺（先选择1个以上的踏跺）"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        step = context.object
        steps = context.selected_objects
        buildingObj = utils.getAcaParent(
            step,con.ACA_TYPE_BUILDING)
        from . import buildPlatform
        funproxy = partial(
                buildPlatform.delStep,
                buildingObj=buildingObj,steps=steps)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
                self.report({'INFO'},"已删除踏跺。")
        
        return {'FINISHED'}

# 连接柱-柱，添加枋
class ACA_OT_add_fang(bpy.types.Operator):
    bl_idname="aca.add_fang"
    bl_label = "添加额枋"
    bl_description = "在柱间添加枋（先选择2根以上的柱子）"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        piller = context.object
        pillers = context.selected_objects
        buildingObj = utils.getAcaParent(piller,con.ACA_TYPE_BUILDING)
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
    bl_description = "在柱间删除枋（先选择1根以上的枋）"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        fang = context.object
        fangs = context.selected_objects
        buildingObj = utils.getAcaParent(
            fang,con.ACA_TYPE_BUILDING)
        buildFloor.delFang(buildingObj,fangs) 
        self.report({'INFO'},"已删除枋。")
        return {'FINISHED'}

# 批量重新生成装修布局，及所有墙体
# 绑定在建筑面板的“墙体营造按钮上”
class ACA_OT_reset_wall_layout(bpy.types.Operator):
    bl_idname="aca.reset_wall_layout"
    bl_label = "更新所有墙体"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "批量生成各个墙体"

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
    bl_description = "在柱间加墙（先选择2根以上的柱子）"
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
    bl_description = "在柱间加隔扇（先选择2根以上的柱子）"
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
    bl_description = "在柱间加槛窗（先选择2根以上的柱子）"
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
    bl_description = "删除柱之间的额枋、槛墙、槛窗、隔扇等"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        if objData.aca_type in (
                con.ACA_TYPE_WALL_CHILD,
                con.ACA_TYPE_WALL, 
                ):
            funproxy = partial(
                buildWall.delWall,
                buildingObj=buildingObj,
                walls = context.selected_objects)
            utils.fastRun(funproxy)
            self.report({'INFO'},"已删除隔断。")
        elif objData.aca_type in (
                con.ACA_TYPE_FANG,
                ):
            funproxy = partial(
                buildFloor.delFang,
                buildingObj=buildingObj,
                fangs = context.selected_objects)
            utils.fastRun(funproxy)
            self.report({'INFO'},"已删除额枋。")
        else:
            self.report({'INFO'},"没有可删除的对象")
        return {'FINISHED'}
    
    # def invoke(self, context, event):
    #     return context.window_manager.invoke_props_dialog(
    #         operator = self,
    #         title="删除对象"
    #         )

    # def draw(self, context):
    #     row = self.layout
    #     row.label(
    #         text=("确定删除【" 
    #               + bpy.context.object.name
    #               + "】吗？"),
    #         icon='QUESTION'
    #         )


# 生成斗栱
class ACA_OT_build_dougong(bpy.types.Operator):
    bl_idname="aca.build_dougong"
    bl_label = "斗栱营造"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "批量生成所有的斗栱"

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
    bl_description = "重新生成屋顶的梁架、椽架、瓦作"

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
    bl_description = "根据柱高、明间宽度，计算最合适的斗口值"

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
    bl_description = '将当前选中的建筑参数保存为模版，以便重复生成'

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
    
# 删除模版
class ACA_OT_del_template(bpy.types.Operator):
    bl_idname="aca.del_template"
    bl_label = "删除模版"
    bl_description = '从配置文件中删除当前模版'

    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):  
        from . import acaTemplate
        result = acaTemplate.delTemplate()
        if 'FINISHED' in result:
            self.report({'INFO'},"模版已删除。")

        return {'FINISHED'}
    
    def invoke(self, context, event):
        # invoke_confirm调用自动自带的确认框，提示文字取bl_label
        # return context.window_manager.invoke_confirm(self, event)
        # invoke_props_dialog调用自定义的对话框，在draw函数中定义
        # https://docs.blender.org/api/current/bpy.types.WindowManager.html#bpy.types.WindowManager.invoke_props_dialog
        return context.window_manager.invoke_props_dialog(
            operator = self,
            title="删除模版"      # 如果为空，自动取bl_label
            )

    def draw(self, context):
        row = self.layout
        row.label(
            text=("确定删除【" 
                  + bpy.context.scene.ACA_data.template 
                  + "】吗？"),
            icon='QUESTION'
            )

# 生成院墙
class ACA_OT_build_yardwall(bpy.types.Operator):
    bl_idname="aca.build_yardwall"
    bl_label = "生成院墙"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        timeStart = time.time()

        # 添加院墙
        buildingObj,bData,objData = utils.getRoot(context.object)
        from . import buildYardWall
        funproxy = partial(
            buildYardWall.buildYardWall,
            buildingObj=buildingObj)
        result = utils.fastRun(funproxy)

        if 'FINISHED' in result:
            timeEnd = time.time()
            self.report(
                {'INFO'},"新院墙添加完成！(%.1f秒)" 
                % (timeEnd-timeStart))
        

        return {'FINISHED'}

class ACA_OT_default_ludingRafterSpan(bpy.types.Operator):
    bl_idname="aca.default_luding_rafterspan"
    bl_label = "默认盝顶步架"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '步架推荐值，自动获取尽间开间尺寸'

    def execute(self, context):  
        # 盝顶步架默认取面阔的尽间宽度
        buildingObj,bData,objData = utils.getRoot(context.object)
        if bData.x_rooms >= 7:
            bData.luding_rafterspan = bData.x_4
        elif bData.x_rooms >= 5:
            bData.luding_rafterspan = bData.x_3
        elif bData.x_rooms >=3:
            bData.luding_rafterspan = bData.x_2
        else:
            bData.luding_rafterspan = 0.01

        return {'FINISHED'}

# 模态提示框
class ACA_OT_Show_Message_Box(bpy.types.Operator):
    bl_idname = "aca.show_message_box"
    bl_label = ""
 
    from bpy.props import StringProperty, BoolProperty
    message: StringProperty()               # type: ignore 
    icon: StringProperty(default="INFO")    # type: ignore 
    center: BoolProperty(default=False)     # type: ignore 
    
    def execute(self, context):
        return {'FINISHED'}
 
    def invoke(self, context, event):
        self.restored = False
        if self.center:
            self.orig_x = event.mouse_x
            self.orig_y = event.mouse_y
            
            w = int(context.window.width/2)
            h = int(context.window.height/2)
            h = h + (20*len(self.message.split("|")))
            context.window.cursor_warp(w, h)
        
        return context.window_manager.invoke_props_dialog(self, width = 400)
 
    def draw(self, context):
        panelTitle = "ACA Blender Addon"
        self.layout.label(text=panelTitle)
        message_list = self.message.split("|")
        for li in message_list:
            row=self.layout.row()
            row.scale_y = 2
            row.label(text=li, icon=self.icon)
        if not self.restored and self.center:
            context.window.cursor_warp(self.orig_x, self.orig_y)
            self.restored = True

# 测试
class ACA_OT_test(bpy.types.Operator):
    bl_idname="aca.test"
    bl_label = "测试"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        timeStart = time.time()
        buildingObj,bData,objData = utils.getRoot(context.object)
        from . import buildPlatform
        funproxy = partial(
            buildPlatform.buildPlatform,
            buildingObj=buildingObj)
        utils.fastRun(funproxy)

        timeEnd = time.time()
        self.report(
                {'INFO'},"完成：(%.2f秒)" 
                % (timeEnd-timeStart))

        return {'FINISHED'}
    

    
