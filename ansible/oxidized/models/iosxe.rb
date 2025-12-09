class IOSXE < Oxidized::Model
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
    # Set appropriate terminal length to avoid pagination
    post_login do
      send "terminal length 0\n"
      expect /^([\w.-]+[>#])\s*$/
    end

    pre_logout do
      cmd 'terminal length 50'
      send "exit\n"
    end
  end
end
