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

# 外部定义的建筑模板数据
class templateData:
    # 默认理论参数
    # 公式来源于马炳坚的《中国古建筑木作营造技术》
    # 在解析XML后，以XML的设计值填充
    # Blender中默认以“米”为单位，以下数据也以米为单位
    NAME = ''                   # 模版名称
    DK = 0.08                   # 斗口
    PD = con.PILLER_D_EAVE * DK   # 柱径
    PILLER_HEIGHT = 70*DK         # 柱高
    PILLER_SOURCE  = ""          # 柱样式
    PILLER_NET = ""             # 柱网实例
    FANG_NET = ""               # 枋实例
    WALL_NET = ""               # 墙体实例
    PLATFORM_HEIGHT = 2*PD        # 默认台基高度
    PLATFORM_EXTEND = 2.4*PD      # 默认台基下出
    ROOM_X = 3                  # 面阔间数
    ROOM_X1 = 77*DK             # 明间宽度
    ROOM_X2 = 66*DK             # 次间宽度
    ROOM_X3 = 66*DK             # 梢间宽度
    ROOM_X4 = 22*DK             # 尽间宽度
    ROOM_Y = 3                  # 进深间数
    ROOM_Y1 = 44*DK             # 明间进深
    ROOM_Y2 = 44*DK             # 次间进深
    ROOM_Y3 = 22*DK             # 梢间进深
    WALL_LAYOUT = 1             # 墙体布局，1-默认无廊
    WALL_STYLE = 1              # 墙体类型，1-槛墙，2-隔扇
    WALL_SOURCE = ''            # 墙体外链对象
    DOOR_HEIGHT = 0.6*PILLER_HEIGHT          # 中槛高度，即门上沿高度，未找到理论值，这里我粗估了一个值
    LINGXIN_SOURCE = ''         # 隔扇棂心外链对象
    USE_DG = False              # 是否用斗栱
    DG_PILLER_SOURCE = ''       # 柱头斗栱
    DG_FILLGAP_SOURCE = ''      # 补间斗栱
    DG_CORNER_SOURCE = ''       # 转角斗栱
    RAFTER_COUNT = 6            # 椽架数
    ROOF_STYLE = 1              # 屋顶样式
    TILE_WIDTH = 0.4            # 瓦垄宽度
    TILE_LENGTH = 0.5           # 瓦片长度
    FLATTILE_SOURCE = ''        # 板瓦
    CIRCULARTILE_SOURCE = ''    # 筒瓦
    EAVETILE_SOURCE = ''        # 瓦当
    DRIPTILE_SOURCE = ''        # 滴水
    RIDGETOP_SOURCE = ''        # 正脊筒
    RIDGEBACK_SOURCE = ''       # 垂脊兽后
    RIDGEFRONT_SOURCE = ''      # 垂脊兽前
    RIDGEEND_SOURCE = ''        # 垂脊兽前
    CHIWEN_SOURCE = ''          # 螭吻
    CHUISHOU_SOURCE = ''        # 垂兽
    TAOSHOU_SOURCE = ''         # 套兽
    PAOSHOU_0_SOURCE = ''       # 跑兽-骑凤仙人
    PAOSHOU_1_SOURCE = ''       # 跑兽-龙
    PAOSHOU_2_SOURCE = ''       # 跑兽-凤
    PAOSHOU_3_SOURCE = ''       # 跑兽-狮子
    PAOSHOU_4_SOURCE = ''       # 跑兽-海马
    PAOSHOU_5_SOURCE = ''       # 跑兽-天马
    PAOSHOU_6_SOURCE = ''       # 跑兽-狎鱼
    PAOSHOU_7_SOURCE = ''       # 跑兽-狻猊
    PAOSHOU_8_SOURCE = ''       # 跑兽-獬豸
    PAOSHOU_9_SOURCE = ''       # 跑兽-斗牛
    PAOSHOU_10_SOURCE = ''      # 跑兽-行什
    BOFENG_SOURCE = ''          # 博缝板

