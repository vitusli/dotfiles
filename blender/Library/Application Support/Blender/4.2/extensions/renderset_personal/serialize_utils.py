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
import mathutils
import idprop
import uuid
import collections
import typing
import logging
from . import scene_props

logger = logging.getLogger(f"polygoniq.{__name__}")


# We use this prefix with datablock uuids, so that we can distinguish between uuid and names when
# deserializing json. E.g. bpy.data.objects['Cube'] -> bpy.data.objects.RSET_UUID-b8ddcdc6f95b421191dbbf78ad8935cc
RSET_UUID_PREFIX = "RSET_UUID-"
# We use this prefix for numerical indexing, so that we can distinguish between numerical indices
# and names that consist of numbers. E.g. bpy.data.objects['0'] -> bpy.data.objects.RSET_INDEX-0
RSET_INDEX_PREFIX = "RSET_INDEX-"


# Has to be wrapped in a function because collections in bpy.data are not available at the time of
# module import. It results in: "AttributeError: '_RestrictData' object has no attribute 'actions'"
def get_datablock_types_to_collections() -> (
    typing.Dict[typing.Type[bpy.types.ID], bpy.types.bpy_prop_collection]
):
    # All types that inherit from bpy.types.ID. They're the same in all supported Blenders 3.6 - 4.2
    # If new Blender introduces a new type and we want to support storing it or its properties in
    # renderset context, we have to add it here and handle that it's not present in older Blenders.
    return {
        bpy.types.Action: bpy.data.actions,
        bpy.types.Armature: bpy.data.armatures,
        bpy.types.Brush: bpy.data.brushes,
        bpy.types.CacheFile: bpy.data.cache_files,
        bpy.types.Camera: bpy.data.cameras,
        bpy.types.Collection: bpy.data.collections,
        bpy.types.Curve: bpy.data.curves,
        bpy.types.Curves: bpy.data.hair_curves,
        bpy.types.FreestyleLineStyle: bpy.data.linestyles,
        bpy.types.GreasePencil: bpy.data.grease_pencils,
        bpy.types.Image: bpy.data.images,
        bpy.types.Key: bpy.data.shape_keys,
        bpy.types.Lattice: bpy.data.lattices,
        bpy.types.Library: bpy.data.libraries,
        bpy.types.Light: bpy.data.lights,
        bpy.types.LightProbe: bpy.data.lightprobes,
        bpy.types.Mask: bpy.data.masks,
        bpy.types.Material: bpy.data.materials,
        bpy.types.Mesh: bpy.data.meshes,
        bpy.types.MetaBall: bpy.data.metaballs,
        bpy.types.MovieClip: bpy.data.movieclips,
        bpy.types.NodeTree: bpy.data.node_groups,
        bpy.types.Object: bpy.data.objects,
        bpy.types.PaintCurve: bpy.data.paint_curves,
        bpy.types.Palette: bpy.data.palettes,
        bpy.types.ParticleSettings: bpy.data.particles,
        bpy.types.PointCloud: bpy.data.pointclouds,
        bpy.types.Scene: bpy.data.scenes,
        bpy.types.Screen: bpy.data.screens,
        bpy.types.Sound: bpy.data.sounds,
        bpy.types.Speaker: bpy.data.speakers,
        bpy.types.Text: bpy.data.texts,
        bpy.types.Texture: bpy.data.textures,
        bpy.types.VectorFont: bpy.data.fonts,
        bpy.types.Volume: bpy.data.volumes,
        bpy.types.WindowManager: bpy.data.window_managers,
        bpy.types.WorkSpace: bpy.data.workspaces,
        bpy.types.World: bpy.data.worlds,
    }


class SyncedPropsDefinition:
    def __init__(
        self,
        properties: typing.List[str],
        ignore_listed: bool = False,
        optional: bool = False,
        **kwargs,
    ):
        """Hierarchical definition of properties that are synced in contexts.

        properties: List of properties that are going to be stored/ignored
        ignore_listed: If True, all properties from dir() except listed in "properties" will be stored.
                       If False, only properties listed in "properties" will be stored.
        optional: Property group doesn't need to exist
        **kwargs: Nested definitions of properties, we use **kwargs for them as a trick to have
                  nicer syntax in DEFAULT_SYNCED_SETTINGS definition
        """
        self.properties = properties
        self.ignore_listed = ignore_listed
        self.optional = optional

        if any(k in ["properties", "ignore_listed", "optional"] for k in kwargs):
            raise ValueError("Reserved keyword used in SyncedPropsDefinition definition!")
        if not all(isinstance(arg, SyncedPropsDefinition) for arg in kwargs.values()):
            raise ValueError(
                "All arguments in SyncedPropsDefinition have to be of type SyncedPropsDefinition!"
            )
        self.child_definitions: typing.Dict[str, 'SyncedPropsDefinition'] = kwargs

    def serialize_bpy_props(self) -> typing.Dict[str, typing.Any]:
        assert "bpy" in self.child_definitions
        return {"bpy": self.child_definitions["bpy"]._serialize_props(bpy)}

    def _serialize_props(
        self, property_group: bpy.types.bpy_struct
    ) -> typing.Dict[str, typing.Any]:
        # Validate that properties defined here in code actually exist and can be accessed
        # in Blender. We do this step mostly to check that names of properties defined in the code
        # didn't change in new Blender or that there isn't a typo.
        for prop_name in self.properties:
            assert hasattr(
                property_group, prop_name
            ), f"Property {prop_name} not found in {property_group}"
        for prop_group_name, prop_group_def in list(self.child_definitions.items()):
            if not prop_group_def.optional:
                assert hasattr(
                    property_group, prop_group_name
                ), f"Property {prop_group_name} not found in {property_group}"

        result: typing.Dict[str, typing.Any] = {}
        assert property_group is not None
        if self.ignore_listed:
            for prop_name, prop_value in get_serializable_props(property_group):
                if prop_name in self.properties:
                    continue

                if any(
                    isinstance(prop_value, t)
                    for t in [str, int, bool, float, mathutils.Color, bpy.types.bpy_prop_array]
                ):
                    result[prop_name] = getattr(property_group, prop_name)
        else:
            for prop_name in self.properties:
                result[prop_name] = getattr(property_group, prop_name)

        for key, value in self.child_definitions.items():
            if value.optional and not hasattr(property_group, key):
                continue
            result[key] = value._serialize_props(getattr(property_group, key))

        return result


