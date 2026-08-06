"""Lab 3 でデプロイした Hosted Agent をターゲットに Foundry Cloud Evaluation を実行する。

ローカル PC から `azure-ai-projects` SDK で評価 run を作成し、intent_resolution 評価器で採点する。
テストデータは data/eval_inputs.json から読み込み、run 完了までポーリングして結果 URL を表示する。
実行: `python src/evaluate.py`
"""

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential
from dotenv import dotenv_values

TERMINAL_STATUSES = {"completed", "failed", "canceled"}
POLL_INTERVAL_SECONDS = 60
MAX_POLL_ATTEMPTS = 30


def load_dotenv_fill_only() -> None:
    """.env を fill-only で読み込む (Codespaces の空文字注入対策)。"""
    dotenv_path = Path(__file__).resolve().parents[1] / ".env"
    for key, value in dotenv_values(dotenv_path).items():
        if value is None:
            continue
        if not (os.getenv(key) or "").strip():
            os.environ[key] = value


def require_env(name: str) -> str:
    """必須環境変数を返す。未設定なら次に確認すべきことを添えて失敗する。"""
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(
            f"{name} が未設定または空です。.env に {name} を設定してから再実行してください。"
        )
    return value


def load_eval_inputs(path: Path) -> list[dict[str, str]]:
    """ワークショップの JSON 配列から評価入力を読み込む。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"評価データが見つかりません: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"評価データの JSON が不正です: {path}") from exc

    if not isinstance(data, list):
        raise RuntimeError(f"評価データは JSON 配列にしてください: {path}")

    inputs: list[dict[str, str]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict) or not isinstance(item.get("query"), str):
            raise RuntimeError(f"評価データ {index} 件目には文字列の query が必要です。")
        query = item["query"].strip()
        if not query:
            raise RuntimeError(f"評価データ {index} 件目の query が空です。")
        inputs.append({"query": query})

    return inputs


def build_testing_criteria(judge_model: str) -> list[dict[str, Any]]:
    """intent_resolution 評価器の定義を組み立てる。judge_model が LLM ジャッジになる。"""
    return [
        {
            "type": "azure_ai_evaluator",
            "name": "intent_resolution",
            "evaluator_name": "builtin.intent_resolution",
            "initialization_parameters": {"deployment_name": judge_model},
            "data_mapping": {
                "query": "{{item.query}}",
                "response": "{{sample.output_text}}",
            },
        }
    ]


def build_data_source(
    inputs: list[dict[str, str]], agent_name: str, agent_version: str
) -> dict[str, Any]:
    """Hosted Agent をターゲットにしたインライン評価入力ソースを組み立てる。"""
    return {
        "type": "azure_ai_target_completions",
        "source": {
            "type": "file_content",
            "content": [{"item": item} for item in inputs],
        },
        "input_messages": {
            "type": "template",
            "template": [
                {
                    "type": "message",
                    "role": "developer",
                    "content": {
                        "type": "input_text",
                        "text": "与えられた質問に出典付きで簡潔に答えてください。",
                    },
                },
                {
                    "type": "message",
                    "role": "user",
                    "content": {"type": "input_text", "text": "{{item.query}}"},
                },
            ],
        },
        "target": {
            "type": "azure_ai_agent",
            "name": agent_name,
            "version": agent_version,
        },
    }


def main() -> None:
    """Foundry Cloud Evaluation の run を作成・実行し、結果 URL を表示する。"""
    load_dotenv_fill_only()

    project_endpoint = require_env("FOUNDRY_PROJECT_ENDPOINT")
    # ジャッジは非 reasoning モデル (例: gpt-4.1-mini) を推奨。gpt-5 系は組み込み評価器が
    # temperature 等を渡すと 400 になり全行が採点不能 (0/0) になる。未設定なら FOUNDRY_MODEL に落とす。
    judge_model = (os.getenv("FOUNDRY_JUDGE_MODEL") or "").strip() or require_env("FOUNDRY_MODEL")
    agent_name = require_env("HOSTED_AGENT_NAME")
    agent_version = os.getenv("HOSTED_AGENT_VERSION", "1").strip() or "1"
    inputs = load_eval_inputs(Path("data/eval_inputs.json"))
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=AzureCliCredential(),
    )
    client = project_client.get_openai_client()

    eval_definition = client.evals.create(
        name=f"ms-updates-eval-{timestamp}",
        data_source_config={
            "type": "custom",
            "item_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "include_sample_schema": True,
        },
        testing_criteria=build_testing_criteria(judge_model),
    )
    print(f"Evaluation definition: {eval_definition.id} (judge={judge_model})")

    run = client.evals.runs.create(
        eval_id=eval_definition.id,
        name=f"run-{timestamp}",
        data_source=build_data_source(inputs, agent_name, agent_version),
    )
    print(f"Run started: {run.id}")

    final_status = "unknown"
    for _ in range(MAX_POLL_ATTEMPTS):
        status = client.evals.runs.retrieve(eval_id=eval_definition.id, run_id=run.id)
        final_status = status.status
        print(f"  status={final_status}")
        if final_status in TERMINAL_STATUSES:
            break
        time.sleep(POLL_INTERVAL_SECONDS)

    result_url = f"https://ai.azure.com/evaluation/{eval_definition.id}/runs/{run.id}"
    print(f"\nResult: {result_url}")

    if final_status != "completed":
        raise RuntimeError(
            f"Cloud Evaluation run が completed になりませんでした: {final_status}"
        )


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
