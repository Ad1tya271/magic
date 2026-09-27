"""Runtime settings, read once from the environment.

``settings`` is a process-wide mutable singleton: other modules keep a reference to it, so
``reload_settings()`` updates it in place instead of rebinding the name.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field, fields

DEFAULT_MODEL = "claude-opus-4-7"

APPROACH = (
    "4-context composer on Claude (category, merchant, trigger, customer) with digest retrieval "
    "and a derived, verified fact sheet; prompt dispatch by trigger.kind; post-LLM validation "
    "(URLs, taboos, number provenance, jargon, repetition) with one repair round; deterministic "
    "per-kind fallback composer; rule-first multi-turn conversation policy (auto-reply, opt-out, "
    "intent transition) with LLM answers inside a hard latency budget"
)


def _env_bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(env: Mapping[str, str], name: str, default: float) -> float:
    try:
        return float(env.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(env: Mapping[str, str], name: str, default: int) -> int:
    try:
        return int(env.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_list(env: Mapping[str, str], name: str, default: list[str]) -> list[str]:
    raw = env.get(name)
    if not raw:
        return list(default)
    return [part.strip() for part in raw.split(",") if part.strip()]


@dataclass
class Settings:
    model: str = DEFAULT_MODEL
    effort: str = "medium"
    llm_enabled: bool = False
    tick_budget_s: float = 9.0
    reply_budget_s: float = 8.0
    compose_budget_s: float = 25.0
    max_tokens: int = 1500
    strict_expiry: bool = False
    default_now: str = "2026-04-26T10:00:00Z"
    max_actions_per_tick: int = 20
    precompute: bool = True
    precompute_concurrency: int = 4
    team_name: str = "Team Vera"
    team_members: list[str] = field(default_factory=lambda: ["Vera Bot Team"])
    contact_email: str = "vera-team@example.com"
    version: str = "1.0.0"
    submitted_at: str = "2026-09-27T00:00:00Z"
    approach: str = APPROACH
    prompt_version: str = "composer_v1"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        has_credentials = bool(env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN"))
        defaults = cls()
        return cls(
            model=env.get("VERA_MODEL") or DEFAULT_MODEL,
            effort=env.get("VERA_EFFORT") or defaults.effort,
            llm_enabled=has_credentials and env.get("VERA_DISABLE_LLM") != "1",
            tick_budget_s=_env_float(env, "VERA_TICK_BUDGET_S", defaults.tick_budget_s),
            reply_budget_s=_env_float(env, "VERA_REPLY_BUDGET_S", defaults.reply_budget_s),
            compose_budget_s=_env_float(env, "VERA_COMPOSE_BUDGET_S", defaults.compose_budget_s),
            max_tokens=_env_int(env, "VERA_MAX_TOKENS", defaults.max_tokens),
            strict_expiry=env.get("VERA_STRICT_EXPIRY") == "1",
            default_now=env.get("VERA_DEFAULT_NOW") or defaults.default_now,
            max_actions_per_tick=_env_int(env, "VERA_MAX_ACTIONS_PER_TICK", defaults.max_actions_per_tick),
            precompute=_env_bool(env, "VERA_PRECOMPUTE", defaults.precompute),
            precompute_concurrency=max(1, _env_int(env, "VERA_PRECOMPUTE_CONCURRENCY",
                                                   defaults.precompute_concurrency)),
            team_name=env.get("VERA_TEAM_NAME") or defaults.team_name,
            team_members=_env_list(env, "VERA_TEAM_MEMBERS", defaults.team_members),
            contact_email=env.get("VERA_CONTACT_EMAIL") or defaults.contact_email,
            version=env.get("VERA_VERSION") or defaults.version,
            submitted_at=env.get("VERA_SUBMITTED_AT") or defaults.submitted_at,
            approach=env.get("VERA_APPROACH") or defaults.approach,
            prompt_version=env.get("VERA_PROMPT_VERSION") or defaults.prompt_version,
        )


settings = Settings.from_env()


def reload_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Re-read the environment into the existing ``settings`` object and return it."""
    fresh = Settings.from_env(env)
    for f in fields(Settings):
        setattr(settings, f.name, getattr(fresh, f.name))
    return settings
