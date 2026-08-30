"""
Validates/normalizes an OnyxChatClient response into the typed
CortexChatBlock contract the frontend actually renders. This is the
enforcement point for "le chat ne devrait pas afficher un texte non
vérifié comme un fait opérationnel" — every block must match one of the
known, explicitly-typed shapes (schemas/chat_schemas.py) or it doesn't
reach the client at all.
"""

from typing import Any, Dict, List

from pydantic import TypeAdapter, ValidationError

from cortex_rental.schemas.chat_schemas import ChatBlock, ErrorBlock
from cortex_rental.services.onyx_chat_client import OnyxChatResult

_block_adapter = TypeAdapter(ChatBlock)


class ChatResponseTransformer:
    @staticmethod
    def transform(result: OnyxChatResult) -> List[Dict[str, Any]]:
        """
        Returns a list of already-validated block dicts (JSON-safe,
        `model_dump(mode="json")`). A malformed block from the upstream
        client is replaced with a single ErrorBlock rather than either
        crashing the whole response or silently dropping it — the user
        sees that *something* went wrong with that part of the answer,
        which is the honest behavior per the spec's error-handling rules.
        """
        blocks: List[Dict[str, Any]] = []

        for raw_block in result.blocks:
            try:
                validated = _block_adapter.validate_python(raw_block)
                blocks.append(validated.model_dump(mode="json"))
            except ValidationError:
                blocks.append(
                    ErrorBlock(
                        title="Réponse partiellement invalide",
                        safe_message=(
                            "Une partie de la réponse n'a pas pu être affichée correctement — "
                            "aucune action n'a été effectuée."
                        ),
                        retry_allowed=True,
                    ).model_dump(mode="json")
                )

        if not blocks:
            # An upstream response with zero blocks and no error is
            # still surfaced honestly rather than shown as a blank
            # message — matches the spec's "ne cache jamais une
            # incertitude" rule.
            blocks.append(
                ErrorBlock(
                    title="Réponse vide",
                    safe_message="Aucune information n'a pu être produite pour cette demande.",
                    retry_allowed=True,
                ).model_dump(mode="json")
            )

        return blocks
