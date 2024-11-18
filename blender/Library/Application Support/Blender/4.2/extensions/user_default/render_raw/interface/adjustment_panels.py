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

import bpy, gpu, os

from ..preferences import get_prefs
from ..update_nodes import RR_node_name

class PresetsMenu(bpy.types.Menu):
    bl_label = 'Render Raw Presets'
    bl_idname = 'RENDER_MT_render_raw_preset_options'

    def draw(self, context):
        col = self.layout.column()
        
        prefs = get_prefs(context)
        path = prefs.preset_path
        if path == '' or not os.path.isdir(path):
            col.label(text='Set folder in preferences', icon='ERROR')
            col.separator()

        col.operator('render.render_raw_save_preset', text='Save Preset', icon='FILE_TICK')
        col.operator('render.render_raw_refresh_presets', text='Refresh Presets', icon='FILE_REFRESH')
        col.operator('render.render_raw_remove_preset', text='Remove Preset', icon='TRASH')

def draw_presets(col, context):
    row = col.row()
    row.prop(context.scene.render_raw, 'preset', text='Preset')
    row.separator()
    row.menu('RENDER_MT_render_raw_preset_options', icon='OPTIONS', text='')

def draw_color_management_panel(self, context):
    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    enable_row = col.row(heading='Color Correction')
    enable_row.prop(context.scene.render_raw, 'enable_RR', text='Enable Render Raw')
    col.separator()
    if context.scene.render_raw.enable_RR:
        col.prop(context.scene.render_raw, 'view_transform')
        draw_presets(col, context)
        col.prop(context.scene.render_raw, 'exposure', slider=True)
        col.prop(context.scene.view_settings, 'gamma')
        if context.scene.render_raw.view_transform == 'sRGB':
            col.separator()
            hdr = col.row()
            hdr.enabled = gpu.capabilities.hdr_support_get()
            hdr.prop(context.scene.view_settings, 'use_hdr_view')
        col.separator()
        if context.area.type == 'VIEW_3D':
            col.prop(context.space_data.shading, 'use_compositor', text='Viewport')
        if bpy.app.version >= (4, 2, 0):
            device = col.row()
            device.prop(context.scene.render, 'compositor_device', text='Render', expand=True)

    else:
        col.prop(context.scene.view_settings, 'view_transform')
        col.prop(context.scene.view_settings, 'look')
        col.prop(context.scene.view_settings, 'exposure')
        col.prop(context.scene.view_settings, 'gamma')

def draw_values_panel(self, context):
    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.enabled = context.scene.render_raw.use_values and context.scene.render_raw.enable_RR
    col.separator()
    col.prop(context.scene.render_raw, 'contrast', slider=True)
    col.separator()
    col.prop(context.scene.render_raw, 'blacks', slider=True)
    col.prop(context.scene.render_raw, 'shadows', slider=True)
    col.prop(context.scene.render_raw, 'highlights', slider=True)
    col.prop(context.scene.render_raw, 'whites', slider=True)

def draw_curves_panel(self, context):
    col = self.layout.column()
    col.enabled = context.scene.render_raw.use_values and context.scene.render_raw.enable_RR
    if 'Render Raw' in [x.name for x in bpy.data.node_groups]:
        nodes = bpy.data.node_groups['Render Raw'].nodes
        col.template_curve_mapping(nodes['Curves'], "mapping", type='COLOR', levels=False, show_tone=False)
    else:
        col.template_curve_mapping(context.scene.view_settings, "curve_mapping", type='COLOR', levels=False)

def draw_colors_panel(self, context):
    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.enabled = context.scene.render_raw.use_colors
    col.prop(context.scene.render_raw, 'temperature', slider=True)
    col.prop(context.scene.render_raw, 'tint', slider=True)
    col.separator()
    col.prop(context.scene.render_raw, 'color_boost', slider=True)
    col.separator()
    col.prop(context.scene.render_raw, 'saturation', slider=True)
    col.prop(context.scene.render_raw, 'saturation_perceptual', slider=True)

def draw_color_balance_panel(self, context):
    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.enabled = context.scene.render_raw.use_colors

    col.prop(context.scene.render_raw, 'offset_color')
    col.prop(context.scene.render_raw, 'power_color')
    col.prop(context.scene.render_raw, 'slope_color')
    col.separator()

    col.prop(context.scene.render_raw, 'lift_color')
    col.prop(context.scene.render_raw, 'gamma_color')
    col.prop(context.scene.render_raw, 'gain_color')

