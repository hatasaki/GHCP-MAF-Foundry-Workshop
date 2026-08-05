"""Microsoft 365 / Azure のリリース情報を Pydantic で構造化出力し JSON 保存する。

src/agent.py と同じ MRC MCP 構成を使い、直近 GA になった主要更新を取得する。
結果は data/report_<YYYYMMDD>.json に保存する。
実行: `python src/report.py`
"""

import asyncio
import os
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from agent_framework.foundry import FoundryChatClient
from agent_framework import MCPStreamableHTTPTool
from azure.identity.aio import AzureCliCredential
from dotenv import dotenv_values
from pydantic import BaseModel, Field

# Windows コンソール (cp1252/cp932) でも日本語を確実に入出力する
for _stream in (sys.stdout, sys.stderr):
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

INSTRUCTIONS = """あなたは Microsoft 365 と Azure のリリースレポートを作成する日本語アシスタントです。

- summary / title / status などの文章はすべて日本語で記述してください。
- レポートを作成する前に、必ず Microsoft Release Communications (MRC) MCP のツールを呼び出して一次情報を取得してください。
- 各 items の url にはツール結果に含まれる出典 URL を設定してください。URL を創作しないでください。
- 出力は ReleaseReport スキーマに厳密に一致する JSON のみとし、余計な文章を含めないでください。"""

QUESTION = "直近 GA になった主要な Microsoft 365 / Azure 更新を 5 件、構造化してレポートしてください。"


class ReleaseItem(BaseModel):
    """個々のリリース項目。"""

    product: str = Field(description="対象プロダクト名 (例: Microsoft 365, Azure)")
    title: str = Field(description="更新のタイトル")
    status: str = Field(description="リリース状態 (例: GA, Preview)")
    released_at: Optional[str] = Field(default=None, description="GA / リリース日 (YYYY-MM-DD 形式が望ましい)")
    url: Optional[str] = Field(default=None, description="出典となる公式 URL")
    summary: str = Field(description="更新内容の日本語要約")


class ReleaseReport(BaseModel):
    """リリースレポート全体。"""

    period: str = Field(description="レポートの対象期間 (例: 2026-07 〜 2026-08)")
    summary: str = Field(description="レポート全体の日本語サマリー")
    items: list[ReleaseItem] = Field(description="直近 GA になった主要な更新 5 件")


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
            name="MSReleaseReportAgent",
            instructions=INSTRUCTIONS,
            tools=[MCPStreamableHTTPTool(name="mrc", url=MRC_MCP_URL)],
        ) as agent:
            result = await agent.run(
                QUESTION,
                options={"response_format": ReleaseReport},
            )

    report: ReleaseReport = result.value

    out_dir = Path(__file__).resolve().parents[1] / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"report_{date.today():%Y%m%d}.json"
    out_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    print(f"期間: {report.period}")
    print(f"サマリー: {report.summary}")
    for item in report.items:
        print(f"- [{item.status}] {item.product}: {item.title} ({item.released_at}) {item.url}")
    print(f"\n保存しました: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
