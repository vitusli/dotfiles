#!/usr/bin/python3
# copyright (c) 2018- polygoniq xyz s.r.o.

# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
import aud
import os
import enum
import shutil
import datetime
import json
import typing
import logging
from . import polib
from . import serialize_utils
from . import output_path_format
from . import compositor_helpers

if typing.TYPE_CHECKING:
    # TYPE_CHECKING is always False at runtime, so this block will never be executed
    # This import is used only for type hinting
    from . import renderset_context
logger = logging.getLogger(f"polygoniq.{__name__}")


MODULE_CLASSES: typing.List[typing.Type] = []


class PostRenderActionType(enum.Enum):
    COPY_OUTPUT_FILE = "copy_output_file"
    POST_ON_SLACK = "post_on_slack"
    DELETE_OUTPUT_FOLDER = "delete_output_folder"
    PLAY_SOUND = "play_sound"
    MOVE_OUTPUT_FILE = "move_output_file"


class PostRenderActionDialogType(enum.Enum):
    NONE = "none"
    ADD = "add"
    EDIT = "edit"


DEFAULT_WEBHOOK_URL = (
    "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
)
DEFAULT_SOUND_FILEPATH = os.path.join(os.path.dirname(__file__), "sounds", "bell.ogg")


class PostRenderAction(bpy.types.PropertyGroup):
    """Encapsulates an action that can be executed after RendersetContext finishes
    rendering. The action can copy files around, notify on slack or possibly more in
    the future.
    """

    bl_idname = "renderset.PostRenderAction"
    bl_label = "PostRenderAction"

    enabled: bpy.props.BoolProperty(
        name="Enabled",
        default=True,
        description="If set to false this post render action will be entirely skipped.",
    )

    action_type: bpy.props.EnumProperty(
        name="Action Type",
        items=[
            (
                PostRenderActionType.COPY_OUTPUT_FILE.value,
                "Copy output file",
                "Copies matching files we output as part of the render",
                'DUPLICATE',
                1,
            ),
            (
                PostRenderActionType.MOVE_OUTPUT_FILE.value,
                "Move output file",
                "Moves (renames) matching files we output as part of the render",
                'ANIM_DATA',
                5,
            ),
            (
                PostRenderActionType.POST_ON_SLACK.value,
                "Post on slack",
                "Post a message on slack when a render finishes",
                'INFO',
                2,
            ),
            (
                PostRenderActionType.DELETE_OUTPUT_FOLDER.value,
                "Delete output folder",
                "Delete the output folder with all output from a render",
                'TRASH',
                3,
            ),
            (
                PostRenderActionType.PLAY_SOUND.value,
                "Play sound",
                "Plays a sound when render context finishes rendering",
                'SOUND',
                4,
            ),
        ],
    )

    custom_layer_name: bpy.props.StringProperty(
        name="Custom Layer Name",
        default="Custom Layer",
        description=f"Custom layer name of the copied/moved output. Available when Render Layer Type "
        f"is set to '{compositor_helpers.RenderPassType.CUSTOM.value}'",
    )

    render_layer_type: bpy.props.EnumProperty(
        name="Render Layer Type",
        description=f"Select render layer of output to be copied/moved. "
        f"Use '{compositor_helpers.RenderPassType.CUSTOM.value}' to input custom layer name",
        items=[
            (compositor_helpers.RenderPassType.CUSTOM.value, "Custom", "Custom"),
            None,
            (compositor_helpers.RenderPassType.COMPOSITE.value, "Composite", "Composite"),
            (compositor_helpers.RenderPassType.DEPTH.value, "Depth", "Depth"),
            (compositor_helpers.RenderPassType.NORMAL.value, "Normal", "Normal"),
            (compositor_helpers.RenderPassType.UV.value, "UV", "UV"),
            (compositor_helpers.RenderPassType.VECTOR.value, "Vector", "Vector"),
            (compositor_helpers.RenderPassType.SHADOW.value, "Shadow", "Shadow"),
            (compositor_helpers.RenderPassType.AO.value, "AO", "AO"),
            (compositor_helpers.RenderPassType.MIST.value, "Mist", "Mist"),
            (compositor_helpers.RenderPassType.EMIT.value, "Emit", "Emit"),
            (compositor_helpers.RenderPassType.ENV.value, "Env", "Env"),
            (compositor_helpers.RenderPassType.NOISY_IMAGE.value, "Noisy Image", "Noisy Image"),
            (compositor_helpers.RenderPassType.FREESTYLE.value, "Freestyle", "Freestyle"),
            None,
            (compositor_helpers.RenderPassType.INDEX_OB.value, "IndexOB", "IndexOB"),
            (compositor_helpers.RenderPassType.INDEX_MA.value, "IndexMA", "IndexMA"),
            None,
            (compositor_helpers.RenderPassType.DIFF_DIR.value, "DiffDir", "DiffDir"),
            (compositor_helpers.RenderPassType.DIFF_IND.value, "DiffInd", "DiffInd"),
            (compositor_helpers.RenderPassType.DIFF_COL.value, "DiffCol", "DiffCol"),
            None,
            (compositor_helpers.RenderPassType.GLOSS_DIR.value, "GlossDir", "GlossDir"),
            (compositor_helpers.RenderPassType.GLOSS_IND.value, "GlossInd", "GlossInd"),
            (compositor_helpers.RenderPassType.GLOSS_COL.value, "GlossCol", "GlossCol"),
            None,
            (compositor_helpers.RenderPassType.TRANS_DIR.value, "TransDir", "TransDir"),
            (compositor_helpers.RenderPassType.TRANS_IND.value, "TransInd", "TransInd"),
            (compositor_helpers.RenderPassType.TRANS_COL.value, "TransCol", "TransCol"),
            None,
            (
                compositor_helpers.RenderPassType.SUBSURFACE_DIR.value,
                "SubsurfaceDir",
                "SubsurfaceDir",
            ),
            (
                compositor_helpers.RenderPassType.SUBSURFACE_IND.value,
                "SubsurfaceInd",
                "SubsurfaceInd",
            ),
            (
                compositor_helpers.RenderPassType.SUBSURFACE_COL.value,
                "SubsurfaceCol",
                "SubsurfaceCol",
            ),
            None,
            (compositor_helpers.RenderPassType.VOLUME_DIR.value, "VolumeDir", "VolumeDir"),
            (compositor_helpers.RenderPassType.VOLUME_IND.value, "VolumeInd", "VolumeInd"),
            None,
        ],
        default=compositor_helpers.RenderPassType.COMPOSITE.value,
    )

    output_format: bpy.props.PointerProperty(type=output_path_format.OutputFormatProperties)

    def ensure_not_empty_webhook_url(self, context: bpy.types.Context) -> None:
        if self.webhook_url == "":
            self.webhook_url = DEFAULT_WEBHOOK_URL

    # Specific to post_on_slack
    webhook_url: bpy.props.StringProperty(
        name="Webhook URL", default=DEFAULT_WEBHOOK_URL, update=ensure_not_empty_webhook_url
    )

    def ensure_not_empty_sound_filepath(self, context: bpy.types.Context) -> None:
        if self.sound_filepath == "":
            self.sound_filepath = DEFAULT_SOUND_FILEPATH

    # Specific to play sound
    sound_filepath: bpy.props.StringProperty(
        name="Sound Filepath",
        default=DEFAULT_SOUND_FILEPATH,
        update=ensure_not_empty_sound_filepath,
    )

    def execute_action(
        self,
        renderset_context: "renderset_context.RendersetContext",
        is_movie_format: bool,
        render_pass_extension_map: typing.Dict[str, str],
        time: typing.Optional[datetime.datetime] = None,
        frame_current: typing.Optional[int] = None,
        frame_start: typing.Optional[int] = None,
        frame_end: typing.Optional[int] = None,
        frame_step: typing.Optional[int] = None,
    ) -> None:
        """Execute post render action after renderset context finalizes the rendered files

        Sometimes Blender keeps files open and they cannot be finalized immediately. In this case, the action
        will be executed after some time and the current context might be different.
        That's why we pass arguments like is_movie_format, render_pass_extension_map and frame-related values.
        """

        if not self.enabled:
            return

        final_output_folder_path = renderset_context.generate_output_folder_path(
            time=time,
            frame_current=frame_current,
            frame_start=frame_start,
            frame_end=frame_end,
            frame_step=frame_step,
        )
        if self.action_type in {
            PostRenderActionType.COPY_OUTPUT_FILE.value,
            PostRenderActionType.MOVE_OUTPUT_FILE.value,
        }:
            render_pass_type = compositor_helpers.RenderPassType.get_render_pass_type(
                self.render_layer_type
            )
            if render_pass_type is None:
                logger.error(
                    f"PostRenderAction of type {self.action_type} failed, "
                    f"invalid render pass type '{self.render_layer_type}'."
                )
                return
            is_composite_pass = render_pass_type == compositor_helpers.RenderPassType.COMPOSITE
            render_pass = (
                self.custom_layer_name
                if render_pass_type == compositor_helpers.RenderPassType.CUSTOM
                else render_pass_type.value
            )

            if time is None:
                time = datetime.datetime.now()

            searched_filename = renderset_context.generate_output_filename(
                is_movie_format,
                time=time,
                render_pass=render_pass,
                frame_current=frame_current,
                frame_start=frame_start,
                frame_end=frame_end,
                frame_step=frame_step,
            )

            output_filename = output_path_format.select_output_filename(
                renderset_context.is_animation,
                is_movie_format,
                render_pass == compositor_helpers.RenderPassType.COMPOSITE.value,
                self.output_format.still_image_filename,
                self.output_format.animation_frame_filename,
                self.output_format.animation_movie_filename,
            )

            target_filename = output_path_format.generate_filename(
                output_filename,
                renderset_context,
                time=time,
                render_pass=render_pass,
                frame_current=frame_current,
                frame_start=frame_start,
                frame_end=frame_end,
                frame_step=frame_step,
            )
            target_folder = output_path_format.generate_folder_path(
                self.output_format.folder_path,
                renderset_context,
                time=time,
                frame_current=frame_current,
                frame_start=frame_start,
                frame_end=frame_end,
                frame_step=frame_step,
            )
            ext = render_pass_extension_map.get(render_pass, None)
            if ext is None:
                logger.warning(
                    f"PostRenderAction of type {self.action_type} cannot be executed, "
                    f"output of render pass '{render_pass}' was not found."
                )
                return

            target_file = os.path.join(target_folder, f"{target_filename}{ext}")
            source_file = os.path.join(final_output_folder_path, f"{searched_filename}{ext}")
            if not os.path.isfile(source_file):
                if not (is_movie_format and frame_end != frame_current and is_composite_pass):
                    # This is not an error if we render a composite animation movie
                    # and we have not reached the last frame yet
                    logger.error(
                        f"PostRenderAction of type {self.action_type} failed, "
                        f"source file '{source_file}' not found."
                    )
                return

            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            if self.action_type == PostRenderActionType.COPY_OUTPUT_FILE.value:
                shutil.copyfile(source_file, target_file)
                transition = f"'{source_file}' copied to '{target_file}'"
            else:
                shutil.move(source_file, target_file)
                transition = f"'{source_file}' moved to '{target_file}'"

            logger.info(f"PostRenderAction of type {self.action_type} executed, {transition}")

        elif self.action_type == PostRenderActionType.POST_ON_SLACK.value:
            import http.client

            connection = http.client.HTTPSConnection("hooks.slack.com", 443, timeout=5)
            headers = {'Content-Type': 'application/json'}
            filepath = bpy.data.filepath if bpy.data.filepath != "" else "unknown.blend"
            message = f"renderset[{filepath}]: "
            message += f"Finished rendering '{renderset_context.custom_name}'. "
            message += f"Results can be found at: "
            message += os.path.realpath(final_output_folder_path)
            body_json = {"text": message}
            connection.request(
                'POST', self.webhook_url, body=json.dumps(body_json), headers=headers
            )
            connection.close()
            logger.info(
                f"PostRenderAction of type {self.action_type} executed, "
                f"webhook_url: {self.webhook_url}"
            )

        elif self.action_type == PostRenderActionType.DELETE_OUTPUT_FOLDER.value:
            if os.path.isdir(final_output_folder_path):
                # we ignore errors because the last thing we want is to bring blender down because we
                # failed to delete the output folder
                shutil.rmtree(final_output_folder_path, ignore_errors=True)

            logger.info(f"PostRenderAction of type {self.action_type} executed")

        elif self.action_type == PostRenderActionType.PLAY_SOUND.value:
            if not os.path.isfile(self.sound_filepath):
                logger.error(
                    f"Can't play post render sound. Sound file "
                    f"{self.sound_filepath} not found! Skipping."
                )

            else:
                # We store all these variables in the class instance to avoid their reference
                # count dropping to zero before we are finished playing the sound.
                self.device = aud.Device()
                self.sound = aud.Sound(self.sound_filepath)
                self.sound_cache = aud.Sound.cache(self.sound)
                self.sound_handle = self.device.play(self.sound_cache)
                # this is the number of loops remaining, since we are already playing the sound
                # the number of loops remaining must be 0 to avoid looping at all
                self.sound_handle.loop_count = 0

            logger.info(
                f"PostRenderAction of type {self.action_type} executed, "
                f"sound_filepath: {self.sound_filepath}"
            )

    def copy_properties(self, other: "PostRenderAction") -> None:
        for property in other.bl_rna.properties:
            if not property.is_readonly:
                pref_value = getattr(other, property.identifier)
                setattr(self, property.identifier, pref_value)

    def draw_edit_dialog(
        self,
        layout: bpy.types.UILayout,
        select_folder_operator: typing.Optional[
            polib.ui_bpy.OperatorButtonLoader[output_path_format.SelectOutputFolderMixin]
        ],
        add_variable_operator: output_path_format.OutputFormatAddVariableMixin,
        renderset_context: typing.Union[
            "renderset_context.RendersetContext", output_path_format.MockRendersetContext
        ],
    ) -> None:
        col = layout.column()
        col.prop(self, "action_type", text="Action Type")
        if self.action_type in {
            PostRenderActionType.COPY_OUTPUT_FILE.value,
            PostRenderActionType.MOVE_OUTPUT_FILE.value,
        }:
            if self.render_layer_type == compositor_helpers.RenderPassType.CUSTOM.value:
                # This value makes the dropdown arrow aligned with the dropdown above
                split = col.split(factor=0.975, align=True)
                split.prop(self, "custom_layer_name", text="Render Layer Type")
                split.prop(self, "render_layer_type", text="")
            else:
                col.prop(self, "render_layer_type", text="Render Layer Type")
            col.separator()
            output_path_format.draw_output_folder_ui(
                self.output_format,
                col,
                select_folder_operator,
                add_variable_operator,
                renderset_context,
            )
            col.separator()
            box = col.box()
            output_path_format.draw_output_filename_ui(
                self.output_format,
                box,
                output_path_format.OutputFormatProperty.STILL_IMAGE_FILENAME,
                add_variable_operator,
                renderset_context,
                "Still Image Filename",
            )
            output_path_format.draw_output_filename_ui(
                self.output_format,
                box,
                output_path_format.OutputFormatProperty.ANIMATION_FRAME_FILENAME,
                add_variable_operator,
                renderset_context,
                "Animation Frame Filename",
            )
            output_path_format.draw_output_filename_ui(
                self.output_format,
                box,
                output_path_format.OutputFormatProperty.ANIMATION_MOVIE_FILENAME,
                add_variable_operator,
                renderset_context,
                "Animation Movie Filename",
            )

        elif self.action_type == PostRenderActionType.POST_ON_SLACK.value:
            col.prop(self, "webhook_url", text="Webhook URL")
        elif self.action_type == PostRenderActionType.DELETE_OUTPUT_FOLDER.value:
            # this action type has no extra props
            pass
        elif self.action_type == PostRenderActionType.PLAY_SOUND.value:
            col.prop(self, "sound_filepath", text="Sound Filepath")


