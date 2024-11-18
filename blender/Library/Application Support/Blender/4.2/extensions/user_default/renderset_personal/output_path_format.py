#!/usr/bin/python3
# copyright (c) 2018- polygoniq xyz s.r.o.

# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
import datetime
import os
import enum
import re
import socket
import pathlib
import typing
import logging
from . import polib
from . import compositor_helpers

if typing.TYPE_CHECKING:
    # TYPE_CHECKING is always False at runtime, so this block will never be executed
    # This import is used only for type hinting
    from . import renderset_context


logger = logging.getLogger(__name__)


MODULE_CLASSES: typing.List[typing.Type] = []


FOLDER_SELECT_RUNNING = False


# See https://docs.blender.org/manual/en/latest/files/media/video_formats.html
class MultiFrameFormatExtensions(enum.Enum):
    # MPEG1
    MPG = ".mpg"
    MPEG = ".mpeg"

    # MPEG2
    DVD = ".dvd"
    VOB = ".vob"
    # ".mpg", ".mpeg"

    # MPEG4
    MP4 = ".mp4"
    # ".mpg", ".mpeg"

    # AVI
    AVI = ".avi"

    # QuickTime
    MOV = ".mov"

    # DV
    DV = ".dv"

    # Ogg Vorbis
    OGG = ".ogg"
    OGV = ".ogv"

    # Matroska
    MKV = ".mkv"

    # Flash
    FLV = ".flv"

    # WebM
    WEBM = ".webm"

    @classmethod
    def is_multi_frame_format_extension(cls, extension: str) -> bool:
        try:
            cls(extension)
            return True
        except ValueError:
            return False


class OutputFormatProperty(enum.Enum):
    """Enum defining names of properties in OutputFormatProperties."""

    OUTPUT_FOLDER = "folder_path"
    STILL_IMAGE_FILENAME = "still_image_filename"
    ANIMATION_FRAME_FILENAME = "animation_frame_filename"
    ANIMATION_MOVIE_FILENAME = "animation_movie_filename"


# For some users the token system is tricky to get started with, we give them a few
# pre-made examples to start with. This should reflect best practices with renderset.
FOLDER_PATH_PRESETS = {
    "absolute: (USER)/renderset/blend_name/render_context_name/date": os.path.expanduser(
        os.path.join("~", "renderset", "{blend_filename}", "{context_name}", "{date_time}")
    ),
    "relative: blend_folder/renders/render_context_name/date": os.path.join(
        "{blend_parent_folder}",
        "renders",
        "{context_name}",
        "{date_time}",
    ),
    "custom date: (USER)/renderset/blend_name/render_context_name/date": os.path.expanduser(
        os.path.join(
            "~",
            "renderset",
            "{blend_filename}",
            "{context_name}",
            "{year}-{month}-{day}T{hour}-{minute}-{second}",
        )
    ),
}


DEFAULT_FOLDER_PATH = FOLDER_PATH_PRESETS["relative: blend_folder/renders/render_context_name/date"]


DEFAULT_FILENAME_FORMATS = {
    OutputFormatProperty.STILL_IMAGE_FILENAME.value: "Image",
    OutputFormatProperty.ANIMATION_FRAME_FILENAME.value: "Frame{frame_current}",
    OutputFormatProperty.ANIMATION_MOVIE_FILENAME.value: "Movie{frame_start}-{frame_end}",
}


AVAILABLE_VARIABLES = {
    "context_name": "Name of rendered context",
    "context_render_type": "Type of render (still or animation)",
    "blend_parent_folder": "Parent folder of current Blend file location",
    "blend_filename": "Name of current Blend file",
    "blend_full_path": "Full path to Blend file",
    "hostname": "Hostname of the machine that is rendering",
    "date_time": "Date and time in format: YYYY-MM-DDTHH-MM-SS",
    "frame_current": "Current frame of the animation",
    "frame_start": "Start frame of the animation",
    "frame_end": "End frame of the animation",
    "frame_step": "Step between frames of the animation",
    "camera": "Camera assigned to the context",
    "world": "World assigned to the context",
    "year": "",
    "month": "",
    "day": "",
    "hour": "",
    "minute": "",
    "second": "",
}


