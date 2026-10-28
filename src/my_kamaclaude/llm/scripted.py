from copy import deepcopy
from .types import LlmResponse, Message, ToolResult, response1, response2

class ScriptedProvider:
    def __init__(self, responses: list[LlmResponse]) -> None:
        self._responses = deepcopy(responses)
        self._index = 0
        self.requests: list[dict[str, object]] = []

    async def chat(
            self,
            messages: list[Message],
            tool_schemas: list[dict[str, object]]|None=None,
    ) -> LlmResponse:
        self.requests.append(
            deepcopy({
                "messages": messages,
                "tool_schemas": tool_schemas,
            })
        )

        if self._index >= len(self._responses):
            raise RuntimeError("No more scripted responses available.")

        response = self._responses[self._index]
        self._index += 1
        return response

async def test_scripted_provider():
    provider = ScriptedProvider([response1, response2])
    messages = [
        Message(role="user", content="读取 text.txt 文件内容")
    ]
    first = await provider.chat(messages,[])
    print("第一次响应",first)
    messages.append(Message(role="assistant", content=first.tool_calls))
    call = first.tool_calls[0]
    result = ToolResult(tool_use_id=call.id, content="学习 asyncio", is_error=False)
    messages.append(Message(role="user", content=[result]))
    second = await provider.chat(messages,[])
    print("第二次响应",second)
    #await provider.chat(messages, []) #RuntimeError: No more scripted responses available.
    print("第一次请求的消息数",
          len(provider.requests[0]["messages"]),
          )
    print("第二次请求的消息数",
          len(provider.requests[1]["messages"]),
          )
if __name__ == "__main__":
    import asyncio
    asyncio.run(test_scripted_provider())