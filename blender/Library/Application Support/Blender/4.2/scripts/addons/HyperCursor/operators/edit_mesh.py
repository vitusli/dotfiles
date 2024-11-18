import bpy
from bpy.props import FloatProperty, EnumProperty, BoolProperty
import bmesh
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_line_line
from .. utils.draw import draw_point, draw_line, draw_init, draw_label
from .. utils.mesh import get_bbox
from .. utils.object import set_obj_origin
from .. utils.math import get_loc_matrix, get_rot_matrix, get_sca_matrix, average_locations
from .. utils.registration import get_addon
from .. utils.ui import force_geo_gizmo_update, get_mouse_pos, init_status, finish_status, force_ui_update
from .. utils.view import get_view_origin_and_dir
from .. items import axis_direction_items
from .. colors import red, green, blue, white, yellow

meshmachine = None

def draw_scale_mesh_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        axis = 'X' if op.direction in ['XMIN', 'XMAX'] else 'Y' if op.direction in ['YMIN', 'YMAX'] else 'Z'
        space = 'Cursor' if op.cursor_space_rotation else 'Object'

        row.label(text=f"Scale Mesh on {space} {axis}")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Confirm")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        if not op.cursor_space_rotation:

            row.label(text="", icon='EVENT_ALT')
            row.label(text=f"Origin: {'Cursor' if op.cursor_space_location else 'Object'}")

        if op.can_origin_change:
            row.label(text="", icon='EVENT_C')
            row.label(text=f"Keep Origin Centered: {op.keep_origin_centered}")

    return draw

