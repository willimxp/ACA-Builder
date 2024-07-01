# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   管理模版
import bpy
import pathlib
import xml.etree.ElementTree as ET
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from .data import ACA_data_template as tmpData
from . import utils


xmlFileName = 'simplyhouse.xml'
blenderFileName = 'acaAssets.blend'
assetsFileName = 'assetsIndex.xml'

# 组合绝对路径
# https://blender.stackexchange.com/questions/253722/blender-api-how-to-distribute-an-add-on-with-assets-and-how-to-append-them-with
def __getPath(fileName):
    addonName = "ACA Builder"
    templateFolder = 'template'
    USER = pathlib.Path(
        bpy.utils.resource_path('USER'))
    srcPath = USER / "scripts/addons" / addonName / templateFolder / fileName
    return str(srcPath)

# 解析XML，获取模版列表
def getTemplateList(onlyname=False):
    # 载入XML
    # 这个结果打包发布后出现错误，改为绝对路径
    # path = os.path.join(templateFolder, xmlFileName)
    path = __getPath(xmlFileName)
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
def loadAssets(assetName : str,
               parent:bpy.types.Object=None,
               hide=True,
               link=True):   
    # 打开资产文件
    filepath = __getPath(blenderFileName)

    # 简化做法，效率更高，但没有关联子对象
    with bpy.data.libraries.load(filepath,link=True) as (data_from, data_to):
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
        # bpy.context.collection.objects.link(sourceObj)
        return sourceObj
    else:
        # 返回一个复制的新对象
        newobj = utils.copyObject(
            sourceObj=sourceObj,
            parentObj=parent,
            singleUser=True
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

# 填充资产库对象索引
def openAssets():
    # 载入数据
    aData : tmpData = bpy.context.scene.ACA_temp

    # 解析XML配置模版
    path = __getPath(assetsFileName)
    tree = ET.parse(path)
    root = tree.getroot()
    
    # 填充
    for node in root:
        tag = node.tag
        type = node.attrib['type']
        value = node.text
        if type == 'Object':
            aData[tag] = loadAssets(value)
    
    return
    

# 载入模版
# 直接将XML填充入bData
# 注意，所有的属性都为选填，所以要做好空值的检查
def openTemplate(buildingObj:bpy.types.Object,
                 templateName:str):
    # 解析XML配置模版
    path = __getPath(xmlFileName)
    tree = ET.parse(path)
    root = tree.getroot()
    templates = root.findall('template')
    if templates == None:
        utils.outputMsg("模版解析失败")
        return
    
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    
    # 在XML中查找对应名称的那个模版
    for template in templates:
        nameNode = template.find('template_name')
        if nameNode != None:
            if nameNode.text == templateName:
                # 初始化bData默认值，根据DK/PD实时刷新一次
                # 模版名称
                bData['template_name'] = nameNode.text
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
                        if tag in ('roof_style',
                                   'juzhe'):
                            bData[tag] = int(value)
                    elif type == 'float':
                        bData[tag] = round(float(value),2)
                    elif type == 'int':
                        bData[tag] = int(value)
                    elif type == 'bool':
                        # 注意这里的True/False是str，用bool()强制转换时都为True，
                        # 所以以下手工进行了判断
                        if value == 'True':
                            bData[tag] = True
                        if value == 'False':
                            bData[tag] = False
                    elif type == 'Object':
                        bData[tag] = loadAssets(value)
                    else:
                        print("can't convert:",node.tag, node.attrib['type'],node.text)

    # 填充资产库对象索引
    openAssets()
    
    return

# 保存模版修改
def saveTemplate(buildingObj:bpy.types.Object):
    # 载入输入
    bData:acaData = buildingObj.ACA_data
    # 模版名称取当前建筑的名称
    templateName = buildingObj.name

    # 忽略处理的节点
    ignoreKeys = {
        # 辅助参数，无需处理
        'aca_obj',
        'x_total',
        'y_total',
        'wall_layout',
        'wall_style',
        'roof_qiao_point',
        'tile_width_real',
        'dg_scale',
    }
    
    # 解析XML配置模版
    path = __getPath(xmlFileName)
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
            value = round(value,3)
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

    return {'FINISHED'}

# 删除模版
def delTemplate():
    # 解析XML配置模版
    path = __getPath(xmlFileName)
    tree = ET.parse(path)
    root = tree.getroot()   # <templates>根节点
    # 验证根节点
    templateNodeList = root.findall('template')
    if templateNodeList == None:
        utils.outputMsg("模版解析失败")
        return
    
    # 遍历查找对应模版
    # 模版名称取panel上选择的模版
    templateName = bpy.context.scene.ACA_data.template
    bFind = False
    nextTemplateName = ''
    preTemplateName = ''
    for templateNode in templateNodeList:
        nameNode = templateNode.find('template_name')
        if nameNode != None:
            # 判断标志位，以暂存下一个选项
            if not bFind:
                if nameNode.text != templateName:
                    # 未找到之前，暂存为上一个选项
                    preTemplateName = nameNode.text
                else:
                    # 如果找到了对应名称
                    # 删除模版
                    root.remove(templateNode)
                    # 更新标志位，进入下一次循环
                    # 以便填充nextTemplateName
                    bFind = True
            else:
                # 暂存下一个选项
                nextTemplateName = nameNode.text
                break

    # 缩进美化
    # https://stackoverflow.com/questions/28813876/how-do-i-get-pythons-elementtree-to-pretty-print-to-an-xml-file
    ET.indent(tree, space="\t", level=0)
    # 保存
    tree.write(path, encoding='UTF-8',xml_declaration=True)

    # 刷新panel的模版列表
    if nextTemplateName != '':
        # 优先绑定下一个选项
        bpy.context.scene.ACA_data.template = nextTemplateName
    elif preTemplateName != '':
        # 候选上一个选项
        bpy.context.scene.ACA_data.template = preTemplateName
    # 如果都为空，则不做绑定

    return {'FINISHED'}