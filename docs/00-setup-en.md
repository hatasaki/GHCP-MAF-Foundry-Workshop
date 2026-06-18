# Lab 0: Environment Setup

## What you do in this Lab

- Confirm the required tools are installed (Python 3.13+, Azure CLI, GitHub CLI, azd, the azd `azure.ai.agents` extension)
- Sign in to your Azure subscription and **verify your role (Foundry Project Manager is required)**
- **Create a new Microsoft Foundry project**
- **Deploy the gpt-4.1-mini model**
- Prepare a Python virtual environment
- Create a `.env` file populated with real values
- ★Optional: fork the workshop repository to your own GitHub account (if you will run GitHub Actions in Lab 5)

> Lab 2 onward assumes a **Foundry project + a deployed model**. Foundry provisioning takes 5–10 minutes, so it is efficient to set up the Python environment in parallel during that wait.

---

## 0-1. Tool Check

### Required tools

Open a shell (PowerShell / bash / fish) and run the following. If every command prints a version, you are good.

```bash
python --version          # 3.13 or higher
az --version              # 2.60 or higher (check azure-cli on the first line)
git --version
gh --version              # GitHub CLI 2.40+ (used for forking and PR creation in Lab 5)
code --version            # VS Code must be on PATH
```

If anything is not installed, install it from the links below:

| Tool | Link |
|---|---|
| Python **3.13** | <https://www.python.org/downloads/> |
| Azure CLI | <https://learn.microsoft.com/cli/azure/install-azure-cli> |
| Git | <https://git-scm.com/downloads> |
| **GitHub CLI** | <https://cli.github.com/> |
| VS Code | <https://code.visualstudio.com/> |

> Python 3.13 is required because the Hosted Agent runtime (Lab 3) is Python 3.13. Python 3.10–3.12 works through Lab 2, but in Lab 3 `azd ai agent run` requires 3.13 when it creates a local virtual environment.

### VS Code extensions

Open VS Code and confirm the following extensions are installed:

- **GitHub Copilot**
- **GitHub Copilot Chat**
- **Python**
- **Azure CLI Tools** (optional / convenient)
- **Microsoft Foundry Toolkit** (recommended for local trace inspection in Lab 3) <https://aka.ms/foundrytk>

Verification command (lists installed extensions):

```bash
code --list-extensions
```

Required IDs: you are good if `GitHub.copilot` / `GitHub.copilot-chat` / `ms-python.python` appear in the output.

### Tools used from Lab 3 onward (easiest to install now together)

**PowerShell (Windows)**

```pwsh
winget install Microsoft.Azd
```

**Bash (macOS / Linux)**

```bash
# macOS
brew tap azure/azd && brew install azd
# Linux
curl -fsSL https://aka.ms/install-azd.sh | bash
```

Common: check the `azd` version → install the `azure.ai.agents` extension.

```bash
azd version                                # 1.25.3 or higher (required for Hosted Agent source-code deploy)
azd extension install azure.ai.agents      # Extension for Hosted Agent deployment (0.1.39+ required)
azd extension list                         # OK if azure.ai.agents appears
```

> If it is already installed, upgrade with `azd extension upgrade azure.ai.agents`. If the version is **below 0.1.39**, you will hit issues such as the `--deploy-mode` option being unavailable in `azd ai agent init`.

---

## 0-2. Azure Sign-in and Permission Check

```bash
az login
azd auth login
az account show --query "{Subscription:name, Tenant:tenantId, User:user.name}"
```

### Required roles

In this workshop you create a new Foundry project and then deploy and run agents. **Deploying a Hosted Agent (Lab 3) requires `Foundry Project Manager`.**

| Purpose | Role | Scope | Necessity |
|---|---|---|---|
| Create Foundry resource / project | **Owner** or **Contributor + User Access Administrator** | Subscription or resource group | Not needed if you reuse an existing resource |
| **Hosted Agent deployment (Lab 3+)** | **Foundry Project Manager** | Foundry project | **Required** |
| Invoke / evaluate the agent | **Foundry User** or higher | Foundry project | Required |

To avoid instability from specifying role names, this workshop uses role definition IDs (GUIDs).

