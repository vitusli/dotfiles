from typing import Final
import bpy
from bpy.props import IntProperty, FloatProperty, BoolProperty, StringProperty
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d, location_3d_to_region_2d
import bmesh
from mathutils import Vector
from math import sin, radians, degrees, tan
from mathutils.geometry import intersect_line_line, intersect_line_plane, intersect_point_line
from .. utils.bmesh import ensure_custom_data_layers, ensure_gizmo_layers
from .. utils.draw import draw_fading_label, draw_line, draw_point, draw_init, draw_label, draw_vector, draw_lines, get_text_dimensions
from .. utils.gizmo import hide_gizmos, restore_gizmos
from .. utils.math import dynamic_format, get_center_between_verts, get_center_between_points, get_edge_normal, average_normals, get_angle_between_edges, get_world_space_normal 
from .. utils.modifier import add_bevel, apply_mod, get_edge_bevel_from_edge, get_edges_from_edge_bevel_mod_vgroup, is_edge_bevel, move_mod, remove_mod, sort_modifiers, subd_poll, flip_bevel_profile, flop_bevel_profile, get_bevel_profile_as_dict, set_bevel_profile_from_dict
from .. utils.object import get_min_dim
from .. utils.operator import Settings
from .. utils.registration import get_prefs
from .. utils.select import clear_hyper_edge_selection, get_selected_edges, get_hyper_edge_selection, get_edges_vert_sequences
from .. utils.system import printd
from .. utils.ui import force_geo_gizmo_update, get_mouse_pos, get_mousemove_divisor, ignore_events, navigation_passthrough, warp_mouse, wrap_mouse, get_zoom_factor, popup_message, init_status, finish_status, scroll_up, scroll_down, force_ui_update, get_scale
from .. utils.view import get_location_2d, get_view_origin_and_dir
from .. utils.vgroup import add_vgroup
from .. colors import white, yellow, green, red, blue, cyan, orange, normal
from .. items import ctrl, alt, shift, numbers, input_mappings

