"""Write measured source-only metrics and clear build-verification limits."""
from pathlib import Path
import json, hashlib, struct
root=Path(__file__).resolve().parent.parent
asset=root/'Assets/TreeTopYokocho'; data=asset/'Data'
m=json.loads((data/'WorldManifest.json').read_text())
v=json.loads((root/'Docs/validation.json').read_text())
n=json.loads((root/'Docs/navigation_validation.json').read_text())
version=m['version']; d=m['detail']; features=m.get('features',{})

def visual_gzip_size(data):
    """Measure only the fully authenticated canonical shard representation."""
    from visual_transport import validated_visual_transport
    return validated_visual_transport(data).compressed_bytes

def cloth_use_wording(features):
    if features.get('venue_projecting_signs') is True:
        return '閉じた店内の布張りと新しい実体付き旗は裏面カリング、単一面の街の布は両面描画。旧107暖簾部品は歴史的復元の対象のまま、既存Noren1/Noren3材質だけを新しい旗2枚で再使用'
    return '閉じた店内の布張りは裏面カリング、単一面の街の布は両面描画。旧暖簾の設定は歴史的互換用で、現行の可視部品や節約量とは数えない'

def projecting_sign_metrics(root, manifest, admission):
    """Measured counters only after the caller's strict current native admission."""
    import projecting_sign_contract as signs
    if signs.validate_gate(manifest):raise ValueError('Invalid projecting-sign summary gate')
    pin=signs.load_oracle(root);prior=signs.before(root)
    scope=admission.get('scope',{})
    if admission.get('passed') is not True or scope.get('passed') is not True or admission.get('oracleSha256')!=signs.ORACLE_SHA256:
        raise ValueError('Current exact projecting-sign native admission required')
    added=pin['addedRows']
    counts=(len(added),sum(r['triangles'] for r in added),sum(r['vertices'] for r in added))
    if counts!=(admission.get('addedBatches'),scope.get('addedTriangles'),scope.get('addedNativeVertices')):
        raise ValueError('Authenticated projecting-sign summary counters disagree')
    raw=(root/'Source/TreeTopYokocho.glb').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=pin['glbSha256']:raise ValueError('Current exact projecting-sign GLB required')
    if raw[:4]!=b'glTF' or struct.unpack_from('<I',raw,4)[0]!=2 or raw[16:20]!=b'JSON':raise ValueError('Invalid GLB summary header')
    glb=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]])
    return dict(projecting_sign_oracle_sha256=signs.ORACLE_SHA256,projecting_sign_native_admission=True,
        projecting_sign_native_sha256=pin['nativeSha256'],projecting_sign_glb_sha256=pin['glbSha256'],
        projecting_sign_baseline_version='2.18.0',projecting_sign_baseline_native_sha256=signs.BEFORE_NATIVE_SHA256,
        projecting_sign_preserved_native_batches=len(prior['rows']),projecting_sign_added_batches=counts[0],
        projecting_sign_added_triangles=counts[1],projecting_sign_added_native_vertices=counts[2],
        projecting_sign_added_source_vertices=scope['addedSourceVertices'],
        projecting_sign_new_material_definitions=len(manifest['materials'])-len(prior['manifest']['materials']),
        native_material_definitions=len(manifest['materials']),glb_used_materials=len(glb['materials']),
        glb_embedded_images=len(glb['images']),projecting_sign_activated_existing_cloth_materials=['Noren1','Noren3'],
        projecting_sign_new_texture_source_files=0,projecting_sign_new_embedded_existing_images=1,
        projecting_sign_new_lights=len(manifest['lights'])-len(prior['manifest']['lights']))

profile=dict(version=version,target='Windows / VRChat / Built-in',target_download_megabytes=50,actual_windows_build_bytes=None,unity_compiled=False,vrchat_tested=False,previous_triangles=3994476,current_triangles=m['visualTriangles'],triangle_reduction_percent=round(100*(1-m['visualTriangles']/3994476),2),renderer_source_batches=m['visualMeshCount'],collision_sha256=hashlib.sha256((data/'CollisionMeshes.bytes').read_bytes()).hexdigest(),collision_bytes=(data/'CollisionMeshes.bytes').stat().st_size,visual_source_bytes=(data/'VisualMeshes.bytes').stat().st_size,visual_source_gzip_bytes=visual_gzip_size(data),source_texture_bytes=sum(p.stat().st_size for p in (asset/'Textures').rglob('*') if p.suffix in ['.png','.jpg']),source_audio_bytes=sum(p.stat().st_size for p in (asset/'Audio').glob('*.wav')),shops=8,seats=len(m['stations']),distant_houses=d['distantHouses'],forest_trees=d['forestTrees'],floor_probes=len(m['floorTests']),barrier_rays=len(m['wallTests']),features=features,note='Source and GPU budgets are not compressed VRChat download size.')
with (data/'VisualMeshes.bytes').open('rb') as stream:
    if stream.read(4)!=b'JYWM':raise ValueError('Invalid native visual header')
    format_version,batch_count=struct.unpack('<II',stream.read(8))
    if format_version!=1:raise ValueError('Unsupported native visual version')
    vertices=triangles=0
    for _ in range(batch_count):
        for _ in range(2):
            size,=struct.unpack('<I',stream.read(4));stream.seek(size,1)
        nv,ni=struct.unpack('<II',stream.read(8));vertices+=nv;triangles+=ni//3;stream.seek(nv*24+ni*4,1)
    if stream.read(1) or triangles!=m['visualTriangles']:raise ValueError('Native counts do not match manifest')
