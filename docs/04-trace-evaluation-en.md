# Lab 4: Trace Inspection and Cloud Evaluation

## What you do in this Lab

- Inspect the **traces** of the Hosted Agent you deployed in Lab 3 in the Foundry portal and Application Insights
- **Targeting the Hosted Agent you deployed in Lab 3**, run an evaluation job from your own PC using the **Foundry SDK (`azure-ai-projects`)**
- Score agent quality with the built-in evaluators (`builtin.task_adherence`, `builtin.tool_call_accuracy`, `builtin.intent_resolution`, `builtin.coherence`)
- The `src/evaluate.py` you build here is **reused as is by the Lab 5 CI/CD pipeline**


---

## 4-1. View Traces in the Foundry Portal

The Hosted Agent **sends OpenTelemetry traces to Foundry by default**. You need no code changes or additional configuration.

1. Open [https://ai.azure.com](https://ai.azure.com)
2. Select the relevant project
3. Select **Build** in the top right, then in the left menu **Agents** > select the agent you created
4. The agent's chat screen opens; enter any input and wait for a response
5. Select **Traces** at the top of the agent's chat screen and select one of the displayed trace IDs

---

## 4-2. Cloud Evaluation: Evaluate the Lab 3 Hosted Agent with the SDK

Foundry's **Cloud Evaluation** runs an evaluation job on the server side and stores the results. In this Lab, you **call the `azure-ai-projects` SDK from your local PC** to create an evaluation run targeting the Hosted Agent you deployed in Lab 3. You run the same script from GitHub Actions in Lab 5.

```text
Your PC                          Foundry service
─────────────────────────────────────────────────────────────────────────────
src/evaluate.py                  ┌────────────────────────────────┐
  ├─ client.evals.create()    ─→ │ Evaluation definition          │
  └─ client.evals.runs.create() ─→ │ Run → azure_ai_agent target  │
                                 │  └→ Lab 3 Hosted Agent          │
                                 │  └→ score with builtin evaluators │
                                 └────────────────────────────────┘
```

### 4-2-1. Check the package

```bash
pip install "azure-ai-projects>=2.2.0"
```

### 4-2-2. Prepare test data

> This file is **already placed at the repository root as `data/eval_inputs.json` from the start**. Edit it only if you want to change the contents. If you want to practice writing it from scratch, you can delete it first and recreate it with the content below.

`data/eval_inputs.json` (**a normal JSON array, not JSONL**. The script expands it one item at a time):

```json
[
  { "query": "Tell me 3 Azure AI-related updates that reached GA this quarter" },
  { "query": "5 Outlook-related items from the Microsoft 365 Copilot roadmap" },
  { "query": "Features in Defender for Cloud that will be Retiring within 90 days" },
  { "query": "In the Microsoft Fabric docs, what are the best practices for Lakehouse?" }
]
```

### 4-2-3. Write the evaluation script

In Copilot Chat:

````text
Create a new src/evaluate.py.

Requirements:
- Create a Microsoft Foundry Cloud Evaluation and
  evaluate it targeting the Hosted Agent deployed in Lab 3
- The evaluator is intent_resolution
- Read the test data from data/eval_inputs.json
- Poll until the run completes, and finally display the Foundry evaluation result URL
- Read the Hosted Agent name and version from environment variables
````

Completed image:

```python
"""Run Foundry Cloud Evaluation against the Lab 3 Hosted Agent."""

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
    """Load repository .env values without overriding non-empty environment values."""
    dotenv_path = Path(__file__).resolve().parents[1] / ".env"
    for key, value in dotenv_values(dotenv_path).items():
        if value is None:
            continue
        if not (os.getenv(key) or "").strip():
            os.environ[key] = value


def require_env(name: str) -> str:
    """Return a required environment variable or fail with an actionable message."""
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is unset or empty. Set {name} in .env and re-run."
        )
    return value


def load_eval_inputs(path: Path) -> list[dict[str, str]]:
    """Load evaluation inputs from the workshop JSON array."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Evaluation data not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Evaluation data JSON is invalid: {path}") from exc

    if not isinstance(data, list):
        raise RuntimeError(f"Evaluation data must be a JSON array: {path}")

    inputs: list[dict[str, str]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict) or not isinstance(item.get("query"), str):
            raise RuntimeError(f"Evaluation data item #{index} requires a string query.")
        query = item["query"].strip()
        if not query:
            raise RuntimeError(f"Evaluation data item #{index} has an empty query.")
        inputs.append({"query": query})

    return inputs


def build_testing_criteria(model_deployment: str) -> list[dict[str, Any]]:
    """Build the intent_resolution evaluator definition for Cloud Evaluation."""
    return [
        {
            "type": "azure_ai_evaluator",
            "name": "intent_resolution",
            "evaluator_name": "builtin.intent_resolution",
            "initialization_parameters": {"deployment_name": model_deployment},
            "data_mapping": {
                "query": "{{item.query}}",
                "response": "{{sample.output_text}}",
            },
        }
    ]


def build_data_source(inputs: list[dict[str, str]], agent_name: str, agent_version: str) -> dict[str, Any]:
    """Build the Hosted Agent target and inline evaluation input source."""
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
                        "text": "Answer the given question concisely with sources.",
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
    """Create and run a Foundry Cloud Evaluation run."""
    load_dotenv_fill_only()

    project_endpoint = require_env("FOUNDRY_PROJECT_ENDPOINT")
    model_deployment = require_env("FOUNDRY_MODEL")
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
        testing_criteria=build_testing_criteria(model_deployment),
    )
    print(f"Evaluation definition: {eval_definition.id}")

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
        raise RuntimeError(f"Cloud Evaluation run did not reach completed: {final_status}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
```


### 4-2-4. Add environment variables

Append to `.env`:

```env
HOSTED_AGENT_NAME=ms-updates-agent
HOSTED_AGENT_VERSION=1
```
Change the version number to the appropriate value for your environment if needed.

### 4-2-5. Run

```bash
python src/evaluate.py
```

Completes in 5–15 minutes. Open the displayed URL to see the score per evaluator and the judgment rationale for each sample.

### 4-2-6. Check the results in the Foundry portal

1. Open [https://ai.azure.com](https://ai.azure.com)
2. Select the relevant project
3. Select **Build** in the top right, then **Evaluation** in the left menu
4. Click the name in the evaluation list
5. Click the name of the evaluation run to check the evaluation results

---

Next → [Lab 5: CI/CD with GitHub Actions](05-cicd-en.md)
