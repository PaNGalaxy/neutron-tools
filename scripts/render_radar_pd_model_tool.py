"""Activate the worker definition only after its immutable image has passed CI."""
import argparse
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def render(image,output):
    if not re.fullmatch(r'ghcr\.io/lalityadav07/impurity_detection_gsas_ver6:(?:models-[a-f0-9]{40})|ghcr\.io/lalityadav07/impurity_detection_gsas_ver6@sha256:[a-f0-9]{64}',image):
        raise ValueError('Use the successful models full-commit tag or registry digest')
    template=Path(__file__).resolve().parents[1]/'templates/radar_pd_model_campaign.xml.in'
    text=template.read_text().replace('@IMMUTABLE_MODEL_IMAGE@',image)
    ET.fromstring(text)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(text)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('image');p.add_argument('output');a=p.parse_args();render(a.image,a.output)
