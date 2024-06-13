# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   柱子的营造
import bpy
from mathutils import Vector
from functools import partial
import math
from typing import List

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import utils
from . import acaTemplate
from . import buildWall
from . import buildPlatform
from . import buildDougong
from . import buildRoof
from . import buildRooftile

# 添加建筑empty根节点，并绑定设计模版
# 返回建筑empty根节点对象
# 被ACA_OT_add_newbuilding类调用
def __addBuildingRoot(templateName):
    coll = utils.setCollection(templateName)
    # 创建buildObj根节点
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    buildingObj = bpy.context.object
    buildingObj.location = bpy.context.scene.cursor.location   # 原点摆放在3D Cursor位置
    buildingObj.name = templateName   # 系统遇到重名会自动添加00x的后缀       
    buildingObj.empty_display_type = 'SPHERE'

    # 在buildingObj中填充模版数据
    acaTemplate.openTemplate(buildingObj,templateName)
    
    return buildingObj

# 返回柱网数据
# 非内部函数，在墙体、斗栱、屋顶制作时都有公开调用
# 将panel中设置的面宽、进深，组合成柱网数组
# 返回net_x[],net_y[]数组
def getFloorDate(buildingObj:bpy.types.Object):
    # 载入设计参数
    bData:acaData = buildingObj.ACA_data

    # 构造柱网X坐标序列
    x_rooms = bData.x_rooms   # 面阔几间
    y_rooms = bData.y_rooms   # 进深几间

    net_x = []  # 重新计算    
    # 排布规律：明间+多个次间+梢间
    # 明间有且只有1间
    offset = bData.x_1 / 2
    net_x.append(offset)
    net_x.insert(0, -offset)
    # 次间可能有多间
    if x_rooms > 5:
        # -1明间-2梢间-2尽间
        cijianNum = x_rooms - 5
    elif x_rooms > 3:
        # -1明间-2梢间
        cijianNum = x_rooms - 3
    else:
        # -1明间
        cijianNum = x_rooms - 1
    for n in range(1,int(cijianNum/2)+1):
        offset = (bData.x_1/2 + bData.x_2*n)
        net_x.append(offset)
        net_x.insert(0, -offset) 
    # 梢间，5间以上配置一间
    if x_rooms >= 5 :
        offset += bData.x_3 
        net_x.append(offset)
        net_x.insert(0, -offset) 
    # 尽间，7间以上配置一间
    if x_rooms >= 7 :
        offset += bData.x_4 
        net_x.append(offset)
        net_x.insert(0, -offset) 

    # 构造柱网Y坐标序列
    # 进深可以为奇数（山柱分两侧），也可以为偶数（山柱居中）
    net_y=[]    # 重新计算
    if y_rooms%2 == 1: # 奇数间
        # 明间，有且只有1间
        offset = bData.y_1 / 2
        net_y.append(offset)
        net_y.insert(0, -offset)
        # 计算次间数量
        if y_rooms > 3:
            # 1间明间，2间梢间
            cijianNum = y_rooms - 3
        else:
            # 仅1间明间，不做梢间
            cijianNum = y_rooms -1
        # 循环计算次间柱位
        for n in range(1,int(cijianNum/2)+1):
            offset = (bData.y_1/2 + bData.y_2*n)
            net_y.append(offset)
            net_y.insert(0, -offset) 
        # 梢间
        if y_rooms > 3:
            offset += bData.y_3 
            net_y.append(offset)
            net_y.insert(0, -offset)
    else:   #偶数间
        # 偶数间进深，有默认的山柱，位置Y=0
        net_y.append(0)
        # 明间，分做2间
        offset = bData.y_1
        net_y.append(offset)
        net_y.insert(0, -offset)
        # 计算次间数量
        if y_rooms > 4:
            # 2间明间，2间梢间
            cijianNum = y_rooms - 4
        else:
            # 仅2间明间，无梢间
            cijianNum = y_rooms - 2
        # 循环计算次间柱位
        for n in range(1,int(cijianNum/2)+1):
            offset = (bData.y_1 + bData.y_2*n)
            net_y.append(offset)
            net_y.insert(0, -offset) 
        # 梢间
        if y_rooms > 4:
            offset += bData.y_3 
            net_y.append(offset)
            net_y.insert(0, -offset)
    
    # 保存通面阔计算结果，以便其他函数中复用
    bData.x_total = net_x[-1]-net_x[0]
    # 保存通进深计算结果，以便其他函数中复用
    bData.y_total = net_y[-1]-net_y[0]

    return net_x,net_y

