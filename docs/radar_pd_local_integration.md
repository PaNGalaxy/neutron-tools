# RADAR-PD NDIP Integration (Local Prototype)

This directory contains a local-only NDIP/Galaxy integration for RADAR-PD. Nothing in this working tree has been pushed or deployed.

## Local tools

| Tool | Purpose |
| --- | --- |
| `radar_pd_configure.xml` | Create a reusable path-independent Full/Rapid configuration. |
| `radar_pd_analyze.xml` | Run uploaded/history data or resolve an optional SNS IPTS input, then return normalized outputs and collections. |
| `radar_pd_library_builder.xml` | Build a portable mini or augmented CIF library. |
| `radar_pd_compare_series.xml` | Compare normalized outputs from mapped scans. |
| `radar_pd_result_explorer.xml` | Inspect a run through an NDIP interactive entry point. |
| `radar_pd_gpx_handoff.xml` | Select and preserve one GPX checkpoint for downstream interactive GSAS-II use. |

The wrappers expect a local image named `radar-pd-ndip:local`, built from `Dockerfile.ndip` in the RADAR-PD `birthright-container` branch.

## Required deployment wiring

- Replace `radar-pd-ndip:local` with an immutable ORNL registry image reference.
- Mount the versioned RADAR-PD catalogs at `/opt/radar-pd/data`.
- Optionally mount the SNS facility tree read-only at `/SNS` for IPTS mode.
- Register the `gpx` datatype using `tool_data/radar_pd_datatypes_conf.xml.sample`.
- Assign Full and Rapid jobs to appropriate NDIP destinations/resources.
- Register a separate interactive GSAS-II image that accepts GPX before enabling editable project continuation.

The existing `asrp_gsas2_refinement.xml` and `asrp_gsas2_refinement_prototype.xml` tools are batch refiners that start from raw data, instrument parameters, and CIFs. They are not existing-GPX openers.

## Local checks

```bash
python -m py_compile scripts/ndip_contracts.py scripts/ndip_outputs.py \
  scripts/ndip_runner.py scripts/ndip_gpx_handoff.py
pixi run pytest tests/test_tool_xml.py
gxwf-lint --skip-best-practices workflows/radar_pd/*.gxwf.yml
```

The prototype branch automatically copies tools to the test NDIP instance when pushed. Do not push until the container image, catalog mount, datatype, resource destination, and repository permissions are agreed with the NDIP maintainers.
