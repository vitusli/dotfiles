plugin {
    id = "vitusli.openInVisualEditor",
    name = "Open Current Folder in VISUAL Editor",
    apiVersion = "2.2",
    author = "vitusli",
    email = "vituspach@gmail.com"
}

action {
    id = "openCurrentInVisualEditor",
    name = "Open Current Folder in VISUAL Editor",
    apply = function(context)
        local pane = context.activePane
        if not pane then return end
        local model = pane.model
        if not model then return end
        local folder = model.folder
        if not folder then return end
        local path = folder.path.rawValue
        -- Open the folder using $VISUAL environment variable (defaults to zed)
        local visual = os.getenv("VISUAL") or "zed"
        martax.execute("/bin/sh", {"-c", visual .. " " .. "'" .. path .. "'"})
    end
}
