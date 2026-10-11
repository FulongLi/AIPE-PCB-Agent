"""ctypes wrapper around the ngspice shared library bundled with KiCad (ngspice-46).

Deterministic in this module: library discovery (``AIPE_NGSPICE_DLL`` override, then
``find_kicad_cli().parent``), deck normalisation, message classification and the
time-grid resampler; these are covered by unit tests without the library. Everything
else needs the native library: ``NgSpice.run`` loads a deck through ``ngSpice_Circ``,
runs it synchronously in the foreground with ``ngSpice_Command("run")`` (the ngspice
background thread is never used) and copies the real vectors of the current plot
through ``ngGet_Vec_Info``. KiCad ships no ``spinit`` file, so XSPICE code models are
unavailable and decks must use native ngspice devices only. The library can be
initialised once per process, so ``NgSpice`` is a process-wide singleton.
"""
from __future__ import annotations

import ctypes
import os
import re
from ctypes import CFUNCTYPE, POINTER, Structure, c_bool, c_char_p, c_double, c_int, c_short, c_void_p
from pathlib import Path

import numpy as np

from automation.setup.detect_kicad import find_kicad_cli

ENV_OVERRIDE = "AIPE_NGSPICE_DLL"
LIBRARY_NAMES = ("ngspice.dll", "libngspice.dll", "libngspice.so", "libngspice.so.0",
                 "libngspice.dylib", "libngspice.0.dylib")
# ngspice reports problems through the SendChar callback, not through return codes
# (ngSpice_Circ returned 0 for an unknown-subcircuit error on KiCad 10.0.7).
ERROR_PATTERN = re.compile(r"\bError\b|\bFatal\b|simulation\(s\) aborted|Timestep too small|"
                           r"there aren't any circuits|singular matrix")
WARNING_PATTERN = re.compile(r"\bWarning\b")
VF_REAL, VF_COMPLEX = 1, 2

SendChar = CFUNCTYPE(c_int, c_char_p, c_int, c_void_p)
SendStat = CFUNCTYPE(c_int, c_char_p, c_int, c_void_p)
ControlledExit = CFUNCTYPE(c_int, c_int, c_bool, c_bool, c_int, c_void_p)
SendData = CFUNCTYPE(c_int, c_void_p, c_int, c_int, c_void_p)
SendInitData = CFUNCTYPE(c_int, c_void_p, c_int, c_void_p)
BGThreadRunning = CFUNCTYPE(c_int, c_bool, c_int, c_void_p)


class VectorInfo(Structure):
    """Mirror of ngspice's ``vector_info`` (sharedspice.h)."""
    _fields_ = [("v_name", c_char_p), ("v_type", c_int), ("v_flags", c_short),
                ("v_realdata", POINTER(c_double)), ("v_compdata", c_void_p), ("v_length", c_int)]


class NgSpiceError(RuntimeError):
    """Raised when ngspice reports an error, requests an exit or produces no usable plot."""

    def __init__(self, message: str, messages: list[str] | None = None):
        super().__init__(message)
        self.messages = list(messages or [])


def find_ngspice_library(config: dict | None = None) -> Path:
    """Locate the ngspice shared library; ``AIPE_NGSPICE_DLL`` wins, else next to kicad-cli."""
    explicit = os.environ.get(ENV_OVERRIDE)
    if explicit:
        candidate = Path(os.path.expandvars(explicit)).expanduser()
        if not candidate.is_file():
            raise FileNotFoundError(f"{ENV_OVERRIDE} points to a missing file: {candidate}")
        return candidate.resolve()
    cli = find_kicad_cli(config)
    if cli is None:
        raise FileNotFoundError(f"ngspice shared library not found: no KiCad CLI was discovered; "
                                f"set {ENV_OVERRIDE} to the library path")
    for folder in (cli.parent, cli.parent.parent / "Frameworks", cli.parent.parent / "lib"):
        for name in LIBRARY_NAMES:
            candidate = folder / name
            if candidate.is_file():
                return candidate.resolve()
    raise FileNotFoundError(f"ngspice shared library not found near {cli}; set {ENV_OVERRIDE}")


def ngspice_available(config: dict | None = None) -> bool:
    """True when a shared library can be located (it is not loaded)."""
    try:
        find_ngspice_library(config)
    except FileNotFoundError:
        return False
    return True


def classify_messages(messages: list[str]) -> tuple[list[str], list[str]]:
    """Split ngspice callback messages into (errors, warnings) by their text."""
    errors = [m for m in messages if ERROR_PATTERN.search(m)]
    warnings = [m for m in messages if WARNING_PATTERN.search(m) and m not in errors]
    return errors, warnings


