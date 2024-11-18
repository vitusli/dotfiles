import bpy
from bpy.props import IntProperty, FloatProperty, EnumProperty, BoolProperty, StringProperty
import bmesh
import sys
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_line_line, intersect_line_plane, intersect_point_line
from math import degrees, pi, sin, cos
import numpy as np
from .. utils.draw import draw_point, draw_line, draw_init, draw_label, draw_tris, draw_vector, draw_points, draw_lines, draw_vectors, draw_fading_label
from .. utils.select import get_hyper_face_selection, get_selected_faces, clear_hyper_face_selection
from .. utils.mesh import get_bbox
from .. utils.bmesh import ensure_custom_data_layers, ensure_gizmo_layers, get_tri_coords, get_face_dim
from .. utils.object import get_min_dim, remove_unused_children, set_obj_origin, duplicate_obj_recursively
from .. utils.math import average_normals, get_center_between_verts, average_locations, get_face_center, get_world_space_normal, create_rotation_matrix_from_face, get_center_between_points, dynamic_format, get_sca_matrix
from .. utils.modifier import get_mod_obj, is_array
from .. utils.raycast import cast_bvh_ray
from .. utils.snap import Snap
from .. utils.registration import get_addon, get_prefs
from .. utils.system import printd
from .. utils.operator import Settings
from .. utils.property import rotate_list, step_enum
from .. utils.ui import force_geo_gizmo_update, force_obj_gizmo_update, ignore_events, navigation_passthrough, init_status, finish_status, popup_message, scroll_up, scroll_down, force_ui_update, get_mouse_pos, gizmo_selection_passthrough, get_scale
from .. utils.gizmo import hide_gizmos, restore_gizmos
from .. utils.view import get_view_origin_and_dir
from .. items import push_mode_items, extrude_mode_items, ctrl, shift, alt, numbers, input_mappings
from .. colors import red, green, blue, yellow, white, normal

meshmachine = None

def draw_push_face_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        if op.is_snapping and not op.is_numeric_input:
            if len(op.snap_proximity_coords) == 3:
                row.label(text=f"{op.mode.title()} Face, Snap to Parallel Edge Center")
            else:
                row.label(text=f"{op.mode.title()} Face, Snap to {'Vert' if len(op.snap_coords) == 1 else 'Edge'} by Proximity")
        else:
            row.label(text=f"{op.mode.title()} Face")

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
            row.label(text="Confirm")

            row.label(text="", icon='MOUSE_RMB')
            row.label(text="Cancel")

            row.label(text="", icon='EVENT_TAB')
            row.label(text="Enter Numeric Input")

            row.separator(factor=10)

            if op.mode == 'MOVE':
                row.label(text="", icon='EVENT_ALT')
                row.label(text="Slide Face")

            if not op.is_snapping:
                row.label(text="", icon='EVENT_CTRL')
                row.label(text="Snap")

            if op.can_origin_change:
                row.label(text="", icon='EVENT_C')
                row.label(text=f"Keep Origin Centered: {op.keep_origin_centered}")

    return draw