# 在柱间添加额枋
def __buildFang(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    # 柱网根节点
    floorRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_FLOOR_ROOT)
    # 获取开间、进深数据
    net_x,net_y = getFloorDate(buildingObj)
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('柱网',parentColl=buildingColl)

    # 删除现有枋
    for obj in floorRootObj.children:
        if 'aca_type' in obj.ACA_data:
            if obj.ACA_data['aca_type'] == con.ACA_TYPE_FANG:
                # 连带小额枋、垫板子对象
                utils.deleteHierarchy(obj,del_parent=True)
    
    # 根据建筑模版的参数设置分布
    # '0/0#1/0,1/0#2/0,2/0#3/0,3/0#3/1,3/1#3/2,3/2#3/3,3/3#2/3,2/3#1/3,1/3#0/3,0/3#0/2,0/2#0/1,0/1#0/0,'
    fangStr = bData.fang_net
    fangID_List = fangStr.split(',')
    for fangID in fangID_List:
        if fangID == '': continue
        setting = fangID.split('#')
        # 分解获取柱子编号
        pFrom = setting[0].split('/')
        pFrom_x = int(pFrom[0])
        pFrom_y = int(pFrom[1])
        vFrom = Vector((net_x[pFrom_x],net_y[pFrom_y],0))

        pTo = setting[1].split('/')
        pTo_x = int(pTo[0])
        pTo_y = int(pTo[1])
        vTo = Vector((net_x[pTo_x],net_y[pTo_y],0))

        # 计算柱子之间的距离和定位      
        fang_length = utils.getVectorDistance(vFrom,vTo)
        fang_rot = utils.alignToVector(vFrom-vTo)
        fang_x = (net_x[pFrom_x]+net_x[pTo_x])/2
        fang_y = (net_y[pFrom_y]+net_y[pTo_y])/2      
        
        # 大额枋
        bigFangScale = Vector((fang_length, 
                con.EFANG_LARGE_Y * dk,
                con.EFANG_LARGE_H * dk))
        bigFangLoc = Vector((fang_x,fang_y,
                bData.piller_height - con.EFANG_LARGE_H*dk/2))
        bigFangObj = utils.drawHexagon(
            bigFangScale,
            bigFangLoc,
            name =  "大额枋." + fangID,
            parent = floorRootObj,
            )
        bigFangObj.rotation_euler = fang_rot
        bigFangObj.ACA_data['aca_obj'] = True
        bigFangObj.ACA_data['aca_type'] = con.ACA_TYPE_FANG
        bigFangObj.ACA_data['fangID'] = fangID
        # 添加边缘导角
        modBevel:bpy.types.BevelModifier=bigFangObj.modifiers.new(
            "Bevel",'BEVEL'
        )
        modBevel.width = con.BEVEL_EXHIGH
        modBevel.segments=3
        # 设置材质
        utils.copyMaterial(bData.mat_red,bigFangObj)

        # 是否需要做小额枋
        if bData.use_smallfang:
            # 垫板
            dianbanScale = Vector((fang_length, 
                    con.BOARD_YOUE_Y*dk,
                    con.BOARD_YOUE_H*dk))
            dianbanLoc = Vector((0,0,
                    - con.EFANG_LARGE_H*dk/2 \
                    - con.BOARD_YOUE_H*dk/2))
            dianbanObj = utils.addCube(
                name="由额垫板." + fangID,
                location=dianbanLoc,
                scale=dianbanScale,
                parent=bigFangObj,
            )
            dianbanObj.ACA_data['aca_obj'] = True
            dianbanObj.ACA_data['aca_type'] = con.ACA_TYPE_FANG
            dianbanObj.ACA_data['fangID'] = fangID
            # 设置材质
            utils.copyMaterial(bData.mat_red,dianbanObj)
            
            # 小额枋
            smallFangScale = Vector( (fang_length, 
                    con.EFANG_SMALL_Y*dk,
                    con.EFANG_SMALL_H*dk))
            smallFangLoc = Vector((0,0,
                    - con.EFANG_LARGE_H*dk/2 \
                    - con.BOARD_YOUE_H*dk \
                    - con.EFANG_SMALL_H*dk/2))
            smallFangObj = utils.drawHexagon(
                smallFangScale,
                smallFangLoc,
                name =  "小额枋." + fangID,
                parent = bigFangObj,
            )
            smallFangObj.ACA_data['aca_obj'] = True
            smallFangObj.ACA_data['aca_type'] = con.ACA_TYPE_FANG
            smallFangObj.ACA_data['fangID'] = fangID
            # 添加边缘导角
            modBevel:bpy.types.BevelModifier=smallFangObj.modifiers.new(
                "Bevel",'BEVEL'
            )
            modBevel.width = con.BEVEL_HIGH
            modBevel.segments=2
            # 设置材质
            utils.copyMaterial(bData.mat_red,smallFangObj)
    
    # 聚焦到最后添加的大额枋，便于用户可以直接删除
    utils.focusObj(bigFangObj)
    return {'FINISHED'}

