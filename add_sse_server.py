import json
import os

def add_mcp_server_to_config(new_server_data):
    config_path = "sse_servers.json"
    
    # Check if config file exists
    if os.path.exists(config_path):
        try:
            # Read existing config
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Ensure mcpServers key exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}
            
            # Add the new server to mcpServers
            for server_name, server_info in new_server_data["mcpServers"].items():
                config["mcpServers"][server_name] = server_info
                
            # Write updated config back to file
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            print(f"Successfully added server(s) to {config_path}")
            
        except json.JSONDecodeError:
            print(f"Error: {config_path} contains invalid JSON")
        except Exception as e:
            print(f"Error updating config: {str(e)}")
    else:
        # Create new config file with the server
        with open(config_path, 'w') as f:
            json.dump(new_server_data, f, indent=2)
            
        print(f"Created new {config_path} with server configuration")

if __name__ == "__main__":
    # New server configuration to add
    new_server = {
      "mcpServers": {
        "@modelcontextprotocol/fetch": {
          "url": "https://router.mcp.so/sse/lt1h2im8llmqnp"
        }
      }
    }

    add_mcp_server_to_config(new_server)
