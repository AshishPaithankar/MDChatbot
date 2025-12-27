from rest_framework.views import APIView
from chat.utils.chatbot import text_pipeline_session
from .models import ClientUser, Conversation, ConversationHistory
from datetime import datetime, timedelta
import json
import re
from rest_framework.response import Response
from rest_framework import status

def clean_response(response_text: str) -> str:
    """
    Cleans the raw Gemini response by:
    - Removing markdown-style ```json code blocks if present.
    - Ensuring valid JSON output.
    - Wrapping raw text in JSON if it's not already valid.
    """
    match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            pass

    try:
        parsed = json.loads(response_text)
        return json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps({"answer": response_text.strip()}, ensure_ascii=False)


class ChatAPIView(APIView):
    """
    POST endpoint for handling chat queries to the Mobile Dairy Assistant.
    Required fields: client_id, client_user_id, query
    """

    def post(self, request):
        if not request.data.get('client_id'):
            return Response({"error": "Missing Mandatory field client"}, status=status.HTTP_400_BAD_REQUEST)

        if request.data.get('client_id') not in [1]:
            return Response({"error": "Invalid client, you do not have access to Assistant"}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        print("Received data:", data)  # Debug logging (optional)

        client_user_id = data.get('client_user_id')
        client_user_name = data.get('client_user_name', 'ClientUser')
        client_id = data.get('client_id')

        # Pass query to the main processing pipeline
        response_text = text_pipeline_session(
            user_text=data['query'],
            client_user_id=client_user_id,
            profile_update={"name": client_user_name}
        )

        # Clean and prepare the Gemini response
        cleaned_response = clean_response(response_text)

        return Response({
            "response": json.loads(cleaned_response),
            "Client": client_id,
            "client_user_id": client_user_id
        })


class ConversationHistoryAPIView(APIView):
    """
    POST endpoint to retrieve historical conversation logs.
    Filters by optional start_date and end_date.
    """

    def post(self, request):
        client_id = request.data.get('client_id')
        client_user_id = request.data.get('client_user_id')
        start_date = request.data.get('start_date')  # Optional (YYYY-MM-DD)
        end_date = request.data.get('end_date')      # Optional (YYYY-MM-DD)

        # Validate required inputs
        if not client_id:
            return Response({"error": "client_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not client_user_id:
            return Response({"error": "client_user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate and parse date inputs
        try:
            if start_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if end_date:
                # Include full day by extending to 23:59:59
                end_date = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch client user from DB
        try:
            client_user = ClientUser.objects.get(client_id=client_id, user_id=client_user_id)
        except ClientUser.DoesNotExist:
            return Response({"error": "Client user not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get all conversation sessions for the user
        conversations = Conversation.objects.filter(client_user=client_user).order_by("-start_time")

        # Apply optional time filters
        if start_date and end_date:
            conversations = conversations.filter(start_time__range=[start_date, end_date])
        elif start_date:
            conversations = conversations.filter(start_time__gte=start_date)
        elif end_date:
            conversations = conversations.filter(start_time__lte=end_date)

        # Format conversation logs
        history_data = []
        for convo in conversations:
            messages = ConversationHistory.objects.filter(conversation=convo).order_by("request_at")
            chat_log = [
                {
                    "user_text": msg.user_text,
                    "assistant_text": json.loads(msg.assistant_text),
                    "request_at": msg.request_at,
                    "response_at": msg.response_at,
                }
                for msg in messages
            ]
            history_data.append({
                "session_id": convo.session_id,
                "start_time": convo.start_time,
                "last_active": convo.last_active,
                "messages": chat_log
            })

        return Response({
            "client_user_id": client_user.user_id,
            "client_user_name": client_user.name,
            "history": history_data
        }, status=status.HTTP_200_OK)
