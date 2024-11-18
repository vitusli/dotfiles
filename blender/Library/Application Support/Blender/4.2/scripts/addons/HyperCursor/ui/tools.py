import bpy
import os
from .. utils.ui import draw_tool_header
from .. utils.registration import get_path
from .. registration import keys

class HyperCursor(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_idname = "machin3.tool_hyper_cursor"
    bl_label = "Hyper Cursor"
    bl_description = ("Cursor Transformation, Cursor History Management, Object and Asset Creation, Kitbashing and Mesh-from-Object-Mode Manipulation")
    bl_icon = os.path.join(get_path(), 'icons', 'machin3.hypercursor')
    bl_widget = "MACHIN3_GGT_hyper_cursor"
    bl_keymap = keys['HYPERCURSOR']

    def draw_settings(context, layout, tool):
        draw_tool_header(context, layout, tool)

class HyperCursorSimple(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_idname = "machin3.tool_hyper_cursor_simple"
    bl_label = "Simple Hyper Cursor"
    bl_description = ("Minimalistic Cursor Transformation, Cursor History Cycling, Object Creation and Mesh Manipulation")
    bl_icon = os.path.join(get_path(), 'icons', 'machin3.hypercursor.simple')
    bl_widget = "MACHIN3_GGT_hyper_cursor_simple"

    def draw_settings(context, layout, tool):
        draw_tool_header(context, layout, tool)

class HyperCursorEditMesh(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = "machin3.tool_hyper_cursor"
    bl_label = "Hyper Cursor"
    bl_description = ("Mesh-From-Object-Mode Manipulation")
    bl_icon = os.path.join(get_path(), 'icons', 'machin3.hypercursor')
    bl_widget = "MACHIN3_GGT_hyper_cursor"
    bl_keymap = keys['HYPERCURSOREDIT']

    def draw_settings(context, layout, tool):
        draw_tool_header(context, layout, tool)

class HyperCursorSimpleEditMesh(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = "machin3.tool_hyper_cursor_simple"
    bl_label = "Simple Hyper Cursor"
    bl_description = ("Minimalistic Cursor Transformation and Cursor History Cycling")
    bl_icon = os.path.join(get_path(), 'icons', 'machin3.hypercursor.simple')
    bl_widget = "MACHIN3_GGT_hyper_cursor_simple"

    def draw_settings(context, layout, tool):
        draw_tool_header(context, layout, tool)