MODULE_CLASSES.append(PostRenderAction)


class PostRenderActions(bpy.types.PropertyGroup):
    actions: bpy.props.CollectionProperty(name="Post Render Actions", type=PostRenderAction)

    active_index: bpy.props.IntProperty(name="Post Render Action Index", default=0)

    def get_active(self) -> typing.Optional[PostRenderAction]:
        if self.active_index < 0 or self.active_index >= len(self.actions):
            return None
        return self.actions[self.active_index]


MODULE_CLASSES.append(PostRenderActions)


class PostRenderActionListMoveDirection(enum.Enum):
    UP = "UP"
    DOWN = "DOWN"


def post_render_action_list_ensure_valid_index(action_props: PostRenderActions) -> None:
    min_index = 0
    max_index = len(action_props.actions) - 1

    index = action_props.active_index
    if index < min_index:
        action_props.active_index = min_index
    elif index > max_index:
        action_props.active_index = max_index


def post_render_action_list_add_item(action_props: PostRenderActions) -> PostRenderAction:
    action = action_props.actions.add()
    post_render_action_list_ensure_valid_index(action_props)
    return action


def post_render_action_list_delete_item(action_props: PostRenderActions) -> None:
    """Delete the currently selected post render action or the one at the given index."""
    index = action_props.active_index
    action_list = action_props.actions
    if index < 0 or index >= len(action_props.actions):
        logger.error("Trying to delete a post render action with invalid index.")
        return
    if index > 0:
        action_props.active_index -= 1
        action_list.remove(index)
        # current index remains unchanged, we switch to context
        # just above the one we are deleting
    else:
        # switch to action just below the one we are deleting
        action_props.active_index += 1
        # remove the first context
        action_list.remove(index)
        # this means all the indices have to be adjusted by -1
        action_props.active_index -= 1

    post_render_action_list_ensure_valid_index(action_props)


