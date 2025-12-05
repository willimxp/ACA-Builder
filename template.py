# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   管理模板
import bpy
import os
import pathlib
import xml.etree.ElementTree as ET
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from .data import ACA_data_template as tmpData
from . import utils
import bpy.utils.previews


xmlFileName = 'template.xml'
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

# 解析XML，获取模板列表
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

# 根据选择的模板，获取模板类型（房屋、院墙）
def getBuildingType(templateName):
    # 载入XML
    # 这个结果打包发布后出现错误，改为绝对路径
    # path = os.path.join(templateFolder, xmlFileName)
    path = __getPath(xmlFileName)
    tree = ET.parse(path)
    root = tree.getroot()
    templates = root.findall('template')

    # 有些模板没有这个类型值，默认置为普通building
    typeName = con.ACA_TYPE_BUILDING

    template_list = []
    for template in templates:
        tname = template.find('template_name')
        if  tname.text == templateName:
            typeNode = template.find('aca_type')
            if typeNode != None:
                typeName = typeNode.text
            break
            
    return typeName

# 解析XML，获取斗栱样式列表
# 配置如下
# <dg_piller_source type="List">
#     <item type='Object' style='斗口单昂'>斗口单昂.柱头科</item>
#     <item type='Object' style='斗口重昂'>斗口重昂.柱头科</item>
#     <item type='Object' style='单翘重昂'>单翘重昂.柱头科</item>
# </dg_piller_source>
def getDougongList():
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
            for n,item in enumerate(items):
                dgStyle = item.attrib['style']
                dougong_list.append(
                    (str(n),dgStyle,dgStyle)
                )
            
    return dougong_list

# 动态初始化斗栱属性和样式
# 根据当前建筑所定义的斗栱样式进行更新
# 在建筑新建、重新生成屋顶、单独生成斗栱层时，都应该使用此方法
def updateDougongData(buildingObj:bpy.types.Object,
                      reloadAssets = True):
    buildingObj,bData,oData = utils.getRoot(buildingObj)
    # 载入数据
    bData : acaData = buildingObj.ACA_data
    aData:tmpData = bpy.context.scene.ACA_temp
    if bData.aca_type != con.ACA_TYPE_BUILDING:
        if bData.combo_type == con.COMBO_ROOT:
            # comboRoot节点无需更新斗栱数据
            utils.outputMsg("组合建筑根节点，无需更新斗栱数据")
            return
        if bData.aca_type == con.ACA_TYPE_YARDWALL:
            utils.outputMsg("院墙，无需更新斗栱数据")
            return
        else:
            raise Exception("更新斗栱数据异常，输入的不是建筑根节点")
    dgrootObj = utils.getAcaChild(
        buildingObj,con.ACA_TYPE_DG_ROOT)
    if dgrootObj == None:       
        # 设置目录
        buildingColl = buildingObj.users_collection[0]
        utils.setCollection(
            con.COLL_NAME_DOUGONG,
            parentColl=buildingColl) 

        # 计算位置
        bData : acaData = buildingObj.ACA_data
        zLoc = bData.platform_height + bData.piller_height 
        # 创建根对象（empty）
        dgrootObj = utils.addEmpty(
            name=con.COLL_NAME_DOUGONG,
            parent=buildingObj,
            location=(0,0,zLoc),)
        dgrootObj.ACA_data['aca_obj'] = True
        dgrootObj.ACA_data['aca_type'] = con.ACA_TYPE_DG_ROOT
    
    # 临时切换到斗栱目录
    preColl = bpy.context.view_layer.active_layer_collection.name
    utils.focusCollByObj(dgrootObj)
    
    # 1、根据斗栱样式，更新对应斗栱资产模板
    # 1.1、验证斗栱样式非空，否则默认取第一个
    if 'dg_style' not in bData:
        bData['dg_style'] = '0'
    
    # 1.2、更新aData中的斗栱样式
    if reloadAssets:
        __updateAssetStyle(
            buildingObj,'dg_piller_source',
            parent=dgrootObj)
        __updateAssetStyle(
            buildingObj,'dg_fillgap_source',
            parent=dgrootObj)
        __updateAssetStyle(
            buildingObj,'dg_fillgap_alt_source',
            parent=dgrootObj)
        __updateAssetStyle(
            buildingObj,'dg_corner_source',
            parent=dgrootObj)
        __updateAssetStyle(
            buildingObj,'dg_balcony_piller_source',
            parent=dgrootObj)
        __updateAssetStyle(
            buildingObj,'dg_balcony_corner_source',
            parent=dgrootObj)
        __updateAssetStyle(
            buildingObj,'dg_balcony_fillgap_source',
            parent=dgrootObj)
        __updateAssetStyle(
            buildingObj,'dg_balcony_fillgap_alt_source',
            parent=dgrootObj)
        if (aData.dg_piller_source == None
                or aData.dg_fillgap_source == None
                or aData.dg_fillgap_alt_source == None
                or aData.dg_corner_source == None
                # or aData.dg_balcony_piller_source == None
                ):
            raise Exception("斗栱配置不完整，请检查")
    
    # 2、更新bData中的斗栱配置参数
    # 包括dg_height,dg_extend,dgScale

    # 2.1、dg_scale: 根据斗口设置进行缩放，参考斗口为二寸五0.08cm
    dgScale = bData.DK / con.DEFAULT_DK * bData.dk_scale
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
    # 250831 新增斗栱是否与大梁连做
    if 'dgWithBeam' in dgObj:
        bData['dg_withbeam'] = dgObj['dgWithBeam']
    else:
        utils.outputMsg("斗栱未定义默认出跳")

    # 250902 如果屋顶为平坐，且有平坐斗栱，覆盖dgHeight
    if (bData.roof_style == con.ROOF_BALCONY and 
        aData.dg_balcony_piller_source != None):
        dgObj = aData.dg_balcony_piller_source
        if 'dgHeight' in dgObj:
            bData['dg_height'] = dgObj['dgHeight']*dgScale

    # print(f"斗栱数据已更新：dgHeight={bData.dg_height},dgExtend={bData.dg_extend}")

    # 恢复原有目录
    utils.focusCollection(preColl)

    return

