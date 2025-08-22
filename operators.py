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
from . import build
from . import buildWall
from . import buildFloor
from . import buildDougong

# 根据当前选中的对象，聚焦建筑根节点
class ACA_OT_focusBuilding(bpy.types.Operator):
    bl_idname="aca.focus_building"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '聚焦建筑根节点'

    def execute(self, context):  
        buildingObj,bData,objData = utils.getRoot(context.object)

        if buildingObj != None:
            # 如果context选择的构件，则聚焦到建筑节点
            if context.object != buildingObj:
                # 聚焦构件对应的建筑
                utils.focusObj(buildingObj)
            # 如果context已经是建筑节点，查看是否有combo父级
            else:
                comboObj = utils.getComboRoot(buildingObj)
                if comboObj is not None:
                    # 聚焦Combo
                    utils.focusObj(comboObj)                
        else:
            self.report({'ERROR'},"找不到根节点")

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
        funproxy = partial(build.build)
        result = utils.fastRun(funproxy)

        message=''
        type = {'INFO'}
        if 'FINISHED' in result:
            from . import data
            scnData : data.ACA_data_scene = bpy.context.scene.ACA_data
            templateList = scnData.templateItem
            templateIndex = scnData.templateIndex
            templateName = templateList[templateIndex].name

            runTime = time.time() - timeStart
            message = "从模板样式新建完成！|建筑样式：【%s】 |运行时间：【%.1f秒】" \
                        % (templateName,runTime)
        
        if message != '':
            utils.popMessageBox(message)
            self.report(type,message)
        return {'FINISHED'}

