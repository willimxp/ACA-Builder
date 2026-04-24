# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   回廊的营造
import bpy
import math
from mathutils import Vector

from .. import utils
from ..const import ACA_Consts as con
from ..locale.i18n import _
from ..data import ACA_data_obj as acaData
from .. import buildFloor
from ..postproc import buildingJoin
from ..postproc import buildingSplice

# 回廊延伸
def loggia_extend(contextObj:bpy.types.Object,
                  dir = 'E', # 方向：东E南N西W北S
                  ):
    # 1、准备 -----------------------
    LoggiaJoined = None

    # 验证是否选中建筑
    building,bData,oData = utils.getRoot(contextObj)
    if building is None:
        utils.popMessageBox(_("请选中建筑"))
        return {'CANCELLED'}
    
    # 找到未合并的本体
    if bData.aca_type == con.ACA_TYPE_BUILDING_JOINED:
        Loggia = buildingJoin.getJoinedOriginal(building)
        LoggiaJoined = building
    else:
        Loggia = building
    bData:acaData = Loggia.ACA_data

    # 标识原廊间的相邻廊间，以便panel上禁用不合理的延伸方向
    # 未合并对象的标注
    if dir in ('E','W','N','S'):
        bData.loggia_sign += '/' + dir
    # 原始廊间是横版，还是竖版？
    zRot = Loggia.rotation_euler.z
    if (abs(zRot - math.radians(0)) < 0.001
        or abs(zRot - math.radians(180)) < 0.001):
        isWE = True
    else:
        isWE = False
    if isWE:
        if dir in ('NE','SE'):
            bData.loggia_sign += '/E' 
        if dir in ('NW','SW'):
            bData.loggia_sign += '/W' 
    else:
        if dir in ('NE','NW'):
            bData.loggia_sign += '/N' 
        if dir in ('SE','SW'):
            bData.loggia_sign += '/S' 
    # 控制螭吻显示
    __setLoggiaChiwen(building,dir)

    # 如果未合并，开始合并
    if LoggiaJoined is None:
        LoggiaJoined = buildingJoin.joinBuilding(Loggia)

        if LoggiaJoined is None:
            utils.popMessageBox(_("未能合并建筑"))
            return {'CANCELLED'}
    
    # 2、判断转角，并生成转角 ---------------------------
    if dir in ('NW','NE','SW','SE'):
        isCorner = True
    else:
        isCorner = False
    if bData.combo_type == con.COMBO_LOGGIA_CORNER:
        isBranch = True
    else:
        isBranch = False
    # 做L形转角
    if isCorner: 
        LoggiaCornerJoined = __add_loggia_corner(
            baseLoggia = LoggiaJoined,
            dir = dir,
        )
    # 做丁字或十字交叉
    if isBranch:
        LoggiaCornerJoined = __update_loggia_corner(
            baseLoggia = LoggiaJoined,
            dir = dir,
        )
    
    # 3、延伸方向的廊间生成 -----------------------
    LoggiaNewJoined = __add_loggia_extend(
        baseLoggia = LoggiaJoined,
        dir = dir,
    )

    # 4、转角屋顶裁剪 ---------------------------
    # 注意：要在新廊间转角关联前处理，以新廊间重复自我裁剪
    if isCorner or isBranch:
        __add_loggia_intersection(
            fromLoggia = LoggiaJoined,
            toLoggia = LoggiaNewJoined,
            cornerLoggia = LoggiaCornerJoined,
        )

    # 5、标识转角与廊间的关联，以便在做T形或X形交叉时找回参考廊间
    if isCorner or isBranch:
        # 转角ID
        LoggiaCorner = buildingJoin.getJoinedOriginal(LoggiaCornerJoined)
        cornerJData:acaData = LoggiaCornerJoined.ACA_data
        cornerData:acaData = LoggiaCorner.ACA_data
        # 新廊间ID
        childID = cornerData.combo_children.add()
        childID.id = LoggiaNewJoined.ACA_data.aca_id
        childID = cornerJData.combo_children.add()
        childID.id = LoggiaNewJoined.ACA_data.aca_id
        if dir in ('NW','NE','SW','SE'):
            # 老廊间关联转角
            childID = cornerData.combo_children.add()
            childID.id = LoggiaJoined.ACA_data.aca_id
            childID = cornerJData.combo_children.add()
            childID.id = LoggiaJoined.ACA_data.aca_id

    # 6、标识原廊间的相邻廊间，以便panel上禁用不合理的延伸方向
    # 已合并对象的标注
    jData:acaData = LoggiaJoined.ACA_data
    jData.loggia_sign = bData.loggia_sign
    for obj in LoggiaJoined.children:
        if con.BOOL_SUFFIX  in obj.name : continue
        oData:acaData = obj.ACA_data
        oData.loggia_sign = bData.loggia_sign

    # 7、转角闭合判断 ----------------------------- 
    isConnected = False
    # 尝试闭合廊间与廊间的碰撞
    # 可能是在一字延伸时触发
    # 也可能是经过转角时触发
    isConnected = __connect_loggia_loggia(
        LoggiaNewJoined,dir)

    # 尝试闭合转角处的碰撞
    # 可能时从转角延伸到廊间，
    # 也可能时一字延伸碰撞到廊间
    if not isConnected:
        # 如果廊间已经闭合过，则不再触发转角闭合，避免修改了原来的转角
        __connect_loggia_corner(LoggiaNewJoined,dir)

    # 尝试闭合开放的转角
    __connect_open_corner(LoggiaNewJoined,dir)

    # 8、聚焦在新loggia
    for obj in LoggiaNewJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        utils.focusObj(obj)

    return {'FINISHED'}

