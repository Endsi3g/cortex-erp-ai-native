// Exporter un tableau : un seul bouton « Exporter » ouvre une fenêtre qui demande le format (PDF ou CSV).
// Le PDF est produit dans le navigateur (aucun service externe, aucune donnée ne quitte l'écran) : tableau paginé en
// format lettre à l'horizontale, police Helvetica, accents français conservés.
window.cortex = window.cortex || {};

(function () {
	// Largeurs de la police Helvetica (millièmes d'em) pour les caractères ASCII imprimables, 32 à 126.
	const W = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584];
	const CP1252 = { "€": 128, "‚": 130, "„": 132, "…": 133, "‘": 145, "’": 146, "“": 147, "”": 148, "•": 149, "–": 150, "—": 151, "™": 153 };

	// Texte → chaîne d'octets WinAnsi (un caractère = un octet) ; ce que la police ne connaît pas devient « ? ».
	function winAnsi(text) {
		let out = "";
		for (const ch of String(text == null ? "" : text).replace(/\s+/g, " ")) {
			const code = ch.codePointAt(0);
			if (code >= 32 && code < 127) out += ch;
			else if (code >= 160 && code <= 255) out += ch;
			else if (CP1252[ch]) out += String.fromCharCode(CP1252[ch]);
			else out += "?";
		}
		return out;
	}

	function widthOf(text, size, bold) {
		let total = 0;
		for (let i = 0; i < text.length; i++) {
			const code = text.charCodeAt(i);
			total += code >= 32 && code < 127 ? W[code - 32] : code >= 192 ? 556 : 556;
		}
		return (total / 1000) * size * (bold ? 1.06 : 1);
	}

	function wrap(text, maxWidth, size) {
		const lines = [];
		let line = "";
		for (const word of text.split(" ")) {
			let candidate = line ? `${line} ${word}` : word;
			if (widthOf(candidate, size) <= maxWidth) {
				line = candidate;
				continue;
			}
			if (line) lines.push(line);
			// Un mot plus long que la colonne (courriel, identifiant) est coupé.
			while (widthOf(word, size) > maxWidth && word.length > 1) {
				let cut = word.length - 1;
				while (cut > 1 && widthOf(word.slice(0, cut), size) > maxWidth) cut--;
				lines.push(word.slice(0, cut));
				word = word.slice(cut);
			}
			line = word;
		}
		if (line) lines.push(line);
		return lines.length ? lines : [""];
	}

	const esc = (s) => s.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");

	// Construit le PDF : `columns` = [{label, key, weight}], `rows` = objets. Renvoie un Blob.
	cortex.buildPdf = function ({ title, subtitle, columns, rows, footer }) {
		const PAGE_W = 792, PAGE_H = 612, M = 36, SIZE = 8.5, LEAD = 11, PAD = 6;
		const usable = PAGE_W - 2 * M;
		const totalWeight = columns.reduce((a, c) => a + (c.weight || 1), 0);
		const xs = [];
		let acc = M;
		const widths = columns.map((c) => ((c.weight || 1) / totalWeight) * usable);
		widths.forEach((w) => {
			xs.push(acc);
			acc += w;
		});
		const pages = [];
		let ops = [];
		let y;
		const text = (x, yy, s, bold, size, gray) => `${gray != null ? `${gray} g ` : ""}BT /${bold ? "F2" : "F1"} ${size} Tf ${x.toFixed(1)} ${yy.toFixed(1)} Td (${esc(s)}) Tj ET${gray != null ? " 0 g" : ""}`;
		const header = () => {
			ops.push(`0.95 g ${M} ${(y - 15).toFixed(1)} ${usable} 18 re f 0 g`);
			columns.forEach((c, i) => ops.push(text(xs[i] + PAD, y - 9, winAnsi(c.label), true, SIZE, 0.25)));
			y -= 20;
		};
		const newPage = (first) => {
			if (ops.length) pages.push(ops);
			ops = [];
			y = PAGE_H - M;
			if (first) {
				ops.push(text(M, y - 12, winAnsi(title), true, 16));
				y -= 20;
				if (subtitle) {
					ops.push(text(M, y - 8, winAnsi(subtitle), false, 9, 0.4));
					y -= 16;
				}
				y -= 6;
			}
			header();
		};
		newPage(true);
		for (const row of rows) {
			const cells = columns.map((c, i) => wrap(winAnsi(row[c.key]), widths[i] - 2 * PAD, SIZE));
			const height = Math.max(...cells.map((l) => l.length)) * LEAD + 8;
			if (y - height < M + 18) newPage(false);
			cells.forEach((lines, i) => lines.forEach((l, n) => ops.push(text(xs[i] + PAD, y - 10 - n * LEAD, l, false, SIZE))));
			y -= height;
			ops.push(`0.9 G 0.5 w ${M} ${y.toFixed(1)} m ${PAGE_W - M} ${y.toFixed(1)} l S 0 G`);
		}
		if (!rows.length) ops.push(text(M + PAD, y - 12, winAnsi("Aucune ligne à exporter."), false, 9, 0.4));
		pages.push(ops);
		const stamp = winAnsi(footer || "Cortex");
		const objects = [];
		const add = (body) => {
			objects.push(body);
			return objects.length;
		};
		add("<< /Type /Catalog /Pages 2 0 R >>");
		add(""); // Pages, rempli plus bas
		add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>");
		add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>");
		const kids = [];
		pages.forEach((pageOps, i) => {
			const label = winAnsi(`Page ${i + 1} / ${pages.length}`);
			const content = pageOps.concat([text(M, 20, stamp, false, 7.5, 0.5), text(PAGE_W - M - widthOf(label, 7.5), 20, label, false, 7.5, 0.5)]).join("\n");
			const contentId = add(`<< /Length ${content.length} >>\nstream\n${content}\nendstream`);
			const pageId = add(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${PAGE_W} ${PAGE_H}] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents ${contentId} 0 R >>`);
			kids.push(`${pageId} 0 R`);
		});
		objects[1] = `<< /Type /Pages /Kids [${kids.join(" ")}] /Count ${pages.length} >>`;
		let pdf = "%PDF-1.4\n";
		const offsets = [];
		objects.forEach((body, i) => {
			offsets.push(pdf.length);
			pdf += `${i + 1} 0 obj\n${body}\nendobj\n`;
		});
		const xref = pdf.length;
		pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${offsets.map((o) => `${String(o).padStart(10, "0")} 00000 n \n`).join("")}trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
		const bytes = new Uint8Array(pdf.length);
		for (let i = 0; i < pdf.length; i++) bytes[i] = pdf.charCodeAt(i) & 255;
		return new Blob([bytes], { type: "application/pdf" });
	};

	cortex.buildCsv = function ({ columns, rows }) {
		const q = (v) => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
		const lines = [columns.map((c) => q(c.label)).join(",")].concat(rows.map((r) => columns.map((c) => q(r[c.key])).join(",")));
		return new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
	};

	function download(blob, name) {
		const link = document.createElement("a");
		link.href = URL.createObjectURL(blob);
		link.download = name;
		document.body.appendChild(link);
		link.click();
		link.remove();
		window.setTimeout(() => URL.revokeObjectURL(link.href), 2000);
	}

	// Un seul bouton côté écran : cette fenêtre demande le format. `spec` = {title, subtitle, columns, rows, filename}.
	cortex.exportData = function (spec) {
		const count = (spec.rows || []).length;
		const choice = (value, label, hint, checked) => `<label class="cx-export-choice"><input type="radio" name="cx-export-format" value="${value}"${checked ? " checked" : ""}><span><b>${label}</b><small>${hint}</small></span></label>`;
		const dialog = new frappe.ui.Dialog({
			title: __("Exporter"),
			fields: [
				{ fieldtype: "HTML", fieldname: "intro", options: `<p class="text-muted">${count ? __("{0} ligne(s) seront exportées, telles qu'elles s'affichent.", [count]) : __("Il n'y a aucune ligne à exporter pour ce filtre.")}</p>` },
				{
					fieldtype: "HTML",
					fieldname: "format",
					options: `<div class="cx-export">${choice("pdf", __("PDF"), __("Un document à lire, imprimer ou envoyer."), true)}${choice("csv", __("CSV"), __("Un tableur à ouvrir dans Excel ou Google Sheets."), false)}</div>`,
				},
			],
			primary_action_label: __("Télécharger"),
			primary_action: () => {
				const format = dialog.$wrapper.find("input[name=cx-export-format]:checked").val() || "pdf";
				const name = `${spec.filename || "export"}-${frappe.datetime.get_today()}`;
				if (format === "pdf") {
					const blob = cortex.buildPdf({ title: spec.title, subtitle: spec.subtitle, columns: spec.columns, rows: spec.rows, footer: `Cortex · ${spec.title} · ${frappe.datetime.get_today()}` });
					download(blob, `${name}.pdf`);
				} else {
					download(cortex.buildCsv(spec), `${name}.csv`);
				}
				dialog.hide();
				frappe.show_alert({ message: format === "pdf" ? __("PDF téléchargé.") : __("CSV téléchargé."), indicator: "green" });
			},
		});
		dialog.show();
	};
})();
