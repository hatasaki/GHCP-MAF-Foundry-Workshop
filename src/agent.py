"""MSUpdatesAgent: Microsoft 365 / Azure の最新リリース情報を日本語で回答する対話 CLI。

Microsoft Release Communications (MRC) MCP と連携し、回答には必ず出典 URL を添える。
同一 session を使い回して文脈を保持し、応答はストリーミングで逐次表示する。
実行: `python src/agent.py` (quit / exit / 終了 で終了)
"""

import asyncio
import os
import sys
from pathlib import Path

from agent_framework import Agent, AgentSession, MCPStreamableHTTPTool
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import AzureCliCredential
from dotenv import dotenv_values

# Windows コンソール (cp1252/cp932) でも日本語を確実に入出力する
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


# --- .env を fill-only で読み込む (Codespaces の空文字注入対策) ---
for _k, _v in dotenv_values(Path(__file__).resolve().parents[1] / ".env").items():
    if _v is not None and not (os.getenv(_k) or "").strip():
        os.environ[_k] = _v


def _require_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(
            f"Required environment variable is missing or empty: {name}. "
            "Set it via .env / export / Codespaces secrets and try again."
        )
    return value


MRC_MCP_URL = "https://www.microsoft.com/releasecommunications/mcp"

INSTRUCTIONS = """あなたは Microsoft 365 と Azure の最新リリース情報を回答する日本語アシスタントです。

- 回答は必ず日本語で行ってください。
- 情報を答える前に、必ず Microsoft Release Communications (MRC) MCP のツールを呼び出して一次情報を取得してください。
- ツールの結果に含まれる出典 URL を回答に必ず明記してください。
- ツール結果に該当情報や URL が無い場合は、その旨を正直に伝え、URL を創作しないでください。
- MCP で取得した一次情報に加えて、補足や関連ブログを探すときは Web 検索を使ってよいです。"""

def _conversation_id(session: AgentSession) -> str:
    """Foundry の会話スレッド ID (無ければローカル session_id) を短縮表示用に返す。"""
    raw = getattr(session, "service_session_id", None) or session.session_id
    return raw[:8]


async def _chat_loop(agent: Agent) -> None:
    session = agent.create_session()  # このループ内で使い回して文脈を保持
    print("MSUpdatesAgent です。質問をどうぞ (quit / exit / 終了 で終了)")

    while True:
        try:
            user_input = input("\nあなた: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_input.lower() in {"quit", "exit", "終了"}:
            break
        if not user_input:
            continue

        print(f"[conv:{_conversation_id(session)}] エージェント: ", end="", flush=True)
        async for update in agent.run(user_input, stream=True, session=session):
            delta = getattr(update, "text", None) or getattr(update, "content", None) or ""
            if delta:
                print(delta, end="", flush=True)
        print()


async def main() -> None:
    project_endpoint = _require_env("FOUNDRY_PROJECT_ENDPOINT")
    model = _require_env("FOUNDRY_MODEL")

    async with AzureCliCredential() as credential:
        client = FoundryChatClient(
            project_endpoint=project_endpoint,
            model=model,
            credential=credential,
        )
        async with client.as_agent(
            name="MSUpdatesAgent",
            instructions=INSTRUCTIONS,
            tools=[
                MCPStreamableHTTPTool(name="mrc", url=MRC_MCP_URL),
                client.get_web_search_tool(),
            ],
        ) as agent:
            await _chat_loop(agent)


if __name__ == "__main__":
    asyncio.run(main())
