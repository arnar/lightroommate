# -*- encoding: utf-8 -*-
import os, struct

class LRPrevFile(object):

    def __init__(self, path):
        self._file = file(path)
        self._sections = list()
        self._section_idxs = dict()
        self._parse_headers()

    @property
    def sections(self):
        return [s["name"] for s in self._sections]

    def load(self, section_name):
        idx = self._section_idxs[section_name]
        hdr = self._sections[idx]
        f = self._file
        f.seek(hdr["offset"])
        data = f.read(hdr["length"])
        return data

    def section_info(self, section_name):
        return self._sections[self._section_idxs[section_name]]

    def close(self):
        self._file.close()

    def _parse_headers(self):
        f = self._file
        f.seek(0)
        i = 0

        while f.read(4) == "AgHg":
            (header_length,) = struct.unpack(">H", f.read(2))
            header = f.read(header_length - 6)
            (version, kind, length, padding) = struct.unpack(">BBQQ", header[:18])
            name = header[18:].split("\0")[0]
            self._sections.append(dict(
                name = name,
                length = length,
                version = version,
                kind = kind,
                offset = f.tell()))
            self._section_idxs[name] = i
            i += 1
            f.seek(length + padding, os.SEEK_CUR)
