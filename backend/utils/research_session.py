import json
from typing import Optional
from datetime import datetime, timedelta
from loguru import logger


# In-memory session storage (should use Redis in production)
# Structure: { session_id: { "user_id": int, "user_question": str, "memories": list, "created_at": datetime, "plan": list } }
_research_sessions: dict = {}

# Session expires after 30 minutes
SESSION_EXPIRATION_MINUTES = 30


class ResearchSessionManager:
    @staticmethod
    def create_session(
        session_id: str,
        user_id: int,
        conversation_id: int,
        user_question: str,
        memories: list,
        research_plan: list,
    ) -> None:
        """Create a new research session with plan"""
        _research_sessions[session_id] = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "user_question": user_question,
            "memories": [str(m) if not isinstance(m, str) else m for m in memories],
            "research_plan": research_plan,
            "created_at": datetime.now(),
        }
        logger.info(f"[ResearchSessionManager] Created research session: {session_id}")

    @staticmethod
    def get_session(session_id: str) -> Optional[dict]:
        """Get session data by ID"""
        session = _research_sessions.get(session_id)
        if not session:
            return None
        
        # Check expiration
        created_at = session.get("created_at")
        if created_at and datetime.now() - created_at > timedelta(minutes=SESSION_EXPIRATION_MINUTES):
            ResearchSessionManager.delete_session(session_id)
            return None
        
        return session

    @staticmethod
    def delete_session(session_id: str) -> None:
        """Delete a session"""
        if session_id in _research_sessions:
            del _research_sessions[session_id]
            logger.info(f"[ResearchSessionManager] Deleted research session: {session_id}")

    @staticmethod
    def update_approved_plan(session_id: str, approved_plan: list) -> bool:
        """Update session with approved plan"""
        session = _research_sessions.get(session_id)
        if not session:
            return False
        
        session["approved_plan"] = approved_plan
        session["approved_at"] = datetime.now()
        logger.info(f"[ResearchSessionManager] Updated research session with approved plan: {session_id}")
        return True

    @staticmethod
    def cleanup_expired_sessions() -> int:
        """Clean up expired sessions"""
        global _research_sessions
        expired_count = 0
        now = datetime.now()
        
        for session_id in list(_research_sessions.keys()):
            session = _research_sessions[session_id]
            created_at = session.get("created_at")
            if created_at and now - created_at > timedelta(minutes=SESSION_EXPIRATION_MINUTES):
                del _research_sessions[session_id]
                expired_count += 1
        
        if expired_count > 0:
            logger.info(f"[ResearchSessionManager] Cleaned up {expired_count} expired sessions")
        
        return expired_count


research_session_manager = ResearchSessionManager()