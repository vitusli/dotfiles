import bpy
from ... utils.ui import get_keymap_item, get_modified_keymap_items

class SetupGenericGizmoKeymap(bpy.types.Operator):
    bl_idname = "machin3.setup_generic_gizmo_keymap"
    bl_label = "MACHIN3: Setup Generic Gizmo Keymap"
    bl_description = "Setup Generic Gizmo Keymap"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        generic_gizmo = get_keymap_item('Generic Gizmo', 'gizmogroup.gizmo_tweak')

        if generic_gizmo:
            return not generic_gizmo.any

    @classmethod
    def description(cls, context, properties):
        desc = "Blender 3.0 introduced a change, making it impossible to ALT click Gizmos by default."
        desc += "\nHyperCursor makes heavy use of modifier keys for gizmos, including the ALT key."
        desc += "\nTo take advantage of all features, the Generic Gizmo Keymap has to be adjusted."
        return desc

    def execute(self, context):
        generic_gizmo = get_keymap_item('Generic Gizmo', 'gizmogroup.gizmo_tweak')
        generic_gizmo.any = True

        print("INFO: Setup Generic Gizmo to support ANY key modifier")

        return {'FINISHED'}

class ResetKeymaps(bpy.types.Operator):
    bl_idname = "machin3.reset_hyper_cursor_keymaps"
    bl_label = "MACHIN3: Reset Hyper Cursor Keymaps"
    bl_description = "This will undo all HyperCursor Keymap changes you have done" 
    bl_options = {'REGISTER'}

    def execute(self, context):
        kmis = get_modified_keymap_items(context)

        for (km, kmi) in kmis:

            if kmi:
                if kmi.idname == 'wm.tool_set_by_id' and (props := kmi.properties) and "machin3.tool_hyper_cursor" in (name := props.get('name')):
                    km.restore_item_to_default(kmi)
                    print(f"INFO: Keymap item: '{kmi.name} > {name}' has been restored to: '{kmi.to_string()}', active: {kmi.active}")

                else:
                    km.restore_item_to_default(kmi)
                    print(f"INFO: Keymap item: '{kmi.name}' has been restored to: '{kmi.to_string()}, active: {kmi.active}'")

            else:
                km.restore_to_default()
        return {'FINISHED'}
