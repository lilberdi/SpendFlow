import { axiosInstance } from '@/api/axiosInstance'
import type { BudgetDto } from '@/api/dashboardApi'

export type BudgetUpsertPayload = {
  category_name: string
  limit_amount: number
  month: number
  year: number
}

export async function fetchBudgets(month: number, year: number): Promise<BudgetDto[]> {
  const res = await axiosInstance.get<BudgetDto[]>('budgets', { params: { month, year } })
  return res.data
}

export async function upsertBudgetsBatch(items: BudgetUpsertPayload[]): Promise<BudgetDto[]> {
  const res = await axiosInstance.post<BudgetDto[]>('budgets/batch', { items })
  return res.data
}
