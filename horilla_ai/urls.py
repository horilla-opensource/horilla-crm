from django.urls import path
from horilla_ai import views

app_name = "horilla_ai"

urlpatterns = [
    path("ask-ai/", views.AskAIView.as_view(), name="ask_ai"),
    path("api/chat/", views.ChatAPIView.as_view(), name="chat_api"),
    path("api/clear-chat/", views.ClearChatAPIView.as_view(), name="clear_chat_api"),
]
