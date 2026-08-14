local previousSandboxVars = SandboxVars
local preset = {}

SandboxVars = preset
local ok, err = pcall(function()
    require("TGSRR/Sandbox/Base").apply()
end)
SandboxVars = previousSandboxVars

if not ok then
    error(err)
end

return preset
