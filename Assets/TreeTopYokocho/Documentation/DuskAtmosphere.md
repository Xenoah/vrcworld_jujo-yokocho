# 夕空・遠景の霞 — v2.11.0

## 調整したこと

暖かな店先と冷たい空、海の反射、距離に沿う霞を一つの設定から調整します。`Assets/TreeTopYokocho/Data/DuskAtmosphere.json` をUnityのシーン生成とBlenderの制作プレビューが読みます。頂点・当たり判定・席・道・提灯の位置、既存の画像は変えていません。

以前のBlenderプレビューは空の方向が逆で、上を向いても水平線の色がほぼ一定でした。方向を直し、空の高さの変化、夕日の方角、細い高層雲を描画します。カメラだけ空の明るさが別になる設定も改め、反射と可視の空を共通にしました。

地面より下に限られていたプレビューの霧を、実際のカメラからの奥行きによるExp2の霞へ変更。密度0.00028と0.00040を同じモデル・視点・露出で比較し、遠い島の輪郭が残る0.00028を選びました。Unity側も同じ密度を使います。

## 表示と実装の区別

- 空と霧のRGBはscene-linearの放射輝度値。Unityの空はVector / SetVectorで渡し、Colorプロパティの暗黙の色変換を避けます。旧シェーダーと同じ数字でも、Unityでの見え方を維持する変更ではありません
- 霧はUnityの色APIへ渡す時に変換。環境光とLight.colorはUnity向けの従来の入力規約を残し、Blenderでは校正した近似値として使います
- BlenderはAgX +0.2、UnityはACES +0.25。全視点で固定し、画像ごとに明るくする補正はしません。ただし両者は同じトーンマッピングではありません
- プレビューの霧はインポート済み材質の透明度と外側の透明ミックスを保持し、葉の抜きや雲の隙間を埋めません。一般的な任意のシェーダーノードに対応する仕組みではありません
- プレビューの発光は以前からカメラ表示専用で、照明は明示したライトで計算します。霧の発光もカメラ専用にして不要な面光源サンプリングを除外しています。ノイズが解消したという比較結果ではありません

Unityのベイク、反射プローブ、TrilightとBlenderのパストレーシングは異なります。画像をUnityの見た目の保証として使わないでください。

## 資産と検査

追加したメッシュ・テクスチャ・ライト・Shaderパス・ランタイムスクリプトはありません。空の定数を編集可能にしたため、26個のスカラー相当のuniformとそれを使う演算が増えます。GPU時間・ビルド容量の増減は未測定です。

10項目のソース検査で方向変換、空の上下差、夕日の方角、Exp2、色の規約、固定露出、乱数不変、既存の単一パス／ステレオ処理と資産追加範囲を確認します。`python Source/test_dusk_atmosphere.py --report Docs/dusk_atmosphere_validation.json` で再実行できます。

画像のJSONはGLBに加え、設定ファイル、実効設定、プレビューコード、Unity側の空・ビルダー・設定読取コードのSHA-256を保存します。通常のOIDNノイズ除去には実シーンの法線・アルベドを使い、元PNGを保持します。

## 次に実行する検証

Unityでシーンを再生成し、Shader/C#をコンパイル、ライト・反射を再ベイクして、Windows Build & TestとVR実機で確認してください。雲海の形状、雪山の表面と島自体の形はこの版では変更していません。

## 一次資料

- [Unity 2022.3 Material.SetVector](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Material.SetVector.html)
- [UnityのShader Color/Vector入力](https://docs.unity3d.com/2022.3/Documentation/Manual/SL-PropertiesInPrograms.html)
- [Unity PostProcessingの霧の色変換](https://github.com/Unity-Technologies/PostProcessing/blob/v2/PostProcessing/Runtime/Effects/Fog.cs)
- [Unity 2022.3のライト変換](https://github.com/Unity-Technologies/UnityCsReference/blob/2022.3/Runtime/Export/GI/Lightmapping.cs)
