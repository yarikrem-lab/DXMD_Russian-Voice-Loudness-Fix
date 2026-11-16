#!/usr/bin/env python3
import sys
import pathlib
import structs
import paths
import archive

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <headerlib> <destdir>", file=sys.stderr)
        sys.exit(1)
    hlib_file = pathlib.Path(sys.argv[1])
    arch_files = hlib_file.parent.glob("*.archive")
    destdir = pathlib.Path(sys.argv[2])
    destdir.mkdir(parents=True, exist_ok=True)

    HLIB = structs.HLIB.compile()
    hlib = HLIB.parse_file(hlib_file)
    #HLIBInner = structs.HLIBInner.compile()
    # Compiling HLIBInner seems to break parsing :(
    HLIBInner = structs.HLIBInner
    hlib_inner = HLIBInner.parse(hlib.bin1.inner)
    ARCH = structs.ARCH.compile()
    archs = [ARCH.parse_stream(open(f, "rb")) for f in arch_files]

    container_by_id = {
            paths.get_resid(c.path1.string): c
            for c in hlib_inner.resource_containers.arr}
    res_by_lib = {}

    for res in hlib_inner.resources.inner.resources:
        lib_rid = paths.get_lib_id(res.container_id)

        if lib_rid in res_by_lib:
            res_by_lib[lib_rid].append(res)
        else:
            res_by_lib[lib_rid] = [res]

    for lib_rid, ress in res_by_lib.items():
        container = container_by_id[lib_rid]
        cfname = paths.get_container_filename(container.path1.string)
        print("---", cfname)
        for arch in archs:
            for f in arch.metadata.files:
                if f.name.string != cfname: continue
                offset = container.extra_header_len + 24
                for i, res in enumerate(ress):
                    header = container.resource_headers.arr[i].inner
                    if container.flags & (1 << 2) > 0:
                        length = header.length + 24
                        data = b""
                    else:
                        length = header.length
                        data = structs.ResourceHeader.build(header)

                    rid = paths.get_resid(res.path1.string)
                    filename = hex(rid)[2:].rjust(16, "0")
                    print(f"{res.path1.string} -> {filename}")
                    data += archive.read_from_arch(arch, f, offset, length)
                    (destdir / filename).write_bytes(data)

                    offset += length

                #for i, res in enumerate(ress):
                #    print("D1", res.path1.string, f.parts[i])
