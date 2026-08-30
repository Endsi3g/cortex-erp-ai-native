// Shared date formatting — the one Frappe Datetime field wire format
// (`YYYY-MM-DD HH:mm:ss`) every Cortex page sends to the backend.
// Extracted here once it was needed by a second page (Transaction
// Composer) verbatim identical to how CortexAvailability.vue already
// used it — not introduced speculatively ahead of a real second caller.

export function fmtDateTime(d) {
	const pad = (n) => String(n).padStart(2, "0");
	return (
		`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
		`${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
	);
}

export function addDays(d, n) {
	const date = new Date(d);
	date.setDate(date.getDate() + n);
	return date;
}
