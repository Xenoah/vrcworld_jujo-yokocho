# Unity / Udon / Windows PC 監査変更

2026-10-13。対象は Unity Built-in Render Pipeline の VCC Worlds プロジェクトです。Unity Editor / VRChat クライアントはこの環境で実行していません。

## 修正内容

- **圧縮メッシュ入力**: `VisualMeshes.bytes.gz` / `CollisionMeshes.bytes.gz` を優先し、存在しない場合は `.bytes.gz.part000` から連番の分割ファイル、最後に従来の `.bytes` を読みます。分割入力は各4MiB以下・欠番なしを検査し、結合後に展開します（`.meta` は除外）。展開後の JYWM v1 形式は変更していません。シーク不可の GZipStream に対応し、名前長、頂点・UVの有限性、三角形インデックス、末尾データを検査します。圧縮入力は Editor 用であり Udon が実行時に展開する方式ではありません。
- **描画負荷**: 店舗・階段・設備の提灯ライトと暖色の補助光を Baked に変更。リアルタイム影は Mixed の主方向光1個に限定。Editor の影距離65m・2 cascades・pixel light count 2、遠景の影投射無効を設定します。実際の VRChat 描画設定や FPS はクライアント側の条件にも依存します。
- **サイズ設定**: Windows Standalone の色・ARM等は BC7、法線は BC5。近景の色・看板は最大2K、補助マップと地形は最大1K。Read/Write を無効化し、同じテクスチャの重複再インポートを回避します。BC5 / BC7 では Crunch を使いません。
- **ベイク設定**: 12 texels/m、最大2048、圧縮した非指向性ライトマップ、間接256 samples、反射プローブ128px。細かい柵・提灯には低い lightmap scale を設定。非指向性はサイズを優先する設定で、指向性ライトマップより法線マップへのベイク光の応答が簡略になります。法線と反射自体は維持します。
- **シェーダー**: 使わない Normal / ARM / Parallax サンプリングをローカルキーワードで除外。葉の alphaClip と tint alpha を反映。Steam / Sky の頂点出力初期化と Shader Model 3.0 指定を明示。水・風で動く葉は static occluder として扱いません。
- **透明な落下防止壁**: 厚みを持つ衝突形状を配置と階高に合わせて再生成。Renderer / MeshFilter なし、非凸・非トリガーの静的 MeshCollider、Interactive layer 8 を使用し、壁にステッカーが浮くことも避けます。衝突メッシュの座標は圧縮しません。
- **安全な復帰処理**: 地面端を避けた地点だけを記録する4方向の床チェックを追加。着席中は落下復帰を一時停止し、退出地点を記録します。昇降口は移動後の実到着を確認してから復帰地点を更新するため、Station が移動を拒否しても別階が復帰先になりません。ローカル処理、4Hz、ネットワーク同期なしです。
- **生成時の堅牢性**: SDK の Station mobility を列挙型名で設定。必須配列を確認し、任意の PPS v2 設定失敗がワールド本体の保存を妨げないようにしました。

## Unity 内で実行できる検査

`2 - Audit Physics` は PlayerLocal と床・壁のレイヤー衝突、壁の有効性、壁の両方向レイ、床、スポーン、全座席退出先、全移動先と復帰参照を検査します。結果は生成フォルダの `PhysicsAudit.txt` に出力します。

新しい `7 - Audit PC Budget` はシーンの三角形、Renderer / material 数、ライト種別、ライトマップ数、読み込まれたテクスチャのメモリ、Shader エラー、Windows ターゲット、未ベイクの有無を記録します。Renderer 数は draw call 数ではありません。1.5M三角形・400Renderer はこの制作物の見直し目安であり、SDK の制限値ではありません。

## 今回実行した範囲

- 変更した C# 4ファイル: tree-sitter による構文解析 PASS
- Shader 5ファイル: 括弧と CGPROGRAM / ENDCG の整合のみ確認
- JYWM の圧縮/非圧縮入力、名前とメッシュヘッダの静的確認。7分割の描画入力を順に結合・gzip展開し、元バイナリとの完全一致を確認（C#ローダーの実行ではありません）
- Unity / VRChat 公式資料で利用APIと制約を確認

**Unity C# コンパイル、UdonSharp変換、Shader コンパイル、ベイク、Unity Physics Audit、ClientSim、Windows SDK Build & Test、VR実機・複数人性能測定は未実施です。** 構文解析やオフライン幾何検査をこれらの代わりとして扱わないでください。

## 最終受け入れ手順

1. VCC の対応 Unity / Worlds SDK でインポートし、Console のコンパイルエラーを解消
2. メニュー1で生成、メニュー2で物理検査
3. メニュー4のベイク完了後にメニュー5の反射ベイク。提灯が Baked のため、この工程を省くと意図した夜景照明にはなりません
4. メニュー7で予算を確認後、Windows x86_64 の SDK Build & Test
5. 全階の階段、開口部、崖際、連打した昇降口、着席/退出/座席切替、着席中の昇降口、Respawn、小柄/長身アバター、VR room-scale 移動を確認
6. 実際の SDK 出力サイズと VR フレーム時間を記録。**約50MB は目標であり測定結果ではありません。** ソースZIP、gzipメッシュ、テクスチャRAMの大きさからアップロード容量を断定しないでください

## 参照した公式資料

- [VRChat World optimization](https://creators.vrchat.com/worlds/submitting-a-world-to-be-made-public/)
- [VRChat layers / physics / stickers](https://creators.vrchat.com/worlds/layers/)
- [VRC Station](https://creators.vrchat.com/worlds/components/vrc_station/)
- [Player positions / TeleportTo](https://creators.vrchat.com/worlds/udon/players/player-positions/)
- [UdonSharp supported features](https://creators.vrchat.com/worlds/udon/udonsharp/)
- [UdonSharp editor scripting](https://creators.vrchat.com/worlds/udon/udonsharp/editorscripting/)
- [Unity 2022.3 BC5](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/TextureImporterFormat.BC5.html) / [BC7](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/TextureImporterFormat.BC7.html)
- [Unity lightmap directionality](https://docs.unity.cn/Documentation/ScriptReference/LightingSettings-directionalityMode.html)
- [Unity secondary UV generation](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Unwrapping.GenerateSecondaryUVSet.html)

## v2.6 高度・雲海

- 近景の反射Probe5個は高度+100mへ移動、地上Probeは固定。樹冠展望台にも128pxの専用Probeを追加（計7個）
- 雲は単一パスのpremultiplied透明材質。static batching/GI/影/Probeを無効にし、最大±0.15mの頂点変位ぶんculling boundsを拡張
- マニフェストの高度をスポーン・カメラ・全座席・昇降口へ適用。復帰下限は地上基準の-8mを維持
- 全C#の構文解析は実行。Unity/Udon/Shaderの実コンパイルは未実行
