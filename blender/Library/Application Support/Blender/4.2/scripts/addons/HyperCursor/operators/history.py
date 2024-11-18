import bpy
from bpy.props import BoolProperty, FloatProperty, EnumProperty, IntProperty, StringProperty
from mathutils import Vector
from .. utils.property import step_collection, step_list
from .. utils.cursor import set_cursor
from .. utils.draw import draw_line, draw_lines, draw_point, draw_points
from .. utils.history import add_history_entry, prettify_history
from .. utils.math import compare_matrix, flatten_matrix
from .. utils.ui import popup_message, get_zoom_factor, init_timer_modal, set_countdown, get_timer_progress, force_ui_update
from .. utils.view import focus_on_cursor
from .. colors import red, blue, green
from .. items import change_history_mode_items

class DrawCursorHistory(bpy.types.Operator):
    bl_idname = "machin3.draw_cursor_history"
    bl_label = "MACHIN3: Draw Cursor History"
    bl_description = "Draw Cursor History"
    bl_options = {'INTERNAL'}

    time: FloatProperty(name="Time", default=2)
    alpha: FloatProperty(name="Alpha", default=0.5, min=0.1, max=1)
    @classmethod
    def poll(cls, context):
        return context.scene.HC.historyCOL

    def draw_VIEW3D(self, context):
        alpha = get_timer_progress(self) * self.alpha

        draw_line(self.locations, width=1, alpha=alpha / 3)

        draw_point(self.locations[0], size=4, color=green, alpha=alpha * 2)
        draw_point(self.locations[-1], size=4, color=red, alpha=alpha * 2)

        draw_points(self.locations[1:-1], size=3, alpha=alpha / 2)

        for axis, color in self.axes:

            size = 1
            coords = []

            for origin, orientation in zip(self.locations, self.orientations):
                factor = get_zoom_factor(context, origin, scale=20, ignore_obj_scale=True)

                coords.append(origin + (orientation @ axis).normalized() * size * factor * 0.1)
                coords.append(origin + (orientation @ axis).normalized() * size * factor)

            if coords:
                draw_lines(coords, color=color, width=2, alpha=alpha / 1.5)

    def modal(self, context, event):
        context.area.tag_redraw()

        if self.countdown < 0:
            self.finish(context)
            return {'FINISHED'}

        if event.type == 'TIMER':
            set_countdown(self)

        return {'PASS_THROUGH'}

    def finish(self, context):
        context.window_manager.event_timer_remove(self.TIMER)
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

    def execute(self, context):
        hc = context.scene.HC
        history = hc.historyCOL

        self.locations = [h.location for h in history]
        self.orientations = [h.rotation for h in history]

        self.matrices = [h.mx for h in history]
        self.axes = [(Vector((1, 0, 0)), red), (Vector((0, 1, 0)), green), (Vector((0, 0, 1)), blue)]

        self.idx = hc.historyIDX

        init_timer_modal(self)

        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')
        self.TIMER = context.window_manager.event_timer_add(0.05, window=context.window)

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

class CycleCursorHistory(bpy.types.Operator):
    bl_idname = "machin3.cycle_cursor_history"
    bl_label = "MACHIN3: Cycle Cursor History"
    bl_description = "Cycle through all stored Cursor States"
    bl_options = {'REGISTER', 'UNDO'}

    backwards: BoolProperty(name="Cycle backwards", default=True)
    @classmethod
    def poll(cls, context):
        return context.scene.HC.historyCOL

    def execute(self, context):
        hc = context.scene.HC
        history = hc.historyCOL

        if hc.use_world:
            hc.avoid_update = True
            hc.use_world = False

        cmx = context.scene.cursor.matrix

        current = history[hc.historyIDX]

        if compare_matrix(cmx, current.mx):
            h = step_collection(hc, current, "historyCOL", "historyIDX", -1 if self.backwards else 1)
        else:
            h = current

        if h != current or not compare_matrix(cmx, current.mx):
            set_cursor(matrix=h.mx)

            if hc.focus_cycle:
                bpy.ops.view3d.view_center_cursor('INVOKE_DEFAULT' if hc.focus_mode == 'SOFT' else 'EXEC_DEFAULT')

            if not hc.draw_history:
                bpy.ops.machin3.draw_cursor_history(time=1)

        return {'FINISHED'}