# 更新建筑
class ACA_OT_update_building(bpy.types.Operator):
    bl_idname="aca.update_building"
    bl_label = "更新建筑"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '根据参数的修改，重新生成建筑'

    # 外部传入的对象
    buildingName: bpy.props.StringProperty(
        name="建筑名称",
        default=''
    ) # type: ignore

    def execute(self, context): 
        # 优先处理外部传入的对象，对在data中传入的id_data
        buildingObj = bpy.data.objects.get(self.buildingName)
        if buildingObj == None: 
            # 如果没有传入对象，是用户直接点击"更新建筑"按钮，此时使用上下文对象
            buildingObj,bData,objData = utils.getRoot(context.object)
            # 强制重新载入素材库
            reloadAssets = True
        else:
            # 有传入的对象，是用户修改属性触发的更新，此时不需要重新载入素材库
            reloadAssets = False
        # 判断是否是ACA对象
        if buildingObj == None:
            utils.popMessageBox("此对象并非插件生成，或已经合并，无法操作。")
            return {'FINISHED'}

        # 更新新建筑
        timeStart = time.time()
        funproxy = partial(build.updateBuilding,
                    buildingObj=buildingObj,
                    reloadAssets=reloadAssets)
        result = utils.fastRun(funproxy)

        # 结果提示
        if 'FINISHED' in result:
            runTime = time.time() - timeStart
            msg = "更新建筑完成！|建筑样式：【%s】 |运行时间：【%.1f秒】" \
                        % (buildingObj.name,runTime)
            utils.outputMsg(msg)
            self.report({'INFO'},msg)
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

    # 外部传入的对象
    buildingName: bpy.props.StringProperty(
        name="建筑名称",
        default=''
    ) # type: ignore

    def execute(self, context):  
        # 优先处理外部传入的对象，对在data中传入的id_data
        buildingObj = bpy.data.objects.get(self.buildingName)
        if buildingObj == None: 
            # 如果没有传入对象，则使用上下文对象
            buildingObj,bData,objData = utils.getRoot(context.object)

        funproxy = partial(build.resetFloor,
                    buildingObj=buildingObj)
        result = utils.fastRun(funproxy)

        if 'FINISHED' in result:
            self.report({'INFO'},"已重新营造柱网！")

        return {'FINISHED'}
    
    def invoke(self, context, event):
        # 开始记录操作，以便后续可以撤销
        #bpy.ops.ed.undo_push(message="Before Confirm Dialog")

        buildingObj,bData,objData = utils.getRoot(context.object)
        # 解决bug：面阔间数在鼠标拖拽时可能为偶数，出现异常
        if bData.x_rooms % 2 == 0:
            # 不处理偶数面阔间数
            utils.popMessageBox("面阔间数不能为偶数")
            # 用户取消操作时执行撤销
            bpy.ops.ed.undo()
            return {'CANCELLED'}

        return context.window_manager.invoke_props_dialog(
            operator = self,
            title="ACA筑韵古建 addon for Blender",
            width = 400,
            )

    def draw(self, context):
        row = self.layout.row()
        row.label(
            text=("请注意，柱网数据将重新生成。"),
            icon='ERROR'
            )
        row = self.layout.row()
        row.label(
            text=("所有额枋、槛墙、槛窗、隔扇都会被删除！"),
            icon='BLANK1'
            )
    
    def cancel(self, context):
        # 用户取消操作时执行撤销
        bpy.ops.ed.undo()
        
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

        funproxy = partial(buildFloor.delPiller,
                    buildingObj=buildingObj,
                    pillers=pillers)
        result = utils.fastRun(funproxy)

        self.report({'INFO'},"已删除柱子")
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
        # 校验用户至少选择2根柱子
        pillerNum = 0
        for piller in pillers:
            if 'aca_type' in piller.ACA_data:   # 可能选择了没有属性的对象
                if piller.ACA_data['aca_type'] \
                    == con.ACA_TYPE_PILLER:
                    pillerNum += 1
        if pillerNum < 2:
            utils.popMessageBox("请至少选择2根柱子")
            return {'CANCELLED'}
        
        buildingObj = utils.getAcaParent(piller,con.ACA_TYPE_BUILDING)
        from . import buildPlatform
        funproxy = partial(
                buildPlatform.addStep,
                buildingObj=buildingObj,pillers=pillers)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
                self.report({'INFO'},"已添加踏跺")
        
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

        selected = False
        for step in steps:
            # 校验用户选择的对象，可能误选了其他东西，直接忽略
            # 如果用户选择的是step子对象，则强制转换到父对象
            if 'aca_type' in step.ACA_data:
                if step.ACA_data['aca_type'] \
                        == con.ACA_TYPE_STEP:
                    selected = True
        
        if not selected:
            utils.popMessageBox("请选择需要删除的踏跺")
            return {'CANCELLED'}
                
        buildingObj = utils.getAcaParent(
            step,con.ACA_TYPE_BUILDING)
        from . import buildPlatform
        funproxy = partial(
                buildPlatform.delStep,
                buildingObj=buildingObj,steps=steps)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
                self.report({'INFO'},"已删除踏跺")
        
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
                self.report({'INFO'},"已添加枋")
        
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
        self.report({'INFO'},"已删除枋")
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
                self.report({'INFO'},"已添加墙体")

        return {'FINISHED'}
    
# 单独生成一个隔扇
class ACA_OT_add_door(bpy.types.Operator):
    bl_idname="aca.add_door"
    bl_label = "隔扇"
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
                wallType=con.ACA_WALLTYPE_GESHAN)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
                self.report({'INFO'},"已添加隔扇")

        return {'FINISHED'}

# 单独生成一个槛窗
class ACA_OT_add_window(bpy.types.Operator):
    bl_idname="aca.add_window"
    bl_label = "槛窗"
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
                self.report({'INFO'},"已添加槛窗")

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
                con.ACA_TYPE_WALL,              # 槛墙
                con.ACA_WALLTYPE_WINDOW,        # 槛窗
                con.ACA_WALLTYPE_GESHAN,        # 隔扇
                con.ACA_WALLTYPE_BARWINDOW,     # 直棂窗
                con.ACA_WALLTYPE_MAINDOOR,      # 板门
                con.ACA_WALLTYPE_FLIPWINDOW,    # 支摘窗
                ):
            funproxy = partial(
                buildWall.delWall,
                buildingObj=buildingObj,
                walls = context.selected_objects)
            utils.fastRun(funproxy)
            self.report({'INFO'},"已删除隔断")
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

