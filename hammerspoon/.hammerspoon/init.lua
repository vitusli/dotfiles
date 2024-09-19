hs.hotkey.bind({ "cmd", "alt", "ctrl" }, "R", function()
	hs.reload()
end)
hs.notify.new({ title = "Hammerspoon", informativeText = "Config relaod" }):send()
-- [ ] TODO sketchybar script

--require("hs.ipc")
--hs.ipc.cliInstall()

--------------
-- Send command(s) to Aerospace (way to complicated for me)
local function aerospace_cli(commands)
	for _, cmd in ipairs(commands) do
		local args = {}
		for arg in string.gmatch(cmd, "%S+") do
			table.insert(args, arg)
		end
		hs.task.new("/opt/homebrew/bin/aerospace", nil, args):start()
	end
end

-- [ ] TODO I also want to feed functions not related to aerospace into to cli (draw mode into sketchybar)
-- bestimmt: if mode $var then $drawiconVAR
-- irgendwie den mode auslesen mit ner Variable oder ner eigenen Funktion
-- define super key
local function super(key, commands)
	hs.hotkey.bind({ "cmd", "alt", "ctrl" }, key, function()
		aerospace_cli(commands)
	end)
end

--------------
-- dependend on super key
super("w", { "layout floating tiling", "mode main" })
