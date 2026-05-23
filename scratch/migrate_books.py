import sqlite3

def migrate():
    conn = sqlite3.connect('/home/roni/Desktop/BookBuddy/bookbuddy.db')
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(books)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "approval_status" not in columns:
            print("Adding approval_status column to books table...")
            cursor.execute("ALTER TABLE books ADD COLUMN approval_status VARCHAR(20) DEFAULT 'approved'")
            print("Column added successfully.")
        else:
            print("Column approval_status already exists.")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        
    finally:
        conn.commit()
        conn.close()

if __name__ == "__main__":
    migrate()