def post_render_action_list_move_item(action_props: PostRenderActions, direction_str: str) -> None:
    direction = PostRenderActionListMoveDirection(direction_str)
    the_list = action_props.actions
    index = action_props.active_index
    neighbor = index + (-1 if direction == PostRenderActionListMoveDirection.UP else 1)
    the_list.move(neighbor, index)
    action_props.active_index = neighbor
    post_render_action_list_ensure_valid_index(action_props)


class PostRenderActionSelectOutputFolderMixin(output_path_format.SelectOutputFolderMixin):
    index: bpy.props.IntProperty(min=-1, default=-1)
    dialog_type: bpy.props.EnumProperty(
        items=[
            (PostRenderActionDialogType.NONE.value, "None", "Do not run any dialog after closing"),
            (
                PostRenderActionDialogType.ADD.value,
                "Add",
                "Run Add Post Render Action dialog after closing",
            ),
            (
                PostRenderActionDialogType.EDIT.value,
                "Edit",
                "Run Edit Post Render Action dialog after closing",
            ),
        ],
        default=PostRenderActionDialogType.NONE.value,
    )

    def apply_selected_folder_path(
        self,
        actions: PostRenderActions,
        folder_path: typing.Optional[str],
        dialog_func: typing.Optional[typing.Callable] = None,
    ):
        self.signal_folder_select_not_running()
        if self.index >= 0:
            if self.index < 0 or self.index >= len(actions.actions):
                self.report({'ERROR'}, "Invalid post render action index")
                return {'FINISHED'}
            action = actions.actions[self.index]
        else:
            action = actions.get_active()
            if action is None:
                self.report({'ERROR'}, "No active post render action")
                return {'FINISHED'}
        if folder_path is not None:
            action.output_format.folder_path = folder_path
        if dialog_func is not None:
            return dialog_func('INVOKE_DEFAULT')
        return {'FINISHED'}


