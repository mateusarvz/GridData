import React, { useEffect, useState } from 'react';
import {
  X,
  Table2,
  Plus,
  History,
  Check,
  Search,
  Filter,
  Download,
  Calendar,
  DollarSign,
  Type,
  CheckSquare,
  Sparkles,
} from 'lucide-react';
import type { TableItem } from '../../types/workspace';
import { api, type RowData } from '../../services/api';
import { TimeTravelDrawer } from './TimeTravelDrawer';

interface TablePreviewProps {
  item: TableItem;
  onClose: () => void;
}

interface ColumnDef {
  id: string;
  name: string;
  type: 'text' | 'number' | 'currency' | 'date' | 'status';
}

export const TablePreview: React.FC<TablePreviewProps> = ({ item, onClose }) => {
  const [columns, setColumns] = useState<ColumnDef[]>([
    { id: 'col-1', name: 'Título / Projeto', type: 'text' },
    { id: 'col-2', name: 'Status', type: 'status' },
    { id: 'col-3', name: 'Orçamento', type: 'currency' },
    { id: 'col-4', name: 'Responsável', type: 'text' },
    { id: 'col-5', name: 'Prazo Limite', type: 'date' },
  ]);

  const [rows, setRows] = useState<RowData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [editingCell, setEditingCell] = useState<{ rowId: string; colId: string } | null>(null);
  const [editValue, setEditValue] = useState<any>('');
  const [activeTimeTravelRow, setActiveTimeTravelRow] = useState<{ id: string; title: string } | null>(null);
  const [search, setSearch] = useState('');

  // Fechar com Escape (a menos que o drawer esteja aberto)
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !activeTimeTravelRow) onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose, activeTimeTravelRow]);

  // Carregar dados iniciais ou fallback demo offline
  useEffect(() => {
    const fetchRows = async () => {
      setLoading(true);
      const res = await api.queryRows(item.id);
      if (res && res.length > 0) {
        setRows(res);
      } else {
        // Fallback demo para visualização imediata em qualquer ambiente
        setRows([
          {
            id: 'row-101',
            table_id: item.id,
            version: 3,
            data: {
              'col-1': 'Expansão Plataforma Dama Box',
              'col-2': 'Em Produção',
              'col-3': 150000,
              'col-4': 'Carlos Eduardo',
              'col-5': '2026-12-15',
            },
            updated_at: 'Há 10 min',
          },
          {
            id: 'row-102',
            table_id: item.id,
            version: 1,
            data: {
              'col-1': 'Auditoria de Segurança Zero-Trust',
              'col-2': 'Concluído',
              'col-3': 45000,
              'col-4': 'Marina Silva',
              'col-5': '2026-06-30',
            },
            updated_at: 'Há 2 dias',
          },
          {
            id: 'row-103',
            table_id: item.id,
            version: 2,
            data: {
              'col-1': 'Migração AWS RDS PostgreSQL',
              'col-2': 'Em Análise',
              'col-3': 85000,
              'col-4': 'Admin Dama',
              'col-5': '2026-08-10',
            },
            updated_at: 'Ontem',
          },
          {
            id: 'row-104',
            table_id: item.id,
            version: 1,
            data: {
              'col-1': 'Inteligência Artificial NL2SQL',
              'col-2': 'Planejado',
              'col-3': 120000,
              'col-4': 'Roberto Dias',
              'col-5': '2027-01-20',
            },
            updated_at: 'Há 4 dias',
          },
        ]);
      }
      setLoading(false);
    };
    fetchRows();
  }, [item.id]);

  const handleAddRow = async () => {
    const newId = `row-${Date.now()}`;
    const initialData = {
      'col-1': 'Novo Registro Dinâmico',
      'col-2': 'Planejado',
      'col-3': 10000,
      'col-4': 'Usuário Logado',
      'col-5': new Date().toISOString().split('T')[0],
    };

    const newRow: RowData = {
      id: newId,
      table_id: item.id,
      version: 1,
      data: initialData,
      updated_at: 'Agora',
    };

    setRows((prev) => [newRow, ...prev]);
    await api.createRow(item.id, initialData);
  };

  const handleAddColumn = () => {
    const names = ['Categoria', 'Prioridade', 'Centro de Custo', 'Aprovador', 'Observações', 'KPI Alvo'];
    const types: ColumnDef['type'][] = ['text', 'status', 'currency', 'text', 'text', 'number'];
    const idx = columns.length % names.length;
    const newCol: ColumnDef = {
      id: `col-${Date.now()}`,
      name: names[idx],
      type: types[idx],
    };
    setColumns((prev) => [...prev, newCol]);
  };

  const startEdit = (rowId: string, colId: string, currentVal: any) => {
    setEditingCell({ rowId, colId });
    setEditValue(currentVal ?? '');
  };

  const saveEdit = async (rowId: string, colId: string) => {
    if (!editingCell) return;
    setEditingCell(null);

    setRows((prev) =>
      prev.map((r) => {
        if (r.id === rowId) {
          const newData = { ...r.data, [colId]: editValue };
          return { ...r, version: r.version + 1, data: newData, updated_at: 'Agora (editado)' };
        }
        return r;
      })
    );

    const targetRow = rows.find((r) => r.id === rowId);
    if (targetRow) {
      await api.updateRow(rowId, { ...targetRow.data, [colId]: editValue });
    }
  };

  const getColIcon = (type: ColumnDef['type']) => {
    switch (type) {
      case 'text': return <Type className="w-3.5 h-3.5 text-blue-500" />;
      case 'number': return <CheckSquare className="w-3.5 h-3.5 text-indigo-500" />;
      case 'currency': return <DollarSign className="w-3.5 h-3.5 text-emerald-500" />;
      case 'date': return <Calendar className="w-3.5 h-3.5 text-amber-500" />;
      case 'status': return <Sparkles className="w-3.5 h-3.5 text-purple-500" />;
    }
  };

  const formatValue = (type: ColumnDef['type'], val: any) => {
    if (val === undefined || val === null || val === '') return <span className="text-gray-300 italic">vazio</span>;
    if (type === 'currency') {
      return typeof val === 'number'
        ? val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
        : `R$ ${val}`;
    }
    if (type === 'status') {
      const isOk = val === 'Concluído' || val === 'Em Produção' || val === 'Aprovado';
      const isPending = val === 'Em Análise' || val === 'Em Andamento';
      return (
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold ${
            isOk ? 'bg-emerald-100 text-emerald-800' : isPending ? 'bg-amber-100 text-amber-800' : 'bg-gray-100 text-gray-800'
          }`}
        >
          {val}
        </span>
      );
    }
    return String(val);
  };

  const filteredRows = rows.filter((r) => {
    if (!search.trim()) return true;
    return Object.values(r.data).some((val) => String(val).toLowerCase().includes(search.toLowerCase()));
  });

  return (
    <div
      className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[95vw] max-w-6xl max-h-[88vh] bg-white rounded-2xl shadow-2xl border border-[var(--color-border)] flex flex-col z-[500] overflow-hidden animate-scale-up"
      role="dialog"
      aria-label={`Planilha: ${item.name}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)] bg-gradient-to-r from-slate-50 to-white">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-primary-soft)] flex items-center justify-center shadow-sm">
            <Table2 className="w-5 h-5 text-[var(--color-primary)]" strokeWidth={1.5} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-[var(--color-ink)]">{item.name}</h2>
              <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                Grid Interativo · JSONB
              </span>
            </div>
            <p className="text-xs text-[var(--color-muted)]">
              {rows.length} linha{rows.length !== 1 ? 's' : ''} · {columns.length} colunas com tipagem forte e Time Travel
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleAddColumn}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--color-surface)] border border-[var(--color-border)] hover:bg-gray-100 transition-colors text-[var(--color-ink)]"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Adicionar Coluna</span>
          </button>
          <button
            onClick={handleAddRow}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-hover)] transition-colors shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Adicionar Linha</span>
          </button>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 text-[var(--color-muted)] hover:text-[var(--color-ink)] transition-colors ml-2"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Barra de Ferramentas / Filtros */}
      <div className="px-6 py-2.5 bg-gray-50 border-b border-[var(--color-border)] flex items-center justify-between text-xs">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Filtrar dados na planilha..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 pr-3 py-1 rounded-md bg-white border border-gray-200 text-xs focus:outline-none focus:border-[var(--color-primary)] w-56"
            />
          </div>
          <button className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-gray-200 bg-white text-gray-600 hover:bg-gray-50">
            <Filter className="w-3.5 h-3.5" />
            <span>Filtros GIN (PostgreSQL)</span>
          </button>
        </div>
        <div className="flex items-center gap-3 text-gray-500">
          <span className="inline-flex items-center gap-1">
            💡 <strong>Dica:</strong> Clique em qualquer célula para edição inline com registro de auditoria!
          </span>
          <button className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-gray-200 bg-white text-gray-600 hover:bg-gray-50">
            <Download className="w-3.5 h-3.5" />
            <span>Exportar CSV</span>
          </button>
        </div>
      </div>

      {/* Grid Table Body */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="h-64 flex flex-col items-center justify-center text-gray-400">
            <div className="w-8 h-8 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin mb-2"></div>
            <span>Carregando planilha interativa...</span>
          </div>
        ) : (
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-gray-100 border-b border-gray-200 text-gray-600 select-none">
                <th className="py-3 px-4 font-semibold w-12 text-center">#</th>
                {columns.map((col) => (
                  <th key={col.id} className="py-3 px-4 font-semibold border-l border-gray-200 min-w-[160px]">
                    <div className="flex items-center gap-1.5">
                      {getColIcon(col.type)}
                      <span>{col.name}</span>
                    </div>
                  </th>
                ))}
                <th className="py-3 px-4 font-semibold border-l border-gray-200 w-28 text-center">Versão</th>
                <th className="py-3 px-4 font-semibold border-l border-gray-200 w-36 text-center">Time Travel</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredRows.map((row, index) => (
                <tr key={row.id} className="hover:bg-blue-50/40 transition-colors group">
                  <td className="py-3 px-4 text-center text-gray-400 font-mono">{index + 1}</td>
                  {columns.map((col) => {
                    const isEditing = editingCell?.rowId === row.id && editingCell?.colId === col.id;
                    const cellVal = row.data[col.id];

                    return (
                      <td
                        key={col.id}
                        className="py-2.5 px-4 border-l border-gray-100 cursor-pointer hover:bg-blue-100/50 transition-colors relative"
                        onClick={() => !isEditing && startEdit(row.id, col.id, cellVal)}
                      >
                        {isEditing ? (
                          <div className="flex items-center gap-1">
                            <input
                              autoFocus
                              type={col.type === 'number' || col.type === 'currency' ? 'number' : 'text'}
                              value={editValue}
                              onChange={(e) =>
                                setEditValue(
                                  col.type === 'number' || col.type === 'currency'
                                    ? Number(e.target.value) || 0
                                    : e.target.value
                                )
                              }
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') saveEdit(row.id, col.id);
                                if (e.key === 'Escape') setEditingCell(null);
                              }}
                              onBlur={() => saveEdit(row.id, col.id)}
                              className="w-full px-2 py-1 rounded border border-blue-500 bg-white shadow-sm focus:outline-none text-xs font-medium"
                            />
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                saveEdit(row.id, col.id);
                              }}
                              className="p-1 rounded bg-blue-600 text-white hover:bg-blue-700"
                            >
                              <Check className="w-3 h-3" />
                            </button>
                          </div>
                        ) : (
                          formatValue(col.type, cellVal)
                        )}
                      </td>
                    );
                  })}
                  <td className="py-2.5 px-4 border-l border-gray-100 text-center">
                    <span className="px-2 py-0.5 rounded bg-gray-100 text-gray-700 font-bold">v{row.version}</span>
                  </td>
                  <td className="py-2.5 px-4 border-l border-gray-100 text-center">
                    <button
                      onClick={() =>
                        setActiveTimeTravelRow({
                          id: row.id,
                          title: String(row.data['col-1'] || `Registro #${index + 1}`),
                        })
                      }
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-purple-100 text-purple-700 hover:bg-purple-600 hover:text-white transition-all shadow-sm"
                      title="Ver Histórico de Auditoria e Reverter Versões"
                    >
                      <History className="w-3.5 h-3.5" />
                      <span>Auditoria</span>
                    </button>
                  </td>
                </tr>
              ))}
              {filteredRows.length === 0 && (
                <tr>
                  <td colSpan={columns.length + 3} className="py-12 text-center text-gray-400">
                    Nenhum registro encontrado. Clique em <strong>"+ Adicionar Linha"</strong> para criar o primeiro!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Footer Info */}
      <div className="px-6 py-3 border-t border-[var(--color-border)] bg-gray-50 flex items-center justify-between text-xs text-gray-500">
        <div>
          Armazenamento multi-tenant: <code className="bg-gray-200 px-1.5 py-0.5 rounded">schema: empresa_dama</code> · Tabela:{' '}
          <code className="bg-gray-200 px-1.5 py-0.5 rounded">id: {item.id}</code>
        </div>
        <div className="flex items-center gap-2 font-medium text-emerald-700">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span>Sincronização Ativa</span>
        </div>
      </div>

      {/* Drawer do Time Travel */}
      {activeTimeTravelRow && (
        <TimeTravelDrawer
          rowId={activeTimeTravelRow.id}
          rowTitle={activeTimeTravelRow.title}
          onClose={() => setActiveTimeTravelRow(null)}
          onRevert={(ver) => {
            setRows((prev) =>
              prev.map((r) =>
                r.id === activeTimeTravelRow.id ? { ...r, version: ver, updated_at: `Revertido para v${ver}` } : r
              )
            );
          }}
        />
      )}
    </div>
  );
};
