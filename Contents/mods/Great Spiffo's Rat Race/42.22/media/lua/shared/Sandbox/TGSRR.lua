local previousSandboxVars = SandboxVars
local preset = {}

SandboxVars = preset
require("TGSRR/Sandbox/Base").apply()
SandboxVars = previousSandboxVars

return preset
