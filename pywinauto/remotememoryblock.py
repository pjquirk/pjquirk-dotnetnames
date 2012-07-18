# GUI Application automation and testing library
# Copyright (C) 2006 Mark Mc Mahon
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
#    Free Software Foundation, Inc.,
#    59 Temple Place,
#    Suite 330,
#    Boston, MA 02111-1307 USA

"A remote memory block"

__revision__ = "$Revision: 716 $"

import time
import ctypes

from pywinauto import win32functions
from pywinauto import win32defines
from pywinauto import win32structures

class AccessDenied(RuntimeError):
    "Raised when we cannot allocate memory in the control's process"
    pass


# Todo: I should return iterators from things like Items() and Texts()
#       to save building full lists all the time
# Todo: ListViews should be based off of GetItem, and then have actions
#       Applied to that e.g. ListView.Item(xxx).Select(), rather then
#       ListView.Select(xxx)
#       Or at least most of the functions should call GetItem to get the
#       Item they want to work with.

#====================================================================
class _RemoteMemoryBlock(object):
    "Class that enables reading and writing memory in a different process"
    #----------------------------------------------------------------
    def __init__(self, handle, size = 8192):
        "Allocate the memory"
        self.memAddress = 0

        self._as_parameter_ = self.memAddress

        process_id = ctypes.c_long()
        win32functions.GetWindowThreadProcessId(
            handle, ctypes.byref(process_id))

        self.process = win32functions.OpenProcess(
                win32defines.PROCESS_VM_OPERATION |
                win32defines.PROCESS_VM_READ |
                win32defines.PROCESS_VM_WRITE,
            0,
            process_id)

        if not self.process:
            raise AccessDenied(
                str(ctypes.WinError()) + "process: %d",
                process_id.value)

        if win32functions.GetVersion() < 2147483648L:
            self.memAddress = win32functions.VirtualAllocEx(
                self.process,	# remote process
                0,				# let Valloc decide where
                size,			# how much to allocate
                    win32defines.MEM_RESERVE |
                    win32defines.MEM_COMMIT,	# allocation type
                win32defines.PAGE_READWRITE	# protection
                )

            if not self.memAddress:
                raise ctypes.WinError()

        else:
            raise RuntimeError("Win9x allocation not supported")

        self._as_parameter_ = self.memAddress

    #----------------------------------------------------------------
    def _CloseHandle(self):
        "Close the handle to the process."
        ret = win32functions.CloseHandle(self.process)

        if not ret:
            raise ctypes.WinError()

    #----------------------------------------------------------------
    def CleanUp(self):
        "Free Memory and the process handle"
        if self.process:
            # free up the memory we allocated
            ret = win32functions.VirtualFreeEx(
                self.process, self.memAddress, 0, win32defines.MEM_RELEASE)

            if not ret:
                self._CloseHandle()
                raise ctypes.WinError()

            self._CloseHandle()


    #----------------------------------------------------------------
    def __del__(self):
        "Ensure that the memory is Freed"
        # Free the memory in the remote process's address space
        self.CleanUp()

    #----------------------------------------------------------------
    def Address(self):
        "Return the address of the memory block"
        return self.memAddress

    #----------------------------------------------------------------
    def Write(self, data):
        "Write data into the memory block"
        # write the data from this process into the memory allocated
        # from the other process
        ret = win32functions.WriteProcessMemory(
            self.process,
            self.memAddress,
            ctypes.pointer(data),
            ctypes.sizeof(data),
            0);

        if not ret:
            raise ctypes.WinError()

    #----------------------------------------------------------------
    def Read(self, data, address = None):
        "Read data from the memory block"
        if not address:
            address = self.memAddress

        ret = win32functions.ReadProcessMemory(
            self.process, address, ctypes.byref(data), ctypes.sizeof(data), 0)

        # disabled as it often returns an error - but
        # seems to work fine anyway!!
        if not ret:
            raise ctypes.WinError()

        return data