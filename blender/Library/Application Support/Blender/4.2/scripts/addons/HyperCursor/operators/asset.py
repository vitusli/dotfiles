import bpy
from bpy.props import EnumProperty, BoolProperty, StringProperty
import os
from bpy.types import FunctionNodeInputBool
from mathutils import Vector
from .. utils.ui import popup_message
from .. utils.asset import update_asset_catalogs, get_asset_details_from_space, get_asset_ids
from .. utils.object import hide_render
from .. utils.system import printd
from .. items import add_boolean_method_items, add_boolean_solver_items, boolean_display_type_items

class FetchAsset(bpy.types.Operator):
    bl_idname = "machin3.fetch_asset"
    bl_label = "MACHIN3: fetch_asset"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'FILE_BROWSER' and context.area.ui_type == 'ASSETS'

    def execute(self, context):
        debug = False

        active, id_type, local_id = get_asset_ids(context)

        if debug:
            print("active:", active)
            print("id_type:", id_type)
            print("local_id:", local_id)

        if active and active.id_type == 'OBJECT':

            if local_id:
                obj = local_id

                if debug:

                    print()
                    print("LOCAL (FetchAsset)", active.name)

                bpy.ops.object.select_all(action='DESELECT')

                asset = obj.copy()
                if asset.data:
                    asset.data = obj.data.copy()

                mcol = context.scene.collection

                mcol.objects.link(asset)

                context.view_layer.objects.active = asset
                asset.select_set(True)

                directory = os.path.join(bpy.data.filepath, 'Object')
                asset.HC.assetpath = os.path.join(directory, obj.name)

                asset.HC.libname = 'LOCAL'
                asset.HC.assetname = obj.name

            else:
                if debug:
                    print()
                    print("EXTERNAL (SetDropAssetProps)", active.name)

                libname, libpath, filename, import_method = get_asset_details_from_space(context, context.space_data, debug=debug)

                if libpath and filename:

                    path = filename.replace('\\', '/')

                    if debug:
                        print("  path:", path)

                    blendpath, objectname = path.split('/Object/')

                    if debug:
                        print("   blendpath:", blendpath)
                        print("   objectname:", objectname)

                    if os.path.exists(os.path.join(libpath, blendpath)):
                        directory = os.path.join(libpath, blendpath, 'Object')

                        if debug:
                            print("  directory:", directory)

                        bpy.ops.object.select_all(action='DESELECT')

                        bpy.ops.wm.append(directory=directory, filename=objectname, do_reuse_local_id=True if import_method == 'APPEND_REUSE' else False)

                        if context.selected_objects:
                            context.view_layer.objects.active = context.selected_objects[0]

                            asset = context.active_object
                            asset.HC.assetpath = os.path.join(directory, objectname)

                            if debug:
                                print()
                                print("HC.assetspath:", asset.HC.assetpath)

                            asset.HC.libname = libname
                            asset.HC.blendpath = blendpath.replace('.blend', '')
                            asset.HC.assetname = objectname

                            asset.asset_clear()

                            if import_method == 'APPEND_REUSE' and asset.type == 'EMPTY' and asset.instance_collection:
                                duplicates = sorted([obj for obj in bpy.data.objects if obj != asset and obj.type == 'EMPTY' and obj.instance_collection and obj.HC.assetpath == asset.HC.assetpath], key=lambda x: x.name)

                                if duplicates:

                                    if bpy.app.version < (3, 2, 0):
                                        orig = duplicates.pop(0)

                                        for obj in duplicates + [asset]:
                                            obj.instance_collection = orig.instance_collection

                                    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

                            return {'FINISHED'}

        return {'CANCELLED'}

