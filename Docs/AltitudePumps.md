# 雲海より上の横丁と段階式給水設備

この変更は架空の 3D 環境の造形です。水圧、流量、飲用水適合性、構造耐力などの設計保証や認証を示すものではありません。

## 高度変更: `Source/altitude_profile.py`

`apply_altitude_profile(g, c, metadata)` は、既存の視覚メッシュ、物理メッシュ、メタデータを同じ座標変換で一度だけ更新します。原点・単位は従来通り、メートル、X 東・Y 北・Z 上です。Unity への軸変換は行いません。

- 地上 G0: 0 m のまま
- 横丁 L1: 34 → 134 m
- 主環状路と舞台 L2: 40 → 140 m
- 横丁 L3: 46 → 146 m
- 展望デッキ L4: 52 → 152 m
- 旧 Z33 m 以上の樹冠、店、看板、照明、通信塔など: 一律 +100 m
- 遠景の地形、町、海、山、遠景樹木: 元の高さのまま

高さ変換は次のとおりです。

```
t = clamp((z - 14) / 19, 0, 1)
f(z) = z + 100 * t² * (3 - 2t)
```

Z14 m 以下は不変、Z33 m 以上は平行移動です。その間だけ樹幹、昇降機の構造、配管が伸長します。変換は連続かつ単調増加で、接続部の一次微分も連続です。`altitude(z)` はスカラーと NumPy 配列、`inverse_altitude(z)` は逆変換を提供します。

元の横丁の床平面形状、通路幅、店や舞台の寸法は変えません。地上の床・アクセス設備も変わりません。根のうち Z14 m より上へ突き出した頂点には、他の樹幹と同じ滑らかな変換が適用されます。

### 正しい統合順序

1. 既存の床、柵、店、樹木、遠景、設備、能舞台を生成する
2. 既存の階段・経路・スポーン・床検査位置をすべて生成する
3. 下のメタデータ束を作り、高度変更を一回だけ適用する
4. 地上 0 m → 樹冠 212 m の新しい独立した階段、雲海、新しいポンプを追加する
5. 新しい階段の床・柵・照明などのメタデータを追加する
6. すべてが揃ってから `Geometry.compact()`、書き出し、検証を実行する

```python
from altitude_profile import apply_altitude_profile
from booster_pumps import add_booster_pumps

altitude_metadata = dict(
    levels=levels, stairs=stairs, spawns=spawns, lights=lights,
    steam=steam, stations=stations, teleports=teleports,
    solidBoxes=solidBoxes, floorTests=floorTests, wallTests=wallTests,
    guards=guards, routes=routes, infrastructure=infrastructure, stage=stage,
)
altitude_report = apply_altitude_profile(g, c, altitude_metadata)
# Existing Python lists/dicts above have now been updated in place.
# Add the independently authored high-crown stairs and cloud sea afterward.
booster_pumps = add_booster_pumps(g, M, infrastructure)
# Suggested manifest fields:
# manifest['altitudeProfile'] = altitude_report
# manifest['boosterPumps'] = booster_pumps
```

新しい階段を伸長させてはいけません。通常は変更後に生成します。二重変更防止用に、`Crown/`、`Safety/Crown/`、`Ramps/Crown*`、`Floors/Crown*`、`Landscape/`、`Infrastructure/Boosters/` のメッシュ、および `crown` / `crownStairs` / `cloudSea` / `boosterPumps` の独立したメタデータ項目は除外しています。ただし、先に生成した新階段の照明や床検査位置を共通リストに混ぜてから変換する使い方は非対応です。必ず上記の順序にしてください。

### 座標データと共有参照

位置の意味が明確な `position`、`center`、`start`、`end`、`destination`、`exit`、境界の `min/max`、経路の `points/centerline`、および高度 `z/base/top` だけを変更します。3 要素だから位置だと推測して一律に変更することはしません。向き、軸、色、範囲、光量、半径、通常の寸法、XY 多角形、WKT はそのままです。

舞台の `z`、`center`、`visualBounds`、`floorRecommendation`、`floorTests` と、設備の `utilityRoutes`、灯器、航空障害灯、支柱基部も同じ規則で更新します。共通の照明リストや床検査リストに同一オブジェクトが複数回現れても、オブジェクト識別によって一度だけ変換します。

