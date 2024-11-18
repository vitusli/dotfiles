import bpy
from ... utils.draw import draw_fading_label
from ... utils.property import step_enum
from ... utils.tools import get_active_tool
from ... utils.ui import force_geo_gizmo_update, force_ui_update
from ... items import edit_mode_items
from ... preferences import tool_keymaps

class ToggleTools(bpy.types.Operator):
    bl_idname = "machin3.toggle_hyper_cursor_tools"
    bl_label = "MACHIN3: Toggle Hyper Cursor Tools"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        tool = get_active_tool(context)
        return tool and 'machin3.tool_hyper_cursor' in tool.idname

    def execute(self, context):
        active_tool = get_active_tool(context)

        if active_tool.idname == 'machin3.tool_hyper_cursor':
            bpy.ops.wm.tool_set_by_id(name='machin3.tool_hyper_cursor_simple')

        elif active_tool.idname == 'machin3.tool_hyper_cursor_simple':
            bpy.ops.wm.tool_set_by_id(name='machin3.tool_hyper_cursor')

        return {'FINISHED'}

class ToggleGizmos(bpy.types.Operator):
    bl_idname = "machin3.toggle_hyper_cursor_gizmos"
    bl_label = "MACHIN3: Toggle Hyper Cursor Gizmos"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        tool = get_active_tool(context)
        return tool and 'machin3.tool_hyper_cursor' in tool.idname

    def execute(self, context):
        hc = context.scene.HC

        hc.show_gizmos = not hc.show_gizmos

        if not hc.draw_HUD:
            hc.draw_HUD = True

        force_ui_update(context)

        return {'FINISHED'}

class ToggleWorld(bpy.types.Operator):
    bl_idname = "machin3.toggle_hyper_cursor_world"
    bl_label = "MACHIN3: Toggle World Mode"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        tool = get_active_tool(context)
        return tool and 'machin3.tool_hyper_cursor' in tool.idname

    def execute(self, context):
        context.scene.HC.use_world = not context.scene.HC.use_world

        return {'FINISHED'}

class ToggleGeometryGizmos(bpy.types.Operator):
    bl_idname = "machin3.toggle_hyper_cursor_geometry_gizmos"
    bl_label = "MACHIN3: Toggle Geometry Gizmos"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            tool = get_active_tool(context)
            if tool and 'machin3.tool_hyper_cursor' in tool.idname:
                active = context.active_object
                return active and active.type == 'MESH' and active.select_get() and active.HC.ishyper

    def execute(self, context):
        active = context.active_object

        if not active.HC.geometry_gizmos_show and len(active.data.polygons) > active.HC.geometry_gizmos_show_limit:
            draw_fading_label(context, text=f"{active.name}'s Mesh is too dense for any Geometry Gizmos!", color=(1, 0.3, 0), alpha=1, move_y=20, time=2)
            return {'CANCELLED'}

        active.HC.geometry_gizmos_show = not active.HC.geometry_gizmos_show

        force_geo_gizmo_update(context)

        return {'FINISHED'}

class ToggleXRayGizmos(bpy.types.Operator):
    bl_idname = "machin3.toggle_hyper_cursor_xray_gizmos"
    bl_label = "MACHIN3: Toggle X-Ray Gizmos"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            tool = get_active_tool(context)
            if tool and 'machin3.tool_hyper_cursor' in tool.idname:
                active = context.active_object

                if active and active.type == 'MESH' and active.display_type not in ['WIRE', 'BOUNDS'] and active.select_get() and active.HC.ishyper:
                    return active.HC.geometry_gizmos_show

    def execute(self, context):
        context.scene.HC.gizmo_xray = not context.scene.HC.gizmo_xray

        force_ui_update(context)

        return {'FINISHED'}

class ToggleEditMode(bpy.types.Operator):
    bl_idname = "machin3.toggle_hyper_cursor_edit_mode"
    bl_label = "MACHIN3: Toggle Gizmo Edit Mode"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            tool = get_active_tool(context)
            if tool and 'machin3.tool_hyper_cursor' in tool.idname:
                active = context.active_object
                return active and active.type == 'MESH' and active.select_get() and active.HC.ishyper

    def execute(self, context):
        active = context.active_object

        if active.HC.geometry_gizmos_edit_mode == 'SCALE':

            if active.HC.objtype == 'CUBE' and len(active.data.polygons) > active.HC.geometry_gizmos_show_cube_limit:
                draw_fading_label(context, text=f"{active.name}'s Polygon Count is too high for EDIT Geometry Gizmos!", color=(1, 0.3, 0), alpha=1, move_y=20, time=2)
                return {'CANCELLED'}

            elif active.HC.objtype == 'CYLINDER' and len(active.data.edges) > active.HC.geometry_gizmos_show_cylinder_limit:
                draw_fading_label(context, text=f"{active.name}'s Edge Count is too high for EDIT Geometry Gizmos!", color=(1, 0.3, 0), alpha=1, move_y=20, time=2)
                return {'CANCELLED'}

        if active.HC.geometry_gizmos_show:
            active.HC.geometry_gizmos_edit_mode = step_enum(active.HC.geometry_gizmos_edit_mode, edit_mode_items, step=1)

        else:
            active.HC.geometry_gizmos_show = True

        force_geo_gizmo_update(context)
        return {'FINISHED'}
