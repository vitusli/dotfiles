plugin {
    id = "vitusli.openInZed",
    name = "Open Current Folder in Zed",
    apiVersion = "2.2",
    author = "vitusli",
    email = "vituspach@gmail.com"
}

action {
    id = "openCurrentInZed",
    name = "Open Current Folder in Zed",
    apply = function(context)
        local pane = context.activePane
        if not pane then return end
        local model = pane.model
        if not model then return end
        local folder = model.folder
        if not folder then return end
        local path = folder.path.rawValue
        -- Open the folder in Zed using the open command
        martax.execute("/usr/bin/open", {"-a", "Zed", path})
    end
}