# 更新资产样式
def __updateAssetStyle(buildingObj:bpy.types.Object,
                     assetName='',
                     parent=None): 
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
                styleValue = int(bData[styleKey])
                # 查找“item”子节点
                items = assetNode.findall('item')
                for n,item in enumerate(items):
                    if n == styleValue:
                        # 250104 为了解决以下报错，做的安全性验证
                        # 似乎是4.2中做了一个Breaking changes：Statically Typed IDProperties
                        # https://developer.blender.org/docs/release_notes/4.2/python_api/#statically-typed-idproperties
                        # TypeError: Cannot assign a 'Object' value to the existing 'dg_piller_source' Group IDProperty
                        if assetName in aData:  
                            # 250907 删除老资产对象
                            utils.deleteHierarchy(aData[assetName],del_parent=True)
                            # del aData[assetName]
                            
                        # 个性化样式资产，不采用link方式，而是复制到各个建筑内
                        aData[assetName] = loadAssets(
                            item.text,link=False,parent=parent)
    return

# 载入Blender中的资产
# 参考教程：https://b3d.interplanety.org/en/appending-all-objects-from-the-external-blend-file-to-the-scene-with-blender-python-api/
# 参考文档：https://docs.blender.org/api/current/bpy.types.BlendDataLibraries.html
def loadAssets(assetName : str,
               parent:bpy.types.Object=None,
               hide=True,
               link=True):   
    import os
    # 查找默认插件目录下的素材库
    filepath = __getPath(blenderFileName)
    # 如果找不到文件，尝试查找用户自定义路径
    if not os.path.exists(filepath):
        # 查找用户自定义路径
        preferences = bpy.context.preferences
        addon_main_name = __name__.split('.')[0]
        addon_prefs = preferences.addons[addon_main_name].preferences
        filepath = addon_prefs.filepath    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"无法打开资产库，请确认已经按照使用手册，关联了acaAssets.blend文件。")   

    # 简化做法，效率更高，但没有关联子对象
    try:
        with bpy.data.libraries.load(filepath,link=link) as (data_from, data_to):
            data_to.objects = [name for name in data_from.objects if name==assetName]
    except OSError:
        raise Exception('无法打开资产库，请确认acaAssets.blend文件已经放入插件目录')
    # 验证找到的资产是否唯一
    if len(data_to.objects) == 0:
        raise Exception(f"资产[{assetName}]载入失败，请检查是否关联最新版本的acaAssets.blend资产库。")
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
    return bData