# Definition of scene settings (of type int, float, str, color) that are synced in contexts by
# default. In addition to these, there are also stored:
#  - camera and world object
#  - exclude, holdout, indirect_only and hide_viewport of view_layers
#  - hide_render, hide_select and hide_viewport of collections and objects
#
# Definition of scene settings is hierarchical starting from bpy.context, e.g.:
# SyncedPropsDefinition(
#     properties=[],
#     bpy = SyncedPropsDefinition(
#         properties=[],
#         context = SyncedPropsDefinition(
#             properties=[],
#             scene = SyncedPropsDefinition(
#                 properties=[],
#                 render = SyncedPropsDefinition(
#                     properties=["filepath"], ignore_listed=True
#                 )
#             )
#         )
#     )
# )
# Means that everything (of type int, float, str or color) from 'bpy.context.scene.render'
# will be stored in renderset context, except of 'bpy.context.scene.render.filepath'
#
# Beside these default settings, additional scene properties can be marked for storing in renderset
# contexts by renderset.toggle_property_override() operator. The same operator can also mark some of
# the default settings to be ignored.
DEFAULT_SYNCED_SETTINGS = SyncedPropsDefinition(
    properties=[],
    bpy=SyncedPropsDefinition(
        properties=[],
        context=SyncedPropsDefinition(
            properties=[],
            scene=SyncedPropsDefinition(
                properties=[
                    "frame_current",
                    "frame_start",
                    "frame_end",
                    "frame_step",
                ],
                view_settings=SyncedPropsDefinition(
                    properties=[
                        "view_transform",
                        "look",
                        "exposure",
                        "gamma",
                    ]
                ),
                cycles=SyncedPropsDefinition(
                    properties=[
                        "max_bounces",
                        "sample_clamp_direct",
                        "sample_clamp_indirect",
                        "samples",
                        "use_animated_seed",
                    ]
                ),
                eevee=SyncedPropsDefinition(
                    properties=[
                        "taa_render_samples",
                    ]
                ),
                render=SyncedPropsDefinition(
                    properties=[
                        "film_transparent",
                        "engine",
                        "resolution_x",
                        "resolution_y",
                        "resolution_percentage",
                    ],
                    image_settings=SyncedPropsDefinition(
                        properties=[],
                        ignore_listed=True,  # remember all
                    ),
                ),
                octane=SyncedPropsDefinition(
                    properties=[], ignore_listed=True, optional=True  # remember all
                ),
                luxcore=SyncedPropsDefinition(
                    properties=[],
                    optional=True,
                    config=SyncedPropsDefinition(
                        properties=[],
                        ignore_listed=True,  # remember all
                        path=SyncedPropsDefinition(
                            properties=[],
                            ignore_listed=True,  # remember all
                        ),
                    ),
                ),
            ),
        ),
    ),
)


def get_serializable_props(
    property_group: bpy.types.bpy_struct,
) -> typing.Iterator[typing.Tuple[str, typing.Any]]:
    for property in property_group.bl_rna.properties:
        # We filter out properties that are both read-only and hidden to avoid serializing
        # Blender's internal properties that are not supposed to be changed by the user.
        # Pointers and collections are read-only but we serialize their values.
        if property.is_readonly and property.is_hidden:
            continue
        prop_value = getattr(property_group, property.identifier)
        if prop_value is not None:
            yield property.identifier, prop_value


def can_store_custom_property(datablock: bpy.types.bpy_struct) -> bool:
    """Returns True if custom properties can be assigned to `datablock`

    Returns False e.g. for bpy.context.scene.render.image_settings
    """
    return isinstance(datablock, (bpy.types.ID, bpy.types.PropertyGroup))


def get_indexed_prop(
    index: str, prop_container: typing.Any
) -> typing.Optional[bpy.types.bpy_struct]:
    if not index.isdecimal():
        return None
    index = int(index)
    if not isinstance(prop_container, bpy.types.bpy_prop_collection):
        return None
    if index >= len(prop_container):
        return None
    return prop_container[index]


