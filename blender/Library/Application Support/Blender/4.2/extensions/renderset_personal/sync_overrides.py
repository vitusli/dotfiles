# copyright (c) 2018- polygoniq xyz s.r.o.

import bpy
import typing
import logging

from . import polib

from . import serialize_utils

logger = logging.getLogger(f"polygoniq.{__name__}")


MODULE_CLASSES: typing.List[typing.Type] = []


def get_prop_full_path(context: bpy.types.Context) -> typing.Optional[str]:
    """Returns path to the property selected in `context`.

    Example: When called from menu operator if render engine selection was right-clicked, it
    returns 'bpy.data.scenes["Scene"].render.engine'.

    Returns None if 'context' isn't a context where a user selected a property.
    """
    button_pointer = getattr(context, "button_pointer", None)
    button_prop = getattr(context, "button_prop", None)

    if button_pointer is None or button_prop is None:
        # Property was not clicked. Either this function was called in wrong context where user
        # didn't click anything or the operator button was clicked in which case
        # context.button_operator is populated.
        return None

    if not hasattr(button_prop, "identifier"):
        # I'm not sure if this can ever happen but to be extra safe, we check it
        logger.error(f"button_prop '{button_prop}' doesn't have 'identifier' attribute!")
        return None

    # When right-clicking on material name in the Shader Editor/Properties users expect to store
    # material assigned to the object, not the material name.
    if isinstance(button_pointer, bpy.types.Material) and button_prop.identifier == "name":
        active_obj = context.active_object
        if active_obj is None:
            return None
        button_pointer = active_obj.material_slots[active_obj.active_material_index]
        button_prop = button_pointer.bl_rna.properties["material"]
    # The same when clicking on material in UIList in the Properties.
    if (
        isinstance(button_pointer, bpy.types.Object)
        and button_prop.identifier == "active_material_index"
    ):
        button_pointer = button_pointer.material_slots[button_pointer.active_material_index]
        button_prop = button_pointer.bl_rna.properties["material"]

    # TODO: button_pointer.__repr__() doesn't always work, for example if we want to access property
    # from an addon. It is more reliable to use copy_data_path_button() operator but that is very
    # slow and cannot be used in poll() method.
    # if bpy.ops.ui.copy_data_path_button.poll():
    #     bpy.ops.ui.copy_data_path_button("INVOKE_DEFAULT", full_path=True)
    #     prop_path = context.window_manager.clipboard
    pointer_path = button_pointer.__repr__()
    # Not really sure now, what "..." means in general in property paths and how to handle it in
    # general. I suspect that in some UI elements when properties are drawn for datablocks from
    # collections, it cannot be retrieved which datablock from collection owns this property.
    # E.g. 'Hide in Viewport' next to objects in the Outliner results in
    # bpy.data.scenes['Scene']...hide_viewport.
    if "..." in pointer_path:
        return None

    pointer_path = pointer_path.replace("\"", "'")

    prop_full_path = None
    if hasattr(button_pointer, button_prop.identifier):
        prop_full_path = f"{pointer_path}.{button_prop.identifier}"
    elif button_prop.identifier in button_pointer:
        prop_full_path = f"{pointer_path}['{button_prop.identifier}']"

    if prop_full_path is None:
        return None

    # Convert path to any scene to the path of current scene starting with bpy.context
    # e.g. 'bpy.data.scenes["Scene"].render.engine' -> 'bpy.context.scene.render.engine'
    # Currently, renderset works per scene, so we want to store/un-store properties on the current
    # scene.
    if prop_full_path.startswith("bpy.data.scenes[") and "]." in prop_full_path:
        prefix_index = prop_full_path.index("].")
        return f"bpy.context.scene.{prop_full_path[prefix_index + len('].'):]}"
    else:
        return prop_full_path


