try:
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass


class CortexImportBatch(Document):
    """
    One CSV import into the active company: the file, the column mapping,
    the per-row validation result and every document it created, so the
    batch can be rolled back record by record.
    """

    pass
