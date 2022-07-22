# Galaxy Tools

This is the repo for Galaxy tools that we create within the NDIP project. At the deployment stage, the tools from this repo will be added to Galaxy.

## Project Structure

- _tools_ - folder with tools, content to be copied to galaxy _tools_ folder
- _tool-data_ - folder with tools data, content to be copied to galaxy _tool-data_ folder
- _config/ndip_tools_conf.xml_ - galaxy tool config file, contains only NDIP tools
- _config/xml_combine.py_ - a script to merge _ndip_tools_conf.xml_ with the one shipped with Galaxy


## Adding a new tool
- put tool files - xml and code (e.g. a python script) to _tools/ndip_tools_
- add a tool to a corresponding section in _config/ndip_tools_conf.xml_
- if needed, add tool data to _tool-data_ folder
