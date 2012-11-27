#
# Copyright (c) 2011,2012 The developers of Aqualid project - http://aqualid.googlecode.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom
# the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE
# AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

__all__ = ( 'FileLock', )

import os
import time
import errno

#//===========================================================================//
#   General implementation
#//===========================================================================//
class GeneralFileLock (object):
  
  class Timeout( Exception ): pass
  
  __slots__ = ('lockfilename', 'locked', 'retries', 'interval')
  
  def   __init__( self, filename, interval = 0.25, timeout = 5 * 60 ):
    self.lockfilename = os.path.normcase( os.path.normpath( os.path.abspath( str(filename) ) ) ) + '.lock'
    self.locked = False
    self.interval = interval
    self.retries = int(timeout / interval)
  
  def   __enter__(self):
    return self

  def   __exit__(self, exc_type, exc_value, traceback):
    self.releaseLock()
  
  def   readLock( self ):
    return self.writeLock()
  
  def   writeLock( self ):
    if self.locked:
      raise AssertionError( 'file: %s is locked already' % self.lockfilename )
    
    index = self.retries
    
    while True:
      try:
        os.mkdir( self.lockfilename )
        break
      except OSError as ex:
        if ex.errno != errno.EEXIST:
          raise
        if not index:
            raise self.Timeout( "Lock file '%s' timeout." % self.lockfilename )
        
        index -= 1
      
      time.sleep( self.interval )
    
    self.locked = True
    return self
  
  def   releaseLock( self ):
    if not self.locked:
      raise AssertionError( 'file: %s is not locked' % self.lockfilename )
    
    try:
      os.rmdir( self.lockfilename )
    except OSError as ex:
      if ex.errno != errno.ENOENT:
        raise
    
    self.locked = False

try:
  #//===========================================================================//
  #   Unix implementation
  #//===========================================================================//
  import fcntl
  
  class UnixFileLock (object):
    
    __slots__ = ('fd')
  
    def   __init__( self, filename ):
      self.fd = os.open( filename, os.O_RDWR | os.O_CREAT )
    
    def   __enter__(self):
      return self
  
    def   __exit__(self, exc_type, exc_value, traceback):
      self.releaseLock()
    
    def   readLock( self, lockf = fcntl.lockf, LOCK_SH = fcntl.LOCK_SH ):
      lockf( self.fd, LOCK_SH )
      return self
    
    def   writeLock( self, lockf = fcntl.lockf, LOCK_EX = fcntl.LOCK_EX):
      lockf( self.fd, LOCK_EX )
      return self
    
    def   releaseLock( self, lockf = fcntl.lockf, LOCK_UN = fcntl.LOCK_UN):
      lockf( self.fd, LOCK_UN )
  
  FileLock = UnixFileLock
  
except ImportError:

  try:
    #//===========================================================================//
    #   Widows implementation
    #//===========================================================================//
    import win32con
    import win32file
    import pywintypes
    
    class WindowsFileLock (object):
      
      __slots__ = ('hfile', )
      _overlapped = pywintypes.OVERLAPPED()
    
      def   __init__( self, filename ):
        lockfilename = filename + ".lock"
        
        self.hfile = win32file.CreateFile( lockfilename,
                                           win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                                           win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                                           None,
                                           win32file.OPEN_ALWAYS,
                                           0,
                                           None )
        self.locked = False
      
      def   __enter__(self):
        return self
    
      def   __exit__(self, exc_type, exc_value, traceback):
        self.releaseLock()
      
      def   readLock( self, LockFileEx = win32file.LockFileEx, overlapped = _overlapped ):
        LockFileEx( self.hfile, 0, 0, 4096, overlapped )
        return self
      
      def   writeLock( self, LockFileEx = win32file.LockFileEx, LOCKFILE_EXCLUSIVE_LOCK = win32con.LOCKFILE_EXCLUSIVE_LOCK, overlapped = _overlapped):
        LockFileEx( self.hfile, LOCKFILE_EXCLUSIVE_LOCK, 0, 4096, overlapped )
        return self
      
      def   releaseLock( self, UnlockFileEx = win32file.UnlockFileEx, overlapped = _overlapped ):
        UnlockFileEx( self.hfile, 0, 4096, overlapped )
    
    FileLock = WindowsFileLock
    
  except ImportError:
    
    FileLock = GeneralFileLock