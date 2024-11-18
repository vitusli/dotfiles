import bpy
import bmesh
from typing import Union
from mathutils import Matrix, Vector
from uuid import uuid4
from math import radians
from . math import average_locations, flatten_matrix, get_sca_matrix
from . modifier import get_mod_obj, is_mod_obj
from . mesh import get_bbox
from . workspace import get_3dview_space
from . registration import get_prefs

def remove_obj(obj):
    if not obj.data:
        bpy.data.objects.remove(obj, do_unlink=True)

    elif obj.data.users > 1:
        bpy.data.objects.remove(obj, do_unlink=True)

    elif obj.type == 'MESH':
        bpy.data.meshes.remove(obj.data, do_unlink=True)

    else:
        bpy.data.objects.remove(obj, do_unlink=True)

def is_removable(obj, ignore_users=[], mods=True, children=True, debug=False):
    if debug:
        print(f"\nchecking if object {obj.name} can/should be removed")

    if children:
        if obj.children:
            if debug:
                print(f" object has {len(obj.children)} children, and so can't be removed")
            return False

    if mods:
        for ob in bpy.data.objects:
            for mod in ob.modifiers:

                if mod in ignore_users:
                    if debug:
                        print(f" ignoring {mod.name} as a potential user")
                    continue

                if get_mod_obj(mod) == obj:
                    if debug:
                        print(f" object is used by mod '{mod.name}' of '{mod.id_data.name}', and so can't be removed")
                    return False

    if debug:
        print(" object does not seem to be used, and so can be removed")
    return True

def flatten(obj, depsgraph=None, preserve_data_layers=False, keep_mods=[]):
    if not depsgraph:
        depsgraph = bpy.context.evaluated_depsgraph_get()

    oldmesh = obj.data

    if preserve_data_layers:
        obj.data = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph)
    else:
        obj.data = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))

    if keep_mods:
        for mod in obj.modifiers:
            if mod not in keep_mods:
                obj.modifiers.remove(mod)

    else:
        obj.modifiers.clear()

    if not oldmesh.users:
        bpy.data.meshes.remove(oldmesh, do_unlink=True)

def compensate_children(obj, oldmx, newmx):
    deltamx = newmx.inverted_safe() @ oldmx
    children = [c for c in obj.children]

    for c in children:
        pmx = c.matrix_parent_inverse
        c.matrix_parent_inverse = deltamx @ pmx

def set_obj_origin(obj, mx, bm=None, decalmachine=False, meshmachine=False, force_quat_mode=False):

    if force_quat_mode:
        obj.rotation_mode = 'QUATERNION'

    omx = obj.matrix_world.copy()

    children = [c for c in obj.children]
    compensate_children(obj, omx, mx)

    deltamx = mx.inverted_safe() @ obj.matrix_world

    obj.matrix_world = mx

    if bm:
        bmesh.ops.transform(bm, verts=bm.verts, matrix=deltamx)
        bmesh.update_edit_mesh(obj.data)
    else:
        obj.data.transform(deltamx)

    if obj.type == 'MESH':
        obj.data.update()

    if decalmachine and children:

        for c in [c for c in children if c.DM.isdecal and c.DM.decalbackup]:
            backup = c.DM.decalbackup
            backup.DM.backupmx = flatten_matrix(deltamx @ backup.DM.backupmx)

    if meshmachine:

        for stash in obj.MM.stashes:

            if stash.obj:

                if getattr(stash, 'version', False) and float('.'.join([v for v in stash.version.split('.')[:2]])) >= 0.7:
                    stashdeltamx = stash.obj.MM.stashdeltamx

                    if stash.self_stash:
                        if stash.obj.users > 2:
                            print(f"INFO: Duplicating {stash.name}'s stashobj {stash.obj.name} as it's used by multiple stashes")

                            dup = stash.obj.copy()
                            dup.data = stash.obj.data.copy()
                            stash.obj = dup

                    stash.obj.MM.stashdeltamx = flatten_matrix(deltamx @ stashdeltamx)
                    stash.obj.MM.stashorphanmx = flatten_matrix(mx)

                    stash.self_stash = False

                else:
                    stashdeltamx = stash.obj.MM.stashtargetmx.inverted_safe() @ stash.obj.MM.stashmx

                    stash.obj.MM.stashmx = flatten_matrix(omx @ stashdeltamx)
                    stash.obj.MM.stashtargetmx = flatten_matrix(mx)

                stash.obj.data.transform(deltamx)
                stash.obj.matrix_world = mx

