try:
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass


class CortexAIAction(Document):
    """
    A write the assistant proposed. Nothing is executed until the person
    who owns the conversation confirms it; execution then runs the normal
    endpoint under that person's rights and is audited like any other write.
    """

    pass