def get_available_variables_enum() -> typing.List[bpy.types.EnumPropertyItem]:
    enum_items = []
    for var, desc in AVAILABLE_VARIABLES.items():
        enum_items.append((var, var, desc))

    return enum_items


FORMAT_PROPERTY_DESCRIPTION = """Describes how to auto-generate renderset context output folder path
when rendering it. All render outputs will be placed in this folder. You can specify path to a folder
with additional variables from following list.

Available variables:
""" + "\n".join(
    [f"- {var}: {desc}" for var, desc in AVAILABLE_VARIABLES.items()]
)


class OutputFormatProperties(bpy.types.PropertyGroup):
    def update_format(self, context: bpy.types.Context) -> None:
        self.folder_path = FOLDER_PATH_PRESETS[self.folder_path_preset]

    folder_path_preset: bpy.props.EnumProperty(
        items=[
            (name, name.title(), fmt_string) for name, fmt_string in FOLDER_PATH_PRESETS.items()
        ],
        update=update_format,
    )

    def ensure_not_empty_output_folder(self, context: bpy.types.Context) -> None:
        if self.folder_path == "":
            self.update_format(context)
        check_output_path_popup_on_error(context, self.folder_path)

    folder_path: bpy.props.StringProperty(
        name="Autogenerated Output Folder Format",
        default=DEFAULT_FOLDER_PATH,
        update=ensure_not_empty_output_folder,
        description=FORMAT_PROPERTY_DESCRIPTION,
        # We need custom folder picker in the lower versions
        # because the default crashes operator dialogs
        subtype='DIR_PATH' if bpy.app.version >= (4, 1, 0) else 'NONE',
    )

    def _update_output_filename(self, filename_type: OutputFormatProperty) -> None:
        if filename_type.value not in DEFAULT_FILENAME_FORMATS:
            raise ValueError(f"Unknown filename type: '{filename_type.value}'")
        if self[filename_type.value] == "":
            self[filename_type.value] = DEFAULT_FILENAME_FORMATS[filename_type.value]

    still_image_filename: bpy.props.StringProperty(
        name="Still Image Filename",
        default=DEFAULT_FILENAME_FORMATS[OutputFormatProperty.STILL_IMAGE_FILENAME.value],
        update=lambda self, _: self._update_output_filename(
            OutputFormatProperty.STILL_IMAGE_FILENAME
        ),
        description="Filename format for still images output",
    )

    animation_frame_filename: bpy.props.StringProperty(
        name="Animation Frame Filename",
        default=DEFAULT_FILENAME_FORMATS[OutputFormatProperty.ANIMATION_FRAME_FILENAME.value],
        update=lambda self, _: self._update_output_filename(
            OutputFormatProperty.ANIMATION_FRAME_FILENAME
        ),
        description="Filename format for animation frame output",
    )

    animation_movie_filename: bpy.props.StringProperty(
        name="Animation Movie Filename",
        default=DEFAULT_FILENAME_FORMATS[OutputFormatProperty.ANIMATION_MOVIE_FILENAME.value],
        update=lambda self, _: self._update_output_filename(
            OutputFormatProperty.ANIMATION_MOVIE_FILENAME
        ),
        description="Filename format for animation movie output",
    )


MODULE_CLASSES.append(OutputFormatProperties)


