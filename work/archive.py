#!/usr/bin/env python3
# Author: Sean Pesce

"""
The classes in this file can be used to extract files from the *.archive files used by DXMD.
Extraction of files that span multiple archives is also supported.
"""

import logging
import os
import sys

from ctypes import c_byte, c_char, c_uint32, c_uint64
from ctypes_util import StructLE


# Maximum read size
READ_SIZE = 50 * 1024 * 1024  # 50MB


# @TODO: Convert code to use lib.file_util

class ArchiveString:
    # Size of the unsigned integer that stores the string length
    STR_LEN_WIDTH = 4

    def __init__(self, value=None, endianness='little', encoding='utf8'):
        self.endianness = endianness
        self.encoding = encoding
        self.value = value

    @classmethod
    def from_fd(cls, fd):
        s = ArchiveString()

        # Read string length
        data = fd.read(cls.STR_LEN_WIDTH)
        assert len(data) == cls.STR_LEN_WIDTH, f'Expected {cls.STR_LEN_WIDTH} bytes, received {len(data)}'
        str_len = int.from_bytes(data, s.endianness, signed=False)

        # Read string value
        data = fd.read(str_len)
        assert len(data) == str_len, f'Expected {str_len} bytes, received {len(data)}'
        s.value = data.decode(s.encoding)

        # Consume null terminator
        data = fd.read(1)
        assert data == b'\x00', f'Expected null terminator, received {data}'
        return s

    def __repr__(self):
        return f'{type(self).__name__}("{self.value}")'

    def __str__(self):
        return self.value

    def __bytes__(self):
        data = self.value.encode(self.encoding)
        data = len(self.value).to_bytes(ArchiveString.STR_LEN_WIDTH, self.endianness, signed=False) + data
        return data + b'\x00'



class FileChunk(StructLE):
    _fields_ = [
        ('archive', c_uint32),  # Archive link index (archive file containing this chunk)
        ('begin', c_uint64),    # Offset in original source file
        ('offset', c_uint64),   # Offset in archive file
        ('length', c_uint64),
    ]


class InnerFileHeader(StructLE):
    _fields_ = [
        ('timestamp', c_uint64),
        ('unk1', c_byte * 16),  # Some kind of hash?
    ]


class InnerFile:
    def __init__(self, endianness='little'):
        self.endianness = endianness
        self.header = None
        self._name = None
        self.chunk_count = None
        self.chunks = None

    @classmethod
    def from_fd(cls, fd):
        file = cls()

        data = fd.read(InnerFileHeader.sizeof())
        file.header = InnerFileHeader.from_bytes(data)

        file._name = ArchiveString.from_fd(fd)

        data = fd.read(4)
        assert len(data) == 4, f'Expected {4} bytes, received {len(data)}'
        file.chunk_count = int.from_bytes(data, file.endianness, signed=False)

        file.chunks = []
        for _ in range(0, file.chunk_count):
            read_sz = FileChunk.sizeof()
            data = fd.read(read_sz)
            assert len(data) == read_sz, f'Expected {read_sz} bytes, received {len(data)}'
            chunk = FileChunk.from_bytes(data)
            file.chunks.append(chunk)
        return file

    @property
    def total_size(self):
        sz = 0
        for c in self.chunks:
            sz += c.length
        return sz

    @property
    def name(self):
        return str(self._name)

    def __repr__(self):
        s = f'{type(self).__name__}\n{self.header}{self.name=}\n{self.total_size=}\n{self.chunk_count=}\nself.chunks=\n'
        for c in self.chunks:
            s += f'  {c}'.replace('\n', '\n  ')
        return s

    def __bytes__(self):
        data = bytes(self.header) + bytes(self._name) + self.chunk_count.to_bytes(4, self.endianness, signed=False)
        for c in self.chunks:
            data += bytes(c)
        return data



class ArchiveHeader(StructLE):
    _fields_ = [
        ('magic', c_char * 4),
        ('unk1', c_uint32),  # version ID?
        ('file_count', c_uint32),
        ('link_count', c_uint32),  # References to archive files
        ('dir_offset', c_uint64),  # Offset of inner file/chunk mapping section
    ]
    
    def validate(self):
        if self.magic != b'ARCH':
            raise ValueError(f'Unrecognized magic bytes: {self.magic}')
        return


