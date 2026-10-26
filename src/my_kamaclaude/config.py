from dataclasses import dataclass
from pathlib import Path
import tomllib,os
@dataclass
class Config():
    model: str="gpt-4"
    max_steps: int=10
    workspace: Path=Path("workspace")
    data_dir: Path=Path("data")

    def __post_init__(self):
        if not isinstance(self.model, str):
            raise ValueError("model must be a string.")
        if self.model.strip() == "":
            raise ValueError("model cannot be empty.")
        if type(self.max_steps) is not int or self.max_steps <= 0:
            raise ValueError("max_steps must be a positive integer.")
        
        self.workspace = Path(self.workspace).expanduser().resolve()
        if not self.workspace.exists():
            raise ValueError(f"Workspace directory '{self.workspace}' does not exist.")
        if not self.workspace.is_dir():
            raise ValueError(f"Workspace directory '{self.workspace}' is not a directory.")
        self.data_dir = Path(self.data_dir).expanduser().resolve()
        if not self.data_dir.exists():
            Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        if not self.data_dir.is_dir():
            raise ValueError(f"Data directory '{self.data_dir}' is not a directory.")
        
def load_config_from_toml(toml_file: Path) -> dict:
    with Path(toml_file).open("rb") as f:
        return tomllib.load(f)

def load_config_from_env() -> dict:
    values = {}

    env_fields = {
        "MY_KAMACLAUDE_MODEL": "model",
        "MY_KAMACLAUDE_MAX_STEPS": "max_steps",
        "MY_KAMACLAUDE_WORKSPACE": "workspace",
        "MY_KAMACLAUDE_DATA_DIR": "data_dir",
    }

    for env_name, field_name in env_fields.items():
        value = os.getenv(env_name)
        if value is not None:
            values[field_name] = value

    if "max_steps" in values:
        try:
            values["max_steps"] = int(values["max_steps"])
        except ValueError:
            raise ValueError(
                "MY_KAMACLAUDE_MAX_STEPS 必须是整数"
            ) from None

    return values

def load_config(toml_file: Path | None = None) -> Config:
    values = {}

    if toml_file is not None:
        values.update(load_config_from_toml(toml_file))

    values.update(load_config_from_env())

    return Config(**values)