class SelectOutputFolderMixin(polib.ui_bpy.SelectFolderPathMixin):
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        global FOLDER_SELECT_RUNNING
        FOLDER_SELECT_RUNNING = True
        return super().invoke(context, event)

    def signal_folder_select_not_running(self):
        global FOLDER_SELECT_RUNNING
        FOLDER_SELECT_RUNNING = False

    def apply_selected_folder_path(
        self,
        output_format: OutputFormatProperties,
        folder_path: typing.Optional[str],
        dialog_func: typing.Optional[typing.Callable] = None,
    ):
        self.signal_folder_select_not_running()
        if folder_path is not None:
            output_format.folder_path = folder_path
        if dialog_func is not None:
            return dialog_func('INVOKE_DEFAULT')
        return {'FINISHED'}


class MockRendersetContext:
    """This is a mock class that can be used in place of renderset_context argument for
    the create_replacement_mapping and generate_folder_path functions. This is useful in
    places where creating a proper RendersetContext would be too much trouble.
    e.g. to give a live example of paths given user's settings.
    """

    class MockDatablock:
        """Mock class representing datablock with name property"""

        def __init__(self, name: str):
            self.name = name

    custom_name = "ExampleContextName"
    render_type = "still"

    def get_camera(self) -> MockDatablock:
        return self.MockDatablock("ExampleContextCamera")

    def get_world(self) -> MockDatablock:
        return self.MockDatablock("ExampleContextWorld")


def create_replacement_mapping(
    renderset_context: typing.Union["renderset_context.RendersetContext", MockRendersetContext],
    time: typing.Optional[datetime.datetime] = None,
    frame_current: typing.Optional[int] = None,
    frame_start: typing.Optional[int] = None,
    frame_end: typing.Optional[int] = None,
    frame_step: typing.Optional[int] = None,
) -> typing.Mapping[str, typing.Union[str, int]]:
    ret: typing.Dict[str, typing.Union[str, int]] = {}

    ret["blend_parent_folder"] = ""
    ret["blend_filename"] = ""
    ret["blend_full_path"] = ""

    if bpy.data.filepath:
        ret["blend_parent_folder"] = os.path.dirname(bpy.data.filepath)
        ret["blend_filename"] = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        ret["blend_full_path"] = os.path.realpath(os.path.abspath(bpy.data.filepath))

    if time is None:
        time = datetime.datetime.now()

    ret["hostname"] = "unknown"
    try:
        ret["hostname"] = socket.gethostname()
    except:
        pass

    # Replace slashes in the context custom name, so the slashes are not treated as folders
    ret["context_name"] = renderset_context.custom_name.replace("\\", "/").replace("/", "_")
    ret["context_render_type"] = renderset_context.render_type
    camera = renderset_context.get_camera()
    world = renderset_context.get_world()
    ret["camera"] = camera.name if camera is not None else ""
    ret["frame_current"] = (
        f"{bpy.context.scene.frame_current:04d}"
        if frame_current is None
        else f"{frame_current:04d}"
    )
    ret["frame_start"] = (
        f"{bpy.context.scene.frame_start:04d}" if frame_start is None else f"{frame_start:04d}"
    )
    ret["frame_end"] = (
        f"{bpy.context.scene.frame_end:04d}" if frame_end is None else f"{frame_end:04d}"
    )
    ret["frame_step"] = (
        f"{bpy.context.scene.frame_step:04d}" if frame_step is None else f"{frame_step:04d}"
    )
    ret["world"] = world.name if world is not None else ""
    ret["year"] = f"{time.year:04d}"
    ret["month"] = f"{time.month:02d}"
    ret["day"] = f"{time.day:02d}"
    ret["hour"] = f"{time.hour:02d}"
    ret["minute"] = f"{time.minute:02d}"
    ret["second"] = f"{time.second:02d}"
    ret["date_time"] = (
        f"{ret['year']}-{ret['month']}-{ret['day']}T{ret['hour']}-{ret['minute']}-{ret['second']}"
    )

    return ret