class PushFace(bpy.types.Operator):
    bl_idname = "machin3.push_face"
    bl_label = "MACHIN3: Push Face"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Face accociated with Gizmo, that is to be moved")
    amount: FloatProperty(name="Amount to Move Face", default=0, unit='LENGTH')
    numeric_amount: StringProperty(name="Input Amount", default="0")
    mode: EnumProperty(name="Push Mode, either Move or Slide", items=push_mode_items, default='MOVE')
    opposite: BoolProperty(default=False)
    keep_origin_centered: BoolProperty(default=True)
    can_origin_change: BoolProperty(default=True)
    is_snapping: BoolProperty()
    is_numeric_input: BoolProperty()

    passthrough = None

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.select_get() and active.HC.ishyper

    @classmethod
    def description(cls, context, properties):
        return f"Push Face {properties.index}\nALT: Repeat Push using previous Amount\nSHIFT: Push Opposite Side too\n\nCTRL: Extrude Face (Quick Access)"

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

        row = column.row(align=True)
        row.prop(self, 'mode', expand=True)

        column.prop(self, 'amount', text="Amount")

        row = column.row(align=True)
        row.prop(self, 'opposite', text="Opposite Side", toggle=True)

        if self.can_origin_change:
            row.prop(self, 'keep_origin_centered', text="Re-Center Origin", toggle=True)

    def draw_HUD(self, context):
        if self.area == context.area:
            draw_init(self)

            dims = draw_label(context, title="Push ", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)
            dims2 = draw_label(context, title=self.mode.title(), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=green if self.mode == 'SLIDE' else yellow, alpha=1)
            dims3 = draw_label(context, title=" Face", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, color=white, alpha=1)

            if self.opposite_verts:
                draw_label(context, title=" + Opposite", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, size=10, color=white, alpha=0.5)

            self.offset += 18

            dims = draw_label(context, title="Amount:", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

            title = "🖩" if self.is_numeric_input else " "
            dims2 = draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset + 3, center=False, size=20, color=green, alpha=0.5)

            if self.is_numeric_input:
                dims3 = draw_label(context, title=self.numeric_amount, coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=green, alpha=1)

                if self.is_numeric_input_marked:
                    scale = get_scale(context)
                    coords = [Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y - (self.offset - 5) * scale, 0)), Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y - (self.offset - 5) * scale, 0))]
                    draw_line(coords, width=12 + 8 * scale, color=green, alpha=0.1, screen=True)

            else:
                draw_label(context, title=dynamic_format(self.amount, decimal_offset=1), coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

            if self.is_snapping and not self.is_numeric_input:
                self.offset += 18
                draw_label(context, title="Snapping", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=red, alpha=1)

            if self.can_origin_change and self.keep_origin_centered:
                self.offset += 18
                draw_label(context, title="Center Origin", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=blue, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:

            draw_vector(self.face_normal * self.min_dim, origin=self.face_origin, fade=True, alpha=0.2)
            draw_vector(-self.face_normal * self.min_dim, origin=self.face_origin, fade=True, alpha=0.2)

            if self.loc and not self.is_numeric_input:
                draw_line([self.init_loc, self.loc], color=(0.5, 0.5, 1), width=2, alpha=0.3)

            if self.can_origin_change and self.keep_origin_centered:
                draw_line([self.origin, self.origin_preview], mx=self.mx, color=blue, alpha=0.5)
                draw_point(self.origin_preview, mx=self.mx, color=blue, alpha=1)

            if self.is_snapping:

                draw_point(self.init_loc, color=(1, 1, 1), alpha=1)

                if len(self.snap_coords) == 2:
                    draw_line(self.snap_coords, color=(1, 0, 0), width=2, alpha=0.75)

                elif len(self.snap_coords) == 1:
                    draw_point(self.snap_coords[0], color=(1, 0, 0), alpha=0.75)

                if self.snap_proximity_coords:

                    if len(self.snap_proximity_coords) == 3:
                        draw_point(self.snap_proximity_coords[0], size=8, color=(1, 0, 0), alpha=0.75)
                        draw_line(self.snap_proximity_coords[1:3], color=(0.5, 1, 0.5), width=1, alpha=0.75)

                    elif len(self.snap_proximity_coords) == 2:
                        draw_line(self.snap_proximity_coords, color=(1, 0.8, 0.3), width=1, alpha=0.75)

                        if len(self.snap_coords) == 2:
                            draw_line([self.snap_coords[0], self.snap_proximity_coords[1]], color=(1, 0, 0), width=2, alpha=0.2)

            if self.push_dirs:
                color = green if self.mode == 'SLIDE' else yellow

                alpha = min(32 / len(self.push_dirs), 1)
                draw_vectors(self.push_dirs, origins=self.push_origins, color=color, alpha=alpha, fade=True)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        if event.type == "TAB" and event.value == 'PRESS':
            self.is_numeric_input = not self.is_numeric_input

            if self.is_numeric_input:
                self.numeric_amount = str(self.amount)
                self.is_numeric_input_marked = True

        if self.is_numeric_input:

            gzm = self.get_gizmo()

            if gzm and gzm.use_draw_modal:
                gzm.use_draw_modal = False

            events = [*numbers, 'BACK_SPACE', 'DELETE', 'PERIOD', 'COMMA', 'MINUS', 'NUMPAD_PERIOD', 'NUMPAD_COMMA', 'NUMPAD_MINUS']

            if event.type in events and event.value == 'PRESS':

                if self.is_numeric_input_marked:
                    self.is_numeric_input_marked = False

                    if event.type == 'BACK_SPACE' and event.alt:
                        self.numeric_amount = self.numeric_amount[:-1]

                    else:
                        self.numeric_amount = input_mappings[event.type]

                else:
                    if event.type in numbers:
                        self.numeric_amount += input_mappings[event.type]

                    elif event.type == 'BACK_SPACE':
                        self.numeric_amount = self.numeric_amount[:-1]

                    elif event.type in ['COMMA', 'PERIOD', 'NUMPAD_COMMA', 'NUMPAD_PERIOD'] and '.' not in self.numeric_amount:
                        self.numeric_amount += '.'

                    elif event.type in ['MINUS', 'NUMPAD_MINUS'] and not self.numeric_amount:
                        self.numeric_amount += '-'

                try:
                    self.amount = float(self.numeric_amount)

                    self.push_move(context) if self.mode == 'MOVE' else self.push_slide(context)

                except:
                    pass

            elif navigation_passthrough(event, alt=True, wheel=True):
                return {'PASS_THROUGH'}

            elif event.type in {'RET', 'NUMPAD_ENTER'}:
                self.finish(context)

                if self.can_origin_change and self.keep_origin_centered:
                    self.change_origin()

                return {'FINISHED'}

            elif event.type in {'ESC'}:
                self.initbm.to_mesh(context.active_object.data)

                self.finish(context)
                return {'CANCELLED'}

            return {'RUNNING_MODAL'}

        else:

            gzm = self.get_gizmo()

            if gzm and not gzm.use_draw_modal:
                gzm.use_draw_modal = True

        self.mode = 'SLIDE' if event.alt else 'MOVE'

        self.is_snapping = event.ctrl

        if self.is_snapping:

            gzm = self.get_gizmo()

            if gzm and gzm.use_draw_modal:
                gzm.use_draw_modal = False

            context.space_data.overlay.show_wireframes = True
            context.space_data.overlay.wireframe_threshold = 1

        elif not self.is_snapping:

            gzm = self.get_gizmo()

            if gzm and not gzm.use_draw_modal:
                gzm.use_draw_modal = True

            self.snap_coords = []
            self.snap_proximity_coords = []

            context.space_data.overlay.show_wireframes = self.show_wires
            context.space_data.overlay.wireframe_threshold = self.wire_threshold

        events = ['MOUSEMOVE', 'C']

        if event.type in events:
            if self.is_snapping:
                self.S.get_hit(self.mouse_pos)

                if self.S.hit:
                    self.snap(context)

                else:
                    self.snap_coords = []
                    self.snap_proximity_coords = []

                force_ui_update(context)

            if event.type == 'MOUSEMOVE':
                get_mouse_pos(self, context, event)

                if not self.is_snapping or not self.S.hit:

                    if self.passthrough:
                        self.passthrough = False

                        loc = self.get_mouse_normal_intersection(context, self.mouse_pos)
                        passthrough_offset = loc - self.loc

                        self.init_loc += passthrough_offset

                    self.loc = self.get_mouse_normal_intersection(context, self.mouse_pos)

                    if self.loc:
                        self.push_vector = (self.loc - self.init_loc)
                        self.amount = self.push_vector.length if self.push_vector.dot(self.face_normal) > 0 else - self.push_vector.length

                        self.push_move(context) if self.mode == 'MOVE' else self.push_slide(context)

            if self.can_origin_change and event.type == 'C' and event.value == 'PRESS':
                self.keep_origin_centered = not self.keep_origin_centered

                context.active_object.select_set(True)

            if self.keep_origin_centered:
                self.origin_preview = average_locations(get_bbox(self.active.data)[0])

        if navigation_passthrough(event):
            self.passthrough = True
            return {'PASS_THROUGH'}

        elif event.type in {'LEFTMOUSE', 'SPACE'}:
            self.finish(context)

            if self.can_origin_change and self.keep_origin_centered:
                self.change_origin()

            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.initbm.to_mesh(context.active_object.data)

            self.finish(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        self.S.finish()

        self.bm.free()
        self.initbm.free()

        finish_status(self)

        if self.has_mods:
            self.active.show_wire = False

        context.space_data.overlay.show_wireframes = self.show_wires
        context.space_data.overlay.wireframe_threshold = self.wire_threshold

        restore_gizmos(self)

        force_geo_gizmo_update(context)

    def invoke(self, context, event):
        if event.ctrl:
            bpy.ops.machin3.extrude_face('INVOKE_DEFAULT', index=self.index)
            return {'FINISHED'}

        self.active = context.active_object
        self.mx = self.active.matrix_world

        self.can_origin_change = (self.active.data.users == 1) and not any((mod.type in ['MIRROR'] and not get_mod_obj(mod)) or ((arr := is_array(mod)) and arr == 'LEGACY_RADIAL') for mod in self.active.modifiers)

        if self.can_origin_change:
            self.origin = self.mx.inverted_safe() @ self.mx.to_translation()
            self.origin_preview = self.origin

        self.has_mods = bool(self.active.modifiers)

        if self.has_mods:
            self.active.show_wire = True

        self.initbm = bmesh.new()
        self.initbm.from_mesh(self.active.data)

        self.bm = bmesh.new()
        self.bm.from_mesh(self.active.data)
        self.bm.normal_update()
        self.bm.faces.ensure_lookup_table()

        self.face = self.bm.faces[self.index]
        self.verts = [(v, v.co.copy()) for v in self.face.verts]
        self.slide_edges = []

        self.opposite = event.shift
        self.opposite_verts = self.get_opposite_side(self.face) if self.opposite else []

        self.face_origin = self.mx @ get_face_center(self.face, method='PROJECTED_BOUNDS')
        self.face_normal = get_world_space_normal(self.face.normal, self.mx)

        if event.alt and self.amount != 0:
            self.push_move(context, repeat=True) if self.mode == 'MOVE' else self.push_slide(context, repeat=True)

            force_ui_update(context)

            if self.can_origin_change and self.keep_origin_centered:

                self.change_origin()

            return {'FINISHED'}

        get_mouse_pos(self, context, event)

        self.init_loc = self.get_mouse_normal_intersection(context, self.mouse_pos)

        if self.init_loc:
            self.loc = self.init_loc

            self.offset_vector = self.init_loc - self.face_origin
            self.push_vector = (self.loc - self.init_loc)

            self.mode = 'SLIDE' if event.ctrl else 'MOVE'

            self.push_dirs = []
            self.push_origins = []

            self.min_dim = get_min_dim(self.active)

            self.S = Snap(context, modifier_toggles=['BOOLEAN'], debug=False)
            self.snap_coords = []
            self.snap_proximity_coords = []
            self.snappable = [obj for obj in context.visible_objects if obj != self.active and obj.display_type != 'WIRE']

            self.show_wires = context.space_data.overlay.show_wireframes
            self.wire_threshold = context.space_data.overlay.wireframe_threshold

            self.is_snapping = False
            self.is_numeric_input = False

            self.gzm_grp = context.gizmo_group

            force_ui_update(context)

            hide_gizmos(self, context, debug=False)

            init_status(self, context, func=draw_push_face_status(self))

            self.area = context.area
            self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
            self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        return {'CANCELLED'}

    def execute(self, context):
        self.active = context.active_object

        self.bm = bmesh.new()
        self.bm.from_mesh(self.active.data)
        self.bm.normal_update()
        self.bm.faces.ensure_lookup_table()

        self.face = self.bm.faces[self.index]
        self.verts = [(v, v.co.copy()) for v in self.face.verts]
        self.slide_edges = []

        self.opposite_verts = self.get_opposite_side(self.face) if self.opposite else []

        self.face_origin = self.mx @ self.face.calc_center_median()
        self.face_normal = get_world_space_normal(self.face.normal, self.mx)

        self.push_move(context, repeat=True) if self.mode == 'MOVE' else self.push_slide(context, repeat=True)

        if self.can_origin_change and self.keep_origin_centered:
            self.change_origin()

        force_ui_update(context)

        return {'FINISHED'}

    def get_mouse_normal_intersection(self, context, mouse_pos):
        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)

        i = intersect_line_line(self.face_origin, self.face_origin + self.face_normal, view_origin, view_origin + view_dir)

        if i:
            return i[0]

    def get_opposite_side(self, face):
        opposite_verts = []

        for f in [f for f in self.bm.faces if f != face]:
            if f.normal.dot(face.normal) < -0.9999:
                opposite_verts.extend([(v, v.co.copy()) for v in f.verts])
        return opposite_verts

    def get_gizmo(self):
        if self.gzm_grp:
            for gzm, normal, gzmtype, index, _, _ in self.gzm_grp.face_gizmos:
                if gzmtype == 'PUSH' and index == self.index:
                    return gzm

    def change_origin(self):
        global meshmachine

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        bbox = get_bbox(self.active.data)[0]
        center = self.mx @ average_locations(bbox)

        _, rot, sca = self.mx.decompose()
        mx = Matrix.LocRotScale(center, rot, sca)

        set_obj_origin(self.active, mx, meshmachine=meshmachine, force_quat_mode=True)

    def push_move(self, context, push_vector=None, repeat=False):
        self.push_dirs = []
        self.push_origins = []

        if not push_vector:

            push_vector = self.face_normal * self.amount if repeat or self.is_numeric_input else self.push_vector

        for v, init_co in self.verts:
            v.co = init_co + self.mx.to_3x3().inverted_safe() @ push_vector

            if not repeat:
                move_dir = push_vector.normalized() * (self.min_dim / 3)
                move_origin = self.mx @ v.co.copy()

                self.push_dirs.append(move_dir)
                self.push_dirs.append(-move_dir)
                self.push_origins.extend([move_origin, move_origin])

        for v, init_co in self.opposite_verts:
            v.co = init_co - self.mx.to_3x3().inverted_safe() @ push_vector

            if not repeat:
                move_dir = push_vector.normalized() * (self.min_dim / 3)
                move_origin = self.mx @ v.co.copy()

                self.push_dirs.append(move_dir)
                self.push_dirs.append(-move_dir)
                self.push_origins.extend([move_origin, move_origin])

        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        self.bm.to_mesh(self.active.data)

    def push_slide(self, context, slide_plane_origin=None, repeat=False):
        self.push_dirs = []
        self.push_origins = []

        if not slide_plane_origin:

            slide_plane_origin = self.face_origin + self.face_normal * self.amount if repeat or self.is_numeric_input else self.loc - self.offset_vector

        slide_edges = []

        for v, init_co in self.verts:

            non_face_edges = [e for e in v.link_edges if e not in self.face.edges]

            if non_face_edges:
                slide_edges.append((v, init_co, non_face_edges[0]))

            else:
                slide_edges.append((v, init_co, None))

        for v, init_co, e in slide_edges:

            if e:
                other_v = e.other_vert(v)

                i = intersect_line_plane(self.mx @ init_co, self.mx @ other_v.co, slide_plane_origin, self.face_normal)

            else:
                i = intersect_line_plane(self.mx @ init_co, self.mx @ (init_co + v.normal), slide_plane_origin, self.face_normal)

            if i:
                v.co = self.mx.inverted_safe() @ i

                if not repeat:
                    if e:
                        slide_dir = self.mx.to_quaternion() @ (other_v.co - init_co).normalized() * (self.min_dim / 3)
                    else:
                        slide_dir = self.mx.to_quaternion() @ v.normal * (self.min_dim / 3)

                    slide_origin = self.mx @ v.co.copy()

                    self.push_dirs.append(slide_dir)
                    self.push_dirs.append(-slide_dir)
                    self.push_origins.extend([slide_origin, slide_origin])

        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        self.bm.to_mesh(context.active_object.data)

    def snap(self, context):
        hitmx = self.S.hitmx
        hit_co = hitmx.inverted_safe() @ self.S.hitlocation
        hitface = self.S.hitface

        edge_weight = 1
        vert_weight = 20

        vert_distance = min([(v, (hit_co - v.co).length / vert_weight) for v in hitface.verts], key=lambda x: x[1])

        edge = min([(e, (hit_co - intersect_point_line(hit_co, e.verts[0].co, e.verts[1].co)[0]).length, (hit_co - get_center_between_verts(*e.verts)).length) for e in hitface.edges if e.calc_length()], key=lambda x: (x[1] * x[2]) / x[0].calc_length())
        edge_distance = (edge[0], ((edge[1] * edge[2]) / edge[0].calc_length()) / edge_weight)

        closest = min([vert_distance, edge_distance], key=lambda x: x[1])

        if isinstance(closest[0], bmesh.types.BMVert):

            vert_co = hitmx @ closest[0].co

            i = intersect_point_line(vert_co, self.face_origin, self.face_origin + self.face_normal)
            loc = i[0]

            self.snap_coords = [vert_co]
            self.snap_proximity_coords = [vert_co, loc]

        elif isinstance(closest[0], bmesh.types.BMEdge):

            edge_dir = hitmx.to_3x3() @ (closest[0].verts[0].co - closest[0].verts[1].co).normalized()
            dot = self.face_normal.dot(edge_dir)

            if abs(round(dot, 6)) == 1:
                edge_center = hitmx @ get_center_between_verts(*closest[0].verts)

                i = intersect_point_line(edge_center, self.face_origin, self.face_origin + self.face_normal)
                loc = i[0]

                self.snap_proximity_coords = [edge_center, edge_center, loc]

            else:
                i = intersect_line_line(self.face_origin, self.face_origin + self.face_normal, hitmx @ closest[0].verts[0].co, hitmx @ closest[0].verts[1].co)
                loc = i[0] if i else None

                self.snap_proximity_coords = [*i] if i else []

            self.snap_coords = [hitmx @ v.co for v in closest[0].verts]

        if loc:

            self.loc = loc

            push_vector = loc - self.face_origin

            self.amount = push_vector.length if push_vector.dot(self.face_normal) > 0 else - push_vector.length

            if self.mode == 'MOVE':
                self.push_move(context, push_vector=push_vector, repeat=False)

            elif self.mode == 'SLIDE':
                self.push_slide(context, slide_plane_origin=loc, repeat=False)

def draw_move_face_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text=f"Move Face")

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
            row.label(text="Confirm")

            row.label(text="", icon='MOUSE_RMB')
            row.label(text="Cancel")

            row.label(text="", icon='EVENT_TAB')
            row.label(text="Enter Numeric Input")

            row.separator(factor=10)

            precision = 2 if op.is_shift else 0 if op.is_ctrl else 1
            row.label(text="", icon='MOUSE_MOVE')
            row.label(text=f"Amount: {dynamic_format(op.amount, decimal_offset=precision)}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_X')
            row.label(text="", icon='EVENT_Y')
            row.label(text="", icon='EVENT_Z')
            row.label(text=f"Move Axis: {'X' if op.move_x else 'Y'}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_F')
            row.label(text="Face Alignment: %s" % ("Edge Pair" if op.face_align_edge_pair else "Longest Edge"))

    return draw

class MoveFace(bpy.types.Operator):
    bl_idname = "machin3.move_face"
    bl_label = "MACHIN3: Move Face"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Face accociated with Gizmo, that is to be moved")
    amount: FloatProperty(name="Amount to Move Face", description="Amount to Move the Face Selection by", default=0)
    is_numeric_input: BoolProperty()
    is_numeric_input_marked: BoolProperty()
    numeric_input_amount: StringProperty(name="Numeric Amount to Move Face", description="Amount to Move the Face Selection by", default='0')
    def update_x_axis(self, context):
        if not self.is_interactive:
            if self.avoid_update:
                self.avoid_update = False
                return

            if self.move_x and self.move_y:
                self.avoid_update = True
                self.move_y = False

            elif not self.move_x and not self.move_y:
                self.avoid_update = True
                self.move_x = True

    def update_y_axis(self, context):
        if not self.is_interactive:
            if self.avoid_update:
                self.avoid_update = False
                return

            if self.move_x and self.move_y:
                self.avoid_update = True
                self.move_x = False

            elif not self.move_x and not self.move_y:
                self.avoid_update = True
                self.move_y = True

    move_x: BoolProperty(name="Move Face Tangent", default=True, description="Move Face on its X Axis", update=update_x_axis)
    move_y: BoolProperty(name="Move Face Binormal", default=False, description="Move Face on its Y Axis", update=update_y_axis)
    opposite: BoolProperty(name="Move the face on the opposite side as well")
    face_align_edge_pair: BoolProperty(name='Align to Face using longest disconnected Edge Pair', default=True)
    passthrough = None
    avoid_update: BoolProperty()
    is_interactive: BoolProperty()

    @classmethod
    def description(cls, context, properties):
        desc = "Move a Face Selection in Face-Space"
        desc += "\nALT: Repeat previous Move"
        desc += "\nSHIFT: Move Opposite Side's Face too"

        return desc

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.select_get() and active.HC.ishyper

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        split = column.split(factor=0.5, align=True)
        split.prop(self, 'amount', text='Amount')

        row = split.row(align=True)
        row.prop(self, 'move_x', text='X', toggle=True)
        row.prop(self, 'move_y', text='Y', toggle=True)

    def draw_HUD(self, context):
        if self.area == context.area:
            draw_init(self)
  
            dims = draw_label(context, title="Move Face ", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)
  
            dims2 = draw_label(context, title="on ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)
            axis, color = ('X ', red) if self.move_x else ('Y ', green)
            dims3 = draw_label(context, title=axis, coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=12, color=color, alpha=1)
  
            if self.is_shift:
                draw_label(context, title="a little", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)
  
            elif self.is_ctrl:
                draw_label(context, title="a lot", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)
  
            self.offset += 18
            dims = draw_label(context, title="Amount:", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
  
            title = "🖩" if self.is_numeric_input else " "
            dims2 = draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset + 3, center=False, size=20, color=green, alpha=0.5)
  
            if self.is_numeric_input:
                dims3 = draw_label(context, title=self.numeric_input_amount, coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=green, alpha=1)

                if self.is_numeric_input_marked:
                    scale = get_scale(context)
                    coords = [Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y - (self.offset - 5) * scale, 0)), Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y - (self.offset - 5) * scale, 0))]
                    draw_line(coords, width=12 + 8 * scale, color=green, alpha=0.1, screen=True)

            else:
                precision = 2 if self.is_shift else 0 if self.is_ctrl else 1
                draw_label(context, title=dynamic_format(self.amount, decimal_offset=precision), coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

            self.offset += 18
            title = 'Edge Pair' if self.face_align_edge_pair else 'Longest Edge'
            draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            move_dir = self.loc - self.init_loc
            loc = self.face_origin + move_dir

            draw_point(self.face_origin, color=yellow)
            draw_point(loc, color=white)

            draw_line([self.face_origin, loc], width=2, alpha=0.3)

            draw_vector(self.tangent * self.face_dim * 0.2, origin=self.face_origin, color=red, width=2, alpha=1 if self.move_x else 0.2)
            draw_vector(self.binormal * self.face_dim * 0.2, origin=self.face_origin, color=green, width=2, alpha=1 if self.move_y else 0.2)

            if self.tri_coords:
                draw_tris(self.tri_coords, color=blue, alpha=0.1)

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
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        finish_status(self)

        clear_hyper_face_selection(context, self.active)

        restore_gizmos(self)
        
        self.is_interactive = False

    def invoke(self, context, event):
        self.is_interactive = True

        self.active = context.active_object
        self.mx = self.active.matrix_world

        self.min_dim = get_min_dim(self.active)

        self.initbm = bmesh.new()
        self.initbm.from_mesh(self.active.data)
        self.initbm.faces.ensure_lookup_table()

        self.cache = {'bmesh': {self.active.name: self.initbm},
                      'bvh': {}}

        face = self.initbm.faces[self.index]
        self.face_origin = self.mx @ get_face_center(face, method='PROJECTED_BOUNDS')
        self.face_normal = get_world_space_normal(face.normal, self.mx)

        self.face_dim = get_face_dim(face, self.mx)

        rotmx = create_rotation_matrix_from_face(context, self.mx, face, edge_pair=self.face_align_edge_pair, align_binormal_with_view=False)
        self.tangent = rotmx.col[0].xyz
        self.binormal = rotmx.col[1].xyz

        if event.alt and self.amount and (self.move_x or self.move_y):
            self.move(interactive=False)
            return {'FINISHED'}

        self.amount = 0
        self.opposite = event.shift

        self.is_shift = False
        self.is_ctrl = False

        self.is_numeric_input = False
        self.is_numeric_input_marked = False
        self.numeric_input_amount = '0'

        self.tri_coords = []

        get_mouse_pos(self, context, event, init_offset=True)

        face_intersection = self.get_index_face_intersection(context, self.mouse_pos - self.mouse_offset, init=True, debug=False)

        self.loc = self.get_move_axis_intersection(context, face_intersection, debug=False)
        self.init_loc = self.loc

        hide_gizmos(self, context)

        init_status(self, context, func=draw_move_face_status(self))

        force_ui_update(context)

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.active = context.active_object
        self.is_interactive = False

        if self.amount and (self.move_x or self.move_y):
            self.move(interactive=False)

            clear_hyper_face_selection(context, self.active)
        
            return {'FINISHED'}
        return {'CANCELLED'}

    def get_index_face_intersection(self, context, mouse_pos, init=False, debug=False):
        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)

        i = intersect_line_plane(view_origin, view_origin + view_dir, self.face_origin, self.face_normal)

        if i: 
            if debug:
                draw_point(i, color=white, modal=False)

            if init:

                if debug:
                    draw_vector(self.tangent, origin=self.face_origin, color=red, modal=False)
                    draw_vector(self.binormal, origin=self.face_origin, color=green, modal=False)

                i_tangent = intersect_point_line(i, self.face_origin, self.face_origin + self.tangent)[0]
                i_binormal = intersect_point_line(i, self.face_origin, self.face_origin + self.binormal)[0]

                distance_tangent = (i_tangent - i).length
                distance_binormal = (i_binormal - i).length

                if distance_tangent <= distance_binormal:
                    self.move_x = True
                    self.move_y = False

                    if debug:
                        print("moving along face tangent x")
                else:
                    self.move_x = False
                    self.move_y = True

                    if debug:
                        print("moving along face binormal y")

            return i

    def get_move_axis_intersection(self, context, loc, debug=False):
        if self.move_x:
            i = intersect_point_line(loc, self.face_origin, self.face_origin + self.tangent)[0]

            if debug:
                draw_point(i, color=red, modal=False)

            return i
        
        elif self.move_y:
            i = intersect_point_line(loc, self.face_origin, self.face_origin + self.binormal)[0]

            if debug:
                draw_point(i, color=green, modal=False)

            return i

    def get_selection(self, bm, index, opposite=False, debug=False):
        index_face = bm.faces[self.index]

        if debug:
            print()
            print("index face:", index_face.index)

        hyper_selected_faces = [f for f in get_hyper_face_selection(bm, debug=False) if f != index_face]

        faces = [index_face] + hyper_selected_faces

        if opposite:
            if debug:
                draw_vector(-self.face_normal, origin=self.face_origin - self.face_normal * self.min_dim * 0.01, color=yellow, fade=True, modal=False)

            hitobj, hitlocation, hitnormal, hitindex, hitdistance, self.cache = cast_bvh_ray(self.face_origin - self.face_normal * self.min_dim * 0.01, -self.face_normal, candidates=[self.active], cache=self.cache, debug=False)

            if hitindex is not None:
                opposite_face = bm.faces[hitindex]

                if opposite_face not in faces:
                    faces.append(opposite_face)

                if debug:
                    draw_point(hitlocation, color=yellow, modal=False)
                    print("opposite face:", opposite_face.index)

        if debug:
            print("hyper selected:", [f.index for f in hyper_selected_faces])

        verts = set(v for f in faces for v in f.verts)

        if debug:
            print("verts:")

            for v in verts:
                print("", v.index)
                draw_point(v.co.copy(), mx=self.mx, color=blue, modal=False)

        return verts, faces

    def numeric_input(self, context, event):
        
        if event.type == "TAB" and event.value == 'PRESS':
            self.is_numeric_input = not self.is_numeric_input

            force_ui_update(context)

            if self.is_numeric_input:
                self.numeric_input_amount = str(self.amount)
                self.is_numeric_input_marked = True

            else:
                return

        if self.is_numeric_input:
            events = [*numbers, 'BACK_SPACE', 'DELETE', 'PERIOD', 'COMMA', 'MINUS', 'NUMPAD_PERIOD', 'NUMPAD_COMMA', 'NUMPAD_MINUS']

            if event.type in events and event.value == 'PRESS':

                if self.is_numeric_input_marked:
                    self.is_numeric_input_marked = False

                    if event.type == 'BACK_SPACE' and event.alt:
                        self.numeric_input_amount = self.numeric_input_amount[:-1]

                    else:
                        self.numeric_input_amount = input_mappings[event.type]

                else:
                    if event.type in numbers:
                        self.numeric_input_amount += input_mappings[event.type]

                    elif event.type == 'BACK_SPACE':
                        self.numeric_input_amount = self.numeric_input_amount[:-1]

                    elif event.type in ['COMMA', 'PERIOD', 'NUMPAD_COMMA', 'NUMPAD_PERIOD'] and '.' not in self.numeric_input_amount:
                        self.numeric_input_amount += '.'

                    elif event.type in ['MINUS', 'NUMPAD_MINUS']:
                        if self.numeric_input_amount.startswith('-'):
                            self.numeric_input_amount = self.numeric_input_amount[1:]

                        else:
                            self.numeric_input_amount = '-' + self.numeric_input_amount

                try:
                    self.amount = float(self.numeric_input_amount)

                except:
                    return {'RUNNING_MODAL'}

                self.move(interactive=False)

            elif navigation_passthrough(event, alt=True, wheel=True):
                return {'PASS_THROUGH'}

            elif event.type in {'RET', 'NUMPAD_ENTER'}:
                self.finish(context)

                return {'FINISHED'}

            elif event.type in {'ESC', 'RIGHTMOUSE'}:
                self.finish(context)

                self.initbm.to_mesh(self.active.data)
                return {'CANCELLED'}

            return {'RUNNING_MODAL'}
            
    def interactive_input(self, context, event):
        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        events = ['MOUSEMOVE', 'X', 'Y', 'Z', 'F', *shift, *ctrl]

        if event.type in events:

            if event.type in ['MOUSEMOVE', *shift, *ctrl]:
                get_mouse_pos(self, context, event)

                face_intersection = self.get_index_face_intersection(context, self.mouse_pos - self.mouse_offset, init=False, debug=False)

                if self.passthrough:
                    self.passthrough = False

                    move_dir = self.loc - self.init_loc

                    self.loc = self.get_move_axis_intersection(context, face_intersection, debug=False)
                    self.init_loc = self.loc - move_dir

                else:
                    self.loc = self.get_move_axis_intersection(context, face_intersection, debug=False)

                self.move()

                force_ui_update(context)

            elif event.type in ['X', 'Y', 'Z'] and event.value == 'PRESS':
                if event.type == 'X':
                    if self.move_x:
                        return {'RUNNING_MODAL'}
                    self.move_x = True
                    self.move_y = False

                else:
                    if self.move_y:
                        return {'RUNNING_MODAL'}
                    self.move_y = True
                    self.move_x = False

                face_intersection = self.get_index_face_intersection(context, self.mouse_pos - self.mouse_offset, init=False, debug=False)
                self.init_loc = self.get_move_axis_intersection(context, face_intersection, debug=False)
                self.loc = self.init_loc

                self.move()

            elif event.type == 'F' and event.value == 'PRESS':
                self.face_align_edge_pair = not self.face_align_edge_pair

                face = self.initbm.faces[self.index]
                rotmx = create_rotation_matrix_from_face(context, self.mx, face, edge_pair=self.face_align_edge_pair, align_binormal_with_view=False)
                self.tangent = rotmx.col[0].xyz
                self.binormal = rotmx.col[1].xyz

                face_intersection = self.get_index_face_intersection(context, self.mouse_pos - self.mouse_offset, init=False, debug=False)
                self.init_loc = self.get_move_axis_intersection(context, face_intersection, debug=False)
                self.loc = self.init_loc

                self.move()

        if navigation_passthrough(event):
            self.passthrough = True
            return {'PASS_THROUGH'}

        elif event.type in ['LEFTMOUSE', 'SPACE'] and event.value == 'PRESS':
            self.finish(context)
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC'] and event.value == 'PRESS':
            self.finish(context)

            self.initbm.to_mesh(self.active.data)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def move(self, interactive=True):
        bm = self.initbm.copy()
        bm.faces.ensure_lookup_table()
        loop_triangles = bm.calc_loop_triangles()

        verts, faces = self.get_selection(bm, self.index, opposite=self.opposite, debug=False)

        if interactive:
            precision = 0.2 if self.is_shift else 5 if self.is_ctrl else 1

            move_dir = self.mx.inverted_safe().to_3x3() @ (self.loc - self.init_loc) * precision

            amount = move_dir.length

            if self.move_x:
                dot = round(move_dir.normalized().dot(self.tangent))

            elif self.move_y:
                dot = round(move_dir.normalized().dot(self.binormal))

            else:
                print("WARNING: No movement axis determined")
                return

            self.amount = amount * dot

        else:
            if self.move_x:
                move_dir = self.tangent * self.amount

            elif self.move_y:
                move_dir = self.binormal * self.amount

        for v in verts:
            v.co += move_dir

        if interactive or self.is_numeric_input:
            self.tri_coords = get_tri_coords(loop_triangles, faces, mx=self.mx)

        bm.to_mesh(self.active.data)
        bm.free()

