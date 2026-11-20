from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from utils.register_subhkl_datatype import register_datatype


ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "tool_data" / "subhkl_datatypes_conf.xml.sample"


def test_register_datatype_is_valid_and_idempotent(tmp_path: Path) -> None:
    config = tmp_path / "datatypes_conf.xml"
    config.write_text(
        '<?xml version="1.0"?>\n<datatypes>\n'
        '  <registration converters_path="converters" display_path="displays">\n'
        '    <datatype extension="txt" type="galaxy.datatypes.data:Text"/>\n'
        "  </registration>\n</datatypes>\n",
        encoding="utf-8",
    )

    assert register_datatype(config, FRAGMENT) is True
    assert register_datatype(config, FRAGMENT) is False

    root = ET.parse(config).getroot()
    matches = root.findall("./registration/datatype[@extension='mtz']")
    assert len(matches) == 1
    assert matches[0].attrib == {
        "extension": "mtz",
        "type": "galaxy.datatypes.binary:Binary",
        "mimetype": "application/octet-stream",
        "display_in_upload": "true",
    }


def test_register_datatype_preserves_existing_custom_datatypes(tmp_path: Path) -> None:
    config = tmp_path / "datatypes_conf.xml"
    config.write_text(
        '<?xml version="1.0"?>\n<datatypes>\n'
        '  <registration converters_path="converters" display_path="displays">\n'
        '    <datatype extension="gpx" type="galaxy.datatypes.binary:Binary" '
        'mimetype="application/octet-stream" display_in_upload="true"/>\n'
        "  </registration>\n</datatypes>\n",
        encoding="utf-8",
    )

    assert register_datatype(config, FRAGMENT) is True
    assert register_datatype(config, FRAGMENT) is False

    root = ET.parse(config).getroot()
    assert len(root.findall("./registration/datatype[@extension='gpx']")) == 1
    assert len(root.findall("./registration/datatype[@extension='mtz']")) == 1


def test_subhkl_and_careless_tools_accept_mtz_or_binary_uploads_and_emit_mtz() -> None:
    careless_root = ET.parse(
        ROOT / "tools" / "neutrons" / "imaginex_subhkl_merge.xml"
    ).getroot()
    refl_param = careless_root.find("./inputs/param[@name='reflections']")
    assert refl_param is not None
    assert refl_param.attrib.get("format") == "mtz,binary"
    mode_param = careless_root.find("./inputs/param[@name='mode']")
    assert mode_param is not None
    assert mode_param.attrib.get("type") == "select"
    mode_opts = [
        (opt.attrib.get("value"), opt.attrib.get("selected"))
        for opt in mode_param.findall("option")
    ]
    assert mode_opts == [("poly", "true"), ("mono", None)]
    gpu_res = {
        el.attrib.get("type"): (el.text or "").strip()
        for el in careless_root.findall("./requirements/resource")
    }
    assert gpu_res.get("cuda_device_count_min") == "1"
    cmd_text = (careless_root.findtext("./command") or "").strip()
    assert "CUDA_CACHE_PATH=/tmp/cuda_cache" in cmd_text
    assert "_GALAXY_JOB_HOME_DIR" in cmd_text
    assert "careless $careless_mode --iterations=$iterations" in cmd_text
    assert "--disable-image-scales" in cmd_text
    assert '#if $careless_mode == "poly":' in cmd_text
    assert "--wavelength-key=WAVEL" in cmd_text
    assert "--wilson-prior-b=" in cmd_text
    assert "--lorentz-correction" in cmd_text
    for out_name in ("merged_mtz", "predictions_mtz", "xval_mtz"):
        out_el = careless_root.find(f"./outputs/data[@name='{out_name}']")
        assert out_el is not None
        assert out_el.attrib.get("format") == "mtz"
    csv_out = careless_root.find("./outputs/data[@name='merge_table_csv']")
    assert csv_out is not None
    assert csv_out.attrib.get("format") == "csv"
    assert csv_out.attrib.get("label") == "merge_table.csv"
    html_out = careless_root.find("./outputs/data[@name='merge_table_html']")
    assert html_out is not None
    assert html_out.attrib.get("format") == "html"
    assert html_out.attrib.get("label") == "merge_table.html"

    cov_root = ET.parse(
        ROOT / "tools" / "neutrons" / "imaginex_instrument_coverage.xml"
    ).getroot()
    cov_in = cov_root.find("./inputs/param[@name='input']")
    assert cov_in is not None
    assert cov_in.attrib.get("format") == "mtz,binary"

    analysis_root = ET.parse(
        ROOT / "tools" / "neutrons" / "imaginex_analysis.xml"
    ).getroot()
    for param_name in ("coverage_file", "phasing_file", "honly_file", "file"):
        param_el = analysis_root.find(f".//param[@name='{param_name}']")
        assert param_el is not None
        assert param_el.attrib.get("format") == "mtz,binary"


