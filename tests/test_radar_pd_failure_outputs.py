"""Exercise failed Analyze output collection after Galaxy-style rendering."""
import json
import os
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET
import zipfile

from Cheetah.Template import Template


TOOL = Path(__file__).parents[1] / 'tools/neutrons/powder_diffraction/radar_pd_analyze.xml'


def script(tmp_path):
    root = ET.parse(TOOL).getroot()
    path = tmp_path / 'finalize.py'
    path.write_text(str(Template(root.findtext("configfiles/configfile[@name='publish_failure_outputs']"))))
    return path


def test_failed_analysis_keeps_original_error_and_all_declared_outputs(tmp_path):
    portal = tmp_path / 'portal'; portal.mkdir()
    log = tmp_path / 'console.txt'
    log.write_text('ValueError: Instrument Gaussian variance is non-positive in fitted range\n'
                   '[FATAL] Main-phase refinement failed\n')
    for name in ('summary.json', 'state.json', 'results.zip'):
        (portal / name).touch()
    result = subprocess.run([sys.executable, str(script(tmp_path)), str(portal), str(log), '7'], capture_output=True)
    assert result.returncode == 0, result.stderr
    summary = json.loads((portal / 'summary.json').read_text())
    assert summary['$schema'] == 'radar-pd-result/v1' and summary['status'] == 'failed'
    assert any('Gaussian variance' in e['message'] for e in summary['errors'])
    assert json.loads((portal / 'state.json').read_text())['status'] == 'failed'
    assert json.loads((portal / 'pattern_observation.json').read_text()) == {}
    for name in ('input_manifest.json', 'gpx_index.json', 'resolved_config.yaml', 'overview.tsv', 'report.html'):
        assert (portal / name).stat().st_size > 0
    with zipfile.ZipFile(portal / 'results.zip') as z:
        assert 'Gaussian variance' in z.read('FAILURE.txt').decode()


def test_failure_does_not_overwrite_existing_scientific_evidence(tmp_path):
    portal = tmp_path / 'portal'; portal.mkdir()
    log = tmp_path / 'console.txt'; log.write_text('[ERROR] output conversion failed\n')
    evidence = {'pattern_observation.json': '{"existing":true}\n',
                'report.html': '<p>Existing scientific report</p>',
                'input_manifest.json': '{"source":"preserved"}'}
    for name, content in evidence.items(): (portal / name).write_text(content)
    subprocess.run([sys.executable, str(script(tmp_path)), str(portal), str(log), '1'], check=True)
    for name, content in evidence.items(): assert (portal / name).read_text() == content


def test_exit_trap_retains_nonzero_status_after_galaxy_flattens_command(tmp_path):
    root = ET.parse(TOOL).getroot(); command = root.findtext('command')
    fragment = command[command.index('radar_finalize()'):command.index('set -euo pipefail')]
    scope = dict(publish_failure_outputs=str(script(tmp_path)), console_output=str(tmp_path / 'console.txt'))
    rendered = str(Template(fragment, searchList=[scope]))
    flattened = ' '.join(line.strip() for line in rendered.splitlines())
    result = subprocess.run(['/bin/bash', '-c',
        'mkdir -p portal resolved_input && ' + flattened + ' (exit 23)'], cwd=tmp_path, capture_output=True,
        env={**os.environ, 'PATH': str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH','')})
    assert result.returncode == 23, result.stderr
    assert json.loads((tmp_path / 'portal/summary.json').read_text())['status'] == 'failed'
    assert (tmp_path / 'console.txt').stat().st_size > 0


def test_success_does_not_create_failure_outputs(tmp_path):
    portal=tmp_path/'portal'
    subprocess.run([sys.executable, str(script(tmp_path)), str(portal), str(tmp_path/'log'), '0'], check=True)
    assert not portal.exists()
