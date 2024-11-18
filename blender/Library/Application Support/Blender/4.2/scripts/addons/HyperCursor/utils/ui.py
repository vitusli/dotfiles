import bpy
from bpy.types import DOPESHEET_MT_channel
from mathutils import Vector
import rna_keymap_ui
from bl_ui.space_statusbar import STATUSBAR_HT_header as statusbar
from bpy_extras.view3d_utils import region_2d_to_location_3d, location_3d_to_region_2d
from . import ui
from . registration import get_prefs
from .. import preferences as prefs
from .. import bl_info
from .. colors import green, yellow, red
from time import time

icons = None

def get_icon(name):
    global icons

    if not icons:
        from .. import icons

    return icons[name].icon_id

def get_mouse_pos(self, context, event, window=False, init_offset=False, hud=True, hud_offset=(20, 20)):
    self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

    if window:
        self.mouse_pos_window = Vector((event.mouse_x, event.mouse_y))

    if init_offset:
        self.mouse_offset = self.mouse_pos - Vector(context.window_manager.HC_mouse_pos_region)

    if hud:
        scale = get_scale(context)

        self.HUD_x = self.mouse_pos.x + hud_offset[0] * scale
        self.HUD_y = self.mouse_pos.y + hud_offset[1] * scale

def wrap_mouse(self, context, x=False, y=False):
    width = context.region.width
    height = context.region.height

    mouse = self.mouse_pos.copy()

    if x:
        if mouse.x <= 0:
            mouse.x = width - 10

        elif mouse.x >= width - 1:  # the -1 is required for full screen, where the max region width is never passed
            mouse.x = 10

    if y and mouse == self.mouse_pos:
        if mouse.y <= 0:
            mouse.y = height - 10

        elif mouse.y >= height - 1:
            mouse.y = 10

    if mouse != self.mouse_pos:
        warp_mouse(self, context, mouse)

def warp_mouse(self, context, co2d=Vector(), region=True, hud_offset=(20, 20)):
    coords = get_window_space_co2d(context, co2d) if region else co2d

    context.window.cursor_warp(int(coords.x), int(coords.y))

    self.mouse_pos = co2d if region else get_region_space_co2d(context, co2d)

    if getattr(self, 'last_mouse', None):
        self.last_mouse = self.mouse_pos

    if getattr(self, 'HUD_x', None):
        scale = get_scale(context)

        self.HUD_x = self.mouse_pos.x + hud_offset[0] * scale
        self.HUD_y = self.mouse_pos.y + hud_offset[1] * scale

def get_window_space_co2d(context, co2d=Vector()):
    return co2d + Vector((context.region.x, context.region.y))

def get_region_space_co2d(context, co2d=Vector()):
    return Vector((context.region.x, context.region.y)) - co2d

def get_zoom_factor(context, depth_location, scale=10, ignore_obj_scale=False, debug=False):
    center = Vector((context.region.width / 2, context.region.height / 2))
    offset = center + Vector((10, 0))

    try:
        center_3d = region_2d_to_location_3d(context.region, context.region_data, center, depth_location)
        offset_3d = region_2d_to_location_3d(context.region, context.region_data, offset, depth_location)

    except:
        return 1

    zoom_factor = (center_3d - offset_3d).length * (scale / 10)

    if context.active_object and not ignore_obj_scale:
        mx = context.active_object.matrix_world.to_3x3()

        zoom_vector = mx.inverted_safe() @ Vector((zoom_factor, 0, 0))
        zoom_factor = zoom_vector.length * (scale / 10)

    if debug:
        from . draw import draw_point

        draw_point(depth_location, color=yellow, modal=False)
        draw_point(center_3d, color=green, modal=False)
        draw_point(offset_3d, color=red, modal=False)

        print("zoom factor:", zoom_factor)
    return zoom_factor

def popup_message(message, title="Info", icon="INFO", terminal=True):
    def draw_message(self, context):
        if isinstance(message, list):
            for m in message:
                self.layout.label(text=m)
        else:
            self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw_message, title=title, icon=icon)

    if terminal:
        if icon == "FILE_TICK":
            icon = "ENABLE"
        elif icon == "CANCEL":
            icon = "DISABLE"
        print(icon, title)

        if isinstance(message, list):
            print(" »", ", ".join(message))
        else:
            print(" »", message)

