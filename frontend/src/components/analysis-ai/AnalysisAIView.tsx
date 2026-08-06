import { MessageSquare } from 'lucide-react';
import { ChatGeminiView } from './ChatGeminiView';

export function AnalysisAIView() {
  return (
    <div className="flex h-full min-h-0 w-full flex-col gap-4 p-6">
      <div>
        <div className="mb-2 flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-violet-400" />
          <h2 className="text-lg font-semibold text-slate-100">Análise com IA</h2>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-white/[0.06] bg-slate-900/30 p-3">
        <ChatGeminiView />
      </div>
    </div>
  );
}
