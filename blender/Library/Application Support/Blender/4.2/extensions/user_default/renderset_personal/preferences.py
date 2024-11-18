# copyright (c) 2018- polygoniq xyz s.r.o.

import typing
import bpy
import enum
import logging
from . import polib
from . import post_render_actions
from . import output_path_format
from . import scene_props

logger = logging.getLogger(f"polygoniq.{__name__}")


telemetry = polib.get_telemetry("renderset")


MODULE_CLASSES: typing.List[typing.Type] = []


class RenderOperator(enum.Enum):
    STANDARD = "STANDARD"
    TURBO_TOOLS = "TURBO_TOOLS"


class ListerProperties(bpy.types.PropertyGroup):

    def switch_to_first_page(self, context: bpy.types.Context) -> None:
        self.page_index = 0

    show: bpy.props.EnumProperty(
        name="Show Stored",
        description="Selects what stored properties are shown",
        items=(
            (
                'PRIMITIVE_PROPS',
                "Primitive Properties",
                "Primitive Properties - floats, integers and strings",
                'RADIOBUT_ON',
                0,
            ),
            (
                'CONTEXT_PROPS',
                "Context Properties",
                "renderset properties of the context",
                'FILE_CACHE',
                1,
            ),
            (
                'VIEW_LAYER_VISIBILITY',
                "View Layer Visibility",
                "Stored visibility restrictions of view layers",
                'RENDERLAYERS',
                2,
            ),
            (
                'COLLECTION_VISIBILITY',
                "Collection Visibility",
                "Stored visibility restrictions of collections",
                'OUTLINER_COLLECTION',
                3,
            ),
            (
                'OBJECT_VISIBILITY',
                "Object Visibility",
                "Stored visibility restrictions of objects",
                'OBJECT_DATA',
                4,
            ),
            (
                'DATA_PROPERTIES',
                "Data Properties",
                "Stored custom properties of Blender data",
                'FILE_BLEND',
                5,
            ),
            ('OUTPUT_PATH', "Output Path", "Preview of the output path", 'OUTPUT', 6),
            (
                'ALL',
                "All",
                "All stored properties in renderset",
                'LIGHTPROBE_GRID' if bpy.app.version < (4, 1, 0) else 'LIGHTPROBE_VOLUME',
                7,
            ),
        ),
        update=lambda self, context: self.switch_to_first_page(context),
        default=7,
    )

    search: bpy.props.StringProperty(
        name="Search",
        description="Search for a property",
        update=lambda self, context: self.switch_to_first_page(context),
    )

    width: bpy.props.IntProperty(
        name="Lister Width (px)",
        default=1500,
        min=1,
        description="Width of render context lister window",
    )

    page_index: bpy.props.IntProperty(name="Current page index", min=0, default=0)

    props_per_page: bpy.props.IntProperty(
        name="Properties per Page",
        min=1,
        default=12,
        description="How many properties to show per page",
    )


MODULE_CLASSES.append(ListerProperties)


