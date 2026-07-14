import uuid
from typing import Any

from app.modules.data_session.domain.repositories import DataSessionRepository
from app.modules.data_session.infrastructure.pandas_reader import (
    validate_file_extension,
    read_file_to_dataframe,
    dataframe_to_preview,
)
from app.modules.data_session.application.dto import UploadedTableMetaDTO, TablePreviewDTO


DEFAULT_SESSION_TTL_SECONDS = 60 * 30  # 30 minutes


class UploadDataFilesUseCase:
    def __init__(self, repository: DataSessionRepository) -> None:
        self.repository = repository

    async def execute(self, user_id: str, files: list[tuple[str, bytes]]) -> list[UploadedTableMetaDTO]:
        table_metadata: list[UploadedTableMetaDTO] = []

        for file_name, content in files:
            if not validate_file_extension(file_name):
                raise ValueError(f'Extensão não suportada: {file_name}')

            _, df = read_file_to_dataframe(file_name, content)
            table_id = str(uuid.uuid4())
            preview = dataframe_to_preview(df)
            metadata = {
                'table_id': table_id,
                'file_name': file_name,
                'columns': df.columns.astype(str).tolist(),
                'row_count': int(df.shape[0]),
                'preview': preview,
            }
            await self.repository.save_table(user_id, table_id, metadata, preview, DEFAULT_SESSION_TTL_SECONDS)
            table_metadata.append(UploadedTableMetaDTO(**metadata))

        return table_metadata


class ListSessionTablesUseCase:
    def __init__(self, repository: DataSessionRepository) -> None:
        self.repository = repository

    async def execute(self, user_id: str) -> list[UploadedTableMetaDTO]:
        raw = await self.repository.list_tables(user_id)
        return [UploadedTableMetaDTO(**item) for item in raw]


class GetTablePreviewUseCase:
    def __init__(self, repository: DataSessionRepository) -> None:
        self.repository = repository

    async def execute(self, user_id: str, table_id: str, page: int = 1, page_size: int = 20) -> TablePreviewDTO | None:
        stored = await self.repository.get_table(user_id, table_id)
        if stored is None:
            return None

        preview = stored.get('preview', [])
        start = (page - 1) * page_size
        end = start + page_size
        return TablePreviewDTO(
            table_id=stored['table_id'],
            file_name=stored['file_name'],
            columns=stored['columns'],
            row_count=stored['row_count'],
            preview=preview[start:end],
            page=page,
            page_size=page_size,
        )


class DeleteSessionTablesUseCase:
    def __init__(self, repository: DataSessionRepository) -> None:
        self.repository = repository

    async def execute(self, user_id: str) -> None:
        await self.repository.delete_session(user_id)
