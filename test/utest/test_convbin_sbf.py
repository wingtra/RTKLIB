"""Run with: python3 test_convbin_sbf.py /path/to/convbin"""
import binascii
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


def measurement(tow_ms):
    # MeasEpoch: one GPS L1 observation (PRN 1), no secondary signals.
    epoch = struct.pack("<IH6B", tow_ms, 2200, 1, 20, 12, 0, 0, 0)
    signal = struct.pack("<4BIiHbBHBB", 0, 0, 1, 4, 1000000, 0, 0, 0, 80, 1, 0, 0)
    body = struct.pack("<HH", 4027, 8 + len(epoch) + len(signal)) + epoch + signal
    return b"$@" + struct.pack("<H", binascii.crc_hqx(body, 0)) + body


def observations(convbin, directory, data):
    (directory / "input.sbf").write_bytes(data)
    output = directory / "output.obs"
    if output.exists():
        output.unlink()
    subprocess.run([str(convbin), "-r", "sbf", "-v", "3.04", "-o", output.name,
                    "input.sbf"], cwd=directory, check=True, capture_output=True)
    if not output.is_file():
        return []
    lines = output.read_text().splitlines()
    header_end = next(i for i, line in enumerate(lines) if "END OF HEADER" in line)
    return lines[header_end + 1:]


if __name__ == "__main__":
    convbin = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        complete = measurement(100000) + measurement(101000)
        expected = observations(convbin, directory, complete)
        assert sum(line.startswith(">") for line in expected) == 2
        last = measurement(102000)
        for cut in range(1, len(last)):
            actual = observations(convbin, directory, complete + last[:cut])
            assert actual == expected, f"lost observations with {cut} bytes of the final block"
