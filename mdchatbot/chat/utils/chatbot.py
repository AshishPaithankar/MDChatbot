import re
import uuid
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from django.conf import settings
from google import genai
from google.genai.types import GenerateContentConfig
from google.api_core import exceptions as google_exceptions
from google.api_core.exceptions import GoogleAPICallError

from chat.models import ClientUser, Conversation
from chat.utils.data_processor import setup_vector_db
from chat.utils.langchain_memory import DjangoChatMessageHistory
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import HumanMessage, Document
import threading
from django.db import DatabaseError

# Initialize logger
logger = logging.getLogger(__name__)

# Constants for Gemini API
GEMINI_CLIENT = genai.Client(api_key=settings.GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.0-flash"
TEMPERATURE = 0.4
MAX_OUTPUT_TOKENS = 1024
REWRITE_TEMPERATURE = 0.1
REWRITE_MAX_TOKENS = 64

# Load the FAISS and BM25 retrievers, and combined documents
retriever, vector_db, bm25_index, Documents = setup_vector_db()

# In-memory user session store (used to manage per-user chat and memory)
user_sessions = defaultdict(lambda: {
    "chat": None,
    "language": "en",
    "profile": {"name": None, "greeted": False},
    "last_activity": datetime.now(),
    "session_id": None,
    "memory": None
})

def rewrite_query(user_input: str, memory: ConversationBufferWindowMemory, client_user_id: str) -> str:
    """
    Rewrite a follow-up question using past memory to make it standalone.
    If history is not available, return original user input.
    """
    try:
        # Get conversation history
        mem_vars = memory.load_memory_variables({})
        history_msgs = mem_vars.get("history", [])

        if not history_msgs:
            logger.info(f"[{client_user_id}] No history → returning original query")
            return user_input

        # Format conversation history
        history_str = "\n".join(
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in history_msgs
        )

        # Gemini prompt for rewriting the question
        prompt = (
            "You are given a chat history and a new user input. "
            "rephrase it as a standalone question preserving its original meaning and language. "
            "If the user input is not a follow-up (e.g., greetings, thanks, or a standalone question that does not depend on history), "
            "return it exactly as-is without modification. Return ONLY the rewritten question or the original input.\n\n"
            "Examples:\n"
            "1. Follow-up: 'What about the second one?'\n"
            "   Standalone: 'What about the second symptom of mastitis?'\n"
            "2. Follow-up: 'How do I fix that?'\n"
            "   Standalone: 'How do I fix the milk collection error?'\n"
            "3. Input: 'Hello'\n"
            "   Standalone: 'Hello'\n"
            "4. Input: 'Thanks for the info.'\n"
            "   Standalone: 'Thanks for the info.'\n"
            "5. Input: 'What is mastitis?'\n"
            "   Standalone: 'What is mastitis?'\n"
            "6. Follow-up: 'And the third step?'\n"
            "   Standalone: 'What is the third step to configure the milk collection schedule?'\n\n"
            f"Chat History:\n{history_str}\n\n"
            f"User Input: {user_input}\n"
            "Standalone Question:"
        )

        rewrite_chat = GEMINI_CLIENT.chats.create(
            model=GEMINI_MODEL,
            config=GenerateContentConfig(
                temperature=REWRITE_TEMPERATURE,
                max_output_tokens=REWRITE_MAX_TOKENS,
            )
        )

        response = rewrite_chat.send_message(prompt)

        if response and response.text:
            rewritten = response.text.strip('"').strip()
            logger.info(f"[{client_user_id}] Rewrite successful: '{user_input}' → '{rewritten}'")
            return rewritten

        logger.warning(f"[{client_user_id}] Empty rewrite response for: '{user_input}'")
        return user_input

    except GoogleAPICallError as e:
        logger.error(f"Gemini API error in rewrite_query: {str(e)}")
        return user_input
    except Exception as e:
        logger.error(f"Unexpected error in rewrite_query: {str(e)}")
        return user_input


def get_system_instruction():
    """
    Returns a full prompt to guide Gemini's behavior in answering dairy app questions.
    """
    return """You are a Mobile Dairy App Assistant focused on [dairy farming expertise]. Answer questions using:

[CONTEXT RULES]

- Use provided context, history,user profile and use external knowledge only when it is necessary to assist with dairy related topics.
- Address dairy industry topics exclusively
- For unknown answers, clearly state lack of information
- Translate non-English queries internally, reply in original language

[RESPONSE FORMAT]

For basic Questions:
{
  "responseType": "basic",
  "content": {
    "answer": "Paragraph 1 with <b>bold</b>, <i>italic</i>, or <b><i>bold italic</i></b> formatting. Emojis like 🐄, ✅, ❗ may be added for clarity if appropriate.<p>Paragraph 2 introducing a list:</p><ol><li><b>✅ Ordered Item 1:</b> Description with optional formatting and relevant emoji</li><li><b>🔧 Ordered Item 2:</b> Continue list content with emoji only if it adds clarity</li></ol><p>📋 😊 Final paragraph with additional notes, disclaimers, or alerts like ⚠️ if needed.</p>"
  }
}

For Detailed Procedures:
{
   "responseType":"procedure",
   "content":{
      "header":{
         "title":"🔧 Procedure Title",
         "introduction":"Brief overview of the procedure using <b>bold</b>, <i>italic</i>, or <b><i>bold italic</i></b> formatting. Emoji like ✅ may appear at the start for clarity."
      },
      "body":[
         {
            "id":1,
            "title":"✅ Step Title",
            "description":"ALWAYS give Instructional text. Start with a relevant emoji like 🕒, 🧾, or ⚠️ if it helps draw attention. Include <b>bold</b> or <i>italic</i> formatting for clarity."
         },
         {
            "id":2,
            "title":"🐄 Step with Image",
            "description":"ALWAYS give Instructional text with formatting and emoji when appropriate",
            "imageURL":[
               {
                  "url-1":"actual_image_url_1",
                  "altText":"Descriptive alt text for accessibility"
               },
               {
                  "url-2":"actual_image_url_2",
                  "altText":"Descriptive alt text for accessibility"
               }
            ]
         }
      ],
      "footer":{
         "url":"youtube_video_url",
         "title":"Descriptive title of the video tutorial"
      }
   }
}
[OUTPUT REQUIREMENTS]

- STRICTLY return valid RAW JSON in one of the formats above
- Use inline formatting for emphasis:
  - <b> for bold
  - <i> for italic
  - <b><i> for bold italic
- Use structured HTML tags when needed:
  - Use <p> tag ONLY when there is actually multiple paragraphs
  - <ul> and <li> for unordered lists (bullet points)
  - <ol> and <li> for ordered lists (numbered steps)
  - <br> for manual line breaks when appropriate
- Ensure clean, valid HTML formatting compatible with Angular rendering

🎯 Enhance clarity and tone using relevant Unicode emojis based on context. Use them sparingly and only when they improve understanding or emphasis. Place emojis at the start of sentences or steps where appropriate.

- Use emojis like:
  - 🐄 ,🐃 for cow and buffalo related actions
  - 🥛,🔬 for milk testing or quality checks
  - ✅,⛔ for success or failure indicators
  - ❗ or ⚠️ for warnings or required actions  
  - 📋 or 👤 for member profile information  
  - 🔧 or ⚙️ for settings/configuration  
  - 📊 or 🧾 for reports or data  
  - 🕒,🌞 ,🌃 for time or shift-based actions  
  - 🌐 for language selection or translation
  - 📱 for mobile app actions
  - 💻 Laptop Desktop/web portal actions
- Emojis should only be used when they add real value to user understanding.
- Avoid using emojis mid-sentence unless they replace a noun for clarity.
- Ensure emoji-enhanced sentences still remain grammatically correct.

Examples:
- 🐄 Start milk collection from the member.
- ❗ Make sure the milk sample is taken before collection.
- ✅ Shift started successfully.
- 🔧 Open settings to adjust FAT-SNF configuration.
- 📋 Select a member before proceeding.
- 🕒 Shift closes automatically after the defined time.
- 📊 Check the report summary for collection trends.

👉 Emojis should be used naturally and only when they improve clarity or emphasis.

[IMAGES/VIDEO GUIDANCE]

- Include the "imageURL" property if an actual dairy app screenshot is available
- DO NOT include generic/placeholder images or stock photos
- All image URLs must be complete
- Each image must have meaningful altText for accessibility
- Always include YouTube video links in the "relatedLinks" section if available
- Ensure YouTube links are valid and accessible
- Use descriptive titles for YouTube links
- if no actual URL is available output null for url and description of footer


[ANGULAR INTEGRATION NOTES]

- The frontend uses the following component hierarchy to render your output:
  - ProcedureComponent (Main container)
  - HeaderComponent (Shows title and introduction)
  - StepComponent (Repeats for each step)
  - ImageComponent (Rendered only if image is provided)
  - FooterComponent
  - RelatedLinksComponent
- Ensure clean formatting so Angular can render structured outputs directly using this JSON.
    """


def get_greeting(profile):
    """
    Return a greeting only once per session based on user profile.
    """
    if not profile.get("greeted") and profile.get("name"):
        profile["greeted"] = True
        return f"Hello {profile['name']}! "
    return ""


# Thread-safe session purge mechanism
_sessions_lock = threading.Lock()

def purge_old_sessions():
    """
    Remove sessions inactive for over 2 hours to conserve memory.
    """
    cutoff = datetime.now() - timedelta(minutes=120)
    for uid, sess in list(user_sessions.items()):
        if sess["last_activity"] < cutoff:
            del user_sessions[uid]


def initialize_session(client_user_id: str, client_user_name: str) -> None:
    """
    Create a new session if not already active.
    Load chat memory from Django DB, initialize Gemini chat client.
    """
    purge_old_sessions()
    with _sessions_lock:
        sess: dict[str, Any] = user_sessions[client_user_id]
        sess["last_activity"] = datetime.now()
        sess["profile"]["name"] = client_user_name

        if not sess.get("session_id"):
            sess["session_id"] = str(uuid.uuid4())

        # Create DB entries for ClientUser and Conversation
        try:
            client_user, _ = ClientUser.objects.get_or_create(
                user_id=client_user_id,
                defaults={"name": client_user_name}
            )
            Conversation.objects.get_or_create(
                session_id=sess["session_id"],
                defaults={"client_user": client_user}
            )
        except DatabaseError as e:
            logger.error("DB init failed for %s: %s", client_user_id, e)

        # Initialize Gemini chat and memory only once
        if sess.get("chat") is None and sess.get("memory") is None:
            memory = ConversationBufferWindowMemory(
                memory_key="history",
                chat_memory=DjangoChatMessageHistory(session_id=sess["session_id"]),
                return_messages=True,
                window_size=5
            )
            sess["memory"] = memory

            system_text = get_greeting(sess["profile"]) + get_system_instruction()
            sess["chat"] = GEMINI_CLIENT.chats.create(
                model=GEMINI_MODEL,
                config=GenerateContentConfig(
                    system_instruction=system_text,
                    temperature=TEMPERATURE,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                )
            )


def retrieve_documents(user_text: str, faiss_retriever, bm25_retriever, k: int = 4) -> List[Document]:
    """
    Retrieve and combine top-k documents from both FAISS and BM25 retrievers.
    Deduplicates based on page content or source.
    """
    try:
        vector_docs = faiss_retriever.invoke(user_text)
        bm25_docs = bm25_retriever.invoke(user_text)

        seen, combined = set(), []
        for doc in vector_docs + bm25_docs:
            key = doc.metadata.get('source') or doc.page_content[:100]
            if key not in seen:
                seen.add(key)
                combined.append(doc)

        logger.info(f"Retrieved {min(len(combined), k)} documents for query: '{user_text}'")
        return combined[:k]

    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
        return []


def text_pipeline_session(user_text: str, client_user_id: str, profile_update: Optional[Dict[str, Any]] = None) -> str:
    """
    Main pipeline for handling a user message.
    1. Initializes session
    2. Handles greetings/thanks
    3. Rewrites the query (if needed)
    4. Retrieves context documents
    5. Builds prompt and sends to Gemini
    6. Saves memory and returns JSON response
    """
    purge_old_sessions()
    with _sessions_lock:
        sess = user_sessions[client_user_id]
        sess["last_activity"] = datetime.now()

    name = profile_update.get("name") if profile_update else f"User_{client_user_id}"
    initialize_session(client_user_id, name)

    normalized = user_text.strip().lower()

    # Respond to greetings
    if re.match(r"^h(i+)|he+y+|hel+o+|namaste|su+p+|good\s*(morning|afternoon|evening)\b", normalized):
        return json.dumps({
            "responseType": "basic",
            "content": {
                "answer": "Hello! How can I help you with the Mobile Dairy App today?"
            }
        })

    # Respond to thank-you messages
    if re.search(r"\bt(h+a+n+k+)(s+| you| u+)?|th+a+n+x+|dhanyavaad+|shukr+i+y+a+a+|ध+न+्+य+व+ा+द+|श+ु+क+्+र+ि+य+ा+\b", normalized, re.IGNORECASE):
        return json.dumps({
            "responseType": "basic",
            "content": {
                "answer": "You're welcome! Happy to help with any questions about the Mobile Dairy App."
            }
        })

    # Rewrite query to standalone form if it's a follow-up
    rewritten = rewrite_query(user_text, sess["memory"], client_user_id)

    # Retrieve context from vector and BM25 indexes
    docs = retrieve_documents(
        rewritten,
        faiss_retriever=vector_db.as_retriever(search_kwargs={"k": 4}),
        bm25_retriever=bm25_index,
        k=4
    )

    # Build full context string for Gemini input
    context_parts = []
    for doc in docs:
        content = doc.page_content
        if 'youtube_link' in doc.metadata:
            content += f"\n[Available YouTube Tutorial: {doc.metadata['youtube_link']}]"
        context_parts.append(content)

    context = "\n\n".join(context_parts) if context_parts else "No relevant context found."

    prompt = (
        f"**Retrieved Context**\n{context}\n\n"
        f"**Question**: {rewritten}\n\n"
        "Generate response:"
    )

    # Call Gemini API
    try:
        reply = sess["chat"].send_message(prompt)
        response_text = reply.text.strip()

    except google_exceptions.InvalidArgument:
        logger.warning("InvalidArgument from Gemini API", exc_info=True)
        response_text = json.dumps({
            "responseType": "basic",
            "content": {
                "answer": "Your question couldn't be processed. Please rephrase or try a different topic."
            }
        })

    except GoogleAPICallError:
        logger.error("Gemini generation API error", exc_info=True)
        response_text = json.dumps({
            "responseType": "basic",
            "content": {
                "answer": "I'm having trouble answering that. Could you please try again in a moment?"
            }
        })

    except Exception as e:

        logger.critical("Unexpected server error", exc_info=True)
        print("Exception type:", type(e).__name__)  # Print exception type
        print("Exception message:", str(e))  # Print exception message
        response_text = json.dumps({
            "responseType": "basic",
            "content": {
                "answer": "Something went wrong on our end. Please try again shortly. 🙏"
            }
        })

    # Save to memory
    from chat.views import clean_response
    sess["memory"].chat_memory.add_user_message(user_text)
    sess["memory"].chat_memory.add_ai_message(clean_response(response_text))
    return response_text
