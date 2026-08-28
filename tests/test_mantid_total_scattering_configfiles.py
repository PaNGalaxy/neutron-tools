"""The tool's configfiles must render to JSON the runner can actually load.

``test_tool_xml.py`` only proves the *command* template fills. These tests fill
the two JSON configfiles with realistic values and parse the result, which is
where a stray comma or an unquoted empty value would otherwise show up only
after a Galaxy job has already been queued.
"""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from galaxy.util.template import fill_template


TOOL = Path(__file__).parents[1] / "tools" / "neutrons" / "mantid_total_scattering_prototype.xml"


class Dataset:
    """Stand-in for a Galaxy dataset wrapper in a Cheetah context."""

    def __init__(self, path: str, element_identifier: str) -> None:
        self.path = path
        self.element_identifier = element_identifier

    def __str__(self) -> str:
        return self.path


def _configfile(name: str) -> str:
    root = ET.parse(TOOL).getroot()
    node = root.find(f"./configfiles/configfile[@name='{name}']")
    assert node is not None, f"missing configfile '{name}'"
    return node.text or ""


def _context(**overrides) -> dict:
    context = {
        "data": {
            "sample_files": [Dataset("/data/1.dat", "sample_run")],
            "normalization_files": [Dataset("/data/2.dat", "vanadium_run")],
            "sample_background_files": [],
            "sample_background_background_files": [],
            "normalization_background_files": [],
            "calibration_file": None,
            "grouping_file": None,
        },
        "experiment": {
            "facility": "SNS",
            "instrument": "NOM",
            "title": "total_scattering",
        },
        "sample": {
            "material": "Si",
            "mass_density": 2.33,
            "packing_fraction": 0.35,
            "geometry": {"shape": "Cylinder", "radius": 0.15, "height": 1.8},
            "absorption_correction": "None",
            "multiple_scattering_correction": "None",
            "inelastic": {"inelastic_correction": "None"},
        },
        "normalization": {
            "material": "V",
            "mass_density": 6.11,
            "packing_fraction": 1.0,
            "radius": 0.2925,
            "height": 1.8,
            "absorption_correction": "None",
            "multiple_scattering_correction": "None",
        },
        "align_and_focus": {"tmin": 300.0, "tmax": 16667.0, "extra_args": ""},
        "merging": {
            "q_min": 0.0,
            "q_delta": 0.02,
            "q_max": 40.0,
            "high_q_linear_fit_range": 0.6,
            "self_scattering_levels": [],
        },
        "advanced": {
            "beam_height": "",
            "push_positive_level": 100.0,
            "debug_mode": False,
            "processing_q_step": "",
            "config_overrides": None,
        },
    }
    for section, values in overrides.items():
        context[section].update(values)
    return context


def _render(name: str, context: dict) -> dict:
    return json.loads(fill_template(_configfile(name), context, retry=0))