class UUIDToPropCollectionKeyCache:
    """Speculative UUID to prop collection key cache to speed-up UUID lookups

    In many places in renderset we need to lookup a specific datablock by its UUID. Since Blender
    API does not allow us to add UUID as a primary index we have to iterate over all datablocks,
    checking each one. This is super slow for large scenes with many datablocks. To speed this up
    we can remember which UUID maps to which datablock name. This cache is speculative, meaning
    if the user renames the datablock, that particular UUID->name mapping will be stale. Once we
    try to lookup the datablock using it we will realize it's stale and update it. That way the
    worst thing that can happen is slower lookups. The cache 'heals' itself over time.
    """

    def __init__(self, capacity: int) -> None:
        self.cache = collections.OrderedDict()
        self.capacity = capacity

    def get(self, uuid: str) -> typing.Optional[str]:
        ret = self.cache.get(uuid, None)
        if ret is not None:
            self.cache.move_to_end(uuid)
        return ret

    def set(self, uuid: str, key: str) -> None:
        if uuid in self.cache:
            self.cache.move_to_end(uuid)
        else:
            if len(self.cache) >= self.capacity:
                self.cache.popitem(last=False)
            self.cache[uuid] = key

    def clear(self) -> None:
        self.cache.clear()


# TODO: The capacity is arbitrary, we try to really overkill it to avoid trashing at all costs.
UUID_TO_PROP_COLLECTION_KEY_CACHE = UUIDToPropCollectionKeyCache(256 * 1024)


def ensure_renderset_uuid(datablock: bpy.types.ID) -> typing.Optional[str]:
    if not hasattr(datablock, "renderset_uuid"):
        logger.debug(
            f"Asked to ensure {datablock} has a valid renderset_uuid but the property "
            f"is not present in it!"
        )
        return None

    if datablock.renderset_uuid == "":
        datablock.renderset_uuid = uuid.uuid4().hex

    UUID_TO_PROP_COLLECTION_KEY_CACHE.set(datablock.renderset_uuid, datablock.name)
    return datablock.renderset_uuid


def _try_get_datablock_from_uuid_in_iterable(
    uuid: str,
    datablocks: bpy.types.bpy_prop_collection,
    getter: typing.Callable[[bpy.types.bpy_struct], str] = None,
) -> typing.Optional[bpy.types.bpy_struct]:
    potential_key = UUID_TO_PROP_COLLECTION_KEY_CACHE.get(uuid)
    if potential_key is not None:
        datablock_index = datablocks.find(potential_key)
        if datablock_index != -1:
            datablock = datablocks[datablock_index]
            assert datablock is not None

            if getter is None:
                renderset_uuid = getattr(datablock, "renderset_uuid", None)
                if renderset_uuid is not None and renderset_uuid == uuid:
                    return datablock
                else:
                    logger.error(
                        f"Cache hit with key {potential_key}, datablock found but its uuid "
                        f"{renderset_uuid} doesn't match {uuid}!"
                    )
            else:
                if getter(datablock) == uuid:
                    return datablock
                else:
                    logger.error(
                        f"Cache hit with key {potential_key}, datablock found but its uuid "
                        f"{renderset_uuid} doesn't match {uuid}!"
                    )

    for datablock in datablocks:
        try:
            if getter is None:
                renderset_uuid = getattr(datablock, "renderset_uuid", None)
                if renderset_uuid is not None and renderset_uuid == uuid:
                    UUID_TO_PROP_COLLECTION_KEY_CACHE.set(uuid, datablock.name)
                    # logger.debug(
                    #    f"Warmed cache with key {uuid} mapping to {datablock.name}. Cache size "
                    #    f"is now {len(UUID_TO_PROP_COLLECTION_KEY_CACHE.cache)}"
                    # )
                    return datablock
            else:
                if getter(datablock) == uuid:
                    UUID_TO_PROP_COLLECTION_KEY_CACHE.set(uuid, datablock.name)
                    # logger.debug(
                    #    f"Warmed cache with key {uuid} mapping to {datablock.name}. Cache size "
                    #    f"is now {len(UUID_TO_PROP_COLLECTION_KEY_CACHE.cache)}"
                    # )
                    return datablock

        except AttributeError:
            logger.exception(
                f"Uncaught exception while trying to find datablock with renderset uuid {uuid}"
            )

    return None


def try_get_datablock_from_uuid(
    uuid: str,
    datablocks: typing.Optional[typing.Iterable[bpy.types.bpy_struct]],
    getter: typing.Callable[[bpy.types.bpy_struct], str] = None,
) -> typing.Optional[bpy.types.bpy_struct]:
    """Try to find datablock with 'uuid', returns None if datablock was not found.

    Datablocks that inherit from bpy.types.ID are located in one of collections from bpy.data
    (e.g. datablocks from bpy.data.objects or bpy.types.Material). If the 'datablocks' is provided,
    we search for the datablock there to save time.

    But datablock can also inherit directly from bpy.types.bpy_struct without inheritance from
    bpy.types.ID. Since it's not stored in a collection from bpy.data and it doesn't have assigned
    uuid directly, we can find it only if 'datablocks' and 'getter' is provided.
    (e.g. bpy.types.LayerCollection)
    """
    assert not uuid.startswith(RSET_UUID_PREFIX)
    if datablocks is not None:
        return _try_get_datablock_from_uuid_in_iterable(uuid, datablocks, getter)

    # find datablock by UUID in all collections
    datablock: typing.Optional[bpy.types.ID] = None
    for id_collection in get_datablock_types_to_collections().values():
        datablock = _try_get_datablock_from_uuid_in_iterable(uuid, id_collection, getter)
        if datablock is not None:
            return datablock

    return None


