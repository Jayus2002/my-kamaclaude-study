# Day 03：消息类型与假 Provider

整理日期：2026-10-28。

本记录依据当前源码、学习过程及学习者的回答整理。学习者已反馈“已测试”，但尚未收录终端完整输出；下文的预期输出来自代码推导。本次整理未运行程序，也未代为确认验收完成。

## 今日行为要求

- 定义 `ToolCall`、`ToolResult`、`Message`、`LlmResponse`，表达工具调用、工具结果、消息历史和模型响应。
- 用 `stop_reason` 区分请求工具与结束本轮回复。
- 实现异步 `ScriptedProvider.chat()`，依次返回预设响应，并保存每次请求的输入快照。
- 不访问模型服务、不使用模型密钥，演示两次调用与脚本耗尽。
- 手动回填工具结果，整理完整请求与响应示例；真正的文件读取留到 Day 04。

## 参考提交与源码对照

参考基线 M：`cdb2070e522b5b3493548c87e54999c9c749d707`。本次只读核对的 `reference-main` HEAD 与其一致，未运行参考项目。

| 参考文件（相对 reference-main） | 关键入口与源码证据 |
| --- | --- |
| `src/kama_claude/core/llm/base.py` | `LLMProvider` 用 Protocol 声明异步 chat，接收 messages、tool_schemas、bus、run_id 等，返回 LlmResponse |
| `src/kama_claude/core/llm/types.py` | 定义 ToolCallBlock、LlmResponse、UsageStats；响应包含停止原因、文本、工具调用及额外字段 |
| `tests/unit/test_loop.py` | `_MockProvider` 用 iter(responses) 与 next() 顺序返回预设响应，供 Loop 测试使用 |
| `src/kama_claude/core/context.py` | add_assistant_message 保存模型内容；add_tool_result 把结果块放入 user 消息并关联调用 ID |

本日分类：**对齐＋简化**。对齐异步接口、结构化响应与脚本驱动的思路；暂不接入真实模型、事件、流式响应或上游全部字段。

## 当前设计及原因

实现文件：`src/my_kamaclaude/llm/types.py` 与 `src/my_kamaclaude/llm/scripted.py`。

### 四个 dataclass 的职责

| 类型 | 字段 | 设计理由 |
| --- | --- | --- |
| ToolCall | `id: str` | 标识一次调用；同名工具可能调用多次，不能仅靠工具名配对结果 |
| ToolCall | `name: str` | 标明希望执行的工具，如 read_text |
| ToolCall | `input: dict[str, object]` | 参数名为字符串，值可以是文本、整数、布尔值等，例如 `{"path": "text.txt"}` |
| ToolResult | `tool_use_id: str` | 对应 ToolCall.id，说明结果属于哪次调用 |
| ToolResult | `content: str` | 当前用文本承载执行结果或错误说明，方便回填模型 |
| ToolResult | `is_error: bool = False` | 明确是否失败，避免根据结果文字猜测状态 |
| Message | `role: str` | 标记消息角色；当前沿参考实现约定，程序生成的工具结果放在 user 消息里 |
| Message | `content: str \| list[ToolCall \| ToolResult]` | 普通消息用文本，工具交互用结构化列表；列表可以容纳多个调用或结果 |
| LlmResponse | `stop_reason: Literal["tool_use", "end_turn"]` | 必须明确本次生成为什么停止，供调用方决定执行工具还是结束本轮 |
| LlmResponse | `text: str = ""` | 无文字时仍为字符串，不必额外判断 None |
| LlmResponse | `tool_calls: list[ToolCall] = field(default_factory=list)` | 无调用时为空列表；工厂为每个响应创建独立列表 |

调用与结果分开，是因为模型提出调用时，工具尚未执行。响应与历史消息分开，是因为 LlmResponse 是一次调用的返回值，Message 是后续请求使用的对话记录。

dataclass 自动生成初始化、打印表示和相等比较，适合承载这些数据。类型注解和 Literal 不会自动校验运行时输入，外部数据及工具参数仍需在后续边界显式检查。无默认值的字段必须排在有默认值的字段之前。

### 为什么设计统一的 Provider

```python
response = await provider.chat(messages, tool_schemas)
```

调用方提供消息历史与工具说明，接收统一的 LlmResponse。具体 Provider 决定响应从哪里来：假 Provider 从预设列表取值，未来的真实 Provider 请求模型服务。

