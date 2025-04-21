import asyncio
from LLM import LLM
from McpClient import MCPClient
from Agent import Agent

async def main():
    fetchMcp = MCPClient(name="fetch", command="uvx",  
            args=['mcp-server-fetch'])
    fileMcp = MCPClient(name="file", command="npx",  
            args=["-y",
            "@modelcontextprotocol/server-filesystem",
            "/Users/xuan/projects/llm-mcp-rag",
           ])
    mcp_clients = [fetchMcp, fileMcp]

    agent = Agent(model="gpt-4o-mini", mcp_clients=mcp_clients)
    await agent.init()
    response = await agent.invoke("爬取https://jsonplaceholder.typicode.com/users的内容，在${currentDir}/knowledge中，每个人创建一个md文件，保存基本信息")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())