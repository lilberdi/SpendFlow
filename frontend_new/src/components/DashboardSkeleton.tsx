function Pulse({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-xl bg-slate-200/80 ${className}`} />
}

/** Только строка метрик — для первого этапа загрузки дашборда */
export function DashboardMetricsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
      <Pulse className="h-[132px]" />
      <Pulse className="h-[132px]" />
      <Pulse className="h-[132px]" />
      <Pulse className="h-[132px]" />
    </div>
  )
}

/** Нижняя часть: график, боковые блоки, таблица */
export function DashboardBodySkeleton() {
  return (
    <>
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[2fr_1fr]">
        <Pulse className="h-[340px]" />
        <div className="space-y-5">
          <Pulse className="h-[220px]" />
          <Pulse className="h-[200px]" />
        </div>
      </div>
      <Pulse className="h-[240px]" />
    </>
  )
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <DashboardMetricsSkeleton />
      <DashboardBodySkeleton />
    </div>
  )
}