| Role name | Role definition ID (GUID) |
|---|---|
| Foundry User | `53ca6127-db72-4b80-b1b0-d745d6d5456d` |
| Foundry Owner | `c883944f-8b7b-4483-af10-35834be79c4a` |
| Foundry Account Owner | `e47c6f54-e4a2-4754-9501-8e0985b135e1` |
| **Foundry Project Manager** | **`eadc314b-1a2d-4efa-be10-5d325db5065e`** |

Permission check:

**PowerShell**

```pwsh
$subId = az account show --query id -o tsv
$myId  = az ad signed-in-user show --query id -o tsv
az role assignment list --assignee $myId `
    --scope "/subscriptions/$subId" --query "[].roleDefinitionName" -o tsv
```

**Bash**

```bash
SUB_ID=$(az account show --query id -o tsv)
MY_ID=$(az ad signed-in-user show --query id -o tsv)
az role assignment list --assignee "$MY_ID" \
    --scope "/subscriptions/$SUB_ID" --query "[].roleDefinitionName" -o tsv
```

If you have `Owner` or `Contributor + User Access Administrator`, you can create a new project in 0-3 and assign yourself **Foundry Project Manager** at that time.

---

## 0-3. Create a Microsoft Foundry Project

Here we only **trigger** the project creation first. While it provisions (5–10 minutes), you can proceed with 0-5 onward in parallel.

### Option A. Create from the portal (recommended / for first-time users)

1. Open the [Microsoft Foundry portal](https://ai.azure.com) in your browser (confirm the **New Foundry** toggle in the top right is ON)
2. Click **+ New project**
3. Enter the following:
   | Item | Value |
   |---|---|
   | Project name | `workshop-foundry-<your-alias>` (e.g., `workshop-foundry-taro`) |
   | Foundry resource | Select **Create new** |
   | Resource group | **Create new** — a unique name per participant (e.g., `rg-taro1111`) |
   | Region | Any (`eastus`, `westus2`, etc. The Lab 3 Hosted Agent is now also available in multiple regions) |
4. Click **Create** → wait 5–10 minutes
5. After completion, copy the **Project endpoint** from the project's **Overview** page (e.g., `https://<account>.services.ai.azure.com/api/projects/<project>`)

> You will paste this endpoint into `.env` in 0-7. Keep it handy in a scratch note.

### Assign yourself Foundry Project Manager

The project creator is usually granted Foundry Project Manager, but verify / assign it just in case.

**PowerShell**

```pwsh
$rg = "<your resource group name>"   # e.g., rg-taro1111
$accountName = "<the Foundry resource name created above>"
$projectName = "workshop-foundry-<your-alias>"
$myId = az ad signed-in-user show --query id -o tsv

$projectId = az cognitiveservices account project show `
    -g $rg --account-name $accountName --name $projectName --query id -o tsv

az role assignment create `
    --role "eadc314b-1a2d-4efa-be10-5d325db5065e" `
    --assignee-object-id $myId --assignee-principal-type User `
    --scope $projectId
```

**Bash**

```bash
RG="<your resource group name>"   # e.g., rg-taro1111
ACCOUNT_NAME="<the Foundry resource name created above>"
PROJECT_NAME="workshop-foundry-<your-alias>"
MY_ID=$(az ad signed-in-user show --query id -o tsv)

PROJECT_ID=$(az cognitiveservices account project show \
    -g "$RG" --account-name "$ACCOUNT_NAME" --name "$PROJECT_NAME" --query id -o tsv)

az role assignment create \
    --role "eadc314b-1a2d-4efa-be10-5d325db5065e" \
    --assignee-object-id "$MY_ID" --assignee-principal-type User \
    --scope "$PROJECT_ID"
```

> If it is already assigned, you will see a `RoleAssignmentExists` error, which you can ignore.

### Option B. Create everything from the CLI (automation-oriented / ★Stretch)

**PowerShell**

```pwsh
$rg = "rg-<your-alias>"          # unique per participant (e.g., rg-taro1111)
$loc = "<region>"                 # e.g., eastus, westus2, etc.
$alias = "<your-alias>"           # lowercase letters and digits only
$accountName = "foundry-$alias"
$projectName = "workshop-foundry-$alias"

az group create -n $rg -l $loc
az cognitiveservices account create `
    -g $rg -n $accountName -l $loc `
    --kind AIServices --sku S0 `
    --custom-domain $accountName --yes
