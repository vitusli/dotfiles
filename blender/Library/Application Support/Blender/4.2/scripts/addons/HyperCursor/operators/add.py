import bpy
from bpy.props import EnumProperty, BoolProperty, FloatProperty, IntProperty
import bmesh
from bpy.utils import time_from_frame
from mathutils import Vector, Matrix, Quaternion
from mathutils.geometry import intersect_line_plane, intersect_point_line
from math import radians, degrees, tan, sqrt
from itertools import zip_longest
from uuid import uuid4
from .. utils.ui import get_mouse_pos, ignore_events, is_on_screen, navigation_passthrough, get_zoom_factor, warp_mouse, wrap_mouse, init_status, finish_status, scroll_up, scroll_down, force_ui_update, get_scale
from .. utils.curve import get_curve_as_dict, get_profile_coords_from_spline, verify_curve_data
from .. utils.draw import draw_fading_label, draw_init, draw_label, draw_line, draw_point, draw_vector, draw_points
from .. utils.math import dynamic_snap, dynamic_format, average_locations, average_normals, create_rotation_matrix_from_vectors, get_center_between_verts
from .. utils.property import step_enum
from .. utils.object import enable_auto_smooth, get_eval_bbox, get_visible_objects, hide_render, parent, is_uniform_scale, is_wire_object, remove_obj
from .. utils.mesh import get_bbox
from .. utils.raycast import cast_bvh_ray_from_mouse, get_closest, cast_scene_ray_from_mouse
from .. utils.modifier import add_boolean, add_subdivision, add_cast, add_mirror, get_edge_bevel_from_edge, get_subdivision, get_cast, get_auto_smooth, apply_mod, add_bevel, bevel_poll, is_edge_bevel, is_invalid_auto_smooth, mirror_poll, remove_mod, sort_modifiers, add_displace, hook_poll, create_bevel_profile
from .. utils.vgroup import add_vgroup
from .. utils.workspace import get_assetbrowser_area
from .. utils.asset import get_pretty_assetpath
from .. utils.gizmo import hide_gizmos, restore_gizmos
from .. utils.bmesh import ensure_edge_glayer, ensure_gizmo_layers
from .. utils.registration import get_prefs
from .. utils.system import printd
from .. utils.view import get_location_2d, get_view_origin_and_dir
from .. items import add_object_items, axis_items, add_cylinder_side_items, add_boolean_method_items, add_boolean_solver_items, number_mappings, display_type_items, boolean_display_type_items, pipe_round_mode_items, axis_vector_mappings, pipe_origin_items, numbers, input_mappings
from .. colors import green, red, normal, blue, yellow, orange, white

def draw_add_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text="Add %s" % (op.type.title()))

        if op.is_numeric_input:
            row.label(text="", icon='EVENT_RETURN')
            row.label(text="Confirm")

            row.label(text="", icon='EVENT_ESC')
            row.label(text="Cancel")

            row.label(text="", icon='EVENT_TAB')
            row.label(text="Abort Numeric Input")

            row.separator(factor=10)

            row.label(text="Numeric Input...")

        else:

            row.label(text="", icon='MOUSE_LMB')
            row.label(text="Finish")

            if op.is_in_history:
                row.label(text="", icon='MOUSE_MMB')
                row.label(text="Finish with Last Size")

            row.label(text="", icon='MOUSE_RMB')
            row.label(text="Cancel")

            row.label(text="", icon='EVENT_TAB')
            row.label(text="Enter Numeric Input")

            row.separator(factor=10)

            row.label(text="", icon='MOUSE_MOVE')
            row.label(text=f"Size: {dynamic_format(op.size, decimal_offset=1 if op.is_snapping and op.is_incremental else 0 if op.is_snapping else 2)}")

            row.separator(factor=1)

            row.label(text="", icon='EVENT_CTRL')
            row.label(text="Dynamic Snap")

            if op.is_snapping:
                row.separator(factor=1)

                row.label(text="", icon='EVENT_ALT')
                row.label(text="Incremental Snap")

            if op.type == 'CYLINDER':
                row.separator(factor=1)

                if not op.boolean:
                    row.label(text="", icon='MOUSE_MMB')

                row.label(text=f"Sides: {op.sides}")

                row.separator(factor=1)

                row.label(text="", icon='EVENT_Q')
                row.label(text=f"Presets: {op.use_side_presets}")

            elif op.type == 'ASSET':
                row.separator(factor=1)

                row.label(text="", icon='EVENT_R')
                row.label(text=f"Rotate: {op.HUD_angle}")

            if op.boolean_parent and op.obj.type == 'MESH':

                if not (op.type in ['CUBE', 'CYLINDER'] and op.is_plane):
                    row.separator(factor=2)

                    r = row.row()
                    r.active = op.can_boolean

                    r.label(text="", icon='EVENT_B')
                    r.label(text=f"Booolean: {op.boolean}")

                    if op.boolean:
                        r.separator(factor=1)

                        r.label(text="", icon='MOUSE_MMB')
                        r.label(text=f"Method: {op.boolean_method.title()}")

                        r.separator(factor=1)

                        r.label(text="", icon='EVENT_E')
                        r.label(text="", icon='EVENT_F')
                        r.label(text=f"Solver: {op.boolean_solver.title()}")

                        row.separator(factor=1)

                        row.label(text="", icon='EVENT_W')
                        row.label(text=f"Display: {op.obj.display_type.title()}")

            if not op.obj.type == 'EMPTY':

                if not (op.type in ['CUBE', 'CYLINDER'] and op.is_plane and op.align_axis == 'Z'):
                    row.separator(factor=2)

                    row.label(text="", icon='EVENT_S')
                    row.label(text=f"Surface Placement: {op.is_surface}")

                    row.separator(factor=1)

                    row.label(text="", icon='EVENT_D')
                    row.label(text=f"Embedded Placement: {op.is_embed}")

                    if op.is_embed:
                        row.separator(factor=1)

                        row.label(text="", icon='EVENT_SHIFT')
                        row.label(text="", icon='MOUSE_MMB')
                        row.label(text=f"Depth: {round(op.embed_depth, 1)}")

            if op.type in ['CYLINDER', 'ASSET'] or (op.type == 'CUBE' and op.is_plane):
                row.separator(factor=1)

                row.label(text="", icon='EVENT_X')
                row.label(text="", icon='EVENT_Y')
                row.label(text=f"Align Axis: {op.align_axis}")

            if op.type == 'CUBE':
                row.separator(factor=2)

                if not op.is_plane:
                    row.label(text="", icon='EVENT_Q')
                    row.label(text=f"Quad Sphere: {op.is_quad_sphere}")

                    if op.is_quad_sphere:
                        row.separator(factor=1)

                        row.label(text="", icon='EVENT_ALT')
                        row.label(text="", icon='MOUSE_MMB')
                        row.label(text=f"Subdivisions: {op.subdivisions}")

                    row.separator(factor=1)

                    row.label(text="", icon='EVENT_R')
                    row.label(text=f"Rounded Cube: {op.is_rounded}")

                    if op.is_rounded:
                        row.separator(factor=1)

                        row.label(text="", icon='EVENT_ALT')
                        row.label(text="", icon='MOUSE_MMB')
                        row.label(text=f"Segments: {op.bevel_segments}")

                    row.separator(factor=1)

                row.label(text="", icon='EVENT_C')
                row.label(text=f"Plane: {op.is_plane}")

            elif op.type in 'CYLINDER':
                row.separator(factor=2)

                if not op.is_plane:
                    row.label(text="", icon='EVENT_R')
                    row.label(text=f"Rounded Cylinder: {op.is_rounded}")

                    if op.is_rounded:
                        row.separator(factor=1)

                        row.label(text="", icon='EVENT_ALT')
                        row.label(text="", icon='MOUSE_MMB')
                        row.label(text=f"Segments: {op.bevel_segments}")

                    row.separator(factor=1)

                row.label(text="", icon='EVENT_C')
                row.label(text=f"Circle: {op.is_plane}")

                row.separator(factor=1)

                row.label(text="", icon='EVENT_V')
                row.label(text=f"Half: {op.is_half}")

            if op.is_scale_appliable:
                row.separator(factor=2)

                row.label(text="", icon='EVENT_A')
                row.label(text=f"Apply Scale: {op.apply_scale}")

            if op.type in 'ASSET' and op.has_subset_mirror:
                row.label(text="", icon='EVENT_M')
                row.label(text=f"Subset Mirror: {op.is_subset_mirror}")

    return draw

