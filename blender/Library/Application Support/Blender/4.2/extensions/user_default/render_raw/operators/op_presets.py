'''
Copyright (C) 2024 Orange Turbine
https://orangeturbine.com
orangeturbine@cgcookie.com

This file is part of the Render Raw add-on, created by Jonathan Lampel for Orange Turbine.

All code distributed with this add-on is open source as described below.

Render Raw is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <https://www.gnu.org/licenses/>.
'''

import bpy, os, json, shutil, warnings

from ..preferences import get_prefs
from ..utilities.conversions import map_range
from ..utilities.version import get_addon_version
from ..utilities.curves import RGB_curve_default, create_curve_preset, set_curve_node
from ..update_nodes import RR_node_name, reset_RR, update_color_panel, update_effects_panel, update_value_panel, update_exposure

blank_preset = 'NONE'

preset_settings_to_skip = ['enable_RR', 'view_transform', 'prev_look', 'prev_use_curves', 'prev_exposure', 'preset', 'presets', 'preset_list', 'preset_name']

default_path = bpy.path.native_pathsep(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        '..', 'assets', 'presets')
)

def get_path(context):
    prefs = get_prefs(context)
    prefs_path = prefs.preset_path
    if prefs_path and os.path.isdir(prefs_path):
        return prefs_path
    else:
        return default_path

def get_preset_files(context, path):
    return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

def copy_default_presets(context):
    prefs = get_prefs(context)
    path = prefs.preset_path
    if os.path.isdir(path):
        for file in get_preset_files(context, default_path):
            shutil.copy2(os.path.join(default_path, file), path)

def get_preset_list(preset_files):
    preset_names = [blank_preset]
    for file in preset_files:
        if file.endswith('.rr'):
            preset_names.append(file.replace('.rr', ''))
    return preset_names

def preset_items(self, context):
    if hasattr(context.scene, 'render_raw_presets'):
        presets = []
        for preset_name in context.scene.render_raw_presets.keys():
            if preset_name == blank_preset:
                presets.append((blank_preset, 'None', ''))
            else:
                presets.append((preset_name, preset_name, ''))
        return presets
    else:
        return [(blank_preset, 'None', '')]

def refresh_presets(context):
    path = get_path(context)
    prev_preset = context.scene.render_raw.preset
    context.scene.render_raw_presets.clear()
    preset_list = get_preset_list(get_preset_files(context, path))

    for preset in preset_list:
        if preset not in context.scene.render_raw_presets.keys():
            new_preset = context.scene.render_raw_presets.add()
            new_preset.name = preset

    if prev_preset not in preset_list:
        context.scene.render_raw.preset = blank_preset

def get_preset_settings(self, context):      
    preset = {}

    settings = context.scene.render_raw
    for key in settings.keys():
        if key not in preset_settings_to_skip:
            if key == 'exposure' and not self.include_exposure:
                pass
            elif settings.bl_rna.properties[key].subtype == 'COLOR':
                preset[key] = [settings[key][0], settings[key][1], settings[key][2]]
            else:
                preset[key] = settings[key]

    nodes = bpy.data.node_groups[RR_node_name].nodes
    preset['value_curves'] = create_curve_preset(nodes['Curves'])
    color_balance_nodes = bpy.data.node_groups['.RR_color_balance'].nodes
    preset['highlight_blending'] = color_balance_nodes['Highlight Color'].blend_type
    preset['midtone_blending'] = color_balance_nodes['Midtone Color'].blend_type
    preset['shadow_blending'] = color_balance_nodes['Shadow Color'].blend_type

    if self.include_gamma:
        preset['gamma'] = context.scene.view_settings.gamma

    preset['version'] = get_addon_version()

    return preset

def write_preset(context, preset, preset_name):
    path = get_path(context)
    with open(
        os.path.join(path, f"{preset_name}.rr"), "w"
    ) as file:
        file.write(json.dumps(preset, indent=4))

def load_preset(context, preset_name):
    path = get_path(context)
    with open(
        os.path.join(path, f"{preset_name}.rr"), "r"
    ) as file:
        return json.load(file)

def remove_preset(context):
    path = get_path(context)
    os.remove(
        os.path.join(path, f"{context.scene.render_raw.preset}.rr")
    )

