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

# 解析XML，获取斗栱样式列表
# 配置如下
# <dg_piller_source type="List">
#     <item type='Object' style='斗口单昂'>斗口单昂.柱头科</item>
#     <item type='Object' style='斗口重昂'>斗口重昂.柱头科</item>
#     <item type='Object' style='单翘重昂'>单翘重昂.柱头科</item>
# </dg_piller_source>
def getDougongList(onlyname=False):
    dougong_list = []

    # 载入XML
    path = __getPath(assetsFileName)
    tree = ET.parse(path)
    # 根节点<assets>
    root = tree.getroot()
    # 查找“柱头科”配置
    dgPillerNode = root.find('dg_piller_source')
    if dgPillerNode != None:
        # 判断type属性
        type = dgPillerNode.attrib['type']
        if type == 'List':
            # 查找“item”子节点
            items = dgPillerNode.findall('item')
            for item in items:
                dgStyle = item.attrib['style']
                styleIndex = item.attrib['index']
                dougong_list.append(
                    (styleIndex,dgStyle,dgStyle)
                )
            
    return dougong_list

# 动态初始化斗栱属性和样式
# 根据当前建筑所定义的斗栱样式进行更新
# 在建筑新建、重新生成屋顶、单独生成斗栱层时，都应该使用此方法
def updateDougongData(buildingObj:bpy.types.Object):
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    if bData.aca_type != con.ACA_TYPE_BUILDING:
        utils.showMessageBox("错误，输入的不是建筑根节点")
        return
    
    # 1、根据斗栱样式，更新对应斗栱资产模版
    # 1.1、验证斗栱样式非空，否则默认取第一个
    if 'dg_style' not in bData:
        bData['dg_style'] = '0'
    
    # 1.2、更新aData中的斗栱样式
    __updateAssetStyle(
        buildingObj,'dg_piller_source')
    __updateAssetStyle(
        buildingObj,'dg_fillgap_source')
    __updateAssetStyle(
        buildingObj,'dg_fillgap_alt_source')
    __updateAssetStyle(
        buildingObj,'dg_corner_source')
    if (aData.dg_piller_source == None
            or aData.dg_fillgap_source == None
            or aData.dg_fillgap_alt_source == None
            or aData.dg_corner_source == None):
        utils.outputMsg("斗栱配置不完整，请检查")
        return
    
    # 2、更新bData中的斗栱配置参数
    # 包括dg_height,dg_extend,dgScale

    # 2.1、dg_scale: 根据斗口设置进行缩放，参考斗口为二寸五0.08cm
    dgScale = bData.DK / con.DEFAULT_DK
    bData['dg_scale'] = (dgScale,dgScale,dgScale)

    # 2.2、dg_height,dg_extend
    # 仅以柱头斗栱为依据，
    # 在blender中应该提前给柱头斗栱定义好dgHeight和dgExtend属性
    dgObj = aData.dg_piller_source
    # 防止无法载入斗栱时的崩溃
    if dgObj == None:
        utils.outputMsg('无法读取斗栱挑高和出跳数据')
        return
    if 'dgHeight' in dgObj:
        bData['dg_height'] = dgObj['dgHeight']*dgScale
    else:
        utils.outputMsg("斗栱未定义默认高度")
    if 'dgExtend' in dgObj:
        bData['dg_extend'] = dgObj['dgExtend']*dgScale
    else:
        utils.outputMsg("斗栱未定义默认出跳")

    return

