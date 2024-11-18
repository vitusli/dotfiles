# copyright (c) 2018- polygoniq xyz s.r.o.

# RendersetContext is a class that stores the state of the Blender context (render settings,
# collections visibility, etc.) in a way that can be serialized to JSON and later deserialized back
# to the Blender context. By default RendersetContext stores only a subset of the context properties
# defined in serialize_utils.DEFAULT_SYNCED_SETTINGS. However, users can mark additional properties
# to be stored or mark default properties to be ignored, these changes are called overrides.
# RendersetContext doesn't store overrides directly, it just stores values of the properties in
# RendersetContext.synced_data_json, overrides are computed by comparing synced_data_json with
# serialize_utils.DEFAULT_SYNCED_SETTINGS.
#
# Visibilities of objects, collections and view_layers are not overridable by right-click overrides
# instead there are toggles for them in Preferences. This is because it make sense to always either
# remember or not remember visibilities for all objects, collections and view_layers.
#
# RendersetContext also stores some of its own bpy properties into synced_data_json. These are defined
# in RendersetContext.SERIALIZABLE_PROPERTIES. The motivation is to keep consistency with storing
# everything that should be remembered in one json, so future features are easier to implement.
# Currently we can serialize only one level of nested properties (pointer properties and collection
# items like post render actions cannot contain other collections or pointers).
#
# Actual values can differ from values in the synced_data_json of the currently active context,
# since we serialize/deserialize only when apply/sync is called. Thus for the currently active
# context, the ground truth are the current values, for all other contexts, the ground truth
# are values in synced_data_json.
#
# FORMAT of synced_data_json:
# It's a hierarchical dictionary with parts of property paths as keys.
#
# KEYS:
# Path to the property in the Blender is split by dots and brackets to form the hierarchical
# dictionary. Paths of PropertyGroups can be directly stored as a simple string names, since they
# won't change. However, we cannot simply use numeric indexes or names of Blender datablocks as keys
# (like bpy.data.objects["Cube"]), because they can change. Instead, we assign custom properties
# called renderset_uuid to Blender datablocks and use them as keys, so bpy.data.objects["Cube"] is
# translated to something like bpy.data.objects.RSET_UUID-1234567890abcdef. We use RSET_UUID- in
# order to distinguish between our uuids and Blender names when deserializing.
#
# VALUES:
# Currently only properties of types int, float, str, bool and types convertible to list[int] and
# list[float] (like mathutils.Vector or bpy.types.bpy_prop_array) are supported.
#
# Example:
# {
#     "bpy": {
#         "context": {
#             "scene": {
#                 "camera": "RSET_UUID-cd5b99c3ac9e4cd69ccb7e99f1f78daa",
#                 "frame_current": 1,
#                 "frame_end": 250,
#                 "frame_start": 1,
#                 "frame_step": 1,
#                 "world": "RSET_UUID-9c85aa0cafb745bfb6672f0502b61425",
#                 "collection": {  # This is root collection, it's always there and cannot be renamed, so we don't use uuid for it
#                     "hide_render": false,
#                     "hide_select": false,
#                     "hide_viewport": false,
#                     "children": {
#                         "RSET_UUID-15cd2baa12ea4dcea915671bf1302075": {  # This is custom collection from Outliner
#                             "hide_render": false,
#                             "hide_select": false,
#                             "hide_viewport": false,
#                             "children": {}
#                         }
#                     }
#                 },
#                 "cycles": {
#                     "samples": 4096,
#                 }
#                 "render": {
#                     "resolution_x": 1920,
#                     "image_settings": {
#                         "file_format": 'PNG'
#                     }
#                 }
#             }
#         }
#     }
# }
#
# Full stored json can be obtained using DumpStoredValues operator.

import bpy
import typing
import json
import os
import tempfile
import datetime
import shutil
import glob
import enum
import functools
import dataclasses
import copy
import logging
from . import polib
from . import utils
from . import compositor_helpers
from . import serialize_utils
from . import output_path_format
from . import renderset_context_old
from . import sync_overrides
from . import post_render_actions
from . import preferences
from . import scene_props

logger = logging.getLogger(f"polygoniq.{__name__}")


MODULE_CLASSES: typing.List[typing.Type] = []


TEMP_FILENAME = "temp_render"


class RenderType(enum.Enum):
    STILL = "still"
    ANIMATION = "animation"


def renderset_context_with_name_exists(
    self: 'RendersetContext',
    context: bpy.types.Context,
    name: str,
    cache: typing.Optional[typing.Dict[str, 'RendersetContext']] = None,
) -> bool:
    """Goes through all RendersetContexts that are present in context.scene,
    True is returned iff a context with given name exists and it is not equal to "self".
    """

    if cache is None:
        cache = {}

    if name in cache and cache[name] != self:
        return True

    for renderset_context in context.scene.renderset_contexts:
        if renderset_context == self:
            continue
        if renderset_context.custom_name == name:
            cache[name] = renderset_context
            return True

    return False


@polib.log_helpers_bpy.logged_operator
class RendersetContextAddVariable(
    output_path_format.OutputFormatAddVariableMixin, bpy.types.Operator
):
    bl_idname = "renderset.context_add_variable"

    def execute(self, context: bpy.types.Context):
        rset_context = get_active_renderset_context(context)
        if rset_context is None:
            self.report({'ERROR'}, "No active renderset context")
            return {'CANCELLED'}
        self.add_variable(rset_context.output_format)
        return {'FINISHED'}


MODULE_CLASSES.append(RendersetContextAddVariable)


@polib.log_helpers_bpy.logged_operator
class RendersetContextPostRenderActionAddVariable(
    output_path_format.OutputFormatAddVariableMixin, bpy.types.Operator
):
    bl_idname = "renderset.context_post_render_action_add_variable"

    def execute(self, context: bpy.types.Context):
        rset_context = get_active_renderset_context(context)
        if rset_context is None:
            self.report({'ERROR'}, "No active renderset context")
            return {'CANCELLED'}

        action = rset_context.post_render_actions.get_active()
        if action is None:
            self.report({'ERROR'}, "Invalid active post render action")
            return {'CANCELLED'}

        self.add_variable(action.output_format)
        return {'FINISHED'}


MODULE_CLASSES.append(RendersetContextPostRenderActionAddVariable)


class ReferencedDatablock(bpy.types.PropertyGroup):
    """A datablock referenced by the renderset context via a UUID in the json

    We have to wrap it in a PropertyGroup because CollectionProperty requires that.
    """

    datablock: bpy.props.PointerProperty(
        type=bpy.types.ID,
        description="Datablock that is assigned to this property group to be marked as used",
    )


MODULE_CLASSES.append(ReferencedDatablock)


