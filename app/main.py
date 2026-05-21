from fastapi import FastAPI

from .database import Base, engine
from .routers import character, quiz, school_food, user, user_quiz_connect

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Boo키우기 API", version="0.1.0")

app.include_router(user.router)
app.include_router(school_food.router)
app.include_router(quiz.router)
app.include_router(character.router)
app.include_router(user_quiz_connect.router)

@app.get("/")
def root():
    return {"message": "Boo키우기 API is running."}
