from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from routes.chat import router as chat_router

app = FastAPI()

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "https://www.gogkuhp.my.id",
    "https://gogkuhp.my.id",
    "https://colab.research.google.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)