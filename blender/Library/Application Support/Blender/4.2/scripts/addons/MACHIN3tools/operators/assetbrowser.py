import bpy
from bpy.props import StringProperty, BoolProperty, FloatProperty, EnumProperty, IntProperty
import os
from mathutils import Vector
import numpy as np
from .. utils.asset import get_asset_library_reference, set_asset_library_reference, update_asset_catalogs
from .. utils.asset import get_assetbrowser_bookmarks, get_catalogs_from_asset_libraries, get_libref_and_catalog, set_assetbrowser_bookmarks, validate_libref_and_catalog
from .. utils.draw import draw_fading_label, draw_points, draw_line
from .. utils.math import average_locations, create_coords_bbox, get_loc_matrix
from .. utils.object import get_eval_bbox, get_object_tree, get_parent, remove_obj, duplicate_objects
from .. utils.registration import get_addon, get_path 
from .. utils.ui import force_ui_update, popup_message
from .. utils.view import ensure_visibility, get_view_bbox
from .. items import create_assembly_asset_empty_location_items, create_assembly_asset_empty_collection_items, asset_browser_bookmark_props
from .. colors import white, yellow, blue

decalmachine = None
meshmachine = None

class CreateAssemblyAsset(bpy.types.Operator):
    bl_idname = "machin3.create_assembly_asset"
    bl_label = "MACHIN3: Create Assembly Asset"
    bl_description = "Create Assembly Asset from the selected Objects"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Asset Name", default="AssemblyAsset")
    move: BoolProperty(name="Move instead of Copy", description="Move Objects into Asset Collection, instead of copying\nThis will unlink them from any existing collections", default=False)
    location: EnumProperty(name="Empty Location", items=create_assembly_asset_empty_location_items, description="Location of Asset's Empty", default='AVGFLOOR')
    emptycol: EnumProperty(name="Empty Collection", items=create_assembly_asset_empty_collection_items, description="Collections to put the the Asset's Empty in", default='OBJCOLS')
    render_thumbnail: BoolProperty(name="Render Thumbnail", default=True)
    thumbnail_lens: FloatProperty(name="Thumbnail Lens", default=100)
    toggle_overlays: BoolProperty(name="Toggle Overlays", default=True)

    avoid_update: BoolProperty()

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return context.mode == 'OBJECT' and context.selected_objects

    def draw(self, context):
        global decalmachine, meshmachine

        layout = self.layout

        box = layout.box()
        box.label(text="Asset Info")
        column = box.column(align=True)

        column.prop(self, 'name')
        column.prop(context.window_manager, 'M3_asset_catalogs', text='Catalog')

        box = layout.box()
        box.label(text="Asset Empty")
        column = box.column(align=True)

        split = column.split(factor=0.2, align=True)
        row = split.row(align=True)
        row.active = False
        row.alignment = 'RIGHT'
        row.label(text="Position")
        row = split.row(align=True)
        row.prop(self, 'location', expand=True)

        split = column.split(factor=0.2, align=True)
        row = split.row(align=True)
        row.alignment = 'RIGHT'
        row.active = False
        row.label(text="Add to")
        row = split.row(align=True)
        row.prop(self, 'emptycol', expand=True)

    def invoke(self, context, event):
        global decalmachine, meshmachine

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        update_asset_catalogs(self, context)

        return context.window_manager.invoke_props_dialog(self, width=400)

    def execute(self, context):
        global decalmachine, meshmachine

        name = self.name.strip()

        if name:
            print(f"INFO: Creation Assembly Asset: {name}")

            objects = self.get_assembly_asset_objects(context)

            loc = self.get_empty_location(context, objects)

            duplicates = duplicate_objects(context, objects)

            for obj in duplicates:
                obj.M3.hide = not obj.visible_get()

            if decalmachine:
                self.delete_decal_backups(duplicates)
            
            if meshmachine:
                self.delete_stashes(duplicates)

            empty = self.create_asset_instance_collection(context, name, duplicates, loc)

            self.switch_asset_browser_to_LOCAL(context, empty)

            asset_bbox = self.get_asset_bbox(duplicates)

            if True:
                self.create_asset_thumbnail(context, empty, asset_bbox)

            return {'FINISHED'}

            render_width = context.scene.render.resolution_x
            render_height = context.scene.render.resolution_y

            context.scene.render.resolution_x = width
            context.scene.render.resolution_y = height

            print()
            print(" width:", width)
            print("height:", height)
            print("  crop:", [tuple(co) for co in render_bbox])

            bpy.ops.render.opengl()

            thumb = bpy.data.images.get('Render Result')
            print(thumb)

            if thumb:
                filepath = os.path.join(get_path(), 'resources', 'render.png')
                thumb.save_render(filepath=filepath)

                thumb = bpy.data.images.load(filepath=filepath)

                pixels = np.array(thumb.pixels[:])

                pixels = pixels.reshape((height, width, 4))

                left = int(render_bbox[0].x)
                right = int(render_bbox[1].x)
                top = int(render_bbox[1].y)
                bottom = int(render_bbox[2].y)

                cropped_pixels = pixels[top:bottom, left:right, :]

                cropped_width = right - left
                cropped_height = bottom - top

                cropped = bpy.data.images.new("Cropped Image", width=cropped_width, height=cropped_height)

                cropped.pixels[:] = cropped_pixels.flatten()         # see CodeMaX below, the difference here is minor though, but extreme for the image_pixels_float

                cropped.scale(256, 256)

                empty.preview_ensure()
                empty.preview.image_size = cropped.size
                empty.preview.image_pixels_float[:] = cropped.pixels  # CodeManX is a legend, see https://blender.stackexchange.com/a/3678/33919

                os.unlink(filepath)
                bpy.data.images.remove(thumb, do_unlink=True)
                bpy.data.images.remove(cropped, do_unlink=True)

            return {'FINISHED'}

            if self.render_thumbnail:
                thumbpath = os.path.join(get_path(), 'resources', 'thumb.png')
                self.render_thumbnail(context, thumbpath)

                thumb = bpy.data.images.load(filepath=thumbpath)

                instance.preview_ensure()
                instance.preview.image_size = thumb.size
                instance.preview.image_pixels_float[:] = thumb.pixels  # CodeManX is a legend

                bpy.data.images.remove(thumb)
                bpy.data.images.remove(bpy.data.images['Render Result'])
                os.unlink(thumbpath)

            return {'FINISHED'}

        else:
            popup_message("The chosen asset name can't be empty", title="Illegal Name")

            return {'CANCELLED'}

    def get_assembly_asset_objects(self, context):
        objects = set()

        for obj in context.selected_objects:
            tops = get_parent(obj, recursive=True, debug=True)
            top = tops[-1] if tops else obj

            obj_tree = [top]
            get_object_tree(top, obj_tree, mod_objects=True, find_disabled_mods=False, check_if_on_viewlayer=True)

            objects.update(obj_tree)

        return objects

    def get_empty_location(self, context, objects):
        rootobjs = [obj for obj in objects if not obj.parent]

        if self.location in ['AVG', 'AVGFLOOR']:
            loc = average_locations([obj.matrix_world.decompose()[0] for obj in rootobjs])

            if self.location == 'AVGFLOOR':
                loc[2] = 0

        else:
            loc = Vector((0, 0, 0))

        return loc

    def delete_decal_backups(self, objects):
        decals_with_backups = [obj for obj in objects if obj.DM.isdecal and obj.DM.decalbackup]

        for decal in decals_with_backups:
            if decal.DM.decalbackup:
                decal.DM.decalbackup = None

    def delete_stashes(self, objects):
        objs_with_stashes = [obj for obj in objects if obj.MM.stashes]

        for obj in objs_with_stashes:
            obj.MM.stashes.clear()

    def create_asset_instance_collection(self, context, name, objects, loc):
        master_col = context.scene.collection

        main_asset_col = bpy.data.collections.get('_Assets')

        if not main_asset_col:
            main_asset_col = bpy.data.collections.new(f"_Assets")

        if main_asset_col.name not in master_col.children:
            master_col.children.link(main_asset_col)

            context.view_layer.layer_collection.children[main_asset_col.name].hide_viewport = True

        asset_col = bpy.data.collections.new(f"_{name}")
        asset_col.M3.is_asset_collection = True

        main_asset_col.children.link(asset_col)

        object_cols = {col for obj in objects for col in obj.users_collection}

        for obj in objects:
            for col in obj.users_collection:
                if col in object_cols:
                    col.objects.unlink(obj)

        for obj in objects:
            asset_col.objects.link(obj)

            if obj.display_type in ['WIRE', 'BOUNDS'] or (obj.type == 'EMPTY' and not obj.instance_collection):
                obj.hide_set(True)

                obj.hide_viewport = True

        empty = bpy.data.objects.new(name, object_data=None)
        empty.instance_collection = asset_col
        empty.instance_type = 'COLLECTION'

        empty.location = loc

        empty.M3.asset_version = "1.1"

        if self.emptycol == 'SCENECOL':
            master_col.objects.link(empty)

        else:
            for col in object_cols:
                col.objects.link(empty)

        asset_col.instance_offset = loc

        empty.asset_mark()

        catalog = context.window_manager.M3_asset_catalogs

        if catalog and catalog != 'NONE':
            for uuid, catalog_data in self.catalogs.items():
                if catalog == catalog_data['catalog']:
                    empty.asset_data.catalog_id = uuid

        bpy.ops.object.select_all(action='DESELECT')
        empty.select_set(True)
        context.view_layer.objects.active = empty

        return empty

    def switch_asset_browser_to_LOCAL(self, context, asset):
        asset_browsers = [area for screen in context.workspace.screens for area in screen.areas if area.type == 'FILE_BROWSER' and area.ui_type == 'ASSETS']

        if len(asset_browsers) == 1:
            for space in asset_browsers[0].spaces:
                if space.type == 'FILE_BROWSER':
                    if get_asset_library_reference(space.params) != 'LOCAL':
                        set_asset_library_reference(space.params, 'LOCAL')

                    space.show_region_toolbar = True
                    space.show_region_tool_props = True

                    space.activate_asset_by_id(asset, deferred=True)

    def get_asset_bbox(self, objects, debug=False):

        coords = []

        for obj in objects:
            if not obj.type == 'EMPTY' and obj.display_type not in ['WIRE', 'BOUNDS'] and not obj.M3.hide:
                coords.extend([obj.matrix_world @ co for co in get_eval_bbox(obj)])
        
        if debug:
            draw_points(coords, color=blue, modal=False)

        bbox = create_coords_bbox(coords)[0]

        return bbox

    def create_asset_thumbnail(self, context, empty, bbox):
        def get_square_view_bbox(debug=False):
            render_bbox = get_view_bbox(context, bbox, margin=20, border_gap=0, debug=False)

            if debug:
                print("render bbox:", render_bbox)

            render_bbox_width = (render_bbox[1] - render_bbox[0]).length
            render_bbox_height = (render_bbox[2] - render_bbox[1]).length

            if debug:
                print("  bbox width:", render_bbox_width)
                print(" bbox height:", render_bbox_height)

            width = context.region.width
            height = context.region.height

            if render_bbox_width > render_bbox_height:
                delta = (render_bbox_width - render_bbox_height) / 2

                xmin = render_bbox[0].x
                xmax = render_bbox[1].x

                ymin = max(min(render_bbox[1].y - delta, height), 0)
                ymax = max(min(render_bbox[2].y + delta, height), 0)

                square_bbox = [Vector((xmin, ymin)), Vector((xmax, ymin)), Vector((xmax, ymax)), Vector((xmin, ymax))]

            elif render_bbox_width < render_bbox_height:
                delta = (render_bbox_height - render_bbox_width) / 2

                xmin = max(min(render_bbox[0].x - delta, width), 0)
                xmax = max(min(render_bbox[1].x + delta, width), 0)

                ymin = render_bbox[1].y
                ymax = render_bbox[2].y

                square_bbox = [Vector((xmin, ymin)), Vector((xmax, ymin)), Vector((xmax, ymax)), Vector((xmin, ymax))]

            else:
                square_bbox = render_bbox

            square_bbox_width = (square_bbox[1] - square_bbox[0]).length
            square_bbox_height = (square_bbox[2] - square_bbox[1]).length
            
            if debug:
                print("square bbox:", square_bbox)
                print(" square bbox width:", square_bbox_width)
                print("square bbox height:", square_bbox_height)

        square_bbox = get_square_view_bbox()

    def render_thumbnail(self, context, filepath):
        resolution = (context.scene.render.resolution_x, context.scene.render.resolution_y)
        file_format = context.scene.render.image_settings.file_format
        lens = context.space_data.lens
        show_overlays = context.space_data.overlay.show_overlays

        context.scene.render.resolution_x = 128
        context.scene.render.resolution_y = 128
        context.scene.render.image_settings.file_format = 'JPEG'

        context.space_data.lens = self.thumbnail_lens

        if show_overlays and self.toggle_overlays:
            context.space_data.overlay.show_overlays = False

        bpy.ops.render.opengl()

        thumb = bpy.data.images.get('Render Result')

        if thumb:
            thumb.save_render(filepath=filepath)

        context.scene.render.resolution_x = resolution[0]
        context.scene.render.resolution_y = resolution[1]
        context.space_data.lens = lens

        context.scene.render.image_settings.file_format = file_format

        if show_overlays and self.toggle_overlays:
            context.space_data.overlay.show_overlays = True

