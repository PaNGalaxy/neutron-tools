"""Exercise both recipe transports through the actual wrapper templates."""

import base64
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/neutrons/powder_diffraction/radar_pd_refine_recipe.xml'


def decoder(tmp_path):
    tool = ET.parse(TOOL).getroot()
    script = tmp_path / 'decode.py'
    script.write_text(tool.findtext("configfiles/configfile[@name='request_decoder']"))
    return tool, script


def test_inline_recipe_preserves_legacy_contract_and_native_worker():
    tool = ET.parse(TOOL).getroot()
    assert tool.attrib['version'] == '0.3.11'
    params = {p.attrib['name']: p for p in tool.findall('inputs/param')}
    assert set(params) == {'action', 'source_gpx', 'recipe_request', 'recipe_request_b64', 'dispatch_key'}
    assert params['recipe_request'].attrib['optional'] == 'true'
    assert params['recipe_request'].attrib['format'] == 'json'
    assert params['recipe_request_b64'].attrib['optional'] == 'true'
    assert params['recipe_request_b64'].find('sanitizer') is None
    assert params['source_gpx'].attrib['format'] == 'binary'
    assert params['dispatch_key'].findtext('validator') == '^[a-f0-9]{24}$'
    assert '/opt/radar-pd/scripts/ndip_refinement.py' in tool.findtext('command')
    assert tool.find('outputs/collection/discover_datasets').attrib['pattern'] == r'verified_(?P<designation>.+)\.gpx'


@pytest.mark.parametrize('mode', ['inline', 'legacy', 'both', 'neither'])
def test_real_cheetah_command_selects_exactly_one_literal_request(tmp_path, mode):
    Template = pytest.importorskip('Cheetah.Template').Template
    tool, script = decoder(tmp_path)
    payload = {'plan': {'request': "La'\n$(touch NEVER); `touch ALSO_NEVER` α"},
               'approval': {'reviewed': True}, 'expected_source_sha256': 'a' * 64,
               'dispatch_key': 'b' * 24}
    raw = (json.dumps(payload, sort_keys=True, indent=2) + '\n').encode()
    b64 = base64.b64encode(raw).decode('ascii')
    assert re.fullmatch(tool.find("inputs/param[@name='recipe_request_b64']").findtext('validator'), b64)
    assert not re.fullmatch(tool.find("inputs/param[@name='recipe_request_b64']").findtext('validator'), '$(touch BAD)')
    inline = tmp_path / 'inline.txt'
    inline.write_text(str(Template(tool.findtext("configfiles/configfile[@name='inline_request']"),
                                   searchList=[{'recipe_request_b64': b64 if mode in {'inline', 'both'} else ''}])))
    legacy = tmp_path / 'legacy.json'
    legacy.write_bytes(raw)
    source = tmp_path / 'source.gpx'
    source.write_bytes(b'unchanged source bytes')
    worker = tmp_path / 'fake_worker.py'
    worker.write_text("from pathlib import Path\nimport sys\nPath('worker-called').touch()\nPath(sys.argv[5]).write_bytes(Path(sys.argv[3]).read_bytes())\n")
    result = tmp_path / 'result.json'
    command = tool.findtext('command').replace('/opt/radar-pd/scripts/ndip_refinement.py', str(worker))
    rendered = str(Template(command, searchList=[dict(
        action='run', source_gpx=str(source), result_bundle=str(result),
        console_output=str(tmp_path / 'console.txt'), request_decoder=str(script), inline_request=str(inline),
        recipe_request_b64=b64 if mode in {'inline', 'both'} else '',
        recipe_request=str(legacy) if mode in {'legacy', 'both'} else None)]))
    rendered = re.sub(r'(?m)^(\s*)python\s', lambda match: match[1] + shlex.quote(sys.executable) + ' ', rendered)
    assert 'touch NEVER' not in rendered
    run = subprocess.run(['/bin/sh', '-c', rendered], cwd=tmp_path, capture_output=True)
    assert source.read_bytes() == b'unchanged source bytes'
    assert not (tmp_path / 'NEVER').exists() and not (tmp_path / 'ALSO_NEVER').exists()
    if mode in {'inline', 'legacy'}:
        assert run.returncode == 0, run.stderr.decode()
        assert (tmp_path / 'worker-called').exists()
        assert result.read_bytes() == raw
    else:
        assert run.returncode != 0
        assert not (tmp_path / 'worker-called').exists()


@pytest.mark.parametrize('raw', [
    b'invalid$', base64.b64encode(b'[]'), base64.b64encode(b'{broken'),
    base64.b64encode(b'\xff'), b'A' * (6 * 1024 * 1024 + 1),
    base64.b64encode(json.dumps({'large': 'x' * (4 * 1024 * 1024)}).encode()),
], ids=['bad-base64', 'not-object', 'bad-json', 'bad-utf8', 'encoded-too-large', 'decoded-too-large'])
def test_bad_inline_request_cannot_reach_the_native_worker(tmp_path, raw):
    _, script = decoder(tmp_path)
    source = tmp_path / 'encoded.txt'
    source.write_bytes(raw)
    target = tmp_path / 'decoded.json'
    run = subprocess.run([sys.executable, str(script), str(source), str(target)], capture_output=True)
    assert run.returncode != 0 and not target.exists()


def test_decoder_does_not_replace_a_different_file_or_follow_a_symlink(tmp_path):
    _, script = decoder(tmp_path)
    source = tmp_path / 'encoded.txt'
    raw = b'{"plan":null}\n'
    source.write_bytes(base64.b64encode(raw))
    target = tmp_path / 'decoded.json'
    for _ in range(2):
        subprocess.run([sys.executable, str(script), str(source), str(target)], check=True)
        assert target.read_bytes() == raw
    target.write_bytes(b'other')
    assert subprocess.run([sys.executable, str(script), str(source), str(target)], capture_output=True).returncode != 0
    assert target.read_bytes() == b'other'
    target.unlink()
    original = tmp_path / 'original.json'
    original.write_bytes(b'preserved')
    target.symlink_to(original)
    assert subprocess.run([sys.executable, str(script), str(source), str(target)], capture_output=True).returncode != 0
    assert original.read_bytes() == b'preserved'
