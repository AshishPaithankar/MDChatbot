# chat/utils/langchain_memory.py

from langchain_core.chat_history import BaseChatMessageHistory
from chat.models import Conversation, ConversationHistory
from langchain.schema.messages import AIMessage, HumanMessage

class DjangoChatMessageHistory(BaseChatMessageHistory):
    """
    Custom chat message history that uses Django models to store and retrieve
    conversation history (user + assistant messages) for LangChain memory.
    """

    def __init__(self, session_id: str):
        """
        Initialize the message history with a unique session_id.
        This is typically tied to a user session in the chat system.
        """
        self.session_id = session_id

    @property
    def messages(self):
        """
        Return the full message history as a list of LangChain `HumanMessage` and `AIMessage`.
        Fetches from the Django ConversationHistory model, ordered by request time.
        """
        try:
            convo = Conversation.objects.get(session_id=self.session_id)
            history = ConversationHistory.objects.filter(conversation=convo).order_by("request_at")
            msgs = []
            for h in history:
                if h.user_text:
                    msgs.append(HumanMessage(content=h.user_text))
                if h.assistant_text:
                    msgs.append(AIMessage(content=h.assistant_text))
            return msgs
        except Conversation.DoesNotExist:
            return []

    def add_user_message(self, message: str):
        """
        Add a new user message to the conversation history.
        Creates a new ConversationHistory record with user_text filled.
        """
        convo, _ = Conversation.objects.get_or_create(session_id=self.session_id)
        ConversationHistory.objects.create(conversation=convo, user_text=message)

    def add_ai_message(self, message: str):
        """
        Add an assistant message to the most recent user message entry (if it exists),
        or create a new entry if no unmatched user message exists.
        """
        convo = Conversation.objects.get(session_id=self.session_id)
        last_entry = ConversationHistory.objects.filter(
            conversation=convo, assistant_text__isnull=True
        ).order_by("-request_at").first()

        if last_entry:
            # Update existing record with assistant reply
            last_entry.assistant_text = message
            last_entry.save()
        else:
            # Fallback if user message was not saved first (shouldn't normally happen)
            ConversationHistory.objects.create(conversation=convo, assistant_text=message)

    def clear(self):
        """
        Clear the entire chat history for this session.
        This removes all related ConversationHistory entries.
        """
        convo = Conversation.objects.get(session_id=self.session_id)
        ConversationHistory.objects.filter(conversation=convo).delete()
