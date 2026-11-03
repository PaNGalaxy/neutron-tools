# RADAR-PD production installation

This package adds the 13 RADAR-PD tools to the production branch without changing
the existing tools or CI. It is an installation candidate; merging the files does
not itself install or restart the production Galaxy service. The site
administrator must apply the registration and runtime configuration below through
the production deployment procedure.

The package is based on production commit
`39eaab3e3f0d1916684b8c07a814305da9f286a0`. The companion wrappers and GPX datatype support
were copied from prototype commit `3dc25baaf437720dc67443e2d20b9e277a2dc721`.
The NOVA 0.6.32 launch-page and user-guide wrapper comes from tested source commit
`bf29e4b8e574044b65458a3ae6a8023a8a541c45`, with immutable image digest
`sha256:ff1a7791dc835bea40b304e4a9594ab68aa5c41daebb230f5dd5cf6c57348852`.
No facility data, credentials, private audit reports, or unrelated prototype
tools are included.

## Register the tools and datatype

1. Install the 13 `tools/neutrons/powder_diffraction/radar_pd_*.xml` files under
   the production Galaxy tool root, preserving their relative paths.
2. Merge the section from
   [`radar_pd_tool_conf.xml.sample`](../tool_data/radar_pd_tool_conf.xml.sample)
   into a configured tool configuration, or add the sample as a separate entry
   in Galaxy's `tool_config_file`. Resolve its tool paths against the production
   tool root. Avoid registering the same tool twice.
3. Register the opaque GSAS-II `gpx` datatype using
   [`radar_pd_datatypes_conf.xml.sample`](../tool_data/radar_pd_datatypes_conf.xml.sample).
   The helper below adds the entry once to an existing datatype configuration;
   it preserves an existing `gpx` registration. Use the actual configuration
   file loaded by production Galaxy and review the resulting entry.

   ```bash
   python utils/register_radar_pd_datatype.py \
     --config /path/to/production/datatypes_conf.xml \
     --fragment tool_data/radar_pd_datatypes_conf.xml.sample
   ```

4. Reload or restart Galaxy through the site deployment procedure, then verify
   that all 13 tools are visible and their configured images can be pulled.

The tool IDs deliberately retain the `_prototype` suffix. The pinned NOVA client
submits and opens companion tools by these IDs; changing them requires a
coordinated client release. The IDs do not choose the Galaxy instance or job
destination. The existing `neutrons_export` tool is also used for export and must
remain installed; this package does not replace it.

## Runtime prerequisites

- Make all image references in the release inventory below available to the
  production container runner, including any registry authentication for GHCR
  and Savannah. Preserve the matching catalogs packaged with the scientific
  images. The XML wrappers call programs inside those images; no checkout of the
  NOVA application or extra repository-local runtime scripts is required.
- Configure interactive tool routing, path prefixes, and WebSocket forwarding.
  NOVA exposes port 8081; the GSAS-II desktop and Result Explorer expose port
  8080. Galaxy must provide its normal per-session URL, API key, history ID, and
  interactive entry-point path.
- Configure job destinations and CPU/memory allocations for analysis and model
  workers. Pass the actual allocation through `GALAXY_SLOTS` and the container
  limits. A concurrency choice in NOVA does not allocate cluster resources; the
  model worker falls back to one process when no allocation is available.
- For direct facility browsing and Live acquisition, mount the authorized SNS
  and HFIR trees read-only into the NOVA session and workers that read them,
  with the required ACLs. The wrapper sets `/SNS` and `/HFIR` as discovery roots;
  these variables do not create mounts. Configure the site's Galaxy-authorized
  file-import route separately when that route is used instead of direct access.
- Retain Galaxy history, dataset, and collection access needed by the session and
  its submitted jobs. Confirm the production service URL and proxy route from
  inside the session; do not point a production session at the test instance.

## Optional model-service credentials

The current NOVA XML exposes optional personal Galaxy credential groups for ORNL
Illumine and Bilbao. Ordinary RADAR-PD analysis does not require either key.
Shared service access needs separate site configuration: deliver the approved
shared secrets to NOVA through its supported `AZURE_ILLUMINE_API_KEY` and
`BCS_API_KEY` environment variables, using the production secret-management
mechanism. This package contains no keys and does not provision that mechanism.

