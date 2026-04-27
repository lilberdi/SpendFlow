import { useCallback, useEffect, useState } from 'react'
import {
  getChartData,
  getMetrics,
  getRecentTransactions,
  invalidateDashboardCache,
  type BudgetDto,
  type ChartData,
  type DashboardMetrics,
  type RecentTransactionsPayload,
} from '@/api/dashboardApi'
import { AddTransactionModal } from '@/components/AddTransactionModal'
import { BudgetLimitsModal } from '@/components/BudgetLimitsModal'
import { DashboardBodySkeleton, DashboardMetricsSkeleton } from '@/components/DashboardSkeleton'
import { EarningsChart } from '@/components/EarningsChart'
import { MetricCard } from '@/components/MetricCard'
import { formatAmountKzt, formatNumberRu } from '@/lib/formatMoney'
import { Car, ShoppingBag, Target, Utensils, Wallet } from 'lucide-react'
import type { ReactNode } from 'react'
import toast from 'react-hot-toast'

const EMPTY_HINT =
  'Пока нет транзакций. Добавьте первый расход, чтобы увидеть аналитику.'

const categoryIcon: Record<string, ReactNode> = {
  Transport: <Car className="h-4 w-4 text-[#1A1D1F]/80" strokeWidth={1.75} />,
  Food: <Utensils className="h-4 w-4 text-[#1A1D1F]/80" strokeWidth={1.75} />,
  Shopping: <ShoppingBag className="h-4 w-4 text-[#1A1D1F]/80" strokeWidth={1.75} />,
  Leisure: <Target className="h-4 w-4 text-[#1A1D1F]/80" strokeWidth={1.75} />,
  Bills: <Wallet className="h-4 w-4 text-[#1A1D1F]/80" strokeWidth={1.75} />,
}

function isDashboardEmpty(metrics: DashboardMetrics, recent: RecentTransactionsPayload) {
  const noTx = recent.transactions.length === 0
  const noSpend = metrics.month_total === 0
  return noTx && noSpend
}

type SpendRiskLevel = 'ok' | 'warning' | 'critical'

function deriveSpendRisk(
  budgets: BudgetDto[],
  mlAnomalyCount: number,
): { level: SpendRiskLevel; headline: string; subtext: string; caption: string } {
  let worst: BudgetDto | null = null
  for (const b of budgets) {
    if (b.limit_amount <= 0) continue
    if (!worst || b.usage_ratio > worst.usage_ratio) worst = b
  }
  const maxR = worst?.usage_ratio ?? 0
  if (worst && maxR >= 2) {
    return {
      level: 'critical',
      headline: 'Аномалия',
      subtext: 'Критично по лимитам',
      caption: `Обнаружен резкий рост трат в категории «${worst.category_name}»: расходы свыше 200% от лимита.`,
    }
  }
  if (worst && maxR > 1.2) {
    const overPct = Math.round((maxR - 1) * 100)
    return {
      level: 'warning',
      headline: 'Внимание',
      subtext: 'Превышение лимита',
      caption: `Категория «${worst.category_name}»: траты выше лимита более чем на 20% (около +${overPct}% к лимиту).`,
    }
  }
  if (mlAnomalyCount > 0) {
    return {
      level: 'warning',
      headline: 'Внимание',
      subtext: 'Нетипичные операции',
      caption: `За месяц отмечено ${mlAnomalyCount} операций с необычной суммой по сравнению с историей.`,
    }
  }
  return {
    level: 'ok',
    headline: 'Стабильно',
    subtext: 'Лимиты в норме',
    caption: 'Траты по категориям не превышают 120% от лимитов.',
  }
}

function nowUtcMonthYear() {
  const d = new Date()
  return { month: d.getUTCMonth() + 1, year: d.getUTCFullYear() }
}

