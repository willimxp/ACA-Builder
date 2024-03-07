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
from .const import ACA_Consts as con
from . import utils
from . import const
from . import buildwall
from functools import partial

# 将模版参数填充入根节点的设计参数中
def setTemplateData(buildingObj:bpy.types.Object,
                    template:const.ACA_template):
    # 映射template对象到ACA_data中
    buildingData = buildingObj.ACA_data
    buildingData['aca_obj'] = True
    buildingData['aca_type'] = con.ACA_TYPE_BUILDING
    buildingData['template'] = template.NAME
    buildingData['DK'] = template.DK
    buildingData['platform_height'] = template.PLATFORM_HEIGHT
    buildingData['platform_extend'] = template.PLATFORM_EXTEND
    buildingData['x_rooms'] = template.ROOM_X
    buildingData['x_1'] = template.ROOM_X1
    buildingData['x_2'] = template.ROOM_X2
    buildingData['x_3'] = template.ROOM_X3
    buildingData['x_4'] = template.ROOM_X4
    buildingData['y_rooms'] = template.ROOM_Y
    buildingData['y_1'] = template.ROOM_Y1
    buildingData['y_2'] = template.ROOM_Y2
    buildingData['y_3'] = template.ROOM_Y3
    buildingData['piller_height'] = template.PILLER_HEIGHT
    buildingData['piller_diameter'] = template.PILLER_D 

# 根据panel中DK的改变，更新整体设计参数
def setTemplateByDK(dk,buildingObj:bpy.types.Object):
    # 载入模版
    template_name = bpy.context.scene.ACA_data.template
    # 根据DK数据，重新计算模版参数
    template = const.ACA_template(template_name,dk)

    # 在根节点绑定模版数据
    setTemplateData(buildingObj,template)
    

# 添加建筑empty根节点，并绑定设计模版
# 返回建筑empty根节点对象
# 被ACA_OT_add_newbuilding类调用
def addBuildingRoot():
    # 获取panel上选择的模版
    template_name = bpy.context.scene.ACA_data.template
    
    # 创建根节点empty
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    buildingObj = bpy.context.object
    buildingObj.location = bpy.context.scene.cursor.location   # 原点摆放在3D Cursor位置
    buildingObj.name = template_name   # 系统遇到重名会自动添加00x的后缀       
    buildingObj.empty_display_type = 'SPHERE'

    # 在根节点绑定模版数据
    template = const.ACA_template(template_name)
    setTemplateData(buildingObj,template)
    
    print("ACA: Building Root added")
    return buildingObj

# 根据固定模板，创建新的台基
def buildPlatform(buildingObj:bpy.types.Object):
    buildingData : data.ACA_data_obj = buildingObj.ACA_data

    # 1、创建地基===========================================================
    # 如果已有，先删除
    pfObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_PLATFORM)
    if pfObj != None:
        utils.delete_hierarchy(pfObj,with_parent=True)

    # 载入模板配置
    platform_height = buildingObj.ACA_data.platform_height
    platform_extend = buildingObj.ACA_data.platform_extend
    # 构造cube三维
    height = platform_height
    width = platform_extend * 2 + buildingData.x_total
    length = platform_extend * 2 + buildingData.y_total
    bpy.ops.mesh.primitive_cube_add(
                size=1.0, 
                calc_uvs=True, 
                enter_editmode=False, 
                align='WORLD', 
                location = (0,0,height/2), 
                scale=(width,length,height))
    pfObj = bpy.context.object
    pfObj.parent = buildingObj
    pfObj.name = con.PLATFORM_NAME
    # 设置插件属性
    pfObj.ACA_data['aca_obj'] = True
    pfObj.ACA_data['aca_type'] = con.ACA_TYPE_PLATFORM

    # 默认锁定对象的位置、旋转、缩放（用户可自行解锁）
    pfObj.lock_location = (True,True,True)
    pfObj.lock_rotation = (True,True,True)
    pfObj.lock_scale = (True,True,True)

     # 更新建筑框大小
    buildingObj.empty_display_size = math.sqrt(
            pfObj.dimensions.x * pfObj.dimensions.x
            + pfObj.dimensions.y * pfObj.dimensions.y
        ) / 2
    
    print("ACA: Platform added")

# 根据插件面板的台基高度、下出等参数变化，更新台基外观
# 绑定于data.py中update_platform回调
def resizePlatform(buildingObj:bpy.types.Object):
    # 载入根节点中的设计参数
    buildingData : data.ACA_data_obj = buildingObj.ACA_data
    
    # 找到台基对象
    pfObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_PLATFORM)
    # 重绘
    pf_extend = buildingData.platform_extend
    # 缩放台基尺寸
    pfObj.dimensions= (
        pf_extend * 2 + buildingData.x_total,
        pf_extend * 2 + buildingData.y_total,
        buildingData.platform_height
    )
    # 应用缩放(有时ops.object会乱跑，这里确保针对台基对象)
    utils.ApplyScale(pfObj)
    # 平移，保持台基下沿在地平线高度
    pfObj.location.z = buildingData.platform_height /2

    # 对齐柱网
    floorObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_FLOOR)
    floorObj.location.z =  buildingData.platform_height

    # 更新建筑框大小
    buildingObj.empty_display_size = math.sqrt(
            pfObj.dimensions.x * pfObj.dimensions.x
            + pfObj.dimensions.y * pfObj.dimensions.y
        ) / 2
    
    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)
    print("ACA: Platform updated")

