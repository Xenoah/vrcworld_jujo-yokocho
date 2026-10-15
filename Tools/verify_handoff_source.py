"""Reconcile current MCP instructions and retained entrance previews, without Unity.

Run with --write to regenerate only the two named JSON reports. The default
checks that their recorded contents still match current source. No rendering,
Unity execution, approval-pin edits, or historical-evidence rewriting occurs.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import io
import json
import re
import shutil
import struct
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ENTRY = "Assets/TreeTopYokochoEntrySystems"
CORE = "Assets/TreeTopYokocho"
INTEGRATION = "Assets/TreeTopYokochoIntegration/Editor"
SETUP = "Docs/MCP_UNITY_SETUP_JA.md"
HISTORY = "Docs/History/MCP_CORE_ENTRY_0.1_REFERENCE_JA.md"
INSTALLER = ENTRY + "/Editor/EntrySystemsInstaller.cs"
BUILDER = ENTRY + "/Editor/EntryPlazaBuilder.cs"
CONFIG = ENTRY + "/EntryPlaza/Data/EntryPlaza.json"
NATIVE = ENTRY + "/EntryPlaza/Data/EntryPlazaMeshes.bytes"
ATLAS = ENTRY + "/Textures/entry_control_labels.png"
RENDER = "Source/render_entry_preview.py"
PROVENANCE = "Docs/entry-preview-provenance.json"
MANIFEST = CORE + "/Data/WorldManifest.json"
CORE_SHA = "aa513b1c948ba9353a08c3d9eea6f4852f5d8ffa05715f036ea27d19f003d466"

# Retained 0.1.0 archive's 93-file PACKAGE_MANIFEST identities. These are
# historical checkpoints, not hashes regenerated to accept changed evidence.
HISTORICAL_PINS = {
    PROVENANCE: "a684f904bf917001f8325a97229b25b9ddaf2741e8ddddfb343c1da4bba9a1c1",
    RENDER: "e64f531c3c6b801cdb300eaf92ab40a315901b11707911275e76f947961b6588",
    "Docs/STATUS_LAYOUT_REVIEW.md": "3d7276e9f9a315a0608dd6dd868cd67136d60e309fd3dbfb552f61ccc172d2bc",
    "Preview/entry-controls-static-layout.png": "af40d5ce65f7227cab456164cbc9b516837603c6155a97909707c0e9b0ab9fb1",
    "Preview/entry-guideboard-interaction-distance.png": "d583d23a179058d8c2b3e23e694a94ae573deaa4a2dd46b8dd70b047720a18ec",
    "Preview/entry-plaza-native-eye.png": "e8a21a55e682ef3ef5ebf7e1646db5ac5578e33d237bd9b4cd92936460971396",
    "Preview/entry-plaza-native-oblique.png": "15086e81f15d6314fc8a92083c5ca34451e50cabe40be2467d4b719adccc240a",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(root, path):
    return (root / path).read_text(encoding="utf-8")


def load(root, path):
    return json.loads(read(root, path))


def hashes(root, paths):
    return {p: digest(root / p) for p in sorted(set(paths))}


def match(pattern, text, label):
    result = re.search(pattern, text, re.S)
    require(result is not None, "Unsupported/missing source structure: " + label)
    return result


def unity(point):
    return [point[0], point[2], point[1]]


def close(a, b, tolerance=1e-8):
    require(len(a) == len(b), "Vector/array size differs")
    require(all(abs(x - y) <= tolerance for x, y in zip(a, b)), f"Values differ: {a} != {b}")


def eval_math(node, values):
    """Only arithmetic/list literals from the retained preview, never exec/eval."""
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.Name):
        return values[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        return [eval_math(x, values) for x in node.elts]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -eval_math(node.operand, values)
    if isinstance(node, ast.BinOp):
        a, b = eval_math(node.left, values), eval_math(node.right, values)
        if isinstance(node.op, ast.Add): return a + b
        if isinstance(node.op, ast.Sub): return a - b
        if isinstance(node.op, ast.Mult): return a * b
        if isinstance(node.op, ast.Div): return a / b
    raise ValueError("Unsupported preview arithmetic: " + ast.dump(node))


def source_menus(root, docs):
    result = []
    # Parse actual attributes, including menu 0's named constant. Reject any
    # attribute not immediately attached to a public static void method.
    for path in sorted((root / "Assets").rglob("*.cs")):
        code = path.read_text(encoding="utf-8")
        if "[MenuItem(" not in code:
            continue
        namespace = match(r"namespace\s+([\w.]+)", code, "namespace")[1]
        owner = match(r"public\s+static\s+class\s+(\w+)", code, "menu class")[1]
        found = re.findall(r'\[MenuItem\(("[^"\n]+"|\w+)(?:,\s*false,\s*\d+)?\)\]\s*public\s+static\s+void\s+(\w+)\s*\(\s*\)', code)
        require(len(found) == code.count("[MenuItem("), "Unrecognized MenuItem: " + str(path))
        for arg, method in found:
            menu = arg[1:-1] if arg.startswith('"') else match(r'const\s+string\s+' + arg + r'\s*=\s*"([^"]+)"', code, "menu constant")[1]
            suffix = menu.rsplit("/", 1)[-1]
            references = [p for p, text in docs.items() if suffix in text]
            # Audit() appears in two classes. A bare token anywhere in a file
            # is insufficient: require owner qualification or the menu's row.
            method_docs = [p for p, text in docs.items() if owner + "." + method + "()" in text
                           or any(method + "()" in line and (suffix in line or namespace + "." + owner in line)
                                  for line in text.splitlines())]
            require(references and method_docs, "Undocumented menu/method: " + menu)
            if suffix.startswith("0 -"):
                category = "standard integrated entry point"
            elif suffix.startswith("1 -"):
                category = "historical/core-only build; not integrated completion"
            elif suffix.startswith("8 -"):
                category = "advanced Entry-only installer; not integrated completion"
            else:
                category = "diagnostic, maintenance, or explicit bake/setup operation"
            result.append(dict(menu=menu, method=method, qualifiedMethod=namespace + "." + owner + "." + method + "()",
                               source=str(path.relative_to(root)), category=category,
                               menuDocumentedIn=references, methodDocumentedIn=method_docs))
    require(len(result) == 12 and len({x["menu"] for x in result}) == 12, "Expected 12 unique current menus")
    return sorted(result, key=lambda x: x["menu"])


def handoff_report(root):
    docs = {p: read(root, p) for p in (SETUP, HISTORY)}
    current, historical = docs[SETUP], docs[HISTORY]
    menus = source_menus(root, docs)
    installer, builder = read(root, INSTALLER), read(root, BUILDER)
    manifest, config = load(root, MANIFEST), load(root, CONFIG)
    require(digest(root / MANIFEST) == CORE_SHA, "Core manifest differs")
    require(CORE_SHA in current and CORE_SHA in installer and config["preservation"]["coreManifestSha256"] == CORE_SHA, "Manifest admission/docs differ")
    require("通常の入口は" in current and menus[0]["menu"] in current, "Menu 0 is not documented as standard")
    require("core-only" in current and "単独実行を統合完了と呼びません" in current, "Legacy core build distinction missing")
    require("旧手順は今回の標準入口を置き換えません" in current, "Historical instructions not bounded")
    require("Unity/Udon/Shader、音声、network、VR、bake、FPSは未実行" in current, "Unexecuted runtime gates missing")
    require("架空のMCPツール名を作りません" in current, "MCP schema discovery rule missing")
    for path, text in docs.items():
        require(sum(line.lstrip().startswith("```") for line in text.splitlines()) % 2 == 0, "Unbalanced fences: " + path)
    require("return new Vector3(p[0], p[2], p[1]);" in builder, "Source-to-Unity axis conversion differs")
    events = re.findall(r'"(_\w+)"', match(r"string\[\]\s+Events\s*=\s*\{([^}]+)\}", installer, "Events")[1])
    require(len(events) == 6 and "i < 4 ? (UdonSharpBehaviour)clock : bgm" in installer, "Six button targets differ")
    api = []
    runtime_paths = [ENTRY + "/Runtime/" + name + ".cs" for name in ("YokochoGlobalClock", "YokochoBgmController", "YokochoEntryControl")]
    for path in runtime_paths[:2]:
        code = read(root, path)
        for method in re.findall(r"public\s+void\s+(_\w+)\s*\(\s*\)", code):
            require("`" + method + "`" in historical, "Runtime API not documented: " + method)
            indices = [i for i, event in enumerate(events) if event == method]
            for i in indices:
                require((i < 4) == ("GlobalClock" in path), "Runtime event target differs")
            api.append(dict(method=method, source=path, defaultButtonIndices=indices, documentedIn=HISTORY))
    require(len(api) == 13 and sum(bool(x["defaultButtonIndices"]) for x in api) == 6, "Runtime API roster differs")
    control = read(root, runtime_paths[2])
    require('eventName.StartsWith("_")' in control and "target.SendCustomEvent(eventName)" in control, "Local event relay differs")
    warps = []
    for warp in config["warps"]:
        target = unity(warp["destination"])
        text_point = "(" + ",".join(format(v, ".2f").rstrip("0").rstrip(".") for v in target) + ")"
        require(text_point in current, "Warp destination not documented: " + text_point)
        core_name = warp["id"].replace("Entry_", "L1_")
        counterpart = [x for x in manifest["teleports"] if x["name"] == core_name]
        require(len(counterpart) == 1, "Core lift counterpart missing")
        close(warp["destination"], counterpart[0]["destination"], 1e-10)
        close(warp["forward"], counterpart[0]["forward"])
        warps.append(dict(id=warp["id"], sourceDestination=warp["destination"], unityDestination=target,
                          unityForward=unity(warp["forward"]), matchingCoreLift=core_name))
    require(len(warps) == 3, "Warp roster differs")
    shard_path = CORE + "/Data/GeometryShards.json"
    shards = load(root, shard_path)
    require(shards["sha256"] in current and len(shards["shards"]) == 8, "Shard handoff differs")
    sources = [x["source"] for x in menus] + runtime_paths + [BUILDER, CONFIG, MANIFEST, shard_path, SETUP, HISTORY]
    return dict(schemaVersion=2, status="PASS_SOURCE_ONLY", scope="Documentation-to-current-source comparison only. No Unity/MCP command or runtime was executed.",
                standardEntryMenu=menus[0]["menu"], menus=menus, menuCount=len(menus), runtimeApi=api, warpAxis="source Z-up -> Unity (x,z,y)", warps=warps,
                coreManifestSha256=CORE_SHA, historicalDocumentIsReferenceOnly=True,
                checks=["12 actual MenuItem attributes resolved to public methods", "menu/method documentation coverage distinguishes current guide and bounded history",
                        "menu 0 standard; menu 1 core-only; no invented MCP API", "13 underscore APIs exist; six default buttons target correct controller",
                        "manifest hash and three warp destinations/forwards agree with current core", "eight-shard transport identity documented", "runtime gates explicitly unexecuted", "Markdown fences balanced"],
                unityExecuted=False, runtimeVerified=False, sourceHashes=hashes(root, sources))


def button_layout(root, config):
    code, render = read(root, INSTALLER), read(root, RENDER)
    num = r"(-?(?:\d+(?:\.\d*)?|\.\d+))f?"
    pattern = r"return new Vector3\(" + num + r"\s*\+\s*\(index % 2 == 0 \?\s*" + num + r"\s*:\s*" + num + r"\),\s*" + num + r"\s*-\s*\(index / 2\)\s*\*\s*" + num + r",\s*" + num + r"\);"
    x0, even, odd, y0, pitch, z0 = map(float, match(pattern, code, "ButtonPosition expression").groups())
    create = match(r"static void CreateButton\([^\n]+\)\s*\{(.*?)\n        \}", code, "CreateButton")[1]
    require("go.transform.position = ButtonPosition(index);" in create, "Button placement no longer uses audited formula")
    size = list(map(float, match(r"collider.size = new Vector3\(" + num + ", " + num + ", " + num + r"\)", create, "collider size").groups()))
    vertex_code = match(r"mesh.vertices = new\[\] \{ (.*?) \};", create, "vertices")[1]
    vertices = [list(map(float, row)) for row in re.findall(r"new Vector3\(" + num + "," + num + "," + num + r"\)", vertex_code)]
    require(len(vertices) == 4, "Four face vertices required")
    require("float low = 1f - (index + 1) / 6f, high = 1f - index / 6f;" in create, "Unsupported atlas row formula")
    uv_code = match(r"mesh.uv = new\[\] \{ (.*?) \};", create, "UVs")[1]
    uv_parts = re.findall(r"new Vector2\((0|1),(low|high)\)", uv_code)
    require(len(uv_parts) == 4, "Four UVs required")
    triangles = [int(v) for v in match(r"mesh.triangles = new\[\] \{ ([\d, ]+) \}", create, "triangles")[1].split(",")]
    # Parse the retained Blender function rather than restating its constants.
    tree = ast.parse(render)
    loops = [n for n in ast.walk(tree) if isinstance(n, ast.For) and ast.unparse(n.target) == "(i, (x, y, z))"]
    require(len(loops) == 1 and "buttonCenters" in ast.unparse(loops[0].iter), "Preview button loop differs")
    loop = loops[0]
    math_nodes = []
    for n in loop.body:
        if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id == "y":
            require(isinstance(n.op, ast.Add), "Preview depth operator changed")
            math_nodes.append(n)
        elif isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ("verts", "low", "high", "uv"):
            math_nodes.append(n)
    require(len(math_nodes) == 5, "Preview arithmetic fields differ")
    face_calls = [n for n in ast.walk(loop) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "from_pydata"]
    require(len(face_calls) == 1, "Preview geometry call differs")
    preview_faces = eval_math(face_calls[0].args[2], {})
    close([i for f in preview_faces for i in [f[0], f[2], f[1]]], triangles)
    anchor = config["systemsControlAnchor"]
    close(unity(size), anchor["buttonSize"])
    require(len(anchor["buttonCenters"]) == 6, "Expected six config buttons")
    rows = []
    max_error = 0.0
    for i, point in enumerate(anchor["buttonCenters"]):
        center = [x0 + (even if i % 2 == 0 else odd), y0 - (i // 2) * pitch, z0]
        close(unity(center), point)
        values = dict(i=i, x=point[0], y=point[1], z=point[2])
        for node in math_nodes:
            if isinstance(node, ast.AugAssign): values["y"] += eval_math(node.value, values)
            else: values[node.targets[0].id] = eval_math(node.value, values)
        actual = [unity([center[j] + v[j] for j in range(3)]) for v in vertices]
        uv = [[int(u), (1 - (i + 1) / 6) if band == "low" else (1 - i / 6)] for u, band in uv_parts]
        for a, b in zip(actual, values["verts"]):
            close(a, b)
            max_error = max(max_error, max(abs(x - y) for x, y in zip(a, b)))
        for a, b in zip(uv, values["uv"]): close(a, b)
        for v in actual:
            for axis in (0, 2): require(anchor["usableMin"][axis] <= v[axis] <= anchor["usableMax"][axis], "Label exceeds panel")
        rows.append(dict(index=i, unityCenter=center, sourceCenter=unity(center), colliderSizeUnity=size,
                         faceVerticesSource=actual, uv=uv, matchesRetainedPreview=True))
    return dict(buttonCount=6, comparison="Current C# literals/formula vs current config and authenticated retained Python preview AST; not Unity mesh execution.",
                maxIdealArithmeticVertexDeltaMeters=max_error, floatingPointScope="Ideal source-number comparison; actual Unity float32/mesh rendering remains unexecuted.",
                faceSizeMeters=[max(v[0] for v in vertices) - min(v[0] for v in vertices), max(v[1] for v in vertices) - min(v[1] for v in vertices)],
                unityTriangles=triangles, previewSourceTriangles=preview_faces, winding="Y/Z swap reverses handedness; triangle order reversed in source-space preview.",
                sourcePositiveYReadableUFlip=uv_parts == [("1", "low"), ("0", "low"), ("0", "high"), ("1", "high")],
                viewerLeftColumnFirst=even > odd, buttons=rows)


def native_counts(path):
    data = path.read_bytes()
    f = io.BytesIO(data)
    require(f.read(4) == b"JYWM", "Native signature differs")
    version, count = struct.unpack("<II", f.read(8))
    require(version == 1, "Native version differs")
    triangles = 0
    for _ in range(count):
        for _ in range(2):
            length, = struct.unpack("<I", f.read(4))
            require(len(f.read(length)) == length, "Truncated native name")
        nv, ni = struct.unpack("<II", f.read(8))
        require(ni % 3 == 0, "Incomplete triangle")
        f.seek(nv * 24 + ni * 4, 1)
        triangles += ni // 3
    require(f.tell() == len(data), "Truncated/trailing native data")
    return dict(batches=count, triangles=triangles)


def preview_report(root):
    for path, expected in HISTORICAL_PINS.items():
        require(digest(root / path) == expected, "Historical evidence changed: " + path)
    historical, config = load(root, PROVENANCE), load(root, CONFIG)
    current_hashes = hashes(root, (CONFIG, NATIVE, ATLAS, INSTALLER, BUILDER, RENDER, MANIFEST, "Docs/control_asset_provenance.json", "Docs/STATUS_LAYOUT_REVIEW.md"))
    for path, key in ((CONFIG, "entryConfigSha256"), (NATIVE, "entryNativeSha256")):
        require(current_hashes[path] == historical[key], "Preview input hash differs: " + path)
    require(current_hashes[ATLAS] == historical["controlProof"]["atlasSha256"], "Control atlas differs")
    atlas = (root / ATLAS).read_bytes()
    require(atlas[:8] == b"\x89PNG\r\n\x1a\n", "Atlas is not PNG")
    dimensions = list(struct.unpack(">II", atlas[16:24]))
    require(dimensions == [960, 1824], "Atlas dimensions differ")
    for path, expected in load(root, "Docs/control_asset_provenance.json")["outputs"].items():
        require(digest(root / path) == expected, "Control asset provenance differs: " + path)
    approved = re.findall(r'\{ "((?:Data|Textures)/[^"\n]+)", "([0-9a-f]{64})" \}', read(root, BUILDER))
    require(len(approved) == 10, "Entrance literal approval roster differs")
    for path, expected in approved:
        require(digest(root / (ENTRY + "/EntryPlaza/" + path)) == expected, "Entrance asset differs: " + path)
    counts = native_counts(root / NATIVE)
    require(counts == dict(batches=config["meshCount"], triangles=config["triangles"]), "Native counts/config differ")
    require(counts["triangles"] == historical["triangleCounts"]["entry"], "Historical native triangle count differs")
    layout = button_layout(root, config)
    require(layout["sourcePositiveYReadableUFlip"] == historical["controlProof"]["sourcePositiveYReadableUFlip"], "UV flip differs")
    require(layout["viewerLeftColumnFirst"] == historical["controlProof"]["viewerLeftColumnFirst"], "Column order differs")
    installer = read(root, INSTALLER)
    for token in ("new Color(.10f, .16f, .13f)", "135.78f, -31.575f), .012f", "135.65f, -31.575f), .008f", "finally { text.text = original; }", "wide <= narrow * 1.5f"):
        require(token in installer, "Current status safeguards differ: " + token)
    return dict(schemaVersion=1, status="PASS_CURRENT_STATIC_RECONCILIATION_WITH_HISTORICAL_DIFF_LIMITATION",
                scope="Reconciles retained historical images to current static entrance inputs and six control faces only. Does not relabel old images as newly rendered or current integrated PBR/Unity screenshots.",
                imageRerendered=False, unityExecuted=False, runtimeVerified=False, historicalProvenanceUnmodified=True,
                retainedHistoricalIdentities=HISTORICAL_PINS, currentInputHashes=current_hashes, allTenPlazaAssetsMatchBuilderPins=True,
                configNativeAtlasMatchHistoricalPreview=True, nativeGeometry=counts, controlAtlasPixels=dimensions, controlLayout=layout,
                installerRevision=dict(historicalSha256=historical["controlProof"]["installerSha256"], currentSha256=current_hashes[INSTALLER],
                    fullHistoricalSourceAvailable=False, historicalDiffReexecuted=False, status="NOT_REEXECUTED_OLD_SOURCE_NOT_RETAINED",
                    historicalTestimonySource="Docs/STATUS_LAYOUT_REVIEW.md",
                    historicalTestimony="The retained review says subsequent changes were dynamic-status ink, character size, and audit code only. This is historical testimony, not a newly reconstructed full-file diff.",
                    independentlyVerifiedNow="Current dark status ink, small text sizes, known-string differential bounds guard and finally restoration exist. Six static face centers, dimensions, vertices, triangle orientation and UVs match retained render arithmetic and unchanged config/atlas.",
                    limitation="Cannot independently prove the complete old-to-current installer delta without the old cac299... source bytes. No missing source was synthesized or approval hash rewritten."),
                remainingGates=["Unity/Udon compilation and importer execution", "dynamic TextMesh bounds/readability in Unity and VR", "saved-scene/reload/no-op behavior", "interaction, audio and multiplayer", "current original-PBR integrated visual review", "bake, build size and headset performance"])


def self_test(root, reports):
    """Exercise mismatch rejection on throwaway copies, never candidate inputs."""
    paths = set(reports["Docs/mcp-handoff-source-check.json"]["sourceHashes"])
    paths.update(reports["Docs/entry-preview-current-reconciliation.json"]["currentInputHashes"])
    paths.update(HISTORICAL_PINS)
    for folder in ("EntryPlaza", "Fonts"):
        paths.update(str(p.relative_to(root)) for p in (root / ENTRY / folder).rglob("*") if p.is_file())
    cases = [
        ("standard menu", SETUP, "通常の入口は", "旧作業は", handoff_report),
        ("documented warp axis", SETUP, "(-16,140.08,-18.55)", "(-16,-18.55,140.08)", handoff_report),
        ("runtime API", ENTRY + "/Runtime/YokochoBgmController.cs", "public void _NextTrack()", "public void _NextTrackRenamed()", handoff_report),
        ("undocumented menu", INTEGRATION + "/IntegratedPreviewBuilder.cs", "0 - Build or Complete Preview", "0 - Build Unexpected Preview", handoff_report),
        ("button pitch", INSTALLER, "135.50f - (index / 2) * .24f", "135.50f - (index / 2) * .25f", preview_report),
        ("button width", INSTALLER, "new Vector3(-.30f,-.095f,.019f)", "new Vector3(-.31f,-.095f,.019f)", preview_report),
        ("button UV", INSTALLER, "new Vector2(1,low), new Vector2(0,low)", "new Vector2(0,low), new Vector2(1,low)", preview_report),
        ("historical provenance", PROVENANCE, "Exact v2.19", "Exact v2.18", preview_report),
    ]
    def rejected(check, temp, name):
        try:
            check(temp)
        except ValueError:
            print("EXPECTED_REJECTION " + name)
        else:
            raise ValueError("Unexpected acceptance: " + name)
    with tempfile.TemporaryDirectory(prefix="yokocho-handoff-negative-") as directory:
        temp = Path(directory)
        for path in paths:
            (temp / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / path, temp / path)
        for name, path, old, new, check in cases:
            file = temp / path
            original = file.read_text(encoding="utf-8")
            require(old in original, "Negative fixture no longer applies: " + name)
            try:
                file.write_text(original.replace(old, new), encoding="utf-8")
                rejected(check, temp, name)
            finally:
                file.write_text(original, encoding="utf-8")
        for path in (NATIVE, ATLAS, "Preview/entry-controls-static-layout.png"):
            file = temp / path
            original = file.read_bytes()
            try:
                file.write_bytes(original + b"changed")
                rejected(preview_report, temp, path)
            finally:
                file.write_bytes(original)
    print("11 negative cases rejected; candidate inputs untouched.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true", help="Regenerate only the two current reconciliation JSONs")
    parser.add_argument("--self-test", action="store_true", help="Also reject 11 mutations in temporary copies")
    args = parser.parse_args()
    root = args.root.resolve()
    reports = {"Docs/mcp-handoff-source-check.json": handoff_report(root), "Docs/entry-preview-current-reconciliation.json": preview_report(root)}
    if args.self_test:
        self_test(root, reports)
    # Both computations must pass before any report mutation.
    for path, report in reports.items():
        if args.write:
            (root / path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            require(load(root, path) == report, "Stale report; review source then regenerate explicitly: " + path)
        print(report["status"] + " " + path)
    print("12 menus; 13 runtime APIs; 3 warp axes; 10 plaza pins; 43 native batches / 2664 triangles; 6 static control faces. No Unity or rendering executed.")


if __name__ == "__main__":
    main()
