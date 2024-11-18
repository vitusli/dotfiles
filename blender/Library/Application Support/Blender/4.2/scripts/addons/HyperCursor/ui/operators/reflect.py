import bpy
from ... utils.registration import get_addon, get_addon_prefs

machin3tools = None
meshmachine = None

class Reflect(bpy.types.Operator):
    bl_idname = "machin3.reflect"
    bl_label = "MACHIN3: Reflect"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    @classmethod
    def description(cls, context, properties):
        global machin3tools, meshmachine

        active = context.active_object

        if machin3tools is None:
            machin3tools = get_addon('MACHIN3tools')[0]

            if machin3tools:
                m3prefs = get_addon_prefs('MACHIN3tools')

                if not m3prefs.activate_mirror:
                    m3prefs.activate_mirror = True

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        if machin3tools and meshmachine and context.active_object.type == 'MESH':
            return "Symmetrize\nALT: Mirror"

        elif machin3tools:
            return "Mirror"

        elif meshmachine and context.active_object.type == 'MESH':
            return "Symmetrize"

    def invoke(self, context, event):
        global machin3tools, meshmachine

        active = context.active_object

        if machin3tools is None:
            machin3tools = get_addon('MACHIN3tools')[0]

            if machin3tools:
                m3prefs = get_addon_prefs('MACHIN3tools')

                if not m3prefs.activate_mirror:
                    m3prefs.activate_mirror = True

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        if machin3tools and (meshmachine and active.type == 'MESH'):
            if event.alt:
                bpy.ops.machin3.mirror('INVOKE_DEFAULT', flick=True, remove=False)
            else:
                bpy.ops.machin3.symmetrize('INVOKE_DEFAULT', objmode=True, partial=False, remove=False)

        elif machin3tools:
            bpy.ops.machin3.mirror('INVOKE_DEFAULT', flick=True, remove=False)

        elif meshmachine and active.type == 'MESH':
            bpy.ops.machin3.symmetrize('INVOKE_DEFAULT', objmode=True, partial=False, remove=False)

        return {'FINISHED'}
