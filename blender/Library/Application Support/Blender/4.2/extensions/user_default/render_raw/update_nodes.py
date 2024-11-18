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

import bpy, addon_utils
from .preferences import get_prefs
from .utilities.version import get_addon_version
from .utilities.append_node import append_node
from .utilities.conversions import get_rgb, map_range, set_alpha
from .utilities.viewport import enable_viewport_compositing
from .utilities.view_transforms import view_transforms_disable, view_transforms_enable
from .operators.op_report import Report

RR_node_name = 'Render Raw'
RR_node_group_name = 'Render Raw'

def set_node_version():
    try:
        nodes = bpy.data.node_groups[RR_node_name].nodes
        nodes['Version'].label = get_addon_version()
    except:
        print('Addon version could not be saved in the node tree')

def check_node_version():
    nodes = bpy.data.node_groups[RR_node_name].nodes
    node_version = nodes['Version'].label
    addon_version = str(
        [addon.bl_info.get("version", (-1, -1, -1)) for addon in addon_utils.modules() if addon.bl_info["name"] == 'Render Raw'][0]
    )
    if node_version != addon_version:
        message = f"The nodes in this file were created with Render Raw {node_version}. The version of Render Raw currently installed is {addon_version}. Please use Refresh Node Tree under Utilities to avoid unexpected behavior."
        bpy.ops.render.render_raw_report(message_type="WARNING", message=message)

# Details Panel 
    
def update_sharpness(self, context):
    nodes = bpy.data.node_groups[RR_node_name].nodes
    if not context.scene.render_raw.use_values or context.scene.render_raw.sharpness == 0:
        nodes['Sharpness'].mute = True
    else: 
        nodes['Sharpness'].mute = False
        nodes['Sharpness'].inputs['Strength'].default_value = context.scene.render_raw.sharpness   
        nodes['Sharpness'].inputs['Masking'].default_value = context.scene.render_raw.sharpness_mask

def update_texture(self, context):
    nodes = bpy.data.node_groups[RR_node_name].nodes
    if not context.scene.render_raw.use_values or context.scene.render_raw.texture == 0:
        nodes['Texture'].mute = True
    else: 
        nodes['Texture'].mute = False
        nodes['Texture'].inputs['Strength'].default_value = context.scene.render_raw.texture
        nodes['Texture'].inputs['Keep Color'].default_value = context.scene.render_raw.texture_color

def update_clarity(self, context):
    nodes = bpy.data.node_groups[RR_node_name].nodes
    if not context.scene.render_raw.use_values or context.scene.render_raw.clarity == 0:
        nodes['Clarity'].mute = True
    else: 
        nodes['Clarity'].mute = False
        nodes['Clarity'].inputs['Strength'].default_value = context.scene.render_raw.clarity
        nodes['Clarity'].inputs['Size'].default_value = context.scene.render_raw.clarity_size

def update_details_panel(self, context):
    update_sharpness(self, context)
    update_texture(self, context)
    update_clarity(self, context)

# Value Panel 

def update_exposure(self, context):
    nodes = bpy.data.node_groups[RR_node_name].nodes
    if context.scene.render_raw.exposure == 0:
        nodes['Exposure'].mute = True
    else:
        nodes['Exposure'].mute = False
        nodes['Exposure'].inputs['Exposure'].default_value = context.scene.render_raw.exposure

def update_contrast(self, context):
    nodes = bpy.data.node_groups[RR_node_name].nodes
    if not context.scene.render_raw.use_values or context.scene.render_raw.contrast == 0:
        nodes['Contrast'].mute = True
    else:
        nodes['Contrast'].mute = False
        nodes['Contrast'].inputs['Contrast'].default_value = context.scene.render_raw.contrast

def update_values(self, context):
    values_node = bpy.data.node_groups[RR_node_name].nodes['Values']
    nodes = values_node.node_tree.nodes
    b = context.scene.render_raw.blacks
    w = context.scene.render_raw.whites
    s = context.scene.render_raw.shadows + 0.5
    h = context.scene.render_raw.highlights + 0.5
    if not context.scene.render_raw.use_values or (b == 0 and w == 0 and s == 0.5 and h == 0.5):
        values_node.mute = True
    else:
        values_node.mute = False
        nodes['Values Black Level'].outputs[0].default_value = -b
        white_level = -w + 1
        nodes['Values'].inputs['White Level'].default_value = [white_level, white_level, white_level, 1]
        curve = nodes['Values'].mapping.curves[3]
        curve.points[1].location[1] = 0.25 + ((s - 0.5) / 2)
        curve.points[2].location[1] = 0.75 + ((h - 0.5) / 2)
        nodes['Values'].mapping.update()
        nodes['Values'].update()