az cognitiveservices account project create `
    -g $rg --account-name $accountName --name $projectName
```

**Bash**

```bash
RG="rg-<your-alias>"              # unique per participant (e.g., rg-taro1111)
LOC="<region>"                     # e.g., eastus, westus2, etc.
ALIAS="<your-alias>"              # lowercase letters and digits only
ACCOUNT_NAME="foundry-$ALIAS"
PROJECT_NAME="workshop-foundry-$ALIAS"

az group create -n "$RG" -l "$LOC"
az cognitiveservices account create \
    -g "$RG" -n "$ACCOUNT_NAME" -l "$LOC" \
    --kind AIServices --sku S0 \
    --custom-domain "$ACCOUNT_NAME" --yes
az cognitiveservices account project create \
    -g "$RG" --account-name "$ACCOUNT_NAME" --name "$PROJECT_NAME"
```

Get the endpoint:

**PowerShell**

```pwsh
az cognitiveservices account project show `
    -g $rg --account-name $accountName --name $projectName `
    --query "properties.endpoints.\"AI Foundry API\"" -o tsv
```

**Bash**

```bash
az cognitiveservices account project show \
    -g "$RG" --account-name "$ACCOUNT_NAME" --name "$PROJECT_NAME" \
    --query 'properties.endpoints."AI Foundry API"' -o tsv
```

---

## 0-4. Deploy the gpt-4.1-mini Model

Run this after the project from 0-3 has **finished provisioning** (the status on the Overview page is `Succeeded`).

### Option A. From the portal (recommended)

1. Open the project you created in the Foundry portal
2. Left menu **Models + endpoints** > **+ Deploy model** > **Deploy base model**
3. Type `gpt-4.1-mini` in the search box → select → **Confirm**
4. Deployment settings:
   | Item | Value |
   |---|---|
   | Deployment name | **`gpt-4.1-mini`** ← keep this **as is**, since you will use it for `FOUNDRY_MODEL` in `.env` |
   | Deployment type | **Global Standard** |
5. Click **Deploy** → completes in 1–2 minutes

### Option B. From the CLI (★Stretch)

**PowerShell**

```pwsh
az cognitiveservices account deployment create `
    -g $rg --name $accountName `
    --deployment-name "gpt-4.1-mini" `
    --model-name "gpt-4.1-mini" `
    --model-format "OpenAI" `
    --sku-name "GlobalStandard"
```

**Bash**

```bash
az cognitiveservices account deployment create \
    -g "$RG" --name "$ACCOUNT_NAME" \
    --deployment-name "gpt-4.1-mini" \
    --model-name "gpt-4.1-mini" \
    --model-format "OpenAI" \
    --sku-name "GlobalStandard"
```

> If you want to pin the model version, add `--model-version 2025-xx-xx`. You can check versions in the Foundry portal under **Models + endpoints > Model catalog**.

### Verification

You are good if `gpt-4.1-mini` appears with **Status: Succeeded** under **Models + endpoints** in the Foundry portal.

---

## 0-5. ★Optional: Fork the Repository to Your GitHub and Clone It

> [!NOTE]
> **This is only needed if you will do Lab 5 (CI/CD).** If you only do Labs 2–4, skip this section and proceed to 0-6.

In Lab 5 you **run GitHub Actions against this forked repository**, so first fork it to your own GitHub account.

### Option A. Fork + clone with the GitHub CLI (recommended)

```bash
gh auth login        # first time only. Authenticate in a web browser
gh repo fork <upstream-owner>/ghcp-maf-foundry-workshop --clone --remote
cd ghcp-maf-foundry-workshop
code .
```

With `--clone --remote`, the fork is cloned at the same time, with `origin` set to your fork and `upstream` to the original repository.

### Option B. Fork from the browser

1. Open the original repository `https://github.com/<upstream-owner>/ghcp-maf-foundry-workshop` in your browser
2. Click **Fork** > **Create fork** in the top right
3. Copy your fork's URL and clone it:

```bash
git clone https://github.com/<your-github-username>/ghcp-maf-foundry-workshop.git
cd ghcp-maf-foundry-workshop
git remote add upstream https://github.com/<upstream-owner>/ghcp-maf-foundry-workshop.git
code .
```

### Verification