class TestToolParamsConfigfile:
    def test_minimal_run_renders_valid_json(self) -> None:
        rendered = _render("tool_params", _context())

        assert rendered["facility"] == "SNS"
        assert rendered["instrument"] == "NOM"
        assert rendered["sample_files"] == [
            {"path": "/data/1.dat", "name": "sample_run"}
        ]
        assert rendered["normalization_files"][0]["path"] == "/data/2.dat"
        assert rendered["calibration_file"] is None
        assert rendered["grouping_file"] is None

    def test_multiple_input_files_are_comma_separated(self) -> None:
        context = _context(data={
            "sample_files": [
                Dataset("/data/1.dat", "a"),
                Dataset("/data/2.dat", "b"),
                Dataset("/data/3.dat", "c"),
            ],
        })
        assert len(_render("tool_params", context)["sample_files"]) == 3

    def test_optional_file_params_render_as_paths_when_given(self) -> None:
        context = _context(data={
            "calibration_file": Dataset("/data/cal.dat", "cal"),
            "grouping_file": Dataset("/data/grp.dat", "grp"),
        })
        rendered = _render("tool_params", context)
        assert rendered["calibration_file"] == "/data/cal.dat"
        assert rendered["grouping_file"] == "/data/grp.dat"

    def test_cylinder_geometry(self) -> None:
        geometry = _render("tool_params", _context())["sample"]["geometry"]
        assert geometry == {"shape": "Cylinder", "radius": 0.15, "height": 1.8}

    def test_hollow_cylinder_geometry(self) -> None:
        context = _context(sample={
            "geometry": {
                "shape": "HollowCylinder",
                "inner_radius": 0.1,
                "outer_radius": 0.15,
                "height": 1.8,
            },
        })
        geometry = _render("tool_params", context)["sample"]["geometry"]
        assert geometry == {
            "shape": "HollowCylinder",
            "inner_radius": 0.1,
            "outer_radius": 0.15,
            "height": 1.8,
        }

    def test_placzek_branch_renders_all_its_settings(self) -> None:
        context = _context(sample={
            "inelastic": {
                "inelastic_correction": "Placzek",
                "order": "1st",
                "self_scattering": True,
                "interference": False,
                "fit_spectrum_with": "GaussConvCubicSpline",
                "lambda_binning_for_fit": "0.16,0.04,2.8",
                "lambda_binning_for_calc": "0.16,0.0001,2.9",
            },
        })
        inelastic = _render("tool_params", context)["sample"]["inelastic_correction"]
        assert inelastic["type"] == "Placzek"
        assert inelastic["self"] is True
        assert inelastic["interference"] is False
        assert inelastic["lambda_binning_for_calc"] == "0.16,0.0001,2.9"

    def test_multi_element_material_survives_rendering(self) -> None:
        context = _context(sample={"material": "Ce0.85 Y0.15 O2"})
        assert _render("tool_params", context)["sample"]["material"] == "Ce0.85 Y0.15 O2"

    def test_self_scattering_repeat_renders_as_a_list(self) -> None:
        context = _context(merging={
            "self_scattering_levels": [
                {"bank": 1, "level_min": 20.0, "level_max": 30.0},
                {"bank": 4, "level_min": 30.0, "level_max": 40.0},
            ],
        })
        levels = _render("tool_params", context)["merging"]["self_scattering_levels"]
        assert levels == [
            {"bank": 1, "min": 20.0, "max": 30.0},
            {"bank": 4, "min": 30.0, "max": 40.0},
        ]

    def test_empty_beam_height_renders_as_null(self) -> None:
        assert _render("tool_params", _context())["advanced"]["beam_height"] is None

    def test_beam_height_renders_when_set(self) -> None:
        context = _context(advanced={"beam_height": 2.5})
        assert _render("tool_params", context)["advanced"]["beam_height"] == 2.5

    def test_empty_processing_q_step_renders_as_null(self) -> None:
        rendered = _render("tool_params", _context())
        assert rendered["advanced"]["processing_q_step"] is None

    def test_processing_q_step_renders_when_set(self) -> None:
        context = _context(advanced={"processing_q_step": 0.005})
        assert _render("tool_params", context)["advanced"]["processing_q_step"] == 0.005

    def test_extra_align_and_focus_args_survive_as_a_json_string(self) -> None:
        context = _context(align_and_focus={"extra_args": '{\\"ResampleX\\": -3000}'})
        rendered = _render("tool_params", context)
        assert json.loads(rendered["align_and_focus"]["extra_args"]) == {
            "ResampleX": -3000
        }


class TestExtraFileListsConfigfile:
    def test_empty_optional_inputs_render_as_empty_lists(self) -> None:
        rendered = _render("extra_file_lists", _context())
        assert rendered == {
            "sample_background_files": [],
            "sample_background_background_files": [],
            "normalization_background_files": [],
        }

    def test_supplied_backgrounds_render_with_paths(self) -> None:
        context = _context(data={
            "sample_background_files": [Dataset("/data/bg.dat", "bg")],
            "sample_background_background_files": [Dataset("/data/bgbg.dat", "bgbg")],
            "normalization_background_files": [
                Dataset("/data/nb1.dat", "nb1"),
                Dataset("/data/nb2.dat", "nb2"),
            ],
        })
        rendered = _render("extra_file_lists", context)
        assert rendered["sample_background_files"] == [
            {"path": "/data/bg.dat", "name": "bg"}
        ]
        assert rendered["sample_background_background_files"][0]["name"] == "bgbg"
        assert len(rendered["normalization_background_files"]) == 2


class TestConfigfilesFeedTheRunner:
    """The two configfiles together are exactly the runner's input."""

    def test_merged_render_has_every_role_the_runner_stages(self) -> None:
        params = _render("tool_params", _context())
        params.update(_render("extra_file_lists", _context()))

        runner = pytest.importorskip(
            "tests.test_mantid_total_scattering_prototype").runner
        for role in runner.ROLES:
            assert role in params
