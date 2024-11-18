bl_info = {
    "name": "Light Wrangler",
    "description": "Cursor-Targeted Lighting Add-On",
    "author": "Leonid Altman",
    "version": (2, 1, 9),
    "blender": (3, 6, 0),
    "category": "Lighting",
}

# Standard library imports
import os
import time
import math
import re
import json
import webbrowser
import platform

# Blender imports
import bpy
import bmesh
import blf
import bpy.utils.previews
import numpy as np
import random

from mathutils import Vector, Matrix
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    PointerProperty,
    FloatProperty,
    StringProperty,
    FloatVectorProperty,
)
from bpy.types import PropertyGroup, Operator
from bpy.app.handlers import persistent
from bpy_extras import view3d_utils

# Constants
ADDON_MODULE_NAME = __name__
ENGINE_CYCLES = "CYCLES"
LIGHT_TYPE = "LIGHT"
CUSTOMIZATION_KEY = "customization"
SCRIM_VALUE = "Scrim"
SCRIM_PREVIEW_MAT = "Scrim Preview"
SCRIM_PREVIEW_PLANE = "Scrim_Preview_Plane"

# Global variables
duplicate_case = False
is_updating_light = False
AdjustingLight = None
AdjustingEmpty = None
KEY_IDENTIFIER = None
last_known_values = None
gobo_previews = None
hdri_previews = None
ies_previews = None

# State dictionary to keep track of the addon's state
state = {
    "operator_running": False,
    "last_active_object_name": None,
    "last_active_object_update_counter": 0,
    "last_customization": "",
}

# Dictionary to store the last activation time for each shortcut
last_activation_time = {
    "Power": 0,
    "Size": 0,
    "Distance": 0,
    "Spread": 0,
    "Isolate Light": 0,
    "Hide Light": 0,
    "Light Linking": 0,
}

def get_navigation_hints():
    try:
        # Detect the operating system
        os_name = platform.system()

        # Define navigation hints based on the operating system
        if os_name == 'Darwin':  # macOS
            return [
                ("🖱️", "Power"),
                ("⇧ + 🖱️", "Size"),  # Shift + Mouse
                ("⌥ + 🖱️", "Distance"),  # Alt + Mouse
                ("⌃ + 🖱️", "Spread"),  # Ctrl + Mouse
            ]
        elif os_name in ['Windows', 'Linux']:  # Windows or Linux
            return [
                ("🖱️", "Power"),
                ("Shift + 🖱️", "Size"),
                ("Alt + 🖱️", "Distance"),
                ("Ctrl + 🖱️", "Spread"),
            ]
        else:
            # Default to text representations if the OS is not recognized
            return [
                ("🖱️", "Power"),
                ("Shift + 🖱️", "Size"),
                ("Alt + 🖱️", "Distance"),
                ("Ctrl + 🖱️", "Spread"),
            ]
    except Exception as e:
        # Log the exception if needed and return default hints
        print(f"Error detecting OS: {e}")
        return [
            ("🖱️", "Power"),
            ("Shift + 🖱️", "Size"),
            ("Alt + 🖱️", "Distance"),
            ("Ctrl + 🖱️", "Spread"),
        ]

def get_light_control_hints():
    try:
        # Detect the operating system
        os_name = platform.system()

        # Define light control hints based on the operating system
        if os_name == 'Darwin':  # macOS
            return [
                ("⇧ + H", "Isolate Light"),  # Shift + H
                ("H", "Hide Light"),
                ("L", "Light Linking"),
            ]
        elif os_name in ['Windows', 'Linux']:  # Windows or Linux
            return [
                ("Shift + H", "Isolate Light"),
                ("H", "Hide Light"),
                ("L", "Light Linking"),
            ]
        else:
            # Default to text representations if the OS is not recognized
            return [
                ("Shift + H", "Isolate Light"),
                ("H", "Hide Light"),
                ("L", "Light Linking"),
            ]
    except Exception as e:
        # Log the exception if needed and return default hints
        print(f"Error detecting OS: {e}")
        return [
            ("Shift + H", "Isolate Light"),
            ("H", "Hide Light"),
            ("L", "Light Linking"),
        ]

# Get the appropriate navigation hints
navigation_hints = get_navigation_hints()

# Mode hints for positioning mode
mode_group = "Positioning Mode"
mode_hints = [
    ("1", "Reflect Mode"),
    ("2", "Orbit Mode"),
    ("3", "Direct Mode"),
]

# New section for light controls
light_control_group = "Light Controls"
light_control_hints = get_light_control_hints()

# List to store addon keymaps
addon_keymaps = []

last_activation_time = {}

def apply_preferences():
    """
    Applies saved preferences to the addon.
    """
    saved_prefs = load_preferences()
    if saved_prefs: 
        try:
            prefs = bpy.context.preferences.addons[__name__].preferences
            for attr, value in saved_prefs.items():
                setattr(prefs, attr, value)
        except Exception as e:
            print(f"Error applying saved preferences: {str(e)}")

def get_preferences_file_path():
    """
    Returns the file path for storing the addon's preferences.
    """
    try:
        preferences_base_path = bpy.utils.user_resource('SCRIPTS')
        preferences_path = os.path.join(preferences_base_path, "preferences")

        if not os.path.exists(preferences_path):
            os.makedirs(preferences_path, exist_ok=True)

        preferences_file = os.path.join(preferences_path, "light_wrangler_preferences.json")
        return preferences_file
    except PermissionError as e:
        print(f"Permission denied when accessing preferences path: {str(e)}")
        
        return None

def save_all_preferences():
    """
    Saves all addon preferences to a JSON file.
    """
    try:
        preferences_file = get_preferences_file_path()
        prefs = bpy.context.preferences.addons[__name__].preferences

        preferences_dict = {
            "hdri_path": prefs.hdri_path,
            "hdri_path_2": prefs.hdri_path_2,
            "hdri_path_3": prefs.hdri_path_3,
            "gobo_path": prefs.gobo_path,
            "gobo_path_2": prefs.gobo_path_2,
            "gobo_path_3": prefs.gobo_path_3,
            "ies_profiles_path": prefs.ies_profiles_path,
            "ies_previews_path": prefs.ies_previews_path,
            "initial_light_distance": prefs.initial_light_distance,
            "initial_light_power": prefs.initial_light_power,
            "initial_light_size": prefs.initial_light_size,
            "initial_light_spread_deg": prefs.initial_light_spread_deg,
            "use_custom_light_setup": prefs.use_custom_light_setup,
            "show_lights_previews": prefs.show_lights_previews,
            "initial_light_temp": prefs.initial_light_temp,
            "detect_ground_ceiling": prefs.detect_ground_ceiling,
            "manual_ground_level": prefs.manual_ground_level,
            "use_manual_ground_level": prefs.use_manual_ground_level,
            "use_calculated_light": prefs.use_calculated_light,
            "initial_mode": prefs.initial_mode,
            "draw_viewport_hints": prefs.draw_viewport_hints,
            "hide_viewport_overlays": prefs.hide_viewport_overlays,
            "toggle_light_visibility": prefs.toggle_light_visibility,
            "organize_lights": prefs.organize_lights,
        }

        with open(preferences_file, 'w') as file:
            json.dump(preferences_dict, file, indent=4)
    except Exception as e:
        print(f"Failed to save preferences: {str(e)}")

def load_preferences():
    """
    Loads addon preferences from a JSON file.
    """
    try:
        preferences_file = get_preferences_file_path()

        if not os.path.exists(preferences_file):
            return {} 

        with open(preferences_file, 'r') as file:
            return json.load(file)
    except PermissionError as e:
        print(f"Permission error accessing preferences file: {str(e)}")
        
        return {}
    except json.JSONDecodeError as e:
        print(f"Error reading preferences file: {str(e)}")
        return {}
    except Exception as e:
        print(f"Unexpected error loading preferences: {str(e)}")
        return {}


def update_hdri_path(self, context):
    """
    Updates the HDRI path preference and reloads HDRI previews.
    """

    save_all_preferences()
    load_hdri_previews()

def update_gobo_path(self, context):
    """
    Updates the Gobo path preference and reloads Gobo previews.
    """
    save_all_preferences()
    scan_and_generate_thumbnails()
    load_gobo_previews()

def update_ies_path(self, context):
    """
    Updates the IES path preference and reloads IES previews.
    """
    save_all_preferences()
    load_ies_previews()

def update_preference(self, context):
    """
    Generic preference update handler that saves preferences.
    """
    save_all_preferences()

class ClearHDRIDirectoryPath(bpy.types.Operator):
    """
    Clear the HDRI Folder Path
    """
    bl_idname = "wm.clear_hdri_directory_path"
    bl_label = "Clear"
    path_index: bpy.props.IntProperty()  

    def execute(self, context):
        prefs = context.preferences.addons[ADDON_MODULE_NAME].preferences
        if self.path_index == 1:
            prefs.hdri_path = ""
        elif self.path_index == 2:
            prefs.hdri_path_2 = ""
        elif self.path_index == 3:
            prefs.hdri_path_3 = ""
        return {'FINISHED'}

class ClearGoboDirectoryPath(bpy.types.Operator):
    """
    Clear the Gobo Folder Path
    """
    bl_idname = "wm.clear_gobo_directory_path"
    bl_label = "Clear"
    path_index: bpy.props.IntProperty()  

    def execute(self, context):
        prefs = context.preferences.addons[ADDON_MODULE_NAME].preferences
        if self.path_index == 1:
            prefs.gobo_path = ""
        elif self.path_index == 2:
            prefs.gobo_path_2 = ""
        elif self.path_index == 3:
            prefs.gobo_path_3 = ""
        return {'FINISHED'}

class RefreshIESPath(bpy.types.Operator):
    """Reloads the IES profiles from the selected folders"""
    bl_idname = "wm.refresh_ies_path"
    bl_label = "Refresh IES Previews"

    def execute(self, context):
        load_ies_previews()
        return {'FINISHED'}

class ClearIESDirectoryPath(bpy.types.Operator):
    """Clear the IES Directory Path"""
    bl_idname = "wm.clear_ies_directory_path"
    bl_label = "Clear"

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        prefs.ies_profiles_path = ""
        prefs.ies_previews_path = ""
        return {'FINISHED'}


class OpenHDRIPathBrowser(bpy.types.Operator):
    """
    Open a file browser to select the HDRI directory
    """
    bl_idname = "object.open_hdri_path_browser"
    bl_label = "Select HDRI Directory"
    filepath: bpy.props.StringProperty(subtype="DIR_PATH")

    def execute(self, context):
        prefs = context.preferences.addons[ADDON_MODULE_NAME].preferences
        prefs.hdri_path = self.filepath
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        self.layout.operator_context = 'INVOKE_DEFAULT'
        self.layout.operator(OpenHDRIPathBrowser.bl_idname, text="Select Directory", icon='FILE_FOLDER').filepath = self.filepath
        return {'RUNNING_MODAL'}
    
class OpenGoboPathBrowser(bpy.types.Operator):
    """
    Open a file browser to select the Gobo directory
    """
    bl_idname = "object.open_gobo_path_browser"
    bl_label = "Select Gobo Directory"
    filepath: bpy.props.StringProperty(subtype="DIR_PATH")

    def execute(self, context):
        prefs = context.preferences.addons[ADDON_MODULE_NAME].preferences
        prefs.gobo_path = self.filepath
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        self.layout.operator_context = 'INVOKE_DEFAULT'
        self.layout.operator(OpenGoboPathBrowser.bl_idname, text="Select Directory", icon='FILE_FOLDER').filepath = self.filepath
        return {'RUNNING_MODAL'}
    
class LightWranglerPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__


    last_360_hdri_directory: bpy.props.StringProperty(
        name="Last 360HDRI Directory",
        subtype='DIR_PATH',
        default=""
    )

    last_scrim_directory: bpy.props.StringProperty(
        name="Last Scrim Directory",
        subtype='DIR_PATH',
        default=""
    )    

    hdri_path: bpy.props.StringProperty(
        name="HDRI Folder 1",
        description="Path to the directory where custom HDRIs are stored.",
        subtype='DIR_PATH',
        update=update_hdri_path
    )

    hdri_path_2: bpy.props.StringProperty(
        name="HDRI Folder 2",
        description="Path to the directory where custom HDRIs are stored.",
        subtype='DIR_PATH',
        update=update_hdri_path
    )

    hdri_path_3: bpy.props.StringProperty(
        name="HDRI Folder 3",
        description="Path to the directory where custom HDRIs are stored.",
        subtype='DIR_PATH',
        update=update_hdri_path
    )

    gobo_path: bpy.props.StringProperty(
        name="Gobo Folder 1",
        description="Path to the directory where custom Gobos are stored.",
        subtype='DIR_PATH',
        update=update_gobo_path
    )

    gobo_path_2: bpy.props.StringProperty(
        name="Gobo Folder 2",
        description="Path to the directory where custom Gobos are stored.",
        subtype='DIR_PATH',
        update=update_gobo_path
    )

    gobo_path_3: bpy.props.StringProperty(
        name="Gobo Folder 3",
        description="Path to the directory where custom Gobos are stored.",
        subtype='DIR_PATH',
        update=update_gobo_path
    )

    ies_profiles_path: bpy.props.StringProperty(
        name="IES Profiles Folder",
        description="Path to the directory where custom IES profiles are stored.",
        subtype='DIR_PATH',
        update=update_ies_path
    )

    ies_previews_path: bpy.props.StringProperty(
        name="IES Previews Folder",
        description="Path to the directory where custom IES preview images are stored.",
        subtype='DIR_PATH',
        update=update_ies_path
    )


    initial_light_distance: bpy.props.FloatProperty(
        name="Initial Light Distance",
        description="Set the initial distance of the light from the object",
        default=1.5,
        min=0.001,
        max=100000000000,
        unit="LENGTH",
        update=update_preference
    )

    initial_light_power: bpy.props.FloatProperty(
        name="Initial Light Power",
        description="Set the initial power of the light",
        default=7,
        min=0.001,
        max=100000000000,
        unit="POWER",
        update=update_preference
    )

    initial_light_size: bpy.props.FloatProperty(
        name="Initial Light Size",
        description="Set the initial size of the light",
        default=1.0,
        min=0.001,
        max=100000000000,
        unit="LENGTH",
        update=update_preference
    )

    initial_light_spread_deg: bpy.props.FloatProperty(
        name="Initial Light Spread",
        description="Set the initial spread of the light",
        default=180,
        min=0.0,
        max=180.0,
        update=update_preference
    )

    use_custom_light_setup: bpy.props.BoolProperty(
        name="Light Customization (Cycles-only)",
        description="Activate custom light node setups",
        default=True,
        update=update_preference
    )

    show_lights_previews: bpy.props.BoolProperty(
        name="Interactive Light Preview (Experimental)",
        description="Displays a real-time scrim light preview in the panel. (WARNING: Use with caution! May cause performance issues or crashes.)",
        default=False,
        update=update_preference
    )

    toggle_light_visibility: bpy.props.BoolProperty(
        name="Auto Light Visibility",
        description="Light visibility to camera toggles with selection: visible when selected, not visible when unselected. Only works when real-time compositor is off.",
        default=True,
        update=update_preference
    )

    organize_lights: bpy.props.BoolProperty(
        name="Organize Lights (Beta)",
        description="Automatically place new lights into a specific 'Lights' collection and rename them to reflect their light mode",
        default=False, 
        update=update_preference
    )

    initial_light_temp: bpy.props.FloatProperty(
        name="Initial Light Temperature",
        description="Set the initial color temperature of the light. Set to 0 to disable and use plain RGB emission.",
        default=0,
        min=0,
        max=20000,
        unit="NONE",
        update=update_preference
    )

    detect_ground_ceiling: bpy.props.BoolProperty(
        name="Detect Ground",
        description="Enable this to prevent the light from going below the ground level",
        default=True,
        update=update_preference
    )

    manual_ground_level: bpy.props.FloatProperty(
        name="Manual Ground Level",
        description="Manually set a ground level for light positioning",
        default=0.0,
        unit="LENGTH",
        update=update_preference
    )

    use_manual_ground_level: bpy.props.BoolProperty(
        name="Use Manual Ground Level",
        description="Enable to use the manually set ground level for light positioning",
        default=False,
        update=update_preference
    )

    use_calculated_light: bpy.props.BoolProperty(
        name="Smart Light Adjustments",
        description="Enable automatic calculation of light power on light size and distance",
        default=False,
        update=update_preference
    )

    initial_mode: bpy.props.EnumProperty(
        name="Initial Positioning Mode",
        description="Set the initial mode for light positioning",
        items=[
            ("reflect", "Reflect", "Positions the light to emphasize reflections"),
            (
                "direct",
                "Direct",
                "Positions the light directly towards the area beneath the cursor",
            ),
        ],
        default="reflect",
        update=update_preference
    )

    # aiming_precision: bpy.props.EnumProperty(
    #     name="Aiming Precision",
    #     description="Set the precision level for light aiming",
    #     items=[
    #         ("precise", "Precise", "Aim light exactly at the cursor location"),
    #         ("adaptive", "Adaptive", "Use advanced algorithms for smoother, context-aware light aiming"),
    #     ],
    #     default="adaptive",
    #     update=update_preference
    # )

    draw_viewport_hints: bpy.props.BoolProperty(
        name="Show Control Hints",
        description="Toggle to display or hide hints for keyboard controls in the viewport",
        default=True,
        update=update_preference
    )

    hide_viewport_overlays: bpy.props.BoolProperty(
        name="Hide Viewport Overlays",
        description="Toggle to enable or disable viewport overlays hiding",
        default=True,
        update=update_preference
    )

    speedfactor: bpy.props.FloatProperty(
        name="Speed Factor",
        description="Set the speed factor for light adjustments",
        default=0.35,
    )

    alpha_EMA: bpy.props.FloatProperty(
        name="Alpha",
        description="Set the alpha value for light adjustments",
        default=0.65,
        min=0.0,
        max=1.0,
        
    )

    lerp_min: bpy.props.FloatProperty(
        name="Lerp Min",
        description="Set the minimum lerp value for light adjustments",
        default=0.35,
        
    )

    lerp_max: bpy.props.FloatProperty(
        name="Lerp Max",
        description="Set the maximum lerp value for light adjustments",
        default=1.0,
        
    )

    alpha: bpy.props.FloatProperty(
        name="Alpha",
        description="Set the alpha value for light adjustments",
        default=1,
        
    )

    def draw(self, context):
        layout = self.layout

        light_settings = layout.box()
        light_settings.label(text="Initial Light Settings", icon="LIGHT")

        cols = light_settings.row().split(factor=0.5)
        col1 = cols.column()
        col1.prop(self, "initial_light_distance")
        col1.prop(self, "initial_light_power")
        col1.prop(self, "initial_light_temp") #next is alpha value setting
        # col1.prop(self, "alpha_EMA")
   

        col2 = cols.column()
        col2.prop(self, "initial_light_size")
        col2.prop(self, "initial_light_spread_deg")

        mode_row = col2.row().split(factor=0.6)
        mode_row.label(text="Initial Positioning Mode:")
        mode_row.prop(self, "initial_mode", text="")

        # #aiming_precision here in the same column that Initial Positioning Mode in the next row
        # aiming_row = col2.row().split(factor=0.6)
        # aiming_row.label(text="Aiming Precision:")
        # aiming_row.prop(self, "aiming_precision", text="")

        

        
        

        

           


        advanced_settings = layout.box()
        advanced_settings.label(text="Advanced Settings", icon="PREFERENCES")
        advanced_cols = advanced_settings.row().split(factor=0.5)

        advanced_col1 = advanced_cols.column()
        advanced_col1.prop(self, "use_custom_light_setup")

        show_lights_previews_row = advanced_col1.row()
        show_lights_previews_row.enabled = self.use_custom_light_setup
        show_lights_previews_row.prop(self, "show_lights_previews")

        advanced_col1.prop(self, "draw_viewport_hints")
        advanced_col1.prop(self, "organize_lights")

        advanced_col2 = advanced_cols.column()
        advanced_col2.prop(self, "use_calculated_light")
        advanced_col2.prop(self, "hide_viewport_overlays")
        advanced_col2.prop(self, "toggle_light_visibility")



        ground_settings = layout.box()
        ground_settings.label(text="Ground Level Settings", icon="CON_FLOOR")
        ground_settings.prop(
            self, "detect_ground_ceiling", text="Smart Ground Detection"
        )
        ground_settings.prop(self, "use_manual_ground_level")

        manual_ground_row = ground_settings.row()
        manual_ground_row.enabled = self.use_manual_ground_level
        manual_ground_row.prop(self, "manual_ground_level")


        path_settings = layout.box()
        path_settings.label(text="Asset Paths", icon="FILE_FOLDER")

        # HDRI Folder 1
        split1 = path_settings.split(factor=0.85, align=True)  # Increased space for buttons
        split1.prop(self, "hdri_path")
        col1 = split1.column(align=True)
        row1 = col1.row(align=True)
        row1.operator("wm.refresh_hdri_path", text="", icon='FILE_REFRESH').path_index = 1
        row1.operator("wm.clear_hdri_directory_path", text="", icon='X').path_index = 1

        # HDRI Folder 2
        split2 = path_settings.split(factor=0.85, align=True)
        split2.prop(self, "hdri_path_2")
        col2 = split2.column(align=True)
        row2 = col2.row(align=True)
        row2.operator("wm.refresh_hdri_path", text="", icon='FILE_REFRESH').path_index = 2
        row2.operator("wm.clear_hdri_directory_path", text="", icon='X').path_index = 2

        # HDRI Folder 3
        split3 = path_settings.split(factor=0.85, align=True)
        split3.prop(self, "hdri_path_3")
        col3 = split3.column(align=True)
        row3 = col3.row(align=True)
        row3.operator("wm.refresh_hdri_path", text="", icon='FILE_REFRESH').path_index = 3
        row3.operator("wm.clear_hdri_directory_path", text="", icon='X').path_index = 3

        # Gobo Folder 1
        split4 = path_settings.split(factor=0.85, align=True)
        split4.prop(self, "gobo_path")
        col4 = split4.column(align=True)
        row4 = col4.row(align=True)
        row4.operator("wm.refresh_gobo_path", text="", icon='FILE_REFRESH').path_index = 1
        row4.operator("wm.clear_gobo_directory_path", text="", icon='X').path_index = 1

        # Gobo Folder 2
        split5 = path_settings.split(factor=0.85, align=True)
        split5.prop(self, "gobo_path_2")
        col5 = split5.column(align=True)
        row5 = col5.row(align=True)
        row5.operator("wm.refresh_gobo_path", text="", icon='FILE_REFRESH').path_index = 2
        row5.operator("wm.clear_gobo_directory_path", text="", icon='X').path_index = 2

        # Gobo Folder 3
        split6 = path_settings.split(factor=0.85, align=True)
        split6.prop(self, "gobo_path_3")
        col6 = split6.column(align=True)
        row6 = col6.row(align=True)
        row6.operator("wm.refresh_gobo_path", text="", icon='FILE_REFRESH').path_index = 3
        row6.operator("wm.clear_gobo_directory_path", text="", icon='X').path_index = 3

        # IES Folders
        ies_box = path_settings.box()
        ies_box.label(text="IES Folders")
        
        # IES Profiles Folder
        split7 = ies_box.split(factor=0.85, align=True)
        split7.prop(self, "ies_profiles_path", text="IES Profiles")
        col7 = split7.column(align=True)
        row7 = col7.row(align=True)
        row7.operator("wm.refresh_ies_path", text="", icon='FILE_REFRESH')
        row7.operator("wm.clear_ies_directory_path", text="", icon='X')

        # IES Previews Folder
        split8 = ies_box.split(factor=0.85, align=True)
        split8.prop(self, "ies_previews_path", text="IES Previews")
        col8 = split8.column(align=True)
        row8 = col8.row(align=True)
        row8.operator("wm.refresh_ies_path", text="", icon='FILE_REFRESH')
        row8.operator("wm.clear_ies_directory_path", text="", icon='X')

        # Validation and info message
        if self.ies_profiles_path and self.ies_previews_path:
            ies_box.label(text="IES folders are set correctly.", icon="CHECKMARK")
        else:
            ies_box.label(text="Both IES folders must be set for custom IES to work.", icon="INFO")

            
        doc_and_support = layout.box()
        doc_and_support.label(text="Documentation and Support", icon="HELP")
        doc_cols = doc_and_support.row()
        doc_cols.operator(
            "wm.url_open", text="Documentation"
        ).url = "https://blendermarket.com/products/light-wrangler/docs"
        doc_cols.operator("wm.open_mail", text="Report a Bug", icon="URL")


def check_render_engine():
    render_engine = bpy.context.scene.render.engine
    return render_engine in ["BLENDER_EEVEE", "CYCLES", "BLENDER_WORKBENCH", "BLENDER_EEVEE_NEXT"]



class RefreshHDRIPath(bpy.types.Operator):
    """Reloads the HDRI images from the selected folder"""

    bl_idname = "wm.refresh_hdri_path"
    bl_label = "Refresh"
    path_index: bpy.props.IntProperty()

    def execute(self, context):
        load_hdri_previews()
        return {'FINISHED'}

class RefreshGoboPath(bpy.types.Operator):
    """Reloads the Gobos from the selected folder"""


    bl_idname = "wm.refresh_gobo_path"
    bl_label = "Refresh"
    path_index: bpy.props.IntProperty()

    def execute(self, context):
        scan_and_generate_thumbnails()
        load_gobo_previews()
        return {'FINISHED'}


# class LIGHT_MT_pie_menu(Menu):
#     bl_label = "Light Operations Pie Menu"

#     @classmethod
#     def poll(cls, context):

#         return (
#             context.active_object is not None
#             and context.active_object.type == "LIGHT"
#             and context.active_object.data.type in {"AREA", "SPOT"}
#         )

#     def draw(self, context):
#         layout = self.layout
#         pie = layout.menu_pie()

#         pie.operator(
#             "wm.open_addon_preferences", text="Preferences", icon="PREFERENCES"
#         )

#         pie.operator(
#             "object.copy_and_adjust_light", text="Duplicate Light", icon="DUPLICATE"
#         )

#         pie.operator(
#             "object.add_empty_at_intersection",
#             text="Track to Target",
#             icon="CON_TRACKTO",
#         )


def natural_sort_key(s):

    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split("([0-9]+)", s)
    ]

def scan_and_generate_thumbnails():
    addon_prefs = bpy.context.preferences.addons[__name__].preferences
    custom_folder_paths = [addon_prefs.gobo_path, addon_prefs.gobo_path_2, addon_prefs.gobo_path_3]
    video_extensions = ('.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.ogv')
    videos_needing_thumbnails = []

    for folder_path in custom_folder_paths:
        if folder_path and os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(video_extensions):
                    video_path = os.path.join(folder_path, filename)
                    thumbnail_path = os.path.join(folder_path, f"{os.path.splitext(filename)[0]}_thumb.png")
                    if not os.path.exists(thumbnail_path):
                        videos_needing_thumbnails.append((video_path, thumbnail_path))
        elif folder_path:
            print(f"Custom gobo folder path does not exist: {folder_path}")

    if videos_needing_thumbnails:
        for video_path, thumbnail_path in videos_needing_thumbnails:
            generate_thumbnail(video_path, thumbnail_path)

