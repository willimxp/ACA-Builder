# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   管理模版
import bpy
import os
import xml.etree.ElementTree as ET

from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import utils

templateFolder = 'template'
xmlFileName = 'simplyhouse.xml'
blenderFileName = 'acaAssets.blend'

# 解析XML，获取模版列表
def getTemplateList(onlyname=False):
    # 载入XML
    path = os.path.join(templateFolder, xmlFileName)
    tree = ET.parse(path)
    root = tree.getroot()
    templates = root.findall('template')

    template_list = []
    for template in templates:
        tname = template.find('template_name')
        if  tname != None:
            template_name = tname.text
            if onlyname:
                template_list.append(template_name)
            else:
                template_list.append(
                    (template_name,template_name,template_name))
            
    return template_list

# 载入Blender中的资产
# 参考教程：https://b3d.interplanety.org/en/appending-all-objects-from-the-external-blend-file-to-the-scene-with-blender-python-api/
# 参考文档：https://docs.blender.org/api/current/bpy.types.BlendDataLibraries.html
def loadAssets(assetName : str,parent:bpy.types.Object,hide=True,link=True):
    # 验证资源是否有重复，直接返回现有对象
    if assetName in bpy.data.objects:
        if link:    # 仅使用于直接连接，append时不做处理
            return bpy.data.objects[assetName]
    
    # 打开资产文件
    filepath = os.path.join(templateFolder, blenderFileName)

    # 简化做法，效率更高，但没有关联子对象
    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        data_to.objects = [name for name in data_from.objects if name.startswith(assetName)]
    # 验证找到的资产是否唯一
    if len(data_to.objects) == 0:
        utils.outputMsg("未找到指定载入的资产:" + assetName)
        return
    if len(data_to.objects) > 1:
        utils.outputMsg("无法定位唯一的资产:" + assetName)
        return
    
    sourceObj = data_to.objects[0]
    if link:
        # 直接返回引用
        return sourceObj
    else:
        # 返回一个复制的新对象
        newobj = utils.copyObject(
            sourceObj=sourceObj,
            parentObj=parent,
        )
        if hide:
            utils.hideObj(newobj)
        else:
            utils.showObj(newobj)
        for child in newobj.children:
            if hide:
                utils.hideObj(child)
            else:
                utils.showObj(child)
        return newobj

