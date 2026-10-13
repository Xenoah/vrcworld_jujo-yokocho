# 未公開チェックポイント v2.1.0

この記録は改修前の作業記録です。v2.1.0としてのリリース／pushは行っていません。現在の結果はREADMEの最新版リンクを参照してください。

# v2.1.0-source-preview — Windows50 制作データ

Unity / VRChat 実機検証前の **ソース・プレビュー版** です。Windows向けのワールド制作データを収録しています。検証済みの .vrcw は含みません。

## 内容
- 巨木の樹上横丁、8店舗・49席、環状路、4デッキ、3組の階段
- 湖岸720棟、遠景6,400本の森林、山並み、橋、寺院
- PBR古材・樹皮・岩、瓦、暖簾、提灯、料理と店内道具
- 両面の葉と風、水面、湯気、夕景の空。Windows Built-in用シェーダー5本
- 外周・内周・階段側面の透明な落下防止Collider、安全復帰と階移動操作
- 160提灯をベイク主体へ変更、BC7/BC5圧縮、ライトマップと反射Probeの予算設定
- 2,387,276描画三角形。既存高精細版の3,994,476から40.24%削減

## 確認済み
- 734本の床検査、3,190本の壁交差検査、49席退出先、12移動先、全5階層の床連続性
- この時点では元の衝突データと一致。その後の独立レビューでR03/W05の横断障害を発見し、v2.2で修正
- C#4本の構文解析、テクスチャとGLBの整合、7分割の圧縮メッシュ復元
- 同じGLBを使ったBlenderレンダー。画像は標準OIDNノイズ低減済み、未加工レンダーはローカル保管（Gitには含めない）

## 未確認
Unity C# / UdonSharp / Shaderコンパイル、ライトベイク、Unity Physics Audit、ClientSim、Windows Build & Test、VR・複数人での挙動とFPS、VRChat公開アップロード。

**約50MBは最終Windowsワールドの目標です。実際のビルド容量は未測定です。ソースZIPやUnitypackageの容量と同じ意味ではありません。**

導入は [SETUP_JA.md](SETUP_JA.md)、実機確認は [ACCEPTANCE_JA.md](ACCEPTANCE_JA.md)、修正詳細は [UnityAudit.md](UnityAudit.md) を参照してください。

## 現バージョンの画像

以下はBlenderの形状・材質プレビューで、UnityまたはVRChatの実機スクリーンショットではありません。照明、空、霧、後処理はプレビュー用のため最終ベイクと異なります。

![樹上横丁の全景 — Blenderプレビュー](../Preview/Blender_overview.png)

![炭火 梢の店先 — Blenderプレビュー](../Preview/Blender_alley.png)
