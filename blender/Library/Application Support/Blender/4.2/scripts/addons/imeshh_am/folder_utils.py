import os
import bpy
from dataclasses import dataclass
from typing import List, Tuple

EXT = {
    "HDRI" : ('.hdr', '.hdri', '.exr'), 
    "OBJECT" : (".blend",), 
    "MATERIAL" : (".blend",)}
@dataclass
class Asset:
    file_path: str = ""
    img_path: str = ""


def without_ext(file: str) -> str:
    return ".".join(file.split(".")[0:-1])


def get_dir_content(parent_dir: str) -> Tuple[List[str], List[str]]:
    """Return directories and asset contained in parent_dir.

    Return : ( directories ([str]), files ([str]))
    """
    dirs = []
    files = []
    for element in os.listdir(parent_dir):
        element_fullpath = os.path.join(parent_dir, element)
        if os.path.isdir(element_fullpath):
            dirs.append(element_fullpath)
        else:
            files.append(element_fullpath)
    return (dirs, files)

def make_asset_from_afolder(dir_path, files, context):
    if files:
        curr_tab = context.scene.imeshh_am.tabs
        if curr_tab in ["OBJECT", "MATERIAL"]: # hdri do not need mapping
            assets=[]
            img_paths = []
            blend_paths = []
            for f in files:
                if f.lower().endswith((".png", ".jpg")):
                    img_paths.append(os.path.join(dir_path, f)) 
                elif f.lower().endswith(EXT[curr_tab]):
                    blend_paths.append(os.path.join(dir_path, f))
            for blend_path in blend_paths:
                if img_paths:
                    # Map 1st image of the stack
                    img_path = img_paths.pop(0)
                else:
                    # Image can be generated from blend file
                    img_path = blend_path 
                assets.append(Asset(file_path=blend_path, img_path=img_path))
            return assets
    return None
                

def make_assets_from_files(parent_dir, files: List[str], context):
    """Make an asset with blend an image with the same name."""

    assets = []
    curr_tab = context.scene.imeshh_am.tabs
    if files:
        if curr_tab in ["OBJECT", "MATERIAL"]:
            blend_files = []
            #TODO Not compatible with list,
            #need to change if multiple ext for material or object 
            ext_not_dot = EXT[curr_tab][0].replace(".", "")
            # gather all blend files
            for f in files:
                if f.lower().endswith(EXT[curr_tab]):
                    blend_files.append(without_ext(f))
            # remove them from original list
            for b_file in blend_files:
                files.remove(".".join([b_file, ext_not_dot]))

            # create Asset with blend and images with same name
            for f in files:
                no_ext_f = without_ext(f)
                if f.lower().endswith((".png", ".jpg")) and no_ext_f in blend_files:
                    blend_files.remove(no_ext_f)
                    assets.append(
                        Asset(
                            file_path=os.path.join(
                                parent_dir,
                                (".".join([no_ext_f, ext_not_dot])),
                            ),
                            img_path=os.path.join(parent_dir, f),
                        )
                    )

            # create Asset with no matched blend file
            for b_file in blend_files:
                f_path = os.path.join(parent_dir, (".".join([b_file, ext_not_dot])))
                assets.append(
                    Asset(
                        file_path=f_path,img_path=f_path
                    )
                )
        elif curr_tab == "HDRI":            
             for f in files:
                if f.lower().endswith(EXT[curr_tab]):
                    full_path = os.path.join(parent_dir, f)
                    assets.append(Asset(file_path=full_path, img_path=full_path))
    return assets

def get_dir_assets(dir, files, context):
    "Return assets contained in files depending on dirtype."
    assets = []
    if is_asset_dir(dir, context):
        assets = make_asset_from_afolder(dir, files, context)
    else:
        assets = make_assets_from_files(dir, files, context)
    return assets

def get_all_sub_assets(parent_dir: str, context) -> List[str]:
    """Return all find below parent_dir in the file hierarchy.

    Return : files ([str])"""
    all_assets = []
    dirs_to_explore = [parent_dir]
    while dirs_to_explore:
        temp_explore_list = dirs_to_explore.copy()
        for dir in temp_explore_list:
            dirs, files = get_dir_content(dir)
            assets = get_dir_assets(dir, files, context)
            if assets:
                all_assets.extend(assets)
            dirs_to_explore.remove(dir)
            dirs_to_explore.extend(dirs)

    return all_assets

def load_preview(img_path: str, pcoll):
    """Load preview if needed and return it id."""
    if img_path in pcoll:
        return pcoll[img_path].icon_id
    else:
        img_type = "IMAGE"
        if img_path.endswith(".blend"):
            img_type = "BLEND"
        thumb = pcoll.load(img_path, img_path, img_type)
        return thumb.icon_id
    

    
def contains_blend(file_list):
    for f in file_list:
        if f.lower().endswith(".blend"):
            return True
    return False

def contains_filetype(file_list, ext : str) -> bool:
    for f in file_list:
        if f.lower().endswith(ext):
            return True
    return False

def is_asset_dir(directory, context):
    """Check if curr dir contain searched files (blend/hdr) and subdir not contain anyone
    and do not have more subfolder."""
    
    dirs, files = get_dir_content(directory)
    curr_tab = context.scene.imeshh_am.tabs
    #check that directory got at least one searched file
    if not contains_filetype(files, EXT[curr_tab]):
        return False
    if curr_tab in ["OBJECT", "MATERIAL"]:
        #check subdirs don't have searched files
        for dir in dirs:
            l_dirs, l_file = get_dir_content(dir)
            if contains_filetype(l_file, EXT[curr_tab]) or l_dirs:
                return False
    elif curr_tab == "HDRI":
       return False
    return True


def get_subdirs_as_items(cls, context):
    items = [('All', 'All', 'All', 'NONE', 0)]
    if os.path.exists(cls.start_folder):
        curr_dir = cls.start_folder
        dirs, files = get_dir_content(curr_dir)
        for idx, dir_path in enumerate(dirs):
            #if not is_asset_dir(dir_path, context):
            name = dir_path.split(os.sep)[-1]
            items.append((dir_path, name, dir_path, 'NONE', idx + 1))
    return items

def get_tab_main_dirs(cls, context):
    """Return as enum items all main directories of the current tab.
    
    (identifier, name, description, icon, number)
    Return : [('path', 'name', path, 'NONE', idx), ...]"""
    dir_items = []
    for dir in context.preferences.addons["imeshh_am"].preferences.paths:
        abs_path = bpy.path.abspath(dir.path)
        if dir.type_dir == context.scene.imeshh_am.tabs:
            dir_items.append((abs_path, dir.name, dir.path, 'NONE', len(dir_items)))
    return dir_items

