# Lab 5 (Optional): GitHub Actions for CI/CD

> **This Lab is optional.** Tackle it if you are interested in CI/CD. You can skip it and still achieve the main learning goals of the workshop in Labs 0–4.

## What you do in this Lab

1. **Place the finished PR Check workflow and CI wrapper into your forked repository by copy-paste**
   - PR Check: pytest + call Lab 4's `src/evaluate.py` via `ci/run_evaluate.py` to run Cloud Evaluation → comment the result on the PR
2. **Issue your own access token in one line and register it as a GitHub Secret** (`az account get-access-token` + `gh secret set`. No permission to create an Entra app/SP/UAMI is needed; it is self-contained with only your own RBAC. The token is valid for 60–90 minutes, so it is enough to issue it once just before running Lab 5)
3. **Add a Microsoft Learn MCP tool to Lab 2's `src/agent.py`**, then push a branch & open a PR
4. Check the evaluation result comment on the PR → after merging to main, run the deployment locally with `azd deploy` manually (see 5-5)

> Prerequisites: you **forked the repository to your own GitHub in Lab 0** (`git remote -v` shows `origin` as your fork), you deployed the Hosted Agent in Lab 3, and Lab 4's `src/evaluate.py` runs locally.

---

## 5-1. Register Your Own Access Token as a Secret

To authenticate to Foundry from GitHub Actions, you only temporarily issue your own bearer token with `az account get-access-token` and upload it as a GitHub Secret.

> **Why the token approach**
>
> Creating an SP / Entra app requires the Entra directory permission (`Application.Create`), and creating a UAMI requires Contributor on the RG, but in many cases corporate tenant policy does not grant these to participants. Furthermore, here we want to use the RBAC (Foundry Project Manager, Cognitive Services User, etc.) that your own `az login`-authenticated account already has, so **using your own bearer token issued by `az` directly as a Secret** is the simplest.
>
> The token is valid for 60–90 minutes, which is plenty to run this Lab once. If it expires, just run the command in 5-1-1 again to overwrite the Secret.
>
> 💡 **Recommendation for production**
>
> The user-token approach requires manual renewal each time the token expires and is of course unsuitable for long-term production operation. If you can coordinate with the Entra app management team, the recommended production setup is **Entra App + Federated Credentials (OIDC)** so that no long-lived secret is needed.

### 5-1-1. Issue the token + register GitHub Secrets / Variables

You can set it up in one shot with the `gh` CLI. Confirm you have run `gh auth login` and that `origin` is your fork, then run it at the repository root.

**PowerShell**

```pwsh
# 1. Issue the token (the primary audience of the Foundry data plane, valid 60-90 minutes)
$token = az account get-access-token --scope https://ai.azure.com/.default --query accessToken -o tsv

# 2. Register it as a Secret (the old token is overwritten)
gh secret set AZURE_AI_AUTH_TOKEN --body $token

# 3. Variables used by the workflow (values OK to be public; same as set in .env / Lab 4)
gh variable set FOUNDRY_PROJECT_ENDPOINT --body "<endpoint obtained in Lab 0>"
gh variable set FOUNDRY_MODEL            --body "gpt-4.1-mini"
gh variable set HOSTED_AGENT_NAME        --body "ms-updates-agent"
gh variable set HOSTED_AGENT_VERSION     --body "1"
```

**Bash**

```bash
# 1. Issue the token
TOKEN=$(az account get-access-token --scope https://ai.azure.com/.default --query accessToken -o tsv)

# 2. Register it as a Secret
gh secret set AZURE_AI_AUTH_TOKEN --body "$TOKEN"

# 3. Variables
gh variable set FOUNDRY_PROJECT_ENDPOINT --body "<endpoint obtained in Lab 0>"
gh variable set FOUNDRY_MODEL            --body "gpt-4.1-mini"
gh variable set HOSTED_AGENT_NAME        --body "ms-updates-agent"
gh variable set HOSTED_AGENT_VERSION     --body "1"
```