class RendersetContext(bpy.types.PropertyGroup):
    """All settings stored in one render context.
    Renderset context can be something like Outside_Sunset_Camera1.
    It remembers which camera to use, which world settings to use
    """

    referenced_datablocks: bpy.props.CollectionProperty(
        type=ReferencedDatablock,
        name="Referenced Datablocks",
        description="Datablocks used by this context are assigned here to prevent them from being "
        "removed as orphan data. Since we store datablocks like world only as UUID strings in "
        "self.synced_data_json, they might not have any users if they are not used in the active "
        "context",
    )

    selected_for_multi_edit: bpy.props.BoolProperty(
        name="selected_for_multi_edit", default=False, options={'HIDDEN'}
    )

    ###
    # Properties that are used in self.prepare_for_render(), self.render(), ...
    # but are not here for storing values between different renderset contexts
    # TODO: Do they really need to be stored in renderset context?
    next_frame_to_render: bpy.props.IntProperty(
        name="next_frame_to_render", default=0, options={'HIDDEN'}
    )

    old_render_filepath: bpy.props.StringProperty(
        name="old_render_filepath", default="", options={'HIDDEN'}
    )

    temporary_output_folder_path: bpy.props.StringProperty(
        name="temporary_output_folder_path", default="", options={'HIDDEN'}
    )

    frozen_time: bpy.props.StringProperty(name="Frozen Time", default="", options={'HIDDEN'})

    execute_post_render_actions: bpy.props.BoolProperty(
        name="execute_post_render_actions", default=True, options={'HIDDEN'}
    )
    ###

    def generate_unique_name(self, context: bpy.types.Context, name_without_suffix: str) -> str:
        i = 1
        cache: typing.Dict[str, RendersetContext] = {}
        while i < 1000 and renderset_context_with_name_exists(
            self, context, f"{name_without_suffix}.{i:03}", cache
        ):
            i += 1
        return f"{name_without_suffix}.{i:03}"

    def set_custom_name(self, value: str) -> None:
        context = bpy.context
        stripped_name = value.strip()
        if renderset_context_with_name_exists(self, context, stripped_name):
            name_without_suffix = polib.utils_bpy.remove_object_duplicate_suffix(stripped_name)
            self["custom_name"] = self.generate_unique_name(context, name_without_suffix)
        else:
            self["custom_name"] = stripped_name

        if get_active_renderset_context(context) != self:
            # We allow to change the name from UI also for non-active contexts but ground truth
            # for non-active contexts is in json, so we need to update it.
            updated_dict = serialize_utils.apply_flattened_patch(
                self.synced_data_dict, {"self.custom_name": self["custom_name"]}
            )
            self.synced_data_json = json.dumps(updated_dict)

    def get_custom_name(self) -> str:
        return self["custom_name"] if "custom_name" in self else "New Context"

    SERIALIZABLE_PROPERTIES: typing.List[str] = []

    custom_name: bpy.props.StringProperty(
        name="Name",
        description="Descriptive name of this render context",
        set=set_custom_name,
        get=get_custom_name,
    )
    SERIALIZABLE_PROPERTIES.append("custom_name")

    def set_include_in_render_all(self, value: bool) -> None:
        self["include_in_render_all"] = value

        if get_active_renderset_context(bpy.context) != self:
            # We allow to change the toggle from UI also for non-active contexts but ground truth
            # for non-active contexts is in json, so we need to update it.
            updated_dict = serialize_utils.apply_flattened_patch(
                self.synced_data_dict, {"self.include_in_render_all": self["include_in_render_all"]}
            )
            self.synced_data_json = json.dumps(updated_dict)

    def get_include_in_render_all(self) -> bool:
        return self["include_in_render_all"] if "include_in_render_all" in self else True

    include_in_render_all: bpy.props.BoolProperty(
        name="Include in Render All",
        description="Whether to render this context as part of 'Render All'",
        set=set_include_in_render_all,
        get=get_include_in_render_all,
    )
    SERIALIZABLE_PROPERTIES.append("include_in_render_all")

    def override_output_folder_changed(self, context: bpy.types.Context) -> None:
        if not self.override_output_folder:
            return
        # If the output folder format is default one, we guess it's because it was never set
        # and we'll use current global value
        if self.output_format.folder_path == output_path_format.DEFAULT_FOLDER_PATH:
            scene_output_format = scene_props.get_output_format(bpy.context)
            self.output_format.folder_path = scene_output_format.folder_path

    override_output_folder: bpy.props.BoolProperty(
        name="Override Output Folder",
        description="Whether to use output folder format from Preferences or the one saved in this "
        "context",
        default=False,
        update=override_output_folder_changed,
    )
    SERIALIZABLE_PROPERTIES.append("override_output_folder")

    def override_output_filenames_changed(self, context: bpy.types.Context) -> None:
        if not self.override_output_filenames:
            return
        # If the filename is default one, we guess it's because it was never set
        # and we'll use current global value
        scene_output_format = scene_props.get_output_format(context)
        if (
            self.output_format.still_image_filename
            == output_path_format.DEFAULT_FILENAME_FORMATS[
                output_path_format.OutputFormatProperty.STILL_IMAGE_FILENAME.value
            ]
        ):
            self.output_format.still_image_filename = scene_output_format.still_image_filename
        if (
            self.output_format.animation_frame_filename
            == output_path_format.DEFAULT_FILENAME_FORMATS[
                output_path_format.OutputFormatProperty.ANIMATION_FRAME_FILENAME.value
            ]
        ):
            self.output_format.animation_frame_filename = (
                scene_output_format.animation_frame_filename
            )
        if (
            self.output_format.animation_movie_filename
            == output_path_format.DEFAULT_FILENAME_FORMATS[
                output_path_format.OutputFormatProperty.ANIMATION_MOVIE_FILENAME.value
            ]
        ):
            self.output_format.animation_movie_filename = (
                scene_output_format.animation_movie_filename
            )

    override_output_filenames: bpy.props.BoolProperty(
        name="Override Output Filenames",
        description="Whether to use output filenames from Preferences or the ones saved in this "
        "context",
        default=False,
        update=override_output_filenames_changed,
    )
    SERIALIZABLE_PROPERTIES.append("override_output_filenames")

    output_format: bpy.props.PointerProperty(
        type=output_path_format.OutputFormatProperties,
        description="Output format overrides for this context",
    )
    SERIALIZABLE_PROPERTIES.append("output_format")

    def override_post_render_actions_changed(self, context: bpy.types.Context) -> None:
        if not self.override_post_render_actions:
            return
        if len(self.post_render_actions.actions) > 0:
            return
        for action in scene_props.get_post_render_actions(context).actions:
            new_action = self.post_render_actions.actions.add()
            new_action.copy_properties(action)

    override_post_render_actions: bpy.props.BoolProperty(
        name="Override Post Render Actions",
        description="Whether to use Post Render Actions from Preferences or the ones saved in this "
        "context",
        default=False,
        update=override_post_render_actions_changed,
    )
    SERIALIZABLE_PROPERTIES.append("override_post_render_actions")

    post_render_actions: bpy.props.PointerProperty(
        type=post_render_actions.PostRenderActions,
        description="Post render action overrides for this context",
    )
    SERIALIZABLE_PROPERTIES.append("post_render_actions")

    render_type: bpy.props.EnumProperty(
        name="Render Type",
        items=[
            (RenderType.STILL.value, "Still Image", "Render just one image", 'FILE_IMAGE', 1),
            (
                RenderType.ANIMATION.value,
                "Animation",
                "Render animation - all images between frame start and frame end",
                'FILE_MOVIE',
                2,
            ),
        ],
    )
    SERIALIZABLE_PROPERTIES.append("render_type")

    def clear_caches(self, context: bpy.types.Context) -> None:
        if hasattr(self, "synced_data_dict"):
            del self.synced_data_dict
        if hasattr(self, "stored_props_dict"):
            del self.stored_props_dict
        if hasattr(self, "overrides"):
            del self.overrides

    synced_data_json: bpy.props.StringProperty(
        default="{}",
        description="JSON with everything we store in renderset context: "
        "scene settings, object and collection visibility, ..",
        update=clear_caches,
    )

    @functools.cached_property
    def synced_data_dict(self) -> typing.Dict[str, typing.Any]:
        try:
            return json.loads(self.synced_data_json)
        except Exception as e:
            logger.exception("Uncaught exception while loading json with scene settings!")
            return {}

    @functools.cached_property
    def stored_props_dict(self) -> typing.Dict[str, typing.Any]:
        """Returns a dictionary with all generic properties stored in this context.

        It contains only properties of primitive types (int, float, str, color) which can be
        serialized into renderset context/apply to Blender context in a generic way. It doesn't
        contain camera, world, view_layers, collection and objects which need uuids and other
        special handling when serializing/applying.
        """
        synced_data = copy.deepcopy(self.synced_data_dict)
        if "self" in synced_data:
            del synced_data["self"]
        scene_settings = synced_data.get("bpy", {}).get("context", {}).get("scene", {})
        if "camera" in scene_settings:
            del scene_settings["camera"]
        if "world" in scene_settings:
            del scene_settings["world"]
        if "view_layers" in scene_settings:
            del scene_settings["view_layers"]
        if "collection" in scene_settings:
            del scene_settings["collection"]
        if "objects" in scene_settings:
            del scene_settings["objects"]
        return synced_data

    @dataclasses.dataclass
    class Overrides:
        add: typing.Set[str]
        remove: typing.Set[str]

        def __len__(self):
            return len(self.add) + len(self.remove)

    @functools.cached_property
    def overrides(self) -> Overrides:
        """Returns property paths that are overridden in this context.

        Example:
            Overrides(
                add = {
                    bpy.context.scene.eevee.taa_render_samples,
                    bpy.context.scene.render.pixel_aspect_x,
                    bpy.context.scene.render.pixel_aspect_y
                },
                remove = {
                    bpy.context.scene.frame_current,
                    bpy.context.scene.frame_step
                }
            )
        defines that 'taa_render_samples', 'pixel_aspect_x' and 'pixel_aspect_y' is stored in this
        context even though it isn't defined in serialize_utils.DEFAULT_SYNCED_SETTINGS while
        'frame_current' and 'frame_step' isn't stored even though it is defined in
        serialize_utils.DEFAULT_SYNCED_SETTINGS.
        """
        flatten_default_synced_props = serialize_utils.flatten_dict(
            serialize_utils.DEFAULT_SYNCED_SETTINGS.serialize_bpy_props()
        )
        flatten_synced_data = serialize_utils.flatten_dict(self.stored_props_dict)
        added = flatten_synced_data.keys() - flatten_default_synced_props.keys()
        ignored = flatten_default_synced_props.keys() - flatten_synced_data.keys()
        return self.Overrides(add=added, remove=ignored)

    def add_overrides(self, prop_paths: typing.Iterable[str], action_store: bool) -> None:
        """Adds or removes stored properties from this context.

        In case the property should be stored in the context, the value of the property is taken\
        from the current Blender context.

        prop_path: Path to the property. Example: "bpy.context.scene.render.resolution_x"
        action_store: If True, the property will be stored in this context. If False, the property
            will be removed from this context.
        """
        prev_json_dict = self.synced_data_dict
        for prop_path in prop_paths:
            prop_parent_path, prop_name = sync_overrides.split_prop_to_path_and_name(prop_path)
            prop_parent_path = sync_overrides.expand_uuids(prop_parent_path)
            assert prop_parent_path is not None

            json_dict = prev_json_dict
            for prop in prop_parent_path.split("."):
                if prop not in json_dict:
                    json_dict[prop] = {}
                json_dict = json_dict[prop]

            if action_store:
                assert prop_name not in json_dict
                prop_container = sync_overrides.evaluate_prop_path(prop_parent_path)
                assert prop_container is not None
                prop_value = serialize_utils.get_serializable_property_value(
                    prop_container, prop_name
                )
                assert prop_value is not None
                json_dict[prop_name] = prop_value
            else:
                assert prop_name in json_dict
                del json_dict[prop_name]

        self.synced_data_json = json.dumps(prev_json_dict)

    def add_override(self, prop_path: str, action_store: bool) -> None:
        """Adds or removes stored property from this context.

        In case the property should be stored in the context, the value of the property is taken\
        from the current Blender context.

        prop_path: Path to the property. Example: "bpy.context.scene.render.resolution_x"
        action_store: If True, the property will be stored in this context. If False, the property
            will be removed from this context.
        """
        self.add_overrides([prop_path], action_store)

    def try_get_scene_settings(self) -> typing.Dict[str, typing.Any]:
        """Returns scene properties from 'json_dict'"""
        # We need to be cautious here. In case all properties from default synced scene settings
        # were overridden to not be synced, json_dict won't contain bpy.context.scene entry
        return self.synced_data_dict.get("bpy", {}).get("context", {}).get("scene", {})

    def ensure_scene_hierarchy_in_json(self, json_dict: typing.Dict[str, typing.Any]) -> None:
        """Ensures that 'json_dict' contains at least json_dict["bpy"]["context"]["scene"]"""
        if "bpy" not in json_dict:
            json_dict["bpy"] = {}
        if "context" not in json_dict["bpy"]:
            json_dict["bpy"]["context"] = {}
        if "scene" not in json_dict["bpy"]["context"]:
            json_dict["bpy"]["context"]["scene"] = {}

    @property
    def is_animation(self) -> bool:
        return self.render_type == RenderType.ANIMATION.value

    def generate_output_folder_path(
        self,
        time: typing.Optional[datetime.datetime] = None,
        frame_current: typing.Optional[int] = None,
        frame_start: typing.Optional[int] = None,
        frame_end: typing.Optional[int] = None,
        frame_step: typing.Optional[int] = None,
    ) -> str:
        scene_output_format = scene_props.get_output_format(bpy.context)
        output_folder_path = (
            self.output_format.folder_path
            if self.override_output_folder
            else scene_output_format.folder_path
        )

        return output_path_format.generate_folder_path(
            output_folder_path,
            self,
            time=time,
            frame_current=frame_current,
            frame_start=frame_start,
            frame_end=frame_end,
            frame_step=frame_step,
        )

    def generate_output_filename(
        self,
        is_movie_format: bool,
        time: typing.Optional[datetime.datetime] = None,
        render_pass: str = compositor_helpers.RenderPassType.COMPOSITE.value,
        frame_current: typing.Optional[int] = None,
        frame_start: typing.Optional[int] = None,
        frame_end: typing.Optional[int] = None,
        frame_step: typing.Optional[int] = None,
    ) -> str:
        scene_output_format = scene_props.get_output_format(bpy.context)
        animation_movie_filename = (
            self.output_format.animation_movie_filename
            if self.override_output_filenames
            else scene_output_format.animation_movie_filename
        )
        animation_frame_filename = (
            self.output_format.animation_frame_filename
            if self.override_output_filenames
            else scene_output_format.animation_frame_filename
        )
        still_image_filename = (
            self.output_format.still_image_filename
            if self.override_output_filenames
            else scene_output_format.still_image_filename
        )

        output_filename = output_path_format.select_output_filename(
            self.is_animation,
            is_movie_format,
            render_pass == compositor_helpers.RenderPassType.COMPOSITE.value,
            still_image_filename,
            animation_frame_filename,
            animation_movie_filename,
        )

        return output_path_format.generate_filename(
            output_filename,
            self,
            time=time,
            render_pass=render_pass,
            frame_current=frame_current,
            frame_start=frame_start,
            frame_end=frame_end,
            frame_step=frame_step,
        )

    def _get_all_output_folder_paths(
        self, context: bpy.types.Context, time: typing.Optional[datetime.datetime] = None
    ) -> typing.Iterable[str]:
        if time is None:
            time = datetime.datetime.now()
        if context.scene.render.is_movie_format or self.render_type == RenderType.STILL.value:
            yield self.generate_output_folder_path(time=time)
        else:
            for frame in range(
                context.scene.frame_start, context.scene.frame_end + 1, context.scene.frame_step
            ):
                yield self.generate_output_folder_path(time=time, frame_current=frame)

    def prepare_render_layers(self, context: bpy.types.Context, output_path: str) -> None:
        assert os.path.isdir(output_path)

        context.scene.use_nodes = True
        if context.scene.render.image_settings.file_format != 'OPEN_EXR_MULTILAYER':
            # OpenEXR multi-layer has all layers in one file, it doesn't make sense to split it
            # into multiple files

            compositor_helpers.ensure_render_layers_file_out(context.scene, output_path)
            # we already output composite node via context.scene.render.filepath
            # so we don't connect it anywhere

    def get_index(self, context: bpy.types.Context) -> int:
        for i, rset_context in enumerate(context.scene.renderset_contexts):
            if rset_context != self:
                continue

            return i

        raise RuntimeError(
            "Failed to infer index for RendersetContext. This context is not in the list!"
        )

    def prepare_for_render(
        self,
        context: bpy.types.Context,
        execute_post_render_actions: bool = True,
        time: typing.Optional[datetime.datetime] = None,
    ) -> None:
        prefs = utils.get_preferences(context)
        if time is None:
            time = datetime.datetime.now()
        self.frozen_time = time.isoformat()

        if self.temporary_output_folder_path is not None and os.path.isdir(
            self.temporary_output_folder_path
        ):
            shutil.rmtree(self.temporary_output_folder_path)
        self.temporary_output_folder_path = tempfile.mkdtemp(prefix="renderset_")

        # Remember what was in render.filepath so that we can put it back after we finish rendering
        self.old_render_filepath = context.scene.render.filepath
        context.scene.render.filepath = os.path.join(
            self.temporary_output_folder_path,
            (
                TEMP_FILENAME
                if self.is_animation
                else f"{TEMP_FILENAME}{context.scene.render.file_extension}"
            ),
        )

        self.execute_post_render_actions = execute_post_render_actions

        if prefs.automatic_render_layer_split:
            self.prepare_render_layers(context, self.temporary_output_folder_path)

        if self.is_animation:
            # frames in render context are not updated at this position
            self.next_frame_to_render = context.scene.frame_start

    def _get_rendered_temp_filename(self) -> str:
        context = bpy.context
        if self.is_animation:
            if context.scene.render.is_movie_format:
                return (
                    f"{TEMP_FILENAME}{context.scene.frame_start:04d}-{context.scene.frame_end:04d}"
                )
            return f"{TEMP_FILENAME}{context.scene.frame_current:04d}"
        return TEMP_FILENAME

    def render_finished_finalize_files(
        self,
        is_movie_format: bool,
        include_multiframe: bool,
        frame_current: typing.Optional[int],
        frame_start: typing.Optional[int],
        frame_end: typing.Optional[int],
        frame_step: typing.Optional[int],
        render_pass_extension_map: typing.Optional[typing.Dict[str, str]] = None,
        try_again_interval: float = 2.0,
    ) -> None:
        """Move files from temporary location to the final location

        This is called when a frame finishes. We always move all files for single-frame formats,
        multi-frame files (mp4, mkv, etc...) are only moved when the whole animation finishes. This
        is controlled with the include_multiframe argument.

        Sometimes Blender keeps files open and we cannot move them immediately. In this case we will
        try again after try_again_interval seconds. We cannot use the current context as it might be
        different when we try again than the context that was used during the initial call.
        That's why we pass arguments like is_movie_format, render_pass_extension_map and frame-related values.
        """
        if render_pass_extension_map is None:
            render_pass_extension_map = {}
        time = datetime.datetime.fromisoformat(self.frozen_time)
        try_again = False
        prefs = utils.get_preferences(bpy.context)
        final_output_folder_path = self.generate_output_folder_path(
            time=time,
            frame_current=frame_current,
            frame_start=frame_start,
            frame_end=frame_end,
            frame_step=frame_step,
        )
        os.makedirs(final_output_folder_path, exist_ok=True)
        # TODO: Handle the possibility that final_output_folder_path exists and is a dir
        # We move files and not the directory to handle partially rendered animations
        temporary_output_contents = os.listdir(self.temporary_output_folder_path)
        contents_moved = []
        temp_filename = self._get_rendered_temp_filename()
        frame_current_formatted = f"{frame_current:04d}"
        for entry in temporary_output_contents:
            entry_name, ext = os.path.splitext(entry)
            if (
                not include_multiframe
                and output_path_format.MultiFrameFormatExtensions.is_multi_frame_format_extension(
                    ext
                )
            ):
                continue
            # Check for composite pass
            if entry_name.startswith(temp_filename):
                render_pass = compositor_helpers.RenderPassType.COMPOSITE.value
            # Other render pass names follow the pattern: {layer}{frame}.{ext}
            elif (
                entry_name.endswith(frame_current_formatted) and prefs.automatic_render_layer_split
            ):
                render_pass = entry_name[: -len(frame_current_formatted)]
                assert render_pass != "", f"Unexpected file in temporary output folder: {entry}"
            else:
                raise RuntimeError(f"Unexpected file in temporary output folder: {entry}")

            # Let's change the filename to what the user defined
            moved_entry = (
                self.generate_output_filename(
                    is_movie_format,
                    time=time,
                    render_pass=render_pass,
                    frame_current=frame_current,
                    frame_start=frame_start,
                    frame_end=frame_end,
                    frame_step=frame_step,
                )
                + ext
            )
            render_pass_extension_map[render_pass] = ext

            # If there are files we will overwrite, move them to .old files.  We are willing to
            # overwrite .old files
            if os.path.exists(os.path.join(final_output_folder_path, moved_entry)):
                shutil.move(
                    os.path.join(final_output_folder_path, moved_entry),
                    os.path.join(final_output_folder_path, f"{moved_entry}.old"),
                )

            try:
                shutil.move(
                    os.path.join(self.temporary_output_folder_path, entry),
                    os.path.join(final_output_folder_path, moved_entry),
                )
                contents_moved.append(moved_entry)
            except PermissionError:
                # Blender might keep some files open and will not let us move them immediately
                # If this is the case we will try moving them again after try_again_interval seconds
                try_again = True

        # we will log multiple times but that's probably OK and hard to avoid here
        if len(contents_moved) > 0:
            logger.info(
                f"Render output {contents_moved} moved to "
                f"output path: {final_output_folder_path}"
            )

        if try_again:
            bpy.app.timers.register(
                lambda: self.render_finished_finalize_files(
                    is_movie_format,
                    include_multiframe,
                    frame_current=frame_current,
                    frame_start=frame_start,
                    frame_end=frame_end,
                    frame_step=frame_step,
                    render_pass_extension_map=render_pass_extension_map,
                    try_again_interval=try_again_interval,
                ),
                first_interval=try_again_interval,
            )
        elif self.execute_post_render_actions:
            # only execute post render actions once, after the last attempt
            if self.override_post_render_actions:
                data = self.post_render_actions
            else:
                data = scene_props.get_post_render_actions(bpy.context)
            for action in data.actions:
                try:
                    action.execute_action(
                        self,
                        is_movie_format,
                        render_pass_extension_map,
                        time=time,
                        frame_current=frame_current,
                        frame_start=frame_start,
                        frame_end=frame_end,
                        frame_step=frame_step,
                    )
                except Exception as e:
                    logger.exception(
                        f"Uncaught exception while executing post render action {action}, "
                        f"message: {e}"
                    )

    def set_old_render_filepath_back(self, scene: bpy.types.Scene, old_render_filepath) -> None:
        try:
            scene.render.filepath = old_render_filepath
        # This is to catch error: "AttributeError: Writing to ID classes in this context is not
        # allowed: Scene, Scene datablock, error setting RenderSettings.filepath". We could not
        # root-cause why this occurs. Relates to Issue #1793
        except AttributeError:
            logger.exception("Uncaught exception while setting old filepath back to scene")

    def render_finished(self, scene: bpy.types.Scene) -> str:
        assert self.temporary_output_folder_path is not None
        time = datetime.datetime.fromisoformat(self.frozen_time)
        final_output_folder_path = self.generate_output_folder_path(
            time=time,
            frame_current=scene.frame_current,
            frame_start=scene.frame_start,
            frame_end=scene.frame_end,
            frame_step=scene.frame_step,
        )

        # self.next_frame_to_render still contains current frame and it is updated in code below
        logger.info(
            f"Frame {self.next_frame_to_render} rendered! "
            f"output_path: {scene.render.filepath}, "
            f"context_name: {self.custom_name}"
        )

        # we need to find out if the render has been canceled or finished successfully
        # doing that is more complicated than it should be :-(
        # in case of animations we check whether the current frame rendered, we want to
        # move completed frames to final location even if the animation render gets
        # canceled
        tested_path = os.path.join(
            self.temporary_output_folder_path, self._get_rendered_temp_filename()
        )
        if self.is_animation and scene.render.is_movie_format:
            glob_result = glob.glob(tested_path + ".*")
            tested_path = glob_result[0] if len(glob_result) == 1 else "INVALID"
        else:
            tested_path += scene.render.file_extension

        if os.path.isfile(tested_path):
            # The >= seems weird but next_frame_to_render hasn't been increased by frame_step at
            # this point yet.
            self.render_finished_finalize_files(
                scene.render.is_movie_format,
                self.next_frame_to_render >= scene.frame_end,
                frame_current=scene.frame_current,
                frame_start=scene.frame_start,
                frame_end=scene.frame_end,
                frame_step=scene.frame_step,
            )

            if self.is_animation:
                print(f"Finished: {self.next_frame_to_render}/{scene.frame_end}")
                if self.next_frame_to_render < scene.frame_end:
                    self.next_frame_to_render += scene.frame_step
                    return 'FRAME_FINISHED'
        else:
            # TODO: temporary_output_folder_path may be an empty dir when we finished rendering
            # We do remove it when we next render but at some point this should be cleaned up
            # and reworked. The dir should be removed when it's no longer needed.
            logger.error(
                f"Render did not save correctly, cannot find {tested_path}. "
                f"Cannot copy the output render into {final_output_folder_path}. "
                f"Directory '{self.temporary_output_folder_path}' contains: "
                f"{', '.join(os.listdir(self.temporary_output_folder_path))}"
            )
            old_render_filepath = f"{self.old_render_filepath}"
            # TODO: This is a hack, we should create a render_cancelled method in this class and
            # react to cancellations there. We have to do this out of loop because in case of errors
            # or cancellations the bpy.context will not be in a state where we alter RenderSettings.
            bpy.app.timers.register(
                lambda: self.set_old_render_filepath_back(scene, old_render_filepath),
                first_interval=0,
            )
            return 'ERROR'

        # We remembered the old render.filepath before we changed it, let's put it back in case the
        # user had something useful in there.
        self.set_old_render_filepath_back(scene, self.old_render_filepath)
        return 'FINISHED'

    def render(
        self,
        context: bpy.types.Context,
        execution_context='INVOKE_DEFAULT',
        execute_post_render_actions: bool = True,
        time: typing.Optional[datetime.datetime] = None,
    ) -> typing.Set[str]:
        self.prepare_for_render(context, execute_post_render_actions, time=time)

        logger.info(
            f"Rendering started, "
            f"render_type: {self.render_type}, "
            f"context_name: {self.custom_name}"
            f", frame_current: {context.scene.frame_current}"
            f", frame_start: {context.scene.frame_start}"
            f", frame_end: {context.scene.frame_end}"
            f", frame_step: {context.scene.frame_step}"
        )
        prefs = utils.get_preferences(context)

        if prefs.render_operators == preferences.RenderOperator.STANDARD.value:
            bpy.ops.render.render(
                execution_context,
                animation=self.render_type == RenderType.ANIMATION.value,
                write_still=True,
            )
        elif prefs.render_operators == preferences.RenderOperator.TURBO_TOOLS.value:
            if self.is_animation:
                bpy.ops.threedi.render_animation(execution_context)
            else:
                bpy.ops.threedi.render_still(execution_context, write_still=True)
        else:
            raise ValueError(f"Unknown render_operators setting: {prefs.render_operators}")

        return set(self._get_all_output_folder_paths(context, time=time))

    def get_camera(self) -> typing.Optional[bpy.types.Object]:
        scene_dict = self.try_get_scene_settings()
        camera_uuid = scene_dict.get("camera", "")
        if not camera_uuid.startswith(serialize_utils.RSET_UUID_PREFIX):
            return None

        camera_uuid = camera_uuid[len(serialize_utils.RSET_UUID_PREFIX) :]
        return serialize_utils.try_get_datablock_from_uuid(camera_uuid, bpy.data.objects)

    def get_world(self) -> typing.Optional[bpy.types.World]:
        scene_dict = self.try_get_scene_settings()
        world_uuid = scene_dict.get("world", "")
        if not world_uuid.startswith(serialize_utils.RSET_UUID_PREFIX):
            return None

        world_uuid = world_uuid[len(serialize_utils.RSET_UUID_PREFIX) :]
        return serialize_utils.try_get_datablock_from_uuid(world_uuid, bpy.data.worlds)

    # TODO: This code for deserializing properties should be moved to polib and used for other
    # features like de/serialization of addon preferences. Do not add more renderset specifics here.
    def apply_self_props(self) -> None:
        def apply_prop_group(
            prop_group: bpy.types.PropertyGroup, prop_group_dict: typing.Dict[str, typing.Any]
        ) -> None:
            for key, value in prop_group_dict.items():
                if not hasattr(prop_group, key):
                    continue
                prop_value = getattr(prop_group, key)

                if isinstance(prop_value, bpy.types.PropertyGroup):
                    if isinstance(value, dict):
                        apply_prop_group(prop_value, value)
                elif isinstance(prop_value, bpy.types.bpy_prop_collection):
                    if isinstance(value, list):
                        prop_value.clear()
                        for inner_dict in value:
                            new_prop_group = prop_value.add()
                            apply_prop_group(new_prop_group, inner_dict)
                else:
                    if getattr(prop_group, key) != value:
                        setattr(prop_group, key, value)

        props_dict = self.synced_data_dict.get("self", {})
        if props_dict is None:
            return
        for prop_name in RendersetContext.SERIALIZABLE_PROPERTIES:
            assert hasattr(self, prop_name)
            prop_value = getattr(self, prop_name)
            if prop_name not in props_dict:
                continue

            if isinstance(prop_value, bpy.types.PropertyGroup):
                apply_prop_group(prop_value, props_dict[prop_name])
            elif isinstance(prop_value, bpy.types.bpy_prop_collection):
                prop_value.clear()
                for prop_group_dict in props_dict[prop_name]:
                    new_prop_group = prop_value.add()
                    apply_prop_group(new_prop_group, prop_group_dict)
            else:
                if getattr(self, prop_name) != props_dict[prop_name]:
                    setattr(self, prop_name, props_dict[prop_name])

    def apply(self, context: bpy.types.Context) -> None:
        """Takes settings stored in this RendersetContext and applies it to the given Blender
        context.
        """
        prefs = utils.get_preferences(context)

        self.apply_self_props()
        context.scene.camera = self.get_camera()
        if context.scene.camera is None:
            logger.warning(
                "Didn't find camera stored in renderset context, cannot set it as active!"
            )

        context.scene.world = self.get_world()
        if context.scene.world is None:
            logger.warning(
                "Didn't find world stored in renderset context, cannot set it as active!"
            )

        scene_dict = self.try_get_scene_settings()
        serialize_utils.apply_view_layers_props(
            context.scene.view_layers,
            scene_dict.get("view_layers", {}),
            scene_props.get_layer_collection_toggles_settings(context),
        )

        serialize_utils.apply_collection_props(
            context.scene.collection,
            scene_dict.get("collection", {}),
            scene_props.get_collection_toggles_settings(context),
        )

        serialize_utils.apply_objects_props(
            context.scene.objects,
            scene_dict.get("objects", {}),
            scene_props.get_object_toggles_settings(context),
        )

        # Apply stored generic properties (int, float, str, color or nested property group)
        try:
            serialize_utils.apply_property_group_props(bpy, self.stored_props_dict["bpy"])
        except Exception:
            logger.exception("Uncaught exception while applying json to scene settings!")

        if prefs.automatic_render_slots:
            render_result = bpy.data.images.get("Render Result")
            if render_result is None:
                logger.warning(
                    "Can't find Render Result in bpy.data.images, skipping render slot switching!"
                )
                return
            slot_index = self.get_index(context)
            # By default Blender has 8 render slots, users can remove them or add more.
            # We can assume there is at least one render slot but should handle all other cases.
            if slot_index >= len(render_result.render_slots):
                logger.warning(
                    f"We are rendering context with index {slot_index} but the Render Result "
                    f"image only has {len(render_result.render_slots)} render slots! "
                    f"Using the last one!"
                )
                slot_index = len(render_result.render_slots) - 1

            render_result.render_slots.active_index = slot_index

    def serialize_camera(
        self, camera_obj: bpy.types.Object, json_dict: typing.Dict[str, typing.Any]
    ) -> None:
        # TODO: Clean up uuids only in objects that are cameras
        serialize_utils.cleanup_duplicate_renderset_uuids(bpy.data.objects)
        serialize_utils.ensure_renderset_uuid(camera_obj)
        assert "camera" not in json_dict
        json_dict["camera"] = f"{serialize_utils.RSET_UUID_PREFIX}{camera_obj.renderset_uuid}"

    def serialize_world(
        self, world: bpy.types.World, json_dict: typing.Dict[str, typing.Any]
    ) -> None:
        serialize_utils.cleanup_duplicate_renderset_uuids(bpy.data.worlds)
        serialize_utils.ensure_renderset_uuid(world)
        assert "world" not in json_dict
        json_dict["world"] = f"{serialize_utils.RSET_UUID_PREFIX}{world.renderset_uuid}"

    # TODO: This code for serializing properties should be moved to polib and used for other
    # features like de/serialization of addon preferences. Do not add more renderset specifics here.
    def serialize_self_props(
        self,
        prop_group: bpy.types.bpy_struct,
        serializable_props: typing.Optional[typing.List[str]] = None,
    ) -> typing.Dict[str, typing.Any]:
        output_dict: typing.Dict[str, typing.Any] = {}
        for prop_name, prop_value in serialize_utils.get_serializable_props(prop_group):
            if serializable_props is not None and prop_name not in serializable_props:
                continue

            if isinstance(prop_value, bpy.types.PropertyGroup):
                output_dict[prop_name] = self.serialize_self_props(prop_value)
            elif isinstance(prop_value, bpy.types.bpy_prop_collection):
                prop_group_list = []
                for inner_prop_group in prop_value:
                    prop_group_list.append(self.serialize_self_props(inner_prop_group))
                output_dict[prop_name] = prop_group_list
            else:
                output_dict[prop_name] = prop_value
        return output_dict

    def init_from(self, context: bpy.types.Context, source: 'RendersetContext') -> None:
        """Store properties stored in 'source' context, values are loaded from Blender context"""
        self.custom_name = source.custom_name
        self.include_in_render_all = source.include_in_render_all
        self.override_output_folder = source.override_output_folder
        self.output_format.folder_path = source.output_format.folder_path
        self.override_output_filenames = source.override_output_filenames
        self.output_format.still_image_filename = source.output_format.still_image_filename
        self.output_format.animation_frame_filename = source.output_format.animation_frame_filename
        self.output_format.animation_movie_filename = source.output_format.animation_movie_filename
        self.override_post_render_actions = source.override_post_render_actions
        self.post_render_actions.actions.clear()
        for post_render_action in source.post_render_actions.actions:
            self.post_render_actions.actions.add().copy_properties(post_render_action)
        self.post_render_actions.active_index = source.post_render_actions.active_index
        self.render_type = source.render_type
        self._sync_according_to_json_dict(context, source.stored_props_dict)

        if get_active_renderset_context(context) == self:
            self.apply(context)

    def init_default(self, context: bpy.types.Context) -> None:
        """Store default properties (no overrides) loaded from Blender context"""
        self.custom_name = "New Context"
        self._sync_according_to_json_dict(
            context, serialize_utils.DEFAULT_SYNCED_SETTINGS.serialize_bpy_props()
        )

        if get_active_renderset_context(context) == self:
            self.apply(context)

    def sync(self, context: bpy.types.Context) -> None:
        """Updates properties stored in this context with values from Blender context"""
        self._sync_according_to_json_dict(context, self.stored_props_dict)

    def _sync_according_to_json_dict(
        self, context: bpy.types.Context, source_json_dict: typing.Dict[str, typing.Any]
    ) -> None:
        """Stores Blender context settings in this RendersetContext.

        source_json_dict: All properties stored in it will be synced. If it's not possible to load
        some of the properties from bpy.context, values stored in this dictionary will be used.
        """
        self.referenced_datablocks.clear()
        prefs = utils.get_preferences(context)
        json_dict: typing.Dict[str, typing.Any] = {}
        json_dict["self"] = self.serialize_self_props(self, self.SERIALIZABLE_PROPERTIES)
        try:
            source_bpy_json_dict = source_json_dict.get("bpy", {})
            source_scene_json_dict = source_bpy_json_dict.get("context", {}).get("scene", {})
            json_dict["bpy"] = serialize_utils.serialize_property_group_props(
                bpy, source_bpy_json_dict
            )
        except Exception:
            logger.exception("Uncaught exception while syncing scene settings!")
            return

        # In case all properties from serialize_utils.DEFAULT_SYNCED_SETTINGS were overridden to not be synced
        self.ensure_scene_hierarchy_in_json(json_dict)
        scene_dict = json_dict["bpy"]["context"]["scene"]

        if context.scene.camera is not None:
            self.serialize_camera(context.scene.camera, scene_dict)

        if context.scene.world is not None:
            self.serialize_world(context.scene.world, scene_dict)
            self.referenced_datablocks.add().datablock = context.scene.world

        view_layers_dict = serialize_utils.serialize_view_layers_props(
            context.scene.view_layers, scene_props.get_layer_collection_toggles_settings(context)
        )
        scene_dict["view_layers"] = view_layers_dict

        collection_dict = serialize_utils.serialize_collection_props(
            context.scene.collection, scene_props.get_collection_toggles_settings(context)
        )
        scene_dict["collection"] = collection_dict

        objects_visibility_dict = serialize_utils.serialize_objects_props(
            context.scene.objects, scene_props.get_object_toggles_settings(context)
        )
        scene_dict["objects"] = objects_visibility_dict

        self.synced_data_json = json.dumps(json_dict)

    def convert_from_old(
        self,
        old_rset_ctx: renderset_context_old.RendersetContextOld,
        bpy_context: bpy.types.Context,
    ) -> None:
        """Initialize this context from old context (prior renderset 2.0)"""
        # Convert relevant properties
        self.custom_name = old_rset_ctx.custom_name
        self.include_in_render_all = old_rset_ctx.include_in_render_all
        self.render_type = old_rset_ctx.render_type
        self.output_format.folder_path = old_rset_ctx.output_folder_format
        self.override_output_folder = old_rset_ctx.override_output_folder_format

        # Convert stored jsons
        json_dict: typing.Dict[str, typing.Any] = {}
        self.ensure_scene_hierarchy_in_json(json_dict)
        scene_dict = json_dict["bpy"]["context"]["scene"]

        # Stored properties have been continuously added through renderset versions. If the blend
        # file doesn't contain stored json, the default value of the property from Preferences will
        # be used.
        # We default most of the properties to some sensible default values, so that we can load
        # them here without errors. (apply() and sync() at the end of the function will populate
        # empty jsons with properties of the current scene).
        # Exceptions are camera and world which can be None. In that case we won't load them
        # and we let apply() and sync() to populate them.

        # Convert camera and world
        if old_rset_ctx.camera is not None:
            self.serialize_camera(old_rset_ctx.camera, scene_dict)
        if old_rset_ctx.world is not None:
            self.serialize_world(old_rset_ctx.world, scene_dict)

        # Scene settings - frame numeric values
        scene_dict["frame_current"] = old_rset_ctx.frame_current
        scene_dict["frame_start"] = old_rset_ctx.frame_start
        scene_dict["frame_end"] = old_rset_ctx.frame_end
        scene_dict["frame_step"] = old_rset_ctx.frame_step

        # Scene settings - property groups
        try:
            scene_dict["display_settings"] = json.loads(old_rset_ctx.display_settings_json)
            scene_dict["view_settings"] = json.loads(old_rset_ctx.view_settings_json)
            scene_dict["cycles"] = json.loads(old_rset_ctx.cycles_json)
            scene_dict["eevee"] = json.loads(old_rset_ctx.eevee_json)

            # Check if Octane and Luxcore are available since they are not in vanilla Blender
            if old_rset_ctx.octane_json != "{}":
                scene_dict["octane"] = json.loads(old_rset_ctx.octane_json)
            if old_rset_ctx.luxcore_config_json != "{}":
                scene_dict["luxcore"] = {}
                scene_dict["luxcore"]["config"] = json.loads(old_rset_ctx.luxcore_config_json)
                if len(old_rset_ctx.luxcore_config_path_json) != "{}":
                    scene_dict["luxcore"]["config"]["path"] = json.loads(
                        old_rset_ctx.luxcore_config_path_json
                    )

            scene_dict["render"] = json.loads(old_rset_ctx.render_json)
            scene_dict["render"]["ffmpeg"] = json.loads(old_rset_ctx.render_ffmpeg_json)
            scene_dict["render"]["image_settings"] = json.loads(
                old_rset_ctx.render_image_settings_json
            )
            scene_dict["render"]["image_settings"]["stereo_3d_format"] = json.loads(
                old_rset_ctx.render_image_settings_stereo_3d_format_json
            )
            scene_dict["render"]["image_settings"]["view_settings"] = json.loads(
                old_rset_ctx.render_image_settings_view_settings_json
            )
        except Exception as e:
            logger.exception("Uncaught exception while loading json with scene settings!")

        # View layers', collections' and objects' visibilities
        scene_dict["view_layers"] = json.loads(old_rset_ctx.view_layers_json)
        scene_dict["collection"] = json.loads(old_rset_ctx.root_collection_json)
        if old_rset_ctx.objects_visibility_json != "{}":
            scene_dict["objects"] = json.loads(old_rset_ctx.objects_visibility_json)

        self.synced_data_json = json.dumps(json_dict)

        # We loaded all scene settings from old renderset context. They contain much more properties
        # than what is now defined in DEFAULT_SYNCED_SETTINGS. These properties would be marked as
        # ADD overrides after migration and there would be hundreds of them since in renderset < 2.0
        # we were storing a lot of stuff. We'll clean contexts by removing ADD overrides which user
        # did't use = they contain the same value in all contexts. See remove_unused_overrides() in
        # __init__.py.
        #
        # However, it can also happen that some properties from DEFAULT_SYNCED_SETTINGS were not
        # stored in RendersetContextOld. Reasons might be:
        #     1) Properties were added in newer Blender versions and RendersetContextOld wasn't
        #         serialized in that Blender version yet.
        #     2) Some of the dictionary jsons were added to RendersetContextOld in later renderset
        #         versions. It can happen that we converted context created in one of those very old
        #         versions of renderset.
        # These properties are now marked as REMOVE overrides. We start storing them in the context
        # here:
        for override in self.overrides.remove:
            self.add_override(override, True)

    def ensure_uuid_prefix(self) -> None:
        """Ensures that all datablock uuids start with UUID prefix

        UUID prefix was introduced in renderset 2.0 with feature for storing any user-selected
        datablocks and their properties. To unify, we add the prefix also to uuids of camera, world,
        collections, view layers collections, and objects. Sadly, we were using renderset 2.0
        internally for several months before introducing UUID prefix , so now we're stuck with this
        conversion.
        """
        UUID_LENGTH = 32  # uuid is 32 hexadecimal digits

        def migrate_uuid_dict(
            data_dict: typing.Dict[str, typing.Any], nested: bool = True
        ) -> typing.Dict[str, typing.Any]:
            new_dict = {}
            for uuid, data in data_dict.items():
                if isinstance(uuid, str) and len(uuid) == UUID_LENGTH:
                    if nested and "children" in data:
                        data["children"] = migrate_uuid_dict(data["children"])
                    new_dict[f"{serialize_utils.RSET_UUID_PREFIX}{uuid}"] = data
                else:
                    new_dict[uuid] = data
            return new_dict

        json_dict = self.synced_data_dict
        scene_dict = json_dict.get("bpy", {}).get("context", {}).get("scene", None)
        if scene_dict is None:
            # Nothing from scene is stored in this context, all was marked as REMOVE override
            return

        camera_uuid = scene_dict.get("camera", None)
        if isinstance(camera_uuid, str) and len(camera_uuid) == UUID_LENGTH:
            scene_dict["camera"] = f"{serialize_utils.RSET_UUID_PREFIX}{camera_uuid}"

        world_uuid = scene_dict.get("world", None)
        if isinstance(world_uuid, str) and len(world_uuid) == UUID_LENGTH:
            scene_dict["world"] = f"{serialize_utils.RSET_UUID_PREFIX}{world_uuid}"

        # Dictionary of Collections which contains nested Collections under ["children"] key
        collection_dict = scene_dict.get("collection", None)
        if collection_dict is not None:
            if "children" in collection_dict:
                collection_dict["children"] = migrate_uuid_dict(collection_dict["children"])

        # Dictionary of ViewLayers which contain LayerCollections under ["layer_collection"][children"] key
        # LayerCollections contain nested LayerCollections under ["children"] key
        view_layers_dict = scene_dict.get("view_layers", None)
        if view_layers_dict is not None:
            new_dict = {}
            for uuid, data in view_layers_dict.items():
                if isinstance(uuid, str) and len(uuid) == UUID_LENGTH:
                    if "layer_collection" in data and "children" in data["layer_collection"]:
                        data["layer_collection"]["children"] = migrate_uuid_dict(
                            data["layer_collection"]["children"]
                        )
                    new_dict[f"{serialize_utils.RSET_UUID_PREFIX}{uuid}"] = data
                else:
                    new_dict[uuid] = data
            scene_dict["view_layers"] = new_dict

        # Dictionary of Objects
        objects_dict = scene_dict.get("objects", None)
        if objects_dict is not None:
            scene_dict["objects"] = migrate_uuid_dict(objects_dict, nested=False)

        json_dict["bpy"]["context"]["scene"] = scene_dict
        self.synced_data_json = json.dumps(json_dict)


