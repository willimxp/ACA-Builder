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
# 返回建筑empty根节点对象
# 被ACA_OT_add_newbuilding类调用
def add_building_root(self, context:bpy.types.Context):
    # 0.1、载入常量列表
    con = const.ACA_Consts
    
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    buildingObj = context.object
    buildingObj.location = context.scene.cursor.location   # 原点摆放在3D Cursor位置
    buildingObj.name = con.BUILDING_NAME   # 系统遇到重名会自动添加00x的后缀       
    buildingObj.ACA_data.aca_obj = True
    buildingObj.ACA_data.aca_type = con.ACA_TYPE_BUILDING
    buildingObj.empty_display_size = 5
    buildingObj.empty_display_type = 'SPHERE'
    
    print("ACA: Building Root added")
    return buildingObj

# 根据固定模板，创建新的台基
# 被ACA_OT_add_newbuilding类调用
def add_platform(self, context:bpy.types.Context,
                 buildingObj:bpy.types.Object):
    # 0、数据初始化（常量、场景参数、对象参数）
    # 0.1、载入常量列表
    con = const.ACA_Consts
    # 0.2、从当前场景中载入数据集
    scnData : data.ACA_data_scene = context.scene.ACA_data
    # 载入同级floor对象和数据
    for child in buildingObj.children:
        if child.ACA_data.aca_type == con.ACA_TYPE_FLOOR:
            floorObj = child
            floorData = floorObj.ACA_data

    # 1、创建地基===========================================================
    # 载入模板配置
    platform_height = con.PLATFORM_HEIGHT
    platform_extend = con.PLATFORM_EXTEND
    # 构造cube三维
    height = platform_height
    width = platform_extend * 2 + floorData.x_total
    length = platform_extend * 2 + floorData.y_total
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
        aca_parent = buildingObj,
        aca_name = con.PLATFORM_NAME,
        aca_type = con.ACA_TYPE_PLATFORM
    )
    
    print("ACA: Platform added")

# 根据用户在插件面板调整的台基参数，更新台基外观
# 绑定于data.py中objdata属性中触发的回调
def update_platform(self, context:bpy.types.Context):
    # 0、数据初始化（常量、场景参数、对象参数）
    # 0.1、载入常量列表
    con = const.ACA_Consts
    # 0.2、从当前场景中载入数据集
    scnData : data.ACA_data_scene = context.scene.ACA_data

    # 载入当前选中的台基的数据
    pfObj = context.object
    pfData : data.ACA_data_obj = pfObj.ACA_data
    # 载入同级的地盘对象及数据
    floorObj = utils.getAcaSibling(pfObj,con.ACA_TYPE_FLOOR)
    floorData : data.ACA_data_obj = floorObj.ACA_data

    if scnData.is_auto_redraw:
        # 重绘
        pf_extend = pfData.platform_extend
        # 缩放台基尺寸
        pfObj.dimensions= (
            pf_extend * 2 + floorData.x_total,
            pf_extend * 2 + floorData.y_total,
            pfData.platform_height
        )
        # 应用缩放(有时ops.object会乱跑，这里确保针对台基对象)
        utils.ApplyScale(pfObj)
        # 平移，保持台基下沿在地平线高度
        pfObj.location.z = pfData.platform_height /2
        # 对齐柱网
        floorObj.location.z =  pfData.platform_height
        buildingObj = pfObj.parent
        buildingObj.empty_display_size = math.sqrt(
                pfObj.dimensions.x * pfObj.dimensions.x
                + pfObj.dimensions.y * pfObj.dimensions.y
            ) / 2
    
    print("ACA: Platform updated")

