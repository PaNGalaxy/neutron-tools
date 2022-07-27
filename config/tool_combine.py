#!/usr/bin/env python
import sys
from xml.etree import ElementTree as et
import argparse


class XMLCombiner(object):
    def __init__(self, filenames):
        assert len(filenames) > 0, 'No filenames!'
        # save all the roots, in order, to be processed later
        self.roots = [et.parse(f).getroot() for f in filenames]

    def combine(self):
        for r in self.roots[1:]:
            # combine each element with the first one, and update that
            self.combine_element(self.roots[0], r)
        # return the string representation
        return et.tostring(self.roots[0], encoding='utf8', method='xml')

    def combine_element(self, one, other):
        one_sections = one.findall("section")
        other_sections = other.findall("section")
        for other_section in other_sections:
            other_id = other_section.attrib['id']
            same_one_section = None
            for one_section in one_sections:
                if one_section.attrib['id'] == other_id:
                    same_one_section = one_section
            if same_one_section == None:
                one.append(other_section)
            else:
                one_tools = same_one_section.findall("tool")
                other_tools = other_section.findall("tool")
                for other_tool in other_tools:
                    other_file = other_tool.attrib['file']
                    tool_found = False
                    for one_tool in one_tools:
                        if one_tool.attrib['file'] == other_file:
                            tool_found = True
                    if not tool_found:
                        same_one_section.append(other_tool)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Merge ndip_tool_conf.xml from local directory with another tools file')
    parser.add_argument('tool_conf_file', type=str, nargs=1,
                        help='tool config xml file to merge with')
    parser.add_argument('--ndip-tools-dir', type=str, default='ndip_tools',
                        help='a folder with ndip tools')
    parser.add_argument('--ndip-tool-conf', type=str, default='ndip_tool_conf.xml',
                        help='a path to file with ndip tools')

    args = parser.parse_args()

    r = XMLCombiner([args.ndip_tool_conf, args.tool_conf_file[0]]).combine()

    print(r.decode().replace('file="ndip_tools', 'file="' + args.ndip_tools_dir))
