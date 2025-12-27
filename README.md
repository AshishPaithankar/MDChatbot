# 🐄 MobileDairyChatBot

**MobileDairyChatBot** is an AI-powered multilingual assistant designed to support dairy collection centers using the Mobile Dairy App. It helps users understand app features, settings, and operations in multiple Indian languages — even when customer support is unavailable.

---

## 🚀 Features

- ✅ **Multilingual support** - 🔍 **RAG architecture** using FAISS (LaBSE), BM25, and LangChain retriever ensemble
- 📄 Supports both **PDF** and **JSON** documents for context-aware answers
- 💬 **Gemini API** for structured, context-grounded responses
- 🧠 **Session-based memory** with conversation tracking using `ConversationBufferWindowMemory`
- 🧾 **Structured JSON output** with `<b>`, `<i>` HTML formatting and YouTube/video links
- 🌐 Supports **Angular-compatible frontend integration**
- 📥 **Upload and update dairy guides** from backend
- 🐄 Specially built for dairy industry use cases (milk collection, farmer records, settings help, etc.)

---

## 🛠️ Tech Stack

| Purpose              | Tool/Library           |
|----------------------|------------------------|
| Language Model       | [Gemini API](https://ai.google.dev/) |
| Vector DB            | FAISS + BM25           |
| Embeddings           | LaBSE (text)           |
| Framework            | LangChain + Django     |
| Frontend Integration | Angular-compatible     |
| Memory               | LangChain Memory + SQLite |
| Hosting              | AWS EC2 (Ubuntu)       |

---

## 🧑‍💻 Getting Started

### 🔧 Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-org/MobileDairyChatBot.git
cd MobileDairyChatBot

# 2. Create a virtual environment (Python 3.12+ recommended)
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies

# If you're using CPU-only version of PyTorch:
pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu

# If you're using GPU version:
pip install torch==2.6.0+cu121

# Then install remaining dependencies:
pip install -r requirements.txt
```

### ⚙️ Environment Variables

Create a `.env` file in the backend directory:

```env
GEMINI_API_KEY=your-gemini-api-key
SECRET_KEY=your-django-secret
ALLOWED_HOSTS=localhost,127.0.0.1
...
```

---

## 🧠 How It Works

1. User asks a question via text.
2. text is processed.
3. LangChain fetches relevant context from FAISS/BM25.
4. Gemini API generates a structured JSON response.
5. The answer is returned with step-by-step instructions, HTML formatting, and multimedia links.

---

## 🗂️ API Endpoints

| Endpoint                        | Method | Description                          |
|----------------------------------|--------|--------------------------------------|
| `/api/chat/`                    | POST   | Chat with the assistant               |
| `/api/chat/history/`           | POST   | Fetch past conversation history       |
| `/api/auth_token/`             | POST   | Obtain authentication token (login)   |

---

## 🧾 API Response Format

The MobileDairyChatBot returns responses in **structured JSON** to support Angular-based rendering, multilingual clarity, and media-rich formatting. The assistant strictly follows two types of responses:

---

### 🔹 Basic Questions

Used for direct explanations or short informative answers.

```
{
  "responseType": "basic",
  "content": {
    "answer": "Paragraph 1 with <b>bold</b>, <i>italic</i>, or <b><i>bold italic</i></b> formatting. Emojis like 🐄, ✅, ❗ may be added for clarity if appropriate.<p>Paragraph 2 introducing a list:</p><ol><li><b>✅ Ordered Item 1:</b> Description with optional formatting and relevant emoji</li><li><b>🔧 Ordered Item 2:</b> Continue list content with emoji only if it adds clarity</li></ol><p>📋 😊 Final paragraph with additional notes, disclaimers, or alerts like ⚠️ if needed.</p>"
  }
}
```
---

### Detailed Procedures
Used for step-by-step instructions with optional images and a tutorial link.

```
{
  "responseType": "procedure",
  "content": {
    "header": {
      "title": "🔧 Procedure Title",
      "introduction": ""
    },
    "body": [
      {
        "id": 1,
        "title": "✅ Step Title",
        "description": ""
      },
      {
        "id": 2,
        "title": "🐄 Step with Image",
        "description": "",
        "imageURL": [
          {
            "url-1": "actual_image_url_1",
            "altText": "Descriptive alt text for accessibility"
          },
          {
            "url-2": "actual_image_url_2",
            "altText": "Descriptive alt text for accessibility"
          }
        ]
      }
    ],
    "footer": {
      "url": "youtube_video_url",
      "title": "Descriptive title of the video tutorial"
    }
  }
}
```
---

## 🤝 Contributing

We welcome contributions from the team!

- Fork the repo
- Create a new feature branch
- Commit and push changes
- Submit a pull request for review

---

## 📄 License

Internal use only – not open-sourced yet.

---

## 📬 Contact

For issues, email the team or raise an issue internally.

---