def draw_keymap_items(kc, keylist, layout):
    drawn = []

    idx = 0

    for item in keylist:
        keymap = item.get("keymap")
        isdrawn = False

        if keymap:
            km = kc.keymaps.get(keymap)

            kmi = None
            if km:
                idname = item.get("idname")

                for kmitem in km.keymap_items:
                    if kmitem.idname == idname:
                        properties = item.get("properties")

                        if properties:
                            if all([getattr(kmitem.properties, name, None) == value for name, value in properties]):
                                kmi = kmitem
                                break

                        else:
                            kmi = kmitem
                            break

            if kmi:
                label = item.get("label", '')

                if label:
                    row = layout.split(factor=0.15)
                    row.label(text=label)
                else:
                    row = layout

                rna_keymap_ui.draw_kmi(["ADDON", "USER", "DEFAULT"], kc, km, kmi, row, 0)

                info = item.get("info", '')

                if info:
                    row = layout.split(factor=0.15)
                    row.active = False
                    row.label(text=f" ↖ {info}", icon="NONE")

                isdrawn = True
                idx += 1

        drawn.append(isdrawn)
    return drawn

def get_event_icon(event_type):
    if 'MOUSE' in event_type:
        return 'MOUSE_LMB' if 'LEFT' in event_type else 'MOUSE_RMB' if 'RIGHT' in event_type else 'MOUSE_MMB'

    elif 'EVT_TWEAK' in event_type:
        return f"MOUSE_{'LMB' if event_type.endswith('_L') else 'RMB' if event_type.endswith('_R') else 'MMB'}_DRAG"

    else:
        return f'EVENT_{event_type}'

def get_keymap_item(name, idname, key=None, alt=False, ctrl=False, shift=False, properties=[]):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user

    km = kc.keymaps.get(name)

    if bpy.app.version >= (3, 0, 0):
        alt = int(alt)
        ctrl = int(ctrl)
        shift = int(shift)

    if km:
        kmi = km.keymap_items.get(idname)

        if kmi:
            found = True if key is None else all([kmi.type == key and kmi.alt is alt and kmi.ctrl is ctrl and kmi.shift is shift])

            if found:
                if properties:
                    if all([getattr(kmi.properties, name, False) == prop for name, prop in properties]):
                        return kmi
                else:
                    return kmi

def get_pretty_keymap_item_name(kmi):
    name = kmi.name.replace('MACHIN3: ', '').replace(' Macro', '')

    if kmi.idname == 'machin3.call_hyper_cursor_pie':
        if kmi.properties.idname == 'MACHIN3_MT_add_object_at_cursor':
            return "Add Object at Cursor"

    elif kmi.idname == 'machin3.transform_cursor':
        if kmi.properties.mode == 'DRAG':
            return name + ' (Drag Mode)'

    elif kmi.idname == 'machin3.point_cursor':
        if kmi.properties.instant:
            return name + ' Z instantly'

    elif kmi.idname == 'machin3.cycle_cursor_history':
        if kmi.properties.backwards:
            return name + ' ↑ (previous)'
        else:
            return name + ' ↓ (next)'

    elif kmi.idname == 'machin3.hyper_modifier':
        return name + f" ({kmi.properties.mode.title()})"

    elif kmi.idname == 'machin3.extract_face':
        return "Extract Evaluated Faces"

    return name

def get_modified_keymap_items(context):
    from .. registration import keys

    wm = context.window_manager
    kc = wm.keyconfigs.user

    modified_kmis = []

    for tool, mappings in keys.items():
        if tool == 'TOOLBAR':
            keymap_name = mappings[0]['keymap']

        elif tool == 'HYPERCURSOR':
            keymap_name = "3D View Tool: Object, Hyper Cursor"

        elif tool == 'HYPERCURSOREDIT':
            keymap_name = "3D View Tool: Edit Mesh, Hyper Cursor"

        else:
            continue

        km = kc.keymaps.get(keymap_name)

        if km:

            modified = []

            for kmi in reversed(km.keymap_items):
                
                if tool == 'TOOLBAR':
                    if (props := kmi.properties) and "machin3.tool_hyper_cursor" in (name := props.get('name')):

                        if kmi.is_user_modified:
                            modified.append((km, kmi))

                else:

                    if kmi.is_user_modified:
                        modified.append((km, kmi))

            if modified:
                modified_kmis.extend(modified)

            if not modified and km.is_user_modified and tool != 'TOOLBAR':  # NOTE: for some reasone the toolbar keymap always shows as user modified?
                modified_kmis.append((km, None))

    return modified_kmis

