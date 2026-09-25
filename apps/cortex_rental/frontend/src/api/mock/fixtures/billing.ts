import type { InvoiceRow, PaymentRow } from '../../contracts'

/** DEMO billing rows for the explicit mock client only. */
export const demoInvoices: InvoiceRow[] = [
  { name: 'DEMO-SINV-0003', customer: 'DEMO-CUST-001', customer_name: 'Production Nord Inc.', posting_date: '2026-09-18', due_date: '2026-10-18', status: 'Draft', docstatus: 0, currency: 'CAD', grand_total: 5173.88, total_advance: 2052.16, outstanding_amount: 3121.72, cortex_rental_transaction: 'DEMO-TRX-2026-001', is_return: 0 },
  { name: 'DEMO-SINV-0002', customer: 'DEMO-CUST-002', customer_name: 'Studio Lumière Montréal', posting_date: '2026-09-05', due_date: '2026-10-05', status: 'Partly Paid', docstatus: 1, currency: 'CAD', grand_total: 2874.38, total_advance: 862.31, outstanding_amount: 1012.07, cortex_rental_transaction: 'DEMO-TRX-2026-002', is_return: 0 },
  { name: 'DEMO-SINV-0001', customer: 'DEMO-CUST-003', customer_name: 'Trequista Events', posting_date: '2026-08-21', due_date: '2026-09-20', status: 'Paid', docstatus: 1, currency: 'CAD', grand_total: 1724.63, total_advance: 517.39, outstanding_amount: 0, cortex_rental_transaction: 'DEMO-TRX-2026-003', is_return: 0 }
]

export const demoPayments: PaymentRow[] = [
  { name: 'DEMO-PE-0004', party: 'DEMO-CUST-001', party_name: 'Production Nord Inc.', posting_date: '2026-09-10', mode_of_payment: 'Carte de crédit', reference_no: 'TPE-88412', paid_amount: 2052.16, unallocated_amount: 0, currency: 'CAD', docstatus: 1, cortex_rental_transaction: 'DEMO-TRX-2026-001' },
  { name: 'DEMO-PE-0003', party: 'DEMO-CUST-002', party_name: 'Studio Lumière Montréal', posting_date: '2026-09-01', mode_of_payment: 'Virement', reference_no: 'VIR-2231', paid_amount: 862.31, unallocated_amount: 0, currency: 'CAD', docstatus: 1, cortex_rental_transaction: 'DEMO-TRX-2026-002' },
  { name: 'DEMO-PE-0002', party: 'DEMO-CUST-002', party_name: 'Studio Lumière Montréal', posting_date: '2026-09-12', mode_of_payment: 'Virement', reference_no: 'VIR-2290', paid_amount: 1000, unallocated_amount: 0, currency: 'CAD', docstatus: 0, cortex_rental_transaction: 'DEMO-TRX-2026-002' }
]