def split_prop_to_path_and_name(prop_path: str) -> typing.Tuple[str, str]:
    """Splits property path on the last dot

    E.g. bpy.context.scene.render.engine -> bpy.context.scene.render, engine
    """
    if "." not in prop_path and "[" not in prop_path:
        return "", prop_path
    last_dot_index = prop_path.rfind(".")
    last_bracket_index = prop_path.rfind("[")

    # e.g. "bpy.context.scene.render.engine"
    if last_dot_index > last_bracket_index:
        prop_path, prop_name = prop_path.rsplit(".", 1)
        return prop_path, prop_name

    # e.g. "bpy.data.object['Cube']['custom_prop']
    prop_path, prop_name = prop_path[:last_bracket_index], prop_path[last_bracket_index:]
    # Strip brackets and quotation marks
    assert len(prop_name) > 4
    assert prop_name[0] == "[" and prop_name[-1] == "]"
    assert prop_name[1] in ("'", "\"") and prop_name[-2] in ("'", "\"")
    prop_name = prop_name[2:-2]
    return prop_path, prop_name


def get_property_name_from_data_path(data_path: str) -> str:
    """Returns name of the property from the given 'data_path' string.

    If property doesn't exist it returns empty string. If property uses 'default_value', then
    we try to get the name from it. Otherwise we check 'rna_type.properties' for the name.

    If property exists but we can't figure out the name, we return fallback - capitalized last part
    of the property path.
    """
    data, prop = split_prop_to_path_and_name(data_path)
    if data is None or prop is None:
        return ""

    fallback_name = prop.capitalize().replace("_", " ")
    if prop == "default_value":
        return getattr(data, "name", fallback_name)

    return data.rna_type.properties[prop].name if hasattr(data, prop) else fallback_name


def _convert_indexing_name(
    prop_container: bpy.types.bpy_struct, prop_name: str, writable_context: bool
) -> typing.Tuple[typing.Optional[bpy.types.bpy_struct], typing.Optional[str]]:
    """Converts indexing from property path to representation with UUIDs and property object

    Returns property object and its UUID representation in the property path.

    E.g.
        obj.material_slots, "0" -> obj.material_slots[0], "RSET_INDEX-0"
        bpy.data.objects, "Cube" -> bpy.data.objects["Cube"], "RSET_UUID-cd5b99c3ac9e4cd69ccb7e99f1f78daa"
        obj, "custom_prop" -> obj["custom_prop"], "custom_prop"
    """
    # Numeric indexing like bpy.data.objects[0] or ...node.inputs[1].default_value
    if prop_name.isdecimal():
        assert isinstance(prop_container, bpy.types.bpy_prop_collection)
        prop_index = int(prop_name)
        return prop_container[prop_index], f"{serialize_utils.RSET_INDEX_PREFIX}{prop_name}"

    # Indexing with string like bpy.data.objects["Cube"] or obj["my_prop"]
    # Remove quotation marks, e.g. "'Scene.001'" -> "Scene.001"
    assert len(prop_name) > 2
    assert prop_name[0] in ("'", "\"") and prop_name[0] == prop_name[-1]
    prop_name = prop_name[1:-1]
    if prop_name not in prop_container:
        logger.warning(
            f"Couldn't convert property path! '{prop_container}' doesn't contain "
            f"indexed '{prop_name}' prop!"
        )
        return None, None

    if not isinstance(prop_container, bpy.types.bpy_prop_collection):
        # Brackets here mean a custom property of the datablock,
        # e.g. # bpy.data.objects["Cube"]["my_prop"]
        return prop_container[prop_name], prop_name
    else:
        # Convert datablock name to UUID if possible
        if not isinstance(prop_container[prop_name], bpy.types.ID):
            logger.debug(f"Property '{prop_name}' is not and ID datablock, cannot get it's uuid!")
            return None, None
        indexed_prop_uuid = serialize_utils.try_get_uuid_from_datablock(
            prop_container[prop_name], writable_context=writable_context
        )

        if indexed_prop_uuid is None:
            logger.warning(f"Failed to ensure UUID for {prop_container[prop_name]}!")
            return None, None

        return prop_container[prop_name], f"{serialize_utils.RSET_UUID_PREFIX}{indexed_prop_uuid}"


