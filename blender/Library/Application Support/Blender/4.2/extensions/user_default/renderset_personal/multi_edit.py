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

# Parts made using the awesome UILists tutorial by Diego Gangl. Thanks!
# See https://sinestesia.co/blog/tutorials/amazing-uilists-in-blender/

import typing
import bpy
import json
import logging
from . import polib
from . import renderset_context
from . import serialize_utils
from . import sync_overrides

logger = logging.getLogger(f"polygoniq.{__name__}")

MODULE_CLASSES: typing.List[typing.Type] = []


def multi_edit_mode_enabled(context: bpy.types.Context) -> bool:
    return context.scene.renderset_multi_edit_mode


@polib.log_helpers_bpy.logged_operator
class RendersetMultiEditSelectAll(bpy.types.Operator):
    bl_idname = "renderset.multi_edit_select_all"
    bl_label = "Multi-Edit Select All"
    bl_description = "Select all contexts in the Multi-Edit panel"
    bl_options = {'REGISTER'}

    def execute(self, context: bpy.types.Context):
        for renderset_context in context.scene.renderset_contexts:
            renderset_context.selected_for_multi_edit = True

        return {'FINISHED'}


MODULE_CLASSES.append(RendersetMultiEditSelectAll)


@polib.log_helpers_bpy.logged_operator
class RendersetMultiEditDeselectAll(bpy.types.Operator):
    bl_idname = "renderset.multi_edit_deselect_all"
    bl_label = "Multi-Edit Select None"
    bl_description = (
        "Deselect all contexts in the Multi-Edit panel, only the current active context will"
        " remain selected"
    )
    bl_options = {'REGISTER'}

    def execute(self, context: bpy.types.Context):
        for i, renderset_context in enumerate(context.scene.renderset_contexts):
            if i == context.scene.renderset_context_index:
                continue  # can't deselect active renderset context
            renderset_context.selected_for_multi_edit = False

        return {'FINISHED'}


MODULE_CLASSES.append(RendersetMultiEditDeselectAll)


class RendersetMultiEditSelectMenu(bpy.types.Menu):
    bl_idname = "UI_MT_renderset_multi_edit_select_menu"
    bl_label = "Multi-Edit Select Menu"
    bl_description = "Choose to select all/none contexts in Multi-Edit"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.operator(
            RendersetMultiEditSelectAll.bl_idname, text="All", icon='RESTRICT_SELECT_OFF'
        )
        layout.operator(RendersetMultiEditDeselectAll.bl_idname, text="None", icon='CANCEL')


MODULE_CLASSES.append(RendersetMultiEditSelectMenu)


