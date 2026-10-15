# 樹上横丁 v2.20.0-preview.1 統合ソース: Unity / MCP 手順

更新: 2026-10-15。**通常の入口は `Tools/TreeTop Yokocho/0 - Build or Complete Preview`。** MCP接続・Unityインポート・Udonコンパイル・ベイク・実機試験・公開は別工程です。この文書はどの実行工程も成功したと主張しません。

## 1. 対象を取り違えない

配布パッケージはv2.20.0-preview.1、保存しているcore形状・manifestはv2.19.0、Entry Systemsは0.1.0です。旧coreのmanifest版数を上書きして同じ検証と偽りません。

- 基準: Unity2022.3.22f1 / VCC Worlds SDK3.10.5 / Built-in / Windows x86_64。
- 旧core release: https://github.com/Xenoah/vrcworld_jujo-yokocho/releases/tag/v2.19.0
- core manifest SHA-256: `aa513b1c948ba9353a08c3d9eea6f4852f5d8ffa05715f036ea27d19f003d466`。
- この版のAssetsは `TreeTopYokocho`、`TreeTopYokochoEntrySystems`、`TreeTopYokochoOriginalPbr`、`TreeTopYokochoIntegration` の4フォルダーを一式で使います。
- 新しいPBR planが未審査／hash不一致なら導入は停止します。検査を通すために定数だけ書き換えないでください。
- `Source/TreeTopYokocho.glb` は旧材質を含むcore履歴データです。単独GLB読込や旧source builderだけで統合完了とはしません。自作材質と入口はメニュー0から追加します。
- この制作環境ではUnity/UnityHub実体が見つからず、Unity/Udon/Shader、音声、network、VR、bake、FPSは未実行です。ソーステストPASSと混同しません。

## 2. 書き込む前の確認

1. MCPの実在ツールで接続先Unityプロセス、プロジェクト絶対パス、Editor版、active scene、console、作業差分を確認。架空のMCPツール名を作りません。
2. Play Modeでなく、import/compile/bake中でもないことを確認。最初のError/Exceptionを記録し、解決前に次へ進みません。
3. VCCでSDK/UdonSharpが解決済み、Built-inであることを確認。URP/HDRP/Questへの自動変換や古いSDK unitypackageの混在はしません。
4. 既存プロジェクト・sceneは複製またはバックアップ。Packages/ProjectSettingsの一括上書き、未保存変更の破棄、認証・権限変更はしません。
5. 同じ配布物のAssets全体を `.meta` とともにコピー。既存GUIDを再作成しません。正常な完全インポート後、単独sceneで操作します。
6. `Data/GeometryShards.json` と8個の `VisualMeshes.bytes.gz.part000` ～ `part007` を検査。単体gzipがあればそちらが先に読まれます。正しい単体連結gzip SHAは `c5d324af8e0e5ea2ad1ddfb22fa050d24b7652cbe22d26079eb7265b807dee29`。古い単体ファイルを放置しない一方、由来不明のファイルを一括削除しません。

## 3. 標準導入はメニュー0だけ

`Tools/TreeTop Yokocho/0 - Build or Complete Preview`

実在するpublic staticメソッド: `TreeTopYokocho.Integration.Editor.IntegratedPreviewBuilder.BuildOrComplete()`。

- source/map/font/shaderの事前検査を先行します。
- 保存確認をキャンセルすれば停止。Don't Save後もdirtyが残る場合は、それを後で勝手に保存せず停止します。明示保存してから再実行します。
- 対応coreがなければ旧builderで新しいsceneを生成。対応coreが既にある場合は同じsceneを使います。複数coreや複数loaded sceneは停止。
- その回のcore PhysicsAuditに現在のUTCと `Errors: 0` があることを確認します。旧coreのauditはerrorをlogするだけなので、統合層が明示的に失敗を止めます。
- 入口のsource／既存scene参照を確認後、自作PBRの材質cloneとEntry Systemsを追加します。
- 完全な既存導入なら新規root/materialを増やさず監査します。部分導入・他版・参照不整合は勝手に消さず停止します。
- PBR監査・入口監査に合格してからsceneを保存します。途中失敗は未成功です。coreを残し、失敗した導入層の自分が作ったアセットだけがrollback対象です。

初回のcore生成先は通常 `Assets/TreeTopYokocho/Generated/World/TreeTopYokocho.unity`。既存生成物がある場合は固有名になるため、成功ログの実際のパスを記録します。