def draw_bevel_edge_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text=f"{'Add Modifier' if op.is_modifier and op.is_new_modifier else 'Edit Modifier' if op.is_modifier and not op.is_new_modifier else 'Mesh'} Bevel")

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

        if op.is_modifier:
            if len(op.mod_stack) > 1:
                row.label(text="", icon='EVENT_ALT')
                row.label(text=f"Move in Stack: {op.is_move}")

                row.separator(factor=2)

                if op.is_move:
                    row.label(text="", icon='MOUSE_MMB')
                    row.label(text="Move Up or Down")
                    return

            row.label(text="", icon='EVENT_Q')
            row.label(text=f"Width Mode: {op.offset_type.title()}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_SHIFT')
        row.label(text=f"Edge Loop: {op.loop}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_C')
        row.label(text=f"Chamfer: {op.is_chamfer}")

        if not op.is_chamfer:
            row.separator(factor=2)
            r = row.row(align=True)
            r.active = not op.is_custom_profile
            r.label(text="", icon='MOUSE_MMB')
            r.label(text=f"Segments: {op.segments}")

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

        row.separator(factor=2)
        row.label(text="", icon='EVENT_W')
        row.label(text=f"Wireframe: {op.active.show_wire}")

        if op.is_modifier and not op.is_move:
            row.separator(factor=2)

            row.label(text="", icon='EVENT_A')
            row.label(text=f"Apply Mod + Finish")

            row.label(text="", icon='EVENT_X')
            row.label(text=f"Remove Mod + Finish")

    return draw

class BevelEdge(bpy.types.Operator, Settings):
    bl_idname = "machin3.bevel_edge"
    bl_label = "MACHIN3: Bevel"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Edge accociated with Gizmo, that is to be beveled")
    is_hypermod_invoke: BoolProperty(name="is HyperMod invokation", default=False)
    offset_type: StringProperty(name="Offset Type", default='OFFSET')
    width: FloatProperty(name="Bevel Modifier Width", default=0)
    width_pct: FloatProperty(name="Bevel Modifier Width", default=0, min=0, max=100)
    segments: IntProperty(name="Bevel Segments", default=0, min=0)
    profile_segments: IntProperty(name="Bevel Profile Segments", default=0, min=0)
    profile_type: StringProperty(name="Profile Type", default='SUPERELLIPSE')
    is_chamfer: BoolProperty(name="Chamfer", default=False)
    use_full: BoolProperty(name="use special FULL 100% Bevel mode", default=True)
    loop: BoolProperty(name="Loop Bevel", default=False)
    is_modifier: BoolProperty(name="is Bevel Modifier", default=False)
    is_new_modifier: BoolProperty(name="is new Bevel Modifier", default=False)
    is_profile_drop: BoolProperty(name="is Profile Drop", default=False)
    has_custom_profile: BoolProperty(name="has Custom Profile", default=False)
    passthrough = None
    is_hypermod_invoke: BoolProperty()

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.select_get() and active.HC.ishyper

    @classmethod
    def description(cls, context, properties):
        return f"Bevel (Modifier) Edge {properties.index}\nALT: Repeat Previous Bevel\nCTRL: Use Mesh Bevel instead"

    def draw_HUD(self, context):
        if context.area == self.area:

            if not (self.is_modifier and not self.is_new_modifier) and self.init_loc_2d:
                draw_point(self.init_loc_2d.resized(3), size=4, alpha=1)

                mouse_dir = self.mouse_pos - self.init_loc_2d
                draw_vector(mouse_dir.resized(3), origin=self.init_loc_2d.resized(3), fade=True, alpha=0.5)

            draw_init(self)

            if self.is_modifier:
                if self.is_new_modifier:

                    title = f"🔧 {'Move' if self.is_move else 'Add'} Modifier{'s' if self.instanced_mods else ''}: "

                    dims = draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=yellow, alpha=1)
                    dims2 = draw_label(context, title=f"{self.bevel_mod.name} ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=white, alpha=0.5)

                    if self.instanced_mods:
                        draw_label(context, title="on active", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, size=9, color=white, alpha=0.15)

                        for mod in self.instanced_mods:
                            self.offset += 18

                            idims = draw_label(context, title=f"{mod.name} ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.25)
                            idims2 = draw_label(context, title="on instance ", coords=Vector((self.HUD_x + dims[0] + idims[0], self.HUD_y)), offset=self.offset, center=False, size=9, color=white, alpha=0.15)
                            draw_label(context, title=mod.id_data.name, coords=Vector((self.HUD_x + dims[0] + idims[0] + idims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.25)

                else:
                    if self.all_mods:

                        title = f"🔧 {'Move' if self.is_move else 'Edit'} All Modifier Bevels "

                        dims = draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=green, alpha=1)

                        if self.instanced_mods:
                            draw_label(context, title="on active", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=9, color=white, alpha=0.15)

                            for mod in self.instanced_mods:
                                self.offset += 18

                                idims = draw_label(context, title="on instance ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=9, color=white, alpha=0.15)
                                draw_label(context, title=mod.id_data.name, coords=Vector((self.HUD_x + dims[0] + idims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.25)

                    else:

                        title = f"🔧 {'Move' if self.is_move else 'Edit'} Modifier{'s' if self.instanced_mods else''}: "

                        dims = draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=green, alpha=1)
                        dims2 = draw_label(context, title=f"{self.bevel_mod.name} ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=white, alpha=0.5)

                        if self.instanced_mods:
                            draw_label(context, title="on active", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, size=9, color=white, alpha=0.15)

                            for mod in self.instanced_mods:
                                self.offset += 18

                                idims = draw_label(context, title=f"{mod.name} ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.25)
                                idims2 = draw_label(context, title="on instance ", coords=Vector((self.HUD_x + dims[0] + idims[0], self.HUD_y)), offset=self.offset, center=False, size=9, color=white, alpha=0.15)
                                draw_label(context, title=mod.id_data.name, coords=Vector((self.HUD_x + dims[0] + idims[0] + idims2[0], self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.25)

            else:

                dims = draw_label(context, title='🌐 Mesh Bevel ', coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

                if self.instanced_objects:
                    draw_label(context, title="on active", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=9, color=white, alpha=0.25)

                    for obj in self.instanced_objects:
                        self.offset += 18
                        draw_label(context, title=f"on {obj.name}", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=9, color=white, alpha=0.25)

            if self.is_move:
                scale = get_scale(context)

                self.offset += 24

                dims = draw_label(context, title="Stack: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

                for idx, mod in enumerate(self.mod_stack):
                    if idx:
                        self.offset += 18

                    is_sel = mod == self.bevel_mod

                    color = yellow if self.is_new_modifier and is_sel else green if is_sel else white
                    size, alpha = (12, 1) if is_sel else (10, 0.5)

                    if is_sel:
                        coords = [Vector((self.HUD_x + dims[0] - (5 * scale), self.HUD_y - (self.offset * scale), 0)), Vector((self.HUD_x + dims[0] - (5 * scale), self.HUD_y - (self.offset * scale) + (10 * scale), 0))]
                        draw_line(coords, color=color, width=2 * scale, screen=True)

                    dims2 = draw_label(context, title=mod.name, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=size, color=color, alpha=alpha)

                    if mod.profile_type == 'CUSTOM':
                        draw_label(context, title=" 🌠", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, size=size, color=blue, alpha=alpha)

            else:

                self.offset += 18
                bevel_type_color = orange if self.is_concave else blue

                if self.is_modifier:
                    is_percent = self.offset_type == 'PERCENT'
                    width = dynamic_format(self.bevel_mod.width_pct if is_percent else self.bevel_mod.width, decimal_offset=1)
                    alpha = 0.3 if width == '0' else 1

                    dims = draw_label(context, title=f"Width: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=alpha)

                    if self.offset_type == 'FULL':
                        draw_label(context, title="FULL", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=normal, alpha=alpha)
                    else:
                        color = green if is_percent else white
                        draw_label(context, title=f"{width}{'%' if is_percent else''}", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=color, alpha=alpha)

                else:
                    width = dynamic_format(self.width, decimal_offset=1)
                    alpha = 0.3 if width == '0' else 1
                    draw_label(context, title=f"Width: {width}", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=alpha)

                self.offset += 18

                if self.is_chamfer:
                    dims = draw_label(context, title="Chamfer ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=bevel_type_color, alpha=1)

                    if self.has_custom_profile:
                        draw_label(context, title="🌠", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=bevel_type_color, alpha=1)

                else:
                    alpha = 0.3 if (self.is_custom_profile or self.segments == 0) else 1
                    segments = self.profile_segments if self.is_custom_profile else self.segments

                    dims = draw_label(context, title=f"Segments: {segments} ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=alpha)

                    if self.has_custom_profile:
                        text = "Custom Profile" if self.is_custom_profile else "🌠"
                        draw_label(context, title=text, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=bevel_type_color, alpha=1)

                if self.loop:
                    self.offset += 18
                    draw_label(context, title=f"Edge Loop", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

                if self.active.show_wire:
                    self.offset += 18
                    draw_label(context, title="Wireframe", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

                if not self.is_chamfer and self.is_custom_profile and self.profile_HUD_coords:
                    draw_line(self.profile_HUD_coords, width=2, color=bevel_type_color, alpha=0.75)
                    draw_line(self.profile_HUD_border_coords, width=1, color=white, alpha=0.1)

                    for dir, origin in self.profile_HUD_edge_dir_coords:
                        draw_vector(dir, origin=origin, color=bevel_type_color, fade=True)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        if self.is_hypermod_invoke and event.type == 'TAB' and event.value == 'RELEASE':
            context.window.cursor_set('SCROLL_X')

        if event.type == 'MOUSEMOVE':
            get_mouse_pos(self, context, event)

            if self.is_modifier and not self.is_new_modifier:
                wrap_mouse(self, context, x=True)

            if self.is_custom_profile:
                self.get_profile_HUD_coords(context)

        if self.is_modifier and len(self.mod_stack) > 1:
            self.is_move = event.alt

        if self.is_move:

            if scroll_up(event, key=True) or scroll_down(event, key=True):
                if scroll_up(event, key=True):
                    self.move_bevel_mod_in_stack(direction='UP')

                else:
                    self.move_bevel_mod_in_stack(direction='DOWN')

            elif event.type in {'LEFTMOUSE', 'SPACE'} and event.value == 'PRESS':
                self.finish(context)

                if self.is_modifier:

                    profile = get_bevel_profile_as_dict(self.bevel_mod)
                    self._properties['machin3.bevel_edge'] = {'custom_profile': profile}

                clear_hyper_edge_selection(context, self.active)

                self.validate_modifier_edge_bevels(context)
                return {'FINISHED'}

            elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':

                mods = self.get_affected_mods()

                if self.is_new_modifier:
                    for mod in mods:
                        remove_mod(mod)

                    self.active.vertex_groups.remove(self.vgroup)

                else:
                    for mod in mods:
                        mod.width = self.init_modifier_width
                        mod.segments = self.init_modifier_segments
                        mod.profile_type = self.init_modifier_profile_type

                        if not self.is_new_modifier:
                            set_bevel_profile_from_dict(mod, self.init_modifier_custom_profile)

                    if self.is_profile_drop and (data := self.active.HC.get('init_custom_profile', None)):
                        del self.active.HC['init_custom_profile']

                    if len(self.mod_stack) > 1:
                        for stack_order in [self.init_stack_order] + self.init_instanced_stack_orders:
                            for mod, idx in stack_order.items():
                                if idx != list(mod.id_data.modifiers).index(mod):
                                    move_mod(mod, idx)

                if self.have_vgroups_changed:
                    self.initbm.to_mesh(self.active.data)
                    self.initbm.free()

                self.finish(context)
                return {'CANCELLED'}

            return {'RUNNING_MODAL'}

        self.is_custom_profile = self.has_custom_profile and self.profile_type == 'CUSTOM'

        events = ['MOUSEMOVE', 'C', 'W', *shift, *alt, *ctrl]

        if self.is_modifier:
            events.append('Q')

        if self.has_custom_profile:
            events.append('B')

        if self.is_custom_profile:
            events.extend(['F', 'V'])

        if event.type in events or (not self.is_chamfer and (scroll_up(event, key=True) or scroll_down(event, key=True))):

            if event.type == 'MOUSEMOVE':

                if self.passthrough:
                    self.passthrough = False

                    if self.is_modifier and not self.is_new_modifier:
                        self.last_mouse = self.mouse_pos

                self.get_width(context, event)

                if self.is_modifier:
                    mods = self.get_affected_mods()

                    for mod in mods:
                        self.set_mod_bevel_width(mod)

            elif event.type == 'Q' and event.value == 'PRESS':

                if self.offset_type == 'OFFSET':
                    self.offset_type = 'PERCENT'

                    if self.is_modifier and not self.is_new_modifier:
                        self.width_pct = self.width * (100 / self.min_dim)

                elif self.offset_type == 'PERCENT':
                    if self.use_full:
                        self.offset_type = 'FULL'

                    else:
                        self.offset_type = 'OFFSET'

                        if self.is_modifier and not self.is_new_modifier:
                            self.width = self.width_pct / (100 / self.min_dim)

                elif self.offset_type == 'FULL':
                    self.offset_type = 'OFFSET'

                    self.width = self.width_pct / (100 / self.min_dim)

                self.get_width(context, event)

                mods = self.get_affected_mods()

                for mod in mods:
                    mod.offset_type = 'PERCENT' if self.offset_type == 'FULL' else self.offset_type

                    self.set_mod_bevel_width(mod)

            elif not self.is_custom_profile and not self.is_chamfer and (scroll_up(event, key=True) or scroll_down(event, key=True)):
                change = 1

                if scroll_up(event, key=True):
                    self.segments += change

                elif scroll_down(event, key=True):
                    self.segments -= change

                if self.is_modifier:

                    mods = self.get_affected_mods()

                    for mod in mods:
                        mod.segments = self.segments + 1

            elif event.type == 'C' and event.value == 'PRESS':
                self.is_chamfer = not self.is_chamfer

                if self.is_modifier:
                    mods = [mod for mod in self.active.modifiers if is_edge_bevel(mod)] if self.all_mods else [self.bevel_mod]

                    for mod in mods:
                        mod.segments = 1 if self.is_chamfer else self.profile_segments if self.is_custom_profile else self.segments + 1

                    for imod in self.instanced_mods:
                        mods = [mod for mod in imod.id_data.modifiers if is_edge_bevel(mod)] if self.all_mods else [imod]

                        for mod in mods:
                            mod.segments = 1 if self.is_chamfer else self.profile_segments + 1 if self.is_custom_profile else self.segments + 1

            elif event.type == 'B' and event.value == 'PRESS':

                if self.is_chamfer and self.profile_type == 'CUSTOM':
                    self.is_chamfer = False

                elif self.profile_type == 'SUPERELLIPSE':
                    self.profile_type = 'CUSTOM'

                else:
                    self.profile_type = 'SUPERELLIPSE'

                mods = self.get_affected_mods()

                if self.profile_type == 'CUSTOM':

                    if self.is_chamfer:
                        self.is_chamfer = False

                    self.profile_segments = len(self.bevel_mod.custom_profile.points) - 2

                    for mod in mods:
                       mod.profile_type = 'CUSTOM'
                       mod.segments = self.profile_segments + 1

                    self.get_profile_HUD_coords(context)

                elif self.profile_type == 'SUPERELLIPSE':

                    for mod in mods:
                        mod.profile_type = 'SUPERELLIPSE'
                        mod.segments = self.segments + 1

            elif event.type == 'F' and event.value == 'PRESS':
                flip_bevel_profile(self.bevel_mod)

                for imod in self.instanced_mods:
                    flip_bevel_profile(imod)

                self.get_profile_HUD_coords(context)

            elif event.type == 'V' and event.value == 'PRESS':
                flop_bevel_profile(self.bevel_mod)

                for imod in self.instanced_mods:
                    flop_bevel_profile(imod)

                self.get_profile_HUD_coords(context)

            elif event.type == 'W' and event.value == 'PRESS':
                self.active.show_wire = not self.active.show_wire

            if event.type in shift:
                self.loop = not self.loop

                if self.is_modifier:
                    self.loop_vgroup(debug=False)

            force_ui_update(context, self.active)

        if self.is_modifier:

            if event.type == 'X' and event.value == 'PRESS':
                self.finish(context)

                mods = [mod for mod in self.active.modifiers if is_edge_bevel(mod)] if self.all_mods else [self.bevel_mod]

                for mod in mods:
                    vgroupname = mod.vertex_group

                    if vgroupname:
                        vgroup = self.active.vertex_groups.get(vgroupname)

                        if vgroup:
                            self.active.vertex_groups.remove(vgroup)

                    remove_mod(mod)

                for imod in self.instanced_mods:
                    mods = [mod for mod in imod.id_data.modifiers if is_edge_bevel(mod)] if self.all_mods else [imod]

                    for mod in mods:
                        remove_mod(mod)

                clear_hyper_edge_selection(context, self.active)

                self.validate_modifier_edge_bevels(context)
                return {'FINISHED'}

            if event.type == 'A' and event.value == 'PRESS':
                self.finish(context)

                mods = [mod for mod in self.active.modifiers if is_edge_bevel(mod)] if self.all_mods else [self.bevel_mod]

                for mod in mods:
                    vgroupname = mod.vertex_group

                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.object.mode_set(mode='OBJECT')

                    apply_mod(mod.name)

                    if vgroupname:
                        vgroup = self.active.vertex_groups.get(vgroupname)

                        if vgroup:
                            self.active.vertex_groups.remove(vgroup)

                if self.instanced_mods:
                    instanced_objects = []

                    for imod in self.instanced_mods:
                        obj = imod.id_data
                        instanced_objects.append(obj)

                        context.view_layer.objects.active = obj

                        mods = [mod for mod in obj.modifiers if is_edge_bevel(mod)] if self.all_mods else [imod]

                        for mod in mods:
                            vgroupname = mod.vertex_group

                            bpy.ops.object.mode_set(mode='EDIT')
                            bpy.ops.object.mode_set(mode='OBJECT')

                            apply_mod(mod.name, context=context, object=obj)

                            if vgroupname:
                                vgroup = obj.vertex_groups.get(vgroupname)

                                if vgroup:
                                    obj.vertex_groups.remove(vgroup)

                    context.view_layer.objects.active = self.active

                    for obj in instanced_objects:
                        mesh = obj.data
                        obj.data = self.active.data

                        bpy.data.meshes.remove(mesh)

                clear_hyper_edge_selection(context, self.active)

                self.validate_modifier_edge_bevels(context)

                force_geo_gizmo_update(context)
                return {'FINISHED'}

        else:
            self.mesh_bevel(context, offset=self.width, loop=self.loop)

            force_ui_update(context, self.active)

        if navigation_passthrough(event, alt=False) and self.is_modifier and not self.is_new_modifier:
            self.passthrough = True

            return {'PASS_THROUGH'}

        elif event.type in {'LEFTMOUSE', 'SPACE'} and event.value == 'PRESS':
            self.finish(context)

            if self.is_modifier:

                profile = get_bevel_profile_as_dict(self.bevel_mod)
                self._properties['machin3.bevel_edge'] = {'custom_profile': profile}

            clear_hyper_edge_selection(context, self.active)

            self.validate_modifier_edge_bevels(context)

            if self.is_hypermod_invoke:
                bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':

            if self.is_modifier:

                mods = self.get_affected_mods()

                if self.is_new_modifier:
                    for mod in mods:
                        remove_mod(mod)

                    self.active.vertex_groups.remove(self.vgroup)

                else:
                    for mod in mods:
                        mod.width = self.init_modifier_width
                        mod.segments = self.init_modifier_segments
                        mod.profile_type = self.init_modifier_profile_type

                        if not self.is_new_modifier:
                            set_bevel_profile_from_dict(mod, self.init_modifier_custom_profile)

                    if self.is_profile_drop and (data := self.active.HC.get('init_custom_profile', None)):
                        del self.active.HC['init_custom_profile']

                    if len(self.mod_stack) > 1:
                        for stack_order in [self.init_stack_order] + self.init_instanced_stack_orders:
                            for mod, idx in stack_order.items():
                                if idx != list(mod.id_data.modifiers).index(mod):
                                    move_mod(mod, idx)

                if self.have_vgroups_changed:
                    self.initbm.to_mesh(self.active.data)
                    self.initbm.free()

            else:

                self.initbm.to_mesh(self.active.data)
                self.initbm.free()

            self.finish(context)

            if self.is_hypermod_invoke:
                bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')
            return {'CANCELLED'}

        self.last_mouse = self.mouse_pos

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        if self.is_modifier and not self.is_new_modifier:
            context.window.cursor_set('DEFAULT')

        restore_gizmos(self)

        self.active.show_wire = False

        finish_status(self)

        force_ui_update(context)

    def invoke(self, context, event):
        wm = context.window_manager

        self.active = context.active_object
        self.mx = self.active.matrix_world
        self.min_dim = get_min_dim(self.active, world_space=False)  # used for get pct width in absolute mode (new mod or mesh bevel)

        self.initbm = bmesh.new()
        self.initbm.from_mesh(self.active.data)
        self.initbm.edges.ensure_lookup_table()

        vg_layer = ensure_custom_data_layers(self.initbm, vertex_groups=True, bevel_weights=False, crease=False)[0]

        if self.index == -1:
            if not self.is_hypermod_invoke:
                self.is_hypermod_invoke = True

            if self.is_hypermod_invoke:
                mod = self.active.modifiers.active

                if mod and is_edge_bevel(mod) and mod.vertex_group:
                    vg_index = [vg.name for vg in self.active.vertex_groups].index(mod.vertex_group)

                    vg_edges = get_edges_from_edge_bevel_mod_vgroup(self.initbm, vg_layer, vg_index)

                    if vg_edges:
                        self.edge = vg_edges[0]

                    else:
                        return {'CANCELLED'}

                else:
                    return {'CANCELLED'}

        else:

            self.edge = self.initbm.edges[self.index]

        self.is_concave = self.edge.calc_face_angle_signed(1) < 0
        
        bevel_mod, vg_name = self.unify_vgroups(vg_layer, mesh_bevel=event.ctrl, debug=False)

        if self.mesh_bevel:
            if self.have_vgroups_changed:
                self.mbbm = bmesh.new()
                self.mbbm.from_mesh(self.active.data)
                self.mbbm.edges.ensure_lookup_table()

            else:
                self.mbbm = self.initbm

        if event.alt:
            if self.is_modifier and self.width != 0:
                self.modifier_bevel(mod=bevel_mod, vgname=vg_name, redo=True, debug=False)

                if self.loop:
                    self.loop_vgroup()

                clear_hyper_edge_selection(context, self.active)
                return {'FINISHED'}

            elif not self.is_modifier and self.width != 0:
                self.mesh_bevel(context, offset=self.width, loop=self.loop)

                clear_hyper_edge_selection(context, self.active)

                force_ui_update(context)
                return {'FINISHED'}

            else:
                return {'CANCELLED'}

        else:

            self.loop = False if bevel_mod else self.active.HC.objtype == 'CYLINDER'

            self.is_modifier = not event.ctrl

            if self.is_modifier:
                self.modifier_bevel(mod=bevel_mod, vgname=vg_name, redo=False, debug=False)

                if self.loop:
                    self.loop_vgroup()

            else:
                self.instanced_objects = [obj for obj in bpy.data.objects if obj.data == self.active.data and obj != self.active] if self.active.data.users > 1 else None

                self.width = 0

        self.has_custom_profile = self.is_modifier and len(self.bevel_mod.custom_profile.points) > 2
        self.is_custom_profile = self.has_custom_profile and self.bevel_mod.profile_type == 'CUSTOM'

        if bevel_mod:
            self.factor = get_zoom_factor(context, self.mx @ get_center_between_verts(*[v for v in self.edge.verts]))

        get_mouse_pos(self, context, event, init_offset=True)

        self.get_profile_HUD_coords(context)

        if self.is_modifier and not self.is_new_modifier:

            self.last_mouse = self.mouse_pos

            context.window.cursor_set('SCROLL_X')

        else:

            self.edge_loc = self.get_mouse_edge_intersection(context, self.mouse_pos - self.mouse_offset)

            self.init_loc_2d = get_location_2d(context, self.edge_loc)

            warp_mouse(self, context, self.init_loc_2d, region=True)

            self.loc = self.get_view_plane_intersection(context, self.mouse_pos)
            self.init_loc = self.loc

        self.is_chamfer = self.bevel_mod.profile_type == 'CUSTOM' and self.bevel_mod.segments == 1 if self.is_modifier else False
        self.is_move = False
        self.all_mods = False

        if self.is_modifier:
            self.get_mod_stack(init=True)

        self.active.show_wire = True

        hide_gizmos(self, context)

        force_ui_update(context)

        init_status(self, context, func=draw_bevel_edge_status(self))

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def unify_vgroups(self, vg_layer, mesh_bevel=False, debug=False):

        self.have_vgroups_changed = False

        bevel_mod, vg_name = get_edge_bevel_from_edge(self.active, self.edge, vg_layer)

        vg = self.active.vertex_groups[vg_name] if vg_name else None

        if vg and mesh_bevel:
            vert_ids = [v.index for v in self.edge.verts]

            vg.remove(vert_ids)
            
            bevel_mod, vg_name = None, None

            self.have_vgroups_changed = True

        if not self.is_profile_drop:

            if debug:
                print()
                print("mesh bevel:", mesh_bevel)
                print("index edge:", self.edge.index)
                print(" vgroup:", f"{vg.name} index: {vg.index}" if vg else vg)
        
            hyper_selected_edges = get_hyper_edge_selection(self.initbm)
            other_edges = [e for e in hyper_selected_edges if e != self.edge]

            if other_edges:
                selected_edges = [self.edge] + other_edges
                selected_verts = set(v for e in selected_edges for v in e.verts)

                sideways_edges = [e for v in selected_verts for e in v.link_edges if e not in selected_edges]

                sideways_vgroups = {v.index: set() for v in selected_verts}

                if debug:
                    print()
                    print("sideways edges:")

                for e in sideways_edges:
                    edge_vgroups = [idx for idx in e.verts[0][vg_layer].keys() if idx in e.verts[1][vg_layer].keys()]

                    if debug:
                        print("  edge_vgroups:", edge_vgroups)

                    for v in e.verts:
                        if v.index in sideways_vgroups:
                            sideways_vgroups[v.index].update(edge_vgroups)

                if debug:
                    printd(sideways_vgroups, name='sideways vgroups')

                if debug:
                    if debug:
                        print()
                        print(" other edges:")

                for other_edge in other_edges:
                    if debug:
                        print("  edge:", other_edge.index)

                    other_bevel_mod, other_vg_name = get_edge_bevel_from_edge(self.active, other_edge, vg_layer)

                    if other_vg_name != vg_name:
                        other_vert_ids = [v.index for v in other_edge.verts]

                        if vg_name:
                            if debug:
                                print(f"   needs to be (re)assigned from vgroup '{other_vg_name}' to '{vg_name}'")

                            if vg_name:
                                vg.add(other_vert_ids, 1, 'ADD')

                        else:
                            if debug:
                                print(f"   vgroup '{other_vg_name}' needs to be cleared")

                        if other_vg_name:
                            other_vg = self.active.vertex_groups[other_vg_name]

                            for v in other_edge.verts:
                                if other_vg.index in sideways_vgroups[v.index]:
                                    other_vert_ids.remove(v.index)

                                    if debug:
                                        print(f"    avoiding removal of vgroup '{other_vg_name}' from vert {v.index}, as it has a sideways edge using the vgroup")

                            other_vg.remove(other_vert_ids)

                        self.have_vgroups_changed = True

        if debug:
            print()
            print("vgroup change?:", self.have_vgroups_changed)
            print("return:", bevel_mod, vg_name)

        return bevel_mod, vg_name

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
            offset_y = -(9 + (len(self.instanced_mods) * 18) * scale) - size

            offset = Vector((offset_x, offset_y))

            for p in points:
                co = Vector((self.HUD_x, self.HUD_y)) + offset + p.location * size
                self.profile_HUD_coords.append(co.resized(3))

            for corner in [(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)]:
                co = Vector((self.HUD_x, self.HUD_y)) + offset + Vector(corner)
                self.profile_HUD_border_coords.append(co.resized(3))

            self.profile_HUD_edge_dir_coords.append((Vector((-size * 0.7, 0, 0)), Vector((self.HUD_x, self.HUD_y, 0)) + offset.resized(3) + Vector((0, size, 0))))
            self.profile_HUD_edge_dir_coords.append((Vector((0, -size * 0.7, 0)), Vector((self.HUD_x, self.HUD_y, 0)) + offset.resized(3) + Vector((size, 0, 0))))

    def get_mouse_edge_intersection(self, context, mouse_pos):
        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)

        i = intersect_line_line(self.mx @ self.edge.verts[0].co, self.mx @ self.edge.verts[1].co, view_origin, view_origin + view_dir)

        if i:
            return i[0]

    def get_view_plane_intersection(self, context, mouse_pos):
        view_origin, view_dir = get_view_origin_and_dir(context, mouse_pos)

        i = intersect_line_plane(view_origin, view_origin + view_dir, self.edge_loc, view_dir)

        if i:
            return i

    def get_mod_stack(self, init=False, debug=False):
        stack = [mod for mod in self.active.modifiers if is_edge_bevel(mod)]

        if debug:
            print()
            print("stack:")

            for mod in stack:
                idx = list(self.active.modifiers).index(mod)
                print("*" if mod == self.bevel_mod else " ", idx, mod.name)

        self.mod_stack = stack

        self.instanced_mod_stacks = []

        if init:
            self.init_stack_order = {mod: list(self.active.modifiers).index(mod) for mod in stack}
            self.init_instanced_stack_orders = []

        for mod in self.instanced_mods:
            instanced_stack = [m for m in mod.id_data.modifiers if m.type == 'BEVEL' and 'Edge Bevel' in m.name]
            self.instanced_mod_stacks.append(instanced_stack)

            if init:
                instanced_stack_order = {m: list(m.id_data.modifiers).index(m) for m in instanced_stack}
                self.init_instanced_stack_orders.append(instanced_stack_order)

    def move_bevel_mod_in_stack(self, direction='UP'):
        for mod, mod_stack in zip([self.bevel_mod] + self.instanced_mods, [self.mod_stack] + self.instanced_mod_stacks):
            obj = mod.id_data

            list_idx = mod_stack.index(mod)

            if direction == 'UP':
                if list_idx == 0:
                    continue

                prev_mod = mod_stack[list_idx - 1]
                prev_idx = list(obj.modifiers).index(prev_mod)

                move_mod(mod, prev_idx)

            elif direction == 'DOWN':
                if list_idx == len(mod_stack) - 1:
                    continue

                next_mod = mod_stack[list_idx + 1]
                next_idx = list(obj.modifiers).index(next_mod)
                move_mod(mod, next_idx)

        self.get_mod_stack()

    def get_affected_mods(self):
        mods = [self.bevel_mod] + self.instanced_mods
        return mods

    def get_width(self, context, event):
        if self.offset_type == 'FULL':
            return

        if self.is_modifier and not self.is_new_modifier:
            divisor = 2 if event.ctrl else 10
            delta_x = self.mouse_pos.x - self.last_mouse.x

            delta_width = delta_x / divisor * self.factor
            delta_width_pct = delta_x / divisor  # percent bevels should not be distance based, so don't use the factor

            self.width += delta_width
            self.width_pct += delta_width_pct

        else:
            self.loc = self.get_view_plane_intersection(context, self.mouse_pos)

            self.width = (self.mx.to_3x3().inverted_safe() @ (self.loc - self.init_loc)).length

            self.width_pct = self.width * (100 / self.min_dim)

    def validate_modifier_edge_bevels(self, context, debug=False): 
        removed_vgroups = []
        removed_mods = []

        group_indices_in_use = set(group.group for v in self.active.data.vertices for group in v.groups)

        edge_bevel_vgroup_names = [(vg.name, vg.index in group_indices_in_use) for vg in self.active.vertex_groups if 'Edge Bevel' in vg.name]

        for name, referenced_by_verts in edge_bevel_vgroup_names:
            if not referenced_by_verts:
                vg = self.active.vertex_groups.get(name, None)

                if vg:
                    if debug:
                        print(f"removing vertex group {name} because it's not referenced by any vert")

                    self.active.vertex_groups.remove(vg)
                    removed_vgroups.append(f"Removed unused vertex group '{name}'")

        instances = [obj for obj in bpy.data.objects if obj.data == self.active.data and obj != self.active] if (self.active.data.users) > 1 else []

        objects = [self.active] + instances

        edge_bevels = [mod for obj in objects for mod in obj.modifiers if is_edge_bevel(mod)]

        for mod in edge_bevels:
            vgname = mod.vertex_group

            if not vgname or vgname not in self.active.vertex_groups:
                modname = mod.name
                objname = mod.id_data.name

                if debug:
                    print(f"removing modifier {modname} on {objname} because it has no vertex group")

                remove_mod(mod)

                removed_mods.append(f"Removed unused Edge Bevel modifier '{modname}'")

                if instances:
                    removed_mods[-1] += f"on {objname}"

        edge_bevels = [mod for obj in objects for mod in obj.modifiers if is_edge_bevel(mod)]

        for name, referenced_by_verts in edge_bevel_vgroup_names:
            if referenced_by_verts:
                if any(mod.vertex_group == name for mod in edge_bevels):
                    continue

                vg = self.active.vertex_groups.get(name, None)
                if vg:
                    if debug:
                        print(f"removing vertex group {name} because it's not referenced by any Edge Bevel mod")

                    self.active.vertex_groups.remove(vg)
                    removed_vgroups.append(f"Removed unused vertex group '{name}'")

        if removed_vgroups or removed_mods:
            draw_fading_label(context, text=removed_vgroups + removed_mods, color=yellow)

    def loop_vgroup(self, debug=False):
        bm = self.initbm.copy()
        bm.normal_update()
        bm.edges.ensure_lookup_table()

        edges = get_selected_edges(bm, index=self.index, loop=self.loop)

        if debug:
            print(sorted([e.index for e in edges]))

        allvertids = [v.index for v in bm.verts]
        self.vgroup.remove(allvertids)

        vertids = list({v.index for e in edges for v in e.verts})

        if debug:
            print(vertids)

        self.vgroup.add(vertids, 1, "ADD")

        bm.free()

    def mesh_bevel(self, context, offset=0, loop=False):
        bm = self.mbbm.copy()
        bm.normal_update()
        bm.edges.ensure_lookup_table()

        edge_glayer, face_glayer = ensure_gizmo_layers(bm)

        edges = get_selected_edges(bm, index=self.index, loop=loop)

        geo = bmesh.ops.bevel(bm, geom=edges, offset=offset, offset_type='OFFSET', loop_slide=True, segments=1 if self.is_chamfer else self.segments + 1, profile=0.58, affect='EDGES')

        if self.active.HC.objtype == 'CUBE':
            for e in geo['edges']:
                e[edge_glayer] = 1

            for f in geo['faces']:
                f[face_glayer] = 1

        elif self.active.HC.objtype == 'CYLINDER':

            cap_faces = [f for f in bm.faces if len(f.verts) != 4]

            if len(cap_faces) == 2:
                cyl_dir = (cap_faces[0].calc_center_median() - cap_faces[1].calc_center_median()).normalized()

                for e in geo['edges']:
                    
                    if e[edge_glayer] == 1:
                        continue

                    else:
                        edge_dir = (e.verts[0].co - e.verts[1].co).normalized()
                        dot = abs(edge_dir.dot(cyl_dir))
                        print("dot:", dot)
                        
                        e[edge_glayer] = dot < 0.5

            for f in geo['faces']:
                f[face_glayer] = 0

        if geo['edges']:
            shortest = min([e.calc_length() for e in geo['edges']])

            bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=shortest / 10)

        bm.to_mesh(self.active.data)
        bm.free()

    def set_mod_bevel_width(self, mod):
        if self.offset_type == 'FULL':
            if mod.width_pct != 100:
                mod.width_pct = 100

        else:
        
            if mod.offset_type == 'OFFSET':
                mod.width = self.width

            elif mod.offset_type == 'PERCENT':
                mod.width_pct = self.width_pct

    def modifier_bevel(self, mod=None, vgname='', redo=False, debug=False):

        instanced_objects = [obj for obj in bpy.data.objects if obj.data == self.active.data and obj != self.active] if self.active.data.users > 1 else []

        if mod and vgname:

            self.bevel_mod = mod

            self.vgroup = self.active.vertex_groups[vgname]

            self.instanced_mods = []

            for obj in instanced_objects:
                mods = [mod for mod in obj.modifiers if is_edge_bevel(mod) and mod.vertex_group == vgname]

                if mods:
                    self.instanced_mods.append(mods[0])

            self.is_new_modifier = False

        else:
            edge_vert_ids = set(v.index for v in self.edge.verts)

            edges = get_hyper_edge_selection(self.initbm, debug=False)
            selected_vert_ids = set(v.index for e in edges for v in e.verts)

            vertids = list(edge_vert_ids | selected_vert_ids)

            self.vgroup = add_vgroup(self.active, 'Edge Bevel', ids=vertids, weight=1)

            self.bevel_mod = add_bevel(self.active, name="Edge Bevel", width=0, limit_method='VGROUP', vertex_group=self.vgroup.name)

            self.instanced_mods = []

            for obj in instanced_objects:
                self.instanced_mods.append(add_bevel(obj, name="Edge Bevel", width=0, limit_method='VGROUP', vertex_group=self.vgroup.name))

            mods = self.get_affected_mods()

            for mod in mods:
                sort_modifiers(mod.id_data, remove_invalid=False, debug=False)

            self.is_new_modifier = True

        mods = self.get_affected_mods()

        for mod in mods:

            if self.is_new_modifier:
                mod.segments = 1 if self.is_chamfer else self.segments + 1

            else:
                mod.is_active = True
                mod.show_viewport = True

        if redo:
            
            data = props['custom_profile'] if (props := self._properties.get('machin3.bevel_edge', None)) else None

            for mod in mods:
                offset_type = 'PERCENT' if self.offset_type == 'FULL' else self.offset_type
                mod.offset_type = offset_type

                self.set_mod_bevel_width(mod)

                mod.segments = 1 if self.is_chamfer else self.segments + 1
                mod.profile_type = self.profile_type

                if data and len(data['points']) > 1:
                    set_bevel_profile_from_dict(mod, data)

        else:

            if not self.is_new_modifier:

                if self.is_profile_drop and (data := self.active.HC.get('init_custom_profile', None)):
                    self.init_modifier_custom_profile = dict(data)

                    self.segments = data['segments'] - 1

                else:
                    self.init_modifier_custom_profile = get_bevel_profile_as_dict(self.bevel_mod)

                self.init_modifier_offset_type = self.bevel_mod.offset_type
                self.init_modifier_width = self.bevel_mod.width
                self.init_modifier_width_pct = self.bevel_mod.width_pct

                self.init_modifier_segments = self.init_modifier_custom_profile['segments']           # both of these are part of the profile, which has been potentially dropped
                self.init_modifier_profile_type = self.init_modifier_custom_profile['profile_type']   # so that's why we get the profile first, and always get it even for new mods, it simplifies the code here

            self.offset_type = 'FULL' if self.bevel_mod.width_pct == 100 else self.bevel_mod.offset_type
            self.width = self.bevel_mod.width
            self.width_pct = self.bevel_mod.width_pct

            self.profile_type = self.bevel_mod.profile_type

            if self.profile_type == 'SUPERELLIPSE':
                self.segments = self.bevel_mod.segments - 1

            elif self.profile_type == 'CUSTOM':
                self.profile_segments = len(self.bevel_mod.custom_profile.points) - 2

class RemoveEdge(bpy.types.Operator):
    bl_idname = "machin3.remove_edge"
    bl_label = "MACHIN3: Remove Edge"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Edge accociated with Gizmo, that is to be removed")

    loop: BoolProperty(name="Loop Edge Selection", default=False)
    min_angle: IntProperty(name="Min Angle", default=60, min=0, max=180)
    prefer_center_of_three: BoolProperty(name="Prefer Center of 3 Edges", default=True)
    ring: BoolProperty(name="Ring Edge Selection", default=False)
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.select_get() and active.HC.ishyper

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)

        if self.loop:
            column.prop(self, 'prefer_center_of_three', toggle=True)
            column.prop(self, 'min_angle', toggle=True)

    @classmethod
    def description(cls, context, properties):
        return f"Remove Edge\nSHIFT: Remove Edge Loop\nCTRL: Remove Edge Ring"

    def invoke(self, context, event):
        self.loop = event.shift
        self.ring = event.ctrl
        return self.execute(context)

    def execute(self, context):
        active = context.active_object

        self.remove_edges(active, loop=self.loop, ring=self.ring)

        clear_hyper_edge_selection(context, active)

        return {'FINISHED'}

    def remove_edges(self, active, loop=False, ring=False):
        bm = bmesh.new()
        bm.from_mesh(active.data)
        bm.normal_update()
        bm.edges.ensure_lookup_table()

        edges = get_selected_edges(bm, index=self.index, loop=self.loop, min_angle=180 - self.min_angle, prefer_center_of_three=self.prefer_center_of_three, ring=ring)

        bmesh.ops.dissolve_edges(bm, edges=edges, use_verts=True, use_face_split=False)

        bm.normal_update()
        bm.to_mesh(active.data)
        bm.free()

def draw_loop_cut_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text=f"{'Loop Cut'}")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Confirm")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text="", icon='MOUSE_MOVE')
        row.label(text="Slide")

        row.separator(factor=2)

        row.label(text="", icon='MOUSE_MMB')
        row.label(text=f"Cuts: {op.cuts}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_G')
        row.label(text=f"Cut Ngons: {op.ring_ngons}")

    return draw

class LoopCut(bpy.types.Operator):
    bl_idname = "machin3.loop_cut"
    bl_label = "MACHIN3: Loop Cut"
    bl_description = "Loop Cut selected Edges\nALT: Repeat Previous Loop Cut\nCTRL: Force Ring Selection even with Hyper Selected Edges"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Edge that is to be loop cut")

    cuts: IntProperty(name="Number of Loop Cuts", default=1, min=1)
    amount: FloatProperty(name="Side Amount", default=0, min=-1, max=1)
    ring: BoolProperty(name="Use Ring Selection", default=False)
    ring_ngons: BoolProperty(name="Ring Select across n-gons", default=True)
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.select_get() and active.HC.ishyper

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            if self.data['coords']:
                for seq_coords in self.data['coords']:
                    draw_line(seq_coords, mx=self.mx, color=yellow, width=2, alpha=0.5)

    def draw_HUD(self, context):
        if context.area == self.area:
            hud = self.HUD_coords

            slide_remapped = self.amount + 1

            if self.is_vertical:
                draw_line((hud['bottom_left'], hud['top_left']), width=2, alpha=0.3)

                if self.snap:
                    for i in range(19):
                        snap_y = hud['height_gap'] + (hud['guide_height'] / 20) * (i + 1)
                        draw_point(Vector((hud['width_gap'], snap_y, 0)), size=5 if i == 9 else 4, alpha=1 if i == 9 else 0.2)

                space = hud['guide_height'] / (self.cuts + 1)

                first_hud_y = space * slide_remapped + hud['height_gap']

                for idx, cut in enumerate(range(self.cuts)):
                    draw_point(Vector((hud['width_gap'], first_hud_y + space * idx, 0)), color=yellow)

            else:
                draw_line((hud['top_left'], hud['top_right']), width=2, alpha=0.3)

                if self.snap:
                    for i in range(19):
                        snap_x = hud['width_gap'] + (hud['guide_width'] / 20) * (i + 1)
                        draw_point(Vector((snap_x, hud['height_gap'] * 9, 0)), size=5 if i == 9 else 4, alpha=1 if i == 9 else 0.2)

                space = hud['guide_width'] / (self.cuts + 1)

                first_hud_x = space * slide_remapped + hud['width_gap']

                for idx, cut in enumerate(range(self.cuts)):
                    draw_point(Vector((first_hud_x + space * idx, hud['height_gap'] * 9, 0)), color=yellow)

            draw_init(self)

            draw_label(context, title="Loop Cut", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

            self.offset += 18
            draw_label(context, title=f"Slide: {round(self.amount * 100)}%", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

            if self.snap:
                self.offset += 18
                draw_label(context, title="Snapping", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        self.snap = event.ctrl

        events = ['MOUSEMOVE', *ctrl, 'N', 'G']

        if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):

            if event.type in ['MOUSEMOVE', *ctrl]:
                get_mouse_pos(self, context, event)

                hud = self.HUD_coords

                if self.is_vertical:

                    if self.mouse_pos.y < hud['height_gap']:
                        warp_mouse(self, context, Vector((self.mouse_pos.x, hud['height_gap'])))

                    elif self.mouse_pos.y > hud['height_gap'] * 9:
                        warp_mouse(self, context, Vector((self.mouse_pos.x, hud['height_gap'] * 9)))

                    divisor = hud['guide_height'] / 2
                    subtractor = hud['mid_height'] / divisor

                    self.amount = self.mouse_pos.y / divisor - subtractor

                else:
                    if self.mouse_pos.x < hud['width_gap']:
                        context.window.cursor_warp(hud['width_gap'], event.mouse_y)
                        warp_mouse(self, context, Vector((hud['width_gap'], self.mouse_pos.y)))

                    elif self.mouse_pos.x > hud['width_gap'] * 9:
                        warp_mouse(self, context, Vector((hud['width_gap'] * 9, self.mouse_pos.y)))

                    divisor = hud['guide_width'] / 2
                    subtractor = hud['mid_width'] / divisor

                    self.amount = self.mouse_pos.x / divisor - subtractor

                if self.snap:
                    self.amount = round(self.amount, 1)

            elif scroll_up(event, key=True) or scroll_down(event, key=True):
                if scroll_up(event, key=True):
                    self.cuts += 1

                elif scroll_down(event, key=True):
                    self.cuts -= 1

                force_ui_update(context)

            elif event.type in ['G', 'N'] and event.value == 'PRESS':
                self.ring_ngons = not self.ring_ngons

                force_ui_update(context)

            self.loop_cut(context, cuts=self.cuts, amount=self.amount)

        if event.type in {'LEFTMOUSE', 'SPACE'} and event.value == 'PRESS':
            self.finish(context)

            clear_hyper_edge_selection(context, self.active)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':

            self.initbm.to_mesh(self.active.data)
            self.initbm.free()

            self.finish(context)

            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        self.active.show_wire = False

        restore_gizmos(self)

        finish_status(self)

        force_ui_update(context)

    def invoke(self, context, event):
        self.active = context.active_object
        self.mx = self.active.matrix_world

        self.initbm = bmesh.new()
        self.initbm.from_mesh(self.active.data)

        self.HUD_coords = self.get_HUD_coords(context)

        if event.alt:
            slide = self.loop_cut(context, cuts=self.cuts, amount=self.amount)

            force_ui_update(context, active=self.active)
            return {'FINISHED'}

        self.cuts = 1
        self.amount = 0
        self.is_vertical = False
        self.ring = event.ctrl

        self.snap = False

        self.HUD_coords = self.get_HUD_coords(context)

        slide = self.loop_cut(context, cuts=self.cuts, amount=self.amount)

        if not slide:
            self.ring = True
            slide = self.loop_cut(context, cuts=self.cuts, amount=self.amount)

        if slide:

            get_mouse_pos(self, context, event, init_offset=True)

            center_coords = self.get_center_coords(context, self.mouse_pos - self.mouse_offset)

            warp_mouse(self, context, center_coords)

            self.active.show_wire = True

            hide_gizmos(self, context)

            init_status(self, context, func=draw_loop_cut_status(self))

            self.area = context.area
            self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')
            self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        self.initbm.to_mesh(self.active.data)
        self.initbm.free()

        return {'CANCELLED'}

    def get_HUD_coords(self, context):
        width = context.region.width
        height = context.region.height

        width_gap = int(width / 10)
        height_gap = int(height / 10)

        hud = {'width': width,
               'height': height,

               'mid_width': width / 2,
               'mid_height': height / 2,

               'width_gap': width_gap,
               'height_gap': height_gap,

               'bottom_left': Vector((width_gap, height_gap, 0)),
               'top_left': Vector((width_gap, height_gap * 9, 0)),
               'top_right': Vector((width_gap * 9, height_gap * 9, 0)),

               'guide_width': width_gap * 8,
               'guide_height': height_gap * 8}

        return hud

    def get_center_coords(self, context, mouse_pos):
        if self.is_vertical:
            center_coords = Vector((mouse_pos.x, context.region.height / 2))
        else:
            center_coords = Vector((context.region.width / 2, mouse_pos.y))

        return center_coords

    def get_slide_data(self, bm, edges, debug=False):
        data = {'sequences': [],
                'coords': []}

        edge_verts = list({v for e in edges for v in e.verts})
        sequences = get_edges_vert_sequences(edge_verts, edges, debug=False)

        for verts, cyclic in sequences:

            seq_data = {'ordered': [v for v in verts],
                        'cyclic': cyclic,
                        'verts': {},
                        'edges': []}

            for idx, v in enumerate(verts):
                nextv = verts[(idx + 1) % len(verts)]

                if not cyclic and idx == len(verts) - 1:
                    prevv = verts[(idx - 1) % len(verts)]
                    edge = bm.edges.get([v, prevv])

                    fwd_loop = [l for l in edge.link_loops if l.vert == prevv][0]

                    left_edge = fwd_loop.link_loop_next.edge
                    right_edge = fwd_loop.link_loop_radial_next.link_loop_prev.edge

                else:
                    edge = bm.edges.get([v, nextv])
                    seq_data['edges'].append(edge)

                    fwd_loop = [l for l in edge.link_loops if l.vert == v][0]

                    left_edge = fwd_loop.link_loop_prev.edge
                    right_edge = fwd_loop.link_loop_radial_next.link_loop_next.edge

                seq_data['verts'][v] = {'co': v.co.copy(),
                                        'left_dir': left_edge.other_vert(v).co - v.co,
                                        'right_dir': right_edge.other_vert(v).co - v.co}

            data['sequences'].append(seq_data)

        if debug:
            printd(data, "sequences")

        return data

    def slide_edges(self, context, bm, edges=[], amount=0, index_edge_cos=[], debug=False):
        if edges:
            self.data = self.get_slide_data(bm, edges, debug=debug)

            hud = self.HUD_coords
            right_view_cos = [Vector((hud['mid_width'], hud['mid_height'])), Vector((hud['mid_width'] + 100, hud['mid_height']))]
            up_view_cos = [Vector((hud['mid_width'], hud['mid_height'])), Vector((hud['mid_width'], hud['mid_height'] + 100))]

            if debug:
                draw_line([co.resized(3) for co in right_view_cos], color=yellow, modal=False, screen=True)
                draw_line([co.resized(3) for co in up_view_cos], color=blue, modal=False, screen=True)

            right_view_dir = Vector((right_view_cos[1] - right_view_cos[0]))
            up_view_dir = Vector((up_view_cos[1] - up_view_cos[0]))

            for sequence in self.data['sequences']:
                coords = []

                if debug:
                    draw_line(index_edge_cos, mx=self.mx, color=cyan, modal=False)

                edge_distances = []

                for e in sequence['edges']:
                    vert_distances = sorted([((intersect_point_line(v.co, *index_edge_cos)[0] - v.co).length, v, e) for v in e.verts], key=lambda x: x[0])
                    edge_distances.append(vert_distances)

                first_vert, first_edge = min(edge_distances, key=lambda x: (x[0][0], x[1][0]))[0][1:3]

                fvco = first_vert.co.copy()

                if debug:
                    draw_point(fvco, mx=self.mx, modal=False)

                edge_view_cos = [location_3d_to_region_2d(context.region, context.region_data, self.mx @ v.co) for v in first_edge.verts]

                if debug:
                    draw_line([co.resized(3) for co in edge_view_cos], modal=False, screen=True)

                edge_view_dir = Vector((edge_view_cos[1] - edge_view_cos[0]))

                right_dot = edge_view_dir.normalized().dot(right_view_dir.normalized())
                up_dot = edge_view_dir.normalized().dot(up_view_dir.normalized())

                self.is_vertical = abs(right_dot) >= abs(up_dot)

                if debug:
                    print("\nvertical mouse movement:", self.is_vertical)

                factor = get_zoom_factor(context, self.mx @ fvco, scale=100, ignore_obj_scale=False)

                if debug:
                    print()
                    print("first vert:", first_vert.index)
                    print("factor:", factor)

                right_edge_dir = sequence['verts'][first_vert]['right_dir'].normalized() * factor
                left_edge_dir = sequence['verts'][first_vert]['left_dir'].normalized() * factor

                if debug:
                    draw_vector(right_edge_dir, origin=fvco, mx=self.mx, modal=False)
                    draw_vector(left_edge_dir, origin=fvco, mx=self.mx, modal=False)

                right_edge_view_cos = [location_3d_to_region_2d(context.region, context.region_data, self.mx @ fvco), location_3d_to_region_2d(context.region, context.region_data, self.mx @ (fvco + right_edge_dir))]
                left_edge_view_cos = [location_3d_to_region_2d(context.region, context.region_data, self.mx @ fvco), location_3d_to_region_2d(context.region, context.region_data, self.mx @ (fvco + left_edge_dir))]

                if debug:
                    print()
                    print("right edge view cos:", right_edge_view_cos)
                    print("left edge view cos:", left_edge_view_cos)

                    draw_line([co.resized(3) for co in right_edge_view_cos], color=red, modal=False, screen=True)
                    draw_line([co.resized(3) for co in left_edge_view_cos], color=green, modal=False, screen=True)

                right_edge_view_dir = right_edge_view_cos[1] - right_edge_view_cos[0]
                left_edge_view_dir = left_edge_view_cos[1] - left_edge_view_cos[0]

                if self.is_vertical:
                    right_dot = up_view_dir.normalized().dot(right_edge_view_dir.normalized())
                    left_dot = up_view_dir.normalized().dot(left_edge_view_dir.normalized())

                    if debug:
                        print("\nup view alignment")
                        print(" right edge:", right_dot)
                        print(" left edge:", left_dot)

                else:
                    right_dot = right_view_dir.normalized().dot(right_edge_view_dir.normalized())
                    left_dot = right_view_dir.normalized().dot(left_edge_view_dir.normalized())

                    if debug:
                        print("\nright view alignment")
                        print(" right edge:", right_dot)
                        print(" left edge:", left_dot)

                if amount >= 0:
                    move_dir_name = 'right' if right_dot >= left_dot else 'left'
                else:
                    move_dir_name = 'left' if right_dot >= left_dot else 'right'

                if debug:
                    print()
                    print("amount:", amount)
                    print("move_dir:", move_dir_name)

                for v in sequence['ordered']:
                    vdata = sequence['verts'][v]
                    v.co = vdata['co'] + vdata[f'{move_dir_name}_dir'] * abs(amount)

                    coords.append(v.co.copy())

                if sequence['cyclic']:
                    coords.append(sequence['ordered'][0].co.copy())

                self.data['coords'].append(coords)

    def loop_cut(self, context, cuts=1, amount=0):
        bm = self.initbm.copy()
        bm.normal_update()
        bm.edges.ensure_lookup_table()

        vertex_group_layer = bm.verts.layers.deform.verify()
        edge_glayer = ensure_gizmo_layers(bm)[0]

        edge = bm.edges[self.index]

        index_edge_cos = [v.co.copy() for v in edge.verts]

        selected = [e for e in get_hyper_edge_selection(bm) if e != edge]

        if not selected and not self.ring:
            self.ring = True

        edges = get_selected_edges(bm, index=self.index, ring=self.ring, ring_ngons=self.ring_ngons)

        geo = bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_only_quads=not self.ring_ngons)

        cut_edges = [el for el in geo['geom_inner'] if isinstance(el, bmesh.types.BMEdge)]
        cut_verts = list({v for e in cut_edges for v in e.verts})

        for v in cut_verts:
            for vgindex, weight in v[vertex_group_layer].items():

                if weight != 1 or v.calc_shell_factor() == 1:
                    del v[vertex_group_layer][vgindex]

        for e in cut_edges:
            e[edge_glayer] = 1

        self.slide_edges(context, bm, edges=cut_edges, amount=amount, index_edge_cos=index_edge_cos)

        bm.to_mesh(self.active.data)
        bm.free()

        return True if cut_edges else False

def draw_slide_edge_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text="Slide Edge")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Confirm")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text="", icon='MOUSE_MOVE')
        row.label(text=f"Amount: {round(op.slide * 100)}")

        row.separator(factor=2)

        row.label(text="", icon='EVENT_ALT')
        row.label(text=f"Slide on Opposite Side: {op.opposite}")

    return draw

class SlideEdge(bpy.types.Operator):
    bl_idname = "machin3.slide_edge"
    bl_label = "MACHIN3: Slide Edge"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Edge that is to be slid")

    slide: FloatProperty(name="Side Amount", default=0)
    loop: BoolProperty(name="Loop Slide", default=False)
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.select_get() and active.HC.ishyper

    @classmethod
    def description(cls, context, properties):
        if context.active_object.HC.objtype == 'CUBE':
            desc = "Slide Edge(s) (on Cubes)"
            desc += "\nSHIFT: Loop Slide"

        elif context.active_object.HC.objtype == 'CYLINDER':
            desc = "Slide Edge(s) (on Cylinders)"
            desc += "\nSHIFT: Skip Loop Slide"

        return desc

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            halve_screen_distance = context.region.height / 10 if self.is_vertical else context.region.width / 10
            guide_dir = Vector((0, halve_screen_distance)) if self.is_vertical else Vector((halve_screen_distance, 0))

            draw_vector(guide_dir.resized(3), origin=self.mouse_pos.resized(3), fade=True, alpha=0.3)
            draw_vector(-guide_dir.resized(3), origin=self.mouse_pos.resized(3), fade=True, alpha=0.3)

            dims = draw_label(context, title="Slide Edge", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

            if self.is_shift:
                draw_label(context, title=" a little", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            elif self.is_ctrl:
                draw_label(context, title=" a lot", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            self.offset += 18
            draw_label(context, title=f"Amount: {round(self.slide * 100)}%", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=1)

            if self.opposite:
                self.offset += 18
                draw_label(context, title="Opposite", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            for seq_coords in self.data['coords']['sequences']:
                draw_line(seq_coords, mx=self.mx, color=yellow, width=2, alpha=0.5)
      
            if self.data['coords']['rails']:
                draw_lines(self.data['coords']['rails'], mx=self.mx, color=green, width=2, alpha=0.5)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        self.opposite = event.alt

        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        events = ['MOUSEMOVE', *alt]

        if event.type in events:

            if event.type in ['MOUSEMOVE', *alt]:
                get_mouse_pos(self, context, event)
                wrap_mouse(self, context, x=True, y=True)

                divisor = 100 if event.shift else 1 if event.ctrl else 10

                if self.is_vertical:
                    delta_y = self.mouse_pos.y - self.last_mouse.y
                    delta_slide = (delta_y * self.factor) / divisor

                else:
                    delta_x = self.mouse_pos.x - self.last_mouse.x
                    delta_slide = (delta_x * self.factor) / divisor

                self.slide += delta_slide

                self.slide_edges(context, amount=self.slide, opposite=self.opposite)

                force_ui_update(context)

        if event.type in {'LEFTMOUSE', 'SPACE'} and event.value == 'PRESS':
            self.finish(context)

            clear_hyper_edge_selection(context, self.active)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':

            self.initbm.to_mesh(self.active.data)
            self.initbm.free()

            self.finish(context)
            return {'CANCELLED'}

        self.last_mouse = self.mouse_pos

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        context.window.cursor_set('DEFAULT')

        context.scene.HC.draw_HUD = True

        self.active.HC.geometry_gizmos_show = True

        self.active.show_wire = False

        restore_gizmos(self)

        finish_status(self)

        force_geo_gizmo_update(context)

    def invoke(self, context, event):
        self.active = context.active_object
        self.mx = self.active.matrix_world

        self.initbm = bmesh.new()
        self.initbm.from_mesh(self.active.data)

        self.slide = 0
        self.is_vertical = False
        self.opposite = False

        self.is_shift = False
        self.is_ctrl = False

        if self.active.HC.objtype == 'CUBE':
            self.loop = event.shift

        elif self.active.HC.objtype == 'CYLINDER':
            self.loop = not event.shift

        self.HUD_coords = self.get_HUD_coords(context)

        if not self.slide_edges(context):
            popup_message("You can't slide multiple edge sequences at the same time!", title="Illegal Selection")
            return {'CANCELLED'}

        self.factor = get_zoom_factor(context, self.data['edge_center'], scale=10, ignore_obj_scale=False)

        hide_gizmos(self, context)

        self.active.show_wire = True

        get_mouse_pos(self, context, event)

        context.window.cursor_set('SCROLL_Y' if self.is_vertical else 'SCROLL_X')

        self.last_mouse = self.mouse_pos

        init_status(self, context, func=draw_slide_edge_status(self))

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def get_data(self, bm, edges, debug=False):
        data = {'sequences': [],
                'coords': {'sequences': [],
                           'rails': []},
                'edge_center': self.mx @ get_center_between_verts(*[v for v in bm.edges[self.index].verts])}

        edge_verts = list({v for e in edges for v in e.verts})
        sequences = get_edges_vert_sequences(edge_verts, edges, debug=False)

        if len(sequences) > 1:
            return

        for verts, cyclic in sequences:

            seq_data = {'ordered': [v for v in verts],
                        'cyclic': cyclic,
                        'verts': {}}

            for idx, v in enumerate(verts):
                nextv = verts[(idx + 1) % len(verts)]

                if not cyclic and idx == len(verts) - 1:
                    prevv = verts[(idx - 1) % len(verts)]
                    edge = bm.edges.get([v, prevv])

                    fwd_loops = [l for l in edge.link_loops if l.vert == prevv]

                    if fwd_loops:
                        fwd_loop = fwd_loops[0]
                    else:
                        fwd_loop = edge.link_loops[0]

                    left_edge = fwd_loop.link_loop_next.edge
                    right_edge = fwd_loop.link_loop_radial_next.link_loop_prev.edge

                else:
                    edge = bm.edges.get([v, nextv])

                    fwd_loops = [l for l in edge.link_loops if l.vert == v]

                    if fwd_loops:
                        fwd_loop = fwd_loops[0]
                    else:
                        fwd_loop = edge.link_loops[0]

                    left_edge = fwd_loop.link_loop_prev.edge
                    right_edge = fwd_loop.link_loop_radial_next.link_loop_next.edge

                left_vert = left_edge.other_vert(v)
                right_vert = right_edge.other_vert(v)

                if not left_vert:
                    left_vert = right_vert

                elif not right_vert:
                    right_vert = left_vert

                seq_data['verts'][v] = {'co': v.co.copy(),
                                        'left_dir': left_vert.co - v.co,
                                        'right_dir': right_vert.co - v.co,

                                        'left_vert': left_vert,
                                        'right_vert': right_vert}

            data['sequences'].append(seq_data)

        if debug:
            printd(data, "sequences")

        return data

    def get_HUD_coords(self, context):
        width = context.region.width
        height = context.region.height

        width_gap = int(width / 10)
        height_gap = int(height / 10)

        hud = {'width': width,
               'height': height,

               'mid_width': width / 2,
               'mid_height': height / 2,

               'width_gap': width_gap,
               'height_gap': height_gap,

               'bottom_left': Vector((width_gap, height_gap, 0)),
               'top_left': Vector((width_gap, height_gap * 9, 0)),
               'top_right': Vector((width_gap * 9, height_gap * 9, 0)),

               'guide_width': width_gap * 8,
               'guide_height': height_gap * 8}

        return hud

    def slide_edges(self, context, amount=0, opposite=False, debug=False):
        bm = self.initbm.copy()
        bm.normal_update()
        bm.edges.ensure_lookup_table()

        edges = get_selected_edges(bm, index=self.index, loop=self.loop)

        self.data = self.get_data(bm, edges, debug=debug)

        if not self.data:
            return False

        hud = self.HUD_coords
        right_view_cos = [Vector((hud['mid_width'], hud['mid_height'])), Vector((hud['mid_width'] + 100, hud['mid_height']))]
        up_view_cos = [Vector((hud['mid_width'], hud['mid_height'])), Vector((hud['mid_width'], hud['mid_height'] + 100))]

        if debug:
            draw_line([co.resized(3) for co in right_view_cos], color=yellow, modal=False, screen=True)
            draw_line([co.resized(3) for co in up_view_cos], color=blue, modal=False, screen=True)

        right_view_dir = Vector((right_view_cos[1] - right_view_cos[0]))
        up_view_dir = Vector((up_view_cos[1] - up_view_cos[0]))

        for sequence in self.data['sequences']:
            coords = []

            first_edge = bm.edges[self.index]

            edge_view_cos = [location_3d_to_region_2d(context.region, context.region_data, self.mx @ v.co) for v in first_edge.verts]
            if debug:
                draw_line([co.resized(3) for co in edge_view_cos], modal=False, screen=True)

            edge_view_dir = Vector((edge_view_cos[1] - edge_view_cos[0]))

            right_dot = edge_view_dir.normalized().dot(right_view_dir.normalized())
            up_dot = edge_view_dir.normalized().dot(up_view_dir.normalized())

            self.is_vertical = abs(right_dot) - 0.4 >= abs(up_dot)

            if debug:
                print("\nvertical mouse movement:", self.is_vertical)

            first_vert = first_edge.verts[0]
            fvco = first_vert.co.copy()

            if debug:
                draw_point(fvco, mx=self.mx, modal=False)

            factor = get_zoom_factor(context, self.mx @ fvco, scale=100, ignore_obj_scale=False)

            if debug:
                print()
                print("first vert:", first_vert.index)
                print("factor:", factor)

            right_edge_dir = sequence['verts'][first_vert]['right_dir'].normalized() * factor
            left_edge_dir = sequence['verts'][first_vert]['left_dir'].normalized() * factor

            if debug:
                draw_vector(right_edge_dir, origin=fvco, mx=self.mx, modal=False)
                draw_vector(left_edge_dir, origin=fvco, mx=self.mx, modal=False)

            right_edge_view_cos = [location_3d_to_region_2d(context.region, context.region_data, self.mx @ fvco), location_3d_to_region_2d(context.region, context.region_data, self.mx @ (fvco + right_edge_dir))]
            left_edge_view_cos = [location_3d_to_region_2d(context.region, context.region_data, self.mx @ fvco), location_3d_to_region_2d(context.region, context.region_data, self.mx @ (fvco + left_edge_dir))]

            if debug:
                print()
                print("right edge view cos:", right_edge_view_cos)
                print("left edge view cos:", left_edge_view_cos)

                draw_line([co.resized(3) for co in right_edge_view_cos], color=red, modal=False, screen=True)
                draw_line([co.resized(3) for co in left_edge_view_cos], color=green, modal=False, screen=True)

            right_edge_view_dir = right_edge_view_cos[1] - right_edge_view_cos[0]
            left_edge_view_dir = left_edge_view_cos[1] - left_edge_view_cos[0]

            if self.is_vertical:
                right_dot = up_view_dir.normalized().dot(right_edge_view_dir.normalized())
                left_dot = up_view_dir.normalized().dot(left_edge_view_dir.normalized())

                if debug:
                    print("\nup view alignment")
                    print(" right edge:", right_dot)
                    print(" left edge:", left_dot)

            else:
                right_dot = right_view_dir.normalized().dot(right_edge_view_dir.normalized())
                left_dot = right_view_dir.normalized().dot(left_edge_view_dir.normalized())

                if debug:
                    print("\nright view alignment")
                    print(" right edge:", right_dot)
                    print(" left edge:", left_dot)

            if amount >= 0:
                move_dir_name = 'right' if right_dot >= left_dot else 'left'
            else:
                move_dir_name = 'left' if right_dot >= left_dot else 'right'

            if debug:
                print()
                print("amount:", amount)
                print("move_dir:", move_dir_name)

            if opposite:
                move_dir_name = 'right' if move_dir_name == 'left' else 'left'

            if debug:
                print("opposite:", opposite)

            for v in sequence['ordered']:
                vdata = sequence['verts'][v]
                move_dir = vdata[f'{move_dir_name}_dir'].normalized()

                v.co = vdata['co'] + (- move_dir if opposite else move_dir) * abs(amount)

                coords.append(v.co.copy())

                rail_co = vdata[f'{move_dir_name}_vert'].co.copy()

                self.data['coords']['rails'].extend([v.co.copy(), rail_co])

            if sequence['cyclic']:
                coords.append(sequence['ordered'][0].co.copy())

            self.data['coords']['sequences'].append(coords)

        edge_center = self.mx @ get_center_between_verts(*[v for v in first_edge.verts])
        self.factor = get_zoom_factor(context, edge_center, scale=10, ignore_obj_scale=False)

        bm.to_mesh(self.active.data)
        bm.free()

        return True

def draw_crease_edge_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text="Crease Edge")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Confirm")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.separator(factor=2)

        row.label(text="", icon='EVENT_ALT')
        row.label(text=f"Absolute: {op.absolute}")

    return draw

class CreaseEdge(bpy.types.Operator):
    bl_idname = "machin3.crease_edge"
    bl_label = "MACHIN3: Crease Edge"
    bl_description = "Crease Edge"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Edge that is to be slid")

    amount: FloatProperty(name="Crease Amount", min=-1, max=1)
    absolute: BoolProperty(name="Absolute Crease", default=False)
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT' and context.active_object:
            return subd_poll(context)

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            guide_dir = Vector((context.region.width / 10, 0))
            draw_vector(guide_dir.resized(3), origin=self.mouse_pos.resized(3), fade=True, alpha=0.3)
            draw_vector(-guide_dir.resized(3), origin=self.mouse_pos.resized(3), fade=True, alpha=0.3)

            for crease, coords, center2d, is_sel in self.creased_edges:

                draw_label(context, title=dynamic_format(crease, decimal_offset=1), coords=center2d, center=True, size=12 if is_sel else 10, color=green if is_sel else white, alpha=1 if is_sel else 0.4)

            dims = draw_label(context, title="Adjust Crease", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

            if self.is_shift:
                draw_label(context, title=" a little", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            elif self.is_ctrl:
                draw_label(context, title=" a lot", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            self.offset += 18
            decimal_offset = 2 if self.is_shift else 0 if self.is_ctrl else 1
            title = dynamic_format(self.amount, decimal_offset=decimal_offset)

            if self.absolute:
                if self.amount <= 0:
                    title = '0'
            elif self.amount > 0:
                title = '+' + title

            draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

            if self.absolute:
                self.offset += 18
                draw_label(context, title="Absolute", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=green, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            for crease, coords, center2d, is_sel in self.creased_edges:
                draw_line(coords, mx=self.mx, color=green if is_sel else white, alpha=0.2 if is_sel else 0.1, width=3 if is_sel else 1)
 
    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        self.absolute = event.alt

        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        events = ['MOUSEMOVE', *alt]

        if event.type in events:
            if event.type in ['MOUSEMOVE', *alt]:
                get_mouse_pos(self, context, event)
                wrap_mouse(self, context, x=True)

                delta_x = self.mouse_pos.x - self.last_mouse.x

                divisor = get_mousemove_divisor(event, normal=5, shift=20, ctrl=2.5, sensitivity=100)

                delta_crease = delta_x / divisor

                self.amount += delta_crease

                self.crease(context, amount=self.amount, absolute=False)

        if event.type in ['LEFTMOUSE', 'SPACE'] and event.value == 'PRESS':
            self.finish(context)

            clear_hyper_edge_selection(context, self.active)

            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:

            self.initbm.to_mesh(self.active.data)
            self.initbm.free()

            self.finish(context)
            return {'CANCELLED'}

        self.last_mouse = self.mouse_pos

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        finish_status(self)

        context.window.cursor_set('DEFAULT')

        restore_gizmos(self)

        force_ui_update(context)

    def invoke(self, context, event):
        self.active = context.active_object
        self.mx = self.active.matrix_world

        self.initbm = bmesh.new()
        self.initbm.from_mesh(self.active.data)

        subd = subd_poll(context)[0]

        if not subd.use_creases:
            subd.use_creases = True

        if subd.levels > subd.render_levels:
            subd.render_levels = subd.levels

        if subd.show_expanded:
            subd.show_expanded = False

        self.amount = 0
        self.is_shift = False
        self.is_ctrl = False

        self.crease(context, amount=0)

        get_mouse_pos(self, context, event)

        self.last_mouse = self.mouse_pos

        context.window.cursor_set('SCROLL_X')

        hide_gizmos(self, context)

        init_status(self, context, func=draw_crease_edge_status(self))
        self.active.select_set(True)

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def crease(self, context, amount, absolute=False):
        bm = self.initbm.copy()
        bm.normal_update()
        bm.edges.ensure_lookup_table()

        crease_layer = ensure_custom_data_layers(bm, vertex_groups=False, bevel_weights=False, crease=True)[0]

        sel = get_selected_edges(bm, index=self.index)

        self.creased_edges = []

        for e in bm.edges:

            init_crease = e[crease_layer]

            if e in sel:
                if self.absolute:
                    e[crease_layer] = max(self.amount, 0)
                else:
                    e[crease_layer] = max(init_crease + self.amount, 0)

            if e[crease_layer]:
                coords = [v.co.copy() for v in e.verts]
                center2d = location_3d_to_region_2d(context.region, context.region_data, get_center_between_points(*[self.mx @ co for co in coords]))
                is_sel = e in sel

                if center2d:
                    self.creased_edges.append((e[crease_layer], coords, center2d, is_sel))

        bm.to_mesh(self.active.data)

def draw_push_edge_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text="Push Edge")

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

            row.separator(factor=2)

            precision = 2 if op.is_shift else 0 if op.is_ctrl else 1
            row.label(text="", icon='MOUSE_MOVE')
            row.label(text=f"Amount: {dynamic_format(op.amount, decimal_offset=precision)}")

    return draw

class PushEdge(bpy.types.Operator):
    bl_idname = "machin3.push_edge"
    bl_label = "MACHIN3: Push Edge"
    bl_description = "description"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Edge that is to be slid")
    amount: FloatProperty(name="Push Amount", default=0)
    loop: BoolProperty(name="Loop Push", default=False)
    passthrough = None

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.select_get() and active.HC.ishyper

    @classmethod
    def description(cls, context, properties):
        if context.active_object.HC.objtype == 'CUBE':
            desc = "Push Edge(s) (on Cubes)"
            desc += "\nSHIFT: Loop Slide"

        elif context.active_object.HC.objtype == 'CYLINDER':
            desc = "Push Edge(s) (on Cylinders)"
            desc += "\nSHIFT: Skip Loop Slide"

        desc += "\nALT: Repeat Push using previous Amount"
        return desc

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        row = column.split(align=True)
        row.prop(self, 'amount', text='Amount')

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            dims = draw_label(context, title="Push Edge", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)

            if self.is_shift:
                draw_label(context, title=" a little", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

            elif self.is_ctrl:
                draw_label(context, title=" a lot", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

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

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            push_dir = self.loc - self.init_loc

            draw_vector(self.edge_normal * self.min_dim * 0.4, origin=self.edge_origin, fade=True, alpha=0.2)
            draw_vector(-self.edge_normal * self.min_dim * 0.4, origin=self.edge_origin, fade=True, alpha=0.2)

            draw_point(self.edge_origin, color=(1, 1, 0))
            draw_point(self.edge_origin + push_dir, color=(1, 1, 1))

            draw_line([self.edge_origin, self.edge_origin + push_dir], width=2, alpha=0.3)

            for coords in self.data['coords']:
                draw_line(coords, width=2, color=yellow, alpha=0.5)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        if ret := self.numeric_input(context, event):
            return ret

        else:
            return self.interactive_input(context, event)

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        restore_gizmos(self)

        finish_status(self)

        force_geo_gizmo_update(context)

    def invoke(self, context, event):
        self.debug = True
        self.debug = False

        self.active = context.active_object
        self.mx = self.active.matrix_world

        self.min_dim = get_min_dim(self.active)

        if self.active.HC.objtype == 'CUBE':
            self.loop = event.shift
        elif self.active.HC.objtype == 'CYLINDER':
            self.loop = not event.shift

        self.initbm = bmesh.new()
        self.initbm.from_mesh(self.active.data)

        self.bm = self.initbm.copy()
        self.bm.normal_update()
        self.bm.edges.ensure_lookup_table()

        self.edge = self.bm.edges[self.index]
        self.edge_normal = get_world_space_normal(get_edge_normal(self.edge), self.mx)
        self.edge_origin = self.mx @ get_center_between_verts(*self.edge.verts)

        edges = get_selected_edges(self.bm, index=self.index, loop=self.loop)

        if event.alt and self.amount != 0:

            self.data = self.get_data(self.bm, edges, debug=self.debug)

            self.push(interactive=False)
            return {'FINISHED'}

        get_mouse_pos(self, context, event, init_offset=True)

        self.init_loc = self.get_edge_normal_intersection(context, self.mouse_pos - self.mouse_offset)

        if self.init_loc:
            self.loc = self.init_loc

            self.data = self.get_data(self.bm, edges, debug=self.debug)

            self.amount = 0
            self.is_shift = False
            self.is_ctrl = False

            self.is_numeric_input = False
            self.is_numeric_input_marked = False
            self.numeric_input_amount = '0'

            hide_gizmos(self, context)

            init_status(self, context, func=draw_push_edge_status(self))

            force_ui_update(context, active=self.active)

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
        self.bm.edges.ensure_lookup_table()

        edges = get_selected_edges(self.bm, index=self.index, loop=self.loop)

        self.data = self.get_data(self.bm, edges, debug=self.debug)

        self.push(interactive=False)
        return {'FINISHED'}

    def get_edge_normal_intersection(self, context, mouse_pos):
        view_origin = region_2d_to_origin_3d(context.region, context.region_data, mouse_pos)
        view_dir = region_2d_to_vector_3d(context.region, context.region_data, mouse_pos)

        i = intersect_line_line(self.edge_origin, self.edge_origin + self.edge_normal, view_origin, view_origin + view_dir)

        if i:
            return i[0]

    def get_data(self, bm, edges, debug=False):
        index_edge = bm.edges[self.index]

        if debug:
            print("\nindex edge:", index_edge.index)
            print("\nselected edges:", [e.index for e in edges])

        data = {'sequences': [],
                'coords': []}

        edge_verts = list({v for e in edges for v in e.verts})
        sequences = get_edges_vert_sequences(edge_verts, edges, debug=False)

        for idx, (verts, cyclic) in enumerate(sequences):

            if debug:
                print("sequence:", idx, cyclic)

            seq_data = {'verts': {},
                        'sorted': [],
                        'cyclic': cyclic}

            for vidx, v in enumerate(verts):
                if debug:
                    print("", v.index)

                seq_data['sorted'].append(v)

                if cyclic:
                    prevv = verts[(vidx - 1) % len(verts)]
                    nextv = verts[(vidx + 1) % len(verts)]

                else:
                    prevv = verts[vidx - 1] if vidx > 0 else None
                    nextv = verts[vidx + 1] if vidx < len(verts) - 1 else None

                if debug:
                    print(" prev vert:", prevv.index if prevv else None)
                    print(" next vert:", nextv.index if nextv else None)

                if prevv and nextv:
                    prev_edge = bm.edges.get([v, prevv])
                    next_edge = bm.edges.get([v, nextv])
                    push_dir = average_normals([get_edge_normal(prev_edge), get_edge_normal(next_edge)])

                    angle = get_angle_between_edges(prev_edge, next_edge, radians=False)

                    beta = angle / 2

                    shell_factor = 1 / sin(radians(beta))

                    if debug:
                        print(" prev edge:", prev_edge.index if prev_edge else None)
                        print(" next edge:", next_edge.index if next_edge else None)

                elif prevv:
                    prev_edge = bm.edges.get([v, prevv])
                    edge_normal = get_edge_normal(prev_edge)
                    end_faces = [f for f in v.link_faces if f not in prev_edge.link_faces]

                    if debug:
                        print(" prev edge:", prev_edge.index)
                        print(" next edge:", None)
                        print(" end faces:", [f.index for f in end_faces])

                    push_dir, shell_factor = self.get_push_dir_from_end_faces(v, edge_normal, end_faces)

                else:
                    next_edge = bm.edges.get([v, nextv])
                    edge_normal = get_edge_normal(next_edge)
                    end_faces = [f for f in v.link_faces if f not in next_edge.link_faces]

                    push_dir, shell_factor = self.get_push_dir_from_end_faces(v, edge_normal, end_faces)

                    if debug:
                        print(" prev edge:", None)
                        print(" next edge:", next_edge.index)
                        print(" end faces:", [f.index for f in end_faces])

                if debug:
                    print(" push dir:", push_dir)
                    print(" shell_factor:", shell_factor)

                    if shell_factor != 1:

                        if shell_factor > 1:
                            draw_vector(push_dir * shell_factor, origin=v.co.copy(), mx=self.mx, color=yellow, normal=False, alpha=1, modal=False)
                            draw_vector(push_dir, origin=v.co.copy(),mx=self.mx, normal=False, alpha=1, modal=False)

                        else:
                            draw_vector(push_dir, origin=v.co.copy(),mx=self.mx, normal=False, alpha=1, modal=False)
                            draw_vector(push_dir * shell_factor, origin=v.co.copy(), mx=self.mx, color=yellow, normal=False, alpha=1, modal=False)

                    else:
                        draw_vector(push_dir, origin=v.co.copy(), mx=self.mx, normal=True, alpha=1, modal=False)

                seq_data['verts'][v] = {'init_co': v.co.copy(),
                                        'push_dir': push_dir,
                                        'shell_factor': shell_factor}

            data['sequences'].append(seq_data)

            coords = []

            for v in verts:
                coords.append(self.mx @ v.co.copy())

            if cyclic:
                coords.append(self.mx @ verts[0].co.copy())

            data['coords'].append(coords)

        if debug:
            printd(data, "sequences")

        return data

    def get_push_dir_from_end_faces(self, v, edge_normal, end_faces, debug=False):
        if end_faces:
            end_faces_normal = average_normals([f.normal for f in end_faces])

            if debug:
                draw_vector(end_faces_normal, origin=v.co, mx=self.mx, modal=False)

            i = intersect_line_plane(v.co + edge_normal, v.co + edge_normal + end_faces_normal, v.co, end_faces_normal)

            if i:
                push_dir = (i - v.co).normalized()

                if debug:
                    draw_point(i, mx=self.mx, modal=False)
                    draw_vector(end_faces_normal, origin=v.co, mx=self.mx, modal=False)

                alpha = degrees(edge_normal.angle(push_dir))

                beta = 180 - 90 - alpha

                if debug:
                    print(" alpha:", alpha)
                    print(" beta:", beta)

                shell_factor = 1 / sin(radians(beta))

            else:
                print("WARNING: no end face intersection, using edge normal as push dir")
                push_dir = edge_normal
                shell_factor = 1

        else:
            print("WARNING: no end faces, using edge normal as push dir")
            push_dir = edge_normal
            shell_factor = 1

        return push_dir, shell_factor

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

                self.push(interactive=False)

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

        events = ['MOUSEMOVE']

        if event.type in events:
            if event.type == 'MOUSEMOVE':
                get_mouse_pos(self, context, event)

                if self.passthrough:
                    self.passthrough = False

                    push_dir = self.loc - self.init_loc

                    self.loc = self.get_edge_normal_intersection(context, self.mouse_pos - self.mouse_offset)
                    self.init_loc = self.loc - push_dir 

                self.loc = self.get_edge_normal_intersection(context, self.mouse_pos - self.mouse_offset)

                if self.loc:

                    self.push(interactive=True)

                    force_ui_update(context, active=self.active)

        elif navigation_passthrough(event):
            self.passthrough = True

            return {'PASS_THROUGH'}

        elif event.type in ['LEFTMOUSE', 'SPACE'] and event.value == 'PRESS':

            clear_hyper_edge_selection(context, self.active)

            self.finish(context)
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC'] and event.value == 'PRESS':
            self.finish(context)

            self.initbm.to_mesh(self.active.data)
            self.initbm.free()

            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def push(self, interactive=True):
        if interactive:
            precision = 0.2 if self.is_shift else 5 if self.is_ctrl else 1

            push_dir = (self.loc - self.init_loc) * precision
            push_dir_local = self.mx.inverted_safe().to_3x3() @ push_dir 

            dot = round(push_dir.normalized().dot(self.edge_normal))

            self.amount = push_dir_local.length * dot

        for seqdata in self.data['sequences']:
            cyclic = seqdata['cyclic']

            for v, vdata in seqdata['verts'].items():
                v.co = vdata['init_co'] + vdata['push_dir'] * vdata['shell_factor'] * self.amount 

            if interactive:
                self.data['coords'] = []
                coords = []

                for v in seqdata['sorted']:
                    coords.append(self.mx @ v.co.copy())

                if cyclic:
                    coords.append(self.mx @ seqdata['sorted'][0].co.copy())

                self.data['coords'].append(coords)

        self.bm.to_mesh(self.active.data)

class StraightenEdges(bpy.types.Operator):
    bl_idname = "machin3.straighten_edges"
    bl_label = "MACHIN3: Straighten Edges"
    bl_description = "Straighten Multi-Edge Selections"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index of Edge that is to be straightend")
    loop: BoolProperty(name="Loop Straighten", default=False)
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.select_get() and active.HC.ishyper

    def draw(self, context):
        layout = self.layout
        column = layout.column()
    
    def execute(self, context):
        self.active = context.active_object
        self.mx = self.active.matrix_world

        bm = bmesh.new()
        bm.from_mesh(self.active.data)
        bm.normal_update()
        bm.edges.ensure_lookup_table()

        edges = get_selected_edges(bm, index=self.index, loop=self.loop)

        data = self.get_data(bm, edges, debug=False)

        if data['can_straighten']:
            for sequence in data['sequences']:
                for v, co in sequence.items():
                    v.co = co

            bm.to_mesh(self.active.data)

            clear_hyper_edge_selection(context, self.active)

            return {'FINISHED'}

        else:

            if 'SINGLE' in data['fail_reasons'] and 'CYCLIC' in data['fail_reasons']:
                msg = ['A single Edge is straight already, dummy.', "And a cyclic loop can't be straightened either."]

            elif 'SINGLE' in data['fail_reasons']:
                msg = ['A single Edge is straight already, dummy.']

            else:
                msg = ["A cyclic loop can't be straightened, dummy."]

            msg.append('Select multiple connected edges instead.')

            popup_message(msg, title="Illegal Selection")
            return {'CANCELLED'}

    def get_data(self, bm, edges, debug=False):
        index_edge = bm.edges[self.index]

        if debug:
            print("\nindex edge:", index_edge.index)
            print("\nselected edges:", [e.index for e in edges])

        data = {'sequences': [],
                'can_straighten': False,
                'fail_reasons': set()}

        edge_verts = list({v for e in edges for v in e.verts})
        sequences = get_edges_vert_sequences(edge_verts, edges, debug=False)

        for idx, (verts, cyclic) in enumerate(sequences):
            if debug:
                print("sequence:", idx, cyclic, len(verts), " verts long")

            sequence = {}

            if not cyclic and len(verts) > 2:
                if debug:
                    print(" can be straightened")

                if not data['can_straighten']:
                    data['can_straighten'] = True

                v_start = verts[0]
                v_end = verts[-1]

                if debug:
                    draw_line([v_start.co.copy(), v_end.co.copy()], mx=self.mx, modal=False)

                for v in verts:

                    if v in [v_start, v_end]:
                        continue

                    else:
                        i = intersect_point_line(v.co, v_start.co, v_end.co)
                        sequence[v] = i[0]

                        if debug:
                            draw_point(i[0], mx=self.mx, color=yellow, modal=False)

                    data['sequences'].append(sequence)

            else:
                if debug:
                    print(" ignoring")

                if cyclic:
                    data['fail_reasons'].add('CYCLIC')
                else:
                    data['fail_reasons'].add('SINGLE')

        if debug:
            printd(data)
            bpy.context.area.tag_redraw()

        return data
