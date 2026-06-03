from fastapi import FastAPI

from .database import Base, engine, ensure_runtime_schema
from .routers import app_bootstrap, character, economy, friend, minigame, quiz, room, school_food, shop, user, user_quiz_connect

Base.metadata.create_all(bind=engine)
ensure_runtime_schema()

app = FastAPI(title="Boo키우기 API", version="0.1.0")

app.include_router(user.router)
app.include_router(school_food.router)
app.include_router(quiz.router)
app.include_router(character.router)
app.include_router(friend.router)
app.include_router(economy.router)
app.include_router(minigame.router)
app.include_router(shop.router)
app.include_router(room.router)
app.include_router(user_quiz_connect.router)
app.include_router(app_bootstrap.router)

@app.get("/")
def root():
    return {"message": "Boo키우기 API is running."}
