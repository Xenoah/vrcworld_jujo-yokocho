# 暖簾の仕立て — v2.14

店先を見上げた時の構造を整えました。8店舗の普通の垂れ布に薄い実体と端の折返しを付け、木のような吊り部材を布の輪へ変更し、竿を節のある丸い竹へ作り替えています。店名・紋・色と印刷用UVの向きは維持しています。

## 制作した構造

- 垂れ布は0.65mmの本体と1.5mmの折返し。裾の半円断面と閉じた切れ込み側面
- 幅15mmの薄い布の輪が竿を越え、布本体へつながる
- 吊り点の両側から浅い折れが下がる。中央の紋や文字の領域は穏やかなまま
- 半径14.4mmの円形の竹竿と小さな節。元の35mm角の範囲に収め、既存のBAMBOO画像領域を使用
- 巻き上げた店員入口、竿から梁への支持紐、看板、灯り、品書きの元部品は維持

薄い布の形・仕立ての改修です。既存の印刷用テクスチャを使っており、微細な織り糸の表現や写実的な布材質の完成を主張するものではありません。

## 範囲と容量

追加は18,542三角形・11,588頂点・正味3バッチ。新しい画像・材質定義・シェーダー・コライダー・乱数呼び出しはありません。

旧56個のIdentityバッチから5個のCounterバッチを取り除き、8個のCraftSurfacesバッチを追加。19個の存続バッチを限定変更し、32個は完全一致です。その他の店舗や遠景を一括して検査から除外することはありません。

薄い布・吊り輪・竹竿を各々の旧範囲へ収めています。浮動小数点書き出しで生じる数µmの差はあるため、完全な実数座標の同一性とは扱いません。指定経路の実メッシュ検査も別途実行します。

## 再現と検査

`noren_craft` が真偽値の `true` の場合だけ実行します。省略・false・数値・文字列では元の処理に戻り、新モジュールもロードしません。

- 元のv2.11ソースZIPから56個の旧Identityペイロードを別枠で固定。既存603個の遠景・枝などの保護基準は変更しない
- 承認した最終59ペイロードと、元のまま保持する107部品スライスを厳密照合
- 単独制作段階の最終float32データで675判定、196部品/材質の記録を確認
- 可搬テストでは閉じたシェル・巻き順・正負の法線・有限の形状・UV・入口部品・材質・乱数不変・厳密な有効化を確認
- 生成後の全体データは[検証記録](Validation.md)、[独立照合](IndependentReview_2.14.0.md)、[可搬テスト結果](noren_craft_validation.json)を参照

薄い端やUVの有効性を確認する極端な接写は、通常の歩行中に同じ大きさで見えるという意味ではありません。Unity/C#/Udon/Shader、VR実機の見え方・片目描画・FPS、圧縮Windowsワールド容量は未確認です。


## v2.16 shop replacement scope

The individually designed shops supersede the prior repeated shop shell and 107 historical noren slices. Those older invariants remain historical inverse tests, not descriptions of current shop geometry. Current admission uses the exact 291-row v2.16 oracle and actual clearance checks. Nonshop shader/geometry preservation remains separately enforced. See [ShopPersonalityDesign](ShopPersonalityDesign.md).
