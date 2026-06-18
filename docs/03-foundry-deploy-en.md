# Lab 3: Deploy the Hosted Agent to Foundry

## What you do in this Lab

- Deploy the MAF agent you built in Lab 2 as a **Foundry Hosted Agent**
- Scaffold a source-code deployment project with `azd ai agent init --deploy-mode code` (no container needed)
- Run provision + deploy with a single `azd up` command
- Verify operation after deployment (`azd ai agent run` / `azd ai agent invoke` / the Foundry portal Playground)
- Check logs and traces

> This Lab assumes that **in [Lab 0](00-setup-en.md) you created a Foundry project and the gpt-4.1-mini model, and you have been granted the Foundry Project Manager role**. If you have not finished, go back to Lab 0.

## Architecture

```text
Your code                                      Foundry
─────────────                                 ──────────
main.py                                       ┌─────────────┐
  ResponsesHostServer(agent).run()  ── zip ──▶ Hosted     │
                                              │  Agent      │
agent.manifest.yaml                           │  (managed)  │
azure.yaml                                    └─────────────┘
requirements.txt                                    │
                                                    ▼
                                            ┌────────────────┐
                                            │ Responses API  │
                                            │ + Playground   │
                                            │ + Tracing      │
                                            └────────────────┘
```

`azd ai agent init --deploy-mode code` generates `main.py` / `agent.manifest.yaml` / `azure.yaml` / `requirements.txt` from templates. You only need to **replace the contents of `main.py` with the Lab 2 logic**, and the source code is deployed to Foundry as is (no Docker needed).

---

## 3-1. Pre-checks

### Are the Lab 0 prerequisites in place?

```bash
azd version                       # 1.25.3 or higher (required for source-code deploy)
# If nothing is shown, install azd fresh
# If the version is old, upgrade it
azd ext list                      # azure.ai.agents must appear
# If it does not appear, run azd extension install azure.ai.agents
# If the version is old, run azd extension upgrade azure.ai.agents
az account show
```

### Check the contents of `.env`

**PowerShell**

```pwsh
Get-Content .env | Select-String "FOUNDRY_PROJECT_ENDPOINT|FOUNDRY_MODEL"
```

**Bash**

```bash
grep -E "FOUNDRY_PROJECT_ENDPOINT|FOUNDRY_MODEL" .env
```

---

## 3-2. Scaffold with `azd ai agent init` (source-code deploy)

Create an **`agent/`** subdirectory at the repository root and expand the template inside it (to keep it separate from the Lab 2 `src/`).

```bash
mkdir agent
cd agent
azd ai agent init --deploy-mode code --runtime python_3_13 --entry-point main.py
```

> **`--deploy-mode code` is important.** This switches to source-code deploy mode, which needs no Docker (`main.py` + `requirements.txt` are zipped as is and hosted on the Foundry service side). Container image builds and ACR are not needed, and deployment time is greatly reduced (roughly 1–2 minutes). If you get an error that `--deploy-mode` is invalid, your `azure.ai.agents` version may be old; run `azd extension upgrade azure.ai.agents` to update it.

Answer the interactive questions (the example answers follow the official Quickstart):

| # | Question | Answer |
|---|---|---|
| 1 | Language | **Python** |
| 2 | Starter template | **Basic agent (Responses, Agent Framework, Python)** |
| 3 | Agent name | **`ms-updates-agent`** |
| 4 | Deployment type | **Code deploy** (already specified by `--deploy-mode code` above) |
| 5 | Runtime | **Python 3.13** (already specified by `--runtime python_3_13` above) |
| 6 | Entry point | **`main.py`** (already specified by `--entry-point main.py` above) |
| 7 | Foundry Project | **Use existing Foundry project** (choose the project you created in Lab 0) |
| 8 | Azure Tenant | Your tenant |
| 9 | Azure subscription | Your subscription |
| 10 | Location | Choose the **same region** as the Foundry project you created in Lab 0 |
| 11 | Model deployment | **`gpt-4.1-mini`** (the same-named deployment you deployed in Lab 0) |
| 12 | Model version | The version you deployed in Lab 0 |
| 13 | Model SKU | **GlobalStandard** |
| 14 | Deployment capacity | The default **10** is fine |
| 15 | Deployment name | The deployment name you created in Lab 0 (`gpt-4.1-mini`) |

On completion, "**AI agent definition added to your azd project successfully!**" is displayed.

### Generated files

