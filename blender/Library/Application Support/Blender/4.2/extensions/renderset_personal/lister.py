# copyright (c) 2018- polygoniq xyz s.r.o.

import bpy
import typing
import math
import logging
from . import polib
from . import renderset_context
from . import serialize_utils
from . import sync_overrides
from . import utils
from . import preferences

logger = logging.getLogger(f"polygoniq.{__name__}")


MODULE_CLASSES: typing.List[typing.Type] = []


def _get_context_displayed_props_flat_dict(
    rset_context: renderset_context.RendersetContext, lister_props: preferences.ListerProperties
) -> typing.Dict[str, str]:
    to_root_prefix = ""
    if lister_props.show == 'PRIMITIVE_PROPS':
        dictionary = rset_context.stored_props_dict
    elif lister_props.show == 'CONTEXT_PROPS':
        dictionary = rset_context.synced_data_dict.get("self", {})
        to_root_prefix = "self."
    elif lister_props.show == 'VIEW_LAYER_VISIBILITY':
        dictionary = (
            rset_context.synced_data_dict.get("bpy", {})
            .get("context", {})
            .get("scene", {})
            .get("view_layers", {})
        )
        to_root_prefix = "bpy.context.scene.view_layers."
    elif lister_props.show == 'COLLECTION_VISIBILITY':
        # We get the "children", as the root "collection" can't get its visibility changed
        dictionary = (
            rset_context.synced_data_dict.get("bpy", {})
            .get("context", {})
            .get("scene", {})
            .get("collection", {})
            .get("children", {})
        )
        to_root_prefix = "bpy.context.scene.collection.children."
    elif lister_props.show == 'OBJECT_VISIBILITY':
        dictionary = (
            rset_context.synced_data_dict.get("bpy", {})
            .get("context", {})
            .get("scene", {})
            .get("objects", {})
        )
        to_root_prefix = "bpy.context.scene.objects."
    elif lister_props.show == 'DATA_PROPERTIES':
        dictionary = rset_context.synced_data_dict.get("bpy", {}).get("data", {})
        to_root_prefix = "bpy.data."
    elif lister_props.show == 'OUTPUT_PATH':
        # TODO: What to do with this
        dictionary = {"Expected Output Path": rset_context.generate_output_folder_path()}
        to_root_prefix = None
    elif lister_props.show == 'ALL':
        dictionary = rset_context.synced_data_dict
    else:
        raise ValueError(f"Unknown show value: {lister_props.show}")

    return serialize_utils.flatten_dict({f"{to_root_prefix}{k}": v for k, v in dictionary.items()})


def _get_total_pages(
    flat_dictionary: typing.Dict[str, str], lister_props: preferences.ListerProperties
) -> int:
    return math.ceil(len(flat_dictionary) / lister_props.props_per_page)


def _get_lister_displayed_contexts_unique_props_flat_dict(
    context: bpy.types.Context, lister_props: preferences.ListerProperties
) -> typing.Dict[str, str]:
    def match_prop(prop: str, search: str) -> bool:
        kws = set(search.lower().split(","))
        prop = prop.lower().replace("_", " ")
        return any(kw.strip() in prop for kw in kws)

    unique_props_flat_dict = {}
    for rset_context in renderset_context.get_all_renderset_contexts(context):
        unique_props_flat_dict.update(
            _get_context_displayed_props_flat_dict(rset_context, lister_props)
        )

    if lister_props.search != "":
        unique_props_flat_dict = [
            prop for prop in unique_props_flat_dict if match_prop(prop, lister_props.search)
        ]

    return unique_props_flat_dict


def _get_human_readable_property_name(
    prop: str,
    lister_props: preferences.ListerProperties,
    rset_context: renderset_context.RendersetContext,
) -> str:
    # Super specific use case, but we want to show the output paths in lister, as it is quite useful
    # to see the output paths of all contexts at once.
    if lister_props.show == 'OUTPUT_PATH':
        return "Output Path"

    user_friendly_prop = sync_overrides.resolve_uuids(
        *renderset_context.infer_initial_prop_container_and_path(prop, rset_context)
    )

    if user_friendly_prop is not None:
        # In case there are brackets, we want to display them, so it is possible to see
        # to what datablock and possibly index of some property the property points to.
        # e. g. bpy.data.collections['Name'].children -> collections['Name'] Children
        start = user_friendly_prop.find("[")
        end = user_friendly_prop.find("]")
        if start != -1 and end != -1:
            return f"{user_friendly_prop[start:end + 1]} {sync_overrides.get_property_name_from_data_path(prop)}"

        return sync_overrides.get_property_name_from_data_path(prop)

    return prop


def _paginate_props(
    props: typing.List[str],
    lister_props: preferences.ListerProperties,
) -> typing.List[str]:
    start = lister_props.page_index * lister_props.props_per_page
    end = start + lister_props.props_per_page
    return props[start:end]


@polib.log_helpers_bpy.logged_operator
class RendersetListerClearSearch(bpy.types.Operator):
    bl_idname = "renderset.lister_clear_search"
    bl_label = "Clear Search"
    bl_description = "Clears the search field in the Render Context Lister"
    bl_options = {'REGISTER'}

    def execute(self, context: bpy.types.Context):
        lister_props = utils.get_preferences(context).lister
        lister_props.search = ""
        return {'FINISHED'}


MODULE_CLASSES.append(RendersetListerClearSearch)


