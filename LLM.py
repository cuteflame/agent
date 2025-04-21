from openai import OpenAI, AsyncOpenAI
import os 
import asyncio
from mcp import Tool
import dotenv
from pydantic import BaseModel
from rich import print as rprint
from utils import Logger
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from openai.types import FunctionDefinition
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

#加载.env环境变量
dotenv.load_dotenv()

'''
Agent大脑部分 接受用户输入后使用llm的api与llm进行对话,
1.利用api连接到llm,注意各种字段的传输
2.不使用langchain这些框架，自行封装对话。
3.llm要能接受用户输入，进行规划，利用mcp客户端和mcp服务器进行工具的调用
4.检查工具调用结果，进行数据验证
'''
# 初始化 logger 实例
Log = Logger.Logger()
Log.title("HELLO START")

#解析和结构化OPenAI返回的tool call相关内容
class ToolCallFunction(BaseModel):#pydantic basemodel自动做数据校验
    name: str = ""
    arguments: str = ""

class ToolCall(BaseModel):
    id: str = ""
    function: ToolCallFunction = ToolCallFunction()

class ChatOpenAIChatResponse(BaseModel):
    content: str = ""
    tool_calls: list[ToolCall] = []

'''使用装饰器来简化类的定义，类用来封装与api进行交互所需的操作和参数，方便用户设置模型、消息、工具、系统提示、和上下文。
'''
@dataclass
class LLM:
    model: str
    messages: List[ChatCompletionMessageParam] = field(default_factory=list)
    tools: List[Tool] = field(default_factory=list)
    system_prompt: str = ""
    context: str = ""
    llm: AsyncOpenAI = field(init=False)

    def __post_init__(self) -> None:
        '''
        dataclass钩子函数，会在init初始化之后自动调用
        用来设置无法自动初始化的字段，llm,本例中初始化了一个异步客户端
        也可以对输入变量做预处理'''
        Log.title("init LLM")
        self.llm = AsyncOpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL")
        )
        if self.system_prompt:
            self.messages.insert(0, {"role": "system", "content": self.system_prompt})#插入到第一个位置
        if self.context:
            self.messages.append({"role": "user", "content": self.context})
            #对话前可以进行一个异常处理
    async def chat(
        self, prompt: str = "", print_llm_output: bool = True
    ) -> ChatOpenAIChatResponse:
        try:
            return await self._chat(prompt, print_llm_output)
        except Exception as e:
            rprint(f"Error during chat: {e!s}")
            raise
    async def _chat(self, prompt: str = "", print_llm_output: bool = True) -> ChatOpenAIChatResponse:
        '''异步方法 说明里面有await操作，例如异步请求
        功能：添加一条用户prompt
        调用OpenAI接口 实时打印LLM响应处理工具 调用结果 返回结果'''
        Log.title("enter CHAT")
        if prompt:
            self.messages.append({"role": "user", "content": prompt})
        
        content = ""
        tool_calls: list[ToolCall] = []
        printed_llm_output = False
        
        # 获取工具定义
        tools_definition = self.get_tools_definition()
        
        async with await self.llm.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=tools_definition,  # 添加工具定义
            tool_choice="auto",  # 让模型自动选择工具
            stream=True,
        ) as stream:
            Log.title("llm RESPONSE")
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    content += delta.content or ""
                    if print_llm_output:
                        print(delta.content, end="")
                        printed_llm_output = True
                #处理tool-call
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        if len(tool_calls)<=tool_call.index:
                            tool_calls.append(ToolCall())
                        this_tool_call = tool_calls[tool_call.index]
                        if tool_call.id:
                            this_tool_call.id += tool_call.id or ""
                        if tool_call.function:
                            if tool_call.function.name:
                                this_tool_call.function.name += (
                                    tool_call.function.name or ""
                                )
                            if tool_call.function.arguments:
                                this_tool_call.function.arguments += (
                                    tool_call.function.arguments or ""
                                )

            if printed_llm_output:
                print()

            self.messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {
                        "type": "function",
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            })

        return ChatOpenAIChatResponse(
            content=content,
            tool_calls=tool_calls
        )
    def get_tools_definition(self) -> list[ChatCompletionToolParam]:
        '''将我们定义的工具，转换为open sdk需要的function call结构'''
        return [
            ChatCompletionToolParam(
                type="function",
                function=FunctionDefinition(
                    name=t.name,
                    description=t.description,
                    parameters=t.inputSchema,
                ),
            )
            for t in self.tools
        ]
    def append_tool_result(self, tool_call_id: str, tool_output: str) -> None:
        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": tool_output,
            }
        )
# # 假设Tool定义如下（你可以换成mcp.Tool）
# @dataclass
# class Tool:
#     name: str
#     description: str
#     inputSchema: dict

# # 添加一个测试函数
# async def main():
#     # 定义一个假工具
#     hello_tool = Tool(
#         name="say_hello",
#         description="Say hello to someone",
#         inputSchema={
#             "type": "object",
#             "properties": {
#                 "name": {
#                     "type": "string",
#                     "description": "The name of the person"
#                 }
#             },
#             "required": ["name"]
#         }
#     )

#     # 初始化LLM
#     llm = LLM(
#         model="gpt-4o-mini",
#         system_prompt="You are a helpful assistant.",
#         tools=[hello_tool],
#     )

#     # 打印工具定义（测试get_tools_definition）
#     rprint(llm.get_tools_definition())

#     # 模拟与模型对话
#     result = await llm.chat("Please say hello to Alice.")
#     rprint(result)

# # 运行程序
# if __name__ == "__main__":
#     asyncio.run(main())