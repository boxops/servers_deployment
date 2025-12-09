class Tachyon < Oxidized::Model
  # Use the 'exec' input method
  cfg :exec do
    # Pass multiple parameters: IP, name, model, username, password, etc.
    cmd '/usr/bin/python3 /usr/local/bin/tachyon.py #{@node.ip} #{@node.name} #{@node.model.class.name} #{@node.auth[:username]} #{@node.auth[:password]}' do |cfg|
    #   cfg.gsub!(/timestamp_to_remove/, '')  # Clean output if needed
      cfg
    end
  end
end
