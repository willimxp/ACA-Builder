# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   构建逻辑类

import math
import bmesh
import bpy
from bpy_extras import object_utils
from bpy_extras.object_utils import AddObjectHelper
from mathutils import Vector,Matrix,geometry,Euler

from . import data
from . import const
from . import utils
from . import const

# 添加建筑empty根节点
# 被ACA_OT_add_newbuilding类调用
def add_building_root(self, context:bpy.types.Context):
    # 0.1、载入常量列表
    con = const.ACA_Consts
    
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    root_obj = context.object
    root_obj.location = context.scene.cursor.location   # 原点摆放在3D Cursor位置
    root_obj.name = con.BUILDING_NAME   # 系统遇到重名会自动添加00x的后缀       
    root_obj.ACA_data.aca_obj = True
    root_obj.ACA_data.aca_type = 'building'
    root_obj.empty_display_size = 5
    root_obj.empty_display_type = 'SPHERE'

    print("ACA: Building Root added")

# 根据固定模板，创建新的台基
# 被ACA_OT_add_newbuilding类调用
def add_platform(self, context):
    # 0、数据初始化（常量、场景参数、对象参数）
    # 0.1、载入常量列表
    con = const.ACA_Consts
    # 0.2、从当前场景中载入数据集
    scnData : data.ACA_data_scene = context.scene.ACA_data

    # 绑定根节点“古建筑.00x”
    parent_obj = context.object

    # 1、创建地基===========================================================
    # 载入模板配置
    platform_height = con.PLATFORM_HEIGHT
    platform_extend = con.PLATFORM_EXTEND
    # 构造cube三维
    height = platform_height
    width = platform_extend * 2 + 4 #scnData.x_total
    length = platform_extend * 2 + 3 #scnData.y_total
    bpy.ops.mesh.primitive_cube_add(
                size=1.0, 
                calc_uvs=True, 
                enter_editmode=False, 
                align='WORLD', 
                location = (0,0,height/2), 
                scale=(width,length,height))
    aca_obj = bpy.context.object
    # 填入通用属性
    utils.setAcaProps(
        aca_obj = aca_obj,
        aca_parent = parent_obj,
        aca_name = con.PLATFORM_NAME,
        aca_type = con.ACA_TYPE_PLATFORM
    )
    
    print("ACA: Platform added")

# 根据用户在插件面板调整的台基参数，更新台基外观
# 绑定于data.py中objdata属性中触发的回调
def update_platform(self, context):
    # 0、数据初始化（常量、场景参数、对象参数）
    # 0.1、载入常量列表
    con = const.ACA_Consts
    # 0.2、从当前场景中载入数据集
    scnData : data.ACA_data_scene = context.scene.ACA_data
    # 0.3、从当前场景中载入数据集
    if context.object != None:
        objData : data.ACA_data_obj = context.object.ACA_data

    if scnData.is_auto_redraw:
        # 重绘
        pf_obj = bpy.context.object
        pf_extend = objData.platform_extend
        # 缩放台基尺寸
        pf_obj.dimensions= (
            pf_extend * 2 + 4, #scnData.x_total,
            pf_extend * 2 + 3, #scnData.y_total,
            objData.platform_height
        )
        # 应用缩放
        bpy.ops.object.transform_apply(
            scale=True,
            rotation=True,
            location=False,
            isolate_users=True) # apply多用户对象时可能失败，所以要加上这个强制单用户
        # 平移，保持台基下沿在地平线高度
        pf_obj.location.z = objData.platform_height /2
    
    print("ACA: Platform updated")

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
        # 常数列表
        con = const.ACA_Consts
        
        # 1.定位到“ACA”根collection，如果没有则新建
        utils.setCollection(context, con.ROOT_COLL_NAME)

        # 2.添加建筑empty，默认为ACA01，用户可以自行修改
        add_building_root(self,context)

        # 3.根据模板，自动创建建筑
        # 3.1 生成台基
        add_platform(self,context)

        return {'FINISHED'}
    
