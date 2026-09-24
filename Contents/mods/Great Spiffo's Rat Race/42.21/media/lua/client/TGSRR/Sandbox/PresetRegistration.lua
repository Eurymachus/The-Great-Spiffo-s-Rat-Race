require("OptionScreens/SandboxOptions")

local TGSRR_SandboxPresetRegistration = {}
local presetValues = require("Sandbox/TGSRR")

local function applyValues(options, values, prefix)
    for key, value in pairs(values) do
        local path = prefix and (prefix .. "." .. key) or key
        if type(value) == "table" then
            applyValues(options, value, path)
        else
            options:set(path, value)
        end
    end
end

local function addPreset(screen)
    screen.presetList:addOption(
        getText("UI_TGSRR_SandboxPreset"))

    local preset = {
        name = "TGSRR",
        options = SandboxOptions.new(),
        userDefined = false,
    }
    applyValues(preset.options, presetValues)
    screen.presets[#screen.presets + 1] = preset
end

if not SandboxOptionsScreen.tgsrrOriginalLoadPresets then
    SandboxOptionsScreen.tgsrrOriginalLoadPresets =
        SandboxOptionsScreen.loadPresets

    function SandboxOptionsScreen:loadPresets()
        self:tgsrrOriginalLoadPresets()

        for i = 1, #self.presets do
            if self.presets[i].name == "TGSRR" then
                return
            end
        end

        addPreset(self)
    end
end

return TGSRR_SandboxPresetRegistration