class ChangeCursorHistory(bpy.types.Operator):
    bl_idname = "machin3.change_cursor_history"
    bl_label = "MACHIN3: Change Cursor History"
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(name="Add or Remove History Entry", items=change_history_mode_items, default='ADD')
    index: IntProperty(name="History Index", description="used to remove specific entry, not the current one", default=-1)
    time: FloatProperty(default=2)
    alpha: FloatProperty(name="Alpha", default=0.5, min=0.1, max=1)
    @classmethod
    def description(cls, context, properties):
        if properties.mode == 'ADD':
            return "Add current Cursor State to History"
        elif properties.mode == 'REMOVE':
            if properties.index == -1:
                return "Remove current Cursor State from History"
            history = context.scene.HC.historyCOL
            entry = history[properties.index]
            return f"Remove {entry.name} entry from History"

    def draw_VIEW3D(self, context):
        alpha = get_timer_progress(self) * self.alpha

        if self.mode == 'REMOVE':
            if self.red_locs:
                draw_line(self.red_locs, color=(1, 0, 0), width=2, alpha=alpha)

            if self.white_locs:
                draw_line(self.white_locs, color=(1, 1, 1), width=2, alpha=alpha / 2)

        elif self.mode == 'ADD':
            draw_line(self.green_locs, color=(0, 1, 0), width=2, alpha=alpha)

        draw_line(self.all_locs, color=(1, 1, 1), width=1, alpha=alpha / 2)

    def modal(self, context, event):
        context.area.tag_redraw()

        if self.countdown < 0:
            self.finish(context)

            return {'FINISHED'}

        if event.type == 'TIMER':
            self.countdown -= 0.1

        return {'PASS_THROUGH'}

    def finish(self, context):
        context.window_manager.event_timer_remove(self.TIMER)
        bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')

    def execute(self, context):
        hc = context.scene.HC

        if self.mode == 'ADD':

            self.all_locs = [entry.location.copy() for entry in hc.historyCOL.values()]

            add_history_entry()

            force_ui_update(context)

            if len(hc.historyCOL) > 1:
                idx = hc.historyIDX

                locations = [entry.location for entry in hc.historyCOL.values()]

                if idx == len(hc.historyCOL) - 1:
                    self.green_locs = [locations[-2], locations[-1]]
                else:
                    self.green_locs = [locations[idx - 1], locations[idx], locations[idx + 1]]

                init_timer_modal(self)

                self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')
                self.TIMER = context.window_manager.event_timer_add(0.05, window=context.window)

                context.window_manager.modal_handler_add(self)
                return {'RUNNING_MODAL'}

        elif self.mode == 'REMOVE':

            if hc.historyCOL:
                cmx = context.scene.cursor.matrix

                current = hc.historyCOL[hc.historyIDX]

                if (self.index == -1 and compare_matrix(cmx, current.mx)) or self.index > -1:

                    locations = [(name, entry.location) for name, entry in hc.historyCOL.items()]

                    removeidx = current.index if self.index == -1 else self.index

                    if len(hc.historyCOL) > 2:

                        if removeidx == 0:
                            self.red_locs = [locations[0][1].copy(), locations[1][1].copy()]
                            self.white_locs = []

                        elif removeidx == len(hc.historyCOL) - 1:
                            self.red_locs = [locations[-2][1].copy(), locations[-1][1].copy()]
                            self.white_locs = []

                        else:
                            self.red_locs = [locations[removeidx - 1][1].copy(), locations[removeidx][1].copy(), locations[removeidx + 1][1].copy()]
                            self.white_locs = [locations[removeidx - 1][1].copy(), locations[removeidx + 1][1].copy()]

                    locations.pop(removeidx)

                    self.all_locs = [loc.copy() for _, loc in locations]

                    hc.historyCOL.remove(removeidx)

                    prettify_history(context)

                    if (hc.historyIDX != 0 or not hc.historyCOL) and (self.index == -1 or removeidx <= hc.historyIDX):
                        hc.historyIDX -= 1

                    if hc.auto_history and hc.historyIDX >= 0 and hc.historyCOL:
                        set_cursor(matrix=hc.historyCOL[hc.historyIDX].mx)

                        if hc.focus_cycle:
                            bpy.ops.view3d.view_center_cursor('INVOKE_DEFAULT' if hc.focus_mode == 'SOFT' else 'EXEC_DEFAULT')

                    force_ui_update(context)

                    if len(self.all_locs) > 1:
                        
                        init_timer_modal(self)

                        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')
                        self.TIMER = context.window_manager.event_timer_add(0.05, window=context.window)

                        context.window_manager.modal_handler_add(self)
                        return {'RUNNING_MODAL'}

                else:
                    popup_message(["The current stored history entry doesn't match the current cursor location.", "Enable Auto-History, cycle to another entry, or manually store the current cursor!"], title="Could not remove Cursor History Entry")
            else:
                popup_message("No cursor history stored yet.", title="Could not remove Cursor History Entry")

        elif self.mode in ['MOVEUP', 'MOVEDOWN']:

            if self.mode == 'MOVEUP' and self.index > 0:

                hc.historyCOL.move(self.index, self.index - 1)
                hc.historyIDX = self.index - 1

            elif self.mode == 'MOVEDOWN' and self.index < len(hc.historyCOL) - 1:

                hc.historyCOL.move(self.index, self.index + 1)
                hc.historyIDX = self.index + 1

            prettify_history(context)

            force_ui_update(context)

        return {'FINISHED'}