class RemoveAssemblyAsset(bpy.types.Operator):
    bl_idname = "machin3.remove_assembly_asset"
    bl_label = "MACHIN3: Remove Assembly Asset"
    bl_description = "description"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.selected_objects if obj.type == 'EMPTY' and obj.instance_collection and obj.instance_type == 'COLLECTION']

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

    def execute(self, context):
        draw_legacy_message = False

        assemblies = [obj for obj in context.selected_objects if obj.type == 'EMPTY' and obj.instance_collection and obj.instance_type == 'COLLECTION']

        asset_cols = set(obj.instance_collection for obj in assemblies)

        legacy_offset_map = {}

        for obj in assemblies:
            if not obj.instance_collection.M3.is_asset_collection:
                legacy_offset_map[obj.instance_collection] = obj.matrix_world.copy()

        for obj in assemblies:
            bpy.data.objects.remove(obj, do_unlink=True)

        for col in asset_cols:
            if not col.users_dupli_group:

                if col.M3.is_asset_collection:
                    for obj in col.objects:
                        remove_obj(obj)

                else:
                    ensure_visibility(context, list(col.objects), select=True)

                    for obj in col.objects:
                        if not obj.parent:
                            obj.matrix_world = legacy_offset_map[col] @ obj.matrix_world

                    draw_legacy_message = True

                bpy.data.collections.remove(col, do_unlink=True)

        main_asset_col = bpy.data.collections.get('_Assets')

        if main_asset_col and not (main_asset_col.children or main_asset_col.objects):
            bpy.data.collections.remove(main_asset_col, do_unlink=True)

        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

        if draw_legacy_message:
            draw_fading_label(context, text=["Legacy Asset Objects have been disassembled, but not removed automatically!", "This is because MACHIN3tools can't be sure they aren't the original objects", "Please remove manually, if desired"], color=[yellow, white], move_y=60, time=6)

        return {'FINISHED'}

