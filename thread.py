import bpy


class ModalTimerOperator(bpy.types.Operator):
    """Operator which runs its self from a timer"""
    bl_idname = "wm.modal_timer_operator"
    bl_label = "Modal Timer Operator"

    _timer = None
    th = None
    prog = 0
    stop_early = False

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)

            self.stop_early = True
            self.th.join()
            print('DONE EARLY')

            return {'CANCELLED'}

        if event.type == 'TIMER':
            context.scene.ProgressWidget_progress = self.prog

            if not self.th.isAlive():
                self.th.join()
                print('DONE')
                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        import threading

        def long_task(self):
            import time
            for i in range(10):
                if self.stop_early:
                    return

                time.sleep(.5)
                self.prog += 10

        self.th = threading.Thread(target=long_task, args=(self,))

        bpy.ops.custom.show_progress_widget()
        self.th.start()

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)


def register():
    bpy.utils.register_class(ModalTimerOperator)


def unregister():
    bpy.utils.unregister_class(ModalTimerOperator)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.wm.modal_timer_operator()