# 用const填充XML中未定义的属性
def __loadDefaultData(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    bData['aca_obj'] = True
    bData['aca_type'] = con.ACA_TYPE_BUILDING

    # 校验DK,PD不能为空
    if bData.DK == 0.0:
        bData['DK'] = con.DEFAULT_DK
    DK = bData.DK
    if bData.piller_diameter == 0.0:
        bData['piller_diameter'] = con.PILLER_D_EAVE*DK    
    PD = bData.piller_diameter

    # 柱高
    bData['piller_height'] = con.PILLER_H_EAVE*DK
    # 默认台基高度
    bData['platform_height'] = con.PLATFORM_HEIGHT*PD
    # 默认台基下出      
    bData['platform_extend'] = con.PLATFORM_EXTEND*PD  
    # 开间
    bData['x_rooms'] = 3
    # 明间宽度    
    bData['x_1'] = con.ROOM_X1*DK 
    # 次间宽度            
    bData['x_2'] = con.ROOM_X2*DK    
    # 梢间宽度         
    bData['x_3'] = con.ROOM_X3*DK     
    # 尽间宽度        
    bData['x_4'] = con.ROOM_X4*DK   
    # 进深
    bData['y_rooms'] = 3
    # 明间进深          
    bData['y_1'] = con.ROOM_Y1*DK
    # 次间进深             
    bData['y_2'] = con.ROOM_Y2*DK  
    # 梢间进深           
    bData['y_3'] = con.ROOM_Y3*DK    
    # 隔扇中槛高度         
    bData['door_height'] = 0.6*bData['piller_height']
    return bData

# 载入模版
# 不再使用templateDate结构中转
# 直接将XML填充入bData
# 注意，所有的属性都为选填，所以要做好空值的检查
def loadTemplate(buildingObj:bpy.types.Object,
                 templateName:str):
    # 解析XML配置模版
    path = os.path.join(templateFolder, xmlFileName)
    tree = ET.parse(path)
    root = tree.getroot()
    templates = root.findall('template')
    if templates == None:
        utils.outputMsg("模版解析失败")
        return
    
    # 同步绑定资产
    # 1. 指定资产目录
    buildingColl = buildingObj.users_collection[0]
    coll = utils.setCollection('资产',parentColl=buildingColl)
    # 2. 指定资产根节点
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    assetsObj = bpy.context.object
    assetsObj.location = buildingObj.location   # 原点摆放在3D Cursor位置
    assetsObj.parent = buildingObj
    assetsObj.name = 'assets'   # 系统遇到重名会自动添加00x的后缀
    assetsObj.ACA_data['aca_obj'] = True
    assetsObj.ACA_data['aca_type'] = con.ACA_TYPE_ASSET_ROOT
    
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    
    # 在XML中查找对应名称的那个模版
    for template in templates:
        template_name = template.find('template_name').text
        if template_name == templateName:
            # 模版名称
            bData['aca_obj'] = True
            bData['aca_type'] = con.ACA_TYPE_BUILDING
            bData['template_name'] = template_name
            
            # 斗口
            dk = template.find('dk').text
            if dk != None: 
                bData['DK'] = float(dk)
            
            # 柱径
            pillers = template.find('pillers')
            if pillers != None:
                pillerD = pillers.find('dimeter')
                if pillerD != None:
                    bData['piller_diameter'] = float(pillerD.text)

            # 初始化默认值，基于前序载入的DK、PD值
            bData = __loadDefaultData(buildingObj)

            # 柱子
            pillers = template.find('pillers')
            if pillers != None:
                # 柱高
                pillerHeight = pillers.find('height')
                if pillerHeight != None:
                    bData['piller_height'] = float(pillerHeight.text)
                # 柱形
                piller_source = pillers.find('piller_source')
                if piller_source != None:
                    bData['piller_source'] = loadAssets(
                        piller_source.text,assetsObj)
                # 柱网
                pillerItems = pillers.findall('piller')
                if pillerItems != None:
                    pillerNet = '' # 防止重复生成时的垃圾数据
                    for piller in pillerItems:
                        pillerNet += piller.attrib['x'] \
                            + "/" \
                            + piller.attrib['y'] \
                            + ","
                    bData['piller_net'] = pillerNet
                # 枋网
                fangs = pillers.findall('fang')
                if fangs != None:
                    fangNet = '' # 防止重复生成时的垃圾数据
                    for fang in fangs:
                        fangNet += \
                            fang.attrib['from'] + '#' \
                            + fang.attrib['to'] + ','
                    bData['fang_net'] = fangNet

            # 台基
            platform = template.find('platform')
            if platform != None:
                # 台基高度
                pfHeight = platform.find('height')
                if pfHeight != None:
                    bData['platform_height'] = float(pfHeight.text)
                # 台基下出
                pfExtend = platform.find('extend')
                if pfExtend != None:
                    bData['platform_extend'] = float(pfExtend.text)
            
            # 地盘
            floor = template.find('floor')
            if floor != None:
                x_rooms = floor.find('x_rooms')
                if x_rooms != None:
                    total = x_rooms.find('total')
                    if total != None:
                        bData['x_rooms'] = int(total.text)
                    x1 = x_rooms.find('x1')
                    if x1 != None:
                        bData['x_1'] = float(x1.text)
                    x2 = x_rooms.find('x2')
                    if x2 != None:
                        bData['x_2'] = float(x2.text)
                    x3 = x_rooms.find('x3')
                    if x3 != None:
                        bData['x_3'] = float(x3.text)
                    x4 = x_rooms.find('x4')
                    if x4 != None:
                        bData['x_4'] = float(x4.text)
                
                y_rooms = floor.find('y_rooms')
                if y_rooms != None:
                    total = y_rooms.find('total')
                    if total != None:
                        bData['y_rooms'] = int(total.text)
                    y1 = y_rooms.find('y1')
                    if y1 != None:
                        bData['y_1'] = float(y1.text)
                    y2 = y_rooms.find('y2')
                    if y2 != None:
                        bData['y_2'] = float(y2.text)
                    y3 = y_rooms.find('y3')
                    if y3 != None:
                        bData['y_3'] = float(y3.text)

            # 墙体
            frame = template.find('frame')
            if frame != None:
                # 墙模版
                wall_source = frame.find('wall_source')
                if wall_source != None:
                    bData['wall_source'] = loadAssets(
                        wall_source.text,assetsObj)
                # 棂心
                lingxin_source = frame.find('lingxin_source')
                if lingxin_source != None:
                    bData['lingxin_source'] = loadAssets(
                        lingxin_source.text,assetsObj)
                # 墙网
                walls = frame.findall('wall')
                if walls != None:
                    wallNet = '' # 防止重新生成时有垃圾数据
                    for wall in walls:
                        wallNet += \
                            wall.attrib['type'] + '#' \
                            + wall.attrib['from'] + '#' \
                            + wall.attrib['to'] + ','
                    bData['wall_net'] = wallNet
                    
            # 斗栱
            dg = template.find('dougong')
            if dg != None:
                bData['use_dg'] = True    # 使用斗栱
                # 柱头斗栱
                piller_source = dg.find('piller_source')
                if piller_source != None:
                    bData['dg_piller_source'] = loadAssets(
                        piller_source.text,assetsObj)
                # 补间斗栱
                fillgap_source = dg.find('fillgap_source')
                if fillgap_source != None:
                    bData['dg_fillgap_source'] = loadAssets(
                        fillgap_source.text,assetsObj)
                corner_source = dg.find('corner_source')
                # 转角斗栱
                if corner_source != None:
                    bData['dg_corner_source'] = loadAssets(
                        corner_source.text,assetsObj)
                # 斗栱攒距
                dg_gap = dg.find('dg_gap')
                if dg_gap != None:
                    bData['dg_gap'] = float(dg_gap.text)
            else:
                bData['use_dg'] = False    # 不用斗栱
            
            # 屋顶
            roof = template.find('roof')
            if roof != None:
                # 屋顶样式
                rafter_style = roof.find('roof_style')
                if rafter_style != None:
                    bData['roof_style'] = int(rafter_style.text)
                # 椽架数量
                rafter_count = roof.find('rafter_count')
                if rafter_count != None:
                    bData['rafter_count'] = int(rafter_count.text)
                # 瓦片垄距
                tile_width = roof.find('tile_width')
                if tile_width != None:
                    bData['tile_width'] = float(tile_width.text)
                # 瓦层宽度
                tile_length = roof.find('tile_length')
                if tile_length != None:
                    bData['tile_length'] = float(tile_length.text)
                # 板瓦对象
                flatTile_source = roof.find('flatTile_source')
                if flatTile_source != None:                       
                    bData['flatTile_source'] = loadAssets(
                        flatTile_source.text,assetsObj)
                # 筒瓦对象
                circularTile_source = roof.find('circularTile_source')
                if circularTile_source != None:                       
                    bData['circularTile_source'] = loadAssets(
                        circularTile_source.text,assetsObj)
                # 瓦当对象
                eaveTile_source = roof.find('eaveTile_source')
                if eaveTile_source != None:
                    bData['eaveTile_source'] = loadAssets(
                        eaveTile_source.text,assetsObj)
                # 滴水对象
                dripTile_source = roof.find('dripTile_source')
                if dripTile_source != None:
                    bData['dripTile_source'] = loadAssets(
                        dripTile_source.text,assetsObj)
                # 正脊对象
                ridgeTop_source = roof.find('ridgeTop_source')
                if ridgeTop_source != None:
                    bData['ridgeTop_source'] = \
                        loadAssets(ridgeTop_source.text,assetsObj)
                # 垂脊兽后对象
                ridgeBack_source = roof.find('ridgeBack_source')
                if ridgeBack_source != None:
                    bData['ridgeBack_source'] = loadAssets(
                        ridgeBack_source.text,assetsObj)
                # 垂脊兽前对象
                ridgeFront_source = roof.find('ridgeFront_source')
                if ridgeFront_source != None:
                    bData['ridgeFront_source'] = loadAssets(
                        ridgeFront_source.text,assetsObj)
                # 端头盘子
                ridgeEnd_source = roof.find('ridgeEnd_source')
                if ridgeEnd_source != None:
                    bData['ridgeEnd_source'] = loadAssets(
                        ridgeEnd_source.text,assetsObj)
                # 博缝板
                bofeng_source = roof.find('bofeng_source')
                if bofeng_source != None:
                    bData['bofeng_source'] = loadAssets(
                        bofeng_source.text,assetsObj)
                # 螭吻
                chiwen_source = roof.find('chiwen_source')
                if chiwen_source != None:
                    bData['chiwen_source'] = loadAssets(
                        chiwen_source.text,assetsObj)
                # 垂兽
                chuishou_source = roof.find('chuishou_source')
                if chuishou_source != None:
                    bData['chuishou_source'] = loadAssets(
                        chuishou_source.text,assetsObj)
                # 套兽
                taoshou_source = roof.find('taoshou_source')
                if taoshou_source != None:
                    bData['taoshou_source'] = loadAssets(
                        taoshou_source.text,assetsObj)
                # 跑兽
                paoshou_0_source = roof.find('paoshou_0_source')
                if paoshou_0_source != None:
                    bData['paoshou_0_source'] = loadAssets(
                        paoshou_0_source.text,assetsObj)
                paoshou_1_source = roof.find('paoshou_0_source')
                if paoshou_1_source != None:
                    bData['paoshou_1_source'] = loadAssets(
                        paoshou_1_source.text,assetsObj)
                paoshou_2_source = roof.find('paoshou_0_source')
                if paoshou_2_source != None:
                    bData['paoshou_2_source'] = loadAssets(
                        paoshou_2_source.text,assetsObj)
                paoshou_3_source = roof.find('paoshou_0_source')
                if paoshou_3_source != None:
                    bData['paoshou_3_source'] = loadAssets(
                        paoshou_3_source.text,assetsObj)
                paoshou_4_source = roof.find('paoshou_0_source')
                if paoshou_4_source != None:
                    bData['paoshou_4_source'] = loadAssets(
                        paoshou_4_source.text,assetsObj)
                paoshou_5_source = roof.find('paoshou_0_source')
                if paoshou_5_source != None:
                    bData['paoshou_5_source'] = loadAssets(
                        paoshou_5_source.text,assetsObj)
                paoshou_6_source = roof.find('paoshou_0_source')
                if paoshou_6_source != None:
                    bData['paoshou_6_source'] = loadAssets(
                        paoshou_6_source.text,assetsObj)
                paoshou_7_source = roof.find('paoshou_0_source')
                if paoshou_7_source != None:
                    bData['paoshou_7_source'] = loadAssets(
                        paoshou_7_source.text,assetsObj)
                paoshou_8_source = roof.find('paoshou_0_source')
                if paoshou_8_source != None:
                    bData['paoshou_8_source'] = loadAssets(
                        paoshou_8_source.text,assetsObj)
                paoshou_9_source = roof.find('paoshou_0_source')
                if paoshou_9_source != None:
                    bData['paoshou_9_source'] = loadAssets(
                        paoshou_9_source.text,assetsObj)
                paoshou_10_source = roof.find('paoshou_0_source')
                if paoshou_10_source != None:
                    bData['paoshou_10_source'] = loadAssets(
                        paoshou_10_source.text,assetsObj)    

            # 材质
            mat = template.find('material')
            if mat != None:
                mat_wood = mat.find('wood_source')
                if mat_wood != None:
                    bData['mat_wood'] = loadAssets(
                        mat_wood.text,assetsObj)
                mat_rock = mat.find('rock_source')
                if mat_rock != None:
                    bData['mat_rock'] = loadAssets(
                        mat_rock.text,assetsObj)
                mat_stone = mat.find('stone_source')
                if mat_stone != None:
                    bData['mat_stone'] = loadAssets(
                        mat_stone.text,assetsObj)
                mat_red = mat.find('paint_red_source')
                if mat_red != None:
                    bData['mat_red'] = loadAssets(
                        mat_red.text,assetsObj)

    return

# 载入模版
# 直接将XML填充入bData
# 注意，所有的属性都为选填，所以要做好空值的检查
def openTemplate(buildingObj:bpy.types.Object,
                 templateName:str):
    # 解析XML配置模版
    path = os.path.join(templateFolder, xmlFileName)
    tree = ET.parse(path)
    root = tree.getroot()
    templates = root.findall('template')
    if templates == None:
        utils.outputMsg("模版解析失败")
        return
    
    # 同步绑定资产
    # 1. 指定资产目录
    buildingColl = buildingObj.users_collection[0]
    coll = utils.setCollection('资产',parentColl=buildingColl)
    # 2. 指定资产根节点
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    assetsObj = bpy.context.object
    assetsObj.location = buildingObj.location   # 原点摆放在3D Cursor位置
    assetsObj.parent = buildingObj
    assetsObj.name = 'assets'   # 系统遇到重名会自动添加00x的后缀
    assetsObj.ACA_data['aca_obj'] = True
    assetsObj.ACA_data['aca_type'] = con.ACA_TYPE_ASSET_ROOT
    
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    
    # 在XML中查找对应名称的那个模版
    for template in templates:
        template_name = template.find('template_name').text
        if template_name == templateName:
            
            # 初始化bData默认值，根据DK/PD实时刷新一次
            # 模版名称
            bData['template_name'] = template_name
            # 斗口
            dk = template.find('dk')
            if dk != None: 
                bData['DK'] = float(dk.text)
            # 柱径
            pd = template.find('piller_diameter')
            if pd != None:
                bData['piller_diameter'] = float(pd.text)
            # 刷新bData默认值
            bData = __loadDefaultData(buildingObj)

            # 遍历所有子节点，并绑定到对应属性
            for node in template:
                tag = node.tag
                type = node.attrib['type']
                value = node.text
                # 类型转换
                if type == 'str':
                    bData[tag] = value
                    # 特殊处理下拉框
                    if tag == 'roof_style':
                        bData[tag] = int(value)
                elif type == 'float':
                    bData[tag] = round(float(value),2)
                elif type == 'int':
                    bData[tag] = int(value)
                elif type == 'bool':
                    bData[tag] = bool(value)
                elif type == 'object':
                    bData[tag] = loadAssets(value,assetsObj)
                else:
                    print("can't convert:",node.tag, node.attrib['type'],node.text)

    return

# 保存模版修改
def saveTemplate(buildingObj:bpy.types.Object):
    # 载入输入
    bData:acaData = buildingObj.ACA_data
    # 模版名称取panel上选择的模版
    # templateName = bpy.context.scene.ACA_data.template
    # 模版名称取当前建筑的名称
    templateName = buildingObj.name

    # 忽略处理的节点
    ignoreKeys = {
        # 辅助参数，无需处理
        'aca_obj',
        'aca_type',
        'x_total',
        'y_total',
        'is_showPlatform',
        'is_showPillers',
        'is_showWalls',
        'is_showDougong',
        'is_showBPW',
        'is_showTiles',
        'wall_layout',
        'wall_style',
        'roof_qiao_point',
        'tile_width_real',
        'dg_scale',

        # # 外部引用，暂不处理
        # 'piller_source',        # 梭柱
        # 'wall_source',          # 墙体
        # 'lingxin_source',       # 棂心.正搭斜交
        # 'dg_piller_source',     # 四铺作插昂柱头.join
        # 'dg_fillgap_source',    # 四铺作插昂柱头.join
        # 'dg_corner_source',     # 四铺作插昂转角.asset
        # 'bofeng_source',        # 博缝板
        # 'flatTile_source',      # 板瓦
        # 'circularTile_source',  # 筒瓦
        # 'eaveTile_source',      # 瓦当
        # 'dripTile_source',      # 滴水
        # 'ridgeTop_source',      # 正脊筒
        # 'ridgeBack_source',     # 垂脊兽后
        # 'ridgeFront_source',    # 垂脊兽前
        # 'ridgeEnd_source',      # 端头组合
        # 'chiwen_source',        # 螭吻
        # 'chuishou_source',      # 垂兽
        # 'taoshou_source',       # 套兽
        # 'paoshou_0_source',     # 0-骑凤仙人
        # 'paoshou_1_source',     # 1-龙
        # 'paoshou_2_source',     # 2-凤
        # 'paoshou_3_source',     # 3-狮子
        # 'paoshou_4_source',     # 4-海马
        # 'paoshou_5_source',     # 5-天马
        # 'paoshou_6_source',     # 6-狎鱼
        # 'paoshou_7_source',     # 7-狻猊
        # 'paoshou_8_source',     # 8-獬豸
        # 'paoshou_9_source',     # 9-斗牛
        # 'paoshou_10_source',    # 10-行什
        # 'mat_wood',          # 原木
        # 'mat_rock',          # 石材
        # 'mat_stone',         # 石头
        # 'mat_red',     # 红漆
    }
    
    # 解析XML配置模版
    path = os.path.join(templateFolder, xmlFileName)
    tree = ET.parse(path)
    root = tree.getroot()   # <templates>根节点
    # 验证根节点
    templateNodeList = root.findall('template')
    if templateNodeList == None:
        utils.outputMsg("模版解析失败")
        return
    
    # 遍历查找对应模版
    isNewTemplate = True
    for templateNode in templateNodeList:
        nameNode = templateNode.find('template_name')
        if nameNode != None:
            if nameNode.text == templateName:
                # 找到对应模版
                isNewTemplate = False
                break
    # 如果没有找到，则新建模版节点
    if isNewTemplate:
        templateNode = ET.SubElement(root,'template')

    # 遍历bData，保存所有的键值
    # https://blender.stackexchange.com/questions/72402/how-to-iterate-through-a-propertygroup
    for key in bData.__annotations__.keys():
        # 提取键值，并保存
        value = getattr(bData, key)
        keyType = type(value).__name__

        # 数据验证和预处理
        # 忽略无需保存的键值
        if key in ignoreKeys: continue
        # 以当前建筑名称覆盖模版名称
        if key == 'template_name':
            value = templateName
        # 浮点数取2位精度
        if keyType == 'float':
            value = round(value,2)
        if keyType == 'Object':
            # value目前未bpy.data.object对象
            object = getattr(bData, key)
            value = object.name  # 对象名称
            # path = object.data.library_weak_reference.filepath

        # 数据保存
        # 查找节点
        keyNode = templateNode.find(key)
        # 验证节点，不存在就新建
        if keyNode == None:
            keyNode = ET.SubElement(templateNode,key)
        # 写入节点
        keyNode.text = str(value)
        keyNode.attrib['type'] = keyType

    # 缩进美化
    # https://stackoverflow.com/questions/28813876/how-do-i-get-pythons-elementtree-to-pretty-print-to-an-xml-file
    ET.indent(tree, space="\t", level=0)
    # 保存
    tree.write(path, encoding='UTF-8',xml_declaration=True)

    # 刷新panel的模版列表
    bpy.context.scene.ACA_data.template = templateName

    return 