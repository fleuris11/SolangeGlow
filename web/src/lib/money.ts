/**
 * Money display, mirroring backend `core.money.Money.format`.
 * Amounts are integers in the smallest unit (`amountMinor`): XOF has no decimals, EUR two.
 */
const EXPONENTS: Record<string, number> = { XOF: 0, XAF: 0, EUR: 2, USD: 2, GBP: 2 };

export function currencyExponent(currency: string): number {
  const exponent = EXPONENTS[currency.toUpperCase()];
  if (exponent === undefined) throw new Error(`Unknown currency: ${currency}`);
  return exponent;
}

/** "15 000 FCFA" (every locale), "25,00 €" (fr, sk), "€25.00" (en). */
export function formatMoney(amountMinor: number, currency: string, locale: string): string {
  if (!Number.isInteger(amountMinor)) throw new Error("amountMinor must be an integer");
  const code = currency.toUpperCase();
  const exponent = currencyExponent(code);
  const major = amountMinor / 10 ** exponent;

  if (code === "XOF" || code === "XAF") {
    const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(major);
    return `${number} FCFA`;
  }
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: code,
    minimumFractionDigits: exponent,
    maximumFractionDigits: exponent,
  }).format(major);
}

/** What a pro types (« 8000 », « 12,50 ») in the smallest unit, or null when it is not a price. */
export function parseMoney(text: string, currency: string): number | null {
  const clean = text.replace(/[\s\u202f\u00a0]/g, "").replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(clean)) return null;
  const exponent = currencyExponent(currency);
  const value = Math.round(Number(clean) * 10 ** exponent);
  return Number.isSafeInteger(value) ? value : null;
}

/** The other way: « 8000 », « 12,50 » (for a field the pro edits). */
export function moneyInput(amountMinor: number, currency: string, locale: string): string {
  const exponent = currencyExponent(currency);
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: exponent,
    maximumFractionDigits: exponent,
    useGrouping: false,
  }).format(amountMinor / 10 ** exponent);
}
