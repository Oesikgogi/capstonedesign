from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserBase(BaseModel):
    email: EmailStr
    student_id: str  # 9자리 숫자
    nickname: str
    name: str  # 실명
    image: Optional[str] = None

    @field_validator("student_id", mode="before")
    @classmethod
    def normalize_student_id(cls, value):
        return str(value)


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    student_id: str  # 학번
    password: str
    remember_me: Optional[bool] = False  # 자동 로그인


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    password: Optional[str] = None
    image: Optional[str] = None


class UserOut(UserBase):
    user_id: int
    xp_point: int
    email_verified: bool
    email_verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SignupEmailRequest(BaseModel):
    email: EmailStr


class SignupEmailVerificationRequest(BaseModel):
    email: EmailStr
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, value):
        if not value.isdigit() or len(value) != 6:
            raise ValueError("Code must be 6 digits")
        return value


class SignupEmailVerificationOut(BaseModel):
    detail: str
    verification_code: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenWithRefresh(Token):
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    student_id: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


QuizOptions = Union[List[str], Dict[str, str]]


class QuizBase(BaseModel):
    question: str
    answer: str
    options: Optional[QuizOptions] = None
    quiz_point: Optional[int] = 10


class QuizCreate(QuizBase):
    pass


class QuizUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    options: Optional[QuizOptions] = None
    quiz_point: Optional[int] = None


class Quiz(QuizBase):
    quiz_id: int

    model_config = ConfigDict(from_attributes=True)


class QuizQuestion(BaseModel):
    quiz_id: int
    question: str
    options: Optional[QuizOptions] = None
    quiz_point: int

    model_config = ConfigDict(from_attributes=True)


class QuizSubmit(BaseModel):
    quiz_id: int
    answer: str


class QuizSubmitResult(BaseModel):
    detail: str
    correct: bool
    awarded_points: int
    xp_point: int
    correct_answer: str


class QuizPlayStatus(BaseModel):
    date: str
    solved_today: int
    daily_limit: int
    remaining_today: int
    cooldown_hours: int
    last_played_at: Optional[datetime] = None
    next_available_at: Optional[datetime] = None
    can_play_now: bool


class UserQuizConnectBase(BaseModel):
    user_id: int
    quiz_id: int
    correct_boolean: Optional[bool] = False
    user_quiz_time: Optional[datetime] = None


class UserQuizConnectCreate(UserQuizConnectBase):
    pass


class UserQuizConnect(UserQuizConnectBase):
    user_quiz_id: int

    model_config = ConfigDict(from_attributes=True)


class CharacterBase(BaseModel):
    character_name: str
    stage: Optional[int] = 1
    user_id: int


class CharacterCreate(CharacterBase):
    pass


class CharacterUpdate(BaseModel):
    character_name: Optional[str] = None
    stage: Optional[int] = None


class Character(CharacterBase):
    character_id: int

    model_config = ConfigDict(from_attributes=True)


class SchoolFoodBase(BaseModel):
    name: str
    school_food_img: Optional[str] = None
    school_food_time: Optional[datetime] = None
    type: Optional[str] = None


class SchoolFoodCreate(SchoolFoodBase):
    pass


class SchoolFoodUpdate(BaseModel):
    name: Optional[str] = None
    school_food_img: Optional[str] = None
    school_food_time: Optional[datetime] = None
    type: Optional[str] = None


class SchoolFood(SchoolFoodBase):
    school_food_id: int

    model_config = ConfigDict(from_attributes=True)


class SchoolFoodFeedRequest(BaseModel):
    school_food_id: int


class SchoolFoodFeedResult(BaseModel):
    detail: str
    feed_id: int
    school_food_id: int
    meal_slot: str
    awarded_xp: int
    xp_point: int
    fed_at: datetime


class SchoolFoodFeedStatus(BaseModel):
    date: str
    current_slot: Optional[str] = None
    fed_slots: list[str]
    can_feed_now: bool
