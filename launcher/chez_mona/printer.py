"""Send raw ESC/POS bytes to the receipt printer, directly over USB or through a
Windows print queue, or save them in dry-run mode."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path


class PrintError(RuntimeError):
    pass


# Status bits from GetPrinter level 2 that mean a job will not print now.
BLOCKING_STATUS = {
    0x00000001: "print queue paused",
    0x00000002: "printer error",
    0x00000008: "paper jam",
    0x00000010: "out of paper",
    0x00000040: "paper problem",
    0x00000080: "printer offline",
    0x00001000: "printer not available",
    0x00100000: "printer needs attention",
    0x00400000: "door open",
}
WORK_OFFLINE = 0x00000400  # PRINTER_ATTRIBUTE_WORK_OFFLINE
ERROR_INVALID_PRINTER_NAME = 1801


def _winspool():
    import ctypes
    from ctypes import wintypes

    class DOC_INFO_1(ctypes.Structure):
        _fields_ = [
            ("pDocName", wintypes.LPWSTR),
            ("pOutputFile", wintypes.LPWSTR),
            ("pDatatype", wintypes.LPWSTR),
        ]

    class PRINTER_INFO_2(ctypes.Structure):
        _fields_ = [(name, wintypes.LPWSTR) for name in (
            "pServerName", "pPrinterName", "pShareName", "pPortName", "pDriverName",
            "pComment", "pLocation")] + [
            ("pDevMode", ctypes.c_void_p),
        ] + [(name, wintypes.LPWSTR) for name in (
            "pSepFile", "pPrintProcessor", "pDatatype", "pParameters")] + [
            ("pSecurityDescriptor", ctypes.c_void_p),
        ] + [(name, wintypes.DWORD) for name in (
            "Attributes", "Priority", "DefaultPriority", "StartTime", "UntilTime",
            "Status", "cJobs", "AveragePPM")]

    dll = ctypes.WinDLL("winspool.drv", use_last_error=True)
    dll.OpenPrinterW.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p]
    dll.GetPrinterW.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    dll.StartDocPrinterW.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(DOC_INFO_1)]
    dll.StartDocPrinterW.restype = wintypes.DWORD
    dll.StartPagePrinter.argtypes = [wintypes.HANDLE]
    dll.WritePrinter.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    dll.EndPagePrinter.argtypes = [wintypes.HANDLE]
    dll.EndDocPrinter.argtypes = [wintypes.HANDLE]
    dll.AbortPrinter.argtypes = [wintypes.HANDLE]
    dll.ClosePrinter.argtypes = [wintypes.HANDLE]
    return ctypes, wintypes, dll, DOC_INFO_1, PRINTER_INFO_2


def _open(queue: str):
    ctypes, wintypes, dll, *_ = _winspool()
    handle = wintypes.HANDLE()
    if not dll.OpenPrinterW(queue, ctypes.byref(handle), None):
        code = ctypes.get_last_error()
        if code == ERROR_INVALID_PRINTER_NAME:
            raise PrintError(f"Print queue '{queue}' was not found on this laptop.")
        raise PrintError(f"Could not open print queue '{queue}' (Windows error {code}).")
    return handle


def queue_status(queue: str) -> dict:
    """Queue state as reported by the spooler. Drivers do not always report problems."""
    if sys.platform != "win32":
        raise PrintError("Printing needs Windows.")
    ctypes, wintypes, dll, _, PRINTER_INFO_2 = _winspool()
    handle = _open(queue)
    try:
        needed = wintypes.DWORD()
        dll.GetPrinterW(handle, 2, None, 0, ctypes.byref(needed))
        buffer = ctypes.create_string_buffer(needed.value)
        if not dll.GetPrinterW(handle, 2, buffer, needed.value, ctypes.byref(needed)):
            raise PrintError(f"Could not read the state of '{queue}' (Windows error {ctypes.get_last_error()}).")
        info = ctypes.cast(buffer, ctypes.POINTER(PRINTER_INFO_2)).contents
        problems = [label for bit, label in BLOCKING_STATUS.items() if info.Status & bit]
        if info.Attributes & WORK_OFFLINE:
            problems.append("set to use printer offline")
        return {
            "queue": queue,
            "driver": info.pDriverName,
            "port": info.pPortName,
            "jobs": info.cJobs,
            "problems": problems,
        }
    finally:
        dll.ClosePrinter(handle)


def submit_raw(queue: str, data: bytes, document: str = "Chez Mona receipt") -> int:
    """Send bytes with the RAW datatype. Returns the spooler job id."""
    status = queue_status(queue)
    if status["problems"]:
        raise PrintError(f"Printer '{queue}' reports: {', '.join(status['problems'])}.")
    ctypes, wintypes, dll, DOC_INFO_1, _ = _winspool()
    handle = _open(queue)
    try:
        info = DOC_INFO_1(document, None, "RAW")
        job = dll.StartDocPrinterW(handle, 1, ctypes.byref(info))
        if not job:
            raise PrintError(f"The spooler refused the receipt (Windows error {ctypes.get_last_error()}).")
        sent = False
        try:
            if not dll.StartPagePrinter(handle):
                raise PrintError(f"Could not start the receipt page (Windows error {ctypes.get_last_error()}).")
            written = wintypes.DWORD()
            buffer = ctypes.create_string_buffer(data, len(data))
            ok = dll.WritePrinter(handle, buffer, len(data), ctypes.byref(written))
            if not ok or written.value != len(data):
                raise PrintError(
                    f"Only {written.value} of {len(data)} bytes reached the spooler, so the receipt was cancelled. "
                    "Check the printer before printing again."
                )
            dll.EndPagePrinter(handle)
            sent = True
        finally:
            # A cut-off job would leave the printer mid-image, so delete it instead.
            if sent:
                dll.EndDocPrinter(handle)
            else:
                dll.AbortPrinter(handle)
        return job
    finally:
        dll.ClosePrinter(handle)


def save_dry_run(out_dir: Path, dish_id: str, data: bytes, png: bytes) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / f"{time.strftime('%Y%m%d-%H%M%S')}-{dish_id}"
    stem.with_suffix(".bin").write_bytes(data)
    stem.with_suffix(".png").write_bytes(png)
    return stem.with_suffix(".png")


# ---------- Direct USB ----------
# Writes to the printer's USB printing class interface, the same one the spooler
# uses, so no printer driver or print queue is needed.

GUID_DEVINTERFACE_USBPRINT = "28d78fad-5a12-11d1-ae5b-0000f803a8c2"
USB_WRITE_TIMEOUT = 20.0
USB_READ_TIMEOUT = 1.0
_usb_lock = threading.Lock()


def _usb_api():
    import ctypes
    import uuid
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("d1", ctypes.c_ulong), ("d2", ctypes.c_ushort), ("d3", ctypes.c_ushort), ("d4", ctypes.c_ubyte * 8)]

    class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("guid", GUID), ("Flags", wintypes.DWORD), ("Reserved", ctypes.c_void_p)]

    class OVERLAPPED(ctypes.Structure):
        _fields_ = [("Internal", ctypes.c_void_p), ("InternalHigh", ctypes.c_void_p), ("Offset", wintypes.DWORD),
                    ("OffsetHigh", wintypes.DWORD), ("hEvent", wintypes.HANDLE)]

    u = uuid.UUID(GUID_DEVINTERFACE_USBPRINT)
    guid = GUID(u.fields[0], u.fields[1], u.fields[2], (ctypes.c_ubyte * 8)(*u.bytes[8:]))

    setup = ctypes.WinDLL("setupapi", use_last_error=True)
    setup.SetupDiGetClassDevsW.restype = ctypes.c_void_p
    setup.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD]
    setup.SetupDiEnumDeviceInterfaces.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID), wintypes.DWORD,
                                                  ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)]
    setup.SetupDiGetDeviceInterfaceDetailW.argtypes = [ctypes.c_void_p, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA), ctypes.c_void_p,
                                                       wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    setup.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                wintypes.DWORD, wintypes.HANDLE]
    k32.CreateEventW.restype = wintypes.HANDLE
    k32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    for name in ("WriteFile", "ReadFile"):
        getattr(k32, name).argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                                       ctypes.POINTER(OVERLAPPED)]
    k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.WaitForSingleObject.restype = wintypes.DWORD
    k32.GetOverlappedResult.argtypes = [wintypes.HANDLE, ctypes.POINTER(OVERLAPPED), ctypes.POINTER(wintypes.DWORD), wintypes.BOOL]
    k32.CancelIoEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(OVERLAPPED)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    return ctypes, wintypes, setup, k32, guid, SP_DEVICE_INTERFACE_DATA, OVERLAPPED


def usb_printers() -> list[str]:
    """Device paths of attached USB printers, for example \\\\?\\usb#vid_0fe6&pid_811e#..."""
    if sys.platform != "win32":
        return []
    ctypes, wintypes, setup, _, guid, SP_DEVICE_INTERFACE_DATA, _ = _usb_api()
    DIGCF_PRESENT, DIGCF_DEVICEINTERFACE = 0x2, 0x10
    devices = setup.SetupDiGetClassDevsW(ctypes.byref(guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE)
    paths = []
    try:
        index = 0
        while True:
            data = SP_DEVICE_INTERFACE_DATA()
            data.cbSize = ctypes.sizeof(data)
            if not setup.SetupDiEnumDeviceInterfaces(devices, None, ctypes.byref(guid), index, ctypes.byref(data)):
                break
            needed = wintypes.DWORD()
            setup.SetupDiGetDeviceInterfaceDetailW(devices, ctypes.byref(data), None, 0, ctypes.byref(needed), None)
            detail = ctypes.create_string_buffer(needed.value)
            # cbSize of SP_DEVICE_INTERFACE_DETAIL_DATA_W: 8 on 64 bit, 6 on 32 bit.
            ctypes.cast(detail, ctypes.POINTER(wintypes.DWORD))[0] = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            if setup.SetupDiGetDeviceInterfaceDetailW(devices, ctypes.byref(data), detail, needed, None, None):
                paths.append(ctypes.wstring_at(ctypes.addressof(detail) + 4))
            index += 1
    finally:
        setup.SetupDiDestroyDeviceInfoList(devices)
    return paths


def _find_usb(match: str) -> str:
    paths = [p for p in usb_printers() if match.lower() in p.lower()]
    if not paths:
        detail = f" matching '{match}'" if match else ""
        raise PrintError(f"No USB receipt printer{detail} is connected. Check the cable and power.")
    return paths[0]


class _UsbHandle:
    def __init__(self, path: str):
        self.api = _usb_api()
        ctypes, wintypes, _, k32, *_ = self.api
        GENERIC_READ, GENERIC_WRITE, OPEN_EXISTING, FILE_FLAG_OVERLAPPED = 0x80000000, 0x40000000, 3, 0x40000000
        self.handle = k32.CreateFileW(path, GENERIC_READ | GENERIC_WRITE, 0x1 | 0x2, None, OPEN_EXISTING,
                                      FILE_FLAG_OVERLAPPED, None)
        if self.handle in (None, wintypes.HANDLE(-1).value):
            raise PrintError(f"Could not open the USB printer (Windows error {ctypes.get_last_error()}). "
                             "Another program may be using it.")

    def _io(self, name: str, buffer, size: int, timeout: float) -> int:
        """Overlapped ReadFile or WriteFile that gives up after timeout seconds."""
        ctypes, wintypes, _, k32, _, _, OVERLAPPED = self.api
        ERROR_IO_PENDING, WAIT_OBJECT_0 = 997, 0
        overlapped = OVERLAPPED()
        overlapped.hEvent = k32.CreateEventW(None, True, False, None)
        done = wintypes.DWORD()
        try:
            ok = getattr(k32, name)(self.handle, buffer, size, None, ctypes.byref(overlapped))
            if not ok and ctypes.get_last_error() != ERROR_IO_PENDING:
                raise PrintError(f"The USB printer refused the data (Windows error {ctypes.get_last_error()}).")
            if k32.WaitForSingleObject(overlapped.hEvent, int(timeout * 1000)) != WAIT_OBJECT_0:
                k32.CancelIoEx(self.handle, ctypes.byref(overlapped))
                k32.GetOverlappedResult(self.handle, ctypes.byref(overlapped), ctypes.byref(done), True)
                raise TimeoutError(done.value)
            if not k32.GetOverlappedResult(self.handle, ctypes.byref(overlapped), ctypes.byref(done), False):
                raise PrintError(f"The USB printer stopped responding (Windows error {ctypes.get_last_error()}).")
            return done.value
        finally:
            k32.CloseHandle(overlapped.hEvent)

    def write(self, data: bytes, timeout: float) -> int:
        ctypes = self.api[0]
        buffer = ctypes.create_string_buffer(data, len(data))
        return self._io("WriteFile", buffer, len(data), timeout)

    def query(self, command: bytes, timeout: float) -> int | None:
        """Send an ESC/POS real time status request and return the status byte, if any."""
        ctypes = self.api[0]
        try:
            self.write(command, timeout)
            buffer = ctypes.create_string_buffer(8)
            got = self._io("ReadFile", buffer, 8, timeout)
        except TimeoutError:
            return None
        return buffer.raw[got - 1] if got else None

    def close(self):
        self.api[3].CloseHandle(self.handle)


def usb_status(match: str = "") -> dict:
    """Connection and, when the printer answers DLE EOT, cover and paper state."""
    if sys.platform != "win32":
        raise PrintError("Printing needs Windows.")
    path = _find_usb(match)
    info = {"device": path, "problems": []}
    with _usb_lock:
        usb = _UsbHandle(path)
        try:
            offline = usb.query(b"\x10\x04\x02", USB_READ_TIMEOUT)
            paper = usb.query(b"\x10\x04\x04", USB_READ_TIMEOUT)
        finally:
            usb.close()
    info["answers_status"] = offline is not None and paper is not None
    if offline is not None and offline & 0x04:
        info["problems"].append("cover open")
    if paper is not None and paper & 0x60:
        info["problems"].append("out of paper")
    elif paper is not None and paper & 0x0C:
        info["problems"].append("paper low")
    return info


def submit_usb(data: bytes, match: str = "") -> dict:
    status = usb_status(match)
    blocking = [p for p in status["problems"] if p != "paper low"]
    if blocking:
        raise PrintError(f"Printer reports: {', '.join(blocking)}.")
    with _usb_lock:
        usb = _UsbHandle(status["device"])
        try:
            try:
                written = usb.write(data, USB_WRITE_TIMEOUT)
            except TimeoutError as exc:
                raise PrintError(
                    f"The printer took too long and only part of the job was sent ({exc.args[0]} of {len(data)} bytes). "
                    "Check the printer before printing again."
                ) from None
        finally:
            usb.close()
    if written != len(data):
        raise PrintError(f"Only {written} of {len(data)} bytes reached the printer. Check the printer before printing again.")
    return {"bytes": written, "paper_low": "paper low" in status["problems"]}