def normalise_deck(deck_lines) -> list[str]:
    """Return deck lines with a title line, no blank lines and a single final ``.end``."""
    lines = [str(line).rstrip("\r\n") for line in deck_lines]
    lines = [line for line in lines if line.strip()]
    if not lines:
        raise ValueError("empty deck")
    if lines[0].lstrip().startswith("."):
        lines.insert(0, "* AIPE deck")
    while lines and lines[-1].strip().lower() == ".end":
        lines.pop()
    lines.append(".end")
    return lines


class NgSpice:
    """Synchronous, foreground-only access to the ngspice shared library (one per process).

    The callbacks are stored on the instance so ctypes keeps them alive for the lifetime
    of the library; ``messages`` holds the text of the most recent ``run``/``command``.
    A second construction returns the same instance (the library argument is then ignored).
    """

    _shared = None

    def __new__(cls, library: Path | str | None = None):
        if cls._shared is None:
            cls._shared = super().__new__(cls)
            cls._shared._ready = False
        return cls._shared

    def __init__(self, library: Path | str | None = None):
        if self._ready:
            return
        self.library_path = Path(library) if library else find_ngspice_library()
        self.lib = ctypes.CDLL(str(self.library_path))
        self.messages: list[str] = []
        self.log: list[str] = []
        self.exit_request: tuple | None = None
        self.data_points = 0
        self.circuit_loaded = False
        self.broken = False
        self._bind()
        self._callbacks = (SendChar(self._on_char), SendStat(self._on_stat), ControlledExit(self._on_exit),
                           SendData(self._on_data), SendInitData(self._on_init), BGThreadRunning(self._on_bg))
        if self.lib.ngSpice_Init(*self._callbacks, None) != 0:
            raise NgSpiceError("ngSpice_Init failed", self.messages)
        self.banner = list(self.messages)
        match = re.search(r"ngspice-(\d+)", " ".join(self.banner))
        self.version = match.group(0) if match else "ngspice-unknown"
        self._ready = True

    def _bind(self):
        lib = self.lib
        lib.ngSpice_Init.restype = c_int
        lib.ngSpice_Init.argtypes = [SendChar, SendStat, ControlledExit, SendData, SendInitData,
                                     BGThreadRunning, c_void_p]
        lib.ngSpice_Circ.restype = c_int
        lib.ngSpice_Circ.argtypes = [POINTER(c_char_p)]
        lib.ngSpice_Command.restype = c_int
        lib.ngSpice_Command.argtypes = [c_char_p]
        lib.ngGet_Vec_Info.restype = POINTER(VectorInfo)
        lib.ngGet_Vec_Info.argtypes = [c_char_p]
        lib.ngSpice_CurPlot.restype = c_char_p
        lib.ngSpice_CurPlot.argtypes = []
        lib.ngSpice_AllVecs.restype = POINTER(c_char_p)
        lib.ngSpice_AllVecs.argtypes = [c_char_p]

    # -- callbacks (signatures fixed by sharedspice.h) ---------------------------------
    def _on_char(self, text, ident, user):
        message = (text or b"").decode("utf-8", "replace")
        self.messages.append(message)
        self.log.append(message)
        return 0

    def _on_stat(self, text, ident, user):
        return 0

    def _on_exit(self, status, immediate, quit_requested, ident, user):
        self.exit_request = (int(status), bool(immediate), bool(quit_requested))
        self.broken = True
        return 0

    def _on_data(self, values, count, ident, user):
        self.data_points += 1
        return 0

    def _on_init(self, info, ident, user):
        return 0

    def _on_bg(self, running, ident, user):
        return 0

    # -- commands ------------------------------------------------------------------------
    def _check_usable(self):
        if self.broken:
            raise NgSpiceError("ngspice requested a controlled exit earlier; restart the process",
                               self.messages)

    def command(self, text: str, check: bool = True) -> list[str]:
        """Send one interactive command; return its messages and raise on reported errors."""
        self._check_usable()
        start = len(self.messages)
        code = self.lib.ngSpice_Command(text.encode("utf-8"))
        new = self.messages[start:]
        if check:
            errors, _ = classify_messages(new)
            if code != 0 or errors or self.exit_request:
                raise NgSpiceError(f"ngspice command {text!r} failed: " + " | ".join(errors or new), new)
        return new

    def load_circuit(self, deck_lines) -> list[str]:
        """Replace the loaded circuit by ``deck_lines`` (title first, ``.end`` appended)."""
        self._check_usable()
        if self.circuit_loaded:
            self.command("remcirc", check=False)
            self.circuit_loaded = False
        self.command("destroy all", check=False)
        self.messages = []
        self.exit_request = None
        self.data_points = 0
        lines = normalise_deck(deck_lines)
        array = (c_char_p * (len(lines) + 1))()
        for index, line in enumerate(lines):
            array[index] = line.encode("utf-8")
        array[len(lines)] = None
        code = self.lib.ngSpice_Circ(array)
        errors, _ = classify_messages(self.messages)
        if code != 0 or errors or self.exit_request:
            raise NgSpiceError("ngspice rejected the deck: " + " | ".join(errors or self.messages),
                               self.messages)
        self.circuit_loaded = True
        return lines

    def current_plot(self) -> str:
        """Name of ngspice's current plot (``const`` when nothing has run)."""
        return (self.lib.ngSpice_CurPlot() or b"").decode()

    def vector_names(self, plot: str | None = None) -> list[str]:
        """Names of the vectors in ``plot`` (default: the current plot)."""
        pointer = self.lib.ngSpice_AllVecs((plot or self.current_plot()).encode())
        names, index = [], 0
        while pointer and pointer[index]:
            names.append(pointer[index].decode())
            index += 1
        return names

    def vector(self, name: str) -> np.ndarray | None:
        """Copy one real vector of the current plot (``None`` if absent or complex)."""
        pointer = self.lib.ngGet_Vec_Info(name.encode())
        if not pointer:
            return None
        info = pointer.contents
        if info.v_length <= 0 or not info.v_realdata or (info.v_flags & VF_COMPLEX):
            return None
        return np.ctypeslib.as_array(info.v_realdata, shape=(info.v_length,)).astype(float, copy=True)

    def run(self, deck_lines, vectors=None, expected_end: float | None = None) -> dict[str, np.ndarray]:
        """Load and run a transient deck in the foreground; return {vector name: real array}.

        Raises ``NgSpiceError`` if ngspice reports an error, no new plot with a ``time``
        vector is produced, or the simulation stopped before ``expected_end`` (seconds).
        ``vectors`` optionally restricts the names copied (``time`` is always included).
        """
        self.load_circuit(deck_lines)
        before = self.current_plot()
        start = len(self.messages)
        code = self.lib.ngSpice_Command(b"run")
        run_messages = self.messages[start:]
        errors, _ = classify_messages(run_messages)
        plot = self.current_plot()
        if code != 0 or errors or self.exit_request or plot in ("", "const", before):
            raise NgSpiceError("ngspice run failed: " + " | ".join(errors or run_messages[-5:]),
                               self.messages)
        names = self.vector_names(plot)
        wanted = {name.lower() for name in (vectors or names)} | {"time"}
        result = {}
        for name in names:
            if name.lower() in wanted:
                data = self.vector(name)
                if data is not None:
                    result[name] = data
        time = result.get("time")
        if time is None or time.size < 2:
            raise NgSpiceError("ngspice produced no time vector", self.messages)
        if expected_end is not None and time[-1] < expected_end * (1 - 1e-6) - 1e-12:
            raise NgSpiceError(f"transient stopped at {time[-1]:.6g} s before {expected_end:.6g} s",
                               self.messages)
        return result

    @property
    def warnings(self) -> list[str]:
        """Warnings reported during the most recent load/run."""
        return classify_messages(self.messages)[1]


