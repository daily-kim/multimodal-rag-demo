from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.adapters.document_conversion.base import ConversionResult, DocumentConverter
from app.domain.exceptions import ExternalServiceError


class LibreOfficeConverter(DocumentConverter):
    def convert(self, source_path: str | Path, output_path: str | Path) -> ConversionResult:
        soffice = shutil.which("soffice")
        if not soffice:
            raise ExternalServiceError("LibreOffice `soffice` is not installed.")

        source = Path(source_path).resolve()
        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        out_dir = target.parent
        result = subprocess.run(
            [
                soffice,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(out_dir),
                str(source),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        converted = out_dir / f"{source.stem}.pdf"
        if result.returncode != 0 or not converted.exists():
            raise ExternalServiceError(result.stderr.strip() or "LibreOffice conversion failed.")
        if converted != target:
            converted.replace(target)
        return ConversionResult(output_path=target)

