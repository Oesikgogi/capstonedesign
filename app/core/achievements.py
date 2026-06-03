from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models


@dataclass(frozen=True)
class AchievementDefinition:
    achievement_key: str
    title: str
    condition_type: str
    target_value: int
    reward_type: str
    reward_value: Optional[int] = None
    reward_item_key: Optional[str] = None
    sort_order: int = 0


ACHIEVEMENTS: list[AchievementDefinition] = [
    AchievementDefinition("first_login", "첫 로그인", "first_login", 1, "coin", 50, sort_order=1),
    AchievementDefinition("feed_1", "학식 1회 먹이기", "feed_count", 1, "xp", 10, sort_order=2),
    AchievementDefinition("quiz_correct_1", "퀴즈 1회 정답", "quiz_correct_count", 1, "coin", 100, sort_order=3),
    AchievementDefinition("room_first_enter", "마이룸 첫 진입", "room_first_enter", 1, "xp", 10, sort_order=4),
    AchievementDefinition("campus_first_visit", "캠퍼스 첫 방문", "campus_first_visit", 1, "coin", 150, sort_order=5),
    AchievementDefinition("friend_1", "친구 1명 만들기", "friend_count", 1, "coin", 100, sort_order=6),
    AchievementDefinition("quiz_correct_5", "퀴즈 누적 5회 정답", "quiz_correct_count", 5, "coin", 200, sort_order=7),
    AchievementDefinition("feed_5", "학식 누적 5회 먹이기", "feed_count", 5, "coin", 200, sort_order=8),
    AchievementDefinition("achievement_10", "업적 10개 달성", "achievement_completed_count", 10, "coin", 300, sort_order=9),
    AchievementDefinition("quiz_correct_15", "퀴즈 누적 15회 정답", "quiz_correct_count", 15, "skin", None, "skin_truth", 10),
    AchievementDefinition("feed_15", "학식 누적 15회 먹이기", "feed_count", 15, "coin", 500, sort_order=11),
    AchievementDefinition("friend_5", "친구 5명 만들기", "friend_count", 5, "coin", 300, sort_order=12),
    AchievementDefinition("minigame_10", "미니게임 누적 10회", "minigame_play_count", 10, "coin", 300, sort_order=13),
    AchievementDefinition("total_xp_1500", "누적 1,500XP 달성", "total_xp", 1500, "coin", 400, sort_order=14),
    AchievementDefinition("room_item_equip_5", "방 아이템 5회 장착", "room_item_equip_count", 5, "coin", 300, sort_order=15),
    AchievementDefinition("quiz_correct_30", "퀴즈 누적 30회 정답", "quiz_correct_count", 30, "coin", 600, sort_order=16),
    AchievementDefinition("feed_30", "학식 누적 30회 먹이기", "feed_count", 30, "coin", 700, sort_order=17),
    AchievementDefinition("friend_15", "친구 15명 만들기", "friend_count", 15, "coin", 700, sort_order=18),
    AchievementDefinition("achievement_20", "업적 20개 달성", "achievement_completed_count", 20, "skin", None, "skin_creation", 19),
    AchievementDefinition("total_xp_2500_skin", "누적 2,500XP 달성 외형", "total_xp", 2500, "skin", None, "skin_peace", 20),
    AchievementDefinition("quiz_correct_50_coin_800", "퀴즈 누적 50회 정답", "quiz_correct_count", 50, "coin", 800, sort_order=21),
    AchievementDefinition("feed_50_coin_1000", "학식 누적 50회 먹이기", "feed_count", 50, "coin", 1000, sort_order=22),
    AchievementDefinition("minigame_50_coin_1000", "미니게임 누적 50회", "minigame_play_count", 50, "coin", 1000, sort_order=23),
    AchievementDefinition("total_xp_2500_xp_50", "누적 2,500XP 달성 보너스", "total_xp", 2500, "xp", 50, sort_order=24),
    AchievementDefinition("quiz_correct_50_coin_1500", "퀴즈 누적 50회 정답 추가 보상", "quiz_correct_count", 50, "coin", 1500, sort_order=25),
    AchievementDefinition("feed_50_coin_2000", "학식 누적 50회 먹이기 추가 보상", "feed_count", 50, "coin", 2000, sort_order=26),
    AchievementDefinition("minigame_50_coin_2000", "미니게임 누적 50회 추가 보상", "minigame_play_count", 50, "coin", 2000, sort_order=27),
    AchievementDefinition("quiz_correct_80", "퀴즈 누적 80회 정답", "quiz_correct_count", 80, "coin", 2500, sort_order=28),
    AchievementDefinition("feed_80", "학식 누적 80회 먹이기", "feed_count", 80, "coin", 2500, sort_order=29),
    AchievementDefinition("minigame_80", "미니게임 누적 80회", "minigame_play_count", 80, "coin", 2500, sort_order=30),
]