def is_uniform_scale(obj):
    return all([round(s, 6) == round(obj.scale[0], 6) for s in obj.scale])

def get_eval_bbox(obj, advanced=False):
    bbox = [Vector(obj.bound_box[0]),
            Vector(obj.bound_box[4]),
            Vector(obj.bound_box[7]), 
            Vector(obj.bound_box[3]), 
            Vector(obj.bound_box[1]), 
            Vector(obj.bound_box[5]), 
            Vector(obj.bound_box[6]), 
            Vector(obj.bound_box[2])]
    
    if advanced:
        centers = [average_locations([bbox[0], bbox[3], bbox[4], bbox[7]]),
                   average_locations([bbox[1], bbox[2], bbox[5], bbox[6]]),
                   average_locations([bbox[0], bbox[1], bbox[4], bbox[5]]),
                   average_locations([bbox[2], bbox[3], bbox[6], bbox[7]]),
                   average_locations([bbox[0], bbox[1], bbox[2], bbox[3]]),
                   average_locations([bbox[4], bbox[5], bbox[6], bbox[7]])]

        return bbox, centers, obj.dimensions

    else:
        return bbox

def get_min_dim(obj, world_space=True):
    dims = [d for d in get_bbox(obj.data)[2] if d]

    if world_space:
        mx = obj.matrix_world
        scale_mx = get_sca_matrix(mx.decompose()[2])
        return min(scale_mx @ Vector(dims).resized(3))

    else:
        return min(dims)

def is_wire_object(obj, wire=True, bounds=True, empty=True, instance_collection=False, curve=True):
    if wire and obj.display_type == 'WIRE':
        return True

    elif bounds and obj.display_type == 'BOUNDS':
        return True

    elif empty and obj.type == 'EMPTY':

        if obj.instance_collection:
            return instance_collection

        else:
            return not obj.empty_display_type == 'IMAGE'

    elif curve and obj.type == 'CURVE' and obj.data.bevel_depth == 0 and obj.data.extrude == 0:
        return True

def is_valid_object(obj):
    return obj and not ' invalid>' in str(obj)

def enable_auto_smooth(obj, angle=20):
    if bpy.app.version >= (4, 1, 0):
        pass

    else:
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = radians(angle)

def parent(obj, parentobj):
    if obj.parent:
        unparent(obj)

    obj.parent = parentobj
    obj.matrix_parent_inverse = parentobj.matrix_world.inverted_safe()

def unparent(obj):
    if obj.parent:
        omx = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = omx

def get_object_tree(obj, obj_tree, mod_objects=True, mod_dict=None, mod_type_ignore=[], depth=0, find_disabled_mods=False, ensure_on_viewlayer=False, debug=False):

    if ensure_on_viewlayer:
        view_layer = bpy.context.view_layer

    depthstr = " " * depth

    if debug:
        print()
        print("depth:", depth, "tree:", [obj.name for obj in obj_tree])
        print(f"{depthstr}{obj.name}")

    for child in obj.children:
        if debug:
            print(f" {depthstr}child: {child.name}")

        if child not in obj_tree:
            if ensure_on_viewlayer and child.name not in view_layer.objects:
                if debug:
                    print(f"  {depthstr}! ignoring child '{child.name}' as it's not on the view layer")
                continue

            obj_tree.append(child)

            get_object_tree(child, obj_tree, mod_objects=mod_objects, mod_dict=mod_dict, mod_type_ignore=mod_type_ignore, depth=depth + 1, find_disabled_mods=find_disabled_mods, debug=debug)

    if mod_objects:
        for mod in obj.modifiers:

            if mod.type not in mod_type_ignore and (mod.show_viewport or find_disabled_mods):
                mod_obj = get_mod_obj(mod)

                if debug:
                    print(f" {depthstr}mod: {mod.name} | obj: {mod_obj.name if mod_obj else mod_obj}")

                if mod_obj:
                    if ensure_on_viewlayer and child.name not in view_layer.objects:
                        if debug:
                            print(f"  {depthstr}! ignoring mod object '{mod_obj.name}' as it's not on the view layer")
                        continue

                    if mod_dict is not None:
                        if mod_obj in mod_dict:
                            mod_dict[mod_obj].append(mod)
                        else:
                            mod_dict[mod_obj] = [mod]

                    if mod_obj not in obj_tree:
                        obj_tree.append(mod_obj)

                        get_object_tree(mod_obj, obj_tree, mod_objects=mod_objects, mod_dict=mod_dict, mod_type_ignore=mod_type_ignore, depth=depth + 1, find_disabled_mods=find_disabled_mods, debug=debug)

