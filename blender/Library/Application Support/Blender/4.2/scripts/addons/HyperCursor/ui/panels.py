import bpy
from .. import bl_info
from .. utils.tools import active_tool_is_hypercursor, get_active_tool
from .. utils.ui import get_event_icon, get_panel_fold
from .. utils.modifier import array_poll, boolean_poll, get_mod_input, hyper_array_poll, is_linear_array, is_radial_array, remote_boolean_poll, local_boolean_poll, mirror_poll, edgebevel_poll, solidify_poll, other_poll
from .. preferences import tool_keymaps_mapping
from .. utils.system import printd
from .. utils.registration import get_prefs
from .. utils.ui import get_icon, get_pretty_keymap_item_name
from .. utils.nodes import get_nodegroup_input_identifier
from .. items import keymap_folds

class PanelHyperCursor(bpy.types.Panel):
    bl_idname = "MACHIN3_PT_hyper_cursor"
    bl_label = ''
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MACHIN3"
    bl_order = 30

    @classmethod
    def poll(cls, context):
        if get_prefs().show_sidebar_panel:
            if context.mode in ['OBJECT', 'EDIT_MESH']:
                return active_tool_is_hypercursor(context)

    def draw(self, context):
        draw_settings_panel(self, context, draw_grip=False)

    def draw_header(self, context):
        layout = self.layout
        hc = context.scene.HC

        row = layout.row(align=True)

        row.label(text=f"HyperCursor {'.'.join([str(v) for v in bl_info['version']])}")

        row.prop(hc, 'sidebar_show_gizmos', text='', icon='GIZMO')
        row.prop(hc, 'sidebar_show_cursor_history', text='', icon='CURSOR')
        row.prop(hc, 'sidebar_show_object_history', text='', icon='CUBE')
        row.prop(hc, 'sidebar_show_focus', text='', icon='HIDE_OFF')
        row.prop(hc, 'sidebar_show_asset_creation', text='', icon='MONKEY')
        row.prop(hc, 'sidebar_show_keymaps', text='', icon='EVENT_SPACEKEY')
        row.prop(hc, 'sidebar_show_links', text='', icon='URL')