def cleanup_duplicate_renderset_uuids(
    datablocks: typing.Iterable[bpy.types.ID],
    setter: typing.Callable[[bpy.types.ID, str], None] = None,
    getter: typing.Callable[[bpy.types.ID], str] = None,
) -> None:
    """In some cases renderset_uuids can become non-unique. The main cause is duplicating
    an existing collection. Blender duplicates the uuid and now there are 2 collections
    with the same uuid.
    We workaround this by assuming that collections later in the list were created later.
    We clear their uuid if it's a duplicate.
    """

    seen_uuids: typing.Set[str] = set()
    for datablock in datablocks:
        uuid: typing.Optional[str] = None
        if getter is None:
            uuid = getattr(datablock, "renderset_uuid", "")
        else:
            uuid = getter(datablock)

        if uuid == "":
            continue

        if uuid in seen_uuids:
            if setter is None:
                setattr(datablock, "renderset_uuid", "")
            else:
                setter(datablock, "")
        seen_uuids.add(uuid)


def _is_up_to_date_uuid(
    tested_datablock: bpy.types.ID, datablocks: typing.Iterable[bpy.types.ID]
) -> bool:
    """Check if the given datablock has an up-to-date UUID.

    Up-to-data UUID has to be a valid UUID and it has to be either unique among the datablocks or if
    it's duplicated, the 'tested_datablock' has to be the first one with this UUID.

    UUID is considered out-dated if it would be removed in cleanup_duplicate_renderset_uuids().
    """
    seen_uuids: typing.Set[str] = set()
    for datablock in datablocks:
        uuid = getattr(datablock, "renderset_uuid", "")

        if datablock == tested_datablock:
            return uuid != "" and uuid not in seen_uuids

        seen_uuids.add(uuid)


def try_get_uuid_from_datablock(
    datablock: bpy.types.ID, writable_context: bool = True
) -> typing.Optional[str]:
    """
    Returns UUID of 'datablock' or None if uuid is not up-to-date and can't be created.

    Used when we do not know the datablock's parent collection. We try to find it across all
    collections in 'bpy.data' (e.g. bpy.data.objects or bpy.types.Material) and check if its
    assigned uuid is up-to-date.

    writable_context: Use False if this method is called from a context where writing into
    properties is forbidden e.g. right-click menu. If False, this will return constant string
    "fake_uuid" if datablock doesn't have a valid UUID. If True, this will create a new UUID if
    datablock doesn't have one or if it's duplicated.
    """
    assert isinstance(datablock, bpy.types.ID) and hasattr(datablock, "renderset_uuid")

    prop_collections = [
        collection
        for type_, collection in get_datablock_types_to_collections().items()
        if isinstance(datablock, type_)
    ]

    if len(prop_collections) == 0:
        logger.warning(f"Could not find a collection for datablock {datablock}!")
        return None
    if len(prop_collections) > 1:
        logger.warning(f"Found multiple collections for datablock {datablock}!")
        return None

    collection = prop_collections[0]
    assert datablock.name_full in collection

    if writable_context:
        cleanup_duplicate_renderset_uuids(collection)
        return ensure_renderset_uuid(datablock)

    # Use UUID if it's not empty or duplicated, otherwise use a fake UUID. We cannot assign
    # anything to ID classes in right-click menu, we'll just use constant string in that case.
    # We can use anything because we're sure it's not stored since it doesn't have valid UUID.
    if _is_up_to_date_uuid(datablock, collection):
        return datablock.renderset_uuid
    else:
        return "fake_uuid"


