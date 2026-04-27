import { Bell, Menu, Plus, Search, UserRound } from 'lucide-react'
import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from '@/components/Sidebar'

const titles: Record<string, string> = {
  '/dashboard': 'Панель управления',
  '/payments': 'Платежи',
  '/transactions': 'Транзакции',
}

export function AppLayout() {
  const { pathname } = useLocation()
  const title = titles[pathname] ?? 'SpendFlow'
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-[#F8F9FA]">
      <Sidebar mobileOpen={mobileMenuOpen} onCloseMobile={() => setMobileMenuOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 px-4 py-4 sm:px-6 lg:px-8 lg:py-5">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              className="inline-flex shrink-0 items-center justify-center rounded-[14px] border border-slate-200/80 bg-white p-2.5 text-[#1A1D1F] shadow-sm lg:hidden"
              aria-label="Открыть меню"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu className="h-5 w-5" strokeWidth={1.75} />
            </button>
            <h1 className="truncate text-xl font-bold tracking-tight text-[#1A1D1F] sm:text-2xl">{title}</h1>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            {pathname === '/dashboard' ? (
              <button
                type="button"
                onClick={() => window.dispatchEvent(new CustomEvent('spendflow:open-add-transaction'))}
                className="inline-flex items-center gap-2 rounded-[16px] bg-[#1A1D1F] px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-[#2d3338]"
              >
                <Plus className="h-4 w-4" strokeWidth={2} />
                Добавить операцию
              </button>
            ) : null}
            <button
              type="button"
              className="hidden items-center gap-2 rounded-[16px] border border-slate-200/80 bg-white px-3 py-2 text-sm text-[#6F767E] shadow-sm sm:flex"
            >
              <Search className="h-4 w-4" strokeWidth={1.75} />
              Поиск
            </button>
            <button
              type="button"
              className="rounded-[16px] border border-slate-200/80 bg-white p-2 text-[#6F767E] shadow-sm"
              aria-label="Уведомления"
            >
              <Bell className="h-4 w-4" strokeWidth={1.75} />
            </button>
            <button
              type="button"
              className="flex items-center gap-2 rounded-[16px] border border-slate-200/80 bg-white px-3 py-2 text-sm text-[#6F767E] shadow-sm"
            >
              <UserRound className="h-4 w-4" strokeWidth={1.75} />
              Профиль
            </button>
          </div>
        </header>
        <main className="flex-1 px-4 pb-8 sm:px-6 lg:px-8 lg:pb-10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