原草稿把这一点类比为 Day 02 中环境变量到配置字段的映射。相似之处是统一外部表示；需要区分：**dataclass 定义内部结构，适配器代码执行字段转换**。dataclass 不会自动转换不同供应商的数据。

供应商可能使用不同字段名、嵌套结构，甚至将工具参数编码为 JSON 字符串。将差异放在适配层后，调用方持续使用 call.name、call.input 等内部字段，避免各模块分别处理供应商格式。当前尚未实现真实适配器或通用 Provider Protocol。

### ScriptedProvider 的状态与调用顺序

- `_responses`：创建实例时深拷贝的预设响应列表，是多次调用的脚本。
- `_index`：下一次返回的位置，初始为 0。
- `requests`：每次调用收到的 messages 与 tool_schemas 的深拷贝快照。

每次 chat：记录请求 → 检查是否耗尽 → 取当前响应 → 索引加一 → 返回一个 LlmResponse。

初始化传入 `[response1, response2]`，表示第一次返回 response1、第二次返回 response2，每次仍只有一个响应。耗尽时抛出 `RuntimeError("No more scripted responses available.")`。

记录请求在耗尽检查之前，因此第三次失败调用也会记录；若调用三次，requests 长度为 3，但只有两个响应成功返回。

deepcopy 保留调用当时的输入，后续追加或修改 messages 不会改变此前快照。历史由调用方维护，Provider 不自动追加 assistant 消息或工具结果。

使用 async def 是为了保持未来网络调用的使用方式；当前内部没有 await，调用方仍须 await chat 才会执行方法并取得响应。

## 完整请求与响应示例

以下用 Python 对象表达当前示例的完整数据，依据源码整理，不是已采集的运行输出。这里的“学习 asyncio”为手动构造的工具结果，没有真正读取文件。

```python
# 第一次请求
messages = [Message(role="user", content="读取 text.txt 文件内容")]
tool_schemas = []

# 第一次响应
first = LlmResponse(
    stop_reason="tool_use",
    text="",
    tool_calls=[
        ToolCall(
            id="tool_use_1",
            name="read_text",
            input={"path": "text.txt"},
        )
    ],
)

# 第二次请求：原始请求 + 模型提出的工具调用 + 对应结果
messages = [
    Message(role="user", content="读取 text.txt 文件内容"),
    Message(role="assistant", content=first.tool_calls),
    Message(
        role="user",
        content=[
            ToolResult(
                tool_use_id="tool_use_1",
                content="学习 asyncio",
                is_error=False,
            )
        ],
    ),
]
tool_schemas = []

# 第二次响应
second = LlmResponse(
    stop_reason="end_turn",
    text="This is a test response.",
    tool_calls=[],
)
```

当前工具说明为空，假 Provider 仍按预设脚本返回工具调用，不检查工具是否可用，也不根据消息生成新答案。工具调用和结果通过 `tool_use_1` 配对，保留执行意图、参数与结果之间的关系。

## 运行命令与结果

```powershell
Set-Location D:\pro\kamaclaude\my-kamaclaude
uv run python -m my_kamaclaude.llm.scripted
```

使用 -m 按包模块运行，可以解析 `from .types import ...`。模块入口用 asyncio.run 执行异步示例，普通导入不会触发入口。

| 项目 | 当前证据 |
| --- | --- |
| 两次预设响应与耗尽实验 | 学习者在学习过程中反馈“已测试”，尚未附终端原文 |
| 回填后的请求快照 | 当前源码包含两次请求及消息数打印；预期分别为 1、3，待收录实际输出 |
| 无模型网络请求、无密钥 | 当前 Provider 只有内存操作，没有模型客户端或网络调用；uv 环境准备是否需要网络另论 |
| 脚本耗尽 | 当前第三次调用已注释，旁边保留异常说明；默认运行不会触发此分支 |

代码推导的预期输出结构：

```text
第一次响应 LlmResponse(stop_reason='tool_use', ...)
第二次响应 LlmResponse(stop_reason='end_turn', ...)
第一次请求的消息数 1
第二次请求的消息数 3
```

省略号为记录中的简写，程序会打印完整字段。复现耗尽实验时，可临时取消第三次调用的注释；当前未捕获异常，该调用之后的打印不会执行。

