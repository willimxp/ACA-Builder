# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   斗栱的营造
import bpy
import math

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import utils
from . import buildFloor
from . import buildRoof

# 添加斗栱根节点
def __addDougongRoot(buildingObj:bpy.types.Object):
    # 设置目录
    buildingColl = buildingObj.users_collection[0]
    utils.setCollection('斗栱',parentColl=buildingColl) 
    
    # 载入数据
    bData : acaData = buildingObj.ACA_data # 载入数据

    # 新建或清空根节点
    dgrootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_DG_ROOT)
    if dgrootObj == None:
        # 创建根对象（empty）===========================================================
        # 相对于屋顶层根节点（挑檐桁下皮）
        root_z = -bData.dg_height
        bpy.ops.object.empty_add(
            type='PLAIN_AXES',location=(0,0,root_z))
        dgrootObj = bpy.context.object
        dgrootObj.name = "斗栱层"
        dgrootObj.ACA_data['aca_obj'] = True
        dgrootObj.ACA_data['aca_type'] = con.ACA_TYPE_DG_ROOT
        # 绑定在屋顶根节点下
        roofRootObj = utils.getAcaChild(
            buildingObj,con.ACA_TYPE_ROOF_ROOT)
        dgrootObj.parent = roofRootObj
    else:
        # 清空根节点
        utils.deleteHierarchy(dgrootObj)
        utils.focusCollByObj(dgrootObj)

    return dgrootObj

