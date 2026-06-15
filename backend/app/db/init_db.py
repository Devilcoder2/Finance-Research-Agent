import asyncio
# pyrefly: ignore [missing-import]
from sqlalchemy import text
# Import engine and Base from session
from backend.app.db.session import engine, Base
# Import all models to ensure they are registered on the Base metadata
from backend.app.db.models import User, Thread, Brief, Annotation, Evaluation, CostMetric, LongTermMemory
from backend.app.api.auth import hash_password

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
        
        # 2.5 Create HNSW vector index
        print("Creating HNSW index on long_term_memory.embedding...")
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS long_term_memory_embedding_hnsw_idx "
            "ON long_term_memory USING hnsw (embedding vector_cosine_ops);"
        ))
        
        # 3. Seed default analyst user
        user_check = await conn.execute(text("SELECT id, password_hash FROM users WHERE email = 'analyst@example.com';"))
        user = user_check.fetchone()
        default_user_id = "00000000-0000-0000-0000-000000000000"
        password_hash = hash_password("password")
        if not user:
            print("Seeding default analyst user...")
            await conn.execute(text(
                "INSERT INTO users (id, email, password_hash, created_at) "
                "VALUES (:id, 'analyst@example.com', :password_hash, NOW());"
            ), {"id": default_user_id, "password_hash": password_hash})
            print(f"✅ Default analyst user seeded (ID: {default_user_id})")
        else:
            if user[1] == "scrypt:32768:8:1$default_hash_value":
                print("Updating default analyst user's password hash from fallback to properly computed hash...")
                await conn.execute(text(
                    "UPDATE users SET password_hash = :password_hash WHERE id = :id;"
                ), {"id": user[0], "password_hash": password_hash})
                print("✅ Default analyst user's password hash updated successfully.")
            
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