def update_value_panel(self, context):
    update_contrast(self, context)
    update_values(self, context)
    update_details_panel(self, context)
    bpy.data.node_groups[RR_node_name].nodes['Curves'].mute = not context.scene.render_raw.use_values


# Color Panel 
    
def update_saturation(self, context):
    nodes = bpy.data.node_groups[RR_node_name].nodes
    if not context.scene.render_raw.use_colors or context.scene.render_raw.saturation == 1:
        nodes['Saturation'].mute = True
    else:
        nodes['Saturation'].mute = False
        nodes['Saturation'].inputs['Saturation'].default_value = context.scene.render_raw.saturation
        nodes['Saturation'].inputs['Perceptual'].default_value = context.scene.render_raw.saturation_perceptual

def update_color_boost(self, context):
    nodes = bpy.data.node_groups[RR_node_name].nodes
    if not context.scene.render_raw.use_colors or context.scene.render_raw.color_boost == 0:
        nodes['Color Boost'].mute = True
    else:
        nodes['Color Boost'].mute = False
        nodes['Color Boost'].inputs['Strength'].default_value = context.scene.render_raw.color_boost

def update_white_balance(self, context):
    nodes = bpy.data.node_groups[RR_node_name].nodes
    if not context.scene.render_raw.use_colors or (context.scene.render_raw.temperature == 0.5 and context.scene.render_raw.tint == 0.5):
        nodes['White Balance'].mute = True
    else:
        nodes['White Balance'].mute = False
        nodes['White Balance'].inputs['Temperature'].default_value = context.scene.render_raw.temperature
        nodes['White Balance'].inputs['Tint'].default_value = context.scene.render_raw.tint

def update_hue(self, context):
    hue_correct_node = bpy.data.node_groups[RR_node_name].nodes['Hue Correct']
    nodes = hue_correct_node.node_tree.nodes
    settings = context.scene.render_raw
    controls = [
        settings.red_hue,     settings.red_value,     settings.red_saturation, 
        settings.orange_hue,  settings.orange_value,  settings.orange_saturation, 
        settings.yellow_hue,  settings.yellow_value,  settings.yellow_saturation, 
        settings.green_hue,   settings.green_value,   settings.green_saturation, 
        settings.teal_hue,    settings.teal_value,    settings.teal_saturation, 
        settings.blue_hue,    settings.blue_value,    settings.blue_saturation, 
        settings.pink_hue,    settings.pink_value,    settings.pink_saturation, 
    ]
    if not context.scene.render_raw.use_colors or all([x == 0.5 for x in controls]):
        hue_correct_node.mute = True
    else:
        hue_correct_node.mute = False

        hue = nodes['Hue Correct'].mapping.curves[0]
        hue.points[0].location[1] = 0.5 - ((0.5 - settings.red_hue) / 2)
        hue.points[7].location[1] = 0.5 - ((0.5 - settings.red_hue) / 2)
        hue.points[1].location[1] = 0.5 - ((0.5 - settings.orange_hue) / 6)
        hue.points[2].location[1] = 0.5 - ((0.5 - settings.yellow_hue) / 2)
        hue.points[3].location[1] = 0.5 - ((0.5 - settings.green_hue) / 2)
        hue.points[4].location[1] = 0.5 - ((0.5 - settings.teal_hue) / 2)
        hue.points[5].location[1] = 0.5 - ((0.5 - settings.blue_hue) / 2)
        hue.points[6].location[1] = 0.5 - ((0.5 - settings.pink_hue) / 2)

        saturation = nodes['Hue Correct'].mapping.curves[1]
        saturation.points[0].location[1] = settings.red_saturation
        saturation.points[7].location[1] = settings.red_saturation
        saturation.points[1].location[1] = settings.orange_saturation
        saturation.points[2].location[1] = settings.yellow_saturation
        saturation.points[3].location[1] = settings.green_saturation
        saturation.points[4].location[1] = settings.teal_saturation
        saturation.points[5].location[1] = settings.blue_saturation
        saturation.points[6].location[1] = settings.pink_saturation

        value = nodes['Hue Correct'].mapping.curves[2]
        value.points[0].location[1] = settings.red_value
        value.points[7].location[1] = settings.red_value
        value.points[1].location[1] = settings.orange_value
        value.points[2].location[1] = settings.yellow_value
        value.points[3].location[1] = settings.green_value
        value.points[4].location[1] = settings.teal_value
        value.points[5].location[1] = settings.blue_value
        value.points[6].location[1] = settings.pink_value

        nodes['Hue Correct'].mapping.update()
        nodes['Hue Correct'].update()

