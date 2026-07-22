local Hash = {}

local MOD = 4294967296
local MAX = 4294967295

local CONSTANTS = {
    1116352408, 1899447441, 3049323471, 3921009573, 961987163, 1508970993, 2453635748, 2870763221,
    3624381080, 310598401, 607225278, 1426881987, 1925078388, 2162078206, 2614888103, 3248222580,
    3835390401, 4022224774, 264347078, 604807628, 770255983, 1249150122, 1555081692, 1996064986,
    2554220882, 2821834349, 2952996808, 3210313671, 3336571891, 3584528711, 113926993, 338241895,
    666307205, 773529912, 1294757372, 1396182291, 1695183700, 1986661051, 2177026350, 2456956037,
    2730485921, 2820302411, 3259730800, 3345764771, 3516065817, 3600352804, 4094571909, 275423344,
    430227734, 506948616, 659060556, 883997877, 958139571, 1322822218, 1537002063, 1747873779,
    1955562222, 2024104815, 2227730452, 2361852424, 2428436474, 2756734187, 3204031479, 3329325298,
}

local function normalize(value)
    return value % MOD
end

local function bxor(a, b)
    a, b = normalize(a), normalize(b)
    local result, place = 0, 1
    for _ = 1, 32 do
        local aa, bb = a % 2, b % 2
        if aa ~= bb then result = result + place end
        a, b, place = math.floor(a / 2), math.floor(b / 2), place * 2
    end
    return result
end

local function band(a, b)
    a, b = normalize(a), normalize(b)
    local result, place = 0, 1
    for _ = 1, 32 do
        local aa, bb = a % 2, b % 2
        if aa == 1 and bb == 1 then result = result + place end
        a, b, place = math.floor(a / 2), math.floor(b / 2), place * 2
    end
    return result
end

local function xor3(a, b, c)
    return bxor(bxor(a, b), c)
end

local function rshift(value, amount)
    return math.floor(normalize(value) / (2 ^ amount))
end

local function rrotate(value, amount)
    value = normalize(value)
    local low = value % (2 ^ amount)
    return normalize(rshift(value, amount) + low * (2 ^ (32 - amount)))
end

local function word(bytes, offset)
    return bytes[offset] * 16777216 + bytes[offset + 1] * 65536 + bytes[offset + 2] * 256 + bytes[offset + 3]
end

local function appendWord(bytes, value)
    value = normalize(value)
    bytes[#bytes + 1] = rshift(value, 24) % 256
    bytes[#bytes + 1] = rshift(value, 16) % 256
    bytes[#bytes + 1] = rshift(value, 8) % 256
    bytes[#bytes + 1] = value % 256
end

function Hash.sha256(value)
    value = tostring(value or "")
    local bytes = { string.byte(value, 1, #value) }
    local bitLength = #bytes * 8
    bytes[#bytes + 1] = 128
    while (#bytes % 64) ~= 56 do bytes[#bytes + 1] = 0 end
    appendWord(bytes, math.floor(bitLength / MOD))
    appendWord(bytes, bitLength)

    local state = {
        1779033703, 3144134277, 1013904242, 2773480762,
        1359893119, 2600822924, 528734635, 1541459225,
    }

    for block = 1, #bytes, 64 do
        local schedule = {}
        for index = 1, 16 do schedule[index] = word(bytes, block + (index - 1) * 4) end
        for index = 17, 64 do
            local a, b = schedule[index - 15], schedule[index - 2]
            local s0 = xor3(rrotate(a, 7), rrotate(a, 18), rshift(a, 3))
            local s1 = xor3(rrotate(b, 17), rrotate(b, 19), rshift(b, 10))
            schedule[index] = normalize(schedule[index - 16] + s0 + schedule[index - 7] + s1)
        end

        local a, b, c, d = state[1], state[2], state[3], state[4]
        local e, f, g, h = state[5], state[6], state[7], state[8]
        for index = 1, 64 do
            local sum1 = xor3(rrotate(e, 6), rrotate(e, 11), rrotate(e, 25))
            local choice = bxor(band(e, f), band(MAX - e, g))
            local temp1 = normalize(h + sum1 + choice + CONSTANTS[index] + schedule[index])
            local sum0 = xor3(rrotate(a, 2), rrotate(a, 13), rrotate(a, 22))
            local majority = xor3(band(a, b), band(a, c), band(b, c))
            local temp2 = normalize(sum0 + majority)
            h, g, f, e, d, c, b, a = g, f, e, normalize(d + temp1), c, b, a, normalize(temp1 + temp2)
        end

        state[1] = normalize(state[1] + a)
        state[2] = normalize(state[2] + b)
        state[3] = normalize(state[3] + c)
        state[4] = normalize(state[4] + d)
        state[5] = normalize(state[5] + e)
        state[6] = normalize(state[6] + f)
        state[7] = normalize(state[7] + g)
        state[8] = normalize(state[8] + h)
    end

    local parts = {}
    for index = 1, 8 do parts[index] = string.format("%08x", state[index]) end
    return table.concat(parts)
end

function Hash.selfTest()
    local vectors = {
        { "", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" },
        { "abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" },
        { "The quick brown fox jumps over the lazy dog", "d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592" },
    }
    for _, vector in ipairs(vectors) do
        if Hash.sha256(vector[1]) ~= vector[2] then return false, "sha256_self_test_failed" end
    end
    return true
end

return Hash
