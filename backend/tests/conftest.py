"""
Test fixtures and configuration
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.db.session import Base, get_db
from app.core.security import create_access_token
from app.models.user import User
from app.models.task import Task
from app.models.transcription import Transcription
from app.models.processing_history import ProcessingHistory


# Test database URL (PostgreSQL test database)
SQLALCHEMY_TEST_DATABASE_URL = "postgresql+asyncpg://user:password@postgres:5432/whisper_test"

# Create test engine
test_engine = create_async_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    poolclass=NullPool,
)

# Create test session factory
TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create test database and tables"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def test_client(test_db):
    """Create test client with test database"""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(test_db):
    """Create test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        is_admin=False
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(test_db):
    """Create test admin user"""
    admin = User(
        username="admin",
        email="admin@example.com",
        is_admin=True
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


@pytest.fixture
def user_token(test_user):
    """Create access token for test user"""
    return create_access_token({
        "sub": test_user.username,
        "user_id": test_user.id,
        "is_admin": test_user.is_admin
    })


@pytest.fixture
def admin_token(test_admin):
    """Create access token for admin user"""
    return create_access_token({
        "sub": test_admin.username,
        "user_id": test_admin.id,
        "is_admin": test_admin.is_admin
    })


@pytest.fixture
def user_headers(user_token):
    """Create auth headers for test user"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token):
    """Create auth headers for admin user"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def test_task(test_db, test_user):
    """Create test task"""
    import uuid
    task = Task(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        filename="test.mp3",
        file_path="/tmp/test.mp3",
        file_size=11010048,  # ~10.5 MB in bytes
        model_name="tiny",
        language="ja",
        status="pending",
        progress=0,
        file_format="mp3"
    )
    test_db.add(task)
    await test_db.commit()
    await test_db.refresh(task)
    return task


@pytest_asyncio.fixture
async def completed_task(test_db, test_user):
    """Create completed test task with transcription"""
    import uuid
    from datetime import datetime, timedelta

    task = Task(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        filename="completed.mp3",
        file_path="/tmp/completed.mp3",
        file_size=15942656,  # ~15.2 MB in bytes
        model_name="tiny",
        language="ja",
        status="completed",
        progress=100,
        file_format="mp3",
        started_at=datetime.utcnow() - timedelta(minutes=5),
        completed_at=datetime.utcnow()
    )
    test_db.add(task)
    await test_db.flush()

    # Create transcription
    segments = [
        {
            "id": 0,
            "start": 0.0,
            "end": 5.5,
            "text": "これはテストです。",
            "speaker_id": 1,
            "speaker_label": "Speaker 1",
            "confidence": 0.95
        },
        {
            "id": 1,
            "start": 5.5,
            "end": 10.0,
            "text": "これは二番目のセグメントです。",
            "speaker_id": 2,
            "speaker_label": "Speaker 2",
            "confidence": 0.92
        }
    ]

    transcription = Transcription(
        task_id=task.id,
        transcription_text="これはテストです。 これは二番目のセグメントです。",
        segments=segments,
        word_count=len("これはテストです。 これは二番目のセグメントです。".split())
    )
    test_db.add(transcription)
    await test_db.commit()
    await test_db.refresh(task)
    await test_db.refresh(transcription)

    return task


@pytest_asyncio.fixture
async def test_processing_history(test_db, completed_task):
    """Create test processing history"""
    # Convert file_size from bytes to MB
    file_size_mb = completed_task.file_size / (1024 * 1024)

    history = ProcessingHistory(
        task_id=completed_task.id,
        user_id=completed_task.user_id,
        processing_time_seconds=300,
        gpu_memory_used_mb=8192,
        model_name=completed_task.model_name,
        file_format=completed_task.file_format,
        file_size_mb=file_size_mb,
        success=True,
        error_type=None
    )
    test_db.add(history)
    await test_db.commit()
    await test_db.refresh(history)
    return history
