"""Create the shared Kanban board of rentals by state.

Columns are the raw `rental_state` Select values (Frappe stores the column name as the field value). Moving a
card still goes through the server-side state machine, which refuses transitions that need an approval.
"""

import json

import frappe

BOARD = "Locations par état"
COLUMNS = (
    ("Quote", "Gray"),
    ("Reservation", "Blue"),
    ("Contract", "Purple"),
    ("Checked Out", "Orange"),
    ("Returned", "Green"),
    ("Closed", "Green"),
    ("Disputed", "Red"),
    ("Quarantine", "Yellow"),
    ("Cancelled", "Red"),
)


def execute():
    if frappe.db.exists("Kanban Board", BOARD):
        return
    board = frappe.get_doc(
        {
            "doctype": "Kanban Board",
            "kanban_board_name": BOARD,
            "reference_doctype": "Cortex Rental Transaction",
            "field_name": "rental_state",
            "private": 0,
            "show_labels": 0,
            "fields": json.dumps(["starts_at", "grand_total"]),
            "columns": [{"column_name": name, "status": "Active", "indicator": color} for name, color in COLUMNS],
        }
    )
    board.insert(ignore_permissions=True)