def generate_thumbnail(video_path, output_path):
    try:
        original_scene = bpy.context.scene
        scene = bpy.data.scenes.new(name="Thumbnail Scene")
        bpy.context.window.scene = scene

        # Set square resolution
        thumbnail_size = 200
        scene.render.resolution_x = thumbnail_size
        scene.render.resolution_y = thumbnail_size
        scene.render.filepath = output_path
        scene.render.image_settings.file_format = 'PNG'

        # Set color management to ensure accurate color reproduction
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'None'
        scene.display_settings.display_device = 'sRGB'

        if scene.sequence_editor is None:
            scene.sequence_editor_create()

        seq = scene.sequence_editor.sequences.new_movie(
            name=os.path.basename(video_path),
            filepath=video_path,
            channel=1,
            frame_start=1
        )

        scene.frame_start = 1
        scene.frame_end = seq.frame_final_duration
        middle_frame = seq.frame_final_duration // 2
        scene.frame_current = middle_frame

        # Calculate scaling factor based on height
        scale_factor = thumbnail_size / seq.elements[0].orig_height

        # Calculate the scaled width
        scaled_width = seq.elements[0].orig_width * scale_factor

        if scaled_width > thumbnail_size:
            # If scaled width is larger than thumbnail, adjust scale to fit width
            scale_factor = thumbnail_size / seq.elements[0].orig_width
            seq.transform.scale_x = scale_factor
            seq.transform.scale_y = scale_factor
            # Center vertically
            seq.transform.offset_y = (thumbnail_size - seq.elements[0].orig_height * scale_factor) / 2
        else:
            # If scaled width is smaller or equal, use height-based scaling
            seq.transform.scale_x = scale_factor
            seq.transform.scale_y = scale_factor
            # Center horizontally
            seq.transform.offset_x = (thumbnail_size - scaled_width) / 2

        # Adjust color space and color management
        seq.colorspace_settings.name = 'sRGB'
        
        # Ensure full color range
        scene.sequencer_colorspace_settings.name = 'sRGB'

        bpy.ops.render.render(write_still=True)
        
        bpy.data.scenes.remove(scene)
        bpy.context.window.scene = original_scene
        
        print(f"Generated thumbnail for {os.path.basename(video_path)}")
    except Exception as e:
        print(f"Error generating thumbnail for {os.path.basename(video_path)}:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        traceback.print_exc()

def load_gobo_previews():
    global gobo_previews


    
    try:
        if gobo_previews is not None:
            bpy.utils.previews.remove(gobo_previews)
            gobo_previews = None
    except Exception as e:
        print("Failed to remove gobo previews:", e)

    gobo_previews = bpy.utils.previews.new()



    gobo_previews_dir = os.path.join(os.path.dirname(__file__), "gobo_previews")
    
    load_images_from_gobo_folder(gobo_previews_dir, is_builtin=True)

    addon_prefs = bpy.context.preferences.addons[__name__].preferences
    custom_folder_paths = [addon_prefs.gobo_path, addon_prefs.gobo_path_2, addon_prefs.gobo_path_3]  # Example custom paths
    for custom_folder_path in custom_folder_paths:
        if custom_folder_path:
            load_images_from_gobo_folder(custom_folder_path)

def load_images_from_gobo_folder(folder_path, is_builtin=False):
    if not folder_path:
        return

    filenames = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith((".jpg", ".png", ".webp"))
    ]
    filenames.sort(key=lambda x: natural_sort_key(os.path.basename(x)))

    for filename in filenames:
        filepath = filename if is_builtin else os.path.join(folder_path, filename)
        name = os.path.basename(filepath) if is_builtin else "user:" + os.path.basename(filepath)

        # Check if the preview already exists before loading
        if name not in gobo_previews:
            try:
                gobo_previews.load(name, filepath, "IMAGE")
            except RuntimeError as e:
                print(f"Error loading {name}: {e}")
        else:
            print(f"Skipping duplicate preview for {name}")



# , ".hdr", ".exr", ".tif", ".tiff"

def load_hdri_previews():
    global hdri_previews

    try:
        if hdri_previews is not None:
            bpy.utils.previews.remove(hdri_previews)
            hdri_previews = None 
    except Exception as e:
        print("Failed to remove HDRI previews:", e) 
           
    hdri_previews = bpy.utils.previews.new()

   
    folder1_path = os.path.join(os.path.dirname(__file__), "hdri_previews")
    load_images_from_folder(folder1_path, is_builtin=True)

    
    addon_prefs = bpy.context.preferences.addons[__name__].preferences
    custom_folder_paths = [addon_prefs.hdri_path, addon_prefs.hdri_path_2, addon_prefs.hdri_path_3]
    for custom_folder_path in custom_folder_paths:
        if custom_folder_path:  
            load_images_from_folder(custom_folder_path)

def load_images_from_folder(folder_path, is_builtin=False):
    if not folder_path:  
        return


    if not os.path.exists(folder_path):
        return

    filenames = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith((".jpg", ".png", ".hdr", ".exr", ".tif", ".tiff", ".webp"))
    ]
    filenames.sort(key=lambda x: natural_sort_key(os.path.basename(x)))

    for filename in filenames:
        filepath = os.path.join(folder_path, filename) if is_builtin else filename
        name = os.path.basename(filepath) if is_builtin else "user:" + filename

        hdri_previews.load(name, filepath, "IMAGE")


def load_ies_previews():
    global ies_previews
    if ies_previews is not None:
        bpy.utils.previews.remove(ies_previews)
    ies_previews = bpy.utils.previews.new()

    # Load built-in IES previews
    ies_previews_dir = os.path.join(os.path.dirname(__file__), "ies_previews")
    load_ies_from_folder(ies_previews_dir, is_builtin=True)

    # Load custom IES previews
    addon_prefs = bpy.context.preferences.addons[__name__].preferences
    if addon_prefs.ies_profiles_path and addon_prefs.ies_previews_path:
        if os.path.exists(addon_prefs.ies_profiles_path) and os.path.exists(addon_prefs.ies_previews_path):
            load_ies_from_folder(addon_prefs.ies_previews_path, addon_prefs.ies_profiles_path)
        else:
            print("One or both of the specified IES folders do not exist.")
    else:
        print("Custom IES folders are not specified in the addon preferences.")

def load_ies_from_folder(previews_folder, profiles_folder=None, is_builtin=False):
    if os.path.exists(previews_folder):
        for filename in os.listdir(previews_folder):
            if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                preview_path = os.path.join(previews_folder, filename)
                ies_filename = os.path.splitext(filename)[0] + ".ies"
                
                if is_builtin or (profiles_folder and os.path.exists(os.path.join(profiles_folder, ies_filename))):
                    identifier = f"{'builtin:' if is_builtin else 'user:'}{ies_filename}"
                    ies_previews.load(identifier, preview_path, 'IMAGE')


def get_gobo_items(self, context):
    enum_items = []
    if context is None:
        return enum_items

    for idx, (name, preview) in enumerate(gobo_previews.items()):
        enum_items.append((name, "", "", preview.icon_id, idx))

    return enum_items


def get_hdri_items(self, context):
    enum_items = []
    if context is None:
        return enum_items

    for idx, (name, preview) in enumerate(hdri_previews.items()):
        is_builtin = not name.startswith("user:")
        path = name if is_builtin else name[5:]
        enum_items.append((path, "", "", preview.icon_id, idx))

    return enum_items


def get_ies_items(self, context):
    enum_items = []
    if context is None:
        return enum_items

    for idx, (name, preview) in enumerate(ies_previews.items()):
        enum_items.append((name, "", "", preview.icon_id, idx))

    return enum_items


def update_gobo_texture(self, context):
    light = context.object
    gobo_name = bpy.path.basename(self.gobo_enum)
    apply_gobo_to_light(light, gobo_name)


def update_hdri_texture(self, context):
    light = context.object
    hdri_path = self.hdri_enum
    apply_hdri_to_light(light, hdri_path)


def update_ies_texture(self, context):
    light = context.object
    ies_name = bpy.path.basename(self.ies_enum)
    apply_ies_to_light(light, ies_name)

class OpenAddonPreferencesOperator(bpy.types.Operator):
    """Opens Addon Preferences"""

    bl_idname = "wm.open_addon_preferences"
    bl_label = "Open Addon Preferences"

    def execute(self, context):
        if bpy.app.version >= (4, 2):
            bpy.context.preferences.active_section = "EXTENSIONS"
            bpy.ops.preferences.addon_show(module=ADDON_MODULE_NAME)
        else:
            bpy.context.preferences.active_section = "ADDONS"
            bpy.ops.preferences.addon_show(module=ADDON_MODULE_NAME)
        return {"FINISHED"}



class LIGHT_OT_apply_custom_data_block(bpy.types.Operator):
    bl_idname = "light.apply_custom_data_block"
    bl_label = "Apply Custom Data Block"
    bl_options = {"REGISTER", "UNDO"}

    bl_description = "Apply a specific customization to the selected light"
    light_name: bpy.props.StringProperty()
    light_type: bpy.props.StringProperty()
    customization: bpy.props.StringProperty()

    @classmethod
    def description(cls, context, properties):
        descriptions = {
            "Gobo": "Apply a Gobo texture to the light",
            "HDRI": "Apply HDRI texture to the light",
            "IES": "Apply an IES light profile to the light",
            "Scrim": "Apply a Scrim node group",
            "Default": "Don't apply any customizations",
        }
        return descriptions.get(properties.customization, cls.bl_description)

    def execute(self, context):
        addon_prefs = bpy.context.preferences.addons[__name__].preferences
        initial_light_temp = addon_prefs.initial_light_temp
        new_block_created = False
        light_obj = bpy.data.objects.get(self.light_name)
        if not light_obj:
            self.report({"ERROR"}, "Light object not found.")
            return {"CANCELLED"}

        id_prop_key = f"custom_data_block_{self.light_type}_{self.customization}"
        
        if id_prop_key in light_obj:
            existing_data_block = light_obj[id_prop_key]
            if existing_data_block and existing_data_block.name in bpy.data.lights:
                new_data_block = existing_data_block
            else:
                self.report(
                    {"ERROR"},
                    "Referenced data block not found or invalid. A new one will be created.",
                )
                new_data_block = self.create_new_data_block(light_obj, id_prop_key)
                new_block_created = True
        elif self.customization == "Default" and not any(prop.startswith("custom_data_block_") for prop in light_obj.keys()):
            new_data_block = self.refurbish_default_data_block(light_obj, id_prop_key)
            new_block_created = True
        else:
            new_data_block = self.create_new_data_block(light_obj, id_prop_key)
            new_block_created = True

        if light_obj.data and light_obj.data.type == self.light_type:
            self.copy_light_settings(light_obj.data, new_data_block)

        light_obj.data = new_data_block
        light_obj.data.type = self.light_type
        light_data = bpy.context.view_layer.objects.active.data

        if hasattr(light_data, "photographer"):
            photographer_settings = light_data.photographer
            if not (hasattr(photographer_settings, "gobo") and photographer_settings.gobo) and not (hasattr(photographer_settings, "ies") and photographer_settings.ies):
                self.ensure_node_group_connection(light_obj.data, self.customization)

        try:
            light_obj["customization"] = self.customization
        except Exception as e:
            print(f"Failed to set customization property: {e}")
        try:
            light_obj[f"last_customization_{self.light_type}"] = self.customization
        except Exception as e:
            print(f"Failed to set last_customization property: {e}")
        bpy.context.view_layer.objects.active = bpy.context.active_object

        if new_block_created:
            self.apply_initial_color_temp(light_obj.data, initial_light_temp)
            
        if bpy.context.preferences.addons[__name__].preferences.organize_lights and bpy.context.scene.render.engine == "CYCLES":
            light_obj.name = new_data_block.name
        
        return {"FINISHED"}

    def apply_initial_color_temp(self, light_data_block, temp_value):
        if light_data_block.use_nodes:
            for node in light_data_block.node_tree.nodes:
                if "ColorTemp" in node.inputs:
                    node.inputs["ColorTemp"].default_value = temp_value
                    break

    def create_new_data_block(self, light_obj, id_prop_key):
        readable_light_type = self.light_type.capitalize()
        new_data_block_name = f"{readable_light_type}.{self.customization}"

        new_data_block = bpy.data.lights.new(
            name=new_data_block_name, type=self.light_type
        )

        if self.customization == "Gobo":
            append_gobo_node_group()
        elif self.customization == "HDRI":
            append_hdri_node_group()
        elif self.customization == "IES":
            append_ies_node_group()
        elif self.customization == "Scrim":
            append_scrim_node_group()
            apply_scrim_to_light(new_data_block)

        light_obj[id_prop_key] = new_data_block
        return new_data_block

    def refurbish_default_data_block(self, light_obj, id_prop_key):
        readable_light_type = self.light_type.capitalize()
        new_data_block_name = f"{readable_light_type}.{self.customization}"

        old_data_block = light_obj.data
        old_data_block.name = new_data_block_name
        new_data_block = old_data_block

        light_obj.data = new_data_block
        light_obj[id_prop_key] = new_data_block
        return new_data_block

    def copy_light_settings(self, old_data_block, new_data_block):
        common_properties = ["color", "use_shadow", "shadow_color"]

        type_specific_properties = {
            "POINT": ["shadow_soft_size", "falloff_type", "energy", "shadow_soft_size"],
            "SPOT": [
                "spot_size",
                "spot_blend",
                "show_cone",
                "energy",
                "shadow_soft_size",
            ],
            "AREA": ["shape", "size", "size_y", "energy"],
            "SUN": ["angle", "sky_intensity", "contact_shadow_distance", "energy"],
        }

        for prop in common_properties:
            if hasattr(old_data_block, prop) and hasattr(new_data_block, prop):
                setattr(new_data_block, prop, getattr(old_data_block, prop))

        if old_data_block.type == new_data_block.type:
            if old_data_block.type in type_specific_properties:
                for prop in type_specific_properties[old_data_block.type]:
                    if hasattr(old_data_block, prop) and hasattr(new_data_block, prop):
                        setattr(new_data_block, prop, getattr(old_data_block, prop))

        if old_data_block.use_nodes and new_data_block.use_nodes:
            for old_node in old_data_block.node_tree.nodes:
                color_temp_input = next(
                    (input for input in old_node.inputs if input.name == "ColorTemp"),
                    None,
                )
                if color_temp_input:
                    new_node = new_data_block.node_tree.nodes.get(old_node.name)
                    if new_node:
                        new_color_temp_input = next(
                            (
                                input
                                for input in new_node.inputs
                                if input.name == "ColorTemp"
                            ),
                            None,
                        )
                        if new_color_temp_input:
                            new_color_temp_input.default_value = (
                                color_temp_input.default_value
                            )

    def ensure_node_group_connection(self, light_data_block, customization):
        if not light_data_block.use_nodes:
            light_data_block.use_nodes = True

        nodes = light_data_block.node_tree.nodes
        output_node = next(
            (node for node in nodes if node.type == "OUTPUT_LIGHT"), None
        )

        customization_key_phrases = {
            "Gobo": "Gobo Light",
            "HDRI": "HDRI Light",
            "IES": "IES Light",
            "Scrim": "Scrim Light",
        }

        key_phrase = customization_key_phrases.get(customization)
        if key_phrase:
            group_node = next(
                (
                    node
                    for node in nodes
                    if node.type == "GROUP" and key_phrase in node.node_tree.name
                ),
                None,
            )

            if group_node and output_node:
                if not any(
                    link.to_node == output_node for link in group_node.outputs[0].links
                ):
                    light_data_block.node_tree.links.new(
                        group_node.outputs[0], output_node.inputs[0]
                    )


def add_custom_properties_to_lights():
    light_types = ["POINT", "SPOT", "AREA", "SUN"]
    custom_options = {
        "POINT": ["Default", "IES"],
        "SPOT": ["Default", "Gobo"],
        "AREA": ["Default", "Scrim", "HDRI", "Gobo"],
        "SUN": ["Default"],
    }

    for light_type in light_types:
        for option in custom_options[light_type]:
            prop_name = f"{light_type.lower()}_{option.lower()}"
            setattr(bpy.types.Light, prop_name, bpy.props.BoolProperty(name=prop_name))


class OBJECT_OT_LightTypeChanged(bpy.types.Operator):
    """Update light type and apply custom data block"""

    bl_idname = "object.light_type_changed_operator"
    bl_label = "Custom Light Setup"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        active_obj = context.active_object
        return active_obj is not None and active_obj.type == "LIGHT"

    def execute(self, context):
        if bpy.types.Scene.modal_running == True:
            return {"CANCELLED"}

        active_obj = context.active_object
        prefs = context.preferences.addons[__name__].preferences

        if not prefs.use_custom_light_setup:
            self.report({"INFO"}, "Custom light setup is not enabled in preferences.")
            return {"CANCELLED"}

        current_light_type = active_obj.data.type

        if (
            "last_light_type" in active_obj
            and active_obj["last_light_type"] == current_light_type
        ):
            return {"CANCELLED"}

        last_customization = active_obj.get(
            f"last_customization_{current_light_type}", "Default"
        )
        result = self.apply_custom_data_block(
            active_obj.name, current_light_type, last_customization
        )

        if result:
            active_obj["last_light_type"] = current_light_type
            return {"FINISHED"}
        else:
            return {"CANCELLED"}

    def apply_custom_data_block(self, light_name, light_type, customization):
        try:
            bpy.ops.light.apply_custom_data_block(
                light_name=light_name,
                light_type=light_type,
                customization=customization,
            )
            return True
        except Exception as error:
            self.report({"ERROR"}, f"Error applying custom data block: {error}")
            return False


def light_type_changed(scene, depsgraph):
    global is_updating_light
    if is_updating_light or bpy.types.Scene.modal_running == True:
        return

    active_obj = bpy.context.active_object
    if active_obj and active_obj.type == "LIGHT":
        is_updating_light = True
        try:
            bpy.ops.object.light_type_changed_operator()
        except Exception as e:
            print("light_type_changed")
        finally:
            is_updating_light = False


def sync_node_values_handler(scene, depsgraph=None):
    if early_exit_conditions():
        return

    current_active_object = bpy.context.view_layer.objects.active
    current_object_name = current_active_object.name if current_active_object else ""

    current_customization_changed = False
    if current_active_object and CUSTOMIZATION_KEY in current_active_object:
        current_customization_changed = state["last_customization"] != current_active_object[CUSTOMIZATION_KEY]
        if current_active_object[CUSTOMIZATION_KEY] != "Scrim":
            return

    if not state_changed(current_object_name, scene.frame_current, current_customization_changed):
        return

    if not is_target_light_object(current_active_object):
        try:
            update_state(current_object_name, scene.frame_current, current_active_object)
            handle_non_light_active_object()
        except Exception as e:
            print(f"An error occurred: {e}")
        return

    try:
        state["operator_running"] = True
        bpy.ops.light.scrim_preview_creator()
    except Exception as e:
        print(f"An error occurred: {e}")    
    finally:
        state["operator_running"] = False
        update_state(current_object_name, scene.frame_current, current_active_object)

def early_exit_conditions():
    prefs = bpy.context.preferences.addons[__name__].preferences
    return (bpy.context.scene.render.engine != ENGINE_CYCLES
            or state["operator_running"]
            or not prefs.use_custom_light_setup
            or not prefs.show_lights_previews
            or bpy.types.Scene.modal_running)

def state_changed(current_object_name, frame_current, current_customization_changed):
    return (state["last_active_object_name"] != current_object_name
            or state["last_active_object_update_counter"] != frame_current
            or current_customization_changed)

def is_target_light_object(current_active_object):
    return (current_active_object and current_active_object.type == LIGHT_TYPE and
            (CUSTOMIZATION_KEY not in current_active_object or current_active_object[CUSTOMIZATION_KEY] == SCRIM_VALUE))

def handle_non_light_active_object():
    if SCRIM_PREVIEW_PLANE in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[SCRIM_PREVIEW_PLANE], do_unlink=True)

def update_state(active_object_name, update_counter, active_object):
    try:
        state["last_active_object_name"] = active_object_name
        state["last_active_object_update_counter"] = update_counter
        state["last_customization"] = active_object.get(CUSTOMIZATION_KEY, "") if active_object else ""
    except Exception as e:
        print(f"Failed to update state: {e}")


class LIGHT_OT_ScrimPreviewCreator(bpy.types.Operator):
    """Doubles the sync node values for custom light setups"""

    bl_idname = "light.scrim_preview_creator"
    bl_label = "Scrim Preview Creator"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        if bpy.types.Scene.modal_running == True or bpy.context.active_object.type != "LIGHT":
            
            return {"CANCELLED"}
     
        self.append_DO_NOT_EDIT_Scrim_Preview()
   
        material = self.create_scrim_preview_material()  

        self.create_plane_and_parent_to_light(material)
    
        light_obj = context.active_object
        
        self.setup_drivers_for_material(light_obj, material)
     
        return {"FINISHED"}

    def append_DO_NOT_EDIT_Scrim_Preview(self):
       
        node_group_name = "DO_NOT_EDIT_Scrim_Preview"
        blender_version = bpy.app.version
        if blender_version[0] >= 4:
            nodegroup_blend_path = os.path.join(
                os.path.dirname(__file__), "nodegroup-4.blend"
            )
        else:
            nodegroup_blend_path = os.path.join(
                os.path.dirname(__file__), "nodegroup.blend"
            )

        if node_group_name not in bpy.data.node_groups:
            with bpy.data.libraries.load(nodegroup_blend_path, link=False) as (
                data_from,
                data_to,
            ):
                if node_group_name in data_from.node_groups:
                    data_to.node_groups = [node_group_name]
                else:
                    print(
                        f"Node group '{node_group_name}' not found in the blend file."
                    )
                    return

            appended_node_group = bpy.data.node_groups.get(node_group_name)
            if appended_node_group:
                appended_node_group.use_fake_user = True
            else:
                print(f"Failed to append node group '{node_group_name}'.")
    

    def create_scrim_preview_material(self):
       
        material_name = "Scrim Preview"
        if material_name not in bpy.data.materials:
            material = bpy.data.materials.new(name=material_name)
            material.use_nodes = True
            material.preview_render_type = "FLAT"
            if "DO_NOT_EDIT_Scrim_Preview" in bpy.data.node_groups:
                nodes = material.node_tree.nodes
                nodes.clear()
                node_group = nodes.new(type="ShaderNodeGroup")
                node_group.node_tree = bpy.data.node_groups["DO_NOT_EDIT_Scrim_Preview"]
                node_group.name = "DO_NOT_EDIT_Scrim_Preview"
                material_output = nodes.new(type="ShaderNodeOutputMaterial")
                links = material.node_tree.links
                links.new(node_group.outputs[0], material_output.inputs["Surface"])
                
            else:
                print("DO_NOT_EDIT_Scrim_Preview node group not found.")
                return None
        else:
            material = bpy.data.materials[material_name]
            material.preview_render_type = "FLAT"
           
        return material

    def create_plane_and_parent_to_light(self, material):

        if "Scrim_Preview_Plane" in bpy.data.objects:
            #no text
            return

        light_obj = bpy.context.active_object
        scene = bpy.data.scenes["Scene"]
        unit_scale = scene.unit_settings.scale_length
        system = scene.unit_settings.system

        if system == "METRIC":

            offset_value = 0.05 / unit_scale
        elif system == "IMPERIAL":

            offset_value = (0.05 / 0.3048) / unit_scale
        else:

            offset_value = 0.05 / unit_scale
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.mesh.primitive_plane_add(
            size=0.00001, location=light_obj.location + Vector((0, 0, offset_value))
        )
        plane = bpy.context.active_object
        plane.name = "Scrim_Preview_Plane"
        plane.data.materials.append(material)
        plane.display_type = "WIRE"

        plane.rotation_euler = light_obj.rotation_euler

        plane.parent = light_obj
        plane.matrix_parent_inverse = light_obj.matrix_world.inverted()

        plane.hide_select = True
        plane.hide_render = True

        plane.visible_camera = False
        plane.visible_diffuse = False
        plane.visible_glossy = False
        plane.visible_transmission = False
        plane.visible_volume_scatter = False
        plane.visible_shadow = False
        plane.display.show_shadows = False

        bpy.context.view_layer.objects.active = light_obj
        bpy.context.view_layer.update()

        light_obj.select_set(True)
        

    def setup_drivers_for_material(self, light_obj, material):
        light_data = bpy.data.lights[light_obj.data.name]

        if not light_data:
            print(f"Light data for {light_obj.data.name} does not exist.")
            return

        if not light_data.use_nodes:
            light_data.use_nodes = True

        node_group_instance = light_data.node_tree.nodes.get("Group")
        if not node_group_instance:
            print("Node group 'Group' not found in the light object.")
            return

        properties = [
            ("ColorTemp", 0),
            ("Feathering", 1),
            ("Horizontal Tilt", 2),
            ("Vertical Tilt", 3),
            ("Disk", 4)  # Assuming 'Disk' is the fifth input in the node group
        ]

        for prop_name, input_index in properties:
            source_data_path = (
                f'node_tree.nodes["Group"].inputs[{input_index}].default_value'
            )
            self.add_driver(
                obj=light_obj,
                target=material.node_tree,
                target_data_path=f'nodes["DO_NOT_EDIT_Scrim_Preview"].inputs["{prop_name}"].default_value',
                source_data_path=source_data_path,
            )

        self.clear_existing_drivers(
            target=material.node_tree,
            target_data_path='nodes["DO_NOT_EDIT_Scrim_Preview"].inputs["Blender Color"].default_value',
        )

        for i in range(3):
            source_data_path = f"color[{i}]"
            self.add_driver(
                obj=light_obj,
                target=material.node_tree,
                target_data_path='nodes["DO_NOT_EDIT_Scrim_Preview"].inputs["Blender Color"].default_value',
                index=i,
                source_data_path=source_data_path,
                clear_existing=False,
            )

    def add_driver(
        self,
        obj,
        target,
        target_data_path,
        source_data_path,
        index=None,
        clear_existing=True,
    ):
        if clear_existing:
            self.clear_existing_drivers(
                target=target, target_data_path=target_data_path
            )

        
        if index is not None:
            driver_fcurve = target.driver_add(target_data_path, index)
        else:
            driver_fcurve = target.driver_add(target_data_path)

        if driver_fcurve is None:
            print(f"Failed to create driver for {target_data_path}")
            return

        driver = driver_fcurve.driver
        driver.type = "SCRIPTED"

        var = driver.variables.new()
        var.name = "color_channel"
        var.type = "SINGLE_PROP"
        var.targets[0].id_type = "LIGHT"
        var.targets[0].id = obj.data
        var.targets[0].data_path = source_data_path

        driver.expression = "color_channel"

    def clear_existing_drivers(self, target, target_data_path):
        if target.animation_data and target.animation_data.drivers:

            drivers_to_remove = [
                driver
                for driver in target.animation_data.drivers
                if driver.data_path == target_data_path
            ]
            for driver in drivers_to_remove:

                target.animation_data.drivers.remove(driver)
               