# 填充资产对象的引用aData
# aData中仅为对模板xx.blend文件中对象的引用
# aData根据bData中定义的dgStyle等属性的不同而动态改变
# aData绑定在Blender的Scene场景中，未做建筑间隔离
# 在更新斗栱时，修改了aData中涉及斗栱的属性
def loadAssetByBuilding(buildingObj:bpy.types.Object):
    utils.outputMsg("重新载入素材库...")
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    aData : tmpData = bpy.context.scene.ACA_temp

    # 解析XML配置模板
    path = __getPath(assetsFileName)
    tree = ET.parse(path)
    root = tree.getroot()
    
    # 填充
    for node in root:
        tag = node.tag
        type = node.attrib['type']
        value = node.text
        # 静态的模板对象声明为Object
        # 动态的模板对象声明为List，
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
    # 250902 在“更新建筑”时，及时更新一次斗栱数据
    # 以便反应平坐斗栱的挑高与柱头斗栱挑高的变化
    updateDougongData(buildingObj)
    
    return

def getTemplateChild(templateName):
    path = __getPath(xmlFileName)
    tree = ET.parse(path)
    root = tree.getroot()
    templates = root.findall('template')

    tempChildren = []
    for template in templates:
        tname = template.find('template_name')
        if tname == None: 
            continue
        if tname.text == templateName:
            children = template.findall('template')
            for child in children:
                tname = child.find('template_name')
                ttype = child.find('aca_type')
                tempChildren.append(
                    {
                        'templateName': tname.text,
                        'acaType' : ttype.text,
                    }
                )
    return tempChildren

def __loadTemplateSingle(
        buildingObj:bpy.types.Object,
        template,
    ):    
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    
    # 初始化bData默认值，根据DK/PD实时刷新一次
    # 斗口
    dk = template.find('DK')
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
        # 针对combo模板，跳过子模板解析
        if node.tag == 'template':
            continue

        # 251205 不使用模板中存在的aca_id，维持对象随机生成
        if node.tag == 'aca_id':continue
        
        tag = node.tag
        type = node.attrib['type']
        value = node.text
        # 读取集合配置
        if type == 'CollectionProperty':
            for subnode in node:
                # 在bDate.xxxList下新建子节点
                subitem = getattr(bData,tag).add()
                # 循环载入该子节点的配置项
                for subsubNode in subnode:
                    subtag,subvalue = __readNode(subsubNode)
                    subitem[subtag] = subvalue
        else:
            tag,value = __readNode(node)
            bData[tag] = value

    # 填充建筑使用的资产对象，根据其中的dg_style等不同，载入不同的资产样式
    loadAssetByBuilding(buildingObj)

    return

