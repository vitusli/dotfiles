import bpy
from bpy.props import BoolProperty
from .. panels import draw_settings_panel, draw_help_panel, draw_object_panel
from ... utils.modifier import sort_modifiers 
from ... utils.ui import finish_status, force_obj_gizmo_update, force_ui_update

machin3tools = None

class HyperCursorSettings(bpy.types.Operator):
    bl_idname = "machin3.hyper_cursor_settings"
    bl_label = "MACHIN3: HyperCursor Settings"
    bl_description = "⚙ Hyper Cursor Settings"
    bl_options = {'INTERNAL'}

    def draw(self, context):
        draw_settings_panel(self, context, draw_grip=True)

    def execute(self, context):
        return context.window_manager.invoke_popup(self, width=300)

class HyperCursorHelp(bpy.types.Operator):
    bl_idname = "machin3.hyper_cursor_help"
    bl_label = "MACHIN3: HyperCursor Help"
    bl_description = "ℹ Hyper Cursor Help\n\nKeymaps, Documentation and Support"
    bl_options = {'INTERNAL'}

    def draw(self, context):
        draw_help_panel(self, context)

    def execute(self, context):
        return context.window_manager.invoke_popup(self, width=250)

class HyperCursorObject(bpy.types.Operator):
    bl_idname = "machin3.hyper_cursor_object"
    bl_label = "MACHIN3: HyperCursor Object"
    bl_options = {'REGISTER', 'UNDO'}

    hide_all_visible_wire_objs: BoolProperty(name="Hide all visible Wire Objects", description="Hide all visible Wire Objects and Empties", default=False)
    sort_modifiers: BoolProperty(name="Sort Modifiers", default=False)
    cycle_object_tree: BoolProperty(name="Cycle Object Tree", description="Toggle Visibility of Wire/Bounds/Empty Objects in the Object Tree", default=False)
    include_mod_objects: BoolProperty(name="Include Mod Objects", description="Include Mod Objects, that aren't parented in the Object Tree", default=True)
    last = None

    @classmethod
    def description(cls, context, properties):
        desc = "Hyper Cursor Object Menu"

        desc += "\n\nCTRL: Manually force Modifier Sorting + Object Gizmo Update"

        desc += "\n\nALT: Hide all visible Wire Objects and Empties"
        desc += "\nShortcut: Alt + ESC"

        return desc

    def draw(self, context):
        if self.is_panel:
            draw_object_panel(self, context)

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

        context.scene.HC.show_object_gizmos = True

        context.active_object.select_set(True)

    def invoke(self, context, event):
        self.sort_modifiers = event.ctrl
        self.hide_all_visible_wire_objs = event.alt

        self.is_panel = False

        if self.hide_all_visible_wire_objs:
            bpy.ops.machin3.hide_wire_objects()
            return {'FINISHED'}

        elif self.sort_modifiers:
            sort_modifiers(obj=context.active_object, debug=False)

            force_obj_gizmo_update(context)
            return {'FINISHED'}

        else:
            self.is_panel = True
            return self.execute(context)

    def execute(self, context):
        bpy.types.MACHIN3_OT_hyper_cursor_object.last = None
        return context.window_manager.invoke_popup(self, width=250)
