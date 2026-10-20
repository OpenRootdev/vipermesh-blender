"""Generate signature-accurate JSON Schema without importing bpy or parsing prose."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--addon")
parser.add_argument("--output")
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
source = Path(args.addon) if args.addon else next(path for path in [
    root / "addon/vipermesh-addon.py", root / "desktop/assets/vipermesh-addon.py"] if path.is_file())
target = Path(args.output) if args.output else root / "lib/blender/tool-input-schemas.json"
tree = ast.parse(source.read_text(encoding="utf8"))
server = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "BlenderMCPServer")
methods = {node.name: node for node in server.body if isinstance(node, ast.FunctionDef)}
handlers = {}
for node in ast.walk(methods["_execute_command_internal"]):
    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and isinstance(key.value, str) and isinstance(value, ast.Attribute):
                if isinstance(value.value, ast.Name) and value.value.id == "self":
                    handlers[key.value] = methods[value.attr]

STRING_FIELDS = set("name other_name reference_name object_name target_name collection_name camera_name material_name new_name filepath output_path image_path checkpoint_filepath original_filepath code query category tags style source asset_id addon_module operator_id preset axis mode format file_format engine resolution primitive_type target_type bone_name armature_name mesh_name modifier_name constraint_name action_name clip_name root_name pivot method direction type texture_id light_type shading_type".split())
STRING_ARRAY_FIELDS = set("names target_names mesh_names object_names material_names include_names exclude_names source_names target_bones".split())
STRING_FIELDS.update("parent_name modifier_type constraint_type subtarget text font_path modifier source_name candidate_name constraint texture_directory wall_material_name floor_material_name ceiling_material_name new_shape_key_name shape_key_name wall_name fill_material_name frame_material_name result_name asset_type uid name_prefix metarig_name rig_name expected_source_fingerprint child_name uv_map_name target_mode target_armature output_filepath source_armature root_source_bone categories active_name fill_mode display_type easing playback_sync hdri_path".split())
STRING_ARRAY_FIELDS.update("operator_ids bone_names helper_patterns group_names export_names".split())
BOOLEAN_FIELDS = set("set_active mute show_viewport show_render show_in_editmode show_on_cage hide_viewport hide_render collection_hide_viewport collection_hide_render dof_use cyclic show_name show_in_front use_denoising film_transparent use_preview_range show_overlays show_xray".split())
INTEGER_FIELDS = set("columns slot_index move_to_index target_face_count iterations area_index baseline_frame bevel_resolution resolution_x resolution_y resolution_percentage samples frame current_frame frame_start frame_end fps preview_start preview_end".split())
VECTOR_FIELDS = set("location rotation scale dimensions target_location offset translation rotation_offset scale_offset origin center min_bounds max_bounds".split())
NUMBER_FIELDS = set("metallic roughness energy lens sensor_width clip_start clip_end size radius width height depth margin tolerance surface_value distance strength ratio voxel_size angle_limit contact_tolerance minimum_clearance dof_focus_distance dof_aperture_fstop".split())
NUMBER_FIELDS.update("influence spacing row_spacing align_bottom_to_z seam_tolerance alpha emission_strength transmission_weight ior cut_depth frame_depth target_ratio target_edge_length bevel_depth display_size shadow_soft_size spot_size spot_blend slider_min slider_max fps_base angle".split())
VECTOR_FIELDS.update("obj_local_point reference_local_point".split())


def vector(size=3):
    return {"type": "array", "items": {"type": "number"}, "minItems": size, "maxItems": size}


def field_schema(name, default):
    if isinstance(default, bool) or name in BOOLEAN_FIELDS:
        return {"type": "boolean"}
    if name in INTEGER_FIELDS:
        return {"type": "integer"}
    if isinstance(default, (int, float)):
        return {"type": "number"}
    if name in VECTOR_FIELDS:
        return vector()
    if name in {"color", "base_color", "background_color", "emission_color"}:
        return {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 4}
    if name in STRING_ARRAY_FIELDS:
        return {"type": "array", "items": {"type": "string"}}
    if name in STRING_FIELDS:
        return {"type": "string"}
    if name in NUMBER_FIELDS:
        return {"type": "number"}
    if isinstance(default, str):
        return {"type": "string"}
    if isinstance(default, (list, tuple)):
        return {"type": "array"}
    if isinstance(default, dict):
        return {"type": "object"}
    # Arbitrary nested configuration remains JSON, with semantic checks in Blender.
    return {"description": "JSON value; operation-specific shape is validated by Blender.", "x-blender-validation": "runtime"}


OVERRIDES = {
    ("import_local_asset", "scale"): {"anyOf": [{"type": "number"}, vector()]},
    ("create_mesh_from_data", "vertices"): {"type": "array", "items": vector()},
    ("create_mesh_from_data", "faces"): {"type": "array", "items": {"type": "array", "items": {"type": "integer"}, "minItems": 3}},
    ("create_mesh_from_data", "edges"): {"type": "array", "items": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2}},
    ("set_shape_key_value", "value"): {"type": "number"},
    ("retarget_animation_clip", "bone_map"): {"type": "object"},
}

# Blender normalizes case and accepts aliases. Examples must not reject those.
EXAMPLES = {
    ("align_object_to_surface", "placement"): ["GROUND", "ON_TOP", "SIDE_POSITIVE", "SIDE_NEGATIVE"],
    ("align_object_to_surface", "axis"): ["X", "Y", "Z"],
    ("set_viewport_shading", "shading_type"): ["WIREFRAME", "SOLID", "MATERIAL", "RENDERED"],
    ("add_light", "light_type"): ["POINT", "SUN", "SPOT", "AREA"],
}

tools = {}
signatures = []
for name, node in sorted(handlers.items()):
    positional = node.args.posonlyargs + node.args.args
    defaults = [None] * (len(positional) - len(node.args.defaults)) + node.args.defaults
    fields = [(arg, default) for arg, default in zip(positional, defaults) if arg.arg != "self"]
    fields += list(zip(node.args.kwonlyargs, node.args.kw_defaults))
    properties, required = {}, []
    for arg, default_node in fields:
        default = ast.literal_eval(default_node) if default_node is not None else None
        schema = OVERRIDES.get((name, arg.arg), field_schema(arg.arg, default))
        if (name, arg.arg) in EXAMPLES:
            schema = {**schema, "examples": EXAMPLES[name, arg.arg],
                      "description": "Preferred values shown as examples; Blender validates normalized values and aliases.",
                      "x-blender-validation": "runtime"}
        if default_node is None:
            required.append(arg.arg)
        elif default is None:
            schema = {"anyOf": [schema, {"type": "null"}]}
        properties[arg.arg] = schema
    tools[name] = {"type": "object", "properties": properties, "required": required,
                   "additionalProperties": node.args.kwarg is not None}
    # Normalize values ourselves: AST repr fields differ between Python versions.
    signatures.append([name, [
        [arg.arg, default is not None, ast.literal_eval(default) if default is not None else None]
        for arg, default in fields
    ], len(node.args.posonlyargs), [arg.arg for arg in node.args.kwonlyargs],
        node.args.vararg.arg if node.args.vararg else None,
        node.args.kwarg.arg if node.args.kwarg else None])
report = {"schemaVersion": 1, "signatureSha256": hashlib.sha256(json.dumps(signatures).encode()).hexdigest(), "tools": tools}
text = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
if args.check:
    if not target.is_file() or target.read_text(encoding="utf8") != text:
        raise SystemExit("Blender input schemas are stale; regenerate after reviewing changed signatures")
else:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf8", newline="\n")
print(f"{'Checked' if args.check else 'Generated'} {len(tools)} Blender handler input schemas")