def get_panel_fold(layout, data=(None, ''), text='', icon='NONE', align=True, default_closed=True, is_popup=False):
    if bpy.app.version >= (4, 1, 0) and not is_popup:
        header, panel = layout.panel(data[1], default_closed=default_closed)
        header.active = bool(panel)
        header.label(text=text, icon=icon)

        return panel.column(align=align) if panel else None

    elif data:
        id, prop = data

        is_folded = getattr(id, prop)

        column = layout.column(align=True)
        row = column.row(align=True)
        row.active = not is_folded
        row.prop(id, prop, text='', icon='RIGHTARROW' if is_folded else 'DOWNARROW_HLT', emboss=False)
        row.prop(id, prop, text=text + '       ', icon=icon, emboss=False)

        return None if is_folded else column.box().column(align=align)

def init_status(self, context, title='', func=None):
    self.bar_orig = statusbar.draw

    if func:
        statusbar.draw = func
    else:
        statusbar.draw = draw_basic_status(self, context, title)

def draw_basic_status(self, context, title):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text=title)

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Finish")

        if context.window_manager.keyconfigs.active.name.startswith('blender'):
            row.label(text="", icon='MOUSE_MMB')
            row.label(text="Viewport")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

    return draw

def finish_status(self):
    statusbar.draw = self.bar_orig

generic_gizmo = None

def draw_enable_gizmos_warning(context, layout, tool):
    wm = context.window_manager
    kc = wm.keyconfigs.user

    mode = context.mode

    keymap = prefs.tool_keymaps_mapping[(tool.idname, mode)]
    km = kc.keymaps.get(keymap)

    if km:
        kmi = km.keymap_items.get('machin3.toggle_hyper_cursor_gizmos')

        if kmi and kmi.active:
            row = layout.row(align=True)
            row.separator(factor=2)

            row.label(text='Reveal Hyper Cursor Gizmos via', icon="ERROR")

            if kmi.shift:
                row.label(text="", icon='EVENT_SHIFT')
            if kmi.alt:
                row.label(text="", icon='EVENT_ALT')
            if kmi.ctrl:
                row.label(text="", icon='EVENT_CTRL')

            row.label(text="", icon=get_event_icon(kmi.type))

def draw_tool_header(context, layout, tool):
    global generic_gizmo

    p = get_prefs()
    version = '.'.join([str(i) for i in bl_info['version']])
    hc = context.scene.HC

    toolbar = getattr(context.space_data, 'show_region_toolbar', False)

    if toolbar:
        layout.label(text=f"Hyper Cursor {version}", icon_value=get_icon('hypercursor'))
    else:
        layout.label(text=f"Hyper Cursor {version}")
    
    if generic_gizmo is None or (generic_gizmo and generic_gizmo.idname != 'gizmogroup.gizmo_tweak'):
        generic_gizmo = ui.get_keymap_item('Generic Gizmo', 'gizmogroup.gizmo_tweak')

    if generic_gizmo and not generic_gizmo.any:
        layout.operator("machin3.setup_generic_gizmo_keymap", text='Setup Generic Gizmo', icon='EVENT_ALT')

    if p.show_world_mode:
        layout.prop(context.scene.HC, 'use_world', text="World", icon='WORLD', toggle=True)

    if p.show_hints:

        if hc.draw_pipe_HUD and not hc.show_gizmos:
            layout.separator(factor=2)

            row = layout.row()
            row.alert = True
            row.label(text="You are in Pipe Mode, with the HyperCursor Gizmo hidden!", icon='ERROR')

        elif not hc.show_gizmos:
            draw_enable_gizmos_warning(context, layout, tool)

    if p.show_help:
        layout.separator(factor=2)
        layout.operator("machin3.hyper_cursor_help", text='Help', icon='INFO')

    if p.show_update_available and p.update_available:
        layout.separator(factor=2)
        layout.label(text="A HyperCursor Update is available!", icon_value=get_icon('refresh_green'))

def navigation_passthrough(event, alt=True, wheel=False) -> bool:

    if alt and wheel:
        return event.type in {'MIDDLEMOUSE'} or event.type.startswith('NDOF') or (event.alt and event.type in {'LEFTMOUSE', 'RIGHTMOUSE'} and event.value == 'PRESS') or event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}
    elif alt:
        return event.type in {'MIDDLEMOUSE'} or event.type.startswith('NDOF') or (event.alt and event.type in {'LEFTMOUSE', 'RIGHTMOUSE'} and event.value == 'PRESS')
    elif wheel:
        return event.type in {'MIDDLEMOUSE'} or event.type.startswith('NDOF') or event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}
    else:
        return event.type in {'MIDDLEMOUSE'} or event.type.startswith('NDOF')

