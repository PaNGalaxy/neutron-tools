"""Live and Model tools render one creating-job provenance contract."""
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('model_tool_renderer',ROOT/'scripts/render_radar_pd_model_tool.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)


def tools(tmp_path):
    image='ghcr.io/lalityadav07/impurity_detection_gsas_ver6:models-'+'a'*40
    result={}
    for name in ('model_campaign','live_snapshot'):
        path=tmp_path/(name+'.xml');renderer.render(image,path,tool=name)
        result[name]=ET.parse(path).getroot()
    return result


def test_future_live_tool_keeps_origin_receipts_separate_and_shares_the_model_contract(tmp_path):
    rendered=tools(tmp_path);live=rendered['live_snapshot']
    assert live.attrib['id']=='neutrons_radar_pd_live_snapshot_prototype'
    assert live.attrib['version']=='0.1.4'
    evidence=live.find("inputs/param[@name='preparation_evidence']")
    assert evidence.attrib['format']=='json' and evidence.attrib['multiple']=='true' and evidence.attrib['optional']=='true'
    assert live.findtext("configfiles/configfile[@name='preparation_provenance']")==rendered['model_campaign'].findtext("configfiles/configfile[@name='preparation_provenance']")
    assert '--preparation-evidence' in live.findtext('command')
    assert ET.parse(ROOT/'tools/neutrons/powder_diffraction/radar_pd_live_snapshot.xml').getroot().attrib['version']=='0.1.3'


@pytest.mark.parametrize('with_cache',[False,True])
@pytest.mark.parametrize('with_origin',[False,True])
def test_real_live_cheetah_command_forwards_server_metadata_with_or_without_a_cache(tmp_path,with_cache,with_origin):
    Template=pytest.importorskip('Cheetah.Template').Template
    tool=tools(tmp_path)['live_snapshot']
    certificate=tmp_path/'native-receipt.json';certificate.write_text('{"native":"data only"}')
    class Dataset:
        unsanitized=SimpleNamespace(creating_job=SimpleNamespace(tool_id='neutrons_radar_pd_model_campaign_prototype',
            tool_version='0.2.17',state='ok',stdout='[RADAR PREPARATION CERTIFICATE] '+'a'*64),
            state='ok',deleted=False,purged=False)
        def __str__(self):return str(certificate)
    envelope=json.loads(str(Template(tool.findtext("configfiles/configfile[@name='preparation_provenance']"),
        searchList=[dict(preparation_evidence=[Dataset()] if with_origin else [])])))
    assert envelope['schema']=='radar-galaxy-preparation-evidence/v1'
    assert len(envelope['records'])==int(with_origin)
    if with_origin:
        assert envelope['records'][0]['certificate_path']==str(certificate)
        assert envelope['records'][0]['job_stdout']=='[RADAR PREPARATION CERTIFICATE] '+'a'*64
    provenance=tmp_path/'server.json';provenance.write_text(json.dumps(envelope))
    worker=tmp_path/'live_worker.py'
    worker.write_text("import argparse,json,pathlib\n"
        "p=argparse.ArgumentParser();p.add_argument('packet');p.add_argument('directory');p.add_argument('result');p.add_argument('output_cache');p.add_argument('--cache');p.add_argument('--preparation-evidence');a=p.parse_args()\n"
        "pathlib.Path(a.result).write_text(json.dumps(dict(packet=a.packet,cache=a.cache,evidence=json.loads(pathlib.Path(a.preparation_evidence).read_text()))))\n"
        "pathlib.Path(a.output_cache).write_bytes(b'checked cache')\n")
    result=tmp_path/'result.json';cache=tmp_path/'output-cache.zip'
    command=tool.findtext('command').replace('-m gpx_recipe.live.galaxy_worker',str(worker))
    rendered=str(Template(command,searchList=[dict(result_bundle=str(result),response_cache_output=str(cache),
        console_output=str(tmp_path/'console.txt'),packet='scientific-packet.zip',
        response_cache='previous-cache.zip' if with_cache else None,preparation_provenance=str(provenance))]))
    rendered=re.sub(r'(?m)^(\s*)python\s',lambda m:m[1]+shlex.quote(sys.executable)+' ',rendered)
    subprocess.run(['/bin/sh','-c',rendered],cwd=tmp_path,check=True)
    assert json.loads(result.read_text())==dict(packet='scientific-packet.zip',
        cache='previous-cache.zip' if with_cache else None,evidence=envelope)
    assert cache.read_bytes()==b'checked cache'


def test_renderer_rejects_unrecognized_tool_kind_before_creating_a_definition(tmp_path):
    with pytest.raises(ValueError,match='installed'):
        renderer.render('ghcr.io/lalityadav07/impurity_detection_gsas_ver6:models-'+'a'*40,
            tmp_path/'other.xml',tool='../arbitrary')
    assert not (tmp_path/'other.xml').exists()
