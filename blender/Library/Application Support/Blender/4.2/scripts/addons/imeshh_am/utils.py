import bpy
from bpy.props import EnumProperty, IntProperty, StringProperty, BoolProperty
from . import folder_utils
import os
import re
#avoid to update preview list 200x at each draw
CURR_PREVIEW = []


def remove_higher(context, cls):
    to_del = []
    find = False
    for idx, f_list in enumerate(context.scene.imeshh_am.ui_folder_list):
        if find:
            to_del.append(idx)
        if f_list == cls:
            find = True
    for idx in to_del:
        context.scene.imeshh_am.ui_folder_list.remove(idx)


def on_change_subdir(cls, context):
    #clear subdirectories display
    remove_higher(context, cls)
    remove_higher(context, cls)
    if hasattr(cls, "list_subdirs") and  cls.list_subdirs != "All":
        #add a new sub display
        folder_list = context.scene.imeshh_am.ui_folder_list.add()
        #set his start folder
        folder_list.start_folder = cls.list_subdirs
    update_and_set_preview(cls, context)    

def on_change_tab(cls, context):
    #clear subdir display
    context.scene.imeshh_am.ui_folder_list.clear()
    #add subdir display
    folder_list = context.scene.imeshh_am.ui_folder_list.add()
    # Reset main folder dropdown value to 0
    items = folder_utils.get_tab_main_dirs(cls, context)
    if items:
        context.scene.imeshh_am.ui_main_folder = items[0][0]
    #set his start folder
    folder_list.start_folder = context.scene.imeshh_am.ui_main_folder
    update_and_set_preview(cls, context)

def on_change_main_folder(cls, context):
    #clear subdir display
    context.scene.imeshh_am.ui_folder_list.clear()
    #add subdir display
    folder_list = context.scene.imeshh_am.ui_folder_list.add()
    #set his start folder
    folder_list.start_folder = context.scene.imeshh_am.ui_main_folder
    update_and_set_preview(cls, context)

def get_name(filepath : str, context) -> str:
    """Return epured file name of given filepath."""
    curr_tab = context.scene.imeshh_am.tabs
    name = filepath.split(os.sep)[-1]
    for ext in folder_utils.EXT[curr_tab]:
        name = name.replace(ext, "")
    name = name.replace(" ", "-")
    return name

def filter_items(context, items):
    to_del = []
    for item in items:
        #id -> asset.file_path
        if context.scene.imeshh_am.search_bar.lower() not in item[0].lower():
            to_del.append(item)
    for item in to_del:
        items.remove(item)
    return items

def update_search_bar(cls, context):
    update_and_set_preview(cls, context)

def update_and_set_preview(cls, context):
    """Call update to previews list value and set to first item."""
    previews = update_previews(cls, context)
    if previews:
        context.window_manager.asset_manager_previews = previews[0][0]

def update_previews(cls, context):
    """Return items of the preview panel."""
    global CURR_PREVIEW
    if isinstance(cls, iMeshh_AM) or isinstance(cls, UIFolder) or not CURR_PREVIEW:
        if context.scene.imeshh_am.ui_folder_list:
            items = []
            from . import preview_collections
            curr_dir = context.scene.imeshh_am.ui_folder_list[-1].start_folder
            if os.path.exists(curr_dir):
                assets = folder_utils.get_all_sub_assets(curr_dir, context)
                img_ids = {}
                for asset in assets:
                    if asset.img_path:
                        id = folder_utils.load_preview(asset.img_path, preview_collections["main"])
                        img_ids[id] = asset.file_path
                for id in img_ids.keys():
                    name = get_name(img_ids[id].split(os.sep)[-1], context)
                    #(identifier, name, description, icon, number)
                    items.append((img_ids[id], name, name, id, len(items)))
                if context.scene.imeshh_am.search_bar:
                    items = filter_items(context, items.copy())
                CURR_PREVIEW = items
    return CURR_PREVIEW

class PathString(bpy.types.PropertyGroup):
    path: StringProperty(subtype="DIR_PATH")
    name: StringProperty()
    type_dir : EnumProperty(
        #(identifier, name, description, icon, number)
        items=[('OBJECT', 'Object', 'Object tab', 'MESH_MONKEY', 0),
               ('MATERIAL', 'Material', 'Material tab', 'MATERIAL', 1),
               ('HDRI', 'Hdri', 'Hdri tab', 'WORLD_DATA', 2)], 
        name = 'Types', 
        description = 'Selected tab',)

