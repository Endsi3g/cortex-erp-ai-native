// Currency formatting for financial screens (Accounting P&L today).
// `Intl.NumberFormat` per design-system-accounting-pnl.md §11 — never a
// manual `$` + toFixed() string build, which mishandles thousands
// separators and negative-value conventions across locales.

export function formatCurrency(value, currency, locale) {
	const amount = Number(value) || 0;
	return new Intl.NumberFormat(locale || "en-US", {
		style: "currency",
		currency: currency || "USD",
		minimumFractionDigits: 2,
	}).format(amount);
}
