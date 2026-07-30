local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "client/?.lua;"
    .. sourceRoot .. "shared/?.lua;"
    .. package.path

package.loaded["OptionScreens/SandboxOptions"] = {}
package.loaded["Sandbox/TGSRR"] = {
    Zombies = 1,
    MultiplierConfig = {
        Global = 0.8,
    },
}

SandboxOptionsScreen = {}

function SandboxOptionsScreen:loadPresets()
    self.presets = {
        { name = "Apocalypse" },
    }
    self.presetList = {
        options = { "Apocalypse" },
        addOption = function(list, text)
            list.options[#list.options + 1] = text
        end,
    }
end

function getText(key)
    assert(key == "UI_TGSRR_SandboxPreset")
    return "Unofficial TGSRR"
end

local applied = {}
SandboxOptions = {
    new = function()
        return {
            set = function(_, name, value)
                applied[name] = value
            end,
        }
    end,
}

require("TGSRR/Sandbox/PresetRegistration")

local screen = setmetatable({}, { __index = SandboxOptionsScreen })
screen:loadPresets()

assert(#screen.presets == 2)
assert(screen.presets[2].name == "TGSRR")
assert(screen.presets[2].userDefined == false)
assert(screen.presetList.options[2] == "Unofficial TGSRR")
assert(applied.Zombies == 1)
assert(applied["MultiplierConfig.Global"] == 0.8)

screen:loadPresets()
assert(#screen.presets == 2)

print("sandbox preset registration test passed")
