import bpy
from bpy.props import StringProperty, BoolProperty, FloatProperty, IntProperty, EnumProperty
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Vector
from mathutils.geometry import intersect_line_plane
from math import degrees, sqrt
import bmesh
from uuid import uuid4
from .. utils.application import delay_execution
from .. utils.bmesh import ensure_gizmo_layers
from .. utils.curve import get_curve_coords
from .. utils.draw import draw_circle, draw_cross_3d, draw_init, draw_label, draw_mesh_wire, draw_point, draw_vector, draw_fading_label
from .. utils.gizmo import hide_gizmos, restore_gizmos, get_highlighted_gizmo
from .. utils.math import average_locations, get_world_space_normal
from .. utils.mesh import get_bbox, get_coords
from .. utils.modifier import remote_radial_array_poll, remote_mirror_poll, remove_mod, apply_mod, add_boolean, get_mod_obj, is_mod_obj
from .. utils.object import get_eval_bbox, remove_obj, get_object_tree, is_wire_object
from .. utils.operator import Settings
from .. utils.property import get_ordinal
from .. utils.raycast import get_closest
from .. utils.registration import get_addon
from .. utils.ui import get_mouse_pos, get_zoom_factor, ignore_events, navigation_passthrough, init_status, finish_status, popup_message, force_ui_update, get_scale
from .. utils.view import ensure_visibility, get_location_2d
from .. utils.system import printd
from .. items import merge_object_preset_items, alt
from .. colors import white, yellow, green, red, blue, normal

meshmachine = None
machin3tools = None

def draw_pick_object_tree_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text=f"Pick Object from Object Tree")

        if not op.highlighted:
            row.label(text="", icon='MOUSE_LMB')
            row.label(text="Finish")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text="", icon='EVENT_ALT')
        row.label(text=f"Affect All: {op.is_alt}")

        if op.is_alt:
            row.separator(factor=1)

            row.label(text="", icon='EVENT_V')
            row.label(text=f"Visible Only: {op.affect_all_visible_only}")

        row.separator(factor=2)

        if op.highlighted:
            row.label(text="", icon="RESTRICT_SELECT_OFF")
            row.label(text=op.highlighted.name)

            row.separator(factor=1)

            row.label(text="", icon='EVENT_F')
            row.label(text="Focus")

        else:
            row.label(text="", icon='EVENT_F')
            row.label(text="Center Pick" if op.is_alt else "Focus on Active")

        if op.highlighted or op.is_alt:
            row.separator(factor=2)

            row.label(text="", icon='EVENT_S')
            row.label(text="Select + Finish")

            row.separator(factor=1)

            row.label(text="", icon='EVENT_SHIFT')
            row.label(text="", icon='EVENT_S')
            row.label(text="Select Multiple")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_D')
            row.label(text="Toggle Modifier")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_X')
            row.label(text="Remove")

        row.separator(factor=2)
        row.label(text="Show")

        row.separator(factor=1)

        row.label(text="", icon='EVENT_N')
        row.label(text=f"Names: {op.show_names}")

        if op.has_any_hypercut:
            row.separator(factor=1)

            row.label(text="", icon='EVENT_C')
            row.label(text=f"Hyper Cuts: {op.show_hypercut}")

        if op.has_any_hyperbevel:
            row.separator(factor=1)

            row.label(text="", icon='EVENT_B')
            row.label(text=f"Hyper Bevels: {op.show_hyperbevel}")

        if op.has_any_other:
            row.separator(factor=1)

            row.label(text="", icon='EVENT_O')
            row.label(text=f"Others: {op.show_other}")

        if op.has_any_nonmodobjs:
            row.separator(factor=1)

            row.label(text="", icon='EVENT_M')
            row.label(text=f"Non-Mod Objects: {op.show_nonmodobjs}")

        if op.has_any_alt_mod_host_obj:
            row.separator(factor=1)

            row.label(text="", icon='EVENT_H')
            row.label(text=f"alt. Mod Hosts: {op.show_alt_mod_host_obj}")

        if op.highlighted and op.highlighted.modname:
            row.separator(factor=2)

            row.label(text="", icon='EVENT_TAB')
            row.label(text="Switch to Hyper Mod")

    return draw

