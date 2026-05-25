# Boo키우기 ERD

```mermaid
erDiagram
    USERS {
        int user_id PK
        string email UK
        string student_id UK
        string name
        string nickname UK
        string password
        boolean email_verified
        datetime email_verified_at
        datetime created_at
        int xp_point
        int coin
        int heart
        datetime heart_updated_at
        string image
    }

    SIGNUP_EMAIL_VERIFICATIONS {
        int verification_id PK
        string email
        string code
        datetime expires_at
        boolean verified
        datetime created_at
    }

    REFRESH_TOKENS {
        int refresh_token_id PK
        string token UK
        int user_id FK
        datetime expires_at
        boolean revoked
        datetime created_at
    }

    PASSWORD_RESET_TOKENS {
        int token_id PK
        string token UK
        int user_id FK
        datetime expires_at
        boolean used
        datetime created_at
    }

    QUIZZES {
        int quiz_id PK
        string question
        string answer
        json options
        int quiz_point
    }

    USER_QUIZ_CONNECT {
        int user_quiz_id PK
        int user_id FK
        int quiz_id FK
        boolean correct_boolean
        datetime user_quiz_time
    }

    SCHOOL_FOODS {
        int school_food_id PK
        string name
        string school_food_img
        datetime school_food_time
        string type
    }

    SCHOOL_FOOD_FEEDS {
        int feed_id PK
        int user_id FK
        int school_food_id FK
        string meal_slot
        date feed_date
        datetime fed_at
        int awarded_xp
    }

    CHARACTERS {
        int character_id PK
        string character_name
        int stage
        int user_id FK
    }

    FRIENDS {
        int friend_id PK
        int user_id FK
        int friend_user_id FK
        datetime created_at
    }

    MINIGAME_RESULTS {
        int result_id PK
        int user_id FK
        string game_type
        string location
        int score
        boolean success
        int play_time_seconds
        datetime created_at
    }

    ROOM_ITEMS {
        int item_id PK
        string name
        string item_type
        string image
        int price
        boolean is_default
        datetime created_at
    }

    USER_ROOM_ITEMS {
        int owned_item_id PK
        int user_id FK
        int item_id FK
        datetime purchased_at
    }

    USER_ROOM_EQUIPPED {
        int equipped_id PK
        int user_id FK
        string item_type
        int item_id FK
        datetime equipped_at
    }

    GUESTBOOK_ENTRIES {
        int entry_id PK
        int room_owner_id FK
        int writer_id FK
        string content
        datetime created_at
    }

    USERS ||--o{ REFRESH_TOKENS : "has"
    USERS ||--o{ PASSWORD_RESET_TOKENS : "requests"

    USERS ||--o{ USER_QUIZ_CONNECT : "solves"
    QUIZZES ||--o{ USER_QUIZ_CONNECT : "is solved in"

    USERS ||--o{ SCHOOL_FOOD_FEEDS : "feeds"
    SCHOOL_FOODS ||--o{ SCHOOL_FOOD_FEEDS : "is fed"

    USERS ||--o{ CHARACTERS : "owns"

    USERS ||--o{ FRIENDS : "adds"
    USERS ||--o{ FRIENDS : "is added as friend"

    USERS ||--o{ MINIGAME_RESULTS : "plays"

    USERS ||--o{ USER_ROOM_ITEMS : "owns"
    ROOM_ITEMS ||--o{ USER_ROOM_ITEMS : "is owned"

    USERS ||--o{ USER_ROOM_EQUIPPED : "equips"
    ROOM_ITEMS ||--o{ USER_ROOM_EQUIPPED : "is equipped"

    USERS ||--o{ GUESTBOOK_ENTRIES : "owns room"
    USERS ||--o{ GUESTBOOK_ENTRIES : "writes"

    SIGNUP_EMAIL_VERIFICATIONS }o..o| USERS : "email verified before signup"
```

## Relationship Summary

- `users` 1:N `refresh_tokens`
- `users` 1:N `password_reset_tokens`
- `users` N:M `quizzes` through `user_quiz_connect`
- `users` N:M `school_foods` through `school_food_feeds`
- `users` 1:N `characters`
- `users` N:M `users` through `friends`
- `users` 1:N `minigame_results`
- `users` N:M `room_items` through `user_room_items`
- `users` N:M `room_items` through `user_room_equipped`
- `users` 1:N `guestbook_entries` as room owner
- `users` 1:N `guestbook_entries` as writer
- `signup_email_verifications` is logically connected to `users.email`, but it has no FK because it is used before user creation.

## Constraints

- `users.email` is unique.
- `users.student_id` is unique.
- `users.nickname` is unique.
- `refresh_tokens.token` is unique.
- `password_reset_tokens.token` is unique.
- `user_quiz_connect` has unique `(user_id, quiz_id)`.
- `school_food_feeds` has unique `(user_id, feed_date, meal_slot)`.
- `friends` has unique `(user_id, friend_user_id)`.
- `user_room_items` has unique `(user_id, item_id)`.
- `user_room_equipped` has unique `(user_id, item_type)`.
