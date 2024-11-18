import bpy
import os
from pprint import pprint
from shutil import rmtree
from . registration import get_prefs
from .. import bl_info

def splitpath(path):
    path = bpy.path.native_pathsep(os.path.normpath(path))
    return path.split(os.sep)

def remove_folder(path):
    if (exists := os.path.exists(path)) and (isfolder := os.path.isdir(path)):
        try:
            rmtree(path)
            return True

        except Exception as e:
            print(f"WARNING: Error while trying to remove {path}: {e}")

    elif exists:
        print(f"WARNING: Couldn't remove {path}, it's not a folder!")
    else:
        print(f"WARNING: Couldn't remove {path}, it doesn't exist!")

    return False

def printd(d, name='', indent=0):
    if name:
        print(f"\n{indent * ' '}{name}")

    print((indent + 1) * " ", end='')
    pprint(d, sort_dicts=False)
    print()

update_files = None

def get_update_files(force=False):
    global update_files

    if update_files is None or force:
        update_files = []

        home_dir = os.path.expanduser('~')

        if os.path.exists(home_dir):
            download_dir = os.path.join(home_dir, 'Downloads')

            home_files = [(f, os.path.join(home_dir, f)) for f in os.listdir(home_dir) if f.startswith(bl_info['name']) and f.endswith('.zip')]
            dl_files = [(f, os.path.join(download_dir, f)) for f in os.listdir(download_dir) if f.startswith(bl_info['name']) and f.endswith('.zip')] if os.path.exists(download_dir) else []

            zip_files = home_files + dl_files

            for filename, path in zip_files:
                split = filename.split('_')

                if len(split) == 2:
                    tail = split[1].replace('.zip', '')
                    s = tail.split('.')

                    if len(s) >= 3:
                        try:
                            version = tuple(int(v) for v in s[:3])

                        except:
                            continue

                        if tail == '.'.join(str(v) for v in bl_info['version']):
                            continue

                        update_files.append((path, tail, version))

        update_files = sorted(update_files, key=lambda x: (x[2], x[1]))

    return update_files

def get_bl_info_from_file(path):
    if os.path.exists(path):
        lines = ""
        
        with open(path) as f:
            for line in f:
                if line := line.strip():
                    lines += (line)
                else:
                    break

        try:
            blinfo = eval(lines.replace('bl_info = ', ''))

        except:
            print(f"WARNING: failed reading bl_info from {path}")
            return

        if 'name' in blinfo and 'version' in blinfo:
            name = blinfo['name']
            version = blinfo['version']

            if name == bl_info['name']:
                if version != bl_info['version']:
                    return blinfo

                else:
                    print(f"WARNING: Versions are identical, an update would be pointless")

            else:
                print(f"WARNING: Addon Mismatch, you can't update {bl_info['name']} to {name}")

    else:
        print(f"WARNING: failed reading bl_info from {path}, path does not exist")

def verify_update():
    path = get_prefs().path
    update_path = os.path.join(path, '_update')

    if os.path.exists(update_path):
        init_path = os.path.join(update_path, bl_info['name'], '__init__.py')

        blinfo = get_bl_info_from_file(init_path)

        if blinfo:
            get_prefs().update_msg = f"{blinfo['name']} {'.'.join(str(v) for v in blinfo['version'])} is ready to be installed."
            get_prefs().show_update = True

        else:
            remove_folder(update_path)

        return

    if get_prefs().show_update:
        get_prefs().show_update = False

    if get_prefs().update_msg:
        get_prefs().update_msg = ''

def install_update():
    path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    update_path = os.path.join(path, '_update')

    if os.path.exists(update_path):
        src = os.path.join(update_path, bl_info['name'])

        if os.path.exists(src):
            
            dst = os.path.join(os.path.dirname(path), f"_update_{bl_info['name']}")

            if os.path.exists(dst):
                remove_folder(dst)
            
            os.rename(src, dst)

            remove_folder(path)

            os.rename(dst, path)
