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

    USERS ||--o{ REFRESH_TOKENS : "has"
    USERS ||--o{ PASSWORD_RESET_TOKENS : "requests"
    USERS ||--o{ USER_QUIZ_CONNECT : "solves"
    QUIZZES ||--o{ USER_QUIZ_CONNECT : "is solved in"
    USERS ||--o{ SCHOOL_FOOD_FEEDS : "feeds"
    SCHOOL_FOODS ||--o{ SCHOOL_FOOD_FEEDS : "is fed"
    USERS ||--o{ CHARACTERS : "owns"

    SIGNUP_EMAIL_VERIFICATIONS }o..o| USERS : "email verified before signup"
```

## Relationship Summary

- `users` 1:N `refresh_tokens`
- `users` 1:N `password_reset_tokens`
- `users` N:M `quizzes` through `user_quiz_connect`
- `users` N:M `school_foods` through `school_food_feeds`
- `users` 1:N `characters`
- `signup_email_verifications` is logically connected to `users.email`, but it has no FK because it is used before user creation.

