import bpy
from .. utils.modifier import hypercut_poll, hyperbevel_poll
from .. utils.tools import get_active_tool
from .. utils.registration import get_prefs

def modifier_buttons(self, context):
    if get_prefs().show_mod_panel:
        layout = self.layout

        if context.active_object and context.active_object.modifiers:
            column = layout.column(align=True)

            row = column.split(factor=0.25, align=True)
            row.label(text='All')
            op = row.operator('machin3.toggle_all_modifiers', text='Toggle', icon='RESTRICT_VIEW_OFF')
            op.active_only = False
            op = row.operator('machin3.apply_all_modifiers', text='Apply', icon='IMPORT')
            op.active_only = False
            op = row.operator('machin3.remove_all_modifiers', text='Remove', icon='X')
            op.active_only = False

            active = context.active_object
            booleans = [mod for mod in active.modifiers if mod.type == 'BOOLEAN']

            if booleans:
                column.separator()

                row = column.split(factor=0.25, align=True)
                row.label(text='Boolean')
                row.operator('machin3.remove_unused_booleans', text='Remove Unused', icon='MOD_BOOLEAN')

class MenuHyperCursorMeshContext(bpy.types.Menu):
    bl_idname = "MACHIN3_MT_hypercursor_mesh_context_menu"
    bl_label = "HyperCursor"

    def draw(self, context):
        layout = self.layout

        is_preview = context.active_object.HC.geometry_gizmos_show_previews
        select_mode = 'Face' if tuple(bpy.context.scene.tool_settings.mesh_select_mode) == (False, False, True) else 'Edge'

        layout.operator('machin3.toggle_gizmo_data_layer_preview', text=f"{'Disable' if is_preview else 'Enable'} Gizmo Preview")
        layout.operator('machin3.toggle_gizmo', text=f"Toggle {select_mode} Gizmo")

def mesh_context_menu(self, context):
    layout = self.layout

    valid_select_mode = tuple(bpy.context.scene.tool_settings.mesh_select_mode) in [(False, True, False), (False, False, True)]

    if get_active_tool(context).idname in ['machin3.tool_hyper_cursor', 'machin3.tool_hyper_cursor_simple'] and valid_select_mode:

        layout.menu("MACHIN3_MT_hypercursor_mesh_context_menu")
        layout.separator()