def update_value_saturation(self, context):
    nodes = bpy.data.node_groups[RR_node_name].nodes['Value Saturation'].node_tree.nodes
    settings = context.scene.render_raw
    if not settings.use_colors:
        nodes['Shadow Saturation'].mute = True
        nodes['Midtone Saturation'].mute = True
        nodes['Highlight Saturation'].mute = True
    else:
        nodes['Shadow Saturation'].mute = settings.shadow_saturation == 1
        nodes['Midtone Saturation'].mute = settings.midtone_saturation == 1
        nodes['Highlight Saturation'].mute = settings.highlight_saturation == 1

        nodes['Shadow Saturation'].inputs['Saturation'].default_value = settings.shadow_saturation
        nodes['Midtone Saturation'].inputs['Saturation'].default_value = settings.midtone_saturation
        nodes['Highlight Saturation'].inputs['Saturation'].default_value = settings.highlight_saturation

        nodes['Shadow Saturation'].inputs['Perceptual'].default_value = settings.value_saturation_perceptual
        nodes['Midtone Saturation'].inputs['Perceptual'].default_value = settings.value_saturation_perceptual
        nodes['Highlight Saturation'].inputs['Perceptual'].default_value = settings.value_saturation_perceptual

        nodes['Shadow Saturation Range'].color_ramp.elements[1].position = 0.25 * (settings.shadow_saturation_range * 2)
        nodes['Shadow Saturation Range'].color_ramp.elements[2].position = 0.5 * (settings.shadow_saturation_range * 2)

        nodes['Midtone Saturation Range'].color_ramp.elements[0].position = 0.25 * (-settings.midtone_saturation_range * 2) + 0.5
        nodes['Midtone Saturation Range'].color_ramp.elements[2].position = 0.75 * (settings.midtone_saturation_range / 1.5) + 0.5

        nodes['Highlight Saturation Range'].color_ramp.elements[0].position = (0.5 * (-settings.highlight_saturation_range * 2)) + 1
        nodes['Highlight Saturation Range'].color_ramp.elements[1].position = (0.25 * (-settings.highlight_saturation_range * 2)) + 1


def update_color_balance(self, context):
    nodes = bpy.data.node_groups[RR_node_name].nodes
    balance_nodes = bpy.data.node_groups[RR_node_name].nodes['Color Balance'].node_tree.nodes
    settings = context.scene.render_raw
    if not settings.use_colors:
        balance_nodes['Color Balance'].mute = True
        nodes['OPS'].mute = True
    else:
        balance_nodes['Color Balance'].mute = (
            get_rgb(settings.lift_color) == [1, 1, 1] and 
            get_rgb(settings.gamma_color) == [1, 1, 1] and 
            get_rgb(settings.gain_color) == [1, 1, 1]
        )
        nodes['OPS'].mute = (
            get_rgb(settings.offset_color) == [0, 0, 0] and 
            get_rgb(settings.power_color) == [1, 1, 1] and 
            get_rgb(settings.slope_color) == [1, 1, 1]
        )

        balance_nodes['Color Balance'].lift = settings.lift_color
        balance_nodes['Color Balance'].gamma = settings.gamma_color
        balance_nodes['Color Balance'].gain = settings.gain_color

        nodes['OPS'].offset = settings.offset_color
        nodes['OPS'].power = settings.power_color
        nodes['OPS'].slope = settings.slope_color

