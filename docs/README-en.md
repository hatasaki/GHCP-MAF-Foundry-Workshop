# GitHub Copilot × Microsoft Agent Framework × Microsoft Foundry Hands-on Workshop

> **The Japanese version of this documentation is available here: [README.md](README.md)**

A workshop where you build a "**Microsoft / Azure release-news agent**" with the **Microsoft Agent Framework (MAF) Python SDK** while leveraging GitHub Copilot's **Agent Skills**, deploy it as a **Microsoft Foundry Hosted Agent**, perform **tracing / evaluation**, and finally experience **automated deployment + automated evaluation with GitHub Actions CI/CD** — all end to end.

## Learning Goals

| # | Outcome |
|---|---------|
| 1 | Understand the concept of Agent Skills and how to author them, and have Copilot invoke them |
| 2 | Build an MCP-server-integrated agent with the MAF Python SDK with Copilot's assistance |
| 3 | Deploy to Foundry as a Hosted Agent and test it in the Playground |
| 4 | Send OpenTelemetry traces to Application Insights and measure quality with Cloud Evaluation |
| 5 | Experience "feature PR → automated evaluation → automated deployment on main merge" with GitHub Actions |

## Audience

- You understand Python basics (`async/await`, function definitions, Pydantic)
- You can run `az login` with the Azure CLI
- You use GitHub and VS Code daily
- You are **new to or have lightly touched** generative AI / agents (intermediate users are also welcome)
- You **can fork this repository to your own GitHub** (required to run GitHub Actions in Lab 5)

## Scenario: Microsoft / Azure Release-News Agent

You will build an internal-facing agent that integrates with the [Microsoft Release Communications MCP Server](https://learn.microsoft.com/en-us/microsoft-365/admin/manage/mrc-mcp?view=o365-worldwide) (public, free, **no authentication required**) and answers questions such as:

- "What Azure AI service updates reached GA this quarter?"
- "Tell me which Azure features will be retired within the next 3 months."
- "Summarize the 5 latest Microsoft 365 Copilot roadmap items."

MCP endpoint: `https://www.microsoft.com/releasecommunications/mcp`

Public tools (the main 4):
- `search_microsoft_release_messages` — Microsoft 365 Message Center
- `search_microsoft_roadmap` — Microsoft 365 Roadmap
- `search_azure_updates` — Azure Updates
- `search_microsoft_documentation` — Microsoft Learn

## Lab List

| Lab | Content |
|-----|-----|
| Lab 0 | [Environment setup (fork the repo + Foundry project + deploy gpt-4.1-mini)](00-setup-en.md) |
| Lab 1 | [Authoring Agent Skills and using them in Copilot](01-agent-skills-en.md) |
| Lab 2 | [Build the Microsoft release-news agent with MAF](02-maf-agent-en.md) (let Copilot write it) |
| Lab 3 | [Deploy the Hosted Agent to Foundry](03-foundry-deploy-en.md) |
| Lab 4 | [Trace inspection and Cloud Evaluation](04-trace-evaluation-en.md) |
| Lab 5 (optional) | [CI/CD with GitHub Actions (paste the finished YAML + Microsoft Learn MCP feature PR)](05-cicd-en.md) |

> Each Lab begins with **"What you build in this Lab"**.
> **Lab 5 is optional.** Tackle it based on your time and interest (you can skip it and still achieve the main learning goals in Labs 0–4).
> If you want to shorten the workshop for time or pacing, skip the chapters marked **★Stretch**.

## Prerequisite Tools

| Required / Optional | Tool | Verification command | Notes |
|---|---|---|---|
| Required | **Python 3.13+** | `python --version` | The Hosted Agent runtime is Python 3.13 |
| Required | Azure CLI 2.60+ | `az --version` | |
| Required | Git | `git --version` | |
| Required | **GitHub CLI** 2.40+ | `gh --version` | Used to fork in Lab 0 and create the PR in Lab 5 |
| Required | VS Code | (GUI) | |
| Required | GitHub Copilot extension | `code --list-extensions` | `GitHub.copilot` / `GitHub.copilot-chat` |
| Required | Azure subscription | | Permission to create a Foundry project + **Foundry Project Manager** |
| Required | **GitHub account** | | Fork this repository in Lab 5 to run Actions |
| Lab 3+ | Azure Developer CLI (azd) 1.25.3+ | `azd version` | |
| Lab 3+ | `azure.ai.agents` extension (0.1.39+) | `azd extension list` | |
| Lab 4 | Docker (optional: local trace inspection with the Aspire Dashboard) | `docker --version` | ★Stretch |

> Detailed setup steps are covered in [Lab 0](00-setup-en.md).

## Repository Structure

```text
ghcp-maf-foundry-workshop/
├─ docs/                          ← Workshop instructions (this folder)
│  ├─ README.md                  ← This file (Japanese)
│  ├─ README-en.md               ← This file (English)
│  ├─ 00-setup.md                ← Lab 0
│  ├─ 01-agent-skills.md         ← Lab 1
│  ├─ 02-maf-agent.md            ← Lab 2
│  ├─ 03-foundry-deploy.md       ← Lab 3
│  ├─ 04-trace-evaluation.md     ← Lab 4
│  └─ 05-cicd.md                 ← Lab 5
├─ kb-1.8.0/                      ← Detailed KB for the MAF Copilot (referenced by chatmodes)
│  ├─ README.md
│  ├─ patterns/  anti-patterns/
│  ├─ api-reference/1.8.0/
│  └─ migration-guides/
├── .github/
│  ├─ instructions/              ← Instructions auto-loaded by Copilot
│  └─ workflows/                 ← Created in Lab 5
├── data/
│  └─ eval_inputs.json           ← Evaluation queries read by Lab 4 / Lab 5 (placed from the start)
├── solutions/                     ← Finished files for each Lab (for when you are stuck / in a hurry)
│  ├─ README.md
│  ├─ lab0/  lab2/  lab3/  lab4/  lab5/
├── src/                          ← Agent code from Lab 2 onward (created by you)
├── .env.sample                    ← Template to copy into .env in Lab 0 (placed from the start)
└── .gitignore                     ← Excludes .env / .venv / .azure / eval results, etc. (placed from the start)
```

> The **`solutions/` folder** contains the finished version of the code you write in each Lab. When you get stuck or run low on time, refer to [`solutions/README.md`](../solutions/README.md).


## Reference Documentation

- [Microsoft Agent Framework official](https://learn.microsoft.com/agent-framework/overview/agent-framework-overview)
- [Microsoft Foundry Hosted Agents Quickstart (azd)](https://learn.microsoft.com/azure/foundry/agents/quickstarts/quickstart-hosted-agent)
- [Hosted Agent permissions reference](https://learn.microsoft.com/azure/foundry/agents/concepts/hosted-agent-permissions)
- [Microsoft Foundry RBAC](https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry)
- [Microsoft Release Communications MCP Server](https://learn.microsoft.com/en-us/microsoft-365/admin/manage/mrc-mcp?view=o365-worldwide)
- [Agent Framework Observability (Python)](https://learn.microsoft.com/agent-framework/agents/observability)
- [Foundry Cloud Evaluation (`azure-ai-projects` `evals`)](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/ai/azure-ai-projects/samples/evaluations)
- [hosted-agents/agent-framework Python samples](https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents/agent-framework/responses)
- [GitHub Copilot Customization](https://code.visualstudio.com/docs/copilot/customization/custom-instructions)

---

When you are ready, start with [Lab 0: Environment Setup](00-setup-en.md).
