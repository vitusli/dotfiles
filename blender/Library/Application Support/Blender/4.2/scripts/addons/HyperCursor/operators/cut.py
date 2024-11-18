import bpy
from bpy.props import BoolProperty, FloatProperty, StringProperty
import bmesh
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_line_line, intersect_line_plane, intersect_point_line
from math import degrees, radians
from uuid import uuid4
from .. utils.bmesh import get_tri_coords, ensure_gizmo_layers
from .. utils.draw import draw_point, draw_vector, draw_tris, draw_line, draw_points, draw_lines, draw_init, draw_label
from .. utils.gizmo import hide_gizmos, restore_gizmos
from .. utils.math import dynamic_format, get_center_between_points, get_center_between_verts, average_locations, get_loc_matrix, create_rotation_matrix_from_vectors
from .. utils.math import get_world_space_normal, create_rotation_matrix_from_normal
from .. utils.mesh import get_bbox
from .. utils.modifier import add_solidify, sort_modifiers, add_boolean, move_mod, add_displace
from .. utils.object import enable_auto_smooth, get_eval_bbox, hide_render, parent, get_min_dim
from .. utils.operator import Settings
from .. utils.property import get_biggest_index_among_names
from .. utils.snap import Snap
from .. utils.ui import force_geo_gizmo_update, get_mouse_pos, ignore_events, navigation_passthrough, get_zoom_factor, init_status, finish_status, force_ui_update, is_key, scroll_up, scroll_down, warp_mouse
from .. utils.view import get_view_origin_and_dir
from .. items import ctrl, alt, shift
from .. colors import red, green, blue, yellow, white, normal, orange

def draw_hyper_cut_status(op):
    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)

        depth_limit = dynamic_format(op.limit_depth_factor, decimal_offset=1 if op.is_shift else 0) if 0 < op.limit_depth_factor < 1 else False
        width_limit = dynamic_format(op.limit_width_factor, decimal_offset=1 if op.is_shift else 0) if 0 < op.limit_width_factor < 1 else False

        row.label(text="Hyper Cut")

        if not op.start:
            row.label(text="", icon='MOUSE_LMB_DRAG')
            row.label(text="Start Cut")

        elif op.start and not op.end:
            row.label(text="", icon='MOUSE_LMB_DRAG')
            row.label(text="Draw Out HyperCut")

        else:
            row.label(text="", icon='EVENT_SPACEKEY')
            row.label(text="Finish Cut")

            row.label(text="", icon='MOUSE_LMB')
            row.label(text="Finish Cut and Select Cutter")

        row.label(text="", icon='MOUSE_MMB')
        row.label(text="Viewport")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        if op.is_depth_limiting:
            row.label(text="", icon='MOUSE_MMB')
            row.label(text=f"Depth Limit: {depth_limit}")

        elif op.is_width_limiting:
            row.label(text="", icon='MOUSE_MMB')
            row.label(text=f"Width Limit: {width_limit}")

        else:
            if not op.start:
                row.label(text="", icon='EVENT_ALT')
                row.label(text=f"Draw on BBox: {op.is_bbox}")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_F')
                row.label(text=f"Draw on Face: {op.face_index}")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_C')
                axis = 'X' if op.cursor_x else 'Y' if op.cursor_y else 'Z'
                row.label(text=f"Draw on Cursor: {axis if op.is_cursor else False}")

                if op.is_cursor:
                    row.separator(factor=2)

                    row.label(text="", icon='EVENT_X')
                    row.label(text="", icon='EVENT_Y')
                    row.label(text="", icon='EVENT_Z')
                    row.label(text="Set Cursor Plane")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_V')
                row.label(text="Align View with Draw Plane")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_SHIFT')
                row.label(text="", icon='EVENT_V')
                row.label(text="Align View with inverted Draw Plane")

            if op.start and op.end:
                row.separator(factor=2)

                row.label(text="", icon='EVENT_S')
                row.label(text=f"Split: {op.mode == 'SPLIT'}")

                if op.mode == 'SPLIT':
                    row.separator(factor=1)

                    row.label(text="", icon='EVENT_Q')
                    row.label(text=f"Lazy Split: {op.lazy_split}")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_CTRL')
                row.label(text=f"Snapping: {op.is_snapping}")

                if op.is_snapping:
                    row.separator(factor=1)

                    row.label(text="", icon='EVENT_SHIFT')
                    row.label(text=f"Snap on Others: {op.is_snapping_on_others}")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_F')
                row.label(text="Flip Cut")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_D')
                row.label(text=f"Depth Limit: {depth_limit}")

                row.separator(factor=1)

                row.label(text="", icon='EVENT_W')
                row.label(text=f"Width Limit: {depth_limit}")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_A')
                row.label(text=f"Apply Boolean: {op.apply_boolean}")

                row.separator(factor=1)

                row.label(text="", icon='EVENT_M')
                row.label(text=f"Minimize Cutter: {op.minimize_cutter}")

                if not op.apply_boolean:
                    row.separator(factor=2)

                    row.label(text="", icon='EVENT_TAB')
                    row.label(text=f"Finish + Invoke HyperMod")

    return draw

