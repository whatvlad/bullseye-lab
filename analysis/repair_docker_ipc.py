"""Remove only the inaccessible zero-byte Docker IPC endpoint, opening it without following reparse data."""
import ctypes
from ctypes import wintypes
p='C:/Users/shiro/AppData/Local/docker-secrets-engine/engine.sock'
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.CreateFileW.restype=wintypes.HANDLE
k.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
k.CloseHandle.argtypes=[wintypes.HANDLE]
k.SetFileInformationByHandle.argtypes=[wintypes.HANDLE,ctypes.c_int,wintypes.LPVOID,wintypes.DWORD]
k.GetFileSizeEx.argtypes=[wintypes.HANDLE,ctypes.POINTER(ctypes.c_longlong)]
h=k.CreateFileW(p,0x10000|0x80,7,None,3,0x00200000|0x02000000,None)
if h==wintypes.HANDLE(-1).value: raise ctypes.WinError(ctypes.get_last_error())
try:
 size=ctypes.c_longlong()
 if not k.GetFileSizeEx(h,ctypes.byref(size)):raise ctypes.WinError(ctypes.get_last_error())
 if size.value!=0:raise ValueError('IPC endpoint is not zero-byte; untouched')
 flags=wintypes.DWORD(1|2|16)
 if not k.SetFileInformationByHandle(h,21,ctypes.byref(flags),ctypes.sizeof(flags)):raise ctypes.WinError(ctypes.get_last_error())
 print('Removed zero-byte stale Docker IPC endpoint')
finally:k.CloseHandle(h)
