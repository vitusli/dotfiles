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

import bpy
from .update_nodes import (
    manage_RR,

    update_view_transform, update_exposure, update_contrast, update_values, update_value_panel,
    
    update_saturation, update_white_balance, update_color_panel, update_hue, update_color_balance, update_color_blending, 
    update_value_saturation, update_color_boost,

    update_sharpness, update_texture, update_clarity, update_details_panel, 
    
    update_vignette, update_glare, update_bloom, update_streaks, update_ghosting, update_distortion, update_grain, 
    update_effects_panel 
)
from .operators.op_presets import apply_preset, preset_items
from .utilities.view_transforms import get_view_transforms

class RenderRawSettings(bpy.types.PropertyGroup):
    enable_RR: bpy.props.BoolProperty(
        name = 'Enable Render Raw',
        description = 'Swaps out the default color management for a compositing setup that offers greater control over colors',
        default = False,
        update = manage_RR
    )
    view_transform: bpy.props.EnumProperty(
        name = 'View Transform',
        description = 'View used when converting an image to a display space',
        items = get_view_transforms(),
        default = 'AgX Base sRGB',
        update = update_view_transform
    )
    preset: bpy.props.EnumProperty(
        name = 'Preset',
        description = 'Preset configurations of Render Raw settings',
        items = preset_items,
        default = None,
        update = apply_preset
    )

    # Values
    use_values: bpy.props.BoolProperty(
        default = True,
        update = update_value_panel
    )
    use_values_viewport: bpy.props.BoolProperty(
        default = True,
        update = update_value_panel
    )
    use_values_render: bpy.props.BoolProperty(
        default = True,
        update = update_value_panel
    )
    exposure: bpy.props.FloatProperty(
        name = 'Exposure',
        description = 'Sets the exposure pre-transform',
        default = 0,
        min = -10,
        max = 10,
        precision = 3,
        update = update_exposure
    )
    contrast: bpy.props.FloatProperty(
        name = 'Contrast',
        description = "Adjusts the exposure and gamma at the same time pre-transform to increase contrast, similar to Blender's high or low contrast looks but with more control",
        default = 0,
        min = -1,
        max = 1,
        update = update_contrast
    )
    whites: bpy.props.FloatProperty(
        name = 'Whites',
        description = 'Adjusts how bright a pixel needs to be in order to result in white, post-transform. Useful for fine tuning highlights to be very bright but not blown out',
        default = 0,
        min = -0.5,
        max = 0.5,
        update = update_values
    )
    highlights: bpy.props.FloatProperty(
        name = 'Highlights',
        description = 'Smoothly adjusts the values between 0.5 and 1.0, post-transform',
        default = 0,
        min = -0.5,
        max = 0.5,
        update = update_values
    )
    shadows: bpy.props.FloatProperty(
        name = 'Shadows',
        description = 'Smoothly adjusts the values between 0.0 and .5, post-transform',
        default = 0,
        min = -0.5,
        max = 0.5,
        update = update_values
    )
    blacks: bpy.props.FloatProperty(
        name = 'Blacks',
        description = 'Adjusts how dark a pixel needs to be in order to result in black, post-transform. Useful for crushing or lifting shadows or increasing contrast in dark areas',
        default = 0,
        min = -0.5,
        max = 0.5,
        update = update_values
    )

    # Colors
    use_colors: bpy.props.BoolProperty(
        default = True,
        update = update_color_panel
    )
    temperature: bpy.props.FloatProperty(
        name = 'Temperature',
        description = 'Adjusts the prominence of the red and blue channels for a warmer or cooler look, pre-transform',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_white_balance
    )
    tint: bpy.props.FloatProperty(
        name = 'Tint',
        description = 'Adjusts the prominence of the green channel for a green or purple look, pre-transform',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_white_balance
    )
    saturation: bpy.props.FloatProperty(
        name = 'Saturation',
        description = 'Adjusts saturation uniformly, post-transform',
        default = 1,
        min = 0,
        max = 2,
        update = update_saturation
    )
    saturation_perceptual: bpy.props.FloatProperty(
        name = 'Perceptual',
        description = 'Keeps the perceived value the same during saturation adjustments rather than the RGB value, which is more intuitive but can cause colors to clip',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_saturation
    )
    color_boost: bpy.props.FloatProperty(
        name = 'Color Boost',
        description = 'Adjusts the saturation of lower saturated areas without changing highly saturated areas, pre-transform',
        default = 0,
        min = -1,
        max = 1,
        update = update_color_boost
    )
    red_hue: bpy.props.FloatProperty(
        name = 'Red',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    red_saturation: bpy.props.FloatProperty(
        name = 'Red',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    red_value: bpy.props.FloatProperty(
        name = 'Red',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    orange_hue: bpy.props.FloatProperty(
        name = 'Orange',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    orange_saturation: bpy.props.FloatProperty(
        name = 'Orange',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    orange_value: bpy.props.FloatProperty(
        name = 'Orange',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    yellow_hue: bpy.props.FloatProperty(
        name = 'Yellow',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    yellow_saturation: bpy.props.FloatProperty(
        name = 'Yellow',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    yellow_value: bpy.props.FloatProperty(
        name = 'Yellow',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    green_hue: bpy.props.FloatProperty(
        name = 'Green',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    green_saturation: bpy.props.FloatProperty(
        name = 'Green',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    green_value: bpy.props.FloatProperty(
        name = 'Green',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    teal_hue: bpy.props.FloatProperty(
        name = 'Teal',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    teal_saturation: bpy.props.FloatProperty(
        name = 'Teal',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    teal_value: bpy.props.FloatProperty(
        name = 'Teal',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    blue_hue: bpy.props.FloatProperty(
        name = 'Blue',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    blue_saturation: bpy.props.FloatProperty(
        name = 'Blue',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    blue_value: bpy.props.FloatProperty(
        name = 'Blue',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    pink_hue: bpy.props.FloatProperty(
        name = 'Pink',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    pink_saturation: bpy.props.FloatProperty(
        name = 'Pink',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    pink_value: bpy.props.FloatProperty(
        name = 'Pink',
        default = 0.5,
        min = 0,
        max = 1,
        update = update_hue
    )
    lift_color: bpy.props.FloatVectorProperty(
        name = 'Lift',
        description = "Adjusts the shadows, post-transform",
        subtype = 'COLOR',
        default = [1, 1, 1],
        min = 0,
        max = 2,
        update = update_color_balance
    )
    gamma_color: bpy.props.FloatVectorProperty(
        name = 'Gamma',
        description = "Adjusts the midtones, post-transform",
        subtype = 'COLOR',
        default = [1, 1, 1],
        min = 0,
        max = 2,
        update = update_color_balance
    )
    gain_color: bpy.props.FloatVectorProperty(
        name = 'Gain',
        description = "Adjusts the highlights, post-transform",
        subtype = 'COLOR',
        default = [1, 1, 1],
        min = 0,
        max = 2,
        update = update_color_balance
    )
    offset_color: bpy.props.FloatVectorProperty(
        name = 'Offset',
        description = "An addative adjustment, pre-transform",
        subtype = 'COLOR',
        default = [0, 0, 0],
        min = 0,
        max = 1,
        update = update_color_balance
    )
    power_color: bpy.props.FloatVectorProperty(
        name = 'Power',
        description = "A pre-transform contrast adjustment defined by a power curve",
        subtype = 'COLOR',
        default = [1, 1, 1],
        min = 0,
        max = 2,
        update = update_color_balance
    )
    slope_color: bpy.props.FloatVectorProperty(
        name = 'Slope',
        description = "Adjusts the image without affecting the black level, pre-transform. It can be thought of as a contrast control that pivots at 0",
        subtype = 'COLOR',
        default = [1, 1, 1],
        min = 0,
        max = 2,
        update = update_color_balance
    )
    shadow_range: bpy.props.FloatProperty(
        name = 'Range',
        description = "Scales the range of values that are considered to be in the shadow range",
        default = 0.5,
        min = 0,
        max = 1,
        update = update_color_blending
    )
    highlight_range: bpy.props.FloatProperty(
        name = 'Range',
        description = "Scales the range of values that are considered to be in the highlight range",
        default = 0.5,
        min = 0,
        max = 1,
        update = update_color_blending
    )
    midtone_range: bpy.props.FloatProperty(
        name = 'Range',
        description = "Scales the range of values that are considered to be in the midtone range",
        default = 0.5,
        min = 0,
        max = 1,
        update = update_color_blending
    )
    shadow_factor: bpy.props.FloatProperty(
        name = 'Factor',
        description = "How much the shadow adjustment gets mixed in with the origional image",
        default = 1,
        min = 0,
        max = 1,
        update = update_color_blending
    )
    highlight_factor: bpy.props.FloatProperty(
        name = 'Factor',
        description = "How much the highlight adjustment gets mixed in with the origional image",
        default = 1,
        min = 0,
        max = 1,
        update = update_color_blending
    )
    midtone_factor: bpy.props.FloatProperty(
        name = 'Factor',
        description = "How much the midtone adjustment gets mixed in with the origional image",
        default = 1,
        min = 0,
        max = 1,
        update = update_color_blending
    )
    highlight_color: bpy.props.FloatVectorProperty(
        name = 'Color',
        subtype = 'COLOR',
        size = 3,
        max = 1,
        min = 0.1,
        precision = 3,
        default = [0.5, 0.5, 0.5],
        update = update_color_blending
    )
    midtone_color: bpy.props.FloatVectorProperty(
        name = 'Color',
        subtype = 'COLOR',
        size = 3,
        max = 1,
        min = 0.1,
        precision = 3,
        default = [0.5, 0.5, 0.5],
        update = update_color_blending
    )
    shadow_color: bpy.props.FloatVectorProperty(
        name = 'Color',
        subtype = 'COLOR',
        size = 3,
        max = 1,
        min = 0.1,
        precision = 3,
        default = [0.5, 0.5, 0.5],
        update = update_color_blending
    )
    shadow_saturation: bpy.props.FloatProperty(
        name = 'Shadows',
        description = "Adjusts the saturation in only the shadow areas, post-transform",
        default = 1,
        min = 0,
        max = 2,
        update = update_value_saturation
    )
    midtone_saturation: bpy.props.FloatProperty(
        name = 'Midtones',
        description = "Adjusts the saturation in only the midtone areas, post-transform",
        default = 1,
        min = 0,
        max = 2,
        update = update_value_saturation
    )
    highlight_saturation: bpy.props.FloatProperty(
        name = 'Highlights',
        description = "Adjusts the saturation in only the highlight areas, post-transform",
        default = 1,
        min = 0,
        max = 2,
        update = update_value_saturation
    )
    shadow_saturation_range: bpy.props.FloatProperty(
        name = 'Range',
        description = "Scales the range of values that are considered to be in the shadow range",
        default = 0.5,
        min = 0,
        max = 1,
        update = update_value_saturation
    )
    midtone_saturation_range: bpy.props.FloatProperty(
        name = 'Range',
        description = "Scales the range of values that are considered to be in the midtone range",
        default = 0.5,
        min = 0,
        max = 1,
        update = update_value_saturation
    )
    highlight_saturation_range: bpy.props.FloatProperty(
        name = 'Range',
        description = "Scales the range of values that are considered to be in the highlight range",
        default = 0.5,
        min = 0,
        max = 1,
        update = update_value_saturation
    )
    value_saturation_perceptual:bpy.props.FloatProperty(
        name = 'Perceptual',
        description = "Adjusts saturation while keeping the perceived brightness the same",
        default = 1,
        min = 0,
        max = 1,
        update = update_value_saturation
    )
    dummy_blending: bpy.props.EnumProperty(
        name = 'Blending',
        items = [
            ('Soft Light', 'Soft Light', ''),
            ('Color', 'Color', '')
        ],
        default='Soft Light'
    )
    dummy_color: bpy.props.FloatVectorProperty(
        name = 'Color',
        subtype = 'COLOR',
        default=[0.5, 0.5, 0.5]
    )
    # TODO: Vibrance 

    # Details
    use_details: bpy.props.BoolProperty(
        default = False,
        update = update_details_panel
    )
    sharpness: bpy.props.FloatProperty(
        name = 'Sharpening',
        description = "Adds high frequency contrast around edges, post-transform",
        default = 0,
        min = 0,
        max = 1,
        update = update_sharpness
    ) 
    sharpness_mask: bpy.props.FloatProperty(
        name = 'Masking',
        description = "Adjusts how different neighboring pixels need to be in order to be considered an edge",
        default = 0,
        min = 0,
        max = 1,
        update = update_sharpness
    ) 
    texture: bpy.props.FloatProperty(
        name = 'Texture',
        description = "Adjusts the contrast in only the midtone areas, post-transform",
        default = 0,
        min = -1,
        max = 1,
        update = update_texture
    ) 
    texture_color: bpy.props.FloatProperty(
        name = 'Keep Color',
        default = 1,
        min = 0,
        max = 1,
        update = update_texture
    ) 
    clarity: bpy.props.FloatProperty(
        name = 'Clarity',
        description = "Adds or removes lower frequency contrast around edges, post-transform",
        default = 0,
        min = -1,
        max = 1,
        update = update_clarity
    ) 
    clarity_size: bpy.props.FloatProperty(
        name = 'Size',
        description = "Adjusts how much of the area around edges are affected by the clarity control",
        default = 0.5,
        min = 0,
        max = 1,
        update = update_clarity
    ) 

    # Effects
    use_effects: bpy.props.BoolProperty(
        default = True,
        update = update_effects_panel
    )
    vignette_value: bpy.props.FloatProperty(
        name = 'Vignette Value',
        description = "Brightens or darkens the edges of the image, post-transform",
        default = 0,
        min = -1,
        max = 1,
        update = update_vignette
    )
    vignette_feathering: bpy.props.FloatProperty(
        name = 'Feathering',
        description = "Adjusts the softness of the vignette",
        default = 0.5,
        min = 0,
        max = 1,
        update = update_vignette
    )
    vignette_scale_x: bpy.props.FloatProperty(
        name = 'Scale X',
        description = "Adjusts the width of the vignette",
        default = 1,
        min = 0,
        max = 2,
        update = update_vignette
    )
    vignette_scale_y: bpy.props.FloatProperty(
        name = 'Scale Y',
        description = "Adjusts the height of the vignette",
        default = 1,
        min = 0,
        max = 2,
        update = update_vignette
    )
    vignette_shift_x: bpy.props.FloatProperty(
        name = 'Shift X',
        description = "Adjusts the horizontal location of the vignette",
        default = 0,
        min = -0.5,
        max = 0.5,
        update = update_vignette
    )
    vignette_shift_y: bpy.props.FloatProperty(
        name = 'Shift Y',
        description = "Adjusts the vertical location of the vignette",
        default = 0,
        min = -0.5,
        max = 0.5,
        update = update_vignette
    )
    vignette_roundness: bpy.props.FloatProperty(
        name = 'Roundness',
        description = "Adjusts how round the corners of the vignette are",
        default = 1,
        min = 0,
        max = 1,
        update = update_vignette
    )
    vignette_highlights: bpy.props.FloatProperty(
        name = 'Highlights',
        description = "Adjusts how much the vignette preserves origional colors and highlights",
        default = 0.5,
        min = 0,
        max = 1,
        update = update_vignette
    )
    glare: bpy.props.FloatProperty(
        name = 'Glare',
        description = "Adjusts how much total glare is applied, pre-transform",
        default = 0,
        min = 0,
        max = 1,
        update = update_glare
    )
    glare_threshold: bpy.props.FloatProperty(
        name = 'Threshold',
        description = "Adjusts how bright a pixel needs to be in order to cause glare",
        default = 1,
        min = 0,
        max = 100,
        update = update_glare
    )
    glare_quality: bpy.props.IntProperty(
        name = 'Quality',
        description = 'Determines how many layers of blur are used in the bloom',
        default = 5,
        min = 1,
        max = 5,
        update = update_glare
    )
    bloom: bpy.props.FloatProperty(
        name = 'Bloom Strength',
        description = "Adjusts how much glow is applied around bright areas",
        default = 1,
        min = 0,
        max = 1,
        update = update_bloom
    )
    bloom_size: bpy.props.IntProperty(
        name = 'Bloom Size',
        description = "Adjusts the size of the glow around bright areas",
        default = 9,
        min = 1,
        max = 9,
        update = update_bloom
    )
    streaks: bpy.props.FloatProperty(
        name = 'Streaks Strength',
        description = "Adjusts how much the streaks are mixed in with the origional image",
        default = 0.5,
        min = 0,
        max = 1,
        update = update_streaks
    )
    streak_length: bpy.props.FloatProperty(
        name = 'Length',
        description = "Adjusts the size of the streaks",
        default = 0.25,
        min = 0,
        max = 1,
        update = update_streaks
    )
    streak_count: bpy.props.IntProperty(
        name = 'Count',
        description = "Adjusts how many streaks are created around bright areas",
        default = 13,
        min = 2,
        max = 16,
        update = update_streaks
    )
    streak_angle: bpy.props.FloatProperty(
        name = 'Angle',
        description = "Adjusts the rotation of the streaks",
        subtype = 'ANGLE',
        default = 0,
        min = 0,
        max = 180,
        update = update_streaks
    )
    ghosting: bpy.props.FloatProperty(
        name = 'Ghosting',
        description = "Adjusts how much camera artifacting is applied on top of the image",
        default = 0.05,
        min = 0,
        max = 1,
        update = update_ghosting
    )
    distortion: bpy.props.FloatProperty(
        name = 'Lens Distortion',
        description = "Simulates warping from the shape of a camera lens",
        default = 0,
        min = -1,
        max = 1,
        update = update_distortion
    )
    dispersion: bpy.props.FloatProperty(
        name = 'Dispersion',
        description = "Simulates color fringing from the imperfect refraction of a camera lens",
        default = 0,
        min = 0,
        max = 1,
        update = update_distortion
    )
    grain: bpy.props.FloatProperty(
        name = 'Film Grain',
        description = "Simulates the noise on film or a digital sensor, which has a very different look from render noise",
        default = 0,
        min = 0,
        max = 1,
        update = update_grain
    )
    grain_method: bpy.props.EnumProperty(
        name = 'Method',
        items = [
            ('FAST', 'Fast', 'Adds a grain texture as a simple overlay'),
            ('ACCURATE', 'Accurate', 'Simulates grain realistically by displacing the image differently per color channel'),
        ],
        default = 'FAST',
        update = update_grain
    )
    grain_scale: bpy.props.FloatProperty(
        name = 'Scale',
        description = "Adjusts the size of the noise pattern",
        default = 5,
        min = 1,
        max = 20,
        update = update_grain
    )
    grain_aspect: bpy.props.FloatProperty(
        name = 'Aspect',
        description = "Adjusts the hight and width of the noise pattern so that the noise doesn't appear stretched when the image is not square",
        default = 0.5,
        min = 0,
        max = 1,
        update = update_grain
    )
    grain_steps: bpy.props.IntProperty(
        name = 'Steps',
        description = "Adjusts the complexity of the noise pattern. Increasing the steps results in more realistic noise but also increases processing time",
        default = 2,
        min = 1,
        max = 5,
        update = update_grain
    )
    grain_saturation: bpy.props.FloatProperty(
        name = 'Color',
        description = "Adjusts how much the noise colors the image",
        default = 1,
        min = 0,
        max = 1,
        update = update_grain
    )
    grain_is_animated: bpy.props.BoolProperty(
        name = 'Animmate',
        description = 'Randomize the grain per frame. This is more realistic but fairly slow in the viewport',
        default = False,
        update = update_grain
    )

def register():
    bpy.utils.register_class(RenderRawSettings)
    bpy.types.Scene.render_raw = bpy.props.PointerProperty(type=RenderRawSettings)

def unregister():
    bpy.utils.unregister_class(RenderRawSettings)