def test_careless_post_metrics_script_emits_csv_and_html_tables(tmp_path: Path) -> None:
    import csv
    import json
    import re
    import shutil
    import subprocess
    import sys

    import pytest

    gemmi = pytest.importorskip("gemmi")
    np = pytest.importorskip("numpy")

    careless_root = ET.parse(
        ROOT / "tools" / "neutrons" / "imaginex_subhkl_merge.xml"
    ).getroot()
    cfg_el = careless_root.find("./configfiles/configfile[@name='post_metrics_script']")
    assert cfg_el is not None and cfg_el.text is not None
    script_src = cfg_el.text.strip().removeprefix("#raw").removesuffix("#end raw").strip()

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    uc = gemmi.UnitCell(55.16, 81.19, 88.70, 90.0, 96.3, 90.0)
    sg = gemmi.find_spacegroup_by_name("I 1 2 1")
    hkls = [
        (2, 0, 0),
        (0, 2, 0),
        (2, 2, 0),
        (4, 2, 2),
        (6, 4, 2),
        (8, 6, 4),
        (10, 8, 6),
        (12, 10, 8),
        (14, 12, 10),
        (16, 14, 12),
    ]

    in_mtz = gemmi.Mtz(with_base=True)
    in_mtz.spacegroup = sg
    in_mtz.set_cell_for_all(uc)
    in_mtz.add_dataset("in")
    in_mtz.add_column("WAVEL", "W")
    in_mtz.add_column("THETA", "R")
    in_mtz.add_column("PHI", "R")
    in_mtz.add_column("BATCH", "I")
    in_mtz.add_column("DPHI", "R")
    in_mtz.add_column("H_0", "H")
    in_mtz.add_column("Hobs", "H")
    in_mtz.add_column("harmonic_id", "I")
    in_mtz.set_data(
        np.asarray(
            [
                [h, k, l, 2.0 + 0.2 * i, 15.0 + i, -40.0 + 5.0 * i, 1000 * (i % 2), 0.0, h, h, 1]
                for i, (h, k, l) in enumerate(hkls)
            ],
            dtype=np.float32,
        )
    )
    in_mtz.write_to_file(str(tmp_path / "input_reflections.mtz"))

    m_mtz = gemmi.Mtz(with_base=True)
    m_mtz.spacegroup = sg
    m_mtz.set_cell_for_all(uc)
    m_mtz.add_dataset("merged")
    m_mtz.add_column("I", "J")
    m_mtz.add_column("SigI", "Q")
    m_mtz.set_data(
        np.asarray([[h, k, l, 180.0 - 8.0 * i, 10.0] for i, (h, k, l) in enumerate(hkls)], dtype=np.float32)
    )
    m_mtz.write_to_file(str(out_dir / "merged.mtz"))

    p_mtz = gemmi.Mtz(with_base=True)
    p_mtz.spacegroup = sg
    p_mtz.set_cell_for_all(uc)
    p_mtz.add_dataset("pred")
    p_mtz.add_column("I", "J")
    p_mtz.set_data(
        np.asarray([[h, k, l, 180.0] for (h, k, l) in hkls for _ in range(4)], dtype=np.float32)
    )
    p_mtz.write_to_file(str(out_dir / "predictions.mtz"))

    x_mtz = gemmi.Mtz(with_base=True)
    x_mtz.spacegroup = sg
    x_mtz.set_cell_for_all(uc)
    x_mtz.add_dataset("xval")
    x_mtz.add_column("half", "I")
    x_mtz.add_column("I", "J")
    x_rows = []
    for i, (h, k, l) in enumerate(hkls):
        x_rows.append([h, k, l, 0, 180.0 - 8.0 * i])
        x_rows.append([h, k, l, 1, 178.0 - 7.9 * i])
    x_mtz.set_data(np.asarray(x_rows, dtype=np.float32))
    x_mtz.write_to_file(str(out_dir / "careless_xval_0.mtz"))

    runner_py = tmp_path / "run_post_metrics.py"
    shim = (
        "import sys, types\n"
        "try:\n"
        "    import reciprocalspaceship\n"
        "except ImportError:\n"
        "    rs = types.ModuleType('reciprocalspaceship')\n"
        "    rs.utils = types.SimpleNamespace(generate_reciprocal_asu=lambda cell, sg, dmin: [[2,0,0],[0,2,0],[2,2,0],[4,2,2],[6,4,2],[8,6,4],[10,8,6],[12,10,8],[14,12,10],[16,14,12]])\n"
        "    sys.modules['reciprocalspaceship'] = rs\n"
    )
    runner_py.write_text(shim + script_src + "\n", encoding="utf-8")
    subprocess.run([sys.executable, str(runner_py)], cwd=str(tmp_path), check=True)

    metrics = json.loads((out_dir / "careless_metrics.json").read_text(encoding="utf-8"))
    assert metrics["space_group"] == "I 1 2 1"
    assert metrics["n_observations"] == 40
    assert metrics["n_merged_asu"] == 10
    for b in metrics["resolution_bins"]:
        if b["n_refl"] > 0:
            assert b["n_obs"] == 4 * b["n_refl"]
            assert abs(b["multiplicity"] - 4.0) < 1e-6

    csv_rows = list(csv.DictReader((out_dir / "merge_table.csv").open(encoding="utf-8")))
    assert len(csv_rows) == 11
    assert csv_rows[-1]["shell"] == "Overall"
    assert csv_rows[-1]["n_obs"] == "40"

    html_text = (out_dir / "merge_table.html").read_text(encoding="utf-8")
    assert "BUBBLE" not in html_text.upper()
    assert "Word / Excel" not in html_text
    assert ">Copy</button>" in html_text
    assert "Download .csv" not in html_text
    assert "Georgia" in html_text
    assert "#0a1020" in html_text and "#bae6fd" in html_text
    if shutil.which("node"):
        m_js = re.search(r"<script>([\s\S]*?)</script>", html_text)
        assert m_js is not None
        js_file = tmp_path / "merge_table_inline.js"
        js_file.write_text(m_js.group(1), encoding="utf-8")
        subprocess.run(["node", "--check", str(js_file)], check=True)

    prep_el = careless_root.find("./configfiles/configfile[@name='prep_mtz_script']")
    assert prep_el is not None and prep_el.text is not None
    prep_src = prep_el.text.strip().removeprefix("#raw").removesuffix("#end raw").strip()
    prep_shim = (
        "import sys, types, gemmi, numpy as np\n"
        "try:\n"
        "    import reciprocalspaceship\n"
        "except ImportError:\n"
        "    class _DummySeries:\n"
        "        def __init__(self, arr):\n"
        "            self._arr = np.asarray(arr)\n"
        "        def to_numpy(self):\n"
        "            return self._arr\n"
        "    class _DummyDS(dict):\n"
        "        merged = False\n"
        "        index = None\n"
        "        def get_m_isym_keys(self): return ['M/ISYM']\n"
        "        def hkl_to_asu(self): return self\n"
        "        def write_mtz(self, p): pass\n"
        "    def _read_mtz(p):\n"
        "        m = gemmi.read_mtz_file(p)\n"
        "        arr = np.array(m, copy=False)\n"
        "        ds = _DummyDS()\n"
        "        for idx, col in enumerate(m.columns):\n"
        "            ds[col.label] = _DummySeries(arr[:, idx])\n"
        "        return ds\n"
        "    rs = types.ModuleType('reciprocalspaceship')\n"
        "    rs.read_mtz = _read_mtz\n"
        "    rs.DataSeries = lambda arr, index=None, dtype=None: _DummySeries(arr)\n"
        "    sys.modules['reciprocalspaceship'] = rs\n"
    )
    prep_py = tmp_path / "run_prep_mtz.py"
    prep_py.write_text(prep_shim + prep_src + "\n", encoding="utf-8")

    import os

    res_poly = subprocess.run(
        [sys.executable, str(prep_py)],
        cwd=str(tmp_path),
        env={**os.environ, "CARELESS_MODE": "poly"},
        check=True,
        capture_output=True,
        text=True,
    )
    poly_keys = res_poly.stdout.strip().split(",")
    assert poly_keys == ["WAVEL", "THETA", "PHI", "RUN"]
    assert "DPHI" not in poly_keys  # constant column filtered out (prevents 0/0 NaN)
    assert "harmonic_id" not in poly_keys and "H_0" not in poly_keys

    res_mono = subprocess.run(
        [sys.executable, str(prep_py)],
        cwd=str(tmp_path),
        env={**os.environ, "CARELESS_MODE": "mono"},
        check=True,
        capture_output=True,
        text=True,
    )
    mono_keys = res_mono.stdout.strip().split(",")
    assert mono_keys == ["WAVEL", "THETA", "PHI", "RUN"]


