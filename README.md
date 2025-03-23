# EasyMCP

EasyMCP is a flexible and beginner-friendly client for the Model Context Protocol (MCP). It allows you to connect to different types of MCP servers—SSE, NPX, and UV—so you can interact with various tools (e.g., file operations) and integrate with the OpenAI API for an enhanced chat experience.

## Features

- **Multiple Server Support**  
  - **SSE Servers:** Connect via Server-Sent Events using a server URL.
  - **NPX Servers:** Launch servers using NPX commands (compatible with Windows and non-Windows systems).
  - **UV Servers:** Run servers configured with UV commands.
- **Dynamic Tool Integration:**  
  The client automatically retrieves available tools from the connected server and uses them to process user queries.
- **Interactive Chat Loop:**  
  Type queries and let the client process responses using OpenAI and the available MCP tools.
- **Configuration Management:**  
  Easily add new server configurations with `add_server.py`, which updates the appropriate configuration file (e.g., `sse_servers.json`, `npx_servers.json`, or `uv_servers.json`).

## Prerequisites

- **Python 3.10+** (for compatibility with `asyncio` and modern async features)
- A valid OpenAI API key (set in your `.env` file)
- Other API keys as needed for additional integrations

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/EasyMCP.git
   cd EasyMCP
   ```

2. **Create a virtual environment and activate it:**

   On Windows:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

   On macOS/Linux:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install the required packages:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up your environment variables:**  
   Rename the provided `.env.sample` to `.env` (or create your own `.env`) and fill in the necessary API keys and configurations.

## Server Configuration Files

EasyMCP uses several JSON configuration files to manage servers:

- **sse_servers.json:** Contains configurations for SSE-based servers.  
  Example:
  ```json
  {
    "mcpServers": {
      "@modelcontextprotocol/time": {
        "url": "https://router.mcp.so/sse/pnabizm8lkazpr"
      }
    }
  }
  ```

- **npx_servers.json:** Contains configurations for NPX servers.  
  Example:
  ```json
  {
    "mcpServers": {
      "filesystem": {
        "command": "npx",
        "args": [
          "-y",
          "@modelcontextprotocol/server-filesystem",
          "C:\\Users\\lotus\\Documents\\llm_books_papers",
          "C:\\Users\\lotus\\Documents\\llm_books_papers"
        ]
      }
    }
  }
  ```

- **uv_servers.json:** Contains configurations for UV servers.  
  Example:
  ```json
  {
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
  ```

## Usage

1. **Run the MCP Client:**

   ```bash
   python main.py
   ```

2. **Select a Server:**  
   The client will load available servers from `sse_servers.json`, `npx_servers.json`, and `uv_servers.json`. When prompted, enter the corresponding number to select a server.

3. **Interact With the Client:**  
   Once connected, type your queries. For example:
   - To read a PDF file: `read Build a Large Language Model.pdf`
   - To use a file tool: `use read_file tool and read 2308.11432v5.pdf`

   The client will guide you through constructing proper file paths based on the allowed directories provided by the MCP server.

## Adding a New Server

To add a new MCP server configuration:

1. **Prepare your JSON configuration** for the new server.
2. **Run `add_server.py`:**

   ```bash
   python add_server.py
   ```

   This script will:
   - Detect the server type (NPX, UV, or default to SSE).
   - Append the new configuration to the appropriate file (e.g., `npx_servers.json`, `uv_servers.json`, or `sse_servers.json`).

## Example Files

- **main.py:**  
  The main entry point of the EasyMCP client. It handles server connections, the chat loop, and processing queries with OpenAI integration.

- **add_server.py:**  
  A script to add new MCP server configurations to the JSON files.

- **UV_client.py & NPX_client.py:**  
  Example client scripts that show how to connect to UV and NPX servers respectively.

- **.env:**  
  Contains environment variables such as API keys and model configurations.

- **requirements.txt:**  
  Lists the project dependencies.  
  (Note: For JavaScript projects, remember to use `yarn` for dependency management; however, this project uses Python.)

## Contributing

Contributions are welcome! Please fork the repository and submit pull requests with detailed descriptions of your changes.

## License

This project is open source and available under the [MIT License](LICENSE).

## Contact

For questions or feature requests, feel free to open an issue in the GitHub repository.

Happy coding!