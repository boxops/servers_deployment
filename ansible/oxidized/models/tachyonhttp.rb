# /home/oxidized/.config/oxidized/model/tachyonhttp.rb
class TachyonHTTP < Oxidized::Model
  # Use the 'http' input method
  cfg :http do
    @username = @node.auth[:username]
    @password = @node.auth[:password]
    @secure = false
    @ssl_verify = false
    @headers = {}
  end

  def cmd
    puts "DEBUG: cmd method started for #{@node.ip}"
    
    # Test 1: Simple output first
    test_output = "! Test output for #{@node.name}\n! This should appear in the config file"
    puts "DEBUG: Test output: #{test_output}"
    
    # Test 2: Try a simple HTTP GET first
    simple_test = simple_http_test
    puts "DEBUG: Simple HTTP test result: #{simple_test}"
    
    # Test 3: Now try the actual login + config flow
    real_config = get_real_config
    puts "DEBUG: Real config result: #{real_config}"
    
    # Return whatever we got
    real_config || simple_test || test_output
  end

  def simple_http_test
    puts "DEBUG: Testing simple HTTP connection"
    begin
      response = get("https://#{@node.ip}/cgi.lua/apiv1/login", {})
      puts "DEBUG: Simple test response: #{response.inspect}"
      "! Simple test successful: #{response.class.name}"
    rescue => e
      puts "DEBUG: Simple test failed: #{e.message}"
      "! Simple test failed: #{e.message}"
    end
  end

  def get_real_config
    puts "DEBUG: Attempting real config retrieval"
    
    # Login first
    login_result = login
    puts "DEBUG: Login result: #{login_result}"
    
    if login_result
      config_result = fetch_config
      puts "DEBUG: Config result: #{config_result}"
      config_result
    else
      "! Login failed"
    end
  end

  def login
    puts "DEBUG: Attempting login to #{@node.ip}"
    puts "DEBUG: Username: #{@username}, Password: #{@password}"
    
    url = "https://#{@node.ip}/cgi.lua/apiv1/login"
    payload = {
      username: @username,
      password: @password
    }
    
    puts "DEBUG: Login URL: #{url}"
    puts "DEBUG: Login payload: #{payload}"
    
    begin
      response = post(url, payload, {'Content-Type' => 'application/json'})
      puts "DEBUG: Login response: #{response.inspect}"
      
      if response && response['token']
        @headers['Cookie'] = "api_token=#{response['token']}"
        puts "DEBUG: Login successful, cookie set: #{@headers['Cookie']}"
        true
      else
        puts "DEBUG: Login failed, no token in response"
        false
      end
    rescue => e
      puts "DEBUG: Login exception: #{e.message}"
      false
    end
  end

  def fetch_config
    puts "DEBUG: Fetching config from #{@node.ip}"
    puts "DEBUG: Using headers: #{@headers}"
    
    url = "https://#{@node.ip}/cgi.lua/apiv1/config"
    
    begin
      response = get(url, @headers)
      puts "DEBUG: Config response: #{response.inspect}"
      
      if response && response['config']
        json_to_plaintext(response['config'])
      else
        puts "DEBUG: No config in response"
        "! No configuration data received"
      end
    rescue => e
      puts "DEBUG: Config fetch exception: #{e.message}"
      "! Config fetch error: #{e.message}"
    end
  end

  def json_to_plaintext(config, indent=0)
    puts "DEBUG: Converting JSON to plaintext"
    output = []
    
    process_dict = lambda do |data, current_indent|
      data.each do |key, value|
        if value.is_a?(Hash)
          output << " " * current_indent + "#{key}:"
          process_dict.call(value, current_indent + 2)
        elsif value.is_a?(Array)
          output << " " * current_indent + "#{key}:"
          value.each do |item|
            if item.is_a?(Hash)
              process_dict.call(item, current_indent + 2)
            else
              output << " " * (current_indent + 2) + "#{item}"
            end
          end
        else
          output << " " * current_indent + "#{key}: #{value}"
        end
      end
    end

    process_dict.call(config, indent)
    result = output.join("\n")
    puts "DEBUG: Plaintext result:\n#{result}"
    result
  end

  prompt /^([\w.@-]+[#>]\s?)$/
end
