"""Write measured source-only metrics and clear build-verification limits."""
from pathlib import Path
import json, hashlib
root=Path(__file__).resolve().parent.parent
asset=root/'Assets/TreeTopYokocho'; data=asset/'Data'
m=json.loads((data/'WorldManifest.json').read_text())
v=json.loads((root/'Docs/validation.json').read_text())
n=json.loads((root/'Docs/navigation_validation.json').read_text())
version=m['version']; d=m['detail']; features=m.get('features',{})
profile=dict(version=version,target='Windows / VRChat / Built-in',target_download_megabytes=50,actual_windows_build_bytes=None,unity_compiled=False,vrchat_tested=False,previous_triangles=3994476,current_triangles=m['visualTriangles'],triangle_reduction_percent=round(100*(1-m['visualTriangles']/3994476),2),renderer_source_batches=m['visualMeshCount'],collision_sha256=hashlib.sha256((data/'CollisionMeshes.bytes').read_bytes()).hexdigest(),collision_bytes=(data/'CollisionMeshes.bytes').stat().st_size,visual_source_bytes=(data/'VisualMeshes.bytes').stat().st_size,visual_source_gzip_bytes=(data/'VisualMeshes.bytes.gz').stat().st_size,source_texture_bytes=sum(p.stat().st_size for p in (asset/'Textures').rglob('*') if p.suffix in ['.png','.jpg']),source_audio_bytes=sum(p.stat().st_size for p in (asset/'Audio').glob('*.wav')),shops=8,seats=len(m['stations']),distant_houses=d['distantHouses'],forest_trees=d['forestTrees'],floor_probes=len(m['floorTests']),barrier_rays=len(m['wallTests']),features=features,note='Source and GPU budgets are not compressed VRChat download size.')
(root/'Docs/WindowsProfile.json').write_text(json.dumps(profile,indent=2))
summary=f'''# 検証記録 — v{version} source preview

## 実行結果

- オフライン形状・資産検査: **{v['status']}**
- 実際の透明壁メッシュを断面化した通路検査: **{n['status']}**
- 8店舗、49席、12階層移動ボタン
- 床プローブ {len(m['floorTests']):,}本、透明壁の正面交差レイ {len(m['wallTests']):,}本
- 各床の実メッシュ面積一致、着席退出先、スポーン・移動先の床
- 実壁を足・腰・頭の高さ（0.2 / 1.0 / 1.65m）で差し引き、半径0.25mの通路中心余裕と階内の目的地接続を確認
- R03の側壁をW05が斜めに横断していた問題を、階段端を回り込むルートへ変更。W04の階段壁角との接触も修正
- PBR画像、GLB、圧縮メッシュ分割の完全復元、C#構文を検査

描画三角形 {m['visualTriangles']:,}、描画ソースバッチ {m['visualMeshCount']:,}、衝突三角形 {m['collisionTriangles']:,}。これらはドローコール・FPS・VRChatアップロード容量の実測ではありません。

## 検査の限界

Unityがないため、C# / UdonSharp / Shaderコンパイル、ベイク、Unity Physics Audit、ClientSim、Windows Build & Test、VR実機・複数人の確認は未実行です。約50MBは圧縮Windowsワールドの目標で、実ビルド容量は未測定です。

この幾何学検査はUnity CharacterControllerやVRトラッキングを再現しません。指定半径以外のアバター、ジャンプ、しゃがみ、着席・退出、階段接合、復帰動作は実機で確認してください。

根拠: [資産と床・壁レイ](validation.json)、[障害物を差し引いた通路](navigation_validation.json)、[容量・規模](WindowsProfile.json)
'''
if features.get('high_altitude'):
    crown=json.loads((root/'Docs/crown_validation.json').read_text())
    bark=json.loads((root/'Docs/bark_clearance_validation.json').read_text())
    summary+='\n## 高標高改修の追加検査\n\n- 地上〜212mの連続経路、実衝突メッシュによる身体余裕・床支持・頭上の検査: '+crown['status']+'\n- 枝の実描画メッシュ '+format(bark['barkTriangles'],',')+' 三角形を、樹冠の床幅全体と横丁・階段・客席の指定領域 '+format(bark['sweeps'],',')+' 区間で検査: '+bark['status']+'（交差'+str(bark['hitSweeps'])+'区間）\n- L4外周橋の透明壁接合部は、両側の実壁プリズムとの重なりを検査\n- 独立レビューで見つかった枝2箇所の視覚的干渉と約14cmの壁の隙間を修正\n\n樹皮検査は三角形面との交差検査で、葉や樹体内部だけに完全に収まる場合の体積包含を再現しません。\n'