# 单独生成一个板门
class ACA_OT_add_maindoor(bpy.types.Operator):
    bl_idname="aca.add_maindoor"
    bl_label = "板门"
    bl_description = "在柱间加板门（先选择2根以上的柱子）"
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
                wallType=con.ACA_WALLTYPE_MAINDOOR)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
                self.report({'INFO'},"已添加板门")

        return {'FINISHED'}
    
# 单独生成一个直棂窗
class ACA_OT_add_barwindow(bpy.types.Operator):
    bl_idname="aca.add_barwindow"
    bl_label = "直棂窗"
    bl_description = "在柱间加直棂窗（先选择2根以上的柱子）"
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
                wallType=con.ACA_WALLTYPE_BARWINDOW)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
                self.report({'INFO'},"已添加直棂窗")

        return {'FINISHED'}
    
# 单独生成一个支摘窗
class ACA_OT_add_flipwindow(bpy.types.Operator):
    bl_idname="aca.add_flipwindow"
    bl_label = "支摘窗"
    bl_description = "在柱间加支摘窗（先选择2根以上的柱子）"
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
                wallType=con.ACA_WALLTYPE_FLIPWINDOW)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
                self.report({'INFO'},"已添加支摘窗")

        return {'FINISHED'}
    
# 单独生成一副栏杆
class ACA_OT_add_railing(bpy.types.Operator):
    bl_idname="aca.add_railing"
    bl_label = "栏杆"
    bl_description = "在柱间加栏杆（先选择2根以上的柱子）"
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
                wallType=con.ACA_WALLTYPE_RAILILNG)
        result = utils.fastRun(funproxy)
        if 'FINISHED' in result:
                self.report({'INFO'},"已添加栏杆")

        return {'FINISHED'}


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
        buildingName = buildingObj.name
        timeStart = time.time()

        # 生成屋顶
        funproxy = partial(
            build.resetRoof,
            buildingObj=buildingObj)
        result = utils.fastRun(funproxy)
        
        build.isFinished = True

        message=''
        type = {'INFO'}
        if 'FINISHED' in result:
            runTime = time.time() - timeStart
            message = "重新生成屋顶完成！|建筑样式：【%s】 |运行时间：【%.1f秒】" \
                    % (buildingName,runTime)
        
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
        if buildingObj == None:
            utils.popMessageBox("此对象并非插件生成，或已经合并，无法操作。")
            return {'FINISHED'}
        
        # 查找是否存在comboRoot
        comboObj = utils.getComboRoot(buildingObj)
        if comboObj is not None:
            # 用combo节点替换buildingObj
            buildingObj = comboObj
        
        from . import template
        result = template.saveTemplateWithCombo(buildingObj)
        if 'FINISHED' in result:
            msg = f"【{buildingObj.name}】模板样式保存成功"
            utils.outputMsg(msg)
            self.report({'INFO'},msg)

        return {'FINISHED'}
    
    def invoke(self, context, event):
        # 查询所有的模板列表
        from . import template
        templateList = template.getTemplateList(onlyname=True)
        # 确认当前建筑名称是否与模板冲突
        buildingObj,bData,objData = utils.getRoot(context.object)

        # 查找是否存在comboRoot
        comboObj = utils.getComboRoot(buildingObj)
        if comboObj is not None:
            # 用combo节点替换buildingObj
            buildingObj = comboObj

        buildingName = buildingObj.name
        for templateItem in templateList:
            if templateItem == buildingName:
                # 提示用户是否覆盖模板
                return context.window_manager.invoke_props_dialog(
                        operator = self,
                        title="ACA筑韵古建 addon for Blender",
                        width = 400,
                        )
        # 检查通过，执行保存
        return self.execute(context)

    def draw(self, context):
        buildingObj,bData,objData = utils.getRoot(context.object)
        # 查找是否存在comboRoot
        comboObj = utils.getComboRoot(buildingObj)
        if comboObj is not None:
            # 用combo节点替换buildingObj
            buildingObj = comboObj

        buildingName = buildingObj.name
        row = self.layout.row()
        row.label(
            text=(f"是否覆盖【{buildingName}】？"),
            icon='INFO'
            )
        row = self.layout.row()
        row.label(
            text=("请注意，覆盖模板样式的操作无法取消！"),
            icon='BLANK1'
            )
        row = self.layout.row()
        row.label(
            text=("你可以先修改名称，再重新保存。"),
            icon='BLANK1'
            )
    