class AddPostRenderActionMixin:
    bl_label = "Add Post Render Action"
    bl_description = "Add a new Post Render Action"
    bl_options = {'REGISTER', 'UNDO'}

    WINDOW_WIDTH = 500

    def invoke_dialog(
        self,
        context: bpy.types.Context,
        action_props: PostRenderActions,
        rset_context: typing.Union[
            "renderset_context.RendersetContext", output_path_format.MockRendersetContext
        ],
        continue_dialog: bool,
        still_image_filename: str,
        animation_frame_filename: str,
        animation_movie_filename: str,
        select_folder_operator: typing.Optional[
            polib.ui_bpy.OperatorButtonLoader[output_path_format.SelectOutputFolderMixin]
        ],
        add_variable_operator: output_path_format.OutputFormatAddVariableMixin,
    ):
        self.action_props = action_props
        self.rset_context = rset_context
        self.select_folder_operator = select_folder_operator
        self.add_variable_operator = add_variable_operator
        self.previous_index = action_props.active_index
        if continue_dialog:
            # We need to get the already active action if we are continuing after a folder selection
            self.action = action_props.get_active()
        else:
            self.action = post_render_action_list_add_item(action_props)
            self.action.output_format.folder_path = os.path.expanduser(
                "~/renderset_one_folder/{context_name}"
            )
            self.action.output_format.still_image_filename = still_image_filename
            self.action.output_format.animation_frame_filename = animation_frame_filename
            self.action.output_format.animation_movie_filename = animation_movie_filename
            action_props.active_index = len(action_props.actions) - 1
        return context.window_manager.invoke_props_dialog(
            self, width=AddPostRenderActionMixin.WINDOW_WIDTH
        )

    def draw(self, context: bpy.types.Context) -> None:
        assert self.action_props is not None and self.rset_context is not None
        self.action.draw_edit_dialog(
            self.layout, self.select_folder_operator, self.add_variable_operator, self.rset_context
        )

    def execute(self, context: bpy.types.Context):
        return {'FINISHED'}

    def cancel(self, context: bpy.types.Context):
        # If the add dialog is canceled by a folder select dialog, we should not revert the changes
        if output_path_format.FOLDER_SELECT_RUNNING:
            return
        assert self.action_props is not None
        post_render_action_list_delete_item(self.action_props)
        self.action_props.active_index = self.previous_index