Keep shared secrets out of XML, source control, submitted request payloads, and
history datasets. Restrict injection to the NOVA session; numerical refinement
and model workers receive the reviewed request or candidate catalog, not the
model-service secrets. Verify shared access in a fresh session after the site
configuration is applied. Personal credential selection remains available in
the copied wrapper until the site chooses how to present shared access.

## Release inventory

These are the exact image references carried by the reviewed prototype package.
The package preserves the scientific worker pins; it does not rebuild them.
Keep the table synchronized with XML when preparing a subsequent release, and
verify the NOVA release image before production installation.

| Wrapper | Version | Image |
| --- | --- | --- |
| `radar_pd_nova.xml` | `0.6.32` | `ghcr.io/lalityadav07/impurity_detection_gsas_ver6:nova-bf29e4b8e574044b65458a3ae6a8023a8a541c45` |
| `radar_pd_analyze.xml` | `0.5.32` | `ghcr.io/lalityadav07/impurity_detection_gsas_ver6:ndip-7e370db403b138a572e1240558dad0822f61ea78` |
| `radar_pd_configure.xml` | `0.3.0` | `savannah.ornl.gov/radar-pd/radar-pd:ndip-bc15eaa-catalog-20260617` |
| `radar_pd_resolve_sns_input.xml` | `0.1.0` | `savannah.ornl.gov/radar-pd/radar-pd:ndip-3e33a6b-catalog-20260617` |
| `radar_pd_facility_access_probe.xml` | `0.1.1` | `savannah.ornl.gov/radar-pd/radar-pd:ndip-3e33a6b-catalog-20260617` |
| `radar_pd_library_builder.xml` | `0.3.11` | `ghcr.io/lalityadav07/impurity_detection_gsas_ver6:ndip-7e370db403b138a572e1240558dad0822f61ea78` |
| `radar_pd_compare_series.xml` | `0.2.1` | `savannah.ornl.gov/radar-pd/radar-pd:ndip-bc15eaa-catalog-20260617` |
| `radar_pd_gpx_handoff.xml` | `0.2.2` | `savannah.ornl.gov/radar-pd/radar-pd:ndip-bc15eaa-catalog-20260617` |
| `radar_pd_gsasii_interactive.xml` | `0.1.17` | `ghcr.io/lalityadav07/impurity_detection_gsas_ver6:gsasii-gui-a4822fab93b172a07d84b611e1a9e38b403a66c2` |
| `radar_pd_result_explorer.xml` | `0.3.9` | `savannah.ornl.gov/radar-pd/radar-pd-nova:nova-0.3.2` |
| `radar_pd_refine_recipe.xml` | `0.3.3` | `ghcr.io/lalityadav07/impurity_detection_gsas_ver6:ndip-08a97f91e6b1224fc0595735614ca2a4d615d9c9` |
| `radar_pd_model_campaign.xml` | `0.2.2` | `ghcr.io/lalityadav07/impurity_detection_gsas_ver6:models-08a97f91e6b1224fc0595735614ca2a4d615d9c9` |
| `radar_pd_live_snapshot.xml` | `0.1.2` | `ghcr.io/lalityadav07/impurity_detection_gsas_ver6:models-d64ba7a3dbdd6356af4859344834b96d5df301bd` |

## Verification scope

Package validation checks XML, registration paths and IDs, GPX registration
idempotency, and unchanged companion-worker pins. These checks do not install
the service, validate production mounts or credentials, or establish scientific
accuracy for a new experiment. After installation, use a controlled production
smoke test to confirm session launch, one authorized dataset submission,
published outputs, GPX reopening, and export. The repository's full interactive
test suite launches tools against its configured Galaxy instance; it is not an
installation command and should not be used as an unreviewed deployment check.

The 0.6.32 image updates the bundled user guide to the current Live, refinement,
model exploration and recovery workflows. It preserves the dated AGES walkthrough
as a separate reference. This is a documentation-only application release; the
12 companion tools and their scientific image pins are unchanged.
