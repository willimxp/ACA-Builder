# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   进度条实现

import bpy

class ModalTimerOperator(bpy.types.Operator):
    bl_idname = "wm.modal_timer_operator"
    bl_label = "Modal Timer Operator"

    _timer = None

    def modal(self, context, event):
        [a.tag_redraw() for a in context.screen.areas]
        if self._timer.time_duration > 3:
            context.window_manager.progress = 1
            return {'FINISHED'}
        context.window_manager.progress = self._timer.time_duration / 3
        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def progress_bar(self, context):
    row = self.layout.row()
    row.progress(
        factor=context.window_manager.progress,
        type="BAR",
        text="Operation in progress..." if context.window_manager.progress < 1 else "Operation Finished !"
    )
    row.scale_x = 2
    

def register():
    bpy.types.WindowManager.progress = bpy.props.FloatProperty()
    bpy.utils.register_class(ModalTimerOperator)
    #bpy.types.TEXT_HT_header.append(progress_bar)
    bpy.types.STATUSBAR_HT_header.append(progress_bar)
    bpy.ops.wm.modal_timer_operator()