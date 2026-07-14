import type { TablePreviewResponse, UploadedTableMeta } from '../types/dataUpload';

const BASE_URL = '/api/v1';

export async function uploadDataFiles(files: FileList): Promise<UploadedTableMeta[]> {
  const validExtensions = ['csv', 'parquet', 'xlsx'];
  const formData = new FormData();

  for (const file of Array.from(files)) {
    const extension = file.name.split('.').pop()?.toLowerCase();
    if (!extension || !validExtensions.includes(extension)) {
      throw new Error(`Formato não suportado: ${file.name}`);
    }
    formData.append('files', file);
  }

  const response = await fetch(`${BASE_URL}/data/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Falha ao enviar arquivos.');
  }

  return response.json();
}

export async function listSessionTables(): Promise<UploadedTableMeta[]> {
  const response = await fetch(`${BASE_URL}/data/session`, {
    method: 'GET',
  });
  if (!response.ok) {
    return [];
  }
  return response.json();
}

export async function getTablePreview(tableId: string, page = 1, pageSize = 20): Promise<TablePreviewResponse> {
  const response = await fetch(`${BASE_URL}/data/${tableId}/preview?page=${page}&page_size=${pageSize}`, {
    method: 'GET',
  });
  if (!response.ok) {
    throw new Error('Falha ao carregar visualização da tabela.');
  }
  return response.json();
}

export async function clearSessionTables(): Promise<void> {
  await fetch(`${BASE_URL}/data/session`, {
    method: 'DELETE',
  });
}