def get_serializable_property_value(
    property_group: typing.Union[bpy.types.bpy_struct, bpy.types.bpy_prop_collection],
    prop_name: str,
    writable_context: bool = True,
) -> typing.Any:
    """Returns value of property that can be stored in the json

    Returns None if property is not found or if it's not serializable.

    writable_context: Use False if this method is called from a context where writing into
    properties is forbidden e.g. right-click menu. If False and property value is ID datablock, this
    will return a fake UUID. If True, this will create a new UUID if datablock doesn't have one or
    if it's duplicated.
    """
    prop_value = None
    if prop_name.startswith(RSET_UUID_PREFIX):
        # This might turn out as a wrong assumption but I think there's not a valid use case of
        # assigning a value to an ID datablock itself. E.g. bpy.data.objects["Cube"] = something
        logger.error(
            f"Property {prop_name} is a renderset UUID which maps to an ID datablock, "
            "we can't assign anything to it!"
        )
        return None

    if prop_name.startswith(RSET_INDEX_PREFIX):
        prop_name = prop_name[len(RSET_INDEX_PREFIX) :]
        prop_value = get_indexed_prop(prop_name, property_group)
    elif hasattr(property_group, prop_name):
        # Blender inbuilt property or custom property assigned to a type like:
        # bpy.types.Object.prop = bpy.props.IntProperty()
        prop_value = getattr(property_group, prop_name)
    elif can_store_custom_property(property_group) and prop_name in property_group:
        # Custom property assigned to a datablock instance like:
        # obj["another_prop"] = 10
        prop_value = property_group.get(prop_name)
    else:
        logger.warning(f"Property {prop_name} not found in {property_group}!")
        return None

    # Supported primitive types
    if isinstance(prop_value, (str, int, float, bool)):
        return prop_value

    # bpy_prop_array is a type of builtin array properties (like obj.color) or custom properties
    # added on datablock type (like bpy.types.Object.prop = bpy.props.IntVectorProperty())
    SUPPORTED_ITERABLE_TYPES = [bpy.types.bpy_prop_array]
    # idprop.types.IDPropertyArray is a type of array custom property assigned on datablock
    # instance (like obj["another_prop"] = [1, 2, 3])
    SUPPORTED_ITERABLE_TYPES += [idprop.types.IDPropertyArray]
    # mathutils types are types of some builtin properties (like obj.location/rotation/...)
    # Support for mathutils.Matrix is missing, because it's not accessible from the UI.
    SUPPORTED_ITERABLE_TYPES += [
        mathutils.Vector,
        mathutils.Color,
        mathutils.Euler,
        mathutils.Quaternion,
    ]

    if isinstance(prop_value, tuple(SUPPORTED_ITERABLE_TYPES)):
        prop_value = list(prop_value)

    if isinstance(prop_value, list):
        if all(isinstance(v, int) for v in prop_value):
            return prop_value
        elif all(isinstance(v, float) for v in prop_value):
            return prop_value
        else:
            return None

    if isinstance(prop_value, bpy.types.ID):
        uuid = try_get_uuid_from_datablock(prop_value, writable_context=writable_context)
        if uuid is None:
            logger.warning(f"Failed to ensure UUID for {prop_value}!")
            return None

        return f"{RSET_UUID_PREFIX}{uuid}"

    return None


def serialize_property_group_props(
    property_group: typing.Union[bpy.types.bpy_struct, bpy.types.bpy_prop_collection],
    old_json_dict: typing.Dict[str, typing.Any],
) -> typing.Dict[str, typing.Any]:
    json_dict: typing.Dict[str, typing.Any] = {}
    # Serialize properties that were stored in the context previously
    for prop_name, old_prop_value in old_json_dict.items():
        assert prop_name not in json_dict and old_prop_value is not None

        # Nested properties are serialized in a recursive way
        if isinstance(old_prop_value, dict):
            if prop_name.startswith(RSET_INDEX_PREFIX):
                index = prop_name[len(RSET_INDEX_PREFIX) :]
                current_prop_value = get_indexed_prop(index, property_group)
            elif prop_name.startswith(RSET_UUID_PREFIX):
                uuid = prop_name[len(RSET_UUID_PREFIX) :]
                collection = None
                if isinstance(property_group, bpy.types.bpy_prop_collection):
                    collection = property_group
                current_prop_value = try_get_datablock_from_uuid(uuid, collection)
            else:
                current_prop_value = getattr(property_group, prop_name, None)

            if current_prop_value is None:
                logger.warning(
                    f"Property {prop_name} could not be retrieved from {property_group}. Value "
                    f"{old_prop_value} stored in the context previously will be kept instead."
                )
                json_dict[prop_name] = old_prop_value
            else:
                json_dict[prop_name] = serialize_property_group_props(
                    current_prop_value, old_prop_value
                )
            continue

        current_prop_value = get_serializable_property_value(property_group, prop_name)
        if current_prop_value is None:
            logger.warning(
                f"Property {prop_name} could not be retrieved from {property_group} or has "
                f"unsupported type. Value {old_prop_value} stored in the context previously will "
                "be kept instead."
            )
            json_dict[prop_name] = old_prop_value
        else:
            json_dict[prop_name] = current_prop_value

    return json_dict