def gizmo_selection_passthrough(event) -> bool:
    return event.type in ['MOUSEMOVE', 'LEFTMOUSE']

def scroll_up(event, wheel=True, key=False):
    up_keys = ['ONE', 'UP_ARROW']

    if event.value == 'PRESS':
        if wheel and key:
            return event.type in {'WHEELUPMOUSE', *up_keys}
        elif wheel:
            return event.type in {'WHEELUPMOUSE'}
        else:
            return event.type in {*up_keys}

def scroll_down(event, wheel=True, key=False):
    down_keys = ['TWO', 'DOWN_ARROW']

    if event.value == 'PRESS':
        if wheel and key:
            return event.type in {'WHEELDOWNMOUSE', *down_keys}
        elif wheel:
            return event.type in {'WHEELDOWNMOUSE'}
        else:
            return event.type in {*down_keys}

def get_mousemove_divisor(event, normal=10, shift=50, ctrl=2, sensitivity=1):
    divisor = ctrl if event.ctrl else shift if event.shift else normal
    ui_scale = bpy.context.preferences.system.ui_scale

    return divisor * ui_scale * sensitivity

def init_timer_modal(self, debug=False):
    self.start = time()

    self.countdown = self.time * get_prefs().modal_hud_timeout

    if debug:
        print(f"initiating timer with a countdown of {self.time}s ({self.time * get_prefs().modal_hud_timeout}s)")

def set_countdown(self, debug=False):
    self.countdown = self.time * get_prefs().modal_hud_timeout - (time() - self.start)

    if debug:
        print("countdown:", self.countdown)

def get_timer_progress(self, debug=False):
    progress =  self.countdown / (self.time * get_prefs().modal_hud_timeout)

    if debug:
        print("progress:", progress)

    return progress

def ignore_events(event, none=True, timer=True, timer_report=True):
    ignore = ['INBETWEEN_MOUSEMOVE', 'WINDOW_DEACTIVATE']

    if none:
        ignore.append('NONE')

    if timer:
        ignore.extend(['TIMER', 'TIMER1', 'TIMER2', 'TIMER3'])

    if timer_report:
        ignore.append('TIMER_REPORT')

    return event.type in ignore

def is_key(self, event, key, debug=False):
    keystr = f'is_{key.lower()}'

    if getattr(self, keystr, None) is None:
        setattr(self, keystr, False)

    if event.type == key:
        if event.value == 'PRESS':
            if not getattr(self, keystr):
                setattr(self, keystr, True)

        elif event.value == 'RELEASE':
            if getattr(self, keystr):
                setattr(self, keystr, False)

    if debug:
        print()
        print(f"is {key.capitalize()}:", getattr(self, keystr))

    return getattr(self, keystr)

def get_flick_direction(context, mouse_loc_3d, flick_vector, axes):
    origin_2d = location_3d_to_region_2d(context.region, context.region_data, mouse_loc_3d, default=Vector((context.region.width / 2, context.region.height / 2)))
    axes_2d = {}

    for direction, axis in axes.items():

        axis_2d = location_3d_to_region_2d(context.region, context.region_data, mouse_loc_3d + axis, default=origin_2d)
        if (axis_2d - origin_2d).length:
            axes_2d[direction] = (axis_2d - origin_2d).normalized()

    return min([(d, abs(flick_vector.xy.angle_signed(a))) for d, a in axes_2d.items()], key=lambda x: x[1])[0]

def force_ui_update(context, active=None):
    if context.mode == 'OBJECT':
        if active:
            active.select_set(True)

        else:
            visible = context.visible_objects

            if visible:
                visible[0].select_set(visible[0].select_get())

    elif context.mode == 'EDIT_MESH':
        context.active_object.select_set(True)

def force_obj_gizmo_update(context):
    from .. ui import gizmos
    gizmos.force_obj_gizmo_update = True

    force_ui_update(context)

def force_geo_gizmo_update(context):
    from .. ui import gizmos
    gizmos.force_geo_gizmo_update = True

    force_ui_update(context)

def force_pick_hyper_bevels_gizmo_update(context):
    from .. ui import gizmos
    gizmos.force_pick_hyper_bevels_gizmo_update = True

    force_ui_update(context)

def get_scale(context):
    return context.preferences.system.ui_scale * get_prefs().modal_hud_scale

def is_on_screen(context, co2d):
    if 0 <= co2d.x <= context.region.width:
        if 0 <= co2d.y <= context.region.height:
            return True
    return False