# 生成回廊转角
def __add_loggia_corner(baseLoggia:bpy.types.Object,
                  dir):
    # 1、准备 ----------------------------------
    # 开启进度条
    global isFinished,progress
    isFinished = False
    progress = 0

    # 参考廊间
    LoggiaJoined = baseLoggia
    Loggia = buildingJoin.getJoinedOriginal(LoggiaJoined)
    bData:acaData = Loggia.ACA_data
    dk = bData.DK   

    # 原始廊间是横版，还是竖版？
    zRot = Loggia.rotation_euler.z
    if (abs(zRot - math.radians(0)) < 0.001
        or abs(zRot - math.radians(180)) < 0.001):
        isWE = True
    else:
        isWE = False

    # 2、原廊间的裁剪 ------------------------
    __cut_base_loggia(baseLoggia,dir)
    
    # 3、创建回廊转角对象 ---------------------
    LoggiaCorner = buildFloor.__addBuildingRoot(_('回廊转角'))
    # 从回廊同步设置
    from .. import buildCombo
    buildCombo.__syncData(
        fromBuilding=Loggia,
        toBuilding=LoggiaCorner,
    )
    # 重新设置柱网，并打标识
    cornerData:acaData = LoggiaCorner.ACA_data
    cornerData['combo_type'] = con.COMBO_LOGGIA_CORNER
    cornerData['x_rooms'] = 1
    cornerData['x_1'] = cornerData.y_1
    cornerData['y_rooms'] = 1
    # 标注相邻廊间
    if isWE: # 水平方向，颠倒东西向
        if dir == 'NE':sign = '/N/W'
        if dir == 'NW':sign = '/N/E'
        if dir == 'SE':sign = '/S/W'
        if dir == 'SW':sign = '/S/E'
    else: # 垂直方向，颠倒南北向
        if dir == 'NE':sign = '/S/E'
        if dir == 'NW':sign = '/S/W'
        if dir == 'SE':sign = '/N/E'
        if dir == 'SW':sign = '/N/W'
    cornerData['loggia_sign'] = sign

    # 4、位移 ----------------------------
    offset_corner = bData.x_total/2 + bData.y_total/2
    # 横版，在廊间左右做转角
    if isWE:
        if dir in ('NE','SE'):
            offset_v = Vector((offset_corner,0,0))
        else:
            offset_v = Vector((-offset_corner,0,0))
    # 竖版，在廊间上下做转角
    else:
        if dir in ('NW','NE'):
            offset_v = Vector((0,offset_corner,0))
        else:
            offset_v = Vector((0,-offset_corner,0))
    LoggiaCorner.location = Loggia.location + offset_v 

    # 5、生成转角 ----------------------------
    buildFloor.buildFloor(LoggiaCorner)
    # 合并转角
    LoggiaCornerJoined = buildingJoin.joinBuilding(LoggiaCorner)

    # 6、屋顶控制 ----------------------------
    # 6.1、裁剪位置
    eaveExt = con.YANCHUAN_EX*dk + con.FLYRAFTER_EX*dk
    if bData.use_dg:
        eaveExt += bData.dg_extend
    eaveExt += con.SPLICE_DEPTH_EXT_DK*dk/2

    offset = eaveExt/2
    buildingH = (bData.platform_height+bData.pillar_height)
    if bData.use_dg:
        buildingH += bData.dg_height
    buildingH += bData.y_total / 2
    buildingH += con.SPLICE_HEIGHT_EXT_DK*dk # 保险高度
    boolCenter = Vector((offset,offset,buildingH/2))
    # 做东南角SE
    if ((isWE and dir == 'NE') # 横版向东北
        or (not isWE and dir == 'SW') # 竖版向西南
        ): 
        boolCenter *= Vector((1,-1,1))
        use_axis=(True,False,False)
        use_bisect=(True,False,False)
        use_flip=(True,False,False)
    # 做东北角NE
    if ((isWE and dir == 'SE') # 横版向东南
        or (not isWE and dir == 'NW') # 竖版向西南
        ): 
        boolCenter *= Vector((1,1,1))
        use_axis=(False,True,False)
        use_bisect=(False,True,False)
        use_flip=(False,False,False)
    # 做西北角NW
    if ((isWE and dir == 'SW') # 横版向东南
        or (not isWE and dir == 'NE') # 竖版向西南
        ): 
        boolCenter *= Vector((-1,1,1))
        use_axis=(True,False,False)
        use_bisect=(True,False,False)
        use_flip=(False,False,False)
    # 做西南角SW
    if ((isWE and dir == 'NW') # 横版向东南
        or (not isWE and dir == 'SE') # 竖版向西南
        ): 
        boolCenter *= Vector((-1,-1,1))
        use_axis=(False,True,False)
        use_bisect=(False,True,False)
        use_flip=(False,True,False)

    # 6.2、转角裁剪 --------------------------------------
    # 260409 务必在做45度镜像前做裁剪，以免产生水密问题
    dim = (cornerData.x_total + eaveExt,
            cornerData.y_total + eaveExt,
            buildingH
    )
    boolCube = utils.addCube(
        name=_("转角裁剪") + con.BOOL_SUFFIX,
        location=boolCenter,
        dimension=dim,
        parent=LoggiaCornerJoined,
    )
    utils.hideObjFace(boolCube)
    utils.hideObj(boolCube)
    for obj in LoggiaCornerJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        utils.addModifierBoolean(
            name='Corner-Cut',
            object=obj,
            boolObj=boolCube,
            operation='INTERSECT',
        )

    # 6.3、45度镜像 ------------------------------------------
    diagnalObj = utils.addEmpty(
        name = _('45度镜像') + con.BOOL_SUFFIX,
        parent = LoggiaCornerJoined,
        rotation=(0,0,math.radians(45)),
        location=(0,0,0)
    )
    utils.hideObj(diagnalObj)
    for obj in LoggiaCornerJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        utils.addModifierMirror(
            object= obj,
            mirrorObj=diagnalObj,
            use_axis=use_axis,
            use_bisect=use_bisect,
            use_flip=use_flip,
            use_merge=True,
            name='45-Axis'
        )
    
    # 关闭进度条
    isFinished = True

    return LoggiaCornerJoined