def draw_color_blending_panel(self, context):
    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.enabled = context.scene.render_raw.use_colors

    color_balance_nodes = bpy.data.node_groups[RR_node_name].nodes['Color Balance'].node_tree.nodes

    if 'Render Raw' in [x.name for x in bpy.data.node_groups]:
        col.prop(color_balance_nodes['Shadow Color'], 'blend_type', text='Shadow Blending')
    else:
        col.prop(context.scene.render_raw, 'dummy_blending', text='Highlight Blending')
    col.prop(context.scene.render_raw, 'shadow_color')
    col.prop(context.scene.render_raw, 'shadow_range', slider=True)
    col.prop(context.scene.render_raw, 'shadow_factor', slider=True)
    col.separator()

    if 'Render Raw' in [x.name for x in bpy.data.node_groups]:
        col.prop(color_balance_nodes['Midtone Color'], 'blend_type', text='Midtone Blending')
    else:
        col.prop(context.scene.render_raw, 'dummy_blending', text='Highlight Blending')
    col.prop(context.scene.render_raw, 'midtone_color')
    col.prop(context.scene.render_raw, 'midtone_range', slider=True)
    col.prop(context.scene.render_raw, 'midtone_factor', slider=True)
    col.separator()

    if 'Render Raw' in [x.name for x in bpy.data.node_groups]:
        col.prop(color_balance_nodes['Highlight Color'], 'blend_type', text='Highlight Blending')
    else:
        col.prop(context.scene.render_raw, 'dummy_blending', text='Highlight Blending')
    col.prop(context.scene.render_raw, 'highlight_color')
    col.prop(context.scene.render_raw, 'highlight_range', slider=True)
    col.prop(context.scene.render_raw, 'highlight_factor', slider=True)

def draw_hue_hue_panel(self, context):
    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.enabled = context.scene.render_raw.use_colors
    col.prop(context.scene.render_raw, 'red_hue', slider=True)
    col.prop(context.scene.render_raw, 'orange_hue', slider=True)
    col.prop(context.scene.render_raw, 'yellow_hue', slider=True)
    col.prop(context.scene.render_raw, 'green_hue', slider=True)
    col.prop(context.scene.render_raw, 'teal_hue', slider=True)
    col.prop(context.scene.render_raw, 'blue_hue', slider=True)
    col.prop(context.scene.render_raw, 'pink_hue', slider=True)

def draw_hue_saturation_panel(self, context):
    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.enabled = context.scene.render_raw.use_colors
    col.prop(context.scene.render_raw, 'red_saturation', slider=True)
    col.prop(context.scene.render_raw, 'orange_saturation', slider=True)
    col.prop(context.scene.render_raw, 'yellow_saturation', slider=True)
    col.prop(context.scene.render_raw, 'green_saturation', slider=True)
    col.prop(context.scene.render_raw, 'teal_saturation', slider=True)
    col.prop(context.scene.render_raw, 'blue_saturation', slider=True)
    col.prop(context.scene.render_raw, 'pink_saturation', slider=True)

def draw_hue_value_panel(self, context):
    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.enabled = context.scene.render_raw.use_colors
    col.prop(context.scene.render_raw, 'red_value', slider=True)
    col.prop(context.scene.render_raw, 'orange_value', slider=True)
    col.prop(context.scene.render_raw, 'yellow_value', slider=True)
    col.prop(context.scene.render_raw, 'green_value', slider=True)
    col.prop(context.scene.render_raw, 'teal_value', slider=True)
    col.prop(context.scene.render_raw, 'blue_value', slider=True)
    col.prop(context.scene.render_raw, 'pink_value', slider=True)

def draw_value_saturation_panel(self, context):
    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.enabled = context.scene.render_raw.use_colors
    col.prop(context.scene.render_raw, 'shadow_saturation', slider=True)
    col.prop(context.scene.render_raw, 'shadow_saturation_range', slider=True)
    col.separator()
    col.prop(context.scene.render_raw, 'midtone_saturation', slider=True)
    col.prop(context.scene.render_raw, 'midtone_saturation_range', slider=True)
    col.separator()
    col.prop(context.scene.render_raw, 'highlight_saturation', slider=True)
    col.prop(context.scene.render_raw, 'highlight_saturation_range', slider=True)
    col.separator()
    col.prop(context.scene.render_raw, 'value_saturation_perceptual', slider=True)
    
def draw_details_panel(self, context):
    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.enabled = context.scene.render_raw.use_values
    col.prop(context.scene.render_raw, 'sharpness', slider=True)
    col.prop(context.scene.render_raw, 'sharpness_mask', slider=True)
    col.separator()
    col.prop(context.scene.render_raw, 'texture', slider=True)
    # col.prop(context.scene.render_raw, 'texture_color', slider=True)
    col.separator()
    col.prop(context.scene.render_raw, 'clarity', slider=True)
    col.prop(context.scene.render_raw, 'clarity_size', slider=True)