class MainPanel(bpy.types.Panel):
    bl_label = "Light Customization"
    bl_idname = "OBJECT_PT_lw_main_panel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        prefs = bpy.context.preferences.addons[__name__].preferences
        return (
            context.scene.render.engine == "CYCLES"
            and context.object is not None
            and context.object.type == "LIGHT"
            and prefs.use_custom_light_setup
        )

    def draw(self, context):
        layout = self.layout
        light_obj = context.object
        light_data = light_obj.data

        if light_data.type == "POINT":
            self.draw_customization_buttons(
                layout, light_obj, "POINT", ["Default", "IES"]
            )
        elif light_data.type == "SPOT":
            self.draw_customization_buttons(
                layout, light_obj, "SPOT", ["Default", "Gobo"]
            )
        elif light_data.type == "AREA":
            self.draw_customization_buttons(
                layout, light_obj, "AREA", ["Default", "Scrim", "HDRI", "Gobo"]
            )
        elif light_data.type == "SUN":
            self.draw_customization_buttons(layout, light_obj, "SUN", ["Default"])

    def draw_customization_buttons(self, layout, light_obj, light_type, options):
        last_customization_key = f"last_customization_{light_type}"
        current_customization = light_obj.get(last_customization_key, "Default")

        row = layout.row(align=True)

        for option in options:
            op = row.operator(
                "light.apply_custom_data_block",
                text=option,
                depress=option == current_customization,
            )
            op.light_name = light_obj.name
            op.light_type = light_type
            op.customization = option

        if current_customization in ["Gobo", "HDRI", "IES"]:
            box = layout.box()
            col = box.column()

            if current_customization == "Gobo":
                col.template_icon_view(
                    light_obj.data,
                    "gobo_enum",
                    show_labels=True,
                    scale_popup=6,
                    scale=7,
                )
                # Add the "Convert to Plane" button below the Gobo enum preview
                col.operator(
                    "light.convert_to_plane",
                    text="Convert to Plane",
                    icon='MESH_PLANE'
                )                
            elif current_customization == "HDRI":
                col.template_icon_view(
                    light_obj.data,
                    "hdri_enum",
                    show_labels=True,
                    scale_popup=6,
                    scale=7,
                )
            elif current_customization == "IES":
                col.template_icon_view(
                    light_obj.data, "ies_enum", show_labels=True, scale_popup=6, scale=7
                )

        elif current_customization == "Scrim":
            mat = bpy.data.materials.get("Scrim Preview")
            prefs = bpy.context.preferences.addons[__name__].preferences
            if (                
                bpy.context.scene.render.engine == ENGINE_CYCLES
                and prefs.use_custom_light_setup
                and prefs.show_lights_previews
                and mat
            ):
                layout.template_preview(mat, show_buttons=False)
                


                # layout.template_ID_preview(
                #     data=bpy.data.objects.get("Scrim_Preview_Plane"), 
                #     property="active_material", 
                #     new="material.new", 
                #     hide_buttons=True,
                # )


class ConvertToPlaneOperator(bpy.types.Operator):
    bl_idname = "light.convert_to_plane"
    bl_label = "Convert Gobo to Plane"
    bl_options = {"REGISTER", "UNDO"}    
    bl_description = "Convert this Gobo light to a stencil plane object"

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'LIGHT'

    def execute(self, context):
        light_obj = context.active_object
        if not light_obj:
            self.report({'WARNING'}, "No light selected")
            return {'CANCELLED'}

        image_texture_node = None
        rotation_value = 0
        invert_gobo_value = False

        if light_obj.data.use_nodes:
            for node in light_obj.data.node_tree.nodes:
                if node.type == 'GROUP':
                    if 'Rotation' in node.inputs:
                        rotation_value = node.inputs['Rotation'].default_value
                    if 'Invert Gobo' in node.inputs:
                        invert_gobo_value = node.inputs['Invert Gobo'].default_value
                    
                    for sub_node in node.node_tree.nodes:
                        if sub_node.type == 'TEX_IMAGE':
                            image_texture_node = sub_node
                            break
                    if image_texture_node:
                        break

        location = light_obj.location.copy()
        rotation = light_obj.rotation_euler.copy()
        
        # Get the actual size of the light, accounting for both intrinsic size and scaling
        if light_obj.data.type == 'AREA':
            size_x = light_obj.data.size * light_obj.scale.x
            size_y = light_obj.data.size_y * light_obj.scale.y if light_obj.data.shape == 'RECTANGLE' else light_obj.data.size * light_obj.scale.y
        else:  # For other light types, use scaling
            size_x = light_obj.scale.x
            size_y = light_obj.scale.y

        bpy.data.objects.remove(light_obj, do_unlink=True)

        # Create plane with the correct size
        bpy.ops.mesh.primitive_plane_add(size=1, location=location)
        plane = context.active_object
        plane.rotation_euler = rotation
        plane.scale = (size_x, size_y, 1)  # Set scale to match light size and scaling

        plane.name = self.generate_unique_name("Gobo Plane")

        material_name = f"{plane.name}_Material"
        new_material = bpy.data.materials.new(name=material_name)
        plane.data.materials.append(new_material)

        self.append_node_group(new_material, image_texture_node, rotation_value, invert_gobo_value)

        plane.display_type = 'TEXTURED'

        self.report({'INFO'}, f"Gobo converted to plane with material {material_name}")
        return {'FINISHED'}

    def generate_unique_name(self, base_name):
        existing_names = {obj.name for obj in bpy.data.objects if base_name in obj.name}
        count = 1
        new_name = base_name
        while new_name in existing_names:
            new_name = f"{base_name}.{str(count).zfill(3)}"
            count += 1
        return new_name

    def append_node_group(self, material, image_texture_node, rotation_value, invert_gobo_value):
        nodegroup_name = "Gobo Stencil"
        nodegroup_blend_path = os.path.join(
            os.path.dirname(__file__), "nodegroup-4.blend"
        )

        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        nodes.clear()

        with bpy.data.libraries.load(nodegroup_blend_path, link=False) as (data_from, data_to):
            if nodegroup_name in data_from.node_groups:
                data_to.node_groups = [nodegroup_name]

        if nodegroup_name in bpy.data.node_groups:
            original_node_group = bpy.data.node_groups[nodegroup_name]
            node_group = original_node_group.copy() 
            node_group.use_fake_user = False

            group_node = nodes.new(type='ShaderNodeGroup')
            group_node.node_tree = node_group
            group_node.location = (0, 0)
            group_node.width = 175 

            material_output = nodes.new(type='ShaderNodeOutputMaterial')
            material_output.location = (400, 0) 

            links.new(group_node.outputs[0], material_output.inputs['Surface'])

            if image_texture_node:
                for sub_node in group_node.node_tree.nodes:
                    if sub_node.type == 'TEX_IMAGE':
                        sub_node.image = image_texture_node.image
                        sub_node.image_user.frame_duration = image_texture_node.image_user.frame_duration
                        sub_node.image_user.frame_start = image_texture_node.image_user.frame_start
                        sub_node.image_user.frame_offset = image_texture_node.image_user.frame_offset
                        sub_node.image_user.use_auto_refresh = image_texture_node.image_user.use_auto_refresh
                        break

            if 'Rotation' in group_node.inputs:
                group_node.inputs['Rotation'].default_value = rotation_value
            if 'Invert Gobo' in group_node.inputs:
                group_node.inputs['Invert Gobo'].default_value = invert_gobo_value

            material.blend_method = 'CLIP'
            material.shadow_method = 'CLIP'




def update_light_spread(context):
    min_spread_degrees = 0.2
    max_spread_degrees = 10
    min_spread_radians = math.radians(min_spread_degrees)
    max_spread_radians = math.radians(max_spread_degrees)

    min_radius = 0.01
    max_radius = 0.3

    light = bpy.context.active_object

    if light and light.type == "LIGHT" and light.data.use_nodes:
        if light.data.type in ["AREA", "SPOT"]:
            for node in light.data.node_tree.nodes:
                if (
                    isinstance(node, bpy.types.ShaderNodeGroup)
                    and "Gobo Light" in node.node_tree.name
                ):
                    focus_node = node.inputs.get("Focus", None)
                    if focus_node:
                        focus = focus_node.default_value

                        last_focus = light.get("last_focus", None)

                        if last_focus is None or last_focus != focus:
                            try:
                                light["last_focus"] = focus
                            except Exception as e:
                                print(e)
                                return
                                 
                            if light.data.type == "AREA":
                                spread = max_spread_radians - (focus / 100) * (
                                    max_spread_radians - min_spread_radians
                                )
                                spread = max(
                                    min(spread, max_spread_radians), min_spread_radians
                                )
                                light.data.spread = spread
                            elif light.data.type == "SPOT":
                                radius = max_radius - (focus / 100) * (
                                    max_radius - min_radius
                                )
                                radius = max(min(radius, max_radius), min_radius)
                                light.data.shadow_soft_size = radius
                            break


class OpenMailOperator(bpy.types.Operator):
    bl_idname = "wm.open_mail"
    bl_label = "Open Email Client"
    bl_description = "Contact the developer to report a bug or request a feature"

    def execute(self, context):
        webbrowser.open(
            "mailto:contact@leonidaltman.com?subject=Light%20Wrangler%20Bug%20Report"
        )
        return {"FINISHED"}


class RenderScrimOperator(bpy.types.Operator):
    """Render an area light's 'Scrim' customization to an EXR file and apply it as the light's material"""
    bl_idname = "scene.render_scrim"
    bl_label = "Save as EXR"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", default="")

    @classmethod
    def poll(cls, context):
        area_light = context.active_object
        return (
            area_light
            and area_light.type == "LIGHT"
            and area_light.data.type == "AREA"
            and area_light.get("customization") == "Scrim"
        )

    def execute(self, context):
        print("Executing render...")
        print("Current filepath: ", self.filepath)

        directory = os.path.dirname(self.filepath)
        prefs = context.preferences.addons[__name__].preferences
        prefs.last_scrim_directory = directory 

        original_scene = bpy.context.window.scene
        area_light = context.active_object

        original_spread = area_light.data.spread if area_light.data.type == 'AREA' else None      
        original_energy = area_light.data.energy

        if not self.filepath:
            self.filepath = "//" + area_light.name + "_Scrim.exr"
            print("Filepath set in execute: ", self.filepath)

        tmp_scene = bpy.data.scenes.new(name="TemporaryScrimRenderScene")
        bpy.context.window.scene = tmp_scene
        tmp_scene.render.engine = "CYCLES"
        tmp_scene.cycles.samples = 1
        tmp_scene.cycles.use_denoising = False

        area_light_copy = area_light.copy()
        area_light_copy.data = area_light.data.copy()
        tmp_scene.collection.objects.link(area_light_copy)
        area_light_copy.rotation_euler = (math.radians(180), 0, 0)
        area_light_copy.visible_camera = True 
        area_light_copy.data.spread = math.radians(180)
        area_light_copy.data.energy = area_light_copy.data.energy / 2

        cam_data = bpy.data.cameras.new(name="ScrimRenderCam")
        cam_obj = bpy.data.objects.new("ScrimRenderCam", cam_data)
        tmp_scene.collection.objects.link(cam_obj)
        tmp_scene.camera = cam_obj

        cam_data.clip_start = 0.001 
        cam_data.clip_end = 1000 

        minimal_distance = 0.002
        cam_obj.location = area_light_copy.location + Vector((0, 0, minimal_distance))

        constraint = cam_obj.constraints.new(type="TRACK_TO")
        constraint.target = area_light_copy
        constraint.up_axis = "UP_Y"
        constraint.track_axis = "TRACK_NEGATIVE_Z"

        cam_data.type = "ORTHO"
        light_shape = area_light_copy.data.shape 

        if light_shape in {'SQUARE', 'DISK'}:
            aspect_ratio = 1
            effective_light_size = area_light_copy.data.size * max(area_light_copy.scale.x, area_light_copy.scale.y)
        else:
            light_size_x = area_light_copy.data.size * area_light_copy.scale.x
            light_size_y = area_light_copy.data.size_y * area_light_copy.scale.y
            effective_light_size = max(light_size_x, light_size_y)
            aspect_ratio = light_size_x / light_size_y if light_size_y != 0 else 1

        cam_data.ortho_scale = effective_light_size

        if aspect_ratio >= 1:
            tmp_scene.render.resolution_x = 2048
            tmp_scene.render.resolution_y = int(2048 / aspect_ratio)
        else:
            tmp_scene.render.resolution_x = int(2048 * aspect_ratio)
            tmp_scene.render.resolution_y = 2048


        tmp_scene.render.image_settings.file_format = 'OPEN_EXR'
        tmp_scene.render.image_settings.exr_codec = 'PXR24'
        tmp_scene.render.image_settings.color_mode = 'RGBA'
        tmp_scene.render.image_settings.color_depth = '32'

        tmp_scene.cycles.device = 'CPU'
        tmp_scene.cycles.clamp_direct = 0.0
        tmp_scene.cycles.clamp_indirect = 10000
        tmp_scene.cycles.filter_glossy = 0.0
        tmp_scene.cycles.use_auto_tile = False

        tmp_scene.render.filepath = self.filepath
        print("Render output path set to:", tmp_scene.render.filepath)
        bpy.ops.render.render(write_still=True, scene=tmp_scene.name)

        for obj in [constraint, cam_obj, cam_data, area_light_copy.data, area_light_copy, tmp_scene]:
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except:
                pass
            try:
                bpy.data.cameras.remove(obj, do_unlink=True)
            except:
                pass
            try:
                bpy.data.lights.remove(obj, do_unlink=True)
            except:
                pass
            try:
                bpy.data.scenes.remove(obj, do_unlink=True)
            except:
                pass

        bpy.context.window.scene = original_scene

        self.report({"INFO"}, f"Scrim Rendered: {self.filepath}")

        bpy.ops.light.apply_custom_data_block(light_name=area_light.name, light_type='AREA', customization='Default')

        if original_spread is not None:
            area_light.data.spread = original_spread

        area_light.data.energy = original_energy

        if not area_light.data.use_nodes:
            area_light.data.use_nodes = True
        nodes = area_light.data.node_tree.nodes
        nodes.clear() 

        if bpy.app.version >= (4, 0, 0):
            coord_node = nodes.new(type='ShaderNodeTexCoord')
            coord_output = 'UV'
        elif bpy.app.version >= (3, 0, 0):
            coord_node = nodes.new(type='ShaderNodeNewGeometry')
            coord_output = 'Parametric'
        else:
            coord_node = nodes.new(type='ShaderNodeGeometry')
            coord_output = 'Parametric'

        mapping_node = nodes.new(type='ShaderNodeMapping')
        image_texture_node = nodes.new(type='ShaderNodeTexImage')
        emission_node = nodes.new(type='ShaderNodeEmission')
        output_node = nodes.new(type='ShaderNodeOutputLight')

        image_texture_node.image = bpy.data.images.load(self.filepath)

        coord_node.location = (-600, 0)
        mapping_node.location = (-400, 0)
        image_texture_node.location = (-200, 0)
        emission_node.location = (100, 0)
        output_node.location = (400, 0)

        mapping_node.inputs['Scale'].default_value[1] = -1

        links = area_light.data.node_tree.links
        links.new(coord_node.outputs[coord_output], mapping_node.inputs['Vector'])
        links.new(mapping_node.outputs['Vector'], image_texture_node.inputs['Vector'])
        links.new(image_texture_node.outputs['Color'], emission_node.inputs['Color'])
        links.new(emission_node.outputs['Emission'], output_node.inputs['Surface'])

        self.report({"INFO"}, f"Scrim Rendered: {self.filepath}")
        return {'FINISHED'}

    def invoke(self, context, event):
        prefs = context.preferences.addons[__name__].preferences
        default_directory = prefs.last_scrim_directory if prefs.last_scrim_directory else os.path.join(os.path.expanduser("~"), "Pictures")
        
        if not os.path.exists(default_directory):
            default_directory = os.path.expanduser("~")

        if context.active_object and context.active_object.type == "LIGHT" and context.active_object.data.type == "AREA":
            self.filepath = os.path.join(default_directory, context.active_object.name + "_Scrim.exr")
        else:
            self.report({"WARNING"}, "No area light selected. Proceed to choose a file location manually.")
            self.filepath = os.path.join(default_directory, "Unnamed_Scrim.exr")

        print("Default filepath set to: ", self.filepath)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}




class HDRI_PT_RenderPanel(bpy.types.Panel):
    """Creates a Panel in the World properties window"""
    bl_label = "HDRI Scene Rendering"
    bl_idname = "WORLD_PT_hdri_render"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "world"

    @classmethod
    def poll(cls, context):
        # Check if Blender version is 4.0 or higher
        return bpy.app.version >= (4, 0, 0)

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)  # Set 'align=True' to stick buttons together

        # Buttons for different resolutions
        ops = row.operator("render.render_360_hdri", text="2K")
        ops.resolution_x = 2048
        ops.resolution_y = 1024

        ops = row.operator("render.render_360_hdri", text="4K")
        ops.resolution_x = 4096
        ops.resolution_y = 2048

        ops = row.operator("render.render_360_hdri", text="8K")
        ops.resolution_x = 8192
        ops.resolution_y = 4096

        ops = row.operator("render.render_360_hdri", text="16K")
        ops.resolution_x = 16384
        ops.resolution_y = 8192



class Render360HDROperator(bpy.types.Operator):
    """Save a 360° HDRI image of the current scene, capturing all lighting and world settings at the specified resolution"""
    bl_idname = "render.render_360_hdri"
    bl_label = "Render 360 HDRI"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH', default="")
    resolution_x: bpy.props.IntProperty(name="Width", default=2048)  # Default to 2K width
    resolution_y: bpy.props.IntProperty(name="Height", default=1024)  # Default to 2K height

    def execute(self, context):
        
        directory = os.path.dirname(self.filepath)
        prefs = context.preferences.addons[__name__].preferences
        prefs.last_360_hdri_directory = directory

        
        return self.render_hdri(context)

    def invoke(self, context, event):
        prefs = context.preferences.addons[__name__].preferences
        default_directory = prefs.last_360_hdri_directory if prefs.last_360_hdri_directory else os.path.join(os.path.expanduser("~"), "Pictures")
        
        if not os.path.exists(default_directory):
            default_directory = os.path.expanduser("~")

        resolution_map = {2048: "2K", 4096: "4K", 8192: "8K", 16384: "16K"}
        resolution_suffix = resolution_map.get(self.resolution_x, "2K")
        blend_name = bpy.path.basename(bpy.context.blend_data.filepath)
        project_name = os.path.splitext(blend_name)[0] if bpy.context.blend_data.filepath else "Untitled"
        filename = f"{project_name}_HDRI_{resolution_suffix}.hdr"
        self.filepath = os.path.join(default_directory, filename)

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def render_hdri(self, context):
        # Save the original scene
        original_scene = bpy.context.scene
        original_areas = context.window_manager.windows[0].screen.areas  # Get all areas
        
        # Initialize the original camera to None
        original_camera = None
        original_camera_view = None

        # Find the 3D Viewport and check if it's looking through a camera
        for area in original_areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        if space.region_3d.view_perspective == 'CAMERA':
                            original_camera_view = space.region_3d.view_camera_zoom
                            original_camera = space.camera  # Corrected attribute

        # Create a new empty scene
        tmp_scene = bpy.data.scenes.new("TempScene")
        bpy.context.window.scene = tmp_scene

        # Check if there is a world in the original scene and copy it if it exists
        if original_scene.world is not None:
            tmp_scene.world = original_scene.world.copy()

        # Initialize a list to track duplicated objects
        duplicated_objects = []

        # Copy only light objects from the original scene to the temporary scene
        # that are not hidden from rendering or the viewport
        for obj in original_scene.objects:
            if obj.type == 'LIGHT' and not obj.hide_render and obj.visible_get():
                new_obj = obj.copy()  # Create a duplicate
                tmp_scene.collection.objects.link(new_obj)
                duplicated_objects.append(new_obj)  # Add to the list for later cleanup


        # Setup camera for 360 rendering
        cam_data = bpy.data.cameras.new(name="360HDRICamera")
        cam_obj = bpy.data.objects.new("360HDRICamera", cam_data)
        cam_data.type = 'PANO'
        cam_data.panorama_type = 'EQUIRECTANGULAR'
        cam_data.clip_start = 0.00001
        cam_data.clip_end = 999999        

        # Link camera to the temporary scene and set as active
        tmp_scene.collection.objects.link(cam_obj)
        tmp_scene.camera = cam_obj
        cam_obj.location = original_scene.cursor.location  # Use the cursor location from the original scene

        # Set the camera rotation to face upwards
        cam_obj.rotation_euler = (math.radians(90), 0, math.radians(-90))

        # Set up the lights and rendering properties
        for obj in tmp_scene.objects:
            if obj.type == 'LIGHT':
                obj.visible_camera = True

        tmp_scene.render.resolution_x = self.resolution_x
        tmp_scene.render.resolution_y = self.resolution_y
        tmp_scene.render.image_settings.file_format = 'OPEN_EXR'
        tmp_scene.render.image_settings.exr_codec = 'PXR24'
        tmp_scene.render.image_settings.color_mode = 'RGB'
        tmp_scene.render.image_settings.color_depth = '32'
        tmp_scene.render.engine = 'CYCLES'
        tmp_scene.cycles.device = 'CPU'
        tmp_scene.cycles.samples = 1
        tmp_scene.cycles.use_denoising = False
        tmp_scene.cycles.clamp_direct = 0.0
        tmp_scene.cycles.clamp_indirect = 10000
        tmp_scene.cycles.filter_glossy = 0.0
        tmp_scene.cycles.use_auto_tile = False

        # # Adjust tile size and auto tiling based on resolution
        # if self.resolution_x == 16384:  # Check if the resolution is 16K
        #     tmp_scene.cycles.use_auto_tile = True
        #     tmp_scene.cycles.tile_size = 2048
        # else:
        #     tmp_scene.cycles.use_auto_tile = False

        # Set file path for rendering
        tmp_scene.render.filepath = self.filepath

        # Render the temporary scene
        bpy.ops.render.render(write_still=True, scene=tmp_scene.name)

        # Clean up: remove the duplicated objects, camera, and temporary world
        for obj in duplicated_objects:
            bpy.data.objects.remove(obj, do_unlink=True)  # Remove duplicated objects
        bpy.data.objects.remove(cam_obj, do_unlink=True)
        bpy.data.cameras.remove(cam_data)
        if tmp_scene.world:
            bpy.data.worlds.remove(tmp_scene.world, do_unlink=True)  # Explicitly remove the copied world

        # Delete the temporary scene and restore the original scene
        bpy.data.scenes.remove(tmp_scene)
        bpy.context.window.scene = original_scene

        # Restore the original active camera if it was set
        if original_camera:
            original_scene.camera = original_camera

        # Restore the original camera view if it was in camera view
        for area in original_areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        if original_camera_view is not None:
                            space.region_3d.view_perspective = 'CAMERA'
                            space.region_3d.view_camera_zoom = original_camera_view
                            space.camera = original_camera  # Use the correct attribute here as well
                        else:
                            space.region_3d.view_perspective = 'PERSP'

        self.report({'INFO'}, f"HDRI Rendered: {self.filepath}")
        return {'FINISHED'}



class AddEmptyAtIntersectionOperator(bpy.types.Operator):
    """Constrain selected area light(s) to a target, which may be a new or existing empty/object"""

    bl_idname = "object.add_empty_at_intersection"
    bl_label = "Track to Target"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):

        lights = [
            obj
            for obj in context.selected_objects
            if obj.type == "LIGHT"
            and obj.data.type in {"AREA", "SPOT"}
            and not obj.constraints
        ]
        others = [obj for obj in context.selected_objects if obj.type != "LIGHT"]
        return (lights and check_render_engine()) and (len(others) <= 1)

    def execute(self, context):

        lights = [
            obj
            for obj in context.selected_objects
            if obj.type == "LIGHT"
            and obj.data.type in {"AREA", "SPOT"}
            and not obj.constraints
        ]
        others = [obj for obj in context.selected_objects if obj.type != "LIGHT"]

        if len(lights) == 1 and len(others) == 0:
            self.track_to_new_empty(context, lights[0])

        elif len(lights) > 1 and len(others) == 0:
            self.track_to_new_empty(context, *lights)

        elif len(others) == 1:
            for light in lights:
                self.add_track_to_constraint(light, others[0])

        return {"FINISHED"}

    def track_to_new_empty(self, context, *lights):

        reference_light = context.active_object
        origin = reference_light.location
        direction = reference_light.rotation_euler.to_matrix() @ Vector((0, 0, -1))
        result, location, normal, index, object, matrix = context.scene.ray_cast(
            context.view_layer.depsgraph, origin, direction
        )

        if result:
            average_dimension = sum(object.dimensions) / 3
            size_cm = (
                average_dimension / 20 * bpy.context.scene.unit_settings.scale_length
            )
            size = min(max(size_cm, 0.01), 0.1)
            bpy.ops.object.empty_add(type="SPHERE", location=location, radius=size)
            empty = context.active_object

            light_index = (
                "." + reference_light.name.split(".")[-1]
                if "." in reference_light.name
                else ""
            )
            light_base_name = (
                ".".join(reference_light.name.split(".")[:-1])
                if "." in reference_light.name
                else reference_light.name
            )
            empty.name = f"{light_base_name}{light_index}_target"

            collection_name = "Lights" if len(lights) > 1 else reference_light.name
            new_collection = self.create_new_collection(context, collection_name)

            if new_collection:
                empty.name = f"{new_collection.name}_target"

            for light in lights:
                self.add_track_to_constraint(light, empty)

            self.move_to_collection(new_collection, *lights, empty)

    def add_track_to_constraint(self, light, target):
        constraint = light.constraints.new("TRACK_TO")
        constraint.target = target
        constraint.track_axis = "TRACK_NEGATIVE_Z"
        constraint.up_axis = "UP_Y"

    def create_new_collection(self, context, name):
        new_collection = bpy.data.collections.new(name=name)
        context.scene.collection.children.link(new_collection)
        return new_collection

    def move_to_collection(self, collection, *objects):
        for obj in objects:

            for col in obj.users_collection:
                col.objects.unlink(obj)

            collection.objects.link(obj)



def update_light_visibility(scene, depsgraph):
    if not bpy.context.preferences.addons[__name__].preferences.toggle_light_visibility or \
       bpy.context.scene.render.engine != "CYCLES":
        return

    compositor_used = False
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            shading = area.spaces.active.shading
            if shading.use_compositor in {'CAMERA', 'ALWAYS'}:
                compositor_used = True
                break

    if compositor_used:
        return

    for obj in (obj for obj in scene.objects if obj.type == "LIGHT"):
        if "prev_visible_camera" not in obj:
            try:
                obj["prev_visible_camera"] = obj.visible_camera
            except:
                pass

        if obj.select_get() != obj["prev_visible_camera"]:
            obj.visible_camera = obj.select_get()
            try:
                obj["prev_visible_camera"] = obj.visible_camera
            except:
                pass


class LightWranglerHintsProperties(bpy.types.PropertyGroup):
    current_mode: StringProperty(
        name="Current Mode",
        description="The currently active positioning mode",
        default="REFLECT"
    )

    show_hints: BoolProperty(
        name="Show Hints",
        description="Toggle visibility of the viewport hints",
        default=True
    )


    font_size: FloatProperty(
        name="Font Size",
        description="Base font size for the hints (will be adjusted by UI scale)",
        default=14.0,
        min=8.0,
        max=32.0
    )


class LightWranglerSettings(bpy.types.PropertyGroup):
    low_poly_threshold: bpy.props.IntProperty(
        name="Low Poly Threshold",
        default=1000,
        min=0,
        description="Threshold for considering a mesh as low poly",
    )
    scaling_factor: bpy.props.FloatProperty(
        name="Scaling Factor",
        default=2.5,
        min=0,
        description="Scaling factor for adaptive sampling",
    )
    distance_factor: bpy.props.FloatProperty(
        name="Distance Factor", default=100, min=0, description="Influence of distance"
    )
    area_factor: bpy.props.FloatProperty(
        name="Area Factor", default=1.5, min=0, description="Influence of area"
    )
    show_polygons_highlight: bpy.props.BoolProperty(
        name="Show Polygons Highlight",
        description="Toggle to enable or disable polygons highlighting in viewport",
        default=False,
    )


def calculate_normal_variance(nearest_polygons):
    normals = [p.normal for p, _, _ in nearest_polygons]
    mean_normal = sum(normals, Vector()) / len(normals)
    return sum((normal - mean_normal).length_squared for normal in normals)


