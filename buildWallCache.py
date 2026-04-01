# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   墙体对象缓存机制，用于缓存栏杆、坐凳、隔扇、雀替等墙体对象
from .locale.i18n import _
import bpy
from typing import Callable, Optional, Tuple, Dict, Any
from weakref import WeakValueDictionary

from . import utils

class WallCache:
    """
    墙体对象缓存类
    
    用于缓存栏杆、坐凳、隔扇、雀替等墙体对象，避免重复生成相同尺寸的对象。
    
    使用示例:
        # 创建缓存实例
        railingCache = WallCache(cacheName="栏杆缓存")
        
        # 生成缓存键
        cacheKey = railingCache.generateKey(
            values={'length': 3.5, 'gap': 0.2, 'type': 'railing'},
            precisions={'length': 2, 'gap': 3}
        )
        
        # 检查并获取缓存
        cachedObj = railingCache.get(cacheKey)
        if cachedObj is None:
            # 生成新对象
            newObj = buildRailing(...)
            # 保存到缓存
            railingCache.set(cacheKey, newObj, namePrefix="_cache_栏杆")
        
        # 清理缓存
        railingCache.clear()
    """
    
    def __init__(self, cacheName: str = "墙体缓存"):
        """
        初始化缓存
        
        参数:
            cacheName: 缓存名称，用于日志输出
        """
        self._cacheName = cacheName
        self._cache: Dict[Tuple, bpy.types.Object] = {}
    
    def generateKey(self, 
                   values: Dict[str, Any], 
                   precisions: Optional[Dict[str, int]] = None) -> Tuple:
        """
        生成缓存键
        
        参数:
            values: 缓存键值字典，如 {'length': 3.5, 'gap': 0.2, 'type': 'railing'}
            precisions: 精度字典，指定每个数值字段的四舍五入精度
                       如 {'length': 2, 'gap': 3} 表示 length 精确到 0.01，gap 精确到 0.001
        
        返回:
            元组形式的缓存键
        """
        keyParts = []
        for key, value in values.items():
            if isinstance(value, float) and precisions and key in precisions:
                precision = precisions[key]
                value = round(value, precision)
            keyParts.append(value)
        return tuple(keyParts)
    
    def get(self, 
           cacheKey: Tuple, 
           parentObj: Optional[bpy.types.Object] = None,
           newName: Optional[str] = None,
           singleUser: bool = False) -> Optional[bpy.types.Object]:
        """
        从缓存获取对象
        
        参数:
            cacheKey: 缓存键
            parentObj: 父对象，如果指定则将复制的对象设置为此父对象的子对象
            newName: 新对象名称，如果指定则重命名复制的对象
            singleUser: 是否创建独立用户副本
        
        返回:
            复制的对象，如果缓存未命中或缓存对象已失效则返回 None
        """
        if cacheKey not in self._cache:
            return None
        
        cachedObj = self._cache[cacheKey]
        
        try:
            if cachedObj is None or cachedObj.name not in bpy.data.objects:
                self._invalidate(cacheKey)
                return None
            
            resultObj = utils.copyObject(
                sourceObj=cachedObj,
                name=newName if newName else cachedObj.name,
                parentObj=parentObj,
                singleUser=singleUser
            )
            # print(_("从缓存复制对象: %s") % (resultObj.name))
            return resultObj
            
        except ReferenceError:
            self._invalidate(cacheKey)
            print(_("%s缓存对象已失效，已清除: %s") % (self._cacheName, str(cacheKey)))
            return None
    
    def set(self,
           cacheKey: Tuple,
           sourceObj: bpy.types.Object,
           namePrefix: str = "_cache_") -> Optional[bpy.types.Object]:
        """
        保存对象到缓存
        
        参数:
            cacheKey: 缓存键
            sourceObj: 源对象
            namePrefix: 缓存对象名称前缀
        
        返回:
            缓存的对象副本
        """
        if sourceObj is None:
            return None
        
        cacheName = f"{namePrefix}{cacheKey[0] if cacheKey else 'unknown'}"
        
        cachedObj = utils.copyObject(
            sourceObj=sourceObj,
            name=cacheName,
            singleUser=False
        )
        
        utils.hideObj(cachedObj)
        self._cache[cacheKey] = cachedObj
        # print(_("对象已缓存: %s") % (cachedObj.name))
        return cachedObj
    
    def _invalidate(self, cacheKey: Tuple):
        """
        使指定缓存键失效
        """
        if cacheKey in self._cache:
            del self._cache[cacheKey]
    
    def clear(self):
        """
        清理所有缓存
        删除所有缓存对象并清空缓存字典
        """
        for cacheKey, cachedObj in list(self._cache.items()):
            try:
                if cachedObj is not None and cachedObj.name in bpy.data.objects:
                    utils.deleteHierarchy(cachedObj,
                                          del_parent=True)
            except ReferenceError:
                pass
        self._cache.clear()
    
    def has(self, cacheKey: Tuple) -> bool:
        """
        检查缓存键是否存在且有效
        
        参数:
            cacheKey: 缓存键
        
        返回:
            缓存是否存在且有效
        """
        if cacheKey not in self._cache:
            return False
        
        cachedObj = self._cache[cacheKey]
        try:
            return cachedObj is not None and cachedObj.name in bpy.data.objects
        except ReferenceError:
            self._invalidate(cacheKey)
            return False
    
    def size(self) -> int:
        """
        返回缓存大小
        
        返回:
            缓存中的对象数量
        """
        return len(self._cache)
    
    def keys(self):
        """
        返回所有缓存键
        
        返回:
            缓存键列表
        """
        return list(self._cache.keys())


