import bpy
import os
from bpy.props import StringProperty, CollectionProperty, IntProperty, BoolProperty
from bpy.types import Panel, Operator, PropertyGroup, UIList
import bmesh
from mathutils import Vector

# 图片项属性组
class IMAGEBROWSER_UL_items(UIList):
    def draw_item(self, 
                  context, 
                  layout, 
                  data, 
                  item, 
                  icon, 
                  active_data, 
                  active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon='IMAGE_DATA')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            # 显示缩略图
            pcoll = preview_collections["main"]
            thumb = pcoll.get(item.name)
            if thumb:
                layout.template_icon(icon_value=thumb.icon_id, scale=4.0)
            else:
                layout.label(text="", icon='IMAGE_DATA')
            layout.label(text=item.name)

# 图片项
class IMAGEBROWSER_OT_image_item(PropertyGroup):
    name: StringProperty(
        name="Name", 
        description="Image name", 
        default="")# type: ignore
    path: StringProperty(
        name="Path", 
        description="Image path", 
        default="")# type: ignore

# 生成缩略图操作符
class IMAGEBROWSER_OT_generate_previews(Operator):
    bl_idname = "imagebrowser.generate_previews"
    bl_label = "Generate Thumbnails"
    bl_description = "Generate thumbnails for all images in the list"
    
    def execute(self, context):
        scene = context.scene.ACA_data
        
        # 获取图像预览集合
        pcoll = preview_collections["main"]
        
        # 为每个图片生成预览
        for item in scene.image_browser_items:
            if os.path.exists(item.path):
                try:
                    # 尝试从预览集合中获取图像
                    thumb = pcoll.get(item.name)
                    if not thumb:
                        # 加载图像并生成预览
                        thumb = pcoll.load(item.name, item.path, 'IMAGE')
                except Exception as e:
                    self.report({'WARNING'}, f"Failed to generate preview for {item.name}: {str(e)}")
        
        return {'FINISHED'}

# 选择目录操作符
class IMAGEBROWSER_OT_select_directory(Operator):
    bl_idname = "imagebrowser.select_directory"
    bl_label = "Select Directory"
    
    directory: StringProperty(
        name="Directory",
        subtype='DIR_PATH'
    )# type: ignore
    
    def execute(self, context):
        scene = context.scene.ACA_data
        scene.image_browser_directory = self.directory
        
        # 清空现有图片列表
        scene.image_browser_items.clear()
        
        # 获取目录中的所有图片文件
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.svg')
        for file in os.listdir(self.directory):
            if file.lower().endswith(image_extensions):
                item = scene.image_browser_items.add()
                item.name = file
                item.path = os.path.join(self.directory, file)
        
        # 自动生成预览（可选）
        if context.scene.image_browser_auto_preview:
            bpy.ops.imagebrowser.generate_previews()
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# 查看图片操作符
class IMAGEBROWSER_OT_view_image(Operator):
    bl_idname = "imagebrowser.view_image"
    bl_label = "View Image"
    
    image_path: StringProperty(name="Image Path")# type: ignore
    
    def execute(self, context):
        # 尝试在 Blender 图像编辑器中打开图片
        try:
            img = bpy.data.images.load(self.image_path)
            area = next((a for a in context.screen.areas if a.type == 'IMAGE_EDITOR'), None)
            if area:
                area.spaces.active.image = img
            else:
                self.report({'INFO'}, f"Image loaded: {self.image_path}. Open an Image Editor to view it.")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load image: {str(e)}")
        
        return {'FINISHED'}

# 主面板
class IMAGEBROWSER_PT_main_panel(Panel):
    bl_label = "Image Browser"
    bl_idname = "IMAGEBROWSER_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Image Browser"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene.ACA_data
        
        # 目录选择
        row = layout.row()
        row.prop(scene, "image_browser_directory", text="")
        row.operator("imagebrowser.select_directory", 
                     text="", 
                     icon='FILE_FOLDER')
        
        # 自动生成预览选项
        layout.prop(scene, 
                    "image_browser_auto_preview", 
                    text="Auto Generate Thumbnails")
        
        # 生成预览按钮
        if scene.image_browser_items:
            layout.operator("imagebrowser.generate_previews")
        
        # 图片列表
        row = layout.row()
        row.template_list("IMAGEBROWSER_UL_items", 
                          "", 
                          scene, 
                          "image_browser_items", 
                          scene, 
                          "image_browser_index", 
                          type='GRID')
        
        # 查看按钮
        # if scene.image_browser_items:
        #     if 0 <= scene.image_browser_index < len(scene.image_browser_items):
        #         item = scene.image_browser_items[scene.image_browser_index]
        #         row = layout.row()
        #         row.operator("imagebrowser.view_image", text="View Image").image_path = item.path

# 预览集合
preview_collections = {}