def draw_scale_face_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text=f"Scale Face")

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
            row.label(text="Confirm")

            row.label(text="", icon='MOUSE_RMB')
            row.label(text="Cancel")

            row.label(text="", icon='EVENT_TAB')
            row.label(text="Enter Numeric Input")

            row.separator(factor=10)

            row.label(text="", icon='EVENT_ALT')
            row.label(text=f"Merge: {op.merge}")

            if not op.merge:
                row.separator(factor=2)

                precision = 2 if op.is_shift else 0 if op.is_ctrl else 1
                row.label(text="", icon='MOUSE_MOVE')
                row.label(text=f"Amount: {dynamic_format(op.amount, decimal_offset=precision)}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_X')
            row.label(text="", icon='EVENT_Y')
            row.label(text="", icon='EVENT_Z')
            row.label(text=f"Scale Ax{'e' if op.scale_x and op.scale_y else 'i'}s: {'XY' if op.scale_x and op.scale_y else 'X' if op.scale_x else 'Y'}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_F')
            row.label(text="Face Alignment: %s" % ("Edge Pair" if op.face_align_edge_pair else "Longest Edge"))

    return draw

class ScaleFace(bpy.types.Operator):
    bl_idname = "machin3.scale_face"
    bl_label = "MACHIN3: Scale Face"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Face accociated with Gizmo, that is to be scaled")
    amount: FloatProperty(name="Amount to Scale Face", default=0)
    is_numeric_input: BoolProperty()
    is_numeric_input_marked: BoolProperty()
    numeric_input_amount: StringProperty(name="Numeric Amount to Move Face", description="Amount to Move the Face Selection by", default='0')
    def update_scale_x(self, context):
        if not self.is_interactive:
            if self.avoid_update:
                self.avoid_update = False
                return

            if not self.scale_x and not self.scale_y:
                self.avoid_update = True
                self.scale_x = True

    def update_scale_y(self, context):
        if not self.is_interactive:
            if self.avoid_update:
                self.avoid_update = False
                return

            if not self.scale_y and not self.scale_x:
                self.avoid_update = True
                self.scale_y = True

    scale_x: BoolProperty(name="Scale Face Tangent", default=True, update=update_scale_x)
    scale_y: BoolProperty(name="Scale Face Binormal", default=True, update=update_scale_y)
    opposite: BoolProperty(name="Scale the face on the opposite side as well")
    face_align_edge_pair: BoolProperty(name='Align to Face using longest disconnected Edge Pair', default=True)
    merge: BoolProperty(name="Merge Face")

    passthrough = None
    avoid_update: BoolProperty()
    is_interactive: BoolProperty()

    @classmethod
    def description(cls, context, properties):
        desc = "Scale a Face Selection in Face-Space"
        desc += "\nALT: Repeat previous Scaling"
        desc += "\nSHIFT: Scale Opposite Side's Face too"

        return desc

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.select_get() and active.HC.ishyper

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

        split = column.split(factor=0.5, align=True)

        row = split.row(align=True)
        row.active = not self.merge
        row.prop(self, 'amount', text='Amount')

        row = split.row(align=True)
        row.prop(self, 'scale_x', text='X', toggle=True)
        row.prop(self, 'scale_y', text='Y', toggle=True)

        row = column.row(align=True)
        row.prop(self, 'merge', text='Merge', toggle=True)

    def draw_HUD(self, context):
        if self.area == context.area:
            draw_init(self)

            title, color = ('Merge ', yellow) if self.merge else ('Scale ', white)
            dims = draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=color, alpha=1)
            dims2 = draw_label(context, title="Face ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=white, alpha=1)
            dims3 = draw_label(context, title="on ", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            if self.scale_x:
                dims4 = draw_label(context, title='X', coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), center=False, size=12, color=red, alpha=1)
            else:
                dims4 = (0, 0)

            if self.scale_y:
                dims5 = draw_label(context, title='Y', coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + dims4[0], self.HUD_y)), center=False, size=12, color=green, alpha=1)
            else:
                dims5 = (0, 0)

            if not self.merge:
                if self.is_shift:
                    draw_label(context, title=" a little", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + dims4[0] + dims5[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

                elif self.is_ctrl:
                    draw_label(context, title=" a lot", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + dims4[0] + dims5[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            if not self.merge:

                self.offset += 18
                dims = draw_label(context, title="Amount:", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
      
                title = "🖩" if self.is_numeric_input else " "
                dims2 = draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset + 3, center=False, size=20, color=green, alpha=0.5)
      
                if self.is_numeric_input:
                    dims3 = draw_label(context, title=self.numeric_input_amount, coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=green, alpha=1)

                    if self.is_numeric_input_marked:
                        scale = get_scale(context)
                        coords = [Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y - (self.offset - 5) * scale, 0)), Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y - (self.offset - 5) * scale, 0))]
                        draw_line(coords, width=12 + 8 * scale, color=green, alpha=0.1, screen=True)

                else:
                    precision = 2 if self.is_shift else 0 if self.is_ctrl else 1
                    draw_label(context, title=dynamic_format(self.amount, decimal_offset=precision), coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

            self.offset += 18
            title = 'Edge Pair' if self.face_align_edge_pair else 'Longest Edge'
            draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            scale_dir = self.loc - self.init_loc
            loc = self.face_origin + scale_dir

            draw_vector(self.init_scale_dir * self.face_dim, origin=self.face_origin, fade=True, alpha=0.2)
            draw_vector(-self.init_scale_dir * self.face_dim, origin=self.face_origin, fade=True, alpha=0.2)

            draw_point(self.face_origin, color=yellow)
            draw_point(self.face_origin + scale_dir, color=white)
            
            color = yellow if self.amount > 0 else normal if self.amount < 0 else white
            draw_line([self.face_origin, self.face_origin + scale_dir], width=2, color=color, alpha=0.5)

            draw_vector(self.tangent * self.face_dim * 0.2, origin=self.face_origin, color=red, width=2, alpha=1 if self.scale_x else 0.2)
            draw_vector(self.binormal * self.face_dim * 0.2, origin=self.face_origin, color=green, width=2, alpha=1 if self.scale_y else 0.2)

            if self.tri_coords:
                draw_tris(self.tri_coords, color=blue, alpha=0.1)

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
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        finish_status(self)

        clear_hyper_face_selection(context, self.active)

        restore_gizmos(self)

        self.is_interactive = False

    def invoke(self, context, event):
        self.is_interactive = True

        self.active = context.active_object
        self.mx = self.active.matrix_world

        self.min_dim = get_min_dim(self.active)

        self.initbm = bmesh.new()
        self.initbm.from_mesh(self.active.data)
        self.initbm.faces.ensure_lookup_table()

        self.cache = {'bmesh': {self.active.name: self.initbm},
                      'bvh': {}}

        face = self.initbm.faces[self.index]
        self.face_origin = self.mx @ get_face_center(face, method='PROJECTED_BOUNDS')
        self.face_normal = get_world_space_normal(face.normal, self.mx)

        self.face_dim = get_face_dim(face, self.mx)

        self.rotmx = create_rotation_matrix_from_face(context, self.mx, face, edge_pair=self.face_align_edge_pair, align_binormal_with_view=False)
        self.tangent = self.rotmx.col[0].xyz
        self.binormal = self.rotmx.col[1].xyz

        if event.alt and self.amount and (self.scale_x or self.scale_y):
            self.scale(interactive=False)
            return {'FINISHED'}

        self.amount = 0
        self.opposite = event.shift

        self.scale_x = True 
        self.scale_y = True

        self.is_shift = False
        self.is_ctrl = False

        self.is_numeric_input = False
        self.is_numeric_input_marked = False
        self.numeric_input_amount = '0'

        self.tri_coords = []

        get_mouse_pos(self, context, event, init_offset=True)

        self.loc = self.get_index_face_intersection(context, self.mouse_pos - self.mouse_offset, init=True, debug=False)
        self.init_loc = self.loc

        hide_gizmos(self, context)

        init_status(self, context, func=draw_scale_face_status(self))

        force_ui_update(context)

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.active = context.active_object

        self.is_interactive = False

        if self.amount and (self.scale_x or self.scale_y):
            self.scale(interactive=False)

            clear_hyper_face_selection(context, self.active)

            return {'FINISHED'}
        return {'CANCELLED'}

    def get_index_face_intersection(self, context, mouse_pos, init=False, debug=False):

        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)

        i = intersect_line_plane(view_origin, view_origin + view_dir, self.face_origin, self.face_normal)

        if i: 
            if debug:
                draw_point(i, color=white, modal=False)

                draw_vector(self.tangent, origin=self.face_origin, color=red, modal=False)
                draw_vector(self.binormal, origin=self.face_origin, color=green, modal=False)

            if init:
                self.init_scale_dir = (i - self.face_origin).normalized()

                if debug:
                    draw_vector(self.init_scale_dir, origin=self.face_origin, fade=True, modal=False)

                if self.active.HC.objtype == 'CUBE':
                    tangent_dot = abs(self.tangent.dot(self.init_scale_dir))
                    binormal_dot = abs(self.binormal.dot(self.init_scale_dir))

                    cutoff = 0.93

                    if tangent_dot < cutoff and binormal_dot < cutoff:
                        self.scale_x = True
                        self.scale_y = True

                    elif tangent_dot > binormal_dot:
                        self.scale_x = True
                        self.scale_y = False

                    else:
                        self.scale_x = False
                        self.scale_y = True

            return i

    def get_init_scale_dir_intersection(self, context, mouse_pos, debug=False):
        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)

        i = intersect_line_line(self.face_origin, self.face_origin + self.init_scale_dir, view_origin, view_origin + view_dir)

        if i:
            if debug:
                draw_point(i[0], color=white, modal=False)

            return i[0]

    def get_selection(self, bm, index, opposite=False, debug=False):
        index_face = bm.faces[self.index]

        if debug:
            print()
            print("index face:", index_face.index)

        hyper_selected_faces = [f for f in get_hyper_face_selection(bm, debug=False) if f != index_face]

        faces = [index_face] + hyper_selected_faces

        if opposite:
            if debug:
                draw_vector(-self.face_normal, origin=self.face_origin - self.face_normal * self.min_dim * 0.01, color=yellow, fade=True, modal=False)

            hitobj, hitlocation, hitnormal, hitindex, hitdistance, self.cache = cast_bvh_ray(self.face_origin - self.face_normal * self.min_dim * 0.01, -self.face_normal, candidates=[self.active], cache=self.cache, debug=False)

            if hitindex is not None:
                opposite_face = bm.faces[hitindex]

                if opposite_face not in faces:
                    faces.append(opposite_face)

                if debug:
                    draw_point(hitlocation, color=yellow, modal=False)
                    print("opposite face:", opposite_face.index)

        if debug:
            print("hyper selected:", [f.index for f in hyper_selected_faces])

        verts = set(v for f in faces for v in f.verts)

        if debug:
            print("verts:")

            for v in verts:
                print("", v.index)
                draw_point(v.co.copy(), mx=self.mx, color=blue, modal=False)

        return verts, faces

    def numeric_input(self, context, event):
        
        if event.type == "TAB" and event.value == 'PRESS':
            self.is_numeric_input = not self.is_numeric_input

            force_ui_update(context)

            if self.is_numeric_input:
                self.numeric_input_amount = str(self.amount)
                self.is_numeric_input_marked = True

            else:
                return

        if self.is_numeric_input:
            events = [*numbers, 'BACK_SPACE', 'DELETE', 'PERIOD', 'COMMA', 'MINUS', 'NUMPAD_PERIOD', 'NUMPAD_COMMA', 'NUMPAD_MINUS']

            if event.type in events and event.value == 'PRESS':

                if self.is_numeric_input_marked:
                    self.is_numeric_input_marked = False

                    if event.type == 'BACK_SPACE' and event.alt:
                        self.numeric_input_amount = self.numeric_input_amount[:-1]

                    else:
                        self.numeric_input_amount = input_mappings[event.type]

                else:
                    if event.type in numbers:
                        self.numeric_input_amount += input_mappings[event.type]

                    elif event.type == 'BACK_SPACE':
                        self.numeric_input_amount = self.numeric_input_amount[:-1]

                    elif event.type in ['COMMA', 'PERIOD', 'NUMPAD_COMMA', 'NUMPAD_PERIOD'] and '.' not in self.numeric_input_amount:
                        self.numeric_input_amount += '.'

                    elif event.type in ['MINUS', 'NUMPAD_MINUS']:
                        if self.numeric_input_amount.startswith('-'):
                            self.numeric_input_amount = self.numeric_input_amount[1:]

                        else:
                            self.numeric_input_amount = '-' + self.numeric_input_amount

                try:
                    self.amount = float(self.numeric_input_amount)

                except:
                    return {'RUNNING_MODAL'}

                self.scale(interactive=False)

            elif navigation_passthrough(event, alt=True, wheel=True):
                return {'PASS_THROUGH'}

            elif event.type in {'RET', 'NUMPAD_ENTER'}:
                self.finish(context)

                return {'FINISHED'}

            elif event.type in {'ESC', 'RIGHTMOUSE'}:
                self.finish(context)

                self.initbm.to_mesh(self.active.data)
                return {'CANCELLED'}

            return {'RUNNING_MODAL'}

    def interactive_input(self, context, event):
        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        self.merge = event.alt

        events = ['MOUSEMOVE', *shift, *ctrl, *alt, 'X', 'Y', 'Z', 'F']

        if event.type in events:

            if event.type in ['MOUSEMOVE', *shift, *ctrl, *alt]:
                get_mouse_pos(self, context, event)

                if self.passthrough:
                    self.passthrough = False

                    scale_dir = self.loc - self.init_loc

                    self.loc = self.get_init_scale_dir_intersection(context, self.mouse_pos - self.mouse_offset)
                    self.init_loc = self.loc - scale_dir

                else:
                    self.loc = self.get_init_scale_dir_intersection(context, self.mouse_pos - self.mouse_offset)

                self.scale()

                force_ui_update(context)

            if event.type in ['X', 'Y', 'Z'] and event.value == 'PRESS':
                if event.type == 'X':

                    if self.scale_x and not self.scale_y:
                        return {'RUNNING_MODAL'}

                    else:
                        self.scale_x = True

                        if self.scale_y and not event.shift:
                            self.scale_y = False

                else:
                    if self.scale_y and not self.scale_x:
                        return {'RUNNING_MODAL'}

                    else:
                        self.scale_y = True

                        if self.scale_x and not event.shift:
                            self.scale_x = False

                self.loc = self.get_init_scale_dir_intersection(context, self.mouse_pos - self.mouse_offset)
                self.init_loc = self.loc

                self.scale()

            elif event.type == 'F' and event.value == 'PRESS':
                self.face_align_edge_pair = not self.face_align_edge_pair

                face = self.initbm.faces[self.index]
                self.rotmx = create_rotation_matrix_from_face(context, self.mx, face, edge_pair=self.face_align_edge_pair, align_binormal_with_view=False)
                self.tangent = self.rotmx.col[0].xyz
                self.binormal = self.rotmx.col[1].xyz

                self.loc = self.get_init_scale_dir_intersection(context, self.mouse_pos - self.mouse_offset)
                self.init_loc = self.loc

                self.scale()

        if navigation_passthrough(event, alt=False):
            self.passthrough = True
            return {'PASS_THROUGH'}

        elif event.type in ['LEFTMOUSE', 'SPACE'] and event.value == 'PRESS':
            self.finish(context)

            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC'] and event.value == 'PRESS':
            self.finish(context)

            self.initbm.to_mesh(self.active.data)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def scale(self, interactive=True):
        bm = self.initbm.copy()
        bm.faces.ensure_lookup_table()
        loop_triangles = bm.calc_loop_triangles()

        verts, faces = self.get_selection(bm, self.index, opposite=self.opposite, debug=False)

        if interactive:
            precision = 0.2 if self.is_shift else 5 if self.is_ctrl else 1

            scale_dir = (self.loc - self.init_loc) * precision
            scale_dir_local = self.mx.inverted_safe().to_3x3() @ scale_dir

            dot = round(scale_dir.normalized().dot(self.init_scale_dir))

            self.amount = (scale_dir.length * dot) / (self.face_dim / 4)

        else:
            pass

        offset_mx = self.mx.inverted_safe() @ Matrix.LocRotScale(self.face_origin, self.rotmx.to_3x3(), Vector((1, 1, 1)))

        if self.merge:
            scale_vector = Vector((int(not self.scale_x), int(not self.scale_y), 1))

        else:
            amount = 1 + self.amount
            scale_vector = Vector((amount if self.scale_x else 1, amount if self.scale_y else 1, 1))

        scale_mx = get_sca_matrix(scale_vector)

        for v in verts:
            v.co = offset_mx @ scale_mx @ offset_mx.inverted_safe() @ v.co

        if interactive or self.is_numeric_input:
            self.tri_coords = get_tri_coords(loop_triangles, faces, mx=self.mx)

        if self.merge:
            bmesh.ops.remove_doubles(bm, verts=list(verts), dist=0.000001)

        bm.to_mesh(self.active.data)
        bm.free()

