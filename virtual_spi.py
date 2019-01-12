#!/usr/bin/env python
from __future__ import print_function, absolute_import, division

import logging

from collections import defaultdict
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
from sys import argv, exit
from time import time
from six import binary_type

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context
import ctypes

_IOC_NRBITS =	8
_IOC_TYPEBITS =	8

_IOC_SIZEBITS =	14
_IOC_DIRBITS =	2

_IOC_NRMASK = (1 << _IOC_NRBITS) - 1
_IOC_TYPEMASK = (1 << _IOC_TYPEBITS) - 1
_IOC_SIZEMASK = (1 << _IOC_SIZEBITS) - 1
_IOC_DIRMASK = (1 << _IOC_DIRBITS) - 1

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT =	_IOC_SIZESHIFT + _IOC_SIZEBITS

# ...and for the drivers/sound files...
# Direction bits

_IOC_NONE = 0
_IOC_WRITE = 1
_IOC_READ = 2

IOC_IN = _IOC_WRITE << _IOC_DIRSHIFT
IOC_OUT = _IOC_READ << _IOC_DIRSHIFT
IOC_INOUT = (_IOC_WRITE|_IOC_READ) << _IOC_DIRSHIFT
IOCSIZE_MASK = _IOC_SIZEMASK << _IOC_SIZESHIFT
IOCSIZE_SHIFT = _IOC_SIZESHIFT



def _ioc(dir, typ, num, size):
    return (dir  << _IOC_DIRSHIFT) | \
           (typ << _IOC_TYPESHIFT) | \
           (num   << _IOC_NRSHIFT) | \
           (size << _IOC_SIZESHIFT)

def _ioc_typecheck(typ):
    return ctypes.sizeof(typ)


# used to create ioctl numbers

def _io(typ, num):
  return _ioc(_IOC_NONE, typ, num, 0)

def _ior(typ, num, size):
  return _ioc(_IOC_READ, typ, num, _ioc_typecheck(size))

def _iow(typ, num, size):
  return _ioc(_IOC_WRITE, typ, num, _ioc_typecheck(size))

def _iowr(typ, num, size):
  return _ioc(_IOC_READ|_IOC_WRITE, typ, num, _ioc_typecheck(size))

def _ior_bad(typ, num, size):
  return _ioc(_IOC_READ, typ, num, sizeof(size))

def _iow_bad(typ, num, size):
  return _ioc(_IOC_WRITE, typ, num, sizeof(size))

def _iowr_bad(typ, num, size):
  return _ioc(_IOC_READ|_IOC_WRITE, typ, num, sizeof(size))


####### SPI Definitions #######



SPI_CPHA = 0x01
SPI_CPOL = 0x02

SPI_MODE_0 = 0
SPI_MODE_1 = SPI_CPHA
SPI_MODE_2 = SPI_CPOL
SPI_MODE_3 = SPI_CPOL | SPI_CPHA

SPI_CS_HIGH = 0x04
SPI_LSB_FIRST = 0x08
SPI_3WIRE = 0x10
SPI_LOOP = 0x20
SPI_NO_CS = 0x40
SPI_READY = 0x80


# IOCTL commands */

SPI_IOC_MAGIC = 107  # ord('k')


class SpiIocTransfer(ctypes.Structure):
    """<linux/spi/spidev.h> struct SpiIocTransfer"""

    _fields_ = [
        ("tx_buf", ctypes.c_uint64),
        ("rx_buf", ctypes.c_uint64),
        ("len", ctypes.c_uint32),
        ("speed_hz", ctypes.c_uint32),
        ("delay_usecs", ctypes.c_uint16),
        ("bits_per_word", ctypes.c_uint8),
        ("cs_change", ctypes.c_uint8),
        ("pad", ctypes.c_uint32)]

    __slots__ = [name for name, typ in _fields_]


# not all platforms use <asm-generic/ioctl.h> or _ioc_typecheck() ...
def spi_msgsize(num):
    if ((num)*(ctypes.sizeof(SpiIocTransfer))) < (1 << _IOC_SIZEBITS):
        return (num)*(ctypes.sizeof(SpiIocTransfer))
    else:
        return 0

def spi_ioc_message(num):
    return _iow(SPI_IOC_MAGIC, 0, ctypes.c_char*spi_msgsize(num))


# Read / Write of SPI mode (SPI_MODE_0..SPI_MODE_3)
SPI_IOC_RD_MODE = _ior(SPI_IOC_MAGIC, 1, ctypes.c_uint8)
SPI_IOC_WR_MODE = _iow(SPI_IOC_MAGIC, 1, ctypes.c_uint8)

# Read / Write SPI bit justification
SPI_IOC_RD_LSB_FIRST = _ior(SPI_IOC_MAGIC, 2, ctypes.c_uint8)
SPI_IOC_WR_LSB_FIRST = _iow(SPI_IOC_MAGIC, 2, ctypes.c_uint8)

# Read / Write SPI device word length (1..N)
SPI_IOC_RD_BITS_PER_WORD = _ior(SPI_IOC_MAGIC, 3, ctypes.c_uint8)
SPI_IOC_WR_BITS_PER_WORD = _iow(SPI_IOC_MAGIC, 3, ctypes.c_uint8)

# Read / Write SPI device default max speed hz
SPI_IOC_RD_MAX_SPEED_HZ = _ior(SPI_IOC_MAGIC, 4, ctypes.c_uint32)
SPI_IOC_WR_MAX_SPEED_HZ = _iow(SPI_IOC_MAGIC, 4, ctypes.c_uint32)