def apply_property_group_props(
    property_group: typing.Union[bpy.types.bpy_struct, bpy.types.bpy_prop_collection],
    json_dict: typing.Dict[str, typing.Any],
    attempts: int = 3,
) -> None:
    # We have to try several times because we don't control in which order the properties
    # are applied. In some cases setting one of the properties opens up more options in other
    # properties (e.g. enums). For example setting image output format to PNG allows different
    # color depth options than Cineon. We try this multiple times in the hope that we apply all
    # properties.
    # TODO: Instead of running this loop 3 times, check if we changed some value and keep repeating
    # as long as we are changing something
    while attempts > 0:
        attempts -= 1

        error_encountered = False
        for prop_name, stored_prop_value in json_dict.items():
            # This property is a property group -> call self recursively
            if isinstance(stored_prop_value, dict):
                if prop_name.startswith(RSET_INDEX_PREFIX):
                    index = prop_name[len(RSET_INDEX_PREFIX) :]
                    current_prop_value = get_indexed_prop(index, property_group)
                elif prop_name.startswith(RSET_UUID_PREFIX):
                    uuid = prop_name[len(RSET_UUID_PREFIX) :]
                    collection = None
                    if isinstance(property_group, bpy.types.bpy_prop_collection):
                        collection = property_group
                    current_prop_value = try_get_datablock_from_uuid(uuid, collection)
                else:
                    current_prop_value = getattr(property_group, prop_name, None)

                if current_prop_value is None:
                    logger.warning(
                        f"Property group {prop_name} could not be retrieved from {property_group} "
                        f"even though it is stored in the context. Skipping.."
                    )
                else:
                    # Try inner values only once, it will be run three times in total
                    apply_property_group_props(current_prop_value, stored_prop_value, 1)
                continue

            current_prop_value = get_serializable_property_value(property_group, prop_name)
            if current_prop_value is None:
                logger.warning(
                    f"Property {prop_name} not found in {property_group} or has unsupported type. "
                    "Skipping.."
                )
                continue

            # skip values that are already the same, this prevents Blender freezing up
            # and recalculating
            if stored_prop_value == current_prop_value:
                continue

            if isinstance(stored_prop_value, str) and stored_prop_value.startswith(
                RSET_UUID_PREFIX
            ):
                uuid = stored_prop_value[len(RSET_UUID_PREFIX) :]
                stored_prop_value = try_get_datablock_from_uuid(uuid, None)
                if stored_prop_value is None:
                    logger.warning(
                        f"Datablock with uuid {uuid} not found in any collection, so it can't be "
                        "assigned. Skipping.."
                    )
                    continue

            try:
                if hasattr(property_group, prop_name):
                    setattr(property_group, prop_name, stored_prop_value)
                else:
                    # Custom property assigned only to a datablock instance
                    property_group[prop_name] = stored_prop_value
                    # Currently, we support custom properties only on datablocks inheriting from
                    # bpy.types.ID. Custom properties on other datablocks like nodes can be
                    # assigned only in the code and it's not accessible from the UI.
                    assert isinstance(property_group, bpy.types.ID)
                    # Python assignments to custom properties doesn't automatically tag datablocks
                    # for updates in the dependency graph (for performance reasons). We have to tag
                    # it manually, otherwise e.g. drivers won't be updated.
                    property_group.update_tag()
            except (AttributeError, TypeError):
                # read only
                error_encountered = True
                pass

        if not error_encountered:
            break


def serialize_layer_collection_props(
    layer_collection: bpy.types.LayerCollection,
    toggles_settings: scene_props.LayerCollectionTogglesSettings,
) -> typing.Dict[str, typing.Any]:
    json_dict = {}
    if not any(
        [
            toggles_settings.exclude,
            toggles_settings.holdout,
            toggles_settings.indirect_only,
            toggles_settings.hide_viewport,
        ]
    ):
        # this function wouldn't serialize anything useful, all the toggles are disabled!
        return json_dict

    if toggles_settings.exclude:
        json_dict["exclude"] = layer_collection.exclude
    if toggles_settings.holdout:
        json_dict["holdout"] = layer_collection.holdout
    if toggles_settings.indirect_only:
        json_dict["indirect_only"] = layer_collection.indirect_only
    if toggles_settings.hide_viewport:
        json_dict["hide_viewport"] = layer_collection.hide_viewport

    cleanup_duplicate_renderset_uuids(
        layer_collection.children,
        setter=lambda lc, v: setattr(lc.collection, "renderset_uuid", v),
        getter=lambda lc: getattr(lc.collection, "renderset_uuid"),
    )

    children = {}
    for child in layer_collection.children:
        ensure_renderset_uuid(child.collection)
        layer_collection_uuid = f"{RSET_UUID_PREFIX}{child.collection.renderset_uuid}"
        assert layer_collection_uuid not in children
        children[layer_collection_uuid] = serialize_layer_collection_props(child, toggles_settings)

    json_dict["children"] = children

    return json_dict


def serialize_view_layers_props(
    view_layers: typing.Iterable[bpy.types.ViewLayer],
    toggles_settings: scene_props.LayerCollectionTogglesSettings,
) -> typing.Dict[str, typing.Any]:
    json_dict: typing.Dict[str, typing.Any] = {}
    if not any(
        [
            toggles_settings.exclude,
            toggles_settings.holdout,
            toggles_settings.indirect_only,
            toggles_settings.hide_viewport,
        ]
    ):
        # this function wouldn't serialize anything useful, all the toggles are disabled!
        return json_dict

    cleanup_duplicate_renderset_uuids(view_layers)
    for view_layer in view_layers:
        ensure_renderset_uuid(view_layer)
        view_layer_uuid = f"{RSET_UUID_PREFIX}{view_layer.renderset_uuid}"
        assert view_layer_uuid not in json_dict
        layer_col_dict = {}
        if view_layer.layer_collection is not None:
            layer_col_dict = serialize_layer_collection_props(
                view_layer.layer_collection, toggles_settings
            )
        json_dict[view_layer_uuid] = {"layer_collection": layer_col_dict}
    return json_dict