# 解析XML，获取模版列表
def getTemplateList():
    # 载入XML
    path = os.path.join(templateFolder, xmlFileName)
    tree = ET.parse(path)
    root = tree.getroot()
    templates = root.findall('template')

    template_list = []
    for template in templates:
        template_name = template.find('name').text
        template_list.append((template_name,template_name,''))
    
    utils.outputMsg("Get template list")
    return template_list

# 载入模版文件中，指定一个模版的数据
# 输入：要求输入配置文件路径
# name：模版名称
def getTemplate(name,doukou=0)->templateData:
    # 解析XML配置模版
    path = os.path.join(templateFolder, xmlFileName)
    tree = ET.parse(path)
    root = tree.getroot()
    templates = root.findall('template')
    tData = templateData

    # 在XML中查找对应名称的那个模版
    for template in templates:
        template_name = template.find('name').text
        if template_name == name:
            # 模版名称
            tData.NAME = name

            # 解析XML中的模版定义，填充实际设计参数            
            # 斗口            
            dk = template.find('dk').text
            if dk != None:
                tData.DK = float(dk)
            # 允许传入的斗口值覆盖模版定义
            if doukou != 0:
                tData.DK = doukou

            # 柱子
            pillers = template.find('pillers')
            if pillers != None:
                pillerD = pillers.find('dimeter')
                if pillerD != None:
                    tData.PD = float(pillerD.text)        
            
            # 根据DK，PD，刷新各个默认值
            tData.PILLER_HEIGHT = 70*tData.DK         # 柱高
            tData.PLATFORM_HEIGHT = 2*tData.PD        # 默认台基高度
            tData.PLATFORM_EXTEND = 2.4*tData.PD      # 默认台基下出
            tData.ROOM_X1 = 77*tData.DK             # 明间宽度
            tData.ROOM_X2 = 66*tData.DK             # 次间宽度
            tData.ROOM_X3 = 66*tData.DK             # 梢间宽度
            tData.ROOM_X4 = 22*tData.DK             # 尽间宽度
            tData.ROOM_Y1 = 44*tData.DK             # 明间进深
            tData.ROOM_Y2 = 44*tData.DK             # 次间进深
            tData.ROOM_Y3 = 22*tData.DK             # 梢间进深
            tData.DOOR_HEIGHT = 0.6*tData.PILLER_HEIGHT

            # 柱子
            pillers = template.find('pillers')
            if pillers != None:
                pillerHeight = pillers.find('height')
                if pillerHeight != None:
                    tData.PILLER_HEIGHT = float(pillerHeight.text)
                piller_source = pillers.find('piller_source')
                if piller_source != None:
                    tData.PILLER_SOURCE = piller_source.text
                pillerItems = pillers.findall('piller')
                if pillerItems != None:
                    tData.PILLER_NET = '' # 防止重复生成时的垃圾数据
                    for piller in pillerItems:
                        tData.PILLER_NET += piller.attrib['x'] \
                            + "/" \
                            + piller.attrib['y'] \
                            + ","
                fangs = pillers.findall('fang')
                if fangs != None:
                    tData.FANG_NET = '' # 防止重复生成时的垃圾数据
                    for fang in fangs:
                        tData.FANG_NET += \
                            fang.attrib['from'] + '#' \
                            + fang.attrib['to'] + ','

            # 台基
            platform = template.find('platform')
            if platform != None:
                pfHeight = platform.find('height')
                if pfHeight != None:
                    tData.PLATFORM_HEIGHT = float(pfHeight.text)
                pfExtend = platform.find('extend')
                if pfExtend != None:
                    tData.PLATFORM_EXTEND = float(pfExtend.text)
            
            # 地盘
            floor = template.find('floor')
            if floor != None:
                x_rooms = floor.find('x_rooms')
                if x_rooms != None:
                    total = x_rooms.find('total')
                    if total != None:
                        tData.ROOM_X = int(total.text)
                    x1 = x_rooms.find('x1')
                    if x1 != None:
                        tData.ROOM_X1 = float(x1.text)
                    x2 = x_rooms.find('x2')
                    if x2 != None:
                        tData.ROOM_X2 = float(x2.text)
                    x3 = x_rooms.find('x3')
                    if x3 != None:
                        tData.ROOM_X3 = float(x3.text)
                    x4 = x_rooms.find('x4')
                    if x4 != None:
                        tData.ROOM_X4 = float(x4.text)
                
                y_rooms = floor.find('y_rooms')
                if y_rooms != None:
                    total = y_rooms.find('total')
                    if total != None:
                        tData.ROOM_Y = int(total.text)
                    y1 = y_rooms.find('y1')
                    if y1 != None:
                        tData.ROOM_Y1 = float(y1.text)
                    y2 = y_rooms.find('y2')
                    if y2 != None:
                        tData.ROOM_Y2 = float(y2.text)
                    y3 = y_rooms.find('y3')
                    if y3 != None:
                        tData.ROOM_Y3 = float(y3.text)

            # 墙体
            frame = template.find('frame')
            if frame != None:
                wall_source = frame.find('wall_source')
                if wall_source != None:
                    tData.WALL_SOURCE = wall_source.text
                lingxin_source = frame.find('lingxin_source')
                if lingxin_source != None:
                    tData.LINGXIN_SOURCE = lingxin_source.text
                walls = frame.findall('wall')
                if walls != None:
                    tData.WALL_NET = '' # 防止重新生成时有垃圾数据
                    for wall in walls:
                        tData.WALL_NET += \
                            wall.attrib['type'] + '#' \
                            + wall.attrib['from'] + '#' \
                            + wall.attrib['to'] + ','
                
            # 斗栱
            dg = template.find('dougong')
            if dg != None:
                tData.USE_DG = True    # 使用斗栱
                piller_source = dg.find('piller_source')
                if piller_source != None:
                    tData.DG_PILLER_SOURCE = piller_source.text
                fillgap_source = dg.find('fillgap_source')
                if fillgap_source != None:
                    tData.DG_FILLGAP_SOURCE = fillgap_source.text
                corner_source = dg.find('corner_source')
                if corner_source != None:
                    tData.DG_CORNER_SOURCE = corner_source.text
            else:
                tData.USE_DG = False    # 不用斗栱
            
            # 屋顶
            roof = template.find('roof')
            if roof != None:
                rafter_style = roof.find('roof_style')
                if rafter_style != None:
                    tData.ROOF_STYLE = int(rafter_style.text)
                rafter_count = roof.find('rafter_count')
                if rafter_count != None:
                    tData.RAFTER_COUNT = int(rafter_count.text)
                tile_width = roof.find('tile_width')
                if tile_width != None:
                    tData.TILE_WIDTH = float(tile_width.text)
                tile_length = roof.find('tile_length')
                if tile_length != None:
                    tData.TILE_LENGTH = float(tile_length.text)
                flatTile_source = roof.find('flatTile_source')
                if flatTile_source != None:
                    tData.FLATTILE_SOURCE = flatTile_source.text
                circularTile_source = roof.find('circularTile_source')
                if circularTile_source != None:
                    tData.CIRCULARTILE_SOURCE = circularTile_source.text
                eaveTile_source = roof.find('eaveTile_source')
                if eaveTile_source != None:
                    tData.EAVETILE_SOURCE = eaveTile_source.text
                dripTile_source = roof.find('dripTile_source')
                if dripTile_source != None:
                    tData.DRIPTILE_SOURCE = dripTile_source.text

                ridgeTop_source = roof.find('ridgeTop_source')
                if ridgeTop_source != None:
                    tData.RIDGETOP_SOURCE = ridgeTop_source.text
                ridgeBack_source = roof.find('ridgeBack_source')
                if ridgeBack_source != None:
                    tData.RIDGEBACK_SOURCE = ridgeBack_source.text
                ridgeFront_source = roof.find('ridgeFront_source')
                if ridgeFront_source != None:
                    tData.RIDGEFRONT_SOURCE = ridgeFront_source.text
                ridgeEnd_source = roof.find('ridgeEnd_source')
                if ridgeEnd_source != None:
                    tData.RIDGEEND_SOURCE = ridgeEnd_source.text

                bofeng_source = roof.find('bofeng_source')
                if bofeng_source != None:
                    tData.BOFENG_SOURCE = bofeng_source.text

                chiwen_source = roof.find('chiwen_source')
                if chiwen_source != None:
                    tData.CHIWEN_SOURCE = chiwen_source.text

                chuishou_source = roof.find('chuishou_source')
                if chuishou_source != None:
                    tData.CHUISHOU_SOURCE = chuishou_source.text

                taoshou_source = roof.find('taoshou_source')
                if taoshou_source != None:
                    tData.TAOSHOU_SOURCE = taoshou_source.text

                paoshou_0_source = roof.find('paoshou_0_source')
                if paoshou_0_source != None:
                    tData.PAOSHOU_0_SOURCE = paoshou_0_source.text
                paoshou_1_source = roof.find('paoshou_1_source')
                if paoshou_1_source != None:
                    tData.PAOSHOU_1_SOURCE = paoshou_1_source.text
                paoshou_2_source = roof.find('paoshou_2_source')
                if paoshou_2_source != None:
                    tData.PAOSHOU_2_SOURCE = paoshou_2_source.text
                paoshou_3_source = roof.find('paoshou_3_source')
                if paoshou_3_source != None:
                    tData.PAOSHOU_3_SOURCE = paoshou_3_source.text
                paoshou_4_source = roof.find('paoshou_4_source')
                if paoshou_4_source != None:
                    tData.PAOSHOU_4_SOURCE = paoshou_4_source.text
                paoshou_5_source = roof.find('paoshou_5_source')
                if paoshou_5_source != None:
                    tData.PAOSHOU_5_SOURCE = paoshou_5_source.text
                paoshou_6_source = roof.find('paoshou_6_source')
                if paoshou_6_source != None:
                    tData.PAOSHOU_6_SOURCE = paoshou_6_source.text
                paoshou_7_source = roof.find('paoshou_7_source')
                if paoshou_7_source != None:
                    tData.PAOSHOU_7_SOURCE = paoshou_7_source.text
                paoshou_8_source = roof.find('paoshou_8_source')
                if paoshou_8_source != None:
                    tData.PAOSHOU_8_SOURCE = paoshou_8_source.text
                paoshou_9_source = roof.find('paoshou_9_source')
                if paoshou_9_source != None:
                    tData.PAOSHOU_9_SOURCE = paoshou_9_source.text
                paoshou_10_source = roof.find('paoshou_10_source')
                if paoshou_10_source != None:
                    tData.PAOSHOU_10_SOURCE = paoshou_10_source.text
                
    return tData    