# 准备柱网数据
# 将panel中设置的面宽、进深，组合成柱网数组
# 返回net_x[],net_y[]数组
def get_floor_date(self,context:bpy.types.Context,
                     floorObj:bpy.types.Object):
    # 0、数据初始化（常量、场景参数、对象参数）
    # 载入常量列表
    con = const.ACA_Consts
    # 从当前场景中载入数据集
    floorData : data.ACA_data_obj = floorObj.ACA_data

    # 构造柱网X坐标序列，罗列了1，3，5，7，9，11间的情况，未能抽象成通用公式
    x_rooms = floorData.x_rooms   # 面阔几间
    y_rooms = floorData.y_rooms   # 进深几间

    net_x = []  # 重新计算
    if x_rooms >=1:     # 明间
        offset = floorData.x_1 / 2
        net_x.append(offset)
        net_x.insert(0, -offset)
    if x_rooms >=3:     # 次间
        offset = floorData.x_1 / 2 + floorData.x_2
        net_x.append(offset)
        net_x.insert(0, -offset)  
    if x_rooms >=5:     # 梢间
        offset = floorData.x_1 / 2 + floorData.x_2 \
                + floorData.x_3
        net_x.append(offset)
        net_x.insert(0, -offset)  
    if x_rooms >=7:     # 尽间
        offset = floorData.x_1 / 2 + floorData.x_2 \
            + floorData.x_3 + floorData.x_4
        net_x.append(offset)
        net_x.insert(0, -offset)  
    if x_rooms >=9:     #更多梢间
        offset = floorData.x_1 / 2 + floorData.x_2 \
            + floorData.x_3 * 2
        net_x[-1] = offset
        net_x[0]= -offset  
        offset = floorData.x_1 / 2 + floorData.x_2 \
            + floorData.x_3 *2 + floorData.x_4
        net_x.append(offset)
        net_x.insert(0, -offset) 
    if x_rooms >=11:     #更多梢间
        offset = floorData.x_1 / 2 + floorData.x_2 \
            + floorData.x_3 * 3
        net_x[-1] = offset
        net_x[0]= -offset  
        offset = floorData.x_1 / 2 + floorData.x_2 \
            + floorData.x_3 *3 + floorData.x_4
        net_x.append(offset)
        net_x.insert(0, -offset) 

    # 构造柱网Y坐标序列，罗列了1-5间的情况，未能抽象成通用公式
    net_y=[]    # 重新计算
    if y_rooms%2 == 1: # 奇数间
        if y_rooms >= 1:     # 明间
            offset = floorData.y_1 / 2
            net_y.append(offset)
            net_y.insert(0, -offset)
        if y_rooms >= 3:     # 次间
            offset = floorData.y_1 / 2 + floorData.y_2
            net_y.append(offset)
            net_y.insert(0, -offset)  
        if y_rooms >= 5:     # 梢间
            offset = floorData.y_1 / 2 + floorData.y_2 \
                    + floorData.y_3
            net_y.append(offset)
            net_y.insert(0, -offset) 
    else:   #偶数间
        if y_rooms >= 2:
            net_y.append(0)
            offset = floorData.y_1
            net_y.append(offset)
            net_y.insert(0,-offset)
        if y_rooms >= 4:
            offset = floorData.y_1 + floorData.y_2
            net_y.append(offset)
            net_y.insert(0,-offset)
    
    # 保存通面阔计算结果，以便其他函数中复用
    floorData.x_total = net_x[-1]-net_x[0]
    # 保存通进深计算结果，以便其他函数中复用
    floorData.y_total = net_y[-1]-net_y[0]

    return net_x,net_y

