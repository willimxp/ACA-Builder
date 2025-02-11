# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   构建逻辑类

import bpy
from functools import partial
import time 
from . import data

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
    bl_description = '根据选择的样式，自动生成建筑的各个构件'

    def execute(self, context):  
        timeStart = time.time()

        # 创建新建筑
        from . import build
        funproxy = partial(build.build)
        result = utils.fastRun(funproxy)

        message=''
        type = {'INFO'}
        if 'FINISHED' in result:
            templateName = bpy.context.scene.ACA_data.template
            runTime = time.time() - timeStart
            message = "参数化营造完成！|建筑样式：【%s】 |运行时间：【%.1f秒】" \
                        % (templateName,runTime)
        elif 'CANCELLED' in result:
            message = ("插件在运行中发生了一个异常错误：|- “"
                + str(result['CANCELLED'])
                + "”|请联系开发者，并提供日志文件")
            type = {'ERROR'}
        
        if message != '':
            utils.popMessageBox(message)
            self.report(type,message)
        return {'FINISHED'}

# 更新建筑
class ACA_OT_update_building(bpy.types.Operator):
    bl_idname="aca.update_building"
    bl_label = "添加新建筑"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '根据参数的修改，重新生成建筑'

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj == None:
            utils.popMessageBox("此对象并非插件生成，或已经合并，无法操作。")
            return {'FINISHED'}
        buildingName = buildingObj.name
        # 更新新建筑
        timeStart = time.time()
        from . import build
        funproxy = partial(build.updateBuilding,
                    buildingObj=buildingObj)
        result = utils.fastRun(funproxy)

        message=''
        type = {'INFO'}
        if 'FINISHED' in result:
            runTime = time.time() - timeStart
            message = "更新建筑完成！(%s , %.1f秒)" \
                        % (buildingName,runTime)
        elif 'CANCELLED' in result:
            message = ("插件在运行中发生了一个异常错误：|- “"
                + str(result['CANCELLED'])
                + "”|请联系开发者，并提供日志文件")

        if message != '':
            utils.popMessageBox(message)
            self.report(type,message)

        return {'FINISHED'}
    