def set_pillers_date(context):
    # 从data中读取用户通过Panel输入的值
    dataset : data.ACA_data_scene = context.scene.ACA_data
    # 计算通面阔
    base_width = 0.0
    x_rooms = dataset.x_rooms   # 面阔几间
    if x_rooms >=1:
        base_width += dataset.x_1   # 明间
    if x_rooms >=3:
        base_width += dataset.x_2 * 2   # 次间
    if x_rooms >=5:
        base_width += dataset.x_3 * 2   # 梢间
    if x_rooms >=7:
        base_width += dataset.x_4 * 2   # 尽间
    if x_rooms >=9:
        base_width += dataset.x_3 * (x_rooms-7) #更多梢间
    
    # 计算通进深
    base_length = 0.0
    y_rooms = dataset.y_rooms   # 进深几间
    if y_rooms >=1:
        base_length += dataset.y_1 * (2 - y_rooms % 2)  # 明间
    if y_rooms >=3:
        base_length += dataset.y_2 * 2   # 次间
    if y_rooms >=5:
        base_length += dataset.y_3 * 2   # 梢间
    
    # 保存通面阔计算结果，以便其他函数中复用
    dataset.x_total = base_width
    # 保存通进深计算结果，以便其他函数中复用
    dataset.y_total = base_length

    # 构造柱网X坐标序列，罗列了1，3，5，7，9，11间的情况，未能抽象成通用公式
    global net_x
    net_x = []  # 重新计算
    if x_rooms >=1:     # 明间
        offset = dataset.x_1 / 2
        net_x.append(offset)
        net_x.insert(0, -offset)
    if x_rooms >=3:     # 次间
        offset = dataset.x_1 / 2 + dataset.x_2
        net_x.append(offset)
        net_x.insert(0, -offset)  
    if x_rooms >=5:     # 梢间
        offset = dataset.x_1 / 2 + dataset.x_2 \
                + dataset.x_3
        net_x.append(offset)
        net_x.insert(0, -offset)  
    if x_rooms >=7:     # 尽间
        offset = dataset.x_1 / 2 + dataset.x_2 \
            + dataset.x_3 + dataset.x_4
        net_x.append(offset)
        net_x.insert(0, -offset)  
    if x_rooms >=9:     #更多梢间
        offset = dataset.x_1 / 2 + dataset.x_2 \
            + dataset.x_3 * 2
        net_x[-1] = offset
        net_x[0]= -offset  
        offset = dataset.x_1 / 2 + dataset.x_2 \
            + dataset.x_3 *2 + dataset.x_4
        net_x.append(offset)
        net_x.insert(0, -offset) 
    if x_rooms >=11:     #更多梢间
        offset = dataset.x_1 / 2 + dataset.x_2 \
            + dataset.x_3 * 3
        net_x[-1] = offset
        net_x[0]= -offset  
        offset = dataset.x_1 / 2 + dataset.x_2 \
            + dataset.x_3 *3 + dataset.x_4
        net_x.append(offset)
        net_x.insert(0, -offset) 

    # 构造柱网Y坐标序列，罗列了1-5间的情况，未能抽象成通用公式
    global net_y
    net_y=[]    # 重新计算
    if y_rooms%2 == 1: # 奇数间
        if y_rooms >= 1:     # 明间
            offset = dataset.y_1 / 2
            net_y.append(offset)
            net_y.insert(0, -offset)
        if y_rooms >= 3:     # 次间
            offset = dataset.y_1 / 2 + dataset.y_2
            net_y.append(offset)
            net_y.insert(0, -offset)  
        if y_rooms >= 5:     # 梢间
            offset = dataset.y_1 / 2 + dataset.y_2 \
                    + dataset.y_3
            net_y.append(offset)
            net_y.insert(0, -offset) 
    else:   #偶数间
        if y_rooms >= 2:
            net_y.append(0)
            offset = dataset.y_1
            net_y.append(offset)
            net_y.insert(0,-offset)
        if y_rooms >= 4:
            offset = dataset.y_1 + dataset.y_2
            net_y.append(offset)
            net_y.insert(0,-offset)

# 根据基本参数，构建建筑体
class ACA_OT_build_piller(bpy.types.Operator, AddObjectHelper):
    bl_idname="aca.build_piller"
    bl_label = "生成柱网层"

    def execute(self, context): 
        # 从data中读取用户通过Panel输入的值
        dataset : data.ACA_data_scene = context.scene.ACA_data  

        # 0、柱网计算
        set_pillers_date(context)
        # 0.1、根据开间变化，刷新台基
        bpy.ops.aca.build_platform()

        # 1、设置目录
        root_coll = utils.setCollection(context, "ACA.柱网")

        # 2、创建根对象（empty）===========================================================
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        root_obj = context.object
        root_obj.name = "柱网.root"
        root_z = dataset.platform_height
        root_obj.location = (0,0,root_z)

        # 3、创建柱网
        # 3.1、默认创建简单柱子
        piller_name = "基本立柱"
        piller_height = 0.2      # 柱子多高
        piller_R = 0.5       # 柱子直径
        piller_basemesh = utils.addCylinder(radius=piller_R,
                    depth=piller_height,
                    location=(0, 0, piller_height/2),
                    name=piller_name,
                    root_obj=root_obj
        )
        # 3.2、循环生成
        x_rooms = dataset.x_rooms   # 面阔几间
        y_rooms = dataset.y_rooms   # 进深几间
        for y in range(y_rooms + 1):
            for x in range(x_rooms + 1):
                # 统一命名为“柱.x/y”，以免更换不同柱时，柱网中的名称无法匹配
                piller_copy_name = "柱" + \
                    '.' + str(x) + '/' + str(y)
                
                # 验证是否已被用户手工减柱
                piller_list_str = dataset.piller_net
                if piller_copy_name not in dataset.piller_net \
                        and piller_list_str != "" :
                    # print("PP: piller skiped " + piller_copy_name)
                    continue
                
                piller_loc = (net_x[x],net_y[y],piller_basemesh.location.z)
                # 复制柱子，仅instance，包含modifier
                piller_copy = utils.ObjectCopy(
                    sourceObj = piller_basemesh,
                    name = piller_copy_name,
                    location=piller_loc,
                    parentObj = root_obj
                )
        bpy.data.objects.remove(piller_basemesh)

        print("ACA: Build pills")
        return {'FINISHED'}