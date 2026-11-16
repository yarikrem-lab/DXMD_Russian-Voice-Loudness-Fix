#!/usr/bin/env python3
import sys
import structs

path = sys.argv[1]
af = open(path, "rb")
a = structs.ARCH.parse_stream(af)
for f in a.metadata.files:
    if f.name.string == sys.argv[2]:
        for p in f.parts:
            af.seek(p.offset_global)
            sys.stdout.buffer.write(af.read(p.data_len))
