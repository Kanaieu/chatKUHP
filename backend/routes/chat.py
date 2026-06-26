from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.gog_chatbot import PlanningModel
import traceback

try:
    from pydantic import model_validator as _model_validator  # type: ignore
    _PV2 = True
except Exception:
    from pydantic import root_validator as _model_validator  # type: ignore
    _PV2 = False

router = APIRouter()

class UserQuery(BaseModel):
    query: Optional[str] = None
    message: Optional[str] = None

    if _PV2:
        @classmethod
        @_model_validator(mode="before")
        def ensure_query_exists(cls, values):
            q = values.get("query") or values.get("message")
            if not q:
                raise ValueError('Either "query" or "message" must be provided')
            values["query"] = q
            return values
    else:
        @classmethod
        @_model_validator
        def ensure_query_exists(cls, values):
            q = values.get("query") or values.get("message")
            if not q:
                raise ValueError('Either "query" or "message" must be provided')
            values["query"] = q
            return values

@router.post("/chat")
async def chat_endpoint(user_query: UserQuery):
    print(f"\n[API] Menerima request chat...", flush=True)
    print(f"[API] Query: {user_query.query}", flush=True)
    try:
        print(f"[API] Inisialisasi chatbot...", flush=True)
        chatbot = PlanningModel()

        print(f"[API] Menjalankan proses planning...", flush=True)
        response = chatbot.planning(task=user_query.query)

        print(f"[API] Response berhasil dibuat.", flush=True)
        return {"response": response}
    except Exception as e:
        print(f"\n[API] ERROR TERJADI: {str(e)}", flush=True)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/getcontext")
async def getcontext_endpoint(user_query: UserQuery):
    print(f"\n[API] Menerima request context...", flush=True)
    print(f"[API] Pertanyaan: {user_query.query}", flush=True)
    try:
        chatbot = PlanningModel()
        response_data = chatbot.getcontext(task=user_query.query)
        return response_data
    except Exception as e:
        print(f"\n[API] ERROR TERJADI: {str(e)}", flush=True)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))