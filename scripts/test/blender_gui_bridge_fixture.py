"""Disposable GUI fixture, launched only by test_blender_mcp_runtime.py."""
import os
import runpy
import bpy

addon = runpy.run_path(os.environ["VIPERMESH_TEST_ADDON"], run_name="vipermesh_test_addon")
bpy.context.preferences.view.show_splash = False
addon["register"]()


def quit_fixture():
    addon["unregister"]()
    bpy.ops.wm.quit_blender()


bpy.app.timers.register(quit_fixture, first_interval=120, persistent=True)
