import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, FloatVectorProperty, StringProperty
import bmesh
from bpy.types import DATA_PT_camera
from mathutils import Quaternion, Vector, Matrix
from math import radians, sin, cos, degrees, pi
from .. utils.asset import get_pretty_assetpath
from .. utils.bmesh import ensure_gizmo_layers, ensure_custom_data_layers
from .. utils.ui import get_mouse_pos, get_mousemove_divisor, is_key, popup_message, get_zoom_factor, wrap_mouse, init_status, finish_status, navigation_passthrough, scroll_up, scroll_down, force_ui_update, force_obj_gizmo_update, ignore_events , get_scale, wrap_mouse
from .. utils.draw import draw_init, draw_label, draw_line, draw_lines, draw_vector, draw_points, draw_point, get_text_dimensions 
from .. utils.math import dynamic_format, average_locations, create_rotation_matrix_from_vectors
from .. utils.modifier import add_weld, get_auto_smooth, get_mod_input, get_mod_obj, hyper_array_poll, is_array, is_radial_array, move_mod, remote_boolean_poll, remove_mod, boolean_poll, set_mod_input, sort_modifiers, displace_poll, add_solidify, add_auto_smooth
from .. utils.object import get_min_dim, is_removable, remove_obj
from .. utils.system import printd
from .. utils.gizmo import hide_gizmos, restore_gizmos
from .. utils.property import step_list
from .. utils.view import ensure_visibility
from .. utils.registration import get_prefs
from .. items import add_cylinder_side_items, alt, shell_offset_mappings, numbers, input_mappings, pipe_mode_items, ctrl, shift
from .. colors import green, red, blue, yellow, white, grey, normal, orange