def draw_effects_panel(self, context):
    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.enabled = context.scene.render_raw.use_effects

    col.prop(context.scene.render_raw, 'distortion', slider=True)
    col.prop(context.scene.render_raw, 'dispersion', slider=True)

def draw_glare_panel(self, context):
    settings = context.scene.render_raw

    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.enabled = settings.use_effects

    col.prop(settings, 'glare', slider=True, text='Strength')
    glare = col.column()
    glare.enabled = settings.glare != 0
    glare.prop(settings, 'glare_threshold')
    glare.prop(settings, 'glare_quality')
    glare.separator()

    glare.prop(settings, 'bloom', slider=True, text='Bloom')
    bloom = glare.column()
    bloom.enabled = settings.glare != 0 and settings.bloom != 0
    if bpy.app.version >= (4, 2, 0):
        bloom.prop(settings, 'bloom_size', text='Size')
    glare.separator()

    glare.prop(settings, 'streaks', slider=True, text='Streaks')
    streaks = glare.column()
    streaks.enabled = settings.glare != 0 and settings.streaks != 0
    streaks.prop(settings, 'streak_length', slider=True, text='Streak Length')
    streaks.prop(settings, 'streak_count', text='Streak Count')
    streaks.prop(settings, 'streak_angle', text='Streak Angle')
    glare.separator()

    glare.prop(settings, 'ghosting', slider=True)

def draw_vignette_panel(self, context):
    settings = context.scene.render_raw

    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.enabled = settings.use_effects

    col.prop(context.scene.render_raw, 'vignette_value', slider=True, text='Strength')
    vig = col.column()
    vig.enabled = settings.vignette_value != 0
    vig.prop(settings, 'vignette_highlights', slider=True)
    vig.prop(settings, 'vignette_feathering', slider=True)
    vig.prop(settings, 'vignette_roundness', slider=True)
    vig.prop(settings, 'vignette_scale_x', slider=True)
    vig.prop(settings, 'vignette_scale_y', slider=True)
    vig.prop(settings, 'vignette_shift_x', slider=True)
    vig.prop(settings, 'vignette_shift_y', slider=True)
    col.separator()

def draw_grain_panel(self, context):
    settings = context.scene.render_raw

    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.enabled = settings.use_effects

    col.prop(settings, 'grain', slider=True, text='Strength')
    grain = col.column()
    grain.enabled = settings.grain != 0
    row = grain.row()
    row.prop(settings, 'grain_method', expand=True)
    grain.prop(settings, 'grain_scale', slider=True)
    grain.prop(settings, 'grain_aspect', slider=True)
    grain.prop(settings, 'grain_saturation', slider=True)
    grain.prop(settings, 'grain_steps')
    row = grain.row(heading='Animate')
    row.prop(settings, 'grain_is_animated', text='')

def draw_original_curves_panel(self, context):
        layout = self.layout
        scene = context.scene
        view = scene.view_settings
        layout.use_property_split = False
        layout.use_property_decorate = False  # No animation.
        layout.enabled = view.use_curve_mapping
        layout.template_curve_mapping(view, "curve_mapping", type='COLOR', levels=True)

def draw_original_display_panel(self, context):
    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.enabled = context.scene.view_settings.view_transform == 'Standard' and gpu.capabilities.hdr_support_get()
    col.prop(context.scene.view_settings, 'use_hdr_view')

def draw_utilities_panel(self, context):
    prefs = get_prefs(context)

    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.operator('render.render_raw_refresh_nodes', icon='FILE_REFRESH')
    col.separator()
    col.prop(context.scene.view_settings, 'view_transform', text="Scene Transform")
    col.prop(context.scene.view_settings, 'look', text="Scene Look")
    col.prop(context.scene.view_settings, 'exposure', text="Scene Exposure")
    col.separator()
    col.operator('render.render_raw_fix_scene_settings', icon='FILE_REFRESH')
    col.separator()
    col.operator('wm.url_open', text='Read the Docs', icon='HELP').url = 'https://cgcookie.github.io/render_raw/'
    col.operator('wm.url_open', text='Report an Issue', icon='ERROR').url = 'https://orangeturbine.com/p/contact'
    col.operator("wm.url_open", text='View on Blender Market', icon='IMPORT').url = 'https://blendermarket.com/products/render-raw'

def draw_scene_settings_panel(self, context):
    col = self.layout.column()
    col.use_property_split = True
    col.use_property_decorate = False

''' Properties Editor Color Management Panels '''

class RenderRawPanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw"
    bl_label = "Color Management"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    
    def draw(self, context):
        col = self.layout.column()
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(context.scene.display_settings, 'display_device')
        col.prop(context.scene.sequencer_colorspace_settings, 'name', text='Sequencer')
        col.separator()
        draw_color_management_panel(self, context)

class ValuesPanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_values"
    bl_parent_id = "RENDER_PT_render_raw"
    bl_label = ""
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'

    @classmethod
    def poll(self, context):
        return context.scene.render_raw.enable_RR

    def draw_header(self, context):
        self.layout.prop(context.scene.render_raw, 'use_values', text="")
        self.layout.label(text="Values")
        """
        row = self.layout.split(factor=0)
        row.label(text="Values")
        icons = row.row(align=True)
        if context.scene.render_raw.use_values_viewport:
            icons.prop(context.scene.render_raw, 'use_values_viewport', text="", icon="RESTRICT_VIEW_OFF")
        else: 
            icons.prop(context.scene.render_raw, 'use_values_viewport', text="", icon="RESTRICT_VIEW_ON")
        if context.scene.render_raw.use_values_render:
            icons.prop(context.scene.render_raw, 'use_values_render', text="", icon="RESTRICT_RENDER_OFF")
        else: 
            icons.prop(context.scene.render_raw, 'use_values_render', text="", icon="RESTRICT_RENDER_ON")
        self.layout.separator()
        """

    def draw(self, context):
        draw_values_panel(self, context)

class CurvesPanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_post_curves"
    bl_parent_id = "RENDER_PT_render_raw_values"
    bl_label = "Curves"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_curves_panel(self, context)

class ColorsPanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_colors"
    bl_parent_id = "RENDER_PT_render_raw"
    bl_label = "Colors"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    # bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return context.scene.render_raw.enable_RR

    def draw_header(self, context):
        self.layout.prop(context.scene.render_raw, 'use_colors', text="")

    def draw(self, context):
        draw_colors_panel(self, context)
        
class ColorBalancePanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_color_balance"
    bl_parent_id = "RENDER_PT_render_raw_colors"
    bl_label = "Color Balance"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_color_balance_panel(self, context)

class ColorBlendingPanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_color_blending"
    bl_parent_id = "RENDER_PT_render_raw_colors"
    bl_label = "Value / Color"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_color_blending_panel(self, context)

class HueHuePanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_hue_hue"
    bl_parent_id = "RENDER_PT_render_raw_colors"
    bl_label = "Hue / Hue"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_hue_hue_panel(self, context)

class HueSaturationPanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_hue_saturation"
    bl_parent_id = "RENDER_PT_render_raw_colors"
    bl_label = "Hue / Saturation"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_hue_saturation_panel(self, context)

class HueValuePanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_hue_value"
    bl_parent_id = "RENDER_PT_render_raw_colors"
    bl_label = "Hue / Value"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_hue_value_panel(self, context)

class ValueSaturationPanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_value_saturation"
    bl_parent_id = "RENDER_PT_render_raw_colors"
    bl_label = "Value / Saturation"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_value_saturation_panel(self, context)

class DetailsPanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_details"
    bl_parent_id = "RENDER_PT_render_raw_values"
    bl_label = "Details"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    # @classmethod
    # def poll(self, context):
    #     return context.scene.render_raw.enable_RR 

    # def draw_header(self, context):
    #     self.layout.prop(context.scene.render_raw, 'use_details', text="")

    def draw(self, context):
        draw_details_panel(self, context)

class EffectsPanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_effects"
    bl_parent_id = "RENDER_PT_render_raw"
    bl_label = "Effects"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return context.scene.render_raw.enable_RR
    
    def draw_header(self, context):
        self.layout.prop(context.scene.render_raw, 'use_effects', text="")

    def draw(self, context):
        draw_effects_panel(self, context)

class GlarePanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_glare"
    bl_parent_id = "RENDER_PT_render_raw_effects"
    bl_label = "Glare"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_glare_panel(self, context)

class VignettePanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_vignette"
    bl_parent_id = "RENDER_PT_render_raw_effects"
    bl_label = "Vignette"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_vignette_panel(self, context)

class GrainPanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_grain"
    bl_parent_id = "RENDER_PT_render_raw_effects"
    bl_label = "Film Grain"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_grain_panel(self, context)

