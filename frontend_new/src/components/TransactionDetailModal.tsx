import * as Dialog from '@radix-ui/react-dialog'
import type { TransactionDto } from '@/api/dashboardApi'
import { formatAmountKzt } from '@/lib/formatMoney'
import { X } from 'lucide-react'

const fullDateFmt = new Intl.DateTimeFormat('ru-RU', {
  dateStyle: 'full',
  timeStyle: 'medium',
  timeZone: 'UTC',
})

function parseTags(tags: string): string[] {
  if (!tags.trim()) return []
  return tags
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean)
}

export function TransactionDetailModal({
  open,
  onOpenChange,
  transaction,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  transaction: TransactionDto | null
}) {
  const rows =
    transaction != null
      ? (() => {
          let fullDate = transaction.created_at
          try {
            fullDate = fullDateFmt.format(new Date(transaction.created_at))
          } catch {
            fullDate = transaction.created_at.replace('T', ' ')
          }
          const tagList = parseTags(transaction.tags)
          return [
            { label: 'ID', value: String(transaction.id) },
            { label: 'Дата и время', value: fullDate },
            { label: 'Категория', value: transaction.category },
            { label: 'Название', value: transaction.description },
            { label: 'Сумма', value: formatAmountKzt(transaction.amount) },
            {
              label: 'Теги',
              value: tagList.length ? tagList.join(', ') : '—',
            },
          ] as { label: string; value: string }[]
        })()
      : []

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      {transaction ? (
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(440px,calc(100vw-24px))] -translate-x-1/2 -translate-y-1/2 rounded-[24px] bg-white p-6 shadow-xl outline-none">
            <div className="mb-4 flex items-start justify-between gap-3">
              <Dialog.Title className="text-lg font-bold text-[#1A1D1F]">Детали транзакции</Dialog.Title>
              <Dialog.Close
                type="button"
                className="rounded-xl p-1.5 text-[#6F767E] transition-colors hover:bg-slate-100 hover:text-[#1A1D1F]"
                aria-label="Закрыть"
              >
                <X className="h-5 w-5" strokeWidth={1.75} />
              </Dialog.Close>
            </div>
            <Dialog.Description className="sr-only">
              Полная информация о выбранной транзакции
            </Dialog.Description>
            <dl className="space-y-3 text-sm">
              {rows.map(({ label, value }) => (
                <div
                  key={label}
                  className="flex flex-col gap-0.5 border-b border-slate-100 pb-3 last:border-0 last:pb-0"
                >
                  <dt className="text-xs font-semibold uppercase tracking-wide text-[#6F767E]">{label}</dt>
                  <dd className="font-medium text-[#1A1D1F]">{value}</dd>
                </div>
              ))}
            </dl>
          </Dialog.Content>
        </Dialog.Portal>
      ) : null}
    </Dialog.Root>
  )
}
