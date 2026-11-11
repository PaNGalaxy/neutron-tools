"""Activate the worker definition only after its immutable image has passed CI."""
import argparse
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def render(image,output,*,tool='model_campaign'):
    if not re.fullmatch(r'ghcr\.io/lalityadav07/impurity_detection_gsas_ver6:(?:models-[a-f0-9]{40})|ghcr\.io/lalityadav07/impurity_detection_gsas_ver6@sha256:[a-f0-9]{64}',image):
        raise ValueError('Use the successful models full-commit tag or registry digest')
    if tool not in {'model_campaign','live_snapshot'}:
        raise ValueError('Choose the reviewed Model Campaign or Live Snapshot template')
    directory=Path(__file__).resolve().parents[1]/'templates'
    template=directory/f'radar_pd_{tool}.xml.in'
    text=template.read_text().replace('@IMMUTABLE_MODELS_IMAGE@',image)
    text=text.replace('@PREPARATION_PROVENANCE@',
                      (directory/'radar_pd_preparation_provenance.xml.in').read_text().rstrip())
    if '@IMMUTABLE_' in text or '@PREPARATION_' in text:
        raise ValueError('An unresolved deployment placeholder remains')
    ET.fromstring(text)
    output=Path(output)
    if output.is_symlink():raise ValueError('Refusing a symlinked tool definition')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(text)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('image');p.add_argument('output')
    p.add_argument('--tool',choices=['model_campaign','live_snapshot'],default='model_campaign')
    a=p.parse_args();render(a.image,a.output,tool=a.tool)
