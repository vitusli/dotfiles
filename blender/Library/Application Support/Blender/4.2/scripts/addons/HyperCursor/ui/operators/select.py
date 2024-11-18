import bpy
from bpy.props import StringProperty

class SelectObject(bpy.types.Operator):
    bl_idname = "machin3.select_object"
    bl_label = "MACHIN3: Select Object"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    objname: StringProperty(name="Name of Object to Select")

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        active = context.active_object

        obj = bpy.data.objects.get(self.objname)

        if obj:
            bpy.types.MACHIN3_OT_hyper_cursor_object.last = active.name if active else ''

            if not obj.visible_get():
                obj.hide_set(False)

            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj

        return {'FINISHED'}