# 删除建筑
class ACA_OT_del_building(bpy.types.Operator):
    bl_idname="aca.del_building"
    bl_label = "删除建筑"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '删除当前建筑'

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj == None:
            utils.popMessageBox("此对象并非插件生成，或已经合并，无法操作。")
            return {'FINISHED'}
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
        if buildingObj == None:
            utils.popMessageBox("此对象并非插件生成，或已经合并，无法操作。")
            return {'FINISHED'}
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
            title="ACA筑韵古建 addon for Blender",
            width = 400,
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
            icon='BLANK1'
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
            self, 
            title="ACA筑韵古建 addon for Blender",
            width = 400,)

    def draw(self, context):
        row = self.layout
        pillers = context.selected_objects
        pillersName = ''
        for piller in pillers:
            pillersName += piller.name + '，'
        row.label(
            text=("确定删除【" 
                  + pillersName[:-1]
                  + "】吗？"),
            icon='QUESTION'
            )
        row.label(
            text=("减柱做为配置参数可以保存在模板样式中"),
            icon='BLANK1'
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
                con.ACA_TYPE_WALL, 
                con.ACA_TYPE_WALL_CHILD,
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
    #         title="ACA筑韵古建 addon for Blender",
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
        if buildingObj == None:
            utils.popMessageBox("此对象并非插件生成，或已经合并，无法操作。")
            return {'FINISHED'}
        else:
            from . import build
            build.isFinished = False
            build.progress = 0

            # 生成屋顶
            funproxy = partial(
                buildRoof.buildRoof,
                buildingObj=buildingObj)
            result = utils.fastRun(funproxy)
            
            build.isFinished = True

            message=''
            type = {'INFO'}
            if 'FINISHED' in result:
                message = "屋顶已重新营造！"
            elif 'CANCELLED' in result:
                message = ("插件在运行中发生了一个异常错误：|- “"
                + str(result['CANCELLED'])
                + "”|请联系开发者，并提供日志文件")
                type = {'ERROR'}
            
            if message != '':
                utils.popMessageBox(message)
                self.report(type,message)

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
            # funproxy = partial(
            #     buildFloor.buildFloor,
            #     buildingObj=buildingObj)
            # utils.fastRun(funproxy)
        else:
            utils.popMessageBox("此对象并非插件生成，或已经合并，无法操作。")
            return {'FINISHED'}

        return {'FINISHED'}

# 保存样式
class ACA_OT_save_template(bpy.types.Operator):
    bl_idname="aca.save_template"
    bl_label = "保存样式修改"
    bl_description = '将当前选中的建筑参数保存为样式，以便重复生成'

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            from . import template
            result = template.saveTemplate(buildingObj)
            if 'FINISHED' in result:
                self.report({'INFO'},"样式修改已保存。")
        else:
            utils.popMessageBox("此对象并非插件生成，或已经合并，无法操作。")
            return {'FINISHED'}

        return {'FINISHED'}
    
# 删除模板
class ACA_OT_del_template(bpy.types.Operator):
    bl_idname="aca.del_template"
    bl_label = "删除样式"
    bl_description = '从模板配置文件中删除当前样式'

    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):  
        from . import template
        result = template.delTemplate()
        if 'FINISHED' in result:
            self.report({'INFO'},"样式已删除。")

        return {'FINISHED'}
    
    def invoke(self, context, event):
        # invoke_confirm调用自动自带的确认框，提示文字取bl_label
        # return context.window_manager.invoke_confirm(self, event)
        # invoke_props_dialog调用自定义的对话框，在draw函数中定义
        # https://docs.blender.org/api/current/bpy.types.WindowManager.html#bpy.types.WindowManager.invoke_props_dialog
        return context.window_manager.invoke_props_dialog(
            operator = self,
            title="ACA筑韵古建 addon for Blender",      # 如果为空，自动取bl_label
            width = 400,
            )

    def draw(self, context):
        row = self.layout
        row.label(
            text=("确定删除【" 
                  + bpy.context.scene.ACA_data.template 
                  + "】吗？"),
            icon='QUESTION'
            )
        row.label(
            text=("注意：建筑样式保存在模板文件中，删除后无法复原。")
            )
        row.label(
            text=("建议先备份插件目录中的template.xml。")
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
        
        return context.window_manager.invoke_props_dialog(
            self, 
            title="ACA筑韵古建 addon for Blender",
            width = 400,)
 
    def draw(self, context):
        # 提示内容，多行之间用'|'分割
        message_list = self.message.split("|")
        for n,li in enumerate(message_list):
            # 对异常信息等很长的行，再次进行二次拆分
            chunkSize = 64
            liSplit = utils.splitText(li,chunkSize)
            for m,lis in enumerate(liSplit):
                if m+n==0: 
                    icon=self.icon
                else:
                    icon = 'BLANK1'
                row=self.layout.row()
                row.label(text=lis,icon=icon)
        if not self.restored and self.center:
            context.window.cursor_warp(self.orig_x, self.orig_y)
            self.restored = True

# 通过执行建造过程，分析性能数据
class ACA_OT_PROFILE(bpy.types.Operator):
    bl_idname="aca.profile"
    bl_label = "性能分析"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        import cProfile
        import pstats  
        import io 

        # Create a profiler object  
        pr = cProfile.Profile()  
        pr.enable()  # Start profiling  

        # Call the function you want to profile  
        from . import build
        funproxy = partial(build.build)
        result = utils.fastRun(funproxy)

        pr.disable()  # Stop profiling  

        # Create a stream to hold the stats  
        s = io.StringIO()  
        sortby = pstats.SortKey.CUMULATIVE  
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)  
        ps.print_stats()  

        # Print the profiling results to the Blender console  
        print(s.getvalue())  

        return {'FINISHED'}

class ACA_OT_JOIN(bpy.types.Operator):
    bl_idname="aca.join"
    bl_label = "合并模型"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '将所有的建筑构件合并为一个整体，便于做裁剪等操作'

    def execute(self, context):  
        # 预处理
        buildingObj,bData,objData = utils.getRoot(context.object)
        # 验证是否选中了建筑
        if buildingObj == None:
            # 没有可合并的对象
            self.report({'INFO'},'合并失败，请选择一个建筑。')
            return {'CANCELLED'}
        
        # 选择所有下级层次对象
        partObjList = []
        def addChild(buildingObj):
            for childObj in buildingObj.children:
                useObj = True
                # 仅处理可见的实体对象
                if childObj.type not in ('MESH','CURVE'):
                    useObj = False
                if childObj.hide_viewport or childObj.hide_render:
                    useObj = False
                # 记录对象名称
                if useObj:
                    partObjList.append(childObj)
                # 次级递归
                if childObj.children:
                    addChild(childObj)
        addChild(buildingObj)
        
        # 合并对象
        if len(partObjList) > 0 :
            joinedModel = utils.joinObjects(
                partObjList,
                buildingObj.name+'.joined')
            
        # 摆脱buildingObj父节点
        # location归零
        joinedModel.location = (
            joinedModel.parent.matrix_world 
            @ joinedModel.location)
        joinedModel.parent = None
        utils.applyTransfrom(joinedModel,use_location=True)

        # 移到导出目录
        coll:bpy.types.Collection = utils.setCollection(
            'ACA古建.合并',isRoot=True,colorTag=3)
        coll.objects.link(joinedModel)

        # 删除原目录
        from . import build
        build.delBuilding(buildingObj)

        # 聚焦
        utils.focusObj(joinedModel)

        return {'FINISHED'}

