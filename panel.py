# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   定义插件面板的UI

import bpy
from . import data
from .const import ACA_Consts as con
from . import utils
from . import build

# 营造向导面板
class ACA_PT_basic(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示 
    
    # 自定义属性
    bl_category = "筑韵古建"         # 标签页名称
    bl_label = ""                   # 面板名称，在draw_header中写入版本号

    def draw_header(self,context):
        from . import bl_info
        ver = ' V%s.%s.%s' % (
            bl_info['version'][0],
            bl_info['version'][1],
            bl_info['version'][2])
        
        layout = self.layout
        row = layout.row()
        row.label(text='ACA筑韵古建'+ ver)

    def draw_header_preset(self,context):
        layout = self.layout
        helpbtn = layout.row(align=True)
        op = helpbtn.operator("wm.url_open",icon='HELP',text='')
        op.url = 'https://docs.qq.com/doc/DYXpwbUp1UWR0RXpu'
    
    def draw(self, context):
        layout = self.layout
        
        # 0、检测运行版本，必须至少在Blender 4.2.0以上
        if bpy.app.version < (4,2,0):
            row = layout.row()
            row.label(text='本插件无法运行在V%s.%s.%s' % (bpy.app.version[0],bpy.app.version[1],bpy.app.version[2]))
            row = layout.row()
            row.label(text='请安装Blender V4.2.0以上')
            row = layout.row()
            op = row.operator("wm.url_open",icon='URL',text='下载Blender')
            op.url = 'https://www.blender.org/download/'
            return
        
        # 1、生成新建筑，调用独立的下拉选择对话框
        buttonAddnew = layout.row()
        buttonAddnew.operator(
            "aca.select_template_dialog",
            icon='SEQUENCE',
            depress=True,
            text='从模板生成新建筑'
            )
        
        # 2、运行中提示
        if not build.isFinished:
            row = layout.row()
            row.label(text='生成中：需要20~90秒，请耐心等待。',icon='INFO')
            row = layout.row()
            row.progress(
                type="BAR",
                factor=build.progress,
                text=build.buildStatus,
            )
            # 运行时，不显示以下的面板内容
            # 待运行结束后，才会显示
            return
        
        # 3. Quick Start提示框
        isShowQS = False
        # 无上下文时
        if context.object == None:
            isShowQS = True
        # 有上下文
        else:
            buildingObj,bData,objData = utils.getRoot(context.object)
            # 如果是ACA建筑，
            if buildingObj == None: 
                # 已经合并的不显示
                if objData.aca_type != con.ACA_TYPE_BUILDING_JOINED:
                    isShowQS = True
        if isShowQS:
            layout.label(text='Quick Start :')
            layout.label(text='选择一个模板，生成古建筑',icon='KEYTYPE_JITTER_VEC')
            layout.label(text='修改参数，定制你的样式',icon='KEYTYPE_MOVING_HOLD_VEC')
            # 不再继续显示后续的设置面板
            return
        
        # 3、详细设置面板
        # 场景数据集
        scnData : data.ACA_data_scene = context.scene.ACA_data
        box = layout.box()
        # 合并的对象不显示这些控件，否则会报错
        if objData.aca_type != con.ACA_TYPE_BUILDING_JOINED:
            toolBox = box.column(align=True)    
            
            #----------------------------
            toolBar = toolBox.grid_flow(columns=2, align=True)
            # 建筑名称
            col = toolBar.column(align=True)
            col.prop(buildingObj,"name",text="")
            # 聚焦根节点，右侧小按钮
            col = toolBar.column(align=True)
            col.operator("aca.focus_building",icon='FILE_PARENT')
            if (buildingObj == None
                or objData.aca_type == con.ACA_TYPE_BUILDING):
                col.enabled = False
            
            #----------------------------
            toolBox = box.row(align=True) 
            toolBar = toolBox.grid_flow(columns=2, align=True)
            # 保存模板
            col = toolBar.column(align=True)
            col.operator(
                "aca.save_template",icon='FILE_TICK',
                text='保存样式')
            # 更新建筑
            col = toolBar.column(align=True)
            col.operator(
                "aca.update_building",
                depress=True,text='更新建筑',
                icon='FILE_REFRESH',
            )              
            # 删除建筑
            col = toolBar.column(align=True)
            col.operator(
                "aca.del_building",icon='TRASH',
                text='删除建筑'
            ) 
            # 是否修改参数时，自动触发更新
            col = toolBar.column(align=True)
            if scnData.is_auto_rebuild:
                text = '暂停刷新'
            else:
                text = '自动刷新'
            col.prop(
                data=bpy.context.scene.ACA_data,
                property='is_auto_rebuild',
                toggle=True,
                icon='FF',
                text=text
            )

        toolBox = box.column(align=True)
        # 合并按钮
        toolBar = toolBox.grid_flow(columns=1, align=True)
        col = toolBar.column(align=True)
        col.operator("aca.join",icon='PACKAGE')
        # 导出按钮
        toolBar = toolBox.grid_flow(columns=2, align=True)
        col = toolBar.column(align=True)
        col.operator("aca.export_fbx",icon='EXPORT')
        col = toolBar.column(align=True)
        col.operator("aca.export_glb",icon='EXPORT')   

        # 性能分析按钮
        # row = layout.row()
        # row.operator("aca.profile",icon='HOME')
        
        # 测试按钮
        # row = layout.row()
        # row.operator("aca.test",icon='HOME')
        return

# # 更多设置子面板
# class ACA_PT_extra(bpy.types.Panel):
#     # 常规属性
#     bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
#     bl_region_type = 'UI'           # UI代表sidebar形式
#     bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
#     # 自定义属性
#     bl_category = "筑韵古建"             # 标签页名称
#     bl_label = "更多设置"                       # 面板名称，已替换为draw_header实现
#     bl_parent_id = "ACA_PT_basic"       # 父面板
#     bl_options = {"DEFAULT_CLOSED"}     # 默认折叠

#     @classmethod 
#     def poll(self, context):
#         if bpy.app.version < (4,2,0):return
        
#         isAcaObj = False
#         # 从当前场景中载入数据集
#         if context.object != None:
#             # 追溯全局属性
#             buildingObj,bData,objData = utils.getRoot(context.object)
#             if buildingObj != None: 
#                 if bData.aca_type == con.ACA_TYPE_BUILDING:
#                     isAcaObj = True
#         if isAcaObj and build.isFinished:
#             return True
        
#     def draw(self, context):
#         sData = context.scene.ACA_data
#         layout = self.layout
#         box = layout.box()

#         # 是否使用倒角
#         row = box.row()
#         row.prop(sData, "use_bevel")

#         toolBox = box.column(align=True)
#         # 合并按钮
#         toolBar = toolBox.grid_flow(columns=1, align=True)
#         col = toolBar.column(align=True)
#         col.operator("aca.join",icon='PACKAGE')
#         # 导出按钮
#         toolBar = toolBox.grid_flow(columns=2, align=True)
#         col = toolBar.column(align=True)
#         col.operator("aca.export_fbx",icon='EXPORT')
#         col = toolBar.column(align=True)
#         col.operator("aca.export_glb",icon='EXPORT')   
        
        
#         return

# “屋身参数”面板
class ACA_PT_props(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "筑韵古建"         # 标签页名称
    bl_label = "屋身参数"            # 面板名称，显示为可折叠的箭头后

    @classmethod 
    def poll(self, context):
        if bpy.app.version < (4,2,0):return
        
        isAcaObj = False
        # 从当前场景中载入数据集
        if context.object != None:
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj != None: 
                if bData.aca_type == con.ACA_TYPE_BUILDING:
                    isAcaObj = True
        if isAcaObj and build.isFinished:
            return True
    
    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            layout = self.layout
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: 
                # 如果不属于建筑构件，提示，并隐藏所有子面板
                row = layout.row()
                row.label(text='没有设置项',icon='INFO')
                row = layout.row()
                row.label(text='请先选择一个或多个建筑对象')
                return             

            # 斗口值
            if bData!= None:
                box = layout.box()
                row = box.row(align=True)
                col = row.column(align=True)
                col.prop(bData,'DK')
                # 计算默认斗口值
                col = row.column(align=True)
                col.operator("aca.default_dk",icon='SHADERFX',text='')
        
        return

# “台基属性”子面板
class ACA_PT_platform(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "筑韵古建"             # 标签页名称
    bl_label = ""                       # 面板名称，已替换为draw_header实现
    bl_parent_id = "ACA_PT_props"       # 父面板
    bl_options = {"DEFAULT_CLOSED"}     # 默认折叠

    # 仅在选中建筑根节点时显示该面板
    @classmethod 
    def poll(self, context):
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            return True
        return

    def draw_header(self,context):
        layout = self.layout
        row = layout.row()
        buildingObj,bData,objData = utils.getRoot(context.object)
        row.prop(bData, "is_showPlatform",text='台基属性')
        if bData.aca_type != con.ACA_TYPE_BUILDING:
            layout.enabled = False

    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            layout = self.layout
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: return

            # 台基属性
            box = layout.box()
            if bData.aca_type != con.ACA_TYPE_BUILDING:
                    box.enabled = False

            col = box.column(align=True)
            grid = col.grid_flow(columns=1, align=True)
            grid.prop(bData, "platform_height")
            grid.prop(bData, "platform_extend")
            
            col = box.column(align=True)
            grid = col.grid_flow(columns=2, align=True)
            col = grid.column(align=True)
            col.operator(operator='aca.add_step',
                         text='添加踏跺',
                         depress=True,
                         icon='PACKAGE')
            col = grid.column(align=True)
            col.operator(operator='aca.del_step',
                         text='删除踏跺',
                         depress=True,
                         icon='TRASH')

            # 切换显示/隐藏台基
            if not bData.is_showPlatform:
                layout.enabled = False
                
# “柱网属性”子面板
class ACA_PT_pillers(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "筑韵古建"             # 标签页名称
    bl_label = ""                       # 面板名称，已替换为draw_header实现
    bl_parent_id = "ACA_PT_props"       # 父面板
    bl_options = {"DEFAULT_CLOSED"}     # 默认折叠

    # 仅在选中建筑根节点时显示该面板
    @classmethod 
    def poll(self, context):
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            return True
        return
    
    def draw_header(self,context):
        layout = self.layout
        row = layout.row()
        buildingObj,bData,objData = utils.getRoot(context.object)
        row.prop(bData, "is_showPillers",text='柱网属性')
        if bData.aca_type != con.ACA_TYPE_BUILDING:
            layout.enabled = False

    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            layout = self.layout
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: return

            # 全局属性
            #if objData.aca_type == con.ACA_TYPE_BUILDING:
            # 柱网属性
            box = layout.box()
            if bData.aca_type != con.ACA_TYPE_BUILDING:
                    box.enabled = False

            row = box.column(align=True)
            row.prop(bData, "x_rooms")      # 面阔间数
            row.prop(bData, "x_1")          # 明间宽度
            if bData.x_rooms >= 3:
                row.prop(bData, "x_2")      # 次间宽度
            if bData.x_rooms >= 5:
                row.prop(bData, "x_3")      # 梢间宽度
            if bData.x_rooms >= 7:
                row.prop(bData, "x_4")      # 尽间宽度
                
            col = box.column(align=True)
            col.prop(bData, "y_rooms")      # 进深间数
            col.prop(bData, "y_1")          # 明间深度
            if bData.y_rooms >= 3:
                col.prop(bData, "y_2")      # 次间深度
            if bData.y_rooms >= 5:
                col.prop(bData, "y_3")      # 梢间深度

            # 柱子属性
            col = box.column(align=True)
            grid = col.grid_flow(columns=1, align=True)
            # 柱高
            grid.prop(bData, "piller_height") 
            # 柱径   
            grid.prop(bData, "piller_diameter")  
            grid = col.grid_flow(columns=2, align=True)
            # 按钮:减柱
            col = grid.column(align=True)
            col.operator(
                "aca.del_piller",icon='X',
                depress=True,text='减柱')  
            if objData.aca_type != con.ACA_TYPE_PILLER:
                col.enabled=False
            # 按钮:重设柱网
            col = grid.column(align=True)
            col.operator(
                "aca.reset_floor",icon='FILE_REFRESH',
                depress=True,text='重设') 
                
# “装修属性”子面板
class ACA_PT_wall(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "筑韵古建"             # 标签页名称
    bl_label = ""                       # 面板名称，已替换为draw_header实现
    bl_parent_id = "ACA_PT_props"       # 父面板
    bl_options = {"DEFAULT_CLOSED"}     # 默认折叠

    # 仅在选中建筑根节点时显示该面板
    @classmethod 
    def poll(self, context):
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            return True
        return

    # 在标题栏中添加显示/隐藏开关
    def draw_header(self,context):
        layout = self.layout
        row = layout.row()
        buildingObj,bData,objData = utils.getRoot(context.object)
        row.prop(bData, "is_showWalls",text='装修属性')

        if bData.aca_type != con.ACA_TYPE_BUILDING:
            layout.enabled = False

    # def draw_header_preset(self,context):
    #     layout = self.layout
    #     row = layout.row()
    #     buildingObj,bData,objData = utils.getRoot(context.object)
    #     if buildingObj == None: return
    #     if bData.aca_type != con.ACA_TYPE_BUILDING:
    #         layout.enabled = False
    #     # 显示为局部设置
    #     if objData.aca_type in (
    #             con.ACA_TYPE_WALL,          # 槛墙
    #             con.ACA_WALLTYPE_WINDOW,    # 槛窗
    #             con.ACA_WALLTYPE_GESHAN,    # 隔扇
    #             con.ACA_WALLTYPE_BARWINDOW, # 直棂窗
    #     ):
    #         col = row.column()
    #         col.label(text='['+context.object.name+']',icon='KEYTYPE_JITTER_VEC')
    #     # 显示为全局设置
    #     else:
    #         col = row.column()
    #         col.label(text='[全局]',icon='KEYTYPE_KEYFRAME_VEC')

    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            layout = self.layout
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: return

            # 控制是否允许修改
            if not bData.is_showWalls:
                layout.enabled = False

            box = layout.box() 
            if bData.aca_type != con.ACA_TYPE_BUILDING:
                    box.enabled = False

            # 彩画样式
            toolBox = box.column(align=True)
            toolBar = toolBox.grid_flow(align=True,columns=1)
            inputPaintStyle = toolBar.column(align=True)
            inputPaintStyle.prop(
                bData, "paint_style",)

            # 工具栏：加枋、加墙、加门、加窗、删除
            toolBox = box.column(align=True)
            toolBar = toolBox.grid_flow(columns=2, align=True)
            # 按钮：加枋
            buttonFang = toolBar.column(align=True)
            buttonFang.operator(
                "aca.add_fang",icon='LINKED',text='额枋')
            # 按钮：加板门
            buttonMaindoor = toolBar.column(align=True)
            buttonMaindoor.operator(
                "aca.add_maindoor",icon='SPLIT_VERTICAL',text='板门')
            # 按钮：加门
            buttonDoor = toolBar.column(align=True)
            buttonDoor.operator(
                "aca.add_door",icon='MOD_TRIANGULATE',text='隔扇门')
            # 按钮：加墙
            buttonWall = toolBar.column(align=True)
            buttonWall.operator(
                "aca.add_wall",icon='MOD_BUILD',text='墙体')
            # 按钮：加直棂窗
            buttonBarwindow = toolBar.column(align=True)
            buttonBarwindow.operator(
                "aca.add_barwindow",icon='FILE_VOLUME',text='直棂窗')
            # 按钮：加槛窗
            buttonWin = toolBar.column(align=True)
            buttonWin.operator(
                "aca.add_window",icon='MOD_LATTICE',text='隔扇窗')
            # 按钮：加支摘窗
            buttonFlipWin = toolBar.column(align=True)
            buttonFlipWin.operator(
                "aca.add_flipwindow",icon='MOD_LATTICE',text='支摘窗')
            
            # 通栏宽度按钮
            toolBar = toolBox.grid_flow(columns=1, align=True)
            # 按钮：删除
            buttonDel = toolBar.column(align=True)
            buttonDel.operator(
                "aca.del_wall",icon='TRASH',text='删除',depress=True)
            
            # 工具可用性判断
            # 至少应选择两根柱子
            if objData.aca_type != con.ACA_TYPE_PILLER \
                or len(context.selected_objects)<2:
                    buttonFang.enabled=False
                    buttonDoor.enabled=False
                    buttonWall.enabled=False
                    buttonWin.enabled=False
                    buttonMaindoor.enabled=False
                    buttonBarwindow.enabled=False
                    buttonFlipWin.enabled=False
            # 删除按钮，是否选中个隔断对象
            if objData.aca_type not in (
                con.ACA_TYPE_FANG,          # 枋对象
                con.ACA_TYPE_WALL,          # 槛墙
                con.ACA_WALLTYPE_WINDOW,    # 槛窗
                con.ACA_WALLTYPE_GESHAN,    # 隔扇
                con.ACA_WALLTYPE_BARWINDOW, # 直棂窗
                con.ACA_WALLTYPE_MAINDOOR,  # 板门
                con.ACA_WALLTYPE_FLIPWINDOW,# 支摘窗
                ):
                buttonDel.enabled = False

            # 区分全局还是个体
            isSetall = False
            if objData.aca_type in (
                con.ACA_TYPE_WALL,          # 槛墙
                con.ACA_WALLTYPE_WINDOW,    # 槛窗
                con.ACA_WALLTYPE_GESHAN,    # 隔扇
                con.ACA_WALLTYPE_BARWINDOW, # 直棂窗
                con.ACA_WALLTYPE_MAINDOOR,  # 板门
                con.ACA_WALLTYPE_FLIPWINDOW,# 支摘窗
            ):     
                # 如果用户选中了wallProxy
                # 仅设置个体参数，取objData
                dataSource = objData
            elif objData.aca_type == con.ACA_TYPE_WALL_CHILD:
                dataSource = context.object.parent.ACA_data
            else:
                dataSource = bData  
                isSetall = True
            
            # 全局参数框
            toolBox = box.column(align=True)
            toolBar = toolBox.grid_flow(align=True,columns=1)
            
            # # 复选框：是否使用横披窗（区分了全局和个体）
            # checkboxTopwin = toolBar.column(align=True)
            # if dataSource.use_topwin:
            #     checkbox_icon = 'CHECKBOX_HLT'
            # else:
            #     checkbox_icon = 'CHECKBOX_DEHLT'
            # checkboxTopwin.prop(
            #     bData, "use_topwin",
            #     toggle=1,text='横披窗',
            #     icon=checkbox_icon)
            # 门口宽度比例
            inputDoorWidth = toolBar.column(align=True)
            inputDoorWidth.prop(
                bData, "doorFrame_width_per")
            # 门口高度
            inputDoorHeight = toolBar.column(align=True)
            inputDoorHeight.prop(
                bData, "doorFrame_height")
            # 走马板高度（不区分）
            inputTopHeight = toolBar.column(align=True)
            inputTopHeight.prop(
                bData, "wall_span")
            # 复选框：是否使用小额枋（不区分）
            checkboxFang = toolBar.column(align=True)
            if dataSource.use_smallfang:
                checkbox_icon = 'CHECKBOX_HLT'
            else:
                checkbox_icon = 'CHECKBOX_DEHLT'
            checkboxFang.prop(
                bData, "use_smallfang",
                toggle=1,text="双重额枋",
                icon=checkbox_icon) 
            
            # 个性参数
            toolBox = box.column(align=True)
            toolBar = toolBox.grid_flow(align=True,columns=1)

            # 显示全区还是个体
            selectRange = toolBar.column(align=True)
            if isSetall: 
                selectRange.label(
                    text='[全局]',
                    icon='KEYTYPE_KEYFRAME_VEC')
            else:
                selectRange.label(
                    text='['+context.object.name+']',
                    icon='KEYTYPE_JITTER_VEC')
                
            # 门钉数量
            inputDingNum = toolBar.column(align=True)
            inputDingNum.prop(
                bData, "door_ding_num")
            
            # 隔扇数量（区分了全局和个体）
            inputDoorNum = toolBar.column(align=True)
            inputDoorNum.prop(
                dataSource, "door_num",text='隔扇数量')
            # 抹头数量（区分了全局和个体）
            inputGapNum = toolBar.column(align=True)
            inputGapNum.prop(
                dataSource, "gap_num",text='抹头数量')            
        
        return

# “屋顶参数”面板
class ACA_PT_roof_props(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "筑韵古建"         # 标签页名称
    bl_label = "屋顶参数"            # 面板名称，显示为可折叠的箭头后

    @classmethod 
    def poll(self, context):
        # 限制最低版本
        if bpy.app.version < (4,2,0):return

        isAcaObj = False
        # 从当前场景中载入数据集
        if context.object != None:
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj != None: 
                if bData.aca_type == con.ACA_TYPE_BUILDING:
                    isAcaObj = True
        if isAcaObj and build.isFinished:
            return True
            
    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            layout = self.layout
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: 
                # 如果不属于建筑构件，提示，并隐藏所有子面板
                row = layout.row()
                row.label(text='没有设置项',icon='INFO')
                row = layout.row()
                row.label(text='请先选择一个或多个建筑对象')
                return
            else:
                # 屋顶属性
                box = layout.box()
                if bData.aca_type != con.ACA_TYPE_BUILDING:
                    box.enabled = False
                # 屋顶样式
                droplistRoofstyle = box.row()
                droplistRoofstyle.prop(
                    bData, "roof_style",text='') 
                # 屋顶营造按钮
                buttonBuildroof = box.row()
                buttonBuildroof.operator(
                    "aca.build_roof",icon='HOME',
                    text='重新生成屋顶',depress=True)# 

# “斗栱属性”子面板
class ACA_PT_dougong(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "筑韵古建"             # 标签页名称
    bl_label = ""                       # 面板名称，已替换为draw_header实现
    bl_parent_id = "ACA_PT_roof_props"  # 父面板
    bl_options = {"DEFAULT_CLOSED"}     # 默认折叠

    # 仅在选中建筑根节点时显示该面板
    @classmethod 
    def poll(self, context):
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            return True
        return
    
    # 在标题栏中添加显示/隐藏开关
    def draw_header(self,context):
        layout = self.layout
        row = layout.row()
        buildingObj,bData,objData = utils.getRoot(context.object)
        row.prop(bData, "is_showDougong",text='斗栱属性')
        if bData.aca_type != con.ACA_TYPE_BUILDING:
            layout.enabled = False

    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: return

            layout = self.layout
            if bData.aca_type != con.ACA_TYPE_BUILDING:
                layout.enabled = False
            if not bData.is_showDougong:
                layout.enabled = False

            box = layout.box()
            toolBox = box.column(align=True)
            toolBar = toolBox.grid_flow(
                align=True,columns=2)
            # 是否使用斗栱
            if bData.use_dg:
                checkbox_icon = 'CHECKBOX_HLT'
            else:
                checkbox_icon = 'CHECKBOX_DEHLT'
            checkboxUsedg = toolBar.column(align=True)
            checkboxUsedg.prop(
                bData, "use_dg",
                toggle=True,icon=checkbox_icon)
            # 是否使用平板枋
            if bData.use_pingbanfang:
                checkbox_icon = 'CHECKBOX_HLT'
            else:
                checkbox_icon = 'CHECKBOX_DEHLT'
            checkboxUsePbf = toolBar.column(align=True)
            checkboxUsePbf.prop(
                bData, "use_pingbanfang",
                toggle=True,icon=checkbox_icon)

            # 斗栱出跳
            toolBar = toolBox.grid_flow(align=True,columns=1)
            inputDgStyle = toolBar.column(align=True)
            inputDgStyle.prop(
                bData, "dg_style",
                text='斗栱类型') 
            inputDkScale = toolBar.column(align=True)
            inputDkScale.prop(
                bData, "dk_scale",
                text='斗栱放大') 
            inputDgextend = toolBar.column(align=True)
            inputDgextend.prop(
                bData, "dg_extend",
                text='斗栱出跳') 
            inputDgextend.enabled =False
            # # 斗栱高度
            # inputDgheight = toolBar.column(align=True)
            # inputDgheight.prop(
            #     bData, "dg_height",
            #     text='斗栱高度') 
            # 斗栱间距
            inputDggap = toolBar.column(align=True)
            inputDggap.prop(
                bData, "dg_gap",
                text='斗栱间距') 
            
            if not bData.use_dg:
                checkboxUsePbf.enabled =False
                inputDgextend.enabled =False
                #inputDgheight.enabled =False
                inputDggap.enabled =False

# “梁架属性”子面板
class ACA_PT_beam(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "筑韵古建"             # 标签页名称
    bl_parent_id = "ACA_PT_roof_props"  # 父面板
    bl_options = {"DEFAULT_CLOSED"}     # 默认折叠
    bl_label = ""                       # 面板名称，已替换为draw_header实现

    # 仅在选中建筑根节点时显示该面板
    @classmethod 
    def poll(self, context):
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            return True
        return
    
    # 在标题栏中添加显示/隐藏开关
    def draw_header(self,context):
        layout = self.layout
        row = layout.row()
        buildingObj,bData,objData = utils.getRoot(context.object)
        row.prop(bData, "is_showBeam",text='梁架属性')
        if bData.aca_type != con.ACA_TYPE_BUILDING:
            layout.enabled = False

    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: return

            layout = self.layout
            if bData.aca_type != con.ACA_TYPE_BUILDING:
                layout.enabled = False
            if not bData.is_showBeam:
                layout.enabled = False

            box = layout.box()
            toolBox = box.column(align=True)
            toolBar = toolBox.grid_flow(
                align=True,columns=1)

            # 做廊步架
            inputJujia= toolBar.column(align=True)
            if bData.y_rooms >= 3:
                if bData.use_hallway:
                    checkbox_icon = 'CHECKBOX_HLT'
                else:
                    checkbox_icon = 'CHECKBOX_DEHLT'
                #checkUseHallway = box.column(align=True)
                inputJujia.prop(
                    bData, "use_hallway",
                    text='廊间举架做法',
                    toggle=True,
                    icon=checkbox_icon) 
            # 步架数量          
            inputRaftercount = toolBar.column(align=True)
            inputRaftercount.prop(
                bData, "rafter_count",
                text='步架数量')
            # 举折系数
            droplistJuzhe = toolBar.column(align=True)
            droplistJuzhe.prop(
                bData, "juzhe",text='',)
            # 推山
            inputTuishan = toolBar.column(align=True)
            inputTuishan.prop(
                bData, "tuishan",text='庑殿推山系数',slider=True)
            # 收山
            inputShoushan = toolBar.column(align=True)
            inputShoushan.prop(
                bData, "shoushan",text='歇山收山尺寸')
            
            toolBar = toolBox.grid_flow(
                align=True,columns=2)
            # 盝顶步架宽度
            inputLudingBujia = toolBar.column(align=True)
            inputLudingBujia.prop(
                bData, "luding_rafterspan",text='盝顶檐步架宽')
            buttonDefaultLDBJ = toolBar.column(align=True)
            buttonDefaultLDBJ.operator(
                operator='aca.default_luding_rafterspan',
                text='',
                icon='SHADERFX',
            )

            # 只有庑殿可以设置推山
            if bData.roof_style != con.ROOF_WUDIAN:
                inputTuishan.enabled = False

            # 只有歇山可以设置收山
            if bData.roof_style not in (
                    con.ROOF_XIESHAN,
                    con.ROOF_XIESHAN_JUANPENG,):
                inputShoushan.enabled = False

            # 只有盝顶可以设置步架
            if bData.roof_style != con.ROOF_LUDING:
                inputLudingBujia.enabled = False
                buttonDefaultLDBJ.enabled = False

# “椽望属性”子面板
class ACA_PT_rafter(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "筑韵古建"             # 标签页名称
    bl_parent_id = "ACA_PT_roof_props"  # 父面板
    bl_options = {"DEFAULT_CLOSED"}     # 默认折叠
    bl_label = ""                       # 面板名称，已替换为draw_header实现

    # 仅在选中建筑根节点时显示该面板
    @classmethod 
    def poll(self, context):
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            return True
        return
    
    # 在标题栏中添加显示/隐藏开关
    def draw_header(self,context):
        layout = self.layout
        row = layout.row()
        buildingObj,bData,objData = utils.getRoot(context.object)
        row.prop(bData, "is_showRafter",text='椽望属性')
        if bData.aca_type != con.ACA_TYPE_BUILDING:
            layout.enabled = False

    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: return

            layout = self.layout
            if bData.aca_type != con.ACA_TYPE_BUILDING:
                layout.enabled = False
            if not bData.is_showRafter:
                layout.enabled = False

            box = layout.box()
            toolBox = box.column(align=True)
            toolBar = toolBox.grid_flow(
                align=True,columns=1)
            # 出冲
            inputChong = toolBar.column(align=True)
            inputChong.prop(
                bData, "chong",text='出冲(椽径)') 
            # 起翘
            inputQiao = toolBar.column(align=True)
            inputQiao.prop(
                bData, "qiqiao",text='起翘(椽径)')
            # 梁头系数
            inputLiangtou = toolBar.column(align=True)
            inputLiangtou.prop(
                bData, "liangtou",text='梁头系数')

            toolBar = toolBox.grid_flow(
                align=True,columns=2)
            # 是否使用飞椽
            if bData.use_flyrafter:
                checkbox_icon = 'CHECKBOX_HLT'
            else:
                checkbox_icon = 'CHECKBOX_DEHLT'
            checkboxUseflyrafter = toolBar.column(align=True)
            checkboxUseflyrafter.prop(
                bData, "use_flyrafter",
                text='使用飞椽',toggle=True,
                icon=checkbox_icon) 
            # 庑殿、歇山不可以不做飞椽
            if bData.roof_style in (
                con.ROOF_WUDIAN,
                con.ROOF_XIESHAN,
                con.ROOF_XIESHAN_JUANPENG,
                con.ROOF_LUDING,
            ):
                checkboxUseflyrafter.enabled = False

            # 是否使用望板
            if bData.use_wangban:
                checkbox_icon = 'CHECKBOX_HLT'
            else:
                checkbox_icon = 'CHECKBOX_DEHLT'
            checkboxUseWangban = toolBar.column(align=True)
            checkboxUseWangban.prop(
                bData, "use_wangban",
                toggle=True,text='使用望板',
                icon=checkbox_icon) 
            
            # 只有庑殿、歇山，可以设置冲、翘
            if bData.roof_style not in (
                    con.ROOF_WUDIAN,
                    con.ROOF_XIESHAN,
                    con.ROOF_XIESHAN_JUANPENG,
                    con.ROOF_LUDING,
                    ):
                inputChong.enabled = False
                inputQiao.enabled = False

            # 瞥向处理
            if bData.use_pie:
                checkbox_icon = 'CHECKBOX_HLT'
            else:
                checkbox_icon = 'CHECKBOX_DEHLT'
            checkboxUsePie = toolBar.column(align=True)
            checkboxUsePie.prop(
                bData, "use_pie",
                text='撇向处理',toggle=True,
                icon=checkbox_icon) 

# “瓦作属性”子面板
class ACA_PT_tiles(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "筑韵古建"             # 标签页名称
    bl_parent_id = "ACA_PT_roof_props"  # 父面板
    bl_options = {"DEFAULT_CLOSED"}     # 默认折叠
    bl_label = ""                       # 面板名称，已替换为draw_header实现

    # 仅在选中建筑根节点时显示该面板
    @classmethod 
    def poll(self, context):
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj != None:
            return True
        return
    
    # 在标题栏中添加显示/隐藏开关
    def draw_header(self,context):
        layout = self.layout
        row = layout.row()
        buildingObj,bData,objData = utils.getRoot(context.object)
        row.prop(bData, "is_showTiles",text='瓦作属性')
        if bData.aca_type != con.ACA_TYPE_BUILDING:
            layout.enabled = False

    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            layout = self.layout
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: return
            if bData.aca_type != con.ACA_TYPE_BUILDING:
                layout.enabled = False
            
            # 瓦作属性
            box = layout.box()
            # row = box.row()
            # row.prop(bData, "tile_width") # 瓦垄宽度
            # row = box.row()
            # row.prop(bData, "tile_length") # 瓦片长度
            # row = box.row()
            # row.prop(bData, "tile_width_real") # 瓦垄宽度
            row = box.row()
            row.prop(bData, "tile_scale") # 瓦作缩放
            row = box.row()
            row.prop(bData, "paoshou_count") # 跑兽数量
            row = box.row()
            row.prop(bData, "tile_color") # 瓦面颜色
            row = box.row()
            row.prop(bData, "tile_alt_color") # 瓦面剪边颜色

            if not bData.is_showTiles:
                layout.enabled = False

# “院墙参数”面板
class ACA_PT_yardwall_props(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "筑韵古建"         # 标签页名称
    bl_label = "院墙参数"            # 面板名称，显示为可折叠的箭头后
    bl_options = {"DEFAULT_CLOSED"}     # 默认折叠
    
    @classmethod 
    def poll(self, context):
        isAcaObj = False
        # 从当前场景中载入数据集
        if context.object != None:
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj != None: 
                if bData.aca_type == con.ACA_TYPE_YARDWALL:
                    isAcaObj = True
        if isAcaObj and build.isFinished:
            return True
            
    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            layout = self.layout
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: 
                # 如果不属于建筑构件，提示，并隐藏所有子面板
                row = layout.row()
                row.label(text='没有设置项',icon='INFO')
                row = layout.row()
                row.label(text='请先选择一个或多个建筑对象')
                return
            else:
                # 院墙属性
                box = layout.box()
                if bData.aca_type != con.ACA_TYPE_YARDWALL:
                    box.enabled = False
                toolBar = box.grid_flow(columns=1, align=True)

                # 是否做4面围墙
                if bData.is_4_sides:
                    checkbox_icon = 'CHECKBOX_HLT'
                else:
                    checkbox_icon = 'CHECKBOX_DEHLT'
                checkbox4sides = toolBar.column(align=True)
                checkbox4sides.prop(bData,
                    'is_4_sides',
                    toggle=True,
                    text='四面环绕',
                    icon=checkbox_icon)
                # 院墙进深
                inputYardDeepth = toolBar.column(align=True)
                inputYardDeepth.prop(bData,'yard_depth',
                    text='院墙进深')
                if not bData.is_4_sides:
                    inputYardDeepth.enabled = False
                # 院墙面阔
                inputYardWidth = toolBar.column(align=True)
                inputYardWidth.prop(bData,'yard_width',
                    text='院墙面阔')
                # 院墙高度
                inputYardwallHeight = toolBar.column(align=True)
                inputYardwallHeight.prop(bData,
                    'yardwall_height',
                    text='院墙高度')
                # 院墙厚度
                inputYardwallDeepth = toolBar.column(align=True)
                inputYardwallDeepth.prop(bData,
                    'yardwall_depth',
                    text='院墙厚度')
                # 帽瓦斜率
                inputYardtileAngle = toolBar.column(align=True)
                inputYardtileAngle.prop(bData,
                    'yardwall_angle',
                    text='帽瓦斜率')
                
                
                buttionBuildYardwall = box.row()
                buttionBuildYardwall.operator(
                    'aca.build_yardwall',
                    icon='PLAY',
                    depress=True,
                    text='重新生成院墙')