import bpy
from bpy.props import FloatProperty, BoolProperty, IntProperty, EnumProperty, StringProperty
import bmesh
from mathutils import Vector
from mathutils.geometry import intersect_line_plane, intersect_line_line, intersect_point_line, interpolate_bezier
from math import radians 
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d, location_3d_to_region_2d
from .. utils.select import get_selected_vert_sequences, get_loop_edges, get_edges_vert_sequences
from .. utils.draw import draw_fading_label, draw_vector, draw_point, draw_points, draw_line, draw_lines, draw_label, draw_vectors, draw_init, get_text_dimensions, draw_fading_label
from .. utils.math import average_normals, average_locations, create_rotation_matrix_from_vectors, get_loc_matrix, get_center_between_verts, get_center_between_points, dynamic_format
from .. utils.object import enable_auto_smooth, hide_render, parent, remove_obj, set_obj_origin
from .. utils.system import printd
from .. utils.bmesh import ensure_gizmo_layers
from .. utils.raycast import cast_bvh_ray_from_mouse, get_closest
from .. utils.ui import get_mouse_pos, ignore_events, init_status, finish_status, popup_message, navigation_passthrough, get_zoom_factor, get_mousemove_divisor, wrap_mouse, scroll_up, scroll_down, force_ui_update, force_pick_hyper_bevels_gizmo_update, get_scale
from .. utils.registration import get_addon, get_addon_prefs, get_prefs
from .. utils.modifier import flip_bevel_profile, flop_bevel_profile, move_mod, remove_mod, set_bevel_profile_from_dict, sort_modifiers, add_bevel, add_weld, get_bevel_profile_as_dict
from .. utils.property import get_biggest_index_among_names, step_list
from .. utils.gizmo import hide_gizmos, restore_gizmos
from .. utils.operator import Settings
from .. utils.vgroup import add_vgroup
from .. utils.select import get_edges_vert_sequences
from .. utils.view import get_view_origin_and_dir
from .. colors import normal, yellow, green, blue, green, normal, white, red
from .. items import shift, alt, ctrl, hyperbevel_mode_items, hyperbevel_segment_preset_items, numbers
from time import time

meshmachine = None
machin3tools = None

