# Unity と VRChat で開く

このリポジトリは SDK 本体を再配布しません。Unity がこの制作環境にはないため、ネイティブシーンの生成と実ビルドは下記の手順で行います。

1. VRChat Creator Companion で Unity 2022.3.22f1 の Worlds プロジェクトを新規作成します
2. このリポジトリの Assets/TreeTopYokocho フォルダーをプロジェクトの Assets 内へコピーします。既存ワールドや ProjectSettings を上書きしないでください
3. VRChat Worlds SDK 3.10.5 を使用します。同版の対応状況を検証できていないため、SDKのコンパイルエラーがあれば先に解決してください
4. 任意で Package Manager から com.unity.postprocessing 3.4.0 を追加します
5. Tools → TreeTop Yokocho → 1 - Build World。編集可能な Unity シーン、メッシュ、マテリアルを生成して保存します
6. 2 - Audit Physics。床、階段、透明壁、プレイヤーレイヤー、座席と移動先を確認します
7. 4 - Bake High Quality Lighting の完了を待ち、5 - Bake Reflections を実行します
8. SDK の Builder で Windows を選び、Build & Test を実行します。これは公開アップロードではありません
9. Docs/ACCEPTANCE_JA.md の項目を実機で確認してください

## Git クローンを VCC へ直接追加する場合

Add Existing Project でこのフォルダーを追加し、Manage Project から Worlds SDK を復元します。VPM Resolver 本体は含めていないため、単に Unity Hub から開くだけでは SDK は復元されません。確実な経路は上記の VCC 新規 Worlds プロジェクトへの Assets コピーです。

## 元データの再生成

Python 3.12とGitがある環境で次を実行します。Gitは圧縮資産の改行変換防止テストにも使用します。

    python -m pip install -r Source/requirements-lock.txt
    python Source/build_world.py .
    python Source/pack_geometry.py
    python Source/run_checks.py

テクスチャの名前にある 4k/2k は元素材の名前です。このWindows50版はアルベドを最大2048、補助マップを最大1024へ縮小した実ファイルを使用します。

## 対応環境の公式資料

- https://creators.vrchat.com/sdk/upgrade/current-unity-version/
- https://creators.vrchat.com/releases/
- https://vcc.docs.vrchat.com/vpm/source-control/

ソースZIPには編集用GLBも収録しています。GitではGLBを省略し、Pythonから再生成します。run_checks.pyはGeometryShards.jsonに記録した分割メッシュのSHA-256を検査し、無視対象の未圧縮データを復元して全オフライン検査を実行します。


## 制作プレビューの再描画

同梱プレビューはBlender 4.3.2のCycles CPUで生成しました。Unityの実行画像ではありません。現在のカメラ設定は `Source/detail_cameras.json` に保存しています。

    blender -b -t 4 --python Source/render_preview.py -- --views stage_craft_eye stage_craft_roof alpine_city --samples 64 --width 1280 --aov
    python -m pip install -r Source/requirements-preview.txt
    python Source/denoise_preview.py Preview/Blender_stage_craft_eye.png Preview/Blender_stage_craft_roof.png Preview/Blender_alpine_city.png

最初のコマンドが実際のPNGと法線・アルベドEXRを生成し、次の処理はその実パスだけを使うOpen Image Denoiseです。元PNGは `Preview/Raw` に保持します。別の画像生成や描き直しはしていません。処理済み画像への二重適用は拒否します。

日本語看板の焼き込み済み画像は同梱されています。再生成時に日本語フォントが見つからなければ同梱画像を保持します。文字を作り直す場合は、日本語OpenType/TrueTypeフォントを `build_world.py` の第2引数へ指定してください。この版の店舗意匠アトラスにはNoto Serif CJK Boldを使用しました。フォントを替えると文字の形や配置は変わります。フォント自体はワールドへ組み込んでいません。

## v2.15 の厳密な印字検査

Unityで同梱済み画像を使うだけなら、制作フォントのインストールは不要です。一方、run_checks.py に含まれる印字の完全一致検査は、元と同じ Noto Serif CJK Bold / Noto Sans CJK Regular の実ファイルとSHA-256を必要とします。Pythonパッケージだけではフォントは入りません。ファイルがない場合や版が異なる場合は、検査を省略せず明示的に失敗します。必要なパス・ハッシュ・検証した環境は Source/testdata/shopfront_print/README.md と fixture_manifest.json に記録しています。別のフォントへ置換して検査を通したことにはしないでください。

制作プレビューでは、Unityのベイク済みランプをCyclesの動的点光源で近似します。照明倍率・光沢の映り込み・反射プローブ・露出は完全一致しません。特にカウンター上の強い光沢を、そのままUnity実機の眩しさや不具合と判断しないでください。


## v2.17の同一版データを使う

店名・発光材質・15灯の色を含む WorldManifest.json と VenueLighting.json、Editor/VenueLightingProfile.cs、YokochoWorldBuilder.cs を同じソース候補から使用してください。旧版のシーンやデータを部分的に混ぜず、Build Worldで再生成した後にライトマップと反射／LightProbeを再ベイクします。本文のオフライン検証は、実際のUnityコンパイルやベイクの完了を意味しません。

Source/fonts は看板画像の再生成用です。Unityへフォント本体を導入する必要はなく、通常はAssets/TreeTopYokochoだけをコピーします。Sourceから画像を作り直す場合は同梱requirements-lock.txtとライセンス付きのサブセットを使用し、日本語未対応の代替書体へ自動置換しないでください。