# 更新转角
# 用于在转角上做丁字或十字交叉
def __update_loggia_corner(baseLoggia:bpy.types.Object,
                  dir=''):
    LoggiaCornerJoined = baseLoggia
    bData:acaData = LoggiaCornerJoined.ACA_data
    dk = bData.DK
    buildingH = (bData.platform_height+bData.pillar_height)
    if bData.use_dg:
        buildingH += bData.dg_height
    buildingH += bData.y_total / 2
    buildingH += con.SPLICE_HEIGHT_EXT_DK*dk # 保险高度
    buildingEave = 20*dk # 悬山出际
    
    # 转角链接的廊间数量
    linkCount = len(bData.combo_children)

    # 做丁字交叉
    if linkCount == 2:
        # 找到转角屋的所有子对象(多个分层)
        cornerObjs = []
        for obj in LoggiaCornerJoined.children:
            if con.BOOL_SUFFIX not in obj.name : 
                cornerObjs.append(obj)
        if cornerObjs == []:
            raise Exception(_("无法找到转角对象"))
    
        # 已有的2个廊间，加上将要做的第3的廊间，推断丁字方向
        cornerLinked = bData.loggia_sign + '/' + dir
        # 丁字方向，丁头顶不出头的方向
        tdir = ''
        if 'N' not in cornerLinked:
            tdir = 'N'
            tdim = Vector((0,1,0))
            tloc = Vector((0,1,0))
        elif 'S' not in cornerLinked:
            tdir = 'S'
            tdim = Vector((0,1,0))
            tloc = Vector((0,-1,0))
        elif 'W' not in cornerLinked:
            tdir = 'W'
            tdim = Vector((1,0,0))
            tloc = Vector((-1,0,0))
        elif 'E' not in cornerLinked:
            tdir = 'E'
            tdim = Vector((1,0,0))
            tloc = Vector((1,0,0))
        
        # 生成丁字裁剪bool对象       
        size = (bData.y_total + buildingEave) * 1.414
        center = size * 1.414/2
        dim = (size,size,buildingH)
        locAdj = Vector((-center,-center,0)) * tloc
        loc = Vector((0,0,buildingH/2)) + locAdj
        # 添加裁剪
        boolCube = utils.addCube(
            name=_('丁字裁剪') + con.BOOL_SUFFIX,
            location=loc,
            dimension=dim,
            parent=LoggiaCornerJoined,
            rotation=(0,0,math.radians(45))
        )
        utils.hideObjFace(boolCube)
        utils.hideObj(boolCube)

        # 逐层处理转角
        for cornerObj in cornerObjs:
            # 原转角的调整 -------------------------------
            # 禁用45度镜像，以便后续如果做十字交叉时恢复
            mod = cornerObj.modifiers.get('45-Axis')
            mod.show_viewport = False
            mod.show_render = False
            # 与丁字方向对应
            if tdir in ('W','E'):
                cornerObj.rotation_euler.z = math.radians(90)

            # 原转角的裁剪 ------------------------------------
            # 默认出檐尺寸
            eaveExt = con.YANCHUAN_EX*dk + con.FLYRAFTER_EX*dk
            if bData.use_dg:
                eaveExt += bData.dg_extend
            eaveExt += con.SPLICE_DEPTH_EXT_DK*dk/2

            # 不出檐尺寸
            # 根据丁字头的出檐调整
            dimAdj = Vector((eaveExt,
                            eaveExt,
                            0)) * tdim
            dim = Vector((bData.x_total,
                        bData.x_total,
                        buildingH)) + dimAdj
            # 根据丁字头的出檐调整
            locAdj = Vector((eaveExt/2,
                            eaveExt/2,
                            0)) * tloc
            loc = Vector((0,
                        0,
                        buildingH/2)) + locAdj
            mod = cornerObj.modifiers.get('Corner-Cut')
            cornerBoolCube:bpy.types.Object = mod.object
            cornerBoolCube.dimensions = dim
            cornerBoolCube.location = loc

            # 复制转角屋并裁剪 ----------------------------------
            cornerCopy = utils.copySimplyObject(cornerObj,
                # 260419 复制对象应该做成单用户，否则在应用修改器后会在丁字转角打架
                singleUser=True)
            # 标注名称，便于在十字交叉时删除
            cornerCopy.name = _('丁字转角')
            # 旋转并交叉
            cornerCopy.rotation_euler.z += math.radians(90)
            utils.addModifierBoolean(
                name='T-Cut',
                object=cornerCopy,
                boolObj=boolCube,
                operation='INTERSECT',
            )
            utils.addModifierBoolean(
                name='T-Cut',
                object=cornerObj,
                boolObj=boolCube,
                operation='DIFFERENCE',
            )

    # 做十字交叉
    if linkCount ==3:
        # 找到转角屋的所有子对象(多个分层)
        cornerObjs = []
        # 删除丁字复制的转角屋
        for obj in LoggiaCornerJoined.children:
            if con.BOOL_SUFFIX  in obj.name : 
                if _('丁字裁剪') in obj.name:
                    # 删除丁字裁剪
                    utils.delObject(obj)
                    continue
                else:
                    # 保留其他bool对象
                    continue
            if _('丁字转角') in obj.name:
                # 删除丁字转角
                utils.delObject(obj)
            else:
                cornerObjs.append(obj)
        if cornerObjs == []:
            raise Exception(_("无法找到转角对象"))
        
        # 逐层处理转角
        for cornerObj in cornerObjs: 
            # 删除丁字裁剪
            mod = cornerObj.modifiers.get('T-Cut')
            cornerObj.modifiers.remove(mod)

            # 恢复旋转（不同的旋转，45度镜像的效果不同）
            cornerObj.rotation_euler.z = 0

            # 调整转角裁剪
            dim = Vector((bData.x_total,bData.x_total,buildingH))
            loc = Vector((0,0,buildingH/2))
            mod = cornerObj.modifiers.get('Corner-Cut')
            cornerBoolCube:bpy.types.Object = mod.object
            cornerBoolCube.dimensions = dim
            cornerBoolCube.location = loc

            # 重新启用45度对称
            mod:bpy.types.MirrorModifier = \
                cornerObj.modifiers.get('45-Axis')
            mod.show_viewport = True
            mod.show_render = True
            mod.use_axis = (True,True,False)
            mod.use_bisect_axis = (True,True,False)
            mod.use_bisect_flip_axis = (True,False,False)

    return LoggiaCornerJoined