def update_color_blending(self, context):
    nodes = bpy.data.node_groups[RR_node_name].nodes['Color Balance'].node_tree.nodes
    settings = context.scene.render_raw
    if not settings.use_colors:
        nodes['Shadow Color'].mute = True
        nodes['Midtone Color'].mute = True
        nodes['Highlight Color'].mute = True
    else:
        nodes['Shadow Color'].mute = False
        nodes['Midtone Color'].mute = False
        nodes['Highlight Color'].mute = False

        nodes['Shadow Color'].inputs[2].default_value = set_alpha(settings.shadow_color, 1)
        nodes['Midtone Color'].inputs[2].default_value = set_alpha(settings.midtone_color, 1)
        nodes['Highlight Color'].inputs[2].default_value = set_alpha(settings.highlight_color, 1)

        nodes['Shadow Range'].color_ramp.elements[1].position = 0.25 * (settings.shadow_range * 2)
        nodes['Shadow Range'].color_ramp.elements[2].position = 0.5 * (settings.shadow_range * 2)

        nodes['Midtone Range'].color_ramp.elements[0].position = 0.25 * (-settings.midtone_range * 2) + 0.5
        nodes['Midtone Range'].color_ramp.elements[2].position = 0.75 * (settings.midtone_range / 1.5) + 0.5

        nodes['Highlight Range'].color_ramp.elements[0].position = (0.5 * (-settings.highlight_range * 2)) + 1
        nodes['Highlight Range'].color_ramp.elements[1].position = (0.25 * (-settings.highlight_range * 2)) + 1

        nodes['Shadow Fac'].inputs[1].default_value = settings.shadow_factor
        nodes['Midtone Fac'].inputs[1].default_value = settings.midtone_factor
        nodes['Highlight Fac'].inputs[1].default_value = settings.highlight_factor


def update_color_panel(self, context):
    update_saturation(self, context)
    update_color_boost(self, context)
    update_white_balance(self, context)
    update_color_balance(self, context)
    update_color_blending(self, context)
    update_hue(self, context)
    update_value_saturation(self, context)


# Effects Panel 
    
def update_vignette(self, context):
    settings = context.scene.render_raw
    nodes = bpy.data.node_groups[RR_node_name].nodes
    if not settings.use_effects or settings.vignette_value == 0:
        nodes['Vignette'].mute = True
    else: 
        nodes['Vignette'].mute = False
        nodes['Vignette'].inputs['Strength'].default_value = settings.vignette_value
        nodes['Vignette'].inputs['Highlights'].default_value = settings.vignette_highlights
        nodes['Vignette'].inputs['Feathering'].default_value = settings.vignette_feathering
        nodes['Vignette'].inputs['Roundness'].default_value = settings.vignette_roundness
        nodes['Vignette'].inputs['Scale X'].default_value = settings.vignette_scale_x - 0.01
        nodes['Vignette'].inputs['Scale Y'].default_value = settings.vignette_scale_y - 0.01
        nodes['Vignette'].inputs['Shift X'].default_value = settings.vignette_shift_x
        nodes['Vignette'].inputs['Shift Y'].default_value = settings.vignette_shift_y

