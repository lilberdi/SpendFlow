import { axiosInstance } from '@/api/axiosInstance'
import { invalidateDashboardCache, type TransactionDto } from '@/api/dashboardApi'

export type UpcomingPaymentDto = {
  regular_payment_id: number
  name: string
  category_name: string
  periodicity: string
  planned_amount: number
  spent_amount: number
  /** Сумма к оплате за текущий период (сервер, из БД). */
  pay_now_amount: number
  next_charge_at: string
  overspend_risk: boolean
}

export type RegularPaymentCreatePayload = {
  name: string
  amount: number
  category_name: string
  periodicity: 'monthly' | 'weekly' | 'yearly'
  next_charge_at?: string | null
}

export async function fetchUpcomingPayments(): Promise<UpcomingPaymentDto[]> {
  const res = await axiosInstance.get<UpcomingPaymentDto[]>('payments/upcoming')
  return res.data
}

/** Сумма для кнопки «Оплатить сейчас» — совпадает с полем с бэкенда. */
export function payableAmount(p: UpcomingPaymentDto): number {
  return Math.max(0, Math.round(p.pay_now_amount * 100) / 100)
}

export async function createRegularPayment(payload: RegularPaymentCreatePayload): Promise<UpcomingPaymentDto> {
  const res = await axiosInstance.post<UpcomingPaymentDto>('payments/regular', payload)
  return res.data
}

export async function payRegularPaymentNow(regularPaymentId: number): Promise<TransactionDto> {
  const res = await axiosInstance.post<TransactionDto>(`payments/regular/${regularPaymentId}/pay`)
  invalidateDashboardCache()
  return res.data
}
