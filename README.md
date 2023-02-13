# Galaxy Tools

This is the repo for Galaxy tools that we create within the neutrons project. At the deployment stage, the tools from this repo will be added to Galaxy.

## Project Structure

- _tools_ - folder with tools, content to be copied to galaxy _tools_ folder
- _tool-data_ - folder with tools data, content to be copied to galaxy _tool-data_ folder

## Development

### Enviroment

Install the conda environment `galaxytools` with file `development.yml`:

```bash
$> conda env create --file development.yml
$> conda activate galaxytools
(galaxytools)$>
```

### Adding a new tool
- put tool files - xml and code (e.g. a python script) to _tools/neutrons_
- if needed, add tool data to _tool-data_ folder

## Deployment

### Installing to Galaxy

#### Copying files
 - copy `tools/neutrons` to a local tools folder. E.g. to a default location of Galaxy tools `$GALAXY_ROOT/tools`
 - copy `tool-data` content to `$GALAXY_ROOT/tool-data` (or to an alternative location of tool-data configured in galaxy.yml)

### Updating tool_conf.xml and tool_data_table.conf
update Galaxy configuration files as needed to add tools from this repo 
(manually or through deployment procedure you are using, e.g. Ansible)