# 根据柱网数组，排布柱子
# 1. 第一次按照模板生成，柱网下没有柱，一切从0开始；
# 2. 用户调整柱网的开间、进深，需要保持柱子的高、径、样式
# 3. 修改柱样式时，也会重排柱子
# 传入柱网节点，柱子样板节点（最后会被删除）
def redraw_floor(self,context:bpy.types.Context,
                floorObj:bpy.types.Object):
    # 0、数据初始化（常量、场景参数、对象参数）
    # 0.1、载入常量列表
    con = const.ACA_Consts
    # 0.3、从当前场景中载入数据集
    floorData : data.ACA_data_obj = floorObj.ACA_data
    piller_source = floorData.piller_source
    piller_height = floorData.piller_height
    piller_R = floorData.piller_diameter /2
  
    # 1、未关联柱样式，按照const模板生成默认柱子
    if piller_source == None:
        piller_name = "基本立柱"
        if piller_height == 0:
            piller_height = con.PILLER_HEIGHT      # 柱高
        if piller_R == 0:
            piller_R = con.PILLER_D/2       # 柱径
        # 默认创建简单柱子
        piller_basemesh = utils.addCylinder(radius=piller_R,
                depth=piller_height,
                location=(0, 0, 0),
                name=piller_name,
                root_obj=floorObj,  # 挂接在柱网节点下
                origin_at_bottom = True,    # 将origin放在底部
            )
        piller_basemesh.ACA_data['aca_type'] = con.ACA_TYPE_PILLER
    else:
        # 已设置柱样式，复制一份临时模板
        piller_basemesh:bpy.types.Object = utils.ObjectCopy(
            sourceObj=piller_source,
            name=piller_source.name,
            parentObj=floorObj,
        )
        piller_basemesh.dimensions = (
            floorData.piller_diameter,
            floorData.piller_diameter,
            floorData.piller_height
        )
        utils.ApplyScale(piller_basemesh)
        piller_basemesh.ACA_data['aca_obj'] = True
        piller_basemesh.ACA_data['aca_type'] = con.ACA_TYPE_PILLER
    
    # 2、循环生成
    x_rooms = floorData.x_rooms   # 面阔几间
    y_rooms = floorData.y_rooms   # 进深几间
    net_x,net_y = get_floor_date(self,context,floorObj)
    for y in range(y_rooms + 1):
        for x in range(x_rooms + 1):
            # 统一命名为“柱.x/y”，以免更换不同柱时，柱网中的名称无法匹配
            piller_copy_name = "柱" + \
                '.' + str(x) + '/' + str(y)
            
            # 验证是否已被用户手工减柱
            piller_list_str = floorData.piller_net
            if piller_copy_name not in floorData.piller_net \
                    and piller_list_str != "" :
                # print("PP: piller skiped " + piller_copy_name)
                continue
            
            piller_loc = (net_x[x],net_y[y],piller_basemesh.location.z)
            # 复制柱子，仅instance，包含modifier
            piller_copy = utils.ObjectCopy(
                sourceObj = piller_basemesh,
                name = piller_copy_name,
                location=piller_loc,
                parentObj = floorObj
            )
            
            # 复制柱础
            pillerbaseObj = floorData.piller_base_source
            if pillerbaseObj != None:
                pillerbase_copy = utils.ObjectCopy(
                    sourceObj = pillerbaseObj,
                    name = '柱础',
                    parentObj = piller_copy
                )
                # 设置为不可选中
                pillerbase_copy.hide_select = True
    
    # 清理临时柱子
    bpy.data.objects.remove(piller_basemesh)

    # 重新聚焦回柱子
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = piller_copy
    piller_copy.select_set(True)

    # 调整柱网指示框尺寸
    floorObj.empty_display_size = (net_x[-1]-net_x[0]+1)/2

    print("ACA: Pillers added")

# 根据固定模板，创建柱网
# 被ACA_OT_add_newbuilding类调用
def add_floor(self,context:bpy.types.Context,
                  buildingObj:bpy.types.Object):
    # 0、数据初始化（常量、场景参数、对象参数）
    # 载入常量列表
    con = const.ACA_Consts

    # 1、创建根对象（empty）===========================================================
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    floorObj = context.object
    floorObj.empty_display_type = 'CUBE'
    floorObj.name = "地盘"
    floorObj.parent = buildingObj  # 挂接在对应建筑节点下
    #与台基顶面对齐
    root_z = con.PLATFORM_HEIGHT    # 柱网从台基顶部开始
    floorObj.location = (0,0,root_z)
    floorObj.ACA_data.aca_obj = True
    floorObj.ACA_data.aca_type = con.ACA_TYPE_FLOOR
    
    # 排列柱网
    redraw_floor(self,context,floorObj)

    print("ACA: Floor added")

