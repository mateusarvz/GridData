interface FileDropzoneProps {
  onFilesSelected: (files: File[]) => void;
  selectedFiles: File[];
  onRemoveFile: (index: number) => void;
  errorMessage: string;
}

const acceptedTypes = ['.csv', '.parquet', '.xlsx'];

export function FileDropzone({ onFilesSelected, selectedFiles, onRemoveFile, errorMessage }: FileDropzoneProps) {
  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files?.length) onFilesSelected(Array.from(files));
    event.target.value = '';
  };

  return (
    <div className="rounded-[28px] border border-dashed border-violet-500/40 bg-slate-950/80 p-8 text-center text-slate-300">
      <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-3xl bg-violet-500/10 text-violet-300">
        <span className="text-3xl">+</span>
      </div>
      <p className="text-sm leading-6 text-slate-300">Arraste e solte arquivos ou selecione manualmente.</p>
      <p className="mt-2 text-xs text-slate-500">Formatos aceitos: {acceptedTypes.join(', ')}</p>
      <label className="mt-6 inline-flex cursor-pointer items-center justify-center rounded-2xl bg-violet-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-violet-400">
        Selecionar arquivos
        <input type="file" multiple accept={acceptedTypes.join(', ')} className="sr-only" onChange={handleInputChange} />
      </label>
      {selectedFiles.length > 0 ? (
        <div className="mt-6 space-y-3 text-left">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Arquivos prontos</p>
          <ul className="space-y-2">
            {selectedFiles.map((file, index) => (
              <li key={`${file.name}-${file.size}-${index}`} className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">
                <div className="min-w-0">
                  <div className="truncate font-medium">{file.name}</div>
                  <div className="text-xs text-slate-500">{Math.max(1, Math.round(file.size / 1024))} KB</div>
                </div>
                <button
                  type="button"
                  onClick={() => onRemoveFile(index)}
                  className="shrink-0 rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-slate-300 transition hover:bg-white/10 hover:text-white"
                >
                  Remover
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {errorMessage ? <div className="mt-4 text-sm text-rose-300">{errorMessage}</div> : null}
    </div>
  );
}