# 准备柱网数据
# 将panel中设置的面宽、进深，组合成柱网数组
# 返回net_x[],net_y[]数组
def getFloorDate(buildingObj:bpy.types.Object):
    # 载入设计参数
    buildingData : data.ACA_data_obj = buildingObj.ACA_data

    # 构造柱网X坐标序列，罗列了1，3，5，7，9，11间的情况，未能抽象成通用公式
    x_rooms = buildingData.x_rooms   # 面阔几间
    y_rooms = buildingData.y_rooms   # 进深几间

    net_x = []  # 重新计算
    if x_rooms >=1:     # 明间
        offset = buildingData.x_1 / 2
        net_x.append(offset)
        net_x.insert(0, -offset)
    if x_rooms >=3:     # 次间
        offset = buildingData.x_1 / 2 + buildingData.x_2
        net_x.append(offset)
        net_x.insert(0, -offset)  
    if x_rooms >=5:     # 梢间
        offset = buildingData.x_1 / 2 + buildingData.x_2 \
                + buildingData.x_3
        net_x.append(offset)
        net_x.insert(0, -offset)  
    if x_rooms >=7:     # 尽间
        offset = buildingData.x_1 / 2 + buildingData.x_2 \
            + buildingData.x_3 + buildingData.x_4
        net_x.append(offset)
        net_x.insert(0, -offset)  
    if x_rooms >=9:     #更多梢间
        offset = buildingData.x_1 / 2 + buildingData.x_2 \
            + buildingData.x_3 * 2
        net_x[-1] = offset
        net_x[0]= -offset  
        offset = buildingData.x_1 / 2 + buildingData.x_2 \
            + buildingData.x_3 *2 + buildingData.x_4
        net_x.append(offset)
        net_x.insert(0, -offset) 
    if x_rooms >=11:     #更多梢间
        offset = buildingData.x_1 / 2 + buildingData.x_2 \
            + buildingData.x_3 * 3
        net_x[-1] = offset
        net_x[0]= -offset  
        offset = buildingData.x_1 / 2 + buildingData.x_2 \
            + buildingData.x_3 *3 + buildingData.x_4
        net_x.append(offset)
        net_x.insert(0, -offset) 

    # 构造柱网Y坐标序列，罗列了1-5间的情况，未能抽象成通用公式
    net_y=[]    # 重新计算
    if y_rooms%2 == 1: # 奇数间
        if y_rooms >= 1:     # 明间
            offset = buildingData.y_1 / 2
            net_y.append(offset)
            net_y.insert(0, -offset)
        if y_rooms >= 3:     # 次间
            offset = buildingData.y_1 / 2 + buildingData.y_2
            net_y.append(offset)
            net_y.insert(0, -offset)  
        if y_rooms >= 5:     # 梢间
            offset = buildingData.y_1 / 2 + buildingData.y_2 \
                    + buildingData.y_3
            net_y.append(offset)
            net_y.insert(0, -offset) 
    else:   #偶数间
        if y_rooms >= 2:
            net_y.append(0)
            offset = buildingData.y_1
            net_y.append(offset)
            net_y.insert(0,-offset)
        if y_rooms >= 4:
            offset = buildingData.y_1 + buildingData.y_2
            net_y.append(offset)
            net_y.insert(0,-offset)
    
    # 保存通面阔计算结果，以便其他函数中复用
    buildingData.x_total = net_x[-1]-net_x[0]
    # 保存通进深计算结果，以便其他函数中复用
    buildingData.y_total = net_y[-1]-net_y[0]

    return net_x,net_y

# 根据柱网数组，排布柱子
# 1. 第一次按照模板生成，柱网下没有柱，一切从0开始；
# 2. 用户调整柱网的开间、进深，需要保持柱子的高、径、样式
# 3. 修改柱样式时，也会重排柱子
# 建筑根节点（内带设计参数集）
def buildFloor(buildingObj:bpy.types.Object):
    # 解决bug：面阔间数在鼠标拖拽时可能为偶数，出现异常
    if buildingObj.ACA_data.x_rooms % 2 == 0:
        # 不处理偶数面阔间数
        utils.ShowMessageBox("面阔间数不能为偶数","ERROR")
        return
    
    # 1、查找或新建地盘根节点
    floorObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_FLOOR)
    if floorObj == None:        
        # 创建新地盘对象（empty）===========================================================
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        floorObj = context.object
        floorObj.name = "地盘"
        floorObj.parent = buildingObj  # 挂接在对应建筑节点下
        floorObj.ACA_data['aca_obj'] = True
        floorObj.ACA_data['aca_type'] = con.ACA_TYPE_FLOOR
        #与台基顶面对齐
        floor_z = buildingObj.ACA_data.platform_height
        floorObj.location = (0,0,floor_z)
    else:
        # 清空地盘下所有的柱子、柱础
        utils.delete_hierarchy(floorObj)

    # 2、生成一个柱子实例piller_basemesh
    # 从当前场景中载入数据集
    buildingData : data.ACA_data_obj = buildingObj.ACA_data
    piller_source = buildingData.piller_source
    piller_height = buildingData.piller_height
    piller_R = buildingData.piller_diameter /2
    if piller_source == None:
        # 默认创建简单柱子
        piller_basemesh = utils.addCylinder(radius=piller_R,
                depth=piller_height,
                location=(0, 0, 0),
                name="基本立柱",
                root_obj=floorObj,  # 挂接在柱网节点下
                origin_at_bottom = True,    # 将origin放在底部
            )
    else:
        # 已设置柱样式，根据设计参数实例化
        piller_basemesh:bpy.types.Object = utils.copyObject(
            sourceObj=piller_source,
            name=piller_source.name,
            parentObj=floorObj,
        )
        piller_basemesh.dimensions = (
            buildingData.piller_diameter,
            buildingData.piller_diameter,
            buildingData.piller_height
        )
        #utils.ApplyScale(piller_basemesh) # 此时mesh已经与source piller解绑，生成了新的mesh
    # 柱子属性
    piller_basemesh.ACA_data['aca_obj'] = True
    piller_basemesh.ACA_data['aca_type'] = con.ACA_TYPE_PILLER
    
    # 3、根据地盘数据，循环排布每根柱子
    x_rooms = buildingData.x_rooms   # 面阔几间
    y_rooms = buildingData.y_rooms   # 进深几间
    net_x,net_y = getFloorDate(buildingObj)
    for y in range(y_rooms + 1):
        for x in range(x_rooms + 1):
            # 统一命名为“柱.x/y”，以免更换不同柱形时，减柱设置失效
            piller_copy_name = "柱" + \
                '.' + str(x) + '/' + str(y)
            
            # 减柱验证
            piller_list_str = buildingData.piller_net
            if piller_copy_name not in piller_list_str \
                    and piller_list_str != "" :
                # print("PP: piller skiped " + piller_copy_name)
                continue    # 结束本次循环
            
            # 复制柱子，仅instance，包含modifier
            piller_loc = (net_x[x],net_y[y],piller_basemesh.location.z)
            piller_copy = utils.copyObject(
                sourceObj = piller_basemesh,
                name = piller_copy_name,
                location=piller_loc,
                parentObj = floorObj
            )   

    # 清理临时柱子
    utils.delete_hierarchy(piller_basemesh,True)

    print("ACA: Pillers rebuilt")