def filter_invalid_characters_from_path(input_path: str) -> str:
    """Windows, Linux and OSX each have different rules for this. Windows is the most strict
    so we will filter as if the user is always on Windows. This is a design decision but
    assuming people work in heterogenous environments they want to follow rules such that
    everyone can work with all files.

    Caveats:
    Windows has crazy rules, for example folders with the name 'con' are forbidden. We don't
    handle that here because it is extremely difficult to filter that out and there are a ton
    of these exceptions.
    """

    # the overcomplicated typing hint is just so that mypy gets this
    forbidden_chars: typing.Dict[str, typing.Union[int, str, None]] = {
        "<": "_",
        ">": "_",
        ":": "_",
        "\"": "_",
        "|": "_",
        "?": "_",
        "*": "_",
    }
    # we have to split into drive and path and only replace in the path
    # this prevents replacing the ':' with '_' in e.g. "C:/something"
    drive, path = os.path.splitdrive(input_path)
    return drive + path.translate(str.maketrans(forbidden_chars))


def generate_folder_path(
    format_string: str,
    renderset_context: typing.Union["renderset_context.RendersetContext", MockRendersetContext],
    time: typing.Optional[datetime.datetime] = None,
    frame_current: typing.Optional[int] = None,
    frame_start: typing.Optional[int] = None,
    frame_end: typing.Optional[int] = None,
    frame_step: typing.Optional[int] = None,
) -> str:
    # 1) replace //
    # We do not want empty tokens generating two slashes and then replacing that with blend
    # parent folder, so we replace // and ~ before we replace tokens
    ret = bpy.path.abspath(format_string)
    # 2) replace ~ with HOMEDIR if present
    ret = os.path.expanduser(ret)
    # 3) replace tokens with their values
    replacement_dict = create_replacement_mapping(
        renderset_context,
        time=time,
        frame_current=frame_current,
        frame_start=frame_start,
        frame_end=frame_end,
        frame_step=frame_step,
    )
    ret = ret.format(**replacement_dict)
    # 4) filter invalid characters
    ret = filter_invalid_characters_from_path(ret)
    # 5) resolve the ../ and ./
    return os.path.abspath(ret)


def generate_filename(
    format_string: str,
    renderset_context: typing.Union["renderset_context.RendersetContext", MockRendersetContext],
    time: typing.Optional[datetime.datetime] = None,
    render_pass: str = compositor_helpers.RenderPassType.COMPOSITE.value,
    frame_current: typing.Optional[int] = None,
    frame_start: typing.Optional[int] = None,
    frame_end: typing.Optional[int] = None,
    frame_step: typing.Optional[int] = None,
) -> str:
    # 1) add a render pass prefix if needed
    if render_pass != compositor_helpers.RenderPassType.COMPOSITE.value:
        format_string = f"{render_pass}_{format_string}"
    # 2) replace tokens with their values
    replacement_dict = create_replacement_mapping(
        renderset_context,
        time=time,
        frame_current=frame_current,
        frame_start=frame_start,
        frame_end=frame_end,
        frame_step=frame_step,
    )
    ret = format_string.format(**replacement_dict)
    # 3) filter invalid characters
    ret = filter_invalid_characters_from_path(ret)
    # 4) Replace (back)slashes with underscores
    return ret.replace("\\", "_").replace("/", "_")


def check_variables_in_format_string(format_string: str) -> typing.Tuple[bool, str]:
    """Checks whether all variables in format_string are existing and if the string has correct formatting.

    Returns (False, msg) for the first unrecognized variable, (True, "") otherwise.
    """
    input_variables = re.findall(r'\{(.*?)(\:.*?)?\}', format_string)
    for input_var, _ in input_variables:
        if input_var == "":
            return False, "Empty '{}' encountered in the format string!"
        if input_var not in AVAILABLE_VARIABLES:
            return (
                False,
                f"Unknown variable {input_var}, check output format description for more info!",
            )
    return True, ""


