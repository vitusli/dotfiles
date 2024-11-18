
def get_assetbrowser_area(context):
    if context.workspace:
        for screen in context.workspace.screens:
            for area in screen.areas:
                if area.type == 'FILE_BROWSER' and area.ui_type == 'ASSETS':
                    return area

def get_assetbrowser_space(area):
    for space in area.spaces:
        if space.type == 'FILE_BROWSER':
            return space

def get_3dview_area(context):
    for screen in context.workspace.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                return area

def get_3dview_space(context):
    if context.space_data.type == 'VIEW_3D':
        return context.space_data

    else:
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        return space

def get_window_region_from_area(area):
    for region in area.regions:
        if region.type == 'WINDOW':
            return region, region.data
