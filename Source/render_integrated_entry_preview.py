"""New integrated entrance SOURCE proof; never rewrites historical previews.

Audit without Blender/rendering:
  python Source/render_integrated_entry_preview.py --source-audit ROOT
After final maps/plan are supplied and rendering is authorized:
  blender -b -t 4 -P Source/render_integrated_entry_preview.py -- --render ROOT
Optional --eye adds the unchanged historical eye camera. Only the new
Preview/IntegratedEntry/*.png and Docs/integrated-entry-preview-provenance.json
are written. This is not a Unity shader, lighting, Udon, or VRChat screenshot.
"""
from pathlib import Path
from collections import Counter
import argparse
import gzip
import hashlib
import importlib.util
import json
import re
import sys

import numpy as np

CORE = "Assets/TreeTopYokocho"
ENTRY = "Assets/TreeTopYokochoEntrySystems"
PLAN = "Assets/TreeTopYokochoOriginalPbr/Data/OriginalPbrPlan.json"
PBR_INSTALLER = "Assets/TreeTopYokochoIntegration/Editor/OriginalPbrInstaller.cs"
MANIFEST_SHA = "aa513b1c948ba9353a08c3d9eea6f4852f5d8ffa05715f036ea27d19f003d466"
NATIVE_SHA = "5c747087ae2327374123be906bdcc5139909c9a30ad89487ade275fb4839674a"
CLIP = [[-12, -35, 133.5], [10, -25.55, 138]]
VIEWS = [
    dict(file="integrated-entry-oblique.png", camera=[-3.5, -25.8, 138.7], target=[-6.2, -30.2, 135.2], lens=28),
    dict(file="integrated-entry-eye.png", camera=[-3.7, -28.6, 135.7], target=[-6.1, -31.7, 135.45], lens=22),
]
SLOTS = {"_MainTex": "texture", "_BumpMap": "normal", "_ARM": "arm", "_HeightMap": "height"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def module(root, relative, name):
    spec = importlib.util.spec_from_file_location(name, root / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def safe_path(root, relative):
    path = root / relative
    require(not Path(relative).is_absolute() and ".." not in Path(relative).parts,
            "Unsafe input path: " + relative)
    require(path.resolve().is_relative_to(root), "Input escaped package root: " + relative)
    return path


def prepare(root, require_plan):
    """Authenticate sources and produce immutable geometry/material inputs."""
    hashes = {}
    def track(relative, expected=None):
        path = safe_path(root, relative)
        digest = sha(path)
        if expected is not None:
            require(digest == expected, "Input digest differs: " + relative)
        hashes[relative] = digest
        return path
    manifest_path = track(CORE + "/Data/WorldManifest.json", MANIFEST_SHA)
    manifest = json.loads(manifest_path.read_text())
    config_path = track(ENTRY + "/EntryPlaza/Data/EntryPlaza.json")
    config = json.loads(config_path.read_text())
    audit = module(root, "Tools/verify_handoff_source.py", "integrated_entry_handoff")
    reconciliation = audit.preview_report(root)  # Read-only numeric/retained-input checks.
    require(reconciliation["controlLayout"]["buttonCount"] == 6, "Six controls required")
    old = json.loads(track("Docs/entry-preview-provenance.json").read_text())
    require(old["contextClip"] == CLIP, "Historical context clip differs")
    for new, previous in zip(VIEWS, old["views"]):
        require(all(new[key] == previous[key] for key in ("camera", "target", "lens")), "Historical camera differs")
    geometry = module(root, "Source/entry_geometry_io.py", "integrated_entry_geometry")
    transport = json.loads(track(CORE + "/Data/GeometryShards.json").read_text())
    require(len(transport["shards"]) == 8, "Expected eight immutable visual shards")
    packed = []
    for shard in transport["shards"]:
        path = track(CORE + "/Data/" + shard["name"], shard["sha256"])
        require(path.stat().st_size == shard["bytes"], "Shard byte count differs")
        packed.append(path.read_bytes())
    packed = b"".join(packed)
    require(hashlib.sha256(packed).hexdigest() == transport["sha256"], "Combined gzip differs")
    raw = gzip.decompress(packed)
    require(hashlib.sha256(raw).hexdigest() == NATIVE_SHA, "Core native geometry differs")
    core_meshes = geometry.parse_geometry(raw)
    del raw, packed
    entry_path = track(ENTRY + "/EntryPlaza/Data/EntryPlazaMeshes.bytes", old["entryNativeSha256"])
    entry_meshes = geometry.parse_geometry(entry_path.read_bytes())
    require(sum(len(x["faces"]) for x in entry_meshes) == 2664, "Entry native triangle count differs")
    materials = {x["name"]: dict(x) for x in manifest["materials"]}
    native_counts = Counter(x["material"] for x in core_meshes)
    plan = None
    admission = "PENDING_MAPS_AND_PLAN"
    replacements = {}
    if (root / PLAN).is_file():
        plan_path = track(PLAN)
        plan = json.loads(plan_path.read_text())
        plan_builder = module(root, "Tools/build_original_pbr_plan.py", "integrated_entry_plan")
        require(plan_path.read_bytes() == plan_builder.encode(plan_builder.build(root)), "Material plan is not current/reproducible")
        require(plan["baselineManifestSha256"] == MANIFEST_SHA and len(plan["materials"]) == 31 and len(plan["maps"]) == 16, "Unexpected material plan")
        for pin in plan["baselineFiles"] + plan["maps"]:
            track(pin["path"], pin["sha256"])
        for row in plan["materials"]:
            require(native_counts[row["name"]] == row["expectedRendererCount"], "Native material count differs")
            for slot in row["slots"]:
                field = SLOTS[slot["property"]]
                require(CORE + "/Textures/" + materials[row["name"]][field] == slot["originalPath"], "Source material mapping differs")
                replacements[(row["name"], field)] = slot["replacementPath"]
        code = track(PBR_INSTALLER).read_text()
        frozen = re.search(r'ApprovedPlanSha256 = "([^"]+)";', code)
        require(frozen is not None, "Installer admission constant missing")
        admission = "ADMITTED" if frozen[1] == sha(plan_path) else "SOURCE_PREVIEW_ONLY_NOT_INSTALLER_ADMITTED"
        if not frozen[1].startswith("UNFROZEN"):
            require(admission == "ADMITTED", "Frozen installer hash disagrees with preview plan")
    elif require_plan:
        raise ValueError("PENDING: final OriginalPbrPlan.json and all sixteen maps are required; no render started")
    used = Counter()
    clipped = []
    for mesh in core_meshes:
        triangles = mesh["vertices"][mesh["faces"]]
        keep = np.all(triangles.max(axis=1) > CLIP[0], axis=1) & np.all(triangles.min(axis=1) < CLIP[1], axis=1)
        if np.any(keep):
            selected = dict(mesh)
            selected["faces"] = mesh["faces"][keep]
            clipped.append(selected)
            used[mesh["material"]] += int(keep.sum())
    require(sum(used.values()) == 29032, "Historical core excerpt triangle count differs")
    bindings = {}
    for name in used:
        spec = materials[name]
        bindings[name] = {}
        for field in SLOTS.values():
            if spec.get(field):
                relative = replacements.get((name, field), CORE + "/Textures/" + spec[field])
                bindings[name][field] = str(track(relative).relative_to(root))
    for spec in config["materials"]:
        if spec.get("texture"):
            track(ENTRY + "/EntryPlaza/Textures/" + spec["texture"])
    track(ENTRY + "/Textures/entry_control_labels.png", old["controlProof"]["atlasSha256"])
    for relative in ("Source/render_integrated_entry_preview.py", "Source/render_entry_preview.py", "Source/entry_geometry_io.py",
                     "Tools/verify_handoff_source.py", "Tools/build_original_pbr_plan.py", CORE + "/Editor/YokochoWorldBuilder.cs",
                     CORE + "/Data/FantasyMaterials.json", CORE + "/Data/VenueLighting.json",
                     ENTRY + "/Editor/EntryPlazaBuilder.cs", ENTRY + "/Editor/EntrySystemsInstaller.cs", PBR_INSTALLER):
        track(relative)
    if (root / "Docs/authored_pbr_origin.json").is_file():
        origin = json.loads(track("Docs/authored_pbr_origin.json").read_text())
        track(origin["sourcePath"], origin["sourceSha256"])
    report = dict(status="SOURCE_INPUTS_AUTHENTICATED" if plan else "SOURCE_INPUTS_AUTHENTICATED_PBR_PENDING",
                  scope="Exact retained local native triangles/camera/control arithmetic, with plan-bound Blender material approximation. Not Unity or runtime execution.",
                  sourceHashes=dict(sorted(hashes.items())), coreNativeSha256=NATIVE_SHA, entryNativeSha256=sha(entry_path),
                  contextClip=CLIP, coordinateSystem="Native source Z-up; geometry is not reauthored or axis-converted for Blender",
                  triangleCounts=dict(core=29032, entry=2664, staticControls=12), nativeSourceBatches=len(core_meshes),
                  excerptTrianglesByMaterial=dict(sorted(used.items())), materialBindings=bindings,
                  planAdmission=admission, replacedExcerptMaterials=sorted({name for name, _ in replacements if name in used}),
                  controls=reconciliation["controlLayout"], historicalImagesAndProvenanceModified=False,
                  unityRuntimeVerified=False, unityShaderEquivalent=False, blenderRendered=False)
    return report, clipped, entry_meshes, materials, config


def render(root, prepared, eye):
    import bpy
    from mathutils import Vector
    report, core_meshes, entry_meshes, specs, config = prepared
    require(report["planAdmission"] != "PENDING_MAPS_AND_PLAN", "No render without complete final maps/plan")
    destination = root / "Preview/IntegratedEntry"
    provenance = root / "Docs/integrated-entry-preview-provenance.json"
    views = VIEWS if eye else VIEWS[:1]
    require(not provenance.exists() and all(not (destination / v["file"]).exists() for v in views), "Integrated output already exists; preserve it and explicitly review a new render revision")
    # All source preflight precedes scene/output changes.
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    material_notes = {}
    attribute_readback = dict(meshes=0, uvCorners=0, colorCorners=0, maxUvDelta=0.0, maxColorDelta=0.0)

    def verify_attributes(mesh, expected_uv, expected_colors=None):
        # Adding CustomData layers can invalidate earlier Blender RNA handles.
        # Read by name after every allocation, then reject any wrong channel.
        actual_uv = np.asarray([tuple(x.uv) for x in mesh.uv_layers["UVMap"].data])
        uv_delta = float(np.max(np.abs(actual_uv - np.asarray(expected_uv))))
        require(uv_delta <= 1e-6, "Blender UV readback differs: " + mesh.name)
        attribute_readback["meshes"] += 1
        attribute_readback["uvCorners"] += len(actual_uv)
        attribute_readback["maxUvDelta"] = max(attribute_readback["maxUvDelta"], uv_delta)
        if expected_colors is not None:
            actual = np.asarray([tuple(x.color) for x in mesh.color_attributes["CoreVertexColor"].data])
            color_delta = float(np.max(np.abs(actual - np.asarray(expected_colors))))
            require(color_delta <= 1e-6, "Blender vertex color readback differs: " + mesh.name)
            attribute_readback["colorCorners"] += len(actual)
            attribute_readback["maxColorDelta"] = max(attribute_readback["maxColorDelta"], color_delta)

    def image_node(tree, path, data, uv=None):
        node = tree.nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(root / path), check_existing=True)
        node.image.colorspace_settings.name = "Non-Color" if data else "sRGB"
        node.extension = "REPEAT"
        node.interpolation = "Linear"
        if uv is not None:
            tree.links.new(uv, node.inputs["Vector"])
        return node.outputs["Color"]

    def multiply(tree, left, right=None, constant=None):
        node = tree.nodes.new("ShaderNodeMixRGB")
        node.blend_type = "MULTIPLY"
        node.inputs[0].default_value = 1
        tree.links.new(left, node.inputs[1])
        if right is not None: tree.links.new(right, node.inputs[2])
        else: node.inputs[2].default_value = (*constant[:3], 1)
        return node.outputs[0]

    def core_material(name):
        spec, paths = specs[name], report["materialBindings"][name]
        material = bpy.data.materials.new("IntegratedCore_" + name)
        material.use_nodes = True
        tree = material.node_tree
        bsdf = tree.nodes.get("Principled BSDF")
        uv = tree.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "UVMap"
        scale = spec.get("uvScale", 1)
        scale = scale if scale > 0 else 1
        scaled = tree.nodes.new("ShaderNodeVectorMath")
        scaled.operation = "SCALE"
        scaled.inputs[3].default_value = scale
        tree.links.new(uv.outputs["UV"], scaled.inputs[0])
        coords = scaled.outputs["Vector"]
        if "texture" in paths:
            albedo = image_node(tree, paths["texture"], False, coords)
            albedo = multiply(tree, albedo, constant=spec["color"])
        else:
            color = tree.nodes.new("ShaderNodeRGB")
            color.outputs[0].default_value = (*spec["color"][:3], 1)
            albedo = color.outputs[0]
        emission_color = albedo  # Core Surface emission does not multiply vertex AO.
        vertex = tree.nodes.new("ShaderNodeVertexColor")
        vertex.layer_name = "CoreVertexColor"
        albedo = multiply(tree, albedo, vertex.outputs["Color"])
        bsdf.inputs["Roughness"].default_value = spec.get("roughness", .8)
        bsdf.inputs["Metallic"].default_value = spec.get("metallic", 0)
        if "arm" in paths:
            arm = image_node(tree, paths["arm"], True, coords)
            split = tree.nodes.new("ShaderNodeSeparateColor")
            split.mode = "RGB"
            tree.links.new(arm, split.inputs["Color"])
            # Cycles has no Unity ambient-occlusion input. This intentional
            # diffuse darkening approximation is disclosed in provenance.
            albedo = multiply(tree, albedo, split.outputs["Red"])
            for channel, prop, factor in (("Green", "Roughness", spec.get("roughness", .8)), ("Blue", "Metallic", spec.get("metallic", 0))):
                node = tree.nodes.new("ShaderNodeMath")
                node.operation = "MULTIPLY"
                node.use_clamp = True
                node.inputs[1].default_value = factor
                tree.links.new(split.outputs[channel], node.inputs[0])
                tree.links.new(node.outputs[0], bsdf.inputs[prop])
        tree.links.new(albedo, bsdf.inputs["Base Color"])
        if "normal" in paths:
            normal = tree.nodes.new("ShaderNodeNormalMap")
            normal.space = "TANGENT"
            normal.uv_map = "UVMap"
            strength = spec.get("normalScale", 1)
            normal.inputs["Strength"].default_value = strength if strength > 0 else 1
            tree.links.new(image_node(tree, paths["normal"], True, coords), normal.inputs["Color"])
            tree.links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
        bsdf.inputs["Emission Strength"].default_value = spec.get("emission", 0)
        tree.links.new(emission_color, bsdf.inputs["Emission Color"])
        material_notes[name] = dict(uvScale=scale, numericTint=spec["color"], normalScale=spec.get("normalScale", 1),
                                  roughnessMultiplier=spec.get("roughness", .8), metallicMultiplier=spec.get("metallic", 0),
                                  textureBindings=paths, heightApplied=False, parallaxApplied=False)
        return material

    materials = {("core", name): core_material(name) for name in report["excerptTrianglesByMaterial"]}
    # Preserve the historical entrance material recipe exactly: albedo*tint,
    # scalar roughness/metallic, no newly invented PBR maps or vertex modulation.
    for spec in config["materials"]:
        material = bpy.data.materials.new("entry_" + spec["name"])
        material.use_nodes = True
        tree = material.node_tree
        bsdf = tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*spec["color"][:3], 1)
        bsdf.inputs["Roughness"].default_value = spec.get("roughness", .8)
        bsdf.inputs["Metallic"].default_value = spec.get("metallic", 0)
        if spec.get("texture"):
            color = image_node(tree, ENTRY + "/EntryPlaza/Textures/" + spec["texture"], False)
            if not all(abs(v - 1) < 1e-4 for v in spec["color"][:3]):
                color = multiply(tree, color, constant=spec["color"])
            tree.links.new(color, bsdf.inputs["Base Color"])
        materials[("entry", spec["name"])] = material

    for prefix, source in (("core", core_meshes), ("entry", entry_meshes)):
        for item in source:
            used, flat = np.unique(item["faces"], return_inverse=True)
            vertices, uv = item["vertices"][used], item["uv"][used]
            mesh = bpy.data.meshes.new(prefix + "_" + item["group"])
            mesh.from_pydata(vertices.tolist(), [], flat.reshape(-1, 3).tolist())
            mesh.update()
            obj = bpy.data.objects.new(mesh.name, mesh)
            bpy.context.collection.objects.link(obj)
            mesh.materials.append(materials[(prefix, item["material"])])
            mesh.uv_layers.new(name="UVMap")
            if prefix == "core":
                mesh.color_attributes.new(name="CoreVertexColor", type="FLOAT_COLOR", domain="CORNER")
            # Reacquire BOTH handles only after all layer allocations. Keeping
            # the original UV handle across color_attributes.new can alias the
            # color layer in Blender 4.3.2 (independently reproduced).
            layer = mesh.uv_layers["UVMap"]
            colors = mesh.color_attributes.get("CoreVertexColor")
            expected_uv, expected_colors = [], []
            for polygon in mesh.polygons:
                for vi, li in zip(polygon.vertices, polygon.loop_indices):
                    layer.data[li].uv = uv[vi]
                    expected_uv.append(uv[vi].tolist())
                    if colors is not None:
                        color = tuple(float(v) / 255 for v in item["colors"][used[vi]])
                        colors.data[li].color = color
                        expected_colors.append(color)
            verify_attributes(mesh, expected_uv, expected_colors if colors is not None else None)
    control = bpy.data.materials.new("Owner control atlas (unlit approximation)")
    control.use_nodes = True
    tree = control.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    emission = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(image_node(tree, ENTRY + "/Textures/entry_control_labels.png", False), emission.inputs["Color"])
    tree.links.new(emission.outputs[0], output.inputs[0])
    for row in report["controls"]["buttons"]:
        mesh = bpy.data.meshes.new("OwnerControl" + str(row["index"]))
        mesh.from_pydata(row["faceVerticesSource"], [], report["controls"]["previewSourceTriangles"])
        mesh.update()
        obj = bpy.data.objects.new(mesh.name, mesh)
        bpy.context.collection.objects.link(obj)
        mesh.materials.append(control)
        layer = mesh.uv_layers.new(name="UVMap")
        expected_uv = []
        for polygon in mesh.polygons:
            for vi, li in zip(polygon.vertices, polygon.loop_indices):
                layer.data[li].uv = row["uv"][vi]
                expected_uv.append(row["uv"][vi])
        verify_attributes(mesh, expected_uv)
    world = bpy.data.worlds.new("Review soft dusk environment")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.24, .31, .37, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .5
    bpy.context.scene.world = world
    lights = [("Warm sky", (-5, -28, 145), 2100, 10, (1, .87, .66)), ("Fill", (-1, -24, 140), 1200, 8, (.69, .84, 1))]
    for name, location, energy, size, color in lights:
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size, light.color = energy, "DISK", size, color
        obj = bpy.data.objects.new(name, light)
        bpy.context.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (Vector((-6, -30, 135)) - obj.location).to_track_quat("-Z", "Y").to_euler()
    camera = bpy.data.cameras.new("Entry review")
    obj = bpy.data.objects.new("Entry review", camera)
    bpy.context.collection.objects.link(obj)
    scene = bpy.context.scene
    scene.camera = obj
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1440, 960, 100
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    destination.mkdir(parents=True, exist_ok=True)
    for view in views:
        obj.location = view["camera"]
        obj.rotation_euler = (Vector(view["target"]) - obj.location).to_track_quat("-Z", "Y").to_euler()
        camera.lens = view["lens"]
        scene.render.filepath = str(destination / view["file"])
        bpy.ops.render.render(write_still=True)
    require(all(sha(root / path) == digest for path, digest in report["sourceHashes"].items()), "Inputs changed during rendering; images are not admitted")
    report.update(blenderRendered=True, blenderVersion=bpy.app.version_string, views=views, samples=32, resolution=[1440, 960],
                  imageHashes={str((destination / view["file"]).relative_to(root)): sha(destination / view["file"]) for view in views},
                  materialEvaluation=material_notes, reviewOnlyLights=lights, meshAttributeReadback=attribute_readback,
                  materialModel=dict(albedo="sRGB image decoded by Blender, multiplied by unchanged numeric manifest tint and native vertex RGB; no asserted Unity color-space equivalence",
                                     normal="Non-Color tangent OpenGL (+Y); Blender Normal Map strength follows normalScale, but Unity tangent generation/strength shader math is not replicated",
                                     arm="Non-Color G*roughness and B*metallic, clamped; R multiplied into diffuse as an AO approximation, not Unity indirect-only occlusion",
                                     uv="Native UVs retained; positive manifest uvScale applied to all core texture samples exactly once",
                                     entry="Historical albedo/tint/scalar material recipe and six unlit static label faces retained"),
                  omitted=["Remote scenery outside the exact historical local triangle clip", "Dynamic clock/BGM TextMesh and runtime state", "Unity shaders and fantasy/venue profile effects", "Unity lights, lightmaps, probes, fog, sky and post-processing", "Height displacement and shader parallax", "Unity import caps, BC compression, mip selection and headset stereo", "Unity smoothing/tangent reconstruction; preview uses native topology with Blender default face shading", "Runtime interactions, colliders, networking, audio and performance"])
    provenance.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(status="BLENDER_SOURCE_PREVIEW_RENDERED", provenance=str(provenance), images=report["imageHashes"], unityRuntimeVerified=False), indent=2))


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--source-audit", action="store_true")
    mode.add_argument("--render", action="store_true")
    parser.add_argument("root", type=Path)
    parser.add_argument("--eye", action="store_true")
    options = parser.parse_args(args)
    root = options.root.resolve()
    prepared = prepare(root, require_plan=options.render)
    if options.render:
        render(root, prepared, options.eye)
    else:
        print(json.dumps(prepared[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
