import bpy
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty
from bpy_extras.view3d_utils import location_3d_to_region_2d
import bmesh
from mathutils import Vector
from uuid import uuid4
from math import degrees, radians
from .. utils.application import delay_execution
from .. utils.modifier import add_displace, add_solidify, add_subdivision, add_weld, get_edges_from_edge_bevel_mod_vgroup, get_mod_input, is_array, is_edge_bevel, is_linear_array, is_radial_array, remove_mod, add_boolean, move_mod, remote_boolean_poll, get_mod_obj, set_mod_input, sort_modifiers, is_remote_mod_obj, get_new_mod_name, get_prefix_from_mod, get_mod_base_name, is_auto_smooth, is_hyper_array
from .. utils.registration import get_addon, get_prefs
from .. utils.object import flatten, get_bbox, get_min_dim, parent, unparent, get_eval_bbox, get_object_tree, remove_unused_children
from .. utils.raycast import get_closest
from .. utils.property import step_list
from .. utils.ui import force_obj_gizmo_update, get_mouse_pos, get_mousemove_divisor, get_zoom_factor, ignore_events, navigation_passthrough, popup_message, init_status, finish_status, scroll_up, scroll_down, force_ui_update, get_scale, is_key, wrap_mouse
from .. utils.math import average_locations, dynamic_format
from .. utils.draw import draw_circle, draw_cross_3d, draw_mesh_wire, draw_point, draw_init, draw_label, draw_line, draw_fading_label
from .. utils.workspace import get_3dview_space
from .. utils.gizmo import hide_gizmos, restore_gizmos
from .. utils.mesh import get_coords, unhide_deselect
from .. utils.bmesh import ensure_custom_data_layers, ensure_gizmo_layers
from .. utils.view import ensure_visibility, get_location_2d
from .. utils.select import get_edges_vert_sequences
from .. utils.tools import active_tool_is_hypercursor
from .. utils.operator import Settings
from .. utils.system import printd
from .. items import alt
from .. colors import yellow, red, white, green, blue, normal, grey, orange

meshmachine = None

def get_boolean_dict(parent, booleans):
    boolean_dict = {}

    for mod in booleans:
        boolean_dict[mod.name] = {'parent': parent,

                                  'object': mod.object,
                                  'isvisible': mod.object.visible_get(),

                                  'index': [mod for mod in parent.modifiers].index(mod),
                                  'operation': mod.operation,
                                  'solver': mod.solver,

                                  'use_self': mod.use_self,
                                  'use_hole_tolerant': mod.use_hole_tolerant,
                                  'double_threshold': mod.double_threshold,

                                  'show_in_editmode': mod.show_in_editmode,
                                  'show_viewport': mod.show_viewport,
                                  'show_render': mod.show_render}

    return boolean_dict

def get_snapping_dict(ts):
    snapping_dict = {'snap_elements': str(ts.snap_elements),
                     'snap_target': ts.snap_target,

                     'use_snap_backface_culling': ts.use_snap_backface_culling,
                     'use_snap_align_rotation': ts.use_snap_align_rotation,
                     'use_snap_peel_object': ts.use_snap_peel_object,
                     'use_snap_grid_absolute': ts.use_snap_grid_absolute,

                     'use_snap_translate': ts.use_snap_translate,
                     'use_snap_rotate': ts.use_snap_rotate,
                     'use_snap_scale': ts.use_snap_scale}

    if bpy.app.version < (4, 0, 0):
        snapping_dict['use_snap_project'] = ts.use_snap_project

    return snapping_dict

def setup_surface_snapping(ts):
    ts.snap_elements = {'FACE'}
    ts.snap_target = 'MEDIAN'

    ts.use_snap_backface_culling = False
    ts.use_snap_align_rotation = True
    ts.use_snap_peel_object = False

    ts.use_snap_translate = True
    ts.use_snap_rotate = False
    ts.use_snap_scale = False

    if bpy.app.version < (4, 0, 0):
        ts.use_snap_project = False

class RemoveBooleanFromParent(bpy.types.Operator):
    bl_idname = "machin3.remove_boolean_from_parent"
    bl_label = "MACHIN3: Remove Boolean from Parent"
    bl_description = "Remove Boolean Modifiers, before moving the object, so it can be surface snapped"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object

            if active and active.parent:
                booleans = [mod for mod in active.parent.modifiers if mod.type == 'BOOLEAN' and mod.object == active]
                return booleans

    def execute(self, context):
        scene = context.scene
        ts = scene.tool_settings

        active = context.active_object
        parent_obj = active.parent

        booleans = [mod for mod in parent_obj.modifiers if mod.type == 'BOOLEAN' and mod.object in [active, *active.children_recursive]]

        boolean_dict = get_boolean_dict(parent_obj, booleans)

        active.HC['booleans'] = boolean_dict

        for mod in booleans:
            remove_mod(mod)

        snapping_dict = get_snapping_dict(ts)

        active.HC['snapping'] = snapping_dict

        setup_surface_snapping(ts)

        return {'FINISHED'}

class RestoreBooleanOnParent(bpy.types.Operator):
    bl_idname = "machin3.restore_boolean_on_parent"
    bl_label = "MACHIN3: Restore Boolean on Parent"
    bl_description = "Restore Boolean Modifiers, after the object has been moved"
    bl_options = {'INTERNAL'}

    duplicate: BoolProperty()

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.active_object

    def execute(self, context):
        scene = context.scene
        ts = scene.tool_settings

        active = context.active_object
        parent_obj = active.parent

        has_parent_changed = False

        if context.visible_objects:
            dg = context.evaluated_depsgraph_get()

            targets = [obj for obj in context.visible_objects if obj.type == 'MESH' and obj != active and obj not in active.children_recursive]
            origin = active.matrix_world.to_translation()

            closest, _, _, _, _, _ = get_closest(dg, targets=targets, origin=origin, debug=False)

            if closest and closest != parent_obj:
                parent_obj = closest
                has_parent_changed = True

        if parent_obj and active.HC.get('booleans'):
            boolean_dict = active.HC.get('booleans').to_dict()

            for name, moddata in boolean_dict.items():
                mod = add_boolean(parent_obj, moddata['object'], method=moddata['operation'], solver=moddata['solver'])
                mod.name = name

                mod.use_self = moddata['use_self']
                mod.use_hole_tolerant = moddata['use_hole_tolerant']
                mod.double_threshold = moddata['double_threshold']

                mod.show_in_editmode = moddata['show_in_editmode']
                mod.show_viewport = moddata['show_viewport']
                mod.show_render = moddata['show_render']

                if has_parent_changed:
                    sort_modifiers(parent_obj)

                else:
                    index = moddata['index']

                    if self.duplicate:
                        index += len(boolean_dict)

                    move_mod(mod, index)

            del active.HC['booleans']

            snapping_dict = active.HC.get('snapping').to_dict()

            for name, snapdata in snapping_dict.items():
                if name == 'snap_elements':
                    ts.snap_elements = eval(snapdata)
                else:
                    setattr(ts, name, snapdata)

            del active.HC['snapping']

            if has_parent_changed:
                parent(active, parent_obj)

        return {'FINISHED'}

class DuplicateBooleanOperator(bpy.types.Operator):
    bl_idname = "machin3.duplicate_boolean_operator"
    bl_label = "MACHIN3: Duplicate Boolean Operator"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object

            if active and active.parent and active_tool_is_hypercursor(context):
                booleans = [mod for mod in active.parent.modifiers if mod.type == 'BOOLEAN' and mod.object == active]
                return booleans

    def execute(self, context):
        view = context.space_data
        scene = context.scene
        ts = scene.tool_settings

        active = context.active_object
        parent = active.parent

        booleans = [mod for mod in parent.modifiers if mod.type == 'BOOLEAN' and mod.object in [active, *active.children_recursive]]

        boolean_dict = get_boolean_dict(parent, booleans)

        snapping_dict = get_snapping_dict(ts)

        for obj in active.children_recursive:
            if obj.name in context.view_layer.objects:

                if view.local_view and not obj.local_view_get(view):
                    obj.local_view_set(view, True)

                if not obj.visible_get():
                    obj.hide_set(False)

                obj.select_set(True)

        sel1 = context.selected_objects
        bpy.ops.object.duplicate()
        sel2 = context.selected_objects

        dupmap = {obj1: obj2 for obj1, obj2 in zip(sel1, sel2)}

        for moddata in boolean_dict.values():
            obj = moddata['object']
            moddata['object'] = dupmap[obj]

            if not moddata['isvisible'] and obj.name in context.view_layer.objects:
                obj.hide_set(True)
                dupmap[obj].hide_set(True)

        active = context.active_object

        for obj in active.children_recursive:
            if obj.name in context.view_layer.objects:
                obj.select_set(False)

        active.HC['booleans'] = boolean_dict
        active.HC['snapping'] = snapping_dict

        setup_surface_snapping(ts)

        return {'FINISHED'}