def draw_inset_face_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text=f"Inset Face")

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
            row.label(text="Confirm")

            row.label(text="", icon='MOUSE_RMB')
            row.label(text="Cancel")

            row.label(text="", icon='EVENT_TAB')
            row.label(text="Enter Numeric Input")

            row.separator(factor=10)

            precision = 2 if op.is_shift else 0 if op.is_ctrl else 1
            row.label(text="", icon='MOUSE_MOVE')
            row.label(text=f"Amount: {dynamic_format(op.amount, decimal_offset=precision)}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_E')
            row.label(text=f"Even Offset: {op.even_offset}")

            if op.has_neighbouring_faces:
                row.separator(factor=2)

                row.label(text="", icon='EVENT_D')
                row.label(text=f"Individual: {op.individual}")

            if not (op.has_neighbouring_faces and op.individual):
                row.separator(factor=2)

                row.label(text="", icon='EVENT_A')
                row.label(text=f"Auto Outset: {op.auto_outset}")

                if op.has_neighbouring_faces or op.use_outset:
                    row.separator(factor=2)

                    row.label(text="", icon='EVENT_R')
                    row.label(text=f"Edge Rail: {op.edge_rail}")

    return draw

class InsetFace(bpy.types.Operator):
    bl_idname = "machin3.inset_face"
    bl_label = "MACHIN3: Inset Face"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Face accociated with Gizmo, that is to be inset")
    amount: FloatProperty(name="Amount to Inset Face", default=0)
    is_numeric_input: BoolProperty()
    is_numeric_input_marked: BoolProperty()
    numeric_input_amount: StringProperty(name="Numeric Amount to Move Face", description="Amount to Move the Face Selection by", default='0')
    auto_outset: BoolProperty(name="Auto Outset", default=True)
    opposite: BoolProperty(name="Inset the face on the opposite side as well")

    even_offset: BoolProperty(name="Even Offset", default=True)
    edge_rail: BoolProperty(name="Edge Rail", default=True)
    individual: BoolProperty(name="Individual", default=False)
    passthrough = None

    @classmethod
    def description(cls, context, properties):
        desc = "Inset a Face Selection"
        desc += "\nALT: Repeat previous Inset"
        desc += "\nSHIFT: Inset Opposite Side's Face too"

        return desc

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.select_get() and active.HC.ishyper

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

        split = column.split(factor=0.5, align=True)
        split.prop(self, 'amount', text='Amount')

        row = split.row(align=True)
        row.prop(self, 'even_offset', text='Even Offset', toggle=True)

        if self.has_neighbouring_faces:
            row.prop(self, 'individual', text='Individual', toggle=True)

        row = column.row(align=True)
        row.active = not (self.has_neighbouring_faces and self.individual)

        row.prop(self, 'auto_outset', text='Auto Outset', toggle=True)

        if self.has_neighbouring_faces or self.use_outset:
            row.prop(self, 'edge_rail', text='Edge Rail', toggle=True)

    def draw_HUD(self, context):
        if self.area == context.area:
            draw_init(self)

            title, color = ('Outset ', red) if self.use_outset else ('Inset ', blue)
            dims = draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=color, alpha=1)
            dims2 = draw_label(context, title="Face", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=white, alpha=1)

            if self.is_shift:
                draw_label(context, title=" a little", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            elif self.is_ctrl:
                draw_label(context, title=" a lot", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            self.offset += 18
            dims = draw_label(context, title="Amount:", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
  
            title = "🖩" if self.is_numeric_input else " "
            dims2 = draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset + 3, center=False, size=20, color=green, alpha=0.5)
  
            if self.is_numeric_input:
                dims3 = draw_label(context, title=self.numeric_input_amount, coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=green, alpha=1)

                if self.is_numeric_input_marked:
                    scale = get_scale(context)
                    coords = [Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y - (self.offset - 5) * scale, 0)), Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y - (self.offset - 5) * scale, 0))]
                    draw_line(coords, width=12 + 8 * scale, color=green, alpha=0.1, screen=True)

            else:
                precision = 2 if self.is_shift else 0 if self.is_ctrl else 1
                draw_label(context, title=dynamic_format(self.amount, decimal_offset=precision), coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

            if self.has_neighbouring_faces and self.individual:
                self.offset += 18
                draw_label(context, title='Individual', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=blue, alpha=1)

            if self.even_offset:
                self.offset += 18
                draw_label(context, title='Even Offset', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)
            
            if not (self.has_neighbouring_faces and self.individual):

                if self.auto_outset:
                    self.offset += 18
                    draw_label(context, title='Auto Outset', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=red, alpha=1)

                if self.has_neighbouring_faces or self.use_outset:
                    if self.edge_rail:
                        self.offset += 18
                        draw_label(context, title='Edge Rail', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=green, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            inset_dir = self.loc - self.init_loc
            loc = self.face_origin + inset_dir

            draw_vector(self.init_inset_dir * self.face_dim, origin=self.face_origin, fade=True, alpha=0.2)
            draw_vector(-self.init_inset_dir * self.face_dim, origin=self.face_origin, fade=True, alpha=0.2)

            draw_point(self.face_origin, color=yellow)
            draw_point(self.face_origin + inset_dir, color=white)
            
            color = yellow if self.amount > 0 else normal if self.amount < 0 else white
            draw_line([self.face_origin, self.face_origin + inset_dir], width=2, color=color, alpha=0.5)

            color = red if self.use_outset else blue

            if self.tri_coords:
                draw_tris(self.tri_coords, color=color, alpha=0.1)

            if self.edge_coords:
                draw_lines(self.edge_coords, mx=self.mx, color=color, alpha=0.5)

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
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        finish_status(self)

        clear_hyper_face_selection(context, self.active)

        restore_gizmos(self)

    def invoke(self, context, event):
        self.active = context.active_object
        self.mx = self.active.matrix_world

        scale_mx = get_sca_matrix(self.mx.decompose()[2])
        self.min_dim = get_min_dim(self.active)

        self.initbm = bmesh.new()
        self.initbm.from_mesh(self.active.data)
        self.initbm.faces.ensure_lookup_table()

        self.cache = {'bmesh': {self.active.name: self.initbm},
                      'bvh': {}}

        face = self.initbm.faces[self.index]
        self.face_origin = self.mx @ get_face_center(face, method='PROJECTED_BOUNDS')
        self.face_normal = get_world_space_normal(face.normal, self.mx)

        self.face_dim = get_face_dim(face, self.mx)

        if event.alt and self.amount:

            self.get_selection(self.initbm, self.index, opposite=self.opposite, init=True, debug=False)

            self.inset(interactive=False)
            return {'FINISHED'}

        self.amount = 0
        self.opposite = event.shift

        self.is_shift = False
        self.is_ctrl = False

        self.is_numeric_input = False
        self.is_numeric_input_marked = False
        self.numeric_input_amount = '0'

        self.tri_coords = []
        self.edge_coords = []

        self.get_selection(self.initbm, self.index, opposite=self.opposite, init=True, debug=False)

        self.use_outset = False

        get_mouse_pos(self, context, event, init_offset=True)

        self.loc = self.get_index_face_intersection(context, self.mouse_pos - self.mouse_offset, init=True, debug=False)
        self.init_loc = self.loc

        hide_gizmos(self, context)

        init_status(self, context, func=draw_inset_face_status(self))

        force_ui_update(context)

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.active = context.active_object

        if self.amount:
            self.inset(interactive=False)

            clear_hyper_face_selection(context, self.active)

            return {'FINISHED'}
        
        return {'FINISHED'}

    def get_index_face_intersection(self, context, mouse_pos, init=False, debug=False):
        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)

        i = intersect_line_plane(view_origin, view_origin + view_dir, self.face_origin, self.face_normal)

        if i: 
            if debug:
                draw_point(i, color=white, modal=False)

            if init:
                self.init_inset_dir = (i - self.face_origin).normalized()

                if debug:
                    draw_vector(self.init_inset_dir, origin=self.face_origin, fade=True, modal=False)

            return i

    def get_init_scale_dir_intersection(self, context, mouse_pos, debug=False):
        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)

        i = intersect_line_line(self.face_origin, self.face_origin + self.init_inset_dir, view_origin, view_origin + view_dir)

        if i:
            if debug:
                draw_point(i[0], color=white, modal=False)

            return i[0]

    def get_selection(self, bm, index, opposite=False, init=False, debug=False):
        index_face = bm.faces[self.index]

        if debug:
            print()
            print("index face:", index_face.index)

        hyper_selected_faces = [f for f in get_hyper_face_selection(bm, debug=False) if f != index_face]

        faces = [index_face] + hyper_selected_faces

        if opposite:
            if debug:
                draw_vector(-self.face_normal, origin=self.face_origin - self.face_normal * self.min_dim * 0.01, color=yellow, fade=True, modal=False)

            hitobj, hitlocation, hitnormal, hitindex, hitdistance, self.cache = cast_bvh_ray(self.face_origin - self.face_normal * self.min_dim * 0.01, -self.face_normal, candidates=[self.active], cache=self.cache, debug=False)

            if hitindex is not None:
                opposite_face = bm.faces[hitindex]

                if opposite_face not in faces:
                    faces.append(opposite_face)

                if debug:
                    draw_point(hitlocation, color=yellow, modal=False)
                    print("opposite face:", opposite_face.index)

        verts = set(v for f in faces for v in f.verts)

        if debug:
            print("hyper selected:", [f.index for f in hyper_selected_faces])

        if init:
            self.has_neighbouring_faces = any(e for f in faces for e in f.edges if all(ef in faces for ef in e.link_faces))

            if debug:
                print("has neighboring faces:", self.has_neighbouring_faces)

        return verts, faces

    def get_coords(self, bm, extruded_edges, extruded_faces, faces, interactive=True):
        if interactive or self.is_numeric_input:
            loop_triangles = bm.calc_loop_triangles()

            self.tri_coords = get_tri_coords(loop_triangles, extruded_faces if self.use_outset else faces, mx=self.mx)

            self.edge_coords = [v.co.copy() for e in extruded_edges for v in e.verts]

    def numeric_input(self, context, event):
        
        if event.type == "TAB" and event.value == 'PRESS':
            self.is_numeric_input = not self.is_numeric_input

            force_ui_update(context)

            if self.is_numeric_input:
                self.numeric_input_amount = str(self.amount)
                self.is_numeric_input_marked = True

            else:
                return

        if self.is_numeric_input:
            events = [*numbers, 'BACK_SPACE', 'DELETE', 'PERIOD', 'COMMA', 'MINUS', 'NUMPAD_PERIOD', 'NUMPAD_COMMA', 'NUMPAD_MINUS']

            if event.type in events and event.value == 'PRESS':

                if self.is_numeric_input_marked:
                    self.is_numeric_input_marked = False

                    if event.type == 'BACK_SPACE' and event.alt:
                        self.numeric_input_amount = self.numeric_input_amount[:-1]

                    else:
                        self.numeric_input_amount = input_mappings[event.type]

                else:
                    if event.type in numbers:
                        self.numeric_input_amount += input_mappings[event.type]

                    elif event.type == 'BACK_SPACE':
                        self.numeric_input_amount = self.numeric_input_amount[:-1]

                    elif event.type in ['COMMA', 'PERIOD', 'NUMPAD_COMMA', 'NUMPAD_PERIOD'] and '.' not in self.numeric_input_amount:
                        self.numeric_input_amount += '.'

                    elif event.type in ['MINUS', 'NUMPAD_MINUS']:
                        if self.numeric_input_amount.startswith('-'):
                            self.numeric_input_amount = self.numeric_input_amount[1:]

                        else:
                            self.numeric_input_amount = '-' + self.numeric_input_amount

                try:
                    self.amount = float(self.numeric_input_amount)

                except:
                    return {'RUNNING_MODAL'}

                self.inset(interactive=False)

            elif navigation_passthrough(event, alt=True, wheel=True):
                return {'PASS_THROUGH'}

            elif event.type in {'RET', 'NUMPAD_ENTER'}:
                self.finish(context)

                return {'FINISHED'}

            elif event.type in {'ESC', 'RIGHTMOUSE'}:
                self.finish(context)

                self.initbm.to_mesh(self.active.data)
                return {'CANCELLED'}

            return {'RUNNING_MODAL'}

    def interactive_input(self, context, event):
        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        events = ['MOUSEMOVE', *shift, *ctrl, 'E']

        if self.has_neighbouring_faces:
            events.extend(['D', 'I'])

        if not (self.has_neighbouring_faces and self.individual):
            events.append('A')

            if self.has_neighbouring_faces or self.use_outset:
                events.append('R')

        if event.type in events:

            if event.type in ['MOUSEMOVE', *shift, *ctrl]:
                get_mouse_pos(self, context, event)

                if self.passthrough:
                    self.passthrough = False

                    inset_dir = self.loc - self.init_loc

                    self.loc = self.get_init_scale_dir_intersection(context, self.mouse_pos - self.mouse_offset)
                    self.init_loc = self.loc - inset_dir

                else:
                    self.loc = self.get_init_scale_dir_intersection(context, self.mouse_pos - self.mouse_offset)

                self.inset()

                force_ui_update(context)

            elif event.type in ['A', 'E', 'R', 'D', 'I'] and event.value == 'PRESS':

                if event.type == 'A':
                    self.auto_outset = not self.auto_outset

                elif event.type == 'E':
                    self.even_offset = not self.even_offset

                elif event.type == 'R':
                    self.edge_rail = not self.edge_rail

                elif event.type in ['D', 'I']:
                    self.individual = not self.individual

                self.inset()

        if navigation_passthrough(event, alt=False):
            self.passthrough = True
            return {'PASS_THROUGH'}

        elif event.type in ['LEFTMOUSE', 'SPACE'] and event.value == 'PRESS':
            self.finish(context)

            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC'] and event.value == 'PRESS':
            self.finish(context)

            self.initbm.to_mesh(self.active.data)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def inset(self, interactive=True):
        bm = self.initbm.copy()
        bm.faces.ensure_lookup_table()

        edge_glayer, face_glayer = ensure_gizmo_layers(bm)
        vert_vg_layer, edge_bw_layer, edge_crease_layer = ensure_custom_data_layers(bm)

        verts, faces = self.get_selection(bm, self.index, opposite=self.opposite, debug=False)

        gizmo_verts = [v for v in verts if len(v.link_edges) == 3 and all(e[edge_glayer] == 1 for e in v.link_edges)]

        if interactive:
            precision = 0.2 if self.is_shift else 5 if self.is_ctrl else 1

            inset_dir = (self.loc - self.init_loc) * precision
            inset_dir_local = self.mx.inverted_safe().to_3x3() @ inset_dir

            dot = round(inset_dir.normalized().dot(self.init_inset_dir))

            self.amount = inset_dir_local.length * dot

        if self.has_neighbouring_faces and self.individual:
            self.use_outset = False

            thickness = -self.amount

            ret = bmesh.ops.inset_individual(bm, faces=faces, thickness=thickness, depth=0, use_even_offset=self.even_offset, use_interpolate=False, use_relative_offset=False)

        else:

            self.use_outset = self.amount > 0 if self.auto_outset else False

            thickness = self.amount if self.use_outset else -self.amount

            ret = bmesh.ops.inset_region(bm, faces=faces, use_boundary=True, use_even_offset=self.even_offset, use_interpolate=False, use_relative_offset=False, use_edge_rail=self.edge_rail, thickness=thickness, depth=0, use_outset=self.use_outset)

        extruded_edges, extruded_faces = self.process_mesh(bm, gizmo_verts, faces, ret, edge_glayer, face_glayer, vert_vg_layer, edge_bw_layer, edge_crease_layer)

        self.get_coords(bm, extruded_edges, extruded_faces, faces, interactive=interactive)

        bm.to_mesh(self.active.data)
        bm.free()

    def process_mesh(self, bm, gizmo_verts, faces, ret, edge_glayer, face_glayer, vert_vg_layer, edge_bw_layer, edge_crease_layer):
        extruded_faces = faces + ret['faces']
        extruded_edges = set(e for f in extruded_faces for e in f.edges)
        extruded_verts = set(v for f in extruded_faces for v in f.verts)

        inner_verts = set(v for f in faces for v in f.verts)
        outer_verts = extruded_verts - inner_verts

        inner_edges = set(e for f in faces for e in f.edges if not all([ef in faces for ef in e.link_faces]))
        outer_edges = set(e for f in extruded_faces for e in f.edges if not all([ef in extruded_faces for ef in e.link_faces]))

        if self.active.HC.objtype == 'CUBE':
            for e in extruded_edges:
                e[edge_glayer] = 1

        elif self.active.HC.objtype == 'CYLINDER':
            for f in [f for f in ret['faces'] if f not in faces]:
                f[face_glayer] = 0

            for v in gizmo_verts:
                for e in v.link_edges:
                    e[edge_glayer] = 1

        clear_verts = outer_verts if self.use_outset else inner_verts

        for v in clear_verts:
            v[vert_vg_layer].clear()
        
        clear_edges = outer_edges if self.use_outset else inner_edges

        for e in clear_edges:
            e[edge_bw_layer] = 0
            e[edge_crease_layer] = 0
            e.seam = False
            e.smooth = True

        return extruded_edges, extruded_faces

