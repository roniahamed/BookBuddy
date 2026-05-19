#!/usr/bin/env python
import os
import sys
from datetime import datetime, timedelta, timezone

# Add the parent directory to python path so we can import the `app` package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from sqlalchemy.orm import Session
    from sqlalchemy import text
    from app.core.database import SessionLocal, engine
    
    # Import ALL models
    from app.modules.users.model import User, UserSettings, UserFCMToken
    from app.modules.auth.model import PasswordResetToken
    from app.modules.books.model import Book, Genre, Wishlist, Review
    from app.modules.borrowing.model import BorrowRequest
    from app.modules.chat.model import Conversation, Message
    from app.modules.admin.model import AppConfig
    
    from app.core.security import get_password_hash
    from app.core.encryption import encrypt
    from app.modules.admin.service import AdminConfigService
except ImportError as e:
    print(f"\033[91mError: Could not import app modules. Please make sure you have activated your virtual environment.\033[0m")
    print(f"Details: {e}")
    sys.exit(1)


def flush_and_seed():
    print("\033[94m" + "="*60)
    print("      BookBuddy Database Flusher and Seeder")
    print("="*60 + "\033[0m")

    db: Session = SessionLocal()
    try:
        # 1. FLUSH / CLEAR ALL TABLES
        print("\n\033[93mFlushing database tables...\033[0m")
        tables = [
            "reviews",
            "wishlist",
            "borrow_requests",
            "messages",
            "conversations",
            "user_fcm_tokens",
            "password_reset_tokens",
            "user_settings",
            "books",
            "genres",
            "users",
            "app_config"
        ]

        dialect_name = engine.dialect.name
        if dialect_name == "postgresql":
            print(f"Detected PostgreSQL. Performing CASCADE truncation on {len(tables)} tables...")
            db.execute(text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE;"))
            db.commit()
            print("\033[92mPostgreSQL tables truncated successfully!\033[0m")
        else:
            print(f"Detected SQLite/Other. Disabling foreign keys and deleting from {len(tables)} tables...")
            db.execute(text("PRAGMA foreign_keys = OFF;"))
            for table in tables:
                db.execute(text(f"DELETE FROM {table};"))
                try:
                    db.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}';"))
                except Exception:
                    pass  # Some tables might not have auto-increment sequence registered
            db.execute(text("PRAGMA foreign_keys = ON;"))
            db.commit()
            print("\033[92mSQLite tables deleted successfully!\033[0m")

        # 2. SEED SECTIONS
        print("\n\033[93mSeeding new high-quality mock data...\033[0m")

        # ─── A. AppConfig Seeding ───────────────────────────
        print("- Seeding AppConfigs...")
        config_service = AdminConfigService(db)
        config_service.seed_defaults()

        # ─── B. Genre Seeding ───────────────────────────────
        print("- Seeding Genres...")
        genre_names = [
            "Science", "History", "Self-Help", "Fiction",
            "Children's", "Business", "Drama", "Fantasy",
            "Mystery", "Biography"
        ]
        genres_dict = {}
        for name in genre_names:
            g = Genre(name=name)
            db.add(g)
            db.flush()
            genres_dict[name] = g.id

        # ─── C. User Seeding ────────────────────────────────
        print("- Seeding Users...")
        pwd_hash = get_password_hash("password123")
        admin_pwd_hash = get_password_hash("admin123")

        # 1. Admin
        admin_user = User(
            full_name="System Admin",
            email="admin@bookbuddy.com",
            password_hash=admin_pwd_hash,
            role="admin",
            credits=500,
            location="Ibn Gabirol St 100, Tel Aviv",
            latitude=32.0782,
            longitude=34.7891,
            is_active=True,
            auth_provider="email"
        )
        # 2. John Doe (Lender focus)
        john = User(
            full_name="John Doe",
            email="john.doe@example.com",
            password_hash=pwd_hash,
            role="user",
            credits=50,
            location="Dizengoff St 50, Tel Aviv",
            latitude=32.0853,
            longitude=34.7818,
            is_active=True,
            auth_provider="email",
            avg_rating=5.0
        )
        # 3. Jane Smith (Active Borrower focus)
        jane = User(
            full_name="Jane Smith",
            email="jane.smith@example.com",
            password_hash=pwd_hash,
            role="user",
            credits=120,
            location="Ibn Gabirol St 20, Tel Aviv",
            latitude=32.0783,
            longitude=34.7915,
            is_active=True,
            auth_provider="email",
            avg_rating=4.8
        )
        # 4. Alice Johnson (Slightly further user)
        alice = User(
            full_name="Alice Johnson",
            email="alice.johnson@example.com",
            password_hash=pwd_hash,
            role="user",
            credits=30,
            location="Nordau Blvd 15, Tel Aviv",
            latitude=32.0912,
            longitude=34.7761,
            is_active=True,
            auth_provider="email"
        )
        # 5. Bob Brown
        bob = User(
            full_name="Bob Brown",
            email="bob.brown@example.com",
            password_hash=pwd_hash,
            role="user",
            credits=75,
            location="Rothschild Blvd 30, Tel Aviv",
            latitude=32.0625,
            longitude=34.7725,
            is_active=True,
            auth_provider="email"
        )

        db.add_all([admin_user, john, jane, alice, bob])
        db.flush()

        # ─── D. UserSettings Seeding ────────────────────────
        print("- Seeding User Settings...")
        users = [admin_user, john, jane, alice, bob]
        for u in users:
            settings_obj = UserSettings(
                user_id=u.id,
                language="EN",
                email_notifications=True,
                new_message_alert=True
            )
            db.add(settings_obj)

        # ─── E. UserFCMTokens Seeding ───────────────────────
        print("- Seeding FCM Device Tokens...")
        for u in users:
            token_obj = UserFCMToken(
                user_id=u.id,
                token=f"fcm_token_{u.email.split('@')[0]}_device1"
            )
            db.add(token_obj)

        db.flush()

        # ─── F. Book Seeding ────────────────────────────────
        print("- Seeding Books...")
        
        # Books owned by John Doe (ID: john.id)
        book_hobbit = Book(
            owner_id=john.id,
            genre_id=genres_dict["Fantasy"],
            title="The Hobbit",
            author_name="J.R.R. Tolkien",
            description="The classic fantasy adventure of Bilbo Baggins. Excellent paperback version, ready for borrowing.",
            front_cover_url="https://images-na.ssl-images-amazon.com/images/I/91b0C2YGPFL.jpg",
            condition="Good",
            borrow_duration_days=30,
            location="Dizengoff St 50, Tel Aviv",
            latitude=32.0853,
            longitude=34.7818,
            availability="available",
            avg_rating=0.0
        )
        book_sapiens = Book(
            owner_id=john.id,
            genre_id=genres_dict["History"],
            title="Sapiens: A Brief History of Humankind",
            author_name="Yuval Noah Harari",
            description="Explores the history of humanity from the Stone Age to the Silicon Age. Brand new hardcover.",
            front_cover_url="https://images-na.ssl-images-amazon.com/images/I/713jIoMO3UL.jpg",
            condition="New",
            borrow_duration_days=30,
            location="Dizengoff St 50, Tel Aviv",
            latitude=32.0853,
            longitude=34.7818,
            availability="borrowed",
            avg_rating=5.0
        )
        book_habits = Book(
            owner_id=john.id,
            genre_id=genres_dict["Self-Help"],
            title="Atomic Habits",
            author_name="James Clear",
            description="An easy and proven way to build good habits and break bad ones. Has a few highlights inside.",
            front_cover_url="https://images-na.ssl-images-amazon.com/images/I/91bYSX41hVL.jpg",
            condition="Good",
            borrow_duration_days=30,
            location="Dizengoff St 50, Tel Aviv",
            latitude=32.0853,
            longitude=34.7818,
            availability="available",
            avg_rating=0.0
        )

        # Books owned by Jane Smith (ID: jane.id)
        book_mockingbird = Book(
            owner_id=jane.id,
            genre_id=genres_dict["Fiction"],
            title="To Kill a Mockingbird",
            author_name="Harper Lee",
            description="A novel about warmth, humor, and the roots of behavior in the Deep South. Classic story.",
            front_cover_url="https://images-na.ssl-images-amazon.com/images/I/81gepf1eMqL.jpg",
            condition="Good",
            borrow_duration_days=30,
            location="Ibn Gabirol St 20, Tel Aviv",
            latitude=32.0783,
            longitude=34.7915,
            availability="available",
            avg_rating=4.5
        )
        book_thinking = Book(
            owner_id=jane.id,
            genre_id=genres_dict["Science"],
            title="Thinking, Fast and Slow",
            author_name="Daniel Kahneman",
            description="Fascinating research about two systems of thinking and decision making. Great condition.",
            front_cover_url="https://images-na.ssl-images-amazon.com/images/I/61f1YfujQ3L.jpg",
            condition="Good",
            borrow_duration_days=30,
            location="Ibn Gabirol St 20, Tel Aviv",
            latitude=32.0783,
            longitude=34.7915,
            availability="available",
            avg_rating=0.0
        )
        book_educated = Book(
            owner_id=jane.id,
            genre_id=genres_dict["Biography"],
            title="Educated",
            author_name="Tara Westover",
            description="An unforgettable memoir about a girl who leaves her survivalist family in Idaho to seek an education.",
            front_cover_url="https://images-na.ssl-images-amazon.com/images/I/81WZ5SJD3DL.jpg",
            condition="Used",
            borrow_duration_days=30,
            location="Ibn Gabirol St 20, Tel Aviv",
            latitude=32.0783,
            longitude=34.7915,
            availability="available",
            avg_rating=0.0
        )

        # Books owned by Alice Johnson (ID: alice.id)
        book_dune = Book(
            owner_id=alice.id,
            genre_id=genres_dict["Fantasy"],
            title="Dune",
            author_name="Frank Herbert",
            description="The greatest science fiction masterpiece of all time. Set on the desert planet Arrakis.",
            front_cover_url="https://images-na.ssl-images-amazon.com/images/I/81ym3QUd3KL.jpg",
            condition="New",
            borrow_duration_days=45,
            location="Nordau Blvd 15, Tel Aviv",
            latitude=32.0912,
            longitude=34.7761,
            availability="borrowed",
            avg_rating=0.0
        )
        book_cleancode = Book(
            owner_id=alice.id,
            genre_id=genres_dict["Science"],
            title="Clean Code",
            author_name="Robert C. Martin",
            description="A handbook of agile software craftsmanship. A must-have for every professional coder.",
            front_cover_url="https://images-na.ssl-images-amazon.com/images/I/41-sN-m7vbL.jpg",
            condition="Good",
            borrow_duration_days=30,
            location="Nordau Blvd 15, Tel Aviv",
            latitude=32.0912,
            longitude=34.7761,
            availability="available",
            avg_rating=0.0
        )

        # Books owned by Bob Brown (ID: bob.id)
        book_1984 = Book(
            owner_id=bob.id,
            genre_id=genres_dict["Fiction"],
            title="1984",
            author_name="George Orwell",
            description="The chilling dystopian masterpiece about Big Brother, truth, and love under totalitarianism.",
            front_cover_url="https://images-na.ssl-images-amazon.com/images/I/71kxa1-gG1L.jpg",
            condition="Used",
            borrow_duration_days=30,
            location="Rothschild Blvd 30, Tel Aviv",
            latitude=32.0625,
            longitude=34.7725,
            availability="available",
            avg_rating=0.0
        )
        book_alchemist = Book(
            owner_id=bob.id,
            genre_id=genres_dict["Fiction"],
            title="The Alchemist",
            author_name="Paulo Coelho",
            description="A gorgeous fable about following your dreams and listening to your heart. Inspiring read.",
            front_cover_url="https://images-na.ssl-images-amazon.com/images/I/71aFt4+OTOL.jpg",
            condition="Good",
            borrow_duration_days=30,
            location="Rothschild Blvd 30, Tel Aviv",
            latitude=32.0625,
            longitude=34.7725,
            availability="available",
            avg_rating=0.0
        )

        db.add_all([
            book_hobbit, book_sapiens, book_habits,
            book_mockingbird, book_thinking, book_educated,
            book_dune, book_cleancode,
            book_1984, book_alchemist
        ])
        db.flush()

        # ─── G. Wishlist Seeding ────────────────────────────
        print("- Seeding Wishlists...")
        wishlist_john = Wishlist(user_id=john.id, book_id=book_dune.id)
        wishlist_jane = Wishlist(user_id=jane.id, book_id=book_habits.id)
        wishlist_alice = Wishlist(user_id=alice.id, book_id=book_1984.id)
        db.add_all([wishlist_john, wishlist_jane, wishlist_alice])

        # ─── H. Borrow Requests Seeding ──────────────────────
        print("- Seeding Borrow Requests...")
        now = datetime.now(timezone.utc)

        # Request 1: Jane borrowed "Sapiens" from John, returned and confirmed (Closed lifecycle)
        req_sapiens = BorrowRequest(
            book_id=book_sapiens.id,
            borrower_id=jane.id,
            status="confirmed",
            requested_at=now - timedelta(days=10),
            approved_at=now - timedelta(days=9),
            borrowed_at=now - timedelta(days=9),
            due_date=now + timedelta(days=21),
            returned_at=now - timedelta(days=3),
            confirmed_at=now - timedelta(days=2)
        )

        # Request 2: Jane currently borrowing "Dune" from Alice (Active lifecycle)
        req_dune = BorrowRequest(
            book_id=book_dune.id,
            borrower_id=jane.id,
            status="active",
            requested_at=now - timedelta(days=5),
            approved_at=now - timedelta(days=4),
            borrowed_at=now - timedelta(days=4),
            due_date=now + timedelta(days=26)
        )

        # Request 3: John requested "1984" from Bob (Pending lifecycle)
        req_1984 = BorrowRequest(
            book_id=book_1984.id,
            borrower_id=john.id,
            status="pending",
            requested_at=now - timedelta(hours=12)
        )

        # Request 4: Alice requested "To Kill a Mockingbird" from Jane (Returned but not yet confirmed by owner)
        req_mockingbird = BorrowRequest(
            book_id=book_mockingbird.id,
            borrower_id=alice.id,
            status="returned",
            requested_at=now - timedelta(days=8),
            approved_at=now - timedelta(days=7),
            borrowed_at=now - timedelta(days=7),
            due_date=now + timedelta(days=22),
            returned_at=now - timedelta(hours=3)
        )

        db.add_all([req_sapiens, req_dune, req_1984, req_mockingbird])
        db.flush()

        # ─── I. Reviews Seeding ─────────────────────────────
        print("- Seeding Reviews...")
        # Review for confirmed loan of "Sapiens"
        # Reviewer: Jane (borrower), Reviewee: John (owner/lender), Book: Sapiens
        rev_sapiens = Review(
            borrow_request_id=req_sapiens.id,
            reviewer_id=jane.id,
            reviewee_id=john.id,
            book_id=book_sapiens.id,
            rating=5.0,
            review_text="Fantastic book in perfect brand new hardcover condition. John was extremely friendly and responsive!"
        )

        # Seed another review from a previous hypothetical completed transaction
        # Reviewer: Bob, Reviewee: Jane, Book: To Kill a Mockingbird
        # We'll mock the borrow request for this retrospectively to prevent foreign key errors:
        req_mock_prev = BorrowRequest(
            book_id=book_mockingbird.id,
            borrower_id=bob.id,
            status="confirmed",
            requested_at=now - timedelta(days=20),
            approved_at=now - timedelta(days=19),
            borrowed_at=now - timedelta(days=19),
            due_date=now + timedelta(days=11),
            returned_at=now - timedelta(days=5),
            confirmed_at=now - timedelta(days=4)
        )
        db.add(req_mock_prev)
        db.flush()

        rev_mockingbird = Review(
            borrow_request_id=req_mock_prev.id,
            reviewer_id=bob.id,
            reviewee_id=jane.id,
            book_id=book_mockingbird.id,
            rating=4.5,
            review_text="Excellent read! Jane was prompt and extremely helpful when handling the book transaction."
        )

        db.add_all([rev_sapiens, rev_mockingbird])
        db.flush()

        # ─── J. Conversations & Messages Seeding ────────────
        print("- Seeding Chats & Messages (Fernet Encrypted)...")
        # Conversation between John and Jane regarding Sapiens
        conv_john_jane = Conversation(
            participant_1=john.id,
            participant_2=jane.id,
            book_id=book_sapiens.id,
            last_message_at=now - timedelta(days=9),
            created_at=now - timedelta(days=10)
        )
        db.add(conv_john_jane)
        db.flush()

        msg1 = Message(
            conversation_id=conv_john_jane.id,
            sender_id=jane.id,
            body_encrypted=encrypt("Hi John! I requested to borrow Sapiens. When and where would be convenient for you to meet up?"),
            is_read=True,
            sent_at=now - timedelta(days=10)
        )
        msg2 = Message(
            conversation_id=conv_john_jane.id,
            sender_id=john.id,
            body_encrypted=encrypt("Hi Jane! Sure, Dizengoff center works best for me on weekdays around 6 PM. Does that suit you?"),
            is_read=True,
            sent_at=now - timedelta(days=9, hours=23)
        )
        msg3 = Message(
            conversation_id=conv_john_jane.id,
            sender_id=jane.id,
            body_encrypted=encrypt("Perfect, that works! See you at 6 PM near the main entrance."),
            is_read=True,
            sent_at=now - timedelta(days=9, hours=22)
        )

        # Conversation between Jane and Alice regarding Dune
        conv_jane_alice = Conversation(
            participant_1=jane.id,
            participant_2=alice.id,
            book_id=book_dune.id,
            last_message_at=now - timedelta(days=4),
            created_at=now - timedelta(days=5)
        )
        db.add(conv_jane_alice)
        db.flush()

        msg4 = Message(
            conversation_id=conv_jane_alice.id,
            sender_id=jane.id,
            body_encrypted=encrypt("Hello Alice, I'm very excited to read Dune! I can meet near Nordau Blvd today if that works?"),
            is_read=True,
            sent_at=now - timedelta(days=5)
        )
        msg5 = Message(
            conversation_id=conv_jane_alice.id,
            sender_id=alice.id,
            body_encrypted=encrypt("Hi Jane! Yes, perfect. Let's meet at the coffee shop at the corner of Nordau and Ben Yehuda."),
            is_read=True,
            sent_at=now - timedelta(days=4, hours=22)
        )

        db.add_all([msg1, msg2, msg3, msg4, msg5])
        db.flush()

        # ─── K. Rating Recalculation ────────────────────────
        print("- Recalculating Book and User Average Ratings...")
        # Recalculate book_sapiens rating
        book_sapiens.avg_rating = 5.0
        # Recalculate book_mockingbird rating
        book_mockingbird.avg_rating = 4.5
        
        # Recalculate John's rating (received 5.0 from Jane)
        john.avg_rating = 5.0
        # Recalculate Jane's rating (received 4.5 from Bob)
        jane.avg_rating = 4.5

        db.commit()
        print("\033[92mDatabase seeding completed successfully!\033[0m")
        print("\033[92mCreated 5 high-quality users, 10 physical books, 5 lifecycle borrow requests, and fully functional encrypted chats.\033[0m")

    except Exception as e:
        db.rollback()
        print(f"\n\033[91mError during flush and seed operation: {e}\033[0m")
    finally:
        db.close()

    print("\033[94m" + "="*60 + "\033[0m")


if __name__ == "__main__":
    flush_and_seed()
