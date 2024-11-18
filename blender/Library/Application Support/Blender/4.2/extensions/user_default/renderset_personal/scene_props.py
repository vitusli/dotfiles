# copyright (c) 2018- polygoniq xyz s.r.o.

import typing
import bpy
import os
import logging
from . import polib
from . import output_path_format
from . import post_render_actions

logger = logging.getLogger(f"polygoniq.{__name__}")


telemetry = polib.get_telemetry("renderset")


MODULE_CLASSES: typing.List[typing.Type] = []


def get_output_format(context: bpy.types.Context) -> output_path_format.OutputFormatProperties:
    return context.scene.renderset_output_format


def get_post_render_actions(context: bpy.types.Context) -> post_render_actions.PostRenderActions:
    return context.scene.renderset_post_render_actions


@polib.log_helpers_bpy.logged_operator
class SceneAddVariable(output_path_format.OutputFormatAddVariableMixin, bpy.types.Operator):
    bl_idname = "renderset.scene_add_variable"

    def execute(self, context: bpy.types.Context):
        output_props = get_output_format(context)
        self.add_variable(output_props)
        return {'FINISHED'}


MODULE_CLASSES.append(SceneAddVariable)


@polib.log_helpers_bpy.logged_operator
class ScenePostRenderActionAddVariable(
    output_path_format.OutputFormatAddVariableMixin, bpy.types.Operator
):
    bl_idname = "renderset.scene_post_render_action_add_variable"

    def execute(self, context: bpy.types.Context):
        scene_actions = get_post_render_actions(context)

        action = scene_actions.get_active()
        if action is None:
            self.report({'ERROR'}, "Invalid active post render action")
            return {'CANCELLED'}

        self.add_variable(action.output_format)
        return {'FINISHED'}


MODULE_CLASSES.append(ScenePostRenderActionAddVariable)


@polib.log_helpers_bpy.logged_operator
class SceneAddPostRenderAction(post_render_actions.AddPostRenderActionMixin, bpy.types.Operator):
    bl_idname = "renderset.scene_add_post_render_action"

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        scene_actions = get_post_render_actions(context)
        scene_output_format = get_output_format(context)
        # We need to use a custom folder picker in versions before 4.1.0
        select_folder_operator = (
            polib.ui_bpy.OperatorButtonLoader(
                ScenePostRenderActionSelectOutputFolder,
                dialog_type=post_render_actions.PostRenderActionDialogType.ADD.value,
            )
            if bpy.app.version < (4, 1, 0)
            else None
        )
        return self.invoke_dialog(
            context,
            scene_actions,
            output_path_format.MockRendersetContext(),
            False,
            scene_output_format.still_image_filename,
            scene_output_format.animation_frame_filename,
            scene_output_format.animation_movie_filename,
            select_folder_operator,
            ScenePostRenderActionAddVariable,
        )


MODULE_CLASSES.append(SceneAddPostRenderAction)


# TODO: Remove this operator when we drop support for Blender < 4.1
@polib.log_helpers_bpy.logged_operator
class SceneAddPostRenderActionInternal(
    post_render_actions.AddPostRenderActionMixin, bpy.types.Operator
):
    """Internal operator to continue the add action dialog after opening a folder picker."""

    bl_idname = "renderset.scene_add_post_render_action_internal"

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        scene_actions = get_post_render_actions(context)
        scene_output_format = get_output_format(context)
        return self.invoke_dialog(
            context,
            scene_actions,
            output_path_format.MockRendersetContext(),
            True,
            scene_output_format.still_image_filename,
            scene_output_format.animation_frame_filename,
            scene_output_format.animation_movie_filename,
            polib.ui_bpy.OperatorButtonLoader(
                ScenePostRenderActionSelectOutputFolder,
                dialog_type=post_render_actions.PostRenderActionDialogType.ADD.value,
            ),
            ScenePostRenderActionAddVariable,
        )


MODULE_CLASSES.append(SceneAddPostRenderActionInternal)