# 根据用户在插件面板调整的柱网参数，更新柱网外观
# 绑定于data.py中objdata属性中触发的回调
def update_floor(self,context:bpy.types.Context):
    # 0.1、载入常量列表
    con = const.ACA_Consts
    
    # 1、数据准备,获取层次节点
    floorObj = context.object

    # 2、重布柱子
    # 删除所有柱子和柱础
    for piller in floorObj.children:
        for pillerbaseObj in piller.children:
            bpy.data.objects.remove(pillerbaseObj)
        bpy.data.objects.remove(piller)
    # 重新排布所有柱子
    redraw_floor(self,context,floorObj)
    
    # 3、更新台基
    pf_obj = utils.getAcaSibling(floorObj,con.ACA_TYPE_PLATFORM)
    bpy.context.view_layer.objects.active = pf_obj
    update_platform(self,context)
    
    # 4、如果原始选择的是柱网节点，重新聚焦回柱网
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = floorObj
    floorObj.select_set(True)

    print("ACA: Floor updated")

# 根据用户在插件面板修改的柱高、柱径，缩放柱子外观
# 绑定于data.py中objdata属性中触发的回调
def update_pillers_size(self,context:bpy.types.Context):
    # 根据的修改，批量调整柱对象的尺寸
    pillerObj = context.object
    floorData = pillerObj.parent.ACA_data
    # 垂直缩放
    piller_h_scale = (
            floorData.piller_height 
            / pillerObj.dimensions.z
        )
    # 垂直位移
    piller_z_offset = (
            floorData.piller_height 
            - pillerObj.dimensions.z
        )/2
    # 平面缩放
    piller_d_scale = (
            floorData.piller_diameter
            / pillerObj.dimensions.x
        )
    
    # 所有柱子为同一个mesh，只需要在edit mode中修改，即可全部生效
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.mesh.select_all(action = 'SELECT')
    bpy.ops.transform.resize(value=(piller_d_scale, piller_d_scale, piller_h_scale))
    bpy.ops.transform.translate(value=(0,0,piller_z_offset))
    bpy.ops.object.mode_set(mode = 'OBJECT')

    # 同步更新每根柱子的属性值
    pillernet = pillerObj.parent
    for piller in pillernet.children:
        piller.ACA_data['piller_height'] = pillerObj.ACA_data.piller_height
        piller.ACA_data['piller_diameter'] = pillerObj.ACA_data.piller_diameter

    print("ACA: Piller size updated")

# 更换柱样式
# 用户在panel上存在绑定一个对应的对象
def update_pillers_style(self,context:bpy.types.Context):
    con = const.ACA_Consts
    pillerObj = context.object
    floorObj = pillerObj.parent

    # 清除柱网下的所有柱子
    for piller in floorObj.children:
        # 清除柱下的柱础
        for child in piller.children:
            bpy.data.objects.remove(child)
        bpy.data.objects.remove(piller)

    # 重新排布所有柱子 
    redraw_floor(self,context,floorObj)

    print("ACA: Piller style updated")

def update_piller_base_style(self,context:bpy.types.Context):
    # 1定位到“ACA”根collection
    # 测试过程中，出现过目录失焦，导致柱础对象绑定到了根目录下
    con= const.ACA_Consts
    utils.setCollection(context, con.ROOT_COLL_NAME)
    
    # 当前选中的柱子对象
    pillerObj = context.object
    floorObj = pillerObj.parent
    floorData = floorObj.ACA_data
    
    # 循环柱网下的每根柱子对象，绑定柱础子对象
    floorObj = pillerObj.parent
    for piller in floorObj.children:
        # 删除老的柱础
        for obj in piller.children:
            bpy.data.objects.remove(obj)
        # 绑定新的柱础
        pillerbase_sourceObj =  floorData.piller_base_source
        if pillerbase_sourceObj != None:
            pillerbaseCopy = utils.ObjectCopy(
                sourceObj=pillerbase_sourceObj,
                name='柱础',
                parentObj=piller,
            )
            pillerbaseCopy.ACA_data['aca_obj'] = True
            pillerbaseCopy.ACA_data['aca_type'] = con.ACA_TYPE_PILLERBASE
            # 设置为不可选中
            pillerbaseCopy.hide_select = True
    
    # 重新聚焦回柱子
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = pillerObj
    pillerObj.select_set(True)

    print("ACA: Piller-base added")

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
        buildingObj = add_building_root(self,context)

        # 3.根据模板，自动创建建筑
        # 3.2 生成柱网
        add_floor(self,context,buildingObj)

        # 3.1 生成台基
        add_platform(self,context,buildingObj)        

        # 3.3 

        return {'FINISHED'}