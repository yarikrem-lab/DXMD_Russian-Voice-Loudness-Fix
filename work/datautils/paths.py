import hashlib

# DX:MD function ZResourceID::IsLibraryResource
def is_library_resource(path):
    path = path.lower()
    return "resourcelib?" in path or "securelib?" in path

# DX:MD function ZResourceID::IsLibrary
def is_library(path):
    path = path.lower()
    return path.endswith("resourcelib") or path.endswith("securelib")

def skip_parens(start, end, string):
    paren_count = 0
    for i in range(len(string)):
        if string[i] == start: paren_count += 1
        if string[i] == end: paren_count -= 1
        if paren_count == 0: return string[i+1:]
    raise Exception("Parentheses unbalanced!")

# Roughly DX:MD function ZResourceID::GetDerivedEndIndex
def get_suffix(path):
    return skip_parens("(", ")",
            skip_parens("[", "]", path))

# DX:MD function ZResourceID::GetRoot
def get_root(path):
    if "?" in get_suffix(path):
        return path[:path.find("?")]
    else:
        return path

# DX:MD function ZResourceID::GetIndexInLibrary
def get_index_in_library(path):
    suff = get_suffix(path)
    if "?" in suff:
        postqm = suff[:suff.find("?")]
        if "." in postqm:
            num = postqm[:postqm.find(".")]
            if num.isnumeric():
                return int(num)
    return -1

def resid_hash(path):
    path = path.lower()
    md5 = list(hashlib.md5(path.encode()).digest())
    #for i in range(8):
        #md5[i] = (md5[i] << 8*(7-i)) & 0xFF
    #return int.from_bytes(md5[8:], "little")
    return ((md5[0] << 0x38) |
            (md5[1] << 0x30) |
            (md5[2] << 0x28) |
            (md5[3] << 0x20) |
            (md5[4] << 0x18) |
            (md5[5] << 0x10) |
            (md5[6] << 0x08) |
            (md5[7] << 0x00))

# Roughly DX:MD function ZRuntimeResourceID::QueryRuntimeResourceID
def get_resid(path):
    path = path.lower()
    if is_library_resource(path):
        base = resid_hash(get_root(path))
        index = get_index_in_library(path)
        return base | ((index & 0xFFFFFF) << 0x20) | 0x8000000000000000
    else:
        if is_library(path):
            return (resid_hash(path) & 0xFFFFFFFF) | 0x4000000000000000
        else:
            return resid_hash(path) & 0xFFFFFFFFFFFFFF

def get_lib_id(resid):
    if resid | 0x8000000000000000 == 0:
        raise Exception("Invalid container-index resource ID")
    return (resid & 0xFFFFFFFF) | 0x4000000000000000

def get_container_filename(path):
    path = path.lower()
    suffix = get_suffix(path)
    if "." in suffix:
        pre_suffix = path[:-len(suffix)]
        pre_dot = path[:len(pre_suffix) + suffix.find(".")]
        ext = path[len(pre_suffix) + suffix.find("."):]
        md5 = hashlib.md5((pre_dot + ".").encode()).hexdigest().upper()
        return md5 + ext
    else:
        return hashlib.md5(path.encode()).hexdigest().upper()