class HyperCut(bpy.types.Operator, Settings):
    bl_idname = "machin3.hyper_cut"
    bl_label = "MACHIN3: Hyper Cut"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    mode: StringProperty(name="Mode", default='CUT')
    is_bbox: BoolProperty(name="BBox Aligned Cutting", default=False)
    is_cursor: BoolProperty(name="Cursor Algned Cutting", default=False)
    cursor_x: BoolProperty(name="Cursor X Cutting", default=False)
    cursor_y: BoolProperty(name="Cursor Y Cutting", default=True)
    cursor_z: BoolProperty(name="Cursor Z Cutting", default=False)
    flip_width: BoolProperty(name="Flip Cutting Direction", default=False)
    lazy_split: BoolProperty(name="Lazy Split", default=False)
    is_depth_limiting: BoolProperty(name="Limit Depth", default=False)
    limit_depth_factor: FloatProperty(name="Limit Depth Factor", default=0, min=0, max=1)
    is_width_limiting: BoolProperty(name="Limit Width", default=False)
    limit_width_factor: FloatProperty(name="Limit width Factor", default=1, min=0, max=1)
    apply_boolean: BoolProperty(name="Apply Boolean", default=False)
    minimize_cutter: BoolProperty(name="Minimize Cutter", default=False)
    active_cutter: BoolProperty(name="Make Cutter Active", default=False)
    is_tab_finish: BoolProperty(name="is Tab Finish", default=False)

    passthrough = None

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.type == 'MESH'

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)

        row = column.row(align=True)
        row.prop(self, 'apply_boolean', toggle=True)

        if not self.apply_boolean:
            row.prop(self, 'active_cutter', toggle=True)

        row = column.row(align=True)
        row.prop(self, 'minimize_cutter', toggle=True)

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            if self.start:
                dims = draw_label(context, title='Hyper ', coords=Vector((self.HUD_x, self.HUD_y)), center=False, alpha=1)
            else:
                dims = (0, 0)

            if self.start:
                if self.mode == 'SPLIT' and self.lazy_split:
                    title = 'Lazy Split'
                else:
                    title = self.mode.title()
            else:
                title = 'Draw'

            color = green if self.start and self.mode == 'SPLIT' else white
            dims2 = draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=color, alpha=1)

            factor = 0.3 if self.start else 1
            dims3 = draw_label(context, title=" on ", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5 * factor)

            axis = 'X' if self.cursor_x else 'Y' if self.cursor_y else 'Z'
            title = 'BBox' if self.is_bbox else f'Cursor {axis} ' if self.is_cursor else f'Face {self.face_index}'
            color = red if self.is_bbox else green if self.is_cursor else blue
            dims4 = draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, color=color, alpha=factor)

            if self.is_cursor:
                draw_label(context, title="plane", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + dims4[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5 * factor)
            
            if self.start:

                if self.is_snapping:
                    self.offset += 18
                    dims2 = draw_label(context, title='Parallel ', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                    dims2 = draw_label(context, title='Snapping ', coords=Vector((self.HUD_x + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)
                    dims4 = draw_label(context, title='on ', coords=Vector((self.HUD_x + dims2[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

                    if self.snap_target:
                        alpha = 1

                        if self.snap_target == 'EDGE':
                            color = yellow
                            title = 'Edge'
                        
                        elif self.snap_target in ['BBOX', 'CURSOR']:
                            title = 'Border'
                            color = red if self.snap_target == 'BBOX' else green

                    else:
                        title, color, alpha = ('Nothing', white, 0.5)

                    draw_label(context, title=title, coords=Vector((self.HUD_x + dims2[0] + dims2[0] + dims4[0], self.HUD_y)), offset=self.offset, center=False, color=color, alpha=alpha)

                    if self.snap_target == 'EDGE' and self.is_snapping_on_others and self.snap_obj_name:
                        self.offset += 18
                        dims4 = draw_label(context, title="of ", coords=Vector((self.HUD_x + dims2[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                        draw_label(context, title=self.snap_obj_name, coords=Vector((self.HUD_x + dims2[0] + dims2[0] + dims4[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

                if (self.is_width_limiting or 0 < self.limit_width_factor < 1) and not (self.mode == 'SPLIT' and self.lazy_split):
                    self.offset += 18
                    title = 'None' if self.limit_width_factor in [0, 1] else dynamic_format(self.limit_width_factor, decimal_offset=1 if self.is_shift else 0)

                    if 0 < self.limit_width_factor < 1:
                        if self.is_width_limiting:
                            draw_label(context, title=f"Limit Width: {title}", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=orange, alpha=1)

                        else:
                            dims = draw_label(context, title=f"Limit Width: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                            draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

                    else:
                        draw_label(context, title=f"Limit Width: {title}", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.25)

                if self.is_depth_limiting or 0 < self.limit_depth_factor < 1:
                    self.offset += 18
                    title = 'None' if self.limit_depth_factor in [0, 1] else dynamic_format(self.limit_depth_factor, decimal_offset=1 if self.is_shift else 0)

                    if 0 < self.limit_depth_factor < 1:
                        if self.is_depth_limiting:
                            draw_label(context, title=f"Limit Depth: {title}", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=orange, alpha=1)

                        else:
                            dims = draw_label(context, title=f"Limit Depth: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                            draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

                    else:
                        draw_label(context, title=f"Limit Depth: {title}", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.25)

                if self.apply_boolean:
                    self.offset += 18
                    draw_label(context, title='Apply Boolean', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=red, alpha=1)

                else:

                    if self.minimize_cutter:
                        self.offset += 18
                        draw_label(context, title='Minimize Cutter', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=normal, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:

            if self.tri_coords:
                if not self.is_depth_limiting:
                    is_drawing = self.start and self.end

                    if is_drawing:
                        color = white
                        alpha = 0.015 if any([self.is_bbox, self.is_cursor]) else 0.05

                    else:
                        color = red if self.is_bbox else green if self.is_cursor else blue
                        alpha = 0.05 

                    mx = Matrix() if self.is_cursor else self.mx

                    draw_tris(self.tri_coords, mx=mx, color=color, alpha=alpha)

            if len(self.coords) > 1:
                draw_line(self.coords, color=red if self.apply_boolean else green, width=2, alpha=0.5)

            if self.is_cursor:
                axes = [(self.cursor_x_dir, red), (self.cursor_y_dir, green), (self.cursor_z_dir, blue)]
                loc = self.cursor_origin
                scale = 0.5

                for axis, color in axes:
                    coords = [loc + axis * 0.1 * scale, loc + axis * scale]
                    draw_line(coords, color=color, width=2, alpha=1)

            if self.cut_width:
                is_lazy_split = self.mode == 'SPLIT' and self.lazy_split

                if not is_lazy_split:
                    draw_tris(self.width_tri_coords, color=white, alpha=0.02)

                color = red if self.apply_boolean else green

                if self.mode == 'CUT':
                    draw_vector(self.cut_width, origin=self.start, color=color, width=10, alpha=0.1, fade=True)
                    draw_vector(self.cut_width, origin=self.end, color=color, width=10, alpha=0.1, fade=True)
                    draw_vector(self.cut_width, origin=self.mid, color=color, width=10, alpha=0.1, fade=True)
                    draw_vector(self.cut_width, origin=get_center_between_points(self.start, self.mid), color=color, width=10, alpha=0.1, fade=True)
                    draw_vector(self.cut_width, origin=get_center_between_points(self.end, self.mid), color=color, width=10, alpha=0.1, fade=True)

                if self.is_width_limiting and 0 < self.limit_width_factor < 1:
                    draw_vector(self.cut_width, origin=self.start, color=orange, alpha=1)
                    draw_vector(self.cut_width, origin=self.end, color=orange, alpha=1)
                    draw_vector(self.end - self.start, origin=self.start + self.cut_width, color=orange, alpha=1)

                if self.is_depth_limiting or 0 < self.limit_depth_factor < 1:

                    xray = not self.is_depth_limiting

                    if is_lazy_split:
                        color, alpha = (orange, 1) if self.is_depth_limiting else (white, 0.05)

                        draw_lines(self.depth_line_coords[:4], color=color, alpha=alpha, xray=xray)
                        draw_line(self.depth_tri_coords[0:2], color=color, alpha=alpha, xray=xray)

                        if self.is_depth_limiting:
                            tri_coords = [self.depth_line_coords[0], self.depth_line_coords[1], self.depth_line_coords[2],
                                          self.depth_line_coords[1], self.depth_line_coords[2], self.depth_line_coords[3]]

                            draw_tris(tri_coords, color=white, alpha=0.05, xray=False)

                            draw_lines(self.depth_line_coords[:4], color=orange, alpha=0.1, xray=True)
                            draw_line(self.depth_tri_coords[0:2], color=orange, alpha=0.1, xray=True)

                    else:
                        alpha = 0.3 if self.is_depth_limiting else 0.05

                        draw_tris(self.depth_tri_coords, color=white, alpha=alpha / 5, xray=xray)
                        draw_lines(self.depth_line_coords, alpha=alpha, xray=xray)

                        if self.is_depth_limiting and 0 < self.limit_depth_factor < 1: 

                            xray = self.limit_width_factor in [0, 1]

                            line_coords = [self.depth_line_coords[4], self.depth_line_coords[5], self.depth_line_coords[6], self.depth_line_coords[7], self.depth_line_coords[5], self.depth_line_coords[7]]

                            draw_lines(line_coords, color=orange, alpha=1, xray=xray)
                            draw_lines(line_coords, color=orange, alpha=0.1, xray=True)

                            if self.is_cursor:
                                line_coords = [self.depth_line_coords[-2], self.depth_line_coords[-1], self.depth_line_coords[-3], self.depth_line_coords[-4], self.depth_line_coords[-3], self.depth_line_coords[-1]]

                                draw_lines(line_coords, color=orange, alpha=1, xray=xray)
                                draw_lines(line_coords, color=orange, alpha=0.1, xray=True)

            if not self.is_depth_limiting:

                if self.snap_coords:
                    color = yellow if self.snap_target == 'EDGE' else red if self.snap_target == 'BBOX' else green
                    draw_line(self.snap_coords, width=2, color=color, alpha=1)

                    if self.extended_snap_coords:
                        draw_line(self.extended_snap_coords, width=1, color=color, alpha=0.3)

                    if self.connected_snap_coords:
                        draw_lines(self.connected_snap_coords, width=1, color=color, alpha=0.15)

            if self.start:
                draw_point(self.start, color=(1, 1, 1), size=3, alpha=0.5)

            if self.end:
                draw_point(self.end, color=(1, 1, 1), size=3, alpha=0.5)

            if self.is_bbox and self.bbox:
                coords = self.bbox[0]

                indices = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
                draw_lines(coords, indices=indices, mx=self.mx, alpha=0.05)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        self.is_shift = event.shift

        if self.start and self.end:

            if not self.is_width_limiting:

                if is_key(self, event, 'D') and not self.is_depth_limiting:

                    self.init_depth_limiting(context)

                if self.is_depth_limiting and not is_key(self, event, 'D'):
                    self.finish_depth_limiting(context)

                if self.is_depth_limiting:
                    return self.adjust_depth_limit(context, event)

            if not self.is_depth_limiting and not (self.mode == 'SPLIT' and self.lazy_split):

                if is_key(self, event, 'W') and not self.is_width_limiting:
                    self.init_width_limiting(context)

                if self.is_width_limiting and not is_key(self, event, 'W'):
                    self.finish_width_limiting(context)

                if self.is_width_limiting:
                    return self.adjust_width_limit(context, event)

        self.is_snapping = event.ctrl

        if self.is_snapping:
            self.is_snapping_on_others = event.shift

        if self.snap_dir and (not self.is_snapping or event.type in shift):
            self.snap_dir = None
            self.snap_coords = []
            self.extended_snap_coords = []
            self.connected_snap_coords = []

        if not self.start and self.is_bbox:
            self.draw_origin, self.draw_normal = self.set_draw_plane_from_bbox(context)

        if self.passthrough:
            self.passthrough = False

            if self.is_cursor:
                self.update_cursor_plane_size(context)

        events = ['MOUSEMOVE', 'LEFTMOUSE', *ctrl, *alt, *shift, 'F', 'A', 'S', 'C', 'V']

        if self.is_width_limiting or self.is_depth_limiting:
            events.extend(['WHEELUPMOUSE', 'WHEELDOWNMOUSE'])

        if self.is_cursor:
            events.extend(['X', 'Y', 'Z'])

        if not self.apply_boolean:
            events.append('M')

            if self.mode == 'SPLIT':
                events.extend(['L', 'Q'])

        if event.type in events:

            if event.type in ['MOUSEMOVE', 'LEFTMOUSE', *ctrl, *shift]:
                get_mouse_pos(self, context, event)

                view_origin, view_dir = get_view_origin_and_dir(context, self.mouse_pos)

                if not self.start and event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                    self.start = intersect_line_plane(view_origin, view_origin + view_dir, self.draw_origin, self.draw_normal)

                    self.coords = [self.start]

                    force_ui_update(context)

                elif self.start and event.type in ['MOUSEMOVE', *ctrl, *shift] and not self.is_depth_limiting:

                    self.get_end_point(view_origin, view_dir)

                if self.start and self.end:

                    force_ui_update(context)

                    self.coords = [self.start, self.end]

                    self.mid = get_center_between_points(*self.coords)

                    self.cut_vec, self.cut_dir = self.get_cut_vector_and_direction(debug=False)

                    self.cut_width = self.get_width_vector(debug=False)

                    self.cut_depth = self.get_depth_vectors(debug=False)

            if not self.start:

                if event.type == 'F' and event.value == 'PRESS':
                    self.draw_origin, self.draw_normal = self.set_draw_plane_from_face(context)

                    self.is_bbox = False
                    self.is_cursor = False

                elif event.type in alt and event.value == 'PRESS':
                    self.is_bbox = not self.is_bbox

                    if self.is_bbox:
                        if self.is_cursor:
                            self.is_cursor = False

                        self.draw_origin, self.draw_normal = self.set_draw_plane_from_bbox(context)

                    else:
                        self.draw_origin, self.draw_normal = self.set_draw_plane_from_face(context)

                elif event.type == 'C' and event.value == 'PRESS':
                    self.is_cursor = not self.is_cursor

                    if self.is_cursor:
                        if self.is_bbox:
                            self.is_bbox = False

                        self.draw_origin, self.draw_normal = self.set_draw_plane_from_cursor(context)

                    else:
                        self.draw_origin, self.draw_normal = self.set_draw_plane_from_face(context)

                elif self.is_cursor and event.type in ['X', 'Y', 'Z'] and event.value == 'PRESS':

                    if event.type == 'X':
                        self.cursor_x = True
                        self.cursor_y = False
                        self.cursor_z = False

                    elif event.type == 'Y':
                        self.cursor_x = False
                        self.cursor_y = True
                        self.cursor_z = False

                    elif event.type == 'Z':
                        self.cursor_x = False
                        self.cursor_y = False
                        self.cursor_z = True

                    self.draw_origin, self.draw_normal = self.set_draw_plane_from_cursor(context)

                elif event.type  == 'V' and event.value == 'PRESS':

                    if not self.init_viewmx:
                        self.init_viewmx = context.space_data.region_3d.view_matrix.copy()

                    self.align_view_to_draw_plane(context, inverted=event.shift, debug=False)

                    if self.is_cursor:
                        self.update_cursor_plane_size(context)

            elif self.start and self.end:

                if event.type == 'W' and event.value == 'PRESS':
                    self.is_width_limiting = not self.is_width_limiting

                elif event.type == 'S' and event.value == 'PRESS':
                    self.mode = 'SPLIT' if self.mode == 'CUT' else 'CUT'
                    self.cut_width = self.get_width_vector()

                elif event.type == 'F' and event.value == 'PRESS':
                    self.flip_width = not self.flip_width

                    self.cut_dir.negate()
                    self.cut_width = self.get_width_vector()

                elif event.type == 'A' and event.value == 'PRESS':
                    self.apply_boolean = not self.apply_boolean

                    if self.apply_boolean:

                        if self.minimize_cutter:
                            self.minimize_cutter = False

                        if self.lazy_split:
                            self.lazy_split = False

                elif not self.apply_boolean and event.type == 'M' and event.value == 'PRESS':
                    self.minimize_cutter = not self.minimize_cutter

                elif event.type in ['L', 'Q'] and event.value == 'PRESS':
                    self.lazy_split = not self.lazy_split

                force_ui_update(context)

        if navigation_passthrough(event, wheel=False):
            self.passthrough = True

            return {'PASS_THROUGH'}

        elif self.end and event.type in ['SPACE', 'LEFTMOUSE', 'TAB']:
            self.finish(context)

            self.reset_viewmx(context)

            if self.limit_depth_factor == 0:
                self.limit_depth_factor = 1
                self.cut_depth = self.get_depth_vectors(debug=False)

            self.is_tab_finish = event.type == 'TAB'

            self.active_cutter = event.type == 'LEFTMOUSE' and not self.is_tab_finish

            return self.execute(context)

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.finish(context)

            self.reset_viewmx(context)

            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        self.S_on_active.finish()
        self.S_on_others.finish()

        restore_gizmos(self)

        finish_status(self)

        if self.has_switched_to_ortho:
            context.space_data.region_3d.view_perspective = 'PERSP'

    def invoke(self, context, event):
        self.init_settings(props=['apply_boolean'])
        self.load_settings()

        self.active = context.active_object
        self.mx = self.active.matrix_world

        self.bbox = get_bbox(self.active.data)

        if not any(self.bbox[2]):
            self.bbox = get_eval_bbox(self.active, advanced=True)

        mirrors = [mod for mod in self.active.modifiers if mod.type == 'MIRROR' and mod.show_viewport and mod.mirror_object]

        arrays = [mod for mod in self.active.modifiers if mod.type == 'ARRAY' and mod.show_viewport]

        for mod in mirrors + arrays:
            mod.show_viewport= False

        self.dg = context.evaluated_depsgraph_get()
        
        self.bm = bmesh.new()

        mesh_eval = self.active.evaluated_get(self.dg).data
        self.bm.from_mesh(mesh_eval)

        self.bm.normal_update()
        self.bm.verts.ensure_lookup_table()
        self.bm.faces.ensure_lookup_table()

        for mod in mirrors + arrays:
            mod.show_viewport = True

        self.is_shift = False

        self.face_index = None
        self.flip_width = False

        self.is_depth_limiting = False
        self.limit_depth_factor = 0
        self.pre_limit_viewmx = None
        self.pre_limit_mousepos = None

        self.is_width_limiting = False
        self.limit_width_factor = 1

        self.start = None
        self.end = None
        self.mid = None
        self.cut_vec = None
        self.cut_dir = None
        self.cut_width = None
        self.cut_depth = None

        self.coords = []
        self.width_tri_coords = []
        self.depth_tri_coords = []
        self.depth_line_coords = []

        self.init_viewmx = None
        self.has_switched_to_ortho = False

        self.is_snapping = False
        self.is_snapping_on_others = False
        self.snap_target = None
        self.snap_obj_name = ''
        self.snap_dir = None
        self.snap_coords = []
        self.extended_snap_coords = []
        self.connected_snap_coords = []
        
        self.S_on_active = Snap(context, include=[self.active], debug=False)
        self.S_on_others = Snap(context, exclude=[self.active], exclude_wire=True, debug=False)

        self.factor = get_zoom_factor(context, context.scene.cursor.location, scale=300, ignore_obj_scale=True)

        cmx = context.scene.cursor.matrix
        self.cursor_origin, self.cursor_rotation, _ = cmx.decompose()

        self.cursor_x_dir = self.cursor_rotation @ Vector((1, 0, 0)) * self.factor
        self.cursor_y_dir = self.cursor_rotation @ Vector((0, 1, 0)) * self.factor
        self.cursor_z_dir = self.cursor_rotation @ Vector((0, 0, 1)) * self.factor

        hide_gizmos(self, context)

        get_mouse_pos(self, context, event)

        self.init_draw_mode(context, debug=False)

        if self.is_cursor:
            self.draw_origin, self.draw_normal = self.set_draw_plane_from_cursor(context)
        elif self.is_bbox:
            self.draw_origin, self.draw_normal = self.set_draw_plane_from_bbox(context)
        else:
            self.draw_origin, self.draw_normal = self.set_draw_plane_from_face(context)

        init_status(self, context, func=draw_hyper_cut_status(self))

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        active = context.active_object

        cutter, mod = self.cut(context, active, debug=False)

        dg, facecount = self.validate_facecount(context, active, cutter, mod, debug=False)

        if self.minimize_cutter:
            self.minimize(dg, active, cutter, facecount, debug=False)

        if self.mode == 'SPLIT' and not self.lazy_split:
            active_dup, cutter_dup, mod_dup = self.setup_split_boolean(context, active, cutter, mod)

            if not self.apply_boolean:
                names = [mo.name for mo in active.modifiers if mo != mod and mo.type == 'BOOLEAN' and 'Hyper Cut' in mo.name]

                if names:
                    maxidx = get_biggest_index_among_names(names)
                    mod.name = f"Hyper Cut.{str(maxidx + 1).zfill(3)} (Difference)"
                
                names = [mo.name for mo in active_dup.modifiers if mo != mod_dup and mo.type == 'BOOLEAN' and 'Hyper Cut' in mo.name]

                if names:
                    maxidx = get_biggest_index_among_names(names)
                    mod_dup.name = f"Hyper Cut.{str(maxidx + 1).zfill(3)} (Intersect)"

        else:
            active_dup = cutter_dup = mod_dup = None

            if not self.apply_boolean:
                names = [mo.name for mo in active.modifiers if mo != mod and mo.type == 'BOOLEAN' and 'Hyper Cut' in mo.name]

                if names:
                    maxidx = get_biggest_index_among_names(names)
                    mod.name = f"Hyper Cut.{str(maxidx + 1).zfill(3)}"

                    if self.mode == 'SPLIT' and self.lazy_split:
                        mod.name += ' (Lazy Split)'

        bpy.ops.object.select_all(action='DESELECT')

        if self.apply_boolean:
            self.apply_boolean_mod(context, active, cutter, mod, active_dup, mod_dup)

        if self.active_cutter and not self.apply_boolean:

            if self.mode == 'SPLIT' and not self.lazy_split:
                cutter_dup.select_set(True)
                context.view_layer.objects.active = cutter_dup
            else:
                cutter.select_set(True)
                context.view_layer.objects.active = cutter
        else:

            if self.mode == 'SPLIT' and not self.lazy_split:
                active_dup.select_set(True)
                context.view_layer.objects.active = active_dup

            else:
                active.select_set(True)
                context.view_layer.objects.active = active

            if not self.apply_boolean:
                cutter.hide_set(True)

                if self.mode == 'SPLIT' and not self.lazy_split:
                    cutter_dup.hide_set(True)

        force_ui_update(context)

        if self.apply_boolean:
            force_geo_gizmo_update(context)

        self.save_settings()

        if self.is_tab_finish:
            bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')

        return {'FINISHED'}

    def init_draw_mode(self, context, debug=False):
        self.is_cursor = False
        self.is_bbox = False

        lastop = None
        faceindex = False

        ops = context.window_manager.operators

        if ops:
            lastop = ops[-1].bl_idname

        if lastop and any(lastop == bl_idname for bl_idname in ['MACHIN3_OT_transform_cursor']):
            self.is_cursor = True

        else:
            self.S_on_active.get_hit(self.mouse_pos)

            if not self.S_on_active.hit:
                self.is_bbox = True

        if debug:
            print()
            print("cursor:", self.is_cursor)
            print("  bbox:", self.is_bbox)
            print("  face:", faceindex)

    def set_draw_plane_from_face(self, context, debug=False):

        self.S_on_active.get_hit(self.mouse_pos)

        if self.S_on_active.hit:
            face = self.bm.faces[self.S_on_active.hitindex]

        else:
            coords = Vector((context.region.width / 2, context.region.height / 2))
            view_origin, view_dir = get_view_origin_and_dir(context, coords)

            faces = [(f, view_dir.dot(self.mx.to_3x3() @ f.normal), (self.mx @ f.calc_center_median() - view_origin).length) for f in self.bm.faces if view_dir.dot(self.mx.to_3x3() @ f.normal) < -0.5]

            if not faces:
                faces = [(f, view_dir.dot(self.mx.to_3x3() @ f.normal), (self.mx @ f.calc_center_median() - view_origin).length) for f in self.bm.faces]

            face = min(faces, key=lambda x: (x[1], x[2]))[0]

        loop_triangles = self.bm.calc_loop_triangles()
        self.tri_coords = get_tri_coords(loop_triangles, [face])

        origin = self.mx @ face.calc_center_median()

        normal = get_world_space_normal(face.normal, self.mx)

        if debug:
            draw_point(origin, color=yellow, modal=False)
            draw_vector(normal, origin=origin, color=yellow, normal=False, modal=False)

        self.face_index = face.index
        force_ui_update(context)

        return origin, normal

    def set_draw_plane_from_bbox(self, context):
        xmin, xmax, ymin, ymax, zmin, zmax = self.bbox[1]

        faces = [(0, (ymin - ymax).normalized(), ymin),
                 (1, (xmax - xmin).normalized(), xmax),
                 (2, (ymax - ymin).normalized(), ymax),
                 (3, (xmin - xmax).normalized(), xmin),
                 (4, (zmax - zmin).normalized(), zmax),
                 (5, (zmin - zmax).normalized(), zmin)]

        coords = Vector((context.region.width / 2, context.region.height / 2))
        _, view_dir = get_view_origin_and_dir(context, coords)

        index, normal, origin = min(faces, key=lambda x: (view_dir.dot(self.mx.to_3x3() @ x[1]), self.mx @ x[2]))

        face_coords = [(self.bbox[0][0], self.bbox[0][1], self.bbox[0][5], self.bbox[0][4]),
                       (self.bbox[0][1], self.bbox[0][2], self.bbox[0][6], self.bbox[0][5]),
                       (self.bbox[0][2], self.bbox[0][3], self.bbox[0][7], self.bbox[0][6]),
                       (self.bbox[0][3], self.bbox[0][0], self.bbox[0][4], self.bbox[0][7]),
                       (self.bbox[0][4], self.bbox[0][5], self.bbox[0][6], self.bbox[0][7]),
                       (self.bbox[0][0], self.bbox[0][1], self.bbox[0][2], self.bbox[0][3])]

        cos = face_coords[index]
        self.tri_coords = [cos[0], cos[1], cos[2], cos[0], cos[2], cos[3]]

        if self.face_index is not None:
            self.face_index = None
            force_ui_update(context)

        return self.mx @ origin, (self.mx.to_3x3() @ normal).normalized()

    def set_draw_plane_from_cursor(self, context, debug=False):
        loc = self.cursor_origin

        x = self.cursor_x_dir
        y = self.cursor_y_dir
        z = self.cursor_z_dir

        if self.cursor_x:
            draw_normal = x.normalized()
            self.tri_coords = [loc - y - z, loc + y - z, loc + y + z, loc - y - z, loc + y + z, loc - y + z]

        elif self.cursor_y:
            draw_normal = y.normalized()
            self.tri_coords = [loc - x - z, loc + x - z, loc + x + z, loc - x - z, loc + x + z, loc - x + z]

        elif self.cursor_z:
            draw_normal = z.normalized()
            self.tri_coords = [loc - x - y, loc + x - y, loc + x + y, loc - x - y, loc + x + y, loc - x + y]

        if debug:
            draw_vector(draw_normal, origin=loc, color=normal, modal=False)

        self.face_index = None
        force_ui_update(context)

        return loc, draw_normal.normalized()

    def update_cursor_plane_size(self, context):
        context.space_data.region_3d.update()

        self.factor = get_zoom_factor(context, context.scene.cursor.location, scale=300, ignore_obj_scale=True)

        self.cursor_x_dir = self.cursor_rotation @ Vector((1, 0, 0)) * self.factor
        self.cursor_y_dir = self.cursor_rotation @ Vector((0, 1, 0)) * self.factor
        self.cursor_z_dir = self.cursor_rotation @ Vector((0, 0, 1)) * self.factor

        self.draw_origin, self.draw_normal = self.set_draw_plane_from_cursor(context)

    def get_end_point(self, view_origin, view_dir):
        if self.is_snapping:

            if self.snap_dir:
                self.end = self.get_projected_end_point_on_draw_plane(view_origin, view_dir)

            else:

                S = self.S_on_others if self.is_snapping_on_others else self.S_on_active

                S.get_hit(self.mouse_pos)

                if S.hit:

                    self.snap_dir = self.get_snap_dir_from_edge(S)

                    if self.snap_dir:
                        self.end = self.get_projected_end_point_on_draw_plane(view_origin, view_dir)
                        self.snap_target = 'EDGE'

                    else:
                        self.end = intersect_line_plane(view_origin, view_origin + view_dir, self.draw_origin, self.draw_normal)
                        self.snap_target = None

                elif self.is_bbox:
                    self.snap_dir, self.end = self.get_snap_dir_from_bbox_border(view_origin, view_dir)
                    self.snap_target = 'BBOX'

                elif self.is_cursor:
                    self.snap_dir, self.end = self.get_snap_dir_from_cursor_plane_border(view_origin, view_dir)
                    self.snap_target = 'CURSOR'

                else:
                    self.snap_dir = None
                    self.end = intersect_line_plane(view_origin, view_origin + view_dir, self.draw_origin, self.draw_normal)
                    self.snap_target = None

            if self.end and self.snap_coords:
                self.get_additional_snap_coords(self.end)

        else:
            self.end = intersect_line_plane(view_origin, view_origin + view_dir, self.draw_origin, self.draw_normal)
            self.snap_target = None

    def get_cut_vector_and_direction(self, debug=False):

        cut_vec = self.end - self.start

        if debug:
            draw_vector(cut_vec, origin=self.start, color=red, modal=False)

        origin = self.mx.to_translation()

        mid_origin_dir = origin - self.mid
        cross = mid_origin_dir.cross(cut_vec).normalized()

        ortho = cross.cross((cut_vec)).normalized()

        i = intersect_line_plane(self.mid + ortho, self.mid + ortho + self.draw_normal, self.draw_origin, self.draw_normal)

        if i:
            cut_dir = (i - self.mid).normalized()

            if self.flip_width:
                cut_dir.negate()

            return cut_vec, cut_dir

    def get_width_vector(self, debug=False):

        distances = []
        factor = self.limit_width_factor

        for v in self.bm.verts:
            co_world = self.mx @ v.co
            v_dir_world = co_world - self.mid

            if v_dir_world.dot(self.cut_dir) > 0:
                i = intersect_point_line(co_world, self.mid, self.mid + self.cut_dir)[0]
                distances.append((self.mid - i).length)

        if distances:
            max_d = max(distances)
            width = max_d * self.cut_dir * factor

            self.width_tri_coords = [self.start, self.end, self.end + width, self.start, self.end + width, self.start + width]

            if debug:
                draw_vector(width, origin=self.mid, normal=False, modal=False)
            return width

        width = self.cut_dir * 0.02
        self.width_tri_coords = [self.start, self.end, self.end + width, self.start, self.end + width, self.start + width]
        return self.cut_dir * 0.02

    def get_depth_vectors(self, debug=False): 

        distances = [0]
        neg_distances = [0]

        factor = self.limit_depth_factor

        for v in self.bm.verts:
            co_world = self.mx @ v.co
            v_dir_world = co_world - self.mid

            if v_dir_world.dot(- self.draw_normal) > 0:
                i = intersect_point_line(co_world, self.mid, self.mid - self.draw_normal)[0]
                distances.append((self.mid - i).length)

            if self.is_cursor:
                if v_dir_world.dot(self.draw_normal) > 0:
                    i = intersect_point_line(co_world, self.mid, self.mid + self.draw_normal)[0]
                    neg_distances.append((self.mid - i).length)

        if len(distances) < len(neg_distances):
            if debug:
                print("flipping distance lists and draw_normal")

            distances, neg_distances = neg_distances, distances
            self.draw_normal.negate()

        if distances != [0]:
            max_d = max(distances)
            max_neg_d = max(neg_distances)

            depth = max_d * - self.draw_normal * factor
            neg_depth = max_neg_d * self.draw_normal * factor if self.is_cursor else Vector()

            if self.is_depth_limiting or 0 < factor < 1:
                self.depth_tri_coords = [self.start + depth, self.end + depth, self.end + self.cut_width + depth, self.start + depth, self.end + self.cut_width + depth, self.start + self.cut_width + depth]

                line_indices = [0, 1, 2, 5]
                self.depth_line_coords = [coords[idx] for idx in line_indices for coords in [self.width_tri_coords, self.depth_tri_coords]]

                if self.is_cursor:
                    self.depth_tri_coords.extend([self.start + neg_depth, self.end + neg_depth, self.end + self.cut_width + neg_depth, self.start + neg_depth, self.end + self.cut_width + neg_depth, self.start + self.cut_width + neg_depth])

                    for idx in [0, 1, 2, 5]:
                        self.depth_line_coords.append(self.width_tri_coords[idx])
                        self.depth_line_coords.append(self.depth_tri_coords[idx + 6])

            if debug:
                draw_vector(depth, origin=self.mid, color=green, normal=False, modal=False)

                if self.is_cursor:
                    draw_vector(neg_depth, origin=self.mid, color=blue, normal=False, modal=False)

            return depth, neg_depth

        depth = - self.draw_normal
        neg_depth = self.draw_normal
        self.depth_tri_coords = [self.start + depth, self.end + depth, self.end + self.cut_width + depth, self.start + depth, self.end + self.cut_width + depth, self.start + self.cut_width + depth]

        line_indices = [0, 1, 2, 5]
        self.depth_line_coords = [coords[idx] for idx in line_indices for coords in [self.width_tri_coords, self.depth_tri_coords]]

        if self.is_cursor:
            self.depth_tri_coords.extend([self.start + neg_depth, self.end + neg_depth, self.end + self.cut_width + neg_depth, self.start + neg_depth, self.end + self.cut_width + neg_depth, self.start + self.cut_width + neg_depth])

            for idx in [0, 1, 2, 5]:
                self.depth_line_coords.append(self.width_tri_coords[idx])
                self.depth_line_coords.append(self.depth_tri_coords[idx + 6])

        return - self.draw_normal, self.draw_normal

    def get_snap_dir_from_edge(self, SnapObject):
        hitmx = SnapObject.hitmx
        hitobj = SnapObject.hitobj
        hitlocation = SnapObject.hitlocation
        hitindex = SnapObject.hitindex
        bm = SnapObject.cache.bmeshes[hitobj.name]

        hit = hitmx.inverted_safe() @ hitlocation

        hitface = bm.faces[hitindex]

        edge = min([(e, (hit - intersect_point_line(hit, e.verts[0].co, e.verts[1].co)[0]).length, (hit - get_center_between_verts(*e.verts)).length) for e in hitface.edges if e.calc_length()], key=lambda x: (x[1] * x[2]) / x[0].calc_length())[0]

        edge_dir = hitmx.to_3x3() @ (edge.verts[0].co - edge.verts[1].co).normalized()

        if abs(edge_dir.dot(self.draw_normal)) > 0.999:
            self.snap_coords = []
            return None

        else:
            self.snap_coords = [hitmx @ v.co for v in edge.verts]
            self.snap_obj_name = hitobj.name
            return edge_dir

    def get_projected_end_point_on_draw_plane(self, view_origin, view_dir):
        end = intersect_line_plane(view_origin, view_origin + view_dir, self.draw_origin, self.draw_normal)

        snapped = intersect_point_line(end, self.start, self.start + self.snap_dir)[0]

        return intersect_line_plane(snapped, snapped + self.draw_normal, self.draw_origin, self.draw_normal)

    def get_snap_dir_from_bbox_border(self, view_origin, view_dir):
        hit = self.mx.inverted_safe() @ intersect_line_plane(view_origin, view_origin + view_dir, self.draw_origin, self.draw_normal)

        bbox_edges = [(self.tri_coords[0], self.tri_coords[1]), (self.tri_coords[1], self.tri_coords[2]), (self.tri_coords[2], self.tri_coords[5]), (self.tri_coords[5], self.tri_coords[0])]

        edge = min([(e, (hit - intersect_point_line(hit, e[0], e[1])[0]).length, (hit - get_center_between_points(*e)).length) for e in bbox_edges], key=lambda x: (x[1] * x[2]) / (x[0][0] - x[0][1]).length)[0]

        edge_dir = self.mx.to_3x3() @ (edge[0] - edge[1]).normalized()

        self.snap_coords = [self.mx @ co for co in edge]

        end = intersect_line_plane(view_origin, view_origin + view_dir, self.draw_origin, self.draw_normal)

        snapped = intersect_point_line(end, self.start, self.start + edge_dir)[0]

        return edge_dir, snapped

    def get_snap_dir_from_cursor_plane_border(self, view_origin, view_dir):
        hit = intersect_line_plane(view_origin, view_origin + view_dir, self.draw_origin, self.draw_normal)

        cursor_plane_edges = [(self.tri_coords[0], self.tri_coords[1]), (self.tri_coords[1], self.tri_coords[2]), (self.tri_coords[2], self.tri_coords[5]), (self.tri_coords[5], self.tri_coords[0])]

        edge = min([(e, (hit - intersect_point_line(hit, e[0], e[1])[0]).length, (hit - get_center_between_points(*e)).length) for e in cursor_plane_edges], key=lambda x: (x[1] * x[2]) / (x[0][0] - x[0][1]).length)[0]

        edge_dir = (edge[0] - edge[1]).normalized()

        self.snap_coords = edge

        end = intersect_line_plane(view_origin, view_origin + view_dir, self.draw_origin, self.draw_normal)

        snapped = intersect_point_line(end, self.start, self.start + edge_dir)[0]

        return edge_dir, snapped

    def get_additional_snap_coords(self, end):
        projected_snap_co_1 = intersect_line_plane(self.snap_coords[0], self.snap_coords[0] - self.draw_normal, self.draw_origin, self.draw_normal)
        projected_snap_co_2 = intersect_line_plane(self.snap_coords[1], self.snap_coords[1] - self.draw_normal, self.draw_origin, self.draw_normal)

        start_parallel_co = intersect_point_line(self.start, projected_snap_co_1, projected_snap_co_2)[0]
        end_parallel_co = intersect_point_line(end, projected_snap_co_1, projected_snap_co_2)[0]
        
        start_reprojected_co = intersect_line_line(start_parallel_co, start_parallel_co + self.draw_normal, *self.snap_coords)[0]
        end_reprojected_co = intersect_line_line(end_parallel_co, end_parallel_co + self.draw_normal, *self.snap_coords)[0]
        self.connected_snap_coords = [self.start, start_parallel_co, start_parallel_co, start_reprojected_co, end, end_parallel_co, end_parallel_co, end_reprojected_co]

        extended_snap_line_1 = [start_reprojected_co, self.snap_coords[0]]
        extended_snap_line_2 = [start_reprojected_co, self.snap_coords[1]]
        extended_snap_line_5 = [start_reprojected_co, end_reprojected_co]
        extended_snap_line_3 = [end_reprojected_co, self.snap_coords[0]]
        extended_snap_line_4 = [end_reprojected_co, self.snap_coords[1]]

        longest = max([((line[1] - line[0]).length, line) for line in [extended_snap_line_1, extended_snap_line_2, extended_snap_line_3, extended_snap_line_4, extended_snap_line_5]], key=lambda x: x[0])
        self.extended_snap_coords = longest[1]

    def align_view_to_draw_plane(self, context, inverted=False, debug=False):
        normal = - self.draw_normal if inverted else self.draw_normal

        loc = self.draw_origin
        rot = create_rotation_matrix_from_normal(self.active, normal)

        if debug:
            tangent = rot.col[0].xyz
            binormal = rot.col[1].xyz

            draw_point(self.draw_origin, modal=False)

            draw_vector(tangent, origin=self.draw_origin, color=red, modal=False)
            draw_vector(binormal, origin=self.draw_origin, color=green, modal=False)
            draw_vector(normal, origin=self.draw_origin, color=blue, modal=False)

        planemx = Matrix.LocRotScale(loc + normal, rot.to_3x3(), Vector((1, 1, 1)))

        space_data = context.space_data
        r3d = space_data.region_3d

        r3d.view_matrix = planemx.inverted_safe()

        if r3d.view_perspective == 'PERSP':
            r3d.view_perspective = 'ORTHO'

            self.has_switched_to_ortho = True

    def reset_viewmx(self, context):
        viewmx = self.init_viewmx if self.init_viewmx else self.pre_limit_viewmx if self.pre_limit_viewmx else None

        if viewmx:
            context.space_data.region_3d.view_matrix = viewmx

    def init_depth_limiting(self, context, debug=False):

        self.is_depth_limiting = True

        self.pre_limit_mousepos = self.mouse_pos

        if self.limit_depth_factor == 0:
            self.limit_depth_factor = 0.1

        elif self.limit_depth_factor == 1:
            self.limit_depth_factor = 0.9

        self.cut_depth = self.get_depth_vectors(debug=False)

        pre_viewmx = context.space_data.region_3d.view_matrix.copy()

        self.pre_limit_viewmx = pre_viewmx

        pre_origin, pre_rot, _ = pre_viewmx.inverted_safe().decompose()

        pre_x = pre_rot @ Vector((1, 0, 0))
        pre_y = pre_rot @ Vector((0, 1, 0))
        pre_z = pre_rot @ Vector((0, 0, 1))

        if debug:
            draw_point(pre_origin, modal=False)

            draw_vector(pre_x, origin=pre_origin, color=red, modal=False)
            draw_vector(pre_y, origin=pre_origin, color=green, modal=False)
            draw_vector(pre_z, origin=pre_origin, color=blue, modal=False)

            draw_point(self.mid, modal=False)

        view_distance = (pre_origin - self.mid).length

        view_origin = self.mid + (self.cut_width + self.cut_dir * view_distance) + ((self.cut_depth[0] + self.cut_depth[1]) / 2)

        view_z = self.cut_dir

        dot = view_z.dot(pre_x)

        coords = Vector((context.region.width / 2, context.region.height / 2))
        _, view_dir = get_view_origin_and_dir(context, coords)

        draw_normal = -self.draw_normal if view_dir.dot(self.draw_normal) > 0 else self.draw_normal

        up_dot = draw_normal.dot(Vector((0, 0, 1)))

        if abs(up_dot) >= 0.95:

            cut_vec = self.cut_vec.normalized()

            view_x = cut_vec if pre_x.dot(cut_vec) > 0 else -cut_vec

        else:

            view_x = -draw_normal if view_z.dot(pre_x) > 0 else draw_normal

        view_y = view_z.cross(view_x)

        if debug:
            draw_point(view_origin, color=yellow, modal=False)

            draw_vector(view_x, origin=view_origin, color=red, modal=False)
            draw_vector(view_z, origin=view_origin, color=blue, modal=False)

        rot = create_rotation_matrix_from_vectors(view_x, view_y, view_z)

        mx = Matrix.LocRotScale(view_origin, rot.to_3x3(), Vector((1, 1, 1)))

        if not debug:
            context.space_data.region_3d.view_matrix = mx.inverted_safe()

        force_ui_update(context)

    def finish_depth_limiting(self, context):
        self.is_depth_limiting = False

        if self.pre_limit_mousepos:
            warp_mouse(self, context, self.pre_limit_mousepos)
            self.pre_limit_mousepos = None

        if self.pre_limit_viewmx:
            context.space_data.region_3d.view_matrix = self.pre_limit_viewmx
            self.pre_limit_viewmx = None

        force_ui_update(context)

    def adjust_depth_limit(self, context, event):
        if event.type == 'MOUSEMOVE':
            get_mouse_pos(self, context, event)

        elif scroll_up(event, key=True) or scroll_down(event, key=True):
            if scroll_up(event, key=True):
                if round(self.limit_depth_factor, 2) == 1:
                    self.limit_depth_factor = 0.01 if event.shift else 0.1
                else:
                    self.limit_depth_factor += 0.01 if event.shift else 0.1
            else:
                if round(self.limit_depth_factor, 2) == 0:
                    self.limit_depth_factor = 0.99 if event.shift else 0.9
                else:
                    self.limit_depth_factor -= 0.01 if event.shift else 0.1

                self.limit_depth_factor = round(self.limit_depth_factor, 2)

            self.cut_depth = self.get_depth_vectors(debug=False)

            force_ui_update(context)

        if navigation_passthrough(event, wheel=False):
            self.passthrough = True

            return {'PASS_THROUGH'}

        elif event.type in ['SPACE', 'LEFTMOUSE', 'TAB']:
            self.finish(context)

            if self.limit_depth_factor == 0:
                self.limit_depth_factor = 1
                self.cut_depth = self.get_depth_vectors(debug=False)

            self.active_cutter = event.type == 'LEFTMOUSE'

            self.is_tab_finish = event.type == 'TAB'

            return self.execute(context)

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.finish(context)

            self.reset_viewmx(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def init_width_limiting(self, context):
        self.is_width_limiting = True

        self.pre_limit_mousepos = self.mouse_pos

        if self.limit_width_factor == 0:
            self.limit_width_factor = 0.1

        elif self.limit_width_factor == 1:
            self.limit_width_factor = 0.9

        self.cut_width = self.get_width_vector()

        if 0 < self.limit_depth_factor < 1:
            self.cut_depth = self.get_depth_vectors(debug=False)

        force_ui_update(context)

    def finish_width_limiting(self, context):
        self.is_width_limiting = False

        if self.pre_limit_mousepos:
            warp_mouse(self, context, self.pre_limit_mousepos)
            self.pre_limit_mousepos = None

        if self.limit_width_factor == 0:
            self.limit_width_factor = 1

            self.cut_width = self.get_width_vector()

            if 0 < self.limit_depth_factor < 1:
                self.cut_depth = self.get_depth_vectors(debug=False)

        force_ui_update(context)

    def adjust_width_limit(self, context, event):
        if event.type == 'MOUSEMOVE':
            get_mouse_pos(self, context, event)
        
        elif scroll_up(event, key=True) or scroll_down(event, key=True):
            if scroll_up(event, key=True):
                if round(self.limit_width_factor, 2) == 1:
                    self.limit_width_factor = 0.01 if event.shift else 0.1
                else:
                    self.limit_width_factor += 0.01 if event.shift else 0.1
            else:
                if round(self.limit_width_factor, 2) == 0:
                    self.limit_width_factor = 0.99 if event.shift else 0.9
                else:
                    self.limit_width_factor -= 0.01 if event.shift else 0.1

                self.limit_width_factor = round(self.limit_width_factor, 2)

            self.cut_width = self.get_width_vector()

            if 0 < self.limit_depth_factor < 1:
                self.cut_depth = self.get_depth_vectors(debug=False)

            force_ui_update(context)

        if navigation_passthrough(event, wheel=False):
            self.passthrough = True

            return {'PASS_THROUGH'}

        elif event.type in ['SPACE', 'LEFTMOUSE', 'TAB']:
            self.finish(context)

            self.reset_viewmx(context)

            if self.limit_depth_factor == 0:
                self.limit_depth_factor = 1
                self.cut_depth = self.get_depth_vectors(debug=False)

            self.active_cutter = event.type == 'LEFTMOUSE'

            self.is_tab_finish = event.type == 'TAB'

            return self.execute(context)

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.finish(context)

            self.reset_viewmx(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def cut(self, context, active, debug=False):
        def create_cutter(overshoot=0.01):

            vec = self.cut_vec
            start, end = self.start, self.end
            width = self.cut_width

            if debug:
                draw_vector(vec, origin=start, color=yellow, modal=False)
                draw_vector(width, origin=end, color=blue, modal=False)

            if self.mode == 'SPLIT' and not lazy_split:
                width *= 1.005

                overshoot *= 20

            depth, neg_depth = self.cut_depth

            if debug:
                draw_vector(depth, origin=end, color=green, modal=False)
                draw_vector(neg_depth, origin=end, color=red, modal=False)

            if lazy_split:
                world_coords = [start + neg_depth, end + neg_depth,
                                start + depth, end + depth]

            else:
                world_coords = [start + neg_depth, end + neg_depth,
                                start + neg_depth + width, end + neg_depth + width,
                                start + depth, end + depth,
                                start + width + depth, end + width + depth]

            origin = average_locations(world_coords)

            if debug:
                draw_points(world_coords, modal=False)
                draw_point(origin, color=yellow, modal=False)

            axis_x = width.normalized()
            axis_y = vec.normalized()
            axis_z = depth.normalized()

            cross = axis_x.cross(axis_z)

            if cross.dot(axis_y) > 0:
                axis_y = - axis_y

            if debug:
                draw_vector(axis_x, origin=origin, color=red, modal=False)
                draw_vector(axis_y, origin=origin, color=green, modal=False)
                draw_vector(axis_z, origin=origin, color=blue, modal=False)

            loc = get_loc_matrix(origin)
            rot = create_rotation_matrix_from_vectors(axis_x, axis_y, axis_z)

            mx = loc @ rot

            cutter = bpy.data.objects.new(name='Hyper Cut', object_data=bpy.data.meshes.new(name='Hyper Cut'))

            enable_auto_smooth(cutter)

            bpy.context.scene.collection.objects.link(cutter)

            cutter.rotation_mode = 'QUATERNION'
            cutter.matrix_world = mx
            cutter.rotation_mode = 'XYZ'

            bm = bmesh.new()
            bm.from_mesh(cutter.data)

            verts = []

            for co in world_coords:
                verts.append(bm.verts.new(mx.inverted_safe() @ co))

            if lazy_split:
                indices = [0, 1, 3, 2]
                bm.faces.new([verts[i] for i in indices])

                offset = min([vec.length, depth.length]) * overshoot

                depth_dir = (verts[2].co - verts[0].co).normalized()

                for v in verts[0:2]:
                    v.co -= depth_dir * offset

                for v in verts[2:]:
                    v.co += depth_dir * offset

            else:
                indices = [(0, 1, 3, 2), (5, 4, 6, 7),
                           (1, 5, 7, 3), (4, 0, 2, 6),
                           (0, 4, 5, 1), (2, 3, 7, 6)]

                for ids in indices:
                    bm.faces.new([verts[i] for i in ids])

                offset = min([width.length, vec.length, depth.length]) * overshoot

                if self.mode == 'SPLIT':
                    offset *= 1.1

                if offset:
                    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

                    for v in verts:
                        v.co += v.normal * offset

            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

            edge_glayer, face_glayer = ensure_gizmo_layers(bm)

            for e in bm.edges:
                e[edge_glayer] = 1

            for f in bm.faces:
                f[face_glayer] = 1

            bm.to_mesh(cutter.data)
            bm.free()

            cutter.display_type = 'WIRE'
            hide_render(cutter, True)

            cutter.HC.ishyper = True
            cutter.HC.objtype = 'CUBE'

            return cutter

        lazy_split = self.mode == 'SPLIT' and self.lazy_split

        cutter = create_cutter()

        parent(cutter, active)

        mod = add_boolean(active, cutter, method='DIFFERENCE', solver='FAST')
        mod.name = 'Hyper Cut (Lazy Split)' if self.mode == 'SPLIT' and self.lazy_split else 'Hyper Cut'

        if lazy_split:

            min_dim = get_min_dim(self.active)
            thickness = min_dim / 333
            
            add_solidify(cutter, name="Shell", thickness=thickness, offset=0, even=True, high_quality=False)

        sort_modifiers(active, debug=False)

        return cutter, mod

    def validate_facecount(self, context, active, cutter, mod, debug=False):
        dg = context.evaluated_depsgraph_get()

        facecount = len(dg.objects[active.name].data.polygons)

        if debug:
            print("initial face count:", facecount)

        if facecount == 0:
            weld = active.modifiers.new(name='Weld', type='WELD')
            weld.show_expanded = False

            names = [mo.name for mo in active.modifiers if mo != weld and mo.type == 'WELD' and 'Weld' in mo.name]

            if names:
                maxidx = get_biggest_index_among_names(names)
                weld.name = f"- Weld.{str(maxidx + 1).zfill(3)}"
            else:
                weld.name = "- Weld"

            index = list(active.modifiers).index(mod)
            move_mod(weld, index=index)

            dg.update()
            facecount = len(dg.objects[active.name].data.polygons)

            if debug:
                print("initial (welded) face count:", facecount)

        return dg, facecount

    def minimize(self, dg, active, cutter, facecount, debug=False):
        def push_face(first=True, step=0.1, reverse=False, debug=False):
            nonlocal height

            bm = bmesh.new()
            bm.from_mesh(cutter.data)
            bm.normal_update()
            bm.faces.ensure_lookup_table()

            if first:
                face = bm.faces[0]
            else:
                face = bm.faces[1]

            if debug:
                draw_point(face.calc_center_median(), mx=cutter.matrix_world, modal=False)

            for v in face.verts:
                move_edge = [e for e in v.link_edges if e not in face.edges][0]

                if height is None:
                    height = move_edge.calc_length()

                move_dir = (move_edge.other_vert(v).co - v.co).normalized()

                if reverse:
                    move_dir.negate()

                amount = height * step
                v.co = v.co + move_dir * amount

            if debug:
                draw_point(face.calc_center_median(), mx=cutter.matrix_world, color=yellow if reverse else white, modal=False)

            bm.to_mesh(cutter.data)
            bm.free()

        if debug:
            from time import time
            start = time()

        height = None
        step = 0.05

        new_facecount = facecount

        for state in [True, False]:
            if debug:
                print("front face") if state else print("back face")

            count = 0

            while facecount == new_facecount:
                count += 1

                if debug:
                    print(" count", count)

                push_face(first=state, step=step, debug=debug)

                dg.update()

                new_facecount = len(dg.objects[active.name].data.polygons)

                if debug:
                    print("  new face count:", new_facecount)

                if facecount != new_facecount:
                    if debug:
                        print("   reversing once")

                    push_face(first=state, step=step, reverse=True, debug=debug)

                    new_facecount = facecount
                    break
                
                if count >= 19:
                    if debug:
                        print("  aborting and resetting")
                    push_face(first=state, step=0.9, reverse=True, debug=debug)
                    break

        if debug:
            print("time:", time() - start)

    def setup_split_boolean(self, context, active, cutter, mod):
        view = context.space_data
        mod.name = 'Hyper Cut (Split Difference)'

        children = {str(uuid4()): (obj, obj.visible_get()) for obj in active.children_recursive if obj.name in context.view_layer.objects}

        for dup_hash, (obj, vis) in children.items():
            obj.HC.dup_hash = dup_hash

            if not vis:
                if view.local_view and not obj.local_view_get(view):
                    obj.local_view_set(view, True)

            obj.hide_set(False)
            obj.select_set(True)

        bpy.ops.object.duplicate(linked=False)

        active_dup = context.active_object
        mod_dup = active_dup.modifiers.get(mod.name)
        mod_dup.operation = 'INTERSECT'
        mod_dup.name ='Hyper Cut (Split Intersect)'

        dup_children = [obj for obj in active_dup.children_recursive if obj.name in context.view_layer.objects]

        for dup in dup_children:
            orig, vis = children[dup.HC.dup_hash]

            orig.hide_set(not vis)
            dup.hide_set(not vis)

            if orig == cutter:

                dupmesh = dup.data
                dup.data = orig.data

                bpy.data.meshes.remove(dupmesh, do_unlink=False)

                cutter_dup = dup

            orig.HC.dup_hash = ''
            dup.HC.dup_hash = ''

        if not self.apply_boolean:
            cutter = mod_dup.object
            add_displace(cutter, mid_level=0, strength=-self.cut_width.length * 0.005)

        return active_dup, cutter_dup, mod_dup

    def apply_boolean_mod(self, context, active, cutter, mod, active_dup=None, mod_dup=None):
        def process_mesh(obj, redundant_angle=179.999, debug=False):
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.normal_update()

            edge_glayer, face_glayer = ensure_gizmo_layers(bm)

            two_edged_verts = [v for v in bm.verts if len(v.link_edges) == 2]

            redundant_verts = []

            for v in two_edged_verts:
                e1 = v.link_edges[0]
                e2 = v.link_edges[1]

                vector1 = e1.other_vert(v).co - v.co
                vector2 = e2.other_vert(v).co - v.co

                angle = min(degrees(vector1.angle(vector2)), 180)

                if redundant_angle < angle:
                    redundant_verts.append(v)

            if redundant_verts:
                if debug:
                    print(f"INFO: Removing {len(redundant_verts)} redundant vertices")

                bmesh.ops.dissolve_verts(bm, verts=redundant_verts)

            gangle = 20

            for e in bm.edges:
                if len(e.link_faces) == 2:
                    angle = degrees(e.calc_face_angle())
                    e[edge_glayer] = angle >= gangle
                else:
                    e[edge_glayer] = 1

            for f in bm.faces:
                if obj.HC.objtype == 'CYLINDER' and len(f.edges) == 4:
                    f[face_glayer] = 0
                elif not all(e[edge_glayer] for e in f.edges):
                    f[face_glayer] = 0
                else:
                    f[face_glayer] = any([degrees(e.calc_face_angle(0)) >= gangle for e in f.edges])
                
            bm.to_mesh(obj.data)
            bm.free()

        with context.temp_override(object=active):
            bpy.ops.object.modifier_apply(modifier=mod.name, single_user=True)

        if self.mode == 'SPLIT' and not self.lazy_split:
            with context.temp_override(object=active_dup):
                bpy.ops.object.modifier_apply(modifier=mod_dup.name, single_user=True)

        process_mesh(active, debug=True)

        if self.mode == 'SPLIT' and not self.lazy_split:
            process_mesh(active_dup, debug=True)

        bpy.data.meshes.remove(cutter.data, do_unlink=True)
