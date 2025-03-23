import json
import os

def add_mcp_server_to_config(new_server_data, config_path="sse_servers.json"):
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

def check_server_type(server_data):
    """Check if 'npx' or 'uv' is present in the server configuration"""
    if "mcpServers" not in server_data:
        return None
    
    for server_name, server_info in server_data["mcpServers"].items():
        # Check if 'npx' or 'uv' is in command
        command = server_info.get("command", "")
        if command == "npx":
            return "npx"
        elif command == "uv":
            return "uv"
        
        # Check if 'npx' or 'uv' is in any of the args
        args = server_info.get("args", [])
        for arg in args:
            arg_str = str(arg)
            if "npx" in arg_str:
                return "npx"
            elif "uv" in arg_str:
                return "uv"
    
    return None

if __name__ == "__main__":
    # New server configuration to add
    new_server = {
  "mcpServers": {
    "sqlite": {
      "command": "uv",
    "args": [
      "--directory",
      "parent_of_servers_repo/servers/src/sqlite",
      "run",
      "mcp-server-sqlite",
      "--db-path",
      "~/test.db"
    ]
  }
}
}
    # Check server type and add to appropriate config file
    server_type = check_server_type(new_server)
    if server_type == "npx":
        add_mcp_server_to_config(new_server, "npx_servers.json")
    elif server_type == "uv":
        add_mcp_server_to_config(new_server, "uv_servers.json")
    else:
        add_mcp_server_to_config(new_server)