def draw_text_callback(self, context):
    hints_props = context.scene.light_wrangler_hints

    if not hints_props.show_hints:
        return

    if context.area.type != 'VIEW_3D':
        return

    region = context.region
    if not (region.x < self.mouse_x < region.x + region.width and
            region.y < self.mouse_y < region.y + region.height):
        return

    viewport_width = region.width
    viewport_height = region.height

    ui_scale = context.preferences.system.ui_scale
    base_ui_scale = 1.25
    scale_factor = ui_scale / base_ui_scale

    min_width = 350 * scale_factor
    min_height = 780 * scale_factor

    if viewport_width < min_width:
        return

    font_id = 0

    theme = context.preferences.themes[0]
    default_text_color = theme.view_3d.space.text_hi
    highlight_color = theme.view_3d.object_active

    margin_x = 0 * scale_factor
    margin_y = 78 * scale_factor
    font_size = int(14 * scale_factor)  # Original font size
    line_spacing = font_size * 1.7

    base_x = margin_x
    base_y = margin_y  # Keep at bottom

    blf.color(font_id, default_text_color[0], default_text_color[1], default_text_color[2], 0.7)
    blf.size(font_id, font_size)

    current_time = time.time()
    highlight_duration = 0.2

    def calculate_block_height(num_items):
        return num_items * line_spacing + font_size

    light_control_hints_height = calculate_block_height(len(light_control_hints))
    navigation_hints_height = calculate_block_height(len(navigation_hints))

    if viewport_height >= min_height:
        show_light_control_hints = True
        show_mode_hints = True
        show_navigation_hints = True
    elif viewport_height >= min_height - light_control_hints_height:
        show_light_control_hints = False
        show_mode_hints = True
        show_navigation_hints = True
    elif viewport_height >= min_height - light_control_hints_height - navigation_hints_height:
        show_light_control_hints = False
        show_mode_hints = True
        show_navigation_hints = False
    else:
        return

    def draw_hint(key, description, value=None, unit='', is_active=False, is_toggle=False):
        nonlocal current_y

        # Shadow color and offset
        shadow_color = (0, 0, 0, 0.9)  
        shadow_offset = 0.75 * scale_factor  

        if is_active:
            current_text_color = (highlight_color[0], highlight_color[1], highlight_color[2], 1.0)
        else:
            current_text_color = (0.9, 0.9, 0.9, 1.0)  

        key_width = 80 * scale_factor
        description_x = base_x + key_width + 10 * scale_factor

        # Right-justify the key
        key_dimensions = blf.dimensions(font_id, key)
        key_x = base_x + key_width - key_dimensions[0]

        # Draw key shadow
        blf.color(font_id, *shadow_color)
        blf.position(font_id, key_x + shadow_offset, current_y - shadow_offset, 0)
        blf.draw(font_id, key)

        # Draw key text
        blf.color(font_id, *current_text_color)
        blf.position(font_id, key_x, current_y, 0)
        blf.draw(font_id, key)

        # Prepare description text
        if value is not None:
            if description == "Spread" or description == "Spot Size":
                text = f"{description} {int(value)}°"
            elif unit == 'W':
                text = f"{description} {value:.1f} {unit}"
            elif unit in ['m', 'cm', 'mm', 'km']:
                if unit == 'mm':
                    text = f"{description} {int(value)} {unit}"
                elif unit == 'cm':
                    text = f"{description} {int(value)} {unit}"
                elif unit == 'm':
                    text = f"{description} {value:.1f} {unit}"
                else:
                    text = f"{description} {value:.2f} {unit}"
            elif unit == '"':
                text = f"{description} {int(value)}{unit}"
            elif unit == "'":
                text = f"{description} {value:.1f}{unit}"
            else:
                text = f"{description} {value:.2f}{unit}"
        else:
            text = description

        if is_toggle and is_active:
            text += " Active"

        # Draw description shadow
        blf.color(font_id, *shadow_color)
        blf.position(font_id, description_x + shadow_offset, current_y - shadow_offset, 0)
        blf.draw(font_id, text)

        # Draw description text
        blf.color(font_id, *current_text_color)
        blf.position(font_id, description_x, current_y, 0)
        blf.draw(font_id, text)

        current_y += line_spacing

    def convert_to_user_units(value, unit_system, unit_scale):
        if unit_system == 'METRIC':
            if unit_scale == 'KILOMETERS':
                return value / 1000, 'km'
            elif unit_scale == 'METERS':
                return value, 'm'
            elif unit_scale == 'CENTIMETERS':
                return value * 100, 'cm'
            elif unit_scale == 'MILLIMETERS':
                return value * 1000, 'mm'
        elif unit_system == 'IMPERIAL':
            if unit_scale == 'MILES':
                return value / 1609.34, 'mi'
            elif unit_scale == 'FEET':
                return value * 3.28084, "'"
            elif unit_scale == 'INCHES':
                return value * 39.3701, '"'
            elif unit_scale == 'THOU':
                return int(value * 39370.1), 'thou'
        return value, ''  # Default case

    if bpy.context.preferences.addons[__name__].preferences.draw_viewport_hints:
        current_y = base_y

        unit_settings = context.scene.unit_settings
        unit_system = unit_settings.system
        unit_scale = unit_settings.length_unit

        if show_light_control_hints:
            for key, description in reversed(light_control_hints):
                is_active = False
                is_toggle = False

                if description == "Hide Light":
                    is_active = self.light.hide_viewport
                    is_toggle = True
                elif description == "Isolate Light":
                    is_active = self.is_isolated
                    is_toggle = True
                else:
                    last_activation = last_activation_time.get(description, 0)
                    is_active = (current_time - last_activation) < highlight_duration

                draw_hint(key, description, is_active=is_active, is_toggle=is_toggle)

            current_y += font_size

        if show_mode_hints:
            active_mode = hints_props.current_mode
            for key, description in reversed(mode_hints):
                is_active = ((active_mode == 'reflect' and key == "1") or
                            (active_mode == 'orbit' and key == "2") or
                            (active_mode == 'direct' and key == "3"))
                draw_hint(key, description, is_active=is_active)

            current_y += font_size

        if show_navigation_hints:
            for key, original_description in reversed(navigation_hints):
                last_activation = last_activation_time.get(original_description, 0)
                time_since_activation = current_time - last_activation

                description = original_description
                value = None
                unit = ''

                if hasattr(self, 'light'):
                    light_type = self.light.data.type

                    if original_description == "Power" and hasattr(self.light.data, 'energy'):
                        value = self.light.data.energy
                        unit = 'W'
                    elif original_description == "Size":
                        if light_type == "SPOT":
                            value = math.degrees(self.light.data.spot_size)
                            description = "Spot Size"
                        elif light_type == "AREA" and hasattr(self.light.data, 'size'):
                            value, unit = convert_to_user_units(self.light.data.size, unit_system, unit_scale)
                            description = "Size"
                    elif original_description == "Distance" and "current_proximity" in self.light:
                        value, unit = convert_to_user_units(self.light["current_proximity"], unit_system, unit_scale)
                        description = "Distance"
                    elif original_description == "Spread":
                        if light_type == "SPOT":
                            value = self.light.data.spot_blend
                            description = "Blend"
                        elif light_type == "AREA" and hasattr(self.light.data, 'spread'):
                            value = math.degrees(self.light.data.spread)

                is_active = time_since_activation < highlight_duration
                draw_hint(key, description, value, unit, is_active)

    else:
        pass
    
class CopyAndAdjustLightOperator(bpy.types.Operator):
    """Copy selected light and trigger light adjust operator"""

    bl_idname = "object.copy_and_adjust_light"
    bl_label = "Copy and Adjust Light"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        selected_lights = [
            obj for obj in context.selected_objects if obj.type == "LIGHT"
        ]
        valid_light_types = {"AREA", "SPOT"}
        return (
            len(selected_lights) == 1
            and context.mode == "OBJECT"
            and context.active_object
            and context.active_object.type == "LIGHT"
            and context.active_object.data.type in valid_light_types
            and not context.active_object.constraints
            and check_render_engine()
        )

    def execute(self, context):
        global duplicate_case
        duplicate_case = True
        bpy.ops.object.duplicate_move()
        copied_light = context.active_object

        global AdjustingLight
        AdjustingLight = copied_light
        bpy.ops.object.adjust_light_position("INVOKE_DEFAULT")

        return {"FINISHED"}


def dynamic_adjust_tooltip(context):
    default_tooltip = "Interactively adjust light position"

    if context.active_object and "light_adjust_mode" in context.active_object:
        light_adjust_mode = context.active_object["light_adjust_mode"]
        if light_adjust_mode == "reflect":
            return "Tab to activate Reflect mode"
        elif light_adjust_mode == "orbit":
            return "Tab to activate Orbit mode"
        elif light_adjust_mode == "direct":
            return "Tab to activate Direct mode"
    return default_tooltip