# 向指定方向延伸一个廊间
def __add_loggia_extend(baseLoggia:bpy.types.Object,
                        dir,
                        ):
    # 1、准备 -----------------------------
    oData:acaData = baseLoggia.ACA_data
    LoggiaJoined = baseLoggia
    Loggia = buildingJoin.getJoinedOriginal(LoggiaJoined)
    bData:acaData = Loggia.ACA_data

    # 原始廊间是横版，还是竖版？
    zRot = Loggia.rotation_euler.z
    if (abs(zRot - math.radians(0)) < 0.001
        or abs(zRot - math.radians(180)) < 0.001):
        isWE = True
    else:
        isWE = False
    # 是否为转角
    if dir in ('NW','NE','SW','SE'):
        isCorner = True
    else:
        isCorner = False
    # 是否做T字或X字分支？
    isBranch = False
    if oData.combo_type == con.COMBO_LOGGIA_CORNER:
        isBranch = True
    # 如果在转角上做分支(T形或X形)，则反查原始廊间
    if isBranch:
        LoggiaCorner = Loggia
        cornerData:acaData = LoggiaCorner.ACA_data
        Loggia = utils.getObjByID(cornerData.combo_children[0].id)
        bData:acaData = Loggia.ACA_data

    # 2、原廊间的裁剪 ----------------------------------
    # 仅一字延伸需要裁剪原廊间
    # L转角在生成转角时已经裁剪过一次，不要重复裁剪
    # 另外，如果是从转角做T字或X字延伸，也不需要对转角进行裁剪
    if (not isCorner and not isBranch):
        __cut_base_loggia(baseLoggia,dir)

    # 3、向延伸方向复制 --------------------------------
    LoggiaColl = Loggia.users_collection[0]
    LoggiaNewColl = utils.copyCollection(
        LoggiaColl.name,LoggiaColl.name)
    LoggiaNew = LoggiaNewColl.objects[0]
    mData:acaData = LoggiaNew.ACA_data
    mData['aca_id'] = utils.generateID()
    # 标识相邻的回廊
    if dir == 'E':
        mData.loggia_sign = '/W'
    if dir == 'W':
        mData.loggia_sign = '/E'
    if dir == 'N':
        mData.loggia_sign = '/S'
    if dir == 'S':
        mData.loggia_sign = '/N'
    if isWE:
        if dir in ('NE','NW'):
            mData.loggia_sign = '/S'
        if dir in ('SE','SW'):
            mData.loggia_sign = '/N'
    else:
        if dir in ('NE','SE'):
            mData.loggia_sign = '/W'
        if dir in ('SW','NW'):
            mData.loggia_sign = '/E'
    
    # 4、如果转角则进行旋转
    if dir in ('NE','NW','SW','SE'):
        # 原廊间横版，转角后为竖版
        if isWE:
            LoggiaNew.rotation_euler.z = math.radians(90)
        # 原廊间竖版，转角后为横板
        else:
            LoggiaNew.rotation_euler.z = 0
    # 如果为分支，强制参考廊间于延伸方向一致
    if isBranch:
        if dir in ('W','E'):
            LoggiaNew.rotation_euler.z = 0
        else:
            LoggiaNew.rotation_euler.z = math.radians(90)

    # 5、位移 ----------------------------------------
    # 如果为分支，先将参考廊间对齐转角
    if isBranch:
        LoggiaNew.location = baseLoggia.location 
        offset = bData.x_total/2 - bData.y_total/2
        if dir == 'E': # 东
            LoggiaNew.location.x -= offset
        elif dir == 'W': # 西
            LoggiaNew.location.x += offset
        elif dir == 'N': # 北
            LoggiaNew.location.y -= offset
        elif dir == 'S': # 南
            LoggiaNew.location.y += offset
    # 一字延伸
    if dir == 'E': # 东
        LoggiaNew.location.x += bData.x_total
    elif dir == 'W': # 西
        LoggiaNew.location.x -= bData.x_total
    elif dir == 'N': # 北
        LoggiaNew.location.y += bData.x_total
    elif dir == 'S': # 南
        LoggiaNew.location.y -= bData.x_total
    # L转角
    offset = bData.x_total/2 + bData.y_total/2
    offset_v = Vector((offset,offset,0))
    if dir == 'NE':
        LoggiaNew.location += offset_v * Vector((1,1,1))
    if dir == 'NW':
        LoggiaNew.location += offset_v * Vector((-1,1,1))
    if dir == 'SE':
        LoggiaNew.location += offset_v * Vector((1,-1,1))
    if dir == 'SW':
        LoggiaNew.location += offset_v * Vector((-1,-1,1))

    # 260408 控制螭吻显示
    __setLoggiaChiwen(LoggiaNew,dir)

    # 6、合并 ------------------------------------
    LoggiaNewJoined = buildingJoin.joinBuilding(LoggiaNew)

    # 7、裁剪 ------------------------------------
    dk = bData.DK

    # 裁剪高度
    buildingH = (bData.platform_height+bData.pillar_height)
    if bData.use_dg:
        buildingH += bData.dg_height
    buildingH += bData.y_total / 2
    buildingH += con.SPLICE_HEIGHT_EXT_DK*dk # 保险高度

    # 裁剪宽度
    buildingEave = 20*dk # 悬山出际

    # 裁剪深度
    buildingDepth = bData.y_total
    # 加前后出檐
    buildingDepth += (con.YANCHUAN_EX*dk + con.FLYRAFTER_EX*dk)*2
    # 加斗栱出檐
    if bData.use_dg:
        buildingDepth += bData.dg_extend * 2
    # 加保留宽度(防止裁剪到瓦作)
    buildingDepth += con.SPLICE_DEPTH_EXT_DK*dk

    # 定位
    offset = buildingEave/2
    # 根据新延伸的回廊的横竖，判断裁剪偏移
    if dir in ('N','S','W','E'):
        # 一字延伸不改变方向
        isWENew = isWE
    else:
        # 转角改变了方向
        isWENew = not isWE
    # 如果为分支，已经旋转了参考廊间，之间按延伸方向判断即可
    if isBranch:
        if dir in ('W','E'):
            isWENew = True
        else:
            isWENew = False
    if isWENew:
        # 水平建筑，旋转为0，E为+x
        if 'E' in dir:
            boolX = offset
        else:
            boolX = -offset
    else:
        # 垂直建筑，旋转为90，N为+x
        if 'N' in dir:
            boolX = offset
        else:
            boolX = -offset
    boolCube = utils.addCube(
        name=_("出檐A裁剪") + con.BOOL_SUFFIX,
        location=Vector((boolX,0,buildingH/2)),
        dimension=(bData.x_total+buildingEave,
                   buildingDepth,
                   buildingH),
        parent=LoggiaNewJoined,
    )
    utils.hideObjFace(boolCube)
    utils.hideObj(boolCube)
    for obj in LoggiaNewJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        utils.addModifierBoolean(
            name='EaveA-Cut',
            object= obj,
            boolObj=boolCube,
            operation='INTERSECT'
        )
    return LoggiaNewJoined

