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

export interface RelatedUserTable {
  table_name: string;
  display_name: string;
  category: string;
  row_count?: number | null;
  columns_count?: number | null;
  related_to_user: boolean;
  metadata: Record<string, unknown>;
}