class PickObjectTree(bpy.types.Operator, Settings):
    bl_idname = "machin3.pick_object_tree"
    bl_label = "MACHIN3: Pick Object Tree"
    bl_description = "Pick Objet from Object Tree"
    bl_options = {'REGISTER', 'UNDO'}

    show_names: BoolProperty(name="Show Names", default=True)
    show_alt_mod_host_obj: BoolProperty(name="Show Objects on alternative (non-active) Mod Host Objects", default=True)
    show_hyperbevel: BoolProperty(name="Show Hyper Bevels", default=False)
    show_hypercut: BoolProperty(name="Show Hyper Cuts", default=True)
    show_other: BoolProperty(name="Show Others Mod Objects", default=True)   # non hypercut and hyperbevel booeleans, but also mirror empties, etc
    show_nonmodobjs: BoolProperty(name="Show Non-Mod Objects", default=True)
    affect_all_visible_only: BoolProperty(name="Affect All Visible (only)", default=True)
    passthrough = None

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active

    def draw_HUD(self, context):
        if context.area == self.area:
            if context.window_manager.HC_pickobjecttreeshowHUD:

                hud_scale = get_scale(context)

                draw_init(self)

                if not self.highlighted:
                    dims = draw_label(context, title="Pick Object ", coords=Vector((self.HUD_x, self.HUD_y)), center=False, color=white, alpha=1)
                    dims2 = draw_label(context, title="in ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=white, alpha=0.5)
                    dims3 = draw_label(context, title="Object Tree ", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), center=False, color=white, alpha=1)

                    if self.is_alt:
                        dims4 = draw_label(context, title="Affect All ", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), center=False, size=10, color=blue, alpha=1)

                        if self.affect_all_visible_only:
                            dims4 = draw_label(context, title="Visible Only", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] +dims4[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

                    filters, on = self.get_filter_names()

                    if filters:
                        self.offset += 18
                        dims = draw_label(context, title="Show ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, size=10, color=white, alpha=0.5)
                        dims2 = draw_label(context, title=filters, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=10, color=white, alpha=1)
                        dims3 = draw_label(context, title=" on ", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, size=10, color=white, alpha=0.5)
                        draw_label(context, title=on, coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, size=10, color=yellow, alpha=1)

                gizmo_size = context.preferences.view.gizmo_size / 75
                hud_scale = get_scale(context)

                for t in self.treeCOL:
                    if t.show or (self.is_alt and not self.affect_all_visible_only) or t.remove:
                        color, alpha = (red, 0.5) if t.remove else (white, 0.3)

                        top_level_coords = Vector(t.co2d) + Vector((-3, 13)) * gizmo_size * hud_scale

                        if self.highlighted and t.is_highlight:

                            if self.is_alt:
                                gzm_level_coords = Vector(t.co2d) + Vector((52 if t.modname else 35, -3)) * gizmo_size * hud_scale
                                draw_label(context, title="Affect All", coords=gzm_level_coords, center=False, size=12, color=blue, alpha=1)

                            dims = draw_label(context, title=t.name, coords=top_level_coords, center=False, size=12, color=color, alpha=1)

                            if t.modhostobjname:
                                mod = bpy.data.objects[t.modhostobjname].modifiers[t.modname]

                                dims2 = draw_label(context, title=" of ", coords=top_level_coords + Vector((dims[0], 0)), center=False, color=white, alpha=0.5)
                                draw_label(context, title=t.modname, coords=top_level_coords + Vector((dims[0] + dims2[0], 0)), center=False, color=yellow, alpha=1 if mod.show_viewport else 0.3)

                                if t.modhostobjname != self.active.name:
                                    self.offset += 18

                                    dims2 = draw_label(context, title=" on ", coords=top_level_coords + Vector((dims[0], 0)), offset=self.offset, center=False, color=white, alpha=0.5)
                                    dims3 = draw_label(context, title=t.modhostobjname, coords=top_level_coords + Vector((dims[0] + dims2[0], 0)), offset=self.offset, center=False, color=normal, alpha=1)

                            if self.highlighted and t.name in self.parenting_map:
                                lvl = self.parenting_map[t.name]
                                color = green if lvl == 1 else yellow
                                alpha = 1 if lvl == 1 else max(0.25, 1 - (0.25 * (lvl - 2)))  # NOTE: lower the alpha down to the 5th level child, beyond that it will no longer be lowered

                                draw_label(context, title=f"{get_ordinal(self.parenting_map[t.name])} degree child" , coords=Vector(t.co2d) - (Vector((3, 18)) * hud_scale * gizmo_size), center=False, size=10, color=color, alpha=alpha)

                        elif not self.highlighted:

                            if self.show_names or t.remove:
                                draw_label(context, title=t.name, coords=top_level_coords, center=False, size=10, color=color, alpha=alpha)

                            if t.name in self.parenting_map:
                                lvl = self.parenting_map[t.name]
                                size, color, alpha = (10, green, 1) if lvl == 1 else (9, yellow, max(0.25, 1 - (0.25 * (lvl - 2))))  # NOTE: lower the alpha down to the 5th level child, beyond that it will no longer be lowered

                                draw_label(context, title=str(lvl), coords=Vector(t.co2d) - Vector((14, 3)) * hud_scale * gizmo_size, center=False, size=size, color=color, alpha=alpha)

                        batch = self.batches[t.name]

                        if batch == 'EMPTY':
                            if t.show:
                                if t.is_highlight or self.is_alt:
                                    color = red if t.remove else blue

                                    if t.modhostobjname:
                                        mod = bpy.data.objects[t.modhostobjname].modifiers[t.modname]
                                    else:
                                        mod = None

                                    if mod and mod.show_viewport or not mod:
                                        alpha = 1 if t.is_highlight else 0.2
                                    else:
                                        alpha = 0.2

                                    draw_circle(Vector(t.co2d), radius=10 * hud_scale, width=2 * hud_scale, color=color, alpha=alpha)

                            elif self.is_alt and not self.affect_all_visible_only:
                                color, alpha = (red, 0.1) if t.remove else (white, 0.05)
                                draw_circle(Vector(t.co2d), radius=10 * hud_scale, width=2 * hud_scale, color=color, alpha=alpha)

    def draw_VIEW3D(self, context):
        if context.area == self.area:

            if context.window_manager.HC_pickobjecttreeshowHUD:

                hud_scale = get_scale(context)

                if self.highlighted or self.is_alt:
                    for t in self.treeCOL:
                        if t.show:
                            if t.is_highlight or self.is_alt:
                                batch = self.batches[t.name]

                                if batch:
                                    color = red if t.remove else blue

                                    if batch == 'EMPTY':
                                        mx = bpy.data.objects[t.name].matrix_world

                                        zoom_factor = get_zoom_factor(context, depth_location=t.co, scale=10, ignore_obj_scale=True)

                                        draw_cross_3d(Vector(), mx=mx, color=color, width=2 * hud_scale, length=3 * zoom_factor * hud_scale, alpha=0.2, xray=True)

                                    else:
                                        draw_mesh_wire(batch, color=color, alpha=0.2, xray=True)

                                    if t.is_highlight:
                                        if t.modhostobjname:
                                            mod = bpy.data.objects[t.modhostobjname].modifiers[t.modname]
                                        else:
                                            mod = None

                                        if mod and mod.show_viewport or not mod:
                                            if batch:
                                                if batch == 'EMPTY':
                                                    draw_cross_3d(Vector(), mx=mx, color=color, width=2 * hud_scale, length=3 * zoom_factor * hud_scale, alpha=1, xray=True)

                                                else:
                                                    draw_mesh_wire(batch, color=color, alpha=1, xray=False)

                                        if t.modhostobjname != self.active.name:
                                            if t.modhostobjname in self.batches:
                                                batch = self.batches[t.modhostobjname]
                                                
                                                draw_mesh_wire(batch, color=normal, alpha=0.2 if mod and mod.show_viewport else 0.05, xray=True)

                            else:
                                color, alpha = (red, 0.5) if t.remove else (white, 0.3)
                                draw_point(Vector(t.co), color=color, size=3, alpha=alpha)

                        elif self.is_alt and not (self.is_alt and self.affect_all_visible_only):
                                batch = self.batches[t.name]

                                if batch:
                                    color, alpha = (red, 0.1) if t.remove else (white, 0.05)

                                    if batch == 'EMPTY':
                                        mx = bpy.data.objects[t.name].matrix_world
                                        loc = mx.inverted_safe() @ Vector(t.co)
                                        zoom_factor = get_zoom_factor(context, depth_location=t.co, scale=10, ignore_obj_scale=True)

                                        draw_cross_3d(Vector(), mx=mx, color=color, width=2 * hud_scale, length=3 * zoom_factor * hud_scale, alpha=alpha, xray=True)

                                    else:
                                        draw_mesh_wire(batch, color=color, alpha=alpha, xray=True)

                for t in self.treeCOL:
                    if not t.show and t.remove:
                        draw_point(Vector(t.co), color=red, size=3, alpha=0.5)

            else:
                for t in self.treeCOL:
                    if t.show or t.remove:
                        color, alpha = (red, 0.5) if t.remove else (white, 0.3)
                        draw_point(Vector(t.co), color=color, size=3, alpha=alpha)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        if self.treeCOL[0].select_finish:
            self.finish(context)
            self.save_settings()
            return {'FINISHED'}

        if self.is_alt_locked:
            if event.type in alt and event.value == 'PRESS':
                self.is_alt_locked = False

        if not self.is_alt_locked:
            self.is_alt = event.alt

        self.is_shift = event.shift

        events = ['MOUSEMOVE', 'F', 'N']

        if self.has_any_hyperbevel:
            events.append('B')

        if self.has_any_hypercut:
            events.append('C')

        if self.has_any_nonmodobjs:
            events.append('M')

        if self.has_any_other:
            events.append('O')

        if self.has_any_alt_mod_host_obj:
            events.append('H')

        if self.is_alt:
            events.append('V')

        self.highlighted = self.get_highlighted(context)

        if self.highlighted or self.is_alt:
            events.extend(['S', 'X'])

            if (self.highlighted and self.highlighted.modname) or self.is_alt:
                events.append('D')

            if (self.highlighted and self.highlighted.modname):
                events.append('TAB')

        if event.type in events:
            if event.type == 'MOUSEMOVE':
                if self.passthrough:
                    self.passthrough = False

                    for t in self.treeCOL:
                        t.co2d = get_location_2d(context, t.co, default='OFF_SCREEN')
                    self.repulse_2d_coords(context)

                    context.window_manager.HC_pickobjecttreeshowHUD = True

                get_mouse_pos(self, context, event)

            elif event.type == 'N' and event.value == 'PRESS':
                self.show_names = not self.show_names

                force_ui_update(context)

            elif event.type == 'S' and event.value == 'PRESS':
                select_entries, state = self.get_affected_collection_prop_entries(event, 'select')

                if select_entries:
                    bpy.ops.object.select_all(action='DESELECT')

                    for t in select_entries:
                        t.select = state

                    for t in self.treeCOL:
                        obj = bpy.data.objects[t.name]

                        obj.hide_set(not t.select)
                        
                        if t.select:
                            obj.select_set(True)

                            if t == select_entries[0]:
                                context.view_layer.objects.active = obj

                    if not any(t.select for t in self.treeCOL):
                        self.active.select_set(True)
                        context.view_layer.objects.active = self.active
                    
                    if event.shift:
                        return {'RUNNING_MODAL'}

                    elif state:
                        self.finish(context)
                        self.save_settings()
                        return {'FINISHED'}

                    return {'RUNNING_MODAL'}

            elif event.type == 'D' and event.value == 'PRESS':
                mod_entries, state = self.get_affected_collection_prop_entries(event, '')

                mods = [bpy.data.objects[t.modhostobjname].modifiers[t.modname] for t in mod_entries if t.modhostobjname]

                if mods:
                    state = not mods[0].show_viewport

                    for mod in mods:
                        mod.show_viewport = state

                return {'RUNNING_MODAL'}

            elif event.type == 'X' and event.value == 'PRESS':
                delete_entries, state = self.get_affected_collection_prop_entries(event, 'remove')

                if delete_entries:

                    for t in delete_entries:
                        t.remove = state

                        if t.modhostobjname:
                            mod_host_obj = bpy.data.objects[t.modhostobjname]
                            mod = mod_host_obj.modifiers[t.modname]

                            mod.show_viewport = not state

                return {'RUNNING_MODAL'}

            elif event.type == 'F' and event.value == 'PRESS':
                
                if event.alt:
                     bpy.ops.view3d.view_center_pick('INVOKE_DEFAULT')

                else:
                    if self.highlighted:
                        bpy.ops.object.select_all(action='DESELECT')

                        obj = bpy.data.objects[self.highlighted.name]
                        obj.hide_set(False)
                        obj.select_set(True)
                        bpy.ops.view3d.view_selected('INVOKE_DEFAULT' if context.scene.HC.focus_mode == 'SOFT' else 'EXEC_DEFAULT')
                        obj.hide_set(True)

                        self.active.select_set(True)

                    else:
                        bpy.ops.object.select_all(action='DESELECT')
                        self.active.select_set(True)
                        bpy.ops.view3d.view_selected('INVOKE_DEFAULT' if context.scene.HC.focus_mode == 'SOFT' else 'EXEC_DEFAULT')

                self.passthrough = True

                delay_execution(self.update_2d_coords, delay=0.2)
                return {'RUNNING_MODAL'}

            elif event.type == 'C' and event.value == 'PRESS':

                if event.shift:
                    self.show_hypercut = True
                    self.show_hyperbevel = False
                    self.show_other = False
                    self.show_nonmodobjs = False

                else:
                    self.show_hypercut = not self.show_hypercut

                for t in self.treeCOL:
                    t.show = self.is_obj_show(t)

                force_ui_update(context)
                return {'RUNNING_MODAL'}

            elif event.type == 'B' and event.value == 'PRESS':

                if event.shift:
                    self.show_hypercut = False
                    self.show_hyperbevel = True
                    self.show_other = False
                    self.show_nonmodobjs = False

                else:
                    self.show_hyperbevel = not self.show_hyperbevel

                for t in self.treeCOL:
                    t.show = self.is_obj_show(t)

                force_ui_update(context)
                return {'RUNNING_MODAL'}

            elif event.type == 'O' and event.value == 'PRESS':

                if event.shift:
                    self.show_hypercut = False
                    self.show_hyperbevel = False
                    self.show_other = True
                    self.show_nonmodobjs = False

                else:
                    self.show_other = not self.show_other

                for t in self.treeCOL:
                    t.show = self.is_obj_show(t)

                force_ui_update(context)
                return {'RUNNING_MODAL'}

            elif event.type == 'M' and event.value == 'PRESS':

                if event.shift:
                    self.show_hypercut = False
                    self.show_hyperbevel = False
                    self.show_other = False
                    self.show_nonmodobjs = True

                else:
                    self.show_nonmodobjs = not self.show_nonmodobjs

                for t in self.treeCOL:
                    t.show = self.is_obj_show(t)

                force_ui_update(context)
                return {'RUNNING_MODAL'}

            elif event.type == 'H' and event.value == 'PRESS':
                self.show_alt_mod_host_obj = not self.show_alt_mod_host_obj

                for t in self.treeCOL:
                    t.show = self.is_obj_show(t)

                force_ui_update(context)
                return {'RUNNING_MODAL'}

            elif event.type == 'V' and event.value == 'PRESS':
                self.affect_all_visible_only = not self.affect_all_visible_only

                self.treeCOL[0].affect_all_visible_only = self.affect_all_visible_only
                force_ui_update(context)
                return {'RUNNING_MODAL'}

            elif event.type == 'TAB' and event.value == 'PRESS':

                mod_host_obj = bpy.data.objects[self.highlighted.modhostobjname]

                if mod_host_obj:
                    bpy.ops.object.select_all(action='DESELECT')

                    ensure_visibility(context, mod_host_obj)

                    mod_host_obj.select_set(True)
                    context.view_layer.objects.active = mod_host_obj

                    self.finish(context)

                    self.save_settings()

                    bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')
                    return {'FINISHED'}

        if navigation_passthrough(event, alt=False, wheel=True) and not event.alt:
            self.passthrough = True

            context.window_manager.HC_pickobjecttreeshowHUD = False
            return {'PASS_THROUGH'}

        finish_events = ['SPACE']

        if not self.highlighted:
            finish_events.append('LEFTMOUSE')

        if event.type in finish_events and event.value == 'PRESS':

            for t in self.treeCOL:
                obj = bpy.data.objects[t.name]

                if not t.select:
                    obj.hide_set(not self.obj_visibility_map[obj])

            self.remove_objects_and_mods_marked_for_deletion(debug=False)

            self.finish(context)
            self.save_settings()
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC'] and event.value == 'PRESS':
            self.finish(context)

            for obj, state in self.obj_visibility_map.items():
                obj.hide_set(not state)

            for mod, state in self.mod_show_viewport_map.items():
                mod.show_viewport = state

            return {'CANCELLED'}

        if event.type == 'MOUSEMOVE' or (self.highlighted and event.type == 'LEFTMOUSE'):
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        finish_status(self)

        restore_gizmos(self)

        wm = context.window_manager
        wm.gizmo_group_type_unlink_delayed('MACHIN3_GGT_pick_object_tree')

        self.treeCOL.clear()

    def invoke(self, context, event):
        wm = context.window_manager

        self.active = context.active_object

        self.dg = context.evaluated_depsgraph_get()

        self.wire_children, self.mod_map = self.get_wire_children(context, self.active, debug=False)

        if self.wire_children:
            self.init_settings(props=['show_names', 'affect_all_visible_only'])
            self.load_settings()

            self.ensure_in_local_view(context.space_data, self.wire_children)

            self.area = context.area
            self.region = context.region
            self.region_data = context.region_data

            self.populate_pick_object_tree_collection(context)

            self.repulse_2d_coords(context)

            for obj in self.wire_children:
                obj.hide_set(True)

            self.highlighted = None
            self.last_highlighted = None

            self.is_alt = False
            self.is_alt_locked = event.alt

            self.is_shift = False

            get_mouse_pos(self, context, event)

            hide_gizmos(self, context)

            init_status(self, context, func=draw_pick_object_tree_status(self))

            wm.HC_pickobjecttreeshowHUD = True

            wm.gizmo_group_type_ensure('MACHIN3_GGT_pick_object_tree')

            self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
            self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

            wm.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:
            draw_fading_label(context, text="Object Tree is Empty", y=120, color=red, alpha=1, move_y=20, time=2)
            return {'CANCELLED'}

        return {'FINISHED'}

    def get_wire_children(self, context, active, debug=False):
        obj_tree = []
        mod_dict = {}
        get_object_tree(active, obj_tree, mod_objects=True, mod_dict=mod_dict, find_disabled_mods=True, ensure_on_viewlayer=True, debug=False)

        wire_children = []

        for obj in obj_tree:
            
            if is_wire_object(obj):

                if obj in active.children_recursive:
                    wire_children.append(obj)

                elif not obj.parent:
                    wire_children.append(obj)

                elif obj in mod_dict and any(mod.id_data == active for mod in mod_dict[obj]):
                    wire_children.append(obj)

        if debug:
            print("\nwire children on", active.name)

            for obj in wire_children:
                print(obj.name)

        if debug:
            print("\nmod dict")

            for obj, mods in mod_dict.items():
                print(obj.name, [(mod.name, "on", mod.id_data) for mod in mods])

        mod_map = {}

        for obj, mods in mod_dict.items():
            if debug:
                print(obj.name, [mod.name for mod in mods])

            if len(mods) > 1:
                keep = sorted([mod for mod in mods if mod.id_data == active], key=lambda x: list(active.modifiers).index(x))

                if keep:
                    mod = keep[0]

                else:
                    mod = mods[0]

            else:
                mod = mods[0]

            mod_map[obj] = mod
            
        if debug:
            print("\nre-sorting wire children by index in mod stack of active")

        idx = 0

        for mod in active.modifiers:
            modobj = get_mod_obj(mod)

            if modobj and modobj in wire_children:
                current_index = wire_children.index(modobj)

                if debug:
                    print(mod.name, "with", modobj.name, "is", current_index)

                if idx != current_index:
                    if debug:
                        print("  index mismatch, moving to", idx)

                    wire_children.insert(idx, wire_children.pop(current_index))

                idx += 1

        if debug:
            print("\nsorted wire children")

            for obj in wire_children:
                mod = mod_map[obj] if obj in mod_map else None

                if mod:
                    print(obj.name, mod.name, "on", mod.id_data.name)
                else:
                    print(obj.name, None)

        return wire_children, mod_map

    def ensure_in_local_view(self, view, objects):
        if view.local_view:
            for obj in objects:
                if not obj.local_view_get(view):
                    obj.local_view_set(view, True)

    def populate_pick_object_tree_collection(self, context):
        self.batches = {}
        self.obj_visibility_map = {obj: obj.visible_get() for obj in self.wire_children}
        self.mod_show_viewport_map = {}
        self.parenting_map = {}

        self.treeCOL = context.window_manager.HC_pickobjecttreeCOL
        self.treeCOL.clear()

        self.has_any_alt_mod_host_obj = False
        self.has_any_hyperbevel = False
        self.has_any_hypercut = False
        self.has_any_other = False
        self.has_any_nonmodobjs = False

        for idx, obj in enumerate(self.wire_children):
            mod = self.mod_map[obj] if obj in self.mod_map else None

            if obj.type == 'MESH' and [mod for mod in obj.modifiers if mod.type in ['ARRAY', 'MIRROR']]:
                bbox = get_bbox(obj.data)[0]
            else:
                bbox = get_eval_bbox(obj)

            co = obj.matrix_world @ average_locations(bbox)
            co2d = get_location_2d(context, co, default='OFF_SCREEN')
            t = self.treeCOL.add()
            t.co = co
            t.co2d = co2d
            t.name = obj.name

            t.modname = mod.name if mod else ''
            t.modhostobjname = mod.id_data.name if mod else ''

            t.select = False
            t.remove = False

            if idx == 0:
                t.affect_all_visible_only = self.affect_all_visible_only
                t.active_object = self.active

            if t.modname:
                if t.modhostobjname != self.active.name:
                    self.has_any_alt_mod_host_obj = True

                if 'Hyper Bevel' in t.modname:
                    self.has_any_hyperbevel = True

                elif 'Hyper Cut' in t.modname:
                    self.has_any_hypercut = True

                else:
                    self.has_any_other = True

                self.mod_show_viewport_map[mod] = mod.show_viewport

            else:
                self.has_any_nonmodobjs = True

            t.show = self.is_obj_show(t)

            t.area_pointer = str(self.area.as_pointer())

            mx = obj.matrix_world

            if obj.type == 'MESH':
                mesh_eval = obj.evaluated_get(self.dg).data
                batch = get_coords(mesh_eval, mx=mx, edge_indices=True)

            elif obj.type == 'CURVE':
                batch = get_curve_coords(obj.data, mx=mx)

            elif obj.type == 'EMPTY':
                batch = 'EMPTY'
                t.avoid_repulsion = True

            else:
                batch = None

            self.batches[obj.name] = batch

            if obj.parent:
                parent = obj.parent

                if parent == self.active and not obj.children:
                    continue

                lvl = 0

                while True:
                    lvl +=1

                    if parent == self.active or not parent:
                        self.parenting_map[t.name] = lvl
                        break

                    else:
                        obj = parent
                        parent = obj.parent

    def repulse_2d_coords(self, context, debug=False):
        def repulse(distance=50, debug=False):
            overlapping_points = {}

            for t in self.treeCOL:

                repulse_from_list = []

                for t2 in self.treeCOL:
                    if t != t2:

                        co_dir = Vector(t2.co2d) - Vector(t.co2d)

                        if co_dir.length < distance - 1:
                            repulse_from_list.append(Vector(t2.co2d))

                if repulse_from_list and not t.avoid_repulsion:
                    overlapping_points[t] = repulse_from_list
                    color = red

                else:
                    color = white

                if debug:
                    draw_circle(Vector(t.co2d), radius=distance / 2, color=color, alpha=0.5, screen=True, modal=False)

            if overlapping_points:
                for t, coords in overlapping_points.items():

                    move_dir = Vector((0, 0))
                    
                    for co in coords:
                        repulse_dir = Vector(t.co2d) - co
                        move_dir += repulse_dir.normalized() * (distance - repulse_dir.length)

                    move_dir = move_dir / sqrt((len(coords) + 2.5))
                    if debug:
                        draw_vector(move_dir.resized(3), origin=Vector(t.co2d).resized(3), fade=True, screen=True, modal=False)

                    repulse_co = Vector(t.co2d) + move_dir

                    if debug:
                        draw_point(repulse_co.resized(3), color=green, size=2, screen=True, modal=False)
                        draw_circle(repulse_co.resized(3), radius=distance / 2, color=green, alpha=0.5, screen=True, modal=False)

                    t.co2d = repulse_co

                return True
            return False

        def avoid_perfect_overlap(debug=False):
            identical_2d_coords = {}

            for t in self.treeCOL:
                co2d = tuple(t.co2d)

                if co2d in identical_2d_coords:
                    identical_2d_coords[co2d].append(t)

                else:
                    identical_2d_coords[tuple(t.co2d)] = [t]

            for ts in identical_2d_coords.values():
                if len(ts) > 1:
                    for idx, t in enumerate(ts[1:]):
                        t.co2d[1] += 1 + idx

                        if debug:
                            print("avoiding perfect overlap for", t.name, "with", ts[0].name)

        if debug:
            print()
            print("repulsing 2d coords")

            from time import time
            start = time()

        iterations = 30

        hud_scale = get_scale(context)
        distance = 40 * hud_scale

        avoid_perfect_overlap(debug=False)

        for i in range(iterations):
            if debug:
                print("\niteration:", i)

            repulsed = repulse(distance=distance, debug=False)

            if not repulsed:
                if debug:
                    print(f" finished repulsing early after {i} iterations")

                break

        if debug:
            print(f"repulsion took {time() - start} seconds")

    def is_obj_show(self, t):
        if t.modname:

            if t.modhostobjname != self.active.name:

                if not self.show_alt_mod_host_obj:
                    return False

            if 'Hyper Bevel' in t.modname:
                return self.show_hyperbevel

            elif 'Hyper Cut' in t.modname:
                return self.show_hypercut

            else:
                return self.show_other

        else:
            return self.show_nonmodobjs

    def get_highlighted(self, context):
        for t in self.treeCOL:
            if t.show and t.is_highlight:

                if t.modhostobjname:
                    mod_host_obj = bpy.data.objects[t.modhostobjname]
                    mod = mod_host_obj.modifiers[t.modname]
                    mod_host_obj.modifiers.active = mod

                if t != self.last_highlighted:
                    self.last_highlighted = t
                    force_ui_update(context)

                return t

        if self.last_highlighted:
            self.last_highlighted = None
            force_ui_update(context)

    def update_2d_coords(self):
        for t in self.treeCOL:
            t.co2d = Vector(round(i) for i in location_3d_to_region_2d(self.region, self.region_data, t.co, default=Vector((-1000, -1000))))
        self.active.select_set(True)

    def get_affected_collection_prop_entries(self, event, prop):
        if self.highlighted:
            state_t = self.highlighted

        elif event.alt:
            if self.affect_all_visible_only:
                state_t = None

                for t in self.treeCOL:
                    if t.show:
                        state_t = t
                        break

                if not state_t:
                    return None, None

            else:
                state_t = self.treeCOL[0]

        else:
            return None, None

        if event.alt:
            if self.affect_all_visible_only:
                entries = [t for t in self.treeCOL if t.show]

            else:
                entries = [t for t in self.treeCOL]
        else:
            entries = [state_t]

        return entries, not getattr(state_t, prop, '')

    def get_filter_names(self):
        filters = ''
        on = 'Active'

        if self.has_any_alt_mod_host_obj and self.show_alt_mod_host_obj:
            on += ' + alt. Mod Host Objs'

        if self.has_any_hypercut and self.show_hypercut:
            filters += 'Hyper Cuts'

        if self.has_any_hyperbevel and self.show_hyperbevel:
            filters += ' + Hyper Bevels'

        if self.has_any_other and self.show_other:
            filters += ' + Others'

        if self.has_any_nonmodobjs and self.show_nonmodobjs:
            filters += ' + Non-Mod Objects'

        if filters.startswith(' + '):
            filters = filters[3:]

        return filters, on

    def remove_objects_and_mods_marked_for_deletion(self, debug=False):
        if debug:
            print()
            print("deleting:")

        objects = set()

        for t in self.treeCOL:
            if t.remove:
                objects.add(bpy.data.objects[t.name])

        if objects:

            for obj in list(objects):
                objects.update(obj.children_recursive)

            for obj in objects:
                mods = is_mod_obj(obj)

                for mod in mods:
                    if debug:
                        print("removing mod", mod.name, "on", mod.id_data.name)

                    remove_mod(mod)

                if debug:
                    print("removing obj", obj.name)

                remove_obj(obj)

        else:
            if debug:
                print("no objects marked for deletion")

class TogglePickObjectTree(bpy.types.Operator):
    bl_idname = "machin3.toggle_pick_object_tree"
    bl_label = "MACHIN3: Toggle Pick Object Tree"
    bl_options = {'REGISTER', 'UNDO'}

    mode: StringProperty()

    @classmethod
    def description(cls, context, properties):
        h = get_highlighted_gizmo(context.window_manager.HC_pickobjecttreeCOL)

        if h:
            obj = bpy.data.objects[h.name]

            if properties.mode == 'SELECT':
                action = 'Select/Unhide'
                desc = f"{action} Object '{h.name}' and finish"
                desc += f"\nSHIFT: {action} Object '{h.name}' without finishing"
                desc += f"\nALT: Affect All"

                desc += f"\n\nShortcut: S and SHIFT + S"

            elif properties.mode == 'TOGGLE':
                if h.modhostobjname:
                    mod_host_obj = bpy.data.objects[h.modhostobjname]
                    mod = mod_host_obj.modifiers[h.modname]

                    if mod:
                        action = 'Disable' if mod.show_viewport else 'Enable'
                        desc = f"{action} Modifier '{h.modname}' on Object '{h.modhostobjname}'"
                        desc += f"\nALT: Affect All"

                        desc += f"\n\nShortcut: D"

            elif properties.mode == 'REMOVE':
                desc = f"Remove Object '{h.name}' and all Modifiers using it"
                desc += f"\nALT: Affect All"

                desc += f"\n\nShortcut: X"

            return desc
        return ''

    def invoke(self, context, event):
        self.treeCOL = context.window_manager.HC_pickobjecttreeCOL
        self.highlighted = get_highlighted_gizmo(self.treeCOL)

        if self.highlighted:
            if self.mode == 'SELECT':
                select_entries, state = self.get_affected_collection_prop_entries(event, 'select')

                if select_entries:
                    bpy.ops.object.select_all(action='DESELECT')

                    for t in select_entries:
                        t.select = state

                    for t in self.treeCOL:
                        obj = bpy.data.objects[t.name]

                        obj.hide_set(not t.select)
                        
                        if t.select:
                            obj.select_set(True)

                            if t == select_entries[0]:
                                context.view_layer.objects.active = obj

                    if not any(t.select for t in self.treeCOL):
                        active = self.treeCOL[0].active_object
                        active.select_set(True)
                        context.view_layer.objects.active = active

                    if not event.shift and state:
                        self.treeCOL[0].select_finish = True

                    return {'FINISHED'}

            elif self.mode == 'TOGGLE':
                mod_entries, _ = self.get_affected_collection_prop_entries(event, '')

                mods = [bpy.data.objects[t.modhostobjname].modifiers[t.modname] for t in mod_entries if t.modhostobjname]

                if mods:
                    state = not mods[0].show_viewport

                    for mod in mods:
                        mod.show_viewport = state

                    return {'FINISHED'}

            elif self.mode == 'REMOVE':
                delete_entries, state = self.get_affected_collection_prop_entries(event, 'remove')

                if delete_entries:
                    for t in delete_entries:
                        t.remove = state

                        if t.modhostobjname:
                            mod_host_obj = bpy.data.objects[t.modhostobjname]
                            mod = mod_host_obj.modifiers[t.modname]

                            mod.show_viewport = not state

                    return {'FINISHED'}
        return {'CANCELLED'}

    def get_affected_collection_prop_entries(self, event, prop):
        state_t = self.highlighted

        if event.alt:
            if self.treeCOL[0].affect_all_visible_only:
                entries = [t for t in self.treeCOL if t.show]

            else:
                entries = [t for t in self.treeCOL]

        else:
            entries = [state_t]

        return entries, not getattr(state_t, prop, None)

class MergeObject(bpy.types.Operator):
    bl_idname = "machin3.merge_object"
    bl_label = "MACHIN3: merge_object"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Face Index")

    def update_merge_presets(self, context):
        if self.merge_presets == '11':
            self.merge_factor = 1
            self.cleanup_factor = 1
        elif self.merge_presets == '12':
            self.merge_factor = 1
            self.cleanup_factor = 2
        elif self.merge_presets == '1020':
            self.merge_factor = 10
            self.cleanup_factor = 20

    merge_presets: EnumProperty(name="Merge Presets", items=merge_object_preset_items, default='1020', update=update_merge_presets)
    merge_factor: FloatProperty(name="Merge Factor", default=10)
    cleanup_factor: FloatProperty(name="Cleanup Factor", default=20)
    redundant_edges: BoolProperty(name="Remove Redundant Edges", default=True)
    @classmethod
    def description(cls, context, properties):
        active = context.active_object

        desc = "Merge Object at chosen Face Gizmo"

        if active:
            if active.modifiers:
                desc += "\n\nNOTE: Object should not have modifiers, but currently has, preventing the merge"

            targets = [obj for obj in context.visible_objects if obj.type == 'MESH' and obj != active and obj.display_type not in ['WIRE', 'BOUNDS'] and not obj.modifiers]

            if not targets:
                desc += "\n\nNOTE: No viable Mesh Objects (without modifiers) closeby, merge not possible"

        return desc

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object

            if active and not active.modifiers:
                return [obj for obj in context.visible_objects if obj.type == 'MESH' and obj != active and obj.display_type not in ['WIRE', 'BOUNDS'] and not obj.modifiers]

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)

        row = column.split(factor=0.2, align=True)
        row.label(text='Presets')
        r = row.row(align=True)
        r.prop(self, 'merge_presets', expand=True)

        row = column.split(factor=0.21, align=True)
        row.label(text='Factor')
        row.prop(self, 'merge_factor', text='Merge')
        row.prop(self, 'cleanup_factor', text='Cleanup')

        row = column.split(factor=0.2, align=True)
        row.label(text='Remove')
        row.prop(self, 'redundant_edges', text='Redundant Edges', toggle=True)

    def execute(self, context):
        active = context.active_object

        if context.visible_objects:
            dg = context.evaluated_depsgraph_get()

            targets = [obj for obj in context.visible_objects if obj.type == 'MESH' and obj != active and obj.display_type not in ['WIRE', 'BOUNDS'] and not obj.modifiers]

            if targets:
                mx = active.matrix_world.copy()

                bm = bmesh.new()
                bm.from_mesh(active.data)
                bm.faces.ensure_lookup_table()

                face = bm.faces[self.index]

                face_origin = mx @ face.calc_center_median()
                face_normal = get_world_space_normal(face.normal, mx)

                merge_obj, _, hitco, hitno, _, distance = get_closest(dg, targets=targets, origin=face_origin, debug=False)

                if merge_obj and distance < 0.01:
                    merge_obj.select_set(True)

                    merge_depth = distance * self.merge_factor

                    corners = {v: None for v in face.verts}

                    face_edges = [e for e in face.edges]

                    for v in corners:

                        corner_edges = [(e, face.normal.dot((v.co - e.other_vert(v).co).normalized())) for e in v.link_edges if e not in face_edges]

                        if corner_edges:
                            best_edge = max(corner_edges, key=lambda x: x[1])[0]

                            corners[v] = (v.co - best_edge.other_vert(v).co).normalized()

                    local_hitco = mx.inverted_safe() @ hitco
                    local_hitno = mx.inverted_safe().to_3x3() @ hitno

                    for v, vdir in corners.items():
                        i = intersect_line_plane(v.co, v.co + vdir, local_hitco, local_hitno)

                        if i:
                            v.co = i

                    for v, vdir in corners.items():

                        v.co += vdir * merge_depth

                    bm.to_mesh(active.data)
                    bm.free()

                    mod = add_boolean(merge_obj, active, method='UNION', solver='EXACT')

                    context.view_layer.objects.active = merge_obj
                    apply_mod(mod.name)

                    remove_obj(active)

                    bm = bmesh.new()
                    bm.from_mesh(merge_obj.data)

                    cleanup_distance = distance * self.cleanup_factor

                    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=cleanup_distance)
                    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=cleanup_distance)

                    self.dissolve_redundant_geometry(bm, verts=True, edges=self.redundant_edges, redundant_angle=179.999)

                    edge_glayer, face_glayer = ensure_gizmo_layers(bm)

                    gangle = 20

                    for e in bm.edges:
                        if len(e.link_faces) == 2:
                            angle = degrees(e.calc_face_angle())
                            e[edge_glayer] = angle >= gangle
                        else:
                            e[edge_glayer] = 1

                    for f in bm.faces:
                        if merge_obj.HC.objtype == 'CYLINDER' and len(f.edges) == 4:
                            f[face_glayer] = 0
                        elif not all(e[edge_glayer] for e in f.edges):
                            f[face_glayer] = 0
                        else:
                            f[face_glayer] = any([degrees(e.calc_face_angle(0)) >= gangle for e in f.edges])

                    bm.to_mesh(merge_obj.data)
                    bm.free()

                    context.area.tag_redraw()

                    bpy.ops.machin3.draw_active_object(time=2, alpha=0.7)
                    return {'FINISHED'}

                else:
                    popup_message(["No viable merge object found!", "Note, that both objects should not have any modifiers."])

        return {'CANCELLED'}

    def dissolve_redundant_geometry(self, bm, verts=True, edges=True, redundant_angle=179.999):
        if edges:
            manifold_edges = [e for e in bm.edges if e.is_manifold]

            redundant_edges = []

            for e in manifold_edges:
                angle = degrees(e.calc_face_angle(0))

                if angle < 180 - redundant_angle:
                    redundant_edges.append(e)

            bmesh.ops.dissolve_edges(bm, edges=redundant_edges, use_verts=False)

            two_edged_verts = {v for e in redundant_edges if e.is_valid for v in e.verts if len(v.link_edges) == 2}
            bmesh.ops.dissolve_verts(bm, verts=list(two_edged_verts))

        if verts:
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

            bmesh.ops.dissolve_verts(bm, verts=redundant_verts)