class UIFolder(bpy.types.PropertyGroup):
    start_folder : StringProperty(name="start folder", default="")
    list_subdirs : EnumProperty(
        items= folder_utils.get_subdirs_as_items,
        name = 'Subdirs', 
        description = 'Sub directories',
        update=on_change_subdir
        )
    idx : IntProperty(name="idx", default=-1)

class iMeshh_AM(bpy.types.PropertyGroup):
    blend : EnumProperty(
                items=[('cycles', 'Cycles', '', 0), ('corona', 'Corona', '', 1)],
                name="Blend",
                description="Select blend")
    current_folder : StringProperty(name='current_folder', default="")

    ui_folder_list : bpy.props.CollectionProperty(type=UIFolder)

    ui_main_folder : EnumProperty(
        items=folder_utils.get_tab_main_dirs,
        name="directory",
        description="main root directory",
        update=on_change_main_folder)
    
    snap : BoolProperty(name='snap', default=False)
    search_bar : StringProperty(name='searchbar', default="", update=update_search_bar)
    #Tabs
    tabs : EnumProperty(
                #(identifier, name, description, icon, number)
                items=[('OBJECT', 'Object', 'Object tab', 'MESH_MONKEY', 0),
                    ('MATERIAL', 'Material', 'Material tab', 'MATERIAL', 1),
                    ('HDRI', 'Hdri', 'Hdri tab', 'WORLD_DATA', 2)], 
                name = 'Tabs', 
                description = 'Selected tab', 
                update=on_change_tab
                )

    asset_manager_collection_import : bpy.props.BoolProperty(
        name="Import other collections if available",
        default=False,
        description="If there are multiple collections in this file, and you don't want to just import the scene collection, then tick this box")

    asset_manager_auto_rename : bpy.props.BoolProperty(
        name="Auto rename Collection to file name",
        default=True,
        description="This addon, by default, will just import the scene collection. This will then auto-rename the scene collection to the assets file name. This will make it easier to find in the library")

    asset_manager_ignore_camera : bpy.props.BoolProperty(
        name="Ignore camera when importing",
        default=True,
        description="This addon will ignore all cameras by default. If you want to import cameras then untick this box")

def enum_members_from_type(rna_type, property):
    prop = rna_type.bl_rna.properties[property]
    return [e.identifier for e in prop.enum_items]

def enum_members_from_instance(data, property):
    """get all available entries for an enum property
    - data : (AnyType) data from wich tot ake property
    - property : (string) Edientifier property in data"""
    return enum_members_from_type(type(data), property)

def select(obj):
    if is_2_80():
        obj.select_set(True)
    else:
        obj.select = True

def is_blend(file):
    return file.lower().endswith(('.blend',))

def get_selected_file(context):
    return context.window_manager.asset_manager_previews

def is_2_80():
    return bpy.app.version >= (2, 80, 0)

def get_data_colls():
    if hasattr(bpy.data, "collections"):
        return bpy.data.collections
    elif hasattr(bpy.data, "groups"):
        return bpy.data.groups

def create_instance_collection(collection, parent_collection):
    empty = bpy.data.objects.new(name = collection.name, object_data = None)
    empty.instance_collection = collection
    empty.instance_type = 'COLLECTION'
    parent_collection.objects.link(empty)
    return empty

def select_coll_to_import(collection_names):
    """ Select wich collection import following the file type and user preferences
    - collection_names : collections names array avalaibles in the blender file
    """
    #file has no collections (blander version < blender 2.80)
    if not collection_names:
        return None
    
    #User ask for import all collections of blend file
    if bpy.context.scene.imeshh_am.asset_manager_collection_import == True:
        return collection_names

    # there is a collection call 'Collection'
    if 'Collection' in collection_names:
        return ['Collection']
    
    # there is no 'Collection' but something like 'Collection.xxx'
    colls = []
    for col in collection_names:
        if re.match(r'(^collection)', col, re.IGNORECASE):
            colls.append(col)
    if colls:
        return colls
    #there is collection but no match, import all
    else:
        return collection_names

