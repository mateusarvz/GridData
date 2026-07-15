import io
from typing import Any

import pandas as pd


ALLOWED_EXTENSIONS = {"csv", "parquet", "xlsx"}


def validate_file_extension(file_name: str) -> bool:
    extension = file_name.rsplit('.', 1)[-1].lower()
    return extension in ALLOWED_EXTENSIONS


def read_file_to_dataframe(file_name: str, content: bytes) -> tuple[str, Any]:
    extension = file_name.rsplit('.', 1)[-1].lower()
    buffer = io.BytesIO(content)

    if extension == 'csv':
        df = pd.read_csv(buffer)
    elif extension == 'parquet':
        df = pd.read_parquet(buffer)
    elif extension == 'xlsx':
        df = pd.read_excel(buffer)
    else:
        raise ValueError('Formato de arquivo não suportado.')

    return file_name, df


def dataframe_to_preview(df: Any, preview_rows: int = 10) -> list[dict[str, Any]]:
    return df.head(preview_rows).fillna('').to_dict(orient='records')