def _is_output_valid(
    output: str, generator_func: typing.Callable[[str, typing.Any], str]
) -> typing.Tuple[bool, str]:
    valid, msg = check_variables_in_format_string(output)
    if not valid:
        return False, msg

    # Variable name is correct, but we can't be sure if the additional formatting options are correct
    try:
        generator_func(output, MockRendersetContext())
    except ValueError as e:
        return False, str(e)

    return True, ""


def is_output_path_valid(output_path: str) -> typing.Tuple[bool, str]:
    """Checks whether all variables in output_path are existing and if the path has correct formatting
    and it can be successfully evaluated.

    Returns (False, msg) of the first error found, (True, "") otherwise
    """
    return _is_output_valid(output_path, generate_folder_path)


def is_output_filename_valid(output_filename: str) -> typing.Tuple[bool, str]:
    """Checks whether all variables in output_filename are existing and if the path has correct formatting
    and it can be successfully evaluated.

    Returns (False, msg) of the first error found, (True, "") otherwise
    """
    return _is_output_valid(output_filename, generate_filename)


def check_output_path_popup_on_error(context: bpy.types.Context, path: str) -> None:
    """Checks whether 'path' argument is a valid output folder path. If not then this invokes
    popup window via window_manager from 'context' with error message about what is wrong.
    """
    popup_msg = ""

    def popup(_self, _context):
        _self.layout.label(text=popup_msg)

    valid, popup_msg = is_output_path_valid(path)
    if not valid:
        context.window_manager.popup_menu(popup, title="Path Format Error", icon='ERROR')


def select_output_filename(
    is_animation: bool,
    is_movie_format: bool,
    is_composite: bool,
    still_image_filename: str,
    animation_frame_filename: str,
    animation_movie_filename: str,
) -> str:
    if is_animation:
        # If we render something else than composite pass in an animation movie
        # the output is an image
        if is_movie_format and is_composite:
            return animation_movie_filename
        else:
            return animation_frame_filename
    else:
        return still_image_filename


@polib.log_helpers_bpy.logged_operator
class OutputFormatPeekVariables(bpy.types.Operator):
    bl_idname = "renderset.output_format_peek_variables"
    bl_label = "Peek Variables"
    bl_description = "Shows all renderset output path variables and their live values"
    bl_options = {'REGISTER'}

    def execute(self, context: bpy.types.Context):
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context: bpy.types.Context):
        replacement_dict = create_replacement_mapping(MockRendersetContext())

        row = self.layout.row()
        var_col = row.column()
        var_col.alignment = 'LEFT'
        var_col.label(text="Variable", icon='COPY_ID')

        value_col = row.column()
        value_col.alignment = 'RIGHT'

        # To add icon to the right side we need to create separate row
        # as a container for both icon and label and set its alignment
        # to 'RIGHT' aswell.
        value_header = value_col.row()
        value_header.alignment = 'RIGHT'
        value_header.label(text="Value")
        value_header.label(text="", icon='TRACKING_REFINE_BACKWARDS')
        for var, value in replacement_dict.items():
            var_col.label(text=f"{{{var}}}")
            value_col.label(text=f"{value}")


MODULE_CLASSES.append(OutputFormatPeekVariables)