def uniform_grid(t_start: float, t_end: float, dt: float) -> np.ndarray:
    """Uniform time grid from ``t_start`` to ``t_end`` inclusive (``dt`` > 0)."""
    if dt <= 0 or t_end <= t_start:
        raise ValueError("uniform_grid needs dt > 0 and t_end > t_start")
    count = int(round((t_end - t_start) / dt)) + 1
    return t_start + dt * np.arange(count)


def resample(time: np.ndarray, values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Linear interpolation of a (possibly non-uniform) waveform onto ``grid``."""
    time = np.asarray(time, float)
    values = np.asarray(values, float)
    keep = np.concatenate(([True], np.diff(time) > 0))
    return np.interp(grid, time[keep], values[keep])


def resample_vectors(vectors: dict[str, np.ndarray], dt: float, t_start: float | None = None,
                     t_end: float | None = None) -> dict[str, np.ndarray]:
    """Resample every vector onto a uniform grid; the result's ``time`` is the grid."""
    time = vectors["time"]
    grid = uniform_grid(time[0] if t_start is None else t_start, time[-1] if t_end is None else t_end, dt)
    out = {"time": grid}
    for name, data in vectors.items():
        if name != "time" and data.shape == time.shape:
            out[name] = resample(time, data, grid)
    return out
