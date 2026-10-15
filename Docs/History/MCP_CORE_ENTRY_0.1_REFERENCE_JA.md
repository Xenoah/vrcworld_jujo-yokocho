# TreeTopYokocho: Unity / MCP 導入・検証手順

対象: 公開済み **v2.19.0 制作ソース** と、別配布予定の **Entry Systems 0.1.0 開発版**。更新日: 2026-10-14。

この文書は Unity を操作する MCP エージェント向けです。**MCP の接続、Unity のインポート、Udon のコンパイル、実機検証、公開は別々の工程**です。実行していない工程を成功扱いにしないでください。

## 1. 最初に固定する対象と境界

- 公開済みソース: [GitHub v2.19.0 release](https://github.com/Xenoah/vrcworld_jujo-yokocho/releases/tag/v2.19.0)。VRChat ワールドの公開・実行確認済みという意味ではありません。
- リリース時のコミット: `97091c96cf66a0f67b952827a753a448768f175a`。
- 対象配布 ZIP の SHA-256: `d8699d41f30ff9edd2d172bc12f683fb07a4a6eb1e499fdc5b67c5bbeedf2036`。GitHub 自動生成の別 ZIP や個別分割 ZIP のハッシュではありません。取得物と一致しなければ停止して出所を確認します。
- core の `Assets/TreeTopYokocho/Data/WorldManifest.json` の SHA-256: `aa513b1c948ba9353a08c3d9eea6f4852f5d8ffa05715f036ea27d19f003d466`。
- Entry Systems は **未公開の追加開発版**。v2.19 の release ZIP だけには、入口広場・追加ワープ・時刻/BGM パネルはありません。この文書だけをコピーしても機能は追加されません。
- 基準は **Unity 2022.3.22f1 / VCC Worlds SDK 3.10.5 / Built-in Render Pipeline / Windows x86_64**。最新版であるという主張ではありません。URP/HDRP や Android/Quest へ自動変換しないでください。
- この制作環境に Unity はありません。core の既存 61 検査は検証済み Linux ツールチェーン上のソース検査です。新規 OS での完全再現、Unity/Udon/Shader コンパイル、ベイク、ClientSim、通信・音声・VR・FPS の証明ではありません。
- addon の構文・ソース契約・独立した Python 参照モデルの検査も実行環境の証明ではありません。再インストールの無変更動作、保存後再読込、ロールバックも Unity では未実行です。入口造形の検査は限定した身体寸法・地点によるオフライン検査であり、実アバター安全性を保証しません。

同梱の古い README/改訂記録に「未公開」など当時の記述が残る場合があります。上記 release の識別子で core を特定し、開発中 addon と混同しないでください。リリース済み原本は変更せず、作業用コピーを使います。

## 2. MCP preflight: 書き込む前に確認

1. 接続先の Unity プロセス、プロジェクト絶対パス、Editor バージョン、現在の scene パス、Git/バックアップ状態を読み取り、対象がユーザーの意図どおりか確認します。MCP のツール名・引数は接続先の実際の schema を使い、架空の操作名を生成しません。
2. Play Mode でないこと、インポート・スクリプトコンパイル・ベイク中でないことを確認します。処理中なら完了を待ち、Console を再取得します。
3. **最初の Error / Exception を保存し、未解消なら生成・ベイク・Build & Test を止めます。** ログを消して成功に見せたり、Missing Script / Udon エラーを残して次へ進めたりしません。警告は内容と判断理由を記録します。
4. VCC で Worlds SDK と UdonSharp が解決済みか確認します。古い SDK `.unitypackage` を同居させず、`ProjectSettings` / `Packages` を別プロジェクトから丸ごと上書きしません。Built-in で Render Pipeline Asset が割り当てられていないことも確認します。
5. 未保存の scene・ユーザー変更をバックアップまたはユーザー指定の場所へ保存します。保存/破棄ダイアログで勝手に「破棄」を選びません。認証、権限変更、不可逆削除、公開アップロードは導入手順の権限に含めません。
6. core と addon のファイルを同一の配布候補から揃えます。`.meta` が提供されているものは一緒に保持し、既存 GUID を再生成しません。部分的な旧版混在や、ハッシュ検査を通すための定数変更は禁止です。

### 特に注意: 8 個のメッシュ分割

`Data/GeometryShards.json` に対応する `VisualMeshes.bytes.gz.part000` ～ `part007` を **8 個とも**保持します。各ファイルのサイズ・SHA-256 と、連結 gzip の SHA-256 を manifest と照合します。

core の読込優先順位は **単体 `.bytes.gz` → 連番 `.bytes.gz.partNNN` → 非圧縮 `.bytes`**。古い `VisualMeshes.bytes.gz` が残ると、正しい 8 分割より先に読まれます。旧作業フォルダーへ無条件で重ね書きせず、クリーンな作業コピーを使ってください。由来不明の単体ファイルは退避対象を特定してから対応し、広いパスを一括削除しません。正しい連結 gzip の SHA-256 は `c5d324af8e0e5ea2ad1ddfb22fa050d24b7652cbe22d26079eb7265b807dee29` です。

## 3. 通常の Unity 導入: Python は不要

1. VCC で上記バージョンの **新規 Worlds プロジェクト**を作成します。既存プロジェクトを使う場合は複製で実施します。
2. 配布物の `Assets/TreeTopYokocho` をプロジェクトの `Assets` 配下へコピーし、インポートとコンパイルの完了を待ちます。通常導入では `Source` / 制作フォント / GLB / Blender / Python は不要です。
3. 任意の Post Processing が必要な場合のみ `com.unity.postprocessing 3.4.0` を導入します。未導入でも core を作成できます。設定失敗は Console で区別し、必要なら後述のメニュー 6 を使います。
4. `Tools/TreeTop Yokocho/1 - Build World` を実行します。これは既成 scene を開く操作ではなく、**新しい scene と生成アセットを作る操作**です。既存 scene の改造を自動移植しません。
5. 成功ログから実際の生成先を記録します。初回の基準パスは `Assets/TreeTopYokocho/Generated/World/TreeTopYokocho.unity`。再生成時は `GenerateUniqueAssetPath` による別フォルダーになるため、`World` 固定で開き直さないでください。
6. scene を開き直し、トップレベルに `TreeTopYokocho_v2` が 1 個だけ存在し、位置 `(0,0,0)`、回転 identity、scale `(1,1,1)` であることを確認します。Missing Script、ピンクの材質、壊れた参照がないことを確認します。
7. `2 - Audit Physics` を実行し、`Errors: 0` を確認します。`Build World` 自体も物理/予算監査を呼びますが、メニューが返っただけで合格とせず出力を読みます。
8. addon を試す場合は次節へ進みます。core のみなら第 5 節へ進みます。

### 実在する Editor 操作

メニューの共通 prefix は `Tools/TreeTop Yokocho/`。core クラスは `TreeTopYokocho.Editor.YokochoWorldBuilder` です。

| メニュー末尾 | public static メソッド | 注意 |
| --- | --- | --- |
| `1 - Build World` | `Build()` | 新規 scene/固有フォルダーを作成。再生成は修復の万能手段ではない |
| `2 - Audit Physics` | `Audit()` | core のレイヤー、床、壁、退出/移動先、参照を検査 |
| `3 - Show Fall Barriers` | `ShowBarriers()` | 検査用選択。壁を削除・無効化する操作ではない |
| `4 - Bake High Quality Lighting` | `BakeLighting()` | 非同期。開始ログと完了は別 |
| `5 - Bake Reflections` | `BakeReflections()` | ライトマップ完了後。各プローブの成功も確認 |
| `6 - Set Up Post Processing` | `SetupPostProcessing()` | 任意 PPS の設定 |
| `7 - Audit PC Budget` | `AuditBudget()` | core の集計。全 scene の実測性能ではない |

MCP にメニュー実行機能があれば完全なメニューパスで呼びます。直接メソッドを呼ぶ機能しかない場合も上記の実在メソッドを使い、保存確認・インポート待ち・結果確認を省きません。無人 batch mode の成功はこの文書では検証していません。

## 4. 任意: Entry Systems 0.1.0 開発版

### インストール順序

1. **統合済みの addon 一式**として `Assets/TreeTopYokochoEntrySystems` を追加します。最低でも `Editor/EntrySystemsInstaller.cs`、`Editor/EntryPlazaBuilder.cs`、`Editor/EntryAssetImporter.cs`、`Runtime`、`Data/CoreCompatibility.json`、`EntryPlaza`、`Fonts`、`Shaders`、`Textures` が必要です。未統合の作業ステージを独自に混ぜないでください。
2. コンパイル完了後、上で生成・保存した core scene を active にして、Play Mode 外で `Tools/TreeTop Yokocho/8 - Install Entry Systems (Add-on)` を実行します。
3. 実装は core manifest と 13 個の互換性対象ファイル、入口データ、scene/root、sky、文字資産を事前照合します。別版・変更済み core を拒否されたら停止し、制約を削って強行しません。
4. 正常な設計上は core の兄弟として `EntrySystems_v1` が 1 個作られ、addon 専用の `Generated/EntrySystems*` に sky 複製・材質・メッシュ・`INSTALLATION.json` が作られます。core の生成材質を clock へ直接割り当てません。
5. **インストーラーは scene を自動保存しません。** 明示的に保存し、UdonSharp をコンパイルし、Console を確認します。Unity を閉じる/scene を再読込した後もメッシュ・font・sky・Udon 参照が残ることを確認します。
6. 同じ scene でもう一度メニュー 8 を実行します。同じ完全な構成なら無変更で終了する設計です。root、controller、生成フォルダーが増えず、scene/参照が変化しないことを Unity 上で確認します。部分的・別版・重複した root は自動上書きしません。

addon クラスは `TreeTopYokocho.EntrySystems.Editor.EntrySystemsInstaller`。メニュー 8 は `Install()`、メニュー `8a - Refresh Local MP3 Playlist` は `RefreshPlaylist()`、メニュー `8b - Audit Installed Entry Systems` は `AuditInstalled()` です。いずれも prefix は `Tools/TreeTop Yokocho/`。`EntryPlazaBuilder.Build(...)` を単独で呼ぶと全体の導入手順を迂回するため、通常導入では呼びません。

### 生成される名前と結線

```text
TreeTopYokocho_v2                         ← 既存 core。名前/親/transform を変えない
EntrySystems_v1                          ← scene 直下の兄弟 root
  EntryPlaza
    StaticTimberAndSigns
    FurnitureColliders
    SystemsControlAnchor
    WayfindingWarps
      Entry_To_G0 / Entry_To_G0_SafeArrival
      Entry_To_L2 / Entry_To_L2_SafeArrival
      Entry_To_L3 / Entry_To_L3_SafeArrival
  SystemsControls
    ClockStatus / MusicStatus
    Control_0 ～ Control_5
  GlobalClock                            ← YokochoGlobalClock
  LocalBGM                               ← YokochoBgmController + 専用 AudioSource
  InstallationReceipt_<config digest>    ← インストーラー管理。手作業で偽装しない
```

| オブジェクト | target / eventName | 効果 |
| --- | --- | --- |
| `Control_0` | clock / `_PreviousHour` | 共有時刻を 1 時間戻し、手動へ |
| `Control_1` | clock / `_NextHour` | 共有時刻を 1 時間進め、手動へ |
| `Control_2` | clock / `_SetAuto` | 実際の JST ×1 へ |
| `Control_3` | clock / `_CycleSpeed` | 2 → 5 → 10 → 30 → 60 → 実際の JST ×1 |
| `Control_4` | bgm / `_ToggleMusic` | 押した本人だけの BGM 入/切 |
| `Control_5` | bgm / `_NextTrack` | 押した本人だけの次のランダム曲 |

`YokochoEntryControl.target` と `eventName` を照合します。追加のローカル API は clock の `_SetDawn` / `_SetNoon` / `_SetDusk` / `_SetMidnight` / `_ResetDusk`、BGM の `_EnableMusic` / `_DisableMusic` です。これらのプリセット用ボタンが初期配置されるわけではありません。`Owner...` は通信受信用です。UI から直接呼ばず、`SetOwner` を追加しません。

- clock: `sun` は core の既存 `BlueHour_Key`。`skyMaterial` は addon 所有の複製。`initialHour=18.5`、`startInAuto=false`。既存 `Sunset_WarmFill` は Baked のため、このインストーラーでは `fillLight=null` とし動的照明に使いません。
- BGM: `musicSource` は専用 source、`playOnAwake=false`、`loop=false`、`spatialBlend=0`、`defaultOn=false`、`volume=0.22`。`CanopyWind.wav` や既存の効果音 source と共有しません。
- 各 control の collider/Udon interaction と status の TextMesh/font/material 参照を確認します。日本語は焼き込み画像、動的表示は ASCII です。

### MP3 の扱い

現在の配布 core と addon に **MP3 はありません**。空 playlist と無音は正常です。風音 `CanopyWind.wav` を曲として代用しません。

利用・配布権限のあるユーザー提供 MP3 だけを `Assets/TreeTopYokochoEntrySystems/Music` に配置し、Unity で正常な `AudioClip` として読み込まれた後に `8a - Refresh Local MP3 Playlist` を実行して保存します。他フォルダー、WAV、URL、実行時ディスク走査は playlist の対象外です。配置だけでは既存 scene の playlist は更新されません。全曲を除いた場合も 8a で空配列へ更新します。

BGM は訪問者ごとに独立し、曲・再生位置・ON/OFF は同期しません。複数曲なら直前の曲を避け、1 曲なら反復します。OFF は fade-out、ON は fade-in ですが **曲間 crossfade ではありません**。失敗曲は同じ視聴セッション内で除外し、全曲失敗で自動再試行を止める設計です。OFF → ON は再試行の操作です。

### 時刻・照明の限界

初期は **18:30 固定の手動モード**。Auto は SDK のネットワーク UTC + 9 時間を使用し、PC のタイムゾーンを使いません。加速開始時は実際の JST とサーバー時刻を共有アンカーにし、その後の加速倍率変更は表示時刻を維持します。Auto または ×1 への復帰は現実の JST に戻ります。

共有されるのはモード・手動時刻・速度・アンカー等の retained state です。途中参加者に過去の操作イベントを再生する方式ではありません。owner 退出時は最後に同期成功した状態を引き継ぎますが、**退出直前の未送信/未反映操作まで永続保証するものではありません**。連打・同時操作は間引かれる場合があります。

実際に変えるのは sky、ambient、fog の色と既存 Mixed 主方向光です。固定ベイク済みの間接光、提灯/補助光、LightProbe、反射テクスチャは再生成されません。**24 時間の完全動的 GI、天文学的な太陽軌道、時刻別ベイク切替ではありません。** 昼夜に夕暮れの残光が混在する点を実機確認します。同じ sky/RenderSettings/主光を別 script、Animator、Timeline で同時制御しないでください。

## 5. 保存 → コンパイル → ベイク → 実行

1. scene とアセットを保存し、Unity の C# / Shader / UdonSharp コンパイルを完了させます。UdonSharp のコンパイル操作は実際の SDK UI/ツールを確認して使います。
2. Play Mode へ入る前の著作時の夕暮れ状態で `4 - Bake High Quality Lighting` を実行します。`Lightmapping.isRunning=false` になるまで待ち、Console と生成ライトマップ/LightProbe を確認します。開始ログだけで次へ進みません。
3. `5 - Bake Reflections` を実行し、各プローブのテクスチャとエラー不在を確認して保存します。Play Mode 中の加速時刻や手動で変えた時刻を誤って基準ベイクにしないでください。
4. `2 - Audit Physics`、`7 - Audit PC Budget` の結果を保存します。正確な出力先は `Assets/TreeTopYokocho/Generated/PhysicsAudit.txt` と `Assets/TreeTopYokocho/Generated/PCBudgetAudit.txt` です。次回実行で上書きされるため証跡は別保管します。
5. addon がある場合は `8b - Audit Installed Entry Systems` を実行し、`Assets/TreeTopYokochoEntrySystems/Generated/EntrySystemsAudit.txt` の `Failures: 0` を確認します。**2/7 の対象は core** で、addon のメッシュ/材質費用も core 集計に入りません。8b は結線・3 ワープ到着点・操作前立位・4 スポーンを、各地点の 17 床レイと半径 0.325 m / 高さ 2.2 m の collider 身体範囲で検査し、addon 三角形/renderer 数も記録します。**visual-only geometry、連続導線、実アバター、Udon/通信、ベイク、性能は検査しません。** authored 配置の全三角形オフライン検査と、第 6 節の実行・全 scene 実測を別途必要とします。8b は代表的な時刻/BGM 状態文字を一時設定し、短い文字列と長い文字列の bounds 更新差を確認した上で、予約した表示範囲への収まりも検査します。元の表示は finally で戻します。bounds が同期更新されない場合は失敗として停止し、Editor の更新後に実際の表示を確認してください。この検査は全状態・全言語・両眼での可読性保証ではありません。8b 自体も本制作環境では未実行です。
6. Play Mode / ClientSim で基本動作を確認し、終了後に不要な runtime 状態を保存しないこと、scene 再読込で初期値に戻ることを確認します。ClientSim の成功を VRChat 通信試験の代用にしません。
7. SDK Builder の **Windows x86_64 Build & Test** を実行します。これは公開アップロードとは別です。正常に参加できるまでビルド成功だけで完了にしません。
8. 下記の実クライアント試験を実施し、実測結果を残します。**Build & Publish、既存 world ID の変更、公開 release の差替えは、この手順から自動実行しません。**

## 6. 受け入れゲート

各行を `PASS / FAIL / NOT RUN / BLOCKED` のいずれかで記録し、ログ・scene パス・環境を添えます。チェックなしは未実施です。

### A. 導入・再読込

- [ ] core と addon のバージョン/ハッシュを記録。Console の実行を妨げる Error/Exception は 0。
- [ ] root は各 1 個。core の形状・49 席・既存移動先・光源数/設定が導入前後で変わらない。addon に新しい light/station はない。
- [ ] clock は 1 個、BGM は 1 個、操作ボタンは 6 個、追加ワープは 3 個。全参照が保存・再読込後も有効。
- [ ] menu 8b が実際に終了し、`EntrySystemsAudit.txt` が今回の対象 scene の結果で `Failures: 0`。限定された静的 collider 検査と理解し、以下の歩行試験を省略しない。
- [ ] 2 回目の同一インストールで重複や無断置換が起きない。差分/不完全構成では停止する。失敗時の検査は使い捨てコピーで行い、core と既存資産が残ることを確認。
- [ ] 初期 18:30 は既存夕景と一致。BGM は OFF。controller 無効化で元の sky/ambient/fog/主光に復帰し、再有効化も正常。

### B. 移動・入口の安全性

- [ ] 4 スポーン、既存 49 席の着席/退出、既存 12 個の階移動、階段・端部・落下復帰を確認。小柄/長身、Desktop/VR、room-scale を分けて記録。
- [ ] 入口看板、ベンチ、切株卓の collider が通路・スポーン・ボタン到達を塞がず、頭/胴体/手の余裕がある。丸太ベンチは追加 Station ではない。
- [ ] `Entry_To_G0` → Unity `(-16, 0.08, -18.55)`、`Entry_To_L2` → `(-16, 140.08, -18.55)`、`Entry_To_L3` → `(-16, 146.08, -18.55)` の安全到着点を確認。元データは Z-up、Unity 変換は `(x,z,y)` なので軸を取り違えない。
- [ ] ワープ到着先に床・頭上余裕があり、復帰参照は既存 `YokochoSafety`。連打、着席中のワープ、ワープ直後の落下/Respawn を確認。移動拒否時に誤った階が復帰先にならない。
- [ ] 入口文字・操作面が近距離/立位/両眼で読め、背面透け、z-fighting、手の届かなさ、既存導線の遮断がない。

### C. 時刻の実通信

- [ ] **同一 instance に最低 2 クライアント**で参加し、異なる参加者から手動 ±1、Auto、2/5/10/30/60 倍を操作。mode・目標時刻・進行が一致する。
- [ ] 00:00 跨ぎ、倍率の連続変更、Auto/×1 へ戻した時の現実 JST、同時押し/連打を確認。視覚の短い補間差と、同期不良を区別。
- [ ] 各 mode の変更・同期後に途中参加者を追加する。3 台目または非 owner の再参加で retained state を検証し、初期 18:30 に戻らない。
- [ ] 実行 OS のタイムゾーンが異なる 2 台で Auto を比較し、信頼できる現在 JST と照合。Editor 内だけの時計で合格にしない。
- [ ] 加速中に owner が退出し、後継 owner が既存アンカーを保ち、操作を継続できる。master であることを権限条件にしない。
- [ ] 操作直後/送信待ち/不良回線時の owner 退出と、controller の無効/再有効を試す。最後に同期した snapshot までしか保証しない制限を記録。

### D. BGM の局所性と失敗系

- [ ] 空 playlist で ON/OFF/Next を押しても無音・例外なし。`NO MP3` 表示があり、風音は従来どおり。
- [ ] 試験用コピーで権利確認済み MP3 を 1 曲、2 曲以上にして 8a を実行。単曲反復、ランダム、直前曲回避、音量、fade、Next を確認。試験音源を無断で配布物へ混ぜない。
- [ ] A の ON/OFF/Next が B に影響せず、途中参加者の BGM は初期 OFF。時刻の共有範囲と音楽の局所範囲を混同しない。
- [ ] 空/null/長さ 0、source 未設定、再生開始に失敗する clip、全曲失敗をテストコピーで確認。無制限の即時再試行・例外連発がなく、OFF → ON で再試行できる。
- [ ] Music から曲を全除去後に 8a を実行して空配列へ戻し、保存/再読込後も古い曲が残らない。

### E. 見た目・性能・サイズ

- [ ] 夕暮れ/昼/夜明け/深夜を実クライアントと VR 両眼で比較。固定ライトマップ/Probe の残光、暗すぎる顔/看板、眩しさ、点滅/片目欠けを確認。
- [ ] 全 scene の CPU/GPU フレーム時間、draw calls/SetPass、VRAM、負荷の高い眺望、想定人数/アバター条件を実測。renderer 数やソース三角形数を FPS と言い換えない。
- [ ] SDK の実際の Windows `.vrcw` / AssetBundle バイト数を記録。**約 50 MB は目標**であり、ソース ZIP/GLB/gzip/texture RAM のサイズでは判定しない。

## 7. 失敗時の停止・復旧

- **メニューがない / `EntryPlazaBuilder` が見つからない:** Console の最初の compile error と addon の欠損を確認。統合済み配布を揃えるまで停止。メニュー番号を推測して別操作を呼ばない。
- **sky/font/ラベル preflight 失敗:** 対象資産の import 完了と提供された importer を確認。status font は静的 ASCII atlas、専用 shader は `TreeTopYokochoEntrySystems/DepthTestedStatusText`。OS 日本語 font への置換や core sky の直接流用で回避しない。
- **互換性/receipt 不一致:** 対象と差分を報告し、バックアップを保持。`EntrySystems_v1` を勝手に削除してやり直さない。承認された修復またはクリーンな v2.19 コピーに切り替える。
- **導入途中の例外:** 実装は、その呼出しで作った root/固有生成フォルダーだけを片付け、元 sky 参照に戻す設計。実際に戻ったか scene・資産を確認し、不明なら再実行せず証拠を残す。
- **元に戻したい:** まず Play Mode を終了し、保存済みの導入前 scene/プロジェクトへ戻す方法を優先。使用中 scene の復旧を、無差別な `Generated` 削除で行わない。実行中に clock が復元するのは Start 時の scene 状態であり、インストール前 scene を自動復元する機能ではありません。
- **core 再生成:** 新しい scene には addon は引き継がれません。新 core の確認後にメニュー 8 を再適用し、保存/結線/ベイク/実行試験をやり直す。古い addon scene object を別 scene へドラッグして接ぎ木しない。
- **ベイク/Build が長い:** 処理状態と最新ログを確認して待つ。開始済みの処理を重複実行しない。停止/中断が必要なら対象と影響を明示し、元データを保持する。

## 8. Source 再生成は別の作業

通常導入は同梱の焼き込み済み日本語 atlas を使い、制作フォントのインストールも画像再生成も不要です。

core の `Source/fonts` には改名済み subset 7 本、元の 4 family に対応する OFL 文書 3 個と、制作専用の full TTF 3 本が含まれます。これらを丸ごと Unity `Assets` へコピーしません。一方、addon は **Assets 内に 64,256 byte の改名済み Klee One 由来 ASCII font と OFL** を意図的に同梱します。これは動的 status 用であり、core の「制作 font は Source のみ」と区別します。日本語静的ラベルは画像です。

厳密な旧版印字再現にはさらに次の **同一バイトの Noto TTC 2 本**が必要です。同梱 subset/TTF とは別物で、配布物には含まれません。

| historical font | 必須 SHA-256 |
| --- | --- |
| `NotoSerifCJK-Bold.ttc` | `1505ee3b9c0890fae6302ee0e9c6fd74d690f4a55a6ace1d9944f3f6352d622d` |
| `NotoSansCJK-Regular.ttc` | `b76b0433203017ca80401b2ee0dd69350349871c4b19d504c34dbdd80541690a` |

詳細は `Source/testdata/shopfront_print/README.md` と `fixture_manifest.json`。当該バイト列を新規 OS で確実に取得する手順は未解決です。単に最新版 `fonts-noto-cjk` を入れれば一致するとは保証できません。欠損/不一致なら明確に失敗として報告し、別 font へ置換、期待 hash 更新、テスト skip で合格にしません。

`Source/build_world.py` / `pack_geometry.py` は生成物を変える制作操作です。Unity 導入の修復として無断実行しないでください。Source 再生成を依頼された場合だけ、別コピー・固定依存・正しい font で実行します。既存 61 検査の結果は fresh-OS 再現成功を意味しません。

## 9. 完了報告に必要なもの

`MCP_UNITY_VERIFICATION_TEMPLATE_JA.md` を作業コピーへ記入し、最低限次を報告します。

- 対象 commit/ZIP/manifest、addon バージョン、Unity/SDK、project/scene パス。
- 実行したメニュー、保存/再読込、Console、Udon、ベイク、Build & Test の結果と証跡。
- core 監査と addon/全 scene 検査の区別。実通信クライアント数、途中参加/owner 退出、音源数、実測性能/容量。
- `NOT RUN` / `BLOCKED` の項目、停止した正確な操作、残る最小の次の手順。
- 公開操作の実施有無。実行しなかったものを「確認済み」「公開済み」と書かない。

参照: `RuntimeSystems.md`（runtime 契約）、`SETUP_JA.md`、`ACCEPTANCE_JA.md`、`UnityAudit.md`、`Data/CoreCompatibility.json`、`EntryPlaza/Data/EntryPlaza.json`。API/生成名は 2026-10-14 の統合担当確認済みソースに対応し、addon は依然開発版です。ソース変更後は文書と再照合してください。