# 删除模板
class ACA_OT_del_template(bpy.types.Operator):
    bl_idname="aca.del_template"
    bl_label = "删除样式"
    bl_description = '从模板配置文件中删除当前样式'

    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):  
        from . import data
        scnData : data.ACA_data_scene = bpy.context.scene.ACA_data
        templateList = scnData.templateItem
        templateIndex = scnData.templateIndex
        templateName = templateList[templateIndex].name

        from . import template
        result = template.delTemplate(templateName)
        if 'FINISHED' in result:
            # 刷新场景中的模板列表数据
            scnData : data.ACA_data_scene = context.scene.ACA_data
            # 清空场景中的模板列表数据
            scnData.templateItem.clear()
            # 查询所有的模板列表
            from . import template
            templateList = template.getTemplateList(onlyname=True)
            # 重新填充场景的模板列表
            for templateItemName in templateList:
                item = scnData.templateItem.add()
                item.name = templateItemName

            self.report({'INFO'},f"【{templateName}】样式已删除。")

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
        from . import data
        scnData : data.ACA_data_scene = bpy.context.scene.ACA_data
        templateList = scnData.templateItem
        templateIndex = scnData.templateIndex
        templateName = templateList[templateIndex].name

        row = self.layout
        row.label(
            text=(f"确定删除【{templateName}】吗？"),
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

            windowWidth = context.window.width
            windowHeight = context.window.height
            # 判断macOs，使用Retina高分辨屏幕时，分辨率x2
            import sys
            platform = sys.platform
            if platform.startswith('darwin'):
                windowWidth = windowWidth*2
                windowHeight = windowHeight*2
            
            w = int(windowWidth/2)
            h = int(windowHeight/2)
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
    bl_label = "合并整体"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '将所有的建筑构件合并为一个整体，便于做导出等操作'

    # 是否分层合并
    useLayer: bpy.props.BoolProperty(
            name="是否分层合并",
            default=False,
    )# type: ignore

    def execute(self, context):  
        timeStart = time.time()
        
        # 验证是否选中了建筑
        buildingObj,bData,objData = utils.getRoot(context.object)
        if not buildingObj:
            self.report({'INFO'},'合并失败，请选择一个建筑。')
            return {'CANCELLED'}
        
        funproxy = partial(
            build.joinBuilding,
            buildingObj=buildingObj,
            useLayer=self.useLayer,)
        result = utils.fastRun(funproxy)

        timeEnd = time.time()
        self.report(
            {'INFO'},"合并完成(%.1f秒)" 
            % (timeEnd-timeStart))

        return {'FINISHED'}

# 导出FBX模型
# https://docs.blender.org/api/current/bpy.ops.export_scene.html#module-bpy.ops.export_scene
class ACA_OT_EXPORT_FBX(bpy.types.Operator):
    bl_idname="aca.export_fbx"
    bl_label = "导出FBX"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '导出为FBX模型，可用于D5渲染器导入'
    
    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Filepath used for exporting the file",
        maxlen=1024,
        subtype='FILE_PATH',)# type: ignore
    check_existing: bpy.props.BoolProperty(
        name="Check Existing",
        description="Check and warn on overwriting existing files",
        default=True,
        options={'HIDDEN'},
    )# type: ignore
    filename: bpy.props.StringProperty()# type: ignore

    def execute(self, context):          
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
        # 获取当前的Blender文件名
        blend_filepath = context.blend_data.filepath
        if not blend_filepath:
            blend_filepath = "untitled"
        else:
            import os
            blend_filepath = os.path.splitext(blend_filepath)[0]

        # 获取当前激活的对象名
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj == None:
            buildingObj = context.object  

        # 合并生成默认的导出名称
        self.filepath = (blend_filepath 
                         + '_' + buildingObj.name
                         + '.fbx')

        # 弹出文件选择框
        context.window_manager.fileselect_add(self)        
        return {'RUNNING_MODAL'}