# 转角处相邻廊间的屋顶裁剪
def __add_loggia_intersection(fromLoggia:bpy.types.Object,
                              toLoggia:bpy.types.Object,
                              cornerLoggia:bpy.types.Object,):
    LoggiaJoined = fromLoggia
    Loggia = buildingJoin.getJoinedOriginal(LoggiaJoined)
    LoggiaNewJoined = toLoggia
    LoggiaNew = buildingJoin.getJoinedOriginal(LoggiaNewJoined)
    LoggiaCornerJoined = cornerLoggia
    LoggiaCorner = buildingJoin.getJoinedOriginal(LoggiaCornerJoined)

    bData:acaData = Loggia.ACA_data
    # L转角的两个廊间裁剪
    if bData.combo_type == con.COMBO_LOGGIA:
        buildingSplice.__unionCrossL(
            fromBuilding= Loggia,
            toBuilding= LoggiaNew,
            fromBuildingJoined= LoggiaJoined,
            toBuildingJoined= LoggiaNewJoined,
        )
    # T转角裁剪
    if bData.combo_type == con.COMBO_LOGGIA_CORNER:
        cornerData:acaData = LoggiaCorner.ACA_data
        linkLoggiaList = cornerData.combo_children
        # 与转角每个相连廊间做裁剪
        for linkLoggia in linkLoggiaList:
            Loggia = utils.getObjByID(linkLoggia.id)
            LoggiaJoined = utils.getObjByID(
                linkLoggia.id,
                aca_type=con.ACA_TYPE_BUILDING_JOINED)
            buildingSplice.__unionCrossL(
                fromBuilding= Loggia,
                toBuilding= LoggiaNew,
                fromBuildingJoined= LoggiaJoined,
                toBuildingJoined= LoggiaNewJoined,
            )

    return 

# 原廊间的裁剪
def __cut_base_loggia(baseLoggia:bpy.types.Object,
                      dir):
    LoggiaJoined = baseLoggia
    Loggia = buildingJoin.getJoinedOriginal(LoggiaJoined)
    bData:acaData = Loggia.ACA_data
    dk = bData.DK

    # 裁剪高度
    buildingH = (bData.platform_height+bData.pillar_height)
    if bData.use_dg:
        buildingH += bData.dg_height
    buildingH += bData.y_total / 2
    buildingH += con.SPLICE_HEIGHT_EXT_DK*dk # 保险高度

    # 裁剪宽度
    buildingEave = 20*dk # 悬山出际

    # 裁剪深度
    buildingDepth = bData.y_total
    # 加前后出檐
    buildingDepth += (con.YANCHUAN_EX*dk + con.FLYRAFTER_EX*dk)*2
    # 加斗栱出檐
    if bData.use_dg:
        buildingDepth += bData.dg_extend * 2
    # 加保留宽度(防止裁剪到瓦作)
    buildingDepth += con.SPLICE_DEPTH_EXT_DK*dk

    # 原始廊间是横版，还是竖版？
    zRot = Loggia.rotation_euler.z
    if (abs(zRot - math.radians(0)) < 0.001
        or abs(zRot - math.radians(180)) < 0.001):
        isWE = True
    else:
        isWE = False

    # 定位
    offset = buildingEave/2
    if isWE:
        if 'E' in dir:
            boolX = -offset
        else:
            boolX = offset
    else:
        if 'S' in dir:
            boolX = offset
        else:
            boolX = -offset
    boolCube = utils.addCube(
        name=_("出檐B裁剪") + con.BOOL_SUFFIX,
        location=Vector((boolX,0,buildingH/2)),
        dimension=(bData.x_total+buildingEave,
                buildingDepth,
                buildingH),
        parent=LoggiaJoined,
    )
    utils.hideObjFace(boolCube)
    utils.hideObj(boolCube)
    for obj in LoggiaJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        utils.addModifierBoolean(
            name='EaveB-Cut',
            object= obj,
            boolObj=boolCube,
            operation='INTERSECT'
        )
    return