def draw_hyper_bevel(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text='Hyper Bevel')

        row.label(text="", icon='MOUSE_MOVE')
        row.label(text="Drag out Bevel Width" if op.is_dragging else "Select Edge")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Finish")

        if context.window_manager.keyconfigs.active.name.startswith('blender'):
            row.label(text="", icon='MOUSE_MMB')
            row.label(text="Viewport")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        if op.is_dragging:

            row.label(text="", icon='EVENT_C')
            row.label(text=f"Chamfer: {op.modal_chamfer}")

            if not op.modal_chamfer:
                row.separator(factor=2)
                row.label(text="", icon='EVENT_A')
                row.label(text=f"Adaptvie: {op.modal_adaptive}")

                row.separator(factor=2)
                row.label(text="", icon='MOUSE_MMB')

                if op.modal_adaptive:
                    row.label(text=f"Adaptive Gain: {op.adaptive_gain}")
                else:
                    row.label(text=f"Segments: {op.bevel_segments}")

            row.separator(factor=2)
            row.label(text="", icon='EVENT_Y')
            row.label(text="", icon='EVENT_Z')
            row.label(text="Preset 6")

            row.separator(factor=2)
            row.label(text="", icon='EVENT_X')
            row.label(text="Preset 12")

        else:
            row.label(text="", icon='EVENT_SPACEKEY')
            row.label(text="Repeat Previous HyperBevel")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_SHIFT')
            row.label(text=f"Loop Select: {op.loop}")

            if op.loop:
                row.separator(factor=2)

                row.label(text="", icon='MOUSE_MMB')
                row.label(text=f"Angle: {180 - op.loop_angle}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_ALT')
            row.label(text=f"Weld: {'True' if op.modal_weld else 'False'}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_A')
            row.label(text=f"Add to Selection")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_X')
            row.label(text=f"Remove from Selection")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_W')
        row.label(text=f"Wireframe: {context.active_object.show_wire}")

        if op.is_dragging:
            row.separator(factor=2)

            row.label(text="", icon='EVENT_TAB')
            row.label(text=f"Finish + Invoke HyperMod")

    return draw

class HyperBevel(bpy.types.Operator, Settings):
    bl_idname = "machin3.hyper_bevel"
    bl_label = "MACHIN3: Hyper Bevel"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(name="HyperCut Mode", items=hyperbevel_mode_items, default='SELECTION')
    width: FloatProperty(name='Width', default=0.1, min=0, step=0.1)
    overshoot: FloatProperty(name='Overshoot', default=0.02, min=0, step=0.1)
    def update_align_mids_inbetween(self, context):
        pass

    align_ends: BoolProperty(name='Align Ends', default=True)
    align_mids: BoolProperty(name='Align Mids', default=True)
    align_mids_inbetween: BoolProperty(name='Align Mids Inbetween', default=False, update=update_align_mids_inbetween)
    align_mids_inbetween_threshold: FloatProperty(name='Align Mids Inbetween Threshold', default=0.1, min=0, max=0.5, step=0.1)
    align_mids_centeraim: BoolProperty(name='Align Mids Center Aim', default=False)
    def update_bevel(self, context):
        if self.avoid_update:
            self.avoid_update = False

        if not self.bevel and self.boolean:
            self.boolean = False

    def update_bevel_segments(self, context):
        if not self.bevel:
            self.bevel = True

        if self.chamfer:
            self.avoid_update = True
            self.chamfer = False

        if self.adaptive:
            self.avoid_update = True
            self.adaptive = False

        if self.bevel_segment_preset != 'CUSTOM':
            self.bevel_segment_preset = 'CUSTOM'

    def update_bevel_segment_preset(self, context):
        if not self.bevel:
            self.bevel = True

        if self.chamfer:
            self.avoid_update = True
            self.chamfer = False

        if self.adaptive:
            self.avoid_update = True
            self.adaptive = False

    bevel: BoolProperty(name='Bevel', default=True, update=update_bevel)
    bevel_segments: IntProperty(name='Segments', default=12, min=0, max=100, step=1, update=update_bevel_segments)
    bevel_segment_preset: EnumProperty(name='Segment Preset', items=hyperbevel_segment_preset_items, default='CUSTOM', update=update_bevel_segment_preset)
    def update_adaptive(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.chamfer:
            self.avoid_update = True
            self.chamfer = False

    def update_chamfer(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.adaptive:
            self.avoid_update = True
            self.adaptive = False

    chamfer: BoolProperty(name="Chamfer", default=False, update=update_chamfer)
    adaptive: BoolProperty(name="Adaptive Bevel", default=False, update=update_adaptive)
    adaptive_factor: FloatProperty(name="Adaptive Factor", default=50)
    adaptive_gain: IntProperty(name="Adaptive Gain", default=0, min=0)
    modal_chamfer: BoolProperty(name="Chamfer (Modal)", default=False, update=update_chamfer)
    modal_adaptive: BoolProperty(name="Adaptive Bevel (Modal)", default=False, update=update_adaptive)
    boolean: BoolProperty(name='Add Boolean', default=True)
    boolean_self: BoolProperty(name='Self Boolean', default=False)
    show_wire: BoolProperty(name='Show Wire', default=False)
    weld: BoolProperty(name='Add Weld', default=False)
    edit: BoolProperty(name='Edit Cutter', default=False)
    draw_cutter_creation: BoolProperty(name='Draw Button', default=True)
    draw_non_cyclic_options: BoolProperty(name='Draw Non-Cyclic', default=True)
    draw_bevel_and_boolean: BoolProperty(name='Draw Anything', default=True)

    loop_angle: IntProperty(name="Loop Select Angle", default=140, min=0, max=180)
    dragging: BoolProperty(name="Dragging Width", default=False)
    is_tab_finish: BoolProperty(name="is Tab Finish", default=False)
    avoid_update: BoolProperty()

    @classmethod
    def poll(cls, context):
        return context.mode in ['EDIT_MESH', 'OBJECT'] and context.active_object and context.active_object.type == 'MESH'

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)

        if not self.mode == 'CUTTER':
            column.prop(self, 'edit', text="Edit", toggle=True)
            column.separator()

        if self.draw_cutter_creation or self.edit:
            row = column.row(align=True)
            row.prop(self, 'width')

            if self.draw_non_cyclic_options:
                row.prop(self, 'overshoot')

            row = column.row(align=True)

            if self.draw_non_cyclic_options:
                row.prop(self, 'align_ends', text='Ends', toggle=True)

            row.prop(self, 'align_mids', text='Mids', toggle=True)

            r = row.row(align=True)
            r.active = self.align_mids
            r.prop(self, 'align_mids_inbetween', text='Inbetween', toggle=True)

            rr = r.row(align=True)
            rr.active = self.align_mids_inbetween
            rr.prop(self, 'align_mids_inbetween_threshold', text='')
            rr.prop(self, 'align_mids_centeraim', text='Aim', toggle=True)

            row.prop(self, 'show_wire', text='', icon='SHADING_WIRE', toggle=True)

        if self.draw_bevel_and_boolean:
            column.separator()

            row = column.split(factor=0.5, align=True)
            r = row.split(factor=0.3, align=True)
            rr = r.split(factor=0.5, align=True)
            rr.prop(self, 'chamfer', text='C', toggle=True)
            rr.prop(self, 'adaptive', text='A', toggle=True)
            r.prop(self, 'bevel', toggle=True)

            if self.adaptive:
                row.prop(self, 'adaptive_factor')

                if self.adaptive_gain:
                    row.prop(self, 'adaptive_gain', text='')
            else:
                r = row.row(align=True)
                r.active = not self.chamfer and self.bevel_segment_preset == 'CUSTOM'
                r.prop(self, 'bevel_segments')

            row = column.row(align=True)
            row.active = not self.chamfer and not self.adaptive and self.bevel_segment_preset != 'CUSTOM'
            row.prop(self, 'bevel_segment_preset', expand=True)

            column.separator()

            row = column.split(factor=0.5, align=True)
            row.prop(self, 'boolean', text="Cut", toggle=True)

            r = row.row(align=True)
            r.active = self.boolean
            r.prop(self, 'boolean_self', text="Self", toggle=True)
            r.prop(self, 'weld', text="Weld", toggle=True)

    def draw_VIEW3D(self, context):
        if context.area == self.area:

            if self.is_dragging:
                color = blue if self.modal_chamfer else green if self.modal_adaptive else yellow

                if self.width_coords:
                    draw_lines(self.width_coords, color=color, width=1, alpha=1)

                if self.segment_coords:
                    draw_lines(self.segment_coords, color=color, width=1, alpha=0.2)

            else:
                if self.selected_coords:
                    draw_line(self.selected_coords, color=yellow, width=2, alpha=0.2 if self.is_dragging else 0.99)

                if self.loop_coords:
                    draw_lines(self.loop_coords, color=yellow, width=2, alpha=0.2 if self.is_dragging else 0.4)

                if self.marked_coords:
                    draw_lines(self.marked_coords, color=green, width=2, alpha=0.2 if self.is_dragging else 0.4)

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            dims = draw_label(context, title="Hyper Bevel ", coords=Vector((self.HUD_x, self.HUD_y)), center=False, alpha=1)

            if self.is_dragging:
                draw_label(context, title="Creation", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, alpha=0.5)

                self.offset += 18

                width = dynamic_format(self.width, decimal_offset=2)
                draw_label(context, title=f'Width: {width}', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

                self.offset += 18

                if self.modal_chamfer:
                    draw_label(context, title='Chamfer', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=blue, alpha=1)

                elif self.modal_adaptive:
                    title = f'Adaptive +{self.adaptive_gain}' if self.adaptive_gain else 'Adaptive'
                    draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=green, alpha=1)

                else:
                    segments = self.bevel_segment_preset if self.bevel_segment_preset != 'CUSTOM' else self.bevel_segments
                    draw_label(context, title=f'Segments: {segments}', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

            else:
                draw_label(context, title="Selection", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, alpha=0.5)

                self.offset += 18

                dims = draw_label(context, title="Edge: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, alpha=0.5)

                title = str(self.edge_index) if self.edge_index is not None else "None"
                dims2 = draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=yellow if self.edge_index is not None else red, alpha=1)

                highlighted = self.edge_index
                loop_selected = set(e.index for e in self.selected if e.index != highlighted)
                marked = set(e.index for e in self.marked if e.index != highlighted) - loop_selected

                if loop_selected:
                    dims3 = draw_label(context, title=f" +{len(loop_selected)} Loop Selected", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, size=10, color=yellow, alpha=1)
                else:
                    dims3 = (0, 0)

                if marked:
                    draw_label(context, title=f" +{len(marked)} Marked", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, size=10, color=green, alpha=1)

                if self.loop:
                    self.offset += 18
                    draw_label(context, title=f"Loop Angle: {180 - self.loop_angle}", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

                if self.modal_weld:
                    self.offset += 18
                    draw_label(context, title=f"Weld", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            get_mouse_pos(self, context, event)

        if event.type in ['W'] and event.value == 'PRESS':
            context.active_object.show_wire = not context.active_object.show_wire

        if not self.is_dragging:

            if event.type in ['MOUSEMOVE', *shift, *alt, 'A', 'X'] or scroll_up(event, key=True) or scroll_down(event, key=True):

                self.loop = event.shift

                if event.type in alt and event.value == 'PRESS' and not self.is_dragging:

                    if self.modal_weld:
                        self.active.modifiers.remove(self.modal_weld)
                        self.modal_weld = None

                    else:
                        self.modal_weld = self.add_weld(self.active)

                    self.dg.update()

                    self.init_bmesh(context)

                    self.marked = []
                    self.marked_coords = []

                    for hitlocation, _, loop in self.marked_hits:
                        _, _, _, _, hitindex, _ = get_closest(depsgraph=self.dg, targets=[self.active], origin=hitlocation, debug=False)

                        hit = self.mx.inverted_safe() @ hitlocation
                        hitface = self.bm.faces[hitindex]

                        edge = min([(e, (hit - intersect_point_line(hit, e.verts[0].co, e.verts[1].co)[0]).length, (hit - get_center_between_verts(*e.verts)).length) for e in hitface.edges if e.calc_length()], key=lambda x: (x[1] * x[2]) / x[0].calc_length())[0]

                        self.marked.append(edge)

                        if loop:
                            get_loop_edges(self.loop_angle, self.marked, edge, edge.verts[0], prefer_center_of_three=False, prefer_center_90_of_three=False)
                            get_loop_edges(self.loop_angle, self.marked, edge, edge.verts[1], prefer_center_of_three=False, prefer_center_90_of_three=False)

                    for e in self.marked:
                        self.marked_coords.extend([self.mx @ v.co for v in e.verts])

                if event.type in ['MOUSEMOVE', *shift, *alt] or scroll_up(event, key=True) or scroll_down(event, key=True):

                    if event.shift:
                        if scroll_up(event, key=True):
                            self.loop_angle -= 5

                        elif scroll_down(event, key=True):
                            self.loop_angle += 5

                        force_ui_update(context)

                    self.select_edge_via_raycast()

                elif self.selected and event.type in ['A', 'X']:
                    if event.type == 'A' and event.value == 'PRESS':

                        for e in self.selected:
                            if e not in self.marked:
                                self.marked.append(e)

                        self.marked_hits = [(hit, edge, loop) for hit, edge, loop in self.marked_hits if edge != self.selected[0]]
                        self.marked_hits.append(self.selected_hit)

                    elif event.type == 'X' and event.value == 'PRESS':

                        for e in self.selected:
                            if e in self.marked:
                                self.marked.remove(e)

                        self.marked_hits = [(hit, edge, loop) for hit, edge, loop in self.marked_hits if edge != self.selected[0]]

                    self.marked_coords = []

                    for e in self.marked:
                        self.marked_coords.extend([self.mx @ v.co for v in e.verts])

                self.edges = self.selected + [e for e in self.marked if e not in self.selected]

        if navigation_passthrough(event):
            return {'PASS_THROUGH'}

        if self.edges:

            if self.is_dragging:

                if scroll_up(event, key=True) or scroll_down(event, key=True):

                    if self.modal_adaptive and not self.modal_chamfer:
                        if scroll_up(event, key=True):
                            self.adaptive_gain += 1

                        elif scroll_down(event, key=True):
                            self.adaptive_gain -= 1

                    elif not self.modal_chamfer:
                        self.bevel_segments = self.get_bevel_segments(modal=True)

                        if scroll_up(event, key=True):
                            self.bevel_segments += 1

                        elif scroll_down(event, key=True):
                            self.bevel_segments -= 1

                    force_ui_update(context)

                elif event.type == 'C' and event.value == 'PRESS':
                    self.modal_chamfer = not self.modal_chamfer

                elif event.type in ['Y', 'Z'] and event.value == 'PRESS':
                    self.modal_adaptive = False
                    self.modal_chamfer = False
                    self.bevel_segments = 6

                elif event.type in ['X'] and event.value == 'PRESS':
                    self.modal_adaptive = False
                    self.modal_chamfer = False
                    self.bevel_segments = 12

                elif event.type in ['A'] and event.value == 'PRESS':

                    if self.modal_chamfer:

                        if self.modal_adaptive:
                            self.modal_chamfer = False

                    else:
                        self.modal_adaptive = not self.modal_adaptive

                        if self.modal_adaptive:
                            self.adaptive_factor = self.get_fixed_bevel_segments() / self.width

                self.get_bevel_width(context)

                self.get_previz_coords()

                if event.type in {'LEFTMOUSE', 'SPACE', 'TAB'}:
                    self.finish(context)

                    self.set_operator_props_from_modal()

                    if props := self._properties.get('machin3.hyper_bevel'):
                        del self._properties['machin3.hyper_bevel']

                    self.is_tab_finish = event.type == 'TAB'

                    return self.execute(context)

            else:

                if event.type == 'LEFTMOUSE' and event.value == 'PRESS':

                    self.is_dragging = True

                    self.active.select_set(True)

                    self.get_bevel_width(context)

                    self.get_previz_coords()
                    return {'RUNNING_MODAL'}

                elif event.type in {'R', 'SPACE'}:
                    self.finish(context)
                    self.set_operator_props_from_modal()
                    return self.execute(context)

        if event.type in {'RIGHTMOUSE', 'ESC'} or (not self.edges and event.type in {'LEFTMOUSE', 'SPACE'}):
            self.finish(context)

            self.active.select_set(True)
            
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

        self.weld = True if self.modal_weld else False

        if self.modal_weld:
            self.active.modifiers.remove(self.modal_weld)

        restore_gizmos(self)

    def invoke(self, context, event):
        wm = context.window_manager

        if wm.HC_pickhyperbevelsCOL:
            wm.gizmo_group_type_unlink_delayed('MACHIN3_GGT_pick_hyper_bevel')

            wm.HC_pickhyperbevelsCOL.clear()

        self.mode = 'RAYCAST' if context.mode == 'OBJECT' else 'CUTTER' if context.active_object.HC.ishyperbevel else 'SELECTION'
        self.overshoot = 0.1

        self.avoid_update = True
        self.bevel = context.active_object.HC.ishyperbevel

        self.boolean = False
        self.boolean_self = False

        self.weld = self.chamfer or self.modal_chamfer

        self.align_ends = True
        self.align_mids = True
        self.align_mids_inbetween = False
        self.align_mids_inbetween_threshold = 0.1
        self.align_mids_centeraim = False

        self.adaptive_gain = 0

        self.init = True
        self.edit = False

        self.draw_cutter_creation = not context.active_object.HC.ishyperbevel
        self.draw_bevel_and_boolean = True

        self.show_wire = context.active_object.show_wire

        if context.mode == 'OBJECT':

            self.active = context.active_object

            if self.chamfer or self.modal_chamfer:
                self.modal_weld = self.add_weld(self.active)

            else:
                self.modal_weld = None

            self.dg = context.evaluated_depsgraph_get()
            self.mx = context.active_object.matrix_world

            self.selected = []
            self.marked = []
            self.loop = False
            self.edge_index = False

            self.selected_hit = (None, None, False)
            self.marked_hits = []

            self.is_dragging = False
            self.drag_origin = None
            self.drag_normal = None

            hide_gizmos(self, context)

            self.init_bmesh(context)

            self.selected_coords = []
            self.marked_coords = []
            self.loop_coords = []
            self.width_coords = []
            self.segment_coords = []

            get_mouse_pos(self, context, event)

            self.select_edge_via_raycast()
            self.edges = self.selected

            init_status(self, context, func=draw_hyper_bevel(self))

            force_ui_update(context)

            self.area = context.area
            self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
            self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:
            return self.execute(context)

    def execute(self, context):
        active = context.active_object

        if self.mode == 'RAYCAST':

            verts = list({v for e in self.edges for v in e.verts})
            sequences = get_edges_vert_sequences(verts, self.edges, debug=False)

            self.full_cut(context, active, self.bm, sequences, debug=False)

        elif self.mode == 'CUTTER':

            active = self.partial_cut(context)

        elif self.mode == 'SELECTION':

            bm = bmesh.from_edit_mesh(active.data)
            bm.normal_update()
            bm.verts.ensure_lookup_table()

            verts = [v for v in bm.verts if v.select]
            sequences = get_selected_vert_sequences(verts, debug=False)

            self.full_cut(context, active, bm, sequences, debug=False)

        if self.boolean and not self.edit:
            sort_modifiers(active, debug=False)

        if self.mode == 'RAYCAST' and self.is_tab_finish:
            bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')

        return {'FINISHED'}

    def get_bevel_segments(self, offset=0, modal=False):
        if modal:
            if self.modal_chamfer:
                return offset
            elif self.modal_adaptive:
                return self.get_adaptive_bevel_segments(offset)
            else:
                return self.get_fixed_bevel_segments(offset)

        else:
            if self.chamfer:
                return offset
            elif self.adaptive:
                return self.get_adaptive_bevel_segments(offset)
            else:
                return self.get_fixed_bevel_segments(offset)

    def get_fixed_bevel_segments(self, offset=0):
        segments = self.bevel_segments if self.bevel_segment_preset == 'CUSTOM' else int(self.bevel_segment_preset)
        return segments + offset

    def get_adaptive_bevel_segments(self, offset=0):
        segments = int(self.width * self.adaptive_factor) + self.adaptive_gain
        return segments + offset

    def get_bevel_width(self, context):
        view_origin = region_2d_to_origin_3d(context.region, context.region_data, self.mouse_pos)
        view_dir = region_2d_to_vector_3d(context.region, context.region_data, self.mouse_pos)

        i = intersect_line_plane(view_origin, view_origin + view_dir, self.drag_origin, self.drag_normal)

        if i:
            edge = self.edges[0]

            intersect = self.mx.inverted_safe() @ i

            i = intersect_point_line(intersect, *[v.co for v in edge.verts])

            if i:
                closest = i[0]

                self.width = (closest - intersect).length

    def set_operator_props_from_modal(self):
        self.avoid_update = True
        self.bevel = True
        self.boolean = True

        self.avoid_update = True
        self.chamfer = self.modal_chamfer

        self.avoid_update = True
        self.adaptive = self.modal_adaptive

    def init_bmesh(self, context):
        self.mesh = bpy.data.meshes.new_from_object(self.active.evaluated_get(self.dg), depsgraph=self.dg)

        self.bm = bmesh.new()
        self.bm.from_mesh(self.mesh)
        self.bm.normal_update()
        self.bm.verts.ensure_lookup_table()
        self.bm.faces.ensure_lookup_table()

        self.bmeshes = {self.active.name: [self.bm]}
        self.bvhs = {}

    def select_edge_via_raycast(self):
        hitobj, hitlocation, hitnormal, hitindex, hitdistance, cache = cast_bvh_ray_from_mouse(self.mouse_pos, candidates=[self.active], bmeshes=self.bmeshes, bvhs=self.bvhs, debug=False)

        self.loop_coords = []
        self.selected_coords = []
        self.edge_index = None

        self.selected = []
        self.selected_hit = (None, None, False)

        if hitobj:

            for name, bvh in cache['bvh'].items():
                if name not in self.bvhs:
                    self.bvhs[name] = bvh

            hit = self.mx.inverted_safe() @ hitlocation

            hitface = self.bm.faces[hitindex]

            edge = min([(e, (hit - intersect_point_line(hit, e.verts[0].co, e.verts[1].co)[0]).length, (hit - get_center_between_verts(*e.verts)).length) for e in hitface.edges if e.calc_length()], key=lambda x: (x[1] * x[2]) / x[0].calc_length())[0]
            self.edge_index = edge.index
            self.selected.append(edge)

            self.selected_hit = (hitlocation, edge, self.loop)

            self.selected_coords = [self.mx @ v.co for v in edge.verts]

            if self.loop:
                get_loop_edges(self.loop_angle, self.selected, edge, edge.verts[0], prefer_center_of_three=False, prefer_center_90_of_three=False)
                get_loop_edges(self.loop_angle, self.selected, edge, edge.verts[1], prefer_center_of_three=False, prefer_center_90_of_three=False)

                self.loop_coords = [self.mx @ v.co for le in [e for e in self.selected if e != edge] for v in le.verts]

            self.drag_origin = hitlocation
            self.drag_normal = hitnormal

    def get_previz_coords(self):
        self.width_coords = []
        self.segment_coords = []

        for edge in self.edges:
            face_dirs = []

            for face in edge.link_faces:
                center = face.calc_center_median()
                i = intersect_point_line(center, edge.verts[0].co, edge.verts[1].co)

                if i:
                    face_dir = (center - i[0]).normalized()

                    face_dirs.append(face_dir)

                    for v in edge.verts:
                        self.width_coords.append(self.mx @ (v.co + face_dir * self.width))

            if len(face_dirs) == 2:
                face_dir1 = face_dirs[0]
                face_dir2 = face_dirs[1]

                v1coords = []
                v2coords = []

                for idx, v in enumerate(edge.verts):
                    co1 = v.co + face_dir1 * self.width
                    co2 = v.co + face_dir2 * self.width

                    handle1 = co1 + (v.co - co1) * 0.8
                    handle2 = co2 + (v.co - co2) * 0.8

                    if idx == 0:
                        v1coords.extend(interpolate_bezier(co1, handle1, handle2, co2, self.get_bevel_segments(offset=2, modal=True)))
                    else:
                        v2coords.extend(interpolate_bezier(co1, handle1, handle2, co2, self.get_bevel_segments(offset=2, modal=True)))

                for co1, co2 in zip(v1coords, v2coords):
                    self.segment_coords.extend([self.mx @ co1, self.mx @ co2])

    def get_data(self, bm, sequences):
        data = {}

        for sidx, (seq, cyclic) in enumerate(sequences):
            data[sidx] = {'cyclic': cyclic, 'convex': None, 'verts': seq, 'edges': []}

            for vidx, v in enumerate(seq):
                prev_vert = seq[(vidx - 1) % len(seq)]
                next_vert = seq[(vidx + 1) % len(seq)]

                data[sidx][v] = {'co': v.co.copy(),
                                 'no': v.normal.copy(),
                                 'dir': None,
                                 'cross': None,

                                 'prev_vert': prev_vert,
                                 'next_vert': next_vert,
                                 'prev_edge': None,
                                 'next_edge': None,

                                 'loop': None,
                                 'left_face': None,
                                 'left_face_dir': None,
                                 'right_face': None,
                                 'right_face_dir': None,

                                 'left_edge_dir': None,
                                 'right_edge_dir': None,

                                 'prev_left_edge_dir': None,
                                 'prev_left_edge_co': None,
                                 'prev_left_edge_distance': None,
                                 'next_left_edge_dir': None,
                                 'next_left_edge_co': None,
                                 'next_left_edge_distance': None,
                                 'prev_right_edge_dir': None,
                                 'prev_right_edge_co': None,
                                 'prev_right_edge_distance': None,
                                 'next_right_edge_dir': None,
                                 'next_right_edge_co': None,
                                 'next_right_edge_distance': None,

                                 'left_inbetween_dir': None,
                                 'left_inbetween_dot': None,
                                 'left_inbetween_ratios': [],
                                 'right_inbetween_dir': None,
                                 'right_inbetween_dot': None,
                                 'right_inbetween_ratios': [],

                                 'left_centeraim_dir': None,
                                 'right_centeraim_dir': None}

            if not cyclic:
                data[sidx][seq[0]]['prev_vert'] = None
                data[sidx][seq[-1]]['next_vert'] = None

            for idx, v in enumerate(seq):
                vdata = data[sidx][v]

                self.get_next_and_prev_edges(bm, v, data, vdata, sidx)

                if idx == 0:
                    edge = data[sidx]['edges'][0]
                    data[sidx]['convex'] = edge.calc_face_angle_signed(1) >= 0

                self.get_directions(data, vdata, sidx)

                self.get_loop_and_faces(v, data, vdata, sidx)

                self.get_left_and_right_face_directions(vdata)

                self.get_aligned_edge_directions(v, data, vdata, sidx, debug=False)

            for v in seq:
                self.get_next_and_prev_aligned_edge_directions(v, data, sidx, debug=False)

            for v in seq:
                self.get_inbetween_and_centeraim_directions(v, data, sidx, debug=False)

        return data

    def get_next_and_prev_edges(self, bm, v, data, vdata, sidx):
        if vdata['next_vert']:
            edge = bm.edges.get([v, vdata['next_vert']])
            vdata['next_edge'] = edge

            if edge not in data[sidx]['edges']:
                data[sidx]['edges'].append(edge)

        if vdata['prev_vert']:
            edge = bm.edges.get([v, vdata['prev_vert']])
            vdata['prev_edge'] = edge

            if edge not in data[sidx]['edges']:
                data[sidx]['edges'].append(edge)

    def get_directions(self, data, vdata, sidx):
        if vdata['prev_vert'] and vdata['next_vert']:
            vdir = ((vdata['next_vert'].co - vdata['co']).normalized() + (vdata['co'] - vdata['prev_vert'].co).normalized()).normalized()
            vdata['dir'] = vdir

        elif vdata['next_vert']:
            vdir = (vdata['next_vert'].co - vdata['co']).normalized()
            vdata['dir'] = vdir

        else:
            vdir = (vdata['co'] - vdata['prev_vert'].co).normalized()
            vdata['dir'] = vdir

        vdata['cross'] = vdata['no'].cross(vdir).normalized()

    def get_loop_and_faces(self, v, data, vdata, sidx):
        if vdata['next_edge']:
            edge = vdata['next_edge']
            loops = [l for l in edge.link_loops if l.vert == v]

            vdata['loop'] = loops[0]
            vdata['left_face'] = loops[0].face
            vdata['right_face'] = loops[0].link_loop_radial_next.face

        else:
            vdata['loop'] = data[sidx][vdata['prev_vert']]['loop']
            vdata['left_face'] = data[sidx][vdata['prev_vert']]['left_face']
            vdata['right_face'] = data[sidx][vdata['prev_vert']]['right_face']

    def get_left_and_right_face_directions(self, vdata):
        i = intersect_line_plane(vdata['co'] + vdata['cross'], vdata['co'] + vdata['cross'] + vdata['left_face'].normal, vdata['co'], vdata['left_face'].normal)
        vdata['left_face_dir'] = (i - vdata['co']).normalized()

        i = intersect_line_plane(vdata['co'] - vdata['cross'], vdata['co'] - vdata['cross'] + vdata['right_face'].normal, vdata['co'], vdata['right_face'].normal)
        vdata['right_face_dir'] = (i - vdata['co']).normalized()

    def get_aligned_edge_directions(self, v, data, vdata, sidx, debug=False):

        connected_edges = [e for e in v.link_edges if e not in data[sidx]['edges']]

        if connected_edges:

            for side in ['left', 'right']:
                edges = [e for e in connected_edges if vdata.get(f'{side}_face') in e.link_faces]

                if edges:
                    edge_dir = (edges[0].other_vert(v).co - vdata['co']).normalized()
                    dot = edge_dir.dot(vdata['dir'])

                    middot = 0.99
                    enddot = 0.98

                    if abs(dot) < (enddot if not all([vdata['prev_vert'], vdata['next_vert']]) else middot):
                        co1 = vdata['co'] + vdata.get(f'{side}_face_dir')
                        co2 = co1 + vdata['dir']
                        co3 = vdata['co']
                        co4 = co3 + edge_dir

                        i = intersect_line_line(co1, co2, co3, co4)
                        if i:
                            aligned_edge_dir = i[1] - vdata['co']
                            vdata[f'{side}_edge_dir'] = aligned_edge_dir

                            if debug:
                                draw_vector(aligned_edge_dir * 0.1, origin=vdata['co'], mx=bpy.context.active_object.matrix_world, color=(1, 0, 1), width=2, modal=False)
                                draw_vector(edge_dir * 0.1, origin=vdata['co'], mx=bpy.context.active_object.matrix_world, width=2, modal=False)

    def get_next_and_prev_aligned_edge_directions(self, v, data, sidx, debug=False):

        if debug:
            print()
            print(v)

        for side in ['left', 'right']:
            if debug:
                print("", side)

            for direction in ['next', 'prev']:
                if debug:
                    print(" ", direction)

                vdata = data[sidx][v]
                co = vdata['co'].copy()
                distance = 0
                c = 0

                while vdata[f'{direction}_vert'] and not vdata[f'{side}_edge_dir']:
                    c += 1

                    vdata = data[sidx][vdata[f'{direction}_vert']]
                    edge_dir = vdata[f'{side}_edge_dir']

                    distance += (vdata['co'] - co).length
                    co = vdata['co'].copy()

                    if edge_dir:
                        if debug:
                            print("   edge_dir:", edge_dir)
                            print("         co:", co)
                            print("   distance:", distance)

                        data[sidx][v][f'{direction}_{side}_edge_dir'] = edge_dir.normalized()
                        data[sidx][v][f'{direction}_{side}_edge_co'] = co
                        data[sidx][v][f'{direction}_{side}_edge_distance'] = distance

                    if data[sidx]['cyclic'] and c > len(data[sidx]['verts']):
                        break

    def get_inbetween_and_centeraim_directions(self, v, data, sidx, debug=False):

        if debug:
            print()
            print(v.index)

        for side in ['left', 'right']:

            vdata = data[sidx][v]

            if not vdata[f'{side}_edge_dir'] and vdata[f'next_{side}_edge_dir'] and vdata[f'prev_{side}_edge_dir']:

                prev_dir = vdata[f'prev_{side}_edge_dir']
                next_dir = vdata[f'next_{side}_edge_dir']

                prev_co = vdata[f'prev_{side}_edge_co']
                next_co = vdata[f'next_{side}_edge_co']

                prev_distance = vdata[f'prev_{side}_edge_distance']
                next_distance = vdata[f'next_{side}_edge_distance']

                if debug:
                    print("        dir:", prev_dir, next_dir)
                    print("         co:", prev_co, next_co)
                    print("   distance:", prev_distance, next_distance)

                inbetween_dir = average_normals([edge_dir * (1 - distance / (prev_distance + next_distance)) for edge_dir, distance in zip([prev_dir, next_dir], [prev_distance, next_distance])])

                centeraim_dir = (get_center_between_points(prev_co, next_co) - vdata['co']).normalized()

                co1 = vdata['co'] + vdata.get(f'{side}_face_dir')
                co2 = co1 + vdata['dir']
                co3 = vdata['co']
                co4 = co3 + inbetween_dir

                i = intersect_line_line(co1, co2, co3, co4)

                if i:
                    corrected_inbetween_dir = i[1] - vdata['co']
                    vdata[f'{side}_inbetween_dir'] = corrected_inbetween_dir

                    vdata[f'{side}_inbetween_dot'] = prev_dir.dot(next_dir)
                    vdata[f'{side}_inbetween_ratios'] = [1 - prev_distance / (prev_distance + next_distance), 1 - next_distance / (prev_distance + next_distance)]

                    if debug:
                        draw_vector(corrected_inbetween_dir * 0.1, origin=vdata['co'], mx=bpy.context.active_object.matrix_world, color=(0, 1, 1), width=2, modal=False)
                        draw_vector(inbetween_dir * 0.1, origin=vdata['co'], mx=bpy.context.active_object.matrix_world, color=(1, 0, 1), width=2, modal=False)

                co4 = co3 + centeraim_dir

                i = intersect_line_line(co1, co2, co3, co4)
                if i:
                    corrected_centeraim_dir = i[1] - vdata['co']
                    vdata[f'{side}_centeraim_dir'] = corrected_centeraim_dir

                    if debug:
                        draw_vector(corrected_centeraim_dir * 0.1, origin=vdata['co'], mx=bpy.context.active_object.matrix_world, color=(0, 1, 1), width=2, modal=False)
                        draw_vector(centeraim_dir * 0.1, origin=vdata['co'], mx=bpy.context.active_object.matrix_world, color=(1, 0, 1), width=2, modal=False)

    def debug_data(self, context, data, mx, factor=0.1):
        printd(data, 'data dict')

        for sidx, selection in data.items():
            for idx, v in enumerate(selection['verts']):
                co = selection[v]['co']
                no = selection[v]['no']
                vdir = selection[v]['dir']
                cross = selection[v]['cross']

                draw_vector(no * factor, origin=co, mx=mx, color=normal, modal=False)
                draw_vector(vdir * factor, origin=co, mx=mx, color=(1, 1, 0), modal=False)

                draw_vector(cross * factor / 3, origin=co, mx=mx, color=(0, 1, 0), alpha=0.5, modal=False)
                draw_vector(-cross * factor / 3, origin=co, mx=mx, color=(1, 0, 0), alpha=0.5, modal=False)

                for side in ['left', 'right']:

                    face_dir = selection[v][f'{side}_face_dir']
                    edge_dir = selection[v][f'{side}_edge_dir']
                    inbetween_dir = selection[v][f'{side}_inbetween_dir']
                    centeraim_dir = selection[v][f'{side}_centeraim_dir']

                    draw_vector(face_dir * factor, origin=co, mx=mx, color=(0, 1, 0) if side == 'left' else (1, 0, 0), modal=False)

                    if edge_dir:
                        draw_vector(edge_dir * factor, origin=co, mx=mx, width=2, modal=False)

                    if inbetween_dir:
                        draw_vector(inbetween_dir * factor, origin=co, mx=mx, color=(0, 0, 1), width=1, modal=False)

                    if centeraim_dir:
                        draw_vector(centeraim_dir * factor, origin=co, mx=mx, color=(0, 1, 1), width=1, modal=False)

        context.area.tag_redraw()

    def get_geo_from_data(self, data, mx):
        geo = {}

        for sidx, selection in data.items():
            cutter = {'cyclic': selection['cyclic'],
                      'convex': selection['convex'],
                      'length': len(selection['verts']),
                      'verts': {},
                      'face_indices': [],
                      'center_edge_indices': [],
                      'overshoot_start': None,
                      'overshoot_end': None,
                      'mx': None}

            for idx, v in enumerate(selection['verts']):
                vdata = selection[v]

                if idx == 0:
                    if selection['convex']:
                        cutter['overshoot_start'] = - vdata['dir'] * vdata['next_edge'].calc_length()
                    else:
                        cutter['overshoot_start'] = Vector()

                elif idx == cutter['length'] - 1:
                    if selection['convex']:
                        cutter['overshoot_end'] = vdata['dir'] * vdata['prev_edge'].calc_length()
                    else:
                        cutter['overshoot_end'] = Vector()

                for i in range(3):
                    vidx = str(3 * idx + i)

                    cutter['verts'][vidx] = {'co': vdata['co'],
                                             'side': None,
                                             'offset': None,
                                             'offset_edge_aligned': None,

                                             'offset_inbetween_aligned': None,
                                             'offset_inbetween_dot': None,
                                             'offset_inbetween_ratios': [],

                                             'offset_centeraim_aligned': None}

                    if i == 1:
                        cutter['verts'][vidx]['side'] = 'CENTER'

                    else:
                        side = {0: 'left', 2: 'right'}[i]

                        cutter['verts'][vidx]['side'] = side.capitalize()
                        cutter['verts'][vidx]['offset'] = vdata[f'{side}_face_dir']

                        if vdata[f'{side}_edge_dir']:
                            cutter['verts'][vidx]['offset_edge_aligned'] = vdata[f'{side}_edge_dir']

                        if vdata[f'{side}_inbetween_dir']:
                            cutter['verts'][vidx]['offset_inbetween_aligned'] = vdata[f'{side}_inbetween_dir']
                            cutter['verts'][vidx]['offset_inbetween_dot'] = vdata[f'{side}_inbetween_dot']
                            cutter['verts'][vidx]['offset_inbetween_ratios'] = vdata[f'{side}_inbetween_ratios']

                        if vdata[f'{side}_centeraim_dir']:
                            cutter['verts'][vidx]['offset_centeraim_aligned'] = vdata[f'{side}_centeraim_dir']

                if idx < cutter['length'] - 1:

                    cutter['face_indices'].append([3 * idx + i for i in [0, 1, 4, 3]])
                    cutter['face_indices'].append([3 * idx + i for i in [1, 2, 5, 4]])

                    cutter['center_edge_indices'].append([3 * idx + 1, 3 * (idx + 1) + 1])

                elif cutter['cyclic']:
                    cutter['face_indices'].append([cutter['length'] * 3 - 3, cutter['length'] * 3 - 2, 1, 0])
                    cutter['face_indices'].append([cutter['length'] * 3 - 2, cutter['length'] * 3 - 1, 2, 1])

                    cutter['center_edge_indices'].append([cutter['length'] * 3 - 2, 1])

            loc = mx @ average_locations([selection[v]['co'] for v in selection['verts']])

            normal = (mx.to_quaternion() @ average_normals([selection[v]['no'] for v in selection['verts']])).normalized()
            binormal = (mx.to_quaternion() @ average_normals([selection[v]['dir'] for v in selection['verts']])).normalized()
            tangent = binormal.cross(normal).normalized()
            normal = tangent.cross(binormal).normalized()

            rot = create_rotation_matrix_from_vectors(tangent, binormal, normal)
            cutter['mx'] = get_loc_matrix(loc) @ rot.to_4x4()

            geo[sidx] = cutter

        return geo

    def debug_geo(self, context, geo, mx, factor=0.1):
        printd(geo, 'geo dict')

        for sidx, geometry in geo.items():
            for idx, vdata in geometry['verts'].items():
                if vdata['side'] == 'CENTER':
                    draw_point(vdata['co'], mx=mx, size=8, modal=False)

                else:
                    draw_point(vdata['co'] + vdata['offset'] * factor, mx=mx, color=(1, 1, 0), size=6, modal=False)

                    if vdata['offset_edge_aligned']:
                        draw_point(vdata['co'] + vdata['offset_edge_aligned'] * factor, mx=mx, color=(0, 1, 0), size=5, modal=False)

                    if vdata['offset_inbetween_aligned']:
                        draw_point(vdata['co'] + vdata['offset_inbetween_aligned'] * factor, mx=mx, color=(0, 0, 1), size=4, modal=False)

                    if vdata['offset_centeraim_aligned']:
                        draw_point(vdata['co'] + vdata['offset_centeraim_aligned'] * factor, mx=mx, color=(0, 1, 1), size=3, modal=False)

            cmx = geometry['mx']
            loc = cmx.to_translation()

            tangent = cmx.col[0].xyz
            binormal = cmx.col[1].xyz
            normal = cmx.col[2].xyz

            draw_point(loc, size=8, color=(0, 1, 0), modal=False)

            draw_vector(normal, origin=loc, color=(0, 0, 1), modal=False)
            draw_vector(binormal, origin=loc, color=(0, 1, 0), modal=False)
            draw_vector(tangent, origin=loc, color=(1, 0, 0), modal=False)

        context.area.tag_redraw()

    def create_cutter(self, context, active, geometry, edit=False):
        cutter = active.copy()
        cutter.data = bpy.data.meshes.new(name="Hyper Bevel")
        context.scene.collection.objects.link(cutter)

        enable_auto_smooth(cutter)

        cutter.HC.ishyperbevel = True
        cutter.modifiers.clear()

        global meshmachine

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        if meshmachine:
            cutter.MM.stashes.clear()

        cutter.name = "Hyper Bevel"
        cutter.display_type = 'WIRE'
        hide_render(cutter, True)

        parent(cutter, active)

        cutter.HC.ishyper = True
        cutter.HC.objtype = 'CUBE'
        cutter.HC.geometry_gizmos_show = True

        bm = bmesh.new()
        bm.from_mesh(cutter.data)

        edge_glayer, face_glayer = ensure_gizmo_layers(bm)

        verts = []
        faces = []

        for idx, vdata in geometry['verts'].items():
            if vdata['side'] == 'CENTER':
                verts.append(bm.verts.new(vdata['co']))
            else:
                verts.append(bm.verts.new(vdata['co'] + vdata['offset'] * self.width))

        for indices in geometry['face_indices']:
            faces.append(bm.faces.new([verts[i] for i in indices]))

        align_indices = []

        if self.align_ends or (self.align_mids and geometry['cyclic']):
            vert_count = len(verts)
            align_indices.extend([0, 2, vert_count - 3, vert_count - 1])

        if self.align_mids:
            if geometry['length'] > 2:
                for l in range(1, geometry['length'] - 1):
                    align_indices.extend([l * 3, l * 3 + 2])

        for idx in align_indices:
            v = verts[idx]
            vdata = geometry['verts'][str(idx)]

            if vdata['offset_edge_aligned']:
                v.co = vdata['co'] + vdata['offset_edge_aligned'] * self.width

            elif self.align_mids_inbetween and vdata['offset_inbetween_aligned']:

                dot = vdata['offset_inbetween_dot']
                ratio = min(vdata['offset_inbetween_ratios'])

                if not (dot < - 0.97 and self.align_mids_inbetween_threshold < ratio):
                    v.co = vdata['co'] + vdata['offset_inbetween_aligned'] * self.width

                elif self.align_mids_centeraim and vdata['offset_centeraim_aligned']:
                    v.co = vdata['co'] + vdata['offset_centeraim_aligned'] * self.width

        if not geometry['cyclic'] and self.overshoot:
            for idx in [0, 1, 2]:
                verts[idx].co = verts[idx].co + geometry['overshoot_start'] * self.overshoot

            for idx in [-3, -2, -1]:
                verts[idx].co = verts[idx].co + geometry['overshoot_end'] * self.overshoot

        center_edges = [bm.edges.get([verts[idx] for idx in indices]) for indices in geometry['center_edge_indices']]

        for e in center_edges:
            e[edge_glayer] = 1

        center_vert_ids = []

        if not edit:
            self.extrude_cutter(cutter, bm, verts, faces, geometry, edge_glayer, face_glayer)

            if self.bevel or self.boolean:
                cutter.HC.ishyperbevel = False
        
        bm.to_mesh(cutter.data)
        bm.free()

        if not edit:
            if self.bevel:
                center_vert_ids = [int(vidx) for vidx in geometry['verts'] if geometry['verts'][vidx]['side'] == 'CENTER']

                vgroup = add_vgroup(cutter, 'Edge Bevel', ids=center_vert_ids, weight=1)

                bevel_mod = add_bevel(cutter, name="Edge Bevel", width=0, limit_method='VGROUP', vertex_group=vgroup.name)
                bevel_mod.offset_type = 'PERCENT'
                bevel_mod.width_pct = 100
                bevel_mod.segments = self.get_bevel_segments(offset=1, modal=False)
                bevel_mod.profile = 0.6
                bevel_mod.loop_slide = True

                if (props := self._properties.get('machin3.hyper_bevel')) and (data := props.get('custom_profile')):
                    set_bevel_profile_from_dict(bevel_mod, dict(data))

                weld = add_weld(cutter, name="Weld", distance=0.000001, mode='CONNECTED')

        geometry['deltamx'] = geometry['mx'].inverted_safe() @ cutter.matrix_world

        set_obj_origin(cutter, geometry['mx'])

        cutter.HC['geometry'] = geometry

        return cutter

    def extrude_cutter(self, cutter, bm, verts, faces, geometry, edge_glayer, face_glayer):
        if self.boolean:
            ret = bmesh.ops.extrude_face_region(bm, geom=faces)

            top_faces = [el for el in ret['geom'] if isinstance(el, bmesh.types.BMFace)]
            top_verts = {v for f in top_faces for v in f.verts}

            for v in top_verts:
                normal = average_normals([f.normal for f in v.link_faces if f in top_faces])
                v.co = v.co + normal * self.width * 0.1 * (1 if geometry['convex'] else -1)

            top_center_edges = [e for f in top_faces for e in f.edges if e[edge_glayer] == 1]

            for e in top_center_edges:
                e[edge_glayer] = 0

            if not geometry['cyclic']:
                first_center_vert = verts[1]
                last_center_vert = verts[-2]

                first_cap_faces = [f for f in first_center_vert.link_faces if f not in faces]
                last_cap_faces = [f for f in last_center_vert.link_faces if f not in faces]

                geo = bmesh.ops.dissolve_faces(bm, faces=first_cap_faces + last_cap_faces)

                for f in geo['region']:
                    f[face_glayer] = 1

            if not geometry['convex']:
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

            hide_faces = {f for v in top_verts for f in v.link_faces}

            for f in hide_faces:
                f.hide_set(True)

    def full_cut(self, context, active, bm, sequences, debug=False):
        data = self.get_data(bm, sequences)

        if debug:
            self.debug_data(context, data, active.matrix_world)

        geo = self.get_geo_from_data(data, active.matrix_world)

        if debug:
            self.debug_geo(context, geo, active.matrix_world)

        for sidx, geometry in geo.items():
            cutter = self.create_cutter(context, active, geometry, edit=self.edit)

            if self.edit:
                if context.mode == 'EDIT_MESH':
                    bpy.ops.object.mode_set(mode='OBJECT')

                bpy.ops.object.select_all(action='DESELECT')

                context.view_layer.objects.active = cutter
                cutter.select_set(True)

                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')

                self.draw_cutter_creation = False
                self.draw_bevel_and_boolean = False

                return

            if self.boolean:
                boolean = self.add_boolean(context, active, cutter, convex=geometry['convex'])

                if self.mode == 'RAYCAST':

                    if self.init:
                        self.init = False

                        face_count = len(self.mesh.polygons)
                        bpy.data.meshes.remove(self.mesh, do_unlink=True)

                        dg = context.evaluated_depsgraph_get()
                        mesh = bpy.data.meshes.new_from_object(active.evaluated_get(dg), depsgraph=dg)

                        if len(mesh.polygons) < face_count / 10:
                            self.init = False
                            boolean.show_viewport = False

                            popup_message("Adjust the Operator Properties, or Undo the Operatrion.", title="Hyper Bevel failed!")

        active.show_wire = self.show_wire

        self.draw_cutter_creation = self.mode != 'CUTTER'
        self.draw_bevel_and_boolean = True

        self.draw_non_cyclic_options = not all([g['cyclic'] for g in geo.values()])

    def partial_cut(self, context):
        cutter = context.active_object
        parent = cutter.parent

        if cutter and parent:

            if cutter.hide_get():
                cutter.hide_set(False)

            booleans = [mod for mod in parent.modifiers if mod.type == 'BOOLEAN' and mod.object == cutter]

            if booleans:
                for mod in booleans:
                    print("removing previous mod:", mod)
                    parent.modifiers.remove(mod)

            bm = bmesh.from_edit_mesh(cutter.data)
            bm.normal_update()
            bm.verts.ensure_lookup_table()

            edge_glayer, face_glayer = ensure_gizmo_layers(bm)

            verts = [v for v in bm.verts]
            faces = [f for f in bm.faces]

            center_edges = [e for e in bm.edges if e[edge_glayer] == 1]
            center_vert_ids = list({v.index for e in center_edges for v in e.verts})

            geometry = {'center_edge_indices': [e.index for e in center_edges],
                        'cyclic': cutter.HC['geometry']['cyclic'],
                        'convex': cutter.HC['geometry']['convex']}
                            
            if geometry['center_edge_indices']:
                self.extrude_cutter(cutter, bm, verts, faces, geometry, edge_glayer, face_glayer)

                bmesh.update_edit_mesh(cutter.data)

                bpy.ops.object.mode_set(mode='OBJECT')

                if self.bevel:

                    vgroup = add_vgroup(cutter, 'Edge Bevel', ids=center_vert_ids, weight=1)

                    bevel_mod = add_bevel(cutter, name="Edge Bevel", width=0, limit_method='VGROUP', vertex_group=vgroup.name)
                    bevel_mod.offset_type = 'PERCENT'
                    bevel_mod.width_pct = 100
                    bevel_mod.segments = self.get_bevel_segments(offset=1, modal=False)
                    bevel_mod.profile = 0.6
                    bevel_mod.loop_slide = True

                    weld = add_weld(cutter, name="Weld", distance=0.000001, mode='CONNECTED')

                if self.boolean:
                    boolean = self.add_boolean(context, parent, cutter, convex=geometry['convex'])

                context.view_layer.objects.active = parent

                return cutter.parent

    def add_boolean(self, context, active, cutter, convex=True):
        if self.weld:
            weld = self.add_weld(active)
            weld.show_in_editmode = self.mode == 'SELECTION'

        boolean = active.modifiers.new(name="Hyper Bevel", type='BOOLEAN')
        boolean.object = cutter
        boolean.solver = 'EXACT'
        boolean.operation = 'DIFFERENCE' if convex else 'UNION'
        boolean.show_expanded = False
        boolean.show_in_editmode = self.mode == 'SELECTION'
        boolean.use_self = self.boolean_self

        names = [mo.name for mo in active.modifiers if mo != boolean and mo.type == 'BOOLEAN' and 'Hyper Bevel' in mo.name]

        if names:
            maxidx = get_biggest_index_among_names(names)
            boolean.name = f"Hyper Bevel.{str(maxidx + 1).zfill(3)}"

        if self.bevel:
            cutter.hide_set(True)

        return boolean

    def add_weld(self, obj):
        mod = add_weld(obj, distance=0.0001, mode='ALL')

        names = [mo.name for mo in obj.modifiers if mo != mod and mo.type == 'WELD' and 'Weld' in mo.name]

        if names:
            maxidx = get_biggest_index_among_names(names)
            mod.name = f"- Weld.{str(maxidx + 1).zfill(3)}"
        else:
            mod.name = "- Weld"

        return mod

def draw_pick_bevel(op):
    global machin3tools

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text='Pick Hyper Bevel')

        if not op.highlighted:
            row.label(text="", icon='MOUSE_LMB')
            row.label(text="Finish")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        if op.highlighted:
            row.label(text="", icon='RESTRICT_SELECT_OFF')
            row.label(text=op.highlighted.name)

            row.separator(factor=2)

            mod = op.active.modifiers.get(op.highlighted.name)

            row.label(text="", icon='EVENT_S')
            row.label(text="Hide" if op.highlighted.obj.visible_get() else "Select")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_D')
            row.label(text=f"Disabled: {not mod.show_viewport}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_X')
            row.label(text=f"Delete: {op.highlighted.remove}")

            row.separator(factor=2)

            if mod.show_viewport:
                segments = edge_bevel.segments - 1 if (obj := op.highlighted.obj) and (edge_bevel := obj.modifiers.get('Edge Bevel')) else None

                row.label(text="", icon='MOUSE_LMB')
                row.label(text="Edit")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_E')
                row.label(text="Extend")

                row.separator(factor=2)

                if segments is not None:
                    row.label(text="", icon='MOUSE_MMB')
                    row.label(text=f"Segments: {segments}")

                if machin3tools:
                    row.separator(factor=2)

                    row.label(text="", icon='EVENT_M')
                    row.label(text="Initialize Mirror")

    return draw

class PickHyperBevel(bpy.types.Operator):
    bl_idname = "machin3.pick_hyper_bevel"
    bl_label = "MACHIN3: Pick Hyper Bevel"
    bl_description = "Pick Hyper Bevel"
    bl_options = {'REGISTER', 'UNDO'}

    mirror = False

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active

    def draw_HUD(self, context):
        if context.area == self.area:
            if context.window_manager.HC_pickhyperbevelshowHUD:

                draw_init(self)

                is_active = bool(self.highlighted and (name := self.highlighted.name) and (mod := self.active.modifiers.get(name, None)) and mod.show_viewport)
                dims = draw_label(context, title='Edit ' if self.highlighted else 'Pick ', coords=Vector((self.HUD_x, self.HUD_y)), color=white, center=False, alpha=1 if is_active else 0.25)

                if self.highlighted:
                    is_remove = self.highlighted.remove

                    cutter = self.highlighted.obj
                    edge_bevel = cutter.modifiers.get('Edge Bevel', None) if cutter else None

                    color, alpha = (green, 1) if is_active else (white, 0.5)
                    dims2 = draw_label(context, title=f"🔧 {name} ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, color=color, center=False, alpha=alpha)

                    if is_remove:
                        draw_label(context, title="to be removed", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, size=10, color=red, center=False, alpha=1)

                    elif not is_active:
                        draw_label(context, title="disabled", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, size=10, color=white, center=False, alpha=0.25)

                else:
                     draw_label(context, title='Hyper Bevel', coords=Vector((self.HUD_x + dims[0], self.HUD_y)), color=white, center=False, alpha=0.25)

                self.offset += 18

                if self.highlighted:

                    if cutter:
                        dims = draw_label(context, title='Object: ', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, size=10, color=white, center=False, alpha=0.5)

                        color = red if is_remove else yellow if is_active else white
                        draw_label(context, title=f'{cutter.name}', coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, size=10, color=color, center=False, alpha=1)

                        if edge_bevel and is_active and not is_remove:
                            self.offset += 24

                            dims = draw_label(context, title='Segments: ', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, color=white, center=False, alpha=0.5)
                            draw_label(context, title=f'{edge_bevel.segments - 1}', coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, color=white, center=False, alpha=1)
                        
                else:
                    draw_label(context, title="None", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, size=10, color=red, center=False, alpha=1)

    def modal(self, context, event):
        if ignore_events(event):
            return {'PASS_THROUGH'}

        context.area.tag_redraw()

        if self.active.show_wire and (time() - self.wire_time) > 1:
            self.active.show_wire = False

        events = ['E', 'S', 'H', 'D', 'X', 'M']

        if event.type == 'MOUSEMOVE':
            get_mouse_pos(self, context, event, window=True)

            self.is_in_3d_view = self.is_mouse_in_3d_view()

        self.highlighted = self.get_highlighted_hyper_bevel(context)

        if self.highlighted:

            if event.type in events and event.value == 'PRESS' or scroll_up(event, key=True) or scroll_down(event, key=True):
                active = bpy.data.objects.get(self.activename)

                mod = active.modifiers.get(self.highlighted.name)

                cutter = self.highlighted.obj
                edge_bevel = cutter.modifiers.get('Edge Bevel')

                if event.type in ['S', 'H']:

                    if cutter:
                        view = context.space_data

                        if view.local_view and not cutter.local_view_get(view):
                            cutter.local_view_set(view, True)

                        if cutter.visible_get():
                            cutter.hide_set(True)

                            bpy.ops.object.select_all(action='DESELECT')

                            active.select_set(True)
                            context.view_layer.objects.active = active

                        else:
                            bpy.ops.object.select_all(action='DESELECT')

                            cutter.hide_set(False)
                            cutter.select_set(True)
                            context.view_layer.objects.active = cutter

                elif event.type == 'D':
                    mod.show_viewport = not mod.show_viewport
                    self.highlighted.active = mod.show_viewport

                    if mod.show_viewport and self.highlighted.remove:
                        self.highlighted.remove = False

                elif event.type == 'X':
                    self.highlighted.remove = not self.highlighted.remove

                    mod.show_viewport = not self.highlighted.remove

                    if mod.show_viewport and not self.highlighted.active:
                        self.highlighted.active = True

                if mod.show_viewport:

                    if edge_bevel and (scroll_up(event, key=True) or scroll_down(event, key=True)):
                        if scroll_up(event, key=True):
                            edge_bevel.segments += 1

                        else:
                            edge_bevel.segments -= 1

                        self.active.show_wire = True
                        self.wire_time = time()

                    if event.type == 'E':
                        bpy.ops.machin3.extend_hyper_bevel('INVOKE_DEFAULT', objname=cutter.name, modname=mod.name, is_hypermod_invoke=False)

                    elif event.type == 'M':
                        global machin3tools

                        if machin3tools:

                            if view.local_view and not cutter.local_view_get(view):
                                cutter.local_view_set(view, True)

                            m3prefs = get_addon_prefs('MACHIN3tools')

                            if not m3prefs.activate_mirror:
                                m3prefs.activate_mirror = True

                            bpy.ops.object.select_all(action='DESELECT')
                            context.view_layer.objects.active = active
                            active.select_set(True)

                            active.HC['hidename'] = cutter.name

                            bpy.ops.machin3.macro_mirror_hide('INVOKE_DEFAULT')

        finish_events = ['SPACE']

        if self.is_in_3d_view and not self.highlighted:
            finish_events.append('LEFTMOUSE')

        if self.highlighted:
            finish_events.append('TAB')

        if event.type in finish_events and event.value == 'PRESS':

            for b in self.bevelsCOL:
                if b.remove:
                    mod = self.active.modifiers.get(b.name, None)

                    if mod:
                        if weld := self.get_preceeding_weld_mod(self.active, mod):
                            remove_mod(weld)

                        remove_mod(mod)

                        if b.obj:
                            remove_obj(b.obj)

            self.finish(context)

            if event.type == 'TAB':
                bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')

            return {'FINISHED'}

        elif event.type in ['ESC', 'RIGHTMOUSE'] and event.value == 'PRESS':
            self.finish(context)

            for name, data in self.initial.items():
                if name == 'MODIFIERS':

                    for idx, modname in enumerate(data):

                        if not self.active.modifiers.get(modname, None):

                            weld = add_weld(self.active)
                            weld.name = modname

                            move_mod(weld, idx)

                    remove = []

                    for mod in self.active.modifiers:
                        if mod.name not in data and 'Weld':
                            remove.append(mod)

                    for mod in remove:
                        remove_mod(mod)

                else:
                    mod = self.active.modifiers.get(name, None)
                    mod.show_viewport = data['show_viewport']

                    if mod and (obj := mod.object):
                        edge_bevel = obj.modifiers.get('Edge Bevel', None)

                        if edge_bevel:
                            edge_bevel.segments = data['segments']
                            edge_bevel.profile = data['profile']

                        bm = data['bmesh']

                        bm.to_mesh(obj.data)
                        bm.free()

                        if obj.visible_get() and data['hidden']:
                            obj.hide_set(True)

                        elif not obj.visible_get() and not data['hidden']:
                            obj.hide_set(False)

            return {'CANCELLED'}

        if event.type in ['MOUSEMOVE', 'T'] or navigation_passthrough(event, alt=True, wheel=not self.highlighted) or (self.highlighted and event.type == 'LEFTMOUSE' and event.value == 'PRESS'):
            return {'PASS_THROUGH'}

        elif self.is_in_3d_view and event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            return {'PASS_THROUGH'}

        elif not self.is_in_3d_view and event.type in ['LEFTMOUSE', *numbers[:10]]:
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        wm = context.window_manager
        wm.gizmo_group_type_unlink_delayed('MACHIN3_GGT_pick_hyper_bevel')

        self.bevelsCOL.clear()

        finish_status(self)

        restore_gizmos(self)

        force_ui_update(context)

    def invoke(self, context, event):
        global machin3tools

        if machin3tools is None:
            machin3tools = get_addon('MACHIN3tools')[0]

        self.active = context.active_object

        self.activename = self.active.name 

        hyperbevels = self.get_hyper_bevels()

        if hyperbevels:

            self.get_init_states(hyperbevels)

            wm = context.window_manager
            self.bevelsCOL = wm.HC_pickhyperbevelsCOL
            self.bevelsCOL.clear()

            for idx, (modobj, mod) in enumerate(hyperbevels.items()):
                bevel = self.bevelsCOL.add()
                bevel.name = mod.name
                bevel.obj = modobj
                bevel.active = mod.show_viewport
                bevel.area_pointer = str(context.area.as_pointer())

            wm.HC_pickhyperbevelshowHUD = True

            self.highlighted = None
            self.last_highlighted = None
            self.wire_time = 0

            wm.gizmo_group_type_ensure('MACHIN3_GGT_pick_hyper_bevel')

            hide_gizmos(self, context)

            get_mouse_pos(self, context, event, window=True)

            self.area = context.area
            self.is_in_3d_view = self.is_mouse_in_3d_view()

            init_status(self, context, func=draw_pick_bevel(self))

            force_ui_update(context)

            self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:
            draw_fading_label(context, text="No valid HyperBevels found!", y=120, color=red, alpha=1, move_y=40, time=4)
            return {'CANCELLED'}

    def get_hyper_bevels(self):
        hyperbevels = {mod.object: mod for mod in self.active.modifiers if mod.type == 'BOOLEAN' and 'Hyper Bevel' in mod.name and mod.object}

        invalid = []

        for cutter, mod in hyperbevels.items():

            edge_bevel = cutter.modifiers.get('Edge Bevel')

            if edge_bevel:
                bm = bmesh.new()
                bm.from_mesh(cutter.data)

                edge_glayer = bm.edges.layers.int.get('HyperEdgeGizmo')
                
                if edge_glayer:
                    continue

            invalid.append(mod.object)

        for cutter in invalid:
            del hyperbevels[cutter]

        return hyperbevels

    def get_init_states(self, hyperbevels):
        self.initial = {'MODIFIERS': [mod.name for mod in self.active.modifiers]}

        for obj, mod in hyperbevels.items():
            edge_bevel = obj.modifiers.get('Edge Bevel')

            bm = bmesh.new()
            bm.from_mesh(obj.data)

            self.initial[mod.name] = {'show_viewport': mod.show_viewport,
                                      'hidden': not obj.visible_get(), 
                                      'segments': edge_bevel.segments,
                                      'profile': edge_bevel.profile,
                                      'bmesh': bm}

    def get_highlighted_hyper_bevel(self, context):
        for b in self.bevelsCOL:
            if b.is_highlight:
                if b != self.last_highlighted:

                    mod = self.active.modifiers.get(b.name)
                    mod.is_active = True

                    force_ui_update(context)
                    self.last_highlighted = b

                return b

        if self.last_highlighted:
            self.last_highlighted = None
            force_ui_update(context)

    def get_preceeding_weld_mod(self, obj, bevel_mod):
        all_mods = [mod for mod in obj.modifiers]
        bevel_index = all_mods.index(bevel_mod)

        if bevel_index >= 1:
            prev_mod = all_mods[bevel_index - 1]
            
            if prev_mod.type == 'WELD' and (prev_mod.name.startswith('- ') or bevel_mod.name.startswith('+ ')):
                return prev_mod

    def is_mouse_in_3d_view(self):
        area_coords = {'x': (self.area.x, self.area.x + self.area.width),
                       'y': (self.area.y, self.area.y + self.area.height)}
        
        if area_coords['x'][0] < self.mouse_pos_window.x < area_coords['x'][1]:
            return area_coords['y'][0] < self.mouse_pos_window.y < area_coords['y'][1]
        return False

def draw_edit_hyper_bevel_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text='Edit Hyper Bevel')

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

        if op.is_valid:
            row.label(text="", icon='EVENT_ALT')
            row.label(text=f"Weld: {bool(op.weld)}")

            row.separator(factor=2)

            row.label(text="", icon='MOUSE_LMB_DRAG')
            row.label(text=f"Adjust Width: {dynamic_format(op.amount, decimal_offset=2)}")

            row.separator(factor=1)

            row.label(text="", icon='EVENT_R')
            row.label(text=f"Relative: {op.relative}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_E')
            solver = 'Exact'

            if op.boolean_mod.use_self:
                solver += " + Self Intersection"

            if op.boolean_mod.use_hole_tolerant:
                solver += " + Hole Tolerant"

            row.label(text=f"Solver: {solver}")

            if not op.is_chamfer:
                row.separator(factor=2)

                row.label(text="", icon='MOUSE_MMB')
                row.label(text=f"Segments: {op.segments}")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_C')
            row.label(text=f"Chamfer: {op.is_chamfer}")

            if op.has_custom_profile:
                row.separator(factor=2)
                row.label(text="", icon='EVENT_B')
                row.label(text=f"Profile: {op.bevel_mod.profile_type.title()}")

                if op.is_custom_profile:
                    row.separator(factor=1)
                    row.label(text="", icon='EVENT_F')
                    row.label(text=f"Flip Profile")

                    row.separator(factor=1)
                    row.label(text="", icon='EVENT_V')
                    row.label(text=f"Flop Profile")

            if not op.is_chamfer and not op.is_custom_profile:
                row.separator(factor=2)

                row.label(text="", icon='EVENT_T')
                row.label(text=f"Tension: {dynamic_format(op.bevel_mod.profile, decimal_offset=1)}")

        else:
            row.label(text=f"Hyper Bevel will be removed when finishing the Operator!", icon='ERROR')

    return draw

class EditHyperBevel(bpy.types.Operator, Settings):
    bl_idname = "machin3.edit_hyper_bevel"
    bl_label = "MACHIN3: Edit Hyper Bevel"
    bl_description = "Edit Hyper Bevel"
    bl_options = {'REGISTER', 'UNDO'}

    modname: StringProperty()
    objname: StringProperty()  # objname here is the name of the host object carrying the hyper bevel (boolean) mod

    amount: FloatProperty(name="Amount", default=0)
    segments: IntProperty(name="Segments", default=6, min=0)
    profile_segments: IntProperty(name="Bevel Profile Segments", default=0, min=0)
    is_chamfer: BoolProperty(name="Chamfer", default=False)
    relative: BoolProperty(name="Relative", default=True)
    is_profile_drop: BoolProperty(name="is Profile Drop", default=False)
    has_custom_profile: BoolProperty(name="has Custom Profile", default=False)
    is_hypermod_invoke: BoolProperty()

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return True

    def draw_HUD(self, context):
        if context.area == self.area:
        
            draw_init(self)

            dims = draw_label(context, title=f'Edit ', coords=Vector((self.HUD_x, self.HUD_y)), color=green, center=False, alpha=1)
            dims2 = draw_label(context, title=f'{self.boolean_mod.name} ', coords=Vector((self.HUD_x + dims[0], self.HUD_y)), color=white, center=False, alpha=1)

            if self.is_shift:
                draw_label(context, title='a little', coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), color=white, center=False, size=10, alpha=0.5)

            elif self.is_ctrl:
                draw_label(context, title='a lot', coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), color=white, center=False, size=10, alpha=0.5)

            if self.is_valid:

                self.offset += 18
                color, alpha = (white, 0.5) if self.is_tension else (yellow, 1)
                dims = draw_label(context, title=f'Amount: {dynamic_format(self.amount, decimal_offset=2)} ', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, color=color, center=False, alpha=alpha)

                if self.relative:
                    color, alpha = (white, 0.2) if self.is_tension else (blue, 1)
                    draw_label(context, title='Relative', coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, color=color, center=False, alpha=alpha)

                if not self.is_custom_profile and not self.is_chamfer:
                    self.offset += 18
                    color, alpha = (yellow, 1) if self.is_tension else (white, 0.5)
                    draw_label(context, title=f'Tension: {dynamic_format(self.bevel_mod.profile, decimal_offset=1)}', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, color=color, center=False, alpha=alpha)

                self.offset += 18
                if self.is_chamfer:
                    dims = draw_label(context, title="Chamfer ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, color=blue, center=False, alpha=1)

                    if self.has_custom_profile:
                        draw_label(context, title="🌠", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=blue, alpha=1)

                else:
                    alpha = 0.3 if (self.is_custom_profile or self.segments == 0) else 1
                    segments = self.profile_segments if self.is_custom_profile else self.segments

                    dims = draw_label(context, title=f"Segments: {segments} ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, color=white, center=False, alpha=alpha)

                    if self.has_custom_profile:
                        text = "Custom Profile" if self.is_custom_profile else "🌠"
                        draw_label(context, title=text, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=blue, alpha=1)

                if self.weld:
                    self.offset += 18
                    draw_label(context, title='Weld', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, color=yellow, center=False, alpha=1)

                mod = self.boolean_mod

                if mod.use_self or mod.use_hole_tolerant:
                    self.offset += 18

                    title = "Self Intersection" if mod.use_self else "Hole Tolerant"
                    draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, color=yellow, center=False, alpha=1)

                    if mod.use_self and mod.use_hole_tolerant:
                        title = "  + Hole Tolerant"
                        self.offset += 18
                        draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, color=yellow, center=False, alpha=1)

                if not self.is_chamfer and self.is_custom_profile and self.profile_HUD_coords:
                    draw_line(self.profile_HUD_coords, width=2, color=blue, alpha=0.75)
                    draw_line(self.profile_HUD_border_coords, width=1, color=white, alpha=0.1)

                    for dir, origin in self.profile_HUD_edge_dir_coords:
                        draw_vector(dir, origin=origin, color=blue, fade=True)

            else:
                self.offset += 18
                draw_label(context, title='Auto Remove', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, color=red, center=False, alpha=1)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        self.is_custom_profile = self.has_custom_profile and self.bevel_mod.profile_type == 'CUSTOM'

        if not self.is_custom_profile and not self.is_chamfer and event.type == 'T':
            if event.value == 'PRESS':
                self.is_tension = True
                context.window.cursor_set('SCROLL_Y')

            elif event.value == 'RELEASE':
                self.is_tension = False
                context.window.cursor_set('SCROLL_X')

        events = ['MOUSEMOVE', 'C', 'R', 'X', 'Y', 'Z', 'E', *shift, *ctrl, *alt]

        if self.has_custom_profile:
            events.append('B')

        if self.is_custom_profile:
            events.extend(['F', 'V'])
        
        if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):

            if event.type == 'MOUSEMOVE':
                get_mouse_pos(self, context, event)

                if self.is_custom_profile:
                    self.get_profile_HUD_coords(context)

                if self.is_tension:
                    wrap_mouse(self, context, y=True)

                    divisor = get_mousemove_divisor(event, 3, 15, 1, sensitivity=50)

                    delta_y = self.mouse_pos.y - self.last_mouse.y
                    delta_tension = delta_y / divisor
                    self.bevel_mod.profile += delta_tension

                else:
                    wrap_mouse(self, context, x=True)

                    divisor = get_mousemove_divisor(event, 3, 15, 1)

                    delta_x = self.mouse_pos.x - self.last_mouse.x
                    delta_amount = delta_x / divisor * self.factor
                    self.amount += delta_amount

                    self.adjust_hyper_bevel_width(self.amount)

                force_ui_update(context)

            elif not self.is_chamfer and not self.is_custom_profile and (scroll_up(event, key=True) or scroll_down(event, key=True)):
                if scroll_up(event, key=True):
                    self.segments += 1

                elif scroll_down(event, key=True):
                    self.segments -= 1

                self.bevel_mod.segments = self.segments + 1

            elif event.type == 'C' and event.value == 'PRESS':
                self.is_chamfer = not self.is_chamfer
                self.bevel_mod.segments = 1 if self.is_chamfer else self.profile_segments + 1 if self.is_custom_profile else self.segments + 1

            elif event.type == 'B' and event.value == 'PRESS':
                if self.is_custom_profile:

                    if self.is_chamfer:
                        self.is_chamfer = False
                        self.bevel_mod.segments = self.profile_segments + 1
                        return {'RUNNING_MODAL'}

                    else:

                        self.bevel_mod.profile_type = 'SUPERELLIPSE'
                        self.bevel_mod.segments = self.segments + 1

                else:

                    if self.is_chamfer:
                        self.is_chamfer = False

                    self.bevel_mod.profile_type = 'CUSTOM'
                    self.bevel_mod.segments = self.profile_segments + 1

                    self.get_profile_HUD_coords(context)

            elif event.type == 'F' and event.value == 'PRESS':
                flip_bevel_profile(self.bevel_mod)

                self.get_profile_HUD_coords(context)

            elif event.type == 'V' and event.value == 'PRESS':
                flop_bevel_profile(self.bevel_mod)

                self.get_profile_HUD_coords(context)

            elif event.type == 'E' and event.value == 'PRESS':
                mod = self.boolean_mod
                modes = ['EXACT', 'EXACT_SELF', 'EXACT_HOLES', 'EXACT_SELF_HOLES']

                if mod.use_self and mod.use_hole_tolerant:
                    mode = 'EXACT_SELF_HOLES'

                elif mod.use_self:
                    mode = 'EXACT_SELF'

                elif mod.use_hole_tolerant:
                    mode = 'EXACT_HOLES'

                else:
                    mode = 'EXACT'

                if event.shift:
                    next_mode = step_list(mode, modes, step=-1, loop=True)

                else:
                    next_mode = step_list(mode, modes, step=1, loop=True)

                if next_mode == 'EXACT':
                    mod.solver = 'EXACT'
                    mod.use_self = False
                    mod.use_hole_tolerant = False

                elif next_mode == 'EXACT_SELF':
                    mod.solver = 'EXACT'
                    mod.use_self = True
                    mod.use_hole_tolerant = False

                elif next_mode == 'EXACT_HOLES':
                    mod.solver = 'EXACT'
                    mod.use_self = False
                    mod.use_hole_tolerant = True

                elif next_mode == 'EXACT_SELF_HOLES':
                    mod.solver = 'EXACT'
                    mod.use_self = True
                    mod.use_hole_tolerant = True

            elif event.type == 'R' and event.value == 'PRESS':
                self.relative = not self.relative

                self.adjust_hyper_bevel_width(self.amount)

            elif event.type in ['Y', 'Z'] and event.value == 'PRESS':
                self.bevel_mod.profile = 0.5

            elif event.type == 'X' and event.value == 'PRESS':
                self.bevel_mod.profile = 0.6

            elif event.type in alt and event.value == 'PRESS':

                if self.weld:
                    remove_mod(self.weld)
                    self.weld = None

                else:
                    self.weld = self.add_weld_before_hyper_bevel(self.active, self.boolean_mod)

        if event.type in ['LEFTMOUSE', 'SPACE']:
            self.finish(context)

            if not self.is_valid:

                for bevel in context.window_manager.HC_pickhyperbevelsCOL:
                    if bevel.name == self.modname and bevel.obj == self.cutter:
                        bevel.remove = True

            if self.is_profile_drop and self.cutter.HC.get('init_custom_profile', None):
                del self.cutter.HC['init_custom_profile']

            if self.is_custom_profile:
                profile = get_bevel_profile_as_dict(self.bevel_mod)
                self._properties['machin3.hyper_bevel'] = {'custom_profile': profile}

            if self.is_hypermod_invoke:
                bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')

            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:
            self.finish(context)

            self.initbm.to_mesh(self.cutter.data)
            self.initbm.free()

            if not self.boolean_mod.show_viewport:
                self.boolean_mod.show_viewport = True

            if self.is_profile_drop and (data := self.cutter.HC.get('init_custom_profile', None)):
                set_bevel_profile_from_dict(self.bevel_mod, dict(data))

                del self.cutter.HC['init_custom_profile']
            
            else:
                for prop, value in self.initial.items():
                    if prop in ['segments', 'profile', 'profile_type']:
                        mod = self.bevel_mod

                    elif prop in ['solver', 'use_self', 'use_hole_tolerant']:
                        mod = self.boolean_mod

                    elif prop == 'weld':
                        weld = self.get_weld_mod(self.active, self.boolean_mod)

                        if value and not weld:
                            self.add_weld_before_hyper_bevel(self.active, self.boolean_mod)

                        elif not value and weld:
                            remove_mod(weld)

                        continue

                    setattr(mod, prop, value)

            if self.is_hypermod_invoke:
                bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')

            return {'CANCELLED'}

        self.last_mouse = self.mouse_pos

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

        self.active.show_wire = False

        context.window.cursor_set('DEFAULT')

        context.window_manager.HC_pickhyperbevelshowHUD = True

    def invoke(self, context, event):
        self.active = bpy.data.objects[self.objname]
        self.boolean_mod = self.active.modifiers.get(self.modname, None)

        if self.boolean_mod:
            if self.boolean_mod.show_viewport:

                self.active.modifiers.active = self.boolean_mod

                self.cutter = self.boolean_mod.object

                if self.cutter:
                    self.bevel_mod = self.cutter.modifiers.get('Edge Bevel', None)

                    if self.bevel_mod:
                        self.mx = self.cutter.matrix_world
                        loc, _, _ = self.mx.decompose()

                        self.initbm = bmesh.new()
                        self.initbm.from_mesh(self.cutter.data)
                        self.initbm.normal_update()
                        self.initbm.verts.ensure_lookup_table()

                        edge_glayer = self.initbm.edges.layers.int.get('HyperEdgeGizmo')

                        if edge_glayer:
                            center_edges = []

                            for e in self.initbm.edges:
                                if e[edge_glayer] == 1:
                                    center_edges.append(e)

                            if center_edges:
                                self.data = self.get_hyper_bevel_side_data(center_edges, debug=False)

                                if self.data:

                                    self.amount = 0
                                    self.is_chamfer = self.bevel_mod.profile_type == 'CUSTOM' and self.bevel_mod.segments == 1
                                    self.segments = self.bevel_mod.segments - 1

                                    self.is_shift = False
                                    self.is_ctrl = False
                                    self.is_tension = False

                                    self.is_valid = True
                                    self.weld = self.get_weld_mod(self.active, self.boolean_mod)

                                    self.has_custom_profile = len(self.bevel_mod.custom_profile.points) > 2
                                    self.is_custom_profile = self.has_custom_profile and self.bevel_mod.profile_type == 'CUSTOM'
                                    
                                    self.profile_segments = len(self.bevel_mod.custom_profile.points) - 2

                                    self.initial = {'segments': self.bevel_mod.segments,
                                                    'profile': self.bevel_mod.profile,
                                                    'profile_type': self.bevel_mod.profile_type,

                                                    'solver': self.boolean_mod.solver,
                                                    'use_self': self.boolean_mod.use_self,
                                                    'use_hole_tolerant': self.boolean_mod.use_hole_tolerant,

                                                    'weld': bool(self.weld)}

                                    self.factor = get_zoom_factor(context, loc, scale=10, debug=False)

                                    self.active.show_wire = True

                                    get_mouse_pos(self, context, event)

                                    self.last_mouse = self.mouse_pos

                                    self.get_profile_HUD_coords(context)

                                    context.window.cursor_set('SCROLL_X')

                                    context.window_manager.HC_pickhyperbevelshowHUD = False

                                    init_status(self, context, func=draw_edit_hyper_bevel_status(self))

                                    self.area = context.area
                                    self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')

                                    context.window_manager.modal_handler_add(self)
                                    return {'RUNNING_MODAL'}

                                else:
                                    print("unsupported hyper bevel geometry")
                            else:
                                print("no center edges found, not valid hyper bevel object")
                        else:
                            print("no edge glayer found, not a valid hyper bevel object")

            else:
                draw_fading_label(context, text="You can't edit a disabled Hyper Bevel", color=red, time=2)

        return {'CANCELLED'}

    def get_hyper_bevel_side_data(self, center_edges, debug=False):
        
        data = {}

        center_verts = list(set(v for e in center_edges for v in e.verts))

        if debug:
            print("center edges:", [e.index for e in center_edges])
            print("center verts:", [v.index for v in center_verts])

        sequences = get_edges_vert_sequences(center_verts, center_edges, debug=False)

        if len(sequences) == 1:
            sorted_center_verts, cyclic = sequences[0]

            for idx, v in enumerate(sorted_center_verts):

                side_edges = [e for e in v.link_edges if e not in center_edges]

                if len(side_edges) == 2:
                    side_verts = [e.other_vert(v) for e in side_edges]
                    
                    for side_vert in side_verts:
                        dir = side_vert.co - v.co

                        data[side_vert.index] = {'co': side_vert.co.copy(),
                                                 'dir': dir.normalized(),

                                                 'length': dir.length,
                                                 'factor': None,

                                                 'type': 'BOTTOM',
                                                 'center': v.index}
                    
                    top_center_vert = None

                    for e in side_edges:

                        loop = [l for l in e.link_loops if l.vert == v][0]

                        if len(loop.face.verts) == 4:
                            top_side_loop = loop.link_loop_next.link_loop_radial_next.link_loop_next.link_loop_next.link_loop_radial_next.link_loop_next

                            top_side_edge = top_side_loop.edge
                            top_side_vert = top_side_loop.vert

                        else:
                            top_side_loop = loop.link_loop_next.link_loop_next

                            top_side_edge = top_side_loop.edge
                            top_side_vert = top_side_loop.vert
                        
                        if not top_center_vert:
                            top_center_vert = top_side_edge.other_vert(top_side_vert)

                        bottom_side_vert = loop.link_loop_next.vert

                        data[top_side_vert.index] = {'co': top_side_vert.co.copy(),
                                                     'dir': (top_side_vert.co - top_center_vert.co).normalized(),

                                                     'bottom_index': bottom_side_vert.index,
                                                     'factor': None,

                                                     'type': 'TOP',
                                                     'center': top_center_vert.index}

                else:
                    return

            max_length = max([vdata['length'] for vdata in data.values() if vdata['type'] == 'BOTTOM'])

            for vdata in data.values():
                if vdata['type'] == 'BOTTOM':
                    vdata['factor'] = vdata['length'] / max_length

            for vdata in data.values():
                if vdata['type'] == 'TOP':
                    bidx = vdata['bottom_index']
                    vdata['factor'] = data[bidx]['factor']

        else:
            return

        if debug:
            printd(data)

            for vdata in data.values():
                co = vdata['co']
                vec = vdata['dir'] * 0.2
                color = green if vdata['type'] == 'BOTTOM' else yellow

        return data

    def get_weld_mod(self, obj, bevel_mod):
        all_mods = [mod for mod in obj.modifiers]
        bevel_index = all_mods.index(bevel_mod)

        if bevel_index >= 1:
            prev_mod = all_mods[bevel_index - 1]
            
            if prev_mod.type == 'WELD' and prev_mod.name.startswith('- '):
                return prev_mod

    def add_weld_before_hyper_bevel(self, obj, hyper_bevel):
        mod = add_weld(obj, distance=0.0001, mode='ALL')

        names = [mo.name for mo in obj.modifiers if mo != mod and mo.type == 'WELD' and 'Weld' in mo.name]

        if names:
            maxidx = get_biggest_index_among_names(names)
            mod.name = f"- Weld.{str(maxidx + 1).zfill(3)}"
        else:
            mod.name = "- Weld"

        modidx = list(obj.modifiers).index(mod)
        bevelidx = list(obj.modifiers).index(hyper_bevel)

        obj.modifiers.move(modidx, bevelidx)
        return mod

    def get_profile_HUD_coords(self, context):
        self.profile_HUD_coords = []
        self.profile_HUD_border_coords = []
        self.profile_HUD_edge_dir_coords = []

        if self.has_custom_profile:
            profile = self.bevel_mod.custom_profile
            points = profile.points

            scale = get_scale(context)
            size = 100

            offset_x = get_text_dimensions(context, text=f"Segments: {len(points) - 2} Custom Profile ")[0]
            offset_y = -(6 * scale) - size

            offset = Vector((offset_x, offset_y))

            for p in points:
                co = Vector((self.HUD_x, self.HUD_y)) + offset + p.location * size
                self.profile_HUD_coords.append(co.resized(3))

            for corner in [(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)]:
                co = Vector((self.HUD_x, self.HUD_y)) + offset + Vector(corner)
                self.profile_HUD_border_coords.append(co.resized(3))

            self.profile_HUD_edge_dir_coords.append((Vector((-size * 0.7, 0, 0)), Vector((self.HUD_x, self.HUD_y, 0)) + offset.resized(3) + Vector((0, size, 0))))
            self.profile_HUD_edge_dir_coords.append((Vector((0, -size * 0.7, 0)), Vector((self.HUD_x, self.HUD_y, 0)) + offset.resized(3) + Vector((size, 0, 0))))

    def adjust_hyper_bevel_width(self, amount):

        bm = self.initbm.copy()
        bm.verts.ensure_lookup_table()

        self.is_valid = True

        new_coords = {}

        for vidx, vdata in self.data.items():
            v = bm.verts[vidx]

            factor = vdata['factor'] if self.relative else 1
            new_co = vdata['co'] + vdata['dir'] * factor * self.amount

            new_coords[v] = new_co

            center = bm.verts[vdata['center']]
            new_dir = (new_co - center.co).normalized()
            dot = new_dir.dot(vdata['dir'])

            if dot <= 0:
                self.is_valid = False

        if self.is_valid:
            for v, co in new_coords.items():
                v.co = co

            if not self.boolean_mod.show_viewport:
                self.boolean_mod.show_viewport = True

        else:

            if self.boolean_mod.show_viewport:
                self.boolean_mod.show_viewport = False

        bm.to_mesh(self.cutter.data)
        bm.free()

def draw_extend_hyper_bevel_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text='Extend Hyper Bevel')

        if op.is_hypermod_invoke:
            row.label(text="", icon='MOUSE_LMB')
            row.label(text="Finish")

        else:
            row.label(text="", icon='EVENT_E')
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
        row.label(text=f"Both Ends: {op.is_shift}")

    return draw

class ExtendHyperBevel(bpy.types.Operator):
    bl_idname = "machin3.extend_hyper_bevel"
    bl_label = "MACHIN3: Extend Hyper Bevel"
    bl_description = "Extend Hyper Bevel"
    bl_options = {'REGISTER', 'UNDO'}

    objname: StringProperty()  # the objname here is the hyper bevel cutter obj
    modname: StringProperty()  # only used for the HUD

    amount: FloatProperty(name="Extend Amount")

    is_hypermod_invoke: BoolProperty()

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return True

    def draw_HUD(self, context):
        if context.area == self.area:
        
            draw_init(self)

            dims = draw_label(context, title=f'Extend ', coords=Vector((self.HUD_x, self.HUD_y)), color=green, center=False, alpha=1)
            dims2 = draw_label(context, title=f'{self.modname} ', coords=Vector((self.HUD_x + dims[0], self.HUD_y)), color=white, center=False, alpha=1)

            if self.is_shift:
                draw_label(context, title='both ends', coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), color=white, center=False, size=10, alpha=0.5)

            if not self.is_valid:
                self.offset += 18
                dims = draw_label(context, title='Invalid ', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, color=red, center=False, size=12, alpha=1)
                draw_label(context, title=f"You can't move beyond {'these points' if self.is_shift else 'this point'}", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, color=white, center=False, size=10, alpha=0.5)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            if self.coords:
                draw_line(self.coords, color=yellow, width=2)

            if self.limit_coords:
                color, alpha = (white, 0.5) if self.is_valid else (red, 1)
                draw_points(self.limit_coords, size=4, color=color, alpha=alpha)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        self.is_shift = event.shift

        events = ['MOUSEMOVE', *shift]

        if event.type in events:

            if event.type in ['MOUSEMOVE', *shift]:
                get_mouse_pos(self, context, event)

                self.loc = self.get_bevel_end_intersection(context, self.mouse_pos)
                self.amount = self.get_extend_amount(debug=False)

                if self.amount:
                    self.extend_hyper_bevel(both_ends=self.is_shift)

        if self.is_hypermod_invoke and event.type in ['LEFTMOUSE', 'SPACE'] and event.value == 'PRESS':
            self.finish(context)

            bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')
            return {'FINISHED'}

        elif not self.is_hypermod_invoke and event.type == 'E' and event.value == 'RELEASE':

            if context.window_manager.HC_pickhyperbevelsCOL:
                force_pick_hyper_bevels_gizmo_update(context)

            self.finish(context)
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:
            self.initbm.to_mesh(self.active.data)

            self.finish(context)

            if self.is_hypermod_invoke:
                bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')

            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        self.parent.show_wire = False

        context.window_manager.HC_pickhyperbevelshowHUD = True

        finish_status(self)

        force_ui_update(context)

    def invoke(self, context, event):
        self.active = bpy.data.objects[self.objname]
        self.mx = self.active.matrix_world

        self.parent = self.active.parent

        if self.active and self.modname and self.parent: 

            self.initbm = bmesh.new()
            self.initbm.from_mesh(self.active.data)
            self.initbm.normal_update()
            self.initbm.verts.ensure_lookup_table()

            edge_glayer = self.initbm.edges.layers.int.get('HyperEdgeGizmo')

            if edge_glayer:
                center_edges = []

                for e in self.initbm.edges:
                    if e[edge_glayer] == 1:
                        center_edges.append(e)

                if center_edges:

                    get_mouse_pos(self, context, event)

                    self.data = self.get_hyper_bevel_end_data(context, center_edges, self.mouse_pos, debug=False)

                    if self.data:

                        self.init_loc = self.get_bevel_end_intersection(context, self.mouse_pos, debug=False)
                        
                        self.loc = self.init_loc
                        self.amount = 0
                        self.is_shift = False
                        self.is_valid = True
                        
                        self.parent.show_wire = True

                        context.window_manager.HC_pickhyperbevelshowHUD = False

                        init_status(self, context, func=draw_extend_hyper_bevel_status(self))

                        self.area = context.area
                        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
                        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

                        context.window_manager.modal_handler_add(self)
                        return {'RUNNING_MODAL'}

        return {'CANCELLED'}

    def get_hyper_bevel_end_data(self, context, center_edges, mouse_pos, debug=False):

        center_verts = list(set(v for e in center_edges for v in e.verts))

        if debug:
            print("center edges:", [e.index for e in center_edges])
            print("center verts:", [v.index for v in center_verts])

        sequences = get_edges_vert_sequences(center_verts, center_edges, debug=False)

        if len(sequences) == 1:
            sorted_center_verts, cyclic = sequences[0]

            if not cyclic:

                start_vert = sorted_center_verts[0]
                next_vert = sorted_center_verts[1]

                end_vert = sorted_center_verts[-1]
                previous_vert = sorted_center_verts[-2]

                start_co = start_vert.co.copy()
                end_co = end_vert.co.copy()

                start_limit = next_vert.co + (start_co - next_vert.co) * 0.1
                end_limit = previous_vert.co + (end_co - previous_vert.co) * 0.1

                if debug:
                    draw_point(start_limit, mx=self.mx, color=green, modal=False)
                    draw_point(end_limit, mx=self.mx, color=red, modal=False)

                if len(sorted_center_verts) == 2:
                    center = get_center_between_verts(start_vert, end_vert)

                    start_center_limit = center + (start_co - center) * 0.1
                    end_center_limit = center + (end_co - center) * 0.1

                    if debug:
                        draw_point(center, mx=self.mx, modal=False)
                        draw_point(start_center_limit, mx=self.mx, color=green, modal=False)
                        draw_point(end_center_limit, mx=self.mx, color=red, modal=False)
                else:
                    start_center_limit = None
                    end_center_limit = None
    
                start_dir = (start_co - next_vert.co).normalized()
                end_dir = (end_co - previous_vert.co).normalized()

                if debug:
                    draw_vector(start_dir, start_co.copy(), mx=self.mx, color=green, fade=True, modal=False)
                    draw_vector(end_dir, end_co.copy(), mx=self.mx, color=red, fade=True, modal=False)

                start_co_2D = location_3d_to_region_2d(context.region, context.region_data, self.mx @ start_co)
                end_co_2D = location_3d_to_region_2d(context.region, context.region_data, self.mx @ end_co)

                side ='START' if (start_co_2D - mouse_pos).length < (end_co_2D - mouse_pos).length else 'END'

                if debug:
                    print("side:", side)

                data = {'side': side,

                        'start_indices': [start_vert.index],
                        'start_coords': [start_co],
                        'start_dirs': [start_dir],

                        'start_limit': start_limit,
                        'start_center_limit': start_center_limit,

                        'end_indices': [end_vert.index],
                        'end_coords': [end_co],
                        'end_dirs': [end_dir],

                        'end_limit': end_limit,
                        'end_center_limit': end_center_limit,

                        'center_indices': [v.index for v in sorted_center_verts],
                        }

                start_face = [f for f in start_vert.link_faces if len(f.verts) > 4][0]
                end_face = [f for f in end_vert.link_faces if len(f.verts) > 4][0]

                for face in [start_face, end_face]:
                    bevel_side = 'start' if face == start_face else 'end'
                    cap_verts = [v for v in face.verts if v not in [start_vert, end_vert]]
                    cap_edges = [e for e in face.edges]

                    for v in cap_verts:
                        data[f'{bevel_side}_indices'].append(v.index)
                        data[f'{bevel_side}_coords'].append(v.co.copy())

                        dir_edge = [e for e in v.link_edges if e not in cap_edges][0]
                        other_v = dir_edge.other_vert(v)

                        data[f'{bevel_side}_dirs'].append((v.co - other_v.co).normalized())

                if debug:
                    draw_vectors(data['start_dirs'][1:], data['start_coords'][1:], mx=self.mx, color=green, fade=True, alpha=0.3, modal=False)
                    draw_vectors(data['end_dirs'][1:], data['end_coords'][1:], mx=self.mx, color=red, fade=True, alpha=0.3, modal=False)

                self.coords = [self.mx @ v.co for v in sorted_center_verts]

                self.limit_coords = [self.mx @ data[f'{side.lower()}_limit']]

                return data

    def get_bevel_end_intersection(self, context, mouse_pos, debug=False):
        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)

        side = self.data['side'].lower()
        ext_origin = self.mx @ self.data[f'{side}_coords'][0]
        ext_dir = self.mx.to_3x3() @ self.data[f'{side}_dirs'][0]

        i = intersect_line_line(ext_origin, ext_origin + ext_dir, view_origin, view_origin + view_dir)

        if i:
            if debug:
                draw_point(i[0], color=yellow, modal=False)
            return i[0]

    def get_extend_amount(self, debug=False):
        move_dir = self.mx.inverted_safe().to_3x3() @ (self.loc - self.init_loc)
        
        ext_dir = self.data[f'{self.data["side"].lower()}_dirs'][0]
        dot = move_dir.normalized().dot(ext_dir)

        amount = move_dir.length if dot >= 0 else - move_dir.length

        if debug:
            print("amount:", self.amount)

        return amount

    def extend_hyper_bevel(self, both_ends=False):
        bm = self.initbm.copy()
        bm.verts.ensure_lookup_table()

        side = self.data["side"].lower()
        is_single_segment = len(self.data['center_indices']) == 2

        if both_ends:
            if is_single_segment:
                self.limit_coords = [self.mx @ self.data['start_center_limit'], self.mx @ self.data['end_center_limit']]
            else:
                self.limit_coords = [self.mx @ self.data['start_limit'], self.mx @ self.data['end_limit']]
        else:
            self.limit_coords = [self.mx @ self.data[f'{side}_limit']]

        for idx, (vidx, co, dir) in enumerate(zip(self.data[f'{side}_indices'], self.data[f'{side}_coords'], self.data[f'{side}_dirs'])):

            new_co = co + dir * self.amount

            if idx == 0:
                limit_co = self.data[f'{side}_center_limit'] if is_single_segment and both_ends else self.data[f'{side}_limit']
                new_dir = (new_co - limit_co).normalized()
                dot = new_dir.dot(dir)

                self.is_valid = dot > 0
                
                if not self.is_valid:
                    return

            vert = bm.verts[vidx]
            vert.co = new_co

        if both_ends:
            other_side = 'end' if side == 'start' else 'start'

            for idx, (vidx, co, dir) in enumerate(zip(self.data[f'{other_side}_indices'], self.data[f'{other_side}_coords'], self.data[f'{other_side}_dirs'])):

                new_co = co + dir * self.amount

                if idx == 0:
                    limit_co = self.data[f'{other_side}_center_limit'] if is_single_segment and both_ends else self.data[f'{other_side}_limit']
                    new_dir = (new_co - limit_co).normalized()
                    dot = new_dir.dot(dir)

                    self.is_valid = dot > 0
                    
                    if not self.is_valid:
                        return

                vert = bm.verts[vidx]
                vert.co = co + dir * self.amount

        self.coords = [self.mx @ bm.verts[idx].co.copy() for idx in self.data['center_indices']]

        bm.to_mesh(self.active.data)
        bm.free()