ACHIEVEMENT_BY_KEY = {achievement.achievement_key: achievement for achievement in ACHIEVEMENTS}


def serialize_achievement_definition(achievement: AchievementDefinition) -> dict:
    return {
        "achievement_key": achievement.achievement_key,
        "title": achievement.title,
        "condition_type": achievement.condition_type,
        "target_value": achievement.target_value,
        "reward_type": achievement.reward_type,
        "reward_value": achievement.reward_value,
        "reward_item_key": achievement.reward_item_key,
        "sort_order": achievement.sort_order,
    }


def serialize_unlocked_achievement(achievement: AchievementDefinition) -> dict:
    return {
        "achievement_key": achievement.achievement_key,
        "title": achievement.title,
        "reward_type": achievement.reward_type,
        "reward_value": achievement.reward_value,
        "reward_item_key": achievement.reward_item_key,
    }


def get_or_create_counter(db: Session, user_id: int) -> models.UserAchievementCounter:
    counter = (
        db.query(models.UserAchievementCounter)
        .filter(models.UserAchievementCounter.user_id == user_id)
        .first()
    )
    if counter:
        return counter

    counter = models.UserAchievementCounter(user_id=user_id)
    db.add(counter)
    db.flush()
    return counter


def sync_counter_from_records(db: Session, user: models.User, counter: models.UserAchievementCounter) -> None:
    counter.feed_count = max(
        counter.feed_count or 0,
        db.query(models.SchoolFoodFeed).filter(models.SchoolFoodFeed.user_id == user.user_id).count(),
    )
    counter.quiz_correct_count = max(
        counter.quiz_correct_count or 0,
        db.query(models.UserQuizConnect)
        .filter(
            models.UserQuizConnect.user_id == user.user_id,
            models.UserQuizConnect.correct_boolean == True,
        )
        .count(),
    )
    counter.friend_count = max(
        counter.friend_count or 0,
        db.query(models.Friend).filter(models.Friend.user_id == user.user_id).count(),
    )
    counter.minigame_play_count = max(
        counter.minigame_play_count or 0,
        db.query(models.MiniGameResult).filter(models.MiniGameResult.user_id == user.user_id).count(),
    )
    counter.achievement_completed_count = db.query(models.UserAchievement).filter(
        models.UserAchievement.user_id == user.user_id,
        models.UserAchievement.completed == True,
    ).count()
    counter.total_xp = max(counter.total_xp or 0, user.xp_point or 0, 0)
    counter.updated_at = datetime.utcnow()


def get_progress_value(achievement: AchievementDefinition, counter: models.UserAchievementCounter) -> int:
    if achievement.condition_type == "first_login":
        return 1 if counter.has_first_login else 0
    if achievement.condition_type == "room_first_enter":
        return 1 if counter.has_entered_room else 0
    if achievement.condition_type == "campus_first_visit":
        return 1 if counter.has_visited_campus else 0
    return getattr(counter, achievement.condition_type, 0) or 0


