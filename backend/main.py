from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.gog_chatbot import PlanningModel
from typing import Optional
from pydantic import BaseModel
import traceback

try:
    from pydantic import model_validator as _model_validator  # type: ignore
    _PV2 = True
except Exception:
    from pydantic import root_validator as _model_validator  # type: ignore
    _PV2 = False

app = FastAPI()

from fastapi.responses import RedirectResponse

@app.get("/", include_in_schema=False)
async def root():
    # Redirect ke halaman dokumentasi
    return RedirectResponse(url="/docs")

origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "https://www.gogkuhp.my.id",
    "https://gogkuhp.my.id"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # gunakan ["*"] hanya untuk development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.post("/chat")
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
        traceback.print_exc()  # Ini akan mencetak detail stack trace ke log Docker
        raise HTTPException(status_code=500, detail=str(e))