import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { TransactionDto } from '@/api/dashboardApi'
import { fetchTransactionsPaged } from '@/api/transactionsApi'
import { TransactionDetailModal } from '@/components/TransactionDetailModal'
import { formatAmountKzt } from '@/lib/formatMoney'
import { ChevronLeft, ChevronRight, Download, Search } from 'lucide-react'
import toast from 'react-hot-toast'

const PAGE_SIZE = 12
const SEARCH_DEBOUNCE_MS = 350

const CATEGORY_FILTER_OPTIONS = [
  { value: '', label: 'Все категории' },
  { value: 'Transport', label: 'Transport' },
  { value: 'Food', label: 'Food' },
  { value: 'Leisure', label: 'Leisure' },
  { value: 'Shopping', label: 'Shopping' },
  { value: 'Bills', label: 'Bills' },
  { value: 'Other', label: 'Other' },
]

function shortWhen(iso: string) {
  try {
    return new Intl.DateTimeFormat('ru-RU', {
      dateStyle: 'short',
      timeStyle: 'short',
      timeZone: 'UTC',
    }).format(new Date(iso))
  } catch {
    return iso.slice(0, 19).replace('T', ' ')
  }
}

function escapeCsvField(value: string | number): string {
  const s = String(value)
  return `"${s.replace(/"/g, '""')}"`
}

function downloadTransactionsCsv(rows: TransactionDto[], filename: string) {
  const header = ['id', 'created_at', 'description', 'category', 'amount', 'tags']
  const lines = [header.join(',')]
  for (const tx of rows) {
    lines.push(
      [
        tx.id,
        escapeCsvField(tx.created_at),
        escapeCsvField(tx.description),
        escapeCsvField(tx.category),
        tx.amount,
        escapeCsvField(tx.tags ?? ''),
      ].join(','),
    )
  }
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function Transactions() {
  const [items, setItems] = useState<TransactionDto[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<TransactionDto | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const initialSync = useRef(false)

  useEffect(() => {
    const delay = initialSync.current ? SEARCH_DEBOUNCE_MS : 0
    const id = window.setTimeout(() => {
      setDebouncedSearch(searchInput.trim())
      initialSync.current = true
    }, delay)
    return () => window.clearTimeout(id)
  }, [searchInput])

  useLayoutEffect(() => {
    setPage(1)
  }, [debouncedSearch, categoryFilter])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const skip = (page - 1) * PAGE_SIZE
      const res = await fetchTransactionsPaged({
        skip,
        limit: PAGE_SIZE,
        q: debouncedSearch || undefined,
        category: categoryFilter || undefined,
      })
      setItems(res.items)
      setTotal(res.total)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Не удалось загрузить транзакции'
      setError(msg)
      setItems([])
      setTotal(0)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }, [page, debouncedSearch, categoryFilter])

  useEffect(() => {
    void load()
  }, [load])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const openRow = (tx: TransactionDto) => {
    setSelected(tx)
    setModalOpen(true)
  }

  const onModalOpenChange = (open: boolean) => {
    setModalOpen(open)
    if (!open) setSelected(null)
  }

  const onExportCsv = () => {
    if (items.length === 0) {
      toast.error('Нет строк для экспорта')
      return
    }
    const cat = categoryFilter || 'all'
    const q = debouncedSearch ? `_${debouncedSearch.slice(0, 24).replace(/\W+/g, '_')}` : ''
    downloadTransactionsCsv(items, `transactions_p${page}_${cat}${q}.csv`)
    toast.success('CSV скачан')
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4">
        <p className="text-sm text-[#6F767E]">
          Всего записей: <span className="font-semibold text-[#1A1D1F]">{total}</span>
        </p>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2 lg:max-w-2xl lg:flex-1">
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#6F767E]"
                strokeWidth={1.75}
              />
              <input
                type="search"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Поиск по названию…"
                className="w-full rounded-[16px] border border-slate-200/80 bg-white py-2.5 pl-10 pr-3 text-sm text-[#1A1D1F] shadow-sm outline-none ring-[#A7D7C5] placeholder:text-[#6F767E] focus:ring-2"
                autoComplete="off"
              />
            </div>
            <div>
              <label htmlFor="tx-category" className="mb-1 block text-xs font-semibold text-[#6F767E]">
                Категория
              </label>
              <select
                id="tx-category"
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="w-full rounded-[16px] border border-slate-200/80 bg-white px-3 py-2.5 text-sm font-medium text-[#1A1D1F] shadow-sm outline-none ring-[#A7D7C5] focus:ring-2"
              >
                {CATEGORY_FILTER_OPTIONS.map((o) => (
                  <option key={o.value || 'all'} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <button
            type="button"
            onClick={onExportCsv}
            disabled={loading || items.length === 0}
            className="inline-flex shrink-0 items-center justify-center gap-2 self-start rounded-[16px] border border-slate-200/80 bg-white px-4 py-2.5 text-sm font-semibold text-[#1A1D1F] shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 lg:self-auto"
          >
            <Download className="h-4 w-4" strokeWidth={1.75} />
            Экспорт CSV
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-[24px] bg-white shadow-sm">
        {error ? (
          <p className="p-6 text-sm text-red-600">Ошибка: {error}</p>
        ) : loading ? (
          <p className="p-8 text-center text-sm text-[#6F767E]">Загрузка…</p>
        ) : items.length === 0 ? (
          <p className="p-8 text-center text-sm font-medium text-[#6F767E]">
            Транзакций не найдено. Измените запрос или добавьте расход.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs font-semibold uppercase tracking-wide text-[#6F767E]">
                  <th className="px-5 py-3">Название</th>
                  <th className="px-5 py-3">Категория</th>
                  <th className="px-5 py-3">Дата</th>
                  <th className="px-5 py-3 text-right">Сумма</th>
                </tr>
              </thead>
              <tbody>
                {items.map((tx) => (
                  <tr
                    key={tx.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => openRow(tx)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        openRow(tx)
                      }
                    }}
                    className="cursor-pointer border-b border-slate-50 transition-colors hover:bg-[#A7D7C5]/10 focus-visible:bg-[#A7D7C5]/15 focus-visible:outline-none"
                  >
                    <td className="px-5 py-3 font-semibold text-[#1A1D1F]">{tx.description}</td>
                    <td className="px-5 py-3 text-[#6F767E]">{tx.category}</td>
                    <td className="px-5 py-3 text-[#6F767E]">{shortWhen(tx.created_at)}</td>
                    <td className="px-5 py-3 text-right font-bold text-[#1A1D1F]">{formatAmountKzt(tx.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && !error && total > 0 ? (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-5 py-4">
            <p className="text-xs text-[#6F767E]">
              Страница {page} из {totalPages}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="inline-flex items-center gap-1 rounded-[14px] border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-[#1A1D1F] shadow-sm disabled:opacity-40"
              >
                <ChevronLeft className="h-4 w-4" strokeWidth={1.75} />
                Назад
              </button>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="inline-flex items-center gap-1 rounded-[14px] border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-[#1A1D1F] shadow-sm disabled:opacity-40"
              >
                Вперёд
                <ChevronRight className="h-4 w-4" strokeWidth={1.75} />
              </button>
            </div>
          </div>
        ) : null}
      </div>

      <TransactionDetailModal open={modalOpen} onOpenChange={onModalOpenChange} transaction={selected} />
    </div>
  )
}
