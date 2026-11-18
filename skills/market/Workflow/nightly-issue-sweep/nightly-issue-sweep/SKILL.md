---
name: nightly-issue-sweep
description: 夜間など定期的に Issue / PR / コードベースを棚卸しし、保守系 Issue や opencode 粒度に分解できる task を起票する 2 段階の skill。Phase 1 で claude-code が 1M context でリポジトリ全体を走査して候補を出し、Phase 2 で codex が候補を整理 / 重複排除 / 起票する。
---

# nightly-issue-sweep

リポジトリの「埋もれた負債 / 既存 Issue の停滞 / opencode に分解できる小粒 task」を定期的に拾い出す 2 段階の sweep。

## いつ使うか

- launchd / cron などからの定期起動
- 人間が手動で「全体棚卸ししてくれ」と要求した場合
- Story 完了直後の余白で次の opencode 候補を仕込みたいとき

## 2 段階の役割分担

| Phase | 担当 | 役割 |
|---|---|---|
| Phase 1 | claude-code | 1M context でコードベース + 既存 Issue / PR を走査し、候補を raw リストとして出す |
| Phase 2 | codex | Phase 1 の候補を `implementation-contract` / `github-write` でフィルタ・分解・起票する |

claude-code は **判断せず広く拾う**、codex は **拾われたものから絞って起票する**。役割が混ざると重複起票や Open Questions 残りが起きる。

## Phase 1: claude-code 走査

### 入力

- 対象 repo (`gh repo view --json nameWithOwner` で確認)
- 直近の sweep 起票履歴 (重複防止)
- `github-read` で取得した Issue / PR 一覧

### 走査対象

1. **既存 Open Issue** の停滞・粒度
   - 90 日以上更新なし
   - `agent:*` 未付与 / `needs-refinement` のまま放置
   - Acceptance Criteria が抽象的で着手不能
2. **コードベースの保守系候補**
   - `TODO` / `FIXME` / `XXX` コメント
   - lint / type / 実装上のスメル (テストの skip / `any`)
   - `agent:opencode` に分解できる典型: typo / 古い参照 / 未使用 import / 文字列定数の重複
3. **PR レビューで未起票の指摘**
   - merged PR の未 resolve thread / 「あとで...」コメント
4. **ドキュメント / 正本との不整合**
   - root `AGENTS.md` / root `CLAUDE.md` / `.agents/skills` / `.claude/skills` と実装の食い違い
   - `ROADMAP.json` の epic と Open Issue の食い違い

### 出力

raw 候補リストを 1 候補 1 ブロックで出す。判断はしない。

```md
### 候補 N
- 場所: <ファイル:行 / Issue #NN / PR #NN>
- 観察: <事実だけ書く>
- 推定 lane: <opencode / codex / claude-code / 不明>
- 重複疑い: <既存 #NN / なし>
```

claude-code は `agent` ラベルを付けない / Issue を起票しない。あくまで raw リスト。

### claude-code 側の subagent 起動

Orchestra が `Agent` tool で claude-code を呼ぶ場合は `isolation: "worktree"` を必ず指定する。codex が claude CLI 経由で呼ぶ場合は default で isolated worktree。

### 落とし穴 (Phase 1)

- **拾い漏れより重複の方が安い**: 迷ったら raw リストに残す。codex が後段で潰す
- TODO 全部を取らない: ソース内の「設計判断が要る」TODO は Phase 2 で `needs-refinement` 候補
- nit / 感想 / 「将来やるかも」は除外する (codex の起票基準と整合)

## Phase 2: codex 整理 / 起票

### 入力

- Phase 1 の raw 候補リスト
- 既存 Open Issue 一覧 (`github-read` の JSON 出力)
- `implementation-contract` / `github-write` skill

### フロー

1. 重複排除: 既存 Issue とマッチする候補は破棄、または既存 Issue にコメントだけ追加
2. レーン判定: `implementation-contract` の agent 境界に従い、`agent:opencode` / `agent:claude-code` / `needs-refinement` のいずれかに振り分け
3. opencode-ready は積極的に分解: 「ついで棚卸し」を 1 Issue に詰めず、複数 Issue に割る
4. nit / 感想 / 具体 task 化できない設計相談は **起票しない**
5. 残ったものを `github-write` で起票する。nightly sweep 経由の Issue は `type:task` ではなく `type:chore` を付ける (story 配下や手動起票の実装系 task と区別する)。`needs-refinement` 候補は `type:chore` を付けず `status:needs-refinement` のみ。Goal / Scope / Acceptance Criteria / Out of Scope / Verification / Stop Conditions を本文に含める
6. 起票直後にユーザーへ報告: Issue URL / ラベル / 起票件数

### 起票時の本文に必須

- `元レビューコメント / 発見元: <URL or "nightly-issue-sweep">`
- `Refs #<親>` (該当する親 Issue / PR があれば)
- Acceptance Criteria 第三者判定可能形
- `Implementation Plan`: 修正担当 agent がそのまま着手できる具体的な作業内容
  - 変更対象のファイル / 関数 / クラス
  - 追加・変更する条件 / 分岐 / データ構造
  - 維持すべき既存仕様
  - 変更してはいけない範囲
- `Verification`: 実行すべき test / lint / build / 差分確認コマンド

`agent:opencode` Issue は特に狭く書く。期待 diff が文章 1 行で言えないもの、テスト追加・修正が必要なもの、近傍実装の理解が必要なものは `agent:opencode` にしない。

### 落とし穴 (Phase 2)

- nightly 起票で ROADMAP の epic 配下を埋もれさせない: 自動起票 Issue は PO が明示的に採用するまで `epics[].issues` に追加しない
- `agent:opencode` に「他箇所も棚卸し」を含めない: 含めるなら `needs-refinement` として codex の整理に戻す
- 1 sweep で大量起票しない: 1 回あたりの起票上限を運用上で決める (例: 5 〜 10 件)。残りは次回回し
- 「Phase 1 で出たから起票する」を反射でやらない。codex 側で必ず `implementation-contract` の agent 境界と Stop Conditions を通す

## 起動経路

定期実行は `.launchd/jobs/` / cron 等で組む。実行は次の 2 ステップ:

1. claude-code を起動: `claude` CLI に「`nightly-issue-sweep` skill の Phase 1 を実行して raw 候補リストを返せ」
2. codex を起動: `codex` CLI に「`nightly-issue-sweep` skill の Phase 2 を、上記 raw 候補リストを入力に実行せよ」

orchestrator は Phase 1 出力を Phase 2 入力にパイプする。Phase 2 でユーザー報告まで完了したら sweep 終了。
