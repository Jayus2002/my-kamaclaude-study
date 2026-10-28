# Day 02：配置、日志与数据边界

整理日期：2026-10-26。


## 今日行为要求

- 集中声明模型名、最大步数、workspace 和 data_dir。
- 实现默认值 → TOML 配置文件 → 环境变量的覆盖顺序。
- 检查配置类型、数值和路径，出错时给出明确提示。
- 将启动与退出日志写入各自的数据目录，不记录密钥。

## 当前设计及原因

### 配置对象与校验

`src/my_kamaclaude/config.py` 中的 `Config` 使用 `@dataclass`：

| 字段 | 默认值 | 规则与职责 |
| --- | --- | --- |
| `model` | `"gpt-4"` | 必须是非空字符串；目前只保存名称，不调用模型 |
| `max_steps` | `10` | 必须是正整数，不接受布尔值 |
| `workspace` | `Path("workspace")` | 工具工作区配置，必须是已存在的目录 |
| `data_dir` | `Path("data")` | 日志等运行数据目录，不存在时创建 |

`__post_init__()` 在字段赋值后执行校验。两个路径均通过 `Path(...).expanduser().resolve()` 规范化。
当前约定所有配置中的相对路径按终端当前工作目录解释，而不是按 TOML 文件所在目录解释。
`resolve()` 不负责创建目录，存在性和目录类型需要另外检查。
目前只定义和检查 workspace，尚未实现工具的文件访问边界。

### 配置加载与覆盖

`load_config_from_toml()` 用二进制模式打开文件，由标准库 `tomllib` 返回字典。
配置字段直接放在 TOML 顶层。`load_config_from_env()` 只收集实际存在的环境变量：

| 环境变量 | 配置字段 |
| --- | --- |
| `MY_KAMACLAUDE_MODEL` | `model` |
| `MY_KAMACLAUDE_MAX_STEPS` | `max_steps` |
| `MY_KAMACLAUDE_WORKSPACE` | `workspace` |
| `MY_KAMACLAUDE_DATA_DIR` | `data_dir` |

环境变量是字符串，因此步数先通过 `int()` 转换；非整数给出明确错误。
当前代码读取进程环境变量，不自动读取 `.env` 文件。

`load_config()` 先合并文件字段，再合并环境变量，最后只创建一次 `Config(**values)`。
后一次 `dict.update()` 覆盖同名键；没有传入的字段使用 dataclass 默认值。
环境变量缺失时不填默认值，避免把文件中设置的值意外覆盖掉。

### 命令入口与日志

```text
解析参数
→ 按 --config 加载配置并校验
→ setup_logging(config.data_dir)
→ 记录启动
→ 打印最终配置及消息或时间
→ finally 中记录退出
```

`--config` 通过 `type=Path` 接收路径。不指定时使用默认值和环境变量，不自动寻找配置文件。
`--help`、`--version` 在参数解析时退出，不依赖配置加载成功。
启动过程中的 `OSError`、`ValueError`、`TypeError` 由 `parser.error()` 转成提示，按 argparse 行为退出码为 2。

`logging_setup.py` 使用 `logging.basicConfig()`，以 UTF-8 编码、INFO 级别向 `data_dir/app.log` 追加日志。
当前日志只记录启动和退出两条固定消息；退出记录不代表业务一定成功，强制结束进程时也不能保证执行 `finally`。

## 可复现命令与已有证据

当前 `config.example.toml` 的内容是：

```toml
model = "example-model"
max_steps = 1
workspace = "."
data_dir = "./data"
```

学习者可在 PowerShell 中复现：

```powershell
Set-Location D:\pro\kamaclaude\my-kamaclaude
uv run my-kamaclaude --config config.example.toml
Get-Content .\data\app.log
```

预期最终配置使用文件值，workspace 与 data_dir 显示为绝对路径；这是根据代码推导的预期，本次未采集终端实际输出。

本次只读检查发现两个已有日志文件，均包含以下真实内容的片段：

```text
INFO - Starting my-kamaclaude application
INFO - Exiting my-kamaclaude application
```

- `data/app.log` 最近一组记录时间为 `2026-10-26 21:38:38`。
- `data-other/app.log` 最近一组记录时间为 `2026-10-26 21:40:11`。

这些内容说明两个目录已有启动和退出记录，但没有逐次运行前后的文件对比，因此不能单凭现有片段确认完整日志隔离验收通过。

## 失败实验与定位过程

用户曾运行程序并得到：

```text
my-kamaclaude: error: Error loading configuration: Unrecognised argument(s): encoder
```

定位发现 `logging.basicConfig()` 中把 `encoding="utf-8"` 写成了 `encoder="utf-8"`。
当前源码已经改为 `encoding`，用户反馈修改完成，且已有日志记录可见。

错误前缀 `Error loading configuration` 来自入口的异常处理：同一个 try 同时包含配置加载和日志初始化，
所以日志初始化异常也被包装为配置错误。后续可考虑更准确的启动错误提示。

## 理解问题的参考解释（待自己复述）

**为什么配置不能散落在各模块？** 集中配置能统一默认值、来源优先级和校验规则，避免不同模块各读一套环境变量，得到不一致的运行参数。

**为什么最后才创建一次 Config？** 先得到最终覆盖结果，再统一检查；避免中间配置尚未覆盖完就失败，也避免反复触发目录创建。

**为什么三种目录要分开？** 当前工作目录是相对路径的解释起点；workspace 是预定的工具访问范围；data_dir 用于保存程序自己的运行数据。
切换终端位置不应被误认为授予工具新的访问权限，也不应把运行日志随意混入待处理材料。

**为什么 workspace 不自动创建，而 data_dir 可以？** workspace 不存在通常表示输入路径有误，应及时提示；data_dir 是程序输出位置，首次启动时允许创建。
**为什么使用env_name, field_name in env_fields.items()读取环境变量?** 1方便pydantic 映射 2解耦代码
## 验收

| 项目 | 当前证据 / 待补内容 |
| --- | --- |
| 文件配置改变输出 | 加载与打印代码已具备；待补实际输出 |
| 环境变量覆盖文件 | 合并顺序已实现；待实际运行确认 |
| 非法步数：0、负数、非整数、布尔值 | 校验逻辑已实现；待记录错误消息与退出码 |
| workspace 不存在或为文件 | 检查逻辑已实现；待记录实际错误 |
| 两个 data_dir 日志互不混合 | 两份日志已存在；待对比逐次运行前后变化 |
| 帮助和版本独立于非法配置 | 参数解析先于配置加载；待实际运行确认 |
| 提交内容不包含运行日志 | `git status --short` 显示 `data-other/` 尚未忽略；提交前自行处理 |

当前 `.gitignore` 只忽略 `/data/`，不会自动忽略 `/data-other/`。本次未修改忽略规则。
下一步先补齐上述验收证据和自己的理解回答，再确认 Day 02 是否完成。

## 与参考实现的差异

本日记录依据自己项目的实现，使用标准库 dataclasses、tomllib、pathlib、argparse 和 logging；本次未对照上游配置源码。
当前没有 daemon、模型调用或工具执行，不要求复制参考项目的完整配置系统。

## 对应提交

已提交
