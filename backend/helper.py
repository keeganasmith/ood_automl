from __future__ import annotations

from pathlib import Path
from typing import Union, IO, Optional, Any
from io import BytesIO

import pandas as pd


def load_table(
    src: Union[str, Path, bytes, IO[bytes]],
    *,
    sheet: Optional[Union[str, int]] = 0,
    **kwargs: Any,
) -> pd.DataFrame:
    """
    Load a CSV, Excel, or Parquet file into a pandas DataFrame.

    Args:
        src: Path/str to a file, raw bytes, or a binary file-like object.
        sheet: Excel sheet name or index (ignored for CSV/Parquet).
        **kwargs: Extra keyword args passed to pandas readers,
                  e.g. dtype=..., nrows=..., columns=...

    Returns:
        pd.DataFrame

    Raises:
        ValueError: If the file type is unsupported.
        RuntimeError: If required optional dependencies are missing.
    """

    file_like = None
    ext = None

    # -----------------------------
    # Normalize input source
    # -----------------------------
    if isinstance(src, (str, Path)):
        path = Path(src)
        ext = path.suffix.lower()
        handle = str(path)

    elif isinstance(src, bytes):
        file_like = BytesIO(src)
        handle = file_like
        ext = None  # unknown unless user passes metadata

    else:
        # Assume it's an IO[bytes]-like object
        handle = src
        name = getattr(src, "name", "") or ""
        ext = Path(name).suffix.lower() if name else None

    # -----------------------------
    # Parquet
    # -----------------------------
    if ext == ".parquet":
        try:
            return pd.read_parquet(handle, **kwargs)
        except ImportError as e:
            raise RuntimeError(
                "Reading Parquet requires 'pyarrow' or 'fastparquet'.\n"
                "Install with: pip install pyarrow"
            ) from e

    # -----------------------------
    # CSV / TSV / TXT
    # -----------------------------
    if ext in {".csv", ".tsv", ".txt"} or ext is None:
        if ext == ".tsv":
            return pd.read_csv(handle, sep="\t", **kwargs)

        return pd.read_csv(handle, sep=None, engine="python", **kwargs)

    # -----------------------------
    # Excel (modern)
    # -----------------------------
    if ext in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        return pd.read_excel(handle, sheet_name=sheet, engine="openpyxl", **kwargs)

    # -----------------------------
    # Excel (legacy .xls)
    # -----------------------------
    if ext == ".xls":
        try:
            return pd.read_excel(handle, sheet_name=sheet, engine="xlrd", **kwargs)
        except ImportError as e:
            raise RuntimeError(
                "Reading .xls requires 'xlrd<2.0'.\n"
                "Install with: pip install 'xlrd<2.0'"
            ) from e

    # -----------------------------
    # Unsupported
    # -----------------------------
    raise ValueError(f"Unsupported file type: {ext!r}")

