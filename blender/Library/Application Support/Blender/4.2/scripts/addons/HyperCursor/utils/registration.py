import bpy
from bpy.utils import register_class, unregister_class, register_tool, unregister_tool, previews
import os
from .. registration import keys as keysdict
from .. registration import classes as classesdict

def get_path():
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def get_name():
    try:
        return os.path.basename(get_path())
    except:
        return "HyperCursor"

def get_prefs():
    return bpy.context.preferences.addons[get_name()].preferences

def get_addon(addon, debug=False):
    import addon_utils

    for mod in addon_utils.modules():
        name = mod.bl_info["name"]
        version = mod.bl_info.get("version", None)
        foldername = mod.__name__
        path = mod.__file__
        enabled = addon_utils.check(foldername)[1]

        if name == addon:
            if debug:
                print(name)
                print("  enabled:", enabled)
                print("  folder name:", foldername)
                print("  version:", version)
                print("  path:", path)
                print()

            return enabled, foldername, version, path
    return False, None, None, None

def get_addon_prefs(addon):
    _, foldername, _, _ = get_addon(addon)
    return bpy.context.preferences.addons.get(foldername).preferences

def register_classes(classlists, debug=False):
    classes = []

    for classlist in classlists:
        for fr, imps in classlist:
            impline = "from ..%s import %s" % (fr, ", ".join([i[0] for i in imps]))
            classline = "classes.extend([%s])" % (", ".join([i[0] for i in imps]))

            exec(impline)
            exec(classline)

    for c in classes:
        if debug:
            print("REGISTERING", c)

        register_class(c)

    return classes

def unregister_classes(classes, debug=False):
    for c in classes:
        if debug:
            print("UN-REGISTERING", c)

        unregister_class(c)

def register_tools(toollists, debug=False):
    tool_classes = []

    for toollist in toollists:
        for fr, tools in toollist:
            impline = "from ..%s import %s" % (fr, ", ".join([t[0][0] for t in tools]))
            exec(impline)

            for tool in tools:
                classline = "tool_classes.append((%s, %s))" % (tool[0][0], tool[1])
                exec(classline)

    for c, args in tool_classes:
        if debug:
            print("REGISTERING TOOL", c, args)

        try:
            register_tool(c, **args)
        except:
            pass

    return [c for c, _ in tool_classes]

def unregister_tools(tools, debug=False):
    for t in tools:
        if debug:
            print("UN-REGISTERING", t)

        try:
            unregister_tool(t)
        except:
            pass

def register_macros(macrolists, debug=False):
    macro_classes = []

    for macrolist in macrolists:
        for fr, macros in macrolist:
            impline = "from ..%s import %s" % (fr, ", ".join([m[0] for m in macros]))
            exec(impline)

            for macro in macros:
                classline = "macro_classes.append(%s)" % (macro[0])
                exec(classline)

    for c in macro_classes:
        if debug:
            print("REGISTERING MACRO", c)

        register_class(c)
        c.init()

    return [c for c in macro_classes]

def unregister_macros(macros, debug=False):
    for m in macros:
        if debug:
            print("UN-REGISTERING", m)

        unregister_class(m)

def register_keymaps(keylists):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    keymaps = []

    if kc:

        for keylist in keylists:
            for item in keylist:
                keymap = item.get("keymap")
                space_type = item.get("space_type", "EMPTY")
                region_type = item.get("region_type", "WINDOW")

                if keymap:
                    km = kc.keymaps.new(name=keymap, space_type=space_type, region_type=region_type)

                    if km:
                        idname = item.get("idname")
                        type = item.get("type")
                        value = item.get("value")

                        shift = item.get("shift", False)
                        ctrl = item.get("ctrl", False)
                        alt = item.get("alt", False)

                        kmi = km.keymap_items.new(idname, type, value, shift=shift, ctrl=ctrl, alt=alt)

                        if kmi:
                            properties = item.get("properties")

                            if properties:
                                for name, value in properties:
                                    setattr(kmi.properties, name, value)

                            active = item.get("active", True)
                            kmi.active = active

                            keymaps.append((km, kmi))
    else:
        print("WARNING: Keyconfig not availabe, skipping HyperCursor keymaps")

    return keymaps

def unregister_keymaps(keymaps):
    for km, kmi in keymaps:
        km.keymap_items.remove(kmi)

def register_icons():
    path = os.path.join(get_prefs().path, "icons")
    icons = previews.new()

    for i in sorted(os.listdir(path)):
        if i.endswith(".png"):
            iconname = i[:-4]
            filepath = os.path.join(path, i)

            icons.load(iconname, filepath, 'IMAGE')

    return icons

def unregister_icons(icons):
    previews.remove(icons)

def get_core():
    classlists = []
    keylists = []

    classlists.append(classesdict["CORE"])
    keylists.append(keysdict["TOOLBAR"])

    return classlists, keylists

def get_tools():
    return [classesdict["TOOLS"]]

def get_macros():
    return [classesdict["MACROS"]]

def get_ops():
    classlists = []
    keylists = []

    classlists.append(classesdict["TRANSFORM"])

    classlists.append(classesdict["HISTORY"])

    classlists.append(classesdict["FOCUS"])

    classlists.append(classesdict["ADD"])

    classlists.append(classesdict["ADJUST"])

    classlists.append(classesdict["CHANGE"])

    classlists.append(classesdict["ASSET"])

    classlists.append(classesdict["EDIT"])

    classlists.append(classesdict["SELECT"])

    classlists.append(classesdict["OBJECT"])

    classlists.append(classesdict["MESH"])

    classlists.append(classesdict["CUT"])

    classlists.append(classesdict["BEVEL"])

    classlists.append(classesdict["BEND"])

    classlists.append(classesdict["MODIFIER"])

    classlists.append(classesdict["DEBUG"])

    return classlists, keylists