> If you prefer the browser: under **Settings** > **Secrets and variables** > **Actions**, add `AZURE_AI_AUTH_TOKEN` as a Secret and the remaining 4 as Variables manually.

### 5-1-2. Refreshing when the token expires

If the workflow fails with `AADSTS70043: The refresh token has expired` / `401 Unauthorized`, re-run `az login`, run steps 1 and 2 of 5-1-1 again, and just click **Re-run jobs** on the Actions tab.

```pwsh
gh secret set AZURE_AI_AUTH_TOKEN --body (az account get-access-token --scope https://ai.azure.com/.default --query accessToken -o tsv)
```

---

## 5-2. Place the PR Check Workflow and CI Wrapper

You only create two files by copy-paste.

```bash
mkdir -p .github/workflows ci
```

### `ci/run_evaluate.py`

Because GitHub Actions cannot run `az login`, you use a lightweight wrapper that **swaps the `AzureCliCredential()` in `src/evaluate.py` for a lightweight class that just returns `AZURE_AI_AUTH_TOKEN`** in place. This way, the `src/evaluate.py` you built in Lab 4 runs in CI as is without a single line of change.

```python
"""Wrapper for GitHub Actions: run src/evaluate.py unmodified.

Workshop participants do not have Entra directory permissions (to create an App / SP),
so as the means to authenticate to Foundry from GitHub Actions, we pass **your own user
access token** via a GitHub Secret.

Run the following locally once beforehand (valid 60-90 minutes):

    az login
    gh secret set AZURE_AI_AUTH_TOKEN --body "$(az account get-access-token \
        --scope https://ai.azure.com/.default --query accessToken -o tsv)"

The workflow only passes AZURE_AI_AUTH_TOKEN to this script via env, and does not
touch the evaluation body (src/evaluate.py) at all.
"""

from __future__ import annotations

import os
import sys
import time

import azure.identity
from azure.core.credentials import AccessToken


class _StaticTokenCredential:
    """A minimal TokenCredential-compatible class that just returns the token passed via env."""

    def __init__(self, token: str, lifetime_seconds: int = 3600) -> None:
        self._token = token
        self._expires_on = int(time.time()) + lifetime_seconds

    def get_token(self, *scopes, **kwargs):
        return AccessToken(self._token, self._expires_on)


def _install_credential() -> None:
    token = os.environ.get("AZURE_AI_AUTH_TOKEN")
    if not token:
        sys.stderr.write(
            "ERROR: AZURE_AI_AUTH_TOKEN is unset. Pass it from the workflow env.\n"
        )
        sys.exit(1)
    # Swap out the place where src/evaluate.py calls AzureCliCredential()
    azure.identity.AzureCliCredential = (
        lambda *args, **kwargs: _StaticTokenCredential(token)
    )


def main() -> None:
    _install_credential()
    script = os.path.join("src", "evaluate.py")
    with open(script, encoding="utf-8") as fp:
        code = fp.read()
    # src/evaluate.py resolves the .env path from __file__, so pass it in exec globals
    exec(compile(code, script, "exec"), {"__name__": "__main__", "__file__": script})


if __name__ == "__main__":
    main()
```

### `.github/workflows/pr-check.yml`