class AddObjectAtCursor(bpy.types.Operator):
    bl_idname = "machin3.add_object_at_cursor"
    bl_label = "MACHIN3: Add Object at Cursor"
    bl_options = {'REGISTER', 'UNDO'}

    is_drop: BoolProperty(name="is Drop Asset", default=False)
    type: EnumProperty(name="Add Object Type", items=add_object_items, default='CUBE')

    def update_is_surface(self, context):
        if not self.is_interactive:
            if self.avoid_update:
                self.avoid_update = False
                return

            if self.is_surface:
                if self.is_embed:
                    self.avoid_update = True
                    self.is_embed = False

    def update_is_embed(self, context):
        if not self.is_interactive:
            if self.avoid_update:
                self.avoid_update = False
                return

            if self.is_embed:
                if self.is_surface:
                    self.avoid_update = True
                    self.is_surface = False

    def update_rotation_offset(self, context):
        if not self.is_interactive:
            if self.avoid_update:
                self.avoid_update = False
                return

            if self.rotation_offset > 360:
                self.avoid_update = True
                self.rotation_offset = 360

            elif self.rotation_offset < 0:
                self.avoid_update = True
                self.rotation_offset = 360 + self.rotation_offset

    is_surface: BoolProperty(name="Add Object at Cursor's Surface (Z-Plane)", description='Place Object on Surface', default=True, update=update_is_surface)
    is_embed: BoolProperty(name="Add Object embedded in Cursor's Surface (Z-Plane)", description='Embed Object in Surface', default=False, update=update_is_embed)
    embed_depth: FloatProperty(name="Embed Depth", default=0.1, min=0.1, max=0.9)
    rotation_offset: IntProperty(name="Rotation Offset", default=0, update=update_rotation_offset)
    align_axis: EnumProperty(name="Align with Axis", items=axis_items, default='Z')
    apply_scale: BoolProperty(name="Apply Scale", default=True)

    def update_is_quad_sphere(self, context):
        if not self.is_interactive:
            if self.avoid_update:
                self.avoid_update = False
                return

            if self.is_quad_sphere:

                if not self.is_subd:
                    self.avoid_update = True
                    self.is_subd = True

                if self.is_rounded:
                    self.avoid_update = True
                    self.is_rounded = False
                
                if self.is_plane:
                    self.avoid_update = True
                    self.is_plane = False

            else:
                if self.is_subd:
                    self.avoid_update = True
                    self.is_subd = False

    def update_is_plane(self, context):
        if not self.is_interactive:
            if self.avoid_update:
                self.avoid_update = False
                return

            if self.is_plane:

                if self.is_quad_sphere:
                    self.avoid_update = True
                    self.is_quad_sphere = False

                    if self.is_subd:
                        self.avoid_update = True
                        self.is_subd = False

                if self.is_rounded:
                    self.avoid_update = True
                    self.is_rounded = False

                if self.is_surface:
                    self.avoid_update = True
                    self.is_surface = False

                if self.is_embed:
                    self.avoid_update = True
                    self.is_embed = False

            else:
                if self.type == 'CUBE':
                    self.align_axis = 'Z'

    def update_is_rounded(self, context):
        if not self.is_interactive:
            if self.avoid_update:
                self.avoid_update = False
                return

            if self.is_rounded:

                if self.is_quad_sphere:
                    self.avoid_update = True
                    self.is_quad_sphere = False

                if self.is_subd:
                    self.avoid_update = True
                    self.is_subd = False

                if self.is_plane:
                    self.avoid_update = True
                    self.is_plane = False

    def update_is_subd(self, context):
        if not self.is_interactive:
            if self.avoid_update:
                self.avoid_update = False
                return

            if self.is_subd:

                if self.is_rounded:
                    self.avoid_update = True
                    self.is_rounded = False

    size: FloatProperty(name="Size of Object", default=1)
    sides: IntProperty(name="Sides", default=32, min=3)
    is_quad_sphere: BoolProperty(name="is Quad Sphere", default=False, update=update_is_quad_sphere)
    is_plane: BoolProperty(name="is Plane", default=False, update=update_is_plane)
    is_subd: BoolProperty(name="is SubD", default=False, update=update_is_subd)
    subdivisions: IntProperty(name="Subdivide", default=3, min=1, max=5)
    is_rounded: BoolProperty(name="is Rounded", default=False, update=update_is_rounded)
    bevel_count: IntProperty(name="Bevel Mod Count", default=1, min=1, max=4)
    bevel_segments: IntProperty(name="Bevel Segments", default=0, min=0)
    is_half: BoolProperty(name="is Semi", default=False)
    is_subset_mirror: BoolProperty(name="is Subset MIrror", default=True)

    boolean: BoolProperty(name="Boolean", default=False)
    boolean_method: EnumProperty(name="Method", items=add_boolean_method_items, default='DIFFERENCE')
    boolean_solver: EnumProperty(name="Solver", items=add_boolean_solver_items, default='FAST')
    boolean_display_type: EnumProperty(name="Boolean Display Type", items=display_type_items, default='WIRE')
    hide_boolean: BoolProperty(name="Hide Boolean", default=False)

    use_side_presets: BoolProperty(name="Adjust Cylidner Sides via Presets", default=True)
    is_scale_appliable: BoolProperty(name="is Scale appliable", default=False)
    is_in_history: BoolProperty(name="is Object in History", default=False)
    is_pipe_init: BoolProperty(name="is Pipe Init", default=False)  # used for MACHIN3tools screencasting

    is_interactive: BoolProperty()
    avoid_update: BoolProperty()

    @classmethod
    def description(cls, context, properties):
        desc = f"Drag out {properties.type.title()} from Cursor\nALT: Repeat Size\nCTRL: Unit Size"

        if properties.type == 'CYLINDER':
            desc += "\nSHIFT: Initialize Pipe"

        return desc

    def draw_HUD(self, context): 
        if context.area == self.area:
            draw_init(self)

            if not self.is_numeric_input:
                placement_origin = self.placement_origin_2d.resized(3)
                draw_point(placement_origin, size=4, alpha=0.5)
                draw_vector(self.mouse_pos.resized(3) - placement_origin, origin=placement_origin, alpha=0.2, fade=True)

            if self.type == 'CUBE':
                dims = draw_label(context, title="Add Cube ", coords=Vector((self.HUD_x, self.HUD_y)), center=False)

                if self.is_quad_sphere:
                    dims2 = draw_label(context, title="Quad Sphere", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=green)

                elif self.is_subd:
                    dims2 = draw_label(context, title="Subdivided", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=green)

                elif self.is_rounded:
                    dims2 = draw_label(context, title="Rounded", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=green)

                elif self.is_plane:
                    dims2 = draw_label(context, title="Plane", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=green)

                else:
                    dims2 = (0, 0)

            elif self.type == 'CYLINDER':
                dims = draw_label(context, title="Add Cylinder ", coords=Vector((self.HUD_x, self.HUD_y)), center=False)

                if self.is_rounded:
                    dims2 = draw_label(context, title="Rounded ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=green)

                elif self.is_plane:
                    dims2 = draw_label(context, title="Circle ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=green)

                else:
                    dims2 = (0, 0)

                if self.is_half:
                    draw_label(context, title="Half", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=red)

            elif self.type == 'ASSET':
                dims = draw_label(context, title="Add Asset ", coords=Vector((self.HUD_x, self.HUD_y)), center=False)

                pretty = get_pretty_assetpath(self.obj)

                pretty_split = pretty.split('•')

                if len(pretty_split) > 1:
                    dims2 = draw_label(context, title='•'.join(pretty_split[:-1]) + '•', coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, alpha=0.5)
                    dims3 = draw_label(context, title=pretty_split[-1], coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, color=yellow)

                else:
                    dims2 = draw_label(context, title=get_pretty_assetpath(self.obj), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=yellow)
                    dims3 = (0, 0)

            if self.boolean and self.obj.type == 'MESH':
                self.offset += 18
                color = red if self.boolean_method == 'DIFFERENCE' else blue if self.boolean_method == 'UNION' else normal if self.boolean_method == 'INTERSECT' else green
                draw_label(context, title=f"{self.boolean_solver.title()} Boolean {self.boolean_method.title()}", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, color=color, center=False)

                if self.boolean_parent:
                    self.offset += 12
                     
                    dims = draw_label(context, title=f"with ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, size=10, alpha=0.5)
                    dims2 = draw_label(context, title=self.boolean_parent.name, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, size=10, center=False)

                    if not self.can_boolean:
                        dims3 = draw_label(context, title=f" ⚠", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, size=20, color=yellow, center=False)
                        draw_label(context, title=f" Out of Range!", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, size=10, color=yellow, center=False)

            if self.is_surface and self.obj.type != 'EMPTY':
                self.offset += 18

                dims = draw_label(context, title="on Surface ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow)
                dims2 = (0, 0)

            elif self.is_embed and self.obj.type != 'EMPTY':
                self.offset += 18

                dims = draw_label(context, title=f"Embedded: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)
                dims2 = draw_label(context, title=f"{round(self.embed_depth, 1)} ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False)

            elif (self.type in ['CYLINDER', 'ASSET'] or (self.type == 'CUBE' and self.is_plane)) and self.align_axis in ['X', 'Y']:
                self.offset += 18
                dims = dims2 = (0, 0)

            if (self.type in ['CYLINDER', 'ASSET'] or (self.type == 'CUBE' and self.is_plane)) and self.align_axis in ['X', 'Y']:
                draw_label(context, title=f"Cursor {self.align_axis} Aligned", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=red if self.align_axis == 'X' else green)

            self.offset += 18

            dims = draw_label(context, title="Size:", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, alpha=0.5)

            title = "🖩" if self.is_numeric_input else " "
            dims2 = draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset + 3, center=False, size=20, color=green, alpha=0.5)

            if self.is_numeric_input:
                dims3 = draw_label(context, title=self.numeric_input_size, coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=green, alpha=1)

                if self.is_numeric_input_marked:
                    scale = get_scale(context)
                    coords = [Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y - (self.offset - 5) * scale, 0)), Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y - (self.offset - 5) * scale, 0))]
                    draw_line(coords, width=12 + 8 * scale, color=green, alpha=0.1, screen=True)

            else:
                size = f"{dynamic_format(self.size, decimal_offset=1 if self.is_snapping and self.is_incremental else 0 if self.is_snapping else 2)}"
                dims3 = draw_label(context, title=size, coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False)

                if self.is_snapping:
                    draw_label(context, title=f" {'Dynamic Incemental' if self.is_incremental else 'Dynamic'} Snapping", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, color=yellow)

            if self.type == 'CYLINDER':
                self.offset += 18

                dims = draw_label(context, title="Sides: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, alpha=0.5)

                if self.use_side_presets:

                    if self.prev_sides < self.sides:
                        dims2 = draw_label(context, title=f"{self.prev_sides} ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.3)
                    else:
                        dims2 = (0, 0)

                    dims3 = draw_label(context, title=f"{self.sides} ", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

                    if self.next_sides > self.sides:
                        dims4 = draw_label(context, title=f"{self.next_sides}", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.3)
                    else:
                        dims4 = (0, 0)

                    draw_label(context, title=' Presets', coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + dims4[0], self.HUD_y)), offset=self.offset, center=False, size=12, color=normal, alpha=1)

                else:
                    draw_label(context, title=str(self.sides), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=12)

            elif self.type == 'ASSET' and self.HUD_angle:
                self.offset += 18

                dims = draw_label(context, title="Rotate: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, alpha=0.5)
                draw_label(context, title=str(self.HUD_angle), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False)

            if self.is_rounded:
                self.offset += 18
                draw_label(context, title=f"{'Chamfer' if self.bevel_segments == 0 else 'Bevel'} Mods: {self.bevel_count} | Segments: {self.bevel_segments}", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, color=blue, center=False)

            if self.is_subd:
                self.offset += 18
                draw_label(context, title=f"Subdivisions: {self.subdivisions}", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, color=blue, center=False)

            if self.is_scale_appliable and self.apply_scale:
                self.offset += 18
                draw_label(context, title="Apply Scale", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=red)

            if self.type == 'ASSET' and self.has_subset_mirror:
                self.offset += 18

                color, alpha = (green, 1) if self.is_subset_mirror else (white, 0.25)
                dims = draw_label(context, title="Subset Mirror", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=color, alpha=alpha)

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

        if self.type == 'CUBE':
            row = column.row(align=True)

            row.prop(self, 'is_plane', text='Plane', toggle=True)
            row.prop(self, 'is_rounded', text='Rounded', toggle=True)
            row.prop(self, 'is_subd', text='Subdivided', toggle=True)
            row.prop(self, 'is_quad_sphere', text='Quad Sphere', toggle=True)

        elif self.type == 'CYLINDER':
            row = column.row(align=True)

            row.prop(self, 'is_plane', text='Circle', toggle=True)
            row.prop(self, 'is_rounded', text='Rounded', toggle=True)
            row.prop(self, 'is_half', text='Half', toggle=True)

        row = column.row(align=True)
        row.prop(self, 'size', text='Size')

        if self.type == 'CUBE':
            if self.is_subd:
                row.prop(self, 'subdivisions', text='Subdivisions')

            elif self.is_rounded:
                row.prop(self, 'bevel_count', text='Mods')
                row.prop(self, 'bevel_segments', text='Segments')

        elif self.type == 'CYLINDER':
            row.prop(self, 'sides', text='Sides')

            if self.is_rounded:
                row.prop(self, 'bevel_count', text='Mods')
                row.prop(self, 'bevel_segments', text='Segments')

        elif self.type == 'ASSET':
            row.prop(self, 'rotation_offset', text='Rotation')

        if not self.obj.type == 'EMPTY':

            if not (self.type in ['CUBE', 'CYLINDER'] and (self.is_plane and self.align_axis == 'Z')):

                column.separator()
                row = column.row(align=True)

                row.prop(self, 'is_surface', text='on Surface', toggle=True)
                row.prop(self, 'is_embed', text='Embedded', toggle=True)

                r = row.row(align=True)
                r.active = self.is_embed
                r.prop(self, 'embed_depth', text='Depth')

        if self.type in ['CYLINDER', 'ASSET'] or (self.type in 'CUBE' and self.is_plane):
            if self.is_plane and self.align_axis == 'Z':
                column.separator()

            row = column.row(align=True)

            row.prop(self, 'align_axis', text='Align with Cursor Axis', expand=True)

        if self.boolean_parent and self.obj.type == 'MESH':
            column.separator()

            row = column.row(align=True)
            
            split = row.split(factor=0.49, align=True)
            split.prop(self, 'boolean', text='Setup Boolean', toggle=True)

            r = split.row(align=True)
            r.active = self.boolean
            r.prop(self, 'boolean_solver', text='Solver', expand=True)

            row = column.row(align=True)
            row.active = self.boolean
            row.prop(self, 'boolean_method', text='Method', expand=True)

            row = column.row(align=True)
            row.active = self.boolean
            row.prop(self, 'hide_boolean', text='Hide Boolean Objects', toggle=True)

        if self.is_scale_appliable:
            column.separator()

            column.prop(self, 'apply_scale', text='Apply Scale', toggle=True)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        if ret := self.numeric_input(context, event):
            return ret

        else:
            return self.interactive_input(context, event)

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

        restore_gizmos(self)
        
        if self.toggled_use_enter_edit_mode:
            context.preferences.edit.use_enter_edit_mode = True
        
        self.is_interactive = False

        force_ui_update(context)

    def invoke(self, context, event):
        if self.type == 'CYLINDER' and event.shift:
            bpy.ops.machin3.add_pipe('INVOKE_DEFAULT')
            return {'FINISHED'}

        self.obj = None
        self.rotation_offset = 0
        self.HUD_angle = 0

        self.is_interactive = True

        self.get_placement_matrix(context, debug=False)

        if not self.placement_origin_2d:
            draw_fading_label(context, text="Make sure the Cursor is positioned and visible on the screen!", y=120, color=(1, 0.3, 0), alpha=1, move_y=20, time=2)
            return {'CANCELLED'}

        self.init_use_enter_edit_mode(context)

        self.prepare_for_boolean(context)

        if (event.ctrl and not self.is_drop) or event.alt:

            if self.type == 'ASSET':
                self.obj = self.create_asset_object(context)

                if not self.obj:
                    draw_fading_label(context, text="Asset could not be added to scene!", y=120, color=red, alpha=1, move_y=40, time=4)

                    return {'CANCELLED'}

            self.prepare_for_subset_mirror(context)

            if event.ctrl:
                self.size = 1
                self.sides = 32
                self.rotation_offset = 0

                self.is_surface = True
                self.is_embed = False

                self.is_quad_sphere = False
                self.is_plane = False
                self.is_subd = False
                self.is_rounded = False

                self.boolean = False
                self.apply_scale = True

            elif event.alt:
                self.init_props(context, redo=True)

            if self.type == 'CUBE':
                self.obj = self.create_cube_object(context)

            elif self.type == 'CYLINDER':
                self.obj = self.create_cylinder_object(context)

            self.get_dimensions()

            self.transform_object(context, interactive=False)

            if self.type == 'ASSET':
                self.compensate_bevels(context, debug=False)

            elif self.type == 'CUBE' and (self.is_quad_sphere or self.is_subd):
                self.setup_quad_sphere_or_subdivided_cube()

                self.apply_mods()

            if self.type == 'CUBE':
                self.finish_cube()

            elif self.type == 'CYLINDER':
                self.finish_cylinder()

            if self.can_scale_be_applied(context):
                self.apply_obj_scale(context)

            if self.boolean and self.boolean_parent:

                self.setup_boolean(interactive=False)
                
                self.verify_boolean_is_in_range()

                self.finish_boolean(context)

                if self.hide_boolean:
                    self.hide_cutter(context)

            self.subset_mirror()

            self.finalize_selection(context)

            if self.type in ['CUBE', 'CYLINDER'] and self.toggled_use_enter_edit_mode and not self.hide_boolean:
                bpy.ops.object.mode_set(mode='EDIT')

            if self.toggled_use_enter_edit_mode:
                context.preferences.edit.use_enter_edit_mode = True

            return {'FINISHED'}

        if self.type == 'CYLINDER':
            self.use_side_presets = True

        self.snap_reset_size = None
        self.is_snapping = False
        self.is_incremental = False

        self.is_numeric_input = False
        self.is_numeric_input_mared = False
        self.numeric_input_size = '0'

        if self.type == 'ASSET':
            self.obj = self.create_asset_object(context)

            if not self.obj:
                text= ["Make sure to select an OBJECT asset in the asset browser!",
                       "It can be a collection instance asset, but not a collection."]

                draw_fading_label(context, text=text, y=120, color=[red, white], alpha=[1, 0.5], move_y=40, time=4)
                return {'CANCELLED'}

        self.prepare_for_subset_mirror(context)

        get_mouse_pos(self, context, event)

        if not self.is_drop:
            warp_mouse(self, context, self.placement_origin_2d)

        self.init_props(context, redo=False)

        if self.type == 'CYLINDER':

            self.prev_sides, self.next_sides = self.get_prev_and_next_sides(self.sides, debug=False)

        if self.type == 'CUBE':
            self.obj = self.create_cube_object(context)

        elif self.type == 'CYLINDER':
            self.obj = self.create_cylinder_object(context)

        self.get_dimensions()

        self.transform_object(context)

        if self.type == 'ASSET':
            self.compensate_bevels(context, debug=False)

        if self.type == 'CUBE' and (self.is_quad_sphere or self.is_subd):
            self.setup_quad_sphere_or_subdivided_cube()

        self.is_scale_appliable = self.can_scale_be_applied(context)

        if self.boolean and self.boolean_parent:
            self.setup_boolean(interactive=True)

        hide_gizmos(self, context)

        init_status(self, context, func=draw_add_status(self))

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.is_interactive = False
        self.obj = None

        self.init_use_enter_edit_mode(context)

        self.prepare_for_boolean(context)

        if self.type == 'ASSET':
            asset = context.active_object

            if asset:

                if asset.type == 'EMPTY' and asset.instance_type == 'COLLECTION' and asset.HC.autodisband:

                    self.disband_collection_instance_assset(context, asset)

                    self.obj = context.active_object

                else:
                    self.obj = asset

        else:
            if self.type == 'CUBE':
                self.obj = self.create_cube_object(context)

            elif self.type == 'CYLINDER':
                self.obj = self.create_cylinder_object(context)
        
        if not self.obj:
            if self.toggled_use_enter_edit_mode:
                context.preferences.edit.use_enter_edit_mode = True
            return {'CANCELLED'}

        self.get_dimensions()

        self.transform_object(context, interactive=False)

        if self.type == 'ASSET':
            self.compensate_bevels(context, debug=False)

        if self.type == 'CUBE' and (self.is_quad_sphere or self.is_subd):
            self.setup_quad_sphere_or_subdivided_cube()

        if self.type == 'CUBE':
            if self.is_quad_sphere or self.is_subd:
                self.apply_mods()

            self.finish_cube()

        elif self.type == 'CYLINDER':
            self.finish_cylinder()

        if self.can_scale_be_applied(context):
            self.apply_obj_scale(context)

        if self.boolean and self.boolean_parent:
            self.setup_boolean(interactive=True)

            self.finish_boolean(context)

        self.store_props(context)

        if self.hide_boolean:
            self.hide_cutter(context)

        if self.type in ['CUBE', 'CYLINDER']:
            if self.toggled_use_enter_edit_mode:
                bpy.ops.object.mode_set(mode='EDIT')

        elif self.type == 'ASSET':
            self.finalize_selection(context)

        if self.toggled_use_enter_edit_mode:
            context.preferences.edit.use_enter_edit_mode = True

        return {'FINISHED'}

    def get_placement_matrix(self, context, debug=False):
        if self.is_drop:
            if debug:
                print("drop matrix")

            active = context.active_object

            pmx = active.matrix_world.copy()
            loc, rot, _ = pmx.decompose()

            if len(context.selected_objects) == 1 and active.type == 'MESH':
                if debug:
                    print(" single mesh object, offseting placement origin to bottom")

                centers = get_bbox(active.data)[1]
                loc = pmx @ centers[-2]

        else:
            if debug:
                print("cursor matrix")

            pmx = context.scene.cursor.matrix
            loc, rot, _ = pmx.decompose()

        self.pmx = pmx
        self.placement_origin = loc
        self.placement_up = rot @ Vector((0, 0, 1))
        self.placement_view_plane = None
        self.placement_origin_2d = None

        loc2d = get_location_2d(context, loc, default='OFF_SCREEN')
        if is_on_screen(context, loc2d):
            self.placement_origin_2d = loc2d

    def init_use_enter_edit_mode(self, context):
        self.toggled_use_enter_edit_mode = False

        if self.type in ['CUBE', 'CYLINDER'] and context.preferences.edit.use_enter_edit_mode:
            context.preferences.edit.use_enter_edit_mode = False
            self.toggled_use_enter_edit_mode = True

    def prepare_for_boolean(self, context):
        self.boolean_parent = None
        self.boolean_mod = None
        self.secondary_booleans = []

        self.boolean_parent_location = None
        self.can_boolean = False

        if context.visible_objects:
            dg = context.evaluated_depsgraph_get()

            if self.is_drop:
                targets = [obj for obj in context.visible_objects if obj.type == 'MESH' and obj != context.active_object]

            else:
                targets = [obj for obj in context.visible_objects if obj.type == 'MESH']

            self.boolean_parent, _, self.boolean_parent_location, _, _, _ = get_closest(dg, targets=targets, origin=self.placement_origin, debug=False)

    def verify_boolean_is_in_range(self):
        if self.boolean and self.boolean_parent and self.boolean_mod:
            distance = (self.placement_origin - self.boolean_parent_location).length

            self.can_boolean = distance * 1.5 < self.size

            for mod in [self.boolean_mod] + self.secondary_booleans:
                if self.can_boolean and not mod.show_viewport:
                    mod.show_viewport = True

                elif not self.can_boolean and mod.show_viewport:
                    mod.show_viewport = False

    def prepare_for_subset_mirror(self, context):
        self.has_subset_mirror = False
        self.is_subset_mirror = False

        if self.type == 'ASSET' and self.boolean_parent:

            self.mirror_mods = mirror_poll(context, obj=self.boolean_parent)

            self.hook_objs = [mod.object for mod in hook_poll(context, obj=self.obj)]

            self.subset_objs= [obj for obj in self.obj.children_recursive if not is_wire_object(obj) and obj not in self.hook_objs]

            self.has_subset_mirror = bool(self.mirror_mods and self.subset_objs)

    def init_props(self, context, redo=False):
        redoCOL = context.scene.HC.redoaddobjCOL

        name = self.type if self.type in ['CUBE', 'CYLINDER'] else self.obj.HC.assetpath

        if name in redoCOL:
            self.is_in_history = True

            entry = redoCOL[name]

            self.size = entry.size

            self.align_axis = entry.align_axis

            self.sides = entry.sides

            self.is_surface = entry.surface
            self.is_embed = entry.embed
            self.embed_depth = entry.embed_depth

            self.apply_scale = entry.apply_scale

            self.is_quad_sphere = entry.is_quad_sphere
            self.is_plane = entry.is_plane
            self.is_subd = entry.is_subd
            self.subdivisions = entry.subdivisions

            self.is_rounded = entry.is_rounded
            self.bevel_count = entry.bevel_count
            self.bevel_segments = entry.bevel_segments

            self.boolean = entry.boolean
            self.boolean_method = entry.boolean_method
            self.boolean_solver = entry.boolean_solver
            self.hide_boolean = entry.hide_boolean

            self.boolean_display_type = entry.display_type

            self.is_subset_mirror = entry.is_subset_mirror

        else:
            self.is_in_history = False

            self.align_axis = 'Z'

            self.boolean = False
            self.boolean_method = 'DIFFERENCE'
            self.boolean_solver = 'FAST'
            self.hide_boolean = False

            self.is_quad_sphere = False
            self.is_plane = False
            self.is_subd = False
            self.is_rounded = False
            self.bevel_count = 1

            if self.obj:
                self.boolean_display_type = 'WIRE' if context.active_object.display_type not in ['WIRE', 'BOUNDS'] else context.active_object.display_type

                if self.obj.HC.isinset:
                    self.is_surface = False
                    self.is_embed = False

                    self.boolean = True
                    self.boolean_method = self.obj.HC.insettype
                    self.boolean_solver = self.obj.HC.insetsolver

            self.apply_scale = True if self.type in ['CUBE', 'CYLINDER'] else False

            self.is_subset_mirror = self.has_subset_mirror

        self.boolean_mod = None

        if not redo:
            self.size = 0

            if self.type in ['CUBE', 'CYLINDER']:
                self.boolean = False

    def get_prev_and_next_sides(self, sides, debug=False):
        side_presets = [int(p[0]) for p in add_cylinder_side_items]

        if self.sides in side_presets:
            index = side_presets.index(sides)

            prev_index = max(0, index - 1)
            next_index = min(len(side_presets) - 1, index + 1)

            prev_sides = side_presets[prev_index]
            next_sides = side_presets[next_index]

            if debug:
                print(sides, "is in presets at index", index)
                print("prev:", prev_sides)
                print("next:", next_sides)
        
        else:
            prev_sides = side_presets[0]
            next_sides = side_presets[-1]

            for p in side_presets:
                if p < sides:
                    prev_sides = p

                elif p > sides:
                    next_sides = p
                    break

            if debug:
                print(sides, "is NOT in pesets")
                print("prev:", prev_sides)
                print("next:", next_sides)

        return prev_sides, next_sides

    def get_placement_view_plane(self, view_dir):
        placement_x = self.pmx.col[0].xyz
        placement_y = self.pmx.col[1].xyz
        placement_z = self.placement_up

        self.placement_view_plane = max([(c, abs(view_dir.dot(c))) for c in [placement_x, placement_y, placement_z]], key=lambda x: x[1])[0]

    def get_dimensions(self):
        if self.type == 'ASSET':

            if self.obj.type == 'MESH':
                _, centers, dimensions = get_bbox(self.obj.data)
            
            else: 
                _, centers, dimensions = get_eval_bbox(self.obj, advanced=True)

            if max(dimensions):
                self.mesh_dimensions = dimensions
                self.mesh_max_dimension_factor = 1 / max(dimensions)
                self.mesh_surface_offsets = [-centers[0].x, -centers[2].y, -centers[4].z]

                self.scaledivisor = max(self.obj.scale)
                self.scale_ratios = Vector([s / self.scaledivisor for s in self.obj.scale])

                return

        self.mesh_dimensions = Vector([2, 2, 2])
        self.mesh_max_dimension_factor = 0.5  # 1 / 2
        self.mesh_surface_offsets = [1, 1, 1]

        self.scale_divisor = 1
        self.scale_ratios = Vector((1, 1, 1))

    def create_asset_object(self, context):
        if self.type == 'ASSET':

            if self.is_drop:
                asset = context.active_object

            else:

                bpy.ops.object.select_all(action='DESELECT')
                context.view_layer.objects.active = None

                area = get_assetbrowser_area(context)

                if area:

                    with context.temp_override(area=area):
                        bpy.ops.machin3.fetch_asset()

                    asset = context.active_object

                    if asset:
                        loc, rot, _ = self.pmx.decompose()
                        _, _, sca = asset.matrix_world.decompose()

                        asset.matrix_world = Matrix.LocRotScale(loc, rot, sca)

                        bpy.ops.ed.undo_push(message="MACHIN3: Fetch Asset")

                    else:
                        return

            if asset.type == 'EMPTY' and asset.instance_type == 'COLLECTION' and asset.HC.autodisband:
                self.disband_collection_instance_assset(context, asset)

            elif asset.type == 'MESH':

                if bpy.app.version >= (4, 1, 0):
                    mod = get_auto_smooth(asset)

                    if mod and is_invalid_auto_smooth(mod):
                        remove_mod(mod)

            return context.active_object

    def disband_collection_instance_assset(self, context, asset):
        acol = asset.instance_collection
        mcol = context.scene.collection

        children = [obj for obj in acol.objects]

        bpy.ops.object.select_all(action='DESELECT')

        for obj in children:
            mcol.objects.link(obj)
            obj.select_set(True)

            if bpy.app.version >= (4, 1, 0):
                mod = get_auto_smooth(obj)

                if mod and is_invalid_auto_smooth(mod):
                    remove_mod(mod)

        if len(acol.users_dupli_group) > 1:
            bpy.ops.object.duplicate()

            for obj in children:
                mcol.objects.unlink(obj)

            children = [obj for obj in context.selected_objects]

            for obj in children:
                if obj.name in acol.objects:
                    acol.objects.unlink(obj)

        root = [obj for obj in children if not obj.parent][0]
        root.matrix_world = asset.matrix_world

        if root.HC.issecondaryboolean:
            self.secondary_booleans = [mod for mod in root.modifiers if mod.type == 'BOOLEAN' and mod.object and mod.show_viewport]

        root.select_set(True)
        context.view_layer.objects.active = root

        root.HC.assetpath = asset.HC.assetpath
        root.HC.libname = asset.HC.libname
        root.HC.blendpath = asset.HC.blendpath
        root.HC.assetname = asset.HC.assetname

        bpy.data.objects.remove(asset, do_unlink=True)

        if len(acol.users_dupli_group) == 0:
            bpy.data.collections.remove(acol, do_unlink=True)

    def create_cube_object(self, context):
        if self.obj:
            bpy.data.meshes.remove(self.obj.data, do_unlink=True)

        bpy.ops.mesh.primitive_cube_add(align='CURSOR')

        obj = context.active_object

        enable_auto_smooth(obj)

        if self.is_quad_sphere:
            obj.name = 'Quad Sphere'

        elif self.is_rounded:
            obj.name = 'Rounded Cube'

            if self.bevel_count in [1, 4]:
                if self.bevel_count == 1:

                    vertids = [0, 1, 2, 3, 4, 5, 6, 7]

                    vgroup = add_vgroup(obj, 'Edge Bevel', ids=vertids, weight=1)

                    mod = add_bevel(obj, name="Edge Bevel", width=0.2, limit_method='VGROUP', vertex_group=vgroup.name)
                    mod.segments = self.bevel_segments + 1

                elif self.bevel_count == 4:

                    vertids = [0, 1, 6, 7]
                    vgroup = add_vgroup(obj, 'Edge Bevel', ids=vertids, weight=1)

                    mod = add_bevel(obj, name="Edge Bevel", width=0.21, limit_method='VGROUP', vertex_group=vgroup.name)
                    mod.segments = self.bevel_segments + 1

                    vertids = [2, 3, 4, 5]
                    vgroup = add_vgroup(obj, 'Edge Bevel.001', ids=vertids, weight=1)

                    mod = add_bevel(obj, name="Edge Bevel.001", width=0.21, limit_method='VGROUP', vertex_group=vgroup.name)
                    mod.segments = self.bevel_segments + 1

                    vertids = [1, 5, 7, 3]
                    vgroup = add_vgroup(obj, 'Edge Bevel.002', ids=vertids, weight=1)

                    mod = add_bevel(obj, name="Edge Bevel.002", width=0.2, limit_method='VGROUP', vertex_group=vgroup.name)
                    mod.segments = self.bevel_segments + 1

                    vertids = [0, 4, 6, 2]
                    vgroup = add_vgroup(obj, 'Edge Bevel.003', ids=vertids, weight=1)

                    mod4 = add_bevel(obj, name="Edge Bevel.003", width=0.2, limit_method='VGROUP', vertex_group=vgroup.name)
                    mod4.segments = self.bevel_segments + 1

            elif self.bevel_count in [2, 3]:
                bm = bmesh.new()
                bm.from_mesh(obj.data)

                bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges], cuts=1, use_grid_fill=True)

                bm.to_mesh(obj.data)
                bm.free()

                if self.bevel_count == 2:

                    vertids = [0, 9, 1, 4, 17, 5, 6, 14, 7, 2, 11, 3]
                    vgroup = add_vgroup(obj, 'Edge Bevel', ids=vertids, weight=1)

                    mod = add_bevel(obj, name="Edge Bevel", width=0.21, limit_method='VGROUP', vertex_group=vgroup.name)
                    mod.segments = self.bevel_segments + 1

                    vertids = [1, 19, 5, 16, 7, 13, 3, 10, 0, 18, 4, 15, 6, 12, 2, 8]
                    vgroup = add_vgroup(obj, 'Edge Bevel.001', ids=vertids, weight=1)

                    mod2 = add_bevel(obj, name="Edge Bevel.001", width=0.2, limit_method='VGROUP', vertex_group=vgroup.name)
                    mod2.segments = self.bevel_segments + 1

                elif self.bevel_count == 3:

                    vertids = [0, 9, 1, 4, 17, 5, 6, 14, 7, 2, 11, 3]
                    vgroup = add_vgroup(obj, 'Edge Bevel', ids=vertids, weight=1)

                    mod = add_bevel(obj, name="Edge Bevel", width=0.21, limit_method='VGROUP', vertex_group=vgroup.name)
                    mod.segments = self.bevel_segments + 1

                    vertids = [1, 19, 5, 16, 7, 13, 3, 10]
                    vgroup = add_vgroup(obj, 'Edge Bevel.001', ids=vertids, weight=1)

                    mod = add_bevel(obj, name="Edge Bevel.001", width=0.2, limit_method='VGROUP', vertex_group=vgroup.name)
                    mod.segments = self.bevel_segments + 1

                    vertids = [0, 18, 4, 15, 6, 12, 2, 8]
                    vgroup = add_vgroup(obj, 'Edge Bevel.002', ids=vertids, weight=1)

                    mod = add_bevel(obj, name="Edge Bevel.002", width=0.2, limit_method='VGROUP', vertex_group=vgroup.name)
                    mod.segments = self.bevel_segments + 1

        elif self.is_plane:
            obj.name = "Plane"

            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.normal_update()
            bm.faces.ensure_lookup_table()

            delete = []

            for f in bm.faces:
                if f.index == 5:
                    for v in f.verts:
                        v.co.z = 0
                else:
                    delete.append(f)

            bmesh.ops.delete(bm, geom=delete, context='FACES')

            bm.to_mesh(obj.data)
            bm.free()

        if self.boolean and self.boolean_mod:
            self.boolean_mod.object = obj
            context.active_object.display_type = self.boolean_display_type

        return obj

    def create_cylinder_object(self, context):
        if self.obj:
            bpy.data.meshes.remove(self.obj.data, do_unlink=True)

        bpy.ops.mesh.primitive_cylinder_add(vertices=self.sides, align='CURSOR')

        obj = context.active_object

        enable_auto_smooth(obj)

        if self.is_rounded:
            obj.name = 'Rounded Cylinder'

            bm = bmesh.new()
            bm.from_mesh(obj.data)

            caps = [f for f in bm.faces if len(f.verts) != 4]

            for f in caps:
                vertids = [v.index for v in f.verts]

                vgroup = add_vgroup(obj, 'Edge Bevel', ids=vertids, weight=1)

                if self.is_half:

                    if self.sides == 18:
                        width = 0.1
                    elif self.sides == 9:
                        width = 0.12
                    else:
                        width = min(3 / self.sides, 0.2)
                else:
                    width = 0.2

                mod = add_bevel(obj, name="Edge Bevel", width=width, limit_method='VGROUP', vertex_group=vgroup.name)
                mod.segments = self.bevel_segments + 1

        elif self.is_plane:
            obj.name = 'Circle'

            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.normal_update()

            delete = []

            top = Vector((0, 0, 1))

            for f in bm.faces:
                dot = round(top.dot(f.normal))

                if dot == 1:
                    for v in f.verts:
                        v.co.z = 0

                else:
                    delete.append(f)

            bmesh.ops.delete(bm, geom=delete, context='FACES')

            bm.to_mesh(obj.data)
            bm.free()

        if self.is_half:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.normal_update()
            bm.verts.ensure_lookup_table()

            geom = [el for seq in [bm.verts, bm.edges, bm.faces] for el in seq]

            bmesh.ops.bisect_plane(bm, geom=geom, dist=0, plane_co=Vector((0, 0, 0)), plane_no=Vector((0, -1, 0)), use_snap_center=False, clear_outer=True, clear_inner=False)

            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00001)

            if not self.is_plane:
                bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if not e.is_manifold], sides=0)

            bm.to_mesh(obj.data)
            bm.free()

        if self.boolean_mod:
            self.boolean_mod.object = obj
            obj.display_type = self.boolean_display_type

        return obj

    def compensate_bevels(self, context, debug=False):
        if debug:
            print()
            print("mesh users:", self.obj.data.users)

        bevel_mods = bevel_poll(context, self.obj)

        if bevel_mods and self.obj.data.users > 1:
            if debug:
                print("fetching original mesh max dimensions factor")

            redoCOL = context.scene.HC.redoaddobjCOL
            entry = redoCOL.get(self.obj.HC.assetpath)

            if entry and entry.original_mesh_max_dimension_factor:
                if debug:
                    print(" original:", entry.original_mesh_max_dimension_factor)

                    print("  current:", self.mesh_max_dimension_factor)

                if entry.original_mesh_max_dimension_factor != str(self.mesh_max_dimension_factor):
                    if debug:
                        print(" it differs, so the current bevels need to be adjusted!")

                    compensate = float(self.mesh_max_dimension_factor) / float(entry.original_mesh_max_dimension_factor)

                    for mod in bevel_mods:
                        mod.width /= compensate

    def setup_quad_sphere_or_subdivided_cube(self):
        subd = add_subdivision(self.obj, name="Subdivision")
        subd.levels = self.subdivisions
        subd.render_levels = self.subdivisions

        if self.is_quad_sphere:
            add_cast(self.obj, name="Cast")

        else:
            subd.subdivision_type = 'SIMPLE'

    def setup_boolean(self, interactive=True):
        method = 'DIFFERENCE' if self.boolean_method == 'SPLIT' else self.boolean_method
        self.boolean_mod = add_boolean(self.boolean_parent, self.obj, method=method, solver=self.boolean_solver)

        if self.boolean_display_type not in ['WIRE', 'BOUNDS']:
            self.boolean_display_type = 'WIRE'

        self.obj.display_type = self.boolean_display_type

        if interactive:
            if self.boolean_method == 'SPLIT':
                self.boolean_mod.show_viewport = False

        if self.type == 'ASSET' and self.secondary_booleans:
            new_mods = []

            for mod in self.secondary_booleans:

                mod.show_viewport = False

                new_mod = add_boolean(self.boolean_parent, mod.object, method=mod.operation, solver=mod.solver)
                new_mod.object.display_type = self.boolean_display_type
                new_mods.append(new_mod)

                remove_mod(mod)

            self.secondary_booleans = new_mods

    def transform_object(self, context, interactive=True):
        self.set_obj_size(context, interactive=interactive)

        self.set_obj_location(context)

        if self.type in ['CYLINDER', 'ASSET'] or (self.type == 'CUBE' and self.is_plane):
            self.set_obj_axis_align(context)

        self.verify_boolean_is_in_range()

    def set_obj_size(self, context, interactive=False):
        if interactive:
            view_origin, view_dir = get_view_origin_and_dir(context, self.mouse_pos)

            if not self.placement_view_plane:
                self.get_placement_view_plane(view_dir)

            i = intersect_line_plane(view_origin, view_origin + view_dir, self.placement_origin, self.placement_view_plane)

            if i:
                self.size = (self.placement_origin - i).length

                if self.is_snapping:
                    self.size = dynamic_snap(self.size, offset=1 if self.is_incremental else 0)

        self.obj.scale = Vector((self.size, self.size, self.size)) * self.mesh_max_dimension_factor * self.scale_ratios

    def set_obj_location(self, context):
        if self.type in ['CYLINDER', 'ASSET']:
            if self.align_axis == 'X':
                surface_offset = self.mesh_surface_offsets[1]
                mesh_dimension = self.mesh_dimensions[1]
                scale_ratio = self.scale_ratios[1]
            elif self.align_axis == 'Y':
                surface_offset = self.mesh_surface_offsets[0]
                mesh_dimension = self.mesh_dimensions[0]
                scale_ratio = self.scale_ratios[0]
            elif self.align_axis == 'Z':
                surface_offset = self.mesh_surface_offsets[2]
                mesh_dimension = self.mesh_dimensions[2]
                scale_ratio = self.scale_ratios[2]

        else:
            surface_offset = self.mesh_surface_offsets[2]
            mesh_dimension = self.mesh_dimensions[2]
            scale_ratio = 1

        mesh_size = self.size * self.mesh_max_dimension_factor

        if self.is_surface and self.obj.type != 'EMPTY':
            context.active_object.location = self.placement_origin + self.placement_up * mesh_size * surface_offset * scale_ratio

        elif self.is_embed and self.obj.type != 'EMPTY':
            context.active_object.location = self.placement_origin + self.placement_up * mesh_size * (surface_offset - mesh_dimension * self.embed_depth) * scale_ratio

        else:
            context.active_object.location = self.placement_origin

    def set_obj_axis_align(self, context):
        loc, _, sca = context.active_object.matrix_basis.decompose()

        rot_offset = Quaternion(Vector((0, 0, 1)), radians(self.rotation_offset)).to_matrix()

        self.HUD_angle = 360 - self.rotation_offset

        if self.HUD_angle == 360:
            self.HUD_angle = 0

        protmx = self.pmx.to_3x3() @ rot_offset

        if self.align_axis == 'X':
            rotmx = protmx.copy()

            rotmx.col[2] = protmx.col[0]
            rotmx.col[1] = protmx.col[2]
            rotmx.col[0] = protmx.col[1]

        elif self.align_axis == 'Y':
            rotmx = protmx.copy()

            rotmx.col[2] = protmx.col[1]
            rotmx.col[1] = protmx.col[0]
            rotmx.col[0] = protmx.col[2]

            z_rot = Quaternion(Vector((0, 0, 1)), radians(-90)).to_matrix()
            rotmx = rotmx @ z_rot

        else:
            rotmx = protmx

        context.active_object.matrix_basis = Matrix.LocRotScale(loc, rotmx, sca)

    def numeric_input(self, context, event):
        
        if event.type == "TAB" and event.value == 'PRESS':
            self.is_numeric_input = not self.is_numeric_input

            force_ui_update(context)

            if self.is_numeric_input:
                self.numeric_input_size = str(self.size)
                self.is_numeric_input_marked = True

            else:
                return

        if self.is_numeric_input:
            events = [*numbers, 'BACK_SPACE', 'DELETE', 'PERIOD', 'COMMA', 'MINUS', 'NUMPAD_PERIOD', 'NUMPAD_COMMA', 'NUMPAD_MINUS']

            if event.type in events and event.value == 'PRESS':

                if self.is_numeric_input_marked:
                    self.is_numeric_input_marked = False

                    if event.type == 'BACK_SPACE' and event.alt:
                        self.numeric_input_size = self.numeric_input_size[:-1]

                    else:
                        self.numeric_input_size = input_mappings[event.type]

                else:
                    if event.type in numbers:
                        self.numeric_input_size += input_mappings[event.type]

                    elif event.type == 'BACK_SPACE':
                        self.numeric_input_size = self.numeric_input_size[:-1]

                    elif event.type in ['COMMA', 'PERIOD', 'NUMPAD_COMMA', 'NUMPAD_PERIOD'] and '.' not in self.numeric_input_size:
                        self.numeric_input_size += '.'

                    elif event.type in ['MINUS', 'NUMPAD_MINUS']:
                        if self.numeric_input_size.startswith('-'):
                            self.numeric_input_size = self.numeric_input_size[1:]

                        else:
                            self.numeric_input_size = '-' + self.numeric_input_size

                try:
                    self.size = float(self.numeric_input_size)

                except:
                    return {'RUNNING_MODAL'}

                self.transform_object(context, interactive=False)

            elif navigation_passthrough(event, alt=True, wheel=True):
                return {'PASS_THROUGH'}

            elif event.type in {'RET', 'NUMPAD_ENTER', 'SPACE'}:
                self.finish(context)

                self.hide_boolean = self.obj.type == 'MESH' and self.boolean and event.type == 'SPACE'

                if self.type == 'CUBE':
                    if self.is_quad_sphere or self.is_subd:
                        self.apply_mods()

                    self.finish_cube()

                elif self.type == 'CYLINDER':
                    self.finish_cylinder()

                if self.can_scale_be_applied:
                    self.apply_obj_scale(context)

                self.finish_boolean(context)

                self.store_props(context)

                if self.hide_boolean:
                    self.hide_cutter(context)

                self.subset_mirror()

                self.finalize_selection(context)

                if self.type in ['CUBE', 'CYLINDER'] and self.toggled_use_enter_edit_mode and not seflf.hide_boolean:
                    bpy.ops.object.mode_set(mode='EDIT')

                return {'FINISHED'}

            elif event.type in {'ESC', 'RIGHTMOUSE'}:
                self.finish(context)

                for obj in context.selected_objects:
                    if obj.type == 'MESH' and obj.data.users == 1:
                        bpy.data.meshes.remove(obj.data, do_unlink=True)
                    else:
                        bpy.data.objects.remove(obj, do_unlink=True)

                if self.boolean_mod:
                    self.boolean_parent.modifiers.remove(self.boolean_mod)

                for mod in self.secondary_booleans:
                    self.boolean_parent.modifiers.remove(mod)

                return {'CANCELLED'}

            return {'RUNNING_MODAL'}

    def interactive_input(self, context, event):
        if event.type == 'MOUSEMOVE':
            get_mouse_pos(self, context, event)

        self.is_snapping = event.ctrl
        self.is_incremental = event.alt

        if self.is_snapping and not self.snap_reset_size:
            self.snap_reset_size = self.size

            self.transform_object(context)

        elif not self.is_snapping and self.snap_reset_size is not None:
            self.size = self.snap_reset_size
            self.snap_reset_size = None

            self.transform_object(context)

        events = ['MOUSEMOVE']
        finish_events = ['LEFTMOUSE', 'SPACE', 'L', 'MIDDLEMOUSE'] if self.is_in_history else ['LEFTMOUSE', 'SPACE']

        if not (self.type in ['CUBE', 'CYLINDER'] and self.is_plane):
            events.append('R')
            
            if self.boolean_parent:
                events.append('B')

            if self.type == 'CUBE':
                events.append('Q')

        if not (self.type in ['CUBE', 'CYLINDER'] and self.is_plane and self.align_axis == 'Z'):
            events.extend(['S', 'D'])

        if self.is_scale_appliable:
            events.append('A')

        if self.type in ['CYLINDER', 'ASSET'] or (self.type == 'CUBE' and self.is_plane): 
            events.extend(['X', 'Y', 'Z'])

        if self.boolean:
            events.extend(['E', 'F', 'W'])

        if self.type == 'CUBE':
            events.extend(['C', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE'])

        elif self.type == 'CYLINDER':
            events.extend(['Q', 'C', 'V', 'H'])

        elif self.type == 'ASSET' and self.has_subset_mirror:
            events.append('M')

        if event.type in events or scroll_up(event, key=False) or scroll_down(event, key=False):

            if self.type == 'CYLINDER':

                if event.type in ['X', 'Y', 'Z'] or scroll_up(event, key=False) or scroll_down(event, key=False):

                    if scroll_up(event, key=True) or scroll_down(event, key=True):

                        if not event.shift and not event.alt and not self.boolean:

                            if self.use_side_presets:
                                if scroll_up(event, key=True):
                                    self.sides = self.next_sides
                                else:
                                    self.sides = self.prev_sides

                                self.prev_sides, self.next_sides = self.get_prev_and_next_sides(self.sides)

                            else:
                                if scroll_up(event, key=True):
                                    self.sides += 1
                                else:
                                    self.sides -= 1

                            self.obj = self.create_cylinder_object(context)

                        elif event.alt and self.is_rounded:
                            if scroll_up(event, key=True):
                                self.bevel_segments += 1

                            elif scroll_down(event, key=True):
                                self.bevel_segments -= 1

                            bevel_mods = bevel_poll(context, self.obj)

                            for mod in bevel_mods:
                                mod.segments = self.bevel_segments + 1

                    if event.type == 'X' and event.value == 'PRESS':
                        self.align_axis = 'Z' if self.align_axis == 'X' else 'X'

                    elif event.type in ['Y', 'Z'] and event.value == 'PRESS':
                        self.align_axis = 'Z' if self.align_axis == 'Y' else 'Y'

                    if self.align_axis == 'Z' and self.is_plane:
                        if self.is_surface:
                            self.is_surface = False

                        if self.is_embed:
                            self.is_embed = False

                    self.transform_object(context)

                elif event.type == 'Q' and event.value == 'PRESS':
                    self.use_side_presets = not self.use_side_presets

                    if self.use_side_presets:
                        self.prev_sides, self.next_sides = self.get_prev_and_next_sides(self.sides)

                    force_ui_update(context)

                elif event.type == 'C' and event.value == 'PRESS':
                    if self.is_plane:
                        self.is_plane = False

                    else:
                        self.is_rounded = False

                        if self.align_axis == 'Z':
                            self.is_embed = False
                            self.is_surface = False
        
                        if self.boolean:
                            self.boolean = False
                            remove_mod(self.boolean_mod)
                            self.boolean_mod = None

                        self.is_plane = True

                    self.obj = self.create_cylinder_object(context)

                    self.transform_object(context)

                elif event.type in ['V', 'H'] and event.value == 'PRESS':
                    if self.is_half:
                        self.is_half = False

                    else:
                        self.is_half = True

                    self.obj = self.create_cylinder_object(context)

                    self.transform_object(context)

                elif event.type == 'R' and event.value == 'PRESS':
                    self.is_rounded = not self.is_rounded

                    if self.is_rounded:
                        self.bevel_count = 2

                    self.obj = self.create_cylinder_object(context)

                    self.transform_object(context)

            elif self.type == 'CUBE':
                subd = get_subdivision(self.obj)
                cast = get_cast(self.obj)

                if event.type == 'Q' and event.value == 'PRESS':

                    if subd and cast:
                        self.obj.modifiers.remove(subd)
                        self.obj.modifiers.remove(cast)

                        self.is_subd = False
                        self.is_quad_sphere = False
                        self.obj.show_wire = False

                        self.obj.name = 'Cube'

                    else:
                        self.is_rounded = False

                        self.is_subd = True
                        self.is_quad_sphere = True

                        self.obj = self.create_cube_object(context)
                        self.obj.show_wire = True

                        subd = add_subdivision(self.obj, name="Subdivision")
                        subd.levels = self.subdivisions
                        subd.render_levels = self.subdivisions

                        cast = add_cast(self.obj, name="Cast")

                        self.transform_object(context)

                elif event.type == 'C' and event.value == 'PRESS':
                    if self.is_plane:
                        self.is_plane = False

                        if self.align_axis in ['X', 'Y']:
                            self.align_axis = 'Z'

                    else:

                        if self.is_quad_sphere:
                            self.is_quad_sphere = False
                            self.is_subd = False

                        self.is_rounded = False

                        self.is_embed = False
                        self.is_surface = False

                        if self.boolean:
                            self.boolean = False
                            remove_mod(self.boolean_mod)
                            self.boolean_mod = None

                        self.is_plane = True

                    self.obj = self.create_cube_object(context)

                    if self.is_subd:
                        subd = add_subdivision(self.obj, name="Subdivision")
                        subd.subdivision_type = 'SIMPLE'
                        subd.show_only_control_edges = False
                        subd.levels = self.subdivisions

                        self.obj.show_wire = True

                    self.transform_object(context)

                elif event.type in ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE'] and event.value == 'PRESS' and not self.is_rounded:
                    self.subdivisions = number_mappings[event.type]

                    if subd:
                        levels = subd.levels

                        if levels != self.subdivisions:
                            subd.levels = self.subdivisions

                        elif not self.is_quad_sphere and levels == self.subdivisions:

                            self.obj.modifiers.remove(subd)

                            self.is_subd = False
                            self.obj.show_wire = False

                    else:
                        subd = add_subdivision(self.obj, name="Subdivision")
                        subd.subdivision_type = 'SIMPLE'
                        subd.show_only_control_edges = False

                        subd.levels = self.subdivisions

                        self.is_subd = True
                        self.obj.show_wire = True

                elif scroll_up(event, key=False) or scroll_down(event, key=False):

                    if event.alt and self.is_subd:
                        if scroll_up(event, key=False):
                            self.subdivisions += 1

                        elif scroll_down(event, key=False):
                            self.subdivisions -= 1

                        subd.levels = self.subdivisions

                    elif event.alt and self.is_rounded:
                        if scroll_up(event, key=False):
                            self.bevel_segments += 1

                        elif scroll_down(event, key=False):
                            self.bevel_segments -= 1

                        bevel_mods = bevel_poll(context, self.obj)

                        for mod in bevel_mods:
                            mod.segments = self.bevel_segments + 1

                elif event.type in ['X', 'Y', 'Z'] and event.value == 'PRESS':
                    if event.type == 'X' and event.value == 'PRESS':
                        self.align_axis = 'Z' if self.align_axis == 'X' else 'X'

                    elif event.type in ['Y', 'Z'] and event.value == 'PRESS':
                        self.align_axis = 'Z' if self.align_axis == 'Y' else 'Y'

                    if self.align_axis == 'Z' and self.is_plane:
                        if self.is_surface:
                            self.is_surface = False

                        if self.is_embed:
                            self.is_embed = False

                    self.transform_object(context)

                elif event.type == 'R' and event.value == 'PRESS':

                    if self.is_rounded:
                        self.is_rounded = False
                        self.obj = self.create_cube_object(context)

                    else:
                        if subd or cast:
                            self.obj.show_wire = False

                            if subd:
                                self.obj.modifiers.remove(subd)

                                self.is_subd = False

                            if cast:
                                self.obj.modifiers.remove(cast)

                                self.is_quad_sphere = False

                        self.is_rounded = True
                        self.bevel_count = 4

                        self.obj = self.create_cube_object(context)

                    self.transform_object(context)

                elif event.type in ['ONE', 'TWO', 'THREE', 'FOUR'] and event.value == 'PRESS' and self.is_rounded:
                    self.bevel_count = number_mappings[event.type]

                    self.obj = self.create_cube_object(context)

                    self.transform_object(context)

            elif self.type == 'ASSET':

                if event.type in ['X', 'Y', 'Z', 'R'] and event.value == 'PRESS':
                    if event.type == 'X':
                        self.align_axis = 'Z' if self.align_axis == 'X' else 'X'

                    elif event.type in ['Y', 'Z']:
                        self.align_axis = 'Z' if self.align_axis == 'Y' else 'Y'

                    elif event.type == 'R':
                        if event.shift:
                            self.rotation_offset += 45
                        else:
                            self.rotation_offset -= 45

                        if self.rotation_offset >= 360:
                            self.rotation_offset = 0
                        elif self.rotation_offset < 0:
                            self.rotation_offset = 315

                    self.transform_object(context)

                elif event.type == 'M' and event.value == 'PRESS':
                    self.is_subset_mirror = not self.is_subset_mirror

                    force_ui_update(context)

            if event.type == 'MOUSEMOVE':
                self.transform_object(context)

            elif event.type == 'S' and event.value == 'PRESS' and self.obj.type != 'EMPTY':
                self.is_surface = not self.is_surface

                if self.is_surface and self.is_embed:
                    self.is_embed = False

                self.transform_object(context)

            elif event.type == 'D' and event.value == 'PRESS' and self.obj.type != 'EMPTY':
                self.is_embed = not self.is_embed

                if self.is_embed and self.is_surface:
                    self.is_surface = False

                self.transform_object(context)

            elif event.type == 'A' and event.value == 'PRESS' and self.obj.type != 'EMPTY':
                self.apply_scale = not self.apply_scale
                context.active_object.select_set(True)

            elif event.type == 'B' and event.value == 'PRESS' and self.obj.type == 'MESH':
                self.boolean = not self.boolean

                if self.boolean_mod:
                    if self.boolean:
                        self.boolean_mod.show_viewport = True
                        self.obj.display_type = self.boolean_display_type

                    else:
                        self.boolean_mod.show_viewport = False
                        self.obj.display_type = 'TEXTURED'

                elif self.boolean:
                    self.setup_boolean(interactive=True)

                self.verify_boolean_is_in_range()

            if self.is_embed:
                if not event.alt and event.shift and (scroll_up(event, key=False) or scroll_down(event, key=False)):
                    if scroll_up(event, key=False):
                        self.embed_depth += 0.1

                    elif scroll_down(event, key=False):
                        self.embed_depth -= 0.1

                    self.transform_object(context)

            if self.boolean:
                if not event.shift and not event.alt and (scroll_up(event, key=False) or scroll_down(event, key=False)):
                    if scroll_up(event, key=True):
                        self.boolean_method = step_enum(self.boolean_method, add_boolean_method_items, 1, loop=True)

                    elif scroll_down(event, key=True):
                        self.boolean_method = step_enum(self.boolean_method, add_boolean_method_items, -1, loop=True)

                    if self.boolean_method == 'SPLIT':
                        self.boolean_mod.operation = 'DIFFERENCE'
                        self.boolean_mod.show_viewport = False

                    else:
                        self.boolean_mod.operation = self.boolean_method
                        self.boolean_mod.show_viewport = self.can_boolean

                    self.boolean_mod.name = self.boolean_method.title()

                elif event.type in ['E', 'F'] and event.value == 'PRESS':
                    if event.type == 'E':
                        self.boolean_solver = 'EXACT'

                    elif event.type == 'F':
                        self.boolean_solver = 'FAST'

                    self.boolean_mod.solver = self.boolean_solver

                elif event.type == 'W' and event.value == 'PRESS':
                    self.boolean_display_type = step_enum(self.boolean_display_type, boolean_display_type_items, 1)

                    self.obj.display_type = self.boolean_display_type

                    for mod in self.secondary_booleans:
                        mod.object.display_type = self.boolean_display_type

        if event.type in finish_events:
            self.finish(context)

            if event.type in ['L', 'MIDDLEMOUSE']:
                redoCOL = context.scene.HC.redoaddobjCOL

                name = self.type if self.type in ['CUBE', 'CYLINDER'] else self.obj.HC.assetpath
                entry = redoCOL[name]
                self.size = entry.size

                self.set_obj_size(context, interactive=False)

                self.hide_boolean = entry.hide_boolean

            else:
                self.hide_boolean = self.obj.type == 'MESH' and self.boolean and event.type == 'SPACE'

            if self.type == 'CUBE':
                if self.is_quad_sphere or self.is_subd:
                    self.apply_mods()

                self.finish_cube()

            elif self.type == 'CYLINDER':
                self.finish_cylinder()

            if self.can_scale_be_applied:
                self.apply_obj_scale(context)

            self.finish_boolean(context)

            self.store_props(context)

            if self.hide_boolean:
                self.hide_cutter(context)

            self.subset_mirror()

            self.finalize_selection(context)

            if self.type in ['CUBE', 'CYLINDER'] and self.toggled_use_enter_edit_mode and not self.hide_boolean:
                bpy.ops.object.mode_set(mode='EDIT')

            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.finish(context)

            for obj in context.selected_objects:
                if obj.type == 'MESH' and obj.data.users == 1:
                    bpy.data.meshes.remove(obj.data, do_unlink=True)
                else:
                    bpy.data.objects.remove(obj, do_unlink=True)

            if self.boolean_mod:
                self.boolean_parent.modifiers.remove(self.boolean_mod)

            for mod in self.secondary_booleans:
                self.boolean_parent.modifiers.remove(mod)

            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish_cube(self):
        bm = bmesh.new()
        bm.from_mesh(self.obj.data)
        bm.normal_update()

        edge_glayer, face_glayer = ensure_gizmo_layers(bm)

        if not (self.is_quad_sphere or self.is_subd):

            for e in bm.edges:
                e[edge_glayer] = 1

            for f in bm.faces:
                f[face_glayer] = 1

        bm.to_mesh(self.obj.data)
        bm.free()

        self.obj.HC.ishyper = True
        self.obj.HC.objtype = 'CUBE'

    def finish_cylinder(self):
        bm = bmesh.new()
        bm.from_mesh(self.obj.data)
        bm.normal_update()

        edge_glayer, face_glayer = ensure_gizmo_layers(bm)

        if self.is_plane:
            caps = bm.faces
            ring_edges = bm.edges

        else:
            caps = [f for f in bm.faces if len(f.verts) != 4]

            ring_edges = [e for f in caps for e in f.edges]
            vertical_edges = [e for e in bm.edges if e not in ring_edges]

        for e in ring_edges:
            e[edge_glayer] = 1

        if not self.is_plane:
            vertical_edges[0][edge_glayer] = 1

        for f in caps:
            f[face_glayer] = 1

        bm.to_mesh(self.obj.data)
        bm.free()

        self.obj.HC.ishyper = True
        self.obj.HC.objtype = 'CYLINDER'
        
        self.obj.HC.avoid_update = True
        self.obj.HC.objtype_without_none = 'CYLINDER'

    def apply_mods(self):
        subd = get_subdivision(self.obj)

        if subd:
            apply_mod(subd.name)
            self.obj.show_wire = False

        cast = get_cast(self.obj)

        if cast:
            apply_mod(cast.name)

    def can_scale_be_applied(self, context):
        if self.obj.type == 'MESH':

            if self.obj.children:
                return False

            if bevel_poll(context, self.obj) and not is_uniform_scale(self.obj):
                return False

            return True
        return False

    def apply_obj_scale(self, context, debug=False):
        if self.apply_scale and self.obj.type == 'MESH' and not self.obj.children:

            if debug:
                print("applying scale")

            bevel_mods = bevel_poll(context, self.obj)

            if debug and bevel_mods:
                print("found bevel mods")

            if bevel_mods:
                if not is_uniform_scale(self.obj):
                    if debug:
                        print("object has bevel mods but isn't scalled uniformly, not aplying scale")
                    return

                bevel_compensator = 1 / (self.size * self.mesh_max_dimension_factor)

                if debug:
                    print("bevel compensator:", bevel_compensator)

                if bevel_compensator >= 1:
                    if debug:
                        print(" compensating bevels before applying scale")

                    for mod in bevel_mods:
                        mod.width /= 1 / (self.size * self.mesh_max_dimension_factor)

                    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True, isolate_users=True)

                else:
                    if debug:
                        print(" compensating bevels after applying scale")

                    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True, isolate_users=True)

                    for mod in bevel_mods:
                        mod.width /= 1 / (self.size * self.mesh_max_dimension_factor)
            else:
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True, isolate_users=True)

            if debug:
                print("scale is applied")

    def finish_boolean(self, context):
        if self.boolean and self.boolean_parent and self.can_boolean:
            parent(self.obj, self.boolean_parent)

            hide_render(self.obj, True)

            boolean_mod_name = self.boolean_mod.name

            secondary_boolean_names = [mod.name for mod in self.secondary_booleans]

            sort_modifiers(self.boolean_parent, debug=False)

            self.boolean_mod = self.boolean_parent.modifiers.get(boolean_mod_name)
            self.secondary_booleans = [self.boolean_parent.modifiers.get(name) for name in secondary_boolean_names]

            for mod in self.secondary_booleans:
                hide_render(mod.object, True)

            if self.boolean_method == 'SPLIT':
                view = context.space_data

                self.boolean_mod.show_viewport = True

                self.boolean_mod.name = 'Split (Difference)'

                context.view_layer.objects.active = self.boolean_parent
                self.boolean_parent.select_set(True)

                children = {str(uuid4()): (obj, obj.visible_get()) for obj in self.boolean_parent.children_recursive if obj.name in context.view_layer.objects}

                for dup_hash, (obj, vis) in children.items():
                    obj.HC.dup_hash = dup_hash

                    if not vis:
                        if view.local_view and not obj.local_view_get(view):
                            obj.local_view_set(view, True)

                    obj.hide_set(False)
                    obj.select_set(True)

                bpy.ops.object.duplicate(linked=False)

                boolean_parent_dup = context.active_object
                dup_mod = boolean_parent_dup.modifiers.get(self.boolean_mod.name)
                dup_mod.operation = 'INTERSECT'
                dup_mod.name ='Split (Intersect)'

                dup_children = [obj for obj in boolean_parent_dup.children_recursive if obj.name in context.view_layer.objects]

                for dup in dup_children:
                    orig, vis = children[dup.HC.dup_hash]

                    orig.hide_set(not vis)
                    dup.hide_set(not vis)

                    if orig == self.obj:

                        dupmesh = dup.data
                        dup.data = orig.data

                        bpy.data.meshes.remove(dupmesh, do_unlink=False)

                        self.obj_dup = dup

                    orig.HC.dup_hash = ''
                    dup.HC.dup_hash = ''

                obj_dup = dup_mod.object
                add_displace(obj_dup, mid_level=0, strength=-0.005)

                bpy.ops.object.select_all(action='DESELECT')
                context.view_layer.objects.active = obj_dup
                obj_dup.select_set(True)

        elif self.boolean_mod:

            for mod in [self.boolean_mod] + self.secondary_booleans:
                remove_mod(mod)

            self.boolean_mod = None
            self.secondary_booleans = []

    def hide_cutter(self, context):
        if self.boolean:
            self.obj.hide_set(True)

            wire_children = [obj for obj in self.obj.children_recursive if is_wire_object(obj)]

            for obj in wire_children:
                obj.hide_set(True)
                
            if self.boolean and self.boolean_method == 'SPLIT':
                self.obj_dup.hide_set(True)

                wire_children = [obj for obj in self.obj_dup.children_recursive if is_wire_object(obj)]

                for obj in wire_children:
                    obj.hide_set(True)

                context.space_data.shading.show_object_outline = True

            if self.secondary_booleans:
                for mod in self.secondary_booleans:
                    mod.object.hide_set(True)

    def finalize_selection(self, context):

        if self.type == 'ASSET' and self.boolean_parent and self.boolean and self.hook_objs:
            handle = self.hook_objs[0]

            bpy.ops.object.select_all(action='DESELECT')

            if not handle.visible_get():
                handle.hide_set(False)

            handle.select_set(True)
            context.view_layer.objects.active = handle

        elif self.boolean_parent and self.hide_boolean:
            bpy.ops.object.select_all(action='DESELECT')
            self.boolean_parent.select_set(True)
            context.view_layer.objects.active = self.boolean_parent

    def subset_mirror(self):
        if self.has_subset_mirror and self.is_subset_mirror:
            for mod in self.mirror_mods:
                for obj in self.subset_objs:
                    mirror = add_mirror(obj)

                    mirror.use_axis = mod.use_axis
                    mirror.use_bisect_axis = mod.use_bisect_axis
                    mirror.use_bisect_flip_axis = mod.use_bisect_flip_axis
                    mirror.show_expanded = mod.show_expanded

                    mirror.mirror_object = mod.mirror_object if mod.mirror_object else self.boolean_parent

    def store_props(self, context):
        redoCOL = context.scene.HC.redoaddobjCOL

        name = self.type if self.type in ['CUBE', 'CYLINDER'] else self.obj.HC.assetpath

        if name in redoCOL:
            entry = redoCOL[name]

        else:
            entry = redoCOL.add()
            entry.name = name

            if self.type == 'ASSET':
                entry.original_mesh_max_dimension_factor = str(self.mesh_max_dimension_factor)

            if name not in ['CUBE', 'CYLINDER']:
                entry.libname = self.obj.HC.libname
                entry.blendpath = self.obj.HC.blendpath
                entry.assetname = self.obj.HC.assetname

        entry.surface = self.is_surface

        entry.embed = self.is_embed
        entry.embed_depth = self.embed_depth

        entry.apply_scale = self.apply_scale

        entry.size = self.size

        entry.sides = self.sides

        entry.is_quad_sphere = self.is_quad_sphere
        entry.is_plane = self.is_plane
        entry.is_subd = self.is_subd
        entry.subdivisions = self.subdivisions

        entry.is_rounded = self.is_rounded
        entry.bevel_count = self.bevel_count
        entry.bevel_segments = self.bevel_segments

        entry.align_axis = self.align_axis

        entry.boolean = self.boolean
        entry.boolean_method = self.boolean_method
        entry.boolean_solver = self.boolean_solver

        entry.hide_boolean = self.hide_boolean

        entry.display_type = self.obj.display_type

        if self.has_subset_mirror:
            entry.is_subset_mirror = self.is_subset_mirror

        index = list(redoCOL).index(entry)

        context.scene.HC.redoaddobjIDX = index