def draw_hyper_mod_status(op):
    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)

        mode = op.mode

        mod = op.mod
        show_mod = mod.show_viewport
        modobj = get_mod_obj(mod)
        prefix = get_prefix_from_mod(mod)

        mods = list(op.active.modifiers)
        modobjs = [mod for mod in mods if mod.type == 'BOOLEAN' and get_mod_obj(mod)]
        modidx = mods.index(mod)

        is_moving = op.is_moving

        is_d = op.is_d
        is_adjusting = op.is_adjusting

        action = "Add" if mode == 'ADD' else "Move" if is_moving else "Enable" if is_d and show_mod else "Disable" if is_d and not show_mod else "Adjust" if is_adjusting else "Pick"
        row.label(text=f"{action} Modifier")

        if is_adjusting:
            row.separator(factor=10)
            row.label(text=mod.name)

            if mod.type == 'SUBSURF':
                row.separator(factor=2)

                row.label(text="", icon='EVENT_T')
                row.label(text=f"Levels: {mod.levels}")

                r = row.row()
                r.active = not op.subd_affect_render
                r.label(text=f"Render: {mod.levels}")

                row.separator(factor=2)
                row.label(text="", icon='EVENT_B')
                row.label(text=f"Affet Both, Levels + Render Levels: {op.subd_affect_render}")

            else:
                row.separator(factor=2)

                row.label(text="", icon='EVENT_SHIFT')
                row.label(text="", icon='EVENT_CTRL')
                row.label(text=f"Precision: {'fine' if op.is_shift else 'coarse' if op.is_ctrl else 'normal'}")

                precision = 2 if op.is_shift else 0 if op.is_ctrl else 1

                row.separator(factor=2)

                if mod.type == 'WELD':
                    row.label(text="", icon='EVENT_T')
                    row.label(text=f"Threshold: {dynamic_format(mod.merge_threshold, decimal_offset=precision)}")

                elif mod.type == 'DISPLACE':
                    row.label(text="", icon='EVENT_T')
                    row.label(text=f"Strength: {dynamic_format(mod.strength, decimal_offset=precision)}")

                elif mod.type == 'SOLIDIFY':
                    row.label(text="", icon='EVENT_T')
                    row.label(text=f"Thickness: {dynamic_format(mod.thickness, decimal_offset=precision)}")

                elif is_auto_smooth(mod):
                    angle = degrees(get_mod_input(mod, 'Angle'))
                    row.label(text="", icon='EVENT_T')
                    row.label(text=f"Angle: {dynamic_format(angle, decimal_offset=precision)}")

        else:

            if mode == 'ADD' and len(mods) > len(op.cancel_remove_mods):
                row.label(text="", icon='MOUSE_LMB')
                row.label(text="Continue in Pick mode")

                row.label(text="", icon='EVENT_SPACEKEY')
                row.label(text="Finish")

            else:
                row.label(text="", icon='MOUSE_LMB')
                row.label(text="Finish")

            row.label(text="", icon='MOUSE_RMB')
            row.label(text="Cancel")

            row.separator(factor=10)

            if not is_moving:
                row.separator(factor=2)

                row.label(text="", icon='EVENT_ALT')
                row.label(text=f"Move Modifier")

            row.label(text="", icon='MOUSE_MMB')
            row.label(text=f"Adjust {'Position' if mode == 'ADD' or is_moving else 'Selection'} in Stack")

            if mode == 'ADD':
                row.separator(factor=2)

                row.label(text="", icon='EVENT_Q')
                row.label(text=f"Use Prefix")

                row.separator(factor=4)

                row.label(text=f"Add: ")

                if mod.type == 'WELD':
                    row.label(text="", icon='EVENT_D')
                    row.label(text=f"Displace")

                    row.label(text="", icon='EVENT_S')
                    row.label(text=f"Shell")

                elif mod.type == 'DISPLACE':
                    row.label(text="", icon='EVENT_W')
                    row.label(text=f"Weld")

                    row.label(text="", icon='EVENT_S')
                    row.label(text=f"Shell")

                elif mod.type == 'SOLIDIFY':
                    row.label(text="", icon='EVENT_W')
                    row.label(text=f"Weld")

                    row.label(text="", icon='EVENT_D')
                    row.label(text=f"Displace")

                    row.label(text="", icon='EVENT_S')
                    row.label(text=f"Preceding SubDs: {bool(op.preceding_mods and len(op.preceding_mods) == 2)}")

                    if modidx > 0:
                        row.label(text="", icon='EVENT_SHIFT')
                        row.label(text="", icon='EVENT_W')
                        row.label(text=f"Preceding Weld: {bool(op.preceding_mods and len(op.preceding_mods) == 1)}")

                row.separator(factor=4)
                row.label(text=f"Jump to")

                row.label(text="", icon='EVENT_G')
                row.label(text=f"Top in Stack")

                row.separator(factor=1)

                row.label(text="", icon='EVENT_SHIFT')
                row.label(text="", icon='EVENT_G')
                row.label(text=f"Bottom in Stack")

            if mode == 'PICK':
                row.separator(factor=2)

                row.label(text="", icon='EVENT_Q')
                row.label(text=f"Cycle Prefix")

                if prefix:
                    row.separator(factor=2)

                    row.label(text="", icon='EVENT_SHIFT')
                    row.label(text="", icon='EVENT_Q')
                    row.label(text=f"Remove Prefix")

                if not is_d:
                    row.separator(factor=2)

                    row.label(text="", icon='EVENT_D')
                    action = 'Disable' if show_mod else 'Enable'
                    row.label(text=f"{action}")

                row.separator(factor=2)

                row.label(text="", icon='EVENT_A')
                action = 'Disable All' if mods[0].show_viewport else 'Enable All'
                row.label(text=action)

                if modobjs:
                    row.separator(factor=1)

                    action = "Hide/Unhide All Mod Objs"
                    row.label(text="", icon='EVENT_SHIFT')
                    row.label(text="", icon='EVENT_A')
                    row.label(text=action)

                if op.can_apply_mods:
                    row.separator(factor=1)
                    row.label(text="", icon='EVENT_CTRL')
                    row.label(text="", icon='EVENT_A')

                    text = "Apply All (visible) Mods"
                    if not op.has_disabled_mods:
                        text += ' + Finish'
                    row.label(text=text)

                row.separator(factor=2)

                row.label(text="", icon='EVENT_X')
                action = 'Un-Delete' if mod in op.deleted else 'Delete'
                row.label(text=action)

                if (mod.type == 'BOOLEAN' or is_radial_array(mod)) and modobj:
                    row.separator(factor=2)

                    row.label(text="", icon='EVENT_S')
                    row.label(text=f"Select Mod Object")

                    row.separator(factor=1)

                    row.label(text="", icon='EVENT_SHIFT')
                    row.label(text="", icon='EVENT_S')
                    row.label(text=f"Select Mod Object (keep existing selection)")

                    row.separator(factor=2)

                    row.label(text="", icon='EVENT_F')
                    row.label(text=f"Focus on Mod Object")

                    row.separator(factor=1)

                    row.label(text="", icon='EVENT_SHIFT')
                    row.label(text="", icon='EVENT_F')
                    row.label(text=f"Focus on Active Object")

                if (smooth := is_auto_smooth(mod)) or mod.type in ['WELD', 'DISPLACE', 'SOLIDIFY', 'BOOLEAN', 'SUBSURF']:
                    modtype = 'Auto Smooth' if smooth else mod.type.title().replace('Solidify', 'Shell')

                    row.separator(factor=4)
                    row.label(text=f"{modtype} Properties:")

                    if mod.type == 'WELD':
                        row.label(text="", icon='EVENT_C')
                        row.label(text=f"Mode: {mod.mode.title()}")

                        row.separator(factor=1)

                        row.label(text="", icon='EVENT_T')
                        row.label(text=f"Threshold: {dynamic_format(mod.merge_threshold)}")

                    elif mod.type == 'DISPLACE':
                        row.label(text="", icon='EVENT_T')
                        row.label(text=f"Srength: {dynamic_format(mod.strength)}")

                    elif mod.type == 'SOLIDIFY':
                        row.label(text="", icon='EVENT_E')
                        row.label(text=f"Even: {mod.use_even_offset}")

                        row.separator(factor=1)

                        row.label(text="", icon='EVENT_T')
                        row.label(text=f"Thickness: {dynamic_format(mod.thickness)}")

                    elif mod.type == 'BOOLEAN':
                        row.label(text="", icon='EVENT_E')
                        solver = mod.solver.title()

                        if mod.use_self:
                            solver += " + Self Intersection"

                        if mod.use_hole_tolerant:
                            solver += " + Hole Tolerant"

                        row.label(text=f"Solver: {solver}")

                        if 'Hyper Bevel' in mod.name:
                            row.separator(factor=1)
                            row.label(text="", icon='EVENT_ALT')
                            row.label(text="", icon='EVENT_E')
                            row.label(text=f"Extend")

                    elif mod.type == 'SUBSURF':
                        row.label(text="", icon='EVENT_T')
                        row.label(text=f"Levels: {mod.levels}")

                        r = row.row()
                        r.separator(factor=1)
                        r.active =False
                        r.label(text=f"Render: {mod.render_levels}")

                    elif is_auto_smooth(mod):
                        angle = degrees(get_mod_input(mod, 'Angle'))
                        row.label(text="", icon='EVENT_T')
                        row.label(text=f"Angle: {dynamic_format(angle, decimal_offset=1)}")

                if op.can_tab_finish:

                    if is_edge_bevel(mod):
                        action = "Edit Edge Bevel"

                    elif 'Hyper Bevel' in mod.name:
                        action = "Edit Hyper Bevel"

                    elif mod.type == 'BOOLEAN':
                        action = "Pick Object Tree"

                    elif mod.type == 'SOLIDIFY':
                        action = "Adjust Shell"

                    elif mod.type == 'DISPLACE':
                        action = "Adjust Displace"

                    elif is_array(mod):
                        action = "Adjust Array"

                    row.separator(factor=2)
                    row.label(text="", icon='EVENT_TAB')
                    row.label(text=f"Switch to {action}")

    return draw

