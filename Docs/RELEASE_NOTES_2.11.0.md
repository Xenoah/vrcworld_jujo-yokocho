# v2.11.0 — 夕空と遠景の霞 / Source pre-release

店先の暖色と冷たい夕空、海の反射、遠い島の霞を調整しました。Unityと制作プレビューは一つの夕景設定を読み、色と方向の入力規約を明示しています。

空の上下方向の不具合を修正し、高さに応じた色と夕日・高層雲を追加。霞は遠い島の輪郭が残るExp2密度0.00028を採用しました。新しいメッシュ・画像・ライトはありません。

## 画像

[夕空と軒先](../Preview/Blender_dusk_eaves.png)
[高所から望む海と島](../Preview/Blender_dusk_sea.png)

実際のモデルのBlender Cyclesプレビューです。Unity／VRChatの画面ではありません。画像ごとのJSONに形状、設定、描画コードのSHA-256を記録します。

## 検査と制限

[夕景の実装と再現手順](DuskAtmosphere.md)、[検証記録](Validation.md)、[独立レビュー](IndependentReview_2.11.0.md)。形状・当たり判定・席と指定経路はv2.10と同じです。10項目の追加ソース検査を実行しました。

Unity側の空の色入力は意図的に変更しています。Blender比較だけでUnityの表示一致や改善を保証しません。Unity/C#/Udon/Shaderコンパイル、ベイク、Windows Build & Test、VR実機、FPS、圧縮ワールド容量は未確認。約50MBは最終ビルドの目標です。
