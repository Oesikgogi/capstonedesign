import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    student_id = Column(String, unique=True, nullable=False)  # 학번 (9자리 숫자)
    name = Column(String, nullable=False)  # 실명
    nickname = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    xp_point = Column(Integer, default=0)
    coin = Column(Integer, default=0)
    heart = Column(Integer, default=5)
    heart_updated_at = Column(DateTime, default=datetime.utcnow)
    image = Column(String, nullable=True)
    graduated_at = Column(DateTime, nullable=True)

    quizzes = relationship("UserQuizConnect", back_populates="user")
    characters = relationship("Character", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    friends = relationship(
        "Friend",
        foreign_keys="Friend.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    minigame_results = relationship("MiniGameResult", back_populates="user", cascade="all, delete-orphan")
    owned_room_items = relationship("UserRoomItem", back_populates="user", cascade="all, delete-orphan")
    equipped_room_items = relationship("UserRoomEquipped", back_populates="user", cascade="all, delete-orphan")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    preference_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    has_seen_game_tutorial = Column(Boolean, default=False)
    has_seen_minigame_tutorial = Column(Boolean, default=False)
    bgm_volume = Column(Float, nullable=True)
    sfx_volume = Column(Float, nullable=True)
    master_volume = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class FriendRequest(Base):
    __tablename__ = "friend_requests"
    __table_args__ = (UniqueConstraint("requester_id", "receiver_id", name="uq_friend_request_once"),)

    request_id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)

    requester = relationship("User", foreign_keys=[requester_id])
    receiver = relationship("User", foreign_keys=[receiver_id])


class UserAchievementCounter(Base):
    __tablename__ = "user_achievement_counters"

    counter_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    feed_count = Column(Integer, default=0)
    quiz_correct_count = Column(Integer, default=0)
    friend_count = Column(Integer, default=0)
    minigame_play_count = Column(Integer, default=0)
    room_item_equip_count = Column(Integer, default=0)
    achievement_completed_count = Column(Integer, default=0)
    total_xp = Column(Integer, default=0)
    has_entered_room = Column(Boolean, default=False)
    has_visited_campus = Column(Boolean, default=False)
    has_first_login = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_key", name="uq_user_achievement_once"),)

    user_achievement_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    achievement_key = Column(String, nullable=False)
    completed = Column(Boolean, default=True)
    completed_at = Column(DateTime, default=datetime.utcnow)
    claimed = Column(Boolean, default=True)

    user = relationship("User")


class UserSkin(Base):
    __tablename__ = "user_skins"
    __table_args__ = (UniqueConstraint("user_id", "skin_key", name="uq_user_skin_once"),)

    user_skin_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    skin_key = Column(String, nullable=False)
    owned = Column(Boolean, default=True)
    acquired_from = Column(String, nullable=True)
    acquired_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class Quiz(Base):
    __tablename__ = "quizzes"

    quiz_id = Column(Integer, primary_key=True, index=True)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    options = Column(JSON, nullable=True)
    quiz_point = Column(Integer, default=10)

    users = relationship("UserQuizConnect", back_populates="quiz")


class UserQuizConnect(Base):
    __tablename__ = "user_quiz_connect"
    __table_args__ = (UniqueConstraint("user_id", "quiz_id", name="uq_user_quiz_once"),)

    user_quiz_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.quiz_id"), nullable=False)
    correct_boolean = Column(Boolean, default=False)
    user_quiz_time = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="quizzes")
    quiz = relationship("Quiz", back_populates="users")


class Character(Base):
    __tablename__ = "characters"

    character_id = Column(Integer, primary_key=True, index=True)
    character_name = Column(String, nullable=False)
    stage = Column(Integer, default=1)
    state = Column(String, default="basic1")
    equipped_skin_key = Column(String, default="default")
    pending_evolution = Column(Boolean, default=False)
    skipped_meal_count = Column(Integer, default=0)
    hungry_state = Column(Boolean, default=False)
    meal_health_date = Column(Date, nullable=True)
    last_checked_meal_slot = Column(String, nullable=True)
    applied_penalty_count = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    user = relationship("User", back_populates="characters")


class SchoolFood(Base):
    __tablename__ = "school_foods"

    school_food_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    school_food_img = Column(String, nullable=True)
    school_food_time = Column(DateTime, nullable=True)
    type = Column(String, nullable=True)


class SchoolFoodFeed(Base):
    __tablename__ = "school_food_feeds"
    __table_args__ = (UniqueConstraint("user_id", "feed_date", "meal_slot", name="uq_user_meal_slot_once"),)

    feed_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    school_food_id = Column(Integer, ForeignKey("school_foods.school_food_id"), nullable=False)
    meal_slot = Column(String, nullable=False)
    feed_date = Column(Date, nullable=False)
    fed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    awarded_xp = Column(Integer, default=50)

    user = relationship("User")
    school_food = relationship("SchoolFood")


class Friend(Base):
    __tablename__ = "friends"
    __table_args__ = (UniqueConstraint("user_id", "friend_user_id", name="uq_user_friend_once"),)

    friend_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    friend_user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id], back_populates="friends")
    friend_user = relationship("User", foreign_keys=[friend_user_id])


class MiniGameResult(Base):
    __tablename__ = "minigame_results"

    result_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    play_session_id = Column(String, nullable=True, index=True)
    game_type = Column(String, nullable=True)
    mode = Column(String, nullable=True)
    location = Column(String, nullable=True)
    score = Column(Integer, nullable=False, default=0)
    success = Column(Boolean, default=False)
    ended_reason = Column(String, nullable=True)
    play_time_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="minigame_results")


class MiniGamePlaySession(Base):
    __tablename__ = "minigame_play_sessions"

    play_session_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    game_type = Column(String, nullable=False)
    mode = Column(String, nullable=False, default="normal")
    spent_heart = Column(Integer, nullable=False, default=1)
    rewarded = Column(Boolean, default=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    rewarded_at = Column(DateTime, nullable=True)

    user = relationship("User")


class RoomItem(Base):
    __tablename__ = "room_items"

    item_id = Column(Integer, primary_key=True, index=True)
    item_key = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=False)
    item_type = Column(String, nullable=False)
    image = Column(String, nullable=True)
    price = Column(Integer, nullable=False, default=0)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owners = relationship("UserRoomItem", back_populates="item")
    equipped_by = relationship("UserRoomEquipped", back_populates="item")


class UserRoomItem(Base):
    __tablename__ = "user_room_items"
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uq_user_room_item_once"),)

    owned_item_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("room_items.item_id", ondelete="CASCADE"), nullable=False)
    purchased_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="owned_room_items")
    item = relationship("RoomItem", back_populates="owners")


class UserRoomEquipped(Base):
    __tablename__ = "user_room_equipped"
    __table_args__ = (UniqueConstraint("user_id", "item_type", name="uq_user_room_equipped_type"),)

    equipped_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    item_type = Column(String, nullable=False)
    item_id = Column(Integer, ForeignKey("room_items.item_id", ondelete="CASCADE"), nullable=False)
    equipped_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="equipped_room_items")
    item = relationship("RoomItem", back_populates="equipped_by")


class GuestbookEntry(Base):
    __tablename__ = "guestbook_entries"

    entry_id = Column(Integer, primary_key=True, index=True)
    room_owner_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    writer_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    room_owner = relationship("User", foreign_keys=[room_owner_id])
    writer = relationship("User", foreign_keys=[writer_id])


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    refresh_token_id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="refresh_tokens")


class SignupEmailVerification(Base):
    __tablename__ = "signup_email_verifications"

    verification_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    token_id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
