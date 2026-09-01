class ConversationNotFoundError(Exception):
    def __init__(
        self,
        conversation_id: int,
    ) -> None:
        self.conversation_id = conversation_id

        super().__init__(f"Conversation {conversation_id} not found")
