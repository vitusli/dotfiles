import bpy
from bpy.props import EnumProperty, BoolProperty, FloatProperty, IntProperty, StringProperty
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d
import bmesh
from math import degrees, radians, sin, cos
from mathutils import Vector, Quaternion, Matrix
from mathutils.geometry import intersect_line_line, intersect_line_plane
from .. utils.bmesh import ensure_gizmo_layers
from .. utils.draw import draw_init, draw_label, draw_line, draw_tris, draw_point, draw_vector, draw_points, draw_vector, draw_mesh_wire
from .. utils.gizmo import hide_gizmos, restore_gizmos
from .. utils.math import dynamic_format
from .. utils.mesh import get_coords
from .. utils.object import get_object_tree
from .. utils.operator import Settings
from .. utils.ui import force_ui_update, navigation_passthrough, scroll_up, scroll_down, ignore_events, init_status, finish_status, get_mouse_pos, get_scale
from .. utils.view import get_location_2d, get_view_origin_and_dir
from .. ui.panels import printd
from .. items import bend_angle_presets, ctrl
from .. colors import red, green, yellow, white, blue, normal, black

def draw_bend_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text=f"Hyper {'Kink' if op.is_kink else 'Bend'}")

        if not op.highlighted:
            row.label(text="", icon='MOUSE_LMB')
            row.label(text="Finish")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        if op.dim_data['POSITIVE_X']:
            row.label(text="", icon='EVENT_Q')
            row.label(text=f"Toggle {'Bend' if op.is_kink else 'Kink'}")

        if op.has_children:
            if op.dim_data['POSITIVE_X']:
                row.separator(factor=2)

            row.label(text="", icon='EVENT_A')
            row.label(text=f"Affect Children: {op.affect_children}")

        if op.dim_data['POSITIVE_X'] or op.has_children:
            row.separator(factor=2)

        row.label(text="", icon='EVENT_C')
        row.label(text=f"Contain: {op.contain}")

        if op.is_kink:
            row.separator(factor=2)

            row.label(text="", icon='EVENT_E')
            row.label(text=f"Use Kink Edges: {op.use_kink_edges}")

        elif op.dim_data['POSITIVE_X']:
            row.separator(factor=2)

            row.label(text="", icon='EVENT_B')
            row.label(text=f"Bisect (positive): {op.positive_bisect}")

        if op.contain:
            row.separator(factor=2)

            row.label(text="", icon='EVENT_X')
            row.label(text=f"Locked Containment: {op.contain_locked}")

        if op.is_kink or op.positive_bisect or op.negative_bisect:
            row.separator(factor=2)

            row.label(text="", icon='EVENT_R')
            row.label(text=f"Remove Redundant: {op.remove_redundant}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_W')
        row.label(text=f"Show pre-{'Kink' if op.is_kink else 'Bend'} Wireframe: {op.wireframe}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_SHIFT')
        row.label(text="", icon='EVENT_W')
        row.label(text=f"Show Object Wireframe: {op.active.show_wire}")

    return draw

class HyperBend(bpy.types.Operator, Settings):
    bl_idname = "machin3.hyper_bend"
    bl_label = "MACHIN3: Hyper Bend"
    bl_description = "Hyper Bend"
    bl_options = {'REGISTER', 'UNDO'}

    affect_children: BoolProperty(name="Kink/Bend Children too", default=True)
    has_children: BoolProperty(name="Has Children", default=False)
    is_kink: BoolProperty(name="Kind instead of Bend", description="Toggle between Kink and Bend Mode", default=False)
    use_kink_edges: BoolProperty(name="Use Edge Dirs for Kinking", default=False)
    def update_angle(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.angle_presets != 'CUSTOM':
            self.avoid_update = True
            self.angle_presets = 'CUSTOM'

    def update_angle_presets(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.angle_presets != 'CUSTOM':
            self.avoid_update = True

            if self.angle < 0:
                self.angle = -float(self.angle_presets)
            else:
                self.angle = float(self.angle_presets)

    def update_negate_angle(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.negate_angle:
            self.avoid_update = True
            self.angle = - self.angle

            self.avoid_update = True
            self.negate_angle = False

    angle: FloatProperty(name="Angle", description="Bend Angle", default=0, min=-360, max=360, step=10, update=update_angle)
    angle_presets: EnumProperty(name="Angle Presets", description="Bend Angle Presets", items=bend_angle_presets, default='CUSTOM', update=update_angle_presets)
    negate_angle: BoolProperty(name="Negate the Angle", default=False, update=update_negate_angle)
    def update_reset_offset(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.reset_offset:
            self.offset = 0

            self.avoid_update = True
            self.reset_offset = False

    offset: FloatProperty(name="Offset", default=0, step=0.1)
    reset_offset: BoolProperty(name="Reset the Offset", default=False, update=update_reset_offset)
    limit_angle: BoolProperty(name="Limit the Angle", default=False)
    positive_bend: BoolProperty(name="Positive Side Bend", default=True)
    positive_bisect: BoolProperty(name="Positive Side Bisect", default=True)
    positive_limit: FloatProperty(name="Positive Side Limit", default=1, min=0, max=1, step=0.1)
    positive_segments: IntProperty(name="Positive Side Segments", default=6, min=0)
    negative_bend: BoolProperty(name="Negative Side Bend", default=False)
    negative_bisect: BoolProperty(name="Negative Side Bisect", default=False)
    negative_limit: FloatProperty(name="Negative Side Limit", default=1, min=0, max=1, step=0.1)
    negative_segments: IntProperty(name="Negative Side Segments", default=6, min=0)
    remove_redundant: BoolProperty(name="Remove Redundant Edges", description="Remove Redundnat Edges after Bending", default=True)
    wireframe: BoolProperty(name="Show Pre-Bend Wireframe", default=True)
    contain: BoolProperty(name="Contain the Bend", description="Contain the Bend on Y and/or Z", default=False)
    contain_locked: BoolProperty(name="Fixed the out-of-containment regions", default=False)
    positive_y_contain: FloatProperty(name="Positive Y Contain", default=1, min=0, max=1, step=0.1)
    negative_y_contain: FloatProperty(name="Negative Y Contain", default=1, min=0, max=1, step=0.1)
    positive_z_contain: FloatProperty(name="Positive Z Contain", default=1, min=0, max=1, step=0.1)
    negative_z_contain: FloatProperty(name="Negative Z Contain", default=1, min=0, max=1, step=0.1)

    def update_mirror_bend(self, context):
        if not self.mirror_bend:
            self.negative_limit = self.positive_limit
            self.negative_segments = self.positive_segments

    mirror_bend: BoolProperty(name="Mirror the Bend", default=False, update=update_mirror_bend)
    avoid_update: BoolProperty()
    passthrough = None

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.type == 'MESH'

    def draw(self, context):
        layout = self.layout

        column = layout.column()

        if self.has_children:
            split = column.split(factor=0.5, align=True)
            row = split.row(align=True)
            row.prop(self, 'is_kink', text='Kink' if self.is_kink else 'Bend', toggle=True)

            split.prop(self, 'affect_children', text='Affect Children', toggle=True)

        else:
            row = column.row(align=True)
            row.prop(self, 'is_kink', text='Kink' if self.is_kink else 'Bend', toggle=True)

        if self.is_kink:
            row.prop(self, 'use_kink_edges', text='', toggle=True, icon='MOD_SIMPLIFY')

        column = layout.column(align=True)
        row = column.row(align=True)
        row.active = self.angle_presets != 'CUSTOM'
        row.prop(self, 'angle_presets', expand=True)

        split = column.split(factor=0.5, align=True)
        row = split.row(align=True)
        r = row.row(align=True)
        r.active = self.angle_presets == 'CUSTOM'
        r.prop(self, 'angle')
        row.prop(self, 'negate_angle', text='', icon='FILE_REFRESH', toggle=True)

        row = split.row(align=True)
        row.prop(self, 'offset')
        r = row.row(align=True)
        r.active = bool(self.offset)
        r.prop(self, 'reset_offset', text='', icon='LOOP_BACK')

        if not self.is_kink:

            split = column.split(factor=0.5, align=True)
            split.prop(self, 'positive_bend', text="Bend", toggle=True)
            r = split.row(align=True)
            r.active = self.positive_bend or self.positive_bisect
            r.prop(self, 'positive_limit', text="Limit")

            rr = r.row(align=True)
            rr.active = self.positive_limit < 1 or (not self.mirror_bend and self.negative_limit < 1)
            rr.prop(self, 'limit_angle', text='', icon='GP_SELECT_BETWEEN_STROKES')

            row = column.row(align=True)
            row.prop(self, 'positive_bisect', text="Bisect", toggle=True)

            r = row.row(align=True)
            r.active = self.positive_bisect
            r.prop(self, 'positive_segments', text="Segments")

            column = layout.column()
            row = column.row()
            row.prop(self, 'mirror_bend', toggle=True)

            if not self.mirror_bend:
                column = layout.column(align=True)
                row = column.row(align=True)
                row.prop(self, 'negative_bend', text="Bend", toggle=True)

                r = row.row(align=True)
                r.active = self.negative_bend or self.negative_bisect
                r.prop(self, 'negative_limit', text="Limit", toggle=True)

                row = column.row(align=True)
                row.prop(self, 'negative_bisect', text="Bisect", toggle=True)
                r = row.row(align=True)
                r.active = self.negative_bisect
                r.prop(self, 'negative_segments', text="Segments")

        column = layout.column(align=True)
        column.prop(self, 'contain', text=f"Contain the {'Kink' if self.is_kink else 'Bend'}", toggle=True)

        if self.contain:
            row = column.row(align=True)
            row.prop(self, 'negative_y_contain', text='Y- Contain')
            row.prop(self, 'positive_y_contain', text='Y+ Contain')

            row = column.row(align=True)
            row.prop(self, 'negative_z_contain', text='Z- Contain')
            row.prop(self, 'positive_z_contain', text='Z+ Contain')

        column = layout.column()
        row = column.row()
        row.prop(self, 'remove_redundant', text="Remove Redundant Edges", toggle=True)

    def draw_HUD(self, context): 
        if context.area == self.area:
            if context.window_manager.HC_bendshowHUD:
                offset = 0

                if self.has_children:
                    offset -= 18

                if self.angle:
                    offset -= 18

                    if self.offset:
                        offset -= 18

                if self.is_kink and self.use_kink_edges:
                    offset -= 18

                else:

                    if self.positive_bisect or self.negative_bisect:
                        offset -= 18

                    if self.positive_bisect and self.negative_bisect and (self.positive_segments != self.negative_segments) and not self.mirror_bend:
                        offset -= 18

                if (self.is_kink or self.positive_bisect or self.negative_bisect) and self.remove_redundant:
                        offset -= 18

                if self.wireframe:
                    offset -= 18

                scale = get_scale(context)
                center = not self.angle

                if center:
                    coords = Vector(self.main_gzm.loc2d) + Vector((0, 90)) * scale

                else:
                    coords = Vector(self.main_gzm.loc2d) + Vector((20, 90)) * scale

                color = yellow if self.is_kink or self.positive_bend or self.negative_bend else white

                if self.contain:
                    title = "🔒Contained " if self.contain_locked else "Contained "
                    titledims = draw_label(context, title=title, coords=coords, offset=offset, center=center, color=white)

                    if center:
                        coords.x -= titledims[0] / 2

                    if self.contain_locked:
                        dims1 = draw_label(context, title="locked ", coords=(coords.x + titledims[0], coords[1]), offset=offset, center=False, size=10, color=white, alpha=0.5)
                    else:
                        dims1 = (0, 0)

                    dims2 = draw_label(context, title=f"Hyper {'Kink' if self.is_kink else 'Bend'} ", coords=(coords.x + titledims[0] + dims1[0], coords[1]), offset=offset, center=False, color=color)
                    dims = (dims1[0] + dims2[0], dims1[1])

                else:
                    titledims = draw_label(context, title=f"Hyper {'Kink' if self.is_kink else 'Bend'} ", coords=coords, offset=offset, center=center, color=color)

                    if center:
                        coords.x -= titledims[0] / 2

                    dims = (0, 0)

                if not self.is_kink and (self.positive_bisect or self.negative_bisect):
                    draw_label(context, title="+ Bisect", coords=(coords.x + titledims[0] + dims[0], coords[1]), offset=offset, center=False, size=10, alpha=0.5)

                if self.angle:
                    offset += 18

                    dims = draw_label(context, title="Angle: ", coords=coords, offset=offset, center=False, alpha=0.5)
                    draw_label(context, title=dynamic_format(self.angle, decimal_offset=1), coords=(coords.x + dims[0], coords[1]), offset=offset, center=False, alpha=1)

                    if self.offset:
                        offset += 18

                        dims = draw_label(context, title="Offset: ", coords=coords, offset=offset, center=False, alpha=0.5)
                        draw_label(context, title=dynamic_format(self.offset, decimal_offset=1), coords=(coords.x + dims[0], coords[1]), offset=offset, center=False, alpha=1)

                if not self.is_kink and (self.positive_bisect or self.negative_bisect):
                    offset += 18

                    if self.positive_bisect and self.negative_bisect and (self.positive_segments != self.negative_segments) and not self.mirror_bend:

                        dims = draw_label(context, title="Segments: ", coords=coords, offset=offset, center=False, alpha=1 if self.mouse_side == 'POSITIVE' else 0.5)
                        dims2 = draw_label(context, title=str(self.positive_segments), coords=(coords.x + dims[0], coords.y), offset=offset, center=False, alpha=1)
                        draw_label(context, title=" positive", coords=(coords.x + dims[0] + dims2[0], coords.y), offset=offset, center=False, size=10, alpha=0.5 if self.mouse_side == 'POSITIVE' else 0.3)

                        offset += 18

                        dims = draw_label(context, title="Segments: ", coords=coords, offset=offset, center=False, alpha=1 if self.mouse_side == 'NEGATIVE' else 0.5)
                        dims2 = draw_label(context, title=str(self.negative_segments), coords=(coords.x + dims[0], coords.y), offset=offset, center=False, alpha=1)
                        draw_label(context, title=" negative", coords=(coords.x + dims[0] + dims2[0], coords.y), offset=offset, center=False, size=10, alpha=0.5 if self.mouse_side == 'NEGATIVE' else 0.3)

                    elif self.positive_bisect:
                        dims = draw_label(context, title="Segments: ", coords=coords, offset=offset, center=False, alpha=0.5)
                        draw_label(context, title=str(self.positive_segments), coords=(coords.x + dims[0], coords.y), offset=offset, center=False, alpha=1)

                    elif self.negative_bisect:
                        dims = draw_label(context, title="Segments: ", coords=coords, offset=offset, center=False, alpha=0.5)
                        draw_label(context, title=str(self.negative_segments), coords=(coords.x + dims[0], coords.y), offset=offset, center=False, alpha=1)

                if self.is_kink and self.use_kink_edges:
                    offset += 18

                    draw_label(context, title="Use Kink Edges", coords=coords, offset=offset, center=False, color=normal, alpha=1)

                if self.has_children:
                    offset += 18

                    color, alpha = (green, 1) if self.affect_children else (white, 0.2)
                    draw_label(context, title=f"{'Affect' if self.affect_children else 'Has'} Children", coords=coords, offset=offset, center=False, color=color, alpha=alpha)

                if (self.is_kink or self.positive_bisect or self.negative_bisect) and self.remove_redundant:
                    offset += 18

                    draw_label(context, title="Remove Redundant", coords=coords, offset=offset, center=False, color=red, alpha=1)

                if self.wireframe:
                    offset += 18

                    draw_label(context, title="Wireframe", coords=coords, offset=offset, center=False, color=blue, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            for axis in self.view3d_bend_axes:
                draw_vector(axis * 1.5, mx=self.cmx, color=green, alpha=0.5, width=2, fade=True)

            if self.wireframe:
                draw_mesh_wire(self.batch, color=white, width=1, alpha=0.1)

            if self.contain and self.contain_locked and self.locked_coords:
                draw_points(self.locked_coords, mx=self.cmx, color=black, size=5, alpha=0.75)

    def modal(self, context, event):
        if ignore_events(event):
            return {'PASS_THROUGH'}

        context.area.tag_redraw()

        self.highlighted = self.get_highlighted(context)

        events = ['MOUSEMOVE', 'C', 'W']

        if self.dim_data['POSITIVE_X']:
            events.append('Q')

            if not self.is_kink:
                events.append('B')

        if self.is_kink:
            events.append('E')

        if self.has_children:
            events.append('A')

        if self.contain:
            events.append('X')

        if self.is_kink or self.positive_bisect or self.negative_bisect:
            events.append('R')

        if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):

            if event.type == 'MOUSEMOVE':

                self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y))

                if self.passthrough:
                    self.passthrough = False

                    loc2d = get_location_2d(context, self.cmx.to_translation(), debug=False)

                    self.main_gzm.loc2d = loc2d
                    self.positive_gzm.loc2d = loc2d
                    self.negative_gzm.loc2d = loc2d

                    context.window_manager.HC_bendshowHUD = True

                if context.window_manager.HC_bendshowHUD:
                    self.mouse_side = self.get_mouse_side(context)

            if context.window_manager.HC_bendshowHUD:

                if (scroll_up(event, key=True) or scroll_down(event, key=True)):
                    if self.positive_bisect and self.negative_bisect:
                        gzm = getattr(self, f"{self.mouse_side.lower()}_gzm")
                    elif self.positive_bisect:
                        gzm = self.positive_gzm
                    else:
                        gzm = self.negative_gzm

                    if scroll_up(event, key=True):
                        gzm.segments += 10 if event.ctrl else 1

                    else:
                        gzm.segments -= 19 if event.ctrl else 1

                elif event.type == 'C' and event.value == 'PRESS':
                    self.main_gzm.contain = not self.main_gzm.contain

                    if self.main_gzm.contain:

                        if self.main_gzm.mirror_bend:
                            self.main_gzm.mirror_bend = False
                            self.mirror_bend = False

                            self.negative_gzm.bisect = False
                            self.negative_bisect = False

                            self.negative_gzm.bend = False
                            self.negative_bend = False

                        if self.negative_bend and self.positive_bend:
                            self.negative_gzm.bisect = False
                            self.negative_bisect = False

                            self.negative_gzm.bend = False
                            self.negative_bend = False

                elif event.type == 'X' and event.value == 'PRESS':
                    self.contain_locked = not self.contain_locked

                    self.modal_bend()

                elif event.type == 'W' and event.value == 'PRESS':
                    
                    if event.shift:
                        self.active.show_wire = not self.active.show_wire

                    else:
                        self.wireframe = not self.wireframe

                    force_ui_update(context)

                elif (self.positive_bisect or self.negative_bisect) and event.type == 'R' and event.value == 'PRESS':
                    self.main_gzm.remove_redundant = not self.main_gzm.remove_redundant

                elif event.type == 'Q' and event.value == 'PRESS':
                    self.main_gzm.is_kink = not self.main_gzm.is_kink

                elif event.type == 'E' and event.value == 'PRESS':
                    self.main_gzm.use_kink_edges = not self.main_gzm.use_kink_edges

                elif event.type == 'A' and event.value == 'PRESS':
                    self.main_gzm.affect_children = not self.main_gzm.affect_children

                elif event.type == 'B' and event.value == 'PRESS':
                    self.positive_gzm.bisect = not self.positive_gzm.bisect

        if self.main_gzm.is_kink != self.is_kink:
            self.is_kink = self.main_gzm.is_kink

            self.modal_bend()

        if self.main_gzm.affect_children != self.affect_children:
            self.affect_children = self.main_gzm.affect_children

            self.modal_bend()

        if self.main_gzm.contain != self.contain:
            self.contain = self.main_gzm.contain

            self.modal_bend()

        if self.main_gzm.angle != self.angle:
            self.angle = self.main_gzm.angle

            self.modal_bend()

        if self.offset_gzm.offset != self.offset:
            self.offset = self.offset_gzm.offset

            self.modal_bend()

        if self.contain:

            if self.contain_negative_y_gzm.limit != self.negative_y_contain:
                self.negative_y_contain = self.contain_negative_y_gzm.limit

                self.modal_bend()

            elif self.contain_positive_y_gzm.limit != self.positive_y_contain:
                self.positive_y_contain = self.contain_positive_y_gzm.limit

                self.modal_bend()
            
            elif self.contain_negative_z_gzm.limit != self.negative_z_contain:
                self.negative_z_contain = self.contain_negative_z_gzm.limit

                self.modal_bend()

            elif self.contain_positive_z_gzm.limit != self.positive_z_contain:
                self.positive_z_contain = self.contain_positive_z_gzm.limit

                self.modal_bend()

        if self.is_kink:

            if self.main_gzm.use_kink_edges != self.use_kink_edges:
                self.use_kink_edges = self.main_gzm.use_kink_edges

                self.modal_bend()

        else:

            if self.positive_bisect and self.positive_gzm.segments != self.positive_segments:
                self.positive_segments = self.positive_gzm.segments

                self.modal_bend()

            if self.negative_bisect and self.negative_gzm.segments != self.negative_segments:
                self.negative_segments = self.negative_gzm.segments

                self.modal_bend()

            if self.positive_gzm.limit != self.positive_limit:
                self.positive_limit = self.positive_gzm.limit

                self.modal_bend()

            if self.negative_gzm.limit != self.negative_limit:
                self.negative_limit = self.negative_gzm.limit

                self.modal_bend()

        if context.window_manager.HC_bendshowHUD:

            if not self.is_kink:

                if self.mirror_bend != self.main_gzm.mirror_bend:
                    self.mirror_bend = self.main_gzm.mirror_bend

                    if self.mirror_bend:
                        self.negative_bend = self.positive_bend
                        self.negative_bisect = self.positive_bisect

                        if self.main_gzm.contain:
                            self.main_gzm.contain = False
                            self.contain = False

                    else:
                        self.negative_bend = not self.positive_bend
                        self.negative_bisect = not self.positive_bisect

                    self.modal_bend()

                if self.positive_bend != self.positive_gzm.bend:
                    self.positive_bend = self.positive_gzm.bend

                    if self.contain and self.negative_bend:
                        self.contain = False
                        self.main_gzm.contain = False

                    self.modal_bend()

                if self.positive_bisect != self.positive_gzm.bisect:
                    self.positive_bisect = self.positive_gzm.bisect

                    self.modal_bend()

                if self.negative_bend != self.negative_gzm.bend:
                    self.negative_bend = self.negative_gzm.bend

                    if self.contain and self.negative_bend:
                        self.contain = False
                        self.main_gzm.contain = False

                    self.modal_bend()

                if self.negative_bisect != self.negative_gzm.bisect:
                    self.negative_bisect = self.negative_gzm.bisect

                    self.modal_bend()

            if self.remove_redundant != self.main_gzm.remove_redundant:
                self.remove_redundant = self.main_gzm.remove_redundant

                self.modal_bend()

        if navigation_passthrough(event, alt=True, wheel=False):
            context.window_manager.HC_bendshowHUD = False
            self.passthrough = True
            return {'PASS_THROUGH'}

        finish_events = ['SPACE']

        if not self.highlighted:
            finish_events.append('LEFTMOUSE')

        if event.type in finish_events and event.value == 'PRESS':
            self.finish(context)
            self.save_settings()

            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC'] and event.value == 'PRESS':
            self.finish(context)

            for obj, bm in self.initbms.items():
                bm.to_mesh(obj.data)

            return {'CANCELLED'}

        if event.type == 'MOUSEMOVE' or (self.highlighted and event.type == 'LEFTMOUSE'):
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        restore_gizmos(self)

        finish_status(self)

        wm = context.window_manager
        wm.gizmo_group_type_unlink_delayed('MACHIN3_GGT_bend')

        context.window_manager.HC_bendshowHUD = False

        self.bendCOL.clear()

        force_ui_update(context)

    def invoke(self, context, event):
        self.init_settings(props=['is_kink', 'positive_bisect', 'positive_bend', 'positive_segments', 'negative_bisect', 'negative_bend', 'negative_segments', 'remove_redundant', 'affect_children'])
        self.load_settings()

        self.active = context.active_object
        self.objects = [self.active]
        self.highlighted = None
        self.last_highlighted = None

        self.mod_dict = self.get_children(context, self.active, self.objects)

        self.mx = self.active.matrix_world.copy()
        self.cmx = context.scene.cursor.matrix
        self.loc, rot, _ = self.cmx.decompose()

        self.deltamx = self.cmx.inverted_safe() @ self.mx
        
        self.initbms = {}

        for obj in self.objects:
            self.initbms[obj] = self.create_bmesh(obj)[0]

        self.setup_bend_collection(context, self.loc, rot)

        self.dim_data = self.get_dimensions_data(self.initbms[self.active], self.deltamx, self.loc, rot, modal=True, debug=False)

        self.verify_init_props(debug=False)

        self.cursor_x_dir = rot @ Vector((1, 0, 0))

        self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y))

        self.mouse_side = self.get_mouse_side(context)

        self.locked_coords = []

        context.window_manager.HC_bendshowHUD = True

        hide_gizmos(self, context)

        context.window_manager.gizmo_group_type_ensure('MACHIN3_GGT_bend')

        init_status(self, context, func=draw_bend_status(self))

        self.modal_bend()

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        active = context.active_object
        objects = [active]

        mod_dict = self.get_children(context, active, objects)

        for obj in objects:
            is_active = obj == active

            mx = obj.matrix_world.copy()
            cmx = context.scene.cursor.matrix
            deltamx = cmx.inverted_safe() @ mx

            bm, vgroups, edge_glayer, face_glayer = self.create_bmesh(obj)

            if is_active:
                loc, rot, _ = cmx.decompose()
                self.dim_data = self.get_dimensions_data(bm, deltamx, loc, rot, modal=False, debug=False)

            if self.mirror_bend:
                self.negative_bend = self.positive_bend
                self.negative_bisect = self.positive_bisect

            if mx != cmx:
                obj.matrix_world = cmx
                bmesh.ops.transform(bm, matrix=deltamx, verts=bm.verts, use_shapekey=False)

            if self.is_kink:
                self.kink(bm, vgroups, angle=self.angle, offset=self.offset, cmx=cmx, debug=False)

            else:

                if self.positive_bisect or self.negative_bisect:
                    self.bisect(bm, vgroups, force_final_cut=not is_active, debug=False)

                if self.angle:

                    if self.positive_bend or self.negative_bend:
                        self.bend(bm, angle=self.angle, offset=self.offset, debug=False)

            if self.angle and is_active:
                self.process_mesh(bm, edge_glayer, face_glayer, obj.HC.objtype, self.angle)

            if mx != cmx:
                bmesh.ops.transform(bm, matrix=deltamx.inverted_safe(), verts=bm.verts, use_shapekey=False)
                obj.matrix_world = mx

            bm.to_mesh(obj.data)
            bm.free()

            if not self.is_kink and not is_active and obj in mod_dict:
                mods = mod_dict[obj]

                for mod in mods:
                    if mod.type == 'BOOLEAN' and mod.solver == 'FAST':
                        mod.solver = 'EXACT'
                        mod.use_hole_tolerant = True

        return {'FINISHED'}

    def modal_bend(self):
        for obj in self.objects:
            is_active = obj == self.active

            if not is_active and not (self.has_children and self.affect_children):
                bm = self.initbms[obj]
                bm.to_mesh(obj.data)
                continue

            mx = obj.matrix_world.copy()
            cmx = self.cmx
            deltamx = cmx.inverted_safe() @ mx

            bm, vgroups, edge_glayer, face_glayer = self.copy_init_bmesh(obj)

            if mx != cmx:
                obj.matrix_world = cmx
                bmesh.ops.transform(bm, matrix=deltamx, verts=bm.verts, use_shapekey=False)

            if self.is_kink:
                self.kink(bm, vgroups, angle=self.angle, offset=self.offset, cmx=cmx, modal=is_active, debug=False)

            else:

                if self.positive_bisect or self.negative_bisect:
                    self.bisect(bm, vgroups, force_final_cut=not is_active, modal=is_active, debug=False)

                if is_active:
                    bm.to_mesh(obj.data)
                    self.batch = get_coords(obj.data, mx=self.cmx, edge_indices=True)

                if self.angle:
                    if self.positive_bend or self.negative_bend:
                        self.bend(bm, angle=self.angle, offset=self.offset, debug=False)

            if self.angle and is_active:
                self.process_mesh(bm, edge_glayer, face_glayer, obj.HC.objtype, self.angle)

            if mx != cmx:
                bmesh.ops.transform(bm, matrix=deltamx.inverted_safe(), verts=bm.verts, use_shapekey=False)
                obj.matrix_world = mx

            bm.to_mesh(obj.data)

            if not self.is_kink and not is_active and obj in self.mod_dict:
                mods = self.mod_dict[obj]

                for mod in mods:
                    if mod.type == 'BOOLEAN' and mod.solver == 'FAST':
                        mod.solver = 'EXACT'
                        mod.use_hole_tolerant = True

    def get_children(self, context, active, objects, debug=False):
        obj_tree = []
        mod_dict = {}
        get_object_tree(active, obj_tree, mod_objects=True, mod_dict=mod_dict, ensure_on_viewlayer=True, debug=False)

        mesh_objects = set(obj for obj in mod_dict if obj.type == 'MESH')
        mesh_objects.update(obj for obj in obj_tree if obj.type == 'MESH')

        if active in mesh_objects:
            mesh_objects.remove(active)
        
        self.has_children = bool(mesh_objects)

        if mesh_objects:
            objects.extend(mesh_objects)

        if debug:
            print()
            print("mesh children (incl. mod objects):" )
            for obj in objects:
                print(obj.name, obj.name in context.view_layer.objects)

        return mod_dict

    def create_bmesh(self, active):
        bm = bmesh.new()
        bm.from_mesh(active.data)
        bm.normal_update()

        vgroups = bm.verts.layers.deform.verify()
        edge_glayer, face_glayer = ensure_gizmo_layers(bm)

        return bm, vgroups, edge_glayer, face_glayer

    def copy_init_bmesh(self, obj):
        bm = self.initbms[obj].copy()
        bm.normal_update()

        vgroups = bm.verts.layers.deform.verify()
        edge_glayer, face_glayer = ensure_gizmo_layers(bm)

        return bm, vgroups, edge_glayer, face_glayer

    def setup_bend_collection(self, context, loc, rot):
        loc2d = get_location_2d(context, loc, debug=False)
        area_pointer = str(context.area.as_pointer())

        self.bendCOL = context.window_manager.HC_bendCOL
        self.bendCOL.clear()

        g = self.bendCOL.add()
        g.index = 0
        g.type = 'MAIN'
        g.obj = self.active
        g.cmx = self.cmx
        g.loc = loc
        g.loc2d = loc2d
        g.is_kink = self.is_kink
        g.remove_redundant = self.remove_redundant
        g.affect_children = self.affect_children
        g.has_children = self.has_children
        g.contain = self.contain
        g.area_pointer = area_pointer

        g = self.bendCOL.add()
        g.index = 1
        g.type = 'OFFSET'
        g.obj = self.active
        g.cmx = self.cmx
        g.loc = loc
        g.rot = rot
        g.offset = 0
        g.area_pointer = area_pointer

        g = self.bendCOL.add()
        g.index = 2
        g.type = 'POSITIVE'
        g.loc2d = loc2d
        g.bisect = self.positive_bisect
        g.bend = self.positive_bend
        g.segments = self.positive_segments
        g.area_pointer = area_pointer

        g = self.bendCOL.add()
        g.index = 3
        g.type = 'NEGATIVE'
        g.loc2d = loc2d
        g.bisect = self.negative_bisect
        g.bend = self.negative_bend
        g.segments = self.negative_segments
        g.area_pointer = area_pointer

        g = self.bendCOL.add()
        g.index = 4
        g.type = 'CONTAIN_NEGATIVE_Y'
        g.area_pointer = area_pointer

        g = self.bendCOL.add()
        g.index = 5
        g.type = 'CONTAIN_POSITIVE_Y'
        g.area_pointer = area_pointer

        g = self.bendCOL.add()
        g.index = 6
        g.type = 'CONTAIN_NEGATIVE_Z'
        g.area_pointer = area_pointer

        g = self.bendCOL.add()
        g.index = 7
        g.type = 'CONTAIN_POSITIVE_Z'
        g.area_pointer = area_pointer

        for g in self.bendCOL:

            gzm_name = f'{g.type.lower()}_gzm'

            setattr(self, gzm_name, g)

    def get_dimensions_data(self, bm, deltamx, loc, rot, modal=False, debug=False):
        dim_data = {'POSITIVE_X': 0,
                    'NEGATIVE_X': 0,
                    'POSITIVE_Y': 0,
                    'NEGATIVE_Y': 0,
                    'POSITIVE_Z': 0,
                    'NEGATIVE_Z': 0}

        dim_data['NEGATIVE_X'] = 0
        dim_data['POSITIVE_X'] = 0

        dim_data['NEGATIVE_Y'] = 0
        dim_data['POSITIVE_Y'] = 0

        dim_data['NEGATIVE_Z'] = 0
        dim_data['POSITIVE_Z'] = 0

        for v in bm.verts:
            co = deltamx @ v.co

            if co.x < dim_data['NEGATIVE_X']:
                dim_data['NEGATIVE_X'] = co.x

            if co.x > dim_data['POSITIVE_X']:
                dim_data['POSITIVE_X'] = co.x

            if co.y < dim_data['NEGATIVE_Y']:
                dim_data['NEGATIVE_Y'] = co.y

            if co.y > dim_data['POSITIVE_Y']:
                dim_data['POSITIVE_Y'] = co.y

            if co.z < dim_data['NEGATIVE_Z']:
                dim_data['NEGATIVE_Z'] = co.z

            if co.z > dim_data['POSITIVE_Z']:
                dim_data['POSITIVE_Z'] = co.z

        if debug:
            printd(dim_data)

        negative_x_limit_co = loc + rot @ Vector((dim_data['NEGATIVE_X'], 0, 0))
        positive_x_limit_co = loc + rot @ Vector((dim_data['POSITIVE_X'], 0, 0))

        if debug:
            draw_point(negative_x_limit_co, color=red, alpha=0.5, modal=False)
            draw_point(positive_x_limit_co, color=red, modal=False)

        negative_y_limit_co = loc + rot @ Vector((0, dim_data['NEGATIVE_Y'], 0))
        positive_y_limit_co = loc + rot @ Vector((0, dim_data['POSITIVE_Y'], 0))

        if debug:
            draw_point(negative_y_limit_co, color=green, alpha=0.5, modal=False)
            draw_point(positive_y_limit_co, color=green, modal=False)

        negative_z_limit_co = loc + rot @ Vector((0, 0, dim_data['NEGATIVE_Z']))
        positive_z_limit_co = loc + rot @ Vector((0, 0, dim_data['POSITIVE_Z']))

        if debug:
            draw_point(negative_z_limit_co, color=blue, alpha=0.5, modal=False)
            draw_point(positive_z_limit_co, color=blue, modal=False)

        if modal:

            ymindir = Vector((0, dim_data['NEGATIVE_Y'], 0))
            ymaxdir = Vector((0, dim_data['POSITIVE_Y'], 0))

            self.view3d_bend_axes = [ymindir, ymaxdir]

            for g in self.bendCOL:

                if g.type == 'OFFSET':
                    self.offset_gzm.z_factor = abs(dim_data['NEGATIVE_Z']) + dim_data['POSITIVE_Z']

                elif g.type == 'NEGATIVE':
                    neg_rot = rot.copy()
                    neg_rot.rotate(Quaternion(Vector(rot @ Vector((0, 1, 0))), radians(-90)))

                    g.limit_distance = abs(dim_data['NEGATIVE_X'])
                    g.obj = self.active
                    g.cmx = self.cmx
                    g.loc = negative_x_limit_co
                    g.rot = neg_rot

                elif g.type == 'POSITIVE':
                    pos_rot = rot.copy()
                    pos_rot.rotate(Quaternion(Vector(rot @ Vector((0, 1, 0))), radians(90)))

                    g.limit_distance = dim_data['POSITIVE_X']
                    g.obj = self.active
                    g.cmx = self.cmx
                    g.loc = positive_x_limit_co
                    g.rot = pos_rot

                elif g.type == 'CONTAIN_NEGATIVE_Y':
                    neg_y_rot = rot.copy()
                    neg_y_rot.rotate(Quaternion(Vector(rot @ Vector((-1, 0, 0))), radians(-90)))

                    g.limit_distance = abs(dim_data['NEGATIVE_Y'])
                    g.obj = self.active
                    g.cmx = self.cmx
                    g.loc = negative_y_limit_co
                    g.rot = neg_y_rot

                elif g.type == 'CONTAIN_POSITIVE_Y':
                    pos_y_rot = rot.copy()
                    pos_y_rot.rotate(Quaternion(Vector(rot @ Vector((-1, 0, 0))), radians(90)))

                    g.limit_distance = abs(dim_data['POSITIVE_Y'])
                    g.obj = self.active
                    g.cmx = self.cmx
                    g.loc = positive_y_limit_co
                    g.rot = pos_y_rot

                elif g.type == 'CONTAIN_NEGATIVE_Z':
                    neg_z_rot = rot.copy()
                    neg_z_rot.rotate(Quaternion(Vector(rot @ Vector((1, 0, 0))), radians(180)))

                    g.limit_distance = abs(dim_data['NEGATIVE_Z'])
                    g.obj = self.active
                    g.cmx = self.cmx
                    g.loc = negative_z_limit_co
                    g.rot = neg_z_rot

                elif g.type == 'CONTAIN_POSITIVE_Z':
                    pos_z_rot = rot.copy()

                    g.limit_distance = abs(dim_data['POSITIVE_Z'])
                    g.obj = self.active
                    g.cmx = self.cmx
                    g.loc = positive_z_limit_co
                    g.rot = pos_z_rot

        return dim_data

    def verify_init_props(self, debug=False):
        if debug:
            print()
            print("initial positive:", self.positive_bisect, self.positive_bend, self.positive_gzm.bisect, self.positive_gzm.bend)
            print("initial negative:", self.negative_bisect, self.negative_bend, self.negative_gzm.bisect, self.negative_gzm.bend)

        positive_distance = self.dim_data['POSITIVE_X']
        negative_distance = self.dim_data['NEGATIVE_X']

        if not positive_distance:
            if self.positive_bisect:
                self.positive_bisect = False
                self.positive_gzm.bisect = False

                if debug:
                    print(" disabled positive bend")

            if self.positive_bend:
                self.positive_bend = False
                self.positive_gzm.bend = False

                if debug:
                    print(" disabled positive bisect")

        if not negative_distance:
            if self.negative_bisect:
                self.negative_bisect = False
                self.negative_gzm.bisect = False

                if debug:
                    print(" disabled negative bend")

            if self.negative_bend:
                self.negative_bend = False
                self.negative_gzm.bend = False

                if debug:
                    print(" disabled negative bisect")

        if not positive_distance and self.is_kink:
            self.is_kink = False
            self.main_gzm.is_kink = False

            if debug:
                print("disabled kink")

        if not any([self.positive_bisect, self.positive_bend, self.negative_bisect, self.negative_bend]):
            if positive_distance:
                self.positive_bisect = True
                self.positive_bend = True

                self.positive_gzm.bisect = True
                self.positive_gzm.bend = True

                if debug:
                    print(" force enabled positive bisect and bend")

            elif negative_distance:
                self.negative_bisect = True
                self.negative_bend = True

                self.negative_gzm.bisect = True
                self.negative_gzm.bend = True

                if debug:
                    print(" force enabled negative bisect and bend")

        if debug:
            print()
            print("verified positive:", self.positive_bisect, self.positive_bend, self.positive_gzm.bisect, self.positive_gzm.bend)
            print("verified negative:", self.negative_bisect, self.negative_bend, self.negative_gzm.bisect, self.negative_gzm.bend)

    def get_side_data(self, bm, positive=True, negative=True, debug=False):
        data = {'POSITIVE': {'verts': {}},

                'NEGATIVE': {'verts': {}}
                }

        for v in bm.verts:
            if positive and v.co.x > 0:
                data['POSITIVE']['verts'][v] = {'distance': v.co.x}

            elif negative and v.co.x < 0:
                data['NEGATIVE']['verts'][v] = {'distance': -v.co.x}

        if debug:
            printd(data, name="sides")

        return data

    def get_side_props(self, side):
        if side == 'POSITIVE' or self.mirror_bend:
            limit = self.positive_limit
            segments = self.positive_segments + 1
        else:
            limit = self.negative_limit
            segments = self.negative_segments + 1

        return 1 if side == 'POSITIVE' else -1 , limit, segments

    def get_mouse_side(self, context):
        self.view_origin = region_2d_to_origin_3d(context.region, context.region_data, self.mousepos)
        self.view_dir = region_2d_to_vector_3d(context.region, context.region_data, self.mousepos)

        i = intersect_line_line(self.loc, self.loc + self.cursor_x_dir, self.view_origin, self.view_origin + self.view_dir)

        if i:
            mousedir = (i[0] - self.loc).normalized()

            dot = self.cursor_x_dir.dot(mousedir)
            return 'POSITIVE' if dot >= 0 else 'NEGATIVE'

    def get_out_of_cointainment_verts(self, bm, included_verts, consider_offset=True, buffer=0.0001, debug=False):

        offset = self.offset if consider_offset else 0

        negative_y_max = self.dim_data['NEGATIVE_Y'] * self.negative_y_contain
        positive_y_max = self.dim_data['POSITIVE_Y'] * self.positive_y_contain

        negative_z_max = self.dim_data['NEGATIVE_Z'] * self.negative_z_contain
        positive_z_max = self.dim_data['POSITIVE_Z'] * self.positive_z_contain

        if debug:
            print()
            print("negative y max:", negative_y_max)
            print("positive y max:", positive_y_max)
            print("negative z max:", negative_z_max)
            print("positive z max:", positive_z_max)

        out_of_containment = []

        for v in bm.verts:

            if v in included_verts:
                continue

            elif self.dim_data['NEGATIVE_Y'] - buffer < v.co.y < negative_y_max - buffer:
                out_of_containment.append(v)

                if debug:
                    print(" added", v.index, "y neg")

            elif positive_y_max + buffer < v.co.y < self.dim_data['POSITIVE_Y'] + buffer:
                out_of_containment.append(v)

                if debug:
                    print(" added", v.index, "y pos")

            elif self.dim_data['NEGATIVE_Z'] - offset - buffer < v.co.z < negative_z_max - offset - buffer:
                out_of_containment.append(v)

                if debug:
                    print(" added", v.index, v.co.z, "z neg")

            elif positive_z_max - offset + buffer < v.co.z < self.dim_data['POSITIVE_Z'] - offset + buffer:
                out_of_containment.append(v)

                if debug:
                    print(" added", v.index, v.co.z, "z pos")

        return out_of_containment

    def get_highlighted(self, context):
        for b in self.bendCOL:
            if b.is_highlight:
                if self.last_highlighted != b:
                    self.last_highlighted = b

                    force_ui_update(context)

                return b

        if self.last_highlighted:
            self.last_highlighted = None
            force_ui_update(context)

    def kink(self, bm, vgroups, angle=45, offset=0, cmx=Matrix(), modal=False, debug=False):
        if modal:
            self.locked_coords = []

        geom = [el for seq in [bm.verts, bm.edges, bm.faces] for el in seq]
        ret = bmesh.ops.bisect_plane(bm, geom=geom, dist=0, plane_co=Vector((0, 0, 0)), plane_no=Vector((1, 0, 0)), use_snap_center=False, clear_outer=False, clear_inner=False)

        geom_cut = ret['geom_cut']

        bisect_verts = [el for el in geom_cut if isinstance(el, bmesh.types.BMVert)]
        bisect_edges = [el for el in geom_cut if isinstance(el, bmesh.types.BMEdge)]

        for v in bisect_verts:
            for vgindex, weight in v[vgroups].items():
                if weight != 1 or v.calc_shell_factor() == 1:
                    del v[vgroups][vgindex]

        data = self.get_side_data(bm, positive=True, negative=False, debug=False)

        if offset:
            bmesh.ops.translate(bm, verts=bm.verts, vec=(0.0, 0.0, -offset))

        positive_verts = [v for v in data['POSITIVE']['verts'] if v not in bisect_verts]

        if debug:
            for v in positive_verts:
                draw_point(v.co.copy(), mx=cmx, modal=False)

            for v in bisect_verts:
                draw_point(v.co.copy(), mx=cmx, color=red, modal=False)

        rotmx = Quaternion(Vector((0, 1, 0)), -radians(angle)).to_matrix()

        if self.contain:

            out_of_cointainment_verts = self.get_out_of_cointainment_verts(bm, positive_verts, debug=False)

            remove_bisect_verts = [v for v in bisect_verts if v in out_of_cointainment_verts]
            remove_bisect_edges = [e for e in bisect_edges if all(v in remove_bisect_verts for v in e.verts)]

            if remove_bisect_edges:

                for v in remove_bisect_verts:
                    if not v.is_valid:
                        bisect_verts.remove(v)

            out_of_cointainment_verts = self.get_out_of_cointainment_verts(bm, [], debug=False)

            if modal:
                mx = self.cmx @ Matrix.Translation(Vector((0, 0, self.offset)))

                bm.to_mesh(self.active.data)
                self.batch = get_coords(self.active.data, mx=mx, edge_indices=True)

                if self.contain and self.contain_locked:
                    self.locked_coords = [Matrix.Translation(Vector((0, 0, self.offset))) @ v.co.copy() for v in out_of_cointainment_verts]

            if self.contain_locked:
                rotate_verts = [v for v in positive_verts if v not in out_of_cointainment_verts]

            else:
                other = set(bm.verts) - set(positive_verts)
                additional = [v for v in other if v in out_of_cointainment_verts]

                rotate_verts = positive_verts + list(additional)
        
        else:
            rotate_verts = positive_verts

            if modal:
                mx = self.cmx @ Matrix.Translation(Vector((0, 0, self.offset)))

                bm.to_mesh(self.active.data)
                self.batch = get_coords(self.active.data, mx=mx, edge_indices=True)

        bmesh.ops.rotate(bm, matrix=rotmx, verts=rotate_verts)

        x_dir = Vector((1, 0, 0))

        if debug:
            draw_vector(x_dir, origin=Vector(), mx=cmx, color=red, modal=False)

        x_dir_rot = x_dir.copy()
        x_dir_rot.rotate(Quaternion(Vector((0, 1, 0)), -radians(angle / 2)))

        if debug:
            draw_vector(x_dir_rot, origin=Vector(), mx=cmx, color=green, modal=False)

        for v in bisect_verts:

            rot_dir = x_dir

            if self.use_kink_edges:

                edge_dirs = [(e.other_vert(v).co - v.co).normalized() for e in v.link_edges if e.other_vert(v) not in bisect_verts and e.other_vert(v).co.x < 0]

                if edge_dirs:
                    rot_dir = edge_dirs[0]

            i = intersect_line_plane(v.co, v.co + rot_dir, Vector(), x_dir_rot)

            if i: 
                if debug:
                    draw_point(i, mx=cmx, color=green, modal=False)

                v.co = i

        if offset:
            bmesh.ops.translate(bm, verts=bm.verts, vec=(0.0, 0.0, offset))

    def bisect(self, bm, vgroups, force_final_cut=False, modal=False, debug=False):
        if modal:
            self.locked_coords = []

        first_cut = None
        
        side_data = self.get_side_data(bm, debug=False)

        for side, side_dict in side_data.items():

            if not side_dict['verts'] or (side == 'POSITIVE' and not self.positive_bisect) or (side == 'NEGATIVE' and not self.negative_bisect):
                continue

            side_factor, limit, segments = self.get_side_props(side)

            if debug:
                print()
                print(f"bisecting {side} side {segments - 1} times")
            
            max_distance = abs(self.dim_data[f"{side}_X"])
            bisect_distance = max_distance * limit

            bisect_verts = []
            bisect_edges = []

            for i in range(segments):

                if i == 0:
                    if first_cut is None:
                        first_cut = True
                    
                    elif first_cut:
                        continue

                reach = (i / segments) * bisect_distance

                geom = [el for seq in [bm.verts, bm.edges, bm.faces] for el in seq]
                ret = bmesh.ops.bisect_plane(bm, geom=geom, dist=0, plane_co=Vector((reach * side_factor, 0, 0)), plane_no=Vector((side_factor, 0, 0)), use_snap_center=False, clear_outer=False, clear_inner=False)

                geom_cut = ret['geom_cut']

                verts = [el for el in geom_cut if isinstance(el, bmesh.types.BMVert)]
                edges = [el for el in geom_cut if isinstance(el, bmesh.types.BMEdge)]

                bisect_verts.extend(verts)
                bisect_edges.extend(edges)

                for v in verts:
                    for vgindex, weight in v[vgroups].items():
                        if weight != 1 or v.calc_shell_factor() == 1:
                            del v[vgroups][vgindex]

                if i == segments - 1 and (limit < 1 or force_final_cut):
                    if debug:
                        print(" additional bisect at the end to delimit the bend")

                    geom = [el for seq in [bm.verts, bm.edges, bm.faces] for el in seq]
                    ret = bmesh.ops.bisect_plane(bm, geom=geom, dist=0, plane_co=Vector((bisect_distance * side_factor, 0, 0)), plane_no=Vector((side_factor, 0, 0)), use_snap_center=False, clear_outer=False, clear_inner=False)

                    geom_cut = ret['geom_cut']

                    verts = [el for el in geom_cut if isinstance(el, bmesh.types.BMVert)]
                    edges = [el for el in geom_cut if isinstance(el, bmesh.types.BMEdge)]

                    bisect_verts.extend(verts)
                    bisect_edges.extend(edges)

                    for v in verts:
                        for vgindex, weight in v[vgroups].items():
                            if weight != 1 or v.calc_shell_factor() == 1:
                                del v[vgroups][vgindex]

            if self.contain and bisect_edges:
                out_of_cointainment_verts = self.get_out_of_cointainment_verts(bm, included_verts=side_dict['verts'], consider_offset=False, debug=False)

                remove_bisect_verts = [v for v in bisect_verts if v in out_of_cointainment_verts]
                remove_bisect_edges = [e for e in bisect_edges if all(v in remove_bisect_verts for v in e.verts)]

                if remove_bisect_edges:
                    bmesh.ops.dissolve_edges(bm, edges=remove_bisect_edges, use_verts=True)

                if modal and self.contain and self.contain_locked:
                    out_of_cointainment_verts = self.get_out_of_cointainment_verts(bm, included_verts=[], consider_offset=False, debug=False)

                    self.locked_coords = [v.co.copy() for v in out_of_cointainment_verts]

    def bend(self, bm, angle=45, offset=0, debug=False):
        side_data = self.get_side_data(bm, debug=False)

        if offset:
            bmesh.ops.translate(bm, verts=bm.verts, vec=(0.0, 0.0, -offset))

        for side, side_dict in side_data.items():

            if not side_dict['verts'] or (side == 'POSITIVE' and not self.positive_bend) or (side == 'NEGATIVE' and not self.negative_bend):
                continue

            if debug:
                print(f"bending {side} side by {angle}")

            side_factor, limit, _ = self.get_side_props(side)

            if limit:
                if debug and limit < 1:
                    print(f"limiting to: {limit * 100}%")

                max_distance = abs(self.dim_data[f"{side}_X"])
                cutoff_distance = max_distance * limit

                bend_factor = radians(self.angle / (max_distance if self.limit_angle else cutoff_distance))

                if debug:
                    print(" max_distance:", max_distance)

                    if limit < 1:
                        print(" cutoff_distance:", cutoff_distance)

                    print(" bend factor:", bend_factor, degrees(bend_factor))

                bend_verts = side_dict['verts']

                if self.contain:
                    bend_verts = side_dict['verts']

                    out_of_cointainment_verts = self.get_out_of_cointainment_verts(bm, included_verts=[], debug=False)

                    for v in out_of_cointainment_verts:
                        bend_verts[v] = {'distance': v.co.x * side_factor}
                
                else:
                    out_of_cointainment_verts = []

                for v, vdata in bend_verts.items():

                    if self.contain and self.contain_locked and v in out_of_cointainment_verts:
                        continue

                    distance = vdata['distance']

                    theta = distance * bend_factor
                    theta_cutoff = cutoff_distance * bend_factor
                    
                    if distance > cutoff_distance or v in out_of_cointainment_verts:
                        if debug:
                            print(" ", v.index, "angle:", degrees(theta_cutoff))

                        v.co.x = -(v.co.z - 1.0 / bend_factor) * sin(theta_cutoff) * side_factor
                        v.co.z = (v.co.z - 1.0 / bend_factor) * cos(theta_cutoff) + 1.0 / bend_factor

                        rot = Quaternion(Vector((0, 1, 0)), -theta_cutoff * side_factor)
                        push = rot @ Vector((side_factor, 0, 0))

                        delta = distance - cutoff_distance
                        v.co += push * delta

                    else:
                        if debug:
                            print(" ", v.index, "angle:", degrees(theta))

                        v.co.x = -(v.co.z - 1.0 / bend_factor) * sin(theta) * side_factor
                        v.co.z = (v.co.z - 1.0 / bend_factor) * cos(theta) + 1.0 / bend_factor

        if offset:
            bmesh.ops.translate(bm, verts=bm.verts, vec=(0.0, 0.0, offset))

    def process_mesh(self, bm, edge_glayer, face_glayer, objtype, angle):
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00001)

        if not self.is_kink and angle in [360, -360]:

            loose_faces = [f for f in bm.faces if all([not e.is_manifold for e in f.edges])]

            if loose_faces:
                bmesh.ops.delete(bm, geom=loose_faces, context="FACES")

        if self.remove_redundant and (self.positive_bisect or self.negative_bisect):
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

            redundant = [e for e in bm.edges if len(e.link_faces) == 2 and round(degrees(e.calc_face_angle()), 4) == 0]

            if redundant:
                bmesh.ops.dissolve_edges(bm, edges=redundant, use_verts=True)

        geo_gzm_angle = 20

        for e in bm.edges:
            if len(e.link_faces) == 2:
                e[edge_glayer] = degrees(e.calc_face_angle()) >= geo_gzm_angle
            else:
                e[edge_glayer] = 1

        for f in bm.faces:
            if objtype == 'CYLINDER' and len(f.edges) == 4:
                f[face_glayer] = 0
            elif not all(e[edge_glayer] for e in f.edges):
                f[face_glayer] = 0
            else:
                f[face_glayer] = any([degrees(e.calc_face_angle(0)) >= geo_gzm_angle for e in f.edges])

        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

def draw_bend_angle_status(op):
    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)

        main_gzm = op.main_gzm
        positive_gzm = op.positive_gzm
        negative_gzm = op.negative_gzm
        is_kink = main_gzm.is_kink

        row.label(text=f"Adjust {'Kink' if is_kink else 'Bend'} Angle")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Confirm")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text=f"Angle: {dynamic_format(main_gzm.angle, decimal_offset=1)}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_CTRL')
        row.label(text=f"Snapped Angle: {op.is_ctrl}")

        if not main_gzm.is_kink and (positive_gzm.bisect or negative_gzm.bisect):
            row.separator(factor=2)

            if positive_gzm.segments == negative_gzm.segments or main_gzm.mirror_bend:
                row.label(text="", icon='MOUSE_MMB')
                row.label(text=f"Segments: {positive_gzm.segments}")

            else:
                if positive_gzm.bisect and negative_gzm.bisect:
                    row.label(text="", icon='MOUSE_MMB')
                    row.label(text=f"Positive Segments: {positive_gzm.segments}")

                    row.separator(factor=2)

                    row.label(text="", icon='MOUSE_MMB')
                    row.label(text=f"Negative Segments: {negative_gzm.segments}")

                elif positive_gzm.bisect:
                    row.label(text="", icon='MOUSE_MMB')
                    row.label(text=f"Positive Segments: {positive_gzm.segments}")

                elif negative_gzm.bisect:
                    row.label(text="", icon='MOUSE_MMB')
                    row.label(text=f"Negative Segments: {negative_gzm.segments}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_R')
        row.label(text="Reset Angle to 0")

    return draw

class AdjustBendAngle(bpy.types.Operator):
    bl_idname = "machin3.adjust_bend_angle"
    bl_label = "MACHIN3: Adjust Bend Angle"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.window_manager.HC_bendCOL

    @classmethod
    def description(cls, context, properties):
        bendCOL = context.window_manager.HC_bendCOL
        return f"Adjust {'Kink' if bendCOL[0].is_kink else 'Bend'} Angle"

    def draw_HUD(self, context):
        if context.area == self.area:
            main_gzm = self.main_gzm

            positive_gzm = self.positive_gzm
            negative_gzm = self.negative_gzm

            draw_init(self)
            draw_label(context, title=f"Adjust {'Kink' if main_gzm.is_kink else 'Bend'} Angle", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

            self.offset += 18
            dims = draw_label(context, title="Angle: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

            color = red if main_gzm.angle in [0, -0] else blue if main_gzm.angle in [360, -360] else white
            dims2 = draw_label(context, title=dynamic_format(main_gzm.angle, decimal_offset=1), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=color, alpha=1)

            if self.is_ctrl:
                draw_label(context, title=" Snapping", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

            if not main_gzm.is_kink and (positive_gzm.bisect or negative_gzm.bisect):
                self.offset += 18

                if positive_gzm.segments == negative_gzm.segments or main_gzm.mirror_bend:
                    dims = draw_label(context, title="Segments: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                    draw_label(context, title=str(positive_gzm.segments), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

                else:
                    if positive_gzm.bisect and negative_gzm.bisect:
                        dims = draw_label(context, title="Segments: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                        dims2 = draw_label(context, title=str(positive_gzm.segments), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)
                        draw_label(context, title=" positive", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, size=10, alpha=0.3)

                        self.offset += 18

                        dims = draw_label(context, title="Segments: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                        dims2 = draw_label(context, title=str(negative_gzm.segments), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)
                        draw_label(context, title=" negative", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, size=10, alpha=0.3)

                    elif positive_gzm.bisect:
                        dims = draw_label(context, title="Segments: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                        draw_label(context, title=str(positive_gzm.segments), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

                    else:
                        dims = draw_label(context, title="Segments: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                        draw_label(context, title=str(negative_gzm.segments), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

            draw_vector(self.mouse_pos.resized(3) - Vector(main_gzm.loc2d).resized(3), origin=Vector(main_gzm.loc2d).resized(3), color=green, fade=True, screen=True)

    def modal(self, context, event):
        if ignore_events(event):
            return {'PASS_THROUGH'}

        context.area.tag_redraw()

        self.is_ctrl = event.ctrl

        events = ['MOUSEMOVE', 'R', *ctrl]

        if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):

            if event.type in ['MOUSEMOVE', *ctrl]:
                get_mouse_pos(self, context, event)

                if self.gzm and self.gzm.draw_options == {'FILL_SELECT'}: 
                    self.gzm.draw_options = {'ANGLE_VALUE'}

                if not (self.positive_gzm.bend or self.negative_gzm.bend):
                    self.positive_gzm.bend = True

                self.delta_angle = self.get_delta_angle(context, self.mouse_pos, debug=False)

                if self.is_ctrl:
                    step = 5

                    angle = self.init_angle + self.delta_angle
                    mod = angle % step

                    self.main_gzm.angle = round(angle + (step - mod) if mod >= (step / 2) else angle - mod)
                
                else:
                    self.main_gzm.angle = self.init_angle + self.delta_angle

            elif scroll_up(event, key=True) or scroll_down(event, key=True):

                if not self.main_gzm.is_kink and (self.positive_gzm.bisect or self.negative_gzm.bisect):
                    if scroll_up(event, key=True):
                        self.positive_gzm.segments += 10 if event.ctrl else 1 
                        self.negative_gzm.segments += 10 if event.ctrl else 1

                    else:
                        self.positive_gzm.segments -= 10 if event.ctrl else 1
                        self.negative_gzm.segments -= 10 if event.ctrl else 1

            elif event.type == 'R' and event.value == 'PRESS':
                self.finish(context)

                self.main_gzm.angle = 0
                return {'FINISHED'}

        elif (event.type == 'LEFTMOUSE' and event.value == 'RELEASE') or event.type == 'SPACE':
            self.finish(context)
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:
            self.finish(context)

            self.main_gzm.angle = self.init_angle
            self.positive_gzm.segments = self.init_positive_segments
            self.negative_gzm.segments = self.init_negative_segments

            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

        self.active.show_wire = False
        
        context.window_manager.HC_bendshowHUD = True

    def invoke(self, context, event):
        self.get_init_props_from_bendCOL(context)

        if self.cmx and self.init_angle is not None and self.init_positive_segments is not None and self.init_negative_segments is not None:

            self.delta_angle = 0
            self.last_angle = 0
            self.accumulated_angle = 0
            
            self.is_ctrl = False

            self.bend_origin = self.cmx.decompose()[0]
            self.bend_axis = self.cmx.to_quaternion() @ Vector((0, 1, 0))

            self.gzm = None
            self.gzm_group = context.gizmo_group

            if self.gzm_group:
                for gzm in self.gzm_group.gizmos:
                    if gzm.bl_idname == 'GIZMO_GT_dial_3d':
                        self.gzm = gzm

            get_mouse_pos(self, context, event)

            self.init_co = self.get_bend_plane_intersection(context, self.mouse_pos)

            if self.init_co:

                self.bend_co = self.init_co

                self.active.show_wire = True

                context.window_manager.HC_bendshowHUD = False

                init_status(self, context, func=draw_bend_angle_status(self))

                self.area = context.area
                self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')

                context.window_manager.modal_handler_add(self)
                return {'RUNNING_MODAL'}

        return {'CANCELLED'}

    def get_init_props_from_bendCOL(self, context):
        self.cmx = None
        self.init_angle = None
        self.init_positive_segments = None
        self.init_negative_segments = None

        self.bendCOL = context.window_manager.HC_bendCOL

        for b in self.bendCOL:
            if b.type == 'MAIN':
                self.main_gzm = b
                self.active = b.obj
                self.cmx = b.cmx

                self.init_angle = b.angle

            elif b.type == 'POSITIVE':
                self.positive_gzm = b
                self.init_positive_segments = b.segments

            elif b.type == 'NEGATIVE':
                self.negative_gzm = b
                self.init_negative_segments = b.segments

    def get_bend_plane_intersection(self, context, mouse_pos):
        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)

        i = intersect_line_plane(view_origin, view_origin + view_dir, self.bend_origin, self.bend_axis)

        return i

    def get_delta_angle(self, context, mouse_pos, debug=False):
        self.bend_co = self.get_bend_plane_intersection(context, mouse_pos)

        if self.bend_co:

            init_dir = (self.init_co - self.bend_origin).normalized()
            bend_dir = (self.bend_co - self.bend_origin).normalized()

            angle = degrees(init_dir.angle(bend_dir))
            deltarot = init_dir.rotation_difference(bend_dir).normalized()

            dot = - round(self.bend_axis.dot(deltarot.axis))

            input_angle = dot * angle

            if input_angle < 0 and self.last_angle > 90:
                self.accumulated_angle += 180

            elif input_angle > 0 and self.last_angle < -90:
                self.accumulated_angle -= 180

            elif input_angle > 0 and -90 < self.last_angle < 0 and self.accumulated_angle:
                self.accumulated_angle += 180

            elif input_angle < 0 and 0 < self.last_angle < 90 and self.accumulated_angle:
                self.accumulated_angle -= 180

            if input_angle < 0 and self.accumulated_angle >= 180:
                delta_angle = self.accumulated_angle + (180 + input_angle)

            elif input_angle > 0 and self.accumulated_angle <= -180:
                delta_angle = self.accumulated_angle - (180 - input_angle)

            else:
                delta_angle = self.accumulated_angle + input_angle

            if debug:
                print("delta angle:", delta_angle)

            self.last_angle = input_angle

            return delta_angle

        return self.delta_angle

def draw_bend_offset_status(op):
    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)

        main_gzm = op.main_gzm
        offset_gzm = op.offset_gzm
        positive_gzm = op.positive_gzm
        negative_gzm = op.negative_gzm

        is_kink = main_gzm.is_kink

        row.label(text=f"Adjust {'Kink' if is_kink else 'Bend'} Offset")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Confirm")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text=f"Offset: {dynamic_format(offset_gzm.offset, decimal_offset=1)}")

        if not main_gzm.is_kink and (positive_gzm.bisect or negative_gzm.bisect):
            row.separator(factor=2)

            if positive_gzm.segments == negative_gzm.segments or main_gzm.mirror_bend:
                row.label(text="", icon='MOUSE_MMB')
                row.label(text=f"Segments: {positive_gzm.segments}")

            else:
                if positive_gzm.bisect and negative_gzm.bisect:
                    row.label(text="", icon='MOUSE_MMB')
                    row.label(text=f"Positive Segments: {positive_gzm.segments}")

                    row.separator(factor=2)

                    row.label(text="", icon='MOUSE_MMB')
                    row.label(text=f"Negative Segments: {negative_gzm.segments}")

                elif positive_gzm.bisect:
                    row.label(text="", icon='MOUSE_MMB')
                    row.label(text=f"Positive Segments: {positive_gzm.segments}")

                elif negative_gzm.bisect:
                    row.label(text="", icon='MOUSE_MMB')
                    row.label(text=f"Negative Segments: {negative_gzm.segments}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_R')
        row.label(text="Reset Offset to 0")

    return draw

class AdjustBendOffset(bpy.types.Operator):
    bl_idname = "machin3.adjust_bend_offset"
    bl_label = "MACHIN3: Adjust Bend Offset"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.window_manager.HC_bendCOL

    @classmethod
    def description(cls, context, properties):
        bendCOL = context.window_manager.HC_bendCOL
        return f"Adjust {'Kink' if bendCOL[0].is_kink else 'Bend'} Offset"

    def draw_HUD(self, context):
        if context.area == self.area:
            main_gzm = self.main_gzm
            offset_gzm = self.offset_gzm

            positive_gzm = self.positive_gzm
            negative_gzm = self.negative_gzm

            draw_init(self)
            draw_label(context, title=f"Adjust {'Kink' if main_gzm.is_kink else 'Bend'} Offset", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

            self.offset += 18
            dims = draw_label(context, title="Offset: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

            color = red if offset_gzm.offset == 0 else white
            dims2 = draw_label(context, title=dynamic_format(offset_gzm.offset, decimal_offset=1), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=color, alpha=1)

            if not main_gzm.is_kink and (positive_gzm.bisect or negative_gzm.bisect):
                self.offset += 18

                if positive_gzm.segments == negative_gzm.segments or self.main_gzm.mirror_bend:
                    dims = draw_label(context, title="Segments: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                    draw_label(context, title=str(positive_gzm.segments), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

                else:
                    if positive_gzm.bisect and negative_gzm.bisect:
                        dims = draw_label(context, title="Segments: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                        dims2 = draw_label(context, title=str(positive_gzm.segments), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)
                        draw_label(context, title=" positive", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, size=10, alpha=0.3)

                        self.offset += 18

                        dims = draw_label(context, title="Segments: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                        dims2 = draw_label(context, title=str(negative_gzm.segments), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)
                        draw_label(context, title=" negative", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, size=10, alpha=0.3)

                    elif positive_gzm.bisect:
                        dims = draw_label(context, title="Segments: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                        draw_label(context, title=str(positive_gzm.segments), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

                    else:
                        dims = draw_label(context, title="Segments: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                        draw_label(context, title=str(negative_gzm.segments), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)
        
    def draw_VIEW3D(self, context):
        if context.area == self.area:
            gzm = self.offset_gzm

            bend_origin = gzm.cmx.to_translation()
            loc = Vector(gzm.loc)

            draw_line([bend_origin, loc], width=2, color=blue)

            factor = gzm.z_factor * 2

            if gzm.offset >= 0:
                draw_vector(self.cursor_z * factor, origin=loc, width=2, color=blue, fade=True)
                draw_vector(-self.cursor_z * factor, origin=bend_origin, width=2, color=blue, fade=True)
            else:
                draw_vector(self.cursor_z * factor, origin=bend_origin, width=2, color=blue, fade=True)
                draw_vector(-self.cursor_z * factor, origin=loc, width=2, color=blue, fade=True)

    def modal(self, context, event):
        if ignore_events(event):
            return {'PASS_THROUGH'}

        context.area.tag_redraw()

        events = ['MOUSEMOVE', 'R', *ctrl]

        if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):

            if event.type in ['MOUSEMOVE', *ctrl]:
                get_mouse_pos(self, context, event)

                co = self.get_cursor_z_intersection(context, self.mouse_pos)

                if co:
                    offset_dir = co - self.init_co

                    dot = self.cursor_z.dot(offset_dir.normalized())

                    offset = offset_dir.length * dot

                    self.offset_gzm.offset = self.init_offset + offset
                    self.offset_gzm.loc = self.init_loc + offset_dir

            elif scroll_up(event, key=True) or scroll_down(event, key=True):
                if not self.main_gzm.is_kink and (self.positive_gzm.bisect or self.negative_gzm.bisect):
                    if scroll_up(event, key=True):
                        self.positive_gzm.segments += 10 if event.ctrl else 1
                        self.negative_gzm.segments += 10 if event.ctrl else 1

                    else:
                        self.positive_gzm.segments -= 10 if event.ctrl else 1
                        self.negative_gzm.segments -= 10 if event.ctrl else 1

            elif event.type == 'R' and event.value == 'PRESS':
                self.finish(context)

                self.offset_gzm.offset = 0
                self.offset_gzm.loc = self.offset_gzm.cmx.to_translation()
                return {'FINISHED'}

        elif (event.type == 'LEFTMOUSE' and event.value == 'RELEASE') or event.type == 'SPACE':
            self.finish(context)
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:
            self.finish(context)

            self.offset_gzm.offset = self.init_offset
            self.offset_gzm.loc = self.init_loc
            self.positive_gzm.segments = self.init_positive_segments
            self.negative_gzm.segments = self.init_negative_segments
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

        self.active.show_wire = False
        
        context.window_manager.HC_bendshowHUD = True

    def invoke(self, context, event):
        self.get_init_props_from_bendCOL(context)

        if self.cmx and self.init_loc:

            get_mouse_pos(self, context, event)

            self.cursor_z = self.cmx.to_quaternion() @ Vector((0, 0, 1))

            self.init_co = self.get_cursor_z_intersection(context, self.mouse_pos)

            if self.init_co:

                self.active.show_wire = True

                context.window_manager.HC_bendshowHUD = False

                init_status(self, context, func=draw_bend_offset_status(self))

                self.area = context.area
                self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
                self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

                context.window_manager.modal_handler_add(self)
                return {'RUNNING_MODAL'}
        
        return {'CANCELLED'}

    def get_init_props_from_bendCOL(self, context):
        self.cmx = None
        self.init_loc = None
        self.init_offset = None
        self.init_positive_segments = None
        self.init_negative_segments = None

        self.bendCOL = context.window_manager.HC_bendCOL

        for b in self.bendCOL:
            if b.type == 'MAIN':
                self.main_gzm = b

            elif b.type == 'OFFSET':
                self.offset_gzm = b
                self.active = b.obj
                self.cmx = b.cmx
                self.init_loc = Vector(b.loc)

                self.init_offset = b.offset

            elif b.type == 'POSITIVE':
                self.positive_gzm = b
                self.init_positive_segments = b.segments

            elif b.type == 'NEGATIVE':
                self.negative_gzm = b
                self.init_negative_segments = b.segments

    def get_cursor_z_intersection(self, context, mouse_pos):
        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)

        i = intersect_line_line(self.init_loc, self.init_loc + self.cursor_z, view_origin, view_origin + view_dir)

        if i:
            return i[0]

def draw_bend_limit_status(op):
    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)

        gzm = op.limit_gzm

        side = gzm.type.title()
        row.label(text=f"Adjust {side} Bend Limit")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Confirm")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text=f"Limit: {dynamic_format(gzm.limit, decimal_offset=1)}")

        if gzm.bisect and gzm.limit > 0:
            row.label(text="", icon='MOUSE_MMB')
            row.label(text=f"Segments: {gzm.segments}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_R')
        row.label(text="Reset Limit to 1")

    return draw

class AdjustBendLimit(bpy.types.Operator):
    bl_idname = "machin3.adjust_bend_limit"
    bl_label = "MACHIN3: Adjust Bend Limit"
    bl_description = "Adjust Bend Limit"
    bl_options = {'REGISTER'}

    side: StringProperty(name="Limit Type", default='POSITIVE')
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.window_manager.HC_bendCOL

    def draw_HUD(self, context):
        if context.area == self.area:
            gzm = self.limit_gzm

            draw_init(self)
            dims = draw_label(context, title=f"Adjust Bend Limit ", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)
            draw_label(context, title=self.side.lower(), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=white, size=10, alpha=0.5)

            self.offset += 18
            dims = draw_label(context, title="Limit: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

            color = red if gzm.limit == 0 else blue if gzm.limit == 1 else white
            dims2 = draw_label(context, title=dynamic_format(gzm.limit, decimal_offset=1), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=color, alpha=1)

            if gzm.bisect and gzm.limit > 0:
                self.offset += 18
                dims = draw_label(context, title="Segments: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
                draw_label(context, title=str(gzm.segments), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            gzm = self.limit_gzm

            bend_origin = gzm.cmx.to_translation()
            loc = Vector(gzm.loc)
            max_loc = self.cmx.to_translation() + self.limit_dir * self.limit_distance

            draw_line([bend_origin, loc], width=2, color=yellow)
            draw_line([bend_origin, max_loc], width=2, color=yellow, alpha=0.2)

    def modal(self, context, event):
        if ignore_events(event):
            return {'PASS_THROUGH'}

        context.area.tag_redraw()

        events = ['MOUSEMOVE', 'R', *ctrl]

        if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):

            if event.type in ['MOUSEMOVE', *ctrl]:
                get_mouse_pos(self, context, event)

                co = self.get_limit_dir_intersection(context, self.mouse_pos)

                if co:
                    limit_dir = co - self.cmx.to_translation() - self.limit_offset_vector

                    dot = self.limit_dir.dot(limit_dir.normalized())

                    if dot > 0:

                        if 0 < limit_dir.length < self.limit_distance:
                            limit = limit_dir.length / self.limit_distance

                        else:
                            limit = 1

                    else:
                        limit = 0

                    self.limit_gzm.limit = limit
                    
                    if limit == 0:
                        self.limit_gzm.loc = self.cmx.to_translation()

                    elif limit == 1:
                        self.limit_gzm.loc = self.cmx.to_translation() + self.limit_dir * self.limit_distance

                    else:
                        self.limit_gzm.loc = co - self.limit_offset_vector

            elif self.limit_gzm.bisect and scroll_up(event, key=True) or scroll_down(event, key=True):

                if scroll_up(event, key=True):
                    self.limit_gzm.segments += 10 if event.ctrl else 1

                elif scroll_down(event, key=True):
                    self.limit_gzm.segments -= 10 if event.ctrl else 1

            elif event.type == 'R' and event.value == 'PRESS':
                self.finish(context)

                self.limit_gzm.limit = 1
                self.limit_gzm.loc = self.cmx.to_translation() + self.limit_dir * self.limit_distance

                return {'FINISHED'}

        if (event.type == 'LEFTMOUSE' and event.value == 'RELEASE') or event.type == 'SPACE':
            self.finish(context)
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:
            self.finish(context)

            self.limit_gzm.limit = self.init_limit
            self.limit_gzm.loc = self.init_loc
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

        self.active.show_wire = False
        
        context.window_manager.HC_bendshowHUD = True

    def invoke(self, context, event):
        self.get_init_props_from_bendCOL(context)

        if self.cmx and self.rot and self.init_loc and self.limit_distance:

            get_mouse_pos(self, context, event)

            self.limit_dir = self.rot @ Vector((0, 0, 1))

            init_co = self.get_limit_dir_intersection(context, self.mouse_pos)

            if init_co:
                self.limit_offset_vector = init_co - self.init_loc
                
                if self.main_gzm.angle:
                    self.active.show_wire = True

                context.window_manager.HC_bendshowHUD = False

                init_status(self, context, func=draw_bend_limit_status(self))

                force_ui_update(context)

                self.area = context.area
                self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
                self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

                context.window_manager.modal_handler_add(self)
                return {'RUNNING_MODAL'}
        
        return {'CANCELLED'}

    def get_init_props_from_bendCOL(self, context):
        self.cmx = None
        self.rot = None

        self.limit_gzm = None
        self.limit_distance = None
        self.init_loc = None
        self.init_limit = None
        self.init_segments = None

        self.bendCOL = context.window_manager.HC_bendCOL

        for b in self.bendCOL:

            if b.type == 'MAIN':
                self.main_gzm = b

            elif b.type == self.side:
                self.limit_gzm = b
                self.active = b.obj
                self.cmx = b.cmx
                self.rot = b.rot
                self.init_loc = Vector(b.loc)

                self.init_limit = b.limit
                self.init_segments = b.segments
                self.limit_distance = b.limit_distance

    def get_limit_dir_intersection(self, context, mouse_pos):
        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)
        
        i = intersect_line_line(self.init_loc, self.init_loc + self.limit_dir, view_origin, view_origin + view_dir)

        if i:
            return i[0]

def draw_bend_containment_status(op):
    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)

        main_gzm = op.main_gzm
        contain_gzm = op.contain_gzm
        is_kink = main_gzm.is_kink

        split = contain_gzm.type.split('_')
        side = f"{split[1].title()} {split[2]}"
        row.label(text=f"Adjust {side} {'Kink' if is_kink else 'Bend'} Containment")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Confirm")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text=f"Contain: {dynamic_format(contain_gzm.limit, decimal_offset=1)}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_R')
        row.label(text="Reset Contain to 1")

    return draw

class AdjustBendContainment(bpy.types.Operator):
    bl_idname = "machin3.adjust_bend_containment"
    bl_label = "MACHIN3: Adjust Bend Containment"
    bl_description = "Adjust Bend Containment"
    bl_options = {'REGISTER'}

    side: StringProperty(name="Containment Side", default='CONTAIN_NEGATIVE_Z')
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.window_manager.HC_bendCOL

    def draw_HUD(self, context):
        if context.area == self.area:
            main_gzm = self.main_gzm
            contain_gzm = self.contain_gzm

            draw_init(self)
            dims = draw_label(context, title=f"Adjust {'Kink' if main_gzm.is_kink else 'Bend'} Containment ", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

            split = self.side.split('_')
            title = f"{split[1].lower()} {split[2]}"
            draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=white, size=10, alpha=0.5)

            self.offset += 18
            dims = draw_label(context, title="Contain: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

            color = red if contain_gzm.limit == 0 else blue if contain_gzm.limit == 1 else white
            dims2 = draw_label(context, title=dynamic_format(contain_gzm.limit, decimal_offset=1), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=color, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            gzm = self.contain_gzm

            bend_origin = gzm.cmx.to_translation()
            loc = Vector(gzm.loc)
            max_loc = self.cmx.to_translation() + self.contain_dir * self.contain_distance

            color = blue if '_Z' in gzm.type else green 
            draw_line([bend_origin, loc], width=2, color=color)
            draw_line([bend_origin, max_loc], width=2, color=color, alpha=0.2)

            if self.coords:
                draw_line(self.coords + [self.coords[0]], color=color)
                draw_tris(self.coords, indices=[(0, 1, 2), (2, 3, 0)], color=color, xray=False, alpha=0.3 if color == blue else 0.15)

    def modal(self, context, event):
        if ignore_events(event):
            return {'PASS_THROUGH'}

        context.area.tag_redraw()

        events = ['MOUSEMOVE', 'R', *ctrl]

        if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):

            if event.type in ['MOUSEMOVE', *ctrl]:
                get_mouse_pos(self, context, event)

                co = self.get_contain_dir_intersection(context, self.mouse_pos)

                if co:
                    contain_dir = co - self.cmx.to_translation() - self.contain_offset_vector

                    dot = self.contain_dir.dot(contain_dir.normalized())

                    if dot > 0:

                        if 0 < contain_dir.length < self.contain_distance:
                            contain = contain_dir.length / self.contain_distance

                        else:
                            contain = 1

                    else:
                        contain = 0

                    self.contain_gzm.limit = contain
                    
                    if contain == 0:
                        self.contain_gzm.loc = self.cmx.to_translation()

                    elif contain == 1:
                        self.contain_gzm.loc = self.cmx.to_translation() + self.contain_dir * self.contain_distance

                    else:
                        self.contain_gzm.loc = co - self.contain_offset_vector

                    self.coords = self.create_contain_plane_coords()

            elif event.type == 'R' and event.value == 'PRESS':
                self.finish(context)

                self.contain_gzm.limit = 1
                self.contain_gzm.loc = self.cmx.to_translation() + self.contain_dir * self.contain_distance

                return {'FINISHED'}

        if (event.type == 'LEFTMOUSE' and event.value == 'RELEASE') or event.type == 'SPACE':
            self.finish(context)
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:
            self.finish(context)

            self.contain_gzm.limit = self.init_contain
            self.contain_gzm.loc = self.init_loc
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

        self.active.show_wire = False
        
        context.window_manager.HC_bendshowHUD = True

    def invoke(self, context, event):
        self.get_init_props_from_bendCOL(context)

        if self.cmx and self.rot and self.init_loc and self.contain_distance:

            get_mouse_pos(self, context, event)

            self.contain_dir = self.rot @ Vector((0, 0, 1))

            init_co = self.get_contain_dir_intersection(context, self.mouse_pos)

            if init_co:
                self.contain_offset_vector = init_co - self.init_loc

                self.coords = self.create_contain_plane_coords()

                if self.main_gzm.angle:
                    self.active.show_wire = True

                context.window_manager.HC_bendshowHUD = False

                init_status(self, context, func=draw_bend_containment_status(self))

                self.area = context.area
                self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
                self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

                context.window_manager.modal_handler_add(self)
                return {'RUNNING_MODAL'}
        
        return {'CANCELLED'}

    def get_init_props_from_bendCOL(self, context):
        other_side = 'Z' if self.side.endswith('_Y') else 'Y'

        self.cmx = None
        self.rot = None

        self.contain_gzm = None
        self.contain_distance = None
        self.init_loc = None
        self.init_contain = None

        self.bendCOL = context.window_manager.HC_bendCOL

        max_distances = []
        self.base_plane_coords = []

        for b in self.bendCOL:

            if b.type == 'MAIN':
                self.main_gzm = b

            elif b.type == self.side:
                self.contain_gzm = b
                self.active = b.obj
                self.cmx = b.cmx
                self.rot = b.rot
                self.init_loc = Vector(b.loc)

                self.init_contain = b.limit
                self.contain_distance = b.limit_distance

            elif b.type == 'POSITIVE':
                max_distances.append(b.limit_distance)

            elif b.type == 'NEGATIVE':
                max_distances.append(-b.limit_distance)

            elif b.type == f'CONTAIN_NEGATIVE_{other_side}':
                max_distances.append(-b.limit_distance)

            elif b.type == f'CONTAIN_POSITIVE_{other_side}':
                max_distances.append(b.limit_distance)

        if self.cmx and len(max_distances) == 4:

            coords = [Vector((max_distances[0], max_distances[3], 0)),
                      Vector((max_distances[1], max_distances[3], 0)),
                      Vector((max_distances[1], max_distances[2], 0)),
                      Vector((max_distances[0], max_distances[2], 0))]

            mx = self.cmx if other_side == 'Y' else self.cmx @ Matrix.Rotation(radians(90), 4, 'X')

            self.base_plane_coords = [mx @ co for co in coords]

    def get_contain_dir_intersection(self, context, mouse_pos):
        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)

        i = intersect_line_line(self.init_loc, self.init_loc + self.contain_dir, view_origin, view_origin + view_dir)

        if i:
            return i[0]

    def create_contain_plane_coords(self):
        contain = self.contain_gzm.limit * self.contain_gzm.limit_distance

        coords = []

        for co in self.base_plane_coords:
            coords.append(co + self.contain_dir * contain)

        return coords

class ToggleBend(bpy.types.Operator):
    bl_idname = "machin3.toggle_bend"
    bl_label = "MACHIN3: Toggle Bend"
    bl_options = {'REGISTER'}

    prop: StringProperty(name="Bend Prop to Toggle")

    @classmethod
    def description(cls, context, properties):
        bendCOL = context.window_manager.HC_bendCOL

        if properties.prop == 'is_kink':
            gzm = bendCOL[0]
            return f"Switch to {'Bending' if gzm.is_kink else 'Kinking'}"

        elif properties.prop == 'use_kink_edges':
            gzm = bendCOL[0]
            return f"{'Disable' if gzm.use_kink_edges else 'Enable'} Kink Constrain to Edges"

        elif properties.prop == 'affect_children':
            gzm = bendCOL[0]
            return f"{'Disable' if gzm.affect_children else 'Enable'} Affect Children"

        elif properties.prop == 'mirror_bend':
            gzm = bendCOL[0]
            return f"{'Disable' if gzm.mirror_bend else 'Enable'} Mirrored Bending"

        elif properties.prop == 'remove_redundant':
            gzm = bendCOL[0]
            return f"{'Disable' if gzm.remove_redundant else 'Enable'} Redundant Edge Removal {'Kinking' if gzm.is_kink else 'Bending'}"

        elif properties.prop == 'positive_bend':
            gzm = bendCOL[2]
            return f"{'Disable' if gzm.bend else 'Enable'} Positive Bending"

        elif properties.prop == 'negative_bend':
            gzm = bendCOL[3]
            return f"{'Disable' if gzm.bend else 'Enable'} Negative Bending"

        elif properties.prop == 'positive_bisect':
            gzm = bendCOL[2]
            return f"{'Disable' if gzm.bisect else 'Enable'} Positive Bisecting"

        elif properties.prop == 'negative_bisect':
            gzm = bendCOL[3]
            return f"{'Disable' if gzm.bisect else 'Enable'} Negative Bisecting"

        return "Nada"

    def execute(self, context):
        bendCOL = context.window_manager.HC_bendCOL

        if self.prop == 'is_kink':
            gzm = bendCOL[0]
            gzm.is_kink = not gzm.is_kink

        elif self.prop == 'affect_children':
            gzm = bendCOL[0]
            gzm.affect_children = not gzm.affect_children

        elif self.prop == 'use_kink_edges':
            gzm = bendCOL[0]
            gzm.use_kink_edges = not gzm.use_kink_edges

        elif self.prop == 'mirror_bend':
            gzm = bendCOL[0]
            gzm.mirror_bend = not gzm.mirror_bend

            pos_gzm = bendCOL[2]
            neg_gzm = bendCOL[3]

            if gzm.mirror_bend:
                neg_gzm.bend = pos_gzm.bend
                neg_gzm.bisect = pos_gzm.bisect

        elif self.prop == 'contain':
            gzm = bendCOL[0]
            gzm.contain = not gzm.contain

        elif self.prop == 'remove_redundant':
            gzm = bendCOL[0]
            gzm.remove_redundant = not gzm.remove_redundant

        elif self.prop == 'positive_bend':
            gzm = bendCOL[2]
            gzm.bend = not gzm.bend

        elif self.prop == 'positive_bisect':
            gzm = bendCOL[2]
            gzm.bisect = not gzm.bisect

        elif self.prop == 'negative_bend':
            gzm = bendCOL[3]
            gzm.bend = not gzm.bend

        elif self.prop == 'negative_bisect':
            gzm = bendCOL[3]
            gzm.bisect = not gzm.bisect

        return {'FINISHED'}