def _convert_prop_path(
    prop_path: str,
    writable_context: bool,
    initial_prop_container: typing.Optional[bpy.types.bpy_struct] = None,
    initial_prop_path: typing.Optional[str] = None,
) -> typing.Tuple[
    typing.Optional[str], typing.Optional[str], typing.Optional[bpy.types.bpy_struct]
]:
    """Converts property path to native Blender Python path, path with UUIDs and property object

    Given property path may or may not already contain some UUIDs.
    """
    MAX_DELIMITER_INDEX = 1_000_000

    if initial_prop_container is None or initial_prop_path is None:
        assert initial_prop_container is None and initial_prop_path is None
        initial_prop_container = bpy
        initial_prop_path = "bpy"
        assert prop_path.startswith("bpy.")
        prop_path = prop_path.removeprefix("bpy.")

    prop_container = initial_prop_container
    # Path like it would appear in Blender, it doesn't contain any UUID
    native_prop_path = initial_prop_path
    # Path where all datablocks are represented by UUIDs
    uuid_prop_path = initial_prop_path

    # Examples are for the input "bpy.data.scenes['Scene.001'].render"
    while len(prop_path) > 0:
        dot_index = prop_path.index(".") if "." in prop_path else MAX_DELIMITER_INDEX
        bracket_index = prop_path.index("[") if "[" in prop_path else MAX_DELIMITER_INDEX

        # Index into property array, e.g. prop_path = "['Scene.001'].render"
        if prop_path[0] == "[":
            assert "]" in prop_path
            prop_path = prop_path[1:]  # Remove "["
            prop_name, prop_path = prop_path.split("]", 1)
            prop_path = prop_path.lstrip(".")

            prop_container, uuid_prop_name = _convert_indexing_name(
                prop_container, prop_name, writable_context
            )
            if uuid_prop_name is None or prop_container is None:
                return None, None, None
            uuid_prop_path += f".{uuid_prop_name}"
            native_prop_path += f"[{prop_name}]"
            continue

        # The last property of the path, e.g. prop_path = "render"
        if dot_index == bracket_index == MAX_DELIMITER_INDEX:
            next_prop, prop_path = prop_path, ""
        # Next property is split by the dot, e.g. prop_path = "data.scenes['Scene.001'].render"
        elif dot_index < bracket_index:
            next_prop, prop_path = prop_path.split(".", 1)
        # Next property is split by the bracket, e.g. prop_path = "scenes['Scene.001'].render"
        else:
            next_prop, prop_path = prop_path.split("[", 1)
            prop_path = "[" + prop_path

        if next_prop.startswith(serialize_utils.RSET_UUID_PREFIX):
            next_prop_uuid = next_prop[len(serialize_utils.RSET_UUID_PREFIX) :]
            collection = None
            if isinstance(prop_container, bpy.types.bpy_prop_collection):
                collection = prop_container
            prop_with_uuid = serialize_utils.try_get_datablock_from_uuid(next_prop_uuid, collection)
            if prop_with_uuid is None:
                logger.warning(
                    f"Couldn't get parent of '{prop_path}' property! "
                    f"Couldn't find datablock with UUID '{next_prop_uuid}'!"
                )
                return None, None, None
            prop_container = prop_with_uuid
            uuid_prop_path += f".{next_prop}"
            if hasattr(prop_with_uuid, "name_full"):
                native_prop_path += f"[{prop_with_uuid.name_full}]"
            else:
                assert hasattr(prop_with_uuid, "name")
                native_prop_path += f"[{prop_with_uuid.name}]"
        elif next_prop.startswith(serialize_utils.RSET_INDEX_PREFIX):
            next_prop_index = next_prop[len(serialize_utils.RSET_INDEX_PREFIX) :]
            prop_container = serialize_utils.get_indexed_prop(next_prop_index, prop_container)
            if prop_container is None:
                logger.warning(
                    f"Couldn't get parent of '{prop_path}' property! "
                    f"Couldn't find property with index '{next_prop_index}'!"
                )
                return None, None, None
            uuid_prop_path += f".{next_prop}"
            native_prop_path += f"[{next_prop_index}]"
        else:
            if hasattr(prop_container, next_prop):
                native_prop_path += f".{next_prop}"
                prop_container = getattr(prop_container, next_prop)
            elif (
                serialize_utils.can_store_custom_property(prop_container)
                and next_prop in prop_container
            ):
                native_prop_path += f"[{next_prop}]"
                prop_container = prop_container[next_prop]
            else:
                logger.warning(
                    f"Couldn't get parent of '{prop_path}' property! "
                    f"'{prop_container}' doesn't contain '{next_prop}' attribute!"
                )
                return None, None, None

            uuid_prop_path += f".{next_prop}"

    return native_prop_path, uuid_prop_path, prop_container