def draw_settings_panel(self, context, draw_grip=False):
    layout = self.layout

    hc = context.scene.HC
    is_popup = self.bl_idname.startswith('MACHIN3_OT_')

    active = context.active_object
    sel = context.selected_objects

    is_wire = active and active.display_type in ['WIRE', 'BOUNDS']

    view = context.space_data

    if draw_grip:
        row = layout.row(align=True)

        row.label(text=f"HyperCursor {'.'.join([str(v) for v in bl_info['version']])}", icon='GRIP')

        row.prop(hc, 'sidebar_show_gizmos', text='', icon='GIZMO')
        row.prop(hc, 'sidebar_show_cursor_history', text='', icon='CURSOR')
        row.prop(hc, 'sidebar_show_object_history', text='', icon='CUBE')
        row.prop(hc, 'sidebar_show_focus', text='', icon='HIDE_OFF')
        row.prop(hc, 'sidebar_show_asset_creation', text='', icon='MONKEY')
        row.prop(hc, 'sidebar_show_keymaps', text='', icon='EVENT_SPACEKEY')
        row.prop(hc, 'sidebar_show_links', text='', icon='URL')

    if context.mode in ['OBJECT', 'EDIT_MESH'] and get_active_tool(context):
        if get_active_tool(context).idname in ['machin3.tool_hyper_cursor', 'machin3.tool_hyper_cursor_simple']:

            if get_prefs().update_available:
                layout.separator(factor=2)
                layout.label(text="A HyperCursor Update is available!", icon_value=get_icon('refresh_green'))
                layout.separator(factor=2)

            if hc.sidebar_show_gizmos:
                panel = get_panel_fold(layout, data=(hc, 'sidebar_fold_gizmos'), text='Gizmos', icon='GIZMO', align=True, default_closed=True, is_popup=is_popup)
                if panel:
                    panel.scale_y = 1.2

                    row = panel.row(align=True)
                    row.prop(hc, 'show_gizmos', text='Show Hyper Cursor', toggle=True, icon_value=get_icon('hypercursor'))
                    row.prop(hc, 'use_world', text='World Orientation', toggle=True, icon='WORLD')

                    row = panel.row(align=True)
                    row.active = hc.show_gizmos
                    row.prop(hc, 'show_button_history', text='History', toggle=True)
                    row.prop(hc, 'show_button_focus', text='Focus', toggle=True)
                    row.prop(hc, 'show_button_settings', text='Settings', toggle=True)
                    row.prop(hc, 'show_button_cast', text='Cast', toggle=True)
                    row.prop(hc, 'show_button_object', text='Object', toggle=True)

                    if active and active.HC.ishyper and active.type == 'MESH' and active in sel and len(sel) == 1: 
                        panel.separator()

                        row = panel.row(align=True)
                        row.alignment = 'LEFT'
                        row.label(text=f"{active.name}")
                        r = row.row(align=True)
                        r.active = False
                        r.label(text="'s Geometry Gizmos")

                        row = panel.row(align=True)
                        row.prop(active.HC, 'geometry_gizmos_show', text='Show Geo Gizmos', toggle=True, icon='MOD_EDGESPLIT')

                        r = row.row(align=True)
                        r.active = active.HC.geometry_gizmos_show
                        r.enabled = not is_wire
                        r.prop(hc, 'gizmo_xray', text='X-Ray', toggle=True, icon='XRAY')

                        row = panel.row(align=True)
                        row.active = active.HC.geometry_gizmos_show
                        row.prop(active.HC, 'geometry_gizmos_edit_mode', expand=True)

                        if active.HC.geometry_gizmos_show:

                            sub_panel = get_panel_fold(panel, data=(hc, 'sidebar_fold_geo_gizmo_limits'), text='Geometry Limits', align=True, default_closed=True, is_popup=is_popup)
                            if sub_panel:
                                if active.HC.objtype == 'CUBE':

                                    if active.HC.geometry_gizmos_show_cube_limit < len(active.data.polygons):
                                        row = sub_panel.row()
                                        row.alert =True
                                        row.label(text="Edit Gizmos Disabled", icon='ERROR')

                                    sub_panel.prop(active.HC, 'geometry_gizmos_show_cube_limit', text="Cube Polygon Limit")

                                elif active.HC.objtype == 'CYLINDER':
                                    if active.HC.geometry_gizmos_show_cylinder_limit < len(active.data.edges):
                                        row = column.row()
                                        row.alert =True
                                        row.label(text="Edit Gizmos Disabled", icon='ERROR')

                                    sub_panel.prop(active.HC, 'geometry_gizmos_show_cylinder_limit', text="Cylinder Edge Limit")

                            if active.HC.geometry_gizmos_edit_mode == 'EDIT':
                                sub_panel = get_panel_fold(panel, data=(hc, 'sidebar_fold_geo_gizmo_scale'), text='Gizmo Scale', align=True, default_closed=True, is_popup=is_popup)
                                if sub_panel:
                                    sub_panel.prop(active.HC, 'geometry_gizmos_scale')
                                    sub_panel.prop(active.HC, 'geometry_gizmos_edge_thickness')
                                    sub_panel.prop(active.HC, 'geometry_gizmos_face_tween')

            if hc.sidebar_show_cursor_history:
                panel = get_panel_fold(layout, data=(hc, 'sidebar_fold_cursor_history'), text='Cursor History', icon='CURSOR', align=True, default_closed=True, is_popup=is_popup)
                if panel:
                    row = panel.split(factor=0.5, align=True)
                    row.scale_y = 1.2

                    row.prop(hc, 'auto_history', text='Auto History', toggle=True)

                    r = row.row(align=True)
                    r.active = True if hc.historyCOL else False
                    r.prop(hc, 'draw_history', text="Draw History", toggle=True)

                    if hc.draw_history:
                        r.prop(hc, 'draw_history_select', text="", icon='RESTRICT_SELECT_OFF', toggle=True)
                        r.prop(hc, 'draw_history_remove', text="", icon='X', toggle=True)

                    row = panel.row(align=True)
                    row.scale_y = 1.2
                    row.operator('machin3.change_cursor_history', text='Add History Entry', icon='ADD').mode = 'ADD'

                    r = row.row(align=True)
                    r.active = True if hc.historyCOL else False
                    r.operator('machin3.clear_cursor_history', text='Clear History')

                    if hc.historyCOL:
                        panel.separator()
                        panel.label(text='Cursor History List')

                        panel.template_list("MACHIN3_UL_history_cursor", "", hc, "historyCOL", hc, "historyIDX", rows=max(len(hc.historyCOL), 1))

            if hc.sidebar_show_object_history:
                if hc.redoaddobjCOL:
                    panel = get_panel_fold(layout, data=(hc, 'sidebar_fold_object_history'), text='Object History', icon='CUBE', align=True, default_closed=True, is_popup=is_popup)
                    if panel:
                        row = panel.row(align=True)
                        row.scale_y = 1.2

                        op = row.operator('machin3.change_add_obj_history', text=f'Clear Unused')
                        op.index = -2
                        op.mode = 'REMOVE'

                        op = row.operator('machin3.change_add_obj_history', text=f'Clear All')
                        op.index = -1
                        op.mode = 'REMOVE'

                        panel.separator()
                        panel.label(text='Object History List')

                        panel.template_list("MACHIN3_UL_redo_add_object", "", hc, "redoaddobjCOL", hc, "redoaddobjIDX", rows=max(len(hc.redoaddobjCOL), 1))

            if hc.sidebar_show_focus:
                panel = get_panel_fold(layout, data=(hc, 'sidebar_fold_focus'), text='Focus', icon='HIDE_OFF', align=True, default_closed=True, is_popup=is_popup)
                if panel:
                    split = panel.split(factor=0.9, align=True)

                    row = split.row(align=True)
                    row.prop(hc, 'focus_proximity', text='Proximity')
                    row.prop(view, 'clip_start', text='Clip Start')
                    split.operator('machin3.reset_focus_proximity', text='', icon='LOOP_BACK')

                    row = panel.row(align=True)
                    row.prop(hc, 'focus_mode', text='Focus Cycle', expand=True)

                    row = panel.row(align=True)
                    row.prop(hc, 'focus_transform', text='Transform', toggle=True)

                    row.prop(hc, 'focus_cycle', text='Cycle', toggle=True)
                    row.prop(hc, 'focus_cast', text='Cast', toggle=True)

            if hc.sidebar_show_asset_creation:
                panel = get_panel_fold(layout, data=(hc, 'sidebar_fold_asset_creation'), text='Hyper Asset Creation', icon='MONKEY', align=True, default_closed=True, is_popup=is_popup)
                if panel:
                    if context.mode == 'OBJECT' and sel:
                        is_instance_collection_asset = any([obj.asset_data and obj.type == 'EMPTY' and obj.instance_type == 'COLLECTION' for obj in sel])

                        row = panel.row(align=True)
                        row.scale_y = 0.8 if is_instance_collection_asset else 1.3
                        action = 'Change' if len(sel) == 1 and sel[0].asset_data and not sel[0].instance_collection else 'Create Collection' if len(sel) > 1 else 'Create'
                        op = row.operator('machin3.create_asset', text=f'{action} Asset')
                        op.ischange = action == 'Change'

                        if is_instance_collection_asset:
                            row = panel.row(align=True)
                            row.scale_y = 1.3
                            row.operator('machin3.disband_collection_instance_asset', text='Disband')

                    else:
                        if context.mode != 'OBJECT' and not sel:
                            panel.label(text="Go into OBJECT mode and make a selection", icon='INFO')

                        elif context.mode != 'OBJECT':
                            panel.label(text="Go into OBJECT mode", icon='INFO')

                        else:
                            panel.label(text="Make a selection", icon='INFO')

            if hc.sidebar_show_keymaps:
                panel = get_panel_fold(layout, data=(hc, 'sidebar_fold_keymaps'), text='Keymaps', icon='EVENT_SPACEKEY', align=True, default_closed=True, is_popup=is_popup)
                if panel:
                    draw_keymaps(self, context, panel)

            if hc.sidebar_show_links:
                panel = get_panel_fold(layout, data=(hc, 'sidebar_fold_links'), text='Documentation / Support', icon='URL', align=True, default_closed=True, is_popup=is_popup)
                if panel:
                    draw_links(self, context, panel)

        else:
            column = layout.column()
            column.scale_y = 1.5
            column.operator('wm.tool_set_by_id', text="Enable HyperCursor Tool", icon_value=get_icon('hypercursor')).name = 'machin3.tool_hyper_cursor'

    if bpy.ops.machin3.button.poll():
        layout.separator()
        column = layout.column()
        column.scale_y = 2
        column.operator('machin3.button', text='Button')