# 载入Blender中的资产
# 参考教程：https://b3d.interplanety.org/en/appending-all-objects-from-the-external-blend-file-to-the-scene-with-blender-python-api/
# 参考文档：https://docs.blender.org/api/current/bpy.types.BlendDataLibraries.html
def loadAssets(assetName : str,parent:bpy.types.Object,hide=True):
    #print("Loading " + assetName + '...')
    # 打开资产文件
    filepath = os.path.join(templateFolder, blenderFileName)

    # 简化做法，效率更高，但没有关联子对象
    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        data_to.objects = [name for name in data_from.objects if name.startswith(assetName)]
    for obj in data_to.objects:
        newobj = utils.copyObject(
            sourceObj=obj,
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

# 将模版参数填充入buildingObj节点中
def fillTemplate(buildingObj:bpy.types.Object,
                    template:templateData):
    # 映射template对象到ACA_data中
    bData = buildingObj.ACA_data
    bData['aca_obj'] = True
    bData['aca_type'] = con.ACA_TYPE_BUILDING
    bData['template'] = template.NAME
    bData['DK'] = template.DK
    bData['platform_height'] = template.PLATFORM_HEIGHT
    bData['platform_extend'] = template.PLATFORM_EXTEND
    bData['x_rooms'] = template.ROOM_X
    bData['x_1'] = template.ROOM_X1
    bData['x_2'] = template.ROOM_X2
    bData['x_3'] = template.ROOM_X3
    bData['x_4'] = template.ROOM_X4
    bData['y_rooms'] = template.ROOM_Y
    bData['y_1'] = template.ROOM_Y1
    bData['y_2'] = template.ROOM_Y2
    bData['y_3'] = template.ROOM_Y3
    bData['piller_height'] = template.PILLER_HEIGHT
    bData['piller_diameter'] = template.PD 
    bData['piller_net'] = template.PILLER_NET
    bData['wall_layout'] = template.WALL_LAYOUT
    bData['wall_style'] = template.WALL_STYLE
    bData['wall_net'] = template.WALL_NET
    bData['fang_net'] = template.FANG_NET
    bData['door_height'] = template.DOOR_HEIGHT
    bData['rafter_count'] = template.RAFTER_COUNT
    bData['roof_style'] = template.ROOF_STYLE
    bData['tile_width'] = template.TILE_WIDTH
    bData['tile_length'] = template.TILE_LENGTH

    # 绑定资产
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

    # 柱形样式
    if template.PILLER_SOURCE != "":
        piller_base:bpy.types.Object = \
            loadAssets(template.PILLER_SOURCE,assetsObj)
        bData['piller_source'] = piller_base
    # 墙体样式
    if template.WALL_SOURCE != "":
        wall_base:bpy.types.Object = \
            loadAssets(template.WALL_SOURCE,assetsObj)
        bData['wall_source'] = wall_base
    # 隔扇棂心样式
    if template.LINGXIN_SOURCE != "" :
        lingxin_base:bpy.types.Object = \
            loadAssets(template.LINGXIN_SOURCE,assetsObj)
        bData['lingxin_source'] = lingxin_base
    # 斗栱样式
    if template.USE_DG:
        bData['use_dg'] = True
        if template.DG_PILLER_SOURCE != "" :
            dg_piller_base:bpy.types.Object = \
                loadAssets(template.DG_PILLER_SOURCE,assetsObj)
            bData['dg_piller_source'] = dg_piller_base
        if template.DG_FILLGAP_SOURCE != "" :
            dg_fillgap_base:bpy.types.Object = \
                loadAssets(template.DG_FILLGAP_SOURCE,assetsObj)
            bData['dg_fillgap_source'] = dg_fillgap_base
        if template.DG_CORNER_SOURCE != "" :
            dg_corner_base:bpy.types.Object = \
                loadAssets(template.DG_CORNER_SOURCE,assetsObj)
            bData['dg_corner_source'] = dg_corner_base
    else:
        bData['use_dg'] = False
    # 瓦片样式
    if template.FLATTILE_SOURCE != "" :
        flatTile_source:bpy.types.Object = \
            loadAssets(template.FLATTILE_SOURCE,assetsObj)
        bData['flatTile_source'] = flatTile_source
    if template.CIRCULARTILE_SOURCE != "" :
        circularTile_source:bpy.types.Object = \
            loadAssets(template.CIRCULARTILE_SOURCE,assetsObj)
        bData['circularTile_source'] = circularTile_source
    if template.EAVETILE_SOURCE != "" :
        eaveTile_source:bpy.types.Object = \
            loadAssets(template.EAVETILE_SOURCE,assetsObj)
        bData['eaveTile_source'] = eaveTile_source
    if template.DRIPTILE_SOURCE != "" :
        dripTile_source:bpy.types.Object = \
            loadAssets(template.DRIPTILE_SOURCE,assetsObj)
        bData['dripTile_source'] = dripTile_source

    if template.RIDGETOP_SOURCE != "" :
        ridgeTop_source:bpy.types.Object = \
            loadAssets(template.RIDGETOP_SOURCE,assetsObj)
        bData['ridgeTop_source'] = ridgeTop_source
    if template.RIDGEBACK_SOURCE != "" :
        ridgeBack_source:bpy.types.Object = \
            loadAssets(template.RIDGEBACK_SOURCE,assetsObj)
        bData['ridgeBack_source'] = ridgeBack_source
    if template.RIDGEFRONT_SOURCE != "" :
        ridgeFront_source:bpy.types.Object = \
            loadAssets(template.RIDGEFRONT_SOURCE,assetsObj)
        bData['ridgeFront_source'] = ridgeFront_source
    if template.RIDGEEND_SOURCE != "" :
        ridgeEnd_source:bpy.types.Object = \
            loadAssets(template.RIDGEEND_SOURCE,assetsObj)
        bData['ridgeEnd_source'] = ridgeEnd_source
    
    if template.BOFENG_SOURCE != "" :
        bofeng_source:bpy.types.Object = \
            loadAssets(template.BOFENG_SOURCE,assetsObj)
        bData['bofeng_source'] = bofeng_source

    if template.CHIWEN_SOURCE != "" :
        chiwen_source:bpy.types.Object = \
            loadAssets(template.CHIWEN_SOURCE,assetsObj)
        bData['chiwen_source'] = chiwen_source
    
    if template.CHUISHOU_SOURCE != "" :
        chuishou_source:bpy.types.Object = \
            loadAssets(template.CHUISHOU_SOURCE,assetsObj)
        bData['chuishou_source'] = chuishou_source

    if template.TAOSHOU_SOURCE != "" :
        taoshou_source:bpy.types.Object = \
            loadAssets(template.TAOSHOU_SOURCE,assetsObj)
        bData['taoshou_source'] = taoshou_source

    if template.PAOSHOU_0_SOURCE != "" :
        paoshou_0_source:bpy.types.Object = \
            loadAssets(template.PAOSHOU_0_SOURCE,assetsObj)
        bData['paoshou_0_source'] = paoshou_0_source
    if template.PAOSHOU_1_SOURCE != "" :
        paoshou_1_source:bpy.types.Object = \
            loadAssets(template.PAOSHOU_1_SOURCE,assetsObj)
        bData['paoshou_1_source'] = paoshou_1_source
    if template.PAOSHOU_2_SOURCE != "" :
        paoshou_2_source:bpy.types.Object = \
            loadAssets(template.PAOSHOU_2_SOURCE,assetsObj)
        bData['paoshou_2_source'] = paoshou_2_source
    if template.PAOSHOU_3_SOURCE != "" :
        paoshou_3_source:bpy.types.Object = \
            loadAssets(template.PAOSHOU_3_SOURCE,assetsObj)
        bData['paoshou_3_source'] = paoshou_3_source
    if template.PAOSHOU_4_SOURCE != "" :
        paoshou_4_source:bpy.types.Object = \
            loadAssets(template.PAOSHOU_4_SOURCE,assetsObj)
        bData['paoshou_4_source'] = paoshou_4_source
    if template.PAOSHOU_5_SOURCE != "" :
        paoshou_5_source:bpy.types.Object = \
            loadAssets(template.PAOSHOU_5_SOURCE,assetsObj)
        bData['paoshou_5_source'] = paoshou_5_source
    if template.PAOSHOU_6_SOURCE != "" :
        paoshou_6_source:bpy.types.Object = \
            loadAssets(template.PAOSHOU_6_SOURCE,assetsObj)
        bData['paoshou_6_source'] = paoshou_6_source
    if template.PAOSHOU_7_SOURCE != "" :
        paoshou_7_source:bpy.types.Object = \
            loadAssets(template.PAOSHOU_7_SOURCE,assetsObj)
        bData['paoshou_7_source'] = paoshou_7_source
    if template.PAOSHOU_8_SOURCE != "" :
        paoshou_8_source:bpy.types.Object = \
            loadAssets(template.PAOSHOU_8_SOURCE,assetsObj)
        bData['paoshou_8_source'] = paoshou_8_source
    if template.PAOSHOU_9_SOURCE != "" :
        paoshou_9_source:bpy.types.Object = \
            loadAssets(template.PAOSHOU_9_SOURCE,assetsObj)
        bData['paoshou_9_source'] = paoshou_9_source
    if template.PAOSHOU_10_SOURCE != "" :
        paoshou_10_source:bpy.types.Object = \
            loadAssets(template.PAOSHOU_10_SOURCE,assetsObj)
        bData['paoshou_10_source'] = paoshou_10_source

# 根据panel中DK的改变，更新整体设计参数
def updateTemplateByDK(dk,buildingObj:bpy.types.Object):
    # 载入模版
    bData : acaData = buildingObj.ACA_data
    template_name = bData.template_name
    # 根据DK数据，重新计算模版参数
    template = getTemplate(template_name,dk)

    # 在根节点绑定模版数据
    fillTemplate(buildingObj,template)