MODULE_CLASSES.append(RendersetContext)


def is_valid_renderset_context_index(context: bpy.types.Context, index: int) -> bool:
    if index < 0:
        return False
    if index >= len(context.scene.renderset_contexts):
        return False
    return True


def get_active_renderset_context(context: bpy.types.Context) -> typing.Optional[RendersetContext]:
    index = context.scene.renderset_context_index
    if not is_valid_renderset_context_index(context, index):
        return None
    return context.scene.renderset_contexts[index]


def get_active_renderset_context_index(context: bpy.types.Context) -> typing.Optional[int]:
    index = context.scene.renderset_context_index
    if not is_valid_renderset_context_index(context, index):
        return None
    return index


def get_all_renderset_contexts(context: bpy.types.Context) -> typing.Iterable[RendersetContext]:
    return context.scene.renderset_contexts


def infer_initial_prop_container_and_path(
    prop: str, rset_context: RendersetContext
) -> typing.Tuple[str, bpy.types.bpy_struct, str]:
    """Infers the prop_path, initial_prop_container and initial_prop_path for a given property.

    E.g.:
    - bpy.context.scene.camera -> ("bpy", bpy, "context.scene.camera")
    - self.include_in_render_all -> ("self", rset_context, "self.include_in_render_all")
    """
    # This would ideally be in sync_overrides, but we need access to RendersetContext, to have
    # it as initial_prop_container
    if prop.startswith("bpy."):
        prop_path = prop.removeprefix("bpy.")
        initial_prop_container = bpy
        initial_prop_path = "bpy"
    elif prop.startswith("self."):
        prop_path = prop.removeprefix("self.")
        initial_prop_container = rset_context
        initial_prop_path = "self"
    else:
        raise ValueError(f"Invalid prop key: {prop}")

    return prop_path, initial_prop_container, initial_prop_path


