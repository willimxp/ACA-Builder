# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
# 常数定义
# 请务必注意，只读取该属性，不要修改属性

class ACA_Consts(object):
    # 系统参数
    ROOT_COLL_NAME = 'ACA古建筑生成' # 根目录名称
    BUILDING_NAME = '古建筑'  # 建筑名称
    PLATFORM_NAME = '台基'      # 台基名称
    ACA_TYPE_PLATFORM = 'platform'  # ACA类型：台基
    
    # 基本参数
    PLATFORM_HEIGHT = 1 # 默认台基高度
    PLATFORM_EXTEND = 1 # 默认台基下出
    
    def __setattr__(self, name, value):
        raise AttributeError("Can't modify constant values")


# 通则类
EAVE_EX = 21 # 带斗拱的建筑，上檐出21斗口
YANCHUAN_EX = 14    # 檐椽平出14斗口
FEICHUAN_EX = 7     # 飞椽平出7斗口
DOUGONG_SPAN = 11   # 斗栱攒距，通常取11斗口
#LIFT_RATIO = [0.5,0.65,0.75,0.9]    # 清工程做法则例的推荐系数
LIFT_RATIO = [0.5,0.7,0.8,0.9]       # 梁思成图纸中采用的系数，可以进行比较

# 柱子
PILLER_D_EAVE = 6   # 檐柱直接径6斗口
PILLER_H_EAVE = 57  # 檐柱高约57斗口（到挑檐桁下皮共70斗口）
PILLER_D_JIN = 6.6  # 金柱直径6.6斗口

# 枋类
EFANG_LARGE_H = 6   # 大额枋高
EFANG_LARGE_Y = 4.8 # 大额枋厚
EFANG_SMALL_H = 4   # 小额枋高
EFANG_SMALL_Y = 3.2 # 小额枋厚
PINGBAN_H = 2       # 平板枋高
PINGBAN_Y = 3.5     # 平板枋厚

# 垫板类
BOARD_YOUE_H = 2    # 由额垫板高
BOARD_YOUE_Y = 1    # 由额垫板厚

# 斗栱类
BIG_DOU_KOU_TOP = 1.2   # 坐斗的斗口高度，也是第一根瓜栱的高度
ZJ_LENGTH = 3 # 拽架宽度3斗口

# 桁檩类
#HENG_TIAOYAN_D = 3   # 挑檐桁直径
#HENG_COMMON_D = 4.5  # 正心桁直径
HENG_TIAOYAN_D = 3.2    # 挑檐桁直径，梁思成数据
HENG_COMMON_D = 4       # 正心桁直径，梁思成数据
FUJIMU_D = 4            # 伏脊木

# 椽飞类
YUANCHUAN_D = 1.5   # 圆椽直径
FEICHUAN_H = 1.5    # 飞椽、方椽高
FEICHUAN_Y = 1.5    # 飞椽、方椽厚
WANGBAN_H = 0.5     # 望板厚
LIKOUMU_H =  FEICHUAN_H + WANGBAN_H     # 里口木高度，一飞椽+一望板
LIKOUMU_Y = FEICHUAN_H     # 里口木厚度
XIAOLIANYAN_H = WANGBAN_H * 1.5         # 小连檐厚度(暂未使用，都用了里口木尺寸)
ZADANGBAN_H = FEICHUAN_H    # 闸挡板高(暂未使用，都用了里口木尺寸)
ZADANGBAN_Y = WANGBAN_H     # 闸挡板厚(暂未使用，都用了里口木尺寸)
DALIANYAN_H = YUANCHUAN_D   # 大连檐，高同椽径
DALIANYAN_Y = YUANCHUAN_D   # 大连檐，宽1.1-1.2椽径
FEICHUAN_HEAD_TILE_RATIO = 1/2.5        # 飞椽头身比，默认一飞二尾五
QUETAI = YUANCHUAN_D*0.2    # 雀台长度(通常1/5~1/3椽径)

