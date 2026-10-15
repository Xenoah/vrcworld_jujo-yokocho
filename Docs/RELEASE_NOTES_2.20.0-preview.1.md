# v2.20.0-preview.1 — 入口・共有時計・自作材質の統合ソース

これは **pre-release の編集用ソース**です。Unity / Udon / Shader の実コンパイル、ベイク、VRChat Build & Test・アップロード、実音声、複数人、VR実機の検証は未実施です。完成済みワールドや、実機動作確認済みの配布物とは扱いません。安定版の v2.19.0 はそのまま残します。

## 維持した v2.19 の制作内容

- 個別の内装・椅子・屋根・看板を持つ8店舗、RPG店名と日本語書体。
- スナック・カクテルバー・音楽バーの3店、全体の37.5%。
- 8つの立体看板、3つの静的布旗、木の茶房サイン。
- 49席、374灯（店舗内の個性ある15灯を含む）、12の既存lift、床・ガード・落下復帰。
- 幻想shaderと既存の平面mesh最適化。core は2,304,649三角形・1,145ソースバッチ。実測FPSやdraw callではありません。

これらを今回初めて実装したとは主張しません。旧coreの Assets・Source・Tools・Packages・ProjectSettings に属する669ファイルは、公開ZIPに記録された元のSHA-256と照合して保存します。旧scan画像も履歴再現用に残ります。

## 今回統合したもの

- 従来ローカル候補だった Entry Systems 0.1.0 を同梱。入口の案内、小広場、丸太ベンチ2脚、切株卓、木札ワープ3個。
- グローバルな24時間時計。±1時間、JST Auto、2/5/10/30/60倍と実JST1倍。初期値は手動18:30。
- 個人別のMP3 ON/OFFと次曲ボタン。複数の有効曲がある場合は直前曲を避けてrandom選択。全曲を一巡するshuffle bagではありません。
- 通常導入を一つにまとめた `Tools/TreeTop Yokocho/0 - Build or Complete Preview`。同一sceneへcore・Entry Systems・自作PBRを組み立て、限定scene監査後に保存します。
- 完全な導入状態の再実行は追加生成しない設計。異版・部分導入・不整合な参照は黙って修復／削除しません。新たに生成した所有範囲の資産だけを失敗時に巻き戻します。

旧メニュー1は core-only の履歴／診断用です。旧メニュー1の単独実行は今回の統合導入ではありません。再実行・保存・再読込・失敗復旧の実際のUnity挙動はまだ検証待ちです。

## 新規の自作PBR

樹皮、風化木材、カウンター木材、苔を含む岩の4系列を、このプロジェクト用の手続き的生成ソースから制作しました。旧scanやAI画像の画素を流用したものではありません。

専用overlayが31材質定義をcloneし、実使用30材質・523 renderer参照に対して88の既存texture slotを置換する設計です。未使用のMoss定義は区別します。既存の非ゼロparallax10項目だけを系列別に較正し、それ以外のshader、tint、UV倍率、keyword、材質数値、形状は維持します。統合sceneの監査は、旧PBR scanへのactive renderer参照が残る場合に失敗します。

同条件28枚の材質／実景比較、map検査92項目、継ぎ目検査80項目、独立再生成22ファイル一致を確認し、source-previewとして採用しました。

採用する画像・数値・render証跡の正確な状態は `ORIGINAL_PBR_REVIEW.json` と `integrated-source-validation.json` を参照してください。手続き的な自然素材表現であり、scanと同等の写実性やUnityでの最終見えを保証しません。ソースのheightは16bitですが、Unity実行用の圧縮・mip・shader挙動は別途目視試験が必要です。

## 残る重要な制約

- **MP3楽曲は0曲**です。再配布権の不明な音源は追加していません。権利確認済みMP3をMusicへ入れてplaylistを更新する必要があります。空の場合は無音・NO MP3、初期BGMはOFFです。
- 時計で空・方向光・霧・環境色は変わりますが、baked GI、店舗灯、light probes、反射画像は固定です。24時間の動的再ベイクではありません。
- 旗は静的造形です。追加の丸太家具は新規VRCStationではありません。
- 茶房S05の木製紋章は内向きの進入方向で屋根陰に入り、識別しづらい既知制限があります。
- 最終配信容量、Windows build容量、FPS、GPUメモリ、headset安全性は未測定です。

## 検証方法

`Tools/run_integrated_checks.py` は、不変のcore回帰61段階と、追加runtimeの独立参照モデル、installer契約、入口実geometryの通路、統合層、包装、手順書照合、材質のchannel／継ぎ目をオフラインで検査します。これらはUnity/Udonの実行テストではありません。

配布ZIPにはCRC・各file SHA-256・同名重複・検証後の全inventoryの一致検査を行います。最終ZIPを新しい場所へ展開した検証結果と公開commitは、release本文に記録します。`ARCHIVE_IDENTITY.json` は配布内容のhash一覧で、自己参照を避けるためZIP自身のhashと公開commitはrelease側に置きます。

導入手順: [MCP_UNITY_SETUP_JA.md](MCP_UNITY_SETUP_JA.md)。未実施項目の記録: [MCP_UNITY_VERIFICATION_TEMPLATE_JA.md](MCP_UNITY_VERIFICATION_TEMPLATE_JA.md)。全要件との対応: [REQUIREMENTS_STATUS_JA.md](REQUIREMENTS_STATUS_JA.md)。
