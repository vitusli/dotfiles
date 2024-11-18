import bpy

def get_view_transforms():
    if bpy.app.version < (4, 2, 0):
        return [
            ('ACEScg', 'ACES', ''),
            ('AgX Base sRGB', 'AgX', ''),
            ('AgX Log', 'AgX Log', ''),
            ('False Color', 'False Color', ''),
            ('Filmic sRGB', 'Filmic', ''),
            ('Filmic Log', 'Filmic Log', ''),
            ('sRGB', 'Standard', ''),
        ]
    else: 
        return [
            ('ACEScg', 'ACES', ''),
            ('AgX Base sRGB', 'AgX', ''),
            ('AgX Log', 'AgX Log', ''),
            ('False Color', 'False Color', ''),
            ('Filmic sRGB', 'Filmic', ''),
            ('Filmic Log', 'Filmic Log', ''),
            ('Khronos PBR Neutral sRGB', 'PBR Neutral', ''),
            ('sRGB', 'Standard', ''),
        ]


view_transforms_enable = {
        'AgX': 'AgX Base sRGB',
        'False Color': 'False Color',
        'Filmic': 'Filmic sRGB',
        'Filmic Log': 'Filmic Log',
        'Standard': 'sRGB',
        'Raw': 'AgX Base sRGB',
        'Khronos PBR Neutral': 'Khronos PBR Neutral sRGB'
    }

view_transforms_disable = {
        'ACEScg': 'AgX',
        'ACES2065-1': 'AgX',
        'AgX Base sRGB': 'AgX',
        'AgX Log': 'AgX',
        'False Color': 'False Color',
        'Filmic sRGB': 'Filmic',
        'Filmic Log': 'Filmic Log',
        'Khronos PBR Neutral sRGB': 'Khronos PBR Neutral',
        'sRGB': 'Standard'
    }