class SetDropAssetProps(bpy.types.Operator):
    bl_idname = "machin3.set_drop_asset_props"
    bl_label = "MACHIN3: Set Drop Asset Props"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'FILE_BROWSER' and context.area.ui_type == 'ASSETS'

    def execute(self, context):
        debug = False

        active, id_type, local_id = get_asset_ids(context)

        if debug:
            print("active:", active)
            print("id_type:", id_type)
            print("local_id:", local_id)

        if active and active.id_type == 'OBJECT':
            asset = context.active_object

            if local_id:
                obj = local_id

                if debug:
                    print()
                    print("LOCAL (SetDropAssetProps)")
                    print("active:", active)
                    print("obj (active.local_id):", obj)
                    print("asset (context.active_object):", asset)

                directory = os.path.join(bpy.data.filepath, 'Object')
                asset.HC.assetpath = os.path.join(directory, obj.name)

                asset.HC.libname = 'LOCAL'
                asset.HC.assetname = obj.name

            else:
                if debug:
                    print()
                    print("EXTERNAL (SetDropAssetProps)")

                libname, libpath, filename, import_method = get_asset_details_from_space(context, context.space_data, debug=debug)

                if libpath and filename:

                    path = filename.replace('\\', '/')
                    
                    if debug:
                        print("path:", path)

                    blendpath, objectname = path.split('/Object/')

                    if debug:
                        print("blendpath", blendpath)
                        print("objectname:", objectname)

                    directory = os.path.join(libpath, blendpath, 'Object')
                    asset.HC.assetpath = os.path.join(directory, objectname)

                    if debug:
                        print("assetpath:", asset.HC.assetpath)

                    asset.HC.libname = libname
                    asset.HC.blendpath = blendpath.replace('.blend', '')
                    asset.HC.assetname = objectname

                    if import_method == 'APPEND_REUSE' and asset.type == 'EMPTY' and asset.instance_collection:
                        duplicates = sorted([obj for obj in bpy.data.objects if obj != asset and obj.type == 'EMPTY' and obj.instance_collection and obj.HC.assetpath == asset.HC.assetpath], key=lambda x: x.name)

                        if duplicates:

                            if bpy.app.version < (3, 2, 0):
                                orig = duplicates.pop(0)

                                for obj in duplicates + [asset]:
                                    obj.instance_collection = orig.instance_collection

                            bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

        return {'FINISHED'}