def grant_achievement_reward(db: Session, user: models.User, achievement: AchievementDefinition) -> None:
    if achievement.reward_type == "coin":
        user.coin = (user.coin or 0) + (achievement.reward_value or 0)
    elif achievement.reward_type == "xp":
        user.xp_point = max((user.xp_point or 0) + (achievement.reward_value or 0), 0)
    elif achievement.reward_type == "skin" and achievement.reward_item_key:
        existing_skin = (
            db.query(models.UserSkin)
            .filter(
                models.UserSkin.user_id == user.user_id,
                models.UserSkin.skin_key == achievement.reward_item_key,
            )
            .first()
        )
        if not existing_skin:
            db.add(
                models.UserSkin(
                    user_id=user.user_id,
                    skin_key=achievement.reward_item_key,
                    owned=True,
                    acquired_from=f"achievement_{achievement.achievement_key}",
                )
            )


def complete_achievement(
    db: Session,
    user: models.User,
    achievement: AchievementDefinition,
) -> dict | None:
    if (
        db.query(models.UserAchievement)
        .filter(
            models.UserAchievement.user_id == user.user_id,
            models.UserAchievement.achievement_key == achievement.achievement_key,
        )
        .first()
    ):
        return None

    user_achievement = models.UserAchievement(
        user_id=user.user_id,
        achievement_key=achievement.achievement_key,
        completed=True,
        claimed=True,
        completed_at=datetime.utcnow(),
    )
    db.add(user_achievement)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return None

    grant_achievement_reward(db, user, achievement)
    return serialize_unlocked_achievement(achievement)


def evaluate_achievements(db: Session, user: models.User) -> list[dict]:
    counter = get_or_create_counter(db, user.user_id)
    unlocked: list[dict] = []

    for _ in range(5):
        sync_counter_from_records(db, user, counter)
        newly_unlocked: list[dict] = []
        for achievement in ACHIEVEMENTS:
            progress_value = get_progress_value(achievement, counter)
            if progress_value < achievement.target_value:
                continue
            unlocked_achievement = complete_achievement(db, user, achievement)
            if unlocked_achievement:
                newly_unlocked.append(unlocked_achievement)

        if not newly_unlocked:
            break
        unlocked.extend(newly_unlocked)

    sync_counter_from_records(db, user, counter)
    return unlocked


def apply_achievement_event(
    db: Session,
    user: models.User,
    event_type: str,
    increment: int = 1,
) -> list[dict]:
    counter = get_or_create_counter(db, user.user_id)

    if event_type == "first_login":
        counter.has_first_login = True
    elif event_type == "feed":
        counter.feed_count = (counter.feed_count or 0) + increment
    elif event_type == "quiz_correct":
        counter.quiz_correct_count = (counter.quiz_correct_count or 0) + increment
    elif event_type == "friend":
        counter.friend_count = max(counter.friend_count or 0, db.query(models.Friend).filter(models.Friend.user_id == user.user_id).count())
    elif event_type == "minigame_play":
        counter.minigame_play_count = (counter.minigame_play_count or 0) + increment
    elif event_type == "room_item_equip":
        counter.room_item_equip_count = (counter.room_item_equip_count or 0) + increment
    elif event_type == "room_enter":
        counter.has_entered_room = True
    elif event_type == "campus_visit":
        counter.has_visited_campus = True

    counter.total_xp = max(counter.total_xp or 0, user.xp_point or 0, 0)
    counter.updated_at = datetime.utcnow()
    return evaluate_achievements(db, user)


def get_user_achievement_progress(db: Session, user: models.User) -> list[dict]:
    counter = get_or_create_counter(db, user.user_id)
    sync_counter_from_records(db, user, counter)
    completed_records = {
        record.achievement_key: record
        for record in db.query(models.UserAchievement)
        .filter(models.UserAchievement.user_id == user.user_id)
        .all()
    }
    return [
        {
            **serialize_achievement_definition(achievement),
            "progress_value": min(get_progress_value(achievement, counter), achievement.target_value),
            "completed": achievement.achievement_key in completed_records,
            "completed_at": completed_records[achievement.achievement_key].completed_at
            if achievement.achievement_key in completed_records
            else None,
            "claimed": completed_records[achievement.achievement_key].claimed
            if achievement.achievement_key in completed_records
            else False,
        }
        for achievement in ACHIEVEMENTS
    ]