def resolve_uuids(
    prop_path: str,
    initial_prop_container: typing.Optional[bpy.types.bpy_struct] = None,
    initial_prop_path: typing.Optional[str] = None,
) -> typing.Optional[str]:
    """Resolves UUIDs and prefixed indices in the property path to native Blender Python path

    Example: "bpy.data.objects.RSET_UUID-cd5b99c3ac9e4cd69ccb7e99f1f78daa.location.RSET_INDEX-0" -> "bpy.data.objects['Cube'].location[0]"
    """
    return _convert_prop_path(
        prop_path,
        writable_context=False,
        initial_prop_container=initial_prop_container,
        initial_prop_path=initial_prop_path,
    )[0]


def expand_uuids(
    prop_path: str,
    writable_context: bool = True,
    initial_prop_container: typing.Optional[bpy.types.bpy_struct] = None,
    initial_prop_path: typing.Optional[str] = None,
) -> typing.Optional[str]:
    """Replaces datablock names in the property path with their UUIDs and add prefix indices

    Example: "bpy.data.objects['Cube'].location[0]" -> "bpy.data.objects.RSET_UUID-cd5b99c3ac9e4cd69ccb7e99f1f78daa.location.RSET_INDEX-0"

    writable_context: Use False if this method is called from a context where writing into
    properties is forbidden e.g. right-click menu. If False, this will replace datablock name with
    UUID only if the datablock already has up-to-date UUID, otherwise a mock-up constant uuid is
    used. If True, this will assign UUIDs to datablocks that don't have them yet.
    """
    return _convert_prop_path(
        prop_path,
        writable_context=writable_context,
        initial_prop_container=initial_prop_container,
        initial_prop_path=initial_prop_path,
    )[1]


def evaluate_prop_path(
    prop_path: str,
    initial_prop_container: typing.Optional[bpy.types.bpy_struct] = None,
    initial_prop_path: typing.Optional[str] = None,
) -> typing.Optional[bpy.types.bpy_struct]:
    """Returns Blender object defined by 'prop_path'

    E.g. "bpy.context.scene.render" -> render property from bpy.context.scene
    or "bpy.data.scenes['Scene.001'].render" -> render property from bpy.data.scenes['Scene.001']
    (result of both of these examples is an object of type RenderSettings, but they are different
    instances if bpy.context.scene is not Scene.001)
    """
    return _convert_prop_path(
        prop_path,
        writable_context=False,
        initial_prop_container=initial_prop_container,
        initial_prop_path=initial_prop_path,
    )[2]


def can_store_property(prop_path: str, verbose: bool = False) -> bool:
    # If prop_path is path in the scene, we expect context-based scene property path
    # e.g. 'bpy.context.scene.render.engine' which is returned by get_prop_full_path().
    assert not prop_path.startswith("bpy.data.scenes[")

    if not prop_path.startswith("bpy."):
        if verbose:
            logger.error("Can't store properties outside of bpy!")
        return False

    # Don't allow storing renderset properties
    if "renderset" in prop_path or "render_set" in prop_path:
        if verbose:
            logger.error("Can't store renderset's internal properties!")
        return False

    # Check if property can be obtained
    prop_parent_path, prop_name = split_prop_to_path_and_name(prop_path)
    prop_parent = evaluate_prop_path(prop_parent_path)
    if prop_parent is None or prop_name is None:
        if verbose:
            logger.error("Can't obtain value of parent property!")
        return False

    # Storing names doesn't make sense, user would most likely expect to store the whole datablock,
    # not just its name.
    if prop_name in {"name", "name_full"}:
        if verbose:
            logger.error("Can't store name properties!")
        return False

    prop_value = serialize_utils.get_serializable_property_value(
        prop_parent, prop_name, writable_context=False
    )
    if prop_value is None:
        if verbose:
            logger.error("Can't obtain value of the property or it has unsupported type!")
        return False

    # Don't allow storing visibility restriction toggles of single datablock, we store/not store
    # them for all based on toggles in the preferences
    BPY_TYPE_TO_RESTRICTION_TOGGLES = {
        bpy.types.Object: ("hide_render", "hide_select", "hide_viewport"),
        bpy.types.Collection: ("hide_render", "hide_select", "hide_viewport"),
        bpy.types.LayerCollection: ("exclude", "holdout", "indirect_only", "hide_viewport"),
    }
    for bpy_type, restriction_toggles in BPY_TYPE_TO_RESTRICTION_TOGGLES.items():
        if isinstance(prop_parent, bpy_type) and prop_name in restriction_toggles:
            if verbose:
                logger.error(
                    f"Can't store visibility restrictions of single {bpy_type}! "
                    "You can set in Preferences if they're always stored or not!"
                )
            return False

    return True


