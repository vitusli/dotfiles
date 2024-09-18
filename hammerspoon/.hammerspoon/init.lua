require("hs.ipc")
hs.ipc.cliInstall()

-- works
-- hs.hotkey.bind({ "cmd", "alt", "ctrl" }, "E", function()
-- 	hs.alert.show("Hello World!")
-- end)

hs.hotkey.bind({ "cmd", "alt", "ctrl" }, "W", function()
	hs.notify.new({ title = "Hammerspoon", informativeText = "Hello World" }):send()
end)

hs.hotkey.bind({ "cmd", "alt", "ctrl" }, "Q", function()
	hs.console.clearConsole()
end)

-- ich sollte das floating window komplett ueber hammerspoon klaeren
-- hotkey: super - f = aerospace floating, scale x% und center, mode stacked, notify
