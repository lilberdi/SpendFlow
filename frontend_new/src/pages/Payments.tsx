import { useCallback, useEffect, useState } from 'react'
import {
  fetchUpcomingPayments,
  payRegularPaymentNow,
  payableAmount,
  type UpcomingPaymentDto,
} from '@/api/paymentsApi'
import { AddRegularPaymentModal } from '@/components/AddRegularPaymentModal'
import { formatAmountKzt } from '@/lib/formatMoney'
import { AlertTriangle, CalendarDays, Loader2, Plus } from 'lucide-react'
import toast from 'react-hot-toast'

const nextChargeFmt = new Intl.DateTimeFormat('ru-RU', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
})

const periodLabel: Record<string, string> = {
  monthly: 'ежемесячно',
  weekly: 'еженедельно',
  yearly: 'ежегодно',
}

export function Payments() {
  const [items, setItems] = useState<UpcomingPaymentDto[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [payingId, setPayingId] = useState<number | null>(null)
  const [addOpen, setAddOpen] = useState(false)

  const load = useCallback(async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) {
      setLoading(true)
    }
    setError(null)
    try {
      const data = await fetchUpcomingPayments()
      setItems(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Не удалось загрузить платежи')
      setItems([])
      toast.error('Не удалось загрузить платежи')
    } finally {
      if (!opts?.silent) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const onPayNow = async (p: UpcomingPaymentDto) => {
    const preview = payableAmount(p)
    if (preview <= 0) {
      toast.error('Нет суммы к оплате в этом периоде.')
      return
    }
    setPayingId(p.regular_payment_id)
    try {
      const created = await payRegularPaymentNow(p.regular_payment_id)
      toast.success('Транзакция создана')
      if (created.limit_warning && created.warning_message) {
        toast(created.warning_message, { icon: '⚠️', duration: 6000 })
      }
      await load({ silent: true })
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Ошибка оплаты')
    } finally {
      setPayingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-bold text-[#1A1D1F]">Предстоящие платежи</h2>
          <p className="mt-1 text-sm text-[#6F767E]">
            Регулярные платежи по категориям. «К оплате сейчас» — сумма текущего периода из системы; после оплаты
            создаётся транзакция, дата следующего списания сдвигается на период вперёд.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setAddOpen(true)}
          className="inline-flex shrink-0 items-center justify-center gap-2 self-start rounded-[16px] border border-[#A7D7C5]/80 bg-[#F4FBF7] px-4 py-2.5 text-sm font-semibold text-[#1A1D1F] shadow-sm transition hover:bg-[#E8F6EF]"
        >
          <Plus className="h-4 w-4" strokeWidth={2} />
          Добавить регулярный платёж
        </button>
      </div>

      <AddRegularPaymentModal open={addOpen} onOpenChange={setAddOpen} onSaved={() => void load({ silent: true })} />

      {error ? (
        <p className="text-sm text-red-600">Ошибка: {error}</p>
      ) : loading ? (
        <p className="text-sm text-[#6F767E]">Загрузка…</p>
      ) : items.length === 0 ? (
        <div className="rounded-[24px] border border-dashed border-[#A7D7C5]/60 bg-white p-8 text-center shadow-sm">
          <p className="text-sm font-medium text-[#6F767E]">
            Нет регулярных платежей. Добавьте подписку или фиксированный платёж, чтобы видеть предстоящие списания.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((p) => {
            let dateLabel = p.next_charge_at
            try {
              dateLabel = nextChargeFmt.format(new Date(p.next_charge_at))
            } catch {
              dateLabel = p.next_charge_at.slice(0, 10)
            }
            const payAmount = payableAmount(p)
            const busy = payingId === p.regular_payment_id
            const risk = p.overspend_risk
            return (
              <article
                key={p.regular_payment_id}
                className={`flex flex-col rounded-[24px] border p-5 shadow-sm ${
                  risk
                    ? 'border-red-200 bg-red-50/90'
                    : 'border-slate-100 bg-white'
                }`}
              >
                <p className="text-xs font-semibold uppercase tracking-wide text-[#6F767E]">Платёж</p>
                <p className="mt-1 text-lg font-bold text-[#1A1D1F]">{p.name}</p>
                <p className="mt-0.5 text-sm text-[#6F767E]">
                  Категория: <span className="font-semibold text-[#1A1D1F]">{p.category_name}</span>
                  <span className="mx-1.5 text-slate-300">·</span>
                  {periodLabel[p.periodicity] ?? p.periodicity}
                </p>
                {risk ? (
                  <p className="mt-3 flex items-center gap-2 rounded-[12px] border border-red-200 bg-white/80 px-3 py-2 text-sm font-semibold text-red-700">
                    <AlertTriangle className="h-4 w-4 shrink-0" strokeWidth={2} />
                    Риск перерасхода
                  </p>
                ) : null}
                <div className="mt-4 flex items-start gap-2 rounded-[16px] bg-[#F8F9FA] p-3">
                  <CalendarDays className="mt-0.5 h-5 w-5 shrink-0 text-[#A7D7C5]" strokeWidth={1.75} />
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-[#6F767E]">
                      Следующее списание
                    </p>
                    <p className="text-sm font-semibold text-[#1A1D1F]">{dateLabel}</p>
                  </div>
                </div>
                <dl className="mt-4 space-y-2 text-sm">
                  <div className="flex justify-between gap-2">
                    <dt className="text-[#6F767E]">Лимит бюджета</dt>
                    <dd className="font-bold text-[#1A1D1F]">{formatAmountKzt(p.planned_amount)}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-[#6F767E]">Уже потрачено</dt>
                    <dd className="font-semibold text-[#1A1D1F]">{formatAmountKzt(p.spent_amount)}</dd>
                  </div>
                  <div className="flex justify-between gap-2 border-t border-slate-100 pt-2">
                    <dt className="text-[#6F767E]">К оплате сейчас</dt>
                    <dd className="font-bold text-[#1A1D1F]">{formatAmountKzt(payAmount)}</dd>
                  </div>
                </dl>
                <button
                  type="button"
                  disabled={busy || payAmount <= 0}
                  onClick={() => void onPayNow(p)}
                  className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-[16px] bg-[#1A1D1F] py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#2d3338] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2} /> : null}
                  Оплатить сейчас
                </button>
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}