# 载入模板
# 直接将XML填充入bData
# 注意，所有的属性都为选填，所以要做好空值的检查
def loadTemplate(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    templateName = bData.template_name
    
    # 解析XML配置模板
    path = __getPath(xmlFileName)
    tree = ET.parse(path)
    root = tree.getroot()
    
    # 读取所有根节点模板
    templateNodeList = root.findall('template')
    if templateNodeList == None:
        raise Exception("模板解析失败")
        return
    
    # 查找是否有子模版
    parent = buildingObj.parent
    if parent is not None:
        isComboNode = False
        # 遍历查找对应的combo节点
        for templateNode in templateNodeList:
            nameNode = templateNode.find('template_name')
            if nameNode != None:
                if nameNode.text == parent.ACA_data.template_name:
                    # 找到对应模板
                    isComboNode = True
                    break
        if isComboNode:
            # 把combo父节点装载入templateNodeList
            # 供下面的循环遍历
            root = templateNode
            templateNodeList = root.findall('template')
        else:
            raise Exception(f"找不到父模板{parent.name}，无法载入子模版")
    
    # 在根层次中查找对应名称的那个模板
    for template in templateNodeList:
        # 查看是否有子模版
        nameNode = template.find('template_name')
        if nameNode != None:
            if nameNode.text == templateName:
                __loadTemplateSingle(
                    buildingObj,template)
                return
                    
    # 经过经过以上循环，没有符合条件的模板，抛出异常
    raise Exception('无法载入模板')

# 保存带Combo的组合模板
def saveTemplateWithCombo(buildingObj:bpy.types.Object):
    # 载入输入
    bData:acaData = buildingObj.ACA_data

    # 保存单体模板
    if bData.aca_type in (
        con.ACA_TYPE_BUILDING,
        con.ACA_TYPE_YARDWALL):
        __saveTemplate(buildingObj)
        return {'FINISHED'}
    
    # 验证是否为组合模板
    if bData.aca_type != con.ACA_TYPE_COMBO:
        raise Exception("f保存模板失败，未知的建筑类型{bData.aca_type}")
        return {'CANCELLED'}
    comboObj = buildingObj
    
    # 保存组合模板-----------------------
    # 解析XML配置模板
    path = __getPath(xmlFileName)
    tree = ET.parse(path)
    root = tree.getroot()   # <templates>根节点
    # 验证根节点
    templateNodeList = root.findall('template')
    if templateNodeList == None:
        utils.outputMsg("模板解析失败")
        return
    
    # 遍历查找对应的combo节点
    templateName = comboObj.name
    isNewTemplate = True
    for templateNode in templateNodeList:
        nameNode = templateNode.find('template_name')
        if nameNode != None:
            if nameNode.text == templateName:
                # 找到对应模板
                isNewTemplate = False
                break
    # 如果没有找到，则新建combo节点
    if isNewTemplate:
        # 将根节点bData存入模板
        __saveTemplate(comboObj)

    # 保存子模板
    for buildingObj in comboObj.children:
        # 不在模板中保存合并的建筑对象
        if buildingObj.ACA_data.aca_type != \
            con.ACA_TYPE_BUILDING_JOINED:
            __saveTemplate(buildingObj)

    return {'FINISHED'}

# 保存模板修改
def __saveTemplate(buildingObj:bpy.types.Object):
    # 载入输入
    bData:acaData = buildingObj.ACA_data
    # 模板名称取当前建筑的名称
    templateName = buildingObj.name

    # 忽略处理的节点
    ignoreKeys = {
        # 辅助参数，无需处理
        'aca_id', # 251205 不在模板中保存建筑id，维持随机生成
        'aca_obj',
        'wall_layout',
        'roof_qiao_point',
        'tile_width_real',
        'dg_scale',
    }
    
    # 解析XML配置模板
    path = __getPath(xmlFileName)
    tree = ET.parse(path)
    root = tree.getroot()   # <templates>根节点
    # 验证根节点
    templateNodeList = root.findall('template')
    if templateNodeList == None:
        utils.outputMsg("模板解析失败")
        return
    
    # 查找是否有子模版
    parent = buildingObj.parent
    if parent is not None:
        isComboNode = False
        # 遍历查找对应的combo节点
        for templateNode in templateNodeList:
            nameNode = templateNode.find('template_name')
            if nameNode != None:
                if nameNode.text == parent.name:
                    # 找到对应模板
                    isComboNode = True
                    break
        if isComboNode:
            # 把combo父节点装载入templateNodeList
            # 供下面的循环遍历
            root = templateNode
            templateNodeList = root.findall('template')
        else:
            raise Exception(f"找不到父模板{parent.name}，无法保存子模版")
            return
    
    # 遍历查找对应模板
    isNewTemplate = True
    for templateNode in templateNodeList:
        nameNode = templateNode.find('template_name')
        if nameNode != None:
            if nameNode.text == templateName:
                # 找到对应模板
                isNewTemplate = False
                break
    # 如果没有找到，则新建模板节点
    if isNewTemplate:
        templateNode = ET.SubElement(root,'template')

    # 遍历bData，保存所有的键值
    # https://blender.stackexchange.com/questions/72402/how-to-iterate-through-a-propertygroup
    # for key in bData.__annotations__.keys():
    # 250826 为了能够获取继承的属性，改为使用bl_rna
    for prop in bData.bl_rna.properties:
        if not prop.is_runtime: continue
        key = prop.identifier
        keyType = prop.rna_type.identifier
        value = getattr(bData, key)        

        # 数据验证和预处理
        # 忽略无需保存的键值
        if key in ignoreKeys: continue
        # 以当前建筑名称覆盖模板名称
        if key == 'template_name':
            value = templateName
        # 浮点数取3位精度
        if keyType == 'FloatProperty':
            value,keyType = __float2xml(value,keyType)
        # 对象引用类型，保存对象名称
        if keyType == 'PointerProperty':
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
        # print(f"key={key} keyType={keyType}")

        # 集合类型，保存子对象
        if keyType == 'CollectionProperty':
            # 清空旧的子节点
            keyNode.clear()
            keyNode.attrib['type'] = keyType

            # 重建子节点
            for idx, item in enumerate(value):
                # 添加子对象，根据index判断是否存在
                # 避免多次保存时，产生了重复数据
                itemNode = keyNode.find(f'item_{idx}')
                if itemNode is None:
                    itemNode = ET.SubElement(keyNode, f'item_{idx}')
                    itemNode.attrib['type'] = 'item'

                # 递归遍历 item 的属性
                for subprop in item.bl_rna.properties:
                    if not subprop.is_runtime: continue
                    subkey = subprop.identifier
                    subkeyType = subprop.rna_type.identifier
                    subvalue = getattr(item, subkey)
                    # 浮点数取3位精度
                    if subkeyType == 'FloatProperty':
                        subvalue,subkeyType =  __float2xml(subvalue,subkeyType)                    
                    subkeyNode = itemNode.find(subkey)
                    if subkeyNode is None:
                        subkeyNode = ET.SubElement(itemNode, subkey)
                    subkeyNode.text = str(subvalue)
                    subkeyNode.attrib['type'] = subkeyType

    # 缩进美化
    # https://stackoverflow.com/questions/28813876/how-do-i-get-pythons-elementtree-to-pretty-print-to-an-xml-file
    ET.indent(tree, space="\t", level=0)
    # 保存
    tree.write(path, encoding='UTF-8',xml_declaration=True)

    return {'FINISHED'}

# 删除模板
def delTemplate(templateName):
    # 解析XML配置模板
    path = __getPath(xmlFileName)
    tree = ET.parse(path)
    root = tree.getroot()   # <templates>根节点
    # 验证根节点
    templateNodeList = root.findall('template')
    if templateNodeList == None:
        utils.outputMsg("模板解析失败")
        return
    
    # 遍历查找对应模板
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
                    # 删除模板
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

    return {'FINISHED'}

# 载入缩略图，必须结合静态的集合操作
preview_collections = {}
def loadThumb():
    # 定义缩略图目录
    addonName = "ACA Builder"
    thumbFolder = 'thumb'
    USER = pathlib.Path(
        bpy.utils.resource_path('USER'))
    thumb_directory = USER / "scripts/addons" / addonName / thumbFolder

    # 载入缩略图到场景参数集合
    scene = bpy.context.scene
    scene.image_browser_items.clear()
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.svg')
    for file in os.listdir(thumb_directory):
        if file.lower().endswith(image_extensions):
            item = scene.image_browser_items.add()
            item.name = file
            item.path = os.path.join(thumb_directory, file)

    # 生成Blender内置的缩略图
    global preview_collections
    # 载入blender preview模块
    if "main" not in preview_collections:
        preview_collections["main"] = bpy.utils.previews.new()
    pcoll = preview_collections["main"]

    for item in scene.image_browser_items:
        if os.path.exists(item.path):
            try:
                if not pcoll.get(item.name):
                    pcoll.load(item.name, item.path, 'IMAGE')
            except Exception as e:
                utils.outputMsg(f"Failed to generate preview for {item.name}: {str(e)}")    
    return

# 载入缩略图，必须结合静态的集合操作
def loadPavilionThumb():
    # 定义缩略图目录
    addonName = "ACA Builder"
    thumbFolder = 'pavilion'
    USER = pathlib.Path(
        bpy.utils.resource_path('USER'))
    thumb_directory = USER / "scripts/addons" / addonName / thumbFolder

    # 载入缩略图到场景参数集合
    scene = bpy.context.scene
    scene.pavilion_browser_items.clear()
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.svg')
    for file in os.listdir(thumb_directory):
        if file.lower().endswith(image_extensions):
            item = scene.pavilion_browser_items.add()
            item.name = file
            item.path = os.path.join(thumb_directory, file)

    # 生成Blender内置的缩略图
    global preview_collections
    # 载入blender preview模块
    if "pavilion" not in preview_collections:
        preview_collections["pavilion"] = bpy.utils.previews.new()
    pcoll = preview_collections["pavilion"]

    for item in scene.pavilion_browser_items:
        if os.path.exists(item.path):
            try:
                if not pcoll.get(item.name):
                    pcoll.load(item.name, item.path, 'IMAGE')
            except Exception as e:
                utils.outputMsg(f"Failed to generate preview for {item.name}: {str(e)}")    
    return

# 构造缩略图列表的enum属性
# 因为使用了Blender的template_view_icon控件，需要构造这个结构
# 为了解决Label显示的乱码问题，引入了一个_make_item()方法
# https://github.com/bonjorno7/3dn-bip/issues/51
_item_map = dict()
def _make_item(id, name, descr, preview_id, uid):
    lookup = f"{str(id)}\0{str(name)}\0{str(descr)}\0{str(preview_id)}\0{str(uid)}"
    if not lookup in _item_map:
        _item_map[lookup] = (id, name, descr, preview_id, uid)
    return _item_map[lookup]
def getThumbEnum(self, context):
    # 引入了_make_item()方法后，不再需要全局声明items
    items = []
    # 不能直接clear，否则会产生乱码
    # https://github.com/bonjorno7/3dn-bip/issues/51
    #items.clear()

    # 载入预览集合
    global preview_collections
    pcoll = preview_collections.get("main", None)
    if not pcoll:
        return items
    
    # 确认缩略图已载入
    scene = context.scene
    if not hasattr(scene, "image_browser_items"):
        return items

    # 基于模板列表，逐一匹配缩略图，使之顺序一致
    scnData = context.scene.ACA_data
    templateItems = scnData.templateItem
    thumbIndex = 0
    # 获取模板列表
    for template in templateItems:
        # 模板名称
        templateName = template.name
        isFindThumb = False
        for image in scene.image_browser_items:
            # 图标ID
            thumb = pcoll.get(image.name)
            iconId = thumb.icon_id if thumb else 0

            # 缩略图名称：图片文件去掉后缀
            thumbName = image.name
            thumbName = thumbName[:thumbName.rfind(".")]

            # 如果找到则添加到Enum列表
            if thumbName == templateName:
                items.append(_make_item(
                    thumbName, thumbName, thumbName, 
                    iconId, thumbIndex))
                isFindThumb = True
                thumbIndex += 1
                break
        
        # 如果没有找到缩略图，则添加一个nopreview.png
        if not isFindThumb:
            thumb = pcoll.get('nopreview.png')
            iconId = thumb.icon_id if thumb else 0

            items.append(_make_item(
                templateName, templateName, templateName, 
                iconId, thumbIndex))
            thumbIndex += 1
            
    # print(repr(items))
    return items

def getPavilionEnum(self, context):
    # 引入了_make_item()方法后，不再需要全局声明items
    items = []
    # 不能直接clear，否则会产生乱码
    # https://github.com/bonjorno7/3dn-bip/issues/51
    #items.clear()

    # 载入预览集合
    global preview_collections
    pcoll = preview_collections.get("pavilion", None)
    if not pcoll:
        return items
    
    # 确认缩略图已载入
    scene = context.scene
    if not hasattr(scene, "pavilion_browser_items"):
        return items

    # 基于模板列表，逐一匹配缩略图，使之顺序一致
    scnData = context.scene.ACA_data
    pavilionItems = scnData.pavilionItem
    thumbIndex = 0
    # 获取模板列表
    for pavilion in pavilionItems:
        # 模板名称
        pavilionName = pavilion.name
        isFindThumb = False
        for image in scene.pavilion_browser_items:
            # 图标ID
            thumb = pcoll.get(image.name)
            iconId = thumb.icon_id if thumb else 0

            # 缩略图名称：图片文件去掉后缀
            thumbName = image.name
            thumbName = thumbName[:thumbName.rfind(".")]

            # 如果找到则添加到Enum列表
            if thumbName == pavilionName:
                items.append(_make_item(
                    thumbName, thumbName, thumbName, 
                    iconId, thumbIndex))
                isFindThumb = True
                thumbIndex += 1
                break
        
        # 如果没有找到缩略图，则添加一个nopreview.png
        if not isFindThumb:
            thumb = pcoll.get('nopreview.png')
            iconId = thumb.icon_id if thumb else 0

            items.append(_make_item(
                pavilionName, pavilionName, pavilionName, 
                iconId, thumbIndex))
            thumbIndex += 1
            
    # print(repr(items))
    return items

# 删除预览集合
# 在__init__.py中的ungregister()中调用
def releasePreview():
    global preview_collections
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

    # global preview_collections
    # for pcoll in preview_collections.values():
    #     bpy.utils.previews.remove(pcoll)
    # preview_collections.clear()

# 将XML中的节点按类型转换
def __readNode(node):
    tag = node.tag
    type = node.attrib['type']
    value = node.text
    # 类型转换
    # 20250209 老版本的模板通过数据类型进行判断
    if type == 'str':
        # 特殊处理下拉框
        if tag in ('roof_style',
                    'juzhe',
                    'dg_style'):
            value = int(value)
        else:
            value = value
    elif type == 'float':
        value = round(float(value),3)
    elif type == 'int':
        value = int(value)
    elif type == 'bool':
        # 注意这里的True/False是str，用bool()强制转换时都为True，
        # 所以以下手工进行了判断
        if value == 'True':
            value = True
        if value == 'False':
            value = False
    # 20250209 新版本的模板通过bdata数据属性进行判断
    if type =='StringProperty':
        value = value
    elif type == 'IntProperty':
        value = int(value)
    elif type == 'FloatProperty':
        value = round(float(value),3)
    elif type == 'BoolProperty':
        if value == 'True':
            value = True
        if value == 'False':
            value = False
    elif type == 'EnumProperty':
        value = int(value)
    elif type == 'FloatVectorProperty':
        # 将字符串'0,0,0'转换为元组(0,0,0)
        value = tuple(float(coord) for coord in value.split(','))

    return tag, value

# 将XML中的节点按类型转换
def __float2xml(value,keytype):
    # 简单的浮点数
    if isinstance(value, float):
        value = round(value,3)
    # 浮点数组，对应于FloatVectorProperty
    if type(value).__name__ == 'bpy_prop_array':
        keytype = 'FloatVectorProperty'
        value = ",".join(str(round(num,3)) for num in value)
    return value,keytype