class DuplicateObject(bpy.types.Operator):
    bl_idname = "machin3.duplicate_object"
    bl_label = "MACHIN3: Duplicate Object"
    bl_description = "Duplicate Object with its entire Object Tree\nThe Object Tree includes all recursive Children and all recursive Modifier Objects\nALT: Instance"
    bl_options = {'REGISTER', 'UNDO'}

    instance: BoolProperty(name="Instance", default=False)
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.active_object

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        column.prop(self, 'instance', toggle=True)

    def invoke(self, context, event):
        self.instance = event.alt
        return self.execute(context)

    def execute(self, context):
        view = context.space_data
        active = context.active_object

        obj_tree = [active]

        get_object_tree(active, obj_tree, mod_objects=True, ensure_on_viewlayer=True, debug=False)

        originals = {str(uuid4()): (obj, obj.visible_get()) for obj in obj_tree}

        bpy.ops.object.select_all(action='DESELECT')

        for dup_hash, (obj, visible) in originals.items():
            obj.HC.dup_hash = dup_hash

            if not visible:
                if view.local_view and not obj.local_view_get(view):
                    obj.local_view_set(view, True)

                obj.hide_set(False)

            obj.select_set(True)

        bpy.ops.object.duplicate(linked=self.instance)

        for dup in context.selected_objects:
            orig, visible = originals[dup.HC.dup_hash]

            orig.HC.dup_hash = ''
            dup.HC.dup_hash = ''

            orig.hide_set(not visible)

            if orig.parent in obj_tree:
                dup.hide_set(not visible)

        return {'FINISHED'}

