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
        one_sections = one.findall("table")
        other_sections = other.findall("table")
        for other_section in other_sections:
            other_id = other_section.attrib['name']
            same_one_section = None
            for one_section in one_sections:
                if one_section.attrib['name'] == other_id:
                    same_one_section = one_section
            if same_one_section == None:
                one.append(other_section)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Merge neutrons_tool_data_table_conf.xml from local directory with another table file')
    parser.add_argument('table_conf_file', type=str, nargs=1,
                        help='table config xml file to merge with')
    parser.add_argument('--neutrons-table-conf', type=str, default='neutrons_tool_data_table_conf.xml',
                        help='a path to file with neutrons tool data table')
    parser.add_argument('--dry-run', action=argparse.BooleanOptionalAction,
                        help='print output to screen ')

    args = parser.parse_args()

    r = XMLCombiner([args.neutrons_table_conf, args.table_conf_file[0]]).combine()
    if args.dry_run:
        print(r.decode())
    else:
        with open(args.table_conf_file[0], "w") as file:
            print(r.decode(), file=file)

