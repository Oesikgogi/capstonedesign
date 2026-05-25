from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
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
    created_at = Column(DateTime, default=datetime.utcnow)
    xp_point = Column(Integer, default=0)
    coin = Column(Integer, default=0)
    heart = Column(Integer, default=5)
    heart_updated_at = Column(DateTime, default=datetime.utcnow)
    image = Column(String, nullable=True)

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
    game_type = Column(String, nullable=True)
    location = Column(String, nullable=True)
    score = Column(Integer, nullable=False, default=0)
    success = Column(Boolean, default=False)
    play_time_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="minigame_results")


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