# 角梁
JIAOLIANG_H = 4.5   # 角梁高（老角梁和子角梁）
JIAOLIANG_Y = 3     # 角梁厚（老角梁和子角梁）
JIAOLIANG_WEI_KOUJIN = 0.2      # 角梁尾的扣金系数，则例没有明说，这个值越小，约陡峭
JIAOLIANG_HEAD_YAJIN = 0.5      # 角梁头的压金系数，则例没有明说，这个值越小，约陡峭
YOUQIANG_YAJIN = 1-JIAOLIANG_WEI_KOUJIN           #由戗压金系数

#瓦作类，以下数据来自刘大可《中国古建筑瓦石营法》p287
BANWA_SIZE = (          # 板瓦=========
   (43.2,35.2,7.29),    # 二样
   (40,32,6.63),        # 三样
   (38.4,30.4,6.3),     # 四样
   (36.8,27.2,5.64),    # 五样
   (33.6,25.6,5.3),     # 六样
   (32,22.4,4.64),      # 七样
   (30.4,20.8,4.31),    # 八样
   (28.8,19.2,3.98)     # 九样
) # 单位厘米，长、宽、囊（弧高，不含瓦厚)
TONGWA_SIZE = (         # 筒瓦==========
   (40,20.8,10.4),      # 二样
   (36.8,19.2,9.6),     # 三样
   (35.2,17.6,8.8),     # 四样
   (33.6,16,8),         # 五样
   (30.4,14.4,7.2),     # 六样
   (28.8,12.8,6.4),     # 七样
   (27.2,11.2,5.6),     # 八样
   (25.6,9.6,4.8)       # 九样
) # 单位厘米，长、宽、高
TILE_OVERLAP = 0.6      # 底瓦重叠4份，露出6份


# 其他
OFFSET_ORIENTATION = 'GLOBAL' # 'GLOBAL'  'LOCAL' #上下层叠构件的错开方式，一般绘图是垂直位移，但其实相对方向的位移更好看
YIJIAOCHUAN_OFFSET = JIAOLIANG_Y/4 # 为了防止翼角椽与角梁打架，而做了一定的让渡
# 屋瓦灰背层高度，用于计算铺瓦的高度
# 一般20cm，北方官式建筑可以达到30cm
# 其实也考虑了算法中从桁中线垂直向上找点，没有顺着坡面加斜，从而导致的误差
ROOFMUD_H = 4
CHUIJI_SMOOTH = 2   #垂脊艺术化处理，在子角梁中点略作弯曲

# 门窗（马炳坚数据）
KAN_DOWN_HEIGHT = 0.8   # 下槛高度，单位D
KAN_DOWN_DEEPTH = 0.3   # 下槛深度，单位D，梁思成实际使用的为0.4
KAN_MID_HEIGHT = 0.66   # 中槛高度，单位D(汤崇平书p20中定为0.64)
KAN_MID_DEEPTH = 0.3    # 中槛深度，单位D
KAN_UP_HEIGHT = 0.5     # 上槛高度，单位D
KAN_UP_DEEPTH = 0.3     # 上槛深度，单位D
KAN_WIND_HEIGHT = 0.5   # 风槛高度
KAN_WIND_DEEPTH = 0.4   # 风槛深度
BAOKUANG_WIDTH = 0.66   # 抱框宽度，单位D
BAOKUANG_DEEPTH = 0.3   # 抱框深度，单位D
BORDER_WIDTH = 0.2    # 边梃、抹头宽
BORDER_DEEPTH = BAOKUANG_DEEPTH     # 边梃、抹头厚
ZIBIAN_WIDTH = BORDER_WIDTH*0.5     # 仔边宽
ZIBIAN_DEEPTH = BORDER_WIDTH*0.5    # 仔边厚
TABAN_DEEPTH = 1.5       # 榻板宽，单位D
TABAN_HEIGHT = 3/8      # 榻板高，单位D
TABAN_EX = 0.1          # 榻板金边，单位unit（米）
GESHAN_GAP = 0.01        # 隔扇的间距，门缝，单位为unit（米）