if features.get('shop_craft'):
    detail=json.loads((root/'Docs/shop_detail_validation.json').read_text())
    sample=next(x['detail'] for x in detail['checks'] if x['name']=='actual_shop_and_railing_triangle_clearance')
    summary+='\n## 店先ディテールの追加検査\n\n- 実描画の店舗・手摺 '+format(detail['visualTrianglesTested'],',')+' 三角形と指定通路・客席 '+format(sample['testedEnvelopes'],',')+' 領域: '+detail['status']+'\n'
    if features.get('staff_access'):
        staff=json.loads((root/'Docs/staff_access_validation.json').read_text())
        deck=json.loads((root/'Docs/deck_surface_validation.json').read_text())
        foliage=json.loads((root/'Docs/foliage_runtime_validation.json').read_text())
        summary+='- 8店舗の入口と短い内側通路: '+staff['status']+'。半径0.25 / 0.325m、頭上1.8 / 2.2mの32領域と実床支持を検査\n- カウンターの16個のBoxColliderのみ幅・中心を指定量変更。残り61個、49席、12階層移動先は維持。移動ボタンは西側に移設\n- 透明壁・床・階段の衝突バイナリは維持。SupportingBranchesはレビュー済みの形状へ固定し、遠景・枝の保護データを厳密比較\n- 書き出し後の床板・連続下地・境界・溝: '+deck['status']+'\n- 葉のRepeat設定と位置基準の風変形式・境界: '+foliage['status']+'。Unity/GPU実行の結果ではありません\n'
        routes_path=root/'Docs/visual_route_validation.json'
        if routes_path.exists():
            routes=json.loads(routes_path.read_text())
            summary+='- 全描画・衝突形状と指定通路・階層移動操作動線の拡張照合: '+routes['status']+'。個別の検査範囲はJSONを参照\n'
    else:
        summary+='- 599個の保護対象バッチは旧版と一致。店員側入口の狭さは未改修\n'
    summary+='\n[店先検査](shop_detail_validation.json)、[入口検査](staff_access_validation.json)、[板床と動線の改修](DeckAndAccess.md)\n'
if features.get('surface_refinement'):
    menus=json.loads((root/'Docs/menu_orientation_validation.json').read_text())
    summary+='\n## 瓦・料理・描画分割の追加検査\n\n- 8枚の品書きの正面・上下左右UV: '+menus['status']+'\n- 葉と小枝の4バッチを東西8バッチへ分割。凍結したv2.8データと頂点共有・位置・UV・色・面順を照合し、承認済みの個別変更を除く保護バッチは完全一致（現在の内訳は下記の厳密検査結果）\n- v2.9の8銅樋バッチを個別に固定。未知の追加バッチや曖昧な名前の正規化は認めない\n- 瓦の頂点色とUV補修後の色継承を単体検査。検査結果はUnityでの見え方を保証しない\n\n[今回の制作と資産容量](SurfaceRefinement.md)\n'
if features.get('herb_planters'):
    summary+='\n## 店先の鉢の追加検査\n\n- 8箇所の元の配置と水平範囲、世界全体の乱数列を維持\n- 旧植物だけの40バッチから、新しい32バッチへの厳密な置換を検査。他の描画グループと603バッチの保護契約を維持。後続の雪の頂点色変更は8件だけ別途固定して検査\n- 独立した表裏の不透明な葉、鉢の開口・土の高さ・有限な形状とUVを10項目で検査\n\n[造形と資産容量](HerbPlanters.md)、[現行データの厳密検査](peer_contract_validation.json)\n'
if (root/'Assets/TreeTopYokocho/Data/DuskAtmosphere.json').exists():
    atmosphere=json.loads((root/'Docs/dusk_atmosphere_validation.json').read_text())
    summary+='\n## 夕空と霞の追加検査\n\n- 共有設定の方向・色入力・固定露出・Exp2と透明度保持のソース契約: '+str(atmosphere['testsRun'])+'項目、失敗'+str(atmosphere['failures'])+'、エラー'+str(atmosphere['errors'])+'\n- 夕景設定の改修自体は形状・衝突・席と動線を変更しない。舞台の追加造形と雪の色の差分は別途下記で検査\n- Unity ShaderとC#の実コンパイルは未実行。色設定の変更はUnity側にも適用されるため再ベイク・実機検査が必要\n\n[夕景の実装と限界](DuskAtmosphere.md)、[追加ソース検査](dusk_atmosphere_validation.json)\n'
if features.get('stage_roof_craft') is True:
    roof=json.loads((root/'Docs/noh_roof_detail_validation.json').read_text())
    summary+='\n## 舞台の軒先・雪山の追加検査\n\n- 舞台の旧15ネイティブバッチと新しい4バッチの完全なペイロードを個別に保護。追加は4バッチ、'+str(roof['addedTriangles'])+'三角形。床から2.757m未満の追加頂点なし\n- 56個の露出した瓦口を168本の検査線で照合。棟内部の旧中実材を中空とは扱わない\n- StageCypressの4枚のPBR参照だけを既存の粗い木材セットへ変更。6項目の材質専用テストを追加。新しい画像は0\n- 雪山は8バッチの承認済みRGBだけを変更。位置・UV・面順・alphaは固定。その他587保護バッチ、8分割済み樹冠バッチ、別枠15舞台バッチも厳密照合\n- 身体検査は指定経路と仮定寸法のオフライン幾何検査。Unityでの歩行やVR実機の代わりではない\n\n[舞台屋根](NohRoofDetail.md)、[雪山](SnowDeposition.md)、[厳密な変更契約](peer_culling_validation.json)、[明示した2視点の床支持と身体余裕](preview_camera_validation.json)\n'
(root/'Docs/Validation.md').write_text(summary)
print(json.dumps(profile,indent=2))