def update_bloom(self, context):
    settings = context.scene.render_raw
    nodes = bpy.data.node_groups[RR_node_name].nodes['Glare'].node_tree.nodes
    links = bpy.data.node_groups[RR_node_name].nodes['Glare'].node_tree.links

    nodes['Glare Alpha'].mute = (
        not settings.use_effects or (settings.bloom == 0 and settings.streaks == 0)
    )

    if not settings.use_effects or settings.glare == 0 or settings.bloom == 0:
        nodes['Bloom'].mute = True
        nodes['Glare'].mute = True
    else:
        if bpy.app.version < (4, 2, 0):
            # Fakes bloom with multiple blur nodes before better bloom was implemented
            nodes['Bloom'].mute = False
            links.new(nodes['Bloom'].outputs[0], nodes['Ghosting'].inputs[0])
            nodes['Bloom'].inputs['Fac'].default_value = settings.bloom * settings.glare
            nodes['Bloom'].inputs['Threshold'].default_value = settings.glare_threshold + 0.001
            if settings.glare_quality == 5:
                nodes['Bloom'].node_tree.nodes['Blur 1'].mute = False
                nodes['Bloom'].node_tree.nodes['Blur 2'].mute = False
                nodes['Bloom'].node_tree.nodes['Blur 3'].mute = False
                nodes['Bloom'].node_tree.nodes['Blur 4'].mute = False
                nodes['Bloom'].node_tree.nodes['Blur 5'].mute = False
            elif settings.glare_quality == 4:
                nodes['Bloom'].node_tree.nodes['Blur 1'].mute = False
                nodes['Bloom'].node_tree.nodes['Blur 2'].mute = False
                nodes['Bloom'].node_tree.nodes['Blur 3'].mute = False
                nodes['Bloom'].node_tree.nodes['Blur 4'].mute = False
                nodes['Bloom'].node_tree.nodes['Blur 5'].mute = True
            elif settings.glare_quality == 3:
                nodes['Bloom'].node_tree.nodes['Blur 1'].mute = True
                nodes['Bloom'].node_tree.nodes['Blur 2'].mute = False
                nodes['Bloom'].node_tree.nodes['Blur 3'].mute = False
                nodes['Bloom'].node_tree.nodes['Blur 4'].mute = False
                nodes['Bloom'].node_tree.nodes['Blur 5'].mute = True
            elif settings.glare_quality == 2:
                nodes['Bloom'].node_tree.nodes['Blur 1'].mute = True
                nodes['Bloom'].node_tree.nodes['Blur 2'].mute = True
                nodes['Bloom'].node_tree.nodes['Blur 3'].mute = False
                nodes['Bloom'].node_tree.nodes['Blur 4'].mute = False
                nodes['Bloom'].node_tree.nodes['Blur 5'].mute = True
            elif settings.glare_quality == 1:
                nodes['Bloom'].node_tree.nodes['Blur 1'].mute = True
                nodes['Bloom'].node_tree.nodes['Blur 2'].mute = True
                nodes['Bloom'].node_tree.nodes['Blur 3'].mute = True
                nodes['Bloom'].node_tree.nodes['Blur 4'].mute = False
                nodes['Bloom'].node_tree.nodes['Blur 5'].mute = True
            # nodes['Bloom'].inputs['Blend Highlights'].default_value = settings.bloom_blending
        else:
            nodes['Glare'].mute = False
            links.new(nodes['Glare'].outputs[0], nodes['Ghosting'].inputs[0])
            nodes['Glare'].glare_type = 'BLOOM'
            nodes['Glare'].mix = settings.bloom * settings.glare - 1
            nodes['Glare'].threshold = settings.glare_threshold + 0.001
            nodes['Glare'].size = settings.bloom_size
            if settings.glare_quality == 5:
                nodes['Glare'].quality = 'HIGH'
            elif settings.glare_quality == 4:
                nodes['Glare'].quality = 'MEDIUM'
            elif settings.glare_quality == 3:
                nodes['Glare'].quality = 'MEDIUM'
            elif settings.glare_quality == 2:
                nodes['Glare'].quality = 'LOW'
            elif settings.glare_quality == 1:
                nodes['Glare'].quality = 'LOW'


def update_streaks(self, context):
    settings = context.scene.render_raw
    nodes = bpy.data.node_groups[RR_node_name].nodes['Glare'].node_tree.nodes

    nodes['Glare Alpha'].mute = (
        not settings.use_effects or (settings.bloom == 0 and settings.streaks == 0)
    )
    
    if not settings.use_effects or settings.glare == 0 or settings.streaks == 0:
        nodes['Streaks'].mute = True
        nodes['Streaks Mix'].mute = True
    else:
        nodes['Streaks'].mute = False
        nodes['Streaks Mix'].mute = False
        nodes['Streaks Strength'].outputs[0].default_value = settings.streaks * settings.glare
        nodes['Streaks'].mix = (settings.streaks * settings.glare) - 1
        nodes['Streaks'].threshold = settings.glare_threshold
        nodes['Streaks'].streaks = settings.streak_count
        nodes['Streaks'].angle_offset = settings.streak_angle
        nodes['Streaks'].fade = map_range(settings.streak_length, 0, 1, 0.9, 1)
        '''
        # Disabling this because it changes the streak length 
        if settings.glare_quality == 5:
            nodes['Streaks'].quality = 'HIGH'
        elif settings.glare_quality == 4:
            nodes['Streaks'].quality = 'HIGH'
        elif settings.glare_quality == 3:
            nodes['Streaks'].quality = 'MEDIUM'
        elif settings.glare_quality == 2:
            nodes['Streaks'].quality = 'MEDIUM'
        elif settings.glare_quality == 1:
            nodes['Streaks'].quality = 'LOW'
        '''
        
