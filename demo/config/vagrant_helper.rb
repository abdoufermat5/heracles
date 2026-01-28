# =============================================================================
# Heracles Demo - Vagrant Configuration
# =============================================================================
# Ruby helper to load demo.conf values for Vagrantfile
# =============================================================================

# Parse demo.conf and return as hash
def load_demo_config(config_path)
  config = {}
  
  File.readlines(config_path).each do |line|
    # Skip comments and empty lines
    next if line.strip.empty? || line.strip.start_with?('#')
    
    # Match KEY="value" or KEY='value' or KEY=value
    if match = line.match(/^([A-Z_][A-Z0-9_]*)=["']?(.*)["']?\s*$/)
      key = match[1]
      value = match[2].gsub(/^["']|["']$/, '')  # Remove surrounding quotes
      
      # Resolve variable references like ${HOST_IP}
      value = value.gsub(/\$\{([A-Z_][A-Z0-9_]*)\}/) { config[$1] || "" }
      
      config[key] = value
    end
  end
  
  config
end

# Load configuration from demo/config/demo.conf
DEMO_CONFIG_PATH = File.join(File.dirname(__FILE__), "demo.conf")
DEMO = load_demo_config(DEMO_CONFIG_PATH)