# 转角闭合判断，做转角时连接廊间和廊间
def __connect_loggia_loggia(LoggiaNewJoined:bpy.types.Object,dir):
    bData:acaData = LoggiaNewJoined.ACA_data

    # 一字廊间撞转角
    if dir == 'N': dir2 = 'S'
    if dir == 'S': dir2 = 'N'
    if dir == 'W': dir2 = 'E'
    if dir == 'E': dir2 = 'W'
    # L廊间撞转角
    if LoggiaNewJoined.rotation_euler.z == 0:
        if dir in ('NW','SW'): 
            dir = 'W'
            dir2 = 'E'
        if dir in ('NE','SE'): 
            dir = 'E'
            dir2 = 'W'
    else:
        if dir in ('NW','NE'): 
            dir = 'N'
            dir2 = 'S'
        if dir in ('SW','SE'): 
            dir = 'S'
            dir2 = 'N'

    # 找到合并目录
    JoinedColl:bpy.types.Collection = \
        bpy.context.scene.collection.children[con.COLL_NAME_ROOT_JOINED]
    connectObj = None
    # 遍历根目录下的每个建筑
    for joinedObj in JoinedColl.objects:
        # 跳过新建的廊间
        if joinedObj == LoggiaNewJoined: continue

        # 仅遍历合并的廊间
        if joinedObj.ACA_data.combo_type != con.COMBO_LOGGIA:
            continue

        # 只取3位小数，否则无法比较
        joinedLoc = utils.round_vector(joinedObj.location)
        newLoggiaLoc = utils.round_vector(LoggiaNewJoined.location)
        distance = utils.getVectorDistance(joinedLoc,newLoggiaLoc)
        roomdis = bData.x_total
        # 判断新廊间与现有廊间是否接近（面阔宽度）
        if distance - roomdis < 0.001:
            # 判断该廊间是否为已连接的相邻廊间
            if dir == 'W':
                # 想左延伸时，相连廊间在右侧
                if joinedLoc.x > newLoggiaLoc.x and joinedLoc.y == newLoggiaLoc.y:
                    continue
            if dir == 'E':
                # 想右延伸时，相连廊间在左侧
                if joinedLoc.x < newLoggiaLoc.x and joinedLoc.y == newLoggiaLoc.y:
                    continue
            if dir == 'N':
                # 想上延伸时，相连廊间在下侧
                if joinedLoc.y < newLoggiaLoc.y and joinedLoc.x == newLoggiaLoc.x:
                    continue
            if dir == 'S':
                # 想下延伸时，相连廊间在上侧
                if joinedLoc.y > newLoggiaLoc.y and joinedLoc.x == newLoggiaLoc.x:
                    continue
            connectObj = joinedObj
            break
    if connectObj is None: return
    # print("找到待闭合廊间：" + connectObj.name)

    # 廊间接头处裁剪
    __cut_base_loggia(LoggiaNewJoined,dir)
    __cut_base_loggia(connectObj,dir2)
    
    # 新廊间继承重叠廊间的标识
    connected_sign = connectObj.ACA_data.loggia_sign
    new_sign =  LoggiaNewJoined.ACA_data.loggia_sign

    LoggiaNewJoined.ACA_data['loggia_sign'] += connected_sign
    newLoggia = buildingJoin.getJoinedOriginal(LoggiaNewJoined)
    newLoggia.ACA_data['loggia_sign'] += connected_sign

    connectObj.ACA_data['loggia_sign'] += new_sign
    connectOrg = buildingJoin.getJoinedOriginal(connectObj)
    connectOrg.ACA_data['loggia_sign'] += new_sign

    # 重新处理螭吻的显示
    __setLoggiaChiwen(LoggiaNewJoined,dir)
    __setLoggiaChiwen(connectObj,dir)

    # print("廊间与廊间的闭合")
    return True