def update_ghosting(self, context):
    settings = context.scene.render_raw
    nodes = bpy.data.node_groups[RR_node_name].nodes['Glare'].node_tree.nodes

    nodes['Glare Alpha'].mute = (
        not settings.use_effects or (settings.bloom == 0 and settings.streaks == 0)
    )
    
    if not settings.use_effects or settings.glare == 0 or settings.ghosting == 0:
        nodes['Ghosting'].mute = True
    else:
        nodes['Ghosting'].mute = False
        nodes['Ghosting'].mix = settings.ghosting / 4 * settings.glare - 1
        nodes['Ghosting'].threshold = settings.glare_threshold
        if settings.glare_quality == 5:
            nodes['Ghosting'].quality = 'HIGH'
        elif settings.glare_quality == 4:
            nodes['Ghosting'].quality = 'MEDIUM'
        elif settings.glare_quality == 3:
            nodes['Ghosting'].quality = 'MEDIUM'
        elif settings.glare_quality == 2:
            nodes['Ghosting'].quality = 'LOW'
        elif settings.glare_quality == 1:
            nodes['Ghosting'].quality = 'LOW'

def update_glare(self, context):
    update_bloom(self, context)
    update_streaks(self, context)
    update_ghosting(self, context)

def update_distortion(self, context):
    nodes = bpy.data.node_groups[RR_node_name].nodes
    if not context.scene.render_raw.use_effects or (context.scene.render_raw.distortion == 0 and context.scene.render_raw.dispersion == 0):
        nodes['Lens Distortion'].mute = True
    else:
        nodes['Lens Distortion'].mute = False
        nodes['Lens Distortion'].inputs['Distortion'].default_value = context.scene.render_raw.distortion / 2
        nodes['Lens Distortion'].inputs['Dispersion'].default_value = context.scene.render_raw.dispersion / 4

def update_grain(self, context):
    nodes = bpy.data.node_groups[RR_node_name].nodes

    if not context.scene.render_raw.use_effects or context.scene.render_raw.grain == 0 or context.scene.render_raw.grain_method == 'ACCURATE':
        nodes['Film Grain Fast'].mute = True
    else:
        nodes['Film Grain Fast'].mute = False
        nodes['Film Grain Fast'].inputs['Strength'].default_value = context.scene.render_raw.grain
        nodes['Film Grain Fast'].inputs['Scale'].default_value = context.scene.render_raw.grain_scale
        nodes['Film Grain Fast'].inputs['Aspect Correction'].default_value = context.scene.render_raw.grain_aspect
        nodes['Film Grain Fast'].inputs['Saturation'].default_value = context.scene.render_raw.grain_saturation
        nodes['Film Grain Fast'].node_tree.nodes['Animate Offset'].mute = not context.scene.render_raw.grain_is_animated
        nodes['Film Grain Fast'].node_tree.links.new(
            nodes['Film Grain Fast'].node_tree.nodes[f'Step {context.scene.render_raw.grain_steps}'].outputs[0],
            nodes['Film Grain Fast'].node_tree.nodes['HSV'].inputs[0]
        )

    if not context.scene.render_raw.use_effects or context.scene.render_raw.grain == 0 or context.scene.render_raw.grain_method == 'FAST':
        nodes['Film Grain Accurate'].mute = True
    else:
        nodes['Film Grain Accurate'].mute = False
        nodes['Film Grain Accurate'].inputs['Strength'].default_value = context.scene.render_raw.grain
        nodes['Film Grain Accurate'].inputs['Scale'].default_value = context.scene.render_raw.grain_scale
        nodes['Film Grain Accurate'].inputs['Aspect Correction'].default_value = context.scene.render_raw.grain_aspect
        nodes['Film Grain Accurate'].inputs['Saturation'].default_value = context.scene.render_raw.grain_saturation
        nodes['Film Grain Accurate'].node_tree.nodes['Step 1'].node_tree.nodes['Animate Offset'].mute = not context.scene.render_raw.grain_is_animated
        nodes['Film Grain Accurate'].node_tree.links.new(
            nodes['Film Grain Accurate'].node_tree.nodes[f'Step {context.scene.render_raw.grain_steps}'].outputs[0],
            nodes['Film Grain Accurate'].node_tree.nodes['Group Output'].inputs[0]
        )

