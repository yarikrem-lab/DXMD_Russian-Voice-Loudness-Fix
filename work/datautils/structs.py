from construct import *

# Inspired by https://zenhax.com/viewtopic.php?t=3193
# Huge thanks to SirKane for letting me look at his code, which many parts of
# this are based on

# Filename list at the end (before BIN1.reslist)
EndFileNameList = Struct(
    filenames_len = Int32ul,
    filenames = RepeatUntil(obj_.index == this.filenames_len - 1, Struct(
        unk1 = Int32ul, # Same for all (?),
        index = Int16ul,
        unk2 = Int16ul,
        unk3 = Int64ul,
        name_len = Int32ul,
        name = Int32ul,
        unk4 = Const(b"\x00"*6),
    ))
)

def ResourceListItem(offset_base):
    return Struct(
        offset = Int64ul, # Offset in BIN1 + something, not in file
        length1 = Int32ul,
        length2 = Int32ul,
        # length1 often == length2, sometimes the MSB is different on length1.
        # TODO: more data samples
        data = If(this.offset != 0xFFFFFFFFFFFFFFFF,
                  Pointer(lambda obj: offset_base(obj._) + obj.offset, Struct(
                      length = Int32ul,
                      data = Aligned(4, Bytes(this.length))))),
    )

def ResourceList(offset_base):
    return Struct(
        res_len = Int32ul,
        res_metadata = Array(this.res_len,
                             ResourceListItem(lambda obj: offset_base(obj._._))),
    )

# Often prepended by 0x18, which is the header length and some other data,
# a small 1-item ResourceList for "all\0"
# 0300 0040 0400 0000 0400 0000 616c 6c00 1800 0000
RLIB = Struct(
    magic = Const(b"BILR"), # "RLIB" -- ResourceLibrary
    unk1 = Const(b"\x00"*8),
    unk2 = Int32ul,
    unk3 = Int64ul,
    res_list = ResourceList(0),
)

RelocationsList = Struct(
    offsets_len = Int32ul,
    offsets = Array(this.offsets_len, Int32ul)
)

BIN1 = Struct(
    magic = Const(b"BIN1"),
    unk1 = Int16ul,
    initialiser_count = Int8ul,
    unk2 = Int8ul,
    inner_len = Int32ub, # XXX: Big endian? Why?
    unk3 = Int32ul,
    offset_base = Tell,
    inner = Bytes(this.inner_len),
    initialiser_tags = Pointer(this.offset_base + this.inner_len, Struct(
        # TODO: 0x12EBA5ED (REBASED?)
        tag = Int32ul,
        data_len = Int32ul,
        data = Switch(this.tag, {
            0x12EBA5ED: RelocationsList,
        }, default=Bytes(this.data_len)),
    )),
)

def Arr(inner_type):
    return Struct(
        arr_ptr = Int64ul,
        arr_len = Int32ul,
        capacity = Int32ul,
        arr = If(this.arr_len > 0,
            Pointer(this.arr_ptr, Array(this.arr_len, inner_type))),
    )

ByteString = Struct(
    str_ptr = Int64ul,
    str_len_flags = Int32ul,
    str_len = Computed(this.str_len_flags & (2**30-1)),
    capacity = Int32ul,
    string = If((this.str_len > 0) & (this.str_ptr != (1<<64)-1),
        Pointer(this.str_ptr, Bytes(this.str_len))),
)

String = Struct(
    str_ptr = Int64ul,
    str_len_flags = Int32ul,
    str_len = Computed(this.str_len_flags & (2**30-1)),
    capacity = Int32ul,
    string = If((this.str_len > 0) & (this.str_ptr != (1<<64)-1),
        Pointer(this.str_ptr, PaddedString(this.str_len, "utf8")))
)

# Null-byte terminated Pascal string
PStringNBT = Struct(
    string = PascalString(Int32ul, "utf8"),
    null_byte = Const(b"\x00"),
)

ResourceHeader = Struct(
    fourcc = Bytes(4),
    header_len = Int32ul,
    unk1 = Int32ul,
    length = Int32ul,
    unk2 = Int64ul,
)

ResourceHeaderContainer = Struct(
    inner_ptr = Int64ul,
    inner_len = Int32ul,
    capacity = Int32ul,
    inner = Pointer(this.inner_ptr, ResourceHeader)
)

ResourceContainer = Struct(
    path1 = String,
    path2 = String,
    extra_header_len = Int32ul,
    unk1 = Const(b"\x00"*4),
    data_len = Int64ul,
    flags = Int64ul,
    locale_ids = Arr(String),
    locale_type = Int64ul,
    stream_group_ids = Arr(Int32ul),
    unk3 = Int32ul,
    unk4 = Int32ul,
    unk5 = Int32ul,
    unk6 = Int32ul,
    lib_header = ResourceHeaderContainer,
    resource_headers = Arr(ResourceHeaderContainer),
    remap_index = Arr(Int32ul),
    remap_resid = Arr(Int64ul),
)