class EditPostRenderActionMixin:
    bl_label = "Edit Post Render Action"
    bl_description = "Edit the selected Post Render Action"
    bl_options = {'REGISTER', 'UNDO'}

    WINDOW_WIDTH = 500

    @classmethod
    def is_applicable(cls, action_props: PostRenderActions) -> bool:
        return action_props.get_active() is not None

    def invoke_dialog(
        self,
        context: bpy.types.Context,
        action_props: PostRenderActions,
        rset_context: typing.Union[
            "renderset_context.RendersetContext", output_path_format.MockRendersetContext
        ],
        select_folder_operator: typing.Optional[
            polib.ui_bpy.OperatorButtonLoader[output_path_format.SelectOutputFolderMixin]
        ],
        add_variable_operator: output_path_format.OutputFormatAddVariableMixin,
    ):
        self.action_props = action_props
        self.rset_context = rset_context
        self.action = action_props.get_active()
        self.select_folder_operator = select_folder_operator
        self.add_variable_operator = add_variable_operator
        self.prev_values_dict = dict(serialize_utils.get_serializable_props(self.action))
        return context.window_manager.invoke_props_dialog(
            self, width=EditPostRenderActionMixin.WINDOW_WIDTH
        )

    def draw(self, context: bpy.types.Context) -> None:
        assert (
            self.action_props is not None
            and self.rset_context is not None
            and self.action is not None
        )
        self.action.draw_edit_dialog(
            self.layout, self.select_folder_operator, self.add_variable_operator, self.rset_context
        )

    def execute(self, context: bpy.types.Context):
        return {'FINISHED'}

    def cancel(self, context: bpy.types.Context):
        # If the edit dialog is canceled by a folder select dialog, we should not revert the changes
        if output_path_format.FOLDER_SELECT_RUNNING:
            return
        assert self.action is not None
        for prop_name, value in self.prev_values_dict.items():
            setattr(self.action, prop_name, value)


