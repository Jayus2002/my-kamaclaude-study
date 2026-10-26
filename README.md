## 项目用途

## 运行目录
my-kamaclaude

## 一些命令
```
uv run my-kamaclaude --help
uv run my-kamaclaude --version
```

## Day 02：配置与日志

配置包含 `model`、`max_steps`、`workspace` 和 `data_dir`，优先级为：

```text
Config 默认值 < 显式指定的 TOML 文件 < 环境变量
```

在项目目录中使用已有示例配置：

```powershell
Set-Location D:\pro\kamaclaude\my-kamaclaude
uv run my-kamaclaude --config config.example.toml
```

示例文件的字段位于 TOML 顶层：

```toml
model = "example-model"
max_steps = 1
workspace = "."
data_dir = "./data"
```

workspace 必须已存在且为目录；data_dir 不存在时自动创建。所有相对路径均按终端当前目录解释。
不传 `--config` 时不会自动加载示例文件，默认 workspace 为 `./workspace`，需先确保该目录存在。
模型名目前只是配置值，程序尚未调用模型。

| 环境变量 | 对应字段 |
| --- | --- |
| `MY_KAMACLAUDE_MODEL` | `model` |
| `MY_KAMACLAUDE_MAX_STEPS` | `max_steps` |
| `MY_KAMACLAUDE_WORKSPACE` | `workspace` |
| `MY_KAMACLAUDE_DATA_DIR` | `data_dir` |

例如，临时覆盖模型名并在结束后恢复原来的环境变量：

```powershell
$previousModel = $env:MY_KAMACLAUDE_MODEL
try {
    $env:MY_KAMACLAUDE_MODEL = "env-model"
    uv run my-kamaclaude --config config.example.toml
}
finally {
    $env:MY_KAMACLAUDE_MODEL = $previousModel
}
```

环境变量缺失时保留文件值；当前实现不自动读取 `.env` 文件。
步数必须是正整数，模型名必须是非空字符串；配置或日志初始化错误通过 argparse 显示，退出码为 2。
`--help` 和 `--version` 在加载配置前处理。

程序向所选数据目录的 `app.log` 追加 UTF-8 编码的启动和退出日志。使用示例配置后可查看：

```powershell
Get-Content .\data\app.log
```

`/data/` 已在 `.gitignore` 中；若实验使用 `data-other/` 等其他目录，需要另外处理忽略规则，避免提交运行日志。
设计说明、已有运行证据和待验收项目见 [Day 02 学习记录](docs/journal/day-02.md)。
