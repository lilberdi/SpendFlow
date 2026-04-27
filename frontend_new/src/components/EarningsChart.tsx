import type { TransactionDto } from '@/api/dashboardApi'
import { formatAmountKzt } from '@/lib/formatMoney'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const FACT_FILL = '#A7D7C5'
/** Светлее мяты для столбца прогноза */
const FORECAST_FILL = '#D4EFE4'

type Row = {
  name: string
  expense: number
  isForecast: boolean
}

type TooltipPayload = {
  dataKey?: string | number
  name?: string
  value?: number
  color?: string
  payload?: Row
}

function RuExpenseTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: TooltipPayload[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload as Row | undefined
  const kind = row?.isForecast ? 'Прогноз расходов' : 'Факт расходов'
  const v = typeof payload[0]?.value === 'number' ? payload[0].value : 0
  return (
    <div className="rounded-xl border border-slate-100 bg-white px-3 py-2.5 text-sm shadow-lg">
      <p className="mb-1 font-semibold text-[#1A1D1F]">{label}</p>
      <p className="text-xs text-[#6F767E]">{kind}</p>
      <p className="mt-1 font-semibold text-[#1A1D1F]">{formatAmountKzt(v)}</p>
    </div>
  )
}

export function EarningsChart({
  months,
  expense,
  expenseForecastFlags,
  transactions = [],
}: {
  months: string[]
  expense: number[]
  expenseForecastFlags: boolean[]
  transactions?: TransactionDto[]
}) {
  const data: Row[] = months.map((name, i) => ({
    name,
    expense: expense[i] ?? 0,
    isForecast: Boolean(expenseForecastFlags[i]),
  }))

  const txCount = transactions.length

  return (
    <div className="h-[340px] w-full rounded-[24px] bg-white p-5 shadow-sm">
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-lg font-bold text-[#1A1D1F]">Расходы по месяцам</p>
        {txCount > 0 ? (
          <span className="text-xs font-medium text-[#6F767E]">Недавних операций: {txCount}</span>
        ) : null}
      </div>
      <p className="mb-4 text-sm text-[#6F767E]">
        Факт — мятный (#A7D7C5), прогноз — светлая штриховка и контур. Подсказки на русском.
      </p>
      <ResponsiveContainer width="100%" height="78%">
        <BarChart data={data} barGap={4} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <pattern id="forecastStripes" width={8} height={8} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width={4} height={10} fill="#D4EFE4" />
              <rect x={4} width={4} height={10} fill="#EEF8F3" />
            </pattern>
          </defs>
          <CartesianGrid vertical={false} stroke="#EEF1F4" strokeDasharray="4 4" />
          <XAxis
            dataKey="name"
            tick={{ fill: '#6F767E', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            dy={6}
            interval={0}
            angle={months.length > 6 ? -28 : 0}
            textAnchor={months.length > 6 ? 'end' : 'middle'}
            height={months.length > 6 ? 56 : 30}
          />
          <YAxis
            tick={{ fill: '#6F767E', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
            width={36}
          />
          <Tooltip cursor={{ fill: 'rgba(167, 215, 197, 0.08)' }} content={(props) => <RuExpenseTooltip {...props} />} />
          <Bar dataKey="expense" name="Расход" radius={[10, 10, 0, 0]} maxBarSize={40}>
            {data.map((entry, index) => (
              <Cell
                key={`c-${entry.name}-${index}`}
                fill={entry.isForecast ? 'url(#forecastStripes)' : FACT_FILL}
                stroke={entry.isForecast ? '#8EBDA8' : 'transparent'}
                strokeWidth={entry.isForecast ? 1.5 : 0}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