# 延伸时，尝试连接廊间和转角
def __connect_loggia_corner(LoggiaNewJoined:bpy.types.Object,
                            dir):
    bData:acaData = LoggiaNewJoined.ACA_data
    
    # 找到合并目录
    JoinedColl:bpy.types.Collection = \
        bpy.context.scene.collection.children[con.COLL_NAME_ROOT_JOINED]
    LoggiaCornerJoined = None
    # 遍历根目录下的每个建筑
    for joinedObj in JoinedColl.objects:
        # 跳过新建的廊间
        if joinedObj == LoggiaNewJoined: continue

        # 仅遍历合并的转角
        if joinedObj.ACA_data.combo_type != con.COMBO_LOGGIA_CORNER:
            continue

        # 只取3位小数，否则无法比较
        joinedLoc = utils.round_vector(joinedObj.location)
        newLoggiaLoc = utils.round_vector(LoggiaNewJoined.location)
        # 判断新廊间与转角是否接近（面阔/2+进深/2）
        distance = utils.getVectorDistance(joinedLoc,newLoggiaLoc)
        roomdis = bData.x_total/2 + bData.y_total/2
        if abs(distance - roomdis) < 0.001:
            LoggiaCornerJoined = joinedObj
            break
    if LoggiaCornerJoined is None: return

    # 如果廊间和转角已经连接，则无需后续处理
    cornerData:acaData = LoggiaCornerJoined.ACA_data
    for linkLoggia in cornerData.combo_children:
        if linkLoggia.id == bData.aca_id:
            return None

    # 转角丁字或十字屋顶更新
    # 一字廊间撞转角
    if dir == 'N': dir2 = 'S'
    if dir == 'S': dir2 = 'N'
    if dir == 'W': dir2 = 'E'
    if dir == 'E': dir2 = 'W'
    # L廊间撞转角
    if LoggiaCornerJoined.rotation_euler.z == 0:
        if dir in ('NW','SW'): dir2 = 'W'
        if dir in ('NE','SE'): dir2 = 'E'
    else:
        if dir in ('NW','NE'): dir2 = 'N'
        if dir in ('SW','SE'): dir2 = 'S'
    LoggiaCornerJoined = __update_loggia_corner(
        baseLoggia = LoggiaCornerJoined,
        dir = dir2
    )

    # 新廊间的更新
    __cut_base_loggia(LoggiaNewJoined,dir)

    # 新廊间屋顶碰撞
    __add_loggia_intersection(
            fromLoggia = LoggiaCornerJoined,
            toLoggia = LoggiaNewJoined,
            cornerLoggia = LoggiaCornerJoined,
        )
    
    # 追加转角的相邻标识
    LoggiaCorner = buildingJoin.getJoinedOriginal(LoggiaCornerJoined)
    LoggiaCorner.ACA_data['loggia_sign'] += '/' + dir2
    LoggiaNew = buildingJoin.getJoinedOriginal(LoggiaNewJoined)
    LoggiaNew.ACA_data['loggia_sign'] += '/' + dir

    # 标识转角与廊间的关联，以便在做T形或X形交叉时找回参考廊间
    cornerJData:acaData = LoggiaCornerJoined.ACA_data
    cornerData:acaData = LoggiaCorner.ACA_data
    # 新廊间ID
    childID = cornerData.combo_children.add()
    childID.id = LoggiaNewJoined.ACA_data.aca_id
    childID = cornerJData.combo_children.add()
    childID.id = LoggiaNewJoined.ACA_data.aca_id

    # print("廊间与转角的闭合")
    return LoggiaCornerJoined

# 尝试连接开放的转角
def __connect_open_corner(LoggiaNewJoined:bpy.types.Object,
                            dir):
    bData:acaData = LoggiaNewJoined.ACA_data
    
    # 找到合并目录
    JoinedColl:bpy.types.Collection = \
        bpy.context.scene.collection.children[con.COLL_NAME_ROOT_JOINED]
    LoggiaOpenCorner = None
    # 遍历根目录下的每个建筑
    for joinedObj in JoinedColl.objects:
        # 跳过新建的廊间
        if joinedObj == LoggiaNewJoined: continue
        # 仅遍历合并的廊间
        if joinedObj.ACA_data.combo_type != con.COMBO_LOGGIA:
            continue
        # 只取3位小数，否则无法比较
        joinedLoc = utils.round_vector(joinedObj.location)
        newLoggiaLoc = utils.round_vector(LoggiaNewJoined.location)

        # 判断新廊间与转角是否接近（面阔/2+进深/2）
        distance = utils.getVectorDistance(joinedLoc,newLoggiaLoc)
        roomdis = (bData.x_total/2 + bData.y_total/2)*1.414
        if abs(distance - roomdis) < 0.001:
            # 再进一步判断相邻廊间之间是否已经存在转角
            hasCorner = False
            for cornerObj in JoinedColl.objects:
                if cornerObj.ACA_data.combo_type != con.COMBO_LOGGIA_CORNER:
                    continue # 只检查转角，其他跳过
                if (cornerObj.location.x == joinedObj.location.x
                    and cornerObj.location.y == LoggiaNewJoined.location.y):
                    # 一侧有转角，跳过
                    hasCorner = True
                    break
                if (cornerObj.location.y == joinedObj.location.y
                    and cornerObj.location.x == LoggiaNewJoined.location.x):
                    # 一侧有转角，跳过
                    hasCorner = True
                    break
            
            # 如果未找到相连的转角，找到需闭合廊间
            if not hasCorner:
                LoggiaOpenCorner = joinedObj
                break # 命中退出循环

    if LoggiaOpenCorner is None: return
    # print("找到待闭合转角，廊间名称为：" + LoggiaOpenCorner.name)

    dirNext = None
    if joinedLoc.x > newLoggiaLoc.x and joinedLoc.y > newLoggiaLoc.y:
        dirNext = 'NE'
    if joinedLoc.x > newLoggiaLoc.x and joinedLoc.y < newLoggiaLoc.y:
        dirNext = 'SE'
    if joinedLoc.x < newLoggiaLoc.x and joinedLoc.y < newLoggiaLoc.y:
        dirNext = 'SW'
    if joinedLoc.x < newLoggiaLoc.x and joinedLoc.y > newLoggiaLoc.y:
        dirNext = 'NW'

    # 做L形转角
    LoggiaCornerJoined = __add_loggia_corner(
        baseLoggia = LoggiaNewJoined,
        dir = dirNext,
    )

    # 闭合廊间的裁剪 ------------------------
    # 横版
    if LoggiaOpenCorner.rotation_euler.z == 0:
        if dirNext in ('NE','SE'):
            dirCut = 'W'
        if dirNext in ('NW','SW'):
            dirCut = 'E'
    else:
        if dirNext in ('NE','NW'):
            dirCut = 'S'
        if dirNext in ('SW','SE'):
            dirCut = 'N'
    __cut_base_loggia(LoggiaOpenCorner,dirCut)

    # 转角屋顶裁剪 ---------------------------
    __add_loggia_intersection(
            fromLoggia = LoggiaNewJoined,
            toLoggia = LoggiaOpenCorner,
            cornerLoggia = LoggiaCornerJoined,
        )
    
    # 相邻廊间的标注
    if LoggiaOpenCorner.rotation_euler.z == 0:
        if dirNext == 'NE':
            signA = 'N'
            signB = 'W'
        if dirNext == 'NW':
            signA = 'N'
            signB = 'E'
        if dirNext == 'SW':
            signA = 'S'
            signB = 'E'
        if dirNext == 'SE':
            signA = 'S'
            signB = 'W'
    else:
        if dirNext == 'NE':
            signA = 'E'
            signB = 'S'
        if dirNext == 'NW':
            signA = 'W'
            signB = 'S'
        if dirNext == 'SW':
            signA = 'W'
            signB = 'N'
        if dirNext == 'SE':
            signA = 'E'
            signB = 'N'
    LoggiaNew = buildingJoin.getJoinedOriginal(LoggiaNewJoined)
    LoggiaNew.ACA_data['loggia_sign'] += '/' + signA
    LoggiaOpen = buildingJoin.getJoinedOriginal(LoggiaOpenCorner)
    LoggiaOpen.ACA_data['loggia_sign'] += '/' + signB

    return

