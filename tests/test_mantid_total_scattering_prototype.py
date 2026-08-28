"""Tests for the Mantid Total Scattering prototype tool.

The tool's logic lives in the ``mts_runner`` configfile inside the XML, which
keeps it in one place and lets Galaxy inject it into a foreign container. These
tests load that script straight out of the XML so there is no second copy to
drift out of agreement with what actually runs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import ModuleType
from xml.etree import ElementTree as ET

import pytest


TOOL = Path(__file__).parents[1] / "tools" / "neutrons" / "mantid_total_scattering_prototype.xml"


def _load_runner() -> ModuleType:
    """Execute the inlined runner script as a module."""
    root = ET.parse(TOOL).getroot()
    configfile = root.find("./configfiles/configfile[@name='mts_runner']")
    assert configfile is not None, "the tool must inline an 'mts_runner' script"

    source = configfile.text or ""
    source = source.replace("#raw", "", 1)
    source = source.rsplit("#end raw", 1)[0]

    module = ModuleType("mts_runner")
    exec(compile(source, str(TOOL), "exec"), module.__dict__)
    return module


runner = _load_runner()


@pytest.fixture
def params() -> dict:
    """A minimal run: one sample file, one normalization file, defaults."""
    return {
        "facility": "SNS",
        "instrument": "NOM",
        "title": "total_scattering",
        "sample_files": [{"path": "/data/sample.dat", "name": "sample"}],
        "normalization_files": [{"path": "/data/van.dat", "name": "van"}],
        "sample_background_files": [],
        "sample_background_background_files": [],
        "normalization_background_files": [],
        "calibration_file": None,
        "grouping_file": None,
        "sample": {
            "material": "Si",
            "mass_density": 2.33,
            "packing_fraction": 0.35,
            "geometry": {"shape": "Cylinder", "radius": 0.15, "height": 1.8},
            "absorption_correction": "None",
            "multiple_scattering_correction": "None",
            "inelastic_correction": {"type": "None", "order": None},
        },
        "normalization": {
            "material": "V",
            "mass_density": 6.11,
            "packing_fraction": 1.0,
            "geometry": {"shape": "Cylinder", "radius": 0.2925, "height": 1.8},
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
            "beam_height": None,
            "push_positive_level": 100.0,
            "debug_mode": False,
            "config_overrides": None,
        },
    }


@pytest.fixture
def staged() -> dict:
    return {
        "sample_files": ["/w/staged/sample_0.nxs"],
        "normalization_files": ["/w/staged/normalization_0.nxs"],
        "sample_background_files": ["/w/staged/sample_background_0.nxs"],
        "sample_background_background_files": [],
        "normalization_background_files": [],
    }


def _build(params: dict, staged: dict, **overrides) -> dict:
    kwargs = {
        "calibration_file": "/app/examples/sns/nomad_cal.h5",
        "grouping_file": "/app/examples/sns/groupings/nomad_group_16_8_masked.xml",
        "config_file": "/w/mts_config/auto_config.json",
        "cache_dir": "/w/cache",
        "output_dir": "/w/output",
    }
    kwargs.update(overrides)
    return runner.build_mts_config(params, staged, **kwargs)


class TestBuildConfigOffCluster:
    """The generated JSON has to be runnable away from the SNS filesystem."""

    def test_skips_the_ipts_catalogue_lookup(self, params, staged) -> None:
        # Without DummyExpt the reduction calls GetIPTS, which needs the
        # analysis cluster's catalogue.
        assert _build(params, staged)["DummyExpt"] is True

    def test_points_at_a_writable_cache_and_output_dir(self, params, staged) -> None:
        config = _build(params, staged)
        assert config["CacheDirMTS"] == "/w/cache"
        assert config["OutputDir"] == "/w/output"

    def test_names_a_facility_config_outside_sns(self, params, staged) -> None:
        assert _build(params, staged)["AutoConfigFile"] == "/w/mts_config/auto_config.json"

    def test_uses_filenames_not_run_numbers(self, params, staged) -> None:
        config = _build(params, staged)
        assert config["Sample"]["Filenames"] == staged["sample_files"]
        assert config["Normalization"]["Filenames"] == staged["normalization_files"]
        assert "Runs" not in config["Sample"]
        assert "Runs" not in config["Normalization"]

    def test_normalization_uses_the_key_the_reduction_reads(self, params, staged) -> None:
        # The reduction indexes config['Normalization'] directly for geometry,
        # so the 'Vanadium' alias is not good enough.
        assert "Normalization" in _build(params, staged)


class TestBuildConfigRequiredShape:
    """Fields the reduction reads without a default must always be present."""

    def test_sample_geometry_carries_a_shape(self, params, staged) -> None:
        geometry = _build(params, staged)["Sample"]["Geometry"]
        assert geometry == {"Shape": "Cylinder", "Radius": 0.15, "Height": 1.8}

    def test_hollow_cylinder_geometry(self, params, staged) -> None:
        params["sample"]["geometry"] = {
            "shape": "HollowCylinder",
            "inner_radius": 0.1,
            "outer_radius": 0.15,
            "height": 1.8,
        }
        assert _build(params, staged)["Sample"]["Geometry"] == {
            "Shape": "HollowCylinder",
            "InnerRadius": 0.1,
            "OuterRadius": 0.15,
            "Height": 1.8,
        }

    def test_sample_always_has_a_background_section(self, params, staged) -> None:
        # The reduction loads a container unconditionally.
        assert _build(params, staged)["Sample"]["Background"]["Filenames"]

    def test_calibration_filename_is_set(self, params, staged) -> None:
        assert _build(params, staged)["Calibration"]["Filename"].endswith("nomad_cal.h5")


class TestBuildConfigGrouping:
    """Grouping choice is what keeps a 100k pixel instrument in memory."""

    def test_initial_grouping_is_applied(self, params, staged) -> None:
        grouping = _build(params, staged)["Merging"]["Grouping"]
        assert grouping["Initial"].endswith("nomad_group_16_8_masked.xml")

    def test_output_grouping_is_left_to_the_calibration(self, params, staged) -> None:
        # An explicit 'Output' grouping changes the number of focussed banks,
        # which then no longer matches QMaxByBank and the reduction aborts in
        # CropWorkspaceRagged.
        assert "Output" not in _build(params, staged)["Merging"]["Grouping"]

    def test_no_grouping_section_without_a_grouping_file(self, params, staged) -> None:
        config = _build(params, staged, grouping_file=None)
        assert "Grouping" not in config["Merging"]


class TestBuildConfigCorrections:
    def test_none_corrections_are_omitted_entirely(self, params, staged) -> None:
        sample = _build(params, staged)["Sample"]
        assert "AbsorptionCorrection" not in sample
        assert "MultipleScatteringCorrection" not in sample
        assert "InelasticCorrection" not in sample

    def test_selected_corrections_become_type_sections(self, params, staged) -> None:
        params["sample"]["absorption_correction"] = "SampleOnly"
        params["sample"]["multiple_scattering_correction"] = "SampleOnly"
        sample = _build(params, staged)["Sample"]
        assert sample["AbsorptionCorrection"] == {"Type": "SampleOnly"}
        assert sample["MultipleScatteringCorrection"] == {"Type": "SampleOnly"}

    def test_placzek_settings_are_carried_through(self, params, staged) -> None:
        params["sample"]["inelastic_correction"] = {
            "type": "Placzek",
            "order": "1st",
            "self": True,
            "interference": False,
            "fit_spectrum_with": "GaussConvCubicSpline",
            "lambda_binning_for_fit": "0.16,0.04,2.8",
            "lambda_binning_for_calc": "0.16,0.0001,2.9",
        }
        inelastic = _build(params, staged)["Sample"]["InelasticCorrection"]
        assert inelastic["Type"] == "Placzek"
        assert inelastic["Order"] == "1st"
        assert inelastic["Self"] is True
        assert inelastic["LambdaBinningForFit"] == "0.16,0.04,2.8"


class TestBuildConfigOptionalSections:
    def test_background_of_the_background_is_nested(self, params, staged) -> None:
        staged["sample_background_background_files"] = ["/w/staged/sbb_0.nxs"]
        background = _build(params, staged)["Sample"]["Background"]
        assert background["Background"]["Filenames"] == ["/w/staged/sbb_0.nxs"]

    def test_no_nested_background_when_none_supplied(self, params, staged) -> None:
        assert "Background" not in _build(params, staged)["Sample"]["Background"]

    def test_normalization_background_is_optional(self, params, staged) -> None:
        assert "Background" not in _build(params, staged)["Normalization"]

        staged["normalization_background_files"] = ["/w/staged/nb_0.nxs"]
        assert _build(params, staged)["Normalization"]["Background"] == {
            "Filenames": ["/w/staged/nb_0.nxs"]
        }

    def test_self_scattering_levels_are_keyed_by_bank(self, params, staged) -> None:
        params["merging"]["self_scattering_levels"] = [
            {"bank": 1, "min": 20.0, "max": 30.0},
            {"bank": 4, "min": 30.0, "max": 40.0},
        ]
        assert _build(params, staged)["SelfScatteringLevelCorrection"] == {
            "Bank1": [20.0, 30.0],
            "Bank4": [30.0, 40.0],
        }

    def test_beam_height_only_when_given(self, params, staged) -> None:
        assert "BeamHeight" not in _build(params, staged)

        params["advanced"]["beam_height"] = 2.5
        assert _build(params, staged)["BeamHeight"] == 2.5

    def test_extra_align_and_focus_args_are_merged(self, params, staged) -> None:
        params["align_and_focus"]["extra_args"] = '{"ResampleX": -3000}'
        args = _build(params, staged)["AlignAndFocusArgs"]
        assert args == {"TMin": 300.0, "TMax": 16667.0, "ResampleX": -3000}

    def test_q_binning_is_a_triple(self, params, staged) -> None:
        assert _build(params, staged)["Merging"]["QBinning"] == [0.0, 0.02, 40.0]


class TestDeepUpdate:
    def test_nested_dicts_are_merged_not_replaced(self) -> None:
        base = {"Sample": {"Material": "Si", "MassDensity": 2.33}}
        runner.deep_update(base, {"Sample": {"MassDensity": 3.0}})
        assert base == {"Sample": {"Material": "Si", "MassDensity": 3.0}}

    def test_non_dict_values_are_replaced(self) -> None:
        base = {"Merging": {"QBinning": [0.0, 0.02, 40.0]}}
        runner.deep_update(base, {"Merging": {"QBinning": [0.0, 0.01, 35.0]}})
        assert base["Merging"]["QBinning"] == [0.0, 0.01, 35.0]


class TestStaging:
    def test_every_input_gets_a_distinct_nxs_name(self, tmp_path, params) -> None:
        source = tmp_path / "galaxy_dataset.dat"
        source.write_bytes(b"nexus")
        params["sample_files"] = [
            {"path": str(source), "name": "a"},
            {"path": str(source), "name": "b"},
        ]

        staged = runner.stage_inputs(params, str(tmp_path / "staged"))

        assert [os.path.basename(p) for p in staged["sample_files"]] == [
            "sample_0.nxs",
            "sample_1.nxs",
        ]
        # MTS hashes the basename for its cache keys, so the names must differ.
        assert len(set(staged["sample_files"])) == 2
        for path in staged["sample_files"]:
            assert os.path.isfile(path)

    def test_absent_roles_stage_to_empty_lists(self, tmp_path, params) -> None:
        params["sample_files"] = []
        staged = runner.stage_inputs(params, str(tmp_path / "staged"))
        assert staged["sample_background_files"] == []


class TestFacilityConfig:
    def test_written_config_has_the_keys_the_reduction_requires(self, tmp_path) -> None:
        config_file = runner.write_facility_config(
            str(tmp_path / "mts_config"), "SNS", "NOM")

        with open(config_file) as handle:
            contents = json.load(handle)
        for key in ("QParamsProcessing", "TMIN", "TMAX", "CacheDir"):
            assert key in contents
        assert os.path.isdir(contents["CacheDir"])

    def test_group_index_is_written_alongside(self, tmp_path) -> None:
        # Older reductions open this unconditionally for non-PG3 instruments.
        config_file = runner.write_facility_config(
            str(tmp_path / "mts_config"), "SNS", "NOM")
        assert os.path.isfile(
            os.path.join(os.path.dirname(config_file), "group_index.txt"))

    def test_unknown_instrument_still_gets_a_usable_config(self, tmp_path) -> None:
        config_file = runner.write_facility_config(
            str(tmp_path / "mts_config"), "SNS", "NOSUCH")
        with open(config_file) as handle:
            assert "QParamsProcessing" in json.load(handle)


class TestCollectOutputs:
    def test_title_named_results_are_copied_to_fixed_paths(self, tmp_path) -> None:
        output_dir = tmp_path / "output"
        (output_dir / "SofQ").mkdir(parents=True)
        (output_dir / "SofQ" / "my_run.nxs").write_bytes(b"sofq")
        destination = tmp_path / "sofq_out"

        written = runner.collect_outputs(
            str(output_dir), "my_run",
            {os.path.join("SofQ", "{title}.nxs"): str(destination)})

        assert written == [str(destination)]
        assert destination.read_bytes() == b"sofq"

    def test_missing_results_are_skipped_not_fatal(self, tmp_path) -> None:
        written = runner.collect_outputs(
            str(tmp_path), "my_run",
            {os.path.join("GSAS", "{title}.gsa"): str(tmp_path / "gsas_out")})
        assert written == []


class TestProcessingQParams:
    """The focussing Q binning has to survive a 100k pixel instrument.

    Without absorption correction the detectors are grouped before the rebin,
    so a fine step is cheap. With absorption correction the reduction rebins
    every pixel on its own, and a 0.001 step over 40 inverse angstroms is tens
    of gigabytes.
    """

    def test_fine_step_when_no_absorption_correction(self, params) -> None:
        assert runner.processing_q_params(params) == "0.01,0.001,40.0"

    def test_falls_back_to_the_output_step_with_sample_absorption(self, params) -> None:
        params["sample"]["absorption_correction"] = "SampleOnly"
        assert runner.processing_q_params(params) == "0.01,0.02,40.0"

    def test_falls_back_to_the_output_step_with_normalization_absorption(self, params) -> None:
        params["normalization"]["absorption_correction"] = "Carpenter"
        assert runner.processing_q_params(params) == "0.01,0.02,40.0"

    def test_explicit_override_wins(self, params) -> None:
        params["sample"]["absorption_correction"] = "SampleOnly"
        params["advanced"]["processing_q_step"] = 0.005
        assert runner.processing_q_params(params) == "0.01,0.005,40.0"

    def test_q_min_is_taken_from_the_merging_binning_when_positive(self, params) -> None:
        params["merging"]["q_min"] = 0.05
        assert runner.processing_q_params(params).startswith("0.05,")

    def test_written_config_carries_the_processing_binning(self, tmp_path, params) -> None:
        params["sample"]["absorption_correction"] = "SampleOnly"
        config_file = runner.write_facility_config(
            str(tmp_path / "mts_config"), "SNS", "NOM",
            q_params=runner.processing_q_params(params))

        with open(config_file) as handle:
            assert json.load(handle)["QParamsProcessing"] == "0.01,0.02,40.0"