def duplicate_obj_recursively(context, obj, keep_selection=False):
    sel = [obj for obj in context.selected_objects]
    active = context.active_object
    view = get_3dview_space(context)

    if view:
        bpy.ops.object.select_all(action='DESELECT')

        children = {str(uuid4()): (ob, ob.visible_get()) for ob in obj.children_recursive if ob.name in context.view_layer.objects}

        for dup_hash, (ob, vis) in children.items():
            ob.HC.dup_hash = dup_hash

            if view.local_view and not obj.local_view_get(view):
                ob.local_view_set(view, True)

            ob.hide_set(False)
            ob.select_set(True)

        context.view_layer.objects.active = obj
        obj.select_set(True)

        bpy.ops.object.duplicate(linked=False)

        obj_dup = context.active_object

        dup_children = [ob for ob in obj_dup.children_recursive if ob.name in context.view_layer.objects]

        for dup in dup_children:
            orig, vis = children[dup.HC.dup_hash]

            orig.hide_set(not vis)
            dup.hide_set(not vis)

            orig.HC.dup_hash = ''
            dup.HC.dup_hash = ''

        bpy.ops.object.select_all(action='DESELECT')

        if keep_selection:
            for ob in sel + [active]:
                ob.select_set(True)

            context.view_layer.objects.active = active

        else:
            obj_dup.select_set(True)
            context.view_layer.objects.active = obj_dup

        return obj_dup

def remove_unused_children(context, obj, depsgraph=None, debug=False):
    if debug:
        print("\nremoving unused children of", obj.name)

    if depsgraph:
        depsgraph.update()

    children = [ob for ob in obj.children_recursive if ob.name in context.view_layer.objects]
    removable = []

    for ob in children:
        if debug:
            print(ob.name)

        if ob.hide_render or is_wire_object(ob, curve=False):
            if debug:
                print("  is a candidate")

            mods = is_mod_obj(ob)

            if debug:
                print("    mods:", [(mod.name, "on", mod.id_data) for mod in mods])

            if not mods:
                removable.append(ob)

                if debug:
                    print("    not used by any, remove!")

        else:
            if debug:
                print("  should be kept")

    for ob in removable:
        for c in ob.children_recursive:
            if c not in removable:
                if debug:
                    print(" re-parenting", ob.name, "child object", c.name, "to obj")
                parent(c, obj)

    if removable:
        bpy.data.batch_remove(removable)

def hide_render(objects, state):
    if isinstance(objects, bpy.types.Object):
        objects = [objects]

    if isinstance(objects, list):
        ray_vis_hide = get_prefs().ray_vis_hide_cutters

        for obj in objects:
            obj.hide_render = state

            if ray_vis_hide:
                obj.visible_camera = not state
                obj.visible_diffuse = not state
                obj.visible_glossy = not state
                obj.visible_transmission = not state
                obj.visible_volume_scatter = not state
                obj.visible_shadow = not state

def get_active_object(context) -> Union[bpy.types.Object, None]:
    objects = getattr(context.view_layer, 'objects', None)

    if objects:
        return getattr(objects, 'active', None)

def get_selected_objects(context) -> list[bpy.types.Object]:
    objects = getattr(context.view_layer, 'objects', None)

    if objects:
        return getattr(objects, 'selected', [])

    return []

def get_visible_objects(context, local_view=False) -> list[bpy.types.Object]:
    view_layer = context.view_layer
    objects = getattr(view_layer, 'objects', [])

    return [obj for obj in objects if obj.visible_get(view_layer=view_layer)]
