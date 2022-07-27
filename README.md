# Galaxy Tools

This is the repo for Galaxy tools that we create within the NDIP project. At the deployment stage, the tools from this repo will be added to Galaxy.

## Project Structure

- _tools_ - folder with tools, content to be copied to galaxy _tools_ folder
- _tool-data_ - folder with tools data, content to be copied to galaxy _tool-data_ folder
- _config/ndip_tools_conf.xml_ - galaxy tool config file, contains only NDIP tools
- _config/ndip_tool_data_table_conf.xml_ - galaxy tools table config file, contains only NDIP tables
- _config/*combine.py_ - scripts to merge config files with those shipped with Galaxy


## Adding a new tool
- put tool files - xml and code (e.g. a python script) to _tools/ndip_tools_
- add a tool to a corresponding section in _config/ndip_tools_conf.xml_
- if needed, add tool data to _tool-data_ folder and/or tool data table config to _config/ndip_tool_data_table_conf.xml_

## Installing to Galaxy

### Copying files
 - copy `tools/ndip_tools` to a local tools folder. E.g. to a default location of Galaxy tools `$GALAXY_ROOT/tools`
 - copy `config/tool_data_table.conf` to `$GALAXY_ROOT/config`
 - copy `tool-data` content to `$GALAXY_ROOT/tool-data` (or to an alternative location of tool-data configured in galaxy.yml)

### Updating tool_conf.xml and tool_data_table.conf
the following example merges Galaxy's `tool_conf.xml` with `ndip_tool_conf.xml` (call it from the repo's root folder). 
You can omit `--ndip-tools-dir` if you installed ndip_tools to `$GALAXY_ROOT/tools`. 
Modify as needed. You can als0 add `--dry-run` to check the output before overwriting the file 
```bash
cd config
GALAXY_ROOT=/galaxy # path to the Galaxy root folder
python3 tool_combine.py --ndip-tools-dir=/local_tools_folder/neutrons $GALAXY_ROOT/config/tool_conf.xml
```
similar for `tool_data_table.conf`
```
python3 table_combine.py $GALAXY_ROOT/config/tool_data_table_conf.xml
```

