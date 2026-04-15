# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   建筑剖视图

import bpy
from mathutils import Vector
from .. import utils
from ..locale.i18n import _
from ..const import ACA_Consts as con
from . import buildingJoin
from .. import texture as mat

# 纵剖视图
def addSection(buildingObj:bpy.types.Object,
               sectionPlan='X+'):
    bData = buildingObj.ACA_data
    # 剖视修改器名称，便于找回
    sectionModName = 'Section'
    # 当前剖视模式
    currentPlan = None
    joinedObj = None

    # 1、验证是否合并？是否剖视？ -----------------------
    # 1.1、如果还未合并，先做合并
    if bData.aca_type != con.ACA_TYPE_BUILDING_JOINED:
        joinedObj = buildingJoin.joinBuilding(
            buildingObj,sectionPlan=sectionPlan)
    # 1.2、如果已经合并，确认是否已经做了剖视
    else:
        # 当前剖视模式
        if 'sectionPlan' in bData:     
            currentPlan = bData['sectionPlan']
        # 1.2.1、已合并但未作剖视的新合并对象，无需特殊处理
        if currentPlan == None:
            joinedObj = buildingObj
        # 1.2.2、已合并已剖视的对象，需要重新处理
        else:
            # 1.2.2.1、如果剖视方案相同，解除剖视
            if sectionPlan == currentPlan:
                # 这里解除合并的同时，就会解除剖视
                buildingJoin.undoJoin(buildingObj)
                return
            # 1.2.2.2、剖视方案不同，重新合并
            else:
                # 解除合并
                buildingObj = buildingJoin.undoJoin(buildingObj)
                joinedObj = buildingJoin.joinBuilding(
                    buildingObj,sectionPlan=sectionPlan)
    
    # 验证是否合并成功
    if joinedObj == None:
        utils.outputMsg(_("合并失败，无法继续做剖视图"))
        return
    
    # 合并的结果需要进行一次刷新
    # 否则可能出现getBoundCenter时结果错误
    utils.updateScene()
    
    # 2、开始做剖视 -----------------------
    # 指定在合并目录中操作
    coll:bpy.types.Collection = utils.setCollection(
                con.COLL_NAME_ROOT_JOINED,isRoot=True,colorTag=3)
    
    # 寻找剖视对象
    sectionObjs = []
    if joinedObj.children:
        # 针对子对象做剖视
        for child in joinedObj.children:
            sectionObjs.append(child)
    else:
        # 针对根对象做剖视
        sectionObjs.append(joinedObj)

    # 逐个对象添加剖视修改器
    for sectionObj in sectionObjs:
        # 1、清除老的bool ---------------------------
        # 确认该对象是否已经有boolean
        mod = sectionObj.modifiers.get(sectionModName)
        # 已有boolean的删除boolCube和modifier
        if mod != None:
            # 删除布尔对象
            utils.delObject(mod.object)
            # 删除修改器
            sectionObj.modifiers.remove(mod)
        
        # 2、新建bool对象 -------------------------------
        # 命名
        boolName = 'b.' + sectionObj.name
        # 略作放大
        sectionDim = (Vector(sectionObj.dimensions) 
                * Vector((1.1,1.1,1.1))
                )
        sectionLoc = utils.getBoundCenter(sectionObj)
        # 260409 修复踏跺的正剖裁剪
        sectionDim += Vector(tuple(map(abs,sectionLoc)))
        # 创建剖视布尔对象
        boolObj = utils.addCube(
            name=boolName,
            dimension=sectionDim,
            location=sectionLoc,
            parent=sectionObj
        )
        
        # 3、载入剖视方案 --------------------------
        # 设置剖视方案
        boolPlan = __getSectionPlan(boolObj,sectionPlan)
        # 布尔材质
        mat.paint(boolObj,boolPlan['mat'])
        # 布尔位移
        boolObj.location += boolPlan['offset']
        # 设置外观
        utils.hideObj(boolObj)
        # boolObj.hide_select = True    # 禁止选中

        # 仅对需要布尔的对象添加修改器
        if boolPlan['bool']:
            # 添加boolean
            utils.addModifierBoolean(
                name=sectionModName,
                object=sectionObj,
                boolObj=boolObj,
                operation=boolPlan['operation'],
            )
    
    joinedObj.ACA_data['sectionPlan']=sectionPlan 
    utils.focusObj(joinedObj)
    return

