"""Harness to run the challenge's judge_simulator.py against the local bot."""
from __future__ import annotations
import os
import sys
import threading
import time
from pathlib import Path
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
CHALLENGE_DIR = ROOT.parent / "magicpin-ai-challenge"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(CHALLENGE_DIR))


def start_server(port: int = 8080) -> uvicorn.Server:
    from bot import app
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(30):
        time.sleep(0.1)
        if server.started:
            break
    return server


def run(scenario: str = "all", port: int = 8080) -> bool:
    server = start_server(port)
    try:
        import judge_simulator

        # Override config
        judge_simulator.BOT_URL = f"http://127.0.0.1:{port}"
        judge_simulator.TEST_SCENARIO = scenario

        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

        if anthropic_key:
            llm = judge_simulator.AnthropicProvider(anthropic_key, "claude-3-5-sonnet-20241022")
        elif gemini_key:
            llm = judge_simulator.GeminiProvider(gemini_key, "gemini-3.8-flash")
        else:
            class DummyProvider(judge_simulator.LLMProvider):
                def name(self) -> str:
                    return "Deterministic Mock Judge (Scoring disabled without API key)"
                def complete(self, prompt: str, system: str = None) -> str:
                    return "{}"
            llm = DummyProvider()

        judge = judge_simulator.JudgeSimulator(llm)
        success = judge.run(scenario)
        return success
    finally:
        server.should_exit = True


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    scenario_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = run(scenario_arg)
    sys.exit(0 if res else 1)