class SceneEditPostRenderAction(post_render_actions.EditPostRenderActionMixin, bpy.types.Operator):
    bl_idname = "renderset.scene_edit_post_render_action"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return cls.is_applicable(get_post_render_actions(context))

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        # We need to use a custom folder picker in versions before 4.1.0
        select_folder_operator = (
            polib.ui_bpy.OperatorButtonLoader(
                ScenePostRenderActionSelectOutputFolder,
                dialog_type=post_render_actions.PostRenderActionDialogType.EDIT.value,
            )
            if bpy.app.version < (4, 1, 0)
            else None
        )
        return self.invoke_dialog(
            context,
            get_post_render_actions(context),
            output_path_format.MockRendersetContext(),
            select_folder_operator,
            ScenePostRenderActionAddVariable,
        )


MODULE_CLASSES.append(SceneEditPostRenderAction)


@polib.log_helpers_bpy.logged_operator
class SceneDeletePostRenderAction(
    post_render_actions.DeletePostRenderActionMixin, bpy.types.Operator
):
    bl_idname = "renderset.scene_delete_post_render_action"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return cls.is_applicable(get_post_render_actions(context))

    def execute(self, context: bpy.types.Context):
        scene_actions = get_post_render_actions(context)
        post_render_actions.post_render_action_list_delete_item(scene_actions)
        return {'FINISHED'}


MODULE_CLASSES.append(SceneDeletePostRenderAction)


# Custom folder selection operators to avoid crashing operator dialogs in Blender < 4.1
# TODO: Remove these operators when we drop support for Blender < 4.1
@polib.log_helpers_bpy.logged_operator
class SceneSelectOutputFolder(output_path_format.SelectOutputFolderMixin, bpy.types.Operator):
    bl_idname = "renderset.scene_select_output_folder"
    bl_description = "Select output folder"

    def execute(self, context: bpy.types.Context):
        scene_output_format = get_output_format(context)
        self.apply_selected_folder_path(scene_output_format, os.path.dirname(self.filepath))
        return {'FINISHED'}


MODULE_CLASSES.append(SceneSelectOutputFolder)


@polib.log_helpers_bpy.logged_operator
class ScenePostRenderActionSelectOutputFolder(
    post_render_actions.PostRenderActionSelectOutputFolderMixin, bpy.types.Operator
):
    bl_idname = "renderset.scene_post_render_action_select_output_folder"
    bl_description = "Select output folder"

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        if self.dialog_type == post_render_actions.PostRenderActionDialogType.ADD.value:
            # Let's call the internal operator to not create a new action
            self.dialog_func = bpy.ops.renderset.scene_add_post_render_action_internal
        elif self.dialog_type == post_render_actions.PostRenderActionDialogType.EDIT.value:
            self.dialog_func = bpy.ops.renderset.scene_edit_post_render_action
        else:
            self.dialog_func = None

        return super().invoke(context, event)

    def execute(self, context: bpy.types.Context):
        return self.apply_selected_folder_path(
            get_post_render_actions(context),
            os.path.dirname(self.filepath),
            dialog_func=self.dialog_func,
        )

    def cancel(self, context: bpy.types.Context):
        self.apply_selected_folder_path(
            get_post_render_actions(context),
            None,
            dialog_func=self.dialog_func,
        )


MODULE_CLASSES.append(ScenePostRenderActionSelectOutputFolder)
# End of custom folder selection operators


@polib.log_helpers_bpy.logged_operator
class SceneMovePostRenderAction(post_render_actions.MovePostRenderActionMixin, bpy.types.Operator):
    bl_idname = "renderset.scene_move_post_render_action"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return cls.is_applicable(get_post_render_actions(context))

    def execute(self, context: bpy.types.Context):
        scene_actions = get_post_render_actions(context)
        post_render_actions.post_render_action_list_move_item(scene_actions, self.direction)
        return {'FINISHED'}


MODULE_CLASSES.append(SceneMovePostRenderAction)