def get_included_renderset_contexts_count(context: bpy.types.Context) -> int:
    return sum(rs_ctx.include_in_render_all for rs_ctx in context.scene.renderset_contexts)


def renderset_context_list_ensure_valid_index(context: bpy.types.Context) -> None:
    min_index = 0
    max_index = len(context.scene.renderset_contexts) - 1

    # This has caused errors when accessing to the context.scene after install
    if max_index == -1:
        return

    index = context.scene.renderset_context_index
    if index < min_index:
        context.scene.renderset_context_index = min_index
    elif index > max_index:
        context.scene.renderset_context_index = max_index


@polib.log_helpers_bpy.logged_operator
class RendersetContextAddPostRenderAction(
    post_render_actions.AddPostRenderActionMixin, bpy.types.Operator
):
    bl_idname = "renderset.context_add_post_render_action"

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        rset_context = get_active_renderset_context(context)
        if rset_context is None:
            self.report({"ERROR"}, "No active Renderset Context")
            return {'FINISHED'}
        output_format = (
            rset_context.output_format
            if rset_context.override_output_filenames
            else scene_props.get_output_format(bpy.context)
        )
        # We need to use a custom folder picker in versions before 4.1.0
        select_folder_operator = (
            polib.ui_bpy.OperatorButtonLoader(
                RendersetContextPostRenderActionSelectOutputFolder,
                dialog_type=post_render_actions.PostRenderActionDialogType.ADD.value,
            )
            if bpy.app.version < (4, 1, 0)
            else None
        )
        return self.invoke_dialog(
            context,
            rset_context.post_render_actions,
            rset_context,
            False,
            output_format.still_image_filename,
            output_format.animation_frame_filename,
            output_format.animation_movie_filename,
            select_folder_operator,
            RendersetContextPostRenderActionAddVariable,
        )