```yaml
name: PR Check
on:
  pull_request:
    branches: [main]

permissions:
  contents: read
  pull-requests: write

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install agent-framework-foundry aiohttp
          pip install azure-identity python-dotenv pytest "azure-ai-projects>=2.2.0"
      - name: Test
        run: pytest tests/ -v || true

  evaluate:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install agent-framework-foundry aiohttp
          pip install azure-identity python-dotenv "azure-ai-projects>=2.2.0"
      - name: Run Cloud Evaluation
        id: eval
        env:
          # Your own user access token issued in 5-1 (valid 60-90 minutes)
          # ci/run_evaluate.py uses this in place of AzureCliCredential
          AZURE_AI_AUTH_TOKEN: ${{ secrets.AZURE_AI_AUTH_TOKEN }}
          FOUNDRY_PROJECT_ENDPOINT: ${{ vars.FOUNDRY_PROJECT_ENDPOINT }}
          FOUNDRY_MODEL: ${{ vars.FOUNDRY_MODEL }}
          HOSTED_AGENT_NAME: ${{ vars.HOSTED_AGENT_NAME }}
          HOSTED_AGENT_VERSION: ${{ vars.HOSTED_AGENT_VERSION }}
        run: |
          python ci/run_evaluate.py | tee eval.log
          RUN_ID=$(grep "Run started:" eval.log | awk '{print $3}')
          URL=$(grep "^Result:"      eval.log | awk '{print $2}')
          echo "run_id=${RUN_ID}" >> $GITHUB_OUTPUT
          echo "url=${URL}"       >> $GITHUB_OUTPUT
      - uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `## Cloud Evaluation result\n- Run ID: \`${{ steps.eval.outputs.run_id }}\`\n- Result: ${{ steps.eval.outputs.url }}`,
            })
```

### 5-2-1. Push the workflow to main

```bash
git checkout main
# Also place the evaluation script body (src/evaluate.py built in Lab 4) that the CI
# evaluate job runs onto main. Without it, CI fails with `FileNotFoundError: src/evaluate.py`.
git add .github/workflows/pr-check.yml ci/run_evaluate.py src/evaluate.py
git commit -m "ci: add PR check workflow + evaluation script"
git push origin main
```

Pushing to main triggers nothing (PR Check is only on the `pull_request` trigger). Actions first runs on the PR you create in 5-3.

> `src/evaluate.py` is placed as is from Lab 4 (CI runs it unmodified). If you do not have it yet, finish Lab 4 first.

---

## 5-3. Add Microsoft Learn MCP to the Lab 2 Agent

From here, it is an experience flow where "an actual developer opens a feature PR and CI runs." Add the official Microsoft Learn MCP server (<https://learn.microsoft.com/api/mcp>) as one tool to the `src/agent.py` you built in Lab 2.

```bash
git checkout -b feat/add-learn-mcp
```

As in Lab 2, switch to **`af-implementer`** in the Copilot Chat chatmode picker (this is a feature addition to existing code, so no new design decisions are needed; you do not need to go through `af-architect`). Enter the following:

````text
Update src/agent.py.
- In addition to the existing MRC MCP, make the Microsoft Learn MCP (https://learn.microsoft.com/api/mcp) usable too
- Add to instructions: "You may supplement technical details and steps not available from MRC with the Learn MCP"
- Keep the canonical pattern (client = FoundryChatClient + async with client.as_agent)
````

`af-implementer` references [kb-1.8.0/api-reference/1.8.0/tools-mcp.md](../kb-1.8.0/api-reference/1.8.0/tools-mcp.md), creates a second `MCPStreamableHTTPTool`, and rewrites it to pass `tools=[mrc_mcp, learn_mcp]` (keeping the same canonical pattern as Lab 2). Completed image:

```python
# src/agent.py (excerpt)
from azure.identity.aio import AzureCliCredential  # ← async version (same as Lab 2)

INSTRUCTIONS = """You are an assistant that answers about the latest Microsoft 365 and Azure release information.
Always use the MRC MCP tools (https://www.microsoft.com/releasecommunications/mcp) to retrieve primary information,
and include source URLs in your answers. You may supplement technical details and steps not available from MRC
with the Microsoft Learn MCP (https://learn.microsoft.com/api/mcp)."""

MRC_URL   = "https://www.microsoft.com/releasecommunications/mcp"
LEARN_URL = "https://learn.microsoft.com/api/mcp"


async def main() -> None:
    # Create MCP tools as plain objects and pass them to tools=.
    # The agent's async with (client.as_agent) automatically enters/exits them.
    mrc_mcp   = MCPStreamableHTTPTool(name="MRC",   url=MRC_URL)
    learn_mcp = MCPStreamableHTTPTool(name="Learn", url=LEARN_URL)

    async with AzureCliCredential() as credential:
        client = FoundryChatClient(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            model=os.environ["FOUNDRY_MODEL"],
            credential=credential,
        )
        async with client.as_agent(
            name="MSUpdatesAgent",
            instructions=INSTRUCTIONS,
            tools=[mrc_mcp, learn_mcp],
        ) as agent:
            # ... the existing dialogue loop (run_once / run_interactive) stays as is
