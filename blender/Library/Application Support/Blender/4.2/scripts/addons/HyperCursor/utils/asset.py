import bpy
import os
from . system import printd
from . registration import get_prefs

def get_asset_library_reference(params):
    if bpy.app.version >= (4, 0, 0):
        return params.asset_library_reference
    else:
        return params.asset_library_ref

def set_asset_library_reference(params, name):
    if bpy.app.version >= (4, 0, 0):
        params.asset_library_reference = name
    else:
        params.asset_library_ref = name

def get_asset_import_method(params):
    if bpy.app.version >= (4, 0, 0):
        return params.import_method
    else:
        return params.import_type

def set_asset_import_method(params, name):
    if bpy.app.version >= (4, 0, 0):
        params.import_method = name
    else:
        params.import_type = name

def get_asset_ids(context):
    if bpy.app.version >= (4, 0, 0):
        active = context.asset

    else:
        active = context.active_file

    if active:
        return active, active.id_type, active.local_id

    return None, None, None

def get_catalogs_from_asset_libraries(context, debug=False):
    asset_libraries = context.preferences.filepaths.asset_libraries
    all_catalogs = []

    for lib in asset_libraries:
        libname = lib.name
        libpath = lib.path

        cat_path = os.path.join(libpath, 'blender_assets.cats.txt')

        if os.path.exists(cat_path):
            if debug:
                print(libname, cat_path)

            with open(cat_path) as f:
                lines = f.readlines()

            for line in lines:
                if line != '\n' and not any([line.startswith(skip) for skip in ['#', 'VERSION']]) and len(line.split(':')) == 3:
                    all_catalogs.append(line[:-1].split(':') + [libname, libpath])

    catalogs = {}

    for uuid, catalog, simple_name, libname, libpath in all_catalogs:
        if uuid not in catalogs:
            catalogs[uuid] = {'catalog': catalog,
                              'simple_name': simple_name,
                              'libname': libname,
                              'libpath': libpath}

    if debug:
        printd(catalogs)

    return catalogs

def update_asset_catalogs(self, context, curve=False):
    self.catalogs = get_catalogs_from_asset_libraries(context, debug=False)

    catalog_names = []
    items = [('NONE', 'None', '')]

    for uuid, catalog_data in self.catalogs.items():
        catalog = catalog_data['catalog']

        if catalog not in catalog_names:
            catalog_names.append(catalog)
            items.append((catalog, catalog, ''))

    if curve:
        default = get_prefs().preferred_default_catalog_curve if get_prefs().preferred_default_catalog_curve in catalog_names else 'NONE'
    else:
        default = get_prefs().preferred_default_catalog if get_prefs().preferred_default_catalog in catalog_names else 'NONE'
    bpy.types.WindowManager.HC_asset_catalogs = bpy.props.EnumProperty(name="Asset Categories", items=items, default=default)

def get_pretty_assetpath(inpt, debug=False):

    if isinstance(inpt, list):
        libname, filename = inpt

        if libname == 'LOCAL':
            if 'Object/' in filename:
                return f"{libname} • {filename.replace('Object/', '')}"

        else:
            split = filename.split('.blend/Object/')

            if len(split) == 2:
                blendname, assetname = split

                return f"{libname} • {blendname} • {assetname}"

    else:
        from HyperCursor.properties import RedoAddObjectCollection

        if isinstance(inpt, RedoAddObjectCollection):
            asset = inpt

        else:
            asset = inpt.HC

        if debug:
            print()
            print("libname:", asset.libname)
            print("blendpath:", asset.blendpath)
            print("assetname:", asset.assetname)

        if asset.libname == 'LOCAL':
            return f"{asset.libname} • {asset.assetname}"

        elif asset.assetname and len(bpy.context.preferences.filepaths.asset_libraries) > 1:
            pretty = f"{asset.libname} • {asset.blendpath} • {asset.assetname}" if asset.blendpath else f"{asset.libname} • {asset.assetname}"

        elif asset.assetname:
            pretty = f"{asset.blendpath} • {asset.assetname}" if asset.blendpath else f"{asset.libname} • {asset.assetname}"

        else:
            pretty = inpt.name

        return pretty

def get_asset_details_from_space(context, space, debug=False):

    lib_reference = get_asset_library_reference(space.params)
    catalog_id = space.params.catalog_id
    libname = '' if lib_reference == 'ALL' else lib_reference
    libpath = space.params.directory.decode('utf-8')
    filename = space.params.filename
    import_method = get_asset_import_method(space.params)

    if debug:
        print()
        print("get_asset_details_from_space()")
        print(" asset_library_reference:", lib_reference)
        print(" catalog_id:", catalog_id)
        print(" libname:", libname)
        print(" libpath:", libpath)
        print(" filename:", filename)
        print(" import_method:", import_method)
        print()

    if libname == 'ESSENTIALS':
        return None, None, '', None

    elif libname == 'LOCAL':
        if 'Object/' in filename:
            return libname, libpath, filename, import_method

    elif not '.blend' in filename:
        if debug:
            print(" WARNING: LOCAL library, but ALL or library is chosen (instead of current file)!")

        if 'Object/' in filename:
            return 'LOCAL', '', filename, import_method

    elif not libname and not libpath:
        if debug:
            print(" WARNING: EXTERNAL library, but library ref is ALL and directory is not set!")

        catalogs = get_catalogs_from_asset_libraries(context, debug=False)

        for uuid, catdata in catalogs.items():
            if catalog_id == uuid:
                catalog = catdata['catalog']
                libname = catdata['libname']
                libpath = catdata['libpath']

                if debug:
                    print(f" INFO: found catalog {catalog}'s libname and libpath via asset catalogs:", libname, "at", libpath)
                break
    if debug:
        print()

    if libpath:
        return libname, libpath, filename, import_method

    else:
        return None, None, '', None
