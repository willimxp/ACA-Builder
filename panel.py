# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   定义插件面板的UI

import bpy
from . import data
from .const import ACA_Consts as con
from . import utils
from .data import ACA_data_obj as acaData
from .data import ACA_data_scene as scnData

# 营造向导面板
class ACA_PT_basic(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示 
    
    # 自定义属性
    bl_category = "古建营造"         # 标签页名称
    bl_label = "营造向导"            # 面板名称，显示为可折叠的箭头后
    
    def draw(self, context):
        # 从当前场景中载入数据集
        scnData : data.ACA_data_scene = context.scene.ACA_data
        layout = self.layout
        box = layout.box()
        
        # 模板选择列表
        droplistTemplate = box.column(align=True)
        droplistTemplate.prop(scnData, "template",text='')
        
        toolBox = box.column(align=True)
        toolBar = toolBox.grid_flow(columns=2, align=True)
        # 保存模版
        col = toolBar.column(align=True)
        col.operator(
            "aca.save_template",icon='FILE_TICK',
            text='保存模板')
        # 删除模版
        col = toolBar.column(align=True)
        col.operator(
            "aca.del_template",icon='TRASH',
            text='删除模板')

        toolBar = toolBox.grid_flow(columns=1, align=True)
        # 生成新建筑        
        buttonAddnew = toolBar.column(align=True)
        buttonAddnew.operator(
            "aca.add_newbuilding",icon='PLAY',
            depress=True,text='添加新建筑'
            )
        
        # # 测试按钮
        # row = layout.row()
        # row.operator("aca.test",icon='HOME')

        return

# “屋身参数”面板
class ACA_PT_props(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "古建营造"         # 标签页名称
    bl_label = "屋身参数"            # 面板名称，显示为可折叠的箭头后

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
            
            box = layout.box()
            # 名称
            row = box.row(align=True)
            col = row.column(align=True)
            col.prop(context.object,"name",text="")
            # 聚焦根节点
            col = row.column(align=True)
            col.operator("aca.focus_building",icon='FILE_PARENT')
            if objData.aca_type == con.ACA_TYPE_BUILDING:
                col.enabled = False
                
            # 斗口值
            row = box.row(align=True)
            col = row.column(align=True)
            col.prop(bData,'DK')
            # 计算默认斗口值
            col = row.column(align=True)
            col.operator("aca.default_dk",icon='SHADERFX',text='')

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

            # 更新建筑
            row = box.row(align=True)
            row.operator(
                "aca.update_building",icon='PLAY',
                depress=True,text='更新建筑'
            )


# “台基属性”子面板
class ACA_PT_platform(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "古建营造"             # 标签页名称
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

    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            layout = self.layout
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: return

            # 台基属性
            box = layout.box()
            col = box.column(align=True)
            col.prop(bData, "platform_height")
            col.prop(bData, "platform_extend")

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
    bl_category = "古建营造"             # 标签页名称
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
                "aca.reset_floor",icon='FILE',
                depress=True,text='重设') 
                
# “墙属性”子面板
class ACA_PT_wall(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "古建营造"             # 标签页名称
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
        row.prop(bData, "is_showWalls",text='墙体属性')

    def draw_header_preset(self,context):
        layout = self.layout
        row = layout.row()
        buildingObj,bData,objData = utils.getRoot(context.object)
        if buildingObj == None: return
        if objData.aca_type == con.ACA_TYPE_WALL:
            col = row.column()
            col.label(text='[个体]',icon='KEYTYPE_JITTER_VEC')
        else:
            col = row.column()
            col.label(text='[全局]',icon='KEYTYPE_KEYFRAME_VEC')

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

            # 工具栏：加枋、加墙、加门、加窗、删除
            toolBox = box.column(align=True)
            toolBar = toolBox.grid_flow(columns=2, align=True)
            # 按钮：加枋
            buttonFang = toolBar.column(align=True)
            buttonFang.operator(
                "aca.add_fang",icon='LINKED',text='额枋')
            # 按钮：加门
            buttonDoor = toolBar.column(align=True)
            buttonDoor.operator(
                "aca.add_door",icon='MOD_TRIANGULATE',text='隔扇')
            # 按钮：加墙
            buttonWall = toolBar.column(align=True)
            buttonWall.operator(
                "aca.add_wall",icon='MOD_BUILD',text='槛墙')
            # 按钮：加窗
            buttonWin = toolBar.column(align=True)
            buttonWin.operator(
                "aca.add_window",icon='MOD_LATTICE',text='槛窗')
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
            # 删除按钮，是否选中个隔断对象
            if objData.aca_type not in (
                con.ACA_TYPE_FANG,          # 枋对象
                con.ACA_TYPE_WALL_CHILD,    # 槛墙对象
                con.ACA_TYPE_WALL,          # wallProxy
                ):
                buttonDel.enabled = False

            # 附属参数框
            if objData.aca_type == con.ACA_TYPE_WALL:     
                # 如果用户选中了wallProxy
                # 仅设置个体参数，取objData
                dataSource = objData
            else:
                dataSource = bData
            
            # 是否使用小额枋       
            toolBox = box.column(align=True)
            
            toolBar = toolBox.grid_flow(align=True,columns=1)
            # 隔扇数量
            inputDoorNum = toolBar.column(align=True)
            inputDoorNum.prop(
                dataSource, "door_num",text='隔扇数量')
            # 抹头数量
            inputGapNum = toolBar.column(align=True)
            inputGapNum.prop(
                dataSource, "gap_num",text='抹头数量')
            # 中槛高度
            inputMidHeight = toolBar.column(align=True)
            inputMidHeight.prop(
                dataSource, "door_height",text='中槛高度')
            
            toolBar = toolBox.grid_flow(align=True,columns=2)
            # 复选框：是否使用小额枋
            checkboxFang = toolBar.column(align=True)
            checkboxFang.prop(
                bData, "use_smallfang",
                toggle=1,text="使用小额枋") 
            # 复选框：是否使用横披窗
            checkboxTopwin = toolBar.column(align=True)
            checkboxTopwin.prop(
                dataSource, "use_topwin",
                toggle=1,text='使用横披窗')

            # 关联“是否使用横披窗”和“中槛高度”
            if not dataSource.use_topwin:
                inputMidHeight.enabled = False 
        
        return

# “屋顶参数”面板
class ACA_PT_roof_props(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "古建营造"         # 标签页名称
    bl_label = "屋顶参数"            # 面板名称，显示为可折叠的箭头后

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
                row = layout.row()
                row.prop(bData, "roof_style") # 屋顶样式
                # 屋顶营造按钮
                row = layout.row()
                row.operator("aca.build_roof",icon='HOME',)# 按钮：生成屋顶

# “斗栱属性”子面板
class ACA_PT_dougong(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "古建营造"             # 标签页名称
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

    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            layout = self.layout
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: return
            row = layout.row()
            # 是否使用斗栱
            col = row.column()
            col.prop(bData, "use_dg")
            # 是否使用平板枋
            col = row.column()
            col.prop(bData, "use_pingbanfang")

            # 斗栱属性
            box = layout.box()
            
            row = box.row()
            row.prop(bData, "dg_extend") # 斗栱出跳
            row = box.row()
            row.prop(bData, "dg_height") # 斗栱高度
            row = box.row()
            row.prop(bData, "dg_gap") # 斗栱间距
            row = box.row()
            row.prop(bData, "dg_piller_source") # 柱头斗栱
            row = box.row()
            row.prop(bData, "dg_fillgap_source") # 补间斗栱
            row = box.row()
            row.prop(bData, "dg_corner_source") # 转角斗栱
            if not bData.is_showDougong:
                layout.enabled = False
            if not bData.use_dg:
                box.enabled =False

# “梁椽望属性”子面板
class ACA_PT_BPW(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "古建营造"             # 标签页名称
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
        row.prop(bData, "is_showBPW",text='椽望属性')

    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            layout = self.layout
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: return

            # 屋顶属性
            box = layout.box()
            row = box.row()
            row.prop(bData, "rafter_count") # 椽架数量
            if bData.roof_style in (con.ROOF_WUDIAN,con.ROOF_XIESHAN):
                row = box.row()
                row.prop(bData, "chong") # 出冲
                row = box.row()
                row.prop(bData, "qiqiao") # 起翘
                # row = box.row()
                # row.prop(bData, "shengqi") # 生起
            row = box.row()
            row.prop(bData, "use_flyrafter") # 添加飞椽
            row = box.row()
            row.prop(bData, "use_wangban") # 添加望板
            if not bData.is_showBPW:
                layout.enabled = False

# “瓦作属性”子面板
class ACA_PT_tiles(bpy.types.Panel):
    # 常规属性
    bl_context = "objectmode"       # 关联的上下文，如，objectmode, mesh_edit, armature_edit等
    bl_region_type = 'UI'           # UI代表sidebar形式
    bl_space_type = 'VIEW_3D'       # View_3D在viewport中显示
    
    # 自定义属性
    bl_category = "古建营造"             # 标签页名称
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

    def draw(self, context):
        # 从当前场景中载入数据集
        if context.object != None:
            layout = self.layout
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: return
            
            # 瓦作属性
            box = layout.box()
            # row = box.row()
            # row.prop(bData, "tile_width") # 瓦垄宽度
            # row = box.row()
            # row.prop(bData, "tile_length") # 瓦片长度
            row = box.row()
            row.prop(bData, "tile_width_real") # 瓦垄宽度
            row = box.row()
            row.prop(bData, "paoshou_count") # 跑兽数量
            row = box.row()
            row.prop(bData, "flatTile_source") # 板瓦
            row = box.row()
            row.prop(bData, "circularTile_source") # 筒瓦
            row = box.row()
            row.prop(bData, "eaveTile_source") # 瓦当
            row = box.row()
            row.prop(bData, "dripTile_source") # 滴水

            # 屋脊属性
            box = layout.box()
            row = box.row()
            row.prop(bData, "ridgeTop_source") # 正脊筒
            row = box.row()
            row.prop(bData, "ridgeBack_source") # 垂脊兽后
            row = box.row()
            row.prop(bData, "ridgeFront_source") # 垂脊兽前
            row = box.row()
            row.prop(bData, "ridgeEnd_source") # 端头盘子
            row = box.row()
            row.prop(bData, "chiwen_source") # 螭吻

            if not bData.is_showTiles:
                layout.enabled = False