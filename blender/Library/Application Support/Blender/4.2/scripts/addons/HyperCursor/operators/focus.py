import bpy
from bpy.props import BoolProperty, FloatProperty
from mathutils import Vector
from math import log10
from .. utils.view import focus_on_cursor, clear_focus_cache
from .. utils.ui import get_mouse_pos, get_prefs, get_zoom_factor, ignore_events, navigation_passthrough, wrap_mouse, init_status, finish_status, force_ui_update, get_scale
from .. utils.draw import draw_init, draw_label, draw_lines, get_active_tool
from .. utils.math import dynamic_format
from .. utils.operator import Settings
from .. utils.registration import get_addon
from .. colors import white, yellow, blue, red, green

machin3tools = None

class FocusCursor(bpy.types.Operator):
    bl_idname = "machin3.focus_cursor"
    bl_label = "MACHIN3: Focus on Cursor"
    bl_description = "Focus on the Cursor"
    bl_options = {'REGISTER'}

    def execute(self, context):
        focus_on_cursor(focusmode=context.scene.HC.focus_mode, ignore_selection=True)

        return {'FINISHED'}

def draw_proximity_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)

        row.label(text=f"Focus Proximity: {dynamic_format(context.scene.HC.focus_proximity, decimal_offset=2)}")
        row.label(text=f"Clip Start: {dynamic_format(op.clip_start)}")

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Confirm")

        row.separator(factor=10)

        row.label(text="", icon='EVENT_A')
        row.label(text="", icon='EVENT_C')
        row.label(text=f"Adjust Clip Start: {op.adjust_clip_start}")

        row.separator(factor=5)
        row.label(text="Proximity Presetst via 1, 2, 3, 4 keys, optionally combine 2, 3, 4 with ALT")

    return draw