# 在选中的柱子间，添加枋
def addFang(buildingObj:bpy.types.Object,
              pillers:List[bpy.types.Object]):
    # 载入数据
    bData:acaData = buildingObj.ACA_data

    # 校验用户至少选择2根柱子
    pillerNum = 0
    for piller in pillers:
        if 'aca_type' in piller.ACA_data:   # 可能选择了没有属性的对象
            if piller.ACA_data['aca_type'] \
                == con.ACA_TYPE_PILLER:
                pillerNum += 1
    if pillerNum < 2:
        utils.showMessageBox("ERROR:请至少选择2根柱子")
        return

    # 构造枋网设置
    pFrom = None
    pTo= None
    fangStr = bData.fang_net
    for piller in pillers:
        # 校验用户选择的对象，可能误选了其他东西，直接忽略
        if 'aca_type' in piller.ACA_data:   # 可能选择了没有属性的对象
            if piller.ACA_data['aca_type'] \
                == con.ACA_TYPE_PILLER:
                if pFrom == None: 
                    pFrom = piller
                    continue #暂存起点
                else:
                    pTo = piller
                    fangID = pFrom.ACA_data['pillerID'] \
                        + '#' + pTo.ACA_data['pillerID'] 
                    fangID_alt = pTo.ACA_data['pillerID'] \
                         + '#' + pFrom.ACA_data['pillerID'] 
                    # 验证枋子是否已经存在
                    if fangID in fangStr or fangID_alt in fangStr:
                        print(fangID + " is in fangstr:" + fangStr)
                        continue
                    fangStr += fangID + ','
                    pFrom = piller

    # 根据fang_net字串，重新生成所有枋子
    bData.fang_net = fangStr
    result = __buildFang(buildingObj)
    
    return result

# 减枋
def delFang(buildingObj:bpy.types.Object,
              fangs:List[bpy.types.Object]):
    # 载入数据
    bData:acaData = buildingObj.ACA_data

    # 删除柱子和柱础
    for fang in fangs:
        # 校验用户选择的对象，可能误选了其他东西，直接忽略
        if 'aca_type' in fang.ACA_data:
            if fang.ACA_data['aca_type'] \
                == con.ACA_TYPE_FANG:
                utils.deleteHierarchy(fang,del_parent=True)

    # 重新生成柱网配置
    floorRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_FLOOR_ROOT
    )    
    floorChildren:List[bpy.types.Object] = floorRootObj.children
    bData.fang_net = ''
    for fang in floorChildren:
        if 'aca_type' in fang.ACA_data:
            if fang.ACA_data['aca_type']==con.ACA_TYPE_FANG:
                fangID = fang.ACA_data['fangID']
                bData.fang_net += fangID + ','
    
    # 重新聚焦根节点
    utils.focusObj(buildingObj)

    return