MODULE_CLASSES.append(RendersetContextAddPostRenderAction)


# TODO: Remove this operator when we drop support for Blender < 4.1
@polib.log_helpers_bpy.logged_operator
class RendersetContextAddPostRenderActionInternal(
    post_render_actions.AddPostRenderActionMixin, bpy.types.Operator
):
    """Internal operator to continue the add action dialog after opening a folder picker."""

    bl_idname = "renderset.context_add_post_render_action_internal"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        rset_context = get_active_renderset_context(context)
        if rset_context is None:
            self.report({"ERROR"}, "No active Renderset Context")
            return {'FINISHED'}
        output_format = (
            rset_context.output_format
            if rset_context.override_output_filenames
            else scene_props.get_output_format(bpy.context)
        )
        return self.invoke_dialog(
            context,
            rset_context.post_render_actions,
            rset_context,
            True,
            output_format.still_image_filename,
            output_format.animation_frame_filename,
            output_format.animation_movie_filename,
            polib.ui_bpy.OperatorButtonLoader(
                RendersetContextPostRenderActionSelectOutputFolder,
                dialog_type=post_render_actions.PostRenderActionDialogType.ADD.value,
            ),
            RendersetContextPostRenderActionAddVariable,
        )


MODULE_CLASSES.append(RendersetContextAddPostRenderActionInternal)


