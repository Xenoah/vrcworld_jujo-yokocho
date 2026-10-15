# オフライン検証の範囲

この記録は v2.20.0-preview.1 のソース検査です。Unity、Udon、Shader、VRChat の実行結果ではありません。

## 実行して合格した検査

- 不変の core `Source/run_checks.py`: 61段階。既公開 v2.19.0 の形状・看板・旗・安全導線等の回帰検査を変更せず実行。
- 追加 runtime の独立参照モデル: 46 tests。実際のUdon実行ではありません。
- Entry installer のソース契約: 18 tests。
- 統合 menu・材質導入層の構文／契約: 14 tests。
- ZIP包装・同名重複・symlink・検証後の改変拒否: 11 tests。
- 材質／入口画像の現ソース対応と改変拒否: 36 tests。
- 入口広場: 15契約、現物geometryで33配置・4導線・12立ち位置を検査。
- MCP手順: 12実在メニュー、13 runtime API、3ワープ軸、10広場asset pin、43 native batches / 2,664 triangles、6操作面の数値・UVを照合。11種類の負例を拒否。
- 自作PBR: 16 mapについて92項目のchannel／normal／height等検査、5縮小段階を含む80項目の周期境界検査。独立再生成でsource・origin・16 maps・4 contact画像の22ファイルがbyte一致。
- 自作PBRの比較画像: 同条件の28画像を目視。全render入力hashと168 map参照を照合。判定と制約は `ORIGINAL_PBR_REVIEW.json` に記録。
- 統合入口の2画像: 87入力hash、11置換材質を照合。89 meshes のUV 95,124 corners／色87,096 cornersをBlender meshから読戻し、UV最大差1.99e-8、色差0を確認。
- 既公開の Assets・Source・Tools・Packages・ProjectSettings に属する669ファイルを元SHA-256と照合。元scan・GLB・core実装・既存oracleを改変せず保存。

入口プレビューの初回描画では、Blenderのlayer追加後に古い属性参照が変わる問題を検出しました。UV／色layerを名前で再取得してから代入し、全要素を読戻す検査を加え、正式な2画像を再描画しています。元geometryやmapを変更して見かけを補正したものではありません。

## 再実行

必要なPython依存は元coreのrequirementsと、PBR出自に記録したNumPy／SciPy／Pillow等です。統合package rootから次を実行します。

    python Tools/run_integrated_checks.py

元coreのsuiteは数分以上かかり、検証用の非配布raw payloadを再構成します。`Tools/verify_integrated_source.py` は全配布候補ファイルのinventoryを固定し、packagerはその後の追加・削除・改変を拒否します。

最終ZIPのCRC、全file SHA-256、展開後の再検査結果、公開commit、ZIP自身のhashはrelease本文に記録します。ここに結果のないUnity／実機項目を実施済みとは扱いません。[Unity検証記録](MCP_UNITY_VERIFICATION_TEMPLATE_JA.md)を別途埋めてください。
