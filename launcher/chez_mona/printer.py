"""Submit raw ESC/POS bytes to a Windows print queue, or save them in dry-run mode."""

from __future__ import annotations

import sys
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
