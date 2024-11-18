import bpy
from bpy.props import StringProperty, BoolProperty

class CallHyperCursorOperator(bpy.types.Operator):
    bl_idname = "machin3.call_hyper_cursor_operator"
    bl_label = "MACHIN3: Call Hyper Cursor Operator"
    bl_options = {'INTERNAL', 'UNDO'}

    idname: StringProperty()
    args: StringProperty()

    invoke: BoolProperty()
    desc: StringProperty()

    @classmethod
    def description(cls, context, properties):
        return properties.desc

    def invoke(self, context, event):
        if self.idname == 'TOGGLE_HISTORY_DRAWING':
            hc = context.scene.HC

            hc.draw_history = not hc.draw_history

        else:
            op = getattr(bpy.ops.machin3, self.idname, None)
            args = eval(self.args) if self.args else None

            if op:
                if self.invoke:
                    op('INVOKE_DEFAULT', **args) if args else op('INVOKE_DEFAULT')

                else:
                    op(**args) if args else op()

        return {'FINISHED'}