# 导出FBX模型
# https://docs.blender.org/api/current/bpy.ops.export_scene.html#module-bpy.ops.export_scene
class ACA_OT_EXPORT_FBX(bpy.types.Operator):
    bl_idname="aca.export_fbx"
    bl_label = "导出FBX"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '导出为FBX模型，可用于D5渲染器导入'
    
    filter_glob: bpy.props.StringProperty(
        default = '*.fbx',
        options = {'HIDDEN'}) # type: ignore
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH")# type: ignore

    def execute(self, context):  
        # # 预处理
        # buildingObj,bData,objData = utils.getRoot(context.object)
        
        # # 验证是否建筑已经过合并
        # is_joined = False
        # if buildingObj == None:
        #     is_joined = True
        #     buildingObj = context.object

        # # 未合并的建筑，先执行合并
        # if not is_joined:
        #     result = bpy.ops.aca.join()
        #     if 'FINISHED' not in result:
        #         return {'CANCELLED'}
        
        # 导出fbx
        filePath = self.filepath
        absPath = bpy.path.abspath(filePath)
        bpy.ops.export_scene.fbx(
            filepath = absPath, 
            check_existing=True,
            use_selection = True,
            mesh_smooth_type = 'FACE',
            path_mode = 'COPY',
            embed_textures = True,
            colors_type='NONE'
        )

        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)        
        return {'RUNNING_MODAL'}

# 导出GLB模型
# https://docs.blender.org/api/current/bpy.ops.export_scene.html#module-bpy.ops.export_scene
class ACA_OT_EXPORT_GLB(bpy.types.Operator):
    bl_idname="aca.export_glb"
    bl_label = "导出GLB"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '导出为GLB模型，推荐UE5导入。'

    filter_glob: bpy.props.StringProperty(
        default = '*.glb',
        options = {'HIDDEN'}) # type: ignore
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH")# type: ignore

    def execute(self, context):  
        # # 预处理
        # buildingObj,bData,objData = utils.getRoot(context.object)
        
        # # 验证是否建筑已经过合并
        # is_joined = False
        # if buildingObj == None:
        #     is_joined = True
        #     buildingObj = context.object

        # # 未合并的建筑，先执行合并
        # if not is_joined:
        #     result = bpy.ops.aca.join()
        #     if 'FINISHED' not in result:
        #         return {'CANCELLED'}
        
        # 导出fbx
        filePath = self.filepath
        absPath = bpy.path.abspath(filePath)
        bpy.ops.export_scene.gltf(
            filepath=absPath, 
            check_existing=True, 
            use_selection=True,         # only select
            use_visible=True,           # only visible
            use_renderable=True,        # only renderable
            export_apply=True,          # apply modifiers
            export_animations=False,    # not export ani
            export_skins=False,         # not export skin
            export_morph=False,         # not export shapekey 
            # not sure
            # export_gn_mesh=False,     # Geometry Nodes Instances (Experimental), Export Geometry nodes instance meshes
            # export_original_specular=False,  # Export original PBR Specular, Export original glTF PBR Specular, instead of Blender Principled Shader Specular
        )

        return {'FINISHED'}
    
    def invoke(self, context, event):        
        # 弹出文件选择框
        context.window_manager.fileselect_add(self)   

        # 设置默认文件名
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj == None:buildingObj = context.object
        self.filepath = buildingObj.name + '.glb'     
        return {'RUNNING_MODAL'}
    
# 测试
class ACA_OT_test(bpy.types.Operator):
    bl_idname="aca.test"
    bl_label = "测试"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):  
        # import cProfile
        # import pstats  
        # import io 

        # # Create a profiler object  
        # pr = cProfile.Profile()  
        # pr.enable()  # Start profiling  

        # # Call the function you want to profile  
        # from . import build
        # funproxy = partial(build.build)
        # result = utils.fastRun(funproxy)

        # pr.disable()  # Stop profiling  

        # # Create a stream to hold the stats  
        # s = io.StringIO()  
        # sortby = pstats.SortKey.CUMULATIVE  
        # ps = pstats.Stats(pr, stream=s).sort_stats(sortby)  
        # ps.print_stats()  

        # # Print the profiling results to the Blender console  
        # print(s.getvalue())  

        utils.addCube('testing')

        return {'FINISHED'}

    
