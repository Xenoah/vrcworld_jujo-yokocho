# 樹上横丁 / Tree-top Yokocho

Windows 向け VRChat ワールドの編集用 Unity プロジェクトです。ユーザー提供の設定資料と既存 v2.0 制作物を引き継ぎ、落下防止と描画予算を改善しています。

## 現在の状態

- 元資料・既存モデルの実ファイルを確認済み。8店舗、49席、4デッキ（展望台を含む）、湖岸集落、山並みを継承
- 巨木・木造の横丁・藍色の暖簾・提灯の暖色を中心にした夕景
- 外周、内周の穴、階段側面に見えない非トリガー衝突壁
- Unity 2022.3.22f1 / Built-in Render Pipeline / VRChat Worlds SDK を想定
- 約50MBは最終 Windows ワールドの目標です。ZIP容量ではありません。実ビルド容量は未測定
- Unity / Udon / Shader のコンパイル、ライトベイク、VRChat Build & Test、VR実機試験は未実行。公開アップロードはしていません

## 導入

VRChat Creator Companionで新規Worldsプロジェクトを作り、Assets/TreeTopYokochoをコピーして Tools → TreeTop Yokocho → 1 - Build World を実行します。詳細: [SETUP_JA.md](Documentation/SETUP_JA.md)

現状はv2.1.0ソース・プレビュー版です。2,387,276描画三角形（従来比40.24%削減）、160提灯はベイク主体、Windows向けBC7/BC5。床734本と壁3,190本のオフライン検査に合格。

- [変更内容と現バージョン画像](Documentation/RELEASE_NOTES_2.1.0.md)
- [実行済みの検査](Documentation/Validation.md)
- [実機で残る確認](Documentation/ACCEPTANCE_JA.md)
- [サイズ設定・安全性の変更](Documentation/UnityAudit.md)

## プレビュー

Blenderの形状・材質プレビューです。Unity／VRChat実機画面ではありません。

![全景](../../../Preview/Blender_overview.png)

![店先](../../../Preview/Blender_alley.png)

## 出典

設定: 樹上横丁_設定資料一式_v1.zip。既存制作物: TreeTopYokocho_VRChat_v1.zip（内容は v2.0 高精細版）。PBRスキャン4セットは Poly Haven CC0、詳細は Docs/ThirdParty/PolyHaven.md。

推奨 Unity バージョン: https://creators.vrchat.com/sdk/upgrade/current-unity-version/