# 剖面图方案
def __getSectionPlan(boolObj:bpy.types.Object,
                     sectionType='X+',):
    # 载入数据
    # boolObj是切割体，parent是层合并对象，该对象在合并时继承了建筑的combo_type
    bData = boolObj.parent.ACA_data
    # 区分是否为楼阁等组合对象
    if bData.combo_type in (con.COMBO_MAIN,con.COMBO_TERRACE):
        isComboNext = False
    else:
        isComboNext = True
    
    Y_reserve = -0.35
    offset = Vector((0,0,0))
    origin_loc = boolObj.location.copy()
    layerName = boolObj.name

    # 每一层对象的布尔处理存入字典
    boolPlan = {}
    boolPlan['bool'] = False
    # 默认无位移
    boolPlan['offset'] = Vector((0,0,0))
    # 操作类型，DIFFERENCE，INTERSECT，UNION
    boolPlan['operation'] = 'DIFFERENCE'
    boolPlan['mat'] = con.M_STONE

    # Y剖面正方向
    if sectionType == 'Y+':
        boolPlan['bool'] = True
        boolPlan['offset'] = Vector((
            0,
            boolObj.dimensions.y/2 - Y_reserve - origin_loc.y,
            0
        ))
    elif sectionType == 'Y-':
        boolPlan['bool'] = True
        boolPlan['offset'] = Vector((
            0,
            -boolObj.dimensions.y/2 + Y_reserve - origin_loc.y,
            0
        ))
    elif sectionType == 'X+':
        boolPlan['bool'] = True
        boolPlan['offset'] = Vector((
            boolObj.dimensions.x/2 - origin_loc.x,
            0,
            0
        ))
    elif sectionType == 'X-':
        boolPlan['bool'] = True
        boolPlan['offset'] = Vector((
            -boolObj.dimensions.x/2 - origin_loc.x,
            0,
            0
        ))
    # 穿墙透壁模式
    elif sectionType == 'A':
        # 1-台基层，不裁剪
        if con.COLL_NAME_BASE in layerName:
            pass
        # 2-柱网层
        elif con.COLL_NAME_PILLAR in layerName:
            pass
        # 3-装修层
        # 因为装修没有做到柱头（额枋），所以实际比柱网层裁剪更低
        elif con.COLL_NAME_WALL in layerName:
            pass
        # 4-斗栱层
        elif con.COLL_NAME_DOUGONG in layerName:
            pass
        # 5-梁架层
        elif con.COLL_NAME_BEAM in layerName:
            pass
        # 6-椽架层
        elif con.COLL_NAME_RAFTER in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 7-山花望板层
        elif con.COLL_NAME_BOARD in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.4 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 8-瓦作层，裁剪整个右侧
        elif con.COLL_NAME_TILE in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.35 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_STONE
    elif sectionType == 'B':
        # 1-台基层，不裁剪
        if con.COLL_NAME_BASE in layerName:
            if not isComboNext:
                # 底层，不裁剪
                pass
            else:
                # 上层楼板裁剪1/4
                boolPlan['bool'] = True
                boolPlan['offset'] = Vector((
                    boolObj.dimensions.x*0.5 - origin_loc.x,
                    -boolObj.dimensions.y*0.5 + Y_reserve,
                    0
                ))
                boolPlan['mat'] = con.M_STONE
        # 2-柱网层
        elif con.COLL_NAME_PILLAR in layerName:
            # 判断combo对象
            if isComboNext:
                boolZ = 0
            else:
                boolZ = boolObj.dimensions.z*0.3
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5 + Y_reserve,
                boolZ
            ))
            boolPlan['mat'] = con.M_WOOD
        # 3-装修层
        # 因为装修没有做到柱头（额枋），所以实际比柱网层裁剪更低
        elif con.COLL_NAME_WALL in layerName:
            # 判断combo对象
            if isComboNext:
                boolZ = 0
            else:
                boolZ = boolObj.dimensions.z*0.2
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5 + Y_reserve,
                boolZ,
            ))
            boolPlan['mat'] = con.M_STONE
        # 4-斗栱层
        elif con.COLL_NAME_DOUGONG in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5 + Y_reserve,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 5-梁架层
        elif con.COLL_NAME_BEAM in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5 + Y_reserve,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 6-椽架层
        elif con.COLL_NAME_RAFTER in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 7-山花望板层
        elif con.COLL_NAME_BOARD in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.4 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 8-瓦作层，裁剪整个右侧
        elif con.COLL_NAME_TILE in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.35 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_STONE
        # 9-平座层，裁剪1/4
        elif con.COLL_NAME_BALCONY in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5,
                0,
            ))
            boolPlan['mat'] = con.M_STONE
    elif sectionType == 'C':
        # 1-台基层
        if con.COLL_NAME_BASE in layerName:
            if not isComboNext:
                # 底层，不裁剪
                pass
            else:
                # 上层楼板裁剪一半
                boolPlan['bool'] = True
                boolPlan['offset'] = Vector((
                    boolObj.dimensions.x*0.5 - origin_loc.x,
                    0,
                    0
                ))
                boolPlan['mat'] = con.M_STONE
        # 2-柱网层
        elif con.COLL_NAME_PILLAR in layerName:
            # 判断combo对象
            if isComboNext:
                boolZ = 0
            else:
                boolZ = boolObj.dimensions.z*0.3
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                0,
                boolZ
            ))
            boolPlan['mat'] = con.M_WOOD
        # 3-装修层
        # 因为装修没有做到柱头（额枋），所以实际比柱网层裁剪更低
        elif con.COLL_NAME_WALL in layerName:
            # 判断combo对象
            if isComboNext:
                boolZ = 0
            else:
                boolZ = boolObj.dimensions.z*0.2
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                0, 
                boolZ,
            ))
            boolPlan['mat'] = con.M_STONE
        # 4-斗栱层
        elif con.COLL_NAME_DOUGONG in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 5-梁架层
        elif con.COLL_NAME_BEAM in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 6-椽架层
        elif con.COLL_NAME_RAFTER in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 7-山花望板层
        elif con.COLL_NAME_BOARD in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.4 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 8-瓦作层，裁剪整个右侧
        elif con.COLL_NAME_TILE in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.35 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_STONE
        # 9-平座层，裁剪一半
        elif con.COLL_NAME_BALCONY in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_STONE

    return boolPlan