# 导出GLB模型
# https://docs.blender.org/api/current/bpy.ops.export_scene.html#module-bpy.ops.export_scene
class ACA_OT_EXPORT_GLB(bpy.types.Operator):
    bl_idname="aca.export_glb"
    bl_label = "导出GLB"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '导出为GLB模型，推荐UE5导入。'

    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH")# type: ignore
    check_existing: bpy.props.BoolProperty(
        name="Check Existing",
        description="Check and warn on overwriting existing files",
        default=True,
        options={'HIDDEN'},
    )# type: ignore
    filename: bpy.props.StringProperty()# type: ignore

    def execute(self, context):        
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
        # 获取当前的Blender文件名
        blend_filepath = context.blend_data.filepath
        if not blend_filepath:
            blend_filepath = "untitled"
        else:
            import os
            blend_filepath = os.path.splitext(blend_filepath)[0]

        # 获取当前激活的对象名
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj == None:
            buildingObj = context.object  

        # 合并生成默认的导出名称
        self.filepath = (blend_filepath 
                         + '_' + buildingObj.name
                         + '.glb')
        
        # 弹出文件选择框
        context.window_manager.fileselect_add(self)   
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

# 插件设置
class ACA_OT_Preferences(bpy.types.AddonPreferences):
    # This must match the add-on name, use `__package__`
    # when defining this for add-on extensions or a sub-module of a python package.
    bl_idname = __name__.split('.')[0]

    filepath: bpy.props.StringProperty(
        name="素材库路径",
        subtype='FILE_PATH',
    )# type: ignore

    use_bevel : bpy.props.BoolProperty(
            default = True,
            name = "是否使用倒角",
            description = "取消后，不再使用倒角，直接生成直角构件",
        ) # type: ignore

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        filepath = self.filepath
        if filepath == '':
            row.label(text="请设置acaAssets.blend文件的路径:")
        else:
            row.label(text=self.filepath)
        row = layout.row()
        row.operator(
            "aca.link_assets",icon='COLLECTION_COLOR_02')
        
        row = layout.row()
        row.prop(self,'use_bevel')
    
# 关联素材库
class ACA_OT_LINK_ASSETS(bpy.types.Operator):
    bl_idname="aca.link_assets"
    bl_label = "关联素材库"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '关联acaAssets.blend素材库'

    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH")# type: ignore
    check_existing: bpy.props.BoolProperty(
        name="Check Existing",
        description="Check and warn on overwriting existing files",
        default=True,
        options={'HIDDEN'},
    )# type: ignore
    filename: bpy.props.StringProperty()# type: ignore

    def execute(self, context):               
        # 检查路径是否包含文件名
        import os
        filepath = self.filepath
        # 检查路径是否为空
        if not filepath:
            utils.popMessageBox("请选择一个文件")
            return {'CANCELLED'}
        # 检查是否为文件
        if not os.path.isfile(filepath):
            utils.popMessageBox("选择的不是一个有效的文件")
            return {'CANCELLED'}
        # 检查文件扩展名是否为 .blend
        if not filepath.lower().endswith('.blend'):
            utils.popMessageBox(f"选择的文件 {filepath} 不是 .blend 文件")
            return {'CANCELLED'}
        # 路径验证通过
        preferences = bpy.context.preferences
        addon_main_name = __name__.split('.')[0]
        addon_prefs = preferences.addons[addon_main_name].preferences
        addon_prefs.filepath = filepath
        utils.popMessageBox("素材库路径设置成功")
        utils.outputMsg(f"素材库路径已设置为 {filepath}")

        return {'FINISHED'}
    
    def invoke(self, context, event): 
        addonName = "ACA Builder"
        templateFolder = 'template'
        blenderFileName = 'acaAssets.blend'
        import pathlib
        USER = pathlib.Path(
            bpy.utils.resource_path('USER'))
        srcPath = USER / "scripts/addons" / addonName / templateFolder /blenderFileName
        self.filepath = str(srcPath)
         
        # 弹出文件选择框
        context.window_manager.fileselect_add(self)   
        return {'RUNNING_MODAL'}


