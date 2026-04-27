/** Число без символа валюты (группировка ru-RU). */
export function formatNumberRu(n: number) {
  return Math.round(n)
    .toLocaleString('ru-RU')
    .replace(/\u00a0/g, ' ')
}

/** Сумма с ₸ после числа. */
export function formatAmountKzt(n: number) {
  return `${formatNumberRu(n)} ₸`
}