class CreateAsset(bpy.types.Operator):
    bl_idname = "machin3.create_asset"
    bl_label = "MACHIN3: Create Asset"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Asset Name", default="AssemblyAsset")
    isasset: BoolProperty(name="is Asset", description="Mark as Asset", default=True)
    ishyperasset: BoolProperty(name="is Hyper Asset", description="Let HyperCursor take over, when dropping this Asset into the 3D View from the Asset Browser", default=True)
    def isinset_update(self, context):
        if self.isinset and not self.autodisband:
            self.avoid_update = True
            self.autodisband = True

    isinset: BoolProperty(name="is Inset", description="Use Object for Boolean", update=isinset_update, default=False)
    insettype: EnumProperty(name="Inset Boolean Type", items=add_boolean_method_items, default="DIFFERENCE")
    insetsolver: EnumProperty(name="Inset Boolean Solver", items=add_boolean_solver_items, default="FAST")
    iscurve: BoolProperty(name="is Curve", description="Is Curve Object, used for Pipe Profiles", default=False)
    display_type: EnumProperty(name="Display Type", items=boolean_display_type_items, default='WIRE')
    def autodisband_update(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.autodisband is False and self.isinset:
            self.avoid_update = True
            self.autodisband = True

    autodisband: BoolProperty(name="Automatically Disband", description="Automatically Disband Collection Assets", update=autodisband_update, default=False)
    hasrootboolean: BoolProperty(name="has root object booleans", default=False)
    issecondaryboolean: BoolProperty(name="is Secondary Boolean", description="Transfer Booleans on Root Object to Parent", default=False)
    ischange: BoolProperty()
    avoid_update: BoolProperty()

    @classmethod
    def description(cls, context, properties):
        sel = context.selected_objects
        action = 'Change' if len(sel) == 1 and sel[0].asset_data and not sel[0].instance_collection else 'Create Collection' if len(sel) > 1 else 'Create'
        return f'{action} Asset\nALT: Initialize as Inset'

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            sel = context.selected_objects

            if any([obj.asset_data and obj.type == 'EMPTY' and obj.instance_type == 'COLLECTION' for obj in sel]):
                return False
            return sel

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)

        if len(self.sel) > 1:
            column.label(text="A Multi-Object Assembly Asset will be created.", icon="INFO")

            if self.hasrootboolean:
                column.label(text="Booleans on Root Object can be transfered to Parent Object.", icon="INFO")

            column.separator()

        if self.iscurve:
            column.prop(self, 'isasset', toggle=True)

        else:
            split = column.split(factor=0.5, align=True)
            row = split.row(align=True)
            s = row.split(factor=0.9, align=True)
            s.prop(self, 'isasset', toggle=True)

            s.prop(self, 'ishyperasset', text="", toggle=True, icon="ACTION_TWEAK")

            r = split.row(align=True)
            r.active = self.isasset
            r.prop(self, 'isinset', toggle=True)

        if len(self.sel) > 1 and self.isasset:
            row = column.row(align=True)
            row.prop(self, 'autodisband', toggle=True)

            if self.hasrootboolean:
                r = row.row(align=True)
                r.active = self.isinset
                r.prop(self, 'issecondaryboolean', toggle=True)

        if self.isasset:
            column = layout.column(align=True)

            row = column.split(factor=0.2, align=True)
            row.label(text='Name')
            row.prop(self, 'name', text='')

            row = column.split(factor=0.2, align=True)
            row.label(text='Catalog')
            row.prop(context.window_manager, 'HC_asset_catalogs', text='')

            if self.isinset:
                column.separator()

                row = column.split(factor=0.2, align=True)
                row.label(text='Type')
                r = row.row(align=True)
                r.prop(self, 'insettype', expand=True)

                row = column.split(factor=0.2, align=True)
                row.label(text='Solver')
                r = row.row(align=True)
                r.prop(self, 'insetsolver', expand=True)

                row = column.split(factor=0.2, align=True)
                row.label(text='Display Type')
                r = row.row(align=True)
                r.prop(self, 'display_type', expand=True)

    def invoke(self, context, event):

        self.sel = context.selected_objects
        obj = self.sel[0]

        if self.ischange:
            self.name = obj.name

            self.asset = True if obj.asset_data else False
            self.ishyperasset = obj.HC.ishyperasset
            self.isinset = obj.HC.isinset
            self.display_type = obj.display_type if obj.display_type in ['WIRE', 'BOUNDS'] else 'WIRE'

            if self.isinset:
                self.insettype = obj.HC.insettype
                self.insetsolver = obj.HC.insetsolver

            self.iscurve = self.sel[0].type == 'CURVE'

            update_asset_catalogs(self, context, curve=self.iscurve)
    
            if obj.asset_data:
                catalog_id = obj.asset_data.catalog_id

                for uuid, data in self.catalogs.items():
                    if uuid == catalog_id:
                        catalog = data['catalog']
                        context.window_manager.HC_asset_catalogs = catalog

        else:

            self.isasset = True
            self.ishyperasset = True
            self.hasrootboolean = False

            self.isinset = event.alt

            self.iscurve = obj.type == 'CURVE'

            update_asset_catalogs(self, context, curve=self.iscurve)

            if len(self.sel) == 1:
                self.name = obj.name

            else:
                self.rootobjs = [obj for obj in self.sel if not obj.parent]

                if not self.rootobjs or len(self.rootobjs) > 1:
                    popup_message(["For Multi-Object Assembly Assets, there should only be a single root object", "1. For insets this should be the boolean cutter", "2. Otherwise it could be an empty, perhaps a MACHIN3tools Group empty, but it doesn't have to be."])
                    return {'CANCELLED'}

                self.name = "Assembly Asset"

                booleans = [mod for mod in self.rootobjs[0].modifiers if mod.type == 'BOOLEAN' and mod.object and mod.show_viewport]

                if booleans:
                    self.hasrootboolean = True

        return context.window_manager.invoke_props_dialog(self, width=350)

    def execute(self, context):

        if len(self.sel) == 1:

            assettype = 'Curve' if self.iscurve else 'Object'
            print(f"INFO: {assettype} Asset")

            obj = self.sel[0]

            if self.isasset:
                print(f"INFO: marking {obj.name} as asset")
                obj.asset_mark()

                if not self.iscurve:

                    if not self.ischange:
                        obj.asset_generate_preview()

                    obj.HC.ishyperasset = self.ishyperasset
                    print(f" HyperAsset: {self.ishyperasset}")

                    print(f"      Inset: {self.isinset}")
                    obj.HC.isinset = self.isinset

                    if self.isinset:
                        obj.display_type = self.display_type

                        obj.HC.insettype = self.insettype
                        print(f"       Type: {self.insettype}")

                        obj.HC.insetsolver = self.insetsolver
                        print(f"     Solver: {self.insetsolver}")

                        hide_render(obj, True)
                    
                    else:
                        obj.HC.isinset = False
                        obj.display_type = 'TEXTURED'
                        hide_render(obj, False)

                self.assign_catalog_to_asset(context, obj)

                if self.name != obj.name:
                    obj.name = self.name

            else:
                print(f"INFO: un-marking {obj.name} as asset")
                obj.asset_clear()

                if not self.iscurve:
                    obj.HC.ishyperasset = False
                    obj.HC.isinset = False
                    obj.display_type = 'TEXTURED'
                    hide_render(obj, False)

        elif self.isasset:
            print("INFO: Collection Asset")
            root = self.rootobjs[0]
            location = root.location.copy()

            mcol = context.scene.collection
            acol = bpy.data.collections.new(self.name)

            mcol.children.link(acol)

            for obj in self.sel:
                for col in obj.users_collection:
                    col.objects.unlink(obj)

                acol.objects.link(obj)

            instance = bpy.data.objects.new(self.name, object_data=None)
            instance.instance_collection = acol
            instance.instance_type = 'COLLECTION'

            mcol.objects.link(instance)

            instance.location = location
            root.location = Vector((0, 0, 0))

            context.view_layer.layer_collection.children[acol.name].hide_viewport = True

            if self.isasset:
                print(f"INFO: marking {instance.name} as asset")
                instance.asset_mark()

                instance.HC.ishyperasset = self.ishyperasset

                instance.HC.autodisband = self.autodisband

                print(f"             Inset: {self.isinset}")
                root.HC.isinset = self.isinset
                root.display_type = self.display_type
                hide_render(root, True)

                if self.isinset:
                    root.HC.insettype = self.insettype
                    print(f"              Type: {self.insettype}")

                    root.HC.insetsolver = self.insetsolver
                    print(f"            Solver: {self.insetsolver}")

                    if self.hasrootboolean and self.issecondaryboolean:
                        print(f" Secondary Boolean: {self.issecondaryboolean}")
                        root.HC.issecondaryboolean = self.issecondaryboolean

                self.assign_catalog_to_asset(context, instance)

                instance.select_set(True)
                context.view_layer.objects.active = instance

            else:
                print(f"INFO: un-marking {instance.name} as asset")
                instance.asset_clear()

        return {'FINISHED'}

    def assign_catalog_to_asset(self, context, asset):
        catalog = context.window_manager.HC_asset_catalogs

        if catalog and catalog != 'NONE':
            print(f"INFO: assigning to catalog {catalog}")

            for uuid, catalog_data in self.catalogs.items():
                if catalog == catalog_data['catalog']:
                    asset.asset_data.catalog_id = uuid