def apply_layer_collection_props(
    layer_collection: bpy.types.LayerCollection,
    json_dict: typing.Dict[str, typing.Any],
    toggles_settings: scene_props.LayerCollectionTogglesSettings,
) -> None:
    if not any(
        [
            toggles_settings.exclude,
            toggles_settings.holdout,
            toggles_settings.indirect_only,
            toggles_settings.hide_viewport,
        ]
    ):
        return  # this function won't do anything, all the toggles are disabled!

    if toggles_settings.exclude:
        exclude_json = json_dict.get("exclude", None)
        if exclude_json is not None and layer_collection.exclude != exclude_json:
            layer_collection.exclude = exclude_json

    if toggles_settings.holdout:
        holdout_json = json_dict.get("holdout", None)
        if holdout_json is not None and layer_collection.holdout != holdout_json:
            layer_collection.holdout = holdout_json

    if toggles_settings.indirect_only:
        indirect_only_json = json_dict.get("indirect_only", None)
        if indirect_only_json is not None and layer_collection.indirect_only != indirect_only_json:
            layer_collection.indirect_only = indirect_only_json

    if toggles_settings.hide_viewport:
        hide_viewport_json = json_dict.get("hide_viewport", None)
        if hide_viewport_json is not None and layer_collection.hide_viewport != hide_viewport_json:
            layer_collection.hide_viewport = hide_viewport_json

    for collection_uuid, child_layer_collection_dict in json_dict.get("children", {}).items():
        collection_uuid = collection_uuid.removeprefix(RSET_UUID_PREFIX)
        child_layer_collection = try_get_datablock_from_uuid(
            collection_uuid,
            layer_collection.children,
            lambda lc: lc.collection.renderset_uuid,
        )
        if child_layer_collection is None:
            logger.debug(f"Failed to find layer collection with collection.uuid {collection_uuid}.")
            continue
        apply_layer_collection_props(
            child_layer_collection, child_layer_collection_dict, toggles_settings
        )


def apply_view_layers_props(
    view_layers: typing.Iterable[bpy.types.ViewLayer],
    json_dict: typing.Dict[str, typing.Any],
    toggles_settings: scene_props.LayerCollectionTogglesSettings,
) -> None:
    if not any(
        [
            toggles_settings.exclude,
            toggles_settings.holdout,
            toggles_settings.indirect_only,
            toggles_settings.hide_viewport,
        ]
    ):
        return  # this function won't do anything, all the toggles are disabled!

    for view_layer_uuid, view_layer_dict in json_dict.items():
        view_layer_uuid = view_layer_uuid.removeprefix(RSET_UUID_PREFIX)
        view_layer = try_get_datablock_from_uuid(view_layer_uuid, view_layers)
        if view_layer is None:
            logger.debug(
                f"Tried to synchronize view_layer with uuid {view_layer_uuid} "
                f"from json str but such uuid was not found among the view_layers!"
            )
            continue

        if view_layer.layer_collection is None:
            return

        layer_collection_dict = view_layer_dict["layer_collection"]
        if len(layer_collection_dict) == 0:
            return
        apply_layer_collection_props(
            view_layer.layer_collection, layer_collection_dict, toggles_settings
        )


def serialize_collection_props(
    collection: bpy.types.Collection, toggles_settings: scene_props.CollectionTogglesSettings
) -> typing.Dict[str, typing.Any]:
    json_dict = {}
    if not any(
        [toggles_settings.hide_render, toggles_settings.hide_select, toggles_settings.hide_viewport]
    ):
        return json_dict  # all toggles are disabled, we wouldn't serialize anything useful

    if toggles_settings.hide_render:
        json_dict["hide_render"] = collection.hide_render
    if toggles_settings.hide_select:
        json_dict["hide_select"] = collection.hide_select
    if toggles_settings.hide_viewport:
        json_dict["hide_viewport"] = collection.hide_viewport

    cleanup_duplicate_renderset_uuids(collection.children)
    children = {}
    for child in collection.children:
        ensure_renderset_uuid(child)
        child_uuid = f"{RSET_UUID_PREFIX}{child.renderset_uuid}"
        assert child_uuid not in children
        children[child_uuid] = serialize_collection_props(child, toggles_settings)

    json_dict["children"] = children
    return json_dict


def apply_collection_props(
    collection: bpy.types.Collection,
    json_dict: typing.Dict[str, typing.Any],
    toggles_settings: scene_props.CollectionTogglesSettings,
) -> None:
    if not any(
        [toggles_settings.hide_render, toggles_settings.hide_select, toggles_settings.hide_viewport]
    ):
        return  # this function won't do anything, all the toggles are disabled!

    if toggles_settings.hide_render:
        hide_render_json = json_dict.get("hide_render", None)
        if hide_render_json is not None and collection.hide_render != hide_render_json:
            collection.hide_render = hide_render_json

    if toggles_settings.hide_select:
        hide_select_json = json_dict.get("hide_select", None)
        if hide_select_json is not None and collection.hide_select != hide_select_json:
            collection.hide_select = hide_select_json

    if toggles_settings.hide_viewport:
        hide_viewport_json = json_dict.get("hide_viewport", None)
        if hide_viewport_json is not None and collection.hide_viewport != hide_viewport_json:
            collection.hide_viewport = hide_viewport_json

    for child_collection_uuid, child_collection_dict in json_dict.get("children", {}).items():
        child_collection_uuid = child_collection_uuid.removeprefix(RSET_UUID_PREFIX)
        child_collection = try_get_datablock_from_uuid(child_collection_uuid, collection.children)
        if child_collection is None:
            logger.debug(
                f"Tried to synchronize collection with uuid {child_collection_uuid} "
                f"from json str but such uuid was not found among the child collections!"
            )
            continue

        apply_collection_props(child_collection, child_collection_dict, toggles_settings)


