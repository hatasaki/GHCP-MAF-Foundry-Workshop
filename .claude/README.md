# `.claude/` — Claude Code 専用アセット

このディレクトリには **Claude Code (CLI / IDE 統合)** 向けの設定が入っています。GitHub Copilot 用の [`.github/`](../.github/) と 1 対 1 で対応します。

> [!NOTE]
> リポジトリ ルートの [`CLAUDE.md`](../CLAUDE.md) が Claude Code に自動で読み込まれるエントリ ポイントです。本ディレクトリのアセットは **CLAUDE.md からは自動 import しません**。サブエージェントとスラッシュ コマンドは「明示的に呼び出されたとき」に読まれます。

## 構成

```text
.claude/
├── README.md                       ← 本ファイル
├── agents/                         ← サブエージェント (Copilot chatmodes 相当)
│   ├── af-architect.md
│   └── af-implementer.md
└── commands/                       ← スラッシュ コマンド (Copilot prompts 相当)
    ├── add-cloud-evaluation.md
    ├── add-mcp-tool.md
    └── deploy-hosted-agent.md
```

## サブエージェント (`agents/`)

`@agent-<name>` でメンションするか、Claude が自動で委譲します。

| 名前 | 役割 | ツール権限 | source-of-truth |
|---|---|---|---|
| `af-architect` | 要件 → 設計ドキュメント (コードを書かない) | Read / Grep / Glob | [`.github/agents/af-architect.agent.md`](../.github/agents/af-architect.agent.md) |
| `af-implementer` | 設計 → Python コード (最小差分、KB 準拠) | Read / Edit / Write / Grep / Glob / Bash | [`.github/agents/af-implementer.agent.md`](../.github/agents/af-implementer.agent.md) |

両サブエージェントとも、本文は Copilot 用の `.agent.md` ファイルを `@` 構文で取り込んでいます。**Copilot 側を更新すれば Claude 側も自動的に反映**されます。

### サブエージェントの呼び出し例

```text
> @agent-af-architect Lab 2 で MCP を使うエージェントの設計を出して

(Claude が af-architect を起動 → 設計ドキュメントを出力)

> @agent-af-implementer 上の設計に従って solutions/lab2/src/agent.py を書いて

(Claude が af-implementer を起動 → 最小差分で実装)
```

## スラッシュ コマンド (`commands/`)

`/コマンド名` で呼び出します。

| コマンド | 用途 | 対応 Lab | source-of-truth |
|---|---|---|---|
| `/deploy-hosted-agent` | `azd ai agent init --deploy-mode code` + `azd up` を案内 | [Lab 3](../docs/03-foundry-deploy.md) | [`.github/prompts/deploy-hosted-agent.prompt.md`](../.github/prompts/deploy-hosted-agent.prompt.md) |
| `/add-cloud-evaluation` | Foundry Cloud Evaluation スクリプトを生成 | [Lab 4](../docs/04-trace-evaluation.md) | [`.github/prompts/add-cloud-evaluation.prompt.md`](../.github/prompts/add-cloud-evaluation.prompt.md) |
| `/add-mcp-tool` | 既存エージェントに MCP を 1 つ追加 | [Lab 5](../docs/05-cicd.md) の前段 | [`.github/prompts/add-mcp-tool.prompt.md`](../.github/prompts/add-mcp-tool.prompt.md) |

### スラッシュ コマンドの呼び出し例

```text
> /add-mcp-tool

Claude: どのファイルにどの MCP サーバーを追加しますか？
> solutions/lab2/src/agent.py に https://learn.microsoft.com/api/mcp を追加

(Claude が KB を参照しながら最小差分で編集)
```

## いつ使うか

- ✅ Lab を一通り終えた後で **同じ作業を別のエージェントで繰り返したい** とき。
- ✅ 手順は理解しているが **タイピング量を減らしたい** とき。
- ✅ 標準パターンから逸脱しない安全な変更を **短時間で適用したい** とき。

## いつ使わないか

- ❌ Lab 1 (Agent Skills を自作する練習): スラッシュ コマンドに頼らず自分で書く価値がある。
- ❌ Lab 1 の前: ブラック ボックス化するので、まず手動で動かして理解する。

## カスタマイズ

独自のサブエージェントやコマンドを追加したい場合:

1. **新規サブエージェント**: `.claude/agents/<name>.md` を作成。先頭の YAML フロントマターに `name` / `description` / `tools` を書く。本文に system prompt を書く。
2. **新規コマンド**: `.claude/commands/<name>.md` を作成。先頭の YAML に `description` / `allowed-tools` (任意) を書く。本文がプロンプトになる。引数は `$ARGUMENTS` で参照。
3. **既存ファイルを再利用したい場合**: 本文に `@相対パス` と書くと、その内容がインラインで取り込まれる。

詳細は Claude Code 公式ドキュメント (`https://docs.anthropic.com/claude-code`) を参照。

## 関連

- [`../CLAUDE.md`](../CLAUDE.md) — Claude Code が最初に読むエントリ ポイント
- [`../.github/copilot-instructions.md`](../.github/copilot-instructions.md) — ワークショップ全体の既定値 (CLAUDE.md が import)
- [`../kb-1.8.0/README.md`](../kb-1.8.0/README.md) — Agent Framework 1.8.1 ナレッジ ベース
- [`../docs/README.md`](../docs/README.md) — ワークショップ Lab 一覧
