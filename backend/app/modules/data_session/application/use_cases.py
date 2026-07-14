import uuid
from typing import Any

from app.core.supabase import get_supabase_service_client
from app.modules.data_session.domain.repositories import DataSessionRepository
from app.modules.data_session.infrastructure.pandas_reader import (
    validate_file_extension,
    read_file_to_dataframe,
    dataframe_to_preview,
)
from app.modules.data_session.application.dto import (
    UploadedTableMetaDTO,
    TablePreviewDTO,
    RelatedTableSummaryDTO,
)


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


class ListRelatedUserTablesUseCase:
    async def execute(self, user_id: str) -> list[RelatedTableSummaryDTO]:
        client = get_supabase_service_client()
        if client is None:
            return []

        summaries: list[RelatedTableSummaryDTO] = []

        def _count_related(table_name: str, field: str, value: str) -> int:
            try:
                response = client.from_(table_name).select("id", count="exact").eq(field, value).execute()
                return int(getattr(response, "count", 0) or 0)
            except Exception:
                return 0

        try:
            user_row = (
                client.from_("users")
                .select("id, email, nome_usuario, criado_em")
                .eq("id", user_id)
                .maybe_single()
                .execute()
            )
            user_data = getattr(user_row, "data", None) or {}
            if user_data:
                summaries.append(
                    RelatedTableSummaryDTO(
                        table_name="users",
                        display_name="Perfil do usuário",
                        category="Identidade",
                        row_count=1,
                        columns_count=4,
                        metadata={
                            "email": user_data.get("email"),
                            "nome_usuario": user_data.get("nome_usuario"),
                            "criado_em": user_data.get("criado_em"),
                        },
                    )
                )

            subscription_row = (
                client.from_("user_subscriptions")
                .select("id, ativo, data_inicio, data_vencimento, plan_id")
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            subscription = getattr(subscription_row, "data", None) or {}
            if subscription:
                plan_name = None
                plan_id = subscription.get("plan_id")
                if plan_id:
                    plan_row = (
                        client.from_("subscription_plans")
                        .select("nome")
                        .eq("id", plan_id)
                        .maybe_single()
                        .execute()
                    )
                    plan_data = getattr(plan_row, "data", None) or {}
                    plan_name = plan_data.get("nome")

                summaries.append(
                    RelatedTableSummaryDTO(
                        table_name="user_subscriptions",
                        display_name="Assinatura do usuário",
                        category="Cobrança",
                        row_count=1,
                        columns_count=5,
                        metadata={
                            "ativo": subscription.get("ativo"),
                            "data_inicio": subscription.get("data_inicio"),
                            "data_vencimento": subscription.get("data_vencimento"),
                            "plano": plan_name,
                        },
                    )
                )

            user_tables = (
                client.from_("user_tables")
                .select("id, nome_tabela, nome_origem_arquivo, tipo_arquivo, total_linhas, criado_em, atualizado_em")
                .eq("user_id", user_id)
                .is_("deleted_at", "null")
                .order("criado_em", desc=True)
                .execute()
            )
            for table in getattr(user_tables, "data", []) or []:
                columns_count = _count_related("user_table_columns", "user_table_id", table["id"])
                relationship_count = _count_related("user_table_relationships", "tabela_origem_id", table["id"])
                summaries.append(
                    RelatedTableSummaryDTO(
                        table_name="user_tables",
                        display_name=table.get("nome_tabela", "Tabela do usuário"),
                        category="Dados",
                        row_count=int(table.get("total_linhas", 0) or 0),
                        columns_count=columns_count,
                        metadata={
                            "user_table_id": table.get("id"),
                            "nome_origem_arquivo": table.get("nome_origem_arquivo"),
                            "tipo_arquivo": table.get("tipo_arquivo"),
                            "relacionamentos": relationship_count,
                            "criado_em": table.get("criado_em"),
                            "atualizado_em": table.get("atualizado_em"),
                        },
                    )
                )

            uploads = (
                client.from_("file_uploads")
                .select("id, nome_arquivo, tipo_arquivo, total_linhas, status, criado_em, processado_em")
                .eq("user_id", user_id)
                .order("criado_em", desc=True)
                .execute()
            )
            for upload in getattr(uploads, "data", []) or []:
                summaries.append(
                    RelatedTableSummaryDTO(
                        table_name="file_uploads",
                        display_name=upload.get("nome_arquivo", "Upload"),
                        category="Arquivos",
                        row_count=int(upload.get("total_linhas", 0) or 0),
                        metadata={
                            "tipo_arquivo": upload.get("tipo_arquivo"),
                            "status": upload.get("status"),
                            "criado_em": upload.get("criado_em"),
                            "processado_em": upload.get("processado_em"),
                        },
                    )
                )

            billing = (
                client.from_("billing_transactions")
                .select("id, tipo, valor, moeda, status, data_vencimento, data_pagamento, criado_em")
                .eq("user_id", user_id)
                .order("criado_em", desc=True)
                .execute()
            )
            for item in getattr(billing, "data", []) or []:
                summaries.append(
                    RelatedTableSummaryDTO(
                        table_name="billing_transactions",
                        display_name=f'{item.get("tipo", "Transação")} - {item.get("status", "")}',
                        category="Cobrança",
                        metadata={
                            "valor": item.get("valor"),
                            "moeda": item.get("moeda"),
                            "status": item.get("status"),
                            "data_vencimento": item.get("data_vencimento"),
                            "data_pagamento": item.get("data_pagamento"),
                            "criado_em": item.get("criado_em"),
                        },
                    )
                )

            audit_logs = (
                client.from_("audit_logs")
                .select("id, acao, descricao, tabela_afetada, registro_id, criado_em")
                .eq("user_id", user_id)
                .order("criado_em", desc=True)
                .execute()
            )
            for log in getattr(audit_logs, "data", []) or []:
                summaries.append(
                    RelatedTableSummaryDTO(
                        table_name="audit_logs",
                        display_name=log.get("acao", "Auditoria"),
                        category="Auditoria",
                        metadata={
                            "descricao": log.get("descricao"),
                            "tabela_afetada": log.get("tabela_afetada"),
                            "registro_id": log.get("registro_id"),
                            "criado_em": log.get("criado_em"),
                        },
                    )
                )
        except Exception:
            return summaries

        return summaries