class DisassembleAsset(bpy.types.Operator):
    bl_idname = "machin3.disassemble_asset"
    bl_label = "MACHIN3: Disassemble Asset"
    bl_description = "Make Instance Collection objects accessible"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.selected_objects if obj.type == 'EMPTY' and obj.instance_collection and obj.instance_type == 'COLLECTION']

    def execute(self, context):
        assemblies = [obj for obj in context.selected_objects if obj.type == 'EMPTY' and obj.instance_collection and obj.instance_type == 'COLLECTION']

        self.ensure_local_assemblies(assemblies)

        for obj in assemblies:
            self.disassemble_asset(context, obj)

        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
        return {'FINISHED'}

    def ensure_local_assemblies(self, assemblies):
        linked = [(obj, 'ASSET EMPTY') for obj in assemblies if obj.library]

        for obj in assemblies:
            if obj.library:
                linked.append((obj.instance_collection, 'ASSET COLLECTION'))

            for ob in obj.instance_collection.objects:
                if ob.library:
                    linked.append((ob, 'ASSEMBLY ASSET OBJECT'))

                if ob.data and ob.data.library:
                    linked.append((ob.data, 'ASSEMBLY ASSET DATA'))

        for id, idtype in linked:
            print(f"INFO: Making {idtype} {id.name} of library {id.library.name} at {id.library.filepath} LOCAL")
            id.make_local()

    def disassemble_asset(self, context, obj): 
        master_col = context.scene.collection

        mx = obj.matrix_world.copy()
        cols = [col for col in obj.users_collection]
        
        asset_col = obj.instance_collection
        asset_objects = [obj for obj in asset_col.objects]

        bpy.data.objects.remove(obj, do_unlink=True)

        for obj in asset_objects:
            if obj.name not in master_col.objects:     # just a pre-caution, should never be needed
                master_col.objects.link(obj)

        if asset_col.users_dupli_group:
            objects = duplicate_objects(context, asset_objects)

            for obj in asset_objects:
                master_col.objects.unlink(obj)

        else:
            objects = asset_objects

        if master_col not in cols:
            for obj in objects:
                master_col.objects.unlink(obj)

        for obj in objects:
            for col in cols:

                if col == master_col:
                    continue

                col.objects.link(obj)

        ensure_visibility(context, objects, view_layer=False, local_view=False, unhide=False, unhide_viewport=True, select=False)

        for obj in objects:
            obj.hide_set(obj.M3.hide)

        for obj in objects:
            if not obj.parent:
                offsetmx = get_loc_matrix(asset_col.instance_offset)
                obj.matrix_world = mx @ offsetmx.inverted_safe() @ obj.matrix_world

        if any(obj.rigid_body for obj in objects):
            if not context.scene.rigidbody_world:
                bpy.ops.rigidbody.world_add()

            for obj in objects:
                if obj.rigid_body:

                    with context.temp_override(object=obj):
                        bpy.ops.rigidbody.object_add(type=obj.rigid_body.type)

            bpy.ops.ptcache.bake_all(bake=True)

