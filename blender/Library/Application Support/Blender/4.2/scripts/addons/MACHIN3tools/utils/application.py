import bpy
import bpy_types
import bpy_restrict_state

def delay_execution(func, delay=0, persistent=False):
    if bpy.app.timers.is_registered(func):
        bpy.app.timers.unregister(func)

    bpy.app.timers.register(func, first_interval=delay, persistent=persistent)

def is_context_safe(context):
    if type(context) == bpy_types.Context:
        return True

    elif type(context) == bpy_restrict_state._RestrictContext:
        print("WARNING: Context is restricted!")
        return False

    else:
        print("WARNING: Unexpected Context Type", context, type(context))
        return False