def draw_extrude_face_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text=f"Extrude Face")

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
            row.label(text="Confirm")

            row.label(text="", icon='MOUSE_RMB')
            row.label(text="Cancel")

            row.label(text="", icon='EVENT_TAB')
            row.label(text="Enter Numeric Input")

            row.separator(factor=10)

            precision = 2 if op.is_shift else 0 if op.is_ctrl else 1

            row.label(text="", icon='MOUSE_MOVE')
            row.label(text=f"Amount: {dynamic_format(op.amount, decimal_offset=precision)}")

            row.separator(factor=10)

            if not op.has_neighbouring_faces:
                row.label(text="Individual: True")

            else:
                row.label(text="", icon='MOUSE_MMB')
                row.label(text=f"Mode: {op.mode.title()}")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_D')
                row.label(text=f"Individual: {op.individual}")

    return draw

class ExtrudeFace(bpy.types.Operator):
    bl_idname = "machin3.extrude_face"
    bl_label = "MACHIN3: Extrude Face"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Face accociated with Gizmo, that is to be extruded")
    amount: FloatProperty(name="Amount to Extrude Face", default=0)
    mode: EnumProperty(name="Extrude Mode", items=extrude_mode_items, default='SELECTED')
    is_numeric_input: BoolProperty()
    is_numeric_input_marked: BoolProperty()
    numeric_input_amount: StringProperty(name="Numeric Amount to Move Face", description="Amount to Move the Face Selection by", default='0')
    opposite: BoolProperty(name="Extrude the face on the opposite side as well")
    individual: BoolProperty(name="Individual", default=False)
    passthrough = None

    @classmethod
    def description(cls, context, properties):
        desc = "Inset a Face Selection"
        desc += "\nALT: Repeat previous Inset"
        desc += "\nSHIFT: Inset Opposite Side's Face too"

        return desc

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.select_get() and active.HC.ishyper

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

        if self.has_neighbouring_faces:
            row = column.row(align=True)
            row.prop(self, 'amount', text='Amount')
            row.prop(self, 'individual', text='Individual', toggle=True)

            row = column.row(align=True)
            row.prop(self, 'mode', expand=True)

        else:
            column.prop(self, 'amount', text='Amount')

    def draw_HUD(self, context):
        if self.area == context.area:
            draw_init(self)

            dims = draw_label(context, title="Extude Face", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

            if self.is_shift:
                draw_label(context, title=" a little", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            elif self.is_ctrl:
                draw_label(context, title=" a lot", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            if not self.individual:

                self.offset += 18
                dims = draw_label(context, title="Mode: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

                for idx, mode in enumerate(extrude_mode_items):
                    if idx > 0:
                        self.offset += 18

                    color = green if self.mode == 'SELECTED' else blue if self.mode == 'AVERAGED' else normal if self.mode == 'VERT' else yellow
                    is_selected_mode = mode[0] == self.mode

                    draw_label(context, title=mode[1], coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=color if is_selected_mode else white, alpha=1 if is_selected_mode else 0.5)

            self.offset += 18
            dims = draw_label(context, title="Amount:", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
  
            title = "🖩" if self.is_numeric_input else " "
            dims2 = draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset + 3, center=False, size=20, color=green, alpha=0.5)
  
            if self.is_numeric_input:
                dims3 = draw_label(context, title=self.numeric_input_amount, coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=green, alpha=1)

                if self.is_numeric_input_marked:
                    scale = get_scale(context)
                    coords = [Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y - (self.offset - 5) * scale, 0)), Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y - (self.offset - 5) * scale, 0))]
                    draw_line(coords, width=12 + 8 * scale, color=green, alpha=0.1, screen=True)

            else:
                precision = 2 if self.is_shift else 0 if self.is_ctrl else 1
                draw_label(context, title=dynamic_format(self.amount, decimal_offset=precision), coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

            if self.individual:
                self.offset += 18
                draw_label(context, title='Individual', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=blue, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            extrude_dir = self.loc - self.init_loc
            loc = self.face_origin + extrude_dir

            draw_vector(self.face_normal * self.face_dim, origin=self.face_origin, fade=True, alpha=0.2)
            draw_vector(-self.face_normal * self.face_dim, origin=self.face_origin, fade=True, alpha=0.2)

            draw_point(self.face_origin, color=yellow)
            draw_point(self.face_origin + extrude_dir, color=white)
            
            color = green if self.amount > 0 else red if self.amount < 0 else white
            draw_line([self.face_origin, self.face_origin + extrude_dir], width=2, color=color, alpha=0.5)

            color = blue if (self.individual or self.mode == 'AVERAGED') else green if self.mode == 'SELECTED' else normal

            if self.tri_coords:
                draw_tris(self.tri_coords, color=color, alpha=0.1)

            if self.edge_coords:
                draw_lines(self.edge_coords, mx=self.mx, color=color, alpha=0.5)

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
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        finish_status(self)

        clear_hyper_face_selection(context, self.active)

        restore_gizmos(self)

    def invoke(self, context, event):
        self.active = context.active_object
        self.mx = self.active.matrix_world

        self.min_dim = get_min_dim(self.active)

        self.initbm = bmesh.new()
        self.initbm.from_mesh(self.active.data)
        self.initbm.faces.ensure_lookup_table()

        self.cache = {'bmesh': {self.active.name: self.initbm},
                      'bvh': {}}

        face = self.initbm.faces[self.index]
        self.face_origin = self.mx @ get_face_center(face, method='PROJECTED_BOUNDS')
        self.face_normal = get_world_space_normal(face.normal, self.mx)

        self.face_dim = get_face_dim(face, self.mx)

        if event.alt and self.amount:

            self.get_selection(self.initbm, self.index, opposite=self.opposite, init=True, debug=False)

            self.extrude(interactive=False)
            return {'FINISHED'}

        self.amount = 0
        self.opposite = event.shift

        self.is_shift = False
        self.is_ctrl = False

        self.is_numeric_input = False
        self.is_numeric_input_marked = False
        self.numeric_input_amount = '0'

        self.tri_coords = []
        self.edge_coords = []

        self.get_selection(self.initbm, self.index, opposite=self.opposite, init=True, debug=False)

        self.individual = not self.has_neighbouring_faces

        get_mouse_pos(self, context, event, init_offset=True)

        self.loc = self.get_index_face_normal_intersection(context, self.mouse_pos - self.mouse_offset, debug=False)
        self.init_loc = self.loc

        hide_gizmos(self, context)

        init_status(self, context, func=draw_extrude_face_status(self))

        force_ui_update(context)

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.active = context.active_object

        if self.amount:
            self.extrude(interactive=False)

            clear_hyper_face_selection(context, self.active)

            return {'FINISHED'}
        
        return {'FINISHED'}

    def get_index_face_normal_intersection(self, context, mouse_pos, debug=False):
        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)

        i = intersect_line_line(self.face_origin, self.face_origin + self.face_normal, view_origin, view_origin + view_dir)

        if i: 
            if debug:
                draw_point(i[0], color=white, modal=False)

            return i[0]

    def get_selection(self, bm, index, opposite=False, init=False, debug=False):
        index_face = bm.faces[self.index]

        if debug:
            print()
            print("index face:", index_face.index)

        hyper_selected_faces = [f for f in get_hyper_face_selection(bm, debug=False) if f != index_face]

        faces = [index_face] + hyper_selected_faces

        if opposite:
            if debug:
                draw_vector(-self.face_normal, origin=self.face_origin - self.face_normal * self.min_dim * 0.01, color=yellow, fade=True, modal=False)

            hitobj, hitlocation, hitnormal, hitindex, hitdistance, self.cache = cast_bvh_ray(self.face_origin - self.face_normal * self.min_dim * 0.01, -self.face_normal, candidates=[self.active], cache=self.cache, debug=False)

            if hitindex is not None:
                opposite_face = bm.faces[hitindex]

                if opposite_face not in faces:
                    faces.append(opposite_face)

                if debug:
                    draw_point(hitlocation, color=yellow, modal=False)
                    print("opposite face:", opposite_face.index)

        verts = [v for f in faces for v in f.verts]

        if debug:
            print("hyper selected:", [f.index for f in hyper_selected_faces])

        if init:
            self.has_neighbouring_faces = any(e.is_manifold for f in faces for e in f.edges if all(ef in faces for ef in e.link_faces))

            if debug:
                print("has neighboring faces:", self.has_neighbouring_faces)

        return verts, faces

    def get_vert_data(self, verts, faces, debug=False):
        data = {}

        avg_normal = average_normals([f.normal for f in faces])

        for v in set(verts):
            vert_data = {'SELECTED': average_normals([f.normal for f in v.link_faces if f in faces]),
                         'AVERAGED': avg_normal,
                         'VERT': v.normal.copy(),
                         'SHELL': v.calc_shell_factor()}

            data[v] = vert_data

            if debug:
                draw_vector(data['SELECTED'], origin=v.co.copy(), mx=self.mx, color=green, modal=False)
                draw_vector(data['AVERAGED'], origin=v.co.copy(), mx=self.mx, color=blue, modal=False)
                draw_vector(data['VERT'], origin=v.co.copy(), mx=self.mx, color=normal, modal=False)

        if debug:
            printd(data)

        return data

    def get_coords(self, bm, extruded_edges, faces, interactive=True):
        if interactive or self.is_numeric_input:

            loop_triangles = bm.calc_loop_triangles()

            self.tri_coords = get_tri_coords(loop_triangles, faces, mx=self.mx)

            self.edge_coords = [v.co.copy() for e in extruded_edges for v in e.verts]

    def numeric_input(self, context, event):
        
        if event.type == "TAB" and event.value == 'PRESS':
            self.is_numeric_input = not self.is_numeric_input

            force_ui_update(context)

            if self.is_numeric_input:
                self.numeric_input_amount = str(self.amount)
                self.is_numeric_input_marked = True

            else:
                return

        if self.is_numeric_input:
            events = [*numbers, 'BACK_SPACE', 'DELETE', 'PERIOD', 'COMMA', 'MINUS', 'NUMPAD_PERIOD', 'NUMPAD_COMMA', 'NUMPAD_MINUS']

            if event.type in events and event.value == 'PRESS':

                if self.is_numeric_input_marked:
                    self.is_numeric_input_marked = False

                    if event.type == 'BACK_SPACE' and event.alt:
                        self.numeric_input_amount = self.numeric_input_amount[:-1]

                    else:
                        self.numeric_input_amount = input_mappings[event.type]

                else:
                    if event.type in numbers:
                        self.numeric_input_amount += input_mappings[event.type]

                    elif event.type == 'BACK_SPACE':
                        self.numeric_input_amount = self.numeric_input_amount[:-1]

                    elif event.type in ['COMMA', 'PERIOD', 'NUMPAD_COMMA', 'NUMPAD_PERIOD'] and '.' not in self.numeric_input_amount:
                        self.numeric_input_amount += '.'

                    elif event.type in ['MINUS', 'NUMPAD_MINUS']:
                        if self.numeric_input_amount.startswith('-'):
                            self.numeric_input_amount = self.numeric_input_amount[1:]

                        else:
                            self.numeric_input_amount = '-' + self.numeric_input_amount

                try:
                    self.amount = float(self.numeric_input_amount)

                except:
                    return {'RUNNING_MODAL'}

                self.extrude(interactive=False)

            elif navigation_passthrough(event, alt=True, wheel=True):
                return {'PASS_THROUGH'}

            elif event.type in {'RET', 'NUMPAD_ENTER'}:
                self.finish(context)

                return {'FINISHED'}

            elif event.type in {'ESC', 'RIGHTMOUSE'}:
                self.finish(context)

                self.initbm.to_mesh(self.active.data)
                return {'CANCELLED'}

            return {'RUNNING_MODAL'}

    def interactive_input(self, context, event):
        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        events = ['MOUSEMOVE', *shift, *ctrl, 'E']

        if self.has_neighbouring_faces:
            events.extend(['D', 'I'])

        if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):

            if event.type in ['MOUSEMOVE', *shift, *ctrl]:
                get_mouse_pos(self, context, event)

                if self.passthrough:
                    self.passthrough = False

                    extrude_dir = self.loc - self.init_loc

                    self.loc = self.get_index_face_normal_intersection(context, self.mouse_pos - self.mouse_offset, debug=False)
                    self.init_loc = self.loc - extrude_dir

                else:
                    self.loc = self.get_index_face_normal_intersection(context, self.mouse_pos - self.mouse_offset, debug=False)

                self.extrude()

                force_ui_update(context)

            elif not self.individual and (scroll_up(event, key=True) or scroll_down(event, key=True)):

                if scroll_up(event, key=True):
                    self.mode = step_enum(self.mode, extrude_mode_items, -1, loop=True)

                else:
                    self.mode = step_enum(self.mode, extrude_mode_items, 1, loop=True)

                self.extrude()

            elif event.type in ['D', 'I'] and event.value == 'PRESS':
                self.individual = not self.individual

                self.extrude()

        if navigation_passthrough(event, alt=False):
            self.passthrough = True
            return {'PASS_THROUGH'}

        elif event.type in ['LEFTMOUSE', 'SPACE'] and event.value == 'PRESS':
            self.finish(context)

            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC'] and event.value == 'PRESS':
            self.finish(context)

            self.initbm.to_mesh(self.active.data)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def extrude(self, interactive=True):
        bm = self.initbm.copy()
        bm.faces.ensure_lookup_table()

        edge_glayer, face_glayer = ensure_gizmo_layers(bm)
        vert_vg_layer, edge_bw_layer, edge_crease_layer = ensure_custom_data_layers(bm)

        verts, faces = self.get_selection(bm, self.index, opposite=self.opposite, debug=False)

        data = self.get_vert_data(verts, faces, debug=False)

        gizmo_verts = [v for v in verts if len(v.link_edges) == 3 and all(e[edge_glayer] == 1 for e in v.link_edges)]

        if interactive:
            precision = 0.2 if self.is_shift else 5 if self.is_ctrl else 1

            extrude_dir = (self.loc - self.init_loc) * precision
            extrude_dir_local = self.mx.inverted_safe().to_3x3() @ extrude_dir

            dot = round(extrude_dir.normalized().dot(self.face_normal))

            self.amount = extrude_dir_local.length * dot

        if (self.has_neighbouring_faces and self.individual) or not self.has_neighbouring_faces:
            ret = bmesh.ops.inset_individual(bm, faces=faces, thickness=0, depth=self.amount, use_even_offset=False, use_interpolate=False, use_relative_offset=False)

        else:
            ret = bmesh.ops.inset_region(bm, faces=faces, use_boundary=True, use_even_offset=False, use_interpolate=False, use_relative_offset=False, use_edge_rail=False, thickness=0, depth=0, use_outset=False)

            vert_map = {v_post: v_pre for v_pre, v_post in zip(verts, [v for f in faces for v in f.verts])}

            max_shell_factor = max(d['SHELL'] for d in data.values())

            for v, v_pre in vert_map.items():
                if self.mode == 'SELECTED':
                    v.co += data[v_pre]['SELECTED'] * self.amount

                elif self.mode == 'AVERAGED':
                    v.co += data[v_pre]['AVERAGED'] * self.amount

                elif self.mode == 'VERT':
                    v.co += data[v_pre]['VERT'] * self.amount * (data[v_pre]['SHELL'] / max_shell_factor)

        extruded_edges = self.process_mesh(bm, gizmo_verts, faces, ret, edge_glayer, face_glayer, vert_vg_layer, edge_bw_layer, edge_crease_layer)

        self.get_coords(bm, extruded_edges, faces, interactive=interactive)

        bm.to_mesh(self.active.data)
        bm.free()

    def process_mesh(self, bm, gizmo_verts, faces, ret, edge_glayer, face_glayer, vert_vg_layer, edge_bw_layer, edge_crease_layer):
        extruded_faces = faces + ret['faces']
        extruded_edges = set(e for f in extruded_faces for e in f.edges)
        extruded_verts = set(v for f in extruded_faces for v in f.verts)

        inner_verts = set(v for f in faces for v in f.verts)
        outer_verts = extruded_verts - inner_verts

        inner_edges = set(e for f in faces for e in f.edges if not all([ef in faces for ef in e.link_faces]))
        outer_edges = set(e for f in extruded_faces for e in f.edges if not all([ef in extruded_faces for ef in e.link_faces]))

        if self.active.HC.objtype == 'CUBE':
            for e in extruded_edges:
                e[edge_glayer] = 1

        elif self.active.HC.objtype == 'CYLINDER':
            for f in [f for f in ret['faces'] if f not in faces]:
                f[face_glayer] = 0

            for v in gizmo_verts:
                for e in v.link_edges:
                    e[edge_glayer] = 1

        for v in outer_verts:
            v[vert_vg_layer].clear()
        
        for e in outer_edges:
            e[edge_bw_layer] = 0
            e[edge_crease_layer] = 0
            e.seam = False
            e.smooth = True

        return extruded_edges

