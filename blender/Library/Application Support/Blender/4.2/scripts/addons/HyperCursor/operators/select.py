import bpy
from bpy.props import IntProperty, BoolProperty 
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d
import bmesh
from mathutils import Vector
from mathutils.geometry import intersect_line_plane, intersect_line_line
import sys
from .. utils.select import clear_hyper_edge_selection, get_edges, clear_hyper_face_selection, get_faces, invert_hyper_face_selection, invert_hyper_edge_selection
from .. utils.draw import draw_point, draw_vector, draw_line
from .. utils.system import printd
from .. utils.ui import force_geo_gizmo_update
from .. utils.bmesh import ensure_select_layers
from .. colors import yellow, red

class SelectEdge(bpy.types.Operator):
    bl_idname = "machin3.select_edge"
    bl_label = "MACHIN3: Select Edge"
    bl_description = "(De)Select Edge\nSHIFT: Loop (De)Select\nCTRL: Ring (De)Select"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Edge accociated with Gizmo, that is to be (un)selected")

    loop: BoolProperty(name="Loop Select Edges", default=False)
    min_angle: IntProperty(name="Min Angle", default=60, min=0, max=180)
    prefer_center_of_three: BoolProperty(name="Prefer Center of 3 Edges", default=True)
    ring: BoolProperty(name="Ring Select Edges", default=False)
    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.active_object

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)

        if self.loop:
            column.prop(self, 'prefer_center_of_three', toggle=True)
            column.prop(self, 'min_angle', toggle=True)

    def invoke(self, context, event):
        self.loop = event.shift
        self.ring = event.ctrl

        print("hello invoking")
        return self.execute(context)

    def execute(self, context):
        active = context.active_object

        bm = bmesh.new()
        bm.from_mesh(active.data)
        bm.normal_update()
        bm.edges.ensure_lookup_table()

        edge_slayer = ensure_select_layers(bm)[0]

        edge = bm.edges[self.index]

        edges = get_edges(edge, loop=self.loop, min_angle=180 - self.min_angle, prefer_center_of_three=self.prefer_center_of_three, ring=self.ring)

        for e in edges:
            e[edge_slayer] = 1 if e[edge_slayer] == 0 else 0

        bm.to_mesh(active.data)
        bm.free()

        force_geo_gizmo_update(context)

        return {'FINISHED'}

class ClearEdgeSelection(bpy.types.Operator):
    bl_idname = "machin3.clear_edge_selection"
    bl_label = "MACHIN3: Clear Edge Selection"
    bl_description = "(De)Select All Edges\nALT: Invert Selection"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.active_object

    def invoke(self, context, event):
        active = context.active_object

        if event.alt:
            invert_hyper_edge_selection(context, active)

        else:
            clear_hyper_edge_selection(context, active)

        return {'FINISHED'}

class SelectFace(bpy.types.Operator):
    bl_idname = "machin3.select_face"
    bl_label = "MACHIN3: Select Face"
    bl_description = "(De)Select Face\nSHIFT: Loop (De)Select"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Edge accociated with Gizmo, that is to be (un)selected")

    loop: BoolProperty(name="Loop Select Faces", default=False)
    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.active_object

    def invoke(self, context, event):
        self.loop = event.shift
        return self.execute(context)

    def execute(self, context):
        active = context.active_object
        mx = active.matrix_world

        bm = bmesh.new()
        bm.from_mesh(active.data)
        bm.normal_update()
        bm.faces.ensure_lookup_table()

        slayer = bm.faces.layers.int.get('HyperFaceSelect')

        if not slayer:
            slayer = bm.faces.layers.int.new('HyperFaceSelect')

        face = bm.faces[self.index]

        if self.loop and len(face.verts) == 4:

            edge = self.get_closest_edge(context, mx, face, debug=False)

            faces = get_faces(face, edge, loop=True)

        else:
            faces = [face]

        for f in faces:
            f[slayer] = 1 if f[slayer] == 0 else 0

        bm.to_mesh(active.data)
        bm.free()

        force_geo_gizmo_update(context)

        return {'FINISHED'}

    def get_closest_edge(self, context, mx, face, debug=False):
        mousepos = Vector((*context.window_manager.HC_mouse_pos_region, 0))

        if debug:
            draw_point(mousepos, modal=False, screen=True)

        view_origin = region_2d_to_origin_3d(context.region, context.region_data, mousepos)
        view_dir = region_2d_to_vector_3d(context.region, context.region_data, mousepos)

        face_center = mx @ face.calc_center_median()

        i = intersect_line_plane(view_origin, view_origin + view_dir, face_center, mx.to_3x3() @ face.normal)
        if debug:
            print(i)

        if i:
            if debug:
                draw_point(i, color=yellow, modal=False)

            select_direction_dir = i - face_center
            if debug:
                print(select_direction_dir)
                draw_vector(select_direction_dir, origin=face_center, color=red, modal=False)

            edges = {e: sys.maxsize for e in face.edges}

            dir_coords = [face_center, i]

            for e in edges:
                if debug:
                    print("intersecting edge", e)

                edge_coords = [mx @ v.co for v in e.verts]

                intersections = intersect_line_line(*edge_coords, *dir_coords)

                if intersections:
                    edge_i = intersections[1]

                    if debug:
                        print(" intersected edge", e.index, "at", edge_i)
                        draw_line((face_center, edge_i.copy()), color=yellow, modal=False)

                    edges[e] = (edge_i - i).length

            if debug:
                printd(edges)

            return min(edges.items(), key=lambda x: x[1])[0]

class ClearFaceSelection(bpy.types.Operator):
    bl_idname = "machin3.clear_face_selection"
    bl_label = "MACHIN3: Clear Face Selection"
    bl_description = "(De)Select All Faces\nALT: Invert Selection"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.active_object

    def invoke(self, context, event):
        active = context.active_object

        if event.alt:
            invert_hyper_face_selection(context, active)

        else:
            clear_hyper_face_selection(context, active)

        force_geo_gizmo_update(context)

        return {'FINISHED'}
