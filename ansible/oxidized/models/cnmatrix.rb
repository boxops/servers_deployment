class CNMatrix < Oxidized::Model
  # Match both user mode (>) and privileged mode (#) prompts
  prompt /^([\w.-]+[>#])\s*$/
  comment '# '

  cmd 'show running-config' do |cfg|
    # Clean up any terminal control characters
    cfg.gsub!(/\e\[\d+(;\d+)*[mK]/, '') # Remove ANSI colors and clear codes
    cfg.gsub!(/\r\n?/, "\n") # Normalize line endings
    cfg
  end

  cfg :ssh do
    post_login do
      send "show tech\n"
      expect /^([\w.-]+[>#])\s*$/
    end
  end
end