@polib.log_helpers_bpy.logged_operator
class RendersetListerSwitchPage(bpy.types.Operator):
    bl_idname = "renderset.lister_switch_page"
    bl_label = "Switch Page"
    bl_description = "Switches the page in the Render Context Lister"
    bl_options = {'REGISTER'}

    direction: bpy.props.EnumProperty(
        name="Direction",
        items=(
            ('PREVIOUS', "Previous", "Switch to the previous page"),
            ('NEXT', "Next", "Switch to the next page"),
        ),
        default='NEXT',
    )

    def execute(self, context: bpy.types.Context):
        lister_props = utils.get_preferences(context).lister
        renderset_contexts = renderset_context.get_all_renderset_contexts(context)
        assert len(renderset_contexts) > 0

        total_pages = _get_total_pages(
            _get_lister_displayed_contexts_unique_props_flat_dict(context, lister_props),
            lister_props,
        )

        if self.direction == 'PREVIOUS':
            lister_props.page_index -= 1
        elif self.direction == 'NEXT':
            lister_props.page_index += 1

        lister_props.page_index = max(0, min(lister_props.page_index, total_pages - 1))

        return {'FINISHED'}


MODULE_CLASSES.append(RendersetListerSwitchPage)


@polib.log_helpers_bpy.logged_operator
class RendersetLister(bpy.types.Operator):
    bl_idname = "renderset.overview"
    bl_label = "Render Context Lister"
    bl_description = "Shows overview of all important properties in renderset contexts"
    bl_options = {'REGISTER'}

    def draw_header(
        self,
        header_box: bpy.types.UILayout,
        lister_props: preferences.ListerProperties,
        total_pages: int,
    ) -> None:
        header_row = header_box.row()
        row = header_row.row()
        row.alignment = 'LEFT'
        row.operator(RendersetListerSwitchPage.bl_idname, icon='TRIA_LEFT', text="").direction = (
            'PREVIOUS'
        )
        row.label(text=f"Page {lister_props.page_index + 1} / {max(total_pages, 1)}")
        row.operator(RendersetListerSwitchPage.bl_idname, icon='TRIA_RIGHT', text="").direction = (
            'NEXT'
        )
        row.prop(lister_props, "props_per_page")

        sub_row = row.row()
        sub_row.scale_x = 1.3
        # placeholder argument is available from 4.1.0 above
        if bpy.app.version < (4, 1, 0):
            sub_row.prop(lister_props, "search", text="", icon='VIEWZOOM')
        else:
            sub_row.prop(
                lister_props,
                "search",
                text="",
                placeholder=f"Search in {lister_props.show.replace('_', ' ').lower()}",
                icon='VIEWZOOM',
            )

        if lister_props.search != "":
            row.operator(RendersetListerClearSearch.bl_idname, text="", icon='X', emboss=False)

        col = header_row.row(align=True)
        col.alignment = 'RIGHT'
        col.prop(lister_props, "show", text="")

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        renderset_contexts = renderset_context.get_all_renderset_contexts(context)
        if len(renderset_contexts) == 0:
            layout.label(text="No renderset contexts found", icon='ERROR')
            return

        lister_props = utils.get_preferences(context).lister
        # TODO: This could be optimized to not get the properties in each draw call, but do it once
        # in invoke, and then only search through the props, when search changes. But it seems to
        # work completely fine performance wise even with the current approach.
        unique_props = _get_lister_displayed_contexts_unique_props_flat_dict(context, lister_props)
        paginated_props = _paginate_props(list(unique_props), lister_props)

        self.draw_header(layout.box(), lister_props, _get_total_pages(unique_props, lister_props))

        box = layout.box()

        if len(unique_props) == 0:
            box.separator()
            row = box.row()
            row.alignment = 'CENTER'
            if lister_props.search == "":
                row.label(text="No such properties are currently stored.", icon='INFO')
            else:
                row.label(text="No such property found.", icon='GHOST_ENABLED')
            box.separator()
            return

        col_flow = box.column_flow()
        row = col_flow.row()
        row.label(text="Context Name")
        for prop in paginated_props:
            row.label(
                text=_get_human_readable_property_name(prop, lister_props, renderset_contexts[0])
            )

        col_flow.row().separator()

        # Iterate first through contexts, so we can fill this row by row
        for i, r_context in enumerate(renderset_contexts):
            row = col_flow.row()
            row.label(text=f"{i}: {r_context.custom_name}")
            this_context_props = _get_context_displayed_props_flat_dict(r_context, lister_props)
            for prop in paginated_props:
                value = this_context_props.get(prop, "-")
                if isinstance(value, str) and value.startswith(serialize_utils.RSET_UUID_PREFIX):
                    datablock = serialize_utils.try_get_datablock_from_uuid(
                        value[len(serialize_utils.RSET_UUID_PREFIX) :], None
                    )
                    if datablock is not None:
                        value = datablock.name

                row.label(text=str(value))

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        # before drawing overview with all values we need to sync them from blender to active renderset context
        active_renderset_context = renderset_context.get_active_renderset_context(context)
        if active_renderset_context is not None:
            active_renderset_context.sync(context)

        return context.window_manager.invoke_props_dialog(
            self, width=utils.get_preferences(context).lister.width
        )

    def execute(self, context: bpy.types.Context):
        return {'FINISHED'}


MODULE_CLASSES.append(RendersetLister)


def register():
    for cls in MODULE_CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(MODULE_CLASSES):
        bpy.utils.unregister_class(cls)
