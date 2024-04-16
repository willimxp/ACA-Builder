# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   柱子的营造
import bpy
from mathutils import Vector
from functools import partial

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import utils
from . import buildWall
from . import buildPlatform
from . import buildDougong
from . import buildRoof
from . import buildRooftile

# 准备柱网数据
# 将panel中设置的面宽、进深，组合成柱网数组
# 返回net_x[],net_y[]数组
def getFloorDate(buildingObj:bpy.types.Object):
    # 载入设计参数
    buildingData:acaData = buildingObj.ACA_data

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
# 不涉及墙体重建，很快
def buildPillers(buildingObj:bpy.types.Object):
    # 解决bug：面阔间数在鼠标拖拽时可能为偶数，出现异常
    if buildingObj.ACA_data.x_rooms % 2 == 0:
        # 不处理偶数面阔间数
        utils.showMessageBox("面阔间数不能为偶数","ERROR")
        return
    
    # 1、查找或新建地盘根节点
    floorObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_FLOOR)
    if floorObj == None:        
        # 创建新地盘对象（empty）===========================================================
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        floorObj = bpy.context.object
        floorObj.name = "地盘"
        floorObj.parent = buildingObj  # 挂接在对应建筑节点下
        floorObj.ACA_data['aca_obj'] = True
        floorObj.ACA_data['aca_type'] = con.ACA_TYPE_FLOOR
        #与台基顶面对齐
        floor_z = buildingObj.ACA_data.platform_height
        floorObj.location = (0,0,floor_z)
    else:
        # 清空地盘下所有的柱子、柱础
        utils.deleteHierarchy(floorObj)

    # 2、生成一个柱子实例piller_basemesh
    # 从当前场景中载入数据集
    buildingData:acaData = buildingObj.ACA_data
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
        #utils.applyScale(piller_basemesh) # 此时mesh已经与source piller解绑，生成了新的mesh
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
                # utils.outputMsg("PP: piller skiped " + piller_copy_name)
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
    utils.deleteHierarchy(piller_basemesh,True)

# 根据用户在插件面板修改的柱高、柱径，缩放柱子外观
# 会自动触发墙体的重建，速度很慢
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

    # 柱高、柱径的变化，都会引起隔扇、墙体的变化，需要重建
    # 重新生成墙体
        funproxy = partial(buildWall.updateWallLayout,buildingObj=buildingObj)
        utils.fastRun(funproxy)

    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)
    utils.outputMsg("Piller resized")

# 执行营造整体过程
# 输入buildingObj，自带设计参数集，且做为其他构件绑定的父节点
# 采用了偏函数和fastrun，极大加速了性能
def buildFloor(buildingObj:bpy.types.Object):
    # 清理数据
    utils.outputMsg("Preparing...")
    utils.delOrphan()
    buildingColl = bpy.context.collection

    # 提高性能模式============
    # https://blender.stackexchange.com/questions/7358/python-performance-with-blender-operators
    # 生成柱网
    utils.outputMsg("Building Pillers...")
    utils.setCollection('柱网',parentColl=buildingColl)
    funproxy = partial(buildPillers,buildingObj=buildingObj)
    utils.fastRun(funproxy)
    
    # 生成台基
    utils.outputMsg("Building Platform...")
    utils.setCollection('台基',parentColl=buildingColl)
    funproxy = partial(buildPlatform.buildPlatform,buildingObj=buildingObj)
    utils.fastRun(funproxy)
    
    # 生成墙体
    utils.outputMsg("Building Wall...")
    utils.setCollection('墙体',parentColl=buildingColl)
    funproxy = partial(buildWall.resetWallLayout,buildingObj=buildingObj)
    utils.fastRun(funproxy)
    
    # 生成屋顶
    utils.outputMsg("Building Roof...")
    funproxy = partial(buildRoof.buildRoof,buildingObj=buildingObj)
    utils.fastRun(funproxy)

    utils.focusObj(buildingObj)