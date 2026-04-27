import * as Dialog from '@radix-ui/react-dialog'
import { useEffect, useState } from 'react'
import { fetchBudgets, upsertBudgetsBatch, type BudgetUpsertPayload } from '@/api/budgetsApi'
import { BUDGET_CATEGORIES } from '@/lib/budgetCategories'
import { formatAmountKzt } from '@/lib/formatMoney'
import { Loader2, X } from 'lucide-react'
import toast from 'react-hot-toast'

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  month: number
  year: number
  onSaved: () => void
}

export function BudgetLimitsModal({ open, onOpenChange, month, year, onSaved }: Props) {
  const [limits, setLimits] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const rows = await fetchBudgets(month, year)
        if (cancelled) return
        const next: Record<string, number> = {}
        for (const c of BUDGET_CATEGORIES) next[c] = 0
        const allowed = new Set<string>(BUDGET_CATEGORIES)
        for (const r of rows) {
          if (allowed.has(r.category_name)) {
            next[r.category_name] = r.limit_amount
          }
        }
        setLimits(next)
      } catch (e: unknown) {
        toast.error(e instanceof Error ? e.message : 'Не удалось загрузить лимиты')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open, month, year])

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const items: BudgetUpsertPayload[] = []
    for (const c of BUDGET_CATEGORIES) {
      const v = limits[c] ?? 0
      if (v > 0) {
        items.push({ category_name: c, limit_amount: v, month, year })
      }
    }
    if (items.length === 0) {
      toast.error('Укажите хотя бы один лимит больше 0 ₸')
      return
    }
    setSaving(true)
    try {
      await upsertBudgetsBatch(items)
      toast.success('Лимиты сохранены')
      onSaved()
      onOpenChange(false)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[60] bg-black/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-[60] max-h-[min(90vh,calc(100vh-24px))] w-[min(480px,calc(100vw-24px))] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-[24px] bg-white p-6 shadow-xl outline-none">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <Dialog.Title className="text-lg font-bold text-[#1A1D1F]">Настроить лимиты</Dialog.Title>
              <p className="mt-1 text-sm text-[#6F767E]">
                Период: {String(month).padStart(2, '0')}.{year}. Пустые или 0 — категория не отправляется.
              </p>
            </div>
            <Dialog.Close
              type="button"
              className="rounded-xl p-1.5 text-[#6F767E] hover:bg-slate-100"
              aria-label="Закрыть"
            >
              <X className="h-5 w-5" strokeWidth={1.75} />
            </Dialog.Close>
          </div>
          <Dialog.Description className="sr-only">Форма лимитов по категориям</Dialog.Description>

          {loading ? (
            <p className="py-8 text-center text-sm text-[#6F767E]">Загрузка…</p>
          ) : (
            <form onSubmit={(e) => void onSubmit(e)} className="space-y-4">
              {BUDGET_CATEGORIES.map((cat) => (
                <label key={cat} className="block">
                  <span className="text-xs font-semibold uppercase tracking-wide text-[#6F767E]">{cat}</span>
                  <input
                    type="number"
                    min={0}
                    step={500}
                    value={limits[cat] ?? 0}
                    onChange={(e) =>
                      setLimits((prev) => ({ ...prev, [cat]: Number.parseFloat(e.target.value) || 0 }))
                    }
                    className="mt-1 w-full rounded-[14px] border border-slate-200 px-3 py-2.5 text-sm font-medium text-[#1A1D1F] outline-none ring-[#A7D7C5] focus:ring-2"
                  />
                  <span className="mt-0.5 block text-xs text-[#6F767E]">Лимит: {formatAmountKzt(limits[cat] ?? 0)}</span>
                </label>
              ))}
              <div className="flex justify-end gap-2 pt-2">
                <Dialog.Close
                  type="button"
                  className="rounded-[14px] border border-slate-200 px-4 py-2.5 text-sm font-semibold text-[#6F767E]"
                >
                  Отмена
                </Dialog.Close>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-[14px] bg-[#1A1D1F] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
                >
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  Сохранить
                </button>
              </div>
            </form>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
