import bpy

class MirrorHide(bpy.types.Macro):
    bl_idname = "machin3.macro_mirror_hide"
    bl_label = "MACHIN3: Mirror Hide Macro"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return getattr(bpy.types, 'MACHIN3_OT_mirror', False)

    def init():
        MirrorHide.define('MACHIN3_OT_hide_mirror_obj').properties.unhide = True
        if getattr(bpy.types, 'MACHIN3_OT_mirror', False):
            op = MirrorHide.define('MACHIN3_OT_mirror')
            op.properties.flick = True
            op.properties.remove = False

        MirrorHide.define('MACHIN3_OT_hide_mirror_obj').properties.unhide = False
