> Historical v2.0 source documentation. Current README/versioned release notes override this record: see WindowsProfile.json, UnityAudit.md and SETUP_JA.md.

# 実装と再生成

## 構成

`Assets/TreeTopYokocho/Data/VisualMeshes.bytes` と `CollisionMeshes.bytes` は、同じ座標基準から出力した別々のメッシュです。Unity Editorのビルダーがバイナリを読み、Unityネイティブの `.asset` と `.unity` に変換して保存します。生成のためのスクリプトはEditor専用です。

ランタイムにはUdonSharpの `YokochoSeat`、`YokochoTeleport`、`YokochoSafety` のみを使います。通常のMonoBehaviourをワールドへ残す方式ではありません。座席と昇降口の処理はローカルのプレイヤーにだけ作用します。ネットワーク同期を必要とする店舗小物・可動かごはありません。

## 座標

| データ | 軸 |
|---|---|
| 元資料・Python | X=東、Y=北、Z=高さ |
| Unity | `(X,Y,Z) = (元X, 元Z, 元Y)` |
| glTF | `(X,Y,Z) = (元X, 元Z, -元Y)` |

Unity側は軸の反射に伴い三角形の頂点順を反転します。位置・階高・尺度はm単位を維持します。glTFはビジュアル編集用で、UnityビルダーはglTFを再インポートせず元のメッシュデータを読みます。

## 設定資料からの実装上の調整

- 接続通路の端を35cm延長し、隣の床と重ねました。W03は外周円への接線位置から始まるため、延長しないと通路が一点でしか接続しません。
- 階段の上端側の床に階段幅の切欠きを設けました。登り切る前に上階の床へ頭がぶつからないための処理です。
- 階段の端には着地用の床を追加。踏面の見た目と連続スロープの当たり判定は分離しています。
- L1を初期スポーンにしています。根元口も存在し、昇降口で往復できます。
- E01はG0〜L3の行先ボタンによる即時移動です。L4行きのボタンはありません。
- SV01は外観のみです。トイレ等の詳細な内装や扉操作は実装していません。

## 落下防止の形状

Shapelyで同じ高さの床のポリゴンを結合し、外周と内周から壁を作ります。凹形状・穴を含む床は制約付きDelaunay分割で三角形化しています。階段の側壁は、その上昇形状に沿った閉じたプリズムです。

標準の壁は8m高、厚さ24cm。各区間の端を重ね、角に微小な隙間が残りにくくしています。下階の境界が階段の真下を通る部分は、下階側の壁を階段裏まで短くし、階段上の動線を確保します。見える手すりと見えない壁は独立です。

階高が6mのため、上階の床に近い下階の壁は上階床の38cm下で終端させます。上階にはその階自身の防護壁があります。これにより、下階の8m壁が上階の到着口・通路を塞ぐのを防ぎます。

階段側壁を含む衝突メッシュは静的・非凸・非トリガーです。Unity物理での実行検査は同梱メニューで行えますが、本制作環境では実行できていません。

## 光と描画

Unity Built-in向けのStandard Surface Shaderへ更新しました。アルベド・OpenGL法線・ARM（R=AO、G=粗さ、B=Metallic）・高さを使用します。色はsRGB、法線・ARM・高さはLinearでインポート。法線はUnityのNormalMap importerで再パックされます。距離に応じた偽の暖色頂点カラーは廃止し、ライトと間接光を使います。

木材・樹皮・岩肌の4Kアルベドと2K補助マップはPoly HavenのCC0素材です。SourceのglTFは最大2Kテクスチャ、Unity用素材は元の解像度を維持します。葉のテクスチャ・瓦・布・メニュー類は今回の手続き生成です。個別の近景葉に加えて、枝葉の透過マスクを使う両面メッシュを重ねています。

近景の建築メッシュはUnityでUV2を生成し、GIを受けるよう設定します。巨木・樹冠はベイクに遮蔽物として寄与し、受光にはLight Probeを使います。広い遠景はLight Probe／環境光を使用します。室内と提灯はMixed Light、光源に近い構造にはリアルタイム影を設定。Light Probeを通路周辺の高さ3段に置き、反射用Probeを6箇所に置きます。

`4 - Bake High Quality Lighting` はProgressive CPU、20 texels/m、最大4096、間接512サンプル、AO有効で非同期ベイクを開始します。完了後に `5 - Bake Reflections` を実行します。高密度の葉を含むため、所要時間とVR内負荷はPCに依存します。この制作環境ではベイクは未実行です。

PPS v2導入時はReference CameraにPostProcessLayer、ワールドにGlobal Volumeを設定します。ACES、低強度ブルーム、彩度の微調整を含みます。被写界深度やモーションブラーは入れていません。PPS未導入でも本体は作成され、後からメニュー6で追加できます。

水面は二重のスクロール法線、小さい頂点波、Standardの反射を使います。リアルタイムの平面反射や物理流体ではありません。湯気はUnity ParticleSystemと専用Shader、葉の風は頂点変形です。通常の実行時MonoBehaviourを追加する方式ではありません。

HTMLは同じGLBをgzip圧縮して内蔵したオフラインビューアーです。Three.jsのPBR・影・ブルーム・環境反射を使用。VRChatの物理やネットワーク挙動を再現するものではありません。

## 再生成

Python 3.12で検証しました。プロジェクトのトップで以下を実行します。

```sh
python -m pip install -r Source/requirements.txt
python Source/build_world.py .
python Source/validate_world.py .
```

同梱テクスチャがあればフォントなしで再生成できます。看板を含めテクスチャを生成し直す場合は、第2引数に日本語フォント（例：Noto Sans CJK JP）のファイルを指定します。

```sh
python Source/build_world.py . /path/to/NotoSansCJKjp-Regular.otf
```

`Source/layout.reference.json` は元資料の保存用です。寸法変更はビルダー内の造形条件にも関係するため、JSONだけの変更ですべてのケースに追従する汎用建築ツールではありません。変更後はオフライン検査に加え、UnityのPhysics AuditとVRChatでのテストを再実行してください。

## バイナリ形式 JYWM v1

Little endian。ヘッダ `JYWM`、uint32バージョン、uint32メッシュ数。各メッシュは、uint32バイト長＋UTF-8のグループ名、同じ形式の材質名、uint32頂点数、uint32インデックス数、float32のXYZ、float32のUV、RGBA各uint8の色、uint32の三角形インデックスを順に持ちます。

## クレジット

配置・店名・寸法の基準：ユーザー提供「樹上横丁_設定資料一式_v1.zip」。今回のメッシュ、追加の図形テクスチャ、環境音は手続き生成です。実写PBRテクスチャ4セットはPoly Haven（CC0）から同梱しています。詳細は `ThirdParty/PolyHaven.md` に記載しています。元の設定画像をテクスチャとして流用していません。看板はNoto Sans CJK JPで描画しており、フォントファイル自体は同梱していません。

HTMLビューアーはThree.js 0.170.0と付属のOrbitControls／GLTFLoaderを使用しています。ライセンスは `ThirdParty/Threejs-LICENSE.txt` に同梱しています。
