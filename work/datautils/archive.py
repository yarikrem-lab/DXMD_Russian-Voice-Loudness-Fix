import pathlib
from collections import namedtuple
import structs

ARCH = structs.ARCH.compile()

Metadata = namedtuple("Metadata", ["container_name_by_id", "resources"])
DirectoryNode = namedtuple("DirectoryNode", ["filename", "children"])
ResourceNode = namedtuple("ResourceNode", [
    "filename", "container_id", "offset", "length", "header"])

OpenedArchives = namedtuple("OpenedArchives", ["archives", "files_by_name"])

def read_archives(datadir):
    archives = []
    files_by_name = {}
    arch_files = list(pathlib.Path(datadir).glob("**/*.archive"))
    # Sometimes afiles are overridden by higher-numbered archive files. There
    # might be some field in the headers saying which .archive the resource is,
    # but I haven't found it and this seems to work
    arch_files.sort(reverse=True)
    for arch_path in arch_files:
        # We can't use parse_file, because we need the file alive for the
        # runtime of the program
        arch_file = open(arch_path, "rb")
        files_by_name[arch_path.name.lower()] = arch_file
        archives.append(ARCH.parse_stream(arch_file))
    return OpenedArchives(archives, files_by_name)

def read_from_arch(oas, arch, afile, offset, length):
    buf = b""
    for part in afile.parts:
        # Skip to starting part
        if part.offset_local + part.data_len < offset: continue
        offset_in_part = offset - part.offset_local
        len_to_read = length - len(buf)
        len_in_part = min(len_to_read, part.data_len - offset_in_part)

        filename = arch.metadata.containing_files[part.containing_file]
        f = oas.files_by_name[filename.string.lower()]
        f.seek(part.offset_global + offset_in_part)
        buf += f.read(len_in_part)

        if len(buf) == length: return buf

    print("Could not read enough for resource!")

def read_resource(oas, meta, resmeta):
    container_name = meta.container_name_by_id[resmeta.container_id]
    for arch in oas.archives:
        for afile in arch.metadata.files:
            if afile.name.string == container_name:
                data = read_from_arch(
                        oas, arch, afile, resmeta.offset, resmeta.length)
                #return resmeta.header + data
                return data
    print(f"Could not find {container_name}!")