def apply_object_props(
    obj: bpy.types.Object,
    json_dict: typing.Dict[str, typing.Any],
    toggles_settings: scene_props.ObjectTogglesSettings,
) -> None:
    if toggles_settings.hide_render:
        hide_render_json = json_dict.get("hide_render", None)
        if hide_render_json is not None and obj.hide_render != hide_render_json:
            obj.hide_render = hide_render_json

    if toggles_settings.hide_select:
        hide_select_json = json_dict.get("hide_select", None)
        if hide_select_json is not None and obj.hide_select != hide_select_json:
            obj.hide_select = hide_select_json

    if toggles_settings.hide_viewport:
        hide_viewport_json = json_dict.get("hide_viewport", None)
        if hide_viewport_json is not None and obj.hide_viewport != hide_viewport_json:
            obj.hide_viewport = hide_viewport_json


def apply_objects_props(
    objects: typing.Iterable[bpy.types.Object],
    json_dict: typing.Dict[str, typing.Any],
    toggles_settings: scene_props.ObjectTogglesSettings,
) -> None:
    if not any(
        [toggles_settings.hide_render, toggles_settings.hide_select, toggles_settings.hide_viewport]
    ):
        return  # this function won't do anything, all the toggles are disabled!

    for obj_uuid, obj_json_dict in json_dict.items():
        obj_uuid = obj_uuid.removeprefix(RSET_UUID_PREFIX)
        obj = try_get_datablock_from_uuid(obj_uuid, objects)
        if obj is None:
            logger.debug(
                f"Tried to sync object with uuid {obj_uuid}, but it was not found in objects collection."
            )
            continue

        apply_object_props(obj, obj_json_dict, toggles_settings)


def serialize_object_props(
    obj: bpy.types.Object, toggles_settings: scene_props.ObjectTogglesSettings
) -> typing.Dict[str, typing.Any]:
    json_dict = {}
    if toggles_settings.hide_render:
        json_dict["hide_render"] = obj.hide_render
    if toggles_settings.hide_select:
        json_dict["hide_select"] = obj.hide_select
    if toggles_settings.hide_viewport:
        json_dict["hide_viewport"] = obj.hide_viewport

    return json_dict


def serialize_objects_props(
    objects: typing.Iterable[bpy.types.Object], toggles_settings: scene_props.ObjectTogglesSettings
) -> typing.Dict[str, typing.Any]:
    json_dict = {}
    if not any(
        [toggles_settings.hide_render, toggles_settings.hide_select, toggles_settings.hide_viewport]
    ):
        return json_dict  # this function wouldn't serialize anything useful, all the toggles are disabled!

    cleanup_duplicate_renderset_uuids(objects)
    for obj in objects:
        ensure_renderset_uuid(obj)
        obj_uuid = f"{RSET_UUID_PREFIX}{obj.renderset_uuid}"
        assert obj_uuid not in json_dict
        json_dict[obj_uuid] = serialize_object_props(obj, toggles_settings)
    return json_dict


def flatten_dict(
    dictionary: typing.Dict[str, typing.Any], parent_key: str = "", separator: str = "."
) -> typing.Dict[str, typing.Any]:
    """Flatten dictionary to one level.

    Example:    {"a": {"b": 1, "c": 2}, "d": 3} -> {"a.b": 1, "a.c": 2, "d": 3}
    """
    result: typing.Dict[str, typing.Any] = {}
    for key, value in dictionary.items():
        new_key = (parent_key + separator + key) if parent_key else key
        if isinstance(value, collections.abc.Mapping):
            inner = flatten_dict(value, new_key, separator=separator)
            assert result.keys().isdisjoint(inner.keys())
            result.update(inner)
        else:
            assert new_key not in result
            result[new_key] = value
    return result


def apply_flattened_patch(
    dictionary: typing.Dict[str, typing.Any],
    flattened_patch: typing.Dict[str, typing.Any],
    separator: str = ".",
) -> typing.Dict[str, typing.Any]:
    ret = dictionary.copy()

    def apply_flattened_patch_hunk(hunk_key: str, hunk_value: typing.Any):
        key_parts = hunk_key.split(separator)
        assert len(key_parts) >= 1
        current_dict = ret
        for key_part in key_parts[:-1]:
            if not key_part in current_dict:
                current_dict[key_part] = {}
            current_dict = current_dict[key_part]
        current_dict[key_parts[-1]] = hunk_value

    for hunk_key, hunk_value in flattened_patch.items():
        apply_flattened_patch_hunk(hunk_key, hunk_value)

    return ret


def draw_property(
    prop_container: bpy.types.bpy_struct, prop_name: str, layout: bpy.types.UILayout, **kwargs
) -> None:
    """Draws property in the layout, supports in-built as well as custom properties"""
    if hasattr(prop_container, prop_name):
        # In-built property or custom property assigned to a type
        layout.prop(prop_container, prop_name, **kwargs)
    elif can_store_custom_property(prop_container) and prop_name in prop_container:
        # Custom property assigned only to a datablock instance
        layout.prop(prop_container, f'["{prop_name}"]', **kwargs)
