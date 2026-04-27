import { axiosInstance } from '@/api/axiosInstance'

/** Matches FastAPI `DashboardResponse` */
export type DashboardDto = {
  month_total: number
  forecast: number
  total_limit: number
  remaining: number
  anomalies_this_month: number
  chart_months: string[]
  chart_expense_amounts: number[]
  chart_expense_forecast_flags: boolean[]
  forecast_note: string | null
  budgets: BudgetDto[]
  recent_transactions: TransactionDto[]
  anomaly_ids: number[]
}

export type BudgetDto = {
  id: number
  category_name: string
  limit_amount: number
  month: number
  year: number
  spent_amount: number
  usage_ratio: number
}

export type TransactionDto = {
  id: number
  created_at: string
  description: string
  amount: number
  category: string
  tags: string
  limit_warning?: boolean
  warning_message?: string | null
  source?: string
  ocr_merchant_raw?: string | null
  ocr_raw_text?: string | null
  ocr_confidence?: number | null
  receipt_storage_key?: string | null
}

export type DashboardMetrics = Pick<
  DashboardDto,
  'month_total' | 'forecast' | 'total_limit' | 'remaining' | 'anomalies_this_month'
>

export type ChartData = {
  months: string[]
  expense: number[]
  expenseForecastFlags: boolean[]
  forecast_note: string | null
}

export type RecentTransactionsPayload = {
  transactions: TransactionDto[]
  anomaly_ids: number[]
  budgets: BudgetDto[]
}

/** One HTTP GET shared when getMetrics / getChartData / getRecentTransactions run in parallel */
let dashboardRequest: Promise<DashboardDto> | null = null

/** Сброс кэша после мутаций (транзакции, лимиты), чтобы следующий запрос подтянул свежие данные. */
export function invalidateDashboardCache(): void {
  dashboardRequest = null
}

async function fetchDashboard(): Promise<DashboardDto> {
  if (!dashboardRequest) {
    dashboardRequest = axiosInstance
      .get<DashboardDto>('dashboard')
      .then((res) => res.data)
      .finally(() => {
        dashboardRequest = null
      })
  }
  return dashboardRequest
}

export async function getMetrics(): Promise<DashboardMetrics> {
  const d = await fetchDashboard()
  return {
    month_total: d.month_total,
    forecast: d.forecast,
    total_limit: d.total_limit,
    remaining: d.remaining,
    anomalies_this_month: d.anomalies_this_month,
  }
}

export async function getChartData(): Promise<ChartData> {
  const d = await fetchDashboard()
  const months = d.chart_months
  let flags = d.chart_expense_forecast_flags ?? []
  if (flags.length !== months.length) {
    flags = months.map((_, i) => i === months.length - 1)
  }
  return {
    months,
    expense: d.chart_expense_amounts,
    expenseForecastFlags: flags,
    forecast_note: d.forecast_note,
  }
}

export async function getRecentTransactions(): Promise<RecentTransactionsPayload> {
  const d = await fetchDashboard()
  return {
    transactions: d.recent_transactions,
    anomaly_ids: d.anomaly_ids,
    budgets: d.budgets,
  }
}

/** Full payload in one call (e.g. refetch button) */
export async function getDashboard(): Promise<DashboardDto> {
  return axiosInstance.get<DashboardDto>('dashboard').then((r) => r.data)
}