# 根据用户在插件面板修改的柱高、柱径，缩放柱子外观
# 绑定于data.py中objdata属性中触发的回调
def resizePiller(buildingObj:bpy.types.Object):
    # 获取一个现有的柱子实例，做为缩放的依据
    pillerObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_PILLER)
    
    buildingData = buildingObj.ACA_data
    # 平面缩放
    piller_d_scale = (
            buildingData.piller_diameter
            / pillerObj.dimensions.x
        )
    # 垂直缩放
    piller_h_scale = (
            buildingData.piller_height 
            / pillerObj.dimensions.z
        )
    
    floorObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_FLOOR)
    if len(floorObj.children) >0 :
        for piller in floorObj.children:
            piller.scale = piller.scale * \
                Vector((piller_d_scale,
                        piller_d_scale,
                        piller_h_scale))

    # # 所有柱子为同一个mesh，只需要在edit mode中修改，即可全部生效
    # # bug: 未指定变形中心，导致异常
    # utils.focusObj(pillerObj)
    # bpy.ops.object.mode_set(mode = 'EDIT')
    # bpy.ops.mesh.select_all(action = 'SELECT')
    # bpy.ops.transform.resize(
    #     value=(piller_d_scale, piller_d_scale, piller_h_scale))
    # bpy.ops.transform.translate(value=(0,0,piller_z_offset))
    # bpy.ops.object.mode_set(mode = 'OBJECT')

    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)
    print("ACA: Piller updated")

# 执行营造整体过程
# 输入buildingObj，自带设计参数集，且做为其他构件绑定的父节点
# 采用了偏函数和fastrun，极大加速了性能
def buildAll(buildingObj:bpy.types.Object):
    # # 普通调用模式=============
    # # 生成柱网
    # buildFloor(buildingObj)
    # # 生成台基
    # buildPlatform(buildingObj)
    # # 生成墙体框线
    # wallBuilder = buildwall.wallBuilder()
    # wallBuilder.buildWallLayout(buildingObj)

    # 提高性能模式============
    # https://blender.stackexchange.com/questions/7358/python-performance-with-blender-operators
    # 生成柱网
    funproxy = partial(buildFloor,buildingObj=buildingObj)
    utils.fastRun(funproxy)
    # 生成台基
    funproxy = partial(buildPlatform,buildingObj=buildingObj)
    utils.fastRun(funproxy)
    # 生成墙体
    wallBuilder = buildwall.wallBuilder()
    funproxy = partial(wallBuilder.buildWallLayout,buildingObj=buildingObj)
    utils.fastRun(funproxy)

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
        # 1.定位到“ACA”根collection，如果没有则新建
        utils.setCollection(context, con.ROOT_COLL_NAME)

        # 2.添加建筑empty
        # 其中绑定了模版数据
        buildingObj = addBuildingRoot()

        # 3.调用营造序列
        buildAll(self,context,buildingObj) 

        # 聚焦到建筑根节点
        utils.focusObj(buildingObj)
        return {'FINISHED'}

# 批量生成墙体布局，及所有墙体
class ACA_OT_build_wall_layout(bpy.types.Operator):
    bl_idname="aca.build_wall_layout"
    bl_label = "墙体营造"

    def execute(self, context):  
        buildingObj = context.object
        bData:data.ACA_data_obj = buildingObj.ACA_data
        if bData.aca_type != con.ACA_TYPE_BUILDING:
            utils.ShowMessageBox("ERROR: 找不到建筑")
        else:
            # 生成墙体框线
            wallbuilder = buildwall.wallBuilder()
            wallbuilder.buildWallLayout(buildingObj)
        return {'FINISHED'}