def buildDougong(buildingObj:bpy.types.Object): 
    # 添加根节点以及目录
    dgrootObj = __addDougongRoot(buildingObj)

    # 载入数据
    bData : acaData = buildingObj.ACA_data
    if bData.aca_type != con.ACA_TYPE_BUILDING:
        utils.showMessageBox("错误，输入的不是建筑根节点")
        return
    dk = bData.DK

    # 椽望定位依赖斗栱，强制生成
    if bData.is_showBPW : bData['is_showDougong'] = True
    # 用户可以暂时不生成斗栱
    if not bData.is_showDougong: return
    # 如果不使用斗栱，以下直接跳过
    if not bData.use_dg: return

    # 获取地盘数据
    net_x,net_y = buildFloor.getFloorDate(buildingObj)

    # 平板枋，在根节点平面之下，便于整体控制
    if bData.use_pingbanfang:
        extendLength = con.HENG_COMMON_D*dk*2
        # 檐面平板枋
        loc = (0,net_y[0],-con.PINGBANFANG_H*dk/2)
        bpy.ops.mesh.primitive_cube_add(
            location=loc
        )
        pingbanfangObj = bpy.context.object
        pingbanfangObj.name = '平板枋'
        pingbanfangObj.parent = dgrootObj
        pingbanfangObj.dimensions =(
            bData.x_total + extendLength,
            con.PINGBANFANG_Y*dk,
            con.PINGBANFANG_H*dk
        )
        utils.applyTransfrom(pingbanfangObj,use_scale=True)
        modBevel:bpy.types.BevelModifier = \
            pingbanfangObj.modifiers.new('Bevel','BEVEL')
        modBevel.width = 0.02
        utils.addModifierMirror(
            object=pingbanfangObj,
            mirrorObj=dgrootObj,
            use_axis=(False,True,False)
        )
        # 山面平板枋
        loc = (net_x[0],0,-con.PINGBANFANG_H*dk/2)
        bpy.ops.mesh.primitive_cube_add(
            location=loc
        )
        pingbanfangObj = bpy.context.object
        pingbanfangObj.name = '平板枋'
        pingbanfangObj.parent = dgrootObj
        pingbanfangObj.dimensions =(
            con.PINGBANFANG_Y*dk,
            bData.y_total + extendLength,
            con.PINGBANFANG_H*dk
        )
        utils.applyTransfrom(pingbanfangObj,use_scale=True)
        modBevel:bpy.types.BevelModifier = \
            pingbanfangObj.modifiers.new('Bevel','BEVEL')
        modBevel.width = 0.02
        utils.addModifierMirror(
            object=pingbanfangObj,
            mirrorObj=dgrootObj,
            use_axis=(True,False,False)
        )       

    # 3、布置斗栱/铺作======================================================
    # 转角斗栱，仅用于庑殿/歇山
    if (bData.roof_style in (
            con.ROOF_WUDIAN,con.ROOF_XIESHAN)
            and bData.dg_corner_source != None):
        # 四个角柱坐标
        dgCornerArray = (
            (net_x[-1], net_y[0],0),
            (net_x[-1], net_y[-1],0),
            (net_x[0], net_y[-1],0),
            (net_x[0], net_y[0],0)
        )
        for n in range(len(dgCornerArray)) :
            dgCornerCopy:bpy.types.Object = utils.copyObject(
                sourceObj = bData.dg_corner_source,
                name = "转角斗栱",
                location = dgCornerArray[n],
                parentObj = dgrootObj
                )
            dgCornerCopy.rotation_euler.z = math.radians(n * 90)
            
        
    # 柱头斗栱
    if bData.dg_piller_source != None:
        dgPiller:bpy.types.Object = bData.dg_piller_source
        dgPiller.scale = bData.dg_scale
        # 前后坡的柱头斗栱
        if bData.roof_style in (con.ROOF_WUDIAN,con.ROOF_XIESHAN):
            # 庑殿/歇山有转角斗栱，所以四角柱头不做斗栱
            dgRange = range(1,len(net_x)-1) 
        else:
            # 硬山/悬山做到最后一个柱头
            dgRange = range(len(net_x)) 
        for n in dgRange : 
            # 南侧
            dgPillerCopy:bpy.types.Object = utils.copySimplyObject(
                sourceObj = dgPiller,
                name = "柱头斗栱",
                location=(net_x[n],net_y[0],0),
                parentObj = dgrootObj
                )
            dgPillerCopy.rotation_euler.z = math.radians(0)
            # 北侧
            dgPillerCopy:bpy.types.Object = utils.copySimplyObject(
                sourceObj = dgPiller,
                name = "柱头斗栱",
                location=(net_x[n],net_y[-1],0),
                parentObj = dgrootObj
                )
            dgPillerCopy.rotation_euler.z = math.radians(180)
        
        # 两山的柱头斗栱，仅庑殿/歇山做两山的斗栱
        if bData.roof_style in (con.ROOF_WUDIAN,con.ROOF_XIESHAN):
            for n in range(len(net_y)-2) : 
                # 东侧
                dgPillerCopy:bpy.types.Object = utils.copySimplyObject(
                    sourceObj = dgPiller,
                    name = "柱头斗栱",
                    location=(net_x[-1],net_y[n+1],0),
                    parentObj = dgrootObj
                    )
                dgPillerCopy.rotation_euler.z = math.radians(90)
                # 西侧
                dgPillerCopy:bpy.types.Object = utils.copySimplyObject(
                    sourceObj = dgPiller,
                    name = "柱头斗栱",
                    location=(net_x[0],net_y[-n-2],0),
                    parentObj = dgrootObj
                    )
                dgPillerCopy.rotation_euler.z = math.radians(270)

        # 各个连接件
        for fang in dgPiller.children:
            yLoc = fang.location.y * bData.dg_scale[1]
            zLoc = fang.location.z * bData.dg_scale[2]
            if yLoc == 0:
                extendLength = con.HENG_COMMON_D*dk*2
            else:
                extendLength = 0
            # 做前后檐连接件
            loc = (0, net_y[0] + yLoc, zLoc)
            fangCopy = utils.copyObject(
                sourceObj = fang,
                location = loc,
                parentObj = dgrootObj,
                singleUser=True
            )
            # 跟随缩放
            fangCopy.scale = bData.dg_scale
            utils.updateScene()
            fangCopy.dimensions.x = bData.x_total + extendLength
            utils.applyTransfrom(fangCopy,use_scale=True)
            utils.addModifierMirror(
                object=fangCopy,
                mirrorObj=dgrootObj,
                use_axis=(False,True,False)
            )
            
            # 做两山连接件
            loc = (net_x[-1]- yLoc,0,zLoc)
            fangCopy = utils.copyObject(
                sourceObj = fang,
                location = loc,
                parentObj = dgrootObj,
                singleUser=True
            )
            # 跟随缩放
            fangCopy.scale = bData.dg_scale
            utils.updateScene()
            fangCopy.dimensions.x = bData.y_total + extendLength
            #utils.applyTransfrom(fangCopy,use_scale=True)
            fangCopy.rotation_euler.z = math.radians(90)
            utils.addModifierMirror(
                object=fangCopy,
                mirrorObj=dgrootObj,
                use_axis=(True,False,False)
            )
    
    # 补间斗栱/平身科
    if bData.dg_fillgap_source != '' :
        # 前后坡的补间斗拱
        for n in range(len(net_x)-1) : 
            # 计算攒数
            pStart = net_x[n]
            pEnd = net_x[n+1]
            # dougong_count =  round(abs(pEnd - pStart) / (con.DOUGONG_SPAN * dk)) # 向下取整
            dougong_count =  math.floor(abs(pEnd - pStart) / bData.dg_gap) 
            # 如果间距过大，可能无需补间斗栱
            if dougong_count == 0 : continue
            dougong_span = abs(pEnd - pStart) / dougong_count
            for m in range(1,dougong_count):
                # 上侧
                dgFillCopy:bpy.types.Object = utils.copySimplyObject(
                    sourceObj = bData.dg_fillgap_source,
                    name = "补间斗栱",
                    location=(net_x[n] + dougong_span * m,
                                net_y[-1],0),
                    parentObj = dgrootObj
                    )
                dgFillCopy.rotation_euler.z = math.radians(180)
                # 下侧
                dgFillCopy:bpy.types.Object = utils.copySimplyObject(
                    sourceObj = bData.dg_fillgap_source,
                    name = "补间斗栱",
                    location=(net_x[n] + dougong_span * m,
                                net_y[0],0),
                    parentObj = dgrootObj
                    )
                dgFillCopy.rotation_euler.z = math.radians(0)
        
        # 两山
        if bData.roof_style in (con.ROOF_WUDIAN,con.ROOF_XIESHAN):
            for n in range(len(net_y)-1) : 
                # 求平身科攒数
                pStart = net_y[n]
                pEnd = net_y[n+1]
                #dougong_count =  math.floor(abs(pEnd - pStart) / (con.DOUGONG_SPAN * dk)) # 向下取整
                dougong_count =  math.floor(abs(pEnd - pStart) / bData.dg_gap) 
                # 如果间距过大，可能无需补间斗栱
                if dougong_count == 0 : continue
                dougong_span = abs(pEnd - pStart) / dougong_count
                for m in range(1,dougong_count):
                    # 左侧
                    dgFillCopy:bpy.types.Object = utils.copySimplyObject(
                        sourceObj = bData.dg_fillgap_source,
                        name = "补间斗栱",
                        location=(net_x[0],
                            net_y[n] + dougong_span * m,0),
                        parentObj = dgrootObj
                        )
                    dgFillCopy.rotation_euler.z = math.radians(270)
                    # 右侧
                    dgFillCopy:bpy.types.Object = utils.copySimplyObject(
                        sourceObj = bData.dg_fillgap_source,
                        name = "补间斗栱",
                        location=(net_x[-1],
                            net_y[n] + dougong_span * m,0),
                        parentObj = dgrootObj
                        )
                    dgFillCopy.rotation_euler.z = math.radians(90)
    
    # 重新聚焦在建筑根节点
    utils.focusObj(buildingObj)
    return 

# 更新斗栱高度
def update_dgHeight(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    
    # 原始比例
    if 'dgHeight' in bData.dg_piller_source:
        originHeight = bData.dg_piller_source['dgHeight']
    else:
        utils.outputMsg("斗栱未定义该属性")
    if 'dgExtend' in bData.dg_piller_source:
        originExtend = bData.dg_piller_source['dgExtend']
    else:
        utils.outputMsg("斗栱未定义该属性")

    # 用户缩放比例
    scale = bData.dg_height / originHeight
    bData['dg_extend'] = originExtend * scale
    bData['dg_scale'] = (scale,scale,scale)
    if bData.dg_corner_source != None:
        bData.dg_corner_source.scale = bData.dg_scale
    if bData.dg_fillgap_source != None:
        bData.dg_fillgap_source.scale = bData.dg_scale
    if bData.dg_piller_source != None:
        bData.dg_piller_source.scale = bData.dg_scale

    # 重新生成
    buildRoof.buildRoof(buildingObj)
    return