class AdjustLightPositionOperator(bpy.types.Operator):
    """Tab to activate Reflect mode"""

    bl_idname = "object.adjust_light_position"
    bl_label = "Adjust Light"
    bl_options = {"REGISTER", "UNDO"}

    key_identifier_dum: bpy.props.StringProperty(options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        valid_light_types = {"AREA", "SPOT"}
        return (
            context.mode == "OBJECT"
            and context.active_object
            and context.active_object.type == "LIGHT"
            and context.active_object.data.type in valid_light_types
            and not context.active_object.constraints
            and check_render_engine()
        )

    def execute(self, context):

        light = context.active_object
        if light:
            global AdjustingLight
            AdjustingLight = light

            light_type = light.data.type
            original_properties = {
                "location": list(light.location),
                "energy": float(light.data.energy),
                "rotation": list(light.rotation_euler),
            }

            if "current_proximity" not in light:
                light["current_proximity"] = context.preferences.addons[
                    __name__
                ].preferences.initial_light_distance

            if "last_hit_location" in light:
                light["current_proximity"] = (
                    light.location - Vector(light["last_hit_location"])
                ).length

            light["start_proximity"] = light["current_proximity"]

            if light_type == "AREA":
                original_properties.update(
                    {
                        "shape": light.data.shape,
                        "size_y": float(light.data.size_y),
                        "size": float(light.data.size),
                        "spread": float(light.data.spread),
                    }
                )
            elif light_type == "SPOT":
                original_properties.update(
                    {
                        "size": float(light.data.spot_size),
                        "spread": float(light.data.spot_blend),
                    }
                )

            light["original_properties"] = original_properties
            global KEY_IDENTIFIER
            KEY_IDENTIFIER = "ONE"

            bpy.ops.object.light_at_point("INVOKE_DEFAULT")

        return {"FINISHED"}


class Two_AdjustLightPositionOperator(bpy.types.Operator):
    """Tab to activate Orbit mode"""

    bl_idname = "object.two_adjust_light_position"
    bl_label = "Adjust Light"
    bl_options = {"REGISTER", "UNDO"}

    key_identifier_dum: bpy.props.StringProperty(options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        valid_light_types = {"AREA", "SPOT"}
        return (
            context.mode == "OBJECT"
            and context.active_object
            and context.active_object.type == "LIGHT"
            and context.active_object.data.type in valid_light_types
            and not context.active_object.constraints
            and check_render_engine()
        )

    def execute(self, context):

        light = context.active_object
        if light:
            global AdjustingLight
            AdjustingLight = light

            light_type = light.data.type
            original_properties = {
                "location": list(light.location),
                "energy": float(light.data.energy),
                "rotation": list(light.rotation_euler),
            }

            if "current_proximity" not in light:
                light["current_proximity"] = context.preferences.addons[
                    __name__
                ].preferences.initial_light_distance

            if "last_hit_location" in light:
                light["current_proximity"] = (
                    light.location - Vector(light["last_hit_location"])
                ).length

            try:
                light["start_proximity"] = light["current_proximity"]
            except Exception as e:
                print(f"Failed to set start_proximity property: {e}")

            if light_type == "AREA":
                original_properties.update(
                    {
                        "shape": light.data.shape,
                        "size_y": float(light.data.size_y),
                        "size": float(light.data.size),
                        "spread": float(light.data.spread),
                    }
                )
            elif light_type == "SPOT":
                original_properties.update(
                    {
                        "size": float(light.data.spot_size),
                        "spread": float(light.data.spot_blend),
                    }
                )

            try:
                light["original_properties"] = original_properties
            except Exception as e:
                print(f"Failed to set original_properties property: {e}")
            global KEY_IDENTIFIER
            KEY_IDENTIFIER = "TWO"

            bpy.ops.object.light_at_point("INVOKE_DEFAULT")

        return {"FINISHED"}


class Three_AdjustLightPositionOperator(bpy.types.Operator):
    """Tab to activate Direct mode"""

    bl_idname = "object.three_adjust_light_position"
    bl_label = "Adjust Light"
    bl_options = {"REGISTER", "UNDO"}

    key_identifier_dum: bpy.props.StringProperty(options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        valid_light_types = {"AREA", "SPOT"}
        return (
            context.mode == "OBJECT"
            and context.active_object
            and context.active_object.type == "LIGHT"
            and context.active_object.data.type in valid_light_types
            and not context.active_object.constraints
            and check_render_engine()
        )

    def execute(self, context):

        light = context.active_object
        if light:
            global AdjustingLight
            AdjustingLight = light

            light_type = light.data.type
            original_properties = {
                "location": list(light.location),
                "energy": float(light.data.energy),
                "rotation": list(light.rotation_euler),
            }

            if "current_proximity" not in light:
                light["current_proximity"] = context.preferences.addons[
                    __name__
                ].preferences.initial_light_distance

            if "last_hit_location" in light:
                light["current_proximity"] = (
                    light.location - Vector(light["last_hit_location"])
                ).length

            light["start_proximity"] = light["current_proximity"]

            if light_type == "AREA":
                original_properties.update(
                    {
                        "shape": light.data.shape,
                        "size_y": float(light.data.size_y),
                        "size": float(light.data.size),
                        "spread": float(light.data.spread),
                    }
                )
            elif light_type == "SPOT":
                original_properties.update(
                    {
                        "size": float(light.data.spot_size),
                        "spread": float(light.data.spot_blend),
                    }
                )

            light["original_properties"] = original_properties
            global KEY_IDENTIFIER
            KEY_IDENTIFIER = "THREE"

            bpy.ops.object.light_at_point("INVOKE_DEFAULT")

        return {"FINISHED"}


class TabAdjustLightPositionOperator(bpy.types.Operator):
    """Interactively adjust light position"""

    bl_idname = "object.tab_adjust_light_position"
    bl_label = "Tab Adjust Light"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        valid_light_types = {"AREA", "SPOT"}
        return (
            context.mode == "OBJECT"
            and context.active_object
            and context.active_object.type == "LIGHT"
            and context.active_object.data.type in valid_light_types
            and not context.active_object.constraints
            and check_render_engine()
        )

    def execute(self, context):

        light = context.active_object
        if light:
            global AdjustingLight
            AdjustingLight = light

            light_type = light.data.type
            original_properties = {
                "location": list(light.location),
                "energy": float(light.data.energy),
                "rotation": list(light.rotation_euler),
            }

            if "current_proximity" not in light:
                light["current_proximity"] = context.preferences.addons[
                    __name__
                ].preferences.initial_light_distance

            if "last_hit_location" in light:
                light["current_proximity"] = (
                    light.location - Vector(light["last_hit_location"])
                ).length

            light["start_proximity"] = light["current_proximity"]

            if light_type == "AREA":
                original_properties.update(
                    {
                        "shape": light.data.shape,
                        "size_y": float(light.data.size_y),
                        "size": float(light.data.size),
                        "spread": float(light.data.spread),
                    }
                )
            elif light_type == "SPOT":
                original_properties.update(
                    {
                        "size": float(light.data.spot_size),
                        "spread": float(light.data.spot_blend),
                    }
                )

            light["original_properties"] = original_properties

            global KEY_IDENTIFIER
            KEY_IDENTIFIER = "TAB"
            bpy.ops.object.light_at_point("INVOKE_DEFAULT")

        return {"FINISHED"}


def append_gobo_node_group():
    nodegroup_name = "Gobo Light"
    blender_version = bpy.app.version
    if blender_version[0] >= 4:
        nodegroup_blend_path = os.path.join(
            os.path.dirname(__file__), "nodegroup-4.blend"
        )
    else:
        nodegroup_blend_path = os.path.join(
            os.path.dirname(__file__), "nodegroup.blend"
        )

    if nodegroup_name not in bpy.data.node_groups:
        with bpy.data.libraries.load(nodegroup_blend_path, link=False) as (
            data_from,
            data_to,
        ):
            if nodegroup_name in data_from.node_groups:
                data_to.node_groups = [nodegroup_name]


def append_hdri_node_group():
    nodegroup_name = "HDRI Light"
    blender_version = bpy.app.version
    if blender_version[0] >= 4:
        nodegroup_blend_path = os.path.join(
            os.path.dirname(__file__), "nodegroup-4.blend"
        )
    else:
        nodegroup_blend_path = os.path.join(
            os.path.dirname(__file__), "nodegroup.blend"
        )

    if nodegroup_name not in bpy.data.node_groups:
        with bpy.data.libraries.load(nodegroup_blend_path, link=False) as (
            data_from,
            data_to,
        ):
            if nodegroup_name in data_from.node_groups:
                data_to.node_groups = [nodegroup_name]


def append_ies_node_group():
    nodegroup_name = "IES Light"
    blender_version = bpy.app.version
    if blender_version[0] >= 4:
        nodegroup_blend_path = os.path.join(
            os.path.dirname(__file__), "nodegroup-4.blend"
        )
    else:
        nodegroup_blend_path = os.path.join(
            os.path.dirname(__file__), "nodegroup.blend"
        )

    if nodegroup_name not in bpy.data.node_groups:
        with bpy.data.libraries.load(nodegroup_blend_path, link=False) as (
            data_from,
            data_to,
        ):
            if nodegroup_name in data_from.node_groups:
                data_to.node_groups = [nodegroup_name]


def append_scrim_node_group():

    nodegroup_name = "Scrim Light"
    blender_version = bpy.app.version
    if blender_version[0] >= 4:
        nodegroup_blend_path = os.path.join(
            os.path.dirname(__file__), "nodegroup-4.blend"
        )
    else:
        nodegroup_blend_path = os.path.join(
            os.path.dirname(__file__), "nodegroup.blend"
        )

    if nodegroup_name not in bpy.data.node_groups:

        with bpy.data.libraries.load(nodegroup_blend_path, link=False) as (
            data_from,
            data_to,
        ):
            if nodegroup_name in data_from.node_groups:
                data_to.node_groups = [nodegroup_name]
                print(f"Node group '{nodegroup_name}' loaded successfully.")
            else:
                print(f"Node group '{nodegroup_name}' not found in the blend file.")


def is_video_file(file_path):

    video_extensions = [
        ".mp4",
        ".m4v",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".mkv",
        ".webm",
        ".ogv",
    ]
    return any(file_path.lower().endswith(ext) for ext in video_extensions)


def apply_gobo_to_light(light, gobo_name):
    print(f"Applying gobo: {gobo_name}")
    append_gobo_node_group()

    if not light.data.use_nodes:
        light.data.use_nodes = True

    nodes = light.data.node_tree.nodes

    gobo_node_group = None
    for node in nodes:
        if node.type == "GROUP" and node.node_tree and "Gobo Light" in node.node_tree.name:
            gobo_node_group = node
            break

    if gobo_node_group is None:
        for node in nodes:
            nodes.remove(node)

        base_node_group = bpy.data.node_groups["Gobo Light"]
        node_group = base_node_group.copy()
        node_group.name = f"Gobo Light {light.name}"

        gobo_node_group = nodes.new(type="ShaderNodeGroup")
        gobo_node_group.node_tree = node_group
        gobo_node_group.location = (0, 0)
        gobo_node_group.width = 175

        light_output_node = nodes.new(type="ShaderNodeOutputLight")
        light_output_node.location = (400, 0)
        links = light.data.node_tree.links
        links.new(light_output_node.inputs["Surface"], gobo_node_group.outputs["Emission"])
        apply_initial_color_temp_global(light.data)
    else:
        # Ensure each light has its own unique node group
        if gobo_node_group.node_tree.users > 1:
            new_node_group = gobo_node_group.node_tree.copy()
            new_node_group.name = f"Gobo Light {light.name}"
            gobo_node_group.node_tree = new_node_group
        node_group = gobo_node_group.node_tree

    possible_extensions = [
        ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp",
        ".gif", ".psd", ".exr", ".hdr", ".svg", ".mp4", 
        ".m4v", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm", ".ogv"
    ]

    gobo_image_path = None
    searched_paths = []

    if gobo_name.startswith("user:"):
        print("Searching for custom gobo")
        addon_prefs = bpy.context.preferences.addons[__name__].preferences
        custom_folder_paths = [addon_prefs.gobo_path, addon_prefs.gobo_path_2, addon_prefs.gobo_path_3]
        
        # Remove the "_thumb.png" suffix if present for custom gobos
        if gobo_name.endswith("_thumb.png"):
            gobo_name = gobo_name[:-10]  # Remove last 10 characters ("_thumb.png")
        
        for folder_path in custom_folder_paths:
            if folder_path:
                test_path = os.path.join(folder_path, gobo_name[5:])
                searched_paths.append(test_path)
                if os.path.exists(test_path):
                    gobo_image_path = test_path
                    print(f"Found custom gobo at: {gobo_image_path}")
                    break
                else:
                    for ext in possible_extensions:
                        test_path_with_ext = test_path + ext
                        searched_paths.append(test_path_with_ext)
                        if os.path.exists(test_path_with_ext):
                            gobo_image_path = test_path_with_ext
                            print(f"Found custom gobo at: {gobo_image_path}")
                            break
                if gobo_image_path:
                    break
    else:
        print("Searching for built-in gobo")
        gobo_name_no_ext = os.path.splitext(gobo_name)[0]
        base_path = os.path.join(os.path.dirname(__file__), "gobo_textures", gobo_name_no_ext)
        for ext in possible_extensions:
            test_path = base_path + ext
            searched_paths.append(test_path)
            if os.path.exists(test_path):
                gobo_image_path = test_path
                print(f"Found built-in gobo at: {gobo_image_path}")
                break

    if gobo_image_path:
        for node in gobo_node_group.node_tree.nodes:
            if node.type == "TEX_IMAGE":
                try:
                    node.image = bpy.data.images.load(gobo_image_path, check_existing=True)
                    node.image.colorspace_settings.name = "sRGB"
                    print(f"Image loaded: {node.image.name}")
                    if is_video_file(gobo_image_path): 
                        node.image_user.frame_duration = node.image.frame_duration
                        node.image_user.use_cyclic = True
                        node.image_user.use_auto_refresh = True
                except Exception as e:
                    print(f"Error loading image: {e}")
                    print(f"Attempted to load from path: {gobo_image_path}")
                break
    else:
        print("Gobo image path does not exist for any known extension")
        print(f"Gobo name: {gobo_name}")
        print(f"Searched paths:")
        for path in searched_paths:
            print(f"  - {path}")

    print(f"Final gobo_image_path: {gobo_image_path}")

def apply_initial_color_temp_global(light_data_block):
    if light_data_block.use_nodes:

        addon_prefs = bpy.context.preferences.addons[__name__].preferences
        initial_light_temp = addon_prefs.initial_light_temp
        for node in light_data_block.node_tree.nodes:
            if "ColorTemp" in node.inputs:
                node.inputs["ColorTemp"].default_value = initial_light_temp
                break


def apply_hdri_to_light(light, hdri_name):
    # print(f"Received HDRI name: {hdri_name}")
    append_hdri_node_group()

    if not light.data.use_nodes:
        light.data.use_nodes = True

    nodes = light.data.node_tree.nodes

    hdri_node_group = None
    for node in nodes:
        if node.type == "GROUP" and node.node_tree and "HDRI Light" in node.node_tree.name:
            hdri_node_group = node
            break

    if hdri_node_group is None:
        for node in nodes:
            nodes.remove(node)

        base_node_group = bpy.data.node_groups["HDRI Light"]
        node_group = base_node_group.copy()
        node_group.name = f"HDRI Light {light.name}"

        hdri_node_group = nodes.new(type="ShaderNodeGroup")
        hdri_node_group.node_tree = node_group
        hdri_node_group.location = (0, 0)
        hdri_node_group.width = 175

        light_output_node = nodes.new(type="ShaderNodeOutputLight")
        light_output_node.location = (400, 0)
        links = light.data.node_tree.links
        links.new(
            light_output_node.inputs["Surface"], hdri_node_group.outputs["Emission"]
        )

        apply_initial_color_temp_global(light.data)
    else:
        # Ensure each light has its own unique node group
        if hdri_node_group.node_tree.users > 1:
            new_node_group = hdri_node_group.node_tree.copy()
            new_node_group.name = f"HDRI Light {light.name}"
            hdri_node_group.node_tree = new_node_group
        node_group = hdri_node_group.node_tree

    possible_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".tiff",
        ".tif",
        ".gif",
        ".psd",
        ".exr",
        ".hdr",
        ".svg",
        ".mp4",
        ".m4v",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".mkv",
        ".webm",
        ".ogv",
        ".webp",
    ]
    # print(f"Attempting to apply HDRI: {hdri_name}")
    if hdri_name.startswith("user:"):
        hdri_image_path = hdri_name[5:]
        # print(f"Custom HDRI image path: {hdri_image_path}")
    else:
        hdri_name_no_ext = os.path.splitext(hdri_name)[0]
        base_path = os.path.join(
            os.path.dirname(__file__), "hdri_textures", hdri_name_no_ext
        )
        hdri_image_path = None
        for ext in possible_extensions:
            test_path = base_path + ext
            if os.path.exists(test_path):
                hdri_image_path = test_path
                break

    if hdri_image_path:
        for node in hdri_node_group.node_tree.nodes:
            if node.type == "TEX_IMAGE":
                try:
                    node.image = bpy.data.images.load(
                        hdri_image_path, check_existing=True
                    )
                    # print("HDRI loaded:", node.image.name)
                    if is_video_file(hdri_image_path):
                        node.image_user.frame_duration = node.image.frame_duration
                        node.image_user.use_cyclic = True
                        node.image_user.use_auto_refresh = True
                except Exception as e:
                    print(f"Error loading image: {e}")
                break
    else:
        print("HDRI image path does not exist for any known extension")
        print(f"HDRI image path: {hdri_image_path}")

    spread_value = None
    match = re.search(r"spread(\d+)", hdri_name)
    if match:
        spread_value = int(match.group(1))
    else:

        addon_prefs = bpy.context.preferences.addons[__name__].preferences
        spread_value = addon_prefs.initial_light_spread_deg

    if spread_value is not None:
        light.data.spread = math.radians(spread_value)
        print(f"Light spread set to {spread_value} degrees.")
    else:
        print("Using default spread value for light.")


def apply_ies_to_light(light, ies_name):
    append_ies_node_group()

    light.data.shadow_soft_size = 0

    if not light.data.use_nodes:
        light.data.use_nodes = True
    nodes = light.data.node_tree.nodes

    ies_node_group = None
    for node in nodes:
        if node.type == "GROUP" and node.node_tree and "IES Light" in node.node_tree.name:
            ies_node_group = node
            break

    if ies_node_group is None:
        for node in nodes:
            nodes.remove(node)

        base_node_group = bpy.data.node_groups["IES Light"]
        node_group = base_node_group.copy()
        node_group.name = f"IES Light {light.name}"

        ies_node_group = nodes.new(type="ShaderNodeGroup")
        ies_node_group.node_tree = node_group
        ies_node_group.location = (0, 0)
        ies_node_group.width = 175

        light_output_node = nodes.new(type="ShaderNodeOutputLight")
        light_output_node.location = (400, 0)
        links = light.data.node_tree.links
        links.new(
            light_output_node.inputs["Surface"], ies_node_group.outputs["Emission"]
        )

        apply_initial_color_temp_global(light.data)
    else:
        # Ensure each light has its own unique node group
        if ies_node_group.node_tree.users > 1:
            new_node_group = ies_node_group.node_tree.copy()
            new_node_group.name = f"IES Light {light.name}"
            ies_node_group.node_tree = new_node_group
        node_group = ies_node_group.node_tree

    ies_filepath = None
    if ies_name.startswith("user:"):
        addon_prefs = bpy.context.preferences.addons[__name__].preferences
        if addon_prefs.ies_profiles_path:
            ies_filepath = os.path.join(addon_prefs.ies_profiles_path, ies_name[5:])
    elif ies_name.startswith("builtin:"):
        ies_name_no_prefix = ies_name[8:]  # Remove "builtin:" prefix
        ies_name_no_ext = os.path.splitext(ies_name_no_prefix)[0]
        base_path = os.path.join(os.path.dirname(__file__), "ies_profiles", ies_name_no_ext)
        ies_filepath = base_path + ".ies"
    else:
        print(f"Unexpected IES name format: {ies_name}")
        return

    if ies_filepath and os.path.exists(ies_filepath):
        print("IES file exists:", ies_filepath)
        shader_node_ies = None
        for node in ies_node_group.node_tree.nodes:
            if node.type == "TEX_IES":
                shader_node_ies = node
                break

        if shader_node_ies:
            try:
                shader_node_ies.filepath = ies_filepath
                shader_node_ies.mode = "EXTERNAL"
                print(
                    "IES file set to ShaderNodeTexIES node:", shader_node_ies.filepath
                )
                print("Mode set to:", shader_node_ies.mode)
            except Exception as e:
                print(f"Error setting IES file to ShaderNodeTexIES node: {e}")
        else:
            print("No ShaderNodeTexIES node found in the group.")
    else:
        print("IES file does not exist:", ies_filepath)


def apply_scrim_to_light(light_data_block):

    append_scrim_node_group()

    if not light_data_block.use_nodes:
        light_data_block.use_nodes = True

    nodes = light_data_block.node_tree.nodes

    for node in nodes:

        nodes.remove(node)

    base_node_group = bpy.data.node_groups["Scrim Light"]
    unique_node_group_name = f"Scrim Light {bpy.context.object.name}"

    if unique_node_group_name not in bpy.data.node_groups:
        node_group = base_node_group.copy()
        node_group.name = unique_node_group_name

    else:
        node_group = bpy.data.node_groups[unique_node_group_name]

    group_node = nodes.new(type="ShaderNodeGroup")
    group_node.node_tree = node_group
    group_node.location = (0, 0)
    group_node.width = 175

    light_output_node = nodes.new(type="ShaderNodeOutputLight")
    light_output_node.location = (400, 0)

    links = light_data_block.node_tree.links
    links.new(light_output_node.inputs["Surface"], group_node.outputs["Emission"])


def use_default_light(light):
    if not light.data.use_nodes:
        light.data.use_nodes = True
    nodes = light.data.node_tree.nodes

    for node in nodes:
        nodes.remove(node)

    emission_node = nodes.new(type="ShaderNodeEmission")
    emission_node.location = (0, 0)

    light_output_node = nodes.new(type="ShaderNodeOutputLight")
    light_output_node.location = (200, 0)

    links = light.data.node_tree.links
    links.new(emission_node.outputs["Emission"], light_output_node.inputs["Surface"])


class ProxyLightAtPointOperator(bpy.types.Operator):
    """Auto-places light to illuminate area under mouse cursor"""

    bl_idname = "object.proxy_light_at_point"
    bl_label = "Auto-places light to illuminate area under mouse cursor"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return check_render_engine()

    def execute(self, context):
        bpy.ops.object.light_at_point("INVOKE_DEFAULT")
        return {"FINISHED"}


def create_or_delete_sphere_empty(self, context, create):
    if create:

        direction = self.light.rotation_euler.to_matrix() @ Vector((0, 0, -1))

        result, location, normal, index, object, matrix = context.scene.ray_cast(
            context.view_layer.depsgraph, self.light.location, direction
        )
        size = 1
        if result:
            average_dimension = sum(object.dimensions) / 3
            size_cm = (
                average_dimension / 20 * bpy.context.scene.unit_settings.scale_length
            )
            size = min(max(size_cm, 0.03), 0.1)

        current_active_object = bpy.context.active_object

        bpy.ops.object.empty_add(type="SPHERE", location=self.orbit_center)
        sphere_empty = bpy.context.active_object
        sphere_empty.name = "Gizmo"
        sphere_empty.scale *= size


        self.sphere_empty_name = sphere_empty.name

        light_collections = self.light.users_collection
        if light_collections:
            target_collection = light_collections[0]
            if sphere_empty.name not in target_collection.objects:
                target_collection.objects.link(sphere_empty)
            for collection in sphere_empty.users_collection:
                if collection != target_collection:
                    collection.objects.unlink(sphere_empty)

        bpy.context.view_layer.objects.active = current_active_object
        if current_active_object: 
            current_active_object.select_set(True)

        rot_quat = direction.to_track_quat("Z", "Y")
        sphere_empty.rotation_euler = rot_quat.to_euler()
        self.sphere_empty_name = sphere_empty.name        

    else:

        sphere_empty = bpy.data.objects.get(self.sphere_empty_name, None)
        if sphere_empty:
            bpy.data.objects.remove(sphere_empty, do_unlink=True)


def purge_orphans():

    orphan_lights = [light for light in bpy.data.lights if light.users == 0]
    for light in orphan_lights:

        bpy.data.lights.remove(light)

    orphan_node_groups = [group for group in bpy.data.node_groups if group.users == 0]
    for group in orphan_node_groups:

        bpy.data.node_groups.remove(group)


def is_orthographic_view(context):
    region_3d = context.space_data.region_3d

    if region_3d.view_perspective == "ORTHO":
        return True
    elif region_3d.view_perspective == "CAMERA":
        camera = context.scene.camera
        if camera and camera.data.type == "ORTHO":
            return True
    return False


original_visibility_states = {}


def hide_viewport_elements(context):
    global original_visibility_states

    original_visibility_states = {}

    overlay_attributes = [
        "show_relationship_lines",
        "show_floor",
        "show_cursor",
        "show_axis_x",
        "show_axis_y",
        "show_axis_z",
        "show_face_orientation",
        "show_wireframes",
        "show_object_origins_all",
        "show_outline_selected",
        "show_motion_paths",
        "show_bones",
        "show_stats",
        "show_text",
        "show_annotation",
    ]

    gizmo_attributes = [
        "show_gizmo",
        "show_gizmo_context",
        "show_gizmo_tool",
        "show_gizmo_object_rotate",
        "show_gizmo_object_translate",
        "show_gizmo_object_scale",
        "show_gizmo_navigate",
    ]

    for attr in overlay_attributes:
        if hasattr(context.space_data.overlay, attr):
            original_visibility_states[attr] = getattr(context.space_data.overlay, attr)
            setattr(context.space_data.overlay, attr, False)

    for attr in gizmo_attributes:
        if hasattr(context.space_data, attr):
            original_visibility_states[attr] = getattr(context.space_data, attr)

            if attr == "show_gizmo":
                setattr(context.space_data, attr, True)
            else:
                setattr(context.space_data, attr, False)


def unhide_viewport_elements(context):
    global original_visibility_states

    for attr, value in original_visibility_states.items():
        if attr in original_visibility_states:
            if attr in [
                "show_gizmo",
                "show_gizmo_context",
                "show_gizmo_tool",
                "show_gizmo_object_rotate",
                "show_gizmo_object_translate",
                "show_gizmo_object_scale",
                "show_gizmo_navigate",
            ]:

                if hasattr(context.space_data, attr):
                    setattr(context.space_data, attr, value)
            else:

                if hasattr(context.space_data.overlay, attr):
                    setattr(context.space_data.overlay, attr, value)

    original_visibility_states.clear()




class LightAtPointOperator(bpy.types.Operator):
    """Auto-places light to illuminate area under mouse cursor"""

    bl_idname = "object.light_at_point"
    bl_label = "Auto-places light to illuminate area under mouse cursor"
    bl_options = {"REGISTER", "UNDO", "GRAB_CURSOR", "BLOCKING"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and check_render_engine()

    num_faces = 16
    max_size = 1.37
    min_size = 0.1


    def __init__(self):
        purge_orphans()

        self.initial_target = None  # Add this line to store initial target

        self.trackpad_sensitivity = 0.1 
        self.mouse_x = 0
        self.mouse_y = 0

        self.bm = None
        self.last_object = None
        self.bvh_tree = None

        max_positions = 80
        self.max_positions = max_positions
        self.position_history = []
        self.weights = np.exp(np.linspace(0, 1, max_positions))
        self.weights /= np.sum(self.weights)

        self.distance = 0
        self.is_isolated = False
        self.is_hidden = False
        
        self.left_mouse_hold = False
        self.lerp_factor = 1
        self.paused = False
        self.saved_mode = None
        self.sphere_empty_name = None
        self._handle = None
        self.last_mouse_pos = None
        self.last_update_time = time.time()
        self.mouse_on_object = None
        
        self.avg_speed = 0
        self.alpha = 0.1

        self.hide_elements = (
            bpy.context.preferences.addons[__name__].preferences.hide_viewport_overlays
            and bpy.context.scene.render.engine in {"CYCLES", "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"}
            and bpy.context.area.spaces.active.shading.type == "RENDERED"
        )
       
        self.original_linking_state = None
        self.orbit_center = None
        self.initial_mouse_pos = None
        self.initial_light_vector = None
        self.color_temp_index = 0
        self.shift_h_active = False
        self.h_active = False

        self.h_pressed = False
        self.shift_pressed = False
        self.was_isolated = False
        self.initial_properties_context = None


        self.node_groups = ["Scrim Light", "Parabolic Light", "Octabox Light"]
        active_light = bpy.context.active_object
        if active_light and active_light.type == "LIGHT":

            self.current_node_group_index = active_light.get(
                "current_node_group_index", 0
            )
        else:
            self.current_node_group_index = 0

        if bpy.context.active_object and bpy.context.active_object.type == "LIGHT":
            
            for area in bpy.context.screen.areas:
                if area.type == "PROPERTIES":
                    for space in area.spaces:
                        if space.type == "PROPERTIES":
                            self.initial_properties_context = space.context
                            space.context = "DATA"
                    break

        self.just_invoked = False

    def store_node_group_index(self, light):
        try:
            light["current_node_group_index"] = self.current_node_group_index
        except Exception as e:
            print(f"Failed to set current_node_group_index property: {e}")

    def restore_node_group_index(self, light):
        self.current_node_group_index = light.get("current_node_group_index", 0)

    def remove_draw_handler(self):
        if self._handle:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, "WINDOW")
            self._handle = None

    def invoke(self, context, event):

        bpy.types.Scene.modal_running = True
            
        

        if self.hide_elements:
            hide_viewport_elements(context)
        self.just_invoked = True
        blender_version = bpy.app.version
        if blender_version[0] >= 4:
            self.nodegroup_blend_path = os.path.join(
                os.path.dirname(__file__), "nodegroup-4.blend"
            )
        else:
            self.nodegroup_blend_path = os.path.join(
                os.path.dirname(__file__), "nodegroup.blend"
            )

        global AdjustingLight, AdjustingEmpty
        
        if context.active_object and context.active_object.type == "LIGHT":
            self.save_linking_state(context, context.active_object)

        if hasattr(self, 'last_mouse_pos'):
            self.last_mouse_pos_2 = self.last_mouse_pos
        self.last_mouse_pos = (event.mouse_region_x, event.mouse_region_y)

        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y

        origin = region_2d_to_origin_3d(region, rv3d, coord)
        direction = region_2d_to_vector_3d(region, rv3d, coord)



        if is_orthographic_view(context):
            origin -= direction * (1000 / 2.0)

        result, location, normal, index, object, matrix = context.scene.ray_cast(
            context.view_layer.depsgraph, origin, direction
        )
        if result:
            self.mouse_on_object = object



        if AdjustingLight:

            self.light = AdjustingLight

            # Store the initial 'target' property
            self.initial_target = self.light.get("target", None)

            global KEY_IDENTIFIER


            if KEY_IDENTIFIER == "ONE":

                self.mode = "reflect"
                context.scene.light_wrangler_hints.current_mode = self.mode
            elif KEY_IDENTIFIER == "TWO":

                self.mode = "orbit"
                context.scene.light_wrangler_hints.current_mode = self.mode
            elif KEY_IDENTIFIER == "THREE":

                self.mode = "direct"
                context.scene.light_wrangler_hints.current_mode = self.mode
            elif KEY_IDENTIFIER == "TAB" and "light_adjust_mode" in self.light:

                self.mode = self.light["light_adjust_mode"]
                context.scene.light_wrangler_hints.current_mode = self.mode
            else:

                self.mode = bpy.context.preferences.addons[
                    __name__
                ].preferences.initial_mode
                context.scene.light_wrangler_hints.current_mode = self.mode
            if self.mode == None:

                self.mode = bpy.context.preferences.addons[
                    __name__
                ].preferences.initial_mode
                context.scene.light_wrangler_hints.current_mode = self.mode
            if self.mode == "orbit":
                if self.light["last_orbit_center"]:
                    last_orbit_center = self.light["last_orbit_center"]
                else:
                    self.orbit_center = self.light["last_hit_location_2"]
                    last_orbit_center = self.orbit_center
                    try:
                        self.light["last_orbit_center"] = last_orbit_center
                    except Exception as e:
                        print(f"Failed to set last_orbit_center property: {e}")
                self.orbit_center = Vector(last_orbit_center)

                if (
                    not self.sphere_empty_name
                    or self.sphere_empty_name not in bpy.data.objects
                ):
                    create_or_delete_sphere_empty(self, context, True)

            original_properties = AdjustingLight["original_properties"]
            # original_location = original_properties["location"]
            original_energy = original_properties["energy"]
            original_rotation = original_properties["rotation"]

            light_type = self.light.data.type

            if light_type == "AREA":
                original_size = original_properties["size"]
                original_size_y = original_properties.get("size_y", original_size)
                original_spread = original_properties["spread"]

                self.light.data.shape = original_properties.get(
                    "shape", self.light.data.shape
                )
                self.light.data.size = original_size
                self.light.data.size_y = original_size_y
                self.light.data.spread = original_spread

            elif light_type == "SPOT":

                original_spot_size = original_properties.get(
                    "spot_size", self.light.data.spot_size
                )
                original_spot_blend = original_properties.get(
                    "spot_blend", self.light.data.spot_blend
                )

                self.light.data.spot_size = original_spot_size
                self.light.data.spot_blend = original_spot_blend

            self.light.data.energy = original_energy
            self.light.rotation_euler = original_rotation

            self.empty_location = location

        else:

            self.empty_location = Vector((0, 0, 0))

            bpy.ops.object.light_add(type="AREA", location=(0, 0, 3))
            
            if bpy.context.preferences.addons[__name__].preferences.organize_lights:
                light_object = bpy.context.active_object
                lights_collection = bpy.data.collections.get("Lights")
                if not lights_collection:
                    lights_collection = bpy.data.collections.new("Lights")
                    bpy.context.scene.collection.children.link(lights_collection)
                    # Set the color tag to blue for the new collection
                    lights_collection.color_tag = 'COLOR_05'  # 'COLOR_05' corresponds to blue
                else:
                    # Set the color tag to blue for existing collection if not already set
                    if lights_collection.color_tag != 'COLOR_05':
                        lights_collection.color_tag = 'COLOR_05'
                
                # Find the LayerCollection corresponding to the "Lights" collection in the current view layer
                layer_collection = bpy.context.view_layer.layer_collection.children.get(lights_collection.name)
                
                if layer_collection and not layer_collection.exclude:
                    if light_object.name not in lights_collection.objects:
                        lights_collection.objects.link(light_object)
                    
                    # Unlink the light from its original collections if not excluded
                    for collection in light_object.users_collection:
                        if collection != lights_collection:
                            collection.objects.unlink(light_object)
                else:
                    print("Lights collection is excluded from the View Layer or does not exist in the current View Layer.")


            self.light = context.object
            addon_prefs = context.preferences.addons[__name__].preferences
            self.light.data.energy = addon_prefs.initial_light_power
            self.light.data.size = addon_prefs.initial_light_size

            if bpy.context.scene.render.engine in ["BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"]:
                self.light.data.use_contact_shadow = True

            def is_int(s):
                try:
                    int(s)
                    return True
                except ValueError:
                    return False

            maxnum = max(
                (
                    int(obj.name.split(".")[1])
                    for obj in bpy.data.objects
                    if obj.name.startswith("Area.") and is_int(obj.name.split(".")[1])
                ),
                default=0,
            )
            newnum = maxnum + 1

            if newnum == 1:
                self.light.name = "Area"
            else:
                self.light.name = f"Area.{newnum - 1:03d}"

            if (
                addon_prefs.use_custom_light_setup
                and bpy.context.scene.render.engine == "CYCLES"
            ):

                active_obj = self.light
                current_light_type = self.light.data.type
                bpy.ops.light.apply_custom_data_block(
                    light_name=active_obj.name,
                    light_type=current_light_type,
                    customization="Scrim",
                )
                if addon_prefs.show_lights_previews == True:
                    current_scene = bpy.context.scene
                    bpy.types.Scene.modal_running = False
                    sync_node_values_handler(current_scene)
                    bpy.types.Scene.modal_running = True

            self.light.data.spread = math.radians(addon_prefs.initial_light_spread_deg)
            self.light.data.size = addon_prefs.initial_light_size
            self.light.data.energy = addon_prefs.initial_light_power
            self.light.data.size = addon_prefs.initial_light_size

        AdjustingLight = None
        AdjustingEmpty = None

        context.window_manager.modal_handler_add(self)

        if not hasattr(self, "mode") or self.mode is None:

            self.mode = bpy.context.preferences.addons[
                __name__
            ].preferences.initial_mode

            context.scene.light_wrangler_hints.current_mode = self.mode

        if self.mode == "reflect":
            bpy.context.window.cursor_set("DEFAULT")
            context.scene.light_wrangler_hints.current_mode = self.mode
        elif self.mode == "direct":
            bpy.context.window.cursor_set("DEFAULT")
            context.scene.light_wrangler_hints.current_mode = self.mode
        elif self.mode == "orbit":
            bpy.context.window.cursor_set("NONE")
            context.scene.light_wrangler_hints.current_mode = self.mode

        if self.mode == "reflect":
            self.light["light_adjust_mode"] = "reflect"
            for _ in range(8):
                self.update_light(context, event)

        elif self.mode == "direct":
            self.light["light_adjust_mode"] = "direct"
            for _ in range(8):
                self.update_light_along_normal(context, event)

        elif self.mode == "orbit":
            self.light["light_adjust_mode"] = "orbit"

        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                self.mouse_x = event.mouse_x
                self.mouse_y = event.mouse_y    
                area.tag_redraw()

        self.mouse_x = event.mouse_x
        self.mouse_y = event.mouse_y
        args = (self, context)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_text_callback, args, 'WINDOW', 'POST_PIXEL')

        wm = context.window_manager
        wm.is_light_adjust_active = not wm.is_light_adjust_active

        return {"RUNNING_MODAL"}

    def cleanup(self):
        # Ensure we're working with a valid light that was being adjusted
        if hasattr(self, 'light') and self.light:
            try:
                # Check if the light object is still valid
                _ = self.light.name
                if self.light.name in bpy.data.objects:
                    # Always unhide the light on cleanup
                    if self.light.hide_viewport:
                        self.light.hide_viewport = False
                        print(f"Light '{self.light.name}' unhidden on cleanup")

                    # Handle isolation (revert Shift+H state)
                    if hasattr(self, 'is_isolated') and self.is_isolated:
                        bpy.ops.light.lw_toggle_visibility()
                        self.is_isolated = False
                        print("Isolation removed on cleanup")

                    # Ensure the light is selected and active
                    bpy.ops.object.select_all(action='DESELECT')
                    self.light.select_set(True)
                    bpy.context.view_layer.objects.active = self.light
                else:
                    print(f"Light object no longer exists in the scene")
            except ReferenceError:
                print("Light object is no longer valid")

        # Existing cleanup for h_active and shift_h_active
        if hasattr(self, 'h_active') and hasattr(self, 'shift_h_active'):
            if self.h_active or self.shift_h_active:
                for obj in bpy.data.objects:
                    if obj.type == "LIGHT":
                        obj.hide_viewport = False
                self.h_active = False
                self.shift_h_active = False

        # Existing cleanup for mesh and object references
        if hasattr(self, 'evaluated_object') and hasattr(self, 'temp_mesh'):
            self.evaluated_object.to_mesh_clear()
            del self.temp_mesh
        if hasattr(self, 'current_object'):
            del self.current_object
        if hasattr(self, 'evaluated_object'):
            del self.evaluated_object
        if hasattr(self, 'bm') and self.bm is not None:
            self.bm.free()
            del self.bm

        # Existing cleanup for properties context
        if hasattr(self, 'initial_properties_context') and self.initial_properties_context == 'OBJECT':
            if self.light:
                for area in bpy.context.screen.areas:
                    if area.type == "PROPERTIES":
                        for space in area.spaces:
                            if space.type == "PROPERTIES":
                                space.context = 'OBJECT'
                        break

    def modal(self, context, event):


        if event.type == "P" and event.value == "PRESS":
            self.paused = not self.paused

            if self.paused:
                self.saved_mode = self.mode
                
            else:
                self.mode = self.saved_mode
                if self.mode == "orbit":
                    region = context.region
                    rv3d = context.region_data
                    coord = (event.mouse_region_x, event.mouse_region_y)

                    origin = region_2d_to_origin_3d(region, rv3d, coord)
                    direction = region_2d_to_vector_3d(region, rv3d, coord)

                    max_distance = 1000

                    (
                        result,
                        location,
                        normal,
                        index,
                        object,
                        matrix,
                    ) = context.scene.ray_cast(
                        context.view_layer.depsgraph,
                        origin,
                        direction,
                        distance=max_distance,
                    )

                    if result:
                        if self.sphere_empty_name:
                            sphere_empty = bpy.data.objects.get(
                                self.sphere_empty_name, None
                            )
                            if sphere_empty:
                                create_or_delete_sphere_empty(self, context, False)

                        self.initial_mouse_pos = None
                        self.orbit_center = location

                        create_or_delete_sphere_empty(self, context, True)

                        self.update_light_in_orbit_mode(context, event)
                    else:
                        print("Ray cast did not hit any object")

                elif self.mode == "direct":
                    
                    for _ in range(8):
                        self.update_light_along_normal(context, event)

                else:
                    
                    for _ in range(8):
                        self.update_light(context, event)

            return {"PASS_THROUGH"}

        if event.type == "SPACE" and event.value == "PRESS":
            if self.paused:
                self.paused = not self.paused
                self.mode = self.saved_mode

            # Store current states
            was_isolated = self.is_isolated
            was_hidden = self.light.hide_viewport if self.light else False

            if self.mode == "reflect":
                self.mode = "orbit"
                self.light["light_adjust_mode"] = "orbit"
                self.initial_mouse_pos = None
                self.orbit_center = self.empty_location
                create_or_delete_sphere_empty(self, context, True)
                bpy.context.window.cursor_set("NONE")
                for _ in range(8):
                    self.update_light(context, event)
            elif self.mode == "orbit":
                self.mode = "direct"
                self.light["light_adjust_mode"] = "direct"
                if self.sphere_empty_name:
                    sphere_empty = bpy.data.objects.get(self.sphere_empty_name, None)
                    if sphere_empty:
                        create_or_delete_sphere_empty(self, context, False)
                bpy.context.window.cursor_set("DEFAULT")
                for _ in range(8):
                    self.update_light_along_normal(context, event)
            elif self.mode == "direct":
                self.mode = "reflect"
                self.light["light_adjust_mode"] = "reflect"
                bpy.context.window.cursor_set("DEFAULT")
                for _ in range(8):
                    self.update_light(context, event)

            # Restore states
            self.restore_light_states(was_isolated, was_hidden)

            context.scene.light_wrangler_hints.current_mode = self.mode
            return {"RUNNING_MODAL"}

        elif (
            event.type in {"ONE", "TWO", "THREE", "NUMPAD_1", "NUMPAD_2", "NUMPAD_3"}
            and event.value == "PRESS"
        ):
            if self.paused:
                self.paused = not self.paused
                self.mode = self.saved_mode

            # Store current states
            was_isolated = self.is_isolated
            was_hidden = self.light.hide_viewport if self.light else False

            if event.type in {"ONE", "NUMPAD_1"} and self.mode != "reflect":
                self.mode = "reflect"
                self.light["light_adjust_mode"] = "reflect"
                bpy.context.window.cursor_set("DEFAULT")
                if self.sphere_empty_name:
                    sphere_empty = bpy.data.objects.get(self.sphere_empty_name, None)
                    if sphere_empty:
                        create_or_delete_sphere_empty(self, context, False)
                
                for _ in range(8):
                    self.update_light(context, event)
            elif event.type in {"TWO", "NUMPAD_2"} and self.mode != "orbit":
                self.mode = "orbit"
                self.light["light_adjust_mode"] = "orbit"
                bpy.context.window.cursor_set("NONE")
                self.initial_mouse_pos = None
                self.orbit_center = self.empty_location
                create_or_delete_sphere_empty(self, context, True)
                
            elif event.type in {"THREE", "NUMPAD_3"} and self.mode != "direct":
                self.mode = "direct"
                self.light["light_adjust_mode"] = "direct"
                bpy.context.window.cursor_set("DEFAULT")
                if self.sphere_empty_name:
                    sphere_empty = bpy.data.objects.get(self.sphere_empty_name, None)
                    if sphere_empty:
                        create_or_delete_sphere_empty(self, context, False)
                
                for _ in range(8):
                    self.update_light_along_normal(context, event)

            # Restore states
            self.restore_light_states(was_isolated, was_hidden)

            context.scene.light_wrangler_hints.current_mode = self.mode


        elif event.type == "TAB" and self.just_invoked:
            self.mode = self.light["light_adjust_mode"]
            context.scene.light_wrangler_hints.current_mode = self.mode
            self.just_invoked = False
            return {"RUNNING_MODAL"}

        elif (
            event.type in {"LEFTMOUSE", "RET", "TAB"} and self.left_mouse_hold == False
        ):
            self.cleanup_light_states(context)
            if self.paused == True:
                self.paused = not self.paused
                self.mode = self.saved_mode
            if self.light:
                self.light["light_adjust_mode"] = self.mode
                self.light["last_used_mode"] = self.mode
                self.light["last_orbit_center"] = self.orbit_center

            # Update the 'target' property to the new target
            if self.light:
                # Assuming 'new_target' is the point where the light is now aimed
                # You need to set 'self.new_target' during your modal operations
                if hasattr(self, 'new_target'):
                    self.light["target"] = self.new_target
                else:
                    # If 'new_target' is not set, use the last known hit location
                    self.light["target"] = self.empty_location

            bpy.context.window.cursor_set("DEFAULT")
            self.remove_draw_handler()
            if self.sphere_empty_name:
                sphere_empty = bpy.data.objects.get(self.sphere_empty_name, None)
                if sphere_empty:
                    create_or_delete_sphere_empty(self, context, False)
            if context.area:
                self.mouse_x = event.mouse_x
                self.mouse_y = event.mouse_y
                context.area.tag_redraw()
            self.cleanup()

            wm = context.window_manager
            wm.is_light_adjust_active = not wm.is_light_adjust_active
            if self.hide_elements:
                unhide_viewport_elements(context)
            
            bpy.types.Scene.modal_running = False
            return {"FINISHED"}

        elif event.type in {"RIGHTMOUSE", "ESC"}:
            # Revert linking changes if modal is cancelled
            self.revert_linking_state(context)         
            self.cleanup_light_states(context)
            bpy.context.window.cursor_set("DEFAULT")
            if self.paused == True:
                self.paused = not self.paused
                self.mode = self.saved_mode
            if self.light:
                if "last_used_mode" in self.light:
                    try:
                        self.light["light_adjust_mode"] = self.light["last_used_mode"]
                    except Exception as e:
                        print(f"Failed to set light_adjust_mode property: {e}")
                else:
                    try:
                        self.light["light_adjust_mode"] = self.mode
                        self.light["last_used_mode"] = self.mode
                    except Exception as e:
                        print(f"Failed to set last_used_mode property: {e}")
                try:
                    self.light["last_orbit_center"] = self.orbit_center
                except Exception as e:
                    print(f"Failed to set last_orbit_center property: {e}")
            
                # Restore the initial 'target' property
                if hasattr(self, 'initial_target'):
                    if self.initial_target is not None:
                        self.light["target"] = self.initial_target
                    else:
                        self.light.pop("target", None)

            self.remove_draw_handler()
            if self.sphere_empty_name:
                sphere_empty = bpy.data.objects.get(self.sphere_empty_name, None)
                if sphere_empty:
                    create_or_delete_sphere_empty(self, context, False)
            if context.area:
                self.mouse_x = event.mouse_x
                self.mouse_y = event.mouse_region_y                
                context.area.tag_redraw()
            if "start_proximity" in self.light:
                self.light["current_proximity"] = self.light["start_proximity"]
            if "original_properties" in self.light and duplicate_case == False:

                original_properties = self.light["original_properties"]
                light_type = self.light.data.type

                self.light.location = original_properties["location"]
                self.light.data.energy = original_properties["energy"]
                self.light.rotation_euler = original_properties["rotation"]

                if light_type == "AREA":
                    self.light.data.size = original_properties["size"]
                    self.light.data.size_y = original_properties.get(
                        "size_y", original_properties["size"]
                    )
                    self.light.data.spread = original_properties["spread"]
                elif light_type == "SPOT":
                    self.light.data.spot_size = original_properties["size"]
                    self.light.data.spot_blend = original_properties["spread"]

            else:

                bpy.data.objects.remove(self.light, do_unlink=True)

            self.cleanup()

            wm = context.window_manager
            wm.is_light_adjust_active = not wm.is_light_adjust_active
            if self.hide_elements:
                unhide_viewport_elements(context)

            
            bpy.types.Scene.modal_running = False
            return {"CANCELLED"}

        elif event.type == "MOUSEMOVE": #and event.type not in {"WHEELUPMOUSE", "WHEELDOWNMOUSE"}:


            current_time = time.time()
            if self.paused == False:
                if self.last_mouse_pos is not None:
                    dx = event.mouse_region_x - self.last_mouse_pos[0]
                    dy = event.mouse_region_y - self.last_mouse_pos[1]
                    distance_moved = (dx**2 + dy**2) ** 0.5
                    time_delta = current_time - self.last_update_time
                    settings = bpy.context.preferences.addons[__name__].preferences
                    speedfactor = settings.speedfactor
                    lerp_min = settings.lerp_min
                    lerp_max = settings.lerp_max
                    alpha = settings.alpha

                    current_speed = (
                        distance_moved / time_delta * speedfactor
                        if time_delta > 0
                        else 0
                    )
                    self.avg_speed = (alpha * current_speed) + (
                        (1 - alpha) * self.avg_speed
                    )
                    self.lerp_factor = min(
                        max(1 - self.avg_speed / 100, lerp_min), lerp_max
                    )
                    self.last_update_time = current_time

                    if self.mode == "orbit" and self.orbit_center is not None:
                        self.update_light_in_orbit_mode(context, event)
                    elif self.mode == "direct":
                        self.update_light_along_normal(context, event)
                    elif self.mode == "reflect":
                        self.update_light(context, event)

                self.last_mouse_pos = (event.mouse_region_x, event.mouse_region_y)


        # Then modify the relevant part of the modal method:
        elif event.type in {"WHEELUPMOUSE", "WHEELDOWNMOUSE", "UP_ARROW", "DOWN_ARROW", "TRACKPADPAN"}:
            if event.type != "TRACKPADPAN" and event.value == "PRESS" or event.type == "TRACKPADPAN":
                # Determine the direction for trackpad pan
                if event.type == "TRACKPADPAN":
                    # Apply the trackpad sensitivity
                    direction = (event.mouse_y - event.mouse_prev_y) * self.trackpad_sensitivity
                else:
                    direction = 1 if event.type in {"WHEELUPMOUSE", "UP_ARROW"} else -1

                if event.ctrl:
                    light_type = self.light.data.type

                    if light_type == "AREA":
                        current_degrees = math.degrees(self.light.data.spread)

                        if direction > 0:
                            if current_degrees >= 4:
                                increment = math.radians(5) * (1 if event.type != "TRACKPADPAN" else abs(direction))
                            else:
                                increment = math.radians(1) * (1 if event.type != "TRACKPADPAN" else abs(direction))
                            self.light.data.spread = min(
                                self.light.data.spread + increment,
                                math.radians(180),
                            )
                        else:
                            if current_degrees > 6:
                                decrement = math.radians(5) * (1 if event.type != "TRACKPADPAN" else abs(direction))
                            else:
                                decrement = math.radians(1) * (1 if event.type != "TRACKPADPAN" else abs(direction))
                            self.light.data.spread = max(
                                self.light.data.spread - decrement, math.radians(1)
                            )

                    elif light_type == "SPOT":
                        current_degrees = math.degrees(self.light.data.spot_blend)

                        if direction > 0:
                            new_blend = min(self.light.data.spot_blend + 0.05 * (1 if event.type != "TRACKPADPAN" else abs(direction)), 1.0)
                        else:
                            new_blend = max(self.light.data.spot_blend - 0.05 * (1 if event.type != "TRACKPADPAN" else abs(direction)), 0.0)
                        self.light.data.spot_blend = new_blend

                    last_activation_time["Spread"] = time.time()

                elif event.shift:
                    adjustment_factor = 0.05 * (1 if event.type != "TRACKPADPAN" else abs(direction))
                    light_type = self.light.data.type

                    if direction > 0:
                        if light_type == "AREA":
                            if self.light.data.shape in {"SQUARE", "DISK"}:
                                self.light.data.size += (
                                    self.light.data.size * adjustment_factor
                                )
                            else:
                                self.light.data.size += (
                                    self.light.data.size * adjustment_factor
                                )
                                self.light.data.size_y += (
                                    self.light.data.size_y * adjustment_factor
                                )
                            addon_prefs = bpy.context.preferences.addons[
                                __name__
                            ].preferences
                            if addon_prefs.use_calculated_light:
                                self.light.data.energy *= (1 + adjustment_factor) ** 1.5

                        elif light_type == "SPOT":
                            self.light.data.spot_size += (
                                self.light.data.spot_size * adjustment_factor
                            )

                    else:
                        if light_type == "AREA":
                            if self.light.data.shape in {"SQUARE", "DISK"}:
                                self.light.data.size -= (
                                    self.light.data.size * adjustment_factor
                                )
                            else:
                                self.light.data.size -= (
                                    self.light.data.size * adjustment_factor
                                )
                                self.light.data.size_y -= (
                                    self.light.data.size_y * adjustment_factor
                                )
                            addon_prefs = bpy.context.preferences.addons[
                                __name__
                            ].preferences

                            if addon_prefs.use_calculated_light:
                                self.light.data.energy /= (1 + adjustment_factor) ** 1.5
                        elif light_type == "SPOT":
                            self.light.data.spot_size -= (
                                self.light.data.spot_size * adjustment_factor
                            )

                        if light_type == "AREA":
                            self.light.data.size = max(self.light.data.size, 0.01)
                        elif light_type == "SPOT":
                            self.light.data.spot_size = max(
                                self.light.data.spot_size, 0.01
                            )
                    last_activation_time["Size"] = time.time()
                elif event.alt:
                    if self.mode != 'orbit': 
                        direction_vec = (self.light.location - self.empty_location).normalized()
                        distance = (self.light.location - self.empty_location).length
                    else:
                        direction_vec = (self.light.location - self.orbit_center).normalized()
                        distance = (self.light.location - self.empty_location).length                          

                    adjustment = 0.05 * distance * (1 if event.type != "TRACKPADPAN" else abs(direction))
                    if direction < 0:
                        self.light.location += direction_vec * adjustment
                        new_distance = (
                            self.light.location - self.empty_location
                        ).length

                        addon_prefs = bpy.context.preferences.addons[
                            __name__
                        ].preferences
                        if addon_prefs.use_calculated_light:
                            self.light.data.energy *= (new_distance / distance) ** 2
                    else:
                        self.light.location -= direction_vec * adjustment
                        new_distance = (
                            self.light.location - self.empty_location
                        ).length

                        addon_prefs = bpy.context.preferences.addons[
                            __name__
                        ].preferences
                        if addon_prefs.use_calculated_light:
                            self.light.data.energy *= (new_distance / distance) ** 2
                    self.light["current_proximity"] = new_distance

                    if self.mode != 'orbit':  
                        self.update_light_properties(self.light.location, self.empty_location)
                    else:
                        self.update_light_properties(self.light.location, self.orbit_center)
                    last_activation_time["Distance"] = time.time()
                elif not event.ctrl:
                    if direction > 0:
                        self.light.data.energy += self.light.data.energy * 0.1 * (1 if event.type != "TRACKPADPAN" else abs(direction))
                    else:
                        self.light.data.energy -= self.light.data.energy * 0.1 * (1 if event.type != "TRACKPADPAN" else abs(direction))

                    self.light.data.energy = max(self.light.data.energy, 0.01)
                    last_activation_time["Power"] = time.time()

                # self.update_light_properties(self.light.location, self.empty_location)

        h_just_pressed = event.type == "H" and event.value == "PRESS"
        shift_pressed = event.shift

        if h_just_pressed:
            if shift_pressed:
                last_activation_time["Isolate Light"] = time.time()
                # Toggle Shift+H (Isolate Light)
                if self.light.hide_viewport:
                    # If light is hidden, unhide it first
                    self.light.hide_viewport = False
                    self.light.select_set(True)
                    context.view_layer.objects.active = self.light
                
                # Toggle isolation
                bpy.ops.light.lw_toggle_visibility()
                self.is_isolated = not self.is_isolated
                self.report({'INFO'}, "Light isolated" if self.is_isolated else "Isolation removed")
            else:
                last_activation_time["Hide Light"] = time.time()
                # Toggle H (Hide Light)
                if self.is_isolated:
                    # If light is isolated, remove isolation first
                    bpy.ops.light.lw_toggle_visibility()
                    self.is_isolated = False
                
                # Toggle hiding
                self.light.hide_viewport = not self.light.hide_viewport
                if self.light.hide_viewport:
                    self.report({'INFO'}, "Light hidden")
                else:
                    self.light.select_set(True)
                    context.view_layer.objects.active = self.light
                    self.report({'INFO'}, "Light unhidden")
            
            return {"RUNNING_MODAL"}
        
        elif (
            event.type == "LEFT_SHIFT" or event.type == "RIGHT_SHIFT"
        ) and self.shift_h_active:
            if event.value == "RELEASE":
                for obj in bpy.data.objects:
                    if obj.type == "LIGHT":
                        obj.hide_viewport = False
                self.shift_h_active = False
            return {"RUNNING_MODAL"}

        elif (
            event.type == "LEFT_SHIFT" or event.type == "RIGHT_SHIFT"
        ) and self.h_active:
            if event.value == "PRESS":

                self.light.hide_viewport = False
                for obj in bpy.data.objects:
                    if obj.type == "LIGHT" and obj != self.light:
                        obj.hide_viewport = True
                self.h_active = False
                self.shift_h_active = True
            elif event.value == "RELEASE":

                pass
            return {"RUNNING_MODAL"}

        elif event.type == "T" and event.value == "PRESS":
            color_temps = [3200, 6500, 7500]

            use_cycles = bpy.context.scene.render.engine == "CYCLES"
            nodes_enabled = (
                self.light.data.use_nodes
                if hasattr(self.light.data, "use_nodes")
                else False
            )

            node_found = False

            if use_cycles and nodes_enabled:
                for node in self.light.data.node_tree.nodes:
                    if (
                        isinstance(node, bpy.types.ShaderNodeGroup)
                        and "ColorTemp" in node.inputs
                    ):
                        node.inputs["ColorTemp"].default_value = color_temps[
                            self.color_temp_index
                        ]
                        node_found = True
                        break

            if not node_found or not use_cycles or not nodes_enabled:

                if (
                    bpy.context.scene.render.engine in ["BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"]
                    or not node_found
                    or not use_cycles
                ):

                    precalculated_rgb = [
                        (1.0, 0.718, 0.482),
                        (1.0, 0.929, 0.871),
                        (0.898, 0.918, 1.0),
                    ]
                    new_color = precalculated_rgb[self.color_temp_index]
                    self.light.data.color = new_color

            self.color_temp_index = (self.color_temp_index + 1) % len(color_temps)
            return {"RUNNING_MODAL"}

        elif event.type == 'L' and event.value == 'PRESS':
            if bpy.context.active_object and bpy.context.active_object.type == "LIGHT":


                last_activation_time["Light Linking"] = time.time()

                for area in bpy.context.screen.areas:
                    if area.type == "PROPERTIES":

                        for space in area.spaces:
                            if space.type == "PROPERTIES":
                                space.context = "OBJECT"
                        break

            if event.shift:
                self.link_object(context, is_blocker=True)
            else:
                self.link_object(context, is_blocker=False)

        return {"RUNNING_MODAL"}


    def restore_light_states(self, was_isolated, was_hidden):
        if self.light and self.light.name in bpy.data.objects:
            # Use the global is_isolated property
            if was_isolated != bpy.context.scene.light_wrangler.is_isolated:
                bpy.ops.light.lw_toggle_visibility()
            self.is_isolated = bpy.context.scene.light_wrangler.is_isolated

            # Restore hiding state
            self.light.hide_viewport = was_hidden

    def save_linking_state(self, context, light):
        self.original_linking_state = {
            'blocker_collection': light.light_linking.blocker_collection,
            'receiver_collection': light.light_linking.receiver_collection,
            'objects': {}
        }
        for collection_type in ('blocker_collection', 'receiver_collection'):
            collection = getattr(light.light_linking, collection_type)
            if collection:
                self.original_linking_state[collection_type + '_name'] = collection.name
                for linked_obj in collection.objects:
                    self.original_linking_state['objects'][linked_obj.name] = {
                        'light_linking_state': linked_obj.get('light_linking_state', None),
                        'collection_type': collection_type
                    }


    def revert_linking_state(self, context):
        if not hasattr(self, 'original_linking_state') or self.original_linking_state is None:
            print("No original linking state to revert.")
            return

        light = context.active_object
        if not light or light.type != 'LIGHT':
            return

        # Rest of the method remains unchanged
        # Clear current collections
        for collection_type in ('blocker_collection', 'receiver_collection'):
            current_collection = getattr(light.light_linking, collection_type)
            if current_collection:
                for obj in list(current_collection.objects):
                    current_collection.objects.unlink(obj)
                    if 'light_linking_state' in obj:
                        del obj['light_linking_state']
                bpy.data.collections.remove(current_collection)
            setattr(light.light_linking, collection_type, None)

        # Restore original state
        for collection_type in ('blocker_collection', 'receiver_collection'):
            collection_name = self.original_linking_state.get(collection_type + '_name')
            if collection_name:
                collection = bpy.data.collections.get(collection_name)
                if not collection:
                    collection = bpy.data.collections.new(collection_name)
                    bpy.context.scene.collection.children.link(collection)
                setattr(light.light_linking, collection_type, collection)

        for obj_name, obj_data in self.original_linking_state['objects'].items():
            obj = bpy.data.objects.get(obj_name)
            if not obj:
                continue
            if obj_data['light_linking_state']:
                obj['light_linking_state'] = obj_data['light_linking_state']
            elif 'light_linking_state' in obj:
                del obj['light_linking_state']
            
            collection = getattr(light.light_linking, obj_data['collection_type'])
            if collection and obj.name not in collection.objects:
                collection.objects.link(obj)


    def ensure_light_linking_collection(self, context, is_blocker):
        light = context.active_object
        if is_blocker:
            if not light.light_linking.blocker_collection:
                bpy.ops.object.light_linking_blocker_collection_new()
        else:
            if not light.light_linking.receiver_collection:
                bpy.ops.object.light_linking_receiver_collection_new()

    def link_object(self, context, is_blocker):
        # Check if the current render engine is Cycles
        if context.scene.render.engine != 'CYCLES':
            self.report({'WARNING'}, "Light linking is only available in Cycles render engine")
            return

        if self.mouse_on_object and self.light:
            
            # Ensure the light is the active object
            context.view_layer.objects.active = self.light
            
            # Ensure the appropriate collection exists
            self.ensure_light_linking_collection(context, is_blocker)
            
            # Get the appropriate collection
            light_linking = self.light.light_linking
            collection = light_linking.blocker_collection if is_blocker else light_linking.receiver_collection
            
            if collection:
                collection_name = collection.name
                
                if self.mouse_on_object.name not in collection.objects:
                    bpy.ops.object.select_all(action='DESELECT')
                    self.mouse_on_object.select_set(True)
                    
                    is_first_object = len(collection.objects) == 0
                    
                    if is_blocker:
                        bpy.ops.object.light_linking_blockers_link(link_state='INCLUDE')
                        if is_first_object:
                            status_message = f"{self.mouse_on_object.name} is now the only object that casts shadow from {self.light.name}"
                        else:
                            status_message = f"{self.mouse_on_object.name} now casts shadow from {self.light.name}"
                    else:
                        bpy.ops.object.light_linking_receivers_link(link_state='INCLUDE')
                        if is_first_object:
                            status_message = f"{self.mouse_on_object.name} is now the only object that receives light from {self.light.name}"
                        else:
                            status_message = f"{self.mouse_on_object.name} now receives light from {self.light.name}"
                    self.mouse_on_object['light_linking_state'] = 'INCLUDE'
                else:
                    link_state = self.mouse_on_object.get('light_linking_state', 'INCLUDE')
                    
                    bpy.ops.object.select_all(action='DESELECT')
                    self.mouse_on_object.select_set(True)
                    
                    if link_state == 'INCLUDE':
                        is_only_object = len(collection.objects) == 1
                        
                        if is_blocker:
                            bpy.ops.object.light_linking_blockers_link(link_state='EXCLUDE')
                            if is_only_object:
                                status_message = f"{self.mouse_on_object.name}, the only blocker, no longer casts shadow from {self.light.name}"
                            else:
                                status_message = f"{self.mouse_on_object.name} no longer casts shadow from {self.light.name}"
                        else:
                            bpy.ops.object.light_linking_receivers_link(link_state='EXCLUDE')
                            if is_only_object:
                                status_message = f"{self.mouse_on_object.name}, the only receiver, now ignores light from {self.light.name}"
                            else:
                                status_message = f"{self.mouse_on_object.name} now ignores light from {self.light.name}"
                        self.mouse_on_object['light_linking_state'] = 'EXCLUDE'
                    else:
                        if self.mouse_on_object.name in collection.objects:
                            collection.objects.unlink(self.mouse_on_object)
                            if is_blocker:
                                status_message = f"{self.mouse_on_object.name} removed from shadow linking collection for {self.light.name}"
                            else:
                                status_message = f"{self.mouse_on_object.name} removed from light linking collection for {self.light.name}"

                            # Check if the collection is now empty
                            if len(collection.objects) == 0:
                                # Check if the collection is used only for this light linking
                                is_unused = True
                                for obj in bpy.data.objects:
                                    if obj.type == 'LIGHT' and obj != self.light:
                                        if (is_blocker and obj.light_linking.blocker_collection == collection) or \
                                        (not is_blocker and obj.light_linking.receiver_collection == collection):
                                            is_unused = False
                                            break

                                if is_unused:
                                    # Remove the collection from all scenes and viewlayers
                                    for scene in bpy.data.scenes:
                                        if collection.name in scene.collection.children:
                                            scene.collection.children.unlink(collection)
                                        for layer in scene.view_layers:
                                            if collection.name in layer.layer_collection.children:
                                                layer.layer_collection.children.unlink(collection)
                                    
                                    # Remove the collection from Blender's data
                                    bpy.data.collections.remove(collection, do_unlink=True)
                                    
                                    # Purge the collection from memory
                                    bpy.data.orphans_purge(do_recursive=True)
                                    
                                    if is_blocker:
                                        self.light.light_linking.blocker_collection = None
                                    else:
                                        self.light.light_linking.receiver_collection = None
                                    
                                    # Set collection to None after deletion
                                    collection = None

                        if 'light_linking_state' in self.mouse_on_object:
                            del self.mouse_on_object['light_linking_state']
            
                # Check if collection still exists before accessing it
                if collection and collection_name in bpy.data.collections:
                    pass
                else:
                    pass
                
                # Deselect the object
                self.mouse_on_object.select_set(False)
                
                # Reselect the light
                self.light.select_set(True)
                context.view_layer.objects.active = self.light

                # Display the improved status message
                self.report({'INFO'}, status_message)

        else:
            self.report({'WARNING'}, "No object under mouse or no active light")

    def cleanup_light_states(self, context):
        # Revert any hidden or isolated states
        if self.h_pressed or self.shift_pressed:
            if self.was_isolated:
                bpy.ops.light.lw_toggle_visibility()
            else:
                for obj in bpy.data.objects:
                    if obj.type == 'LIGHT':
                        obj.hide_viewport = False
            
            # Restore original selection state
            self.light.select_set(self.was_selected)
            context.view_layer.objects.active = self.light if self.was_selected else None

    def update_light(self, context, event):
        if not hasattr(self, 'light') or self.light is None:
            return {'CANCELLED'}

        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y

        is_ortho_camera = (rv3d.view_perspective == 'CAMERA' and
                        context.scene.camera.data.type == 'ORTHO')

        if is_ortho_camera:
            camera = context.scene.camera
            camera_matrix = camera.matrix_world
            camera_direction = camera_matrix.to_3x3() @ Vector((0, 0, -1))
            mouse_pos_3d = view3d_utils.region_2d_to_location_3d(region, rv3d, coord, camera_matrix.translation)
            ray_origin = mouse_pos_3d
            ray_direction = camera_direction
        else:
            ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
            ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)

        result, location, normal, index, object, matrix = context.scene.ray_cast(
            context.view_layer.depsgraph,
            ray_origin,
            ray_direction
        )
        if result:
            self.mouse_on_object = object
     

        if result:
            is_instance = False

            # Check if we need to update the evaluated object and temp mesh
            if not hasattr(self, 'temp_mesh') or self.temp_mesh is None or self.current_object_temp_mesh != object:
                # Clear previous temp mesh if it exists
                if hasattr(self, 'evaluated_object') and hasattr(self, 'temp_mesh'):
                    self.evaluated_object.to_mesh_clear()
                    # print("Cleared existing temp mesh")
                
                # Get the evaluated object with modifiers applied
                depsgraph = context.evaluated_depsgraph_get()
                self.current_object_temp_mesh = object
                self.evaluated_object = object.evaluated_get(depsgraph)
                # Try to convert the evaluated object to a mesh
                try:
                    self.temp_mesh = self.evaluated_object.to_mesh()
                except RuntimeError:
                    
                    self.temp_mesh = None
                

            # Get the object's scale
            object_scale = self.evaluated_object.matrix_world.to_scale()

            # Calculate the maximum scale component
            max_scale = max(object_scale)

            # Ensure the temp_mesh is valid and has polygons
            if self.temp_mesh and self.temp_mesh.polygons and index < len(self.temp_mesh.polygons):
                hit_polygon = self.temp_mesh.polygons[index]
                hit_polygon_center = self.evaluated_object.matrix_world @ hit_polygon.center

                # Adjust max_vertex_distance calculation
                max_vertex_distance = max((self.temp_mesh.vertices[vertex].co - hit_polygon.center).length for vertex in hit_polygon.vertices)
                max_vertex_distance *= max_scale  # Scale the distance

                is_instance = (location - hit_polygon_center).length > max_vertex_distance
            else:
                
                self.temp_mesh = None


          
            # Get world matrix and its inverse
            world_matrix = self.evaluated_object.matrix_world
            world_matrix_inv = world_matrix.inverted()

            if hasattr(self.evaluated_object.data, 'polygons') and (not is_instance and len(self.evaluated_object.data.polygons) < 350000) and self.temp_mesh != None:
          


                # Get local hit position
                local_hit_pos = world_matrix_inv @ location

                # Create bmesh from temp_mesh
                if not hasattr(self, 'bm') or self.bm is None or self.current_object_bmesh != object:
                    if hasattr(self, 'bm') and self.bm is not None:
                        self.bm.free()
                        # print("Freed existing BMesh")
                    self.bm = bmesh.new()
                    self.bm.from_mesh(self.temp_mesh)
                    self.bm.faces.ensure_lookup_table()
                    self.current_object_bmesh = object
                    # print(f"Created new bmesh with {len(self.bm.faces)} faces for object: {object.name}")
                # else:
                #     print(f"Using existing bmesh with {len(self.bm.faces)} faces for object: {object.name}")

                # Function to get neighboring faces
                def get_neighboring_faces(bm, start_face, max_rings):
                    face_rings = [{start_face}]
                    visited = {start_face}
                    for _ in range(max_rings):
                        new_ring = set()
                        for face in face_rings[-1]:
                            for vert in face.verts:
                                for neighbor_face in vert.link_faces:
                                    if neighbor_face not in visited:
                                        new_ring.add(neighbor_face)
                                        visited.add(neighbor_face)
                        if not new_ring:
                            break
                        face_rings.append(new_ring)
                    return face_rings

                # Check if the index is within the valid range for BMesh faces
                if index < len(self.bm.faces):
                    start_face = self.bm.faces[index]
                else:
                    # print(f"Warning: Face index {index} out of range. Using closest face.")
                    # Find the closest face in the BMesh
                    start_face = min(self.bm.faces, key=lambda f: (f.calc_center_median() - local_hit_pos).length)

                # Get neighboring faces
                max_rings = min(1 + len(self.bm.faces) // 1000, 6)
                face_rings = get_neighboring_faces(self.bm, start_face, max_rings)

                # world_matrix = self.evaluated_object.matrix_world
                world_hit_pos = world_matrix @ local_hit_pos

                weighted_normal = Vector((0, 0, 0))
                total_weight = 0

                # Get the normal of the hit face
                hit_face_normal = start_face.normal



                # Simple k-means clustering implementation
                def kmeans_clustering(data, k, max_iterations=100):

                    # Initialize centroids randomly
                    centroids = random.sample(data, k)
                    
                    for _ in range(max_iterations):
                        # Assign points to clusters
                        clusters = [[] for _ in range(k)]
                        for point in data:
                            distances = [(point - c).length_squared for c in centroids]
                            closest_centroid = distances.index(min(distances))
                            clusters[closest_centroid].append(point)
                        
                        # Update centroids
                        new_centroids = []
                        for cluster in clusters:
                            if cluster:
                                new_centroid = Vector((0, 0, 0))
                                for point in cluster:
                                    new_centroid += point
                                new_centroid /= len(cluster)
                                new_centroids.append(new_centroid)
                            else:
                                new_centroids.append(random.choice(data))
                        
                        # Check for convergence
                        if all((c1 - c2).length < 0.001 for c1, c2 in zip(centroids, new_centroids)):
                            break
                        
                        centroids = new_centroids
                    
                    return centroids, clusters

                # Function to determine geometry complexity
                def is_complex_geometry(bm, sample_size=100, n_clusters=3):
                    # Convert BMFaces to a list that can be sampled
                    faces = list(bm.faces)
                    
                    if len(faces) <= sample_size:
                        sample = faces
                    else:
                        sample = random.sample(faces, sample_size)
                    
                    # Convert face normals to Vector
                    normals = [face.normal.copy() for face in sample]

                    # Adjust n_clusters if there are fewer normals than clusters
                    n_clusters = min(n_clusters, len(normals))

                    # Perform k-means clustering
                    centroids, clusters = kmeans_clustering(normals, n_clusters)

                    # Calculate the average distance to cluster centers
                    total_distance = sum(min((normal - centroid).length for centroid in centroids) for normal in normals)
                    avg_distance = total_distance / len(normals)

                    # You can adjust this threshold as needed
                    return avg_distance > 0.5  # Consider complex if average distance to cluster centers is high

                is_complex = is_complex_geometry(self.bm)

                for ring, faces in enumerate(face_rings):
                    for face in faces:
                        face_center_local = face.calc_center_median()
                        face_center_world = world_matrix @ face_center_local
                        distance = (face_center_world - world_hit_pos).length
                        face_area = face.calc_area()

                        if len(self.temp_mesh.polygons) <= 1000 or not is_complex:
                            # print("Not Complex")
                            # Original weighting for meshes with 1000 faces or fewer
                            ring_weight = 1 / (ring + 1)
                            if face.normal.length > 0 and hit_face_normal.length > 0:
                                angle = face.normal.angle(hit_face_normal)
                                angle_factor = math.pow((math.cos(angle) + 1) / 2, 1.0)
                            else:
                                angle_factor = 0
                            face_weight = ring_weight * face_area * angle_factor / (distance + 0.001)
                        else:
                            # Amplified area weighting for meshes with more than 1000 faces
                            face_weight = max(face_area, 1e-6)  # Ensure a minimum weight
                            # face_weight = face_area  
                            # print("Complex")
                        weighted_normal += face.normal * face_weight
                        total_weight += face_weight

                if total_weight > 1e-6:  # Use a small threshold instead of exactly zero
                    average_normal = (weighted_normal / total_weight).normalized()
                else:
                    print("Warning: Total weight is near zero. Using hit face normal.")
                    average_normal = hit_face_normal.normalized()

                # Transform average normal to world space
                world_normal = (world_matrix.to_3x3().inverted().transposed() @ average_normal).normalized()

                # Calculate view_vector based on the view type
                if is_ortho_camera:
                    view_vector = -ray_direction
                else:
                    view_vector = ray_origin - location

                light_direction = -view_vector.reflect(world_normal)
       

                addon_prefs = context.preferences.addons[__name__].preferences
                initial_light_distance = addon_prefs.initial_light_distance

                if not hasattr(self, 'AdjustingLight') or self.AdjustingLight is None:
                    if "current_proximity" not in self.light:
                        current_proximity = initial_light_distance
                        self.light["current_proximity"] = current_proximity
                    else:
                        current_proximity = self.light["current_proximity"]
                else:
                    current_proximity = self.light["current_proximity"]

                alpha_EMA = 0.65 * self.lerp_factor

                # Apply EMA to the light direction
                if not hasattr(self, 'ema_light_direction'):
                    self.ema_light_direction = light_direction.normalized()
                else:
                    self.ema_light_direction = (alpha_EMA * light_direction.normalized() + (1 - alpha_EMA) * self.ema_light_direction).normalized()
  
            else:


                # Parameters for controlling the "aroundness" area
                initial_num_rays = 20  # 1 main + 19 additional
                initial_radius_percentage = 0.35  # Initial radius in pixels        

                # Get the UI scale factor
                ui_scale = context.preferences.view.ui_scale

                # Get the viewport's height in pixels
                viewport_height = context.region.height

                def cast_additional_rays(num_rays, radius_percentage):
                    viewport_radius_px = (radius_percentage / 100) * viewport_height * ui_scale
                    hit_points = []
                    hit_normals = [normal]

                    for i in range(num_rays):
                        # Generate points in a regular circular pattern
                        theta = (i / num_rays) * 2 * math.pi
                        
                        offset_x = viewport_radius_px * math.cos(theta)
                        offset_y = viewport_radius_px * math.sin(theta)
                        
                        # Calculate new 2D coordinates
                        new_x = event.mouse_region_x + offset_x
                        new_y = event.mouse_region_y + offset_y

                        # Handle orthographic and perspective cases separately
                        if is_ortho_camera:
                            mouse_pos_3d = view3d_utils.region_2d_to_location_3d(region, rv3d, (new_x, new_y), camera_matrix.translation)
                            additional_origin = mouse_pos_3d
                            additional_direction = camera_direction
                        else:
                            additional_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, (new_x, new_y))
                            additional_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, (new_x, new_y))
                        
                        additional_result, additional_location, additional_normal, _, _, _ = context.scene.ray_cast(
                            context.view_layer.depsgraph,
                            additional_origin,
                            additional_direction
                        )
                        
                        if additional_result:
                            hit_points.append(additional_location)
                            hit_normals.append(additional_normal)
                    return hit_points, hit_normals

                hit_points, hit_normals = cast_additional_rays(initial_num_rays, initial_radius_percentage)

                # Transform hit points and normals to local space
                local_hit_points = [world_matrix_inv @ point for point in hit_points]
                local_hit_normals = [(world_matrix_inv.to_3x3() @ normal).normalized() for normal in hit_normals]

                def calculate_normal_from_points(points):
                    if len(points) < 3:
                        return Vector((0, 0, 1))  # Default normal if not enough points
                    center = sum(points, Vector()) / len(points)
                    normal = Vector((0, 0, 0))
                    for i in range(len(points)):
                        p1 = points[i]
                        p2 = points[(i + 1) % len(points)]
                        normal += (p1 - center).cross(p2 - center)
                    return normal.normalized()

                # Calculate normal in local space
                local_normal = calculate_normal_from_points(local_hit_points)

                def calculate_centroid(vectors):
                    """Calculate the centroid of a list of vectors."""
                    return sum(vectors, Vector()) / len(vectors)

                def assign_to_clusters(normals, centroids):
                    """Assign each normal to the closest centroid."""
                    clusters = {i: [] for i in range(len(centroids))}
                    for normal in normals:
                        distances = [(normal - centroid).length for centroid in centroids]
                        closest = distances.index(min(distances))
                        clusters[closest].append(normal)
                    return clusters

                def update_centroids(clusters):
                    """Update centroids based on the clusters formed."""
                    new_centroids = []
                    for index in sorted(clusters):
                        if clusters[index]:
                            new_centroids.append(calculate_centroid(clusters[index]))
                        else:
                            # Handle empty cluster by creating a new random centroid
                            new_centroids.append(Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized())
                    return new_centroids

                def k_means_clustering(normals, k=10, max_iterations=100):
                    """Perform k-means clustering on a list of normals."""
                    if len(normals) < k:
                        return None  # Not enough normals to form k clusters

                    # Initialize centroids randomly from the input normals
                    centroids = random.sample(normals, k)
                    for i in range(max_iterations):
                        clusters = assign_to_clusters(normals, centroids)
                        new_centroids = update_centroids(clusters)
                        if all((new_centroids[j] - centroids[j]).length < 1e-4 for j in range(k)):
                            break  # Centroids have stabilized
                        centroids = new_centroids

                    return clusters, centroids

                def is_surface_smooth(normals, k=10, max_iterations=100, variance_threshold=0.035):
                    """Determine if the surface is smooth based on the uniformity of clusters."""
                    cluster_data = k_means_clustering(normals, k, max_iterations)
                    if cluster_data is None:
                        # print("Not enough data to determine surface smoothness. Assuming smooth.")
                        return True  # Assume smooth if not enough data

                    clusters, centroids = cluster_data
                    for index in sorted(clusters):
                        if clusters[index]:
                            variances = [(normal - centroids[index]).length for normal in clusters[index]]
                            max_variance = max(variances)
                            if max_variance > variance_threshold:
                                # print(f"Not smooth. Cluster {index} has max variance {max_variance:.4f}, exceeding threshold {variance_threshold}")
                                return False
                    
                    # print(f"Smooth. All cluster variances are below threshold {variance_threshold}")
                    return True

                if not is_surface_smooth(local_hit_normals):
                    # Increase sampling for chaotic geometry
                    expanded_num_rays = initial_num_rays * 1
                    expanded_radius_percentage = initial_radius_percentage * 2.2
                    hit_points, hit_normals = cast_additional_rays(expanded_num_rays, expanded_radius_percentage)
                    local_hit_points = [world_matrix_inv @ point for point in hit_points]
                    local_hit_normals = [(world_matrix_inv.to_3x3() @ normal).normalized() for normal in hit_normals]
                    local_normal = calculate_normal_from_points(local_hit_points)
                    alpha_EMA = 0.1

                else:
                    alpha_EMA = 1.0 * self.lerp_factor  

                    
                world_normal = (world_matrix.to_3x3().inverted().transposed() @ local_normal).normalized()

                if is_ortho_camera:
                    view_vector = -ray_direction
                else:
                    view_vector = ray_origin - location

                light_direction = -view_vector.reflect(world_normal)

                


                addon_prefs = context.preferences.addons[__name__].preferences
                initial_light_distance = addon_prefs.initial_light_distance

            

                if not hasattr(self, 'AdjustingLight') or self.AdjustingLight is None:
                    if "current_proximity" not in self.light:
                        current_proximity = initial_light_distance
                        self.light["current_proximity"] = current_proximity
                    else:
                        current_proximity = self.light["current_proximity"]
                else:
                    current_proximity = self.light["current_proximity"]

                # Apply EMA to the light direction
                if not hasattr(self, 'ema_light_direction'):
                    self.ema_light_direction = light_direction.normalized()
                else:
                    self.ema_light_direction = (alpha_EMA * light_direction.normalized() + (1 - alpha_EMA) * self.ema_light_direction).normalized()


            # Calculate new light position using the EMA direction and current proximity
            new_light_location = location + self.ema_light_direction * current_proximity


            # Update light properties with interpolated location
            self.update_light_properties(new_light_location, location)

            # Point light directly at the original hit location
            direction = location - new_light_location
            rot_quat = direction.to_track_quat('-Z', 'Y')
            self.light.rotation_euler = rot_quat.to_euler()

            # Store original hit location for future use
            self.light["target"] = location
            self.empty_location = location
            self.new_target = location

            if hasattr(self, "last_hit_location_2"):
                self.light["last_hit_location_2"] = self.light.get("last_hit_location", location)
            else:
                self.light["last_hit_location_2"] = location

            self.light["last_hit_location"] = location
            
                      


    def update_light_along_normal(self, context, event):
        if not hasattr(self, 'light') or self.light is None:
            return {'CANCELLED'}

        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y

        is_ortho_camera = (rv3d.view_perspective == 'CAMERA' and
                        context.scene.camera.data.type == 'ORTHO')

        if is_ortho_camera:
            camera = context.scene.camera
            camera_matrix = camera.matrix_world
            camera_direction = camera_matrix.to_3x3() @ Vector((0, 0, -1))
            mouse_pos_3d = view3d_utils.region_2d_to_location_3d(region, rv3d, coord, camera_matrix.translation)
            ray_origin = mouse_pos_3d
            ray_direction = camera_direction
        else:
            ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
            ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)

        result, location, normal, index, object, matrix = context.scene.ray_cast(
            context.view_layer.depsgraph,
            ray_origin,
            ray_direction
        )
        if result:
            self.mouse_on_object = object
     

        if result:
            is_instance = False

            # Check if we need to update the evaluated object and temp mesh
            if not hasattr(self, 'temp_mesh') or self.temp_mesh is None or self.current_object_temp_mesh != object:
                # Clear previous temp mesh if it exists
                if hasattr(self, 'evaluated_object') and hasattr(self, 'temp_mesh'):
                    self.evaluated_object.to_mesh_clear()
                    # print("Cleared existing temp mesh")
                
                # Get the evaluated object with modifiers applied
                depsgraph = context.evaluated_depsgraph_get()
                self.current_object_temp_mesh = object
                self.evaluated_object = object.evaluated_get(depsgraph)
                # Try to convert the evaluated object to a mesh
                try:
                    self.temp_mesh = self.evaluated_object.to_mesh()
                except RuntimeError:
                    
                    self.temp_mesh = None
                
 
            # Get the object's scale
            object_scale = self.evaluated_object.matrix_world.to_scale()

            # Calculate the maximum scale component
            max_scale = max(object_scale)

            # Ensure the temp_mesh is valid and has polygons
            if self.temp_mesh and self.temp_mesh.polygons and index < len(self.temp_mesh.polygons):
                hit_polygon = self.temp_mesh.polygons[index]
                hit_polygon_center = self.evaluated_object.matrix_world @ hit_polygon.center

                # Adjust max_vertex_distance calculation
                max_vertex_distance = max((self.temp_mesh.vertices[vertex].co - hit_polygon.center).length for vertex in hit_polygon.vertices)
                max_vertex_distance *= max_scale  # Scale the distance

                is_instance = (location - hit_polygon_center).length > max_vertex_distance
            else:
                
                self.temp_mesh = None


          
            # Get world matrix and its inverse
            world_matrix = self.evaluated_object.matrix_world
            world_matrix_inv = world_matrix.inverted()

            if hasattr(self.evaluated_object.data, 'polygons') and (not is_instance and len(self.evaluated_object.data.polygons) < 350000) and self.temp_mesh != None:
          


                # Get local hit position
                local_hit_pos = world_matrix_inv @ location

                # Create bmesh from temp_mesh
                if not hasattr(self, 'bm') or self.bm is None or self.current_object_bmesh != object:
                    if hasattr(self, 'bm') and self.bm is not None:
                        self.bm.free()
                        # print("Freed existing BMesh")
                    self.bm = bmesh.new()
                    self.bm.from_mesh(self.temp_mesh)
                    self.bm.faces.ensure_lookup_table()
                    self.current_object_bmesh = object
                #     print(f"Created new bmesh with {len(self.bm.faces)} faces for object: {object.name}")
                # else:
                #     print(f"Using existing bmesh with {len(self.bm.faces)} faces for object: {object.name}")

                # Function to get neighboring faces
                def get_neighboring_faces(bm, start_face, max_rings):
                    face_rings = [{start_face}]
                    visited = {start_face}
                    for _ in range(max_rings):
                        new_ring = set()
                        for face in face_rings[-1]:
                            for vert in face.verts:
                                for neighbor_face in vert.link_faces:
                                    if neighbor_face not in visited:
                                        new_ring.add(neighbor_face)
                                        visited.add(neighbor_face)
                        if not new_ring:
                            break
                        face_rings.append(new_ring)
                    return face_rings

                # Check if the index is within the valid range for BMesh faces
                if index < len(self.bm.faces):
                    start_face = self.bm.faces[index]
                else:
                    # print(f"Warning: Face index {index} out of range. Using closest face.")
                    # Find the closest face in the BMesh
                    start_face = min(self.bm.faces, key=lambda f: (f.calc_center_median() - local_hit_pos).length)

                # Get neighboring faces
                max_rings = min(1 + len(self.bm.faces) // 1000, 6)
                face_rings = get_neighboring_faces(self.bm, start_face, max_rings)

                # world_matrix = self.evaluated_object.matrix_world
                world_hit_pos = world_matrix @ local_hit_pos

                weighted_normal = Vector((0, 0, 0))
                total_weight = 0

                # Get the normal of the hit face
                hit_face_normal = start_face.normal



                # Simple k-means clustering implementation
                def kmeans_clustering(data, k, max_iterations=100):

                    # Initialize centroids randomly
                    centroids = random.sample(data, k)
                    
                    for _ in range(max_iterations):
                        # Assign points to clusters
                        clusters = [[] for _ in range(k)]
                        for point in data:
                            distances = [(point - c).length_squared for c in centroids]
                            closest_centroid = distances.index(min(distances))
                            clusters[closest_centroid].append(point)
                        
                        # Update centroids
                        new_centroids = []
                        for cluster in clusters:
                            if cluster:
                                new_centroid = Vector((0, 0, 0))
                                for point in cluster:
                                    new_centroid += point
                                new_centroid /= len(cluster)
                                new_centroids.append(new_centroid)
                            else:
                                new_centroids.append(random.choice(data))
                        
                        # Check for convergence
                        if all((c1 - c2).length < 0.001 for c1, c2 in zip(centroids, new_centroids)):
                            break
                        
                        centroids = new_centroids
                    
                    return centroids, clusters

                # Function to determine geometry complexity
                def is_complex_geometry(bm, sample_size=100, n_clusters=3):
                    # Convert BMFaces to a list that can be sampled
                    faces = list(bm.faces)
                    
                    if len(faces) <= sample_size:
                        sample = faces
                    else:
                        sample = random.sample(faces, sample_size)
                    
                    # Convert face normals to Vector
                    normals = [face.normal.copy() for face in sample]

                    # Adjust n_clusters if there are fewer normals than clusters
                    n_clusters = min(n_clusters, len(normals))

                    # Perform k-means clustering
                    centroids, clusters = kmeans_clustering(normals, n_clusters)

                    # Calculate the average distance to cluster centers
                    total_distance = sum(min((normal - centroid).length for centroid in centroids) for normal in normals)
                    avg_distance = total_distance / len(normals)

                    # You can adjust this threshold as needed
                    return avg_distance > 0.5  # Consider complex if average distance to cluster centers is high

                is_complex = is_complex_geometry(self.bm)

                for ring, faces in enumerate(face_rings):
                    for face in faces:
                        face_center_local = face.calc_center_median()
                        face_center_world = world_matrix @ face_center_local
                        distance = (face_center_world - world_hit_pos).length
                        face_area = face.calc_area()

                        if len(self.temp_mesh.polygons) <= 1000 or not is_complex:
                            # print("Not Complex")
                            # Original weighting for meshes with 1000 faces or fewer
                            ring_weight = 1 / (ring + 1)
                            if face.normal.length > 0 and hit_face_normal.length > 0:
                                angle = face.normal.angle(hit_face_normal)
                                angle_factor = math.pow((math.cos(angle) + 1) / 2, 1.0)
                            else:
                                angle_factor = 0
                            face_weight = ring_weight * face_area * angle_factor / (distance + 0.001)
                        else:
                            # Amplified area weighting for meshes with more than 1000 faces
                            face_weight = max(face_area, 1e-6)  # Ensure a minimum weight
                            # face_weight = face_area  
                            # print("Complex")
                        weighted_normal += face.normal * face_weight
                        total_weight += face_weight

                if total_weight > 1e-6:  # Use a small threshold instead of exactly zero
                    average_normal = (weighted_normal / total_weight).normalized()
                else:
                    # print("Warning: Total weight is near zero. Using hit face normal.")
                    average_normal = hit_face_normal.normalized()

                # Transform average normal to world space
                world_normal = (world_matrix.to_3x3().inverted().transposed() @ average_normal).normalized()

                # # Calculate view_vector based on the view type
                # if is_ortho_camera:
                #     view_vector = -ray_direction
                # else:
                #     view_vector = ray_origin - location

                light_direction = world_normal
       

                addon_prefs = context.preferences.addons[__name__].preferences
                initial_light_distance = addon_prefs.initial_light_distance

                if not hasattr(self, 'AdjustingLight') or self.AdjustingLight is None:
                    if "current_proximity" not in self.light:
                        current_proximity = initial_light_distance
                        self.light["current_proximity"] = current_proximity
                    else:
                        current_proximity = self.light["current_proximity"]
                else:
                    current_proximity = self.light["current_proximity"]

                alpha_EMA = 0.65 * self.lerp_factor

                # Apply EMA to the light direction
                if not hasattr(self, 'ema_light_direction'):
                    self.ema_light_direction = light_direction.normalized()
                else:
                    self.ema_light_direction = (alpha_EMA * light_direction.normalized() + (1 - alpha_EMA) * self.ema_light_direction).normalized()
  
            else:


                # Parameters for controlling the "aroundness" area
                initial_num_rays = 20  # 1 main + 19 additional
                initial_radius_percentage = 0.35  # Initial radius in pixels        

                # Get the UI scale factor
                ui_scale = context.preferences.view.ui_scale

                # Get the viewport's height in pixels
                viewport_height = context.region.height

                def cast_additional_rays(num_rays, radius_percentage):
                    viewport_radius_px = (radius_percentage / 100) * viewport_height * ui_scale
                    hit_points = []
                    hit_normals = [normal]

                    for i in range(num_rays):
                        # Generate points in a regular circular pattern
                        theta = (i / num_rays) * 2 * math.pi
                        
                        offset_x = viewport_radius_px * math.cos(theta)
                        offset_y = viewport_radius_px * math.sin(theta)
                        
                        # Calculate new 2D coordinates
                        new_x = event.mouse_region_x + offset_x
                        new_y = event.mouse_region_y + offset_y

                        # Handle orthographic and perspective cases separately
                        if is_ortho_camera:
                            mouse_pos_3d = view3d_utils.region_2d_to_location_3d(region, rv3d, (new_x, new_y), camera_matrix.translation)
                            additional_origin = mouse_pos_3d
                            additional_direction = camera_direction
                        else:
                            additional_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, (new_x, new_y))
                            additional_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, (new_x, new_y))
                        
                        additional_result, additional_location, additional_normal, _, _, _ = context.scene.ray_cast(
                            context.view_layer.depsgraph,
                            additional_origin,
                            additional_direction
                        )
                        
                        if additional_result:
                            hit_points.append(additional_location)
                            hit_normals.append(additional_normal)
                    return hit_points, hit_normals

                hit_points, hit_normals = cast_additional_rays(initial_num_rays, initial_radius_percentage)

                # Transform hit points and normals to local space
                local_hit_points = [world_matrix_inv @ point for point in hit_points]
                local_hit_normals = [(world_matrix_inv.to_3x3() @ normal).normalized() for normal in hit_normals]

                def calculate_normal_from_points(points):
                    if len(points) < 3:
                        return Vector((0, 0, 1))  # Default normal if not enough points
                    center = sum(points, Vector()) / len(points)
                    normal = Vector((0, 0, 0))
                    for i in range(len(points)):
                        p1 = points[i]
                        p2 = points[(i + 1) % len(points)]
                        normal += (p1 - center).cross(p2 - center)
                    return normal.normalized()

                # Calculate normal in local space
                local_normal = calculate_normal_from_points(local_hit_points)

                def calculate_centroid(vectors):
                    """Calculate the centroid of a list of vectors."""
                    return sum(vectors, Vector()) / len(vectors)

                def assign_to_clusters(normals, centroids):
                    """Assign each normal to the closest centroid."""
                    clusters = {i: [] for i in range(len(centroids))}
                    for normal in normals:
                        distances = [(normal - centroid).length for centroid in centroids]
                        closest = distances.index(min(distances))
                        clusters[closest].append(normal)
                    return clusters

                def update_centroids(clusters):
                    """Update centroids based on the clusters formed."""
                    new_centroids = []
                    for index in sorted(clusters):
                        if clusters[index]:
                            new_centroids.append(calculate_centroid(clusters[index]))
                        else:
                            # Handle empty cluster by creating a new random centroid
                            new_centroids.append(Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized())
                    return new_centroids

                def k_means_clustering(normals, k=10, max_iterations=100):
                    """Perform k-means clustering on a list of normals."""
                    if len(normals) < k:
                        return None  # Not enough normals to form k clusters

                    # Initialize centroids randomly from the input normals
                    centroids = random.sample(normals, k)
                    for i in range(max_iterations):
                        clusters = assign_to_clusters(normals, centroids)
                        new_centroids = update_centroids(clusters)
                        if all((new_centroids[j] - centroids[j]).length < 1e-4 for j in range(k)):
                            break  # Centroids have stabilized
                        centroids = new_centroids

                    return clusters, centroids

                def is_surface_smooth(normals, k=10, max_iterations=100, variance_threshold=0.035):
                    """Determine if the surface is smooth based on the uniformity of clusters."""
                    cluster_data = k_means_clustering(normals, k, max_iterations)
                    if cluster_data is None:
                        # print("Not enough data to determine surface smoothness. Assuming smooth.")
                        return True  # Assume smooth if not enough data

                    clusters, centroids = cluster_data
                    for index in sorted(clusters):
                        if clusters[index]:
                            variances = [(normal - centroids[index]).length for normal in clusters[index]]
                            max_variance = max(variances)
                            if max_variance > variance_threshold:
                                # print(f"Not smooth. Cluster {index} has max variance {max_variance:.4f}, exceeding threshold {variance_threshold}")
                                return False
                    
                    # print(f"Smooth. All cluster variances are below threshold {variance_threshold}")
                    return True

                if not is_surface_smooth(local_hit_normals):
                    # Increase sampling for chaotic geometry
                    expanded_num_rays = initial_num_rays * 1
                    expanded_radius_percentage = initial_radius_percentage * 2.2
                    hit_points, hit_normals = cast_additional_rays(expanded_num_rays, expanded_radius_percentage)
                    local_hit_points = [world_matrix_inv @ point for point in hit_points]
                    local_hit_normals = [(world_matrix_inv.to_3x3() @ normal).normalized() for normal in hit_normals]
                    local_normal = calculate_normal_from_points(local_hit_points)
                    alpha_EMA = 0.1

                else:
                    alpha_EMA = 1.0 * self.lerp_factor  

                    
                world_normal = (world_matrix.to_3x3().inverted().transposed() @ local_normal).normalized()

                # if is_ortho_camera:
                #     view_vector = -ray_direction
                # else:
                #     view_vector = ray_origin - location

                light_direction = world_normal

                


                addon_prefs = context.preferences.addons[__name__].preferences
                initial_light_distance = addon_prefs.initial_light_distance

            

                if not hasattr(self, 'AdjustingLight') or self.AdjustingLight is None:
                    if "current_proximity" not in self.light:
                        current_proximity = initial_light_distance
                        self.light["current_proximity"] = current_proximity
                    else:
                        current_proximity = self.light["current_proximity"]
                else:
                    current_proximity = self.light["current_proximity"]

                # Apply EMA to the light direction
                if not hasattr(self, 'ema_light_direction'):
                    self.ema_light_direction = light_direction.normalized()
                else:
                    self.ema_light_direction = (alpha_EMA * light_direction.normalized() + (1 - alpha_EMA) * self.ema_light_direction).normalized()


            # Calculate new light position using the EMA direction and current proximity
            new_light_location = location + self.ema_light_direction * current_proximity


            # Update light properties with interpolated location
            self.update_light_properties(new_light_location, location)

            # Point light directly at the original hit location
            direction = location - new_light_location
            rot_quat = direction.to_track_quat('-Z', 'Y')
            self.light.rotation_euler = rot_quat.to_euler()

            # Store original hit location for future use
            self.light["target"] = location
            self.empty_location = location
            self.new_target = location


            if hasattr(self, "last_hit_location_2"):
                self.light["last_hit_location_2"] = self.light.get("last_hit_location", location)
            else:
                self.light["last_hit_location_2"] = location

            self.light["last_hit_location"] = location


    def update_light_in_orbit_mode(self, context, event):
        bpy.types.Scene.modal_running = True
        if self.initial_mouse_pos is None:
            self.initial_mouse_pos = Vector(
                (event.mouse_region_x, event.mouse_region_y)
            )
            self.initial_light_vector = self.light.location - self.orbit_center

        current_mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        mouse_delta = current_mouse_pos - self.initial_mouse_pos

        view_matrix = context.region_data.view_matrix
        view_right = Vector(view_matrix[0][:3])
        view_up = Vector(view_matrix[1][:3])

        rotation_vector = (
            view_right * -mouse_delta.y + view_up * mouse_delta.x
        ) * 0.006

        rot_mat = Matrix.Rotation(
            rotation_vector.length, 4, rotation_vector.normalized()
        )
        new_light_vector = rot_mat @ self.initial_light_vector
        if "current_proximity" in self.light:
            new_light_vector = (
                new_light_vector.normalized() * self.light["current_proximity"]
            )
        else:
            addon_prefs = context.preferences.addons[__name__].preferences
            initial_light_distance = addon_prefs.initial_light_distance
            new_light_vector = new_light_vector.normalized() * initial_light_distance

        self.light.location = self.orbit_center + new_light_vector

        self.initial_mouse_pos = current_mouse_pos
        self.initial_light_vector = self.light.location - self.orbit_center

        direction_vector = self.light.location - self.orbit_center
        rot_quat = direction_vector.to_track_quat("Z", "Y")
        self.light.rotation_euler = rot_quat.to_euler()

        sphere_empty = bpy.data.objects.get(self.sphere_empty_name, None)
        if sphere_empty:
            self.light["target"] = self.orbit_center
            self.new_target = self.orbit_center
            direction_vector = self.light.location - self.orbit_center
            rot_quat = direction_vector.to_track_quat("Z", "Y")
            sphere_empty.rotation_euler = rot_quat.to_euler()

    def update_light_properties(self, light_location, location):
        scene = bpy.context.scene
        view_layer = bpy.context.view_layer
        addon_prefs = bpy.context.preferences.addons[__name__].preferences

        light_type = self.light.data.type

        ground_level_detected = float("-inf")
        if addon_prefs.detect_ground_ceiling:
            ray_start_down = Vector(
                (light_location.x, light_location.y, location.z + 0.01)
            )
            ray_end_down = Vector((light_location.x, light_location.y, -1000))
            ray_direction_down = ray_end_down - ray_start_down
            hit_down, hit_location_down, _, _, _, _ = scene.ray_cast(
                view_layer.depsgraph, ray_start_down, ray_direction_down.normalized()
            )

            if hit_down:
                ground_level_detected = hit_location_down.z

        manual_ground_level = (
            addon_prefs.manual_ground_level
            if addon_prefs.use_manual_ground_level
            else float("-inf")
        )
        effective_ground_level = max(ground_level_detected, manual_ground_level)

        if light_type == "AREA":
            light_size_half = self.light.data.size / 2
        elif light_type == "SPOT":
            light_size_half = 0
        else:
            light_size_half = 0  # Default for other light types

        if light_location.z < effective_ground_level + light_size_half:
            light_location.z = effective_ground_level + light_size_half

        self.light.location = light_location

        direction_vector = light_location - location
        rot_quat = direction_vector.to_track_quat("Z", "Y")
        self.light.rotation_euler = rot_quat.to_euler()

    def cancel(self, context):

        self.cleanup()





