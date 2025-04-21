import asyncio
from dataclasses import dataclass
import json
from rich import print as rprint
from LLM import LLM
from McpClient import MCPClient
from utils.Logger import Logger

log = Logger()
@dataclass#省略自己写构造函数
class Agent:
    mcp_clients: list[MCPClient]
    model: str
    llm: LLM | None = None
    system_prompt: str = ""
    context: str = ""

    async def init(self) -> None:
        log.title("INIT LLM& MCP client")
        tools = []
        for mcp_client in self.mcp_clients:
            await mcp_client.init()#先初始化mcp_client,初始化会主动去连接srever，建立session，get tools
            tools.extend(mcp_client.get_tools())
        self.llm = LLM(
            self.model,
            tools=tools,
            system_prompt=self.system_prompt,
            context=self.context,
        )

    async def cleanup(self) -> None:
        log.title("CLEANUP LLM&Client")
        while self.mcp_clients:
            mcp_client = self.mcp_clients.pop()#pop是list方法从列表中表尾弹出一个
            await mcp_client.cleanup()

    async def invoke(self, prompt: str) -> str | None:#agent向外暴露的唯一接口
        return await self._invoke(prompt)

    async def _invoke(self, prompt: str) -> str | None:#_代表内部使用的方法
        if self.llm is None:
            raise ValueError("llm not call .init()")#判断llm是否初始化了，未初始化成功就不能进行chat
        llm_resp = await self.llm.chat(prompt)
        '''开始持续与llm对话'''
        i = 0
        while True:
            log.title(f"INVOKE CYCLE {i}")
            i += 1
            # 处理工具调用
            rprint(llm_resp)#打印本轮llm的回复
            if llm_resp.tool_calls:#检查llm回复是否有tool_calls
                for tool_call in llm_resp.tool_calls:#如果有tool_calls
                    target_mcp_client: MCPClient | None = None#
                    for mcp_client in self.mcp_clients:
                        if tool_call.function.name in [
                            t.name for t in mcp_client.get_tools()
                        ]:
                            target_mcp_client = mcp_client
                            break
                    if target_mcp_client:
                        log.title(f"TOOL USE `{tool_call.function.name}`")
                        rprint("with args:", tool_call.function.arguments)
                        mcp_result = await target_mcp_client.call_tool(#mcp——client进行工具调用
                            tool_call.function.name,
                            json.loads(tool_call.function.arguments),
                        )
                        rprint("call result:", mcp_result)
                        self.llm.append_tool_result(
                            tool_call.id, mcp_result.model_dump_json()
                        )
                    else:
                        self.llm.append_tool_result(tool_call.id, "tool not found")#没有找到工具
                llm_resp = await self.llm.chat()#调用工具结束之后，直接进入下一轮循环
            else:
                return llm_resp.content
            

