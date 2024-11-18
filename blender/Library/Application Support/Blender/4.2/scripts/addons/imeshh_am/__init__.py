bl_info = {
    "name": "iMeshh asset manager",
    "author": "Flores Arnaud",
    "version": (3, 4),
    "blender": (3, 6, 5),
    'category': 'Asset Manager',
    "location": "View3D > TOOLS > iMeshh",
    }

import bpy
from . import operators, panels, utils
from bpy.utils import previews
from bpy.types import WindowManager

preferences_classes = [utils.PathString,
                        operators.IMESHH_OT_AddFolderPath,
                        operators.IMESHH_OT_RemoveFolderPath,]
for cls in preferences_classes:
    bpy.utils.register_class(cls)

class Imeshh_PrefPanel(bpy.types.AddonPreferences):
    bl_idname = __name__

    paths : bpy.props.CollectionProperty(type=utils.PathString)
    scale_ui_popup : bpy.props.IntProperty(name="Thumbnail scale", default=8)

    def draw(self, context):
        layout = self.layout
        row = self.layout.row()
        row.prop(self, "scale_ui_popup")
        layout.use_property_split = False
        layout.use_property_decorate = False

        #paths = context.preferences.filepaths

        box = layout.box()
        split = box.split(factor=0.35)
        name_col = split.column()
        path_col = split.column()
        type_col = split.column()

        row = name_col.row(align=True)  # Padding
        row.separator()
        row.label(text="Name")

        row = path_col.row(align=True)  # Padding
        row.separator()
        row.label(text="Path")

        row = type_col.row(align=True)  # Padding
        row.separator()
        row.label(text="Type")

        for i, library in enumerate(self.paths):
            row = name_col.row()
            row.alert = not library.name
            row.prop(library, "name", text="")

            row = path_col.row()
            subrow = row.row()
            subrow.alert = not library.path
            subrow.prop(library, "path", text="")

            row = type_col.row()
            for item in utils.enum_members_from_instance(library, 'type_dir'):
                row.prop_enum(library, 'type_dir', value=item, text= '')
            row.operator("imeshh.remove_folder_path", text="", icon='X', emboss=False).index = i

        row = box.row()
        row.alignment = 'RIGHT'
        row.operator("imeshh.add_folder_path", text="", icon='ADD', emboss=False)


classes = [
    Imeshh_PrefPanel,
    panels.IMESHH_PT_ImeshhSettingsPanel,
    panels.IMESHH_PT_ViewPanel,
    utils.UIFolder,
    utils.iMeshh_AM,
    operators.IMESHH_OT_ImportObject,
    operators.IMESHH_OT_ImportMaterial,
    operators.IMESHH_OT_ImportHDR,
    operators.IMESHH_OT_OpenThumbnail,
    operators.IMESHH_OT_OpenBlend]

preview_collections = {}

def register():
    preferences_classes.extend(classes)
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except:
            continue
    bpy.types.Scene.imeshh_am = bpy.props.PointerProperty(type=utils.iMeshh_AM)
    preview_coll = previews.new()
    # Main preview enum
    WindowManager.asset_manager_previews = bpy.props.EnumProperty(items=utils.update_previews)

    preview_collections["main"] = preview_coll


def unregister():
    del bpy.types.Scene.imeshh_am
    preferences_classes.extend(classes)
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    for preview_coll in preview_collections.values():
        previews.remove(preview_coll)
    del WindowManager.asset_manager_previews
    preview_collections.clear()