```

> [!IMPORTANT]
> Keep the Lab 2 canonical pattern. Confirm it was not rewritten into `Agent(client=FoundryChatClient(...))`, `async with FoundryChatClient(...)`, or the sync `AzureCliCredential()` (details: [Lab 2](02-maf-agent-en.md) and [`missing-async-with-cleanup.md`](../kb-1.8.0/anti-patterns/missing-async-with-cleanup.md)).

Add the Learn MCP to the already-deployed `agent/main.py` from Lab 3 in the same way. Note that the Hosted Agent uses `client.get_mcp_tool(...)` rather than `MCPStreamableHTTPTool` ([the inference rule in kb-1.8.0/api-reference/1.8.0/tools-mcp.md](../kb-1.8.0/api-reference/1.8.0/tools-mcp.md#ユーザー指示からの推論ルール) lets Copilot decide automatically).

````text
Add the same Microsoft Learn MCP to agent/main.py as a Hosted MCP (client.get_mcp_tool).
````

Just confirm local connectivity.

```bash
python src/agent.py "Check the latest feature updates for the Azure Functions Premium plan and its configuration steps on Learn, and tell me"
```

---

## 5-4. Open a PR and Experience CI

```bash
git add src/agent.py agent/main.py
git commit -m "feat(agent): add Microsoft Learn MCP for technical follow-up"
git push -u origin feat/add-learn-mcp
gh pr create --title "feat: add Learn MCP" --body "Add Microsoft Learn MCP in addition to MRC. With the Copilot Skill inference rule, the Hosted Agent side auto-switches to get_mcp_tool." --base main
```

After a few tens of seconds, **Actions** > **PR Check** on GitHub starts.

1. `test` job: `pytest` (does not fail even when empty)
2. `evaluate` job: `ci/run_evaluate.py` runs `src/evaluate.py` **with the same script as Lab 4** to issue a Cloud Evaluation (the wrapper swaps `AzureCliCredential()` for the user token)
3. When the evaluation completes in 5–15 minutes, a comment like the following is automatically posted to the PR:

> ## Cloud Evaluation result
> - Run ID: `evalrun_xxxxxxxx`
> - Result: <https://ai.azure.com/evaluation/eval_xxxx/runs/evalrun_xxxx>

Open the URL and check the score of `intent_resolution` (the evaluator you set in 4-2-3 of Lab 4) and the judgment rationale for each sample.

> [!NOTE]
> The evaluation target at this PR point is **still the pre-redeploy Hosted Agent (`ms-updates-agent` version 1 = MRC only)**. Even if you add the Learn MCP to the code, the deployment happens in 5-5 (after merge), so it is not reflected in the evaluation. If you want to measure the effect of adding the Learn MCP, re-run the evaluation after `azd deploy` in 5-5 and compare the scores.

---

## 5-5. Merge to main and Deploy the Hosted Agent Locally

After you merge the PR, run `azd deploy` **manually on your machine**. Deploying to the Hosted Agent involves a container build and ARM operations, which require broad-scope authentication (Contributor + Foundry Project Manager) each time, so the user token alone is unsuitable.

```bash
git checkout main
git pull
cd agent
azd deploy            # Deploy with your own az login session
azd ai agent show     # Confirm the new version is active
```

> If you want automatic deployment on GitHub at the time of the main merge, you need to set up **Entra App + Federated Credentials (OIDC)** as in production operation. It is out of scope for the workshop, so consult your company's Entra administrator.

---

## 5-6. ★Stretch: Fail the PR if the Evaluation Score Is Below a Threshold

If you append the following to the end of `main()` in Lab 4's `src/evaluate.py` (after displaying `Result:`), CI becomes a quality gate. The variable names match Lab 4's `eval_definition` / `run` / `client` (`project_client.get_openai_client()`) directly.

```python
    # Append inside main(), after displaying Result (match the indentation to main()'s scope)
    final = client.evals.runs.retrieve(eval_id=eval_definition.id, run_id=run.id)
    passed = getattr(final.result_counts, "passed", 0)
    total = getattr(final.result_counts, "total", 0)
    ratio = passed / total if total else 0
    print(f"pass_ratio={ratio:.2f} ({passed}/{total})")

    THRESHOLD = 0.7
    if ratio < THRESHOLD:
        print(f"::error::pass_ratio {ratio:.2f} < {THRESHOLD}")
        sys.exit(1)
