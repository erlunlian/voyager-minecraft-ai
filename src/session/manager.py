"""Session Manager - Handles bot session persistence and recovery using SQLAlchemy."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

from session.models import Base, BotStateHistory, LearnedSkill, Session, Task


class SessionManager:
    """Manages bot sessions with PostgreSQL persistence using SQLAlchemy."""

    def __init__(self, db_url: str):
        """Initialize session manager with database URL.

        Args:
            db_url: SQLAlchemy database URL (e.g., postgresql+psycopg2://user:pass@host:port/db)
        """
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False)
        self.current_session_id = None
        self._initialize_tables()

    def _initialize_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self.engine)

    def create_session(
        self, bot_username: str, server_host: str, metadata: Dict[str, Any] = None
    ) -> int:
        """Create a new session."""
        with self.SessionLocal() as db:
            session = Session(
                bot_username=bot_username,
                server_host=server_host,
                metadata=metadata or {},
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            self.current_session_id = session.session_id
            print(f"Created new session: {session.session_id}")
            return session.session_id

    def get_active_session(self, bot_username: str) -> Optional[int]:
        """Get the most recent active session for a bot."""
        with self.SessionLocal() as db:
            session = (
                db.query(Session)
                .filter(
                    Session.bot_username == bot_username, Session.status == "active"
                )
                .order_by(desc(Session.last_update))
                .first()
            )

            if session:
                self.current_session_id = session.session_id
                return session.session_id

        return None

    def update_session_status(self, session_id: int, status: str):
        """Update session status."""
        with self.SessionLocal() as db:
            session = db.query(Session).filter(Session.session_id == session_id).first()
            if session:
                session.status = status
                session.last_update = datetime.utcnow()
                db.commit()

    def log_task(self, task_description: str, status: str = "pending") -> int:
        """Log a new task."""
        with self.SessionLocal() as db:
            task = Task(
                session_id=self.current_session_id,
                task_description=task_description,
                status=status,
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return task.task_id

    def update_task(
        self,
        task_id: int,
        status: str = None,
        success: bool = None,
        evaluation: Dict[str, Any] = None,
        bot_state_before: Dict[str, Any] = None,
        bot_state_after: Dict[str, Any] = None,
        generated_code: str = None,
        execution_result: Dict[str, Any] = None,
    ):
        """Update task with results."""
        with self.SessionLocal() as db:
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                return

            if status:
                task.status = status
            if success is not None:
                task.success = success
            if status in ["completed", "failed"]:
                task.completed_at = datetime.utcnow()
            if evaluation:
                task.evaluation = evaluation
            if bot_state_before:
                task.bot_state_before = bot_state_before
            if bot_state_after:
                task.bot_state_after = bot_state_after
            if generated_code:
                task.generated_code = generated_code
            if execution_result:
                task.execution_result = execution_result

            db.commit()

    def log_learned_skill(self, task_id: int, skill_name: str, skill_code: str):
        """Log a newly learned skill."""
        with self.SessionLocal() as db:
            skill = LearnedSkill(
                session_id=self.current_session_id,
                task_id=task_id,
                skill_name=skill_name,
                skill_code=skill_code,
            )
            db.add(skill)
            db.commit()

    def log_bot_state(self, bot_state, event_type: str = "update"):
        """Log bot state snapshot.

        Args:
            bot_state: BotState dataclass or dict
            event_type: Type of event (task_start, task_execute, etc.)
        """
        with self.SessionLocal() as db:
            # Handle both BotState dataclass and dict
            if hasattr(bot_state, "position"):
                # BotState dataclass
                position = {
                    "x": bot_state.position.x,
                    "y": bot_state.position.y,
                    "z": bot_state.position.z,
                }
                inventory = [
                    {"name": item.name, "count": item.count, "slot": item.slot}
                    for item in bot_state.inventory
                ]
                health = bot_state.health
                food = bot_state.food
            else:
                # Dict fallback
                position = bot_state.get("position", {})
                inventory = bot_state.get("inventory", [])
                health = bot_state.get("health", 0)
                food = bot_state.get("food", 0)

            state = BotStateHistory(
                session_id=self.current_session_id,
                position=position,
                inventory=inventory,
                health=health,
                food=food,
                event_type=event_type,
            )
            db.add(state)
            db.commit()

    def get_completed_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently completed tasks."""
        with self.SessionLocal() as db:
            tasks = (
                db.query(Task)
                .filter(
                    Task.session_id == self.current_session_id,
                    Task.status == "completed",
                )
                .order_by(desc(Task.completed_at))
                .limit(limit)
                .all()
            )

            return [
                {
                    "task_description": task.task_description,
                    "success": task.success,
                    "evaluation": task.evaluation,
                }
                for task in tasks
            ]

    def get_failed_tasks(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recently failed tasks."""
        with self.SessionLocal() as db:
            tasks = (
                db.query(Task)
                .filter(
                    Task.session_id == self.current_session_id, Task.status == "failed"
                )
                .order_by(desc(Task.completed_at))
                .limit(limit)
                .all()
            )

            return [
                {
                    "task_description": task.task_description,
                    "evaluation": task.evaluation,
                }
                for task in tasks
            ]

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics for current session."""
        with self.SessionLocal() as db:
            # Get task stats
            tasks = (
                db.query(Task).filter(Task.session_id == self.current_session_id).all()
            )

            total_tasks = len(tasks)
            successful_tasks = sum(1 for t in tasks if t.success is True)
            failed_tasks = sum(1 for t in tasks if t.success is False)

            # Get skills count
            skills_count = (
                db.query(LearnedSkill)
                .filter(LearnedSkill.session_id == self.current_session_id)
                .count()
            )

            return {
                "total_tasks": total_tasks,
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "skills_learned": skills_count,
            }

    def resume_session(self, session_id: int) -> Dict[str, Any]:
        """Resume a previous session."""
        self.current_session_id = session_id

        with self.SessionLocal() as db:
            # Get last bot state
            last_state = (
                db.query(BotStateHistory)
                .filter(BotStateHistory.session_id == session_id)
                .order_by(desc(BotStateHistory.timestamp))
                .first()
            )

            # Get incomplete tasks
            pending_tasks = (
                db.query(Task)
                .filter(Task.session_id == session_id, Task.status == "pending")
                .order_by(Task.created_at)
                .all()
            )

        self.update_session_status(session_id, "active")

        return {
            "session_id": session_id,
            "last_state": (
                {
                    "position": last_state.position,
                    "inventory": last_state.inventory,
                    "health": last_state.health,
                    "food": last_state.food,
                    "event_type": last_state.event_type,
                }
                if last_state
                else None
            ),
            "pending_tasks": [
                {
                    "task_id": task.task_id,
                    "task_description": task.task_description,
                    "created_at": task.created_at,
                }
                for task in pending_tasks
            ],
        }

    def close(self):
        """Close database connection."""
        self.engine.dispose()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
