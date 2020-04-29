#!/usr/bin/env nix-shell
#!nix-shell -i python3

import libfdt
import argparse
import struct
import os
import subprocess
import itertools
from collections import namedtuple

parser = argparse.ArgumentParser(description="List all modules required by a dtb")
parser.add_argument("--dtb", type=str, required=True, help="the dtb file to parse")
parser.add_argument("--modalias", type=str, required=True, help="the modules.alias file")
args = parser.parse_args()

device = namedtuple('device', 'name compatible')

def all_nodes(fdt):
    def go(parent_node_offset):
        yield parent_node_offset

        node_offset = fdt.first_subnode(
            parent_node_offset, quiet=[libfdt.FDT_ERR_NOTFOUND]
        )

        while True:
            if node_offset == -1:
                return

            yield from go(node_offset)

            node_offset = fdt.next_subnode(
                node_offset, quiet=[libfdt.FDT_ERR_NOTFOUND]
            )

    root_offset = fdt.path_offset('/')
    yield from go(root_offset)

def all_devices(fdt):
    for node_offset in all_nodes(fdt):
        prop = fdt.getprop(
            node_offset,
            'compatible',
            quiet=[libfdt.FDT_ERR_NOTFOUND]
        )
        if prop == -1:
            continue

        node_name = fdt.get_name(node_offset)
        prop_strings = [x.decode('utf-8') for x in prop.split(b'\0')[:-1]]
        yield device(node_name, prop_strings)

# TODO: this must be in the library somewhere
def lines(file):
    while True:
        line = file.readline()
        if line is None or line == '':
            return
        yield line.rstrip('\n')

def read_aliases(modalias_file):
    for line in lines(open(modalias_file, 'r')):
        terms = line.split(' ')
        if terms[0] == 'alias':
            yield terms[1], terms[2]

def index_modules_by_compatible(aliases):
    index=dict()
    for alias, module_name in aliases.items():
        if not alias.startswith('of:'):
            continue
        compatible = [ alias for alias in alias.split('C')[1:] if alias != '*' ]
        for c in compatible:
            index[c] = module_name
    return index

if __name__ == '__main__':
    fdt = libfdt.Fdt(open(args.dtb, 'rb').read())
    devices = list(all_devices(fdt))
    aliases = dict(read_aliases(args.modalias))

    index = index_modules_by_compatible(aliases)

    def match_module(expanded):
        device, compatible = expanded
        return index.get(compatible)

    requests = (
        [(device, compatible)
         for device in devices
         for compatible in device.compatible]
    )


    requests_matched = [request for request in requests if request[1] in index]
    devices_matched = set([request[0].name for request in requests_matched])

    print("[")
    print()
    for module_name, match in itertools.groupby(sorted(requests_matched, key=match_module), match_module):
        if module_name is None:
            continue
        for device, c in match:
            print(f"  # {device.name} compatible=\"{c}\"")
        print(f"  \"{module_name}\"")
        print()

    for d in devices:
        if d.name in devices_matched:
            continue
        print(f"  # unmatched #{d}")
    print("]")
