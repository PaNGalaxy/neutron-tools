# RADAR-PD Galaxy Workflow Templates

These Format2 (`*.gxwf.yml`) files are local workflow templates for the prototype tools. They cover uploaded Rapid and Full runs, an SNS IPTS/event-driven run, a mini custom library followed by analysis, and collection-mapped scan-series analysis.

Before import into NDIP, validate and convert them against the exact Galaxy/gxformat2 version used by NDIP:

```bash
gxwf-lint workflows/radar_pd/*.gxwf.yml
gxwf-to-native workflows/radar_pd/uploaded_rapid.gxwf.yml > uploaded_rapid.ga
```

The mapped-series template relies on Galaxy collection mapping inferred from its collection input. Confirm that the deployed NDIP Galaxy version accepts the nested conditional input paths used by `radar_pd_analyze.xml` before publishing the workflow.
