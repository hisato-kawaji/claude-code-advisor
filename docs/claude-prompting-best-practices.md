# Claude Code の改善アドバイスの考え方

確認日: 2026-10-31。アドバイスは対象として選んだ履歴の抜粋に限られます。履歴に見えない検証や設定が存在しないとは判断できません。

- Claude が自力で知ることのできない要件や制約を伝え、作業に合った検証手段を用意する。単純な作業に詳細な計画やテストを一律に要求しない。
- CLAUDE.md、対象を絞った rules、skills、hooks、MCP、subagents は役割が異なる。必要な場合に選択し、未使用を減点しない。
- cache read の累計はコンテキストの占有率ではない。高消費や複数回の指示だけでは、無駄・失敗・原因を断定できない。
- 履歴の時間順に基づく帰属は推定であり、並列作業や取得漏れを含め完全な再構成ではない。
- AIが出す意見は確認候補であり、成果の評価や原因を証明するものではない。外部送信前に対象を確認する。

参照: [公式ベストプラクティス](https://code.claude.com/docs/en/best-practices)、[拡張機能](https://code.claude.com/docs/en/features-overview)、[モニタリング](https://code.claude.com/docs/en/monitoring-usage)。詳細な見直し方針は [修正提案](claude-code-modernization-proposal.md) を参照。
