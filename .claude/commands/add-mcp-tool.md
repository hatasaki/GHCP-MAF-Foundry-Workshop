---
description: 既存の Microsoft Agent Framework 1.8.1 エージェントに MCP サーバー (ローカル または Hosted) を 1 つだけ最小差分で追加する。kb-1.8.0 の正規パターンに従う。
allowed-tools: Read, Edit, Write, Grep, Glob, Bash
---

# /add-mcp-tool

既存のエージェントに **MCP サーバー** を 1 つ追加するスラッシュ コマンドです。Lab 2 / 3 で作ったエージェントに Microsoft Learn MCP を追加するときなどに使います。Copilot の `/add-mcp-tool` プロンプトと同一仕様です。

## 仕様の取り込み

以下の Copilot 用プロンプト本文がそのままこのコマンドの指示として有効です。

@.github/prompts/add-mcp-tool.prompt.md

## ワークショップ既定値 (必ず読む)

@.github/copilot-instructions.md

## Python コーディング規約 (必ず読む)

@.github/instructions/python.instructions.md

## Claude Code 固有メモ

- **最小差分の原則**: import を 1 行追加 (Local の場合のみ) と `tools=[...]` に 1 つ追加するだけ。**他のツールを消さない**。instructions の書き換えや関数の分割は禁止。
- **Local vs Hosted を勝手に決めない**: 編集対象が `solutions/lab3/agent/main.py` のような Hosted Agent エントリ ポイントなら Hosted MCP (`FoundryChatClient.get_mcp_tool(...)`)、それ以外のローカル実行スクリプト (`asyncio.run(main())` で動かす) なら Local MCP (`MCPStreamableHTTPTool`)。迷ったらユーザーに確認すること。
- **`MCPStreamableHTTPTool` の引数名**: `name=` と `url=` のみ。`uri=` や `endpoint=` は不可 ([`kb-1.8.0/anti-patterns/removed-apis-since-1.0.md`](../../kb-1.8.0/anti-patterns/removed-apis-since-1.0.md))。
- **検証は案内のみ**: 編集後は `python -m compileall -q <ファイル>` を実行して構文を確認するところまで。実際の MCP 呼び出しテスト (`python src/agent.py`) はユーザーが対話的に実行します。

## 引数

ユーザー入力: $ARGUMENTS

引数がない場合は「編集対象ファイル」「MCP サーバー URL」「表示名 (任意)」を 1 ターンで確認してください。
