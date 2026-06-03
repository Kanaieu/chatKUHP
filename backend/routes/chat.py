from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.gog_chatbot import PlanningModel

router = APIRouter()

class UserQuery(BaseModel):
    query: str

@router.post("/chat")
async def chat_endpoint(user_query: UserQuery):
    chatbot = PlanningModel()
    try:
        response_data = chatbot.planning(task=user_query.query)
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))