class HyperMod(bpy.types.Operator, Settings):
    bl_idname = "machin3.hyper_modifier"
    bl_label = "MACHIN3: Hyper Mod"
    bl_options = {'REGISTER', 'UNDO'}

    mode: StringProperty(name="Mode", default='ADD')
    is_moving: BoolProperty(name="Move the picked Modifier", default=False)
    is_double_subd: BoolProperty(name="Add Double SubD before Shell mod", default=False)
    subd_affect_render: BoolProperty(name="Affect Render Levels too", default=True)
    is_gizmo_invokation: BoolProperty(name="is Gizmo invoke", default=False)
    passthrough = None

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            active = context.active_object
            return active and active.type == 'MESH' and active.select_get() and active.HC.ishyper

    @classmethod
    def description(cls, context, properties):
        desc = "Pick any modifier, and Move it to a different place in the stack"

        desc += "\n\nSHIFT: Add Weld/Solidify/Displace Modifier at specifiic place in the stack"

        desc += "\n\nALT: Pick HyperBevel"
        desc += "\nShortcut: ALT + B"

        desc += "\n\nCTRL: Pick Wire/Bounds/Empty Object in Object Tree"
        desc += "\nShortcut: ALT + S"

        desc += "\n\nALT + CTRL: Look for and remove unused Boolean Modifiers and their Mod Objects"
        return desc

    def draw_HUD(self, context):
        if context.area == self.area:
            scale = get_scale(context)

            mode = self.mode

            mod = self.mod
            show_mod = mod.show_viewport
            modobj = get_mod_obj(mod)
            prefix = get_prefix_from_mod(mod)

            mods = self.active.modifiers
            modobjs = [mod for mod in mods if mod.type == 'BOOLEAN' and get_mod_obj(mod)]

            is_moving = self.is_moving

            is_d = self.is_d
            is_adjusting = self.is_adjusting

            self.offset = self.get_compensated_offset(context)

            action = "Add" if mode == 'ADD' else "Move" if is_moving else "Enable" if is_d and show_mod else "Disable" if is_d and not show_mod else "Adjust" if is_adjusting else "Pick"
            action_color = green if mode == 'ADD' else yellow if is_moving else white if is_d and show_mod else grey if is_d and not show_mod else orange if is_adjusting else blue

            dims = draw_label(context, title=action, coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=action_color)
            dims2 = draw_label(context, title=" Modifier: ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white)
            dims3 = draw_label(context, title=f"{mod.name} ", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=action_color)

            if mode == 'ADD' and mod.type == 'SOLIDIFY' and self.preceding_mods:
                title = '+ Weld' if len(self.preceding_mods) == 1 else '+ Double SubD'
                draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, size=10, color=action_color)

            elif mod in self.deleted:
                dims4 = draw_label(context, title="to be deleted", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, size=10, color=red)

            elif not show_mod:
                dims4 = draw_label(context, title="disabled (viewport)", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, size=10, color=white, alpha=0.2)

            else:
                dims4 = (0, 0)

            if (mod.type == 'BOOLEAN' and not modobj) or (is_edge_bevel(mod) and mod not in self.batches):
                draw_label(context, title="INVALID", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + dims4[0], self.HUD_y)), offset=self.offset, center=False, size=10, color=red, alpha=1)

            if mod.type == 'WELD':
                precision = 1

                if is_adjusting and (self.is_shift or self.is_ctrl):
                    title = "a little" if self.is_shift else "a lot"
                    draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, size=10, center=False, alpha=0.5)

                    if self.is_shift:
                        precision += 1
                    else:
                        precision -= 1

                self.offset += 18

                dims = draw_label(context, title="Threshold: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, alpha=0.5)
                dims2 = draw_label(context, title=f"{dynamic_format(mod.merge_threshold, decimal_offset=precision)} ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=yellow if is_adjusting else white)

                if not is_adjusting:
                    draw_label(context, title=mod.mode.title(), coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=yellow)

            elif mod.type == 'DISPLACE':
                precision = 1

                if is_adjusting and (self.is_shift or self.is_ctrl):
                    title = "a little" if self.is_shift else "a lot"
                    draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, size=10, center=False, alpha=0.5)

                    if self.is_shift:
                        precision += 1
                    else:
                        precision -= 1

                self.offset += 18

                dims = draw_label(context, title="Strength: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, alpha=0.5)
                dims2 = draw_label(context, title=f"{dynamic_format(mod.strength, decimal_offset=precision)} ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=yellow if self.is_t else white)

            elif mod.type == 'SOLIDIFY':
                precision = 1

                if is_adjusting and (self.is_shift or self.is_ctrl):
                    title = "a little" if self.is_shift else "a lot"
                    draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, size=10, center=False, alpha=0.5)

                    if self.is_shift:
                        precision += 1
                    else:
                        precision -= 1

                self.offset += 18

                dims = draw_label(context, title="Thickness: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, alpha=0.5)
                dims2 = draw_label(context, title=f"{dynamic_format(mod.thickness, decimal_offset=precision)} ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=yellow if is_adjusting else white)

                if mod.use_even_offset and not is_adjusting:
                    draw_label(context, title="Even", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, color=blue)

            elif mod.type == 'BOOLEAN':
                self.offset += 18

                op = mod.operation
                solver = mod.solver

                dims = draw_label(context, title=f"{solver.title()} ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, alpha=1)

                color = blue if op == 'UNION' else red if op == 'DIFFERENCE' else normal
                draw_label(context, title=mod.operation.title(), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=color, alpha=1)

                if solver == 'EXACT' and (mod.use_self or mod.use_hole_tolerant):
                    self.offset += 18

                    title = "Self Intersection" if mod.use_self else "Hole Tolerant"

                    if mod.use_self and mod.use_hole_tolerant:
                        title += " + Hole Tolerant"

                    draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow)

            elif mod.type == 'SUBSURF':
                self.offset += 18

                dims = draw_label(context, title="Levels: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, alpha=0.5)
                dims2 = draw_label(context, title=f"{mod.levels} ", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=orange if is_adjusting else white, alpha=1)

                if is_adjusting:
                    dims3 = draw_label(context, title="Render: ", coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, alpha=0.5)
                else:
                    dims3 = (0, 0)

                dims4 = draw_label(context, title=f"{mod.render_levels} ", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, color=orange if is_adjusting and self.subd_affect_render else white, alpha=0.5)

                if is_adjusting:
                    if self.subd_affect_render:
                        draw_label(context, title="Affect Both", coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + dims4[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)
                else:
                    subd_type = mod.subdivision_type.title().replace('_', '-')
                    draw_label(context, title=subd_type, coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0] + dims4[0], self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

            elif is_auto_smooth(mod):
                precision = 1

                if is_adjusting and (self.is_shift or self.is_ctrl):
                    title = "a little" if self.is_shift else "a lot"
                    draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, size=10, center=False, alpha=0.5)

                    if self.is_shift:
                        precision += 1

                    elif self.is_ctrl:
                        precision -= 1

                self.offset += 18

                angle = degrees(get_mod_input(mod, 'Angle'))

                if angle is not None:
                    dims = draw_label(context, title="Angle: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, alpha=0.5)
                    dims2 = draw_label(context, title=f"{dynamic_format(angle, decimal_offset=precision)}°", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=yellow if self.is_t else white)

                else:
                    draw_label(context, title="INVALID", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=red, alpha=1)

            if self.warn_indices:
                self.offset += 6

            if self.has_multiple_solidify:
                self.offset += 18
                draw_label(context, title="Multiple SOLIDIFY mods in the stack!", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=red)

            if self.has_multiple_displace:
                self.offset += 18
                draw_label(context, title="Multiple DISPLACE mods in the stack!", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=red)

            if is_adjusting:
                return

            ref_idx, ref_type = self.get_reference_mod_index_from_prefix()

            self.offset += 24

            dims = draw_label(context, title="Stack: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

            for idx, mod in enumerate(mods):
                is_sel = mod == self.mod
                is_profile_bevel = is_edge_bevel(mod) and mod.profile_type == 'CUSTOM'

                if idx:
                    self.offset += 18

                if is_sel:
                    size, color, alpha = (12, action_color, 1)

                    if len(mods) > 1:
                        coords = [Vector((self.HUD_x + dims[0] - (5 * scale), self.HUD_y - (self.offset * scale), 0)), Vector((self.HUD_x + dims[0] - (5 * scale), self.HUD_y - (self.offset * scale) + (10 * scale), 0))]
                        draw_line(coords, color=red if mod in self.deleted else action_color, width=2 * scale, screen=True)

                elif idx == ref_idx:
                    size, color, alpha = (10, action_color, 0.6 if is_moving else 0.4)

                else:
                    size, color, alpha = (10, white, 0.4)

                dims2 = draw_label(context, title=mod.name, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, size=size, color=red if mod in self.deleted else color, alpha=0.5 if mod in self.deleted else alpha if mod.show_viewport else 0.15)

                if is_profile_bevel:
                    dims3 = draw_label(context, title=" 🌠" , coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, size=size, color=blue, alpha=alpha)

                else:
                    if idx in self.warn_indices:
                        dims3 = draw_label(context, title=" *" , coords=Vector((self.HUD_x + dims[0] + dims2[0], self.HUD_y)), offset=self.offset, center=False, size=size, color=red, alpha=1)
                    else:
                        dims3 = (0, 0)

                if is_sel and ref_type:
                    draw_label(context, title=ref_type , coords=Vector((self.HUD_x + dims[0] + dims2[0] + dims3[0], self.HUD_y)), offset=self.offset, center=False, size=10, color=white, alpha=1 if self.is_moving else 0.3)

            if (is_radial_array(self.mod) or self.mod.type == 'MIRROR') and self.mod in self.batches:
                if not self.passthrough:
                    batch = self.batches[self.mod]

                    if len(batch) == 5:
                        _, co2d, _, _, hud_scale = self.batches[self.mod]
                        color  = red if self.mod in self.deleted else yellow if self.is_moving else blue

                        draw_circle(co2d, radius=10 * hud_scale, width=2 * hud_scale, color=color, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            if self.mode == 'PICK' and self.mod in self.batches:

                if self.mod.type == 'BOOLEAN':
                    batch = self.batches[self.mod]
                    color  = red if self.mod in self.deleted else yellow if self.is_moving else blue

                    draw_mesh_wire(batch, color=color, width=1, alpha=0.2, xray=True)

                    if self.mod.show_viewport:
                        draw_mesh_wire(batch, color=color, width=1, alpha=1, xray=False)

                elif self.mod.type == 'BEVEL':
                    color  = red if self.mod in self.deleted else yellow if self.is_moving else blue

                    for coords in self.batches[self.mod]:
                        draw_line(coords, width=2, color=color, alpha=0.5, xray=True)  

                        if self.mod.show_viewport:
                            draw_line(coords, width=3, color=color, alpha=1, xray=False)

                elif is_radial_array(self.mod) or self.mod.type == 'MIRROR':
                    batch = self.batches[self.mod]
                    color  = red if self.mod in self.deleted else yellow if self.is_moving else blue

                    if len(batch) == 5:
                        co, _, mx, zoom_factor, hud_scale = self.batches[self.mod]

                        if self.passthrough:
                            draw_point(co, color=color, size=3)

                        else:

                            draw_cross_3d(Vector(), mx=mx, color=color, width=2 * hud_scale, length=3 * zoom_factor * hud_scale, alpha=1, xray=True)

                    elif len(batch) == 2:
                        draw_mesh_wire(batch, color=color, width=1, alpha=0.2, xray=True)

                        if self.mod.show_viewport:
                            draw_mesh_wire(batch, color=color, width=1, alpha=1, xray=False)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        if self.is_tab_locked:
            if event.type == 'TAB' and event.value == 'RELEASE':
                self.is_tab_locked = False
                self.check_tab_finish()

        if self.is_alt_locked:
            if event.type in alt and event.value == 'PRESS':
                self.is_alt_locked = False

        if event.type == 'MOUSEMOVE':
            get_mouse_pos(self, context, event)

            if self.passthrough:
                self.passthrough = False

                self.factor = get_zoom_factor(context, depth_location=self.loc, scale=1, ignore_obj_scale=False)

                for mod, batch in self.batches.items():
                    if is_radial_array(mod) or mod.type == 'MIRROR':
                        if len(batch) == 5:
                            co, _, mx, _, hud_scale = batch

                            zoom_factor = get_zoom_factor(context, depth_location=co, scale=10, ignore_obj_scale=True)
                            co2d = get_location_2d(context, co, default='OFF_SCREEN')
                            self.batches[mod] = (co, co2d, mx, zoom_factor, hud_scale)

        if self.mode == 'PICK' and not self.is_alt_locked:
            self.is_moving = event.alt

        if event.type in [*alt, 'D', 'T']:
            force_ui_update(context, self.active)

        if self.is_adjusting:
            wrap_mouse(self, context, x=True)

            self.is_shift = event.shift
            self.is_ctrl = event.ctrl

            delta_x = self.mouse_pos.x - self.last_mouse.x

            if self.mod.type == 'WELD':
                divisor = get_mousemove_divisor(event, sensitivity=1000)
                self.mod.merge_threshold += delta_x / divisor

            elif self.mod.type == 'SOLIDIFY':
                divisor = get_mousemove_divisor(event, normal=1, shift=20, ctrl=0.1, sensitivity=1)

                self.mod.thickness += delta_x * (self.factor / divisor)

            elif self.mod.type == 'DISPLACE':
                divisor = get_mousemove_divisor(event, normal=1, shift=20, ctrl=0.1, sensitivity=1)

                self.mod.strength -= delta_x * (self.factor / divisor)

            elif self.mod.type == 'SUBSURF':

                if event.type in ['B', 'R'] and event.value == 'PRESS':
                    self.subd_affect_render = not self.subd_affect_render
                    force_ui_update(context)

                divisor = get_mousemove_divisor(event, normal=1, shift=1, ctrl=1, sensitivity=0.05)  # we use this, even though mod keys have no effect, becuase it considers the ui scaling

                self.subd_levels += delta_x * (self.factor / divisor)
                self.subd_levels = max(self.subd_levels, 0)

                self.mod.levels = round(self.subd_levels)

                if self.subd_affect_render:
                    self.mod.render_levels = self.mod.levels

            elif is_auto_smooth(self.mod):
                angle = degrees(get_mod_input(self.mod, 'Angle'))

                if angle:
                    divisor = get_mousemove_divisor(event, normal=1, shift=5, ctrl=0.5, sensitivity=30)
                    set_mod_input(self.mod, 'Angle', radians(angle + (delta_x / divisor)))
                    self.active.update_tag()

        else:

            events = ['Q', 'G']

            if self.mode == 'ADD':

                if self.mod.type == 'WELD':
                    events.extend(['D', 'S'])

                elif self.mod.type == 'DISPLACE':
                    events.extend(['W', 'S'])

                elif self.mod.type == 'SOLIDIFY':
                    events.extend(['W', 'D', 'S'])

            elif self.mode == 'PICK':

                events.extend(['A', 'D', 'X', 'F', 'S'])

                if self.can_tab_finish:
                    events.append('TAB')

                if self.mod.type == 'WELD':
                    events.extend(['C'])

                elif self.mod.type == 'SOLIDIFY':
                    events.extend(['E'])

                elif self.mod.type == 'BOOLEAN':
                    events.extend(['E'])

            if event.type in events or scroll_up(event, key=True) or scroll_down(event, key=True):
                mods, mods_len, current_idx = self.get_mods_and_indices(debug=False)

                if mods_len > 1 and (scroll_up(event, key=True) or scroll_down(event, key=True) or (event.type == 'G' and event.value == 'PRESS')):

                    if self.mode == 'ADD':
                        self.remove_preceeding_mods()

                        mods, mods_len, current_idx = self.get_mods_and_indices(debug=False)

                    if scroll_up(event, key=True):
                        new_index = current_idx - 1

                        if new_index < 0:
                            new_index = mods_len -1

                    elif scroll_down(event, key=True):
                        new_index = current_idx + 1

                        if new_index >= mods_len:
                            new_index = 0

                    elif event.type == 'G':
                        new_index = mods_len - 1 if event.shift else 0

                    if self.is_moving:
                        move_mod(self.mod, index=new_index)

                        self.ensure_prefix()

                    else:
                        self.pick_mod(context, index=new_index)

                        if self.is_d:
                            self.mod.show_viewport = self.visibility_state

                    self.check_multiple_warning(debug=False)

                    self.verify_can_apply_mods()

                elif event.type == 'Q' and event.value == 'PRESS':
                    prefix = get_prefix_from_mod(self.mod)

                    if self.is_moving:
                        if prefix == '+':
                            self.mod.name = f"{'-'} {self.modname}"

                        elif prefix == '-':
                            self.mod.name = f"{'+'} {self.modname}"

                        if self.mode == 'ADD':
                            self.remove_preceeding_mods()

                        self.ensure_prefix()

                        if self.mode == 'ADD' and prefix:
                            self.mod.name = get_mod_base_name(self.mod)

                    else:
                        if prefix:

                            if event.shift or self.mode == 'ADD':
                                self.mod.name = get_mod_base_name(self.mod)

                            else:
                                if prefix == '+':
                                    self.mod.name = f"{'-'} {self.modname}"

                                elif prefix == '-':
                                    self.mod.name = get_mod_base_name(self.mod)

                        elif not event.shift:
                            self.mod.name = f"{'+'} {self.modname}"

                if self.mod.type == 'WELD':

                    if event.type in ['C'] and event.value == 'PRESS':
                        
                        if self.mod.mode == 'ALL':
                            self.mod.mode = 'CONNECTED'

                        elif self.mod.mode == 'CONNECTED':
                            self.mod.mode = 'ALL'

                    if self.mode == 'ADD':

                        if event.type in ['D'] and event.value == 'PRESS':

                            self.add_mod(modtype='DISPLACE')

                        elif event.type in ['S'] and event.value == 'PRESS':

                            self.add_mod(modtype='SOLIDIFY')

                elif self.mod.type == 'DISPLACE':

                    if self.mode == 'ADD':

                        if event.type in ['W'] and event.value == 'PRESS':

                            self.add_mod(modtype='WELD')

                        elif event.type in ['S'] and event.value == 'PRESS':

                            self.add_mod(modtype='SOLIDIFY')

                elif self.mod.type == 'SOLIDIFY':

                    if event.type in ['E'] and event.value == 'PRESS':
                        self.mod.use_even_offset = not self.mod.use_even_offset

                    if self.mode == 'ADD':

                        if event.type in ['S'] and event.value == 'PRESS':

                            if self.preceding_mods:

                                if len(self.preceding_mods) == 1:
                                    self.remove_preceeding_mods()

                                    current_idx = list(self.active.modifiers).index(self.mod)

                                elif len(self.preceding_mods) == 2:
                                    self.remove_preceeding_mods()
                                    return {'RUNNING_MODAL'}

                            self.preceding_mods = self.add_double_subd(current_idx)

                        elif event.type in ['W'] and event.value == 'PRESS':

                            if event.shift:

                                if self.preceding_mods:

                                    if len(self.preceding_mods) == 1:
                                        self.remove_preceeding_mods()
                                        return {'RUNNING_MODAL'}

                                    elif len(self.preceding_mods) == 2:
                                        self.remove_preceeding_mods()

                                        current_idx = list(self.active.modifiers).index(self.mod)

                                if current_idx > 0:
                                    modname = get_new_mod_name(self.active, modtype='WELD')
                                    prefix = get_prefix_from_mod(self.mod)

                                    if prefix:
                                        modname = f"{prefix} {modname}"

                                    self.preceding_mods = add_weld(self.active, name=modname), 

                                    for mod in self.preceding_mods:
                                        move_mod(mod, current_idx)

                                    self.cancel_remove_mods.update(self.preceding_mods)

                                self.check_multiple_warning()

                            else:

                                self.add_mod(modtype='WELD')

                        elif event.type in ['D'] and event.value == 'PRESS':

                            self.add_mod(modtype='DISPLACE')

                elif self.mod.type == 'BOOLEAN':

                    if event.type in ['E'] and event.value == 'PRESS':
                        modobj = get_mod_obj(self.mod)

                        if event.alt:
                            if "Hyper Bevel" in self.mod.name and modobj :

                                self.finish(context)
                                self.save_settings()

                                bpy.ops.machin3.extend_hyper_bevel('INVOKE_DEFAULT', objname=modobj.name, modname=self.mod.name, is_hypermod_invoke=True)

                                return {'FINISHED'}

                        else:
                            modes = ['FAST', 'EXACT', 'EXACT_SELF', 'EXACT_HOLES', 'EXACT_SELF_HOLES']

                            if self.mod.solver == 'FAST':
                                mode = 'FAST'

                            elif self.mod.solver == 'EXACT':
                                if self.mod.use_self and self.mod.use_hole_tolerant:
                                    mode = 'EXACT_SELF_HOLES'

                                elif self.mod.use_self:
                                    mode = 'EXACT_SELF'

                                elif self.mod.use_hole_tolerant:
                                    mode = 'EXACT_HOLES'

                                else:
                                    mode = 'EXACT'

                            if event.shift:
                                next_mode = step_list(mode, modes, step=-1, loop=True)

                            else:
                                next_mode = step_list(mode, modes, step=1, loop=True)

                            if next_mode == 'FAST':
                                self.mod.solver = 'FAST'
                                self.mod.use_self = False
                                self.mod.use_hole_tolerant = False

                            elif next_mode == 'EXACT':
                                self.mod.solver = 'EXACT'
                                self.mod.use_self = False
                                self.mod.use_hole_tolerant = False

                            elif next_mode == 'EXACT_SELF':
                                self.mod.solver = 'EXACT'
                                self.mod.use_self = True
                                self.mod.use_hole_tolerant = False

                            elif next_mode == 'EXACT_HOLES':
                                self.mod.solver = 'EXACT'
                                self.mod.use_self = False
                                self.mod.use_hole_tolerant = True

                            elif next_mode == 'EXACT_SELF_HOLES':
                                self.mod.solver = 'EXACT'
                                self.mod.use_self = True
                                self.mod.use_hole_tolerant = True

                if self.mode == 'PICK':

                    if event.type in ['D'] and event.value == 'PRESS' and not self.is_d:

                        if event.shift:
                            mods, _, current_idx = self.get_mods_and_indices()
                            slice = mods[current_idx:]

                            state = not self.mod.show_viewport

                            for mod in slice:

                                if mod not in self.deleted:
                                    mod.show_viewport = state

                        else:
                            if self.mod not in self.deleted:
                                self.mod.show_viewport = not self.mod.show_viewport

                        self.verify_can_apply_mods()

                    elif event.type in ['A'] and event.value == 'PRESS':

                        if self.can_apply_mods and event.ctrl:
                            self.finish(context)
                            self.save_settings()

                            bpy.ops.machin3.apply_all_modifiers(backup=True, duplicate=False)
                            
                            if self.has_disabled_mods:
                                bpy.ops.machin3.hyper_modifier('INVOKE_DEFAULT', is_gizmo_invokation=False, mode='PICK')

                            return {'FINISHED'}

                        else:
                            mods, _, _ = self.get_mods_and_indices()

                            if event.shift:
                                modobjs = [get_mod_obj(mod) for mod in mods if (mod.type == 'BOOLEAN' or is_radial_array(mod)) and get_mod_obj(mod)]

                                if modobjs:

                                    state = modobjs[0].visible_get()

                                    view = context.space_data
                                    
                                    for obj in modobjs:
                                        if view.local_view and not obj.local_view_get(view):
                                            obj.local_view_set(view, True)
                                        
                                        obj.hide_set(state)

                            else:
                                state = not mods[0].show_viewport

                                for mod in mods:
                                    if mod not in self.deleted:
                                        if self.avoid_all_toggling_autosmooth(mod):
                                            continue

                                        mod.show_viewport = state

                            self.verify_can_apply_mods()

                    elif event.type in ['S'] and event.value == 'PRESS':

                        if self.mod.type in ['BOOLEAN', 'MIRROR'] or is_radial_array(self.mod):
                            modobj = get_mod_obj(self.mod)

                            if modobj:
                                self.finish(context)
                                self.save_settings()

                                ensure_visibility(context, modobj)

                                if not event.shift:
                                    bpy.ops.object.select_all(action='DESELECT')

                                modobj.select_set(True)
                                context.view_layer.objects.active = modobj

                                return {'FINISHED'}

                    elif event.type in ['F'] and event.value == 'PRESS':

                        if event.shift:
                            bpy.ops.view3d.view_selected('INVOKE_DEFAULT' if context.scene.HC.focus_mode == 'SOFT' else 'EXEC_DEFAULT')

                        elif self.mod.type in ['BOOLEAN', 'MIRROR'] or is_radial_array(self.mod):
                            modobj = get_mod_obj(self.mod)

                            if modobj:
                                bpy.ops.object.select_all(action='DESELECT')

                                view = context.space_data

                                if view.local_view and not modobj.local_view_get(view):
                                    modobj.local_view_set(view, True)

                                is_hidden = not modobj.visible_get()

                                if is_hidden:
                                    modobj.hide_set(False)

                                modobj.select_set(True)

                                bpy.ops.view3d.view_selected('INVOKE_DEFAULT' if context.scene.HC.focus_mode == 'SOFT' else 'EXEC_DEFAULT')

                                modobj.select_set(False)

                                if is_hidden:
                                    modobj.hide_set(True)

                                self.active.select_set(True)

                        self.passthrough = True
                        return {'RUNNING_MODAL'}

                    elif event.type in ['X'] and event.value == 'PRESS':

                        if event.shift:
                            mods, _, current_idx = self.get_mods_and_indices()
                            slice = mods[current_idx:]

                            state = self.mod in self.deleted

                            for mod in slice:

                                if state and mod in self.deleted:
                                    mod.show_viewport = self.deleted[mod]
                                    del self.deleted[mod]
                                
                                elif not state and mod not in self.deleted:
                                    self.deleted[mod] = mod.show_viewport
                                    mod.show_viewport = False

                        else:

                            if self.mod in self.deleted:
                                self.mod.show_viewport = self.deleted[self.mod]

                                del self.deleted[self.mod]

                            else:

                                self.deleted[self.mod] = self.mod.show_viewport

                                self.mod.show_viewport = False

                        self.verify_can_apply_mods()

                    elif event.type == 'TAB' and event.value == 'PRESS':
                        self.finish(context)
                        self.save_settings()

                        if is_edge_bevel(self.mod):
                            bpy.ops.machin3.bevel_edge('INVOKE_DEFAULT', index=-1, is_hypermod_invoke=True)
                            return {'FINISHED'}

                        elif 'Hyper Bevel' in self.mod.name:
                            bpy.ops.machin3.edit_hyper_bevel('INVOKE_DEFAULT', objname=self.active.name, modname=self.mod.name, is_hypermod_invoke=True)
                            return {'FINISHED'}

                        elif self.mod.type == 'BOOLEAN':
                            bpy.ops.machin3.pick_object_tree('INVOKE_DEFAULT')
                            return {'FINISHED'}

                        elif self.mod.type == 'SOLIDIFY':
                            bpy.ops.machin3.adjust_shell('INVOKE_DEFAULT', is_hypermod_invoke=True)
                            return {'FINISHED'}

                        elif self.mod.type == 'DISPLACE':
                            bpy.ops.machin3.adjust_displace('INVOKE_DEFAULT', is_hypermod_invoke=True)
                            return {'FINISHED'}

                        elif is_array(self.mod):
                            bpy.ops.machin3.adjust_array('INVOKE_DEFAULT', is_hypermod_invoke=True)
                            return {'FINISHED'}

            elif navigation_passthrough(event, alt=False, wheel=False):
                self.passthrough = True
                return {'PASS_THROUGH'}

            elif event.type in ['LEFTMOUSE', 'SPACE'] and event.value == 'PRESS':
                mods, mods_len, _ = self.get_mods_and_indices()

                if mods_len > 1 and event.type == 'LEFTMOUSE' and self.mode == 'ADD':
                    self.mode = 'PICK'

                    self.is_moving = False

                    self.verify_can_apply_mods()

                    self.check_tab_finish()

                    force_ui_update(context)
                    return {'RUNNING_MODAL'}

                else:
                    self.finish(context)
                    self.save_settings()

                    if self.deleted:
                        for mod in self.deleted:
                            if mod.type == 'BEVEL' and mod.vertex_group:
                                vgroup = self.active.vertex_groups.get(mod.vertex_group, None)

                                if vgroup:
                                    self.active.vertex_groups.remove(vgroup)

                            remove_mod(mod)

                    force_obj_gizmo_update(context)
                    return {'FINISHED'}

            elif event.type in ['RIGHTMOUSE', 'ESC'] and event.value == 'PRESS':
                self.finish(context)

                for mod in self.cancel_remove_mods:
                    remove_mod(mod)
                        
                if self.mode == 'PICK':
                    mods = list(self.active.modifiers)

                    for idx, mod in enumerate(mods):
                        init = self.initial[mod]
                        modtype = 'AUTOSMOOTH' if is_auto_smooth(mod) else mod.type

                        if idx != init['index']:
                            move_mod(mod, init['index'])

                        if mod.show_viewport != init['show_viewport']:
                            mod.show_viewport = init['show_viewport']

                        if mod.name != init['name']:
                            mod.name = init['name']

                        if modtype in init:
                            for name, value in init[modtype].items():

                                if mod.type == 'BOOLEAN' and name in ['mod_obj', 'mod_obj_hide']:
                                    if name == 'mod_obj_hide':
                                        continue

                                    modobj = init[mod.type]['mod_obj']
                                    if modobj and modobj.hide_get() != init[mod.type]['mod_obj_hide']:
                                        modobj.hide_set(init[mod.type]['mod_obj_hide'])

                                elif modtype == 'AUTOSMOOTH':
                                    if (angle := get_mod_input(mod, 'Angle')) != init['AUTOSMOOTH']['angle']:
                                        print(f"    {modtype}'s Angle prop has changed from {degrees(angle)} to {degrees(value)}")
                                        set_mod_input(mod, 'Angle', value)

                                elif getattr(mod, name) != value:
                                    setattr(mod, name, value)

                return {'CANCELLED'}

        if self.mode == 'PICK':
            is_key(self, event, 'D', debug=False)
            is_key(self, event, 'T', debug=False)

            if event.type == 'D' and event.value == 'PRESS':
                self.visibility_state = self.mod.show_viewport

            if event.type == 'T' and (self.mod.type in ['WELD', 'SOLIDIFY', 'DISPLACE', 'SUBSURF'] or is_auto_smooth(self.mod)):
                if event.value == 'PRESS' and not self.is_adjusting:   # NOTE: only set it once, by checking for self.is_adjusting (set below)
                    context.window.cursor_set('SCROLL_X')

                elif event.value == 'RELEASE':
                    context.window.cursor_set('DEFAULT')

                if self.mod.type in ['WELD', 'SUBSURF']:
                    if event.value == 'PRESS' and not self.is_adjusting:   # NOTE: only set it once, by checking for self.is_adjusting (set below)
                        self.active.show_wire = True

                        if self.mod.type == 'SUBSURF':
                            self.subd_levels = self.mod.levels
                            self.subd_render_levels = self.mod.render_levels

                    elif event.value == 'RELEASE':
                        self.active.show_wire = False

                if event.value == 'PRESS':
                    self.is_adjusting = True
                elif event.value == 'RELEASE':
                    self.is_adjusting = False

        self.last_mouse = self.mouse_pos

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        
        restore_gizmos(self)

        finish_status(self)

    def invoke(self, context, event):
        if self.is_gizmo_invokation:

            if event.alt and event.ctrl:
                bpy.ops.machin3.remove_unused_booleans('INVOKE_DEFAULT')
                return {'FINISHED'}

            elif event.alt:
                bpy.ops.machin3.pick_hyper_bevel('INVOKE_DEFAULT')
                return {'FINISHED'}

            elif event.ctrl:
                bpy.ops.machin3.pick_object_tree('INVOKE_DEFAULT')
                return {'FINISHED'}

            self.mode = 'ADD' if event.shift else 'PICK'

        self.init_settings(props=['subd_affect_render'])
        self.load_settings()

        self.active = context.active_object
        self.mx = self.active.matrix_world
        self.loc = self.mx.to_translation()

        self.bm = None

        self.mod = None
        self.preceding_mods = None
        self.is_double_subd = False

        self.is_shift = False
        self.is_ctrl = False

        self.is_d = False
        self.is_t = False

        self.is_adjusting = False

        self.is_tab_locked = event.type == 'TAB'
        self.is_alt_locked = not self.is_gizmo_invokation and event.alt

        self.can_tab_finish = False

        self.subd_levels = 0
        self.subd_render_levels = 0

        self.verify_can_apply_mods()

        self.dg = context.evaluated_depsgraph_get()
        self.batches = {}

        self.cancel_remove_mods = set()

        self.initial = self.get_initial_mod_states()

        self.deleted = {}

        if self.mode == 'ADD':
            
            modtype = 'WELD' if self.active.modifiers else 'SOLIDIFY'

            self.add_mod(modtype=modtype, debug=False)

            self.is_moving = True

        elif self.active.modifiers and self.mode == 'PICK':
            self.pick_mod(context)

            force_ui_update(context, active=self.active)

            self.is_moving = False

        else:
            text = [f"No Modifiers on {self.active.name} to pick/move!",
                    f"You can run the tool with the SHIFT key pressed - while clicking on the 🔧 gizmo - to add a modifier!"]

            draw_fading_label(context, text=text, y=120, color=[red, white], alpha=[1, 0.5], move_y=30, time=3)

            return {'CANCELLED'}

        self.factor = get_zoom_factor(context, depth_location=self.loc, scale=1, ignore_obj_scale=False)

        get_mouse_pos(self, context, event)

        self.last_mouse = self.mouse_pos

        hide_gizmos(self, context)

        init_status(self, context, func=draw_hyper_mod_status(self))

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def get_initial_mod_states(self):
        initial = {}
        
        for idx, mod in enumerate(self.active.modifiers):
            initial[mod] = {'index': idx,
                            'name': mod.name,
                            'show_viewport': mod.show_viewport}

            if mod.type in ['WELD', 'SOLIDIFY', 'DISPLACE', 'BOOLEAN'] or (smooth := is_auto_smooth(mod)):

                if mod.type == 'WELD':
                    initial[mod]['WELD'] = {'mode': mod.mode,
                                            'merge_threshold': mod.merge_threshold}

                elif mod.type == 'SOLIDIFY':
                    initial[mod]['SOLIDIFY'] = {'use_even_offset': mod.use_even_offset,
                                                'thickness': mod.thickness}

                elif mod.type == 'DISPLACE':
                    initial[mod]['DISPLACE'] = {'strength': mod.strength,
                                                'mid_level': mod.mid_level}

                elif mod.type == 'BOOLEAN':
                    modobj = get_mod_obj(mod)

                    initial[mod]['BOOLEAN'] = {'solver': mod.solver,
                                               'use_self': mod.use_self,
                                               'use_hole_tolerant': mod.use_hole_tolerant,
                                               'mod_obj': modobj,
                                               'mod_obj_hide': modobj.hide_get() if modobj else None}

                elif smooth:
                    initial[mod]['AUTOSMOOTH'] = {'angle': get_mod_input(mod, 'Angle')}

        return initial

    def verify_can_apply_mods(self):
        self.can_apply_mods = False
        self.has_disabled_mods = False

        if self.mode == 'PICK':
            for mod in self.active.modifiers:
                if mod.show_viewport:
                    self.can_apply_mods = True

                else:
                    self.has_disabled_mods = True

    def get_mods_and_indices(self, debug=False):
        mods = list(self.active.modifiers)
        mods_len = len(mods)

        current_idx = mods.index(self.mod)

        if debug:
            print("current:", current_idx, "of", mods_len - 1)

        return mods, mods_len, current_idx

    def ensure_prefix(self, debug=False):
        mods, mods_len, current_idx = self.get_mods_and_indices(debug=False)

        prefix = get_prefix_from_mod(self.mod)

        next_prefix = None
        prev_prefix = None

        if current_idx > 0:
            prev_mod = mods[current_idx - 1]
            prev_prefix = get_prefix_from_mod(prev_mod)

        if current_idx < mods_len - 1:
            next_mod = mods[current_idx + 1]
            next_prefix = get_prefix_from_mod(next_mod)

        if debug:
            print()
            print("setting prefix for mod:", self.modname, current_idx, "/", mods_len)
            print(" current prefix is:", prefix)
            print("    prev prefix is:", prev_prefix, f"({prev_mod.name if current_idx > 0 else ''})")
            print("    next prefix is:", next_prefix, f"({next_mod.name if current_idx < mods_len - 2 else ''})")
        
        if prefix == '+' and current_idx == 0:
            self.mod.name = f"- {self.modname}"
        
        elif prefix == '-' and current_idx == mods_len - 1:
            self.mod.name = f"+ {self.modname}"

        elif prefix == '+' and prev_prefix == '-':
            if debug:
                print(f"mods {self.mod.name} and {prev_mod.name} reference each other, preventing")

            self.mod.name = f"- {self.modname}"

        elif prefix == '-' and next_prefix == '+':
            if debug:
                print(f"mods {self.mod.name} and {next_mod.name} reference each other, preventing")

            self.mod.name = f"+ {self.modname}"

        elif prefix is None and self.is_moving:
            if debug:
                print()
                print("mod has no prefix!")
                print(" mods_len:", mods_len)
                print(" current idx:", current_idx)

            if current_idx == 0:
                self.mod.name = f"- {self.modname}"

                if debug:
                    print(" added prefix -")

            else:
                self.mod.name = f"+ {self.modname}"
                if debug:
                    print(" added prefix +")

    def populate_batches(self, context):
        if self.mod not in self.batches:

            if self.mod.type == 'BOOLEAN':
                modobj = get_mod_obj(self.mod)

                if modobj:

                    mesh_eval = modobj.evaluated_get(self.dg).data
                    self.batches[self.mod] = get_coords(mesh_eval, mx=modobj.matrix_world, edge_indices=True)

            elif is_edge_bevel(self.mod) and self.mod.vertex_group:
                if self.bm is None:
                    bm = bmesh.new()
                    bm.from_mesh(self.active.data)
                    bm.edges.ensure_lookup_table()

                    vg_layer = ensure_custom_data_layers(bm, vertex_groups=True, bevel_weights=False, crease=False)[0]

                    self.bm = (bm, vg_layer)

                else:
                    bm, vg_layer = self.bm

                vg_index = [vg.name for vg in self.active.vertex_groups].index(self.mod.vertex_group)

                vg_edges, verts = get_edges_from_edge_bevel_mod_vgroup(bm, vg_layer, vg_index, verts_too=True)

                if vg_edges:

                    sequences = get_edges_vert_sequences(verts, vg_edges, debug=False)

                    batch = []

                    for seq, cyclic in sequences:
                        coords = [self.mx @ v.co for v in seq]

                        if cyclic:
                            coords.append(self.mx @ seq[0].co)

                        batch.append(coords)

                    if batch:
                        self.batches[self.mod] = batch

                else:
                    print(f"WARNING: Edge Bevel '{self.mod.name}' is invalid! It's vertex groip does not create a single Edge.")

            elif is_radial_array(self.mod) or self.mod.type == 'MIRROR':
                modobj = get_mod_obj(self.mod)

                if modobj:

                    if modobj.type == 'EMPTY':
                        mx = modobj.matrix_world.copy()
                        co = mx.to_translation()
                        zoom_factor = get_zoom_factor(context, depth_location=co, scale=10, ignore_obj_scale=True)
                        hud_scale = get_scale(context)

                        co2d = get_location_2d(context, co, default='OFF_SCREEN')
                        self.batches[self.mod] = (co, co2d, mx, zoom_factor, hud_scale)

                    elif modobj.type == 'MESH':
                        mesh_eval = modobj.evaluated_get(self.dg).data
                        self.batches[self.mod] = get_coords(mesh_eval, mx=modobj.matrix_world, edge_indices=True)

    def check_multiple_warning(self, debug=False):
        mods, _, _ = self.get_mods_and_indices()

        solidifies = [mod for mod in self.active.modifiers if mod.type == 'SOLIDIFY']
        displaces = [mod for mod in self.active.modifiers if mod.type == 'DISPLACE']

        self.has_multiple_solidify = len(solidifies) > 1
        self.has_multiple_displace = len(displaces) > 1

        self.warn_indices = []

        if self.has_multiple_solidify:
            for mod in solidifies:
                self.warn_indices.append(mods.index(mod))

        if self.has_multiple_displace:
            for mod in displaces:
                self.warn_indices.append(mods.index(mod))

        if debug:
            print()
            print("multiple solidify:", self.has_multiple_solidify)
            print("multiple displace:", self.has_multiple_displace)
            print("       at indices:", self.warn_indices)

    def check_tab_finish(self):
        self.can_tab_finish = False
 
        if self.mode == 'PICK' and not self.is_tab_locked:

            if is_edge_bevel(self.mod) and self.mod in self.batches:
                self.can_tab_finish = True

            elif self.mod.type == 'BOOLEAN' and get_mod_obj(self.mod):
                self.can_tab_finish = True

            elif self.mod.type == 'SOLIDIFY':
                self.can_tab_finish = True

            elif self.mod.type == 'DISPLACE':
                self.can_tab_finish = True

            elif is_hyper_array(self.mod):
                self.can_tab_finish = True

    def get_reference_mod_index_from_prefix(self):
        prefix = get_prefix_from_mod(self.mod)

        if prefix in ['-', '+']:

            mods, mods_len, current_idx = self.get_mods_and_indices(debug=False)

            if prefix == '-':

                if current_idx < mods_len - 1:
                    return current_idx + 1, " 🡷 precedes"

            elif prefix == '+':

                if current_idx > 0:
                    return current_idx - 1, " 🡴 follows"

        return None, None

    def remove_preceeding_mods(self):
        if self.preceding_mods:
            for mod in self.preceding_mods:
                self.cancel_remove_mods.remove(mod)

                remove_mod(mod)

            self.preceding_mods = None

    def avoid_all_toggling_autosmooth(self, mod):
        if bpy.app.version >= (4, 1, 0) and get_prefs().avoid_all_toggling_autosmooth:
            if mod.type == 'NODES' and (ng := mod.node_group):
                return ng.name.startswith('Smooth by Angle') or ng.name.startswith('Auto Smooth')

        return False

    def get_total_HUD_height(self):
        total_offset = 24 + 18 * (len(self.active.modifiers) - 1)

        if self.mod.type in ['WELD', 'DISPLACE', 'SOLIDIFY', 'BOOLEAN']:
            total_offset += 18

        if self.mod.type == 'BOOLEAN' and self.mod.solver == 'EXACT' and (self.mod.use_self or self.mod.use_hole_tolerant):
            total_offset += 18

        if self.warn_indices:
            total_offset += 6

        if self.has_multiple_solidify:
            total_offset += 18

        if self.has_multiple_displace:
            total_offset += 18

        return total_offset

    def get_compensated_offset(self, context, gap=20, debug=False):

        scale = get_scale(context)

        total_height = self.get_total_HUD_height() * scale

        mouse_height = self.HUD_y

        if debug:
            print()
            print("UI scale:", scale)
            print("HUD height:", total_height)
            print("mouse_height:", mouse_height)
            print("region height:", context.region.height)

        if mouse_height - gap < total_height:
            compensate_offset = total_height - mouse_height + gap

            if debug:
                print("offsetting up by:", compensate_offset)

            return - compensate_offset / scale

        elif mouse_height + gap > context.region.height:
            compensate_offset = mouse_height - context.region.height + gap

            if debug:
                print("offsetting down by:", compensate_offset)

            return compensate_offset / scale

        else:
            return 0

    def add_mod(self, modtype='WELD', debug=False):

        if self.mod:
            self.cancel_remove_mods.remove(self.mod)

            remove_mod(self.mod)

        self.remove_preceeding_mods()

        self.modname = get_new_mod_name(self.active, modtype=modtype, debug=debug)

        if modtype == 'WELD':
            self.mod = add_weld(self.active)

        elif modtype == 'DISPLACE':

            self.mod = add_displace(self.active, mid_level=0, strength=-0.0001)

        elif modtype == 'SOLIDIFY':

            min_dim = get_min_dim(self.active, world_space=False)
            self.mod = add_solidify(self.active, name='Shell', thickness=min_dim / 50)

        self.cancel_remove_mods.add(self.mod)

        mods, mods_len, current_idx = self.get_mods_and_indices()

        if modtype == 'WELD':
            mirrors = [mod for mod in mods if mod.type == 'MIRROR']

            if mirrors:
                last_mirror = mirrors[-1]
                last_mirror_idx = mods.index(last_mirror)

                move_mod(self.mod, last_mirror_idx)
                self.mod.name = f"- {self.modname}"

            elif mods_len > 1:
                self.mod.name = f"+ {self.modname}"

            else:
                self.mod.name = self.modname

        elif modtype == 'DISPLACE':
            earlier = [mod for mod in mods if mod.type in ['HOOK', 'BEVEL', 'SUBSURF', 'DISPLACE'] and mod != self.mod]

            if earlier:
                last_earlier = earlier[-1]
                last_earlier_idx = mods.index(last_earlier)

                move_mod(self.mod, last_earlier_idx + 1)

            else:
                move_mod(self.mod, 0)

            self.mod.name = self.modname

        elif modtype == 'SOLIDIFY':
            earlier = [mod for mod in mods if mod.type in ['HOOK', 'BEVEL', 'SUBSURF', 'DISPLACE', 'SOLIDIFY'] and mod != self.mod]

            if earlier:
                last_earlier = earlier[-1]
                last_earlier_idx = mods.index(last_earlier)

                move_mod(self.mod, last_earlier_idx + 1)

            else:
                move_mod(self.mod, 0)

            self.mod.name = self.modname

        if debug:
            print(f"Added Modifier {self.mod.name} to", self.active.name)

        self.check_multiple_warning(debug=debug)

    def add_double_subd(self, index):
        simple = add_subdivision(self.active, subdivision_type='SIMPLE', levels=2)
        simple.name = 'Subdivision (Simple)'

        catmull = add_subdivision(self.active, subdivision_type='CATMULL_CLARK', levels=2)
        catmull.name = 'Subdivision (Catmull Clark)'

        move_mod(simple, index)
        move_mod(catmull, index + 1)

        self.cancel_remove_mods.update((simple, catmull))

        return simple, catmull

    def pick_mod(self, context, index=None, debug=False):
        mods = self.active.modifiers
        active_mod = mods.active

        if self.mod:
            self.mod = list(mods)[index]
        
        elif active_mod:
            self.mod = active_mod

        else:
            self.mod = self.active.modifiers[-1]

        if self.mod != active_mod:
            self.mod.is_active = True

        self.modname = get_mod_base_name(self.mod)

        if debug:
            print(f"Picked Modifier {self.mod.name} of", self.active.name, "at index", index)

        if self.mod.type == 'SUBSURF':
            self.subd_levels = self.mod.levels
            self.sub_rendr_levels = self.mod.render_levels

        self.populate_batches(context)

        self.check_multiple_warning(debug=debug)

        self.check_tab_finish()

def draw_remove_unused_boolean_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text="Remove Unused Boolean")

        if not op.highlighted:
            row.label(text="", icon='MOUSE_LMB')
            row.label(text="Finish")

        row.label(text="", icon='EVENT_ESC')
        row.label(text="Cancel")

        row.separator(factor=10)

        row.label(text="", icon='EVENT_ALT')
        row.label(text=f"Affect all: {op.is_alt}")

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

            row.label(text="", icon='EVENT_D')
            row.label(text="Toggle Modifier")

            row.separator(factor=2)

            row.label(text="", icon='EVENT_X')
            row.label(text="Toggle Remove/Keep")

    return draw

class RemoveUnusedBooleans(bpy.types.Operator):
    bl_idname = "machin3.remove_unused_booleans"
    bl_label = "MACHIN3: Remove Unused Booleans"
    bl_description = "Look for and remove unused Boolean Modifiers and their Mod Objects"
    bl_options = {'REGISTER', 'UNDO'}

    passthrough = False

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.active_object

    def draw_HUD(self, context):
        if context.area == self.area:
            draw_init(self)

            gizmo_size = context.preferences.view.gizmo_size / 75
            ui_scale = context.preferences.system.ui_scale

            if context.scene.HC.draw_remove_unused_booleans_HUD:
                for r in self.removeCOL:
                    mod = self.active.modifiers.get(r.name)

                    color = red if r.remove else green
                    alpha = 0.7 if mod.show_viewport else 0.2

                    title = 'remove' if r.remove else 'keep'

                    if self.highlighted and r.is_highlight:

                        coords = Vector(r.co2d) + Vector((35, -3)) * gizmo_size * ui_scale
                        draw_label(context, title=title, coords=coords, center=False, color=color, alpha=1)

                        coords = Vector(r.co2d) + Vector((-5, -20)) * gizmo_size * ui_scale
                        draw_label(context, title=r.name, coords=coords, center=False, color=white, alpha=alpha)

                    elif not self.highlighted:

                        coords = Vector(r.co2d) + Vector((32, -3)) * gizmo_size * ui_scale
                        draw_label(context, title=title, coords=coords, center=False, size=10, color=color, alpha=1)

                        coords = Vector(r.co2d) + Vector((-5, -17)) * gizmo_size * ui_scale
                        draw_label(context, title=r.name, coords=coords, center=False, size=10, color=white, alpha=alpha)

    def draw_VIEW3D(self, context):
        if context.area == self.area:

            if context.scene.HC.draw_remove_unused_booleans_HUD:

                for r in self.removeCOL:

                    if r.is_highlight:
                        batch = self.remove_dict[r.name]['batch']
                        draw_mesh_wire(batch, color=red if r.remove else green, alpha=0.25, xray=True)
                        draw_mesh_wire(batch, color=red if r.remove else green, alpha=1, xray=False)

                    elif self.is_alt or (not r.remove):
                        batch = self.remove_dict[r.name]['batch']
                        draw_mesh_wire(batch, color=red if r.remove else green, alpha=0.25)

                if self.highlighted:
                    for r in self.removeCOL:
                        if not r.is_highlight:
                            draw_point(Vector(r.co), size=4, color=red if r.remove else green, alpha=0.4)

            else:
                for r in self.removeCOL:
                    draw_point(Vector(r.co), size=4, color=red if r.remove else green, alpha=0.4)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        if self.is_alt_locked:
            if event.type in alt and event.value == 'PRESS':
                self.is_alt_locked = False

        if not self.is_alt_locked:
            self.is_alt = event.alt

        if not self.is_launched_from_3d_view and event.type in alt:
            force_ui_update(context, active=self.active)

        self.highlighted = self.get_highlighted(context)

        events = ['MOUSEMOVE', 'F']

        if self.highlighted or self.is_alt:
            events.extend(['X', 'D'])

        if event.type in events:
            if event.type == 'MOUSEMOVE':

                if not self.is_launched_from_3d_view:
                    force_ui_update(context, active=self.active)

                if self.passthrough:
                    self.passthrough = False
                    
                    for r in self.removeCOL:
                        r.co2d = get_location_2d(context, r.co, default='OFF_SCREEN')
                    context.scene.HC.draw_remove_unused_booleans_HUD = True

            elif event.type in ['X', 'D', 'F'] and event.value == 'PRESS':

                if event.type == 'X':
                    state = self.highlighted.remove if self.highlighted else self.removeCOL[0].remove

                    if self.highlighted:
                        self.highlighted.remove = not state

                    elif self.is_alt:
                        for r in self.removeCOL:
                            r.remove = not state

                elif event.type == 'D':
                    statemod = self.active.modifiers.get(self.highlighted.name if self.highlighted else self.removeCOL[0].name)
                    state = statemod.show_viewport

                    if self.highlighted:
                        statemod.show_viewport = not state

                    elif self.is_alt:
                        for r in self.removeCOL:
                            mod = self.active.modifiers.get(r.name)
                            mod.show_viewport = not state

                elif event.type == 'F':

                    if event.alt:
                         bpy.ops.view3d.view_center_pick('INVOKE_DEFAULT')

                    else:
                        if self.highlighted:
                            bpy.ops.object.select_all(action='DESELECT')

                            mod = self.active.modifiers.get(self.highlighted.name)
                            obj = mod.object

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

        if navigation_passthrough(event, alt=False, wheel=True):
            self.passthrough = True

            context.scene.HC.draw_remove_unused_booleans_HUD = False

            return {'PASS_THROUGH'}

        finish_events = ['SPACE']
        
        if not self.highlighted:
            finish_events.append('LEFTMOUSE')

        if event.type in finish_events and event.value == 'PRESS':

            if context.active_object != self.active:
                bpy.ops.object.select_all(action='DESELECT')

                context.view_layer.objects.active = self.active
                self.active.select_set(True)

            operant_objs = set()

            for r in self.removeCOL:
                if r.remove:
                    mod = self.active.modifiers.get(r.name)

                    operant_objs.add(mod.object)

                    for obj in mod.object.children_recursive:
                        operant_objs.add(obj)

                    remove_mod(mod)

            remove = []

            for obj in operant_objs:
                remote = remote_boolean_poll(context, obj)

                if not remote:
                    remove.append(obj)
                    
                    if obj in self.hidden:
                        self.hidden.remove(obj)

            if remove:
                bpy.data.batch_remove(remove)

                bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

                with context.temp_override(area=self.area, region=self.region, region_data=self.region_data):
                    draw_fading_label(context, text=f"Removed {len(remove)} unused Boolean Modifiers and their mod objects", y=120, color=red, alpha=1, move_y=40, time=4)

            else:
                with context.temp_override(area=self.area, region=self.region, region_data=self.region_data):

                    draw_fading_label(context, text="Nothing removed.", y=120, color=green, alpha=1, move_y=20, time=2)

            self.finish(context)
            return {'FINISHED'}

        elif event.type in ['RIGHTMOUSE', 'ESC']:
            self.finish(context)

            return {'CANCELLED'}

        if event.type == 'MOUSEMOVE' or (self.highlighted and event.type == 'LEFTMOUSE'):
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        restore_gizmos(self)

        finish_status(self)

        for obj in self.hidden:
            obj.hide_set(False)

        wm = context.window_manager
        wm.gizmo_group_type_unlink_delayed('MACHIN3_GGT_remove_unused_booleans')

        self.removeCOL.clear()

        context.scene.HC.draw_remove_unused_booleans_HUD = False

    def invoke(self, context, event):
        self.active = context.active_object
        self.dg = context.evaluated_depsgraph_get()

        view = context.space_data

        if view.type != 'VIEW_3D':
            self.is_launched_from_3d_view = False
            self.area, view, self.region, self.region_data = self.get_3d_view(context)

            if not view:
                popup_message("This operator needs a 3D present in the workspace!")
                return {'CANCELLED'}

        else:
            self.is_launched_from_3d_view = True

            self.area = context.area
            self.region = context.region
            self.region_data = context.region.data

        self.mods = self.get_unused_booleans(context, self.active)

        if self.mods:
            wm = context.window_manager

            self.hidden = {obj for obj in context.visible_objects if obj.display_type in ['WIRE', 'BOUNDS'] or obj.type == 'EMPTY'}

            for obj in self.hidden:
                obj.hide_set(True)

            self.init_remove_dict(context)

            self.populate_remove_unused_booleans_collection(context)

            self.highlighted = None
            self.last_highlighted = None

            self.batch = None

            self.is_alt = False
            self.is_alt_locked = event.alt

            context.scene.HC.draw_remove_unused_booleans_HUD = True

            hide_gizmos(self, context)

            wm.HC_removeunusedbooleansactive = self.active

            wm.gizmo_group_type_ensure('MACHIN3_GGT_remove_unused_booleans')

            init_status(self, context, func=draw_remove_unused_boolean_status(self))

            self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
            self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:
            with context.temp_override(area=self.area, region=self.region, region_data=self.region_data):
                draw_fading_label(context, text="✔ There don't seem to be any unused Boolean Modifiers.", y=120, color=green, alpha=1, move_y=30, time=3)

            return {'FINISHED'}

    def get_3d_view(self, context):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        for region in area.regions:
                            if region.type == 'WINDOW':
                                return area, space, region, region.data

        return None, None, None, None

    def get_unused_booleans(self, context, obj, debug=False):

        booleans = [mod for mod in obj.modifiers if mod.type == 'BOOLEAN']

        dimensions = self.dg.objects[obj.name].dimensions.copy()
        facecount = len(self.dg.objects[obj.name].data.polygons)

        if debug:
            print()
            print("initial")
            print(" dimensions:", dimensions)
            print(" face count:", facecount)
            print()

        unused = []

        for mod in booleans:

            if mod.show_viewport:

                if not mod.object:
                    remove_mod(mod)

                else:

                    mod.show_viewport = False
                    self.dg.update()

                    mod_dimensions = self.dg.objects[obj.name].dimensions.copy()
                    mod_facecount = len(self.dg.objects[obj.name].data.polygons)

                    if debug:
                        print(mod.name)
                        print(" dimensions;", mod_dimensions)
                        print(" facecount:", mod_facecount)

                    if mod_dimensions == dimensions:
                        if mod_facecount == facecount:
                            unused.append(mod)

                    mod.show_viewport = True

        return unused

    def init_remove_dict(self, context):
        self.remove_dict = {mod.name: {'remove': True,

                                       'obj': mod.object,
                                       'vis': mod.object.visible_get(), 

                                       'co': None, 
                                       'co2d': None, 

                                       'batch': None} for mod in self.mods}

        for mod in self.mods:
            obj = mod.object

            ensure_visibility(context, obj, unhide=False)

            if obj.type == 'MESH' and [mod for mod in obj.modifiers if mod.type in ['ARRAY', 'MIRROR']]:
                bbox = get_bbox(obj.data)[0]
            else:
                bbox = get_eval_bbox(obj)

            co = obj.matrix_world @ average_locations(bbox)
            co2d = get_location_2d(context, co, default='OFF_SCREEN')
            mesh_eval = obj.evaluated_get(self.dg).data
            batch = get_coords(mesh_eval, mx=obj.matrix_world, edge_indices=True)

            self.remove_dict[mod.name]['co'] = co
            self.remove_dict[mod.name]['co2d'] = co2d
            self.remove_dict[mod.name]['batch'] = batch

    def populate_remove_unused_booleans_collection(self, context):
        self.removeCOL = context.window_manager.HC_removeunusedbooleansCOL
        self.removeCOL.clear()

        for modname, data in self.remove_dict.items():
            r = self.removeCOL.add()
            r.co = data['co']
            r.co2d = data['co2d']
            r.name = modname
            r.objname = data['obj'].name
            r.area_pointer = str(self.area.as_pointer())

    def get_highlighted(self, context):
        for r in self.removeCOL:
            if r.is_highlight:

                mod = self.active.modifiers.get(r.name, None)
                mod.is_active = True

                if r != self.last_highlighted:
                    self.last_highlighted = r
                    force_ui_update(context)

                return r

        if self.last_highlighted:
            self.last_highlighted = None
            force_ui_update(context)

    def update_2d_coords(self):
        for r in self.removeCOL:
            r.co2d = Vector(round(i) for i in location_3d_to_region_2d(self.region, self.region_data, r.co, default=Vector((-1000, -1000))))
        self.active.select_set(True)

class ToggleUnusedBooleanMod(bpy.types.Operator):
    bl_idname = "machin3.toggle_unused_boolean_mod"
    bl_label = "MACHIN3: Toggle Unused Boolean Mod"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()
    mode: StringProperty()

    @classmethod
    def description(cls, context, properties):
        if properties.mode == 'REMOVE':
            desc = "Toggle Modifier Removal"
        elif properties.mode == 'MODIFIER':
            desc = "Toggle Modifier Visibility"
        desc += "\nALT: Affect all Modifiers"
        return desc

    def invoke(self, context, event):
        wm = context.window_manager

        active = wm.HC_removeunusedbooleansactive
        removeCOL = wm.HC_removeunusedbooleansCOL

        if event.alt:
            rs = [r for r in removeCOL]
            mods = [active.modifiers.get(r.name) for r in rs]

        else:
            rs = [removeCOL[self.index]]
            mods = [active.modifiers.get(rs[0].name)]

        if self.mode == 'REMOVE':
            for r in rs:
                r.remove = not r.remove

        elif self.mode == 'MODIFIER':
            for mod in mods:
                mod.show_viewport = not mod.show_viewport

        if context.active_object != active:
            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = active
            active.select_set(True)

        if not mods[0].is_active:
            mods[0].is_active = True

        force_ui_update(context)

        return {'FINISHED'}

class ToggleAll(bpy.types.Operator):
    bl_idname = "machin3.toggle_all_modifiers"
    bl_label = "MACHIN3: Toggle All Modifiers"
    bl_description = "Toggle All Modifiers\nALT: Toggle Boolean Objects"
    bl_options = {'REGISTER', 'UNDO'}

    toggle_objects: BoolProperty(name="Toggle Objects, instead of Modifiers", default=False)
    active_only: BoolProperty(name="Only apply mods on the active object", default=False)
    def invoke(self, context, event):
        self.toggle_objects = event.alt
        return self.execute(context)

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)
        column.prop(self, 'toggle_objects', toggle=True)

    def execute(self, context):
        if self.active_only:
            sel = [context.active_object]

        else:
            sel = {obj for obj in context.selected_objects + [context.active_object] if obj.modifiers}

        for obj in sel:
            if self.toggle_objects:
                objects = [mod.object for mod in obj.modifiers if mod.type == 'BOOLEAN' and mod.object]

                if objects:
                    state = not objects[0].hide_get()

                    for obj in objects:
                        obj.hide_set(state)

            else:
                modifiers = [mod for mod in obj.modifiers]

                if modifiers:
                    if context.mode == 'EDIT_MESH':
                        state = not modifiers[0].show_in_editmode

                        for mod in modifiers:
                            mod.show_in_editmode = state

                    elif context.mode == 'OBJECT':
                        state = not modifiers[0].show_viewport

                        for mod in modifiers:
                            mod.show_viewport = state

        return {'FINISHED'}

class ApplyAll(bpy.types.Operator):
    bl_idname = "machin3.apply_all_modifiers"
    bl_label = "MACHIN3: Apply All Modifiers"
    bl_options = {'REGISTER', 'UNDO'}

    backup: BoolProperty(name="Create Backup", description="Create Backup before applying Mods", default=True)
    duplicate: BoolProperty(name="Duplicate", description="Apply Mods on Duplicate", default=False)
    parent_unparented_mod_objects: BoolProperty(name="Parent Unparented", description="Parent unparented Backup Mod Objects", default=True)
    stash_original: BoolProperty(name="Stash Original", default=True)
    stash_cutters: BoolProperty(name="Stash the Cutters", default=True)
    cleanup: BoolProperty(name="Clean Up", description="Clean up the Mesh, after the Mods have been applied", default=True)
    distance: FloatProperty(name="Distance", description="Distance by which Verts get merged", default=0.0001, precision=5, step=0.00001, min=0)
    active_only: BoolProperty(name="Only apply mods on the active object", default=False)
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.active_object and get_3dview_space(context)

    @classmethod
    def description(cls, context, properties):
        desc = "Apply all Modifiers"
        desc += "\nALT: Skip Backup Creation before Applying Modifiers"
        desc += "\nCTRL: Apply Modifiers on Duplicate"
        return desc

    def draw(self, context):
        global meshmachine

        layout = self.layout

        column = layout.column(align=True)

        row = column.row(align=True)
        row.prop(self, "duplicate", toggle=True)
        row.prop(self, "backup", toggle=True)

        r = row.row(align=True)
        r.active = self.backup
        r.prop(self, "parent_unparented_mod_objects", toggle=True)

        row = column.row(align=True)

        if meshmachine:
            row.prop(self, "stash_original", toggle=True)
            row.prop(self, "stash_cutters", toggle=True)

        row = column.row(align=True)
        row.prop(self, "cleanup", toggle=True)
        r = row.row(align=True)
        r.active = self.cleanup
        r.prop(self, "distance")

    def invoke(self, context, event):
        global meshmachine

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        if not meshmachine:
            self.stash_cutters = False
            self.stash_original = False

        self.backup = not event.alt
        self.duplicate = event.ctrl
        return self.execute(context)

    def execute(self, context):
        debug = True
        debug = False

        view = get_3dview_space(context)
        dg = context.evaluated_depsgraph_get()

        if self.active_only:
            sel = [context.active_object] if any([mod.show_viewport for mod in context.active_object.modifiers]) else []

        else:
            sel = {obj for obj in context.selected_objects + [context.active_object] if any([mod.show_viewport for mod in obj.modifiers])}

        if debug:
            print()
            print("backup:", self.backup)
            print("duplicate:", self.duplicate)
            print("selection:", [obj.name for obj in sel])

        for obj in sel:

            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = obj
            obj.select_set(True)

            objname = obj.name

            if debug:
                print("obj:", objname)

            if self.duplicate:

                obj_tree, _, _, _, _ = self.analyse_object_tree(obj, debug=debug)

                obj_dup, dups, duplicate_dict = self.duplicate_tree(context, dg, view, obj_tree, debug=debug)

                self.restore_pre_duplication_visibility(obj, obj_dup, dups, duplicate_dict, debug=debug)

                obj = obj_dup

                bpy.ops.object.select_all(action='DESELECT')
                context.view_layer.objects.active = obj
                obj.select_set(True)

            if self.backup:
                if debug:
                    print("\nApplying mods on", obj.name, "and creating backup")
            
                backup_name = f"{objname}_Backup"

                backupcol = bpy.data.collections.new(name=backup_name)

                obj_tree, mod_dict, outside_mod_objects, stashable_mod_objects, removable_mod_objects = self.analyse_object_tree(obj, debug=debug)

                self.replace_outside_mirror_mod_objects(obj_tree, outside_mod_objects, removable_mod_objects, debug=debug)

                obj_backup, dups, duplicate_dict = self.duplicate_tree(context, dg, view, obj_tree, debug=debug)

                self.link_duplicates_to_backup_collection(backupcol, obj, obj_backup, dups, duplicate_dict, outside_mod_objects, debug=debug)

                bc = obj.HC.backupCOL.add()
                bc.name = backup_name
                bc.collection = backupcol
                bc.active = obj_backup

            else:
                if debug:
                    print("\nApplying mods on", obj.name)

                obj_tree, mod_dict, outside_mod_objects, stashable_mod_objects, removable_mod_objects = self.analyse_object_tree(obj, debug=debug)

                self.avoid_removing_outside_mirror_mod_objets(outside_mod_objects, removable_mod_objects, debug=debug)

            obj.name = f"{objname}_AppliedMods_on_Duplicate" if self.duplicate else f"{objname}_AppliedMods"
            
            if self.stash_original:
                self.stash_orig(obj)

            flatten(obj, depsgraph=dg, keep_mods=[mod for mod in obj.modifiers if not mod.show_viewport])

            if self.stash_cutters:
                self.stash_modobjs(obj, stashable_mod_objects)

            self.remove_removable_and_unused(context, dg, obj, removable_mod_objects, debug=debug)

            self.remove_unused_edge_bevel_vgroups(context, obj)

            self.process_mesh(obj, debug=False)

        if sel:
            context.view_layer.objects.active = obj
            obj.select_set(True)

        return {'FINISHED'}

    def analyse_object_tree(self, obj, debug=False):
        obj_tree = []
        mod_dict = {}
        get_object_tree(obj, obj_tree=obj_tree, mod_objects=True, mod_dict=mod_dict, ensure_on_viewlayer=True)

        outside_mod_objects = []
        stashable_mod_objects = []
        removable_mod_objects = []

        if debug:
            print("\nentire obj tree")
            for ob in obj_tree:
                print(ob.name)

        if debug:
            print("\nmod objects only")

        for ob, mods in mod_dict.items():

            if ob == obj:
                continue

            if debug:
                print(ob.name, [(mod.name, mod.type, "on", mod.id_data.name) for mod in mods])

            if ob not in obj.children_recursive:
                outside_mod_objects.append((ob, mods))

                if debug:
                    print(" is not in obj's hierarchy")

            if ob.type == 'MESH' and any([mod.type == 'BOOLEAN' and mod.id_data == obj for mod in mods]):
                stashable_mod_objects.append(ob)

                if debug:
                    print(" is stashable")

            if not is_remote_mod_obj(obj, modobj=ob):
                removable_mod_objects.append(ob)
                
                if debug:
                    print(" is removable")

        return obj_tree, mod_dict, outside_mod_objects, stashable_mod_objects, removable_mod_objects

    def replace_outside_mirror_mod_objects(self, obj_tree, outside_mod_objects, removable_mod_objects, debug=False):
        if debug:
            print("\noutside mod objects")

        for ob, mods in outside_mod_objects:
            if debug:
                print(ob.name, [(mod.name, mod.type, mod.id_data.name) for mod in mods])

            if ob.data and all(mod.type in ['MIRROR'] for mod in mods):
                empty = bpy.data.objects.new("Mirror Empty", object_data=None)
                empty.matrix_world = ob.matrix_world

                if debug:
                    print(" replacing with empty", empty.name)

                for col in ob.users_collection:
                    col.objects.link(empty)

                for mod in mods:
                    mod.mirror_object = empty

                obj_tree.remove(ob)
                obj_tree.append(empty)

                removable_mod_objects.append(empty)

                if not self.duplicate and ob in removable_mod_objects:
                    removable_mod_objects.remove(ob)

    def avoid_removing_outside_mirror_mod_objets(self, outside_mod_objects, removable_mod_objects, debug=False):
        if debug:
            print("\noutside mod objects")

        for ob, mods in outside_mod_objects:
            if debug:
                print(ob.name, [(mod.name, mod.type, mod.id_data) for mod in mods], ob in removable_mod_objects)

            if ob in removable_mod_objects and ob.data and all(mod.type in ['MIRROR'] for mod in mods):
                if debug:
                    print(" avoid removing mod object", ob.name)

                removable_mod_objects.remove(ob)

    def duplicate_tree(self, context, dg, view, obj_tree, debug=False):
        dg.update()

        if debug:
            print("\nduplicating:")

        duplicate_dict = {str(uuid4()): (ob, ob.visible_get()) for ob in obj_tree if ob.name in context.view_layer.objects}

        for dup_hash, (ob, vis) in duplicate_dict.items():
            if debug:
                print(dup_hash, ob.name)

            ob.HC.dup_hash = dup_hash

            if view.local_view and not ob.local_view_get(view):
                if debug:
                    print("  adding", ob.name, "to local view")

                ob.local_view_set(view, True)

            ob.hide_set(False)
            ob.select_set(True)

        bpy.ops.object.duplicate(linked=False)

        obj_dup = context.active_object

        dups = [ob for ob in context.selected_objects if ob != obj_dup]

        return obj_dup, dups, duplicate_dict

    def link_duplicates_to_backup_collection(self, backupcol, obj, obj_backup, dups, duplicate_dict, outside_mod_objects, debug=False):
        outside_objs = [ob for ob, _ in outside_mod_objects]

        if debug:
            print("\nprocessing duplicated for backup")

        for dup in [obj_backup] + dups:

            if dup == obj_backup:
                if debug:
                    print(obj.name, ":", obj_backup.name)

            else:
                orig, vis = duplicate_dict[dup.HC.dup_hash]

                if debug:
                    print(orig.name, ":", dup.name)

                orig.hide_set(not vis)

                if orig in outside_objs:
                    if orig.parent:
                        if debug:
                            print("", orig.name, "is an outside object, whose dup will be unpareted now")

                        unparent(dup)

                if not dup.parent and self.parent_unparented_mod_objects:
                    if debug:
                        print(" parenting", dup.name, "to obj")

                    parent(dup, obj_backup)

                orig.HC.dup_hash = ''
                dup.HC.dup_hash = ''

            for col in dup.users_collection:
                col.objects.unlink(dup)

            backupcol.objects.link(dup)

            if debug:
                print(" added", dup.name, "to backup collection")

    def restore_pre_duplication_visibility(self, obj, obj_dup, dups, duplicate_dict, debug=False):
        if debug:
            print("\nprocessing duplicated for duplication")

        for dup in [obj_dup] + dups:
            if dup == obj_dup:
                print(obj.name, ":", obj_dup.name)

            else:
                orig, vis = duplicate_dict[dup.HC.dup_hash]
                
                if debug:
                    print(orig.name, ":", dup.name)

                orig.hide_set(not vis)
                dup.hide_set(not vis)

                orig.HC.dup_hash = ''
                dup.HC.dup_hash = ''

    def stash_orig(self, obj):
        from MESHmachine.utils.stash import create_stash

        dup = obj.copy()
        dup.data = obj.data.copy()
        dup.modifiers.clear()

        dup.HC.backupCOL.clear()

        for col in obj.users_collection:
            col.objects.link(dup)

        create_stash(obj, dup)
        bpy.data.meshes.remove(dup.data, do_unlink=True)

    def stash_modobjs(self, obj, modobjs):
        from MESHmachine.utils.stash import create_stash

        for modobj in modobjs:
            create_stash(obj, modobj, flatten_stack=True if modobj.modifiers else False)

    def remove_removable_and_unused(self, context, dg, obj, removable_mod_objects, debug=False):
        if debug:
            print("\nremoving")

        for ob in removable_mod_objects:
            if debug:
                print(ob, ob.name)

            for c in ob.children_recursive:
                if c not in removable_mod_objects:
                    if debug:
                        print(" re-parenting child object", c.name, "to obj")

                    parent(c, obj)

        bpy.data.batch_remove(removable_mod_objects)
        
        remove_unused_children(context, obj, depsgraph=dg, debug=debug)

        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    def remove_unused_edge_bevel_vgroups(self, context, obj):
        edge_bevel_vgroup_names = [vg.name for vg in obj.vertex_groups if 'Edge Bevel' in vg.name]

        edge_bevels = [mod for mod in obj.modifiers if is_edge_bevel(mod)]

        for mod in edge_bevels:
            if mod.vertex_group in edge_bevel_vgroup_names:
                edge_bevel_vgroup_names.remove(mod.vertex_group)

        for vgname in edge_bevel_vgroup_names:
            vg = obj.vertex_groups.get(vgname)

            if vg:
                obj.vertex_groups.remove(vg)

    def process_mesh(self, obj, debug=False):
        if debug:
            print("\nprocess mesh")

            print("objtype:", obj.HC.objtype)
            print("editmode:", obj.HC.geometry_gizmos_edit_mode)
            print("show geo gizmos:", obj.HC.geometry_gizmos_show)
            print("geo gizmo limit:", obj.HC.geometry_gizmos_show_limit)
            print("geo gizmo cube limit:", obj.HC.geometry_gizmos_show_cube_limit)
            print("gie gizmo cylinder limit ", obj.HC.geometry_gizmos_show_cylinder_limit)

        unhide_deselect(obj.data)

        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.normal_update()
        bm.verts.ensure_lookup_table()

        edge_glayer, face_glayer = ensure_gizmo_layers(bm)

        if self.cleanup:
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=self.distance)
            bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=self.distance)

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

class RemoveAll(bpy.types.Operator):
    bl_idname = "machin3.remove_all_modifiers"
    bl_label = "MACHIN3: Remove All Modifiers"
    bl_description = "Remove All Modifiers\nALT: Keep Cutters"
    bl_options = {'REGISTER', 'UNDO'}

    remove_cutters: BoolProperty(name="Remove Cutters", default=True)
    active_only: BoolProperty(name="Only remove mods from the active object", default=False)
    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.active_object

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)
        column.prop(self, 'remove_cutters', toggle=True)

    def invoke(self, context, event):
        self.remove_cutters = not event.alt
        return self.execute(context)

    def execute(self, context):
        if self.active_only:
            sel = [context.active_object]

        else:
            sel = {obj for obj in context.selected_objects + [context.active_object] if obj.modifiers}

        for obj in sel:

            all_modobjs = [(get_mod_obj(mod), mod.type) for mod in obj.modifiers if get_mod_obj(mod)]

            removable =[]

            for modobj, modtype in all_modobjs:

                if not is_remote_mod_obj(obj, modobj=modobj, debug=False):
                    if modtype == 'MIRROR' and modobj.type == 'MESH':
                        break
                    else:
                        removable.append(modobj)

            obj.modifiers.clear()

            if self.remove_cutters:

                children = [o for ob in removable for o in ob.children_recursive]

                bpy.data.batch_remove(removable + children)

                bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

        return {'FINISHED'}