# 设置回廊的螭吻显示状态
def __setLoggiaChiwen(Loggia:bpy.types.Object,dir:str):
    building,bData,oData = utils.getRoot(Loggia)
    isUnjoined = False

    # 如果不是庑殿、歇山、硬山、悬山，则不涉及螭吻的设置
    if bData.roof_style not in (con.ROOF_WUDIAN,
                         con.ROOF_XIESHAN,
                         con.ROOF_XUANSHAN,
                         con.ROOF_YINGSHAN):
        return

    # 判断回廊是否已经合并
    if bData.aca_type == con.ACA_TYPE_BUILDING_JOINED:
        # 临时取消合并
        Loggia = buildingJoin.undoJoin(building)
        # 记录取消合并，后续重新合并
        isUnjoined = True
    else:
        Loggia = building

    # 根据回廊可扩展性，觉得螭吻的显示
    zRot = Loggia.rotation_euler.z
    if (abs(zRot - math.radians(0)) < 0.001
        or abs(zRot - math.radians(180)) < 0.001):
        isWE = True
    else:
        isWE = False
    extSign = Loggia.ACA_data.loggia_sign
    chiwenPos = ''
    # 初始未延伸的回廊
    if extSign == '':
        if dir=='E':
            chiwenPos = 'L'
        # 初始右端
        elif dir=='W':
            chiwenPos = 'R'
    # 已延伸的回廊
    else:
        # 东西方向
        if isWE:
            # 中段不做螭吻
            if ('E' in extSign) and ('W' in extSign):
                chiwenPos = ''
            # 东端做右螭吻
            elif 'W' in extSign:
                chiwenPos = 'R'
            # 西端做左螭吻
            elif 'E' in extSign:
                chiwenPos = 'L'
        # 南北方向
        else:
            # 中段不做螭吻
            if ('N' in extSign) and ('S' in extSign):
                chiwenPos = ''
            # 北端做右螭吻
            elif 'S' in extSign:
                chiwenPos = 'R'
            # 南端做左螭吻
            elif 'N' in extSign:
                chiwenPos = 'L'
    
    # 获取螭吻
    chiwenObj = utils.getAcaChild(
        Loggia,con.ACA_TYPE_CHIWEN
    )
    if chiwenObj is None:
        # 未找到螭吻，退出
        return

    # 如果无需螭吻
    if chiwenPos == '':
        # 仅隐藏，供后续廊间参考
        utils.hideObj(chiwenObj)
    else:
        # 替换新螭吻，不管原来螭吻是否做了镜像
        from ..data import ACA_data_template as tmpData
        aData:tmpData = bpy.context.scene.ACA_temp
        tileRootObj = utils.getAcaChild(
            Loggia,con.ACA_TYPE_TILE_ROOT
        )
        chiwenNewObj = utils.copyObject(
            sourceObj=aData.chiwen_source,
            name=_('螭吻'),
            location=chiwenObj.location,
            scale=chiwenObj.scale,
            rotation=chiwenObj.rotation_euler,
            parentObj=tileRootObj,
            singleUser=True)
        chiwenNewObj.ACA_data['aca_type'] = con.ACA_TYPE_CHIWEN
        chiwenNewObj.users_collection[0].objects.unlink(chiwenNewObj)
        chiwenObj.users_collection[0].objects.link(chiwenNewObj)
        from .. import texture as mat
        mat.setGlazeStyle(chiwenNewObj,resetUV=False)

        if chiwenPos == 'L':
            # 保持原位
            chiwenNewObj.location.x = - abs(chiwenObj.location.x)
            chiwenNewObj.scale.x = abs(chiwenObj.scale.x)
        elif chiwenPos == 'R':
            # 放到右边
            chiwenNewObj.location.x = abs(chiwenObj.location.x)
            chiwenNewObj.scale.x = - abs(chiwenObj.scale.x)
        
        # 删除原螭吻
        utils.delObject(chiwenObj)

    # 重新合并
    if isUnjoined:
        Loggia = buildingJoin.joinBuilding(Loggia)
   
