# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   进度条实现

import bpy
import time
import platform
import os
import tempfile
from . import utils
import threading

# --- global variables ---
verboseDebug = False

# ----- misc functions -----
# 统一文件路径格式
def unixifyPath(path):
	path = path.replace('\\', '/')
	return path

# return (ProgressValue, ProgressText)
# -10 = no progress file 
# -3 = crashed
# -11 = bad progress file format
def get_progress_status(theOp):
    ProgressText = ""
    ProgressValueFloat = None

    # 读取进度文件
    progressLines=[]
    try:
        pf = open(theOp.progressFilename, "r")
        progressLines = pf.read().splitlines()
        pf.close()
    except Exception:
        return -10, "" # 打开文件失败

    if len(progressLines)>=1:
        # 尝试读取第一行
        try:
            ProgressValueFloat = float(progressLines[0])
        except Exception:
            utils.outputMsg('Error getting progress info...')
        
        if ProgressValueFloat != None:
            # 如果第一行是负数，则显示第二行的提示文字
            if (ProgressValueFloat < 0):
                if len(progressLines)>=2:
                    ProgressText = progressLines[1]
                return ProgressValueFloat, ProgressText
            
            # 如果第一行是2，退出进程
            if ProgressValueFloat == 2:
                return ProgressValueFloat, ""

            # # check process is running: (NB need to be done in 2 cases : during building + if builder can't
            # if (theOp.BuildingTimerCounter > 2 and theOp.BuildingTimerCounter % 3 == 0): # only every 3 timer (~1 sec)
            # 	if (theOp.buildProcess.poll() != None):
            # 		ProgressValueFloat = -3    # this means that the builder crashed
            # 		ProgressText = "Building Failed! (-3)"
            # 		return ProgressValueFloat, ProgressText
            
            return ProgressValueFloat, ProgressText

# 启动进程
def doBuilding_Start(theOp, context) :
    # 变量重置
    theOp.progressFilename = None
    theOp.IsBuilding = False	

    # 文件路径（mac和win不一样）
    isMacOSX = (platform.system()=="Darwin") or (platform.system()=="macosx")
    if isMacOSX :
        QRTempFolder = "/var/tmp/"
    else :
        QRTempFolder = tempfile.gettempdir()
    if not os.path.exists(QRTempFolder):
        os.makedirs(QRTempFolder)

    export_path = os.path.join(QRTempFolder, "ACA")
    export_path = unixifyPath(export_path)
    if not os.path.exists(export_path):
        os.makedirs(export_path)

    theOp.progressFilename = os.path.join(export_path, 'progress.txt')
    
    # 删除历史文件
    if (os.path.isfile(theOp.progressFilename)):
        os.remove(theOp.progressFilename)

    # 写入新文件
    progress_file = open(theOp.progressFilename, "w")
    progress_file.write('0.1\n')
    progress_file.close()
    utils.outputMsg("Progress文件创建")

    # 启动定时器
    theOp.IsBuilding = True
    theOp.StartBuildingTime = time.time()
	
    return

# 结束进程
def doBuilding_Finish(theOp, context) :
	utils.outputMsg('doBuilding_Finish')

# 非阻塞的定时器
class ModalTimerOperator(bpy.types.Operator):
    bl_idname = "wm.modal_timer_operator"
    bl_label = "Modal Timer Operator"

    # class variables
    IsBuilding = False
    progressFilename = ""
    Aborted = False
    StartBuildingTime = 0
    BuildingTimerCounter = 0
    th = None

    @classmethod
    def poll(self, context):
        # 运行前检查
        return True
    
    def invoke(self, context, event):
        # 响应用户操作
        utils.outputMsg("invoke called!!!")
        self.execute(context)
        if self.IsBuilding:
            return {'RUNNING_MODAL'}
        else:
            return {'FINISHED'}

    def execute(self, context):
        # 启动定时器
        doBuilding_Start(self, context)

        # 启动新线程，执行营造任务
        self.th = threading.Thread(target=bpy.ops.aca.add_newbuilding)
        self.th.start()

        if (self.IsBuilding):
            wm = context.window_manager
			# add timer
            self.BuildingTimerCounter = 0
            self.timer = wm.event_timer_add(0.3, window=context.window)  
            wm.modal_handler_add(self)
            return {'RUNNING_MODAL'}  
        else:
            return {'FINISHED'}
    
    # 结束处理，在modal，cancel函数复用
    def onEndingOperator(self, context, isSuccess):
        wm = context.window_manager  
        # 移除定时器
        if self.timer != None:
            wm.event_timer_remove(self.timer)  
            self.timer = None
        # 重置各项参数
        self.IsBuilding = False
        self.progressFilename = ""
        self.Aborted = False
        self.StartBuildingTime = 0
        self.BuildingTimerCounter = 0

    def modal(self, context, event):  		
        # 执行操作，定时器会不断触发
        # utils.outputMsg("modal called.   event.type="+str(event.type))

        # 用户点击ESC，取消操作
        if event.type in {'ESC'}:
            self.report({'INFO'}, "Building CANCELLED !")
            self.onEndingOperator(context, False)
            return {'CANCELLED'}

        # 定时器不断触发逻辑
        if event.type == 'TIMER':
            # 计数器
            self.BuildingTimerCounter = self.BuildingTimerCounter + 1
			
			# 读取当前进度
            ProgressValueFloat, ProgressText = get_progress_status(self)   

            if not self.th.is_alive():
                self.th.join()
                utils.outputMsg('Threading is DONE')
                # return {'FINISHED'}       

            # 确认progress file已创建
            CurTimeFromStart = time.time() - self.StartBuildingTime
            if ProgressValueFloat == -10:   # no progress file found
                # 2秒未写入，警告
                if CurTimeFromStart > 2 :   # after 2 seconds without progressFile..
                    utils.outputMsg(' WARNING : no progressFile....')
                # 40秒未写入，超时结束进程
                if CurTimeFromStart > 40 :   # after 40 seconds without progressFile..
                    utils.outputMsg(' ERROR : no progressFile after 40s....')
                    self.report({'ERROR'}, "Building FAILED !")
                    self.onEndingOperator(context, False)
                    return {'FINISHED'}
                
            # 正在执行中
            if ProgressValueFloat >= 0 and ProgressValueFloat <= 1.0:
                newPBarValue = int( (99.0 * ProgressValueFloat + 1.0) )
				#utils.outputMsg('ProgressValueFloat=%s   newPBarValue=%s' % (str(ProgressValueFloat),str(newPBarValue)))
                self.report({'INFO'}, "Building progress:"+str(newPBarValue)+"% (ESC=Abort)")
                return {'RUNNING_MODAL'}
			
            # 执行成功
            elif ProgressValueFloat == 2:   # SUCCESS -> import the result
                doBuilding_Finish(self, context)
                self.onEndingOperator(context, True)
                self.report({'INFO'}, "Building Succeded !")
                return {'FINISHED'}
            
            # 执行失败
            elif ProgressValueFloat < 0:	# error returned
                utils.outputMsg(' RETURNING ERROR.... ProgressValueFloat='+str(ProgressValueFloat))
                self.onEndingOperator(context, False)
                if (ProgressText != None and len(ProgressText)>0):
                    self.report({'ERROR'}, ProgressText)
                else:
                    self.report({'ERROR'}, "Building FAILED !")
                return {'FINISHED'}
			
        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        # 取消操作
        utils.outputMsg("cancel called!!!")
        # 与正常处理类似，移除定时器、重置状态
        self.onEndingOperator(context, False)
        return {'CANCELLED'}