class OriginalCurvePanel(bpy.types.Panel):
    bl_label = "Use Curves"
    bl_idname = 'RENDER_PT_render_raw_original_curves'
    bl_parent_id = "RENDER_PT_render_raw"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    COMPAT_ENGINES = {
        'BLENDER_RENDER',
        'BLENDER_EEVEE',
        'BLENDER_EEVEE_NEXT',
        'BLENDER_WORKBENCH',
    }

    @classmethod
    def poll(self, context):
        return not context.scene.render_raw.enable_RR
    
    def draw_header(self, context):
        scene = context.scene
        view = scene.view_settings
        self.layout.prop(view, "use_curve_mapping", text="")

    def draw(self, context):
        draw_original_curves_panel(self, context)

class OriginalDisplayPanel(bpy.types.Panel):
    bl_label = "Display"
    bl_idname = 'RENDER_PT_render_raw_original_display'
    bl_parent_id = "RENDER_PT_render_raw"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    COMPAT_ENGINES = {
        'BLENDER_RENDER',
        'BLENDER_EEVEE',
        'BLENDER_EEVEE_NEXT',
        'BLENDER_WORKBENCH',
    }

    @classmethod
    def poll(self, context):
        return not context.scene.render_raw.enable_RR

    def draw(self, context):
        draw_original_display_panel(self, context)

class UtilitiesPanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_utilities"
    bl_parent_id = "RENDER_PT_render_raw"
    bl_label = "Utilities"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return context.scene.render_raw.enable_RR 

    def draw(self, context):
        draw_utilities_panel(self, context)