class ClearCursorHistory(bpy.types.Operator):
    bl_idname = "machin3.clear_cursor_history"
    bl_label = "MACHIN3: Clear Cursor History"
    bl_description = "Clear All Cursor History"
    bl_options = {'REGISTER', 'UNDO'}

    alpha: FloatProperty(name="Alpha", default=0.5, min=0.1, max=1)
    @classmethod
    def poll(cls, context):
        return context.scene.HC.historyCOL

    def draw_VIEW3D(self, context):
        alpha = self.countdown / self.time * self.alpha

        if len(self.all_locs) > 1:
            draw_line(self.all_locs, color=(1, 0, 0), width=2, alpha=alpha)

        else:
            draw_point(self.all_locs[0], color=(1, 0, 0), size=10, alpha=alpha)

    def modal(self, context, event):
        context.area.tag_redraw()

        if self.countdown < 0:

            context.window_manager.event_timer_remove(self.TIMER)

            bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
            return {'FINISHED'}

        if event.type == 'TIMER':
            self.countdown -= 0.1

        return {'PASS_THROUGH'}

    def execute(self, context):
        hc = context.scene.HC

        self.all_locs = [h.mx.to_translation() for _, h in hc.historyCOL.items()]

        hc.historyCOL.clear()
        hc.historyIDX = -1

        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (context, ), 'WINDOW', 'POST_VIEW')

        self.TIMER = context.window_manager.event_timer_add(0.1, window=context.window)

        self.time = self.countdown = 0.75

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

class SelectCursorHistory(bpy.types.Operator):
    bl_idname = "machin3.select_cursor_history"
    bl_label = "MACHIN3: Select Cursor History Entry"
    bl_description = "Set Cursor to History Entry\nALT: Avoid Focusing on Cursor and making it the Active Entry"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="History Index")

    def invoke(self, context, event):
        scene = context.scene
        hc = scene.HC
        history = hc.historyCOL

        if self.index < len(history):

            entry = history[self.index]

            set_cursor(matrix=entry.mx)

            if not event.alt:
                hc.historyIDX = self.index
                focus_on_cursor(focusmode=hc.focus_mode, ignore_selection=True)

        return {'FINISHED'}

class ChangeAddObjHistory(bpy.types.Operator):
    bl_idname = "machin3.change_add_obj_history"
    bl_label = "MACHIN3: Change Add Object History"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index in Redo Add Object Collection")
    mode: StringProperty(name="Mode", default='REMOVE')
    @classmethod
    def description(cls, context, properties):
        if properties.mode == 'SELECT':
            return "Select/Cycle through objects"
        elif properties.mode == 'FETCHSIZE':
            return "Set Size from Active Object"
        elif properties.mode == 'REMOVE':
            if properties.index == -1:
                return "Clear All History Entries"
            elif properties.index == -2:
                return "Clear Unused History Entries"
            else:
                return "Remove History Entry"

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.scene.HC.redoaddobjCOL

    def execute(self, context):
        redoCOL = context.scene.HC.redoaddobjCOL
        entry = redoCOL[self.index]
        active = context.active_object

        if self.mode == 'SELECT':
            if entry.name not in ['CUBE', 'CYLINDER']:
                objs = [obj for obj in context.scene.objects if obj.HC.assetpath == entry.name]

                if objs:
                    if active in objs and len(objs) > 1:
                        obj = step_list(active, objs, step=1, loop=True)
                    else:
                        obj = objs[0]

                    if obj != active:
                        bpy.ops.object.select_all(action='DESELECT')

                        if obj.hide_get():
                            obj.hide_set(False)

                        obj.select_set(True)
                        context.view_layer.objects.active = obj

                        bpy.ops.view3d.view_selected('INVOKE_DEFAULT')

        elif self.mode == 'FETCHSIZE' and active:
            entry.size = max(active.dimensions)

        elif self.mode == 'REMOVE':

            if self.index == -1:
                redoCOL.clear()

            elif self.index == -2:
                remove = []

                for entry in redoCOL:
                    assetpath = entry.name

                    if assetpath in ['CUBE', 'CYLINDER']:
                        objs = [obj for obj in context.scene.objects if obj.HC.ishyper and obj.HC.objtype == assetpath and not obj.parent and obj.display_type not in ['WIRE', 'BOUNDS']]

                        if not objs:
                            remove.append(assetpath)

                    else:
                        objs = [obj for obj in context.scene.objects if obj.HC.assetpath == assetpath]

                        if not objs:
                            remove.append(assetpath)

                for assetpath in remove:
                    index = list(redoCOL).index(redoCOL[assetpath])
                    redoCOL.remove(index)

            else:
                redoCOL.remove(self.index)

        return {'FINISHED'}