# 模板列表的自定义行样式
class ACA_UL_Template_Items(bpy.types.UIList):
    def draw_item(self, context, layout, data, 
                  item, icon, active_data, active_propname, index):
        row = layout.row()
        row.label(text=item.name,icon='KEYTYPE_GENERATED_VEC')

# 选择生成模板
class ACA_OT_SELECT_TEMPLATE_DIALOG(bpy.types.Operator):
    bl_idname = "aca.select_template_dialog"
    bl_label = "请选择一个古建筑模板样式："
 
    from bpy.props import StringProperty, BoolProperty
    message: StringProperty()               # type: ignore 
    icon: StringProperty(default="INFO")    # type: ignore 
    center: BoolProperty(default=True)     # type: ignore 
    
    def execute(self, context):
        bpy.ops.aca.add_newbuilding()
        return {'FINISHED'}
 
    def invoke(self, context, event):
        # 鼠标定位
        self.restored = False
        if self.center:
            self.orig_x = event.mouse_x
            self.orig_y = event.mouse_y

            windowWidth = context.window.width
            windowHeight = context.window.height
            # 判断macOs，使用Retina高分辨屏幕时，分辨率x2
            import sys
            platform = sys.platform
            if platform.startswith('darwin'):
                windowWidth = windowWidth*2
                windowHeight = windowHeight*2
            
            w = int(windowWidth/2)
            h = int(windowHeight/2)
            h = h + (20*len(self.message.split("|")))
            context.window.cursor_warp(w, h)
        
        scnData : data.ACA_data_scene = context.scene.ACA_data
        # 清空场景中的模板列表数据
        scnData.templateItem.clear()
        # 查询所有的模板列表
        from . import template
        templateList = template.getTemplateList(onlyname=True)
        # 重新填充场景的模板列表
        for templateName in templateList:
            item = scnData.templateItem.add()
            item.name = templateName

        # 填充缩略图
        template.loadThumb()
        
        # 弹出对话框
        return context.window_manager.invoke_props_dialog(
            self, 
            width = 450,
            confirm_text='生成')
 
    def draw(self, context):
        scnData : data.ACA_data_scene = context.scene.ACA_data
        layout = self.layout 
        
        # 模板列表    
        row = layout.row()
        col_left = row.column(align=True)
        col_left.scale_x = 0.5  # 左侧占70%宽度
        col_left.template_list(
            listtype_name="ACA_UL_Template_Items", 
            list_id="my_list", 
            dataptr=scnData, 
            propname="templateItem", 
            active_dataptr=scnData, 
            active_propname="templateIndex", 
            rows=10)
        
        # 右侧边栏
        col_right = row.column(align=True)
        col_right.scale_x = 0.5 # 右侧占30%宽度
        # 缩略图展示，使用了blender内置的template_icon_view控件
        scene = context.scene
        col_right.template_icon_view(scene,
                               "image_browser_enum",
                               show_labels=True,
                               scale=10)
        # 删除按钮
        col_right.operator("aca.del_template", icon='TRASH', text="删除模板")

        # 鼠标定位
        if not self.restored and self.center:
            context.window.cursor_warp(self.orig_x, self.orig_y)
            self.restored = True

# 添加剖视图
class ACA_OT_SECTION(bpy.types.Operator):
    bl_idname="aca.section"
    bl_label = "添加剖视图"
    bl_options = {'REGISTER', 'UNDO'}

    # 参数：剖视方案
    sectionPlan: bpy.props.StringProperty(
        name="剖视方案",
        default="X+"
    ) # type: ignore

    def execute(self, context): 
        buildingObj,bData,objData = utils.getRoot(context.object)
        # 生成剖视系统，传入剖视方案
        funproxy = partial(
            build.addSection,
            buildingObj=buildingObj,
            sectionPlan=self.sectionPlan)
        result = utils.fastRun(funproxy)
        
        return {'FINISHED'}
    