def apply_preset(self, context):
    reset_RR(context)

    settings = context.scene.render_raw
    if settings.preset != blank_preset:
        nodes = bpy.data.node_groups[RR_node_name].nodes
        color_balance_nodes = bpy.data.node_groups['.RR_color_balance'].nodes
        preset = load_preset(context, settings.preset)
        preset_keys = preset.keys()

        for key in preset_keys:
            if key =='gamma':
                context.scene.view_settings.gamma = preset[key]
            elif key == 'value_curves': 
                set_curve_node(nodes['Curves'], preset[key])
            elif key == 'highlight_blending':
                color_balance_nodes['Highlight Color'].blend_type = preset[key]
            elif key == 'midtone_blending':
                color_balance_nodes['Midtone Color'].blend_type = preset[key]
            elif key == 'shadow_blending':
                color_balance_nodes['Shadow Color'].blend_type = preset[key]
            elif hasattr(settings, key):
                settings[key] = preset[key]

        # Handle conversions from previous RR versions
        if 'version' not in preset_keys: 
            print('Converting Render Raw preset from < v1.0.0 to v1.0.0')
            for key in preset_keys:
                if hasattr(settings, key):
                    if key == 'blacks':
                        settings[key] = map_range(preset[key], 0, 1, 0.5, -0.5)
                    if key == 'whites':
                        settings[key] = map_range(preset[key], 0, 1, 0.5, -0.5)
                    if key == 'highlights':
                        settings[key] = map_range(preset[key], 0, 1, -0.5, 0.5)
                    if key == 'shadows':
                        settings[key] = map_range(preset[key], 0, 1, -0.5, 0.5)

    update_exposure(self, context)
    update_value_panel(self, context)
    update_color_panel(self, context)
    update_effects_panel(self, context)


class Presets(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()

class SetPresetDirectory(bpy.types.Operator):
    bl_label = 'Set Presets Folder'
    bl_idname = "render.render_raw_set_preset_directory"
    bl_options = {'REGISTER'}

    directory: bpy.props.StringProperty(
        name = 'Path'
    )
    filter_folder: bpy.props.BoolProperty(
        default = True,
        options={"HIDDEN"}
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        prefs = get_prefs(context)
        prefs.preset_path = self.directory
        copy_default_presets(context)
        return{'FINISHED'}

class SavePreset(bpy.types.Operator):
    bl_label = 'Save Preset'
    bl_idname = "render.render_raw_save_preset"
    bl_description = (
        "Save the current Render Raw settings as a preset which can be used in any other project. "
        "A preset folder must be specified in the add-on preferences for this to be enabled"
    )

    preset_name: bpy.props.StringProperty(
        name = 'Name',
        default = 'My Preset'
    )
    include_exposure: bpy.props.BoolProperty(
        name = 'Exposure',
        default = False
    )
    include_gamma: bpy.props.BoolProperty(
        name = 'Gamma',
        default = False
    )
    
    @classmethod
    def poll(self, context):
        prefs = get_prefs(context)
        prefs_path = prefs.preset_path
        return prefs_path and os.path.isdir(prefs_path)

    def draw(self, context):
        col = self.layout.column()
        col.use_property_split = True
        col.prop(self, 'preset_name')
        col.separator()
        col = self.layout.column(heading='Include')
        col.use_property_split = True
        col.prop(self, 'include_exposure')
        col.prop(self, 'include_gamma')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        if not hasattr(context.scene, 'render_raw'):
            self.report({'ERROR'}, "Preset not saved because Render Raw has not been enabled in this scene")
            return {'FINISHED'}
        preset = get_preset_settings(self, context)
        write_preset(context, preset, self.preset_name)
        refresh_presets(context)
        context.scene.render_raw.preset = self.preset_name
        return {'FINISHED'}
    
class RemovePreset(bpy.types.Operator):
    bl_label = 'Remove Render Raw Preset'
    bl_idname = 'render.render_raw_remove_preset'
    bl_description = (
        'Deletes the current preset. '
        'A preset folder must be specified in the add-on preferences for this to be enabled'
    )

    @classmethod
    def poll(self, context):
        prefs = get_prefs(context)
        prefs_path = prefs.preset_path
        return (
            context.scene.render_raw.preset != blank_preset and 
            prefs_path and os.path.isdir(prefs_path)
        )

    def draw(self, context):
        row = self.layout.row()
        row.label(text=f'Permanently delete {context.scene.render_raw.preset}?', icon='QUESTION')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        remove_preset(context)
        refresh_presets(context)
        return {'FINISHED'}
    
class RefreshPresets(bpy.types.Operator):
    bl_label = 'Refresh Render Raw Presets'
    bl_idname = 'render.render_raw_refresh_presets'
    bl_description = (
        'Updates all presets. '
        'A preset folder must be specified in the add-on preferences for this to be enabled'
    )
    
    @classmethod
    def poll(self, context):
        prefs = get_prefs(context)
        prefs_path = prefs.preset_path
        return prefs_path and os.path.isdir(prefs_path)

    def execute(self, context):
        refresh_presets(context)
        return {'FINISHED'}

    
classes = [SavePreset, RemovePreset, Presets, RefreshPresets, SetPresetDirectory]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.render_raw_presets = bpy.props.CollectionProperty(type=Presets)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)