class OutputFormatAddVariableMixin:
    bl_label = "Add Variable"
    bl_description = "Adds one of predefined variables to the target output format"
    bl_options = {'REGISTER', 'UNDO'}

    target: bpy.props.EnumProperty(
        name="Target",
        items=(
            (
                OutputFormatProperty.OUTPUT_FOLDER.value,
                "Autogenerated Output Folder Path",
                "Add into output folder path in preferences",
            ),
            (
                OutputFormatProperty.STILL_IMAGE_FILENAME.value,
                "Still Image Filename",
                "Add into still image filename format in preferences",
            ),
            (
                OutputFormatProperty.ANIMATION_FRAME_FILENAME.value,
                "Animation Frame Filename",
                "Add into animation frame filename format in preferences",
            ),
            (
                OutputFormatProperty.ANIMATION_MOVIE_FILENAME.value,
                "Animation Movie Filename",
                "Add into animation movie filename format in preferences",
            ),
        ),
    )

    variable: bpy.props.EnumProperty(
        name="Available variables",
        description="Variables available in output formats",
        items=get_available_variables_enum(),
    )

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context: bpy.types.Context):
        replacement_dict = create_replacement_mapping(MockRendersetContext())
        col = self.layout.column()
        col.label(text="Variable", icon='COPY_ID')
        col.prop(self, "variable", text="")
        col.separator()
        col.label(text="Live Value", icon='TRACKING_REFINE_BACKWARDS')
        col.label(text=f"{replacement_dict[self.variable]}")

    def add_variable(self, output_props: OutputFormatProperties) -> None:
        token_to_append = "{" + self.variable + "}"

        if self.target == OutputFormatProperty.OUTPUT_FOLDER.value:
            if not output_props.folder_path.endswith(("/", "\\")):
                token_to_append = os.path.sep + token_to_append
            output_props.folder_path += token_to_append

        elif self.target == OutputFormatProperty.STILL_IMAGE_FILENAME.value:
            if not output_props.still_image_filename.endswith("_"):
                token_to_append = "_" + token_to_append
            output_props.still_image_filename += token_to_append

        elif self.target == OutputFormatProperty.ANIMATION_FRAME_FILENAME.value:
            if not output_props.animation_frame_filename.endswith("_"):
                token_to_append = "_" + token_to_append
            output_props.animation_frame_filename += token_to_append

        elif self.target == OutputFormatProperty.ANIMATION_MOVIE_FILENAME.value:
            if not output_props.animation_movie_filename.endswith("_"):
                token_to_append = "_" + token_to_append
            output_props.animation_movie_filename += token_to_append
        else:
            raise RuntimeError(f"Unknown target '{self.target}'!")


def draw_add_variable_ui(
    layout: bpy.types.UILayout,
    add_variable_operator: OutputFormatAddVariableMixin,
    target: OutputFormatProperty,
    text: str = "Add Variable",
) -> None:
    layout.operator(add_variable_operator.bl_idname, icon='COPY_ID', text=text).target = (
        target.value
    )
    layout.operator(OutputFormatPeekVariables.bl_idname, icon='ZOOM_ALL', text="")


def split_path_to_existing_and_nonexisting(path: str) -> typing.Tuple[str, str]:
    parts = pathlib.Path(path).parts
    existing_path = ""

    for i, part in enumerate(parts):
        existing_path = os.path.join(existing_path, part)
        if not os.path.exists(existing_path):
            nonexisting_path = os.path.join(*parts[i:])
            return os.path.dirname(existing_path), nonexisting_path
    return path, ""


def draw_existing_and_nonexisting_path_ui(layout: bpy.types.UILayout, path: str) -> None:
    existing_path, nonexisting_path = split_path_to_existing_and_nonexisting(path)
    row = layout.row(align=True)
    col = row.column(align=True)
    row_label = col.row()
    row_label.enabled = False
    row_label.alignment = 'LEFT'
    row_label.label(text=f"Already Exists:")
    row_path = col.row()
    row_path.alignment = 'LEFT'
    row_path.label(text=f"{existing_path}{os.path.sep}")
    if len(nonexisting_path) > 0:
        col = row.column(align=True)
        row_label = col.row()
        row_label.enabled = False
        row_label.alignment = 'LEFT'
        row_label.label(text=f"To Be Created:", icon='NEWFOLDER')
        row_path = col.row()
        row_path.alignment = 'LEFT'
        row_path.label(text=f"{nonexisting_path}")