# 根据柱网数组，排布柱子
# 1. 第一次按照模板生成，柱网下没有柱，一切从0开始；
# 2. 用户调整柱网的开间、进深，需要保持柱子的高、径、样式
# 3. 修改柱样式时，也会重排柱子
# 建筑根节点（内带设计参数集）
# 不涉及墙体重建，很快
def buildPillers(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    pd = con.PILLER_D_EAVE * dk
    bData['is_showPillers'] = True

    # 锁定操作目录
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('柱网',parentColl=buildingColl)

    # 解决bug：面阔间数在鼠标拖拽时可能为偶数，出现异常
    if bData.x_rooms % 2 == 0:
        # 不处理偶数面阔间数
        utils.showMessageBox("面阔间数不能为偶数","ERROR")
        return
    
    # 1、查找或新建地盘根节点
    floorRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_FLOOR_ROOT)
    if floorRootObj == None:        
        # 创建新地盘对象（empty）===========================================================
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        floorRootObj = bpy.context.object
        floorRootObj.name = "柱网"
        floorRootObj.parent = buildingObj  # 挂接在对应建筑节点下
        floorRootObj.ACA_data['aca_obj'] = True
        floorRootObj.ACA_data['aca_type'] = con.ACA_TYPE_FLOOR_ROOT
        #与台基顶面对齐
        floor_z = bData.platform_height
        floorRootObj.location = (0,0,floor_z)
    else:
        # 清空地盘下所有的柱子、柱础
        utils.deleteHierarchy(floorRootObj)

    # 2、生成一个柱子实例piller_basemesh
    # 从当前场景中载入数据集
    bData:acaData = buildingObj.ACA_data
    piller_source = bData.piller_source
    piller_height = bData.piller_height
    piller_R = bData.piller_diameter /2
    if piller_source == None:
        # 默认创建简单柱子
        piller_basemesh = utils.addCylinder(radius=piller_R,
                depth=piller_height,
                location=(0, 0, 0),
                name="基本立柱",
                root_obj=floorRootObj,  # 挂接在柱网节点下
                origin_at_bottom = True,    # 将origin放在底部
            )
    else:
        # 已设置柱样式，根据设计参数实例化
        piller_basemesh:bpy.types.Object = utils.copyObject(
            sourceObj=piller_source,
            name=piller_source.name,
            parentObj=floorRootObj,
            singleUser=True
        )
        # 获取对象应用modifier后的实际尺寸
        utils.updateScene()
        piller_basemesh.dimensions = (
            bData.piller_diameter,
            bData.piller_diameter,
            bData.piller_height
        )
        #utils.applyScale(piller_basemesh) # 此时mesh已经与source piller解绑，生成了新的mesh
    # 柱子属性
    piller_basemesh.ACA_data['aca_obj'] = True
    piller_basemesh.ACA_data['aca_type'] = con.ACA_TYPE_PILLER
    
    # 3、根据地盘数据，循环排布每根柱子
    net_x,net_y = getFloorDate(buildingObj)
    x_rooms = bData.x_rooms   # 面阔几间
    y_rooms = bData.y_rooms   # 进深几间
    for y in range(y_rooms + 1):
        for x in range(x_rooms + 1):
            # 统一命名为“柱.x/y”，以免更换不同柱形时，减柱设置失效
            pillerID = str(x) + '/' + str(y)
            
            # 减柱验证
            piller_list_str = bData.piller_net
            if pillerID not in piller_list_str \
                    and piller_list_str != "" :
                # utils.outputMsg("PP: piller skiped " + piller_copy_name)
                continue    # 结束本次循环
            
            # 复制柱子，仅instance，包含modifier
            piller_loc = (net_x[x],net_y[y],piller_basemesh.location.z)
            piller_copy = utils.copyObject(
                sourceObj = piller_basemesh,
                name = '柱.' + pillerID,
                location=piller_loc,
                parentObj = floorRootObj
            )
            piller_copy.ACA_data['pillerID'] = pillerID

            # 生成柱顶石
            pillerBase_h = 0.3
            pillerBase_popup = 0.02
            pillerBase = utils.addCube(
                name='柱顶石',
                location=(0,0,
                          (piller_copy.location.z 
                           - pillerBase_h/2
                           +pillerBase_popup)),
                scale=(2*bData.piller_diameter/piller_copy.scale.x,
                       2*bData.piller_diameter/piller_copy.scale.y,
                       pillerBase_h),
                parent=piller_copy
            )
            # 添加bevel
            modBevel:bpy.types.BevelModifier = \
                pillerBase.modifiers.new('Bevel','BEVEL')
            modBevel.width = con.BEVEL_HIGH
            modBevel.offset_type = 'WIDTH'
            # 材质
            utils.copyMaterial(bData.mat_stone,pillerBase)

    # 清理临时柱子
    utils.deleteHierarchy(piller_basemesh,True)

    # 添加柱间的额枋
    # 重设柱网时，可能清除fang_net数据，而导致异常
    if bData.fang_net != '':
        __buildFang(buildingObj)

    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)
    
    return