def update_effects_panel(self, context):
    update_vignette(self, context)
    update_distortion(self, context)
    update_glare(self, context)
    update_grain(self, context)


# Master  
    
def reset_RR(context):
    if hasattr(context.scene, 'render_raw'):
        settings = context.scene.render_raw

        from .operators.op_presets import preset_settings_to_skip
        for key in settings.keys():
            if key not in preset_settings_to_skip and key in settings.bl_rna.properties.keys() and key != 'exposure':
                if settings.bl_rna.properties[key].subtype == 'COLOR':
                    settings[key] = settings.bl_rna.properties[key].default_array
                else:
                    settings[key] = settings.bl_rna.properties[key].default

        from .utilities.curves import RGB_curve_default, set_curve_node
        nodes = bpy.data.node_groups[RR_node_name].nodes
        set_curve_node(nodes['Curves'], RGB_curve_default)
        color_balance_nodes = nodes['Color Balance'].node_tree.nodes
        color_balance_nodes['Highlight Color'].blend_type = 'SOFT_LIGHT'
        color_balance_nodes['Midtone Color'].blend_type = 'SOFT_LIGHT'
        color_balance_nodes['Shadow Color'].blend_type = 'SOFT_LIGHT'

def update_view_transform(self, context):
    nodes = bpy.data.node_groups[RR_node_name].nodes
    settings = context.scene.render_raw
    context.scene.node_tree.nodes[RR_node_name].mute = settings.view_transform == 'False Color'
    nodes['ACES Gamma'].mute = settings.view_transform != 'ACEScg' 
    if settings.view_transform == 'False Color':
        context.scene.view_settings.view_transform = 'False Color'
    else:
        context.scene.view_settings.view_transform = 'Raw'
        nodes['Convert Colorspace'].to_color_space = settings.view_transform
            
def enable_RR(self, context):
    was_using_nodes = bpy.context.scene.use_nodes
    bpy.context.scene.use_nodes = True

    prefs = get_prefs(context)
    if prefs.enable_compositing != 'NONE':
        enable_viewport_compositing(context, prefs.enable_compositing)
    if bpy.app.version < (4, 2, 0):
        if prefs.enable_OpenCL:
            context.scene.node_tree.use_opencl = True
        if prefs.enable_buffer_groups:
            context.scene.node_tree.use_groupnode_buffer = True

    nodes = context.scene.node_tree.nodes
    links = context.scene.node_tree.links
    settings = context.scene.render_raw

    # Import RR node group 
    is_RR_node_created = False

    if RR_node_name in [x.name for x in bpy.data.node_groups]:
        if RR_node_name in [x.name for x in nodes]:
            RR_node = nodes[RR_node_name]
        else:
            RR_node = nodes.new("CompositorNodeGroup")
            RR_node.name = RR_node_name
            RR_node.width = 175
            is_RR_node_created = True
        RR_node.node_tree = bpy.data.node_groups[RR_node_name]
        check_node_version()
    else:
        RR_node = append_node(self, nodes, RR_node_name)
        RR_node.name = RR_node_name
        is_RR_node_created = True
        set_node_version()

    # Set up compositing inputs and outputs 
    if is_RR_node_created:
        has_composite_node = False
        for node in nodes:
            if node.bl_idname == 'CompositorNodeComposite':
                composite_node = node
                has_composite_node = True
        if not has_composite_node:
            composite_node = nodes.new('CompositorNodeComposite')
        RR_node.location = composite_node.location
        composite_node.location[0] += 200

        if was_using_nodes and composite_node.inputs[0].links:
            from_socket = composite_node.inputs[0].links[0].from_socket
            links.new(from_socket, RR_node.inputs[0])
        else:
            has_render_layers_node = False
            for node in nodes:
                if node.bl_idname == 'CompositorNodeRLayers':
                    render_layers_node = node
                    has_render_layers_node = True
            if not has_render_layers_node:
                render_layers_node = nodes.new('CompositorNodeRLayers')
                render_layers_node.location[0] = -300
            links.new(render_layers_node.outputs[0], RR_node.inputs[0])

        links.new(RR_node.outputs[0], composite_node.inputs[0])

    for node in nodes:
        if node.bl_idname == 'CompositorNodeViewer':
            links.new(RR_node.outputs[0], node.inputs[0])
            break

    # Convert settings to RR nodes
    transforms = view_transforms_enable

    keys = [x for x in context.scene.render_raw.keys()]
    for key in keys:
        settings[key] = context.scene.render_raw[key]
    settings.view_transform = transforms[context.scene.view_settings.view_transform]
    context.scene['render_raw']['prev_look'] = context.scene.view_settings.look
    context.scene['render_raw']['prev_use_curves'] = context.scene.view_settings.use_curve_mapping
    context.scene['render_raw']['prev_exposure'] = context.scene.view_settings.exposure
    settings.exposure = context.scene.view_settings.exposure
    context.scene.view_settings.exposure = 0
    context.scene.view_settings.look = 'None'
    context.scene.view_settings.use_curve_mapping = False

    from .operators.op_presets import refresh_presets
    refresh_presets(context)

    update_value_panel(self, context)
    update_color_panel(self, context)
    update_details_panel(self, context)
    update_effects_panel(self, context)


