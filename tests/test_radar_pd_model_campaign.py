from pathlib import Path
import importlib.util
import xml.etree.ElementTree as ET

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('model_tool_renderer',ROOT/'scripts/render_radar_pd_model_tool.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)


def test_worker_template_binds_exact_dispatch_result_and_data_inputs(tmp_path):
    output=tmp_path/'models.xml';image='ghcr.io/lalityadav07/impurity_detection_gsas_ver6:models-'+'a'*40
    renderer.render(image,output);tool=ET.parse(output).getroot()
    assert tool.attrib['id']=='neutrons_radar_pd_model_campaign_prototype'
    assert tool.findtext('requirements/container')==image
    assert {p.attrib['name'] for p in tool.findall('inputs/param')}=={'action','source_gpx','model_assets','model_request','dispatch_key'}
    result=tool.find('outputs/data[@name="result_bundle"]')
    assert result.attrib['label']=='RADAR-PD model ${dispatch_key} results'
    assert '&&' in tool.findtext('command') and '&amp;' not in tool.findtext('command')
    assert 'worker/verified_projects' in tool.find('outputs/collection/discover_datasets').attrib['directory']
    assert (ROOT/'templates/radar_pd_model_campaign.xml.in').is_file()
    assert '@IMMUTABLE_MODEL_IMAGE@' not in output.read_text()


@pytest.mark.parametrize('image',['latest','models-main','ghcr.io/lalityadav07/impurity_detection_gsas_ver6:models-short','evil.example/image:models-'+'a'*40])
def test_activation_requires_successful_immutable_worker_image(image,tmp_path):
    with pytest.raises(ValueError):renderer.render(image,tmp_path/'bad.xml')