class DisbandCollectionInstanceAsset(bpy.types.Operator):
    bl_idname = "machin3.disband_collection_instance_asset"
    bl_label = "MACHIN3: Disband Collection Instance Asset"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            sel = context.selected_objects
            return any([obj.asset_data and obj.type == 'EMPTY' and obj.instance_type == 'COLLECTION' for obj in sel])

    def execute(self, context):
        sel = context.selected_objects
        assets = [obj for obj in sel if obj.asset_data and obj.type == 'EMPTY' and obj.instance_type == 'COLLECTION']

        for instance in assets:

            acol = instance.instance_collection

            cols = [col for col in instance.users_collection]
            imx = instance.matrix_world

            children = [obj for obj in acol.objects]

            bpy.ops.object.select_all(action='DESELECT')

            for obj in children:
                for col in cols:
                    col.objects.link(obj)
                obj.select_set(True)

            if len(acol.users_dupli_group) > 1:

                bpy.ops.object.duplicate()

                for obj in children:
                    for col in cols:
                        col.objects.unlink(obj)

                children = [obj for obj in context.selected_objects]

                for obj in children:
                    if obj.name in acol.objects:
                        acol.objects.unlink(obj)

            root_children = [obj for obj in children if not obj.parent]

            for obj in root_children:
                obj.matrix_world = imx @ obj.matrix_world

                obj.select_set(True)
                context.view_layer.objects.active = obj

                obj.HC.isinset = False
                obj.display_type = 'TEXTURED'
                hide_render(obj, False)

            bpy.data.objects.remove(instance, do_unlink=True)

            if len(acol.users_dupli_group) == 0:
                bpy.data.collections.remove(acol, do_unlink=True)

        return {'FINISHED'}
