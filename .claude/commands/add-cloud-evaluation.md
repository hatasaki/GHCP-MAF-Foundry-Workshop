---
description: Lab 3 までにデプロイ済みの Hosted Agent に対し、Foundry Cloud Evaluation (azure-ai-projects) を呼び出して採点するスクリプトを 1 ファイルで生成する。Lab 4 のショートカット。
allowed-tools: Read, Edit, Write, Grep, Glob, Bash
---

# /add-cloud-evaluation

Lab 4 ([`docs/04-trace-evaluation.md`](../../docs/04-trace-evaluation.md)) の作業を代行するスラッシュ コマンドです。Copilot の `/add-cloud-evaluation` プロンプトと同一仕様です。

## 仕様の取り込み

以下の Copilot 用プロンプト本文がそのままこのコマンドの指示として有効です。

@.github/prompts/add-cloud-evaluation.prompt.md

## ワークショップ既定値 (必ず読む)

@.github/copilot-instructions.md

## Python コーディング規約 (必ず読む)

@.github/instructions/python.instructions.md

## Claude Code 固有メモ

- **Lab 3 が前提**: `.env` の `HOSTED_AGENT_NAME` が空のときは fail-fast で停止し、`/deploy-hosted-agent` を案内してください。
- **雛形**: [`solutions/lab4/src/evaluate.py`](../../solutions/lab4/src/evaluate.py) をそのままコピーして必要箇所だけ差分編集する。クラス化やロガー注入など余計な抽象化はしない。
- **`outputs/` を `.gitignore` に確認**: 評価結果 JSON はリポジトリにコミットしないこと (既存 `.gitignore` の `outputs/` 行を確認)。
- **シークレットを出さない**: 生成した評価結果 JSON にプロンプト / 応答が含まれる可能性がある。Lab 4 デモ内では問題ないが、`outputs/eval-result-*.json` は **必ず gitignore 済み** であることを念のため確認。

## 引数

ユーザー入力: $ARGUMENTS

引数がない場合は「出力先ファイル」「評価入力 JSON のパス」を 1 ターンで確認してください。
