#!/usr/bin/env python3
import sys
import pathlib
import structs
import paths

def print_resid(path, id):
    print(hex(id)[2:].rjust(16, "0"), path, sep="\t")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <game data dir>", file=sys.stderr)
        sys.exit(1)

    datadir = pathlib.Path(sys.argv[1])

    namemap = {}

    for hlib_path in datadir.glob("**/*.pc_headerlib"):
        hlib = structs.HLIB.parse_file(hlib_path)
        hlib_inner = structs.HLIBInner.parse(hlib.bin1.inner)
        for res_container in hlib_inner.resource_containers.arr:
            path = res_container.path1.string
            namemap[paths.get_resid(path)] = path
        for ext_res in hlib_inner.external_resources.arr or []:
            path = ext_res.string
            namemap[paths.get_resid(path)] = path
        for res in hlib_inner.resources.inner.resources:
            namemap[res.resource_id] = res.path1.string

    for (id, path) in namemap.items():
        print_resid(path, id)
