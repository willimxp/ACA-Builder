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
                    tData.PILLER_D = float(pillerD.text)
                pillerHeight = piller.find('height')
                if pillerHeight != None:
                    tData.PILLER_HEIGHT = float(pillerHeight.text)
            
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

# 根据panel中DK的改变，更新整体设计参数
def updateTemplateByDK(dk,buildingObj:bpy.types.Object):
    # 载入模版
    bData : acaData = buildingObj.ACA_data
    template_name = bData.template_name
    # 根据DK数据，重新计算模版参数
    template = getTemplate(template_name,dk)

    # 在根节点绑定模版数据
    fillTemplate(buildingObj,template)