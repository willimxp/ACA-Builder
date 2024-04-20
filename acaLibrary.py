# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   管理资产库
import bpy
import os

from . import utils
from .const import ACA_Consts as con

# 载入Blender中的资产
# 参考教程：https://b3d.interplanety.org/en/appending-all-objects-from-the-external-blend-file-to-the-scene-with-blender-python-api/
# 参考文档：https://docs.blender.org/api/current/bpy.types.BlendDataLibraries.html
def loadAssets(assetName : str,parent:bpy.types.Object,hide=True):
    # 打开资产文件
    filepath = os.path.join('template', 'acaAssets.blend')

    # 载入文件中所有的object
    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        data_to.objects = data_from.objects

    asset = None
    assets = set()
    # 查找指定名称的对象
    for obj in data_to.objects:
        if assetName in obj.name:
            asset = obj # 暂存该对象
            assets.add(obj)
            # 查找其子对象
            if len(obj.children) >0:
                for child in obj.children:
                    assets.add(child)

    # 把对象绑定到建筑上
    # 其子对象仍保持原来的父子关系
    asset.parent = parent

    # 将父子对象全部绑定到场景中
    # coll = utils.setCollection(con.ROOT_COLL_NAME)
    # buildingObj = utils.getAcaParent(parent,con.ACA_TYPE_BUILDING)
    # buildingColl = buildingObj.users_collection[0]
    # utils.setCollection('资产',parentColl=buildingColl)
    coll = bpy.context.collection
    for a in assets:
        coll.objects.link(a)
        if hide:
            utils.hideObj(a)
        else:
            utils.showObj(a)
    
    return(asset)

    