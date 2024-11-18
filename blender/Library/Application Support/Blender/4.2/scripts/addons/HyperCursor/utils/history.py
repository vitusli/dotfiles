import bpy
import re

def add_history_entry(debug=False):
    context = bpy.context

    scene = context.scene
    hc = scene.HC

    cmx = scene.cursor.matrix
    loc, rot, _ = cmx.decompose()

    h = hc.historyCOL.add()
    h.mx = cmx
    h.location = loc
    h.rotation = rot.to_matrix()

    newidx = hc.historyIDX + 1

    hc.historyIDX = newidx

    if newidx != len(hc.historyCOL) - 1:
        hc.historyCOL.move(len(hc.historyCOL) - 1, newidx)

    prettify_history(context)

    if debug:
        print(f"INFO: Added new Cursor History entry at {hc.historyIDX}/{len(hc.historyCOL) - 1}")

def prettify_history(context):
    historyCOL = context.scene.HC.historyCOL

    nameidx = 0
    nameRegex = re.compile(r"Cursor\.[\d]{3}")

    for idx, entry in enumerate(historyCOL):
        entry.index = idx

        mo = nameRegex.match(entry.name)

        if not (entry.name and not mo):
            entry.name = f"Cursor.{str(nameidx).zfill(3)}"
            nameidx += 1