class FocusProximity(bpy.types.Operator, Settings):
    bl_idname = "machin3.focus_proximity"
    bl_label = "MACHIN3: Focus Proximity"
    bl_description = "Focus on the Cursor\nDRAG: Adjust the Proximity\nALT: Toggle Cursor"
    bl_options = {'REGISTER', 'UNDO'}

    proximity: FloatProperty(name="Proximity", default=1, min=0.000000001)
    adjust_clip_start: BoolProperty(name="Set the view's clip_start value, based on the cursor proximity, for fluid zooming", default=True)
    cache: BoolProperty(default=True)
    @classmethod
    def poll(cls, context):
        return context.mode in ['OBJECT', 'EDIT_MESH']

    def draw_HUD(self, context):
        if context.area == self.area:
            if self.show_HUD:

                draw_init(self)

                dims = draw_label(context, title="Adjust Cursor Focus Proximity", coords=Vector((self.HUD_x, self.HUD_y)), center=False)

                if self.is_shift:
                    draw_label(context, title=" a little", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

                elif self.is_ctrl:
                    draw_label(context, title=" a lot", coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, size=10, color=white, alpha=0.5)

                self.offset += 18

                dims = draw_label(context, title=f"Proximity: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, alpha=0.5)
                draw_label(context, title=dynamic_format(self.proximity, decimal_offset=2), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False)

                self.offset += 18

                dims = draw_label(context, title=f"Clip Start: ", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, alpha=0.5 if self.adjust_clip_start else 0.25)
                dims2 = draw_label(context, title=dynamic_format(self.clip_start, decimal_offset=2), coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, alpha=1 if self.adjust_clip_start else 0.25)

                if self.adjust_clip_start:
                    draw_label(context, title=" Auto", coords=Vector((self.HUD_x + dims[0] +dims2[0], self.HUD_y)), offset=self.offset, center=False, color=blue, alpha=1)

                if context.space_data.region_3d.view_perspective == 'PERSP':
                    if not self.adjust_clip_start:
                        self.offset += 18

                        draw_label(context, title=f"NOTE: Without setting Clip Start based on Proxmity, zooming is limited,", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

                        self.offset += 18
                        draw_label(context, title=f"and clipping may occur in Perspective Views", coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=yellow, alpha=1)

    def draw_VIEW3D(self, context):
        if context.area == self.area:
            if self.show_HUD and not self.is_cursor_shown:
                cmx = self.cursor.matrix
                loc, rot, _ = cmx.decompose()

                scale = get_scale(context)
                factor = get_zoom_factor(context, loc, scale=300, ignore_obj_scale=True)
                size = 0.1

                axes = [(Vector((1, 0, 0)), red), (Vector((0, 1, 0)), green), (Vector((0, 0, 1)), blue)]

                for axis, color in axes:
                    coords = []

                    coords.append(loc + (rot @ axis).normalized() * factor * size * scale * 0.9)
                    coords.append(loc + (rot @ axis).normalized() * factor * size * scale)

                    coords.append(loc + (rot @ axis).normalized() * factor * size * scale * 0.1)
                    coords.append(loc + (rot @ axis).normalized() * factor * size * scale * 0.7)

                    if coords:
                        draw_lines(coords, indices=None, width=2, color=color)

    def modal(self, context, event):
        if ignore_events(event):
            return {'RUNNING_MODAL'}

        context.area.tag_redraw()

        self.is_shift = event.shift
        self.is_ctrl = event.ctrl

        events = ['MOUSEMOVE', 'ONE', 'TWO', 'THREE', 'FOUR', 'C', 'A']

        if event.type in events:

            if event.type == 'MOUSEMOVE':
                get_mouse_pos(self, context, event)
                wrap_mouse(self, context, x=True)

                if context.scene.HC.focus_proximity != 0:

                    lg10 = log10(context.scene.HC.focus_proximity)
                    dynamic_divisor = pow(10, -lg10)
                    
                    delta_x = self.mouse_pos.x - self.last_mouse.x
                    delta_prox = delta_x / 333 / dynamic_divisor

                    precision = 0.1 if self.is_shift else 10 if self.is_ctrl else 1

                    self.proximity = context.scene.HC.focus_proximity - (delta_prox * precision)

                    self.set_proximity(context)

            elif event.type in ['ONE', 'TWO', 'THREE', 'FOUR'] and event.value == 'PRESS':

                if event.type == 'ONE':
                    self.proximity = 1

                elif event.type == 'TWO' and event.value == 'PRESS':
                    self.proximity = 5 if event.alt else 0.5

                elif event.type == 'THREE' and event.value == 'PRESS':
                    self.proximity = 10 if event.alt else 0.1

                elif event.type == 'FOUR' and event.value == 'PRESS':
                    self.proximity = 100 if event.alt else 0.01

                self.set_proximity(context)

            elif event.type in ['A', 'C'] and event.value == 'PRESS':
                self.adjust_clip_start = not self.adjust_clip_start

                force_ui_update(context)

                self.set_clip_start(context)

            if self.last_focus_proximity != self.proximity:
                self.last_focus_proximity = self.proximity
                
                if not self.show_HUD:
                    self.show_HUD = True

                    context.window.cursor_set('SCROLL_X')

                focus_on_cursor(focusmode='SOFT', ignore_selection=context.mode == 'EDIT_MESH', cache_bm=self.cache)

                if context.mode == 'EDIT_MESH':
                    force_ui_update(context)

        elif navigation_passthrough(event, alt=False, wheel=False):
            return {'PASS_THROUGH'}

        elif event.type in ['LEFTMOUSE', 'SPACE']:
            self.finish(context)

            self.save_settings()
            return {'FINISHED'}

        elif event.type in ['ESC', 'RIGHTMOUSE']:
            self.finish(context)

            context.scene.HC.focus_proximity = self.init_focus_proximity
            context.space_data.clip_start = self.init_clip_start

            focus_on_cursor(focusmode='SOFT', ignore_selection=True)

            return {'CANCELLED'}
        
        self.last_mouse = self.mouse_pos

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

        finish_status(self)
        
        context.window.cursor_set('DEFAULT')

        for obj in self.sel:
            obj.select_set(True)

        context.scene.HC.draw_HUD = True

        clear_focus_cache()

    def invoke(self, context, event):
        self.init_settings(props=['adjust_clip_start'])
        self.load_settings()

        if context.gizmo_group:
            if event.alt:
                context.space_data.overlay.show_cursor = not context.space_data.overlay.show_cursor
                return {'FINISHED'}

        else:
            context.window.cursor_set('SCROLL_X')

        self.sel = [obj for obj in context.selected_objects]

        for obj in self.sel:
            obj.select_set(False)

        self.is_cursor_shown = self.get_cursor_shown(context, debug=False)

        self.init_focus_proximity = context.scene.HC.focus_proximity
        self.init_clip_start = context.space_data.clip_start

        self.proximity = self.init_focus_proximity
        self.clip_start = self.init_clip_start

        self.last_focus_proximity = self.init_focus_proximity

        self.is_shift = False
        self.is_ctrl = False

        self.show_HUD = not context.gizmo_group

        focus_on_cursor(focusmode='SOFT', ignore_selection=context.mode == 'EDIT_MESH', cache_bm=self.cache)

        context.scene.HC.draw_HUD = False

        self.cursor = context.scene.cursor

        get_mouse_pos(self, context, event)

        self.last_mouse = self.mouse_pos

        init_status(self, context, func=draw_proximity_status(self))

        self.area = context.area
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def get_cursor_shown(self, context, debug=False):
        global machin3tools

        if machin3tools is None:
            machin3tools = get_addon('MACHIN3tools')[0]

        view = context.space_data

        m3_draw_cursor_axes = context.scene.M3.draw_cursor_axes if machin3tools else False
        hc_show_gizmos = get_active_tool(context).idname in ['machin3.tool_hyper_cursor'] and context.scene.HC.show_gizmos

        is_cursor_shown = view.overlay.show_cursor or (m3_draw_cursor_axes and not hc_show_gizmos)

        if debug:
            print("b3d show_cursor:", view.overlay.show_cursor)
            print("m3 draw_cursor_axes:", m3_draw_cursor_axes)
            print("hc show_gizmos:", hc_show_gizmos)
            print("is cursor shown?:", is_cursor_shown)

        return is_cursor_shown

    def set_proximity(self, context):

        context.scene.HC.focus_proximity = self.proximity

        self.set_clip_start(context)

    def set_clip_start(self, context):
        if self.adjust_clip_start:
            self.clip_start = 0.05 if self.proximity == 1 else self.proximity / 3

            if self.clip_start != context.space_data.clip_start:
                context.space_data.clip_start = self.clip_start

        else:
            if context.space_data.clip_start != self.init_clip_start:
                self.clip_start = self.init_clip_start
                context.space_data.clip_start = self.init_clip_start

class ResetFocusProximity(bpy.types.Operator):
    bl_idname = "machin3.reset_focus_proximity"
    bl_label = "MACHIN3: Reset Focus Proximity"
    bl_description = "Reset Focus Proximity to 1 and clip_start to 0.05"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.HC.focus_proximity = 1
        context.space_data.clip_start = 0.05

        focus_on_cursor(focusmode=context.scene.HC.focus_mode, ignore_selection=True)

        return {'FINISHED'}
