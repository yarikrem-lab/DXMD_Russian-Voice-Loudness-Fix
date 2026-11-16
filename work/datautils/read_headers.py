#!/usr/bin/env python3
import sys
import pickle
import pathlib
from collections import namedtuple
import structs
import paths
import archive

HLIB = structs.HLIB.compile()
# Compiling HLIBInner seems to break parsing :(
HLIBInner = structs.HLIBInner

Resource = namedtuple("Resource", [
    "path", "container_id", "offset", "length", "header"])

def respath_to_fs_path(respath):
    if respath == "":
        return []
    if respath[0] == "[":
        after_parens = paths.skip_parens("[", "]", respath)
        inner_end = len(respath) - len(after_parens) - 1
        inner = respath[1:inner_end]
        return respath_to_fs_path(inner) + respath_to_fs_path(after_parens)
    if respath[0] == "(":
        after_parens = paths.skip_parens("(", ")", respath)
        inner_end = len(respath) - len(after_parens) - 1
        inner = respath[1:inner_end]
        return respath_to_fs_path(inner) + respath_to_fs_path(after_parens)
    else:
        return respath.split("/")

def create_nodes(resources_by_path):
    root = archive.DirectoryNode("/", {})
    for path, res in resources_by_path.items():
        d = root
        for elem in path[:-1]:
            if elem not in d.children:
                d.children[elem] = archive.DirectoryNode(elem, {})
            d = d.children[elem]
        d.children[path[-1]] = archive.ResourceNode(
            filename=path[-1],
            container_id=res.container_id,
            offset=res.offset,
            length=res.length,
            header=res.header)
    return root

def process_hlib(hlib_file):
    hlib = HLIB.parse_file(hlib_file)
    hlib_inner = HLIBInner.parse(hlib.bin1.inner)


    containers_by_id = {
            paths.get_resid(c.path1.string): c
            for c in hlib_inner.resource_containers.arr}

    res_by_lib = {}

    for res in hlib_inner.resources.inner.resources:
        lib_rid = paths.get_lib_id(res.container_id)

        if lib_rid in res_by_lib:
            res_by_lib[lib_rid].append(res)
        else:
            res_by_lib[lib_rid] = [res]

    resources = []
    for lib_rid, ress in res_by_lib.items():
        container = containers_by_id[lib_rid]
        # +24 -- skip the headerlib's own embedded header
        offset = container.extra_header_len + 24
        for i, res in enumerate(ress):
            header = container.resource_headers.arr[i].inner
            if container.flags & (1 << 2) > 0:
                # TODO
                length = header.length + 24
                #length = header.length
                header_bytes = b""
            else:
                length = header.length
                header_bytes = structs.ResourceHeader.build(header)

            resources.append(Resource(
                path = res.path1.string,
                container_id = lib_rid,
                offset = offset,
                length = length,
                header = header_bytes,
            ))

            offset += length


    container_name_by_id = {
            paths.get_resid(c.path1.string):
                paths.get_container_filename(c.path1.string)
            for c in hlib_inner.resource_containers.arr}

    return (container_name_by_id, resources)

def process_hlibs(datadir):
    paths_seen = set()
    resources_by_path = {}
    container_name_by_id = {}
    for hlib_file in datadir.glob("**/*.pc_headerlib"):
        cnbi, ress = process_hlib(hlib_file)
        container_name_by_id.update(cnbi)
        for res in ress:
            if res.path in paths_seen: continue
            paths_seen.add(res.path)

            path = tuple(respath_to_fs_path(res.path))
            resources_by_path[path] = archive.ResourceNode(
                filename = path[-1],
                container_id = res.container_id,
                offset = res.offset,
                length = res.length,
                header = res.header,
            )

    resources = create_nodes(resources_by_path)
    return archive.Metadata(container_name_by_id, resources)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <game data dir> <outfile>", file=sys.stderr)
        sys.exit(1)

    datadir = pathlib.Path(sys.argv[1])
    outfile = pathlib.Path(sys.argv[2])

    data = process_hlibs(datadir)
    pickle.dump(data, open(outfile, "wb"))