class MakeAssetLocal(bpy.types.Operator):
    bl_idname = "machin3.make_asset_local"
    bl_label = "MACHIN3: Make Asset Local"
    bl_description = "Make Linked Asset Local"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.selected_objects if obj.type == 'EMPTY' and obj.instance_collection and obj.instance_type == 'COLLECTION' and obj.library]

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

    def execute(self, context):
        linked_assemblies = [obj for obj in context.selected_objects if obj.type == 'EMPTY' and obj.instance_collection and obj.instance_type == 'COLLECTION' and obj.library]

        DisassembleAsset.ensure_local_assemblies(self, linked_assemblies)
        return {'FINISHED'}

class AssetBrowserBookmark(bpy.types.Operator):
    bl_idname = "machin3.assetbrowser_bookmark"
    bl_label = "MACHIN3: Assetbrowser Bookmark"
    bl_description = "description"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index", default=1, min=1, max=10)
    save_bookmark: BoolProperty(name="Save Bookmark", default=False)
    clear_bookmark: BoolProperty(name="Clear Bookmark", default=False)
    @classmethod
    def poll(cls, context):
        if context.area:
            return context.area.type == 'FILE_BROWSER' and context.area.ui_type == 'ASSETS'

    @classmethod
    def description(cls, context, properties):
        idx = str(properties.index)

        desc = f"Bookmark: {idx}"

        bookmarks = get_assetbrowser_bookmarks(force=True)
        bookmark = bookmarks[idx]

        libref, _, catalog = get_libref_and_catalog(context, bookmark=bookmark)

        if catalog:
            if libref == 'ALL':
                desc += f"\n Library: ALL ({libref})"
            else:
                desc += f"\n Library: {libref}"

            desc += f"\n Catalog: {catalog['catalog']}"

        elif libref:
            desc += f"\n Library: {libref}"

        else:
            desc += "\nNone"

        if catalog:
            desc += "\n\nClick: Jump to this Bookmark's Library and Catalog"
        else:
            desc += "\n"

        desc += "\nSHIFT: Save the current Library and Catalog on this Bookmark"

        if catalog:
            desc += "\nCTRL: Remove the stored Bookmark"

        return desc

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)

    def invoke(self, context, event):
        self.save_bookmark = event.shift
        self.clear_bookmark = event.ctrl

        space = context.space_data
        catalogs = get_catalogs_from_asset_libraries(context, debug=False)
        bookmarks = get_assetbrowser_bookmarks(force=True)

        if self.save_bookmark:
            libref = get_asset_library_reference(space.params)
            catalog_id = space.params.catalog_id
            display_size = space.params.display_size
            display_type = space.params.display_type

            if catalog_id in catalogs:
                bookmark = {'libref': libref,
                            'catalog_id': catalog_id,
                            'display_size': display_size,
                            'display_type': display_type,
                            'valid': True}

                bookmarks[str(self.index)] = bookmark

                set_assetbrowser_bookmarks(bookmarks)

                if getattr(context.window_manager, 'M3_screen_cast', False):
                    force_ui_update(context)

            else:

                print("  WARNING: no catalog found under this id! Reload the blend file? Restart Blender?")
                return {'CANCELLED'}

        elif self.clear_bookmark:
            bookmark = bookmarks.get(str(self.index), None)
            
            if bookmark:

                bookmarks[str(self.index)] = {key: None for key in asset_browser_bookmark_props}
                
                set_assetbrowser_bookmarks(bookmarks)

                if getattr(context.window_manager, 'M3_screen_cast', False):
                    force_ui_update(context)

            else:
                print(f" WARNING: no bookmark found for {self.index}. This should not happen! Reload the blend file.")
                return {'CANCELLED'}

        else:
            bookmark = bookmarks.get(str(self.index), None)

            if bookmark:
                libref = bookmark.get('libref', None)
                catalog_id = bookmark.get('catalog_id', None)
                display_size = bookmark.get('display_size', None)
                display_type = bookmark.get('display_type', None)
                valid = bookmark.get('valid', None)

                if libref and catalog_id:

                    if validate_libref_and_catalog(context, libref, catalog_id):
                        params = space.params

                        set_asset_library_reference(params, libref)
                        params.catalog_id = catalog_id
                        params.display_size = display_size
                        params.display_type = display_type

                        if not valid:
                            bookmark['valid'] = True

                            set_assetbrowser_bookmarks(bookmarks)

                    else:
                        bookmark['valid'] = False

                        set_assetbrowser_bookmarks(bookmarks)

            else:
                print(f" WARNING: no bookmark found for {self.index}. This should not happen! Reload the blend file.")
                return {'CANCELLED'}

        return {'FINISHED'}