export function Dashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [chart, setChart] = useState<ChartData | null>(null)
  const [recent, setRecent] = useState<RecentTransactionsPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [budgetModalOpen, setBudgetModalOpen] = useState(false)
  const [addTxModalOpen, setAddTxModalOpen] = useState(false)

  const reloadDashboard = useCallback(async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) {
      setLoading(true)
      setError(null)
    }
    try {
      invalidateDashboardCache()
      const [m, c, r] = await Promise.all([getMetrics(), getChartData(), getRecentTransactions()])
      setError(null)
      setMetrics(m)
      setChart(c)
      setRecent(r)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Не удалось загрузить панель'
      if (!opts?.silent) {
        setError(msg)
        setMetrics(null)
        setChart(null)
        setRecent(null)
      }
      toast.error(msg)
    } finally {
      if (!opts?.silent) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    void reloadDashboard()
  }, [reloadDashboard])

  useEffect(() => {
    const openAdd = () => setAddTxModalOpen(true)
    const openBudgets = () => setBudgetModalOpen(true)
    window.addEventListener('spendflow:open-add-transaction', openAdd)
    window.addEventListener('spendflow:open-budget-limits', openBudgets)
    return () => {
      window.removeEventListener('spendflow:open-add-transaction', openAdd)
      window.removeEventListener('spendflow:open-budget-limits', openBudgets)
    }
  }, [])

  if (error) {
    return <p className="text-sm text-red-600">Ошибка: {error}</p>
  }

  if (loading || !metrics || !chart || !recent) {
    return (
      <div className="space-y-6">
        <DashboardMetricsSkeleton />
        <DashboardBodySkeleton />
      </div>
    )
  }

  const empty = isDashboardEmpty(metrics, recent)
  const pctUsed = metrics.total_limit > 0 ? (metrics.month_total / metrics.total_limit) * 100 : 0
  const savingsVariant =
    metrics.remaining < 0 ? 'negative' : pctUsed > 90 ? 'negative' : pctUsed > 70 ? 'neutral' : 'positive'
  const spendRisk = deriveSpendRisk(recent.budgets, metrics.anomalies_this_month)
  const anomalyVariant =
    spendRisk.level === 'critical' ? 'negative' : spendRisk.level === 'warning' ? 'warning' : 'positive'

  const chartHasPoints = chart.months.length > 0 && chart.expense.some((v) => v > 0)

  const lastMonthLabel = chart.months.length ? chart.months[chart.months.length - 1] : ''
  const { month: budgetMonth, year: budgetYear } = nowUtcMonthYear()

  return (
    <div className="space-y-6">
      <AddTransactionModal
        open={addTxModalOpen}
        onOpenChange={setAddTxModalOpen}
        budgets={recent.budgets}
        onSaved={() => void reloadDashboard({ silent: true })}
      />
      <BudgetLimitsModal
        open={budgetModalOpen}
        onOpenChange={setBudgetModalOpen}
        month={budgetMonth}
        year={budgetYear}
        onSaved={() => void reloadDashboard({ silent: true })}
      />

      {empty ? (
        <div className="rounded-[24px] border border-dashed border-[#A7D7C5]/60 bg-white p-6 text-center shadow-sm">
          <p className="text-base font-semibold text-[#1A1D1F]">{EMPTY_HINT}</p>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Всего расходов"
          value={formatNumberRu(metrics.month_total)}
          subtext="Текущий месяц"
          variant="neutral"
          placeholder={empty ? EMPTY_HINT : undefined}
        />
        <MetricCard
          title={`Прогноз${lastMonthLabel ? ` (${lastMonthLabel})` : ''}`}
          value={formatNumberRu(metrics.forecast)}
          subtext="Проекция на следующий месяц"
          variant="neutral"
          placeholder={empty ? EMPTY_HINT : undefined}
        />
        <MetricCard
          title="Сбережения / лимит"
          value={formatNumberRu(Math.max(0, metrics.remaining))}
          subtext={
            metrics.remaining < 0
              ? `Превышение на ${formatNumberRu(Math.abs(metrics.remaining))} ₸`
              : 'Остаток до потолка'
          }
          variant={savingsVariant}
          valueSuffix={metrics.remaining < 0 ? '' : ' ₸'}
          placeholder={empty ? EMPTY_HINT : undefined}
        />
        <MetricCard
          title="Аномалии и лимиты"
          value={empty ? '' : spendRisk.headline}
          subtext={empty ? '' : spendRisk.subtext}
          variant={anomalyVariant}
          valueSuffix=""
          placeholder={empty ? EMPTY_HINT : undefined}
          caption={empty ? undefined : spendRisk.caption}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[2fr_1fr]">
        <div>
          {empty || !chartHasPoints ? (
            <div className="flex min-h-[320px] flex-col items-center justify-center rounded-[24px] bg-white p-8 text-center shadow-sm">
              <p className="max-w-md text-sm font-medium text-[#6F767E]">{EMPTY_HINT}</p>
            </div>
          ) : (
            <>
              <EarningsChart
                months={chart.months}
                expense={chart.expense}
                expenseForecastFlags={chart.expenseForecastFlags}
                transactions={recent.transactions}
              />
              {chart.forecast_note ? (
                <p className="mt-2 text-xs text-[#6F767E]">{chart.forecast_note}</p>
              ) : null}
            </>
          )}
        </div>
        <div className="space-y-5">
          <div className="rounded-[24px] bg-white p-5 shadow-sm">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-lg font-bold text-[#1A1D1F]">Лимиты по категориям</p>
              <button
                type="button"
                onClick={() => setBudgetModalOpen(true)}
                className="shrink-0 rounded-[14px] border border-slate-200 bg-[#F8F9FA] px-3 py-2 text-sm font-semibold text-[#1A1D1F] shadow-sm hover:bg-[#A7D7C5]/30"
              >
                Настроить лимиты
              </button>
            </div>
            {recent.budgets.length === 0 ? (
              <p className="text-sm text-[#6F767E]">Нет бюджетов на этот месяц.</p>
            ) : (
              <div className="space-y-4">
                {[...recent.budgets]
                  .sort((a, b) => b.usage_ratio - a.usage_ratio)
                  .map((b) => (
                    <div key={b.id}>
                      <div className="mb-1 flex items-center gap-2">
                        <span className="flex h-9 w-9 items-center justify-center rounded-full border border-[#A7D7C5]/50 bg-[#A7D7C5]/15">
                          {categoryIcon[b.category_name] ?? (
                            <span className="text-xs font-bold text-[#6F767E]">{b.category_name[0]}</span>
                          )}
                        </span>
                        <span className="text-sm font-semibold text-[#1A1D1F]">{b.category_name}</span>
                      </div>
                      <p className="mb-2 pl-11 text-xs text-[#6F767E]">
                        {formatAmountKzt(b.spent_amount)} / {formatAmountKzt(b.limit_amount)} ·{' '}
                        {(b.usage_ratio * 100).toFixed(0)}%
                      </p>
                      <div className="pl-11">
                        <div className="h-3.5 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className="h-full rounded-full bg-[#A7D7C5] transition-all"
                            style={{ width: `${Math.min(100, b.usage_ratio * 100)}%` }}
                          />
                        </div>
                        {b.usage_ratio >= 1 ? (
                          <p className="mt-1 text-xs font-medium text-red-600">Критично · превышен лимит</p>
                        ) : null}
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>

          <div className="rounded-[24px] bg-white p-5 shadow-sm">
            <p className="mb-3 text-lg font-bold text-[#1A1D1F]">Последние действия</p>
            {recent.transactions.length === 0 ? (
              <p className="text-sm text-[#6F767E]">{EMPTY_HINT}</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {recent.transactions.slice(0, 8).map((tx) => {
                  const warn = recent.anomaly_ids.includes(tx.id)
                  return (
                    <div key={tx.id} className="flex items-center justify-between gap-3 py-3 first:pt-0">
                      <div className="flex min-w-0 items-center gap-3">
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[#A7D7C5]/50 bg-[#A7D7C5]/15 text-sm">
                          {warn ? '⚠️' : categoryIcon[tx.category] ?? '💸'}
                        </span>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-[#1A1D1F]">{tx.description}</p>
                          <p className="text-xs text-[#6F767E]">{tx.category}</p>
                        </div>
                      </div>
                      <p className="shrink-0 text-sm font-bold text-[#1A1D1F]">{formatAmountKzt(tx.amount)}</p>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-[24px] bg-white p-5 shadow-sm">
        <p className="mb-4 text-lg font-bold text-[#1A1D1F]">История транзакций</p>
        {recent.transactions.length === 0 ? (
          <p className="text-sm font-medium text-[#6F767E]">{EMPTY_HINT}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="text-xs font-semibold uppercase tracking-wide text-[#6F767E]">
                  <th className="pb-3 pr-4">Операция</th>
                  <th className="pb-3 pr-4">Когда</th>
                  <th className="pb-3 pr-4 text-right">Сумма</th>
                  <th className="pb-3">Статус</th>
                </tr>
              </thead>
              <tbody>
                {recent.transactions.map((tx) => {
                  const warn = recent.anomaly_ids.includes(tx.id)
                  return (
                    <tr key={tx.id} className={warn ? 'bg-amber-50/60' : ''}>
                      <td className="border-t border-slate-100 py-3 pr-4">
                        <p className="font-semibold text-[#1A1D1F]">{tx.description}</p>
                        <p className="text-xs text-[#6F767E]">{tx.category}</p>
                      </td>
                      <td className="border-t border-slate-100 py-3 pr-4 text-[#6F767E]">
                        {tx.created_at.slice(0, 19).replace('T', ' ')}
                      </td>
                      <td className="border-t border-slate-100 py-3 pr-4 text-right font-bold text-[#1A1D1F]">
                        {formatAmountKzt(tx.amount)}
                      </td>
                      <td className="border-t border-slate-100 py-3">
                        {warn ? (
                          <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-900">
                            Внимание
                          </span>
                        ) : (
                          <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800">
                            ОК
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
