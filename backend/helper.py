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
    Load a CSV or Excel file into a pandas DataFrame.
    
    Args:
        src: Path/str to a file, raw bytes, or a binary file-like object.
        sheet: Excel sheet name or index (ignored for CSV). Default: 0 (first sheet).
        **kwargs: Extra keyword args passed to pandas (read_csv/read_excel),
                  e.g. use `dtype=...`, `nrows=...`, etc.

    Returns:
        pd.DataFrame

    Raises:
        ValueError: If the file type is unsupported.
        RuntimeError: If .xls reading requires xlrd and it's missing.
    """
    # Normalize to something pandas can read
    file_like = None
    ext = None

    if isinstance(src, (str, Path)):
        path = Path(src)
        ext = path.suffix.lower()
        handle = str(path)
    elif isinstance(src, bytes):
        file_like = BytesIO(src)
        handle = file_like
    else:
        # Assume it's an IO[bytes]-like object
        handle = src
        # Try to infer extension from name attribute if present
        name = getattr(src, "name", "") or ""
        ext = Path(name).suffix.lower() if name else None

    # CSV
    if ext in {".csv", ".tsv", ".txt"} or ext is None:
        # If it's explicitly a TSV, default to tab; otherwise let pandas sniff.
        if ext == ".tsv":
            return pd.read_csv(handle, sep="\t", **kwargs)
        # sep=None triggers delimiter inference (uses python engine)
        return pd.read_csv(handle, sep=None, engine="python", **kwargs)

    # Excel (modern)
    if ext in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        return pd.read_excel(handle, sheet_name=sheet, engine="openpyxl", **kwargs)

    # Legacy .xls
    if ext == ".xls":
        try:
            return pd.read_excel(handle, sheet_name=sheet, engine="xlrd", **kwargs)
        except ImportError as e:
            raise RuntimeError(
                "Reading .xls requires 'xlrd<2.0'. Install with: pip install 'xlrd<2.0'"
            ) from e

    raise ValueError(f"Unsupported file type: {ext!r}")