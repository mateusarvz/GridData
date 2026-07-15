interface FileDropzoneProps {
  onFilesSelected: (files: FileList) => void;
  errorMessage: string;
}

const acceptedTypes = ['.csv', '.parquet', '.xlsx'];

export function FileDropzone({ onFilesSelected, errorMessage }: FileDropzoneProps) {
  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) onFilesSelected(files);
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
      {errorMessage ? <div className="mt-4 text-sm text-rose-300">{errorMessage}</div> : null}
    </div>
  );
}