**实际终端输出：待学习者补充或确认。**

## 失败点与定位过程

以下是学习过程中的代码检查发现，未逐项收录实际报错，不将推导错误写成已采集的运行日志。

| 早期问题 | 原因与修正 |
| --- | --- |
| 构造响应缺少 stop_reason | 缺失必填字段会导致 TypeError；分别补 tool_use、end_turn |
| tool_calls 接收单个 ToolCall | 字段应为列表，改为 `[ToolCall(...)]` |
| input 是文件名字符串 | 参数应为字典，改为 `{"path": "text.txt"}`；dataclass 自身不拦截类型不匹配 |
| `requests.append({deepcopy({...})})` | 外层大括号创建集合，字典不能作为集合元素，会导致 unhashable type: dict；去掉多余大括号 |
| 只定义异步示例函数 | 函数不会自动执行；增加模块入口和 asyncio.run |
| 两次调用间没有追加历史 | 假脚本仍返回第二个响应，但请求缺少交互依据；补入调用与结果 |

## 理解问题与回答

### 学习者已作出的回答

**把 response2.text 改成“你好”，第二次调用会返回什么？**

学习者回答：“返回你好，因为这是预设的返回结果。”

代码层面的补充：应在创建 Provider 前修改预设响应；创建实例时已 deepcopy，之后修改外部 response2 不会改变该实例的脚本。

**删除回填工具结果后，是否仍会返回 response2？**

学习者回答：“依旧会，假的 provider 只能验证流程正确，不能验证工具调用对于返回的影响。”

进一步明确：假 Provider 提供可控响应，要配合检查请求快照和程序行为才能验证流程；它不会自行判定流程正确，也不能证明真实模型会正确使用工具结果。

### 计划中的理解问题：整理说明，待自己复述确认

**模型请求和响应分别携带什么？** 请求包含历史消息与工具说明；当前响应包含文本、工具调用和停止原因。调用方将模型内容及工具结果追加到历史，再发起下一次请求。

**为什么供应商格式在适配器里转换？** 内部类型表达程序需要的数据，适配器处理供应商差异，让执行逻辑不用分别处理各种字段和解析方式。当前假 Provider 直接返回内部对象，真实转换尚未实现。

**为什么停止原因必填？** 是否输出文字不能可靠决定下一步，模型可能同时输出说明与工具请求。tool_use 表示等待工具，end_turn 表示本轮回复结束；步数限制、取消等 Agent 终止原因由后续运行逻辑另外管理。

## 与参考实现的差异及限制

| 项目 | 本日实现与差异原因 |
| --- | --- |
| Provider 接口 | 只有具体的 ScriptedProvider.chat，省略 Protocol、事件总线、run_id 等，先学习最小交互 |
| 耗尽处理 | 自己显式抛 RuntimeError；所读上游 _MockProvider 直接 next，没有转换成同样的耗尽错误 |
| 请求记录 | 自己增加 deepcopy 快照，便于检查历史变化；所读上游 _MockProvider 没有请求记录 |
| 消息表示 | 自己用 Message、ToolResult dataclass；参考调用链使用字典和内容块，尚不能直接对接其 Provider |
| 响应字段 | 省略 usage、缓存统计和 thinking_blocks，按本日最小范围实现 |
| 混合内容 | Message.content 当前为文本或工具块列表，尚不能在同一条消息中同时保存文本和工具块；当前 response1 无文本，后续扩展时需留意完整保留 |
| 类型约束 | role 为任意字符串，Literal 也不执行运行时校验；尚未校验角色、停止原因与内容组合是否合法 |
| 执行能力 | 结果为手动构造，没有真实模型、文件读取、工具派发或自动 Agent Loop |

## 未完成项与下一步

- 由学习者补充两次响应、1/3 条消息快照及耗尽异常的实际终端输出，并确认验收结果。
- 由学习者复述请求与响应、适配器转换两个理解问题；整理说明不代替独立回答。
- 预设响应仍在 types.py，调用示例仍在 scripted.py，以后可按需要移到独立示例或测试文件，本日不为此重构。
- Day 04 实现 workspace 内的真实只读工具；Day 05 再连接自动循环。

## 对应提交

待学习者提交。本次整理时 day-03.md 与 llm 目录仍为未跟踪文件；未创建 Git 提交，也未勾选 DAILY_PLAN.md。
