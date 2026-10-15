> この文書はEntry Systems 0.1.0単独候補の履歴です。現在の統合パッケージはREADME.mdとDocs/MCP_UNITY_SETUP_JA.mdを優先し、標準入口のメニュー0を使ってください。以下の未公開／別コピーという記述は旧候補時点のものです。

# 樹上横丁 Entry Systems 0.1.0（未公開ソース候補）

公開済み v2.19.0 に、入口の案内・小さな休憩広場・追加ワープ・時刻/BGM 操作を追加する別フォルダーです。元のワールドを置き換える完成済み Unity scene ではありません。

## 導入

1. v2.19.0 の作業用コピーを VCC Worlds / Unity 2022.3.22f1 / SDK 3.10.5 / Built-in で導入し、core のメニュー1でワールドを生成して保存します。
2. この候補の `Assets/TreeTopYokochoEntrySystems` を同じプロジェクトの `Assets` へコピーします。全ファイルと `.meta` を揃え、インポート/コンパイルエラーを解消します。
3. `Tools/TreeTop Yokocho/8 - Install Entry Systems (Add-on)` を実行します。既存 core の兄弟に `EntrySystems_v1` を追加します。同じ完全な導入状態なら無変更で戻り、不一致や部分導入を勝手に上書きしません。
4. 保存・再読込後、メニュー `8b - Audit Installed Entry Systems` と、`Docs/MCP_UNITY_SETUP_JA.md` の実行時検証を行います。

core の Build World をやり直すと新しい scene が生成されるため、その scene で addon を再適用します。導入前の scene/プロジェクトを保持してください。失敗時に既存 `Generated` をまとめて削除しないでください。

## 操作の範囲

- 時刻はインスタンス全体で共有します。手動の時刻変更、JST Auto、2/5/10/30/60倍の切替があります。Auto1倍は実際の JST、加速開始は JST を基準とします。最初は従来の夕景に合わせた手動18:30です。
- BGM は操作した人だけのローカル再生です。初期値は OFF。`Assets/TreeTopYokochoEntrySystems/Music` の再配布権限がある MP3 を Unity に読み込み、メニュー8aでリストを更新します。現在の候補には楽曲は含まれず、空の場合は無音・NO MP3 表示です。既存の風の環境音は別です。
- 入口の木札は既存の根元・二層・三層の到着点へ移動します。元の階層間ワープはそのまま残ります。
- 新しい丸太風家具は飾り/休憩用の造形です。既存49席とは別の新しい VRC Station は追加しません。

## 検証の限界

構文、ソース契約、独立した参照モデル、実際の制作形状による限定寸法の通路検査を行いますが、ここには Unity 実行環境がありません。Unity/Udon コンパイル、音声再生、複数人同期、実アバター、ベイク、FPS は未実行です。メニュー8b自体も Unity では未実行です。

時刻変更で sky・環境色・霧・既存の方向光を変化させますが、焼き込み済みライトマップ・反射・店舗照明を動的に焼き直しません。時刻に応じたすべての影や反射が正確になるという意味ではありません。

旧 core の61段階の検証は、この addon の機能検証を代替しません。新規 OS の完全再現試験でもありません。詳細は MCP 手順と未実施欄を残した検証テンプレートを参照してください。

## オフライン検査を再実行する場合

この追加ソースだけでは core 形状の再検査はできません。別途、公開 v2.19.0 の完全な展開先が必要です。既存の検証済み Linux 環境で使用した依存は `Tests/requirements-offline.txt` に記録しています。通常の Unity 導入では Python は不要です。

- `python -m unittest discover -s Tests -p 'test_*.py' -v`
- `python Source/test_entry_plaza_contract.py /path/to/v2.19/TreeTopYokocho`
- `python Source/audit_entry_plaza.py /path/to/v2.19/TreeTopYokocho .`

後二つは `Docs` に検査結果を書き出します。配布候補の原本を残し、検査用コピーで実行してください。全て成功しても Unity/Udon の実行試験に代わりません。
