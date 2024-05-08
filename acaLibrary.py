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
    #print("Loading " + assetName + '...')
    # 打开资产文件
    filepath = os.path.join('template', 'acaAssets.blend')

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

    