def draw_help_panel(self, context):
    layout = self.layout
    hc = context.scene.HC

    draw_keymaps(self, context, layout, help_popup=True)

    panel = get_panel_fold(layout, data=(hc, 'help_popup_fold_links'), text='Documentation / Support', align=True, default_closed=True, is_popup=True)
    if panel:
        draw_links(self, context, panel)

def draw_keymaps(self, context, layout, help_popup=False):
    wm = context.window_manager
    kc = wm.keyconfigs.user

    hc = context.scene.HC
    is_popup = self.bl_idname.startswith('MACHIN3_OT_')

    mode = context.mode
    active_tool = get_active_tool(context)

    keymap = tool_keymaps_mapping[(active_tool.idname, mode)]

    km = kc.keymaps.get(keymap)

    if km:
        text, icon= f"{mode.title().replace('_', ' ')} Mode", 'NONE'

        if help_popup:
            text += ' Keymaps'
            icon = 'GRIP'

        layout.label(text=text, icon=icon)

        panel = None

        for kmi in reversed(km.keymap_items):

            if kmi.active:

                if kmi.idname.startswith('view3d'):
                    continue

                if text := keymap_folds[mode].get(kmi.id, None):
                      panel = get_panel_fold(layout, data=(hc, f"sidebar_fold_keymaps_{mode.lower()}_{kmi.id}"), text=text, align=True, default_closed=True, is_popup=is_popup)
                if panel:
                    row = panel.split(factor=0.3, align=True)
                    r = row.row(align=True)

                    if kmi.shift:
                        r.label(text="", icon='EVENT_SHIFT')
                    if kmi.alt:
                        r.label(text="", icon='EVENT_ALT')
                    if kmi.ctrl:
                        r.label(text="", icon='EVENT_CTRL')

                    r.label(text="", icon=get_event_icon(kmi.type))

                    row.label(text=get_pretty_keymap_item_name(kmi))

