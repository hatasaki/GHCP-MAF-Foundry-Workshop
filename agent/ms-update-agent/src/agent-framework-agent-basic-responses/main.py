# Copyright (c) Microsoft. All rights reserved.
"""Foundry Hosted Agent: MSUpdatesAgent (Lab 2 の src/agent.py と同じロジック)。

MRC MCP と Microsoft Learn MCP を Hosted MCP (client.get_mcp_tool) として登録し、
Microsoft 365 / Azure の最新リリース情報を日本語で回答する。``azd up`` で Foundry にデプロイする。
"""

import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

AGENT_NAME = "MSUpdatesAgent"
MRC_MCP_URL = "https://www.microsoft.com/releasecommunications/mcp"
LEARN_MCP_URL = "https://learn.microsoft.com/api/mcp"

INSTRUCTIONS = """あなたは Microsoft 365 と Azure の最新リリース情報を回答する日本語アシスタントです。
必ず MRC MCP のツール (https://www.microsoft.com/releasecommunications/mcp) を使って一次情報を取得し、
MRC で取得できない技術詳細や手順は Microsoft Learn MCP (https://learn.microsoft.com/api/mcp) で補足してよいです。
回答に出典 URL を添えてください。文末は、「ござる」に統一してください"""


def resolve_model() -> str:
    """ローカルは .env の FOUNDRY_MODEL、デプロイ後は Foundry 注入の deployment 名を使う。"""
    model = (os.getenv("FOUNDRY_MODEL") or "").strip()
    if model:
        return model
    model = (os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME") or "").strip()
    if model:
        return model
    raise RuntimeError(
        "Model deployment name is not configured. Set "
        "FOUNDRY_MODEL or AZURE_AI_MODEL_DEPLOYMENT_NAME."
    )


def main() -> None:
    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=resolve_model(),
        credential=DefaultAzureCredential(),
    )

    agent = Agent(
        client=client,
        name=AGENT_NAME,
        instructions=INSTRUCTIONS,
        tools=[
            # Hosted Agent では in-process の MCPStreamableHTTPTool ではなく
            # Hosted MCP (client.get_mcp_tool) として登録する。
            client.get_mcp_tool(
                name="MRC",
                url=MRC_MCP_URL,
                approval_mode="never_require",
            ),
            client.get_mcp_tool(
                name="Learn",
                url=LEARN_MCP_URL,
                approval_mode="never_require",
            ),
        ],
        # MCP ツールの往復で store=False は encrypted_content を要求し、非推論モデル
        # (gpt-4.1-mini) では 400 になる。store=True で previous_response_id を使う。
        default_options={"store": True},
    )

    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()