def hextorgb(hex_color):

    hex_color = hex_color.lstrip("#")
    lv = len(hex_color)
    return tuple(
        int(hex_color[i : i + lv // 3], 16) / 255.0 for i in range(0, lv, lv // 3)
    )



class LIGHT_GGT_lw_viewport_gizmos(bpy.types.GizmoGroup):
    bl_idname = "LIGHT_GGT_lw_viewport_gizmos"
    bl_label = "Viewport Gizmos"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', 'SCALE', 'SHOW_MODAL_ALL', 'SELECT'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'LIGHT'

    def setup(self, context):
        
        alpha = 0.8
        color = (0.15, 0.15, 0.15)
        color_highlight = (0.4, 0.4, 0.4)
        alpha_highlight = 0.8
        scale_basis = 14.5

        # Visibility toggle gizmo
        self.visibility_gizmo = self.create_gizmo(context, "GIZMO_GT_button_2d", "SOLO_ON", alpha, color, color_highlight, alpha_highlight, scale_basis, "light.lw_toggle_visibility", "Toggle Light Visibility")

        # # Energy gizmo
        # self.energy_gizmo = self.create_gizmo(context, "GIZMO_GT_button_2d", "SOLO_ON", alpha, color, color_highlight, alpha_highlight, scale_basis, "light.adjust_energy", "Adjust Light Energy")

        # # Color gizmo
        # self.color_gizmo = self.create_gizmo(context, "GIZMO_GT_button_2d", "COLOR", alpha, color, color_highlight, alpha_highlight, scale_basis, "light.adjust_color", "Adjust Light Color")

    def create_gizmo(self, context, gizmo_type, icon, alpha, color, color_highlight, alpha_highlight, scale_basis, operator, description):
        gzm = self.gizmos.new(gizmo_type)
        gzm.icon = icon
        gzm.draw_options = {'BACKDROP', 'OUTLINE'}
        gzm.scale_basis = scale_basis
        gzm.color = color
        gzm.alpha = alpha
        gzm.color_highlight = color_highlight
        gzm.alpha_highlight = alpha_highlight
        gzm.target_set_operator(operator)
        gzm.use_draw_modal = True
        return gzm


    def draw_prepare(self, context):
        light = context.object
        ui_scale = context.preferences.system.ui_scale

        # Base UI scale for which the current values are optimized
        base_ui_scale = 1.25
        scale_factor = ui_scale / base_ui_scale

        # Dynamically adjust margins and gap between gizmos based on UI scale
        margin_x = 28 * scale_factor  # Adjusted gap from the right edge of the viewport
        margin_y = 90 * scale_factor  # Adjusted gap from the bottom edge of the viewport
        base_gap_between_gizmos = 36 * scale_factor  # Adjusted base gap between gizmos

        # Assuming fixed gizmo height for simplicity, adjust as necessary
        # Adjust gizmo height based on UI scale to keep consistent proportions
        gizmo_height = 2 * scale_factor  # Example adjusted height of each gizmo

        # Determine if the current light is the only visible light
        light_objects = [obj for obj in bpy.data.objects if obj.type == 'LIGHT']
        only_light_visible = len(light_objects) > 1 and all(obj.hide_viewport or obj == light for obj in light_objects)

        # Update gizmo color based on the light's isolation status
        if light:
            # Change gizmo color if the current light is isolated
            if only_light_visible:
                self.visibility_gizmo.color = hextorgb("f2a249")  # Color to indicate isolation
            else:
                self.visibility_gizmo.color = (0.35, 0.35, 0.35) if light.hide_viewport else (0.15, 0.15, 0.15)  # Default color

        # Calculate positions for gizmos dynamically
        gizmos = [self.visibility_gizmo]
        viewport_width = context.area.width  # Obtain the viewport width

        for i, gizmo in enumerate(gizmos):
            # Position each gizmo with a consistent gap from the right
            pos_x = viewport_width - margin_x  # X position remains constant, aligned to the right
            
            # Calculate the Y position for each gizmo starting from the bottom
            pos_y = margin_y + (gizmo_height + base_gap_between_gizmos) * i

            # Apply the calculated positions to the gizmo matrix
            gizmo.matrix_basis[0][3] = pos_x
            gizmo.matrix_basis[1][3] = pos_y
            gizmo.matrix_basis[2][3] = 0  # Z position remains 0 for 2D gizmos


class LightVisibilityState(PropertyGroup):
    name: bpy.props.StringProperty()
    hide_viewport: BoolProperty()
    emission_strength: FloatProperty()

class WorldNodeMuteState(PropertyGroup):
    name: bpy.props.StringProperty()
    mute: BoolProperty()

class LightWranglerProperties(PropertyGroup):
    is_isolated: BoolProperty(default=False)
    original_states: CollectionProperty(type=LightVisibilityState)
    original_world_states: CollectionProperty(type=WorldNodeMuteState)


is_handling_selection_change = False
is_operator_isolating = False

class LIGHT_OT_lw_toggle_visibility(Operator):
    """Isolate current light"""
    bl_idname = "light.lw_toggle_visibility"
    bl_label = "Toggle Light Visibility"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global is_operator_isolating
        is_operator_isolating = True
        
        scene = context.scene
        current_object = context.object

        def world_is_emitting():
            if scene.world and scene.world.node_tree:
                for node in scene.world.node_tree.nodes:
                    if node.type in {'BACKGROUND', 'EMISSION', 'BSDF_PRINCIPLED'}:
                        if node.inputs['Strength'].default_value > 0:
                            return True
                output_node = next((node for node in scene.world.node_tree.nodes if node.type == 'OUTPUT_WORLD'), None)
                if output_node and output_node.inputs['Surface'].links:
                    return True
            return False

        def get_emitting_nodes():
            if scene.world and scene.world.node_tree:
                return [node for node in scene.world.node_tree.nodes 
                        if node.type in {'BACKGROUND', 'EMISSION', 'BSDF_PRINCIPLED'}]
            return []

        def is_emission_object(obj):
            if obj.type == 'MESH' and obj.active_material and obj.active_material.node_tree:
                for node in obj.active_material.node_tree.nodes:
                    if node.type == 'EMISSION':
                        if node.inputs['Strength'].default_value > 0:
                            return True
                    elif node.type == 'BSDF_PRINCIPLED':
                        if 'Emission Strength' in node.inputs and node.inputs['Emission Strength'].default_value > 0:
                            return True
            return False

        def get_emission_strength(obj):
            if obj.active_material and obj.active_material.node_tree:
                for node in obj.active_material.node_tree.nodes:
                    if node.type == 'EMISSION':
                        return node.inputs['Strength'].default_value
                    elif node.type == 'BSDF_PRINCIPLED':
                        if 'Emission Strength' in node.inputs:
                            return node.inputs['Emission Strength'].default_value
            return 0

        def set_emission_strength(obj, strength):
            if obj.active_material and obj.active_material.node_tree:
                for node in obj.active_material.node_tree.nodes:
                    if node.type == 'EMISSION':
                        node.inputs['Strength'].default_value = strength
                    elif node.type == 'BSDF_PRINCIPLED':
                        if 'Emission Strength' in node.inputs:
                            node.inputs['Emission Strength'].default_value = strength

        is_world_background = current_object is None and world_is_emitting()

        # Separate light objects and emissive objects
        light_sources = [obj for obj in bpy.data.objects if obj.type == 'LIGHT']
        emissive_objects = [obj for obj in bpy.data.objects if is_emission_object(obj)]
        
        if not scene.light_wrangler.is_isolated:
            # Store the original visibility state for lights and emission strength for emissive objects
            scene.light_wrangler.original_states.clear()
            for obj in light_sources + emissive_objects:
                item = scene.light_wrangler.original_states.add()
                item.name = obj.name
                item.hide_viewport = obj.hide_viewport if obj.type == 'LIGHT' else False
                item.emission_strength = get_emission_strength(obj) if obj.type != 'LIGHT' else 0

            scene.light_wrangler.original_world_states.clear()
            for node in get_emitting_nodes():
                item = scene.light_wrangler.original_world_states.add()
                item.name = node.name
                item.mute = node.mute

            # Hide all light sources except current, and handle emissive objects
            for obj in light_sources:
                obj.hide_viewport = obj != current_object if current_object else True
            
            for obj in emissive_objects:
                set_emission_strength(obj, 0 if obj != current_object else get_emission_strength(obj))
            
            for node in get_emitting_nodes():
                node.mute = not is_world_background
            
            scene.light_wrangler.is_isolated = True
        else:
            # Revert to original states
            for item in scene.light_wrangler.original_states:
                obj = bpy.data.objects.get(item.name)
                if obj:
                    if obj.type == 'LIGHT':
                        obj.hide_viewport = item.hide_viewport
                    else:
                        set_emission_strength(obj, item.emission_strength)

            for item in scene.light_wrangler.original_world_states:
                node = scene.world.node_tree.nodes.get(item.name)
                if node:
                    node.mute = item.mute
            
            scene.light_wrangler.is_isolated = False

        # Update the viewport
        context.view_layer.update()

        is_operator_isolating = False
        return {'FINISHED'}

@persistent
def light_selection_handler(scene):
    global is_handling_selection_change, is_operator_isolating
    if is_handling_selection_change or is_operator_isolating:
        return

    current_object = bpy.context.view_layer.objects.active

    if scene.light_wrangler.is_isolated:
        if not current_object or current_object.type != 'LIGHT':
            # The isolated light was deselected or a non-light was selected
            is_handling_selection_change = True
            
            # Call the toggle_visibility operator to revert the isolation
            bpy.ops.light.lw_toggle_visibility()
            
            is_handling_selection_change = False
        elif current_object and current_object.type == 'LIGHT':
            # A different light was selected while in isolation mode
            is_handling_selection_change = True
            
            # Get all light objects
            light_objects = [obj for obj in bpy.data.objects if obj.type == 'LIGHT']
            
            # Hide all lights except the newly selected one
            for light in light_objects:
                light.hide_viewport = (light != current_object)
            
            # Update the viewport
            bpy.context.view_layer.update()
            
            is_handling_selection_change = False



class LightIntersectionGizmoGroup(bpy.types.GizmoGroup):
    bl_idname = "OBJECT_GGT_light_intersection"
    bl_label = "Light Intersection Gizmo"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"3D", "PERSISTENT"}

    @classmethod
    def poll(cls, context):
        # Check if the active object is a selected area or spot light
        active_obj = context.active_object
        return (active_obj and
                active_obj.type == "LIGHT" and
                active_obj.data.type in {"AREA", "SPOT"} and
                active_obj in context.selected_objects)

    def setup(self, context):
        # Get the color for selected objects from the current theme
        object_selected_color = bpy.context.preferences.themes[0].view_3d.object_selected
        color = list(object_selected_color)[:3]

        # Get the current light adjustment mode
        light_adjust_mode = context.object.get("light_adjust_mode", "reflect")

        # Create gizmo based on the light adjustment mode
        gizmo_configs = {
            "reflect": ("GIZMO_GT_move_3d", "RING_2D", {"ALIGN_VIEW"}, 0.055, self.hextorgb("F3F3F7"), "object.adjust_light_position"),
            "direct": ("GIZMO_GT_move_3d", "RING_2D", {"FILL", "ALIGN_VIEW"}, 0.055, self.hextorgb("F3F3F7"), "object.three_adjust_light_position"),
            "orbit": ("GIZMO_GT_dial_3d", "RING_2D", {"FILL_SELECT", "ANGLE_MIRROR"}, 0.12, color, "object.two_adjust_light_position")
        }

        if light_adjust_mode in gizmo_configs:
            self.create_gizmo(light_adjust_mode, *gizmo_configs[light_adjust_mode])

    def hextorgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return [int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4)]

    def create_gizmo(self, mode, gizmo_type, draw_style, draw_options, scale_basis, color, target_operator):
        mpr = self.gizmos.new(gizmo_type)
        if gizmo_type != "GIZMO_GT_dial_3d":
            mpr.draw_style = draw_style
        mpr.draw_options = draw_options
        mpr.scale_basis = scale_basis
        mpr.color = color
        mpr.alpha = 1
        mpr.target_set_operator(target_operator)
        light_obj = bpy.context.object
        mpr.matrix_basis = light_obj.matrix_world.normalized()

    def clear_gizmos(self):
        # Remove all existing gizmos
        for gz in self.gizmos:
            self.gizmos.remove(gz)

    def refresh(self, context):
        if not self.gizmos:
            return

        light_obj = context.object
        self.clear_gizmos()
        self.setup(context)
        depsgraph = context.evaluated_depsgraph_get()

        for mpr in self.gizmos:
            self.update_gizmo_position(mpr, light_obj, depsgraph)

    def update_gizmo_position(self, mpr, light_obj, depsgraph):


        target = light_obj.get("target", None)
        # Get the light's current forward direction (assuming -Z is forward)
        light_forward = (light_obj.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))).normalized()
        if target is not None:
            # Calculate direction from light to target
            light_to_target = (Vector(target) - light_obj.location).normalized()
            # Calculate the angle between the two directions
            angle = light_forward.angle(light_to_target)
            # Define a small tolerance (in radians)
            tolerance = math.radians(0.2)
            if angle <= tolerance:
                # The target is valid; position gizmo at target
                mpr.matrix_basis = Matrix.Translation(target)
                return
        # If target is invalid or doesn't exist, perform ray cast
        ray_origin = light_obj.location
        ray_direction = light_forward
        result, location, normal, index, object, matrix = depsgraph.scene.ray_cast(
            depsgraph, ray_origin, ray_direction
        )
        if result:
            mpr.matrix_basis = Matrix.Translation(location)
        else:
            # Place gizmo at a default distance along the light's forward direction
            default_distance = 10.0  # Adjust as needed
            fallback_location = ray_origin + ray_direction * default_distance
            mpr.matrix_basis = Matrix.Translation(fallback_location)




