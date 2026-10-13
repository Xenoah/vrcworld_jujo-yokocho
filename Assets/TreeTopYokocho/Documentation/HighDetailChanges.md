> Historical v2.0 source documentation. Current README/versioned release notes override this record: see WindowsProfile.json, UnityAudit.md and SETUP_JA.md.

# v2.0 高精細版への更新

## 変更した内容

- 描画三角形：3,994,476、描画メッシュ：590。
- 樹皮・古い板材・仕上げ木材・岩肌の4Kアルベドと、2K法線／ARM／高さ。
- Standard PBR、パララックス、両面の葉と風、水面の微細な波、湯気。
- 瓦の重なり、軒裏の垂木、暖簾の折り目と裾、金具、釘、収納、流し、調理器具、酒瓶ラベル、食器、箸、茶器、料理。
- 720棟の湖岸集落、6,400本の森林、周回道路、橋、寺院、複数の山稜。
- 近景のUV2生成、Mixed Light、Shadowmask、Light Probe、6個のReflection Probe、ACES・ブルームのPPS設定。

## 維持した内容

8店舗の中心位置と階高、49席、12個の階層移動操作、床と階段の接続、落下防止壁。

旧配布物から取り出した `CollisionMeshes.bytes` と今回のファイルをSHA-256で比較し、完全一致を確認しました。視覚的な追加部品が落下防止形状を変更していません。

## 実行した確認

床 734点、壁 3190本、全席の退出先と全移動先、床全体の面積と連続性、PBR画像の完全読込、GLBと独自バイナリの整合性、C#構文、HTML描画を確認。

UnityのC#／Udon／Shaderコンパイル、ライトベイク、Native Physics、ClientSim、VRChat Build & Testおよびアップロードは、この環境では実行していません。

## Unityで仕上げる

`1 - Build World` → `2 - Audit Physics` → `4 - Bake High Quality Lighting` の完了を待つ → `5 - Bake Reflections` → SDKのBuild & Test。PPSを後から追加する場合は `6 - Set Up Post Processing`。

HTMLは同じモデルを使いますが、別のレンダラーによる参考表示です。プレビューの画像をUnityのベイク結果として扱わないでください。