class ScaleMesh(bpy.types.Operator):
    bl_idname = "machin3.scale_mesh"
    bl_label = "MACHIN3: Scale Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(name="Scale Axis Direction", items=axis_direction_items, default='XMIN')
    cursor_space_location: BoolProperty(name="Scale in Cursor Space (ignoring cursor orientation)", default=False)
    cursor_space_rotation: BoolProperty(name="Scale in Cursor Space (using cursor orientation)", default=False)
    amount: FloatProperty(name="Scale Amount")

    uniform_scale: BoolProperty(default=False)
    plane_scale: BoolProperty(default=False)
    keep_origin_centered: BoolProperty(default=False)
    cah_origin_change: BoolProperty(default=True)
    @classmethod
    def poll(cls, context):
        active = context.active_object

        if active and active.select_get() and active.HC.ishyper:
            if context.mode == 'EDIT_MESH':
                bm = bmesh.from_edit_mesh(active.data)
                return [v for v in bm.verts if v.select]
            return context.mode == 'OBJECT'

    @classmethod
    def description(cls, context, properties):
        content = "Active Object's Mesh" if context.mode == 'OBJECT' else 'Mesh Selection'
        desc = f"Scale {content} along {'Cursor' if properties.cursor_space_rotation else 'Object'}'s {'X' if properties.direction in ['XMIN', 'XMAX'] else 'Y' if properties.direction in ['YMIN', 'YMAX'] else 'Z'}"
        desc += "\nALT: Repeat Scale using previous Amount"
        desc += "\nSHIFT: Plane Scaling"
        desc += "\nCTRL: Uniform Scaling"
        return desc

    def draw_VIEW3D(self, context):
        if context.area == self.area:

            color = (1, 0, 0) if self.direction in ['XMIN', 'XMAX'] else (0, 1, 0) if self.direction in ['YMIN', 'YMAX'] else (0, 0, 1)
            draw_line([self.init_loc, self.loc], color=color, width=2, alpha=0.3)

            mx = self.cmx if self.cursor_space_rotation or self.cursor_space_location else self.mx
            draw_point(mx.to_translation(), color=yellow)

            if self.can_origin_change and self.keep_origin_centered:
                draw_line([self.origin, self.origin_preview], mx=self.mx, color=green, alpha=0.5)
                draw_point(self.origin_preview, mx=self.mx, color=green, alpha=1)

    def draw_HUD(self, context):
        if context.area == self.area:

            draw_init(self)

            content = "Mesh" if context.mode == 'OBJECT' else "Mesh Selection"
            direction = f"{'Cursor' if self.cursor_space_rotation else 'Object'}'s"

            dims = draw_label(context, title=f"Scaling {content} ", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)
            dims2 = draw_label(context, title=f"in ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=white, alpha=0.5)
            dims3 = draw_label(context, title=f"{direction} ", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, color=white, alpha=1)

            if self.uniform_scale:
                axes_colors = [('X', red), ('Y', green), ('Z', blue)]

            elif self.plane_scale:

                if self.direction in ['XMIN', 'XMAX']:
                    axes_colors = [('Y', green), ('Z', blue)]

                elif self.direction in ['YMIN', 'YMAX']:
                    axes_colors = [('X', red), ('Z', blue)]

                else:
                    axes_colors = [('X', red), ('Y', green)]

            else:
                axis = f"{'X' if self.direction in ['XMIN', 'XMAX'] else 'Y' if self.direction in ['YMIN', 'YMAX'] else 'Z'}"
                color = red if axis == 'X' else green if axis == 'Y' else blue
                axes_colors = [(axis, color)]

            d = 0

            for axis, color in axes_colors:
                dimensions = draw_label(context, title=f"{axis}", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + d, self.HUD_y)), center=False, color=color, alpha=1)
                d += dimensions[0]

            self.offset += 18

            across = f"{'Cursor' if self.cursor_space_rotation or self.cursor_space_location else 'Object Origin'}"
            dims = draw_label(context, title=f"across ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)
            draw_label(context, title=f"{across}", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

            if self.keep_origin_centered:
                self.offset += 18

                draw_label(context, title="Center Origin", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=green, alpha=1)

    def modal(self, context, event):
        context.area.tag_redraw()

        self.cursor_space_location = event.alt

        events = ['MOUSEMOVE']

        if self.can_origin_change:
            events.append('C')

        if event.type in events:

            if event.type == 'MOUSEMOVE':
                get_mouse_pos(self, context, event)

                self.loc = self.get_mouse_normal_intersection(context, self.mouse_pos)

                if self.loc:
                    self.scale_vector = self.loc - self.init_loc

                    self.amount = self.scale_vector.length if self.scale_vector.dot(self.gzm_normal) > 0 else - self.scale_vector.length

                self.scale_mesh(context)

            if self.can_origin_change and event.type == 'C' and event.value == 'PRESS':
                self.keep_origin_centered = not self.keep_origin_centered

                force_ui_update(context)

            if self.keep_origin_centered:
                self.origin_preview = average_locations(get_bbox(self.active.data)[0])

        if event.type in {'LEFTMOUSE', 'SPACE'}:
            self.finish(context)

            if self.can_origin_change and self.keep_origin_centered:
                self.change_origin()

            force_geo_gizmo_update(context)

            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel_modal(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def cancel_modal(self, context):
        if context.mode == 'OBJECT':
            self.initbm.to_mesh(context.active_object.data)
            self.initbm.free()

        elif context.mode == 'EDIT_MESH':
            for v, co in self.verts:
                v.co = co

            bmesh.update_edit_mesh(self.active.data)

        self.finish(context)

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

        context.scene.HC.draw_HUD = True

        force_ui_update(context)

    def invoke(self, context, event):
        self.active = context.active_object
        self.mx = self.active.matrix_world
        self.cmx = context.scene.cursor.matrix

        self.can_origin_change = context.mode == 'OBJECT' and (self.active.data.users == 1) and not any(mod.type in ['ARRAY'] for mod in self.active.modifiers)

        if self.can_origin_change:
            self.origin = self.mx.inverted_safe() @ self.mx.to_translation()
            self.origin_preview = self.origin

        if context.mode == 'OBJECT':
            self.initbm = bmesh.new()
            self.initbm.from_mesh(self.active.data)

        elif context.mode == 'EDIT_MESH':
            self.bm = bmesh.from_edit_mesh(self.active.data)
            self.bm.normal_update()
            self.verts = [(v, v.co.copy()) for v in self.bm.verts if v.select]

        self.gzm = None

        if context.gizmo_group:

            if self.cursor_space_rotation:
                self.gzm = getattr(context.gizmo_group, 'scale_x' if self.direction == 'XMIN' else 'scale_y' if self.direction == 'YMIN' else 'scale_z', None)

                self.gzm_origin = self.gzm.matrix_world.to_translation()
                self.gzm_normal = - self.gzm.matrix_world.to_3x3().col[2].normalized()

            else:
                self.gzm = getattr(context.gizmo_group, self.direction.lower(), None)

                self.gzm_origin = self.gzm.matrix_world.to_translation()
                self.gzm_normal = self.gzm.matrix_world.to_3x3().col[2].normalized()

        if self.gzm:
            self.dimensions = get_bbox(self.active.data)[2]

        if not self.gzm:
            self.gzm_origin, self.gzm_normal, self.dimensions = self.get_gizmo_location_and_normal()

        if event.alt:

            self.scale_vector = self.gzm_normal * self.amount

            self.scale_mesh(context)

            if self.can_origin_change and self.keep_origin_centered:
                self.change_origin()

            force_ui_update(context)

            return {'FINISHED'}

        get_mouse_pos(self, context, event)

        self.init_loc = self.get_mouse_normal_intersection(context, self.mouse_pos)
        self.loc = self.init_loc

        if self.init_loc:
            self.uniform_scale = False
            self.plane_scale = False

            if event.ctrl:
                self.uniform_scale = True
            elif event.shift:
                self.plane_scale = True

            self.scale_vector = self.loc - self.init_loc

            context.scene.HC.draw_HUD = False

            self.cursor_space_location = event.alt

            init_status(self, context, func=draw_scale_mesh_status(self))

            force_ui_update(context)

            self.area = context.area
            self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
            self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        return {'CANCELLED'}

    def get_mouse_normal_intersection(self, context, mouse_pos):
        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)

        i = intersect_line_line(self.gzm_origin, self.gzm_origin + self.gzm_normal, view_origin, view_origin + view_dir)

        if i:
            return i[0]

    def get_gizmo_location_and_normal(self):
        _, centers, dimensions = get_bbox(self.active.data)

        if self.direction == 'XMIN':
            loc = self.mx @ centers[0]
            normal = self.mx.to_quaternion() @ (centers[0] - centers[1]).normalized()

        elif self.direction == 'XMAX':
            loc = self.mx @ centers[1]
            normal = self.mx.to_quaternion() @ (centers[1] - centers[0]).normalized()

        elif self.direction == 'YMIN':
            loc = self.mx @ centers[2]
            normal = self.mx.to_quaternion() @ (centers[2] - centers[3]).normalized()

        elif self.direction == 'YMAX':
            loc = self.mx @ centers[3]
            normal = self.mx.to_quaternion() @ (centers[3] - centers[2]).normalized()

        elif self.direction == 'ZMIN':
            loc = self.mx @ centers[4]
            normal = self.mx.to_quaternion() @ (centers[4] - centers[5]).normalized()

        elif self.direction == 'ZMAX':
            loc = self.mx @ centers[5]
            normal = self.mx.to_quaternion() @ (centers[5] - centers[4]).normalized()

        return loc, normal, dimensions

    def scale_mesh(self, context):
        if context.mode == 'OBJECT':
            bm = self.initbm.copy()
            bm.normal_update()

        elif context.mode == 'EDIT_MESH':
            for v, co in self.verts:
                v.co = co

        if self.direction in ['XMIN', 'YMIN', 'ZMIN']:
            self.scale_vector.negate()

        if not self.cursor_space_rotation:
            scale_vector = self.mx.to_3x3().inverted_safe() @ self.scale_vector

        else:
            scale_vector = context.scene.cursor.matrix.inverted_safe().to_quaternion() @ (get_sca_matrix(self.mx.inverted_safe().to_scale()) @ self.scale_vector)

        if self.cursor_space_rotation:
            dimension = sum(self.dimensions) / 3
            div = dimension / 2

            scale_vector = scale_vector / div

        else:

            if self.direction in ['XMIN', 'XMAX']:
                dimension = self.dimensions[0]
                origin_distance = (self.mx.inverted_safe() @ self.gzm_origin)[0]

            elif self.direction in ['YMIN', 'YMAX']:
                dimension = self.dimensions[1]
                origin_distance = (self.mx.inverted_safe() @ self.gzm_origin)[1]

            elif self.direction in ['ZMIN', 'ZMAX']:
                dimension = self.dimensions[2]
                origin_distance = (self.mx.inverted_safe() @ self.gzm_origin)[2]

            if origin_distance == 0:
                origin_distance = dimension

            if self.direction in ['XMIN', 'YMIN', 'ZMIN']:
                div = dimension / - (dimension / origin_distance)
            else:
                div = dimension / (dimension / origin_distance)

            scale_vector = scale_vector / div

        if self.cursor_space_rotation:
            space = context.scene.cursor.matrix.inverted_safe() @ self.mx

        elif self.cursor_space_location:
            loc, _, sca = context.scene.cursor.matrix.decompose()
            rot = self.mx.to_quaternion()
            cspace = get_loc_matrix(loc) @ get_rot_matrix(rot) @ get_sca_matrix(sca)
            space = cspace.inverted_safe() @ self.mx

        else:
            space = Matrix()

        if self.uniform_scale or self.plane_scale:

            if self.uniform_scale:
                scale_vector = Vector((scale_vector.length, scale_vector.length, scale_vector.length))

            elif self.plane_scale:
                if self.direction in ['XMIN', 'XMAX']:
                    scale_vector = Vector((0, scale_vector.length, scale_vector.length))

                elif self.direction in ['YMIN', 'YMAX']:
                    scale_vector = Vector((scale_vector.length, 0, scale_vector.length))

                elif self.direction in ['ZMIN', 'ZMAX']:
                    scale_vector = Vector((scale_vector.length, scale_vector.length, 0))

            if self.amount < 0:
                scale_vector.negate()

        if context.mode == 'OBJECT':
            bmesh.ops.scale(bm, vec=Vector((1, 1, 1)) + scale_vector, space=space, verts=bm.verts)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

            bm.to_mesh(self.active.data)
            bm.free()

        elif context.mode == 'EDIT_MESH':
            bmesh.ops.scale(self.bm, vec=Vector((1, 1, 1)) + scale_vector, space=space, verts=[v for v, _ in self.verts])
            bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
            bmesh.update_edit_mesh(self.active.data)

    def change_origin(self):
        global meshmachine, meshmachine_version

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        bbox = get_bbox(self.active.data)[0]
        center = self.mx @ average_locations(bbox)

        _, rot, sca = self.mx.decompose()
        mx = Matrix.LocRotScale(center, rot, sca)

        set_obj_origin(self.active, mx, meshmachine=meshmachine, force_quat_mode=True)