def test_interactivetool_subhkl_declares_local_staging_gpu_mode() -> None:
    it_root = ET.parse(
        ROOT
        / "tools"
        / "neutrons"
        / "single-crystal-diffraction"
        / "interactivetool_subhkl.xml"
    ).getroot()
    env_vars = {
        el.attrib.get("name"): (el.text or "").strip()
        for el in it_root.findall("./environment_variables/environment_variable")
    }
    assert env_vars.get("SUBHKL_EXEC_MODE") == "local"
    assert env_vars.get("JAX_PLATFORMS") == "cpu"
    assert env_vars.get("XLA_PYTHON_CLIENT_PREALLOCATE") == "false"
    cmd_text = (it_root.findtext("./command") or "").strip()
    assert "SUBHKL_STAGING_DIR=" in cmd_text
    assert "umask 0000" in cmd_text
    assert "CUDA_CACHE_PATH=/tmp/cuda_cache" in cmd_text
    assert "_GALAXY_JOB_HOME_DIR" in cmd_text


def test_pulsar_cleanup_trap_unlocks_0700_nv_dir_and_preserves_exit_code(
    tmp_path: Path,
) -> None:
    import os
    import stat
    import subprocess

    xml_paths = [
        *sorted((ROOT / "tools" / "neutrons").glob("imaginex_subhkl*.xml")),
        ROOT
        / "tools"
        / "neutrons"
        / "single-crystal-diffraction"
        / "interactivetool_subhkl.xml",
    ]
    assert len(xml_paths) >= 10
    for xp in xml_paths:
        cmd = ET.parse(xp).getroot().findtext("./command") or ""
        assert "CUDA_CACHE_PATH=/tmp/cuda_cache" in cmd, xp.name
        assert "_GALAXY_JOB_HOME_DIR" in cmd, xp.name

    work = tmp_path / "working"
    home = tmp_path / "home"
    gtmp = tmp_path / "tmp"
    nv_dir = home / ".nv" / "ComputeCache"
    work.mkdir()
    nv_dir.mkdir(parents=True)
    gtmp.mkdir()
    os.chmod(home / ".nv", 0o700)
    os.chmod(nv_dir, 0o700)

    rendered_trap = (
        'set -e\n'
        'trap \'rc=$?; chmod -R a+rwX "$PWD" '
        '${_GALAXY_JOB_HOME_DIR:+"$_GALAXY_JOB_HOME_DIR"} '
        '${_GALAXY_JOB_TMP_DIR:+"$_GALAXY_JOB_TMP_DIR"} '
        '2>/dev/null || true; exit $rc\' EXIT\n'
        'exit 7\n'
    )
    res = subprocess.run(
        ["/bin/sh", "-c", rendered_trap],
        cwd=str(work),
        env={
            **os.environ,
            "_GALAXY_JOB_HOME_DIR": str(home),
            "_GALAXY_JOB_TMP_DIR": str(gtmp),
        },
    )
    assert res.returncode == 7
    assert stat.S_IMODE(os.stat(home / ".nv").st_mode) == 0o777
    assert stat.S_IMODE(os.stat(nv_dir).st_mode) == 0o777

