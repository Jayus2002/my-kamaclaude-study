from dataclasses import dataclass, field
from typing import Literal
@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, object]

@dataclass
class ToolResult:
    tool_use_id: str
    content: str
    is_error: bool = False

@dataclass
class Message:
    role: str
    content: str|list[ToolCall|ToolResult]

@dataclass
class LlmResponse:
    stop_reason: Literal["tool_use", "end_turn"]
    text: str=""
    tool_calls: list[ToolCall] = field(default_factory=list)
    

message1 = Message(role="user", content="读取 text.txt 文件内容")

response1 = LlmResponse(
    stop_reason="tool_use",
    tool_calls=[
        ToolCall(id="tool_use_1",
                name="read_text",
                input={"path":"text.txt"}),
    ]
)


response2 = LlmResponse(
    stop_reason="end_turn",
    text="This is a test response."
)
