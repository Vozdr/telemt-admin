from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


class UserInput(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    secret: str | None = None
    limit: int = Field(default=0, ge=0, le=100000)
    comment: str = Field(default="", max_length=200)
    blocked: bool = False


class RenameInput(UserInput):
    old_name: str = Field(min_length=1, max_length=64)


class ToggleInput(BaseModel):
    blocked: bool


class SecretInput(BaseModel):
    secret: str | None = None


class ConfigSettingChange(BaseModel):
    section: str = Field(default="")
    key: str = Field(min_length=1, max_length=128)
    type: str = Field(default="unknown", max_length=128)
    action: str = Field(default="set", max_length=16)
    value: Any = None


class ConfigSettingsInput(BaseModel):
    changes: list[ConfigSettingChange] = Field(default_factory=list)


@dataclass
class UserRecord:
    name: str
    secret: str
    limit: int
    comment: str
    blocked: bool
    added_at: str
    updated_at: str
    blocked_at: str
    stats: dict[str, Any]
    link: str
    qr: str


@dataclass(frozen=True)
class ConfigSpec:
    section: str
    key: str
    kind: str
    default: Any = ""
    hot_reload: bool = False
    editable: bool = False
    choices: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return f"{self.section}.{self.key}" if self.section else self.key


def spec(section: str, key: str, kind: str, default: Any = "", hot_reload: bool = False, choices: tuple[str, ...] = ()) -> ConfigSpec:
    return ConfigSpec(section, key, kind, default, hot_reload, False, choices)