class LightOperationsSubMenu(bpy.types.Menu):
    bl_label = "Light Operations"
    bl_idname = "OBJECT_MT_light_operations_submenu"

    def draw(self, context):
        layout = self.layout

        # Define menu items with their respective operators, text, and icons
        menu_items = [
            (ProxyLightAtPointOperator.bl_idname, "Add Light", "LIGHT_AREA"),
            (TabAdjustLightPositionOperator.bl_idname, "Adjust Light", "ARROW_LEFTRIGHT"),
            (AddEmptyAtIntersectionOperator.bl_idname, "Track to Target", "CON_TRACKTO"),
            (CopyAndAdjustLightOperator.bl_idname, "Duplicate Light", "DUPLICATE"),
        ]

        # Add standard menu items
        for operator, text, icon in menu_items:
            layout.operator(operator, text=text, icon=icon)

        # Add "Convert to HDRI" option for Scrim lights
        active_obj = context.active_object
        if (active_obj and 
            active_obj.type == 'LIGHT' and 
            active_obj.data.type == 'AREA' and
            active_obj.get("customization", "") == "Scrim"):
            layout.operator("scene.render_scrim", text="Convert to HDRI", icon='IMAGE_DATA')

        # Add preferences option
        layout.operator(OpenAddonPreferencesOperator.bl_idname, text="Preferences", icon="PREFERENCES")