class HideWireObjects(bpy.types.Operator):
    bl_idname = "machin3.hide_wire_objects"
    bl_label = "MACHIN3: Hide Wire Objects"
    bl_description = "Hide all visible Wire Objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        global machin3tools, meshmachine

        if machin3tools is None:
            machin3tools = get_addon('MACHIN3tools')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        active = context.active_object
       
        wire_objects = [obj for obj in context.visible_objects if is_wire_object(obj)]

        if machin3tools:
            wire_objects = [obj for obj in wire_objects if not (obj.type == 'EMPTY' and obj.M3.is_group_empty)]

        if meshmachine:
            wire_objects = [obj for obj in wire_objects if not (obj.type == 'MESH' and obj.MM.isplughandle)]

        for obj in wire_objects:
            obj.hide_set(True)

        if active in wire_objects:

            if active.parent:

                obj = active

                while obj.parent:
                    obj = obj.parent

                    if obj.visible_get() and obj.type == 'MESH' and obj.HC.ishyper and not is_wire_object(obj):
                        obj.select_set(True)
                        context.view_layer.objects.active = obj
                        return {'FINISHED'}

                    elif obj.parent is None:

                        if obj.visible_get():
                            obj.select_set(True)
                            context.view_layer.objects.active = obj

            else:

                arrays = remote_radial_array_poll(context, active)

                for obj in arrays:
                    if obj.visible_get() and obj.type == 'MESH' and obj.HC.ishyper and not is_wire_object(obj):
                        obj.select_set(True)
                        context.view_layer.objects.active = obj
                        return {'FINISHED'}

                mirrors = remote_mirror_poll(context, active)

                for obj in mirrors:
                    if obj.visible_get() and obj.type == 'MESH' and obj.HC.ishyper and not is_wire_object(obj):
                        obj.select_set(True)
                        context.view_layer.objects.active = obj
                        return {'FINISHED'}

        return {'FINISHED'}

class HideMirrorObj(bpy.types.Operator):
    bl_idname = "machin3.hide_mirror_obj"
    bl_label = "MACHIN3: (Un)Hide Mirror"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    unhide: BoolProperty(name="Unhide instead of Hide", default=False)
    def execute(self, context):
        active = context.active_object

        name = active.HC.get('hidename')
        hideobj = bpy.data.objects.get(name)

        if hideobj:
            if self.unhide:
                bpy.ops.object.select_all(action='DESELECT')
                active.select_set(True)

                hideobj.hide_set(False)
                hideobj.select_set(True)

            else:
                hideobj.hide_set(True)

                del active.HC['hidename']

            return {'FINISHED'}