```bash
git remote -v
# origin    https://github.com/<your-github-username>/ghcp-maf-foundry-workshop.git (fetch/push)
# upstream  https://github.com/<upstream-owner>/ghcp-maf-foundry-workshop.git       (fetch/push)
```

Check the directory structure:

```bash
ls -la                 # Bash
Get-ChildItem -Force   # PowerShell
```

You are good if `docs/`, `kb-1.8.0/`, and `.github/` are present.

---

## 0-6. Python Virtual Environment and Packages

### Create and activate the virtual environment

**PowerShell (Windows)**

```pwsh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Bash (macOS / Linux / WSL / Git Bash)**

```bash
python -m venv .venv
source .venv/bin/activate    # On Windows Git Bash, use source .venv/Scripts/activate
```

**Fish (when using the fish shell on macOS / Linux)**

```fish
python -m venv .venv
source .venv/bin/activate.fish    # Fish requires explicitly specifying activate.fish
```

> Running `source .venv/bin/activate` in Fish produces an `Unsupported use of '='` error. Always specify `activate.fish`.

### Install packages (common to both shells)

```bash
pip install --upgrade pip

# For Lab 2 (local MAF) —— Agent Framework Python 1.0.0 GA or later
# `--pre` is not needed. `aiohttp` is used by the FoundryChatClient HTTP client.
# `mcp` is for `MCPStreamableHTTPTool` / `MCPStdioTool` (required for the MRC MCP connection in Lab 2).
pip install agent-framework-foundry aiohttp mcp
pip install azure-identity python-dotenv pydantic

# For Lab 4 (Cloud Evaluation) —— the evals API stabilized in 2.2.0 or later
pip install "azure-ai-projects>=2.2.0"
```

> `mcp` is an **optional extra** of `agent-framework-core` (included in `agent-framework-core[all]`), so installing only `agent-framework-foundry` does not include it. Since Lab 2 uses `MCPStreamableHTTPTool`, **install it explicitly**. Without it, the runtime fails with `ModuleNotFoundError: 'MCPStreamableHTTPTool' requires 'mcp'` (the class import itself succeeds, so `compileall` does not catch it).

> Because Agent Framework Python 1.0.0 went GA in early 2026, `--pre` is no longer required. However, the `agent-framework[all]` umbrella takes a long time to resolve dependencies, so explicitly installing `agent-framework-foundry` + individual dependencies as shown above is more stable.

> Lab 3 (Hosted Agent deployment) also needs `agent-framework-foundry-hosting`, but in Lab 3 `azd ai agent init` generates a `requirements.txt` that lists it, so you do not need to install it explicitly here.

> If VS Code does not recognize the virtual environment, use `Ctrl+Shift+P` → **Python: Select Interpreter** and choose the Python under `.venv`.

Verify the installation:

```bash
python -c "import agent_framework; print(agent_framework.__version__)"
python -c "from agent_framework.foundry import FoundryChatClient; print('FoundryChatClient OK')"
python -c "from azure.ai.projects import AIProjectClient; print('AIProjectClient OK')"
python -c "from mcp.client.streamable_http import streamable_http_client; print('mcp streamable_http OK')"
```

You are good if all four lines run without exceptions. The last `mcp` import test pre-validates the lazy import that `MCPStreamableHTTPTool` needs at runtime in Lab 2.

---

## 0-7. Create Environment Variables (`.env`)

The repository root already contains **`.env.sample` and `.gitignore` from the start**. You only need to copy the template and fill in real values.

### Copy `.env.sample` to create `.env`

Common to both shells (`cp` is an alias for `Copy-Item` in PowerShell):

```bash
cp .env.sample .env
code .env    # Paste the endpoint from 0-3 into FOUNDRY_PROJECT_ENDPOINT
```

In principle you only change the URL in `FOUNDRY_PROJECT_ENDPOINT`. `FOUNDRY_MODEL=gpt-4.1-mini` can stay as is because you deployed it under the same name in 0-4. Update `HOSTED_AGENT_NAME` / `HOSTED_AGENT_VERSION` as needed after completing Lab 3.

> `.gitignore` already excludes `.env` from the start, so there is no risk of an accidental commit.

---

When you are ready → [Lab 1: Authoring Agent Skills and Using Them in Copilot](01-agent-skills-en.md)