def draw_renderset_context_menu_items(self, context: bpy.types.Context) -> None:
    """Given property right-click 'context', it adds renderset operator to the menu"""
    prop_full_path = get_prop_full_path(context)
    if prop_full_path is None:
        return

    if not can_store_property(prop_full_path):
        return

    if len(context.scene.renderset_contexts) == 0:
        return

    # Any renderset context will do, we just need to check if the property is stored in them
    rset_context = context.scene.renderset_contexts[0]
    expanded_prop_path = expand_uuids(prop_full_path, writable_context=False)
    if expanded_prop_path is None:
        return
    is_stored = expanded_prop_path in serialize_utils.flatten_dict(rset_context.stored_props_dict)

    self.layout.separator()
    self.layout.operator(
        WM_OT_renderset_toggle_property_override.bl_idname,
        text="Remove Property" if is_stored else "Store Property",
        icon_value=polib.ui_bpy.icon_manager.get_icon_id("logo_renderset"),
    ).mode = (
        'REMOVE' if is_stored else 'ADD'
    )


class WM_OT_renderset_toggle_property_override(bpy.types.Operator):
    """This operator is added to the right-click context menu of properties in the UI. It currently
    works only on properties starting with bpy.context.scene. We can easily extend it to other
    int, float, str and array properties (like color). The problem is with properties of datablocks
    from collections (like object visibility) as we would need to assign UUIDs to those datablocks
    (easy) and have a custom functions that would iterate over specific collections and set there
    the stored properties (difficult). E.g. Iterate over material slots on all objects and set there
    stored material.
    """

    bl_idname = "renderset.toggle_property_override"
    bl_label = "Add/Remove property from Stored Properties in renderset context"

    mode: bpy.props.EnumProperty(
        name="Mode of Additional Properties",
        description="Defines if selected property should be added or removed from stored properties",
        items=(
            ('ADD', "Add", "Add property to stored"),
            ('REMOVE', "Remove", "Remove property from stored"),
        ),
    )

    @classmethod
    def description(
        cls, context: bpy.types.Context, properties: bpy.types.OperatorProperties
    ) -> str:
        current_mode = getattr(properties, "mode", None)
        if current_mode == 'ADD':
            return "Property will be remembered per renderset context"
        elif current_mode == 'REMOVE':
            return "Property will not be stored per renderset context"
        else:
            raise ValueError(f"Unknown mode: {properties.mode}!")

    def execute(self, context: bpy.types.Context):
        prop_full_path = get_prop_full_path(context)
        assert prop_full_path is not None

        if not can_store_property(prop_full_path, verbose=True):
            self.report({'ERROR'}, "Cannot store selected property!")
            return {'CANCELLED'}

        for rset_context in context.scene.renderset_contexts:
            if self.mode == 'ADD':
                rset_context.add_override(prop_full_path, action_store=True)
            elif self.mode == 'REMOVE':
                rset_context.add_override(prop_full_path, action_store=False)
            else:
                raise ValueError(f"Unknown mode: {self.mode}!")

        return {'FINISHED'}


MODULE_CLASSES.append(WM_OT_renderset_toggle_property_override)


def register():
    for cls in MODULE_CLASSES:
        bpy.utils.register_class(cls)

    # Taken from example in: https://docs.blender.org/api/3.3/bpy.types.Menu.html#extending-the-button-context-menu
    # Most online sources use WM_MT_button_context() menu but that was deprecated in Blender 3.3:
    # https://wiki.blender.org/wiki/Reference/Release_Notes/3.3/Python_API
    bpy.types.UI_MT_button_context_menu.append(draw_renderset_context_menu_items)


def unregister():
    bpy.types.UI_MT_button_context_menu.remove(draw_renderset_context_menu_items)
    for cls in reversed(MODULE_CLASSES):
        bpy.utils.unregister_class(cls)
