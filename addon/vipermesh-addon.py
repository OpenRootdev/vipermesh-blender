# ViperMesh for Blender Addon
# Based on BlenderMCP by Siddharth Ahuja (www.github.com/ahujasid)
# Modified for ViperMesh - AI-Powered Blender Assistant

import bpy
import mathutils
import json
import threading
import queue
import socket
import time
import requests
import tempfile
import traceback
import os
import math
import shutil
import zipfile
import itertools
import hashlib
import inspect
import marshal
import uuid
from array import array
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty
import io
from contextlib import redirect_stdout, suppress

ADDON_VERSION = (1, 3, 0)
ADDON_VERSION_LABEL = ".".join(str(part) for part in ADDON_VERSION)
MAX_POSE_DEFORMATION_WORK = 2_000_000
MAX_MESH_SURFACE_COMPARISON_FACES = 500_000
MAX_MESH_SURFACE_COMPARISON_VERTICES = 1_000_000

bl_info = {
    "name": "ViperMesh for Blender",
    "author": "ViperMesh Team",
    "version": (1, 3, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > ViperMesh",
    "description": "Persistent local Blender bridge for ViperMesh and MCP-compatible agents",
    "category": "Interface",
    "doc_url": "https://github.com/OpenRootdev/vipermesh-blender",
}

# Add User-Agent as required by Poly Haven API
REQ_HEADERS = requests.utils.default_headers()
REQ_HEADERS.update({"User-Agent": "vipermesh-blender"})

VALID_VIEWPORT_SHADING_TYPES = {"WIREFRAME", "SOLID", "MATERIAL", "RENDERED"}

class BlenderMCPServer:
    def __init__(self, host='127.0.0.1', port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.server_thread = None
        self.clients = set()
        self.clients_lock = threading.Lock()
        self.last_error = ""
        self.background = bool(bpy.app.background)
        self.pending = queue.Queue(maxsize=128)
        self.last_activity = time.monotonic()
        self._timer_callback = self._drain_gui_commands

    @property
    def active_clients(self):
        with self.clients_lock:
            return len(self.clients)

    def start(self):
        if self.running:
            print("Server is already running")
            return

        try:
            self.last_error = ""
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)

            # Only set running after socket is successfully bound
            self.running = True
            self.last_activity = time.monotonic()
            if not self.background:
                bpy.app.timers.register(self._timer_callback, first_interval=0, persistent=True)

            # Start server thread
            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()

            print(f"BlenderMCP server started on {self.host}:{self.port}")
        except Exception as e:
            self.last_error = str(e)
            print(f"Failed to start server: {self.last_error}")
            self.stop()

    def stop(self):
        self.running = False
        if threading.current_thread() is threading.main_thread():
            if bpy.app.timers.is_registered(self._timer_callback):
                bpy.app.timers.unregister(self._timer_callback)
        while True:
            try:
                item = self.pending.get_nowait()
            except queue.Empty:
                break
            item["response"] = {"status": "error", "code": "BRIDGE_STOPPED", "message": "Bridge stopped before dispatch"}
            item["done"].set()

        with self.clients_lock:
            clients = list(self.clients)
        for client in clients:
            try:
                client.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                client.close()
            except:
                pass

        # Close socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        # Wait for thread to finish
        if self.server_thread:
            try:
                if self.server_thread.is_alive():
                    self.server_thread.join(timeout=1.0)
            except:
                pass
            self.server_thread = None

        print("BlenderMCP server stopped")

    def _server_loop(self):
        """Main server loop in a separate thread"""
        print("Server thread started")
        self.socket.settimeout(1.0)  # Timeout to allow for stopping

        while self.running:
            try:
                # Accept new connection
                try:
                    client, address = self.socket.accept()
                    with self.clients_lock:
                        self.clients.add(client)
                    print(f"Connected to client: {address}")

                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    # Just check running condition
                    continue
                except Exception as e:
                    if self.running:
                        self.last_error = str(e)
                        print(f"Error accepting connection: {self.last_error}")
                    time.sleep(0.5)
            except Exception as e:
                print(f"Error in server loop: {str(e)}")
                if not self.running:
                    break
                time.sleep(0.5)

        print("Server thread stopped")

    def _drain_commands(self):
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("Blender commands must execute on the main thread")
        started = time.monotonic()
        for _ in range(8):
            if not self.running:
                break
            try:
                item = self.pending.get_nowait()
            except queue.Empty:
                break
            try:
                response = self.execute_command(item["command"])
                if "id" in item["command"]:
                    response["id"] = item["command"]["id"]
                item["response"] = response
            except Exception as exc:
                item["response"] = {"status": "error", "message": str(exc)}
            finally:
                self.last_activity = time.monotonic()
                item["done"].set()
            if time.monotonic() - started >= 0.01:
                break

    def _drain_gui_commands(self):
        if not self.running:
            return None
        self._drain_commands()
        return 0.01

    def serve_headless(self, idle_timeout=0, max_runtime=0):
        """Own the main thread explicitly; background Blender has no GUI event loop."""
        if not self.background or threading.current_thread() is not threading.main_thread():
            raise RuntimeError("serve_headless requires background Blender's main thread")
        started = time.monotonic()
        try:
            while self.running:
                self._drain_commands()
                now = time.monotonic()
                if idle_timeout and now - self.last_activity >= idle_timeout:
                    break
                if max_runtime and now - started >= max_runtime:
                    break
                time.sleep(0.005)
        finally:
            self.stop()

    def _handle_client(self, client):
        """Handle connected client"""
        print("Client handler started")
        client.settimeout(1.0)
        buffer = b''
        MAX_BUFFER_BYTES = 10 * 1024 * 1024  # 10 MB safety limit

        try:
            while self.running:
                # Receive data
                try:
                    try:
                        data = client.recv(8192)
                    except socket.timeout:
                        continue
                    if not data:
                        print("Client disconnected")
                        break

                    buffer += data
                    if len(buffer) > MAX_BUFFER_BYTES:
                        client.sendall(json.dumps({"status": "error", "code": "REQUEST_TOO_LARGE", "message": "Request exceeds 10 MiB"}).encode())
                        print(f"Buffer exceeded {MAX_BUFFER_BYTES} bytes, dropping connection")
                        break
                    try:
                        text = buffer.decode('utf-8')
                    except UnicodeDecodeError as exc:
                        if exc.reason == 'unexpected end of data':
                            continue
                        client.sendall(json.dumps({"status": "error", "code": "INVALID_ENCODING", "message": "Request must be UTF-8 JSON"}).encode())
                        break
                    try:
                        text = text.lstrip()
                        if not text:
                            buffer = b''
                            continue
                        def reject_constant(value):
                            raise ValueError(f"Non-JSON numeric constant: {value}")
                        command, consumed = json.JSONDecoder(parse_constant=reject_constant).raw_decode(text)
                        if text[consumed:].strip():
                            client.sendall(json.dumps({"status": "error", "code": "PIPELINING_NOT_SUPPORTED", "message": "Send one complete request and await its response"}).encode())
                            break
                        buffer = b''
                        if (not isinstance(command, dict) or not isinstance(command.get("type"), str)
                                or not isinstance(command.get("params", {}), dict)
                                or ("id" in command and (isinstance(command["id"], bool) or not isinstance(command["id"], (str, int))))):
                            client.sendall(json.dumps({"status": "error", "code": "INVALID_REQUEST", "message": "Expected type:string, params:object and optional string/integer id"}).encode())
                            continue
                        item = {"command": command, "done": threading.Event()}
                        try:
                            self.pending.put_nowait(item)
                        except queue.Full:
                            client.sendall(json.dumps({"status": "error", "code": "BRIDGE_BUSY", "message": "Command queue is full"}).encode())
                            continue
                        self.last_activity = time.monotonic()
                        while self.running and not item["done"].wait(0.1):
                            pass
                        if not item["done"].is_set():
                            break
                        # Socket I/O stays off the Blender main thread.
                        client.sendall(json.dumps(item["response"]).encode('utf-8'))
                    except json.JSONDecodeError:
                        if text and text[0] not in '{["-0123456789tfn':
                            client.sendall(json.dumps({"status": "error", "code": "INVALID_JSON", "message": "Invalid JSON document"}).encode())
                            break
                        continue
                    except ValueError as exc:
                        client.sendall(json.dumps({"status": "error", "code": "INVALID_JSON", "message": str(exc)}).encode())
                        break
                except Exception as e:
                    print(f"Error receiving data: {str(e)}")
                    break
        except Exception as e:
            print(f"Error in client handler: {str(e)}")
        finally:
            try:
                client.close()
            except:
                pass
            with self.clients_lock:
                self.clients.discard(client)
            print("Client handler stopped")

    def execute_command(self, command):
        """Execute a command in the main Blender thread"""
        try:
            return self._execute_command_internal(command)

        except Exception as e:
            print(f"Error executing command: {str(e)}")
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def _execute_command_internal(self, command):
        """Internal command execution with proper context"""
        cmd_type = command.get("type")
        params = command.get("params", {})
        if bpy.app.background and cmd_type in {
            "get_viewport_screenshot", "render_viewport_to_path", "inspect_viewport_areas",
            "set_viewport_shading", "focus_viewport_on_objects",
        }:
            return {"status": "error", "code": "UI_CONTEXT_REQUIRED", "message": f"{cmd_type} requires a GUI viewport; use a camera render in background mode"}

        # Base handlers that are always available
        handlers = {
            "get_scene_info": self.get_scene_info,
            "get_object_info": self.get_object_info,
            "get_all_object_info": self.get_all_object_info,
            "inspect_blend_file_health": self.inspect_blend_file_health,
            "get_blendfile_summary_path_info": self.get_blendfile_summary_path_info,
            "get_blendfile_summary_datablocks": self.get_blendfile_summary_datablocks,
            "get_blendfile_summary_missing_files": self.get_blendfile_summary_missing_files,
            "get_blendfile_summary_of_linked_libraries": self.get_blendfile_summary_of_linked_libraries,
            "get_blendfile_summary_usage_guess": self.get_blendfile_summary_usage_guess,
            "get_viewport_screenshot": self.get_viewport_screenshot,
            "render_viewport_to_path": self.render_viewport_to_path,
            "inspect_viewport_areas": self.inspect_viewport_areas,
            "set_viewport_shading": self.set_viewport_shading,
            "focus_viewport_on_objects": self.focus_viewport_on_objects,
            "select_scene_objects": self.select_scene_objects,
            "set_active_collection": self.set_active_collection,
            "execute_code": self.execute_code,
            "save_blend_file": self.save_blend_file,
            "restore_blend_checkpoint": self.restore_blend_checkpoint,
            "list_materials": self.list_materials,
            "delete_object": self.delete_object,
            "delete_objects": self.delete_objects,
            "set_object_transform": self.set_object_transform,
            "align_object_to_surface": self.align_object_to_surface,
            "validate_object_clearance": self.validate_object_clearance,
            "inspect_spatial_relations": self.inspect_spatial_relations,
            "inspect_mesh_intersections": self.inspect_mesh_intersections,
            "inspect_scene_grounding": self.inspect_scene_grounding,
            "align_object_attachment_points": self.align_object_attachment_points,
            "rename_object": self.rename_object,
            "duplicate_object": self.duplicate_object,
            "arrange_objects": self.arrange_objects,
            "duplicate_object_pattern": self.duplicate_object_pattern,
            "join_objects": self.join_objects,
            "add_empty_object": self.add_empty_object,
            "set_empty_properties": self.set_empty_properties,
            "add_text_object": self.add_text_object,
            "add_mesh_primitive": self.add_mesh_primitive,
            "create_primitive_assembly": self.create_primitive_assembly,
            "create_parametric_staircase": self.create_parametric_staircase,
            "create_room_shell": self.create_room_shell,
            "create_wall_opening": self.create_wall_opening,
            "add_curve_object": self.add_curve_object,
            "set_curve_properties": self.set_curve_properties,
            "create_mesh_from_data": self.create_mesh_from_data,
            "create_draped_surface_mesh": self.create_draped_surface_mesh,
            "validate_mesh_geometry": self.validate_mesh_geometry,
            "repair_mesh_geometry": self.repair_mesh_geometry,
            "inspect_retopology_readiness": self.inspect_retopology_readiness,
            "compare_mesh_surfaces": self.compare_mesh_surfaces,
            "decimate_mesh": self.decimate_mesh,
            "voxel_remesh_mesh": self.voxel_remesh_mesh,
            "quadriflow_remesh_mesh": self.quadriflow_remesh_mesh,
            "inspect_modifier_constraint_stack": self.inspect_modifier_constraint_stack,
            "inspect_rigging_data": self.inspect_rigging_data,
            "inspect_edit_bone_alignment": self.inspect_edit_bone_alignment,
            "set_edit_bone_alignment": self.set_edit_bone_alignment,
            "inspect_weight_paint_readiness": self.inspect_weight_paint_readiness,
            "inspect_pose_deformation": self.inspect_pose_deformation,
            "normalize_vertex_group_weights": self.normalize_vertex_group_weights,
            "create_rigify_metarig": self.create_rigify_metarig,
            "generate_rigify_rig": self.generate_rigify_rig,
            "bind_mesh_to_armature": self.bind_mesh_to_armature,
            "transfer_vertex_group_weights": self.transfer_vertex_group_weights,
            "project_vertex_group_weights": self.project_vertex_group_weights,
            "inspect_animation_data": self.inspect_animation_data,
            "retarget_animation_clip": self.retarget_animation_clip,
            "inspect_shape_keys": self.inspect_shape_keys,
            "extract_shape_key_to_object": self.extract_shape_key_to_object,
            "create_shape_key_from_object": self.create_shape_key_from_object,
            "set_shape_key_properties": self.set_shape_key_properties,
            "rename_shape_key": self.rename_shape_key,
            "delete_shape_key": self.delete_shape_key,
            "duplicate_shape_key": self.duplicate_shape_key,
            "create_shape_key_from_mix": self.create_shape_key_from_mix,
            "set_shape_key_value": self.set_shape_key_value,
            "set_timeline_settings": self.set_timeline_settings,
            "set_keyframe_animation": self.set_keyframe_animation,
            "create_turntable_animation": self.create_turntable_animation,
            "add_modifier": self.add_modifier,
            "soften_mesh_edges": self.soften_mesh_edges,
            "configure_modifier": self.configure_modifier,
            "add_object_constraint": self.add_object_constraint,
            "remove_object_constraint": self.remove_object_constraint,
            "configure_constraint": self.configure_constraint,
            "apply_modifier": self.apply_modifier,
            "apply_transforms": self.apply_transforms,
            "shade_smooth": self.shade_smooth,
            "parent_set": self.parent_set,
            "parent_clear": self.parent_clear,
            "set_origin": self.set_origin,
            "inspect_collection_hierarchy": self.inspect_collection_hierarchy,
            "organize_collection_hierarchy": self.organize_collection_hierarchy,
            "move_to_collection": self.move_to_collection,
            "set_visibility": self.set_visibility,
            "inspect_export_cleanup_candidates": self.inspect_export_cleanup_candidates,
            "prepare_uv_layout": self.prepare_uv_layout,
            "validate_export_readiness": self.validate_export_readiness,
            "inspect_export_texture_dependencies": self.inspect_export_texture_dependencies,
            "export_asset_package": self.export_asset_package,
            "validate_gltf_roundtrip": self.validate_gltf_roundtrip,
            "get_vipermesh_runtime_identity": self.get_vipermesh_runtime_identity,
            "export_object": self.export_object,
            "list_installed_addons": self.list_installed_addons,
            "inspect_addon_capabilities": self.inspect_addon_capabilities,
            "invoke_addon_capability": self.invoke_addon_capability,
            "create_material": self.create_material,
            "assign_material": self.assign_material,
            "create_material_preset": self.create_material_preset,
            "create_pbr_material_from_textures": self.create_pbr_material_from_textures,
            "inspect_material_node_graph": self.inspect_material_node_graph,
            "normalize_material_texture_channels": self.normalize_material_texture_channels,
            "set_world_environment": self.set_world_environment,
            "setup_studio_scene": self.setup_studio_scene,
            "validate_studio_scene": self.validate_studio_scene,
            "frame_camera_to_targets": self.frame_camera_to_targets,
            "create_camera_orbit_animation": self.create_camera_orbit_animation,
            "render_thumbnail_to_path": self.render_thumbnail_to_path,
            "inspect_render_artifact": self.inspect_render_artifact,
            "add_light": self.add_light,
            "set_light_properties": self.set_light_properties,
            "add_camera": self.add_camera,
            "set_camera_properties": self.set_camera_properties,
            "aim_camera_at": self.aim_camera_at,
            "set_render_settings": self.set_render_settings,
            "render_image": self.render_image,
            "get_local_asset_library_status": self.get_local_asset_library_status,
            "get_polyhaven_status": self.get_polyhaven_status,
            "get_sketchfab_status": self.get_sketchfab_status,
        }

        # Add local asset library handlers only if enabled
        if bpy.context.scene.blendermcp_use_local_assets:
            local_asset_handlers = {
                "search_local_assets": self.search_local_assets,
                "import_local_asset": self.import_local_asset,
            }
            handlers.update(local_asset_handlers)

        # Add Polyhaven handlers only if enabled
        if bpy.context.scene.blendermcp_use_polyhaven:
            polyhaven_handlers = {
                "get_polyhaven_categories": self.get_polyhaven_categories,
                "search_polyhaven_assets": self.search_polyhaven_assets,
                "download_polyhaven_asset": self.download_polyhaven_asset,
                "set_texture": self.set_texture,
            }
            handlers.update(polyhaven_handlers)

        # Add Sketchfab handlers only if enabled
        if bpy.context.scene.blendermcp_use_sketchfab:
            sketchfab_handlers = {
                "search_sketchfab_models": self.search_sketchfab_models,
                "download_sketchfab_model": self.download_sketchfab_model,
            }
            handlers.update(sketchfab_handlers)

        handler = handlers.get(cmd_type)
        if handler:
            try:
                print(f"Executing handler for {cmd_type}")
                result = handler(**params)
                print(f"Handler execution complete")
                return {"status": "success", "result": result}
            except Exception as e:
                print(f"Error in handler: {str(e)}")
                traceback.print_exc()
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": f"Unknown command type: {cmd_type}"}



    def get_scene_info(self):
        """Get information about the current Blender scene"""
        try:
            print("Getting scene info...")
            # Simplify the scene info to reduce data size
            scene_info = {
                "name": bpy.context.scene.name,
                "object_count": len(bpy.context.scene.objects),
                "objects": [],
                "materials_count": len(bpy.data.materials),
            }

            # Collect minimal object information (limit to first 10 objects)
            for i, obj in enumerate(bpy.context.scene.objects):
                if i >= 10:  # Reduced from 20 to 10
                    break

                obj_info = {
                    "name": obj.name,
                    "type": obj.type,
                    # Only include basic location data
                    "location": [round(float(obj.location.x), 2),
                                round(float(obj.location.y), 2),
                                round(float(obj.location.z), 2)],
                }
                scene_info["objects"].append(obj_info)

            print(f"Scene info collected: {len(scene_info['objects'])} objects")
            return scene_info
        except Exception as e:
            print(f"Error in get_scene_info: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}

    @staticmethod
    def _get_aabb(obj):
        """ Returns the world-space axis-aligned bounding box (AABB) of an object. """
        if obj.type != 'MESH':
            raise TypeError("Object must be a mesh")

        # Get the bounding box corners in local space
        local_bbox_corners = [mathutils.Vector(corner) for corner in obj.bound_box]

        # Convert to world coordinates
        world_bbox_corners = [obj.matrix_world @ corner for corner in local_bbox_corners]

        # Compute axis-aligned min/max coordinates
        min_corner = mathutils.Vector(map(min, zip(*world_bbox_corners)))
        max_corner = mathutils.Vector(map(max, zip(*world_bbox_corners)))

        return [
            [*min_corner], [*max_corner]
        ]



    def get_object_info(self, name):
        """Get detailed information about a specific object"""
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object not found: {name}")

        # Basic object info
        obj_info = {
            "name": obj.name,
            "type": obj.type,
            "location": [obj.location.x, obj.location.y, obj.location.z],
            "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
            "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            "visible": obj.visible_get(),
            "materials": [],
        }

        if obj.type == "MESH":
            bounding_box = self._get_aabb(obj)
            obj_info["world_bounding_box"] = bounding_box

        # Add material slots
        for slot in obj.material_slots:
            if slot.material:
                obj_info["materials"].append(slot.material.name)

        # Add mesh data if applicable
        if obj.type == 'MESH' and obj.data:
            mesh = obj.data
            obj_info["mesh"] = {
                "vertices": len(mesh.vertices),
                "edges": len(mesh.edges),
                "polygons": len(mesh.polygons),
            }

        return obj_info

    def get_all_object_info(self, max_objects=50, start_index=0):
        """Get detailed information about all objects in the scene.
        Returns a list of object details including type, transforms, materials,
        mesh stats, and modifiers for every object.
        Supports pagination via max_objects and start_index."""
        try:
            print("Getting all object info...")
            all_scene_objects = list(bpy.context.scene.objects)
            total_count = len(all_scene_objects)
            subset = all_scene_objects[start_index:start_index + max_objects]
            all_objects = []

            for obj in subset:
                obj_info = {
                    "name": obj.name,
                    "type": obj.type,
                    "location": [round(float(obj.location.x), 3),
                                 round(float(obj.location.y), 3),
                                 round(float(obj.location.z), 3)],
                    "rotation": [round(float(obj.rotation_euler.x), 3),
                                 round(float(obj.rotation_euler.y), 3),
                                 round(float(obj.rotation_euler.z), 3)],
                    "scale": [round(float(obj.scale.x), 3),
                              round(float(obj.scale.y), 3),
                              round(float(obj.scale.z), 3)],
                    "visible": obj.visible_get(),
                    "materials": [],
                    "modifiers": [],
                }

                # Bounding box for mesh objects
                if obj.type == "MESH":
                    try:
                        bounding_box = self._get_aabb(obj)
                        obj_info["world_bounding_box"] = bounding_box
                    except Exception:
                        pass

                # Material slots
                for slot in obj.material_slots:
                    if slot.material:
                        obj_info["materials"].append(slot.material.name)

                # Mesh stats
                if obj.type == 'MESH' and obj.data:
                    mesh = obj.data
                    obj_info["mesh"] = {
                        "vertices": len(mesh.vertices),
                        "edges": len(mesh.edges),
                        "polygons": len(mesh.polygons),
                    }

                # Modifiers
                for mod in obj.modifiers:
                    obj_info["modifiers"].append({
                        "name": mod.name,
                        "type": mod.type,
                    })

                # Light-specific data
                if obj.type == 'LIGHT' and obj.data:
                    light = obj.data
                    obj_info["light"] = {
                        "type": light.type,
                        "energy": round(float(light.energy), 2),
                        "color": [round(float(light.color.r), 3),
                                  round(float(light.color.g), 3),
                                  round(float(light.color.b), 3)],
                    }

                # Camera-specific data
                if obj.type == 'CAMERA' and obj.data:
                    cam = obj.data
                    obj_info["camera"] = {
                        "type": cam.type,
                        "lens": round(float(cam.lens), 2),
                        "clip_start": round(float(cam.clip_start), 3),
                        "clip_end": round(float(cam.clip_end), 2),
                    }

                all_objects.append(obj_info)

            print(f"Collected info for {len(all_objects)} objects (of {total_count} total)")
            return {
                "object_count": len(all_objects),
                "total_in_scene": total_count,
                "start_index": start_index,
                "has_more": start_index + max_objects < total_count,
                "objects": all_objects,
            }
        except Exception as e:
            print(f"Error in get_all_object_info: {str(e)}")
            traceback.print_exc()
            raise

    def inspect_blend_file_health(self, max_external_files=80, include_object_samples=True):
        """Inspect .blend file health without mutating the scene.

        Returns structured counts, missing external files, linked libraries,
        packed asset counts, and high-signal scene organization warnings.
        """
        try:
            def parse_positive_int(value, default_value):
                try:
                    parsed = int(value)
                except (TypeError, ValueError):
                    parsed = default_value
                return max(1, parsed)

            def parse_bool(value):
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() in {"true", "1", "yes", "y"}
                return bool(value)

            max_external_files = parse_positive_int(max_external_files, 80)
            include_object_samples = parse_bool(include_object_samples)

            filepath = bpy.data.filepath or ""
            external_files = []
            missing_external_files = []
            packed_files = []

            def normalize_path(raw_path, library=None):
                if not raw_path:
                    return ""
                try:
                    return bpy.path.abspath(raw_path, library=library)
                except Exception:
                    return raw_path

            def record_external_file(kind, name, raw_path, packed=False, library=None):
                resolved_path = normalize_path(raw_path, library=library)
                exists = bool(resolved_path and os.path.exists(resolved_path))
                entry = {
                    "type": kind,
                    "name": name,
                    "filepath": raw_path or "",
                    "resolved_path": resolved_path,
                    "exists": exists,
                    "packed": bool(packed),
                }
                if packed:
                    packed_files.append(entry)
                else:
                    external_files.append(entry)
                    if not exists:
                        missing_external_files.append(entry)

            for image in bpy.data.images:
                if getattr(image, "source", "") == "FILE":
                    filepath_attr = getattr(image, "filepath", "")
                    if filepath_attr:
                        record_external_file("image", image.name, filepath_attr, bool(getattr(image, "packed_file", None)), getattr(image, "library", None))

            for library in bpy.data.libraries:
                filepath_attr = getattr(library, "filepath", "")
                if filepath_attr:
                    record_external_file("library", library.name, filepath_attr, False, getattr(library, "library", None))

            for font in bpy.data.fonts:
                filepath_attr = getattr(font, "filepath", "")
                if filepath_attr:
                    record_external_file("font", font.name, filepath_attr, False, getattr(font, "library", None))

            for movie_clip in bpy.data.movieclips:
                filepath_attr = getattr(movie_clip, "filepath", "")
                if filepath_attr:
                    record_external_file("movie_clip", movie_clip.name, filepath_attr, False, getattr(movie_clip, "library", None))

            for sound in bpy.data.sounds:
                filepath_attr = getattr(sound, "filepath", "")
                if filepath_attr:
                    record_external_file("sound", sound.name, filepath_attr, False, getattr(sound, "library", None))

            object_type_counts = {}
            hidden_viewport_count = 0
            hidden_render_count = 0
            modifier_count = 0
            constraint_count = 0
            parented_object_count = 0
            object_samples = []

            for obj in bpy.data.objects:
                object_type_counts[obj.type] = object_type_counts.get(obj.type, 0) + 1
                if obj.hide_viewport:
                    hidden_viewport_count += 1
                if obj.hide_render:
                    hidden_render_count += 1
                modifier_count += len(getattr(obj, "modifiers", []))
                constraint_count += len(getattr(obj, "constraints", []))
                if obj.parent:
                    parented_object_count += 1
                if include_object_samples and len(object_samples) < 20:
                    object_samples.append({
                        "name": obj.name,
                        "type": obj.type,
                        "visible": obj.visible_get(),
                        "hide_viewport": bool(obj.hide_viewport),
                        "hide_render": bool(obj.hide_render),
                        "modifiers": len(getattr(obj, "modifiers", [])),
                        "constraints": len(getattr(obj, "constraints", [])),
                        "parent": obj.parent.name if obj.parent else None,
                    })

            orphan_counts = {
                "meshes": sum(1 for item in bpy.data.meshes if item.users == 0),
                "materials": sum(1 for item in bpy.data.materials if item.users == 0),
                "images": sum(1 for item in bpy.data.images if item.users == 0),
                "actions": sum(1 for item in bpy.data.actions if item.users == 0),
            }

            issues = []
            if not filepath:
                issues.append({
                    "severity": "warn",
                    "code": "unsaved_blend_file",
                    "message": "The current Blender file has not been saved yet.",
                })
            if missing_external_files:
                issues.append({
                    "severity": "error",
                    "code": "missing_external_files",
                    "message": f"{len(missing_external_files)} external file(s) are missing.",
                })
            if len(bpy.data.objects) > 500:
                issues.append({
                    "severity": "warn",
                    "code": "large_scene",
                    "message": "Scene has more than 500 objects; use pagination or collection-focused inspection.",
                })
            if any(count > 0 for count in orphan_counts.values()):
                issues.append({
                    "severity": "info",
                    "code": "orphaned_datablocks",
                    "message": "Unused datablocks are present; purge only after confirming they are not needed.",
                })

            health_status = "healthy"
            if any(issue["severity"] == "error" for issue in issues):
                health_status = "error"
            elif any(issue["severity"] == "warn" for issue in issues):
                health_status = "warning"

            return {
                "status": health_status,
                "scene_evidence": {
                    key: bpy.context.scene.get(key)
                    for key in (
                        "vipermesh_fixture_id",
                        "vipermesh_fixture_source",
                        "vipermesh_fixture_license",
                        "vipermesh_asset_glb_sha256",
                        "vipermesh_candidate_glb_sha256",
                    )
                    if bpy.context.scene.get(key) is not None
                },
                "file": {
                    "filepath": filepath,
                    "directory": os.path.dirname(filepath) if filepath else "",
                    "saved": bool(filepath),
                    "dirty": bool(getattr(bpy.data, "is_dirty", False)),
                },
                "counts": {
                    "objects": len(bpy.data.objects),
                    "collections": len(bpy.data.collections),
                    "meshes": len(bpy.data.meshes),
                    "materials": len(bpy.data.materials),
                    "images": len(bpy.data.images),
                    "libraries": len(bpy.data.libraries),
                    "actions": len(bpy.data.actions),
                    "cameras": len(bpy.data.cameras),
                    "lights": len(bpy.data.lights),
                    "modifiers": modifier_count,
                    "constraints": constraint_count,
                    "parented_objects": parented_object_count,
                    "hidden_viewport_objects": hidden_viewport_count,
                    "hidden_render_objects": hidden_render_count,
                },
                "object_type_counts": object_type_counts,
                "external_files": external_files[:max_external_files],
                "missing_external_files": missing_external_files[:max_external_files],
                "missing_external_file_count": len(missing_external_files),
                "linked_libraries": [
                    {
                        "name": library.name,
                        "filepath": getattr(library, "filepath", ""),
                        "resolved_path": normalize_path(getattr(library, "filepath", ""), getattr(library, "library", None)),
                        "exists": os.path.exists(normalize_path(getattr(library, "filepath", ""), getattr(library, "library", None))),
                    }
                    for library in bpy.data.libraries
                ],
                "packed_file_count": len(packed_files),
                "orphan_counts": orphan_counts,
                "object_samples": object_samples,
                "issues": issues,
            }
        except Exception as e:
            print(f"Error in inspect_blend_file_health: {str(e)}")
            traceback.print_exc()
            raise

    def get_blendfile_summary_path_info(self):
        """Return saved path, directory, dirty state, and basic file-path diagnostics."""
        health = self.inspect_blend_file_health(max_external_files=1, include_object_samples=False)
        file_info = health.get("file", {})
        return {
            "status": health.get("status"),
            "file": file_info,
            "saved": bool(file_info.get("saved")),
            "dirty": bool(file_info.get("dirty")),
            "filepath": file_info.get("filepath", ""),
            "directory": file_info.get("directory", ""),
            "issues": [
                issue for issue in health.get("issues", [])
                if issue.get("code") in {"unsaved_blend_file"}
            ],
            "next_safe_action": "Use missing-file or linked-library summaries before relinking assets.",
        }

    def get_blendfile_summary_datablocks(self, include_object_samples=True):
        """Return high-level Blender datablock counts and orphan counts."""
        health = self.inspect_blend_file_health(max_external_files=1, include_object_samples=include_object_samples)
        return {
            "status": health.get("status"),
            "counts": health.get("counts", {}),
            "object_type_counts": health.get("object_type_counts", {}),
            "orphan_counts": health.get("orphan_counts", {}),
            "object_samples": health.get("object_samples", []) if include_object_samples else [],
            "issues": [
                issue for issue in health.get("issues", [])
                if issue.get("code") in {"large_scene", "orphaned_datablocks"}
            ],
            "next_safe_action": "Inspect specific object, collection, modifier, or rigging data before mutating the scene.",
        }

    def get_blendfile_summary_missing_files(self, max_files=80):
        """Return external-file and missing-file summaries without changing the scene."""
        health = self.inspect_blend_file_health(max_external_files=max_files, include_object_samples=False)
        return {
            "status": health.get("status"),
            "external_file_count": len(health.get("external_files", [])),
            "missing_external_file_count": health.get("missing_external_file_count", 0),
            "missing_external_files": health.get("missing_external_files", []),
            "packed_file_count": health.get("packed_file_count", 0),
            "issues": [
                issue for issue in health.get("issues", [])
                if issue.get("code") in {"missing_external_files"}
            ],
            "next_safe_action": "Ask for a packaged/relinked asset before rebuilding materials when files are missing.",
        }

    def get_blendfile_summary_of_linked_libraries(self, max_libraries=80):
        """Return linked library paths and missing linked-library diagnostics."""
        health = self.inspect_blend_file_health(max_external_files=1, include_object_samples=False)
        try:
            max_libraries = max(1, int(max_libraries))
        except (TypeError, ValueError):
            max_libraries = 80
        linked_libraries = health.get("linked_libraries", [])
        missing_libraries = [library for library in linked_libraries if not library.get("exists")]
        return {
            "status": "error" if missing_libraries else health.get("status"),
            "linked_library_count": len(linked_libraries),
            "missing_linked_library_count": len(missing_libraries),
            "linked_libraries": linked_libraries[:max_libraries],
            "missing_linked_libraries": missing_libraries[:max_libraries],
            "next_safe_action": "Do not purge linked data automatically; ask the user to relink or package missing libraries.",
        }

    def get_blendfile_summary_usage_guess(self):
        """Return a conservative usage guess from scene/file summary signals."""
        health = self.inspect_blend_file_health(max_external_files=8, include_object_samples=False)
        counts = health.get("counts", {})
        object_types = health.get("object_type_counts", {})
        signals = []
        usage_guess = "general_blender_scene"

        if counts.get("actions", 0) > 0:
            usage_guess = "animated_scene_or_rig"
            signals.append("actions_present")
        if object_types.get("ARMATURE", 0) > 0:
            usage_guess = "rigged_character_or_deformable_asset"
            signals.append("armatures_present")
        if counts.get("libraries", 0) > 0:
            signals.append("linked_libraries_present")
        if counts.get("images", 0) > 0 or counts.get("materials", 0) > 0:
            signals.append("materials_or_images_present")
        if counts.get("cameras", 0) > 0 and counts.get("lights", 0) > 0:
            signals.append("render_setup_present")
        if health.get("missing_external_file_count", 0) > 0:
            signals.append("missing_external_files")
        if counts.get("objects", 0) > 500:
            signals.append("large_scene")

        if usage_guess == "general_blender_scene" and "render_setup_present" in signals:
            usage_guess = "render_ready_scene"
        if usage_guess == "general_blender_scene" and "materials_or_images_present" in signals:
            usage_guess = "textured_asset_or_scene"

        return {
            "status": health.get("status"),
            "usage_guess": usage_guess,
            "signals": signals,
            "counts": counts,
            "object_type_counts": object_types,
            "missing_external_file_count": health.get("missing_external_file_count", 0),
            "next_safe_action": "Use the specific summary or inspection tool matching the strongest signal before editing.",
        }

    def _view3d_areas(self):
        screen = getattr(bpy.context, "screen", None)
        if not screen:
            return []
        return [area for area in screen.areas if area.type == 'VIEW_3D']

    def _view3d_area_context(self, area_index=None):
        areas = self._view3d_areas()
        if not areas:
            return None, None, None, "No 3D viewport found"
        try:
            index = 0 if area_index is None else int(area_index)
        except Exception:
            return None, None, None, "area_index must be an integer"
        if index < 0 or index >= len(areas):
            return None, None, None, f"3D viewport area_index {index} out of range; available areas: {len(areas)}"

        area = areas[index]
        region = next((region for region in area.regions if region.type == 'WINDOW'), None)
        space = area.spaces.active
        if region is None:
            return None, None, None, f"3D viewport area_index {index} has no window region"
        return area, region, space, None

    def set_viewport_shading(self, shading_type="MATERIAL", area_index=None, all_areas=False, show_overlays=None, show_xray=None):
        """Set 3D viewport shading without raw execute_code snippets."""
        try:
            target_type = str(shading_type or "MATERIAL").strip().upper()
            if target_type not in VALID_VIEWPORT_SHADING_TYPES:
                return {
                    "error": f"Invalid viewport shading type: {shading_type}",
                    "valid_types": sorted(VALID_VIEWPORT_SHADING_TYPES),
                }

            areas = self._view3d_areas()
            if not areas:
                return {"error": "No 3D viewport found"}

            if bool(all_areas):
                indexed_areas = list(enumerate(areas))
            else:
                try:
                    index = 0 if area_index is None else int(area_index)
                except Exception:
                    return {"error": "area_index must be an integer"}
                if index < 0 or index >= len(areas):
                    return {"error": f"3D viewport area_index {index} out of range; available areas: {len(areas)}"}
                indexed_areas = [(index, areas[index])]

            applied = []
            for index, area in indexed_areas:
                space = area.spaces.active
                shading = getattr(space, "shading", None)
                overlay = getattr(space, "overlay", None)
                previous = {
                    "shading_type": str(getattr(shading, "type", "")) if shading else None,
                    "show_xray": bool(getattr(shading, "show_xray", False)) if shading and hasattr(shading, "show_xray") else None,
                    "show_overlays": bool(getattr(overlay, "show_overlays", False)) if overlay and hasattr(overlay, "show_overlays") else None,
                }
                if shading is not None:
                    shading.type = target_type
                    if show_xray is not None and hasattr(shading, "show_xray"):
                        shading.show_xray = bool(show_xray)
                if show_overlays is not None and overlay is not None and hasattr(overlay, "show_overlays"):
                    overlay.show_overlays = bool(show_overlays)

                applied.append({
                    "area_index": index,
                    "previous": previous,
                    "current": {
                        "shading_type": str(getattr(shading, "type", "")) if shading else None,
                        "show_xray": bool(getattr(shading, "show_xray", False)) if shading and hasattr(shading, "show_xray") else None,
                        "show_overlays": bool(getattr(overlay, "show_overlays", False)) if overlay and hasattr(overlay, "show_overlays") else None,
                    },
                })

            return {
                "success": True,
                "applied_count": len(applied),
                "areas": applied,
                "next_safe_action": "capture get_viewport_screenshot with the same area_index to verify viewport appearance",
            }
        except Exception as e:
            return {"error": f"Failed to set viewport shading: {str(e)}"}

    def inspect_viewport_areas(self):
        """Inspect available 3D viewport areas and their current region state."""
        try:
            areas = self._view3d_areas()
            reports = []
            for index, area in enumerate(areas):
                region = next((region for region in area.regions if region.type == 'WINDOW'), None)
                space = area.spaces.active
                region_3d = getattr(space, "region_3d", None)
                report = {
                    "area_index": index,
                    "type": area.type,
                    "x": int(area.x),
                    "y": int(area.y),
                    "width": int(area.width),
                    "height": int(area.height),
                    "window_region": {
                        "width": int(region.width) if region else None,
                        "height": int(region.height) if region else None,
                    },
                    "space_type": getattr(space, "type", None),
                    "lens": float(getattr(space, "lens", 0.0)),
                    "clip_start": float(getattr(space, "clip_start", 0.0)),
                    "clip_end": float(getattr(space, "clip_end", 0.0)),
                }
                if region_3d is not None:
                    report["region_3d"] = {
                        "view_perspective": str(getattr(region_3d, "view_perspective", "")),
                        "view_location": list(getattr(region_3d, "view_location", [])),
                        "view_distance": float(getattr(region_3d, "view_distance", 0.0)),
                        "view_rotation": list(getattr(region_3d, "view_rotation", [])),
                        "is_perspective": bool(getattr(region_3d, "is_perspective", False)),
                    }
                reports.append(report)

            return {
                "success": len(reports) > 0,
                "area_count": len(reports),
                "areas": reports,
                "active_camera": bpy.context.scene.camera.name if bpy.context.scene.camera else None,
                "next_safe_action": "use area_index with focus_viewport_on_objects and get_viewport_screenshot for area-specific visual checks",
            }
        except Exception as e:
            return {"error": f"Failed to inspect viewport areas: {str(e)}"}

    def focus_viewport_on_objects(self, names=None, area_index=None):
        """Focus a 3D viewport area on named or currently selected objects without changing scene data."""
        try:
            area, region, space, error = self._view3d_area_context(area_index)
            if error:
                return {"error": error}

            if names is None:
                target_objects = list(bpy.context.selected_objects)
            elif isinstance(names, str):
                target_objects = [bpy.data.objects.get(part.strip()) for part in names.split(",") if part.strip()]
            elif isinstance(names, (list, tuple)):
                target_objects = [bpy.data.objects.get(str(name).strip()) for name in names if str(name).strip()]
            else:
                return {"error": "names must be an array of object names, a comma-separated string, or omitted"}

            missing_names = []
            if names is not None:
                raw_names = [part.strip() for part in names.split(",") if part.strip()] if isinstance(names, str) else [str(name).strip() for name in names if str(name).strip()]
                found_names = {obj.name for obj in target_objects if obj is not None}
                missing_names = [name for name in raw_names if name not in found_names]

            target_objects = [obj for obj in target_objects if obj is not None]
            if not target_objects:
                return {"error": "No target objects found to focus viewport", "missing_objects": missing_names}

            previous_selection = list(bpy.context.selected_objects)
            previous_active = bpy.context.view_layer.objects.active
            previous_context_object = bpy.context.object
            previous_mode = previous_context_object.mode if previous_context_object else "OBJECT"
            changed_mode = False

            try:
                if bpy.context.object and bpy.context.object.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                    changed_mode = True
                bpy.ops.object.select_all(action='DESELECT')
                for obj in target_objects:
                    obj.select_set(True)
                bpy.context.view_layer.objects.active = target_objects[0]

                with bpy.context.temp_override(area=area, region=region, space_data=space):
                    bpy.ops.view3d.view_selected(use_all_regions=False)
            finally:
                with suppress(Exception):
                    if bpy.context.object and bpy.context.object.mode != "OBJECT":
                        bpy.ops.object.mode_set(mode="OBJECT")
                    bpy.ops.object.select_all(action='DESELECT')
                    for obj in previous_selection:
                        if obj.name in bpy.data.objects:
                            obj.select_set(True)
                    if previous_active and previous_active.name in bpy.data.objects:
                        bpy.context.view_layer.objects.active = previous_active
                    if changed_mode and previous_context_object and previous_context_object.name in bpy.data.objects:
                        bpy.context.view_layer.objects.active = previous_context_object
                        previous_context_object.select_set(True)
                        bpy.ops.object.mode_set(mode=previous_mode)

            region_3d = getattr(space, "region_3d", None)
            return {
                "success": True,
                "area_index": self._view3d_areas().index(area),
                "focused_objects": [obj.name for obj in target_objects],
                "missing_objects": missing_names,
                "view": {
                    "view_location": list(getattr(region_3d, "view_location", [])) if region_3d else None,
                    "view_distance": float(getattr(region_3d, "view_distance", 0.0)) if region_3d else None,
                    "view_perspective": str(getattr(region_3d, "view_perspective", "")) if region_3d else None,
                },
                "next_safe_action": "capture get_viewport_screenshot with the same area_index to verify framing",
            }
        except Exception as e:
            return {"error": f"Failed to focus viewport: {str(e)}"}

    def get_viewport_screenshot(self, max_size=800, filepath=None, format="png", area_index=None):
        """
        Capture a screenshot of the current 3D viewport.

        Parameters:
        - max_size: Maximum size in pixels for the largest dimension of the image
        - filepath: Optional path to save the screenshot file. If None, returns
                    the image as base64-encoded data directly.
        - format: Image format (png, jpg, etc.)

        Returns:
        - If filepath: {success, width, height, filepath}
        - If no filepath: {image (base64), width, height, format}
        """
        import os
        import tempfile
        import base64

        return_base64 = filepath is None
        try:
            area, region, space, error = self._view3d_area_context(area_index)
            if error:
                return {"error": error}

            # Determine file path — use temp if none provided
            if return_base64:
                tmp = tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False)
                filepath = tmp.name
                tmp.close()

            # Take screenshot with proper context override
            with bpy.context.temp_override(area=area, region=region, space_data=space):
                bpy.ops.screen.screenshot_area(filepath=filepath)

            # Load and resize if needed
            img = bpy.data.images.load(filepath)
            width, height = img.size

            if max(width, height) > max_size:
                scale = max_size / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img.scale(new_width, new_height)

                # Set format and save
                img.file_format = format.upper()
                img.save()
                width, height = new_width, new_height

            # Cleanup Blender image data
            bpy.data.images.remove(img)

            if return_base64:
                # Read the file and encode as base64
                with open(filepath, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode("utf-8")
                # Clean up temp file
                try:
                    os.remove(filepath)
                except OSError:
                    pass
                return {
                    "image": image_data,
                    "width": width,
                    "height": height,
                    "format": format,
                    "area_index": self._view3d_areas().index(area),
                }
            else:
                return {
                    "success": True,
                    "width": width,
                    "height": height,
                    "filepath": filepath,
                    "area_index": self._view3d_areas().index(area),
                }

        except Exception as e:
            # Clean up temp file on error
            if return_base64 and filepath:
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            return {"error": str(e)}

    def render_viewport_to_path(self, output_path=None, max_size=1200, format="png", area_index=None):
        """Save a viewport preview artifact to disk without touching final render settings."""
        try:
            fmt = str(format or "png").lower()
            extension = {
                "jpeg": "jpg",
                "jpg": "jpg",
                "png": "png",
                "webp": "webp",
                "tiff": "tiff",
                "tif": "tiff",
            }.get(fmt, fmt)
            if not output_path:
                output_path = os.path.join(tempfile.gettempdir(), f"vipermesh-viewport-{int(time.time() * 1000)}.{extension}")
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            result = self.get_viewport_screenshot(
                max_size=max(128, min(int(max_size), 4096)),
                filepath=output_path,
                format=fmt,
                area_index=area_index,
            )
            if result.get("error"):
                return result

            return {
                "success": True,
                "viewport_render": True,
                "output_path": result.get("filepath", output_path),
                "width": result.get("width"),
                "height": result.get("height"),
                "format": fmt,
                "area_index": result.get("area_index"),
                "next_safe_action": "use output_path as a viewport preview artifact; use render_thumbnail_to_path for studio-lit thumbnails or render_image for final renders",
            }
        except Exception as e:
            return {"error": f"Failed to render viewport preview: {str(e)}"}

    def _find_layer_collection(self, collection_name, layer_collection=None):
        layer_collection = layer_collection or bpy.context.view_layer.layer_collection
        if layer_collection.collection.name == collection_name:
            return layer_collection
        for child in layer_collection.children:
            found = self._find_layer_collection(collection_name, child)
            if found:
                return found
        return None

    def select_scene_objects(self, names=None, active_name=None, selection_mode="REPLACE"):
        """Select scene objects and optionally set the active object for guided debugging."""
        previous_context_object = bpy.context.object
        previous_mode = previous_context_object.mode if previous_context_object else "OBJECT"
        changed_mode = False
        try:
            if names is None:
                requested_names = []
            elif isinstance(names, str):
                requested_names = [part.strip() for part in names.split(",") if part.strip()]
            elif isinstance(names, (list, tuple)):
                requested_names = [str(name).strip() for name in names if str(name).strip()]
            else:
                return {"error": "names must be an array of object names, a comma-separated string, or omitted"}
            requested_names = list(dict.fromkeys(requested_names))

            active_name = str(active_name).strip() if active_name else None
            if active_name and active_name not in requested_names:
                requested_names.append(active_name)
            if not requested_names:
                return {"error": "select_scene_objects requires names or active_name"}

            mode = str(selection_mode or "REPLACE").upper()
            if mode not in {"REPLACE", "ADD", "REMOVE", "TOGGLE"}:
                return {"error": "selection_mode must be REPLACE, ADD, REMOVE, or TOGGLE"}

            if bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
                changed_mode = True

            if mode == "REPLACE":
                bpy.ops.object.select_all(action='DESELECT')

            selected_objects = []
            missing_objects = []
            for obj_name in requested_names:
                obj = bpy.data.objects.get(obj_name)
                if not obj:
                    missing_objects.append(obj_name)
                    continue
                if mode == "REMOVE":
                    obj.select_set(False)
                elif mode == "TOGGLE":
                    obj.select_set(not obj.select_get())
                else:
                    obj.select_set(True)
                if obj.select_get():
                    selected_objects.append(obj.name)

            active_obj = None
            if active_name:
                active_obj = bpy.data.objects.get(active_name)
                if active_obj and active_obj.select_get():
                    bpy.context.view_layer.objects.active = active_obj
            elif selected_objects:
                active_obj = bpy.data.objects.get(selected_objects[0])
                if active_obj:
                    bpy.context.view_layer.objects.active = active_obj

            return {
                "success": bool(selected_objects) or mode == "REMOVE",
                "selection_mode": mode,
                "selected_objects": [obj.name for obj in bpy.context.selected_objects],
                "active_object": bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
                "missing_objects": missing_objects,
                "warnings": [f"Missing object(s): {', '.join(missing_objects)}"] if missing_objects else [],
                "next_safe_action": "use focus_viewport_on_objects or inspect_collection_hierarchy to verify the selected context",
            }
        except Exception as e:
            return {"error": f"Failed to select scene objects: {str(e)}"}
        finally:
            with suppress(Exception):
                if changed_mode and previous_context_object and previous_context_object.name in bpy.data.objects:
                    bpy.context.view_layer.objects.active = previous_context_object
                    previous_context_object.select_set(True)
                    bpy.ops.object.mode_set(mode=previous_mode)

    def set_active_collection(self, collection_name, create_new=False):
        """Set the active layer collection in the current view layer for guided organization/debugging."""
        try:
            if not collection_name:
                return {"error": "collection_name is required"}

            collection_name = str(collection_name).strip()
            collection = bpy.data.collections.get(collection_name)
            created_new = False
            if not collection:
                if not create_new:
                    available = [collection.name for collection in bpy.data.collections]
                    return {"error": f"Collection '{collection_name}' not found", "available_collections": available}
                collection = bpy.data.collections.new(collection_name)
                bpy.context.scene.collection.children.link(collection)
                created_new = True

            layer_collection = self._find_layer_collection(collection.name)
            if not layer_collection:
                return {"error": f"Collection '{collection.name}' is not visible in the active view layer"}

            bpy.context.view_layer.active_layer_collection = layer_collection
            return {
                "success": True,
                "collection": collection.name,
                "created_new": created_new,
                "active_layer_collection": bpy.context.view_layer.active_layer_collection.collection.name,
                "next_safe_action": "use organize_collection_hierarchy or move_to_collection to place objects in the active collection",
            }
        except Exception as e:
            return {"error": f"Failed to set active collection: {str(e)}"}

    def execute_code(self, code):
        """Execute arbitrary Blender Python code"""
        # This is powerful but potentially dangerous - use with caution
        try:
            # Create a local namespace for execution
            namespace = {"bpy": bpy}

            # Capture stdout during execution, and return it as result
            capture_buffer = io.StringIO()
            with redirect_stdout(capture_buffer):
                exec(code, namespace)

            captured_output = capture_buffer.getvalue()
            return {"executed": True, "result": captured_output}
        except Exception as e:
            raise Exception(f"Code execution error: {str(e)}")

    def save_blend_file(self, filepath, make_dirs=True, check_existing=False, copy=False):
        """Save the current .blend file to an explicit path."""
        try:
            if not filepath or not str(filepath).strip():
                return {"error": "filepath must be provided"}

            resolved_path = os.path.abspath(os.path.expanduser(str(filepath)))
            if not resolved_path.lower().endswith(".blend"):
                return {"error": "filepath must end with .blend"}

            output_dir = os.path.dirname(resolved_path)
            if output_dir and not os.path.isdir(output_dir):
                if make_dirs:
                    os.makedirs(output_dir, exist_ok=True)
                else:
                    return {"error": f"Output directory does not exist: {output_dir}"}

            if check_existing and os.path.exists(resolved_path):
                return {"error": f"File already exists: {resolved_path}. Set check_existing=false to overwrite."}

            bpy.ops.wm.save_as_mainfile(filepath=resolved_path, check_existing=bool(check_existing), copy=bool(copy))

            return {
                "success": True,
                "filepath": resolved_path,
                "copy": bool(copy),
                "exists": os.path.exists(resolved_path),
                "size": os.path.getsize(resolved_path) if os.path.exists(resolved_path) else None,
                "next_safe_action": "attach this .blend path as benchmark or export evidence",
            }
        except Exception as e:
            return {"error": f"Failed to save blend file: {str(e)}"}

    def restore_blend_checkpoint(self, checkpoint_filepath, original_filepath):
        """Restore a saved checkpoint and return Blender to the original .blend path."""
        try:
            checkpoint_path = os.path.abspath(
                os.path.expanduser(str(checkpoint_filepath))
            )
            original_path = os.path.abspath(
                os.path.expanduser(str(original_filepath))
            )
            if not checkpoint_path.lower().endswith(".blend"):
                return {"error": "checkpoint_filepath must end with .blend"}
            if not original_path.lower().endswith(".blend"):
                return {"error": "original_filepath must end with .blend"}
            if not os.path.isfile(checkpoint_path):
                return {
                    "error": f"Checkpoint file does not exist: {checkpoint_path}"
                }

            bpy.ops.wm.open_mainfile(filepath=checkpoint_path)
            bpy.ops.wm.save_as_mainfile(
                filepath=original_path,
                check_existing=False,
            )
            return {
                "success": True,
                "restored": True,
                "checkpoint_filepath": checkpoint_path,
                "filepath": bpy.data.filepath,
                "original_filepath": original_path,
                "dirty": bool(getattr(bpy.data, "is_dirty", False)),
                "next_safe_action": "re-run inspect_blend_file_health before retrying the failed operation",
            }
        except Exception as e:
            return {
                "error": f"Failed to restore blend checkpoint: {str(e)}",
                "restored": False,
            }

    def list_materials(self):
        """List all materials in the .blend file with their node counts and linked objects"""
        try:
            materials = []
            for mat in bpy.data.materials:
                mat_info = {
                    "name": mat.name,
                    "use_nodes": mat.use_nodes,
                    "node_count": len(mat.node_tree.nodes) if mat.use_nodes and mat.node_tree else 0,
                    "users": mat.users,
                    "linked_objects": [],
                }
                # Find objects using this material
                for obj in bpy.data.objects:
                    if obj.type == 'MESH' and obj.data:
                        for slot in obj.material_slots:
                            if slot.material == mat:
                                mat_info["linked_objects"].append(obj.name)
                                break
                materials.append(mat_info)
            return {"materials": materials, "count": len(materials)}
        except Exception as e:
            return {"error": str(e)}

    def delete_object(self, name):
        """Safely delete an object from the scene by name"""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}

            obj_type = obj.type
            # Store mesh/data ref for orphan cleanup
            obj_data = obj.data

            # Deselect all, select target, delete
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.delete(use_global=False)

            # Clean up orphaned mesh data
            if obj_data and obj_data.users == 0:
                if obj_type == 'MESH':
                    bpy.data.meshes.remove(obj_data)
                elif obj_type == 'CURVE':
                    bpy.data.curves.remove(obj_data)
                elif obj_type == 'LIGHT':
                    bpy.data.lights.remove(obj_data)
                elif obj_type == 'CAMERA':
                    bpy.data.cameras.remove(obj_data)

            return {
                "success": True,
                "message": f"Deleted object '{name}' (type: {obj_type})",
                "remaining_objects": len(bpy.context.scene.objects)
            }
        except Exception as e:
            return {"error": f"Failed to delete object: {str(e)}"}

    def delete_objects(self, names=None, ignore_missing=True, max_delete=500):
        """Safely delete multiple explicitly named objects from the scene."""
        try:
            if not isinstance(names, (list, tuple)) or len(names) == 0:
                return {"error": "names must be a non-empty list"}

            resolved_max = int(max_delete)
            if resolved_max < 1 or resolved_max > 1000:
                return {"error": "max_delete must be between 1 and 1000"}
            if len(names) > resolved_max:
                return {"error": f"Refusing to delete {len(names)} objects; max_delete is {resolved_max}"}

            deleted = []
            missing = []
            skipped = []
            seen = set()
            for raw_name in names:
                object_name = str(raw_name or "").strip()
                if not object_name:
                    skipped.append({"name": raw_name, "reason": "empty name"})
                    continue
                if object_name in seen:
                    skipped.append({"name": object_name, "reason": "duplicate request"})
                    continue
                seen.add(object_name)

                obj = bpy.data.objects.get(object_name)
                if not obj:
                    missing.append(object_name)
                    continue

                obj_type = obj.type
                obj_data = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if obj_data and obj_data.users == 0:
                    if obj_type == 'MESH':
                        bpy.data.meshes.remove(obj_data)
                    elif obj_type == 'CURVE':
                        bpy.data.curves.remove(obj_data)
                    elif obj_type == 'LIGHT':
                        bpy.data.lights.remove(obj_data)
                    elif obj_type == 'CAMERA':
                        bpy.data.cameras.remove(obj_data)
                deleted.append({"name": object_name, "type": obj_type})

            if missing and not ignore_missing:
                return {"error": f"Objects not found: {', '.join(missing)}", "deleted": deleted, "missing": missing}

            return {
                "success": True,
                "deleted_count": len(deleted),
                "deleted": deleted,
                "missing": missing,
                "skipped": skipped,
                "remaining_objects": len(bpy.context.scene.objects),
                "next_safe_action": "run get_scene_info or get_all_object_info to verify the remaining scene contents",
            }
        except Exception as e:
            return {"error": f"Failed to delete objects: {str(e)}"}

    # ---------- Phase 1A: Transform Tools ----------

    def set_object_transform(self, name, location=None, rotation=None, scale=None):
        """Set an object's location, rotation (euler degrees), and/or scale"""
        try:
            import math
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}

            changes = []
            if location is not None:
                obj.location = (float(location[0]), float(location[1]), float(location[2]))
                changes.append("location")
            if rotation is not None:
                obj.rotation_euler = (
                    math.radians(float(rotation[0])),
                    math.radians(float(rotation[1])),
                    math.radians(float(rotation[2])),
                )
                changes.append("rotation")
            if scale is not None:
                obj.scale = (float(scale[0]), float(scale[1]), float(scale[2]))
                changes.append("scale")

            if not changes:
                return {"error": "No transform values provided. Supply location, rotation, and/or scale."}

            return {
                "success": True,
                "object": name,
                "changed": changes,
                "location": list(obj.location),
                "rotation_degrees": [math.degrees(r) for r in obj.rotation_euler],
                "scale": list(obj.scale),
            }
        except Exception as e:
            return {"error": f"Failed to set transform: {str(e)}"}

    def _placement_world_bounds(self, obj):
        """Use evaluated geometry, including descendants of imported assembly roots."""
        candidates = list(obj.children_recursive) if obj.type == 'EMPTY' else [obj]
        geometry_types = {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}
        geometry = [item for item in candidates if item.type in geometry_types]
        if not geometry:
            raise ValueError(f"Object '{obj.name}' has no geometry for placement bounds")
        depsgraph = bpy.context.evaluated_depsgraph_get()
        points = []
        for item in geometry:
            evaluated = item.evaluated_get(depsgraph)
            points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
        return (
            Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
            Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
        )

    def align_object_to_surface(
        self,
        name,
        placement="GROUND",
        reference_name=None,
        axis="Z",
        surface_value=0.0,
        margin=0.002,
    ):
        """Align object world-space bounds to ground, support top, or side faces."""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}
            if not getattr(obj, "bound_box", None):
                return {"error": f"Object '{name}' has no bounding box for surface alignment"}

            def world_bounds(target_obj):
                return self._placement_world_bounds(target_obj)

            placement_key = str(placement or "GROUND").upper().replace("-", "_").replace(" ", "_")
            aliases = {
                "FLOOR": "GROUND",
                "GROUND_Z": "GROUND",
                "ON_TOP_OF": "ON_TOP",
                "TOP": "ON_TOP",
                "BESIDE_POSITIVE": "SIDE_POSITIVE",
                "BESIDE_NEGATIVE": "SIDE_NEGATIVE",
            }
            placement_key = aliases.get(placement_key, placement_key)
            allowed = {"GROUND", "ON_TOP", "SIDE_POSITIVE", "SIDE_NEGATIVE"}
            if placement_key not in allowed:
                return {"error": f"placement must be one of: {', '.join(sorted(allowed))}"}

            axis_key = str(axis or "Z").upper()
            axis_index = {"X": 0, "Y": 1, "Z": 2}.get(axis_key)
            if axis_index is None:
                return {"error": "axis must be X, Y, or Z"}

            resolved_margin = float(margin)
            if resolved_margin < -1000.0 or resolved_margin > 1000.0:
                return {"error": "margin must be between -1000.0 and 1000.0"}

            reference_obj = None
            if placement_key != "GROUND":
                if not reference_name:
                    return {"error": f"reference_name is required for {placement_key} placement"}
                reference_obj = bpy.data.objects.get(reference_name)
                if not reference_obj:
                    return {"error": f"Reference object not found: {reference_name}"}
                if reference_obj == obj:
                    return {"error": "reference_name must refer to a different object"}
                if reference_obj in obj.children_recursive or obj in reference_obj.children_recursive:
                    return {"error": "Support and subject must not contain one another in the same hierarchy"}
                if not getattr(reference_obj, "bound_box", None):
                    return {"error": f"Reference object '{reference_name}' has no bounding box"}

            obj_min, obj_max = world_bounds(obj)
            ref_min = ref_max = None
            if reference_obj:
                ref_min, ref_max = world_bounds(reference_obj)

            delta = Vector((0.0, 0.0, 0.0))
            if placement_key == "GROUND":
                delta[axis_index] = (float(surface_value) + resolved_margin) - obj_min[axis_index]
            elif placement_key == "ON_TOP":
                if axis_key != "Z":
                    return {"error": "ON_TOP placement requires axis=Z"}
                delta.z = (ref_max.z + resolved_margin) - obj_min.z
            elif placement_key == "SIDE_POSITIVE":
                delta[axis_index] = (ref_max[axis_index] + resolved_margin) - obj_min[axis_index]
            else:
                delta[axis_index] = (ref_min[axis_index] - resolved_margin) - obj_max[axis_index]

            before_location = obj.location.copy()
            matrix = obj.matrix_world.copy()
            matrix.translation += delta
            obj.matrix_world = matrix
            bpy.context.view_layer.update()
            after_min, after_max = world_bounds(obj)

            return {
                "success": True,
                "object": obj.name,
                "placement": placement_key,
                "reference": reference_obj.name if reference_obj else None,
                "axis": axis_key,
                "margin": resolved_margin,
                "delta": [round(value, 6) for value in delta],
                "old_location": [round(value, 6) for value in before_location],
                "new_location": [round(value, 6) for value in obj.location],
                "bounds_min": [round(value, 6) for value in after_min],
                "bounds_max": [round(value, 6) for value in after_max],
                "next_safe_action": "use get_object_info or a viewport screenshot to verify contact and clearance",
            }
        except Exception as e:
            return {"error": f"Failed to align object to surface: {str(e)}"}

    def validate_object_clearance(self, name, other_name, margin=0.0):
        """Validate world-space AABB clearance or overlap between two objects."""
        try:
            obj = bpy.data.objects.get(name)
            other = bpy.data.objects.get(other_name)
            if not obj:
                return {"error": f"Object not found: {name}"}
            if not other:
                return {"error": f"Other object not found: {other_name}"}
            if obj == other:
                return {"error": "name and other_name must refer to different objects"}

            def world_bounds(target_obj):
                if not getattr(target_obj, "bound_box", None):
                    raise ValueError(f"Object '{target_obj.name}' has no bounding box")
                return self._placement_world_bounds(target_obj)

            resolved_margin = float(margin)
            if resolved_margin < 0.0 or resolved_margin > 1000.0:
                return {"error": "margin must be between 0.0 and 1000.0"}

            obj_min, obj_max = world_bounds(obj)
            other_min, other_max = world_bounds(other)

            axes = ["X", "Y", "Z"]
            axis_reports = {}
            separating_gaps = []
            overlap_axes = []

            for index, axis_name in enumerate(axes):
                if obj_max[index] <= other_min[index]:
                    gap = other_min[index] - obj_max[index]
                    axis_reports[axis_name] = {"relation": "before", "gap": round(gap, 6), "overlap_depth": 0.0}
                    separating_gaps.append(gap)
                elif other_max[index] <= obj_min[index]:
                    gap = obj_min[index] - other_max[index]
                    axis_reports[axis_name] = {"relation": "after", "gap": round(gap, 6), "overlap_depth": 0.0}
                    separating_gaps.append(gap)
                else:
                    overlap_depth = min(obj_max[index], other_max[index]) - max(obj_min[index], other_min[index])
                    axis_reports[axis_name] = {"relation": "overlap", "gap": 0.0, "overlap_depth": round(overlap_depth, 6)}
                    overlap_axes.append(axis_name)

            overlap = len(overlap_axes) == 3
            minimum_gap = min(separating_gaps) if separating_gaps else 0.0
            clearance_ok = (not overlap) and bool(separating_gaps) and minimum_gap >= resolved_margin

            return {
                "success": True,
                "object": obj.name,
                "other_object": other.name,
                "margin": resolved_margin,
                "overlap": overlap,
                "clearance_ok": clearance_ok,
                "minimum_gap": round(minimum_gap, 6),
                "overlap_axes": overlap_axes,
                "axes": axis_reports,
                "bounds": {
                    obj.name: {
                        "min": [round(value, 6) for value in obj_min],
                        "max": [round(value, 6) for value in obj_max],
                    },
                    other.name: {
                        "min": [round(value, 6) for value in other_min],
                        "max": [round(value, 6) for value in other_max],
                    },
                },
                "next_safe_action": "adjust with align_object_to_surface or set_object_transform if overlap is true or clearance_ok is false",
            }
        except Exception as e:
            return {"error": f"Failed to validate object clearance: {str(e)}"}

    def inspect_spatial_relations(self, relations=None, tolerance=0.03):
        """Inspect named spatial relations using world-space bounds and transforms."""
        try:
            if relations is None:
                relations = []
            if isinstance(relations, str):
                relations = json.loads(relations)
            if not isinstance(relations, list):
                return {"error": "relations must be a list of relation objects"}
            if len(relations) > 100:
                return {"error": "relations may contain at most 100 checks"}

            resolved_tolerance = max(0.0, float(tolerance or 0.0))

            def object_name(relation, *keys):
                for key in keys:
                    value = relation.get(key)
                    if value:
                        return str(value)
                return None

            def bounds_for(obj):
                if obj.type in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'} or (
                    obj.type == 'EMPTY' and any(
                        child.type in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}
                        for child in obj.children_recursive
                    )
                ):
                    min_corner, max_corner = self._placement_world_bounds(obj)
                elif getattr(obj, "bound_box", None):
                    corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
                    min_corner = mathutils.Vector((
                        min(corner.x for corner in corners),
                        min(corner.y for corner in corners),
                        min(corner.z for corner in corners),
                    ))
                    max_corner = mathutils.Vector((
                        max(corner.x for corner in corners),
                        max(corner.y for corner in corners),
                        max(corner.z for corner in corners),
                    ))
                else:
                    center = obj.matrix_world.translation
                    min_corner = center.copy()
                    max_corner = center.copy()
                return {
                    "min": min_corner,
                    "max": max_corner,
                    "center": (min_corner + max_corner) * 0.5,
                    "size": max_corner - min_corner,
                }

            def axis_vector(label):
                normalized = str(label or "-Y").strip().upper()
                vectors = {
                    "+X": mathutils.Vector((1, 0, 0)),
                    "X": mathutils.Vector((1, 0, 0)),
                    "-X": mathutils.Vector((-1, 0, 0)),
                    "+Y": mathutils.Vector((0, 1, 0)),
                    "Y": mathutils.Vector((0, 1, 0)),
                    "-Y": mathutils.Vector((0, -1, 0)),
                    "+Z": mathutils.Vector((0, 0, 1)),
                    "Z": mathutils.Vector((0, 0, 1)),
                    "-Z": mathutils.Vector((0, 0, -1)),
                }
                return vectors.get(normalized, vectors["-Y"])

            def overlap_amount(a_min, a_max, b_min, b_max):
                return min(a_max, b_max) - max(a_min, b_min)

            def xy_overlap(subject_bounds, reference_bounds):
                overlap_x = overlap_amount(
                    subject_bounds["min"].x,
                    subject_bounds["max"].x,
                    reference_bounds["min"].x,
                    reference_bounds["max"].x,
                )
                overlap_y = overlap_amount(
                    subject_bounds["min"].y,
                    subject_bounds["max"].y,
                    reference_bounds["min"].y,
                    reference_bounds["max"].y,
                )
                return overlap_x, overlap_y

            def relation_passes(relation_type, subject, reference, other, relation):
                subject_bounds = bounds_for(subject)
                reference_bounds = bounds_for(reference) if reference else None
                other_bounds = bounds_for(other) if other else None
                margin = float(relation.get("margin", resolved_tolerance) or 0.0)
                relation_type = str(relation_type or "").strip().lower()
                details = {}

                if reference_bounds:
                    details["subject_center"] = [round(value, 6) for value in subject_bounds["center"]]
                    details["reference_center"] = [round(value, 6) for value in reference_bounds["center"]]

                if relation_type in {"north_of", "south_of", "east_of", "west_of", "above", "below"}:
                    axis, sign = {
                        "north_of": ("y", 1),
                        "south_of": ("y", -1),
                        "east_of": ("x", 1),
                        "west_of": ("x", -1),
                        "above": ("z", 1),
                        "below": ("z", -1),
                    }[relation_type]
                    delta = getattr(subject_bounds["center"], axis) - getattr(reference_bounds["center"], axis)
                    details["axis_delta"] = round(delta, 6)
                    return sign * delta > margin, details

                if relation_type in {"inside_xy", "contains_xy"}:
                    inside = (
                        subject_bounds["min"].x >= reference_bounds["min"].x - margin
                        and subject_bounds["max"].x <= reference_bounds["max"].x + margin
                        and subject_bounds["min"].y >= reference_bounds["min"].y - margin
                        and subject_bounds["max"].y <= reference_bounds["max"].y + margin
                    )
                    details["subject_bounds_min"] = [round(value, 6) for value in subject_bounds["min"]]
                    details["subject_bounds_max"] = [round(value, 6) for value in subject_bounds["max"]]
                    return inside, details

                if relation_type == "outside_xy":
                    inside = (
                        subject_bounds["min"].x >= reference_bounds["min"].x - margin
                        and subject_bounds["max"].x <= reference_bounds["max"].x + margin
                        and subject_bounds["min"].y >= reference_bounds["min"].y - margin
                        and subject_bounds["max"].y <= reference_bounds["max"].y + margin
                    )
                    return not inside, details

                if relation_type in {"supported_by", "on_top_of"}:
                    overlap_x, overlap_y = xy_overlap(subject_bounds, reference_bounds)
                    vertical_gap = subject_bounds["min"].z - reference_bounds["max"].z
                    supported = overlap_x > margin and overlap_y > margin and abs(vertical_gap) <= max(resolved_tolerance, margin)
                    details.update({
                        "vertical_gap": round(vertical_gap, 6),
                        "xy_overlap": [round(overlap_x, 6), round(overlap_y, 6)],
                    })
                    return supported, details

                if relation_type == "closer_to":
                    if other is None or other_bounds is None:
                        return False, {"error": "closer_to requires other/other_name"}
                    distance_to_reference = (subject_bounds["center"] - reference_bounds["center"]).length
                    distance_to_other = (subject_bounds["center"] - other_bounds["center"]).length
                    details.update({
                        "distance_to_reference": round(distance_to_reference, 6),
                        "distance_to_other": round(distance_to_other, 6),
                    })
                    return distance_to_reference + margin < distance_to_other, details

                if relation_type == "facing":
                    direction = reference_bounds["center"] - subject_bounds["center"]
                    if direction.length == 0:
                        return False, {"error": "subject and reference centers are identical"}
                    direction.normalize()
                    local_axis = axis_vector(relation.get("local_axis", "-Y"))
                    forward = subject.matrix_world.to_quaternion() @ local_axis
                    if forward.length == 0:
                        return False, {"error": "subject facing vector has zero length"}
                    forward.normalize()
                    dot = forward.dot(direction)
                    min_dot = float(relation.get("min_dot")) if relation.get("min_dot") is not None else 0.5
                    details.update({
                        "dot": round(dot, 6),
                        "min_dot": round(min_dot, 6),
                        "local_axis": str(relation.get("local_axis", "-Y")),
                    })
                    return dot >= min_dot, details

                return False, {"error": f"Unsupported relation type: {relation_type}"}

            checked = []
            missing_objects = []
            for index, relation in enumerate(relations):
                if not isinstance(relation, dict):
                    checked.append({
                        "index": index,
                        "status": "fail",
                        "error": "relation must be an object",
                    })
                    continue

                relation_type = relation.get("type") or relation.get("relation")
                subject_name = object_name(relation, "subject", "subject_name", "name")
                reference_name = object_name(relation, "reference", "reference_name", "other_name")
                alternate_name = object_name(relation, "other", "alternate", "alternate_name")
                subject = bpy.data.objects.get(subject_name) if subject_name else None
                reference = bpy.data.objects.get(reference_name) if reference_name else None
                other = bpy.data.objects.get(alternate_name) if alternate_name else None

                missing = []
                if not subject:
                    missing.append(subject_name or "subject")
                if relation_type and not reference:
                    missing.append(reference_name or "reference")
                if str(relation_type or "").strip().lower() == "closer_to" and not other:
                    missing.append(alternate_name or "other")
                if missing:
                    missing_objects.extend(missing)
                    checked.append({
                        "index": index,
                        "type": relation_type,
                        "subject": subject_name,
                        "reference": reference_name,
                        "other": alternate_name,
                        "status": "fail",
                        "missing": missing,
                    })
                    continue

                try:
                    passed, details = relation_passes(relation_type, subject, reference, other, relation)
                    checked.append({
                        "index": index,
                        "type": relation_type,
                        "subject": subject_name,
                        "reference": reference_name,
                        "other": alternate_name,
                        "status": "pass" if passed else "fail",
                        "passed": bool(passed),
                        "details": details,
                    })
                except Exception as relation_error:
                    checked.append({
                        "index": index,
                        "type": relation_type,
                        "subject": subject_name,
                        "reference": reference_name,
                        "other": alternate_name,
                        "status": "fail",
                        "passed": False,
                        "details": {"error": str(relation_error)},
                    })

            failed = [item for item in checked if item.get("status") != "pass"]
            return {
                "ready": len(failed) == 0,
                "checked_count": len(checked),
                "pass_count": len(checked) - len(failed),
                "fail_count": len(failed),
                "missing_objects": sorted(set(missing_objects)),
                "relations": checked,
                "next_safe_action": "fix failed named relations with set_object_transform, align_object_to_surface, arrange_objects, or curve tools; then inspect_spatial_relations again",
            }
        except Exception as e:
            return {"error": f"Failed to inspect spatial relations: {str(e)}"}

    def inspect_mesh_intersections(self, pairs=None, max_intersections=10000, epsilon=0.000001):
        """Inspect evaluated mesh-surface intersections for explicit object pairs."""
        try:
            if pairs is None:
                pairs = []
            if isinstance(pairs, str):
                pairs = json.loads(pairs)
            if not isinstance(pairs, list) or not pairs:
                return {"error": "pairs must be a non-empty list of {subject, reference} objects"}
            if len(pairs) > 100:
                return {"error": "pairs may contain at most 100 checks"}

            resolved_limit = max(1, min(int(max_intersections), 100000))
            resolved_epsilon = max(0.0, min(float(epsilon), 1.0))
            depsgraph = bpy.context.evaluated_depsgraph_get()
            cache = {}

            def object_tree(obj):
                if obj.name in cache:
                    return cache[obj.name]
                evaluated = obj.evaluated_get(depsgraph)
                mesh = evaluated.to_mesh()
                try:
                    mesh.calc_loop_triangles()
                    vertices = [
                        evaluated.matrix_world @ vertex.co
                        for vertex in mesh.vertices
                    ]
                    polygons = [
                        tuple(int(index) for index in triangle.vertices)
                        for triangle in mesh.loop_triangles
                    ]
                    tree = BVHTree.FromPolygons(
                        vertices,
                        polygons,
                        all_triangles=True,
                        epsilon=resolved_epsilon,
                    )
                finally:
                    evaluated.to_mesh_clear()
                cache[obj.name] = tree
                return tree

            checked = []
            missing_objects = []
            for index, pair in enumerate(pairs):
                if not isinstance(pair, dict):
                    checked.append({
                        "index": index,
                        "status": "fail",
                        "error": "pair must be an object",
                    })
                    continue
                subject_name = str(
                    pair.get("subject") or pair.get("name") or ""
                ).strip()
                reference_name = str(
                    pair.get("reference") or pair.get("other_name") or ""
                ).strip()
                subject = bpy.data.objects.get(subject_name)
                reference = bpy.data.objects.get(reference_name)
                missing = [
                    name
                    for name, obj in (
                        (subject_name or "subject", subject),
                        (reference_name or "reference", reference),
                    )
                    if obj is None
                ]
                if missing:
                    missing_objects.extend(missing)
                    checked.append({
                        "index": index,
                        "subject": subject_name,
                        "reference": reference_name,
                        "status": "fail",
                        "missing": missing,
                    })
                    continue
                if subject.type != "MESH" or reference.type != "MESH":
                    checked.append({
                        "index": index,
                        "subject": subject_name,
                        "reference": reference_name,
                        "status": "fail",
                        "error": "both objects must be meshes",
                    })
                    continue
                if subject == reference:
                    checked.append({
                        "index": index,
                        "subject": subject_name,
                        "reference": reference_name,
                        "status": "fail",
                        "error": "subject and reference must be different objects",
                    })
                    continue

                overlaps = object_tree(subject).overlap(object_tree(reference))
                intersection_count = len(overlaps)
                checked.append({
                    "index": index,
                    "subject": subject_name,
                    "reference": reference_name,
                    "status": "pass" if intersection_count == 0 else "fail",
                    "intersects": intersection_count > 0,
                    "intersection_count": intersection_count,
                    "sample_polygon_pairs": [
                        [int(subject_polygon), int(reference_polygon)]
                        for subject_polygon, reference_polygon
                        in overlaps[:resolved_limit]
                    ],
                    "intersections_truncated": intersection_count > resolved_limit,
                })

            failed = [item for item in checked if item.get("status") != "pass"]
            return {
                "success": len(missing_objects) == 0,
                "ready": len(failed) == 0,
                "checked_count": len(checked),
                "pass_count": len(checked) - len(failed),
                "fail_count": len(failed),
                "missing_objects": sorted(set(missing_objects)),
                "pairs": checked,
                "next_safe_action": "fix intersecting mesh pairs, then run inspect_mesh_intersections again",
            }
        except Exception as e:
            return {"error": f"Failed to inspect mesh intersections: {str(e)}"}

    def inspect_scene_grounding(self, names=None, ground_z=0.0, tolerance=0.02, max_objects=100, include_supports=True):
        """Report mesh objects whose lower bounds float above ground or nearby support surfaces."""
        try:
            resolved_tolerance = max(0.0, float(tolerance))
            resolved_ground_z = float(ground_z)
            resolved_max_objects = max(1, min(int(max_objects), 500))
            if names is not None and not isinstance(names, (list, tuple)):
                return {"error": "names must be a list of object names when provided"}

            requested_names = {str(name) for name in names} if names else None
            mesh_objects = [
                obj for obj in bpy.context.scene.objects
                if obj.type == "MESH" and getattr(obj, "bound_box", None) and not obj.hide_get()
            ]
            if requested_names:
                missing = sorted(name for name in requested_names if name not in bpy.data.objects)
                mesh_objects = [obj for obj in mesh_objects if obj.name in requested_names]
            else:
                missing = []
                mesh_objects = mesh_objects[:resolved_max_objects]

            def world_bounds(target_obj):
                corners = [target_obj.matrix_world @ Vector(corner) for corner in target_obj.bound_box]
                min_corner = Vector((
                    min(corner.x for corner in corners),
                    min(corner.y for corner in corners),
                    min(corner.z for corner in corners),
                ))
                max_corner = Vector((
                    max(corner.x for corner in corners),
                    max(corner.y for corner in corners),
                    max(corner.z for corner in corners),
                ))
                return min_corner, max_corner

            bounds_by_name = {}
            for obj in mesh_objects:
                obj_min, obj_max = world_bounds(obj)
                bounds_by_name[obj.name] = (obj_min, obj_max)

            floating_objects = []
            grounded_objects = []
            below_ground_objects = []
            attached_objects = []
            high_priority_floating_objects = []
            low_priority_floating_objects = []

            def grounding_priority_for(obj_name, contact_type, contact_gap, attached_support_name):
                """Separate likely placement errors from intentional assembly details."""
                lowered_name = obj_name.lower()
                assembly_terms = (
                    "apron", "band", "bar", "base", "bolt", "button", "bulb", "cable_clip",
                    "crossbar", "deck", "frame", "glass", "handle", "hinge", "lever",
                    "pane", "panel", "port", "rail", "rim", "screen", "seat", "shelf",
                    "shelf_pin", "socket", "tower", "trim", "weave",
                )
                wall_terms = ("wall", "window", "mirror", "door")
                if contact_type == "attached":
                    return "low"
                if any(term in lowered_name for term in assembly_terms):
                    return "low"
                if any(term in lowered_name for term in wall_terms) and attached_support_name is not None:
                    return "low"
                if contact_gap <= max(resolved_tolerance * 2.0, 0.05):
                    return "medium"
                return "high"

            for obj in mesh_objects:
                obj_min, obj_max = bounds_by_name[obj.name]
                bottom_z = obj_min.z
                ground_gap = bottom_z - resolved_ground_z
                nearest_support = None
                nearest_support_gap = None
                vertical_support = None
                vertical_support_gap = None
                attached_support = None
                attached_overlap_volume = 0.0
                attached_side_contact_score = 0.0
                attached_axis = None
                side_contact_gap = None

                if include_supports:
                    for support in mesh_objects:
                        if support == obj:
                            continue
                        support_min, support_max = bounds_by_name[support.name]
                        overlap_x = min(obj_max.x, support_max.x) - max(obj_min.x, support_min.x)
                        overlap_y = min(obj_max.y, support_max.y) - max(obj_min.y, support_min.y)
                        overlap_z = min(obj_max.z, support_max.z) - max(obj_min.z, support_min.z)
                        if overlap_x > 0.0 and overlap_y > 0.0 and overlap_z > 0.0:
                            overlap_volume = overlap_x * overlap_y * overlap_z
                            if overlap_volume > attached_overlap_volume:
                                attached_overlap_volume = overlap_volume
                                attached_support = support.name
                                attached_axis = "volume"
                                side_contact_gap = 0.0
                        side_contacts = [
                            ("x", max(support_min.x - obj_max.x, obj_min.x - support_max.x, 0.0), overlap_y, overlap_z),
                            ("y", max(support_min.y - obj_max.y, obj_min.y - support_max.y, 0.0), overlap_x, overlap_z),
                        ]
                        for axis_name, axis_gap, overlap_a, overlap_b in side_contacts:
                            if axis_gap <= resolved_tolerance and overlap_a > 0.0 and overlap_b > 0.0:
                                contact_score = overlap_a * overlap_b
                                if attached_axis != "volume" and contact_score > attached_side_contact_score:
                                    attached_side_contact_score = contact_score
                                    attached_support = support.name
                                    attached_axis = axis_name
                                    side_contact_gap = axis_gap
                        if overlap_x <= 0.0 or overlap_y <= 0.0:
                            continue
                        support_gap = bottom_z - support_max.z
                        if support_gap < -resolved_tolerance:
                            continue
                        if nearest_support_gap is None or abs(support_gap) < abs(nearest_support_gap):
                            nearest_support_gap = support_gap
                            nearest_support = support.name
                            vertical_support_gap = support_gap
                            vertical_support = support.name

                contact_gap = ground_gap
                contact_type = "ground"
                ground_intersects_object = obj_min.z <= resolved_ground_z <= obj_max.z
                if nearest_support is not None and abs(nearest_support_gap) < abs(contact_gap):
                    contact_gap = nearest_support_gap
                    contact_type = "support"
                if ground_intersects_object:
                    contact_gap = 0.0
                    contact_type = "ground"
                elif attached_support is not None:
                    # A real overlap or side contact is physical attachment, including
                    # wall-mounted and assembled details that have no vertical support.
                    contact_gap = 0.0
                    contact_type = "attached"
                    nearest_support = attached_support
                    nearest_support_gap = 0.0

                report = {
                    "name": obj.name,
                    "bottom_z": round(bottom_z, 6),
                    "ground_gap": round(ground_gap, 6),
                    "contact_type": contact_type,
                    "contact_gap": round(contact_gap, 6),
                    "nearest_support": nearest_support,
                    "nearest_support_gap": round(nearest_support_gap, 6) if nearest_support_gap is not None else None,
                    "vertical_support": vertical_support,
                    "vertical_support_gap": round(vertical_support_gap, 6) if vertical_support_gap is not None else None,
                    "attached_support": attached_support,
                    "attached_axis": attached_axis,
                    "side_contact_gap": round(side_contact_gap, 6) if side_contact_gap is not None else None,
                    "bounds_min": [round(value, 6) for value in obj_min],
                    "bounds_max": [round(value, 6) for value in obj_max],
                }
                report["grounding_priority"] = grounding_priority_for(
                    obj.name,
                    contact_type,
                    abs(contact_gap),
                    attached_support,
                )

                if ground_intersects_object:
                    grounded_objects.append(report)
                elif bottom_z < resolved_ground_z - resolved_tolerance:
                    below_ground_objects.append(report)
                elif contact_type == "attached":
                    attached_objects.append(report)
                elif contact_gap > resolved_tolerance:
                    floating_objects.append(report)
                    if report["grounding_priority"] == "high":
                        high_priority_floating_objects.append(report)
                    elif report["grounding_priority"] == "low":
                        low_priority_floating_objects.append(report)
                else:
                    grounded_objects.append(report)

            return {
                "success": True,
                "ground_z": resolved_ground_z,
                "tolerance": resolved_tolerance,
                "checked_count": len(mesh_objects),
                "missing": missing,
                "floating_count": len(floating_objects),
                "high_priority_floating_count": len(high_priority_floating_objects),
                "low_priority_floating_count": len(low_priority_floating_objects),
                "below_ground_count": len(below_ground_objects),
                "grounded_count": len(grounded_objects),
                "attached_count": len(attached_objects),
                "floating_objects": floating_objects,
                "high_priority_floating_objects": high_priority_floating_objects,
                "low_priority_floating_sample": low_priority_floating_objects[:25],
                "below_ground_objects": below_ground_objects,
                "attached_sample": attached_objects[:25],
                "grounded_sample": grounded_objects[:25],
                "ready": len(high_priority_floating_objects) == 0 and len(below_ground_objects) == 0,
                "next_safe_action": "use align_object_to_surface for floating objects, then inspect_scene_grounding again",
            }
        except Exception as e:
            return {"error": f"Failed to inspect scene grounding: {str(e)}"}

    def align_object_attachment_points(
        self,
        name,
        obj_local_point,
        reference_name,
        reference_local_point,
        offset=None,
        preserve_rotation=True,
    ):
        """Move object so one local attachment point meets a reference local point."""
        try:
            obj = bpy.data.objects.get(name)
            reference_obj = bpy.data.objects.get(reference_name)
            if not obj:
                return {"error": f"Object not found: {name}"}
            if not reference_obj:
                return {"error": f"Reference object not found: {reference_name}"}
            if obj == reference_obj:
                return {"error": "name and reference_name must refer to different objects"}

            def vector3(value, label, default=None):
                raw = default if value is None else value
                if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                    raise ValueError(f"{label} must be [x,y,z]")
                return tuple(float(component) for component in raw[:3])

            def coerce_bool(value, default=True):
                if value is None:
                    return default
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() in {"1", "true", "yes", "on"}
                return bool(value)

            resolved_obj_local = vector3(obj_local_point, "obj_local_point")
            resolved_ref_local = vector3(reference_local_point, "reference_local_point")
            resolved_offset = Vector(vector3(offset, "offset", (0.0, 0.0, 0.0)))
            resolved_preserve_rotation = coerce_bool(preserve_rotation, True)
            if not resolved_preserve_rotation:
                return {"error": "preserve_rotation=false is not supported yet; use set_object_transform for explicit rotation first"}

            obj_world_point = obj.matrix_world @ Vector(resolved_obj_local)
            reference_world_point = reference_obj.matrix_world @ Vector(resolved_ref_local)
            target_world_point = reference_world_point + resolved_offset
            delta = target_world_point - obj_world_point

            before_location = obj.location.copy()
            matrix = obj.matrix_world.copy()
            matrix.translation += delta
            obj.matrix_world = matrix
            aligned_world_point = obj.matrix_world @ Vector(resolved_obj_local)

            return {
                "success": True,
                "object": obj.name,
                "reference": reference_obj.name,
                "obj_local_point": list(resolved_obj_local),
                "reference_local_point": list(resolved_ref_local),
                "offset": [round(value, 6) for value in resolved_offset],
                "delta": [round(value, 6) for value in delta],
                "old_location": [round(value, 6) for value in before_location],
                "new_location": [round(value, 6) for value in obj.location],
                "target_world_point": [round(value, 6) for value in target_world_point],
                "aligned_world_point": [round(value, 6) for value in aligned_world_point],
                "preserve_rotation": resolved_preserve_rotation,
                "next_safe_action": "validate_object_clearance or inspect with get_object_info after attachment alignment",
            }
        except Exception as e:
            return {"error": f"Failed to align object attachment points: {str(e)}"}

    def rename_object(self, name, new_name):
        """Rename an object in the scene"""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}
            if bpy.data.objects.get(new_name):
                return {"error": f"An object named '{new_name}' already exists"}

            old_name = obj.name
            obj.name = new_name
            # Also rename the data block if it matches the old name
            if obj.data and obj.data.name == old_name:
                obj.data.name = new_name

            return {
                "success": True,
                "old_name": old_name,
                "new_name": obj.name,
            }
        except Exception as e:
            return {"error": f"Failed to rename object: {str(e)}"}

    def duplicate_object(self, name, new_name=None, linked=False):
        """Duplicate an object. linked=True shares mesh data."""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}

            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.duplicate(linked=linked)

            dup = bpy.context.active_object
            if new_name:
                dup.name = new_name
                if dup.data and not linked:
                    dup.data.name = new_name

            return {
                "success": True,
                "original": name,
                "duplicate": dup.name,
                "linked": linked,
            }
        except Exception as e:
            return {"error": f"Failed to duplicate object: {str(e)}"}

    def _pattern_positions(
        self,
        count,
        layout="LINE",
        center=None,
        spacing=None,
        axis="X",
        radius=1.0,
        plane="XY",
        columns=None,
        row_spacing=None,
        start_angle_degrees=0.0,
    ):
        if count < 1:
            raise ValueError("count must be at least 1")

        def vector3(value, fallback, label):
            raw = fallback if value is None else value
            if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                raise ValueError(f"{label} must be [x,y,z]")
            return Vector((float(raw[0]), float(raw[1]), float(raw[2])))

        resolved_center = vector3(center, (0.0, 0.0, 0.0), "center")
        resolved_layout = str(layout or "LINE").upper()
        resolved_axis = str(axis or "X").upper()
        resolved_plane = str(plane or "XY").upper()

        axis_vectors = {
            "X": Vector((1.0, 0.0, 0.0)),
            "Y": Vector((0.0, 1.0, 0.0)),
            "Z": Vector((0.0, 0.0, 1.0)),
        }
        plane_axes = {
            "XY": (Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0))),
            "XZ": (Vector((1.0, 0.0, 0.0)), Vector((0.0, 0.0, 1.0))),
            "YZ": (Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, 1.0))),
        }

        if resolved_layout == "LINE":
            if isinstance(spacing, (list, tuple)):
                step = vector3(spacing, (1.0, 0.0, 0.0), "spacing")
            else:
                if resolved_axis not in axis_vectors:
                    raise ValueError("axis must be X, Y, or Z")
                step = axis_vectors[resolved_axis] * float(1.0 if spacing is None else spacing)
            midpoint = (count - 1) / 2.0
            return [resolved_center + step * (index - midpoint) for index in range(count)]

        if resolved_layout == "CIRCLE":
            if resolved_plane not in plane_axes:
                raise ValueError("plane must be XY, XZ, or YZ")
            basis_a, basis_b = plane_axes[resolved_plane]
            resolved_radius = max(float(radius), 0.0)
            start_angle = math.radians(float(start_angle_degrees or 0.0))
            angle_step = (math.tau / count) if count > 0 else 0.0
            return [
                resolved_center
                + basis_a * (math.cos(start_angle + angle_step * index) * resolved_radius)
                + basis_b * (math.sin(start_angle + angle_step * index) * resolved_radius)
                for index in range(count)
            ]

        if resolved_layout == "GRID":
            if resolved_plane not in plane_axes:
                raise ValueError("plane must be XY, XZ, or YZ")
            basis_a, basis_b = plane_axes[resolved_plane]
            resolved_columns = int(columns or math.ceil(math.sqrt(count)))
            if resolved_columns < 1:
                raise ValueError("columns must be at least 1")
            if isinstance(spacing, (list, tuple)):
                step_a = float(spacing[0])
                step_b = float(spacing[1] if len(spacing) > 1 else spacing[0])
            else:
                step_a = float(1.0 if spacing is None else spacing)
                step_b = float(row_spacing if row_spacing is not None else step_a)
            rows = math.ceil(count / resolved_columns)
            x_midpoint = (resolved_columns - 1) / 2.0
            y_midpoint = (rows - 1) / 2.0
            positions = []
            for index in range(count):
                column = index % resolved_columns
                row = index // resolved_columns
                positions.append(
                    resolved_center
                    + basis_a * ((column - x_midpoint) * step_a)
                    + basis_b * ((row - y_midpoint) * step_b)
                )
            return positions

        raise ValueError("layout must be LINE, CIRCLE, or GRID")

    def _align_object_bottom_to_z(self, obj, target_z):
        if target_z is None:
            return
        if not hasattr(obj, "bound_box") or not obj.bound_box:
            obj.location.z = float(target_z)
            return
        bottom_z = min((obj.matrix_world @ Vector(corner)).z for corner in obj.bound_box)
        obj.location.z += float(target_z) - bottom_z

    def _move_object_to_pattern_position(self, obj, position, align_bottom_to_z=None):
        matrix = obj.matrix_world.copy()
        matrix.translation = Vector(position)
        obj.matrix_world = matrix
        self._align_object_bottom_to_z(obj, align_bottom_to_z)

    def arrange_objects(
        self,
        names,
        layout="LINE",
        center=None,
        spacing=None,
        axis="X",
        radius=1.0,
        plane="XY",
        columns=None,
        row_spacing=None,
        start_angle_degrees=0.0,
        align_bottom_to_z=None,
    ):
        """Arrange existing objects into a line, circle, or grid without Python loops."""
        try:
            if not isinstance(names, (list, tuple)) or not names:
                return {"error": "names must be a non-empty list"}
            objects = []
            for name in names:
                obj = bpy.data.objects.get(str(name))
                if not obj:
                    return {"error": f"Object not found: {name}"}
                objects.append(obj)

            positions = self._pattern_positions(
                len(objects),
                layout=layout,
                center=center,
                spacing=spacing,
                axis=axis,
                radius=radius,
                plane=plane,
                columns=columns,
                row_spacing=row_spacing,
                start_angle_degrees=start_angle_degrees,
            )

            arranged = []
            for obj, position in zip(objects, positions):
                self._move_object_to_pattern_position(obj, position, align_bottom_to_z)
                arranged.append({
                    "name": obj.name,
                    "location": [round(value, 6) for value in obj.location],
                })

            return {
                "success": True,
                "layout": str(layout or "LINE").upper(),
                "arranged_count": len(arranged),
                "objects": arranged,
                "next_safe_action": "validate_object_clearance or inspect with get_all_object_info after arranging objects",
            }
        except Exception as e:
            return {"error": f"Failed to arrange objects: {str(e)}"}

    def duplicate_object_pattern(
        self,
        name,
        count=1,
        layout="LINE",
        name_prefix=None,
        linked=False,
        include_source=False,
        center=None,
        spacing=None,
        axis="X",
        radius=1.0,
        plane="XY",
        columns=None,
        row_spacing=None,
        start_angle_degrees=0.0,
        align_bottom_to_z=None,
    ):
        """Duplicate one object into a repeated line, circle, or grid pattern."""
        try:
            source = bpy.data.objects.get(name)
            if not source:
                return {"error": f"Object not found: {name}"}
            resolved_count = int(count or 1)
            if resolved_count < 1 or resolved_count > 100:
                return {"error": "count must be between 1 and 100"}

            def coerce_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() in {"1", "true", "yes", "on"}
                return bool(value)

            resolved_linked = coerce_bool(linked, False)
            resolved_include_source = coerce_bool(include_source, False)
            objects_to_place = [source] if resolved_include_source else []
            copies_to_create = resolved_count - len(objects_to_place)
            if copies_to_create < 0:
                copies_to_create = 0

            collection = source.users_collection[0] if source.users_collection else bpy.context.collection
            prefix = str(name_prefix or source.name)
            created = []
            for index in range(copies_to_create):
                new_obj = source.copy()
                if source.data and not resolved_linked:
                    new_obj.data = source.data.copy()
                new_obj.name = f"{prefix}_{index + 1:02d}" if not resolved_include_source else f"{prefix}_{index + 2:02d}"
                if new_obj.data and not resolved_linked:
                    new_obj.data.name = new_obj.name
                new_obj.animation_data_clear()
                collection.objects.link(new_obj)
                objects_to_place.append(new_obj)
                created.append(new_obj.name)

            positions = self._pattern_positions(
                len(objects_to_place),
                layout=layout,
                center=center,
                spacing=spacing,
                axis=axis,
                radius=radius,
                plane=plane,
                columns=columns,
                row_spacing=row_spacing,
                start_angle_degrees=start_angle_degrees,
            )

            placed = []
            for obj, position in zip(objects_to_place, positions):
                self._move_object_to_pattern_position(obj, position, align_bottom_to_z)
                placed.append({
                    "name": obj.name,
                    "location": [round(value, 6) for value in obj.location],
                })

            return {
                "success": True,
                "source": source.name,
                "layout": str(layout or "LINE").upper(),
                "linked": resolved_linked,
                "include_source": resolved_include_source,
                "created": created,
                "placed": placed,
                "next_safe_action": "validate_object_clearance or inspect with get_all_object_info after duplicating the pattern",
            }
        except Exception as e:
            return {"error": f"Failed to duplicate object pattern: {str(e)}"}

    def join_objects(self, names):
        """Join multiple objects into one. First name becomes the active (target) object."""
        try:
            if not names or len(names) < 2:
                return {"error": "Provide at least 2 object names to join"}

            # Validate all names exist
            objects = []
            for n in names:
                obj = bpy.data.objects.get(n)
                if not obj:
                    return {"error": f"Object not found: {n}"}
                if obj.type != 'MESH':
                    return {"error": f"Object '{n}' is type '{obj.type}', only MESH objects can be joined"}
                objects.append(obj)

            bpy.ops.object.select_all(action='DESELECT')
            for obj in objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = objects[0]
            bpy.ops.object.join()

            result_obj = bpy.context.active_object
            return {
                "success": True,
                "result_object": result_obj.name,
                "joined_count": len(names),
                "vertex_count": len(result_obj.data.vertices) if result_obj.data else 0,
            }
        except Exception as e:
            return {"error": f"Failed to join objects: {str(e)}"}

    # ---------- Phase 1B: Modifier & Mesh Tools ----------

    def add_empty_object(
        self,
        name=None,
        location=None,
        rotation=None,
        scale=None,
        display_type="PLAIN_AXES",
        display_size=1.0,
        collection_name=None,
        parent_name=None,
        replace_existing=False,
    ):
        """Create a root/control Empty object without arbitrary Python."""
        temp_obj = None
        created_collection = None
        try:
            def vector3(value, fallback, label):
                raw = fallback if value is None else value
                if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                    raise ValueError(f"{label} must be [x,y,z]")
                return tuple(float(component) for component in raw[:3])

            def positive_float(value, label, minimum=0.001, maximum=10000.0):
                number = float(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            def coerce_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() in {"1", "true", "yes", "on"}
                return bool(value)

            empty_name = str(name or "Empty").strip()
            if not empty_name:
                return {"error": "name must not be empty"}

            resolved_replace_existing = coerce_bool(replace_existing)
            existing = bpy.data.objects.get(empty_name)
            if existing and not resolved_replace_existing:
                return {"error": f"Object already exists: {empty_name}. Set replace_existing=true to rebuild it."}

            display_key = str(display_type or "PLAIN_AXES").upper().replace("-", "_").replace(" ", "_")
            aliases = {
                "AXES": "PLAIN_AXES",
                "PLAIN": "PLAIN_AXES",
                "ARROW": "SINGLE_ARROW",
                "SINGLE": "SINGLE_ARROW",
            }
            display_key = aliases.get(display_key, display_key)
            allowed_display_types = {"PLAIN_AXES", "ARROWS", "SINGLE_ARROW", "CIRCLE", "CUBE", "SPHERE", "CONE"}
            if display_key not in allowed_display_types:
                return {
                    "error": "display_type must be one of: "
                    + ", ".join(sorted(allowed_display_types))
                }

            target_collection = bpy.context.collection
            if collection_name:
                target_collection = bpy.data.collections.get(collection_name)
                if not target_collection:
                    created_collection = bpy.data.collections.new(collection_name)
                    bpy.context.scene.collection.children.link(created_collection)
                    target_collection = created_collection

            parent_obj = None
            if parent_name:
                parent_obj = bpy.data.objects.get(parent_name)
                if not parent_obj:
                    return {"error": f"Parent object not found: {parent_name}"}

            resolved_location = vector3(location, (0.0, 0.0, 0.0), "location")
            resolved_rotation = tuple(math.radians(value) for value in vector3(rotation, (0.0, 0.0, 0.0), "rotation"))
            resolved_scale = vector3(scale, (1.0, 1.0, 1.0), "scale")
            resolved_display_size = positive_float(display_size, "display_size")

            obj = bpy.data.objects.new(f"__ViperMesh_Empty_Temp_{int(time.time() * 1000)}", None)
            temp_obj = obj
            obj.empty_display_type = display_key
            obj.empty_display_size = resolved_display_size
            obj.location = resolved_location
            obj.rotation_euler = resolved_rotation
            obj.scale = resolved_scale

            target_collection.objects.link(obj)

            if parent_obj:
                world_matrix = obj.matrix_world.copy()
                obj.parent = parent_obj
                obj.matrix_world = world_matrix

            if existing and resolved_replace_existing:
                constraint_users = []
                for other in bpy.data.objects:
                    for constraint in other.constraints:
                        if getattr(constraint, "target", None) == existing:
                            constraint_users.append(f"{other.name}:{constraint.name}")
                if constraint_users:
                    if temp_obj and temp_obj.name in bpy.data.objects:
                        bpy.data.objects.remove(temp_obj, do_unlink=True)
                        temp_obj = None
                    if created_collection and created_collection.name in bpy.data.collections and not created_collection.objects:
                        bpy.data.collections.remove(created_collection)
                    return {
                        "error": "Cannot replace existing Empty while constraints target it: "
                        + ", ".join(constraint_users[:10])
                    }

                for key in existing.keys():
                    obj[key] = existing[key]

                rebound_children = []
                for child in list(existing.children):
                    child_world = child.matrix_world.copy()
                    child_parent_type = child.parent_type
                    child_parent_bone = getattr(child, "parent_bone", "")
                    child.parent = obj
                    child.parent_type = child_parent_type
                    if child_parent_bone:
                        child.parent_bone = child_parent_bone
                    child.matrix_world = child_world
                    rebound_children.append(child.name)

                bpy.data.objects.remove(existing, do_unlink=True)
            else:
                rebound_children = []

            obj.name = empty_name
            temp_obj = None

            return {
                "success": True,
                "object": obj.name,
                "type": obj.type,
                "display_type": obj.empty_display_type,
                "display_size": obj.empty_display_size,
                "collection": target_collection.name if target_collection else None,
                "parent": obj.parent.name if obj.parent else None,
                "location": list(obj.location),
                "rotation_degrees": [round(math.degrees(value), 3) for value in obj.rotation_euler],
                "scale": list(obj.scale),
                "rebound_children": rebound_children,
                "next_safe_action": "parent_set child objects to this root empty or set_object_transform to move the whole assembly",
            }
        except Exception as e:
            if temp_obj and temp_obj.name in bpy.data.objects:
                bpy.data.objects.remove(temp_obj, do_unlink=True)
            if created_collection and created_collection.name in bpy.data.collections and not created_collection.objects:
                bpy.data.collections.remove(created_collection)
            return {"error": f"Failed to add empty object: {str(e)}"}

    def set_empty_properties(
        self,
        name,
        display_type=None,
        display_size=None,
        show_name=None,
        show_in_front=None,
    ):
        """Tune an existing Empty root/control display without arbitrary Python."""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}
            if obj.type != "EMPTY":
                return {"error": f"Object '{name}' is type '{obj.type}', expected EMPTY"}

            def coerce_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() in {"1", "true", "yes", "on"}
                return bool(value)

            allowed_display_types = {"PLAIN_AXES", "ARROWS", "SINGLE_ARROW", "CIRCLE", "CUBE", "SPHERE", "CONE"}
            next_display_type = obj.empty_display_type
            if display_type is not None:
                display_key = str(display_type).upper().replace("-", "_").replace(" ", "_")
                aliases = {
                    "AXES": "PLAIN_AXES",
                    "PLAIN": "PLAIN_AXES",
                    "ARROW": "SINGLE_ARROW",
                    "SINGLE": "SINGLE_ARROW",
                }
                display_key = aliases.get(display_key, display_key)
                if display_key not in allowed_display_types:
                    return {
                        "error": "display_type must be one of: "
                        + ", ".join(sorted(allowed_display_types))
                    }
                next_display_type = display_key

            next_display_size = obj.empty_display_size
            if display_size is not None:
                next_display_size = float(display_size)
                if next_display_size < 0.001 or next_display_size > 10000.0:
                    return {"error": "display_size must be between 0.001 and 10000.0"}

            next_show_name = obj.show_name if show_name is None else coerce_bool(show_name)
            next_show_in_front = obj.show_in_front if show_in_front is None else coerce_bool(show_in_front)

            obj.empty_display_type = next_display_type
            obj.empty_display_size = next_display_size
            obj.show_name = next_show_name
            obj.show_in_front = next_show_in_front

            return {
                "success": True,
                "object": obj.name,
                "type": obj.type,
                "display_type": obj.empty_display_type,
                "display_size": obj.empty_display_size,
                "show_name": obj.show_name,
                "show_in_front": obj.show_in_front,
                "next_safe_action": "set_object_transform to reposition the root control or parent_set additional children",
            }
        except Exception as e:
            return {"error": f"Failed to set empty properties: {str(e)}"}

    def add_text_object(
        self,
        text,
        name=None,
        location=None,
        rotation=None,
        scale=None,
        size=1.0,
        align_x="CENTER",
        align_y="CENTER",
        extrude=0.0,
        bevel_depth=0.0,
        bevel_resolution=0,
        font_path=None,
        material_name=None,
        collection_name=None,
        replace_existing=False,
        convert_to_mesh=False,
    ):
        """Create a bounded 3D text object without arbitrary Python."""
        temp_obj = None
        created_collection = None
        try:
            body = str(text or "")
            if not body.strip():
                return {"error": "text must not be empty"}
            if len(body) > 1000:
                return {"error": "text is too long; keep add_text_object text under 1000 characters"}

            def vector3(value, fallback, label):
                raw = fallback if value is None else value
                if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                    raise ValueError(f"{label} must be [x,y,z]")
                return tuple(float(component) for component in raw[:3])

            def bounded_float(value, label, minimum, maximum):
                number = float(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            def bounded_int(value, label, minimum, maximum):
                number = int(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            text_name = str(name or "Text").strip()
            if not text_name:
                return {"error": "name must not be empty"}

            existing = bpy.data.objects.get(text_name)
            if existing and not replace_existing:
                return {"error": f"Object already exists: {text_name}. Set replace_existing=true to rebuild it."}

            resolved_font_path = None
            if font_path:
                resolved_font_path = bpy.path.abspath(str(font_path))
                if not os.path.exists(resolved_font_path):
                    return {"error": f"Font file not found: {font_path}"}
                if not resolved_font_path.lower().endswith((".ttf", ".otf")):
                    return {"error": "font_path must point to a .ttf or .otf file"}

            target_collection = None
            if collection_name:
                target_collection = bpy.data.collections.get(collection_name)
            else:
                target_collection = bpy.context.collection

            mat = None
            if material_name:
                mat = bpy.data.materials.get(material_name)
                if not mat:
                    return {"error": f"Material not found: {material_name}"}

            horizontal = str(align_x or "CENTER").upper()
            vertical = str(align_y or "CENTER").upper()
            if horizontal not in {"LEFT", "CENTER", "RIGHT", "JUSTIFY", "FLUSH"}:
                return {"error": "align_x must be LEFT, CENTER, RIGHT, JUSTIFY, or FLUSH"}
            if vertical not in {"TOP", "TOP_BASELINE", "CENTER", "BOTTOM_BASELINE", "BOTTOM"}:
                return {"error": "align_y must be TOP, TOP_BASELINE, CENTER, BOTTOM_BASELINE, or BOTTOM"}

            resolved_location = vector3(location, (0.0, 0.0, 0.0), "location")
            resolved_rotation = tuple(math.radians(value) for value in vector3(rotation, (0.0, 0.0, 0.0), "rotation"))
            resolved_scale = vector3(scale, (1.0, 1.0, 1.0), "scale")
            resolved_size = bounded_float(size, "size", 0.001, 1000.0)
            resolved_extrude = bounded_float(extrude, "extrude", 0.0, 1000.0)
            resolved_bevel_depth = bounded_float(bevel_depth, "bevel_depth", 0.0, 100.0)
            resolved_bevel_resolution = bounded_int(bevel_resolution, "bevel_resolution", 0, 12)

            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.text_add(location=resolved_location)

            obj = bpy.context.active_object
            if not obj or obj.type != "FONT":
                return {"error": "Text operator completed without an active text object"}

            temp_obj = obj
            temp_name = f"__ViperMesh_Text_Temp_{int(time.time() * 1000)}"
            obj.name = temp_name
            obj.rotation_euler = resolved_rotation
            obj.data.name = f"{temp_name}_Curve"
            obj.data.body = body
            obj.data.size = resolved_size
            obj.data.align_x = horizontal
            obj.data.align_y = vertical
            obj.data.extrude = resolved_extrude
            obj.data.bevel_depth = resolved_bevel_depth
            obj.data.bevel_resolution = resolved_bevel_resolution
            obj.scale = resolved_scale

            if resolved_font_path:
                loaded_font = bpy.data.fonts.load(resolved_font_path, check_existing=True)
                obj.data.font = loaded_font

            assigned_material = None
            if mat and obj.data:
                obj.data.materials.append(mat)
                assigned_material = mat.name

            object_type = obj.type
            if convert_to_mesh:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.convert(target='MESH')
                obj = bpy.context.active_object
                temp_obj = obj
                obj.name = temp_name
                if obj.data:
                    obj.data.name = f"{temp_name}_Mesh"
                object_type = obj.type

            if collection_name and not target_collection:
                created_collection = bpy.data.collections.new(collection_name)
                bpy.context.scene.collection.children.link(created_collection)
                target_collection = created_collection

            if target_collection and target_collection.name not in {collection.name for collection in obj.users_collection}:
                target_collection.objects.link(obj)
            if target_collection:
                for collection in list(obj.users_collection):
                    if collection != target_collection and len(obj.users_collection) > 1:
                        collection.objects.unlink(obj)

            if existing and replace_existing:
                bpy.data.objects.remove(existing, do_unlink=True)

            obj.name = text_name
            if obj.data:
                obj.data.name = f"{text_name}_Mesh" if obj.type == "MESH" else f"{text_name}_Curve"
            temp_obj = None

            return {
                "success": True,
                "object": obj.name,
                "type": object_type,
                "text": body,
                "collection": target_collection.name if target_collection else None,
                "material": assigned_material,
                "location": list(obj.location),
                "rotation_degrees": [round(math.degrees(value), 3) for value in obj.rotation_euler],
                "scale": list(obj.scale),
                "size": resolved_size,
                "align_x": horizontal,
                "align_y": vertical,
                "extrude": resolved_extrude,
                "bevel_depth": resolved_bevel_depth,
                "convert_to_mesh": bool(convert_to_mesh),
                "next_safe_action": "assign_material, set_object_transform, or add_modifier if converted to mesh",
            }
        except Exception as e:
            if temp_obj and temp_obj.name in bpy.data.objects:
                bpy.data.objects.remove(temp_obj, do_unlink=True)
            if created_collection and created_collection.name in bpy.data.collections and not created_collection.objects:
                bpy.data.collections.remove(created_collection)
            return {"error": f"Failed to add text object: {str(e)}"}

    def add_mesh_primitive(
        self,
        primitive_type,
        name=None,
        location=None,
        rotation=None,
        scale=None,
        size=2.0,
        radius=1.0,
        radius1=1.0,
        radius2=0.0,
        depth=2.0,
        vertices=32,
        segments=32,
        ring_count=16,
        major_radius=1.0,
        minor_radius=0.25,
        major_segments=48,
        minor_segments=12,
        collection_name=None,
        material_name=None,
        replace_existing=False,
        shade_smooth=False,
        validate=True,
    ):
        """Create a bounded common mesh primitive without arbitrary Python."""
        try:
            primitive_key = str(primitive_type or "").lower().replace("-", "_")
            aliases = {
                "box": "cube",
                "uvsphere": "uv_sphere",
                "sphere": "uv_sphere",
                "cylinder": "cylinder",
                "cone": "cone",
                "plane": "plane",
                "torus": "torus",
                "cube": "cube",
            }
            primitive_key = aliases.get(primitive_key, primitive_key)
            allowed = {"cube", "uv_sphere", "cylinder", "cone", "plane", "torus"}
            if primitive_key not in allowed:
                return {"error": f"Unsupported primitive_type: {primitive_type}. Use one of: {', '.join(sorted(allowed))}"}

            def vector3(value, fallback, label):
                raw = fallback if value is None else value
                if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                    raise ValueError(f"{label} must be [x,y,z]")
                return tuple(float(component) for component in raw[:3])

            def positive_float(value, label, minimum=0.0001, maximum=10000.0):
                number = float(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            def nonnegative_float(value, label, maximum=10000.0):
                number = float(value)
                if number < 0.0 or number > maximum:
                    raise ValueError(f"{label} must be between 0.0 and {maximum}")
                return number

            def bounded_int(value, label, minimum, maximum):
                number = int(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            obj_name = str(name or primitive_key.title().replace("_", ""))
            if not obj_name:
                return {"error": "name must not be empty"}

            existing = bpy.data.objects.get(obj_name)
            if existing and not replace_existing:
                return {"error": f"Object already exists: {obj_name}. Set replace_existing=true to rebuild it."}

            target_collection = bpy.context.collection
            if collection_name:
                target_collection = bpy.data.collections.get(collection_name)
                if not target_collection:
                    target_collection = bpy.data.collections.new(collection_name)
                    bpy.context.scene.collection.children.link(target_collection)

            mat = None
            if material_name:
                mat = bpy.data.materials.get(material_name)
                if not mat:
                    return {"error": f"Material not found: {material_name}"}

            resolved_location = vector3(location, (0.0, 0.0, 0.0), "location")
            resolved_rotation = tuple(math.radians(value) for value in vector3(rotation, (0.0, 0.0, 0.0), "rotation"))
            resolved_scale = vector3(scale, (1.0, 1.0, 1.0), "scale")

            if existing and replace_existing:
                bpy.data.objects.remove(existing, do_unlink=True)

            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='OBJECT')
            if primitive_key == "cube":
                bpy.ops.mesh.primitive_cube_add(size=positive_float(size, "size"), location=resolved_location, rotation=resolved_rotation)
            elif primitive_key == "plane":
                bpy.ops.mesh.primitive_plane_add(size=positive_float(size, "size"), location=resolved_location, rotation=resolved_rotation)
            elif primitive_key == "uv_sphere":
                bpy.ops.mesh.primitive_uv_sphere_add(
                    segments=bounded_int(segments, "segments", 3, 256),
                    ring_count=bounded_int(ring_count, "ring_count", 3, 128),
                    radius=positive_float(radius, "radius"),
                    location=resolved_location,
                    rotation=resolved_rotation,
                )
            elif primitive_key == "cylinder":
                bpy.ops.mesh.primitive_cylinder_add(
                    vertices=bounded_int(vertices, "vertices", 3, 256),
                    radius=positive_float(radius, "radius"),
                    depth=positive_float(depth, "depth"),
                    location=resolved_location,
                    rotation=resolved_rotation,
                )
            elif primitive_key == "cone":
                bpy.ops.mesh.primitive_cone_add(
                    vertices=bounded_int(vertices, "vertices", 3, 256),
                    radius1=positive_float(radius1, "radius1"),
                    radius2=nonnegative_float(radius2, "radius2"),
                    depth=positive_float(depth, "depth"),
                    location=resolved_location,
                    rotation=resolved_rotation,
                )
            else:
                bpy.ops.mesh.primitive_torus_add(
                    major_segments=bounded_int(major_segments, "major_segments", 3, 256),
                    minor_segments=bounded_int(minor_segments, "minor_segments", 3, 128),
                    major_radius=positive_float(major_radius, "major_radius"),
                    minor_radius=positive_float(minor_radius, "minor_radius"),
                    location=resolved_location,
                    rotation=resolved_rotation,
                )

            obj = bpy.context.active_object
            if not obj:
                return {"error": "Primitive operator completed without an active object"}
            obj.name = obj_name
            if obj.data:
                obj.data.name = f"{obj_name}_Mesh"
            obj.scale = resolved_scale

            if target_collection and target_collection.name not in {collection.name for collection in obj.users_collection}:
                target_collection.objects.link(obj)
            if target_collection:
                for collection in list(obj.users_collection):
                    if collection != target_collection and len(obj.users_collection) > 1:
                        collection.objects.unlink(obj)

            assigned_material = None
            if mat and obj.data:
                obj.data.materials.append(mat)
                assigned_material = mat.name

            if shade_smooth and obj.data:
                for poly in obj.data.polygons:
                    poly.use_smooth = True

            report = self._mesh_geometry_report(obj, cleanup=bool(validate)) if obj.type == "MESH" else None

            return {
                "success": True,
                "object": obj.name,
                "primitive_type": primitive_key,
                "mesh": obj.data.name if obj.data else None,
                "collection": target_collection.name if target_collection else None,
                "material": assigned_material,
                "location": list(obj.location),
                "rotation_degrees": [round(math.degrees(value), 3) for value in obj.rotation_euler],
                "scale": list(obj.scale),
                "geometry": report,
                "next_safe_action": "validate_mesh_geometry or add_modifier when this primitive needs refinement",
            }
        except Exception as e:
            return {"error": f"Failed to add mesh primitive: {str(e)}"}

    def create_primitive_assembly(
        self,
        name="Primitive_Assembly",
        parts=None,
        location=None,
        rotation=None,
        collection_name=None,
        create_root_empty=True,
        root_display_type="CUBE",
        root_display_size=0.5,
        replace_existing=False,
        validate=True,
    ):
        """Create a grouped local-coordinate assembly from bounded primitive part specs."""
        try:
            def vector3(value, fallback, label):
                raw = fallback if value is None else value
                if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                    raise ValueError(f"{label} must be [x,y,z]")
                return tuple(float(component) for component in raw[:3])

            def positive_float(value, label, minimum=0.0001, maximum=10000.0):
                number = float(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            def nonnegative_float(value, label, maximum=10000.0):
                number = float(value)
                if number < 0.0 or number > maximum:
                    raise ValueError(f"{label} must be between 0.0 and {maximum}")
                return number

            def bounded_int(value, label, minimum, maximum):
                number = int(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            def coerce_part_bool(part, key, fallback=False):
                if not isinstance(part, dict) or key not in part:
                    return fallback
                return bool(part.get(key))

            def primitive_key_for(value):
                key = str(value or "").lower().replace("-", "_")
                aliases = {
                    "box": "cube",
                    "uvsphere": "uv_sphere",
                    "sphere": "uv_sphere",
                    "cylinder": "cylinder",
                    "cone": "cone",
                    "plane": "plane",
                    "torus": "torus",
                    "cube": "cube",
                }
                key = aliases.get(key, key)
                allowed = {"cube", "uv_sphere", "cylinder", "cone", "plane", "torus"}
                if key not in allowed:
                    raise ValueError(f"Unsupported primitive_type: {value}. Use one of: {', '.join(sorted(allowed))}")
                return key

            def rotation_matrix_from_degrees(degrees):
                radians = tuple(math.radians(value) for value in vector3(degrees, (0.0, 0.0, 0.0), "rotation"))
                return (
                    mathutils.Matrix.Rotation(radians[2], 4, "Z")
                    @ mathutils.Matrix.Rotation(radians[1], 4, "Y")
                    @ mathutils.Matrix.Rotation(radians[0], 4, "X")
                )

            assembly_name = str(name or "Primitive_Assembly").strip()
            if not assembly_name:
                return {"error": "name must not be empty"}
            if not isinstance(parts, list) or len(parts) == 0:
                return {"error": "parts must be a non-empty list"}
            if len(parts) > 128:
                return {"error": "parts must contain 128 items or fewer"}

            origin = Vector(vector3(location, (0.0, 0.0, 0.0), "location"))
            root_rotation = rotation_matrix_from_degrees(rotation)

            target_collection = bpy.context.collection
            if collection_name:
                target_collection = bpy.data.collections.get(collection_name)
                if not target_collection:
                    target_collection = bpy.data.collections.new(collection_name)
                    bpy.context.scene.collection.children.link(target_collection)

            root_empty = None
            created_objects = []
            expected_names = []
            validated_parts = []
            seen_names = set()
            for index, part in enumerate(parts):
                if not isinstance(part, dict):
                    return {"error": f"parts[{index}] must be an object"}
                primitive_key = primitive_key_for(part.get("primitive_type"))
                part_name = str(part.get("name") or f"{assembly_name}_Part_{index + 1:02d}").strip()
                if not part_name:
                    return {"error": f"parts[{index}].name must not be empty"}
                if part_name == assembly_name:
                    return {"error": f"parts[{index}].name must not match assembly name: {assembly_name}"}
                if part_name in seen_names:
                    return {"error": f"Duplicate part name: {part_name}"}
                seen_names.add(part_name)
                expected_names.append(part_name)
                material_name = part.get("material_name")
                material = bpy.data.materials.get(str(material_name)) if material_name else None
                if material_name and not material:
                    return {"error": f"Material not found for parts[{index}]: {material_name}"}

                primitive_options = {}
                if primitive_key in {"cube", "plane"}:
                    primitive_options["size"] = positive_float(part.get("size", 1.0), f"parts[{index}].size")
                elif primitive_key == "uv_sphere":
                    primitive_options["segments"] = bounded_int(part.get("segments", 32), f"parts[{index}].segments", 3, 256)
                    primitive_options["ring_count"] = bounded_int(part.get("ring_count", 16), f"parts[{index}].ring_count", 3, 128)
                    primitive_options["radius"] = positive_float(part.get("radius", 1.0), f"parts[{index}].radius")
                elif primitive_key == "cylinder":
                    primitive_options["vertices"] = bounded_int(part.get("vertices", 32), f"parts[{index}].vertices", 3, 256)
                    primitive_options["radius"] = positive_float(part.get("radius", 1.0), f"parts[{index}].radius")
                    primitive_options["depth"] = positive_float(part.get("depth", 2.0), f"parts[{index}].depth")
                elif primitive_key == "cone":
                    primitive_options["vertices"] = bounded_int(part.get("vertices", 32), f"parts[{index}].vertices", 3, 256)
                    primitive_options["radius1"] = positive_float(part.get("radius1", 1.0), f"parts[{index}].radius1")
                    primitive_options["radius2"] = nonnegative_float(part.get("radius2", 0.0), f"parts[{index}].radius2")
                    primitive_options["depth"] = positive_float(part.get("depth", 2.0), f"parts[{index}].depth")
                else:
                    primitive_options["major_segments"] = bounded_int(part.get("major_segments", 48), f"parts[{index}].major_segments", 3, 256)
                    primitive_options["minor_segments"] = bounded_int(part.get("minor_segments", 12), f"parts[{index}].minor_segments", 3, 128)
                    primitive_options["major_radius"] = positive_float(part.get("major_radius", 1.0), f"parts[{index}].major_radius")
                    primitive_options["minor_radius"] = positive_float(part.get("minor_radius", 0.25), f"parts[{index}].minor_radius")

                validated_parts.append({
                    "primitive_key": primitive_key,
                    "name": part_name,
                    "local_location": Vector(vector3(part.get("local_location"), (0.0, 0.0, 0.0), f"parts[{index}].local_location")),
                    "local_rotation": rotation_matrix_from_degrees(part.get("local_rotation")),
                    "scale": vector3(part.get("scale"), (1.0, 1.0, 1.0), f"parts[{index}].scale"),
                    "material": material,
                    "shade_smooth": coerce_part_bool(part, "shade_smooth", False),
                    "options": primitive_options,
                })

            if create_root_empty:
                expected_names.append(assembly_name)

            existing_names = [object_name for object_name in expected_names if bpy.data.objects.get(object_name)]
            if existing_names and not replace_existing:
                return {"error": f"Objects already exist: {', '.join(existing_names)}. Set replace_existing=true to rebuild them."}
            if replace_existing:
                for object_name in existing_names:
                    obj = bpy.data.objects.get(object_name)
                    if obj:
                        bpy.data.objects.remove(obj, do_unlink=True)

            if create_root_empty:
                root_empty = bpy.data.objects.new(assembly_name, None)
                root_empty.empty_display_type = str(root_display_type or "CUBE").upper()
                root_empty.empty_display_size = positive_float(root_display_size, "root_display_size", 0.001, 1000.0)
                root_empty.location = origin
                root_empty.rotation_euler = root_rotation.to_euler()
                target_collection.objects.link(root_empty)

            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='OBJECT')

            for spec in validated_parts:
                primitive_key = spec["primitive_key"]
                part_name = spec["name"]
                local_location = spec["local_location"]
                local_rotation = spec["local_rotation"]
                world_location = origin + (root_rotation @ local_location)
                world_rotation = (root_rotation @ local_rotation).to_euler()

                if primitive_key == "cube":
                    bpy.ops.mesh.primitive_cube_add(
                        size=spec["options"]["size"],
                        location=world_location,
                        rotation=world_rotation,
                    )
                elif primitive_key == "plane":
                    bpy.ops.mesh.primitive_plane_add(
                        size=spec["options"]["size"],
                        location=world_location,
                        rotation=world_rotation,
                    )
                elif primitive_key == "uv_sphere":
                    bpy.ops.mesh.primitive_uv_sphere_add(
                        segments=spec["options"]["segments"],
                        ring_count=spec["options"]["ring_count"],
                        radius=spec["options"]["radius"],
                        location=world_location,
                        rotation=world_rotation,
                    )
                elif primitive_key == "cylinder":
                    bpy.ops.mesh.primitive_cylinder_add(
                        vertices=spec["options"]["vertices"],
                        radius=spec["options"]["radius"],
                        depth=spec["options"]["depth"],
                        location=world_location,
                        rotation=world_rotation,
                    )
                elif primitive_key == "cone":
                    bpy.ops.mesh.primitive_cone_add(
                        vertices=spec["options"]["vertices"],
                        radius1=spec["options"]["radius1"],
                        radius2=spec["options"]["radius2"],
                        depth=spec["options"]["depth"],
                        location=world_location,
                        rotation=world_rotation,
                    )
                else:
                    bpy.ops.mesh.primitive_torus_add(
                        major_segments=spec["options"]["major_segments"],
                        minor_segments=spec["options"]["minor_segments"],
                        major_radius=spec["options"]["major_radius"],
                        minor_radius=spec["options"]["minor_radius"],
                        location=world_location,
                        rotation=world_rotation,
                    )

                obj = bpy.context.active_object
                if not obj:
                    return {"error": f"Primitive operator completed without an active object for {part_name}"}
                obj.name = part_name
                if obj.data:
                    obj.data.name = f"{part_name}_Mesh"

                obj.scale = spec["scale"]

                assigned_material = None
                if spec["material"]:
                    obj.data.materials.append(spec["material"])
                    assigned_material = spec["material"].name

                if spec["shade_smooth"] and obj.data:
                    for poly in obj.data.polygons:
                        poly.use_smooth = True

                if target_collection and target_collection.name not in {collection.name for collection in obj.users_collection}:
                    target_collection.objects.link(obj)
                if target_collection:
                    for collection in list(obj.users_collection):
                        if collection != target_collection and len(obj.users_collection) > 1:
                            collection.objects.unlink(obj)

                if root_empty:
                    obj.parent = root_empty
                    obj.matrix_parent_inverse = root_empty.matrix_world.inverted()

                report = self._mesh_geometry_report(obj, cleanup=bool(validate)) if obj.type == "MESH" else None
                created_objects.append({
                    "name": obj.name,
                    "primitive_type": primitive_key,
                    "material": assigned_material,
                    "local_location": list(local_location),
                    "location": [round(float(value), 6) for value in obj.location],
                    "rotation_degrees": [round(math.degrees(value), 3) for value in obj.rotation_euler],
                    "scale": list(obj.scale),
                    "parent": root_empty.name if root_empty else None,
                    "geometry": report,
                })

            return {
                "success": True,
                "assembly": assembly_name,
                "root_empty": root_empty.name if root_empty else None,
                "objects": created_objects,
                "part_count": len(created_objects),
                "collection": target_collection.name if target_collection else None,
                "next_safe_action": "run inspect_scene_grounding and inspect_spatial_relations to verify the assembled object family",
            }
        except Exception as e:
            return {"error": f"Failed to create primitive assembly: {str(e)}"}

    def create_parametric_staircase(
        self,
        name="Parametric_Staircase",
        step_count=8,
        step_width=2.0,
        step_depth=0.35,
        step_height=0.18,
        location=None,
        rotation=None,
        collection_name=None,
        material_name=None,
        replace_existing=False,
        shade_smooth=False,
        validate=True,
    ):
        """Create a bounded hard-surface staircase mesh from width, depth, height, and step count."""
        try:
            def vector3(value, fallback, label):
                raw = fallback if value is None else value
                if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                    raise ValueError(f"{label} must be [x,y,z]")
                return tuple(float(component) for component in raw[:3])

            def positive_float(value, label, minimum=0.0001, maximum=10000.0):
                number = float(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            def bounded_int(value, label, minimum, maximum):
                number = int(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            obj_name = str(name or "Parametric_Staircase").strip()
            if not obj_name:
                return {"error": "name must not be empty"}

            resolved_step_count = bounded_int(step_count, "step_count", 1, 128)
            resolved_width = positive_float(step_width, "step_width")
            resolved_depth = positive_float(step_depth, "step_depth")
            resolved_height = positive_float(step_height, "step_height")
            resolved_location = vector3(location, (0.0, 0.0, 0.0), "location")
            resolved_rotation = tuple(math.radians(value) for value in vector3(rotation, (0.0, 0.0, 0.0), "rotation"))

            existing = bpy.data.objects.get(obj_name)
            if existing and not replace_existing:
                return {"error": f"Object already exists: {obj_name}. Set replace_existing=true to rebuild it."}

            target_collection = bpy.context.collection
            if collection_name:
                target_collection = bpy.data.collections.get(collection_name)
                if not target_collection:
                    target_collection = bpy.data.collections.new(collection_name)
                    bpy.context.scene.collection.children.link(target_collection)

            mat = None
            if material_name:
                mat = bpy.data.materials.get(material_name)
                if not mat:
                    return {"error": f"Material not found: {material_name}"}

            total_depth = resolved_depth * resolved_step_count
            total_height = resolved_height * resolved_step_count
            half_width = resolved_width * 0.5
            profile = [(0.0, 0.0), (total_depth, 0.0), (total_depth, total_height)]
            for index in range(resolved_step_count - 1, -1, -1):
                profile.append((index * resolved_depth, (index + 1) * resolved_height))
                if index > 0:
                    profile.append((index * resolved_depth, index * resolved_height))

            vertices = []
            for x in (-half_width, half_width):
                for y, z in profile:
                    vertices.append((x, y, z))

            count = len(profile)
            left_face = tuple(range(count - 1, -1, -1))
            right_face = tuple(range(count, count * 2))
            faces = [left_face, right_face]
            for index in range(count):
                next_index = (index + 1) % count
                faces.append((index, next_index, next_index + count, index + count))

            if existing and replace_existing:
                bpy.data.objects.remove(existing, do_unlink=True)

            mesh = bpy.data.meshes.new(f"{obj_name}_Mesh")
            mesh.from_pydata(vertices, [], faces)
            mesh.update(calc_edges=True)
            obj = bpy.data.objects.new(obj_name, mesh)
            obj.location = resolved_location
            obj.rotation_euler = resolved_rotation
            target_collection.objects.link(obj)

            assigned_material = None
            if mat:
                obj.data.materials.append(mat)
                assigned_material = mat.name

            if shade_smooth:
                for poly in obj.data.polygons:
                    poly.use_smooth = True

            report = self._mesh_geometry_report(obj, cleanup=bool(validate))

            return {
                "success": True,
                "object": obj.name,
                "mesh": mesh.name,
                "step_count": resolved_step_count,
                "step_width": resolved_width,
                "step_depth": resolved_depth,
                "step_height": resolved_height,
                "total_depth": total_depth,
                "total_height": total_height,
                "collection": target_collection.name if target_collection else None,
                "material": assigned_material,
                "location": list(obj.location),
                "rotation_degrees": [round(math.degrees(value), 3) for value in obj.rotation_euler],
                "shade_smooth": bool(shade_smooth),
                "geometry": report,
                "next_safe_action": "validate_mesh_geometry before bevels, railings, booleans, or export",
            }
        except Exception as e:
            return {"error": f"Failed to create parametric staircase: {str(e)}"}

    def create_room_shell(
        self,
        name="Room_Shell",
        width=4.0,
        depth=5.0,
        height=2.8,
        wall_thickness=0.2,
        floor_thickness=0.12,
        location=None,
        collection_name=None,
        wall_material_name=None,
        floor_material_name=None,
        ceiling_material_name=None,
        include_ceiling=True,
        open_front=True,
        replace_existing=False,
        validate=True,
    ):
        """Create a bounded room shell with real-thickness floor, walls, and optional ceiling."""
        try:
            def vector3(value, fallback, label):
                raw = fallback if value is None else value
                if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                    raise ValueError(f"{label} must be [x,y,z]")
                return tuple(float(component) for component in raw[:3])

            def positive_float(value, label, minimum=0.0001, maximum=10000.0):
                number = float(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            shell_name = str(name or "Room_Shell").strip()
            if not shell_name:
                return {"error": "name must not be empty"}

            resolved_width = positive_float(width, "width", 0.1, 10000.0)
            resolved_depth = positive_float(depth, "depth", 0.1, 10000.0)
            resolved_height = positive_float(height, "height", 0.1, 10000.0)
            resolved_wall_thickness = positive_float(wall_thickness, "wall_thickness", 0.01, 0.5)
            resolved_floor_thickness = positive_float(floor_thickness, "floor_thickness", 0.01, 0.5)
            resolved_location = vector3(location, (0.0, 0.0, 0.0), "location")

            target_collection = bpy.context.collection
            if collection_name:
                target_collection = bpy.data.collections.get(collection_name)
                if not target_collection:
                    target_collection = bpy.data.collections.new(collection_name)
                    bpy.context.scene.collection.children.link(target_collection)

            wall_material = bpy.data.materials.get(wall_material_name) if wall_material_name else None
            floor_material = bpy.data.materials.get(floor_material_name) if floor_material_name else None
            ceiling_material = bpy.data.materials.get(ceiling_material_name) if ceiling_material_name else None
            if wall_material_name and not wall_material:
                return {"error": f"Wall material not found: {wall_material_name}"}
            if floor_material_name and not floor_material:
                return {"error": f"Floor material not found: {floor_material_name}"}
            if ceiling_material_name and not ceiling_material:
                return {"error": f"Ceiling material not found: {ceiling_material_name}"}

            parts = [
                {
                    "suffix": "Floor",
                    "dimensions": (
                        resolved_width + resolved_wall_thickness * 2.0,
                        resolved_depth + resolved_wall_thickness * 2.0,
                        resolved_floor_thickness,
                    ),
                    "center": (0.0, 0.0, -resolved_floor_thickness * 0.5),
                    "material": floor_material,
                },
                {
                    "suffix": "BackWall",
                    "dimensions": (
                        resolved_width + resolved_wall_thickness * 2.0,
                        resolved_wall_thickness,
                        resolved_height,
                    ),
                    "center": (0.0, resolved_depth * 0.5 + resolved_wall_thickness * 0.5, resolved_height * 0.5),
                    "material": wall_material,
                },
                {
                    "suffix": "LeftWall",
                    "dimensions": (resolved_wall_thickness, resolved_depth, resolved_height),
                    "center": (-resolved_width * 0.5 - resolved_wall_thickness * 0.5, 0.0, resolved_height * 0.5),
                    "material": wall_material,
                },
                {
                    "suffix": "RightWall",
                    "dimensions": (resolved_wall_thickness, resolved_depth, resolved_height),
                    "center": (resolved_width * 0.5 + resolved_wall_thickness * 0.5, 0.0, resolved_height * 0.5),
                    "material": wall_material,
                },
            ]
            if not bool(open_front):
                parts.append({
                    "suffix": "FrontWall",
                    "dimensions": (
                        resolved_width + resolved_wall_thickness * 2.0,
                        resolved_wall_thickness,
                        resolved_height,
                    ),
                    "center": (0.0, -resolved_depth * 0.5 - resolved_wall_thickness * 0.5, resolved_height * 0.5),
                    "material": wall_material,
                })
            if bool(include_ceiling):
                parts.append({
                    "suffix": "Ceiling",
                    "dimensions": (
                        resolved_width + resolved_wall_thickness * 2.0,
                        resolved_depth + resolved_wall_thickness * 2.0,
                        resolved_floor_thickness,
                    ),
                    "center": (0.0, 0.0, resolved_height + resolved_floor_thickness * 0.5),
                    "material": ceiling_material or wall_material,
                })

            all_suffixes = ["Floor", "BackWall", "LeftWall", "RightWall", "FrontWall", "Ceiling"]
            object_names = [f"{shell_name}_{suffix}" for suffix in all_suffixes]
            existing = [bpy.data.objects.get(object_name) for object_name in object_names]
            existing = [obj for obj in existing if obj]
            if existing and not replace_existing:
                return {
                    "error": f"Room shell objects already exist: {', '.join(obj.name for obj in existing)}. Set replace_existing=true to rebuild them."
                }
            if replace_existing:
                for obj in existing:
                    bpy.data.objects.remove(obj, do_unlink=True)

            def cuboid_mesh_data(dimensions):
                sx, sy, sz = (dimension * 0.5 for dimension in dimensions)
                vertices = [
                    (-sx, -sy, -sz),
                    (sx, -sy, -sz),
                    (sx, sy, -sz),
                    (-sx, sy, -sz),
                    (-sx, -sy, sz),
                    (sx, -sy, sz),
                    (sx, sy, sz),
                    (-sx, sy, sz),
                ]
                faces = [
                    (0, 1, 2, 3),
                    (4, 7, 6, 5),
                    (0, 4, 5, 1),
                    (1, 5, 6, 2),
                    (2, 6, 7, 3),
                    (3, 7, 4, 0),
                ]
                return vertices, faces

            created = []
            reports = []
            for part in parts:
                obj_name = f"{shell_name}_{part['suffix']}"
                vertices, faces = cuboid_mesh_data(part["dimensions"])
                mesh = bpy.data.meshes.new(f"{obj_name}_Mesh")
                mesh.from_pydata(vertices, [], faces)
                mesh.update(calc_edges=True)
                obj = bpy.data.objects.new(obj_name, mesh)
                obj.location = (
                    resolved_location[0] + part["center"][0],
                    resolved_location[1] + part["center"][1],
                    resolved_location[2] + part["center"][2],
                )
                if part["material"]:
                    obj.data.materials.append(part["material"])
                target_collection.objects.link(obj)
                created.append(obj.name)
                reports.append(self._mesh_geometry_report(obj, cleanup=bool(validate)))

            return {
                "success": True,
                "name": shell_name,
                "objects": created,
                "width": resolved_width,
                "depth": resolved_depth,
                "height": resolved_height,
                "wall_thickness": resolved_wall_thickness,
                "floor_thickness": resolved_floor_thickness,
                "include_ceiling": bool(include_ceiling),
                "open_front": bool(open_front),
                "collection": target_collection.name if target_collection else None,
                "location": list(resolved_location),
                "geometry": reports,
                "next_safe_action": "validate_mesh_geometry before window/door booleans, bevels, furniture placement, or export",
            }
        except Exception as e:
            return {"error": f"Failed to create room shell: {str(e)}"}

    def create_wall_opening(
        self,
        wall_name,
        name="Wall_Opening",
        opening_type="window",
        center=None,
        opening_width=1.0,
        opening_height=1.2,
        cut_depth=None,
        wall_axis="auto",
        fill_type="glass",
        panel_thickness=0.03,
        create_frame=True,
        frame_width=0.08,
        frame_depth=None,
        collection_name=None,
        fill_material_name=None,
        frame_material_name=None,
        replace_existing=False,
        validate=True,
    ):
        """Cut a bounded window/door opening in an existing wall and optionally add fill/frame parts."""
        cutter = None
        try:
            def vector3(value, label):
                if not isinstance(value, (list, tuple)) or len(value) != 3:
                    raise ValueError(f"{label} must be [x,y,z]")
                return tuple(float(component) for component in value[:3])

            def positive_float(value, label, minimum=0.0001, maximum=10000.0):
                number = float(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            wall = bpy.data.objects.get(wall_name)
            if not wall or wall.type != "MESH":
                return {"error": f"Mesh wall not found: {wall_name}"}

            opening_name = str(name or "Wall_Opening").strip()
            if not opening_name:
                return {"error": "name must not be empty"}

            resolved_type = str(opening_type or "window").lower()
            if resolved_type not in ("window", "door", "empty"):
                return {"error": "opening_type must be window, door, or empty"}

            resolved_width = positive_float(opening_width, "opening_width", 0.05, 10000.0)
            resolved_height = positive_float(opening_height, "opening_height", 0.05, 10000.0)
            resolved_panel_thickness = positive_float(panel_thickness, "panel_thickness", 0.005, 10.0)
            resolved_frame_width = positive_float(frame_width, "frame_width", 0.005, 10.0)
            resolved_center = vector3(center, "center") if center is not None else tuple(wall.location)

            axis = str(wall_axis or "auto").lower()
            if axis not in ("auto", "x", "y"):
                return {"error": "wall_axis must be auto, x, or y"}
            if axis == "auto":
                dims = wall.dimensions
                axis = "x" if float(dims.x) <= float(dims.y) else "y"

            inferred_wall_depth = max(0.01, float(wall.dimensions.x if axis == "x" else wall.dimensions.y))
            resolved_cut_depth = positive_float(
                cut_depth if cut_depth is not None else inferred_wall_depth + 0.1,
                "cut_depth",
                0.01,
                10000.0,
            )
            resolved_frame_depth = positive_float(
                frame_depth if frame_depth is not None else max(resolved_panel_thickness, inferred_wall_depth * 0.55),
                "frame_depth",
                0.005,
                10000.0,
            )

            fill_mode = str(fill_type or "none").lower()
            if fill_mode not in ("none", "glass", "door"):
                return {"error": "fill_type must be none, glass, or door"}
            if resolved_type == "empty":
                fill_mode = "none"

            target_collection = bpy.data.collections.get(collection_name) if collection_name else None
            if collection_name and not target_collection:
                target_collection = bpy.data.collections.new(collection_name)
                bpy.context.scene.collection.children.link(target_collection)
            if not target_collection:
                target_collection = wall.users_collection[0] if wall.users_collection else bpy.context.collection

            fill_material = bpy.data.materials.get(fill_material_name) if fill_material_name else None
            frame_material = bpy.data.materials.get(frame_material_name) if frame_material_name else None
            if fill_material_name and not fill_material:
                return {"error": f"Fill material not found: {fill_material_name}"}
            if frame_material_name and not frame_material:
                return {"error": f"Frame material not found: {frame_material_name}"}

            generated_names = [
                f"{opening_name}_Glass",
                f"{opening_name}_DoorPanel",
                f"{opening_name}_Frame_Top",
                f"{opening_name}_Frame_Bottom",
                f"{opening_name}_Frame_Left",
                f"{opening_name}_Frame_Right",
            ]
            existing = [bpy.data.objects.get(object_name) for object_name in generated_names]
            existing = [obj for obj in existing if obj]
            if existing and not replace_existing:
                return {
                    "error": f"Wall opening objects already exist: {', '.join(obj.name for obj in existing)}. Set replace_existing=true to rebuild them."
                }
            if replace_existing:
                for obj in existing:
                    bpy.data.objects.remove(obj, do_unlink=True)

            def cuboid_mesh_data(dimensions):
                sx, sy, sz = (dimension * 0.5 for dimension in dimensions)
                vertices = [
                    (-sx, -sy, -sz),
                    (sx, -sy, -sz),
                    (sx, sy, -sz),
                    (-sx, sy, -sz),
                    (-sx, -sy, sz),
                    (sx, -sy, sz),
                    (sx, sy, sz),
                    (-sx, sy, sz),
                ]
                faces = [
                    (0, 1, 2, 3),
                    (4, 7, 6, 5),
                    (0, 4, 5, 1),
                    (1, 5, 6, 2),
                    (2, 6, 7, 3),
                    (3, 7, 4, 0),
                ]
                return vertices, faces

            def create_cuboid(obj_name, dimensions, obj_center, material=None):
                vertices, faces = cuboid_mesh_data(dimensions)
                mesh = bpy.data.meshes.new(f"{obj_name}_Mesh")
                mesh.from_pydata(vertices, [], faces)
                mesh.update(calc_edges=True)
                obj = bpy.data.objects.new(obj_name, mesh)
                obj.location = obj_center
                if material:
                    obj.data.materials.append(material)
                target_collection.objects.link(obj)
                return obj

            if axis == "x":
                cutter_dimensions = (resolved_cut_depth, resolved_width, resolved_height)
            else:
                cutter_dimensions = (resolved_width, resolved_cut_depth, resolved_height)

            cutter = create_cuboid(f"{opening_name}_Cutter", cutter_dimensions, resolved_center)
            modifier = wall.modifiers.new(name=f"{opening_name}_Cut", type='BOOLEAN')
            modifier.operation = 'DIFFERENCE'
            modifier.object = cutter
            if hasattr(modifier, "solver"):
                modifier.solver = 'EXACT'

            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            wall.select_set(True)
            bpy.context.view_layer.objects.active = wall
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            bpy.data.objects.remove(cutter, do_unlink=True)
            cutter = None

            created = []
            reports = [self._mesh_geometry_report(wall, cleanup=bool(validate))]
            if fill_mode in ("glass", "door"):
                fill_name = f"{opening_name}_Glass" if fill_mode == "glass" else f"{opening_name}_DoorPanel"
                if axis == "x":
                    fill_dimensions = (resolved_panel_thickness, resolved_width, resolved_height)
                else:
                    fill_dimensions = (resolved_width, resolved_panel_thickness, resolved_height)
                fill_obj = create_cuboid(fill_name, fill_dimensions, resolved_center, fill_material)
                created.append(fill_obj.name)
                reports.append(self._mesh_geometry_report(fill_obj, cleanup=bool(validate)))

            if bool(create_frame):
                frame_specs = []
                if axis == "x":
                    frame_specs = [
                        ("Top", (resolved_frame_depth, resolved_width + resolved_frame_width * 2.0, resolved_frame_width), (0.0, 0.0, resolved_height * 0.5 + resolved_frame_width * 0.5)),
                        ("Bottom", (resolved_frame_depth, resolved_width + resolved_frame_width * 2.0, resolved_frame_width), (0.0, 0.0, -resolved_height * 0.5 - resolved_frame_width * 0.5)),
                        ("Left", (resolved_frame_depth, resolved_frame_width, resolved_height + resolved_frame_width * 2.0), (0.0, -resolved_width * 0.5 - resolved_frame_width * 0.5, 0.0)),
                        ("Right", (resolved_frame_depth, resolved_frame_width, resolved_height + resolved_frame_width * 2.0), (0.0, resolved_width * 0.5 + resolved_frame_width * 0.5, 0.0)),
                    ]
                else:
                    frame_specs = [
                        ("Top", (resolved_width + resolved_frame_width * 2.0, resolved_frame_depth, resolved_frame_width), (0.0, 0.0, resolved_height * 0.5 + resolved_frame_width * 0.5)),
                        ("Bottom", (resolved_width + resolved_frame_width * 2.0, resolved_frame_depth, resolved_frame_width), (0.0, 0.0, -resolved_height * 0.5 - resolved_frame_width * 0.5)),
                        ("Left", (resolved_frame_width, resolved_frame_depth, resolved_height + resolved_frame_width * 2.0), (-resolved_width * 0.5 - resolved_frame_width * 0.5, 0.0, 0.0)),
                        ("Right", (resolved_frame_width, resolved_frame_depth, resolved_height + resolved_frame_width * 2.0), (resolved_width * 0.5 + resolved_frame_width * 0.5, 0.0, 0.0)),
                    ]
                for suffix, dimensions, offset in frame_specs:
                    obj_center = (
                        resolved_center[0] + offset[0],
                        resolved_center[1] + offset[1],
                        resolved_center[2] + offset[2],
                    )
                    frame_obj = create_cuboid(f"{opening_name}_Frame_{suffix}", dimensions, obj_center, frame_material)
                    created.append(frame_obj.name)
                    reports.append(self._mesh_geometry_report(frame_obj, cleanup=bool(validate)))

            return {
                "success": True,
                "wall": wall.name,
                "opening": opening_name,
                "opening_type": resolved_type,
                "wall_axis": axis,
                "center": list(resolved_center),
                "opening_width": resolved_width,
                "opening_height": resolved_height,
                "cut_depth": resolved_cut_depth,
                "fill_type": fill_mode,
                "created_objects": created,
                "geometry": reports,
                "next_safe_action": "validate_object_clearance for fill/frame placement, then create_material_preset or inspect_material_node_graph",
            }
        except Exception as e:
            if cutter and cutter.name in bpy.data.objects:
                bpy.data.objects.remove(cutter, do_unlink=True)
            return {"error": f"Failed to create wall opening: {str(e)}"}

    def add_curve_object(
        self,
        curve_type="bezier",
        name=None,
        points=None,
        cyclic=False,
        resolution=12,
        radius=1.0,
        turns=3,
        height=3.0,
        start_radius=1.0,
        end_radius=1.0,
        points_per_turn=16,
        location=None,
        rotation=None,
        scale=None,
        bevel_depth=0.0,
        bevel_resolution=0,
        fill_mode="FULL",
        material_name=None,
        collection_name=None,
        replace_existing=False,
        convert_to_mesh=False,
    ):
        """Create bounded curve/path objects without arbitrary Python."""
        temp_obj = None
        temp_curve_data = None
        created_collection = None
        try:
            def vector3(value, fallback, label):
                raw = fallback if value is None else value
                if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                    raise ValueError(f"{label} must be [x,y,z]")
                return tuple(float(component) for component in raw[:3])

            def point_list(value):
                if value is None:
                    return [(-1.0, 0.0, 0.0), (0.0, 0.0, 0.75), (1.0, 0.0, 0.0)]
                if not isinstance(value, (list, tuple)) or len(value) < 2:
                    raise ValueError("points must contain at least 2 [x,y,z] coordinates")
                if len(value) > 256:
                    raise ValueError("points must contain no more than 256 coordinates")
                return [vector3(point, None, "point") for point in value]

            def bounded_float(value, label, minimum, maximum):
                number = float(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            def bounded_int(value, label, minimum, maximum):
                number = int(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            curve_key = str(curve_type or "bezier").lower().replace("-", "_")
            aliases = {
                "path": "polyline",
                "poly": "polyline",
                "line": "polyline",
                "bezier_curve": "bezier",
                "circle_curve": "circle",
                "helix": "spiral",
            }
            curve_key = aliases.get(curve_key, curve_key)
            allowed = {"bezier", "polyline", "circle", "spiral"}
            if curve_key not in allowed:
                return {"error": f"Unsupported curve_type: {curve_type}. Use one of: {', '.join(sorted(allowed))}"}

            obj_name = str(name or curve_key.title()).strip()
            if not obj_name:
                return {"error": "name must not be empty"}

            existing = bpy.data.objects.get(obj_name)
            if existing and not replace_existing:
                return {"error": f"Object already exists: {obj_name}. Set replace_existing=true to rebuild it."}

            target_collection = bpy.context.collection
            if collection_name:
                target_collection = bpy.data.collections.get(collection_name)
                if not target_collection:
                    created_collection = bpy.data.collections.new(collection_name)
                    bpy.context.scene.collection.children.link(created_collection)
                    target_collection = created_collection

            mat = None
            if material_name:
                mat = bpy.data.materials.get(material_name)
                if not mat:
                    return {"error": f"Material not found: {material_name}"}

            resolved_location = vector3(location, (0.0, 0.0, 0.0), "location")
            resolved_rotation = tuple(math.radians(value) for value in vector3(rotation, (0.0, 0.0, 0.0), "rotation"))
            resolved_scale = vector3(scale, (1.0, 1.0, 1.0), "scale")
            resolved_resolution = bounded_int(resolution, "resolution", 0, 1024)
            resolved_bevel_depth = bounded_float(bevel_depth, "bevel_depth", 0.0, 1000.0)
            resolved_bevel_resolution = bounded_int(bevel_resolution, "bevel_resolution", 0, 32)
            resolved_fill = str(fill_mode or "FULL").upper()
            if resolved_fill not in {"FULL", "FRONT", "BACK", "HALF"}:
                return {"error": "fill_mode must be FULL, FRONT, BACK, or HALF"}

            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='OBJECT')

            if curve_key == "circle":
                bpy.ops.curve.primitive_bezier_circle_add(
                    radius=bounded_float(radius, "radius", 0.0001, 10000.0),
                    location=resolved_location,
                    rotation=resolved_rotation,
                )
                obj = bpy.context.active_object
                if obj and obj.data:
                    for spline in obj.data.splines:
                        spline.use_cyclic_u = bool(cyclic)
            else:
                if curve_key == "spiral":
                    resolved_turns = bounded_int(turns, "turns", 1, 64)
                    resolved_points_per_turn = bounded_int(points_per_turn, "points_per_turn", 4, 128)
                    resolved_height = bounded_float(height, "height", -10000.0, 10000.0)
                    resolved_start_radius = bounded_float(start_radius, "start_radius", 0.0001, 10000.0)
                    resolved_end_radius = bounded_float(end_radius, "end_radius", 0.0001, 10000.0)
                    total_points = min(512, resolved_turns * resolved_points_per_turn + 1)
                    resolved_points = []
                    for index in range(total_points):
                        t = index / max(1, total_points - 1)
                        angle = t * resolved_turns * 2 * math.pi
                        current_radius = resolved_start_radius + (resolved_end_radius - resolved_start_radius) * t
                        resolved_points.append((
                            math.cos(angle) * current_radius,
                            math.sin(angle) * current_radius,
                            t * resolved_height,
                        ))
                    spline_type = 'POLY'
                elif curve_key == "polyline":
                    resolved_points = point_list(points)
                    spline_type = 'POLY'
                else:
                    resolved_points = point_list(points)
                    spline_type = 'BEZIER'

                curve_data = bpy.data.curves.new(f"__ViperMesh_Curve_Temp_{int(time.time() * 1000)}", type='CURVE')
                temp_curve_data = curve_data
                curve_data.dimensions = '3D'
                curve_data.resolution_u = resolved_resolution

                if spline_type == 'POLY':
                    spline = curve_data.splines.new('POLY')
                    spline.points.add(len(resolved_points) - 1)
                    for index, point in enumerate(resolved_points):
                        spline.points[index].co = (point[0], point[1], point[2], 1.0)
                else:
                    spline = curve_data.splines.new('BEZIER')
                    spline.bezier_points.add(len(resolved_points) - 1)
                    for index, point in enumerate(resolved_points):
                        bezier_point = spline.bezier_points[index]
                        bezier_point.co = point
                        bezier_point.handle_left_type = 'AUTO'
                        bezier_point.handle_right_type = 'AUTO'

                spline.use_cyclic_u = bool(cyclic)
                obj = bpy.data.objects.new(f"__ViperMesh_Curve_Object_Temp_{int(time.time() * 1000)}", curve_data)
                target_collection.objects.link(obj)
                obj.location = resolved_location
                obj.rotation_euler = resolved_rotation

            if not obj or obj.type != "CURVE":
                raise ValueError("Curve creation completed without an active curve object")

            temp_obj = obj
            obj.name = f"__ViperMesh_Curve_Temp_{int(time.time() * 1000)}"
            obj.data.name = f"{obj.name}_Data"
            obj.scale = resolved_scale
            obj.data.resolution_u = resolved_resolution
            obj.data.bevel_depth = resolved_bevel_depth
            obj.data.bevel_resolution = resolved_bevel_resolution
            obj.data.fill_mode = resolved_fill

            if target_collection and target_collection.name not in {collection.name for collection in obj.users_collection}:
                target_collection.objects.link(obj)
            if target_collection:
                for collection in list(obj.users_collection):
                    if collection != target_collection and len(obj.users_collection) > 1:
                        collection.objects.unlink(obj)

            assigned_material = None
            if mat and obj.data:
                obj.data.materials.append(mat)
                assigned_material = mat.name

            object_type = obj.type
            if convert_to_mesh:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.convert(target='MESH')
                obj = bpy.context.active_object
                temp_obj = obj
                obj.name = f"__ViperMesh_Curve_Temp_{int(time.time() * 1000)}"
                if obj.data:
                    obj.data.name = f"{obj.name}_Mesh"
                object_type = obj.type

            if existing and replace_existing:
                bpy.data.objects.remove(existing, do_unlink=True)

            obj.name = obj_name
            if obj.data:
                obj.data.name = f"{obj_name}_Mesh" if obj.type == "MESH" else f"{obj_name}_Curve"
            temp_obj = None

            spline_count = len(obj.data.splines) if obj.type == "CURVE" and obj.data else None
            point_count = None
            if obj.type == "CURVE" and obj.data:
                point_count = 0
                for spline in obj.data.splines:
                    point_count += len(spline.bezier_points) if spline.type == "BEZIER" else len(spline.points)

            return {
                "success": True,
                "object": obj.name,
                "type": object_type,
                "curve_type": curve_key,
                "collection": target_collection.name if target_collection else None,
                "material": assigned_material,
                "location": list(obj.location),
                "rotation_degrees": [round(math.degrees(value), 3) for value in obj.rotation_euler],
                "scale": list(obj.scale),
                "splines": spline_count,
                "points": point_count,
                "cyclic": bool(cyclic),
                "resolution": resolved_resolution,
                "bevel_depth": resolved_bevel_depth,
                "bevel_resolution": resolved_bevel_resolution,
                "fill_mode": resolved_fill,
                "convert_to_mesh": bool(convert_to_mesh),
                "next_safe_action": "assign_material, set_object_transform, or add_modifier if converted to mesh",
            }
        except Exception as e:
            if temp_obj and temp_obj.name in bpy.data.objects:
                bpy.data.objects.remove(temp_obj, do_unlink=True)
            if temp_curve_data and temp_curve_data.name in bpy.data.curves and temp_curve_data.users == 0:
                bpy.data.curves.remove(temp_curve_data)
            if created_collection and created_collection.name in bpy.data.collections and not created_collection.objects:
                bpy.data.collections.remove(created_collection)
            return {"error": f"Failed to add curve object: {str(e)}"}

    def set_curve_properties(
        self,
        name,
        resolution=None,
        bevel_depth=None,
        bevel_resolution=None,
        fill_mode=None,
        cyclic=None,
        material_name=None,
    ):
        """Tune safe properties on an existing curve object."""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}
            if obj.type != "CURVE":
                return {"error": f"Object '{name}' is type '{obj.type}', expected CURVE"}

            def bounded_float(value, label, minimum, maximum):
                number = float(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            def bounded_int(value, label, minimum, maximum):
                number = int(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            resolved_changes = {}
            resolved_material = None
            if resolution is not None:
                resolved_changes["resolution"] = bounded_int(resolution, "resolution", 0, 1024)
            if bevel_depth is not None:
                resolved_changes["bevel_depth"] = bounded_float(bevel_depth, "bevel_depth", 0.0, 1000.0)
            if bevel_resolution is not None:
                resolved_changes["bevel_resolution"] = bounded_int(bevel_resolution, "bevel_resolution", 0, 32)
            if fill_mode is not None:
                value = str(fill_mode).upper()
                if value not in {"FULL", "FRONT", "BACK", "HALF"}:
                    return {"error": "fill_mode must be FULL, FRONT, BACK, or HALF"}
                resolved_changes["fill_mode"] = value
            if cyclic is not None:
                resolved_changes["cyclic"] = bool(cyclic)
            if material_name is not None:
                resolved_material = bpy.data.materials.get(material_name)
                if not resolved_material:
                    return {"error": f"Material not found: {material_name}"}
                resolved_changes["material"] = resolved_material.name

            changes = {}
            if "resolution" in resolved_changes:
                obj.data.resolution_u = resolved_changes["resolution"]
                changes["resolution"] = resolved_changes["resolution"]
            if "bevel_depth" in resolved_changes:
                obj.data.bevel_depth = resolved_changes["bevel_depth"]
                changes["bevel_depth"] = resolved_changes["bevel_depth"]
            if "bevel_resolution" in resolved_changes:
                obj.data.bevel_resolution = resolved_changes["bevel_resolution"]
                changes["bevel_resolution"] = resolved_changes["bevel_resolution"]
            if "fill_mode" in resolved_changes:
                obj.data.fill_mode = resolved_changes["fill_mode"]
                changes["fill_mode"] = resolved_changes["fill_mode"]
            if "cyclic" in resolved_changes:
                for spline in obj.data.splines:
                    spline.use_cyclic_u = resolved_changes["cyclic"]
                changes["cyclic"] = resolved_changes["cyclic"]
            if resolved_material is not None:
                if obj.data.materials:
                    obj.data.materials[0] = resolved_material
                else:
                    obj.data.materials.append(resolved_material)
                changes["material"] = resolved_material.name

            point_count = 0
            for spline in obj.data.splines:
                point_count += len(spline.bezier_points) if spline.type == "BEZIER" else len(spline.points)

            return {
                "success": True,
                "object": obj.name,
                "type": obj.type,
                "splines": len(obj.data.splines),
                "points": point_count,
                "changes": changes,
                "bevel_depth": obj.data.bevel_depth,
                "bevel_resolution": obj.data.bevel_resolution,
                "resolution": obj.data.resolution_u,
                "fill_mode": obj.data.fill_mode,
                "materials": [material.name if material else None for material in obj.data.materials],
            }
        except Exception as e:
            return {"error": f"Failed to set curve properties: {str(e)}"}

    def _mesh_geometry_report(self, obj, cleanup=False):
        mesh = obj.data
        working_mesh = mesh if cleanup else mesh.copy()
        try:
            validate_changed = bool(working_mesh.validate(verbose=False))
            if cleanup:
                working_mesh.update()

            zero_area_faces = 0
            for poly in working_mesh.polygons:
                if poly.area <= 1e-10:
                    zero_area_faces += 1

            edge_face_counts = {}
            for poly in working_mesh.polygons:
                indices = list(poly.vertices)
                for idx, a in enumerate(indices):
                    b = indices[(idx + 1) % len(indices)]
                    edge = tuple(sorted((int(a), int(b))))
                    edge_face_counts[edge] = edge_face_counts.get(edge, 0) + 1

            boundary_edges = sum(1 for count in edge_face_counts.values() if count == 1)
            non_manifold_edges = sum(1 for count in edge_face_counts.values() if count > 2)
            loose_edges = max(0, len(working_mesh.edges) - len(edge_face_counts))

            return {
                "object": obj.name,
                "mesh": mesh.name,
                "vertices": len(working_mesh.vertices),
                "edges": len(working_mesh.edges),
                "faces": len(working_mesh.polygons),
                "validate_changed": validate_changed,
                "zero_area_faces": zero_area_faces,
                "boundary_edges": boundary_edges,
                "non_manifold_edges": non_manifold_edges,
                "loose_edges": loose_edges,
                "valid": (
                    not validate_changed
                    and zero_area_faces == 0
                    and boundary_edges == 0
                    and non_manifold_edges == 0
                    and loose_edges == 0
                ),
                "cleanup_applied": bool(cleanup),
            }
        finally:
            if not cleanup:
                bpy.data.meshes.remove(working_mesh)

    def create_mesh_from_data(
        self,
        name,
        vertices,
        faces,
        edges=None,
        collection_name=None,
        material_name=None,
        location=None,
        replace_existing=False,
        validate=True,
        shade_smooth=False,
    ):
        """Create a mesh object from explicit vertices/faces using Blender's Data API."""
        try:
            if not isinstance(vertices, list) or len(vertices) < 3:
                return {"error": "vertices must contain at least 3 [x,y,z] points"}
            if not isinstance(faces, list) or len(faces) < 1:
                return {"error": "faces must contain at least one face index list"}

            vertex_data = []
            for vertex in vertices:
                if not isinstance(vertex, (list, tuple)) or len(vertex) != 3:
                    return {"error": "Each vertex must be [x,y,z]"}
                vertex_data.append(tuple(float(value) for value in vertex))

            face_data = []
            for face in faces:
                if not isinstance(face, (list, tuple)) or len(face) < 3:
                    return {"error": "Each face must reference at least 3 vertex indices"}
                converted = tuple(int(index) for index in face)
                if any(index < 0 or index >= len(vertex_data) for index in converted):
                    return {"error": f"Face contains vertex index outside 0..{len(vertex_data) - 1}: {list(converted)}"}
                face_data.append(converted)

            edge_data = []
            if edges:
                for edge in edges:
                    if not isinstance(edge, (list, tuple)) or len(edge) != 2:
                        return {"error": "Each edge must be [a,b]"}
                    converted = tuple(int(index) for index in edge)
                    if any(index < 0 or index >= len(vertex_data) for index in converted):
                        return {"error": f"Edge contains vertex index outside 0..{len(vertex_data) - 1}: {list(converted)}"}
                    edge_data.append(converted)

            existing = bpy.data.objects.get(name)
            if existing:
                if not replace_existing:
                    return {"error": f"Object already exists: {name}. Set replace_existing=true to rebuild it."}
                bpy.data.objects.remove(existing, do_unlink=True)

            mesh = bpy.data.meshes.new(f"{name}_Mesh")
            mesh.from_pydata(vertex_data, edge_data, face_data)
            mesh.update(calc_edges=True)
            obj = bpy.data.objects.new(name, mesh)

            if location is not None:
                if not isinstance(location, (list, tuple)) or len(location) != 3:
                    return {"error": "location must be [x,y,z]"}
                obj.location = tuple(float(value) for value in location)

            target_collection = bpy.context.collection
            if collection_name:
                target_collection = bpy.data.collections.get(collection_name)
                if not target_collection:
                    target_collection = bpy.data.collections.new(collection_name)
                    bpy.context.scene.collection.children.link(target_collection)
            target_collection.objects.link(obj)

            assigned_material = None
            if material_name:
                mat = bpy.data.materials.get(material_name)
                if not mat:
                    return {"error": f"Material not found: {material_name}"}
                obj.data.materials.append(mat)
                assigned_material = mat.name

            if shade_smooth:
                for poly in mesh.polygons:
                    poly.use_smooth = True

            report = self._mesh_geometry_report(obj, cleanup=bool(validate))

            return {
                "success": True,
                "object": obj.name,
                "mesh": mesh.name,
                "collection": target_collection.name,
                "material": assigned_material,
                "geometry": report,
                "next_safe_action": "validate_mesh_geometry",
            }
        except Exception as e:
            return {"error": f"Failed to create mesh from data: {str(e)}"}

    def create_draped_surface_mesh(
        self,
        name="Draped_Surface",
        width=2.0,
        depth=2.0,
        subdivisions_x=4,
        subdivisions_y=4,
        sag=0.15,
        wave_amplitude=0.0,
        wave_frequency_x=1.0,
        wave_frequency_y=0.0,
        edge_lift=0.0,
        height=0.0,
        location=None,
        rotation=None,
        collection_name=None,
        material_name=None,
        replace_existing=False,
        validate=True,
        shade_smooth=True,
    ):
        """Create a bounded draped/wavy grid surface mesh without arbitrary Python."""
        try:
            def vector3(value, fallback, label):
                raw = fallback if value is None else value
                if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                    raise ValueError(f"{label} must be [x,y,z]")
                return tuple(float(component) for component in raw[:3])

            def positive_float(value, label, minimum=0.0001, maximum=10000.0):
                number = float(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            def nonnegative_float(value, label, maximum=10000.0):
                number = float(value)
                if number < 0.0 or number > maximum:
                    raise ValueError(f"{label} must be between 0.0 and {maximum}")
                return number

            def bounded_int(value, label, minimum, maximum):
                number = int(value)
                if number < minimum or number > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return number

            obj_name = str(name or "Draped_Surface").strip()
            if not obj_name:
                return {"error": "name must not be empty"}

            resolved_width = positive_float(width, "width")
            resolved_depth = positive_float(depth, "depth")
            resolved_subdivisions_x = bounded_int(subdivisions_x, "subdivisions_x", 1, 256)
            resolved_subdivisions_y = bounded_int(subdivisions_y, "subdivisions_y", 1, 256)
            resolved_sag = nonnegative_float(sag, "sag")
            resolved_wave_amplitude = nonnegative_float(wave_amplitude, "wave_amplitude")
            resolved_wave_frequency_x = float(wave_frequency_x)
            resolved_wave_frequency_y = float(wave_frequency_y)
            resolved_edge_lift = nonnegative_float(edge_lift, "edge_lift")
            resolved_height = float(height)
            resolved_location = vector3(location, (0.0, 0.0, 0.0), "location")
            resolved_rotation = tuple(math.radians(value) for value in vector3(rotation, (0.0, 0.0, 0.0), "rotation"))

            existing = bpy.data.objects.get(obj_name)
            if existing:
                if not replace_existing:
                    return {"error": f"Object already exists: {obj_name}. Set replace_existing=true to rebuild it."}
                bpy.data.objects.remove(existing, do_unlink=True)

            target_collection = bpy.context.collection
            if collection_name:
                target_collection = bpy.data.collections.get(collection_name)
                if not target_collection:
                    target_collection = bpy.data.collections.new(collection_name)
                    bpy.context.scene.collection.children.link(target_collection)

            mat = None
            if material_name:
                mat = bpy.data.materials.get(material_name)
                if not mat:
                    return {"error": f"Material not found: {material_name}"}

            vertices = []
            for y_index in range(resolved_subdivisions_y + 1):
                v = y_index / resolved_subdivisions_y
                y = (v - 0.5) * resolved_depth
                normalized_y = (v * 2.0) - 1.0
                for x_index in range(resolved_subdivisions_x + 1):
                    u = x_index / resolved_subdivisions_x
                    x = (u - 0.5) * resolved_width
                    normalized_x = (u * 2.0) - 1.0
                    center_weight = max(0.0, 1.0 - abs(normalized_x)) * max(0.0, 1.0 - abs(normalized_y))
                    edge_weight = max(abs(normalized_x), abs(normalized_y))
                    wave = resolved_wave_amplitude * math.sin(
                        2.0 * math.pi * ((u * resolved_wave_frequency_x) + (v * resolved_wave_frequency_y))
                    )
                    z = resolved_height + (resolved_edge_lift * edge_weight) - (resolved_sag * center_weight) + wave
                    vertices.append((x, y, z))

            faces = []
            row_width = resolved_subdivisions_x + 1
            for y_index in range(resolved_subdivisions_y):
                for x_index in range(resolved_subdivisions_x):
                    a = y_index * row_width + x_index
                    faces.append((a, a + 1, a + 1 + row_width, a + row_width))

            mesh = bpy.data.meshes.new(f"{obj_name}_Mesh")
            mesh.from_pydata(vertices, [], faces)
            mesh.update(calc_edges=True)
            obj = bpy.data.objects.new(obj_name, mesh)
            obj.location = resolved_location
            obj.rotation_euler = resolved_rotation
            target_collection.objects.link(obj)

            assigned_material = None
            if mat:
                obj.data.materials.append(mat)
                assigned_material = mat.name

            if shade_smooth:
                for poly in obj.data.polygons:
                    poly.use_smooth = True

            report = self._mesh_geometry_report(obj, cleanup=bool(validate))

            return {
                "success": True,
                "object": obj.name,
                "mesh": mesh.name,
                "width": resolved_width,
                "depth": resolved_depth,
                "subdivisions_x": resolved_subdivisions_x,
                "subdivisions_y": resolved_subdivisions_y,
                "sag": resolved_sag,
                "wave_amplitude": resolved_wave_amplitude,
                "wave_frequency_x": resolved_wave_frequency_x,
                "wave_frequency_y": resolved_wave_frequency_y,
                "edge_lift": resolved_edge_lift,
                "height": resolved_height,
                "vertices": len(vertices),
                "faces": len(faces),
                "collection": target_collection.name if target_collection else None,
                "material": assigned_material,
                "location": list(obj.location),
                "rotation_degrees": [round(math.degrees(value), 3) for value in obj.rotation_euler],
                "shade_smooth": bool(shade_smooth),
                "geometry": report,
                "next_safe_action": "validate_mesh_geometry, assign material, then inspect grounding/spatial relations",
            }
        except Exception as e:
            return {"error": f"Failed to create draped surface mesh: {str(e)}"}

    def validate_mesh_geometry(self, names, cleanup=False, require_closed=False):
        """Validate mesh geometry with optional cleanup via mesh.validate()."""
        try:
            raw_names = names if isinstance(names, list) else [names]
            reports = []
            errors = []
            warnings = []

            for raw_name in raw_names:
                obj = bpy.data.objects.get(str(raw_name))
                if not obj:
                    errors.append(f"Object not found: {raw_name}")
                    continue
                if obj.type != "MESH":
                    errors.append(f"{obj.name} is not a mesh (type: {obj.type})")
                    continue

                report = self._mesh_geometry_report(obj, cleanup=bool(cleanup))
                if report["validate_changed"] and not cleanup:
                    errors.append(f"{obj.name}: mesh.validate() would modify invalid geometry")
                if report["zero_area_faces"] > 0:
                    errors.append(f"{obj.name}: {report['zero_area_faces']} zero-area face(s)")
                if report["non_manifold_edges"] > 0:
                    errors.append(f"{obj.name}: {report['non_manifold_edges']} non-manifold edge(s)")
                if require_closed and report["boundary_edges"] > 0:
                    errors.append(f"{obj.name}: {report['boundary_edges']} boundary edge(s); mesh is not closed")
                elif report["boundary_edges"] > 0:
                    warnings.append(f"{obj.name}: {report['boundary_edges']} boundary edge(s)")
                if report["loose_edges"] > 0:
                    warnings.append(f"{obj.name}: {report['loose_edges']} loose edge(s)")
                reports.append(report)

            return {
                "success": True,
                "ready": len(errors) == 0,
                "objects": reports,
                "errors": errors,
                "warnings": warnings,
                "cleanup_applied": bool(cleanup),
                "next_safe_action": "continue" if len(errors) == 0 else "repair mesh data or rerun with cleanup=true when safe",
            }
        except Exception as e:
            return {"error": f"Failed to validate mesh geometry: {str(e)}"}

    def repair_mesh_geometry(
        self,
        name,
        result_name=None,
        mode="COPY",
        preserve_source=True,
        merge_by_distance=True,
        merge_distance=0.0001,
        remove_loose=True,
        recalculate_normals=True,
        shade_smooth=False,
    ):
        """Repair common mesh geometry issues, preserving the source by default."""
        try:
            obj = bpy.data.objects.get(str(name))
            if not obj:
                return {"error": f"Object not found: {name}"}
            if obj.type != "MESH":
                return {"error": f"{obj.name} is not a mesh (type: {obj.type})"}
            original_source_name = obj.name

            mode_key = str(mode or ("COPY" if preserve_source else "REPLACE")).strip().upper()
            if preserve_source is False:
                mode_key = "REPLACE"
            if mode_key not in {"COPY", "REPLACE"}:
                return {"error": "mode must be COPY or REPLACE"}

            try:
                resolved_merge_distance = float(merge_distance)
            except (TypeError, ValueError):
                return {"error": "merge_distance must be a finite positive number"}
            if not math.isfinite(resolved_merge_distance) or resolved_merge_distance <= 0:
                return {"error": "merge_distance must be a finite positive number"}

            def mesh_counts(target):
                mesh = target.data
                return {
                    "vertices": len(mesh.vertices),
                    "edges": len(mesh.edges),
                    "faces": len(mesh.polygons),
                    "uv_layers": len(mesh.uv_layers),
                    "material_slots": len(target.material_slots),
                }

            def ensure_object_mode():
                active = bpy.context.view_layer.objects.active
                if active and getattr(active, "mode", "OBJECT") != "OBJECT":
                    mode_result = bpy.ops.object.mode_set(mode='OBJECT')
                    if "FINISHED" not in mode_result:
                        raise RuntimeError(f"Failed to switch to OBJECT mode: {sorted(mode_result)}")

            before_counts = mesh_counts(obj)
            before_validation = self._mesh_geometry_report(obj, cleanup=False)
            if before_counts["vertices"] < 1:
                return {"error": f"{obj.name} has no vertices to repair"}

            created_target = False
            original_target_name = obj.name
            original_target_mesh_name = obj.data.name

            if mode_key == "COPY":
                target_name = str(result_name).strip() if result_name else f"{obj.name}_Repaired"
                if not target_name:
                    return {"error": "result_name cannot be blank"}
                if bpy.data.objects.get(target_name):
                    return {"error": f"Object already exists: {target_name}. Choose a unique result_name."}
                target = obj.copy()
                target.data = obj.data.copy()
                target.name = target_name
                target.data.name = f"{target_name}_Mesh"
                if obj.users_collection:
                    for collection in obj.users_collection:
                        collection.objects.link(target)
                else:
                    bpy.context.collection.objects.link(target)
                target.matrix_world = obj.matrix_world.copy()
                created_target = True
                source_preserved = True
            else:
                target = obj
                if result_name and str(result_name).strip() and str(result_name).strip() != obj.name:
                    if bpy.data.objects.get(str(result_name).strip()):
                        return {"error": f"Object already exists: {str(result_name).strip()}"}
                    target.name = str(result_name).strip()
                    target.data.name = f"{target.name}_Mesh"
                source_preserved = False

            def cleanup_created_target():
                if created_target and target and target.name in bpy.data.objects:
                    bpy.data.objects.remove(target, do_unlink=True)

            def restore_renamed_target():
                if not created_target and target:
                    target.name = original_target_name
                    if target.data:
                        target.data.name = original_target_mesh_name

            operator_status = {}
            try:
                ensure_object_mode()
                select_result = bpy.ops.object.select_all(action='DESELECT')
                if "FINISHED" not in select_result:
                    raise RuntimeError(f"Failed to clear object selection: {sorted(select_result)}")
                target.select_set(True)
                bpy.context.view_layer.objects.active = target

                mode_result = bpy.ops.object.mode_set(mode='EDIT')
                if "FINISHED" not in mode_result:
                    raise RuntimeError(f"Failed to switch to EDIT mode: {sorted(mode_result)}")

                if bool(merge_by_distance):
                    select_all_result = bpy.ops.mesh.select_all(action='SELECT')
                    if "FINISHED" not in select_all_result:
                        raise RuntimeError(f"Failed to select mesh geometry before merge: {sorted(select_all_result)}")
                    merge_result = bpy.ops.mesh.remove_doubles(threshold=resolved_merge_distance)
                    if "FINISHED" not in merge_result:
                        raise RuntimeError(f"Failed to merge duplicate vertices: {sorted(merge_result)}")
                    operator_status["remove_doubles"] = sorted(merge_result)

                if bool(remove_loose):
                    loose_result = bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
                    if "FINISHED" not in loose_result:
                        raise RuntimeError(f"Failed to remove loose geometry: {sorted(loose_result)}")
                    operator_status["delete_loose"] = sorted(loose_result)

                if bool(recalculate_normals):
                    select_all_result = bpy.ops.mesh.select_all(action='SELECT')
                    if "FINISHED" not in select_all_result:
                        raise RuntimeError(f"Failed to select mesh geometry before normal recalculation: {sorted(select_all_result)}")
                    normals_result = bpy.ops.mesh.normals_make_consistent(inside=False)
                    if "FINISHED" not in normals_result:
                        raise RuntimeError(f"Failed to recalculate mesh normals: {sorted(normals_result)}")
                    operator_status["normals_make_consistent"] = sorted(normals_result)

                object_mode_result = bpy.ops.object.mode_set(mode='OBJECT')
                if "FINISHED" not in object_mode_result:
                    raise RuntimeError(f"Failed to return to OBJECT mode: {sorted(object_mode_result)}")
            except Exception as operator_error:
                try:
                    if bpy.context.view_layer.objects.active and getattr(bpy.context.view_layer.objects.active, "mode", "OBJECT") != "OBJECT":
                        bpy.ops.object.mode_set(mode='OBJECT')
                except Exception:
                    pass
                cleanup_created_target()
                restore_renamed_target()
                return {"error": f"Failed to repair mesh geometry: {str(operator_error)}"}

            target.data.update()
            if bool(shade_smooth):
                for polygon in target.data.polygons:
                    polygon.use_smooth = True

            after_counts = mesh_counts(target)
            after_validation = self._mesh_geometry_report(target, cleanup=False)

            return {
                "success": True,
                "source_object": original_source_name,
                "result_object": target.name,
                "mode": mode_key,
                "source_preserved": source_preserved,
                "merge_by_distance": bool(merge_by_distance),
                "merge_distance": resolved_merge_distance,
                "remove_loose": bool(remove_loose),
                "recalculate_normals": bool(recalculate_normals),
                "shade_smooth": bool(shade_smooth),
                "before_counts": before_counts,
                "after_counts": after_counts,
                "before_validation": before_validation,
                "after_validation": after_validation,
                "vertices_removed": max(0, before_counts["vertices"] - after_counts["vertices"]),
                "edges_removed": max(0, before_counts["edges"] - after_counts["edges"]),
                "faces_removed": max(0, before_counts["faces"] - after_counts["faces"]),
                "operator_status": operator_status,
                "next_safe_action": "validate_mesh_geometry before retopology, rigging, or export",
            }
        except Exception as e:
            return {"error": f"Failed to repair mesh geometry: {str(e)}"}

    def inspect_retopology_readiness(self, names=None, max_objects=120, high_density_face_threshold=100000):
        """Inspect topology density and face composition before retopology, decimation, remesh, or export."""
        try:
            if names is None:
                objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"][:max(1, int(max_objects))]
                missing_names = []
            else:
                raw_names = names if isinstance(names, list) else [names]
                objects = []
                missing_names = []
                for raw_name in list(dict.fromkeys(str(name) for name in raw_names)):
                    obj = bpy.data.objects.get(str(raw_name))
                    if obj and obj.type == "MESH":
                        objects.append(obj)
                    elif obj:
                        missing_names.append(f"{raw_name} (not a mesh: {obj.type})")
                    else:
                        missing_names.append(str(raw_name))

            reports = []
            issues = []
            threshold = max(1, int(high_density_face_threshold))
            for obj in objects:
                mesh = obj.data
                geometry = self._mesh_geometry_report(obj, cleanup=False)
                triangle_faces = 0
                quad_faces = 0
                ngon_faces = 0
                evaluated_triangles = 0
                material_indices = set()
                smooth_faces = 0
                for poly in mesh.polygons:
                    sides = len(poly.vertices)
                    evaluated_triangles += max(0, sides - 2)
                    if sides == 3:
                        triangle_faces += 1
                    elif sides == 4:
                        quad_faces += 1
                    else:
                        ngon_faces += 1
                    material_indices.add(int(poly.material_index))
                    if bool(getattr(poly, "use_smooth", False)):
                        smooth_faces += 1

                face_count = len(mesh.polygons)
                triangle_ratio = (triangle_faces / face_count) if face_count else 0.0
                quad_ratio = (quad_faces / face_count) if face_count else 0.0
                ngon_ratio = (ngon_faces / face_count) if face_count else 0.0
                has_uvs = len(mesh.uv_layers) > 0
                has_materials = len(obj.material_slots) > 0
                decimation_candidate = face_count >= threshold or triangle_ratio > 0.85

                object_issues = []
                if face_count == 0:
                    object_issues.append("empty_mesh")
                if geometry["non_manifold_edges"] > 0:
                    object_issues.append("non_manifold_edges")
                if geometry["zero_area_faces"] > 0:
                    object_issues.append("zero_area_faces")
                if ngon_faces > 0:
                    object_issues.append("ngon_faces")
                if decimation_candidate:
                    object_issues.append("decimation_candidate")
                if not has_uvs:
                    object_issues.append("missing_uvs")
                if not has_materials:
                    object_issues.append("missing_materials")

                for issue in object_issues:
                    issues.append({"object": obj.name, "code": issue})

                reports.append({
                    "name": obj.name,
                    "mesh": mesh.name,
                    "vertices": len(mesh.vertices),
                    "edges": len(mesh.edges),
                    "faces": face_count,
                    "evaluated_triangles": evaluated_triangles,
                    "triangle_faces": triangle_faces,
                    "quad_faces": quad_faces,
                    "ngon_faces": ngon_faces,
                    "triangle_ratio": triangle_ratio,
                    "quad_ratio": quad_ratio,
                    "ngon_ratio": ngon_ratio,
                    "smooth_face_ratio": (smooth_faces / face_count) if face_count else 0.0,
                    "uv_layer_count": len(mesh.uv_layers),
                    "has_uvs": has_uvs,
                    "material_slot_count": len(obj.material_slots),
                    "used_material_indices": sorted(material_indices),
                    "non_manifold_edges": geometry["non_manifold_edges"],
                    "boundary_edges": geometry["boundary_edges"],
                    "loose_edges": geometry["loose_edges"],
                    "zero_area_faces": geometry["zero_area_faces"],
                    "decimation_candidate": decimation_candidate,
                    "recommended_next_tool": "validate_mesh_geometry" if object_issues else "continue",
                    "issues": object_issues,
                })

            return {
                "success": True,
                "ready": len(issues) == 0,
                "object_count": len(reports),
                "missing_objects": missing_names,
                "objects": reports,
                "issues": issues,
                "next_safe_action": "use validate_mesh_geometry for invalid topology, prepare_uv_layout for missing UVs, or add_modifier DECIMATE/REMESH only after inspection",
            }
        except Exception as e:
            return {"error": f"Failed to inspect retopology readiness: {str(e)}"}

    def compare_mesh_surfaces(
        self,
        source_name,
        candidate_name,
        distance_tolerance=0.01,
        seam_tolerance=None,
        max_surface_samples=10000,
        max_attribute_samples=10000,
    ):
        """Compare two evaluated meshes without changing either object."""
        try:
            source = bpy.data.objects.get(str(source_name))
            candidate = bpy.data.objects.get(str(candidate_name))
            missing = [
                name for name, obj in (
                    (str(source_name), source),
                    (str(candidate_name), candidate),
                )
                if obj is None
            ]
            if missing:
                return {"success": False, "error": "Objects not found", "missing_names": missing}
            invalid = [obj.name for obj in (source, candidate) if obj.type != "MESH"]
            if invalid:
                return {
                    "success": False,
                    "error": "Mesh surface comparison only supports mesh objects",
                    "invalid_names": invalid,
                }
            if source == candidate:
                return {
                    "success": False,
                    "error": "source_name and candidate_name must identify different objects",
                }

            distance_tolerance = float(distance_tolerance)
            if not math.isfinite(distance_tolerance) or distance_tolerance < 0:
                return {"success": False, "error": "distance_tolerance must be a finite non-negative number"}
            seam_tolerance = distance_tolerance if seam_tolerance is None else float(seam_tolerance)
            if not math.isfinite(seam_tolerance) or seam_tolerance < 0:
                return {"success": False, "error": "seam_tolerance must be a finite non-negative number"}
            max_surface_samples = max(1, min(int(max_surface_samples), 20000))
            max_attribute_samples = max(1, min(int(max_attribute_samples), 20000))

            depsgraph = bpy.context.evaluated_depsgraph_get()

            def snapshot(obj):
                evaluated = obj.evaluated_get(depsgraph)
                mesh = evaluated.to_mesh()
                try:
                    if len(mesh.polygons) > MAX_MESH_SURFACE_COMPARISON_FACES:
                        raise ValueError(
                            f"{obj.name} exceeds the {MAX_MESH_SURFACE_COMPARISON_FACES} evaluated-face comparison limit"
                        )
                    if len(mesh.vertices) > MAX_MESH_SURFACE_COMPARISON_VERTICES:
                        raise ValueError(
                            f"{obj.name} exceeds the {MAX_MESH_SURFACE_COMPARISON_VERTICES} evaluated-vertex comparison limit"
                        )
                    matrix = evaluated.matrix_world
                    vertices = [tuple(matrix @ vertex.co) for vertex in mesh.vertices]
                    polygons = [tuple(polygon.vertices) for polygon in mesh.polygons]
                    polygon_centers = []
                    material_names = []
                    for polygon in mesh.polygons:
                        polygon_centers.append(tuple(matrix @ polygon.center))
                        material = (
                            evaluated.material_slots[polygon.material_index].material
                            if polygon.material_index < len(evaluated.material_slots)
                            else None
                        )
                        material_names.append(material.name if material else None)
                    seam_segments = []
                    for edge in mesh.edges:
                        if not bool(getattr(edge, "use_seam", False)):
                            continue
                        start, end = edge.vertices
                        start_point = matrix @ mesh.vertices[start].co
                        end_point = matrix @ mesh.vertices[end].co
                        seam_segments.append({
                            "start": tuple(start_point),
                            "end": tuple(end_point),
                            "midpoint": tuple((start_point + end_point) * 0.5),
                        })
                    return {
                        "vertices": vertices,
                        "polygons": polygons,
                        "polygon_centers": polygon_centers,
                        "material_names": material_names,
                        "seam_segments": seam_segments,
                    }
                finally:
                    evaluated.to_mesh_clear()

            def sample_indices(count, maximum):
                if count <= maximum:
                    return list(range(count))
                return sorted({
                    min(count - 1, int(index * count / maximum))
                    for index in range(maximum)
                })

            def build_bvh(snapshot):
                if not snapshot["vertices"] or not snapshot["polygons"]:
                    raise ValueError("Both objects need evaluated polygon surfaces")
                return BVHTree.FromPolygons(
                    snapshot["vertices"],
                    snapshot["polygons"],
                    all_triangles=False,
                )

            def nearest_distances(points, tree, maximum):
                distances = []
                for index in sample_indices(len(points), maximum):
                    nearest = tree.find_nearest(Vector(points[index]))
                    if nearest is None or nearest[3] is None:
                        raise ValueError("Nearest-surface comparison failed")
                    distances.append(float(nearest[3]))
                return distances

            def polygon_center(snapshot, polygon_index):
                return Vector(snapshot["polygon_centers"][polygon_index])

            def material_mismatches(origin, target, target_tree):
                mismatches = 0
                compared = 0
                for polygon_index in sample_indices(
                    len(origin["polygons"]),
                    max_attribute_samples,
                ):
                    nearest = target_tree.find_nearest(
                        polygon_center(origin, polygon_index),
                    )
                    target_index = nearest[2] if nearest else None
                    if target_index is None:
                        mismatches += 1
                    elif (
                        origin["material_names"][polygon_index]
                        != target["material_names"][target_index]
                    ):
                        mismatches += 1
                    compared += 1
                return mismatches, compared

            def seam_mismatches(origin_segments, target_segments):
                sampled = sample_indices(len(origin_segments), max_attribute_samples)
                if not sampled:
                    return 0, 0
                if not target_segments:
                    return len(sampled), len(sampled)
                tree = KDTree(len(target_segments))
                for index, segment in enumerate(target_segments):
                    tree.insert(segment["midpoint"], index)
                tree.balance()
                mismatches = 0
                matched_target_indices = set()
                for index in sampled:
                    origin = origin_segments[index]
                    matches = sorted(
                        tree.find_range(
                            origin["midpoint"],
                            max(seam_tolerance, 1e-12),
                        ),
                        key=lambda match: float(match[2]),
                    )
                    matched = False
                    for _co, target_index, _distance in matches:
                        if target_index in matched_target_indices:
                            continue
                        target = target_segments[target_index]
                        direct = max(
                            (Vector(origin["start"]) - Vector(target["start"])).length,
                            (Vector(origin["end"]) - Vector(target["end"])).length,
                        )
                        reversed_match = max(
                            (Vector(origin["start"]) - Vector(target["end"])).length,
                            (Vector(origin["end"]) - Vector(target["start"])).length,
                        )
                        if min(direct, reversed_match) <= seam_tolerance:
                            matched_target_indices.add(target_index)
                            matched = True
                            break
                    if not matched:
                        mismatches += 1
                return mismatches, len(sampled)

            source_snapshot = snapshot(source)
            candidate_snapshot = snapshot(candidate)
            source_tree = build_bvh(source_snapshot)
            candidate_tree = build_bvh(candidate_snapshot)

            source_surface_points = (
                source_snapshot["vertices"] + source_snapshot["polygon_centers"]
            )
            candidate_surface_points = (
                candidate_snapshot["vertices"] + candidate_snapshot["polygon_centers"]
            )
            source_distances = nearest_distances(
                source_surface_points,
                candidate_tree,
                max_surface_samples,
            )
            candidate_distances = nearest_distances(
                candidate_surface_points,
                source_tree,
                max_surface_samples,
            )
            all_distances = source_distances + candidate_distances

            source_material_mismatches, source_material_compared = material_mismatches(
                source_snapshot,
                candidate_snapshot,
                candidate_tree,
            )
            candidate_material_mismatches, candidate_material_compared = material_mismatches(
                candidate_snapshot,
                source_snapshot,
                source_tree,
            )
            source_seam_mismatches, source_seams_compared = seam_mismatches(
                source_snapshot["seam_segments"],
                candidate_snapshot["seam_segments"],
            )
            candidate_seam_mismatches, candidate_seams_compared = seam_mismatches(
                candidate_snapshot["seam_segments"],
                source_snapshot["seam_segments"],
            )

            max_surface_deviation = max(all_distances) if all_distances else 0.0
            return {
                "success": True,
                "policy_version": "mesh-surface-comparison-v1",
                "source_object": source.name,
                "candidate_object": candidate.name,
                "distance_tolerance": distance_tolerance,
                "seam_tolerance": seam_tolerance,
                "surface_sampling_mode": "vertices-and-polygon-centers",
                "source_vertex_count": len(source_snapshot["vertices"]),
                "candidate_vertex_count": len(candidate_snapshot["vertices"]),
                "source_polygon_count": len(source_snapshot["polygons"]),
                "candidate_polygon_count": len(candidate_snapshot["polygons"]),
                "max_surface_deviation": max_surface_deviation,
                "mean_surface_deviation": (
                    sum(all_distances) / len(all_distances) if all_distances else 0.0
                ),
                "surface_deviation_exceeds_tolerance": (
                    max_surface_deviation > distance_tolerance
                ),
                "surface_sample_count": len(all_distances),
                "surface_sampling_complete": (
                    len(source_surface_points) <= max_surface_samples
                    and len(candidate_surface_points) <= max_surface_samples
                ),
                "material_sample_count": (
                    source_material_compared + candidate_material_compared
                ),
                "material_sampling_complete": (
                    len(source_snapshot["polygons"]) <= max_attribute_samples
                    and len(candidate_snapshot["polygons"]) <= max_attribute_samples
                ),
                "material_boundary_mismatch_count": (
                    source_material_mismatches + candidate_material_mismatches
                ),
                "source_uv_seam_count": len(source_snapshot["seam_segments"]),
                "candidate_uv_seam_count": len(candidate_snapshot["seam_segments"]),
                "uv_seam_sample_count": source_seams_compared + candidate_seams_compared,
                "uv_seam_sampling_complete": (
                    len(source_snapshot["seam_segments"]) <= max_attribute_samples
                    and len(candidate_snapshot["seam_segments"]) <= max_attribute_samples
                ),
                "uv_seam_mismatch_count": (
                    source_seam_mismatches + candidate_seam_mismatches
                ),
                "note": (
                    "This is bounded geometric evidence. The artist decides whether "
                    "the candidate preserves the intended visual result."
                ),
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to compare mesh surfaces: {str(e)}"}

    def decimate_mesh(
        self,
        name,
        result_name=None,
        mode="COPY",
        preserve_source=True,
        ratio=None,
        target_face_count=None,
        decimate_type="COLLAPSE",
        iterations=None,
        angle_limit=None,
        apply_modifier=True,
    ):
        """Reduce mesh density with Blender's Decimate modifier, preserving the source by default."""
        try:
            obj = bpy.data.objects.get(str(name))
            if not obj:
                return {"error": f"Object not found: {name}"}
            if obj.type != "MESH":
                return {"error": f"{obj.name} is not a mesh (type: {obj.type})"}
            original_source_name = obj.name

            mode_key = str(mode or ("COPY" if preserve_source else "REPLACE")).strip().upper()
            if preserve_source is False:
                mode_key = "REPLACE"
            if mode_key not in {"COPY", "REPLACE"}:
                return {"error": "mode must be COPY or REPLACE"}

            if ratio is not None and target_face_count is not None:
                return {"error": "target_face_count and ratio are mutually exclusive"}

            type_key = str(decimate_type or "COLLAPSE").strip().upper()
            if type_key not in {"COLLAPSE", "UNSUBDIV", "DISSOLVE"}:
                return {"error": "decimate_type must be COLLAPSE, UNSUBDIV, or DISSOLVE"}
            if target_face_count is not None and type_key != "COLLAPSE":
                return {"error": "target_face_count is only supported for COLLAPSE decimation"}

            def mesh_counts(target):
                mesh = target.data
                return {
                    "vertices": len(mesh.vertices),
                    "edges": len(mesh.edges),
                    "faces": len(mesh.polygons),
                    "uv_layers": len(mesh.uv_layers),
                    "material_slots": len(target.material_slots),
                }

            def evaluated_mesh_counts(target):
                depsgraph = bpy.context.evaluated_depsgraph_get()
                evaluated = target.evaluated_get(depsgraph)
                mesh = evaluated.to_mesh()
                try:
                    return {
                        "vertices": len(mesh.vertices),
                        "edges": len(mesh.edges),
                        "faces": len(mesh.polygons),
                        "uv_layers": len(mesh.uv_layers),
                        "material_slots": len(target.material_slots),
                    }
                finally:
                    evaluated.to_mesh_clear()

            def ensure_object_mode():
                active = bpy.context.view_layer.objects.active
                if active and getattr(active, "mode", "OBJECT") != "OBJECT":
                    mode_result = bpy.ops.object.mode_set(mode='OBJECT')
                    if "FINISHED" not in mode_result:
                        raise RuntimeError(f"Failed to switch to OBJECT mode: {sorted(mode_result)}")

            before_counts = mesh_counts(obj)
            if before_counts["faces"] < 1:
                return {"error": f"{obj.name} has no faces to decimate"}

            warnings = []
            resolved_ratio = None
            resolved_iterations = None
            resolved_angle_limit = None

            if type_key == "COLLAPSE":
                if target_face_count is not None:
                    try:
                        target_faces = int(target_face_count)
                    except (TypeError, ValueError):
                        return {"error": "target_face_count must be an integer"}
                    if target_faces < 1:
                        return {"error": "target_face_count must be at least 1"}
                    resolved_ratio = min(1.0, target_faces / before_counts["faces"])
                    if target_faces >= before_counts["faces"]:
                        warnings.append("target_face_count is not below the current face count; ratio was clamped to 1.0")
                elif ratio is None:
                    resolved_ratio = 0.5
                else:
                    try:
                        resolved_ratio = float(ratio)
                    except (TypeError, ValueError):
                        return {"error": "ratio must be a finite number greater than 0 and at most 1"}
                    if not math.isfinite(resolved_ratio) or resolved_ratio <= 0 or resolved_ratio > 1:
                        return {"error": "ratio must be a finite number greater than 0 and at most 1"}

            elif type_key == "UNSUBDIV":
                if iterations is None:
                    resolved_iterations = 1
                else:
                    try:
                        resolved_iterations = int(iterations)
                    except (TypeError, ValueError):
                        return {"error": "iterations must be an integer between 1 and 10"}
                    if resolved_iterations < 1 or resolved_iterations > 10:
                        return {"error": "iterations must be an integer between 1 and 10"}

            elif type_key == "DISSOLVE":
                if angle_limit is None:
                    resolved_angle_limit = math.radians(5.0)
                else:
                    try:
                        resolved_angle_limit = float(angle_limit)
                    except (TypeError, ValueError):
                        return {"error": "angle_limit must be a finite non-negative number in radians"}
                    if not math.isfinite(resolved_angle_limit) or resolved_angle_limit < 0:
                        return {"error": "angle_limit must be a finite non-negative number in radians"}

            created_target = False
            original_target_name = obj.name
            original_target_mesh_name = obj.data.name

            if mode_key == "COPY":
                target_name = str(result_name).strip() if result_name else f"{obj.name}_Decimated"
                if not target_name:
                    return {"error": "result_name cannot be blank"}
                if bpy.data.objects.get(target_name):
                    return {"error": f"Object already exists: {target_name}. Choose a unique result_name."}
                target = obj.copy()
                target.data = obj.data.copy()
                target.name = target_name
                target.data.name = f"{target_name}_Mesh"
                if obj.users_collection:
                    for collection in obj.users_collection:
                        collection.objects.link(target)
                else:
                    bpy.context.collection.objects.link(target)
                target.matrix_world = obj.matrix_world.copy()
                created_target = True
                source_preserved = True
            else:
                target = obj
                if result_name and str(result_name).strip() and str(result_name).strip() != obj.name:
                    if bpy.data.objects.get(str(result_name).strip()):
                        return {"error": f"Object already exists: {str(result_name).strip()}"}
                    target.name = str(result_name).strip()
                    target.data.name = f"{target.name}_Mesh"
                source_preserved = False

            def cleanup_created_target():
                if created_target and target and target.name in bpy.data.objects:
                    bpy.data.objects.remove(target, do_unlink=True)

            def restore_renamed_target():
                if not created_target and target:
                    target.name = original_target_name
                    if target.data:
                        target.data.name = original_target_mesh_name

            original_material_names = [slot.material.name if slot.material else None for slot in obj.material_slots]
            original_uv_names = [layer.name for layer in obj.data.uv_layers]

            try:
                ensure_object_mode()
                select_result = bpy.ops.object.select_all(action='DESELECT')
                if "FINISHED" not in select_result:
                    raise RuntimeError(f"Failed to clear object selection: {sorted(select_result)}")
                target.select_set(True)
                bpy.context.view_layer.objects.active = target

                modifier = target.modifiers.new(name="ViperMesh_Decimate", type='DECIMATE')
                modifier.decimate_type = type_key
                if type_key == "COLLAPSE":
                    modifier.ratio = resolved_ratio
                elif type_key == "UNSUBDIV":
                    modifier.iterations = resolved_iterations
                elif type_key == "DISSOLVE":
                    modifier.angle_limit = resolved_angle_limit

                if bool(apply_modifier):
                    apply_result = bpy.ops.object.modifier_apply(modifier=modifier.name)
                    if "FINISHED" not in apply_result:
                        raise RuntimeError(f"Failed to apply Decimate modifier: {sorted(apply_result)}")
            except Exception as operator_error:
                cleanup_created_target()
                restore_renamed_target()
                return {"error": f"Failed to decimate mesh: {str(operator_error)}"}

            target.data.update()
            after_counts = mesh_counts(target) if bool(apply_modifier) else evaluated_mesh_counts(target)
            result_material_names = [slot.material.name if slot.material else None for slot in target.material_slots]
            result_uv_names = [layer.name for layer in target.data.uv_layers]
            materials_preserved = result_material_names == original_material_names
            uv_layers_preserved = result_uv_names == original_uv_names

            return {
                "success": True,
                "source_object": original_source_name,
                "result_object": target.name,
                "mode": mode_key,
                "source_preserved": source_preserved,
                "modifier_applied": bool(apply_modifier),
                "decimate_type": type_key,
                "ratio": resolved_ratio,
                "target_face_count": int(target_face_count) if target_face_count is not None else None,
                "iterations": resolved_iterations,
                "angle_limit": resolved_angle_limit,
                "before_counts": before_counts,
                "after_counts": after_counts,
                "materials_preserved": materials_preserved,
                "uv_layers_preserved": uv_layers_preserved,
                "material_slots": result_material_names,
                "uv_layers": result_uv_names,
                "warnings": warnings,
                "next_safe_action": "inspect_retopology_readiness then validate_mesh_geometry before export, remesh, rigging, or destructive cleanup",
            }
        except Exception as e:
            return {"error": f"Failed to decimate mesh: {str(e)}"}

    def voxel_remesh_mesh(
        self,
        name,
        result_name=None,
        mode="COPY",
        preserve_source=True,
        voxel_size=0.03,
        adaptivity=0.0,
        preserve_attributes=True,
        preserve_volume=True,
        fix_poles=False,
    ):
        """Voxel remesh a mesh object, preserving the source by default."""
        try:
            obj = bpy.data.objects.get(str(name))
            if not obj:
                return {"error": f"Object not found: {name}"}
            if obj.type != "MESH":
                return {"error": f"{obj.name} is not a mesh (type: {obj.type})"}
            original_source_name = obj.name

            mode_key = str(mode or ("COPY" if preserve_source else "REPLACE")).strip().upper()
            if preserve_source is False:
                mode_key = "REPLACE"
            if mode_key not in {"COPY", "REPLACE"}:
                return {"error": "mode must be COPY or REPLACE"}

            try:
                resolved_voxel_size = float(voxel_size)
            except (TypeError, ValueError):
                return {"error": "voxel_size must be a finite positive number"}
            if not math.isfinite(resolved_voxel_size) or resolved_voxel_size <= 0:
                return {"error": "voxel_size must be a finite positive number"}

            try:
                resolved_adaptivity = float(adaptivity)
            except (TypeError, ValueError):
                return {"error": "adaptivity must be a finite number between 0 and 1"}
            if not math.isfinite(resolved_adaptivity) or resolved_adaptivity < 0 or resolved_adaptivity > 1:
                return {"error": "adaptivity must be a finite number between 0 and 1"}

            def mesh_counts(target):
                mesh = target.data
                return {
                    "vertices": len(mesh.vertices),
                    "edges": len(mesh.edges),
                    "faces": len(mesh.polygons),
                    "uv_layers": len(mesh.uv_layers),
                    "material_slots": len(target.material_slots),
                }

            def mesh_attribute_signature(target):
                attributes = getattr(target.data, "attributes", None)
                if not attributes:
                    return []
                signature = []
                for attribute in attributes:
                    if str(attribute.name).startswith("."):
                        continue
                    signature.append((
                        str(attribute.name),
                        str(getattr(attribute, "data_type", "")),
                        str(getattr(attribute, "domain", "")),
                    ))
                return sorted(signature)

            def ensure_object_mode():
                active = bpy.context.view_layer.objects.active
                if active and getattr(active, "mode", "OBJECT") != "OBJECT":
                    mode_result = bpy.ops.object.mode_set(mode='OBJECT')
                    if "FINISHED" not in mode_result:
                        raise RuntimeError(f"Failed to switch to OBJECT mode: {sorted(mode_result)}")

            before_counts = mesh_counts(obj)
            if before_counts["faces"] < 1:
                return {"error": f"{obj.name} has no faces to voxel remesh"}

            created_target = False
            original_target_name = obj.name
            original_target_mesh_name = obj.data.name

            if mode_key == "COPY":
                target_name = str(result_name).strip() if result_name else f"{obj.name}_VoxelRemesh"
                if not target_name:
                    return {"error": "result_name cannot be blank"}
                if bpy.data.objects.get(target_name):
                    return {"error": f"Object already exists: {target_name}. Choose a unique result_name."}
                target = obj.copy()
                target.data = obj.data.copy()
                target.name = target_name
                target.data.name = f"{target_name}_Mesh"
                if obj.users_collection:
                    for collection in obj.users_collection:
                        collection.objects.link(target)
                else:
                    bpy.context.collection.objects.link(target)
                target.matrix_world = obj.matrix_world.copy()
                created_target = True
                source_preserved = True
            else:
                target = obj
                if result_name and str(result_name).strip() and str(result_name).strip() != obj.name:
                    if bpy.data.objects.get(str(result_name).strip()):
                        return {"error": f"Object already exists: {str(result_name).strip()}"}
                    target.name = str(result_name).strip()
                    target.data.name = f"{target.name}_Mesh"
                source_preserved = False

            def cleanup_created_target():
                if created_target and target and target.name in bpy.data.objects:
                    bpy.data.objects.remove(target, do_unlink=True)

            def restore_renamed_target():
                if not created_target and target:
                    target.name = original_target_name
                    if target.data:
                        target.data.name = original_target_mesh_name

            original_material_names = [slot.material.name if slot.material else None for slot in obj.material_slots]
            original_uv_names = [layer.name for layer in obj.data.uv_layers]
            original_attribute_signature = mesh_attribute_signature(obj)
            preserve_attributes_supported = hasattr(target.data, "use_remesh_preserve_attributes")

            target.data.remesh_mode = 'VOXEL'
            target.data.remesh_voxel_size = resolved_voxel_size
            target.data.remesh_voxel_adaptivity = resolved_adaptivity
            if preserve_attributes_supported:
                target.data.use_remesh_preserve_attributes = bool(preserve_attributes)
            if hasattr(target.data, "use_remesh_preserve_volume"):
                target.data.use_remesh_preserve_volume = bool(preserve_volume)
            if hasattr(target.data, "use_remesh_fix_poles"):
                target.data.use_remesh_fix_poles = bool(fix_poles)

            try:
                ensure_object_mode()
                select_result = bpy.ops.object.select_all(action='DESELECT')
                if "FINISHED" not in select_result:
                    raise RuntimeError(f"Failed to clear object selection: {sorted(select_result)}")
                target.select_set(True)
                bpy.context.view_layer.objects.active = target
                voxel_result = bpy.ops.object.voxel_remesh()
                if "FINISHED" not in voxel_result:
                    raise RuntimeError(f"Failed to voxel remesh mesh: {sorted(voxel_result)}")
            except Exception as operator_error:
                cleanup_created_target()
                restore_renamed_target()
                return {"error": f"Failed to voxel remesh mesh: {str(operator_error)}"}

            target.data.update()
            after_counts = mesh_counts(target)
            result_material_names = [slot.material.name if slot.material else None for slot in target.material_slots]
            result_uv_names = [layer.name for layer in target.data.uv_layers]
            result_attribute_signature = mesh_attribute_signature(target)
            materials_preserved = result_material_names == original_material_names
            uv_layers_preserved = result_uv_names == original_uv_names
            attributes_preserved = (
                preserve_attributes_supported
                and bool(preserve_attributes)
                and all(attribute in result_attribute_signature for attribute in original_attribute_signature)
            )

            return {
                "success": True,
                "source_object": original_source_name,
                "result_object": target.name,
                "mode": mode_key,
                "source_preserved": source_preserved,
                "voxel_size": resolved_voxel_size,
                "adaptivity": resolved_adaptivity,
                "preserve_attributes": bool(preserve_attributes),
                "preserve_attributes_supported": preserve_attributes_supported,
                "preserve_volume": bool(preserve_volume),
                "fix_poles": bool(fix_poles),
                "before_counts": before_counts,
                "after_counts": after_counts,
                "materials_preserved": materials_preserved,
                "uv_layers_preserved": uv_layers_preserved,
                "attributes_preserved": attributes_preserved,
                "original_attribute_signature": original_attribute_signature,
                "result_attribute_signature": result_attribute_signature,
                "material_slots": result_material_names,
                "uv_layers": result_uv_names,
                "next_safe_action": "inspect_retopology_readiness then validate_mesh_geometry before decimation, QuadriFlow, rigging, or export",
            }
        except Exception as e:
            return {"error": f"Failed to voxel remesh mesh: {str(e)}"}

    def quadriflow_remesh_mesh(
        self,
        name,
        result_name=None,
        mode="COPY",
        preserve_source=True,
        target_mode=None,
        target_faces=4000,
        target_ratio=None,
        target_edge_length=None,
        use_mesh_symmetry=True,
        preserve_sharp=False,
        preserve_boundary=False,
        preserve_attributes=True,
        smooth_normals=False,
        seed=0,
    ):
        """QuadriFlow remesh a mesh object into quad-dominant topology, preserving the source by default."""
        try:
            obj = bpy.data.objects.get(str(name))
            if not obj:
                return {"error": f"Object not found: {name}"}
            if obj.type != "MESH":
                return {"error": f"{obj.name} is not a mesh (type: {obj.type})"}
            original_source_name = obj.name

            mode_key = str(mode or ("COPY" if preserve_source else "REPLACE")).strip().upper()
            if preserve_source is False:
                mode_key = "REPLACE"
            if mode_key not in {"COPY", "REPLACE"}:
                return {"error": "mode must be COPY or REPLACE"}

            requested_target_mode = str(target_mode).strip().upper() if target_mode is not None else None
            if requested_target_mode and requested_target_mode != "FACES":
                return {"error": "Only target_faces/FACES mode is currently exposed for QuadriFlow because RATIO and EDGE density modes were not stable enough in the validated latest stable Blender 5.1.2 runtime"}
            if target_ratio is not None or target_edge_length is not None:
                return {"error": "Only target_faces/FACES mode is currently exposed for QuadriFlow because RATIO and EDGE density modes were not stable enough in the validated latest stable Blender 5.1.2 runtime"}
            resolved_target_mode = "FACES"

            def mesh_counts(target):
                mesh = target.data
                quad_faces = sum(1 for polygon in mesh.polygons if len(polygon.vertices) == 4)
                return {
                    "vertices": len(mesh.vertices),
                    "edges": len(mesh.edges),
                    "faces": len(mesh.polygons),
                    "quad_faces": quad_faces,
                    "triangle_faces": sum(1 for polygon in mesh.polygons if len(polygon.vertices) == 3),
                    "ngon_faces": sum(1 for polygon in mesh.polygons if len(polygon.vertices) > 4),
                    "uv_layers": len(mesh.uv_layers),
                    "material_slots": len(target.material_slots),
                }

            def mesh_attribute_signature(target):
                attributes = getattr(target.data, "attributes", None)
                if not attributes:
                    return []
                signature = []
                for attribute in attributes:
                    attribute_name = str(attribute.name)
                    if attribute_name.startswith(".") or attribute_name in {"position", "sharp_face"}:
                        continue
                    signature.append((
                        attribute_name,
                        str(getattr(attribute, "data_type", "")),
                        str(getattr(attribute, "domain", "")),
                    ))
                return sorted(signature)

            def ensure_object_mode():
                active = bpy.context.view_layer.objects.active
                if active and getattr(active, "mode", "OBJECT") != "OBJECT":
                    mode_result = bpy.ops.object.mode_set(mode='OBJECT')
                    if "FINISHED" not in mode_result:
                        raise RuntimeError(f"Failed to switch to OBJECT mode: {sorted(mode_result)}")

            before_counts = mesh_counts(obj)
            if before_counts["faces"] < 1:
                return {"error": f"{obj.name} has no faces to QuadriFlow remesh"}

            warnings = []
            resolved_target_faces = 4000

            try:
                resolved_target_faces = int(target_faces)
            except (TypeError, ValueError):
                return {"error": "target_faces must be an integer of at least 1"}
            if resolved_target_faces < 1:
                return {"error": "target_faces must be an integer of at least 1"}
            if resolved_target_faces > before_counts["faces"] * 4:
                warnings.append("target_faces is much higher than the current face count; QuadriFlow may add substantial geometry")

            try:
                resolved_seed = int(seed)
            except (TypeError, ValueError):
                return {"error": "seed must be a non-negative integer"}
            if resolved_seed < 0:
                return {"error": "seed must be a non-negative integer"}

            created_target = False
            original_target_name = obj.name
            original_target_mesh_name = obj.data.name

            if mode_key == "COPY":
                target_name = str(result_name).strip() if result_name else f"{obj.name}_QuadriFlow"
                if not target_name:
                    return {"error": "result_name cannot be blank"}
                if bpy.data.objects.get(target_name):
                    return {"error": f"Object already exists: {target_name}. Choose a unique result_name."}
                target = obj.copy()
                target.data = obj.data.copy()
                target.name = target_name
                target.data.name = f"{target_name}_Mesh"
                if obj.users_collection:
                    for collection in obj.users_collection:
                        collection.objects.link(target)
                else:
                    bpy.context.collection.objects.link(target)
                target.matrix_world = obj.matrix_world.copy()
                created_target = True
                source_preserved = True
            else:
                target = obj
                if result_name and str(result_name).strip() and str(result_name).strip() != obj.name:
                    if bpy.data.objects.get(str(result_name).strip()):
                        return {"error": f"Object already exists: {str(result_name).strip()}"}
                    target.name = str(result_name).strip()
                    target.data.name = f"{target.name}_Mesh"
                source_preserved = False

            def cleanup_created_target():
                if created_target and target and target.name in bpy.data.objects:
                    bpy.data.objects.remove(target, do_unlink=True)

            def restore_renamed_target():
                if not created_target and target:
                    target.name = original_target_name
                    if target.data:
                        target.data.name = original_target_mesh_name

            original_material_names = [slot.material.name if slot.material else None for slot in obj.material_slots]
            original_uv_names = [layer.name for layer in obj.data.uv_layers]
            original_attribute_signature = mesh_attribute_signature(obj)

            try:
                ensure_object_mode()
                select_result = bpy.ops.object.select_all(action='DESELECT')
                if "FINISHED" not in select_result:
                    raise RuntimeError(f"Failed to clear object selection: {sorted(select_result)}")
                target.select_set(True)
                bpy.context.view_layer.objects.active = target
                quadriflow_result = bpy.ops.object.quadriflow_remesh(
                    use_mesh_symmetry=bool(use_mesh_symmetry),
                    use_preserve_sharp=bool(preserve_sharp),
                    use_preserve_boundary=bool(preserve_boundary),
                    preserve_attributes=bool(preserve_attributes),
                    smooth_normals=bool(smooth_normals),
                    mode=resolved_target_mode,
                    target_faces=resolved_target_faces,
                    seed=resolved_seed,
                )
                if "FINISHED" not in quadriflow_result:
                    raise RuntimeError(f"Failed to QuadriFlow remesh mesh: {sorted(quadriflow_result)}")
            except Exception as operator_error:
                cleanup_created_target()
                restore_renamed_target()
                return {"error": f"Failed to QuadriFlow remesh mesh: {str(operator_error)}"}

            target.data.update()
            after_counts = mesh_counts(target)
            result_material_names = [slot.material.name if slot.material else None for slot in target.material_slots]
            result_uv_names = [layer.name for layer in target.data.uv_layers]
            result_attribute_signature = mesh_attribute_signature(target)
            materials_preserved = result_material_names == original_material_names
            uv_layers_preserved = all(layer_name in result_uv_names for layer_name in original_uv_names)
            attributes_preserved = (
                bool(preserve_attributes)
                and all(attribute in result_attribute_signature for attribute in original_attribute_signature)
            )

            return {
                "success": True,
                "source_object": original_source_name,
                "result_object": target.name,
                "mode": mode_key,
                "source_preserved": source_preserved,
                "target_mode": resolved_target_mode,
                "target_faces": resolved_target_faces,
                "use_mesh_symmetry": bool(use_mesh_symmetry),
                "preserve_sharp": bool(preserve_sharp),
                "preserve_boundary": bool(preserve_boundary),
                "preserve_attributes": bool(preserve_attributes),
                "smooth_normals": bool(smooth_normals),
                "seed": resolved_seed,
                "before_counts": before_counts,
                "after_counts": after_counts,
                "quad_faces_after": after_counts["quad_faces"],
                "materials_preserved": materials_preserved,
                "uv_layers_preserved": uv_layers_preserved,
                "attributes_preserved": attributes_preserved,
                "original_attribute_signature": original_attribute_signature,
                "result_attribute_signature": result_attribute_signature,
                "material_slots": result_material_names,
                "uv_layers": result_uv_names,
                "warnings": warnings,
                "next_safe_action": "inspect_retopology_readiness then validate_mesh_geometry before rigging, animation, subdivision, or export",
            }
        except Exception as e:
            return {"error": f"Failed to QuadriFlow remesh mesh: {str(e)}"}

    def inspect_modifier_constraint_stack(self, names=None, include_empty=False):
        """Inspect modifier and constraint stacks without mutating objects."""
        try:
            if names is None:
                requested_names = []
            elif isinstance(names, str):
                requested_names = [part.strip() for part in names.split(",") if part.strip()]
            elif isinstance(names, (list, tuple)):
                requested_names = [str(name).strip() for name in names if str(name).strip()]
            else:
                return {"error": "names must be an array of object names, a comma-separated string, or omitted"}

            if isinstance(include_empty, str):
                include_empty = include_empty.strip().lower() in {"true", "1", "yes", "y"}
            else:
                include_empty = bool(include_empty)
            if requested_names:
                objects = []
                missing_objects = []
                for name in requested_names:
                    obj = bpy.data.objects.get(name)
                    if obj:
                        objects.append(obj)
                    else:
                        missing_objects.append(name)
            else:
                objects = list(bpy.context.scene.objects)
                missing_objects = []

            reports = []
            issues = []

            for obj in objects:
                if not include_empty and len(obj.modifiers) == 0 and len(obj.constraints) == 0:
                    continue

                modifier_reports = []
                for index, mod in enumerate(obj.modifiers):
                    modifier_report = {
                        "index": index,
                        "name": mod.name,
                        "type": mod.type,
                        "show_viewport": bool(getattr(mod, "show_viewport", True)),
                        "show_render": bool(getattr(mod, "show_render", True)),
                        "show_expanded": bool(getattr(mod, "show_expanded", False)),
                        "is_active": getattr(obj.modifiers, "active", None) == mod,
                    }

                    if hasattr(mod, "levels"):
                        modifier_report["levels"] = int(getattr(mod, "levels", 0))
                    if hasattr(mod, "render_levels"):
                        modifier_report["render_levels"] = int(getattr(mod, "render_levels", 0))
                    if hasattr(mod, "width"):
                        modifier_report["width"] = float(getattr(mod, "width", 0.0))
                    if hasattr(mod, "segments"):
                        modifier_report["segments"] = int(getattr(mod, "segments", 0))
                    if hasattr(mod, "operation"):
                        modifier_report["operation"] = str(getattr(mod, "operation", ""))
                    if hasattr(mod, "solver"):
                        modifier_report["solver"] = str(getattr(mod, "solver", ""))
                    if hasattr(mod, "object"):
                        target = getattr(mod, "object", None)
                        modifier_report["target_object"] = target.name if target else None
                    if mod.type == "BOOLEAN":
                        operand_type = str(getattr(mod, "operand_type", "OBJECT"))
                        target_object = getattr(mod, "object", None)
                        target_collection = getattr(mod, "collection", None)
                        modifier_report["operand_type"] = operand_type
                        modifier_report["target_object"] = target_object.name if target_object else None
                        modifier_report["target_collection"] = target_collection.name if target_collection else None

                        if operand_type == "COLLECTION":
                            if target_collection is None:
                                issues.append({
                                    "severity": "error",
                                    "code": "missing_boolean_collection_target",
                                    "object": obj.name,
                                    "modifier": mod.name,
                                    "message": f"Boolean collection modifier '{mod.name}' on '{obj.name}' has no target collection.",
                                })
                        elif target_object is None:
                            issues.append({
                                "severity": "error",
                                "code": "missing_boolean_target",
                                "object": obj.name,
                                "modifier": mod.name,
                                "message": f"Boolean object modifier '{mod.name}' on '{obj.name}' has no target object.",
                            })

                    if mod.type == "SUBSURF" and int(getattr(mod, "levels", 0)) > 2:
                        issues.append({
                            "severity": "warn",
                            "code": "subsurf_viewport_high",
                            "object": obj.name,
                            "modifier": mod.name,
                            "message": f"SubSurf modifier '{mod.name}' on '{obj.name}' has viewport levels above 2.",
                        })

                    modifier_reports.append(modifier_report)

                constraint_reports = []
                for index, constraint in enumerate(obj.constraints):
                    target = getattr(constraint, "target", None)
                    constraint_report = {
                        "index": index,
                        "name": constraint.name,
                        "type": constraint.type,
                        "target": target.name if target else None,
                        "subtarget": str(getattr(constraint, "subtarget", "")),
                        "influence": float(getattr(constraint, "influence", 1.0)),
                        "mute": bool(getattr(constraint, "mute", False)),
                        "owner_space": str(getattr(constraint, "owner_space", "")),
                        "target_space": str(getattr(constraint, "target_space", "")),
                    }

                    needs_target = constraint.type in {
                        "CHILD_OF",
                        "COPY_LOCATION",
                        "COPY_ROTATION",
                        "COPY_SCALE",
                        "COPY_TRANSFORMS",
                        "DAMPED_TRACK",
                        "LIMIT_DISTANCE",
                        "LOCKED_TRACK",
                        "TRACK_TO",
                        "STRETCH_TO",
                        "SHRINKWRAP",
                    }
                    if needs_target and target is None:
                        issues.append({
                            "severity": "error",
                            "code": "missing_constraint_target",
                            "object": obj.name,
                            "constraint": constraint.name,
                            "message": f"Constraint '{constraint.name}' on '{obj.name}' has no target object.",
                        })

                    constraint_reports.append(constraint_report)

                reports.append({
                    "name": obj.name,
                    "type": obj.type,
                    "modifier_count": len(obj.modifiers),
                    "constraint_count": len(obj.constraints),
                    "modifiers": modifier_reports,
                    "constraints": constraint_reports,
                })

            for name in missing_objects:
                issues.append({
                    "severity": "error",
                    "code": "object_not_found",
                    "object": name,
                    "message": f"Object '{name}' was not found.",
                })

            return {
                "success": len([issue for issue in issues if issue["severity"] == "error"]) == 0,
                "object_count": len(reports),
                "missing_objects": missing_objects,
                "objects": reports,
                "issues": issues,
                "next_safe_action": "inspect issues before modifying stacks" if issues else "safe to add, reorder, apply, or remove stack entries as needed",
            }
        except Exception as e:
            return {"error": f"Failed to inspect modifier/constraint stack: {str(e)}"}

    def inspect_rigging_data(self, names=None, include_vertex_groups=True, max_bones=120, max_objects=120):
        """Inspect armatures, bones, vertex groups, and Armature modifiers without mutating the scene."""
        try:
            def normalize_names(value):
                if value is None:
                    return None
                if isinstance(value, str):
                    return [part.strip() for part in value.split(",") if part.strip()]
                if isinstance(value, (list, tuple)):
                    return [str(name).strip() for name in value if str(name).strip()]
                return []

            requested_names = normalize_names(names)
            missing_names = []
            if requested_names is not None:
                objects = []
                for obj_name in list(dict.fromkeys(requested_names)):
                    obj = bpy.data.objects.get(obj_name)
                    if obj:
                        objects.append(obj)
                    else:
                        missing_names.append(obj_name)
            else:
                objects = [
                    obj for obj in bpy.context.scene.objects
                    if obj.type == "ARMATURE"
                    or len(getattr(obj, "vertex_groups", [])) > 0
                    or any(getattr(mod, "type", "") == "ARMATURE" for mod in getattr(obj, "modifiers", []))
                ][:max(1, int(max_objects))]

            armature_reports = []
            mesh_reports = []
            issues = []

            max_bone_count = max(1, int(max_bones))
            for obj in objects:
                if obj.type == "ARMATURE":
                    bones = []
                    for index, bone in enumerate(obj.data.bones):
                        if index >= max_bone_count:
                            break
                        bones.append({
                            "name": bone.name,
                            "parent": bone.parent.name if bone.parent else None,
                            "children": [child.name for child in bone.children],
                            "use_deform": bool(getattr(bone, "use_deform", False)),
                            "head_local": list(bone.head_local),
                            "tail_local": list(bone.tail_local),
                        })

                    pose_bones = []
                    pose = getattr(obj, "pose", None)
                    if pose:
                        for index, pose_bone in enumerate(pose.bones):
                            if index >= max_bone_count:
                                break
                            pose_bones.append({
                                "name": pose_bone.name,
                                "rotation_mode": str(getattr(pose_bone, "rotation_mode", "")),
                                "constraint_count": len(getattr(pose_bone, "constraints", [])),
                                "custom_shape": pose_bone.custom_shape.name if getattr(pose_bone, "custom_shape", None) else None,
                            })

                    armature_reports.append({
                        "name": obj.name,
                        "bone_count": len(obj.data.bones),
                        "pose_bone_count": len(pose.bones) if pose else 0,
                        "bones_truncated": len(obj.data.bones) > max_bone_count,
                        "bones": bones,
                        "pose_bones": pose_bones,
                    })

                armature_modifiers = []
                for mod in getattr(obj, "modifiers", []):
                    if getattr(mod, "type", "") != "ARMATURE":
                        continue
                    target = getattr(mod, "object", None)
                    if target is None:
                        issues.append({
                            "code": "missing_armature_target",
                            "object": obj.name,
                            "modifier": mod.name,
                            "message": f"Armature modifier '{mod.name}' on '{obj.name}' has no target armature.",
                        })
                    armature_modifiers.append({
                        "name": mod.name,
                        "show_viewport": bool(getattr(mod, "show_viewport", True)),
                        "show_render": bool(getattr(mod, "show_render", True)),
                        "target_armature": target.name if target else None,
                        "use_vertex_groups": bool(getattr(mod, "use_vertex_groups", False)),
                        "use_bone_envelopes": bool(getattr(mod, "use_bone_envelopes", False)),
                    })

                vertex_group_reports = []
                if include_vertex_groups and hasattr(obj, "vertex_groups"):
                    for group in obj.vertex_groups:
                        vertex_group_reports.append({
                            "name": group.name,
                            "index": int(group.index),
                            "lock_weight": bool(getattr(group, "lock_weight", False)),
                        })

                if armature_modifiers or vertex_group_reports:
                    mesh_reports.append({
                        "name": obj.name,
                        "type": obj.type,
                        "vertex_group_count": len(getattr(obj, "vertex_groups", [])),
                        "vertex_groups": vertex_group_reports,
                        "armature_modifiers": armature_modifiers,
                    })

            return {
                "success": True,
                "armature_count": len(armature_reports),
                "mesh_count": len(mesh_reports),
                "missing_objects": missing_names,
                "armatures": armature_reports,
                "meshes": mesh_reports,
                "issues": issues,
                "next_safe_action": "use inspect_modifier_constraint_stack before adding constraints or changing rigging modifiers",
            }
        except Exception as e:
            return {"error": f"Failed to inspect rigging data: {str(e)}"}

    def inspect_weight_paint_readiness(self, names=None, max_objects=80, max_vertices_sample=5000, max_influences=4, weight_sum_tolerance=0.05):
        """Inspect mesh vertex weights and armature/group alignment before weight painting or skinning changes."""
        try:
            def normalize_names(value):
                if value is None:
                    return None
                if isinstance(value, str):
                    return [part.strip() for part in value.split(",") if part.strip()]
                if isinstance(value, (list, tuple)):
                    return [str(name).strip() for name in value if str(name).strip()]
                return []

            requested_names = normalize_names(names)
            missing_names = []
            if requested_names is not None:
                objects = []
                for obj_name in list(dict.fromkeys(requested_names)):
                    obj = bpy.data.objects.get(obj_name)
                    if obj:
                        objects.append(obj)
                    else:
                        missing_names.append(obj_name)
            else:
                objects = [
                    obj for obj in bpy.context.scene.objects
                    if obj.type == "MESH"
                    and (
                        len(getattr(obj, "vertex_groups", [])) > 0
                        or any(getattr(mod, "type", "") == "ARMATURE" for mod in getattr(obj, "modifiers", []))
                    )
                ][:max(1, int(max_objects))]

            sample_limit = max(1, int(max_vertices_sample))
            max_allowed_influences = max(1, int(max_influences))
            tolerance = max(0.0, float(weight_sum_tolerance))
            reports = []
            issues = []

            for obj in objects:
                if obj.type != "MESH":
                    issues.append({
                        "severity": "warning",
                        "code": "not_a_mesh",
                        "object": obj.name,
                        "message": f"Object '{obj.name}' is {obj.type}, not a mesh.",
                    })
                    continue

                vertex_groups = list(getattr(obj, "vertex_groups", []))
                vertex_group_names = {group.name for group in vertex_groups}
                locked_vertex_groups = [group.name for group in vertex_groups if bool(getattr(group, "lock_weight", False))]

                armature_modifiers = []
                deform_bone_names = set()
                for mod in getattr(obj, "modifiers", []):
                    if getattr(mod, "type", "") != "ARMATURE":
                        continue
                    target = getattr(mod, "object", None)
                    invalid_target = target is None or target.type != "ARMATURE"
                    if target and target.type == "ARMATURE":
                        deform_bones = [
                            bone.name for bone in target.data.bones
                            if bool(getattr(bone, "use_deform", False))
                        ]
                        deform_bone_names.update(deform_bones)
                    else:
                        deform_bones = []
                        issues.append({
                            "severity": "warning",
                            "code": "invalid_armature_target",
                            "object": obj.name,
                            "modifier": mod.name,
                            "message": f"Armature modifier '{mod.name}' on '{obj.name}' has no valid armature target.",
                        })
                    armature_modifiers.append({
                        "name": mod.name,
                        "target_armature": target.name if target else None,
                        "invalid_target": invalid_target,
                        "deform_bone_count": len(deform_bones),
                        "use_vertex_groups": bool(getattr(mod, "use_vertex_groups", False)),
                        "show_viewport": bool(getattr(mod, "show_viewport", True)),
                        "show_render": bool(getattr(mod, "show_render", True)),
                    })

                groups_without_deform_bones = sorted(vertex_group_names - deform_bone_names) if deform_bone_names else sorted(vertex_group_names)
                deform_bones_without_groups = sorted(deform_bone_names - vertex_group_names)

                unweighted_vertices = 0
                over_influenced_vertices = 0
                abnormal_weight_sum_vertices = 0
                total_influences = 0
                max_seen_influences = 0
                sampled_count = 0
                group_index_to_name = {group.index: group.name for group in vertex_groups}

                for vertex in itertools.islice(obj.data.vertices, sample_limit):
                    sampled_count += 1
                    positive_weights = [
                        group.weight for group in vertex.groups
                        if getattr(group, "weight", 0.0) > 0.000001
                        and (
                            not deform_bone_names
                            or group_index_to_name.get(group.group) in deform_bone_names
                        )
                    ]
                    influence_count = len(positive_weights)
                    weight_sum = sum(positive_weights)
                    total_influences += influence_count
                    max_seen_influences = max(max_seen_influences, influence_count)
                    if influence_count == 0:
                        unweighted_vertices += 1
                    if influence_count > max_allowed_influences:
                        over_influenced_vertices += 1
                    if influence_count > 0 and abs(weight_sum - 1.0) > tolerance:
                        abnormal_weight_sum_vertices += 1

                if len(vertex_groups) == 0:
                    issues.append({
                        "severity": "warning",
                        "code": "no_vertex_groups",
                        "object": obj.name,
                        "message": f"Mesh '{obj.name}' has no vertex groups for skinning weights.",
                    })
                if armature_modifiers and len(deform_bones_without_groups) > 0:
                    issues.append({
                        "severity": "warning",
                        "code": "deform_bones_without_groups",
                        "object": obj.name,
                        "message": f"Mesh '{obj.name}' is missing vertex groups for {len(deform_bones_without_groups)} deform bone(s).",
                    })
                if unweighted_vertices > 0:
                    issues.append({
                        "severity": "warning",
                        "code": "unweighted_vertices",
                        "object": obj.name,
                        "message": f"Mesh '{obj.name}' has {unweighted_vertices} unweighted sampled vertex/vertices.",
                    })
                if over_influenced_vertices > 0:
                    issues.append({
                        "severity": "warning",
                        "code": "over_influenced_vertices",
                        "object": obj.name,
                        "message": f"Mesh '{obj.name}' has {over_influenced_vertices} sampled vertex/vertices over {max_allowed_influences} influences.",
                    })
                if abnormal_weight_sum_vertices > 0:
                    issues.append({
                        "severity": "warning",
                        "code": "abnormal_weight_sum_vertices",
                        "object": obj.name,
                        "message": f"Mesh '{obj.name}' has {abnormal_weight_sum_vertices} sampled weighted vertex/vertices outside weight sum tolerance {tolerance}.",
                    })

                reports.append({
                    "name": obj.name,
                    "vertex_count": len(obj.data.vertices),
                    "sampled_vertex_count": sampled_count,
                    "vertex_group_count": len(vertex_groups),
                    "locked_vertex_group_count": len(locked_vertex_groups),
                    "locked_vertex_groups": locked_vertex_groups,
                    "armature_modifier_count": len(armature_modifiers),
                    "armature_modifiers": armature_modifiers,
                    "deform_bone_count": len(deform_bone_names),
                    "groups_matching_deform_bones": sorted(vertex_group_names & deform_bone_names),
                    "groups_without_deform_bones": groups_without_deform_bones,
                    "deform_bones_without_groups": deform_bones_without_groups,
                    "unweighted_vertices": unweighted_vertices,
                    "unweighted_vertex_ratio": (unweighted_vertices / sampled_count) if sampled_count else 0,
                    "over_influenced_vertices": over_influenced_vertices,
                    "max_influences_per_vertex": max_seen_influences,
                    "average_influences_per_vertex": (total_influences / sampled_count) if sampled_count else 0,
                    "abnormal_weight_sum_vertices": abnormal_weight_sum_vertices,
                    "weight_sum_tolerance": tolerance,
                    "vertices_truncated": len(obj.data.vertices) > sample_limit,
                })

            return {
                "success": True,
                "mesh_count": len(reports),
                "missing_objects": missing_names,
                "meshes": reports,
                "issues": issues,
                "next_safe_action": "fix reported weight/vertex-group issues before weight painting or skinning edits" if issues else "safe to proceed with bounded weight-paint or skinning operations",
            }
        except Exception as e:
            return {"error": f"Failed to inspect weight paint readiness: {str(e)}"}

    def normalize_vertex_group_weights(
        self,
        names=None,
        max_influences=4,
        prune_threshold=0.0001,
        preserve_locked=True,
        only_deform_bone_groups=True,
        max_vertices=200000,
    ):
        """Normalize and prune mesh vertex group weights for named meshes without generating Python scripts."""
        try:
            if isinstance(names, str):
                requested_names = [part.strip() for part in names.split(",") if part.strip()]
            elif isinstance(names, (list, tuple)):
                requested_names = [str(name).strip() for name in names if str(name).strip()]
            else:
                requested_names = []
            requested_names = list(dict.fromkeys(requested_names))
            if not requested_names:
                return {"error": "normalize_vertex_group_weights requires one or more mesh names"}

            max_allowed_influences = max(1, int(max_influences))
            threshold = max(0.0, float(prune_threshold))
            vertex_limit = max(1, int(max_vertices))
            preserve_locked = bool(preserve_locked)
            only_deform_bone_groups = bool(only_deform_bone_groups)

            reports = []
            issues = []
            missing_objects = []

            for name in requested_names:
                obj = bpy.data.objects.get(name)
                if not obj:
                    missing_objects.append(name)
                    issues.append({
                        "severity": "error",
                        "code": "object_not_found",
                        "object": name,
                        "message": f"Object '{name}' was not found.",
                    })
                    continue
                if obj.type != "MESH":
                    issues.append({
                        "severity": "error",
                        "code": "not_a_mesh",
                        "object": obj.name,
                        "message": f"Object '{obj.name}' is {obj.type}, not a mesh.",
                    })
                    continue

                vertex_groups = list(getattr(obj, "vertex_groups", []))
                if not vertex_groups:
                    issues.append({
                        "severity": "warning",
                        "code": "no_vertex_groups",
                        "object": obj.name,
                        "message": f"Mesh '{obj.name}' has no vertex groups to normalize.",
                    })
                    reports.append({
                        "name": obj.name,
                        "vertex_count": len(obj.data.vertices),
                        "processed_vertices": 0,
                        "changed_vertices": 0,
                        "removed_assignments": 0,
                        "normalized_assignments": 0,
                    })
                    continue

                group_by_index = {group.index: group for group in vertex_groups}
                deform_bone_names = set()
                for mod in getattr(obj, "modifiers", []):
                    if getattr(mod, "type", "") != "ARMATURE":
                        continue
                    target = getattr(mod, "object", None)
                    if target and target.type == "ARMATURE":
                        deform_bone_names.update(
                            bone.name for bone in target.data.bones
                            if bool(getattr(bone, "use_deform", False))
                        )

                if only_deform_bone_groups and deform_bone_names:
                    eligible_group_indices = {
                        group.index for group in vertex_groups
                        if group.name in deform_bone_names
                    }
                else:
                    eligible_group_indices = {group.index for group in vertex_groups}

                processed_vertices = 0
                changed_vertices = 0
                removed_assignments = 0
                normalized_assignments = 0
                locked_overweight_vertices = 0

                for vertex in itertools.islice(obj.data.vertices, vertex_limit):
                    processed_vertices += 1
                    existing = [
                        (entry.group, float(entry.weight))
                        for entry in vertex.groups
                        if entry.group in eligible_group_indices
                    ]
                    if not existing:
                        continue

                    locked_entries = []
                    editable_entries = []
                    for group_index, weight in existing:
                        group = group_by_index.get(group_index)
                        if not group:
                            continue
                        if preserve_locked and bool(getattr(group, "lock_weight", False)):
                            locked_entries.append((group_index, weight))
                        elif weight > threshold:
                            editable_entries.append((group_index, weight))

                    editable_entries.sort(key=lambda item: item[1], reverse=True)
                    remaining_slots = max(0, max_allowed_influences - len(locked_entries))
                    kept_editable = editable_entries[:remaining_slots]
                    kept_indices = {group_index for group_index, _ in locked_entries + kept_editable}

                    locked_sum = sum(weight for _, weight in locked_entries)
                    editable_sum = sum(weight for _, weight in kept_editable)
                    if locked_sum > 1.0:
                        locked_overweight_vertices += 1
                        remaining_weight = 0.0
                    else:
                        remaining_weight = max(0.0, 1.0 - locked_sum)

                    vertex_changed = False
                    for group_index, _weight in existing:
                        group = group_by_index.get(group_index)
                        if not group or group_index in kept_indices or (preserve_locked and bool(getattr(group, "lock_weight", False))):
                            continue
                        try:
                            group.remove([vertex.index])
                            removed_assignments += 1
                            vertex_changed = True
                        except RuntimeError:
                            pass

                    if editable_sum > 0 and remaining_weight > 0:
                        for group_index, weight in kept_editable:
                            group = group_by_index.get(group_index)
                            if not group:
                                continue
                            normalized_weight = weight / editable_sum * remaining_weight
                            group.add([vertex.index], normalized_weight, "REPLACE")
                            normalized_assignments += 1
                            vertex_changed = True

                    if vertex_changed:
                        changed_vertices += 1

                if locked_overweight_vertices > 0:
                    issues.append({
                        "severity": "warning",
                        "code": "locked_weights_exceed_one",
                        "object": obj.name,
                        "message": f"Mesh '{obj.name}' has {locked_overweight_vertices} sampled vertex/vertices where locked group weights exceed 1.0.",
                    })

                reports.append({
                    "name": obj.name,
                    "vertex_count": len(obj.data.vertices),
                    "processed_vertices": processed_vertices,
                    "vertices_truncated": len(obj.data.vertices) > vertex_limit,
                    "eligible_group_count": len(eligible_group_indices),
                    "deform_bone_group_filter_active": bool(only_deform_bone_groups and deform_bone_names),
                    "max_influences": max_allowed_influences,
                    "prune_threshold": threshold,
                    "preserve_locked": preserve_locked,
                    "changed_vertices": changed_vertices,
                    "removed_assignments": removed_assignments,
                    "normalized_assignments": normalized_assignments,
                    "locked_overweight_vertices": locked_overweight_vertices,
                })

            return {
                "success": len([issue for issue in issues if issue.get("severity") == "error"]) == 0,
                "object_count": len(reports),
                "missing_objects": missing_objects,
                "objects": reports,
                "issues": issues,
                "next_safe_action": "run inspect_weight_paint_readiness to verify normalized weights before further rigging edits",
            }
        except Exception as e:
            return {"error": f"Failed to normalize vertex group weights: {str(e)}"}

    def _ensure_rigify_enabled(self):
        """Enable Blender's bundled Rigify addon when needed."""
        import addon_utils

        _loaded_default, loaded_state = addon_utils.check("rigify")
        if not loaded_state:
            bpy.ops.preferences.addon_enable(module="rigify")
        return "rigify" in bpy.context.preferences.addons

    def inspect_edit_bone_alignment(self, armature_name, bone_names=None, max_bones=80):
        """Inspect edit-bone head, tail, and roll alignment for one armature."""
        previous_active_object = bpy.context.view_layer.objects.active
        previous_selection = list(bpy.context.selected_objects)
        previous_mode = previous_active_object.mode if previous_active_object else "OBJECT"

        def restore_context():
            try:
                if bpy.context.object and bpy.context.object.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.select_all(action="DESELECT")
                for selected_object in previous_selection:
                    if selected_object.name in bpy.data.objects:
                        selected_object.select_set(True)
                if previous_active_object and previous_active_object.name in bpy.data.objects:
                    bpy.context.view_layer.objects.active = previous_active_object
                    if previous_mode != "OBJECT" and bpy.ops.object.mode_set.poll():
                        previous_active_object.select_set(True)
                        bpy.ops.object.mode_set(mode=previous_mode)
            except Exception:
                pass

        def normalize_names(value):
            if value is None:
                return None
            if isinstance(value, str):
                return [part.strip() for part in value.split(",") if part.strip()]
            if isinstance(value, (list, tuple)):
                return [str(name).strip() for name in value if str(name).strip()]
            return []

        def bone_record(edit_bone, pose_bone=None):
            return {
                "name": edit_bone.name,
                "parent": edit_bone.parent.name if edit_bone.parent else None,
                "children": [child.name for child in edit_bone.children],
                "head": [float(value) for value in edit_bone.head],
                "tail": [float(value) for value in edit_bone.tail],
                "roll": float(edit_bone.roll),
                "length": float(edit_bone.length),
                "use_connect": bool(getattr(edit_bone, "use_connect", False)),
                "use_deform": bool(getattr(edit_bone, "use_deform", False)),
                "rigify_type": str(getattr(pose_bone, "rigify_type", "")) if pose_bone else "",
            }

        try:
            armature = bpy.data.objects.get(str(armature_name))
            if not armature:
                return {"error": f"Armature object not found: {armature_name}"}
            if armature.type != "ARMATURE":
                return {"error": f"Object '{armature.name}' is type '{armature.type}', expected ARMATURE"}

            requested_names = normalize_names(bone_names)
            try:
                max_bone_count = int(max_bones)
            except (TypeError, ValueError):
                max_bone_count = 80
            max_bone_count = max(1, min(max_bone_count, 80))

            if bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
            armature.select_set(True)
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode="EDIT")

            edit_bones = armature.data.edit_bones
            requested_names_truncated = False
            if requested_names is None:
                names_to_report = [bone.name for bone in list(edit_bones)[:max_bone_count]]
            else:
                deduped_requested_names = list(dict.fromkeys(requested_names))
                requested_names_truncated = len(deduped_requested_names) > max_bone_count
                names_to_report = deduped_requested_names[:max_bone_count]

            missing_bones = []
            bones = []
            for bone_name in names_to_report:
                edit_bone = edit_bones.get(bone_name)
                if not edit_bone:
                    missing_bones.append(bone_name)
                    continue
                pose_bone = armature.pose.bones.get(bone_name) if armature.pose else None
                bones.append(bone_record(edit_bone, pose_bone))

            return {
                "success": True,
                "armature": armature.name,
                "bone_count": len(armature.data.bones),
                "reported_bone_count": len(bones),
                "bones_truncated": (
                    requested_names is None and len(armature.data.bones) > max_bone_count
                ) or requested_names_truncated,
                "missing_bones": missing_bones,
                "bones": bones,
                "next_safe_action": "set_edit_bone_alignment for explicit bone edits, then inspect_edit_bone_alignment again",
            }
        except Exception as e:
            return {"error": f"Failed to inspect edit-bone alignment: {str(e)}"}
        finally:
            restore_context()

    def set_edit_bone_alignment(self, armature_name, bones, allow_generated_target=False):
        """Set explicit edit-bone head, tail, roll, and deformation flags on one armature."""
        previous_active_object = bpy.context.view_layer.objects.active
        previous_selection = list(bpy.context.selected_objects)
        previous_mode = previous_active_object.mode if previous_active_object else "OBJECT"

        def restore_context():
            try:
                if bpy.context.object and bpy.context.object.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.select_all(action="DESELECT")
                for selected_object in previous_selection:
                    if selected_object.name in bpy.data.objects:
                        selected_object.select_set(True)
                if previous_active_object and previous_active_object.name in bpy.data.objects:
                    bpy.context.view_layer.objects.active = previous_active_object
                    if previous_mode != "OBJECT" and bpy.ops.object.mode_set.poll():
                        previous_active_object.select_set(True)
                        bpy.ops.object.mode_set(mode=previous_mode)
            except Exception:
                pass

        def coerce_bool(value, default=False):
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"true", "1", "yes", "y", "on"}
            return bool(value)

        def coerce_vector3(value, label):
            if not isinstance(value, (list, tuple)) or len(value) != 3:
                raise ValueError(f"{label} must be a 3-number array")
            vector = Vector((float(value[0]), float(value[1]), float(value[2])))
            if not all(math.isfinite(component) for component in vector):
                raise ValueError(f"{label} must contain only finite numbers")
            return vector

        def coerce_finite_float(value, label):
            number = float(value)
            if not math.isfinite(number):
                raise ValueError(f"{label} must be a finite number")
            return number

        def bone_record(edit_bone, pose_bone=None):
            return {
                "name": edit_bone.name,
                "parent": edit_bone.parent.name if edit_bone.parent else None,
                "children": [child.name for child in edit_bone.children],
                "head": [float(value) for value in edit_bone.head],
                "tail": [float(value) for value in edit_bone.tail],
                "roll": float(edit_bone.roll),
                "length": float(edit_bone.length),
                "use_connect": bool(getattr(edit_bone, "use_connect", False)),
                "use_deform": bool(getattr(edit_bone, "use_deform", False)),
                "rigify_type": str(getattr(pose_bone, "rigify_type", "")) if pose_bone else "",
            }

        try:
            armature = bpy.data.objects.get(str(armature_name))
            if not armature:
                return {"error": f"Armature object not found: {armature_name}"}
            if armature.type != "ARMATURE":
                return {"error": f"Object '{armature.name}' is type '{armature.type}', expected ARMATURE"}
            if not isinstance(bones, list) or len(bones) == 0:
                return {"error": "bones must be a non-empty array of edit-bone changes"}
            if len(bones) > 64:
                return {"error": "set_edit_bone_alignment accepts at most 64 bone changes per call"}
            if getattr(armature.data, "rigify_target_rig", None) and not coerce_bool(allow_generated_target, False):
                return {
                    "error": f"Armature '{armature.name}' already owns a generated Rigify target rig",
                    "next_safe_action": "set allow_generated_target=true only if regeneration is intended",
                }

            if bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
            armature.select_set(True)
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode="EDIT")

            edit_bones = armature.data.edit_bones
            updated = []
            errors = []

            for change in bones:
                if not isinstance(change, dict):
                    errors.append("Each bone change must be an object")
                    continue
                bone_name = str(change.get("name", "")).strip()
                if not bone_name:
                    errors.append("Each bone change requires a non-empty name")
                    continue
                edit_bone = edit_bones.get(bone_name)
                if not edit_bone:
                    errors.append(f"Edit bone not found: {bone_name}")
                    continue

                try:
                    original_head = Vector(edit_bone.head)
                    original_tail = Vector(edit_bone.tail)
                    original_roll = float(edit_bone.roll)
                    original_use_connect = bool(getattr(edit_bone, "use_connect", False))
                    original_use_deform = bool(getattr(edit_bone, "use_deform", False))
                    proposed_head = coerce_vector3(change["head"], f"{bone_name}.head") if "head" in change else Vector(edit_bone.head)
                    proposed_tail = coerce_vector3(change["tail"], f"{bone_name}.tail") if "tail" in change else Vector(edit_bone.tail)
                    proposed_roll = coerce_finite_float(change["roll"], f"{bone_name}.roll") if "roll" in change else original_roll
                    proposed_use_connect = coerce_bool(change["use_connect"], False) if "use_connect" in change else original_use_connect
                    proposed_use_deform = coerce_bool(change["use_deform"], False) if "use_deform" in change else original_use_deform
                    if (proposed_tail - proposed_head).length <= 0.000001:
                        errors.append(f"{bone_name}: zero-length bone edits are not allowed")
                        continue

                    try:
                        edit_bone.head = proposed_head
                        edit_bone.tail = proposed_tail
                        edit_bone.roll = proposed_roll
                        edit_bone.use_connect = proposed_use_connect
                        edit_bone.use_deform = proposed_use_deform
                    except Exception:
                        with suppress(Exception):
                            edit_bone.head = original_head
                            edit_bone.tail = original_tail
                            edit_bone.roll = original_roll
                            edit_bone.use_connect = original_use_connect
                            edit_bone.use_deform = original_use_deform
                        raise

                    pose_bone = armature.pose.bones.get(bone_name) if armature.pose else None
                    updated.append(bone_record(edit_bone, pose_bone))
                except Exception as change_error:
                    errors.append(f"{bone_name}: {str(change_error)}")

            return {
                "success": len(errors) == 0,
                "armature": armature.name,
                "updated_bone_count": len(updated),
                "updated_bones": updated,
                "errors": errors,
                "next_safe_action": "inspect_edit_bone_alignment then generate_rigify_rig" if len(errors) == 0 else "fix reported bone edits and retry",
            }
        except Exception as e:
            return {"error": f"Failed to set edit-bone alignment: {str(e)}"}
        finally:
            restore_context()

    def create_rigify_metarig(
        self,
        template="basic_human",
        name="Character_Metarig",
        location=None,
        rotation=None,
        scale=None,
        collection_name=None,
        replace_existing=False,
    ):
        """Create one allowlisted Rigify metarig without fitting it to a target mesh."""
        try:
            def coerce_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(value)

            resolved_replace_existing = coerce_bool(replace_existing, False)
            template_key = (
                str(template or "basic_human")
                .strip()
                .lower()
                .replace("-", "_")
                .replace(" ", "_")
            )
            template_operators = {
                "human": "armature_human_metarig_add",
                "basic_human": "armature_basic_human_metarig_add",
                "basic_quadruped": "armature_basic_quadruped_metarig_add",
                "bird": "armature_bird_metarig_add",
                "cat": "armature_cat_metarig_add",
                "horse": "armature_horse_metarig_add",
                "shark": "armature_shark_metarig_add",
                "wolf": "armature_wolf_metarig_add",
            }
            if template_key not in template_operators:
                return {
                    "error": (
                        f"Unsupported Rigify template '{template}'. Expected one of: "
                        + ", ".join(sorted(template_operators.keys()))
                    )
                }

            object_name = str(name or "Character_Metarig").strip()
            if not object_name:
                return {"error": "Metarig name must not be empty"}
            resolved_location = None
            if location is not None:
                if not isinstance(location, (list, tuple)) or len(location) != 3:
                    return {"error": "location must be a 3-number array"}
                resolved_location = tuple(float(value) for value in location)
            resolved_rotation = None
            if rotation is not None:
                if not isinstance(rotation, (list, tuple)) or len(rotation) != 3:
                    return {"error": "rotation must be a 3-number array in degrees"}
                resolved_rotation = tuple(math.radians(float(value)) for value in rotation)
            resolved_scale = None
            if scale is not None:
                if not isinstance(scale, (list, tuple)) or len(scale) != 3:
                    return {"error": "scale must be a 3-number array"}
                resolved_scale = tuple(float(value) for value in scale)
                if any(value <= 0 for value in resolved_scale):
                    return {"error": "scale values must be greater than zero"}

            existing = bpy.data.objects.get(object_name)
            if existing:
                existing_target = (
                    getattr(existing.data, "rigify_target_rig", None)
                    if existing.type == "ARMATURE"
                    else None
                )
                if not resolved_replace_existing:
                    return {
                        "error": f"Object already exists: {object_name}",
                        "next_safe_action": "choose a new metarig name or set replace_existing=true",
                    }
                if existing_target:
                    return {
                        "error": (
                            f"Metarig '{object_name}' already owns generated rig "
                            f"'{existing_target.name}' and cannot be replaced directly"
                        ),
                        "next_safe_action": "use generate_rigify_rig with regenerate_existing=true",
                    }

            if not self._ensure_rigify_enabled():
                return {"error": "Rigify could not be enabled in this Blender installation"}

            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
            operator = getattr(bpy.ops.object, template_operators[template_key], None)
            if operator is None:
                return {
                    "error": (
                        f"Rigify operator '{template_operators[template_key]}' is unavailable"
                    )
                }
            result = operator()
            if "FINISHED" not in result:
                return {
                    "error": (
                        f"Rigify metarig operator returned {sorted(result)} "
                        f"for template '{template_key}'"
                    )
                }

            metarig = bpy.context.active_object
            if not metarig or metarig.type != "ARMATURE":
                return {"error": "Rigify did not create an active armature metarig"}

            if existing:
                bpy.data.objects.remove(existing, do_unlink=True)
            metarig.name = object_name
            metarig.data.name = f"{object_name}_Data"
            if resolved_location is not None:
                metarig.location = resolved_location
            if resolved_rotation is not None:
                metarig.rotation_euler = resolved_rotation
            if resolved_scale is not None:
                metarig.scale = resolved_scale

            if collection_name:
                target_collection = bpy.data.collections.get(str(collection_name))
                if target_collection is None:
                    target_collection = bpy.data.collections.new(str(collection_name))
                    bpy.context.scene.collection.children.link(target_collection)
                for collection in list(metarig.users_collection):
                    collection.objects.unlink(metarig)
                target_collection.objects.link(metarig)

            rigify_type_count = sum(
                1 for pose_bone in metarig.pose.bones
                if bool(getattr(pose_bone, "rigify_type", ""))
            )
            return {
                "success": True,
                "metarig": metarig.name,
                "template": template_key,
                "bone_count": len(metarig.data.bones),
                "rigify_type_count": rigify_type_count,
                "collection": (
                    metarig.users_collection[0].name
                    if metarig.users_collection
                    else None
                ),
                "next_safe_action": (
                    "manually align every metarig bone inside the target mesh, "
                    "preserve slight elbow/knee bends, then run inspect_rigging_data "
                    "before generate_rigify_rig"
                ),
            }
        except Exception as e:
            return {"error": f"Failed to create Rigify metarig: {str(e)}"}

    def generate_rigify_rig(
        self,
        metarig_name,
        rig_name=None,
        hide_metarig=True,
        regenerate_existing=False,
    ):
        """Generate or explicitly regenerate a Rigify control rig from an aligned metarig."""
        try:
            def coerce_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(value)

            resolved_hide_metarig = coerce_bool(hide_metarig, True)
            resolved_regenerate = coerce_bool(regenerate_existing, False)
            metarig = bpy.data.objects.get(metarig_name)
            if not metarig:
                return {"error": f"Metarig object not found: {metarig_name}"}
            if metarig.type != "ARMATURE":
                return {
                    "error": (
                        f"Object '{metarig_name}' is type '{metarig.type}', expected ARMATURE"
                    )
                }
            if not self._ensure_rigify_enabled():
                return {"error": "Rigify could not be enabled in this Blender installation"}

            rigify_type_count = sum(
                1 for pose_bone in metarig.pose.bones
                if bool(getattr(pose_bone, "rigify_type", ""))
            )
            if rigify_type_count == 0:
                return {
                    "error": f"Armature '{metarig.name}' has no Rigify bone types",
                    "next_safe_action": "use create_rigify_metarig or configure Rigify types before generation",
                }

            existing_target = getattr(metarig.data, "rigify_target_rig", None)
            if existing_target and not resolved_regenerate:
                return {
                    "error": (
                        f"Metarig '{metarig.name}' already has generated rig "
                        f"'{existing_target.name}'"
                    ),
                    "next_safe_action": "set regenerate_existing=true only after confirming regeneration is intended",
                }

            desired_name = str(rig_name).strip() if rig_name else None
            if desired_name:
                name_collision = bpy.data.objects.get(desired_name)
                if name_collision and name_collision != existing_target:
                    return {
                        "error": f"Rig output name is already in use: {desired_name}",
                        "next_safe_action": "choose a unique rig_name",
                    }

            if bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
            metarig.hide_set(False)
            metarig.hide_viewport = False
            metarig.select_set(True)
            bpy.context.view_layer.objects.active = metarig

            result = bpy.ops.pose.rigify_generate()
            if "FINISHED" not in result:
                return {
                    "error": (
                        f"Rigify generation returned {sorted(result)} for '{metarig.name}'"
                    )
                }

            generated_rig = getattr(metarig.data, "rigify_target_rig", None)
            if not generated_rig or generated_rig.type != "ARMATURE":
                return {"error": "Rigify finished without exposing a generated target rig"}
            if desired_name:
                generated_rig.name = desired_name
                generated_rig.data.name = f"{desired_name}_Data"
            if resolved_hide_metarig:
                metarig.hide_set(True)
                metarig.hide_render = True

            deform_bone_count = sum(
                1 for bone in generated_rig.data.bones
                if bool(getattr(bone, "use_deform", False))
            )
            return {
                "success": True,
                "metarig": metarig.name,
                "rig": generated_rig.name,
                "regenerated": bool(existing_target),
                "bone_count": len(generated_rig.data.bones),
                "deform_bone_count": deform_bone_count,
                "metarig_hidden": resolved_hide_metarig,
                "next_safe_action": (
                    f"run inspect_rigging_data for '{generated_rig.name}', then use "
                    "bind_mesh_to_armature to bind the prepared target mesh"
                ),
            }
        except Exception as e:
            return {"error": f"Failed to generate Rigify rig: {str(e)}"}

    def bind_mesh_to_armature(
        self,
        mesh_name,
        armature_name,
        binding_mode="AUTOMATIC",
        replace_existing=False,
        keep_transform=True,
    ):
        """Bind one mesh to one armature using a bounded Blender parenting mode."""
        try:
            def coerce_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(value)

            resolved_replace_existing = coerce_bool(replace_existing, False)
            resolved_keep_transform = coerce_bool(keep_transform, True)
            mesh = bpy.data.objects.get(mesh_name)
            armature = bpy.data.objects.get(armature_name)
            if not mesh:
                return {"error": f"Mesh object not found: {mesh_name}"}
            if mesh.type != "MESH":
                return {"error": f"Object '{mesh_name}' is type '{mesh.type}', expected MESH"}
            if not armature:
                return {"error": f"Armature object not found: {armature_name}"}
            if armature.type != "ARMATURE":
                return {"error": f"Object '{armature_name}' is type '{armature.type}', expected ARMATURE"}
            if mesh == armature:
                return {"error": "Mesh and armature must be different objects"}

            mode = str(binding_mode or "AUTOMATIC").strip().upper()
            parent_type_by_mode = {
                "AUTOMATIC": "ARMATURE_AUTO",
                "ENVELOPE": "ARMATURE_ENVELOPE",
                "EMPTY": "ARMATURE_NAME",
                "NAME": "ARMATURE",
            }
            if mode not in parent_type_by_mode:
                return {
                    "error": (
                        f"Unsupported binding_mode '{binding_mode}'. "
                        "Expected AUTOMATIC, ENVELOPE, EMPTY, or NAME"
                    )
                }

            existing_modifiers = [
                modifier for modifier in mesh.modifiers
                if getattr(modifier, "type", "") == "ARMATURE"
            ]
            existing_armature_parent = (
                mesh.parent
                if mesh.parent and mesh.parent.type == "ARMATURE"
                else None
            )
            target_deform_bone_names = {
                bone.name for bone in armature.data.bones
                if bool(getattr(bone, "use_deform", False))
            }
            existing_deform_bone_names = set()
            for modifier in existing_modifiers:
                modifier_target = getattr(modifier, "object", None)
                if modifier_target and modifier_target.type == "ARMATURE":
                    existing_deform_bone_names.update(
                        bone.name for bone in modifier_target.data.bones
                        if bool(getattr(bone, "use_deform", False))
                    )
            if existing_armature_parent:
                existing_deform_bone_names.update(
                    bone.name for bone in existing_armature_parent.data.bones
                    if bool(getattr(bone, "use_deform", False))
                )
            existing_target_deform_groups = [
                group.name for group in mesh.vertex_groups
                if group.name in target_deform_bone_names
            ]
            creates_weights = mode in {"AUTOMATIC", "ENVELOPE", "EMPTY"}
            if (
                existing_modifiers
                or existing_armature_parent
                or (creates_weights and existing_target_deform_groups)
            ) and not resolved_replace_existing:
                return {
                    "error": (
                        f"Mesh '{mesh.name}' already has armature skinning state. "
                        "Inspect it first or set replace_existing=true explicitly."
                    ),
                    "existing_armature_modifiers": [modifier.name for modifier in existing_modifiers],
                    "existing_armature_parent": existing_armature_parent.name if existing_armature_parent else None,
                    "existing_deform_groups": existing_target_deform_groups,
                    "next_safe_action": "run inspect_rigging_data before replacing existing skinning state",
                }

            original_parent = mesh.parent
            original_parent_type = mesh.parent_type
            original_parent_bone = mesh.parent_bone
            original_world_matrix = mesh.matrix_world.copy()
            modifier_snapshots = []
            for modifier_index, modifier in enumerate(mesh.modifiers):
                if getattr(modifier, "type", "") != "ARMATURE":
                    continue
                modifier_snapshots.append({
                    "index": modifier_index,
                    "name": modifier.name,
                    "object": getattr(modifier, "object", None),
                    "vertex_group": str(getattr(modifier, "vertex_group", "")),
                    "invert_vertex_group": bool(getattr(modifier, "invert_vertex_group", False)),
                    "use_vertex_groups": bool(getattr(modifier, "use_vertex_groups", True)),
                    "use_bone_envelopes": bool(getattr(modifier, "use_bone_envelopes", False)),
                    "use_deform_preserve_volume": bool(getattr(modifier, "use_deform_preserve_volume", False)),
                    "use_multi_modifier": bool(getattr(modifier, "use_multi_modifier", False)),
                    "show_viewport": bool(getattr(modifier, "show_viewport", True)),
                    "show_render": bool(getattr(modifier, "show_render", True)),
                    "show_in_editmode": bool(getattr(modifier, "show_in_editmode", False)),
                    "show_on_cage": bool(getattr(modifier, "show_on_cage", False)),
                })
            groups_to_replace = (
                target_deform_bone_names | existing_deform_bone_names
                if creates_weights and resolved_replace_existing
                else set()
            )
            group_snapshots = {
                group.name: {
                    "lock_weight": bool(getattr(group, "lock_weight", False)),
                    "weights": [],
                }
                for group in mesh.vertex_groups
                if group.name in groups_to_replace
            }
            snapshot_group_names = {
                group.index: group.name for group in mesh.vertex_groups
                if group.name in group_snapshots
            }
            for vertex in mesh.data.vertices:
                for assignment in vertex.groups:
                    group_name = snapshot_group_names.get(assignment.group)
                    if group_name:
                        group_snapshots[group_name]["weights"].append(
                            (vertex.index, float(assignment.weight))
                        )

            removed_modifiers = []
            removed_groups = []
            try:
                if bpy.context.object and bpy.context.object.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")

                if resolved_replace_existing:
                    for modifier in list(existing_modifiers):
                        removed_modifiers.append(modifier.name)
                        mesh.modifiers.remove(modifier)
                    if existing_armature_parent:
                        mesh.parent = None
                        if resolved_keep_transform:
                            mesh.matrix_world = original_world_matrix

                    if creates_weights:
                        for group in list(mesh.vertex_groups):
                            if group.name in groups_to_replace:
                                removed_groups.append(group.name)
                                mesh.vertex_groups.remove(group)

                world_matrix = mesh.matrix_world.copy()
                bpy.ops.object.select_all(action="DESELECT")
                mesh.select_set(True)
                armature.select_set(True)
                bpy.context.view_layer.objects.active = armature
                try:
                    bpy.ops.object.parent_set(
                        type=parent_type_by_mode[mode],
                        keep_transform=resolved_keep_transform,
                    )
                    if resolved_keep_transform:
                        mesh.matrix_world = world_matrix
                except Exception:
                    for modifier in list(mesh.modifiers):
                        if getattr(modifier, "type", "") == "ARMATURE":
                            mesh.modifiers.remove(modifier)
                    for group in list(mesh.vertex_groups):
                        if group.name in target_deform_bone_names or group.name in group_snapshots:
                            mesh.vertex_groups.remove(group)
                    for snapshot in modifier_snapshots:
                        restored = mesh.modifiers.new(name=snapshot["name"], type="ARMATURE")
                        restored.object = snapshot["object"]
                        restored.vertex_group = snapshot["vertex_group"]
                        restored.invert_vertex_group = snapshot["invert_vertex_group"]
                        restored.use_vertex_groups = snapshot["use_vertex_groups"]
                        restored.use_bone_envelopes = snapshot["use_bone_envelopes"]
                        restored.use_deform_preserve_volume = snapshot["use_deform_preserve_volume"]
                        restored.use_multi_modifier = snapshot["use_multi_modifier"]
                        restored.show_viewport = snapshot["show_viewport"]
                        restored.show_render = snapshot["show_render"]
                        restored.show_in_editmode = snapshot["show_in_editmode"]
                        restored.show_on_cage = snapshot["show_on_cage"]
                        mesh.modifiers.move(len(mesh.modifiers) - 1, snapshot["index"])
                    for group_name, snapshot in group_snapshots.items():
                        restored_group = mesh.vertex_groups.new(name=group_name)
                        restored_group.lock_weight = snapshot["lock_weight"]
                        for vertex_index, weight in snapshot["weights"]:
                            restored_group.add([vertex_index], weight, "REPLACE")
                    mesh.parent = original_parent
                    if original_parent:
                        mesh.parent_type = original_parent_type
                        mesh.parent_bone = original_parent_bone
                    mesh.matrix_world = original_world_matrix
                    raise
            finally:
                if bpy.context.object and bpy.context.object.mode != "OBJECT":
                    try:
                        bpy.ops.object.mode_set(mode="OBJECT")
                    except Exception:
                        pass

            armature_modifiers = [
                modifier for modifier in mesh.modifiers
                if getattr(modifier, "type", "") == "ARMATURE"
            ]
            matching_groups = [
                group.name for group in mesh.vertex_groups
                if armature.data.bones.get(group.name)
            ]
            return {
                "success": True,
                "mesh": mesh.name,
                "armature": armature.name,
                "binding_mode": mode,
                "parent_type": parent_type_by_mode[mode],
                "parent": mesh.parent.name if mesh.parent else None,
                "armature_modifiers": [
                    {
                        "name": modifier.name,
                        "target": modifier.object.name if getattr(modifier, "object", None) else None,
                    }
                    for modifier in armature_modifiers
                ],
                "matching_vertex_group_count": len(matching_groups),
                "removed_armature_modifiers": removed_modifiers,
                "removed_deform_groups": removed_groups,
                "next_safe_action": (
                    f"run inspect_weight_paint_readiness for mesh '{mesh.name}', "
                    "then normalize_vertex_group_weights if cleanup is needed"
                ),
            }
        except Exception as e:
            return {"error": f"Failed to bind mesh to armature: {str(e)}"}

    def transfer_vertex_group_weights(
        self,
        source_name,
        target_name,
        group_names=None,
        armature_name=None,
        only_deform_bone_groups=True,
        replace_existing=True,
        max_vertices=1000000,
    ):
        """Transfer same-topology vertex group weights by vertex index."""
        try:
            def coerce_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(value)

            resolved_only_deform = coerce_bool(only_deform_bone_groups, True)
            resolved_replace_existing = coerce_bool(replace_existing, True)
            source = bpy.data.objects.get(source_name)
            target = bpy.data.objects.get(target_name)
            if not source:
                return {"error": f"Source object not found: {source_name}"}
            if source.type != "MESH":
                return {"error": f"Source object '{source_name}' is type '{source.type}', expected MESH"}
            if not target:
                return {"error": f"Target object not found: {target_name}"}
            if target.type != "MESH":
                return {"error": f"Target object '{target_name}' is type '{target.type}', expected MESH"}
            if source == target:
                return {"error": "Source and target meshes must be different objects"}

            source_vertex_count = len(source.data.vertices)
            target_vertex_count = len(target.data.vertices)
            vertex_limit = max(1, int(max_vertices))
            if source_vertex_count != target_vertex_count:
                return {
                    "error": (
                        "Source and target vertex count must match for bounded index-based transfer: "
                        f"{source_vertex_count} != {target_vertex_count}"
                    ),
                    "next_safe_action": "use a topology-aware Data Transfer workflow for meshes with different topology",
                }
            if source_vertex_count > vertex_limit:
                return {
                    "error": (
                        f"Mesh vertex count {source_vertex_count} exceeds max_vertices {vertex_limit}"
                    )
                }
            source_polygon_count = len(source.data.polygons)
            target_polygon_count = len(target.data.polygons)
            if source_polygon_count != target_polygon_count:
                return {
                    "error": (
                        "Source and target polygon count must match for bounded index-based transfer: "
                        f"{source_polygon_count} != {target_polygon_count}"
                    ),
                    "next_safe_action": "use a topology-aware Data Transfer workflow for meshes with different topology",
                }
            topology_mismatch = any(
                tuple(source_polygon.vertices) != tuple(target_polygon.vertices)
                for source_polygon, target_polygon in zip(
                    source.data.polygons,
                    target.data.polygons,
                )
            )
            if topology_mismatch:
                return {
                    "error": "Source and target indexed face topology does not match",
                    "next_safe_action": "use a topology-aware Data Transfer workflow for meshes with different topology",
                }
            if group_names is None:
                requested_group_names = [group.name for group in source.vertex_groups]
            elif isinstance(group_names, str):
                requested_group_names = [
                    part.strip() for part in group_names.split(",") if part.strip()
                ]
            elif isinstance(group_names, (list, tuple)):
                requested_group_names = [
                    str(name).strip() for name in group_names if str(name).strip()
                ]
            else:
                return {"error": "group_names must be an array, comma-separated string, or omitted"}
            requested_group_names = list(dict.fromkeys(requested_group_names))

            missing_groups = [
                name for name in requested_group_names
                if source.vertex_groups.get(name) is None
            ]
            selected_group_names = [
                name for name in requested_group_names
                if source.vertex_groups.get(name) is not None
            ]

            deform_bone_names = set()
            armature = None
            if armature_name:
                armature = bpy.data.objects.get(armature_name)
                if not armature:
                    return {"error": f"Armature object not found: {armature_name}"}
                if armature.type != "ARMATURE":
                    return {
                        "error": (
                            f"Object '{armature_name}' is type '{armature.type}', expected ARMATURE"
                        )
                    }
                deform_bone_names = {
                    bone.name for bone in armature.data.bones
                    if bool(getattr(bone, "use_deform", False))
                }
            elif resolved_only_deform:
                for modifier in source.modifiers:
                    modifier_target = getattr(modifier, "object", None)
                    if (
                        getattr(modifier, "type", "") == "ARMATURE"
                        and modifier_target
                        and modifier_target.type == "ARMATURE"
                    ):
                        armature = modifier_target
                        deform_bone_names = {
                            bone.name for bone in armature.data.bones
                            if bool(getattr(bone, "use_deform", False))
                        }
                        break

            if resolved_only_deform and not deform_bone_names:
                return {
                    "error": (
                        "No deform bones could be resolved for deform-only weight transfer"
                    ),
                    "next_safe_action": (
                        "provide armature_name or add a valid Armature modifier to the source mesh"
                    ),
                }
            if resolved_only_deform:
                selected_group_names = [
                    name for name in selected_group_names
                    if name in deform_bone_names
                ]

            if not selected_group_names:
                return {
                    "error": "No eligible source vertex groups were selected for transfer",
                    "missing_groups": missing_groups,
                    "next_safe_action": "inspect_rigging_data to verify source groups and deform bone names",
                }

            locked_target_groups = [
                name for name in selected_group_names
                if (
                    target.vertex_groups.get(name)
                    and bool(getattr(target.vertex_groups.get(name), "lock_weight", False))
                )
            ]
            if locked_target_groups:
                return {
                    "error": "One or more target vertex groups are locked",
                    "locked_target_groups": locked_target_groups,
                    "next_safe_action": "unlock the target groups explicitly before transferring weights",
                }

            source_group_index_to_name = {
                group.index: group.name for group in source.vertex_groups
                if group.name in selected_group_names
            }
            assignments_by_group = {name: [] for name in selected_group_names}
            for vertex in source.data.vertices:
                for assignment in vertex.groups:
                    group_name = source_group_index_to_name.get(assignment.group)
                    if group_name and float(assignment.weight) > 0.0:
                        assignments_by_group[group_name].append(
                            (vertex.index, float(assignment.weight))
                        )

            transferred_assignments = 0
            created_groups = []
            replaced_groups = []
            for group_name in selected_group_names:
                target_group = target.vertex_groups.get(group_name)
                if target_group and resolved_replace_existing:
                    target.vertex_groups.remove(target_group)
                    target_group = None
                    replaced_groups.append(group_name)
                if target_group is None:
                    target_group = target.vertex_groups.new(name=group_name)
                    created_groups.append(group_name)

                for vertex_index, weight in assignments_by_group[group_name]:
                    target_group.add([vertex_index], weight, "REPLACE")
                    transferred_assignments += 1

            return {
                "success": True,
                "source": source.name,
                "target": target.name,
                "armature": armature.name if armature else None,
                "vertex_count": source_vertex_count,
                "transferred_group_count": len(selected_group_names),
                "transferred_groups": selected_group_names,
                "transferred_assignments": transferred_assignments,
                "created_groups": created_groups,
                "replaced_groups": replaced_groups,
                "missing_source_groups": missing_groups,
                "deform_bone_filter_active": bool(
                    resolved_only_deform and deform_bone_names
                ),
                "next_safe_action": (
                    f"run inspect_weight_paint_readiness for mesh '{target.name}', "
                    "then normalize_vertex_group_weights if cleanup is needed"
                ),
            }
        except Exception as e:
            return {"error": f"Failed to transfer vertex group weights: {str(e)}"}

    def project_vertex_group_weights(
        self,
        source_name,
        target_name,
        group_names=None,
        armature_name=None,
        only_deform_bone_groups=True,
        replace_existing=True,
        mapping="POLYINTERP_NEAREST",
        use_max_distance=False,
        max_distance=1.0,
        mix_mode="REPLACE",
        mix_factor=1.0,
    ):
        """Project vertex group weights across different topology using Blender Data Transfer."""
        try:
            def coerce_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(value)

            def parse_group_names(raw_group_names):
                if raw_group_names is None:
                    return None
                if isinstance(raw_group_names, str):
                    return [part.strip() for part in raw_group_names.split(",") if part.strip()]
                if isinstance(raw_group_names, (list, tuple)):
                    return [str(name).strip() for name in raw_group_names if str(name).strip()]
                raise ValueError("group_names must be an array, comma-separated string, or omitted")

            def coerce_finite_float(value, label, minimum=None, maximum=None):
                try:
                    parsed = float(value)
                except Exception:
                    raise ValueError(f"{label} must be a finite number")
                if not math.isfinite(parsed):
                    raise ValueError(f"{label} must be a finite number")
                if minimum is not None and parsed < minimum:
                    raise ValueError(f"{label} must be greater than or equal to {minimum}")
                if maximum is not None and parsed > maximum:
                    raise ValueError(f"{label} must be less than or equal to {maximum}")
                return parsed

            source = bpy.data.objects.get(source_name)
            target = bpy.data.objects.get(target_name)
            if not source:
                return {"error": f"Source object not found: {source_name}"}
            if source.type != "MESH":
                return {"error": f"Source object '{source_name}' is type '{source.type}', expected MESH"}
            if not target:
                return {"error": f"Target object not found: {target_name}"}
            if target.type != "MESH":
                return {"error": f"Target object '{target_name}' is type '{target.type}', expected MESH"}
            if source == target:
                return {"error": "Source and target meshes must be different objects"}
            if not source.vertex_groups:
                return {
                    "error": f"Source mesh '{source.name}' has no vertex groups to project",
                    "next_safe_action": "bind or weight-paint the source mesh before projection",
                }

            valid_mappings = {
                "NEAREST",
                "EDGE_NEAREST",
                "EDGEINTERP_NEAREST",
                "POLY_NEAREST",
                "POLYINTERP_NEAREST",
                "POLYINTERP_VNORPROJ",
            }
            resolved_mapping = str(mapping or "POLYINTERP_NEAREST").strip().upper()
            if resolved_mapping not in valid_mappings:
                return {
                    "error": f"Unsupported Data Transfer vertex mapping: {mapping}",
                    "supported_mappings": sorted(valid_mappings),
                }

            valid_mix_modes = {"REPLACE", "ABOVE_THRESHOLD", "BELOW_THRESHOLD", "MIX", "ADD", "SUB", "MUL"}
            resolved_mix_mode = str(mix_mode or "REPLACE").strip().upper()
            if resolved_mix_mode not in valid_mix_modes:
                return {
                    "error": f"Unsupported Data Transfer mix mode: {mix_mode}",
                    "supported_mix_modes": sorted(valid_mix_modes),
                }

            resolved_only_deform = coerce_bool(only_deform_bone_groups, True)
            resolved_replace_existing = coerce_bool(replace_existing, True)
            resolved_use_max_distance = coerce_bool(use_max_distance, False)
            resolved_max_distance = coerce_finite_float(max_distance, "max_distance", 0.0)
            resolved_mix_factor = coerce_finite_float(mix_factor, "mix_factor", 0.0, 1.0)

            requested_group_names = parse_group_names(group_names)
            if requested_group_names is None:
                requested_group_names = [group.name for group in source.vertex_groups]
            requested_group_names = list(dict.fromkeys(requested_group_names))

            missing_groups = [
                name for name in requested_group_names
                if source.vertex_groups.get(name) is None
            ]
            selected_group_names = [
                name for name in requested_group_names
                if source.vertex_groups.get(name) is not None
            ]

            deform_bone_names = set()
            armature = None
            if armature_name:
                armature = bpy.data.objects.get(armature_name)
                if not armature:
                    return {"error": f"Armature object not found: {armature_name}"}
                if armature.type != "ARMATURE":
                    return {
                        "error": (
                            f"Object '{armature_name}' is type '{armature.type}', expected ARMATURE"
                        )
                    }
                deform_bone_names = {
                    bone.name for bone in armature.data.bones
                    if bool(getattr(bone, "use_deform", False))
                }
            elif resolved_only_deform:
                for modifier in source.modifiers:
                    modifier_target = getattr(modifier, "object", None)
                    if (
                        getattr(modifier, "type", "") == "ARMATURE"
                        and modifier_target
                        and modifier_target.type == "ARMATURE"
                    ):
                        armature = modifier_target
                        deform_bone_names = {
                            bone.name for bone in armature.data.bones
                            if bool(getattr(bone, "use_deform", False))
                        }
                        break

            if resolved_only_deform:
                if not deform_bone_names:
                    return {
                        "error": "No deform bones could be resolved for deform-only weight projection",
                        "next_safe_action": (
                            "provide armature_name, add a valid Armature modifier to the source mesh, "
                            "or disable only_deform_bone_groups explicitly"
                        ),
                    }
                selected_group_names = [
                    name for name in selected_group_names
                    if name in deform_bone_names
                ]

            if not selected_group_names:
                return {
                    "error": "No eligible source vertex groups were selected for projection",
                    "missing_groups": missing_groups,
                    "next_safe_action": "inspect_rigging_data to verify source groups and deform bone names",
                }

            locked_target_groups = [
                name for name in selected_group_names
                if (
                    target.vertex_groups.get(name)
                    and bool(getattr(target.vertex_groups.get(name), "lock_weight", False))
                )
            ]
            if locked_target_groups:
                return {
                    "error": "One or more target vertex groups are locked",
                    "locked_target_groups": locked_target_groups,
                    "next_safe_action": "unlock the target groups explicitly before projecting weights",
                }

            group_snapshots = {}
            for group_name in selected_group_names:
                target_group = target.vertex_groups.get(group_name)
                if not target_group:
                    continue
                weights = []
                for vertex in target.data.vertices:
                    for assignment in vertex.groups:
                        if assignment.group == target_group.index:
                            weights.append((vertex.index, float(assignment.weight)))
                            break
                group_snapshots[group_name] = {
                    "lock_weight": bool(getattr(target_group, "lock_weight", False)),
                    "weights": weights,
                }

            previous_active = bpy.context.view_layer.objects.active
            previous_selection = [obj for obj in bpy.context.selected_objects]
            previous_source_active_index = source.vertex_groups.active_index if source.vertex_groups else -1
            previous_target_active_index = target.vertex_groups.active_index if target.vertex_groups else -1
            created_groups = []
            replaced_groups = []
            projected_groups = []
            transfer_modifier = None
            transfer_modifier_name = None

            def restore_existing_groups():
                for group_name in selected_group_names:
                    existing_group = target.vertex_groups.get(group_name)
                    if existing_group:
                        target.vertex_groups.remove(existing_group)
                for group_name, snapshot in group_snapshots.items():
                    restored_group = target.vertex_groups.new(name=group_name)
                    restored_group.lock_weight = snapshot["lock_weight"]
                    for vertex_index, weight in snapshot["weights"]:
                        restored_group.add([vertex_index], weight, "REPLACE")

            try:
                if bpy.context.object and bpy.context.object.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.select_all(action="DESELECT")
                target.select_set(True)
                bpy.context.view_layer.objects.active = target

                for group_name in selected_group_names:
                    source_group = source.vertex_groups.get(group_name)
                    if not source_group:
                        continue
                    target_group = target.vertex_groups.get(group_name)
                    if target_group and resolved_replace_existing:
                        target.vertex_groups.remove(target_group)
                        target_group = None
                        replaced_groups.append(group_name)
                    if target_group is None:
                        target_group = target.vertex_groups.new(name=group_name)
                        created_groups.append(group_name)

                    source.vertex_groups.active_index = source_group.index
                    target.vertex_groups.active_index = target_group.index
                    transfer_modifier = target.modifiers.new(
                        f"ViperMesh Project Weights {group_name}",
                        "DATA_TRANSFER",
                    )
                    transfer_modifier_name = transfer_modifier.name
                    transfer_modifier.object = source
                    transfer_modifier.use_object_transform = True
                    transfer_modifier.use_vert_data = True
                    transfer_modifier.data_types_verts = {"VGROUP_WEIGHTS"}
                    transfer_modifier.vert_mapping = resolved_mapping
                    # Blender 5.1 exposes live vertex-group names through this dynamic enum.
                    transfer_modifier.layers_vgroup_select_src = group_name
                    transfer_modifier.layers_vgroup_select_dst = "NAME"
                    transfer_modifier.mix_mode = resolved_mix_mode
                    transfer_modifier.mix_factor = resolved_mix_factor
                    transfer_modifier.use_max_distance = resolved_use_max_distance
                    if resolved_use_max_distance:
                        transfer_modifier.max_distance = resolved_max_distance
                    bpy.ops.object.modifier_apply(modifier=transfer_modifier_name)
                    transfer_modifier = None
                    transfer_modifier_name = None
                    projected_groups.append(group_name)
            except Exception:
                if transfer_modifier_name and target.modifiers.get(transfer_modifier_name):
                    target.modifiers.remove(transfer_modifier)
                restore_existing_groups()
                raise
            finally:
                if transfer_modifier_name and target.modifiers.get(transfer_modifier_name):
                    target.modifiers.remove(transfer_modifier)
                if previous_source_active_index >= 0 and previous_source_active_index < len(source.vertex_groups):
                    source.vertex_groups.active_index = previous_source_active_index
                if previous_target_active_index >= 0 and previous_target_active_index < len(target.vertex_groups):
                    target.vertex_groups.active_index = previous_target_active_index
                bpy.ops.object.select_all(action="DESELECT")
                for obj in previous_selection:
                    if obj.name in bpy.data.objects:
                        obj.select_set(True)
                if previous_active and previous_active.name in bpy.data.objects:
                    bpy.context.view_layer.objects.active = previous_active

            projected_assignments = 0
            for group_name in projected_groups:
                target_group = target.vertex_groups.get(group_name)
                if not target_group:
                    continue
                for vertex in target.data.vertices:
                    for assignment in vertex.groups:
                        if assignment.group == target_group.index and float(assignment.weight) > 0.0:
                            projected_assignments += 1
                            break

            return {
                "success": True,
                "source": source.name,
                "target": target.name,
                "armature": armature.name if armature else None,
                "mapping": resolved_mapping,
                "mix_mode": resolved_mix_mode,
                "mix_factor": resolved_mix_factor,
                "use_max_distance": resolved_use_max_distance,
                "max_distance": resolved_max_distance if resolved_use_max_distance else None,
                "projected_group_count": len(projected_groups),
                "projected_groups": projected_groups,
                "projected_assignments": projected_assignments,
                "created_groups": created_groups,
                "replaced_groups": replaced_groups,
                "missing_source_groups": missing_groups,
                "deform_bone_filter_active": bool(
                    resolved_only_deform and deform_bone_names
                ),
                "next_safe_action": (
                    f"run inspect_weight_paint_readiness for mesh '{target.name}', "
                    "then normalize_vertex_group_weights if cleanup is needed"
                ),
            }
        except Exception as e:
            return {"error": f"Failed to project vertex group weights: {str(e)}"}

    def inspect_pose_deformation(
        self,
        names=None,
        baseline_frame=None,
        stress_frames=None,
        max_objects=20,
        max_vertices_sample=10000,
        max_edges_sample=20000,
        edge_ratio_threshold=2.0,
        displacement_epsilon=0.0001,
    ):
        """Inspect evaluated rigged meshes across frames without changing persistent scene data."""
        scene = bpy.context.scene
        original_frame = scene.frame_current
        original_subframe = scene.frame_subframe
        reports = []
        try:
            def parse_names(raw_names):
                if raw_names is None:
                    return []
                if isinstance(raw_names, str):
                    return [part.strip() for part in raw_names.split(",") if part.strip()]
                if isinstance(raw_names, (list, tuple)):
                    return [str(name).strip() for name in raw_names if str(name).strip()]
                raise ValueError("names must be an array of mesh object names, a comma-separated string, or omitted")

            def parse_frames(raw_frames):
                if raw_frames is None:
                    return [int(scene.frame_current)]
                if isinstance(raw_frames, (int, float)):
                    return [int(raw_frames)]
                if isinstance(raw_frames, str):
                    raw_frames = [part.strip() for part in raw_frames.split(",") if part.strip()]
                if not isinstance(raw_frames, (list, tuple)):
                    raise ValueError("stress_frames must be an array of frame numbers, a comma-separated string, or omitted")
                frames = []
                for value in raw_frames:
                    frame = int(value)
                    if frame not in frames:
                        frames.append(frame)
                if not frames:
                    raise ValueError("stress_frames must contain at least one frame")
                return frames[:24]

            requested_names = parse_names(names)
            baseline_frame = int(scene.frame_start if baseline_frame is None else baseline_frame)
            stress_frames = parse_frames(stress_frames)
            if baseline_frame in stress_frames:
                return {
                    "success": False,
                    "error": "baseline_frame must differ from every stress frame",
                    "baseline_frame": baseline_frame,
                    "stress_frames": stress_frames,
                }
            max_objects = max(1, min(int(max_objects), 20))
            max_vertices_sample = max(1, min(int(max_vertices_sample), 50000))
            max_edges_sample = max(1, min(int(max_edges_sample), 100000))
            edge_ratio_threshold = max(1.0, min(float(edge_ratio_threshold), 100.0))
            displacement_epsilon = max(0.0, float(displacement_epsilon))

            if requested_names:
                if len(requested_names) != len(set(requested_names)):
                    return {"success": False, "error": "names must not contain duplicates"}
                if len(requested_names) > max_objects:
                    return {
                        "success": False,
                        "error": f"names exceeds max_objects ({max_objects})",
                    }
                missing = [name for name in requested_names if bpy.data.objects.get(name) is None]
                if missing:
                    return {
                        "error": "Objects not found",
                        "missing_names": missing,
                        "original_frame": original_frame,
                    }
                objects = [bpy.data.objects[name] for name in requested_names]
                invalid = [obj.name for obj in objects if obj.type != "MESH"]
                if invalid:
                    return {
                        "error": "Pose deformation inspection only supports mesh objects",
                        "invalid_names": invalid,
                        "original_frame": original_frame,
                    }
            else:
                objects = [
                    obj for obj in scene.objects
                    if obj.type == "MESH" and any(mod.type == "ARMATURE" for mod in obj.modifiers)
                ][:max_objects]

            if not objects:
                return {
                    "success": False,
                    "error": "No rigged mesh objects found",
                    "baseline_frame": baseline_frame,
                    "stress_frames": stress_frames,
                    "original_frame": original_frame,
                }

            def valid_armature_modifiers(obj):
                return [
                    modifier for modifier in obj.modifiers
                    if (
                        modifier.type == "ARMATURE"
                        and modifier.show_viewport
                        and modifier.object is not None
                        and modifier.object.type == "ARMATURE"
                    )
                ]

            invalid_rigged_meshes = [
                obj.name for obj in objects if not valid_armature_modifiers(obj)
            ]
            if invalid_rigged_meshes:
                return {
                    "success": False,
                    "error": "Every inspected mesh needs an enabled Armature modifier with a valid armature target",
                    "invalid_rigged_meshes": invalid_rigged_meshes,
                }

            estimated_work = (
                len(objects)
                * len(stress_frames)
                * (max_vertices_sample + max_edges_sample)
            )
            if estimated_work > MAX_POSE_DEFORMATION_WORK:
                return {
                    "success": False,
                    "error": "Requested pose deformation inspection exceeds the bounded work budget",
                    "estimated_work": estimated_work,
                    "max_work": MAX_POSE_DEFORMATION_WORK,
                }

            depsgraph = bpy.context.evaluated_depsgraph_get()

            def evaluated_snapshot(obj):
                evaluated = obj.evaluated_get(depsgraph)
                mesh = evaluated.to_mesh()
                try:
                    vertices = [
                        tuple(vertex.co)
                        for vertex in itertools.islice(mesh.vertices, max_vertices_sample)
                    ]
                    edges = [
                        tuple(edge.vertices)
                        for edge in itertools.islice(mesh.edges, max_edges_sample)
                    ]
                    return {
                        "vertex_count": len(mesh.vertices),
                        "edge_count": len(mesh.edges),
                        "vertices": vertices,
                        "edges": edges,
                    }
                finally:
                    evaluated.to_mesh_clear()

            scene.frame_set(baseline_frame)
            bpy.context.view_layer.update()
            baselines = {obj.name: evaluated_snapshot(obj) for obj in objects}

            threshold_failure_count = 0
            reports_by_name = {
                obj.name: {
                    "name": obj.name,
                    "baseline_vertex_count": baselines[obj.name]["vertex_count"],
                    "baseline_edge_count": baselines[obj.name]["edge_count"],
                    "sampled_vertices_truncated": (
                        baselines[obj.name]["vertex_count"] > len(baselines[obj.name]["vertices"])
                    ),
                    "sampled_edges_truncated": (
                        baselines[obj.name]["edge_count"] > len(baselines[obj.name]["edges"])
                    ),
                    "frames": [],
                }
                for obj in objects
            }
            for frame in stress_frames:
                scene.frame_set(frame)
                bpy.context.view_layer.update()
                for obj in objects:
                    baseline = baselines[obj.name]
                    current = evaluated_snapshot(obj)
                    topology_changed = (
                        current["vertex_count"] != baseline["vertex_count"]
                        or current["edge_count"] != baseline["edge_count"]
                    )
                    invalid_coordinate_count = 0
                    deformed_vertex_count = 0
                    displacement_total = 0.0
                    max_displacement = 0.0
                    compared_vertices = min(len(baseline["vertices"]), len(current["vertices"]))
                    for index in range(compared_vertices):
                        base_co = baseline["vertices"][index]
                        current_co = current["vertices"][index]
                        if not all(math.isfinite(value) for value in current_co):
                            invalid_coordinate_count += 1
                            continue
                        displacement = math.sqrt(sum(
                            (current_co[axis] - base_co[axis]) ** 2 for axis in range(3)
                        ))
                        displacement_total += displacement
                        max_displacement = max(max_displacement, displacement)
                        if displacement > displacement_epsilon:
                            deformed_vertex_count += 1

                    outlier_edge_ratio_count = 0
                    max_symmetric_edge_ratio = 1.0
                    compared_edges = 0
                    if not topology_changed:
                        for edge_index, (start, end) in enumerate(baseline["edges"]):
                            if edge_index >= len(current["edges"]) or current["edges"][edge_index] != (start, end):
                                topology_changed = True
                                break
                            if start >= compared_vertices or end >= compared_vertices:
                                continue
                            base_length = math.dist(baseline["vertices"][start], baseline["vertices"][end])
                            current_length = math.dist(current["vertices"][start], current["vertices"][end])
                            if base_length <= 1e-12:
                                continue
                            compared_edges += 1
                            if current_length <= 1e-12:
                                ratio = edge_ratio_threshold + 1.0
                            else:
                                ratio = max(
                                    current_length / base_length,
                                    base_length / current_length,
                                )
                            max_symmetric_edge_ratio = max(max_symmetric_edge_ratio, ratio)
                            if ratio > edge_ratio_threshold:
                                outlier_edge_ratio_count += 1

                    threshold_failed = (
                        topology_changed
                        or invalid_coordinate_count > 0
                        or outlier_edge_ratio_count > 0
                    )
                    if threshold_failed:
                        threshold_failure_count += 1
                    reports_by_name[obj.name]["frames"].append({
                        "frame": frame,
                        "topology_changed": topology_changed,
                        "sampled_vertex_count": compared_vertices,
                        "invalid_coordinate_count": invalid_coordinate_count,
                        "deformed_vertex_count": deformed_vertex_count,
                        "mean_displacement": (
                            displacement_total / compared_vertices if compared_vertices else 0.0
                        ),
                        "max_displacement": max_displacement,
                        "sampled_edge_count": compared_edges,
                        "outlier_edge_ratio_count": outlier_edge_ratio_count,
                        "max_symmetric_edge_ratio": max_symmetric_edge_ratio,
                        "threshold_failed": threshold_failed,
                    })
            reports = [reports_by_name[obj.name] for obj in objects]

            return {
                "success": True,
                "policy_version": "pose-deformation-v1",
                "baseline_frame": baseline_frame,
                "stress_frames": stress_frames,
                "stress_frame_count": len(stress_frames),
                "object_count": len(reports),
                "thresholds": {
                    "edge_ratio_threshold": edge_ratio_threshold,
                    "edge_ratio_mode": "symmetric",
                    "displacement_epsilon": displacement_epsilon,
                },
                "threshold_failure_count": threshold_failure_count,
                "reports": reports,
                "note": (
                    "Threshold results identify mechanical anomalies only. "
                    "The artist still decides whether deformation quality is acceptable."
                ),
            }
        except Exception as e:
            return {"error": f"Failed to inspect pose deformation: {str(e)}"}
        finally:
            scene.frame_set(original_frame, subframe=original_subframe)
            bpy.context.view_layer.update()

    def inspect_animation_data(
        self,
        names=None,
        include_materials=False,
        include_actions=True,
        max_keyframes_per_curve=12,
        max_objects=80,
        max_materials=80,
        max_actions=120,
    ):
        """Inspect timeline, actions, keyframes, drivers, and NLA data without mutating the scene."""
        try:
            def parse_names(raw_names):
                if raw_names is None:
                    return []
                if isinstance(raw_names, str):
                    return [part.strip() for part in raw_names.split(",") if part.strip()]
                if isinstance(raw_names, (list, tuple)):
                    return [str(name).strip() for name in raw_names if str(name).strip()]
                raise ValueError("names must be an array of object names, a comma-separated string, or omitted")

            def coerce_bool(value):
                if isinstance(value, str):
                    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(value)

            def coerce_positive_int(value, default_value, upper_bound=100):
                try:
                    parsed = int(value)
                    if parsed < 1:
                        return default_value
                    return min(parsed, upper_bound)
                except Exception:
                    return default_value

            def frame_number(value):
                try:
                    number = float(value)
                    if number.is_integer():
                        return int(number)
                    return number
                except Exception:
                    return value

            requested_names = parse_names(names)
            include_materials = coerce_bool(include_materials)
            include_actions = coerce_bool(include_actions)
            max_keyframes_per_curve = coerce_positive_int(max_keyframes_per_curve, 12)
            max_objects = coerce_positive_int(max_objects, 80, 500)
            max_materials = coerce_positive_int(max_materials, 80, 500)
            max_actions = coerce_positive_int(max_actions, 120, 500)

            def resolve_action_slot(action, handle):
                if action is None or handle is None:
                    return None
                try:
                    slots = list(getattr(action, "slots", []) or [])
                except Exception:
                    return None
                for candidate in slots:
                    if getattr(candidate, "handle", None) == handle:
                        return candidate
                if isinstance(handle, int) and 0 <= handle < len(slots):
                    return slots[handle]
                return None

            def get_action_slot(animation_data, action=None):
                if not animation_data:
                    return None
                slot = getattr(animation_data, "action_slot", None)
                if slot is not None and not isinstance(slot, int):
                    return slot
                handle = getattr(animation_data, "action_slot_handle", None)
                if handle is None and isinstance(slot, int):
                    handle = slot
                return resolve_action_slot(action or getattr(animation_data, "action", None), handle)

            def collect_action_fcurves(action, action_slot=None):
                if action is None:
                    return [], "none"

                channelbag_error = None
                try:
                    from bpy_extras import anim_utils

                    if action_slot is not None and hasattr(anim_utils, "action_get_channelbag_for_slot"):
                        channelbag = anim_utils.action_get_channelbag_for_slot(action, action_slot)
                        if channelbag is not None and hasattr(channelbag, "fcurves"):
                            return list(channelbag.fcurves), "channelbag"
                except Exception as exc:
                    channelbag_error = type(exc).__name__

                try:
                    legacy_fcurves = getattr(action, "fcurves", None)
                    if legacy_fcurves is not None:
                        legacy_source = "legacy_fcurves"
                        if channelbag_error:
                            legacy_source = f"legacy_fcurves_after_channelbag_{channelbag_error}"
                        return list(legacy_fcurves), legacy_source
                except Exception as exc:
                    if channelbag_error:
                        return [], f"channelbag_{channelbag_error}_legacy_{type(exc).__name__}"
                    return [], f"legacy_{type(exc).__name__}"

                if channelbag_error:
                    return [], f"channelbag_{channelbag_error}"
                return [], "unavailable"

            def summarize_fcurve(fcurve):
                keyframes = []
                for point in list(getattr(fcurve, "keyframe_points", []))[:max_keyframes_per_curve]:
                    co = getattr(point, "co", None)
                    keyframes.append({
                        "frame": frame_number(co[0]) if co is not None else None,
                        "value": float(co[1]) if co is not None else None,
                        "interpolation": str(getattr(point, "interpolation", "")),
                        "easing": str(getattr(point, "easing", "")),
                    })

                all_points = list(getattr(fcurve, "keyframe_points", []))
                first_frame = None
                last_frame = None
                if all_points:
                    frames = [float(point.co[0]) for point in all_points if getattr(point, "co", None) is not None]
                    if frames:
                        first_frame = frame_number(min(frames))
                        last_frame = frame_number(max(frames))

                modifiers = []
                for modifier in getattr(fcurve, "modifiers", []):
                    modifiers.append({
                        "type": str(getattr(modifier, "type", "")),
                        "active": bool(getattr(modifier, "active", True)),
                    })

                return {
                    "data_path": str(getattr(fcurve, "data_path", "")),
                    "array_index": int(getattr(fcurve, "array_index", 0)),
                    "keyframe_count": len(all_points),
                    "first_frame": first_frame,
                    "last_frame": last_frame,
                    "sample_keyframes": keyframes,
                    "truncated_keyframes": max(0, len(all_points) - len(keyframes)),
                    "modifier_count": len(modifiers),
                    "modifiers": modifiers,
                }

            def summarize_drivers(animation_data):
                if not animation_data:
                    return []
                drivers = []
                for driver_curve in getattr(animation_data, "drivers", []) or []:
                    driver = getattr(driver_curve, "driver", None)
                    variables = []
                    if driver is not None:
                        for variable in getattr(driver, "variables", []) or []:
                            variables.append({
                                "name": str(getattr(variable, "name", "")),
                                "type": str(getattr(variable, "type", "")),
                            })
                    drivers.append({
                        "data_path": str(getattr(driver_curve, "data_path", "")),
                        "array_index": int(getattr(driver_curve, "array_index", 0)),
                        "expression": str(getattr(driver, "expression", "")) if driver is not None else "",
                        "variable_count": len(variables),
                        "variables": variables,
                    })
                return drivers

            def summarize_nla(animation_data):
                if not animation_data:
                    return []
                tracks = []
                for track in getattr(animation_data, "nla_tracks", []) or []:
                    strips = []
                    for strip in getattr(track, "strips", []) or []:
                        action = getattr(strip, "action", None)
                        strips.append({
                            "name": str(getattr(strip, "name", "")),
                            "action": action.name if action else None,
                            "frame_start": frame_number(getattr(strip, "frame_start", 0)),
                            "frame_end": frame_number(getattr(strip, "frame_end", 0)),
                            "mute": bool(getattr(strip, "mute", False)),
                        })
                    tracks.append({
                        "name": track.name,
                        "mute": bool(getattr(track, "mute", False)),
                        "strip_count": len(strips),
                        "strips": strips,
                    })
                return tracks

            def action_slot_label(action_slot):
                if action_slot is None:
                    return None
                return str(getattr(action_slot, "name", getattr(action_slot, "identifier", action_slot)))

            def summarize_animation_owner(owner, owner_type, owner_name, explicit=False):
                animation_data = getattr(owner, "animation_data", None)
                if animation_data is None:
                    if explicit:
                        return {
                            "name": owner_name,
                            "type": owner_type,
                            "animated": False,
                            "issues": [{"severity": "info", "code": "no_animation_data", "message": f"{owner_name} has no animation data."}],
                        }
                    return None

                action = getattr(animation_data, "action", None)
                action_slot = get_action_slot(animation_data, action)
                fcurves, fcurve_source = collect_action_fcurves(action, action_slot)
                drivers = summarize_drivers(animation_data)
                nla_tracks = summarize_nla(animation_data)
                issues = []

                if action is not None and fcurve_source == "unavailable":
                    issues.append({
                        "severity": "warn",
                        "code": "fcurve_access_unavailable",
                        "message": f"Could not access F-curves for action '{action.name}'.",
                    })

                animated = action is not None or len(drivers) > 0 or len(nla_tracks) > 0
                if not animated and not explicit:
                    return None
                if not animated:
                    issues.append({"severity": "info", "code": "no_active_animation", "message": f"{owner_name} has animation data but no active action, drivers, or NLA tracks."})

                return {
                    "name": owner_name,
                    "type": owner_type,
                    "animated": animated,
                    "action": action.name if action else None,
                    "action_slot": action_slot_label(action_slot),
                    "fcurve_source": fcurve_source,
                    "fcurve_count": len(fcurves),
                    "fcurves": [summarize_fcurve(fcurve) for fcurve in fcurves],
                    "driver_count": len(drivers),
                    "drivers": drivers,
                    "nla_track_count": len(nla_tracks),
                    "nla_tracks": nla_tracks,
                    "issues": issues,
                }

            scene = bpy.context.scene
            timeline = {
                "frame_start": int(scene.frame_start),
                "frame_end": int(scene.frame_end),
                "frame_current": int(scene.frame_current),
                "fps": int(scene.render.fps),
                "fps_base": float(scene.render.fps_base),
            }

            missing_objects = []
            if requested_names:
                objects = []
                for name in requested_names:
                    obj = bpy.data.objects.get(name)
                    if obj:
                        objects.append(obj)
                    else:
                        missing_objects.append(name)
            else:
                scene_objects = list(bpy.context.scene.objects)
                objects = scene_objects[:max_objects]
            objects_truncated = max(0, len(list(bpy.context.scene.objects)) - len(objects)) if not requested_names else 0

            object_reports = []
            issues = []
            for obj in objects:
                report = summarize_animation_owner(obj, obj.type, obj.name, explicit=bool(requested_names))
                if report:
                    object_reports.append(report)
                    issues.extend(report.get("issues", []))

            for name in missing_objects:
                issues.append({
                    "severity": "error",
                    "code": "object_not_found",
                    "object": name,
                    "message": f"Object '{name}' was not found.",
                })

            material_reports = []
            materials_truncated = 0
            if include_materials:
                materials = list(bpy.data.materials)
                materials_truncated = max(0, len(materials) - max_materials)
                for material in materials[:max_materials]:
                    node_tree = getattr(material, "node_tree", None)
                    if node_tree is None:
                        continue
                    report = summarize_animation_owner(node_tree, "MATERIAL_NODE_TREE", material.name)
                    if report:
                        material_reports.append(report)
                        issues.extend(report.get("issues", []))

            action_reports = []
            actions_truncated = 0
            if include_actions:
                actions = list(bpy.data.actions)
                actions_truncated = max(0, len(actions) - max_actions)
                for action in actions[:max_actions]:
                    slot_reports = []
                    total_fcurves = 0
                    sources = set()
                    slots = list(getattr(action, "slots", []) or [])
                    if slots:
                        for slot in slots:
                            fcurves, fcurve_source = collect_action_fcurves(action, slot)
                            slot_reports.append({
                                "slot": action_slot_label(slot),
                                "fcurve_source": fcurve_source,
                                "fcurve_count": len(fcurves),
                            })
                            total_fcurves += len(fcurves)
                            sources.add(fcurve_source)
                        fcurve_source = "slots" if sources == {"channelbag"} else ",".join(sorted(sources))
                    else:
                        fcurves, fcurve_source = collect_action_fcurves(action, None)
                        total_fcurves = len(fcurves)
                        slot_reports = []
                    frame_range = getattr(action, "frame_range", None)
                    action_reports.append({
                        "name": action.name,
                        "users": int(getattr(action, "users", 0)),
                        "fcurve_source": fcurve_source,
                        "fcurve_count": total_fcurves,
                        "slots": slot_reports,
                        "frame_start": frame_number(frame_range[0]) if frame_range is not None else None,
                        "frame_end": frame_number(frame_range[1]) if frame_range is not None else None,
                    })

            return {
                "success": len([issue for issue in issues if issue.get("severity") == "error"]) == 0,
                "timeline": timeline,
                "limits": {
                    "max_objects": max_objects,
                    "max_materials": max_materials,
                    "max_actions": max_actions,
                    "max_keyframes_per_curve": max_keyframes_per_curve,
                },
                "object_count": len(object_reports),
                "objects": object_reports,
                "objects_truncated": objects_truncated,
                "material_count": len(material_reports),
                "materials": material_reports,
                "materials_truncated": materials_truncated,
                "action_count": len(action_reports),
                "actions": action_reports,
                "actions_truncated": actions_truncated,
                "missing_objects": missing_objects,
                "issues": issues,
                "next_safe_action": "use these keyframe, driver, and NLA details before creating or editing keyframes",
            }
        except Exception as e:
            return {"error": f"Failed to inspect animation data: {str(e)}"}

    def inspect_shape_keys(self, names=None, max_objects=80, max_shape_keys_per_object=80):
        """Inspect existing mesh shape keys without mutating the scene."""
        try:
            def parse_names(raw_names):
                if raw_names is None:
                    return []
                if isinstance(raw_names, str):
                    return [part.strip() for part in raw_names.split(",") if part.strip()]
                if isinstance(raw_names, (list, tuple)):
                    return [str(name).strip() for name in raw_names if str(name).strip()]
                raise ValueError("names must be an array of object names, a comma-separated string, or omitted")

            def coerce_positive_int(value, default_value, upper_bound=500):
                try:
                    parsed = int(value)
                    if parsed < 1:
                        return default_value
                    return min(parsed, upper_bound)
                except Exception:
                    return default_value

            requested_names = parse_names(names)
            max_objects = coerce_positive_int(max_objects, 80)
            max_shape_keys_per_object = coerce_positive_int(max_shape_keys_per_object, 80)

            if requested_names:
                objects = []
                missing_objects = []
                for name in requested_names:
                    obj = bpy.data.objects.get(name)
                    if obj:
                        objects.append(obj)
                    else:
                        missing_objects.append(name)
            else:
                scene_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
                objects = scene_meshes[:max_objects]
                missing_objects = []

            reports = []
            issues = []
            for obj in objects:
                if obj.type != "MESH":
                    issues.append({
                        "severity": "warn",
                        "code": "not_mesh",
                        "object": obj.name,
                        "message": f"Object '{obj.name}' is {obj.type}, not MESH.",
                    })
                    continue

                shape_keys = getattr(obj.data, "shape_keys", None)
                key_blocks = list(getattr(shape_keys, "key_blocks", []) or []) if shape_keys else []
                animation_data = getattr(shape_keys, "animation_data", None) if shape_keys else None
                drivers = []
                if animation_data:
                    for driver_curve in getattr(animation_data, "drivers", []) or []:
                        drivers.append({
                            "data_path": str(getattr(driver_curve, "data_path", "")),
                            "array_index": int(getattr(driver_curve, "array_index", 0)),
                        })

                shape_key_reports = []
                for key_block in key_blocks[:max_shape_keys_per_object]:
                    shape_key_reports.append({
                        "name": key_block.name,
                        "value": round(float(getattr(key_block, "value", 0.0)), 6),
                        "slider_min": round(float(getattr(key_block, "slider_min", 0.0)), 6),
                        "slider_max": round(float(getattr(key_block, "slider_max", 1.0)), 6),
                        "mute": bool(getattr(key_block, "mute", False)),
                        "vertex_count": len(getattr(key_block, "data", []) or []),
                    })

                reports.append({
                    "name": obj.name,
                    "type": obj.type,
                    "has_shape_keys": bool(shape_keys and len(key_blocks) > 0),
                    "shape_key_count": len(key_blocks),
                    "shape_keys": shape_key_reports,
                    "shape_keys_truncated": max(0, len(key_blocks) - len(shape_key_reports)),
                    "driver_count": len(drivers),
                    "drivers": drivers,
                    "animation_action": animation_data.action.name if animation_data and getattr(animation_data, "action", None) else None,
                })

            for name in missing_objects:
                issues.append({
                    "severity": "error",
                    "code": "object_not_found",
                    "object": name,
                    "message": f"Object '{name}' was not found.",
                })

            return {
                "success": len([issue for issue in issues if issue.get("severity") == "error"]) == 0,
                "object_count": len(reports),
                "objects": reports,
                "missing_objects": missing_objects,
                "objects_truncated": 0 if requested_names else max(0, len([obj for obj in bpy.context.scene.objects if obj.type == "MESH"]) - len(objects)),
                "limits": {
                    "max_objects": max_objects,
                    "max_shape_keys_per_object": max_shape_keys_per_object,
                },
                "issues": issues,
                "next_safe_action": "use extract_shape_key_to_object to materialize an editable target, create_shape_key_from_object for same-topology morph target geometry, then set_shape_key_value for values or keyframes",
            }
        except Exception as e:
            return {"error": f"Failed to inspect shape keys: {str(e)}"}

    def extract_shape_key_to_object(
        self,
        name,
        shape_key_name,
        result_name=None,
        value=1.0,
        collection_name=None,
        copy_materials=True,
        replace_existing=False,
    ):
        """Extract an existing shape key into an editable same-topology mesh object."""
        try:
            source_obj = bpy.data.objects.get(str(name))
            if source_obj is None:
                return {"error": f"Object '{name}' not found"}
            if source_obj.type != "MESH":
                return {"error": f"Object '{source_obj.name}' is {source_obj.type}, not MESH"}

            shape_keys = getattr(source_obj.data, "shape_keys", None)
            if not shape_keys or not getattr(shape_keys, "key_blocks", None):
                return {"error": f"Object '{source_obj.name}' has no shape keys"}

            shape_key_name = str(shape_key_name or "").strip()
            if not shape_key_name:
                return {"error": "shape_key_name is required"}
            if shape_key_name == "Basis":
                return {"error": "Basis shape key extraction is redundant; duplicate the object instead"}

            shape_key = shape_keys.key_blocks.get(shape_key_name)
            if shape_key is None:
                return {"error": f"Shape key '{shape_key_name}' not found on object '{source_obj.name}'"}
            basis_key = shape_keys.key_blocks.get("Basis") or shape_keys.key_blocks[0]

            def coerce_bool(raw_value, default=False):
                if raw_value is None:
                    return default
                if isinstance(raw_value, str):
                    return raw_value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(raw_value)

            resolved_value = float(value)
            copy_materials = coerce_bool(copy_materials, True)
            replace_existing = coerce_bool(replace_existing)
            result_name = str(result_name or f"{source_obj.name}_{shape_key.name}_Target").strip()
            if not result_name:
                return {"error": "result_name cannot be blank"}

            existing = bpy.data.objects.get(result_name)
            if existing is not None:
                if not replace_existing:
                    return {
                        "error": f"Object '{result_name}' already exists",
                        "object": source_obj.name,
                        "result_name": result_name,
                        "next_safe_action": "choose a different result_name or pass replace_existing=true",
                    }
                existing_mesh = existing.data if getattr(existing, "type", None) == "MESH" else None
                bpy.data.objects.remove(existing, do_unlink=True)
                if existing_mesh is not None and int(getattr(existing_mesh, "users", 0) or 0) == 0:
                    bpy.data.meshes.remove(existing_mesh)

            vertices = []
            for index, basis_point in enumerate(basis_key.data):
                basis_co = basis_point.co
                target_co = shape_key.data[index].co
                vertices.append((
                    basis_co.x + (target_co.x - basis_co.x) * resolved_value,
                    basis_co.y + (target_co.y - basis_co.y) * resolved_value,
                    basis_co.z + (target_co.z - basis_co.z) * resolved_value,
                ))
            edges = [[vertex for vertex in edge.vertices] for edge in source_obj.data.edges]
            faces = [[vertex for vertex in polygon.vertices] for polygon in source_obj.data.polygons]

            new_mesh = bpy.data.meshes.new(f"{result_name}Mesh")
            new_mesh.from_pydata(vertices, edges, faces)
            new_mesh.update()
            for source_polygon, target_polygon in zip(source_obj.data.polygons, new_mesh.polygons):
                target_polygon.material_index = int(getattr(source_polygon, "material_index", 0))
                target_polygon.use_smooth = bool(getattr(source_polygon, "use_smooth", False))

            result_obj = bpy.data.objects.new(result_name, new_mesh)
            if collection_name:
                collection = bpy.data.collections.get(str(collection_name))
                if collection is None:
                    collection = bpy.data.collections.new(str(collection_name))
                    bpy.context.scene.collection.children.link(collection)
            else:
                collection = source_obj.users_collection[0] if source_obj.users_collection else bpy.context.collection
            collection.objects.link(result_obj)
            result_obj.matrix_world = source_obj.matrix_world.copy()

            material_names = []
            if copy_materials:
                for slot in getattr(source_obj, "material_slots", []) or []:
                    material = getattr(slot, "material", None)
                    if material is not None:
                        result_obj.data.materials.append(material)
                        material_names.append(material.name)

            return {
                "success": True,
                "object": source_obj.name,
                "shape_key": shape_key.name,
                "result_name": result_obj.name,
                "value": round(resolved_value, 6),
                "vertex_count": len(vertices),
                "face_count": len(faces),
                "edge_count": len(edges),
                "collection": collection.name,
                "materials": material_names,
                "replace_existing": replace_existing,
                "next_safe_action": "edit the extracted target object, then use create_shape_key_from_object to write it back as same-topology shape-key geometry",
            }
        except Exception as e:
            return {"error": f"Failed to extract shape key to object: {str(e)}"}

    def create_shape_key_from_object(
        self,
        name,
        target_name,
        shape_key_name,
        value=0.0,
        replace_existing=False,
        slider_min=0.0,
        slider_max=1.0,
    ):
        """Create a shape key by copying coordinates from a same-topology target mesh."""
        try:
            source_obj = bpy.data.objects.get(str(name))
            if source_obj is None:
                return {"error": f"Object '{name}' not found"}
            target_obj = bpy.data.objects.get(str(target_name))
            if target_obj is None:
                return {"error": f"Target object '{target_name}' not found"}
            if source_obj.type != "MESH":
                return {"error": f"Object '{source_obj.name}' is {source_obj.type}, not MESH"}
            if target_obj.type != "MESH":
                return {"error": f"Target object '{target_obj.name}' is {target_obj.type}, not MESH"}

            shape_key_name = str(shape_key_name or "").strip()
            if not shape_key_name:
                return {"error": "shape_key_name is required"}
            if shape_key_name == "Basis":
                return {"error": "Basis shape key cannot be created or replaced"}
            slider_min = float(slider_min)
            slider_max = float(slider_max)
            if slider_min > slider_max:
                return {"error": "slider_min must be <= slider_max"}

            def coerce_bool(raw_value, default=False):
                if raw_value is None:
                    return default
                if isinstance(raw_value, str):
                    return raw_value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(raw_value)

            source_mesh = source_obj.data
            target_mesh = target_obj.data
            source_vertex_count = len(getattr(source_mesh, "vertices", []) or [])
            target_vertex_count = len(getattr(target_mesh, "vertices", []) or [])
            if source_vertex_count != target_vertex_count:
                return {
                    "error": "Shape key target must have the same vertex count and vertex order as the source mesh",
                    "object": source_obj.name,
                    "target": target_obj.name,
                    "source_vertex_count": source_vertex_count,
                    "target_vertex_count": target_vertex_count,
                    "next_safe_action": "use inspect_retopology_readiness or validate_mesh_geometry, then create a same-topology target before calling create_shape_key_from_object",
                }

            replace_existing = coerce_bool(replace_existing)
            mesh_copied = False
            source_mesh_name = getattr(source_mesh, "name", None)
            if int(getattr(source_mesh, "users", 0) or 0) > 1:
                source_obj.data = source_mesh.copy()
                source_obj.data.name = f"{source_obj.name}_ShapeKeys"
                source_mesh = source_obj.data
                mesh_copied = True

            if not getattr(source_mesh, "shape_keys", None):
                source_obj.shape_key_add(name="Basis", from_mix=False)
            shape_keys = source_mesh.shape_keys
            existing_key = shape_keys.key_blocks.get(shape_key_name)
            if existing_key is not None:
                if not replace_existing:
                    return {
                        "error": f"Shape key '{shape_key_name}' already exists on object '{source_obj.name}'",
                        "object": source_obj.name,
                        "shape_key": shape_key_name,
                        "next_safe_action": "set replace_existing=true to overwrite this non-Basis shape key, or choose a new shape_key_name",
                    }
                source_obj.shape_key_remove(existing_key)

            key_block = source_obj.shape_key_add(name=shape_key_name, from_mix=False)
            for index, target_vertex in enumerate(target_mesh.vertices):
                key_block.data[index].co = target_vertex.co

            key_block.slider_min = slider_min
            key_block.slider_max = slider_max
            key_block.value = max(slider_min, min(float(value), slider_max))

            bpy.context.view_layer.update()

            return {
                "success": True,
                "object": source_obj.name,
                "target": target_obj.name,
                "shape_key": key_block.name,
                "vertex_count": source_vertex_count,
                "value": round(float(key_block.value), 6),
                "slider_min": round(float(key_block.slider_min), 6),
                "slider_max": round(float(key_block.slider_max), 6),
                "replace_existing": replace_existing,
                "mesh_copied": mesh_copied,
                "source_mesh": source_mesh_name,
                "next_safe_action": "run inspect_shape_keys to verify created shape-key geometry, then set_shape_key_value for values or keyframes",
            }
        except Exception as e:
            return {"error": f"Failed to create shape key from object: {str(e)}"}

    def set_shape_key_properties(
        self,
        name,
        shape_key_name,
        slider_min=None,
        slider_max=None,
        mute=None,
        clamp_value=True,
    ):
        """Set bounded shape key metadata such as slider range and mute state."""
        try:
            obj = bpy.data.objects.get(str(name))
            if obj is None:
                return {"error": f"Object '{name}' not found"}
            if obj.type != "MESH":
                return {"error": f"Object '{obj.name}' is {obj.type}, not MESH"}

            mesh_data = obj.data
            shape_keys = getattr(mesh_data, "shape_keys", None)
            if not shape_keys or not getattr(shape_keys, "key_blocks", None):
                return {"error": f"Object '{obj.name}' has no shape keys"}

            shape_key = shape_keys.key_blocks.get(str(shape_key_name))
            if shape_key is None:
                return {"error": f"Shape key '{shape_key_name}' not found on object '{obj.name}'"}
            if shape_key.name == "Basis":
                return {"error": "Basis shape key properties cannot be edited"}
            if slider_min is None and slider_max is None and mute is None:
                return {"error": "Provide at least one of slider_min, slider_max, or mute"}

            def coerce_bool(raw_value, default=False):
                if raw_value is None:
                    return default
                if isinstance(raw_value, str):
                    return raw_value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(raw_value)

            target_slider_min = float(shape_key.slider_min) if slider_min is None else float(slider_min)
            target_slider_max = float(shape_key.slider_max) if slider_max is None else float(slider_max)
            if target_slider_min > target_slider_max:
                return {"error": "slider_min must be <= slider_max"}

            source_mesh_name = getattr(mesh_data, "name", None)
            mesh_copied = False
            target_shape_key_name = shape_key.name
            if int(getattr(mesh_data, "users", 0) or 0) > 1:
                obj.data = mesh_data.copy()
                obj.data.name = f"{obj.name}_ShapeKeys"
                mesh_data = obj.data
                shape_keys = getattr(mesh_data, "shape_keys", None)
                shape_key = shape_keys.key_blocks.get(target_shape_key_name) if shape_keys else None
                if shape_key is None:
                    return {"error": f"Failed to copy shared mesh data for shape key '{target_shape_key_name}'"}
                mesh_copied = True

            old_properties = {
                "slider_min": round(float(shape_key.slider_min), 6),
                "slider_max": round(float(shape_key.slider_max), 6),
                "mute": bool(getattr(shape_key, "mute", False)),
                "value": round(float(getattr(shape_key, "value", 0.0)), 6),
            }

            shape_key.slider_min = target_slider_min
            shape_key.slider_max = target_slider_max
            if mute is not None:
                shape_key.mute = coerce_bool(mute)
            clamp_value = coerce_bool(clamp_value, True)
            if clamp_value:
                shape_key.value = max(target_slider_min, min(float(shape_key.value), target_slider_max))

            bpy.context.view_layer.update()

            return {
                "success": True,
                "object": obj.name,
                "shape_key": shape_key.name,
                "old_properties": old_properties,
                "properties": {
                    "slider_min": round(float(shape_key.slider_min), 6),
                    "slider_max": round(float(shape_key.slider_max), 6),
                    "mute": bool(getattr(shape_key, "mute", False)),
                    "value": round(float(getattr(shape_key, "value", 0.0)), 6),
                },
                "clamp_value": clamp_value,
                "mesh_copied": mesh_copied,
                "source_mesh": source_mesh_name,
                "next_safe_action": "run inspect_shape_keys to verify shape-key properties before setting values or keyframes",
            }
        except Exception as e:
            return {"error": f"Failed to set shape key properties: {str(e)}"}

    def rename_shape_key(
        self,
        name,
        shape_key_name,
        new_shape_key_name,
        replace_existing=False,
    ):
        """Rename a non-Basis shape key with shared mesh data protection."""
        try:
            obj = bpy.data.objects.get(str(name))
            if obj is None:
                return {"error": f"Object '{name}' not found"}
            if obj.type != "MESH":
                return {"error": f"Object '{obj.name}' is {obj.type}, not MESH"}

            old_name = str(shape_key_name or "").strip()
            new_name = str(new_shape_key_name or "").strip()
            if not old_name:
                return {"error": "shape_key_name is required"}
            if not new_name:
                return {"error": "new_shape_key_name is required"}
            if old_name == "Basis":
                return {"error": "Basis shape key cannot be renamed"}
            if new_name == "Basis":
                return {"error": "Shape key cannot be renamed to Basis"}

            def coerce_bool(raw_value, default=False):
                if raw_value is None:
                    return default
                if isinstance(raw_value, str):
                    return raw_value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(raw_value)

            mesh_data = obj.data
            shape_keys = getattr(mesh_data, "shape_keys", None)
            if not shape_keys or not getattr(shape_keys, "key_blocks", None):
                return {"error": f"Object '{obj.name}' has no shape keys"}

            shape_key = shape_keys.key_blocks.get(old_name)
            if shape_key is None:
                return {"error": f"Shape key '{old_name}' not found on object '{obj.name}'"}
            existing_key = shape_keys.key_blocks.get(new_name)
            if existing_key is shape_key:
                return {
                    "success": True,
                    "object": obj.name,
                    "old_shape_key": old_name,
                    "shape_key": shape_key.name,
                    "changed": False,
                    "replace_existing": False,
                    "mesh_copied": False,
                    "source_mesh": getattr(mesh_data, "name", None),
                    "next_safe_action": "run inspect_shape_keys to verify renamed shape keys before setting values or keyframes",
                }
            replace_existing = coerce_bool(replace_existing)
            if existing_key is not None and not replace_existing:
                return {
                    "error": f"Shape key '{new_name}' already exists on object '{obj.name}'",
                    "object": obj.name,
                    "shape_key": old_name,
                    "new_shape_key_name": new_name,
                    "next_safe_action": "set replace_existing=true to remove the destination non-Basis shape key, or choose another new_shape_key_name",
                }
            if existing_key is not None and existing_key.name == "Basis":
                return {"error": "Basis shape key cannot be replaced"}

            source_mesh_name = getattr(mesh_data, "name", None)
            mesh_copied = False
            if int(getattr(mesh_data, "users", 0) or 0) > 1:
                obj.data = mesh_data.copy()
                obj.data.name = f"{obj.name}_ShapeKeys"
                mesh_data = obj.data
                shape_keys = getattr(mesh_data, "shape_keys", None)
                shape_key = shape_keys.key_blocks.get(old_name) if shape_keys else None
                existing_key = shape_keys.key_blocks.get(new_name) if shape_keys else None
                if shape_key is None:
                    return {"error": f"Failed to copy shared mesh data for shape key '{old_name}'"}
                mesh_copied = True

            removed_existing = False
            if existing_key is not None:
                obj.shape_key_remove(existing_key)
                removed_existing = True

            shape_key.name = new_name
            bpy.context.view_layer.update()

            return {
                "success": True,
                "object": obj.name,
                "old_shape_key": old_name,
                "shape_key": shape_key.name,
                "changed": True,
                "replace_existing": replace_existing,
                "removed_existing": removed_existing,
                "mesh_copied": mesh_copied,
                "source_mesh": source_mesh_name,
                "next_safe_action": "run inspect_shape_keys to verify renamed shape keys before setting values or keyframes",
            }
        except Exception as e:
            return {"error": f"Failed to rename shape key: {str(e)}"}

    def delete_shape_key(self, name, shape_key_name):
        """Delete a non-Basis shape key with shared mesh data protection."""
        try:
            obj = bpy.data.objects.get(str(name))
            if obj is None:
                return {"error": f"Object '{name}' not found"}
            if obj.type != "MESH":
                return {"error": f"Object '{obj.name}' is {obj.type}, not MESH"}

            target_name = str(shape_key_name or "").strip()
            if not target_name:
                return {"error": "shape_key_name is required"}
            if target_name == "Basis":
                return {"error": "Basis shape key cannot be deleted"}

            mesh_data = obj.data
            shape_keys = getattr(mesh_data, "shape_keys", None)
            if not shape_keys or not getattr(shape_keys, "key_blocks", None):
                return {"error": f"Object '{obj.name}' has no shape keys"}

            shape_key = shape_keys.key_blocks.get(target_name)
            if shape_key is None:
                return {"error": f"Shape key '{target_name}' not found on object '{obj.name}'"}

            source_mesh_name = getattr(mesh_data, "name", None)
            mesh_copied = False
            if int(getattr(mesh_data, "users", 0) or 0) > 1:
                obj.data = mesh_data.copy()
                obj.data.name = f"{obj.name}_ShapeKeys"
                mesh_data = obj.data
                shape_keys = getattr(mesh_data, "shape_keys", None)
                shape_key = shape_keys.key_blocks.get(target_name) if shape_keys else None
                if shape_key is None:
                    return {"error": f"Failed to copy shared mesh data for shape key '{target_name}'"}
                mesh_copied = True

            previous_count = len(shape_keys.key_blocks)
            obj.shape_key_remove(shape_key)
            remaining_count = len(getattr(mesh_data.shape_keys, "key_blocks", []) or []) if getattr(mesh_data, "shape_keys", None) else 0
            bpy.context.view_layer.update()

            return {
                "success": True,
                "object": obj.name,
                "deleted_shape_key": target_name,
                "shape_key_count_before": previous_count,
                "shape_key_count": remaining_count,
                "mesh_copied": mesh_copied,
                "source_mesh": source_mesh_name,
                "next_safe_action": "run inspect_shape_keys to verify deleted shape keys before setting values or keyframes",
            }
        except Exception as e:
            return {"error": f"Failed to delete shape key: {str(e)}"}

    def duplicate_shape_key(
        self,
        name,
        shape_key_name,
        new_shape_key_name,
        value=None,
        replace_existing=False,
        copy_properties=True,
    ):
        """Duplicate a non-Basis shape key by copying its coordinates."""
        try:
            obj = bpy.data.objects.get(str(name))
            if obj is None:
                return {"error": f"Object '{name}' not found"}
            if obj.type != "MESH":
                return {"error": f"Object '{obj.name}' is {obj.type}, not MESH"}

            source_name = str(shape_key_name or "").strip()
            new_name = str(new_shape_key_name or "").strip()
            if not source_name:
                return {"error": "shape_key_name is required"}
            if not new_name:
                return {"error": "new_shape_key_name is required"}
            if source_name == "Basis":
                return {"error": "Basis shape key cannot be duplicated"}
            if new_name == "Basis":
                return {"error": "Shape key cannot be duplicated to Basis"}

            def coerce_bool(raw_value, default=False):
                if raw_value is None:
                    return default
                if isinstance(raw_value, str):
                    return raw_value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(raw_value)

            mesh_data = obj.data
            shape_keys = getattr(mesh_data, "shape_keys", None)
            if not shape_keys or not getattr(shape_keys, "key_blocks", None):
                return {"error": f"Object '{obj.name}' has no shape keys"}

            source_key = shape_keys.key_blocks.get(source_name)
            if source_key is None:
                return {"error": f"Shape key '{source_name}' not found on object '{obj.name}'"}
            if source_name == new_name:
                return {"error": "shape_key_name and new_shape_key_name must be different"}
            existing_key = shape_keys.key_blocks.get(new_name)
            replace_existing = coerce_bool(replace_existing)
            copy_properties = coerce_bool(copy_properties, True)
            if existing_key is not None and not replace_existing:
                return {
                    "error": f"Shape key '{new_name}' already exists on object '{obj.name}'",
                    "object": obj.name,
                    "shape_key": source_name,
                    "new_shape_key_name": new_name,
                    "next_safe_action": "set replace_existing=true to overwrite this non-Basis shape key, or choose another new_shape_key_name",
                }
            if existing_key is not None and existing_key.name == "Basis":
                return {"error": "Basis shape key cannot be replaced"}

            source_mesh_name = getattr(mesh_data, "name", None)
            mesh_copied = False
            if int(getattr(mesh_data, "users", 0) or 0) > 1:
                obj.data = mesh_data.copy()
                obj.data.name = f"{obj.name}_ShapeKeys"
                mesh_data = obj.data
                shape_keys = getattr(mesh_data, "shape_keys", None)
                source_key = shape_keys.key_blocks.get(source_name) if shape_keys else None
                existing_key = shape_keys.key_blocks.get(new_name) if shape_keys else None
                if source_key is None:
                    return {"error": f"Failed to copy shared mesh data for shape key '{source_name}'"}
                mesh_copied = True

            removed_existing = False
            if existing_key is not None:
                obj.shape_key_remove(existing_key)
                removed_existing = True

            duplicate_key = obj.shape_key_add(name=new_name, from_mix=False)
            for index, source_point in enumerate(source_key.data):
                duplicate_key.data[index].co = source_point.co

            if copy_properties:
                duplicate_key.slider_min = float(source_key.slider_min)
                duplicate_key.slider_max = float(source_key.slider_max)
                duplicate_key.mute = bool(getattr(source_key, "mute", False))
                duplicate_key.value = float(source_key.value if value is None else value)
            else:
                duplicate_key.value = float(0.0 if value is None else value)
            duplicate_key.value = max(float(duplicate_key.slider_min), min(float(duplicate_key.value), float(duplicate_key.slider_max)))

            bpy.context.view_layer.update()

            return {
                "success": True,
                "object": obj.name,
                "source_shape_key": source_key.name,
                "shape_key": duplicate_key.name,
                "value": round(float(duplicate_key.value), 6),
                "slider_min": round(float(duplicate_key.slider_min), 6),
                "slider_max": round(float(duplicate_key.slider_max), 6),
                "replace_existing": replace_existing,
                "removed_existing": removed_existing,
                "copy_properties": copy_properties,
                "mesh_copied": mesh_copied,
                "source_mesh": source_mesh_name,
                "next_safe_action": "run inspect_shape_keys to verify duplicated shape keys before setting values or keyframes",
            }
        except Exception as e:
            return {"error": f"Failed to duplicate shape key: {str(e)}"}

    def create_shape_key_from_mix(
        self,
        name,
        new_shape_key_name,
        mix_values=None,
        value=0.0,
        replace_existing=False,
        slider_min=0.0,
        slider_max=1.0,
        restore_values=True,
    ):
        """Create a non-Basis shape key from the current or explicit shape-key value mix."""
        try:
            obj = bpy.data.objects.get(str(name))
            if obj is None:
                return {"error": f"Object '{name}' not found"}
            if obj.type != "MESH":
                return {"error": f"Object '{obj.name}' is {obj.type}, not MESH"}

            new_name = str(new_shape_key_name or "").strip()
            if not new_name:
                return {"error": "new_shape_key_name is required"}
            if new_name == "Basis":
                return {"error": "Shape key cannot be created from mix as Basis"}
            slider_min = float(slider_min)
            slider_max = float(slider_max)
            if slider_min > slider_max:
                return {"error": "slider_min must be <= slider_max"}

            def coerce_bool(raw_value, default=False):
                if raw_value is None:
                    return default
                if isinstance(raw_value, str):
                    return raw_value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(raw_value)

            mesh_data = obj.data
            shape_keys = getattr(mesh_data, "shape_keys", None)
            if not shape_keys or not getattr(shape_keys, "key_blocks", None):
                return {"error": f"Object '{obj.name}' has no shape keys"}

            key_blocks = shape_keys.key_blocks
            existing_key = key_blocks.get(new_name)
            replace_existing = coerce_bool(replace_existing)
            restore_values = coerce_bool(restore_values, True)
            if existing_key is not None and not replace_existing:
                return {
                    "error": f"Shape key '{new_name}' already exists on object '{obj.name}'",
                    "object": obj.name,
                    "new_shape_key_name": new_name,
                    "next_safe_action": "set replace_existing=true to overwrite this non-Basis shape key, or choose another new_shape_key_name",
                }
            if existing_key is not None and existing_key.name == "Basis":
                return {"error": "Basis shape key cannot be replaced"}

            normalized_mix = {}
            if isinstance(mix_values, dict):
                for raw_name, raw_value in mix_values.items():
                    key_name = str(raw_name or "").strip()
                    if not key_name:
                        return {"error": "mix_values cannot contain blank shape key names"}
                    if key_name == "Basis":
                        return {"error": "Basis shape key cannot be used as a mix source"}
                    key_block = key_blocks.get(key_name)
                    if key_block is None:
                        return {"error": f"Shape key '{key_name}' not found on object '{obj.name}'"}
                    normalized_mix[key_name] = max(float(key_block.slider_min), min(float(raw_value), float(key_block.slider_max)))

            source_mesh_name = getattr(mesh_data, "name", None)
            mesh_copied = False
            if int(getattr(mesh_data, "users", 0) or 0) > 1:
                obj.data = mesh_data.copy()
                obj.data.name = f"{obj.name}_ShapeKeys"
                mesh_data = obj.data
                shape_keys = getattr(mesh_data, "shape_keys", None)
                key_blocks = shape_keys.key_blocks if shape_keys else None
                existing_key = key_blocks.get(new_name) if key_blocks else None
                for key_name in normalized_mix:
                    if key_blocks is None or key_blocks.get(key_name) is None:
                        return {"error": f"Failed to copy shared mesh data for shape key '{key_name}'"}
                mesh_copied = True

            removed_existing = False
            if existing_key is not None:
                obj.shape_key_remove(existing_key)
                removed_existing = True

            original_values = {
                key.name: float(getattr(key, "value", 0.0))
                for key in key_blocks
                if key.name != "Basis"
            }
            original_mutes = {
                key.name: bool(getattr(key, "mute", False))
                for key in key_blocks
                if key.name != "Basis"
            }

            try:
                if normalized_mix:
                    for key in key_blocks:
                        if key.name != "Basis":
                            key.value = normalized_mix.get(key.name, 0.0)
                            if key.name in normalized_mix:
                                key.mute = False
                mixed_key = obj.shape_key_add(name=new_name, from_mix=True)
            finally:
                if restore_values:
                    for key_name, old_value in original_values.items():
                        key = key_blocks.get(key_name)
                        if key is not None:
                            key.value = old_value
                            key.mute = original_mutes.get(key_name, False)

            mixed_key.slider_min = slider_min
            mixed_key.slider_max = slider_max
            mixed_key.value = max(slider_min, min(float(value), slider_max))

            bpy.context.view_layer.update()

            return {
                "success": True,
                "object": obj.name,
                "shape_key": mixed_key.name,
                "mix_values": normalized_mix or "current",
                "value": round(float(mixed_key.value), 6),
                "slider_min": round(float(mixed_key.slider_min), 6),
                "slider_max": round(float(mixed_key.slider_max), 6),
                "replace_existing": replace_existing,
                "removed_existing": removed_existing,
                "restore_values": restore_values,
                "mesh_copied": mesh_copied,
                "source_mesh": source_mesh_name,
                "next_safe_action": "run inspect_shape_keys to verify mixed shape keys before setting values or keyframes",
            }
        except Exception as e:
            return {"error": f"Failed to create shape key from mix: {str(e)}"}

    def set_shape_key_value(
        self,
        name,
        shape_key_name,
        value,
        frame=None,
        keyframes=None,
        interpolation="BEZIER",
        clear_existing=False,
        set_scene_range=True,
    ):
        """Set or keyframe an existing mesh shape key value without arbitrary Python."""
        try:
            obj = bpy.data.objects.get(str(name))
            if obj is None:
                return {"error": f"Object '{name}' not found"}
            if obj.type != "MESH":
                return {"error": f"Object '{obj.name}' is {obj.type}, not MESH"}

            mesh_data = obj.data
            shape_keys = getattr(mesh_data, "shape_keys", None)
            if not shape_keys or not getattr(shape_keys, "key_blocks", None):
                return {"error": f"Object '{obj.name}' has no shape keys"}

            shape_key = shape_keys.key_blocks.get(str(shape_key_name))
            if shape_key is None:
                return {"error": f"Shape key '{shape_key_name}' not found on object '{obj.name}'"}
            if shape_key.name == "Basis":
                return {"error": "Basis shape key value cannot be edited"}

            def coerce_bool(raw_value, default=False):
                if raw_value is None:
                    return default
                if isinstance(raw_value, str):
                    return raw_value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(raw_value)

            def coerce_frame(raw_value):
                parsed = int(round(float(raw_value)))
                if parsed < 0:
                    raise ValueError("frame values must be >= 0")
                return parsed

            def coerce_value(raw_value):
                return max(float(shape_key.slider_min), min(float(raw_value), float(shape_key.slider_max)))

            normalized_keyframes = []
            if isinstance(keyframes, (list, tuple)) and len(keyframes) > 0:
                for index, keyframe in enumerate(keyframes):
                    if not isinstance(keyframe, dict):
                        return {"error": f"keyframes[{index}] must be an object with frame and value fields"}
                    if "frame" not in keyframe or "value" not in keyframe:
                        return {"error": f"keyframes[{index}] must include frame and value"}
                    normalized_keyframes.append({
                        "frame": coerce_frame(keyframe["frame"]),
                        "value": coerce_value(keyframe["value"]),
                    })
            elif frame is not None:
                normalized_keyframes.append({"frame": coerce_frame(frame), "value": coerce_value(value)})

            normalized_keyframes.sort(key=lambda item: item["frame"])
            target_value = coerce_value(value)
            interpolation = str(interpolation or "BEZIER").upper()
            allowed_interpolation = {"CONSTANT", "LINEAR", "BEZIER", "SINE", "QUAD", "CUBIC", "QUART", "QUINT", "EXPO", "CIRC", "BACK", "BOUNCE", "ELASTIC"}
            if interpolation not in allowed_interpolation:
                return {"error": f"Unsupported interpolation '{interpolation}'"}
            clear_existing = coerce_bool(clear_existing)
            set_scene_range = coerce_bool(set_scene_range, True)

            target_shape_key_name = shape_key.name
            data_path = shape_key.path_from_id("value")

            def resolve_action_slot(action, handle):
                if action is None or handle is None:
                    return None
                try:
                    slots = list(getattr(action, "slots", []) or [])
                except Exception:
                    return None
                for candidate in slots:
                    if getattr(candidate, "handle", None) == handle:
                        return candidate
                if isinstance(handle, int) and 0 <= handle < len(slots):
                    return slots[handle]
                return None

            def get_action_slot(animation_data, action=None):
                if not animation_data:
                    return None
                slot = getattr(animation_data, "action_slot", None)
                if slot is not None and not isinstance(slot, int):
                    return slot
                handle = getattr(animation_data, "action_slot_handle", None)
                if handle is None and isinstance(slot, int):
                    handle = slot
                return resolve_action_slot(action or getattr(animation_data, "action", None), handle)

            def collect_action_fcurves(action, action_slot=None):
                if action is None:
                    return [], None, "none"
                channelbag_error = None
                try:
                    from bpy_extras import anim_utils

                    if action_slot is not None and hasattr(anim_utils, "action_get_channelbag_for_slot"):
                        channelbag = anim_utils.action_get_channelbag_for_slot(action, action_slot)
                        if channelbag is not None and hasattr(channelbag, "fcurves"):
                            return list(channelbag.fcurves), channelbag, "channelbag"
                except Exception as exc:
                    channelbag_error = type(exc).__name__

                try:
                    legacy_fcurves = getattr(action, "fcurves", None)
                    if legacy_fcurves is not None:
                        source = "legacy_fcurves"
                        if channelbag_error:
                            source = f"legacy_fcurves_after_channelbag_{channelbag_error}"
                        return list(legacy_fcurves), action, source
                except Exception as exc:
                    if channelbag_error:
                        return [], None, f"channelbag_{channelbag_error}_legacy_{type(exc).__name__}"
                    return [], None, f"legacy_{type(exc).__name__}"

                if channelbag_error:
                    return [], None, f"channelbag_{channelbag_error}"
                return [], None, "unavailable"

            def matching_driver_paths(animation_data):
                if not animation_data:
                    return []
                matches = []
                for driver_curve in getattr(animation_data, "drivers", []) or []:
                    if getattr(driver_curve, "data_path", None) == data_path and not bool(getattr(driver_curve, "mute", False)):
                        matches.append(str(getattr(driver_curve, "data_path", "")))
                return matches

            def count_matching_action_fcurves(animation_data, action):
                if action is None:
                    return 0
                action_slot = get_action_slot(animation_data, action)
                fcurves, _fcurve_owner, _fcurve_source = collect_action_fcurves(action, action_slot)
                return sum(1 for fcurve in fcurves if getattr(fcurve, "data_path", None) == data_path)

            driver_paths = matching_driver_paths(shape_keys.animation_data)
            if driver_paths:
                return {
                    "error": f"Shape key '{target_shape_key_name}' is controlled by a driver; mute/remove the driver or bake it before setting direct values or keyframes",
                    "object": obj.name,
                    "shape_key": target_shape_key_name,
                    "driver_count": len(driver_paths),
                    "drivers": driver_paths,
                    "next_safe_action": "run inspect_shape_keys or inspect_animation_data, then mute/remove the driver or bake it before using set_shape_key_value",
                }

            action = shape_keys.animation_data.action if shape_keys.animation_data else None
            if not normalized_keyframes and not clear_existing and count_matching_action_fcurves(shape_keys.animation_data, action) > 0:
                return {
                    "error": f"Shape key '{target_shape_key_name}' already has value animation; pass keyframes or clear_existing=true before setting a static value",
                    "object": obj.name,
                    "shape_key": target_shape_key_name,
                    "next_safe_action": "run inspect_shape_keys or inspect_animation_data, then pass keyframes or clear_existing=true if replacing the animated value",
                }

            mesh_copied = False
            source_mesh_name = getattr(mesh_data, "name", None)
            if int(getattr(mesh_data, "users", 0) or 0) > 1:
                obj.data = mesh_data.copy()
                obj.data.name = f"{obj.name}_ShapeKeys"
                mesh_copied = True
                mesh_data = obj.data
                shape_keys = getattr(mesh_data, "shape_keys", None)
                shape_key = shape_keys.key_blocks.get(target_shape_key_name) if shape_keys else None
                if shape_key is None:
                    return {"error": f"Failed to copy shared mesh data for shape key '{target_shape_key_name}'"}
                data_path = shape_key.path_from_id("value")

            def ensure_single_user_action():
                animation_data = shape_keys.animation_data
                action = animation_data.action if animation_data else None
                if action is not None and int(getattr(action, "users", 0) or 0) > 1:
                    action = action.copy()
                    action.name = f"{obj.name}_{shape_key.name}_Keyframes"
                    if shape_keys.animation_data is None:
                        shape_keys.animation_data_create()
                    shape_keys.animation_data.action = action
                    return action, True
                return action, False

            action_copied = False
            if clear_existing or normalized_keyframes:
                action, action_copied = ensure_single_user_action()

            removed_fcurves = 0
            if clear_existing and action is not None:
                action_slot = get_action_slot(shape_keys.animation_data, action)
                fcurves, fcurve_owner, _fcurve_source = collect_action_fcurves(action, action_slot)
                owner_fcurves = getattr(fcurve_owner, "fcurves", None) if fcurve_owner else None
                if owner_fcurves is not None:
                    for fcurve in list(fcurves):
                        if getattr(fcurve, "data_path", None) == data_path:
                            owner_fcurves.remove(fcurve)
                            removed_fcurves += 1

            scene = bpy.context.scene
            current_frame = int(scene.frame_current)
            if normalized_keyframes:
                for keyframe in normalized_keyframes:
                    shape_key.value = keyframe["value"]
                    shape_key.keyframe_insert(data_path="value", frame=keyframe["frame"])
                target_value = normalized_keyframes[-1]["value"]
            else:
                shape_key.value = target_value

            action = shape_keys.animation_data.action if shape_keys.animation_data else None
            edited_fcurves = 0
            fcurve_source = "none"
            if normalized_keyframes and action is not None:
                action_slot = get_action_slot(shape_keys.animation_data, action)
                fcurves, _fcurve_owner, fcurve_source = collect_action_fcurves(action, action_slot)
                target_frames = {keyframe["frame"] for keyframe in normalized_keyframes}
                for fcurve in list(fcurves):
                    if getattr(fcurve, "data_path", None) != data_path:
                        continue
                    edited_fcurves += 1
                    for point in getattr(fcurve, "keyframe_points", []) or []:
                        co = getattr(point, "co", None)
                        if normalized_keyframes and (co is None or int(round(float(co[0]))) not in target_frames):
                            continue
                        point.interpolation = interpolation
                    try:
                        fcurve.update()
                    except Exception:
                        pass

            if set_scene_range and normalized_keyframes:
                scene.frame_start = min(int(scene.frame_start), normalized_keyframes[0]["frame"])
                scene.frame_end = max(int(scene.frame_end), normalized_keyframes[-1]["frame"])

            if normalized_keyframes:
                scene.frame_set(current_frame)
                bpy.context.view_layer.update()

            return {
                "success": True,
                "object": obj.name,
                "shape_key": shape_key.name,
                "value": round(float(shape_key.value), 6),
                "requested_value": round(float(value), 6),
                "slider_min": round(float(shape_key.slider_min), 6),
                "slider_max": round(float(shape_key.slider_max), 6),
                "keyframed": len(normalized_keyframes) > 0,
                "keyframes": normalized_keyframes,
                "interpolation": interpolation,
                "clear_existing": clear_existing,
                "removed_fcurves": removed_fcurves,
                "edited_fcurves": edited_fcurves,
                "fcurve_source": fcurve_source,
                "action": action.name if action else None,
                "mesh_copied": mesh_copied,
                "source_mesh": source_mesh_name,
                "action_copied": action_copied,
                "scene_range": {
                    "frame_start": int(scene.frame_start),
                    "frame_end": int(scene.frame_end),
                },
                "next_safe_action": "run inspect_shape_keys then inspect_animation_data to verify shape key values and keyframes",
            }
        except Exception as e:
            return {"error": f"Failed to set shape key value: {str(e)}"}

    def retarget_animation_clip(
        self,
        filepath,
        target_armature,
        bone_map,
        action_name,
        export_names,
        output_filepath,
        source_armature=None,
        root_motion="in_place",
        root_source_bone=None,
        frame_start=None,
        frame_end=None,
        bake_step=1,
        cleanup_imported=True,
        overwrite=False,
    ):
        """Import BVH/FBX motion, retarget it through explicit bone constraints, bake, and export a GLB candidate."""
        imported_objects = []
        created_data = {}
        source_armature_name = None
        added_constraints = []
        baked_action = None
        previous_action = None
        previous_selection = list(bpy.context.selected_objects)
        previous_active = bpy.context.view_layer.objects.active
        previous_mode = (
            previous_active.mode
            if previous_active is not None
            else "OBJECT"
        )
        scene = bpy.context.scene
        previous_frame_start = int(scene.frame_start)
        previous_frame_end = int(scene.frame_end)
        previous_frame = int(scene.frame_current)
        output_path = None
        output_backup_path = None
        exported = False
        output_existed = False
        backup_complete = False
        output_touched = False
        tracked_data = {}
        before_names = {}
        previous_pose = {}
        target_had_animation_data = False
        recovery_failed = False

        def coerce_bool(value, default=False):
            if value is None:
                return default
            if isinstance(value, str):
                return value.strip().lower() in {
                    "true",
                    "1",
                    "yes",
                    "y",
                    "on",
                }
            return bool(value)

        def cleanup_created_imports():
            nonlocal created_data, imported_objects
            if before_names:
                created_data = {
                    key: [block for block in collection if block.name not in before_names[key]]
                    for key, collection in tracked_data.items()
                }
                imported_objects = list(created_data.get("objects", []))
            for obj in list(imported_objects):
                if obj.name in bpy.data.objects:
                    bpy.data.objects.remove(obj, do_unlink=True)
            for data_name, blocks in created_data.items():
                if data_name == "objects":
                    continue
                collection = getattr(bpy.data, data_name)
                for block in list(blocks):
                    block_name = block.name
                    if (
                        block is baked_action
                        or collection.get(block_name) is None
                        or block.users > 0
                    ):
                        continue
                    collection.remove(block)

        def remove_added_constraints():
            for pose_bone, constraint in reversed(
                added_constraints
            ):
                if constraint in pose_bone.constraints.values():
                    pose_bone.constraints.remove(constraint)
            added_constraints.clear()

        def rollback():
            nonlocal baked_action
            with suppress(Exception):
                if bpy.context.object and bpy.context.object.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
            remove_added_constraints()
            target = bpy.data.objects.get(str(target_armature))
            if target is not None:
                if target_had_animation_data:
                    target.animation_data_create()
                    target.animation_data.action = previous_action
                elif previous_pose:
                    target.animation_data_clear()
            if baked_action is not None and baked_action.users == 0:
                with suppress(Exception):
                    bpy.data.actions.remove(baked_action)
            baked_action = None
            cleanup_created_imports()
            if backup_complete and output_backup_path and os.path.isfile(output_backup_path):
                os.replace(output_backup_path, output_path)
            elif output_touched and not output_existed and output_path and os.path.isfile(output_path):
                os.remove(output_path)
            elif output_backup_path and not backup_complete and os.path.isfile(output_backup_path):
                os.remove(output_backup_path)

        try:
            input_path = bpy.path.abspath(str(filepath))
            input_extension = os.path.splitext(input_path)[1].lower()
            if input_extension not in {".bvh", ".fbx"}:
                return {
                    "error": "filepath must point to a .bvh or .fbx motion file"
                }
            if not os.path.isfile(input_path):
                return {
                    "error": f"Motion file not found: {input_path}"
                }

            target = bpy.data.objects.get(str(target_armature))
            if target is None or target.type != "ARMATURE":
                return {
                    "error": f"Target armature '{target_armature}' not found"
                }
            previous_action = (
                target.animation_data.action
                if target.animation_data
                else None
            )
            target_had_animation_data = target.animation_data is not None
            previous_pose = {bone.name: (bone.matrix_basis.copy(), bone.rotation_mode) for bone in target.pose.bones}
            if not isinstance(bone_map, dict) or not bone_map:
                return {
                    "error": "bone_map must be a non-empty object mapping source bone names to target bone names"
                }
            normalized_map = {}
            for source_name, target_name in bone_map.items():
                source_key = str(source_name).strip()
                target_key = str(target_name).strip()
                if not source_key or not target_key:
                    return {
                        "error": "bone_map names must be non-empty strings"
                    }
                normalized_map[source_key] = target_key

            resolved_action_name = str(action_name).strip()
            if not resolved_action_name:
                return {"error": "action_name is required"}
            if bpy.data.actions.get(resolved_action_name) is not None:
                return {
                    "error": f"Action already exists: {resolved_action_name}"
                }

            if not isinstance(export_names, (list, tuple)):
                return {
                    "error": "export_names must be a non-empty array of explicit object names"
                }
            normalized_export_names = list(
                dict.fromkeys(
                    str(name).strip()
                    for name in export_names
                    if str(name).strip()
                )
            )
            if not normalized_export_names:
                return {
                    "error": "export_names must be a non-empty array of explicit object names"
                }
            if target.name not in normalized_export_names:
                return {
                    "error": "export_names must include the target armature"
                }
            missing_export_names = [
                name
                for name in normalized_export_names
                if bpy.data.objects.get(name) is None
            ]
            if missing_export_names:
                return {
                    "error": "Export objects not found: "
                    + ", ".join(missing_export_names)
                }

            raw_output_path = str(output_filepath).strip()
            if not os.path.isabs(raw_output_path):
                return {"error": "output_filepath must be absolute"}
            output_path = os.path.abspath(raw_output_path)
            if os.path.splitext(output_path)[1].lower() != ".glb":
                return {
                    "error": "output_filepath must end with .glb"
                }
            output_directory = os.path.dirname(output_path)
            if not os.path.isdir(output_directory):
                return {
                    "error": f"Output directory does not exist: {output_directory}"
                }
            if os.path.exists(output_path) and not coerce_bool(
                overwrite,
                False,
            ):
                return {
                    "error": f"Output file already exists: {output_path}"
                }
            if os.path.exists(output_path):
                output_existed = True
                output_backup_path = (
                    f"{output_path}.vipermesh-backup-{uuid.uuid4().hex}"
                )
                shutil.copy2(output_path, output_backup_path)
                backup_complete = True

            root_motion_mode = str(root_motion or "in_place").lower()
            if root_motion_mode not in {"in_place", "preserve"}:
                return {
                    "error": "root_motion must be IN_PLACE or PRESERVE"
                }
            try:
                step = int(bake_step)
            except (TypeError, ValueError):
                return {"error": "bake_step must be an integer"}
            if step < 1 or step > 16:
                return {
                    "error": "bake_step must be between 1 and 16"
                }

            tracked_data = {
                "objects": bpy.data.objects,
                "armatures": bpy.data.armatures,
                "meshes": bpy.data.meshes,
                "actions": bpy.data.actions,
                "collections": bpy.data.collections,
                "materials": bpy.data.materials,
                "images": bpy.data.images,
            }
            before_names = {
                key: {block.name for block in collection}
                for key, collection in tracked_data.items()
            }

            if bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
            if input_extension == ".bvh":
                import_result = bpy.ops.import_anim.bvh(
                    filepath=input_path,
                    target="ARMATURE",
                    rotate_mode="NATIVE",
                    update_scene_duration=True,
                )
            else:
                import_result = bpy.ops.import_scene.fbx(
                    filepath=input_path,
                    use_anim=True,
                    ignore_leaf_bones=False,
                )
            if "FINISHED" not in import_result:
                raise RuntimeError(
                    f"Motion import operator returned {sorted(import_result)}"
                )

            created_data = {
                key: [
                    block
                    for block in collection
                    if block.name not in before_names[key]
                ]
                for key, collection in tracked_data.items()
            }
            imported_objects = list(created_data["objects"])
            imported_armatures = [
                obj for obj in imported_objects if obj.type == "ARMATURE"
            ]
            if source_armature:
                source = bpy.data.objects.get(str(source_armature))
                if source not in imported_armatures:
                    raise ValueError(
                        "source_armature must name an armature imported from filepath"
                    )
            elif len(imported_armatures) == 1:
                source = imported_armatures[0]
            else:
                raise ValueError(
                    "Motion import must create exactly one armature unless source_armature is explicit"
                )

            source_action = (
                source.animation_data.action
                if source.animation_data
                else None
            )
            if source_action is None:
                raise ValueError(
                    "Imported source armature has no active animation action"
                )
            source_armature_name = source.name

            missing_source_bones = [
                name
                for name in normalized_map
                if source.pose.bones.get(name) is None
            ]
            missing_target_bones = [
                name
                for name in normalized_map.values()
                if target.pose.bones.get(name) is None
            ]
            if missing_source_bones or missing_target_bones:
                raise ValueError(
                    "Bone map could not be resolved; missing source bones: "
                    + ", ".join(missing_source_bones or ["none"])
                    + "; missing target bones: "
                    + ", ".join(missing_target_bones or ["none"])
                )

            resolved_root_source = (
                str(root_source_bone).strip()
                if root_source_bone
                else None
            )
            if root_motion_mode == "preserve":
                if resolved_root_source is None:
                    root_candidates = [
                        source_name
                        for source_name in normalized_map
                        if source.pose.bones[source_name].parent is None
                    ]
                    if len(root_candidates) != 1:
                        raise ValueError(
                            "PRESERVE root motion requires root_source_bone when the mapped root is ambiguous"
                        )
                    resolved_root_source = root_candidates[0]
                if resolved_root_source not in normalized_map:
                    raise ValueError(
                        "root_source_bone must be present in bone_map"
                    )

            target.animation_data_create()
            baked_action = bpy.data.actions.new(
                name=resolved_action_name
            )
            target.animation_data.action = baked_action

            for source_name, target_name in normalized_map.items():
                target_pose_bone = target.pose.bones[target_name]
                rotation_constraint = (
                    target_pose_bone.constraints.new(
                        type="COPY_ROTATION"
                    )
                )
                rotation_constraint.name = (
                    f"ViperMesh_Retarget_Rotation_{source_name}"
                )
                rotation_constraint.target = source
                rotation_constraint.subtarget = source_name
                rotation_constraint.target_space = "POSE"
                rotation_constraint.owner_space = "POSE"
                rotation_constraint.mix_mode = "REPLACE"
                added_constraints.append(
                    (target_pose_bone, rotation_constraint)
                )

            if (
                root_motion_mode == "preserve"
                and resolved_root_source is not None
            ):
                root_target_name = normalized_map[
                    resolved_root_source
                ]
                root_target_pose = target.pose.bones[
                    root_target_name
                ]
                location_constraint = (
                    root_target_pose.constraints.new(
                        type="COPY_LOCATION"
                    )
                )
                location_constraint.name = (
                    "ViperMesh_Retarget_Root_Location"
                )
                location_constraint.target = source
                location_constraint.subtarget = (
                    resolved_root_source
                )
                location_constraint.target_space = "POSE"
                location_constraint.owner_space = "POSE"
                added_constraints.append(
                    (root_target_pose, location_constraint)
                )

            source_start = int(math.floor(source_action.frame_range[0]))
            source_end = int(math.ceil(source_action.frame_range[1]))
            resolved_start = (
                source_start
                if frame_start is None
                else int(frame_start)
            )
            resolved_end = (
                source_end if frame_end is None else int(frame_end)
            )
            if resolved_start < 0 or resolved_end < resolved_start:
                raise ValueError(
                    "frame_start and frame_end must define a non-negative ordered range"
                )
            scene.frame_start = resolved_start
            scene.frame_end = resolved_end
            scene.frame_set(resolved_start)

            bpy.ops.object.select_all(action="DESELECT")
            target.select_set(True)
            bpy.context.view_layer.objects.active = target
            bpy.ops.object.mode_set(mode="POSE")
            bpy.ops.pose.select_all(action="DESELECT")
            for target_name in normalized_map.values():
                target.pose.bones[target_name].select = True
            bake_result = bpy.ops.nla.bake(
                frame_start=resolved_start,
                frame_end=resolved_end,
                step=step,
                only_selected=True,
                visual_keying=True,
                clear_constraints=False,
                clear_parents=False,
                use_current_action=True,
                clean_curves=False,
                bake_types={"POSE"},
                channel_types={
                    "LOCATION",
                    "ROTATION",
                    "SCALE",
                    "BBONE",
                    "PROPS",
                },
            )
            if "FINISHED" not in bake_result:
                raise RuntimeError(
                    f"NLA bake operator returned {sorted(bake_result)}"
                )
            bpy.ops.object.mode_set(mode="OBJECT")
            remove_added_constraints()
            bpy.context.view_layer.update()

            output_touched = True
            export_result = self.export_object(
                normalized_export_names,
                output_path,
                "GLB",
            )
            if export_result.get("error"):
                raise RuntimeError(export_result["error"])
            if coerce_bool(cleanup_imported, True):
                cleanup_created_imports()

            animation_report = self.inspect_animation_data(
                names=[target.name],
                include_actions=True,
                max_actions=20,
            )
            if output_backup_path and os.path.isfile(output_backup_path):
                os.remove(output_backup_path)
                output_backup_path = None
            exported = True
            return {
                "success": True,
                "source_filepath": input_path,
                "source_armature": source_armature_name,
                "target_armature": target.name,
                "bone_map": normalized_map,
                "mapped_bone_count": len(normalized_map),
                "root_motion": root_motion_mode,
                "root_source_bone": resolved_root_source,
                "action_name": baked_action.name,
                "frame_start": resolved_start,
                "frame_end": resolved_end,
                "bake_step": step,
                "cleanup_imported": coerce_bool(
                    cleanup_imported,
                    True,
                ),
                "export_names": normalized_export_names,
                "output_filepath": output_path,
                "file_size_bytes": export_result.get(
                    "file_size_bytes",
                    0,
                ),
                "animation_report": animation_report,
                "next_safe_action": "run inspect_animation_data and inspect_pose_deformation, then review the exported candidate before acceptance",
            }
        except Exception as error:
            try:
                rollback()
            except Exception as recovery_error:
                recovery_failed = True
                return {"error": f"Failed to retarget animation clip: {error}; recovery failed: {recovery_error}", "rolled_back": False, "recovery_backup": output_backup_path}
            return {
                "error": f"Failed to retarget animation clip: {str(error)}",
                "rolled_back": True,
            }
        finally:
            with suppress(Exception):
                if bpy.context.object and bpy.context.object.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.select_all(action="DESELECT")
                for obj in previous_selection:
                    if obj.name in bpy.data.objects:
                        obj.select_set(True)
                if (
                    previous_active is not None
                    and previous_active.name in bpy.data.objects
                ):
                    bpy.context.view_layer.objects.active = (
                        previous_active
                    )
                    if previous_mode != "OBJECT":
                        bpy.ops.object.mode_set(mode=previous_mode)
                scene.frame_start = previous_frame_start
                scene.frame_end = previous_frame_end
                scene.frame_set(previous_frame)
                if not exported and previous_pose:
                    target = bpy.data.objects.get(str(target_armature))
                    if target is not None:
                        for name, (matrix, rotation_mode) in previous_pose.items():
                            bone = target.pose.bones.get(name)
                            if bone is not None:
                                bone.rotation_mode = rotation_mode
                                bone.matrix_basis = matrix
                        bpy.context.view_layer.update()
            if output_backup_path and backup_complete and not output_touched and not recovery_failed:
                with suppress(Exception):
                    os.remove(output_backup_path)

    def set_keyframe_animation(
        self,
        name,
        data_path="location",
        keyframes=None,
        interpolation="BEZIER",
        easing=None,
        rotation_unit="radians",
        clear_existing=False,
        set_scene_range=True,
    ):
        """Create bounded transform keyframes for location, rotation_euler, or scale without arbitrary Python."""
        try:
            import math

            obj = bpy.data.objects.get(str(name))
            if obj is None:
                return {"error": f"Object '{name}' not found"}

            allowed_paths = {"location", "rotation_euler", "scale"}
            data_path = str(data_path or "location").strip()
            if data_path not in allowed_paths:
                return {"error": f"Unsupported data_path '{data_path}'. Use one of: {', '.join(sorted(allowed_paths))}"}

            if not isinstance(keyframes, (list, tuple)) or len(keyframes) < 2:
                return {"error": "keyframes must contain at least two entries with frame and value fields"}

            def coerce_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, str):
                    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(value)

            def coerce_frame(value):
                frame = int(round(float(value)))
                if frame < 0:
                    raise ValueError("frame values must be >= 0")
                return frame

            def coerce_vector(value):
                if not isinstance(value, (list, tuple)) or len(value) != 3:
                    raise ValueError("keyframe value must be a 3-number array")
                vector = [float(value[0]), float(value[1]), float(value[2])]
                if data_path == "rotation_euler" and str(rotation_unit).lower() == "degrees":
                    vector = [math.radians(component) for component in vector]
                return vector

            normalized_keyframes = []
            for index, keyframe in enumerate(keyframes):
                if not isinstance(keyframe, dict):
                    return {"error": f"keyframes[{index}] must be an object with frame and value fields"}
                if "frame" not in keyframe or "value" not in keyframe:
                    return {"error": f"keyframes[{index}] must include frame and value"}
                normalized_keyframes.append({
                    "frame": coerce_frame(keyframe["frame"]),
                    "value": coerce_vector(keyframe["value"]),
                })

            normalized_keyframes.sort(key=lambda item: item["frame"])
            clear_existing = coerce_bool(clear_existing)
            set_scene_range = coerce_bool(set_scene_range, True)
            interpolation = str(interpolation or "BEZIER").upper()
            easing = str(easing).upper() if easing else None
            allowed_interpolation = {"CONSTANT", "LINEAR", "BEZIER", "SINE", "QUAD", "CUBIC", "QUART", "QUINT", "EXPO", "CIRC", "BACK", "BOUNCE", "ELASTIC"}
            if interpolation not in allowed_interpolation:
                return {"error": f"Unsupported interpolation '{interpolation}'"}
            allowed_easing = {"EASE_IN", "EASE_OUT", "EASE_IN_OUT"}
            if easing and easing not in allowed_easing:
                return {"error": f"Unsupported easing '{easing}'. Use one of: {', '.join(sorted(allowed_easing))}"}

            scene = bpy.context.scene
            current_frame = int(scene.frame_current)

            def resolve_action_slot(action, handle):
                if action is None or handle is None:
                    return None
                try:
                    slots = list(getattr(action, "slots", []) or [])
                except Exception:
                    return None
                for candidate in slots:
                    if getattr(candidate, "handle", None) == handle:
                        return candidate
                if isinstance(handle, int) and 0 <= handle < len(slots):
                    return slots[handle]
                return None

            def get_action_slot(animation_data, action=None):
                if not animation_data:
                    return None
                slot = getattr(animation_data, "action_slot", None)
                if slot is not None and not isinstance(slot, int):
                    return slot
                handle = getattr(animation_data, "action_slot_handle", None)
                if handle is None and isinstance(slot, int):
                    handle = slot
                return resolve_action_slot(action or getattr(animation_data, "action", None), handle)

            def collect_action_fcurves(action, action_slot=None):
                if action is None:
                    return [], None, "none"
                channelbag_error = None
                try:
                    from bpy_extras import anim_utils

                    if action_slot is not None and hasattr(anim_utils, "action_get_channelbag_for_slot"):
                        channelbag = anim_utils.action_get_channelbag_for_slot(action, action_slot)
                        if channelbag is not None and hasattr(channelbag, "fcurves"):
                            return list(channelbag.fcurves), channelbag, "channelbag"
                except Exception as exc:
                    channelbag_error = type(exc).__name__

                try:
                    legacy_fcurves = getattr(action, "fcurves", None)
                    if legacy_fcurves is not None:
                        source = "legacy_fcurves"
                        if channelbag_error:
                            source = f"legacy_fcurves_after_channelbag_{channelbag_error}"
                        return list(legacy_fcurves), action, source
                except Exception as exc:
                    if channelbag_error:
                        return [], None, f"channelbag_{channelbag_error}_legacy_{type(exc).__name__}"
                    return [], None, f"legacy_{type(exc).__name__}"

                if channelbag_error:
                    return [], None, f"channelbag_{channelbag_error}"
                return [], None, "unavailable"

            action = obj.animation_data.action if obj.animation_data else None
            if action is not None and int(getattr(action, "users", 0) or 0) > 1:
                action = action.copy()
                action.name = f"{obj.name}_Keyframes"
                obj.animation_data.action = action

            if clear_existing and action is not None:
                action_slot = get_action_slot(obj.animation_data, action)
                fcurves, fcurve_owner, _fcurve_source = collect_action_fcurves(action, action_slot)
                try:
                    owner_fcurves = getattr(fcurve_owner, "fcurves", None)
                    for fcurve in list(fcurves):
                        if getattr(fcurve, "data_path", None) == data_path:
                            owner_fcurves.remove(fcurve)
                except Exception:
                    pass

            target_frames = {keyframe["frame"] for keyframe in normalized_keyframes}
            for keyframe in normalized_keyframes:
                setattr(obj, data_path, keyframe["value"])
                obj.keyframe_insert(data_path=data_path, frame=keyframe["frame"])

            action = obj.animation_data.action if obj.animation_data else None
            edited_fcurves = []
            easing_warnings = []
            action_slot = get_action_slot(obj.animation_data, action) if action is not None else None
            fcurves, _fcurve_owner, _fcurve_source = collect_action_fcurves(action, action_slot)
            if action is not None:
                try:
                    for fcurve in list(fcurves):
                        if getattr(fcurve, "data_path", None) == data_path:
                            edited_fcurves.append(fcurve)
                            for point in getattr(fcurve, "keyframe_points", []) or []:
                                co = getattr(point, "co", None)
                                if not clear_existing and (co is None or int(round(float(co[0]))) not in target_frames):
                                    continue
                                point.interpolation = interpolation
                                if easing and hasattr(point, "easing"):
                                    try:
                                        point.easing = easing
                                    except Exception as exc:
                                        easing_warnings.append(f"Failed to set easing on frame {int(round(float(co[0]))) if co is not None else 'unknown'}: {type(exc).__name__}")
                            try:
                                fcurve.update()
                            except Exception:
                                pass
                except Exception:
                    pass

            if set_scene_range and normalized_keyframes:
                first_frame = normalized_keyframes[0]["frame"]
                last_frame = normalized_keyframes[-1]["frame"]
                scene.frame_start = min(int(scene.frame_start), first_frame)
                scene.frame_end = max(int(scene.frame_end), last_frame)

            scene.frame_set(current_frame)
            bpy.context.view_layer.update()

            return {
                "success": True,
                "object": obj.name,
                "data_path": data_path,
                "keyframe_count": len(normalized_keyframes),
                "frames": [keyframe["frame"] for keyframe in normalized_keyframes],
                "interpolation": interpolation,
                "easing": easing if easing and not easing_warnings else None,
                "easing_requested": easing,
                "easing_warnings": easing_warnings,
                "rotation_unit": rotation_unit,
                "cleared_existing": clear_existing,
                "action": action.name if action else None,
                "fcurve_count": len(edited_fcurves),
                "scene_range": {
                    "frame_start": int(bpy.context.scene.frame_start),
                    "frame_end": int(bpy.context.scene.frame_end),
                },
                "next_safe_action": "run inspect_animation_data to verify the generated F-curves before adding more animation",
            }
        except Exception as e:
            return {"error": f"Failed to set keyframe animation: {str(e)}"}

    def create_turntable_animation(
        self,
        target_names=None,
        start_frame=1,
        end_frame=120,
        axis="Z",
        rotations=1.0,
        interpolation="LINEAR",
        clear_existing=True,
        set_scene_range=True,
    ):
        """Create deterministic product/model turntable rotation keyframes for explicit objects."""
        try:
            import math

            if isinstance(target_names, str):
                target_names = [target_names]
            if not isinstance(target_names, (list, tuple)) or not target_names:
                return {"error": "target_names must contain at least one object name"}

            axis = str(axis or "Z").strip().upper()
            axis_index_map = {"X": 0, "Y": 1, "Z": 2}
            if axis not in axis_index_map:
                return {"error": "axis must be one of X, Y, or Z"}
            axis_index = axis_index_map[axis]

            start_frame = int(round(float(start_frame)))
            end_frame = int(round(float(end_frame)))
            if start_frame < 0 or end_frame < 0:
                return {"error": "start_frame and end_frame must be >= 0"}
            if end_frame <= start_frame:
                return {"error": "end_frame must be greater than start_frame"}

            rotations = float(rotations)
            if rotations == 0:
                return {"error": "rotations must be non-zero"}

            def coerce_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, str):
                    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(value)

            interpolation = str(interpolation or "LINEAR").upper()
            allowed_interpolation = {"CONSTANT", "LINEAR", "BEZIER", "SINE", "QUAD", "CUBIC", "QUART", "QUINT", "EXPO", "CIRC", "BACK", "BOUNCE", "ELASTIC"}
            if interpolation not in allowed_interpolation:
                return {"error": f"Unsupported interpolation '{interpolation}'"}

            clear_existing = coerce_bool(clear_existing, True)
            set_scene_range = coerce_bool(set_scene_range, True)

            objects = []
            missing_objects = []
            for raw_name in target_names:
                name = str(raw_name)
                obj = bpy.data.objects.get(name)
                if obj is None:
                    missing_objects.append(name)
                else:
                    objects.append(obj)
            if not objects:
                return {"error": "No target objects were found", "missing_objects": missing_objects}

            scene = bpy.context.scene
            current_frame = int(scene.frame_current)

            def resolve_action_slot(action, handle):
                if action is None or handle is None:
                    return None
                try:
                    slots = list(getattr(action, "slots", []) or [])
                except Exception:
                    return None
                for candidate in slots:
                    if getattr(candidate, "handle", None) == handle:
                        return candidate
                if isinstance(handle, int) and 0 <= handle < len(slots):
                    return slots[handle]
                return None

            def get_action_slot(animation_data, action=None):
                if not animation_data:
                    return None
                slot = getattr(animation_data, "action_slot", None)
                if slot is not None and not isinstance(slot, int):
                    return slot
                handle = getattr(animation_data, "action_slot_handle", None)
                if handle is None and isinstance(slot, int):
                    handle = slot
                return resolve_action_slot(action or getattr(animation_data, "action", None), handle)

            def collect_action_fcurves(action, action_slot=None):
                if action is None:
                    return [], None
                try:
                    from bpy_extras import anim_utils

                    if action_slot is not None and hasattr(anim_utils, "action_get_channelbag_for_slot"):
                        channelbag = anim_utils.action_get_channelbag_for_slot(action, action_slot)
                        if channelbag is not None and hasattr(channelbag, "fcurves"):
                            return list(channelbag.fcurves), channelbag
                except Exception:
                    pass

                try:
                    legacy_fcurves = getattr(action, "fcurves", None)
                    if legacy_fcurves is not None:
                        return list(legacy_fcurves), action
                except Exception:
                    pass
                return [], None

            def clear_rotation_fcurves(obj):
                action = obj.animation_data.action if obj.animation_data else None
                if action is None:
                    return 0
                if int(getattr(action, "users", 0) or 0) > 1:
                    action = action.copy()
                    action.name = f"{obj.name}_Turntable"
                    obj.animation_data.action = action
                action_slot = get_action_slot(obj.animation_data, action)
                fcurves, fcurve_owner = collect_action_fcurves(action, action_slot)
                removed = 0
                try:
                    owner_fcurves = getattr(fcurve_owner, "fcurves", None)
                    if owner_fcurves is None:
                        return 0
                    for fcurve in list(fcurves):
                        if getattr(fcurve, "data_path", None) == "rotation_euler":
                            owner_fcurves.remove(fcurve)
                            removed += 1
                except Exception:
                    return removed
                return removed

            def style_rotation_fcurves(obj):
                action = obj.animation_data.action if obj.animation_data else None
                if action is None:
                    return 0
                action_slot = get_action_slot(obj.animation_data, action)
                fcurves, _fcurve_owner = collect_action_fcurves(action, action_slot)
                edited = 0
                for fcurve in list(fcurves):
                    if getattr(fcurve, "data_path", None) != "rotation_euler":
                        continue
                    edited += 1
                    for point in getattr(fcurve, "keyframe_points", []) or []:
                        point.interpolation = interpolation
                    try:
                        fcurve.update()
                    except Exception:
                        pass
                return edited

            animated = []
            total_removed_fcurves = 0
            total_edited_fcurves = 0
            delta = math.tau * rotations
            for obj in objects:
                if clear_existing:
                    total_removed_fcurves += clear_rotation_fcurves(obj)

                start_rotation = [float(obj.rotation_euler[0]), float(obj.rotation_euler[1]), float(obj.rotation_euler[2])]
                end_rotation = list(start_rotation)
                end_rotation[axis_index] = end_rotation[axis_index] + delta

                obj.rotation_euler = start_rotation
                obj.keyframe_insert(data_path="rotation_euler", frame=start_frame)
                obj.rotation_euler = end_rotation
                obj.keyframe_insert(data_path="rotation_euler", frame=end_frame)
                total_edited_fcurves += style_rotation_fcurves(obj)

                animated.append({
                    "name": obj.name,
                    "start_rotation": start_rotation,
                    "end_rotation": end_rotation,
                })

            if set_scene_range:
                scene.frame_start = min(int(scene.frame_start), start_frame)
                scene.frame_end = max(int(scene.frame_end), end_frame)

            scene.frame_set(current_frame)
            bpy.context.view_layer.update()

            return {
                "success": True,
                "animated_objects": animated,
                "missing_objects": missing_objects,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "axis": axis,
                "rotations": rotations,
                "interpolation": interpolation,
                "cleared_existing": clear_existing,
                "removed_fcurves": total_removed_fcurves,
                "edited_fcurves": total_edited_fcurves,
                "scene_range": {
                    "frame_start": int(scene.frame_start),
                    "frame_end": int(scene.frame_end),
                },
                "next_safe_action": "run inspect_animation_data to verify the generated turntable F-curves before adding more animation",
            }
        except Exception as e:
            return {"error": f"Failed to create turntable animation: {str(e)}"}

    def set_timeline_settings(
        self,
        frame_start=None,
        frame_end=None,
        current_frame=None,
        fps=None,
        fps_base=None,
        use_preview_range=None,
        preview_start=None,
        preview_end=None,
        playback_sync=None,
    ):
        """Set bounded scene timeline settings without arbitrary Python."""
        try:
            scene = bpy.context.scene
            changed = {}

            def coerce_int(value, label, minimum=None):
                number = int(round(float(value)))
                if minimum is not None and number < minimum:
                    raise ValueError(f"{label} must be >= {minimum}")
                return number

            def coerce_float(value, label, minimum=None):
                number = float(value)
                if minimum is not None and number < minimum:
                    raise ValueError(f"{label} must be >= {minimum}")
                return number

            def coerce_bool(value):
                if isinstance(value, str):
                    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(value)

            new_frame_start = int(scene.frame_start)
            new_frame_end = int(scene.frame_end)
            new_current_frame = int(scene.frame_current)
            new_fps = int(scene.render.fps)
            new_fps_base = float(scene.render.fps_base)
            new_use_preview_range = bool(scene.use_preview_range)
            new_preview_start = int(scene.frame_preview_start)
            new_preview_end = int(scene.frame_preview_end)
            new_playback_sync = str(scene.sync_mode)

            if frame_start is not None:
                new_frame_start = coerce_int(frame_start, "frame_start", 0)
            if frame_end is not None:
                new_frame_end = coerce_int(frame_end, "frame_end", 0)

            if fps is not None:
                new_fps = coerce_int(fps, "fps", 1)
            if fps_base is not None:
                new_fps_base = coerce_float(fps_base, "fps_base", 0.001)

            if use_preview_range is not None:
                new_use_preview_range = coerce_bool(use_preview_range)
            if preview_start is not None:
                new_preview_start = coerce_int(preview_start, "preview_start", 0)
            if preview_end is not None:
                new_preview_end = coerce_int(preview_end, "preview_end", 0)

            if playback_sync is not None:
                sync_mode = str(playback_sync).upper()
                allowed_sync_modes = {"NONE", "FRAME_DROP", "AUDIO_SYNC"}
                if sync_mode not in allowed_sync_modes:
                    return {"error": f"Unsupported playback_sync '{playback_sync}'. Use one of: {', '.join(sorted(allowed_sync_modes))}"}
                new_playback_sync = sync_mode

            if current_frame is not None:
                new_current_frame = coerce_int(current_frame, "current_frame", 0)

            if new_frame_end < new_frame_start:
                return {"error": "frame_end must be greater than or equal to frame_start"}
            if new_preview_end < new_preview_start:
                return {"error": "preview_end must be greater than or equal to preview_start"}

            if frame_start is not None:
                scene.frame_start = new_frame_start
                changed["frame_start"] = int(scene.frame_start)
            if frame_end is not None:
                scene.frame_end = new_frame_end
                changed["frame_end"] = int(scene.frame_end)
            if fps is not None:
                scene.render.fps = new_fps
                changed["fps"] = int(scene.render.fps)
            if fps_base is not None:
                scene.render.fps_base = new_fps_base
                changed["fps_base"] = float(scene.render.fps_base)
            if use_preview_range is not None:
                scene.use_preview_range = new_use_preview_range
                changed["use_preview_range"] = bool(scene.use_preview_range)
            if preview_start is not None:
                scene.frame_preview_start = new_preview_start
                changed["preview_start"] = int(scene.frame_preview_start)
            if preview_end is not None:
                scene.frame_preview_end = new_preview_end
                changed["preview_end"] = int(scene.frame_preview_end)
            if playback_sync is not None:
                scene.sync_mode = new_playback_sync
                changed["playback_sync"] = str(scene.sync_mode)

            scene.frame_set(new_current_frame)
            if current_frame is not None:
                changed["current_frame"] = int(scene.frame_current)

            bpy.context.view_layer.update()

            return {
                "success": True,
                "changed": changed,
                "timeline": {
                    "frame_start": int(scene.frame_start),
                    "frame_end": int(scene.frame_end),
                    "current_frame": int(scene.frame_current),
                    "fps": int(scene.render.fps),
                    "fps_base": float(scene.render.fps_base),
                    "use_preview_range": bool(scene.use_preview_range),
                    "preview_start": int(scene.frame_preview_start),
                    "preview_end": int(scene.frame_preview_end),
                    "playback_sync": str(scene.sync_mode),
                },
                "next_safe_action": "run inspect_animation_data to verify timeline and action state before editing keyframes",
            }
        except Exception as e:
            return {"error": f"Failed to set timeline settings: {str(e)}"}

    def inspect_collection_hierarchy(self, names=None, max_collections=120, max_objects=200, include_hidden=True):
        """Inspect collection nesting, object membership, parent links, and visibility without mutating the scene."""
        try:
            def parse_names(raw_names):
                if raw_names is None:
                    return []
                if isinstance(raw_names, str):
                    return [part.strip() for part in raw_names.split(",") if part.strip()]
                if isinstance(raw_names, (list, tuple)):
                    return [str(name).strip() for name in raw_names if str(name).strip()]
                raise ValueError("names must be an array of object/collection names, a comma-separated string, or omitted")

            def coerce_bool(value):
                if isinstance(value, str):
                    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(value)

            def coerce_positive_int(value, default_value, upper_bound=1000):
                try:
                    parsed = int(value)
                    if parsed < 1:
                        return default_value
                    return min(parsed, upper_bound)
                except Exception:
                    return default_value

            requested_names = parse_names(names)
            max_collections = coerce_positive_int(max_collections, 120)
            max_objects = coerce_positive_int(max_objects, 200)
            include_hidden = coerce_bool(include_hidden)

            scene = bpy.context.scene
            root_collection = scene.collection
            collection_parent_map = {}
            collection_paths = {}
            walked_collections = []

            def walk_collection(collection, path):
                if collection.name in collection_paths:
                    return
                walked_collections.append(collection)
                collection_paths[collection.name] = path + [collection.name]
                for child in collection.children:
                    collection_parent_map.setdefault(child.name, []).append(collection.name)
                    walk_collection(child, collection_paths[collection.name])

            walk_collection(root_collection, [])
            all_collections = walked_collections

            def collection_visible(collection):
                return not bool(getattr(collection, "hide_viewport", False)) and not bool(getattr(collection, "hide_render", False))

            def object_visible(obj):
                try:
                    return bool(obj.visible_get())
                except Exception:
                    return not bool(getattr(obj, "hide_viewport", False)) and not bool(getattr(obj, "hide_render", False))

            def summarize_collection(collection):
                object_names = [
                    obj.name
                    for obj in collection.objects
                    if include_hidden or object_visible(obj)
                ]
                child_names = [
                    child.name
                    for child in collection.children
                    if include_hidden or collection_visible(child)
                ]
                return {
                    "name": collection.name,
                    "is_scene_root": collection == root_collection,
                    "path": collection_paths.get(collection.name, [collection.name]),
                    "parent_collections": collection_parent_map.get(collection.name, []),
                    "child_collections": child_names,
                    "child_collection_count": len(child_names),
                    "objects": object_names[:50],
                    "object_count": len(object_names),
                    "objects_list_truncated": max(0, len(object_names) - 50),
                    "hide_viewport": bool(getattr(collection, "hide_viewport", False)),
                    "hide_render": bool(getattr(collection, "hide_render", False)),
                }

            def summarize_object(obj):
                collection_names = [collection.name for collection in obj.users_collection]
                child_names = [child.name for child in obj.children]
                parent = getattr(obj, "parent", None)
                issues = []
                if not collection_names:
                    issues.append({
                        "severity": "warn",
                        "code": "object_without_collection",
                        "object": obj.name,
                        "message": f"Object '{obj.name}' is not linked to any collection.",
                    })
                if len(collection_names) > 1:
                    issues.append({
                        "severity": "info",
                        "code": "object_in_multiple_collections",
                        "object": obj.name,
                        "message": f"Object '{obj.name}' is linked to multiple collections.",
                    })
                if bool(getattr(obj, "hide_viewport", False)) or bool(getattr(obj, "hide_render", False)):
                    issues.append({
                        "severity": "info",
                        "code": "object_hidden",
                        "object": obj.name,
                        "message": f"Object '{obj.name}' has viewport or render visibility disabled.",
                    })

                return {
                    "name": obj.name,
                    "type": obj.type,
                    "parent": parent.name if parent else None,
                    "parent_type": str(getattr(obj, "parent_type", "")),
                    "children": child_names,
                    "child_count": len(child_names),
                    "collections": collection_names,
                    "collection_count": len(collection_names),
                    "hide_viewport": bool(getattr(obj, "hide_viewport", False)),
                    "hide_render": bool(getattr(obj, "hide_render", False)),
                    "visible": object_visible(obj),
                    "issues": issues,
                }

            issues = []
            if requested_names:
                selected_collections = []
                selected_objects = []
                selected_collection_names = set()
                selected_object_names = set()
                matched_names = set()

                def add_object_scope(obj):
                    if not include_hidden and not object_visible(obj):
                        return
                    if obj.name not in selected_object_names:
                        selected_objects.append(obj)
                        selected_object_names.add(obj.name)

                def add_collection_scope(collection):
                    stack = [collection]
                    while stack:
                        current = stack.pop()
                        if not include_hidden and not collection_visible(current):
                            continue
                        if current.name in selected_collection_names:
                            continue
                        selected_collections.append(current)
                        selected_collection_names.add(current.name)
                        for obj in current.objects:
                            add_object_scope(obj)
                        stack.extend(reversed(list(current.children)))

                for name in dict.fromkeys(requested_names):
                    collection = bpy.data.collections.get(name)
                    if collection is not None:
                        add_collection_scope(collection)
                        matched_names.add(name)
                    obj = bpy.data.objects.get(name)
                    if obj is not None:
                        add_object_scope(obj)
                        matched_names.add(name)
                        for collection in obj.users_collection:
                            if collection.name not in selected_collection_names and (include_hidden or collection_visible(collection)):
                                selected_collections.append(collection)
                                selected_collection_names.add(collection.name)

                for name in requested_names:
                    if name not in matched_names:
                        issues.append({
                            "severity": "error",
                            "code": "name_not_found",
                            "name": name,
                            "message": f"No object or collection named '{name}' was found.",
                        })

                collections_truncated = 0
                objects_truncated = 0
            else:
                scene_collections = all_collections if include_hidden else [collection for collection in all_collections if collection_visible(collection)]
                selected_collections = scene_collections[:max_collections]
                scene_objects = list(scene.objects)
                if not include_hidden:
                    scene_objects = [obj for obj in scene_objects if object_visible(obj)]
                selected_objects = scene_objects[:max_objects]
                collections_truncated = max(0, len(scene_collections) - len(selected_collections))
                objects_truncated = max(0, len(scene_objects) - len(selected_objects))

            collection_reports = [
                summarize_collection(collection)
                for collection in selected_collections
                if include_hidden or collection_visible(collection)
            ]
            object_reports = []
            for obj in selected_objects:
                report = summarize_object(obj)
                object_reports.append(report)
                issues.extend(report.get("issues", []))

            return {
                "success": len([issue for issue in issues if issue.get("severity") == "error"]) == 0,
                "scene_collection": root_collection.name,
                "limits": {
                    "max_collections": max_collections,
                    "max_objects": max_objects,
                    "include_hidden": include_hidden,
                },
                "collection_count": len(collection_reports),
                "collections": collection_reports,
                "collections_truncated": collections_truncated,
                "object_count": len(object_reports),
                "objects": object_reports,
                "objects_truncated": objects_truncated,
                "issues": issues,
                "next_safe_action": "inspect collection membership and parent links before moving objects, parenting, unparenting, or changing visibility",
            }
        except Exception as e:
            return {"error": f"Failed to inspect collection hierarchy: {str(e)}"}

    def add_modifier(self, name, modifier_type, modifier_name=None, properties=None):
        """Add a modifier to an object. modifier_type is the Blender enum (SUBSURF, MIRROR, BEVEL, etc.)"""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}

            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_add(type=modifier_type)

            # The newly added modifier is the last one
            mod = obj.modifiers[-1]
            if modifier_name:
                mod.name = modifier_name

            # Apply optional properties
            if properties and isinstance(properties, dict):
                for prop_name, prop_value in properties.items():
                    try:
                        setattr(mod, prop_name, prop_value)
                    except (AttributeError, TypeError) as prop_err:
                        pass  # Skip invalid properties silently

            return {
                "success": True,
                "object": name,
                "modifier": mod.name,
                "type": modifier_type,
                "total_modifiers": len(obj.modifiers),
            }
        except RuntimeError as e:
            return {"error": f"Invalid modifier type '{modifier_type}': {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to add modifier: {str(e)}"}

    def soften_mesh_edges(
        self,
        names,
        width=0.02,
        segments=2,
        profile=0.5,
        affect="EDGES",
        harden_normals=True,
        clamp_overlap=True,
        shade_smooth=True,
        add_weighted_normal=True,
        apply_modifier=False,
        modifier_name="ViperMesh_EdgeSoften",
        replace_existing=True,
        skip_non_mesh=True,
    ):
        """Batch-add bounded bevel/normal smoothing to mesh objects without generated Python."""
        previous_active = bpy.context.view_layer.objects.active
        previous_selection = list(bpy.context.selected_objects)
        previous_context_object = bpy.context.object
        previous_mode = previous_context_object.mode if previous_context_object else "OBJECT"
        try:
            if isinstance(names, str):
                requested_names = [
                    part.strip() for part in names.split(",") if part.strip()
                ]
            elif isinstance(names, (list, tuple)):
                requested_names = [
                    str(name).strip() for name in names if str(name).strip()
                ]
            else:
                return {"error": "names must be an array or comma-separated string"}

            requested_names = list(dict.fromkeys(requested_names))
            if not requested_names:
                return {"error": "At least one object name is required"}

            def bounded_float(value, label, minimum, maximum):
                try:
                    resolved = float(value)
                except (TypeError, ValueError):
                    raise ValueError(f"{label} must be a number")
                if resolved < minimum or resolved > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return resolved

            def bounded_int(value, label, minimum, maximum):
                try:
                    resolved = int(value)
                except (TypeError, ValueError):
                    raise ValueError(f"{label} must be an integer")
                if resolved < minimum or resolved > maximum:
                    raise ValueError(f"{label} must be between {minimum} and {maximum}")
                return resolved

            resolved_width = bounded_float(width, "width", 0.000001, 100.0)
            resolved_segments = bounded_int(segments, "segments", 1, 32)
            resolved_profile = bounded_float(profile, "profile", 0.0, 1.0)
            resolved_affect = str(affect or "EDGES").upper()
            if resolved_affect not in {"EDGES", "VERTICES"}:
                return {"error": "affect must be EDGES or VERTICES"}
            resolved_modifier_name = str(modifier_name or "ViperMesh_EdgeSoften").strip()
            if not resolved_modifier_name:
                return {"error": "modifier_name cannot be empty"}
            resolved_shade_smooth = bool(shade_smooth) or bool(harden_normals)

            results = []
            skipped = []
            for object_name in requested_names:
                obj = bpy.data.objects.get(object_name)
                if not obj:
                    skipped.append({"object": object_name, "reason": "not_found"})
                    continue
                if obj.type != 'MESH':
                    if skip_non_mesh:
                        skipped.append({
                            "object": obj.name,
                            "reason": f"type_{obj.type}",
                        })
                        continue
                    return {
                        "error": f"Object '{obj.name}' is type '{obj.type}', expected MESH",
                        "results": results,
                        "skipped": skipped,
                    }

                created_modifiers = []
                warnings = []
                if bool(harden_normals) and not bool(shade_smooth):
                    warnings.append("harden_normals requires smooth shading; shade_smooth was enabled for this object")
                existing = obj.modifiers.get(resolved_modifier_name)
                if existing and bool(replace_existing):
                    obj.modifiers.remove(existing)
                    existing = None
                if existing and existing.type != 'BEVEL':
                    obj.modifiers.remove(existing)
                    existing = None
                if existing:
                    mod = existing
                else:
                    mod = obj.modifiers.new(name=resolved_modifier_name, type='BEVEL')
                mod.width = resolved_width
                mod.segments = resolved_segments
                mod.profile = resolved_profile
                if hasattr(mod, "affect"):
                    mod.affect = resolved_affect
                if hasattr(mod, "harden_normals"):
                    mod.harden_normals = bool(harden_normals)
                if hasattr(mod, "use_clamp_overlap"):
                    mod.use_clamp_overlap = bool(clamp_overlap)
                bevel_modifier_name = mod.name
                created_modifiers.append(bevel_modifier_name)
                modifier_names_to_apply = [bevel_modifier_name]

                if resolved_shade_smooth:
                    for polygon in obj.data.polygons:
                        polygon.use_smooth = True

                weighted_normal_modifier = None
                weighted_normal_modifier_name = None
                if bool(add_weighted_normal):
                    weighted_normal_name = f"{resolved_modifier_name}_WeightedNormal"
                    existing_weighted_normal = obj.modifiers.get(weighted_normal_name)
                    if existing_weighted_normal and bool(replace_existing):
                        obj.modifiers.remove(existing_weighted_normal)
                        existing_weighted_normal = None
                    if existing_weighted_normal and existing_weighted_normal.type != 'WEIGHTED_NORMAL':
                        obj.modifiers.remove(existing_weighted_normal)
                        existing_weighted_normal = None
                    if existing_weighted_normal:
                        weighted_normal_modifier = existing_weighted_normal
                    else:
                        weighted_normal_modifier = obj.modifiers.new(
                            name=weighted_normal_name,
                            type='WEIGHTED_NORMAL',
                        )
                    if hasattr(weighted_normal_modifier, "keep_sharp"):
                        weighted_normal_modifier.keep_sharp = True
                    weighted_normal_modifier_name = weighted_normal_modifier.name
                    created_modifiers.append(weighted_normal_modifier_name)
                    modifier_names_to_apply.append(weighted_normal_modifier_name)

                def modifier_index(modifier_name):
                    for index, candidate_modifier in enumerate(obj.modifiers):
                        if candidate_modifier.name == modifier_name:
                            return index
                    return None

                if weighted_normal_modifier_name:
                    bevel_index = modifier_index(bevel_modifier_name)
                    weighted_normal_index = modifier_index(weighted_normal_modifier_name)
                    if (
                        bevel_index is not None
                        and weighted_normal_index is not None
                        and bevel_index > weighted_normal_index
                    ):
                        obj.modifiers.move(bevel_index, weighted_normal_index)

                applied_modifiers = []
                apply_failed = False
                if bool(apply_modifier):
                    if bpy.context.object and bpy.context.object.mode != "OBJECT":
                        bpy.ops.object.mode_set(mode="OBJECT")
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    bpy.context.view_layer.objects.active = obj
                    for modifier_name_to_apply in modifier_names_to_apply:
                        if obj.modifiers.get(modifier_name_to_apply):
                            try:
                                apply_result = bpy.ops.object.modifier_apply(
                                    modifier=modifier_name_to_apply
                                )
                            except Exception as apply_error:
                                apply_failed = True
                                warnings.append(
                                    f"Failed to apply modifier {modifier_name_to_apply}: {apply_error}"
                                )
                                skipped.append({
                                    "object": obj.name,
                                    "modifier": modifier_name_to_apply,
                                    "reason": "apply_failed",
                                    "message": str(apply_error),
                                })
                                break
                            if 'FINISHED' not in apply_result:
                                apply_failed = True
                                message = f"Failed to apply modifier {modifier_name_to_apply}: {sorted(apply_result)}"
                                warnings.append(message)
                                skipped.append({
                                    "object": obj.name,
                                    "modifier": modifier_name_to_apply,
                                    "reason": "apply_failed",
                                    "message": message,
                                })
                                break
                            applied_modifiers.append(modifier_name_to_apply)

                results.append({
                    "object": obj.name,
                    "bevel_modifier": bevel_modifier_name,
                    "weighted_normal_modifier": weighted_normal_modifier_name,
                    "width": resolved_width,
                    "segments": resolved_segments,
                    "profile": resolved_profile,
                    "affect": resolved_affect,
                    "shade_smooth": resolved_shade_smooth,
                    "modifiers": created_modifiers,
                    "applied_modifiers": applied_modifiers,
                    "apply_failed": apply_failed,
                    "warnings": warnings,
                })

            if not results:
                return {
                    "error": "No mesh objects were softened",
                    "requested": requested_names,
                    "skipped": skipped,
                }

            return {
                "success": True,
                "requested_count": len(requested_names),
                "softened_count": len(results),
                "skipped_count": len(skipped),
                "results": results,
                "skipped": skipped,
                "next_safe_action": "inspect_modifier_constraint_stack for softened objects before applying or exporting",
            }
        except Exception as e:
            return {"error": f"Failed to soften mesh edges: {str(e)}"}
        finally:
            with suppress(Exception):
                if bpy.context.object and bpy.context.object.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.select_all(action='DESELECT')
                for obj in previous_selection:
                    if obj.name in bpy.data.objects:
                        obj.select_set(True)
                if previous_active and previous_active.name in bpy.data.objects:
                    bpy.context.view_layer.objects.active = previous_active
                if previous_context_object and previous_context_object.name in bpy.data.objects:
                    if previous_mode != "OBJECT":
                        bpy.context.view_layer.objects.active = previous_context_object
                        previous_context_object.select_set(True)
                        bpy.ops.object.mode_set(mode=previous_mode)

    def configure_modifier(self, name, modifier, show_viewport=None, show_render=None, show_in_editmode=None, show_on_cage=None, move_to_index=None):
        """Configure safe modifier stack flags or move a modifier to a stack index without applying it."""
        previous_active = bpy.context.view_layer.objects.active
        previous_selection = list(bpy.context.selected_objects)
        previous_context_object = bpy.context.object
        previous_mode = previous_context_object.mode if previous_context_object else "OBJECT"
        changed_mode = False
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}
            if modifier not in obj.modifiers:
                available = [m.name for m in obj.modifiers]
                return {"error": f"Modifier '{modifier}' not found on '{name}'. Available: {available}"}

            mod = obj.modifiers[modifier]
            changes = []
            for attr, value in {
                "show_viewport": show_viewport,
                "show_render": show_render,
                "show_in_editmode": show_in_editmode,
                "show_on_cage": show_on_cage,
            }.items():
                if value is not None and hasattr(mod, attr):
                    setattr(mod, attr, bool(value))
                    changes.append(f"{attr}={bool(value)}")

            if move_to_index is not None:
                target_index = int(move_to_index)
                if target_index < 0 or target_index >= len(obj.modifiers):
                    return {"error": f"move_to_index must be between 0 and {len(obj.modifiers) - 1}"}
                if bpy.context.object and bpy.context.object.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                    changed_mode = True
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=target_index)
                changes.append(f"move_to_index={target_index}")

            return {
                "success": True,
                "object": name,
                "modifier": mod.name,
                "changes": changes,
                "stack_order": [m.name for m in obj.modifiers],
                "show_viewport": bool(getattr(mod, "show_viewport", True)),
                "show_render": bool(getattr(mod, "show_render", True)),
            }
        except Exception as e:
            return {"error": f"Failed to configure modifier: {str(e)}"}
        finally:
            with suppress(Exception):
                if bpy.context.object and bpy.context.object.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.select_all(action='DESELECT')
                for obj in previous_selection:
                    if obj.name in bpy.data.objects:
                        obj.select_set(True)
                if previous_active and previous_active.name in bpy.data.objects:
                    bpy.context.view_layer.objects.active = previous_active
                if changed_mode and previous_context_object and previous_context_object.name in bpy.data.objects:
                    bpy.context.view_layer.objects.active = previous_context_object
                    previous_context_object.select_set(True)
                    bpy.ops.object.mode_set(mode=previous_mode)

    def configure_constraint(self, name, constraint, influence=None, mute=None):
        """Configure safe constraint flags without changing targets or applying transforms."""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}
            if constraint not in obj.constraints:
                available = [c.name for c in obj.constraints]
                return {"error": f"Constraint '{constraint}' not found on '{name}'. Available: {available}"}

            constraint_obj = obj.constraints[constraint]
            changes = []
            if influence is not None:
                clamped_influence = max(0.0, min(1.0, float(influence)))
                constraint_obj.influence = clamped_influence
                changes.append(f"influence={clamped_influence}")
            if mute is not None:
                constraint_obj.mute = bool(mute)
                changes.append(f"mute={bool(mute)}")

            return {
                "success": True,
                "object": name,
                "constraint": constraint_obj.name,
                "changes": changes,
                "influence": float(getattr(constraint_obj, "influence", 1.0)),
                "mute": bool(getattr(constraint_obj, "mute", False)),
            }
        except Exception as e:
            return {"error": f"Failed to configure constraint: {str(e)}"}

    def add_object_constraint(self, name, constraint_type, constraint_name=None, target_name=None, subtarget=None, influence=None, properties=None):
        """Add an object constraint without freeform Python. constraint_type is the Blender enum such as TRACK_TO, COPY_LOCATION, or LIMIT_ROTATION."""
        constraint_type_value = str(constraint_type or "").upper()
        constraint_obj = None
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}

            if not constraint_type_value:
                return {"error": "constraint_type is required"}

            target_obj = None
            if target_name:
                target_obj = bpy.data.objects.get(str(target_name))
                if not target_obj:
                    return {"error": f"Target object not found: {target_name}"}

            influence_value = None
            if influence is not None:
                influence_value = max(0.0, min(1.0, float(influence)))

            if properties is not None and not isinstance(properties, dict):
                return {"error": "properties must be an object/dict when provided"}

            constraint_obj = obj.constraints.new(type=constraint_type_value)
            if constraint_name:
                constraint_obj.name = str(constraint_name)

            if target_obj:
                constraint_obj.target = target_obj

            if subtarget is not None and hasattr(constraint_obj, "subtarget"):
                constraint_obj.subtarget = str(subtarget)
            if influence_value is not None:
                constraint_obj.influence = influence_value

            property_warnings = []
            if properties:
                for prop_name, prop_value in properties.items():
                    try:
                        setattr(constraint_obj, str(prop_name), prop_value)
                    except (AttributeError, TypeError, ValueError) as prop_err:
                        property_warnings.append(f"Skipped property {prop_name}: {str(prop_err)}")

            warnings = property_warnings

            return {
                "success": True,
                "object": obj.name,
                "constraint": constraint_obj.name,
                "type": constraint_obj.type,
                "target": constraint_obj.target.name if getattr(constraint_obj, "target", None) else None,
                "subtarget": str(getattr(constraint_obj, "subtarget", "")),
                "influence": float(getattr(constraint_obj, "influence", 1.0)),
                "warnings": warnings,
                "next_safe_action": "run inspect_modifier_constraint_stack for this object to verify the new constraint",
            }
        except TypeError as e:
            if constraint_obj:
                with suppress(Exception):
                    obj.constraints.remove(constraint_obj)
            return {"error": f"Invalid constraint type '{constraint_type_value}': {str(e)}"}
        except Exception as e:
            if constraint_obj:
                with suppress(Exception):
                    obj.constraints.remove(constraint_obj)
            return {"error": f"Failed to add object constraint: {str(e)}"}

    def remove_object_constraint(self, name, constraint):
        """Remove an object constraint by name."""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}
            if constraint not in obj.constraints:
                available = [c.name for c in obj.constraints]
                return {"error": f"Constraint '{constraint}' not found on '{name}'. Available: {available}"}

            constraint_obj = obj.constraints[constraint]
            constraint_type = constraint_obj.type
            obj.constraints.remove(constraint_obj)
            return {
                "success": True,
                "object": obj.name,
                "removed_constraint": constraint,
                "type": constraint_type,
                "remaining_constraints": [c.name for c in obj.constraints],
            }
        except Exception as e:
            return {"error": f"Failed to remove object constraint: {str(e)}"}

    def apply_modifier(self, name, modifier):
        """Apply (bake) a modifier on an object and remove it from the stack"""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}
            if modifier not in obj.modifiers:
                available = [m.name for m in obj.modifiers]
                return {"error": f"Modifier '{modifier}' not found on '{name}'. Available: {available}"}

            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_apply(modifier=modifier)

            return {
                "success": True,
                "object": name,
                "applied_modifier": modifier,
                "remaining_modifiers": [m.name for m in obj.modifiers],
            }
        except Exception as e:
            return {"error": f"Failed to apply modifier: {str(e)}"}

    def apply_transforms(self, name, location=True, rotation=True, scale=True):
        """Apply the object's visual transforms to its data (freezes transforms)"""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}

            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.transform_apply(
                location=bool(location),
                rotation=bool(rotation),
                scale=bool(scale),
            )

            applied = []
            if location:
                applied.append("location")
            if rotation:
                applied.append("rotation")
            if scale:
                applied.append("scale")

            return {
                "success": True,
                "object": name,
                "applied": applied,
            }
        except Exception as e:
            return {"error": f"Failed to apply transforms: {str(e)}"}

    def shade_smooth(self, name, smooth=True, angle=None):
        """Set smooth or flat shading on an object. Optional angle for auto-smooth."""
        try:
            import math
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}
            if obj.type != 'MESH':
                return {"error": f"Object '{name}' is type '{obj.type}', shading only works on MESH"}

            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            if smooth:
                if angle is not None:
                    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(float(angle)))
                    mode = f"smooth_by_angle({angle}°)"
                else:
                    bpy.ops.object.shade_smooth()
                    mode = "smooth"
            else:
                bpy.ops.object.shade_flat()
                mode = "flat"

            return {
                "success": True,
                "object": name,
                "shading": mode,
            }
        except Exception as e:
            return {"error": f"Failed to set shading: {str(e)}"}

    # ---------- Phase 2: Medium-Priority Tools ----------

    def parent_set(self, child_name, parent_name, parent_type='OBJECT'):
        """Set parent-child relationship between objects"""
        try:
            child = bpy.data.objects.get(child_name)
            parent = bpy.data.objects.get(parent_name)
            if not child:
                return {"error": f"Child object not found: {child_name}"}
            if not parent:
                return {"error": f"Parent object not found: {parent_name}"}

            bpy.ops.object.select_all(action='DESELECT')
            child.select_set(True)
            parent.select_set(True)
            bpy.context.view_layer.objects.active = parent
            bpy.ops.object.parent_set(type=parent_type, keep_transform=True)

            return {
                "success": True,
                "child": child.name,
                "parent": parent.name,
                "type": parent_type,
            }
        except Exception as e:
            return {"error": f"Failed to set parent: {str(e)}"}

    def parent_clear(self, name, keep_transform=True):
        """Clear parent from an object"""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}
            if not obj.parent:
                return {"error": f"Object '{name}' has no parent"}

            old_parent = obj.parent.name
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            clear_type = 'CLEAR_KEEP_TRANSFORM' if keep_transform else 'CLEAR'
            bpy.ops.object.parent_clear(type=clear_type)

            return {
                "success": True,
                "object": name,
                "old_parent": old_parent,
                "keep_transform": keep_transform,
            }
        except Exception as e:
            return {"error": f"Failed to clear parent: {str(e)}"}

    def set_origin(self, name, origin_type='ORIGIN_GEOMETRY', center='MEDIAN'):
        """Set the origin point of an object"""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}

            valid_types = ['GEOMETRY_ORIGIN', 'ORIGIN_GEOMETRY', 'ORIGIN_CURSOR',
                           'ORIGIN_CENTER_OF_MASS', 'ORIGIN_CENTER_OF_VOLUME']
            if origin_type not in valid_types:
                return {"error": f"Invalid origin type. Must be one of: {valid_types}"}

            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.origin_set(type=origin_type, center=center)

            return {
                "success": True,
                "object": name,
                "origin_type": origin_type,
                "new_origin": list(obj.location),
            }
        except Exception as e:
            return {"error": f"Failed to set origin: {str(e)}"}

    def inspect_export_cleanup_candidates(
        self,
        names=None,
        action="report",
        helper_patterns=None,
        target_collection="Helpers",
        include_hidden=True,
    ):
        """Inspect or safely act on helper/reference/construction objects before export."""
        try:
            def parse_names(value):
                if value is None:
                    return []
                if isinstance(value, str):
                    return [part.strip() for part in value.split(",") if part.strip()]
                if isinstance(value, (list, tuple)):
                    return [str(name).strip() for name in value if str(name).strip()]
                return []

            def parse_bool(value, default=True):
                if value is None:
                    return default
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() in {"1", "true", "yes", "on"}
                return bool(value)

            def pattern_matches(value, patterns):
                normalized = str(value or "").lower()
                for pattern in patterns:
                    token = str(pattern).strip().lower()
                    if not token:
                        continue
                    if token.startswith("*") and token.endswith("*") and token.strip("*") in normalized:
                        return True
                    if token.endswith("*") and normalized.startswith(token[:-1]):
                        return True
                    if token.startswith("*") and normalized.endswith(token[1:]):
                        return True
                    if normalized == token or token in normalized:
                        return True
                return False

            requested_names = parse_names(names)
            requested_set = set(requested_names)
            if helper_patterns is None:
                helper_patterns = [
                    "helper", "helpers", "reference", "ref_", "guide", "construction",
                    "cutter", "boolean", "temp", "tmp", "proxy", "debug", "draft"
                ]
            elif isinstance(helper_patterns, str):
                helper_patterns = [part.strip() for part in helper_patterns.split(",") if part.strip()]
            elif not isinstance(helper_patterns, (list, tuple)):
                return {"error": "helper_patterns must be an array, a comma-separated string, or omitted"}

            action = str(action or "report").lower().replace("-", "_")
            if action not in {"report", "hide", "move_to_collection", "delete"}:
                return {"error": "action must be report, hide, move_to_collection, or delete"}

            referenced_object_names = set()
            for obj in bpy.data.objects:
                if obj.parent:
                    referenced_object_names.add(obj.parent.name)
                for constraint in getattr(obj, "constraints", []):
                    target = getattr(constraint, "target", None)
                    if target:
                        referenced_object_names.add(target.name)
                for modifier in getattr(obj, "modifiers", []):
                    target = getattr(modifier, "object", None)
                    if target:
                        referenced_object_names.add(target.name)
                    collection = getattr(modifier, "collection", None)
                    if collection:
                        for collection_obj in collection.objects:
                            referenced_object_names.add(collection_obj.name)

            protected_names = set(requested_set) | referenced_object_names
            candidates = []
            skipped_protected = []
            include_hidden = parse_bool(include_hidden, True)

            for obj in bpy.data.objects:
                reasons = []
                if obj.name in protected_names:
                    skipped_protected.append(obj.name)
                    continue
                if obj.type in {"EMPTY", "CAMERA", "LIGHT"}:
                    reasons.append(f"type:{obj.type}")
                if pattern_matches(obj.name, helper_patterns):
                    reasons.append("name_pattern")
                collection_names = [collection.name for collection in obj.users_collection]
                if any(pattern_matches(collection_name, helper_patterns) for collection_name in collection_names):
                    reasons.append("collection_pattern")
                if include_hidden and (obj.hide_viewport or obj.hide_render):
                    reasons.append("hidden")
                if not reasons:
                    continue
                candidates.append({
                    "name": obj.name,
                    "type": obj.type,
                    "collections": collection_names,
                    "hide_viewport": bool(obj.hide_viewport),
                    "hide_render": bool(obj.hide_render),
                    "reasons": sorted(set(reasons)),
                })

            changed_objects = []
            target_col = None
            if action == "move_to_collection" and candidates:
                target_col = bpy.data.collections.get(str(target_collection or "Helpers"))
                if not target_col:
                    target_col = bpy.data.collections.new(str(target_collection or "Helpers"))
                    bpy.context.scene.collection.children.link(target_col)

            for candidate in candidates:
                obj = bpy.data.objects.get(candidate["name"])
                if not obj:
                    continue
                if action == "hide":
                    obj.hide_viewport = True
                    obj.hide_render = True
                    changed_objects.append(obj.name)
                elif action == "move_to_collection":
                    if obj.name not in target_col.objects:
                        target_col.objects.link(obj)
                    for collection in list(obj.users_collection):
                        if collection != target_col and len(obj.users_collection) > 1:
                            collection.objects.unlink(obj)
                    changed_objects.append(obj.name)
                elif action == "delete":
                    changed_objects.append(obj.name)
                    bpy.data.objects.remove(obj, do_unlink=True)

            return {
                "success": True,
                "action": action,
                "candidate_count": len(candidates),
                "candidates": candidates,
                "changed_objects": changed_objects,
                "protected_names": sorted(protected_names),
                "referenced_object_names": sorted(referenced_object_names),
                "skipped_protected_count": len(set(skipped_protected)),
                "helper_patterns": list(helper_patterns),
                "target_collection": target_col.name if target_col else target_collection,
                "next_safe_action": "validate_export_readiness before export_asset_package",
            }
        except Exception as e:
            return {"error": f"Failed to inspect export cleanup candidates: {str(e)}"}

    def move_to_collection(self, name, collection_name, create_new=False):
        """Move an object to a collection. Optionally create the collection if it doesn't exist."""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}

            target_col = bpy.data.collections.get(collection_name)
            if not target_col:
                if create_new:
                    target_col = bpy.data.collections.new(collection_name)
                    bpy.context.scene.collection.children.link(target_col)
                else:
                    available = [c.name for c in bpy.data.collections]
                    return {"error": f"Collection '{collection_name}' not found. Available: {available}. Set create_new=true to create it."}

            # Link to target collection
            if obj.name not in target_col.objects:
                target_col.objects.link(obj)

            # Unlink from all other collections
            for col in obj.users_collection:
                if col != target_col:
                    col.objects.unlink(obj)

            return {
                "success": True,
                "object": name,
                "collection": target_col.name,
                "created_new": create_new and not bpy.data.collections.get(collection_name),
            }
        except Exception as e:
            return {"error": f"Failed to move to collection: {str(e)}"}

    def organize_collection_hierarchy(
        self,
        collection_name=None,
        object_names=None,
        create_collection=True,
        move_objects=True,
        parent_name=None,
        clear_parent=False,
        hide_viewport=None,
        hide_render=None,
        collection_hide_viewport=None,
        collection_hide_render=None,
    ):
        """Batch organize collections, object membership, parenting, and visibility while preserving transforms."""
        try:
            if object_names is None:
                requested_names = []
            elif isinstance(object_names, str):
                requested_names = [part.strip() for part in object_names.split(",") if part.strip()]
            elif isinstance(object_names, (list, tuple)):
                requested_names = [str(name).strip() for name in object_names if str(name).strip()]
            else:
                return {"error": "object_names must be an array of object names, a comma-separated string, or omitted"}
            requested_names = list(dict.fromkeys(requested_names))

            objects = []
            missing_objects = []
            for obj_name in requested_names:
                obj = bpy.data.objects.get(obj_name)
                if obj:
                    objects.append(obj)
                else:
                    missing_objects.append(obj_name)

            if parent_name and clear_parent:
                return {"error": "Use either parent_name or clear_parent, not both"}

            parent_obj = None
            if parent_name:
                parent_obj = bpy.data.objects.get(parent_name)
                if not parent_obj:
                    return {"error": f"Parent object not found: {parent_name}", "missing_objects": missing_objects}
                if parent_obj.name in [obj.name for obj in objects]:
                    return {
                        "error": "parent_name cannot be one of the objects being organized",
                        "parent": parent_obj.name,
                        "missing_objects": missing_objects,
                    }

            target_col = None
            created_collection = False
            if collection_name:
                target_col = bpy.data.collections.get(collection_name)
                if not target_col:
                    if not create_collection:
                        return {"error": f"Collection '{collection_name}' not found", "missing_objects": missing_objects}
                    target_col = bpy.data.collections.new(collection_name)
                    bpy.context.scene.collection.children.link(target_col)
                    created_collection = True

            moved_objects = []
            parented_objects = []
            cleared_parent_objects = []
            visibility_changes = []

            if target_col and (collection_hide_viewport is not None or collection_hide_render is not None):
                if collection_hide_viewport is not None:
                    target_col.hide_viewport = bool(collection_hide_viewport)
                    visibility_changes.append(f"{target_col.name}.hide_viewport={bool(collection_hide_viewport)}")
                if collection_hide_render is not None:
                    target_col.hide_render = bool(collection_hide_render)
                    visibility_changes.append(f"{target_col.name}.hide_render={bool(collection_hide_render)}")

            for obj in objects:
                if target_col and move_objects:
                    if obj.name not in target_col.objects:
                        target_col.objects.link(obj)
                    for col in list(obj.users_collection):
                        if col != target_col:
                            col.objects.unlink(obj)
                    moved_objects.append(obj.name)

                if parent_obj:
                    world_matrix = obj.matrix_world.copy()
                    obj.parent = parent_obj
                    obj.matrix_parent_inverse = parent_obj.matrix_world.inverted_safe()
                    obj.matrix_world = world_matrix
                    parented_objects.append(obj.name)
                elif clear_parent and obj.parent:
                    world_matrix = obj.matrix_world.copy()
                    obj.parent = None
                    obj.matrix_world = world_matrix
                    cleared_parent_objects.append(obj.name)

                if hide_viewport is not None:
                    obj.hide_viewport = bool(hide_viewport)
                    visibility_changes.append(f"{obj.name}.hide_viewport={bool(hide_viewport)}")
                if hide_render is not None:
                    obj.hide_render = bool(hide_render)
                    visibility_changes.append(f"{obj.name}.hide_render={bool(hide_render)}")

            warnings = []
            if missing_objects:
                warnings.append(f"Missing object(s): {', '.join(missing_objects)}")

            return {
                "success": bool(objects) or not requested_names,
                "collection": target_col.name if target_col else None,
                "created_collection": created_collection,
                "object_count": len(objects),
                "moved_objects": moved_objects,
                "parent": parent_obj.name if parent_obj else None,
                "parented_objects": parented_objects,
                "cleared_parent_objects": cleared_parent_objects,
                "visibility_changes": visibility_changes,
                "missing_objects": missing_objects,
                "warnings": warnings,
                "next_safe_action": "run inspect_collection_hierarchy for the changed objects or collection to verify organization",
            }
        except Exception as e:
            return {"error": f"Failed to organize collection hierarchy: {str(e)}"}

    def set_visibility(self, name, hide_viewport=None, hide_render=None):
        """Set viewport and/or render visibility for an object"""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}

            changes = []
            if hide_viewport is not None:
                obj.hide_viewport = bool(hide_viewport)
                changes.append(f"hide_viewport={hide_viewport}")
            if hide_render is not None:
                obj.hide_render = bool(hide_render)
                changes.append(f"hide_render={hide_render}")

            if not changes:
                return {"error": "Provide hide_viewport and/or hide_render"}

            return {
                "success": True,
                "object": name,
                "hide_viewport": obj.hide_viewport,
                "hide_render": obj.hide_render,
                "changes": changes,
            }
        except Exception as e:
            return {"error": f"Failed to set visibility: {str(e)}"}

    def _resolve_mesh_objects(self, names):
        raw_names = names if isinstance(names, list) else [names]
        objects = []
        missing = []
        non_mesh = []
        for raw_name in raw_names:
            obj = bpy.data.objects.get(str(raw_name))
            if not obj:
                missing.append(str(raw_name))
            elif obj.type != "MESH":
                non_mesh.append(obj.name)
            else:
                objects.append(obj)
        return objects, missing, non_mesh

    def _collect_uv_stats(self, obj):
        mesh = obj.data
        uv_layers = list(mesh.uv_layers)
        active_layer = mesh.uv_layers.active
        bounds = None
        faces_without_uvs = len(mesh.polygons)
        degenerate_uv_faces = 0
        outside_unit_square = False

        if active_layer and len(active_layer.data) > 0:
            u_values = []
            v_values = []
            faces_without_uvs = 0
            for polygon in mesh.polygons:
                coords = []
                face_has_uvs = True
                for loop_index in polygon.loop_indices:
                    if loop_index >= len(active_layer.data):
                        face_has_uvs = False
                        continue
                    uv = active_layer.data[loop_index].uv
                    if not math.isfinite(uv.x) or not math.isfinite(uv.y):
                        face_has_uvs = False
                        continue
                    coords.append((uv.x, uv.y))
                    u_values.append(uv.x)
                    v_values.append(uv.y)
                if not face_has_uvs or len(coords) < 3:
                    faces_without_uvs += 1
                    continue
                area = 0.0
                for idx, (u_a, v_a) in enumerate(coords):
                    u_b, v_b = coords[(idx + 1) % len(coords)]
                    area += (u_a * v_b) - (u_b * v_a)
                if abs(area) * 0.5 < 1e-8:
                    degenerate_uv_faces += 1
            if u_values and v_values:
                bounds = {
                    "min_u": min(u_values),
                    "max_u": max(u_values),
                    "min_v": min(v_values),
                    "max_v": max(v_values),
                }
                outside_unit_square = (
                    bounds["min_u"] < -0.001
                    or bounds["max_u"] > 1.001
                    or bounds["min_v"] < -0.001
                    or bounds["max_v"] > 1.001
                )

        return {
            "object": obj.name,
            "mesh": mesh.name,
            "uv_layer_count": len(uv_layers),
            "uv_layers": [layer.name for layer in uv_layers],
            "active_uv": active_layer.name if active_layer else None,
            "has_uvs": bool(active_layer and len(active_layer.data) > 0),
            "faces": len(mesh.polygons),
            "loops": len(mesh.loops),
            "faces_without_uvs": faces_without_uvs,
            "degenerate_uv_faces": degenerate_uv_faces,
            "outside_unit_square": outside_unit_square,
            "bounds": bounds,
        }

    def _texture_path_warnings(self, obj, check_texture_formats=True):
        warnings = []
        missing_paths = []
        packed_images = []
        risky_images = []
        empty_texture_paths = []
        dependencies = []
        risky_extensions = {".avif", ".heic", ".heif", ".psd", ".tif", ".tiff", ".webp"}
        for slot in obj.material_slots:
            mat = slot.material
            if not mat or not mat.use_nodes:
                continue
            for node in mat.node_tree.nodes:
                if node.bl_idname != "ShaderNodeTexImage" or not getattr(node, "image", None):
                    continue
                image = node.image
                raw_path = getattr(image, "filepath", "")
                library = getattr(image, "library", None) or getattr(mat, "library", None)
                extension = os.path.splitext(str(raw_path))[1].lower() if raw_path else ""
                dependency = {
                    "object": obj.name,
                    "material": mat.name,
                    "node": node.name,
                    "image": image.name,
                    "source": getattr(image, "source", ""),
                    "colorspace": getattr(getattr(image, "colorspace_settings", None), "name", ""),
                    "filepath": raw_path or "",
                    "resolved_path": "",
                    "exists": False,
                    "packed": bool(getattr(image, "packed_file", None)),
                    "extension": extension,
                    "risky_format": extension in risky_extensions,
                }
                if image.packed_file:
                    packed_images.append(image.name)
                    dependency["exists"] = True
                    dependencies.append(dependency)
                    continue
                if not raw_path:
                    empty_entry = {"object": obj.name, "material": mat.name, "image": image.name, "node": node.name}
                    empty_texture_paths.append(empty_entry)
                    dependencies.append(dependency)
                    continue
                absolute_path = bpy.path.abspath(raw_path, library=library)
                dependency["resolved_path"] = absolute_path
                dependency["exists"] = os.path.exists(absolute_path)
                if not os.path.exists(absolute_path):
                    missing_paths.append({"object": obj.name, "material": mat.name, "image": image.name, "node": node.name, "path": absolute_path})
                extension = os.path.splitext(absolute_path)[1].lower()
                dependency["extension"] = extension
                dependency["risky_format"] = extension in risky_extensions
                if check_texture_formats and extension in risky_extensions:
                    risky_images.append({"image": image.name, "path": absolute_path, "extension": extension})
                dependencies.append(dependency)

        if empty_texture_paths:
            warnings.append(f"{obj.name}: {len(empty_texture_paths)} image texture node(s) have empty filepaths")
        if missing_paths:
            warnings.append(f"{obj.name}: {len(missing_paths)} image texture path(s) are missing")
        if risky_images:
            warnings.append(f"{obj.name}: {len(risky_images)} texture image(s) use formats that are risky for portable GLB/FBX/OBJ delivery; prefer PNG or JPEG")
        return warnings, missing_paths, packed_images, risky_images, empty_texture_paths, dependencies

    def inspect_export_texture_dependencies(self, names, file_format="GLB", max_dependencies=200, check_texture_formats=True):
        """Inspect image texture dependencies for export without mutating the scene."""
        try:
            objects, missing, non_mesh = self._resolve_mesh_objects(names)
            try:
                max_dependencies = max(1, int(max_dependencies))
            except (TypeError, ValueError):
                max_dependencies = 200
            if isinstance(check_texture_formats, str):
                check_texture_formats = check_texture_formats.strip().lower() in {"1", "true", "yes", "on"}
            else:
                check_texture_formats = bool(check_texture_formats)

            errors = []
            warnings = []
            if missing:
                errors.append(f"Object not found: {', '.join(missing)}")
            if non_mesh:
                warnings.append(f"Non-mesh object(s) skipped: {', '.join(non_mesh)}")
            if not objects:
                errors.append("No mesh objects provided")

            dependency_entries = []
            object_reports = []
            missing_textures = []
            empty_texture_paths = []
            packed_images = []
            risky_texture_formats = []

            for obj in objects:
                texture_warnings, object_missing, object_packed, object_risky, object_empty, object_dependencies = self._texture_path_warnings(obj, check_texture_formats=check_texture_formats)
                warnings.extend(texture_warnings)
                missing_textures.extend(object_missing)
                empty_texture_paths.extend(object_empty)
                packed_images.extend({"object": obj.name, "image": image_name} for image_name in object_packed)
                risky_texture_formats.extend(object_risky)
                dependency_entries.extend(object_dependencies)
                object_reports.append({
                    "object": obj.name,
                    "material_slots": len(obj.material_slots),
                    "dependency_count": len(object_dependencies),
                    "missing_texture_count": len(object_missing),
                    "empty_texture_path_count": len(object_empty),
                    "packed_image_count": len(object_packed),
                    "risky_texture_format_count": len(object_risky),
                })

            status = "healthy"
            if errors or missing_textures:
                status = "error"
            elif empty_texture_paths or risky_texture_formats:
                status = "warning"

            fmt = str(file_format or "GLB").upper()
            return {
                "success": True,
                "status": status,
                "format": fmt,
                "objects": object_reports,
                "dependency_count": len(dependency_entries),
                "dependencies": dependency_entries[:max_dependencies],
                "has_more_dependencies": len(dependency_entries) > max_dependencies,
                "missing_texture_count": len(missing_textures),
                "missing_textures": missing_textures[:max_dependencies],
                "empty_texture_path_count": len(empty_texture_paths),
                "empty_texture_paths": empty_texture_paths[:max_dependencies],
                "packed_image_count": len(packed_images),
                "packed_images": packed_images[:max_dependencies],
                "risky_texture_format_count": len(risky_texture_formats),
                "risky_texture_formats": risky_texture_formats[:max_dependencies],
                "errors": errors,
                "warnings": warnings,
                "next_safe_action": "fix missing/empty texture paths before export_asset_package" if status == "error" else "validate_export_readiness before export_asset_package",
            }
        except Exception as e:
            return {"error": f"Failed to inspect export texture dependencies: {str(e)}"}

    def prepare_uv_layout(
        self,
        names,
        mode="preserve_original",
        uv_map_name=None,
        angle_limit=66.0,
        island_margin=0.003,
        rotate=True,
        scale=True,
    ):
        """Preserve, create, or pack UVs for mesh objects with structured validation output."""
        previous_active = bpy.context.view_layer.objects.active
        previous_selection = [obj for obj in bpy.context.scene.objects if obj.select_get()]
        previous_mode = previous_active.mode if previous_active else "OBJECT"
        try:
            objects, missing, non_mesh = self._resolve_mesh_objects(names)
            errors = []
            warnings = []
            if missing:
                errors.append(f"Object not found: {', '.join(missing)}")
            if non_mesh:
                warnings.append(f"Skipped non-mesh object(s): {', '.join(non_mesh)}")
            if not objects:
                return {"error": "; ".join(errors or ["No mesh objects provided"]), "warnings": warnings}

            mode_key = str(mode or "preserve_original").lower().replace("-", "_")
            supported_modes = {"preserve_original", "smart_project", "lightmap_pack", "pack_existing"}
            if mode_key not in supported_modes:
                return {
                    "error": f"Unsupported UV mode: {mode}. Supported modes: {', '.join(sorted(supported_modes))}",
                    "warnings": warnings,
                }

            if bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")

            changed_objects = []
            before = {obj.name: self._collect_uv_stats(obj) for obj in objects}
            margin_value = max(0.0, min(0.25, float(island_margin)))

            for obj in objects:
                bpy.ops.object.select_all(action="DESELECT")
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj

                if uv_map_name:
                    existing_layer = obj.data.uv_layers.get(str(uv_map_name))
                    if existing_layer:
                        obj.data.uv_layers.active = existing_layer
                    else:
                        obj.data.uv_layers.active = obj.data.uv_layers.new(name=str(uv_map_name))
                elif not obj.data.uv_layers and mode_key != "preserve_original":
                    obj.data.uv_layers.new(name="UVMap")

                if mode_key == "preserve_original":
                    if not obj.data.uv_layers:
                        warnings.append(f"{obj.name}: no UV layer to preserve")
                    continue

                if mode_key == "pack_existing" and not obj.data.uv_layers:
                    warnings.append(f"{obj.name}: no UV layer available to pack")
                    continue

                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.mesh.select_all(action="SELECT")
                if mode_key == "smart_project":
                    bpy.ops.uv.smart_project(
                        angle_limit=math.radians(float(angle_limit)),
                        island_margin=margin_value,
                        correct_aspect=True,
                        scale_to_bounds=False,
                    )
                elif mode_key == "lightmap_pack":
                    bpy.ops.uv.lightmap_pack(
                        PREF_CONTEXT="SEL_FACES",
                        PREF_PACK_IN_ONE=True,
                        PREF_NEW_UVLAYER=False,
                        PREF_MARGIN_DIV=max(0.001, margin_value),
                    )
                elif mode_key == "pack_existing":
                    bpy.ops.uv.pack_islands(
                        rotate=bool(rotate),
                        scale=bool(scale),
                        margin=margin_value,
                    )
                bpy.ops.object.mode_set(mode="OBJECT")
                changed_objects.append(obj.name)

            after = {obj.name: self._collect_uv_stats(obj) for obj in objects}
            ready = not errors and all(stats["has_uvs"] for stats in after.values())
            return {
                "success": True,
                "ready": ready,
                "mode": mode_key,
                "changed_objects": changed_objects,
                "before": before,
                "after": after,
                "errors": errors,
                "warnings": warnings,
            }
        except Exception as e:
            return {"error": f"Failed to prepare UV layout: {str(e)}"}
        finally:
            with suppress(Exception):
                if bpy.context.object and bpy.context.object.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.select_all(action="DESELECT")
                for obj in previous_selection:
                    if obj.name in bpy.data.objects:
                        obj.select_set(True)
                if previous_active and previous_active.name in bpy.data.objects:
                    bpy.context.view_layer.objects.active = previous_active
                    if previous_mode != "OBJECT":
                        bpy.ops.object.mode_set(mode=previous_mode)

    def validate_export_readiness(
        self,
        names,
        filepath=None,
        file_format="GLB",
        required_uvs=True,
        require_materials=False,
        require_applied_transforms=True,
        check_textures=True,
        check_texture_formats=True,
        require_absolute_path=True,
    ):
        """Validate object, UV, material, texture, transform, and filepath readiness before export."""
        try:
            objects, missing, non_mesh = self._resolve_mesh_objects(names)
            fmt = str(file_format or "GLB").upper()
            supported_formats = {"GLB", "GLTF", "FBX", "OBJ", "STL"}
            errors = []
            warnings = []
            object_reports = []

            if fmt not in supported_formats:
                errors.append(f"Unsupported format: {file_format}. Use GLB, GLTF, FBX, OBJ, or STL.")
            if missing:
                errors.append(f"Object not found: {', '.join(missing)}")
            if non_mesh:
                warnings.append(f"Non-mesh object(s) will be skipped by validation: {', '.join(non_mesh)}")
            if not objects:
                errors.append("No mesh objects provided")

            expected_files = []
            if filepath:
                raw_filepath = str(filepath)
                if require_absolute_path and not os.path.isabs(raw_filepath):
                    errors.append("Export filepath must be absolute; use a full path before calling export_object")
                absolute_filepath = bpy.path.abspath(str(filepath))
                output_dir = os.path.dirname(absolute_filepath)
                extension = os.path.splitext(absolute_filepath)[1].lower()
                expected_extension = {
                    "GLB": ".glb",
                    "GLTF": ".gltf",
                    "FBX": ".fbx",
                    "OBJ": ".obj",
                    "STL": ".stl",
                }[fmt] if fmt in supported_formats else None
                if expected_extension and extension != expected_extension:
                    warnings.append(f"File extension {extension or '(none)'} does not match {fmt}; expected {expected_extension}")
                if output_dir and not os.path.exists(output_dir):
                    warnings.append(f"Output directory does not exist yet: {output_dir}")
                elif output_dir and not os.access(output_dir, os.W_OK):
                    errors.append(f"Output directory is not writable: {output_dir}")
                expected_files.append(absolute_filepath)
                if fmt == "OBJ":
                    expected_files.append(os.path.splitext(absolute_filepath)[0] + ".mtl")
                elif fmt == "GLTF":
                    expected_files.append(os.path.splitext(absolute_filepath)[0] + ".bin")
            else:
                absolute_filepath = None
                warnings.append("No filepath provided; export_object still needs an absolute output path")

            for obj in objects:
                mesh = obj.data
                uv_stats = self._collect_uv_stats(obj)
                mesh_copy = mesh.copy()
                try:
                    mesh_changed_by_validation = bool(mesh_copy.validate(verbose=False))
                finally:
                    bpy.data.meshes.remove(mesh_copy)

                material_count = sum(1 for slot in obj.material_slots if slot.material)
                if check_textures:
                    texture_warnings, missing_textures, packed_images, risky_textures, empty_texture_paths, texture_dependencies = self._texture_path_warnings(obj, check_texture_formats=check_texture_formats)
                else:
                    texture_warnings, missing_textures, packed_images, risky_textures, empty_texture_paths, texture_dependencies = [], [], [], [], [], []
                warnings.extend(texture_warnings)
                if check_texture_formats and fmt in {"GLB", "GLTF", "FBX", "OBJ"} and risky_textures:
                    warnings.append(f"{obj.name}: convert risky texture format(s) to PNG/JPEG before export for the safest viewer compatibility")

                transform_issues = []
                if require_applied_transforms:
                    if any(abs(value - 1.0) > 1e-4 for value in obj.scale):
                        transform_issues.append("scale is not applied")
                    if any(abs(value) > 1e-4 for value in obj.rotation_euler):
                        transform_issues.append("rotation is not applied")
                if transform_issues:
                    warnings.append(f"{obj.name}: {', '.join(transform_issues)}")

                if required_uvs and fmt not in {"STL"} and not uv_stats["has_uvs"]:
                    errors.append(f"{obj.name}: missing active UV layout")
                if required_uvs and fmt not in {"STL"} and uv_stats["faces_without_uvs"] > 0:
                    errors.append(f"{obj.name}: {uv_stats['faces_without_uvs']} face(s) have incomplete UV coordinates")
                if required_uvs and fmt not in {"STL"} and uv_stats["degenerate_uv_faces"] > 0:
                    warnings.append(f"{obj.name}: {uv_stats['degenerate_uv_faces']} face(s) have degenerate UV islands")
                if required_uvs and fmt not in {"STL"} and uv_stats["outside_unit_square"]:
                    warnings.append(f"{obj.name}: active UV bounds extend outside the 0-1 texture tile")
                if require_materials and fmt not in {"STL"} and material_count == 0:
                    errors.append(f"{obj.name}: no material assigned")
                if mesh_changed_by_validation:
                    errors.append(f"{obj.name}: mesh.validate() reports invalid geometry")

                object_reports.append({
                    "object": obj.name,
                    "type": obj.type,
                    "vertices": len(mesh.vertices),
                    "faces": len(mesh.polygons),
                    "materials": material_count,
                    "uv": uv_stats,
                    "mesh_valid": not mesh_changed_by_validation,
                    "texture_dependencies": texture_dependencies,
                    "missing_textures": missing_textures,
                    "empty_texture_paths": empty_texture_paths,
                    "packed_images": packed_images,
                    "risky_texture_formats": risky_textures,
                    "transform_issues": transform_issues,
                })

            if fmt == "STL" and require_materials:
                warnings.append("STL does not preserve materials; disable require_materials or choose GLB/FBX/OBJ")
            if fmt == "OBJ":
                warnings.append("OBJ exports material data as a sidecar .mtl file; keep both files together")
            if fmt == "GLTF":
                warnings.append("GLTF separate export may create sidecar buffer/texture files; GLB is safer for a single-file web asset")

            return {
                "success": True,
                "ready": len(errors) == 0,
                "format": fmt,
                "filepath": absolute_filepath,
                "expected_files": expected_files,
                "objects": object_reports,
                "errors": errors,
                "warnings": warnings,
                "next_safe_action": "export_object" if len(errors) == 0 else "fix reported errors before export_object",
            }
        except Exception as e:
            return {"error": f"Failed to validate export readiness: {str(e)}"}

    def export_asset_package(
        self,
        names,
        filepath,
        file_format="GLB",
        uv_mode="preserve_original",
        apply_transforms=False,
        required_uvs=True,
        require_materials=False,
        check_textures=True,
        check_texture_formats=True,
        make_dirs=True,
        force_export=False,
    ):
        """Run UV prep, export readiness validation, optional transform apply, and export in one safe step."""
        previous_active = bpy.context.view_layer.objects.active
        previous_selection = [obj for obj in bpy.context.scene.objects if obj.select_get()]
        previous_mode = previous_active.mode if previous_active else "OBJECT"
        try:
            if not filepath:
                return {"error": "filepath is required"}

            def coerce_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() in {"1", "true", "yes", "on"}
                return bool(value)

            objects, missing, non_mesh = self._resolve_mesh_objects(names)
            if missing:
                return {"error": f"Object not found: {', '.join(missing)}"}
            if not objects:
                return {"error": "No mesh objects provided"}

            absolute_filepath = bpy.path.abspath(str(filepath))
            output_dir = os.path.dirname(absolute_filepath)
            if output_dir and not os.path.exists(output_dir):
                if coerce_bool(make_dirs, True):
                    os.makedirs(output_dir, exist_ok=True)
                else:
                    return {"error": f"Output directory does not exist: {output_dir}"}

            uv_report = None
            mode_key = str(uv_mode or "none").lower().replace("-", "_")
            if mode_key not in {"none", "skip", "preserve_original", "smart_project", "lightmap_pack", "pack_existing"}:
                return {"error": "uv_mode must be none, preserve_original, smart_project, lightmap_pack, or pack_existing"}
            if mode_key not in {"none", "skip"}:
                uv_report = self.prepare_uv_layout(
                    [obj.name for obj in objects],
                    mode=mode_key,
                )
                if uv_report.get("error"):
                    return {"error": uv_report["error"], "uv_report": uv_report}

            transform_report = {"applied": False, "objects": []}
            if coerce_bool(apply_transforms, False):
                if bpy.context.object and bpy.context.object.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.select_all(action="DESELECT")
                for obj in objects:
                    obj.select_set(True)
                    transform_report["objects"].append(obj.name)
                bpy.context.view_layer.objects.active = objects[0]
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
                transform_report["applied"] = True

            validation = self.validate_export_readiness(
                [obj.name for obj in objects],
                filepath=absolute_filepath,
                file_format=file_format,
                required_uvs=coerce_bool(required_uvs, True),
                require_materials=coerce_bool(require_materials, False),
                require_applied_transforms=not transform_report["applied"],
                check_textures=coerce_bool(check_textures, True),
                check_texture_formats=coerce_bool(check_texture_formats, True),
                require_absolute_path=True,
            )
            if validation.get("error"):
                return {"error": validation["error"], "validation": validation, "uv_report": uv_report}

            should_export = validation.get("ready", False) or coerce_bool(force_export, False)
            if not should_export:
                return {
                    "success": True,
                    "exported": False,
                    "filepath": absolute_filepath,
                    "format": validation.get("format"),
                    "uv_report": uv_report,
                    "transform_report": transform_report,
                    "validation": validation,
                    "errors": validation.get("errors", []),
                    "warnings": validation.get("warnings", []),
                    "next_safe_action": "fix validation errors or call export_asset_package with force_export=true",
                }

            export_result = self.export_object(
                [obj.name for obj in objects],
                absolute_filepath,
                validation.get("format") or file_format,
            )
            if export_result.get("error"):
                return {
                    "error": export_result["error"],
                    "uv_report": uv_report,
                    "transform_report": transform_report,
                    "validation": validation,
                }

            expected_files = validation.get("expected_files") or [absolute_filepath]
            existing_files = [path for path in expected_files if os.path.exists(path)]
            missing_expected_files = [path for path in expected_files if not os.path.exists(path)]

            return {
                "success": True,
                "exported": True,
                "filepath": absolute_filepath,
                "format": validation.get("format"),
                "exported_objects": export_result.get("exported_objects", []),
                "file_size_bytes": export_result.get("file_size_bytes", 0),
                "expected_files": expected_files,
                "existing_files": existing_files,
                "missing_expected_files": missing_expected_files,
                "uv_report": uv_report,
                "transform_report": transform_report,
                "validation": validation,
                "warnings": validation.get("warnings", []),
            }
        except Exception as e:
            return {"error": f"Failed to export asset package: {str(e)}"}
        finally:
            with suppress(Exception):
                if bpy.context.object and bpy.context.object.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.select_all(action="DESELECT")
                for obj in previous_selection:
                    if obj.name in bpy.data.objects:
                        obj.select_set(True)
                if previous_active and previous_active.name in bpy.data.objects:
                    bpy.context.view_layer.objects.active = previous_active
                    if previous_mode != "OBJECT":
                        bpy.ops.object.mode_set(mode=previous_mode)

    def export_object(self, names, filepath, file_format='GLB'):
        """Export selected objects to a file. Supports GLB, GLTF, FBX, OBJ, STL."""
        try:
            import os
            # Validate objects
            objects = []
            for n in (names if isinstance(names, list) else [names]):
                obj = bpy.data.objects.get(n)
                if not obj:
                    return {"error": f"Object not found: {n}"}
                objects.append(obj)

            # Select only the target objects
            bpy.ops.object.select_all(action='DESELECT')
            for obj in objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = objects[0]

            fmt = file_format.upper()
            if fmt in ('GLB', 'GLTF'):
                export_format = 'GLB' if fmt == 'GLB' else 'GLTF_SEPARATE'
                bpy.ops.export_scene.gltf(
                    filepath=filepath,
                    use_selection=True,
                    export_format=export_format,
                )
            elif fmt == 'FBX':
                bpy.ops.export_scene.fbx(
                    filepath=filepath,
                    use_selection=True,
                )
            elif fmt == 'OBJ':
                bpy.ops.wm.obj_export(
                    filepath=filepath,
                    export_selected_objects=True,
                )
            elif fmt == 'STL':
                bpy.ops.wm.stl_export(
                    filepath=filepath,
                    export_selected_objects=True,
                )
            else:
                return {"error": f"Unsupported format: {file_format}. Use GLB, GLTF, FBX, OBJ, or STL."}

            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            return {
                "success": True,
                "exported_objects": [o.name for o in objects],
                "filepath": filepath,
                "format": fmt,
                "file_size_bytes": file_size,
            }
        except Exception as e:
            return {"error": f"Failed to export: {str(e)}"}

    def get_vipermesh_runtime_identity(self):
        """Return a fingerprint that capability sync can bind to this exact add-on runtime."""
        config_directory = bpy.utils.user_resource(
            "CONFIG",
            path="vipermesh",
            create=True,
        )
        device_id_path = os.path.join(
            config_directory,
            "runtime-device-id",
        )
        runtime_device_key = None
        if os.path.isfile(device_id_path):
            with open(device_id_path, "r", encoding="utf-8") as device_file:
                candidate = device_file.read().strip()
            try:
                runtime_device_key = str(uuid.UUID(candidate))
            except (ValueError, AttributeError):
                runtime_device_key = None
        if runtime_device_key is None:
            runtime_device_key = str(uuid.uuid4())
            temporary_path = f"{device_id_path}.tmp"
            with open(temporary_path, "w", encoding="utf-8") as device_file:
                device_file.write(runtime_device_key)
            os.replace(temporary_path, device_id_path)
        addon_path = os.path.abspath(__file__)
        with open(addon_path, "rb") as addon_file:
            source_fingerprint = hashlib.sha256(
                addon_file.read()
            ).hexdigest()
        return {
            "success": True,
            "device_key": runtime_device_key,
            "source_fingerprint": f"sha256:{source_fingerprint}",
            "blender_version": bpy.app.version_string,
            "addon_version": ".".join(
                str(value) for value in bl_info.get("version", ())
            ),
        }

    def validate_gltf_roundtrip(self, filepath, cleanup=True):
        """Temporarily import a glTF/GLB export, report its contents, then remove imported data."""
        imported_objects = []
        created_datablocks = {}
        tracked_collections = {}
        before_names = {}
        previous_selection = list(bpy.context.selected_objects)
        previous_active = bpy.context.view_layer.objects.active
        try:
            absolute_filepath = bpy.path.abspath(str(filepath))
            extension = os.path.splitext(absolute_filepath)[1].lower()
            if extension not in {".glb", ".gltf"}:
                return {"error": "filepath must point to a .glb or .gltf file"}
            if not os.path.isfile(absolute_filepath):
                return {"error": f"glTF file not found: {absolute_filepath}"}

            tracked_collections = {
                "objects": bpy.data.objects,
                "meshes": bpy.data.meshes,
                "materials": bpy.data.materials,
                "images": bpy.data.images,
                "armatures": bpy.data.armatures,
                "actions": bpy.data.actions,
                "collections": bpy.data.collections,
            }
            before_names = {
                key: {block.name for block in collection}
                for key, collection in tracked_collections.items()
            }

            if bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
            import_result = bpy.ops.import_scene.gltf(filepath=absolute_filepath)
            if "FINISHED" not in import_result:
                raise RuntimeError(f"glTF import operator returned {sorted(import_result)}")

            created_datablocks = {
                key: [
                    block
                    for block in collection
                    if block.name not in before_names[key]
                ]
                for key, collection in tracked_collections.items()
            }
            imported_objects = list(created_datablocks["objects"])
            reportable_objects = [
                obj
                for obj in imported_objects
                if not any(
                    collection.name == "glTF_not_exported"
                    for collection in obj.users_collection
                )
            ]
            mesh_objects = [
                obj for obj in reportable_objects if obj.type == "MESH"
            ]
            armature_objects = [
                obj for obj in reportable_objects if obj.type == "ARMATURE"
            ]
            def bound_armatures(obj):
                names = set()
                for modifier in obj.modifiers:
                    if (
                        modifier.type != "ARMATURE"
                        or modifier.object is None
                    ):
                        continue
                    armature = modifier.object
                    bone_names = {
                        bone.name for bone in armature.data.bones
                    }
                    vertex_group_indices = {
                        group.index
                        for group in obj.vertex_groups
                        if group.name in bone_names
                    }
                    has_weighted_vertices = any(
                        assignment.group in vertex_group_indices
                        and assignment.weight > 0
                        for vertex in obj.data.vertices
                        for assignment in vertex.groups
                    )
                    if has_weighted_vertices:
                        names.add(armature.name)
                return sorted(names)

            skinned_mesh_objects = [
                obj
                for obj in mesh_objects
                if bound_armatures(obj)
            ]
            evaluated_triangles = sum(
                max(0, len(poly.vertices) - 2)
                for obj in mesh_objects
                for poly in obj.data.polygons
            )
            material_names = sorted({
                slot.material.name
                for obj in mesh_objects
                for slot in obj.material_slots
                if slot.material
            })
            missing_images = sorted({
                image.name
                for image in created_datablocks["images"]
                if image.source == "FILE"
                and not image.packed_file
                and image.filepath
                and not os.path.isfile(bpy.path.abspath(image.filepath, library=image.library))
            })
            issues = []
            if not reportable_objects:
                issues.append("no_objects_imported")
            if not mesh_objects:
                issues.append("no_meshes_imported")
            if missing_images:
                issues.append("missing_images")
            with open(absolute_filepath, "rb") as checkpoint_file:
                checkpoint_sha256 = hashlib.sha256(
                    checkpoint_file.read()
                ).hexdigest()

            return {
                "success": True,
                "roundtrip_valid": len(issues) == 0,
                "filepath": absolute_filepath,
                "sha256": checkpoint_sha256,
                "file_size_bytes": os.path.getsize(absolute_filepath),
                "object_count": len(reportable_objects),
                "mesh_count": len(mesh_objects),
                "armature_count": len(armature_objects),
                "skinned_mesh_count": len(skinned_mesh_objects),
                "material_count": len(material_names),
                "image_count": len(created_datablocks["images"]),
                "action_count": len(created_datablocks["actions"]),
                "evaluated_triangles": evaluated_triangles,
                "objects": [
                    {"name": obj.name, "type": obj.type}
                    for obj in reportable_objects
                ],
                "skinned_meshes": [
                    {
                        "name": obj.name,
                        "armatures": bound_armatures(obj),
                    }
                    for obj in skinned_mesh_objects
                ],
                "armatures": [
                    {
                        "name": obj.name,
                        "bones": [
                            bone.name for bone in obj.data.bones
                        ],
                    }
                    for obj in armature_objects
                ],
                "materials": material_names,
                "missing_images": missing_images,
                "issues": issues,
                "cleanup_requested": bool(cleanup),
                "next_safe_action": "use the imported evidence to approve the export" if not issues else "fix round-trip issues before approving the export",
            }
        except Exception as e:
            return {"error": f"Failed to validate glTF round trip: {str(e)}"}
        finally:
            if cleanup:
                with suppress(Exception):
                    if before_names:
                        created_datablocks = {
                            key: [block for block in collection if block.name not in before_names[key]]
                            for key, collection in tracked_collections.items()
                        }
                        imported_objects = list(created_datablocks.get("objects", []))
                    if bpy.context.object and bpy.context.object.mode != "OBJECT":
                        bpy.ops.object.mode_set(mode="OBJECT")
                    for obj in imported_objects:
                        if obj.name in bpy.data.objects:
                            bpy.data.objects.remove(obj, do_unlink=True)
                    for key in ("collections", "actions", "armatures", "meshes", "materials", "images"):
                        collection = getattr(bpy.data, key)
                        for block in created_datablocks.get(key, []):
                            if block.name in collection and block.users == 0:
                                collection.remove(block)
                    bpy.ops.object.select_all(action="DESELECT")
                    for obj in previous_selection:
                        if obj.name in bpy.data.objects:
                            obj.select_set(True)
                    if previous_active and previous_active.name in bpy.data.objects:
                        bpy.context.view_layer.objects.active = previous_active

    # ---------- Phase 3: Dynamic Addon Detection ----------

    def list_installed_addons(self):
        """List all enabled Blender addons with metadata for dynamic capability detection"""
        try:
            import addon_utils
            addons = []
            for mod in addon_utils.modules():
                addon_name = mod.__name__
                is_enabled = addon_name in bpy.context.preferences.addons

                if not is_enabled:
                    continue

                info = {
                    "module": addon_name,
                    "name": getattr(mod, "bl_info", {}).get("name", addon_name),
                    "description": getattr(mod, "bl_info", {}).get("description", ""),
                    "category": getattr(mod, "bl_info", {}).get("category", ""),
                    "version": str(getattr(mod, "bl_info", {}).get("version", "")),
                    "author": getattr(mod, "bl_info", {}).get("author", ""),
                }
                addons.append(info)

            return {
                "addons": addons,
                "count": len(addons),
                "blender_version": ".".join(str(v) for v in bpy.app.version),
            }
        except Exception as e:
            return {"error": f"Failed to list addons: {str(e)}"}

    def _json_safe_rna_value(self, value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe_rna_value(item) for item in value]
        try:
            return [self._json_safe_rna_value(item) for item in value]
        except (TypeError, AttributeError):
            return str(value)

    def _find_operator_class(self, operator_id):
        queue = list(bpy.types.Operator.__subclasses__())
        seen = set()
        while queue:
            operator_class = queue.pop()
            if operator_class in seen:
                continue
            seen.add(operator_class)
            if getattr(operator_class, "bl_idname", "") == operator_id:
                return operator_class
            queue.extend(operator_class.__subclasses__())
        return None

    def _operator_callable(self, operator_id):
        if not isinstance(operator_id, str) or operator_id.count(".") != 1:
            raise ValueError("operator_id must use Blender's category.operation form")
        category, operation = operator_id.split(".", 1)
        operator_group = getattr(bpy.ops, category, None)
        operator_callable = getattr(operator_group, operation, None) if operator_group else None
        if operator_callable is None:
            raise ValueError(f"Blender operator is not registered: {operator_id}")
        return operator_callable

    def _rna_property_schema(self, prop):
        scalar_types = {
            "BOOLEAN": "boolean",
            "INT": "integer",
            "FLOAT": "number",
            "STRING": "string",
            "ENUM": "string",
        }
        value_schema = {"type": scalar_types.get(prop.type, "unsupported")}
        supported = prop.type in scalar_types
        if prop.type == "ENUM":
            value_schema["enum"] = [
                item.identifier
                for item in prop.enum_items
                if getattr(item, "identifier", "")
            ]
            if getattr(prop, "is_enum_flag", False):
                value_schema = {
                    "type": "array",
                    "items": value_schema,
                    "uniqueItems": True,
                }
        if prop.type in {"INT", "FLOAT"}:
            value_schema["minimum"] = prop.hard_min
            value_schema["maximum"] = prop.hard_max
        if getattr(prop, "array_length", 0) > 0:
            value_schema = {
                "type": "array",
                "items": value_schema,
                "minItems": prop.array_length,
                "maxItems": prop.array_length,
            }
        default_source = (
            getattr(prop, "default_flag", None)
            if prop.type == "ENUM" and getattr(prop, "is_enum_flag", False)
            else getattr(prop, "default_array", None)
            if getattr(prop, "array_length", 0) > 0
            else getattr(prop, "default", None)
        )
        default = self._json_safe_rna_value(default_source)
        if default is not None:
            value_schema["default"] = default
        return {
            "identifier": prop.identifier,
            "name": prop.name or prop.identifier,
            "description": prop.description or "",
            "schema": value_schema,
            "supported": supported and not prop.is_readonly,
            "read_only": bool(prop.is_readonly),
            "hidden": bool(getattr(prop, "is_hidden", False)),
            "subtype": str(getattr(prop, "subtype", "NONE")),
            "enum_flag": prop.type == "ENUM" and bool(getattr(prop, "is_enum_flag", False)),
        }

    def _inspect_addon_operator(self, addon_module, operator_id, addon_version=""):
        operator_class = self._find_operator_class(operator_id)
        if operator_class is None:
            raise ValueError(f"Unable to resolve operator class: {operator_id}")
        class_module = getattr(operator_class, "__module__", "")
        if class_module != addon_module and not class_module.startswith(f"{addon_module}."):
            raise ValueError(
                f"Operator {operator_id} is owned by {class_module or 'an unknown module'}, "
                f"not {addon_module}"
            )

        operator_callable = self._operator_callable(operator_id)
        properties = []
        for prop in operator_callable.get_rna_type().properties:
            if prop.identifier == "rna_type":
                continue
            properties.append(self._rna_property_schema(prop))
        input_schema = {
            "type": "object",
            "properties": {
                prop["identifier"]: prop["schema"]
                for prop in properties
                if prop["supported"] and not prop["hidden"]
            },
            "additionalProperties": False,
        }
        try:
            poll_available = bool(operator_callable.poll())
            poll_error = None
        except Exception as exc:
            poll_available = False
            poll_error = str(exc)

        fingerprint_payload = {
            "addon_module": addon_module,
            "addon_version": addon_version,
            "blender_version": ".".join(str(v) for v in bpy.app.version),
            "operator_id": operator_id,
            "properties": properties,
            "implementation": self._operator_implementation_fingerprint(operator_class),
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                fingerprint_payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return {
            "operator_id": operator_id,
            "label": getattr(operator_class, "bl_label", "") or operator_id,
            "description": getattr(operator_class, "bl_description", "") or "",
            "class_module": class_module,
            "input_schema": input_schema,
            "properties": properties,
            "poll_available": poll_available,
            "poll_error": poll_error,
            "source_fingerprint": f"sha256:{fingerprint}",
        }

    def _operator_implementation_fingerprint(self, operator_class):
        provenance = {}
        try:
            source_path = inspect.getsourcefile(operator_class)
        except (TypeError, OSError):
            source_path = None
        if source_path and os.path.isfile(source_path):
            digest = hashlib.sha256()
            with open(source_path, "rb") as source:
                for chunk in iter(lambda: source.read(65536), b""):
                    digest.update(chunk)
            provenance["module_sha256"] = digest.hexdigest()
        for name in ("execute", "invoke", "poll", "modal", "draw", "__init__"):
            function = getattr(operator_class, name, None)
            function = getattr(function, "__func__", function)
            code = getattr(function, "__code__", None)
            if code is not None:
                payload = marshal.dumps(code) + repr(getattr(function, "__defaults__", None)).encode("utf-8")
                provenance[name] = hashlib.sha256(payload).hexdigest()
        if not provenance:
            raise ValueError("Operator implementation provenance is unavailable; review a custom invocation instead")
        return provenance

    def _enabled_addon_metadata(self, addon_module):
        import addon_utils

        if addon_module not in bpy.context.preferences.addons:
            raise ValueError(f"Addon is not enabled: {addon_module}")
        for module in addon_utils.modules():
            if module.__name__ != addon_module:
                continue
            bl_info = getattr(module, "bl_info", {})
            version = bl_info.get("version", ())
            version_label = ".".join(str(part) for part in version) if version else ""
            return {
                "module": addon_module,
                "name": bl_info.get("name", addon_module),
                "version": version_label,
                "description": bl_info.get("description", ""),
            }
        return {
            "module": addon_module,
            "name": addon_module,
            "version": "",
            "description": "",
        }

    def inspect_addon_capabilities(
        self,
        addon_module,
        operator_ids=None,
        max_operators=100,
    ):
        """Inspect enabled add-on operators and RNA inputs without executing them."""
        try:
            addon = self._enabled_addon_metadata(addon_module)
            max_operators = max(1, min(int(max_operators), 250))
            if operator_ids is None:
                operator_ids = sorted({
                    getattr(operator_class, "bl_idname", "")
                    for operator_class in self._all_operator_classes()
                    if (
                        getattr(operator_class, "__module__", "") == addon_module
                        or getattr(operator_class, "__module__", "").startswith(
                            f"{addon_module}."
                        )
                    )
                    and getattr(operator_class, "bl_idname", "")
                })
            if not isinstance(operator_ids, (list, tuple)):
                return {"error": "operator_ids must be an array when provided"}

            unique_operator_ids = list(dict.fromkeys(operator_ids))
            capabilities = []
            errors = []
            for operator_id in unique_operator_ids[:max_operators]:
                try:
                    capabilities.append(
                        self._inspect_addon_operator(
                            addon_module,
                            operator_id,
                            addon["version"],
                        )
                    )
                except Exception as exc:
                    errors.append({"operator_id": operator_id, "error": str(exc)})
            inventory_payload = {
                "addon": addon,
                "blender_version": ".".join(str(v) for v in bpy.app.version),
                "capability_fingerprints": [
                    capability["source_fingerprint"] for capability in capabilities
                ],
            }
            inventory_fingerprint = hashlib.sha256(
                json.dumps(
                    inventory_payload,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            return {
                "addon": addon,
                "blender_version": inventory_payload["blender_version"],
                "capabilities": capabilities,
                "count": len(capabilities),
                "total_operator_count": len(unique_operator_ids),
                "truncated": len(unique_operator_ids) > max_operators,
                "errors": errors,
                "inventory_fingerprint": f"sha256:{inventory_fingerprint}",
                "executed_operators": 0,
            }
        except Exception as e:
            return {"error": f"Failed to inspect addon capabilities: {str(e)}"}

    def _all_operator_classes(self):
        queue = list(bpy.types.Operator.__subclasses__())
        seen = set()
        while queue:
            operator_class = queue.pop()
            if operator_class in seen:
                continue
            seen.add(operator_class)
            yield operator_class
            queue.extend(operator_class.__subclasses__())

    def _addon_invocation_scene_state(self):
        active = bpy.context.view_layer.objects.active
        return {
            "object_count": len(bpy.context.scene.objects),
            "objects": sorted(obj.name for obj in bpy.context.scene.objects),
            "selected": sorted(obj.name for obj in bpy.context.selected_objects),
            "active": active.name if active else None,
            "mode": bpy.context.mode,
        }

    def invoke_addon_capability(
        self,
        addon_module,
        operator_id,
        arguments=None,
        expected_source_fingerprint=None,
        dry_run=True,
        approved=False,
        checkpoint_filepath=None,
    ):
        """Dry-run or explicitly invoke one fingerprint-matched enabled add-on operator."""
        try:
            addon = self._enabled_addon_metadata(addon_module)
            capability = self._inspect_addon_operator(
                addon_module,
                operator_id,
                addon["version"],
            )
            if expected_source_fingerprint != capability["source_fingerprint"]:
                return {
                    "error": "Capability fingerprint is missing or stale; inspect again",
                    "actual_source_fingerprint": capability["source_fingerprint"],
                }
            arguments = arguments or {}
            if not isinstance(arguments, dict):
                return {"error": "arguments must be an object"}
            supported_properties = capability["input_schema"]["properties"]
            unknown_arguments = sorted(set(arguments) - set(supported_properties))
            if unknown_arguments:
                return {
                    "error": "Invocation contains unknown or unsupported arguments",
                    "unknown_arguments": unknown_arguments,
                }
            if not capability["poll_available"]:
                return {
                    "error": "Operator is unavailable in the current Blender context",
                    "poll_error": capability["poll_error"],
                }
            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "would_invoke": operator_id,
                    "arguments": arguments,
                    "capability": capability,
                    "executed_operators": 0,
                }
            if approved is not True:
                return {"error": "Explicit approved=true is required for invocation"}
            if (
                not isinstance(checkpoint_filepath, str)
                or not os.path.isabs(checkpoint_filepath)
                or not checkpoint_filepath.lower().endswith(".blend")
            ):
                return {
                    "error": "An absolute .blend checkpoint_filepath is required"
                }

            os.makedirs(os.path.dirname(checkpoint_filepath), exist_ok=True)
            if os.path.exists(checkpoint_filepath):
                return {"error": "Checkpoint already exists; choose a fresh checkpoint path"}
            saved = bpy.ops.wm.save_as_mainfile(filepath=checkpoint_filepath, copy=True)
            if "FINISHED" not in saved or not os.path.isfile(checkpoint_filepath):
                return {"error": "Checkpoint save did not finish; operator was not invoked", "executed_operators": 0}
            enum_flags = {prop["identifier"] for prop in capability["properties"] if prop.get("enum_flag")}
            for key in enum_flags & set(arguments):
                if not isinstance(arguments[key], list) or any(not isinstance(value, str) for value in arguments[key]):
                    return {"error": f"Enum flag argument {key} must be an array of strings", "executed_operators": 0}
            runtime_arguments = {key: set(value) if key in enum_flags else value for key, value in arguments.items()}
            before = self._addon_invocation_scene_state()
            result = self._operator_callable(operator_id)(**runtime_arguments)
            after = self._addon_invocation_scene_state()
            if "FINISHED" not in result:
                return {"success": False, "error": f"Operator did not finish: {sorted(result)}", "checkpoint_filepath": checkpoint_filepath, "executed_operators": 1, "before": before, "after": after}
            return {
                "success": True,
                "dry_run": False,
                "operator_id": operator_id,
                "operator_result": sorted(str(item) for item in result),
                "arguments": arguments,
                "checkpoint_filepath": checkpoint_filepath,
                "source_fingerprint": capability["source_fingerprint"],
                "before": before,
                "after": after,
                "executed_operators": 1,
            }
        except Exception as e:
            return {"error": f"Failed to invoke addon capability: {str(e)}"}

    # ---------- Phase 5: Material / Lighting / Camera / Render Tools ----------

    def create_material(self, name, color=None, metallic=None, roughness=None, use_nodes=True):
        """Create a new Principled BSDF material with optional base color, metallic, and roughness."""
        try:
            mat = bpy.data.materials.new(name=name)
            mat.use_nodes = bool(use_nodes)

            if mat.use_nodes and mat.node_tree:
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                if bsdf:
                    if color is not None:
                        # Accept [R,G,B] or [R,G,B,A] in 0-1 range
                        c = list(color)
                        if len(c) == 3:
                            c.append(1.0)
                        bsdf.inputs["Base Color"].default_value = c
                    if metallic is not None:
                        bsdf.inputs["Metallic"].default_value = float(metallic)
                    if roughness is not None:
                        bsdf.inputs["Roughness"].default_value = float(roughness)

            return {
                "success": True,
                "material": mat.name,
                "use_nodes": mat.use_nodes,
            }
        except Exception as e:
            return {"error": f"Failed to create material: {str(e)}"}

    def assign_material(self, object_name, material_name, slot_index=None):
        """Assign a material to an object. Replaces slot 0 by default (so the material is visible).
        Use slot_index to target a specific slot, or slot_index=-1 to append to a new slot."""
        try:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"Object not found: {object_name}"}
            mat = bpy.data.materials.get(material_name)
            if not mat:
                return {"error": f"Material not found: {material_name}"}

            if slot_index is not None:
                idx = int(slot_index)
                if idx < -1:
                    return {"error": "slot_index must be >= 0, or -1 to append"}
                if idx == -1:
                    # Explicit append mode
                    obj.data.materials.append(mat)
                    assigned_slot = len(obj.material_slots) - 1
                else:
                    # Replace specific slot
                    while len(obj.material_slots) <= idx:
                        obj.data.materials.append(None)
                    obj.material_slots[idx].material = mat
                    assigned_slot = idx
            else:
                # Default: replace slot 0 (or create it) so the material is immediately visible
                if len(obj.material_slots) > 0:
                    obj.material_slots[0].material = mat
                else:
                    obj.data.materials.append(mat)
                assigned_slot = 0

            return {
                "success": True,
                "object": obj.name,
                "material": mat.name,
                "slot": assigned_slot,
                "total_slots": len(obj.material_slots),
            }
        except Exception as e:
            return {"error": f"Failed to assign material: {str(e)}"}

    def _as_rgba(self, color, fallback, clamp=True):
        values = list(color if color is not None else fallback)
        if len(values) == 3:
            values.append(1.0)
        if len(values) != 4:
            raise ValueError("Color values must be [R,G,B] or [R,G,B,A]")
        if clamp:
            return tuple(float(max(0.0, min(1.0, value))) for value in values)
        return tuple(float(value) for value in values)

    def _set_socket_value(self, node, socket_name, value, warnings):
        socket = node.inputs.get(socket_name) if node else None
        if socket is None:
            warnings.append(f"Socket not found on Principled BSDF: {socket_name}")
            return False
        socket.default_value = value
        return True

    def _load_material_image(self, path, role, warnings):
        absolute_path = bpy.path.abspath(str(path))
        if not absolute_path:
            warnings.append(f"Texture path for {role} is empty")
            return None
        if not os.path.exists(absolute_path):
            warnings.append(f"Texture file for {role} does not exist: {absolute_path}")
            return None
        image = bpy.data.images.load(absolute_path, check_existing=True)
        try:
            if role in {"base_color", "emission"}:
                image.colorspace_settings.name = "sRGB"
            else:
                image.colorspace_settings.name = "Non-Color"
        except Exception as exc:
            warnings.append(f"Could not set color space for {role}: {str(exc)}")
        return image

    def create_pbr_material_from_textures(
        self,
        name,
        texture_directory=None,
        texture_paths=None,
        object_name=None,
        preset="dielectric",
        recursive=False,
        max_files=200,
        replace_existing=False,
        slot_index=None,
    ):
        """Infer common PBR texture roles, then create a deterministic material preset."""
        try:
            supported_extensions = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".webp", ".bmp", ".tga"}
            role_aliases = {
                "base_color": ["basecolor", "base_color", "albedo", "diffuse", "color", "col"],
                "normal": ["normal", "normalmap", "normal_map", "nrm"],
                "roughness": ["roughness", "rough", "rgh"],
                "metallic": ["metallic", "metalness", "mtl"],
                "emission": ["emission", "emissive", "emit"],
                "displacement": ["displacement", "height", "disp"],
            }
            role_priority = [
                "normal",
                "roughness",
                "metallic",
                "base_color",
                "emission",
                "displacement",
            ]

            def coerce_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, str):
                    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(value)

            def coerce_positive_int(value, default, minimum=1, maximum=1000):
                try:
                    parsed = int(value)
                except Exception:
                    return default
                return max(minimum, min(maximum, parsed))

            def normalize_token(value):
                token = str(value or "").strip().lower()
                for separator in (" ", "-", ".", "__"):
                    token = token.replace(separator, "_")
                return token

            def alias_matches(tokens, alias):
                alias_tokens = [token for token in normalize_token(alias).split("_") if token]
                if not alias_tokens:
                    return False
                if len(alias_tokens) == 1:
                    return alias_tokens[0] in tokens
                for index in range(0, len(tokens) - len(alias_tokens) + 1):
                    if tokens[index:index + len(alias_tokens)] == alias_tokens:
                        return True
                return False

            def infer_role(path):
                stem = os.path.splitext(os.path.basename(str(path)))[0]
                tokens = [token for token in normalize_token(stem).split("_") if token]
                for role in role_priority:
                    if any(alias_matches(tokens, alias) for alias in role_aliases[role]):
                        return role
                return None

            recursive = coerce_bool(recursive, False)
            max_files = coerce_positive_int(max_files, 200)
            warnings = []
            ignored_textures = []
            ambiguous_textures = []
            collected_paths = []

            def append_collected_path(path):
                if len(collected_paths) >= max_files:
                    return False
                collected_paths.append(path)
                return True

            if texture_directory:
                directory_path = bpy.path.abspath(str(texture_directory))
                if not os.path.isdir(directory_path):
                    return {"error": f"Texture directory not found: {directory_path}"}
                if recursive:
                    for root, _dirs, files in os.walk(directory_path):
                        if len(collected_paths) >= max_files:
                            break
                        for filename in files:
                            if not append_collected_path(os.path.join(root, filename)):
                                break
                else:
                    for filename in os.listdir(directory_path):
                        if not append_collected_path(os.path.join(directory_path, filename)):
                            break

            if texture_paths:
                if isinstance(texture_paths, str):
                    append_collected_path(texture_paths)
                elif isinstance(texture_paths, (list, tuple)):
                    for texture_path in texture_paths:
                        if not append_collected_path(texture_path):
                            break
                else:
                    return {"error": "texture_paths must be a string or list of strings"}

            unique_paths = []
            seen_paths = set()
            for raw_path in collected_paths:
                absolute_path = bpy.path.abspath(str(raw_path))
                normalized_path = os.path.normcase(os.path.abspath(absolute_path))
                if normalized_path in seen_paths:
                    continue
                seen_paths.add(normalized_path)
                unique_paths.append(absolute_path)

            texture_maps = {}
            candidates = []
            for texture_path in sorted(unique_paths, key=lambda path: path.lower())[:max_files]:
                extension = os.path.splitext(texture_path)[1].lower()
                if extension not in supported_extensions:
                    ignored_textures.append({"path": texture_path, "reason": "unsupported_extension"})
                    continue
                if not os.path.isfile(texture_path):
                    ignored_textures.append({"path": texture_path, "reason": "missing_file"})
                    continue
                role = infer_role(texture_path)
                if not role:
                    ignored_textures.append({"path": texture_path, "reason": "unknown_role"})
                    continue
                candidates.append({"role": role, "path": texture_path})
                if role in texture_maps:
                    ambiguous_textures.append({
                        "role": role,
                        "kept": texture_maps[role],
                        "ignored": texture_path,
                    })
                    continue
                texture_maps[role] = texture_path

            truncated_count = max(0, len(unique_paths) - max_files)
            if truncated_count:
                warnings.append(f"Skipped {truncated_count} texture path(s) after max_files={max_files}")

            if not texture_maps:
                return {
                    "error": "No supported PBR texture maps were found",
                    "texture_directory": texture_directory,
                    "paths_checked": len(unique_paths),
                    "ignored_textures": ignored_textures,
                    "warnings": warnings,
                }

            material_report = self.create_material_preset(
                name=name,
                preset=preset,
                object_name=object_name,
                texture_maps=texture_maps,
                replace_existing=replace_existing,
                slot_index=slot_index,
            )
            if material_report.get("error"):
                return {
                    "error": material_report["error"],
                    "inferred_texture_maps": texture_maps,
                    "ignored_textures": ignored_textures,
                    "ambiguous_textures": ambiguous_textures,
                    "warnings": warnings,
                }

            return {
                "success": True,
                "material": material_report.get("material", name),
                "preset": material_report.get("preset", preset),
                "assigned_object": material_report.get("assigned_object"),
                "inferred_texture_maps": texture_maps,
                "inferred_roles": sorted(texture_maps.keys()),
                "candidate_count": len(candidates),
                "ignored_textures": ignored_textures,
                "ambiguous_textures": ambiguous_textures,
                "warnings": warnings + material_report.get("warnings", []),
                "material_report": material_report,
                "next_safe_action": "run inspect_material_node_graph on the material, then validate_export_readiness if exporting",
            }
        except Exception as e:
            return {"error": f"Failed to create PBR material from textures: {str(e)}"}

    def create_material_preset(
        self,
        name,
        preset="dielectric",
        object_name=None,
        base_color=None,
        metallic=None,
        roughness=None,
        alpha=None,
        emission_color=None,
        emission_strength=None,
        transmission_weight=None,
        ior=None,
        texture_maps=None,
        replace_existing=False,
        slot_index=None,
    ):
        """Create or update a deterministic Blender 5.x Principled BSDF material preset."""
        try:
            preset_key = str(preset or "dielectric").lower().replace("-", "_")
            presets = {
                "dielectric": {"color": (0.8, 0.78, 0.72, 1.0), "metallic": 0.0, "roughness": 0.55},
                "plastic": {"color": (0.65, 0.68, 0.72, 1.0), "metallic": 0.0, "roughness": 0.42},
                "rubber": {"color": (0.025, 0.025, 0.025, 1.0), "metallic": 0.0, "roughness": 0.88},
                "fabric": {"color": (0.55, 0.48, 0.42, 1.0), "metallic": 0.0, "roughness": 0.92, "sheen": 0.35},
                "ceramic": {"color": (0.86, 0.84, 0.8, 1.0), "metallic": 0.0, "roughness": 0.34, "coat": 0.25},
                "metal": {"color": (0.8, 0.72, 0.58, 1.0), "metallic": 1.0, "roughness": 0.28},
                "glass": {
                    "color": (0.92, 0.97, 1.0, 0.35),
                    "metallic": 0.0,
                    "roughness": 0.02,
                    "transmission": 1.0,
                    "ior": 1.45,
                    "alpha": 0.35,
                },
                "emissive": {
                    "color": (1.0, 0.72, 0.28, 1.0),
                    "metallic": 0.0,
                    "roughness": 0.28,
                    "emission_color": (1.0, 0.72, 0.28, 1.0),
                    "emission_strength": 3.0,
                },
            }
            if preset_key not in presets:
                return {"error": f"Unsupported material preset: {preset}. Supported presets: {', '.join(sorted(presets.keys()))}"}

            warnings = []
            defaults = presets[preset_key]
            existing = bpy.data.materials.get(name)
            if existing and replace_existing:
                bpy.data.materials.remove(existing)
                existing = None

            mat = existing or bpy.data.materials.new(name=name)
            mat.use_nodes = True

            resolved_color = self._as_rgba(base_color, defaults["color"])
            if alpha is not None:
                resolved_alpha = float(max(0.0, min(1.0, alpha)))
                resolved_color = (resolved_color[0], resolved_color[1], resolved_color[2], resolved_alpha)
            else:
                resolved_alpha = float(max(0.0, min(1.0, resolved_color[3])))

            uses_transparency = preset_key == "glass" or resolved_alpha < 1.0
            if hasattr(mat, "surface_render_method"):
                mat.surface_render_method = "BLENDED" if uses_transparency else "DITHERED"
            elif hasattr(mat, "blend_method"):
                mat.blend_method = "BLEND" if uses_transparency else "OPAQUE"
            if hasattr(mat, "use_raytrace_refraction"):
                mat.use_raytrace_refraction = preset_key == "glass"
            elif hasattr(mat, "use_screen_refraction"):
                mat.use_screen_refraction = preset_key == "glass"

            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            nodes.clear()

            output = nodes.new(type="ShaderNodeOutputMaterial")
            output.location = (420, 0)
            bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
            bsdf.location = (120, 0)
            links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

            socket_values = {
                "Base Color": resolved_color,
                "Metallic": float(defaults.get("metallic", 0.0) if metallic is None else metallic),
                "Roughness": float(defaults.get("roughness", 0.5) if roughness is None else roughness),
            }
            if "alpha" in defaults or alpha is not None or resolved_alpha < 1.0:
                socket_values["Alpha"] = resolved_alpha
            if "transmission" in defaults or transmission_weight is not None:
                socket_values["Transmission Weight"] = float(defaults.get("transmission", 0.0) if transmission_weight is None else transmission_weight)
            if "ior" in defaults or ior is not None:
                socket_values["IOR"] = float(defaults.get("ior", 1.45) if ior is None else ior)
            if "coat" in defaults:
                socket_values["Coat Weight"] = float(defaults["coat"])
            if "sheen" in defaults:
                socket_values["Sheen Weight"] = float(defaults["sheen"])

            resolved_emission = emission_color if emission_color is not None else defaults.get("emission_color")
            if resolved_emission is not None:
                socket_values["Emission Color"] = self._as_rgba(resolved_emission, defaults["color"], clamp=False)
                socket_values["Emission Strength"] = float(defaults.get("emission_strength", 1.0) if emission_strength is None else emission_strength)

            sockets_set = []
            for socket_name, value in socket_values.items():
                if self._set_socket_value(bsdf, socket_name, value, warnings):
                    sockets_set.append(socket_name)

            role_aliases = {
                "albedo": "base_color",
                "diffuse": "base_color",
                "color": "base_color",
                "basecolor": "base_color",
                "base_color": "base_color",
                "rough": "roughness",
                "roughness": "roughness",
                "metal": "metallic",
                "metalness": "metallic",
                "metallic": "metallic",
                "normal": "normal",
                "normal_map": "normal",
                "emission": "emission",
                "emissive": "emission",
                "displacement": "displacement",
                "height": "displacement",
            }
            role_targets = {
                "base_color": ("Color", bsdf.inputs.get("Base Color")),
                "roughness": ("Color", bsdf.inputs.get("Roughness")),
                "metallic": ("Color", bsdf.inputs.get("Metallic")),
                "emission": ("Color", bsdf.inputs.get("Emission Color")),
            }
            texture_nodes = []
            maps = texture_maps if isinstance(texture_maps, dict) else {}
            y_offset = 260
            for raw_role, texture_path in maps.items():
                role = role_aliases.get(str(raw_role).lower().replace(" ", "_"), str(raw_role).lower())
                image = self._load_material_image(texture_path, role, warnings)
                if image is None:
                    continue
                tex = nodes.new(type="ShaderNodeTexImage")
                tex.label = f"{role} map"
                tex.location = (-520, y_offset)
                tex.image = image
                y_offset -= 220
                texture_nodes.append({"role": role, "image": image.name, "color_space": image.colorspace_settings.name})

                if role == "normal":
                    normal_node = nodes.new(type="ShaderNodeNormalMap")
                    normal_node.location = (-160, tex.location.y)
                    links.new(tex.outputs["Color"], normal_node.inputs["Color"])
                    if bsdf.inputs.get("Normal"):
                        links.new(normal_node.outputs["Normal"], bsdf.inputs["Normal"])
                    continue
                if role == "displacement":
                    displacement = nodes.new(type="ShaderNodeDisplacement")
                    displacement.location = (-160, tex.location.y)
                    links.new(tex.outputs["Color"], displacement.inputs["Height"])
                    if output.inputs.get("Displacement"):
                        links.new(displacement.outputs["Displacement"], output.inputs["Displacement"])
                    continue

                target = role_targets.get(role)
                if target and target[1] is not None:
                    links.new(tex.outputs[target[0]], target[1])
                else:
                    warnings.append(f"Texture role loaded but not connected: {raw_role}")

            assigned_slot = None
            if object_name:
                assignment = self.assign_material(object_name, mat.name, slot_index)
                if assignment.get("error"):
                    warnings.append(assignment["error"])
                else:
                    assigned_slot = assignment.get("slot")

            return {
                "success": True,
                "material": mat.name,
                "preset": preset_key,
                "reused_existing": existing is not None,
                "assigned_object": object_name,
                "assigned_slot": assigned_slot,
                "sockets_set": sockets_set,
                "texture_nodes": texture_nodes,
                "node_count": len(nodes),
                "link_count": len(links),
                "warnings": warnings,
            }
        except Exception as e:
            return {"error": f"Failed to create material preset: {str(e)}"}

    def inspect_material_node_graph(self, material_name):
        """Return a compact material node graph summary for verification."""
        try:
            mat = bpy.data.materials.get(material_name)
            if not mat:
                return {"error": f"Material not found: {material_name}"}

            nodes = []
            links = []
            image_nodes = []
            principled = None
            if mat.node_tree:
                for node in mat.node_tree.nodes:
                    nodes.append({
                        "name": node.name,
                        "type": node.bl_idname,
                        "label": node.label,
                    })
                    if node.bl_idname == "ShaderNodeBsdfPrincipled":
                        principled = node
                    if node.bl_idname == "ShaderNodeTexImage" and node.image:
                        image_nodes.append({
                            "name": node.name,
                            "label": node.label,
                            "image": node.image.name,
                            "color_space": node.image.colorspace_settings.name,
                            "filepath": bpy.path.abspath(node.image.filepath) if node.image.filepath else "",
                        })
                for link in mat.node_tree.links:
                    links.append({
                        "from_node": link.from_node.name,
                        "from_socket": link.from_socket.name,
                        "to_node": link.to_node.name,
                        "to_socket": link.to_socket.name,
                    })

            principled_inputs = {}
            if principled:
                for socket_name in [
                    "Base Color",
                    "Metallic",
                    "Roughness",
                    "Alpha",
                    "Transmission Weight",
                    "IOR",
                    "Emission Color",
                    "Emission Strength",
                    "Coat Weight",
                    "Sheen Weight",
                ]:
                    socket = principled.inputs.get(socket_name)
                    if socket:
                        value = socket.default_value
                        if hasattr(value, "__len__"):
                            value = list(value)
                        principled_inputs[socket_name] = value

            assigned_objects = []
            for obj in bpy.data.objects:
                if hasattr(obj, "material_slots"):
                    for index, slot in enumerate(obj.material_slots):
                        if slot.material == mat:
                            assigned_objects.append({"object": obj.name, "slot": index})

            return {
                "success": True,
                "material": mat.name,
                "surface_render_method": getattr(mat, "surface_render_method", None),
                "blend_method": getattr(mat, "blend_method", None),
                "node_count": len(nodes),
                "link_count": len(links),
                "nodes": nodes,
                "links": links,
                "image_nodes": image_nodes,
                "principled_inputs": principled_inputs,
                "assigned_objects": assigned_objects,
            }
        except Exception as e:
            return {"error": f"Failed to inspect material node graph: {str(e)}"}

    def normalize_material_texture_channels(self, material_names=None, apply_changes=False):
        """Inspect and optionally fix image texture color spaces for common PBR material channels."""
        try:
            expected_color_spaces = {
                "base_color": "sRGB",
                "emission": "sRGB",
                "roughness": "Non-Color",
                "metallic": "Non-Color",
                "normal": "Non-Color",
                "displacement": "Non-Color",
                "alpha": "Non-Color",
                "ambient_occlusion": "Non-Color",
            }
            role_aliases = {
                "albedo": "base_color",
                "diffuse": "base_color",
                "basecolor": "base_color",
                "base_color": "base_color",
                "color": "base_color",
                "emissive": "emission",
                "emission": "emission",
                "rough": "roughness",
                "roughness": "roughness",
                "metal": "metallic",
                "metalness": "metallic",
                "metallic": "metallic",
                "normal": "normal",
                "normalmap": "normal",
                "normal_map": "normal",
                "height": "displacement",
                "displacement": "displacement",
                "alpha": "alpha",
                "opacity": "alpha",
                "ao": "ambient_occlusion",
                "occlusion": "ambient_occlusion",
                "ambientocclusion": "ambient_occlusion",
                "ambient_occlusion": "ambient_occlusion",
            }
            socket_roles = {
                "base color": "base_color",
                "emission color": "emission",
                "roughness": "roughness",
                "metallic": "metallic",
                "normal": "normal",
                "displacement": "displacement",
                "alpha": "alpha",
            }

            def coerce_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, str):
                    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(value)

            def normalize_token(value):
                token = str(value or "").strip().lower()
                for separator in (" ", "-", ".", "__"):
                    token = token.replace(separator, "_")
                return token

            def infer_from_text(*values):
                joined = "_".join(normalize_token(value) for value in values if value)
                tokens = [token for token in joined.split("_") if token]
                role_priority = [
                    ("normal", ["normal", "normalmap", "normal_map"]),
                    ("displacement", ["displacement", "height"]),
                    ("roughness", ["roughness", "rough"]),
                    ("metallic", ["metallic", "metalness", "metal"]),
                    ("ambient_occlusion", ["ambient_occlusion", "ambientocclusion", "occlusion", "ao"]),
                    ("alpha", ["alpha", "opacity"]),
                    ("emission", ["emission", "emissive"]),
                    ("base_color", ["base_color", "basecolor", "albedo", "diffuse", "color"]),
                ]
                for role, aliases in role_priority:
                    for alias in aliases:
                        alias_tokens = [token for token in normalize_token(alias).split("_") if token]
                        if not alias_tokens:
                            continue
                        if len(alias_tokens) == 1:
                            if alias_tokens[0] in tokens:
                                return role
                            continue
                        for index in range(0, len(tokens) - len(alias_tokens) + 1):
                            if tokens[index:index + len(alias_tokens)] == alias_tokens:
                                return role
                return None

            def infer_texture_role(node):
                pending_links = []
                for output in getattr(node, "outputs", []) or []:
                    pending_links.extend(list(getattr(output, "links", []) or []))

                visited_nodes = set()
                while pending_links:
                    link = pending_links.pop(0)
                    to_node = getattr(link, "to_node", None)
                    to_socket = getattr(link, "to_socket", None)
                    if to_node is None:
                        continue
                    node_id = id(to_node)
                    if node_id in visited_nodes:
                        continue
                    visited_nodes.add(node_id)

                    to_socket_name = str(getattr(to_socket, "name", "")).strip().lower()
                    to_node_type = str(getattr(to_node, "bl_idname", ""))
                    if to_node_type == "ShaderNodeNormalMap":
                        return "normal", "normal_map_node"
                    if to_node_type == "ShaderNodeDisplacement":
                        return "displacement", "displacement_node"
                    if to_socket_name in socket_roles:
                        return socket_roles[to_socket_name], "linked_socket"

                    for output in getattr(to_node, "outputs", []) or []:
                        pending_links.extend(list(getattr(output, "links", []) or []))

                role = infer_from_text(getattr(node, "label", ""), getattr(node, "name", ""))
                if role:
                    return role, "node_label_or_name"

                image = getattr(node, "image", None)
                if image:
                    role = infer_from_text(getattr(image, "name", ""), getattr(image, "filepath", ""))
                    if role:
                        return role, "image_name_or_path"
                return None, "unknown"

            apply_changes = coerce_bool(apply_changes, False)
            if isinstance(material_names, str):
                requested_names = [material_names]
            elif isinstance(material_names, (list, tuple)):
                requested_names = [str(name) for name in material_names]
            else:
                requested_names = []

            missing_materials = []
            if requested_names:
                materials = []
                for name in requested_names:
                    material = bpy.data.materials.get(name)
                    if material is None:
                        missing_materials.append(name)
                    else:
                        materials.append(material)
            else:
                materials = [material for material in bpy.data.materials if getattr(material, "use_nodes", False)]

            reports = []
            changes = []
            warnings = []
            for material in materials:
                material_report = {
                    "material": material.name,
                    "image_textures": [],
                }
                node_tree = getattr(material, "node_tree", None)
                if not node_tree:
                    reports.append(material_report)
                    continue

                for node in node_tree.nodes:
                    if getattr(node, "bl_idname", "") != "ShaderNodeTexImage":
                        continue
                    image = getattr(node, "image", None)
                    if image is None:
                        material_report["image_textures"].append({
                            "node": node.name,
                            "role": None,
                            "issue": "missing_image",
                        })
                        continue

                    role, role_source = infer_texture_role(node)
                    current_color_space = image.colorspace_settings.name
                    expected_color_space = expected_color_spaces.get(role)
                    needs_change = bool(expected_color_space and current_color_space != expected_color_space)
                    entry = {
                        "node": node.name,
                        "label": node.label,
                        "image": image.name,
                        "filepath": bpy.path.abspath(image.filepath) if image.filepath else "",
                        "role": role,
                        "role_source": role_source,
                        "current_color_space": current_color_space,
                        "expected_color_space": expected_color_space,
                        "needs_change": needs_change,
                    }

                    if role is None:
                        warnings.append(f"{material.name}/{node.name}: could not infer texture role")
                    elif needs_change:
                        change = {
                            "material": material.name,
                            "node": node.name,
                            "image": image.name,
                            "role": role,
                            "from": current_color_space,
                            "to": expected_color_space,
                            "applied": False,
                        }
                        if apply_changes:
                            try:
                                image.colorspace_settings.name = expected_color_space
                                change["applied"] = True
                                entry["current_color_space"] = image.colorspace_settings.name
                                entry["needs_change"] = image.colorspace_settings.name != expected_color_space
                            except Exception as exc:
                                change["error"] = str(exc)
                                warnings.append(f"{material.name}/{node.name}: failed to set color space to {expected_color_space}: {str(exc)}")
                        changes.append(change)

                    material_report["image_textures"].append(entry)

                reports.append(material_report)

            return {
                "success": not missing_materials,
                "apply_changes": apply_changes,
                "materials_checked": len(reports),
                "missing_materials": missing_materials,
                "changes": changes,
                "warnings": warnings,
                "reports": reports,
                "next_safe_action": "run inspect_material_node_graph on changed materials, then validate_export_readiness if exporting",
            }
        except Exception as e:
            return {"error": f"Failed to normalize material texture channels: {str(e)}"}

    def _studio_target_objects(self, target_names=None):
        if target_names:
            raw_names = target_names if isinstance(target_names, list) else [target_names]
            objects = [bpy.data.objects.get(str(name)) for name in raw_names]
            missing = [str(name) for name, obj in zip(raw_names, objects) if obj is None]
            mesh_objects = [obj for obj in objects if obj and obj.type == "MESH"]
        else:
            missing = []
            mesh_objects = [
                obj for obj in bpy.context.scene.objects
                if obj.type == "MESH" and obj.visible_get() and not obj.hide_render
            ]
        return mesh_objects, missing

    def _studio_bounds(self, target_names=None):
        objects, missing = self._studio_target_objects(target_names)
        if not objects:
            return None, missing

        points = []
        for obj in objects:
            matrix = obj.matrix_world
            points.extend([matrix @ mathutils.Vector(corner) for corner in obj.bound_box])

        min_corner = mathutils.Vector((
            min(point.x for point in points),
            min(point.y for point in points),
            min(point.z for point in points),
        ))
        max_corner = mathutils.Vector((
            max(point.x for point in points),
            max(point.y for point in points),
            max(point.z for point in points),
        ))
        center = (min_corner + max_corner) * 0.5
        size = max_corner - min_corner
        radius = max(size.length * 0.5, 0.5)
        return {
            "objects": [obj.name for obj in objects],
            "center": center,
            "min": min_corner,
            "max": max_corner,
            "size": size,
            "radius": radius,
        }, missing

    def _studio_box_corners(self, bounds):
        min_corner = bounds["min"]
        max_corner = bounds["max"]
        return [
            mathutils.Vector((x, y, z))
            for x in (min_corner.x, max_corner.x)
            for y in (min_corner.y, max_corner.y)
            for z in (min_corner.z, max_corner.z)
        ]

    def _look_at(self, obj, target):
        direction = mathutils.Vector(target) - obj.location
        if direction.length > 0:
            obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    def _upsert_area_light(self, name, location, target, energy, size, color):
        obj = bpy.data.objects.get(name)
        if obj and obj.type != "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)
            obj = None
        if not obj:
            light_data = bpy.data.lights.new(name=name, type="AREA")
            obj = bpy.data.objects.new(name=name, object_data=light_data)
            bpy.context.collection.objects.link(obj)
        elif obj.data.type != "AREA":
            obj.data.type = "AREA"

        obj.location = location
        self._look_at(obj, target)
        obj.data.energy = float(energy)
        obj.data.size = float(size)
        obj.data.color = tuple(float(c) for c in color[:3])
        return obj

    def set_world_environment(
        self,
        mode="solid",
        color=None,
        strength=1.0,
        hdri_path=None,
        rotation_z=0.0,
        sky_type="NISHITA",
        sun_elevation=45.0,
        sun_rotation=0.0,
    ):
        """Configure world background/environment lighting without arbitrary Python."""
        try:
            mode_key = str(mode or "solid").lower().replace("-", "_")
            allowed_modes = {"solid", "hdri", "sky"}
            if mode_key not in allowed_modes:
                return {"error": f"Unsupported world environment mode: {mode}. Use one of: {', '.join(sorted(allowed_modes))}"}

            def clamp(value, minimum, maximum):
                return max(minimum, min(maximum, float(value)))

            def rgb(value, fallback):
                raw = list(value if value is not None else fallback)
                if len(raw) < 3:
                    raise ValueError("color must contain at least three RGB values")
                return tuple(clamp(raw[index], 0.0, 1.0) for index in range(3))

            resolved_strength = clamp(strength, 0.0, 20.0)
            resolved_color = None
            resolved_path = None
            if mode_key == "solid":
                resolved_color = rgb(color, (0.025, 0.03, 0.04))
            elif mode_key == "hdri":
                if not hdri_path:
                    return {"error": "hdri_path is required when mode is 'hdri'"}
                resolved_path = bpy.path.abspath(str(hdri_path))
                if not os.path.exists(resolved_path):
                    return {"error": f"HDRI file does not exist: {resolved_path}"}

            world = bpy.context.scene.world
            if world is None:
                world = bpy.data.worlds.new("ViperMesh_World")
                bpy.context.scene.world = world
            world.use_nodes = True

            nodes = world.node_tree.nodes
            links = world.node_tree.links
            nodes.clear()

            background = nodes.new(type="ShaderNodeBackground")
            background.location = (120, 0)
            background.inputs["Strength"].default_value = resolved_strength

            output = nodes.new(type="ShaderNodeOutputWorld")
            output.location = (340, 0)

            result = {
                "success": True,
                "mode": mode_key,
                "world": world.name,
                "strength": float(background.inputs["Strength"].default_value),
                "nodes": [],
            }

            if mode_key == "solid":
                world.color = resolved_color
                background.inputs["Color"].default_value = (*resolved_color, 1.0)
                result["color"] = list(resolved_color)
            elif mode_key == "hdri":
                tex_coord = nodes.new(type="ShaderNodeTexCoord")
                tex_coord.location = (-620, 0)
                mapping = nodes.new(type="ShaderNodeMapping")
                mapping.location = (-400, 0)
                mapping.inputs["Rotation"].default_value[2] = math.radians(float(rotation_z))
                env_tex = nodes.new(type="ShaderNodeTexEnvironment")
                env_tex.location = (-160, 0)
                env_tex.image = bpy.data.images.load(resolved_path, check_existing=True)

                links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
                links.new(mapping.outputs["Vector"], env_tex.inputs["Vector"])
                links.new(env_tex.outputs["Color"], background.inputs["Color"])
                result.update({
                    "hdri_path": resolved_path,
                    "image": env_tex.image.name if env_tex.image else None,
                    "rotation_z": float(rotation_z),
                })
            else:
                sky = nodes.new(type="ShaderNodeTexSky")
                sky.location = (-160, 0)
                if hasattr(sky, "sky_type"):
                    requested_sky_type = str(sky_type or "NISHITA").upper()
                    try:
                        sky.sky_type = requested_sky_type
                    except Exception:
                        sky.sky_type = "NISHITA"
                if hasattr(sky, "sun_elevation"):
                    sky.sun_elevation = math.radians(float(sun_elevation))
                if hasattr(sky, "sun_rotation"):
                    sky.sun_rotation = math.radians(float(sun_rotation))
                links.new(sky.outputs["Color"], background.inputs["Color"])
                result.update({
                    "sky_type": getattr(sky, "sky_type", None),
                    "sun_elevation": float(sun_elevation),
                    "sun_rotation": float(sun_rotation),
                })

            links.new(background.outputs["Background"], output.inputs["Surface"])
            result["nodes"] = [node.name for node in nodes]
            result["next_safe_action"] = "run validate_studio_scene or render_viewport_to_path to verify the environment lighting visually"
            return result
        except Exception as e:
            return {"error": f"Failed to set world environment: {str(e)}"}

    def setup_studio_scene(
        self,
        target_names=None,
        preset="studio",
        camera_name="ViperMesh_Studio_Camera",
        frame_camera=True,
        focal_length=70,
        distance_multiplier=2.8,
        resolution_x=1600,
        resolution_y=1600,
        samples=64,
        background_color=None,
        world_strength=0.08,
        set_active_camera=True,
    ):
        """Create a deterministic studio lighting/camera/render setup around target meshes."""
        try:
            bounds, missing = self._studio_bounds(target_names)
            if not bounds:
                return {"error": "No mesh targets found for studio setup", "missing": missing}

            preset_key = str(preset or "studio").lower().replace("-", "_")
            presets = {
                "studio": {"key": 550, "fill": 120, "rim": 180, "world": 0.08, "color": (0.025, 0.03, 0.04)},
                "product": {"key": 720, "fill": 180, "rim": 220, "world": 0.1, "color": (0.02, 0.024, 0.03)},
                "indoor": {"key": 360, "fill": 140, "rim": 80, "world": 0.16, "color": (0.045, 0.043, 0.04)},
                "exterior": {"key": 900, "fill": 230, "rim": 160, "world": 0.22, "color": (0.055, 0.065, 0.075)},
                "night": {"key": 180, "fill": 45, "rim": 260, "world": 0.035, "color": (0.005, 0.008, 0.018)},
            }
            if preset_key not in presets:
                return {"error": f"Unsupported studio preset: {preset}. Supported presets: {', '.join(sorted(presets.keys()))}"}

            config = presets[preset_key]
            center = bounds["center"]
            radius = bounds["radius"]
            target = mathutils.Vector((center.x, center.y, center.z + bounds["size"].z * 0.08))

            key = self._upsert_area_light(
                "ViperMesh_Studio_Key",
                center + mathutils.Vector((-radius * 1.5, -radius * 2.2, radius * 1.9)),
                target,
                config["key"],
                radius * 1.8,
                (1.0, 0.96, 0.9),
            )
            fill = self._upsert_area_light(
                "ViperMesh_Studio_Fill",
                center + mathutils.Vector((radius * 2.2, -radius * 1.5, radius * 1.2)),
                target,
                config["fill"],
                radius * 2.4,
                (0.72, 0.82, 1.0),
            )
            rim = self._upsert_area_light(
                "ViperMesh_Studio_Rim",
                center + mathutils.Vector((radius * 1.0, radius * 2.0, radius * 1.8)),
                target,
                config["rim"],
                radius * 1.5,
                (0.86, 0.92, 1.0),
            )

            camera = bpy.data.objects.get(camera_name)
            if camera and camera.type != "CAMERA":
                bpy.data.objects.remove(camera, do_unlink=True)
                camera = None
            if not camera:
                camera_data = bpy.data.cameras.new(name=camera_name)
                camera = bpy.data.objects.new(name=camera_name, object_data=camera_data)
                bpy.context.collection.objects.link(camera)

            if frame_camera:
                distance = max(radius * float(distance_multiplier), 1.5)
                camera.location = center + mathutils.Vector((radius * 0.35, -distance, radius * 0.55))
                self._look_at(camera, target)
            camera.data.lens = float(focal_length)
            camera.data.clip_start = 0.01
            camera.data.clip_end = max(1000.0, radius * 20.0)
            camera.data.dof.use_dof = True
            camera.data.dof.focus_distance = max((camera.location - target).length, 0.1)
            camera.data.dof.aperture_fstop = 8.0
            if set_active_camera:
                bpy.context.scene.camera = camera

            scene = bpy.context.scene
            scene.render.resolution_x = int(resolution_x)
            scene.render.resolution_y = int(resolution_y)
            scene.render.resolution_percentage = 100
            try:
                scene.render.engine = "BLENDER_EEVEE_NEXT"
            except TypeError:
                scene.render.engine = "BLENDER_EEVEE"
            if scene.render.engine == "CYCLES" and hasattr(scene, "cycles"):
                scene.cycles.samples = int(samples)
            elif hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
                scene.eevee.taa_render_samples = int(samples)

            world = scene.world or bpy.data.worlds.new("ViperMesh_World")
            scene.world = world
            world.color = tuple(float(c) for c in (background_color or config["color"])[:3])
            if world.use_nodes and world.node_tree:
                bg = world.node_tree.nodes.get("Background")
                if bg:
                    bg.inputs["Strength"].default_value = float(world_strength if world_strength is not None else config["world"])
                    bg.inputs["Color"].default_value = (*world.color, 1.0)

            return {
                "success": True,
                "preset": preset_key,
                "target_objects": bounds["objects"],
                "missing_targets": missing,
                "camera": {
                    "name": camera.name,
                    "location": list(camera.location),
                    "lens": camera.data.lens,
                    "focus_distance": camera.data.dof.focus_distance,
                    "active": bpy.context.scene.camera == camera,
                },
                "lights": [
                    {"name": key.name, "energy": key.data.energy, "size": key.data.size},
                    {"name": fill.name, "energy": fill.data.energy, "size": fill.data.size},
                    {"name": rim.name, "energy": rim.data.energy, "size": rim.data.size},
                ],
                "render": {
                    "engine": scene.render.engine,
                    "resolution": [scene.render.resolution_x, scene.render.resolution_y],
                    "samples": int(samples),
                },
                "bounds": {
                    "center": list(center),
                    "size": list(bounds["size"]),
                    "radius": radius,
                },
            }
        except Exception as e:
            return {"error": f"Failed to set up studio scene: {str(e)}"}

    def validate_studio_scene(
        self,
        target_names=None,
        camera_name=None,
        require_camera=True,
        require_lights=True,
        require_render_settings=True,
        min_frame_fill=0.18,
        max_frame_fill=0.92,
        frame_margin=0.06,
    ):
        """Validate that the scene has usable target meshes, lighting, camera framing, and render settings."""
        try:
            bounds, missing = self._studio_bounds(target_names)
            errors = []
            warnings = []
            if missing:
                errors.append(f"Missing target object(s): {', '.join(missing)}")
            if not bounds:
                errors.append("No visible mesh targets found")

            scene = bpy.context.scene
            camera = bpy.data.objects.get(camera_name) if camera_name else scene.camera
            camera_report = None
            if require_camera and not camera:
                errors.append("No active camera or requested camera found")
            elif camera:
                camera_report = {
                    "name": camera.name,
                    "active": scene.camera == camera,
                    "location": list(camera.location),
                    "lens": camera.data.lens if camera.type == "CAMERA" else None,
                }
                if camera.type != "CAMERA":
                    errors.append(f"{camera.name} is not a camera")
                elif bounds:
                    bpy.context.view_layer.update()
                    distance = (camera.location - bounds["center"]).length
                    if distance < bounds["radius"] * 0.8:
                        warnings.append("Camera may be too close to target bounds")
                    try:
                        from bpy_extras.object_utils import world_to_camera_view
                        projected = [
                            world_to_camera_view(scene, camera, corner)
                            for corner in self._studio_box_corners(bounds)
                        ]
                        if any(point.z < 0 for point in projected):
                            errors.append("Target bounds are behind the camera")
                        min_x = min(point.x for point in projected)
                        max_x = max(point.x for point in projected)
                        min_y = min(point.y for point in projected)
                        max_y = max(point.y for point in projected)
                        frame_width = max_x - min_x
                        frame_height = max_y - min_y
                        frame_fill = max(frame_width, frame_height)
                        frame_bounds = {
                            "min_x": round(min_x, 6),
                            "max_x": round(max_x, 6),
                            "min_y": round(min_y, 6),
                            "max_y": round(max_y, 6),
                            "width": round(frame_width, 6),
                            "height": round(frame_height, 6),
                            "fill": round(frame_fill, 6),
                            "margin": round(float(frame_margin), 6),
                        }
                        camera_report["frame_bounds"] = frame_bounds
                        if min_x < float(frame_margin) or max_x > 1.0 - float(frame_margin) or min_y < float(frame_margin) or max_y > 1.0 - float(frame_margin):
                            warnings.append("Target bounds may be partially outside the camera frame")
                        if frame_fill < float(min_frame_fill):
                            warnings.append("Target occupies too little of the camera frame")
                        if frame_fill > float(max_frame_fill):
                            warnings.append("Target occupies too much of the camera frame")
                    except Exception as exc:
                        warnings.append(f"Could not project target into camera view: {str(exc)}")

            lights = [obj for obj in scene.objects if obj.type == "LIGHT" and not obj.hide_render]
            usable_lights = [obj for obj in lights if getattr(obj.data, "energy", 0) > 0]
            if require_lights and not usable_lights:
                errors.append("No render-visible lights with positive energy found")

            render_report = {
                "engine": scene.render.engine,
                "resolution": [scene.render.resolution_x, scene.render.resolution_y],
                "resolution_percentage": scene.render.resolution_percentage,
                "filepath": bpy.path.abspath(scene.render.filepath),
                "file_format": scene.render.image_settings.file_format,
            }
            if require_render_settings:
                if scene.render.resolution_x < 512 or scene.render.resolution_y < 512:
                    warnings.append("Render resolution is below 512px on at least one axis")
                if scene.render.resolution_percentage < 50:
                    warnings.append("Render resolution percentage is below 50")

            return {
                "success": True,
                "ready": len(errors) == 0,
                "target_objects": bounds["objects"] if bounds else [],
                "missing_targets": missing,
                "camera": camera_report,
                "lights": [
                    {"name": obj.name, "type": obj.data.type, "energy": obj.data.energy}
                    for obj in usable_lights
                ],
                "render": render_report,
                "errors": errors,
                "warnings": warnings,
                "next_safe_action": "render_image" if len(errors) == 0 else "setup_studio_scene or fix reported errors before render_image",
            }
        except Exception as e:
            return {"error": f"Failed to validate studio scene: {str(e)}"}

    def frame_camera_to_targets(
        self,
        target_names=None,
        camera_name=None,
        desired_frame_fill=0.62,
        frame_margin=0.08,
        min_distance_multiplier=1.05,
        max_distance_multiplier=12.0,
        set_active=True,
        set_dof_focus=True,
    ):
        """Move a camera along its target-view ray until target bounds occupy a useful frame share."""
        try:
            bounds, missing = self._studio_bounds(target_names)
            if not bounds:
                return {"error": "No mesh targets found for camera framing", "missing": missing}

            def coerce_bool(value, default=True):
                if value is None:
                    return default
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() in {"1", "true", "yes", "on"}
                return bool(value)

            def coerce_float(value, default, minimum=None, maximum=None):
                if value is None:
                    result = float(default)
                else:
                    result = float(value)
                if minimum is not None:
                    result = max(float(minimum), result)
                if maximum is not None:
                    result = min(float(maximum), result)
                return result

            scene = bpy.context.scene
            target = bounds["center"]
            radius = max(bounds["radius"], 0.5)
            desired_fill = coerce_float(desired_frame_fill, 0.62, 0.05, 0.95)
            frame_margin_value = coerce_float(frame_margin, 0.08, -1.0, 0.5)
            min_distance = radius * coerce_float(min_distance_multiplier, 1.05, 0.1)
            max_distance = radius * coerce_float(max_distance_multiplier, 12.0, 0.5)
            if max_distance < min_distance:
                max_distance = min_distance
            camera = bpy.data.objects.get(camera_name) if camera_name else scene.camera
            if camera and camera.type != "CAMERA":
                return {"error": f"{camera.name} is not a camera"}
            if not camera:
                camera_data = bpy.data.cameras.new(name=str(camera_name or "ViperMesh_Studio_Camera"))
                camera = bpy.data.objects.new(name=camera_data.name, object_data=camera_data)
                bpy.context.collection.objects.link(camera)
                camera.location = target + mathutils.Vector((radius * 0.35, -radius * 2.8, radius * 0.55))
                camera.data.lens = 70

            def projected_frame_bounds():
                from bpy_extras.object_utils import world_to_camera_view
                projected = [
                    world_to_camera_view(scene, camera, corner)
                    for corner in self._studio_box_corners(bounds)
                ]
                if any(point.z < 0 for point in projected):
                    return {"behind_camera": True}
                min_x = min(point.x for point in projected)
                max_x = max(point.x for point in projected)
                min_y = min(point.y for point in projected)
                max_y = max(point.y for point in projected)
                frame_width = max_x - min_x
                frame_height = max_y - min_y
                frame_fill = max(frame_width, frame_height)
                return {
                    "behind_camera": False,
                    "min_x": round(min_x, 6),
                    "max_x": round(max_x, 6),
                    "min_y": round(min_y, 6),
                    "max_y": round(max_y, 6),
                    "width": round(frame_width, 6),
                    "height": round(frame_height, 6),
                    "fill": round(frame_fill, 6),
                    "inside_margin": min_x >= frame_margin_value and max_x <= 1.0 - frame_margin_value and min_y >= frame_margin_value and max_y <= 1.0 - frame_margin_value,
                }

            self._look_at(camera, target)
            before_frame = projected_frame_bounds()
            if before_frame.get("behind_camera"):
                camera.location = target + mathutils.Vector((radius * 0.35, -radius * 2.8, radius * 0.55))
                self._look_at(camera, target)
                before_frame = projected_frame_bounds()

            current_fill = max(float(before_frame.get("fill", 0.0)), 0.001)
            current_distance = max((camera.location - target).length, min_distance)
            next_distance = current_distance * (current_fill / desired_fill)
            next_distance = max(min_distance, min(next_distance, max_distance))
            direction = camera.location - target
            if direction.length <= 0.001:
                direction = mathutils.Vector((0.35, -2.8, 0.55))
            direction.normalize()
            camera.location = target + direction * next_distance
            self._look_at(camera, target)

            if coerce_bool(set_active, True):
                scene.camera = camera
            if coerce_bool(set_dof_focus, True):
                camera.data.dof.use_dof = True
                camera.data.dof.focus_distance = max((camera.location - target).length, 0.1)

            after_frame = projected_frame_bounds()
            return {
                "success": True,
                "camera": camera.name,
                "target_objects": bounds["objects"],
                "missing_targets": missing,
                "desired_frame_fill": desired_fill,
                "frame_margin": frame_margin_value,
                "before_frame": before_frame,
                "after_frame": after_frame,
                "location": [round(value, 6) for value in camera.location],
                "distance": round((camera.location - target).length, 6),
                "active": scene.camera == camera,
                "dof_focus_distance": camera.data.dof.focus_distance,
                "next_safe_action": "validate_studio_scene to verify final framing before render_image",
            }
        except Exception as e:
            return {"error": f"Failed to frame camera to targets: {str(e)}"}

    def create_camera_orbit_animation(
        self,
        target_names=None,
        camera_name="ViperMesh_Orbit_Camera",
        start_frame=1,
        end_frame=120,
        radius_multiplier=2.8,
        height_multiplier=0.55,
        start_angle_degrees=-35,
        end_angle_degrees=325,
        focal_length=70,
        interpolation="LINEAR",
        clear_existing=True,
        set_active=True,
        set_scene_range=True,
    ):
        """Create a deterministic camera orbit animation around target bounds without arbitrary Python."""
        try:
            import math

            bounds, missing = self._studio_bounds(target_names)
            if not bounds:
                return {"error": "No mesh targets found for camera orbit", "missing": missing}

            start_frame = int(round(float(start_frame)))
            end_frame = int(round(float(end_frame)))
            if start_frame < 0 or end_frame < 0:
                return {"error": "start_frame and end_frame must be >= 0"}
            if end_frame <= start_frame:
                return {"error": "end_frame must be greater than start_frame"}

            def coerce_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, str):
                    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
                return bool(value)

            interpolation = str(interpolation or "LINEAR").upper()
            allowed_interpolation = {"CONSTANT", "LINEAR", "BEZIER", "SINE", "QUAD", "CUBIC", "QUART", "QUINT", "EXPO", "CIRC", "BACK", "BOUNCE", "ELASTIC"}
            if interpolation not in allowed_interpolation:
                return {"error": f"Unsupported interpolation '{interpolation}'"}

            clear_existing = coerce_bool(clear_existing, True)
            set_active = coerce_bool(set_active, True)
            set_scene_range = coerce_bool(set_scene_range, True)

            scene = bpy.context.scene
            current_frame = int(scene.frame_current)
            center = bounds["center"]
            radius = max(float(bounds["radius"]), 0.1)
            target = mathutils.Vector((center.x, center.y, center.z + bounds["size"].z * 0.08))
            orbit_radius = max(radius * float(radius_multiplier), 0.35)
            orbit_height = radius * float(height_multiplier)

            camera_name = str(camera_name or "ViperMesh_Orbit_Camera")
            camera = bpy.data.objects.get(camera_name)
            if camera and camera.type != "CAMERA":
                return {"error": f"{camera.name} is not a camera"}
            if not camera:
                camera_data = bpy.data.cameras.new(name=camera_name)
                camera = bpy.data.objects.new(name=camera_data.name, object_data=camera_data)
                bpy.context.collection.objects.link(camera)

            camera.data.lens = float(focal_length)
            camera.data.clip_start = 0.01
            camera.data.clip_end = max(1000.0, radius * 25.0)
            camera.data.dof.use_dof = True

            def orbit_location(angle_degrees):
                angle = math.radians(float(angle_degrees))
                return center + mathutils.Vector((
                    math.cos(angle) * orbit_radius,
                    math.sin(angle) * orbit_radius,
                    orbit_height,
                ))

            def resolve_action_slot(action, handle):
                if action is None or handle is None:
                    return None
                try:
                    slots = list(getattr(action, "slots", []) or [])
                except Exception:
                    return None
                for candidate in slots:
                    if getattr(candidate, "handle", None) == handle:
                        return candidate
                if isinstance(handle, int) and 0 <= handle < len(slots):
                    return slots[handle]
                return None

            def get_action_slot(animation_data, action=None):
                if not animation_data:
                    return None
                slot = getattr(animation_data, "action_slot", None)
                if slot is not None and not isinstance(slot, int):
                    return slot
                handle = getattr(animation_data, "action_slot_handle", None)
                if handle is None and isinstance(slot, int):
                    handle = slot
                return resolve_action_slot(action or getattr(animation_data, "action", None), handle)

            def collect_action_fcurves(action, action_slot=None):
                if action is None:
                    return [], None
                try:
                    from bpy_extras import anim_utils

                    if action_slot is not None and hasattr(anim_utils, "action_get_channelbag_for_slot"):
                        channelbag = anim_utils.action_get_channelbag_for_slot(action, action_slot)
                        if channelbag is not None and hasattr(channelbag, "fcurves"):
                            return list(channelbag.fcurves), channelbag
                except Exception:
                    pass

                try:
                    legacy_fcurves = getattr(action, "fcurves", None)
                    if legacy_fcurves is not None:
                        return list(legacy_fcurves), action
                except Exception:
                    pass
                return [], None

            def clear_camera_fcurves():
                action = camera.animation_data.action if camera.animation_data else None
                if action is None:
                    return 0
                if int(getattr(action, "users", 0) or 0) > 1:
                    action = action.copy()
                    action.name = f"{camera.name}_Orbit"
                    camera.animation_data.action = action
                action_slot = get_action_slot(camera.animation_data, action)
                fcurves, fcurve_owner = collect_action_fcurves(action, action_slot)
                removed = 0
                try:
                    owner_fcurves = getattr(fcurve_owner, "fcurves", None)
                    if owner_fcurves is None:
                        return 0
                    for fcurve in list(fcurves):
                        if getattr(fcurve, "data_path", None) in {"location", "rotation_euler"}:
                            owner_fcurves.remove(fcurve)
                            removed += 1
                except Exception:
                    return removed
                return removed

            def style_camera_fcurves():
                action = camera.animation_data.action if camera.animation_data else None
                if action is None:
                    return 0
                action_slot = get_action_slot(camera.animation_data, action)
                fcurves, _fcurve_owner = collect_action_fcurves(action, action_slot)
                edited = 0
                for fcurve in list(fcurves):
                    if getattr(fcurve, "data_path", None) not in {"location", "rotation_euler"}:
                        continue
                    edited += 1
                    for point in getattr(fcurve, "keyframe_points", []) or []:
                        point.interpolation = interpolation
                    try:
                        fcurve.update()
                    except Exception:
                        pass
                return edited

            removed_fcurves = clear_camera_fcurves() if clear_existing else 0

            start_location = orbit_location(start_angle_degrees)
            camera.location = start_location
            self._look_at(camera, target)
            camera.data.dof.focus_distance = max((camera.location - target).length, 0.1)
            camera.keyframe_insert(data_path="location", frame=start_frame)
            camera.keyframe_insert(data_path="rotation_euler", frame=start_frame)

            end_location = orbit_location(end_angle_degrees)
            camera.location = end_location
            self._look_at(camera, target)
            camera.data.dof.focus_distance = max((camera.location - target).length, 0.1)
            camera.keyframe_insert(data_path="location", frame=end_frame)
            camera.keyframe_insert(data_path="rotation_euler", frame=end_frame)

            edited_fcurves = style_camera_fcurves()

            if set_scene_range:
                scene.frame_start = min(int(scene.frame_start), start_frame)
                scene.frame_end = max(int(scene.frame_end), end_frame)
            if set_active:
                scene.camera = camera

            scene.frame_set(current_frame)
            bpy.context.view_layer.update()

            return {
                "success": True,
                "camera": camera.name,
                "missing_targets": missing,
                "target": [round(value, 6) for value in target],
                "start_frame": start_frame,
                "end_frame": end_frame,
                "start_location": [round(value, 6) for value in start_location],
                "end_location": [round(value, 6) for value in end_location],
                "start_angle_degrees": float(start_angle_degrees),
                "end_angle_degrees": float(end_angle_degrees),
                "orbit_radius": round(orbit_radius, 6),
                "orbit_height": round(orbit_height, 6),
                "interpolation": interpolation,
                "cleared_existing": clear_existing,
                "removed_fcurves": removed_fcurves,
                "edited_fcurves": edited_fcurves,
                "active": scene.camera == camera,
                "dof_focus_distance": camera.data.dof.focus_distance,
                "next_safe_action": "run validate_studio_scene or render_viewport_to_path to verify camera framing before rendering",
            }
        except Exception as e:
            return {"error": f"Failed to create camera orbit animation: {str(e)}"}

    def render_thumbnail_to_path(
        self,
        output_path=None,
        target_names=None,
        preset="studio",
        camera_name="ViperMesh_Thumbnail_Camera",
        resolution=512,
        samples=32,
        file_format="PNG",
        frame_camera=True,
        distance_multiplier=2.45,
        focal_length=70,
    ):
        """Render a lightweight studio thumbnail preview without changing final render intent."""
        def snapshot_object(name):
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"exists": False, "name": name}
            data = {
                "exists": True,
                "name": name,
                "type": obj.type,
                "location": obj.location.copy(),
                "rotation_euler": obj.rotation_euler.copy(),
                "scale": obj.scale.copy(),
                "hide_viewport": bool(obj.hide_viewport),
                "hide_render": bool(obj.hide_render),
            }
            if obj.type == "CAMERA":
                data.update({
                    "lens": obj.data.lens,
                    "clip_start": obj.data.clip_start,
                    "clip_end": obj.data.clip_end,
                    "dof_use": bool(obj.data.dof.use_dof),
                    "dof_focus_distance": obj.data.dof.focus_distance,
                    "dof_aperture_fstop": obj.data.dof.aperture_fstop,
                })
            elif obj.type == "LIGHT":
                data.update({
                    "light_type": obj.data.type,
                    "energy": obj.data.energy,
                    "size": getattr(obj.data, "size", None),
                    "color": tuple(obj.data.color),
                })
            return data

        def restore_object(snapshot):
            obj = bpy.data.objects.get(snapshot["name"])
            if not snapshot["exists"]:
                if obj:
                    bpy.data.objects.remove(obj, do_unlink=True)
                return
            if not obj or obj.type != snapshot["type"]:
                return
            obj.location = snapshot["location"]
            obj.rotation_euler = snapshot["rotation_euler"]
            obj.scale = snapshot["scale"]
            obj.hide_viewport = snapshot["hide_viewport"]
            obj.hide_render = snapshot["hide_render"]
            if obj.type == "CAMERA":
                obj.data.lens = snapshot["lens"]
                obj.data.clip_start = snapshot["clip_start"]
                obj.data.clip_end = snapshot["clip_end"]
                obj.data.dof.use_dof = snapshot["dof_use"]
                obj.data.dof.focus_distance = snapshot["dof_focus_distance"]
                obj.data.dof.aperture_fstop = snapshot["dof_aperture_fstop"]
            elif obj.type == "LIGHT":
                obj.data.type = snapshot["light_type"]
                obj.data.energy = snapshot["energy"]
                if snapshot["size"] is not None and hasattr(obj.data, "size"):
                    obj.data.size = snapshot["size"]
                obj.data.color = snapshot["color"]

        scene = bpy.context.scene
        active_camera = scene.camera
        render_state = {
            "filepath": scene.render.filepath,
            "file_format": scene.render.image_settings.file_format,
            "resolution_x": scene.render.resolution_x,
            "resolution_y": scene.render.resolution_y,
            "resolution_percentage": scene.render.resolution_percentage,
            "engine": scene.render.engine,
            "eevee_samples": getattr(scene.eevee, "taa_render_samples", None) if hasattr(scene, "eevee") else None,
        }
        world = scene.world
        world_state = {
            "world": world,
            "color": tuple(world.color) if world else None,
            "background_color": None,
            "background_strength": None,
        }
        if world and world.use_nodes and world.node_tree:
            bg = world.node_tree.nodes.get("Background")
            if bg:
                world_state["background_color"] = tuple(bg.inputs["Color"].default_value)
                world_state["background_strength"] = bg.inputs["Strength"].default_value

        managed_object_snapshots = [
            snapshot_object(camera_name),
            snapshot_object("ViperMesh_Studio_Key"),
            snapshot_object("ViperMesh_Studio_Fill"),
            snapshot_object("ViperMesh_Studio_Rim"),
        ]

        try:
            fmt = str(file_format or "PNG").upper()
            extension = {
                "JPEG": "jpg",
                "JPG": "jpg",
                "PNG": "png",
                "WEBP": "webp",
                "TIFF": "tiff",
                "TARGA": "tga",
                "OPEN_EXR": "exr",
                "HDR": "hdr",
            }.get(fmt, fmt.lower())
            if not output_path:
                output_path = os.path.join(tempfile.gettempdir(), f"vipermesh-thumbnail-{int(time.time() * 1000)}.{extension}")

            resolution = max(128, min(int(resolution), 2048))
            samples = max(1, min(int(samples), 256))

            setup = self.setup_studio_scene(
                target_names=target_names,
                preset=preset,
                camera_name=camera_name,
                frame_camera=frame_camera,
                focal_length=focal_length,
                distance_multiplier=distance_multiplier,
                resolution_x=resolution,
                resolution_y=resolution,
                samples=samples,
                set_active_camera=True,
            )
            if setup.get("error"):
                return setup

            validation = self.validate_studio_scene(
                target_names=target_names,
                camera_name=camera_name,
                require_camera=True,
                require_lights=True,
                require_render_settings=True,
            )
            if validation.get("error"):
                return validation
            if not validation.get("ready"):
                return {
                    "error": "Thumbnail render preflight failed",
                    "validation": validation,
                    "next_safe_action": "setup_studio_scene or fix reported validation errors before retrying render_thumbnail_to_path",
                }

            scene.render.filepath = output_path
            scene.render.image_settings.file_format = fmt
            scene.render.resolution_x = resolution
            scene.render.resolution_y = resolution
            scene.render.resolution_percentage = 100
            try:
                scene.render.engine = "BLENDER_EEVEE_NEXT"
            except TypeError:
                scene.render.engine = "BLENDER_EEVEE"
            if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
                scene.eevee.taa_render_samples = samples

            bpy.ops.render.render(write_still=True)

            return {
                "success": True,
                "thumbnail_render": True,
                "output_path": bpy.path.abspath(scene.render.filepath),
                "target_objects": setup.get("target_objects", []),
                "camera": setup.get("camera"),
                "preset": setup.get("preset"),
                "engine": scene.render.engine,
                "resolution": [scene.render.resolution_x, scene.render.resolution_y],
                "samples": samples,
                "file_format": scene.render.image_settings.file_format,
                "next_safe_action": "use output_path as a lightweight preview artifact; use render_image only for final renders",
            }
        except Exception as e:
            return {"error": f"Failed to render thumbnail: {str(e)}"}
        finally:
            scene.render.filepath = render_state["filepath"]
            scene.render.image_settings.file_format = render_state["file_format"]
            scene.render.resolution_x = render_state["resolution_x"]
            scene.render.resolution_y = render_state["resolution_y"]
            scene.render.resolution_percentage = render_state["resolution_percentage"]
            try:
                scene.render.engine = render_state["engine"]
            except TypeError:
                pass
            if render_state["eevee_samples"] is not None and hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
                scene.eevee.taa_render_samples = render_state["eevee_samples"]
            scene.camera = active_camera
            scene.world = world_state["world"]
            if scene.world and world_state["color"] is not None:
                scene.world.color = world_state["color"]
                if scene.world.use_nodes and scene.world.node_tree:
                    bg = scene.world.node_tree.nodes.get("Background")
                    if bg:
                        if world_state["background_color"] is not None:
                            bg.inputs["Color"].default_value = world_state["background_color"]
                        if world_state["background_strength"] is not None:
                            bg.inputs["Strength"].default_value = world_state["background_strength"]
            for snapshot in managed_object_snapshots:
                restore_object(snapshot)

    def inspect_render_artifact(
        self,
        image_path,
        min_brightness=0.02,
        max_brightness=0.98,
        min_alpha_coverage=0.98,
        edge_sample_percent=0.05,
        corner_sample_percent=0.08,
        background_tolerance=0.08,
        max_sample_pixels=100000,
    ):
        """Inspect a saved render/thumbnail image for basic artifact signals."""
        image = None
        try:
            if not image_path:
                return {"error": "image_path is required"}

            resolved_path = bpy.path.abspath(str(image_path))
            if not os.path.exists(resolved_path):
                return {"error": f"Image file not found: {resolved_path}"}
            if not os.path.isfile(resolved_path):
                return {"error": f"Image path is not a file: {resolved_path}"}

            edge_sample_percent = max(0.01, min(float(edge_sample_percent), 0.25))
            corner_sample_percent = max(0.01, min(float(corner_sample_percent), 0.25))
            background_tolerance = max(0.0, min(float(background_tolerance), 1.0))
            min_brightness = max(0.0, min(float(min_brightness), 1.0))
            max_brightness = max(0.0, min(float(max_brightness), 1.0))
            min_alpha_coverage = max(0.0, min(float(min_alpha_coverage), 1.0))
            max_sample_pixels = max(256, min(int(max_sample_pixels), 2000000))

            image = bpy.data.images.load(resolved_path, check_existing=False)
            width, height = int(image.size[0]), int(image.size[1])
            if width <= 0 or height <= 0:
                return {"error": f"Image has invalid dimensions: {width}x{height}"}

            pixels = array('f', [0.0]) * (width * height * 4)
            image.pixels.foreach_get(pixels)
            pixel_count = width * height
            stride = max(1, int(math.ceil(math.sqrt(pixel_count / max_sample_pixels))))
            edge_px = max(1, int(round(min(width, height) * edge_sample_percent)))
            corner_px = max(1, int(round(min(width, height) * corner_sample_percent)))
            alpha_threshold = 0.01

            stats = {
                "count": 0,
                "brightness_sum": 0.0,
                "brightness_min": 1.0,
                "brightness_max": 0.0,
                "alpha_opaque": 0,
                "alpha_transparent": 0,
                "edge_count": 0,
                "edge_brightness_sum": 0.0,
                "center_count": 0,
                "center_brightness_sum": 0.0,
                "corner_count": 0,
                "corner_r": 0.0,
                "corner_g": 0.0,
                "corner_b": 0.0,
            }
            corner_samples = []
            edge_samples = []
            center_margin_x = max(edge_px, int(round(width * 0.25)))
            center_margin_y = max(edge_px, int(round(height * 0.25)))

            def pixel_at(x, y):
                idx = (y * width + x) * 4
                return float(pixels[idx]), float(pixels[idx + 1]), float(pixels[idx + 2]), float(pixels[idx + 3])

            def brightness_of(r, g, b):
                return 0.2126 * r + 0.7152 * g + 0.0722 * b

            def sampled_axis(size, edge_band):
                values = set(range(0, size, stride))
                values.update(range(max(0, size - edge_band), size, stride))
                values.add(0)
                values.add(size - 1)
                return sorted(values)

            sample_edge_band = max(edge_px, corner_px)
            x_samples = sampled_axis(width, sample_edge_band)
            y_samples = sampled_axis(height, sample_edge_band)

            for y in y_samples:
                for x in x_samples:
                    r, g, b, a = pixel_at(x, y)
                    brightness = brightness_of(r, g, b)
                    stats["count"] += 1
                    stats["brightness_sum"] += brightness
                    stats["brightness_min"] = min(stats["brightness_min"], brightness)
                    stats["brightness_max"] = max(stats["brightness_max"], brightness)
                    if a >= 1.0 - alpha_threshold:
                        stats["alpha_opaque"] += 1
                    if a <= alpha_threshold:
                        stats["alpha_transparent"] += 1

                    is_edge = x < edge_px or x >= width - edge_px or y < edge_px or y >= height - edge_px
                    is_corner = (x < corner_px or x >= width - corner_px) and (y < corner_px or y >= height - corner_px)
                    is_center = center_margin_x <= x < width - center_margin_x and center_margin_y <= y < height - center_margin_y

                    if is_edge:
                        stats["edge_count"] += 1
                        stats["edge_brightness_sum"] += brightness
                        edge_samples.append((r, g, b))
                    if is_corner:
                        stats["corner_count"] += 1
                        stats["corner_r"] += r
                        stats["corner_g"] += g
                        stats["corner_b"] += b
                        corner_samples.append((r, g, b))
                    if is_center:
                        stats["center_count"] += 1
                        stats["center_brightness_sum"] += brightness

            if stats["count"] == 0:
                return {"error": "No pixels were sampled from image"}

            brightness_mean = stats["brightness_sum"] / stats["count"]
            edge_brightness = stats["edge_brightness_sum"] / stats["edge_count"] if stats["edge_count"] else None
            center_brightness = stats["center_brightness_sum"] / stats["center_count"] if stats["center_count"] else None
            alpha_coverage = stats["alpha_opaque"] / stats["count"]
            transparent_fraction = stats["alpha_transparent"] / stats["count"]

            corner_background_rgb = None
            corner_background_similarity = None
            edge_foreground_ratio = None
            if stats["corner_count"] > 0:
                corner_background_rgb = [
                    stats["corner_r"] / stats["corner_count"],
                    stats["corner_g"] / stats["corner_count"],
                    stats["corner_b"] / stats["corner_count"],
                ]
                corner_diffs = [
                    max(abs(sample[channel] - corner_background_rgb[channel]) for channel in range(3))
                    for sample in corner_samples
                ]
                mean_corner_diff = sum(corner_diffs) / len(corner_diffs) if corner_diffs else 0.0
                corner_background_similarity = max(0.0, 1.0 - mean_corner_diff)

                edge_diffs = [
                    max(abs(sample[channel] - corner_background_rgb[channel]) for channel in range(3))
                    for sample in edge_samples
                ]
                edge_foreground_ratio = (
                    sum(1 for diff in edge_diffs if diff > background_tolerance) / len(edge_diffs)
                    if edge_diffs else 0.0
                )

            warnings = []
            if brightness_mean < min_brightness:
                warnings.append("image is very dark; render may be underexposed or blank")
            if brightness_mean > max_brightness:
                warnings.append("image is very bright; render may be overexposed or mostly blank background")
            if alpha_coverage < min_alpha_coverage:
                warnings.append("image contains substantial transparency; confirm this is intentional and saved in an alpha-capable format")
            if edge_foreground_ratio is not None and edge_foreground_ratio > 0.35:
                warnings.append("edge pixels differ from the corner background; subject or scene content may be cropped or touching the frame")
            if corner_background_similarity is not None and corner_background_similarity < 0.92:
                warnings.append("corner background samples vary; background may be uneven, cropped, or not a clean studio backdrop")

            return {
                "success": True,
                "ready": len(warnings) == 0,
                "image_path": resolved_path,
                "dimensions": [width, height],
                "sampled_pixels": stats["count"],
                "sample_stride": stride,
                "brightness": {
                    "mean": round(brightness_mean, 6),
                    "min": round(stats["brightness_min"], 6),
                    "max": round(stats["brightness_max"], 6),
                    "edge_mean": round(edge_brightness, 6) if edge_brightness is not None else None,
                    "center_mean": round(center_brightness, 6) if center_brightness is not None else None,
                },
                "alpha_coverage": round(alpha_coverage, 6),
                "transparent_fraction": round(transparent_fraction, 6),
                "corner_background_rgb": [round(value, 6) for value in corner_background_rgb] if corner_background_rgb else None,
                "corner_background_similarity": round(corner_background_similarity, 6) if corner_background_similarity is not None else None,
                "edge_foreground_ratio": round(edge_foreground_ratio, 6) if edge_foreground_ratio is not None else None,
                "warnings": warnings,
                "next_safe_action": "use render_viewport_to_path or get_viewport_screenshot to visually verify composition" if warnings else "use this artifact as a render/thumbnail validation signal alongside visual review",
            }
        except Exception as e:
            return {"error": f"Failed to inspect render artifact: {str(e)}"}
        finally:
            if image:
                with suppress(Exception):
                    bpy.data.images.remove(image)

    def add_light(self, light_type='POINT', name=None, location=None, energy=None, color=None):
        """Add a new light to the scene. Types: POINT, SUN, SPOT, AREA."""
        try:
            valid = {'POINT', 'SUN', 'SPOT', 'AREA'}
            lt = light_type.upper()
            if lt not in valid:
                return {"error": f"Invalid light type: {light_type}. Use one of {valid}"}

            light_name = name or f"{lt.capitalize()}Light"
            light_data = bpy.data.lights.new(name=light_name, type=lt)
            if energy is not None:
                light_data.energy = float(energy)
            if color is not None:
                light_data.color = tuple(float(c) for c in color[:3])

            light_obj = bpy.data.objects.new(name=light_name, object_data=light_data)
            bpy.context.collection.objects.link(light_obj)

            if location is not None:
                light_obj.location = tuple(float(v) for v in location[:3])

            return {
                "success": True,
                "name": light_obj.name,
                "type": lt,
                "energy": light_data.energy,
                "color": list(light_data.color),
                "location": list(light_obj.location),
            }
        except Exception as e:
            return {"error": f"Failed to add light: {str(e)}"}

    def set_light_properties(self, name, energy=None, color=None, shadow_soft_size=None,
                              spot_size=None, spot_blend=None, size=None):
        """Set properties on an existing light object."""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}
            if obj.type != 'LIGHT':
                return {"error": f"Object '{name}' is not a light (type: {obj.type})"}

            light = obj.data
            changes = []

            if energy is not None:
                light.energy = float(energy)
                changes.append(f"energy={energy}")
            if color is not None:
                light.color = tuple(float(c) for c in color[:3])
                changes.append(f"color={list(light.color)}")
            if shadow_soft_size is not None:
                light.shadow_soft_size = float(shadow_soft_size)
                changes.append(f"shadow_soft_size={shadow_soft_size}")
            if spot_size is not None and light.type == 'SPOT':
                import math
                light.spot_size = math.radians(float(spot_size))
                changes.append(f"spot_size={spot_size}°")
            if spot_blend is not None and light.type == 'SPOT':
                light.spot_blend = float(spot_blend)
                changes.append(f"spot_blend={spot_blend}")
            if size is not None and light.type == 'AREA':
                light.size = float(size)
                changes.append(f"size={size}")

            if not changes:
                return {"error": "No valid properties provided"}

            return {
                "success": True,
                "light": name,
                "light_type": light.type,
                "changes": changes,
            }
        except Exception as e:
            return {"error": f"Failed to set light properties: {str(e)}"}

    def add_camera(self, name=None, location=None, rotation=None, lens=None, sensor_width=None):
        """Add a new camera to the scene."""
        try:
            import math
            cam_name = name or "Camera"
            cam_data = bpy.data.cameras.new(name=cam_name)
            if lens is not None:
                cam_data.lens = float(lens)
            if sensor_width is not None:
                cam_data.sensor_width = float(sensor_width)

            cam_obj = bpy.data.objects.new(name=cam_name, object_data=cam_data)
            bpy.context.collection.objects.link(cam_obj)

            if location is not None:
                cam_obj.location = tuple(float(v) for v in location[:3])
            if rotation is not None:
                cam_obj.rotation_euler = tuple(math.radians(float(v)) for v in rotation[:3])

            return {
                "success": True,
                "name": cam_obj.name,
                "lens": cam_data.lens,
                "sensor_width": cam_data.sensor_width,
                "location": list(cam_obj.location),
                "rotation_deg": [round(math.degrees(r), 2) for r in cam_obj.rotation_euler],
            }
        except Exception as e:
            return {"error": f"Failed to add camera: {str(e)}"}

    def set_camera_properties(self, name, lens=None, sensor_width=None, clip_start=None,
                               clip_end=None, dof_use=None, dof_focus_distance=None,
                               dof_aperture_fstop=None, set_active=None):
        """Set properties on an existing camera. Optionally set it as the active scene camera."""
        try:
            obj = bpy.data.objects.get(name)
            if not obj:
                return {"error": f"Object not found: {name}"}
            if obj.type != 'CAMERA':
                return {"error": f"Object '{name}' is not a camera (type: {obj.type})"}

            cam = obj.data
            changes = []

            if lens is not None:
                cam.lens = float(lens)
                changes.append(f"lens={lens}mm")
            if sensor_width is not None:
                cam.sensor_width = float(sensor_width)
                changes.append(f"sensor_width={sensor_width}")
            if clip_start is not None:
                cam.clip_start = float(clip_start)
                changes.append(f"clip_start={clip_start}")
            if clip_end is not None:
                cam.clip_end = float(clip_end)
                changes.append(f"clip_end={clip_end}")
            if dof_use is not None:
                cam.dof.use_dof = bool(dof_use)
                changes.append(f"dof_use={dof_use}")
            if dof_focus_distance is not None:
                cam.dof.focus_distance = float(dof_focus_distance)
                changes.append(f"dof_focus_distance={dof_focus_distance}")
            if dof_aperture_fstop is not None:
                cam.dof.aperture_fstop = float(dof_aperture_fstop)
                changes.append(f"dof_aperture_fstop={dof_aperture_fstop}")
            if set_active is not None and set_active:
                bpy.context.scene.camera = obj
                changes.append("set_active=True")

            if not changes:
                return {"error": "No valid properties provided"}

            return {
                "success": True,
                "camera": name,
                "changes": changes,
            }
        except Exception as e:
            return {"error": f"Failed to set camera properties: {str(e)}"}

    def aim_camera_at(self, name, target_name=None, target_location=None, set_active=None, set_dof_focus=True):
        """Aim an existing camera at an object or world-space point without manual Euler guesses."""
        try:
            def normalize_bool(value, default=False):
                if value is None:
                    return default
                if isinstance(value, str):
                    normalized = value.strip().lower()
                    if normalized in {"false", "0", "no", "n", "off"}:
                        return False
                    if normalized in {"true", "1", "yes", "y", "on"}:
                        return True
                return bool(value)

            should_set_active = normalize_bool(set_active, False)
            should_set_dof_focus = normalize_bool(set_dof_focus, True)

            camera_obj = bpy.data.objects.get(name)
            if not camera_obj:
                return {"error": f"Object not found: {name}"}
            if camera_obj.type != 'CAMERA':
                return {"error": f"Object '{name}' is not a camera (type: {camera_obj.type})"}

            target_obj = None
            if target_name:
                target_obj = bpy.data.objects.get(str(target_name))
                if not target_obj:
                    return {"error": f"Target object not found: {target_name}"}
                if hasattr(target_obj, "bound_box") and target_obj.bound_box:
                    points = [target_obj.matrix_world @ mathutils.Vector(corner) for corner in target_obj.bound_box]
                    target = mathutils.Vector((
                        sum(point.x for point in points) / len(points),
                        sum(point.y for point in points) / len(points),
                        sum(point.z for point in points) / len(points),
                    ))
                else:
                    target = target_obj.location.copy()
            elif target_location is not None:
                if len(target_location) < 3:
                    return {"error": "target_location must contain three numbers"}
                target = mathutils.Vector(tuple(float(value) for value in target_location[:3]))
            else:
                return {"error": "Provide target_name or target_location"}

            self._look_at(camera_obj, target)
            focus_distance = max((camera_obj.location - target).length, 0.001)

            if should_set_dof_focus:
                camera_obj.data.dof.use_dof = True
                camera_obj.data.dof.focus_distance = focus_distance

            if should_set_active:
                bpy.context.scene.camera = camera_obj

            return {
                "success": True,
                "camera": camera_obj.name,
                "target_name": target_obj.name if target_obj else None,
                "target_location": [float(target.x), float(target.y), float(target.z)],
                "rotation_deg": [round(math.degrees(value), 3) for value in camera_obj.rotation_euler],
                "focus_distance": float(focus_distance),
                "dof_focus_updated": should_set_dof_focus,
                "active_camera": bpy.context.scene.camera.name if bpy.context.scene.camera else None,
                "next_safe_action": "run validate_studio_scene or render_viewport_to_path to verify camera framing",
            }
        except Exception as e:
            return {"error": f"Failed to aim camera: {str(e)}"}

    def set_render_settings(self, engine=None, resolution_x=None, resolution_y=None,
                             resolution_percentage=None, samples=None, use_denoising=None,
                             film_transparent=None, output_path=None, file_format=None):
        """Set render engine and render settings. Engines: BLENDER_EEVEE, CYCLES."""
        try:
            scene = bpy.context.scene
            changes = []
            engine_hints = {item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
            engine_hints.add(scene.render.engine)
            requested_engine = None

            if engine is not None:
                eng = str(engine).upper()
                requested_engine = eng
                candidates = [eng]
                if eng in ('EEVEE', 'BLENDER_EEVEE', 'EEVEE_NEXT', 'BLENDER_EEVEE_NEXT'):
                    candidates = ['BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT']
                # Static RNA enum_items omits dynamically registered engines such as Cycles.
                # Property assignment uses Blender's complete runtime enum and validates it.
                engine_error = None
                for candidate in candidates:
                    try:
                        scene.render.engine = candidate
                        engine_error = None
                        break
                    except (TypeError, ValueError) as exc:
                        engine_error = str(exc)
                if engine_error:
                    return {"error": f"Render engine '{requested_engine}' is not available: {engine_error}",
                            "available_engines": sorted(engine_hints), "available_engines_complete": False}
                eng = scene.render.engine
                engine_hints.add(eng)
                if requested_engine != eng:
                    changes.append(f"requested_engine={requested_engine}")
                changes.append(f"engine={eng}")
            if resolution_x is not None:
                scene.render.resolution_x = int(resolution_x)
                changes.append(f"resolution_x={resolution_x}")
            if resolution_y is not None:
                scene.render.resolution_y = int(resolution_y)
                changes.append(f"resolution_y={resolution_y}")
            if resolution_percentage is not None:
                scene.render.resolution_percentage = int(resolution_percentage)
                changes.append(f"resolution_percentage={resolution_percentage}")
            if samples is not None:
                if scene.render.engine == 'CYCLES':
                    scene.cycles.samples = int(samples)
                elif hasattr(scene.eevee, 'taa_render_samples'):
                    scene.eevee.taa_render_samples = int(samples)
                changes.append(f"samples={samples}")
            if use_denoising is not None:
                if scene.render.engine == 'CYCLES':
                    scene.cycles.use_denoising = bool(use_denoising)
                changes.append(f"use_denoising={use_denoising}")
            if film_transparent is not None:
                scene.render.film_transparent = bool(film_transparent)
                changes.append(f"film_transparent={film_transparent}")
            if output_path is not None:
                scene.render.filepath = output_path
                changes.append(f"output_path={output_path}")
            if file_format is not None:
                scene.render.image_settings.file_format = file_format.upper()
                changes.append(f"file_format={file_format}")

            if not changes:
                return {"error": "No valid settings provided"}

            return {
                "success": True,
                "requested_engine": requested_engine,
                "engine": scene.render.engine,
                "available_engines": sorted(engine_hints),
                "available_engines_complete": False,
                "resolution": f"{scene.render.resolution_x}x{scene.render.resolution_y}",
                "changes": changes,
            }
        except Exception as e:
            return {"error": f"Failed to set render settings: {str(e)}"}

    def render_image(self, output_path=None, file_format=None, open_after=False):
        """Render the current scene and optionally save to a file. Returns the output path."""
        try:
            scene = bpy.context.scene

            if output_path:
                scene.render.filepath = output_path
            if file_format:
                scene.render.image_settings.file_format = file_format.upper()

            bpy.ops.render.render(write_still=True)

            return {
                "success": True,
                "output_path": bpy.path.abspath(scene.render.filepath),
                "engine": scene.render.engine,
                "resolution": f"{scene.render.resolution_x}x{scene.render.resolution_y}",
                "file_format": scene.render.image_settings.file_format,
            }
        except Exception as e:
            return {"error": f"Failed to render: {str(e)}"}

    def get_polyhaven_categories(self, asset_type):
        """Get categories for a specific asset type from Polyhaven"""
        try:
            if asset_type not in ["hdris", "textures", "models", "all"]:
                return {"error": f"Invalid asset type: {asset_type}. Must be one of: hdris, textures, models, all"}

            response = requests.get(f"https://api.polyhaven.com/categories/{asset_type}", headers=REQ_HEADERS, timeout=30)
            if response.status_code == 200:
                return {"categories": response.json()}
            else:
                return {"error": f"API request failed with status code {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def search_polyhaven_assets(self, asset_type=None, categories=None):
        """Search for assets from Polyhaven with optional filtering"""
        try:
            url = "https://api.polyhaven.com/assets"
            params = {}

            if asset_type and asset_type != "all":
                if asset_type not in ["hdris", "textures", "models"]:
                    return {"error": f"Invalid asset type: {asset_type}. Must be one of: hdris, textures, models, all"}
                params["type"] = asset_type

            if categories:
                params["categories"] = categories

            response = requests.get(url, params=params, headers=REQ_HEADERS, timeout=30)
            if response.status_code == 200:
                # Limit the response size to avoid overwhelming Blender
                assets = response.json()
                # Return only the first 20 assets to keep response size manageable
                limited_assets = {}
                for i, (key, value) in enumerate(assets.items()):
                    if i >= 20:  # Limit to 20 assets
                        break
                    limited_assets[key] = value

                return {"assets": limited_assets, "total_count": len(assets), "returned_count": len(limited_assets)}
            else:
                return {"error": f"API request failed with status code {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def download_polyhaven_asset(self, asset_id, asset_type, resolution="1k", file_format=None):
        try:
            # First get the files information
            files_response = requests.get(f"https://api.polyhaven.com/files/{asset_id}", headers=REQ_HEADERS, timeout=30)
            if files_response.status_code != 200:
                return {"error": f"Failed to get asset files: {files_response.status_code}"}

            files_data = files_response.json()

            # Handle different asset types
            if asset_type == "hdris":
                # For HDRIs, download the .hdr or .exr file
                if not file_format:
                    file_format = "hdr"  # Default format for HDRIs

                if "hdri" in files_data and resolution in files_data["hdri"] and file_format in files_data["hdri"][resolution]:
                    file_info = files_data["hdri"][resolution][file_format]
                    file_url = file_info["url"]

                    # Save HDRI to a persistent cache directory so Blender can
                    # reference the file after loading (temp files get deleted and
                    # cause pink 'missing texture' errors)
                    cache_dir = os.path.join(os.path.expanduser("~"), ".vipermesh", "cache", "hdris")
                    os.makedirs(cache_dir, exist_ok=True)
                    # Sanitize filename parts to prevent path traversal
                    safe_asset_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in asset_id)
                    safe_resolution = "".join(c if c.isalnum() or c in "-_" else "_" for c in resolution)
                    safe_format = str(file_format).lower()
                    if safe_format not in {"hdr", "exr"}:
                        return {"error": f"Unsupported HDRI format: {file_format}"}
                    cache_path = os.path.abspath(
                        os.path.join(cache_dir, f"{safe_asset_id}_{safe_resolution}.{safe_format}")
                    )
                    if os.path.commonpath([os.path.abspath(cache_dir), cache_path]) != os.path.abspath(cache_dir):
                        return {"error": "Invalid HDRI cache path"}

                    # Download the file (skip if already cached)
                    if not os.path.isfile(cache_path):
                        response = requests.get(file_url, headers=REQ_HEADERS, timeout=60)
                        if response.status_code != 200:
                            return {"error": f"Failed to download HDRI: {response.status_code}"}
                        with open(cache_path, 'wb') as f:
                            f.write(response.content)

                    try:
                        # Create a new world if none exists
                        if not bpy.data.worlds:
                            bpy.data.worlds.new("World")

                        world = bpy.data.worlds[0]
                        world.use_nodes = True
                        node_tree = world.node_tree

                        # Clear existing nodes
                        for node in node_tree.nodes:
                            node_tree.nodes.remove(node)

                        # Create nodes
                        tex_coord = node_tree.nodes.new(type='ShaderNodeTexCoord')
                        tex_coord.location = (-800, 0)

                        mapping = node_tree.nodes.new(type='ShaderNodeMapping')
                        mapping.location = (-600, 0)

                        # Load the image from the persistent cache file
                        env_tex = node_tree.nodes.new(type='ShaderNodeTexEnvironment')
                        env_tex.location = (-400, 0)
                        env_tex.image = bpy.data.images.load(cache_path)

                        # Use a color space that exists in all Blender versions
                        if file_format.lower() == 'exr':
                            # Try to use Linear color space for EXR files
                            try:
                                env_tex.image.colorspace_settings.name = 'Linear'
                            except:
                                # Fallback to Non-Color if Linear isn't available
                                env_tex.image.colorspace_settings.name = 'Non-Color'
                        else:  # hdr
                            # For HDR files, try these options in order
                            for color_space in ['Linear', 'Linear Rec.709', 'Non-Color']:
                                try:
                                    env_tex.image.colorspace_settings.name = color_space
                                    break  # Stop if we successfully set a color space
                                except:
                                    continue

                        background = node_tree.nodes.new(type='ShaderNodeBackground')
                        background.location = (-200, 0)

                        output = node_tree.nodes.new(type='ShaderNodeOutputWorld')
                        output.location = (0, 0)

                        # Connect nodes
                        node_tree.links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
                        node_tree.links.new(mapping.outputs['Vector'], env_tex.inputs['Vector'])
                        node_tree.links.new(env_tex.outputs['Color'], background.inputs['Color'])
                        node_tree.links.new(background.outputs['Background'], output.inputs['Surface'])

                        # Set as active world
                        bpy.context.scene.world = world

                        return {
                            "success": True,
                            "message": f"HDRI {asset_id} imported successfully",
                            "image_name": env_tex.image.name
                        }
                    except Exception as e:
                        return {"error": f"Failed to set up HDRI in Blender: {str(e)}"}
                else:
                    return {"error": f"Requested resolution or format not available for this HDRI"}

            elif asset_type == "textures":
                if not file_format:
                    file_format = "jpg"  # Default format for textures

                downloaded_maps = {}

                try:
                    for map_type in files_data:
                        if map_type not in ["blend", "gltf"]:  # Skip non-texture files
                            if resolution in files_data[map_type] and file_format in files_data[map_type][resolution]:
                                file_info = files_data[map_type][resolution][file_format]
                                file_url = file_info["url"]

                                # Use NamedTemporaryFile like we do for HDRIs
                                with tempfile.NamedTemporaryFile(suffix=f".{file_format}", delete=False) as tmp_file:
                                    # Download the file
                                    response = requests.get(file_url, headers=REQ_HEADERS, timeout=60)
                                    if response.status_code == 200:
                                        tmp_file.write(response.content)
                                        tmp_path = tmp_file.name

                                        # Load image from temporary file
                                        image = bpy.data.images.load(tmp_path)
                                        image.name = f"{asset_id}_{map_type}.{file_format}"

                                        # Pack the image into .blend file
                                        image.pack()

                                        # Set color space based on map type
                                        if map_type in ['color', 'diffuse', 'albedo']:
                                            try:
                                                image.colorspace_settings.name = 'sRGB'
                                            except:
                                                pass
                                        else:
                                            try:
                                                image.colorspace_settings.name = 'Non-Color'
                                            except:
                                                pass

                                        downloaded_maps[map_type] = image

                                        # Clean up temporary file
                                        try:
                                            os.unlink(tmp_path)
                                        except:
                                            pass

                    if not downloaded_maps:
                        return {"error": f"No texture maps found for the requested resolution and format"}

                    # Create a new material with the downloaded textures
                    mat = bpy.data.materials.new(name=asset_id)
                    mat.use_nodes = True # Fix #8: Add use_nodes=True safety check
                    nodes = mat.node_tree.nodes
                    links = mat.node_tree.links

                    # Clear default nodes
                    for node in nodes:
                        nodes.remove(node)

                    # Create output node
                    output = nodes.new(type='ShaderNodeOutputMaterial')
                    output.location = (300, 0)

                    # Create principled BSDF node
                    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
                    principled.location = (0, 0)
                    links.new(principled.outputs[0], output.inputs[0])

                    # Add texture nodes based on available maps
                    tex_coord = nodes.new(type='ShaderNodeTexCoord')
                    tex_coord.location = (-800, 0)

                    mapping = nodes.new(type='ShaderNodeMapping')
                    mapping.location = (-600, 0)
                    mapping.vector_type = 'TEXTURE'  # Changed from default 'POINT' to 'TEXTURE'
                    links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])

                    # Position offset for texture nodes
                    x_pos = -400
                    y_pos = 300

                    # Connect different texture maps
                    for map_type, image in downloaded_maps.items():
                        tex_node = nodes.new(type='ShaderNodeTexImage')
                        tex_node.location = (x_pos, y_pos)
                        tex_node.image = image

                        # Set color space based on map type
                        if map_type.lower() in ['color', 'diffuse', 'albedo']:
                            try:
                                tex_node.image.colorspace_settings.name = 'sRGB'
                            except:
                                pass  # Use default if sRGB not available
                        else:
                            try:
                                tex_node.image.colorspace_settings.name = 'Non-Color'
                            except:
                                pass  # Use default if Non-Color not available

                        links.new(mapping.outputs['Vector'], tex_node.inputs['Vector'])

                        # Connect to appropriate input on Principled BSDF
                        if map_type.lower() in ['color', 'diffuse', 'albedo']:
                            links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
                        elif map_type.lower() in ['roughness', 'rough']:
                            links.new(tex_node.outputs['Color'], principled.inputs['Roughness'])
                        elif map_type.lower() in ['metallic', 'metalness', 'metal']:
                            links.new(tex_node.outputs['Color'], principled.inputs['Metallic'])
                        elif map_type.lower() in ['normal', 'nor']:
                            # Add normal map node
                            normal_map = nodes.new(type='ShaderNodeNormalMap')
                            normal_map.location = (x_pos + 200, y_pos)
                            links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
                            links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
                        elif map_type in ['displacement', 'disp', 'height']:
                            # Add displacement node
                            disp_node = nodes.new(type='ShaderNodeDisplacement')
                            disp_node.location = (x_pos + 200, y_pos - 200)
                            links.new(tex_node.outputs['Color'], disp_node.inputs['Height'])
                            links.new(disp_node.outputs['Displacement'], output.inputs['Displacement'])

                        y_pos -= 250

                    return {
                        "success": True,
                        "message": f"Texture {asset_id} imported as material",
                        "material": mat.name,
                        "maps": list(downloaded_maps.keys())
                    }

                except Exception as e:
                    return {"error": f"Failed to process textures: {str(e)}"}

            elif asset_type == "models":
                # For models, prefer glTF format if available
                if not file_format:
                    file_format = "gltf"  # Default format for models

                if file_format in files_data and resolution in files_data[file_format]:
                    file_info = files_data[file_format][resolution][file_format]
                    file_url = file_info["url"]

                    # Create a temporary directory to store the model and its dependencies
                    temp_dir = tempfile.mkdtemp()
                    main_file_path = ""

                    try:
                        # Download the main model file
                        main_file_name = file_url.split("/")[-1]
                        main_file_path = os.path.join(temp_dir, main_file_name)

                        response = requests.get(file_url, headers=REQ_HEADERS, timeout=60)
                        if response.status_code != 200:
                            return {"error": f"Failed to download model: {response.status_code}"}

                        with open(main_file_path, "wb") as f:
                            f.write(response.content)

                        # Check for included files and download them
                        if "include" in file_info and file_info["include"]:
                            for include_path, include_info in file_info["include"].items():
                                # Get the URL for the included file - this is the fix
                                include_url = include_info["url"]

                                # Create the directory structure for the included file
                                include_file_path = os.path.join(temp_dir, include_path)
                                os.makedirs(os.path.dirname(include_file_path), exist_ok=True)

                                # Download the included file
                                include_response = requests.get(include_url, headers=REQ_HEADERS, timeout=60)
                                if include_response.status_code == 200:
                                    with open(include_file_path, "wb") as f:
                                        f.write(include_response.content)
                                else:
                                    print(f"Failed to download included file: {include_path}")

                        # Import the model into Blender
                        if file_format == "gltf" or file_format == "glb":
                            bpy.ops.import_scene.gltf(filepath=main_file_path)
                        elif file_format == "fbx":
                            bpy.ops.import_scene.fbx(filepath=main_file_path)
                        elif file_format == "obj":
                            bpy.ops.import_scene.obj(filepath=main_file_path)
                        elif file_format == "blend":
                            # For blend files, we need to append or link
                            with bpy.data.libraries.load(main_file_path, link=False) as (data_from, data_to):
                                data_to.objects = data_from.objects

                            # Link the objects to the scene
                            for obj in data_to.objects:
                                if obj is not None:
                                    bpy.context.collection.objects.link(obj)
                        else:
                            return {"error": f"Unsupported model format: {file_format}"}

                        # Get the names of imported objects
                        imported_objects = [obj.name for obj in bpy.context.selected_objects]

                        return {
                            "success": True,
                            "message": f"Model {asset_id} imported successfully",
                            "imported_objects": imported_objects
                        }
                    except Exception as e:
                        return {"error": f"Failed to import model: {str(e)}"}
                    finally:
                        # Clean up temporary directory
                        with suppress(Exception):
                            shutil.rmtree(temp_dir)
                else:
                    return {"error": f"Requested format or resolution not available for this model"}

            else:
                return {"error": f"Unsupported asset type: {asset_type}"}

        except Exception as e:
            return {"error": f"Failed to download asset: {str(e)}"}

    def set_texture(self, object_name, texture_id):
        """Apply a previously downloaded Polyhaven texture to an object by creating a new material"""
        try:
            # Get the object
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"error": f"Object not found: {object_name}"}

            # Make sure object can accept materials
            if not hasattr(obj, 'data') or not hasattr(obj.data, 'materials'):
                return {"error": f"Object {object_name} cannot accept materials"}

            # Find all images related to this texture and ensure they're properly loaded
            texture_images = {}
            for img in bpy.data.images:
                if img.name.startswith(texture_id + "_"):
                    # Extract the map type from the image name
                    map_type = img.name.split('_')[-1].split('.')[0]

                    # Force a reload of the image
                    img.reload()

                    # Ensure proper color space
                    if map_type.lower() in ['color', 'diffuse', 'albedo']:
                        try:
                            img.colorspace_settings.name = 'sRGB'
                        except:
                            pass
                    else:
                        try:
                            img.colorspace_settings.name = 'Non-Color'
                        except:
                            pass

                    # Ensure the image is packed
                    if not img.packed_file:
                        img.pack()

                    texture_images[map_type] = img
                    print(f"Loaded texture map: {map_type} - {img.name}")

                    # Debug info
                    print(f"Image size: {img.size[0]}x{img.size[1]}")
                    print(f"Color space: {img.colorspace_settings.name}")
                    print(f"File format: {img.file_format}")
                    print(f"Is packed: {bool(img.packed_file)}")

            if not texture_images:
                return {"error": f"No texture images found for: {texture_id}. Please download the texture first."}

            # Create a new material
            new_mat_name = f"{texture_id}_material_{object_name}"

            # Remove any existing material with this name to avoid conflicts
            existing_mat = bpy.data.materials.get(new_mat_name)
            if existing_mat:
                bpy.data.materials.remove(existing_mat)

            new_mat = bpy.data.materials.new(name=new_mat_name)
            new_mat.use_nodes = True

            # Set up the material nodes
            nodes = new_mat.node_tree.nodes
            links = new_mat.node_tree.links

            # Clear default nodes
            nodes.clear()

            # Create output node
            output = nodes.new(type='ShaderNodeOutputMaterial')
            output.location = (600, 0)

            # Create principled BSDF node
            principled = nodes.new(type='ShaderNodeBsdfPrincipled')
            principled.location = (300, 0)
            links.new(principled.outputs[0], output.inputs[0])

            # Add texture nodes based on available maps
            tex_coord = nodes.new(type='ShaderNodeTexCoord')
            tex_coord.location = (-800, 0)

            mapping = nodes.new(type='ShaderNodeMapping')
            mapping.location = (-600, 0)
            mapping.vector_type = 'TEXTURE'  # Changed from default 'POINT' to 'TEXTURE'
            links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])

            # Position offset for texture nodes
            x_pos = -400
            y_pos = 300

            # Connect different texture maps
            for map_type, image in texture_images.items():
                tex_node = nodes.new(type='ShaderNodeTexImage')
                tex_node.location = (x_pos, y_pos)
                tex_node.image = image

                # Set color space based on map type
                if map_type.lower() in ['color', 'diffuse', 'albedo']:
                    try:
                        tex_node.image.colorspace_settings.name = 'sRGB'
                    except:
                        pass  # Use default if sRGB not available
                else:
                    try:
                        tex_node.image.colorspace_settings.name = 'Non-Color'
                    except:
                        pass  # Use default if Non-Color not available

                links.new(mapping.outputs['Vector'], tex_node.inputs['Vector'])

                # Connect to appropriate input on Principled BSDF
                if map_type.lower() in ['color', 'diffuse', 'albedo']:
                    links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
                elif map_type.lower() in ['roughness', 'rough']:
                    links.new(tex_node.outputs['Color'], principled.inputs['Roughness'])
                elif map_type.lower() in ['metallic', 'metalness', 'metal']:
                    links.new(tex_node.outputs['Color'], principled.inputs['Metallic'])
                elif map_type.lower() in ['normal', 'nor', 'dx', 'gl']:
                    # Add normal map node
                    normal_map = nodes.new(type='ShaderNodeNormalMap')
                    normal_map.location = (x_pos + 200, y_pos)
                    links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
                    links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
                elif map_type.lower() in ['displacement', 'disp', 'height']:
                    # Add displacement node
                    disp_node = nodes.new(type='ShaderNodeDisplacement')
                    disp_node.location = (x_pos + 200, y_pos - 200)
                    disp_node.inputs['Scale'].default_value = 0.1  # Reduce displacement strength
                    links.new(tex_node.outputs['Color'], disp_node.inputs['Height'])
                    links.new(disp_node.outputs['Displacement'], output.inputs['Displacement'])

                y_pos -= 250

            # Build lookup of tex nodes by map type for ARM/AO handling
            texture_nodes = {}
            for node in nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    for map_type, image in texture_images.items():
                        if node.image == image:
                            texture_nodes[map_type] = node
                            break

            # Handle ARM texture (Ambient Occlusion, Roughness, Metallic packed)
            if 'arm' in texture_nodes:
                separate_rgb = nodes.new(type='ShaderNodeSeparateColor')
                separate_rgb.location = (-200, -100)
                links.new(texture_nodes['arm'].outputs['Color'], separate_rgb.inputs['Color'])

                # Connect Roughness (G) if no dedicated roughness map
                if not any(mn in texture_nodes for mn in ['roughness', 'rough']):
                    links.new(separate_rgb.outputs[1], principled.inputs['Roughness'])
                    print("Connected ARM.G to Roughness")

                # Connect Metallic (B) if no dedicated metallic map
                if not any(mn in texture_nodes for mn in ['metallic', 'metalness', 'metal']):
                    links.new(separate_rgb.outputs[2], principled.inputs['Metallic'])
                    print("Connected ARM.B to Metallic")

                # For AO (R channel), multiply with base color if we have one
                base_color_node = None
                for mn in ['color', 'diffuse', 'albedo']:
                    if mn in texture_nodes:
                        base_color_node = texture_nodes[mn]
                        break

                if base_color_node:
                    mix_node = nodes.new(type='ShaderNodeMix')
                    mix_node.data_type = 'RGBA'
                    mix_node.blend_type = 'MULTIPLY'
                    mix_node.location = (100, 200)
                    mix_node.inputs['Factor'].default_value = 0.8

                    # Disconnect direct connection to base color
                    for link in list(base_color_node.outputs['Color'].links):
                        if link.to_socket == principled.inputs['Base Color']:
                            links.remove(link)

                    links.new(base_color_node.outputs['Color'], mix_node.inputs[6])  # A input
                    links.new(separate_rgb.outputs[0], mix_node.inputs[7])  # B input
                    links.new(mix_node.outputs[2], principled.inputs['Base Color'])  # Result
                    print("Connected ARM.R to AO mix with Base Color")

            # Handle AO (Ambient Occlusion) if separate
            if 'ao' in texture_nodes:
                base_color_node = None
                for mn in ['color', 'diffuse', 'albedo']:
                    if mn in texture_nodes:
                        base_color_node = texture_nodes[mn]
                        break

                if base_color_node:
                    mix_node = nodes.new(type='ShaderNodeMix')
                    mix_node.data_type = 'RGBA'
                    mix_node.blend_type = 'MULTIPLY'
                    mix_node.location = (100, 200)
                    mix_node.inputs['Factor'].default_value = 0.8

                    for link in list(base_color_node.outputs['Color'].links):
                        if link.to_socket == principled.inputs['Base Color']:
                            links.remove(link)

                    links.new(base_color_node.outputs['Color'], mix_node.inputs[6])
                    links.new(texture_nodes['ao'].outputs['Color'], mix_node.inputs[7])
                    links.new(mix_node.outputs[2], principled.inputs['Base Color'])
                    print("Connected AO to mix with Base Color")

            # CRITICAL: Make sure to clear all existing materials from the object
            while len(obj.data.materials) > 0:
                obj.data.materials.pop(index=0)

            # Assign the new material to the object
            obj.data.materials.append(new_mat)

            # CRITICAL: Make the object active and select it
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)

            # CRITICAL: Force Blender to update the material
            bpy.context.view_layer.update()

            # Get the list of texture maps
            texture_maps = list(texture_images.keys())

            # Get info about texture nodes for debugging
            material_info = {
                "name": new_mat.name,
                "has_nodes": new_mat.use_nodes,
                "node_count": len(new_mat.node_tree.nodes),
                "texture_nodes": []
            }

            for node in new_mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    connections = []
                    for output in node.outputs:
                        for link in output.links:
                            connections.append(f"{output.name} → {link.to_node.name}.{link.to_socket.name}")

                    material_info["texture_nodes"].append({
                        "name": node.name,
                        "image": node.image.name,
                        "colorspace": node.image.colorspace_settings.name,
                        "connections": connections
                    })

            return {
                "success": True,
                "message": f"Created new material and applied texture {texture_id} to {object_name}",
                "material": new_mat.name,
                "maps": texture_maps,
                "material_info": material_info
            }

        except Exception as e:
            print(f"Error in set_texture: {str(e)}")
            traceback.print_exc()
            return {"error": f"Failed to apply texture: {str(e)}"}

    #region Local Asset Library
    @staticmethod
    def _default_managed_asset_library_root():
        documents_root = os.path.abspath(os.path.expanduser("~/Documents"))
        if os.path.isdir(documents_root):
            return os.path.join(documents_root, "ViperMeshAssets")
        return os.path.join(os.path.abspath(os.path.expanduser("~")), "ViperMeshAssets")

    @staticmethod
    def _default_managed_asset_catalog_path():
        return os.path.join(
            BlenderMCPServer._default_managed_asset_library_root(),
            "catalog",
            "assets.json"
        )

    @staticmethod
    def _default_managed_asset_cache_root():
        return os.path.join(
            BlenderMCPServer._default_managed_asset_library_root(),
            "cache"
        )

    @staticmethod
    def _resolve_local_asset_catalog_path():
        scene = bpy.context.scene
        raw_path = (
            getattr(scene, "blendermcp_local_asset_catalog_path", "")
            or os.environ.get("VIPERMESH_LOCAL_ASSET_CATALOG", "")
            or BlenderMCPServer._default_managed_asset_catalog_path()
        )
        if not raw_path:
            return None
        return os.path.abspath(os.path.expanduser(raw_path))

    @staticmethod
    def _resolve_local_asset_library_root(catalog=None):
        scene = bpy.context.scene
        raw_root = (
            getattr(scene, "blendermcp_local_asset_library_root", "")
            or os.environ.get("VIPERMESH_LOCAL_ASSET_LIBRARY_ROOT", "")
            or BlenderMCPServer._default_managed_asset_library_root()
        )
        if raw_root:
            return os.path.abspath(os.path.expanduser(raw_root))
        if isinstance(catalog, dict) and catalog.get("library_root"):
            return os.path.abspath(os.path.expanduser(catalog["library_root"]))
        catalog_path = BlenderMCPServer._resolve_local_asset_catalog_path()
        if catalog_path:
            return os.path.dirname(catalog_path)
        return None

    @staticmethod
    def _load_local_asset_catalog():
        catalog_path = BlenderMCPServer._resolve_local_asset_catalog_path()
        if not catalog_path:
            return None, None, "Local asset catalog path is not configured."
        if not os.path.isfile(catalog_path):
            return None, catalog_path, f"Local asset catalog was not found at: {catalog_path}"

        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                catalog = json.load(f)
        except json.JSONDecodeError as e:
            return None, catalog_path, f"Local asset catalog is not valid JSON: {str(e)}"
        except Exception as e:
            return None, catalog_path, f"Failed to read local asset catalog: {str(e)}"

        assets = catalog.get("assets")
        if not isinstance(assets, list):
            return None, catalog_path, "Local asset catalog must contain an 'assets' array."

        return catalog, catalog_path, None

    @staticmethod
    def _asset_text_fields(asset):
        values = [
            asset.get("id", ""),
            asset.get("name", ""),
            asset.get("category", ""),
            asset.get("style", ""),
            asset.get("description", ""),
            asset.get("license", ""),
            asset.get("source", ""),
            " ".join(asset.get("tags", [])),
        ]
        return " ".join(str(v) for v in values if v).lower()

    @staticmethod
    def _score_local_asset(asset, query_terms):
        searchable = BlenderMCPServer._asset_text_fields(asset)
        tags = [str(tag).lower() for tag in asset.get("tags", [])]
        name = str(asset.get("name", "")).lower()
        category = str(asset.get("category", "")).lower()
        style = str(asset.get("style", "")).lower()
        description = str(asset.get("description", "")).lower()

        score = float(asset.get("quality_score", 0.0) or 0.0)
        matched_terms = 0
        for term in query_terms:
            if term not in searchable:
                continue
            matched_terms += 1
            if term in name:
                score += 10
            elif term in tags:
                score += 6
            elif term in category or term in style:
                score += 4
            elif term in description:
                score += 2
            else:
                score += 1
        if query_terms and matched_terms == 0:
            return None
        if query_terms:
            score += matched_terms / max(1, len(query_terms))
        return score

    @staticmethod
    def _resolve_local_asset_file_path(catalog, catalog_path, asset):
        import_spec = asset.get("import_spec") or {}
        file_path = import_spec.get("file_path") or asset.get("file_path")
        if not file_path:
            return None, import_spec, "Asset is missing import_spec.file_path"

        file_path = os.path.expanduser(file_path)
        if os.path.isabs(file_path):
            return os.path.abspath(file_path), import_spec, None

        library_root = BlenderMCPServer._resolve_local_asset_library_root(catalog)
        base_dir = library_root or os.path.dirname(catalog_path)
        return os.path.abspath(os.path.join(base_dir, file_path)), import_spec, None

    def get_local_asset_library_status(self):
        """Get the current status of the local curated asset library."""
        enabled = bpy.context.scene.blendermcp_use_local_assets
        catalog, catalog_path, error = self._load_local_asset_catalog()
        library_root = self._resolve_local_asset_library_root(catalog)

        if not enabled:
            return {
                "enabled": False,
                "message": """ViperMesh Assets are currently disabled. To enable them:
                            1. In the 3D Viewport, find the ViperMesh panel in the sidebar (press N if hidden)
                            2. Check the 'ViperMesh Assets' checkbox
                            3. Keep the managed defaults, or override them with your own catalog and library root
                            4. Restart the connection to ViperMesh""",
                "catalog_path": catalog_path,
                "library_root": library_root,
                "managed_cache_root": self._default_managed_asset_cache_root(),
            }

        if error:
            return {
                "enabled": False,
                "message": error,
                "catalog_path": catalog_path,
                "library_root": library_root,
                "managed_cache_root": self._default_managed_asset_cache_root(),
            }

        return {
            "enabled": True,
            "message": "ViperMesh Assets are enabled and ready to use.",
            "catalog_path": catalog_path,
            "library_root": library_root,
            "managed_cache_root": self._default_managed_asset_cache_root(),
            "asset_count": len(catalog.get("assets", [])),
            "catalog_version": catalog.get("version"),
        }

    def search_local_assets(self, query=None, category=None, tags=None, style=None, limit=10):
        """Search the local curated asset manifest."""
        catalog, catalog_path, error = self._load_local_asset_catalog()
        if error:
            return {"error": error}

        query_terms = [term.strip().lower() for term in str(query or "").split() if term.strip()]
        requested_category = str(category or "").strip().lower()
        requested_style = str(style or "").strip().lower()
        requested_tags = [tag.strip().lower() for tag in str(tags or "").split(",") if tag.strip()]

        matches = []
        for asset in catalog.get("assets", []):
            asset_category = str(asset.get("category", "")).lower()
            asset_style = str(asset.get("style", "")).lower()
            asset_tags = [str(tag).lower() for tag in asset.get("tags", [])]

            if requested_category and requested_category != asset_category and requested_category not in asset_tags:
                continue
            if requested_style and requested_style != asset_style:
                continue
            if requested_tags and not all(tag in asset_tags for tag in requested_tags):
                continue

            score = self._score_local_asset(asset, query_terms)
            if query_terms and score is None:
                continue
            if score is None:
                score = float(asset.get("quality_score", 0.0) or 0.0)

            matches.append({
                "id": asset.get("id"),
                "name": asset.get("name"),
                "category": asset.get("category"),
                "style": asset.get("style"),
                "tags": asset.get("tags", []),
                "description": asset.get("description", ""),
                "license": asset.get("license", ""),
                "source": asset.get("source", ""),
                "preview_path": asset.get("preview_path"),
                "quality_score": asset.get("quality_score"),
                "dimensions_m": asset.get("dimensions_m"),
                "score": round(score, 3),
            })

        matches.sort(key=lambda item: item.get("score", 0), reverse=True)
        return {
            "success": True,
            "catalog_path": catalog_path,
            "result_count": len(matches),
            "assets": matches[:max(1, int(limit or 10))],
        }

    def import_local_asset(
        self,
        asset_id,
        link=False,
        create_root=False,
        root_name=None,
        location=None,
        rotation=None,
        scale=None,
        pivot="BOTTOM_CENTER",
        compact=False,
    ):
        """Import and optionally place a curated asset as one managed hierarchy."""
        pivot_mode = str(pivot or "BOTTOM_CENTER").strip().upper()
        if pivot_mode not in {"BOTTOM_CENTER", "CENTER", "WORLD_ORIGIN"}:
            return {"error": "pivot must be BOTTOM_CENTER, CENTER, or WORLD_ORIGIN"}
        if location is not None and (not isinstance(location, (list, tuple)) or len(location) != 3):
            return {"error": "location must contain three values"}
        if rotation is not None and (not isinstance(rotation, (list, tuple)) or len(rotation) != 3):
            return {"error": "rotation must contain three degree values"}
        if scale is not None and not (
            isinstance(scale, (int, float)) or (isinstance(scale, (list, tuple)) and len(scale) == 3)
        ):
            return {"error": "scale must be one number or three values"}
        requested_placement = any(value is not None for value in (root_name, location, rotation, scale))
        if link and (create_root or requested_placement):
            return {"error": "Managed asset placement requires link=false so the imported hierarchy is editable"}

        catalog, catalog_path, error = self._load_local_asset_catalog()
        if error:
            return {"error": error}

        asset = next((item for item in catalog.get("assets", []) if item.get("id") == asset_id), None)
        if asset is None:
            return {"error": f"Asset '{asset_id}' was not found in the local asset catalog."}

        resolved_path, import_spec, path_error = self._resolve_local_asset_file_path(catalog, catalog_path, asset)
        if path_error:
            return {"error": path_error}
        if not os.path.isfile(resolved_path):
            return {"error": f"Asset file was not found at: {resolved_path}"}

        format_hint = str(import_spec.get("format") or os.path.splitext(resolved_path)[1].lstrip(".")).lower()
        if format_hint == "gltf":
            format_hint = "glb"

        existing_objects = set(obj.name for obj in bpy.data.objects)
        existing_collections = set(coll.name for coll in bpy.data.collections)

        try:
            if format_hint == "glb":
                bpy.ops.import_scene.gltf(filepath=resolved_path)
            elif format_hint == "fbx":
                bpy.ops.import_scene.fbx(filepath=resolved_path)
            elif format_hint == "obj":
                bpy.ops.import_scene.obj(filepath=resolved_path)
            elif format_hint == "blend":
                append_type = str(import_spec.get("append_type", "collections")).lower()
                if append_type == "collection":
                    append_type = "collections"
                if append_type == "object":
                    append_type = "objects"
                if append_type not in {"collections", "objects"}:
                    return {"error": f"Unsupported blend append_type: {append_type}"}

                requested_names = import_spec.get("asset_names") or []
                with bpy.data.libraries.load(resolved_path, link=link) as (data_from, data_to):
                    available_names = list(getattr(data_from, append_type))
                    if not requested_names:
                        requested_names = available_names[:1]
                    valid_names = [name for name in requested_names if name in available_names]
                    if not valid_names:
                        return {"error": f"No importable {append_type} matched the manifest entry for '{asset_id}'."}

                    if append_type == "collections":
                        data_to.collections = valid_names
                    else:
                        data_to.objects = valid_names

                if append_type == "collections":
                    scene_children = {child.name for child in bpy.context.scene.collection.children}
                    for coll in bpy.data.collections:
                        if coll.name not in existing_collections and coll.name not in scene_children:
                            bpy.context.scene.collection.children.link(coll)
                else:
                    current_objects = {obj.name for obj in bpy.context.collection.objects}
                    for obj in bpy.data.objects:
                        if obj.name not in existing_objects and obj.name not in current_objects:
                            bpy.context.collection.objects.link(obj)
            else:
                return {"error": f"Unsupported local asset format: {format_hint}"}

            bpy.context.view_layer.update()

            imported_object_refs = [obj for obj in bpy.data.objects if obj.name not in existing_objects]
            imported_objects = [obj.name for obj in imported_object_refs]
            imported_collections = [coll.name for coll in bpy.data.collections if coll.name not in existing_collections]

            managed_root = None
            if create_root or requested_placement:
                bound_points = []
                for obj in imported_object_refs:
                    if obj.type in {"MESH", "CURVE", "SURFACE", "FONT", "META"}:
                        bound_points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)

                if bound_points and pivot_mode != "WORLD_ORIGIN":
                    minimum = Vector((
                        min(point.x for point in bound_points),
                        min(point.y for point in bound_points),
                        min(point.z for point in bound_points),
                    ))
                    maximum = Vector((
                        max(point.x for point in bound_points),
                        max(point.y for point in bound_points),
                        max(point.z for point in bound_points),
                    ))
                    pivot_location = (minimum + maximum) * 0.5
                    if pivot_mode == "BOTTOM_CENTER":
                        pivot_location.z = minimum.z
                else:
                    pivot_location = Vector((0.0, 0.0, 0.0))

                managed_root = bpy.data.objects.new(root_name or f"Asset_{asset.get('name') or 'Root'}", None)
                managed_root.empty_display_type = "PLAIN_AXES"
                managed_root.location = pivot_location
                bpy.context.collection.objects.link(managed_root)

                imported_set = set(imported_object_refs)
                top_level_objects = [obj for obj in imported_object_refs if obj.parent not in imported_set]
                for obj in top_level_objects:
                    world_matrix = obj.matrix_world.copy()
                    obj.parent = managed_root
                    obj.matrix_world = world_matrix

                if rotation is not None:
                    managed_root.rotation_euler = tuple(math.radians(float(value)) for value in rotation)
                if scale is not None:
                    if isinstance(scale, (int, float)):
                        managed_root.scale = (float(scale),) * 3
                    else:
                        managed_root.scale = tuple(float(value) for value in scale)
                if location is not None:
                    managed_root.location = tuple(float(value) for value in location)

                bpy.context.view_layer.update()

            response = {
                "success": True,
                "message": f"Imported local asset '{asset_id}'",
                "asset": {
                    "id": asset.get("id"),
                    "name": asset.get("name"),
                    "category": asset.get("category"),
                    "style": asset.get("style"),
                    "license": asset.get("license"),
                    "source": asset.get("source"),
                },
                "file_path": resolved_path,
                "format": format_hint,
                "imported_objects": imported_objects,
                "imported_collections": imported_collections,
                "imported_object_count": len(imported_objects),
                "imported_collection_count": len(imported_collections),
                "root_name": managed_root.name if managed_root else None,
                "placement": {
                    "location": [round(value, 6) for value in managed_root.location],
                    "rotation_degrees": [round(math.degrees(value), 6) for value in managed_root.rotation_euler],
                    "scale": [round(value, 6) for value in managed_root.scale],
                    "pivot": pivot_mode,
                } if managed_root else None,
            }
            if compact:
                response.pop("file_path", None)
                response.pop("imported_objects", None)
                response.pop("imported_collections", None)
            return response
        except Exception as e:
            traceback.print_exc()
            return {"error": f"Failed to import local asset: {str(e)}"}
    #endregion

    def get_polyhaven_status(self):
        """Get the current status of PolyHaven integration"""
        enabled = bpy.context.scene.blendermcp_use_polyhaven
        if enabled:
            return {"enabled": True, "message": "PolyHaven integration is enabled and ready to use."}
        else:
            return {
                "enabled": False,
                "message": """PolyHaven integration is currently disabled. To enable it:
                            1. In the 3D Viewport, find the BlenderMCP panel in the sidebar (press N if hidden)
                            2. Check the 'Use assets from Poly Haven' checkbox
                            3. Restart the connection to Claude"""
        }


    #region Sketchfab API
    def get_sketchfab_status(self):
        """Get the current status of Sketchfab integration"""
        enabled = bpy.context.scene.blendermcp_use_sketchfab
        api_key = bpy.context.scene.blendermcp_sketchfab_api_key

        # Test the API key if present
        if api_key:
            try:
                headers = {
                    "Authorization": f"Token {api_key}"
                }

                response = requests.get(
                    "https://api.sketchfab.com/v3/me",
                    headers=headers,
                    timeout=30  # Add timeout of 30 seconds
                )

                if response.status_code == 200:
                    user_data = response.json()
                    username = user_data.get("username", "Unknown user")
                    return {
                        "enabled": True,
                        "message": f"Sketchfab integration is enabled and ready to use. Logged in as: {username}"
                    }
                else:
                    return {
                        "enabled": False,
                        "message": f"Sketchfab API key seems invalid. Status code: {response.status_code}"
                    }
            except requests.exceptions.Timeout:
                return {
                    "enabled": False,
                    "message": "Timeout connecting to Sketchfab API. Check your internet connection."
                }
            except Exception as e:
                return {
                    "enabled": False,
                    "message": f"Error testing Sketchfab API key: {str(e)}"
                }

        if enabled and api_key:
            return {"enabled": True, "message": "Sketchfab integration is enabled and ready to use."}
        elif enabled and not api_key:
            return {
                "enabled": False,
                "message": """Sketchfab integration is currently enabled, but API key is not given. To enable it:
                            1. In the 3D Viewport, find the BlenderMCP panel in the sidebar (press N if hidden)
                            2. Keep the 'Use Sketchfab' checkbox checked
                            3. Enter your Sketchfab API Key
                            4. Restart the connection to Claude"""
            }
        else:
            return {
                "enabled": False,
                "message": """Sketchfab integration is currently disabled. To enable it:
                            1. In the 3D Viewport, find the BlenderMCP panel in the sidebar (press N if hidden)
                            2. Check the 'Use assets from Sketchfab' checkbox
                            3. Enter your Sketchfab API Key
                            4. Restart the connection to Claude"""
            }

    def search_sketchfab_models(self, query, categories=None, count=20, downloadable=True):
        """Search for models on Sketchfab based on query and optional filters"""
        try:
            api_key = bpy.context.scene.blendermcp_sketchfab_api_key
            if not api_key:
                return {"error": "Sketchfab API key is not configured"}

            # Build search parameters with exact fields from Sketchfab API docs
            params = {
                "type": "models",
                "q": query,
                "count": count,
                "downloadable": downloadable,
                "archives_flavours": False
            }

            if categories:
                params["categories"] = categories

            # Make API request to Sketchfab search endpoint
            # The proper format according to Sketchfab API docs for API key auth
            headers = {
                "Authorization": f"Token {api_key}"
            }


            # Use the search endpoint as specified in the API documentation
            response = requests.get(
                "https://api.sketchfab.com/v3/search",
                headers=headers,
                params=params,
                timeout=30  # Add timeout of 30 seconds
            )

            if response.status_code == 401:
                return {"error": "Authentication failed (401). Check your API key."}

            if response.status_code != 200:
                return {"error": f"API request failed with status code {response.status_code}"}

            response_data = response.json()

            # Safety check on the response structure
            if response_data is None:
                return {"error": "Received empty response from Sketchfab API"}

            # Handle 'results' potentially missing from response
            results = response_data.get("results", [])
            if not isinstance(results, list):
                return {"error": f"Unexpected response format from Sketchfab API: {response_data}"}

            return response_data

        except requests.exceptions.Timeout:
            return {"error": "Request timed out. Check your internet connection."}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON response from Sketchfab API: {str(e)}"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def download_sketchfab_model(self, uid):
        """Download a model from Sketchfab by its UID"""
        try:
            api_key = bpy.context.scene.blendermcp_sketchfab_api_key
            if not api_key:
                return {"error": "Sketchfab API key is not configured"}

            # Use proper authorization header for API key auth
            headers = {
                "Authorization": f"Token {api_key}"
            }

            # Request download URL using the exact endpoint from the documentation
            download_endpoint = f"https://api.sketchfab.com/v3/models/{uid}/download"

            response = requests.get(
                download_endpoint,
                headers=headers,
                timeout=30  # Add timeout of 30 seconds
            )

            if response.status_code == 401:
                return {"error": "Authentication failed (401). Check your API key."}

            if response.status_code != 200:
                return {"error": f"Download request failed with status code {response.status_code}"}

            data = response.json()

            # Safety check for None data
            if data is None:
                return {"error": "Received empty response from Sketchfab API for download request"}

            # Extract download URL with safety checks
            gltf_data = data.get("gltf")
            if not gltf_data:
                return {"error": "No gltf download URL available for this model. Response: " + str(data)}

            download_url = gltf_data.get("url")
            if not download_url:
                return {"error": "No download URL available for this model. Make sure the model is downloadable and you have access."}

            # Download the model (already has timeout)
            model_response = requests.get(download_url, timeout=60)  # 60 second timeout

            if model_response.status_code != 200:
                return {"error": f"Model download failed with status code {model_response.status_code}"}

            # Save to temporary file
            temp_dir = tempfile.mkdtemp()
            zip_file_path = os.path.join(temp_dir, f"{uid}.zip")

            with open(zip_file_path, "wb") as f:
                f.write(model_response.content)

            # Extract the zip file with enhanced security
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # More secure zip slip prevention
                for file_info in zip_ref.infolist():
                    # Get the path of the file
                    file_path = file_info.filename

                    # Convert directory separators to the current OS style
                    # This handles both / and \ in zip entries
                    target_path = os.path.join(temp_dir, os.path.normpath(file_path))

                    # Get absolute paths for comparison
                    abs_temp_dir = os.path.abspath(temp_dir)
                    abs_target_path = os.path.abspath(target_path)

                    # Ensure the normalized path doesn't escape the target directory
                    if not abs_target_path.startswith(abs_temp_dir):
                        with suppress(Exception):
                            shutil.rmtree(temp_dir)
                        return {"error": "Security issue: Zip contains files with path traversal attempt"}

                    # Additional explicit check for directory traversal
                    if ".." in file_path:
                        with suppress(Exception):
                            shutil.rmtree(temp_dir)
                        return {"error": "Security issue: Zip contains files with directory traversal sequence"}

                # If all files passed security checks, extract them
                zip_ref.extractall(temp_dir)

            # Find the main glTF file
            gltf_files = [f for f in os.listdir(temp_dir) if f.endswith('.gltf') or f.endswith('.glb')]

            if not gltf_files:
                with suppress(Exception):
                    shutil.rmtree(temp_dir)
                return {"error": "No glTF file found in the downloaded model"}

            main_file = os.path.join(temp_dir, gltf_files[0])

            # Import the model
            bpy.ops.import_scene.gltf(filepath=main_file)

            # Get the names of imported objects
            imported_objects = [obj.name for obj in bpy.context.selected_objects]

            # Clean up temporary files
            with suppress(Exception):
                shutil.rmtree(temp_dir)

            return {
                "success": True,
                "message": "Model imported successfully",
                "imported_objects": imported_objects
            }

        except requests.exceptions.Timeout:
            return {"error": "Request timed out. Check your internet connection and try again with a simpler model."}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON response from Sketchfab API: {str(e)}"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to download model: {str(e)}"}
    #endregion

# Blender UI Panel
class VIPERMESH_PT_Panel(bpy.types.Panel):
    bl_label = "ViperMesh for Blender"
    bl_idname = "VIPERMESH_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ViperMesh'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Sync scene property from actual server state (survives File → New)
        server = (
            bpy.types.blendermcp_server
            if hasattr(bpy.types, "blendermcp_server")
            else None
        )
        actually_running = (
            server is not None
            and getattr(server, "running", False)
        )
        if scene.blendermcp_server_running != actually_running:
            scene.blendermcp_server_running = actually_running

        version_row = layout.row()
        version_row.enabled = False
        version_row.label(text=f"Addon v{ADDON_VERSION_LABEL}")

        layout.separator()

        box = layout.box()
        row = box.row()
        row.scale_y = 1.5
        active_clients = getattr(server, "active_clients", 0) if server else 0
        last_error = getattr(server, "last_error", "") if server else ""

        if scene.blendermcp_server_running and active_clients:
            row.label(text="Agent connected", icon='LINKED')
        elif scene.blendermcp_server_running:
            row.label(text="Ready for agent", icon='CHECKMARK')
        elif last_error:
            row.label(text="Bridge error", icon='ERROR')
        else:
            row.label(text="Bridge stopped", icon='PAUSE')

        endpoint_row = box.row()
        endpoint_row.enabled = False
        endpoint_row.label(text=f"Local endpoint: 127.0.0.1:{scene.blendermcp_port}")

        if not scene.blendermcp_server_running:
            layout.operator("vipermesh.start_server", text="Start Local Bridge", icon='PLAY')
        else:
            layout.operator("vipermesh.stop_server", text="Stop Local Bridge", icon='PAUSE')

        layout.separator()

        setup_box = layout.box()
        setup_box.prop(
            scene,
            "blendermcp_show_agent_setup",
            text="Agent Setup",
            icon='TRIA_DOWN' if scene.blendermcp_show_agent_setup else 'TRIA_RIGHT',
            emboss=False,
        )
        if scene.blendermcp_show_agent_setup:
            col = setup_box.column(align=True)
            col.label(text="Keep this bridge running for the complete agent session.")
            col.label(text="Configure one persistent vipermesh-blender MCP server.")
            col.label(text="Call bootstrap_vipermesh_session once at startup.")
            col.prop(scene, "blendermcp_port", text="Port")

        asset_box = layout.box()
        asset_box.prop(
            scene,
            "blendermcp_show_asset_sources",
            text="Asset Sources",
            icon='TRIA_DOWN' if scene.blendermcp_show_asset_sources else 'TRIA_RIGHT',
            emboss=False,
        )
        if scene.blendermcp_show_asset_sources:
            asset_box.prop(scene, "blendermcp_use_local_assets", text="ViperMesh Assets")
            col = asset_box.column(align=True)
            col.enabled = scene.blendermcp_use_local_assets
            col.prop(scene, "blendermcp_local_asset_catalog_path", text="Catalog JSON")
            col.prop(scene, "blendermcp_local_asset_library_root", text="Library Root")
            asset_box.prop(scene, "blendermcp_use_polyhaven", text="Poly Haven")
            asset_box.prop(scene, "blendermcp_use_sketchfab", text="Sketchfab")
            col = asset_box.column(align=True)
            col.enabled = scene.blendermcp_use_sketchfab
            col.prop(scene, "blendermcp_sketchfab_api_key", text="API Key")

        diagnostics_box = layout.box()
        diagnostics_box.prop(
            scene,
            "blendermcp_show_diagnostics",
            text="Diagnostics",
            icon='TRIA_DOWN' if scene.blendermcp_show_diagnostics else 'TRIA_RIGHT',
            emboss=False,
        )
        if scene.blendermcp_show_diagnostics:
            diagnostics_box.label(text=f"Active agent connections: {active_clients}")
            diagnostics_box.label(text="Transport: loopback TCP")
            if last_error:
                error_row = diagnostics_box.row()
                error_row.alert = True
                error_row.label(text=f"Last error: {last_error[:120]}", icon='ERROR')

# Operator to start the server
class VIPERMESH_OT_StartServer(bpy.types.Operator):
    bl_idname = "vipermesh.start_server"
    bl_label = "Start Local Bridge"
    bl_description = "Start the loopback bridge used by one persistent MCP agent session"

    def execute(self, context):
        scene = context.scene

        # Create a new server instance
        if not hasattr(bpy.types, "blendermcp_server") or not bpy.types.blendermcp_server:
            bpy.types.blendermcp_server = BlenderMCPServer(port=scene.blendermcp_port)

        # Start the server
        bpy.types.blendermcp_server.start()
        scene.blendermcp_server_running = bpy.types.blendermcp_server.running

        return {'FINISHED'}

# Operator to stop the server
class VIPERMESH_OT_StopServer(bpy.types.Operator):
    bl_idname = "vipermesh.stop_server"
    bl_label = "Stop Local Bridge"
    bl_description = "Stop the loopback bridge and close active agent connections"

    def execute(self, context):
        scene = context.scene

        # Stop the server if it exists
        if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
            bpy.types.blendermcp_server.stop()
            del bpy.types.blendermcp_server

        scene.blendermcp_server_running = False

        return {'FINISHED'}

@bpy.app.handlers.persistent
def _sync_server_status(_dummy=None):
    """Re-sync blendermcp_server_running after file load (File → New / Open)"""
    actually_running = (
        hasattr(bpy.types, "blendermcp_server")
        and bpy.types.blendermcp_server is not None
        and getattr(bpy.types.blendermcp_server, "running", False)
    )
    for scene in bpy.data.scenes:
        scene.blendermcp_server_running = actually_running


# Registration functions
def register():
    bpy.types.Scene.blendermcp_port = IntProperty(
        name="Port",
        description="Port for the BlenderMCP server",
        default=9876,
        min=1024,
        max=65535
    )

    bpy.types.Scene.blendermcp_server_running = bpy.props.BoolProperty(
        name="Server Running",
        default=False
    )

    bpy.types.Scene.blendermcp_show_agent_setup = bpy.props.BoolProperty(
        name="Show Agent Setup",
        default=True
    )

    bpy.types.Scene.blendermcp_show_asset_sources = bpy.props.BoolProperty(
        name="Show Asset Sources",
        default=False
    )

    bpy.types.Scene.blendermcp_show_diagnostics = bpy.props.BoolProperty(
        name="Show Diagnostics",
        default=False
    )

    bpy.types.Scene.blendermcp_use_local_assets = bpy.props.BoolProperty(
        name="Use ViperMesh Assets",
        description="Enable curated ViperMesh assets from a JSON manifest",
        default=False
    )

    bpy.types.Scene.blendermcp_local_asset_catalog_path = bpy.props.StringProperty(
        name="Local Asset Catalog",
        description="Path to the ViperMesh local asset catalog JSON manifest",
        default=(
            os.environ.get("VIPERMESH_LOCAL_ASSET_CATALOG", "")
            or BlenderMCPServer._default_managed_asset_catalog_path()
        ),
        subtype="FILE_PATH"
    )

    bpy.types.Scene.blendermcp_local_asset_library_root = bpy.props.StringProperty(
        name="Local Asset Library Root",
        description="Optional root folder used to resolve relative asset paths from the catalog",
        default=(
            os.environ.get("VIPERMESH_LOCAL_ASSET_LIBRARY_ROOT", "")
            or BlenderMCPServer._default_managed_asset_library_root()
        ),
        subtype="DIR_PATH"
    )

    bpy.types.Scene.blendermcp_use_polyhaven = bpy.props.BoolProperty(
        name="Use Poly Haven",
        description="Enable Poly Haven asset integration",
        default=False
    )

    bpy.types.Scene.blendermcp_use_sketchfab = bpy.props.BoolProperty(
        name="Use Sketchfab",
        description="Enable Sketchfab asset integration",
        default=False
    )

    bpy.types.Scene.blendermcp_sketchfab_api_key = bpy.props.StringProperty(
        name="Sketchfab API Key",
        subtype="PASSWORD",
        description="API Key provided by Sketchfab",
        default=""
    )

    bpy.utils.register_class(VIPERMESH_PT_Panel)
    bpy.utils.register_class(VIPERMESH_OT_StartServer)
    bpy.utils.register_class(VIPERMESH_OT_StopServer)

    # Re-sync server status after File → New / File → Open
    bpy.app.handlers.load_post.append(_sync_server_status)

    print("ViperMesh Blender addon registered")
    if os.environ.get("VIPERMESH_BRIDGE_AUTOSTART", "").lower() in {"1", "true", "yes"}:
        port = int(os.environ.get("VIPERMESH_BRIDGE_PORT", "9876"))
        if not 1024 <= port <= 65535:
            raise ValueError("VIPERMESH_BRIDGE_PORT must be between 1024 and 65535")
        bpy.context.scene.blendermcp_port = port
        bpy.ops.vipermesh.start_server()

def unregister():
    # Stop the server if it's running
    if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
        bpy.types.blendermcp_server.stop()
        del bpy.types.blendermcp_server

    for cls in (VIPERMESH_OT_StopServer, VIPERMESH_OT_StartServer, VIPERMESH_PT_Panel):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass

    # Remove load_post handler
    if _sync_server_status in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_sync_server_status)

    props = [
        "blendermcp_port", "blendermcp_server_running",
        "blendermcp_show_agent_setup", "blendermcp_show_asset_sources",
        "blendermcp_show_diagnostics", "blendermcp_use_local_assets",
        "blendermcp_local_asset_catalog_path", "blendermcp_local_asset_library_root",
        "blendermcp_use_polyhaven",
        "blendermcp_use_sketchfab", "blendermcp_sketchfab_api_key",
    ]
    for prop in props:
        try:
            delattr(bpy.types.Scene, prop)
        except AttributeError:
            pass

    print("ViperMesh Blender addon unregistered")

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="ViperMesh local background Blender bridge")
    parser.add_argument("--serve", action="store_true", help="Run the main-thread background service loop")
    parser.add_argument("--port", type=int, default=int(os.environ.get("VIPERMESH_BRIDGE_PORT", "9876")))
    parser.add_argument("--idle-timeout", type=float, default=0, help="Stop after this many idle seconds; 0 disables")
    parser.add_argument("--max-runtime", type=float, default=0, help="Stop between commands after this many seconds; 0 disables")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if not 1024 <= args.port <= 65535 or not all(math.isfinite(value) and value >= 0 for value in (args.idle_timeout, args.max_runtime)):
        parser.error("Use a port between 1024 and 65535 and nonnegative timeouts")
    register()
    should_serve = args.serve or os.environ.get("VIPERMESH_BRIDGE_AUTOSTART", "").lower() in {"1", "true", "yes"}
    if should_serve and bpy.app.background:
        try:
            bpy.context.scene.blendermcp_port = args.port
            existing = getattr(bpy.types, "blendermcp_server", None)
            if existing and existing.port != args.port:
                bpy.ops.vipermesh.stop_server()
            bpy.ops.vipermesh.start_server()
            bridge = bpy.types.blendermcp_server
            if not bridge.running:
                raise RuntimeError(bridge.last_error or "Unable to start bridge")
            print(json.dumps({"vipermesh_headless_ready": True, "host": bridge.host, "port": bridge.port}), flush=True)
            bridge.serve_headless(args.idle_timeout, args.max_runtime)
        except KeyboardInterrupt:
            pass
        finally:
            unregister()

