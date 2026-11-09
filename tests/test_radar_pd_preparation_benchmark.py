"""The pilot uses bounded data requests and leaves deployed tools unchanged."""
import base64
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from Cheetah.Template import Template
import pytest

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'tools/neutrons/powder_diffraction/radar_pd_preparation_benchmark.xml'
TRAINING=PATH.with_name('radar_pd_preparation_training_benchmark.xml')


def expanded(path):
    tool=ET.parse(path).getroot()
    macro=ET.parse(path.parent/'radar_pd_preparation_benchmark.macros').getroot()
    for child in list(tool):
        if child.tag=='expand':
            body=macro.find('./xml[@name="'+child.attrib['macro']+'"]')
            assert body is not None
            position=list(tool).index(child);tool.remove(child)
            for offset,item in enumerate(body):tool.insert(position+offset,copy.deepcopy(item))
    tool.remove(tool.find('macros'))
    return tool


@pytest.mark.parametrize('encoded',[True,False])
@pytest.mark.parametrize('parts',[[],['part-one.zip','part-two.zip']])
@pytest.mark.parametrize('action',['native','chunk'])
@pytest.mark.parametrize('path',[PATH,TRAINING])
def test_native_request_transport_renders_with_optional_input_parts(encoded,parts,action,path):
    tool=expanded(path)
    scope={key:key+'.data' for key in ('result_bundle','console_output','preparation_certificate',
        'runtime_probe','request_decoder','inline_request','source_gpx','model_assets','preparation_provenance')}
    scope.update(action=action,model_request_b64='e30=' if encoded else '',
                 model_request=None if encoded else 'request.json',model_asset_parts=parts)
    command=str(Template(tool.findtext('command'),searchList=[scope]))
    result=subprocess.run(['bash','-n'],input=command,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    assert command.index("python 'runtime_probe.data'")<command.index('/opt/radar-symmetry/ndip_model_campaign.py')
    assert command.count('--asset-part')==len(parts)
    assert '--preparation-evidence' in command and '--preparation-certificate' in command
    assert ('decoded-model-request.json' in command)==encoded
    assert "ndip_model_campaign.py '"+action+"'" in command


def test_pilot_is_separate_and_never_sets_its_own_scheduler_grant():
    tool=expanded(PATH)
    assert tool.attrib['id']=='neutrons_radar_pd_preparation_benchmark_prototype'
    assert tool.attrib['hidden']=='true'
    image=tool.findtext('./requirements/container')
    assert image.endswith('models-d2bc43d8e76a9677415b2d6afc8f098b39558103')
    assert not tool.findall('./environment_variables/environment_variable')
    assert not tool.findall('./requirements/credentials')
    assert [r.attrib['value'] for r in tool.findall('./inputs/param[@name="action"]/option')]==['native','chunk']
    probe=tool.find('./configfiles/configfile[@name="runtime_probe"]').text
    compile(probe,'runtime_probe','exec')
    assert 'allocation(4)' in probe and 'torch.cuda.is_available()' in probe
    assert 'os.environ' not in probe


@pytest.mark.parametrize('path,cores,memory',[(PATH,1,4096),(TRAINING,4,8192)])
def test_allocation_hints_are_declarative_with_optional_site_schema_validation(tmp_path,path,cores,memory):
    tool=expanded(path)
    resources={r.attrib['type']:int(r.text) for r in tool.findall('./requirements/resource')}
    assert resources==dict(cores_min=cores,cores_max=cores,ram_min=memory)
    assert not tool.findall('./environment_variables/environment_variable')
    xml=tmp_path/'tool.xml';ET.ElementTree(tool).write(xml,encoding='utf-8')
    schema=os.environ.get('RADAR_GALAXY_SCHEMA')
    if schema:
        result=subprocess.run(['xmllint','--noout','--schema',schema,str(xml)],capture_output=True,text=True)
        assert result.returncode==0,result.stderr


@pytest.mark.parametrize('value',[dict(operation='preparation-structural-training'),['not','an','object']])
def test_embedded_decoder_accepts_data_objects_only(tmp_path,value):
    tool=expanded(PATH)
    script=tmp_path/'decoder.py';script.write_text(tool.find('./configfiles/configfile[@name="request_decoder"]').text)
    encoded=tmp_path/'encoded.txt';encoded.write_bytes(base64.b64encode(json.dumps(value).encode()))
    output=tmp_path/'request.json'
    result=subprocess.run([sys.executable,str(script),str(encoded),str(output)],capture_output=True,text=True)
    if isinstance(value,dict):assert result.returncode==0 and json.loads(output.read_text())==value
    else:assert result.returncode!=0 and not output.exists()