def menu_func_light_add(self, context):
    # Add "Area (Auto)" option to the Add Light menu if the render engine is compatible
    if check_render_engine():
        self.layout.operator(
            LightAtPointOperator.bl_idname, text="Area (Auto)", icon="LIGHT_AREA"
        )

def menu_func_context_menu(self, context):
    # Add "Light Operations" submenu to the context menu if the render engine is compatible
    if check_render_engine():
        self.layout.separator()
        self.layout.menu(LightOperationsSubMenu.bl_idname, text="Light Operations")
        self.layout.separator()

def toggle_collection_hotkeys(key_types, action_idname, enable=True):
    """
    Toggle the active state of collection hotkeys.
    
    :param key_types: List of key types to toggle
    :param action_idname: The idname of the action to toggle
    :param enable: Whether to enable (True) or disable (False) the hotkeys
    """
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    target_keymaps = ["Object Mode", "3D View"]

    for key_type in key_types:
        for keymap_name, keymap in kc.keymaps.items():
            if keymap_name in target_keymaps:
                for item in keymap.keymap_items:
                    try:
                        if item.type == key_type and item.idname == action_idname:
                            item.active = enable
                    except Exception as e:
                        print(f"Error {'enabling' if enable else 'disabling'} hotkey {key_type} in {keymap_name}: {e}")

def disable_collection_hotkeys(key_types, action_idname):
    # Disable specified collection hotkeys
    toggle_collection_hotkeys(key_types, action_idname, enable=False)

def enable_collection_hotkeys(key_types, action_idname):
    # Enable specified collection hotkeys
    toggle_collection_hotkeys(key_types, action_idname, enable=True)

def load_sync():
    # Synchronize node values for the current scene
    current_scene = bpy.context.scene
    sync_node_values_handler(current_scene)

@persistent
def after_load_handler(dummy):
    """
    Handler that runs after a blend file is loaded.
    Ensures all necessary handlers are registered and syncs node values.
    """
    handlers = [
        (bpy.app.handlers.depsgraph_update_post, update_light_spread),
        (bpy.app.handlers.depsgraph_update_pre, light_type_changed),
        (bpy.app.handlers.depsgraph_update_post, sync_node_values_handler),
        (bpy.app.handlers.depsgraph_update_post, update_light_visibility),
        (bpy.app.handlers.depsgraph_update_post, light_selection_handler)
    ]
    # Add handlers if they're not already registered
    for handler_list, func in handlers:
        if func not in handler_list:
            handler_list.append(func)
    # Sync node values
    load_sync()

def register():
    # Register classes
    classes = [
        ClearHDRIDirectoryPath, ClearGoboDirectoryPath, LightWranglerPreferences,
        LightVisibilityState, WorldNodeMuteState, LightWranglerProperties,
        LIGHT_OT_apply_custom_data_block, OpenAddonPreferencesOperator, MainPanel,
        LightIntersectionGizmoGroup, LIGHT_GGT_lw_viewport_gizmos,
        LIGHT_OT_lw_toggle_visibility, LightWranglerHintsProperties,
        ConvertToPlaneOperator, RefreshHDRIPath, RefreshGoboPath,
        CopyAndAdjustLightOperator, LightOperationsSubMenu, OpenMailOperator,
        ProxyLightAtPointOperator, AddEmptyAtIntersectionOperator, LightAtPointOperator,
        AdjustLightPositionOperator, Two_AdjustLightPositionOperator,
        Three_AdjustLightPositionOperator, TabAdjustLightPositionOperator,
        LightWranglerSettings, OBJECT_OT_LightTypeChanged, LIGHT_OT_ScrimPreviewCreator,
        RenderScrimOperator, Render360HDROperator, HDRI_PT_RenderPanel,
        RefreshIESPath, ClearIESDirectoryPath
    ]
    for cls in classes:
        bpy.utils.register_class(cls)

    # Disable collection hotkeys
    disable_collection_hotkeys(["ONE", "TWO", "THREE"], "object.hide_collection")

    # Add menu items
    bpy.types.VIEW3D_MT_object_context_menu.prepend(menu_func_context_menu)
    bpy.types.VIEW3D_MT_light_add.append(menu_func_light_add)

    # Apply preferences
    apply_preferences()

    # Register properties
    bpy.types.Scene.light_wrangler = PointerProperty(type=LightWranglerProperties)
    bpy.types.WindowManager.is_light_adjust_active = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.light_wrangler_settings = bpy.props.PointerProperty(type=LightWranglerSettings)
    bpy.types.Scene.modal_running = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.light_wrangler_hints = bpy.props.PointerProperty(type=LightWranglerHintsProperties)

    # Add handlers
    handlers = [
        (bpy.app.handlers.depsgraph_update_post, update_light_spread),
        (bpy.app.handlers.depsgraph_update_pre, light_type_changed),
        (bpy.app.handlers.depsgraph_update_post, sync_node_values_handler),
        (bpy.app.handlers.load_post, after_load_handler),
        (bpy.app.handlers.depsgraph_update_post, update_light_visibility),
        (bpy.app.handlers.depsgraph_update_post, light_selection_handler)
        
    ]
    for handler_list, func in handlers:
        if func not in handler_list:
            handler_list.append(func)

    # Custom properties
    add_custom_properties_to_lights()

    

    # Load previews and register enums
    for preview_type in ['gobo', 'hdri', 'ies']:
        globals()[f'load_{preview_type}_previews']()
        setattr(bpy.types.Light, f'{preview_type}_enum', bpy.props.EnumProperty(
            items=globals()[f'get_{preview_type}_items'],
            name=f"{preview_type.upper()} Texture" if preview_type != 'ies' else "IES Profile",
            description="",
            update=globals()[f'update_{preview_type}_texture']
        ))

    # Register keymaps
    register_keymaps()

def unregister():
    # Unregister classes
    classes = [
        ClearHDRIDirectoryPath, ClearGoboDirectoryPath, LightWranglerPreferences,
        LightVisibilityState, WorldNodeMuteState, LightWranglerProperties,
        LIGHT_OT_apply_custom_data_block, OpenAddonPreferencesOperator, MainPanel,
        LightIntersectionGizmoGroup, LIGHT_GGT_lw_viewport_gizmos,
        LIGHT_OT_lw_toggle_visibility, LightWranglerHintsProperties,
        ConvertToPlaneOperator, RefreshHDRIPath, RefreshGoboPath,
        CopyAndAdjustLightOperator, LightOperationsSubMenu, OpenMailOperator,
        ProxyLightAtPointOperator, AddEmptyAtIntersectionOperator, LightAtPointOperator,
        AdjustLightPositionOperator, Two_AdjustLightPositionOperator,
        Three_AdjustLightPositionOperator, TabAdjustLightPositionOperator,
        LightWranglerSettings, OBJECT_OT_LightTypeChanged, LIGHT_OT_ScrimPreviewCreator,
        RenderScrimOperator, Render360HDROperator, HDRI_PT_RenderPanel,
        RefreshIESPath, ClearIESDirectoryPath
    ]
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    # Enable collection hotkeys
    enable_collection_hotkeys(["ONE", "TWO", "THREE"], "object.hide_collection")

    # Remove menu items
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func_context_menu)
    bpy.types.VIEW3D_MT_light_add.remove(menu_func_light_add)

    # Remove handlers
    handlers = [
        (bpy.app.handlers.depsgraph_update_post, update_light_spread),
        (bpy.app.handlers.depsgraph_update_pre, light_type_changed),
        (bpy.app.handlers.depsgraph_update_post, sync_node_values_handler),
        (bpy.app.handlers.load_post, after_load_handler),
        (bpy.app.handlers.depsgraph_update_post, update_light_visibility),
        (bpy.app.handlers.depsgraph_update_post, light_selection_handler)
    ]
    for handler_list, func in handlers:
        if func in handler_list:
            handler_list.remove(func)

    # Remove properties
    del bpy.types.WindowManager.is_light_adjust_active
    del bpy.types.Scene.light_wrangler
    del bpy.types.Scene.light_wrangler_settings
    del bpy.types.Scene.modal_running
    del bpy.types.Scene.light_wrangler_hints

    # Remove previews and enums
    for preview_type in ['gobo', 'hdri', 'ies']:
        try:
            bpy.utils.previews.remove(globals()[f'{preview_type}_previews'])
        except Exception as e:
            print(f"Failed to remove {preview_type} previews:", e)
        if hasattr(bpy.types.Light, f'{preview_type}_enum'):
            delattr(bpy.types.Light, f'{preview_type}_enum')

    # Unregister keymaps
    unregister_keymaps()


def register_keymaps():
    """
    Register keyboard shortcuts for the addon.
    This function sets up the keymaps for various light adjustment operations.
    """
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        # Register F9 key for adding a new light
        km = kc.keymaps.new(name="3D View Generic", space_type="VIEW_3D")
        kmi = km.keymap_items.new(ProxyLightAtPointOperator.bl_idname, "F9", "PRESS")
        addon_keymaps.append(km)

        # Register number keys for different light adjustment modes
        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
        for key, operator in [
            (["ONE", "SEVEN"], AdjustLightPositionOperator.bl_idname),
            (["TWO", "EIGHT"], Two_AdjustLightPositionOperator.bl_idname),
            (["THREE", "NINE"], Three_AdjustLightPositionOperator.bl_idname)
        ]:
            for k in key:
                kmi = km.keymap_items.new(operator, k, "PRESS")
                kmi.properties.key_identifier_dum = k

        # Register TAB key for cycling through light adjustment modes
        km.keymap_items.new(TabAdjustLightPositionOperator.bl_idname, "TAB", "PRESS")
        addon_keymaps.append(km)

def unregister_keymaps():
    """
    Unregister all keyboard shortcuts set by the addon.
    This function is called when the addon is disabled or uninstalled.
    """
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        for km in addon_keymaps:
            try:
                kc.keymaps.remove(km)
            except Exception as e:
                print(f"Failed to remove keymap {km.name}: {e}")
    addon_keymaps.clear()

if __name__ == "__main__":
    register()
