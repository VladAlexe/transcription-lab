"""What has to be true before a tag is pushed.

A release build runs on a machine that has nothing on it. Everything here exists to catch,
here rather than in CI or in a stranger's Downloads folder, the ways that can go wrong: a
dependency that only exists on the developer's machine, a version that disagrees with its
tag, an icon that was never regenerated, an FFmpeg that is not actually beside the exe.
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def pathlib_read(module) -> str:
    return Path(module.__file__).read_text(encoding="utf-8")
WORKFLOW = ROOT / ".github" / "workflows" / "windows-build.yml"
SHIPPED_EXCLUDED = {".venv", "build", "tests", "screenshots", "__pycache__"}
# Imported only by tools_make_icon.py, which is a development tool and is excluded from
# the package; it must not become a runtime dependency by accident.
DEV_ONLY_MODULES = {"PIL"}
DISTRIBUTION = {"flet": "flet", "flet_audio": "flet-audio", "docx": "python-docx",
                "openai": "openai"}


def shipped_modules() -> list[Path]:
    return [path for path in ROOT.rglob("*.py")
            if not any(part in SHIPPED_EXCLUDED for part in path.parts)
            and path.name != "tools_make_icon.py"]


def imports_of(paths: list[Path]) -> set[str]:
    found: set[str] = set()
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                found |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module.split(".")[0])
    return found


def requirement_pins(name: str = "requirements.txt") -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if "==" in line:
            package, version = line.split("==", 1)
            pins[package.strip()] = version.strip()
    return pins


class DependencyTests(unittest.TestCase):
    def test_every_third_party_import_is_pinned(self) -> None:
        local = {path.stem for path in ROOT.glob("*.py")} | {"components", "views", "providers"}
        third_party = (imports_of(shipped_modules()) - set(sys.stdlib_module_names)
                       - local - {"__future__"})
        pins = requirement_pins()
        missing = sorted(module for module in third_party
                         if DISTRIBUTION.get(module, module) not in pins)
        self.assertEqual(missing, [], f"the built exe would need {missing} from nowhere")

    def test_the_four_the_brief_names_are_all_there(self) -> None:
        pins = requirement_pins()
        for package in ("flet", "flet-audio", "python-docx", "openai"):
            self.assertIn(package, pins, f"{package} is not pinned")

    def test_nothing_is_pinned_by_range(self) -> None:
        """A release has to be reproducible: the version CI ships is the version tested."""
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if not line:
                continue
            self.assertRegex(line, r"^[A-Za-z0-9_.\-]+==[0-9][0-9A-Za-z.\-]*$",
                             f"{line!r} is not an exact pin")

    def test_development_tools_stay_out_of_the_runtime_requirements(self) -> None:
        self.assertNotIn("pillow", {name.lower() for name in requirement_pins()},
                         "Pillow is only used by tools_make_icon.py")
        self.assertIn("pillow", {name.lower() for name in requirement_pins("requirements-dev.txt")})

    def test_no_shipped_module_imports_a_development_only_package(self) -> None:
        leaked = imports_of(shipped_modules()) & DEV_ONLY_MODULES
        self.assertEqual(leaked, set(), f"{leaked} is not installed by the release workflow")


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        # PyYAML reads the bare key `on:` as the boolean True.
        cls.triggers = cls.data[True] if True in cls.data else cls.data["on"]
        cls.job = cls.data["jobs"]["build"]
        cls.steps = cls.job["steps"]
        cls.script = "\n".join(str(step.get("run", "")) for step in cls.steps)

    def test_it_fires_on_a_version_tag(self) -> None:
        self.assertIn("push", self.triggers)
        self.assertEqual(self.triggers["push"]["tags"], ["v*"])

    def test_it_runs_where_the_cpp_toolchain_is(self) -> None:
        self.assertEqual(self.job["runs-on"], "windows-latest")

    def test_it_installs_the_pinned_requirements(self) -> None:
        self.assertIn("pip install -r requirements.txt", self.script)
        self.assertNotIn("requirements-dev.txt", self.script.replace("requirements-dev.txt\n", "", 0)
                         .split("--exclude")[0], "dev tools must not be installed")

    def test_it_proves_flet_audio_is_importable_before_building(self) -> None:
        self.assertIn("import flet, flet_audio, docx, openai", self.script)

    def test_it_runs_the_tests_before_building(self) -> None:
        names = [step.get("name", "") for step in self.steps]
        self.assertLess(names.index("Run tests"), names.index("Build Windows application"))

    def test_it_builds_a_windows_application(self) -> None:
        self.assertIn("flet build windows", self.script)

    def test_it_checks_ffmpeg_landed_in_the_distribution(self) -> None:
        self.assertIn("ffmpeg.exe", self.script)
        self.assertIn("ffprobe.exe", self.script)
        self.assertIn("LICENSE-FFMPEG.txt", self.script)
        self.assertIn(r"build\windows", self.script)

    def test_it_fetches_ffmpeg_instead_of_cloning_it(self) -> None:
        """The binaries are not in the repository, so the build has to go and get them."""
        self.assertIn("python tools_fetch_ffmpeg.py", self.script)
        self.assertIn("5MB", self.script, "a truncated download must not become a release")

    def test_it_never_packages_the_repository_into_the_application(self) -> None:
        """`.git` is the whole history — LFS objects, branch names, anything ever committed.

        Packaged, it both bloats the download and hands every user a copy of the repository.
        `.flet` is a build cache that has no business inside a shipped app either.
        """
        build = [step for step in self.steps if "flet build windows" in str(step.get("run", ""))][0]
        excluded = str(build["run"]).split("--exclude", 1)[1].split("--project", 1)[0]
        for directory in (".git", ".flet", ".venv", "build", "tests", "__pycache__"):
            with self.subTest(directory=directory):
                self.assertIn(directory, excluded)

    def test_it_does_not_ask_git_lfs_for_anything(self) -> None:
        """Nothing large is tracked any more, and an LFS fetch would only cost bandwidth."""
        checkout = [step for step in self.steps
                    if str(step.get("uses", "")).startswith("actions/checkout")][0]
        self.assertNotEqual((checkout.get("with") or {}).get("lfs"), True)
        self.assertNotIn("git lfs pull", self.script)

    def test_the_ffmpeg_version_is_declared_in_exactly_one_place(self) -> None:
        import tools_fetch_ffmpeg
        self.assertEqual(self.data["env"]["FFMPEG_RELEASE"], tools_fetch_ffmpeg.VERSION,
                         "the workflow and the fetch tool disagree about which build ships")

    def test_it_unlocks_the_symlinks_the_flutter_build_needs(self) -> None:
        """Without Developer Mode the build stops before MSVC is ever invoked."""
        self.assertIn("AllowDevelopmentWithoutDevLicense", self.script)

    def test_it_attaches_the_archive_to_the_release(self) -> None:
        release = [step for step in self.steps
                   if str(step.get("uses", "")).startswith("softprops/action-gh-release")]
        self.assertEqual(len(release), 1)
        self.assertIn("refs/tags/v", str(release[0]["if"]),
                      "the release only publishes for a version tag")
        self.assertTrue(str(release[0]["with"]["files"]).endswith(".zip"))

    def test_it_may_write_the_release(self) -> None:
        self.assertEqual(self.data["permissions"]["contents"], "write")

    def test_the_workflow_version_matches_the_application(self) -> None:
        import document_export
        self.assertEqual(self.data["env"]["APP_VERSION"], document_export.APP_VERSION,
                         "bump both together, or a tagged build fails its own check")

    def test_it_refuses_a_tag_that_disagrees_with_the_version(self) -> None:
        self.assertIn("does not match APP_VERSION", self.script)


class PackagingTests(unittest.TestCase):
    def test_every_icon_the_build_needs_is_committed(self) -> None:
        for name in ("icon.png", "icon.ico", "icon_windows.png", "icon.svg"):
            with self.subTest(icon=name):
                path = ROOT / "assets" / name
                self.assertTrue(path.is_file(), f"assets/{name} is missing")
                self.assertGreater(path.stat().st_size, 1000)

    def test_the_windows_icon_is_unambiguous(self) -> None:
        """`flet build` globs assets/icon.* and takes the first match. A dedicated
        icon_windows.png removes the chance of it picking the .svg it cannot decode."""
        self.assertTrue((ROOT / "assets" / "icon_windows.png").is_file())

    def test_the_provenance_note_is_committed_even_though_the_binaries_are_not(self) -> None:
        note = (ROOT / "assets" / "bin" / "windows" / "SOURCE-FFMPEG.txt").read_text(encoding="utf-8")
        self.assertIn("essentials_build", note)
        self.assertIn("tools_fetch_ffmpeg.py", note, "it must say where the binaries come from")

    def test_the_fetch_tool_pins_the_essentials_build_and_takes_the_licence_with_it(self) -> None:
        import tools_fetch_ffmpeg as fetch
        self.assertEqual(fetch.BUILD, "essentials")
        self.assertIn(fetch.VERSION, fetch.URL)
        self.assertIn("essentials_build", fetch.URL)
        self.assertEqual(fetch.WANTED, ("ffmpeg.exe", "ffprobe.exe"))
        self.assertIn("LICENSE-FFMPEG.txt", pathlib_read(fetch),
                      "the licence has to travel with the binaries it covers")

    def test_the_binaries_are_ignored_and_the_provenance_is_not(self) -> None:
        rules = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        for name in ("ffmpeg.exe", "ffprobe.exe", "LICENSE-FFMPEG.txt"):
            with self.subTest(file=name):
                self.assertIn(f"assets/bin/windows/{name}", rules)
                self.assertNotIn(f"!assets/bin/windows/{name}", rules)
        self.assertIn("!assets/bin/windows/SOURCE-FFMPEG.txt", rules)

    def test_whatever_is_in_the_working_tree_is_the_build_we_pin(self) -> None:
        """Skipped on a fresh clone, where the pair has not been fetched yet."""
        import tools_fetch_ffmpeg as fetch
        if not fetch.present():
            self.skipTest("run python tools_fetch_ffmpeg.py first")
        banner = fetch.reported_version(fetch.TARGET / "ffmpeg.exe")
        self.assertIn(f"{fetch.VERSION}-{fetch.BUILD}_build", banner, banner)

    def test_the_app_looks_for_ffmpeg_beside_its_own_executable(self) -> None:
        """On the developer's machine it is found next to the source. On an installed copy
        there is no source tree, so the executable's own directory has to be searched too."""
        import media_tools
        roots = [str(root).replace("\\", "/") for root, _ in media_tools._candidate_roots()]
        executable = str(Path(sys.executable).resolve().parent).replace("\\", "/")
        self.assertTrue(any(root.startswith(executable) for root in roots),
                        f"nothing relative to the executable is searched: {roots}")

    def test_a_missing_ffmpeg_is_reported_rather_than_crashing(self) -> None:
        from models import MediaToolPaths
        self.assertFalse(MediaToolPaths().is_valid, "the app asks the user to locate it")