```text
agent/<your agent name>/
├─ azure.yaml                  ← azd project definition (services.host: foundryagent)
├─ infra/                      ← required Bicep (Log Analytics / App Insights only. No ACR)
└─ src/<your agent name>/
    ├─ agent.yaml              ← Hosted Agent definition (model, runtime: python_3_13, entry-point, etc.)
    ├─ main.py                 ← entry point (template)
    ├─ requirements.txt        ← agent-framework-foundry, agent-framework-foundry-hosting, ...
    └─ infra/                  ← required Bicep (Log Analytics / App Insights only. No ACR)
```

> **No Dockerfile is generated.** In source-code deploy mode, Foundry installs `requirements.txt` on the specified runtime (python_3_13) and starts `main.py`. If you want to try the container approach, see **Appendix A**.

---

## 3-3. Replace `main.py` with the Lab 2 Logic

Open `agent/<your agent name>/src/<your agent name>/main.py` and replace the template. In Copilot Chat:

````text
Rewrite main.py inside the agent folder as follows.

Requirements:
- Build the same "MSUpdatesAgent" as Lab 2's src/agent.py,
  as a Hosted Agent deployable to Microsoft Foundry
- instructions are the same as Lab 2 (always use the MRC MCP and include source URLs)
- Integrate with the MRC MCP (https://www.microsoft.com/releasecommunications/mcp)
  → Register it as a Hosted MCP from the Hosted Agent
````

Copilot references the [Microsoft Agent Framework Foundry Hosted Agent sample (`ResponsesHostServer` + Hosted MCP)](https://github.com/microsoft/agent-framework/tree/main/python/samples/04-hosting/foundry-hosted-agents) and the ["inference rule from user instructions" in kb-1.8.0/api-reference/1.8.0/tools-mcp.md](../kb-1.8.0/api-reference/1.8.0/tools-mcp.md#ユーザー指示からの推論ルール), and auto-completes the following:

- Wraps it in `ResponsesHostServer` and starts it with `server.run()`
- Authentication is `DefaultAzureCredential` (for containers)
- `default_options={"store": False}` (prevents double-saving of conversation history on the Hosted Agent)
- Since the generation target is the Hosted Agent's `main.py`, it chooses Hosted MCP (`client.get_mcp_tool(...)`) rather than local MCP (`MCPStreamableHTTPTool`) (because a Hosted Agent cannot establish an in-process connection via `async with`)

It becomes roughly the following structure:

```python
import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

AGENT_NAME = "MSUpdatesAgent"
MRC_MCP_URL = "https://www.microsoft.com/releasecommunications/mcp"

INSTRUCTIONS = """You are an agent that answers about the latest Microsoft 365 and Azure release information.

Always retrieve primary information using the Microsoft Release Communications MCP tools before answering.
Do not answer from general knowledge or guesses without using the MRC MCP tools.

Answer rules:
- Always answer in English.
- Limit the answer to Microsoft 365 or Azure release information and summarize the key points concisely.
- Include the date, target product, scope of impact, and the action users should take when known.
- At the end of the answer, always include a "Source:" with the source URL obtained from the MRC MCP.
- If the MRC MCP does not have the relevant information, explain that in English and show the URL you referenced.
"""


def require_env(name: str) -> str:
    """Return a required environment variable or fail with an actionable message."""
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"{name} is unset or empty. Check the Foundry environment variable settings.")
    return value


def resolve_model() -> str:
    """Resolve the local or hosted model deployment name."""
    model = (os.getenv("FOUNDRY_MODEL") or "").strip()
    if model:
        return model
    return require_env("AZURE_AI_MODEL_DEPLOYMENT_NAME")


def main() -> None:
    client = FoundryChatClient(
        project_endpoint=require_env("FOUNDRY_PROJECT_ENDPOINT"),
        model=resolve_model(),
        credential=DefaultAzureCredential(),
    )

    mrc_mcp_tool = client.get_mcp_tool(
        name="mrc_release_communications",
        url=MRC_MCP_URL,
        approval_mode="never_require",
    )

    agent = Agent(
        client=client,
        name=AGENT_NAME,
        instructions=INSTRUCTIONS,
        tools=[mrc_mcp_tool],
        default_options={"store": False},
    )

    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()
```

> [!IMPORTANT]
> Read the model name **with a fallback**: `os.environ.get("FOUNDRY_MODEL") or os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"]`. Local runs use `FOUNDRY_MODEL` from `.env`, while the Hosted Agent container deployed with `azd up` uses `AZURE_AI_MODEL_DEPLOYMENT_NAME` injected by Foundry. Using only `os.environ["FOUNDRY_MODEL"]` **fails with `KeyError` at container startup** (the container does not have `FOUNDRY_MODEL` injected).

### Check `requirements.txt`

The `requirements.txt` generated by `azd ai agent init` should contain at least the following:

```text
agent-framework-foundry
agent-framework-foundry-hosting
aiohttp
azure-identity
python-dotenv
mcp
```

`aiohttp` is used by the `FoundryChatClient` HTTP client, so including it explicitly avoids dependency-resolution errors at deploy time. Add anything that is missing.

---

## 3-4. Run provision + deploy at once with `azd up`

Under the `agent/<your agent name>/` directory:

```bash
azd up
```

`azd up` runs **provision (create Azure resources) + deploy (zip the code + push to Foundry)** in a single command. Because it is source-code deploy mode, ACR and container builds are not needed. The only resources created are:

| Resource | Purpose |
|---|---|
| Resource group | Container for the other resources |
| Log Analytics workspace | Logs |
| Application Insights | Traces / metrics (used in Lab 4) |
| Managed identity | Azure authentication for the Hosted Agent |

> The existing Foundry project / model deployment created in Lab 0 is reused, so nothing new is created here.

On deployment completion, the Playground URL and Agent endpoint are displayed:

```text
Deploying services (azd deploy)
  Done: Deploying service ms-updates-agent
  - Agent playground (portal): https://ai.azure.com/.../build/agents/ms-updates-agent/build?version=1
  - Agent endpoint: https://<account>.services.ai.azure.com/api/projects/<project>/agents/ms-updates-agent/versions/1
```

Completes in 3–5 minutes (2–3 minutes faster than the container approach).

---

## 3-5. Invoke the Deployed Agent

### From the CLI

```bash
azd ai agent invoke "Tell me 3 Azure features that recently reached GA"
```

### Check status

```bash
azd ai agent show
```

Deployment succeeded if `status: Active`.

### Watch logs live

```bash
azd ai agent monitor --follow
```

When you run `azd ai agent invoke "..."` in another terminal, requests stream to the log in real time. Stop with `Ctrl+C`.

### Verify in the Foundry portal Playground

1. Open the Playground URL displayed on `azd up` completion in your browser (or Foundry portal > **Build** > **Agents** > `ms-updates-agent` > **Open in playground**)
2. Example prompts:
   ```text
   Summarize the 5 newest Outlook-related items from the Microsoft 365 Copilot roadmap
   ```
   ```text
   Tell me which Azure features will be Retiring within the next 90 days
   ```
3. On the **Tool calls** tab at the bottom, confirm that the MCP tools (`search_microsoft_release_messages`, etc.) are called

---

## 3-6. ★Stretch: Reflect a Code Change

Edit `INSTRUCTIONS` in `main.py` and just run `azd deploy` again to deploy a new version (from the second time on, provisioning is unnecessary, so `azd deploy` is faster than `azd up`).

```bash
azd deploy
azd ai agent show     # the version is incremented
azd ai agent invoke "Test question"
```

The new version becomes active and past versions remain as history.

---

## Appendix A: If You Want to Deploy with the Container Approach (★Stretch)

If your team policy requires a Docker image and ACR, select the following at scaffold time:

```bash
azd ai agent init --deploy-mode container --runtime python_3_13
```

In this case, you are additionally asked the following:

| Question | Recommended answer |
|---|---|
| Dependency resolution | **Remote build (dependencies installed on server during deployment)** |
| Container resources | The default **0.5 cores, 1Gi memory** |

With the container approach, an Azure Container Registry is created, and `azd deploy` builds the container image → pushes it to ACR (5–10 minutes longer than source-code deploy). It is mainly used in enterprise scenarios that need bring-your-own-Docker or a custom base image.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `azd ai agent init` does not recognize the `--deploy-mode` option | Run `azd extension upgrade azure.ai.agents` to update the extension |
| `SubscriptionNotRegistered` | `az provider register --namespace Microsoft.CognitiveServices` |
| `AuthorizationFailed` during provisioning | You need **Foundry Project Manager** + **Contributor**. Re-check Lab 0 |

If you hit errors when calling the tools of the `Microsoft Release Communications MCP Server`, consider using the `Microsoft Learn MCP Server` instead. Its endpoint is `https://learn.microsoft.com/api/mcp`.

---

Next → [Lab 4: Trace Inspection and Cloud Evaluation](04-trace-evaluation-en.md)
