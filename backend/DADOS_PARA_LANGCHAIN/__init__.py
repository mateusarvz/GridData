# DADOS_PARA_LANGCHAIN — Metadata, schema & relationship layer for SQL Agent context.
# This package prepares ONLY structural metadata (not data rows) for the LangChain
# SQL Agent. Actual row data is accessed ONLY at query time, through a read-only
# database connection pre-filtered to the authenticated user.