@polib.log_helpers_bpy.logged_preferences
class Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    show_context_stored_values: bpy.props.BoolProperty(
        name="Show Context Stored Values",
        default=False,
        description="If true we will show values of what's contained within the currently "
        "selected RendersetContext. Keep in mind that these values are not guaranteed to "
        "be up to date! RendersetContexts are stored when you switch away from them. No "
        "data is ever lost, it just may not be up to date in the stored details box",
    )

    render_operators: bpy.props.EnumProperty(
        name="Render Operators",
        description="Which render operators should renderset use",
        items=(
            (
                RenderOperator.STANDARD.value,
                "Blender Standard",
                "Standard operators that come with Blender",
            ),
            (
                RenderOperator.TURBO_TOOLS.value,
                "Turbo Tools",
                "Turbo Tools operators for stills and animations",
            ),
        ),
        default=RenderOperator.STANDARD.value,
    )

    automatic_render_slots: bpy.props.BoolProperty(
        name="Automatic Render Slots",
        default=True,
        description="If enabled, each renderset context will be rendered into a render slot "
        "based on its index. This might take additional memory because it's all stored in Blender",
    )

    automatic_render_layer_split: bpy.props.BoolProperty(
        name="Automatic Render Layer Split",
        default=True,
        description="If enabled, renderset will automatically split renders into separate files",
    )

    debug_enabled: bpy.props.BoolProperty(
        name="Debug Enabled",
        default=False,
        description="If enabled, renderset shows new option to view internal stored debug information",
    )

    lister: bpy.props.PointerProperty(type=ListerProperties)

    lock_interface: bpy.props.BoolProperty(
        name="Auto Lock Interface",
        default=True,
        description="Renderset automatically locks interface for rendering. This surpresses possible crashes and makes the rendering faster. "
        "On the other hand controlling of the interface during rendering is disabled."
        "It is heavily recommended to leave this enabled!",
    )

    switch_to_solid_view_before_rendering: bpy.props.BoolProperty(
        name="Switch to Solid View before Rendering", default=True
    )

    show_render_output_settings: bpy.props.BoolProperty(
        description="Show/Hide Output Settings", default=True
    )

    show_output_filename_settings: bpy.props.BoolProperty(
        description="Show/Hide Output Filename Settings", default=False
    )

    show_post_render_actions: bpy.props.BoolProperty(
        description="Show/Hide Post Render Actions", default=False
    )

    show_options: bpy.props.BoolProperty(description="Show/Hide Options", default=True)

    def draw_all_output_filenames_ui(self, layout: bpy.types.UILayout):
        box = layout.box()
        row = box.row()
        row.prop(
            self,
            "show_output_filename_settings",
            icon=(
                'DISCLOSURE_TRI_DOWN'
                if self.show_output_filename_settings
                else 'DISCLOSURE_TRI_RIGHT'
            ),
            text="",
            emboss=False,
        )
        row.label(text="Output Filenames")
        if not self.show_output_filename_settings:
            return

        scene_output_format = scene_props.get_output_format(bpy.context)
        output_path_format.draw_output_filename_ui(
            scene_output_format,
            box,
            output_path_format.OutputFormatProperty.STILL_IMAGE_FILENAME,
            scene_props.SceneAddVariable,
            output_path_format.MockRendersetContext(),
            "Still Image",
        )
        output_path_format.draw_output_filename_ui(
            scene_output_format,
            box,
            output_path_format.OutputFormatProperty.ANIMATION_FRAME_FILENAME,
            scene_props.SceneAddVariable,
            output_path_format.MockRendersetContext(),
            "Animation Frame",
        )
        output_path_format.draw_output_filename_ui(
            scene_output_format,
            box,
            output_path_format.OutputFormatProperty.ANIMATION_MOVIE_FILENAME,
            scene_props.SceneAddVariable,
            output_path_format.MockRendersetContext(),
            "Animation Movie",
        )

    def draw_collection_restriction_toggles(self, layout: bpy.types.UILayout) -> None:
        collection_toggles_settings = scene_props.get_collection_toggles_settings(bpy.context)
        layer_collection_toggles_settings = scene_props.get_layer_collection_toggles_settings(
            bpy.context
        )
        row = layout.row()
        row.label(text="Collection", icon='OUTLINER_COLLECTION')
        row.alignment = 'LEFT'
        row = row.row(align=True)
        row.prop(
            layer_collection_toggles_settings,
            "exclude",
            text="",
            icon=(
                'CHECKBOX_HLT' if layer_collection_toggles_settings.exclude else 'CHECKBOX_DEHLT'
            ),
            emboss=False,
        )
        row.prop(
            collection_toggles_settings,
            "hide_select",
            text="",
            icon=(
                'RESTRICT_SELECT_OFF'
                if collection_toggles_settings.hide_select
                else 'RESTRICT_SELECT_ON'
            ),
            emboss=False,
        )
        row.prop(
            layer_collection_toggles_settings,
            "hide_viewport",
            text="",
            icon='HIDE_OFF' if layer_collection_toggles_settings.hide_viewport else 'HIDE_ON',
            emboss=False,
        )
        row.prop(
            collection_toggles_settings,
            "hide_viewport",
            text="",
            icon=(
                'RESTRICT_VIEW_OFF'
                if collection_toggles_settings.hide_viewport
                else 'RESTRICT_VIEW_ON'
            ),
            emboss=False,
        )
        row.prop(
            collection_toggles_settings,
            "hide_render",
            text="",
            icon=(
                'RESTRICT_RENDER_OFF'
                if collection_toggles_settings.hide_render
                else 'RESTRICT_RENDER_ON'
            ),
            emboss=False,
        )
        row.prop(
            layer_collection_toggles_settings,
            "holdout",
            text="",
            icon='HOLDOUT_ON' if layer_collection_toggles_settings.holdout else 'HOLDOUT_OFF',
            emboss=False,
        )
        row.prop(
            layer_collection_toggles_settings,
            "indirect_only",
            text="",
            icon=(
                'INDIRECT_ONLY_ON'
                if layer_collection_toggles_settings.indirect_only
                else 'INDIRECT_ONLY_OFF'
            ),
            emboss=False,
        )

    def draw_object_restriction_toggles(self, layout: bpy.types.UILayout) -> None:
        object_toggles_settings = scene_props.get_object_toggles_settings(bpy.context)
        row = layout.row()
        row.label(text="Object", icon='OBJECT_DATA')
        row.alignment = 'LEFT'
        row = row.row(align=True)
        row.prop(
            object_toggles_settings,
            "hide_select",
            text="",
            icon=(
                'RESTRICT_SELECT_OFF'
                if object_toggles_settings.hide_select
                else 'RESTRICT_SELECT_ON'
            ),
            emboss=False,
        )
        row.prop(
            object_toggles_settings,
            "hide_viewport",
            text="",
            icon=(
                'RESTRICT_VIEW_OFF' if object_toggles_settings.hide_viewport else 'RESTRICT_VIEW_ON'
            ),
            emboss=False,
        )
        row.prop(
            object_toggles_settings,
            "hide_render",
            text="",
            icon=(
                'RESTRICT_RENDER_OFF'
                if object_toggles_settings.hide_render
                else 'RESTRICT_RENDER_ON'
            ),
            emboss=False,
        )

    def draw(self, context: bpy.types.Context):
        box_col = self.layout.column()

        # Render Output Settings section
        box = box_col.box()
        row = box.row()
        row.prop(
            self,
            "show_render_output_settings",
            icon=(
                'DISCLOSURE_TRI_DOWN'
                if self.show_render_output_settings
                else 'DISCLOSURE_TRI_RIGHT'
            ),
            text="",
            emboss=False,
        )
        row.label(text="Render Output Settings")
        if self.show_render_output_settings:
            col = box.column()
            scene_output_format = scene_props.get_output_format(bpy.context)
            output_path_format.draw_output_folder_ui(
                scene_output_format,
                col,
                polib.ui_bpy.OperatorButtonLoader(scene_props.SceneSelectOutputFolder),
                scene_props.SceneAddVariable,
                output_path_format.MockRendersetContext(),
            )
            self.draw_all_output_filenames_ui(col)

            # Post Render Actions subsection
            box = col.box()
            row = box.row()
            row.prop(
                self,
                "show_post_render_actions",
                icon=(
                    'DISCLOSURE_TRI_DOWN'
                    if self.show_post_render_actions
                    else 'DISCLOSURE_TRI_RIGHT'
                ),
                text="",
                emboss=False,
            )
            row.label(text="Post Render Actions")
            if self.show_post_render_actions:
                post_render_actions.draw_post_render_actions_ui(
                    box,
                    scene_props.ScenePostRenderActionList,
                    scene_props.get_post_render_actions(context),
                    scene_props.SceneAddPostRenderAction,
                    scene_props.SceneEditPostRenderAction,
                    scene_props.SceneDeletePostRenderAction,
                    scene_props.SceneMovePostRenderAction,
                    scene_props.SceneClearPostRenderActions,
                )

        # Render Options section
        box = box_col.box()
        row = box.row()
        row.prop(
            self,
            "show_options",
            icon='DISCLOSURE_TRI_DOWN' if self.show_options else 'DISCLOSURE_TRI_RIGHT',
            text="",
            emboss=False,
        )
        row.label(text="Options")
        if self.show_options:
            col = box.column()
            col.label(text="Remembered Visibility Restrictions:")
            self.draw_collection_restriction_toggles(col)
            self.draw_object_restriction_toggles(col)
            col.separator()

            col = box.column(align=True)
            row = col.row()
            row.prop(self, "render_operators")

            col.separator()

            row = col.row()
            row.prop(self, "automatic_render_slots")
            row.prop(self, "automatic_render_layer_split")

            row = col.row()
            row.prop(self, "lock_interface")
            row.prop(self, "switch_to_solid_view_before_rendering")

            col.separator()
            row = col.row()
            row.prop(self, "debug_enabled")
            row.prop(self.lister, "width")

        row = self.layout.row()
        row.operator(PackLogs.bl_idname, icon='EXPERIMENTAL')

        polib.ui_bpy.draw_settings_footer(self.layout)


MODULE_CLASSES.append(Preferences)


@polib.log_helpers_bpy.logged_operator
class PackLogs(bpy.types.Operator):
    bl_idname = "renderset.pack_logs"
    bl_label = "Pack Logs"
    bl_description = "Archives polygoniq logs as zip file and opens its location"
    bl_options = {'REGISTER'}

    def execute(self, context):
        packed_logs_directory_path = polib.log_helpers_bpy.pack_logs(telemetry)
        polib.utils_bpy.xdg_open_file(packed_logs_directory_path)
        return {'FINISHED'}


MODULE_CLASSES.append(PackLogs)


def register():
    for cls in MODULE_CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(MODULE_CLASSES):
        bpy.utils.unregister_class(cls)
