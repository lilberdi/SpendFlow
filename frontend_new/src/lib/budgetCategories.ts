/** Категории для лимитов и ручного ввода (согласованы с seed / backend). */
export const BUDGET_CATEGORIES = ['Transport', 'Food', 'Leisure', 'Shopping', 'Bills'] as const

export type BudgetCategory = (typeof BUDGET_CATEGORIES)[number]
