import { CreditCard, LayoutDashboard, Receipt, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const items = [
  { to: '/dashboard', label: 'Панель управления', icon: LayoutDashboard },
  { to: '/payments', label: 'Платежи', icon: CreditCard },
  { to: '/transactions', label: 'Транзакции', icon: Receipt },
] as const

type SidebarProps = {
  mobileOpen: boolean
  onCloseMobile: () => void
}

export function Sidebar({ mobileOpen, onCloseMobile }: SidebarProps) {
  return (
    <>
      {mobileOpen ? (
        <button
          type="button"
          aria-label="Закрыть меню"
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          onClick={onCloseMobile}
        />
      ) : null}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[240px] shrink-0 -translate-x-full flex-col border-r border-slate-200/80 bg-white px-3 py-6 shadow-lg transition-transform duration-200 ease-out lg:static lg:z-auto lg:translate-x-0 lg:shadow-sm ${
          mobileOpen ? 'translate-x-0' : ''
        }`}
      >
        <div className="mb-6 flex items-center justify-between gap-2 px-2 lg:mb-8">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#A7D7C5]/25 text-lg">💳</div>
            <div>
              <p className="text-sm font-bold text-[#1A1D1F]">SpendFlow</p>
              <p className="text-xs text-[#6F767E]">Финансы</p>
            </div>
          </div>
          <button
            type="button"
            className="rounded-lg p-2 text-[#6F767E] hover:bg-slate-100 lg:hidden"
            aria-label="Закрыть"
            onClick={onCloseMobile}
          >
            <X className="h-5 w-5" strokeWidth={1.75} />
          </button>
        </div>
        <nav className="flex flex-col gap-1">
          {items.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => onCloseMobile()}
              className={({ isActive }) =>
                `flex w-full items-center gap-3 rounded-[14px] py-2.5 pl-3 pr-3 text-left text-sm font-semibold transition-colors ${
                  isActive
                    ? 'bg-[#A7D7C5] text-[#1A1D1F] shadow-sm'
                    : 'text-[#6F767E] hover:bg-[#A7D7C5]/25 hover:text-[#1A1D1F]'
                }`
              }
            >
              <Icon strokeWidth={1.75} className="h-[18px] w-[18px] shrink-0 opacity-80" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto rounded-[24px] bg-[#F8F9FA] p-3 shadow-sm">
          <p className="text-xs font-semibold text-[#1A1D1F]">Система</p>
          <p className="mt-1 text-xs text-[#6F767E]">PostgreSQL · активен</p>
        </div>
      </aside>
    </>
  )
}