期待するscene直下:

- `TreeTopYokocho_v2`: v2.19 core。49席、374灯、既存12lift。
- `OriginalPbr_v1`: 自作材質導入receipt。31定義のうち30active、Mossは未使用。
- `EntrySystems_v1`: EntryPlaza、SystemsControls、GlobalClock、LocalBGM。

旧 `1 - Build World` はcore-onlyの履歴再現／診断用です。単独実行を統合完了と呼びません。新しいcore sceneを作ったら、そのsceneでメニュー0を実行します。古いsceneのaddon objectsを新しいsceneへそのままコピーしません。

## 4. 保存・再読込・再実行の検証

以下は**必須の未実施Unity検証**です。source設計があることを実行PASSの代わりにしません。

1. UdonSharpをコンパイルしConsoleに影響のあるerrorがないこと。
2. 保存・scene再読込・Unity再起動後もmesh/font/sky/material/Udon参照が残ること。
3. 再びメニュー0を実行し、root数、材質参照、Generatedディレクトリ数が増えないこと。
4. `Tools/TreeTop Yokocho/0a - Audit Integrated Original PBR` を実行。publicメソッド `OriginalPbrInstaller.Audit()`。全active core rendererから旧PBR scan参照が除かれ、shader・tint・UV倍率などが維持されていること。
5. `Tools/TreeTop Yokocho/8b - Audit Installed Entry Systems` を実行。入口の配置・warp参照・文字bounds等を確認。文字boundsは短時間内容を差し替えてfinally復元し、監査reportを書きます。実VRの見え方まで保証しません。

## 5. MP3と24時間時計

MP3は未同梱です。再配布権限が明らかな曲だけを `Assets/TreeTopYokochoEntrySystems/Music` に追加し、`Tools/TreeTop Yokocho/8a - Refresh Local MP3 Playlist` (`EntrySystemsInstaller.RefreshPlaylist()`) を実行します。空なら無音とNO MP3表示が正解です。風WAVをBGMへ流用しません。

BGMは操作した本人だけに作用し、初期OFF。ON/OFF/次曲・フェード・無効clip・全曲失敗・OFF→ON再試行を試験。複数曲時は直前曲を避けてrandom選択する方式で、全曲一巡保証やcrossfadeではありません。

時刻は共有。初期18:30手動、±1h、JST Auto、2/5/10/30/60倍、実JST1倍に戻る操作を2client以上で試験。深夜跨ぎ、途中参加、owner退出、連打、送信中の退出、異なるOS timezoneを含めます。未送信の最後のcommandはowner退出で失われる可能性があります。

時刻変更はsky／方向光／fog／環境色を動かす芸術的cycleです。既存baked GI・店舗照明・probe・反射画像は変わりません。正午・夜明け・深夜・夕景で固定照明の残り方を確認し、完全動的再ベイクと呼びません。

## 6. 見た目・安全・性能の試験

- 8店舗、主看板／立体看板、静的3旗、店舗別配色、布／和紙／釉薬等のshaderを確認。
- 自作4PBR系統について近距離・中距離・繰返し・斜光・実UV倍率・normal向き／ARM／parallaxを確認。sourcePNGの寸法はGPU解像度や実メモリを意味しません。岩albedoのStandalone上限は従来どおり1024、他albedo2048、data maps1024。
- 木の茶房S05は屋根陰の内向き進入で紋章が読みにくい既知制限があるため、近接だけで合格にしません。
- 4spawn、49席の出入り、既存12lift、入口3warp、階段・床端・身体サイズ・room-scale移動・落下復帰を確認。
- 入口warpのUnity到着点は(-16,0.08,-18.55)、(-16,140.08,-18.55)、(-16,146.08,-18.55)。木札はinteractのみで、自動trigger teleportではありません。
- `4 - Bake High Quality Lighting`と`5 - Bake Reflections`は非同期の開始と完了を区別。ベイク成功、SDK Build & Test、stereo、実機FPS、実ビルド容量を別記録にします。

## 7. 完了表現

未実施欄は未実施のまま残します。ソースの構文検査、Python参照モデル、Blender画像、geometry検査だけでは「Unity動作確認済み」「VRChat完成」「アップロード済み」「50MB達成」「FPS達成」と記載しません。

過去のcore／入口単独手順は `History/MCP_CORE_ENTRY_0.1_REFERENCE_JA.md` に保存しています。旧手順は今回の標準入口を置き換えません。