def draw_extract_face_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text=f"{'Keep' if op.keep else 'Extract'} Evaluated Faces")

        if op.selected:
            row.label(text="", icon='EVENT_SPACEKEY')
            row.label(text="Confirm")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text="", icon='EVENT_Q')
        row.label(text="Toggle Extraction Mode")

        if not op.is_shift:
            row.separator(factor=2)

            row.label(text="", icon='MOUSE_LMB_DRAG')
            row.label(text="Circle Select")

            row.label(text="", icon='MOUSE_MMB')
            row.label(text="Change Selection Size")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_O')
            row.label(text="Select Outwards-Facing")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_SHIFT')
        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Fill Select")

        row.separator(factor=2)

        if op.is_shift:
            row.label(text="", icon='MOUSE_MMB')
            row.label(text=f"Fill Angle: {op.fill_angle}")

        if op.selected:
            row.separator(factor=2)

            row.label(text="", icon='EVENT_CTRL')
            row.label(text=f"Deselect: {op.is_ctrl}")

            if not op.is_shift:
                row.separator(factor=2)

                row.label(text="", icon='EVENT_A')
                row.label(text="Deselect All")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_C')
        row.label(text=f"Center Origin: {op.center_origin}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_B')
        row.label(text=f"Backface Culling: {op.backface_cull}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_SHIFT')
        row.label(text="", icon='EVENT_F')
        row.label(text="Focus in Obj")

        if not op.is_shift:

            row.separator(factor=2)

            row.label(text="", icon='EVENT_F')
            row.label(text="Focus on Mouse")

    return draw

class ExtractFace(bpy.types.Operator, Settings):
    bl_idname = "machin3.extract_face"
    bl_label = "MACHIN3: Extract Face"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Face accociated with Gizmo, that is to be extracted")

    keep: BoolProperty(name="Keep (only) the Selection instead of Extracting it", default=False)
    evaluated: BoolProperty(name="Extract from Evaluate Mesh", default=False)
    selection_radius: IntProperty(name="Selection Radius", default=20, min=5)
    fill_angle: IntProperty(name="Fill Selection Angle", default=20)
    backface_cull: BoolProperty(name="Backface Culling", default=True)
    center_origin: BoolProperty(name="Center the Origin", default=True)
    passthrough = None

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.select_get() and active.HC.ishyper

    @classmethod
    def description(cls, context, properties):
        desc = "Extract selected Faces"
        desc += "\nCTRL: Keep only selected Faces"

        desc += "\n\nALT: Evaluated Face Extraction"
        return desc

    def draw_HUD(self, context):
        if context.area == self.area:

            draw_init(self)

            title = 'Keep' if self.keep else 'Extract'
            color = green if self.keep else red 

            dims = draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), center=False, size=12, color=color)
            dims2 = draw_label(context, title=" Evaluated Faces ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=12)
            draw_label(context, title="De-Select" if self.is_ctrl else "Select", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, alpha=0.5)

            if self.selected and self.center_origin:
                self.offset += 18
                dims = draw_label(context, title="Center Origin", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, size=12, color=blue)

            if self.backface_cull:
                self.offset += 18
                dims = draw_label(context, title="Backface Culling", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, size=12, color=yellow)

            if self.is_shift:
                self.offset += 18
                dims = draw_label(context, title="Fill ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, size=12, color=red if self.is_ctrl else green)

                dims2 = draw_label(context, title="Angle: ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=12, color=white, alpha=0.5)
                draw_label(context, title=str(self.fill_angle), coords=Vector((self.HUD_x + dims[0] +dims2[0], self.HUD_y)), offset=self.offset, center=False, size=12, color=white, alpha=1)

            if self.is_shift:
                draw_point(self.mouse_pos.resized(3), color=red if self.is_ctrl else green, size=6, screen=True)

            else:
                draw_point(self.mouse_pos.resized(3), color=yellow, size=3, screen=True)

                color = white if self.hit_any else red

                if self.ray_origins:

                    if not self.is_click:
                        draw_points(self.ray_origins, size=2, color=white, alpha=0.2, screen=True)

                if self.circle_coords:
                    draw_line(self.circle_coords, color=color, alpha=0.6 if self.is_click else 0.1, screen=True)

                if self.is_ctrl:
                    draw_lines(self.deselect_coords, width=4, color=color, alpha=0.2 if self.is_click else 0.1, screen=True)

    def draw_VIEW3D(self, context):
        if context.area == self.area:

            if self.backface_cull and self.culled_tri_coords:
                color, alpha = (green, 0.2) if self.keep else (red, 0.3)
                draw_tris(self.culled_tri_coords, color=color, alpha=alpha)

            elif not self.backface_cull and self.tri_coords:
                color, alpha = (green, 0.2) if self.keep else (red, 0.3)
                draw_tris(self.tri_coords, color=color, alpha=alpha)

            if self.center_origin and self.origin_preview_co:
                draw_point(self.origin_preview_co, color=blue, size=6)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        if event.type == 'LEFTMOUSE' and not event.alt and not event.shift:
            if event.value == 'PRESS':
                self.is_click = True
            else:
                self.is_click = False 

            force_ui_update(context)

        self.is_ctrl = event.ctrl
        self.is_shift = event.shift

        events = ['MOUSEMOVE', 'F', 'Q', 'K', 'B']

        if self.selected:
            events.append('C')

        if not self.is_shift:
            events.extend(['A', 'O'])

        if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):

            if event.type == 'MOUSEMOVE' or scroll_up(event, key=True) or scroll_down(event, key=True):
                if event.type == 'MOUSEMOVE':

                    if self.passthrough:
                        self.passthrough = False

                        if self.selected:
                            self.get_tri_coords(context, all=False, culled=True, debug=False)

                if self.is_shift:
                    if scroll_up(event, key=True):
                        self.fill_angle += 5

                    elif scroll_down(event, key=True):
                        self.fill_angle -= 5

                    force_ui_update(context)

                else:
                    if scroll_up(event, key=True):
                        self.selection_radius += 1 if event.shift else 5

                    elif scroll_down(event, key=True):
                        self.selection_radius -= 1 if event.shift else 5

                get_mouse_pos(self, context, event, hud_offset=(self.selection_radius, self.selection_radius))
                self.ray_origins = self.get_circular_ray_origins_from_mouse_pos(self.mouse_pos)

            if event.type in ['Q', 'K'] and event.value == 'PRESS':
                self.keep = not self.keep

                force_ui_update(context)

            elif event.type == 'A' and event.value == 'PRESS':
                self.selected = set()
                self.tri_coords = []
                self.culled_tri_coords = []

                force_ui_update(context)

            elif event.type == 'B' and event.value == 'PRESS':
                self.backface_cull = not self.backface_cull

                force_ui_update(context)

            elif event.type == 'O' and event.value == 'PRESS':
                self.outwards_select()

                self.get_tri_coords(context, all=True, culled=True, debug=False)

                self.origin_preview_co = self.get_origin_preview()

            elif event.type == 'F' and event.value == 'PRESS':

                if event.shift:
                    bpy.ops.view3d.view_selected('INVOKE_DEFAULT' if context.scene.HC.focus_mode == 'SOFT' else 'EXEC_DEFAULT')

                else:
                    bpy.ops.view3d.view_center_pick('INVOKE_DEFAULT')

                if self.selected:
                    self.get_tri_coords(context, all=False, culled=True, debug=False)

            elif event.type == 'C' and event.value == 'PRESS':
                self.center_origin = not self.center_origin

                force_ui_update(context)

        if self.is_click:
            self.update_face_selection(context, deselect=self.is_ctrl)

            self.get_tri_coords(context, all=True, culled=True, debug=False)

            self.origin_preview_co = self.get_origin_preview()

        else:
            self.hit_any = True

        if event.shift and event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.fill_select(context, deselect=self.is_ctrl, debug=True)

            self.get_tri_coords(context, all=True, culled=True, debug=False)

            self.origin_preview_co = self.get_origin_preview()

        if navigation_passthrough(event, alt=True, wheel=False):
            self.passthrough = True
            return {'PASS_THROUGH'}

        elif event.type in ['SPACE'] and self.selected:
            self.finish(context)

            self.save_settings()

            self.extract_evaluated_faces(context)
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:
            self.finish(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        
        finish_status(self)

        self.S.finish()

        self.active.show_wire = False

        restore_gizmos(self)

    def invoke(self, context, event):
        self.init_settings(props=['fill_angle', 'backface_cull', 'center_origin'])
        self.load_settings()

        self.active = context.active_object
        self.mx = self.active.matrix_world
        self.dg = context.evaluated_depsgraph_get()

        if event.alt or self.evaluated:

            self.keep = False
            self.selection_radius = 20
            self.selected = set()
            self.hit_any = True

            self.tri_coords = []
            self.culled_tri_coords = []
            self.circle_coords = []
            self.deselect_coords = []
            self.origin_preview_co = None

            self.is_click = False
            self.is_ctrl = False
            self.is_shift = False

            hide_gizmos(self, context)

            get_mouse_pos(self, context, event)
            self.ray_origins = self.get_circular_ray_origins_from_mouse_pos(self.mouse_pos)

            self.S = Snap(context, include=[self.active], debug=False)

            init_status(self, context, func=draw_extract_face_status(self))

            self.area = context.area
            self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
            self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:

            if event.ctrl:
                extracted = self.active
            
            else:

                extracted = duplicate_obj_recursively(context, self.active)
                extracted.name = f"{self.active.name}_Extracted"

            bm = bmesh.new()
            bm.from_mesh(extracted.data)
            bm.normal_update()
            bm.faces.ensure_lookup_table()

            selected = get_selected_faces(bm, index=self.index)
            remove = [f for f in bm.faces if f not in selected]

            bmesh.ops.delete(bm, geom=remove, context='FACES')

            bm.to_mesh(extracted.data)
            bm.free()

            extracted.HC.objtype = 'CUBE'
            extracted.HC.ishyper = True

            clear_hyper_face_selection(context, extracted)

            force_obj_gizmo_update(context)

            return {'FINISHED'}

    def get_circular_ray_origins_from_mouse_pos(self, mousepos):
        segments = min(max(int(self.selection_radius), 12), 64)

        ray_coords = []
        self.circle_coords = []
        self.deselect_coords = []

        ray_segments = segments
        radius = self.selection_radius

        for i in range(ray_segments):

            theta = 2 * pi * i / ray_segments 

            x = mousepos.x + radius * cos(theta)
            y = mousepos.y + radius * sin(theta)

            ray_coords.append(Vector((x, y)))

            self.circle_coords.append(Vector((x, y, 0)))

        self.circle_coords.append(self.circle_coords[0])

        if self.selection_radius > 20:
            ray_segments = int(segments / 4)   
            radius = self.selection_radius / 2

            for i in range(ray_segments):

                theta = 2 * pi * i / ray_segments

                x = mousepos.x + radius * cos(theta)
                y = mousepos.y + radius * sin(theta)

                ray_coords.append(Vector((x, y)))

        for angle in [0.25 * pi, 1.25 * pi, 1.75 * pi, 0.75 * pi]:
            x = mousepos.x + self.selection_radius * cos(angle)
            y = mousepos.y + self.selection_radius * sin(angle)

            self.deselect_coords.append(Vector((x, y, 0)))

        return ray_coords

    def get_tri_coords(self, context, all=True, culled=True, debug=False):
        name = self.active.name
        cache = self.S.cache
        bm = cache.bmeshes[self.active.name]

        if all:
            self.tri_coords = [co for idx in self.selected for co in cache.tri_coords[name][idx]]

        if culled:

            _, view_dir = get_view_origin_and_dir(context)

            self.culled_tri_coords = [co for idx in self.selected if get_world_space_normal(bm.faces[idx].normal, self.mx).dot(view_dir) < 0 for co in cache.tri_coords[name][idx]]

        if debug:
            print()
            print("tri_coords count:", len(self.tri_coords))
            print("culled tri_coords count:", len(self.culled_tri_coords))

    def manually_add_eval_mesh_to_snapping_cache(self, name, cache):

        cache.objects[name] = self.active

        mesh = bpy.data.meshes.new_from_object(self.active.evaluated_get(self.dg), depsgraph=self.dg)
        cache.meshes[name] = mesh

        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        cache.bmeshes[name] = bm

        cache.loop_triangles[name] = bm.calc_loop_triangles()
        cache.tri_coords[name] = {}

    def update_face_selection(self, context, deselect=False):
        hitindices = set()

        if self.backface_cull:
            view_dir = get_view_origin_and_dir(context)[1]

        for co in [self.mouse_pos] + self.ray_origins:
            self.S.get_hit(co)

            if self.S.hit:

                if self.backface_cull:
                    dot = view_dir.dot(self.S.hitnormal)

                    if dot < 0:
                        hitindices.add(self.S.hitindex)
                else:
                    hitindices.add(self.S.hitindex)

        for idx in hitindices:
            if deselect:
                if idx in self.selected:
                    self.selected.remove(idx)
            else:
                self.selected.add(idx)

        self.hit_any = bool(hitindices)

    def outwards_select(self, debug=False):
        name = self.active.name
        cache = self.S.cache

        if name not in cache.objects:
            self.manually_add_eval_mesh_to_snapping_cache(name, cache)

        center = self.active.matrix_world.to_translation()
        
        bm = cache.bmeshes[name]

        for f in bm.faces:

            face_center = self.mx @ f.calc_center_median_weighted()
            face_normal = get_world_space_normal(f.normal, self.mx)

            center_dir = (center - face_center).normalized()
            
            dot = face_normal.dot(center_dir)

            if dot < 0:
                if debug:
                    draw_point(face_center, modal=False)
                    draw_line([center, face_center], color=yellow, alpha=0.2, modal=False)
                    draw_vector(get_world_space_normal(f.normal, self.mx) * 0.2, origin=face_center, fade=True, modal=False)

                self.selected.add(f.index)

                if f.index not in cache.tri_coords[name]:
                    loop_triangles = cache.loop_triangles[name]

                    tri_coords = get_tri_coords(loop_triangles, [f], self.mx)
                    cache.tri_coords[name][f.index] = tri_coords

    def fill_select(self, context, deselect=False, debug=False):
        name = self.active.name
        cache = self.S.cache

        if self.backface_cull:
            view_dir = get_view_origin_and_dir(context)[1]

        self.S.get_hit(self.mouse_pos)

        if self.S.hit:

            bm = cache.bmeshes[name]

            if self.backface_cull:
                dot = view_dir.dot(self.S.hitnormal)

                if dot < 0:
                    hitface = bm.faces[self.S.hitindex]
                else:
                    hitface = None
            else:
                hitface = bm.faces[self.S.hitindex]

            if hitface:

                fill_faces = set()
                new_faces = {hitface}

                while new_faces:
                    face = new_faces.pop()
                    fill_faces.add(face)

                    neighbors = [f for e in face.edges for f in e.link_faces if f != face and f not in fill_faces and degrees(e.calc_face_angle()) < self.fill_angle]
                    new_faces.update(neighbors)

                for f in fill_faces:
                    if deselect:
                        if f.index in self.selected:
                            self.selected.remove(f.index)

                    else:
                        self.selected.add(f.index)

                        if f.index not in cache.tri_coords[name]:
                            loop_triangles = cache.loop_triangles[name]

                            tri_coords = get_tri_coords(loop_triangles, [f], self.mx)
                            cache.tri_coords[name][f.index] = tri_coords

    def get_origin_preview(self):
        if self.selected:
            bm = self.S.cache.bmeshes[self.active.name]

            verts = set(v for idx in self.selected for v in bm.faces[idx].verts)

            coords = np.array([v.co for v in verts])

            xmin = np.min(coords[:, 0])
            xmax = np.max(coords[:, 0])
            ymin = np.min(coords[:, 1])
            ymax = np.max(coords[:, 1])
            zmin = np.min(coords[:, 2])
            zmax = np.max(coords[:, 2])

            bbox = [Vector((xmin, ymin, zmin)),
                    Vector((xmax, ymin, zmin)),
                    Vector((xmax, ymax, zmin)),
                    Vector((xmin, ymax, zmin)),
                    Vector((xmin, ymin, zmax)),
                    Vector((xmax, ymin, zmax)),
                    Vector((xmax, ymax, zmax)),
                    Vector((xmin, ymax, zmax))]

            return self.mx @ average_locations(bbox)

    def change_origin(self, obj):
        bbox = get_bbox(obj.data)[0]
        center = self.mx @ average_locations(bbox)

        _, rot, sca = self.mx.decompose()
        mx = Matrix.LocRotScale(center, rot, sca)

        set_obj_origin(obj, mx, force_quat_mode=True)

    def extract_evaluated_faces(self, context):
        active = self.active
        mesh = bpy.data.meshes.new_from_object(active.evaluated_get(self.dg), depsgraph=self.dg)
        hc = active.HC

        objtype = hc.objtype
        cubelimit = hc.geometry_gizmos_show_cube_limit
        cylinderlimit = hc.geometry_gizmos_show_cylinder_limit
        
        if self.keep:
            old_mesh = active.data

            extracted = active
            extracted.modifiers.clear()

            extracted.data = mesh

            bpy.data.meshes.remove(old_mesh, do_unlink=True)

            remove_unused_children(context, extracted, debug=False)

        else:
            extracted = bpy.data.objects.new(name=f"{active.name}_Extracted", object_data=mesh)
        
            for col in active.users_collection:
                col.objects.link(extracted)

            extracted.matrix_world = active.matrix_world

            extracted.HC.objtype = objtype
            extracted.HC.ishyper = True

            extracted.HC.geometry_gizmos_show_cube_limit = cubelimit
            extracted.HC.geometry_gizmos_show_cylinder_limit = cylinderlimit

        extracted.vertex_groups.clear()

        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.normal_update()
        bm.faces.ensure_lookup_table()

        edge_glayer, face_glayer = ensure_gizmo_layers(bm)
        
        for v in bm.verts:
            v.hide = False

        clear_gizmos = hc.objtype == 'CUBE' and cubelimit < len(mesh.polygons) or hc.objtype == 'CYLINDER' and cylinderlimit < len(mesh.edges)

        for e in bm.edges:
            e.hide = False

            if clear_gizmos:
                e[edge_glayer] = 0

        for f in bm.faces:
            f.hide = False

            if clear_gizmos:
                f[face_glayer] = 0

        remove = [f for f in bm.faces if f.index not in self.selected]
        bmesh.ops.delete(bm, geom=remove, context='FACES')

        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=0.0001)

        loose_verts = [v for v in bm.verts if not v.link_edges]

        if loose_verts:
            bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")

        loose_edges = [e for e in bm.edges if not e.link_faces]

        if loose_edges:
            bmesh.ops.delete(bm, geom=loose_edges, context="EDGES")

        bm.to_mesh(mesh)
        bm.free()

        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = extracted
        extracted.select_set(True)

        if self.center_origin:
            self.change_origin(extracted)

        if self.keep:
            force_obj_gizmo_update(context)

class RemoveFace(bpy.types.Operator):
    bl_idname = "machin3.remove_face"
    bl_label = "MACHIN3: Remove Face"
    bl_description = "Remove selected Faces"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Face accociated with Gizmo, that is to be removed")

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.select_get() and active.HC.ishyper

    def invoke(self, context, event):
        self.loop = event.shift

        return self.execute(context)

    def execute(self, context):
        active = context.active_object

        self.remove_faces(active, loop=False)

        clear_hyper_face_selection(context, active)

        force_obj_gizmo_update(context)

        return {'FINISHED'}

    def remove_faces(self, active, loop=False):
        bm = bmesh.new()
        bm.from_mesh(active.data)
        bm.normal_update()
        bm.faces.ensure_lookup_table()

        remove = get_selected_faces(bm, index=self.index)
        bmesh.ops.delete(bm, geom=remove, context='FACES')

        bm.to_mesh(active.data)
        bm.free()

def draw_match_surface_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text="Match Surface")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Confirm")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text="", icon='MOUSE_MOVE')
        row.label(text="Pick Face")

        row.separator(factor=2)

        if op.S.hit:

            row.label(text="", icon='EVENT_ALT')
            row.label(text=f"Match Normal Only: {op.normal_only}")

            if op.is_active_obj_hit and not op.active.modifiers:
                row.separator(factor=2)

                row.label(text="", icon='EVENT_R')
                row.label(text=f"Remove Redundant Shared Edges: {op.remove_redundant}")

    return draw

class MatchSurface(bpy.types.Operator):
    bl_idname = "machin3.match_surface"
    bl_label = "MACHIN3: Match Surface"
    bl_description = "Match chosen Target Surface"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Face Index to match")

    is_active_obj_hit: BoolProperty(name="is ctive hit", description="hit is on the active object itself", default=False)
    is_index_face_hit: BoolProperty(name="is self hit", description="hit is on the index face itself", default=False)
    normal_only: BoolProperty(name="Match Normal Only", default=False)
    remove_redundant: BoolProperty(name="Remove Redundant Shared Edges", default=True)
    def draw(self, context):
        layout = self.layout
        column = layout.column()

        row = column.row(align=True)
        row.prop(self, 'normal_only', text="Normal Only", toggle=True)

        if self.is_active_obj_hit and not self.active.modifiers:
            row.prop(self, 'remove_redundant', text="Remove Redundant", toggle=True)

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            draw_label(context, title="Pick Face to Match", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

            self.offset += 18

            if self.S.hit:
                dims = draw_label(context, title=f"{self.S.hitobj.name} ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=green if self.is_active_obj_hit else blue, alpha=1)
                draw_label(context, title=f"Face: {self.S.hitindex}", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=red if self.is_index_face_hit else yellow, alpha=1)

            else:
                draw_label(context, title="None", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

            if self.is_index_face_hit:
                self.offset += 18
                draw_label(context, title="You can't match a face to itself", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=red, alpha=1)

            elif self.S.hit and self.normal_only:
                self.offset += 18
                draw_label(context, title="Only Match Normal", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=normal, alpha=1)

            if self.is_active_obj_hit and not self.active.modifiers and self.remove_redundant:
                self.offset += 18
                draw_label(context, title="Remove Redundant Shared Edges", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=red, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            if self.tri_coords:

                color = red if self.is_index_face_hit else green if self.is_active_obj_hit else blue
                draw_tris(self.tri_coords, color=color, alpha=0.1)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        self.normal_only = event.alt

        events = ['MOUSEMOVE']

        if self.is_active_obj_hit and not self.active.modifiers:
            events.append('R')

        if event.type in events:

            if event.type == 'MOUSEMOVE':
                get_mouse_pos(self, context, event)

                self.S.get_hit(self.mouse_pos)

                if self.S.hit:

                    self.is_active_obj_hit = self.S.hitobj == self.active
                    self.is_index_face_hit = self.is_active_obj_hit and self.S.hitindex == self.index

                    self.update_tri_coords()

                else:
                    self.is_active_obj_hit = False
                    self.is_index_face_hit = False

            elif event.type == 'R' and event.value == 'PRESS':
                self.remove_redundant = not self.remove_redundant

            force_ui_update(context)

        if navigation_passthrough(event, alt=False, wheel=True):
            return {'PASS_THROUGH'}

        elif self.S.hit and event.type in {'LEFTMOUSE', 'SPACE'}:

            if self.is_index_face_hit:
                draw_fading_label(context, text="You can't match a face to itself, duh!", y=120, color=red, alpha=1, move_y=20, time=2)

                return {'RUNNING_MODAL'}

            else:
                self.finish(context)

                self.match_surface(context)
                return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.finish(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        self.S.finish()

        finish_status(self)

        restore_gizmos(self)

        force_geo_gizmo_update(context)

    def invoke(self, context, event):
        self.active = context.active_object
        self.mx = self.active.matrix_world

        self.is_active_obj_hit = False
        self.is_index_face_hit = False

        self.normal_only = False

        self.tri_coords = []

        self.S = Snap(context, exclude_wire=True, debug=False)

        get_mouse_pos(self, context, event)

        hide_gizmos(self, context)

        init_status(self, context, func=draw_match_surface_status(self))

        force_ui_update(context)

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.active = context.active_object
        self.mx = self.active.matrix_world

        self.match_surface(context, debug=False)
        return {'FINISHED'}

    def update_tri_coords(self, debug=False):
        tri_coords = self.S.cache.tri_coords[self.S.hitobj.name]

        if self.S.hitindex in tri_coords:
            self.tri_coords = tri_coords[self.S.hitindex]
            
            if debug:
                print()
                print(f"found tri coords for index {self.S.hitindex} on object {self.S.hitobj.name}")
                print("", self.tri_coords)

    def match_surface(self, context, debug=False):
        hit_loc = self.mx.inverted_safe() @ self.S.hitlocation
        hit_normal = self.mx.inverted_safe().to_3x3() @ self.S.hitnormal

        hit_index = self.S.hitindex

        if debug:
            draw_point(hit_loc, mx=self.mx, color=yellow, modal=False)
            draw_vector(hit_normal, origin=hit_loc, mx=self.mx, color=white, modal=False)

        bm = bmesh.new()
        bm.from_mesh(self.active.data)
        bm.normal_update()
        bm.faces.ensure_lookup_table()

        face = bm.faces[self.index]

        face_loc = get_face_center(face, method='PROJECTED_BOUNDS')

        corners = {v: None for v in face.verts}

        face_edges = [e for e in face.edges]

        for v in corners:
            if debug:
                print("vert", v.index)

            corner_edges = [(e, face.normal.dot((v.co - e.other_vert(v).co).normalized())) for e in v.link_edges if e not in face_edges]

            if debug:
                for e, dot in corner_edges:
                    print("", e.index, dot)

            if corner_edges:
                best_edge = max(corner_edges, key=lambda x: x[1])[0]

                if debug:
                    print(" best edge:", best_edge)

                corners[v] = (v.co.copy(), best_edge.other_vert(v).co.copy())

        for v, line_coords in corners.items():
            if line_coords:
                i = intersect_line_plane(*line_coords, face_loc if self.normal_only else hit_loc, hit_normal)

                if i:
                    if debug:
                        draw_point(i, mx=self.mx, modal=False)

                    v.co = i

        if not self.active.modifiers and self.is_active_obj_hit and self.remove_redundant:

            hitface = bm.faces[hit_index]
            shared_edges = [e for e in face.edges if e in hitface.edges]

            if shared_edges:
                bmesh.ops.dissolve_edges(bm, edges=shared_edges, use_verts=True, use_face_split=False)

        bm.to_mesh(self.active.data)
        bm.free()

        self.active.select_set(True)

def draw_curve_surface_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text="Curve Surface")

        row.label(text="", icon='EVENT_SPACEKEY')
        row.label(text="Finish")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text="", icon='EVENT_A')
        row.label(text=f"New Object: {op.new_object}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_F')
        row.label(text="Flip Subdivision")

        row.separator(factor=2)

        row.label(text="", icon='MOUSE_MMB')
        row.label(text="Adjust Subdivision")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_ALT')
        row.label(text="", icon='MOUSE_MMB')
        row.label(text="Adjust Other Subdivision")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_CTRL')
        row.label(text="", icon='MOUSE_MMB')
        row.label(text="Adjust Pinch")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_Q')
        row.label(text=f"Lean: {op.lean}")

        if not op.new_object:
            row.separator(factor=2)

            row.label(text="", icon='EVENT_X')
            row.label(text=f"Remove Redundant Edges: {op.remove_redundant}")

    return draw

class CurveSurface(bpy.types.Operator):
    bl_idname = "machin3.curve_surface"
    bl_label = "MACHIN3: Curve Surface"
    bl_description = "Curve Chosen Face"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Face Index to curve")

    subd_x: IntProperty(name="Subdivide across Tangent", default=2, min=0)
    subd_y: IntProperty(name="Subdivide across Binormal", default=3, min=0)
    pinch: FloatProperty(name="Pinch", default=1.3, min=0.1)
    lean: BoolProperty(name="Lean Curvature Segments", default=True)
    remove_redundant: BoolProperty(name="Remove Redundant Edges", default=True)
    new_object: BoolProperty(name="Create New Object", default=False)
    passthrough = None

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.active_object

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            draw_label(context, title="Curve Surface", coords=Vector((self.HUD_x, self.HUD_y)), center=False, size=12)

            self.offset += 18

            dims = draw_label(context, title="Depth: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
            draw_label(context, title=dynamic_format(self.move_dir.length, decimal_offset=1), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False)

            self.offset += 18

            dims = draw_label(context, title="Subdivisions: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
            dims2 = draw_label(context, title=str(self.subd_x), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=red)
            dims3 = draw_label(context, title=" x ", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
            draw_label(context, title=str(self.subd_y), coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, color=green)

            self.offset += 18

            dims = draw_label(context, title="Pinch: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
            draw_label(context, title=f"{self.pinch:.1f}", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False)

            if self.lean:
                self.offset += 18
                draw_label(context, title="Leaning", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, size=12, color=yellow)

            if self.new_object:
                self.offset += 18
                draw_label(context, title="Add Curved Surface Object", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, size=12, color=green)

            elif self.remove_redundant:
                self.offset += 18
                draw_label(context, title="Remove Redundant Edges", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, size=12, color=red)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            draw_vector(self.tangent * 0.2, origin=self.face_origin, color=red, width=2, alpha=1)
            draw_vector(self.binormal * 0.2, origin=self.face_origin, color=green, width=2, alpha=1)

            if self.curved_grid_coords:
                draw_points(self.curved_grid_coords, color=white, size=3, alpha=0.7)
                draw_lines(self.curved_grid_coords, indices=self.curve_grid_indices, color=green if self.new_object else blue, alpha=1)

            if self.move_dir.length:
                point = context.window_manager.HC_curvesurfCOL[0]

                draw_line([Vector(point.bind_co), Vector(point.co)], color=yellow, alpha=0.4)

            if self.remove_redundant and not self.new_object:
                draw_line(self.data['redundant_edge_coords'], color=red, alpha=1)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        p = self.csCOL[0]
        self.move_dir = Vector(p.co) - Vector(p.bind_co)

        self.weight_map = self.create_weight_map(context)

        events = ['MOUSEMOVE', 'Q', 'F', 'R', 'X', 'A']

        if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):
            if event.type == 'MOUSEMOVE':
                get_mouse_pos(self, context, event)

                if self.passthrough:
                    self.passthrough = False

                    self.direction = self.get_movement_and_subd_direction(context, self.mouse_pos)

            if scroll_up(event, key=True) or scroll_down(event, key=True):

                if scroll_up(event, key=True):
                    if event.ctrl:
                        self.pinch += 0.1

                    elif event.shift:
                        self.subd_x += 1
                        self.subd_y += 1

                    elif self.direction == 'TANGENT':
                        if event.alt:
                            self.subd_y += 1
                        else:
                            self.subd_x += 1

                    elif self.direction == 'BINORMAL':
                        if event.alt:
                            self.subd_x += 1
                        else:
                            self.subd_y += 1

                elif scroll_down(event, key=True):
                    if event.ctrl:
                        self.pinch -= 0.1

                    elif event.shift:
                        self.subd_x -= 1
                        self.subd_y -= 1

                    elif self.direction == 'TANGENT':
                        if event.alt:
                            self.subd_y -= 1
                        else:
                            self.subd_x -= 1

                    elif self.direction == 'BINORMAL':
                        if event.alt:
                            self.subd_x -= 1
                        else:
                            self.subd_y -= 1

            if event.value == 'PRESS':

                if event.type == 'Q':
                    self.lean = not self.lean
                    self.active.select_set(True)

                elif event.type == 'F':
                    self.subd_x, self.subd_y = self.subd_y, self.subd_x

                elif event.type in ['R', 'X']:
                    self.remove_redundant = not self.remove_redundant
                    self.active.select_set(True)

                elif event.type == 'A':
                    self.new_object = not self.new_object
                    self.active.select_set(True)

                self.subd_coords = self.create_subd_coords()

                self.weight_map = self.create_weight_map(context)

        if navigation_passthrough(event, wheel=False):
            self.passthrough = True
            return {'PASS_THROUGH'}

        if gizmo_selection_passthrough(event):
            return {'PASS_THROUGH'}

        elif (self.subd_x or self.subd_y) and self.move_dir.length and event.type in ['SPACE'] and event.value == 'PRESS':
            self.create_curved_geo(context, debug=False)

            self.finish(context)
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC'] and event.value == 'PRESS':
            self.finish(context)

            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        wm = context.window_manager
        wm.gizmo_group_type_unlink_delayed('MACHIN3_GGT_curve_surface')

        finish_status(self)

        restore_gizmos(self)

        force_ui_update(context)

    def invoke(self, context, event):
        self.active = context.active_object
        mx = self.active.matrix_world

        self.bm = bmesh.new()
        self.bm.from_mesh(self.active.data)
        self.bm.normal_update()
        self.bm.faces.ensure_lookup_table()

        self.face = self.bm.faces[self.index]

        if len(self.face.verts) == 4:

            self.face_origin = mx @ get_face_center(self.face, method='PROJECTED_BOUNDS')
            self.face_normal = get_world_space_normal(self.face.normal, mx)

            self.rotmx = create_rotation_matrix_from_face(context, mx, self.face, edge_pair=True, align_binormal_with_view=False)
            
            self.tangent = self.rotmx.col[0].xyz
            self.binormal = self.rotmx.col[1].xyz

            self.csCOL = context.window_manager.HC_curvesurfCOL
            self.csCOL.clear()

            p = self.csCOL.add()
            p.co = self.face_origin
            p.bind_co = self.face_origin
            p.area_pointer = str(context.area.as_pointer())

            self.move_dir = Vector()

            p.normal = self.face_normal
            p.binormal = self.binormal
            p.tangent = self.tangent

            self.curved_grid_coords = []
            self.curve_grid_indices = []

            self.data = self.get_face_data(self.face, mx, debug=False)

            self.subd_coords = self.create_subd_coords()

            self.weight_map = self.create_weight_map(context)

            get_mouse_pos(self, context, event)

            self.direction = self.get_movement_and_subd_direction(context, self.mouse_pos, debug=True)

            context.window_manager.gizmo_group_type_ensure('MACHIN3_GGT_curve_surface')

            hide_gizmos(self, context)

            init_status(self, context, func=draw_curve_surface_status(self))

            force_ui_update(context)

            self.area = context.area
            self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
            self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        return {'CANCELLED'}

    def get_face_data(self, face, mx, debug=False):
        if debug:
            print()
            print(face)

        data = {'edges': [],
                'edge_dirs': {},
                'edge_coords': {},

                'corners': [],
                'redundant_edge_coords': []}

        for idx, loop in enumerate(face.loops):
            vert = loop.vert
            edge = loop.edge
            other = edge.other_vert(vert)

            edge_dir = (other.co - vert.co)

            data['edges'].append(edge)
            data['edge_dirs'][edge.index] = (mx.to_3x3() @ edge_dir)
            data['edge_coords'][edge.index] = (mx @ vert.co, mx @ other.co)

            data['corners'].append(vert)

            data['redundant_edge_coords'].extend(data['edge_coords'][edge.index])

        first_edge = min([(e, data['edge_dirs'][e.index].normalized().dot(self.binormal)) for e in data['edges']], key=lambda x: abs(x[1]))[0]

        if debug:
            print("edges:", [e.index for e in data['edges']])
            print("first:", first_edge.index)

            draw_line(data['edge_coords'][first_edge.index], color=green, modal=False)

        current_index = data['edges'].index(first_edge)

        if current_index != 0:
            rotate_list(data['edges'], amount=current_index)

            rotate_list(data['corners'], amount=current_index)

        data['corners'].insert(1, data['corners'].pop(-1))

        if debug:
            printd(data, 'face data (after rotation)')

        return data

    def create_subd_coords(self):
        first_edge = self.data['edges'][0]
        third_edge = self.data['edges'][2]

        first_co = self.data['edge_coords'][first_edge.index][0]
        fourth_co = self.data['edge_coords'][third_edge.index][1]

        first_dir = self.data['edge_dirs'][first_edge.index]
        third_dir = self.data['edge_dirs'][third_edge.index]

        subd_data = []

        for x in range(self.subd_x + 2):
            factor_x = (x) / (self.subd_x + 1)

            rail = []

            for y in range(self.subd_y + 2):
                factor_y = (y) / (self.subd_y + 1)

                rail.append(get_center_between_points(first_co + first_dir * factor_x, fourth_co - third_dir * factor_x, center=factor_y))

            subd_data.append(rail)

        return subd_data

    def create_weight_map(self, context):
        self.curved_grid_coords = []
        self.curve_grid_indices = []

        coords = [(co, tidx, bidx) for tidx, rail in enumerate(self.subd_coords) for bidx, co in enumerate(rail)]

        point = context.window_manager.HC_curvesurfCOL[0]
        bind_co = Vector(point.bind_co)

        weight_map = {idx: {'tidx': tidx,
                            'bidx': bidx,
                            'bind_co': co,

                            'moved_co': co,

                            'is_corner': False,
                            'vert': None} for idx, (co, tidx, bidx) in enumerate(coords)}

        for idx, data in weight_map.items():
            tidx = data['tidx']
            bidx = data['bidx']

            if (tidx == 0 and bidx == 0) or \
                    (tidx == 0 and bidx == self.subd_y + 1) or \
                    (tidx == self.subd_x + 1 and bidx == 0) or \
                    (tidx == self.subd_x + 1 and bidx == self.subd_y + 1):

                data['is_corner'] = True

            reversed_tidx = (self.subd_x + 1) - tidx
            reversed_bidx = (self.subd_y + 1) - bidx

            distance_tangent = min([tidx, reversed_tidx])
            distance_binormal = min([bidx, reversed_bidx])

            normalized_tangent = distance_tangent / ((self.subd_x + 1) / 2)
            normalized_binormal = distance_binormal / ((self.subd_y + 1) / 2)

            p = self.pinch  # pinch value, make it higher for a less bubbly look
            weight_tangent = (normalized_tangent / (pow(normalized_tangent, 1 + p) + p) * (1 + p))
            weight_binormal = (normalized_binormal / (pow(normalized_binormal, 1 + p) + p) * (1 + p))

            if self.lean:
                data['moved_co'] = data['bind_co'] + self.move_dir * ((weight_tangent + weight_binormal) / 2)

            else:
                i = intersect_point_line(Vector(point.co), bind_co, bind_co + self.tangent)
                move_dir_tangent = i[0] - self.face_origin

                i = intersect_point_line(Vector(point.co), bind_co, bind_co + self.binormal)
                move_dir_binormal = i[0] - self.face_origin

                i = intersect_point_line(Vector(point.co), bind_co, bind_co + self.face_normal)
                move_dir_normal = i[0] - self.face_origin

                data['moved_co'] = data['bind_co'] + move_dir_normal * ((weight_tangent + weight_binormal) / 2) + move_dir_tangent * weight_tangent + move_dir_binormal * weight_binormal

            self.curved_grid_coords.append(data['moved_co'])

            if bidx < self.subd_y + 1:
                self.curve_grid_indices.append((idx, idx + 1))

            if tidx < self.subd_x + 1:
                self.curve_grid_indices.append((idx, idx + self.subd_y + 2))

        return weight_map

    def get_movement_and_subd_direction(self, context, mouse_pos, debug=False):
        _, view_dir = get_view_origin_and_dir(context, mouse_pos)

        dot_tangent = abs(self.tangent.dot(view_dir))
        dot_binormal = abs(self.binormal.dot(view_dir))

        direction = 'BINORMAL' if dot_tangent >= dot_binormal else 'TANGENT'

        if debug:
            print("direction:", direction)

        return direction

    def create_weight_map_testing(self, context):
        coords = [(co, tidx, bidx) for tidx, rail in enumerate(self.subd_coords) for bidx, co in enumerate(rail)]

        point = context.window_manager.HC_curvesurfCOL[0]
        bind_co = Vector(point.bind_co)

        weight_map = {idx: {'tidx': tidx,
                            'bidx': bidx,
                            'bind_co': co,
                            'distance': 0,
                            'distance_tangent': 0,
                            'distance_binormal': 0,
                            'weight': 1,
                            'moved_co': co} for idx, (co, tidx, bidx) in enumerate(coords)}

        distances = []

        if self.move_dir.length:
            for idx, data in weight_map.items():
                distance = (bind_co - data['bind_co']).length
                data['distance'] = distance

                distances.append(distance)

            max_distance = max(distances)

            print()

            for idx, data in weight_map.items():
                distance = data['distance']

                reversed_tidx = (self.subd_x + 1) - data['tidx']
                reversed_bidx = (self.subd_y + 1) - data['bidx']

                print(str(idx).zfill(2), "tidx:", data['tidx'], f"({reversed_tidx})", "bidx:", data['bidx'], f"({reversed_bidx})",)

                data['distance_binormal'] = min([data['bidx'], reversed_bidx])

                print(" distance binormal:", data['distance_binormal'])

                normalized = data['distance_binormal'] / ((self.subd_y + 1) / 2)
                weight = (normalized / (pow(normalized, 2) + 1) * 2)

                data['moved_co'] = data['bind_co'] + self.move_dir * weight

        return weight_map

    def create_curved_geo(self, context, debug=False):
        if self.new_object:
            if debug:
                print("\nCreating new Curved Surface object")

            active = bpy.data.objects.new(name="Curved Surface", object_data=bpy.data.meshes.new(name="Curved Surface"))
            active.HC.ishyper = True
            active.HC.objtype = 'CUBE'

            bpy.ops.object.select_all(action='DESELECT')

            context.scene.collection.objects.link(active)
            active.select_set(True)
            context.view_layer.objects.active = active

            mx = Matrix.LocRotScale(self.face_origin, self.rotmx.to_3x3(), Vector((1, 1, 1)))

            active.matrix_world = mx

            bm = bmesh.new()
            bm.from_mesh(active.data)

            edge_glayer, face_glayer = ensure_gizmo_layers(bm)

        else:
            if debug:
                print("\nTurning Face into Curved Surface")

            active = self.active
            mx = active.matrix_world
            bm = self.bm

            edge_glayer, face_glayer = ensure_gizmo_layers(bm)

        if debug:
            printd(self.data, 'data')
            printd(self.weight_map, 'weight map')

        for idx, pdata in self.weight_map.items():

            if not self.new_object and pdata['is_corner']:
                pdata['vert'] = self.data['corners'].pop(0)

            else:

                v = bm.verts.new()
                v.co = mx.inverted_safe() @ pdata['moved_co']
                pdata['vert'] = v

        for idx, pdata in self.weight_map.items():
            if pdata['bidx'] <= self.subd_y and pdata['tidx'] <= self.subd_x:

                if debug:
                    print("creating face", idx, pdata['bidx'], pdata['tidx'])

                v1 = self.weight_map[idx]['vert']
                v2 = self.weight_map[idx + self.subd_y + 2]['vert']
                v3 = self.weight_map[idx + self.subd_y + 3]['vert']
                v4 = self.weight_map[idx + 1]['vert']

                bm.faces.new([v1, v2, v3, v4])

                if pdata['tidx'] == 0:
                    e = bm.edges.get([v1, v4])

                elif pdata['tidx'] == self.subd_x:
                    e = bm.edges.get([v2, v3])

                e[edge_glayer] = 1

                if pdata['bidx'] == 0:
                    e = bm.edges.get([v1, v2])
                elif pdata['bidx'] ==  self.subd_y:
                    e = bm.edges.get([v3, v4])

                e[edge_glayer] = 1

        if not self.new_object:

            if self.subd_x > 0:
                f = bm.faces.new([self.weight_map[idx]['vert'] for idx in reversed([i * (self.subd_y + 2) for i in range(self.subd_x + 2)])])
                f[face_glayer] = 1

                f = bm.faces.new([self.weight_map[idx]['vert'] for idx in [i * (self.subd_y + 2) + self.subd_y + 1 for i in range(self.subd_x + 2)]])
                f[face_glayer] = 1

            if self.subd_y > 0:
                f = bm.faces.new([self.weight_map[idx]['vert'] for idx in range(0, self.subd_y + 2)])
                f[face_glayer] = 1

                f = bm.faces.new([self.weight_map[idx]['vert'] for idx in reversed(range((self.subd_x + 1) * (self.subd_y + 2), (self.subd_x + 2) * (self.subd_y + 2)))])
                f[face_glayer] = 1

            bmesh.ops.delete(bm, geom=[self.face], context='FACES')

            edges = []

            if debug:
                print("\nredundant edges")

            for e in self.data['edges']:
                angle = round(degrees(e.calc_face_angle()) if e.is_manifold else 0, 4)

                if debug:
                    print(e.index, angle)

                if (angle == 0 and self.remove_redundant) or angle == 180:
                    edges.append(e)

            if edges:
                bmesh.ops.dissolve_edges(bm, edges=edges, use_verts=True, use_face_split=False)

        bm.to_mesh(active.data)
        bm.free()

def draw_adjust_curve_surface_point_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text="Adjust Curve Surface Point")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Finish")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text="", icon='MOUSE_MOVE')
        row.label(text="Adjust Curvature")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_CTRL')
        row.label(text="Limit Movement to Face Normal")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_X')
        row.label(text="Reset Curve Point on Face X")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_Y')
        row.label(text="", icon='EVENT_Z')
        row.label(text="Reset Curve Point on Face Y")

    return draw

class AdjustCurveSurfacePoint(bpy.types.Operator):
    bl_idname = "machin3.adjust_curve_surface_point"
    bl_label = "MACHIN3: Adjust Curve Surface Point"
    bl_options = {'INTERNAL'}

    index: IntProperty(name="Point Index to Adjust")

    def draw_VIEW3D(self, context):
        if context.area == self.area:

            draw_point(self.init_co, color=yellow, size=4)

            draw_point(self.co)

            draw_line([self.init_co, self.co], color=blue if self.is_snapping else white, alpha=0.5 if self.is_snapping else 0.1)

    def modal(self, context, event):
        if ignore_events(event):
            return {'PASS_THROUGH'}

        context.area.tag_redraw()

        self.is_snapping = event.ctrl

        events = ['MOUSEMOVE', *ctrl, 'X', 'Y', 'Z']

        if event.type in events:
            point = context.window_manager.HC_curvesurfCOL[self.index]

            if event.type in ['MOUSEMOVE', *ctrl]:
                get_mouse_pos(self, context, event)

                co = self.get_move_plane_intersection(context, self.mouse_pos)

                if self.is_snapping:
                    self.co = intersect_point_line(co, self.init_co, self.init_co + Vector(self.point.normal))[0]

                else:
                    self.co = co

                point.co = self.co

            elif event.type in ['X', 'Y', 'Z'] and event.value == 'PRESS':
                if event.type == 'X':
                    point.co = intersect_line_plane(Vector(point.co), Vector(point.co) + Vector(point.tangent), Vector(point.bind_co), Vector(point.tangent))

                elif event.type in ['Y', 'Z']:
                    point.co = intersect_line_plane(Vector(point.co), Vector(point.co) + Vector(point.binormal), Vector(point.bind_co), Vector(point.binormal))

                self.finish(context)
                return {'FINISHED'}

        if event.type in ['LEFTMOUSE', 'SPACE']:
            self.finish(context)

            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC'] and event.value == 'PRESS':
            self.finish(context)

            point = context.window_manager.HC_curvesurfCOL[self.index]
            point.co = self.init_co

            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        finish_status(self)

        if context.visible_objects:
            context.visible_objects[0].select_set(context.visible_objects[0].select_get())

    def invoke(self, context, event):
        self.csCOL = context.window_manager.HC_curvesurfCOL
        self.point = self.csCOL[self.index]
        self.init_co = Vector(self.point.co)

        self.is_snapping = False

        get_mouse_pos(self, context, event)

        self.move_plane_no = self.get_move_plane_normal(context, self.mouse_pos)

        self.co = self.get_move_plane_intersection(context, self.mouse_pos)

        init_status(self, context, func=draw_adjust_curve_surface_point_status(self))

        force_ui_update(context)

        self.area = context.area
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def get_move_plane_normal(self, context, mouse_pos):
        _, view_dir = get_view_origin_and_dir(context, coord=mouse_pos)

        return max([(no, no.dot(view_dir)) for no in [Vector(self.point.normal), Vector(self.point.binormal), Vector(self.point.tangent)]], key=lambda x: abs(x[1]))[0]

    def get_move_plane_intersection(self, context, mouse_pos):
        view_origin, view_dir = get_view_origin_and_dir(context, coord=mouse_pos)

        i = intersect_line_plane(view_origin, view_origin + view_dir, self.init_co, self.move_plane_no)

        if i:
            return i

class FlattenFace(bpy.types.Operator):
    bl_idname = "machin3.flatten_face"
    bl_label = "MACHIN3: Flatten Face"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Face accociated with Gizmo, that is to be removed")

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.select_get() and active.HC.ishyper

    @classmethod
    def description(cls, context, properties):
        return f"Flatten Face {properties.index}"

    def draw(self, context):
        layout = self.layout
        column = layout.column()

    def execute(self, context):
        print()
        print("Flatten Face", self.index)

        debug = False

        active = context.active_object
        mx = active.matrix_world

        bm = bmesh.new()
        bm.from_mesh(active.data)
        bm.normal_update()
        bm.faces.ensure_lookup_table()

        face = bm.faces[self.index]

        corner_vert = self.get_closest_vert(context, mx, face, debug=False)

        if corner_vert:
            print(corner_vert.index)

            if debug:
                draw_point(corner_vert.co.copy(), mx=mx, color=yellow, modal=False)

            connected_verts = [e.other_vert(corner_vert) for e in corner_vert.link_edges if face in e.link_faces]

            if debug:
                for v in connected_verts:
                    draw_point(v.co.copy(), mx=mx, modal=False)

            if len(connected_verts) == 2:

                flatten_normal = self.get_flatten_normal(corner_vert, connected_verts, face, mx=mx, debug=False)

                flatten_verts = [v for v in face.verts if v not in connected_verts + [corner_vert]]

                if flatten_verts:

                    data = self.get_data(face, flatten_verts, flatten_normal, mx, debug=False)

                    for v in flatten_verts:
                        i = intersect_line_plane(v.co, v.co + data[v], corner_vert.co, flatten_normal)

                        if i:
                            v.co = i

                    bm.to_mesh(active.data)
                    bm.free()

                    context.area.tag_redraw()

                    force_geo_gizmo_update(context)
                    return {'FINISHED'}

                else:
                    popup_message("Triangular Faces are flat already!", title="Illegal Selection")

        return {'CANCELLED'}

    def get_closest_vert(self, context, mx, face, debug=False):

        mousepos = Vector((*context.window_manager.HC_mouse_pos_region, 0))

        view_origin, view_dir = get_view_origin_and_dir(context, coord=mousepos)

        face_center = mx @ get_face_center(face, method='PROJECTED_BOUNDS')

        i = intersect_line_plane(view_origin, view_origin + view_dir, face_center, get_world_space_normal(face.normal, mx))

        if debug:
            print(i)

        if i:
            if debug:
                draw_point(i, color=yellow, modal=False)

            select_direction_dir = i - face_center

            if debug:
                print(select_direction_dir)
                draw_vector(select_direction_dir, origin=face_center, color=red, modal=False)

            edges = {e: {'distance': sys.maxsize,
                         'intersection': None} for e in face.edges}

            dir_coords = [face_center, i]

            for e in edges:
                if debug:
                    print("intersecting edge", e)

                edge_coords = [mx @ v.co for v in e.verts]

                intersections = intersect_line_line(*edge_coords, *dir_coords)

                if intersections:
                    edge_i = intersections[0]

                    intersect_dir = edge_i - face_center

                    dot = select_direction_dir.dot(intersect_dir)

                    if dot > 0:
                        if debug:
                            print(" intersected edge", e.index, "at", edge_i)
                            draw_point(edge_i, color=red, modal=False)
                            draw_line((face_center, edge_i.copy()), color=yellow, modal=False)

                        edges[e]['distance'] = (edge_i - i).length
                        edges[e]['intersection'] = mx.inverted_safe() @ edge_i

            closest_edge =  min(edges, key=lambda x: edges[x]['distance'])

            intersection = edges[closest_edge]['intersection']

            closest_vert = min([v for v in closest_edge.verts], key=lambda x: (x.co - intersection).length)

            if debug:
                print()
                print("intersected edge:", closest_edge.index)
                print("closest vert:", closest_vert.index)

                draw_point(closest_vert.co.copy(), mx=mx, size=10, modal=False)

            return closest_vert

    def get_flatten_normal(self, corner_vert, connected_verts, face, mx, debug=False):
        flatten_normal = (corner_vert.co - connected_verts[0].co).cross(corner_vert.co - connected_verts[1].co).normalized()

        if face.normal.dot(flatten_normal) < 0:
            flatten_normal.negate()

        if debug:
            draw_vector(flatten_normal, origin=corner_vert.co.copy(), mx=mx, color=yellow, modal=False)

        return flatten_normal

    def get_data(self, face, flatten_verts, flatten_normal, mx, debug=False):
        data = {}

        if debug:
            print("flatten verts:")

        for v in flatten_verts:

            if debug:
                print("", v)
                draw_point(v.co.copy(), mx=mx, color=green, modal=False)

            flatten_dir = flatten_normal

            dir_edges = [e for e in v.link_edges if e not in face.edges]

            if dir_edges:

                edge_dirs = [(edir := (e.verts[0].co - e.verts[1].co).normalized(), abs(edir.dot(flatten_normal))) for e in dir_edges]

                flatten_dir = max(edge_dirs, key=lambda x: x[1])[0]

            if debug:
                draw_vector(flatten_dir, origin=v.co.copy(), mx=mx, color=blue, modal=False)

            data[v] = flatten_dir

        if debug:
            printd(data)

        return data