# 减柱并保存
def delPiller(buildingObj:bpy.types.Object,
              pillers:List[bpy.types.Object]):
    # 载入数据
    bData:acaData = buildingObj.ACA_data

    # 删除柱子和柱础
    for piller in pillers:
        # 校验用户选择的对象，可能误选了其他东西，直接忽略
        if 'aca_type' in piller.ACA_data:
            if piller.ACA_data['aca_type'] \
                == con.ACA_TYPE_PILLER:
                utils.deleteHierarchy(piller,del_parent=True)

    # 重新生成柱网配置
    floorRootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_FLOOR_ROOT
    )    
    floorChildren:List[bpy.types.Object] = floorRootObj.children
    bData.piller_net = ''
    for piller in floorChildren:
        if 'aca_type' in piller.ACA_data:
            if piller.ACA_data['aca_type']==con.ACA_TYPE_PILLER:
                pillerID = piller.ACA_data['pillerID']
                bData.piller_net += pillerID + ','
    return

# 根据用户在插件面板修改的柱高、柱径，缩放柱子外观
# 会自动触发墙体的重建，速度很慢
# 绑定于data.py中objdata属性中触发的回调
def resizePiller(buildingObj:bpy.types.Object):   
    bData:acaData = buildingObj.ACA_data
    
    floorRootObj = utils.getAcaChild(buildingObj,con.ACA_TYPE_FLOOR_ROOT)
    if len(floorRootObj.children) >0 :
        for piller in floorRootObj.children:
            if piller.ACA_data['aca_type'] == con.ACA_TYPE_PILLER:
                piller.dimensions = (
                    bData.piller_diameter,
                    bData.piller_diameter,
                    bData.piller_height
                )

    # 柱高、柱径的变化，都会引起隔扇、墙体的变化，需要重建
    # 重新生成墙体
    funproxy = partial(buildWall.buildWallLayout,buildingObj=buildingObj)
    utils.fastRun(funproxy)

    # 重新聚焦建筑根节点
    utils.focusObj(buildingObj)
    utils.outputMsg("Piller resized")

# 重设柱网设置，让减柱重新显示
def resetFloor(buildingObj:bpy.types.Object):
    bData:acaData = buildingObj.ACA_data
    bData.piller_net = ''
    bData.fang_net = ''
    bData.wall_net = ''
    result = buildFloor(buildingObj)
    return result

# 执行营造整体过程
# 输入buildingObj，自带设计参数集，且做为其他构件绑定的父节点
# 采用了偏函数和fastrun，极大加速了性能
def buildFloor(buildingObj:bpy.types.Object):
    # 定位到collection，如果没有则新建
    utils.setCollection(con.ROOT_COLL_NAME,isRoot=True)

    # 新建还是刷新？
    if buildingObj == None:
        utils.outputMsg("创建新建筑...")
        # 获取panel上选择的模版
        templateName = bpy.context.scene.ACA_data.template
        # 添加建筑根节点，同时载入模版
        buildingObj = __addBuildingRoot(templateName)
    else:
        # 删除屋顶，柱网变化必然引起屋顶重构
        roofRoot = utils.getAcaChild(
            buildingObj,con.ACA_TYPE_ROOF_ROOT)
        utils.deleteHierarchy(roofRoot)
        # 删除墙体，柱网变化必然引起墙体重构
        wallRoot = utils.getAcaChild(
            buildingObj,con.ACA_TYPE_WALL_ROOT)
        utils.deleteHierarchy(wallRoot)

    # 生成柱网
    utils.outputMsg("Building Pillers...")
    buildPillers(buildingObj)
    
    # 生成台基
    utils.outputMsg("Building Platform...")
    buildPlatform.buildPlatform(buildingObj)
    
    # 生成墙体
    utils.outputMsg("Building Wall...")
    buildWall.buildWallLayout(buildingObj)
    
    # 生成屋顶
    utils.outputMsg("Building Roof...")
    buildRoof.buildRoof(buildingObj)

    # 重新聚焦回根节点
    utils.focusObj(buildingObj)

    return {'FINISHED'}