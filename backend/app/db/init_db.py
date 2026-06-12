import asyncio
# pyrefly: ignore [missing-import]
from sqlalchemy import text
# Import engine and Base from session
from backend.app.db.session import engine, Base
# Import all models to ensure they are registered on the Base metadata
from backend.app.db.models import User, Thread, Brief, Annotation, Evaluation, CostMetric, LongTermMemory

async def init_db():
    print("Connecting to PostgreSQL...")
    async with engine.begin() as conn:
        # 1. Enable pgvector extension
        print("Checking/Enabling pgvector extension...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        
        # 2. Create all tables
        print("Recreating database tables according to SQLAlchemy models...")
        # Note: In production, you'd use Alembic migrations. For initial setup and testing, 
        # Base.metadata.create_all is perfect.
        await conn.run_sync(Base.metadata.create_all)
        
        # 3. Seed default analyst user
        user_check = await conn.execute(text("SELECT id FROM users WHERE email = 'analyst@example.com';"))
        user = user_check.fetchone()
        if not user:
            print("Seeding default analyst user...")
            default_user_id = "00000000-0000-0000-0000-000000000000"
            await conn.execute(text(
                "INSERT INTO users (id, email, password_hash, created_at) "
                "VALUES (:id, 'analyst@example.com', 'scrypt:32768:8:1$default_hash_value', NOW());"
            ), {"id": default_user_id})
            print(f"✅ Default analyst user seeded (ID: {default_user_id})")
            
    print("Database tables created and seeded successfully!")
    
    # 3. Verification checks
    print("\n--- Verifying Setup ---")
    async with engine.connect() as conn:
        # Check pgvector extension status
        ext_result = await conn.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"))
        ext = ext_result.fetchone()
        if ext:
            print(f"✅ Extension '{ext[0]}' is ACTIVE (Version: {ext[1]})")
        else:
            print("❌ pgvector extension is NOT active")
            
        # Check tables list in public schema
        table_result = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
        ))
        tables = [row[0] for row in table_result.fetchall()]
        print(f"✅ Created {len(tables)} tables: {', '.join(tables)}")

if __name__ == "__main__":
    asyncio.run(init_db())
