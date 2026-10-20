"""End-to-end SDK test: own Blender process, isolated profile, one MCP session."""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time

parser = argparse.ArgumentParser()
parser.add_argument("--blender", required=True)
parser.add_argument("--addon", required=True)
parser.add_argument("--server", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--gui", action="store_true")
parser.add_argument("--node", default="node")
args = parser.parse_args()
output = Path(args.output).resolve()
output.mkdir(parents=True, exist_ok=False)
with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
addon = str(Path(args.addon).resolve())
with tempfile.TemporaryDirectory(prefix="vipermesh-test-profile-") as profile:
    env = {**os.environ, "BLENDER_USER_CONFIG": profile,
           "VIPERMESH_BRIDGE_AUTOSTART": "1", "VIPERMESH_BRIDGE_PORT": str(port),
           "VIPERMESH_TEST_ADDON": addon}
    command = [args.blender, "--factory-startup", "--disable-autoexec", "--python-exit-code", "1"]
    if args.gui:
        command += ["--python", str(Path(__file__).with_name("blender_gui_bridge_fixture.py").resolve())]
    else:
        command += ["--background", "--python", addon, "--", "--max-runtime", "120"]
    with (output / "blender.log").open("w", encoding="utf8") as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 45
            while True:
                if process.poll() is not None:
                    raise RuntimeError(f"Blender exited before readiness; see {output / 'blender.log'}")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Blender bridge did not start")
                    time.sleep(0.1)
            subprocess.run([args.node, str(Path(__file__).with_name("test-blender-mcp-runtime.mjs").resolve()),
                            str(Path(args.server).resolve()), str(port), str(output),
                            "gui" if args.gui else "background"], check=True, timeout=100)
        finally:
            # This PID belongs to the disposable fixture, never a user's Blender.
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=15)
print(f"MCP runtime integration passed: {'GUI' if args.gui else 'background'}; {output}")
