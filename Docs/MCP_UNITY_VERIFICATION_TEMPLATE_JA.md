# Unity / MCP 検証記録

記入規則: `PASS / FAIL / NOT RUN / BLOCKED`。実際に実行した操作だけを記入する。開始/完了を分け、未確認値を推測しない。初期値はすべて未実施。

## 対象

- 実施日時 / 担当:
- core release / commit:
- 統合 package version / commit:
- 配布 ZIP 名 / SHA-256:
- WorldManifest SHA-256:
- addon バージョン / 配布物または commit / 変更内容:
- Unity / Worlds SDK / UdonSharp:
- OS / build target / render pipeline:
- MCP 接続先 project 絶対パス:
- 生成した scene パス / GUID:
- addon 生成先 / INSTALLATION.json:
- OriginalPbrPlan SHA-256 / OriginalPbr_v1 receipt GUID:
- 導入前バックアップ / 差分:

## 導入・コンパイル

| 工程 | 結果 | 証跡・備考 |
| --- | --- | --- |
| ZIP / core / 8 shards の同一性 | NOT RUN | |
| compile/import 待機と Console 確認 | NOT RUN | |
| 標準 menu 0 初回生成・同一 scene 統合 | NOT RUN | core・OriginalPbr_v1・EntrySystems root が各1個 |
| menu 0 保存後再読込・再実行 | NOT RUN | root / material / collider / interaction 数と GUID 不変 |
| 既存 v2.19 core に menu 0 で追加 | NOT RUN | 元 scene をコピーして実施 |
| 旧 core-only menu 1 の診断 | NOT RUN | 完成導入の代わりには使わない |
| 旧 addon menu 8 の診断 | NOT RUN | 通常導入は menu 0 |
| 保存後再読込・Udon 参照保持 | NOT RUN | |
| menu 8 再実行で無変更 | NOT RUN | |
| menu 0a 自作 PBR 結線監査 | NOT RUN | 31定義、実使用30材質、旧 scan 参照0 |
| 16 map の normalGL / ARM / sRGB / repeat / BC5/BC7 | NOT RUN | 入力 hash と Unity importer、見た目を別々に検査 |
| 旧材質と clone の非対象property一致 | NOT RUN | shader・UV scale/offset・tint・keywords・render state |
| 4系列材質の近接／斜光／反復／stereo | NOT RUN | source Blender proof は Unity shader の代用ではない |
| キャンセル／保存しない／別 scene の停止 | NOT RUN | 元編集が勝手に保存・破棄されないこと |
| 不完全/異版 root の停止、失敗時復旧 | NOT RUN | テスト用コピー |
| C# / UdonSharp / Shader コンパイル | NOT RUN | 各々分けて記録 |
| Console Error/Exception 数 | NOT RUN | 最初のエラー全文と stack trace |
| 警告の判断 | NOT RUN | 無視した理由も記録 |

## ベイク・実行・安全

| 工程 | 結果 | 証跡・備考 |
| --- | --- | --- |
| menu 4 開始 / 完了 / lightmap・LightProbe | NOT RUN | |
| menu 5 各 reflection の完了 | NOT RUN | |
| menu 2 core PhysicsAudit | NOT RUN | 既存 core の監査。別途 entry 導線検査も行う |
| menu 7 core PCBudgetAudit | NOT RUN | addon 費用は含まない |
| menu 8b addon EntrySystemsAudit | NOT RUN | 結線/限定立位 collider 検査。導線/実機は別 |
| ClientSim / Play Mode | NOT RUN | 実通信の代用ではない |
| Windows Build & Test / 実際の入室 | NOT RUN | |
| 全スポーン / 49 席 / 既存 12 移動ボタン | NOT RUN | |
| 入口導線・家具衝突・3 追加ワープ | NOT RUN | 到着先、着席中、連打、復帰 |
| Desktop / VR / 小柄・長身 / room-scale | NOT RUN | |
| 昼・夜明け・深夜・夕景の両眼表示 | NOT RUN | 固定ベイク残光を含む |

## 通信・音声

- 実クライアント数 / テスト instance:
- OS タイムゾーン / 比較した現在 JST:
- MP3 試験曲数 / 権利確認済みか / 配布物に含めたか:

| ケース | 結果 | 証跡・備考 |
| --- | --- | --- |
| 手動 ±1 / 00:00 跨ぎ / Auto JST | NOT RUN | |
| 2/5/10/30/60 倍 / 倍率変更 / ×1 復帰 | NOT RUN | |
| mode ごとの途中参加 / 同時押し | NOT RUN | |
| owner 退出 / 後継 owner / 時刻継続 | NOT RUN | |
| 未送信操作直後の退出 / 不良回線 | NOT RUN | 最終同期 snapshot の制約 |
| clock 無効・再有効 / baseline 復帰 | NOT RUN | |
| BGM 初期 OFF / 空 playlist / Next | NOT RUN | |
| 1 曲反復 / 複数曲ランダム / fade | NOT RUN | |
| A の操作が B に影響しない | NOT RUN | |
| source 不在 / 失敗曲 / 全曲失敗 | NOT RUN | |
| menu 8a 更新 / 全曲除去後の空配列 | NOT RUN | 保存・再読込も確認 |

## 実測・判断

- 全 scene の CPU/GPU frame time / draw calls / SetPass / VRAM:
- 測定機材、表示解像度、地点、参加人数、avatar 条件:
- SDK Windows 出力名 / バイト数:
- 公開操作: **未実施**（実施した場合のみ権限と対象を記録）
- 受け入れ判断: **未判定**
- 残る FAIL / NOT RUN / BLOCKED:
- 正確な停止操作 / 対象 / 原因 / 結果が不明か:
- 次の最小手順:
- ログ/画像/差分の保存先:

ソース検査や Blender 画像だけで Unity/VRChat 実行欄を PASS にしない。renderer 数を draw calls、ソース ZIP サイズを配信容量、目標値を実測値として記入しない。
