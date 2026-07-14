import { useUserStore } from '../../store/userStore';

export function Topbar() {
  const nomeUsuario = useUserStore((state) => state.nomeUsuario);

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-slate-950/95 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 text-white sm:px-6">
        <div className="text-sm text-slate-300">{nomeUsuario || 'Usuário'}</div>
        <div className="text-base font-semibold uppercase tracking-[0.15em] text-violet-300">damabox</div>
      </div>
    </header>
  );
}