class DeletePostRenderActionMixin:
    bl_label = "Delete Post Render Action"
    bl_description = "Delete the selected Post Render Action from the list"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def is_applicable(cls, action_props: PostRenderActions) -> bool:
        return len(action_props.actions) > 0


class MovePostRenderActionMixin:
    bl_label = "Move Post Render Action"
    bl_description = "Move selected Post Render Action in the list"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.EnumProperty(
        name="direction",
        items=(
            (
                PostRenderActionListMoveDirection.UP.value,
                "Up",
                "Move currently active Post Render Action one step higher in the list",
            ),
            (
                PostRenderActionListMoveDirection.DOWN.value,
                "Down",
                "Move currently active Post Render Action one step lower in the list",
            ),
        ),
    )

    @classmethod
    def is_applicable(cls, action_props: PostRenderActions) -> bool:
        return len(action_props.actions) > 1


class RemovePostRenderActionsMixin:
    bl_label = "Remove All Post Render Actions"
    bl_description = "Remove all Post Render Actions from the list"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def is_applicable(cls, action_props: PostRenderActions) -> bool:
        return len(action_props.actions) > 0

    def invoke(self, context: bpy.types.Context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context: bpy.types.Context):
        self.layout.label(text="Are you sure you want to remove all post render actions?")


