import { useState } from 'react';
import { FileDropzone } from './FileDropzone';

interface DataUploadModalProps {
  onClose: () => void;
  onUpload: (files: FileList) => Promise<void>;
}

export function DataUploadModal({ onClose, onUpload }: DataUploadModalProps) {
  const [error, setError] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  const handleFilesSelected = async (files: FileList) => {
    setError('');
    try {
      setIsUploading(true);
      await onUpload(files);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro no upload.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-[32px] border border-white/10 bg-slate-950/95 p-6 shadow-2xl shadow-slate-950/40">
        <div className="flex items-center justify-between gap-4 pb-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Carregar Dados</h2>
            <p className="text-sm text-slate-400">Envie arquivos CSV, Parquet ou XLSX para processar em memória.</p>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 transition hover:text-white">
            Fechar
          </button>
        </div>

        <FileDropzone onFilesSelected={handleFilesSelected} errorMessage={error} />

        <div className="mt-6 flex items-center justify-end gap-3">
          <button type="button" onClick={onClose} className="rounded-2xl border border-white/10 px-4 py-3 text-sm text-slate-300 transition hover:bg-white/5">
            Cancelar
          </button>
          <button type="button" disabled={isUploading} className="rounded-2xl bg-violet-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-violet-400 disabled:cursor-not-allowed disabled:opacity-60">
            {isUploading ? 'Enviando...' : 'Enviar arquivos'}
          </button>
        </div>
      </div>
    </div>
  );
}