class RendersetContextEditPostRenderAction(
    post_render_actions.EditPostRenderActionMixin, bpy.types.Operator
):
    bl_idname = "renderset.context_edit_post_render_action"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        rset_context = get_active_renderset_context(context)
        if rset_context is None:
            return False
        return cls.is_applicable(rset_context.post_render_actions)

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        rset_context = get_active_renderset_context(context)
        if rset_context is None:
            self.report({"ERROR"}, "No active Renderset Context")
            return {'FINISHED'}
        # We need to use a custom folder picker in versions before 4.1.0
        select_folder_operator = (
            polib.ui_bpy.OperatorButtonLoader(
                RendersetContextPostRenderActionSelectOutputFolder,
                dialog_type=post_render_actions.PostRenderActionDialogType.EDIT.value,
            )
            if bpy.app.version < (4, 1, 0)
            else None
        )
        return self.invoke_dialog(
            context,
            rset_context.post_render_actions,
            rset_context,
            select_folder_operator,
            RendersetContextPostRenderActionAddVariable,
        )


MODULE_CLASSES.append(RendersetContextEditPostRenderAction)


# Custom folder selection operators to avoid crashing operator dialogs in Blender < 4.1
# TODO: Remove these operators when we drop support for Blender < 4.1
@polib.log_helpers_bpy.logged_operator
class RendersetContextSelectOutputFolder(
    output_path_format.SelectOutputFolderMixin, bpy.types.Operator
):
    bl_idname = "renderset.context_select_output_folder"
    bl_description = "Select output folder"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        rset_context = get_active_renderset_context(context)
        if rset_context is None:
            logger.error("No active renderset context")
        return rset_context is not None

    def execute(self, context: bpy.types.Context):
        rset_context = get_active_renderset_context(context)
        assert rset_context is not None
        self.apply_selected_folder_path(rset_context.output_format, os.path.dirname(self.filepath))
        return {'FINISHED'}


