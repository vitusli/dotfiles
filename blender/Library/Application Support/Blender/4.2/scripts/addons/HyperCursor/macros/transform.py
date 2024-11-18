import bpy
from .. utils.registration import get_addon

class Translate(bpy.types.Macro):
    bl_idname = "machin3.macro_hyper_cursor_translate"
    bl_label = "MACHIN3: Translate Macro"
    bl_options = {'INTERNAL'}

    def init():
        Translate.define('TRANSFORM_OT_translate')
        Translate.define('WM_OT_context_toggle')

class Rotate(bpy.types.Macro):
    bl_idname = "machin3.macro_hyper_cursor_rotate"
    bl_label = "MACHIN3: Rotate Macro"
    bl_options = {'INTERNAL'}

    def init():
        Rotate.define('TRANSFORM_OT_rotate')
        Rotate.define('WM_OT_context_toggle')

class BooleanTranslate(bpy.types.Macro):
    bl_idname = "machin3.macro_hyper_cursor_boolean_translate"
    bl_label = "MACHIN3: Boolean Translate Macro"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object

            if active and active.parent:
                booleans = [mod for mod in active.parent.modifiers if mod.type == 'BOOLEAN' and mod.object == active]
                return booleans

    def init():
        BooleanTranslate.define('MACHIN3_OT_remove_boolean_from_parent')
        BooleanTranslate.define('TRANSFORM_OT_translate')
        BooleanTranslate.define('MACHIN3_OT_restore_boolean_on_parent')

class BooleanDuplicateTranslate(bpy.types.Macro):
    bl_idname = "machin3.macro_hyper_cursor_boolean_duplicate_translate"
    bl_label = "MACHIN3: Boolean Duplicate Macro"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object

            if active and active.parent:
                booleans = [mod for mod in active.parent.modifiers if mod.type == 'BOOLEAN' and mod.object == active]
                return booleans

    def init():
        BooleanDuplicateTranslate.define('MACHIN3_OT_duplicate_boolean_operator')
        BooleanDuplicateTranslate.define('TRANSFORM_OT_translate')
        BooleanDuplicateTranslate.define('MACHIN3_OT_restore_boolean_on_parent').properties.duplicate = True
