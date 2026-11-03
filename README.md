# Galaxy Tools

This is the repo for Galaxy tools that we create within the neutrons project. At the deployment stage, the tools from this repo will be added to Galaxy.

## Project Structure

- _tools_ - folder with tools, content to be copied to galaxy _tools_ folder
- _tool-data_ - folder with tools data, content to be copied to galaxy _tool-data_ folder


## Adding a new tool

- put tool files - xml and code (e.g. a python script) to _tools/neutrons_
- if needed, add tool data to _tool-data_ folder

Before pushing, we provide some some tests for your XML file. You can run these tests with:

```bash
pixi run pytest
```

You can also configure these tests to run when you commit by using `pre-commit`:

```bash
pixi run pre-commit install
# If you run the tests on commit and other peoples prototype XML files are causing failures, then you can still commit with the following.
git commit --no-verify
```

## Logs for Failing Tests

When a test that runs against a live Galaxy fails, a link to a Kibana dashboard with
Elasticsearch logs is added to the failure output if available, where it shows up both in
the job log and in the JUnit report that GitLab renders in the test report tab of the
pipeline. The link covers the time between the first job the test submitted and the moment
the failure was recorded, padded by 15 seconds on both sides, so the job's own logs are in
view.

The link is only produced when `KIBANA_URL` is set to the Kibana dashboard holding the logs
of the environment being tested, e.g. `https://ndip.ornl.gov/logs`. Tests run without it,
such as the XML linting, simply report their failures as before. The URL itself is built in
`scripts/kibana.py`, which both paths below share.

### Tests run under pytest

The interactive tool tests report their job submissions through the `log_window` fixture,
which is applied automatically:

```python
def test_something(log_window):
    log_window.job_submitted(job_id)
```

A test that never calls `job_submitted` still gets a link, covering the time the test
itself ran. The job ids passed in are listed alongside the link, so they can be used to
narrow the search further in Kibana.

### Tests run under planemo

planemo writes its own JUnit report, so the pytest fixture never sees those tests. The
reports are post-processed by `scripts/add_kibana_links.py` instead, which takes the window
each tool's job ran in from the `--test_output_json` report planemo writes alongside the
XML. A test whose tool never started has no job to take times from, so it falls back to the
window of the whole planemo run, which the CI job passes in with `--run-start`/`--run-end`.

## Installing to Galaxy

### Copying files
 - copy `tools/neutrons` to a local tools folder. E.g. to a default location of Galaxy tools `$GALAXY_ROOT/tools`
 - copy `tool-data` content to `$GALAXY_ROOT/tool-data` (or to an alternative location of tool-data configured in galaxy.yml)

### Updating tool_conf.xml and tool_data_table.conf
update Galaxy configuration files as needed to add tools from this repo 
(manually or through deployment procedure you are using, e.g. Ansible) 