def draw_links(self, context, layout):
    layout.label(text="None of this works yet!", icon='ERROR')
    layout.label(text="Talk to me on patreon or via email:")
    layout.label(text="hype@machin3.io")
    layout.separator(factor=2)

    row = layout.row(align=True)
    row.scale_y = 1.5
    row.operator("wm.url_open", text="Documentation", icon='HELP').url = "https://machin3.io/HyperCursor/docs"
    row.operator("wm.url_open", text="Get Support", icon='GREASEPENCIL')

    row = layout.row(align=True)
    row.operator("wm.url_open", text="Blender Artists", icon="COMMUNITY").url = "https://blenderartists.org/t/TODO"

    layout.operator("wm.url_open", text="Youtube", icon='FILE_MOVIE').url = "https://www.youtube.com/playlist?list=TODO"

def draw_object_panel(self, context):
    def draw_edge_bevels():
        box = layout.box()
        box.label(text='Edge Bevel')

        col = box.column(align=True)

        for mod in edgebevels:
            row = col.row(align=True)

            split = row.split(factor=0.5, align=True)
            op = split.operator('machin3.change_edge_bevel', text=mod.name, emboss=mod.show_viewport)
            op.modname = mod.name
            op.mode = 'ACTIVATE'

            s = split.split(factor=0.6, align=True)
            if mod.offset_type == 'PERCENT':
                s.prop(mod, 'width_pct', text="")
            else:
                s.prop(mod, 'width', text="")
            s.prop(mod, 'segments', text="")

            op = row.operator('machin3.change_edge_bevel', text="", icon='IMPORT')
            op.modname = mod.name
            op.mode = 'APPLY'

            op = row.operator('machin3.change_edge_bevel', text="", icon='X')
            op.modname = mod.name
            op.mode = 'REMOVE'

    def draw_solidifies():
        box = layout.box()
        box.label(text='Solidify')

        col = box.column(align=True)

        for mod in solidifies:
            row = col.row(align=True)

            split = row.split(factor=0.3, align=True)
            op = split.operator('machin3.change_solidify', text=mod.name, emboss=mod.show_viewport)
            op.modname = mod.name
            op.mode = 'ACTIVATE'

            s = split.split(factor=0.4, align=True)
            s.prop(mod, 'thickness', text="")
            s.prop(mod, 'offset', text="")
            s.prop(mod, 'use_even_offset', text="Even", toggle=True)

            op = row.operator('machin3.change_solidify', text="", icon='IMPORT')
            op.modname = mod.name
            op.mode = 'APPLY'

            op = row.operator('machin3.change_solidify', text="", icon='X')
            op.modname = mod.name
            op.mode = 'REMOVE'

    def draw_remote_booleans():
        box = layout.box()
        box.label(text='Remote Boolean')

        col = box.column(align=True)
        for obj, mods in remote_booleans.items():
            for mod in mods:
                row = col.row(align=True)

                icon = 'HIDE_OFF' if mod.object.visible_get() else 'HIDE_ON'
                op = row.operator('machin3.change_remote_boolean', text="", icon=icon)
                op.objname = obj.name
                op.modname = mod.name
                op.mode = 'HIDE'

                icon = 'MOD_WIREFRAME' if mod.object.display_type == 'BOUNDS' else 'SHADING_WIRE'
                op = row.operator('machin3.change_remote_boolean', text="", icon=icon)
                op.objname = obj.name
                op.modname = mod.name
                op.mode = 'WIRE'

                split = row.split(factor=0.7, align=True)
                op = split.operator('machin3.change_remote_boolean', text=mod.name, emboss=mod.show_viewport)
                op.objname = obj.name
                op.modname = mod.name
                op.mode = 'ACTIVATE'

                op = split.operator('machin3.change_remote_boolean', text=mod.solver.title())
                op.objname = obj.name
                op.modname = mod.name
                op.mode = 'SOLVER'

                op = row.operator('machin3.change_remote_boolean', text="", icon='IMPORT')
                op.objname = obj.name
                op.modname = mod.name
                op.mode = 'APPLY'

                op = row.operator('machin3.change_remote_boolean', text="", icon='X')
                op.objname = obj.name
                op.modname = mod.name
                op.mode = 'REMOVE'

    def draw_local_booleans():
        box = layout.box()
        box.label(text='Local Boolean')

        if local_booleans['Hyper Cut']:
            col = box.column(align=True)

            for mod in local_booleans['Hyper Cut']:
                row = col.row(align=True)

                icon = 'HIDE_OFF' if mod.object.visible_get() else 'HIDE_ON'
                op = row.operator('machin3.change_local_boolean', text="", icon=icon)
                op.boolean_type = 'Hyper Cut'
                op.modname = mod.name
                op.mode = 'HIDE'

                split = row.split(factor=0.7, align=True)
                op = split.operator('machin3.change_local_boolean', text=mod.name, emboss=mod.show_viewport)
                op.boolean_type = 'Hyper Cut'
                op.modname = mod.name
                op.mode = 'ACTIVATE'

                op = split.operator('machin3.change_local_boolean', text=mod.solver.title())
                op.boolean_type = 'Hyper Cut'
                op.modname = mod.name
                op.mode = 'SOLVER'

                op = row.operator('machin3.change_local_boolean', text="", icon='LONGDISPLAY')
                op.boolean_type = 'Hyper Cut'
                op.modname = mod.name
                op.mode = 'SORT'

                op = row.operator('machin3.change_local_boolean', text="", icon='IMPORT')
                op.boolean_type = 'Hyper Cut'
                op.modname = mod.name
                op.mode = 'APPLY'

                op = row.operator('machin3.change_local_boolean', text="", icon='X')
                op.boolean_type = 'Hyper Cut'
                op.modname = mod.name
                op.mode = 'REMOVE'

        if local_booleans['Hyper Bevel']:
            col = box.column(align=True)

            for mod in local_booleans['Hyper Bevel']:
                row = col.row(align=True)

                icon = 'HIDE_OFF' if mod.object.visible_get() else 'HIDE_ON'
                op = row.operator('machin3.change_local_boolean', text="", icon=icon)
                op.boolean_type = 'Hyper Bevel'
                op.modname = mod.name
                op.mode = 'HIDE'

                split = row.split(factor=0.7, align=True)
                op = split.operator('machin3.change_local_boolean', text=mod.name, emboss=mod.show_viewport)
                op.boolean_type = 'Hyper Bevel'
                op.modname = mod.name
                op.mode = 'ACTIVATE'

                op = split.operator('machin3.change_local_boolean', text=mod.solver.title())
                op.boolean_type = 'Hyper Bevel'
                op.modname = mod.name
                op.mode = 'SOLVER'

                op = row.operator('machin3.change_local_boolean', text="", icon='LONGDISPLAY')
                op.boolean_type = 'Hyper Bevel'
                op.modname = mod.name
                op.mode = 'SORT'

                op = row.operator('machin3.change_local_boolean', text="", icon='IMPORT')
                op.boolean_type = 'Hyper Bevel'
                op.modname = mod.name
                op.mode = 'APPLY'

                op = row.operator('machin3.change_local_boolean', text="", icon='X')
                op.boolean_type = 'Hyper Bevel'
                op.modname = mod.name
                op.mode = 'REMOVE'

        if local_booleans['Other']:
            col = box.column(align=True)

            for mod in local_booleans['Other']:
                row = col.row(align=True)

                icon = 'HIDE_OFF' if mod.object.visible_get() else 'HIDE_ON'
                op = row.operator('machin3.change_local_boolean', text="", icon=icon)
                op.boolean_type = 'Other'
                op.modname = mod.name
                op.mode = 'HIDE'

                icon = 'MOD_WIREFRAME' if mod.object.display_type == 'BOUNDS' else 'SHADING_WIRE'
                op = row.operator('machin3.change_local_boolean', text="", icon=icon)
                op.boolean_type = 'Other'
                op.modname = mod.name
                op.mode = 'WIRE'

                split = row.split(factor=0.7, align=True)
                op = split.operator('machin3.change_local_boolean', text=mod.name, emboss=mod.show_viewport)
                op.boolean_type = 'Other'
                op.modname = mod.name
                op.mode = 'ACTIVATE'

                op = split.operator('machin3.change_local_boolean', text=mod.solver.title())
                op.boolean_type = 'Other'
                op.modname = mod.name
                op.mode = 'SOLVER'

                op = row.operator('machin3.change_local_boolean', text="", icon='LONGDISPLAY')
                op.boolean_type = 'Other'
                op.modname = mod.name
                op.mode = 'SORT'

                op = row.operator('machin3.change_local_boolean', text="", icon='IMPORT')
                op.boolean_type = 'Other'
                op.modname = mod.name
                op.mode = 'APPLY'

                op = row.operator('machin3.change_local_boolean', text="", icon='X')
                op.boolean_type = 'Other'
                op.modname = mod.name
                op.mode = 'REMOVE'

    def draw_mirror():
        box = layout.box()
        box.label(text='Mirror')

        col = box.column(align=True)
        for mod in mirrors:
            row = col.row(align=True)

            split = row.split(factor=0.7, align=True)

            op = split.operator('machin3.change_mirror', text=mod.name, emboss=mod.show_viewport)
            op.modname = mod.name
            op.mode = 'ACTIVATE'

            op = split.operator('machin3.change_mirror', text="X", emboss=mod.use_axis[0])
            op.modname = mod.name
            op.mode = 'X'

            op = split.operator('machin3.change_mirror', text="Y", emboss=mod.use_axis[1])
            op.modname = mod.name
            op.mode = 'Y'

            op = split.operator('machin3.change_mirror', text="Z", emboss=mod.use_axis[2])
            op.modname = mod.name
            op.mode = 'Z'

            op = row.operator('machin3.change_mirror', text="", icon='IMPORT')
            op.modname = mod.name
            op.mode = 'APPLY'

            op = row.operator('machin3.change_mirror', text="", icon='X')
            op.modname = mod.name
            op.mode = 'REMOVE'

    def draw_array():
        box = layout.box()
        box.label(text='Legacy Array')

        col = box.column(align=True)
        for mod in arrays:
            row = col.row(align=True)

            if 'Radial' in mod.name:
                icon = 'HIDE_OFF' if mod.offset_object.visible_get() else 'HIDE_ON'
                op = row.operator('machin3.change_array', text="", icon=icon)
                op.modname = mod.name
                op.mode = 'HIDE'

            split = row.split(factor=0.7, align=True)

            op = split.operator('machin3.change_array', text=mod.name, emboss=mod.show_viewport)
            op.modname = mod.name
            op.mode = 'ACTIVATE'

            split.prop(mod, 'count', text="")

            op = row.operator('machin3.change_array', text="", icon='IMPORT')
            op.modname = mod.name
            op.mode = 'APPLY'

            op = row.operator('machin3.change_array', text="", icon='X')
            op.modname = mod.name
            op.mode = 'REMOVE'

    def draw_hyper_array():
        box = layout.box()
        box.label(text='Hyper Array')

        col = box.column(align=True)
        for mod in hyper_arrays:
            row = col.row(align=True)

            if is_radial_array(mod) and (modobj := get_mod_input(mod, 'Origin')):
                icon = 'HIDE_OFF' if modobj.visible_get() else 'HIDE_ON'
                op = row.operator('machin3.change_hyper_array', text="", icon=icon)
                op.modname = mod.name
                op.mode = 'HIDE'

            split = row.split(factor=0.7, align=True)

            op = split.operator('machin3.change_hyper_array', text=mod.name, emboss=mod.show_viewport)
            op.modname = mod.name
            op.mode = 'ACTIVATE'

            identifier = get_nodegroup_input_identifier(mod.node_group, 'Count')[0]
            split.prop(mod, f'["{identifier}"]', text="")  # see https://blender.stackexchange.com/questions/222535/how-to-draw-inputs-from-geometry-nodes-modifier-in-a-panel and the following comment below as well

            op = row.operator('machin3.change_hyper_array', text="", icon='IMPORT')
            op.modname = mod.name
            op.mode = 'APPLY'

            op = row.operator('machin3.change_hyper_array', text="", icon='X')
            op.modname = mod.name
            op.mode = 'REMOVE'

    def draw_others():
        box = layout.box()
        box.label(text='Others')

        col = box.column(align=True)

        for mod in others:
            row = col.row(align=True)

            if mod.type in ['SUBSURF', 'DISPLACE', 'WELD']:
                split = row.split(factor=0.7, align=True)
                op = split.operator('machin3.change_other', text=mod.name, emboss=mod.show_viewport)
                op.modname = mod.name
                op.mode = 'ACTIVATE'

            else:
                op = row.operator('machin3.change_other', text=mod.name, emboss=mod.show_viewport)
                op.modname = mod.name
                op.mode = 'ACTIVATE'

            if mod.type == 'SUBSURF':
                split.prop(mod, 'levels', text='')

            elif mod.type == 'DISPLACE':
                split.prop(mod, 'mid_level', text='')

            elif mod.type == 'WELD':
                split.prop(mod, 'merge_threshold', text='')

            op = row.operator('machin3.change_other', text="", icon='IMPORT')
            op.modname = mod.name
            op.mode = 'APPLY'

            op = row.operator('machin3.change_other', text="", icon='X')
            op.modname = mod.name
            op.mode = 'REMOVE'

    layout = self.layout
    layout.label(text='Object and Modifiers', icon='GRIP')

    active = context.active_object

    last = bpy.types.MACHIN3_OT_hyper_cursor_object.last

    if last and bpy.data.objects.get(last):
        column = layout.column()
        column.scale_y = 1.2
        op = column.operator('machin3.select_object', text=last, icon='LOOP_BACK')
        op.objname = last

    column = layout.column()

    row = column.row()

    row.prop(active, 'name', text='')
    row.operator('machin3.duplicate_object', text='Duplicate')

    if active.HC.backupCOL:
        box = layout.box()
        box.label(text='Backups')

        col = box.column(align=True)

        for idx, bc in enumerate(active.HC.backupCOL):
            row = col.row(align=True)
            row.prop(bc, 'name', text='')

            op = row.operator('machin3.change_backup', text="", icon='FILE_REFRESH')
            op.index = idx
            op.name = bc.name
            op.mode = 'RECOVER'

            op = row.operator('machin3.change_backup', text="", icon='X')
            op.index = idx
            op.name = bc.name
            op.mode = 'REMOVE'

    booleans = [mod for mod in active.modifiers if mod.type == 'BOOLEAN']
    remote_booleans = remote_boolean_poll(context, active)
    local_booleans = local_boolean_poll(context, active, dictionary=True)

    edgebevels = edgebevel_poll(context, active)
    solidifies = solidify_poll(context, active)

    if active.modifiers:
        box = layout.box()
        box.label(text='Modifiers')

        col = box.column(align=True)

        split = col.split(factor=0.2, align=True)
        split.label(text='All')

        row = split.row(align=True)
        op = row.operator('machin3.toggle_all_modifiers', text='Toggle', icon='RESTRICT_VIEW_OFF')
        op.active_only = True
        op = row.operator('machin3.apply_all_modifiers', text='Apply', icon='IMPORT')
        op.active_only = True
        op = row.operator('machin3.remove_all_modifiers', text='Remove', icon='X')
        op.active_only = True

        if booleans:
            split = col.split(factor=0.2, align=True)
            split.label(text='Boolean')

            row = split.row(align=True)
            row.scale_y = 1.2
            row.operator('machin3.remove_unused_booleans', text='Remove Unused', icon='MOD_BOOLEAN')

    if edgebevels:
        draw_edge_bevels()

    if solidifies:
        draw_solidifies()

    if remote_booleans:
        draw_remote_booleans()

    if any(local_booleans.values()):
        draw_local_booleans()

    mirrors = mirror_poll(context, active)

    if mirrors:
        draw_mirror()

    arrays = array_poll(context, active)

    if arrays:
        draw_array()

    hyper_arrays = hyper_array_poll(context, active)

    if hyper_arrays:
        draw_hyper_array()

    others = other_poll(context, active)

    if others:
        draw_others()

