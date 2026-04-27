import * as Dialog from '@radix-ui/react-dialog'
import { useEffect, useMemo, useState } from 'react'
import type { BudgetDto } from '@/api/dashboardApi'
import { createTransaction, uploadReceiptOcrMock, type ReceiptOcrDto } from '@/api/transactionsApi'
import { BUDGET_CATEGORIES } from '@/lib/budgetCategories'
import { Loader2, X } from 'lucide-react'
import toast from 'react-hot-toast'

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  budgets: BudgetDto[]
  onSaved: () => void
}

type EntryMode = 'manual' | 'receipt'

function overspendMessage(amount: number, category: string, budgets: BudgetDto[]): string | null {
  if (!Number.isFinite(amount) || amount <= 0 || !category) return null
  const b = budgets.find((x) => x.category_name === category)
  if (!b || b.limit_amount <= 0) return null
  const remaining = b.limit_amount - b.spent_amount
  if (amount > remaining) {
    return `Внимание! Этот платеж приведет к перерасходу в категории ${category}.`
  }
  return null
}

export function AddTransactionModal({ open, onOpenChange, budgets, onSaved }: Props) {
  const [mode, setMode] = useState<EntryMode>('manual')
  const [description, setDescription] = useState('')
  const [amount, setAmount] = useState<number>(0)
  const [category, setCategory] = useState<string>(BUDGET_CATEGORIES[0])
  const [file, setFile] = useState<File | null>(null)
  const [ocrResult, setOcrResult] = useState<ReceiptOcrDto | null>(null)
  const [ocrLoading, setOcrLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) {
      setMode('manual')
      setDescription('')
      setAmount(0)
      setCategory(BUDGET_CATEGORIES[0])
      setFile(null)
      setOcrResult(null)
    }
  }, [open])

  const warn = useMemo(() => overspendMessage(amount, category, budgets), [amount, category, budgets])

  const runOcr = async () => {
    if (!file) {
      toast.error('Выберите файл чека')
      return
    }
    setOcrLoading(true)
    try {
      const o = await uploadReceiptOcrMock(file)
      setOcrResult(o)
      setAmount(o.amount)
      setCategory(o.category)
      setDescription(o.merchant ? `Чек: ${o.merchant}` : 'Расход по чеку (OCR)')
      toast.success('Чек распознан (демо)')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Ошибка распознавания')
    } finally {
      setOcrLoading(false)
    }
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!description.trim()) {
      toast.error('Укажите описание')
      return
    }
    if (!amount || amount <= 0) {
      toast.error('Укажите сумму')
      return
    }
    setSubmitting(true)
    try {
      const payload =
        mode === 'receipt'
          ? {
              description: description.trim(),
              amount,
              category,
              tags: ['ocr', 'receipt'],
              source: 'ocr' as const,
              ocr_merchant_raw: description.startsWith('Чек:') ? description.replace(/^Чек:\s*/, '') : null,
              ocr_raw_text: ocrResult?.raw_text_stub ?? null,
              ocr_confidence: ocrResult?.confidence ?? 0.85,
              receipt_storage_key: file?.name ?? null,
            }
          : {
              description: description.trim(),
              amount,
              category,
              tags: ['manual'],
              source: 'manual' as const,
            }
      const created = await createTransaction(payload)
      toast.success('Операция добавлена')
      if (created.limit_warning && created.warning_message) {
        toast(created.warning_message, { icon: '⚠️', duration: 6000 })
      }
      onSaved()
      onOpenChange(false)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Ошибка сохранения')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[60] bg-black/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-[60] max-h-[min(90vh,calc(100vh-24px))] w-[min(440px,calc(100vw-24px))] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-[24px] bg-white p-6 shadow-xl outline-none">
          <div className="mb-4 flex items-start justify-between gap-3">
            <Dialog.Title className="text-lg font-bold text-[#1A1D1F]">Добавить операцию</Dialog.Title>
            <Dialog.Close
              type="button"
              className="rounded-xl p-1.5 text-[#6F767E] hover:bg-slate-100"
              aria-label="Закрыть"
            >
              <X className="h-5 w-5" strokeWidth={1.75} />
            </Dialog.Close>
          </div>
          <Dialog.Description className="sr-only">Новая транзакция вручную или по чеку</Dialog.Description>

          <div className="mb-4 flex rounded-[14px] border border-slate-200 p-1 text-sm font-semibold">
            <button
              type="button"
              onClick={() => setMode('manual')}
              className={`flex-1 rounded-[10px] py-2 transition-colors ${
                mode === 'manual' ? 'bg-[#A7D7C5] text-[#1A1D1F]' : 'text-[#6F767E]'
              }`}
            >
              Ручной ввод
            </button>
            <button
              type="button"
              onClick={() => setMode('receipt')}
              className={`flex-1 rounded-[10px] py-2 transition-colors ${
                mode === 'receipt' ? 'bg-[#A7D7C5] text-[#1A1D1F]' : 'text-[#6F767E]'
              }`}
            >
              Загрузить чек
            </button>
          </div>

          <form onSubmit={(e) => void onSubmit(e)} className="space-y-4">
            {mode === 'receipt' ? (
              <div className="space-y-2">
                <label className="block text-xs font-semibold uppercase tracking-wide text-[#6F767E]">
                  Изображение чека
                </label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  className="w-full text-sm text-[#1A1D1F]"
                />
                <button
                  type="button"
                  onClick={() => void runOcr()}
                  disabled={ocrLoading || !file}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-[14px] border border-slate-200 py-2.5 text-sm font-semibold text-[#1A1D1F] disabled:opacity-50"
                >
                  {ocrLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  Распознать (демо OCR)
                </button>
                <p className="text-xs text-[#6F767E]">
                  Демо: ответ как у SROIE (TOTAL / категория). Файл на сервер не сохраняется.
                </p>
              </div>
            ) : null}

            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-[#6F767E]">Описание</span>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="mt-1 w-full rounded-[14px] border border-slate-200 px-3 py-2.5 text-sm text-[#1A1D1F] outline-none ring-[#A7D7C5] focus:ring-2"
                placeholder="Например, Продукты в Magnum"
              />
            </label>

            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-[#6F767E]">Категория</span>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="mt-1 w-full rounded-[14px] border border-slate-200 px-3 py-2.5 text-sm font-medium text-[#1A1D1F] outline-none ring-[#A7D7C5] focus:ring-2"
              >
                {BUDGET_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-[#6F767E]">Сумма, ₸</span>
              <input
                type="number"
                min={0}
                step={100}
                value={amount || ''}
                onChange={(e) => setAmount(Number.parseFloat(e.target.value) || 0)}
                className="mt-1 w-full rounded-[14px] border border-slate-200 px-3 py-2.5 text-sm text-[#1A1D1F] outline-none ring-[#A7D7C5] focus:ring-2"
              />
            </label>

            {warn ? (
              <p className="rounded-[14px] border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900">
                {warn}
              </p>
            ) : null}

            <div className="flex justify-end gap-2 pt-2">
              <Dialog.Close
                type="button"
                className="rounded-[14px] border border-slate-200 px-4 py-2.5 text-sm font-semibold text-[#6F767E]"
              >
                Отмена
              </Dialog.Close>
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center gap-2 rounded-[14px] bg-[#1A1D1F] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
              >
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Сохранить
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