def disable_RR(self, context):
    settings = context.scene.render_raw
    transforms = view_transforms_disable

    if transforms[settings.view_transform]:
        context.scene.view_settings.view_transform = transforms[settings.view_transform]

    if settings.use_values and hasattr(settings, 'exposure'):
        context.scene.view_settings.exposure = settings.exposure
    elif hasattr(settings, 'prev_exposure'):
        context.scene.view_settings.exposure = settings.prev_exposure
    else:
        context.scene.view_settings.exposure = 0

    if hasattr(context.scene, 'render_raw'):
        if hasattr(settings, 'prev_look'):
            prev_look = settings.prev_look
            view_transform = context.scene.view_settings.view_transform
            if prev_look == 'None':
                context.scene.view_settings.look = 'None'
            elif view_transform == 'AgX':
                context.scene.view_settings.look = f"{view_transform} - {prev_look}"
            else:
                context.scene.view_settings.look = prev_look
        if hasattr(settings, 'prev_use_curves'):
            context.scene.view_settings.use_curve_mapping = settings.prev_use_curves

    # Remove nodes 
    if context.scene.node_tree and RR_node_name in [x.name for x in context.scene.node_tree.nodes]:
        nodes = context.scene.node_tree.nodes
        links = context.scene.node_tree.links

        if nodes[RR_node_name].inputs[0].links:
            from_socket = nodes[RR_node_name].inputs[0].links[0].from_socket
            for link in nodes[RR_node_name].outputs[0].links:
                to_socket = link.to_socket
                to_node = nodes[RR_node_name].outputs[0].links[0].to_node
                if to_node.bl_idname == 'CompositorNodeComposite':
                    to_node.location[0] -= 200
                links.new(from_socket, to_socket)

        nodes.remove(nodes[RR_node_name])

def manage_RR(self, context):
    settings = context.scene.render_raw
    # enabled = settings.enable_RR and any([settings.use_values, settings.use_colors, settings.use_details, settings.use_effects])
    if settings.enable_RR:
        enable_RR(self, context)
    else:
        disable_RR(self, context)

def refresh_RR_nodes(self, context):
    disable_RR(self, context)

    if RR_node_name in bpy.data.node_groups:
        sub_groups = [x.node_tree for x in bpy.data.node_groups[RR_node_group_name].nodes if x.bl_label == 'Group']
        bpy.data.node_groups.remove(bpy.data.node_groups[RR_node_group_name])
        for g in sub_groups:
            bpy.data.node_groups.remove(g)

    enable_RR(self, context)

    for scene in bpy.data.scenes:
        if scene.use_nodes and RR_node_name in [x.name for x in scene.node_tree.nodes]:
            scene.node_tree.nodes[RR_node_name].node_tree = bpy.data.node_groups[RR_node_group_name]

    
