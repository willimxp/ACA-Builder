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
        row = box.row()
        row.prop(scnData, "template")
        # 按钮，生成新建筑
        row = box.row()
        row.operator("aca.add_newbuilding",icon='FILE_3D')
        # 按钮，保存模版
        row = box.row()
        row.operator("aca.save_template",icon='HOME',text='保存模板')
        
        # 测试按钮
        row = layout.row()
        row.operator("aca.test",icon='HOME')

        # 从当前场景中载入数据集
        if context.object != None:
            # 追溯全局属性
            buildingObj,bData,objData = utils.getRoot(context.object)
            if buildingObj == None: 
                layout.label(text='营造中...请耐心等待')
                return
            else:
                # 名称
                box = layout.box()
                row = box.row()
                col = row.column()
                col.prop(context.object,"name",text="")
                # 聚焦根节点
                col = row.column()
                col.operator("aca.focus_building",icon='FILE_PARENT')
                if objData.aca_type == con.ACA_TYPE_BUILDING:
                    col.enabled = False
                # 斗口值
                row = box.row()
                col = row.column()
                col.prop(bData,'DK')
                col = row.column()
                col.operator("aca.default_dk",icon='SHADERFX',text='')


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

            # # 名称
            # row = layout.row()
            # col = row.column()
            # col.prop(context.object,"name",text="")
            # # 聚焦根节点
            # col = row.column()
            # col.operator("aca.focus_building",icon='FILE_PARENT')
            # if objData.aca_type == con.ACA_TYPE_BUILDING:
            #     col.enabled = False

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
            row = box.row()
            row.prop(bData, "platform_height")
            row = box.row()
            row.prop(bData, "platform_extend")

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
            row = box.column(align=True)
            row.prop(bData, "x_rooms")      # 面阔间数
            row.prop(bData, "x_1")          # 明间宽度
            if bData.x_rooms >= 3:
                row.prop(bData, "x_2")      # 次间宽度
            if bData.x_rooms >= 5:
                row.prop(bData, "x_3")      # 梢间宽度
            if bData.x_rooms >= 7:
                row.prop(bData, "x_4")      # 尽间宽度
                
            row = box.column(align=True)
            row.prop(bData, "y_rooms")      # 进深间数
            row.prop(bData, "y_1")          # 明间深度
            if bData.y_rooms >= 3:
                row.prop(bData, "y_2")      # 次间深度
            if bData.y_rooms >= 5:
                row.prop(bData, "y_3")      # 梢间深度

            #柱子属性
            box = layout.box()
            row = box.row()
            row.prop(bData, "piller_source")    # 柱样式
            row = box.row()
            row.prop(bData, "piller_height")    # 柱高
            row = box.row()
            row.prop(bData, "piller_diameter")  # 柱径
            row = box.row()
            col = row.column()
            col.operator(
                "aca.del_piller",icon='X',)     # 按钮:减柱
            if objData.aca_type != con.ACA_TYPE_PILLER:
                col.enabled=False
            col = row.column()
            col.operator(
                "aca.reset_floor",icon='FILE',) # 按钮:重设柱网
            
            # 枋属性
            box = layout.box()
            row = box.row()
            col = row.column()
            col.label(text='设置枋子:')
            col = row.column()
            col.prop(objData, "use_smallfang") # 使用小额枋
            row = box.row()
            col = row.column()
            col.operator("aca.add_fang",icon='LINKED',)# 按钮:连接
            if objData.aca_type != con.ACA_TYPE_PILLER \
                or len(context.selected_objects)<2:
                    col.enabled=False

            col = row.column()
            col.operator("aca.del_fang",icon='UNLINKED',)# 按钮:断开
            if objData.aca_type == con.ACA_TYPE_PILLER:col.enabled=False

            # 切换显示/隐藏台基
            if not bData.is_showPillers:
                layout.enabled = False

                
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

            # 墙样式
            box = layout.box()
            row = box.row() 
            if objData.aca_type == con.ACA_TYPE_WALL:
                row.prop(objData, "wall_source") # 个体
            else:
                row.prop(bData, "wall_source") # 全局
            # 工具栏
            row = box.row()
            col = row.column()
            # 生成墙
            col.operator("aca.add_wall",icon='MOD_BUILD')
            if objData.aca_type != con.ACA_TYPE_PILLER \
                or len(context.selected_objects) < 2:
                col.enabled = False
            # 删除隔断
            col = row.column()
            col.operator("aca.del_wall",icon='TRASH')
            if objData.aca_type not in (
                con.ACA_WALLTYPE_WALL,con.ACA_TYPE_WALL_CHILD):
                col.enabled = False
                
            # 隔扇、槛窗
            box = layout.box()
            # 个体
            if objData.aca_type == con.ACA_TYPE_WALL:
                row = box.row() 
                row.prop(objData, "lingxin_source")   # 棂心样式
                row = box.row()
                row.prop(objData, "door_num")     # 隔扇数量
                row = box.row()
                row.prop(objData, "gap_num")      # 抹头数量
                row = box.row()
                row.prop(objData, "use_topwin")   # 添加横披窗
                row = box.row()
                row.prop(objData, "door_height")  # 中槛高度
                if not objData.use_topwin:
                    row.enabled = False    
            # 全局  
            else: 
                row = box.row() 
                row.prop(bData, "lingxin_source")   # 棂心样式
                row = box.row()
                row.prop(bData, "door_num")     # 隔扇数量
                row = box.row()
                row.prop(bData, "gap_num")      # 抹头数量
                row = box.row()
                row.prop(bData, "use_topwin")   # 添加横披窗
                row = box.row()
                row.prop(bData, "door_height")  # 中槛高度
                if not bData.use_topwin:
                    row.enabled = False
            # 工具栏
            row = box.row()
            row.operator("aca.add_door",icon='MOD_TRIANGULATE')# 按钮：生成隔扇
            row.operator("aca.add_window",icon='MOD_LATTICE')# 按钮：生成槛窗
            if objData.aca_type != con.ACA_TYPE_PILLER \
                or len(context.selected_objects) < 2:
                row.enabled = False
            row = box.row()
            row.operator("aca.del_wall",icon='TRASH')# 按钮：删除隔断
            if objData.aca_type not in (
                con.ACA_TYPE_WALL_CHILD,
                con.ACA_TYPE_WALL):
                row.enabled = False
        
            # 切换显示/隐藏台基
            if not bData.is_showWalls:
                layout.enabled = False

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
            