# 单独生成一个墙体
class ACA_OT_build_wall_single(bpy.types.Operator):
    bl_idname="aca.build_wall_single"
    bl_label = "墙体营造"

    def execute(self, context):  
        wallproxy = context.object
        wData:data.ACA_data_obj = wallproxy.ACA_data
        if wData.aca_type != con.ACA_TYPE_WALL:
            utils.ShowMessageBox("ERROR: 找不到建筑")
        else:
            # 生成墙体框线
            wallbuilder = buildwall.wallBuilder()
            wallbuilder.buildSingleWall(wallproxy)
        return {'FINISHED'}
    
# 生成柱间隔扇
class ACA_OT_build_door(bpy.types.Operator):
    bl_idname="aca.build_door"
    bl_label = "墙体营造"

    # 构建扇心
    # 包括在槛框中嵌入的横披窗扇心
    # 也包括在隔扇中嵌入的隔扇扇心
    def buildShanxin(self,context,parent,scale:Vector,location:Vector):
        # parent在横披窗中传入的wallproxy，但在隔扇中传入的geshanroot，所以需要重新定位
        # 载入数据
        buildingObj = utils.getAcaParent(parent,con.ACA_TYPE_BUILDING)
        wallproxy = utils.getAcaChild(buildingObj,con.ACA_TYPE_WALL)
        bData:data.ACA_data_obj = buildingObj.ACA_data
        wData:data.ACA_data_obj = wallproxy.ACA_data
        # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
        # todo：是采用用户可调整的设计值，还是取模版中定义的理论值？
        dk = bData.DK
        pd = con.PILLER_D_EAVE * dk

        # 仔边环绕
        # 创建一个平面，转换为curve，设置curve的横截面
        bpy.ops.mesh.primitive_plane_add(size=1,location=location)
        zibianObj = bpy.context.object
        zibianObj.name = '仔边'
        zibianObj.parent = parent
        # 三维的scale转为plane二维的scale
        zibianObj.rotation_euler.x = math.radians(90)
        zibianObj.scale = (
            scale.x - con.ZIBIAN_WIDTH*pd,
            scale.z - con.ZIBIAN_WIDTH*pd, # 旋转90度，原Zscale给Yscale
            0)
        # apply scale
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        # 转换为Curve
        bpy.ops.object.convert(target='CURVE')
        # 旋转所有的点45度，形成四边形
        bpy.ops.object.editmode_toggle()
        bpy.ops.curve.select_all(action='SELECT')
        bpy.ops.transform.tilt(value=math.radians(45))
        bpy.ops.object.editmode_toggle()
        # 设置Bevel
        zibianObj.data.bevel_mode = 'PROFILE'        
        zibianObj.data.bevel_depth = con.ZIBIAN_WIDTH/2  # 仔边宽度

        # 填充棂心
        lingxinObj = wData.lingxin_source
        if lingxinObj == None: return
        # 定位：从左下角排布array
        loc = (location.x-scale.x/2+con.ZIBIAN_WIDTH*pd,
               location.y,
               location.z-scale.z/2+con.ZIBIAN_WIDTH*pd)
        lingxin = utils.copyObject(
            sourceObj=lingxinObj,
            name='棂心',
            parentObj=parent,
            location=loc)
        # 计算平铺的行列数
        unitWidth,unitDeepth,unitHeight = utils.getMeshDims(lingxin)
        lingxingWidth = scale.x- con.ZIBIAN_WIDTH*2*pd
        linxingHeight = scale.z- con.ZIBIAN_WIDTH*2*pd
        rows = math.ceil(linxingHeight/unitHeight)+1 #加一，尽量让棂心紧凑，避免出现割裂
        row_span = linxingHeight/rows
        mod_rows = lingxin.modifiers.get('Rows')
        mod_rows.count = rows
        mod_rows.constant_offset_displace[2] = row_span

        cols = math.ceil(lingxingWidth/unitWidth)+1#加一，尽量让棂心紧凑，避免出现割裂
        col_span = lingxingWidth/cols
        mod_cols = lingxin.modifiers.get('Columns')
        mod_cols.count = cols
        mod_cols.constant_offset_displace[0] = col_span

    # 构建槛框
    # 基于输入的槛框线框对象
    def buildKanKuang(self,context,wallproxy):
        # 载入数据
        buildingObj = utils.getAcaParent(wallproxy,con.ACA_TYPE_BUILDING)
        bData:data.ACA_data_obj = buildingObj.ACA_data
        wData:data.ACA_data_obj = wallproxy.ACA_data
        # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
        # todo：是采用用户可调整的设计值，还是取模版中定义的理论值？
        dk = bData.DK
        pd = con.PILLER_D_EAVE * dk
        is_with_wall = wData.is_with_wall
        pillerD = bData.piller_diameter
        # 分解槛框的长、宽、高
        frame_width,frame_deepth,frame_height = wallproxy.dimensions

        # region 1、下槛 ---------------------
        KanDownScale = Vector((frame_width, # 长度随面宽
                    con.KAN_DOWN_DEEPTH * pd, # 厚0.3D
                    con.KAN_DOWN_HEIGHT * pd, # 高0.8D
                    ))
        KanDownLoc = Vector((0,0,con.KAN_DOWN_HEIGHT*pd/2))
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = KanDownLoc, 
                            scale= KanDownScale)
        KanDownObj = context.object
        KanDownObj.name = '下槛'
        KanDownObj.parent = wallproxy
        if is_with_wall:
            KanDownObj.hide_set(True) 
        # endregion 1、下槛 ---------------------
            
        # region 2、上槛 ---------------------
        KanUpScale = Vector((frame_width, # 长度随面宽
                    con.KAN_UP_DEEPTH * pd, # 厚0.3D
                    con.KAN_UP_HEIGHT * pd, # 高0.8D
                    ))
        KanUpLoc = Vector((0,0,
                frame_height - con.KAN_UP_HEIGHT*pd/2))
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = KanUpLoc, 
                            scale= KanUpScale)
        context.object.name = '上槛'
        context.object.parent = wallproxy
        # endregion 2、上槛 ---------------------

        # region 3、中槛 ---------------------
        KanMidScale = Vector((frame_width, # 长度随面宽
                    con.KAN_MID_DEEPTH * pd, # 厚0.3D
                    con.KAN_MID_HEIGHT * pd, # 高0.8D
                    ))
        KanMidLoc = Vector((0,0,
                wData.door_height + con.KAN_MID_HEIGHT*pd/2))
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = KanMidLoc, 
                            scale= KanMidScale)
        context.object.name = '中槛'
        context.object.parent = wallproxy
        # endregion 3、中槛 ---------------------

        # region 4、下抱框 ---------------------
        # 高度：从下槛上皮到中槛下皮
        BaoKuangDownHeight = (KanMidLoc.z - KanMidScale.z/2) \
            - (KanDownLoc.z + KanDownScale.z/2)
        BaoKuangDownScale = Vector((
                    con.BAOKUANG_WIDTH * pd, # 宽0.66D
                    con.BAOKUANG_DEEPTH * pd, # 厚0.3D
                    BaoKuangDownHeight, 
                    ))
        # 位置Z：从下槛+一半高度
        BaoKuangDown_z = (KanDownLoc.z + KanDownScale.z/2) \
                            + BaoKuangDownHeight/2
        # 位置X：半柱间距 - 半柱径 - 半抱框宽度
        BaoKuangDown_x = frame_width/2 - pillerD/2 - con.BAOKUANG_WIDTH*pd/2
        BaoKuangDownLoc = Vector((BaoKuangDown_x,0,BaoKuangDown_z))
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = BaoKuangDownLoc, 
                            scale= BaoKuangDownScale)
        BaoKuangDownObj = context.object
        BaoKuangDownObj.name = '下抱框'
        BaoKuangDownObj.parent = wallproxy
        # 添加mirror
        mod = BaoKuangDownObj.modifiers.new(name='mirror', type='MIRROR')
        mod.use_axis[0] = True
        mod.use_axis[1] = False
        mod.mirror_object = wallproxy
        # endregion 4、下抱框 ---------------------

        # region 5、上抱框 ---------------------
        # 高度：从上槛下皮到中槛上皮
        BaoKuangUpHeight = (KanUpLoc.z - KanUpScale.z/2) \
            - (KanMidLoc.z + KanMidScale.z/2)
        BaoKuangUpScale = Vector((
                    con.BAOKUANG_WIDTH * pd, # 宽0.66D
                    con.BAOKUANG_DEEPTH * pd, # 厚0.3D
                    BaoKuangUpHeight, 
                    ))
        # 位置Z：从上槛下皮，减一半高度
        BaoKuangUp_z = (KanUpLoc.z - KanUpScale.z/2) \
                            - BaoKuangUpHeight/2
        # 位置X：半柱间距 - 半柱径 - 半抱框宽度
        BaoKuangUp_x = frame_width/2 - pillerD/2 - con.BAOKUANG_WIDTH*pd/2
        BaoKuangUpLoc = Vector((BaoKuangUp_x,0,BaoKuangUp_z))
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = BaoKuangUpLoc, 
                            scale= BaoKuangUpScale)
        BaoKuangUpObj  = context.object
        BaoKuangUpObj.name = '上抱框'
        BaoKuangUpObj.parent = wallproxy
        # 添加mirror
        mod = BaoKuangUpObj.modifiers.new(name='mirror', type='MIRROR')
        mod.use_axis[0] = True
        mod.use_axis[1] = False
        mod.mirror_object = wallproxy
        # endregion 5、上抱框 ---------------------

        # region 6、横披窗 ---------------------
        # 横披窗数量：比隔扇少一扇
        window_top_num = wData.door_num - 1
        # 横披窗宽度:(柱间距-柱径-4抱框)/3
        window_top_width =  \
            (frame_width - pillerD - con.BAOKUANG_WIDTH*4*pd)/window_top_num
        # 循环生成每一扇横披窗
        for n in range(1,window_top_num):
            # 横披间框：右抱框中心 - n*横披窗间隔 - n*横披窗宽度
            windowTopKuang_x = BaoKuangUp_x - con.BAOKUANG_WIDTH*pd*n \
                - window_top_width * n
            windowTopKuangLoc = Vector((windowTopKuang_x,0,BaoKuangUp_z))
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = windowTopKuangLoc, 
                                scale= BaoKuangUpScale)
            context.object.name = '横披间框'
            context.object.parent = wallproxy

        # 横披窗尺寸
        WindowTopScale = Vector((window_top_width, # 宽度取横披窗宽度
                 con.ZIBIAN_DEEPTH,
                BaoKuangUpHeight # 高度与上抱框相同
        ))
        # 填充棂心
        for n in range(0,window_top_num):
            windowTop_x = BaoKuangUp_x - \
                (con.BAOKUANG_WIDTH*pd + window_top_width)*(n+0.5)
            WindowTopLoc =  Vector((windowTop_x,0,BaoKuangUp_z))
            self.buildShanxin(context,wallproxy,WindowTopScale,WindowTopLoc)

        # endregion 6、横披窗 ---------------------
        
        # 输出下抱框，做为隔扇生成的参考
        return BaoKuangDownObj

    # 构建隔扇
    # 采用故宫王璞子书的做法，马炳坚的做法不够协调
    def buildGeshan(self,name,context,wallproxy,scale,location):
        # 载入数据
        buildingObj = utils.getAcaParent(wallproxy,con.ACA_TYPE_BUILDING)
        bData:data.ACA_data_obj = buildingObj.ACA_data
        wData:data.ACA_data_obj = wallproxy.ACA_data
        # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
        # todo：是采用用户可调整的设计值，还是取模版中定义的理论值？
        dk = bData.DK
        pd = con.PILLER_D_EAVE * dk
        is_with_wall = wData.is_with_wall

        # 1.隔扇根对象
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        geshan_root:bpy.types.Object = context.object
        geshan_root.name = name
        geshan_root.location = location
        geshan_width,geshan_deepth,geshan_height = scale
        geshan_root.parent = wallproxy  # 绑定到外框父对象    

        # 2.边梃/抹头宽（看面）: 1/10隔扇宽（或1/5D）
        # border_width = geshan_width / 10
        border_width = con.BORDER_WIDTH * pd
        # 边梃/抹头厚(进深)：1.5倍宽或0.3D，这里直接取了抱框厚度
        # border_deepth = BAOKUANG_DEEPTH * pd
        border_deepth = con.BORDER_DEEPTH * pd
        # 边梃
        loc = (geshan_width/2-border_width/2,0,0)
        scale = (border_width,border_deepth,geshan_height)
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc, 
                            scale= scale)
        context.object.name = '边梃'
        context.object.parent = geshan_root
        # 添加mirror
        mod = context.object.modifiers.new(name='mirror', type='MIRROR')
        mod.use_axis[0] = True
        mod.mirror_object = geshan_root

        # 3.构件抹头
        # 抹头上下
        loc = (0,0,geshan_height/2-border_width/2)
        motou_width = geshan_width-border_width*2
        scale = (motou_width,border_deepth,border_width)
        bpy.ops.mesh.primitive_cube_add(
                            size=1.0, 
                            location = loc, 
                            scale= scale)
        context.object.name = '抹头.上下'
        context.object.parent = geshan_root
        if not is_with_wall:
            # 添加mirror
            mod = context.object.modifiers.new(name='mirror', type='MIRROR')
            mod.use_axis[0] = False
            mod.use_axis[2] = True
            mod.mirror_object = geshan_root

        # 4. 分割棂心、裙板、绦环板
        gap_num = wData.gap_num   # 门缝，与槛框留出一些距离
        windowsill_height = 0       # 窗台高度，在需要做槛墙的槛框中定位
        if gap_num == 2:
            # 满铺扇心
            heartHeight = geshan_height - border_width *2
            # 扇心：抹二上推半扇心
            loc1 = Vector((0,0,0))
            scale = Vector((motou_width,border_deepth,heartHeight))
            self.buildShanxin(context,geshan_root,scale,loc1)
        if gap_num == 3:
            # 三抹：扇心、裙板按6:4分
            # 隔扇心高度
            heartHeight = (geshan_height - border_width *3)*0.6
            loc2 = Vector((0,0,
                geshan_height/2-heartHeight-border_width*1.5))
            scale = Vector((motou_width,border_deepth,border_width))
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc2, 
                                scale= scale)
            context.object.name = '抹头.二'
            context.object.parent = geshan_root
            # 扇心：抹二上推半扇心
            loc8 = loc2+Vector((0,0,heartHeight/2+border_width/2))
            scale = Vector((motou_width,border_deepth,heartHeight))
            self.buildShanxin(context,geshan_root,scale,loc8)
            if is_with_wall:
                 # 计算窗台高度:抹二下皮
                windowsill_height = loc2.z - border_width/2
            else:
                # 裙板，抹二下方
                loc3 = loc2-Vector((0,0,heartHeight*2/6+border_width/2))
                scale = Vector((motou_width,border_deepth/3,heartHeight*4/6))
                bpy.ops.mesh.primitive_cube_add(
                                    size=1.0, 
                                    location = loc3, 
                                    scale= scale)
                context.object.name = '裙板'
                context.object.parent = geshan_root           
        if gap_num == 4:
            # 四抹：一块绦环板
            # 减去4根抹头厚+绦环板(2抹高)，扇心裙板6/4分
            heartHeight = (geshan_height - border_width*6)*0.6
            # 抹二
            loc2 = Vector((0,0,
                geshan_height/2-heartHeight-border_width*1.5))
            scale = (motou_width,border_deepth,border_width)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc2, 
                                scale= scale)
            context.object.name = '抹头.二'
            context.object.parent = geshan_root
            # 抹三
            loc3 = loc2 - Vector((0,0,border_width*3))
            scale = (motou_width,border_deepth,border_width)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc3, 
                                scale= scale)
            context.object.name = '抹头.三'
            context.object.parent = geshan_root
            # 绦环板
            loc4 = (loc2+loc3)/2
            scale = (motou_width,border_deepth/3,border_width*2)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc4, 
                                scale= scale)
            context.object.name = '绦环板'
            context.object.parent = geshan_root
            # 扇心：抹二上推半扇心
            loc8 = loc2+Vector((0,0,heartHeight/2+border_width/2))
            scale = Vector((motou_width,border_deepth,heartHeight))
            self.buildShanxin(context,geshan_root,scale,loc8)
            if is_with_wall:
                # 计算窗台高度:抹三下皮
                windowsill_height = loc3.z - border_width/2
            else:
                # 裙板，抹三下方
                loc5 = loc3-Vector((0,0,heartHeight*2/6+border_width/2))
                scale = (motou_width,border_deepth/3,heartHeight*4/6)
                bpy.ops.mesh.primitive_cube_add(
                                    size=1.0, 
                                    location = loc5, 
                                    scale= scale)
                context.object.name = '裙板'
                context.object.parent = geshan_root            
        if gap_num == 5:
            # 五抹：减去5根抹头厚+2绦环板(4抹高)，扇心裙板6/4分
            heartHeight = (geshan_height - border_width*9)*0.6
            # 抹二
            loc2 = Vector((0,0,
                geshan_height/2-heartHeight-border_width*1.5))
            scale = (motou_width,border_deepth,border_width)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc2, 
                                scale= scale)
            context.object.name = '抹头.二'
            context.object.parent = geshan_root
            # 抹三，抹二向下一块绦环板
            loc3 = loc2 - Vector((0,0,border_width*3))
            scale = (motou_width,border_deepth,border_width)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc3, 
                                scale= scale)
            context.object.name = '抹头.三'
            context.object.parent = geshan_root
            # 绦环板一
            loc5 = (loc2+loc3)/2
            scale = (motou_width,border_deepth/3,border_width*2)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc5, 
                                scale= scale)
            context.object.name = '绦环板一'
            context.object.parent = geshan_root
            # 扇心：抹二上推半扇心
            loc8 = loc2+Vector((0,0,heartHeight/2+border_width/2))
            scale = Vector((motou_width,border_deepth,heartHeight))
            self.buildShanxin(context,geshan_root,scale,loc8)
            if is_with_wall:
                # 计算窗台高度:抹三下皮
                windowsill_height = loc3.z - border_width/2
            else:
                # 抹四，底边向上一块绦环板
                loc4 = Vector((0,0,
                    -geshan_height/2+border_width*3.5))
                scale = (motou_width,border_deepth,border_width)
                bpy.ops.mesh.primitive_cube_add(
                                    size=1.0, 
                                    location = loc4, 
                                    scale= scale)
                context.object.name = '抹头.四'
                context.object.parent = geshan_root
                # 绦环板二
                loc6 = loc4 - Vector((0,0,border_width*1.5))
                scale = (motou_width,border_deepth/3,border_width*2)
                bpy.ops.mesh.primitive_cube_add(
                                    size=1.0, 
                                    location = loc6, 
                                    scale= scale)
                context.object.name = '绦环板二'
                context.object.parent = geshan_root
                # 裙板
                loc7 = (loc3+loc4)/2
                scale = (motou_width,border_deepth/3,heartHeight*4/6)
                bpy.ops.mesh.primitive_cube_add(
                                    size=1.0, 
                                    location = loc7, 
                                    scale= scale)
                context.object.name = '裙板'
                context.object.parent = geshan_root
        if gap_num == 6:
            # 六抹：减去6根抹头厚+3绦环板(6抹高)，扇心裙板6/4分
            heartHeight = (geshan_height-border_width*12)*0.6
            # 抹二，固定向下1.5抹+绦环板（2抹）
            loc2 = Vector((0,0,
                geshan_height/2-border_width*3.5))
            scale = (motou_width,border_deepth,border_width)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc2, 
                                scale= scale)
            context.object.name = '抹头.二'
            context.object.parent = geshan_root
            # 抹三, 向下一个扇心+抹头
            loc3 = loc2 - Vector((0,0,heartHeight+border_width))
            scale = (motou_width,border_deepth,border_width)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc3, 
                                scale= scale)
            context.object.name = '抹头.三'
            context.object.parent = geshan_root
            # 抹四，向下一块绦环板
            loc4 = loc3 - Vector((0,0,border_width*3))
            scale = (motou_width,border_deepth,border_width)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc4, 
                                scale= scale)
            context.object.name = '抹头.四'
            context.object.parent = geshan_root
            # 抹五，底边反推一绦环板
            loc5 = Vector((
                0,0,-geshan_height/2+border_width*3.5
            ))
            scale = (motou_width,border_deepth,border_width)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc5, 
                                scale= scale)
            context.object.name = '抹头.五'
            context.object.parent = geshan_root
            # 绦环板一，抹二反推
            loc6 = loc2+Vector((0,0,border_width*1.5))
            scale = (motou_width,border_deepth/3,border_width*2)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc6, 
                                scale= scale)
            context.object.name = '绦环板一'
            context.object.parent = geshan_root
            # 绦环板二，抹三抹四之间
            loc7 = (loc3+loc4)/2
            scale = (motou_width,border_deepth/3,border_width*2)
            bpy.ops.mesh.primitive_cube_add(
                                size=1.0, 
                                location = loc7, 
                                scale= scale)
            context.object.name = '绦环板二'
            context.object.parent = geshan_root
            
            # 扇心：抹二和抹三之间
            loc8 = (loc2+loc3)/2
            scale = Vector((motou_width,border_deepth,heartHeight))
            self.buildShanxin(context,geshan_root,scale,loc8)
            if is_with_wall:
                # 计算窗台高度:抹四下皮
                windowsill_height = loc4.z - border_width/2
            else:
                # 裙板，抹四抹五之间
                loc8 = (loc4+loc5)/2
                scale = (motou_width,border_deepth/3,heartHeight*4/6)
                bpy.ops.mesh.primitive_cube_add(
                                    size=1.0, 
                                    location = loc8, 
                                    scale= scale)
                context.object.name = '裙板'
                context.object.parent = geshan_root
                # 绦环板三，底边反推
                loc9 = Vector((0,0,-geshan_height/2+border_width*2))
                scale = (motou_width,border_deepth/3,border_width*2)
                bpy.ops.mesh.primitive_cube_add(
                                    size=1.0, 
                                    location = loc9, 
                                    scale= scale)
                context.object.name = '绦环板三'
                context.object.parent = geshan_root        
        return windowsill_height
        
    # 构建槛墙
    # 槛墙定位要与隔扇裙板上抹对齐，所以要根据隔扇的尺寸进行定位
    def buildKanqiang(self,context,
                      wallproxy:bpy.types.Object
                      ,dimension):
        # 载入数据
        buildingObj = utils.getAcaParent(wallproxy,con.ACA_TYPE_BUILDING)
        bData:data.ACA_data_obj = buildingObj.ACA_data
        wData:data.ACA_data_obj = wallproxy.ACA_data
        # 模数因子，采用柱径，这里采用的6斗口的理论值，与用户实际设置的柱径无关
        # todo：是采用用户可调整的设计值，还是取模版中定义的理论值？
        dk = bData.DK
        pd = con.PILLER_D_EAVE * dk
        is_with_wall = wData.is_with_wall

        # 风槛
        scl1 = Vector((
            dimension.x,
            con.KAN_WIND_DEEPTH*pd,
            con.KAN_WIND_HEIGHT*pd
        ))
        loc1 = Vector((
            0,0,dimension.z-scl1.z/2
        ))
        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=loc1,
            scale=scl1
        )
        kanWindObj = bpy.context.object
        kanWindObj.name = '风槛'
        kanWindObj.parent = wallproxy
        # 榻板
        scl2 = Vector((
            dimension.x+con.TABAN_EX,
            con.TABAN_DEEPTH*pd+con.TABAN_EX,
            con.TABAN_HEIGHT*pd
        ))
        loc2 = Vector((
            0,0,dimension.z-scl1.z-scl2.z/2
        ))
        kanWindObj:bpy.types.Object = utils.drawHexagon(scl2,loc2)
        kanWindObj = bpy.context.object
        kanWindObj.name = '榻板'
        kanWindObj.parent = wallproxy
        # 槛墙
        scl3 = Vector((
            dimension.x,
            con.TABAN_DEEPTH*pd,
            dimension.z-scl1.z-scl2.z
        ))
        loc3 = Vector((
            0,0,scl3.z/2
        ))
        kanqiangObj:bpy.types.Object = utils.drawHexagon(scl3,loc3)
        kanqiangObj.name = '槛墙'
        kanqiangObj.parent = wallproxy
        return
    
    # 构建完整的隔扇
    def buildDoor(self,context,wallproxy):       
        # 载入设计数据
        buildingObj = utils.getAcaParent(wallproxy,con.ACA_TYPE_BUILDING)
        bdata:data.ACA_data_obj = buildingObj.ACA_data
        wData:data.ACA_data_obj = wallproxy.ACA_data
        if bdata == None:
            utils.ShowMessageBox("无法读取设计数据","ERROR")
            return {'FINISHED'}
        elif bdata.aca_type != con.ACA_TYPE_BUILDING:
            utils.ShowMessageBox("未找到建筑根节点","ERROR")
            return {'FINISHED'}
        dk = bdata.DK
        pd = con.PILLER_D_EAVE * dk
        pillerD = bdata.piller_diameter
        # 分解槛框的长、宽、高
        frame_width,frame_deepth,frame_height = wallproxy.dimensions

        # 清理之前的子对象
        # utils.delete_hierarchy(wallproxy)
        # 聚焦在当前collection中
        utils.setCollection(context, con.ROOT_COLL_NAME)
        
        # 2、构建槛框，返回下抱框，做为隔扇生成的参考  
        BaoKuangDownObj = self.buildKanKuang(context,wallproxy)

        # 3、构建槛框内的每一扇隔扇
        # 隔扇数量
        geshan_num = wData.door_num
        geshan_total_width = frame_width - pillerD - con.BAOKUANG_WIDTH*pd*2
        # 每个隔扇宽度：抱框位置 / 隔扇数量
        geshan_width = geshan_total_width/geshan_num
        # 与下抱框等高，参考buildKankuang函数的返回对象
        geshan_height = BaoKuangDownObj.dimensions.z
        scale = Vector((geshan_width-con.GESHAN_GAP,
                 con.BAOKUANG_DEEPTH * pd,
                 geshan_height-con.GESHAN_GAP))
        for n in range(geshan_num):
            # 位置
            location = Vector((geshan_width*(geshan_num/2-n-0.5),   #向右半扇
                        0,
                        BaoKuangDownObj.location.z    #与抱框平齐
                        ))
            windowsill_height = self.buildGeshan(
                '隔扇',context,wallproxy,scale,location)

        # 4、添加槛墙
        is_with_wall = wData.is_with_wall
        if is_with_wall :
            # 窗台高度
            windowsill_z = windowsill_height + BaoKuangDownObj.location.z
            scale = Vector((
                wallproxy.dimensions.x,
                wallproxy.dimensions.y,
                windowsill_z
            ))
            # 添加槛墙
            self.buildKanqiang(context,wallproxy,scale)

        utils.focusObj(wallproxy)

    def execute(self, context): 
        wallproxy = context.object

        # 确认选择的对象必须是墙体线框
        if wallproxy.ACA_data.aca_type != con.ACA_TYPE_WALL:
            utils.ShowMessageBox("请选择一个隔扇线框","ERROR")
            return
        
        self.buildDoor(context,wallproxy)

        return {'FINISHED'}