MODULE_CLASSES.append(RendersetContextSelectOutputFolder)


@polib.log_helpers_bpy.logged_operator
class RendersetContextPostRenderActionSelectOutputFolder(
    post_render_actions.PostRenderActionSelectOutputFolderMixin, bpy.types.Operator
):
    bl_idname = "renderset.context_post_render_action_select_output_folder"
    bl_description = "Select output folder"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        rset_context = get_active_renderset_context(context)
        if rset_context is None:
            logger.error("No active renderset context")
        return rset_context is not None

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        if self.dialog_type == post_render_actions.PostRenderActionDialogType.ADD.value:
            # Let's call the internal operator to not create a new action
            self.dialog_func = bpy.ops.renderset.context_add_post_render_action_internal
        elif self.dialog_type == post_render_actions.PostRenderActionDialogType.EDIT.value:
            self.dialog_func = bpy.ops.renderset.context_edit_post_render_action
        else:
            self.dialog_func = None

        return super().invoke(context, event)

    def execute(self, context: bpy.types.Context):
        rset_context = get_active_renderset_context(context)
        assert rset_context is not None
        return self.apply_selected_folder_path(
            rset_context.post_render_actions,
            os.path.dirname(self.filepath),
            dialog_func=self.dialog_func,
        )

    def cancel(self, context: bpy.types.Context):
        rset_context = get_active_renderset_context(context)
        assert rset_context is not None
        self.apply_selected_folder_path(
            rset_context.post_render_actions,
            None,
            dialog_func=self.dialog_func,
        )


