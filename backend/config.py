"""全局配置：从 .env 读取，统一通过 settings 暴露。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = "sk-stub"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    use_llm: bool = False
    max_plan_iterations: int = 3
    max_revision_rounds: int = 5

    # 搜索轮次上限（Reflect Loop 硬限制）
    max_search_rounds: int = 2
    # 提前停止：候选 POI 数达到即停
    early_stop_poi_count: int = 15
    # 提前停止：候选方案数达到即停
    early_stop_plan_count: int = 10


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
