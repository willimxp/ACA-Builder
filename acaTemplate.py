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
from . import acaLibrary

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
    PILLER_STYLE  = ""          # 柱样式
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
    DG_PILLER_SOURCE = ''       # 柱头斗栱
    DG_FILLGAP_SOURCE = ''      # 补间斗栱
    DG_CORNER_SOURCE = ''       # 转角斗栱

# 解析XML，获取模版列表
def getTemplateList():
    # 载入XML
    path = os.path.join('template', 'simplyhouse.xml')
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
    path = os.path.join('template', 'simplyhouse.xml')
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
            piller = template.find('piller')
            if piller != None:
                pillerD = piller.find('dimeter')
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
            piller = template.find('piller')
            if piller != None:
                pillerHeight = piller.find('height')
                if pillerHeight != None:
                    tData.PILLER_HEIGHT = float(pillerHeight.text)
                pillerStyle = piller.find('style')
                if pillerStyle != None:
                    tData.PILLER_STYLE = pillerStyle.text

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
            wall = template.find('wall')
            if wall != None:
                layout = wall.find('layout')
                if layout != None:
                    tData.WALL_LAYOUT = int(layout.text)
                style = wall.find('style')
                if style != None:
                    tData.WALL_STYLE = int(style.text)
                wall_source = wall.find('wall_source')
                if wall_source != None:
                    tData.WALL_SOURCE = wall_source.text
                lingxin_source = wall.find('lingxin_source')
                if lingxin_source != None:
                    tData.LINGXIN_SOURCE = lingxin_source.text
            
            # 斗栱
            dg = template.find('dougong')
            if dg != None:
                piller_source = dg.find('piller_source')
                if piller_source != None:
                    tData.DG_PILLER_SOURCE = piller_source.text
                fillgap_source = dg.find('fillgap_source')
                if fillgap_source != None:
                    tData.DG_FILLGAP_SOURCE = fillgap_source.text
                corner_source = dg.find('corner_source')
                if corner_source != None:
                    tData.DG_CORNER_SOURCE = corner_source.text
                
    
    return tData    

# 将模版参数填充入buildingObj节点中
def fillTemplate(buildingObj:bpy.types.Object,
                    template:templateData):
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
    buildingData['piller_diameter'] = template.PD 
    buildingData['wall_layout'] = template.WALL_LAYOUT
    buildingData['wall_style'] = template.WALL_STYLE
    buildingData['door_height'] = template.DOOR_HEIGHT

    # 绑定资产
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    assetsObj = bpy.context.object
    assetsObj.location = buildingObj.location   # 原点摆放在3D Cursor位置
    assetsObj.parent = buildingObj
    assetsObj.name = 'assets'   # 系统遇到重名会自动添加00x的后缀
    # 柱形样式
    if template.PILLER_STYLE != "":
        piller_base:bpy.types.Object = \
            acaLibrary.loadAssets(template.PILLER_STYLE,assetsObj)
        buildingData['piller_source'] = piller_base
    # 墙体样式
    if template.WALL_SOURCE != "":
        wall_base:bpy.types.Object = \
            acaLibrary.loadAssets(template.WALL_SOURCE,assetsObj)
        buildingData['wall_source'] = wall_base
    # 隔扇棂心样式
    if template.LINGXIN_SOURCE != "" :
        lingxin_base:bpy.types.Object = \
            acaLibrary.loadAssets(template.LINGXIN_SOURCE,assetsObj)
        buildingData['lingxin_source'] = lingxin_base
    # 柱头斗栱样式
    if template.DG_PILLER_SOURCE != "" :
        dg_piller_base:bpy.types.Object = \
            acaLibrary.loadAssets(template.DG_PILLER_SOURCE,assetsObj)
        buildingData['dg_piller_source'] = dg_piller_base
    if template.DG_FILLGAP_SOURCE != "" :
        dg_fillgap_base:bpy.types.Object = \
            acaLibrary.loadAssets(template.DG_FILLGAP_SOURCE,assetsObj)
        buildingData['dg_fillgap_source'] = dg_fillgap_base
    if template.DG_CORNER_SOURCE != "" :
        dg_corner_base:bpy.types.Object = \
            acaLibrary.loadAssets(template.DG_CORNER_SOURCE,assetsObj)
        buildingData['dg_corner_source'] = dg_corner_base

# 根据panel中DK的改变，更新整体设计参数
def updateTemplateByDK(dk,buildingObj:bpy.types.Object):
    # 载入模版
    bData : acaData = buildingObj.ACA_data
    template_name = bData.template_name
    # 根据DK数据，重新计算模版参数
    template = getTemplate(template_name,dk)

    # 在根节点绑定模版数据
    fillTemplate(buildingObj,template)