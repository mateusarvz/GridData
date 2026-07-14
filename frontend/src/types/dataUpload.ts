export interface UploadedTableMeta {
  table_id: string;
  file_name: string;
  columns: string[];
  row_count: number;
  preview: Array<Record<string, unknown>>;
}

export interface TablePreviewResponse {
  table_id: string;
  file_name: string;
  columns: string[];
  row_count: number;
  preview: Array<Record<string, unknown>>;
  page: number;
  page_size: number;
}