# 更新资产样式
def __updateAssetStyle(buildingObj:bpy.types.Object,
                     assetName=''): 
    # 载入数据
    bData:acaData = buildingObj.ACA_data  
    aData : tmpData = bpy.context.scene.ACA_temp
    # 载入XML
    path = __getPath(assetsFileName)
    tree = ET.parse(path)
    # 根节点<assets>
    root = tree.getroot()
    # 查找配置
    assetNode = root.find(assetName)
    if assetNode != None:
        # 判断type属性
        type = assetNode.attrib['type']
        if type == 'List':
            # 获取样式定义，是指bData中定义的变量名称
            styleKey = assetNode.attrib['key']
            # 有些配置可能太老，导致部分styleKey缺失
            if styleKey in bData:
                # styleValue为了样式下拉框能自动选中，
                # 在载入样式时自动转为了int，这里要转为str与xml比较
                styleValue = str(bData[styleKey])   
                # 查找“item”子节点
                items = assetNode.findall('item')
                for item in items:
                    dgStyleIndex = item.attrib['index']
                    if dgStyleIndex == styleValue:
                        # 250104 为了解决以下报错，做的安全性验证
                        # 似乎是4.2中做了一个Breaking changes：Statically Typed IDProperties
                        # https://developer.blender.org/docs/release_notes/4.2/python_api/#statically-typed-idproperties
                        # TypeError: Cannot assign a 'Object' value to the existing 'dg_piller_source' Group IDProperty
                        if assetName in aData:  
                            del aData[assetName] 
                        aData[assetName] = loadAssets(item.text)
    return

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
        data_to.objects = [name for name in data_from.objects if name==assetName]
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

# 填充资产对象的引用aData
# aData中仅为对模版xx.blend文件中对象的引用
# aData根据bData中定义的dgStyle等属性的不同而动态改变
# aData绑定在Blender的Scene场景中，未做建筑间隔离
# 在更新斗栱时，修改了aData中涉及斗栱的属性
def __loadAssetByBuilding(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
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
        # 静态的模版对象声明为Object
        # 动态的模版对象声明为List，
        # 不在这里处理，而拆分到类似updateDougongData的定制方法中处理
        if type == 'Object':
            # 241224 为了解决以下报错，做的安全性验证
            # 似乎是4.2中做了一个Breaking changes：Statically Typed IDProperties
            # https://developer.blender.org/docs/release_notes/4.2/python_api/#statically-typed-idproperties
            # TypeError: Cannot assign a 'Object' value to the existing 'mat_wood' Group IDProperty
            if tag in aData:  
                del aData[tag]  
            aData[tag] = loadAssets(value)

    # 3、其他个性化处理
    # 提取斗栱自定义属性，填充入bData
    # 如，bData.dg_height，bData.dg_extend，bData.dg_scale
    updateDougongData(buildingObj)
    
    return

# 载入模版
# 直接将XML填充入bData
# 注意，所有的属性都为选填，所以要做好空值的检查
def loadTemplate(buildingObj:bpy.types.Object):
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
    templateName = bData.template_name
    
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
                    bData['DK'] = round(float(dk.text),3)
                # 柱径
                pd = template.find('piller_diameter')
                if pd != None:
                    bData['piller_diameter'] = round(float(pd.text),3)
                # 刷新bData默认值
                bData = __loadDefaultData(buildingObj)

                # 遍历所有子节点，并绑定到对应属性
                for node in template:
                    tag = node.tag
                    type = node.attrib['type']
                    value = node.text
                    # 类型转换
                    if type == 'str':
                        # 特殊处理下拉框
                        if tag in ('roof_style',
                                   'juzhe',
                                   'dg_style'):
                            bData[tag] = int(value)
                        else:
                            bData[tag] = value
                    elif type == 'float':
                        bData[tag] = round(float(value),3)
                    elif type == 'int':
                        bData[tag] = int(value)
                    elif type == 'bool':
                        # 注意这里的True/False是str，用bool()强制转换时都为True，
                        # 所以以下手工进行了判断
                        if value == 'True':
                            bData[tag] = True
                        if value == 'False':
                            bData[tag] = False
                    else:
                        print("can't convert:",node.tag, node.attrib['type'],node.text)

    # 填充建筑使用的资产对象，根据其中的dg_style等不同，载入不同的资产样式
    __loadAssetByBuilding(buildingObj)
    
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
        # 浮点数取3位精度
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