@polib.log_helpers_bpy.logged_operator
class SceneClearPostRenderActions(
    post_render_actions.RemovePostRenderActionsMixin, bpy.types.Operator
):
    bl_idname = "renderset.scene_clear_post_render_actions"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return cls.is_applicable(get_post_render_actions(context))

    def execute(self, context: bpy.types.Context):
        get_post_render_actions(context).actions.clear()
        return {'FINISHED'}


MODULE_CLASSES.append(SceneClearPostRenderActions)


class ScenePostRenderActionList(post_render_actions.PostRenderActionListMixin, bpy.types.UIList):
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
            ScenePostRenderActionSelectOutputFolder if bpy.app.version < (4, 1, 0) else None
        )
        self._draw_item(layout, item, index, folder_select_operator)


MODULE_CLASSES.append(ScenePostRenderActionList)


class CollectionTogglesSettings(bpy.types.PropertyGroup):
    hide_select: bpy.props.BoolProperty(
        name="Remember Disable Selection",
        default=False,
    )
    hide_viewport: bpy.props.BoolProperty(
        name="Remember Disable in Viewports",
        default=True,
    )
    hide_render: bpy.props.BoolProperty(
        name="Remember Disable in Renders",
        default=True,
    )


MODULE_CLASSES.append(CollectionTogglesSettings)


class LayerCollectionTogglesSettings(bpy.types.PropertyGroup):
    exclude: bpy.props.BoolProperty(
        name="Remember Exclude from View Layer",
        default=True,
    )
    hide_viewport: bpy.props.BoolProperty(
        name="Remember Hide in Viewport",
        default=True,
    )
    holdout: bpy.props.BoolProperty(
        name="Remember Holdout",
        default=True,
    )
    indirect_only: bpy.props.BoolProperty(
        name="Remember Indirect Only",
        default=True,
    )


MODULE_CLASSES.append(LayerCollectionTogglesSettings)


class ObjectTogglesSettings(bpy.types.PropertyGroup):
    hide_select: bpy.props.BoolProperty(
        name="Remember Disable Selection",
        default=False,
    )
    hide_viewport: bpy.props.BoolProperty(
        name="Remember Disable in Viewports",
        default=False,
    )
    hide_render: bpy.props.BoolProperty(
        name="Remember Disable in Renders",
        default=False,
    )


MODULE_CLASSES.append(ObjectTogglesSettings)


def get_collection_toggles_settings(context: bpy.types.Context) -> CollectionTogglesSettings:
    return context.scene.renderset_collection_toggles_settings


def get_layer_collection_toggles_settings(
    context: bpy.types.Context,
) -> LayerCollectionTogglesSettings:
    return context.scene.renderset_layer_collection_toggles_settings


def get_object_toggles_settings(context: bpy.types.Context) -> ObjectTogglesSettings:
    return context.scene.renderset_object_toggles_settings


def register():
    for cls in MODULE_CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.Scene.renderset_output_format = bpy.props.PointerProperty(
        type=output_path_format.OutputFormatProperties,
    )
    bpy.types.Scene.renderset_post_render_actions = bpy.props.PointerProperty(
        type=post_render_actions.PostRenderActions
    )
    bpy.types.Scene.renderset_collection_toggles_settings = bpy.props.PointerProperty(
        type=CollectionTogglesSettings,
    )
    bpy.types.Scene.renderset_layer_collection_toggles_settings = bpy.props.PointerProperty(
        type=LayerCollectionTogglesSettings,
    )
    bpy.types.Scene.renderset_object_toggles_settings = bpy.props.PointerProperty(
        type=ObjectTogglesSettings,
    )


def unregister():
    del bpy.types.Scene.renderset_object_toggles_settings
    del bpy.types.Scene.renderset_layer_collection_toggles_settings
    del bpy.types.Scene.renderset_collection_toggles_settings
    del bpy.types.Scene.renderset_post_render_actions
    del bpy.types.Scene.renderset_output_format

    for cls in MODULE_CLASSES:
        bpy.utils.unregister_class(cls)