class ArchiveFile:
    def __init__(self, file_path):
        self.fpath = file_path
        self.fd = None
        self.fsize = None
        self.header = None
        self.links = None
        self.linked_archives = None
        self.files = None
        self.parse()
    
    
    def parse(self):
        if self.fpath is None:
            return

        logging.info(f'Parsing {self.fpath}')
        self.fsize = os.path.getsize(self.fpath)
        self.links = []
        self.files = {}
        self.linked_archives = {}

        # Initialize file descriptor
        if self.fd is not None:
            self.fd.close()
        self.fd = open(self.fpath, 'rb')
        
        data = self.fd.read(ArchiveHeader.sizeof())
        self.header = ArchiveHeader.from_bytes(data)

        self.fd.seek(self.header.dir_offset)

        # Parse linked archives
        for _ in range(0, self.header.link_count):
            s = ArchiveString.from_fd(self.fd)
            self.links.append(s)

        # Parse linked archives
        logging.info(f'Linked archives: {self.links}\n')
        full_path = os.path.abspath(self.fpath)
        archive_dir = os.path.dirname(full_path)
        for link in self.links:
            linked_archive_path = os.path.abspath(os.path.join(archive_dir, str(link)))
            if linked_archive_path == full_path:
                self.linked_archives[str(link)] = self
                continue
            # Parse archives that are a dependency of this archive
            linked_archive = self.__class__(linked_archive_path)
            self.linked_archives[str(link)] = linked_archive

        # Parse inner files
        for _ in range(0, self.header.file_count):
            inner_file = InnerFile.from_fd(self.fd)

            assert inner_file.name != '', f'Encountered archived file at offset: {self.fd.tell():#x}'
            assert inner_file.name not in self.files, f'Duplicate archived file: {inner_file.name}'

            self.files[inner_file.name] = inner_file
            logging.debug(inner_file)

        # Check for trailing data
        final_offset = self.fd.tell()
        trailing_data = self.fd.read()
        assert len(trailing_data) == 0, f'{len(trailing_data)} bytes of unknown data starting at offset {final_offset:#x}'


    def extract(self, inner_fname, outdir=''):
        inner_file = self.files[inner_fname]
        extract_fpath = os.path.join(outdir, inner_file.name)

        logging.info(f'Extracting {extract_fpath}')
        with open(extract_fpath, 'wb') as f_out:
            last_end = 0
            for chunk in inner_file.chunks:
                # Check that chunks are contiguous and in-order
                assert chunk.begin == last_end, f'Out-of-order chunks found but not supported. Contact the developer.'
                last_end = chunk.begin + chunk.length

                # Obtain handle to the archive file containing the chunk data
                container = self.linked_archives[str(self.links[chunk.archive])]

                # Save current file offset
                saved_fp = container.fd.tell()

                # Read and write data
                container.fd.seek(chunk.offset)
                remaining = chunk.length
                while remaining > 0:
                    read_sz = remaining
                    if read_sz > READ_SIZE:
                        read_sz = READ_SIZE

                    data = container.fd.read(read_sz)
                    assert len(data) == read_sz, f'Expected {read_sz} bytes, received {len(data)}'

                    n_written = f_out.write(data)
                    assert n_written == read_sz, f'Expected to write {read_sz} bytes, but wrote {n_written}'

                    remaining -= read_sz

                # Restore current file offset
                container.fd.seek(saved_fp)
                assert container.fd.tell() == saved_fp, f'Bad file pointer offset: {container.fd.tell():#x}'
        return


    def extract_all(self, outdir=''):
        for f in self.files:
            self.extract(f, outdir)
        return


    def list(self):
        for f in self.files:
            print(f)
        return


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage:\n  {sys.argv[0]} <archive file> [output directory] [-v]')
        sys.exit()

    if '-v' in sys.argv:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
        
    OUT_DIR = ''
    if len(sys.argv) > 2 and not sys.argv[2].startswith('-'):
        OUT_DIR = sys.argv[2]
    
    ARCHIVE_FPATH = sys.argv[1]

    archive = ArchiveFile(ARCHIVE_FPATH)
    
    if '-l' in sys.argv or '--list' in sys.argv:
        archive.list()
        sys.exit()
    
    archive.extract_all(OUT_DIR)
