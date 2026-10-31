from pathlib import Path
import importlib.util
import base64,json,re,subprocess,sys,shlex
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
    assert {p.attrib['name'] for p in tool.findall('inputs/param')}=={'action','source_gpx','model_assets','model_request','model_request_b64','dispatch_key'}
    assert tool.find("inputs/param[@name='model_request']").attrib['optional']=='true'
    result=tool.find('outputs/data[@name="result_bundle"]')
    assert result.attrib['label']=='RADAR-PD model ${dispatch_key} results'
    assert '&&' in tool.findtext('command') and '&amp;' not in tool.findtext('command')
    assert 'worker/verified_projects' in tool.find('outputs/collection/discover_datasets').attrib['directory']
    assert (ROOT/'templates/radar_pd_model_campaign.xml.in').is_file()
    assert '@IMMUTABLE_MODEL_IMAGE@' not in output.read_text()


@pytest.mark.parametrize('image',['latest','models-main','ghcr.io/lalityadav07/impurity_detection_gsas_ver6:models-short','evil.example/image:models-'+'a'*40])
def test_activation_requires_successful_immutable_worker_image(image,tmp_path):
    with pytest.raises(ValueError):renderer.render(image,tmp_path/'bad.xml')


def decoder(tmp_path):
    tool=ET.parse(ROOT/'tools/neutrons/powder_diffraction/radar_pd_model_campaign.xml').getroot()
    path=tmp_path/'decode.py';path.write_text(tool.findtext("configfiles/configfile[@name='request_decoder']"))
    return tool,path


def test_encoded_transport_keeps_default_sanitization_and_decodes_literal_data(tmp_path):
    tool,script=decoder(tmp_path)
    param=tool.find("inputs/param[@name='model_request_b64']")
    assert param.find('sanitizer') is None
    pattern=param.findtext('validator')
    payload={'literal':"Fe'\n$(touch MUST_NOT_EXIST); `touch ALSO_NOT`"}
    encoded=base64.b64encode(json.dumps(payload).encode()).decode()
    assert re.fullmatch(pattern,encoded) and not re.fullmatch(pattern,"$(touch unsafe)")
    source=tmp_path/'encoded.txt';source.write_text(encoded+'\n')
    target=tmp_path/'decoded.json'
    subprocess.run([sys.executable,str(script),str(source),str(target)],cwd=tmp_path,check=True)
    assert json.loads(target.read_text())==payload and not (tmp_path/'MUST_NOT_EXIST').exists()
    subprocess.run([sys.executable,str(script),str(source),str(target)],cwd=tmp_path,check=True)
    target.write_text('{"another":"request"}')
    assert subprocess.run([sys.executable,str(script),str(source),str(target)],capture_output=True).returncode!=0


@pytest.mark.parametrize('raw',[b'invalid$',base64.b64encode(b'[]'),base64.b64encode(b'{broken'),b'A'*(6*1024*1024+1)],
                         ids=['bad-base64','not-object','bad-json','oversized'])
def test_invalid_or_oversized_encoded_request_stops_before_native_execution(tmp_path,raw):
    _,script=decoder(tmp_path);source=tmp_path/'bad.txt';source.write_bytes(raw)
    result=subprocess.run([sys.executable,str(script),str(source),str(tmp_path/'decoded.json')],capture_output=True)
    assert result.returncode!=0 and not (tmp_path/'decoded.json').exists()


@pytest.mark.parametrize('encoded',[True,False])
def test_real_cheetah_command_preserves_both_request_paths(tmp_path,encoded):
    Template=pytest.importorskip('Cheetah.Template').Template
    tool,script=decoder(tmp_path)
    payload={'literal':"Fe' $(touch MUST_NOT_EXIST)"}
    data=json.dumps(payload);b64=base64.b64encode(data.encode()).decode()
    inline=tmp_path/'inline.txt';inline.write_text(b64)
    legacy=tmp_path/'legacy.json';legacy.write_text(data)
    worker=tmp_path/'fake_worker.py'
    worker.write_text("import json,pathlib,sys\np=pathlib.Path\np(sys.argv[6]).write_text(json.dumps(json.loads(p(sys.argv[4]).read_text())))\n")
    command=tool.findtext('command').replace('/opt/radar-symmetry/ndip_model_campaign.py',str(worker))
    result=tmp_path/'result.json'
    rendered=str(Template(command,searchList=[dict(action='native',result_bundle=str(result),console_output=str(tmp_path/'console.txt'),
        source_gpx='source.gpx',model_assets='assets.zip',model_request=None if encoded else str(legacy),
        model_request_b64=b64 if encoded else None,request_decoder=str(script),inline_request=str(inline))]))
    rendered=re.sub(r'(?m)^(\s*)python\s',lambda m:m[1]+shlex.quote(sys.executable)+' ',rendered)
    assert 'touch MUST_NOT_EXIST' not in rendered
    subprocess.run(['/bin/sh','-c',rendered],cwd=tmp_path,check=True)
    assert json.loads(result.read_text())==payload and not (tmp_path/'MUST_NOT_EXIST').exists()
