import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty, FloatProperty, IntProperty
import rna_keymap_ui
import os
from . import bl_info
from . utils.registration import get_path, get_name, get_addon
from . utils import ui
from . utils.draw import draw_split_row
from . registration import keys as keysdict
from . utils.system import get_bl_info_from_file, remove_folder, get_update_files
from . items import prefs_tab_items, keymap_folds

tool_keymaps = ['3D View Tool: Object, Hyper Cursor',
                '3D View Tool: Edit Mesh, Hyper Cursor']

tool_keymaps_mapping = {('machin3.tool_hyper_cursor', 'OBJECT'): tool_keymaps[0],
                        ('machin3.tool_hyper_cursor', 'EDIT_MESH'): tool_keymaps[1]}

hud_shadow_items = [('0', '0', "Don't Blur Shadow"),
                    ('3', '3', 'Shadow Blur Level 3'),
                    ('5', '5', 'Shadow Blur level 5')]

machin3tools = None
meshmachine = None

class HyperCursorPreferences(bpy.types.AddonPreferences):
    path = get_path()
    bl_idname = get_name()

    def update_update_path(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.update_path:
            if os.path.exists(self.update_path):
                filename = os.path.basename(self.update_path)

                if filename.endswith('.zip'):
                    split = filename.split('_')

                    if len(split) == 2:
                        addon_name, tail = split

                        if addon_name == bl_info['name']:
                            split = tail.split('.')

                            if len(split) >= 3:
                                dst = os.path.join(self.path, '_update')

                                from zipfile import ZipFile

                                with ZipFile(self.update_path, mode="r") as z:
                                    print(f"INFO: extracting {addon_name} update to {dst}")
                                    z.extractall(path=dst)

                                blinfo = get_bl_info_from_file(os.path.join(dst, addon_name, '__init__.py'))

                                if blinfo:
                                    self.update_msg = f"{blinfo['name']} {'.'.join(str(v) for v in blinfo['version'])} is ready to be installed."

                                else:
                                    remove_folder(dst)

            self.avoid_update = True
            self.update_path = ''

    update_path: StringProperty(name="Update File Path", subtype="FILE_PATH", update=update_update_path)
    update_msg: StringProperty(name="Update Message")

    registration_debug: BoolProperty(name="Addon Terminal Registration Output", default=True)

    blendulate_segment_count: IntProperty(name="Blendulate default Segment Count", description="Use this many Segments, when invoking Blendulate with a single Point selection", default=6, min=0)
    ray_vis_hide_cutters: BoolProperty(name="Hide Boolean Objects using Ray Visibility Properties", description="If this is disabled, Boolean Objects such as those created by HyperCursor or HyperBevel, may still appear when Viewport Rendering with Cycles, despite being hidden from Rendering", default=True)
    avoid_all_toggling_autosmooth: BoolProperty(name="Avoid all-toggling AutoSmooth in HyperMod", default=True)

    cast_flick_distance: IntProperty(name="Cursor Cast Flick Distance", default=75, min=20, max=1000)
    show_sidebar_panel: BoolProperty(name="Show Sidebar Panel", default=True)
    show_mod_panel: BoolProperty(name="Show HyperCursor Modifier Buttons in Blender's Modifier Panel", default=True)

    modal_hud_scale: FloatProperty(name="HUD Scale", default=1, min=0.5, max=10)
    modal_hud_timeout: FloatProperty(name="HUD Timeout", default=1, min=0.1, max=10)
    modal_hud_shadow: BoolProperty(name="HUD Shadow", description="HUD Shadow", default=False)
    modal_hud_shadow_blur: EnumProperty(name="HUD Shadow Blur", items=hud_shadow_items, default='3')
    modal_hud_shadow_offset: IntProperty(name="HUD Shadow Offset", default=1, min=0)

    preferred_default_catalog: StringProperty(name="Preferred Default Catalog", default="Insets")
    preferred_default_catalog_curve: StringProperty(name="Preferred Default Catalog for Curves", default="Profiles (Bevel)")
    avoid_append_reuse_import_method: BoolProperty(name="Avoid Append Reuse Import Method", description="If enabled, HyperCursor will try to switch to the Append import method, when Append Reuse is set", default=True)
    skip_changing_import_method: StringProperty(name="Skip Changing Import Method on these Workspaces", default="Shading, Material, World, Rendering")

    geometry_gizmos_scale: FloatProperty(name="Global Geometry Gizmos Scale", default=1, min=0.5, max=10)
    show_generic_gizmo_details: BoolProperty(name="Show Generic Gizmo Keymap Details", default=False)
    show_hypermod_gizmo: BoolProperty(name="Show HyperMod Gizmo", default=True)
    show_machin3tools_mirror_gizmo: BoolProperty(name="Show MACHIN3tools Mirror Gizmo", default=False)
    show_meshmachine_symmetrize_gizmo: BoolProperty(name="Show MESHmachine Symmetrize Gizmo", default=True)

    show_world_mode: BoolProperty(name="Show World Mode", description="Show World Mode Toggle", default=True)
    show_hints: BoolProperty(name="Show Hints", description="Show Hint when Gizmo is disabled or when in Pipe Mode", default=True)
    show_help: BoolProperty(name="Show Help", description="Show Help Menu Button", default=True)
    show_update_available: BoolProperty(name="Show Update Available", description="Show Update Available", default=True)

    update_available: BoolProperty(name="Update is available", default=False)

    def update_show_update(self, context):
        if self.show_update:
            get_update_files(force=True)

    show_update: BoolProperty(default=False, update=update_show_update)
    avoid_update: BoolProperty(default=False)
    tabs: EnumProperty(name="Tabs", items=prefs_tab_items, default="SETTINGS")
    fold_addon: BoolProperty(name="Fold Addon Settings", default=False)
    fold_addon_defaults: BoolProperty(name="Fold Addon Defaults Settings", default=True)
    fold_interface: BoolProperty(name="Fold Interface Settings", default=False)
    fold_interface_tool_header: BoolProperty(name="Fold Interface Tool Header Settings", default=True)
    fold_interface_HUD: BoolProperty(name="Fold Interface HUD Settings", default=True)
    fold_interface_gizmos: BoolProperty(name="Fold Interface Gizmos Settings", default=False)
    fold_assets: BoolProperty(name="Fold Asset Settings", default=False)
    fold_assets_import: BoolProperty(name="Fold Asset Import Settings", default=True)
    fold_assets_creation: BoolProperty(name="Fold Asset Creation Settings", default=True)
    fold_keymaps_tool: BoolProperty(name="Fold Tool Keymaps", default=False)
    fold_keymaps_toolbar: BoolProperty(name="Fold Toolbar Keymaps", default=False)
    fold_object_mode_tool_keymaps: BoolProperty(name="Fold Object Mode Tool Keymaps", default=False)
    fold_edit_mode_tool_keymaps: BoolProperty(name="Fold Object Mode Tool Keymaps", default=False)
    fold_keymaps_tool_object_1: BoolProperty(name="Fold Keymaps", default=True)
    fold_keymaps_tool_object_4: BoolProperty(name="Fold Keymaps", default=False)
    fold_keymaps_tool_object_9: BoolProperty(name="Fold Keymaps", default=True)
    fold_keymaps_tool_object_11: BoolProperty(name="Fold Keymaps", default=True)
    fold_keymaps_tool_object_13: BoolProperty(name="Fold Keymaps", default=True)
    fold_keymaps_tool_object_17: BoolProperty(name="Fold Keymaps", default=True)
    fold_keymaps_tool_object_18: BoolProperty(name="Fold Keymaps", default=True)
    fold_keymaps_tool_object_21: BoolProperty(name="Fold Keymaps", default=True)
    fold_keymaps_tool_object_26: BoolProperty(name="Fold Keymaps", default=True)
    fold_keymaps_tool_object_28: BoolProperty(name="Fold Keymaps", default=True)
    fold_keymaps_tool_edit_mesh_1: BoolProperty(name="Fold Keymaps", default=True)
    fold_keymaps_tool_edit_mesh_4: BoolProperty(name="Fold Keymaps", default=True)
    fold_keymaps_tool_edit_mesh_6: BoolProperty(name="Fold Keymaps", default=True)
    fold_keymaps_tool_edit_mesh_8: BoolProperty(name="Fold Keymaps", default=True)
    fold_keymaps_tool_edit_mesh_10: BoolProperty(name="Fold Keymaps", default=True)
    fold_keymaps_tool_edit_mesh_14: BoolProperty(name="Fold Keymaps", default=True)
    def draw(self, context):
        layout = self.layout
        column = layout.column()

        wm = context.window_manager
        kc = wm.keyconfigs.user

        self.draw_update_available(column)
        self.draw_update(column)

        column.separator()

        row = column.row(align=True)
        row.prop(self, 'tabs', expand=True)

        if self.tabs == 'SETTINGS':

            panel = ui.get_panel_fold(layout, data=(self, 'fold_addon'), text='Addon', align=False, default_closed=False)
            if panel:
                self.draw_addon(panel)

                sub_panel = ui.get_panel_fold(panel, data=(self, 'fold_addon_defaults'), text='Defaults', align=False, default_closed=True)
                if sub_panel:
                    self.draw_defaults(sub_panel)

            panel = ui.get_panel_fold(layout, data=(self, 'fold_interface'), text='Interface', align=False, default_closed=False)
            if panel:

                self.draw_properties_panel(panel)

                sub_panel = ui.get_panel_fold(panel, data=(self, 'fold_interface_tool_header'), text='Tool Header', align=False, default_closed=True)
                if sub_panel:
                    self.draw_tool_header(sub_panel)

                sub_panel = ui.get_panel_fold(panel, data=(self, 'fold_interface_HUD'), text='HUD', align=False, default_closed=True)
                if sub_panel:
                    self.draw_HUD(sub_panel)

                sub_panel = ui.get_panel_fold(panel, data=(self, 'fold_interface_gizmos'), text='Gizmos', align=False, default_closed=False)
                if sub_panel:
                    self.draw_gizmos(sub_panel, kc)

            panel = ui.get_panel_fold(layout, data=(self, 'fold_assets'), text='Assets', align=False, default_closed=False)
            if panel:

                self.draw_example_assets(context, panel)

                sub_panel = ui.get_panel_fold(panel, data=(self, 'fold_assets_import'), text='Asset Import', align=False, default_closed=True)
                if sub_panel:
                    self.draw_asset_import(sub_panel)

                sub_panel = ui.get_panel_fold(panel, data=(self, 'fold_assets_creation'), text='Asset Creation', align=False, default_closed=True)
                if sub_panel:
                    self.draw_asset_creation(sub_panel)

        elif self.tabs == 'KEYMAPS':

            panel = ui.get_panel_fold(layout, data=(self, 'fold_keymaps_tool'), text='HyperCursor Tool Keymaps', align=False, default_closed=False)
            if panel:
                self.draw_tool_keymaps(panel, kc)

            panel = ui.get_panel_fold(layout, data=(self, 'fold_keymaps_toolbar'), text='HyperCursor Toolbar Popup Keymaps', align=False, default_closed=True)
            if panel:
                self.draw_toolbar_keymaps(panel, kc)

            self.draw_keymap_reset(context, layout, kc)

    def draw_update(self, layout):
        row = layout.row()
        row.scale_y = 1.25
        row.prop(self, 'show_update', text="Install HyperCursor Update", icon='TRIA_DOWN' if self.show_update else 'TRIA_RIGHT')

        if self.show_update:
            update_files = get_update_files()

            box = layout.box()
            box.separator()

            if self.update_msg:
                row = box.row()
                row.scale_y = 1.5

                split = row.split(factor=0.4, align=True)
                split.label(text=self.update_msg, icon_value=ui.get_icon('refresh_green'))

                s = split.split(factor=0.3, align=True)
                s.operator('machin3.remove_hypercursor_update', text='Remove Update', icon='CANCEL')
                s.operator('wm.quit_blender', text='Quit Blender + Install Update', icon='FILE_REFRESH')

            else:
                b = box.box()
                col = b.column(align=True)

                row = col.row()
                row.alignment = 'LEFT'

                if update_files:
                    row.label(text="Found the following Updates in your home and/or Downloads folder: ")
                    row.operator('machin3.rescan_hypercursor_updates', text="Re-Scan", icon='FILE_REFRESH')

                    col.separator()

                    for path, tail, _ in update_files:
                        row = col.row()
                        row.alignment = 'LEFT'

                        r = row.row()
                        r.active = False

                        r.alignment = 'LEFT'
                        r.label(text="found")

                        op = row.operator('machin3.use_hypercursor_update', text=f"HyperCursor {tail}")
                        op.path = path
                        op.tail = tail

                        r = row.row()
                        r.active = False
                        r.alignment = 'LEFT'
                        r.label(text=path)

                else:
                    row.label(text="No Update was found. Neither in your Home directory, nor in your Downloads folder.")
                    row.operator('machin3.rescan_hypercursor_updates', text="Re-Scan", icon='FILE_REFRESH')

                row = box.row()

                split = row.split(factor=0.4, align=True)
                split.prop(self, 'update_path', text='')

                text = "Select HyperCursor_x.x.x.zip file"

                if update_files:
                    if len(update_files) > 1:
                        text += " or pick one from above"

                    else:
                        text += " or pick the one above"

                split.label(text=text)

            box.separator()

    def draw_update_available(self, layout):
        if self.update_available:
            split = layout.split(factor=0.4)
            split.separator()
            split.label(text="A HyperCursor Update is available!", icon_value=ui.get_icon('refresh_green'))
            layout.separator(factor=3)

    def draw_addon(self, layout):
        column = layout.column(align=True)

        draw_split_row(self, column, prop='registration_debug', label='Print Addon Registration Output in System Console')
        draw_split_row(self, column, 'show_sidebar_panel', label='Show Addon Sidebar Panel in 3D View', factor=0.202, info="Under the MACHIN3 tab!")

    def draw_defaults(self, layout):
        column = layout.column(align=True)

        draw_split_row(self, column, 'blendulate_segment_count', label='Blendulate Default Segment Count')
        draw_split_row(self, column, 'ray_vis_hide_cutters', label='Hide Boolean Operant Objects for Viewport Rendering using Cycles Ray Visibility properties')
        draw_split_row(self, column, 'avoid_all_toggling_autosmooth', label='In HyperMod, avoid toggling AutoSmooth mod, when toggling all mods via A key')

    def draw_properties_panel(self, layout):
        draw_split_row(self, layout, 'show_mod_panel', label="Show HyperCursor Modifier Buttons in Blender's Modifier Panel")

    def draw_tool_header(self, layout):
        column = layout.column(align=True)

        draw_split_row(self, column, 'show_world_mode', label="Show World Mode Toggle")
        draw_split_row(self, column, 'show_hints', label="Show Hints when Gizmo is disabled or when in Pipe Mode")
        draw_split_row(self, column, 'show_help', label="Show Help Menu Button")
        draw_split_row(self, column, 'show_update_available', label="Show Update Available Note")

    def draw_HUD(self, layout):
        column = layout.column(align=True)

        draw_split_row(self, column, 'modal_hud_scale', label='Scale')
        draw_split_row(self, column, 'modal_hud_timeout', label='Timeout', factor=0.202, info='Modulate Duraton of Fading HUDs')
        draw_split_row(self, column, 'modal_hud_shadow', label='Shadow')

        if self.modal_hud_shadow:
            row = column.split(factor=0.2, align=True)
            row.separator()
            s = row.split(factor=0.5)
            rs = s.row()
            rs.prop(self, "modal_hud_shadow_blur", expand=True)
            rs.label(text="Blur")
            rs.prop(self, "modal_hud_shadow_offset", text='')
            rs.label(text="Offset")

        draw_split_row(self, column, 'cast_flick_distance', label='Cursor Cast Flick Distance')

    def draw_gizmos(self, layout, kc):
        global machin3tools, meshmachine

        if machin3tools is None:
            machin3tools = get_addon('MACHIN3tools')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        column = layout.column(align=True)

        generic_gizmo = ui.get_keymap_item('Generic Gizmo', 'gizmogroup.gizmo_tweak')

        if generic_gizmo:
            row = column.row()
            row.prop(self, 'show_generic_gizmo_details', text='', icon='PREFERENCES', toggle=True)
            row.label(text="Generic Gizmo Keymap")

            if self.show_generic_gizmo_details:
                keylist = [{'keymap': 'Generic Gizmo', 'idname': 'gizmogroup.gizmo_tweak', "properties": None}]
                ui.draw_keymap_items(kc, keylist, column)

            if generic_gizmo.any:
                column.label(text="Generic Gizmo is properly set up to accept ALT modifer keys", icon_value=ui.get_icon('save'))

            else:
                column.separator(factor=2)

                box = column.box()
                split = box.split()

                col = split.column()
                col.label(text="Blender 3.0 introduced a change, making it impossible to ALT click Gizmos by default.")
                col.label(text="HyperCursor makes heavy use of modifier keys for gizmos, including the ALT key.")
                col.label(text="To take advantage of all features, the Generic Gizmo Keymap has to be adjusted.")
                col.label(text="See this commit and discussion for details about that change in Blender behavior:")

                row = col.row(align=True)
                row.operator('wm.url_open', text='Commit', icon='URL').url = 'https://developer.blender.org/rB83975965a797642eb0aece30c6a887061b34978d'
                row.operator('wm.url_open', text='Discussion', icon='URL').url = 'https://developer.blender.org/T93699'

                col = split.column()
                col.separator(factor=2.5)
                col.scale_y = 2
                col.operator('machin3.setup_generic_gizmo_keymap', text='Setup Generic Gizmo', icon='EVENT_ALT')

            column.separator(factor=2)

        draw_split_row(self, column, 'geometry_gizmos_scale', label='Global Geometry Gizmos Scale')

        column.separator()
        draw_split_row(self, column, 'show_hypermod_gizmo', label="Show HyperMod Object Gizmo", factor=0.202, info="It can alternatively be invoked purely via Keymaps too")

        if meshmachine:
            draw_split_row(self, column, 'show_meshmachine_symmetrize_gizmo', label="Show MESHmachine Symmetrize Object Gizmo", factor=0.202, info="Allows for Mesh Symmetrizing from Object Mode!")

        if machin3tools:
            draw_split_row(self, column, 'show_machin3tools_mirror_gizmo', label="Show MACHIN3tools Mirror Object Gizmo", factor=0.202, info="Usually it's called via Keymap, so I prefer having this disabled")

    def draw_example_assets(self, context, layout):
        column = layout.column(align=True)

        asset_path = os.path.join(self.path, 'assets')
        asset_libraries = [data.path for data in context.preferences.filepaths.asset_libraries.values()]

        if asset_path in asset_libraries:
            row = column.split(factor=0.603)
            row.label(text="HyperCursor Example Assets are ready to use!", icon_value=ui.get_icon('save'))

            if context.preferences.is_dirty and not context.preferences.use_preferences_save:
                row.label(text="Save your preferences!", icon='INFO')

        else:
            split = column.split()

            col = split.column()
            col.label(text="HyperCursor supplies a few Example Assets, such as Insets and Profiles for Bevels and Pipes.")
            col.label(text="To use them, add their location (in the HyperCursor's addon folder) to your list of libraries.")

            col = split.column()
            col.scale_y = 2
            col.operator('machin3.add_hyper_cursor_assets_path', text='Add HyperCursor Example Assts to Library', icon='MONKEY')

    def draw_asset_import(self, layout):
        column = layout.column(align=True)

        draw_split_row(self, column, 'avoid_append_reuse_import_method', label="Avoid 'Append Reuse' when importing Assets", factor=0.202, info="There can be issues with bevel mods, when importing object assets whose meshes have been changed")

        if self.avoid_append_reuse_import_method:
            draw_split_row(self, column, 'skip_changing_import_method', label="Avoid Changing Import Method on these Workspaces though")

    def draw_asset_creation(self, layout):
        column = layout.column(align=True)

        draw_split_row(self, column, 'preferred_default_catalog', label="Preferred Default Catalog", info="must exist already")
        draw_split_row(self, column, 'preferred_default_catalog_curve', label="Preferred Default Catalog for Curves", info="👆")

    def draw_tool_keymaps(self, layout, kc):
        column = layout.column(align=True)

        column.separator(factor=2)
        row = column.row()
        row.alignment = 'CENTER'
        row.label(text="Tool Keymaps only work, when the HyperCursor Tool is active!", icon='INFO')
        column.separator(factor=2)

        for keymap in tool_keymaps:
            km = kc.keymaps.get(keymap)
            prop, mode, mode_pretty = ('fold_object_mode_tool_keymaps', 'OBJECT', 'Object Mode') if keymap == '3D View Tool: Object, Hyper Cursor' else ('fold_edit_mode_tool_keymaps', 'EDIT_MESH', 'Edit Mesh Mode') if '3D View Tool: Edit Mesh, Hyper Cursor' else None

            if km and prop:
                panel = ui.get_panel_fold(layout, data=(self, prop), text=mode_pretty, align=False, default_closed=False)
                if panel:
                    sub_panel = None

                    for kmi in reversed(km.keymap_items):

                        if text := keymap_folds[mode].get(kmi.id, None):
                            sub_panel = ui.get_panel_fold(panel, data=(self, f"fold_keymaps_tool_{mode.lower()}_{kmi.id}"), text=text, align=True, default_closed=not (kmi.id == 4 and mode == 'OBJECT'))
                        if sub_panel:
                            rna_keymap_ui.draw_kmi(["ADDON", "USER", "DEFAULT"], kc, km, kmi, sub_panel, 0)

    def draw_toolbar_keymaps(self, layout, kc):
        column = layout.column(align=True)
        keylist = keysdict['TOOLBAR']

        column.separator(factor=2)
        row = column.row()
        row.alignment = 'CENTER'
        row.label(text="Toolbar Popup Keymaps only work, with the Tooolbar Popup open!", icon='INFO')
        column.separator(factor=2)

        ui.draw_keymap_items(kc, keylist, column)

    def draw_keymap_reset(self, context, layout, kc):
        if ui.get_modified_keymap_items(context):
            column = layout.column(align=True)
            row = column.row(align=True)
            row.scale_y = 1.5
            row.alert = True

            row.operator('machin3.reset_hyper_cursor_keymaps', text='Reset Keymaps to Default')