class FirstRunTests(unittest.TestCase):
    """A stranger double-clicks the exe on a machine that has never seen this app."""

    def test_missing_preferences_are_not_an_error(self) -> None:
        import utils
        original = utils.preferences_path
        try:
            utils.preferences_path = lambda: Path("this-file-does-not-exist.json")
            self.assertEqual(utils.load_preferences(), {})
        finally:
            utils.preferences_path = original

    def test_a_fresh_state_starts_on_the_recording_step_with_no_key(self) -> None:
        from app_state import AppState
        state = AppState()
        self.assertEqual(state.current_workflow_step, 0, "Recording")
        self.assertEqual(state.active_api_key, "")
        self.assertIsNone(state.selected_file_metadata)

    def test_the_first_screen_says_the_key_is_the_user_to_bring(self) -> None:
        import flet as ft
        import layout_audit
        import strings as s
        from app_state import AppState
        from views import recording_view
        noop = lambda *a, **k: None
        screen = recording_view.build(AppState(), noop, noop, noop, noop, lambda *a: None,
                                      960, noop, noop)
        shown = [c.value for c in layout_audit.walk(screen) if isinstance(c, ft.Text) and c.value]
        self.assertIn(s.BYOK_TITLE, shown)
        self.assertIn(s.BYOK_BODY, shown)
        self.assertIn("Settings", s.BYOK_BODY, "it has to name where the provider is chosen")

    def test_the_notice_goes_away_once_a_key_is_entered(self) -> None:
        import flet as ft
        import layout_audit
        import strings as s
        from app_state import AppState
        from views import recording_view
        noop = lambda *a, **k: None
        state = AppState()
        state.set_active_api_key("a-key")
        screen = recording_view.build(state, noop, noop, noop, noop, lambda *a: None, 960,
                                      noop, noop)
        shown = [c.value for c in layout_audit.walk(screen) if isinstance(c, ft.Text) and c.value]
        self.assertNotIn(s.BYOK_TITLE, shown)

    def test_nothing_on_the_first_screen_needs_a_file_that_may_not_exist(self) -> None:
        """A missing asset must degrade, not raise: the mark falls back to a sage tile."""
        from components import brand
        self.assertIsNotNone(brand.mark().error_content)

    def test_the_key_is_never_written_to_the_preferences_file(self) -> None:
        import main
        source = Path(main.__file__).read_text(encoding="utf-8")
        saved = re.search(r"save_preferences\(\{[^}]*\}\)", source, re.S)
        for field in ("api_key", "gladia_api_key", "soniox_api_key", "deepgram_api_key"):
            self.assertNotIn(field, saved.group(0) if saved else "")


if __name__ == "__main__": unittest.main()