def draw_output_folder_ui(
    output_props: OutputFormatProperties,
    layout: bpy.types.UILayout,
    select_folder_operator: typing.Optional[
        polib.ui_bpy.OperatorButtonLoader[SelectOutputFolderMixin]
    ],
    add_variable_operator: OutputFormatAddVariableMixin,
    renderset_context: typing.Union["renderset_context.RendersetContext", MockRendersetContext],
    label: str = "Output Folder Path:",
) -> None:
    main_col = layout.column(align=True)
    row = main_col.row()
    row.label(text=f"{label}")
    row = row.row(align=True)
    row.alignment = 'RIGHT'
    row.prop_menu_enum(output_props, "folder_path_preset", text="Choose Preset")
    draw_add_variable_ui(row, add_variable_operator, OutputFormatProperty.OUTPUT_FOLDER)

    folder_row = main_col.row(align=True)
    folder_row.prop(output_props, OutputFormatProperty.OUTPUT_FOLDER.value, text="")
    if select_folder_operator is not None:
        select_folder_operator.draw_button(folder_row, icon='FILE_FOLDER', text="").filepath = (
            os.path.join(output_props.folder_path, os.path.sep)
        )
    valid, err_msg = is_output_path_valid(output_props.folder_path)

    box = main_col.box()
    if bpy.data.filepath == "":  # blend file is not saved
        row = box.row()
        row.enabled = False
        row.label(text="Save the blend file to see an example preview of the output path")
    elif valid:
        path_preview = generate_folder_path(output_props.folder_path, renderset_context)
        draw_existing_and_nonexisting_path_ui(box, path_preview)
    else:
        row = box.row()
        row.alert = True
        row.label(text=f"Specified path is invalid! {err_msg}", icon='ERROR')


def draw_output_filename_ui(
    output_props: OutputFormatProperties,
    layout: bpy.types.UILayout,
    output_type: OutputFormatProperty,
    add_variable_operator: OutputFormatAddVariableMixin,
    renderset_context: typing.Union["renderset_context.RendersetContext", MockRendersetContext],
    label_text: str,
) -> None:
    assert output_type.value in DEFAULT_FILENAME_FORMATS
    if output_type == OutputFormatProperty.STILL_IMAGE_FILENAME:
        output_filename = output_props.still_image_filename
    elif output_type == OutputFormatProperty.ANIMATION_FRAME_FILENAME:
        output_filename = output_props.animation_frame_filename
    elif output_type == OutputFormatProperty.ANIMATION_MOVIE_FILENAME:
        output_filename = output_props.animation_movie_filename
    else:
        raise RuntimeError(f"Unknown output_type '{output_type}'!")

    col = layout.column()
    split = col.split(factor=0.25)
    left = split.column(align=True)
    left.label(text=f"{label_text}:")
    right = split.column(align=True)
    row = right.row(align=True)
    row.prop(output_props, output_type.value, text="")
    draw_add_variable_ui(row, add_variable_operator, output_type, text="")

    valid, err_msg = is_output_filename_valid(output_filename)
    if valid:
        evaluated_prefix = generate_filename(output_filename, renderset_context)
        example_row = right.row()
        row_label = example_row.row()
        row_label.alignment = 'LEFT'
        row_label.enabled = False
        row_label.label(text="Preview:")
        row_filename = example_row.row()
        row_filename.alignment = 'LEFT'
        if output_type == OutputFormatProperty.ANIMATION_MOVIE_FILENAME:
            extension = "avi"
        else:
            extension = "png"
        row_filename.label(text=f"{evaluated_prefix}.{extension}")
        if output_type == OutputFormatProperty.ANIMATION_FRAME_FILENAME:
            if "{frame_current}" not in output_filename:
                row = col.row()
                row.alert = True
                row.label(
                    text="Filename does not contain {frame_current} variable, "
                    "each frame will overwrite the previous one!",
                    icon='ERROR',
                )
    else:
        row = col.row()
        row.alert = True
        row.label(text=f"Specified filename is invalid! {err_msg}", icon='ERROR')


def register():
    for cls in MODULE_CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in MODULE_CLASSES:
        bpy.utils.unregister_class(cls)
