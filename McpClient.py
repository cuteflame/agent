import asyncio #异步IO库
from typing import Optional, Any#类型提示
from contextlib import AsyncExitStack#异步上下文管理
#MCP相关客户端组件
from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client
from rich import print as rprint
from utils import Logger
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env
Log = Logger.Logger()

#客户端类
class MCPClient:
    def __init__(
        self,
        name: str,  # 客户端名称
        command: str,  # 要执行的命令 因为执行命令是uv *** 命令+参数
        args: list[str],  # 命令参数
        version: str = "1.0.0",  # 版本号
    ):
        self.session: Optional[ClientSession] = None  # MCP会话，初始为None
        self.exit_stack = AsyncExitStack()  # 异步退出栈，用于管理多个异步上下文
        self.name = name  # 客户端名称
        self.version = version  # 客户端版本
        self.command = command  # 要执行的命令
        self.args = args  # 命令参数
        self.tools: list[Tool] = []  # 可用工具列表，初始为空
    
    async def init(self) -> None:
        """初始化客户端并连接到服务器"""
        Log.title("init MCPclient")
        await self._connect_to_server()
    
    async def cleanup(self) -> None:
        Log.title("close MCPclient")
        """清理资源，关闭连接"""
        if not self.exit_stack:
            return  # 如果没有初始化，则不需要清理
        
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            print(f"Error during MCP client cleanup: {e}")
            # 不要再次抛出异常，以避免干扰其他清理操作

    async def _connect_to_server(self) -> None:
        """连接到MCP服务器"""
        Log.title("connect MCPserver")
        # 设置服务器参数
        server_params = StdioServerParameters(
            command=self.command,  # 要执行的命令
            args=self.args,  # 命令参数
        )

        # 创建标准输入输出客户端
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params),
        )
        self.stdio, self.write = stdio_transport  # 解包输入和输出流
    
        # 创建客户端会话
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        # 初始化会话
        await self.session.initialize()

        # 获取可用工具列表
        Log.title("MCPserver tools")
        response = await self.session.list_tools()
        self.tools = response.tools
        rprint("\nConnected to server with tools:", [tool.name for tool in self.tools])

    def get_tools(self) -> list[Tool]:
        """获取可用工具列表"""
        return self.tools  # 返回可用工具列表

    async def call_tool(self, name: str, params: dict[str, Any]):
        """调用指定名称的工具"""
        if not self.session:
            raise RuntimeError("Session not initialized. Call init() first.")
        return await self.session.call_tool(name, params)

# # 示例函数
# async def example():
#     """测试MCP客户端功能的示例"""

#     client = MCPClient(
#         name="fetchMcpclient",  # fetchMCP是官方提供的一个server
#         command="uvx",  # server提供了一个fetch工具，提供一个url获取到内容
#         args=['mcp-server-fetch'],
#     )
#     await client.init()  # 初始化异步连接
#     tools = client.get_tools()  # 使用client而不是fetchMcpclient
#     rprint(tools)
#     await client.cleanup()  # 使用client而不是fetchMcpclient


# if __name__ == "__main__":
#     asyncio.run(example())