MODULE_CLASSES.append(RendersetContextPostRenderActionSelectOutputFolder)
# End of custom folder selection operators


@polib.log_helpers_bpy.logged_operator
class RendersetContextDeletePostRenderAction(
    post_render_actions.DeletePostRenderActionMixin, bpy.types.Operator
):
    bl_idname = "renderset.context_delete_post_render_action"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        rset_context = get_active_renderset_context(context)
        if rset_context is None:
            return False
        return cls.is_applicable(rset_context.post_render_actions)

    def execute(self, context: bpy.types.Context):
        rset_context = get_active_renderset_context(context)
        if rset_context is None:
            self.report({"ERROR"}, "No active Renderset Context")
            return {"CANCELLED"}

        post_render_actions.post_render_action_list_delete_item(rset_context.post_render_actions)
        return {'FINISHED'}


MODULE_CLASSES.append(RendersetContextDeletePostRenderAction)


@polib.log_helpers_bpy.logged_operator
class RendersetContextMovePostRenderAction(
    post_render_actions.MovePostRenderActionMixin, bpy.types.Operator
):
    bl_idname = "renderset.context_move_post_render_action"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        rset_context = get_active_renderset_context(context)
        if rset_context is None:
            return False
        return cls.is_applicable(rset_context.post_render_actions)

    def execute(self, context: bpy.types.Context):
        rset_context = get_active_renderset_context(context)
        if rset_context is None:
            self.report({"ERROR"}, "No active Renderset Context")
            return {"CANCELLED"}

        post_render_actions.post_render_action_list_move_item(
            rset_context.post_render_actions, self.direction
        )
        return {'FINISHED'}


MODULE_CLASSES.append(RendersetContextMovePostRenderAction)


@polib.log_helpers_bpy.logged_operator
class RendersetContextClearPostRenderActions(
    post_render_actions.RemovePostRenderActionsMixin, bpy.types.Operator
):
    bl_idname = "renderset.context_clear_post_render_actions"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        rset_context = get_active_renderset_context(context)
        if rset_context is None:
            return False
        return cls.is_applicable(rset_context.post_render_actions)

    def execute(self, context: bpy.types.Context):
        rset_context = get_active_renderset_context(context)
        if rset_context is None:
            self.report({"ERROR"}, "No active Renderset Context")
            return {"CANCELLED"}

        rset_context.post_render_actions.actions.clear()
        return {'FINISHED'}


MODULE_CLASSES.append(RendersetContextClearPostRenderActions)


class RendersetContextPostRenderActionList(
    post_render_actions.PostRenderActionListMixin, bpy.types.UIList
):
    def draw_item(
        self,
        context: bpy.types.Context,
        layout: bpy.types.UILayout,
        data: post_render_actions.PostRenderActions,
        item: post_render_actions.PostRenderAction,
        icon,
        active_data,
        active_propname,
        index,
    ) -> None:
        folder_select_operator = (
            RendersetContextPostRenderActionSelectOutputFolder
            if bpy.app.version < (4, 1, 0)
            else None
        )
        self._draw_item(layout, item, index, folder_select_operator)


MODULE_CLASSES.append(RendersetContextPostRenderActionList)


def register():
    for cls in MODULE_CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(MODULE_CLASSES):
        bpy.utils.unregister_class(cls)
