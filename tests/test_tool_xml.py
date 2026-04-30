import re
import subprocess
import sys
from itertools import chain
from typing import Any, Dict, List

import pytest
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.parser.output_objects import ToolOutput, ToolOutputCollection
from galaxy.util.template import fill_template


def _parse_inputs(input_sources: Any) -> Dict[str, Any]:
    if input_sources is None:
        return {}

    inputs: Dict[str, Any] = {}
    for source in chain.from_iterable(input_sources):
        try:
            key = source.parse_name()
        except Exception:
            continue

        nested_sources = [source.parse_nested_inputs_source().parse_input_sources()]
        conditional_sources = [
            conditional_source[1].parse_input_sources()
            for conditional_source in source.parse_when_input_sources()
        ]
        if nested_sources == [[]] and conditional_sources == []:
            inputs[key] = "__ndip_testing_value"
        if nested_sources != [[]]:
            if source.input_type == "repeat":
                inputs[key] = [_parse_inputs(nested_sources)]
            else:
                inputs[key] = _parse_inputs(nested_sources)
        if conditional_sources != []:
            inner_params = _parse_inputs(conditional_sources)
            if inputs[key] == "__ndip_testing_value":
                inputs[key] = inner_params
            else:
                inputs[key] = inputs[key] | inner_params

            for inner_key, inner_value in inner_params.items():
                if inner_key not in inputs:
                    inputs[inner_key] = inner_value

    return inputs


def _check_planemo_linter(xml_path: str) -> None:
    # Test with the planemo linter to validate common missing required parameters
    subprocess.run(
        [
            "planemo",
            "lint",
            "--fail_level=error",
            "--report_level=error",
            "--skip",
            "ValidDatatypes,XSD",
            xml_path,
        ],
        capture_output=True,
        check=True,
        text=True,
    )


def _check_tool_command(xml_path: str) -> None:
    tool_source = get_tool_source(xml_path)

    # Parse tool command
    raw_command = tool_source.parse_command()
    # $getVar() doesn't rely on defined inputs/outputs and is valid, so we need to ignore it.
    filtered_command = re.sub(r"\$getVar\(.*\)", "'__ndip_test_value'", raw_command)

    # Parse tool outputs
    outputs = tool_source.parse_outputs(None)[0].keys()

    # Parse tool inputs
    page_sources = tool_source.parse_input_pages().page_sources
    inputs = _parse_inputs([page.parse_input_sources() for page in page_sources])

    # Parse config files
    config_files = tool_source.parse_template_configfiles()
    for file in config_files:
        if file.name:
            inputs[file.name] = file.content

    # Test if we can build a valid command from the cheetah template
    try:
        fill_template(
            filtered_command,
            inputs | dict.fromkeys(outputs, "test"),
            retry=0,
        )
    except Exception as exc:
        # These will get flagged but are generally safe.
        for safe_field in [
            "'__galaxy_url__'",
            "'element_identifier'",
            "'hid'",
            "'name'",
            "'tags'",
            "'value'",
        ]:
            if safe_field in str(exc):
                return

        raise


def _check_missing_output(xml_path: str) -> None:
    tool_source = get_tool_source(xml_path)

    # Parse tool command and outputs
    command = tool_source.parse_command()

    # Unlike in fill_template, we need to skip collections here
    output_items = tool_source.parse_outputs(None)[0]
    outputs: List[str] = []
    for key, value in output_items.items():
        if isinstance(value, ToolOutput) and value.from_work_dir:
            continue
        if isinstance(value, ToolOutputCollection):
            continue
        outputs.append(key)

    for output in outputs:
        if f"${output}" not in command:
            raise ValueError(
                f"The tool command never references declared output '{output}'. This will cause your tool to behave unexpectedly in Galaxy."
            )


def test_tool_xml(xml_path) -> None:
    _check_planemo_linter(xml_path)
    _check_tool_command(xml_path)
    _check_missing_output(xml_path)


if __name__ == "__main__":
    pytest.main(sys.argv)
