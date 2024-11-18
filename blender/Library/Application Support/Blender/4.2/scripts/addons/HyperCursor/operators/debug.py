from math import factorial, sqrt
import bpy
from bpy.props import IntProperty
import bmesh
from mathutils import Vector, Matrix
import numpy as np
from .. utils.math import get_face_center
from .. utils.mesh import get_coords
from .. utils.draw import draw_line, draw_lines, draw_point, draw_vector, draw_vectors, draw_mesh_wire, draw_circle
from .. utils.modifier import get_mod_obj, get_mod_objects
from .. utils.system import printd
from .. colors import yellow, green, red, normal, blue, white

class Button(bpy.types.Operator):
    bl_idname = "machin3.button"
    bl_label = "MACHIN3: button"
    bl_description = "Button"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index")

    @classmethod
    def poll(cls, context):
        return False

    def execute(self, context):
        active = context.active_object

        return {'FINISHED'}

class RepulseTest(bpy.types.Operator):
    bl_idname = "machin3.repulse_test"
    bl_label = "MACHIN3: Repulse Test"
    bl_description = "Button"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active = context.active_object
        self.mx = active.matrix_world

        distance = 0.1
        iterations = 10

        bm = bmesh.new()
        bm.from_mesh(active.data)
        bm.verts.ensure_lookup_table()

        collected_verts = []

        for i in range(iterations):
            repulsed = self.repulse(bm, collected_verts, distance=distance, first=i==0)

            if not repulsed:
                print(f"breaking after {i}th iteration")
                break

        for v in collected_verts:
            draw_circle(self.mx @ v.co, radius=distance / 2, color=green, alpha=0.5, modal=False)

        bm.to_mesh(active.data)
        bm.free()

        context.area.tag_redraw()
        return {'FINISHED'}

    def repulse(self, bm, collected_verts, distance=0.1, first=True):
        radius = distance / 2

        coords = [v.co for v in bm.verts]
        indices = [v.index for v in bm.verts]

        overlapping_points = {}

        for idx, co in zip(indices, coords):

            repulse_from = []

            for idx2, co2 in zip(indices, coords):
                if idx != idx2:
                    co_dir = (co2 - co)

                    if co_dir.length < distance:
                        repulse_from.append(co2)

            if repulse_from:
                overlapping_points[idx] = repulse_from
                color = red
            else:
                color = white

            if first:
                draw_circle(self.mx @ co, radius=radius, color=color, alpha=0.5, modal=False)

        if overlapping_points:

            repulsed_verts = {}

            for idx, coords in overlapping_points.items():
                v = bm.verts[idx]

                if v not in collected_verts:
                    collected_verts.append(v)

                print(idx)

                for co in coords:
                    print("", co)
                
                move_dir = Vector((0, 0, 0))
                
                for co in coords:
                    repulse_dir = v.co - co
                    move_dir += repulse_dir.normalized() * (distance - repulse_dir.length)

                move_dir = move_dir / sqrt((len(coords) + 2.5))
                draw_vector(move_dir, origin=v.co.copy(), mx=self.mx, fade=True, modal=False)

                repulse_co = v.co + move_dir
                draw_point(repulse_co, mx=self.mx, color=green, size=2, modal=False)

                repulsed_verts[v] = v.co + move_dir

            for v, co in repulsed_verts.items():
                print(v, co)
                v.co = co

            return True
        return False

class DrawTests(bpy.types.Operator):
    bl_idname = "machin3.draw_tests"
    bl_label = "MACHIN3: Draw Tests"
    bl_description = "Draw Tests"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active = context.active_object

        if active:
            mx = active.matrix_world
            loc, rot, _ = mx.decompose()

            coords = [Vector((0, 0, 0)), Vector((1, 1, 1)), Vector((2, 2, 1)), Vector((5, -1, 5))]
            draw_line(coords, mx=mx, color=green, alpha=0.3, width=2, xray=True, modal=False)
            
            coords2 = [co - Vector((0, 1, 0)) for co in coords]
            draw_lines(coords2, mx=mx, color=red, alpha=0.5, width=1, xray=True, modal=False)
            
            vector = Vector((-1, -1, 1))
            origin = Vector((0, 0, 0))
            draw_vector(vector, origin=origin, mx=mx, color=normal, fade=True, width=2, modal=False)

            vectors = [Vector((-1, -1, 1)), Vector((1, 1, -1))]
            origins = [Vector((1, 1, 1)), Vector((3, 3, 3))]
            draw_vectors(vectors, mx=mx, origins=origins, color=normal, fade=True, width=2, modal=False)

            batch = get_coords(active.data, mx=active.matrix_world, offset=0.01, edge_indices=True)
            draw_mesh_wire(batch, color=yellow, width=1, alpha=0.5, xray=True, modal=False)
        
            draw_circle(loc, rot, radius=75, width=2, segments='AUTO', color=green, alpha=0.5, modal=False, screen=False)

        screen_coords = [Vector((20, 20, 0)), Vector((500, 500, 0))]
        draw_line(screen_coords, color=blue, alpha=0.7, width=2, xray=True, modal=False, screen=True)

        draw_circle(loc=Vector((500, 500, 0)), radius=75, width=2, segments='AUTO', color=green, alpha=0.5, modal=False, screen=True)

        context.area.tag_redraw()
        return {'FINISHED'}
