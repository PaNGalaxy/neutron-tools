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
    assert tool.attrib['version']=='0.2.17'
    # Updating the future template does not activate an unpublished image.
    assert ET.parse(ROOT/'tools/neutrons/powder_diffraction/radar_pd_model_campaign.xml').getroot().attrib['version']=='0.2.15'
    assert tool.findtext('requirements/container')==image
    assert {p.attrib['name'] for p in tool.findall('inputs/param')}=={'action','source_gpx','model_assets','model_request','model_request_b64','dispatch_key','preparation_evidence'}
    evidence=tool.find("inputs/param[@name='preparation_evidence']")
    assert evidence.attrib['optional']==evidence.attrib['multiple']=='true'
    assert tool.find("outputs/data[@name='preparation_certificate']").attrib['hidden']=='true'
    assert tool.find("inputs/param[@name='model_request']").attrib['optional']=='true'
    source=tool.find("inputs/param[@name='source_gpx']")
    assert set(source.attrib['format'].split(','))=={'binary','txt'}
    assert 'CIF' in source.attrib['label']
    result=tool.find('outputs/data[@name="result_bundle"]')
    assert result.attrib['label']=='RADAR-PD model ${dispatch_key} results'
    assert '&&' in tool.findtext('command') and '&amp;' not in tool.findtext('command')
    assert 'worker/verified_projects' in tool.find('outputs/collection/discover_datasets').attrib['directory']
    point_fits=tool.find("outputs/collection[@name='reviewable_projects']")
    assert 'review required' in point_fits.attrib['label']
    assert point_fits.find('discover_datasets').attrib['directory']=='worker/reviewable_projects'
    assert 'reviewable_' in point_fits.find('discover_datasets').attrib['pattern']
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


def future_tool(tmp_path):
    output=tmp_path/'future.xml'
    renderer.render('ghcr.io/lalityadav07/impurity_detection_gsas_ver6:models-'+'a'*40,output)
    return ET.parse(output).getroot()


@pytest.mark.parametrize('have_receipt',[False,True])
def test_provenance_config_uses_creating_job_metadata_and_literal_json(tmp_path,have_receipt):
    Template=pytest.importorskip('Cheetah.Template').Template
    from types import SimpleNamespace
    tool=future_tool(tmp_path)
    class Dataset:
        unsanitized=SimpleNamespace(creating_job=SimpleNamespace(tool_id='native-tool',tool_version='0.2.17',state='ok',
            stdout='not provenance\n[RADAR PREPARATION CERTIFICATE] '+'a'*64+'\n'),state='ok',deleted=False,purged=False)
        def __str__(self):return str(tmp_path/"literal' $(touch MUST_NOT_EXIST).json")
    row=Dataset()
    rendered=str(Template(tool.findtext("configfiles/configfile[@name='preparation_provenance']"),
        searchList=[dict(preparation_evidence=[row] if have_receipt else [])]))
    envelope=json.loads(rendered)
    assert envelope['schema']=='radar-galaxy-preparation-evidence/v1'
    if have_receipt:
        record=envelope['records'][0]
        assert record==dict(certificate_path=str(row),tool_id='native-tool',tool_version='0.2.17',job_state='ok',
            dataset_state='ok',dataset_deleted=False,dataset_purged=False,
            job_stdout='[RADAR PREPARATION CERTIFICATE] '+'a'*64)
    else:assert envelope['records']==[]
    assert not (tmp_path/'MUST_NOT_EXIST').exists()


@pytest.mark.parametrize('encoded',[True,False])
def test_future_command_passes_provenance_outside_request_and_announces_only_fixed_receipt(tmp_path,encoded):
    Template=pytest.importorskip('Cheetah.Template').Template
    tool=future_tool(tmp_path)
    decoder=tmp_path/'decode.py';decoder.write_text(tool.findtext("configfiles/configfile[@name='request_decoder']"))
    payload={'literal':"Fe' $(touch MUST_NOT_EXIST)"};data=json.dumps(payload)
    b64=base64.b64encode(data.encode()).decode()
    inline=tmp_path/'inline.txt';inline.write_text(b64)
    legacy=tmp_path/'legacy.json';legacy.write_text(data)
    provenance=tmp_path/'server.json';provenance.write_text('{"server":"owned"}')
    worker=tmp_path/'fake_worker.py'
    worker.write_text("import json,pathlib,sys\np=pathlib.Path\n"
        "assert p(sys.argv[sys.argv.index('--preparation-evidence')+1]).read_text()=='{\\\"server\\\":\\\"owned\\\"}'\n"
        "p(sys.argv[6]).write_text(json.dumps(json.loads(p(sys.argv[4]).read_text())))\n"
        "p(sys.argv[sys.argv.index('--preparation-certificate')+1]).write_text('{\\\"receipt\\\":true}')\n"
        "print('[RADAR PREPARATION CERTIFICATE] untrusted-scientific-output')\n")
    announce=tmp_path/'announce.py'
    announce.write_text("import hashlib,pathlib,sys\nprint('[RADAR PREPARATION CERTIFICATE] '+hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())\n")
    command=tool.findtext('command').replace('/opt/radar-symmetry/ndip_model_campaign.py',str(worker))
    command=command.replace('-m gpx_recipe.preparation.certificates',str(announce))
    result=tmp_path/'result.json';console=tmp_path/'console.txt';certificate=tmp_path/'certificate.json'
    rendered=str(Template(command,searchList=[dict(action='native',result_bundle=str(result),console_output=str(console),
        preparation_certificate=str(certificate),preparation_provenance=str(provenance),
        source_gpx='source.gpx',model_assets='assets.zip',model_request=None if encoded else str(legacy),
        model_request_b64=b64 if encoded else None,request_decoder=str(decoder),inline_request=str(inline))]))
    rendered=re.sub(r'(?m)^(\s*)python\s',lambda m:m[1]+shlex.quote(sys.executable)+' ',rendered)
    process=subprocess.run(['/bin/sh','-c',rendered],cwd=tmp_path,check=True,capture_output=True,text=True)
    assert json.loads(result.read_text())==payload and not (tmp_path/'MUST_NOT_EXIST').exists()
    import hashlib
    assert process.stdout=='[RADAR PREPARATION CERTIFICATE] '+hashlib.sha256(certificate.read_bytes()).hexdigest()+'\n'
    assert 'untrusted-scientific-output' in console.read_text() and 'untrusted-scientific-output' not in process.stdout
