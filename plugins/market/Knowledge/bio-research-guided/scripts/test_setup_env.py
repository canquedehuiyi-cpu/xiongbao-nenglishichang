"""Regression tests for R readiness and installation failures (stdlib only)."""

import argparse
import contextlib
import io
from pathlib import Path
import runpy
import subprocess
import unittest
from unittest import mock


class REnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.module = runpy.run_path(str(Path(__file__).with_name("setup_env.py")))
        self.globals = self.module["collect"].__globals__
        self.packages = ["pheatmap", "ComplexHeatmap"]

    def collect(self, results, *, executable="Rscript", include_r=True):
        replacements = {
            "load_spec": lambda _: (
                Path("/spec"), Path("/spec/requirements.lock"), {"demo": "demo"}, [],
                {"cran": ["pheatmap"], "bioconductor": ["ComplexHeatmap"]},
            ),
            "parse_requirement_names": lambda _: ["demo"],
            "installed_packages": lambda _: {"demo": "1.0"},
            "verify_imports": lambda *_: {"demo": "1.0"},
            "rscript": lambda: executable,
            "r_version": lambda _: "4.6.2",
            "check_r_packages": mock.Mock(return_value=results),
        }
        with mock.patch.dict(self.globals, replacements), mock.patch.object(
            Path, "is_file", return_value=True
        ):
            return self.module["collect"]("foundation", Path("/env"), include_r)

    def test_only_complete_valid_r_results_are_ready(self):
        cases = [
            ({"pheatmap": "1.0.13", "ComplexHeatmap": "2.28.0"}, True),
            ({"pheatmap": "1.0.13", "ComplexHeatmap": "MISSING"}, False),
            ({"pheatmap": "1.0.13"}, False),
            ({}, False),
            (dict.fromkeys(self.packages, "ERROR: Rscript failed"), False),
            (dict.fromkeys(self.packages, ""), False),
            (dict.fromkeys(self.packages, "unexpected output"), False),
        ]
        for results, expected in cases:
            with self.subTest(results=results):
                info = self.collect(results)
                self.assertEqual(info["ready"], expected)
                self.assertEqual(info["r"]["ok"], expected)
                if not expected:
                    self.assertTrue(info["r"]["packages"]["missing"])
                    self.assertFalse(any(
                        value.startswith("ERROR")
                        for value in info["r"]["packages"]["installed"].values()
                    ))

    def test_missing_r_is_not_ready(self):
        self.assertFalse(self.collect({}, executable=None)["ready"])

    def test_skip_r_is_explicit_and_does_not_block_python(self):
        info = self.collect({}, executable=None, include_r=False)
        self.assertTrue(info["ready"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.module["print_report"](info)
        self.assertIn("skipped (--skip-r)", output.getvalue())
        self.assertNotIn("Rscript not found", output.getvalue())

    def test_r_output_requires_a_result_for_every_package(self):
        cases = [
            ("pheatmap\t1.0.13\nComplexHeatmap\t2.28.0\n", True),
            ("pheatmap\t1.0.13\n", False),
            ("", False),
            ("startup text\n", False),
            ("pheatmap\t\nComplexHeatmap\t2.28.0\n", False),
        ]
        for output, expected in cases:
            with self.subTest(output=output), mock.patch.dict(
                self.globals, {"run": mock.Mock(return_value=output)}
            ):
                result = self.module["check_r_packages"](
                    "Rscript", Path("/env/R/library"), self.packages
                )
                self.assertEqual(set(result), set(self.packages))
                self.assertEqual(all(not v.startswith("ERROR") for v in result.values()), expected)

    def test_r_process_failure_remains_an_error(self):
        for error in (subprocess.CalledProcessError(1, ["Rscript"]), OSError("missing executable")):
            with self.subTest(error=error), mock.patch.dict(
                self.globals, {"run": mock.Mock(side_effect=error)}
            ):
                result = self.module["check_r_packages"]("Rscript", Path("/library"), self.packages)
                self.assertTrue(all(v.startswith("ERROR") for v in result.values()))

    def test_check_exit_status_and_skip_flag(self):
        for ready in (True, False):
            with self.subTest(ready=ready):
                collect = mock.Mock(return_value={"ready": ready})
                with mock.patch.dict(self.globals, {"collect": collect, "print_report": mock.Mock()}):
                    args = argparse.Namespace(domain="foundation", env_root="/env", skip_r=True, json=False)
                    self.assertEqual(self.module["command_check"](args), 0 if ready else 1)
                    self.assertFalse(collect.call_args.kwargs["include_r"])

    def test_install_reuses_valid_isolated_r_packages(self):
        run = mock.Mock()
        with mock.patch.dict(self.globals, {
            "check_r_packages": mock.Mock(return_value=dict.fromkeys(self.packages, "1.0")),
            "run": run,
        }):
            self.module["install_r_packages"](
                "Rscript", Path("/library"),
                {"cran": ["pheatmap"], "bioconductor": ["ComplexHeatmap"]}, False,
            )
        run.assert_not_called()

    def test_install_failure_exits_nonzero_without_traceback(self):
        for error in (subprocess.CalledProcessError(1, ["Rscript"]), OSError("missing executable")):
            with self.subTest(error=error), mock.patch.dict(self.globals, {
                "check_r_packages": mock.Mock(return_value={"pheatmap": "MISSING"}),
                "run": mock.Mock(side_effect=error),
            }):
                with self.assertRaises(SystemExit) as caught:
                    self.module["install_r_packages"](
                        "Rscript", Path("/library"), {"cran": ["pheatmap"]}, False
                    )
                self.assertIn("R package installation failed", str(caught.exception))

    def test_install_repairs_only_missing_packages(self):
        run = mock.Mock()
        with mock.patch.dict(self.globals, {
            "check_r_packages": mock.Mock(return_value={
                "pheatmap": "1.0.13", "ComplexHeatmap": "MISSING",
            }),
            "run": run,
        }):
            self.module["install_r_packages"](
                "Rscript", Path("/library"),
                {"cran": ["pheatmap"], "bioconductor": ["ComplexHeatmap"]}, False,
            )
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][-1], "ComplexHeatmap")

    def test_r_installer_launch_failure_is_reported(self):
        args = argparse.Namespace(install_r=True, dry_run=False)
        with mock.patch.dict(self.globals, {
            "host_r_install_candidates": lambda: [["brew", "install", "r"]],
            "run": mock.Mock(side_effect=OSError("missing package manager")),
        }), contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertIsNone(self.module["ensure_r"](None, args))
        self.assertIn("installing R failed", output.getvalue())

    def test_platform_package_manager_selection(self):
        cases = [
            ("darwin", "posix", "brew", "brew"),
            ("win32", "nt", "winget", "winget"),
            ("linux", "posix", "apt-get", "sudo"),
            ("linux", "posix", "dnf", "sudo"),
            ("linux", "posix", "pacman", "sudo"),
        ]
        for platform, name, manager, first in cases:
            with self.subTest(platform=platform, manager=manager), mock.patch.object(
                self.module["sys"], "platform", platform
            ), mock.patch.object(self.module["os"], "name", name), mock.patch.object(
                self.module["shutil"], "which",
                side_effect=lambda executable: executable if executable == manager else None,
            ):
                self.assertEqual(self.module["host_r_install_candidates"]()[0][0], first)

    def test_dry_run_does_not_probe_r_or_hide_install_steps(self):
        check = mock.Mock(side_effect=AssertionError("dry-run must not execute R"))
        run = mock.Mock()
        with mock.patch.dict(self.globals, {"check_r_packages": check, "run": run}):
            self.module["install_r_packages"](
                "Rscript", Path("/library"),
                {"cran": ["pheatmap"], "bioconductor": ["ComplexHeatmap"]}, True,
            )
        self.assertEqual(run.call_count, 2)
        self.assertTrue(all(call.kwargs["dry_run"] for call in run.call_args_list))

    def test_github_r_package_is_part_of_readiness(self):
        spec = {"cran": [], "bioconductor": [],
                "github": [{"package": "lionessR", "repo": "kuijjerlab/lionessR"}]}
        self.assertEqual(self.module["r_package_names"](spec), ["lionessR"])
        load = mock.Mock(return_value=(Path("/spec"), Path("/spec/requirements.in"), {}, [], spec))
        with mock.patch.dict(self.globals, {
            "load_spec": load, "parse_requirement_names": lambda _: [],
            "installed_packages": lambda _: {}, "verify_imports": lambda *_: {},
            "rscript": lambda: "Rscript", "r_version": lambda _: "4.3",
            "check_r_packages": lambda *_: {"lionessR": "MISSING"},
        }), mock.patch.object(Path, "is_file", return_value=True):
            result = self.module["collect"]("example", Path("/env"))
        self.assertFalse(result["ready"])
        self.assertEqual(result["r"]["packages"]["missing"], ["lionessR"])

    def test_github_install_uses_argument_list_and_inherits_library(self):
        spec = {"github": [{"package": "lionessR", "repo": "kuijjerlab/lionessR"}]}
        run = mock.Mock()
        library = Path("/env with spaces/R")
        with mock.patch.dict(self.globals, {"run": run}):
            self.module["install_r_packages"]("Rscript", library, spec, True)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][-3:],
                         [str(library), "lionessR", "kuijjerlab/lionessR"])
        self.assertEqual(run.call_args.kwargs["env"]["R_LIBS_USER"], str(library))

    def test_github_install_failure_exits_nonzero(self):
        with mock.patch.dict(self.globals, {
            "check_r_packages": lambda *_: {"lionessR": "MISSING"},
            "run": mock.Mock(side_effect=subprocess.CalledProcessError(1, ["Rscript"])),
        }):
            with self.assertRaises(SystemExit):
                self.module["install_r_packages"]("Rscript", Path("/library"), {
                    "github": [{"package": "lionessR", "repo": "kuijjerlab/lionessR"}],
                }, False)

    def test_full_profile_contains_all_dependency_types(self):
        _, requirements, _, tools, r_spec = self.module["load_spec"]("biomystery-full")
        self.assertEqual(len(self.module["parse_requirement_names"](requirements)), 53)
        self.assertIn("lionessR", self.module["r_package_names"](r_spec))
        self.assertEqual(len(r_spec["bioconductor"]), 25)
        self.assertTrue({"blastn", "samtools", "java", "node", "ossutil", "uv"}
                        .issubset({tool["name"] for tool in tools}))

    def test_missing_r_still_shows_package_stages_in_dry_run(self):
        args = argparse.Namespace(domain="biomystery-full", env_root="/env",
                                  dry_run=True, install_r=False, skip_r=False)
        install_r = mock.Mock()
        with mock.patch.dict(self.globals, {
            "run": mock.Mock(), "rscript": lambda: None,
            "ensure_r": lambda *_: None, "install_r_packages": install_r,
        }), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.module["command_install"](args), 0)
        self.assertEqual(install_r.call_args.args[0], "Rscript")
        self.assertIn("lionessR", self.module["r_package_names"](install_r.call_args.args[2]))
        self.assertTrue(install_r.call_args.args[3])


if __name__ == "__main__":
    unittest.main()
