from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .database import Base, engine, ensure_runtime_schema
from .routers import achievement, app_bootstrap, character, debug, economy, friend, graduation, minigame, quiz, room, school_food, shop, user, user_quiz_connect
from .seed_room_items import seed_room_items
from .seed_school_foods import seed_school_foods
from .seed_quizzes import seed_quizzes

Base.metadata.create_all(bind=engine)
ensure_runtime_schema()
seed_school_foods()
seed_room_items()
seed_quizzes()

app = FastAPI(title="Boo키우기 API", version="0.1.0")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and {"code", "message", "meta"}.issubset(detail.keys()):
        content = detail
    else:
        content = {
            "code": "HTTP_ERROR",
            "message": str(detail),
            "meta": {},
        }
    return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "요청 값이 올바르지 않습니다.",
            "meta": {"errors": jsonable_encoder(exc.errors())},
        },
    )

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
app.include_router(achievement.router)
app.include_router(graduation.router)
app.include_router(debug.router)

@app.get("/")
def root():
    return {"message": "Boo키우기 API is running."}