def draw_adjust_cylinder(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text="Adjust Cylinder")

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

            row.label(text="", icon='MOUSE_RMB')
            row.label(text="Cancel")

            row.label(text="", icon='EVENT_TAB')
            row.label(text="Enter Numeric Input")

            row.separator(factor=10)

            row.label(text="", icon='MOUSE_MMB')
            row.label(text=f"Sides: {op.sides}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_Q')
            row.label(text=f"Side Presets: {op.use_side_presets}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_R')
            row.label(text=f"Realtime Mesh Update: {op.use_realtime}")

            if op.use_realtime:
                row.separator(factor=2)

                row.label(text="", icon='EVENT_W')
                row.label(text=f"Wireframe: {op.show_wire}")

    return draw

class AdjustCylinder(bpy.types.Operator):
    bl_idname = "machin3.adjust_cylinder"
    bl_label = "MACHIN3: Adjust Cylinder"
    bl_description = "Adjust Cylinder Sides"
    bl_options = {'REGISTER', 'UNDO'}

    sides: IntProperty(name="Sides", default=12, min=3)
    angle_offset: FloatProperty(name="Angle Offset", default=0)
    use_side_presets: BoolProperty(name="Adjust Sides via Presets", default=True)
    use_realtime: BoolProperty(name="Realtime Mesh Adjustment", default=True)
    show_wire: BoolProperty(name="Show Wire", default=True)
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.HC.objtype == 'CYLINDER'

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        row = column.row(align=True)
        row.prop(self, 'segments')
        row.prop(self, 'angle_offset')

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            dims = draw_label(context, title="Adjust Cylinder ", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

            self.offset += 18

            dims = draw_label(context, title="Sides:", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

            title = "🖩" if self.is_numeric_input else " "
            dims2 = draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset + 3, center=False, size=20, color=green, alpha=0.5)

            if self.is_numeric_input:
                dims3 = draw_label(context, title=self.numeric_input_segments, coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=green, alpha=1)

                if self.is_numeric_input_marked:
                    scale = get_scale(context)
                    coords = [Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y - (self.offset - 5) * scale, 0)), Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y - (self.offset - 5) * scale, 0))]
                    draw_line(coords, width=12 + 8 * scale, color=green, alpha=0.1, screen=True)

            else:

                if self.use_side_presets:

                    if self.prev_sides < self.sides:
                        dims3 = draw_label(context, title=f"{self.prev_sides} ", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.3)
                    else:
                        dims3 = (0, 0)

                    dims4 = draw_label(context, title=f"{self.sides} ", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

                    if self.next_sides > self.sides:
                        dims5 = draw_label(context, title=f"{self.next_sides}", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + dims4[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.3)
                    else:
                        dims5 = (0, 0)

                    draw_label(context, title=' Presets', coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + dims4[0] + dims5[0], self.HUD_y)), offset=self.offset, center=False, size=12, color=normal, alpha=1)

                else:
                    draw_label(context, title=str(self.sides), coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

            if self.use_realtime:
                self.offset += 18
                draw_label(context, title="Realtime", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=green, alpha=1)

                if self.show_wire:
                    self.offset += 18
                    draw_label(context, title="Wireframe", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=blue, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            if not self.use_realtime:

                size = max(2, 5 - int(self.sides / 32))

                for ring in self.data['rings']:
                    draw_points(ring['coords'], mx=self.mx, size=size, alpha=0.3)

                for coords in self.data['ring_coords']:
                    draw_line(coords, mx=self.mx, width=1, alpha=0.2)

                for coords in self.data['segment_coords']:
                    draw_line(coords, mx=self.mx, width=1, alpha=0.2)

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

        if not self.active.visible_get():
            self.active.hide_set(False)

        restore_gizmos(self)

        self.active.show_wire = False

        force_ui_update(context, self.active)

        self.initbm.free()
        self.bm.free()

    def invoke(self, context, event): 
        self.debug = False

        self.active = context.active_object
        self.mx = self.active.matrix_world

        self.bm, self.initbm, self.layers = self.initialize_bmesh(self.active)

        cylinder_verts, is_smooth, has_bottom_face, has_top_face = self.analyse_cylinder_geometry(self.bm, debug=self.debug)

        if cylinder_verts:
            if self.debug:
                print("\ncylinder verts:")
                for idx, ring in enumerate(cylinder_verts):
                    print(" ring", idx, [v.index for v in ring])

                print("is smooth:", is_smooth)
                print("has bottom face:", has_bottom_face)
                print("has top face:", has_top_face)

            self.angle_offset = 0

            self.use_realtime = False if remote_boolean_poll(context, self.active) else True

            if self.use_realtime:
                self.active.show_wire = self.show_wire

            else:
                self.active.hide_set(True)

            hide_gizmos(self, context)

            get_mouse_pos(self, context, event)

            self.cylinder_data = self.get_cylinder_data(self.active.data, self.bm, self.layers, cylinder_verts, is_smooth, has_bottom_face, has_top_face, debug=self.debug)

            self.sides = self.cylinder_data['init_segments']

            self.prev_sides, self.next_sides = self.get_prev_and_next_sides(self.sides, debug=self.debug)

            self.is_numeric_input = False
            self.is_numeric_input_marked = False
            self.numeric_input_segments = '0'

            self.data = self.create_new_cylinder_data(self.cylinder_data, segments=self.sides, mx=self.mx, debug=self.debug)

            self.create_new_cylinder_geo(self.active, self.bm, self.data, self.layers)

            init_status(self, context, func=draw_adjust_cylinder(self))

            self.area = context.area
            self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
            self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:
            popup_message("Unexpected non-cylindrical Mesh", title="Illegal Topology")

            self.active.HC.objtype = 'CUBE'

            force_obj_gizmo_update(context)

            return {'CANCELLED'}

    def execute(self, context):
        debug = False

        active = context.active_object
        mx = active.matrix_world

        bm, initbm, layers = self.initialize_bmesh(active)

        cylinder_verts, is_smooth, has_bottom_face, has_top_face = self.analyse_cylinder_geometry(bm, debug=debug)

        if cylinder_verts:
            cylinder_data = self.get_cylinder_data(active.data, bm, layers, cylinder_verts, is_smooth, has_bottom_face, has_top_face, debug=debug)

            new_data = self.create_new_cylinder_data(cylinder_data, segments=self.sides, mx=mx, debug=debug)

            self.create_new_cylinder_geo(active, bm, new_data, layers, debug=debug)

        else:
            popup_message("Unexpected non-cylindrical Mesh", title="Illegal Topology")

            self.active.HC.objtype = 'CUBE'

            force_obj_gizmo_update(context)

        bm.free()
        initbm.free()

        return {'FINISHED'}

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

    def initialize_bmesh(self, active):
        initbm = bmesh.new()
        initbm.from_mesh(active.data)
        initbm.normal_update()

        bm = initbm.copy()

        glayers = ensure_gizmo_layers(bm)

        clayers = ensure_custom_data_layers(bm)

        layers = [*glayers, *clayers]

        return bm, initbm, layers

    def analyse_cylinder_geometry(self, bm, debug=False):
        def get_cylinder_verts(bottom_face, top_face, segments, edge_rings, debug=False):
            cylinder_verts = []

            loop = min([loop for loop in bottom_face.loops], key=lambda l: l.vert.index)

            first_edge = loop.edge

            if debug:
                print("\nbottom face looping:", first_edge.index, loop)

            verts = [loop.vert]
            cs = 1

            while True:
                loop = loop.link_loop_next

                if loop.edge == first_edge:
                    radial_next = loop.link_loop_radial_next
                    break
                else:
                    verts.append(loop.vert)
                    cs += 1

                if cs > segments:
                    print("WARNING: too many segments counted, encountered unexpected cylinder topology, aborting")
                    break

            if debug:
                print("bottom verts:", [v.index for v in verts])

            cylinder_verts.append(verts)
            cr = 1

            while True:

                loop = radial_next.link_loop_next.link_loop_next
                first_edge = loop.edge

                if debug:
                    print("side face looping:", first_edge.index, loop)

                verts = [loop.vert]
                cs = 1

                while True:
                    loop = loop.link_loop_next.link_loop_radial_next.link_loop_next

                    if loop.edge == first_edge:
                        radial_next = loop.link_loop_radial_next
                        break
                    else:
                        verts.append(loop.vert)
                        cs += 1

                    if cs > segments:
                        print("WARNING: too many segments counted, encountered unexpected cylinder topology, aborting")
                        break

                if debug:
                    print("side verts:", [v.index for v in verts])

                cylinder_verts.append(verts)
                cr += 1

                if radial_next.face == top_face or (top_face is None and not radial_next.edge.is_manifold):
                    if debug:
                        print("reached the cylinder top")
                    break

                if cr > edge_rings:
                    print("WARNING: too many edge rings counted, encountered unexpected cylinder topology, aborting")
                    break

            return cylinder_verts

        def get_circle_verts(top_face, debug=False):
            cylinder_verts = []

            loop = min([loop for loop in top_face.loops], key=lambda l: l.vert.index)

            first_edge = loop.edge

            if debug:
                print("\ntop face looping:", first_edge.index, loop)

            verts = [loop.vert]

            while True:
                loop = loop.link_loop_next

                if loop.edge == first_edge:
                    radial_next = loop.link_loop_radial_next
                    break
                else:
                    verts.append(loop.vert)

            if debug:
                print("top verts:", [v.index for v in verts])

            cylinder_verts.append(verts)

            return cylinder_verts

        if all(e.is_manifold for e in bm.edges):
            if debug:
                print("\nit's manifold all right")

            cap_faces = sorted([f for f in bm.faces if len(vs := f.verts) < 4 or len(vs) > 4], key=lambda x: x.calc_center_median().z)

            if len(cap_faces) == 2:

                bottom_face, top_face = cap_faces

                if debug:
                    print("found exactly 2 potential cap faces")
                    print(" bottom face index:", bottom_face.index)
                    print(" top face index:", top_face.index)

            elif all(len(f.verts) == 4 for f in bm.faces):
                all_faces = sorted([f for f in bm.faces], key=lambda x: x.calc_center_median().z)

                bottom_face, top_face = all_faces[::len(all_faces) - 1]

                if debug:
                    print("found all quad object")
                    print(" bottom face index:", bottom_face.index)
                    print(" top face index:", top_face.index)

            else:
                return None, None, None, None

            if len(bottom_face.verts) == len(top_face.verts):

                segment_count = len(bottom_face.verts)

                edge_ring_count = int(len(bm.verts) / segment_count)

                if debug:
                    print("top and bottom faces share the same vert count")
                    print(" segment count:", segment_count)
                    print(" edge rings:", edge_ring_count)

                cylinder_verts = get_cylinder_verts(bottom_face, top_face, segments=segment_count, edge_rings=edge_ring_count, debug=debug)
                
                return cylinder_verts, bottom_face.smooth, True, True

        else:
            if debug:
                print("\nit's not manifold!")

            cap_faces = sorted([f for f in bm.faces if len(vs := f.verts) < 4 or len(vs) > 4], key=lambda x: x.calc_center_median().z)

            if len(cap_faces) == 1:

                if debug:
                    print("found exactly 1 potential cap faces")

                if len(cap_faces[0].verts) == len(bm.verts):
                    top_face = cap_faces[0]

                    if debug:
                        print(" it's a circle!")
                        print(" top face index:", top_face.index)

                    cylinder_verts = get_circle_verts(top_face, debug=debug)

                    return cylinder_verts, top_face.smooth, False, True

                else:
                    top_face = None
                    bottom_face = cap_faces[0]

                    segment_count = len(bottom_face.verts)

                    if debug:
                        print(" bottom face index:", bottom_face.index)

                    edge_ring_count = int(len(bm.verts) / segment_count)

                    cylinder_verts = get_cylinder_verts(bottom_face, None, segments=segment_count, edge_rings=edge_ring_count, debug=debug)

                    return cylinder_verts, bottom_face.smooth, True, False

        return None, None, None, None

    def get_cylinder_data(self, mesh, bm, layers, cylinder_verts, is_smooth, has_bottom_face, has_top_face, debug=False):
        def create_z_dir_from_vert_ring(cylinder_verts, debug=False):
            first_ring = cylinder_verts[0]

            step_size = len(first_ring) // 3
            first, second, third = (first_ring[0], first_ring[step_size], first_ring[2 * step_size])

            second_dir = (second.co - first.co).normalized()
            third_dir = (third.co - first.co).normalized()

            z_dir = third_dir.cross(second_dir)

            if debug:
                draw_vector(second_dir, origin=first.co, mx=self.mx, color=yellow, modal=False)
                draw_vector(third_dir, origin=first.co, mx=self.mx, color=green, modal=False)
                draw_vector(z_dir, origin=first.co, mx=self.mx, color=blue, modal=False)

            return z_dir

        edge_glayer, face_glayer, vert_vg_layer, edge_bw_layer, edge_crease_layer = layers

        cylinder_data = {'edge_rings': [],
                         'init_segments': len(cylinder_verts[0]),
                         'is_smooth': is_smooth,
                         'has_bottom_face': has_bottom_face,
                         'has_top_face': has_top_face}

        z_dir = create_z_dir_from_vert_ring(cylinder_verts, debug=False)

        for ring in cylinder_verts:
            midpoint = average_locations([v.co for v in ring])

            first_dir = (ring[0].co - midpoint)

            x_dir = first_dir.normalized().cross(z_dir)

            y_dir = z_dir.cross(x_dir)

            radius = first_dir.project(y_dir).length

            first_edge = bm.edges.get([ring[0], ring[1]])

            ring_data = {'midpoint': midpoint,

                         'x_dir': x_dir,
                         'y_dir': y_dir,
                         'z_dir': z_dir,

                         'radius': radius,

                         'gizmos': first_edge[edge_glayer],

                         'sharp': not first_edge.smooth,
                         'seam': first_edge.seam,
                         'crease': first_edge[edge_crease_layer],
                         'bevelweight': first_edge[edge_bw_layer],

                         'vgroups': [vg for vg in ring[0][vert_vg_layer].items()]} 

            cylinder_data['edge_rings'].append(ring_data)

            if debug:
                draw_vector(x_dir, origin=midpoint, mx=self.mx, color=red, modal=False)
                draw_vector(y_dir, origin=midpoint, mx=self.mx, color=green, modal=False)
                draw_vector(z_dir, origin=midpoint, mx=self.mx, color=blue, modal=False)

        if debug:
            printd(cylinder_data)

        return cylinder_data

    def numeric_input(self, context, event):

        if event.type == "TAB" and event.value == 'PRESS':
            self.is_numeric_input = not self.is_numeric_input

            force_ui_update(context)

            if self.is_numeric_input:
                self.numeric_input_segments = str(self.sides)
                self.is_numeric_input_marked = True

            else:

                if self.use_side_presets:
                    self.prev_sides, self.next_sides = self.get_prev_and_next_sides(self.sides, debug=self.debug)

                return

        if self.is_numeric_input:
            events = [*numbers, 'BACK_SPACE', 'DELETE']

            if event.type in events and event.value == 'PRESS':

                if self.is_numeric_input_marked:
                    self.is_numeric_input_marked = False

                    if event.type == 'BACK_SPACE' and event.alt:
                        self.numeric_input_segments = self.numeric_input_segments[:-1]

                    else:
                        self.numeric_input_segments = input_mappings[event.type]

                else:
                    if event.type in numbers:
                        self.numeric_input_segments += input_mappings[event.type]

                    elif event.type == 'BACK_SPACE':
                        self.numeric_input_segments = self.numeric_input_segments[:-1]

                try:
                    if int(self.numeric_input_segments) >= 3:
                        self.sides = int(self.numeric_input_segments)

                    else:
                        return {'RUNNING_MODAL'}

                except:
                    return {'RUNNING_MODAL'}

                self.data = self.create_new_cylinder_data(self.cylinder_data, segments=self.sides, mx=self.mx, debug=self.debug)

                if self.use_realtime:
                    self.create_new_cylinder_geo(self.active, self.bm, self.data, self.layers)

            elif navigation_passthrough(event, alt=True, wheel=True):
                return {'PASS_THROUGH'}

            elif event.type in {'RET', 'NUMPAD_ENTER'}:
                if not self.use_realtime:
                    self.create_new_cylinder_geo(self.active, self.bm, self.data, self.layers)
                    
                self.finish(context)

                return {'FINISHED'}

            elif event.type in {'ESC', 'RIGHTMOUSE'}:
                self.initbm.to_mesh(self.active.data)

                self.finish(context)
                return {'CANCELLED'}

            return {'RUNNING_MODAL'}

    def interactive_input(self, context, event):
        events = ['MOUSEMOVE', 'Q', 'R', 'W']

        if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):

            if event.type == 'MOUSEMOVE':
                get_mouse_pos(self, context, event)

            elif scroll_up(event, key=True) or scroll_down(event, key=True):

                if self.use_side_presets:
                    if scroll_up(event, key=True):
                        self.sides = self.next_sides
                    else:
                        self.sides = self.prev_sides

                    self.prev_sides, self.next_sides = self.get_prev_and_next_sides(self.sides, debug=self.debug)

                else:
                    if scroll_up(event, key=True):
                        self.sides += 1
                    else:
                        self.sides -= 1

                self.data = self.create_new_cylinder_data(self.cylinder_data, segments=self.sides, mx=self.mx, debug=self.debug)

                if self.use_realtime:
                    self.create_new_cylinder_geo(self.active, self.bm, self.data, self.layers)

                force_ui_update(context, active=self.active)

            elif event.type in 'Q' and event.value == 'PRESS':
                self.use_side_presets = not self.use_side_presets

                if self.use_side_presets:
                    self.prev_sides, self.next_sides = self.get_prev_and_next_sides(self.sides, debug=self.debug)

                force_ui_update(context)

            elif event.type in 'R' and event.value == 'PRESS':
                self.use_realtime = not self.use_realtime

                self.active.hide_set(not self.use_realtime)

                if self.use_realtime:
                    self.create_new_cylinder_geo(self.active, self.bm, self.data, self.layers)

                    self.active.select_set(True)

                else:
                    self.data = self.create_new_cylinder_data(self.cylinder_data, segments=self.sides, mx=self.mx, debug=self.debug)

            elif self.use_realtime and event.type == 'W' and event.value == 'PRESS':
                self.show_wire = not self.show_wire

                self.active.show_wire = self.show_wire

        elif navigation_passthrough(event, alt=True, wheel=True):
            return {'PASS_THROUGH'}

        elif event.type in ['LEFTMOUSE', 'SPACE'] and event.value == 'PRESS':

            if not self.use_realtime:
                self.create_new_cylinder_geo(self.active, self.bm, self.data, self.layers)
                
            self.finish(context)
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:

            self.initbm.to_mesh(self.active.data)

            self.finish(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def create_new_cylinder_data(self, cylinder_data, segments=32, mx=Matrix(), debug=False):
        ring_coords = []
        segment_coords = [[] for i in range(segments)]

        new_data = {'rings': [],
                    'segments': segments, 

                    'is_smooth': cylinder_data['is_smooth'],
                    'has_bottom_face': cylinder_data['has_bottom_face'],
                    'has_top_face': cylinder_data['has_top_face'],

                    'ring_coords': ring_coords,
                    'segment_coords': segment_coords}

        for ring in cylinder_data['edge_rings']:
            midpoint = ring['midpoint']
            radius = ring['radius']

            ring_data = {'coords': None,

                         'gizmos': ring['gizmos'],

                         'sharp': ring['sharp'],
                         'seam': ring['seam'],
                         'crease': ring['crease'],
                         'bevelweight': ring['bevelweight'],

                         'vgroups': ring['vgroups']}

            coords = []

            for i in range(segments):

                angle = - radians(i * 360 / segments - 90 + self.angle_offset) 

                x = cos(angle) * radius
                y = sin(angle) * radius

                co = Vector((x, y, 0))
                coords.append(co)

            x_axis = ring['x_dir']
            y_axis = ring['y_dir']
            z_axis = ring['z_dir']

            if debug:
                draw_vector(x_axis, origin=midpoint, mx=mx, color=red, modal=False)
                draw_vector(y_axis, origin=midpoint, mx=mx, color=green, modal=False)
                draw_vector(z_axis, origin=midpoint, mx=mx, color=blue, modal=False)

            rotmx = create_rotation_matrix_from_vectors(x_axis, binormal=y_axis, normal=z_axis)

            z_align_mx = Matrix.LocRotScale(midpoint, rotmx.to_quaternion(), Vector((1, 1, 1)))

            new_cylinder_coords = [z_align_mx @ co for co in coords]
            ring_data['coords'] = new_cylinder_coords

            if not self.use_realtime:

                ring_coords.append(new_cylinder_coords + [new_cylinder_coords[0]])

                for idx, co in enumerate(new_cylinder_coords):
                    segment_coords[idx].append(co)

            if debug:
                draw_points(new_cylinder_coords, mx=mx, alpha=0.5, modal=False)

            new_data['rings'].append(ring_data)

        return new_data

    def create_new_cylinder_geo(self, active, bm, data, layers, debug=False):
        bmesh.ops.delete(bm, geom=bm.faces, context='FACES')

        edge_glayer, face_glayer, vert_vg_layer, edge_bw_layer, edge_crease_layer = layers

        segments = data['segments']

        new_verts = []

        for ridx, ring in enumerate(data['rings']):
            ring_verts = []

            for vidx, co in enumerate(ring['coords']):
                v = bm.verts.new(co)
                ring_verts.append(v)

                v.index = ridx * segments + vidx

            new_verts.append(ring_verts)

        for ridx, ring in enumerate(new_verts):

            if ridx < len(new_verts) - 1:

                ring_data = data['rings'][ridx]
                
                if ridx == len(new_verts) - 2:
                    next_ring_data = data['rings'][ridx + 1]

                for vidx, v in enumerate(ring):
                    current_v = v
                    next_v = ring[(vidx + 1) % segments] 

                    next_ring = new_verts[ridx + 1]

                    next_ring_current_v = next_ring[vidx]
                    next_ring_next_v = next_ring[(vidx + 1) % segments]

                    f = bm.faces.new((current_v, next_ring_current_v, next_ring_next_v, next_v))
                    f.smooth = data['is_smooth']

                    current_edge = bm.edges.get((current_v, next_v))

                    current_edge[edge_glayer] = ring_data['gizmos']

                    current_edge.smooth = not ring_data['sharp']
                    current_edge.seam = ring_data['seam']
                    current_edge[edge_crease_layer] = ring_data['crease']
                    current_edge[edge_bw_layer] = ring_data['bevelweight']

                    for gidx, weight in ring_data['vgroups']:
                        current_v[vert_vg_layer][gidx] = weight

                    if ridx == len(new_verts) - 2:
                        next_ring_current_edge = bm.edges.get((next_ring_current_v, next_ring_next_v))

                        next_ring_current_edge[edge_glayer] = next_ring_data['gizmos']

                        next_ring_current_edge.smooth = not next_ring_data['sharp']
                        next_ring_current_edge.seam = next_ring_data['seam']
                        next_ring_current_edge[edge_crease_layer] = next_ring_data['crease']
                        next_ring_current_edge[edge_bw_layer] = next_ring_data['bevelweight']

                        for gidx, weight in next_ring_data['vgroups']:
                            next_ring_current_v[vert_vg_layer][gidx] = weight

                    if vidx == 0:

                        vertical_edge = bm.edges.get((current_v, next_ring_current_v))
                        vertical_edge[edge_glayer] = 1

            if data['has_bottom_face'] and ridx == 0:
                f = bm.faces.new(ring)
                f.smooth = data['is_smooth']

                f[face_glayer] = 1

            elif data['has_top_face'] and ridx == len(new_verts) - 1:

                if data['has_bottom_face']:
                    ring.reverse()

                f = bm.faces.new(ring)
                f.smooth = data['is_smooth']

                f[face_glayer] = 1

        bm.verts.sort()

        bm.to_mesh(active.data)

        if len(active.data.edges) > active.HC.geometry_gizmos_show_cylinder_limit and active.HC.geometry_gizmos_edit_mode == 'EDIT':
           active.HC.geometry_gizmos_edit_mode = 'SCALE'

        elif len(active.data.edges) <= active.HC.geometry_gizmos_show_cylinder_limit and active.HC.geometry_gizmos_edit_mode == 'SCALE':
           active.HC.geometry_gizmos_edit_mode = 'EDIT'

def draw_adjust_pipe_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text="Adjust Pipe")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Finsh")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        if not op.is_cyclic:
            row.label(text="", icon='EVENT_E')
            row.label(text=f"Extend Ends: {op.extend_mode}")

            row.separator(factor=2)

        if op.pipe.data.bevel_mode != 'OBJECT':
            row.label(text="", icon='EVENT_X')
            row.label(text=f"Extrude Curve: {op.extrude_mode}")

            row.separator(factor=2)

        if op.pipe.data.bevel_mode in ['OBJECT', 'PROFILE'] or op.pipe.data.extrude:
            row.label(text="", icon='EVENT_T')
            row.label(text=f"Tilt Profile: {op.rotate_mode}")

            row.separator(factor=2)

        row.label(text="", icon='MOUSE_MOVE')
        text = "Adjust Pipe Ends" if op.extend_mode else "Adjust Profile Rotation" if op.rotate_mode else "Adjust Radius"
        row.label(text=text)

        if op.extrude_mode or op.rotate_mode:
            row.separator(factor=2)

            row.label(text="", icon='EVENT_R')
            row.label(text=f"Reset {'Extrusion' if op.extrude_mode else 'Tilt'}")

        if not any([op.extend_mode, op.extrude_mode, op.rotate_mode]):
            row.separator(factor=10)

            row.label(text="", icon='EVENT_B')
            row.label(text=f"Mode: {op.mode.title()}")

            if op.pipe.data.bevel_mode in ['ROUND', 'PROFILE']:
                row.separator(factor=2)

                row.label(text="", icon='MOUSE_MMB')
                row.label(text=f"Resolution: {op.pipe.data.bevel_resolution}")

            elif op.pipe.data.bevel_mode == 'OBJECT':
                if len(op.profiles) > 1:
                    row.separator(factor=2)

                    row.label(text="", icon='MOUSE_MMB')
                    row.label(text="Select Profile")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_F')
                row.label(text="Flip Profile")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_X')
                row.label(text="Remove Profile")

            if not op.is_cyclic:
                row.separator(factor=2)

                row.label(text="", icon='EVENT_C')
                row.label(text=f"Fill Caps: {op.fill_caps}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_S')
            row.label(text=f"Smooth Shading: {op.smooth}")

            if bpy.app.version >= (4, 1, 0) and op.smooth:
                row.separator(factor=1)

                row.label(text="", icon='EVENT_A')
                row.label(text=f"Auto Smooth: {op.autosmooth}")

    return draw

class AdjustPipe(bpy.types.Operator):
    bl_idname = "machin3.adjust_pipe"
    bl_label = "MACHIN3: Adjust Pipe"
    bl_description = "Adjust Pipe Radius, Resolution and Shading\nALT: Repeat last Adjustment"
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(name="Pipe Mode", items=pipe_mode_items, default='ROUND')
    radius: FloatProperty(name="Radius", default=0, min=0)
    resolution: IntProperty(name="Resolution", default=4, min=0)
    smooth: BoolProperty(name="Smooth", default=False)
    autosmooth: BoolProperty(name="AutoSmooth", default=False)
    fill_caps: BoolProperty(name="Fill Caps", default=True)
    extend: FloatProperty(name="Extend", default=0)
    rotate: FloatProperty(name="Rotate", default=0)
    is_profile_drop: BoolProperty(name="is Profile Drop", default=False)
    passthrough = None

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.type == 'CURVE'

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            if self.extend_mode:

                dims = draw_label(context, title=f"Extend Pipe ", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)
                dims2 = draw_label(context, title=f"Ends ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=yellow, alpha=1)

                if self.is_shift or self.is_ctrl:
                    if self.is_shift:
                        draw_label(context, title=f"a little", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)
                    else:
                        draw_label(context, title=f"a lot", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

                self.offset += 18
                dims = draw_label(context, title="Amount: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                draw_label(context, title=dynamic_format(self.extend, decimal_offset=1), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

            elif self.extrude_mode:

                dims = draw_label(context, title=f"Pipe ", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)
                dims2 = draw_label(context, title=f"Extrude ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=yellow, alpha=1)

                if self.is_shift or self.is_ctrl:
                    if self.is_shift:
                        draw_label(context, title=f"a little", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)
                    else:
                        draw_label(context, title=f"a lot", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

                self.offset += 18
                dims = draw_label(context, title="Amount: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                draw_label(context, title=dynamic_format(self.extrude, decimal_offset=1), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

            elif self.rotate_mode:

                dims = draw_label(context, title=f"Pipe ", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)
                dims2 = draw_label(context, title=f"Tilt ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=yellow, alpha=1)

                if self.is_shift:
                    if self.is_shift:
                        draw_label(context, title=f"a little", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

                self.offset += 18

                dims = draw_label(context, title="Rotate: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

                title = f"{int(self.snapped_rotate)}° " if self.is_ctrl else f"{dynamic_format(self.rotate, decimal_offset=1)}° "
                dims2 = draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=yellow if self.is_ctrl else white, alpha=1)

                if self.is_ctrl:
                    draw_label(context, title="Snapping", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

            else:

                dims = draw_label(context, title="Adjust ", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

                color = blue if self.mode == 'OBJECT' else yellow
                dims2 = draw_label(context, title=self.mode.title(), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=color, alpha=1)
                dims3 = draw_label(context, title=" Pipe ", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, color=white, alpha=1)

                if self.profiles:
                    dims4 = draw_label(context, title="🌠 ", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), center=False, color=blue, alpha=1)

                else:
                    dims4 = (0, 0)

                if self.is_shift or self.is_ctrl:
                    if self.is_shift:
                        draw_label(context, title="a little", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + dims4[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

                    else:
                        draw_label(context, title="a lot", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + dims4[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

                self.offset += 18

                title = 'Radius: ' if self.mode == 'ROUND' else 'Depth: '
                dims = draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

                draw_label(context, title=dynamic_format(self.radius, decimal_offset=1), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

                if self.mode == 'ROUND':
                    self.offset += 18

                    dims = draw_label(context, title="Resolution: ",  coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                    draw_label(context, title=str(self.resolution), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

                if self.mode == 'OBJECT':
                    self.offset += 18

                    dims = draw_label(context, title=f"Profile{'s' if len(self.profiles) > 1 else ''}: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=blue, alpha=1)

                    for idx, obj in enumerate(self.profiles):
                        if idx:
                            self.offset += 18

                        color = white if obj == self.pipe.data.bevel_object else grey
                        draw_label(context, title=get_pretty_assetpath(obj), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=color, alpha=1)

                if not self.is_cyclic:
                    self.offset += 18
                    
                    color, alpha = (green, 1) if self.fill_caps else (white, 0.25)
                    draw_label(context, title='Fill Caps', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=color, alpha=alpha)

                if self.autosmooth:
                    self.offset += 18
                    draw_label(context, title='Auto Smooth', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=red, alpha=1)

                elif self.smooth:
                    self.offset += 18
                    draw_label(context, title='Smooth', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=blue, alpha=1)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        self.is_shift = event.shift
        self.is_ctrl = event.ctrl  # NOTE: used for faster radius/depth adjustment, but also for snapping tilt rotation

        if not self.is_cyclic:

            if event.type == 'E':
                if event.value == 'PRESS':

                    if not self.extend_mode:

                        self.extend_mode = True
                        context.window.cursor_set('SCROLL_Y')

                elif event.value == 'RELEASE':

                    self.extend_mode = False
                    context.window.cursor_set('SCROLL_X')

                force_ui_update(context)

                return {'RUNNING_MODAL'}

            if self.extend_mode:

                if event.type == 'MOUSEMOVE':
                    get_mouse_pos(self, context, event)
                    wrap_mouse(self, context, y=True)

                    delta_y = self.mouse_pos.y - self.last_mouse.y
                    divisor = get_mousemove_divisor(event, sensitivity=0.03)

                    self.extend += delta_y * (self.factor / divisor)

                    first = self.ends_data['first']['point']
                    last = self.ends_data['last']['point']

                    first.co.xyz = self.ends_data['first']['co'] - self.ends_data['first']['dir'] * self.extend
                    last.co.xyz = self.ends_data['last']['co'] - self.ends_data['last']['dir'] * self.extend

                self.last_mouse = self.mouse_pos

                return {'RUNNING_MODAL'}

        if self.pipe.data.bevel_mode != 'OBJECT':
            if event.type == 'X':
                if event.value == 'PRESS':

                    if not self.extrude_mode:

                        self.extrude_mode = True
                        context.window.cursor_set('SCROLL_Y')

                elif event.value == 'RELEASE':

                    self.extrude_mode = False
                    context.window.cursor_set('SCROLL_X')

                force_ui_update(context)

                return {'RUNNING_MODAL'}

            if self.extrude_mode:

                if event.type == 'MOUSEMOVE':
                    get_mouse_pos(self, context, event)
                    wrap_mouse(self, context, y=True)

                    delta_y = self.mouse_pos.y - self.last_mouse.y
                    divisor = get_mousemove_divisor(event, sensitivity=0.03)

                    self.extrude += delta_y * (self.factor / divisor)

                    if self.extrude < 0:
                        self.extrude = 0

                elif event.type == 'R' and event.value == 'PRESS':

                    self.extrude = 0

                    self.extrude_mode = False
                    context.window.cursor_set('SCROLL_X')

                    force_ui_update(context)

                self.pipe.data.extrude = self.extrude

                self.last_mouse = self.mouse_pos

                return {'RUNNING_MODAL'}

        if self.pipe.data.bevel_mode in ['OBJECT', 'PROFILE'] or self.pipe.data.extrude:

            if event.type == 'T':
                if event.value == 'PRESS':

                    if not self.rotate_mode:

                        self.rotate_mode = True
                        context.window.cursor_set('SCROLL_Y')

                elif event.value == 'RELEASE':

                    self.rotate_mode = False
                    context.window.cursor_set('SCROLL_X')

                force_ui_update(context)

                return {'RUNNING_MODAL'}

            if self.rotate_mode:

                if event.type in ['MOUSEMOVE', *ctrl]:
                    get_mouse_pos(self, context, event)
                    wrap_mouse(self, context, y=True)

                    delta_y = self.mouse_pos.y - self.last_mouse.y
                    divisor = get_mousemove_divisor(event, ctrl=10, sensitivity=0.3)

                    self.rotate += delta_y / divisor

                    if self.is_ctrl:
                        step = 5
                        mod = self.rotate % step

                        self.snapped_rotate = self.rotate + (step - mod) if mod >= (step / 2) else self.rotate - mod

                    points = self.pipe.data.splines[0].points

                    for idx, p in enumerate(points):
                        p.tilt = radians(self.snapped_rotate if self.is_ctrl else self.rotate)

                elif event.type == 'R':
                    self.rotate_mode = False
                    context.window.cursor_set('SCROLL_X')

                    points = self.pipe.data.splines[0].points

                    for idx, p in enumerate(points):
                        p.tilt = 0

                    force_ui_update(context)

                self.last_mouse = self.mouse_pos

                return {'RUNNING_MODAL'}

        events = ['MOUSEMOVE', 'S', 'B']

        if bpy.app.version >= (4, 1, 0) and self.smooth:
            events.append('A')

        if not self.is_cyclic:
            events.append('C')

        if self.pipe.data.bevel_mode == 'OBJECT':
            events.append('X')
            events.append('F')

        if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):

            if event.type == 'MOUSEMOVE':
                get_mouse_pos(self, context, event)
                wrap_mouse(self, context, x=True)

                if self.passthrough:
                    self.passthrough = False

                    self.factor = get_zoom_factor(context, depth_location=self.pipe_loc, scale=1, ignore_obj_scale=False)

                delta_x = self.mouse_pos.x - self.last_mouse.x
                divisor = get_mousemove_divisor(event, sensitivity=0.03)

                self.radius += delta_x * (self.factor / divisor)

                self.pipe.data.bevel_depth = self.radius

                if self.pipe.data.bevel_mode == 'OBJECT':
                    self.set_profile_obj_size()

            elif self.mode in ['ROUND', 'OBJECT'] and scroll_up(event, key=True) or scroll_down(event, key=True):

                if scroll_up(event, key=True):

                    if self.mode == 'ROUND':
                        self.resolution += 1

                    elif self.mode == 'OBJECT':
                        self.pipe.data.bevel_object = step_list(self.pipe.data.bevel_object, self.profiles, step=-1, loop=True)

                elif scroll_down(event, key=True):

                    if self.mode == 'ROUND':
                        self.resolution -= 1

                    elif self.mode == 'OBJECT':
                        self.pipe.data.bevel_object = step_list(self.pipe.data.bevel_object, self.profiles, step=1, loop=True)

                if self.mode == 'ROUND':
                    self.pipe.data.bevel_resolution = self.resolution

                elif self.mode == 'OBJECT':
                    self.set_profile_obj_size()
                    self.update_profile_obj_visibility(context)

            elif event.type == 'S' and event.value == 'PRESS':
                self.smooth = not self.smooth

                for spline in self.pipe.data.splines:
                    spline.use_smooth = self.smooth

                if not self.smooth:
                    if mod := get_auto_smooth(self.pipe):
                        remove_mod(mod)

                    if self.autosmooth:
                        self.autosmooth =False

            elif event.type == 'A' and event.value == 'PRESS':
                self.autosmooth = not self.autosmooth

                if self.autosmooth and not (mod := get_auto_smooth(self.pipe)):
                    add_auto_smooth(self.pipe)

                elif not self.autosmooth and (mod := get_auto_smooth(self.pipe)):
                    remove_mod(mod)

            elif event.type == 'C' and event.value == 'PRESS':
                self.fill_caps = not self.fill_caps
                self.pipe.data.use_fill_caps = self.fill_caps

            elif event.type == 'B' and event.value == 'PRESS':
                self.cycle_pipe_mode(context, reverse=event.shift)

                force_ui_update(context, active=self.pipe)

            elif event.type == 'X' and event.value == 'PRESS':
                profile = self.pipe.data.bevel_object
                next_profile = step_list(profile, self.profiles, step=1, loop=True) if len(self.profiles) > 1 else None

                self.profiles.remove(profile)

                if next_profile:
                    self.pipe.data.bevel_object = next_profile

                else:
                    self.mode = 'ROUND'
                    self.pipe.data.bevel_mode = 'ROUND'
                    self.pipe.show_wire = True

                profile.hide_set(True)
                profile.show_in_front = False

            elif event.type == 'F' and event.value == 'PRESS':
                self.flip_profile_obj()

        if navigation_passthrough(event):
            self.passthrough = True
            return {'PASS_THROUGH'}

        elif event.type in ['LEFTMOUSE', 'SPACE']:
            self.finish(context)

            remove_profiles = set(self.initial_props['profiles']) - set(self.profiles)

            if remove_profiles:
                for obj in remove_profiles:
                    remove_obj(obj)

            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:
            self.finish(context)

            curve = self.pipe.data

            for prop, value in self.initial_props.items():
                if prop in ['bevel_mode', 'bevel_depth', 'bevel_resolution', 'bevel_object', 'use_fill_caps']:

                    if self.is_profile_drop and prop == 'bevel_object':
                        self.profiles.remove(value)

                        if self.profiles:
                            curve.bevel_object = self.profiles[0]

                        elif curve.bevel_mode == 'OBJECT':
                            if curve.bevel_resolution in [0, 1]:
                                curve.bevel_mode = 'PROFILE'
                            else:
                                curve.bevel_mode = 'ROUND'

                        bpy.data.objects.remove(value, do_unlink=True)

                    else:
                        setattr(curve, prop, value)

                elif prop == 'use_smooth':
                    for idx, spline in enumerate(self.pipe.data.splines):
                        spline.use_smooth = value[idx]

                elif prop == 'autosmooth':
                    mod = get_auto_smooth(self.pipe)

                    if value and not mod:
                        add_auto_smooth(self.pipe)

                    elif not value and mod:
                        remove_mod(mod)

            first = self.ends_data['first']['point']
            last = self.ends_data['last']['point']

            if not self.is_cyclic and self.extend != 0:
                first.co.xyz = self.ends_data['first']['co']
                last.co.xyz = self.ends_data['last']['co']

            return {'CANCELLED'}

        self.last_mouse = self.mouse_pos

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

        context.window.cursor_set('DEFAULT')

        self.pipe.show_wire = False

        restore_gizmos(self)

        self.update_profile_obj_visibility(context, reset=True)

    def invoke(self, context, event):
        self.pipe = context.active_object

        if event.alt:
            self.pipe.data.bevel_depth = self.radius
            self.pipe.data.bevel_resolution = self.resolution
            self.pipe.data.splines[0].use_smooth = self.smooth

            self.is_cyclic = self.pipe.data.splines[0].use_cyclic_u

            if not self.is_cyclic and self.extend != 0:
                self.ends_data = self.get_pipe_ends_data(debug=False)

                first = self.ends_data['first']['point']
                last = self.ends_data['last']['point']

                first.co.xyz = self.ends_data['first']['co'] - self.ends_data['first']['dir'] * self.extend
                last.co.xyz = self.ends_data['last']['co'] - self.ends_data['last']['dir'] * self.extend

                return {'FINISHED'}

        self.pipe_loc = self.pipe.matrix_world.to_translation()
        self.is_cyclic = self.pipe.data.splines[0].use_cyclic_u

        self.extend = 0
        self.extend_mode = False

        self.extrude = self.pipe.data.extrude
        self.extrude_mode = False

        self.rotate = degrees(self.pipe.data.splines[0].points[0].tilt)
        self.snapped_rotate = round(self.rotate)
        self.rotate_mode = False

        self.mode = self.get_pipe_mode()

        self.resolution = self.pipe.data.bevel_resolution if self.mode == 'ROUND' else 12

        self.radius = self.pipe.data.bevel_depth
        self.smooth = self.pipe.data.splines[0].use_smooth
        self.autosmooth = bool(bpy.app.version >= (4, 1, 0) and get_auto_smooth(self.pipe))
        self.fill_caps = self.pipe.data.use_fill_caps

        self.initial_props = {'bevel_mode': self.pipe.data.bevel_mode,
                              'bevel_depth': self.pipe.data.bevel_depth,
                              'bevel_resolution': self.pipe.data.bevel_resolution,
                              'bevel_object': self.pipe.data.bevel_object,
                              'use_fill_caps': self.pipe.data.use_fill_caps,
                              'use_smooth': [spline.use_smooth for spline in self.pipe.data.splines],
                              'profiles': [obj for obj in self.pipe.children if obj.type == 'CURVE']}   # profiles are not used for canceling, but when finsihing to determine if profile objects should be deleted!

        if bpy.app.version >= (4, 1, 0):
            self.initial_props['autosmooth'] = bool(get_auto_smooth(self.pipe))

        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        if not self.is_cyclic:
            self.ends_data = self.get_pipe_ends_data(debug=False)

        self.pipe.show_wire = self.mode != 'OBJECT'

        self.profiles = [obj for obj in self.pipe.children if obj.type == 'CURVE']

        if self.profiles and self.pipe.data.bevel_mode == 'OBJECT' and not self.pipe.data.bevel_object:
            self.pipe.data.bevel_object = self.profiles[0]

        self.update_profile_obj_visibility(context)

        get_mouse_pos(self, context, event)

        self.last_mouse = self.mouse_pos

        context.window.cursor_set('SCROLL_X')

        self.factor = get_zoom_factor(context, depth_location=self.pipe_loc, scale=1, ignore_obj_scale=False)

        hide_gizmos(self, context)

        init_status(self, context, func=draw_adjust_pipe_status(self))

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def get_pipe_mode(self):
        curve = self.pipe.data

        if curve.bevel_mode == 'ROUND':
            return 'ROUND'

        elif curve.bevel_mode == 'PROFILE':
            if curve.bevel_resolution == 0:
                return 'DIAMOND'

            else:
                if curve.bevel_resolution > 1:
                    curve.bevel_resolution = 1

                return 'SQUARE'

        else:
            return 'OBJECT'

    def cycle_pipe_mode(self, context, reverse=False):
        modes = [mode[0] for mode in pipe_mode_items]

        if not self.profiles:
            modes.remove('OBJECT')

        self.mode = step_list(self.mode, modes, step=-1 if reverse else 1)

        if self.mode == 'ROUND':
            self.pipe.data.bevel_mode = 'ROUND'
            self.pipe.show_wire = True
            self.pipe.data.bevel_resolution = self.resolution

        elif self.mode in ['DIAMOND', 'SQUARE']:
            self.pipe.data.bevel_mode = 'PROFILE'
            self.pipe.show_wire = True

            points = self.pipe.data.bevel_profile.points

            if len(points) == 2:
                pt = points.add(1, 1)
                pt.handle_type_1 = 'VECTOR'
                pt.handle_type_2 = 'VECTOR'
                pt.select = True

            self.pipe.data.bevel_resolution = 0 if self.mode == 'DIAMOND' else 1

        elif self.mode == 'OBJECT':
            self.pipe.data.bevel_mode = 'OBJECT'
            self.pipe.show_wire = False

        if self.pipe.data.bevel_object:
            self.update_profile_obj_visibility(context)

    def get_pipe_ends_data(self, debug=False):
        data = {'first': {'point': None,
                          'co': None,
                          'dir': None},

                'last': {'point': None,
                         'co': None,
                         'dir': None}}

        points = self.pipe.data.splines[0].points

        first = points[0]
        first_co = first.co.xyz.copy()
        first_dir = (points[0].co.xyz - points[1].co.xyz).normalized()

        last = points[-1]
        last_co = last.co.xyz.copy()
        last_dir = (points[-1].co.xyz - points[-2].co.xyz).normalized()

        data['first'] = {'point': first,
                         'co': first_co,
                         'dir': first_dir}

        data['last'] = {'point': last,
                        'co': last_co,
                        'dir': last_dir}

        if debug:
            printd(data, name='ends data')

            mx = self.pipe.matrix_world

            draw_point(first_co, mx=mx, color=green, modal=False)
            draw_point(last_co, mx=mx, color=red, modal=False)

            draw_vector(first_dir, origin=first_co, mx=mx, color=yellow, alpha=1, modal=False)
            draw_vector(last_dir, origin=last_co, mx=mx, color=yellow, alpha=1, modal=False)

        return data

    def update_profile_obj_visibility(self, context, reset=False):
        bevel_object = self.pipe.data.bevel_object

        if self.pipe.data.bevel_mode == 'OBJECT':
            for p in self.profiles:
                if p == bevel_object and not reset:
                    p.hide_set(False)

                    if context.space_data.local_view:
                        p.local_view_set(context.space_data, True)

                    p.select_set(True)
                    p.show_in_front = True

                else:
                    p.select_set(False)
                    p.show_in_front = False
                    p.hide_set(True)

        elif bevel_object:
            bevel_object.hide_set(True)
            bevel_object.show_in_front = False

    def set_profile_obj_size(self):
        if self.radius == 0:
            self.radius = 0.0001

        profile = self.pipe.data.bevel_object

        maxdim = max(profile.dimensions)
        dimdivisor = maxdim / self.radius / 2

        profile.dimensions = profile.dimensions / dimdivisor

    def flip_profile_obj(self, debug=False):
        for spline in self.pipe.data.splines:
            use_smooth = spline.use_smooth
            use_cyclic_u = spline.use_cyclic_u

            point_data = []

            if debug:
                print("\nbefore")

            for p in spline.points:
                point_data.append((p.co.copy(), p.tilt))

                if debug:
                    print(p.co, p.tilt)

            self.pipe.data.splines.remove(spline)

            new_spline = self.pipe.data.splines.new('POLY')
            new_spline.use_smooth = use_smooth
            new_spline.use_cyclic_u = use_cyclic_u

            new_spline.points.add(len(point_data) - 1)

            for idx, (co, tilt) in enumerate(reversed(point_data)):
                new_spline.points[idx].co = co
                new_spline.points[idx].tilt = 2 * pi - tilt

            if debug:
                print("\nafter")

                for p in new_spline.points:
                    print(p.co, p.tilt)

        self.rotate = degrees(self.pipe.data.splines[0].points[0].tilt)

def draw_adjust_pipe_arc_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text=f"Adjust Arc {op.index} {'Segments' if op.is_alt else 'Radius'}")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Finsh")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text="", icon='EVENT_ALT')
        row.label(text=f"Adjust Segments: {op.is_alt}")

        row.separator(factor=2)

        if op.is_alt:
            row.label(text="", icon='MOUSE_MOVE')
            row.label(text="Adjust Segments")

        else:
            row.label(text="", icon='MOUSE_MOVE')
            row.label(text="Adjust Radius")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_R')
        row.label(text=f"Reset")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_A')
        row.label(text=f"Reset All")

    return draw

class AdjustPipeArc(bpy.types.Operator):
    bl_idname = "machin3.adjust_pipe_arc"
    bl_label = "MACHIN3: Adjust Pipe Arc"
    bl_options = {'INTERNAL'}

    index: IntProperty(name="Arc Index to Adjust")

    @classmethod
    def description(cls, context, properties):
        dscr = f"Adjust Arc {properties.index} Radius"
        dscr += "\nALT: Adjust Segments"
        return dscr

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            dims = draw_label(context, title=f"Modulate Arc {self.index}", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

            if not self.is_alt:
                if self.is_shift:
                    draw_label(context, title=" a little", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

                elif self.is_ctrl:
                    draw_label(context, title=" a lot", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            self.offset += 18

            color, alpha = (white, 0.5) if self.is_alt else (yellow, 1)
            draw_label(context, title=f"Radius: {'+' if self.arc.modulate > 0 else ''}{dynamic_format(self.arc.modulate, decimal_offset=1)}", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=color, alpha=alpha)

            self.offset += 18

            color, alpha = (yellow, 1) if self.is_alt else (white, 0.5)
            draw_label(context, title=f"Segments: {'+' if self.arc.segment_modulate > 0 else ''}{int(self.arc.segment_modulate)}", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=color, alpha=alpha)

    def modal(self, context, event):
        if ignore_events(event):
            return {'PASS_THROUGH'}

        context.area.tag_redraw()

        events = ['MOUSEMOVE', 'R', 'A', *alt]

        self.is_alt = event.alt
        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        if event.type in events:

            if event.type == 'MOUSEMOVE':
                get_mouse_pos(self, context, event)
                wrap_mouse(self, context, x=True)

                delta_x = self.mouse_pos.x - self.last_mouse.x

                if event.alt:
                    self.arc.segment_modulate += (delta_x / 10)

                else:
                    divisor = get_mousemove_divisor(event, normal=1, shift=20, ctrl=0.1, sensitivity=1)

                    self.arc.modulate += delta_x * (self.factor / divisor)

            elif event.type == 'R' and event.value == 'PRESS':

                if event.alt:
                    self.arc.segment_modulate = 0
                else:
                    self.arc.modulate = 0

                self.finish(context)
                return {'FINISHED'}

            elif event.type == 'A' and event.value == 'PRESS':
                for arc in context.window_manager.HC_piperadiiCOL:

                    if event.alt:
                        arc.segment_modulate = 0
                    else:
                        arc.modulate = 0

                self.finish(context)
                return {'FINISHED'}

        if event.type in ['LEFTMOUSE', 'SPACE']:
            self.finish(context)
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:
            self.finish(context)

            self.arc.modulate = self.init_modulate

            return {'CANCELLED'}

        self.last_mouse = self.mouse_pos

        return {'PASS_THROUGH'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        restore_gizmos(self)

        finish_status(self)

        force_ui_update(context)

        context.window.cursor_set('DEFAULT')

        context.scene.HC.draw_pipe_HUD = True

    def invoke(self, context, event):
        self.arc = context.window_manager.HC_piperadiiCOL[self.index]
        self.init_modulate = self.arc.modulate

        self.is_alt = False
        self.is_shift = False
        self.is_ctrl = False

        context.scene.HC.draw_pipe_HUD = False

        get_mouse_pos(self, context, event)

        self.last_mouse = self.mouse_pos

        context.window.cursor_set('SCROLL_X')

        self.factor = get_zoom_factor(context, depth_location=self.arc.co, scale=1, ignore_obj_scale=True)

        hide_gizmos(self, context)

        init_status(self, context, func=draw_adjust_pipe_arc_status(self))

        force_ui_update(context)

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

def draw_adjust_shell_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text="Adjust Shell")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Finish")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        if op.is_hypermod_invoke:
            row.separator(factor=1)
            r = row.row(align=True)
            r.active = False
            r.label(text="Returns to HyperMod")
            row.separator(factor=2)

        else:
            row.separator(factor=10)

        row.label(text="", icon='EVENT_SHIFT')
        row.label(text="", icon='EVENT_CTRL')
        row.label(text=f"Precision: {'fine' if op.is_shift else 'coarse' if op.is_ctrl else 'normal'}")

        row.separator(factor=2)

        row.label(text="", icon='MOUSE_MOVE')
        precision = 2 if op.is_shift else 0 if op.is_ctrl else 1
        row.label(text=f"Thickness: {dynamic_format(op.shell_thickness, decimal_offset=precision)}")

        row.separator(factor=2)

        row.label(text="", icon='MOUSE_MMB')
        row.label(text=f"Offset: {shell_offset_mappings[op.shell_offset]}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_X')
        row.label(text="Remove Shell and Finish")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_E')
        row.label(text=f"Even: {op.shell_even}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_N')
        row.label(text=f"High Quality: {op.shell_high_quality}")

    return draw

class AdjustShell(bpy.types.Operator):
    bl_idname = "machin3.adjust_shell"
    bl_label = "MACHIN3: Adjust Shell Modifier"
    bl_description = "Adjust Shell Thickness\nALT: Repeat last Adjustment"
    bl_options = {'REGISTER', 'UNDO'}

    shell_thickness: FloatProperty(name="Thickness")
    shell_offset: FloatProperty(name="Offset")
    shell_even: BoolProperty(name="Even", default=False)
    shell_high_quality: BoolProperty(name="High Quality Normals", default=True)
    passthrough = None
    is_hypermod_invoke: BoolProperty()

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.active_object

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            dims = draw_label(context, title=f"Adjust {self.mod.name}", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

            if self.is_shift:
                draw_label(context, title=" a little", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            elif self.is_ctrl:
                draw_label(context, title=" a lot", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            self.offset += 18
            dims = draw_label(context, title="Thickness: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
            precision = 2 if self.is_shift else 0 if self.is_ctrl else 1
            dims2 = draw_label(context, title=dynamic_format(self.shell_thickness, decimal_offset=precision), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

            if self.shell_even:
                draw_label(context, title=" Even", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=blue, alpha=1)

            self.offset += 18
            dims = draw_label(context, title="Offset: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
            dims2 = draw_label(context, title=shell_offset_mappings[self.shell_offset], coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

            if self.shell_high_quality:
                self.offset += 18
                dims2 = draw_label(context, title="High Quality Normals", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=normal, alpha=1)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        events = ['MOUSEMOVE', 'E', 'X', 'N']

        if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):

            if event.type in ['MOUSEMOVE', 'D']:
                get_mouse_pos(self, context, event)
                wrap_mouse(self, context, x=True)

                if self.passthrough:
                    self.passthrough = False

                    self.factor = get_zoom_factor(context, depth_location=self.loc, scale=1, ignore_obj_scale=False)

                delta_x = self.mouse_pos.x - self.last_mouse.x
                divisor = get_mousemove_divisor(event, normal=1, shift=20, ctrl=0.1, sensitivity=1)

                self.shell_thickness += delta_x * (self.factor / divisor)
                self.mod.thickness = self.shell_thickness

            elif scroll_up(event, key=True) or scroll_down(event, key=True):
                offset_list = [-1, 0, 1]

                self.shell_offset = step_list(self.shell_offset, offset_list, step=-1 if event.type == 'WHEELUPMOUSE' else 1, loop=True)
                self.mod.offset = self.shell_offset
                self.mod.show_on_cage = self.mod.offset > -1

            if event.type == 'E' and event.value == 'PRESS':
                self.shell_even = not self.shell_even
                self.mod.use_even_offset = self.shell_even

            elif event.type == 'N' and event.value == 'PRESS':
                self.shell_high_quality = not self.shell_high_quality
                self.mod.use_quality_normals = self.shell_high_quality

            elif event.type == 'X' and event.value == 'PRESS':
                self.finish(context)

                remove_mod(self.mod)

                force_obj_gizmo_update(context)

                return {'FINISHED'}

        if navigation_passthrough(event):
            self.passthrough = True
            return {'PASS_THROUGH'}

        elif event.type in ['LEFTMOUSE', 'SPACE']:
            self.finish(context)

            if self.is_hypermod_invoke:
                bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')

            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:
            self.finish(context)

            if self.is_new_mod:
                remove_mod(self.mod)

            else:
                self.mod.thickness = self.init_thickness
                self.mod.offset = self.init_offset
                self.mod.use_even_offset = self.init_even
                self.mod.use_quality_normals = self.init_high_quality

                if self.is_hypermod_invoke:
                    bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')

            return {'CANCELLED'}

        self.last_mouse = self.mouse_pos

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

        restore_gizmos(self)

        context.window.cursor_set('DEFAULT')

    def invoke(self, context, event):
        self.active = context.active_object

        mods = [mod for mod in self.active.modifiers if mod.type == 'SOLIDIFY']

        if mods:
            enabled_mods = [mod for mod in mods if mod.show_viewport]

            if enabled_mods:
                self.mod = enabled_mods[0]

            else:
                self.mod = mods[0]
                self.mod.show_viewport = True

            self.is_new_mod = False
            self.init_thickness = self.mod.thickness
            self.init_offset = self.mod.offset

            self.init_even = self.mod.use_even_offset
            self.init_high_quality = self.mod.use_quality_normals

        else:
            min_dim = get_min_dim(self.active, world_space=False)
            self.mod = add_solidify(self.active, name='Shell', thickness=min_dim / 50)

            self.is_new_mod = True
            sort_modifiers(self.active, debug=False)

        self.mod.is_active = True

        if event.alt:
            self.mod.thickness = self.shell_thickness
            self.mod.offset = self.shell_offset
            self.mod.use_even_offset = self.shell_even
            self.mod.use_quality_normals = self.shell_high_quality
            return {'FINISHED'}

        self.loc = self.active.matrix_world.to_translation()
        self.is_shift = False
        self.is_ctrl = False

        self.shell_thickness = self.mod.thickness

        if self.mod.offset not in [-1, 0, 1]:
            self.mod.offset = round(self.mod.offset)
        self.shell_offset = self.mod.offset

        self.shell_even = self.mod.use_even_offset
        self.shell_high_quality = self.mod.use_quality_normals

        self.factor = get_zoom_factor(context, depth_location=self.loc, scale=1, ignore_obj_scale=False)

        get_mouse_pos(self, context, event)

        self.last_mouse = self.mouse_pos

        hide_gizmos(self, context)

        context.window.cursor_set('SCROLL_X')

        force_ui_update(context)

        init_status(self, context, func=draw_adjust_shell_status(self))

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

def draw_adjust_displace_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text=f"Adjust {'Remote ' if op.is_remote else ''}Displace")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Finish")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        if op.is_hypermod_invoke:
            row.separator(factor=1)
            r = row.row(align=True)
            r.active = False
            r.label(text="Returns to HyperMod")
            row.separator(factor=2)

        else:
            row.separator(factor=10)

        if op.is_remote:
            row.label(text="", icon='EVENT_S')
            row.label(text="Switch to Remote Displace")

            row.separator(factor=2)

        row.label(text="", icon='EVENT_SHIFT')
        row.label(text="", icon='EVENT_CTRL')
        row.label(text=f"Precision: {'fine' if op.is_shift else 'coarse' if op.is_ctrl else 'normal'}")

        row.separator(factor=2)

        row.label(text="", icon='MOUSE_MOVE')
        precision = 2 if op.is_shift else 0 if op.is_ctrl else 1
        row.label(text=f"Strength: {dynamic_format(op.displace_strength, decimal_offset=precision)}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_X')
        row.label(text="Remove Displace and Finish")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_R')
        row.label(text="Reset Displace Strength to 0")

    return draw

class AdjustDisplace(bpy.types.Operator):
    bl_idname = "machin3.adjust_displace"
    bl_label = "MACHIN3: Adjust Displace Modifier"
    bl_description = "Adjust Displace Amount\nALT: Repeat last Adjustment"
    bl_options = {'REGISTER', 'UNDO'}

    displace_strength: FloatProperty(name="Strength")
    is_remote: BoolProperty(name="Remote Displace")

    passthrough = None
    is_hypermod_invoke: BoolProperty()

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.active_object

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            dims = draw_label(context, title=f"Adjust {self.mod.name}", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

            if self.is_shift:
                draw_label(context, title=" a little", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            elif self.is_ctrl:
                draw_label(context, title=" a lot", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            if self.is_remote and self.boolean_object:
                dims2 = draw_label(context, title=" remotely on ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)
                draw_label(context, title=self.boolean_object.name, coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=12, color=white, alpha=1)

            self.offset += 18
            dims = draw_label(context, title="Strength: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
            precision = 2 if self.is_shift else 0 if self.is_ctrl else 1
            draw_label(context, title=dynamic_format(self.displace_strength, decimal_offset=precision), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        events = ['MOUSEMOVE', 'X', 'R']

        if self.is_remote:
            events.append('S')

        if event.type in events:

            if event.type in ['MOUSEMOVE', 'S']:
                get_mouse_pos(self, context, event)
                wrap_mouse(self, context, x=True)

                if self.passthrough:
                    self.passthrough = False

                    self.factor = get_zoom_factor(context, depth_location=self.loc, scale=1, ignore_obj_scale=False)

                delta_x = self.mouse_pos.x - self.last_mouse.x
                divisor = get_mousemove_divisor(event, normal=1, shift=20, ctrl=0.1, sensitivity=1)

                self.displace_strength -= delta_x * (self.factor / divisor)
                self.mod.strength = self.displace_strength

            if event.type == 'R' and event.value == 'PRESS':
                self.mod.strength = 0

                self.finish(context)

                if self.is_hypermod_invoke:
                    bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')
                return {'FINISHED'}

            elif event.type == 'X' and event.value == 'PRESS':
                self.finish(context)

                remove_mod(self.mod)

                force_obj_gizmo_update(context)

                return {'FINISHED'}

            elif event.type == 'S' and event.value == 'PRESS':
                if self.is_remote and self.boolean_object:
                    self.finish(context)

                    ensure_visibility(context, self.boolean_object)

                    bpy.ops.object.select_all(action='DESELECT')

                    self.boolean_object.select_set(True)
                    context.view_layer.objects.active = self.boolean_object

                    bpy.ops.machin3.adjust_displace('INVOKE_DEFAULT')

                    return {'FINISHED'}

        if navigation_passthrough(event):
            self.passthrough = True
            return {'PASS_THROUGH'}

        elif event.type in ['LEFTMOUSE', 'SPACE']:
            self.finish(context)

            if self.is_hypermod_invoke:
                bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:
            self.finish(context)

            self.mod.strength = self.init_strength

            if self.is_hypermod_invoke:
                bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')

            return {'CANCELLED'}

        self.last_mouse = self.mouse_pos

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

        restore_gizmos(self)

        context.window.cursor_set('DEFAULT')

    def invoke(self, context, event):
        self.active = context.active_object
        self.mod = None

        mods = [mod for mod in self.active.modifiers if mod.type == 'DISPLACE']

        if mods:
            enabled_mods = [mod for mod in mods if mod.show_viewport]

            if enabled_mods:
                self.mod = enabled_mods[0]

            else:
                self.mod = mods[0]
                self.mod.show_viewport = True

            self.is_remote = False
            self.boolean_object = None

        else:
            intersect_booleans = [mod for mod in boolean_poll(context) if mod.operation == 'INTERSECT']

            for boolean_mod in reversed(intersect_booleans):
                mods = displace_poll(context, obj=boolean_mod.object)

                if mods:
                    self.mod = mods[0]
                    self.is_remote = True
                    self.boolean_object = boolean_mod.object
                    break

        if self.mod:
            self.init_strength = self.mod.strength

        else:
            return {'CANCELLED'}

        self.mod.is_active = True

        if event.alt:
            self.mod.strength = self.displace_strength

            return {'FINISHED'}

        self.loc = self.active.matrix_world.to_translation()
        self.is_shift = False
        self.is_ctrl = False

        self.displace_strength = self.mod.strength

        self.factor = get_zoom_factor(context, depth_location=self.loc, scale=1, ignore_obj_scale=False)

        get_mouse_pos(self, context, event)

        self.last_mouse = self.mouse_pos

        hide_gizmos(self, context)

        context.window.cursor_set('SCROLL_X')

        force_ui_update(context)

        init_status(self, context, func=draw_adjust_displace_status(self))

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

def draw_adjust_array_status(op):
    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)

        mod = op.mod
        is_radial = op.is_radial

        row.label(text=f"Adjust {'Radial' if is_radial else 'Linear'} Array")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Finish")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        if op.is_hypermod_invoke:
            row.separator(factor=1)
            r = row.row(align=True)
            r.active = False
            r.label(text="Returns to HyperMod")
            row.separator(factor=2)

        else:
            row.separator(factor=10)

        if op.is_multi_array and not op.is_adjusting:
            row.label(text="", icon='EVENT_CTRL')
            row.label(text="", icon='MOUSE_MMB')
            row.label(text=f"Select Array: {op.mod.name}")

            row.separator(factor=2)

        if op.is_radial:
            angle = "360°" if op.radial_full else dynamic_format(degrees(op.radial_angle), decimal_offset=1)

            if not (op.radial_full):
                row.label(text="", icon='EVENT_T')

            row.label(text=f"Angle: {angle}")

        else:
            distance = dynamic_format(op.distance, decimal_offset=1)
            row.label(text="", icon='EVENT_T')
            row.label(text=f"Distance: {distance}")

        if op.is_adjusting:
            row.separator(factor=2)

            if op.is_radial:
                row.label(text="", icon='EVENT_SHIFT')
                row.label(text=f"Precision: {'fine' if op.is_shift else 'normal'}")

                row.separator(factor=3)
                row.label(text="", icon='EVENT_CTRL')
                row.label(text=f"{1 if op.is_shift else 5}° Angle Snap: {op.is_ctrl}")

            else:
                row.label(text="", icon='EVENT_SHIFT')
                row.label(text="", icon='EVENT_CTRL')
                row.label(text=f"Precision: {'fine' if op.is_shift else 'coarse' if op.is_ctrl else 'normal'}")

        else:
            row.separator(factor=2)

            row.label(text="", icon='MOUSE_MMB')
            row.label(text=f"Count: {op.count}")

            if not (op.is_radial and op.radial_full):
                row.separator(factor=2)

                row.label(text="", icon='EVENT_A')
                row.label(text=f"Mode: {'Fit' if op.fit else 'Add'}")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_C')
                row.label(text=f"Center: {op.center}")

            if op.is_radial:
                row.separator(factor=2)

                row.label(text="", icon='EVENT_F')
                row.label(text=f"Full 360°: {op.radial_full}")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_Q')
                row.label(text=f"Align: {op.radial_align}")

                if op.radial_full and not op.instances and op.radial_align:
                    row.separator(factor=2)
                    row.label(text="", icon='EVENT_W')
                    row.label(text=f"Weld: {bool(op.weld)}")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_S')
                row.label(text="Select Origin Object")

                row.separator(factor=1)

                row.label(text="", icon='EVENT_SHIFT')
                row.label(text="", icon='EVENT_S')
                row.label(text="Select Origin Object (keep existing Selection)")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_X')
            row.label(text=f"Remove Array{'s' if op.instances and op.affect_instances else''}")

            if op.instances:
                row.separator(factor=2)

                row.label(text="", icon='EVENT_R')
                row.label(text=f"Affect Related Arrays: {op.affect_instances}")

    return draw

class AdjustArray(bpy.types.Operator):
    bl_idname = "machin3.adjust_array"
    bl_label = "MACHIN3: Adjust Array"
    bl_description = "Adjust Hyper Array Modifier"
    bl_options = {'REGISTER', 'UNDO'}

    count: IntProperty(name="Count", default=2, min=2)
    fit: BoolProperty(name="Fit", default=False)
    center: BoolProperty(name="Center", default=False)
    linear_offset: FloatVectorProperty(name="Offset")
    distance: FloatProperty(name="Distance")

    radial_angle: FloatProperty(name="Angle", default=0)
    radial_full: BoolProperty(name="Full 360°", default=False)
    radial_align: BoolProperty(name="Align", default=False)
    affect_instances: BoolProperty(name="Affect Instances", default=True)
    passthrough = None
    is_hypermod_invoke: BoolProperty()

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.active_object

    def draw_HUD(self, context):
        if self.area == context.area:
            draw_init(self)

            scale = get_scale(context)

            action = 'Pick' if self.is_picking else 'Adjust'
            dims = draw_label(context, title=f"{action} ", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=orange if self.is_adjusting else white, alpha=1)

            if self.is_multi_array:

                dims = get_text_dimensions(context, 'Adjust ')

                index = self.arrays.index(self.mod)
                color = blue if self.is_picking else green

                size = 10 if self.is_picking else 8

                if index > 0:
                    self.offset -= (index - 1) * (18 if self.is_picking else 10) + 18

                for idx, mod in enumerate(self.arrays):
                    if idx < index:
                        alpha = 0.3 if self.is_picking else (idx + 1) * (0.3 / (index + 1))
                        draw_label(context, title=mod.name, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=size, color=white, alpha=alpha)

                        self.offset += 18 if (self.is_picking or idx == index - 1) else 10

                    elif idx == index:
                        dims2 = draw_label(context, title=self.mod.name, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=color, alpha=1)

                        if self.is_adjusting:
                            if self.is_shift:
                                draw_label(context, title=" a little", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

                            elif self.is_ctrl and not self.is_radial:
                                draw_label(context, title=" a lot", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

                        elif self.is_picking:
                            coords = [Vector((self.HUD_x + dims[0] - (5 * scale), self.HUD_y - (self.offset * scale), 0)), Vector((self.HUD_x + dims[0] - (5 * scale), self.HUD_y - (self.offset * scale) + (10 * scale), 0))]
                            draw_line(coords, color=blue, width=2 * scale, screen=True)

                        if idx < len(self.arrays) - 1:
                            self.offset += 18

                    else:
                        alpha = 0.3 if self.is_picking else 0.3 - ((idx - index) * (0.3 / (len(self.arrays) - index)))
                        draw_label(context, title=mod.name, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=size, color=white, alpha=alpha)

                        if idx < len(self.arrays) - 1:
                            self.offset += 18 if self.is_picking else 10

            else:
                dims2 = draw_label(context, title=self.mod.name, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=green, alpha=1)

                if self.is_adjusting:
                    if self.is_shift:
                        draw_label(context, title=" a little", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

                    elif self.is_ctrl and not self.is_radial:
                        draw_label(context, title=" a lot", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)
            
            if self.is_radial:
                self.offset += 18

                is_angle_snapping = self.is_adjusting and self.is_ctrl and not self.radial_full
                is_smol = self.is_adjusting and self.is_shift and not self.radial_full

                if self.radial_full:
                    angle = dynamic_format(360 / self.count, 1)
                    alpha = 0.2

                else:
                    precision = 0 if is_angle_snapping else 2 if is_smol else 1
                    angle = dynamic_format(degrees(self.snapped_angle if self.is_ctrl and self.is_adjusting else self.radial_angle), decimal_offset=precision)
                    alpha = 1

                dims = draw_label(context, title="Angle: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

                if self.radial_full or not self.center:
                    dims2 = (0, 0)

                elif self.center:
                    half_angle = dynamic_format(degrees(self.radial_angle / 2), decimal_offset=precision)
                    dims2 = draw_label(context, title=f"{half_angle}° ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.2)

                dims3 = draw_label(context, title=f"{angle}°", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white if is_angle_snapping else yellow if self.is_adjusting else white, alpha=alpha)

                if is_angle_snapping:
                    dims4 = draw_label(context, title=" Angle Snapping", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

                elif self.radial_full:
                    draw_label(context, title=" Full 360°", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

                else:
                    dims4 = (0, 0)

                if not self.radial_full and self.center:
                    draw_label(context, title=" Center Array", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + dims4[0], self.HUD_y)), offset=self.offset, center=False, color=normal, alpha=1)

                if self.warning:
                    self.offset += 18
                    draw_label(context, title="Warning: 360° Overshoot", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=red, alpha=1)

            else:
                self.offset += 18

                precision = 1
                distance = dynamic_format(self.distance, precision)

                dims = draw_label(context, title="Distance: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                    
                if self.center:
                    half_distance = dynamic_format(Vector(self.linear_offset).length / 2, precision)
                    dims2 = draw_label(context, title=f"{half_distance} ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.2)

                else:
                    dims2 = (0, 0)

                dims3 = draw_label(context, title=str(distance), coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=yellow if self.is_adjusting else white, alpha=1)

                if self.center:
                    draw_label(context, title=' Center Array', coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, color=normal, alpha=1)

            if not self.is_adjusting:

                self.offset += 18
                dims = draw_label(context, title="Count: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                draw_label(context, title=str(self.count), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

                if not (self.is_radial and self.radial_full):

                    self.offset += 18
                    dims = draw_label(context, title="Mode: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                    draw_label(context, title='FIT' if self.fit else 'ADD', coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=blue if self.fit else orange, alpha=1)

                if self.is_radial and self.radial_align:
                    self.offset += 18

                    title = 'Aligned'

                    if self.radial_full and not self.instances and self.weld:
                        title += ' + Welded'

                    draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

            if self.instances and not (not self.affect_instances and self.is_adjusting):   # NOTE: hide it when affecting instances is disabled while in adjust mode, so as to not give the impression, that you can toggle it in adjust mode)
                self.offset += 18

                dims = draw_label(context, title=f"Affect Related{': ' if self.affect_instances else ''}", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1 if self.affect_instances else 0.2)

                if self.affect_instances:
                    for mod in self.instances:
                        dims2 = draw_label(context, title=mod.name, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                        dims3 = draw_label(context, title=" on ", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.15)
                        draw_label(context, title=mod.id_data.name, coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.25)

                        self.offset += 18

    def draw_VIEW3D(self, context):
        if context.area == self.area:

            for idx, coords in enumerate(self.coords):

                if self.is_radial:
                    color = white if idx > 0 else yellow if self.radial_full else blue if self.fit else orange
                    alpha = 0.2 if idx > 0 else 1
                    
                    if self.radial_full:

                        if idx == 0:
                            draw_point(coords[0], size=14, color=color, alpha=alpha)

                        draw_point(coords[1], size=10, color=color, alpha=alpha)

                        if idx == 0:
                            draw_point(coords[1], size=5, color=white, alpha=alpha)

                        draw_line(coords[:2], width=2, color=color, alpha=alpha)

                        draw_points(coords[2:], size=6, color=color, alpha=alpha * 0.5)

                        for co in coords[2:]:
                            draw_line([coords[0], co], width=1, color=color, alpha=alpha * 0.25)

                        if self.count > 2:
                            coords = [coords[1], *coords[2:], coords[1]]
                            draw_line(coords, color=color, width=20, alpha=alpha*0.05)

                    else:
                        
                        if self.center:
                            if idx == 0:
                                draw_point(coords[0], size=14, color=normal, alpha=alpha)

                                draw_point(coords[1], size=14, color=normal, alpha=alpha)

                                draw_point(coords[1], size=5, color=white, alpha=alpha)

                                draw_line(coords[:2], width=2, color=normal, alpha=alpha)

                            draw_points(coords[2:4], size=10, color=color, alpha=alpha)

                            draw_lines([coords[0], coords[2], coords[0], coords[3]], width=2, color=color, alpha=alpha)

                            draw_points(coords[4:], size=6, color=color, alpha=alpha if self.fit else alpha * 0.5)

                            for co in coords[4:]:
                                draw_line([coords[0], co], width=1, color=color, alpha=alpha * 0.5)

                            if self.fit:
                                count = int(((self.count - 2) - (self.count % 2)) / 2)

                                if self.count % 2:
                                    coords = [coords[2], *coords[4:4+count], coords[1], *coords[4+count:], coords[3]]

                                else:
                                    coords = [coords[2], *coords[4:], coords[3]]

                            else:
                                count = int(((self.count - 2) + (self.count % 2)) / 2)

                                if self.count % 2:
                                    coords = [*coords[4:4+count], coords[1], *coords[4+count:]]

                                else:
                                    coords = [*coords[4:4+count], coords[2], coords[3], *coords[4+count:]]

                            draw_line(coords, color=color, width=20, alpha=alpha * 0.1 if self.fit else alpha * 0.05)

                        else:
                            if idx == 0:
                                draw_point(coords[0], size=14, color=color, alpha=alpha)

                            draw_points(coords[1:3], size=10, color=color, alpha=alpha)

                            if idx == 0:
                                draw_point(coords[1], size=5, color=white, alpha=alpha)

                            draw_lines([coords[0], coords[1], coords[0], coords[2]], width=2, color=color, alpha=alpha)

                            if self.count > 2:

                                draw_points(coords[3:], size=6, color=color, alpha=alpha if self.fit else alpha * 0.5)

                                for co in coords[3:]:
                                    draw_line([coords[0], co], width=1, color=color, alpha=alpha * 0.5)

                                coords = [coords[1], *coords[3:], coords[2]] if self.fit else [coords[1], coords[2], *coords[3:]]
                                draw_line(coords, color=color, width=20, alpha=alpha * 0.1 if self.fit else alpha * 0.05)

                            else:
                                draw_line([coords[1], coords[2]], color=color, width=20, alpha=alpha * 0.1 if self.fit else alpha * 0.05)

                else:
                    color = white if idx > 0 else blue if self.fit else orange
                    alpha = 0.2 if idx > 0 else 1

                    if self.center:

                        if idx == 0:
                            draw_point(coords[0], size=14, color=normal, alpha=alpha)

                        draw_points(coords[1:3], size=10, color=color, alpha=alpha)

                        draw_line(coords[1:3], width=2, color=color, alpha=alpha)

                        if idx == 0:
                            draw_vector(coords[1] - coords[0], origin=coords[0], color=normal, width=3, fade=True)
                            draw_vector(coords[2] - coords[0], origin=coords[0], color=normal, width=3, fade=True)

                        if idx == 0:
                            draw_point(coords[0], size=5, color=white, alpha=alpha)

                        if self.count > 2:

                            draw_points(coords[3:], size=6, color=color, alpha=alpha if self.fit else alpha * 0.5)

                            if not self.fit:
                                draw_line([coords[1], coords[-2]], width=1, color=color, alpha=alpha * 0.75)
                                draw_line([coords[2], coords[-1]], width=1, color=color, alpha=alpha * 0.75)

                    else:

                        draw_points(coords[:2], size=10, color=color, alpha=alpha)

                        if idx == 0:
                            draw_point(coords[0], size=5, color=white, alpha=alpha)

                        draw_line(coords[:2], width=2, color=color, alpha=alpha)

                        if self.count > 2:

                            draw_points(coords[2:], size=6, color=color, alpha=alpha if self.fit else alpha * 0.5)

                            if not self.fit:
                                draw_line([coords[1], coords[-1]], width=1, color=color, alpha=alpha * 0.75)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            if self.passthrough:
                self.passthrough = False

                self.factor = get_zoom_factor(context, depth_location=self.loc, scale=1, ignore_obj_scale=False)

            get_mouse_pos(self, context, event)
            wrap_mouse(self, context, x=self.is_adjusting)

        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        if not (self.is_radial and self.radial_full):
            self.update_adjust_mode(context, event, 'T')

        if self.is_multi_array and not self.is_adjusting:
            self.is_picking = self.is_ctrl

        if self.is_adjusting:
            if event.type in ['MOUSEMOVE', *ctrl, *shift]:
                mods = self.get_mods()
                delta_x = self.mouse_pos.x - self.last_mouse.x

                if self.is_radial:
                    divisor = get_mousemove_divisor(event, normal=5, shift=20, ctrl=5, sensitivity=50)

                    self.radial_angle += delta_x / divisor

                    if self.is_ctrl:

                        self.snapped_angle = self.get_snapped_angle(step=1 if self.is_shift else 5)

                        for mod in mods:
                            set_mod_input(mod, 'Angle', self.snapped_angle)

                    else:
                        for mod in mods:
                            set_mod_input(mod, 'Angle', self.radial_angle)

                    for mod in mods:
                        mod.id_data.update_tag()

                    self.warning = self.get_radial_overshoot_warning()

                else:
                    divisor = get_mousemove_divisor(event, normal=1, shift=20, ctrl=0.1, sensitivity=0.1)

                    init_dir = self.initial[self.active][self.mod]['offset']

                    self.distance += delta_x * (self.factor / divisor)

                    self.linear_offset = init_dir.normalized() * self.distance

                    if self.instances and self.affect_instances:
                        world_space_offset = self.active.matrix_world.to_3x3() @ Vector(self.linear_offset)

                    for mod in mods:
                        if mod == self.mod:
                            set_mod_input(mod, 'Offset', self.linear_offset)
                        
                        else:
                            mx = mod.id_data.matrix_world.inverted_safe().to_3x3()
                            set_mod_input(mod, 'Offset', mx @ world_space_offset)

                        mod.id_data.update_tag()

                self.coords = self.get_coords()

                force_ui_update(context)

                self.last_mouse = self.mouse_pos
            return {'RUNNING_MODAL'}

        elif self.is_picking:

            if scroll_up(event, key=True) or scroll_down(event, key=True):
                if scroll_up(event, key=True):
                    self.mod = step_list(self.mod, self.arrays, step=-1, loop=False)

                else:
                    self.mod = step_list(self.mod, self.arrays, step=1, loop=False)

                self.mod.is_active = True

                if not self.mod.show_viewport:
                    self.mod.show_viewport = True

                self.instances = self.get_instances()
                    
                self.count = get_mod_input(self.mod, 'Count')
                self.fit = get_mod_input(self.mod, 'Fit')
                self.center = get_mod_input(self.mod, 'Center')

                self.is_radial = is_radial_array(self.mod)
                    
                if self.weld:
                    remove_mod(self.mod)
                    self.mod = None

                if self.is_radial:
                    self.radial_angle = get_mod_input(self.mod, 'Angle')
                    self.radial_full = get_mod_input(self.mod, 'Full 360°')
                    self.radial_align = get_mod_input(self.mod, 'Align')
                    self.snapped_angle = self.get_snapped_angle(step=5)

                else:
                    self.linear_offset = get_mod_input(self.mod, 'Offset')

                self.coords = self.get_coords()

            return {'RUNNING_MODAL'}

        events = ['A', 'C', 'X']

        if self.is_radial:
            events.extend(['F', 'Q', 'S'])

            if self.radial_full:
                events.remove('A')
                events.remove('C')

                if self.radial_align and not self.instances:
                    events.append('W')

        if self.instances:
                events.append('R')

        if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):

            if scroll_up(event, key=True) or scroll_down(event, key=True):
                if scroll_down(event, key=True):
                    self.count -= 1

                else:
                    self.count += 1

            elif event.type == 'A' and event.value == 'PRESS':
                self.fit = not self.fit

            elif event.type == 'C' and event.value == 'PRESS':
                self.center = not self.center

            elif event.type == 'F' and event.value == 'PRESS':
                self.radial_full = not self.radial_full

                if not self.radial_full and self.weld:
                    remove_mod(self.weld)
                    self.weld = None
                    self.active.show_wire = False

            elif event.type == 'Q' and event.value == 'PRESS':
                self.radial_align = not self.radial_align

                if not self.radial_align and self.weld:
                    remove_mod(self.weld)
                    self.weld = False
                    self.active.show_wire = False

            elif event.type == 'S' and event.value == 'PRESS':
                modobj = get_mod_obj(self.mod)

                if modobj:
                    self.finish(context)

                    ensure_visibility(context, modobj)

                    if event.shift:

                        if self.instances and self.affect_instances:
                            for mod in self.instances:
                                hostobj = mod.id_data
                                ensure_visibility(context, hostobj)
                                hostobj.select_set(True)

                    else:
                        bpy.ops.object.select_all(action='DESELECT')

                    modobj.select_set(True)
                    context.view_layer.objects.active = modobj

                    if self.weld:
                        self.active.show_wire = False
                    return {'FINISHED'}

            elif event.type == 'X' and event.value == 'PRESS':
                self.finish(context)

                mods = self.get_mods()

                if self.is_radial:
                    modobj = get_mod_obj(self.mod)

                    if modobj and is_removable(modobj, ignore_users=mods, debug=False):
                        remove_obj(modobj)

                for mod in mods:
                    remove_mod(mod)

                if self.weld:
                    remove_mod(self.weld)
                    self.active.show_wire = False
                return {'FINISHED'}

            elif event.type == 'R' and event.value == 'PRESS':
                self.affect_instances = not self.affect_instances

                for mod in self.instances:
                    
                    if self.affect_instances:

                        if self.is_radial:
                            set_mod_input(mod, 'Angle', self.radial_angle)

                        else:
                            world_space_offset = self.active.matrix_world.to_3x3() @ Vector(self.linear_offset)
                            mx = mod.id_data.matrix_world.inverted_safe().to_3x3()
                            set_mod_input(mod, 'Offset', mx @ world_space_offset)
                        
                        self.set_array_props([mod])

                    else:
                        for hostobj, host_data in self.initial.items():
                            for m, mod_data in host_data.items():
                                if m == mod:
                                    set_mod_input(m, 'Count', mod_data['count'])
                                    set_mod_input(m, 'Fit', mod_data['fit'])
                                    set_mod_input(m, 'Center', mod_data['center'])

                                    if self.is_radial:
                                        set_mod_input(m, 'Angle', mod_data['angle'])
                                        set_mod_input(m, 'Full 360°', mod_data['full'])
                                        set_mod_input(m, 'Align', mod_data['align'])

                                    else:
                                        set_mod_input(m, 'Offset', mod_data['offset'])

                                    hostobj.update_tag()

                force_ui_update(context)

                self.coords = self.get_coords()
                return {'RUNNING_MODAL'}

            elif event.type == 'W' and event.value == 'PRESS':

                if self.weld:
                    remove_mod(self.weld)
                    self.weld = None

                else:
                    self.weld = add_weld(self.active, name='+ Weld', mode='ALL')
                    index = list(self.active.modifiers).index(self.mod) + 1
                    move_mod(self.weld, index)

                self.active.show_wire = bool(self.weld)

            self.set_array_props(self.get_mods())

            self.coords = self.get_coords()

            self.warning = self.get_radial_overshoot_warning()

            force_ui_update(context)

        if navigation_passthrough(event):
            self.passthrough = True
            return {'PASS_THROUGH'}

        elif event.type in ['LEFTMOUSE', 'SPACE'] and event.value == 'PRESS':
            self.finish(context)

            if self.weld:
                self.active.show_wire = False

            if self.is_hypermod_invoke:
                bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')
            
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC'] and event.value == 'PRESS':
            self.finish(context)

            for hostobj, host_data in self.initial.items():
                for mod, mod_data in host_data.items():

                    if mod == 'active':
                        hostobj.modifiers.active = mod_data

                    else:
                        set_mod_input(mod, 'Count', mod_data['count'])
                        set_mod_input(mod, 'Fit', mod_data['fit'])
                        set_mod_input(mod, 'Center', mod_data['center'])

                        if is_radial_array(mod):
                            set_mod_input(mod, 'Angle', mod_data['angle'])
                            set_mod_input(mod, 'Full 360°', mod_data['full'])
                            set_mod_input(mod, 'Align', mod_data['align'])

                        else:
                            set_mod_input(mod, 'Offset', mod_data['offset'])

                hostobj.update_tag()

            if self.weld:
                remove_mod(self.weld)
                self.active.show_wire 

            if self.is_hypermod_invoke:
                bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')
            return {'CANCELLED'}

        self.last_mouse = self.mouse_pos

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        finish_status(self)

        restore_gizmos(self)

    def invoke(self, context, event):
        self.active = context.active_object
        self.loc = self.active.matrix_world.to_translation()

        self.arrays = hyper_array_poll(context, self.active)

        if not self.arrays:
            force_obj_gizmo_update(context)
            return {'CANCELLED'}

        self.initial = self.get_initial_mod_states(context, debug=False)

        self.is_multi_array = len(self.arrays) > 1

        enabled_arrays = [mod for mod in self.arrays if mod.show_viewport]

        if enabled_arrays:
            self.mod = self.active.modifiers.active if self.active.modifiers.active in enabled_arrays else enabled_arrays[0]

        else:
            self.mod = self.active.modifiers.active if self.active.modifiers.active in self.arrays else self.arrays[0]

            self.mod.show_viewport = True

        self.mod.is_active = True

        self.instances = self.get_instances()

        self.count = get_mod_input(self.mod, 'Count')
        self.fit = get_mod_input(self.mod, 'Fit')
        self.center = get_mod_input(self.mod, 'Center')

        self.is_radial = is_radial_array(self.mod)
        self.weld = None

        if self.is_radial:
            self.radial_angle = get_mod_input(self.mod, 'Angle')
            self.radial_full = get_mod_input(self.mod, 'Full 360°')
            self.radial_align = get_mod_input(self.mod, 'Align')
            self.snapped_angle = self.get_snapped_angle(step=5)

        else:
            self.linear_offset = get_mod_input(self.mod, 'Offset')
            self.distance = Vector(self.linear_offset).length  # only used for modal adjustment, in combination with the stored initial offset vector, this allows for setting a negative distance

        self.is_shift = False
        self.is_ctrl = False
        self.is_alt = False

        self.is_adjusting = False
        self.is_picking = False
        self.is_moving = False

        self.warning = self.get_radial_overshoot_warning()

        self.coords = self.get_coords()

        self.factor = get_zoom_factor(context, depth_location=self.loc, scale=1, ignore_obj_scale=False)

        get_mouse_pos(self, context, event, init_offset=True)
        self.last_mouse = self.mouse_pos

        hide_gizmos(self, context)

        init_status(self, context, func=draw_adjust_array_status(self))

        force_ui_update(context)

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def get_initial_mod_states(self, context, debug=False):
        def get_instanced_arrays(context, uuid='', debug=False):
            instances = []

            if uuid:
                if debug:
                    print("\nlooking for mod instances using uuid:", uuid)

                for obj in bpy.data.objects:
                    if obj == self.active:
                        continue

                    arrays = hyper_array_poll(context, obj)

                    for mod in arrays:
                        if get_mod_input(mod, 'UUID') == uuid:
                            instances.append(mod)

            if debug:
                for mod in instances:
                    print(" found insrtanced mod", mod.name, "on", mod.id_data.name)

            return instances

        initial = {}

        for mod in self.arrays:
            uuid = get_mod_input(mod, 'UUID')
            instances = get_instanced_arrays(context, uuid=uuid)

            if debug:
                print(mod.name)
                print(" uuid:", uuid)
                print(" instances:", [f"'{mod.name}' on '{mod.id_data.name}'" for mod in instances])

            for m in [mod] + instances:
                hostobj = m.id_data

                data = {'index': list(hostobj.modifiers).index(m),
                        'name': m.name,

                        'count': get_mod_input(m, 'Count'),
                        'fit': get_mod_input(m, 'Fit'),
                        'center': get_mod_input(m, 'Center'),

                        'instances': instances if m == mod else None}

                if is_radial_array(m):
                    data['angle'] = get_mod_input(m, 'Angle')
                    data['full'] = get_mod_input(m, 'Full 360°')
                    data['align'] = get_mod_input(m, 'Align')

                else:
                    data['offset'] = Vector(get_mod_input(m, 'Offset'))

                if hostobj in initial:
                    initial[hostobj][m] = data

                else:
                    initial[hostobj] = {m: data, 
                                       'active': hostobj.modifiers.active}

        if debug:
            printd(initial)

        return initial

    def get_instances(self):
        return self.initial[self.active][self.mod]['instances']

    def get_radial_overshoot_warning(self):
        if self.is_radial and not self.radial_full:
            angle = self.snapped_angle if self.is_adjusting and self.is_ctrl else self.radial_angle

            if self.fit:
                return abs(degrees(angle)) > 360
            else:
                return abs(degrees(angle)) * (self.count - 1) > 360

    def get_mods(self):
        if self.instances and self.affect_instances:
            return [self.mod] + self.instances

        else:
            return [self.mod]

    def get_snapped_angle(self, step=5):
        dangle = degrees(self.radial_angle)
        mod = dangle % step

        return radians(dangle + (step - mod)) if mod >= (step / 2) else radians(dangle - mod)

    def get_coords(self):
        all_coords = []

        for mod in self.get_mods():
            hostobj = mod.id_data
            loc, rot, _ = hostobj.matrix_world.decompose()

            if self.is_radial:
                empty = get_mod_obj(self.mod)

                if empty:
                    mod_angle = self.snapped_angle if self.is_ctrl else self.radial_angle

                    empty_mx = empty.matrix_world.copy()
                    empty_mx_inv = empty_mx.inverted_safe()
                    empty_loc, empty_rot, _ = empty_mx.decompose()

                    coords = [empty_loc]

                    coords.append(loc)

                    if self.radial_full:
                        for i in range(self.count - 1):
                            angle = (i + 1) * (radians(360) / self.count)

                            instance_rot = Quaternion(Vector((0, 1, 0)), angle).to_matrix().to_4x4()
                            instance_loc = empty_mx @ instance_rot @ empty_mx_inv @ loc

                            coords.append(instance_loc)

                    else:

                        if self.center:
                            
                            angle = -mod_angle + (mod_angle / 2)

                            instance_rot = Quaternion(Vector((0, 1, 0)), angle).to_matrix().to_4x4()
                            instance_loc = empty_mx @ instance_rot @ empty_mx_inv @ loc
                            coords.append(instance_loc)

                            angle = mod_angle - (mod_angle / 2)
                            instance_rot = Quaternion(Vector((0, 1, 0)), angle).to_matrix().to_4x4()
                            instance_loc = empty_mx @ instance_rot @ empty_mx_inv @ loc
                            coords.append(instance_loc)

                            if self.count > 2:

                                if self.fit:
                                    count = int(((self.count - 2) - (self.count % 2)) / 2)

                                    for i in range(count):
                                        angle = (i + 1) * (mod_angle / (self.count - 1))

                                        instance_rot = Quaternion(Vector((0, 1, 0)), angle).to_matrix().to_4x4()
                                        instance_loc = empty_mx @ instance_rot @ empty_mx_inv @ coords[2]
                                        coords.append(instance_loc)

                                    for i in range(count):

                                        angle = (count - i) * (mod_angle / (self.count - 1))

                                        instance_rot = Quaternion(Vector((0, 1, 0)), -angle).to_matrix().to_4x4()
                                        instance_loc = empty_mx @ instance_rot @ empty_mx_inv @ coords[3]
                                        coords.append(instance_loc)

                                else:

                                    count = int(((self.count - 2) + (self.count % 2)) / 2)

                                    for i in range(count):
                                        angle = (count - i) * mod_angle
                                        
                                        if self.count % 2:
                                            instance_rot = Quaternion(Vector((0, 1, 0)), -angle).to_matrix().to_4x4()
                                            instance_loc = empty_mx @ instance_rot @ empty_mx_inv @ loc
                                            coords.append(instance_loc)

                                        else: 
                                            instance_rot = Quaternion(Vector((0, 1, 0)), -angle).to_matrix().to_4x4()
                                            instance_loc = empty_mx @ instance_rot @ empty_mx_inv @ coords[2]
                                            coords.append(instance_loc)

                                    for i in range(count):
                                        angle = (i + 1) * mod_angle

                                        if self.count % 2:
                                            instance_rot = Quaternion(Vector((0, 1, 0)), angle).to_matrix().to_4x4()
                                            instance_loc = empty_mx @ instance_rot @ empty_mx_inv @ loc
                                            coords.append(instance_loc)

                                        else: 
                                            instance_rot = Quaternion(Vector((0, 1, 0)), angle).to_matrix().to_4x4()
                                            instance_loc = empty_mx @ instance_rot @ empty_mx_inv @ coords[3]
                                            coords.append(instance_loc)

                        else:

                            instance_rot = Quaternion(Vector((0, 1, 0)), mod_angle).to_matrix().to_4x4()

                            instance_loc = empty_mx @ instance_rot @ empty_mx_inv @ loc
                            coords.append(instance_loc)

                            if self.count > 2:
                                count = self.count - 2

                                for i in range(count):
                                    angle = (i + 1) * (mod_angle / (count + 1)) if self.fit else mod_angle * (i + 2)

                                    instance_rot = Quaternion(Vector((0, 1, 0)), angle).to_matrix().to_4x4()
                                    instance_loc = empty_mx @ instance_rot @ empty_mx_inv @ loc

                                    coords.append(instance_loc)

            else:

                move_dir = self.active.matrix_world.to_3x3() @ Vector(self.linear_offset)

                if self.center:

                    coords = [loc]

                    coords.extend([loc - move_dir / 2, loc + move_dir / 2])

                    if self.count > 2:

                        if self.fit:
                            gap_dir = move_dir / ( self.count - 1)

                            count = int(((self.count - 2) - (self.count % 2)) / 2)

                            for i in range(count):
                                coords.append(coords[2] - gap_dir * (i + 1))
                                coords.append(coords[1] + gap_dir * (i + 1))

                        else:
                            count = int(((self.count - 2) + (self.count % 2)) / 2)

                            for i in range(count):

                                if self.count % 2:
                                    coords.append(loc - move_dir * (i + 1))
                                    coords.append(loc + move_dir * (i + 1))

                                else: 
                                    coords.append(coords[1] - move_dir * (i + 1))
                                    coords.append(coords[2] + move_dir * (i + 1))

                else:

                    coords = [loc, loc + move_dir]

                    if self.count > 2:
                        if self.fit:
                            gap_dir = move_dir / (self.count - 1)
                            
                            for i in range(self.count - 2):
                                coords.append(loc + gap_dir * (i + 1))

                        else:

                            for i in range(self.count - 2):
                                coords.append(loc +  move_dir * (i + 2))

            all_coords.append(coords)

        return all_coords

    def update_adjust_mode(self, context, event, key):
        is_key(self, event, key, debug=False)

        if event.type == key:
            if event.value == 'PRESS' and not self.is_adjusting:
                context.window.cursor_set('SCROLL_X')

                force_ui_update(context)

                if not self.is_radial:
                    sign = -1 if self.distance < 0 else 1
                    self.distance = sign * Vector(get_mod_input(self.mod, 'Offset')).length

            elif event.value == 'RELEASE':
                context.window.cursor_set('DEFAULT')

                if self.is_radial and not self.radial_full and self.is_ctrl:
                    self.radial_angle = self.snapped_angle

                force_ui_update(context)

        self.is_adjusting = getattr(self, f"is_{key.lower()}")

    def set_array_props(self, mods):
        for mod in mods:
            set_mod_input(mod, 'Count', self.count)
            set_mod_input(mod, 'Fit', self.fit)
            set_mod_input(mod, 'Center', self.center)

            if self.is_radial:
                set_mod_input(mod, 'Full 360°', self.radial_full)
                set_mod_input(mod, 'Align', self.radial_align)

            mod.id_data.update_tag()
