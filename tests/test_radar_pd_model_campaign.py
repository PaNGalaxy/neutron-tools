from pathlib import Path
import importlib.util
import base64,json,re,subprocess,sys,shlex
import xml.etree.ElementTree as ET
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('model_tool_renderer',ROOT/'scripts/render_radar_pd_model_tool.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)


def test_worker_template_binds_exact_dispatch_result_and_data_inputs(tmp_path):
    output=tmp_path/'models.xml';image='ghcr.io/lalityadav07/impurity_detection_gsas_ver6:models-'+'a'*40
    renderer.render(image,output);tool=ET.parse(output).getroot()
    assert tool.attrib['id']=='neutrons_radar_pd_model_campaign_prototype'
    assert tool.attrib['version']=='0.3.8'
    assert ET.parse(ROOT/'tools/neutrons/powder_diffraction/radar_pd_model_campaign.xml').getroot().attrib['version']=='0.3.8'
    assert tool.findtext('requirements/container')==image
    assert {v.attrib['value'] for v in tool.findall("inputs/param[@name='action']/option")} == {'native','admission','chunk'}
    assert {p.attrib['name'] for p in tool.findall('inputs/param')}=={'action','source_gpx','model_assets','model_asset_parts','preparation_evidence','model_request','model_request_b64','dispatch_key'}
    assert tool.find("inputs/param[@name='model_request']").attrib['optional']=='true'
    result=tool.find('outputs/data[@name="result_bundle"]')
    assert result.attrib['label']=='RADAR-PD model ${dispatch_key} results'
    assert '&&' in tool.findtext('command') and '&amp;' not in tool.findtext('command')
    assert 'worker/verified_projects' in tool.find('outputs/collection/discover_datasets').attrib['directory']
    assert (ROOT/'templates/radar_pd_model_campaign.xml.in').is_file()
    assert '@IMMUTABLE_MODEL_IMAGE@' not in output.read_text()
    assert '@PREPARATION_' not in output.read_text()
    assert tool.find("outputs/data[@name='preparation_certificate']") is not None
    assert tool.find("outputs/collection[@name='reviewable_projects']") is not None


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
@pytest.mark.parametrize('action',['native','admission','chunk'])
@pytest.mark.parametrize('folded',[False,True])
def test_real_cheetah_command_preserves_both_request_paths(tmp_path,encoded,action,folded):
    Template=pytest.importorskip('Cheetah.Template').Template
    tool,script=decoder(tmp_path)
    payload={'literal':"Fe' $(touch MUST_NOT_EXIST)"}
    data=json.dumps(payload);b64=base64.b64encode(data.encode()).decode()
    inline=tmp_path/'inline.txt';inline.write_text(b64)
    legacy=tmp_path/'legacy.json';legacy.write_text(data)
    worker=tmp_path/'fake_worker.py'
    worker.write_text("import json,pathlib,sys\np=pathlib.Path\np(sys.argv[6]).write_text(json.dumps(json.loads(p(sys.argv[4]).read_text())))\n")
    command=tool.findtext('command').replace('/opt/radar-symmetry/ndip_model_campaign.py',str(worker))
    publisher=tmp_path/'publish.py'
    publisher.write_text("import pathlib,sys\nassert pathlib.Path(sys.argv[1]).is_file()\n")
    command=command.replace('python -m gpx_recipe.preparation.certificates','python '+shlex.quote(str(publisher)))
    result=tmp_path/'result.json'
    rendered=str(Template(command,searchList=[dict(action=action,result_bundle=str(result),console_output=str(tmp_path/'console.txt'),
        source_gpx='source.gpx',model_assets='assets.zip',model_request=None if encoded else str(legacy),
        model_request_b64=b64 if encoded else None,request_decoder=str(script),inline_request=str(inline),
        model_asset_parts=[],preparation_evidence=[],preparation_provenance=str(tmp_path/'provenance.json'),
        preparation_certificate=str(tmp_path/'certificate.json'))]))
    rendered=re.sub(r'(?m)^(\s*)python\s',lambda m:m[1]+shlex.quote(sys.executable)+' ',rendered)
    if folded:rendered=' '.join(line.strip() for line in rendered.splitlines())
    assert 'touch MUST_NOT_EXIST' not in rendered
    subprocess.run(['/bin/sh','-c',rendered],cwd=tmp_path,check=True)
    assert json.loads(result.read_text())==payload and not (tmp_path/'MUST_NOT_EXIST').exists()


def test_both_templates_use_the_same_server_bound_preparation_provenance(tmp_path):
    nodes=[]
    for name in ('model_campaign','live_snapshot'):
        output=tmp_path/(name+'.xml')
        renderer.render('ghcr.io/lalityadav07/impurity_detection_gsas_ver6:models-'+'a'*40,output,tool=name)
        nodes.append(ET.parse(output).getroot())
    envelopes=[node.findtext("configfiles/configfile[@name='preparation_provenance']") for node in nodes]
    assert envelopes[0]==envelopes[1]
    Template=pytest.importorskip('Cheetah.Template').Template
    class Certificate:
        def __str__(self):return '/staged/native-certificate.json'
        unsanitized=SimpleNamespace(state='ok',deleted=False,purged=False,
            creating_job=SimpleNamespace(tool_id='neutrons_radar_pd_model_campaign_prototype',
                tool_version='0.3.4',state='ok',stdout='unrelated log\n[RADAR PREPARATION CERTIFICATE] '+64*'a'))
    record=json.loads(str(Template(envelopes[0],searchList=[dict(preparation_evidence=[Certificate()])])) )['records'][0]
    assert record['certificate_path']=='/staged/native-certificate.json'
    assert record['tool_version']=='0.3.4' and record['dataset_deleted'] is False
    assert record['job_stdout']=='[RADAR PREPARATION CERTIFICATE] '+64*'a'


@pytest.mark.parametrize('cache',[False,True])
def test_live_snapshot_passes_the_cache_as_an_argument_not_a_new_shell_command(tmp_path,cache):
    Template=pytest.importorskip('Cheetah.Template').Template
    output=tmp_path/'live.xml'
    renderer.render('ghcr.io/lalityadav07/impurity_detection_gsas_ver6:models-'+'a'*40,output,tool='live_snapshot')
    node=ET.parse(output).getroot()
    command=str(Template(node.findtext('command'),searchList=[dict(packet='packet.zip',result_bundle='out.zip',
        response_cache_output='cache-out.zip',console_output='console.txt',preparation_provenance='provenance.json',
        response_cache='cache-in.zip' if cache else None)]))
    bootstrap="python() { printf '%s\\0' \"$@\" > args.bin; }\n"
    subprocess.run(['/bin/sh','-c',bootstrap+command],cwd=tmp_path,check=True)
    args=(tmp_path/'args.bin').read_bytes().decode().split('\0')[:-1]
    assert args[:6]==['-m','gpx_recipe.live.galaxy_worker','packet.zip','worker','out.zip','cache-out.zip']
    assert args[6:8]==['--preparation-evidence','provenance.json']
    assert args[8:]==(['--cache','cache-in.zip'] if cache else [])