profile.update(visual_source_vertices=vertices,quality_pass_baseline_version='2.14.0',quality_pass_baseline_triangles=2649607,quality_pass_triangle_delta=m['visualTriangles']-2649607,quality_pass_baseline_vertices=3200270,quality_pass_vertex_delta=vertices-3200270,quality_pass_baseline_native_bytes=108651058,quality_pass_native_byte_delta=profile['visual_source_bytes']-108651058)
(root/'Docs/WindowsProfile.json').write_text(json.dumps(profile,indent=2))
summary=f'''# 検証記録 — v{version} source preview

## 実行結果

各節は、その改修単独の差分と検査範囲です。後続の明示した個別契約による変更も含む現行全体の値は、WindowsProfile.jsonと現行ネイティブ契約の結果を参照してください。

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
if features.get('shop_craft') and features.get('shop_personality') is not True:
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
    summary+='\n## 舞台の軒先・雪山の追加検査\n\n- 舞台の旧15ネイティブバッチと新しい4バッチの完全なペイロードを個別に保護。追加は4バッチ、'+str(roof['addedTriangles'])+'三角形。床から2.757m未満の追加頂点なし\n- 56個の露出した瓦口を168本の検査線で照合。棟内部の旧中実材を中空とは扱わない\n- StageCypressの4枚のPBR参照だけを既存の粗い木材セットへ変更。6項目の材質専用テストを追加。新しい画像は0\n- 雪山は8バッチの承認済みRGBだけを変更。位置・UV・面順・alphaは固定。その他の承認済み変更を除く保護バッチ、8分割済み樹冠バッチ、別枠15舞台バッチも厳密照合\n- 身体検査は指定経路と仮定寸法のオフライン幾何検査。Unityでの歩行やVR実機の代わりではない\n\n[舞台屋根](NohRoofDetail.md)、[雪山](SnowDeposition.md)、[厳密な変更契約](peer_culling_validation.json)、[明示した視点の床支持と身体余裕](preview_camera_validation.json)\n'
if features.get('cloud_depth') is True:
    summary+='\n## 雲海の厚みの追加検査\n\n- 8個の雲バッチのZのみを124m基準で2.2倍に拡張し、個別の完全ペイロードを厳密照合\n- 元のX/Y・UV・色・面順、36,288三角形・8バッチ、他の1,047描画バッチを維持\n- 実形状の高度93.816–123.604m、最大0.15mの揺れでもL1より10.246m下\n- 中央の開口と階段との水平余裕を維持。新しいテクスチャ・灯り・シェーダー・コライダーは0\n- 透明描画の重なりとVR実機の見え方・速度は未測定\n\n[実装と制約](CloudDepth.md)、[ソース検査](cloud_depth_source_validation.json)\n'
if features.get('noren_craft') is True and features.get('shop_personality') is not True:
    nr=json.loads((root/'Docs/noren_craft_validation.json').read_text())
    summary+='\n## 暖簾の仕立ての追加検査\n\n- 8店舗の普通の垂れ布だけに薄い実体・折返し・吊り輪・円形の竹竿を追加。新しい画像・材質定義・シェーダーは0\n- 59個の最終Identityペイロードを個別固定。32個の旧バッチと107個の保存部品を元のアーカイブと厳密照合\n- 巻き上げた店員入口・竿の支持紐・看板・品書き・灯りの元部品を維持\n- 可搬テスト '+str(nr['testsRun'])+'項目: '+nr['status']+'。全体の圧縮容量や実機の見え方は別途確認が必要\n\n[制作内容と制限](NorenCraft.md)、[暖簾のソース検査](noren_craft_validation.json)\n'
if features.get('visual_unused_compaction') is True and features.get('static_planar_sea') is True:
    opt=json.loads((root/'Docs/mesh_optimization_contract_tests.json').read_text())
    summary+='\n## 平面・未使用頂点の追加検査\n\n- 未参照頂点だけの除去と、遠方の海の平面再分割を別々の明示フラグで管理。132件の変更前後の完全なデータを個別固定\n- '+str(opt['assertions'])+'件の厳密検査: '+opt['status']+'。海以外の描画三角形の属性と共有関係、全バッチの境界箱、この最適化単独では旧暖簾107部品を維持（v2.16店舗置換では歴史的復元検査）\n- 海の旧最大43mmの頂点移動は、静的平面と時間変化する法線へ変更。頂点変形の完全互換とは扱わない。具体的な視点・画角の誤差範囲は資料を参照\n- 頂点数・三角形数・ソース容量の減少は計測値。Unityの速度・FPS・配信容量は未測定\n\n[平面最適化と測定条件](PlanarOptimization.md)、[厳密検査](mesh_optimization_contract_tests.json)\n'
if features.get('fantasy_materials') is True:
    fantasy=json.loads((root/'Docs/fantasy_material_validation.json').read_text())
    summary+='\n## 幻想的な材質と空の追加検査\n\n- 布・和紙灯り・釉薬の専用不透明シェーダーと、控えめな空の帯・星、斜めに変化する海面法線を追加。形状を増やす装飾粒子は追加しない\n- '+str(fantasy['testsRun'])+'件のソース・数値・実データの材質参照検査: '+fantasy['status']+'。シェーダー資産は'+str(fantasy['shaderAssetCount'])+'種類\n- '+cloth_use_wording(features)+'\n- Blender画像は実モデルを使った近似。星・布の微分フィルタは再現せず、木や金属の粗さ式は既存のテクスチャ入力から近似し、Unityの実描画・ベイク・両眼確認は未実行\n\n[材質の実装・費用・限界](FantasyShaderIntegration.md)、[ソース検査と実使用数](fantasy_material_validation.json)\n'
if features.get('city_roof_hidden_caps') is True:
    caps=json.loads((root/'Docs/city_roof_caps_validation.json').read_text())
    summary+='\n## 遠景の内部面の追加検査\n\n- 278個の閉じた不透明な破風材内部に完全に収まる834枚の端面だけを除去。1バッチを個別固定し、1,668三角形・3,336頂点を削減\n- '+str(caps['assertions'])+'件の厳密検査: '+caps['status']+'。この内部面除去処理では他の1,057バッチ、残存面の属性、衝突と座席は変更しない\n- 未検証の量子化で55.255mmの内部余裕を崩さないよう、この1バッチだけのMeshCompressionをOffにする。Unityの保存・配信容量への影響は未測定\n\n[内部面の証明と制約](CityRoofCaps.md)、[現行検査](city_roof_caps_validation.json)\n'
if features.get('mountain_detail') is True:
    mountain=json.loads((root/'Docs/mountain_quality_validation.json').read_text())
    summary+='\n## 雪山の稜線・積雪・継ぎ目の追加検査\n\n- 元の高さ関数・水平範囲を維持し、平坦な領域を粗く、曲率が大きい領域を細かく再分割。12バッチだけ変更し、3,756三角形・2,229頂点を追加\n- 密な参照との稜線RMS誤差は指定1280px視点で2.637→0.767px。最高Zは約10.859m上がるため、形状・境界が完全不変とは表記しない\n- 8雪材の色だけに連続した柔らかい積雪の分布を追加。鋭い稜線を除外し、3,637個の法線スロットだけ継ぎ目を共有\n- '+str(mountain['testsRun'])+'件のソース・数値・現行ネイティブ検査: '+mountain['status']+'。12メッシュの圧縮をOffにし、Unity側では接線も再計算する。C#の実行・実描画・容量効果は未測定\n\n[造形・色・法線の個別証明](MountainQuality.md)、[現行検査](mountain_quality_validation.json)\n'
if features.get('shopfront_print_aa') is True:
    printed=json.loads((root/'Docs/shopfront_print_validation.json').read_text())
    summary+='\n## 旧店先の印字と符号化の保持検査\n\n- 元の文字・紋・位置を、印字部分だけ8倍で描き直して面積平均。出力は2048平方のまま、3,853,374個の非印字ピクセル・形状・UVを維持\n- '+str(printed['result']['tests'])+'件の厳密検査。不要な旧PNGの複製は同じ再生成SHA検査へ置き換え、証明を保ったまま約4.18MBのテスト重複を除去\n- 店先アトラスだけ編集用GLBでもPNGを維持し、JPEGの印字ノイズを防ぐ。この選択はGLBを約4.06MB増やす。Unityは元からPNGを使用するため、実機の画質向上とは混同しない\n\n[印字の保持検査](shopfront_print_validation.json)、[選択的画像符号化](shopfront_lossless_validation.json)、[実モデルの確認視点](ShopPreviewQA.md)\n'
if features.get('shop_personality') is True:
    from shop_personality_contract import validate_native, ORACLE_SHA256
    native_ok,native_detail=validate_native(root,m)
    if not native_ok:raise ValueError('Current shop oracle admission failed: '+str(native_detail))
    staff=json.loads((root/'Docs/staff_access_validation.json').read_text())
    from validation_report_integrity import checked_shop_access_counts
    access_counts=checked_shop_access_counts(root,staff)
    if access_counts['largerGuestContacts']!=13:raise ValueError('Update the reviewed diagnostic wording for changed contacts')
    profile.update(shop_personality_oracle_sha256=ORACLE_SHA256,shop_personality_native_admission=True,nightlife_venues=3,shop_station_ids_retained=49,shop_explicit_colliders=98,unchanged_nonshop_batches=815,retained_root_components=40,baseline_source_batches=1058,source_batch_delta=m['visualMeshCount']-1058,measured_draw_calls=None)
    (root/'Docs/WindowsProfile.json').write_text(json.dumps(profile,indent=2))
    summary+='\n## v2.16 店舗全体の作り直し\n\n- 炭火・麺・おでん・茶房・菓子店と、スナック・カクテルバー・音楽バー。夜の店は3/8（37.5%）\n- v2.16の291店舗バッチを歴史的基準として固定し、その後の限定改訂は別の完全一致契約で検査。店舗外815バッチ、元の鉢・下部構造40部品、外部衝突メッシュは維持\n- 49座席IDは維持するが、座席位置・退出先と98個の店内BoxColliderは新内装へ更新。旧シーンの見た目だけを交換しない\n- 最終実形状の208必須検査と49退出先の接続: '+staff['status']+'。入口・店員・作業経路は半径0.325m/高さ2.2m、客経路・移乗は半径0.25m、着席胴体は半径0.28mの設計包絡\n- 大きい客半径0.325mの追加診断13件は家具に接触。全体の任意体格対応やVR実行を保証しない。連続移乗検査は実際のVRCStation退出移動のシミュレーションではない\n- 頂点 '+format(vertices,',')+'、三角形 '+format(triangles,',')+'。ソースバッチは1,058→'+str(m['visualMeshCount'])+'（'+str(m['visualMeshCount']-1058)+'増）。実描画コール・FPS・Unity配信容量は未測定\n- 旧107暖簾部品は完全な歴史的復元テストで照合し、現行店舗は新しい完全一致契約で別途検査\n\n[店舗構成と境界](ShopPersonalityDesign.md)、[変更点](RELEASE_NOTES_2.16.0.md)、[独立レビュー](IndependentReview_2.16.0.md)\n'
if 'shop_rpg_identity' in features or 'venue_lighting_identity' in features:
    from rpg_identity_contract import validate_native as validate_rpg_native, ORACLE_SHA256 as RPG_ORACLE_SHA256
    rpg_ok,rpg_detail=validate_rpg_native(root,m)
    if not rpg_ok:raise ValueError('Current RPG revision admission failed: '+str(rpg_detail))
    from venue_lighting import load_profile as load_lighting_profile, validate_manifest as validate_lighting_manifest, PROFILE_RELATIVE as LIGHTING_RELATIVE
    lighting_profile=load_lighting_profile(root/LIGHTING_RELATIVE) if features.get('venue_lighting_identity') is True else None
    validate_lighting_manifest(m,lighting_profile)
    owned=[x for x in m['lights'] if 'venueLighting' in x]
    clones=[x for x in m['materials'] if x['name'].startswith('VenueLight_')]
    names=[x['displayName'] for x in m['shopPersonality']['shops']]
    profile.update(rpg_revision_oracle_sha256=RPG_ORACLE_SHA256,rpg_revision_native_admission=True,rpg_shop_names=names,
        venue_lighting_owned_existing_points=len(owned),venue_lighting_unrelated_points=len(m['lights'])-len(owned),venue_emitter_material_clones=len(clones))
    (root/'Docs/WindowsProfile.json').write_text(json.dumps(profile,indent=2))
    summary+='\n## v2.17 RPGの店名・書体・店舗別照明\n\n- 現行のメッシュ・メタデータ・ソース・アトラス・実装依存を固定した別契約へ完全一致。旧v2.16の契約は改変せず、認証後の歴史的な投影で引き続き検査\n- 店名: '+ '、'.join(names)+'\n- 字画の引き伸ばしを避けた看板UVと、ライセンス付き日本語フォントの同梱・再生成。このv2.17の文字・照明変更単独では形状・座席・退出先・衝突をv2.16から維持。後続の造形追加は各改訂の範囲を参照\n- 既存店内照明 '+str(len(owned))+' 灯だけに静的な配色と有効強度倍率。店舗外 '+str(len(m['lights'])-len(owned))+' 灯は維持。発光材質の専用複製 '+str(len(clones))+' 件。灯数やRealtime灯は追加しない\n- Blenderでは実モデルを確認したが、Unityベイク・顔の実際の色被り・両眼表示・実行負荷の試験ではない\n\n[変更点](RELEASE_NOTES_2.17.0.md)、[照明の範囲と限界](VenueLighting.md)、[書体・UVの出典](RpgIdentityHandoff.md)\n'
if features.get('s05_pendant_refinement') is True:
    from s05_pendant_contract import load_oracle as load_pendant_oracle, ORACLE_SHA256 as PENDANT_ORACLE_SHA256
    pendant=load_pendant_oracle(root)
    info=m['s05PendantRefinement']
    if (info['capCount'],info['stileCount'],info['addedTriangles'])!=(4,12,144):raise ValueError('Unexpected approved pendant counters')
    profile.update(s05_pendant_oracle_sha256=PENDANT_ORACLE_SHA256,s05_pendant_added_triangles=info['addedTriangles'],s05_pendant_caps=info['capCount'],s05_pendant_stiles=info['stileCount'])
    (root/'Docs/WindowsProfile.json').write_text(json.dumps(profile,indent=2))
    summary+='\n## v2.18 茶房の木枠照明\n\n- 既存4枚の面取り付き上下枠の形状を保持し、既存の暗い木材へ変更。12本の控えめな縦格子を追加\n- この改訂単独で144三角形・288頂点・1ソースバッチを追加。和紙の発光面・全体外形・2灯の位置と配色・座席・退出先・通路・衝突は維持\n- 新しい材質・テクスチャ・ライトは追加しない。既存v2.17オラクルは変更せず、新しい完全一致契約で認証\n\n[限定変更](RELEASE_NOTES_2.18.0.md)、[同条件の実モデル比較](s05_pendant_preview_comparison.json)\n'
if features.get('venue_projecting_signs') is True:
    # rpg_detail was produced above through the exact outer v2.19 native gate.
    sign_metrics=projecting_sign_metrics(root,m,rpg_detail)
    profile.update(sign_metrics)
    (root/'Docs/WindowsProfile.json').write_text(json.dumps(profile,indent=2))
    summary+='\n## v2.19 立体看板と店先の旗\n\n- 8店舗に小さな立体紋章、3店舗に実体付きの旗。茶房は既存の濃い木材と明るい木彫りで月と茶器を表現\n- v2.18の全'+format(sign_metrics['projecting_sign_preserved_native_batches'],',')+'ネイティブバッチと全旧GLB配列・配置・材質を保持。追加は'+str(sign_metrics['projecting_sign_added_batches'])+'バッチ・'+format(sign_metrics['projecting_sign_added_triangles'],',')+'三角形・'+format(sign_metrics['projecting_sign_added_native_vertices'],',')+'頂点。店名・書体・49席・照明・衝突・経路は維持\n- ネイティブ材質定義は'+str(sign_metrics['native_material_definitions'])+'のまま。既存Noren1/Noren3を新しい旗に使用するため、GLB使用材質は108→'+str(sign_metrics['glb_used_materials'])+'、埋込み画像は33→'+str(sign_metrics['glb_embedded_images'])+'。追加の1画像は既存の織布ARMで、元テクスチャファイル・シェーダー・ライトの新規追加は0\n- 新しい看板と旗も除外せず、実描画三角形による208必須アクセス検査に含める。別々の店先範囲、面の巻き順、閉じた布形状とUV密度を検査。旧暖簾の非使用検査は歴史的分岐に残す\n- 新しい完全一致契約へ認証してから旧契約へ投影。斜めの実モデル画像は制作確認であり、Unityの描画・VR歩行・速度・配信容量の実測ではない\n\n[現行変更契約](peer_contract_validation.json)、[編集用GLB](shop_personality_glb_validation.json)、[実形状のアクセス](staff_access_validation.json)\n'
(root/'Docs/Validation.md').write_text(summary)
print(json.dumps(profile,indent=2))