class WallCacheManager:
    """
    墙体缓存管理器
    
    管理多种墙体类型的缓存实例，提供统一的缓存管理接口。
    
    使用示例:
        # 获取管理器实例
        manager = WallCacheManager.getInstance()
        
        # 获取栏杆缓存
        railingCache = manager.getCache('railing')
        
        # 清理所有缓存
        manager.clearAll()
    """
    
    _instance = None
    _caches: Dict[str, WallCache] = {}
    
    @classmethod
    def getInstance(cls):
        """
        获取单例实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def getCache(self, cacheType: str, cacheName: Optional[str] = None) -> WallCache:
        """
        获取指定类型的缓存实例
        
        参数:
            cacheType: 缓存类型，如 'railing', 'bench', 'geshan', 'queti' 等
            cacheName: 缓存名称，如果不指定则使用类型名称
        
        返回:
            WallCache 实例
        """
        if cacheType not in self._caches:
            name = cacheName if cacheName else f"{cacheType}缓存"
            self._caches[cacheType] = WallCache(cacheName=name)
        return self._caches[cacheType]
    
    def clearCache(self, cacheType: str):
        """
        清理指定类型的缓存
        
        参数:
            cacheType: 缓存类型
        """
        if cacheType in self._caches:
            self._caches[cacheType].clear()
    
    def clearAll(self):
        """
        清理所有缓存
        """
        for cache in self._caches.values():
            cache.clear()
    
    def removeCache(self, cacheType: str):
        """
        移除指定类型的缓存实例
        
        参数:
            cacheType: 缓存类型
        """
        if cacheType in self._caches:
            self._caches[cacheType].clear()
            del self._caches[cacheType]


def getRailingCache() -> WallCache:
    """
    获取栏杆缓存实例
    
    返回:
        栏杆缓存实例
    """
    return WallCacheManager.getInstance().getCache('railing', "栏杆缓存")


def getBenchCache() -> WallCache:
    """
    获取坐凳缓存实例
    
    返回:
        坐凳缓存实例
    """
    return WallCacheManager.getInstance().getCache('bench', "坐凳缓存")


def getGeshanCache() -> WallCache:
    """
    获取隔扇缓存实例
    
    返回:
        隔扇缓存实例
    """
    return WallCacheManager.getInstance().getCache('geshan', "隔扇缓存")


def getQuetiCache() -> WallCache:
    """
    获取雀替缓存实例
    
    返回:
        雀替缓存实例
    """
    return WallCacheManager.getInstance().getCache('queti', "雀替缓存")


def getDoorCache() -> WallCache:
    """
    获取门/隔扇缓存实例
    
    返回:
        门/隔扇缓存实例
    """
    return WallCacheManager.getInstance().getCache('door', "门/隔扇缓存")


def clearAllWallCache():
    """
    清理所有墙体缓存
    """
    WallCacheManager.getInstance().clearAll()