ResourceList = Struct(
    inner_ptr = Int64ul,
    inner_len = Int32ul,
    capacity = Int32ul,
    inner = Pointer(this.inner_ptr, Struct(
        resources_len = Int32ul,
        resources = Array(this.resources_len, Struct(
            container_id = Int64ul,
            resource_id = Int64ul,
            path1 = PStringNBT,
            path2 = PStringNBT,
        )),
    )),
)

HLIBInner = Struct(
    stream_groups = Arr(String),
    resource_containers = Arr(ResourceContainer),
    external_resources = Arr(String),
    entity_resid = Int64ul,
    unk1 = Int64ul,
    resources = ResourceList,
    unk2 = String,
    unk3 = Arr(Int32ul),
    unk4 = Int32ul,
    unk5 = Int32ul,
    unk6 = Int64ul,
)

HLIBExtraHeader = Struct(
    pos = Tell,
    entries_len = Int32ul,
    unk1 = Int32ul,
    # I don't understand what this does and there are only two options in the
    # game's files. TODO
    unk2 = Switch(this.entries_len, {
        1: Struct(
            unk1 = Const(bytes([0x10,0,0,0, 0x14,0,0,0])),
            unk2 = Int32ul,
            path = CString("utf8"),
        ),
        2: Struct(
            unk1 = Int32ul,
            unk2 = Const(bytes([0x14,0,0,0, 0x1c,0,0,0, 0,0,0,0x1])),
            path1_len = Int32ul,
            path1 = CString("utf8"),
            path2 = CString("utf8"),
        ),
    }),
)

# TODO: Allow for big-endinan version
HLIB = Struct(
    magic = Const(b"BILH"), # "HLIB" -- "HeaderLibrary"
    header_len = Int32ul,
    unk1 = Int32ul,
    length = Int32ul,
    unk2 = Const(bytes([0xFF]*8)),
    header = If(this.header_len > 0, HLIBExtraHeader),
    bin1 = BIN1,
)

ArchiveFilePart = Struct(
    # Each part can be saved in a different file. Look at
    # ARCH.metadata.containing_files[containing_file] to see the filename
    containing_file = Int32ul,
    offset_local = Int64ul,
    offset_global = Int64ul,
    data_len = Int64ul,
)

ArchiveFile = Struct(
    # Luigi A.'s script says this should be a timestamp, but I don't
    # know how to get the time out of it
    file_stamp = Int64ul,
    unk1 = Int64ul,
    unk2 = Int64ul,
    name = PStringNBT,
    parts_len = Int32ul,
    parts = ArchiveFilePart[this.parts_len],
)

# Based on aluigi.org/bms/deus_ex_mankind_divided.bms
ARCH = Struct(
    magic = Const(b"ARCH"),
    unk1 = Int32ul,
    files_len = Int32ul,
    containing_files_len = Int32ul,
    metadata_offset = Int64ul,
    metadata = Pointer(this.metadata_offset, Struct(
        containing_files = PStringNBT[this._.containing_files_len],
        files = ArchiveFile[this._.files_len],
    )),
)

TextureHeader = Struct(
    # This first int is actually handled by the Install() method, not by
    # ZTextureMap
    unk1 = Int32ul,
    total_size = Int32ul,
    flags = Int32ul,
    width = Int16ul,
    height = Int16ul,
    depth = Int16ul,
    format = Int16ul,
    num_mip_levels = Int8ul,
    default_mip_level = Int8ul,
    interpret_as = Int8ul,
    dimensions = Int8ul,
    mip_interpolation = Int8ul,
    unk2 = Bytes(3),
    ia_data_size = Int32ul,
    ia_data = Int32ul, # Offset relative to start of Texture
    # Raw texture data follows
)

CPPT = Struct(
    unk1 = Int64ul,
    unk2 = Int64ul,
    unk3 = Arr(Struct(
        unk1 = Int64ul,
        unk2 = Int64ul,
        unk3 = Int64ul,
    )),
)

TBLU = Struct(
    unk1 = Int32ul,
    unk2 = Int32ul,
    unk3 = Arr(Struct(
        unk1 = Int32ul,
        unk2 = Int32ul,
        unk3 = String,
        unk4 = ByteString[5], # TODO
        unk5 = Struct(
            str_ptr = Int64ul,
            unk1 = Int32ul,
            unk2 = Int32ul,
            inner = If(this.str_ptr != (1<<64)-1,
                Pointer(this.str_ptr_ptr, String))
        ),
        unk6 = Int64ul,
    )),
    unk4 = Arr(Bytes(16)),
    unk5 = Arr(Bytes(18)),
    unk6 = Arr(Bytes(16)),
)

TEMP = Struct( # Template
    unk1 = Int32ul,
    unk2 = Int32ul,
    unk3 = Int64ul,
    unk4 = Arr(Struct(
        unk1 = Int32ul,
        unk2 = Int32ul,
        unk3 = Arr(Bytes(24)),
        unk4 = Arr(Bytes(24)), #?
    )),
)