```

`::error::` is GitHub Actions' annotation syntax; a warning marker appears in the Files changed tab of the PR.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `AADSTS70043` / `401 Unauthorized` / `Token has expired` | The 60–90 minute validity of `AZURE_AI_AUTH_TOKEN` expired. Run the one line in 5-1-2 again, then **Re-run jobs** on Actions |
| `ERROR: AZURE_AI_AUTH_TOKEN is unset` | The Secret is not registered. Run 5-1-1, or confirm `AZURE_AI_AUTH_TOKEN` is visible with `gh secret list` |
| `AADSTS500011: The resource principal named ... was not found` | Confirm you issued it with `--scope https://ai.azure.com/.default`. Other audiences such as `https://management.azure.com` are not accepted by the Foundry data plane |
| `403 Forbidden` from Foundry API | Your Azure account has insufficient role on the Foundry Project. Confirm that the **Foundry Project Manager** granted in Lab 0 is still active under Azure portal > Foundry resource > IAM |
| The evaluate job times out | Increase the polling limit (30 minutes) in `src/evaluate.py` |
| The PR comment is not added | Confirm the workflow has `permissions: pull-requests: write` |
| `MFA required` / `interaction_required` | Re-run `az login --tenant <tenant-id>` locally to clear MFA, then reissue the token |
| Can the Secret be seen / read on GitHub? | No. Repo Settings > Secrets cannot be read later even by the creator, and they are masked as `***` in Actions logs, so use them with confidence |

---

## Checklist

- [ ] In 5-1, issue `az account get-access-token` and register the `AZURE_AI_AUTH_TOKEN` Secret + 4 Variables on GitHub
- [ ] Push `.github/workflows/pr-check.yml` + `ci/run_evaluate.py` to main
- [ ] Add the Learn MCP to `src/agent.py` + `agent/main.py` on the `feat/add-learn-mcp` branch
- [ ] Create the PR → Actions > PR Check runs → evaluation result comment on the PR (if the token expires, refresh in 5-1-2 → Re-run)
- [ ] Merge to main → run `azd deploy` manually locally → confirm the new version is active with `azd ai agent show`

---

## Workshop Complete!

You have now completed the following:

- Lab 0: Foundry project + repository fork + Foundry Project Manager assignment
- Lab 1: GHCP reads the MAF × Foundry skill and can produce suggestions on the latest API
- Lab 2: Local MAF agent (FoundryChatClient + MCP + AgentSession + streaming)
- Lab 3: Deployed as a Foundry Hosted Agent (`azd ai agent init` → `azd deploy`)
- Lab 4: Hosted Agent trace inspection + Cloud Evaluation run from local with the Foundry SDK
- Lab 5: Experienced "feature PR → automated evaluation → `azd deploy` locally after merge" with GitHub Actions

When you want to clean up:

```bash
cd agent
azd down --purge --force
```

Reference links:

- [Microsoft Agent Framework Python](https://github.com/microsoft/agent-framework/tree/main/python)
- [Foundry samples — hosted-agents](https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents)
- [azure-ai-projects evaluations sample](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/samples/evaluations)
- [Microsoft Foundry quickstart (official steps for the user-token approach)](https://learn.microsoft.com/azure/foundry/quickstarts/get-started-code#set-environment-variables-and-get-the-code)
- [Connect from GitHub Actions to Azure with OIDC (recommended for production)](https://learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect)
