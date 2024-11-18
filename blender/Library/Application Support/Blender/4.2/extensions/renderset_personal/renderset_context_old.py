# copyright (c) 2018- polygoniq xyz s.r.o.

import bpy
import typing

# This file contains a definition of RendersetContext class from renderset older than 2.0.
# It is used to load old render contexts from the file and convert them to the new format.

MODULE_CLASSES: typing.List[typing.Type] = []

# Not used anymore. Keeping just for reference of what was stored in the old format.
SCENE_SYNCED_PROPERTY_GROUPS_JSON: typing.Dict[
    str, typing.Dict[str, typing.Union[str, bool, typing.List[str]]]
] = {
    "display_settings": {},
    "view_settings": {
        "ignored_properties": [
            "curve_mapping",
        ],
    },
    "cycles": {
        "ignored_properties": [
            "preview_denoiser",
            "use_preview_denoising",
            "preview_denoising",
            "preview_denoising_start_sample",
            "preview_samples",
            "use_progressive_refine",
            "debug_use_spatial_splits",
            "debug_use_hair_bvh",
            "debug_bvh_time_steps",
            "preview_start_resolution",
        ],
    },
    "eevee": {
        "ignored_properties": [
            "use_taa_reprojection",
            "taa_samples",
        ],
    },
    "octane": {
        "ignored_properties": [],
        # Octane is not present in vanilla versions of Blender
        "optional": True,
    },
    "luxcore_config": {
        "path_override": "luxcore.config",
        "ignored_properties": ["path"],
        # LuxCoreRenderer is not present in vanilla versions of Blender
        "optional": True,
    },
    "luxcore_config_path": {
        "path_override": "luxcore.config.path",
        "ignored_properties": [],
        # LuxCoreRenderer is not present in vanilla versions of Blender
        "optional": True,
    },
    "render": {
        "ignored_properties": [
            "filepath",  # filepath is overridden by renderset itself
            "threads_mode",
            "threads",
            "tile_x",
            "tile_y",
            "use_save_buffers",
            "use_persistent_data",
            "preview_pixel_size",
            "use_high_quality_normals",
            "ffmpeg",
            "image_settings",
            "views",
            "stereo_views",
            "motion_blur_shutter_curve",
            "bake",
        ],
    },
    "render.ffmpeg": {},
    "render.image_settings": {
        "ignored_properties": [
            "stereo_3d_format",
            "view_settings",
            "display_settings",
        ],
    },
    "render.image_settings.stereo_3d_format": {},
    "render.image_settings.view_settings": {
        "ignored_properties": [
            "curve_mapping",
        ],
    },
}


class RendersetContextOld(bpy.types.PropertyGroup):
    """All settings stored in one render context.
    Renderset context can be something like Outside_Sunset_Camera1.
    It remembers which camera to use, which world settings to use
    """

    custom_name: bpy.props.StringProperty(
        name="Name", description="Descriptive name of this render context", default="New Context"
    )

    include_in_render_all: bpy.props.BoolProperty(
        name="Include in Render All",
        description="Whether to render this context as part of 'Render All'",
        default=True,
    )

    override_output_folder_format: bpy.props.BoolProperty(
        name="Override Output Folder Format",
        description="Whether to use output folder format from Preferences or the one saved in this "
        "context",
        default=False,
    )

    output_folder_format: bpy.props.StringProperty(
        name="Output Folder Format",
        description="Output Folder Format specific to this context. Used only when "
        "Override Output Folder is enabled. Same variables as in preferences can be used here",
        default="",
        subtype='DIR_PATH',
    )

    camera: bpy.props.PointerProperty(
        name="Camera",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'CAMERA',
    )

    world: bpy.props.PointerProperty(
        name="World",
        type=bpy.types.World,
    )

    render_type: bpy.props.EnumProperty(
        name="Render Type",
        items=(
            ("still", "Still Image", "Render just one image", 'FILE_IMAGE', 1),
            (
                "animation",
                "Animation",
                "Render animation - all images between frame start and frame end",
                'FILE_MOVIE',
                2,
            ),
        ),
        default="still",
    )

    frame_current: bpy.props.IntProperty(name="Frame Current", default=1)

    frame_start: bpy.props.IntProperty(name="Frame Start", default=1)

    frame_end: bpy.props.IntProperty(name="Frame End", default=250)

    frame_step: bpy.props.IntProperty(name="Frame Step", default=1)

    # Scene settings serialized into json
    display_settings_json: bpy.props.StringProperty(default="{}")
    view_settings_json: bpy.props.StringProperty(default="{}")
    cycles_json: bpy.props.StringProperty(default="{}")
    eevee_json: bpy.props.StringProperty(default="{}")
    render_json: bpy.props.StringProperty(default="{}")
    render_ffmpeg_json: bpy.props.StringProperty(default="{}")
    render_image_settings_json: bpy.props.StringProperty(default="{}")
    render_image_settings_stereo_3d_format_json: bpy.props.StringProperty(default="{}")
    render_image_settings_view_settings_json: bpy.props.StringProperty(default="{}")
    # These are optional as Octane and Luxcore are not in vanilla Blender.
    octane_json: bpy.props.StringProperty(default="{}")
    luxcore_config_json: bpy.props.StringProperty(default="{}")
    luxcore_config_path_json: bpy.props.StringProperty(default="{}")

    # View layers', collections' and objects' visibility properties serialized into json
    view_layers_json: bpy.props.StringProperty(default="{}")
    root_collection_json: bpy.props.StringProperty(default="{}")
    objects_visibility_json: bpy.props.StringProperty(default="{}")


MODULE_CLASSES.append(RendersetContextOld)


def register():
    for cls in MODULE_CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(MODULE_CLASSES):
        bpy.utils.unregister_class(cls)