class SceneSettingsPanel(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_scene"
    bl_parent_id = "RENDER_PT_render_raw_utilities"
    bl_label = "Scene Color Settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_scene_settings_panel(self, context)

''' 3D View Sidebar Panels '''

class RenderRawPanel3DView(bpy.types.Panel):
    bl_label = "Color Management"
    bl_idname = 'RENDER_PT_render_raw_color_management_3d_view'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'

    @classmethod
    def poll(self, context):
        try:
            prefs = get_prefs(context)
            return prefs.enable_3d_view_sidebar
        except:
            return False

    def draw(self, context):
        draw_color_management_panel(self, context) 

class ValuesPanel3DView(bpy.types.Panel):
    bl_label = "Values"
    bl_idname = 'RENDER_PT_render_raw_values_3d_view'
    bl_parent_id = "RENDER_PT_render_raw_color_management_3d_view"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    # bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return context.scene.render_raw.enable_RR

    def draw_header(self, context):
        self.layout.prop(context.scene.render_raw, 'use_values', text="")

    def draw(self, context):
        draw_values_panel(self, context)

class CurvesPanel3DView(bpy.types.Panel):
    bl_label = "Curves"
    bl_idname = 'RENDER_PT_render_raw_curves_3d_view'
    bl_parent_id = "RENDER_PT_render_raw_values_3d_view"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_curves_panel(self, context)

class ColorsPanel3DView(bpy.types.Panel):
    bl_label = "Colors"
    bl_idname = 'RENDER_PT_render_raw_colors_3d_view'
    bl_parent_id = "RENDER_PT_render_raw_color_management_3d_view"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    # bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return context.scene.render_raw.enable_RR

    def draw_header(self, context):
        self.layout.prop(context.scene.render_raw, 'use_colors', text="")

    def draw(self, context):
        draw_colors_panel(self, context)

class ColorBalancePanel3DView(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_color_balance_3d_view"
    bl_parent_id = "RENDER_PT_render_raw_colors_3d_view"
    bl_label = "Color Balance"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_color_balance_panel(self, context)

class ColorBlendingPanel3DView(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_color_blending_3d_view"
    bl_parent_id = "RENDER_PT_render_raw_colors_3d_view"
    bl_label = "Value / Color"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_color_blending_panel(self, context)

class HueHuePanel3DView(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_hue_hue_3d_view"
    bl_parent_id = "RENDER_PT_render_raw_colors_3d_view"
    bl_label = "Hue / Hue"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_hue_hue_panel(self, context)

class HueSaturationPanel3DView(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_hue_saturation_3d_view"
    bl_parent_id = "RENDER_PT_render_raw_colors_3d_view"
    bl_label = "Hue / Saturation"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_hue_saturation_panel(self, context)

class HueValuePanel3DView(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_hue_value_3d_view"
    bl_parent_id = "RENDER_PT_render_raw_colors_3d_view"
    bl_label = "Hue / Value"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_hue_value_panel(self, context)

class ValueSaturationPanel3DView(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_value_saturation_3d_view"
    bl_parent_id = "RENDER_PT_render_raw_colors_3d_view"
    bl_label = "Value / Saturation"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_value_saturation_panel(self, context)

class DetailsPanel3DView(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_details_3d_view"
    bl_parent_id = "RENDER_PT_render_raw_values_3d_view"
    bl_label = "Details"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    bl_options = {'DEFAULT_CLOSED'}

    # @classmethod
    # def poll(self, context):
    #     return context.scene.render_raw.enable_RR

    # def draw_header(self, context):
    #     self.layout.prop(context.scene.render_raw, 'use_details', text="")

    def draw(self, context):
        draw_details_panel(self, context)

class EffectsPanel3DView(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_effects_3d_view"
    bl_parent_id = "RENDER_PT_render_raw_color_management_3d_view"
    bl_label = "Effects"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    # bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return context.scene.render_raw.enable_RR
    
    def draw_header(self, context):
        self.layout.prop(context.scene.render_raw, 'use_effects', text="")

    def draw(self, context):
        draw_effects_panel(self, context)

class GlarePanel3DView(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_glare_3d_view"
    bl_parent_id = "RENDER_PT_render_raw_effects_3d_view"
    bl_label = "Glare"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_glare_panel(self, context)

class VignettePanel3DView(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_vignette_3d_view"
    bl_parent_id = "RENDER_PT_render_raw_effects_3d_view"
    bl_label = "Vignette"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_vignette_panel(self, context)

class GrainPanel3DView(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_grain_3d_view"
    bl_parent_id = "RENDER_PT_render_raw_effects_3d_view"
    bl_label = "Film Grain"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_grain_panel(self, context)

class OriginalCurvePanel3DView(bpy.types.Panel):
    bl_label = "Use Curves"
    bl_idname = 'RENDER_PT_render_raw_original_curves_3d_view'
    bl_parent_id = "RENDER_PT_render_raw_color_management_3d_view"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    COMPAT_ENGINES = {
        'BLENDER_RENDER',
        'BLENDER_EEVEE',
        'BLENDER_EEVEE_NEXT',
        'BLENDER_WORKBENCH',
    }

    @classmethod
    def poll(self, context):
        return not context.scene.render_raw.enable_RR
    
    def draw_header(self, context):
        scene = context.scene
        view = scene.view_settings
        self.layout.prop(view, "use_curve_mapping", text="")

    def draw(self, context):
        draw_original_curves_panel(self, context)

class OriginalDisplayPanel3DView(bpy.types.Panel):
    bl_label = "Display"
    bl_idname = 'RENDER_PT_render_raw_original_display_3d_view'
    bl_parent_id = "RENDER_PT_render_raw_color_management_3d_view"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render'
    COMPAT_ENGINES = {
        'BLENDER_RENDER',
        'BLENDER_EEVEE',
        'BLENDER_EEVEE_NEXT',
        'BLENDER_WORKBENCH',
    }

    @classmethod
    def poll(self, context):
        return not context.scene.render_raw.enable_RR

    def draw(self, context):
        draw_original_display_panel(self, context)

class UtilitiesPanel3DView(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_utilities_3d_view"
    bl_parent_id = "RENDER_PT_render_raw_color_management_3d_view"
    bl_label = "Utilities"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return context.scene.render_raw.enable_RR 

    def draw(self, context):
        draw_utilities_panel(self, context)

class SceneSettingsPanel3DView(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_scene_settings_3d_view"
    bl_parent_id = "RENDER_PT_render_raw_utilities_3d_view"
    bl_label = "Scene Color Settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = 'render'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_scene_settings_panel(self, context)

''' Node Editor Panels '''

class ValuesPanelNode(bpy.types.Panel):
    bl_label = "Values"
    bl_idname = 'NODE_PT_render_raw_values_node'
    bl_parent_id = "NODE_PT_active_node_properties"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'

    @classmethod
    def poll(self, context):
        return context.scene.render_raw.enable_RR and context.scene.node_tree.nodes.active.name == 'Render Raw'

    def draw_header(self, context):
        self.layout.prop(context.scene.render_raw, 'use_values', text="")

    def draw(self, context):
        draw_values_panel(self, context)

class CurvesPanelNode(bpy.types.Panel):
    bl_label = "Curves"
    bl_idname = 'NODE_PT_render_raw_curves_node'
    bl_parent_id = "NODE_PT_render_raw_values_node"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_curves_panel(self, context)

class ColorPanelNode(bpy.types.Panel):
    bl_label = "Colors"
    bl_idname = 'NODE_PT_render_raw_colors_node'
    bl_parent_id = "NODE_PT_active_node_properties"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'

    @classmethod
    def poll(self, context):
        return context.scene.render_raw.enable_RR and context.scene.node_tree.nodes.active.name == 'Render Raw'

    def draw_header(self, context):
        self.layout.prop(context.scene.render_raw, 'use_colors', text="")

    def draw(self, context):
        draw_colors_panel(self, context)

class ColorBalancePanelNode(bpy.types.Panel):
    bl_label = "Color Balance"
    bl_idname = 'NODE_PT_render_raw_color_balance_node'
    bl_parent_id = "NODE_PT_render_raw_colors_node"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_color_balance_panel(self, context)
        
class ColorBlendingPanelNode(bpy.types.Panel):
    bl_label = "Value / Color"
    bl_idname = 'NODE_PT_render_raw_color_blending_node'
    bl_parent_id = "NODE_PT_render_raw_colors_node"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_color_blending_panel(self, context)

class HueHuePanelNode(bpy.types.Panel):
    bl_label = "Hue / Hue"
    bl_idname = 'NODE_PT_render_raw_hue_hue_node'
    bl_parent_id = "NODE_PT_render_raw_colors_node"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_hue_hue_panel(self, context)

class HueSaturationPanelNode(bpy.types.Panel):
    bl_label = "Hue / Saturation"
    bl_idname = 'NODE_PT_render_raw_hue_saturation_node'
    bl_parent_id = "NODE_PT_render_raw_colors_node"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_hue_saturation_panel(self, context)

class HueValuePanelNode(bpy.types.Panel):
    bl_label = "Hue / Value"
    bl_idname = 'NODE_PT_render_raw_hue_value_node'
    bl_parent_id = "NODE_PT_render_raw_colors_node"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_hue_value_panel(self, context)

class ValueSaturationPanelNode(bpy.types.Panel):
    bl_label = "Value / Saturation"
    bl_idname = 'NODE_PT_render_raw_value_saturation_node'
    bl_parent_id = "NODE_PT_render_raw_colors_node"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_value_saturation_panel(self, context)

class DetailsPanelNode(bpy.types.Panel):
    bl_label = "Details"
    bl_idname = 'NODE_PT_render_raw_details_node'
    bl_parent_id = "NODE_PT_render_raw_values_node"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_details_panel(self, context)

class EffectsPanelNode(bpy.types.Panel):
    bl_label = "Effects"
    bl_idname = 'NODE_PT_render_raw_effects_node'
    bl_parent_id = "NODE_PT_active_node_properties"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'

    @classmethod
    def poll(self, context):
        return context.scene.render_raw.enable_RR and context.scene.node_tree.nodes.active.name == 'Render Raw'
    
    def draw_header(self, context):
        self.layout.prop(context.scene.render_raw, 'use_effects', text="")

    def draw(self, context):
        draw_effects_panel(self, context)

class GlarePanelNode(bpy.types.Panel):
    bl_label = "Glare"
    bl_idname = 'NODE_PT_render_raw_glare_node'
    bl_parent_id = "NODE_PT_render_raw_effects_node"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    # bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_glare_panel(self, context)

class VignettePanelNode(bpy.types.Panel):
    bl_label = "Vignette"
    bl_idname = 'NODE_PT_render_raw_vignette_node'
    bl_parent_id = "NODE_PT_render_raw_effects_node"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    # bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_vignette_panel(self, context)

class GrainPanelNode(bpy.types.Panel):
    bl_label = "Grain"
    bl_idname = 'NODE_PT_render_raw_grain_node'
    bl_parent_id = "NODE_PT_render_raw_effects_node"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    # bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_grain_panel(self, context)

class UtilitiesPanelNode(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_utilities_node"
    bl_parent_id = "NODE_PT_active_node_properties"
    bl_label = "Utilities"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return context.scene.render_raw.enable_RR 

    def draw(self, context):
        draw_utilities_panel(self, context)

class SceneSettingsPanelNode(bpy.types.Panel):
    bl_idname = "RENDER_PT_render_raw_scene_settings_node"
    bl_parent_id = "RENDER_PT_render_raw_utilities_node"
    bl_label = "Scene Settings"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        draw_scene_settings_panel(self, context)

''' Image Editor Panels '''
# TODO


''' Dummy Blender Panels '''

class RENDER_PT_render_raw_dummy_color_management(bpy.types.Panel):
    bl_label = "Color Management"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'PROPERTIES'
    bl_context = 'render'
    bl_region_type = 'WINDOW'
    COMPAT_ENGINES = {
        'BLENDER_RENDER',
        'BLENDER_EEVEE',
        'BLENDER_EEVEE_NEXT',
        'BLENDER_WORKBENCH',
    }
    
    def draw(self, context):
        col = self.layout.column()
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(context.scene.display_settings, 'display_device')
        col.separator()
        col.prop(context.scene.view_settings, 'view_transform')
        col.prop(context.scene.view_settings, 'look')
        col.prop(context.scene.view_settings, 'exposure')
        col.prop(context.scene.view_settings, 'gamma')
        col.separator()
        col.prop(context.scene.sequencer_colorspace_settings, 'name', text='Sequencer')

class RENDER_PT_render_raw_dummy_display(bpy.types.Panel):
    bl_label = "Display"
    bl_parent_id = "RENDER_PT_render_raw_dummy_color_management"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    COMPAT_ENGINES = {
        'BLENDER_RENDER',
        'BLENDER_EEVEE',
        'BLENDER_EEVEE_NEXT',
        'BLENDER_WORKBENCH',
    }

    def draw(self, context):
        col = self.layout.column()
        col.use_property_split = True
        col.enabled = context.scene.view_settings.view_transform == 'Standard' and gpu.capabilities.hdr_support_get()
        col.prop(context.scene.view_settings, 'use_hdr_view')

class RENDER_PT_render_raw_dummy_curves(bpy.types.Panel):
    bl_label = "Use Curves"
    bl_parent_id = "RENDER_PT_render_raw_dummy_color_management"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    COMPAT_ENGINES = {
        'BLENDER_RENDER',
        'BLENDER_EEVEE',
        'BLENDER_EEVEE_NEXT',
        'BLENDER_WORKBENCH',
    }
    
    def draw_header(self, context):
        scene = context.scene
        view = scene.view_settings
        self.layout.prop(view, "use_curve_mapping", text="")

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        view = scene.view_settings
        layout.use_property_split = False
        layout.use_property_decorate = False  # No animation.
        layout.enabled = view.use_curve_mapping
        layout.template_curve_mapping(view, "curve_mapping", type='COLOR', levels=True)

classes = [
    PresetsMenu,

    RenderRawPanel, 
        ValuesPanel, 
            DetailsPanel, CurvesPanel, 
        ColorsPanel, 
            ColorBalancePanel, ValueSaturationPanel, ColorBlendingPanel, 
            HueHuePanel, HueSaturationPanel, HueValuePanel, 
        EffectsPanel, 
            GrainPanel, GlarePanel, VignettePanel, 
        UtilitiesPanel,
    OriginalDisplayPanel, OriginalCurvePanel, 
    
    RenderRawPanel3DView, 
        ValuesPanel3DView, 
            DetailsPanel3DView, CurvesPanel3DView, 
        ColorsPanel3DView,  
            ColorBalancePanel3DView, ValueSaturationPanel3DView, ColorBlendingPanel3DView, 
            HueHuePanel3DView, HueSaturationPanel3DView, HueValuePanel3DView, 
        EffectsPanel3DView, 
            GrainPanel3DView, GlarePanel3DView, VignettePanel3DView,
        UtilitiesPanel3DView, 
    OriginalDisplayPanel3DView, OriginalCurvePanel3DView, 

    ValuesPanelNode, 
        DetailsPanelNode, CurvesPanelNode, 
    ColorPanelNode, 
        ColorBalancePanelNode, ValueSaturationPanelNode, ColorBlendingPanelNode, 
        HueHuePanelNode, HueSaturationPanelNode, HueValuePanelNode, 
    EffectsPanelNode, 
        GlarePanelNode, GrainPanelNode, VignettePanelNode,
    UtilitiesPanelNode,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    if hasattr(bpy.types, 'RENDER_PT_color_management'):
        bpy.utils.unregister_class(bpy.types.RENDER_PT_color_management)
    if hasattr(bpy.types, 'RENDER_PT_color_management_curves'):
        bpy.utils.unregister_class(bpy.types.RENDER_PT_color_management_curves)
    if hasattr(bpy.types, 'RENDER_PT_color_management_display_settings'):
        bpy.utils.unregister_class(bpy.types.RENDER_PT_color_management_display_settings)

    if hasattr(bpy.types, 'RENDER_PT_render_raw_dummy_color_management'):
        bpy.utils.unregister_class(bpy.types.RENDER_PT_render_raw_dummy_color_management)
    if hasattr(bpy.types, 'RENDER_PT_render_raw_dummy_curves'):
        bpy.utils.unregister_class(bpy.types.RENDER_PT_render_raw_dummy_curves)
    if hasattr(bpy.types, 'RENDER_PT_render_raw_dummy_display'):
        bpy.utils.unregister_class(bpy.types.RENDER_PT_render_raw_dummy_display)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.utils.register_class(RENDER_PT_render_raw_dummy_color_management)
    bpy.utils.register_class(RENDER_PT_render_raw_dummy_display)
    bpy.utils.register_class(RENDER_PT_render_raw_dummy_curves)