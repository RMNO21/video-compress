-- =========================================================================
-- Video-Compress MPV Integration Plugin
-- Author: RMNO21
-- Description: Real-time GPU spatial-temporal reconstruction filter for MPV
-- =========================================================================

local mp = require 'mp'
local utils = require 'mp.utils'

local is_enabled = false
local shader_path = nil

-- Find the shader hook file relative to the script directory
local function find_shader()
    local script_dir = mp.get_script_directory()
    if script_dir then
        local candidate = utils.join_path(script_dir, "video_compress_reconstruct.hook")
        local info = utils.file_info(candidate)
        if info and info.is_file then
            return candidate
        end
        -- Check shaders directory
        local parent_dir = utils.split_path(script_dir)
        local candidate_shader = utils.join_path(parent_dir, "shaders/video_compress_reconstruct.hook")
        info = utils.file_info(candidate_shader)
        if info and info.is_file then
            return candidate_shader
        end
    end
    -- Fallback to default MPV config directory
    local mpv_home = mp.command_native({"expand-path", "~~/shaders/video_compress_reconstruct.hook"})
    return mpv_home
end

local function update_shader_state()
    shader_path = find_shader()
    if not shader_path then
        mp.osd_message("Video-Compress: Shader hook not found!", 3)
        return
    end

    if is_enabled then
        mp.commandv("change-list", "glsl-shaders", "append", shader_path)
        mp.osd_message("🗜️ Video-Compress: GPU Reconstruction [ACTIVE]", 2)
    else
        mp.commandv("change-list", "glsl-shaders", "remove", shader_path)
        mp.osd_message("🗜️ Video-Compress: Reconstruction [BYPASSED]", 2)
    end
end

local function toggle_reconstruction()
    is_enabled = not is_enabled
    update_shader_state()
end

-- Auto-enable if video filename contains _compressed
local function on_file_loaded()
    local path = mp.get_property("path", "")
    if path:match("_compressed") or path:match("%.vcz") then
        if not is_enabled then
            is_enabled = true
            update_shader_state()
        end
    end
end

-- Register keybindings
mp.add_key_binding("ctrl+v", "toggle-video-compress", toggle_reconstruction)
mp.register_event("file-loaded", on_file_loaded)

mp.msg.info("Video-Compress MPV plugin loaded. Press Ctrl+V to toggle GPU reconstruction.")
