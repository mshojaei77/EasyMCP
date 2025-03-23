import asyncio
import json
import os
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

from openai import OpenAI
from dotenv import load_dotenv
import anyio

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self._streams_context = None
        self._session_context = None
        self.exit_stack = AsyncExitStack()
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")

    async def connect_to_sse_server(self, server_url: str):
        """Connect to an MCP server running with SSE transport"""
        # Store the context managers so they stay alive
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        # Initialize
        await self.session.initialize()

        # List available tools to verify connection
        print("Initialized SSE client...")
        print("Listing tools...")
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def connect_to_stdio_server(self, command: str, args: list):
        """Connect to an MCP server running with STDIO transport (NPX, UV, etc.)"""
        # On Windows, we need to use cmd.exe to run npx
        if os.name == 'nt' and command in ['npx', 'uv']:
            # Convert the command and args to a single command string for cmd.exe
            cmd_args = ' '.join([command] + args)
            server_params = StdioServerParameters(
                command='cmd.exe',
                args=['/c', cmd_args]
            )
        else:
            # For non-Windows systems or other commands
            server_params = StdioServerParameters(command=command, args=args)
        
        # Store the context managers so they stay alive
        self._streams_context = stdio_client(server_params)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        # Initialize
        await self.session.initialize()

        # List available tools to verify connection
        print(f"Initialized {command.upper()} client...")
        print("Listing tools...")
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def cleanup(self):
        """Properly clean up the session and streams"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        # Try to get tools list, with reconnection logic if needed
        try:
            response = await self.session.list_tools()
        except anyio.BrokenResourceError:
            print("Connection to server lost. Attempting to reconnect...")
            # Get the current server details from the existing session
            # This is a simplified reconnection - you might need to adjust based on server type
            if hasattr(self._streams_context, 'url'):  # SSE connection
                server_url = self._streams_context.url
                await self.cleanup()
                await self.connect_to_sse_server(server_url)
            else:
                print("Unable to automatically reconnect. Please restart the client.")
                return "Connection to server lost. Please restart the client."
            
            # Try again after reconnection
            try:
                response = await self.session.list_tools()
            except Exception as e:
                return f"Failed to reconnect to server: {str(e)}"

        available_tools = [{ 
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in response.tools]

        # Initial OpenAI API call
        try:
            response = self.openai.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=available_tools,
                tool_choice="auto"
            )

            # Process response and handle tool calls
            tool_results = []
            final_text = []

            message = response.choices[0].message
            final_text.append(message.content or "")
            
            # Check if the model wants to call a tool
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        # Execute tool call
                        print(f"Calling tool: {tool_name} with args: {json.dumps(tool_args)}")
                        result = await self.session.call_tool(tool_name, tool_args)
                        
                        # Extract the content as a string from the result object
                        if hasattr(result, 'content'):
                            result_content = str(result.content)
                        else:
                            result_content = str(result)
                            
                        tool_results.append({"call": tool_name, "result": result_content})
                        final_text.append(f"[Calling tool {tool_name} with args {json.dumps(tool_args)}]")

                        # Add assistant's response with tool call to the messages
                        messages.append({
                            "role": "assistant",
                            "content": None,  # OpenAI requires content to be null when tool_calls is present
                            "tool_calls": [
                                {
                                    "id": tool_call.id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_call.function.name,
                                        "arguments": tool_call.function.arguments
                                    }
                                }
                            ]
                        })
                        
                        # Add the tool response to messages - Make sure it's a simple string
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result_content  # This must be a string, not an object
                        })

                        # Get next response from OpenAI
                        response = self.openai.chat.completions.create(
                            model=self.model,
                            messages=messages
                        )
                        
                        final_text.append(response.choices[0].message.content)
                    except Exception as e:
                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                        print(error_msg)
                        final_text.append(error_msg)
                        # Continue with OpenAI to get a response even if tool call failed
                        messages.append({
                            "role": "system",
                            "content": f"There was an error calling the {tool_name} tool: {str(e)}. Please respond without using the tool."
                        })
                        response = self.openai.chat.completions.create(
                            model=self.model,
                            messages=messages
                        )
                        final_text.append(response.choices[0].message.content)
                
            return "\n".join(final_text)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"An error occurred: {str(e)}"
    

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                elif not query:
                    continue
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
                import traceback
                traceback.print_exc()  # Print the full error traceback for debugging


async def main():
    # Initialize empty servers dictionary
    servers = {}
    server_types = {}
    
    # Load configuration from sse_servers.json
    try:
        with open('sse_servers.json', 'r') as f:
            sse_config = json.load(f)
            sse_servers = sse_config.get('mcpServers', {})
            for name, server in sse_servers.items():
                servers[name] = server
                server_types[name] = "sse"
        print("Loaded SSE servers configuration.")
    except FileNotFoundError:
        print("sse_servers.json not found, continuing without SSE servers.")
    except json.JSONDecodeError:
        print("Error parsing sse_servers.json, continuing without SSE servers.")
    
    # Load configuration from npx_servers.json
    try:
        with open('npx_servers.json', 'r') as f:
            npx_config = json.load(f)
            npx_servers = npx_config.get('mcpServers', {})
            for name, server in npx_servers.items():
                servers[name] = server
                server_types[name] = "npx"
        print("Loaded NPX servers configuration.")
    except FileNotFoundError:
        print("npx_servers.json not found, continuing without NPX servers.")
    except json.JSONDecodeError:
        print("Error parsing npx_servers.json, continuing without NPX servers.")
        
    # Load configuration from uv_servers.json
    try:
        with open('uv_servers.json', 'r') as f:
            uv_config = json.load(f)
            uv_servers = uv_config.get('mcpServers', {})
            for name, server in uv_servers.items():
                servers[name] = server
                server_types[name] = "uv"
        print("Loaded UV servers configuration.")
    except FileNotFoundError:
        print("uv_servers.json not found, continuing without UV servers.")
    except json.JSONDecodeError:
        print("Error parsing uv_servers.json, continuing without UV servers.")
    
    # Check if we have any servers
    if not servers:
        print("No MCP servers found in configuration files.")
        return
    
    # Print available servers
    print("\nAvailable MCP servers:")
    for i, name in enumerate(servers.keys(), 1):
        server_type = server_types[name]
        print(f"{i}. {name} ({server_type.upper()})")
    
    # Ask user to select a server
    selection = input("\nSelect a server (number): ")
    try:
        index = int(selection) - 1
        selected_server = list(servers.keys())[index]
        server_config = servers[selected_server]
        server_type = server_types[selected_server]
    except (ValueError, IndexError):
        print("Invalid selection. Exiting.")
        return
    
    client = MCPClient()
    try:
        if server_type == "sse":
            server_url = server_config['url']
            print(f"Using SSE server: {selected_server} ({server_url})")
            await client.connect_to_sse_server(server_url=server_url)
        elif server_type in ["npx", "uv"]:
            command = server_config['command']
            args = server_config['args']
            print(f"Using {server_type.upper()} server: {selected_server} ({command} {' '.join(args)})")
            await client.connect_to_stdio_server(command=command, args=args)
        
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys
    asyncio.run(main())