RES1 = spi_ioc_message(1)
RES2 = spi_ioc_message(2)
RES3 = spi_ioc_message(3)
RES4 = spi_ioc_message(4)
RES5 = spi_ioc_message(5)
RES6 = spi_ioc_message(6)

class VirtualSPI(LoggingMixIn, Operations):
    'Example memory filesystem. Supports only one level of files.'

    def __init__(self):
        self.files = {}
        self.data = defaultdict(binary_type)
        self.fd_ = 0
        now = time()
        self.files['/'] = dict(st_mode=(S_IFDIR | 0o755), st_ctime=now,
                               st_mtime=now, st_atime=now, st_nlink=2)

    def chmod(self, path, mode):
        self.files[path]['st_mode'] &= 0o770000
        self.files[path]['st_mode'] |= mode
        return 0

    def chown(self, path, uid, gid):
        self.files[path]['st_uid'] = uid
        self.files[path]['st_gid'] = gid

    def create(self, path, mode):
        self.files[path] = dict(st_mode=(S_IFREG | mode), st_nlink=1,
                                st_size=0, st_ctime=time(), st_mtime=time(),
                                st_atime=time())

        self.fd_ += 1
        return self.fd_

    def getattr(self, path, fh_=None):
#        if path not in self.files:
#            raise FuseOSError(ENOENT)
        vspi = fuse_get_context()
        if path == '/':
            st_ = dict(st_mode=(S_IFDIR | 0o755), st_nlink=2)
        elif path == '/spidev0.0':
            #size = len('%s\n' % vspi)
            size = 40
            st_ = dict(st_mode=(S_IFREG | 0o444), st_size=size)
        else:
            raise FuseOSError(ENOENT)
        st_['st_ctime'] = st_['st_mtime'] = st_['st_atime'] = time()
        return st_
        #return self.files[path]

    def getxattr(self, path, name, position=0):
        attrs = self.files[path].get('attrs', {})

        try:
            return attrs[name]
        except KeyError:
            return ''       # Should return ENOATTR

    def listxattr(self, path):
        attrs = self.files[path].get('attrs', {})
        return attrs.keys()

    def mkdir(self, path, mode):
        self.files[path] = dict(st_mode=(S_IFDIR | mode), st_nlink=2,
                                st_size=0, st_ctime=time(), st_mtime=time(),
                                st_atime=time())

        self.files['/']['st_nlink'] += 1

    def open(self, path, flags):
        self.fd_ += 1
        return self.fd_

    def read(self, path, size, offset, fh_):
      return "Its an SPI device, dont read, use ioctl\n".encode('utf-8')
      # return self.data[path][offset:offset + size]

    def readdir(self, path, fh_):
      #return ['.', '..'] + [x[1:] for x in self.files if x != '/']
      return ['.', '..', 'spidev0.0']

    def readlink(self, path):
        return self.data[path]

    def removexattr(self, path, name):
        attrs = self.files[path].get('attrs', {})

        try:
            del attrs[name]
        except KeyError:
            pass        # Should return ENOATTR

    def rename(self, old, new):
        self.files[new] = self.files.pop(old)

    def rmdir(self, path):
        self.files.pop(path)
        self.files['/']['st_nlink'] -= 1

    def setxattr(self, path, name, value, options, position=0):
        # Ignore options
        attrs = self.files[path].setdefault('attrs', {})
        attrs[name] = value

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        self.files[target] = dict(st_mode=(S_IFLNK | 0o777), st_nlink=1,
                                  st_size=len(source))

        self.data[target] = source

    def truncate(self, path, length, fh_=None):
        self.data[path] = self.data[path][:length]
        self.files[path]['st_size'] = length

    def unlink(self, path):
        self.files.pop(path)

    def utimens(self, path, times=None):
        now = time()
        atime, mtime = times if times else (now, now)
        self.files[path]['st_atime'] = atime
        self.files[path]['st_mtime'] = mtime



    def write(self, path, data, offset, fh_):
        self.data[path] = self.data[path][:offset] + data
        self.files[path]['st_size'] = len(self.data[path])
        return len(data)

    def ioctl(self, path, cmd, arg, fh_, flags, data):
        logging.info(cmd)
        if cmd == SPI_IOC_WR_MODE:
            logging.info("SPI_IOC_WR_MODE")
        if cmd == SPI_IOC_RD_MODE:
            logging.info("SPI_IOC_RD_MODE")
        if cmd == SPI_IOC_WR_BITS_PER_WORD:
            logging.info("SPI_IOC_WR_BITS_PER_WORD")
        if cmd == SPI_IOC_RD_BITS_PER_WORD:
            logging.info("SPI_IOC_RD_BITS_PER_WORD")
        if cmd == SPI_IOC_WR_MAX_SPEED_HZ:
            logging.info("SPI_IOC_WR_MAX_SPEED_HZ")
        if cmd == SPI_IOC_RD_MAX_SPEED_HZ:
            logging.info("SPI_IOC_RD_MAX_SPEED_HZ")
        if cmd == RES1:
            logging.info("1 spi_ioc_message")
            return 1
        if cmd == RES2:
            logging.info("2 spi_ioc_message")
            return 2
        logging.info("IOCTL")
        return 0

def main():
  if len(argv) != 2:
    print('usage: %s <mountpoint>' % argv[0])
    exit(1)

  # Write to log instead of outputing to console
  # logging.basicConfig(filename='spidev.log', level=logging.DEBUG)
  logging.basicConfig(level=logging.DEBUG)
  fuse = FUSE(VirtualSPI(), argv[1], foreground=False)

if __name__ == '__main__':
  main()
