import type { ToolCategory, ToolMetadata } from "../blender/tool-metadata"

export const TOOL_REGISTRY: ToolMetadata[] = [
  {
    name: "get_scene_info",
    description:
      "Summarize the current Blender scene, including object names, counts, and basic transform data. Call this at the start of every plan to capture state.",
    category: "inspection",
    parameters: "(no parameters)",
  },
  {
    name: "get_object_info",
    description:
      "Inspect a specific object by name to retrieve type, transforms, materials, and bounding boxes. Use before modifying or reusing existing geometry.",
    category: "inspection",
    parameters: "name: string (object name)",
  },
  {
    name: "get_all_object_info",
    description:
      "Retrieve detailed info for every object in the scene at once: transforms, materials, modifiers, mesh stats, light/camera data. Use instead of multiple get_object_info calls when you need the full picture.",
    category: "inspection",
    parameters: "max_objects?: number (default 50), start_index?: number (default 0)",
  },
  {
    name: "inspect_blend_file_health",
    description:
      "Inspect .blend file health without mutating the scene: missing external files, linked libraries, packed assets, orphaned datablocks, object type counts, hidden objects, modifiers, constraints, and large-scene warnings.",
    category: "inspection",
    parameters: "max_external_files?: number (default 80), include_object_samples?: boolean (default true)",
  },
  {
    name: "get_blendfile_summary_path_info",
    description:
      "Return saved path, directory, dirty state, and path diagnostics for the current .blend file without mutating the scene.",
    category: "inspection",
    parameters: "(no parameters)",
  },
  {
    name: "get_blendfile_summary_datablocks",
    description:
      "Return datablock counts, object type counts, orphan counts, and optional object samples for the current .blend file.",
    category: "inspection",
    parameters: "include_object_samples?: boolean (default true)",
  },
  {
    name: "get_blendfile_summary_missing_files",
    description:
      "Return missing external file paths and counts for images, libraries, fonts, movie clips, and sounds.",
    category: "inspection",
    parameters: "max_files?: number (default 80)",
  },
  {
    name: "get_blendfile_summary_of_linked_libraries",
    description:
      "Return linked library paths, existence flags, and missing linked-library diagnostics without cleaning or relinking data.",
    category: "inspection",
    parameters: "max_libraries?: number (default 80)",
  },
  {
    name: "get_blendfile_summary_usage_guess",
    description:
      "Return a conservative usage guess for the current .blend based on counts, object types, asset links, lights, cameras, and animation signals.",
    category: "inspection",
    parameters: "(no parameters)",
  },
  {
    name: "save_blend_file",
    description:
      "Save the current Blender scene to an explicit .blend filepath without generated Python. Use for review artifacts, handoff checkpoints, and export/package workflows.",
    category: "advanced",
    parameters: "filepath: string (.blend), make_dirs?: boolean, check_existing?: boolean, copy?: boolean",
  },
  {
    name: "restore_blend_checkpoint",
    description:
      "Restore a saved .blend checkpoint after a failed guarded mutation and return Blender to the original file path.",
    category: "advanced",
    parameters: "checkpoint_filepath: string (.blend), original_filepath: string (.blend)",
  },
  {
    name: "open_blend_file",
    description:
      "Open an existing .blend file as the current session file. Refuses when the current file has unsaved changes unless discard_unsaved=true.",
    category: "advanced",
    parameters: "filepath: string (.blend), discard_unsaved?: boolean, load_ui?: boolean",
  },
  {
    name: "get_viewport_screenshot",
    description:
      "Capture a 3D viewport for visual confirmation. Supports area_index from inspect_viewport_areas for area-specific screenshots.",
    category: "inspection",
    parameters: "area_index?: number, max_size?: number (default 800)",
  },
  {
    name: "render_viewport_to_path",
    description:
      "Save a viewport preview artifact to a file path without changing final render settings. Use for disk-based visual artifacts of the current viewport.",
    category: "inspection",
    parameters: "output_path?: string, max_size?: number (default 1200), format?: string, area_index?: number",
  },
  {
    name: "inspect_viewport_areas",
    description:
      "Inspect available Blender 3D viewport areas and current region_3d state before area-specific screenshots or viewport focus operations.",
    category: "inspection",
    parameters: "(no parameters)",
  },
  {
    name: "set_viewport_shading",
    description:
      "Set 3D viewport shading mode and optional overlay/xray flags without changing scene data. Use before screenshots or user-guided debugging.",
    category: "inspection",
    parameters: "shading_type?: WIREFRAME|SOLID|MATERIAL|RENDERED, area_index?: number, all_areas?: boolean, show_overlays?: boolean, show_xray?: boolean",
  },
  {
    name: "focus_viewport_on_objects",
    description:
      "Frame named or selected objects in a chosen 3D viewport area without changing scene data before taking a screenshot.",
    category: "inspection",
    parameters: "names?: string[], area_index?: number",
  },
  {
    name: "select_scene_objects",
    description:
      "Select scene objects and optionally set the active object for guided debugging or user-visible context.",
    category: "inspection",
    parameters: "names?: string[], active_name?: string, selection_mode?: REPLACE|ADD|REMOVE|TOGGLE",
  },
  {
    name: "set_active_collection",
    description:
      "Set the active Blender layer collection for guided organization/debugging, optionally creating it.",
    category: "inspection",
    parameters: "collection_name: string, create_new?: boolean",
  },
  {
    name: "list_materials",
    description:
      "List existing Blender materials before reusing, assigning, or replacing material slots.",
    category: "materials",
    parameters: "(no parameters)",
  },
  {
    name: "delete_object",
    description:
      "Delete a named object from the scene without generated Python. Use after inspecting scene state and confirming the exact object name.",
    category: "geometry",
    parameters: "name: string",
  },
  {
    name: "delete_objects",
    description:
      "Bulk delete multiple explicitly named objects in one bounded direct tool call. Use after get_all_object_info when clearing benchmark scenes or removing known object groups.",
    category: "geometry",
    parameters: "names: string[], ignore_missing?: boolean, max_delete?: number",
  },
  {
    name: "set_object_transform",
    description:
      "Set object location, rotation, or scale directly with structured parameters instead of Python snippets.",
    category: "geometry",
    parameters: "name: string, location?: number[3], rotation?: number[3] degrees, scale?: number[3]",
  },
  {
    name: "align_object_to_surface",
    description:
      "Align object world-space bounds to ground, a support top surface, or a support side face without generated Python.",
    category: "geometry",
    parameters:
      "name: string, placement?: GROUND|ON_TOP|SIDE_POSITIVE|SIDE_NEGATIVE, reference_name?: string, axis?: X|Y|Z, surface_value?: number, margin?: number",
  },
  {
    name: "validate_object_clearance",
    description:
      "Validate world-space AABB clearance or overlap between two objects after close placement or support-surface alignment.",
    category: "geometry",
    parameters: "name: string, other_name: string, margin?: number",
  },
  {
    name: "inspect_spatial_relations",
    description:
      "Inspect named spatial relations such as north/south/east/west, supported-by, inside/outside bounds, closer-than, and facing direction without generated Python.",
    category: "inspection",
    parameters:
      "relations: Array<{type, subject, reference?, other?, margin?, local_axis?, min_dot?}>, tolerance?: number",
  },
  {
    name: "inspect_mesh_intersections",
    description:
      "Inspect evaluated mesh-surface intersections for explicit object pairs using Blender BVH geometry. Use when bounds-only clearance cannot prove clothing, collision, or assembly penetration.",
    category: "inspection",
    parameters:
      "pairs: Array<{subject: string, reference: string}>, max_intersections?: number, epsilon?: number",
  },
  {
    name: "inspect_scene_grounding",
    description:
      "Inspect mesh object lower bounds against the ground plane and nearby support surfaces to find floating, unsupported, or below-ground objects before accepting a scene.",
    category: "inspection",
    parameters: "names?: string[], ground_z?: number, tolerance?: number, max_objects?: number, include_supports?: boolean",
  },
  {
    name: "align_object_attachment_points",
    description:
      "Translate an object so one of its local attachment points meets a local attachment point on a reference object without generated Python.",
    category: "geometry",
    parameters:
      "name: string, obj_local_point: number[3], reference_name: string, reference_local_point: number[3], offset?: number[3], preserve_rotation?: boolean",
  },
  {
    name: "rename_object",
    description:
      "Rename an object with a deterministic direct tool so later tool calls can reference stable names.",
    category: "geometry",
    parameters: "name: string, new_name: string",
  },
  {
    name: "duplicate_object",
    description:
      "Duplicate an existing object and optionally place it, preserving the source object as-is.",
    category: "geometry",
    parameters: "name: string, new_name?: string, linked?: boolean",
  },
  {
    name: "arrange_objects",
    description:
      "Arrange existing objects into centered line, circle, or grid patterns without generated Python loops.",
    category: "geometry",
    parameters:
      "names: string[], layout?: LINE|CIRCLE|GRID, center?: number[3], spacing?: number|number[], axis?: X|Y|Z, radius?: number, plane?: XY|XZ|YZ, columns?: number, row_spacing?: number, start_angle_degrees?: number, align_bottom_to_z?: number",
  },
  {
    name: "duplicate_object_pattern",
    description:
      "Duplicate one source object into a line, circle, or grid pattern without generated Python loops.",
    category: "geometry",
    parameters:
      "name: string, count: number, layout?: LINE|CIRCLE|GRID, name_prefix?: string, linked?: boolean, include_source?: boolean, center?: number[3], spacing?: number|number[], axis?: X|Y|Z, radius?: number, plane?: XY|XZ|YZ, columns?: number, row_spacing?: number, start_angle_degrees?: number, align_bottom_to_z?: number",
  },
  {
    name: "join_objects",
    description:
      "Join multiple mesh objects into one named object when the scene needs a single combined mesh.",
    category: "geometry",
    parameters: "names: string[], new_name?: string",
  },
  {
    name: "add_modifier",
    description:
      "Add a Blender modifier to an object using structured parameters before configuring or applying it.",
    category: "geometry",
    parameters: "name: string, modifier_type: string, modifier_name?: string",
  },
  {
    name: "soften_mesh_edges",
    description:
      "Batch-soften hard-surface mesh object families with bounded bevel modifiers, smooth shading, and optional weighted normals.",
    category: "geometry",
    parameters:
      "names: string[], width?: number, segments?: number, profile?: number, affect?: EDGES|VERTICES, harden_normals?: boolean, clamp_overlap?: boolean, shade_smooth?: boolean, add_weighted_normal?: boolean, apply_modifier?: boolean, modifier_name?: string, replace_existing?: boolean, skip_non_mesh?: boolean",
  },
  {
    name: "apply_modifier",
    description:
      "Apply a named modifier after stack inspection and validation.",
    category: "geometry",
    parameters: "name: string, modifier: string",
  },
  {
    name: "apply_transforms",
    description:
      "Apply object location, rotation, or scale transforms with explicit booleans.",
    category: "geometry",
    parameters: "name: string, location?: boolean, rotation?: boolean, scale?: boolean",
  },
  {
    name: "shade_smooth",
    description:
      "Set smooth or flat shading for mesh objects without Python.",
    category: "geometry",
    parameters: "name: string, smooth?: boolean",
  },
  {
    name: "parent_set",
    description:
      "Parent one or more child objects to a parent while preserving the intended scene hierarchy.",
    category: "geometry",
    parameters: "child_name: string, parent_name: string, parent_type?: OBJECT|ARMATURE|BONE",
  },
  {
    name: "parent_clear",
    description:
      "Clear object parenting with optional transform preservation.",
    category: "geometry",
    parameters: "name: string, keep_transform?: boolean",
  },
  {
    name: "set_origin",
    description:
      "Set object origin using a bounded direct tool instead of context-sensitive Python operators.",
    category: "geometry",
    parameters: "name: string, origin_type?: ORIGIN_GEOMETRY|ORIGIN_CURSOR|GEOMETRY_ORIGIN|ORIGIN_CENTER_OF_VOLUME, center?: MEDIAN|BOUNDS",
  },
  {
    name: "move_to_collection",
    description:
      "Move objects into an existing or newly created collection for deterministic scene organization.",
    category: "geometry",
    parameters: "name: string, collection_name: string, create_new?: boolean",
  },
  {
    name: "set_visibility",
    description:
      "Set viewport and/or render visibility for a named object.",
    category: "geometry",
    parameters: "name: string, hide_viewport?: boolean, hide_render?: boolean",
  },
  {
    name: "add_empty_object",
    description:
      "Create a Blender Empty root/control/locator object for parenting, grouping, transform handles, and assembly anchors without generated Python.",
    category: "geometry",
    parameters:
      "name?: string, location?: number[3], rotation?: number[3], scale?: number[3], display_type?: PLAIN_AXES|ARROWS|SINGLE_ARROW|CIRCLE|CUBE|SPHERE|CONE, display_size?: number, collection_name?: string, parent_name?: string, replace_existing?: boolean",
  },
  {
    name: "set_empty_properties",
    description:
      "Tune an existing Empty root/control display shape, display size, name visibility, and in-front visibility without generated Python.",
    category: "geometry",
    parameters:
      "name: string, display_type?: PLAIN_AXES|ARROWS|SINGLE_ARROW|CIRCLE|CUBE|SPHERE|CONE, display_size?: number, show_name?: boolean, show_in_front?: boolean",
  },
  {
    name: "add_text_object",
    description:
      "Create a bounded Blender text object for labels, signage, titles, annotations, or simple extruded lettering without generated Python.",
    category: "geometry",
    parameters:
      "text: string, name?: string, location?: number[3], rotation?: number[3], scale?: number[3], size?: number, align_x?: LEFT|CENTER|RIGHT|JUSTIFY|FLUSH, align_y?: TOP|TOP_BASELINE|CENTER|BOTTOM_BASELINE|BOTTOM, extrude?: number, bevel_depth?: number, bevel_resolution?: number, font_path?: string, material_name?: string, collection_name?: string, replace_existing?: boolean, convert_to_mesh?: boolean",
  },
  {
    name: "export_object",
    description:
      "Export named objects to GLB, GLTF, FBX, OBJ, or STL after export readiness validation.",
    category: "advanced",
    parameters: "names: string[], filepath: string, file_format?: GLB|GLTF|FBX|OBJ|STL",
  },
  {
    name: "export_asset_package",
    description:
      "Run UV preparation, optional transform apply, export readiness validation, export, and expected-file reporting in one safe package flow.",
    category: "advanced",
    parameters:
      "names: string[], filepath: string, file_format?: GLB|GLTF|FBX|OBJ|STL, uv_mode?: none|preserve_original|smart_project|lightmap_pack|pack_existing, apply_transforms?: boolean, required_uvs?: boolean, require_materials?: boolean, check_textures?: boolean, check_texture_formats?: boolean, make_dirs?: boolean, force_export?: boolean",
  },
  {
    name: "list_installed_addons",
    description:
      "List enabled Blender addons so the agent can adapt to available capabilities and avoid assuming unavailable integrations.",
    category: "inspection",
    parameters: "(no parameters)",
  },
  {
    name: "inspect_addon_capabilities",
    description:
      "Inspect registered Blender operator RNA for one enabled add-on without executing any operator. Returns typed inputs, current-context availability, provenance fingerprints, and inspection errors for personal capability onboarding.",
    category: "inspection",
    parameters:
      "addon_module: string, operator_ids?: string[], max_operators?: number (default 100, max 250)",
  },
  {
    name: "invoke_addon_capability",
    description:
      "Dry-run or invoke one inspected third-party add-on operator. Real invocation requires the exact current fingerprint, approved=true, and an absolute .blend checkpoint path; dry_run defaults to true.",
    category: "advanced",
    parameters:
      "addon_module: string, operator_id: string, arguments?: object, expected_source_fingerprint: string, dry_run?: boolean, approved?: boolean, checkpoint_filepath?: string",
  },
  {
    name: "create_material",
    description:
      "Create a basic Blender material with structured color and shader parameters when a full preset is unnecessary.",
    category: "materials",
    parameters: "name: string, color?: number[4], roughness?: number, metallic?: number",
  },
  {
    name: "assign_material",
    description:
      "Assign an existing material to an object by name without generated Python.",
    category: "materials",
    parameters: "object_name: string, material_name: string, slot_index?: number",
  },
  {
    name: "execute_code",
    description:
      "Fallback for scoped Blender Python only when no direct MCP tool fits, such as one-off custom geometry, procedural effects, animation internals, or short API introspection. Prefer direct tools for materials, lighting, cameras, transforms, UV/export, and validation.",
    category: "advanced",
    parameters: "code: string (scoped Blender Python script to execute)",
  },
  {
    name: "get_local_asset_library_status",
    description:
      "Check whether the local curated ViperMesh asset catalog is configured inside Blender and ready for search/import.",
    category: "assets",
    parameters: "(no parameters)",
  },
  {
    name: "search_local_assets",
    description:
      "Search the local curated asset catalog for reusable models such as furniture, props, foliage, or decor. Prefer a single asset type like 'basket' or 'desk lamp' when possible; broader scene queries can still return partial matches.",
    category: "assets",
    parameters: "query?: string, category?: string, tags?: string (comma-separated), style?: string, limit?: number (default 10)",
  },
  {
    name: "import_local_asset",
    description:
      "Append or link a curated asset and optionally place its complete hierarchy under one managed root. Prefer managed bottom-center placement over manual Empty creation and per-child parenting.",
    category: "assets",
    parameters: "asset_id: string, link?: boolean, create_root?: boolean, root_name?: string, location?: [x,y,z], rotation?: [degrees], scale?: number|[x,y,z], pivot?: 'BOTTOM_CENTER'|'CENTER'|'WORLD_ORIGIN', compact?: boolean",
  },
  {
    name: "get_polyhaven_status",
    description:
      "Check whether PolyHaven integration is configured inside Blender and ready for asset downloads.",
    category: "assets",
    parameters: "(no parameters)",
  },
  {
    name: "get_polyhaven_categories",
    description:
      "List available categories for a PolyHaven asset type. Call before search_polyhaven_assets to discover valid category filters.",
    category: "assets",
    parameters: "asset_type: string ('hdris'|'textures'|'models'|'all')",
  },
  {
    name: "search_polyhaven_assets",
    description:
      "Search the PolyHaven catalog for HDRIs, textures, or models using optional type and category filters.",
    category: "assets",
    parameters: "asset_type?: string ('hdris'|'textures'|'models'|'all'), categories?: string (comma-separated category names)",
  },
  {
    name: "download_polyhaven_asset",
    description:
      "Download a PolyHaven asset by ID and import it into the Blender scene. Requires the status check to have succeeded.",
    category: "assets",
    parameters: "asset_id: string, asset_type: string ('hdris'|'textures'|'models'), resolution?: string (default '1k'), file_format?: string",
  },
  {
    name: "set_texture",
    description:
      "Apply a previously downloaded PolyHaven texture to a mesh object, creating material slots when needed.",
    category: "materials",
    parameters: "object_name: string, texture_id: string",
  },
  {
    name: "create_material_preset",
    description:
      "Create or update a deterministic Blender 5.x Principled BSDF material preset, optionally assign it, and wire PBR map roles with correct color spaces.",
    category: "materials",
    parameters:
      "name: string, preset?: dielectric|plastic|rubber|fabric|ceramic|metal|glass|emissive, object_name?: string, base_color?: number[], metallic?: number, roughness?: number, alpha?: number, emission_color?: number[], emission_strength?: number, transmission_weight?: number, ior?: number, texture_maps?: object, replace_existing?: boolean, slot_index?: number",
  },
  {
    name: "create_pbr_material_from_textures",
    description:
      "Infer common PBR texture roles from a texture directory or explicit image paths, then create/update and optionally assign a Principled BSDF material.",
    category: "materials",
    parameters:
      "name: string, texture_directory?: string, texture_paths?: string[], object_name?: string, preset?: dielectric|plastic|rubber|fabric|ceramic|metal|glass|emissive, recursive?: boolean, max_files?: number, replace_existing?: boolean, slot_index?: number",
  },
  {
    name: "inspect_material_node_graph",
    description:
      "Inspect a material node graph, including Principled socket values, image texture color spaces, links, and assigned objects.",
    category: "materials",
    parameters: "material_name: string",
  },
  {
    name: "normalize_material_texture_channels",
    description:
      "Inspect and optionally fix imported material image texture color spaces by inferred PBR channel. Defaults to report-only mode; apply_changes=true performs deterministic corrections.",
    category: "materials",
    parameters: "material_names?: string[], apply_changes?: boolean",
  },
  {
    name: "prepare_uv_layout",
    description:
      "Preserve original UVs or run deterministic UV prep before texturing/export. Use preserve_original for imported assets and smart_project for generated meshes without UVs.",
    category: "advanced",
    parameters:
      "names: string[], mode?: preserve_original|smart_project|lightmap_pack|pack_existing, uv_map_name?: string, angle_limit?: number, island_margin?: number, rotate?: boolean, scale?: boolean",
  },
  {
    name: "validate_export_readiness",
    description:
      "Validate mesh UV completeness, materials, texture paths/formats, transforms, mesh health, expected output files, and format-specific risks before calling export_object.",
    category: "advanced",
    parameters:
      "names: string[], filepath?: string, file_format?: GLB|GLTF|FBX|OBJ|STL, required_uvs?: boolean, require_materials?: boolean, require_applied_transforms?: boolean, check_textures?: boolean, check_texture_formats?: boolean, require_absolute_path?: boolean",
  },
  {
    name: "inspect_export_cleanup_candidates",
    description:
      "Inspect helper, reference, hidden, and construction objects before export while protecting objects referenced by modifiers, constraints, or parents. Can report, hide, move, or explicitly delete candidates.",
    category: "advanced",
    parameters:
      "names?: string[], action?: report|hide|move_to_collection|delete, helper_patterns?: string[], target_collection?: string, include_hidden?: boolean",
  },
  {
    name: "inspect_export_texture_dependencies",
    description:
      "Inspect selected meshes' image texture dependencies before export, including resolved paths, missing files, empty filepaths, packed images, and risky portable-export formats.",
    category: "advanced",
    parameters:
      "names: string[], file_format?: GLB|GLTF|FBX|OBJ|STL, max_dependencies?: number, check_texture_formats?: boolean",
  },
  {
    name: "validate_gltf_roundtrip",
    description:
      "Temporarily import a GLB or glTF export, inventory meshes, armature bones, skinned meshes, materials, images, actions, and triangle count, then clean up the imported data by default.",
    category: "advanced",
    parameters: "filepath: string, cleanup?: boolean",
  },
  {
    name: "set_world_environment",
    description:
      "Configure world/background environment lighting without generated Python: solid color, HDRI path with rotation, or procedural sky.",
    category: "lighting",
    parameters:
      "mode?: solid|hdri|sky, color?: number[3], strength?: number, hdri_path?: string, rotation_z?: number, sky_type?: string, sun_elevation?: number, sun_rotation?: number",
  },
  {
    name: "setup_studio_scene",
    description:
      "Create a deterministic studio/product lighting rig, frame a camera around target meshes, and apply render defaults for model previews.",
    category: "lighting",
    parameters:
      "target_names?: string[], preset?: studio|product|indoor|exterior|night, camera_name?: string, frame_camera?: boolean, focal_length?: number, distance_multiplier?: number, resolution_x?: number, resolution_y?: number, samples?: number, background_color?: number[], world_strength?: number, set_active_camera?: boolean",
  },
  {
    name: "validate_studio_scene",
    description:
      "Validate target meshes, active/requested camera, target framing, render-visible lights, and render settings before render_image.",
    category: "lighting",
    parameters:
      "target_names?: string[], camera_name?: string, require_camera?: boolean, require_lights?: boolean, require_render_settings?: boolean, min_frame_fill?: number, max_frame_fill?: number, frame_margin?: number",
  },
  {
    name: "frame_camera_to_targets",
    description:
      "Reframe an active or named camera around target meshes by moving along the target-view ray until projected bounds reach the desired frame fill.",
    category: "lighting",
    parameters:
      "target_names?: string[], camera_name?: string, desired_frame_fill?: number, frame_margin?: number, min_distance_multiplier?: number, max_distance_multiplier?: number, set_active?: boolean, set_dof_focus?: boolean",
  },
  {
    name: "create_camera_orbit_animation",
    description:
      "Create a deterministic camera orbit animation around target bounds while leaving the model still. Use for product showcase previews and camera-spin loops before validating framing.",
    category: "advanced",
    parameters:
      "target_names?: string[], camera_name?: string, start_frame?: number, end_frame?: number, radius_multiplier?: number, height_multiplier?: number, start_angle_degrees?: number, end_angle_degrees?: number, focal_length?: number, interpolation?: string, clear_existing?: boolean, set_active?: boolean, set_scene_range?: boolean",
  },
  {
    name: "render_thumbnail_to_path",
    description:
      "Render a lightweight studio thumbnail preview to a path for asset previews and visual validation artifacts, separate from final render_image output.",
    category: "lighting",
    parameters:
      "output_path?: string, target_names?: string[], preset?: studio|product|indoor|exterior|night, camera_name?: string, resolution?: number, samples?: number, file_format?: string, frame_camera?: boolean, distance_multiplier?: number, focal_length?: number",
  },
  {
    name: "inspect_render_artifact",
    description:
      "Inspect a saved render, thumbnail, or viewport image artifact for dimensions, brightness, alpha coverage, and edge/corner background signals before accepting the output.",
    category: "lighting",
    parameters:
      "image_path: string, min_brightness?: number, max_brightness?: number, min_alpha_coverage?: number, edge_sample_percent?: number, corner_sample_percent?: number, background_tolerance?: number, max_sample_pixels?: number",
  },
  {
    name: "render_image",
    description:
      "Render the current scene to an image file using current render settings, optionally overriding output path or file format.",
    category: "lighting",
    parameters:
      "output_path?: string, file_format?: PNG|JPEG|OPEN_EXR|TIFF",
  },
  {
    name: "add_light",
    description:
      "Add a new POINT, SUN, SPOT, or AREA light with optional location, energy, and RGB color. Prefer this over execute_code for simple scene lighting.",
    category: "lighting",
    parameters:
      "light_type?: POINT|SUN|SPOT|AREA, name?: string, location?: number[3], energy?: number, color?: number[3]",
  },
  {
    name: "set_light_properties",
    description:
      "Modify an existing light's energy, color, softness, spot cone, spot blend, or area size without generated Python.",
    category: "lighting",
    parameters:
      "name: string, energy?: number, color?: number[3], shadow_soft_size?: number, spot_size?: number, spot_blend?: number, size?: number",
  },
  {
    name: "add_camera",
    description:
      "Add a new camera with optional location, rotation in degrees, lens, and sensor width. Use for explicit camera creation before rendering.",
    category: "lighting",
    parameters:
      "name?: string, location?: number[3], rotation?: number[3] degrees, lens?: number, sensor_width?: number",
  },
  {
    name: "set_camera_properties",
    description:
      "Modify an existing camera's lens, sensor width, clipping, depth of field, and active-scene-camera state. Make the camera active with set_active=true before render_image.",
    category: "lighting",
    parameters:
      "name: string, lens?: number, sensor_width?: number, clip_start?: number, clip_end?: number, dof_use?: boolean, dof_focus_distance?: number, dof_aperture_fstop?: number, set_active?: boolean",
  },
  {
    name: "aim_camera_at",
    description:
      "Aim an existing camera at an object or world-space point, optionally setting it active and updating depth-of-field focus distance.",
    category: "lighting",
    parameters:
      "name: string, target_name?: string, target_location?: number[3] (at least one of target_name or target_location required), set_active?: boolean, set_dof_focus?: boolean",
  },
  {
    name: "set_render_settings",
    description:
      "Configure render engine, resolution, samples, denoising, transparency, output path, and file format before preview or final renders. Prefer BLENDER_EEVEE or EEVEE for EEVEE previews; BLENDER_EEVEE_NEXT is only a compatibility alias and may not exist in current Blender.",
    category: "lighting",
    parameters:
      "engine?: EEVEE|BLENDER_EEVEE|CYCLES|BLENDER_WORKBENCH (BLENDER_EEVEE_NEXT is only a compatibility alias), resolution_x?: number, resolution_y?: number, resolution_percentage?: number, samples?: number, use_denoising?: boolean, film_transparent?: boolean, output_path?: string, file_format?: PNG|JPEG|OPEN_EXR|TIFF",
  },
  {
    name: "add_mesh_primitive",
    description:
      "Create a bounded common mesh primitive such as cube, sphere, cylinder, cone, plane, or torus without generated Python.",
    category: "geometry",
    parameters:
      "primitive_type: cube|uv_sphere|sphere|cylinder|cone|plane|torus, name?: string, location?: number[3], rotation?: number[3], scale?: number[3], size?: number, radius?: number, radius1?: number, radius2?: number, depth?: number, vertices?: number, segments?: number, ring_count?: number, major_radius?: number, minor_radius?: number, major_segments?: number, minor_segments?: number, collection_name?: string, material_name?: string, replace_existing?: boolean, shade_smooth?: boolean, validate?: boolean",
  },
  {
    name: "create_primitive_assembly",
    description:
      "Create a grouped primitive assembly from local-coordinate part specs, optionally parented to a root Empty. Use for brackets, furniture, fixtures, and hard-surface object families before execute_code.",
    category: "geometry",
    parameters:
      "name?: string, parts: Array<{primitive_type, name?, local_location?, local_rotation?, scale?, material_name?}>, location?: number[3], rotation?: number[3], collection_name?: string, create_root_empty?: boolean, root_display_type?: string, root_display_size?: number, replace_existing?: boolean, validate?: boolean",
  },
  {
    name: "create_parametric_staircase",
    description:
      "Create a bounded hard-surface staircase mesh with configurable step count, width, tread depth, and rise height without generated Python.",
    category: "geometry",
    parameters:
      "name?: string, step_count?: number, step_width?: number, step_depth?: number, step_height?: number, location?: number[3], rotation?: number[3] degrees, collection_name?: string, material_name?: string, replace_existing?: boolean, shade_smooth?: boolean, validate?: boolean",
  },
  {
    name: "create_room_shell",
    description:
      "Create a bounded architectural room shell with real-thickness floor, walls, and optional ceiling without generated Python.",
    category: "geometry",
    parameters:
      "name?: string, width?: number, depth?: number, height?: number, wall_thickness?: number, floor_thickness?: number, location?: number[3], collection_name?: string, wall_material_name?: string, floor_material_name?: string, ceiling_material_name?: string, include_ceiling?: boolean, open_front?: boolean, replace_existing?: boolean, validate?: boolean",
  },
  {
    name: "create_wall_opening",
    description:
      "Cut a bounded window/door opening in an existing wall with a Boolean cutter and optionally add glass/door fill and frame components.",
    category: "geometry",
    parameters:
      "wall_name: string, name?: string, opening_type?: window|door|empty, center?: number[3], opening_width?: number, opening_height?: number, cut_depth?: number, wall_axis?: auto|x|y, fill_type?: none|glass|door, panel_thickness?: number, create_frame?: boolean, frame_width?: number, frame_depth?: number, collection_name?: string, fill_material_name?: string, frame_material_name?: string, replace_existing?: boolean, validate?: boolean",
  },
  {
    name: "add_curve_object",
    description:
      "Create a bounded curve/path object such as a Bezier curve, polyline, circle, or spiral without generated Python. Use for cables, vines, rails, arcs, decorative paths, and bevelled tube-like strokes.",
    category: "geometry",
    parameters:
      "curve_type?: bezier|polyline|circle|spiral, name?: string, points?: number[3][], cyclic?: boolean, resolution?: number, radius?: number, turns?: number, height?: number, start_radius?: number, end_radius?: number, points_per_turn?: number, location?: number[3], rotation?: number[3], scale?: number[3], bevel_depth?: number, bevel_resolution?: number, fill_mode?: FULL|FRONT|BACK|HALF, material_name?: string, collection_name?: string, replace_existing?: boolean, convert_to_mesh?: boolean",
  },
  {
    name: "set_curve_properties",
    description:
      "Tune an existing curve object's resolution, bevel thickness, fill mode, cyclic/open path state, and material assignment without generated Python.",
    category: "geometry",
    parameters:
      "name: string, resolution?: number, bevel_depth?: number, bevel_resolution?: number, fill_mode?: FULL|FRONT|BACK|HALF, cyclic?: boolean, material_name?: string",
  },
  {
    name: "create_mesh_from_data",
    description:
      "Create a mesh object from explicit vertices, optional edges, and faces using Blender's Data API. Prefer this over execute_code when the mesh topology is already structured.",
    category: "geometry",
    parameters:
      "name: string, vertices: number[][], faces: number[][], edges?: number[][], collection_name?: string, material_name?: string, location?: number[], replace_existing?: boolean, validate?: boolean, shade_smooth?: boolean",
  },
  {
    name: "create_draped_surface_mesh",
    description:
      "Create a bounded sagging or wavy grid surface mesh for tarps, cloth panels, flags, canopies, awnings, terrain patches, and irregular panels without generated Python.",
    category: "geometry",
    parameters:
      "name?: string, width?: number, depth?: number, subdivisions_x?: number, subdivisions_y?: number, sag?: number, wave_amplitude?: number, wave_frequency_x?: number, wave_frequency_y?: number, edge_lift?: number, height?: number, location?: number[3], rotation?: number[3] degrees, collection_name?: string, material_name?: string, replace_existing?: boolean, validate?: boolean, shade_smooth?: boolean",
  },
  {
    name: "validate_mesh_geometry",
    description:
      "Validate mesh geometry for invalid data, zero-area faces, boundary/non-manifold edges, and loose edges. Optional cleanup runs mesh.validate() on real mesh data.",
    category: "geometry",
    parameters:
      "names: string[], cleanup?: boolean, require_closed?: boolean",
  },
  {
    name: "repair_mesh_geometry",
    description:
      "Repair common mesh issues by merging duplicate vertices, removing loose vertices/edges, and recalculating normals. Defaults to source-preserving COPY mode; use REPLACE only for explicit destructive repair.",
    category: "geometry",
    parameters:
      "name: string, result_name?: string, mode?: COPY|REPLACE, preserve_source?: boolean, merge_by_distance?: boolean, merge_distance?: number, remove_loose?: boolean, recalculate_normals?: boolean, shade_smooth?: boolean",
  },
  {
    name: "inspect_retopology_readiness",
    description:
      "Inspect mesh topology density, triangle/quad/ngon composition, non-manifold risk, UV/material readiness, and decimation candidates before retopology or remesh decisions.",
    category: "inspection",
    parameters:
      "names?: string[], max_objects?: number, high_density_face_threshold?: number",
  },
  {
    name: "compare_mesh_surfaces",
    description:
      "Compare source and candidate evaluated meshes using bounded bidirectional vertex and polygon-center surface deviation, nearest material-region correspondence, and coverage-aware UV seam position correspondence. Read-only and intended for topology or LOD evidence before artist acceptance.",
    category: "inspection",
    parameters:
      "source_name: string, candidate_name: string, distance_tolerance?: number, seam_tolerance?: number, max_surface_samples?: number, max_attribute_samples?: number",
  },
  {
    name: "decimate_mesh",
    description:
      "Create a lower-density mesh with Blender's Decimate modifier. Defaults to source-preserving COPY mode; use REPLACE only for explicit destructive decimation.",
    category: "geometry",
    parameters:
      "name: string, result_name?: string, mode?: COPY|REPLACE, preserve_source?: boolean, ratio?: number, target_face_count?: number, decimate_type?: COLLAPSE|UNSUBDIV|DISSOLVE, iterations?: number, angle_limit?: number, apply_modifier?: boolean",
  },
  {
    name: "voxel_remesh_mesh",
    description:
      "Create a unified voxel-remeshed mesh with Blender's voxel remesh operator. Defaults to source-preserving COPY mode; use REPLACE only for explicit destructive remesh.",
    category: "geometry",
    parameters:
      "name: string, result_name?: string, mode?: COPY|REPLACE, preserve_source?: boolean, voxel_size?: number, adaptivity?: number, preserve_attributes?: boolean, preserve_volume?: boolean, fix_poles?: boolean",
  },
  {
    name: "quadriflow_remesh_mesh",
    description:
      "Create quad-dominant retopology with Blender's QuadriFlow operator. Defaults to source-preserving COPY mode; use REPLACE only for explicit destructive remesh.",
    category: "geometry",
    parameters:
      "name: string, result_name?: string, mode?: COPY|REPLACE, preserve_source?: boolean, target_faces?: number, use_mesh_symmetry?: boolean, preserve_sharp?: boolean, preserve_boundary?: boolean, preserve_attributes?: boolean, smooth_normals?: boolean, seed?: number",
  },
  {
    name: "inspect_modifier_constraint_stack",
    description:
      "Inspect modifier and constraint stack order, common settings, missing targets, disabled flags, and high-risk SubSurf viewport levels before changing stacks.",
    category: "inspection",
    parameters:
      "names?: string[], include_empty?: boolean",
  },
  {
    name: "inspect_rigging_data",
    description:
      "Inspect armatures, bones, pose bones, vertex groups, Armature modifiers, and missing rigging targets before rigging or weight changes.",
    category: "inspection",
    parameters:
      "names?: string[], include_vertex_groups?: boolean, max_bones?: number, max_objects?: number",
  },
  {
    name: "inspect_edit_bone_alignment",
    description:
      "Inspect named armature edit-bone alignment, including head, tail, roll, length, parent/child links, and Rigify type.",
    category: "inspection",
    parameters:
      "armature_name: string, bone_names?: string[], max_bones?: number",
  },
  {
    name: "set_edit_bone_alignment",
    description:
      "Set explicit armature edit-bone head, tail, roll, connection, and deform flags for bounded metarig alignment.",
    category: "geometry",
    parameters:
      "armature_name: string, bones: {name: string, head?: number[3], tail?: number[3], roll?: number, use_connect?: boolean, use_deform?: boolean}[], allow_generated_target?: boolean",
  },
  {
    name: "inspect_weight_paint_readiness",
    description:
      "Inspect mesh vertex groups, sampled weights, unweighted vertices, over-influenced vertices, and armature/deform-bone alignment before weight painting or skinning edits.",
    category: "inspection",
    parameters:
      "names?: string[], max_objects?: number, max_vertices_sample?: number, max_influences?: number, weight_sum_tolerance?: number",
  },
  {
    name: "inspect_pose_deformation",
    description:
      "Non-mutating stress pose inspection for evaluated rigged meshes. Reports sampled displacement, invalid coordinates, topology changes, and symmetric stretch/compression outliers while restoring the artist's current frame and subframe.",
    category: "inspection",
    parameters:
      "names?: string[] (max 20), baseline_frame?: number, stress_frames?: number[] (max 24), max_objects?: number, max_vertices_sample?: number, max_edges_sample?: number, edge_ratio_threshold?: number, displacement_epsilon?: number",
  },
  {
    name: "normalize_vertex_group_weights",
    description:
      "Normalize and prune mesh vertex group weights with max influence, prune threshold, locked-group preservation, and deform-bone group filtering.",
    category: "geometry",
    parameters:
      "names: string[], max_influences?: number, prune_threshold?: number, preserve_locked?: boolean, only_deform_bone_groups?: boolean, max_vertices?: number",
  },
  {
    name: "create_rigify_metarig",
    description:
      "Create a bundled Rigify metarig template for deliberate per-bone alignment before final rig generation.",
    category: "geometry",
    parameters:
      "template?: human|basic_human|basic_quadruped|bird|cat|horse|shark|wolf, name?: string, location?: number[3], rotation?: number[3] degrees, scale?: positive number[3], collection_name?: string, replace_existing?: boolean",
  },
  {
    name: "generate_rigify_rig",
    description:
      "Generate or explicitly regenerate a Rigify control rig from an already aligned Rigify metarig.",
    category: "geometry",
    parameters:
      "metarig_name: string, rig_name?: string, hide_metarig?: boolean, regenerate_existing?: boolean",
  },
  {
    name: "bind_mesh_to_armature",
    description:
      "Bind one mesh to one armature using automatic weights, bone envelopes, empty groups, or existing name-matched groups.",
    category: "geometry",
    parameters:
      "mesh_name: string, armature_name: string, binding_mode?: AUTOMATIC|ENVELOPE|EMPTY|NAME, replace_existing?: boolean, keep_transform?: boolean",
  },
  {
    name: "transfer_vertex_group_weights",
    description:
      "Transfer vertex-group weights between same-topology meshes by vertex index, optionally restricted to deform-bone groups.",
    category: "geometry",
    parameters:
      "source_name: string, target_name: string, group_names?: string[], armature_name?: string, only_deform_bone_groups?: boolean, replace_existing?: boolean, max_vertices?: number",
  },
  {
    name: "project_vertex_group_weights",
    description:
      "Project vertex-group weights from a source mesh to a different-topology target using Blender's Data Transfer modifier.",
    category: "geometry",
    parameters:
      "source_name: string, target_name: string, group_names?: string[], armature_name?: string, only_deform_bone_groups?: boolean, replace_existing?: boolean, mapping?: NEAREST|EDGE_NEAREST|EDGEINTERP_NEAREST|POLY_NEAREST|POLYINTERP_NEAREST|POLYINTERP_VNORPROJ, use_max_distance?: boolean, max_distance?: number, mix_mode?: REPLACE|ABOVE_THRESHOLD|BELOW_THRESHOLD|MIX|ADD|SUB|MUL, mix_factor?: number",
  },
  {
    name: "configure_modifier",
    description:
      "Configure modifier viewport/render/edit/cage flags or move a modifier to a stack index without applying/baking it.",
    category: "geometry",
    parameters:
      "name: string, modifier: string, show_viewport?: boolean, show_render?: boolean, show_in_editmode?: boolean, show_on_cage?: boolean, move_to_index?: number",
  },
  {
    name: "get_geometry_nodes_inputs",
    description:
      "List a Geometry Nodes modifier's inputs: name, identifier, type, panel, current value (datablocks by name), menu items, attribute bindings; include_defaults adds default/min/max.",
    category: "geometry",
    parameters: "name: string, modifier?: string (required when the object has several Geometry Nodes modifiers), include_defaults?: boolean, panel?: string (panel path prefix filter)",
  },
  {
    name: "set_geometry_nodes_inputs",
    description:
      "Assign a geometry node group to a Geometry Nodes modifier and/or set its inputs by socket name or identifier. Menu inputs take item names; Object/Collection/Material/Image inputs take datablock names. Reports per-input errors.",
    category: "geometry",
    parameters: "name: string, values?: object (socket name|identifier -> value), modifier?: string, node_group?: string",
  },
  {
    name: "inspect_node_group",
    description:
      "Summarize a node group (geometry, shader or compositor): interface sockets with defaults, node type counts, nested groups, users; optionally nodes with unlinked input values and links, filtered by node_filter and capped by max_nodes.",
    category: "inspection",
    parameters: "node_group_name: string, include_nodes?: boolean, include_links?: boolean, max_nodes?: number, node_filter?: string",
  },
  {
    name: "configure_constraint",
    description:
      "Configure constraint influence or mute state without changing targets, parenting, or object transforms.",
    category: "geometry",
    parameters:
      "name: string, constraint: string, influence?: number (0-1), mute?: boolean",
  },
  {
    name: "add_object_constraint",
    description:
      "Add an object constraint such as TRACK_TO, COPY_LOCATION, COPY_ROTATION, LIMIT_LOCATION, or LIMIT_ROTATION without freeform Python.",
    category: "geometry",
    parameters:
      "name: string, constraint_type: string, constraint_name?: string, target_name?: string, subtarget?: string, influence?: number (0-1), properties?: object",
  },
  {
    name: "remove_object_constraint",
    description:
      "Remove an object constraint by name after stack inspection.",
    category: "geometry",
    parameters:
      "name: string, constraint: string",
  },
  {
    name: "inspect_animation_data",
    description:
      "Inspect timeline settings, actions, Blender 5 slotted-action F-curves, legacy F-curves, keyframe samples, drivers, and NLA tracks before creating or editing animation.",
    category: "inspection",
    parameters:
      "names?: string[], include_materials?: boolean, include_actions?: boolean, max_keyframes_per_curve?: number, max_objects?: number, max_materials?: number, max_actions?: number",
  },
  {
    name: "retarget_animation_clip",
    description:
      "Import a BVH or FBX motion clip, retarget an explicit source-to-target bone map through temporary constraints, bake a new target action, clean imported data, and export explicit objects as a GLB candidate with rollback on failure.",
    category: "advanced",
    parameters:
      "filepath: string, target_armature: string, bone_map: Record<string,string>, action_name: string, export_names: string[], output_filepath: string (.glb), source_armature?: string, root_motion?: IN_PLACE|PRESERVE, root_source_bone?: string, frame_start?: number, frame_end?: number, bake_step?: number, cleanup_imported?: boolean, overwrite?: boolean",
  },
  {
    name: "inspect_shape_keys",
    description:
      "Inspect existing mesh shape keys, values, slider ranges, drivers, and animation action state before editing morph, viseme, blend-shape, or expression values.",
    category: "inspection",
    parameters:
      "names?: string[], max_objects?: number, max_shape_keys_per_object?: number",
  },
  {
    name: "extract_shape_key_to_object",
    description:
      "Extract an existing non-Basis shape key into an editable same-topology target mesh object. Use before target-object morph edits, then write it back with create_shape_key_from_object.",
    category: "geometry",
    parameters:
      "name: string, shape_key_name: string, result_name?: string, value?: number, collection_name?: string, copy_materials?: boolean, replace_existing?: boolean",
  },
  {
    name: "create_shape_key_from_object",
    description:
      "Create or replace a mesh shape key by copying vertex coordinates from a same-topology target mesh object. Use for morph target geometry when a duplicate/edit target already exists.",
    category: "geometry",
    parameters:
      "name: string, target_name: string, shape_key_name: string, value?: number, replace_existing?: boolean, slider_min?: number, slider_max?: number",
  },
  {
    name: "set_shape_key_properties",
    description:
      "Set non-geometric shape key properties such as slider min/max and mute state without freeform Python.",
    category: "geometry",
    parameters:
      "name: string, shape_key_name: string, slider_min?: number, slider_max?: number, mute?: boolean, clamp_value?: boolean",
  },
  {
    name: "rename_shape_key",
    description:
      "Rename an existing non-Basis mesh shape key without freeform Python.",
    category: "geometry",
    parameters:
      "name: string, shape_key_name: string, new_shape_key_name: string, replace_existing?: boolean",
  },
  {
    name: "delete_shape_key",
    description:
      "Delete an existing non-Basis mesh shape key without freeform Python.",
    category: "geometry",
    parameters:
      "name: string, shape_key_name: string",
  },
  {
    name: "duplicate_shape_key",
    description:
      "Duplicate an existing non-Basis mesh shape key without freeform Python.",
    category: "geometry",
    parameters:
      "name: string, shape_key_name: string, new_shape_key_name: string, value?: number, replace_existing?: boolean, copy_properties?: boolean",
  },
  {
    name: "create_shape_key_from_mix",
    description:
      "Create a non-Basis mesh shape key from the current or explicit mix of existing shape-key values without freeform Python.",
    category: "geometry",
    parameters:
      "name: string, new_shape_key_name: string, mix_values?: Record<string, number>, value?: number, replace_existing?: boolean, slider_min?: number, slider_max?: number, restore_values?: boolean",
  },
  {
    name: "set_shape_key_value",
    description:
      "Set or keyframe an existing mesh shape key value without freeform Python. Use for morph targets, visemes, blend shapes, and facial expression sliders.",
    category: "advanced",
    parameters:
      "name: string, shape_key_name: string, value: number, frame?: number, keyframes?: {frame: number, value: number}[], interpolation?: string, clear_existing?: boolean, set_scene_range?: boolean",
  },
  {
    name: "set_timeline_settings",
    description:
      "Set bounded scene timeline settings such as frame range, current frame, FPS, preview range, and playback sync before animation or render workflows.",
    category: "advanced",
    parameters:
      "frame_start?: number, frame_end?: number, current_frame?: number, fps?: number, fps_base?: number, use_preview_range?: boolean, preview_start?: number, preview_end?: number, playback_sync?: NONE|FRAME_DROP|AUDIO_SYNC",
  },
  {
    name: "set_keyframe_animation",
    description:
      "Create bounded transform keyframes for an object's location, rotation_euler, or scale without freeform Python. Use after animation inspection for common moves, bounces, reveals, turntables, and scale animations.",
    category: "advanced",
    parameters:
      "name: string, data_path?: location|rotation_euler|scale, keyframes: {frame: number, value: number[3]}[], interpolation?: string, easing?: string, rotation_unit?: radians|degrees, clear_existing?: boolean, set_scene_range?: boolean",
  },
  {
    name: "create_turntable_animation",
    description:
      "Create a deterministic product/model turntable by rotating explicit target objects with bounded rotation_euler keyframes. Use for product spins and model showcase previews before verifying with animation inspection.",
    category: "advanced",
    parameters:
      "target_names: string[], start_frame?: number, end_frame?: number, axis?: X|Y|Z, rotations?: number, interpolation?: string, clear_existing?: boolean, set_scene_range?: boolean",
  },
  {
    name: "inspect_collection_hierarchy",
    description:
      "Inspect collection hierarchy, object collection membership, parent-child relationships, and visibility flags before moving objects, parenting, unparenting, or reorganizing the outliner.",
    category: "inspection",
    parameters:
      "names?: string[], max_collections?: number, max_objects?: number, include_hidden?: boolean",
  },
  {
    name: "organize_collection_hierarchy",
    description:
      "Batch create/reuse a collection, move objects, parent or unparent while preserving world transforms, and set object/collection visibility.",
    category: "geometry",
    parameters:
      "collection_name?: string, object_names?: string[], create_collection?: boolean, move_objects?: boolean, parent_name?: string, clear_parent?: boolean, hide_viewport?: boolean, hide_render?: boolean, collection_hide_viewport?: boolean, collection_hide_render?: boolean",
  },
  {
    name: "get_sketchfab_status",
    description:
      "Verify Sketchfab integration and credentials before searching the catalog.",
    category: "assets",
    parameters: "(no parameters)",
  },
  {
    name: "search_sketchfab_models",
    description:
      "Search Sketchfab for models that match user-provided keywords.",
    category: "assets",
    parameters: "query: string, categories?: string, count?: number (default 20), downloadable?: boolean (default true)",
  },
  {
    name: "download_sketchfab_model",
    description:
      "Download and import a Sketchfab model. Ensure usage rights are respected.",
    category: "assets",
    parameters: "uid: string",
  },
]

export function getToolMetadata(name: string): ToolMetadata | undefined {
  return TOOL_REGISTRY.find((tool) => tool.name === name)
}

export function toolsByCategory(category: ToolCategory): ToolMetadata[] {
  return TOOL_REGISTRY.filter((tool) => tool.category === category)
}