`solidBoxes` の垂直寸法だけは、実際の下端と上端を変換して求め直します。店舗や舞台のように平行移動領域にある直立箱の寸法は維持されます。変形領域を横切る直立した長い箱は、中心位置と垂直寸法を両方変更します。非線形領域に斜めの BoxCollider を渡した場合は、誤った形状を生成する代わりに明示的なエラーにします。

`Geometry` とメタデータ束には一回適用済みの印が付き、同じ入力への再適用はエラーになります。新しい `Geometry` へ古いバッチをコピーして印を失った状態で再適用する使い方はしないでください。

### テクスチャ密度

樹皮チューブの輪ごとの中心線を計り直し、伸びた区間に応じて長手方向 V を繰り返します。根と幹の別チューブの位相は混ぜず、端面の UV は維持します。昇降機の独立した箱面は伸長後の辺長で UV を再計算します。上の店や看板の UV を一律拡大することはありません。

## 給水設備: `Source/booster_pumps.py`

`add_booster_pumps(g, M, infrastructure)` は、高度変更済みの `Trunk_water` と `Ground_water` を使用します。上端が Z152 m でない入力、地上配管と幹配管の不一致、二重生成は明示的なエラーになります。既存の配管メタデータは変更しません。

### 造形

- 既存の地上設備バンク前列に、10 段の目に見えるインペラー帯を持つ大型縦型ポンプを 2 基追加
- Z52 m と Z102 m に、同じポンプ各 2 基を置いた独立した中継設備を追加
- 中継設備は、樹幹に固定した左右の三角持送りと横桁で支持
- 6 基すべてに積層ケーシング、締付ロッド、大きな電動機、冷却フィン、端子箱、配線、ボルト付き基部を造形
- 7 個の逆止弁、4 個の隔離ハンドル、4 個のアナログ計器、フランジ、流れ方向矢印、区分色を追加
- 元の縦幹配管は隔離弁付きバイパスとして残し、各中継設備の吸込と吐出を接続
- Z155 m の支持台上に縦型上部タンクを追加。タンク中心は約 `[-7.068, -6.697, 157.05]`、最上部は約 Z159.09 m
- 上部タンクに給水管、既存上部幹配管への戻り、覗き管、受け皿へ落ちるオーバーフロー管を追加

区分は地上 → 52 m、52 → 102 m、102 → 155 m の 3 段です。数値の圧力や流量は示しません。設備支持台は一般歩行用床として扱わず、独立したコライダーも作りません。

配管接続位置は変換後の既存幹配管から補間して求めています。旧樹木の高さ式をそのまま新高度で再評価することはありません。地上の新設備は既存サービス区画の前列に収まり、中継設備は半径 40 m の新階段から十分内側にあります。上部タンクは主環状歩道の内側にあり、既存の足場・経路の XY 輪郭との非交差を検査しています。

### コスト

検証時の追加分:

- 18,812 三角形、27 マテリアル/グループバッチ
- 追加の単色マテリアル 3 個
- 追加テクスチャ、コライダー、ランタイムスクリプト: 0
- 30,000 三角形未満を生成時に検査

返却データには `stations`、`storage`、`utilityRoutes`、`valves`、`supports`、`pressureZones`、`stats`、全体境界が含まれます。これらは JSON 保存可能です。

## 検証

メインワールドを再生成せず、次を実行できます。

```bash
python Source/altitude_profile.py
python Source/booster_pumps.py
```

高度変換の 14 チェック: 単調性、接続部連続性、逆変換、各階高度、共有オブジェクトの一回変更、方向・色・寸法維持、長い箱の上下端、独立階段と遠景の除外、店舗寸法、配管端点、有限頂点/UV、樹皮と昇降機の繰り返し、二重適用拒否。

ポンプの 16 チェック: 三角形予算、6 基/60 帯、3 箇所の支持台、各高度、テクスチャ/コライダーなし、元配管不変、地上/上部/中継の接続一致、全弁の配管中心線一致、有限頂点/UV、退化三角形なし、新階段の半径方向離隔、上部貯水槽と既存通路の非交差。

さらに既存の完全な WorldManifest を読み、14,813 位置・81 BoxCollider に変更を適用する検査を実施しました。箱寸法と軸、座席方向、柵上下端、テレポート先、舞台境界、給水幹の到達高度が期待通りでした。

これらはオフライン生成と数値検査です。実際の Unity/VRChat の表示、物理、アップロード、フレームレートの確認を代替するものではありません。統合側の既存設備検査は幹配管上端の旧値 `52/46/94` を新値 `152/146/194` に更新する必要があります。