# TODO: Unify Post Render Actions UILists once we drop support for Blender < 4.1
class PostRenderActionListMixin:
    """Mixin for UI lists for managing post render actions.

    We need to implement a UIList for each class that can own Post Render Actions
    because of using custom file pickers in Blender < 4.1.
    """

    def _draw_item(
        self,
        layout: bpy.types.UILayout,
        item: PostRenderAction,
        index: int,
        select_folder_operator: typing.Optional[
            typing.Type[PostRenderActionSelectOutputFolderMixin]
        ],
    ) -> None:
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "enabled", text="")
            row.prop(item, "action_type", text="")
            if item.action_type in {
                PostRenderActionType.COPY_OUTPUT_FILE.value,
                PostRenderActionType.MOVE_OUTPUT_FILE.value,
            }:
                # 0.3 of the row layout for the prefix and 0.7 for the path display
                split = row.split(factor=0.3, align=True)
                if item.render_layer_type == compositor_helpers.RenderPassType.CUSTOM.value:
                    # In case of custom prefix we split once more and show additional property
                    # for the 'custom_layer_name'
                    custom_prefix_split = split.split(factor=0.9, align=True)
                    custom_prefix_split.prop(item, "custom_layer_name", text="")
                    custom_prefix_split.prop(item, "render_layer_type", text="")
                else:
                    split.prop(item, "render_layer_type", text="")

                path_row = split.row(align=True)
                valid, _ = output_path_format.is_output_path_valid(item.output_format.folder_path)
                if not valid:
                    path_row.alert = True
                    path_row.label(icon='ERROR')
                path_row.prop(item.output_format, "folder_path", text="", emboss=False)
                if select_folder_operator is not None:
                    path_row.operator(
                        select_folder_operator.bl_idname, text="", icon='FILE_FOLDER'
                    ).index = index

            elif item.action_type == PostRenderActionType.POST_ON_SLACK.value:
                row.prop(item, "webhook_url", text="", emboss=False)
            elif item.action_type == PostRenderActionType.DELETE_OUTPUT_FOLDER.value:
                # this action type has no extra props
                pass
            elif item.action_type == PostRenderActionType.PLAY_SOUND.value:
                row.prop(item, "sound_filepath", text="", emboss=False)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="")


def draw_post_render_actions_ui(
    layout: bpy.types.UILayout,
    ui_list: typing.Type[
        PostRenderActionListMixin
    ],  # We should use Type wherever we do not pass an instance
    action_props: PostRenderActions,
    add_action_operator: AddPostRenderActionMixin,
    edit_action_operator: EditPostRenderActionMixin,
    delete_action_operator: DeletePostRenderActionMixin,
    move_action_operator: MovePostRenderActionMixin,
    remove_actions_operator: RemovePostRenderActionsMixin,
) -> None:
    row = layout.row()
    col = row.column(align=True)
    col.operator(edit_action_operator.bl_idname, icon='GREASEPENCIL', text="")
    col.separator()
    col.operator(add_action_operator.bl_idname, text="", icon='ADD')
    col.operator(delete_action_operator.bl_idname, text="", icon='REMOVE')
    col.separator()
    col.operator(move_action_operator.bl_idname, text="", icon='TRIA_UP').direction = (
        PostRenderActionListMoveDirection.UP.value
    )
    col.operator(move_action_operator.bl_idname, text="", icon='TRIA_DOWN').direction = (
        PostRenderActionListMoveDirection.DOWN.value
    )
    col.separator()
    col.operator(remove_actions_operator.bl_idname, text="", icon='TRASH')

    col = row.column(align=True)
    col.template_list(
        ui_list.__name__,
        PostRenderAction.__name__,
        action_props,
        "actions",
        action_props,
        "active_index",
        rows=6,
    )


def register():
    for cls in MODULE_CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(MODULE_CLASSES):
        bpy.utils.unregister_class(cls)
