"""The fixed launchers expose grants without exporting arbitrary environment data."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET

from Cheetah.Template import Template
import pytest

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'tools/neutrons/powder_diffraction'

def fixture_probe(tmp_path,name):
    tree=ET.parse(TOOLS/('radar_pd_'+name+'.xml')).getroot()
    source=tree.findtext("configfiles/configfile[@name='resource_probe']")
    assert source
    package=tmp_path/'gpx_recipe/symmetry';package.mkdir(parents=True)
    for folder in (package.parent,package): (folder/'__init__.py').touch()
    (package/'resources.py').write_text('def allocation(requested):\n    return {"requested_workers": requested}\n')
    probe=tmp_path/'resource probe.py';probe.write_text(source)
    env={**os.environ,'PYTHONPATH':str(tmp_path),'GALAXY_SLOTS':'4','GALAXY_MEMORY_MB':'8192','UNRELATED_SECRET':'not-for-the-log'}
    return tree,probe,env

@pytest.mark.parametrize('name',['library_builder','refine_recipe','live_snapshot'])
def test_fixed_probe_reports_only_grants_and_marks_capacity(tmp_path,name):
    tree,probe,env=fixture_probe(tmp_path,name)
    run=subprocess.run([sys.executable,str(probe)],env=env,capture_output=True,text=True,check=True)
    prefix='[RADAR RESOURCE ALLOCATION] '
    assert run.stdout.startswith(prefix) and 'not-for-the-log' not in run.stdout
    row=json.loads(run.stdout[len(prefix):])
    assert row['reported']=={'GALAXY_SLOTS':4,'GALAXY_MEMORY_MB':8192}
    assert row['capacity']=={'requested_workers':4}
    assert 'not a measurement of simultaneous CPU use' in row['scope']
    assert tree.findtext('command').count("python '$resource_probe'")==1

@pytest.mark.parametrize('cache',[None,'prior cache.zip'])
@pytest.mark.parametrize('worker_exit',[0,2])
def test_live_command_keeps_worker_arguments_and_both_logs(tmp_path,cache,worker_exit):
    tree,probe,env=fixture_probe(tmp_path,'live_snapshot')
    recorder=tmp_path/'fake worker.py'
    recorder.write_text('import json,os,pathlib,sys\npathlib.Path("arguments.json").write_text(json.dumps(sys.argv[1:]))\nprint("native-worker-log")\nsys.exit(int(os.environ["WORKER_EXIT"]))\n')
    values=dict(resource_probe=str(probe),packet='input packet.zip',result_bundle='result bundle.zip',
                response_cache_output='cache output.zip',console_output='console.txt',
                preparation_provenance='preparation evidence.json',response_cache=cache)
    command=tree.findtext('command').replace('python -m gpx_recipe.live.galaxy_worker','python '+shlex.quote(str(recorder)))
    rendered=str(Template(command,searchList=[values]))
    rendered=' '.join(line.strip() for line in rendered.split('\n')).replace('\r',' ').strip()
    rendered=rendered.replace('python ',shlex.quote(sys.executable)+' ')
    run=subprocess.run(['/bin/sh','-ec',rendered],cwd=tmp_path,env={**env,'WORKER_EXIT':str(worker_exit)},capture_output=True,text=True)
    expected=['input packet.zip','worker','result bundle.zip','cache output.zip','--preparation-evidence','preparation evidence.json']
    if cache:expected+=['--cache',cache]
    assert json.loads((tmp_path/'arguments.json').read_text())==expected
    assert run.returncode==worker_exit
    lines=(tmp_path/'console.txt').read_text().splitlines()
    assert lines[0].startswith('[RADAR RESOURCE ALLOCATION] ') and lines[-1]=='native-worker-log'
    assert not run.stdout

def test_live_generation_template_preserves_the_same_probe():
    a=ET.parse(TOOLS/'radar_pd_live_snapshot.xml').getroot()
    b=ET.parse(ROOT/'templates/radar_pd_live_snapshot.xml.in').getroot()
    assert a.findtext('command')==b.findtext('command')
    assert a.findtext("configfiles/configfile[@name='resource_probe']")==b.findtext("configfiles/configfile[@name='resource_probe']")
