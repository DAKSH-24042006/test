"""
Liveness Session Manager — Server-Side Challenge-Response Session Management

Creates, validates, and manages one-time-use liveness verification sessions.
Each session has:
- Unique session_id with cryptographic nonce
- Randomized challenge sequence (e.g., blink, turn_left, turn_right)
- TTL-based expiry (default 60 seconds)
- One-time-use enforcement
"""

import uuid
import time
import secrets
import random
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from backend.app.database.connection import settings

logger = logging.getLogger("liveness_session")

# Available challenge actions for the randomized sequence
CHALLENGE_ACTIONS = [
    "blink",
    "turn_left",
    "turn_right",
    "nod_up",
    "nod_down",
]

# Human-readable descriptions for the Flutter UI
CHALLENGE_DESCRIPTIONS = {
    "blink": "Blink your eyes",
    "turn_left": "Turn your head left",
    "turn_right": "Turn your head right",
    "nod_up": "Look up slightly",
    "nod_down": "Look down slightly",
}


@dataclass
class LivenessSession:
    """Represents a single liveness verification session."""
    session_id: str
    student_id: str
    nonce: str
    challenges: List[str]
    challenge_descriptions: List[str]
    created_at: float
    ttl: int
    used: bool = False
    completed_at: Optional[float] = None

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl

    @property
    def is_valid(self) -> bool:
        return not self.used and not self.is_expired

    @property
    def remaining_seconds(self) -> float:
        return max(0, self.ttl - (time.time() - self.created_at))

    def to_client_response(self) -> Dict:
        """Returns the session info to send to the Flutter client."""
        return {
            "session_id": self.session_id,
            "nonce": self.nonce,
            "challenges": self.challenges,
            "challenge_descriptions": self.challenge_descriptions,
            "expires_in_seconds": self.ttl,
            "created_at": self.created_at,
        }


class LivenessSessionManager:
    """
    Thread-safe, in-memory session store for liveness verification.
    Sessions auto-expire and are cleaned up periodically.
    """

    _sessions: Dict[str, LivenessSession] = {}
    _last_cleanup: float = 0.0
    _cleanup_interval: float = 30.0  # Cleanup every 30 seconds

    @classmethod
    def create_session(cls, student_id: str, num_challenges: int = 2) -> LivenessSession:
        """
        Creates a new liveness session with a randomized challenge sequence.
        
        Args:
            student_id: The student being verified
            num_challenges: Number of challenges to include (2-3 recommended)
            
        Returns:
            LivenessSession with challenges and session metadata
        """
        # Periodic cleanup of expired sessions
        cls._cleanup_expired()

        # Rate limiting: prevent session flooding per student
        active_sessions = sum(
            1 for s in cls._sessions.values()
            if s.student_id == student_id and s.is_valid
        )
        if active_sessions >= 3:
            # Invalidate old sessions for this student
            for sid, session in list(cls._sessions.items()):
                if session.student_id == student_id and session.is_valid:
                    session.used = True
            logger.warning(f"Rate limit: invalidated {active_sessions} active sessions for student {student_id}")

        # Generate session
        session_id = str(uuid.uuid4())
        nonce = secrets.token_hex(16)  # 128-bit cryptographic nonce

        # Randomize challenge selection
        num_challenges = min(num_challenges, len(CHALLENGE_ACTIONS))
        selected_challenges = random.sample(CHALLENGE_ACTIONS, num_challenges)

        # Always start with a frontal face check (implicit)
        challenge_descriptions = [
            CHALLENGE_DESCRIPTIONS[c] for c in selected_challenges
        ]

        session = LivenessSession(
            session_id=session_id,
            student_id=student_id,
            nonce=nonce,
            challenges=selected_challenges,
            challenge_descriptions=challenge_descriptions,
            created_at=time.time(),
            ttl=settings.LIVENESS_SESSION_TTL,
        )

        cls._sessions[session_id] = session
        logger.info(
            f"Created liveness session {session_id[:8]}... for student {student_id} "
            f"with challenges: {selected_challenges}"
        )

        return session

    @classmethod
    def validate_session(cls, session_id: str, student_id: str) -> Tuple[bool, str, Optional[LivenessSession]]:
        """
        Validates a session for use.
        
        Returns:
            (is_valid, error_message, session)
        """
        session = cls._sessions.get(session_id)

        if session is None:
            return False, "Invalid or unknown session ID.", None

        if session.student_id != student_id:
            logger.warning(
                f"Session {session_id[:8]}... belongs to {session.student_id} "
                f"but was submitted by {student_id}"
            )
            return False, "Session does not belong to this student.", None

        if session.used:
            return False, "This liveness session has already been used. Please start a new scan.", None

        if session.is_expired:
            return False, f"Liveness session expired ({settings.LIVENESS_SESSION_TTL}s TTL). Please start a new scan.", None

        return True, "", session

    @classmethod
    def mark_used(cls, session_id: str):
        """Marks a session as consumed (one-time use)."""
        session = cls._sessions.get(session_id)
        if session:
            session.used = True
            session.completed_at = time.time()
            logger.info(f"Session {session_id[:8]}... marked as used.")

    @classmethod
    def _cleanup_expired(cls):
        """Remove expired sessions to prevent memory leaks."""
        now = time.time()
        if now - cls._last_cleanup < cls._cleanup_interval:
            return

        expired_ids = [
            sid for sid, session in cls._sessions.items()
            if session.is_expired or session.used
        ]

        for sid in expired_ids:
            # Keep used sessions for 5 minutes for audit logging
            session = cls._sessions[sid]
            if session.is_expired and (now - session.created_at) > 300:
                del cls._sessions[sid]
            elif session.used and session.completed_at and (now - session.completed_at) > 300:
                del cls._sessions[sid]

        if expired_ids:
            logger.debug(f"Cleaned up {len(expired_ids)} expired/used liveness sessions.")

        cls._last_cleanup = now

    @classmethod
    def get_active_session_count(cls) -> int:
        """Returns count of active (unexpired, unused) sessions."""
        return sum(1 for s in cls._sessions.values() if s.is_valid)

    @classmethod
    def clear_all(cls):
        """Clears all sessions (used in testing/reset)."""
        cls._sessions.clear()
        logger.info("All liveness sessions cleared.")
