plugin {
    id = "vitusli.openInVSCode",
    name = "Open Current Folder in VS Code",
    apiVersion = "2.2",
    author = "vitusli",
    email = "vituspach@gmail.com"
}

action {
    id = "openCurrentInVSCode",
    name = "Open Current Folder in VS Code",
    apply = function(context)
        local pane = context.activePane
        if not pane then return end
        local model = pane.model
        if not model then return end
        local folder = model.folder
        if not folder then return end
        local path = folder.path.rawValue
        -- Open the folder in Visual Studio Code via bundle identifier
        martax.openFiles(path, "com.microsoft.VSCode")
    end
}
