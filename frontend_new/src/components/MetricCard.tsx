type Variant = 'positive' | 'negative' | 'neutral' | 'warning'

const badge: Record<Variant, string> = {
  positive: 'bg-emerald-50 text-emerald-800',
  negative: 'bg-red-50 text-red-700',
  neutral: 'bg-slate-100 text-[#6F767E]',
  warning: 'bg-amber-50 text-amber-900',
}

export function MetricCard({
  title,
  value,
  subtext,
  variant = 'neutral',
  valueSuffix = ' ₸',
  /** When set, replaces the large numeric headline (empty / onboarding states) */
  placeholder,
  /** Доп. пояснение под бейджем (например причина статуса) */
  caption,
}: {
  title: string
  value: string
  subtext: string
  variant?: Variant
  valueSuffix?: string
  placeholder?: string
  caption?: string
}) {
  return (
    <div className="rounded-[24px] bg-white p-5 shadow-sm">
      <p className="m-0 text-sm font-medium text-[#6F767E]">{title}</p>
      {placeholder ? (
        <p className="my-2 text-sm font-medium leading-snug text-[#6F767E]">{placeholder}</p>
      ) : (
        <h2 className="my-1 text-[28px] font-bold leading-tight tracking-tight text-[#1A1D1F]">
          {value}
          {valueSuffix}
        </h2>
      )}
      {!placeholder ? (
        <>
          <span className={`inline-block rounded-lg px-2 py-1 text-xs font-semibold ${badge[variant]}`}>
            {subtext}
          </span>
          {caption ? (
            <p className="mt-2 text-xs leading-relaxed text-[#6F767E]">{caption}</p>
          ) : null}
        </>
      ) : null}
    </div>
  )
}