# 删除月台
class ACA_OT_TERRACE_DEL(bpy.types.Operator):
    bl_idname="aca.terrace_del"
    bl_label = "删除月台"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '删除月台（请先选择月台）'

    def execute(self, context): 
        timeStart = time.time()

        terraceObj,bData,objData = utils.getRoot(context.object)
        
        from . import buildCombo
        funproxy = partial(
            buildCombo.delTerrace,
            terraceObj=terraceObj,
        )
        result = utils.fastRun(funproxy)

        if 'FINISHED' in result:
            timeEnd = time.time()
            self.report(
                {'INFO'},"月台删除(%.1f秒)" 
                % (timeEnd-timeStart))
        
        return {'FINISHED'}
    
# 添加月台
class ACA_OT_TERRACE_ADD(bpy.types.Operator):
    bl_idname="aca.terrace_add"
    bl_label = "添加月台"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '添加月台（请先选择台基）'

    def execute(self, context): 
        timeStart = time.time()

        buildingObj,bData,objData = utils.getRoot(context.object)
        
        from . import buildCombo
        funproxy = partial(
            buildCombo.addTerrace,
            buildingObj=buildingObj,
        )
        result = utils.fastRun(funproxy)

        if 'FINISHED' in result:
            timeEnd = time.time()
            self.report(
                {'INFO'},"月台添加(%.1f秒)" 
                % (timeEnd-timeStart))
        
        return {'FINISHED'}
    
# 添加重檐
class ACA_OT_DOUBLE_EAVE_ADD(bpy.types.Operator):
    bl_idname="aca.double_eave_add"
    bl_label = "添加重檐"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '添加重檐'

    def execute(self, context): 
        timeStart = time.time()

        buildingObj,bData,objData = utils.getRoot(context.object)
        
        from . import buildCombo
        funproxy = partial(
            buildCombo.addDoubleEave,
            buildingObj=buildingObj,
        )
        result = utils.fastRun(funproxy)

        if 'FINISHED' in result:
            runTime = time.time() - timeStart
            msg = '添加重檐完成 | 运行时间【%.1f秒】' % runTime
            self.report({'INFO'},msg)
            utils.popMessageBox(msg)
        
        return {'FINISHED'}
    
# 取消重檐
class ACA_OT_DOUBLE_EAVE_DEL(bpy.types.Operator):
    bl_idname="aca.double_eave_del"
    bl_label = "取消重檐"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '取消重檐'

    def execute(self, context): 
        timeStart = time.time()

        buildingObj,bData,objData = utils.getRoot(context.object)
        
        from . import buildCombo
        funproxy = partial(
            buildCombo.delDoubleEave,
            buildingObj=buildingObj,
        )
        result = utils.fastRun(funproxy)

        if 'FINISHED' in result:
            runTime = time.time() - timeStart
            msg = '取消重檐完成 | 运行时间【%.1f秒】' % runTime
            self.report({'INFO'},msg)
            utils.popMessageBox(msg)
        
        return {'FINISHED'}
    
# 添加重楼
class ACA_OT_MULTI_FLOOR_ADD(bpy.types.Operator):
    bl_idname="aca.multi_floor_add"
    bl_label = "添加重楼"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '添加重楼'

    def execute(self, context): 
        timeStart = time.time()

        buildingObj,bData,objData = utils.getRoot(context.object)
        
        from . import buildCombo
        funproxy = partial(
            buildCombo.addMultiFloor,
            buildingObj=buildingObj,
        )
        result = utils.fastRun(funproxy)

        if 'FINISHED' in result:
            runTime = time.time() - timeStart
            msg = '添加重楼完成 | 运行时间【%.1f秒】' % runTime
            self.report({'INFO'},msg)
            utils.popMessageBox(msg)
        
        return {'FINISHED'}