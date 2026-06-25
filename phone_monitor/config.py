"""配置管理 — 从环境变量加载所有配置"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # ── 搜索配置 ──
    tavily_api_key: str = ""
    brands: list[str] = field(default_factory=lambda: ["OPPO", "vivo", "华为", "iPhone"])

    # ── LLM 配置（支持 OpenAI 兼容接口：OpenAI / DeepSeek / 通义千问） ──
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"  # 默认 DeepSeek
    llm_model: str = "deepseek-chat"
    # 备选示例：
    #   OpenAI:     https://api.openai.com/v1          | gpt-4o-mini
    #   通义千问:    https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-turbo

    # ── 飞书推送配置 ──
    feishu_webhook_url: str = ""

    # ── 运行模式 ──
    dry_run: bool = False  # True = 只打印结果，不推送飞书

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量 + .env 文件加载配置"""
        # 尝试加载 .env 文件
        _try_load_dotenv()

        return cls(
            tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1"),
            llm_model=os.getenv("LLM_MODEL", "deepseek-chat"),
            feishu_webhook_url=os.getenv("FEISHU_WEBHOOK_URL", ""),
            dry_run=os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes"),
            brands=_parse_brands(os.getenv("BRANDS", "OPPO,vivo,华为,iPhone")),
        )

    def validate(self) -> list[str]:
        """检查必要配置是否齐全，返回缺失项列表"""
        missing = []
        if not self.tavily_api_key:
            missing.append("TAVILY_API_KEY")
        if not self.llm_api_key:
            missing.append("LLM_API_KEY")
        if not self.feishu_webhook_url and not self.dry_run:
            missing.append("FEISHU_WEBHOOK_URL（或启用 DRY_RUN=true）")
        return missing


def _try_load_dotenv() -> None:
    """尝试加载 .env 文件（轻量实现，无第三方依赖）"""
    import os
    import pathlib

    env_path = pathlib.Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("\"'")
            if key not in os.environ:  # 不覆盖已设置的环境变量
                os.environ[key] = value


def _parse_brands(raw: str) -> list[str]:
    """解析逗号分隔的品牌列表"""
    return [b.strip() for b in raw.split(",") if b.strip()]
