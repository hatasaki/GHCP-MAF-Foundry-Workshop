---
description: ローカル動作確認済みの Microsoft Agent Framework 1.8.1 エージェントを Foundry の Hosted Agent としてデプロイする (azd ai agent init --deploy-mode code + azd up)。Lab 3 のショートカット。
allowed-tools: Read, Edit, Write, Grep, Glob, Bash
---

# /deploy-hosted-agent

Lab 3 ([`docs/03-foundry-deploy.md`](../../docs/03-foundry-deploy.md)) の作業を代行するスラッシュ コマンドです。Copilot の `/deploy-hosted-agent` プロンプトと同一仕様です。

## 仕様の取り込み

以下の Copilot 用プロンプト本文がそのままこのコマンドの指示として有効です。

@.github/prompts/deploy-hosted-agent.prompt.md

## ワークショップ既定値 (必ず読む)

@.github/copilot-instructions.md

## Claude Code 固有メモ

- **`azd` コマンドは実行しない**: Hosted Agent のデプロイには Azure 認証 / リージョン選択など対話的な手順が必要なため、Claude はコマンドを **案内** するだけにし、ユーザー自身が手動で `azd ai agent init` / `azd up` を実行します。
- **生成するファイル**: `agent/main.py` と `agent/requirements.txt` のみ。`azd ai agent init` が出力する `agent.yaml` と `infra/` は生成しない (ユーザーが対話的に作る)。
- **`AzureCliCredential` ではなく `DefaultAzureCredential` を使う**: Hosted Agent のコンテナ内に Azure CLI は存在しません。
- **`asyncio.run(main())` を残さない**: `ResponsesHostServer(agent).run()` が代替します。

## 引数

ユーザー入力: $ARGUMENTS

引数がない場合は対話で「元のローカル コード パス」「Hosted Agent 名」を 1 ターンで確認してください。