@polib.log_helpers_bpy.logged_operator
class RendersetEnterMultiEdit(bpy.types.Operator):
    bl_idname = "renderset.enter_multi_edit"
    bl_label = "Multi-Edit Mode"
    bl_description = (
        "Enter the multi-edit mode for render contexts. This allows to change values once and have "
        "it be reflected in all contexts selected for multi-edit"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return len(context.scene.renderset_contexts) > 1 and not multi_edit_mode_enabled(context)

    def execute(self, context: bpy.types.Context):
        selected_contexts = []
        for rset_context in context.scene.renderset_contexts:
            if rset_context.selected_for_multi_edit:
                selected_contexts.append(rset_context)
        if len(selected_contexts) < 2:
            self.report({'ERROR'}, "Select at least one additional context for multi-editing!")
            return {'CANCELLED'}

        context.scene.renderset_multi_edit_mode = True
        active_context = renderset_context.get_active_renderset_context(context)
        # sync everything from blender to the context's json when we begin to multi-edit,
        # we will later diff the changes and apply them to all selected contexts
        active_context.sync(context)
        # TODO: This shouldn't be necessary but for unknown reasons we have to get the context
        #       again! Otherwise the synced_data_dict is not up to date!
        active_context = renderset_context.get_active_renderset_context(context)
        # we store the json dict here because some actions can sync the renderset context even when
        # the user does not switch to another context - e.g. adding an additional override
        context.scene.renderset_pre_multi_edit_flattened_dict = json.dumps(
            serialize_utils.flatten_dict(active_context.synced_data_dict)
        )
        return {'FINISHED'}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.row().label(text="Which contexts to simultaneously edit:")

        row = layout.row(align=True)
        row.menu(RendersetMultiEditSelectMenu.bl_idname, text="Select:", icon='MESH_PLANE')

        box = layout.box()
        checked_col, name_col = polib.ui_bpy.multi_column(box, [0.1, 0.9])
        for i, rset_context in enumerate(context.scene.renderset_contexts):
            if i == context.scene.renderset_context_index:
                checked_col.label(text="", icon='KEYTYPE_JITTER_VEC')
                name_col.label(text=rset_context.custom_name)
            else:
                checked_col.prop(rset_context, "selected_for_multi_edit", text="")
                name_col.label(text=rset_context.custom_name)

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        # ensure the currently active context is selected for multi-editing
        active_context = renderset_context.get_active_renderset_context(context)
        active_context.selected_for_multi_edit = True

        return context.window_manager.invoke_props_dialog(self)


MODULE_CLASSES.append(RendersetEnterMultiEdit)


@polib.log_helpers_bpy.logged_operator
class RendersetMultiEditDismissChange(bpy.types.Operator):
    bl_idname = "renderset.multi_edit_dismiss_change"
    bl_label = "Dismiss Hunk"
    bl_description = "Dismiss a specific change in the flattened dict patch"
    bl_options = {'REGISTER', 'UNDO'}

    hunk_key: bpy.props.StringProperty(
        name="Hunk Key",
        default="",
        description="Which hunk key should be dismissed from the flattened dict patch",
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return (
            multi_edit_mode_enabled(context)
            and len(context.scene.renderset_multi_edit_flattened_dict_patch) > 2
        )  # "{}" is size 2

    def execute(self, context: bpy.types.Context):
        try:
            flattened_dict_patch = json.loads(
                context.scene.renderset_multi_edit_flattened_dict_patch
            )
        except:
            logger.exception("Failed to load JSON of flattened dict patch!")
            flattened_dict_patch = {}

        if self.hunk_key not in flattened_dict_patch:
            logger.error(f"Key {self.hunk_key} not found in the flattened dict patch!")
            return {'CANCELLED'}

        flattened_dict_patch.pop(self.hunk_key)
        context.scene.renderset_multi_edit_flattened_dict_patch = json.dumps(flattened_dict_patch)
        return {'FINISHED'}


MODULE_CLASSES.append(RendersetMultiEditDismissChange)


@polib.log_helpers_bpy.logged_operator
class RendersetLeaveMultiEdit(bpy.types.Operator):
    bl_idname = "renderset.leave_multi_edit"
    bl_label = "Multi-Edit Mode"
    bl_description = (
        "Leave the multi-edit mode for render contexts. This looks up all changes in multi-edit "
        "mode and applies them to all contexts selected for multi-edit"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return multi_edit_mode_enabled(context)

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout

        try:
            flattened_dict_patch = json.loads(
                context.scene.renderset_multi_edit_flattened_dict_patch
            )
        except:
            logger.exception("Failed to load JSON of flattened dict patch!")
            flattened_dict_patch = {}

        if len(flattened_dict_patch) == 0:
            layout.row().label(text="No changes to stored properties detected in multi-edit mode!")
            return

        layout.row().label(text="Review changes:")
        box = layout.box()
        col = box.column()
        for hunk_key, _ in flattened_dict_patch.items():
            row = col.row()
            row.operator(
                RendersetMultiEditDismissChange.bl_idname, text="", icon='PANEL_CLOSE'
            ).hunk_key = hunk_key
            sub_row = row.row()
            sub_row.enabled = False

            prop_path, initial_prop_container, initial_prop_path = (
                renderset_context.infer_initial_prop_container_and_path(
                    hunk_key, renderset_context.get_active_renderset_context(context)
                )
            )
            user_friendly_hunk_key = sync_overrides.resolve_uuids(
                prop_path, initial_prop_container, initial_prop_path
            )
            if user_friendly_hunk_key is not None:
                sub_row.label(text=user_friendly_hunk_key)
            else:
                sub_row.label(text=hunk_key)

            prop_parent_path, prop_name = sync_overrides.split_prop_to_path_and_name(prop_path)
            parent = sync_overrides.evaluate_prop_path(
                prop_parent_path, initial_prop_container, initial_prop_path
            )
            if parent is None or prop_name is None:
                continue
            serialize_utils.draw_property(parent, prop_name, sub_row, text="")

        layout.row().label(text="Apply to contexts:")

        box = layout.box()
        col = box.column()
        for i, rset_context in enumerate(context.scene.renderset_contexts):
            if i == context.scene.renderset_context_index:
                row = col.row()
                row.label(text="", icon='KEYTYPE_JITTER_VEC')
                row.label(text=rset_context.custom_name)
            elif rset_context.selected_for_multi_edit:
                row = col.row()
                row.prop(rset_context, "selected_for_multi_edit", text="")
                row.label(text=rset_context.custom_name)

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        active_context = renderset_context.get_active_renderset_context(context)
        # we remember the state when multi-edit mode was entered
        # now we store current state
        active_context.sync(context)
        # TODO: This shouldn't be necessary but for unknown reasons we have to get the context
        #       again! Otherwise the fields are not up to date.
        active_context = renderset_context.get_active_renderset_context(context)

        try:
            pre_multi_edit_flattened_dict = json.loads(
                context.scene.renderset_pre_multi_edit_flattened_dict
            )
        except:
            logger.exception("Can't load pre multi edit flattened dict JSON!")
            pre_multi_edit_flattened_dict = {}

        flattened_post_multi_edit_dict = serialize_utils.flatten_dict(
            active_context.synced_data_dict
        )
        flattened_dict_patch = {}
        for key, value in flattened_post_multi_edit_dict.items():
            if key in pre_multi_edit_flattened_dict and pre_multi_edit_flattened_dict[key] == value:
                continue  # this key and value did not change between pre and post dicts
            flattened_dict_patch[key] = value
        for key, value in pre_multi_edit_flattened_dict.items():
            if key not in flattened_post_multi_edit_dict:
                # the key was there but is now missing, this can happen when you e.g. unassign
                # camera or world in the context. we simulate this by setting it to None
                flattened_dict_patch[key] = None

        context.scene.renderset_multi_edit_flattened_dict_patch = json.dumps(flattened_dict_patch)

        invoke_kwargs = {"width": 800}
        if bpy.app.version >= (4, 1, 0):
            invoke_kwargs["confirm_text"] = "Apply Changes"

        return context.window_manager.invoke_props_dialog(self, **invoke_kwargs)

    def execute(self, context: bpy.types.Context):
        try:
            try:
                flattened_dict_patch = json.loads(
                    context.scene.renderset_multi_edit_flattened_dict_patch
                )
            except:
                logger.exception("Failed to load JSON of flattened dict patch!")
                flattened_dict_patch = {}

            if len(flattened_dict_patch) == 0:
                logger.warning("No changes detected in multi-edit mode, nothing to apply!")
            else:
                logger.info(f"Flattened dict patch: {flattened_dict_patch}")

                active_context = renderset_context.get_active_renderset_context(context)

                for rset_context in context.scene.renderset_contexts:
                    if not rset_context.selected_for_multi_edit:
                        continue
                    if rset_context == active_context:
                        # no need to patch active context, it wouldn't do anything
                        continue

                    dict_to_patch = rset_context.synced_data_dict
                    logger.debug(f"Dict to patch: {dict_to_patch}")
                    patched_dict = serialize_utils.apply_flattened_patch(
                        dict_to_patch, flattened_dict_patch
                    )
                    logger.debug(f"Patched dict: {patched_dict}")
                    rset_context.synced_data_json = json.dumps(patched_dict)
                    logger.info(f"Applied flattened dict patch to {rset_context.custom_name}")
        finally:
            context.scene.renderset_multi_edit_mode = False
            context.scene.renderset_pre_multi_edit_flattened_dict = "{}"
            context.scene.renderset_multi_edit_flattened_dict_patch = "{}"

        return {'FINISHED'}


MODULE_CLASSES.append(RendersetLeaveMultiEdit)


def register():
    for cls in MODULE_CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.Scene.renderset_multi_edit_mode = bpy.props.BoolProperty(
        name="renderset_multi_edit_mode",
        default=False,
        description="If true renderset is in multi-edit mode",
    )
    bpy.types.Scene.renderset_pre_multi_edit_flattened_dict = bpy.props.StringProperty(
        name="renderset_pre_multi_edit_flattened_dict",
        default="{}",
        description="JSON of the flattened dict of the active context before entering multi-edit",
    )
    bpy.types.Scene.renderset_multi_edit_flattened_dict_patch = bpy.props.StringProperty(
        name="renderset_multi_edit_flattened_dict_patch",
        default="{}",
        description=(
            "Generated flattened patch from pre and post multi-edit data dictionaries. "
            "We apply this to all renderset contexts selected for multi-editing"
        ),
    )


def unregister():
    del bpy.types.Scene.renderset_multi_edit_flattened_dict_patch
    del bpy.types.Scene.renderset_pre_multi_edit_flattened_dict
    del bpy.types.Scene.renderset_multi_edit_mode

    for cls in reversed(MODULE_CLASSES):
        bpy.utils.unregister_class(cls)
