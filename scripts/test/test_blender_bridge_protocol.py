"""Run with ordinary Python; starts only its own disposable Blender process."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import unittest

parser = argparse.ArgumentParser()
parser.add_argument("--blender", required=True)
parser.add_argument("--addon", required=True)
parser.add_argument("--output", required=True)
options, remaining = parser.parse_known_args()
root = Path(options.output).resolve()
root.mkdir(parents=True, exist_ok=False)


class BridgeLifecycle(unittest.TestCase):
    def run_fixture(self, label, extra=None, autostart=False):
        env = {key: value for key, value in os.environ.items()
               if key not in {"VIPERMESH_BRIDGE_AUTOSTART", "VIPERMESH_BRIDGE_PORT"}}
        if autostart:
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                env.update(VIPERMESH_BRIDGE_AUTOSTART="1", VIPERMESH_BRIDGE_PORT=str(probe.getsockname()[1]))
        result = subprocess.run([options.blender, "--background", "--factory-startup",
                                 "--python-exit-code", "1", "--python", str(Path(options.addon).resolve()),
                                 *(["--", *extra] if extra else [])],
                                env=env, capture_output=True, timeout=20)
        (root / f"{label}.log").write_bytes(result.stdout + result.stderr)
        return result, (result.stdout + result.stderr).decode("utf8", errors="replace")

    def test_autostart_is_opt_in(self):
        result, log = self.run_fixture("default-off")
        self.assertEqual(result.returncode, 0, log)
        self.assertNotIn("server started on", log)

    def test_env_autostart_and_runtime_shutdown(self):
        result, log = self.run_fixture("env-autostart", ["--max-runtime", "0.3"], autostart=True)
        self.assertEqual(result.returncode, 0, log)
        self.assertIn('"vipermesh_headless_ready": true', log)
        self.assertIn("server stopped", log)

    def test_invalid_timeout_refused(self):
        result, log = self.run_fixture("invalid-timeout", ["--serve", "--max-runtime", "nan"])
        self.assertNotEqual(result.returncode, 0, log)
        self.assertIn("nonnegative timeouts", log)


class BridgeProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            cls.port = probe.getsockname()[1]
        cls.log = (root / "blender.log").open("w", encoding="utf8")
        cls.process = subprocess.Popen([
            options.blender, "--background", "--factory-startup", "--python-exit-code", "1",
            "--python", str(Path(options.addon).resolve()), "--", "--serve", "--port", str(cls.port),
            "--idle-timeout", "4", "--max-runtime", "90",
        ], stdout=cls.log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if cls.process.poll() is not None:
                raise RuntimeError(f"Background service exited before readiness; see {root / 'blender.log'}")
            try:
                with socket.create_connection(("127.0.0.1", cls.port), timeout=0.2):
                    return
            except OSError:
                time.sleep(0.1)
        cls.process.terminate()
        cls.process.wait(timeout=10)
        raise RuntimeError("Background service never listened")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.process.wait(timeout=12)
            assert cls.process.returncode == 0, (root / "blender.log").read_text(encoding="utf8")
        finally:
            if cls.process.poll() is None:
                cls.process.terminate()
                cls.process.wait(timeout=10)
            cls.log.close()

    def connection(self):
        client = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        client.settimeout(10)
        return client

    def response(self, client):
        received = b""
        while True:
            chunk = client.recv(65536)
            self.assertTrue(chunk, "Connection closed without a response")
            received += chunk
            try:
                return json.loads(received)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

    def call(self, client, kind, params=None, request_id="probe"):
        client.sendall(json.dumps({"type": kind, "params": params or {}, "id": request_id}).encode() + b"\n")
        response = self.response(client)
        self.assertEqual(response.get("id"), request_id)
        return response

    def test_main_thread_mutation_inspection_and_save(self):
        with self.connection() as client:
            self.assertEqual(self.call(client, "get_scene_info")["status"], "success")
            name = "Probe_\u63a2\u9488"
            result = self.call(client, "execute_code", {"code":
                "import bpy,threading\nassert threading.current_thread() is threading.main_thread()\n"
                f"bpy.ops.mesh.primitive_cube_add()\nbpy.context.object.name={name!r}\nprint('MAIN_THREAD_VERIFIED')"})
            self.assertEqual(result["status"], "success", result)
            payload = json.dumps({"type": "get_object_info", "params": {"name": name}}, ensure_ascii=False).encode()
            split = payload.index("\u63a2".encode()) + 1
            client.sendall(payload[:split])
            time.sleep(0.05)
            client.sendall(payload[split:])
            response = self.response(client)
            self.assertEqual(response["status"], "success", response)
            self.assertNotIn("error", response.get("result", {}))
            saved = self.call(client, "save_blend_file", {"filepath": str(root / "probe.blend")})
            self.assertEqual(saved["status"], "success", saved)
            self.assertTrue((root / "probe.blend").is_file())

    def test_shape_errors_and_reuse(self):
        with self.connection() as client:
            bad = self.call(client, "get_scene_info", {"unexpected": True}, 17)
            self.assertEqual(bad["status"], "error")
            self.assertEqual(self.call(client, "get_scene_info")["status"], "success")
            client.sendall(b"[]\n")
            self.assertEqual(self.response(client)["code"], "INVALID_REQUEST")

    def test_pipeline_refusal(self):
        with self.connection() as client:
            command = b'{"type":"get_scene_info","params":{}}'
            client.sendall(command + command)
            self.assertEqual(self.response(client)["code"], "PIPELINING_NOT_SUPPORTED")

    def test_invalid_utf8(self):
        with self.connection() as client:
            client.sendall(b"\xff")
            self.assertEqual(self.response(client)["code"], "INVALID_ENCODING")

    def test_invalid_json_number(self):
        with self.connection() as client:
            client.sendall(b'{"type":"get_scene_info","params":{"invalid":NaN}}')
            self.assertEqual(self.response(client)["code"], "INVALID_JSON")

    def test_viewport_refusal(self):
        with self.connection() as client:
            response = self.call(client, "get_viewport_screenshot")
            self.assertEqual(response["code"], "UI_CONTEXT_REQUIRED")


unittest.main(argv=[__file__, *remaining])
