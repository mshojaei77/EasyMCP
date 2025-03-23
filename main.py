import asyncio
import json
import os
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
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

        response = await self.session.list_tools()
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
    # Load configuration from sse_servers.json
    with open('sse_servers.json', 'r') as f:
        config = json.load(f)
    
    # Print available servers
    servers = config.get('mcpServers', {})
    if not servers:
        print("No MCP servers found in sse_servers.json")
        return
    
    print("Available MCP servers:")
    for i, (name, server) in enumerate(servers.items(), 1):
        print(f"{i}. {name}")
    
    # Ask user to select a server
    selection = input("\nSelect a server (number): ")
    try:
        index = int(selection) - 1
        selected_server = list(servers.keys())[index]
        server_url = servers[selected_server]['url']
    except (ValueError, IndexError):
        print("Invalid selection. Exiting.")
        return
    
    print(f"Using server: {selected_server} ({server_url})")
    
    client = MCPClient()
    try:
        await client.connect_to_sse_server(server_url=server_url)
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys
    asyncio.run(main())