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
    student_id: Optional[str] = None
    nickname: Optional[str] = None
    password: Optional[str] = None
    image: Optional[str] = None

    @field_validator("student_id", mode="before")
    @classmethod
    def normalize_student_id(cls, value):
        if value is None:
            return value
        return str(value)


class UserOut(UserBase):
    user_id: int
    xp_point: int
    coin: int
    heart: int
    heart_updated_at: Optional[datetime] = None
    email_verified: bool
    email_verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserAccountUpdate(UserUpdate):
    pass


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
    awarded_coin: int
    xp_point: int
    coin: int
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
    spent_coin: int
    xp_point: int
    coin: int
    fed_at: datetime


class SchoolFoodFeedStatus(BaseModel):
    date: str
    current_slot: Optional[str] = None
    fed_slots: list[str]
    can_feed_now: bool


class FriendUser(BaseModel):
    user_id: int
    student_id: str
    nickname: str
    image: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FriendCreate(BaseModel):
    student_id: str

    @field_validator("student_id", mode="before")
    @classmethod
    def normalize_student_id(cls, value):
        return str(value)


class FriendOut(BaseModel):
    friend_id: int
    created_at: datetime
    friend: FriendUser

    model_config = ConfigDict(from_attributes=True)


class EconomyStatus(BaseModel):
    coin: int
    heart: int
    max_heart: int


class MiniGamePlayResult(BaseModel):
    detail: str
    awarded_coin: int
    spent_heart: int
    coin: int
    heart: int
    max_heart: int


class MiniGameResultCreate(BaseModel):
    score: int
    success: Optional[bool] = False
    game_type: Optional[str] = None
    location: Optional[str] = None
    play_time_seconds: Optional[int] = None

    @field_validator("score")
    @classmethod
    def validate_score(cls, value):
        if value < 0:
            raise ValueError("Score must be 0 or greater")
        return value

    @field_validator("play_time_seconds")
    @classmethod
    def validate_play_time_seconds(cls, value):
        if value is not None and value < 0:
            raise ValueError("Play time must be 0 or greater")
        return value


class MiniGameResultOut(BaseModel):
    result_id: int
    user_id: int
    game_type: Optional[str] = None
    location: Optional[str] = None
    score: int
    success: bool
    play_time_seconds: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MiniGameRankingMe(BaseModel):
    rank: Optional[int] = None
    best_score: Optional[int] = None
    total_ranked_users: int
    total_users: int


class RoomItemBase(BaseModel):
    name: str
    item_type: str
    image: Optional[str] = None
    price: int = 0
    is_default: Optional[bool] = False

    @field_validator("price")
    @classmethod
    def validate_price(cls, value):
        if value < 0:
            raise ValueError("Price must be 0 or greater")
        return value

    @field_validator("item_type")
    @classmethod
    def validate_item_type(cls, value):
        item_type_aliases = {
            "desk": "desk",
            "책상": "desk",
            "bed": "bed",
            "침대": "bed",
            "closet": "closet",
            "장롱": "closet",
            "room": "room",
            "마이룸방": "room",
        }
        normalized = item_type_aliases.get(value.strip())
        if not normalized:
            raise ValueError("Item type must be one of desk, bed, closet, room")
        return normalized


class RoomItemCreate(RoomItemBase):
    pass


class RoomItemOut(RoomItemBase):
    item_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShopItemOut(RoomItemOut):
    owned: bool
    equipped: bool


class ShopItemTypeOut(BaseModel):
    item_type: str
    label: str


class RoomItemPurchaseResult(BaseModel):
    detail: str
    item: RoomItemOut
    coin: int


class RoomEquipRequest(BaseModel):
    item_id: int


class RoomEquippedItemOut(BaseModel):
    equipped_id: int
    item_type: str
    equipped_at: datetime
    item: RoomItemOut

    model_config = ConfigDict(from_attributes=True)


class RoomView(BaseModel):
    owner: FriendUser
    equipped_items: list[RoomEquippedItemOut]


class GuestbookCreate(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Content is required")
        if len(value) > 15:
            raise ValueError("Content must be 15 characters or fewer")
        return value


class GuestbookOut(BaseModel):
    entry_id: int
    room_owner_id: int
    writer_id: int
    writer_nickname: str
    content: str
    created_at: datetime
