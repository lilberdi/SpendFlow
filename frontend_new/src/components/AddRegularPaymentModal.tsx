import * as Dialog from '@radix-ui/react-dialog'
import { useEffect, useState } from 'react'
import { createRegularPayment, type RegularPaymentCreatePayload } from '@/api/paymentsApi'
import { BUDGET_CATEGORIES } from '@/lib/budgetCategories'
import { Loader2, X } from 'lucide-react'
import toast from 'react-hot-toast'

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSaved: () => void
}

const PERIOD_LABELS: { value: RegularPaymentCreatePayload['periodicity']; label: string }[] = [
  { value: 'monthly', label: 'Ежемесячно' },
  { value: 'weekly', label: 'Еженедельно' },
  { value: 'yearly', label: 'Ежегодно' },
]

export function AddRegularPaymentModal({ open, onOpenChange, onSaved }: Props) {
  const [name, setName] = useState('')
  const [amount, setAmount] = useState<number>(0)
  const [category, setCategory] = useState<string>(BUDGET_CATEGORIES[0])
  const [periodicity, setPeriodicity] = useState<RegularPaymentCreatePayload['periodicity']>('monthly')
  const [nextChargeLocal, setNextChargeLocal] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) {
      setName('')
      setAmount(0)
      setCategory(BUDGET_CATEGORIES[0])
      setPeriodicity('monthly')
      setNextChargeLocal('')
    }
  }, [open])

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      toast.error('Укажите название')
      return
    }
    if (!amount || amount <= 0) {
      toast.error('Укажите сумму')
      return
    }
    const payload: RegularPaymentCreatePayload = {
      name: name.trim(),
      amount,
      category_name: category,
      periodicity,
    }
    if (nextChargeLocal.trim()) {
      const d = new Date(nextChargeLocal)
      if (!Number.isNaN(d.getTime())) {
        payload.next_charge_at = d.toISOString()
      }
    }
    setSubmitting(true)
    try {
      await createRegularPayment(payload)
      toast.success('Регулярный платёж добавлен')
      onSaved()
      onOpenChange(false)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Не удалось сохранить')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(100vw-1.5rem,420px)] -translate-x-1/2 -translate-y-1/2 rounded-[24px] border border-slate-100 bg-white p-6 shadow-xl">
          <div className="flex items-start justify-between gap-3">
            <div>
              <Dialog.Title className="text-lg font-bold text-[#1A1D1F]">Регулярный платёж</Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-[#6F767E]">
                Название, сумма, категория и периодичность. Дата следующего списания по умолчанию — 1-е число
                следующего месяца.
              </Dialog.Description>
            </div>
            <Dialog.Close
              type="button"
              className="rounded-full p-1.5 text-[#6F767E] hover:bg-slate-100"
              aria-label="Закрыть"
            >
              <X className="h-5 w-5" />
            </Dialog.Close>
          </div>

          <form className="mt-5 space-y-4" onSubmit={(e) => void onSubmit(e)}>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-[#6F767E]">Название</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded-[14px] border border-slate-200 px-3 py-2.5 text-sm outline-none ring-[#A7D7C5] focus:ring-2"
                placeholder="Например, Интернет"
                autoComplete="off"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-[#6F767E]">Сумма, ₸</label>
              <input
                type="number"
                min={1}
                step={1}
                value={amount || ''}
                onChange={(e) => setAmount(Number(e.target.value))}
                className="mt-1 w-full rounded-[14px] border border-slate-200 px-3 py-2.5 text-sm outline-none ring-[#A7D7C5] focus:ring-2"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-[#6F767E]">Категория</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="mt-1 w-full rounded-[14px] border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none ring-[#A7D7C5] focus:ring-2"
              >
                {BUDGET_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-[#6F767E]">Периодичность</label>
              <select
                value={periodicity}
                onChange={(e) => setPeriodicity(e.target.value as RegularPaymentCreatePayload['periodicity'])}
                className="mt-1 w-full rounded-[14px] border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none ring-[#A7D7C5] focus:ring-2"
              >
                {PERIOD_LABELS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-[#6F767E]">
                Дата следующего списания (необязательно)
              </label>
              <input
                type="datetime-local"
                value={nextChargeLocal}
                onChange={(e) => setNextChargeLocal(e.target.value)}
                className="mt-1 w-full rounded-[14px] border border-slate-200 px-3 py-2.5 text-sm outline-none ring-[#A7D7C5] focus:ring-2"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Dialog.Close
                type="button"
                className="rounded-[14px] px-4 py-2.5 text-sm font-semibold text-[#6F767E] hover:bg-slate-100"
              >
                Отмена
              </Dialog.Close>
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center justify-center gap-2 rounded-[14px] bg-[#1A1D1F] px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
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
