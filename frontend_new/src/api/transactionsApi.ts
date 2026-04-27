import type { TransactionDto } from '@/api/dashboardApi'
import { axiosInstance } from '@/api/axiosInstance'

export type TransactionPageDto = {
  items: TransactionDto[]
  total: number
}

export type CreateTransactionPayload = {
  description: string
  amount: number
  category: string
  tags?: string[]
  source?: 'manual' | 'ocr'
  ocr_merchant_raw?: string | null
  ocr_raw_text?: string | null
  ocr_confidence?: number | null
  receipt_storage_key?: string | null
}

export type ReceiptOcrDto = {
  amount: number
  category: string
  merchant: string | null
  confidence: number
  mock: boolean
  dataset_note: string
  raw_text_stub: string
}

export async function fetchTransactionsPaged(params: {
  skip: number
  limit: number
  q?: string
  category?: string
}): Promise<TransactionPageDto> {
  const { skip, limit, q, category } = params
  const res = await axiosInstance.get<TransactionPageDto>('transactions/paged', {
    params: {
      skip,
      limit,
      q: q?.trim() || undefined,
      category: category?.trim() || undefined,
    },
  })
  return res.data
}

export async function createTransaction(payload: CreateTransactionPayload): Promise<TransactionDto> {
  const res = await axiosInstance.post<TransactionDto>('transactions', payload)
  return res.data
}

export async function uploadReceiptOcrMock(file: File): Promise<ReceiptOcrDto> {
  const form = new FormData()
  form.append('file', file)
  const res = await axiosInstance.post<ReceiptOcrDto>('transactions/upload-receipt', form)
  return res.data
}

export async function fetchTransactionById(id: number): Promise<TransactionDto> {
  const res = await axiosInstance.get<TransactionDto>(`transactions/${id}`)
  return res.data
}
