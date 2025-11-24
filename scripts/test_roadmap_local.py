import sys
from pathlib import Path

# Ensure project root is on sys.path when running this script from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from storage.db import init_db, engine
from sqlmodel import Session, select
from storage.models import User, LearningRoadmap
from services.ndlrm_service import generate_learning_roadmap, get_user_roadmap
import time

# Ensure DB and tables exist
init_db()

# Create test user if not exists
with Session(engine) as s:
    user = s.exec(select(User).where(User.email == 'test@example.com')).first()
    if not user:
        user = User(email='test@example.com', hashed_password='x', full_name='Test User')
        s.add(user)
        s.commit()
        s.refresh(user)
    print('Test user id:', user.id)

# Call generate_learning_roadmap
roadmap = generate_learning_roadmap(user_id=user.id, target_career='AI Engineer')
print('Generated roadmap (function returned):', roadmap)

# Query DB for latest roadmap rows
with Session(engine) as s:
    rows = s.exec(select(LearningRoadmap).where(LearningRoadmap.user_id == user.id).order_by(LearningRoadmap.generated_at.desc())).all()
    print('Rows saved:', len(rows))
    if rows:
        for r in rows:
            print('Row id:', r.id, 'week_start:', r.week_start, 'generated_at:', r.generated_at)

# Also call get_user_roadmap
gm = get_user_roadmap(user.id)
print('get_user_roadmap result:', gm)
