"""A standalone diagnostic measures the actual inference entry point."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from Cheetah.Template import Template
import pytest

PATH=Path(__file__).resolve().parents[1]/'tools/neutrons/powder_diffraction/radar_pd_preparation_ranking_benchmark.xml'


def test_ranking_transport_preserves_all_arguments(tmp_path):
    tool=ET.parse(PATH).getroot()
    values={name:name+'.data' for name in ('ranking_driver','inline_request','source_gpx','model_assets','result_bundle','console_output')}
    command=' '.join(line.strip() for line in str(Template(tool.findtext('command'),searchList=[values])).splitlines())
    stub="python() { printf '%s\\0' \"$@\" > actual.bin; }\n"
    p=subprocess.run(['bash'],input=stub+command,text=True,cwd=tmp_path,capture_output=True)
    assert p.returncode==0,p.stderr
    assert (tmp_path/'actual.bin').read_bytes().decode().split('\0')[:-1]==[
        'ranking_driver.data','inline_request.data','source_gpx.data','model_assets.data','worker','result_bundle.data']


@pytest.mark.parametrize('payload',[[],{},dict(schema='wrong'),dict(schema='radar-structural-ranking-benchmark/v1',code='print(1)')])
def test_invalid_data_never_reaches_native_import(tmp_path,payload):
    tool=ET.parse(PATH).getroot();script=tool.find('./configfiles/configfile[@name="ranking_driver"]').text
    compile(script,'ranking-driver','exec')
    p=tmp_path/'driver.py';p.write_text(script)
    encoded=tmp_path/'encoded';encoded.write_bytes(base64.b64encode(json.dumps(payload).encode()))
    result=subprocess.run([sys.executable,str(p),str(encoded),'missing-source','missing-assets','worker','out.zip'],capture_output=True,text=True,cwd=tmp_path)
    assert result.returncode and 'closed data-only' in result.stderr
    assert not (tmp_path/'worker').exists()


def test_native_inference_and_inputs_are_bound():
    tool=ET.parse(PATH).getroot();script=tool.find('./configfiles/configfile[@name="ranking_driver"]').text
    assert tool.attrib['hidden']=='true'
    assert tool.findtext('./requirements/container').endswith('models-d2bc43d8e76a9677415b2d6afc8f098b39558103')
    assert not tool.findall('./environment_variables/environment_variable')
    assert not tool.findall('./requirements/credentials')
    assert 'gpx_recipe.preparation.structural_ranking_native' in script
    assert 'execute_chunk' not in script
    assert 'verify_inputs(protocol, inputs)' in script
    assert 'file_sha(source) != expected' in script
    assert "pack(destination, archive, ['ranking.json', 'response.json'])" in script
    assert 'package_signature()' in script