def link_collections(blend_file, parent_col):
    """ Import collections of a blend file as instances collection if it's possible
    - blend_file : file with collection to import
    - parent_col : collection of actual file wich will get as child news instances collections
    """
    objects_linked = False
    with bpy.data.libraries.load(blend_file, link = True) as (data_from, data_to):
        data_to.collections = select_coll_to_import(data_from.collections)
        if data_to.collections == None:
            objects_linked = True
            data_to.objects = data_from.objects
    
    # fix if color space unrecognized
    for img in bpy.data.images:
        if img.colorspace_settings.name == '':
                possible_values = img.colorspace_settings.bl_rna.properties["name"].enum_items.keys()
                if 'sRGB' in possible_values:
                    img.colorspace_settings.name = 'sRGB'
    #no collection found in blend file
    if objects_linked:
        for obj in data_to.objects:
            if bpy.context.scene.imeshh_am.asset_manager_ignore_camera \
            and obj.type == 'CAMERA':
                continue
            # override object
            ov = obj.override_create()
            parent_col.objects.link(ov)
            select(ov)
    else:
        # check if imported collections are not empty
        sub_objects = []
        for col in data_to.collections:
            if col.objects:
                sub_objects.extend(col.objects)
        # link and override every found objects
        if not sub_objects:
            with bpy.data.libraries.load(blend_file, link = True) as (data_from, data_to):
                data_to.objects = data_from.objects
            for obj in data_to.objects:
                if bpy.context.scene.imeshh_am.asset_manager_ignore_camera \
                and obj.type == 'CAMERA':
                    continue
                # override object
                ov = obj.override_create()
                parent_col.objects.link(ov)
                select(ov)
        else:
            #create all instances collections
            for col in data_to.collections:
                instance = create_instance_collection(col, parent_col)
                if re.match(r'(^collection)', instance.name, re.IGNORECASE) \
                and bpy.context.scene.imeshh_am.asset_manager_auto_rename == True:
                    instance.name = parent_col.name
                select(instance)

def get_selected_blend(context):
    file = get_selected_file(context)
    return file
    # if is_blend(file):
    #     if context.scene.asset_manager.blend == 'corona':
    #         return file.replace('Cycles', 'Corona')
    #     else:
    #         return file.replace('Corona', 'Cycles')

def append_blend(blend_file, link=False):
    coll_name = os.path.splitext(os.path.basename(blend_file))[0].title()
    obj_coll = get_data_colls().new(coll_name)

    if is_2_80():
        asset_coll = get_data_colls()[get_asset_col_name()]
        asset_coll.children.link(obj_coll)

    if not link:
        with bpy.data.libraries.load(blend_file, link = link) as (data_from, data_to):
            data_to.objects = data_from.objects
        # fix if color space unrecognized
        for img in bpy.data.images:
            if img.colorspace_settings.name == '':
                # get colorspace possible values
                possible_values = img.colorspace_settings.bl_rna.properties["name"].enum_items.keys()
                if 'sRGB' in possible_values:
                    img.colorspace_settings.name = 'sRGB'

        for obj in data_to.objects:
            if bpy.context.scene.imeshh_am.asset_manager_ignore_camera \
            and obj.type == 'CAMERA':
                continue
            obj_coll.objects.link(obj)

            select(obj)
    else:
        link_collections(blend_file, obj_coll)

    bpy.ops.view3d.snap_selected_to_cursor(use_offset=True)

def get_asset_col_name():
    asset_col_name = "_".join(["Imeshh_Assets", bpy.context.scene.name])
    return asset_col_name

def import_object(context, link):
    # active_layer = context.view_layer.active_layer_collection

    # Deselect all objects
    if  bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT', toggle = False)
    bpy.ops.object.select_all(action='DESELECT')

    # 2.79 and 2.80 killing me.
    if is_2_80():
        if get_asset_col_name() not in bpy.context.scene.collection.children.keys():
            asset_coll = bpy.data.collections.new(get_asset_col_name())
            context.scene.collection.children.link(asset_coll)

    blend = get_selected_blend(context)
    if blend:
        append_blend(blend, link)

def import_material(context, link):
    active_ob = context.active_object
    if bpy.ops.object.mode_set.poll(): 
        bpy.ops.object.mode_set(mode='OBJECT', toggle = False)
    bpy.ops.object.select_all(action='DESELECT')

    blend = get_selected_blend(context)
    files = []
    with bpy.data.libraries.load(blend) as (data_from, data_to):
        for name in data_from.materials:
            files.append({'name': name})
    action = bpy.ops.wm.link if link else bpy.ops.wm.append
    action(directory=blend + "/Material/", files=files)

    if active_ob is not None:
        for file in files:
            mat = bpy.data.materials[file['name']]
            active_ob.data.materials.append(mat)
            select(active_ob)