def draw_geo_gizmo_panel(context, layout):
    layout.label(text='Object Type and Geometry Gizmos', icon='GRIP')

    column = layout.column(align=True)

    active = context.active_object

    split = column.split(factor=0.2, align=True)
    split.label(text='Type')
    row = split.row(align=True)
    row.prop(active.HC, 'objtype_without_none', expand=True)

    split = column.split(factor=0.2, align=True)
    split.label(text='Mode')
    row = split.row(align=True)
    row.prop(active.HC, 'geometry_gizmos_edit_mode', expand=True)

    column = layout.column(align=True)

    if active.HC.objtype == 'CUBE':
        split = column.split(factor=0.35, align=True)
        split.label(text='Polygons')
        split.label(text=str(len(active.data.polygons)))

        split = column.split(factor=0.35, align=True)
        split.label(text='Polygon Limit')
        split.prop(active.HC, 'geometry_gizmos_show_cube_limit', text='')

        if active.HC.geometry_gizmos_edit_mode == 'EDIT':
            if len(active.data.polygons) <= active.HC.geometry_gizmos_show_cube_limit:
                column = layout.column(align=True)

                split = column.split(factor=0.35, align=True)
                split.label(text='Gizmo Scale')
                split.prop(active.HC, 'geometry_gizmos_scale', text='')

                split = column.split(factor=0.35, align=True)
                split.label(text='Edge Thickness')
                split.prop(active.HC, 'geometry_gizmos_edge_thickness', text='')

                split = column.split(factor=0.35, align=True)
                split.label(text='Face Tween')
                split.prop(active.HC, 'geometry_gizmos_face_tween', text='')

    elif active.HC.objtype == 'CYLINDER':
        split = column.split(factor=0.35, align=True)
        split.label(text='Edges')
        split.label(text=str(len(active.data.edges)))

        split = column.split(factor=0.35, align=True)
        split.label(text='Edge Limit')
        split.prop(active.HC, 'geometry_gizmos_show_cylinder_limit', text='')

        if active.HC.geometry_gizmos_edit_mode == 'EDIT':
            if len(active.data.edges) <= active.HC.geometry_gizmos_show_cylinder_limit:
                column = layout.column(align=True)

                split = column.split(factor=0.35, align=True)
                split.label(text='Gizmo Scale')
                split.prop(active.HC, 'geometry_gizmos_scale', text='')

                split = column.split(factor=0.35, align=True)
                split.label(text='Edge Thickness')
                split.prop(active.HC, 'geometry_gizmos_edge_thickness', text='')

                split = column.split(factor=0.35, align=True)
                split.label(text='Face Tween')
                split.prop(active.HC, 'geometry_gizmos_face_tween', text='')
