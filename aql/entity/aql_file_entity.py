#
# Copyright (c) 2014-2015 The developers of Aqualid project
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom
# the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
#  OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import os

from .aql_entity import EntityBase
from .aql_entity_pickler import pickleable

from aql.utils import file_signature, file_time_signature

__all__ = (
    'FileEntityBase',
    'FileChecksumEntity',
    'FilePartChecksumEntity',
    'FileTimestampEntity',
    'DirEntity',
)

# ==============================================================================


class ErrorFileEntityNoName(Exception):

    def __init__(self):
        msg = "Filename is not specified"
        super(ErrorFileEntityNoName, self).__init__(msg)


# ==============================================================================
class FileEntityBase (EntityBase):

    def __new__(cls, name, signature=NotImplemented, tags=None):

        if isinstance(name, FileEntityBase):
            name = name.name
        else:
            if isinstance(name, EntityBase):
                name = name.get()

        if not name:
            raise ErrorFileEntityNoName()

        name = os.path.normcase(os.path.abspath(name))

        self = super(FileEntityBase, cls).__new__(cls, name,
                                                  signature, tags=tags)
        return self

    # -----------------------------------------------------------

    def get(self):
        return self.name

    # -----------------------------------------------------------

    def __getnewargs__(self):
        tags = self.tags
        if not tags:
            tags = None

        return self.name, self.signature, tags

    # -----------------------------------------------------------

    def remove(self):
        try:
            os.remove(self.name)
        except OSError:
            pass

    # -----------------------------------------------------------

    def get_actual(self):
        signature = self.get_signature()
        if self.signature == signature:
            return self

        other = super(FileEntityBase, self).__new__(self.__class__,
                                                    self.name,
                                                    signature,
                                                    self.tags)
        other.id = self.id
        return other

    # -----------------------------------------------------------

    def is_actual(self):
        if not self.signature:
            return False

        if self.signature == self.get_signature():
            return True

        return False


# ==============================================================================
def _get_file_checksum(path, offset=0):
    try:
        signature = file_signature(path, offset)
    except (OSError, IOError):
        try:
            signature = file_time_signature(path)
        except (OSError, IOError):
            return None

    return signature


# ==============================================================================
def _get_file_timestamp(path):
    try:
        signature = file_time_signature(path)
    except (OSError, IOError):
        return None

    return signature


# ==============================================================================
@pickleable
class FileChecksumEntity(FileEntityBase):
    def get_signature(self):
        return _get_file_checksum(self.name)


# ==============================================================================
@pickleable
class FileTimestampEntity(FileEntityBase):
    def get_signature(self):
        return _get_file_timestamp(self.name)


# ==============================================================================
@pickleable
class DirEntity (FileTimestampEntity):
    def remove(self):
        try:
            os.rmdir(self.name)
        except OSError:
            pass


# ==============================================================================
@pickleable
class FilePartChecksumEntity (FileEntityBase):
    __slots__ = ('offset',)

    def __new__(cls, name, signature=NotImplemented, tags=None, offset=0):

        self = super(FilePartChecksumEntity, cls).__new__(cls,
                                                          name,
                                                          signature,
                                                          tags=tags)
        self.offset = offset
        return self

    # -----------------------------------------------------------

    def __getnewargs__(self):
        tags = self.tags
        if not tags:
            tags = None

        return self.name, self.signature, tags, self.offset

    # -----------------------------------------------------------

    def get_signature(self):
        return _get_file_checksum(self.name, self.offset)

    # ----------------------------------------------------------

    def get_actual(self):
        signature = self.get_signature()
        if self.signature == signature:
            return self

        other = super(FileEntityBase, self).__new__(self.__class__,
                                                    self.name,
                                                    signature,
                                                    self.tags)
        other.id = self.id
        other.offset = self.offset
        return other

    # ----------------------------------------------------------

    def __eq__(self, other):
        return super(FilePartChecksumEntity, self).__eq__(other) and \
            (self.offset == other.offset)