def draw_pipe_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text="Add Pipe")

        if len(op.pipe_coords) > 1:
            row.label(text="", icon='EVENT_SPACEKEY')
            row.label(text="Finish")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        if len(op.pipe_coords) > 1:
            row.label(text="", icon='EVENT_O')
            row.label(text=f"Origin: {op.origin.title().replace('_', ' ')}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_D')
            row.label(text=f"Delete Mode: {op.delete_mode}")

            if op.delete_mode:
                row.label(text="", icon='MOUSE_MMB')
                row.label(text="Select Previous/Next Curve Point for Deletion")

            else:
                row.separator(factor=2)

                row.label(text="", icon='EVENT_X')
                row.label(text="", icon='EVENT_Y')
                row.label(text="", icon='EVENT_Z')
                row.label(text=f"Mirror: {'X' if op.is_mirror_x else 'Y' if op.is_mirror_y else 'Z' if op.is_mirror_z else False}")

        if len(op.pipe_coords) > 2 and not op.delete_mode:
            row.separator(factor=2)

            row.label(text="", icon='EVENT_C')
            row.label(text=f"Cyclic: {op.is_cyclic}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_R')
            row.label(text=f"Rounded: {op.is_rounded}")

            if op.is_rounded:
                row.separator(factor=2)

                row.label(text="", icon='EVENT_A')
                row.label(text=f"Adaptive: {op.is_adaptive}")

                row.separator(factor=2)

                row.label(text="", icon='MOUSE_MMB')
                if op.is_adaptive:
                    row.label(text=f"Factor: {op.adaptive_factor}")
                else:
                    row.label(text=f"Segments: {op.round_segments}")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_Q')
                row.label(text=f"Mode: {op.round_mode.title()}")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_W')
                row.label(text=f"Adjust {op.round_mode.title()}")

    return draw

class AddPipe(bpy.types.Operator):
    bl_idname = "machin3.add_pipe"
    bl_label = "MACHIN3: Add Pipe"
    bl_description = "Create Pipe Curve"
    bl_options = {'REGISTER', 'UNDO'}

    is_cyclic: BoolProperty(name="is Cyclic", default=False)
    is_rounded: BoolProperty(name="is Rounded", default=False)
    is_mirror_x: BoolProperty(name="is Mirror X", default=False)
    is_mirror_y: BoolProperty(name="is Mirror Y", default=False)
    is_mirror_z: BoolProperty(name="is Mirror Z", default=False)
    round_mode: EnumProperty(name="Round Mode", items=pipe_round_mode_items, default='RADIUS')
    round_segments: IntProperty(name="Round Segments", default=6, min=0)
    is_adaptive: BoolProperty(name="is Adaptive", default=True)
    adaptive_factor: IntProperty(name="Adaptive Factor", default=10, min=1)
    radius: FloatProperty(name="Radius", default=0.1, min=0)
    origin: EnumProperty(name="Origin", items=pipe_origin_items, default='AVERAGE_ENDS')
    def draw_VIEW3D(self, context):
        if context.area == self.area:
            if len(self.cursor_coords) > 1:

                draw_line(self.pipe_coords, color=blue, width=3, alpha=0.8)

                draw_point(self.origin_loc, color=yellow, size=6)

                axes = [(Vector((1, 0, 0)), red), (Vector((0, 1, 0)), green), (Vector((0, 0, 1)), blue)]
                factor = get_zoom_factor(context, self.origin_loc, scale=20, ignore_obj_scale=True)
                size = 1

                for axis, color in axes:
                    coords = []

                    coords.append(self.origin_loc + (self.origin_rot @ axis).normalized() * size * factor * 0.1)
                    coords.append(self.origin_loc + (self.origin_rot @ axis).normalized() * size * factor)

                    draw_line(coords, color=color, alpha=1)

            if self.delete_mode:
                draw_point(self.cursor_coords[self.delete_idx], size=11 if self.is_rounded else 7, color=red, alpha=1)

            color, size = (yellow, 5) if self.is_rounded else (white, 3)
            draw_points(self.cursor_coords, size=size, color=color, alpha=0.5)

            if self.is_rounded:
                color = green if self.round_mode == 'RADIUS' else orange

                if self.rounded_mid_coords:
                    draw_points(self.rounded_mid_coords, size=5 if self.round_mode == 'RADIUS' else 4, color=color, alpha=0.5)

                if self.rounded_trim_coords:
                    draw_points(self.rounded_trim_coords, size=3, color=color, alpha=1)

                if self.rounded_mid_coords and self.rounded_trim_coords:

                    if self.round_mode == 'RADIUS':
                        for mid, trim_prev, trim_next in zip(self.rounded_mid_coords, self.rounded_trim_coords[0::2], self.rounded_trim_coords[1::2]):
                            draw_line([mid, trim_prev], alpha=0.2)
                            draw_line([mid, trim_next], alpha=0.2)

                    elif self.round_mode == 'OFFSET':
                        for corner, trim_prev, trim_next in zip(self.rounded_corner_coords, self.rounded_trim_coords[0::2], self.rounded_trim_coords[1::2]):
                            draw_line([corner, trim_prev], alpha=0.2)
                            draw_line([corner, trim_next], alpha=0.2)

                if self.rounded_arc_coords:
                    draw_points(self.rounded_arc_coords, size=3, alpha=0.5)

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            if self.is_rounded and self.adjust_radius_mode:
                draw_label(context, title=f"Adjust {self.round_mode.title()}", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

                self.offset += 18
                draw_label(context, title=dynamic_format(self.radius, decimal_offset=1), coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

    def modal(self, context, event):
        if ignore_events(event):
            return {'PASS_THROUGH'}

        context.area.tag_redraw()

        if ignore_events(event, timer=True, timer_report=True):
            return {'RUNNING_MODAL'}

        if self.is_rounded and event.type == 'ESC':
            return {'PASS_THROUGH'}

        elif event.shift and event.type == 'W':
            return {'PASS_THROUGH'}

        if event.type == 'W':
            if self.is_rounded:
                if event.value == 'PRESS':
                    get_mouse_pos(self, context, event)

                    self.last_mouse = self.mouse_pos

                    self.adjust_radius_mode = True

                    self.factor = get_zoom_factor(context, depth_location=self.cursor.location, scale=1, ignore_obj_scale=True)

                    context.window.cursor_set('SCROLL_X')

                elif event.value == 'RELEASE':
                    self.adjust_radius_mode = False

                    context.window.cursor_set('DEFAULT')

            return {'RUNNING_MODAL'}

        self.pipe_coords = self.get_pipe_coords(context, debug=False)

        if event.type == 'D':

            if len(self.cursor_coords) == 1:
                self.finish(context)
                return {'CANCELLED'}

            else:
                if event.value == 'PRESS':

                    if not self.delete_mode:
                        self.delete_mode = True
                        self.delete_idx = len(self.cursor_coords) - 1

                    context.window.cursor_set('STOP')

                elif event.value == 'RELEASE':
                    self.delete_mode = False

                    self.remove_cursor_coord(context, debug=False)

                    context.window.cursor_set('DEFAULT')

                    self.pipe_coords = self.get_pipe_coords(context, debug=False)

                force_ui_update(context)

            return {'RUNNING_MODAL'}

        if self.delete_mode:

            if scroll_up(event, key=True) or scroll_down(event, key=True):
                if scroll_up(event, key=True):
                    self.delete_idx = max(self.delete_idx - 1, 0)

                elif scroll_down(event, key=True):
                    self.delete_idx = min(self.delete_idx + 1, len(self.cursor_coords) - 1)

            return {'RUNNING_MODAL'}

        events = ['MOUSEMOVE', 'R', 'Q', 'A', 'X', 'Y', 'Z', 'O']

        if event.type == 'C' and not event.shift:
            events.append('C')

        if event.type in events or (self.is_rounded and (scroll_up(event, key=True) or scroll_down(event, key=True))):
            if event.type == 'MOUSEMOVE' and self.adjust_radius_mode:
                get_mouse_pos(self, context, event)
                wrap_mouse(self, context, x=True)

                delta_x = self.mouse_pos.x - self.last_mouse.x
                factor = self.factor / 20 if event.shift else self.factor * 10 if event.ctrl else self.factor

                self.radius += delta_x * factor

                self.pipe_coords = self.get_pipe_coords(context, debug=False)

            if event.value == 'PRESS':
                if len(self.cursor_coords) > 1:

                    if event.type == 'O':
                        self.origin = step_enum(self.origin, pipe_origin_items, step=1, loop=True)

                    elif event.type in ['X', 'Y', 'Z']:
                        if event.type == 'X':
                            self.is_mirror_x = not self.is_mirror_x
                            self.is_mirror_y = False
                            self.is_mirror_z = False

                        elif event.type == 'Y':
                            self.is_mirror_x = False
                            self.is_mirror_y = not self.is_mirror_y
                            self.is_mirror_z = False

                        elif event.type == 'Z':
                            self.is_mirror_x = False
                            self.is_mirror_y = False
                            self.is_mirror_z = not self.is_mirror_z

                if len(self.cursor_coords) > 2:

                    if event.type == 'C':
                        self.is_cyclic = not self.is_cyclic

                    elif event.type == 'R':
                        self.is_rounded = not self.is_rounded

                        if self.is_rounded and not self.has_rounded_been_activated:
                            self.has_rounded_been_activated = True
                            self.radius = min([(co2 - co1).length for co1, co2 in zip(self.cursor_coords, self.cursor_coords[1:])]) / 2

                        if not self.is_rounded:
                            for r in self.radiiCOL:
                                r.hide = True

                    elif self.is_rounded and event.type == 'Q':
                        self.round_mode = step_enum(self.round_mode, pipe_round_mode_items, step=1, loop=True)

                    elif event.type == 'A':
                        self.is_adaptive = not self.is_adaptive

                    elif scroll_up(event, key=True) or scroll_down(event, key=True):
                        if scroll_up(event, key=True):
                            if self.is_adaptive:
                                self.adaptive_factor -= 10 if event.ctrl else 1
                            else:
                                self.round_segments += 1

                        elif scroll_down(event, key=True):
                            if self.is_adaptive:
                                self.adaptive_factor += 10 if event.ctrl else 1
                            else:
                                self.round_segments -= 1

                self.pipe_coords = self.get_pipe_coords(context, debug=False)

                force_ui_update(context)

                return {'RUNNING_MODAL'}

        if self.cursor.location != self.cursor_coords[-1]:
            print()
            print("adding pipe coord:", self.cursor.location)
            print("last cursor coord:", self.cursor_coords[-1])
            print("event:", event.type)

            self.add_cursor_coord(context, debug=False)

            self.pipe_coords = self.get_pipe_coords(context, debug=False)

        if self.cursor.matrix.to_3x3() != self.last_cursor_rotation:
            if any([self.is_mirror_x, self.is_mirror_y, self.is_mirror_z]):
                self.pipe_coords = self.get_pipe_coords(context, debug=False)

        if event.type in ['SPACE'] and len(self.pipe_coords) > 1:
            self.finish(context)
            self.create_curve_object(context)
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE'] and event.value == 'PRESS':
            self.finish(context)

            return {'CANCELLED'}

        self.last_mouse = self.mouse_pos
        
        self.last_cursor_rotation = self.cursor.matrix.to_3x3()

        return {'PASS_THROUGH'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

        context.window_manager.gizmo_group_type_unlink_delayed('MACHIN3_GGT_pipe_radius')

        restore_gizmos(self)

        self.radiiCOL.clear()

        force_ui_update(context)

    def invoke(self, context, event):
        self.cursor = context.scene.cursor
        self.last_cursor_rotation = self.cursor.matrix.to_3x3()
        self.is_rounded = False
        self.has_rounded_been_activated = False
        self.adjust_radius_mode = False
        self.delete_mode = False
        self.delete_idx = 0

        self.radiiCOL = context.window_manager.HC_piperadiiCOL
        self.radiiCOL.clear()

        self.origin_loc = self.cursor.location.copy()
        self.origin_rot = self.cursor.rotation_quaternion.copy()

        self.factor = get_zoom_factor(context, depth_location=self.cursor.location, scale=5, ignore_obj_scale=True)

        self.cursor_coords = []
        self.add_cursor_coord(context, debug=False)

        self.pipe_coords = self.cursor_coords.copy()

        self.rounded_mid_coords = []
        self.rounded_corner_coords = []
        self.rounded_trim_coords = []
        self.rounded_arc_coords = []

        hide_gizmos(self, context, buttons=['HISTORY', 'FOCUS', 'SETTINGS', 'CAST', 'OBJECT'], debug=False)

        hc = context.scene.HC
        hc.show_gizmos = True
        hc.show_button_cast = True
        hc.draw_HUD = True

        hc.draw_pipe_HUD = True
        self.hidden_gizmos['draw_pipe_HUD'] = False

        self.store_pre_pipe_gizmo_settings_on_scene(context)

        get_mouse_pos(self, context, event)

        self.last_mouse = self.mouse_pos

        context.window_manager.gizmo_group_type_ensure('MACHIN3_GGT_pipe_radius')

        init_status(self, context, func=draw_pipe_status(self))

        force_ui_update(context)

        self.area = context.area
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def add_cursor_coord(self, context, debug=False):
        coord = self.cursor.location.copy()

        self.cursor_coords.append(coord)

        r = self.radiiCOL.add()
        r.co = coord
        r.hide = True
        r.area_pointer = str(context.area.as_pointer())

        if debug:
            print("\nadded new pipe co to self.cursor_coords and HCpiperaddiCOL")

            for co in self.cursor_coords:
                print(co)

        if len(self.cursor_coords) > 2:
            redundant = []

            if debug:
                print("\nchecking for redundant coords")

            for idx, co in enumerate(self.cursor_coords):

                if 0 < idx < len(self.cursor_coords) - 1:
                    prev_co = self.cursor_coords[(idx - 1) % len(self.cursor_coords)]
                    next_co = self.cursor_coords[(idx + 1) % len(self.cursor_coords)]

                    if debug:
                        print(idx, co)
                        print(" prev:", prev_co)
                        print(" next:", next_co)

                    vec_prev = (prev_co - co).normalized()
                    vec_next = (next_co - co).normalized()

                    angle = round(degrees(vec_prev.angle(vec_next)))

                    if debug:
                        print(" angle:", angle)

                    if angle in [0, 180]:
                        redundant.append(idx)

                        if debug:
                            print(" is redundant")

            if redundant:
                if debug:
                    print("\nremoving indices:", redundant)

                for idx in sorted(redundant, reverse=True):
                    if debug:
                        print("removing redundant index:", idx)

                    self.cursor_coords.pop(idx)
                    self.radiiCOL.remove(idx)

                if debug:
                    print("\npost redundancy removal")

                    for co in self.cursor_coords:
                        print("", co)

                    print()

                    for r in self.radiiCOL:
                        print("", Vector(r.co))

        force_ui_update(context)

    def remove_cursor_coord(self, context, debug=False):
        if debug:
            print("\nremoving index", self.delete_idx)

        self.cursor_coords.pop(self.delete_idx)
        self.radiiCOL.remove(self.delete_idx)

        if debug:
            for co in self.cursor_coords:
                print("", co)

            print()

            for r in self.radiiCOL:
                print("", Vector(r.co))

        if self.delete_idx != len(self.cursor_coords) - 1:
            self.cursor.location = self.cursor_coords[-1]

            bpy.ops.view3d.view_center_cursor('INVOKE_DEFAULT' if context.scene.HC.focus_mode == 'SOFT' else 'EXEC_DEFAULT')

    def get_pipe_coords(self, context, debug=False):
        is_mirror = any([self.is_mirror_x, self.is_mirror_y, self.is_mirror_z])

        if is_mirror:
            mirror_coords, angle = self.get_mirror_coords(debug=debug)

            if mirror_coords:
                cursor_coords = self.cursor_coords + mirror_coords

        else:
            cursor_coords = self.cursor_coords.copy()

        if self.is_rounded:
            pipe_coords = self.get_rounded_pipe_coords(context, cursor_coords, debug=False)

        else:

            if is_mirror and round(angle) == 180:
                cursor_coords.pop(len(self.cursor_coords) - 1)

            pipe_coords = cursor_coords.copy()

            if self.is_cyclic:
                pipe_coords.append(self.cursor_coords[0])

        self.update_pipe_origin(cursor_coords)

        return pipe_coords

    def get_rounded_pipe_coords(self, context, cursor_coords, debug=False):
        def get_arc_coords(idx, co, prev_co, next_co, modulate, segment_modulate, debug=False):
            vec_prev = (prev_co - co).normalized()
            vec_next = (next_co - co).normalized()

            if vec_prev.length != 0 and vec_next.length != 0:
                angle = degrees(vec_prev.angle(vec_next))

                if round(angle) == 180:
                    if debug:
                        print(idx, "coord is 180 degees and so redundant")
                    return []

            else:
                if debug:
                    print(idx, "coord has zero length vectors to the next and/or previous")
                return [co]

            if debug:
                print(idx, "has", angle, "degrees")

            if self.round_mode == 'OFFSET':
                trim_prev_co = co + vec_prev * (self.radius + modulate)
                trim_next_co = co + vec_next * (self.radius + modulate)

                beta = angle / 2
                a = self.radius + modulate
                b = a * tan(radians(beta))

            elif self.round_mode == 'RADIUS':

                alpha = 180 - 90 - (angle / 2)
                b = self.radius + modulate
                a = b * tan(radians(alpha))

                trim_prev_co = co + vec_prev * a
                trim_next_co = co + vec_next * a

            arc_coords = [trim_prev_co]

            self.rounded_trim_coords.extend([trim_prev_co, trim_next_co])

            c = sqrt(pow(a, 2) + pow(b, 2))

            vec_mid = (vec_prev + vec_next).normalized()
            mid_co = co + vec_mid * c

            self.rounded_mid_coords.append(mid_co)
            self.rounded_corner_coords.append(co)

            arc_vec_prev = trim_prev_co - mid_co
            arc_vec_next = trim_next_co - mid_co

            delta = arc_vec_prev.rotation_difference(arc_vec_next)

            if self.is_adaptive:

                if self.round_mode == 'RADIUS':
                    segments = round((180 - angle) / self.adaptive_factor) + int(segment_modulate)

                elif self.round_mode == 'OFFSET':

                    arc_length = b * (180 - angle)
                    segments = round(arc_length / (self.adaptive_factor / 10)) + int(segment_modulate)

            else:
                segments = self.round_segments + 1 + int(segment_modulate)

            for segment in range(1, segments):
                factor = segment / segments

                rot = delta.copy()
                rot.angle = delta.angle * factor

                arc = rot @ arc_vec_prev

                arc_co = mid_co + arc

                arc_coords.append(arc_co)

                self.rounded_arc_coords.append(arc_co)

            arc_coords.append(trim_next_co)

            return arc_coords

        self.rounded_mid_coords = []
        self.rounded_corner_coords = []
        self.rounded_trim_coords = []
        self.rounded_arc_coords = []

        if debug:
            print("\npre-rounding coordinate comparison")

            print(len(self.cursor_coords))
            print(len(self.radiiCOL))
            print(len(cursor_coords))

            print()
            print("compare")

        is_mirror = len(self.radiiCOL) != len(cursor_coords)
        is_cyclic = self.is_cyclic

        rounded_coords = []

        for idx, (origco, colco, argco) in enumerate(zip_longest(self.cursor_coords, self.radiiCOL, cursor_coords)):

            if debug:
                print()
                print(idx)
                print("orig:", origco)
                print(" col:", Vector(colco.co) if colco else colco)
                print(" arg:", argco)

            if idx == 0:
                if is_cyclic:
                    prev_co = cursor_coords[-1]
                    next_co = cursor_coords[idx + 1]

                    modulate = self.radiiCOL[idx].modulate
                    segment_modulate = self.radiiCOL[idx].segment_modulate

                    if debug:
                        print("first coord, and it's cyclic, so is rounded", modulate)
                else:
                    if debug:
                        print("first coord, no rounding")

                    rounded_coords.append(argco)

                    colco.hide = True
                    continue

            elif is_mirror and (idx == len(self.radiiCOL) - 1 or idx == len(cursor_coords) - 1):

                if idx == len(self.radiiCOL) - 1:
                    prev_co = cursor_coords[idx - 1]
                    next_co = cursor_coords[idx + 1]

                    modulate = self.radiiCOL[idx].modulate
                    segment_modulate = self.radiiCOL[idx].segment_modulate

                    if debug:
                        print("mirror intersection coord", modulate)

                elif idx == len(cursor_coords) - 1:
                    if is_cyclic:
                        mapped_back_idx = 0

                        prev_co = cursor_coords[idx - 1]
                        next_co = cursor_coords[0]

                        modulate = self.radiiCOL[mapped_back_idx].modulate
                        segment_modulate = self.radiiCOL[mapped_back_idx].segment_modulate

                        if debug:
                            print("last mirrored coord and its cyclic, so is rounded", modulate)
                            print(" but get's no gizmo!")
                            print(" mapped back to", mapped_back_idx)

                    else:
                        if debug:
                            print("last mirrored coord, no rounding")

                        rounded_coords.append(argco)
                        continue

            elif idx == len(self.radiiCOL) - 1:
                if is_cyclic:
                    prev_co = cursor_coords[idx - 1]
                    next_co = cursor_coords[0]

                    modulate = self.radiiCOL[idx].modulate
                    segment_modulate = self.radiiCOL[idx].segment_modulate

                    if debug:
                        print("last original coord and it's cyclic, so is rounded", modulate)

                else:
                    if debug:
                        print("last original coord, no rounding")

                    rounded_coords.append(argco)

                    colco.hide = True
                    continue

            else:
                prev_co = cursor_coords[idx - 1]
                next_co = cursor_coords[idx + 1]

                if colco:
                    modulate = self.radiiCOL[idx].modulate
                    segment_modulate = self.radiiCOL[idx].segment_modulate

                    if debug:
                        print("normal coord, so is rounded", modulate)

                else:
                    mapped_back_idx = len(cursor_coords) - idx - 1
                    modulate = self.radiiCOL[mapped_back_idx].modulate
                    segment_modulate = self.radiiCOL[mapped_back_idx].segment_modulate

                    if debug:
                        print("normal mirrored coord, so is rounded", modulate)
                        print(" but get's no gizmo!")
                        print(" mapped back to", mapped_back_idx)

            arc_coords = get_arc_coords(idx, argco, prev_co, next_co, modulate, segment_modulate, debug=debug)
            rounded_coords.extend(arc_coords)

            if colco:
                colco.hide = len(arc_coords) < 2

        if is_cyclic:
            rounded_coords.append(rounded_coords[0])

        return rounded_coords

    def get_mirror_coords(self, debug=False):
        axis = 'X' if self.is_mirror_x else 'Y' if self.is_mirror_y else 'Z' if self.is_mirror_z else None

        mirror_coords = []

        if axis:
            if debug:
                print("mirroring across", axis)

            mirror_dir = self.cursor.matrix.to_3x3() @ axis_vector_mappings[axis]

            for co in reversed(self.cursor_coords[:-1]):
                i = intersect_line_plane(co, co + mirror_dir, self.cursor.location, mirror_dir)

                mirror_vec = i - co

                mirror_co = co + 2 * mirror_vec

                mirror_coords.append(mirror_co)

        vec_prev = self.cursor_coords[-2] - self.cursor_coords[-1]
        vec_next = mirror_coords[0] - self.cursor_coords[-1]
        mirror_angle = degrees(vec_prev.angle(vec_next))

        return mirror_coords, mirror_angle

    def update_pipe_origin(self, coords, debug=False):
        if self.origin in ['AVERAGE_ENDS', 'CURSOR_ORIENTATION']:
            self.origin_loc = average_locations([coords[0], coords[-1]])

        else:
            self.origin_loc = self.cursor.location

        if self.origin == 'AVERAGE_ENDS' and len(coords) > 2:

            v_start = (coords[1] - coords[0]).normalized()
            v_end = (coords[-2] - coords[-1]).normalized()
            z = average_normals([v_start, v_end])

            x = (coords[-1] - coords[0]).normalized()

            y = z.cross(x)

            z = x.cross(y)

            if debug:
                draw_vector(x * 0.1, origin=self.origin_loc + Vector((0, 0, 0.1)), color=red, alpha=1, modal=False)
                draw_vector(y * 0.1, origin=self.origin_loc + Vector((0, 0, 0.1)), color=green, alpha=1, modal=False)
                draw_vector(z * 0.1, origin=self.origin_loc + Vector((0, 0, 0.1)), color=blue, alpha=1, modal=False)

            self.origin_rot = create_rotation_matrix_from_vectors(x, y, z).to_quaternion()

        else:
            self.origin_rot = self.cursor.rotation_quaternion

    def store_pre_pipe_gizmo_settings_on_scene(self, context):
        context.scene.HC['hidden_gizmos'] = self.hidden_gizmos

    def create_curve_object(self, context):
        pipemx = Matrix.LocRotScale(self.origin_loc, self.origin_rot, Vector((1, 1, 1)))

        curve = bpy.data.curves.new('Pipe', type='CURVE')

        curve = bpy.data.curves.new(name='Curve', type='CURVE')
        curve.dimensions = '3D'

        curve.use_fill_caps = True
        curve.bevel_resolution = 12

        spline = curve.splines.new('POLY')

        coords = self.pipe_coords[:-1] if self.is_cyclic else self.pipe_coords
        spline.use_cyclic_u = self.is_cyclic

        spline.points.add(len(coords) - 1)

        for idx, co in enumerate(coords):
            local_co = pipemx.inverted_safe() @ co
            spline.points[idx].co = (*local_co, 1)

        spline.use_smooth = False

        pipe = bpy.data.objects.new('Pipe', object_data=curve)
        pipe.matrix_world = pipemx

        pipe.HC.ishyper = True

        bpy.ops.object.select_all(action='DESELECT')

        context.scene.collection.objects.link(pipe)
        pipe.select_set(True)
        context.view_layer.objects.active = pipe

class AddCurveAsset(bpy.types.Operator):
    bl_idname = "machin3.add_curve_asset"
    bl_label = "MACHIN3: Add Curve Asset"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.active_object

    def invoke(self, context, event):
        curve = context.active_object

        is_wire_shading = context.space_data.shading.type == 'WIREFRAME'

        wire_objs = [] if is_wire_shading else [obj for obj in context.visible_objects if is_wire_object(obj)] 

        mousepos = Vector((event.mouse_region_x, event.mouse_region_y))
        dg = context.evaluated_depsgraph_get()

        hit, hitobj, _, hitlocation_eval, _, _ = cast_scene_ray_from_mouse(mousepos, dg, exclude=wire_objs, debug=False)
        
        if hit:

            if hitobj.type == 'MESH':
                bevel_obj = hitobj
                mx = bevel_obj.matrix_world

                msg = ["ℹℹ The dropped Curve Asset couldn't be used as a Bevel Profile ℹℹ"]

                data = get_curve_as_dict(curve.data)

                if spline := verify_curve_data(data, 'is_first_spline_non-cyclic'):

                    if verify_curve_data(data, 'is_first_spline_profile'):

                        hyper_bevel = None

                        if bevelsCOL := context.window_manager.HC_pickhyperbevelsCOL:
                            for b in bevelsCOL:
                                if b.is_highlight:
                                    hyper_bevel = b

                        if hyper_bevel:
                            obj = hyper_bevel.obj
                            active = obj.parent

                            edge_bevel = obj.modifiers.get('Edge Bevel')

                            if edge_bevel:

                                coords = get_profile_coords_from_spline(spline, flop=False)

                                create_bevel_profile(edge_bevel, coords)

                                remove_obj(curve)

                                bpy.ops.object.select_all(action='DESELECT')
                                active.select_set(True)
                                context.view_layer.objects.active = active

                                bpy.ops.machin3.edit_hyper_bevel('INVOKE_DEFAULT', modname=hyper_bevel.name, objname=active.name, is_profile_drop=True)

                                return {'FINISHED'}

                            else:
                                msg.append("There is no Edge Bevel Modifier on this HyperBevel!")
                                draw_fading_label(context, text=msg, color=[yellow, white], alpha=[1, 0.5])

                        else:

                            get_mouse_pos(self, context, event)

                            hitobj, hitlocation, hitnormal, hitindex, hitdistance, cache = cast_bvh_ray_from_mouse(self.mouse_pos, candidates = [bevel_obj], debug=False)

                            hit_co = mx.inverted_safe() @ hitlocation

                            bm = bmesh.new()
                            bm.from_mesh(bevel_obj.data)
                            bm.normal_update()
                            bm.faces.ensure_lookup_table()

                            vertex_group_layer = bm.verts.layers.deform.verify()
                            edge_glayer = ensure_edge_glayer(bm)

                            hitface = bm.faces[hitindex]

                            gizmo_edges = [e for e in hitface.edges if e[edge_glayer] == 1]

                            if gizmo_edges:

                                edge = min([(e, (hit_co - intersect_point_line(hit_co, e.verts[0].co, e.verts[1].co)[0]).length, (hit_co - get_center_between_verts(*e.verts)).length) for e in gizmo_edges if e.calc_length()], key=lambda x: (x[1] * x[2]) / x[0].calc_length())[0]
                                
                                is_concave = edge.calc_face_angle_signed(1) < 0

                                index = edge.index

                                edge_coords = [mx @ v.co for v in edge.verts]

                                edge_bevel, vgroupname = get_edge_bevel_from_edge(bevel_obj, edge, vertex_group_layer)

                                if edge_bevel:

                                    coords = get_profile_coords_from_spline(spline, flop=is_concave)

                                    create_bevel_profile(edge_bevel, coords)

                                    if bevel_obj.data.users > 1:
                                        instanced_objects = [obj for obj in bpy.data.objects if obj.data == bevel_obj.data and obj != bevel_obj]

                                        for obj in instanced_objects:
                                            mods = [mod for mod in obj.modifiers if is_edge_bevel(mod) and mod.vertex_group == vgroupname]

                                            if mods:
                                                create_bevel_profile(mods[0], coords)

                                    remove_obj(curve)

                                    bpy.ops.object.select_all(action='DESELECT')
                                    bevel_obj.select_set(True)
                                    context.view_layer.objects.active = bevel_obj

                                    bpy.ops.machin3.bevel_edge('INVOKE_DEFAULT', index=index, is_profile_drop=True)

                                    return {'FINISHED'}

                                else:
                                    msg.append("There is no Edge Bevel Modifier close to the dropped location!")

                                    if bevelsCOL:
                                        msg.append("If you want to apply the profile to a HyperBevel, then you need to drop it on the Gizmo!")

                                    draw_fading_label(context, text=msg, color=[yellow, white], alpha=[1, 0.5])

                            else:
                                msg.append("There are no Edges with Gizmos close to the dropped location!")
                                draw_fading_label(context, text=msg, color=[yellow, white], alpha=[1, 0.5])

                    else:
                        msg.append("The Profile needs to have a first point, that is to the left, and above the last point!")
                        draw_fading_label(context, text=msg, color=[yellow, white], alpha=[1, 0.5])

                else:
                    msg.append("The Profile can't be a cyclic Curve!")
                    draw_fading_label(context, text=msg, color=[yellow, white], alpha=[1, 0.5])

                remove_obj(curve)

                return {'CANCELLED'}

            elif hitobj.type == 'CURVE':
                pipe = hitobj

                curve.matrix_world = pipe.matrix_world
                parent(curve, pipe)

                pipe.data.bevel_mode = 'OBJECT'
                pipe.data.bevel_object = curve

                maxdim = max(curve.dimensions)

                if pipe.data.bevel_depth == 0:
                    pipe.data.bevel.depth = 0.0001

                dimdivisor = maxdim / pipe.data.bevel_depth / 2
                curve.dimensions = curve.dimensions / dimdivisor

                context.view_layer.objects.active = pipe
                pipe.select_set(True)

                bpy.ops.machin3.adjust_pipe('INVOKE_DEFAULT', is_profile_drop=True)

                return {'FINISHED'}

        return {'CANCELLED'}
