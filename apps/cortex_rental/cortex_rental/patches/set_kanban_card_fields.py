"""Show the start date and total on each card of the rentals Kanban board (it only showed the customer name)."""

import json

import frappe

BOARD = "Locations par état"


def execute():
    if frappe.db.exists("Kanban Board", BOARD):
        frappe.db.set_value("Kanban Board", BOARD, "fields", json.dumps(["starts_at", "grand_total"]))
